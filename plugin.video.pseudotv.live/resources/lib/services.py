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
    """
    Player Event Trigger Execution Pipeline:
    1. onPlayBackStarted
    2. onAVChange (if codec shifts/resolves during playback initialization)
    3. onAVStarted
    4. onPlayBackSeek / onPlayBackStopped / onPlayBackEnded
    """
    enableOverlay      = SETTINGS.getSettingBool('Overlay_Enable')
    infoOnChange       = SETTINGS.getSettingBool('Enable_OnInfo')
    disableTrakt       = SETTINGS.getSettingBool('Disable_Trakt')
    rollbackPlaycount  = SETTINGS.getSettingBool('Rollback_Watched')
    saveDuration       = SETTINGS.getSettingBool('Store_Duration')
    minDuration        = SETTINGS.getSettingInt('Seek_Tolerance')
    maxProgress        = SETTINGS.getSettingInt('Seek_Threshold')
    sleepTime          = SETTINGS.getSettingInt('Idle_Timer')
    runWhilePlaying    = SETTINGS.getSettingBool('Run_While_Playing')
    replayPercentage   = SETTINGS.getSettingInt('Replay_Percentage')
    OnNextMode         = SETTINGS.getSettingInt('OnNext_Mode')
    onNextPosition     = SETTINGS.getSetting("OnNext_Position_XY")	
    
    def __init__(self, monitor=None, service=None):
        super().__init__()
        self.monitor = monitor
        self.service = service
        self.jsonRPC = service.jsonRPC if service else None

        self.pendingItem = {}
        self.playingItem = {}

        self.background = None
        self.overlay = None
        self.replay = None
        self.runActions = None
        self.lastSubState = False
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def onPlayBackStarted(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'item': {}, 'last': self.pendingItem.get('item', {})})
        self.log(f"onPlayBackStarted: pendingItem={self.pendingItem}")

    def onAVChange(self):
        self.pendingItem.update({'resume': -1, 'seek': -1, 'item': {}})
        self.log(f"onAVChange: playingItem={self.playingItem}")
        
    def onAVStarted(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'item': self.getplayingItem()})
        self.log(f"onAVStarted: pendingItem={self.pendingItem}")
        self._onPlay(self.pendingItem.get('item', {}))
        
    def onPlayBackSeek(self, seek_time=None, seek_offset=None):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'item': {}})
        self.log(f"onPlayBackSeek: time={seek_time}, offset={seek_offset}")
    
    def onPlayBackError(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'item': {}})
        self.log("onPlayBackError triggered", xbmc.LOGERROR)
        self._onError(self.playingItem)
        
    def onPlayBackEnded(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'item': {}})
        self.log("onPlayBackEnded")
        self._onChange(self.playingItem)
        
    def onPlayBackStopped(self):
        self.pendingItem.update({'invoked': -1, 'pending': False, 'item': {}})
        self.log("onPlayBackStopped")
        self._onStop(self.playingItem)

    def getplayingItem(self):
        try: 
            playingItem = FileAccess._decodeString(self.getPlayingItem().getProperty('sysInfo')) or {}
            if f"@{Globals._slugify(ADDON_NAME)}" in playingItem.get('chid', ''):
                playingItem['isPseudoTV'] = True
                playingItem['chfile']     = BUILTIN.getInfoLabel('Player.Filename')
                playingItem['chfolder']   = BUILTIN.getInfoLabel('Player.Folderpath')
                playingItem['chpath']     = BUILTIN.getInfoLabel('Player.Filenameandpath')
                
                f_item = combineDicts(playingItem.get('fitem', {}), Globals._decodePlot(BUILTIN.getInfoLabel('VideoPlayer.Plot')))
                n_item = combineDicts(playingItem.get('nitem', {}), Globals._decodePlot(BUILTIN.getInfoLabel('VideoPlayer.NextPlot')))
                channel_match = next((item for item in getattr(self.service, 'curchannels', []) if item.get('id', -1) == playingItem.get('chid', 0)), {})
                c_item = combineDicts(f_item.get('citem', {}), channel_match)
                
                f_item['runtime'] = self.getPlayerTime()
                f_item['isfiller'] = isFiller(f_item)
                n_item['isfiller'] = isFiller(n_item)
                
                playingItem.update({'fitem': f_item, 'nitem': n_item, 'citem': c_item})
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
        return self.isPlaying() and self.isPseudoTV()

    def setSubtitles(self, state: bool = True):
        if not BUILTIN.hasSubtitle(): state = False
        self.showSubtitles(state)

    @threadit
    def _onPlay(self, playingItem=None):
        if playingItem is None: playingItem = {}
        self.log(f"_onPlay tracking hit: {playingItem}")
        self.toggleInfo(False)
        self.toggleOverlay(False)
        self.toggleBackground(False)
        self.lastSubState = BUILTIN.isSubtitle()
        
        if playingItem.get('isPseudoTV'):
            oldInfo = self.playingItem
            newChan = oldInfo.get('chid', random.random()) != playingItem.get('chid')
            if newChan:
                self.runActions = RulesList([playingItem.get('citem', {})]).runActions
                self.playingItem = self._runActions(RULES_ACTION_PLAYER_START, playingItem.get('citem', {}), playingItem, inherited=self)
                PROPERTIES.setTrakt(self.disableTrakt)
                self.setSubtitles(self.lastSubState)
                self.toggleReplay(bool(self.replayPercentage))
            else:
                self.playingItem = playingItem
                if playingItem.get('radio', False): 
                    BUILTIN.executebuiltin('Action(back)')
                    BUILTIN.executewindow('ReplaceWindow(visualisation)')
                elif playingItem.get('isPlaylist', False): 
                    BUILTIN.executewindow('ReplaceWindow(fullscreenvideo)')
                self.toggleInfo(self.infoOnChange)
                
            if self.jsonRPC:
                self.jsonRPC.quePlaycount(oldInfo.get('fitem', {}), self.rollbackPlaycount)
                self.jsonRPC._setRuntime(playingItem.get('fitem', {}), playingItem.get('fitem', {}).get('runtime'), self.saveDuration)

    @threadit
    def _onChange(self, playingItem=None):
        if playingItem is None: playingItem = {}
        self.toggleOverlay(False)
        if playingItem:
            if not playingItem.get('isPlaylist', False):
                self.toggleBackground(self.enableOverlay)
                BUILTIN.executebuiltin(f"PlayMedia({playingItem.get('callback')})")
            self._runActions(RULES_ACTION_PLAYER_CHANGE, playingItem.get('citem', {}), playingItem, inherited=self)
        else:
            self.toggleBackground(False)
        
    @threadit
    def _onError(self, playingItem=None):
        if playingItem is None: playingItem = {}
        if self.isPseudoTV() and SETTINGS.getSettingBool('Debug_Enable'):
            DIALOG.notificationDialog(LANGUAGE(32000))
            self._onStop(playingItem)
           
    @threadit 
    def _onStop(self, playingItem=None):
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
            
    def _runActions(self, action, citem=None, parameter=None, inherited=None):
        if citem is None: citem = {}
        if self.runActions: return self.runActions(action, citem, parameter, inherited)
        return parameter

    def _onSleep(self):
        self.log('_onSleep dialog warning sequence engaged.')
        xbmc.playSFX(NOTE_WAV)
        dia = DIALOG.progressDialog(message=LANGUAGE(30078))
        inc = int(100 / 15)
        cnx = False
        
        for sec in range(1, 16):
            if self.monitor.abortRequested() or self.service._shutdown(1.0) or dia is None:
                cnx = True
                break
            msg = f"{LANGUAGE(32039)}\n{LANGUAGE(32040) % (15 - sec)}"
            dia = DIALOG.progressDialog((inc * sec), dia, msg)
        if dia: DIALOG.progressDialog(100, dia)
        return not cnx

    def _onIdle(self):
        if not self.isPlaying(): return
        if self.pendingItem.get('invoked', -1) > 0 and not BUILTIN.isBusyDialog():
            if (time.time() - self.pendingItem.get('invoked', -1)) > SETTINGS.getSettingInt('Playback_Timeout'):
                self.onPlayBackError()
                return

        played    = ceil(self.getPlayedTime())
        remaining = floor(self.getRemainingTime())
        if not self.playingItem.get('callback') and self.jsonRPC:
            self.playingItem['callback'] = self.jsonRPC.getCallback(self.playingItem)
            PROPERTIES.setProperty('lastPlayed.sysInfo', self.playingItem)

        if remaining <= (OSD_TIMER * 2):
            self.toggleBackground(self.enableOverlay)

        if not self.isPlayingFiller():
            if self.playingItem.get('isPlaylist', False) and self.playingItem.get('fitem', {}).get('file') == self.getPlayingFile():
                resume = {
                    "position": played,
                    "total": self.getPlayerTime(),
                    "file": self.getPlayerFile(),
                    "updated": {'instance': PROPERTIES.getFriendlyName(), 'time': getUTCstamp()}
                }
                self.playingItem.setdefault('resume', {}).update(resume)
            if played > self.minDuration: 
                self.toggleOverlay(self.enableOverlay)

        if self.isPlayingPseudoTV() and not self.isPlayingFiller() and self.overlay is not None:
            total_time = int(self.getPlayerTime() * (self.maxProgress / 100))
            threshold = abs((total_time - (total_time * 0.75)) - (ONNEXT_TIMER * 3))
            int_time = roundupDIV(threshold, 3)
            
            if played > self.minDuration and (threshold >= remaining >= int_time): 
                self.overlay.toggleOnNext(bool(self.OnNextMode))
        
        if self.sleepTime > 0 and (self.monitor.idleTime > (self.sleepTime * 10800)):
            if not PROPERTIES.isRunning('Player.__chkSleep'):
                with PROPERTIES.chkRunning('Player.__chkSleep'):
                    if self._onSleep(): 
                        self.stop()
                        
    def toggleBackground(self, state: bool = None):
        if state is None: state = self.enableOverlay
        if state and self.monitor.isIdle and self.background is None:
            if self.overlay is not None: 
                self.toggleOverlay(False)
            BUILTIN.executebuiltin("Dialog.Close(all)")
            self.background = Background(BACKGROUND_XML, ADDON_PATH, "default", service=self.service)
            self.background.show()
        elif not state and self.background is not None:
            if hasattr(self.background, 'close'):
                self.background.close()
            self.background = None

    def toggleOverlay(self, state: bool = None):
        if state is None: state = self.enableOverlay
        if state and self.isPlayingPseudoTV() and self.overlay is None:
            self.overlay = Overlay(service=self.service)
            self.overlay.open()
        elif not state and self.overlay is not None:
            if hasattr(self.overlay, 'close'):
                self.overlay.close()
            self.overlay = None

    def toggleReplay(self, state: bool = None):
        if state is None: state = bool(self.replayPercentage)
        if state and self.isPlayingPseudoTV() and not self.isPlayingFiller() and self.replay is None:
            self.replay = Replay(REPLAY_XML, ADDON_PATH, "default", "1080i", service=self.service)
            if hasattr(self.replay, 'show_dialog'):
                self.replay.show_dialog()
            else:
                self.replay.doModal()
        elif not state and self.replay is not None:
            if hasattr(self.replay, 'onClose'):
                self.replay.onClose()
            elif hasattr(self.replay, 'close'):
                self.replay.close()
            self.replay = None

    def toggleInfo(self, state: bool = None):
        if state is None: state = self.infoOnChange
        is_info_visible = BUILTIN.getInfoBool('Window.IsVisible(fullscreeninfo)')
        if state and self.isPlayingPseudoTV() and not self.isPlayingFiller() and not is_info_visible:
            BUILTIN.executewindow('ActivateWindow(fullscreeninfo)')
            timerit(self.toggleInfo)(float(OSD_TIMER), False)
        elif not state and is_info_visible:
            BUILTIN.executebuiltin('Action(back)')
            BUILTIN.executebuiltin('Dialog.Close(fullscreeninfo)')


class Monitor(xbmc.Monitor):
    def __init__(self, service=None):
        super().__init__()
        self.service    = service
        self.jsonRPC    = service.jsonRPC if service else None
        self.idleTime   = 0
        self.isIdle     = False
        self.isRunning  = False
        self.player     = Player(monitor=self, service=service)
        self.idle_lock  = threading.Lock()
        self.idleThread = None

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def chkIdle(self):
        with self.idle_lock:
            if self.idleThread and self.idleThread.is_alive():
                try: self.idleThread.join(timeout=0.2)
                except Exception: pass
            self.idleThread = threading.Thread(target=self._chkIdle, name="PseudoTV_IdleMonitor")
            self.idleThread.daemon = True
            self.idleThread.start()
            
    def _chkIdle(self):
        if self.isRunning: return
        self.isRunning = True
        self.log("Background idle tracking engine engaged.")
        try:
            while not self.abortRequested():
                if self.service._shutdown(0.5): break
                if self.player.isPlayingPseudoTV():
                    self.idleTime = BUILTIN.getIdle()
                    self.isIdle = self.idleTime > OSD_TIMER
                    if self.isIdle: self.player._onIdle()
                else:
                    self.log("_chkIdle: Playback state dropped, pausing loop.")
                    break
        finally:
            self.isRunning = False
            self.log("_chkIdle background lifecycle completed.")

    def onNotification(self, sender, method, data):
        self.log(f"onNotification received -> Sender: {sender} | Method: {method} | Data: {data}")

    @debounceit(SERVICE_INTERVAL)
    def onSettingsChanged(self):
        self.log('onSettingsChanged; queuing settings synchronization...')
        self.service._que(self._updatePlayerSettings)
        self.service._que(self._updateServiceSettings)
            
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
    def __init__(self):
        self.log("Initializing core system service layers...")
        self.channels   = []
        self.isScanning = False
        self.isPaused   = False
        self.isPlaying  = False
        self.isClient   = SETTINGS.getSettingBool('Enable_Client')
        
        self.pendingSuspend   = False
        self.pendingInterrupt = False
        self.pendingShutdown  = False
        self.pendingRestart   = False
        
        self.jsonQue    = set(SETTINGS.getCacheSetting('jsonQue', default=[]))
        self.postQue    = set(SETTINGS.getCacheSetting('postQue', default=[]))
        self.logoQue    = set(SETTINGS.getCacheSetting('logoQue', default=[]))
        self.trailerQue = set(SETTINGS.getCacheSetting('trailerQue', default=[]))
        self.imageCache = OrderedDict(SETTINGS.getCacheSetting('imageCache', default={}))

        self.jsonRPC = JSONRPC(service=self)
        self.monitor = Monitor(service=self)
        self.player  = self.monitor.player
        self.tasks   = Tasks(service=self)
        
        self.curchannels = self.tasks.getChannels()
        self.cursettings = SETTINGS.getCurrentSettings()
        self.priorityQUE = CustomQueue(service=self)

    def __del__(self):
        self._saveCache()

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def _que(self, func, priority=-1, delay=0, timer=0, *args, **kwargs):
        self.priorityQUE._push((func, args, kwargs), priority, delay, timer)

    def _isPlaying(self) -> bool:
        if (self.isPlaying or self.isPaused) and not getattr(self.player, 'runWhilePlaying', False): 
            return True
        return False
        
    def _tasks(self):
        self._que(self.tasks.chkQueTimer, 1, DISCOVER_INTERVAL)
        
    def _shutdown(self, wait=SERVICE_INTERVAL) -> bool:
        pending_state = any([PROPERTIES.isPendingShutdown(), self.monitor.waitForAbort(wait)])
        PROPERTIES.clrEXTProperty(f'{ADDON_ID}.SERVICE.pendingShutdown')
        if self.pendingShutdown != pending_state:
            self.pendingShutdown = pending_state
            self.log(f"_shutdown flag mutated: state={self.pendingShutdown}, lock_delay={wait}")
        return self.pendingShutdown
        
    def _restart(self) -> bool:
        pending_state = PROPERTIES.isPendingRestart()
        PROPERTIES.clrEXTProperty(f'{ADDON_ID}.SERVICE.pendingRestart')
        if self.pendingRestart != pending_state:
            self.pendingRestart = pending_state
            self.log(f"_restart flag mutated: state={self.pendingRestart}")
        return self.pendingRestart
         
    def _interrupt(self) -> bool:
        pending_state = any([
            PROPERTIES.isInterruptActivity(), 
            self.pendingShutdown, 
            self.pendingRestart, 
            self.isScanning, 
            self._isPlaying()
        ])
        
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
            if self.monitor.waitForAbort(CPU_CYCLE) or self._interrupt(): 
                return True
            wait -= CPU_CYCLE
        return False
               
    def _initialize(self):
        PROPERTIES.setEXTProperty(f'{ADDON_ID}.Local_Host', self.jsonRPC.getLocalHost())
        if self.isClient: self._que(self.tasks._client, 1)
        else:             self._que(self.tasks._host, 1)

    def _saveCache(self):
        try:
            SETTINGS.setCacheSetting('jsonQue', list(self.jsonQue))
            SETTINGS.setCacheSetting('postQue', list(self.postQue))
            SETTINGS.setCacheSetting('logoQue', list(self.logoQue))
            SETTINGS.setCacheSetting('trailerQue', list(self.trailerQue))
            SETTINGS.setCacheSetting('imageCache', dict(self.imageCache))
        except Exception as e: self.log(f"_saveCache, failed! {str(e)}", xbmc.LOGERROR)
        return True

    def _start(self):
        self.log("Starting main core background lifecycle...")
        self._initialize()
        if DIALOG.notificationWait(f"{LANGUAGE(32054)}...", wait=15):
            if self.player.isPlayingPseudoTV(): 
                self.player.onAVStarted()
                
            while not self.monitor.abortRequested():
                self.isScanning  = BUILTIN.isScanning()
                self.isPaused    = BUILTIN.isPaused()
                self.isPlaying   = self.player.isPlaying()
                isInterrupt      = self._interrupt()
                
                if self._shutdown() and isInterrupt:
                    self._sleep()
                    break
                elif self._restart() and isInterrupt:
                    self._sleep()
                    break
                elif not self._isPlaying(): self._tasks()
                self.monitor.waitForAbort(CPU_CYCLE)
            return self._stop(self.pendingRestart)

    def _stop(self, pendingRestart: bool = False) -> bool:
        self.log(f"_stop, shutdown sequence. Restart state: {pendingRestart}")
        if self.player.isPlayingPseudoTV(): self.player.onPlayBackStopped()
        if self._saveCache(): SETTINGS.cache.cache.shutdown()
        with PROPERTIES.interruptActivity():
            for thread in threading.enumerate():
                if thread.name != "MainThread" and thread.is_alive():
                    if "PseudoTV" in thread.name or thread.name.startswith(f"{ADDON_ID}"):
                        self.log(f"Terminating module-bound worker worker: {thread.name}")
                        if hasattr(thread, 'cancel'): thread.cancel()
                        try:  thread.join(timeout=0.5)
                        except Exception: pass
            PROPERTIES._clrTrash(PROPERTIES.getProcessID())
        return pendingRestart