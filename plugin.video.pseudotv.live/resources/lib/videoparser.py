#   Copyright (C) 2011 Jason Anderson
#   Copyright (C) 2024 Lunatixz
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

from globals    import *
from parsers    import MP4Parser
from parsers    import AVIParser
from parsers    import MKVParser
from parsers    import FLVParser
from parsers    import TSParser
from parsers    import VFSParser
from parsers    import NFOParser
from parsers    import YTParser
 
EXTERNAL_PARSER = [NFOParser.NFOParser]
try:
    import hachoir
    from parsers import Hachoir
    EXTERNAL_PARSER.append(Hachoir.Hachoir)
except: pass
    
try:
    import ffmpeg
    from parsers import FFProbe
    EXTERNAL_PARSER.append(FFProbe.FFProbe)
except: pass
    
try:
    import cv2
    from parsers import OpenCV
    EXTERNAL_PARSER.append(OpenCV.OpenCV)
except: pass
    
try:
    import moviepy
    from parsers import MoviePY
    EXTERNAL_PARSER.append(MoviePY.MoviePY)
except: pass
    
try:
    import pymediainfo
    from parsers import MediaInfo
    EXTERNAL_PARSER.append(MediaInfo.MediaInfo)
except: pass
    
class VideoParser:
    def __init__(self):
        self.AVIExts   = ['.avi']
        self.MP4Exts   = ['.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov']
        self.MKVExts   = ['.mkv']
        self.FLVExts   = ['.flv']
        self.TSExts    = ['.ts', '.m2ts']
        self.STRMExts  = ['.strm']
        self.VFSPaths  = ['resource://','plugin://','upnp://','pvr://']
        self.YTPaths   = ['plugin://plugin.video.youtube','plugin://plugin.video.tubed','plugin://plugin.video.invidious']


    def getVideoLength(self, filename: str, fileitem: dict={}, jsonRPC=None) -> int and float:
        duration = jsonRPC._getDuration(filename)
        if duration == 0:
            if not filename: log("VideoParser: getVideoLength, no filename.")
            elif filename.lower().startswith(tuple(self.VFSPaths)):
                duration = VFSParser.VFSParser().determineLength(filename, fileitem, jsonRPC)
                if duration == 0 and filename.lower().startswith(tuple(self.YTPaths)):
                    duration = YTParser.YTParser().determineLength(filename)
            else:
                ext = os.path.splitext(filename)[1].lower()
                if not FileAccess.exists(filename):
                    log("VideoParser: getVideoLength, Unable to find the file")
                    duration = 0
                elif ext in self.AVIExts:
                    duration = AVIParser.AVIParser().determineLength(filename)
                elif ext in self.MP4Exts:
                    duration = MP4Parser.MP4Parser().determineLength(filename)
                elif ext in self.MKVExts:
                    duration = MKVParser.MKVParser().determineLength(filename)
                elif ext in self.FLVExts:
                    duration = FLVParser.FLVParser().determineLength(filename)
                elif ext in self.TSExts:
                    duration = TSParser.TSParser().determineLength(filename)
                elif ext in self.STRMExts:
                    duration = NFOParser.NFOParser().determineLength(filename)
                else: 
                    duration = 0

                if duration == 0:
                    for parser in EXTERNAL_PARSER:
                        if MONITOR.waitForAbort(.001) or duration > 0: break
                        duration = parser().determineLength(filename)
            if duration > 0: duration = jsonRPC._setDuration(filename, fileitem, int(duration))
        log("VideoParser: getVideoLength duration = %s, filename = %s"%(duration,filename))
        return duration