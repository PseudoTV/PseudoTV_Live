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
from typing     import Any, Optional, Callable
from variables  import *
from cqueue     import *
from cache      import Cache
from _services  import _Service
from overlay    import Background, Overlay, Replay
from rules      import RulesList
from tasks      import Tasks
from jsonrpc    import JSONRPC

class Player(xbmc.Player):
    """
    Player Event Trigger Execution Pipeline:
    1. onPlayBackStarted
    2. onAVChange (if codec shifts/resolves during playback initialization)
    3. onAVStarted
    4. onPlayBackSeek / onPlayBackStopped / onPlayBackEnded
    """
    def __init__(self, monitor: 'Monitor', service: 'Service'):
        super(Player, self).__init__()
        self.pendingItem    = {}
        self.playingItem    = {}
        self.lastSubState   = False
        self.background     = None
        self.overlay        = None
        self.replay         = None
        self.runActions     = None
        self.playingThread  = None
        self.playingStopped = Event()
        
        self.enableOverlay     = Globals.settings.getSettingBool('Overlay_Enable')
        self.infoOnChange      = Globals.settings.getSettingBool('Enable_OnInfo')
        self.disableTrakt      = Globals.settings.getSettingBool('Disable_Trakt')
        self.rollbackPlaycount = Globals.settings.getSettingBool('Rollback_Watched')
        self.saveDuration      = Globals.settings.getSettingBool('Store_Duration')
        self.minDuration       = Globals.settings.getSettingInt('Seek_Tolerance')
        self.maxProgress       = Globals.settings.getSettingInt('Seek_Threshold')
        self.sleepTime         = Globals.settings.getSettingInt('Idle_Timer')
        self.runWhilePlaying   = Globals.settings.getSettingBool('Run_While_Playing')
        self.replayPercentage  = Globals.settings.getSettingInt('Replay_Percentage')
        self.OnNextMode        = Globals.settings.getSettingInt('OnNext_Mode')
        self.onNextPosition    = Globals.settings.getSetting("OnNext_Position_XY")	
        self.playbackTimeout   = Globals.settings.getSettingInt('Playback_Timeout')
        
        self.monitor = monitor
        self.service = service
        self.pool    = service.pool
        self.jsonRPC = service.jsonRPC
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)

    def onPlayBackStarted(self):
        self.pendingItem.update({'invoked': time.time(), 'pending': True, 'item': {}})
        self.log(f"onPlayBackStarted: pendingItem={self.pendingItem}")

    def onAVStarted(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'playing': True, 'item': {}})
        self.log(f"onAVStarted: pendingItem={self.pendingItem}")
        self.pool.submit(self._onPlay,{})

    def onAVChange(self):
        self.log(f"onAVChange: playingItem={self.playingItem}")
        # self._onCheckpoint(self.playingItem)
        self.pool.submit(self._onCheckpoint,self.playingItem)
                    
    def onPlayBackSeek(self, seek_time: Optional[float] = None, seek_offset: Optional[float] = None):
        self.playingItem.setdefault('seek',{}).update({'seek':seek_time, 'offset': seek_offset})
        self.log(f"onPlayBackSeek: seek={seek_time}, offset={seek_offset}")
    
    def onPlayBackError(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'last': self.playingItem})
        self.log("onPlayBackError", xbmc.LOGERROR)
        # self._onError(self.playingItem)
        self.pool.submit(self._onError,self.playingItem)
        
    def onPlayBackEnded(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'item': {}, 'last': self.playingItem})
        self.log("onPlayBackEnded")
        # self._onChange(self.playingItem)
        self.pool.submit(self._onChange,self.playingItem)
        
    def onPlayBackStopped(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'playing': False, 'item': {}, 'last': {}})
        self.log("onPlayBackStopped")
        # self._onStop(self.playingItem)
        self.pool.submit(self._onStop,self.playingItem)

    def getplayingItem(self) -> dict:
        try: 
            playingItem = FileAccess._decodeString(self.getPlayerItem().getProperty('sysInfo')) or {}
            if f"@{Globals._slugify(ADDON_NAME)}" in playingItem.get('chid', ''):
                fitem = Globals._combineDicts(playingItem.get('fitem', {}), Globals._decodePlot(Globals.builtin.getInfoLabel('VideoPlayer.Plot')))
                nitem = Globals._combineDicts(playingItem.get('nitem', {}), Globals._decodePlot(Globals.builtin.getInfoLabel('VideoPlayer.NextPlot')))
                citem = Globals._combineDicts(fitem.get('citem', {}), next((item for item in getattr(self.service, 'curchannels', []) if item.get('id', -1) == playingItem.get('chid', 0)), {}))
                
                fitem['runtime']  = self.getPlayerTime()
                fitem['isfiller'] = Globals._isFiller(fitem)
                nitem['isfiller'] = Globals._isFiller(nitem)
                
                playingItem['isPseudoTV'] = True
                playingItem['chfile']     = Globals.builtin.getInfoLabel('Player.Filename')
                playingItem['chfolder']   = Globals.builtin.getInfoLabel('Player.Folderpath')
                playingItem['chpath']     = Globals.builtin.getInfoLabel('Player.Filenameandpath')
                playingItem['callback']   = self.jsonRPC.getCallback(playingItem)
                playingItem.update({'fitem': fitem, 'nitem': nitem, 'citem': citem})
                Globals.properties.setProperty('lastPlayed.sysInfo', playingItem)
            return playingItem
        except Exception as e: 
            self.log(f"getplayingItem compilation failed: {str(e)}", xbmc.LOGERROR)
            return {}
            
    def getPlayerItem(self) -> xbmcgui.ListItem:
        try:
            if not self.isPlaying(): return xbmcgui.ListItem()
            return self.getPlayingItem()
        except Exception as e:
            self.log(f'getPlayerItem, failed: {e}', xbmc.LOGWARNING)
            self.monitor.waitForAbort(OSD_TIMER)
            return self.getPlayingItem() if self.isPlaying() else xbmcgui.ListItem()
        
    def getPlayerFile(self) -> str:
        return self.getPlayingFile() if self.isPlaying() else self.playingItem.get('fitem', {}).get('file')

    def getPlayerTime(self) -> int:
        return (self.getTimeLabel('Duration') or self.getTotalTime()) if self.isPlaying() else (self.playingItem.get('fitem', {}).get('runtime') or -1)
       
    def getPlayedTime(self) -> int:
        return (self.getTimeLabel('Time') or self.getTime()) if self.isPlaying() else -1
       
    def getRemainingTime(self) -> int:
        return (self.getPlayerTime() - self.getPlayedTime()) if self.isPlaying() else self.getTimeLabel('TimeRemaining')

    def getPlayerProgress(self) -> int:
        if self.isPlaying(): 
            try: return abs(int((self.getRemainingTime() / self.getPlayerTime()) * 100) - 100)
            except ZeroDivisionError: return 0
        return int(Globals.builtin.getInfoLabel('Player.Progress') or '-1')

    def getTimeLabel(self, prop: str = 'TimeRemaining') -> int:
        return Globals._timeString2Seconds(Globals.builtin.getInfoLabel(f"Player.{prop}(hh:mm:ss)")) if self.isPlaying() else -1

    def isPlayingFiller(self) -> bool:
        if self.isPlaying(): return Globals._isFiller({'genre': Globals.builtin.getInfoLabel('VideoPlayer.Genre(slash)').split(' / ')})
        return Globals._isFiller(self.playingItem.get('fitem', {}))
        
    def isNextFiller(self) -> bool:
        if self.isPlaying(): return Globals._isFiller({'genre': Globals.builtin.getInfoLabel('VideoPlayer.NextGenre(slash)').split(' / ')})
        return Globals._isFiller(self.playingItem.get('nitem', {}))

    def isPlaylist(self) -> bool:
        return bool(self.playingItem.get('isPlaylist', False))

    def isPseudoTV(self) -> bool:
        return bool(self.playingItem.get('isPseudoTV', False))

    def isPlayingPseudoTV(self) -> bool:
        return self.isPlaying() and self.isPseudoTV() and self.pendingItem.get('playing',False)

    def setSubtitles(self, state: Optional[bool] = None):
        if not Globals.builtin.hasSubtitle(): state = False
        elif state is None:           state = Globals.builtin.isSubtitle()
        self.showSubtitles(state)
  
    # @debounceit(OSD_TIMER)
    def _onCheckpoint(self, playingItem: Optional[dict] = None):
        self.log(f"_onCheckpoint, playingItem")
        if playingItem is None: playingItem = {}
        if self.isPlayingPseudoTV() and not self.isPlayingFiller() and playingItem.get('isPlaylist', False):
            playingFile = self.getPlayerFile()
            if self.pendingItem.get('item', {}).get('file') == playingItem.get('item', {}).get('file') == playingFile:
                    resume = { "file"    : playingFile,
                               "position": ceil(self.getPlayedTime()),
                               "total"   : self.getPlayerTime(),
                               "updated" : {'instance': Globals.properties.getFriendlyName(), 'time': Globals._getUTCstamp()} }
                    self.playingItem.setdefault('resume',{}).update(resume)
                    self.log(f"_onCheckpoint, {resume}")

    def _onPlaying(self):
        self.log(f"_onPlaying, started")
        while not self.monitor.abortRequested() and not self.playingStopped.is_set():
            if self.service._shutdown(0.5): break
            elif not self.isPlayingPseudoTV(): break
            else:
                _remaining = floor(self.getRemainingTime())
                if _remaining <= (OSD_TIMER * 2): 
                    self.toggleBackground(self.enableOverlay)
                    
                    _played = ceil(self.getPlayedTime())
                    if _played > self.minDuration: 
                        self.toggleOverlay(self.enableOverlay)
                        
                    if self.overlay is not None:
                        total_time = int(self.getPlayerTime() * (self.maxProgress / 100))
                        threshold  = abs((total_time - (total_time * 0.75)) - (ONNEXT_TIMER * 3))
                        if _played > self.minDuration and (threshold >= _remaining >= Globals._roundupDIV(threshold, 3)):
                            self.overlay.toggleOnNext(bool(self.OnNextMode))
        self.log(f"_onPlaying, stopped")

    def _onPlay(self, playingItem: Optional[dict] = None):
        if playingItem is None: playingItem = {}
        self.log(f"_onPlay")
        if not playingItem:
            playingItem = self.getplayingItem()
        self.toggleInfo(False)
        self.toggleOverlay(False)
        self.toggleBackground(False)
        self.lastSubState = Globals.builtin.isSubtitle()
        
        if playingItem.get('isPseudoTV'):
            oldInfo = self.playingItem
            if self.jsonRPC:
                self.jsonRPC.quePlaycount(oldInfo.get('fitem', {}), self.rollbackPlaycount)
                self.jsonRPC._setRuntime(playingItem.get('fitem', {}), playingItem.get('fitem', {}).get('runtime'), self.saveDuration)

            newChan = oldInfo.get('chid', 'unknown') != playingItem.get('chid','unavailable')
            if newChan:
                self.runActions  = RulesList([playingItem.get('citem', {})]).runActions
                self.playingItem = self._runActions(RULES_ACTION_PLAYER_START, playingItem.get('citem', {}), playingItem, inherited=self)
                Globals.properties.setTrakt(self.disableTrakt)
                self.setSubtitles(self.lastSubState)
                self.toggleReplay(bool(self.replayPercentage))
                
                if self.playingThread is not None and self.playingThread.is_alive():
                    self.playingStopped.set()
                    self.playingThread.join(timeout=1.0)
                    
                self.playingStopped.clear()
                self.playingThread = Thread(target=self._onPlaying, daemon=True)
                self.playingThread.start()
            else:
                self.playingItem = playingItem
                if playingItem.get('radio', False): 
                    Globals.builtin.executebuiltin('Action(back)')
                    Globals.builtin.executewindow('ReplaceWindow(visualisation)')
                elif playingItem.get('isPlaylist', False): 
                    Globals.builtin.executewindow('ReplaceWindow(fullscreenvideo)')
            self.toggleInfo(self.infoOnChange)   
            
            if not self.playingItem.get('callback') and self.jsonRPC:
                self.playingItem['callback'] = self.jsonRPC.getCallback(self.playingItem)
                Globals.properties.setProperty('lastPlayed.sysInfo', self.playingItem)
                      
    def _onChange(self, playingItem: Optional[dict] = None):
        self.log(f"_onChange")
        if playingItem is None: playingItem = {}
        self.toggleOverlay(False)
        if playingItem:
            if not playingItem.get('isPlaylist', False):
                self.toggleBackground(self.enableOverlay)
                Globals.builtin.executebuiltin(f"PlayMedia({playingItem.get('callback')})")
            self._runActions(RULES_ACTION_PLAYER_CHANGE, playingItem.get('citem', {}), playingItem, inherited=self)
        else:
            self.toggleBackground(False)
        
    def _onError(self, playingItem: Optional[dict] = None):
        self.log(f"_onError")
        if playingItem is None: playingItem = {}
        if self.isPseudoTV() and Globals.settings.getSettingBool('Debug_Enable'):
            Globals.dialog.notificationDialog(LANGUAGE(32000))
            self.onPlayBackStopped()
           
    def _onStop(self, playingItem: Optional[dict] = None):
        self.log(f"_onStop")
        if playingItem is None: playingItem = {}
        self.toggleInfo(False)
        self.toggleOverlay(False)
        self.toggleBackground(False)
        
        if playingItem:
            Globals.properties.setTrakt(False)
            if playingItem.get('isPlaylist', False): xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
            if self.jsonRPC: self.jsonRPC.quePlaycount(playingItem.get('fitem', {}), self.rollbackPlaycount)
            self._runActions(RULES_ACTION_PLAYER_STOP, playingItem.get('citem', {}), playingItem, inherited=self)
            self.playingItem = {}
        self.playingStopped.set()
            
    def _runActions(self, action: str, citem: Optional[dict] = None, parameter: Any = None, inherited: Any = None) -> Any:
        if citem is None: citem = {}
        if self.runActions: return self.runActions(action, citem, parameter, inherited)
        return parameter

    def _onSleep(self):
        self.log('_onSleep')
        xbmc.playSFX(NOTE_WAV)
        dia = Globals.dialog.progressDialog(message=LANGUAGE(30078))
        inc = int(100 / 15)
        cnx = False
        
        for sec in range(1, 16):
            if self.monitor.abortRequested() or self.service._shutdown(1.0) or dia is None:
                cnx = True
                break
            msg = f"{LANGUAGE(32039)}\n{LANGUAGE(32040) % (15 - sec)}"
            dia = Globals.dialog.progressDialog((inc * sec), dia, msg)
        if dia: Globals.dialog.progressDialog(100, dia)
        return not cnx

    def toggleBackground(self, state: bool = False):
        self.log(f"toggleBackground, state = {state}")
        try:
            if state and self.background is None:
                if self.overlay: self.toggleOverlay(False)
                self.background = Background(BACKGROUND_XML, ADDON_PATH, "default", service=self.service)
                self.background.show()
            elif not state:
                if hasattr(self.background, 'close'): self.background.close()
                self.background = None
        except Exception as e: self.log(f"toggleBackground, failed: {e}", xbmc.LOGERROR)

    def toggleOverlay(self, state: bool = False):
        self.log(f"toggleOverlay, state = {state}")
        try:
            if state and self.overlay is None:
                self.overlay = Overlay(service=self.service)
                self.overlay.open()
            elif not state:
                if hasattr(self.overlay, 'close'): self.overlay.close()
                self.overlay = None
        except Exception as e: self.log(f"toggleOverlay, failed: {e}", xbmc.LOGERROR)

    # @debounceit(OSD_TIMER)
    def toggleReplay(self, state: bool = False):
        self.log(f"toggleReplay, state = {state}")
        if state and self.replay is None:
            self.replay = Replay(REPLAY_XML, ADDON_PATH, "default", "1080i", service=self.service)
            if   hasattr(self.replay, 'show_dialog'): self.replay.show_dialog()
            elif hasattr(self.replay, 'doModal'):     self.replay.doModal()
        elif not state:
            if   hasattr(self.replay, 'onClose'): self.replay.onClose()
            elif hasattr(self.replay, 'close'):   self.replay.close()
            self.replay = None


    # @debounceit(OSD_TIMER)
    def toggleInfo(self, state: bool = False):
        self.log(f"toggleInfo, state = {state}")
        if state and not Globals.builtin.getInfoBool('Window.IsVisible(fullscreeninfo)'):
            Globals.builtin.executewindow('ActivateWindow(fullscreeninfo)')
            timerit(self.toggleInfo)(float(OSD_TIMER), False)
        elif not state:
            if Globals.builtin.getInfoBool('Window.IsVisible(fullscreeninfo)'):
                Globals.builtin.executebuiltin('Action(back)')
            Globals.builtin.executebuiltin('Globals.dialog.Close(fullscreeninfo)')
           
class Monitor(xbmc.Monitor):
    def __init__(self, service: 'Service'):
        super(Monitor, self).__init__()
        self.idleTime   = 0
        self.isIdle     = False
        self.isPlaying  = False
        self.service    = service
        self.pool       = service.pool
        self.jsonRPC    = service.jsonRPC
        self.player     = Player(monitor=self, service=service)
        LOG(f"Monitor: Player created = {self.player is not None}")
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)

    def _onIdle(self):
        #chkidle
        self.idleTime = Globals.builtin.getIdle()
        self.isIdle   = self.idleTime > OSD_TIMER
        self.log(f"__onIdle, isIdle = {self.isIdle}")
        if self.player.isPlayingPseudoTV():
            #chkerror
            if self.player.pendingItem.get('invoked', -1) > 0 and not Globals.builtin.isBusyDialog():
                if (time.time() - self.player.pendingItem.get('invoked', -1)) > self.player.playbackTimeout:
                    self.player.onPlayBackError()
            #chksleep
            if self.player.sleepTime > 0 and (self.idleTime > (self.player.sleepTime * 10800)):
                    if self.player._onSleep(): self.player.stop()
            #chkresume
            self.player.onAVChange()
        #chksync
        self._chkSync()

    def onNotification(self, sender: str, method: str, data: str):
        self.log(f"onNotification received -> Sender: {sender} | Method: {method} | Data: {data}")
        if 'pvr' in sender.lower() or 'PVR' in method:
            self._logEvents(method, data)

    def _logEvents(self, method: str, data: str):
        """Track PVR-related notification events."""
        try:
            info = Globals._decodeDict(data) if data else {}
        except Exception:
            info = {}
        now = time.time()
        
        if 'Channel' in method:
            ch_type = info.get('channeltype', 'tv')
            self.log(f"_logEvents, channel {ch_type} update received")
        elif 'Epg' in method:
            self.log(f"_logEvents, EPG update received")
        elif 'Scanner' in method or 'Scan' in method:
            self.log(f"_logEvents, scanner event: {method}")

    _lastSyncCheck = 0
    def _chkSync(self):
        """Periodic health check - verify PVR sync every 5 minutes."""
        now = time.time()
        if (now - self._lastSyncCheck) < 300: return
        self._lastSyncCheck = now
        try:
            if hasattr(self.service, 'tasks') and hasattr(self.service.tasks, 'chkSync'):
                self.service._que(self.service.tasks.chkSync, 3)
        except Exception: pass

    # @debounceit()
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
        self.player.enableOverlay      = Globals.settings.getSettingBool('Overlay_Enable')
        self.player.infoOnChange       = Globals.settings.getSettingBool('Enable_OnInfo')
        self.player.disableTrakt       = Globals.settings.getSettingBool('Disable_Trakt')
        self.player.rollbackPlaycount  = Globals.settings.getSettingBool('Rollback_Watched')
        self.player.saveDuration       = Globals.settings.getSettingBool('Store_Duration')
        self.player.minDuration        = Globals.settings.getSettingInt('Seek_Tolerance')
        self.player.maxProgress        = Globals.settings.getSettingInt('Seek_Threshold')
        self.player.sleepTime          = Globals.settings.getSettingInt('Idle_Timer')
        self.player.runWhilePlaying    = Globals.settings.getSettingBool('Run_While_Playing')
        self.player.replayPercentage   = Globals.settings.getSettingInt('Replay_Percentage')
        self.player.OnNextMode         = Globals.settings.getSettingInt('OnNext_Mode')
        self.player.onNextPosition     = Globals.settings.getSetting("OnNext_Position_XY")

class Service(object):
    pendingShutdown  = False
    pendingRestart   = False
    pendingInterrupt = False
    pendingSuspend   = False
    
    def __init__(self):
        self.log("Initializing core system service layers...")
        self.isClient    = Globals.settings.getSettingBool('Enable_Client')
        self.jsonQue     = list(Globals.settings.getCacheSetting('jsonQue', default=[]))
        self.postQue     = set(Globals.settings.getCacheSetting('postQue', default=[]))
        self.logoQue     = set(Globals.settings.getCacheSetting('logoQue', default=[]))
        self.trailerQue  = set(Globals.settings.getCacheSetting('trailerQue', default=[]))
        self.imageCache  = OrderedDict(Globals.settings.getCacheSetting('imageCache', default={}))
        
        self.pool        = ExecutorPool()
        self.cache       = Cache(mem_cache=True)
        self.jsonRPC     = JSONRPC(service=self)
        self.monitor     = Monitor(service=self)
        self.player      = self.monitor.player
        self.tasks       = Tasks(service=self)
        self.queue       = CustomQueue(service=self)
        
        self.curchannels = self.tasks.getChannels()
        self.cursettings = Globals.settings.getCurrentSettings()

    def __del__(self):
        self._save()

    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)

    def _que(self, func: Callable, priority: int = 3, delay: float = 0, timer: float = 0, *args: Any, **kwargs: Any):
        self.queue.push((func, args, kwargs), priority, delay, timer)

    def _isPlaying(self) -> bool: #assert isPseudoTV Playing/User allows background tasks while playing.
        if self.player.isPlaying() and not getattr(self.player, 'runWhilePlaying', False): return True
        return False     
        
    def _save(self) -> bool:
        try:
            Globals.settings.setCacheSetting('jsonQue'   , list(self.jsonQue))
            Globals.settings.setCacheSetting('postQue'   , list(self.postQue))
            Globals.settings.setCacheSetting('logoQue'   , list(self.logoQue))
            Globals.settings.setCacheSetting('trailerQue', list(self.trailerQue))
            Globals.settings.setCacheSetting('imageCache', dict(self.imageCache))
        except Exception as e: self.log(f"_save, failed! {str(e)}", xbmc.LOGERROR)
        return True

    def _shutdown(self, wait: Optional[float] = None) -> bool:
        if wait is None: wait = SERVICE_INTERVAL
        pending_restart = Globals.properties.isPendingRestart()
        pending_state   = pending_restart or Globals.properties.isPendingShutdown() or self.monitor.waitForAbort(wait)
        if self.pendingShutdown != pending_state:
            self.pendingRestart  = pending_restart
            self.pendingShutdown = pending_state
            self.log(f"_shutdown: state={pending_state}, restart={pending_restart}, lock_delay={wait}")
        return self.pendingShutdown

    def interrupt(self) -> bool:
        pending_state = any((self.pendingRestart, self.pendingShutdown, Globals.properties.isInterruptActivity(), Globals.builtin.isScanning(), self._isPlaying()))
        if self.pendingInterrupt != pending_state:
            self.pendingInterrupt = Globals.properties.setPendingInterrupt(pending_state)
            self.log(f"interrupt boundary changed: active={self.pendingInterrupt}")
        return self.pendingInterrupt

    def suspend(self) -> bool:
        pending_state = any((Globals.properties.isSuspendActivity(), Globals.builtin.isSettingsOpened()))
        if pending_state != self.pendingSuspend:
            self.pendingSuspend = Globals.properties.setPendingSuspend(pending_state)
            self.log(f"suspend boundary changed: active={self.pendingSuspend}")
        return self.pendingSuspend
        
    def sleep(self, wait: float = CPU_CYCLE) -> bool:
        while not self.monitor.abortRequested():
            if   self.interrupt():     break
            elif self._shutdown(wait): break
        return True
               
    def _tasks(self):
        self.monitor._onIdle()
        self._que(self.tasks.chkQueTimer, 3, 30.0)
        
    def _initialize(self):
        self._que(self.tasks._client if self.isClient else self.tasks._host, 1)
        Globals.properties.setEXTProperty(f'{ADDON_ID}.Local_Host', self.jsonRPC.getLocalHost())
        if self.player.isPlayingPseudoTV(): self.player.onAVStarted()
                
    def _start(self) -> bool:
        self._initialize()
        Globals.dialog.notificationWait(f"{LANGUAGE(32054)}...", wait=15, usethread=True)
        self.log("_start, service started")
        while not self.monitor.abortRequested():
            if    self._shutdown(): break
            else: self._tasks()
        self.monitor.waitForAbort(SERVICE_INTERVAL)
        return self._stop(self.pendingRestart)

    def _stop(self, pendingRestart: bool = False) -> bool:
        if self.player.isPlayingPseudoTV(): self.player.onPlayBackStopped()
        with Globals.properties.interruptActivity():
            for thread in threading.enumerate():
                if thread.name != "MainThread" and thread.is_alive():
                    if thread.name.startswith(f"{ADDON_ID}"):
                        self.log(f"_stop, Terminating Thread: {thread.name}")
                        if hasattr(thread, 'cancel'): thread.cancel()
                        try:  thread.join(timeout=0.5)
                        except Exception as e: self.log('_stop thread join failed: %s' % e, xbmc.LOGDEBUG)
        if self._save():
            self.pool.shutdown(wait=False, cancel=True)
            self.cache.shutdown()
        _Service().pool.shutdown(wait=False, cancel=True)
        Globals.properties._clrTrash(Globals.properties.getProcessID())
        self.log(f"_stop, service shutdown sequence. Restart state: {pendingRestart}")
        return pendingRestart
        
        