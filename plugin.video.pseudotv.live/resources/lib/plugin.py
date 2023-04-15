#   Copyright (C) 2023 Lunatixz
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
from globals     import *
from jsonrpc     import JSONRPC
from rules       import RulesList
from infotagger.listitem import ListItemInfoTag

PAGE_LIMIT = int((REAL_SETTINGS.getSetting('Page_Limit') or "25"))
SEEK_TOLER = SETTINGS.getSettingInt('Seek_Tolerance')
SEEK_THRED = SETTINGS.getSettingInt('Seek_Threshold')

class Plugin:
    def __init__(self, sysARG=sys.argv):
        self.cache   = Cache(mem_cache=True)
        self.jsonRPC    = JSONRPC()
        self.rules      = RulesList()
        self.runActions = self.rules.runActions

        self.sysARG     = sysARG
        self.sysInfo    = {'name'   : BUILTIN.getInfoLabel('ChannelName'),
                           'number' : BUILTIN.getInfoLabel('ChannelNumberLabel'),
                           'path'   : BUILTIN.getInfoLabel('FileNameAndPath'),
                           'fitem'  : decodeWriter(BUILTIN.getInfoLabel('Writer')),
                           'citem'  : decodeWriter(BUILTIN.getInfoLabel('Writer')).get('citem',{})}
        
        self.log('__init__, sysARG = %s\nsysInfo = %s'%(sysARG,self.sysInfo))
        self.channelPlaylist  = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.channelPlaylist.clear()
        xbmc.sleep(100)

                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def buildWriterItem(self, item={}, media='video'):
        return LISTITEMS.buildItemListItem(decodeWriter(item.get('writer','')), media)


    @timeit
    def getCallback(self, chname, id, radio=False, isPlaylist=False):
        self.log('getCallback, id = %s, radio = %s, isPlaylist = %s'%(id,radio,isPlaylist))
        def _matchVFS():
            pvrType = 'radio' if radio else 'tv'
            pvrRoot = "pvr://channels/{dir}/".format(dir=pvrType)
            results = self.jsonRPC.walkListDirectory(pvrRoot,checksum=getInstanceID(),expiration=datetime.timedelta(minutes=OVERLAY_DELAY))[0]
            for dir in [ADDON_NAME,'All channels']: #todo "All channels" may not work with non-English translations!
                for result in results:
                    if result.lower().startswith(quoteString(dir.lower())):
                        pvrPath = os.path.join(pvrRoot,result)
                        SETTINGS.setCacheSetting('pseudopvr', pvrPath)
                        self.log('getCallback: _matchVFS, found dir = %s'%(pvrPath))
                        response = self.jsonRPC.walkListDirectory(pvrPath,append_path=True,checksum=getInstanceID(),expiration=datetime.timedelta(minutes=OVERLAY_DELAY))[1]
                        for pvr in response:
                            if pvr.lower().endswith('%s.pvr'%(id)):
                                self.log('getCallback: _matchVFS, found file = %s'%(pvr))
                                return pvr
            self.log('getCallback: _matchVFS, no callback found!\nresults = %s'%(results))
            
        def _matchJSON():
            pvrType = 'radio' if radio else 'tv'
            results = self.jsonRPC.getDirectory(param={"directory":"pvr://channels/{dir}/".format(dir=pvrType)}, cache=True).get('files',[])
            for dir in [ADDON_NAME,'All channels']: #todo "All channels" may not work with non-English translations!
                for result in results:
                    if result.get('label','').lower().startswith(dir.lower()):
                        SETTINGS.setCacheSetting('pseudopvr', result.get('file'))
                        self.log('getCallback: _matchJSON, found dir = %s'%(result.get('file')))
                        response = self.jsonRPC.getDirectory(param={"directory":result.get('file')},checksum=getInstanceID(),expiration=datetime.timedelta(minutes=OVERLAY_DELAY)).get('files',[])
                        for item in response:
                            if item.get('label','').lower() == chname.lower() and item.get('uniqueid','') == id:
                                self.log('getCallback: _matchJSON, found file = %s'%(item.get('file')))
                                return item.get('file')
            self.log('getCallback: _matchJSON, no callback found!\nresults = %s'%(results))

        if isPlaylist or radio:
            #omega changed pvr paths, requiring double jsonRPC calls to return true file path. maybe more efficient to call through plugin rather than direct pvr. 
            #this breaks "pvr" should only apply to playlists, avoid unnecessary jsonRPC calls which are slow on lowpower devices. 
            callback = '%s%s'%(self.sysARG[0],self.sysARG[2])
        elif PROPERTIES.getPropertyBool('isLowPower') or not PROPERTIES.getPropertyBool('hasPVRSource'):
            callback = _matchVFS()
        else:
            callback = _matchJSON() #use faster jsonrpc on high power devices. requires 'pvr://' json whitelisting.
        if callback is None: return DIALOG.okDialog(LANGUAGE(32133), autoclose=90, usethread=True)
        return callback
        
        
    @timeit
    def matchChannel(self, chname, id, radio=False, isPlaylist=False):
        self.log('matchChannel, id = %s, radio = %s, isPlaylist = %s'%(id,radio,isPlaylist))
        def _match():
            channels = self.jsonRPC.getPVRChannels(radio)
            for channel in channels:
                if channel.get('label').lower() == chname.lower():
                    for key in ['broadcastnow', 'broadcastnext']:
                        chid = decodeWriter(channel.get(key,{}).get('writer','')).get('citem',{}).get('id')
                        if chid == id:
                            channel['broadcastnext'] = [channel.get('broadcastnext',{})]
                            self.log('matchChannel, id = %s, found pvritem = %s'%(id,channel))
                            return channel
        
        cacheName     = 'matchChannel.%s'%(getMD5('%s.%s.%s.%s'%(chname,id,radio,isPlaylist)))
        cacheResponse = self.cache.get(cacheName, checksum=getInstanceID(), json_data=True, default={})
        if not cacheResponse:
            pvritem = _match()
            if not pvritem:
                pvritem = {'channelid':'-1'}
                pvritem['playcount'] = PROPERTIES.getPropertyDict('pendingPVRITEM.%s'%(pvritem.get('channelid','-1'))).get('playcount',0) + 1
                return self.playError(pvritem)
                
            pvritem['isPlaylist'] = isPlaylist
            pvritem['callback']   = self.getCallback(pvritem.get('channel'),pvritem.get('uniqueid'),radio,isPlaylist)
            pvritem['citem']      = (self.sysInfo.get('citem') or decodeWriter(pvritem.get('broadcastnow',{}).get('writer','')).get('citem',{}))
            pvritem['playcount']  = PROPERTIES.getPropertyDict('pendingPVRITEM.%s'%(pvritem.get('channelid','-1'))).get('playcount',0) + 1
          
            if pvritem['playcount'] > 3:
                return self.playError(pvritem)
                
            try:    pvritem['epgurl'] = 'pvr://guide/%s/{starttime}.epg'%(re.compile('pvr://guide/(.*)/', re.IGNORECASE).search(self.sysInfo.get('path')).group(1))
            except: pvritem['epgurl'] = ''#"pvr://guide/1197/2022-02-14 18:22:24.epg"
            if isPlaylist and not radio: pvritem = self.extendProgrammes(pvritem)
            PROPERTIES.setPropertyDict('pendingPVRITEM.%s'%(pvritem.get('channelid','-1')),pvritem)
            cacheResponse = self.cache.set(cacheName, pvritem, checksum=getInstanceID(), expiration=datetime.timedelta(seconds=OVERLAY_DELAY), json_data=True)
        return cacheResponse


    def extendProgrammes(self, pvritem, limit=PAGE_LIMIT):
        channelItem = {}
        def _parseBroadcast(broadcast={}):
            if broadcast.get('progresspercentage',0) > 0 and broadcast.get('progresspercentage',0) != 100:
                channelItem['broadcastnow'] = broadcast
            elif broadcast.get('progresspercentage',0) and len(channelItem.get('broadcastnext',[])) < limit:
                channelItem.setdefault('broadcastnext',[]).append(broadcast)
        
        nextitems = self.jsonRPC.getPVRBroadcasts(pvritem.get('channelid',{}))
        poolit(_parseBroadcast)(nextitems)
        nextitems = channelItem.get('broadcastnext',pvritem['broadcastnext'])
        del nextitems[limit:]# list of upcoming items, truncate for speed.
        pvritem['broadcastnext'] = nextitems
        self.log('extendProgrammes, extend broadcastnext to %s entries'%(len(pvritem['broadcastnext'])))
        return pvritem


    def playVOD(self, name, id):
        path = decodeString(id)
        self.log('playVOD, id = %s\npath = %s'%(id,path))
        liz = xbmcgui.ListItem(name,path=path)
        liz.setProperty("IsPlayable","true")
        self.resolveURL(True, liz)


    def playChannel(self, name, id, isPlaylist=False):
        self.log('playChannel, id = %s, isPlaylist = %s'%(id,isPlaylist))
        with pending_Playback():
            found     = False
            listitems = [xbmcgui.ListItem()] #empty listitem required to pass failed playback.
            pvritem   = self.matchChannel(name,id,False,isPlaylist)
            if pvritem:
                found     = True
                nowitem   = pvritem.get('broadcastnow',{})  # current item
                nextitems = pvritem.get('broadcastnext',[]) # upcoming items
                
                if nowitem.get('broadcastid',random.random()):# != SETTINGS.getCacheSetting('PLAYCHANNEL_LAST_BROADCAST_ID',checksum=id):# and not nowitem.get('isStack',False): #new item to play
                    nowitem = self.runActions(RULES_ACTION_PLAYBACK, pvritem['citem'], nowitem, inherited=self)
                    timeremaining = ((nowitem['runtime'] * 60) - nowitem['progress'])
                    self.log('playChannel, runtime = %s, timeremaining = %s'%(nowitem['progress'],timeremaining))
                    self.log('playChannel, progress = %s, Seek_Tolerance = %s'%(nowitem['progress'],SEEK_TOLER))
                    self.log('playChannel, progresspercentage = %s, Seek_Threshold = %s'%(nowitem['progresspercentage'],SEEK_THRED))
                    
                    if round(nowitem['progress']) <= SEEK_TOLER: # near start or new content, play from the beginning.
                        nowitem['progress']           = 0
                        nowitem['progresspercentage'] = 0
                        self.log('playChannel, progress start at the beginning')
                        
                    elif round(nowitem['progresspercentage']) > SEEK_THRED: # near end, avoid callback; override nowitem and queue next show.
                        self.log('playChannel, progress near the end, queue nextitem')
                        nowitem = nextitems.pop(0) #remove first element in nextitems keep playlist order

                elif round(nowitem['progresspercentage']) > SEEK_THRED:
                    self.log('playChannel, progress near the end playing nextitem')
                    nowitem = nextitems.pop(0)

                writer = decodeWriter(nowitem.get('writer',{}))
                liz    = LISTITEMS.buildItemListItem(writer)
                path   = liz.getPath()
                self.log('playChannel, nowitem = %s\ncitem = %s\nwriter = %s'%(nowitem,pvritem['citem'],writer))
                
                if (nowitem['progress'] > 0 and nowitem['runtime'] > 0):
                    self.log('playChannel, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((nowitem['runtime'] * 60),nowitem['progress']))
                    liz.setProperty('startoffset', str(nowitem['progress'])) #secs
                    infoTag = ListItemInfoTag(liz, 'video')
                    infoTag.set_resume_point({'ResumeTime':nowitem['progress'],'TotalTime':(nowitem['runtime'] * 60)})

                pvritem['broadcastnow']  = nowitem   # current item
                pvritem['broadcastnext'] = nextitems # upcoming items
                liz.setProperty('pvritem',dumpJSON(pvritem))
                listitems = [liz]
                listitems.extend(poolit(self.buildWriterItem)(nextitems))
                PROPERTIES.clearProperty('pendingPVRITEM.%s'%(pvritem.get('channelid','-1')))
                
                if isPlaylist:
                    for idx,lz in enumerate(listitems):
                        self.channelPlaylist.add(lz.getPath(),lz,idx)
                    self.log('playChannel, Playlist size = %s'%(self.channelPlaylist.size()))
                    if isPlaylistRandom(): self.channelPlaylist.unshuffle()
                    return PLAYER.play(self.channelPlaylist)

            else: return self.playError(pvritem)
            self.resolveURL(found, listitems[0])


    def playRadio(self, name, id, isPlaylist=True):
        self.log('playRadio, id = %s'%(id))
        with pending_Playback():
            found     = False
            listitems = [LISTITEMS.getListItem()] #empty listitem required to pass failed playback.
            pvritem   = self.matchChannel(name,id,True,isPlaylist)
            if pvritem:
                found   = True
                nowitem = pvritem.get('broadcastnow',{})  # current item
                if nowitem.get('broadcastid',random.random()):
                    nowitem  = self.runActions(RULES_ACTION_PLAYBACK, pvritem['citem'], nowitem, inherited=self)
                    fileList = [self.jsonRPC.requestList(pvritem['citem'], path, 'music', page=RADIO_ITEM_LIMIT) for path in pvritem['citem'].get('path',[])]#todo replace RADIO_ITEM_LIMIT with cacluated runtime to EPG_HRS
                    fileList = list(interleave(fileList))
                    if len(fileList) > 0:
                        randomShuffle(fileList)
                        listitems = [LISTITEMS.buildItemListItem(item,media='music') for item in fileList]
                        for idx,lz in enumerate(listitems):
                            self.channelPlaylist.add(lz.getPath(),lz,idx)
                            
                        self.log('playRadio, Playlist size = %s'%(self.channelPlaylist.size()))
                        if not isPlaylistRandom(): self.channelPlaylist.shuffle()
                        if PLAYER.isPlayingVideo(): PLAYER.stop()
                        return PLAYER.play(self.channelPlaylist)
            else: return self.playError(pvritem)
            self.resolveURL(False, xbmcgui.ListItem())


    def contextPlay(self, writer={}, isPlaylist=False):
        found     = False
        listitems = [xbmcgui.ListItem()] #empty listitem required to pass failed playback.

        if writer.get('citem',{}): 
            found   = True
            citem   = writer.get('citem')
            pvritem = self.matchChannel(citem.get('name'),citem.get('id'),False,isPlaylist)
            self.log('contextPlay, citem = %s\npvritem = %s\nisPlaylist = %s'%(citem,pvritem,isPlaylist))
            
            if isPlaylist:
                nowitem   = pvritem.get('broadcastnow',{})  # current item
                nowitem   = self.runActions(RULES_ACTION_PLAYBACK, citem, nowitem, inherited=self)
                nextitems = pvritem.get('broadcastnext',[]) # upcoming items
                nextitems.insert(0,nowitem)

                for pos, nextitem in enumerate(nextitems):
                    if decodeWriter(nextitem.get('writer',{})).get('file') == writer.get('file'):
                        del nextitems[0:pos]      # start array at correct position
                        break
                       
                nowitem = nextitems.pop(0)
                writer  = decodeWriter(nowitem.get('writer',{}))
                liz = LISTITEMS.buildItemListItem(writer)
                
                if round(nowitem['progress']) <= SEEK_TOLER or round(nowitem['progresspercentage']) > SEEK_THRED:
                    self.log('contextPlay, progress start at the beginning')
                    nowitem['progress']           = 0
                    nowitem['progresspercentage'] = 0
                    
                if (nowitem['progress'] > 0 and nowitem['runtime'] > 0):
                    self.log('contextPlay, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((nowitem['runtime'] * 60),nowitem['progress']))
                    liz.setProperty('startoffset', str(nowitem['progress'])) #secs
                    infoTag = ListItemInfoTag(liz, 'video')
                    infoTag.set_resume_point({'ResumeTime':nowitem['progress'],'TotalTime':(nowitem['runtime'] * 60)})
                    
                pvritem['broadcastnow']  = nowitem   # current item
                pvritem['broadcastnext'] = nextitems # upcoming items
                liz.setProperty('pvritem',dumpJSON(pvritem))
                listitems = [liz]
                listitems.extend(poolit(self.buildWriterItem)(nextitems))
            else:
                liz = LISTITEMS.buildItemListItem(writer)
                liz.setProperty('pvritem', dumpJSON(pvritem))
                listitems = [liz]
                
            for idx,lz in enumerate(listitems):
                path = lz.getPath()
                self.channelPlaylist.add(lz.getPath(),lz,idx)
                
            PROPERTIES.clearProperty('pendingPVRITEM.%s'%(pvritem.get('channelid','-1')))
            self.log('contextPlay, Playlist size = %s'%(self.channelPlaylist.size()))
            if isPlaylistRandom(): self.channelPlaylist.unshuffle()
            return PLAYER.play(self.channelPlaylist)
        else: return DIALOG.notificationDialog(LANGUAGE(32000))
        self.resolveURL(found, listitems[0])
        

    def playError(self, pvritem={}):
        PROPERTIES.setPropertyDict('pendingPVRITEM.%s'%(pvritem.get('channelid','-1')),pvritem)
        self.log('playError, id = %s, attempt = %s\n%s'%(pvritem.get('channelid','-1'),pvritem['playcount'],pvritem))
        if pvritem['playcount'] == 1: setInstanceID() #reset instance and force cache flush.
        if pvritem['playcount'] <= 2:
            with busy_dialog():
                DIALOG.notificationWait(LANGUAGE(32038)%(pvritem['playcount']),wait=OVERLAY_DELAY)
                self.resolveURL(False, xbmcgui.ListItem()) #release pending playback.
                return BUILTIN.executebuiltin('PlayMedia(%s%s)'%(self.sysARG[0],self.sysARG[2]))
        elif pvritem['playcount'] == 3: forceBrute()
        elif pvritem['playcount'] == 4: DIALOG.okDialog(LANGUAGE(32134)%(ADDON_NAME),autoclose=90)
        else: DIALOG.notificationWait(LANGUAGE(32000))
        self.resolveURL(False, xbmcgui.ListItem()) #release pending playback.


    def resolveURL(self, found, listitem):
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitem)