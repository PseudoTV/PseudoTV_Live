#   Copyright (C) 2020 Lunatixz
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
# -*- coding: utf-8 -*-
from resources.lib.globals     import *
from resources.lib.jsonrpc     import JSONRPC

class UPNP:
    def __init__(self, cache=None):
        self.log('__init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
        self.jsonRPC = JSONRPC(self.cache)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def CHKUPNP_Setting(self):
        log('CHKUPNP_Setting')# Check Kodi UPNP support.
        if not self.jsonRPC.getSettingValue('{"setting":"services.upnp"}').get('result',{}).get('value',True): 
            return self.setUPNP_Setting()
        
    
    def setUPNP_Setting(self):
        log('setUPNP_Setting') #Enable Kodi UPNP support.
        return self.jsonRPC.setSettingValue('{"setting":"services.upnp","value":true}')

    
    def getUPNP_IDs(self):
        log('getUPNP_IDs') #Check if upnp id is valid.
        if self.CHKUPNP_Setting():
            return self.jsonRPC.getDirectory('{"directory":"upnp://"},cache=False).get('result',{}').get('files',[])
            
            
    def chkUPNP(self, path):
        log('chkUPNP') #Query json, match old path with new upnp id.
        files = self.getUPNP_IDs()
        return path
        # for file in files:            
        # self.log('existsVFS path = %s, media = %s'%(path,media))
        # dirs  = []
        # json_response = self.requestList(str(random.random()), path, media)
        # for item in json_response:
            # file = item.get('file','')
            # fileType = item.get('filetype','file')
            # if fileType == 'file':
                # dur = self.fileList.getDuration(file, item)
                # if dur > 0: return {'file':file,'duration':dur,'seek':self.chkSeeking(file, dur)}
            # else: dirs.append(file)
        # for dir in dirs: return self.existsVFS(dir, media)
        # return None
            # if file.get('label','').lower() == label.lower(): return file.get('file',path)
        # return path
