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

from resources.lib.Globals import *
from resources.lib.FileAccess import FileAccess


class MP4DataBlock:
    def __init__(self):
        self.size = -1
        self.boxtype = ''
        self.data = ''


class MP4MovieHeader:
    def __init__(self):
        self.version = 0
        self.flags = 0
        self.created = 0
        self.modified = 0
        self.scale = 0
        self.duration = 0


class MP4Parser:
    def __init__(self):
        self.MovieHeader = MP4MovieHeader()


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('MP4Parser: ' + ascii(msg), level)


    def determineLength(self, filename):
        self.log("determineLength " + filename)

        try:
            self.File = FileAccess.open(filename, "rb", None)
        except:
            self.log("Unable to open the file")
            return

        dur = self.readHeader()
        self.File.close()
        self.log("Duration: " + str(dur))
        return dur


    def readHeader(self):
        data = self.readBlock()

        if data.boxtype != 'ftyp':
            self.log("No file block")
            return 0

        # Skip past the file header
        try:
            self.File.seek(data.size, 1)
        except:
            self.log('Error while seeking')
            return 0

        data = self.readBlock()

        while data.boxtype != 'moov' and data.size > 0:
            try:
                self.File.seek(data.size, 1)
            except:
                self.log('Error while seeking')
                return 0

            data = self.readBlock()

        data = self.readBlock()

        while data.boxtype != 'mvhd' and data.size > 0:
            try:
                self.File.seek(data.size, 1)
            except:
                self.log('Error while seeking')
                return 0

            data = self.readBlock()

        self.readMovieHeader()

        if self.MovieHeader.scale > 0 and self.MovieHeader.duration > 0:
            return int(self.MovieHeader.duration / self.MovieHeader.scale)

        return 0


    def readMovieHeader(self):
        try:
            self.MovieHeader.version = struct.unpack('>b', self.File.read(1))[0]
            self.File.read(3)   #skip flags for now
    
            if self.MovieHeader.version == 1:
                data = struct.unpack('>QQIQQ', self.File.read(36))
            else:
                data = struct.unpack('>IIIII', self.File.read(20))

            self.MovieHeader.created = data[0]
            self.MovieHeader.modified = data[1]
            self.MovieHeader.scale = data[2]
            self.MovieHeader.duration = data[3]
        except:
            self.MovieHeader.duration = 0


    def readBlock(self):
        box = MP4DataBlock()
        
        try:
            data = self.File.read(4)
            box.size = struct.unpack('>I', data)[0]
            box.boxtype = self.File.read(4)
    
            if box.size == 1:
                box.size = struct.unpack('>q', self.File.read(8))[0]
                box.size -= 8
    
            box.size -= 8
    
            if box.boxtype == 'uuid':
                box.boxtype = self.File.read(16)
                box.size -= 16
        except:
            pass

        return box