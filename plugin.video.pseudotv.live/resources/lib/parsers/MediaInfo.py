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
from typing import Union

class MediaInfo:
    def determineLength(self, filename: str) -> Union[int, float]:
        try:
            from pymediainfo import MediaInfo
            dur = 0
            mi  = None
            xml = None
            fle = None
            
            if FileAccess.exists(filename.replace('.%s'%(filename.rsplit('.',1)[1]),'-mediainfo.xml')):
                xml = filename.replace('.%s'%(filename.rsplit('.',1)[1]),'-mediainfo.xml')
            elif FileAccess.exists(filename.replace('.%s'%(filename.rsplit('.',1)[1]),'.xml')):
                xml = filename.replace('.%s'%(filename.rsplit('.',1)[1]),'.xml')
            
            try:
                if xml is None: raise Exception('no xml found!, directly parsing file.')
                LOG("MediaInfo: parsing XML %s"%(xml))
                fle = FileAccess.open(xml, 'rb')
                mi  = MediaInfo(fle.read())
            except Exception: 
                LOG("MediaInfo: parsing %s"%(FileAccess.translatePath(filename)))
                mi = MediaInfo.parse(FileAccess.translatePath(filename))
            finally:
                if hasattr(fle, 'close'): 
                    fle.close()
                
            if not mi is None and mi.tracks:
                for track in mi.tracks:
                    if track.track_type == 'General':
                        dur = track.duration / 1000
                        break
            
            LOG("MediaInfo: determineLength %s Duration is %s"%(filename,dur))
            return dur
        except Exception as e:
            LOG("MediaInfo: failed! %s"%(e), xbmc.LOGERROR)
            return 0
            
            
            
