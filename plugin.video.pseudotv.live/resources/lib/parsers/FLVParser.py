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

class FLVTagHeader:
    def __init__(self):
        self.tagtype = 0
        self.datasize = 0
        self.timestamp = 0
        self.timestampext = 0


    def readHeader(self, thefile):
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
        except:
            self.tagtype = 0
            self.datasize = 0
            self.timestamp = 0
            self.timestampext = 0



class FLVParser:
    def __init__(self):
        self.monitor = MONITOR()    
    
    
    def determineLength(self, filename: str) -> int and float:
        log("FLVParser: determineLength %s"%filename)

        try: self.File = FileAccess.open(filename, "rb", None)
        except:
            log("FLVParser: Unable to open the file")
            return 0

        if self.verifyFLV() == False:
            log("FLVParser: Not a valid FLV")
            self.File.close()
            return 0

        tagheader = self.findLastVideoTag()

        if tagheader is None:
            log("FLVParser: Unable to find a video tag")
            self.File.close()
            return 0

        dur = int(self.getDurFromTag(tagheader))
        self.File.close()
        log("FLVParser: Duration is %s"%(dur))
        return dur


    def verifyFLV(self):
        data = self.File.read(3)

        if data != 'FLV':
            return False

        return True


    def findLastVideoTag(self):
        try:
            self.File.seek(0, 2)
            curloc = self.File.tell()
        except:
            log("FLVParser: Exception seeking in findLastVideoTag")
            return None

        # Go through a limited amount of the file before quiting
        maximum = curloc - (2 * 1024 * 1024)

        if maximum < 0:
            maximum = 8

        while not self.monitor.abortRequested() and curloc > maximum:
            try:
                self.File.seek(-4, 1)
                data = int(struct.unpack('>I', self.File.readBytes(4))[0])

                if data < 1:
                    log('FLVParser: Invalid packet data')
                    return None

                if curloc - data <= 0:
                    log('FLVParser: No video packet found')
                    return None

                self.File.seek(-4 - data, 1)
                curloc = curloc - data
                tag = FLVTagHeader()
                tag.readHeader(self.File)

                if tag.datasize <= 0:
                    log('FLVParser: Invalid packet header')
                    return None

                if curloc - 8 <= 0:
                    log('FLVParser: No video packet found')
                    return None

                self.File.seek(-8, 1)
                log("FLVParser: detected tag type %s"%(tag.tagtype))
                curloc = self.File.tell()

                if tag.tagtype == 9:
                    return tag
            except:
                log('FLVParser: Exception in findLastVideoTag')
                return None

        return None


    def getDurFromTag(self, tag):
        tottime = tag.timestamp | (tag.timestampext << 24)
        tottime = int(tottime / 1000)
        return tottime
