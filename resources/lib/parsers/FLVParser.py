#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc
import os, struct

from resources.lib.Globals import ascii
from resources.lib.FileAccess import FileAccess



class FLVTagHeader:
    def __init__(self):
        self.tagtype = 0
        self.datasize = 0
        self.timestamp = 0
        self.timestampext = 0


    def readHeader(self, thefile):
        try:
            data = struct.unpack('B', thefile.read(1))[0]
            self.tagtype = (data & 0x1F)
            self.datasize = struct.unpack('>H', thefile.read(2))[0]
            data = struct.unpack('>B', thefile.read(1))[0]
            self.datasize = (self.datasize << 8) | data
            self.timestamp = struct.unpack('>H', thefile.read(2))[0]
            data = struct.unpack('>B', thefile.read(1))[0]
            self.timestamp = (self.timestamp << 8) | data
            self.timestampext = struct.unpack('>B', thefile.read(1))[0]
        except:
            self.tagtype = 0
            self.datasize = 0
            self.timestamp = 0
            self.timestampext = 0



class FLVParser:
    def log(self, msg, level = xbmc.LOGDEBUG):
        xbmc.log('FLVParser: ' + ascii(msg), level)


    def determineLength(self, filename):
        self.log("determineLength " + filename)

        try:
            self.File = FileAccess.open(filename, "rb", None)
        except:
            self.log("Unable to open the file")
            return

        if self.verifyFLV() == False:
            self.log("Not a valid FLV")
            self.File.close()
            return 0

        tagheader = self.findLastVideoTag()

        if tagheader is None:
            self.log("Unable to find a video tag")
            self.File.close()
            return 0

        dur = self.getDurFromTag(tagheader)
        self.File.close()
        self.log("Duration: " + str(dur))
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
            self.log("Exception seeking in findLastVideoTag")
            return None

        # Go through a limited amount of the file before quiting
        maximum = curloc - (2 * 1024 * 1024)

        if maximum < 0:
            maximum = 8

        while curloc > maximum:
            try:
                self.File.seek(-4, 1)
                data = int(struct.unpack('>I', self.File.read(4))[0])

                if data < 1:
                    self.log('Invalid packet data')
                    return None

                if curloc - data <= 0:
                    self.log('No video packet found')
                    return None

                self.File.seek(-4 - data, 1)
                curloc = curloc - data
                tag = FLVTagHeader()
                tag.readHeader(self.File)

                if tag.datasize <= 0:
                    self.log('Invalid packet header')
                    return None

                if curloc - 8 <= 0:
                    self.log('No video packet found')
                    return None

                self.File.seek(-8, 1)
                self.log("detected tag type " + str(tag.tagtype))
                curloc = self.File.tell()

                if tag.tagtype == 9:
                    return tag
            except:
                self.log('Exception in findLastVideoTag')
                return None

        return None


    def getDurFromTag(self, tag):
        tottime = tag.timestamp | (tag.timestampext << 24)
        tottime = int(tottime / 1000)
        return tottime
