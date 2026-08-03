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
from threading    import Thread
import variables

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
        match = _VIDEOID_RE.search(filename) if 'videoid' in filename else None
        if match: return match.group(1)
        match = _VIDEO_ID_RE.search(filename) if 'video_id' in filename else None
        if match: return match.group(1)
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
        # Run extract_info in a watchdog thread: youtube_dl can hang indefinitely on
        # a dead endpoint regardless of socket_timeout, which would freeze the build.
        # A 25s ceiling bounds each probe; the orphaned thread is daemon and abandoned.
        YDL_TIMEOUT = 25.0
        result = [0]
        def _probe():
            try:
                if xbmc.getCondVisibility('System.HasAddon(script.module.youtube.dl)'):
                    from youtube_dl import YoutubeDL
                    LOG("YTParser: _getDurationViaYDL, [%s] file = %s"%(vID,filename))
                    ydl = YoutubeDL({'quiet': True, 'skip_download': True, 'cookiefile': self._cookiesFile(), 'no_color': True, 'format': 'best', 'outtmpl': '%(id)s.%(ext)s', 'no-mtime': True, 'add-header': HEADER, 'socket_timeout': 10})
                    with ydl:
                        result[0] = ydl.extract_info("https://www.youtube.com/watch?v={vID}".format(vID=vID), download=False).get('duration',0)
            except Exception as e:
                LOG("YTParser: _getDurationViaYDL, [%s] failed!\n%s"%(vID,e), xbmc.LOGWARNING)
        probe = Thread(target=_probe)
        probe.daemon = True
        probe.start()
        probe.join(YDL_TIMEOUT)
        if probe.is_alive():
            LOG("YTParser: _getDurationViaYDL, [%s] timed out after %ss"%(vID, YDL_TIMEOUT), xbmc.LOGWARNING)
        return result[0]


    def _cookiesFile(self) -> str:
        """Resolve the YouTube cookies file: a user-supplied path from settings
        (Youtube_Cookies) if set and present, else the default generated file."""
        try:
            user = (variables.Globals.settings.getSetting('Youtube_Cookies') or '').strip()
            if user:
                path = FileAccess.translatePath(user)
                if FileAccess.exists(path):
                    return path
        except Exception:
            pass
        return FileAccess.translatePath(YOUTUBE_COOKIES)


    def _youtube_cookie_md5(self) -> str:
        """md5 of the YouTube cookies file, memoized on the file's (mtime, size).

        'nocookie' when the file is missing; when it appears/changes the memo
        refreshes and cached YouTube durations re-parse.
        """
        try:
            fle = self._cookiesFile()
            st = (os.path.getmtime(fle), os.path.getsize(fle)) if FileAccess.exists(fle) else None
            memo = getattr(self, '_yt_cookie_md5_memo', None)
            if memo and memo[0] == st:
                return memo[1]
            value = 'nocookie'
            if st:
                with FileAccess.open(fle, 'r') as f:
                    value = FileAccess._getMD5(f.read())
            self._yt_cookie_md5_memo = (st, value)
            return value
        except Exception:
            return 'nocookie'


    def _getYouTubeDuration(self, video_id: str) -> Union[int, None]:
        """Cached YouTube duration (incl. failed 0), or None when uncached or the
        cookies file changed (re-auth) — caller should re-parse."""
        if not video_id: return None
        value = variables.Globals.settings.cache.get('yt.duration.%s' % video_id, checksum=self._youtube_cookie_md5())
        return round(value) if value is not None else None


    def _setYouTubeDuration(self, video_id: str, duration: int) -> int:
        """Cache a YouTube duration (incl. 0) keyed on the cookies-file md5."""
        if video_id:
            variables.Globals.settings.cache.set('yt.duration.%s' % video_id, round(duration),
                                       checksum=self._youtube_cookie_md5(), expiration=datetime.timedelta(days=28))
        return duration


    def determineLength(self, filename: str) -> Union[int, float]:
        dur = 0
        vID = self._getVideoID(filename)
        if not vID:
            LOG("YTParser: determineLength, no video_id found in [%s]"%filename, xbmc.LOGWARNING)
            return 0
        LOG("YTParser: determineLength, [%s] file = %s"%(vID,filename))
        cached = self._getYouTubeDuration(vID)
        if cached is not None:
            LOG('YTParser: determineLength, cached = %s'%cached)
            return cached
        dur = self._getDurationViaYTPlugin(vID)
        if dur == 0:
            dur = self._getDurationViaYDL(vID, filename)
        self._setYouTubeDuration(vID, dur)
        LOG('YTParser: determineLength, duration = %s'%dur)
        return dur