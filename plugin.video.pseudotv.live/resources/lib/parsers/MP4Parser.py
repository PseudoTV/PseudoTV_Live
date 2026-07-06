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

class MP4DataBlock:
    def __init__(self):
        self.size    = -1
        self.boxtype = ''
        self.data    = ''


class MP4MovieHeader:
    def __init__(self):
        self.version  = 0
        self.flags    = 0
        self.created  = 0
        self.modified = 0
        self.scale    = 0
        self.duration = 0

class MP4Parser:
    def __init__(self):
        self.monitor = MONITOR()
        self.MovieHeader = MP4MovieHeader()


    def determineLength(self, filename: str) -> int:
        """Determine the duration of an MP4 file in seconds.
        
        Args:
            filename (str): Path to the MP4 file
            
        Returns:
            int: Duration in seconds, or 0 if unable to determine
        """
        LOG("MP4Parser: determineLength %s"%filename)
        try:
            self.File = FileAccess.open(filename, "rb", None)
        except Exception as e:
            LOG("MP4Parser: Unable to open the file: %s"%str(e))
            return 0
            
        dur = self.readHeader()
        if not dur:
            LOG("MP4Parser - Using New Parser")
            try:
                boxes = self.find_boxes(self.File)
                
                # Check for required boxes
                if b"moov" not in boxes:
                    LOG("MP4Parser: Missing required 'moov' box")
                    self.File.close()
                    return 0
                
                if b"ftyp" not in boxes:
                    LOG("MP4Parser: Missing required 'ftyp' box")
                    self.File.close()
                    return 0
                
                moov_boxes = self.find_boxes(self.File, boxes[b"moov"][0] + 8, boxes[b"moov"][1])
                
                # Try to get duration from mvhd (primary method)
                if b"mvhd" in moov_boxes:
                    dur = self.scan_mvhd(self.File, moov_boxes[b"mvhd"][0])
                    if dur > 0:
                        LOG("MP4Parser: Got duration from mvhd: %s seconds"%dur)
                else:
                    LOG("MP4Parser: Missing 'mvhd' box in moov, trying fallback")
                
                # If mvhd failed, try fallback from trak boxes
                if not dur and b"trak" in moov_boxes:
                    LOG("MP4Parser: Trying fallback duration detection from trak boxes")
                    dur = self.get_track_duration(self.File, moov_boxes)
                    if dur > 0:
                        LOG("MP4Parser: Got duration from trak boxes: %s seconds"%dur)
                
                if not dur:
                    LOG("MP4Parser: All duration detection methods failed")
                
            except Exception as e:
                LOG("MP4Parser, failed! %s"%str(e), xbmc.LOGERROR)
                dur = 0
                
        self.File.close()
        LOG("MP4Parser: Duration is %s"%(dur))
        return dur


    def find_boxes(self, f, start_offset=0, end_offset=float("inf")):
        """Returns a dictionary of all the data boxes and their absolute starting
        and ending offsets inside the mp4 file. Specify a start_offset and end_offset to read sub-boxes.
        
        Args:
            f: File object to read from
            start_offset (int): Starting byte offset (default: 0)
            end_offset (float): Ending byte offset (default: infinity)
            
        Returns:
            dict: Dictionary mapping box types (bytes) to tuples of (start_offset, end_offset)
        """
        s = struct.Struct("> I 4s")
        boxes  = {}
        offset = start_offset
        last_offset = -1
        
        try:
            f.seek(offset, 0)
        except Exception as e:
            LOG("MP4Parser: Error seeking to offset %s: %s"%(offset, str(e)))
            return boxes
        
        while not self.monitor.abortRequested() and offset < end_offset:
            try:
                if last_offset == offset:
                    break
                else:
                    last_offset = offset
                
                data = f.readBytes(8)  # read box header
                if not data or len(data) < 8:
                    break  # EOF or incomplete header
                
                length, text = s.unpack(data)
                
                # Validate box size (must be at least 8 bytes, max 2GB)
                if length < 8 or length > 2147483648:
                    LOG("MP4Parser: Invalid box size: %s at offset %s"%(length, offset))
                    break
                
                # Skip to next box
                try:
                    f.seek(length - 8, 1)
                except Exception as e:
                    LOG("MP4Parser: Error seeking in box: %s"%str(e))
                    break
                
                boxes[text] = (offset, offset + length)
                offset += length
                
            except Exception as e:
                LOG("MP4Parser: Error reading box at offset %s: %s"%(offset, str(e)))
                break
                
        return boxes


    def scan_mvhd(self, f, offset):
        """Parse the Movie Header (mvhd) box to extract duration.
        
        Args:
            f: File object to read from
            offset (int): Byte offset of the mvhd box
            
        Returns:
            int: Duration in seconds, or 0 if unable to determine
        """
        try:
            f.seek(offset, 0)
            f.seek(8, 1)  # skip box header (size + type)
            
            # Read and validate version
            version_data = f.readBytes(1)
            if not version_data or len(version_data) < 1:
                LOG("MP4Parser: Unable to read mvhd version")
                return 0
            
            version = int.from_bytes(version_data, "big")
            word_size = 8 if version == 1 else 4
            
            f.seek(3, 1)  # skip flags
            f.seek(word_size * 2, 1)  # skip creation and modification time
            
            # Read and validate timescale
            timescale_data = f.readBytes(4)
            if not timescale_data or len(timescale_data) < 4:
                LOG("MP4Parser: Unable to read timescale")
                return 0
            
            timescale = int.from_bytes(timescale_data, "big")
            if timescale <= 0:
                LOG("MP4Parser: Invalid timescale: %s, using default 1000"%timescale)
                timescale = 1000
            
            # Read and validate duration
            duration_data = f.readBytes(word_size)
            if not duration_data or len(duration_data) < word_size:
                LOG("MP4Parser: Unable to read duration")
                return 0
            
            duration = int.from_bytes(duration_data, "big")
            calculated_duration = round(duration / timescale)
            
            # Sanity check
            if calculated_duration <= 0:
                LOG("MP4Parser: Invalid duration calculated: %s / %s = %s"%(duration, timescale, calculated_duration))
                return 0
            
            LOG("MP4Parser: Calculated duration from mvhd: %s seconds"%calculated_duration)
            return calculated_duration
            
        except Exception as e:
            LOG("MP4Parser: Error scanning mvhd at offset %s: %s"%(offset, str(e)), xbmc.LOGERROR)
            return 0


    def get_track_duration(self, f, moov_boxes):
        """Fallback method to get duration from track (trak) boxes.
        
        This method is used when mvhd box is missing or fails to provide duration.
        It reads the track header (tkhd) to extract duration information.
        
        Args:
            f: File object to read from
            moov_boxes (dict): Dictionary of boxes within moov from find_boxes()
            
        Returns:
            int: Duration in seconds, or 0 if unable to determine
        """
        try:
            if b"trak" not in moov_boxes:
                LOG("MP4Parser: No trak box found for fallback duration detection")
                return 0
            
            trak_offset, trak_end = moov_boxes[b"trak"]
            LOG("MP4Parser: Reading trak box at offset %s-%s"%(trak_offset, trak_end))
            
            # Parse trak box to find tkhd
            trak_boxes = self.find_boxes(f, trak_offset + 8, trak_end)
            
            if b"tkhd" not in trak_boxes:
                LOG("MP4Parser: No tkhd box found in trak")
                return 0
            
            tkhd_offset = trak_boxes[b"tkhd"][0]
            duration = self.scan_tkhd(f, tkhd_offset)
            
            if duration > 0:
                LOG("MP4Parser: Successfully got duration from tkhd: %s seconds"%duration)
                return duration
            
            return 0
            
        except Exception as e:
            LOG("MP4Parser: Error in get_track_duration: %s"%str(e), xbmc.LOGERROR)
            return 0


    def scan_tkhd(self, f, offset):
        """Parse the Track Header (tkhd) box to extract duration.
        
        The tkhd box contains track-specific information including duration.
        Duration in tkhd is in the same timescale as mvhd.
        
        Args:
            f: File object to read from
            offset (int): Byte offset of the tkhd box
            
        Returns:
            int: Duration in seconds, or 0 if unable to determine
        """
        try:
            f.seek(offset, 0)
            f.seek(8, 1)  # skip box header (size + type)
            
            # Read and validate version
            version_data = f.readBytes(1)
            if not version_data or len(version_data) < 1:
                LOG("MP4Parser: Unable to read tkhd version")
                return 0
            
            version = int.from_bytes(version_data, "big")
            word_size = 8 if version == 1 else 4
            
            f.seek(3, 1)  # skip flags
            f.seek(word_size * 2, 1)  # skip creation and modification time
            f.seek(4, 1)  # skip track ID
            f.seek(4, 1)  # skip reserved
            
            # Read duration from tkhd
            duration_data = f.readBytes(word_size)
            if not duration_data or len(duration_data) < word_size:
                LOG("MP4Parser: Unable to read tkhd duration")
                return 0
            
            duration = int.from_bytes(duration_data, "big")
            
            if duration <= 0:
                LOG("MP4Parser: Invalid tkhd duration: %s"%duration)
                return 0
            
            # Note: tkhd duration is also in timescale units, but we need to convert it
            # For now, return the duration value - it may need timescale conversion
            LOG("MP4Parser: Got tkhd duration value: %s"%duration)
            return duration
            
        except Exception as e:
            LOG("MP4Parser: Error scanning tkhd at offset %s: %s"%(offset, str(e)), xbmc.LOGERROR)
            return 0


    def readHeader(self):
        """Legacy header reading method for backward compatibility.
        
        Returns:
            int: Duration in seconds, or 0 if unable to determine
        """
        data = self.readBlock()

        if data.boxtype != 'ftyp':
            LOG("MP4Parser: No ftyp block found")
            return 0

        # Skip past the file header
        try:
            self.File.seek(data.size, 1)
        except Exception as e:
            LOG('MP4Parser: Error while seeking past ftyp: %s'%str(e))
            return 0

        data = self.readBlock()

        while not self.monitor.abortRequested() and data.boxtype != 'moov' and data.size > 0:
            try:
                self.File.seek(data.size, 1)
            except Exception as e:
                LOG('MP4Parser: Error while seeking: %s'%str(e))
                return 0

            data = self.readBlock()

        data = self.readBlock()

        while not self.monitor.abortRequested() and data.boxtype != 'mvhd' and data.size > 0:
            try:
                self.File.seek(data.size, 1)
            except Exception as e:
                LOG('MP4Parser: Error while seeking: %s'%str(e))
                return 0

            data = self.readBlock()

        self.readMovieHeader()

        if self.MovieHeader.scale > 0 and self.MovieHeader.duration > 0:
            return int(self.MovieHeader.duration / self.MovieHeader.scale)

        return 0


    def readMovieHeader(self):
        """Parse the movie header to extract duration and timescale.
        
        Updates self.MovieHeader with parsed values.
        """
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
            
            LOG("MP4Parser: MovieHeader - version:%s, scale:%s, duration:%s"%(self.MovieHeader.version, self.MovieHeader.scale, self.MovieHeader.duration))
            
        except Exception as e:
            LOG("MP4Parser: Error reading movie header: %s"%str(e), xbmc.LOGERROR)
            self.MovieHeader.duration = 0


    def readBlock(self):
        """Read an MP4 box header.
        
        Returns:
            MP4DataBlock: Box with size, boxtype, and data information
        """
        box = MP4DataBlock()
        
        try:
            data = self.File.readBytes(4)
            if not data or len(data) < 4:
                return box
            
            box.size = struct.unpack('>I', data)[0]
            box_type_data = self.File.read(4)
            if not box_type_data or len(box_type_data) < 4:
                return box
                
            box.boxtype = box_type_data
    
            if box.size == 1:
                # Extended size
                extended_size_data = self.File.readBytes(8)
                if not extended_size_data or len(extended_size_data) < 8:
                    return box
                    
                box.size = struct.unpack('>q', extended_size_data)[0]
                box.size -= 8
            
            box.size -= 8
    
            if box.boxtype == b'uuid':
                uuid_data = self.File.read(16)
                if uuid_data and len(uuid_data) == 16:
                    box.boxtype = uuid_data
                    box.size -= 16
                    
        except Exception as e:
            LOG("MP4Parser: Error reading block: %s"%str(e))
            pass

        return box