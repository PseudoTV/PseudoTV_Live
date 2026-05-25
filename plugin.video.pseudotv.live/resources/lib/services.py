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
#
# -*- coding: utf-8 -*-
from globals    import *
from cqueue     import *
from overlay    import Background, Overlay, Replay
from rules      import RulesList
from tasks      import Tasks
from jsonrpc    import JSONRPC


class Player(xbmc.Player):
    pendingItem       = {}
    playingItem       = {}
    background        = None
    overlay           = None
    replay            = None
    runActions        = None
    lastSubState      = False
    
    #global rules
    enableOverlay     = SETTINGS.getSettingBool('Overlay_Enable')
    infoOnChange      = SETTINGS.getSettingBool('Enable_OnInfo')
    disableTrakt      = SETTINGS.getSettingBool('Disable_Trakt')
    rollbackPlaycount = SETTINGS.getSettingBool('Rollback_Watched')
    saveDuration      = SETTINGS.getSettingBool('Store_Duration')
    minDuration       = SETTINGS.getSettingInt('Seek_Tolerance')
    maxProgress       = SETTINGS.getSettingInt('Seek_Threshold')
    sleepTime         = SETTINGS.getSettingInt('Idle_Timer')
    runWhilePlaying   = SETTINGS.getSettingBool('Run_While_Playing')
    replayPercentage  = SETTINGS.getSettingInt('Replay_Percentage')
    OnNextMode        = SETTINGS.getSettingInt('OnNext_Mode')
    onNextPosition    = SETTINGS.getSetting("OnNext_Position_XY")	
    
    """ 
    Player() Trigger Order
    Player: onPlayBackStarted
    Player: onAVChange (if playing)
    Player: onPlayBackEnded (if playing)
    Player: onAVStarted
    Player: onPlayBackSeek (if seek)
    Player: onAVChange (if changed)
    Player: onPlayBackError
    Player: onPlayBackEnded
    Player: onPlayBackStopped
    """
    
    def __init__(self, monitor=None, service=None):
        xbmc.Player.__init__(self)
        self.monitor   = monitor
        self.service   = service
        self.jsonRPC   = service.jsonRPC
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onPlayBackStarted(self):
        self.pendingItem.update({'invoked':-1,'pending':False,'item':{},'last':self.pendingItem.get('item',{})})
        self.log('onPlayBackStarted, pendingItem = %s'%(self.pendingItem))
        

    def onAVChange(self):
        self.pendingItem.update({'resume':-1,'seek':-1,'item':{}})
        self.log('onAVChange, playingItem = %s'%(self.playingItem))

        
    def onAVStarted(self):
        self.pendingItem.update({'invoked':-1,'pending':False,'item':self.getplayingItem()})
        self.log('onAVStarted, pendingItem = %s'%(self.pendingItem))
        self._onPlay(self.pendingItem.get('item',{}))
        
                
    def onPlayBackSeek(self, seek_time=None, seek_offset=None): #Kodi bug? `OnPlayBackSeek` no longer called by player during seek, issue limited to pvr?
        self.pendingItem.update({'invoked':-1,'pending':False,'item':{}})
        self.log('onPlayBackSeek, seek_time = %s, seek_offset = %s, playingItem = %s'%(seek_time,seek_offset,self.playingItem))
    
    
    def onPlayBackError(self):
        self.pendingItem.update({'invoked':-1,'pending':False,'item':{}})
        self.log('onPlayBackError, pendingItem = %s'%(self.pendingItem))
        self._onError(self.playingItem)
        
        
    def onPlayBackEnded(self):
        self.pendingItem.update({'invoked':-1,'pending':False,'item':{}})
        self.log('onPlayBackEnded, pendingItem = %s'%(self.pendingItem))
        self._onChange(self.playingItem)
        
        
    def onPlayBackStopped(self):
        self.pendingItem.update({'invoked':-1,'pending':False,'item':{}})
        self.log('onPlayBackStopped, pendingItem = %s'%(self.pendingItem))
        self._onStop(self.playingItem)


    def getplayingItem(self):
        try: 
            playingItem = (FileAccess._decodeString(self.getPlayerItem().getProperty('sysInfo')) or {})
            if '@%s'%(Globals._slugify(ADDON_NAME)) in playingItem.get('chid',''):
                playingItem['isPseudoTV'] = True
                playingItem['chfile']   = BUILTIN.getInfoLabel('Player.Filename')
                playingItem['chfolder'] = BUILTIN.getInfoLabel('Player.Folderpath')
                playingItem['chpath']   = BUILTIN.getInfoLabel('Player.Filenameandpath')
                #playingItem from listitem maybe outdated, check with channels.json for fresh citem.
                playingItem.update({'fitem':combineDicts(playingItem.get('fitem',{}),Globals._decodePlot(BUILTIN.getInfoLabel('VideoPlayer.Plot')))})
                playingItem.update({'nitem':combineDicts(playingItem.get('nitem',{}),Globals._decodePlot(BUILTIN.getInfoLabel('VideoPlayer.NextPlot')))})
                playingItem.update({'citem':combineDicts(playingItem.get('fitem',{}).get('citem',{}),next((item for item in self.service.curchannels if item.get('id',-1) == playingItem.get('chid',0)),{}))})
                playingItem['fitem']['runtime']  = self.getPlayerTime()
                playingItem['fitem']['isfiller'] = isFiller(playingItem['fitem'])
                playingItem['nitem']['isfiller'] = isFiller(playingItem['nitem'])
                PROPERTIES.setProperty('lastPlayed.sysInfo',playingItem)
            return playingItem
        except Exception as e: 
            self.log('getplayingItem: failed! %s'%(e), xbmc.LOGERROR)
            
        
    def getPlayerItem(self):
        try:
            if not self.isPlaying(): 
                raise Exception('Not Playing')
            return self.getPlayingItem()
        except Exception:
            self.monitor.waitForAbort(OSD_TIMER) 
            if not self.isPlaying(): return xbmcgui.ListItem()
            return self.getPlayerItem()
        
        
    def getPlayerFile(self):
        if self.isPlaying(): return self.getPlayingFile()
        else:                return self.playingItem.get('fitem',{}).get('file')


    def getPlayerTime(self):
        if self.isPlaying(): return (self.getTimeLabel('Duration') or self.getTotalTime())
        else:                return (self.playingItem.get('fitem',{}).get('runtime') or -1)
            
       
    def getPlayedTime(self):
        if self.isPlaying(): return (self.getTimeLabel('Time') or self.getTime()) #getTime retrieves Guide times not actual media time.
        else:                return -1
       
            
    def getRemainingTime(self):
        if self.isPlaying(): return self.getPlayerTime() - self.getPlayedTime()
        else:                return self.getTimeLabel('TimeRemaining')


    def getPlayerProgress(self):
        if self.isPlaying(): return abs(int((self.getRemainingTime() / self.getPlayerTime()) * 100) - 100)
        else:                return int((BUILTIN.getInfoLabel('Player.Progress') or '-1'))


    def getTimeLabel(self, prop: str='TimeRemaining') -> int and float: #prop='EpgEventElapsedTime'
        if self.isPlaying(): return timeString2Seconds(BUILTIN.getInfoLabel('Player.%s(hh:mm:ss)'%(prop)))
        else:                return -1


    def isPlayingFiller(self):
        if self.isPlaying(): return isFiller({'genre':BUILTIN.getInfoLabel('VideoPlayer.Genre(slash)').split(' / ')})
        else:                return isFiller(self.playingItem.get('fitem',{}))
        
        
    def isNextFiller(self):
        if self.isPlaying(): return isFiller({'genre':BUILTIN.getInfoLabel('VideoPlayer.NextGenre(slash)').split(' / ')})
        else:                return isFiller(self.playingItem.get('nitem',{}))


    def isPlaylist(self):
        return (self.playingItem.get('isPlaylist') or False)


    def isPseudoTV(self):
        return (self.playingItem.get('isPseudoTV') or False)


    def isPlayingPseudoTV(self):
        return (self.isPlaying() & self.isPseudoTV())


    def setSubtitles(self, state: bool=True):
        hasSubtitle = BUILTIN.hasSubtitle()
        self.log('setSubtitles, show subtitles = %s, hasSubtitle = %s'%(state,hasSubtitle))
        if not hasSubtitle: state = False
        self.showSubtitles(state)


    @threadit
    def _onPlay(self, playingItem={}):
        self.log('_onPlay, playingItem = %s'%(playingItem))
        self.toggleInfo(False)
        self.toggleOverlay(False)
        self.toggleBackground(False)
        self.lastSubState = BUILTIN.isSubtitle()
        if playingItem.get('isPseudoTV'):
            oldInfo = self.playingItem
            newChan = oldInfo.get('chid',random.random()) != playingItem.get('chid')
            self.log('_onPlay, [%s], mode = %s, isPlaylist = %s, new channel = %s'%(playingItem.get('citem',{}).get('id'), playingItem.get('mode'), playingItem.get('isPlaylist',False), newChan))
            if newChan: #New channel
                self.runActions  = RulesList([playingItem.get('citem',{})]).runActions
                self.playingItem = self._runActions(RULES_ACTION_PLAYER_START, playingItem.get('citem',{}), playingItem, inherited=self)
                PROPERTIES.setTrakt(self.disableTrakt)
                self.setSubtitles(self.lastSubState) #todo allow rules to set sub preference per channel.
                self.toggleReplay(bool(self.replayPercentage))
            else: #New Program/Same Channel
                self.playingItem = playingItem
                if playingItem.get('radio',False): 
                    BUILTIN.executebuiltin('Action(back)')
                    BUILTIN.executewindow('ReplaceWindow(visualisation)')
                elif playingItem.get('isPlaylist',False): 
                    BUILTIN.executewindow('ReplaceWindow(fullscreenvideo)')
                self.toggleInfo(self.infoOnChange)
            self.jsonRPC.quePlaycount(oldInfo.get('fitem',{}),self.rollbackPlaycount)
            self.jsonRPC._setRuntime(playingItem.get('fitem',{}),playingItem.get('fitem',{}).get('runtime'),self.saveDuration)

            
    @threadit
    def _onChange(self, playingItem={}):
        self.log('_onChange, playingItem = %s'%(playingItem))
        self.toggleOverlay(False)
        if playingItem:
            if not playingItem.get('isPlaylist',False):
                self.toggleBackground(self.enableOverlay)
                BUILTIN.executebuiltin('PlayMedia(%s)'%(playingItem.get('callback')))
                self.log('_onChange, [%s], isPlaylist = %s, callback = %s'%(playingItem.get('citem',{}).get('id'),playingItem.get('isPlaylist',False),playingItem.get('callback')))
            self._runActions(RULES_ACTION_PLAYER_CHANGE, playingItem.get('citem',{}), playingItem, inherited=self)
        else:
            self.toggleBackground(False)
        
        
    @threadit
    def _onError(self, playingItem={}): #todo evaluate potential for error handling.
        self.log('_onError, playingItem = %s'%(playingItem))
        if self.isPseudoTV() and SETTINGS.getSettingBool('Debug_Enable'):
            DIALOG.notificationDialog(LANGUAGE(32000))
            self._onStop(playingItem)
            
           
    @threadit 
    def _onStop(self, playingItem={}):
        self.log('_onStop, playingItem = %s'%(playingItem))
        self.toggleInfo(False)
        self.toggleOverlay(False)
        self.toggleBackground(False)
        if playingItem:
            PROPERTIES.setTrakt(False)
            if playingItem.get('isPlaylist',False): xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
            self.jsonRPC.quePlaycount(playingItem.get('fitem',{}),self.rollbackPlaycount)
            self._runActions(RULES_ACTION_PLAYER_STOP, playingItem.get('citem',{}), playingItem, inherited=self)
            self.playingItem = {}
            
            
    def _runActions(self, action, citem={}, parameter=None, inherited=None):
        if self.runActions: return self.runActions(action, citem, parameter, inherited)
        else:               return parameter


    def _onSleep(self):
        self.log('_onSleep')
        sec = 0
        cnx = False
        inc = int(100/15)
        xbmc.playSFX(NOTE_WAV)
        dia = DIALOG.progressDialog(message=LANGUAGE(30078))
        while not self.monitor.abortRequested() and (sec < 15):
            sec += 1
            msg = '%s\n%s'%(LANGUAGE(32039),LANGUAGE(32040)%(15-sec))
            dia = DIALOG.progressDialog((inc*sec),dia, msg)
            if self.service._shutdown(1.0) or dia is None:
                cnx = True
                break
        DIALOG.progressDialog(100,dia)
        return not bool(cnx)


    def _onIdle(self):
        def __chkPlayback():
            if self.pendingItem.get('invoked',-1) > 0 and not BUILTIN.isBusyDialog() and (time.time() - self.pendingItem.get('invoked',-1)) > SETTINGS.getSettingInt('Playback_Timeout'):
                self.onPlayBackError()

        def __chkCallback():
            if not self.playingItem.get('callback'):
                self.playingItem['callback'] = self.jsonRPC.getCallback(self.playingItem)
                self.log('__chkCallback, callback = %s'%(self.playingItem['callback']))
                PROPERTIES.setProperty('lastPlayed.sysInfo',self.playingItem)

        def __chkBackground():
            remaining = floor(self.getRemainingTime())
            if remaining <= (OSD_TIMER*2):
                self.log('__chkBackground, remaining = %s'%(remaining))
                self.toggleBackground(self.enableOverlay)

        def __chkResumeTime():
            if not self.isPlayingFiller() and self.isPlayingPlaylist():
                if self.playingItem.get('fitem',{}).get('file') == self.getPlayingFile():
                    resume = {"position":self.getPlayedTime(),
                              "total":   self.getPlayerTime(),
                              "file" :   self.getPlayerFile(),
                              "updated":{'instance':PROPERTIES.getFriendlyName(),'time':getUTCstamp()}}
                    self.playingItem.setdefault('resume',{}).update(resume)
                    self.log('__chkResumeTime, resume = %s'%(self.playingItem.get('resume')))

        def __chkOverlay():
            if not self.isPlayingFiller() and ceil(self.getPlayedTime()) > self.minDuration: 
                self.toggleOverlay(self.enableOverlay)

        def __chkOnNext():
            played    = ceil(self.getPlayedTime())
            remaining = floor(self.getRemainingTime())
            totalTime = int(self.getPlayerTime() * (self.maxProgress / 100))
            threshold = abs((totalTime - (totalTime * .75)) - (ONNEXT_TIMER*3))
            intTime   = roundupDIV(threshold,3)
            if self.isPlayingPseudoTV() and not self.isPlayingFiller() and not self.overlay is None:
                if played > self.minDuration and (remaining <= threshold and remaining >= intTime): 
                    self.log('__chkOnNext, played = %s, remaining = %s'%(played,remaining))
                    self.overlay.toggleOnNext(bool(self.OnNextMode))
                
        def __chkSleep():
            if self.sleepTime > 0 and (self.monitor.idleTime > (self.sleepTime * 10800)):
                if not PROPERTIES.isRunning('Player.__chkSleep'):
                    with PROPERTIES.chkRunning('Player.__chkSleep'):
                        if self._onSleep(): self.stop()
        
        __chkPlayback()
        __chkBackground()
        __chkResumeTime()
        __chkCallback()
        __chkOverlay()
        __chkOnNext()	
        __chkSleep()
            
                
    def toggleBackground(self, state: bool=SETTINGS.getSettingBool('Overlay_Enable')):
        if state and self.monitor.isIdle and self.background is None:
            if not self.overlay is None: self.toggleOverlay(False)
            BUILTIN.executebuiltin("Dialog.Close(all)")
            self.background = Background(BACKGROUND_XML, ADDON_PATH, "default", service=self.service)
            self.background.show()
        elif not state and hasattr(self.background,'close'):
            self.background = self.background.close()
        else: return
        self.log("toggleBackground, state = %s, background = %s"%(state,self.background))


    def toggleOverlay(self, state: bool=SETTINGS.getSettingBool('Overlay_Enable')):
        if state and self.isPlayingPseudoTV() and self.overlay is None:
            self.overlay = Overlay(service=self.service)
            self.overlay.open()
        elif not state and hasattr(self.overlay,'close'):
            self.overlay = self.overlay.close()
        else: return
        self.log("toggleOverlay, state = %s, overlay = %s"%(state, self.overlay))


    @debounceit(OSD_TIMER)
    def toggleReplay(self, state: bool=bool(SETTINGS.getSettingInt('Replay_Percentage'))):
        if state and self.isPlayingPseudoTV() and not self.isPlayingFiller() and self.replay is None:
            self.replay = Replay(REPLAY_XML, ADDON_PATH, "default", "1080i", service=self.service)
        elif not state and hasattr(self.replay,'onClose'):
            self.replay = self.replay.onClose()
        else: return
        self.log("toggleReplay, state = %s, replay = %s"%(state,self.replay))
        
        
    @debounceit(OSD_TIMER)
    def toggleInfo(self, state: bool=SETTINGS.getSettingBool('Enable_OnInfo')):
        if state and self.isPlayingPseudoTV() and not self.isPlayingFiller() and not BUILTIN.getInfoBool('Window.IsVisible(fullscreeninfo)'):
            BUILTIN.executewindow('ActivateWindow(fullscreeninfo)')
            timerit(self.toggleInfo)(float(OSD_TIMER),False)
        elif not state and BUILTIN.getInfoBool('Window.IsVisible(fullscreeninfo)'):
            BUILTIN.executebuiltin('Action(back)')
            BUILTIN.executebuiltin('Dialog.Close(fullscreeninfo)')
        else: return
        self.log('toggleInfo, state = %s'%(state))


class Monitor(xbmc.Monitor):
    idleTime  = 0
    isIdle    = False
    isRunning = False
    
    def __init__(self, service=None):
        xbmc.Monitor.__init__(self)
        self.service = service
        self.jsonRPC = service.jsonRPC
        self.player  = Player(self,service)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def chkIdle(self):
        self.idleThread = Thread(target=self._chkIdle)
        if self.idleThread.is_alive():
            if hasattr(self.idleThread, 'cancel'): self.idleThread.cancel()
            try: self.idleThread.join(1.0)
            except Exception: pass
        self.idleThread.daemon = True
        self.idleThread.start()
            
        
    def _chkIdle(self):
        if not self.isRunning:
            self.isRunning = True
            while not self.abortRequested():
                if   self.service._shutdown(0.5): break
                elif self.player.isPlayingPseudoTV(): 
                    self.idleTime = BUILTIN.getIdle()
                    self.isIdle   = bool(self.idleTime) | self.idleTime > OSD_TIMER
                    self.log('_chkIdle, isIdle = %s, idleTime = %s'%(self.isIdle, self.idleTime))
                    if self.isIdle: self.player._onIdle()
                elif self.service._shutdown(0.5):
                    self.log("_chkIdle, not playing!")
                    break # not playing loosen timing
            self.isRunning = False
            self.log("_chkIdle, shutdown!")


    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            

    @debounceit(SERVICE_INTERVAL)
    def onSettingsChanged(self):
        self.log('onSettingsChanged') 
        self.service._que(self._updatePlayerSettings)
        self.service._que(self._updateServiceSettings)
            
            
    def _updateServiceSettings(self):
        self.log('_updateServiceSettings')
        self.service.curchannels = self.service.tasks.getChannels()
        self.service.cursettings = self.service.tasks.chkSettingsChange(self.service.cursettings) #check for settings change, take action if needed
        
        
    def _updatePlayerSettings(self):
        self.log('_updatePlayerSettings')
        self.player.enableOverlay     = SETTINGS.getSettingBool('Overlay_Enable')
        self.player.infoOnChange      = SETTINGS.getSettingBool('Enable_OnInfo')
        self.player.disableTrakt      = SETTINGS.getSettingBool('Disable_Trakt')
        self.player.rollbackPlaycount = SETTINGS.getSettingBool('Rollback_Watched')
        self.player.saveDuration      = SETTINGS.getSettingBool('Store_Duration')
        self.player.minDuration       = SETTINGS.getSettingInt('Seek_Tolerance')
        self.player.maxProgress       = SETTINGS.getSettingInt('Seek_Threshold')
        self.player.sleepTime         = SETTINGS.getSettingInt('Idle_Timer')
        self.player.runWhilePlaying   = SETTINGS.getSettingBool('Run_While_Playing')
        self.player.replayPercentage  = SETTINGS.getSettingInt('Replay_Percentage')
        self.player.OnNextMode        = SETTINGS.getSettingInt('OnNext_Mode')
        self.player.onNextPosition    = SETTINGS.getSetting("OnNext_Position_XY")
        
        
class Service(object):
    channels         = []
    isScanning       = BUILTIN.isScanning()
    isPaused         = BUILTIN.isPaused()
    isPlaying        = BUILTIN.isPlaying()
    isClient         = SETTINGS.getSettingBool('Enable_Client')
    pendingSuspend   = PROPERTIES.setPendingSuspend(False)
    pendingInterrupt = PROPERTIES.setPendingInterrupt(False)
    pendingShutdown  = PROPERTIES.setPendingShutdown(False)
    pendingRestart   = PROPERTIES.setPendingRestart(False)
    jsonQue          = set(SETTINGS.getCacheSetting('jsonQue', default=[]))
    postQue          = set(SETTINGS.getCacheSetting('postQue', default=[]))
    logoQue          = set(SETTINGS.getCacheSetting('logoQue', default=[]))
    trailerQue       = set(SETTINGS.getCacheSetting('trailerQue', default=[]))
    imageCache       = OrderedDict(SETTINGS.getCacheSetting('imageCache', default={}))


    def __init__(self):
        self.jsonRPC       = JSONRPC(service=self)
        self.monitor       = Monitor(service=self)
        self.player        = self.monitor.player
        self.tasks         = Tasks(service=self)
        self.curchannels   = self.tasks.getChannels()
        self.cursettings   = SETTINGS.getCurrentSettings()
        self.isClient      = SETTINGS.getSettingBool('Enable_Client')
        self.priorityQUE   = CustomQueue(priority=True, service=self)
    

    def __del__(self):
        try:
            SETTINGS.setCacheSetting('jsonQue'   , self.jsonQue)
            SETTINGS.setCacheSetting('postQue'   , self.postQue)
            SETTINGS.setCacheSetting('logoQue'   , self.logoQue)
            SETTINGS.setCacheSetting('trailerQue', self.trailerQue)
            SETTINGS.setCacheSetting('imageCache', self.imageCache)
        except Exception: pass


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _que(self, func, priority=-1, *args, **kwargs):# priority -1 autostack (FIFO), 1 Highest, 5 Lowest
        self.priorityQUE._push((func, args, kwargs), priority)


    def _isPlaying(self) -> bool: #assert playback for background service throttling.
        if (self.isPlaying or self.isPaused) and not self.player.runWhilePlaying: return True
        return False
    
        
    def _tasks(self):
        self._que(self.tasks._chkEpochTimer,-1,*('chkQueTimer', self.tasks.chkQueTimer, 15)) #keep CustomQueue alive after interrupt.
    
    
    def _shutdown(self, wait=SERVICE_INTERVAL) -> bool: #service break
        pendingShutdown = any([PROPERTIES.isPendingShutdown(),self.monitor.waitForAbort(wait)])
        if self.pendingShutdown != pendingShutdown:
            self.pendingShutdown = pendingShutdown
            self.log('_shutdown, pendingShutdown = %s, wait = %s'%(self.pendingShutdown,wait))
        return self.pendingShutdown
    
    
    def _restart(self) -> bool: #service restart
        pendingRestart = PROPERTIES.isPendingRestart()
        if self.pendingRestart != pendingRestart:
            self.pendingRestart = pendingRestart
            self.log('_restart, pendingRestart = %s'%(self.pendingRestart))
        return self.pendingRestart
         
        
    def _interrupt(self) -> bool: #tasks break
        pendingInterrupt = any([PROPERTIES.isInterruptActivity(), self.pendingShutdown, self.pendingRestart, self.isScanning, self._isPlaying()])
        if pendingInterrupt != self.pendingInterrupt:
            self.pendingInterrupt = PROPERTIES.setPendingInterrupt(pendingInterrupt)
            self.log('_interrupt, pendingInterrupt = %s'%(self.pendingInterrupt))
        return self.pendingInterrupt
    

    def _suspend(self) -> bool: #tasks continue
        pendingSuspend = any([PROPERTIES.isSuspendActivity(),BUILTIN.isSettingsOpened()])
        if pendingSuspend != self.pendingSuspend:
            self.pendingSuspend = PROPERTIES.setPendingSuspend(pendingSuspend)
            self.log('_suspend, pendingSuspend = %s'%(self.pendingSuspend))
        return self.pendingSuspend
        

    def _sleep(self, wait=CPU_CYCLE): #waitForAbort replacement for tasks
        while not self.monitor.abortRequested() and wait > 0:
            if any([self.monitor.waitForAbort(CPU_CYCLE),self._interrupt()]): return True
            else: wait -= CPU_CYCLE
        if wait > 0: self.log('_sleep, remaining = %s'%(wait))
        return False
                
                
    def _initialize(self):
        PROPERTIES.setEXTProperty('%s.Local_Host'%(ADDON_ID),self.jsonRPC.getLocalHost())
        if self.isClient: self._que(self.tasks._client,1)
        else:             self._que(self.tasks._host,1)


    def _start(self):
        self.log('_start')
        self._initialize()
        if DIALOG.notificationWait('%s...'%(LANGUAGE(32054)),wait=15):
            if self.player.isPlayingPseudoTV(): self.player.onAVStarted()
            while not self.monitor.abortRequested():
                self.isScanning = BUILTIN.isScanning()
                self.isPaused   = BUILTIN.isPaused()
                self.isPlaying  = self.player.isPlaying()
                if       self._shutdown() and self._interrupt() and self._sleep(): break
                elif     self._restart()  and self._interrupt() and self._sleep(): break
                elif not self._isPlaying(): self._tasks()
            return self._stop(self.pendingRestart)


    def _stop(self, pendingRestart: bool=False):
        if self.player.isPlayingPseudoTV(): self.player.onPlayBackStopped()
        SETTINGS.cache.cache.shutdown()
        with PROPERTIES.interruptActivity():
            for thread in thread_enumerate():
                if thread.name != "MainThread" and thread.is_alive():
                    if hasattr(thread, 'cancel'): thread.cancel()
                    try: thread.join(1.0)
                    except Exception: pass
                    self.log('_stop, closing %s...'%(thread.name))
        if pendingRestart: return True
        PROPERTIES._clrTrash(PROPERTIES.getProcessID()) #clrTrash
        