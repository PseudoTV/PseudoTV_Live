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
            from pymediainfo import MediaInfo
            dur = 0
            mi  = None
            fileXML = filename.replace('.%s'%(filename.rsplit('.',1)[1]),'-mediainfo.xml')
            if FileAccess.exists(fileXML):
                log("MediaInfo: parsing XML %s"%(fileXML))
                fle = FileAccess.open(fileXML, 'rb')
                mi  = MediaInfo(fle.read())
                fle.close()
            else:
                log("MediaInfo: parsing %s"%(FileAccess.translatePath(filename)))
                mi = MediaInfo.parse(FileAccess.translatePath(filename))
                
            if not mi is None and mi.tracks:
                for track in mi.tracks:
                    if track.track_type == 'General':
                        dur = track.duration / 1000
                        break
            
            log("MediaInfo: determineLength %s Duration is %s"%(filename,dur))
            return dur
        except Exception as e:
            log("MediaInfo: failed! %s"%(e), xbmc.LOGERROR)
            return 0
            
            
            
