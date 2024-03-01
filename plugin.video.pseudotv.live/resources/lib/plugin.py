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
from globals     import *
from jsonrpc     import JSONRPC
from rules       import RulesList
from infotagger.listitem import ListItemInfoTag

class Plugin:
    @contextmanager
    def preparingPlayback(self):
        if self.playCHK(loadJSON(PROPERTIES.getEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID)))):
            PROPERTIES.setEXTProperty('%s.preparingPlayback'%(ADDON_ID),'true')
            self.runActions(RULES_ACTION_PLAYBACK, self.sysInfo['citem'], inherited=self)
            try: yield
            finally:
                PROPERTIES.setEXTProperty('%s.preparingPlayback'%(ADDON_ID),'false')
                PROPERTIES.setEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID),dumpJSON(self.sysInfo))
        else:
            yield self.playError()


    def __init__(self, sysARG=sys.argv):
        self.sysARG     = sysARG
        self.cache      = Cache(mem_cache=True)
        self.jsonRPC    = JSONRPC()
        self.runActions = RulesList().runActions
        self.pageLimit  = int((REAL_SETTINGS.getSetting('Page_Limit') or "25"))
        self.seekTOL    = SETTINGS.getSettingInt('Seek_Tolerance')
        self.seekTHD    = SETTINGS.getSettingInt('Seek_Threshold')

        try:    self.sysInfo  = dict(urllib.parse.parse_qsl(sysARG[2][1:].replace('.pvr','')))
        except: self.sysInfo  = {}
        
        self.sysInfo.update({"name"     : (unquoteString(self.sysInfo.get('name',''))  or BUILTIN.getInfoLabel('ChannelName')),
                             "title"    : (unquoteString(self.sysInfo.get('title','')) or BUILTIN.getInfoLabel('label')),
                             "vid"      : decodeString(self.sysInfo.get('vid','')),
                             "duration" : (int(self.sysInfo.get('duration','-1'))      or timeString2Seconds(BUILTIN.getInfoLabel('Duration(hh:mm:ss)'))),
                             "progress" : (BUILTIN.getInfoLabel('Progress'),BUILTIN.getInfoLabel('PercentPlayed')),
                             "chlabel"  : BUILTIN.getInfoLabel('ChannelNumberLabel'),
                             "chpath"   : BUILTIN.getInfoLabel('FileNameAndPath'),
                             "fitem"    : decodeWriter(BUILTIN.getInfoLabel('Writer')),
                             "citem"    : decodeWriter(BUILTIN.getInfoLabel('Writer')).get('citem',{'id':self.sysInfo['chid']})})
        try:
            self.sysInfo['epoch']     = datetime.datetime.timestamp(strpTime(self.sysInfo['start'], DTJSONFORMAT))
            self.sysInfo["starttime"] = datetime.datetime.fromtimestamp((datetime.datetime.timestamp(strpTime(self.sysInfo['start'], DTJSONFORMAT)) - getTimeoffset())).strftime(DTJSONFORMAT)
            self.sysInfo['endtime']   = datetime.datetime.fromtimestamp(datetime.datetime.timestamp(strpTime(self.sysInfo['starttime'], DTJSONFORMAT) + datetime.timedelta(seconds=self.sysInfo['duration']))).strftime(DTJSONFORMAT)
            self.sysInfo["seek"]      = (getUTCstamp() - datetime.datetime.timestamp(strpTime(self.sysInfo['starttime'], DTJSONFORMAT)))
        except:
            self.sysInfo['epoch']     = None
            self.sysInfo["starttime"] = None
            self.sysInfo["endtime"]   = None
            self.sysInfo["seek"]      = None
            
        self.log('__init__, sysARG = %s\nsysInfo = %s'%(sysARG,self.sysInfo))

                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def playVOD(self, title, vid):
        with self.preparingPlayback():
            self.log('playVOD, title = %s, vid = %s'%(title,vid))
            liz = xbmcgui.ListItem(title,path=vid)
            liz.setProperty("IsPlayable","true")
            self.resolveURL(True, liz)


    def playLive(self, name, chid, vid):
        with self.preparingPlayback():
            self.log('playLive, id = %s, start = %s, seek = %s'%(chid,self.sysInfo['starttime'],self.sysInfo['seek']))
            liz = xbmcgui.ListItem(name,path=vid)
            liz.setProperty("IsPlayable","true")
            liz.setProperty('pvritem',dumpJSON({"citem":self.sysInfo.get('citem',{}),"sysinfo":self.sysInfo}))
            liz.setProperty('startoffset', str(self.sysInfo['seek'])) #secs
            infoTag = ListItemInfoTag(liz, 'video')
            infoTag.set_resume_point({'ResumeTime':self.sysInfo['seek'],'TotalTime':(self.sysInfo['duration'] * 60)})
            self.resolveURL(True, liz)


    def playBroadcast(self, name, chid, vid):
        with self.preparingPlayback():
            self.log('playBroadcast, id = %s, start = %s, seek = %s'%(chid,self.sysInfo['start'],self.sysInfo['seek']))
            liz = xbmcgui.ListItem(name,path=vid)
            liz.setProperty("IsPlayable","true")
            liz.setProperty('pvritem',dumpJSON({"citem":self.sysInfo.get('citem',{}),"sysinfo":self.sysInfo}))
            liz.setProperty('startoffset', str(self.sysInfo['seek'])) #secs
            infoTag = ListItemInfoTag(liz, 'video')
            infoTag.set_resume_point({'ResumeTime':self.sysInfo['seek'],'TotalTime':(self.sysInfo['duration'] * 60)})
            self.resolveURL(True, liz)
            
            
    def playRadio(self, name, chid, vid):
        self.log('playRadio, id = %s'%(chid))
        with self.preparingPlayback():
            fileList = list(interleave([self.jsonRPC.requestList({'id':chid}, path, 'music', page=RADIO_ITEM_LIMIT) for path in vid.split('|')]))#todo replace RADIO_ITEM_LIMIT with cacluated runtime to EPG_HRS
            if len(fileList) > 0:
                channelPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                channelPlaylist.clear()
                xbmc.sleep(100) #give channelPlaylist.clear() enought time to clear queue.
                for idx,liz in enumerate([LISTITEMS.buildItemListItem(item,media='music') for item in randomShuffle(fileList)]):
                    channelPlaylist.add(liz.getPath(),liz,idx)
                self.log('playRadio, Playlist size = %s'%(channelPlaylist.size()))
                if not isPlaylistRandom(): channelPlaylist.unshuffle()
                else:                      channelPlaylist.shuffle()
                PLAYER.play(channelPlaylist,windowed=True)
                BUILTIN.executebuiltin('ReplaceWindow(visualisation)')
            self.resolveURL(False, xbmcgui.ListItem())
    
        
    def playTV(self, name, chid):
        self.log('playTV, id = %s'%(chid))
        DIALOG.okDialog("Error! Outdated M3U/XMLTV detected!\nPlease open %s settings, Misc. Utility Menu and select %s."%(ADDON_NAME,LANGUAGE(32117)))


    def playPlaylist(self, name, chid):
        self.log('playPlaylist, id = %s'%(chid))
        def buildWriterItem(item={}, media='video'):
            return LISTITEMS.buildItemListItem(decodeWriter(item.get('writer','')), media)
            
        listitems = [xbmcgui.ListItem()]
        fitem     = self.sysInfo.get('fitem')
        pvritem   = self.matchChannel(name,chid,radio=False,isPlaylist=True)
        if pvritem:
            nowitem   = pvritem.get('broadcastnow',{})
            nextitems = pvritem.get('broadcastnext',[]) # upcoming items
            nextitems.insert(0,nowitem)
            
            for pos, nextitem in enumerate(nextitems):
                fitem = decodeWriter(nextitem.get('writer',{}))
                if (fitem.get('file') == self.sysInfo.get('fitem',{}).get('file') and fitem.get('idx') == self.sysInfo.get('fitem',{}).get('idx')) or (nextitem.get('starttime') ==  self.sysInfo.get('starttime',random.random())):
                    del nextitems[0:pos] # start array at correct position
                    break
                   
            nowitem = nextitems.pop(0)
            liz = LISTITEMS.buildItemListItem(fitem)
            if round(nowitem['progress']) <= self.seekTOL or round(nowitem['progresspercentage']) > self.seekTHD:
                self.log('playPlaylist, progress start at the beginning')
                nowitem['progress']           = 0
                nowitem['progresspercentage'] = 0
                
            if (nowitem['progress'] > 0 and nowitem['runtime'] > 0):
                self.log('playPlaylist, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((nowitem['runtime'] * 60),nowitem['progress']))
                liz.setProperty('startoffset', str(nowitem['progress'])) #secs
                infoTag = ListItemInfoTag(liz, 'video')
                infoTag.set_resume_point({'ResumeTime':nowitem['progress'],'TotalTime':(nowitem['runtime'] * 60)})
                
            del nextitems[PAGE_LIMIT:]# list of upcoming items, truncate for speed.
            self.sysInfo['fitem']    = fitem
            pvritem['broadcastnow']  = nowitem   # current item
            pvritem['broadcastnext'] = nextitems # upcoming items
            liz.setProperty('pvritem',dumpJSON({"citem":self.sysInfo.get('citem',{}),"sysinfo":self.sysInfo}))
            listitems = [liz]
            listitems.extend(poolit(buildWriterItem)(nextitems))
            channelPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            channelPlaylist.clear()
            xbmc.sleep(100)
            
            for idx,lz in enumerate(listitems):
                channelPlaylist.add(lz.getPath(),lz,idx)
                
            self.log('playPlaylist, Playlist size = %s'%(channelPlaylist.size()))
            if isPlaylistRandom(): channelPlaylist.unshuffle()
            PLAYER.play(channelPlaylist,windowed=True)
        else: self.playError()
        
        
    @timeit
    def matchChannel(self, chname, id, radio=False, isPlaylist=False):
        self.log('matchChannel, id = %s, chname = %s, radio = %s, isPlaylist = %s'%(id,chname,radio,isPlaylist))
        def getCallback(chname, id, radio=False, isPlaylist=False):
            self.log('getCallback, id = %s, radio = %s, isPlaylist = %s'%(id,radio,isPlaylist))
            def _matchVFS():
                pvrType = 'radio' if radio else 'tv'
                pvrRoot = "pvr://channels/{dir}/".format(dir=pvrType)
                results = self.jsonRPC.walkListDirectory(pvrRoot,checksum=getInstanceID(),expiration=datetime.timedelta(minutes=OVERLAY_DELAY))[0]
                for dir in [ADDON_NAME,'All channels']: #todo "All channels" may not work with non-English translations!
                    for result in results:
                        if result.lower().startswith(quoteString(dir.lower())):
                            self.log('getCallback: _matchVFS, found dir = %s'%(os.path.join(pvrRoot,result)))
                            response = self.jsonRPC.walkListDirectory(os.path.join(pvrRoot,result),append_path=True,checksum=getInstanceID(),expiration=datetime.timedelta(minutes=OVERLAY_DELAY))[1]
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
                            self.log('getCallback: _matchJSON, found dir = %s'%(result.get('file')))
                            response = self.jsonRPC.getDirectory(param={"directory":result.get('file')},checksum=getInstanceID(),expiration=datetime.timedelta(minutes=OVERLAY_DELAY)).get('files',[])
                            for item in response:
                                if item.get('label','').lower() == chname.lower() and item.get('uniqueid','') == id:
                                    self.log('getCallback: _matchJSON, found file = %s'%(item.get('file')))
                                    return item.get('file')
                self.log('getCallback: _matchJSON, no callback found!\nresults = %s'%(results))

            if (isPlaylist or radio) and len(self.sysARG) > 2:
                #omega changed pvr paths, requiring double jsonRPC calls to return true file path. maybe more efficient to call through plugin rather than direct pvr. 
                #this breaks "pvr" should only apply to playlists, avoid unnecessary jsonRPC calls which are slow on lowpower devices. 
                callback = '%s%s'%(self.sysARG[0],self.sysARG[2])
            elif isLowPower() or not PROPERTIES.getPropertyBool('hasPVRSource'):
                callback = _matchVFS()
            else:
                callback = _matchJSON() #use faster jsonrpc on high power devices. requires 'pvr://' json whitelisting.
            if callback is None: return DIALOG.okDialog(LANGUAGE(32133), autoclose=90, usethread=True)
            return callback
             
        def _extend(pvritem):
            channelItem = {}
            def _parseBroadcast(broadcast={}):
                if broadcast.get('progresspercentage',0) > 0 and broadcast.get('progresspercentage',0) != 100:
                    channelItem['broadcastnow'] = broadcast
                elif broadcast.get('progresspercentage',0) == 0 and broadcast.get('progresspercentage',0) != 100:
                    channelItem.setdefault('broadcastnext',[]).append(broadcast)
            
            nextitems = self.jsonRPC.getPVRBroadcasts(pvritem.get('channelid',{}))
            poolit(_parseBroadcast)(nextitems)
            nextitems = channelItem.get('broadcastnext',pvritem['broadcastnext'])
            pvritem['broadcastnext'] = nextitems
            self.log('extendProgrammes, extend broadcastnext to %s entries'%(len(pvritem['broadcastnext'])))
            return pvritem
            
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
            if not pvritem: return self.playError()
            pvritem['isPlaylist'] = isPlaylist
            pvritem['callback']   = getCallback(pvritem.get('channel'),pvritem.get('uniqueid'),radio,isPlaylist)
            pvritem['citem']      = (self.sysInfo.get('citem') or decodeWriter(pvritem.get('broadcastnow',{}).get('writer','')).get('citem',{}))
            try:    pvritem['epgurl'] = 'pvr://guide/%s/{starttime}.epg'%(re.compile('pvr://guide/(.*)/', re.IGNORECASE).search(self.sysInfo.get('path')).group(1))
            except: pvritem['epgurl'] = self.sysInfo.get('path','')#"pvr://guide/1197/2022-02-14 18:22:24.epg"
            if isPlaylist and not radio: pvritem = _extend(pvritem)
            cacheResponse = self.cache.set(cacheName, pvritem, checksum=getInstanceID(), expiration=datetime.timedelta(seconds=OVERLAY_DELAY), json_data=True)
        return cacheResponse


    def playCHK(self, oldInfo={}):
        self.log('playCHK, id = %s\n%s'%(oldInfo.get('chid','-1'),oldInfo))
        if oldInfo.get('chid',random.random()) == self.sysInfo.get('chid') and oldInfo.get('starttime',random.random()) == self.sysInfo.get('starttime'):
            self.sysInfo['playcount'] = oldInfo.get('playcount',0) + 1
            self.sysInfo['runtime']   = oldInfo.get('runtime',-1)
            if self.sysInfo['duration'] > self.sysInfo['runtime']:
                self.log('playCHK, failed! Duration error between player (%s) and pvr (%s).'%(self.sysInfo['duration'],self.sysInfo['runtime']))
                return False
            elif int(oldInfo['seek']) >= oldInfo['duration']:
                self.log('playCHK, failed! Seeking past duration.')
                return False
            elif oldInfo['seek'] == self.sysInfo['seek']:
                self.log('playCHK, failed! Seeking to same position.')
                return False
        return True
        
        
    def playError(self):
        MONITOR.waitForAbort(1) #allow a full second to pass beyond any msecs differential.
        self.log('playError, id = %s, attempt = %s\n%s'%(self.sysInfo.get('chid','-1'),self.sysInfo['playcount'],self.sysInfo))
        PROPERTIES.setEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID),dumpJSON(self.sysInfo))
        if   self.sysInfo['playcount'] == 1 and not PLAYER.isPlaying(): setInstanceID() #reset instance and force cache flush.
        elif self.sysInfo['playcount'] == 2:
            with busy_dialog():
                DIALOG.notificationWait(LANGUAGE(32038)%(self.sysInfo.get('playcount',0)))
            self.resolveURL(False, xbmcgui.ListItem()) #release pending playback.
            return BUILTIN.executebuiltin('PlayMedia(%s%s)'%(self.sysARG[0],self.sysARG[2])) #retry channel
        # elif self.sysInfo['playcount'] == 3: bruteForcePVR()
        elif self.sysInfo['playcount'] == 4: DIALOG.okDialog(LANGUAGE(32134)%(ADDON_NAME),autoclose=90)
        else: DIALOG.notificationWait(LANGUAGE(32000))
        self.resolveURL(False, xbmcgui.ListItem()) #release pending playback.
        
        
    def resolveURL(self, found, listitem):
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitem)