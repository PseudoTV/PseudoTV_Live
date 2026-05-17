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

# -*- coding: utf-8 -*-

from globals    import *
from multiroom  import Multiroom

#todo create dataclasses for all jsons
# https://pypi.org/project/dataclasses-json/
class Channels(object):
    
    def __init__(self, key=None, writable=False):
        if key is None: key = CHANNELAUTOTUNE_KEY if SETTINGS.getSettingBool('Enable_Autotune') else CHANNEL_KEY
        self.writable    = writable
        self.channelDATA = FileAccess.getJSON(CHANNELFLE_DEFAULT)
        self.channelKEY  = f'{key}.{self.channelDATA.get("version",ADDON_VERSION)}'
        self.channelTEMP = self.channelDATA.get('channels',[{}]).pop(0)
        self.channelRULE = self.channelTEMP.pop('rules')
        self.channelTEMP['rules'] = {}
        self.channelDATA.update(self._load())
        self.channelDATA_OLD = self.channelDATA.copy()
        self.log(f'__init__ channelKEY = {self.channelKEY}')
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: [%s] %s'%(self.__class__.__name__,self.channelKEY,msg),level)


    def _load(self) -> dict:
        channelDATA = (SETTINGS.getCacheSetting(self.channelKEY, FileAccess._getMD5(self.channelKEY)) or {})
        if CHANNELAUTOTUNE_KEY not in self.channelKEY: SETTINGS.setSetting('Open_Manager','[B]%s[/B] Channels'%(len(channelDATA.get('channels',[]))))
        self.log('_load channels = %s'%(len(channelDATA.get('channels',[]))))
        return channelDATA
    
        
    def _verify(self, channels: list=[]):
        for idx, citem in enumerate(channels):
            if not citem.get('name') or not citem.get('id') or len(citem.get('path',[])) == 0:
                self.log('[%s] _verify in-valid\n%s'%(citem.get('id'),citem))
                continue
            yield citem
                
                
    def _save(self, expiration=-1) -> bool:
        if self.writable:
            if CHANNELAUTOTUNE_KEY in self.channelKEY: expiration = datetime.timedelta(days=MAX_GUIDEDAYS)
            self.log('_save channels = %s, expiration = %s'%(len(self.channelDATA['channels']),expiration))
            return SETTINGS.setCacheSetting(self.channelKEY, self.channelDATA, FileAccess._getMD5(self.channelKEY), expiration)
            

    def getTemplate(self) -> dict: 
        return self.channelTEMP.copy()
        
        
    def getChannels(self) -> list:
        self.log('getChannels channels = %s'%(len(self.channelDATA.get('channels',[]))))
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
        self.channelDATA['name']     = PROPERTIES.getFriendlyName()
        self.channelDATA['uuid']     = SETTINGS.getMYUUID()
        self.channelDATA['channels'] = self.sortChannels(list(self._verify(channels)))
        if len(self.channelDATA['channels']) > 0: PROPERTIES.setHasChannels(self.channelKEY, self.channelDATA)
        if CHANNELAUTOTUNE_KEY not in self.channelKEY: SETTINGS.setSetting('Open_Manager','[B]%s[/B] Channels'%(len(self.channelDATA['channels'])))
        self.log('setChannels channels = %s'%(len(self.channelDATA.get('channels',[]))))
        return self._save()
        

    def getImportPlugins(self) -> list:
        return self.channelDATA.get('plugins',[])
        
        
    def setImportPlugins(self, data: list=[]) -> bool:
        self.channelDATA['plugins'] = data
        return self._save()
         
         
    def clrChannels(self):
        self.channelDATA['channels'] = []
        

    def delChannel(self, citem: dict={}) -> bool:
        if isinstance(citem,list): return any([self.delChannel(channel) for channel in citem])
        try: 
            self.channelDATA['channels'].pop(self.findChannel(citem)[0])
            self.log('[%s] delChannel channel deleted!'%(citem['id']), xbmc.LOGINFO)
            return True
        except Exception: pass
    
    
    def addChannel(self, citem: dict={}) -> bool:
        if isinstance(citem,list): return any([self.addChannel(channel) for channel in citem])
        self.delChannel(citem)
        self.log('[%s] addChannel adding channel %s'%(citem["id"],citem["name"]), xbmc.LOGINFO)
        self.channelDATA.setdefault('channels',[]).append(Globals._cleanGroups(citem))
        return True
        
        
    def findChannel(self, citem: dict={}, channels=None) -> tuple:
        if channels is None: channels = self.channelDATA['channels']
        if citem.get('id') is None: citem['id'] = getChannelID(citem.get('name'), citem.get('path'), citem.get('number'), uuid=self.channelDATA.get('uuid'))
        return tuple(next(((idx, eitem) for idx, eitem in enumerate(channels) if citem['id'] == eitem.get('id', str(random.random()))), (None,{})))
                    
                    
    def _channelManager(self):
        with FileAccess.stream(MANAGERPATH, "r") as fle:
            html_content = fle.read()
        html_content = html_content.replace("{{ channel_limit }}", str(CHANNEL_LIMIT))
        html_content = html_content.replace("{{ media_loc }}"    , MEDIA_LOC)
        html_content = html_content.replace("{{ remote_host }}"  , PROPERTIES.getRemoteHost())
        return html_content.encode(encoding=DEFAULT_ENCODING)
        