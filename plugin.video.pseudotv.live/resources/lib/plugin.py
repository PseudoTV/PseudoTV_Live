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
from resources.lib.jsonrpc     import JSONRPC 
from resources.lib.rules       import RulesList, ChannelList

class Plugin:
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
        self.jsonRPC    = JSONRPC(inherited=self)
        self.ruleList   = RulesList()
        self.runActions = self.ruleList.runActions
        self.chanList   = self.ruleList.channels
        
        self.seekTLRNC  = SETTINGS.getSettingInt('Seek_Tolerance')
        self.seekTHLD   = SETTINGS.getSettingInt('Seek_Threshold%')
        
        
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
        poolit(_parseBroadcast)(self.jsonRPC.getPVRBroadcasts(channelItem.get('channelid')))
        return channelItem


    @cacheit(expiration=datetime.timedelta(seconds=OVERLAY_DELAY),checksum=getInstanceID(),json_data=True)#channel-surfing buffer
    def matchChannel(self, chname, id, radio=False):
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
        return {}
        

    def getChannelID(self, chname, id, radio=False): # Convert PseudoTV Live id into a Kodi PVR channelID
        channel = self.matchChannel(chname, id, radio)
        chmatch = {'channelid':channel.get('channelid',-1),'uniqueid':channel.get('uniqueid',-1)}
        self.log('getChannelID, id = %s, chmatch =  %s'%(id,chmatch))
        return chmatch
        

    def buildChannel(self, chname, id, isPlaylist=False, radio=False):
        channelItem  = self.getChannelID(chname, id, radio)
        channelItem['isPlaylist'] = isPlaylist
        channelLimit = PAGE_LIMIT if isPlaylist else 2
        channelItem['citem']      = {'name':chname,'id':id,'radio':radio}
        channelItem['callback']   = 'pvr://channels/tv/All%20channels/pvr.iptvsimple_{id}.pvr'.format(id=(channelItem.get('uniqueid')))
        return self.parseBroadcasts(channelItem)
    
    
    def contextPlay(self, writer={}, isPlaylist=False):
        found     = False
        listitems = [xbmcgui.ListItem()] #empty listitem required to pass failed playback.

        if writer.get('citem',{}): 
            found = True
            citem = writer.get('citem')
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
                
                if round(nowitem['progress']) <= self.seekTLRNC or round(nowitem['progresspercentage']) > self.seekTHLD:
                    self.log('contextPlay, progress start at the beginning')
                    nowitem['progress']           = 0
                    nowitem['progresspercentage'] = 0
                    
                if (nowitem['progress'] > 0 and nowitem['runtime'] > 0):
                    self.log('contextPlay, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((nowitem['runtime'] * 60),nowitem['progress']))
                    liz.setProperty('totaltime'  , str((nowitem['runtime'] * 60))) #secs
                    liz.setProperty('resumetime' , str(nowitem['progress']))       #secs
                    liz.setProperty('startoffset', str(nowitem['progress']))       #secs
                
                # lastitem  = nextitems.pop(-1)
                # lastwrite = getWriter(lastitem.get('writer',''))
                # lastwrite['file']  = PVR_URL.format(addon=ADDON_ID,name=quoteString(citem['name']),id=quoteString(citem['id']),radio=str(citem['radio']))#pvritem.get('callback')
                # lastitem['writer'] = setWriter(LANGUAGE(30161),lastwrite)
                # nextitems.append(lastitem) #insert pvr callback
                
                listitems = [liz]
                listitems.extend(poolit(self.buildWriterItem)(nextitems))
            else:
                liz = self.dialog.buildItemListItem(writer)
                liz.setProperty('pvritem', dumpJSON(pvritem))
                listitems = [liz]
                
            for idx,lz in enumerate(listitems):
                path = lz.getPath()
                # if isStack(path): lz.setPath(translateStack(path))#translate vfs stacks to local..
                self.channelPlaylist.add(lz.getPath(),lz,idx)
                xbmc.sleep(100)
                
            self.log('contextPlay, Playlist size = %s'%(self.channelPlaylist.size()))
            if isPlaylistRandom(): self.channelPlaylist.unshuffle()
            return self.player.play(self.channelPlaylist, startpos=0)

        else: return self.playbackError(id, playCount)
        return xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitems[0])
        
        
    def playChannel(self, name, id, isPlaylist=False):
        self.log('playChannel, id = %s, isPlaylist = %s'%(id,isPlaylist))
        found     = False
        listitems = [xbmcgui.ListItem()] #empty listitem required to pass failed playback.
        
        playCount = (SETTINGS.getCacheSetting('PLAYCHANNEL_ATTEMPT_COUNT',checksum=id) or 0)
        playCount+=1
        SETTINGS.setCacheSetting('PLAYCHANNEL_ATTEMPT_COUNT',playCount,checksum=id,life=datetime.timedelta(seconds=(OVERLAY_DELAY)))
        
        if PROPERTIES.getProperty('currentChannel') != id: 
            PROPERTIES.setProperty('currentChannel',id)

        pvritem   = self.buildChannel(name, id, isPlaylist)
        nowitem   = pvritem.get('broadcastnow',{})  # current item
        nextitems = pvritem.get('broadcastnext',[]) # upcoming items
        del nextitems[PAGE_LIMIT:]# list of upcoming items, truncate for speed.
                    
        try:    pvritem['citem'].update(self.chanList.getChannel(id)[0]) #update pvritem citem with comprehensive meta from channels.json
        except: pvritem['citem'].update(getWriter(nowitem.get('writer',{})).get('citem',{})) #update pvritem citem with stale meta from xmltv
        citem = pvritem['citem']

        if nowitem:
            found = True
            if nowitem.get('broadcastid',random.random()) != SETTINGS.getCacheSetting('PLAYCHANNEL_LAST_BROADCAST_ID',checksum=id):# and not nowitem.get('isStack',False): #new item to play
                nowitem = self.runActions(RULES_ACTION_PLAYBACK, citem, nowitem, inherited=self)
                timeremaining = ((nowitem['runtime'] * 60) - nowitem['progress'])
                self.log('playChannel, runtime = %s, timeremaining = %s'%(nowitem['progress'],timeremaining))
                self.log('playChannel, progress = %s, Seek_Tolerance = %s'%(nowitem['progress'],self.seekTLRNC))
                self.log('playChannel, progresspercentage = %s, Seek_Threshold = %s'%(nowitem['progresspercentage'],self.seekTHLD))
                
                if round(nowitem['progress']) <= self.seekTLRNC: # near start or new content, play from the beginning.
                    nowitem['progress']           = 0
                    nowitem['progresspercentage'] = 0
                    self.log('playChannel, progress start at the beginning')
                    
                elif round(nowitem['progresspercentage']) > self.seekTHLD: # near end, avoid callback; override nowitem and queue next show.
                    self.log('playChannel, progress near the end, queue nextitem')
                    nowitem = nextitems.pop(0) #remove first element in nextitems keep playlist order
                
            # elif nowitem.get('isStack',False):
                # pvritem = PROPERTIES.getPropertyDict('Last_Played_PVRItem')
                # path = popStack(nowitem.get('playing'))
                # nowitem['isStack'] = isStack(path)
                # nowitem['playing'] = path
                # nwriter = getWriter(nowitem.get('writer',{}))
                # nwriter['file'] = path
                # nowitem['writer'] = setWriter(LANGUAGE(30161),nwriter)
                # self.log('playChannel, stack detected advancing...')
                
            elif round(nowitem['progresspercentage']) > self.seekTHLD:
                self.log('playChannel, progress near the end playing nextitem')
                nowitem = nextitems.pop(0)
                
            elif playCount > 2: 
                found = False
                self.playbackError(id, playCount)
                
            if found:
                writer = getWriter(nowitem.get('writer',{}))
                liz    = self.dialog.buildItemListItem(writer)
                path   = liz.getPath()
                self.log('playChannel, nowitem = %s\ncitem = %s\nwriter = %s'%(nowitem,citem,writer))
                SETTINGS.setCacheSetting('PLAYCHANNEL_LAST_BROADCAST_ID',nowitem.get('broadcastid',random.random()),checksum=id,life=datetime.timedelta(seconds=OVERLAY_DELAY-1))
                
                if (nowitem['progress'] > 0 and nowitem['runtime'] > 0):
                    self.log('playChannel, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((nowitem['runtime'] * 60),nowitem['progress']))
                    liz.setProperty('totaltime'  , str((nowitem['runtime'] * 60))) #secs
                    liz.setProperty('resumetime' , str(nowitem['progress']))       #secs
                    liz.setProperty('startoffset', str(nowitem['progress']))       #secs
                    
                    file = writer.get('originalfile','')
                    # if isStack(path) and not hasStack(path,file):
                        # self.log('playChannel, nowitem isStack with path = %s'%(path))
                        # liz.setPath(translateStack(stripPreroll(path, file)))#remove pre-roll stack from seek offset video, translate vfs to local.
                        
                # elif isStack(path):
                    # liz.setPath(translateStack(path))#translate vfs stacks to local..
                self.log('playChannel, playing path = %s'%(liz.getPath()))
                
                # if nextitems:  #hijack last element in playlist, insert pvr callback to last item. experimental! 
                    # lastitem  = nextitems.pop(-1)
                    # lastwrite = getWriter(lastitem.get('writer',''))
                    # lastwrite['file']  = PVR_URL.format(addon=ADDON_ID,name=quoteString(name),id=quoteString(id),radio=str(False))
                    # lastitem['writer'] = setWriter(LANGUAGE(30161),lastwrite)
                    # nextitems.append(lastitem)

                nowitem['playing']       = liz.getPath()
                # nowitem['isStack']       = isStack(nowitem['playing'])
                pvritem['broadcastnow']  = nowitem
                pvritem['broadcastnext'] = nextitems
                liz.setProperty('pvritem',dumpJSON(pvritem))
                                
                # if nowitem['isStack']:
                    # PROPERTIES.setPropertyDict('Last_Played_PVRItem',pvritem)
                # else:
                    # PROPERTIES.clearProperty('Last_Played_PVRItem')
                    
                self.channelPlaylist.clear()
                xbmc.sleep(100)
                    
                listitems = [liz]
                listitems.extend(poolit(self.buildWriterItem)(nextitems))
                for idx,lz in enumerate(listitems):
                    self.channelPlaylist.add(lz.getPath(),lz,idx)
                    xbmc.sleep(100)
                    
                if isPlaylist:
                    self.log('playChannel, Playlist size = %s'%(self.channelPlaylist.size()))
                    if isPlaylistRandom(): self.channelPlaylist.unshuffle()
                    self.player.play(self.channelPlaylist)
                    xbmc.sleep(100)
                    if isBusyDialog(): xbmc.executebuiltin("Action(Back)")#todo debug busy spinner from leftover waiting for setResolvedUrl.
                    return
                
        else: self.playbackError(id, playCount)
        return xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitems[0])
        
        
    def playRadio(self, name, id):
        self.log('playRadio, id = %s'%(id))
        pvritem = self.buildChannel(name, id, isPlaylist=True, radio=True)
        nowitem = pvritem.get('broadcastnow',{})  # current item

        try:    pvritem['citem'].update(self.chanList.getChannel(id)[0]) #update pvritem citem with comprehensive meta from channels.json
        except: pvritem['citem'].update(getWriter(nowitem.get('writer',{})).get('citem',{})) #update pvritem citem with stale meta from xmltv
        citem = pvritem['citem']
                        
        playCount = (SETTINGS.getCacheSetting('PLAYCHANNEL_ATTEMPT_COUNT',checksum=id) or 0)
        playCount+=1
        SETTINGS.setCacheSetting('PLAYCHANNEL_ATTEMPT_COUNT',playCount,checksum=id,life=datetime.timedelta(seconds=(OVERLAY_DELAY)))
        
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
                
                # nowitem   = nextitems.pop(0)
                # lastitem  = nextitems.pop(-1)
                # lastwrite = getWriter(lastitem.get('writer',''))
                # lastwrite['file']  = PVR_URL.format(addon=ADDON_ID,name=quoteString(name),id=quoteString(id),radio=str(True))
                # lastitem['writer'] = setWriter(LANGUAGE(30161),lastwrite)
                # nextitems.append(lastitem) #insert pvr callback
                
                liz = self.dialog.buildItemListItem(nowitem, mType='music')
                liz.setProperty('pvritem', dumpJSON(pvritem))          
                
                listitems = [liz]
                listitems.extend(poolit(self.buildWriterItem)(nextitems,kwargs={'mType':'song'}))
                for idx,lz in enumerate(listitems): 
                    self.channelPlaylist.add(lz.getPath(),lz,idx)
                    xbmc.sleep(100)
                    
                self.log('playRadio, Playlist size = %s'%(self.channelPlaylist.size()))
                if not isPlaylistRandom(): self.channelPlaylist.shuffle()
                return self.player.play(self.channelPlaylist)
        else: return self.playbackError(id, playCount)
        return xbmcplugin.setResolvedUrl(int(self.sysARG[1]), False, xbmcgui.ListItem())


    def playVOD(self, name, id):
        path = decodeString(id)
        self.log('playVOD, path = %s'%(path))
        liz = xbmcgui.ListItem(name,path=path)
        liz.setProperty("IsPlayable","true")
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)


    def playbackError(self, id, attempt=0):
        self.log('playbackError, id = %s, attempt = %s'%(id,attempt))
        waitTime = OVERLAY_DELAY
        if attempt == 3: 
            if brutePVR(override=True): setInstanceID()
        else: waitTime = floor(OVERLAY_DELAY//4)
        with busy_dialog():
            self.dialog.notificationWait(LANGUAGE(30059),wait=waitTime)
        xbmc.executebuiltin('PlayMedia(%s%s)'%(self.sysARG[0],self.sysARG[2]))