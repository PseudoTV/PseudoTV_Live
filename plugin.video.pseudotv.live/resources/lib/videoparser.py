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
    
class VideoParser:
    def __init__(self):
        self.AVIExts   = ['.avi']
        self.MP4Exts   = ['.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov']
        self.MKVExts   = ['.mkv']
        self.FLVExts   = ['.flv']
        self.TSExts    = ['.ts', '.m2ts']
        self.STRMExts  = ['.strm']
        self.VFSPaths  = ['resource://','plugin://','upnp://','pvr://']


    def getExt(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext in self.AVIExts:
            return AVIParser.AVIParser().determineLength(filename)
        elif ext in self.MP4Exts:
            return MP4Parser.MP4Parser().determineLength(filename)
        elif ext in self.MKVExts:
            return MKVParser.MKVParser().determineLength(filename)
        elif ext in self.FLVExts:
            return FLVParser.FLVParser().determineLength(filename)
        elif ext in self.TSExts:
            return TSParser.TSParser().determineLength(filename)
        elif ext in self.STRMExts:
            return NFOParser.NFOParser().determineLength(filename)
        else: 
            return 0


    def getRPC(self, filename, fileitem, jsonRPC):
        return VFSParser.VFSParser().determineLength(filename, fileitem, jsonRPC)
        

    def getVideoLength(self, filename, fileitem={}, jsonRPC=None):
        log("VideoParser: getVideoLength %s"%filename)
        if len(filename) == 0:
            log("VideoParser: getVideoLength, No file name specified")
            return 0

        if not FileAccess.exists(filename):
            log("VideoParser: getVideoLength, Unable to find the file")
            return 0

        if filename.startswith(tuple(self.VFSPaths)):
            dur = self.getRPC(filename, fileitem, jsonRPC)
        else:
            dur = self.getExt(filename)
            if not dur:
                for parser in EXTERNAL_PARSER:
                    dur = parser().determineLength(filename)
                    if MONITOR.waitForAbort(0.001) or dur > 0: break
        log('VideoParser: getVideoLength, duration = %s'%(dur))
        return dur