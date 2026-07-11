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
from typing import Union
import struct

class MKVParser:
    """
    Parser for Matroska (MKV) video files.
    Extracts duration from EBML header information.
    """
    def __init__(self):
        self.monitor = MONITOR()
        

    def determineLength(self, filename: str) -> Union[int, float]:
        """
        Determines video length from MKV file.
        Returns duration in seconds.
        """
        LOG("MKVParser: determineLength %s"%filename)
        try: 
            self.File = FileAccess.open(filename, "rb", None)
        except IOError as e:
            LOG("MKVParser: Unable to open the file: %s"%e)
            return 0

        try:
            size = self.findHeader()

            if size == 0:
                LOG('MKVParser: Unable to find the segment info')
                dur = 0
            else:
                dur = int(round(self.parseHeader(size)))

            LOG("MKVParser: Duration is %s seconds"%(dur))
            return dur
        except Exception as e:
            LOG("MKVParser: Error: %s"%e, xbmc.LOGERROR)
            LOG(traceback.format_exc(), xbmc.LOGERROR)
            return 0
        finally:
            try:
                self.File.close()
            except Exception as e:
                LOG('MKVParser: File.close failed: %s' % e, xbmc.LOGDEBUG)
        

    def parseHeader(self, size: int) -> Union[int, float]:
        """Parse MKV header to extract duration and timecode scale."""
        duration = 0
        timecode = 0
        fileend = self.File.tell() + size
        datasize = 1
        data = 1

        while not self.monitor.abortRequested() and self.File.tell() < fileend and datasize > 0 and data > 0:
            data = self.getEBMLId()
            datasize = self.getDataSize()

            if data == 0x2ad7b1:  # TimecodeScale element
                timecode = 0

                try:
                    for x in range(datasize):
                        timecode = (timecode << 8) + struct.unpack('B', self.getData(1))[0]
                except Exception as e:
                    LOG("MKVParser: Error reading timecode: %s"%e)
                    timecode = 0

                if duration != 0 and timecode != 0:
                    break
                    
            elif data == 0x4489:  # Duration element
                try:
                    if datasize == 4:
                        duration = int(struct.unpack('>f', self.getData(datasize))[0])
                    else:
                        duration = int(struct.unpack('>d', self.getData(datasize))[0])
                except Exception as e:
                    LOG("MKVParser: Error getting duration in header, size is %s: %s"%(datasize, e))
                    duration = 0

                if timecode != 0 and duration != 0:
                    break
            else:
                try:    
                    self.File.seek(datasize, 1)
                except Exception as e:
                    LOG('MKVParser: Error while seeking: %s'%e)
                    return 0

        if duration > 0 and timecode > 0:
            # Convert duration from floating point (in milliseconds) to seconds
            dur = (duration * timecode) / 1000000000
            return dur

        return 0


    def findHeader(self) -> int:
        """Locate the segment info header in the MKV file."""
        LOG("MKVParser: findHeader")
        filesize = self.getFileSize()
        if filesize == 0:
            LOG("MKVParser: Empty file")
            return 0

        data = self.getEBMLId()

        # Check for EBML element ID (1A 45 DF A3)
        if data != 0x1A45DFA3:
            LOG("MKVParser: Not a proper MKV")
            return 0

        datasize = self.getDataSize()
        
        try:
            self.File.seek(datasize, 1)
        except Exception as e:
            LOG('MKVParser: Error while seeking: %s'%e)
            return 0

        data = self.getEBMLId()

        # Look for the segment header (element ID 18 53 80 67)
        while not self.monitor.abortRequested() and data != 0x18538067 and self.File.tell() < filesize and data > 0 and datasize > 0:
            datasize = self.getDataSize()

            try:
                self.File.seek(datasize, 1)
            except Exception as e:
                LOG('MKVParser: Error while seeking: %s'%e)
                return 0

            data = self.getEBMLId()

        datasize = self.getDataSize()
        data = self.getEBMLId()

        # Find segment info element (element ID 15 49 A9 66)
        while not self.monitor.abortRequested() and data != 0x1549A966 and self.File.tell() < filesize and data > 0 and datasize > 0:
            datasize = self.getDataSize()

            try:
                self.File.seek(datasize, 1)
            except Exception as e:
                LOG('MKVParser: Error while seeking: %s'%e)
                return 0

            data = self.getEBMLId()

        datasize = self.getDataSize()

        if self.File.tell() < filesize:
            return datasize

        return 0


    def getFileSize(self) -> int:
        """Get the total file size."""
        size = 0
        try:
            pos = self.File.tell()
            self.File.seek(0, 2)
            size = self.File.tell()
            self.File.seek(pos, 0)
        except Exception as e:
            LOG("MKVParser: Error getting file size: %s"%e)
        return size


    def getData(self, datasize: int) -> bytes:
        """Read the specified number of bytes from the file."""
        try:
            data = self.File.readBytes(datasize)
            return data
        except Exception as e:
            LOG("MKVParser: Error reading data: %s"%e)
            return b''


    def getDataSize(self) -> int:
        """Read and parse EBML variable-length integer for data size."""
        try:
            data = self.File.readBytes(1)
            firstbyte = struct.unpack('>B', data)[0]
            datasize = firstbyte
            mask = 0xFFFF
        
            for i in range(8):
                if datasize >> (7 - i) == 1:
                    mask = mask ^ (1 << (7 - i))
                    break

            datasize = datasize & mask
        
            if firstbyte >> 7 != 1:
                for i in range(1, 8):
                    datasize = (datasize << 8) + struct.unpack('>B', self.File.readBytes(1))[0]

                    if firstbyte >> (7 - i) == 1:
                        break
        except Exception as e:
            LOG("MKVParser: Error in getDataSize: %s"%e)
            datasize = 0

        return datasize


    def getEBMLId(self) -> int:
        """Read and parse EBML element ID."""
        try:
            data = self.File.readBytes(1)
            firstbyte = struct.unpack('>B', data)[0]
            ID = firstbyte

            if firstbyte >> 7 != 1:
                for i in range(1, 4):
                    ID = (ID << 8) + struct.unpack('>B', self.File.readBytes(1))[0]

                    if firstbyte >> (7 - i) == 1:
                        break
        except Exception as e:
            LOG("MKVParser: Error in getEBMLId: %s"%e)
            ID = 0
        return ID