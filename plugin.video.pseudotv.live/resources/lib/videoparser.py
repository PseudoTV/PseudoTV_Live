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
    import pymediainfo
    from parsers import MediaInfo
    EXTERNAL_PARSER.append(MediaInfo.MediaInfo)
except: pass
    
try:
    import ffmpeg
    from parsers import FFProbe
    EXTERNAL_PARSER.append(FFProbe.FFProbe)
except: pass
    
try:
    import hachoir
    from parsers import Hachoir
    EXTERNAL_PARSER.append(Hachoir.Hachoir)
except: pass

try:
    import moviepy
    from parsers import MoviePY
    from numpy.core._multiarray_umath import *
    EXTERNAL_PARSER.append(MoviePY.MoviePY)
except: pass

try:
    import cv2
    from parsers import OpenCV
    EXTERNAL_PARSER.append(OpenCV.OpenCV)
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


    def _validateDuration(self, duration, filename=""):
        """Validate duration - only reject None and negative values"""
        if duration is None:
            log("VideoParser: Duration is None for %s" % filename, xbmc.LOGWARNING)
            return 0
        
        # Accept numeric types (int, float)
        try:
            duration = float(duration)
        except (ValueError, TypeError):
            log("VideoParser: Invalid duration type %s for %s" % (type(duration), filename), xbmc.LOGWARNING)
            return 0
        
        if duration < 0:
            log("VideoParser: Negative duration %s detected for %s" % (duration, filename), xbmc.LOGWARNING)
            return 0
        
        # Log warnings for unusual durations but preserve the value
        if duration > 86400 * 7:  # > 7 days
            log("VideoParser: Very long duration %s for %s - verify file is valid" % (duration, filename), xbmc.LOGWARNING)
        
        # Return duration as-is to preserve fractional seconds
        return duration


    def _getKodiDuration(self, filename, fileitem, jsonRPC):
        """Try to get duration from Kodi's database as a fallback"""
        try:
            # Try getting runtime from the file item's metadata
            runtime = fileitem.get('runtime', 0)
            if runtime and runtime > 0:
                validated = self._validateDuration(runtime, filename)
                if validated > 0:
                    log("VideoParser: Using Kodi runtime from fileitem: %s for %s" % (validated, filename))
                    return validated
            
            # Try streamdetails
            streamdetails = fileitem.get('streamdetails', {})
            video_details = streamdetails.get('video', [])
            if video_details and len(video_details) > 0:
                stream_duration = video_details[0].get('duration', 0)
                if stream_duration and stream_duration > 0:
                    # streamdetails.video.duration is often in seconds but can be milliseconds
                    # If duration seems unreasonably large (>30 days), it's likely in milliseconds
                    if stream_duration > 86400 * 30:
                        stream_duration = stream_duration / 1000  # Convert from ms
                    validated = self._validateDuration(stream_duration, filename)
                    if validated > 0:
                        log("VideoParser: Using Kodi streamdetails duration: %s for %s" % (validated, filename))
                        return validated
            
            # Try resume total
            resume = fileitem.get('resume', {})
            total = resume.get('total', 0)
            if total and total > 0:
                validated = self._validateDuration(total, filename)
                if validated > 0:
                    log("VideoParser: Using Kodi resume total: %s for %s" % (validated, filename))
                    return validated
                    
        except Exception as e:
            log("VideoParser: _getKodiDuration exception: %s" % e, xbmc.LOGWARNING)
        
        return 0


    def getVideoLength(self, filename: str, fileitem: dict={}, jsonRPC=None) -> int:
        duration = jsonRPC._getDuration(filename)
        if duration == 0:
            if not filename: 
                log("VideoParser: getVideoLength, no filename.")
                return 0
            elif filename.lower().startswith(tuple(self.VFSPaths)):
                if filename.lower().startswith(tuple(self.YTPaths)):
                    duration = YTParser.YTParser().determineLength(filename)
                if duration == 0:
                    duration = VFSParser.VFSParser().determineLength(filename, fileitem, jsonRPC)
            else:
                ext = os.path.splitext(filename)[1].lower()
                if not FileAccess.exists(filename):
                    log("VideoParser: getVideoLength, Unable to find the file: %s" % filename)
                    duration = 0
                else:
                    # Try built-in parsers first
                    try:
                        if ext in self.AVIExts:
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
                    except Exception as e:
                        log("VideoParser: Parser exception for %s: %s" % (filename, e), xbmc.LOGERROR)
                        duration = 0

                    # Validate the parsed duration
                    duration = self._validateDuration(duration, filename)

                    # If parsing failed, try external parsers
                    if duration == 0:
                        log("VideoParser: Primary parser returned 0 for %s, trying external parsers" % filename)
                        for parser in EXTERNAL_PARSER:
                            if MONITOR().waitForAbort(0.0001) or duration > 0: 
                                break
                            try:
                                duration = parser().determineLength(filename)
                                duration = self._validateDuration(duration, filename)
                            except Exception as e:
                                log("VideoParser: External parser %s failed: %s" % (parser.__name__, e), xbmc.LOGWARNING)
                                duration = 0
                    
                    # If all parsers failed, try Kodi's database as final fallback
                    if duration == 0 and fileitem:
                        log("VideoParser: All parsers failed for %s, trying Kodi database fallback" % filename)
                        duration = self._getKodiDuration(filename, fileitem, jsonRPC)
            
            # Final validation before caching
            duration = self._validateDuration(duration, filename)
            
            if duration > 0: 
                # Preserve fractional durations - round to 3 decimal places for storage
                cache_duration = round(duration, 3)
                duration = jsonRPC._setDuration(filename, fileitem, cache_duration)
        
        log("VideoParser: getVideoLength duration = %s, filename = %s" % (duration, filename))
        return duration
