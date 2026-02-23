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
        self.writable   = writable
        self.channelFile = file
        self.channelDATA = FileAccess.getJSON(CHANNELFLE_DEFAULT)
        self.channelTEMP = self.channelDATA.get('channels',[{}]).pop(0)
        self.channelRULE = self.channelTEMP.pop('rules')
        self.channelTEMP['rules'] = {}
        self.channelDATA.update(self._load())
        self.channelDATA_OLD = self.channelDATA.copy()
        
        
    def __del__(self):
        self._save()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _load(self) -> dict:
        channelDATA = FileAccess.getJSON(self.channelFile)
        SETTINGS.setSetting('Open_Manager','[B]%s[/B] Channels'%(len(channelDATA.get('channels',[]))))
        self.log('_load, file = %s\nchannels = %s'%(self.channelFile,len(channelDATA.get('channels',[]))))
        return channelDATA
    
    
    def _reload(self) -> bool:
        self.log('_reload') 
        self.__init__()
        return True
        
        
    def _verify(self, channels: list=[]):
        for idx, citem in enumerate(self.channelDATA.get('channels',[])):
            if not citem.get('name') or not citem.get('id') or len(citem.get('path',[])) == 0:
                self.log('_verify, in-valid citem [%s]\n%s'%(citem.get('id'),citem))
                continue
            else: 
                yield citem
                
                
    def _save(self) -> bool:
        self.channelDATA['uuid']     = SETTINGS.getMYUUID()
        self.channelDATA['channels'] = self.sortChannels(self.channelDATA['channels'])
        self.log('_save, writable = %s, file = %s\nchannels = %s'%(self.writable,self.channelFile,len(self.channelDATA['channels'])))
        if self.writable: return FileAccess.setJSON(self.channelFile,self.channelDATA)
        
        
    def getTemplate(self) -> dict: 
        return self.channelTEMP.copy()
        
        
    def getChannels(self) -> list:
        return sorted(self.channelDATA['channels'], key=itemgetter('number'))
        
                
    def popChannels(self, type: str, channels: list=[]) -> list:
        return [self.channelDATA['channels'].pop(self.channelDATA['channels'].index(citem)) for citem in list([c for c in channels if c.get('type') == type])]
        
        
    def getChannelbyID(self, id: str) -> list:
        channels = self.getChannels()
        return list([c for c in channels if c.get('id') == id])
        
        
    def getType(self, type: str):
        channels = self.getChannels()
        return list([citem for citem in channels if citem.get('type') == type])


    def sortChannels(self, channels: list) -> list:
        try:    return sorted(channels, key=itemgetter('number'))
        except: return channels


    def setChannels(self, channels: list=[]) -> bool:
        self.channelDATA['channels'] = channels
        SETTINGS.setSetting('Open_Manager','[B]%s[/B] Channels'%(len(channels)))
        PROPERTIES.setChannels(len(channels)>0)
        return self._save()


    def getImports(self) -> list:
        return self.channelDATA.get('imports',[])
        
        
    def setImports(self, data: list=[]) -> bool:
        self.channelDATA['imports'] = data
        return self.setChannels(self.getChannels())

         
    def clearChannels(self):
        self.channelDATA['channels'] = []
         

    def delChannel(self, citem: dict={}) -> bool:
        if isinstance(citem,list): return any([self.delChannel(channel) for channel in citem])
        self.log('delChannel,[%s]'%(citem['id']), xbmc.LOGINFO)
        idx, channel = self.findChannel(citem)
        if idx is not None: self.channelDATA['channels'].pop(idx)
        return True
    
    
    def addChannel(self, citem: dict={}) -> bool:
        if isinstance(citem,list): return any([self.addChannel(channel) for channel in citem])
        channels = self.getChannels()
        idx, channel = self.findChannel(citem, channels)
        if idx is not None:
            channels[idx].update(citem)
            self.log('addChannel, [%s] updating channel %s'%(citem["id"],citem["name"]), xbmc.LOGINFO)
            self.channelDATA['channels'] = channels
        else:
            self.log('addChannel, [%s] adding channel %s'%(citem["id"],citem["name"]), xbmc.LOGINFO)
            self.channelDATA.setdefault('channels',[]).append(citem)
        return True
        
        
    def findChannel(self, citem: dict={}, channels: list=[]) -> tuple:
        if len(channels) == 0: channels = self.getChannels()
        return tuple(next(((idx, eitem) for idx, eitem in enumerate(channels) if citem.get('id') == (eitem.get('id') or str(random.random()))), (None,{})))
        