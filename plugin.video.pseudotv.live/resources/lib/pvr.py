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


class PVR:
    def __init__(self, cache=None):
        self.log('__init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
        self.jsonRPC = JSONRPC(self.cache)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def matchPVRPath(self, channelid=-1):
        self.log('matchPVRPath, channelid = %s'%(channelid))
        pvrPaths = ['pvr://channels/tv/%s/'%(urllib.parse.quote(ADDON_NAME)),
                    'pvr://channels/tv/All%20channels/',
                    'pvr://channels/tv/*']
                    
        for path in pvrPaths:
            json_response = self.jsonRPC.getDirectory('{"directory":"%s","properties":["file"]}'%(path),cache=False).get('result',{}).get('files',[])
            if json_response: break 
            
        if json_response:
            item = list(filter(lambda k:k.get('id',-1) == channelid, json_response))
            if item: 
                self.log('matchPVRPath, path found: %s'%(item[0].get('file','')))
                return item[0].get('file','')
        self.log('matchPVRPath, path not found \n%s'%(dumpJSON(json_response)))
        return ''
        
         
    def matchPVRChannel(self, chname, id, radio=False): # Convert PseudoTV Live channelID into a Kodi channelID for playback
        log('matchPVRChannel, chname = %s, id = %s'%(chname,id))
        channels = self.jsonRPC.getPVRChannels(radio)
        for channel in channels:
            for key in ['broadcastnow','broadcastnext']:
                writer = channel.get(key,{}).get('writer','')
                if getWriter(writer).get('data',{}).get('id','') == id:
                    log('matchPVRChannel, match found! writer = %s'%(writer))
                    return channel
        log('matchPVRChannel, no match found! \n%s'%(dumpJSON(channels)))
        return None
        
        
    def fillPVRbroadcasts(self, channelItem):
        self.log('fillPVRbroadcasts')
        channelItem['broadcastnext'] = []
        json_response = self.jsonRPC.getPVRBroadcasts(channelItem['channelid'])
        for idx, item in enumerate(json_response):
            if item['progresspercentage'] == 100: continue
            elif item['progresspercentage'] > 0: 
                broadcastnow = channelItem['broadcastnow']
                channelItem.pop('broadcastnow')
                item.update(broadcastnow) 
                channelItem['broadcastnow'] = item
            elif item['progresspercentage'] == 0: 
                channelItem['broadcastnext'].append(item)
        self.log('fillPVRbroadcasts, found broadcastnext = %s'%(len(channelItem['broadcastnext'])))
        return channelItem
        
        
    def getPVRposition(self, chname, id, radio=False, isPlaylist=False):
        self.log('getPVRposition, chname = %s, id = %s, isPlaylist = %s'%(chname,id,isPlaylist))
        channelItem = self.matchPVRChannel(chname, id, radio)
        if not channelItem: return {}
        if isPlaylist:
            channelItem = self.fillPVRbroadcasts(channelItem)
        else: 
            channelItem['broadcastnext'] = [channelItem.get('broadcastnext',[])]
        return channelItem