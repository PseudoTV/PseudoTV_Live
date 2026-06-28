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
from variables  import DIALOG, PROPERTIES, SETTINGS, LISTITEMS, BUILTIN

class Player(xbmc.Player):
    """
    Player Event Trigger Execution Pipeline:
    1. onPlayBackStarted
    2. onAVChange (if codec shifts/resolves during playback initialization)
    3. onAVStarted
    4. onPlayBackSeek / onPlayBackStopped / onPlayBackEnded
    """
    def __init__(self, monitor, service):
        super(Player, self).__init__()
        self.pendingItem    = {}
        self.playingItem    = {}
        self.lastSubState   = False
        self.background     = None
        self.overlay        = None
        self.replay         = None
        self.runActions     = None
        self.playingThread  = None
        # self.playingStopped = Event()
        
        self.enableOverlay     = SETTINGS.getSettingBool('Overlay_Enable')
        self.infoOnChange      = SETTINGS.getSettingBool('Enable_OnInfo')
        self.disableTrakt      = SETTINGS.getSettingBool('Disable_Trakt')
        self.rollbackPlaycount = SETTINGS.getSettingBool('Rollback_Watched')
        self.saveDuration      = SETTINGS.getSettingBool('Store_Duration')
        self.minDuration       = SETTINGS.getSettingInt('Seek_Tolerance')
        self.maxProgress       = SETTINGS.getSettingInt('Seek_Threshold')
        self.sleepTime         = SETTINGS.getSettingInt('Idle_Timer')
        self.runWhilePlaying   = SETTINGS.getSettingBool('Run_While_Playing')
        self.replayPercentage  = SETTINGS.getSettingInt('Replay_Percentage')
        self.OnNextMode        = SETTINGS.getSettingInt('OnNext_Mode')
        self.onNextPosition    = SETTINGS.getSetting("OnNext_Position_XY")	
        self.playbackTimeout   = SETTINGS.getSettingInt('Playback_Timeout')
        
        self.monitor = monitor
        self.service = service
        self.pool    = service.pool
        self.jsonRPC = service.jsonRPC
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def onPlayBackStarted(self):
        self.pendingItem.update({'invoked': time.time(), 'pending': True, 'item': {}})
        self.log(f"onPlayBackStarted: pendingItem={self.pendingItem}")

    def onAVStarted(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'playing': True, 'item': self.getplayingItem()})
        self.log(f"onAVStarted: pendingItem={self.pendingItem}")
        # self._onPlay(self.pendingItem.get('item',{}))
        self.pool.executor(self._onPlay,None,self.pendingItem.get('item',{}))

    def onAVChange(self):
        self.log(f"onAVChange: playingItem={self.playingItem}")
        # self._onCheckpoint(self.playingItem)
        self.pool.executor(self._onCheckpoint,None,self.playingItem)
                    
    def onPlayBackSeek(self, seek_time=None, seek_offset=None):
        self.playingItem.setdefault('seek',{}).update({'seek':seek_time, 'offset': seek_offset})
        self.log(f"onPlayBackSeek: seek={seek_time}, offset={seek_offset}")
    
    def onPlayBackError(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'last': self.playingItem})
        self.log("onPlayBackError", xbmc.LOGERROR)
        # self._onError(self.playingItem)
        self.pool.executor(self._onError,None,self.playingItem)
        
    def onPlayBackEnded(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'item': {}, 'last': self.playingItem})
        self.log("onPlayBackEnded")
        # self._onChange(self.playingItem)
        self.pool.executor(self._onChange,None,self.playingItem)
        
    def onPlayBackStopped(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'playing': False, 'item': {}, 'last': {}})
        self.log("onPlayBackStopped")
        # self._onStop(self.playingItem)
        self.pool.executor(self._onStop,None,self.playingItem)

    def getplayingItem(self):
        try: 
            playingItem = FileAccess._decodeString(self.getPlayerItem().getProperty('sysInfo')) or {}
            if f"@{Globals._slugify(ADDON_NAME)}" in playingItem.get('chid', ''):
                fitem = combineDicts(playingItem.get('fitem', {}), Globals._decodePlot(BUILTIN.getInfoLabel('VideoPlayer.Plot')))
                nitem = combineDicts(playingItem.get('nitem', {}), Globals._decodePlot(BUILTIN.getInfoLabel('VideoPlayer.NextPlot')))
                citem = combineDicts(fitem.get('citem', {}), next((item for item in getattr(self.service, 'curchannels', []) if item.get('id', -1) == playingItem.get('chid', 0)), {}))
                
                fitem['runtime']  = self.getPlayerTime()
                fitem['isfiller'] = isFiller(fitem)
                nitem['isfiller'] = isFiller(nitem)
                
                playingItem['isPseudoTV'] = True
                playingItem['chfile']     = BUILTIN.getInfoLabel('Player.Filename')
                playingItem['chfolder']   = BUILTIN.getInfoLabel('Player.Folderpath')
                playingItem['chpath']     = BUILTIN.getInfoLabel('Player.Filenameandpath')
                playingItem['callback']   = self.jsonRPC.getCallback(playingItem)
                playingItem.update({'fitem': fitem, 'nitem': nitem, 'citem': citem})
                PROPERTIES.setProperty('lastPlayed.sysInfo', playingItem)
            return playingItem
        except Exception as e: 
            self.log(f"getplayingItem compilation failed: {str(e)}", xbmc.LOGERROR)
            return {}
            
    def getPlayerItem(self):
        try:
            if not self.isPlaying(): return xbmcgui.ListItem()
            return self.getPlayingItem()
        except Exception:
            self.monitor.waitForAbort(OSD_TIMER)
            return self.getPlayingItem() if self.isPlaying() else xbmcgui.ListItem()
        
    def getPlayerFile(self):
        return self.getPlayingFile() if self.isPlaying() else self.playingItem.get('fitem', {}).get('file')

    def getPlayerTime(self):
        return (self.getTimeLabel('Duration') or self.getTotalTime()) if self.isPlaying() else (self.playingItem.get('fitem', {}).get('runtime') or -1)
       
    def getPlayedTime(self):
        return (self.getTimeLabel('Time') or self.getTime()) if self.isPlaying() else -1
       
    def getRemainingTime(self):
        return (self.getPlayerTime() - self.getPlayedTime()) if self.isPlaying() else self.getTimeLabel('TimeRemaining')

    def getPlayerProgress(self):
        if self.isPlaying(): 
            try: return abs(int((self.getRemainingTime() / self.getPlayerTime()) * 100) - 100)
            except ZeroDivisionError: return 0
        return int(BUILTIN.getInfoLabel('Player.Progress') or '-1')

    def getTimeLabel(self, prop: str = 'TimeRemaining'):
        return timeString2Seconds(BUILTIN.getInfoLabel(f"Player.{prop}(hh:mm:ss)")) if self.isPlaying() else -1

    def isPlayingFiller(self):
        if self.isPlaying(): return isFiller({'genre': BUILTIN.getInfoLabel('VideoPlayer.Genre(slash)').split(' / ')})
        return isFiller(self.playingItem.get('fitem', {}))
        
    def isNextFiller(self):
        if self.isPlaying(): return isFiller({'genre': BUILTIN.getInfoLabel('VideoPlayer.NextGenre(slash)').split(' / ')})
        return isFiller(self.playingItem.get('nitem', {}))

    def isPlaylist(self):
        return bool(self.playingItem.get('isPlaylist', False))

    def isPseudoTV(self):
        return bool(self.playingItem.get('isPseudoTV', False))

    def isPlayingPseudoTV(self):
        return self.isPlaying() and self.isPseudoTV() and self.pendingItem.get('playing',False)

    def setSubtitles(self, state: bool = None):
        if not BUILTIN.hasSubtitle(): state = False
        elif state is None:           state = BUILTIN.isSubtitle()
        self.showSubtitles(state)
  
    # @debounceit(OSD_TIMER)
    def _onCheckpoint(self, playingItem=None):
        self.log(f"_onCheckpoint, playingItem")
        if playingItem is None: playingItem = {}
        if self.isPlayingPseudoTV() and not self.isPlayingFiller() and playingItem.get('isPlaylist', False):
            playingFile = self.getPlayerFile()
            if self.pendingItem.get('item', {}).get('file') == playingItem.get('item', {}).get('file') == playingFile:
                    resume = { "file"    : playingFile,
                               "position": ceil(self.getPlayedTime()),
                               "total"   : self.getPlayerTime(),
                               "updated" : {'instance': PROPERTIES.getFriendlyName(), 'time': getUTCstamp()} }
                    self.playingItem.setdefault('resume',{}).update(resume)
                    self.log(f"_onCheckpoint, {resume}")

    def _onPlaying(self):
        self.log(f"_onPlaying, started")
        # while not self.monitor.abortRequested() and not self.playingStopped.is_set():
            # if self.service._shutdown(0.5): break
            # elif not self.isPlayingPseudoTV(): break
            # else:
                # self.log(f"_onPlaying, running")
                # self.log(f"_onPlaying, isPlayingPseudoTV = {self.isPlayingPseudoTV()}")
                # _remaining = floor(self.getRemainingTime())
                # if _remaining <= (OSD_TIMER * 2): 
                    # self.toggleBackground(self.enableOverlay)
                    
                    # _played = ceil(self.getPlayedTime())
                    # if _played > self.minDuration: 
                        # self.toggleOverlay(self.enableOverlay)
                        
                    # if self.overlay is not None:
                        # total_time = int(self.getPlayerTime() * (self.maxProgress / 100))
                        # threshold  = abs((total_time - (total_time * 0.75)) - (ONNEXT_TIMER * 3))
                        # if _played > self.minDuration and (threshold >= _remaining >= roundupDIV(threshold, 3)):
                            # self.overlay.toggleOnNext(bool(self.OnNextMode))
            # self.log(f"_onPlaying, stopped")

    def _onPlay(self, playingItem=None):
        if playingItem is None: playingItem = {}
        self.log(f"_onPlay")
        self.toggleInfo(False)
        self.toggleOverlay(False)
        self.toggleBackground(False)
        self.lastSubState = BUILTIN.isSubtitle()
        
        if playingItem.get('isPseudoTV'):
            oldInfo = self.playingItem
            if self.jsonRPC:
                self.jsonRPC.quePlaycount(oldInfo.get('fitem', {}), self.rollbackPlaycount)
                self.jsonRPC._setRuntime(playingItem.get('fitem', {}), playingItem.get('fitem', {}).get('runtime'), self.saveDuration)

            newChan = oldInfo.get('chid', 'unknown') != playingItem.get('chid','unavailable')
            if newChan:
                self.runActions  = RulesList([playingItem.get('citem', {})]).runActions
                self.playingItem = self._runActions(RULES_ACTION_PLAYER_START, playingItem.get('citem', {}), playingItem, inherited=self)
                PROPERTIES.setTrakt(self.disableTrakt)
                self.setSubtitles(self.lastSubState)
                self.toggleReplay(bool(self.replayPercentage))
                
                # if self.playingThread is None or not self.playingThread.is_alive():
                    # self.playingStopped.clear()
                    # self.playingThread = Thread(target=self._onPlaying, daemon=True)
                    # self.playingThread.start()
            else:
                self.playingItem = playingItem
                if playingItem.get('radio', False): 
                    BUILTIN.executebuiltin('Action(back)')
                    BUILTIN.executewindow('ReplaceWindow(visualisation)')
                elif playingItem.get('isPlaylist', False): 
                    BUILTIN.executewindow('ReplaceWindow(fullscreenvideo)')
            self.toggleInfo(self.infoOnChange)   
            
            if not self.playingItem.get('callback') and self.jsonRPC:
                self.playingItem['callback'] = self.jsonRPC.getCallback(self.playingItem)
                PROPERTIES.setProperty('lastPlayed.sysInfo', self.playingItem)
                      
    def _onChange(self, playingItem=None):
        self.log(f"_onChange")
        if playingItem is None: playingItem = {}
        self.toggleOverlay(False)
        if playingItem:
            if not playingItem.get('isPlaylist', False):
                self.toggleBackground(self.enableOverlay)
                BUILTIN.executebuiltin(f"PlayMedia({playingItem.get('callback')})")
            self._runActions(RULES_ACTION_PLAYER_CHANGE, playingItem.get('citem', {}), playingItem, inherited=self)
        else:
            self.toggleBackground(False)
        
    def _onError(self, playingItem=None):
        self.log(f"_onError")
        if playingItem is None: playingItem = {}
        if self.isPseudoTV() and SETTINGS.getSettingBool('Debug_Enable'):
            DIALOG.notificationDialog(LANGUAGE(32000))
            self.onPlayBackStopped()
           
    def _onStop(self, playingItem=None):
        self.log(f"_onStop")
        if playingItem is None: playingItem = {}
        self.toggleInfo(False)
        self.toggleOverlay(False)
        self.toggleBackground(False)
        
        if playingItem:
            PROPERTIES.setTrakt(False)
            if playingItem.get('isPlaylist', False): xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
            if self.jsonRPC: self.jsonRPC.quePlaycount(playingItem.get('fitem', {}), self.rollbackPlaycount)
            self._runActions(RULES_ACTION_PLAYER_STOP, playingItem.get('citem', {}), playingItem, inherited=self)
            self.playingItem = {}
        # self.playingStopped.set()
            
    def _runActions(self, action, citem=None, parameter=None, inherited=None):
        if citem is None: citem = {}
        if self.runActions: return self.runActions(action, citem, parameter, inherited)
        return parameter

    def _onSleep(self):
        self.log('_onSleep')
        # xbmc.playSFX(NOTE_WAV)
        # dia = DIALOG.progressDialog(message=LANGUAGE(30078))
        # inc = int(100 / 15)
        # cnx = False
        
        # for sec in range(1, 16):
            # if self.monitor.abortRequested() or self.service._shutdown(1.0) or dia is None:
                # cnx = True
                # break
            # msg = f"{LANGUAGE(32039)}\n{LANGUAGE(32040) % (15 - sec)}"
            # dia = DIALOG.progressDialog((inc * sec), dia, msg)
        # if dia: DIALOG.progressDialog(100, dia)
        # return not cnx

    def toggleBackground(self, state: bool=False):
        self.log(f"toggleBackground, state = {state}")
        # if state and self.background is None:
            # if self.overlay: self.toggleOverlay(False)
            # # BUILTIN.executebuiltin("Dialog.Close(all)")
            # self.background = Background(BACKGROUND_XML, ADDON_PATH, "default", service=self.service)
            # self.background.show()
        # elif not state:
            # if hasattr(self.background, 'close'): self.background.close()
            # self.background = None

    def toggleOverlay(self, state: bool=False):
        self.log(f"toggleOverlay, state = {state}")
        # if state and self.overlay is None:
            # self.overlay = Overlay(service=self.service)
            # self.overlay.open()
        # elif not state:
            # if hasattr(self.overlay, 'close'): self.overlay.close()
            # self.overlay = None

    # @debounceit(OSD_TIMER)
    def toggleReplay(self, state: bool=False):
        self.log(f"toggleReplay, state = {state}")
        # if state and self.replay is None:
            # self.replay = Replay(REPLAY_XML, ADDON_PATH, "default", "1080i", service=self.service)
            # if   hasattr(self.replay, 'show_dialog'): self.replay.show_dialog()
            # elif hasattr(self.replay, 'doModal'):     self.replay.doModal()
        # elif not state:
            # if   hasattr(self.replay, 'onClose'): self.replay.onClose()
            # elif hasattr(self.replay, 'close'):   self.replay.close()
            # self.replay = None

    # @debounceit(OSD_TIMER)
    def toggleInfo(self, state: bool=False):
        self.log(f"toggleInfo, state = {state}")
        # if state and not BUILTIN.getInfoBool('Window.IsVisible(fullscreeninfo)'):
            # BUILTIN.executewindow('ActivateWindow(fullscreeninfo)')
            # timerit(self.toggleInfo)(float(OSD_TIMER), False)
        # elif not state:
            # if BUILTIN.getInfoBool('Window.IsVisible(fullscreeninfo)'):
                # BUILTIN.executebuiltin('Action(back)')
            # BUILTIN.executebuiltin('Dialog.Close(fullscreeninfo)')
           
class Monitor(xbmc.Monitor):
    def __init__(self, service):
        super(Monitor, self).__init__()
        self.idleTime   = 0
        self.isIdle     = False
        self.isPlaying  = False
        self.service    = service
        self.pool       = service.pool
        self.jsonRPC    = service.jsonRPC if service else None
        self.player     = Player(monitor=self, service=service)
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def _onIdle(self):
        #chkidle
        self.idleTime = BUILTIN.getIdle()
        self.isIdle   = self.idleTime > OSD_TIMER
        self.log(f"__onIdle, isIdle = {self.isIdle}")
        if self.player.isPlayingPseudoTV():
            #chkerror
            if self.player.pendingItem.get('invoked', -1) > 0 and not BUILTIN.isBusyDialog():
                if (time.time() - self.player.pendingItem.get('invoked', -1)) > self.player.playbackTimeout:
                    self.player.onPlayBackError()
            #chksleep
            if self.player.sleepTime > 0 and (self.idleTime > (self.player.sleepTime * 10800)):
                    if self.player._onSleep(): self.player.stop()
            #chkresume
            self.player.onAVChange()

    def onNotification(self, sender, method, data):
        self.log(f"onNotification received -> Sender: {sender} | Method: {method} | Data: {data}")

    # @debounceit(SERVICE_INTERVAL)
    def onSettingsChanged(self):
        self.log('onSettingsChanged; queuing settings synchronization...')
        self.service._que(self._updatePlayerSettings,1)
        self.service._que(self._updateServiceSettings,1)
            
    def _updateServiceSettings(self):
        self.log('_updateServiceSettings')
        if hasattr(self.service, 'tasks'):
            self.service.curchannels = self.service.tasks.getChannels()
            self.service.cursettings = self.service.tasks.chkSettingsChange(self.service.cursettings)
       
    def _updatePlayerSettings(self):
        self.log('_updatePlayerSettings')
        self.player.enableOverlay      = SETTINGS.getSettingBool('Overlay_Enable')
        self.player.infoOnChange       = SETTINGS.getSettingBool('Enable_OnInfo')
        self.player.disableTrakt       = SETTINGS.getSettingBool('Disable_Trakt')
        self.player.rollbackPlaycount  = SETTINGS.getSettingBool('Rollback_Watched')
        self.player.saveDuration       = SETTINGS.getSettingBool('Store_Duration')
        self.player.minDuration        = SETTINGS.getSettingInt('Seek_Tolerance')
        self.player.maxProgress        = SETTINGS.getSettingInt('Seek_Threshold')
        self.player.sleepTime          = SETTINGS.getSettingInt('Idle_Timer')
        self.player.runWhilePlaying    = SETTINGS.getSettingBool('Run_While_Playing')
        self.player.replayPercentage   = SETTINGS.getSettingInt('Replay_Percentage')
        self.player.OnNextMode         = SETTINGS.getSettingInt('OnNext_Mode')
        self.player.onNextPosition     = SETTINGS.getSetting("OnNext_Position_XY")
        
class Service(object):
    pendingShutdown  = False
    pendingRestart   = False
    pendingInterrupt = False
    pendingSuspend   = False
    
    def __init__(self):
        self.log("Initializing core system service layers...")
        self.isClient    = SETTINGS.getSettingBool('Enable_Client')
        self.jsonQue     = set(SETTINGS.getCacheSetting('jsonQue', default=[]))
        self.postQue     = set(SETTINGS.getCacheSetting('postQue', default=[]))
        self.logoQue     = set(SETTINGS.getCacheSetting('logoQue', default=[]))
        self.trailerQue  = set(SETTINGS.getCacheSetting('trailerQue', default=[]))
        self.imageCache  = OrderedDict(SETTINGS.getCacheSetting('imageCache', default={}))
        
        self.pool        = ExecutorPool()
        self.cache       = Cache(mem_cache=True)
        self.jsonRPC     = JSONRPC(service=self)
        self.monitor     = Monitor(service=self)
        self.player      = self.monitor.player
        self.tasks       = Tasks(service=self)
        self.queue       = CustomQueue(service=self)
        
        # self.curchannels = self.tasks.getChannels()
        # self.cursettings = SETTINGS.getCurrentSettings()

    def __del__(self):
        self._save()

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def _que(self, func, priority=3, delay=0, timer=0, *args, **kwargs):
        self.queue.push((func, args, kwargs), priority, delay, timer)

    def _isPlaying(self) -> bool: #assert isPseudoTV Playing/User allows background tasks while playing.
        if self.player.isPlaying() and not getattr(self.player, 'runWhilePlaying', False): return True
        return False     
        
    def _save(self):
        try:
            SETTINGS.setCacheSetting('jsonQue'   , list(self.jsonQue))
            SETTINGS.setCacheSetting('postQue'   , list(self.postQue))
            SETTINGS.setCacheSetting('logoQue'   , list(self.logoQue))
            SETTINGS.setCacheSetting('trailerQue', list(self.trailerQue))
            SETTINGS.setCacheSetting('imageCache', dict(self.imageCache))
        except Exception as e: self.log(f"_save, failed! {str(e)}", xbmc.LOGERROR)
        return True

    def _shutdown(self, wait=SERVICE_INTERVAL) -> bool:
        pending_state = any([PROPERTIES.isPendingShutdown(), self.monitor.waitForAbort(wait)])
        if self.pendingShutdown != pending_state:
            self.pendingShutdown = pending_state
            PROPERTIES.clrEXTProperty(f'{ADDON_ID}.SERVICE.pendingShutdown')
            self.log(f"_shutdown flag mutated: state={self.pendingShutdown}, lock_delay={wait}")
        return self.pendingShutdown
        
    def _restart(self) -> bool:
        pending_state = PROPERTIES.isPendingRestart()
        if self.pendingRestart != pending_state:
            self.pendingRestart = pending_state
            PROPERTIES.clrEXTProperty(f'{ADDON_ID}.SERVICE.pendingRestart')
            self.log(f"_restart flag mutated: state={self.pendingRestart}")
        return self.pendingRestart
         
    def _interrupt(self) -> bool:
        pending_state = any([PROPERTIES.isInterruptActivity(), self.pendingShutdown, self.pendingRestart, BUILTIN.isScanning(), self._isPlaying()])
        if pending_state != self.pendingInterrupt:
            self.pendingInterrupt = PROPERTIES.setPendingInterrupt(pending_state)
            self.log(f"_interrupt boundary changed: active={self.pendingInterrupt}")
        return self.pendingInterrupt

    def _suspend(self) -> bool:
        pending_state = any([PROPERTIES.isSuspendActivity(), BUILTIN.isSettingsOpened()])
        if pending_state != self.pendingSuspend:
            self.pendingSuspend = PROPERTIES.setPendingSuspend(pending_state)
            self.log(f"_suspend boundary changed: active={self.pendingSuspend}")
        return self.pendingSuspend
        
    def _sleep(self, wait=CPU_CYCLE) -> bool:
        """Throttles main daemon cycles to prevent high CPU utilization spikes."""
        while not self.monitor.abortRequested() and wait > 0:
            self.monitor.waitForAbort(wait)
            if self.pendingShutdown or self.pendingInterrupt: return True
            wait -= CPU_CYCLE
        return False
               
    def _initialize(self):
        PROPERTIES.setEXTProperty(f'{ADDON_ID}.Local_Host', self.jsonRPC.getLocalHost())
        self._que(self.tasks._client if self.isClient else self.tasks._host, 1)

    def _tasks(self):
        self._que(self.tasks.chkQueTimer, 1, 30.0)

    def _start(self):
        self.log("_start, service started")
        self._initialize()
        if DIALOG.notificationWait(f"{LANGUAGE(32054)}...", wait=15):
            if self.player.isPlayingPseudoTV(): 
                self.player.onAVStarted()
                
            while not self.monitor.abortRequested():
                if self._shutdown() or self._restart(): break
                else:
                    self._interrupt(), self._suspend()
                    if not self._isPlaying(): self._tasks()
            self.monitor.waitForAbort(SERVICE_INTERVAL)
            return self._stop(self.pendingRestart)

    def _stop(self, pendingRestart: bool = False) -> bool:
        if self.player.isPlayingPseudoTV(): self.player.onPlayBackStopped()
        with PROPERTIES.interruptActivity():
            for thread in threading.enumerate():
                if thread.name != "MainThread" and thread.is_alive():
                    if thread.name.startswith(f"{ADDON_ID}"):
                        self.log(f"_stop, Terminating Thread: {thread.name}")
                        if hasattr(thread, 'cancel'): thread.cancel()
                        try:  thread.join(timeout=0.5)
                        except Exception: pass
        if self._save(): 
            SETTINGS.cache.cache.shutdown()
            self.pool.shutdown()
        PROPERTIES._clrTrash(PROPERTIES.getProcessID())
        self.log(f"_stop, service shutdown sequence. Restart state: {pendingRestart}")
        return pendingRestart
        
        