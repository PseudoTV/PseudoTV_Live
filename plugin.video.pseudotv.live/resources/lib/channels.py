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

from typing import Any, Generator, Optional, Union

from variables    import *
from multiroom  import Multiroom

#todo create dataclasses for all jsons
# https://pypi.org/project/dataclasses-json/
class Channels(object):
    _lock = RLock()
    
    def __init__(self, key: str, writable: bool = False):
        self.writable    = writable
        self.channelDATA = FileAccess.getJSON(CHANNELFLE_DEFAULT)
        # Ensure name fields are strings (JSON parses "24" as int)
        for ch in self.channelDATA.get('channels', []):
            if 'name' in ch and not isinstance(ch['name'], str):
                ch['name'] = str(ch['name'])
        self.channelKEY  = f'{key}.{self.channelDATA.get("version",ADDON_VERSION)}'
        channels = self.channelDATA.get('channels') or []
        self.channelTEMP = channels.pop(0) if channels else {}
        self.channelRULE = self.channelTEMP.pop('rules', {})
        self.channelTEMP['rules'] = {}
        self.channelDATA.update(self._load())
        self.log(f'__init__ channelKEY = {self.channelKEY}')
        
        
    def __enter__(self) -> 'Channels':
        return self


    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]):
        try:
            if self.writable: self._save()
        except Exception as e: self.log("__exit__ save failed: %s" % e, xbmc.LOGDEBUG)
            
            
    def __del__(self):
        try:
            if getattr(self, 'writable', False): self._save()
            self.log('__del__, writable = %s' % (getattr(self, 'writable', False)))
        except Exception as e: 
            self.log("__del__ save failed: %s" % e, xbmc.LOGDEBUG)
        
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: [%s] %s'%(self.__class__.__name__,self.channelKEY,msg),level)


    def _load(self) -> dict:
        channelDATA = Globals.settings.getCacheSetting(self.channelKEY, FileAccess._getMD5(self.channelKEY), default={})
        if CHANNELAUTOTUNE_KEY not in self.channelKEY:
            verified = len(list(self._verify(channelDATA.get('channels',[]))))
            Globals.settings.setSetting('Open_Manager','[B]%s[/B] Channels'%(verified))
        self.log('_load, channels=%d' % len(channelDATA.get('channels',[])))
        return channelDATA
    
        
    def _verify(self, channels: list = []) -> Generator[dict, None, None]:
        """Filter and yield only valid channel items with required fields."""
        for idx, citem in enumerate(channels):
            if not citem.get('name') or not citem.get('id') or len(citem.get('path',[])) == 0:
                self.log('[%s] _verify in-valid\n%s'%(citem.get('id'),citem))
                continue
            yield citem
                
                
    def _save(self, expiration=-1) -> bool:
        if self.writable:
            if CHANNELAUTOTUNE_KEY in self.channelKEY:
                expiration = datetime.timedelta(days=MAX_GUIDEDAYS)
                FileAccess.setJSON(CHANNEL_EXPORT_FLE,self.channelDATA)
            self.log('_save, channels=%d, expiration=%s' % (len(self.channelDATA['channels']), expiration))
            return Globals.settings.setCacheSetting(self.channelKEY, self.channelDATA, FileAccess._getMD5(self.channelKEY), expiration)
            


    def getTemplate(self) -> dict: 
        return self.channelTEMP.copy()
        
        
    def getChannels(self) -> list:
        with self._lock:
            channelDATA = (self.channelDATA or FileAccess.getJSON(CHANNELFLE_DEFAULT))
            self.log('getChannels, channels=%d' % len(channelDATA.get('channels',[])))
            return sorted(channelDATA['channels'], key=itemgetter('number'))
        
        
    def getChannelbyID(self, id: str) -> list:
        return [c for c in self.channelDATA['channels'] if c.get('id') == id]
        
        
    def getChannelbyType(self, type: str) -> list:
        return [citem for citem in self.channelDATA['channels'] if citem.get('type') == type]


    def sortChannels(self, channels: list) -> list:
        try:              return sorted(channels, key=itemgetter('number'))
        except Exception as e: 
            self.log(f'sortChannels, failed to sort by number: {e}', xbmc.LOGDEBUG)
            return channels

    
    def setChannels(self, channels: Optional[list] = None) -> bool:
        with self._lock:
            if channels is None: channels = self.channelDATA['channels']
            self.channelDATA['name']     = Globals.properties.getFriendlyName()
            self.channelDATA['uuid']     = Globals.settings.getMYUUID()
            self.channelDATA['channels'] = self.sortChannels(list(self._verify(channels)))
            if len(self.channelDATA['channels']) > 0: Globals.properties.setHasChannels(self.channelKEY, self.channelDATA)
            if CHANNELAUTOTUNE_KEY not in self.channelKEY: Globals.settings.setSetting('Open_Manager','[B]%s[/B] Channels'%(len(self.channelDATA['channels'])))
            self.log('setChannels, channels=%d' % len(self.channelDATA.get('channels',[])))
        return self._save()
        
        
    def getImportPlugins(self) -> list:
        return self.channelDATA.get('plugins',[])
        
        
    def setImportPlugins(self, data: list=[]) -> bool:
        self.channelDATA['plugins'] = data
        return self._save()
         
         
    def clrChannels(self):
        self.channelDATA['channels'] = []
        


    def delChannel(self, citem: Optional[Union[dict, list]] = None) -> bool:
        """Delete channel(s) by ID or dict. Handles single dict or list of dicts."""
        if citem is None: citem = {}
        if isinstance(citem,list): return any(self.delChannel(channel) for channel in citem)
        with self._lock:
            try: 
                self.channelDATA['channels'].pop(self.findChannel(citem)[0])
                self.log('[%s] delChannel channel deleted!'%(citem['id']), xbmc.LOGINFO)
                return True
            except Exception as e: self.log('[%s] delChannel failed: %s'%(citem.get('id',''), e), xbmc.LOGDEBUG)
    
    
    def addChannel(self, citem: Union[dict, list] = {}) -> bool:
        """Add a channel or list of channels, removing duplicates first."""
        if isinstance(citem,list): return any(self.addChannel(channel) for channel in citem)
        with self._lock:
            self.delChannel(citem)
            self.log('[%s] addChannel adding channel %s'%(citem["id"],citem["name"]), xbmc.LOGINFO)
            self.channelDATA.setdefault('channels',[]).append(Globals._cleanGroups(citem))
            return True
        
        
    def findChannel(self, citem: dict = {}, channels: Optional[list] = None) -> tuple:
        """Find a channel by ID, returning (index, channel) tuple or (None, {}) if not found."""
        if channels is None: channels = self.channelDATA['channels']
        if citem.get('id') is None: citem['id'] = Globals._getChannelID(citem.get('name'), citem.get('path'), citem.get('number'), uuid=self.channelDATA.get('uuid'))
        return tuple(next(((idx, eitem) for idx, eitem in enumerate(channels) if citem['id'] == eitem.get('id', '')), (None,{})))
                    
                    
    def _channelManager(self) -> bytes:
        """Load and return the channel manager HTML template with placeholders replaced."""
        with FileAccess.stream(MANAGERPATH, "r") as fle:
            html_content = fle.read()
        html_content = html_content.replace("{{ channel_limit }}", str(CHANNEL_LIMIT))
        html_content = html_content.replace("{{ media_loc }}"    , MEDIA_LOC)
        html_content = html_content.replace("{{ remote_host }}"  , Globals.properties.getRemoteHost())
        return html_content.encode(encoding=DEFAULT_ENCODING)
        