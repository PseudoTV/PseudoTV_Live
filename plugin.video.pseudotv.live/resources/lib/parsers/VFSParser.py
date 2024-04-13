#   Copyright (C) 2024 Lunatixz
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live Live.  If not, see <http://www.gnu.org/licenses/>.

from globals import *

class VFSParser:
    def determineLength(self, filename, fileitem={}, jsonRPC=None):
        log("VFSParser: determineLength, file = %s\nitem = %s"%(filename,fileitem))
        duration = (fileitem.get('runtime') or fileitem.get('duration') or (fileitem.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration') or 0)
        if duration == 0 and not filename.lower().startswith(fileitem.get('originalpath','').lower()):
            metadata = self.jsonRPC.sendJSON('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"video","properties":["duration","runtime"]}}'%(fileitem.get('originalpath'))).get('filedetails',{})
            duration = (metadata.get('runtime') or metadata.get('duration') or (metadata.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration') or 0)
        log("VFSParser: Duration is %s"%(duration))
        return duration
