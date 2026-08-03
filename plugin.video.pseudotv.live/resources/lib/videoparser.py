#   Copyright (C) 2011 Jason Anderson
#   Copyright (C) 2026 Lunatixz
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

from typing import Any, Optional
from variables  import *
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
    import pymediainfo
    from parsers import MediaInfo
    EXTERNAL_PARSER.append(MediaInfo.MediaInfo)
except Exception as e: LOG('VideoParser: pymediainfo not available, failed!\n%s' % e, xbmc.LOGDEBUG)
    
try:
    import shutil
    if shutil.which('ffmpeg') or shutil.which('ffprobe'):
        import ffmpeg
        from parsers import FFProbe
        EXTERNAL_PARSER.append(FFProbe.FFProbe)
except Exception as e: LOG('VideoParser: ffmpeg not available, failed!\n%s' % e, xbmc.LOGDEBUG)
    
try:
    import hachoir
    from parsers import Hachoir
    EXTERNAL_PARSER.append(Hachoir.Hachoir)
except Exception as e: LOG('VideoParser: hachoir not available, failed!\n%s' % e, xbmc.LOGDEBUG)

# moviepy and cv2 are intentionally omitted: their single-phase-init C extensions
# (numpy/OpenCV) cannot load in Kodi's Python subinterpreter
# ("cannot load module more than once per process"), so these fallbacks can never
# work here and only spam the log at every startup.

class VideoParser(object):
    def __init__(self):
        self.AVIExts  = ['.avi']
        self.MP4Exts  = ['.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov']
        self.MKVExts  = ['.mkv']
        self.FLVExts  = ['.flv']
        self.TSExts   = ['.ts', '.m2ts']
        self.STRMExts = ['.strm']
        self.VFSPaths = ['resource://','plugin://','upnp://','pvr://']
        self.YTPaths  = ['plugin://plugin.video.youtube','plugin://plugin.video.tubed','plugin://plugin.video.invidious']


    def getVideoLength(self, filename: str, fileitem: dict = {}, jsonRPC: Any = None) -> float:
        duration = jsonRPC._getDuration(filename)
        if duration == 0:
            if not filename: LOG("VideoParser: getVideoLength, no filename.")
            elif filename.lower().startswith(tuple(self.VFSPaths)):
                if filename.lower().startswith(tuple(self.YTPaths)):
                    # YouTube: determineLength checks the cookie-keyed cache (incl. a
                    # failed bot-check 0) and re-parses only when uncached or the
                    # cookies file changed. No fall-through to the VFS probe.
                    duration = YTParser.YTParser().determineLength(filename)
                else:
                    duration = VFSParser.VFSParser().determineLength(filename, fileitem, jsonRPC)
            else:
                ext = os.path.splitext(filename)[1].lower()
                if not FileAccess.exists(filename):
                    LOG("VideoParser: getVideoLength, unable to find the file")
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
                    monitor = MONITOR()
                    for parser in EXTERNAL_PARSER:
                        if monitor.waitForAbort(0.0001) or duration > 0: break
                        duration = parser().determineLength(filename)
                    del monitor
            
            # Cache successful probes in the generic duration cache — YouTube stays in
            # its own cookie-keyed cache so a re-auth invalidates it correctly.
            if duration > 0 and not filename.lower().startswith(tuple(self.YTPaths)):
                duration = jsonRPC._setDuration(filename, fileitem, round(duration))
        LOG("VideoParser: getVideoLength, duration = %s, filename = %s"%(duration,filename))
        return duration