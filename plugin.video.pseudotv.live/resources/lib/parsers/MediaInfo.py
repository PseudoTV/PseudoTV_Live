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

class MediaInfo:
    def determineLength(self, filename: str) -> int and float:
        try:
            log("MediaInfo: determineLength %s"%(filename))
            from pymediainfo import MediaInfo
            dur = 0
            mi  = None
            fileXML = filename.replace('.%s'%(filename.rsplit('.',1)[1]),'-mediainfo.xml')
            if FileAccess.exists(fileXML):
                log("MediaInfo: parsing XML %s"%(fileXML))
                with xbmcvfs.File(fileXML) as fle:
                    mi = pymediainfo.MediaInfo(fle.read())
            else:
                try:
                    mi = MediaInfo.parse(xbmcvfs.translatePath(filename))
                    log("MediaInfo: parsing %s"%(filename))
                except: 
                    with xbmcvfs.File(filename) as fle:
                        mi = MediaInfo.parse(xbmcvfs.translatePath(fle.read()))
                        log("MediaInfo: reading %s"%(filename))
            if not mi is None: dur = (mi.tracks[0].duration // 1000 or 0)
            log('MediaInfo: Duration is %s'%(dur))
            return dur
        except Exception as e:
            log("MediaInfo: failed! %s"%(e), xbmc.LOGERROR)
            return 0