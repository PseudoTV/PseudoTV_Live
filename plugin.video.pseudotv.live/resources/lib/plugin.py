#   Copyright (C) 2025 Lunatixz
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
from globals             import *
from jsonrpc             import JSONRPC
from rules               import RulesList
from infotagger.listitem import ListItemInfoTag

class Plugin(object):
    def __init__(self, sysARG=sys.argv, sysInfo={}):
        with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
            self.sysARG  = sysARG
            self.sysInfo = sysInfo
            self.jsonRPC = JSONRPC()
            self.cache   = SETTINGS.cache
            
            self.sysInfo['now']   = int(sysInfo.get('now')   or int(getUTCstamp()))
            self.sysInfo['start'] = int(sysInfo.get('start') or '-1')
            self.sysInfo['stop']  = int(sysInfo.get('stop')  or '-1')
            self.sysInfo['citem'] = (sysInfo.get('citem')    or combineDicts({'id':sysInfo.get("chid")},sysInfo.get('fitem',{}).get('citem',{})))
            
            if sysInfo.get('fitem'):
                if sysInfo.get("nitem"): self.sysInfo.update({'citem':combineDicts(self.sysInfo["nitem"].pop('citem'),self.sysInfo["fitem"].pop('citem'))})
                else:                    self.sysInfo.update({'citem':combineDicts(self.sysInfo["citem"],self.sysInfo["fitem"].pop('citem'))})
                
                if self.sysInfo.get('start') == -1:
                    self.sysInfo['start'] = (self.sysInfo['fitem'].get('start') or -1)
                    self.sysInfo['stop']  = (self.sysInfo['fitem'].get('stop')  or -1)
                self.sysInfo['duration']  = float(sysInfo.get('duration')       or self.jsonRPC._getRuntime(self.sysInfo['fitem']) or timeString2Seconds(BUILTIN.getInfoLabel('Duration(hh:mm:ss)')))
            else:
                self.sysInfo['duration']  = float((sysInfo.get('duration')      or '-1'))
            try:
                self.sysInfo['seek'] = int(sysInfo.get('seek') or (abs(self.sysInfo['start'] - self.sysInfo['now']) if self.sysInfo['start'] > 0 else -1))
                self.sysInfo["progresspercentage"] = -1 if self.sysInfo['seek'] == -1 else (self.sysInfo["seek"]/self.sysInfo["duration"]) * 100
            except:
                self.sysInfo['seek'] = int(sysInfo.get('seek','-1'))
                self.sysInfo["progresspercentage"] = -1
                
            self.log('__init__, sysARG = %s\nsysInfo = %s'%(sysARG,self.sysInfo))

                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _setResume(self, chid, listitem):
        if self.sysInfo.get('seek',0) > SETTINGS.getSettingInt('Seek_Tolerance') and self.sysInfo.get('progresspercentage',100) < 100:
            self.log('[%s] _setResume, seek = %s, progresspercentage = %s\npath = %s'%(chid, self.sysInfo.get('seek',0), self.sysInfo.get('progresspercentage',100), listitem.getPath()))
            listitem.setProperty('startoffset', str(self.sysInfo['seek'])) #secs
            infoTag = ListItemInfoTag(listitem,'video')
            infoTag.set_resume_point({'ResumeTime':self.sysInfo['seek'],'TotalTime':(self.sysInfo['duration'] * 60)})
        else:
            self.sysInfo["seek"] = -1
            self.sysInfo["progresspercentage"] = -1
            listitem.setProperty('startoffset', str(0)) #secs
            infoTag = ListItemInfoTag(listitem,'video')
            infoTag.set_resume_point({'ResumeTime':0,'TotalTime':(self.sysInfo['duration'] * 60)})
        return listitem
            
            
    def _cuePlaylist(self, chid, listitems, pltype=xbmc.PLAYLIST_VIDEO, shuffle=BUILTIN.isPlaylistRandom()):
        self.log('[%s] _cuePlaylist, listitems = %s, shuffle = %s'%(chid, len(listitems),shuffle))
        channelPlaylist = xbmc.PlayList(pltype)
        channelPlaylist.clear()
        xbmc.sleep(100) #give channelPlaylist.clear() enough time to clear queue.
        [channelPlaylist.add(listitem.getPath(),listitem,idx) for idx,listitem in enumerate(listitems) if listitem.getPath()]
        self.log('[%s] _cuePlaylist, Playlist size = %s, shuffle = %s'%(chid, channelPlaylist.size(),shuffle))
        if shuffle: channelPlaylist.shuffle()
        else:       channelPlaylist.unshuffle()
        return channelPlaylist


    def getRadioItems(self, name, chid, vid, limit=RADIO_ITEM_LIMIT):
        self.log('[%s] getRadioItems'%(chid))
        return interleave([self.jsonRPC.requestList({'id':chid}, path, 'music', page=limit, sort={"method":"random"})[0] for path in vid.split('|')], SETTINGS.getSettingInt('Interleave_Set'), SETTINGS.getSettingBool('Interleave_Repeat'))

    
    def getPausedItems(self, name, chid):
        self.log('[%s] getPausedItems'%(chid))
        def __buildfItem(item):
            if 'citem' in item: item.pop('citem')
            sysInfo = self.sysInfo.copy()
            sysInfo['isPlaylist'] = True
            listitem = LISTITEMS.buildItemListItem(item,'video')
            
            if item.get('file') == item.get('resume',{}).get('file',str(random.random())):
                seektime = int(item.get('resume',{}).get('position',0.0))
                runtime  = int(item.get('resume',{}).get('total',0.0))
                self.log('[%s] getPausedItems, within seek tolerance setting seek totaltime = %s, resumetime = %s'%(chid, runtime, seektime))
                listitem.setProperty('startoffset', str(seektime)) #secs
                infoTag = ListItemInfoTag(listitem, 'video')
                infoTag.set_resume_point({'ResumeTime':seektime, 'TotalTime':runtime * 60})
                
            sysInfo.update({'fitem':item,'resume':{"idx":nextitems.index(item)}})
            listitem.setProperty("IsPlayable","true")
            listitem.setProperty('sysInfo',Globals._encodeString(FileAccess.dumpJSON(sysInfo)))
            return listitem
        
        nextitems = RulesList([self.sysInfo.get('citem',{'name':name,'id':chid})]).runActions(RULES_ACTION_PLAYBACK_RESUME, self.sysInfo.get('citem',{'name':name,'id':chid}))
        if nextitems:
            nextitems = nextitems[:SETTINGS.getSettingInt('Page_Limit')]# list of upcoming items, truncate for speed
            self.log('[%s] getPausedItems, building nextitems (%s)'%(chid, len(nextitems)))
            with PROPERTIES.setBackgroundLabel('Building Playlist...') as setLabel:
                return poolit(__buildfItem)(nextitems) #[__buildfItem(idx, nextitem) for idx, nextitem in enumerate(nextitems)]
        else: DIALOG.notificationDialog(LANGUAGE(32000))
        return []
    
        
    def getPVRItems(self, name: str, chid: str) -> list:
        self.log('[%s] getPVRItems, chname = %s'%(chid,name))
        def __buildfItem(item):
            sysInfo = self.sysInfo.copy()
            nowitem = Globals._decodePlot(item.get('plot',''))
            if 'citem' in nowitem: nowitem.pop('citem')
            nowitem['pvritem'] = item
            sysInfo.update({'fitem':nowitem,'position':nextitems.index(item)})
            
            try: #next broadcast
                nextitem = Globals._decodePlot(nextitems[idx+1][1].get('plot',''))
                if 'citem' in nextitem: nextitem.pop('citem')
                nextitem.get('customproperties',{})['pvritem'] = nextitems[idx + 1]
                sysInfo.update({'nitem':nextitem})
            except: pass
            
            listitem = LISTITEMS.buildItemListItem(nowitem,'video')
            if (item.get('progress',0) > 0 and item.get('runtime',0) > 0):
                self.log('[%s] getPVRItems, within seek tolerance setting seek totaltime = %s, resumetime = %s'%(chid,(item['runtime'] * 60),item['progress']))
                listitem.setProperty('startoffset', str(item['progress'])) #secs
                infoTag = ListItemInfoTag(listitem, 'video')
                infoTag.set_resume_point({'ResumeTime':item['progress'],'TotalTime':(item['runtime'] * 60)})
            listitem.setProperty("IsPlayable","true")
            listitem.setProperty('sysInfo',Globals._encodeString(FileAccess.dumpJSON(sysInfo)))
            return listitem
            
        found   = False
        pvritem = self.jsonRPC.matchChannel(name,chid,radio=False)
        if pvritem:
            pastItems = pvritem.get('broadcastpast',[])
            nowitem   = pvritem.get('broadcastnow',{})
            nextitems = pvritem.get('broadcastnext',[]) # upcoming items
            nextitems.insert(0,nowitem)
            nextitems = pastItems + nextitems
       
            if (self.sysInfo.get('fitem') or self.sysInfo.get('vid')):
                for pos, nextitem in enumerate(nextitems):
                    fitem = Globals._decodePlot(nextitem.get('plot',{}))
                    file  = self.sysInfo.get('fitem',{}).get('file') if self.sysInfo.get('fitem') else self.sysInfo.get('vid')
                    if file == fitem.get('file') and self.sysInfo.get('citem',{}).get('id') == fitem.get('citem',{}).get('id',str(random.random())):
                        found = True
                        self.log('[%s] getPVRItems found matching fitem'%(chid))
                        del nextitems[0:pos] # start array at correct position
                        break
                        
            elif self.sysInfo.get('now') and self.sysInfo.get('vid'):
                for pos, nextitem in enumerate(nextitems):
                    fitem = Globals._decodePlot(nextitem.get('plot',{}))
                    ntime = epochTime(float(self.sysInfo.get('now')),tz=False)
                    if ntime >= strpTime(nextitem.get('starttime')) and ntime < strpTime(nextitem.get('endtime')) and chid == fitem.get('citem',{}).get('id',str(random.random())):
                        found = True
                        self.log('[%s] getPVRItems found matching starttime'%(chid))
                        del nextitems[0:pos] # start array at correct position
                        break
                        
            elif nowitem: found = True
                
            if found:
                nowitem = nextitems.pop(0)
                if round(nowitem['progresspercentage']) > SETTINGS.getSettingInt('Seek_Threshold'):
                    self.log('[%s] getPVRItems, progress past threshold advance to nextitem'%(chid))
                    nowitem = nextitems.pop(0)
                
                if round(nowitem['progress']) < SETTINGS.getSettingInt('Seek_Tolerance'):
                    self.log('[%s] getPVRItems, progress start at the beginning'%(chid))
                    nowitem['progress']           = 0
                    nowitem['progresspercentage'] = 0
                        
                self.sysInfo.update({'citem':Globals._decodePlot(nowitem.get('plot','')).get('citem',self.sysInfo.get('citem'))})
                self.sysInfo['callback'] = self.jsonRPC.getCallback(self.sysInfo)
                nextitems = nextitems[:SETTINGS.getSettingInt('Page_Limit')]# list of upcoming items, truncate for speed
                nextitems.insert(0,nowitem)
                self.log('[%s] getPVRItems, building nextitems (%s)'%(chid,len(nextitems)))
                with PROPERTIES.setBackgroundLabel('Building Playlist...') as setLabel:
                    return poolit(__buildfItem)(nextitems) #[__buildfItem(idx, item) for idx, item in enumerate(nextitems)]
            else: DIALOG.notificationDialog(LANGUAGE(32164))
        else: DIALOG.notificationDialog(LANGUAGE(32000))
        return [xbmcgui.ListItem()]
    

    @threadit
    def playTV(self, name: str, chid: str):
        self.log('[%s] playTV'%(chid))
        with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
            if self.sysInfo.get('fitem') and (self.sysInfo.get('fitem').get('file','-1') == self.sysInfo.get('vid','0')): #-> live
                listitem = self._setResume(chid, LISTITEMS.buildItemListItem(self.sysInfo['fitem']))
            else:
                listitem = self.getPVRItems(name, chid)[0]
            self._resolveURL(True, listitem)
        

    @threadit
    def playLive(self, name: str, chid: str, vid: str):
        self.log('[%s] playLive, name = %s'%(chid, name))
        with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
            if self.sysInfo.get('fitem').get('file','-1') == vid:#-> live playback from UI incl. listitem
                listitem = self._setResume(chid, LISTITEMS.buildItemListItem(self.sysInfo['fitem']))
                self._resolveURL(True, listitem)
            elif self.sysInfo.get('fitem'):#-> VOD called by non-current EPG cell. (Unreliable during playback)  
                self.sysInfo['mode'] = 'vod'
                self.sysInfo['name'] = self.sysInfo['fitem'].get('label')
                self.sysInfo['vid']  = self.sysInfo['fitem'].get('file')
                self.sysInfo["seek"] = -1
                self.sysInfo["progresspercentage"] = -1
                self.log('[%s] playLive, VOD = %s'%(chid, self.sysInfo['vid']))
                DIALOG.notificationDialog(LANGUAGE(32185)%(self.sysInfo['name']))
                listitem = LISTITEMS.buildItemListItem(self.sysInfo.get('fitem'))
                listitem.setProperty("IsPlayable","true")
                listitem.setProperty('sysInfo',Globals._encodeString(FileAccess.dumpJSON(self.sysInfo)))
                timerit(PLAYER().play)(1.0,[self.sysInfo['vid'],listitem,True])
                self._resolveURL(False, listitem)
            elif vid:#-> onChange callback from "live" or widget or channel switch (change via input not ui)
                self.log('[%s] playLive, VID = %s'%(chid, vid))
                listitem = self._setResume(chid, xbmcgui.ListItem(name,path=vid))
                self._resolveURL(True, listitem)
            else:#lookup current media via jsonRPC
                self.playTV(name, chid)


    @threadit
    def playBroadcast(self, name: str, chid: str, vid: str): #-> catchup-source
        self.log('[%s] playBroadcast'%(chid))
        with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
            if self.sysInfo.get('fitem'): #-> catchup-id called via ui "play programme"
                listitem = LISTITEMS.buildItemListItem(self.sysInfo.get('fitem'))
            else:
                listitem = xbmcgui.ListItem(name,path=vid)
            self.sysInfo["seek"] = -1
            self.sysInfo["progresspercentage"] = -1
            self._resolveURL(True, listitem)
            
            
    @threadit
    def playVOD(self, title: str, vid: str): #-> catchup-id
        self.log('[%s] playVOD, title = %s'%(vid,title))
        with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
            self._resolveURL(True, LISTITEMS.buildItemListItem(self.sysInfo.get('fitem')))


    @threadit
    def playDVR(self, title: str, vid: str): #-> catchup-id
        self.log('[%s] playDVR, title = %s'%(vid, title))
        with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
            self._resolveURL(True, self._setResume(vid, LISTITEMS.buildItemListItem(self.sysInfo.get('fitem'))))


    @threadit
    def playRadio(self, name: str, chid: str, vid: str):
        self.log('[%s] playRadio'%(chid))
        def __buildfItem(item: dict={}):
            return LISTITEMS.buildItemListItem(item, 'music')
        with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
            items = randomShuffle(self.getRadioItems(name, chid, vid))
            with PROPERTIES.setBackgroundLabel('Building Playlist...') as setLabel:
                listitems = poolit(__buildfItem)(items) #[__buildfItem(idx, item) for idx, item in enumerate(items)]
            if len(listitems) > 0: 
                playlist = self._cuePlaylist(chid, listitems, pltype=xbmc.PLAYLIST_MUSIC, shuffle=True)
                # BUILTIN.executewindow('ReplaceWindow(visualisation)',delay=OSD_TIMER,condition=BUILTIN.isPlaying)
                # BUILTIN.executebuiltin('Dialog.Close(all)')
                PLAYER().play(playlist,windowed=True)
            self._resolveURL(False, xbmcgui.ListItem())


    @threadit
    def playPlaylist(self, name: str, chid: str):
        self.log('[%s] playPlaylist'%(chid))
        with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
            listitems = self.getPVRItems(name, chid)
            if len(listitems) > 0: 
                playlist = self._cuePlaylist(chid, listitems,shuffle=False)
                if BUILTIN.getInfoBool('Playing','Player'): BUILTIN.executebuiltin('PlayerControl(Stop)')
                # BUILTIN.executewindow('ReplaceWindow(fullscreenvideo)',delay=OSD_TIMER,condition=BUILTIN.isPlaying)
                # BUILTIN.executebuiltin("Dialog.Close(all)")
                PLAYER().play(playlist,windowed=True)
            self._resolveURL(False, xbmcgui.ListItem())


    @threadit
    def playPaused(self, name: str, chid: str):
        self.log('[%s] playPaused'%(chid))
        with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
            listitems = self.getPausedItems(name, chid)
            if len(listitems) > 0: 
                playlist = self._cuePlaylist(chid, listitems,shuffle=False)
                if BUILTIN.getInfoBool('Playing','Player'): BUILTIN.executebuiltin('PlayerControl(Stop)')
                # BUILTIN.executewindow(OSD_TIMER,['ReplaceWindow(fullscreenvideo)',False,False,BUILTIN.isPlaying])
                # BUILTIN.executebuiltin("Dialog.Close(all)")
                PLAYER().play(playlist,windowed=True)
            self._resolveURL(False, xbmcgui.ListItem())


    def _resolveURL(self, found, listitem):
        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), *self.playCheck(found, listitem))
        
        
    def playCheck(self, found, listitem) -> bool and xbmcgui.ListItem:
        def _chkTime():
            if self.sysInfo['mode'] == 'live':
                if self.sysInfo['stop'] > 0 and self.sysInfo['now'] >= self.sysInfo['stop']:
                    self.log('[%s] playCheck _chkTime, failed! Current time (%s) is past the contents stop time (%s).'%(self.sysInfo.get('citem',{}).get('id'),self.sysInfo['now'],self.sysInfo['stop']))
                    DIALOG.notificationDialog("Current time (%s) is past the contents stop time (%s)."%(self.sysInfo['now'],self.sysInfo['stop']),show=SETTINGS.getSettingBool('Debug_Enable'))
                    return False
            return True
            
        def _chkFile():
            def __findMissing(file):
                fitem = self.sysInfo.get('fitem',{})
                if fitem.get('type') == 'episode':
                    episodes = self.jsonRPC.getEpisode(fitem.get('tvshowid'),fitem.get('season'),fitem.get('episode'))
                    for episode in episodes:
                        if episode == episode.get('episode',-1) and episode.get('file'):
                            self.log('[%s] playCheck, __findMissing episodedb found file = %s'%(self.sysInfo.get('citem',{}).get('id'),episode.get('file','')))
                            fitem = episode
                            break
                            
                elif fitem.get('type') == 'movie':
                    movies = self.jsonRPC.getMovie(fitem.get('uniqueid'),fitem.get('title'),fitem.get('year'))
                    for movie in movies:
                        if uniqueid.get('tmdb') == movie.get('uniqueid').get('tmdb') and movie.get('file'):
                            self.log('[%s] playCheck, __findMissing moviedb found file = %s'%(self.sysInfo.get('citem',{}).get('id'),movie.get('file','')))
                            fitem = movie
                            break
                            
                if not FileAccess.exists(fitem.get('file',file)):
                    oSeason, oEpisode = parseSE(file)
                    folder, filename = os.path.split(fitem.get('file',file))
                    items, limits, errors = self.jsonRPC.getDirectory({"directory":folder,"media": "video"})
                    for item in items:
                        if item.get('file','').endswith(tuple(VIDEO_EXTS)):
                            season, episode = parseSE(item.get('file',''))
                            if oSeason and oEpisode and (oSeason == season and oEpisode == episode):
                                self.log('[%s] playCheck, __findMissing search found episode file = %s'%(self.sysInfo.get('citem',{}).get('id'),item.get('file',file)))
                                fitem['file'] = item.get('file',file)
                                break
                            elif SequenceMatcher(None, filename, item.get('label','')).ratio() >= .70: #todo user sets ratio.
                                self.log('[%s] playCheck, __findMissing search found fuzzy file = %s'%(self.sysInfo.get('citem',{}).get('id'),item.get('file',file)))
                                fitem['file'] = item.get('file',file)
                                break
                self.sysInfo['fitem'] = fitem
                self.sysInfo['vid']   = fitem.get('file',file)
                return FileAccess.exists(self.sysInfo['vid'])
                
            file = (self.sysInfo.get('vid') or self.sysInfo.get('fitem',{}).get('file') or "")
            if   file.startswith(tuple(WEB_TYPES)): return True
            elif file.startswith(tuple(VFS_TYPES)): return SETTINGS.hasAddon(file)
            elif not FileAccess.exists(file):       return __findMissing(file)
            return FileAccess.exists(self.sysInfo.get('vid',file))
            
        oldInfo = FileAccess.loadJSON(Globals._decodeString(PROPERTIES.getEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID))))
        self.sysInfo['playcount'] = 1
        if self.sysInfo.get('chid') == oldInfo.get('chid',random.random()):
            if self.sysInfo.get('start') == oldInfo.get('start',random.random()):
                self.sysInfo['playcount'] = oldInfo.get('playcount',0) + 1 #carry over playcount
                self.sysInfo['runtime']   = oldInfo.get('runtime',0)       #carry over previous player runtime
        self.log('[%s] playCheck, playcount = %s'%(self.sysInfo.get('citem',{}).get('id'),self.sysInfo.get('playcount',1)))
        
        if found:
            if self.sysInfo.get('playcount',1) <= 3: 
                # found = (_chkFile() & _chkTime())
                found = True #todo fix
                if not found: return self.playError()
            listitem.setProperty("IsPlayable","true")
            listitem.setPath(self.sysInfo['vid'])
            listitem.setProperty('sysInfo',Globals._encodeString(FileAccess.dumpJSON(self.sysInfo)))
        PROPERTIES.setEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID),Globals._encodeString(FileAccess.dumpJSON(self.sysInfo)))
        return found, listitem
        
        
    def playError(self):
        self.log('[%s] playError, attempt = %s\n%s'%(self.sysInfo.get('chid','-1'),self.sysInfo.get('playcount',1),self.sysInfo))
        PROPERTIES.setEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID),Globals._encodeString(FileAccess.dumpJSON(self.sysInfo)))
        DIALOG.notificationWait(LANGUAGE(32167))
        if self.sysInfo.get('playcount',1) <= 1:
            DIALOG.notificationWait(LANGUAGE(32038)%(self.sysInfo.get('playcount',1)))
            BUILTIN.executebuiltin('PlayMedia(%s%s)'%(self.sysARG[0],self.sysARG[2])) #retry channel
        elif self.sysInfo.get('playcount',2) <= 2:
            DIALOG.notificationWait(LANGUAGE(32038)%(self.sysInfo.get('playcount',1)))
            BUILTIN.executebuiltin('AlarmClock(last,Number(0),.5,true,false)') #last channel
        elif self.sysInfo.get('playcount',3) <= 3:
            DIALOG.notificationDialog(LANGUAGE(32000))
            PROPERTIES.setPropTimer('chkPVRRefresh')
            timerit(DIALOG.okDialog)(0.1,[LANGUAGE(32134)%(ADDON_NAME)])
        else:
            DIALOG.notificationDialog(LANGUAGE(32000))
        return False, xbmcgui.ListItem()#release pending playback