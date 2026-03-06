#   Copyright (C) 2025 Lunatixz
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

from globals    import *
#todo create dataclasses for all jsons
# https://pypi.org/project/dataclasses-json/
class Channels(object):
    
    def __init__(self, file=CHANNELFLEPATH, writable=False):
        self.writable    = writable
        self.channelFile = file
        self.channelDATA = FileAccess.getJSON(CHANNELFLE_DEFAULT)
        self.channelTEMP = self.channelDATA.get('channels',[{}]).pop(0)
        self.channelRULE = self.channelTEMP.pop('rules')
        self.channelTEMP['rules'] = {}
        self.channelDATA.update(self._load())
        self.channelDATA_OLD = self.channelDATA.copy()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _load(self) -> dict:
        channelDATA = FileAccess.getJSON(self.channelFile)
        SETTINGS.setSetting('Open_Manager','[B]%s[/B] Channels'%(len(channelDATA.get('channels',[]))))
        self.log('_load, file = %s\nchannels = %s'%(self.channelFile,len(channelDATA.get('channels',[]))))
        return channelDATA
    
        
    def _verify(self, channels: list=[]):
        for idx, citem in enumerate(self.channelDATA.get('channels',[])):
            if not citem.get('name') or not citem.get('id') or len(citem.get('path',[])) == 0:
                self.log('_verify, in-valid citem [%s]\n%s'%(citem.get('id'),citem))
                continue
            yield citem
                
                
    def _save(self) -> bool:
        self.log('_save, writable = %s, file = %s\nchannels = %s'%(self.writable,self.channelFile,len(self.channelDATA['channels'])))
        if self.writable:
            with PROPERTIES.interruptActivity():
                if FileAccess.setJSON(self.channelFile,self.channelDATA):
                    SETTINGS.setSetting('Open_Manager','[B]%s[/B] Channels'%(len(self.channelDATA['channels'])))
                    return True
        
        
    def getTemplate(self) -> dict: 
        return self.channelTEMP.copy()
        
        
    def getChannels(self) -> list:
        return sorted(self.channelDATA['channels'], key=itemgetter('number'))
        
        
    def getChannelbyID(self, id: str) -> list:
        return list([c for c in self.channelDATA['channels'] if c.get('id') == id])
        
        
    def getChannelbyType(self, type: str):
        return list([citem for citem in self.channelDATA['channels'] if citem.get('type') == type])


    def sortChannels(self, channels: list) -> list:
        try:              return sorted(channels, key=itemgetter('number'))
        except Exception: return channels

    
    def setChannels(self, channels=None) -> bool:
        if channels is None: channels = self.channelDATA['channels']
        self.channelDATA['uuid']     = SETTINGS.getMYUUID()
        self.channelDATA['channels'] = self.sortChannels(channels)
        PROPERTIES.setHasChannels(len(channels)>0)
        return self._save()
        

    def getImports(self) -> list:
        return self.channelDATA.get('imports',[])
        
        
    def setImports(self, data: list=[]) -> bool:
        self.channelDATA['imports'] = data
        return self._save()
         
         
    def clrChannels(self):
        self.channelDATA['channels'] = []
        

    def delChannel(self, citem: dict={}) -> bool:
        if isinstance(citem,list): return any([self.delChannel(channel) for channel in citem])
        try: 
            self.channelDATA['channels'].pop(self.findChannel(citem)[0])
            self.log('[%s] delChannel, channel deleted!'%(citem['id']), xbmc.LOGINFO)
            return True
        except Exception: pass
    
    
    def addChannel(self, citem: dict={}) -> bool:
        if isinstance(citem,list): return any([self.addChannel(channel) for channel in citem])
        self.delChannel(citem)
        self.log('addChannel, [%s] adding channel %s'%(citem["id"],citem["name"]), xbmc.LOGINFO)
        self.channelDATA.setdefault('channels',[]).append(Globals._cleanGroups(citem))
        return True
        
        
    def findChannel(self, citem: dict={}, channels=None) -> tuple:
        if channels is None: channels = self.channelDATA['channels']
        if citem.get('id') is None: citem['id'] = getChannelID(citem.get('name'), citem.get('path'), citem.get('number'), uuid=self.channelDATA.get('uuid'))
        return tuple(next(((idx, eitem) for idx, eitem in enumerate(channels) if citem['id'] == eitem.get('id', str(random.random()))), (None,{})))
        