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
from typing              import Optional, Tuple
from variables           import *
from _services           import _Service
from rules               import RulesList
from infotagger.listitem import ListItemInfoTag

class Plugin(object):
    def __init__(self, mode: str = 'playlist', sysInfo: dict = {}):
        self.service = _Service()   
        self.pool    = self.service.pool
        self.jsonRPC = self.service.jsonRPC
        self.cache   = self.service.cache
        self.monitor = self.service.monitor
        self.sysInfo = sysInfo
        self.sysInfo['seek'] = (sysInfo.get('seek') or abs(int(sysInfo.get('start',-1)) - int(sysInfo.get('now',-1))) if int(sysInfo.get('start',-1)) > 0 else -1)
        self.sysInfo["progresspercentage"] = round((self.sysInfo["seek"]/int(self.sysInfo["duration"])) * 100, 2) if self.sysInfo['seek'] > 0 else -1 
        
        if not self.sysInfo.get('fitem'): 
            self._updateSysInfo() #Widgets don't include listitem meta, attempt to find matching meta with jsonrpc
            
        self.sysInfo['isVOD']      = False#self.sysInfo.get('fitem').get('file','-1') != self.sysInfo.get('vid','-1')
        self.sysInfo['isSTRM']     = self.sysInfo.get('fitem').get('file','').endswith('.strm')
        self.sysInfo['isPlaylist'] = bool(Globals.settings.getSettingInt('Playback_Method'))
        mode = 'playlist' if any((self.sysInfo['isVOD'],self.sysInfo['isSTRM'],self.sysInfo['isPlaylist'])) else sysInfo.get('mode')
        self.log(f'__init__, mode = {mode}, sysInfo = {self.sysInfo}')
        
        with Globals.builtin.busy_dialog():
            if   mode == 'live':                    self.playLive()
            elif mode == 'radio':                   self.playRadio()
            elif mode == 'resume':                  self.playPaused()
            elif mode in ['vod','dvr']:             self.playVOD()
            elif mode in ['playlist','broadcast']:  self.playPlaylist()
        
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)

            
    def _updateSysInfo(self):
        self.log('[%s] _updateSysInfo'%(self.sysInfo.get('chid')))
        if not self.service.player.isPlaying() and Globals.settings.getSettingBool('Debug_Enable'): Globals.dialog.notificationDialog('%s %s\n%s'%(LANGUAGE(32248),LANGUAGE(30223),LANGUAGE(32140)))
        with Globals.properties.suspendActivity():
            pvritem = self.jsonRPC.matchChannel(self.sysInfo.get('name'),self.sysInfo.get('chid'),self.sysInfo.get('radio',False),extend=False)
        if pvritem:
            self.sysInfo['fitem'] = Globals._decodePlot(pvritem.get('broadcastnow',{}).get('plot',''))
            self.sysInfo['nitem'] = Globals._decodePlot(pvritem.get('broadcastnext',[{}])[0].get('plot',''))
        else:
            self.log('[%s] _updateSysInfo, channel not found in PVR, may need refresh' % self.sysInfo.get('chid'), xbmc.LOGWARNING)
            Globals.dialog.notificationDialog(LANGUAGE(32000))
                
            
    def _quePlaylist(self, listitems: list, pltype: int = xbmc.PLAYLIST_VIDEO, shuffle: Optional[bool] = None) -> Optional[Tuple[xbmc.PlayList, xbmcgui.ListItem]]:
        def __add(listitem: xbmcgui.ListItem):
            if listitem.getPath():
                playlist.add(listitem.getPath(),listitem,listitems.index(listitem))
                
        if listitems:
            self.sysInfo['isPlaylist'] = True
            if shuffle is None: shuffle = Globals.builtin.isPlaylistRandom()
            self.log('[%s] _quePlaylist, listitems = %s, shuffle = %s'%(self.sysInfo.get('chid'), len(listitems), shuffle))
            playlist = xbmc.PlayList(pltype)
            playlist.clear()
            xbmc.sleep(100)#give playlist.clear() enough time to clear queue.           
            poolit(__add)(listitems)
            self.log('[%s] _quePlaylist, Playlist size = %s, shuffle = %s'%(self.sysInfo.get('chid'), playlist.size(),shuffle))
            if shuffle: playlist.shuffle()
            else:       playlist.unshuffle()
            return playlist, listitems[0]


    def _getPVRItems(self) -> list:
        def __findCurrent(items: list, byFile: bool = True, found: int = -1) -> list:
            for pos, nextitem in enumerate(items):
                fitem = Globals._decodePlot(nextitem.get('plot',{}))
                if byFile and self.sysInfo.get('fitem',{}).get('file').lower() == fitem.get('file','').lower(): found = pos
                elif not byFile and ntime >= Globals._strpTime(nextitem.get('starttime')) and ntime < Globals._strpTime(nextitem.get('endtime')) and self.sysInfo.get('chid') == fitem.get('citem',{}).get('id',str(random.random())): found = pos
                if found >= 0:
                    self.log('[%s] __buildPlaylist __findCurrent found match!'%(self.sysInfo.get('chid')))
                    items = items[found:]
                    break
                
            if len(items) > 0:
                if self.sysInfo.get('mode',False) == 'playlist':
                    # Offset start based on user configured tolerances. 
                    nowitem = items.pop(0)
                    # content almost concluded, move to next queued item
                    if round(nowitem['progresspercentage']) > Globals.settings.getSettingInt('Seek_Threshold'):
                        self.log('[%s] __buildPlaylist, __findCurrent progress past threshold advance to nextitem'%(self.sysInfo.get('chid')))
                        nowitem = items.pop(0)
                    # content just started, reset seek and progress to the beginning. 
                    if round(nowitem['progress']) < Globals.settings.getSettingInt('Seek_Tolerance'):
                        self.log('[%s] __buildPlaylist, __findCurrent progress start at the beginning'%(self.sysInfo.get('chid')))
                        nowitem['progress']           = 0
                        nowitem['progresspercentage'] = 0
                    with Globals.properties.suspendActivity():
                        self.sysInfo['callback'] = self.jsonRPC.getCallback(self.sysInfo)
                    items = items[:Globals.settings.getSettingInt('Page_Limit')]# list of upcoming items, truncate for speed
                    items.insert(0,nowitem)
                Globals._combineDicts(self.sysInfo['fitem'],items[0].get('fitem',{}))
            self.log('[%s] __buildPlaylist, __findCurrent building nextitems (%s)'%(self.sysInfo.get('chid'),len(items)))
            return items
            
        self.log('[%s] _getPVRItems'%(self.sysInfo.get('chid')))
        with Globals.properties.suspendActivity():
            pvritem = self.jsonRPC.matchChannel(self.sysInfo.get('name'),self.sysInfo.get('chid'),self.sysInfo.get('radio',False),extend=True)
        
        if pvritem:
            pastItems = pvritem.get('broadcastpast',[]) # past items
            nowitem   = pvritem.get('broadcastnow',{})  # current item
            nextitems = pvritem.get('broadcastnext',[]) # future items
            nextitems.insert(0,nowitem)
            nextitems = pastItems + nextitems
            # start array at correct position
            if   self.sysInfo['fitem'].get('file'): nextitems = __findCurrent(nextitems)
            else:                                   nextitems = __findCurrent(nextitems, byFile=False)
            if len(nextitems) > 0: return nextitems
            else: Globals.dialog.notificationDialog(LANGUAGE(32164))
        else: Globals.dialog.notificationDialog(LANGUAGE(32000))
        return []
                   
                   
    def _setResume(self, listitem: xbmcgui.ListItem) -> xbmcgui.ListItem:
        if self.sysInfo.get('seek',0) > Globals.settings.getSettingInt('Seek_Tolerance') and self.sysInfo.get('progresspercentage',100) < 100:
            self.log('[%s] _setResume, seek = %s, progresspercentage = %s\npath = %s'%(self.sysInfo.get('chid'), self.sysInfo.get('seek',0), self.sysInfo.get('progresspercentage',100), listitem.getPath()))
            listitem.setProperty('startoffset', str(self.sysInfo['seek'])) #secs
            infoTag = ListItemInfoTag(listitem,'video')
            infoTag.set_resume_point({'ResumeTime':self.sysInfo['seek'],'TotalTime':(self.sysInfo['duration'] * 60)})
        return listitem

        
    @threadit
    def playLive(self):
        self.log('[%s] playLive, name = %s'%(self.sysInfo.get('chid'), self.sysInfo.get('name')))
        #VOD called from Guide not live! / break PVR bind for correct meta.
        if self.sysInfo['isVOD'] or self.sysInfo['isSTRM']:
            if self.sysInfo['isVOD']:
                self.sysInfo['mode'] = 'vod'
                self.sysInfo["seek"] = -1
                self.sysInfo["progresspercentage"] = -1
                self.sysInfo['name'] = self.sysInfo['fitem'].get('label')
                self.sysInfo['vid']  = self.sysInfo['fitem'].get('file')
                Globals.dialog.notificationDialog(f"{LANGUAGE(32185)%('Channel')}: [B]{self.sysInfo['fitem'].get('label')}[/B]\n{self.sysInfo['fitem'].get('episodelabel')}")
                listitem = Globals.listitems.buildItemListItem(self.sysInfo.get('fitem'))
            else:
                #STRM called from Guide, presumably live; workaround for Kodi bug w/strm handling in setResolvedUrl.
                listitem = self._setResume(Globals.listitems.buildItemListItem(self.sysInfo.get('fitem')))
            listitem.setProperty('sysInfo',FileAccess._encodeString(self.sysInfo))
            self._play(listitem.getPath(),listitem)
        else:#LIVE called from Guide/Channels.
            listitem = self._setResume(Globals.listitems.buildItemListItem(self.sysInfo.get('fitem')))
            listitem.setProperty('sysInfo',FileAccess._encodeString(self.sysInfo))
            self._resolveURL(True, listitem)
    
            
    @threadit
    def playRadio(self, limit: int = RADIO_ITEM_LIMIT):
        def __buildfItem(item: dict = {}) -> xbmcgui.ListItem:
            sysInfo = self.sysInfo.copy()
            sysInfo['isPlaylist'] = True
            listitem = Globals.listitems.buildItemListItem(item,'music')
            listitem.setProperty('sysInfo',FileAccess._encodeString(sysInfo))
            return listitem
            
        def __buildPlaylist(chid: str, name: str) -> list:
            with Globals.properties.suspendActivity():
                return Globals._randomShuffle(Globals._interleave([self.jsonRPC.requestList({'id':chid}, path, 'music', page=limit, sort={"method":"random"})[0] for path in self.sysInfo.get('vid').split('|')], Globals.settings.getSettingInt('Interleave_Set'), Globals.settings.getSettingBool('Interleave_Repeat')))
        
        self.log('[%s] playRadio, name = %s'%(self.sysInfo.get('chid'), self.sysInfo.get('name')))
        listitems = poolit(__buildfItem)(__buildPlaylist(self.sysInfo.get('chid'),self.sysInfo.get('name')))
        self._play(*(self._quePlaylist(listitems, pltype=xbmc.PLAYLIST_MUSIC, shuffle=True)))
               
                      
    @threadit         
    def playPaused(self):
        def __buildfItem(item: dict = {}) -> Optional[xbmcgui.ListItem]:
            sysInfo = self.sysInfo.copy()
            sysInfo['isPlaylist'] = True
            listitem = Globals.listitems.buildItemListItem(item,'video')
            if FileAccess.exists(listitem.getPath()):  #todo insert missing media placeholder
                if item.get('file') == item.get('resume',{}).get('file',str(random.random())):
                    seektime = int(item.get('resume',{}).get('position',0.0))
                    runtime  = int(item.get('resume',{}).get('total',0.0))
                    self.log('[%s] __buildfItem, within seek tolerance setting seek totaltime = %s, resumetime = %s'%(chid, runtime, seektime))
                    listitem.setProperty('startoffset', str(seektime)) #secs
                    infoTag = ListItemInfoTag(listitem, 'video')
                    infoTag.set_resume_point({'ResumeTime':seektime, 'TotalTime':runtime * 60})
                    
                sysInfo.update({'fitem':item,'resume':{"idx":lizLST.index(item)}})
                listitem.setProperty('sysInfo',FileAccess._encodeString(sysInfo))
                return listitem
            
        def __buildPlaylist(chid: str, name: str) -> list:
            lizLST = RulesList([self.sysInfo.get('fitem',{}).get('citem',{'name':name,'id':chid})]).runActions(RULES_ACTION_PLAYBACK_RESUME, self.sysInfo.get('fitem',{}).get('citem',{'name':name,'id':chid}))
            if lizLST:
                lizLST = nextitems[:Globals.settings.getSettingInt('Page_Limit')]
                self.log('[%s] __buildPlaylist, building lizLST (%s)'%(chid, len(lizLST)))
                return poolit(__buildfItem)(lizLST)
            else: Globals.dialog.notificationDialog(LANGUAGE(32000))
            return []
        
        self.log('[%s] playPaused, name = %s'%(self.sysInfo.get('chid'), self.sysInfo.get('name')))
        listitems = self.__buildPlaylist(self.sysInfo.get('chid'), self.sysInfo.get('name'))
        self._play(*(self._quePlaylist(listitems, pltype=xbmc.PLAYLIST_VIDEO, shuffle=False)))
            
            
    @threadit         
    def playVOD(self):
        self.log('[%s] playVOD, vid = %s'%(self.sysInfo.get('chid'), self.sysInfo.get('vid')))
        self.sysInfo["seek"] = -1
        self.sysInfo["progresspercentage"] = -1
        Globals.dialog.notificationDialog(f"{LANGUAGE(32185)%('VOD')}: [B]{self.sysInfo['fitem'].get('label')}[/B]\n{self.sysInfo['fitem'].get('episodelabel')}")
        self._resolveURL(True, Globals.listitems.buildItemListItem(self.sysInfo.get('fitem')))
            
            
    @threadit
    def playPlaylist(self):
        def __buildfItem(nextitem: dict = {}) -> Optional[xbmcgui.ListItem]:
            sysInfo = self.sysInfo.copy()
            sysInfo['isPlaylist'] = True
            idx      = nextitems.index(nextitem)
            fitem    = Globals._decodePlot(nextitem.get('plot',''))
            listitem = Globals.listitems.buildItemListItem(fitem,'video')
            if FileAccess.exists(listitem.getPath()): #todo insert missing media placeholder
                if not self.sysInfo['isVOD']:
                    listitem = self._setResume(Globals.listitems.buildItemListItem(self.sysInfo.get('fitem')))
                sysInfo.update({'fitem':fitem,'resume':{"idx":idx}})
                listitem.setProperty('sysInfo',FileAccess._encodeString(sysInfo))
                return listitem
            
        self.log('[%s] playPlaylist, name = %s'%(self.sysInfo.get('chid'), self.sysInfo.get('name')))
        Globals.dialog.notificationDialog(f"{LANGUAGE(32185)%('Playlist')}: [B]{self.sysInfo['name']}[/B]\n{self.sysInfo['fitem'].get('label')}")
        nextitems = self._getPVRItems()
        listitems = poolit(__buildfItem)(nextitems)
        self._play(*(self._quePlaylist(listitems, pltype=xbmc.PLAYLIST_VIDEO, shuffle=False)))
        
            
    def _playCheck(self, path: str, found: bool, listitem: Optional[xbmcgui.ListItem] = None) -> Tuple[str, bool, xbmcgui.ListItem]:
        def __findMissing(listitem: xbmcgui.ListItem) -> Tuple[bool, xbmcgui.ListItem]:
            label = (self.sysInfo['fitem'].get('label') or listitem.getLabel())
            file  = (self.sysInfo['fitem'].get('file')  or listitem.getPath())
            if file.startswith(tuple(VFS_TYPES)): found = True
            else:
                folder, filename  = os.path.split(file)
                oSeason, oEpisode = Globals._parseSE(filename)
                self.log(f"[{self.sysInfo.get('chid')}] _playCheck, __findMissing searching {label}: {filename} in {folder}")
                Globals.dialog.notificationDialog(f"Missing: [B]{self.sysInfo['fitem'].get('label')}[/B]\n{self.sysInfo['fitem'].get('episodelabel')}")
                with Globals.properties.suspendActivity():
                    items, limits, errors = self.jsonRPC.getDirectory({"directory":folder,"media": "video"})
                    
                found = False
                for item in items:
                    if item.get('file','').endswith(tuple(VIDEO_EXTS)):
                        season, episode  = Globals._parseSE(os.path.split(item.get('file',''))[1])
                        if item.get('type') == 'movies' and item.get('label','').lower() == label.lower():
                            found = True
                            break
                        elif oSeason and oEpisode and (oSeason == season and oEpisode == episode):
                            found = True
                            break
                if found: 
                    Globals._combineDicts(self.sysInfo['fitem'],item)
                    listitem.setPath(self.sysInfo['fitem']['file'])
                    self.log(f"[{self.sysInfo.get('chid')}] _playCheck, __findMissing found {self.sysInfo['fitem']['file']}")
                    Globals.dialog.notificationDialog(f"Found: [B]{self.sysInfo['fitem'].get('label')}[/B]\n{self.sysInfo['fitem'].get('episodelabel')}")
                #else: listitem.setPath(insert missing media placeholder)
            return found, listitem
            
        #File Exists
        if listitem is None: listitem = xbmcgui.ListItem()
        if not FileAccess.exists(listitem.getPath()): found, listitem = __findMissing(listitem)
        #TODO ROBOUST ERROR CORRECTION
        if self.sysInfo['isPlaylist']: return path, found, listitem
        else:                          return listitem.getPath(), found, listitem


    def _play(self, file: str, listitem: Optional[xbmcgui.ListItem] = None, wait: int = 30):
        #PVR Live Channel Detection workaround.
        if listitem is None: listitem = xbmcgui.ListItem()
       
        while not self.monitor.abortRequested() and self.player.isPlaying():
            if    self.monitor.waitForAbort(0.5): return
            else: self.player.stop()
            
        file, found, listitem = self._playCheck(file, True, listitem)
        timerit(self.player.play)(1.0,*(file,listitem))
        self._resolveURL(False, listitem)
        #Playlist don't always gain screen focus depending on user Kodi configuration. Force fullscreen.
        self.log(f"[{self.sysInfo.get('chid')}] _play, found = {found}, playlist = {self.sysInfo['isPlaylist']}")
        
        while not self.monitor.abortRequested() and not self.player.isPlaying():
            if self.monitor.waitForAbort(0.5) or wait < 1: return
            wait -= 1
            
        if self.player.isPlayingAudio(): window = 'visualisation'
        else:                            window = 'fullscreenvideo'
        timerit(Globals.builtin.executewindow)(1.0,*('ActivateWindow(%s)'%(window),True,False,self.player.isPlaying))


    def _resolveURL(self, found: bool = False, listitem: Optional[xbmcgui.ListItem] = None):
        self.log(f"[{self.sysInfo.get('chid')}] _resolveURL, found = {found}: {listitem.getPath()}")
        if listitem is None: listitem = xbmcgui.ListItem()
        else: _, found, listitem = self._playCheck(listitem.getPath(), found, listitem)
        xbmcplugin.setResolvedUrl(int(self.sysInfo['sysARG'][1]), found, listitem)
        
        