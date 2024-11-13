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

from globals import *

class TSPacket:
    def __init__(self):
        self.pid = 0
        self.errorbit = 1
        self.pesstartbit = 0
        self.adaption = 1
        self.adaptiondata = ''
        self.pesdata = ''


class TSParser:
    def __init__(self):
        self.monitor = MONITOR()
        

    def determineLength(self, filename: str) -> int and float:
        log("TSParser: determineLength " + filename)
        self.pid = -1

        try: self.File = FileAccess.open(filename, "rb", None)
        except:
            log("TSParser: Unable to open the file")
            return 0

        self.filesize = self.getFileSize()
        self.packetLength = self.findPacketLength()

        if self.packetLength <= 0:
            return 0

        start = self.getStartTime()
        log('TSParser: Start - ' + str(start))
        end = self.getEndTime()
        log('TSParser: End - ' + str(end))

        if end > start:
            dur = int((end - start) / 90000)
        else:
            dur = 0

        self.File.close()
        log("TSParser: Duration is " + str(dur))
        return dur
        

    def findPacketLength(self):
        log('TSParser: findPacketLength')
        maxbytes = 600
        start = 0
        self.packetLength = 0

        
        while not self.monitor.abortRequested() and maxbytes > 0:
            maxbytes -= 1

            try:
                data = self.File.readBytes(1)
                data = struct.unpack('B', data)

                if data[0] == 71:
                    if start > 0:
                        end = self.File.tell()
                        break
                    else:
                        start = self.File.tell()
                        # A minimum of 188, so skip the rest
                        self.File.seek(187, 1)
            except:
                log('TSParser: Exception in findPacketLength')
                return

        if (start > 0) and (end > start):
            log('TSParser: Packet Length: ' + str(int(end - start)))
            return (end - start)

        return


    def getFileSize(self):
        size = 0
        try:
            pos = self.File.tell()
            self.File.seek(0, 2)
            size = self.File.tell()
            self.File.seek(pos, 0)
        except:
            pass

        return size


    def getStartTime(self):
        # A reasonably high number of retries in case the PES starts in the middle
        # and is it's maximum length
        maxpackets = 12000
        log('TSParser: getStartTime')

        try:
            self.File.seek(0, 0)
        except:
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
                    log('TSParser: PID: ' + str(self.pid))
                    return ret

        return 0


    def getEndTime(self):
        log('TSParser: getEndTime')
        packetcount = int(self.filesize / self.packetLength)

        try:
            self.File.seek((packetcount * self.packetLength)- self.packetLength, 0)
        except:
            return 0

        maxpackets = 12000

        while not self.monitor.abortRequested() and maxpackets > 0:
            packet = self.readTSPacket()
            maxpackets -= 1

            if packet == None:
                log('TSParser: getEndTime got a null packet')
                return 0

            if packet.errorbit == 0 and packet.pesstartbit == 1 and packet.pid == self.pid:
                ret = self.getPTS(packet)

                if ret > 0:
                    log('TSParser: getEndTime returning time')
                    return ret
            else:
                try:
                    self.File.seek(-1 * (self.packetLength * 2), 1)
                except:
                    log('TSParser: exception')
                    return 0

        log('TSParser: getEndTime no found end time')
        return 0


    def getPTS(self, packet):
        timestamp = 0
        log('TSParser: getPTS')

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
        except:
            log('TSParser: exception in getPTS')
            pass

        log('TSParser: getPTS returning 0')
        return 0


    def readTSPacket(self):
        packet = TSPacket()
        pos = 0

        try:
            data = self.File.readBytes(4)
            pos = 4
            data = struct.unpack('4B', data)

            if data[0] == 71:
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
        except:
            log('TSParser: readTSPacket exception')
            return None

        return packet
