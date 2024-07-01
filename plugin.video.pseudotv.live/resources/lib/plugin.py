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
from infotagger.listitem import ListItemInfoTag

#todo move sysinfo to dataclass and zlib meta.

class Plugin:
    @contextmanager
    def preparingPlayback(self):
        if self.playCheck(loadJSON(decodeString(PROPERTIES.getEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID))))):
            self.preparingPlayback = True
            try: yield
            finally:
                PROPERTIES.setEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID),encodeString(dumpJSON(self.sysInfo)))
                self.preparingPlayback = False
        else:
            yield self.playError()


    def __init__(self, sysARG=sys.argv):
        self.sysARG     = sysARG
        self.cache      = Cache(mem_cache=True)
        self.pageLimit  = int((REAL_SETTINGS.getSetting('Page_Limit') or "25"))
        self.seekTOL    = SETTINGS.getSettingInt('Seek_Tolerance')
        self.seekTHD    = SETTINGS.getSettingInt('Seek_Threshold')
        self.nowTime    = getUTCstamp()
        
        try:    self.sysInfo = dict(urllib.parse.parse_qsl(sysARG[2][1:].replace('.pvr','')))
        except: self.sysInfo = {}
        
        self.sysInfo.update({"name"      : (unquoteString(self.sysInfo.get('name',''))  or BUILTIN.getInfoLabel('ChannelName')),
                             "title"     : (unquoteString(self.sysInfo.get('title','')) or BUILTIN.getInfoLabel('label')),
                             "vid"       : decodeString(self.sysInfo.get('vid','')),
                             "duration"  : (int(self.sysInfo.get('duration','0')) or timeString2Seconds(BUILTIN.getInfoLabel('Duration(hh:mm:ss)'))),
                             "progress"  : (BUILTIN.getInfoLabel('Progress'),BUILTIN.getInfoLabel('PercentPlayed')),
                             "chlabel"   : BUILTIN.getInfoLabel('ChannelNumberLabel'),
                             "chpath"    : BUILTIN.getInfoLabel('FileNameAndPath'),
                             "fitem"     : decodePlot(BUILTIN.getInfoLabel('Plot')),
                             "isPlaylist": bool(SETTINGS.getSettingInt('Playback_Method')),
                             "playcount" : 0})
                             
        if not self.sysInfo.get('start') and self.sysInfo['fitem']:
            self.sysInfo['start'] = self.sysInfo['fitem'].get('start')
            self.sysInfo['stop']  = self.sysInfo['fitem'].get('stop')
            
        try:    self.sysInfo['seek'] = float(self.sysInfo['now']) - float(self.sysInfo['start'])
        except: self.sysInfo['seek'] = -1
        
        try:    self.sysInfo["citem"] = self.sysInfo["fitem"].pop('citem')
        except: self.sysInfo["citem"] = {'id':self.sysInfo['chid']}
            
        self.sysInfo["progresspercentage"] = (self.sysInfo["seek"]/self.sysInfo["duration"]) * 100
        self.log('__init__, sysARG = %s\nsysInfo = %s'%(sysARG,self.sysInfo))

                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def quePlaylist(self, listitems, pltype=xbmc.PLAYLIST_VIDEO):
        with busy_dialog():
            channelPlaylist = xbmc.PlayList(pltype)
            channelPlaylist.clear()
            xbmc.sleep(100) #give channelPlaylist.clear() enough time to clear queue.
            [channelPlaylist.add(liz.getPath(),liz,idx) for idx,liz in enumerate(listitems) if FileAccess.exists(liz.getPath())]
            return channelPlaylist
            

    def playVOD(self, title: str, vid: str):
        with self.preparingPlayback():
            self.log('playVOD, title = %s, vid = %s'%(title,vid))
            liz = xbmcgui.ListItem(title,path=vid)
            liz.setProperty("IsPlayable","true")
            self.resolveURL(True, liz)


    def playLive(self, name: str, chid: str, vid: str):
        with self.preparingPlayback():
            self.log('playLive, id = %s, seek = %s'%(chid,self.sysInfo['seek']))
            if round(self.sysInfo['seek']) <= self.seekTOL or round(self.sysInfo['progresspercentage']) > self.seekTHD:
                self.sysInfo['seek'] = 0
                
            if round(self.sysInfo['progresspercentage']) > self.seekTHD:
                listitems = self.getPVRItems(name, chid)
                if len(listitems) > 0:
                    liz = listitems[0]
                    self.sysInfo['duration'] = liz.getProperty('duration')
                else: return self.playError()
            else: 
                liz = xbmcgui.ListItem(name,path=vid)
                liz.setProperty("IsPlayable","true")
                
            liz.setProperty('sysInfo',encodeString(dumpJSON(self.sysInfo)))
            liz.setProperty('startoffset', str(self.sysInfo['seek'])) #secs
            infoTag = ListItemInfoTag(liz, 'video')
            infoTag.set_resume_point({'ResumeTime':self.sysInfo['seek'],'TotalTime':(self.sysInfo['duration'] * 60)})
            self.resolveURL(True, liz)


    def playBroadcast(self, name: str, chid: str, vid: str):
        with self.preparingPlayback():
            self.log('playBroadcast, id = %s, seek = %s'%(chid,self.sysInfo['seek']))
            liz = xbmcgui.ListItem(name,path=vid)
            liz.setProperty("IsPlayable","true")
            liz.setProperty('sysInfo',encodeString(dumpJSON(self.sysInfo)))
            infoTag = ListItemInfoTag(liz, 'video')
            self.resolveURL(True, liz)
            
            
    def playRadio(self, name: str, chid: str, vid: str):
        self.log('playRadio, id = %s'%(chid))
        def buildfItem(item: dict={}):
            liz = LISTITEMS.buildItemListItem(item, 'music')
            return liz

        with busy_dialog():
            jsonRPC = JSONRPC(self.cache)
            fileList = interleave([jsonRPC.requestList({'id':chid}, path, 'music', page=RADIO_ITEM_LIMIT, sort={"method":"random"})[0] for path in vid.split('|')])
            del jsonRPC

        if len(fileList) > 0:
            channelPlaylist = self.quePlaylist(poolit(buildfItem)(randomShuffle(fileList)),pltype=xbmc.PLAYLIST_MUSIC)
            channelPlaylist.shuffle()
            self.log('playRadio, Playlist size = %s'%(channelPlaylist.size()))
            PLAYER.play(channelPlaylist,windowed=True)
            BUILTIN.executebuiltin('ReplaceWindow(visualisation)')
        else: self.resolveURL(False, xbmcgui.ListItem())
    
        
    def playTV(self, name: str, chid: str):
        self.log('playTV, id = %s'%(chid))
        DIALOG.okDialog("Error! Outdated M3U/XMLTV detected!\nPlease open %s settings, Misc. Utility Menu and select %s."%(ADDON_NAME,LANGUAGE(32117)))


    def playPlaylist(self, name: str, chid: str):
        self.log('playPlaylist, id = %s'%(chid))
        listitems = self.getPVRItems(name, chid)
        if listitems:
            channelPlaylist = self.quePlaylist(listitems)
            self.log('playPlaylist, Playlist size = %s'%(channelPlaylist.size()))
            if isPlaylistRandom(): channelPlaylist.unshuffle()
            PLAYER.play(channelPlaylist,windowed=True)
            BUILTIN.executebuiltin('ReplaceWindow(fullscreenvideo)')
        else: self.resolveURL(False, xbmcgui.ListItem())


    def getPVRItems(self, name: str, chid: str) -> list:
        self.log('getPVRItems, id = %s'%(chid))
        def buildfItem(item: dict={}):
            liz = LISTITEMS.buildItemListItem(decodePlot(item.get('plot','')), 'video')
            liz.setProperty('sysInfo',encodeString(dumpJSON(self.sysInfo)))
            return liz
            
        found = False
        fitem = self.sysInfo.get('fitem')
        
        with busy_dialog():
            pvritem = self.matchChannel(name,chid,radio=False,isPlaylist=True)
    
            if pvritem:
                if pvritem.get('citem'):
                    self.sysInfo['citem'].update(pvritem.pop('citem'))
                    
                pastItems = pvritem.get('broadcastpast',[])
                nowitem   = pvritem.get('broadcastnow',{})
                nextitems = pvritem.get('broadcastnext',[]) # upcoming items
                nextitems.insert(0,nowitem)
                
                for pos, nextitem in enumerate(pastItems + nextitems):
                    fitem = decodePlot(nextitem.get('plot',{}))
                    if (fitem.get('file') == self.sysInfo.get('fitem',{}).get('file') and fitem.get('idx') == self.sysInfo.get('fitem',{}).get('idx')):
                        found = True
                        del nextitems[0:pos] # start array at correct position
                        break
                        
                if found:
                    nowitem = nextitems.pop(0)
                    liz = buildfItem(fitem)
                    if round(nowitem['progresspercentage']) > self.seekTHD:
                        self.log('getPVRItems, progress past threshold advance to nextitem')
                        nowitem = nextitems.pop(0)
                    
                    if round(nowitem['progress']) <= self.seekTOL:
                        self.log('getPVRItems, progress start at the beginning')
                        nowitem['progress']           = 0
                        nowitem['progresspercentage'] = 0
                        
                    if (nowitem['progress'] > 0 and nowitem['runtime'] > 0):
                        self.log('getPVRItems, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((nowitem['runtime'] * 60),nowitem['progress']))
                        liz.setProperty('startoffset', str(nowitem['progress'])) #secs
                        infoTag = ListItemInfoTag(liz, 'video')
                        infoTag.set_resume_point({'ResumeTime':nowitem['progress'],'TotalTime':(nowitem['runtime'] * 60)})
                        
                    del nextitems[PAGE_LIMIT-1:]# list of upcoming items, truncate for speed.
                    self.sysInfo['fitem']    = fitem
                    pvritem['broadcastnow']  = nowitem   # current item
                    pvritem['broadcastnext'] = nextitems # upcoming items
                    self.sysInfo['pvritem']  = pvritem
                    
                    listitems = [liz]
                    listitems.extend(poolit(buildfItem)(nextitems))
                    return listitems
                else: DIALOG.notificationDialog(LANGUAGE(32164))
            else: DIALOG.notificationDialog(LANGUAGE(32000))
            return []
    
    
    @cacheit(expiration=datetime.timedelta(seconds=15),json_data=True)
    def matchChannel(self, chname: str, id: str, radio: bool=False, isPlaylist: bool=False) -> str:
        self.log('matchChannel, id = %s, chname = %s, radio = %s, isPlaylist = %s'%(id,chname,radio,isPlaylist))
        def getCallback(chname, id, radio=False, isPlaylist=False):
            self.log('getCallback, id = %s, radio = %s, isPlaylist = %s'%(id,radio,isPlaylist))
            def _matchJSON():
                results = jsonRPC.getDirectory(param={"directory":"pvr://channels/{dir}/".format(dir={True:'radio',False:'tv'}[radio])}, cache=True).get('files',[])
                for dir in [ADDON_NAME,'All channels']: #todo "All channels" may not work with non-English translations!
                    for result in results:
                        if result.get('label','').lower().startswith(dir.lower()):
                            self.log('getCallback: _matchJSON, found dir = %s'%(result.get('file')))
                            response = jsonRPC.getDirectory(param={"directory":result.get('file')},checksum=getInstanceID(),expiration=datetime.timedelta(minutes=OVERLAY_DELAY)).get('files',[])
                            for item in response:
                                if item.get('label','').lower() == chname.lower() and item.get('uniqueid','') == id:
                                    self.log('getCallback: _matchJSON, found file = %s'%(item.get('file')))
                                    return item.get('file')
                self.log('getCallback: _matchJSON, no callback found!\nresults = %s'%(results))

            if (isPlaylist or radio) and len(self.sysARG) > 2:
                callback = '%s%s'%(self.sysARG[0],self.sysARG[2])
            else:
                callback = _matchJSON() #requires 'pvr://' json whitelisting.
            if callback is None: return DIALOG.okDialog(LANGUAGE(32133))
            return callback
             
        def _match():
            channels = jsonRPC.getPVRChannels(radio)
            for channel in channels:
                if channel.get('label').lower() == chname.lower():
                    for key in ['broadcastnow', 'broadcastnext']:
                        if decodePlot(channel.get(key,{}).get('plot','')).get('citem',{}).get('id') == id:
                            channel['broadcastnext'] = [channel.get('broadcastnext',{})]
                            self.log('matchChannel, id = %s, found pvritem = %s'%(id,channel))
                            return channel
        
        def _extend(pvritem: dict={}) -> dict:
            channelItem = {}
            def _parseBroadcast(broadcast={}):
                if broadcast.get('progresspercentage',0) == 100:
                    channelItem.setdefault('broadcastpast',[]).append(broadcast)
                elif broadcast.get('progresspercentage',0) > 0 and broadcast.get('progresspercentage',0) != 100:
                    channelItem['broadcastnow'] = broadcast
                elif broadcast.get('progresspercentage',0) == 0 and broadcast.get('progresspercentage',0) != 100:
                    channelItem.setdefault('broadcastnext',[]).append(broadcast)
            
            poolit(_parseBroadcast)(jsonRPC.getPVRBroadcasts(pvritem.get('channelid',{})))
            nextitems = channelItem.get('broadcastnext',pvritem['broadcastnext'])
            pvritem['broadcastnext'] = nextitems
            self.log('extendProgrammes, extend broadcastnext to %s entries'%(len(pvritem['broadcastnext'])))
            return pvritem
            
        jsonRPC = JSONRPC(self.cache)
        cacheName = 'matchChannel.%s'%(getMD5('%s.%s.%s.%s'%(chname,id,radio,isPlaylist)))
        cacheResponse = (self.cache.get(cacheName, checksum=getInstanceID(), json_data=True) or {})
        if not cacheResponse:
            pvritem = _match()
            if not pvritem: return self.playError()
            self.sysInfo['isPlaylist'] = isPlaylist
            self.sysInfo['callback']   = getCallback(pvritem.get('channel'),pvritem.get('uniqueid'),radio,isPlaylist)
            pvritem['citem'] = decodePlot(pvritem.get('broadcastnow',{}).get('plot','')).get('citem',{})
            if isPlaylist and not radio: pvritem = _extend(pvritem)
            cacheResponse = self.cache.set(cacheName, pvritem, checksum=getInstanceID(), expiration=datetime.timedelta(seconds=OVERLAY_DELAY), json_data=True)
        del jsonRPC
        return cacheResponse


    def playCheck(self, oldInfo: dict={}) -> bool:
        #check that resource or plugin installed?
        self.log('playCheck, id = %s\noldInfo = %s'%(oldInfo.get('chid','-1'),oldInfo))
        def _chkPath():
            if self.sysInfo.get('vid','').startswith(tuple(VFS_TYPES)): return hasAddon(self.sysInfo.get('vid',''),install=True,enable=True)
            elif FileAccess.exists(self.sysInfo.get('vid','')): return True
            else:
                self.log('playCheck _chkPath, failed! path (%s) not found.'%(self.sysInfo.get('vid','')))
                DIALOG.notificationDialog(LANGUAGE(32167))
                return False
            
        def _chkGuide():
            if self.sysInfo.get('chid') == self.sysInfo.get('citem',{}).get('id',random.random()):
                if self.sysInfo.get('title') != self.sysInfo.get('fitem',{}).get('label',self.sysInfo.get('title')):
                    self.log('playCheck _chkGuide, failed! Current EPG cell (%s) does not match PVR backend (%s).'%(self.sysInfo.get('fitem',{}).get('label',self.sysInfo.get('title')),self.sysInfo.get('title')))
                    # DIALOG.notificationDialog(LANGUAGE(32129)%(PVR_CLIENT_NAME))
                    return False
            return True
            
        def _chkLoop():
            if self.sysInfo.get('chid') == oldInfo.get('chid',random.random()):
                if self.sysInfo.get('start') == oldInfo.get('start',random.random()):
                    self.sysInfo['playcount'] = oldInfo.get('playcount',0) + 1 #carry over playcount
                    self.sysInfo['runtime']   = oldInfo.get('runtime',-1)      #carry over previous player runtime
                    
                    if self.sysInfo['now'] >= self.sysInfo['stop']:
                        self.log('playCheck _chkLoop, failed! Current time (%s) is past the contents stop time (%s).'%(self.sysInfo['now'],self.sysInfo['stop']))
                        return False
                    elif self.sysInfo['duration'] > self.sysInfo['runtime']:
                        self.log('playCheck _chkLoop, failed! Duration error between player (%s) and pvr (%s).'%(self.sysInfo['duration'],self.sysInfo['runtime']))
                        return False
                    elif self.sysInfo['seek'] >= oldInfo.get('runtime',self.sysInfo['duration']):
                        self.log('playCheck _chkLoop, failed! Seeking to a position (%s) past contents runtime (%s).'%(self.sysInfo['seek'],oldInfo.get('runtime',self.sysInfo['duration'])))
                        return False
                    elif self.sysInfo['seek'] == oldInfo.get('seek',self.sysInfo['seek']):
                        self.log('playCheck _chkLoop, failed! Seeking to same position.')
                        return False
            return True

        _chkPath()
        _chkGuide()
        _chkLoop()
        #todo take action on fail. for now log events to strategize actions. 
        return True
        
        
    def playError(self):
        self.log('playError, id = %s, attempt = %s\n%s'%(self.sysInfo.get('chid','-1'),self.sysInfo.get('playcount'),self.sysInfo))
        PROPERTIES.setEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID),encodeString(dumpJSON(self.sysInfo)))
        if self.sysInfo.get('playcount') in [1,2,3]:
            with busy_dialog():
                DIALOG.notificationWait(LANGUAGE(32038)%(self.sysInfo.get('playcount',0)))
            self.resolveURL(False, xbmcgui.ListItem()) #release pending playback.
            MONITOR.waitForAbort(1.0) #allow a full second to pass beyond any msecs differential.
            return BUILTIN.executebuiltin('PlayMedia(%s%s)'%(self.sysARG[0],self.sysARG[2])) #retry channel
        elif self.sysInfo.get('playcount') == 4: DIALOG.okDialog(LANGUAGE(32134)%(ADDON_NAME))
        else: DIALOG.notificationWait(LANGUAGE(32000))
        self.resolveURL(False, xbmcgui.ListItem()) #release pending playback.
        
        
    def resolveURL(self, found, listitem):
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitem)