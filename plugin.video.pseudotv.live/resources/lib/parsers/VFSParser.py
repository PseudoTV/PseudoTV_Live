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

from variables import *
from typing import Optional, Union

class VFSParser:
    def determineLength(self, filename: str, fileitem: Optional[dict] = None, jsonRPC=None) -> Union[int, float]:
        """
        Determines video duration from VFS metadata.
        Returns duration in seconds from available metadata sources.
        
        Priority: resume.total > runtime > duration > streamdetails.video.duration
        """
        if fileitem is None: fileitem = {}
        LOG("VFSParser: determineLength, [%s]"%(filename))
        # Try to extract duration from fileitem metadata (assumed to be in seconds)
        duration = (fileitem.get('resume', {}).get('total') or fileitem.get('runtime') or 
                    fileitem.get('duration') or (fileitem.get('streamdetails', {}).get('video', []) or [{}])[0].get('duration') or 0)
        
        # If no duration found and paths don't match, try JSON-RPC
        if duration == 0 and jsonRPC is not None:
            try:
                if not filename.lower().startswith(fileitem.get('originalpath', '').lower()) and not filename.lower().startswith(tuple(['resource://','plugin://','upnp://','pvr://'])):
                    metadata = jsonRPC.getFileDetails((fileitem.get('originalpath') or fileitem.get('file') or filename))
                    duration = (metadata.get('resume', {}).get('total') or  metadata.get('runtime') or 
                                metadata.get('duration') or (metadata.get('streamdetails', {}).get('video', []) or [{}])[0].get('duration') or 0)
            except Exception as e:
                LOG("VFSParser: getFileDetails, failed!\n%s"%(e), xbmc.LOGERROR)
        
        try:
            duration = round(duration)
        except (ValueError, TypeError):
            duration = 0
        
        LOG("VFSParser: determineLength, duration = %s seconds"%(duration))
        return duration