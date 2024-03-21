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
from parsers    import NFOParser
from parsers    import VFSParser
 
class VideoParser:
    def __init__(self):
        self.AVIExts   = ['.avi']
        self.MP4Exts   = ['.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov']
        self.MKVExts   = ['.mkv']
        self.FLVExts   = ['.flv']
        self.TSExts    = ['.ts', '.m2ts']
        self.STRMExts  = ['.strm']
        self.VFSPaths  = ['resource://','plugin://','upnp://','pvr://']


    def getFFProbe(self, filename):
        try:
            result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            return float(result.stdout)
        except Exception as e:
            log("VideoParser: getFFMPEG, FFMPEG failed! %s"%(e), xbmc.LOGERROR)
            return 0


    def getVideoLength(self, filename, fileItem={}, jsonRPC=None):
        log("VideoParser: getVideoLength %s"%filename)
        if len(filename) == 0:
            log("VideoParser: getVideoLength, No file name specified")
            return 0

        if FileAccess.exists(filename) == False:
            log("VideoParser: getVideoLength, Unable to find the file")
            return 0

        base, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if filename.startswith(tuple(self.VFSPaths)):
            self.parser = VFSParser.VFSParser(fileItem, jsonRPC)
        elif ext in self.AVIExts:
            self.parser = AVIParser.AVIParser()
        elif ext in self.MP4Exts:
            self.parser = MP4Parser.MP4Parser()
        elif ext in self.MKVExts:
            self.parser = MKVParser.MKVParser()
        elif ext in self.FLVExts:
            self.parser = FLVParser.FLVParser()
        elif ext in self.TSExts:
            self.parser = TSParser.TSParser()
        elif ext in self.STRMExts:
            self.parser = NFOParser.NFOParser()
        else:
            log("VideoParser: getVideoLength, No parser found for extension %s"%(ext))
            return 0
       
        duration = 0
        if not filename.startswith(tuple(self.VFSPaths)):
            duration = self.parser.determineLength(filename)
            if duration == 0:
                duration = NFOParser.NFOParser().determineLength(filename)
                    
        log('VideoParser: getVideoLength, duration = %s'%(duration))
        return duration