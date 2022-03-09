#   Copyright (C) 2022 Lunatixz
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

from resources.lib.globals import *

class VFSParser:
    def __init__(self, fileItem={}):
        self.fileItem = fileItem
        
        
    def walkVFS(self, filename, originalPath):
        #todo parse json for item, walk dir.
        return {}
         
         
    def determineLength(self, filename={}):
        log("VFSParser: determineLength, file = %s, item = %s"%(filename,self.fileItem))
        if not self.fileItem: 
            self.fileItem = self.walkVFS(filename, self.fileItem.get('originalpath',''))
        elif not filename.lower().startswith(self.fileItem.get('originalpath','')[:30].lower()): 
            return 0
        duration = int(self.fileItem.get('runtime','') or self.fileItem.get('duration','') or (self.fileItem.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration','') or '0')
        log("VFSParser: Duration is %s"%(duration))
        return duration