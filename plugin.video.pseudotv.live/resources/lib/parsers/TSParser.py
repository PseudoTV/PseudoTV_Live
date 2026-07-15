#   Copyright (C) 2024 Jason Anderson, Lunatixz
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

from variables import *
from typing import Optional, Union
import struct

class TSPacket:


    def __init__(self):
        self.pid = 0
        self.errorbit = 1
        self.pesstartbit = 0
        self.adaption = 1
        self.adaptiondata = ''
        self.pesdata = ''


class TSParser:
    """
    Parser for MPEG-TS (.ts) video files.
    Duration is calculated from PTS (Presentation TimeStamp) in 90kHz clock cycles.
    """


    def __init__(self):
        self.monitor = MONITOR()
        


    def determineLength(self, filename: str) -> Union[int, float]:
        """
        Determines video length from TS file by reading PTS timestamps.
        Returns duration in seconds.
        """
        LOG("TSParser: determineLength, [%s]"%filename)
        self.pid = -1

        try: 
            self.File = FileAccess.open(filename, "rb", None)
        except IOError as e:
            LOG("TSParser: determineLength, unable to open the file, failed!\n%s"%e)
            return 0

        try:
            self.filesize = self.getFileSize()
            self.packetLength = self.findPacketLength()

            if self.packetLength <= 0:
                LOG("TSParser: determineLength, invalid packet length")
                return 0

            start = self.getStartTime()
            LOG('TSParser: determineLength, start = %s'%(start))
            end = self.getEndTime()
            LOG('TSParser: determineLength, end = %s'%(end))

            if end > start:
                # 90000 is the PTS clock frequency (90 kHz)
                dur = int((end - start) / 90000)
            else:
                dur = 0

                LOG("TSParser: determineLength, duration = %s seconds"%(dur))
            return dur
        finally:
            try:
                self.File.close()
            except Exception as e:
                LOG('TSParser: File.close, failed!\n%s' % e, xbmc.LOGDEBUG)
        


    def findPacketLength(self) -> int:
        LOG('TSParser: findPacketLength')
        maxbytes = 600
        start = 0
        self.packetLength = 0
        end = 0
        
        while not self.monitor.abortRequested() and maxbytes > 0:
            maxbytes -= 1

            try:
                data = self.File.readBytes(1)
                data = struct.unpack('B', data)

                if data[0] == 71:  # TS packet sync byte
                    if start > 0:
                        end = self.File.tell()
                        break
                    else:
                        start = self.File.tell()
                        # A minimum of 188, so skip the rest
                        self.File.seek(187, 1)
            except Exception as e:
                LOG('TSParser: findPacketLength, failed!\n%s'%e)
                return 0

        if (start > 0) and (end > start):
            LOG('TSParser: findPacketLength, packet length = %s'%(end - start))
            return (end - start)

        return 0


    def getFileSize(self) -> int:
        size = 0
        try:
            pos = self.File.tell()
            self.File.seek(0, 2)
            size = self.File.tell()
            self.File.seek(pos, 0)
        except Exception as e:
                LOG("TSParser: getFileSize, failed!\n%s"%e)

        return size


    def getStartTime(self) -> int:
        """Find the first valid PTS timestamp in the file."""
        # A reasonably high number of retries in case the PES starts in the middle
        # and is it's maximum length
        maxpackets = 12000
        LOG('TSParser: getStartTime')

        try:
            self.File.seek(0, 0)
        except Exception as e:
            LOG("TSParser: seekToStart, failed!\n%s"%e)
            return 0

        while not self.monitor.abortRequested() and maxpackets > 0:
            packet = self.readTSPacket()
            maxpackets -= 1

            if packet == None:
                return 0

            if packet.errorbit == 0 and packet.pesstartbit == 1:
                ret = self.getPTS(packet)

                if ret > 0:
                    self.pid = packet.pid
                    LOG('TSParser: getStartTime, PID = %s'%(self.pid))
                    return ret

        return 0


    def getEndTime(self) -> int:
        """Find the last valid PTS timestamp in the file."""
        LOG('TSParser: getEndTime')
        if self.packetLength <= 0:
            return 0
        
        packetcount = int(self.filesize / self.packetLength)

        try:
            self.File.seek((packetcount * self.packetLength) - self.packetLength, 0)
        except Exception as e:
            LOG("TSParser: Error seeking to end: %s"%e)
            return 0

        maxpackets = 12000

        while not self.monitor.abortRequested() and maxpackets > 0:
            packet = self.readTSPacket()
            maxpackets -= 1

            if packet == None:
                LOG('TSParser: getEndTime got a null packet')
                return 0

            if packet.errorbit == 0 and packet.pesstartbit == 1 and packet.pid == self.pid:
                ret = self.getPTS(packet)

                if ret > 0:
                    LOG('TSParser: getEndTime returning time')
                    return ret
            else:
                try:
                    self.File.seek(-1 * (self.packetLength * 2), 1)
                except Exception as e:
                    LOG('TSParser: exception seeking: %s'%e)
                    return 0

        LOG('TSParser: getEndTime no found end time')
        return 0


    def getPTS(self, packet: TSPacket) -> int:
        """Extract PTS (Presentation TimeStamp) from packet data."""
        timestamp = 0
        LOG('TSParser: getPTS')

        try:
            data = struct.unpack('19B', packet.pesdata[:19])

            # start code
            if data[0] == 0 and data[1] == 0 and data[2] == 1:
                # cant be a navigation packet
                if data[3] != 190 and data[3] != 191:
                    offset = 0

                    if (data[9] >> 4) == 3:
                        offset = 5

                    # a little dangerous...ignoring the LSB of the timestamp
                    timestamp = ((data[9 + offset] >> 1) & 7) << 30
                    timestamp = timestamp | (data[10 + offset] << 22)
                    timestamp = timestamp | ((data[11 + offset] >> 1) << 15)
                    timestamp = timestamp | (data[12 + offset] << 7)
                    timestamp = timestamp | (data[13 + offset] >> 1)
                    return timestamp
        except Exception as e:
            LOG('TSParser: exception in getPTS: %s'%e)

        LOG('TSParser: getPTS returning 0')
        return 0


    def readTSPacket(self) -> Optional[TSPacket]:
        """Read and parse a single TS packet from the file."""
        packet = TSPacket()
        pos = 0

        try:
            data = self.File.readBytes(4)
            pos = 4
            data = struct.unpack('4B', data)

            if data[0] == 71:  # TS packet sync byte
                packet.pid = (data[1] & 31) << 8
                packet.pid = packet.pid | data[2]

                # skip tables and null packets
                if packet.pid < 21 or packet.pid == 8191:
                    self.File.seek(self.packetLength - 4, 1)
                else:
                    packet.adaption = (data[3] >> 4) & 3
                    packet.errorbit = data[1] >> 7
                    packet.pesstartbit = (data[1] >> 6) & 1

                    if packet.adaption > 1:
                        data = self.File.readBytes(1)
                        length = struct.unpack('B', data)[0]

                        if length > 0:
                            data = self.File.readBytes(length)
                        else:
                            length = 0

                        pos += length + 1

                    if pos < 188:
                        # read the PES data
                        packet.pesdata = self.File.readBytes(self.packetLength - pos)
        except Exception as e:
            LOG('TSParser: readTSPacket exception: %s'%e)
            return None

        return packet