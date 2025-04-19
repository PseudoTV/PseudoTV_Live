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

class YTParser:
    def determineLength(self, filename: str) -> int and float:
        try:
            if hasAddon('script.module.youtube.dl'):
                from youtube_dl import YoutubeDL
                if   'videoid'  in filename: vID = (re.compile(r'videoid\=(.*)' , re.IGNORECASE).search(filename)).group(1)
                elif 'video_id' in filename: vID = (re.compile(r'video_id\=(.*)', re.IGNORECASE).search(filename)).group(1)
                else: raise Exception('No video_id found!')
                log("YTParser: determineLength, file = %s, id = %s"%(filename,vID))
                ydl = YoutubeDL({'no_color': True, 'format': 'best', 'outtmpl': '%(id)s.%(ext)s', 'no-mtime': True, 'add-header': HEADER})
                with ydl:
                    dur = ydl.extract_info("https://www.youtube.com/watch?v={sID}".format(sID=vID), download=False).get('duration',0)
            log('YTParser: Duration is %s'%(dur))
            return dur
        except Exception as e:
            log("YTParser: failed! %s\nfile = %s"%(e,filename), xbmc.LOGERROR)
            return 0