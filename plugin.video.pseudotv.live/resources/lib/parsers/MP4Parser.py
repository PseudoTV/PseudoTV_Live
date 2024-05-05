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

from globals     import *

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


    def determineLength(self, filename):
        log("MP4Parser: determineLength " + filename)
        try: self.File = FileAccess.open(filename, "rb", None)
        except:
            log("MP4Parser: Unable to open the file")
            return
            
        dur = self.readHeader()
        if not dur:
            log("MP4Parser - Using New Parser")
            boxes = self.find_boxes(self.File)
            # Sanity check that this really is a movie file.
            if (boxes.get(b"ftyp",[-1])[0] == 0):
                try:
                    moov_boxes = self.find_boxes(self.File, boxes[b"moov"][0] + 8, boxes[b"moov"][1])
                    trak_boxes = self.find_boxes(self.File, moov_boxes[b"trak"][0] + 8, moov_boxes[b"trak"][1])
                    udta_boxes = self.find_boxes(self.File, moov_boxes[b"udta"][0] + 8, moov_boxes[b"udta"][1])
                    dur = self.scan_mvhd(self.File, moov_boxes[b"mvhd"][0])
                except Exception as e:
                    log("MP4Parser, failed! %s\nboxes = %s"%(e,boxes), xbmc.LOGERROR)
                    dur = 0
        self.File.close()
        log("MP4Parser: Duration is %s"%(dur))
        return dur


    def find_boxes(self, f, start_offset=0, end_offset=float("inf")):
        """Returns a dictionary of all the data boxes and their absolute starting
        and ending offsets inside the mp4 file. Specify a start_offset and end_offset to read sub-boxes."""
        s = struct.Struct("> I 4s")
        boxes  = {}
        offset = start_offset
        last_offset = -1
        f.seek(offset, 0)
        while not MONITOR.abortRequested() and offset < end_offset:
            if last_offset == offset: break
            else: last_offset = offset
            data = f.readBytes(8)  # read box header
            if data == b"": break  # EOF
            length, text = s.unpack(data)
            f.seek(length - 8, 1)  # skip to next box
            boxes[text] = (offset, offset + length)
            offset += length
        return boxes


    def scan_mvhd(self, f, offset):
        f.seek(offset, 0)
        f.seek(8, 1)  # skip box header
        data = f.readBytes(1)  # read version number
        version = int.from_bytes(data, "big")
        word_size = 8 if version == 1 else 4
        f.seek(3, 1)  # skip flags
        f.seek(word_size * 2, 1)  # skip dates
        timescale = int.from_bytes(f.readBytes(4), "big")
        if timescale == 0: timescale = 600
        duration = int.from_bytes(f.readBytes(word_size), "big")
        duration = round(duration / timescale)
        return duration


    def readHeader(self):
        data = self.readBlock()

        if data.boxtype != 'ftyp':
            log("MP4Parser: No file block")
            return 0

        # Skip past the file header
        try:
            self.File.seek(data.size, 1)
        except:
            log('MP4Parser: Error while seeking')
            return 0

        data = self.readBlock()

        while not MONITOR.abortRequested() and data.boxtype != 'moov' and data.size > 0:
            try:
                self.File.seek(data.size, 1)
            except:
                log('MP4Parser: Error while seeking')
                return 0

            data = self.readBlock()

        data = self.readBlock()

        while not MONITOR.abortRequested() and data.boxtype != 'mvhd' and data.size > 0:
            try:
                self.File.seek(data.size, 1)
            except:
                log('MP4Parser: Error while seeking')
                return 0

            data = self.readBlock()

        self.readMovieHeader()

        if self.MovieHeader.scale > 0 and self.MovieHeader.duration > 0:
            return int(self.MovieHeader.duration / self.MovieHeader.scale)

        return 0


    def readMovieHeader(self):
        try:
            self.MovieHeader.version = struct.unpack('>b', self.File.readBytes(1))[0]
            self.File.read(3)   #skip flags for now
    
            if self.MovieHeader.version == 1:
                data = struct.unpack('>QQIQQ', self.File.readBytes(36))
            else:
                data = struct.unpack('>IIIII', self.File.readBytes(20))

            self.MovieHeader.created = data[0]
            self.MovieHeader.modified = data[1]
            self.MovieHeader.scale = data[2]
            self.MovieHeader.duration = data[3]
        except:
            self.MovieHeader.duration = 0


    def readBlock(self):
        box = MP4DataBlock()
        
        try:
            data = self.File.readBytes(4)
            box.size = struct.unpack('>I', data)[0]
            box.boxtype = self.File.read(4)
    
            if box.size == 1:
                box.size = struct.unpack('>q', self.File.readBytes(8))[0]
                box.size -= 8
            box.size -= 8
    
            if box.boxtype == 'uuid':
                box.boxtype = self.File.read(16)
                box.size -= 16
        except:
            pass

        return box