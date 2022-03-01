#   Copyright (C) 2022 Lunatixz
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
from resources.lib.cache       import Cache
from resources.lib.concurrency import PoolHelper
from resources.lib.jsonrpc     import JSONRPC 
# from resources.lib.channels    import Channels
from resources.lib.rules       import RulesList

class Plugin:
    currentChannel  = ''
    channelPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    
    def __init__(self, sysARG=sys.argv):
        self.sysARG      = sysARG
        self.channelInfo = {'name'       : xbmc.getInfoLabel('ListItem.ChannelName'),
                            'number'     : xbmc.getInfoLabel('ListItem.ChannelNumber'),
                            'numberlabel': xbmc.getInfoLabel('ListItem.ChannelNumberLabel'),
                            'uniqueid'   : xbmc.getInfoLabel('ListItem.UniqueID')}
                            
        self.log('__init__, sysARG = %s, channelInfo = %s'%(sysARG,self.channelInfo))
        self.setOffset  = False #todo adv. channel rule to disable seek 
        self.monitor    = xbmc.Monitor()
        self.player     = xbmc.Player()
        self.cache      = Cache()
        self.dialog     = Dialog()
        self.pool       = PoolHelper()
        self.jsonRPC    = JSONRPC(inherited=self)
        # self.channels   = Channels()
        self.runActions = RulesList().runActions
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def buildWriterItem(self, writer, mType='video'):
        if writer.get('writer',''):
            writer = getWriter(writer.get('writer',''))
        return self.dialog.buildItemListItem(writer, mType)


    @cacheit(expiration=datetime.timedelta(seconds=OVERLAY_DELAY),checksum=getInstanceID(),json_data=True)#channel-surfing buffer
    def parseBroadcasts(self, channelItem, channelLimit=PAGE_LIMIT):
        def _parseBroadcast(broadcast):
            if broadcast['progresspercentage'] > 0 and broadcast['progresspercentage'] != 100:
                channelItem['broadcastnow'] = broadcast
            elif broadcast['progresspercentage'] == 0 and len(channelItem.get('broadcastnext',[])) < channelLimit:
                channelItem.setdefault('broadcastnext',[]).append(broadcast)
                
        self.pool.poolList(_parseBroadcast, self.jsonRPC.getPVRBroadcasts(channelItem.get('channelid')))
        return channelItem


    @cacheit(expiration=datetime.timedelta(seconds=OVERLAY_DELAY),checksum=getInstanceID(),json_data=True)#channel-surfing buffer
    def getChannel(self, chname, id, radio=False, second_attempt=False):
        def _matchChannel(channel):
            if channel.get('label') == chname:
                for key in ['broadcastnow', 'broadcastnext']:
                    writer = getWriter(channel.get(key,{}).get('writer',''))
                    if writer.get('citem',{}).get('id','') == id:
                        return channel

        channels = self.jsonRPC.getPVRChannels(radio)
        for channel in channels:
            match = _matchChannel(channel)
            if match: return match
                
        if not second_attempt and brutePVR(override=True): 
            self.dialog.notificationDialog(LANGUAGE(30059))
            return self.getChannel(chname, id, radio, second_attempt=True)
        return {}
        
        
    @cacheit(checksum=getInstanceID(),json_data=True)
    def getChannelID(self, chname, id, radio=False): # Convert PseudoTV Live id into a Kodi channelID
        channel = self.getChannel(chname, id, radio)
        return {'channelid':channel.get('channelid',-1),'uniqueid':channel.get('uniqueid',-1)}
        

    def buildChannel(self, chname, id, isPlaylist=False, radio=False):
        channelItem  = self.getChannelID(chname, id, radio)
        channelItem['isPlaylist'] = isPlaylist
        channelLimit = PAGE_LIMIT if isPlaylist else 2
        channelItem['citem']      = {'name':chname,'id':id,'radio':radio}
        channelItem['callback']   = 'pvr://channels/tv/All%20channels/pvr.iptvsimple_{id}.pvr'.format(id=(channelItem.get('uniqueid')))
        return self.parseBroadcasts(channelItem)
    
    
    def contextPlay(self, writer, isPlaylist=False):
        found     = False
        listitems = [xbmcgui.ListItem()] #empty listitem required to pass failed playback.
        citem     = writer.get('citem',{})
        
        if citem: 
            pvritem = self.buildChannel(citem.get('name'), citem.get('id'), isPlaylist)
            pvritem['citem'].update(citem) #update citem with comprehensive meta
            self.log('contextPlay, citem = %s\npvritem = %s\nisPlaylist = %s'%(citem,pvritem,isPlaylist))
            
            self.channelPlaylist.clear()
            xbmc.sleep(100)
            
            if isPlaylist:
                nowitem   = pvritem.get('broadcastnow',{})  # current item
                nowitem   = self.runActions(RULES_ACTION_PLAYBACK, citem, nowitem, inherited=self)
                nextitems = pvritem.get('broadcastnext',[]) # upcoming items
                nextitems.insert(0,nowitem)

                for pos, nextitem in enumerate(nextitems):
                    if getWriter(nextitem.get('writer',{})).get('file') == writer.get('file'):
                        del nextitems[0:pos]      # start array at correct position
                        del nextitems[PAGE_LIMIT:]# list of upcoming items, truncate for speed.
                        break
                       
                nowitem = nextitems.pop(0)
                writer  = getWriter(nowitem.get('writer',{}))
                liz = self.dialog.buildItemListItem(writer)         
                liz.setProperty('pvritem', dumpJSON(pvritem))       
                
                lastitem  = nextitems.pop(-1)
                lastwrite = getWriter(lastitem.get('writer',''))
                lastwrite['file']  = PVR_URL.format(addon=ADDON_ID,name=quoteString(citem['name']),id=quoteString(citem['id']),radio=str(citem['radio']))#pvritem.get('callback')
                lastitem['writer'] = setWriter(LANGUAGE(30161),lastwrite)
                nextitems.append(lastitem) #insert pvr callback
                
                listitems = [liz]
                listitems.extend(self.pool.poolList(self.buildWriterItem,nextitems))
            else:
                liz = self.dialog.buildItemListItem(writer)
                liz.setProperty('pvritem', dumpJSON(pvritem))
                listitems = [liz]
                
            self.log('contextPlay, listitems size = %s'%(len(listitems)))
            for idx,lz in enumerate(listitems): self.channelPlaylist.add(lz.getPath(),lz,idx)
            if isPlaylistRandom(): self.channelPlaylist.unshuffle()
            return self.player.play(self.channelPlaylist, startpos=0)

        else: self.playbackError()
        return xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitems[0])
        
        
    def playChannel(self, name, id, isPlaylist=False):
        self.log('playChannel, id = %s, isPlaylist = %s'%(id,isPlaylist))
        found     = False
        listitems = [xbmcgui.ListItem()] #empty listitem required to pass failed playback.
        
        if self.currentChannel != id: self.currentChannel = id
        pvritem   = self.buildChannel(name, id, isPlaylist)
        nowitem   = pvritem.get('broadcastnow',{})  # current item
        nextitems = pvritem.get('broadcastnext',[]) # upcoming items
        del nextitems[PAGE_LIMIT:]# list of upcoming items, truncate for speed.
        
        #todo to slow move to parser
        # try:    pvritem['citem'].update(self.channels.getChannel(id)[0]) #update pvritem citem with comprehensive meta from channels.json
        # except: pvritem['citem'].update(getWriter(nowitem.get('writer',{})).get('citem',{})) #update pvritem citem with stale meta from xmltv
        pvritem['citem'].update(getWriter(nowitem.get('writer',{})).get('citem',{})) #update pvritem citem with stale meta from xmltv
        citem = pvritem['citem']
        
        if nowitem:
            found = True
            if nowitem != PROPERTIES.getPropertyDict('Last_Played_NowItem'): #detect loopback
                nowitem   = self.runActions(RULES_ACTION_PLAYBACK, citem, nowitem, inherited=self)
                seekTLRNC = SETTINGS.getSettingInt('Seek_Tolerance')
                seekTHLD  = SETTINGS.getSettingInt('Seek_Threshold%')
                timeremaining = ((nowitem['runtime'] * 60) - nowitem['progress'])
                self.log('playChannel, runtime = %s, timeremaining = %s'%(nowitem['progress'],timeremaining))
                self.log('playChannel, progress = %s, Seek_Tolerance = %s'%(nowitem['progress'],seekTLRNC))
                self.log('playChannel, progresspercentage = %s, Seek_Threshold = %s'%(nowitem['progresspercentage'],seekTHLD))
                
                if round(nowitem['progress']) <= seekTLRNC:
                    nowitem['progress']           = 0
                    nowitem['progresspercentage'] = 0
                    
                elif round(nowitem['progresspercentage']) > seekTHLD: # near end, avoid callback; override nowitem and queue next show.
                    self.log('playChannel, progress near the end, queue nextitem')
                    nowitem = nextitems.pop(0) #remove first element in nextitems keep playlist order.
            else: 
                nowitem = nextitems.pop(0)
                self.log('playChannel, loopback detected advancing queue to nextitem')
            PROPERTIES.setPropertyDict('Last_Played_NowItem',nowitem)
            
            writer = getWriter(nowitem.get('writer',{}))
            liz    = self.dialog.buildItemListItem(writer)
            self.log('playChannel, nowitem = %s\ncitem = %s\nwriter = %s'%(nowitem,citem,writer))
            
            if (nowitem['progress'] > 0 and nowitem['runtime'] > 0):
                self.log('playChannel, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((nowitem['runtime'] * 60),nowitem['progress']))
                liz.setProperty('totaltime'  , str((nowitem['runtime'] * 60))) #secs
                liz.setProperty('resumetime' , str(nowitem['progress']))       #secs
                liz.setProperty('startoffset', str(nowitem['progress']))       #secs
                
                # url  = liz.getPath()
                # file = writer.get('originalfile','')
                # if isStack(url) and not hasStack(url,file):
                    # self.log('playChannel, playing stack with url = %s'%(url))
                    # liz.setPath('stack://%s'%(' , '.join(stripStack(url, file))))#remove pre-roll stack from seek offset video.
            
            if nextitems:  #hijack last element in playlist, insert pvr callback to last item. experimental! 
                lastitem  = nextitems.pop(-1)
                lastwrite = getWriter(lastitem.get('writer',''))
                lastwrite['file']  = PVR_URL.format(addon=ADDON_ID,name=quoteString(name),id=quoteString(id),radio=str(False))
                lastitem['writer'] = setWriter(LANGUAGE(30161),lastwrite)
                nextitems.append(lastitem)
            
            pvritem['broadcastnow']  = nowitem
            pvritem['broadcastnext'] = nextitems
            liz.setProperty('pvritem',dumpJSON(pvritem))
            
            self.channelPlaylist.clear()
            xbmc.sleep(100)
                
            listitems = [liz]
            listitems.extend(self.pool.poolList(self.buildWriterItem,nextitems))
            if isPlaylistRandom(): self.channelPlaylist.unshuffle()
            for idx,lz in enumerate(listitems): self.channelPlaylist.add(lz.getPath(),lz,idx)

            # if isStack(listitems[0].getPath()):
                # url = 'plugin://%s/?mode=vod&name=%s&id=%s&channel=%s&radio=%s'%(ADDON_ID,quoteString(listitems[0].getLabel()),quoteString(encodeString(listitems[0].getPath())),quoteString(citem['id']),'False')
                # self.log('playChannel, isStack calling playVOD url = %s'%(url))
                # listitems[0].setPath(url) #test to see if stacks play better as playmedia.
                # return self.player.play(listitems[0].getPath(),listitems[0])
                
            # listitems = []
            # paths = splitStacks(liz.getPath())
            # paths.append(pvritem['callback'])
            # listitems[0].setPath('stack://%s'%(' , '.join(url)))
            
            # for idx,path in enumerate(paths):
                # print(idx,path)
                # lz = liz
                # lz.setPath(path)
                # listitems.append(lz)
                # print(listitems)
                # self.channelPlaylist.add(path,lz,idx)
            # self.log('playChannel, set callback stack with paths = %s'%(paths))

            if isPlaylist:
                self.log('playChannel, Playlist size = %s'%(self.channelPlaylist.size()))
                self.player.play(self.channelPlaylist)
                xbmc.sleep(100)
                return xbmc.executebuiltin("Action(Back)")#todo debug busy spinner.
                
        else: self.playbackError()
        return xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitems[0])
        
        
    def playRadio(self, name, id):
        self.log('playRadio, id = %s'%(id))
        pvritem = self.buildChannel(name, id, isPlaylist=True, radio=True)
        nowitem = pvritem.get('broadcastnow',{})  # current item
        
        #todo to slow move to parser
        # try:    pvritem['citem'].update(self.channels.getChannel(id)[0]) #update pvritem citem with comprehensive meta from channels.json
        # except: pvritem['citem'].update(getWriter(nowitem.get('writer',{})).get('citem',{})) #update pvritem citem with stale meta from xmltv
        pvritem['citem'].update(getWriter(nowitem.get('writer',{})).get('citem',{})) #update pvritem citem with stale meta from xmltv
        citem = pvritem['citem']
        
        if nowitem:
            nowitem  = self.runActions(RULES_ACTION_PLAYBACK, citem, nowitem, inherited=self)
            writer   = getWriter(nowitem.get('writer',{}))
            path     = writer.get('citem',{}).get('path','')
            
            if isinstance(path,list): path = path[0]
            response = self.jsonRPC.requestList(citem, path, 'music', page=RADIO_ITEM_LIMIT)
            
            if response:
                self.channelPlaylist.clear()
                xbmc.sleep(100)
                
                nextitems = response
                random.shuffle(nextitems)
                
                nowitem   = nextitems.pop(0)
                lastitem  = nextitems.pop(-1)
                lastwrite = getWriter(lastitem.get('writer',''))
                lastwrite['file']  = PVR_URL.format(addon=ADDON_ID,name=quoteString(name),id=quoteString(id),radio=str(True))
                lastitem['writer'] = setWriter(LANGUAGE(30161),lastwrite)
                nextitems.append(lastitem) #insert pvr callback
                
                liz = self.dialog.buildItemListItem(nowitem, mType='music')
                liz.setProperty('pvritem', dumpJSON(pvritem))          
                
                listitems = [liz]
                listitems.extend(self.pool.poolList(self.buildWriterItem,nextitems,kwargs={'mType':'song'}))
                for idx,lz in enumerate(listitems): self.channelPlaylist.add(lz.getPath(),lz,idx)
                if not isPlaylistRandom(): self.channelPlaylist.shuffle()
                self.log('playRadio, Playlist size = %s'%(self.channelPlaylist.size()))
                return self.player.play(self.channelPlaylist)

        else: self.playbackError()
        return xbmcplugin.setResolvedUrl(int(self.sysARG[1]), False, xbmcgui.ListItem())


    def playVOD(self, name, id):
        path = decodeString(id)
        self.log('playVOD, path = %s'%(path))
        liz = xbmcgui.ListItem(name,path=path)
        liz.setProperty("IsPlayable","true")
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)


    def playbackError(self):
        setInstanceID()
        self.dialog.notificationDialog(LANGUAGE(30001))
