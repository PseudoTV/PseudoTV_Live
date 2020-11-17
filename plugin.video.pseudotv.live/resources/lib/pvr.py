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
        json_response = self.jsonRPC.getDirectory('{"directory":"%s","properties":["file"]}'%('pvr://channels/tv/%s/'%(urllib.parse.quote(ADDON_NAME))),cache=False).get('result',{}).get('files',[]) #get group list
        if not json_response: 
            json_response = self.jsonRPC.getDirectory('{"directory":"pvr://channels/tv/All%20channels/","properties":["file"]}',cache=False).get('result',{}).get('files',[]) #get all tv
        if json_response:
            for path in json_response:
                if channelid == path['id']:
                    self.log('matchPVRPath, found path = %s'%(path['file']))
                    return path['file']
        self.log('matchPVRPath, path not found \n%s'%(dumpJSON(json_response)))
        return ''
        
         
    def matchPVRChannel(self, chname, id, radio=False): # Convert PseudoTV Live channelID into a Kodi channelID for playback
        channels = self.jsonRPC.getPVRChannels(radio)
        for item in channels:
            writer = item.get('broadcastnow',{}).get('writer','')
            if not writer: continue #filter other PVR backends
            try: 
                if getWriter(writer)['data']['id'] == id:
                    log('matchPVRChannel, match found chname = %s, id = %s'%(chname,id))
                    return item
            except: continue
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