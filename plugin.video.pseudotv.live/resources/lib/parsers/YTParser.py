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

from variables    import *
from typing       import Union

_VIDEOID_RE  = re.compile(r'videoid\=(.*)' , re.IGNORECASE)
_VIDEO_ID_RE = re.compile(r'video_id\=(.*)', re.IGNORECASE)
_ISO8601_RE  = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', re.IGNORECASE)

class YTParser(object):


    def _parseISO8601Duration(self, duration: str) -> int:
        match = _ISO8601_RE.match(duration)
        if match:
            hours   = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return (hours * 3600) + (minutes * 60) + seconds
        return 0


    def _getVideoID(self, filename: str) -> Union[str, None]:
        if   'videoid'  in filename: return _VIDEOID_RE.search(filename).group(1)
        elif 'video_id' in filename: return _VIDEO_ID_RE.search(filename).group(1)
        return None


    def _getDurationViaYTPlugin(self, vID: str) -> int:
        try:
            if xbmc.getCondVisibility('System.HasAddon(plugin.video.youtube)') and xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.youtube)'):
                from youtube_requests import get_videos
                items = get_videos(vID)
                if items and isinstance(items, list):
                    item = items[0]
                    duration_str = item.get('contentDetails', {}).get('duration', '')
                    if duration_str:
                        dur = self._parseISO8601Duration(duration_str)
                        if dur > 0:
                            LOG("YTParser: _getDurationViaYTPlugin, [%s] duration = %ds"%(vID, dur))
                            return dur
        except Exception as e:
            LOG("YTParser: _getDurationViaYTPlugin, failed!\n%s"%e, xbmc.LOGDEBUG)
        return 0


    def _getDurationViaYDL(self, vID: str, filename: str) -> int:
        try:
            if xbmc.getCondVisibility('System.HasAddon(script.module.youtube.dl)'):
                from youtube_dl import YoutubeDL
                LOG("YTParser: _getDurationViaYDL, [%s] file = %s"%(vID,filename))
                ydl = YoutubeDL({'quiet': False, 'skip_download': True, 'cookiefile': FileAccess.translatePath(YOUTUBE_COOKIES), 'no_color': True, 'format': 'best', 'outtmpl': '%(id)s.%(ext)s', 'no-mtime': True, 'add-header': HEADER, 'socket_timeout': 10})
                with ydl:
                    return ydl.extract_info("https://www.youtube.com/watch?v={sID}".format(sID=vID), download=False).get('duration',0)
        except Exception as e:
            LOG("YTParser: _getDurationViaYDL, [%s] failed!\n%s"%(vID,e), xbmc.LOGWARNING)
        return 0


    def determineLength(self, filename: str) -> Union[int, float]:
        dur = 0
        vID = self._getVideoID(filename)
        if not vID:
            LOG("YTParser: determineLength, no video_id found in [%s]"%filename, xbmc.LOGWARNING)
            return 0
        LOG("YTParser: determineLength, [%s] file = %s"%(vID,filename))
        dur = self._getDurationViaYTPlugin(vID)
        if dur == 0:
            dur = self._getDurationViaYDL(vID, filename)
        LOG('YTParser: determineLength, duration = %s'%dur)
        return dur