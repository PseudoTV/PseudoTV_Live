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

from variables    import *
from typing import Any, Optional, Union
import struct

class AVIChunk:
    def __init__(self):
        self.empty()

    def empty(self) -> None:
        self.size = 0
        self.fourcc = ''
        self.datatype = 1
        self.chunk = ''

    def read(self, thefile: Any):
        data = thefile.readBytes(4)
        try:    
            self.size = struct.unpack('<i', data)[0]
        except Exception as e: 
            LOG('AVIParser: struct.unpack failed: %s' % e, xbmc.LOGDEBUG)
            self.size = 0
        # Putting an upper limit on the chunk size, in case the file is corrupt
        if self.size > 0 and self.size < 10000: 
            self.chunk = thefile.readBytes(self.size)
        else:
            self.chunk = ''
            self.size = 0


class AVIList:
    def __init__(self):
        self.empty()

    def empty(self) -> None:
        self.size = 0
        self.fourcc = ''
        self.datatype = 2

    def read(self, thefile: Any):
        data = thefile.readBytes(4)
        try:    
            self.size = struct.unpack('<i', data)[0]
        except Exception as e: 
            LOG('AVIParser: ListChunk.struct.unpack failed: %s' % e, xbmc.LOGDEBUG)
            self.size = 0
        self.fourcc = thefile.read(4)


class AVIHeader:
    def __init__(self):
        self.empty()

    def empty(self) -> None:
        self.dwMicroSecPerFrame = 0
        self.dwMaxBytesPerSec = 0
        self.dwPaddingGranularity = 0
        self.dwFlags = 0
        self.dwTotalFrames = 0
        self.dwInitialFrames = 0
        self.dwStreams = 0
        self.dwSuggestedBufferSize = 0
        self.dwWidth = 0
        self.dwHeight = 0


class AVIStreamHeader:
    def __init__(self):
        self.empty()

    def empty(self) -> None:
        self.fccType = ''
        self.fccHandler = ''
        self.dwFlags = 0
        self.wPriority = 0
        self.wLanguage = 0
        self.dwInitialFrame = 0
        self.dwScale = 0
        self.dwRate = 0
        self.dwStart = 0
        self.dwLength = 0
        self.dwSuggestedBuffer = 0
        self.dwQuality = 0
        self.dwSampleSize = 0
        self.rcFrame = ''


class AVIParser:
    """
    Parser for AVI video files.
    Duration is calculated from stream header information.
    """
    def __init__(self):
        self.Header = AVIHeader()
        self.StreamHeader = AVIStreamHeader()

    def determineLength(self, filename: str) -> Union[int, float]:
        """
        Determines video length from AVI file.
        Returns duration in seconds.
        """
        LOG("AVIParser: determineLength %s"%filename)

        try: 
            self.File = FileAccess.open(filename, "rb", None)
        except IOError as e:
            LOG("AVIParser: Unable to open the file: %s"%e)
            return 0

        try:
            dur = int(self.readHeader())
            LOG('AVIParser: Duration is %s seconds'%(dur))
            return dur
        except Exception as e:
            LOG("AVIParser: Error reading header: %s"%e)
            return 0
        finally:
            try:
                self.File.close()
            except Exception as e:
                LOG('AVIParser: File.close failed: %s' % e, xbmc.LOGDEBUG)

    def readHeader(self) -> int:
        # AVI Chunk
        data = self.getChunkOrList()
        
        if data.datatype != 2:
            LOG("AVIParser: Not an avi")
            return 0
        
        if data.fourcc[0:4] != "AVI ":
            LOG("AVIParser: Wrong FourCC")
            return 0

        # Header List
        data = self.getChunkOrList()
        if data.fourcc != "hdrl":
            LOG("AVIParser: Header not found")
            return 0

        # Header chunk
        data = self.getChunkOrList()

        if data.fourcc != 'avih':
            LOG('Header chunk not found')
            return 0

        self.parseHeader(data)
        # Stream list
        data = self.getChunkOrList()

        if self.Header.dwStreams > 10:
            self.Header.dwStreams = 10

        for i in range(self.Header.dwStreams):
            if data.datatype != 2:
                LOG("AVIParser: Unable to find streams")
                return 0

            listsize = data.size
            # Stream chunk number 1, the stream header
            data = self.getChunkOrList()

            if data.datatype != 1:
                LOG("AVIParser: Broken stream header")
                return 0

            self.StreamHeader.empty()
            self.parseStreamHeader(data)

            # If this is the video header, determine the duration
            if self.StreamHeader.fccType == 'vids':
                return self.getStreamDuration()

            # If this isn't the video header, skip through the rest of these
            # stream chunks
            try:
                if listsize - data.size - 12 > 0:
                    self.File.seek(listsize - data.size - 12, 1)

                data = self.getChunkOrList()
            except Exception as e:
                LOG("AVIParser: Unable to seek: %s"%e)

        LOG("AVIParser: Video stream not found")
        return 0


    def getStreamDuration(self) -> int:
        """Calculate duration from stream header (duration in seconds)."""
        try:
            if self.StreamHeader.dwRate <= 0 or self.StreamHeader.dwScale <= 0:
                return 0
            return int(self.StreamHeader.dwLength / (float(self.StreamHeader.dwRate) / float(self.StreamHeader.dwScale)))
        except (ZeroDivisionError, TypeError):
            LOG("AVIParser: Error calculating duration", xbmc.LOGERROR)
            return 0


    def parseHeader(self, data: AVIChunk):
        try:
            header = struct.unpack('<iiiiiiiiiiiiii', data.chunk)
            self.Header.dwMicroSecPerFrame = header[0]
            self.Header.dwMaxBytesPerSec = header[1]
            self.Header.dwPaddingGranularity = header[2]
            self.Header.dwFlags = header[3]
            self.Header.dwTotalFrames = header[4]
            self.Header.dwInitialFrames = header[5]
            self.Header.dwStreams = header[6]
            self.Header.dwSuggestedBufferSize = header[7]
            self.Header.dwWidth = header[8]
            self.Header.dwHeight = header[9]
        except Exception as e:
            self.Header.empty()
            LOG("AVIParser: Unable to parse the header: %s"%e)


    def parseStreamHeader(self, data: AVIChunk):
        try:
            self.StreamHeader.fccType = data.chunk[0:4].decode(DEFAULT_ENCODING)
            self.StreamHeader.fccHandler = data.chunk[4:8].decode(DEFAULT_ENCODING)
            header = struct.unpack('<ihhiiiiiiiid', data.chunk[8:])
            self.StreamHeader.dwFlags = header[0]
            self.StreamHeader.wPriority = header[1]
            self.StreamHeader.wLanguage = header[2]
            self.StreamHeader.dwInitialFrame = header[3]
            self.StreamHeader.dwScale = header[4]
            self.StreamHeader.dwRate = header[5]
            self.StreamHeader.dwStart = header[6]
            self.StreamHeader.dwLength = header[7]
            self.StreamHeader.dwSuggestedBuffer = header[8]
            self.StreamHeader.dwQuality = header[9]
            self.StreamHeader.dwSampleSize = header[10]
            self.StreamHeader.rcFrame = ''
        except Exception as e:
            self.StreamHeader.empty()
            LOG("AVIParser: Error reading stream header: %s"%e)


    def getChunkOrList(self) -> Union[AVIChunk, AVIList]:
        try: 
            data = self.File.readBytes(4).decode(DEFAULT_ENCODING)
        except Exception as e: 
            LOG('AVIParser: getChunkOrList decode failed: %s, using read fallback' % e, xbmc.LOGDEBUG)
            data = self.File.read(4)
        
        if data == "RIFF" or data == "LIST":
            dataclass = AVIList()
        elif len(data) == 0:
            dataclass = AVIChunk()
            dataclass.datatype = 3
        else:
            dataclass = AVIChunk()
            dataclass.fourcc = data

        # Fill in the chunk or list info
        dataclass.read(self.File)
        return dataclass