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

# -*- coding: utf-8 -*-

from globals    import *
#todo create dataclasses for all jsons
# https://pypi.org/project/dataclasses-json/
class Channels:
             
    def __init__(self):
        self.channelDATA = getJSON(CHANNELFLE_DEFAULT)
        self.channelTEMP = getJSON(CHANNEL_ITEM)
        self.channelDATA.update(self._load())
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _load(self, file=CHANNELFLEPATH) -> dict:
        channelDATA = getJSON(file)
        self.log('_load, channels = %s'%(len(channelDATA.get('channels',[]))))
        return channelDATA
    
    
    def _verify(self, channels: list=[]):
        for idx, citem in enumerate(self.channelDATA.get('channels',[])):
            if not citem.get('name') or not citem.get('id') or len(citem.get('path',[])) == 0:
                self.log('_verify, in-valid citem [%s]\n%s'%(citem.get('id'),citem))
                continue
            else: yield citem
                
                
    def _save(self, file=CHANNELFLEPATH) -> bool:
        self.channelDATA['uuid']     = SETTINGS.getMYUUID()
        self.channelDATA['channels'] = self.sortChannels(self.channelDATA['channels'])
        self.log('_save, channels = %s'%(len(self.channelDATA['channels'])))
        return setJSON(file,self.channelDATA)

        
    def getTemplate(self) -> dict: 
        return self.channelTEMP.copy()
        
        
    def getChannels(self) -> list:
        return sorted(self.channelDATA['channels'], key=itemgetter('number'))
        
                
    def popChannels(self, type: str, channels: list=[]) -> list:
        return [self.channelDATA['channels'].pop(self.channelDATA['channels'].index(citem)) for citem in list([c for c in channels if c.get('type') == type])]
        
        
    def getCustom(self) -> list:
        channels = self.getChannels()
        return list([citem for citem in channels if citem.get('number') <= CHANNEL_LIMIT])
        
        
    def getAutotuned(self) -> list: 
        channels = self.getChannels()
        return list([citem for citem in channels if citem.get('number') > CHANNEL_LIMIT])
        

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
        if len(channels) == 0: channels = self.channelDATA['channels']
        self.channelDATA['channels'] = channels
        SETTINGS.setSetting('Select_Channels','[B]%s[/B] Channels'%(len(channels)))
        PROPERTIES.setChannels(len(channels)>0)
        return self._save()

    
    def getImports(self) -> list:
        return self.channelDATA.get('imports',[])
        
        
    def setImports(self, data: list=[]) -> bool:
        self.channelDATA['imports'] = data
        return self.setChannels()

         
    def clearChannels(self):
        self.channelDATA['channels'] = []
         

    def delChannel(self, citem: dict={}) -> bool:
        self.log('delChannel,[%s]'%(citem['id']), xbmc.LOGINFO)
        idx, channel = self.findChannel(citem)
        if idx is not None: self.channelDATA['channels'].pop(idx)
        return True
    
    
    def addChannel(self, citem: dict={}) -> bool:
        idx, channel = self.findChannel(citem)
        if idx is not None:
            for key in ['id','rules','number','favorite','logo']: 
                if channel.get(key): citem[key] = channel[key] # existing id found, reuse channel meta.
                
            if citem.get('favorite',False):
                citem['group'].append(LANGUAGE(32019))
                citem['group'] = sorted(set(citem['group']))
                
            self.log('addChannel, [%s] updating channel %s'%(citem["id"],citem["name"]), xbmc.LOGINFO)
            self.channelDATA['channels'][idx] = citem
        else:
            self.log('addChannel, [%s] adding channel %s'%(citem["id"],citem["name"]), xbmc.LOGINFO)
            self.channelDATA.setdefault('channels',[]).append(citem)
        return True
        
        
    def findChannel(self, citem: dict={}, channels: list=[]) -> tuple:
        if len(channels) == 0: channels = self.getChannels()
        for idx, eitem in enumerate(channels):
            if citem.get('id') == eitem.get('id',str(random.random())):
                return idx, eitem
        return None, {}
            
            
    def findAutotuned(self, citem: dict={}, channels: list=[]) -> tuple:
        if len(channels) == 0: channels = self.getAutotuned()
        for idx, eitem in enumerate(channels):
            if (citem.get('id') == eitem.get('id',str(random.random()))) or (citem.get('type') == eitem.get('type',str(random.random())) and citem.get('name').lower() == eitem.get('name',str(random.random())).lower()):
                return idx, eitem
        return None, {}
            
