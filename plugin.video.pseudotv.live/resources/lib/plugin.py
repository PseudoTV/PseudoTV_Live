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


class Plugin:
    @contextmanager
    def preparingPlayback(self):
        if self.playCheck(loadJSON(decodeString(PROPERTIES.getEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID))))):
            try: yield
            finally: PROPERTIES.setEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID),encodeString(dumpJSON(self.sysInfo)))
        else: yield self.playError()


    def __init__(self, sysARG=sys.argv, sysInfo={}):
        self.sysARG      = sysARG
        self.sysInfo     = sysInfo
        self.jsonRPC     = JSONRPC()
        self.cache       = SETTINGS.cache
        
        self.pageLimit   = int((REAL_SETTINGS.getSetting('Page_Limit') or "25"))
        self.seekTOL     = SETTINGS.getSettingInt('Seek_Tolerance')
        self.seekTHD     = SETTINGS.getSettingInt('Seek_Threshold')
        
        self.sysInfo['radio'] = sysInfo.get('mode','').lower() == "radio"
        self.sysInfo['now']   = int(sysInfo.get('now')   or int(getUTCstamp()))
        self.sysInfo['start'] = int(sysInfo.get('start') or '-1')
        self.sysInfo['stop']  = int(sysInfo.get('stop')  or '-1')
        self.sysInfo['citem'] = (sysInfo.get('citem')    or combineDicts({'id':sysInfo.get("chid")},sysInfo.get('fitem',{}).get('citem',{})))
        
        if sysInfo.get('fitem'):
            if sysInfo.get("nitem"): self.sysInfo.update({'citem':combineDicts(self.sysInfo["nitem"].pop('citem'),self.sysInfo["fitem"].pop('citem'))})
            else:                    self.sysInfo.update({'citem':combineDicts(self.sysInfo["citem"],self.sysInfo["fitem"].pop('citem'))})
            
            if self.sysInfo.get('start') == -1:
                self.sysInfo['start'] = self.sysInfo['fitem'].get('start')
                self.sysInfo['stop']  = self.sysInfo['fitem'].get('stop')

            self.sysInfo['duration']  = float(sysInfo.get('duration')  or self.jsonRPC._getRuntime(self.sysInfo['fitem']) or timeString2Seconds(BUILTIN.getInfoLabel('Duration(hh:mm:ss)')))
        else:
            self.sysInfo['duration']  = float((sysInfo.get('duration') or '-1'))
            
        try:
            self.sysInfo['seek']               = int(sysInfo.get('seek') or (abs(self.sysInfo['start'] - self.sysInfo['now']) if self.sysInfo['start'] > 0 else -1))
            self.sysInfo["progresspercentage"] = -1 if self.sysInfo['seek'] == -1 else (self.sysInfo["seek"]/self.sysInfo["duration"]) * 100
        except:
            self.sysInfo['seek']               = int(sysInfo.get('seek','-1'))
            self.sysInfo["progresspercentage"] = -1
            
        self.log('__init__, sysARG = %s\nsysInfo = %s'%(sysARG,self.sysInfo))

                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def quePlaylist(self, listitems, pltype=xbmc.PLAYLIST_VIDEO, shuffle=BUILTIN.isPlaylistRandom()):
        self.log('quePlaylist, listitems = %s, shuffle = %s'%(len(listitems),shuffle))
        with BUILTIN.busy_dialog():
            channelPlaylist = xbmc.PlayList(pltype)
            channelPlaylist.clear()
            xbmc.sleep(100) #give channelPlaylist.clear() enough time to clear queue.
            [channelPlaylist.add(liz.getPath(),liz,idx) for idx,liz in enumerate(listitems) if liz.getPath()]
            self.log('quePlaylist, Playlist size = %s, shuffle = %s'%(channelPlaylist.size(),shuffle))
            if shuffle: channelPlaylist.shuffle()
            else:       channelPlaylist.unshuffle()
            return channelPlaylist


    def getResumeItems(self, name, chid):
        self.log('getResumeItems, id = %s'%(chid))
        def buildfItem(item: dict={}):
            idx, item = item
            sysInfo = self.sysInfo.copy()
            sysInfo['isPlaylist'] = True
            
            if idx == 0 and round(sysInfo.get('progresspercentage',0)) > self.seekTHD:
                self.IDXModifier = 1
            
            nowitem = nextitems[idx+self.IDXModifier][1] #now broadcast
            if 'citem' in nowitem: nowitem.pop('citem')
            sysInfo.update({'fitem':nowitem,'position':idx})
            
            try: #next broadcast
                nextitem = nextitems[idx+self.IDXModifier+1][1]
                if 'citem' in nextitem: nextitem.pop('citem')
                sysInfo.update({'nitem':nextitem})
            except: pass
            
            liz = LISTITEMS.buildItemListItem(nowitem,'video')
            if idx == 0 and item.get('resume'):
                seektime = int(item.get('resume',{}).get('position',0.0))
                runtime  = int(item.get('resume',{}).get('total',0.0))
                self.log('getResumeItems, within seek tolerance setting seek totaltime = %s, resumetime = %s'%(runtime, seektime))
                liz.setProperty('startoffset', str(seektime)) #secs
                infoTag = ListItemInfoTag(liz, 'video')
                infoTag.set_resume_point({'ResumeTime':seektime, 'TotalTime':runtime * 60})
            liz.setProperty('sysInfo',encodeString(dumpJSON(sysInfo)))
            return liz
        
        with BUILTIN.busy_dialog():
            from rules import RulesList
            nextitems = RulesList().runActions(RULES_ACTION_PLAYBACK_RESUME, self.sysInfo.get('citem',{'name':name,'id':chid}))
            if nextitems:
                self.IDXModifier = 0
                del nextitems[PAGE_LIMIT-1:]# list of upcoming items, truncate for speed
                self.log('getResumeItems, building nextitems (%s)'%(len(nextitems)))
                return poolit(buildfItem)(nextitems)
            else: DIALOG.notificationDialog(LANGUAGE(32000))
            return []
        

    def getPVRItems(self, name: str, chid: str) -> list:
        self.log('getPVRItems, id = %s'%(chid))
        def buildfItem(item: dict={}):
            idx, item = item
            sysInfo = self.sysInfo.copy()
            nowitem = decodePlot(item.get('plot',''))
            if 'citem' in nowitem: nowitem.pop('citem')
            nowitem['pvritem'] = item
            sysInfo.update({'fitem':nowitem,'position':idx})
            
            try: #next broadcast
                nextitem = decodePlot(nextitems[idx+1][1].get('plot',''))
                if 'citem' in nextitem: nextitem.pop('citem')
                nextitem.get('customproperties',{})['pvritem'] = nextitems[idx + 1]
                sysInfo.update({'nitem':nextitem})
            except: pass
            
            liz = LISTITEMS.buildItemListItem(nowitem,'video')
            if (item.get('progress',0) > 0 and item.get('runtime',0) > 0):
                self.log('getPVRItems, within seek tolerance setting seek totaltime = %s, resumetime = %s'%((item['runtime'] * 60),item['progress']))
                liz.setProperty('startoffset', str(item['progress'])) #secs
                infoTag = ListItemInfoTag(liz, 'video')
                infoTag.set_resume_point({'ResumeTime':item['progress'],'TotalTime':(item['runtime'] * 60)})
            liz.setProperty('sysInfo',encodeString(dumpJSON(sysInfo)))
            return liz
            
        found = False
        with BUILTIN.busy_dialog():
            pvritem = self._matchChannel(name,chid,radio=False)
            if pvritem:
                pastItems = pvritem.get('broadcastpast',[])
                nowitem   = pvritem.get('broadcastnow',{})
                nextitems = pvritem.get('broadcastnext',[]) # upcoming items
                nextitems.insert(0,nowitem)
                nextitems = pastItems + nextitems
                
                if (self.sysInfo.get('fitem') or self.sysInfo.get('vid')):
                    for pos, nextitem in enumerate(nextitems):
                        fitem = decodePlot(nextitem.get('plot',{}))
                        file  = self.sysInfo.get('fitem',{}).get('file') if self.sysInfo.get('fitem') else self.sysInfo.get('vid')
                        if file == fitem.get('file') and self.sysInfo.get('citem',{}).get('id') == fitem.get('citem',{}).get('id',str(random.random())):
                            found = True
                            self.log('getPVRItems, id = %s found matching fitem'%(chid))
                            del nextitems[0:pos] # start array at correct position
                            break
                            
                elif self.sysInfo.get('now'):
                    for pos, nextitem in enumerate(nextitems):
                        fitem = decodePlot(nextitem.get('plot',{}))
                        ntime = datetime.datetime.fromtimestamp(float(self.sysInfo.get('now')))
                        if ntime >= strpTime(nextitem.get('starttime')) and ntime < strpTime(nextitem.get('endtime')) and chid == fitem.get('citem',{}).get('id',str(random.random())):
                            found = True
                            self.log('getPVRItems, id = %s found matching starttime'%(chid))
                            del nextitems[0:pos] # start array at correct position
                            break
                    
                if found:
                    nowitem = nextitems.pop(0)
                    if round(nowitem['progresspercentage']) > self.seekTHD:
                        self.log('getPVRItems, progress past threshold advance to nextitem')
                        nowitem = nextitems.pop(0)
                    
                    if round(nowitem['progress']) <= self.seekTOL:
                        self.log('getPVRItems, progress start at the beginning')
                        nowitem['progress']           = 0
                        nowitem['progresspercentage'] = 0

                    del nextitems[PAGE_LIMIT-1:]# list of upcoming items, truncate for speed
                    nextitems.insert(0,nowitem)
                    self.log('getPVRItems, building nextitems (%s)'%(len(nextitems)))
                    return poolit(buildfItem)([(idx, item) for idx, item in enumerate(nextitems)])
                else: DIALOG.notificationDialog(LANGUAGE(32164))
            else: DIALOG.notificationDialog(LANGUAGE(32000))
            return []
    

    def _matchChannel(self, chname: str, id: str, radio: bool=False):
        self.log('_matchChannel, id = %s, chname = %s, radio = %s'%(id,chname,radio))
        def __match():
            channels = jsonRPC.getPVRChannels(radio)
            for channel in channels:
                if channel.get('label').lower() == chname.lower():
                    for key in ['broadcastnow', 'broadcastnext']:
                        if decodePlot(channel.get(key,{}).get('plot','')).get('citem',{}).get('id') == id:
                            channel['broadcastnext'] = [channel.get('broadcastnext',{})]
                            self.log('_matchChannel: __match, id = %s, found pvritem = %s'%(id,channel))
                            return channel
        
        def __extend(pvritem: dict={}) -> dict:
            channelItem = {}
            def _parseBroadcast(broadcast={}):
                if broadcast.get('progresspercentage',0) == 100:
                    channelItem.setdefault('broadcastpast',[]).append(broadcast)
                elif broadcast.get('progresspercentage',0) > 0 and broadcast.get('progresspercentage',0) != 100:
                    channelItem['broadcastnow'] = broadcast
                elif broadcast.get('progresspercentage',0) == 0 and broadcast.get('progresspercentage',0) != 100:
                    channelItem.setdefault('broadcastnext',[]).append(broadcast)
            
            poolit(_parseBroadcast)(jsonRPC.getPVRBroadcasts(pvritem.get('channelid',{})))
            pvritem['broadcastnext'] = channelItem.get('broadcastnext',pvritem['broadcastnext'])
            self.log('_matchChannel: __extend, broadcastnext = %s entries'%(len(pvritem['broadcastnext'])))
            return pvritem
            
        cacheName     = 'matchChannel.%s'%(getMD5('%s.%s.%s'%(chname,id,radio)))
        cacheResponse = (self.cache.get(cacheName, checksum=PROPERTIES.getInstanceID(), json_data=True) or {})
        if not cacheResponse:
            jsonRPC = JSONRPC()
            pvritem = __match()
            if not pvritem:
                del jsonRPC
                return self.resolveURL(False, xbmcgui.ListItem())
            else:
                self.sysInfo.update({'citem':decodePlot(pvritem.get('broadcastnow',{}).get('plot','')).get('citem',self.sysInfo.get('citem'))})
                self.sysInfo['callback'] = self.jsonRPC.getCallback(self.sysInfo)# or (('%s%s'%(self.sysARG[0],self.sysARG[2])).split('%s&'%(slugify(ADDON_NAME))))[0])
                cacheResponse = self.cache.set(cacheName, __extend(pvritem), checksum=PROPERTIES.getInstanceID(), expiration=datetime.timedelta(seconds=FIFTEEN), json_data=True)
                del jsonRPC
        return cacheResponse


    def playTV(self, name: str, chid: str):
        self.log('playTV, id = %s'%(chid))
        with self.preparingPlayback(), PROPERTIES.suspendActivity():
            if self.sysInfo.get('fitem'):
                liz = LISTITEMS.buildItemListItem(self.sysInfo['fitem'])
                if (self.sysInfo.get('fitem').get('file','-1') == self.sysInfo.get('vid','0')): #-> live
                    if (self.sysInfo.get('seek',0) > self.seekTOL) and (self.sysInfo.get('progresspercentage') > 0 and self.sysInfo.get('progresspercentage') < 100 ):
                        self.log('playTV, id = %s, seek = %s'%(chid, self.sysInfo['seek']))
                        liz.setProperty('startoffset', str(self.sysInfo['seek'])) #secs
                        infoTag = ListItemInfoTag(liz,'video')
                        infoTag.set_resume_point({'ResumeTime':self.sysInfo['seek'],'TotalTime':(self.sysInfo['duration'] * 60)})
            else: liz = self.getPVRItems(name, chid)[0]
            liz.setProperty('sysInfo',encodeString(dumpJSON(self.sysInfo)))
            self.resolveURL(True, liz)
        

    def playLive(self, name: str, chid: str, vid: str):
        self.log('playLive, id = %s, name = %s'%(chid, name))
        with self.preparingPlayback(), PROPERTIES.suspendActivity():
            if self.sysInfo.get('fitem'):#-> live playback from UI incl. listitem
                liz = LISTITEMS.buildItemListItem(self.sysInfo['fitem'])
                if (self.sysInfo.get('fitem').get('file','-1') == self.sysInfo.get('vid','0')) or (self.sysInfo.get('seek',0) < self.seekTOL and self.sysInfo.get('progresspercentage',0) < self.seekTHD): #-> live
                    if (self.sysInfo.get('seek',0) > self.seekTOL) and (self.sysInfo.get('progresspercentage') > 0 and self.sysInfo.get('progresspercentage') < 100 ):
                        self.log('playLive, id = %s, seek = %s'%(chid, self.sysInfo['seek']))
                        liz.setProperty('startoffset', str(self.sysInfo['seek'])) #secs
                        infoTag = ListItemInfoTag(liz,'video')
                        infoTag.set_resume_point({'ResumeTime':self.sysInfo['seek'],'TotalTime':(self.sysInfo['duration'] * 60)})
                    liz.setProperty('sysInfo',encodeString(dumpJSON(self.sysInfo)))
                    self.resolveURL(True, liz)
                else: #-> VOD called by non-current EPG cell. (Unreliable during playback)
                    url = self.sysInfo['fitem'].get('catchup-id')
                    self.log('playLive, id = %s, VOD = %s'%(chid, url))
                    self.sysInfo['vid'] = self.sysInfo['fitem'].get('file',url)
                    DIALOG.notificationDialog(LANGUAGE(32185)%(self.sysInfo['fitem'].get('label',self.sysInfo.get('title',''))))
                    timerit(BUILTIN.executebuiltin)(0.1,['PlayMedia(%s)'%(url)])
                    self.resolveURL(False, xbmcgui.ListItem())
                # else: 
                    # DIALOG.notificationDialog(LANGUAGE(32000))
                    # timerit(BUILTIN.executebuiltin)(0.1,['Action(stop)'])
                    # self.resolveURL(False, xbmcgui.ListItem())
                #else: self.resolveURL(False, xbmcgui.ListItem())
            else:#-> onChange callback from "live" or widget or channel switch (change via input not ui)
                liz = xbmcgui.ListItem(name,path=vid)
                liz.setProperty("IsPlayable","true")
                if (self.sysInfo.get('seek',0) > self.seekTOL) and (self.sysInfo.get('progresspercentage') > 0 and self.sysInfo.get('progresspercentage') < 100 ):
                    self.log('playLive, id = %s, seek = %s'%(chid, self.sysInfo['seek']))
                    liz.setProperty('startoffset', str(self.sysInfo['seek'])) #secs
                    infoTag = ListItemInfoTag(liz,'video')
                    infoTag.set_resume_point({'ResumeTime':self.sysInfo['seek'],'TotalTime':(self.sysInfo['duration'] * 60)})
                liz.setProperty('sysInfo',encodeString(dumpJSON(self.sysInfo)))
                self.resolveURL(True, liz)


    def playBroadcast(self, name: str, chid: str, vid: str): #-> catchup-source
        self.log('playBroadcast, id = %s'%(chid))
        with self.preparingPlayback(), PROPERTIES.suspendActivity():
            if self.sysInfo.get('fitem'): #-> catchup-id called via ui "play programme"
                liz = LISTITEMS.buildItemListItem(self.sysInfo.get('fitem'))
            else:
                liz = xbmcgui.ListItem(name,path=vid)
                liz.setProperty("IsPlayable","true")
            self.sysInfo["seek"] = -1
            self.sysInfo["progresspercentage"] = -1
            liz.setProperty('sysInfo',encodeString(dumpJSON(self.sysInfo)))
            self.resolveURL(True, liz)
            
            
    def playVOD(self, title: str, vid: str): #-> catchup-id
        self.log('playVOD, title = %s, vid = %s'%(title,vid))
        with self.preparingPlayback(), PROPERTIES.suspendActivity():
            if self.sysInfo.get('fitem') and self.sysInfo.get('mode','').lower() != 'dvr': #-> live playback from UI incl. listitem
                liz = LISTITEMS.buildItemListItem(self.sysInfo.get('fitem'))
                self.sysInfo["seek"] = -1
                self.sysInfo["progresspercentage"] = -1
            else: #-> recordings, non UI callbacks.
                liz = xbmcgui.ListItem(title,path=vid)
                liz.setProperty("IsPlayable","true")
                if (self.sysInfo.get('seek',0) > self.seekTOL) and (self.sysInfo.get('progresspercentage') > 0 and self.sysInfo.get('progresspercentage') < 100 ):
                    self.log('playVOD, vid = %s, seek = %s'%(vid, self.sysInfo['seek']))
                    liz.setProperty('startoffset', str(self.sysInfo['seek'])) #secs
                    infoTag = ListItemInfoTag(liz,'video')
                    infoTag.set_resume_point({'ResumeTime':self.sysInfo['seek'],'TotalTime':(self.sysInfo['duration'] * 60)})
                else:
                    self.sysInfo["seek"] = -1
                    self.sysInfo["progresspercentage"] = -1
            liz.setProperty('sysInfo',encodeString(dumpJSON(self.sysInfo)))
            self.resolveURL(True, liz)
            
            
    def playRadio(self, name: str, chid: str, vid: str):
        self.log('playRadio, id = %s'%(chid))
        def buildfItem(item: dict={}): return LISTITEMS.buildItemListItem(item, 'music')
        with BUILTIN.busy_dialog():
            jsonRPC  = JSONRPC()
            fileList = interleave([jsonRPC.requestList({'id':chid}, path, 'music', page=RADIO_ITEM_LIMIT, sort={"method":"random"})[0] for path in vid.split('|')], SETTINGS.getSettingInt('Interleave_Value'))
            del jsonRPC

        if len(fileList) > 0:
            PLAYER().play(self.quePlaylist(poolit(buildfItem)(randomShuffle(fileList)),pltype=xbmc.PLAYLIST_MUSIC,shuffle=True),windowed=True)
            timerit(BUILTIN.executebuiltin)(0.1,['ReplaceWindow(visualisation)'])
        self.resolveURL(False, xbmcgui.ListItem())


    def playPlaylist(self, name: str, chid: str):
        self.log('playPlaylist, id = %s'%(chid))
        listitems = self.getPVRItems(name, chid)
        if len(listitems) > 0:
            PLAYER().play(self.quePlaylist(listitems),windowed=True)
        self.resolveURL(False, xbmcgui.ListItem())


    def playResume(self, name: str, chid: str):
        self.log('playResume, id = %s'%(chid))
        listitems = self.getResumeItems(name, chid)
        if len(listitems) > 0: PLAYER().play(self.quePlaylist(listitems),windowed=True)
        self.resolveURL(False, xbmcgui.ListItem())


    def playCheck(self, oldInfo: dict={}) -> bool:
        self.log('playCheck, sysInfo=%s\noldInfo = %s'%(self.sysInfo,oldInfo))
        def _chkPath():
            if not self.sysInfo.get('vid'): return True 
            elif   self.sysInfo.get('vid','').startswith(tuple(WEB_TYPES)): return True
            elif   self.sysInfo.get('vid','').startswith(tuple(VFS_TYPES)): return hasAddon(self.sysInfo.get('vid',''))
            elif   FileAccess.exists(self.sysInfo.get('vid','')): return True
            self.log('playCheck _chkPath, failed! path (%s) not found.'%(self.sysInfo.get('vid','')))
            if SETTINGS.getSettingBool('Debug_Enable'): DIALOG.notificationDialog(LANGUAGE(32167))
            return False
            
        def _chkLoop():
            if self.sysInfo.get('chid') == oldInfo.get('chid',random.random()):
                if self.sysInfo.get('start') == oldInfo.get('start',random.random()):
                    self.sysInfo['playcount'] = oldInfo.get('playcount',0) + 1 #carry over playcount
                    self.sysInfo['runtime']   = oldInfo.get('runtime',-1)      #carry over previous player runtime
                    
                    if self.sysInfo['now'] >= self.sysInfo['stop']:
                        self.log('playCheck _chkLoop, failed! Current time (%s) is past the contents stop time (%s).'%(self.sysInfo['now'],self.sysInfo['stop']))
                        if SETTINGS.getSettingBool('Debug_Enable'): DIALOG.notificationDialog("Current time (%s) is past the contents stop time (%s)."%(self.sysInfo['now'],self.sysInfo['stop']))
                        return False
                    elif self.sysInfo['duration'] > self.sysInfo['runtime'] and self.sysInfo['runtime'] > 0:
                        self.log('playCheck _chkLoop, failed! Duration error between player (%s) and pvr (%s).'%(self.sysInfo['duration'],self.sysInfo['runtime']))
                        if SETTINGS.getSettingBool('Debug_Enable'): DIALOG.notificationDialog("Duration error between player (%s) and pvr (%s)."%(self.sysInfo['duration'],self.sysInfo['runtime']))
                        return False
                    elif self.sysInfo['seek'] >= oldInfo.get('runtime',self.sysInfo['duration']):
                        self.log('playCheck _chkLoop, failed! Seeking to a position (%s) past media runtime (%s).'%(self.sysInfo['seek'],oldInfo.get('runtime',self.sysInfo['duration'])))
                        if SETTINGS.getSettingBool('Debug_Enable'): DIALOG.notificationDialog("Seeking to a position (%s) past media runtime (%s)."%(self.sysInfo['seek'],oldInfo.get('runtime',self.sysInfo['duration'])))
                        return False
                    elif self.sysInfo['seek'] == oldInfo.get('seek',self.sysInfo['seek']):
                        self.log('playCheck _chkLoop, failed! Seeking to same position.')
                        if SETTINGS.getSettingBool('Debug_Enable'): DIALOG.notificationDialog("Playback Failed: Seeking to same position")
                        return False
            return True

        _chkPath()
        _chkLoop()
        #todo take action on fail. for now log events and strategize actions. 
        return True
        
        
    def playError(self):
        self.log('playError, id = %s, attempt = %s\n%s'%(self.sysInfo.get('chid','-1'),self.sysInfo.get('playcount'),self.sysInfo))
        PROPERTIES.setEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID),encodeString(dumpJSON(self.sysInfo)))
        if self.sysInfo.get('playcount') in [1,2,3]:
            with BUILTIN.busy_dialog():
                DIALOG.notificationWait(LANGUAGE(32038)%(self.sysInfo.get('playcount',0)))
            self.resolveURL(False, xbmcgui.ListItem()) #release pending playback.
            MONITOR().waitForAbort(1.0) #allow a full second to pass beyond any msecs differential.
            return BUILTIN.executebuiltin('PlayMedia(%s%s)'%(self.sysARG[0],self.sysARG[2])) #retry channel
        elif self.sysInfo.get('playcount') == 4: DIALOG.okDialog(LANGUAGE(32134)%(ADDON_NAME))
        else: DIALOG.notificationWait(LANGUAGE(32000))
        self.resolveURL(False, xbmcgui.ListItem()) #release pending playback
        DIALOG.closeBusyDialog()
        
        
    def resolveURL(self, found, listitem):
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), found, listitem)