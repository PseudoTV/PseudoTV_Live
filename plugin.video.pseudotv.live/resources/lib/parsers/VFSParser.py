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
    def __init__(self, fileItem={}, jsonRPC=None):
        self.jsonRPC  = jsonRPC
        self.fileItem = fileItem
        
        
    def walkVFS(self, filename, originalPath):
        log("VFSParser: walkVFS, originalPath = %s"%(originalPath))
        #todo parse json for item, walk dir.
        # results = []
        # json_response = self.jsonRPC.getDirectory('{"directory":"%s","media":"%s","properties":["duration","runtime"]}'%(path, media), cache=False).get('files', [])
        # for item in json_response:
            # file = item['file']
            # if item['filetype'] == 'file':
                # results.append({'label': item['label'], 'duration': dur, 'path': path, 'file': file})
            # else:
                # results.extend(self.getFileDirectory(file, media, ignoreDuration, checksum, expiration))

        return {}
         
         
    def determineLength(self, filename={}):
        log("VFSParser: determineLength, file = %s, item = %s"%(filename,self.fileItem))
        if not self.fileItem: 
            self.fileItem = self.walkVFS(filename, self.fileItem.get('originalpath',''))
        elif not filename.lower().startswith(self.fileItem.get('originalpath','')[:30].lower()): 
            return 0
        duration = ceil(self.fileItem.get('runtime','') or self.fileItem.get('duration','') or (self.fileItem.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration','') or '0')
        log("VFSParser: Duration is %s"%(duration))
        return duration