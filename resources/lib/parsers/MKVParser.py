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
import traceback

from resources.lib.Globals import *
from resources.lib.FileAccess import FileAccess



class MKVParser:
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('MKVParser: ' + ascii(msg), level)


    def determineLength(self, filename):
        self.log("determineLength " + filename)

        try:
            self.File = FileAccess.open(filename, "rb", None)
        except:
            self.log("Unable to open the file")
            self.log(traceback.format_exc(), xbmc.LOGERROR)
            return

        size = self.findHeader()

        if size == 0:
            self.log('Unable to find the segment info')
            dur = 0
        else:
            dur = self.parseHeader(size)

        self.log("Duration is " + str(dur))
        return dur


    def parseHeader(self, size):
        duration = 0
        timecode = 0
        fileend = self.File.tell() + size
        datasize = 1
        data = 1

        while self.File.tell() < fileend and datasize > 0 and data > 0:
            data = self.getEBMLId()
            datasize = self.getDataSize()

            if data == 0x2ad7b1:
                timecode = 0

                try:
                    for x in range(datasize):
                        timecode = (timecode << 8) + struct.unpack('B', self.getData(1))[0]
                except:
                    timecode = 0

                if duration != 0 and timecode != 0:
                        break
            elif data == 0x4489:
                try:
                    if datasize == 4:
                        duration = int(struct.unpack('>f', self.getData(datasize))[0])
                    else:
                        duration = int(struct.unpack('>d', self.getData(datasize))[0])
                except:
                    self.log("Error getting duration in header, size is " + str(datasize))
                    duration = 0

                if timecode != 0 and duration != 0:
                    break
            else:
                try:
                    self.File.seek(datasize, 1)
                except:
                    self.log('Error while seeking')
                    return 0

        if duration > 0 and timecode > 0:
            dur = (duration * timecode) / 1000000000
            return dur

        return 0


    def findHeader(self):
        self.log("findHeader")
        filesize = self.getFileSize()
        
        if filesize == 0:
            self.log("Empty file")
            return 0

        data = self.getEBMLId()

        # Check for 1A 45 DF A3
        if data != 0x1A45DFA3:
            self.log("Not a proper MKV")
            return 0

        datasize = self.getDataSize()
        
        try:
            self.File.seek(datasize, 1)
        except:
            self.log('Error while seeking')
            return 0

        data = self.getEBMLId()

        # Look for the segment header
        while data != 0x18538067 and self.File.tell() < filesize and data > 0 and datasize > 0:
            datasize = self.getDataSize()

            try:
                self.File.seek(datasize, 1)
            except:
                self.log('Error while seeking')
                return 0

            data = self.getEBMLId()

        datasize = self.getDataSize()
        data = self.getEBMLId()

        # Find segment info
        while data != 0x1549A966 and self.File.tell() < filesize and data > 0 and datasize > 0:
            datasize = self.getDataSize()

            try:
                self.File.seek(datasize, 1)
            except:
                self.log('Error while seeking')
                return 0

            data = self.getEBMLId()

        datasize = self.getDataSize()

        if self.File.tell() < filesize:
            return datasize

        return 0


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


    def getData(self, datasize):
        data = self.File.read(datasize)
        return data


    def getDataSize(self):
        data = self.File.read(1)

        try:
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
                    datasize = (datasize << 8) + struct.unpack('>B', self.File.read(1))[0]
    
                    if firstbyte >> (7 - i) == 1:
                        break
        except:
            datasize = 0

        return datasize


    def getEBMLId(self):
        data = self.File.read(1)

        try:
            firstbyte = struct.unpack('>B', data)[0]
            ID = firstbyte
    
            if firstbyte >> 7 != 1:
                for i in range(1, 4):
                    ID = (ID << 8) + struct.unpack('>B', self.File.read(1))[0]
    
                    if firstbyte >> (7 - i) == 1:
                        break
        except:
            ID = 0

        return ID
