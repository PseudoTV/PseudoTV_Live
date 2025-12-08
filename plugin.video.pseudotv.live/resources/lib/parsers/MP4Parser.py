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
        self.monitor     = MONITOR()


    def determineLength(self, filename: str) -> int:
        log("MP4Parser: determineLength %s" % filename)
        dur = 0
        try:
            self.File = FileAccess.open(filename, "rb", None)
        except Exception as e:
            log("MP4Parser: Unable to open the file: %s" % e, xbmc.LOGERROR)
            return 0
        
        try:
            dur = self.readHeader()
            if not dur:
                log("MP4Parser - Using New Parser (legacy parser returned 0)")
                boxes = self.find_boxes(self.File)
                log("MP4Parser: Found boxes: %s" % list(boxes.keys()))
                
                # Sanity check that this really is a movie file.
                if boxes.get(b"ftyp", [-1])[0] == 0:
                    try:
                        moov_info = boxes.get(b"moov")
                        
                        # Check if moov box exists - it may be at the end of file after mdat
                        if moov_info is None:
                            # moov might be after a large mdat block - scan from end of mdat
                            if b"mdat" in boxes:
                                mdat_end = boxes[b"mdat"][1]
                                log("MP4Parser: moov not found at start, scanning after mdat at offset %s" % mdat_end)
                                # Use separate dict for additional boxes to avoid corrupting main offsets
                                additional_boxes = self.find_boxes(self.File, mdat_end)
                                log("MP4Parser: Additional boxes found: %s" % list(additional_boxes.keys()))
                                moov_info = additional_boxes.get(b"moov")
                        
                        if moov_info is not None:
                            moov_start, moov_end = moov_info
                            log("MP4Parser: moov box found at offset %s-%s" % (moov_start, moov_end))
                            # Use separate dict for moov sub-boxes - these have absolute offsets
                            moov_boxes = self.find_boxes(self.File, moov_start + 8, moov_end)
                            if b"mvhd" in moov_boxes:
                                dur = self.scan_mvhd(self.File, moov_boxes[b"mvhd"][0])
                                log("MP4Parser: mvhd parsed, raw duration = %s" % dur)
                            else:
                                log("MP4Parser: mvhd box not found in moov. Available: %s" % list(moov_boxes.keys()), xbmc.LOGERROR)
                                dur = 0
                        else:
                            log("MP4Parser: moov box not found in file after full scan", xbmc.LOGERROR)
                            dur = 0
                    except Exception as e:
                        log("MP4Parser: New parser failed! %s\nboxes = %s" % (e, boxes), xbmc.LOGERROR)
                        dur = 0
                else:
                    log("MP4Parser: Not a valid MP4 file (ftyp not at position 0)", xbmc.LOGERROR)
                    dur = 0
        except Exception as e:
            log("MP4Parser: determineLength exception: %s" % e, xbmc.LOGERROR)
            dur = 0
        finally:
            try:
                self.File.close()
            except:
                pass
        
        # Validate duration - only reject clearly invalid values
        dur = self._validateDuration(dur, filename)
        log("MP4Parser: Final duration is %s seconds for %s" % (dur, filename))
        return dur


    def _validateDuration(self, duration, filename=""):
        """Validate duration - only reject clearly invalid values (None, negative)"""
        if duration is None:
            log("MP4Parser: Duration is None, returning 0", xbmc.LOGWARNING)
            return 0
        
        if duration < 0:
            log("MP4Parser: Negative duration %s detected for %s, returning 0" % (duration, filename), xbmc.LOGWARNING)
            return 0
        
        # Log warnings for unusual durations but don't reject them
        if duration > 86400 * 7:  # > 7 days
            log("MP4Parser: Very long duration %s for %s - verify file is valid" % (duration, filename), xbmc.LOGWARNING)
        
        # Return duration as-is to preserve fractional seconds
        return duration


    def find_boxes(self, f, start_offset=0, end_offset=float("inf")):
        """Returns a dictionary of all the data boxes and their absolute starting
        and ending offsets inside the mp4 file. Specify a start_offset and end_offset to read sub-boxes."""
        s = struct.Struct("> I 4s")
        boxes  = {}
        offset = start_offset
        last_offset = -1
        max_iterations = 10000  # Prevent infinite loops
        iterations = 0
        
        try:
            f.seek(offset, 0)
        except Exception as e:
            log("MP4Parser: find_boxes seek failed at offset %s: %s" % (offset, e), xbmc.LOGERROR)
            return boxes
        
        while not self.monitor.abortRequested() and offset < end_offset and iterations < max_iterations:
            iterations += 1
            try:
                if last_offset == offset:
                    log("MP4Parser: find_boxes stuck at offset %s, breaking" % offset)
                    break
                last_offset = offset
                
                data = f.readBytes(8)  # read box header
                if data == b"" or len(data) < 8:
                    break  # EOF or incomplete read
                
                length, text = s.unpack(data)
                
                # Handle extended size (length == 1 means 64-bit size follows)
                if length == 1:
                    extended_data = f.readBytes(8)
                    if len(extended_data) < 8:
                        log("MP4Parser: Incomplete extended size read", xbmc.LOGWARNING)
                        break
                    length = struct.unpack(">Q", extended_data)[0]
                    # Seek past the rest of the box (length - 16 because we read 8+8 bytes)
                    if length > 16:
                        f.seek(length - 16, 1)
                elif length == 0:
                    # length == 0 means box extends to EOF
                    log("MP4Parser: Box %s extends to EOF" % text)
                    break
                elif length < 8:
                    log("MP4Parser: Invalid box length %s for %s at offset %s" % (length, text, offset), xbmc.LOGWARNING)
                    break
                else:
                    f.seek(length - 8, 1)  # skip to next box
                
                boxes[text] = (offset, offset + length)
                offset += length
                
            except struct.error as e:
                log("MP4Parser: find_boxes struct error at offset %s: %s" % (offset, e), xbmc.LOGWARNING)
                break
            except Exception as e:
                log("MP4Parser: find_boxes exception at offset %s: %s" % (offset, e), xbmc.LOGWARNING)
                break
        
        if iterations >= max_iterations:
            log("MP4Parser: find_boxes reached max iterations, possible corrupt file", xbmc.LOGWARNING)
        
        return boxes


    def scan_mvhd(self, f, offset):
        """Parse the movie header (mvhd) box to extract duration"""
        try:
            f.seek(offset, 0)
            f.seek(8, 1)  # skip box header
            data = f.readBytes(1)  # read version number
            if not data:
                log("MP4Parser: scan_mvhd - no version data", xbmc.LOGERROR)
                return 0
            
            version = int.from_bytes(data, "big")
            word_size = 8 if version == 1 else 4
            log("MP4Parser: scan_mvhd version=%s, word_size=%s" % (version, word_size))
            
            f.seek(3, 1)  # skip flags
            f.seek(word_size * 2, 1)  # skip dates
            
            timescale_data = f.readBytes(4)
            if len(timescale_data) < 4:
                log("MP4Parser: scan_mvhd - incomplete timescale read", xbmc.LOGERROR)
                return 0
            timescale = int.from_bytes(timescale_data, "big")
            
            if timescale == 0:
                log("MP4Parser: scan_mvhd - timescale is 0, using default 600", xbmc.LOGWARNING)
                timescale = 600
            
            duration_data = f.readBytes(word_size)
            if len(duration_data) < word_size:
                log("MP4Parser: scan_mvhd - incomplete duration read", xbmc.LOGERROR)
                return 0
            raw_duration = int.from_bytes(duration_data, "big")
            
            # Check for special values indicating unknown duration
            max_val = (2 ** (word_size * 8)) - 1
            if raw_duration == max_val:
                log("MP4Parser: scan_mvhd - duration is max value (unknown duration)", xbmc.LOGWARNING)
                return 0
            
            # Return raw float to preserve fractional seconds for short clips
            duration = raw_duration / timescale
            log("MP4Parser: scan_mvhd raw_duration=%s, timescale=%s, calculated=%s seconds" % (raw_duration, timescale, duration))
            
            return duration
        except Exception as e:
            log("MP4Parser: scan_mvhd exception: %s" % e, xbmc.LOGERROR)
            return 0


    def readHeader(self):
        """Legacy header reading method"""
        try:
            data = self.readBlock()

            if data.boxtype != 'ftyp':
                log("MP4Parser: readHeader - No ftyp block, got: %s" % data.boxtype)
                return 0

            # Skip past the file header
            try:
                self.File.seek(data.size, 1)
            except Exception as e:
                log('MP4Parser: readHeader - Error while seeking past ftyp: %s' % e)
                return 0

            data = self.readBlock()
            max_blocks = 1000  # Prevent infinite loop
            block_count = 0

            while not self.monitor.abortRequested() and data.boxtype != 'moov' and data.size > 0 and block_count < max_blocks:
                block_count += 1
                try:
                    self.File.seek(data.size, 1)
                except Exception as e:
                    log('MP4Parser: readHeader - Error while seeking to moov: %s' % e)
                    return 0
                data = self.readBlock()

            if block_count >= max_blocks:
                log("MP4Parser: readHeader - max blocks reached looking for moov", xbmc.LOGWARNING)
                return 0

            if data.boxtype != 'moov':
                log("MP4Parser: readHeader - moov not found, got: %s" % data.boxtype)
                return 0

            data = self.readBlock()
            block_count = 0

            while not self.monitor.abortRequested() and data.boxtype != 'mvhd' and data.size > 0 and block_count < max_blocks:
                block_count += 1
                try:
                    self.File.seek(data.size, 1)
                except Exception as e:
                    log('MP4Parser: readHeader - Error while seeking to mvhd: %s' % e)
                    return 0
                data = self.readBlock()

            if block_count >= max_blocks:
                log("MP4Parser: readHeader - max blocks reached looking for mvhd", xbmc.LOGWARNING)
                return 0

            self.readMovieHeader()

            if self.MovieHeader.scale > 0 and self.MovieHeader.duration > 0:
                # Return raw float to preserve fractional seconds for short clips
                duration = self.MovieHeader.duration / self.MovieHeader.scale
                log("MP4Parser: readHeader - duration=%s, scale=%s, calculated=%s" % (self.MovieHeader.duration, self.MovieHeader.scale, duration))
                return duration

            log("MP4Parser: readHeader - invalid scale (%s) or duration (%s)" % (self.MovieHeader.scale, self.MovieHeader.duration))
            return 0
        except Exception as e:
            log("MP4Parser: readHeader exception: %s" % e, xbmc.LOGERROR)
            return 0


    def readMovieHeader(self):
        """Read movie header data"""
        try:
            self.MovieHeader.version = struct.unpack('>b', self.File.readBytes(1))[0]
            self.File.read(3)   # skip flags for now
    
            if self.MovieHeader.version == 1:
                data = struct.unpack('>QQIQQ', self.File.readBytes(36))
            else:
                data = struct.unpack('>IIIII', self.File.readBytes(20))

            self.MovieHeader.created = data[0]
            self.MovieHeader.modified = data[1]
            self.MovieHeader.scale = data[2]
            self.MovieHeader.duration = data[3]
            
            log("MP4Parser: readMovieHeader - version=%s, scale=%s, duration=%s" % (self.MovieHeader.version, self.MovieHeader.scale, self.MovieHeader.duration))
        except Exception as e:
            log("MP4Parser: readMovieHeader exception: %s" % e, xbmc.LOGERROR)
            self.MovieHeader.duration = 0
            self.MovieHeader.scale = 0


    def readBlock(self):
        """Read a single MP4 box/atom header"""
        box = MP4DataBlock()
        
        try:
            data = self.File.readBytes(4)
            if len(data) < 4:
                return box
            
            box.size = struct.unpack('>I', data)[0]
            boxtype_data = self.File.read(4)
            box.boxtype = boxtype_data.decode('latin-1') if isinstance(boxtype_data, bytes) else boxtype_data
    
            if box.size == 1:
                # Extended size
                extended = self.File.readBytes(8)
                if len(extended) < 8:
                    box.size = -1
                    return box
                box.size = struct.unpack('>q', extended)[0]
                box.size -= 8
            elif box.size == 0:
                # Box extends to EOF - we can't handle this in legacy parser
                box.size = -1
                return box
            
            box.size -= 8
    
            if box.boxtype == 'uuid':
                uuid_data = self.File.read(16)
                box.boxtype = uuid_data.decode('latin-1') if isinstance(uuid_data, bytes) else uuid_data
                box.size -= 16
        except Exception as e:
            log("MP4Parser: readBlock exception: %s" % e, xbmc.LOGWARNING)
            box.size = -1

        return box
