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
from typing import Any, Optional, Union
import struct

class FLVTagHeader:
    def __init__(self):
        self.tagtype = 0
        self.datasize = 0
        self.timestamp = 0
        self.timestampext = 0
        
    def readHeader(self, thefile: Any):
        try:
            data = struct.unpack('B', thefile.readBytes(1))[0]
            self.tagtype = (data & 0x1F)
            self.datasize = struct.unpack('>H', thefile.readBytes(2))[0]
            data = struct.unpack('>B', thefile.readBytes(1))[0]
            self.datasize = (self.datasize << 8) | data
            self.timestamp = struct.unpack('>H', thefile.readBytes(2))[0]
            data = struct.unpack('>B', thefile.readBytes(1))[0]
            self.timestamp = (self.timestamp << 8) | data
            self.timestampext = struct.unpack('>B', thefile.readBytes(1))[0]
        except Exception as e:
            LOG("FLVTagHeader: Error reading header: %s"%e)
            self.tagtype = 0
            self.datasize = 0
            self.timestamp = 0
            self.timestampext = 0


class FLVParser:
    """
    Parser for FLV (Flash Video) files.
    Duration is extracted from the last video tag timestamp.
    """

    def __init__(self):
        self.monitor = MONITOR()    
    
    def determineLength(self, filename: str) -> Union[int, float]:
        """
        Determines video length from FLV file.
        Returns duration in seconds.
        """
        LOG("FLVParser: determineLength, [%s]"%filename)

        try: 
            self.File = FileAccess.open(filename, "rb", None)
        except IOError as e:
            LOG("FLVParser: determineLength, unable to open the file, failed!\n%s"%e)
            return 0

        try:
            if self.verifyFLV() == False:
                LOG("FLVParser: determineLength, not a valid FLV")
                return 0

            tagheader = self.findLastVideoTag()

            if tagheader is None:
                LOG("FLVParser: determineLength, unable to find a video tag")
                return 0

            dur = int(self.getDurFromTag(tagheader))
            LOG("FLVParser: determineLength, duration = %s seconds"%(dur))
            return dur
        except Exception as e:
            LOG("FLVParser: determineLength, failed!\n%s"%e)
            return 0
        finally:
            try:
                self.File.close()
            except Exception as e:
                LOG('FLVParser: File.close, failed!\n%s' % e, xbmc.LOGDEBUG)


    def verifyFLV(self) -> bool:
        """Verify the file is a valid FLV by checking file signature."""
        try:
            data = self.File.read(3)
            return data == b'FLV' or data == 'FLV'
        except Exception as e:
            LOG('FLVParser: verifyFLV, failed!\n%s' % e, xbmc.LOGDEBUG)
            return False


    def findLastVideoTag(self) -> Optional[FLVTagHeader]:
        """Find the last video tag in the FLV file to determine duration."""
        try:
            self.File.seek(0, 2)
            curloc = self.File.tell()
        except Exception as e:
            LOG("FLVParser: findLastVideoTag, failed!\n%s"%e)
            return None

        # Go through a limited amount of the file before quitting
        maximum = curloc - (2 * 1024 * 1024)

        if maximum < 0:
            maximum = 8

        while not self.monitor.abortRequested() and curloc > maximum:
            try:
                self.File.seek(-4, 1)
                data = int(struct.unpack('>I', self.File.readBytes(4))[0])

                if data < 1:
                    LOG('FLVParser: findLastVideoTag, invalid packet data')
                    return None

                if curloc - data <= 0:
                    LOG('FLVParser: findLastVideoTag, no video packet found')
                    return None

                self.File.seek(-4 - data, 1)
                curloc = curloc - data
                tag = FLVTagHeader()
                tag.readHeader(self.File)

                if tag.datasize <= 0:
                    LOG('FLVParser: findLastVideoTag, invalid packet header')
                    return None

                if curloc - 8 <= 0:
                    LOG('FLVParser: findLastVideoTag, no video packet found')
                    return None

                self.File.seek(-8, 1)
                LOG("FLVParser: findLastVideoTag, detected tag type %s"%(tag.tagtype))
                curloc = self.File.tell()

                if tag.tagtype == 9:  # Video tag type
                    return tag
            except Exception as e:
                LOG('FLVParser: findLastVideoTag, failed!\n%s'%e)
                return None

        return None


    def getDurFromTag(self, tag: FLVTagHeader) -> int:
        """
        Convert FLV tag timestamp to duration in seconds.
        FLV timestamps are in milliseconds.
        """
        tottime = tag.timestamp | (tag.timestampext << 24)
        tottime = int(tottime / 1000)  # Convert from milliseconds to seconds
        return tottime