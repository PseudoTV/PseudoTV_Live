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
#
# -*- coding: utf-8 -*-
from globals    import *
from overlay    import Background, Restart, Overlay, OnNext
from rules      import RulesList
from tasks      import Tasks
from jsonrpc    import JSONRPC


class Player(xbmc.Player):
    sysInfo      = {}
    isPseudoTV   = False
    pendingStop  = False
    pendingPlay  = -1
    lastSubState = False
    background   = None
    restart      = None
    onnext       = None
    overlay      = None
    channelBug   = None
    rules        = RulesList()
    runActions   = rules.runActions
    
    """ 
    Player() Trigger Order
    Player: onPlayBackStarted
    Player: onAVChange (if playing)
    Player: onAVStarted
    Player: onPlayBackSeek (if seek)
    Player: onAVChange (if changed)
    Player: onPlayBackError
    Player: onPlayBackEnded
    Player: onPlayBackStopped
    """
    
    def __init__(self, service=None):
        xbmc.Player.__init__(self)
        self.service           = service
        self.jsonRPC           = service.jsonRPC
        self.enableOverlay     = SETTINGS.getSettingBool('Overlay_Enable')
        self.infoOnChange      = SETTINGS.getSettingBool('Enable_OnInfo')
        self.disableTrakt      = SETTINGS.getSettingBool('Disable_Trakt')
        self.rollbackPlaycount = SETTINGS.getSettingBool('Rollback_Watched')
        self.saveDuration      = SETTINGS.getSettingBool('Store_Duration')
        self.minDuration       = SETTINGS.getSettingInt('Seek_Tolerance')
        self.maxProgress       = SETTINGS.getSettingInt('Seek_Threshold')
        self.sleepTime         = SETTINGS.getSettingInt('Idle_Timer')
        self.runWhilePlaying   = SETTINGS.getSettingBool('Run_While_Playing')
        self.restartPercentage = SETTINGS.getSettingInt('Restart_Percentage')
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onPlayBackStarted(self):
        self.pendingStop = True
        self.pendingPlay = time.time()
        self.log('onPlayBackStarted, pendingStop = %s, pendingPlay = %s'%(self.pendingStop,self.pendingPlay))
        

    def onAVChange(self):
        self.isPseudoTV   = self.isPseudoTVPlaying()
        self.lastSubState = BUILTIN.isSubtitle()
        self.log('onAVChange, pendingStop = %s, isPseudoTV = %s'%(self.pendingStop,self.isPseudoTV))
        if not self.isPseudoTV: self._onStop()

        
    def onAVStarted(self):
        self.pendingPlay = -1
        self.isPseudoTV  = self.isPseudoTVPlaying()
        self.log('onAVStarted, pendingStop = %s, isPseudoTV = %s'%(self.pendingStop,self.isPseudoTV))
        if self.isPseudoTV: self._onPlay()
        else:               self._onStop()
        
                
    def onPlayBackSeek(self, seek_time=None, seek_offset=None): #Kodi bug? `OnPlayBackSeek` no longer called by player during seek, issue limited to pvr?
        self.log('onPlayBackSeek, seek_time = %s, seek_offset = %s'%(seek_time,seek_offset))
    
    
    def onPlayBackError(self):
        self.log('onPlayBackError, pendingStop = %s, isPseudoTV = %s'%(self.pendingStop,self.isPseudoTV))
        if self.isPseudoTV: self.isPseudoTV = self._onError()
        
        
    def onPlayBackEnded(self):
        self.pendingStop = False
        self.pendingPlay = -1
        self.log('onPlayBackEnded, pendingStop = %s, isPseudoTV = %s, isPlaylist = %s'%(self.pendingStop,self.isPseudoTV,self.sysInfo.get('isPlaylist',False)))
        if self.isPseudoTV: self._onChange()
        
        
    def onPlayBackStopped(self):
        self.pendingStop = False
        self.pendingPlay = -1
        self.log('onPlayBackStopped, pendingStop = %s, isPseudoTV = %s'%(self.pendingStop,self.isPseudoTV))
        if self.isPseudoTV: self.isPseudoTV = self._onStop()
        
        
    def isPseudoTVPlaying(self):
        chid  = loadJSON(decodeString(self.getPlayerItem().getProperty('sysInfo'))).get('chid','')
        state = '@%s'%(slugify(ADDON_NAME)) in chid
        self.log('isPseudoTVPlaying = %s, id = %s'%(state,chid))
        return state
        
        
    def getPlayerSysInfo(self):
        def __update(id, citem={}):
            channels = self.service.tasks.getChannels()
            for item in channels:
                if item.get('id',random.random()) == id: 
                    return combineDicts(citem,item)
            return citem
            
        sysInfo = loadJSON(decodeString(self.getPlayerItem().getProperty('sysInfo')))
        sysInfo['chfile']   = BUILTIN.getInfoLabel('Filename','Player')
        sysInfo['chfolder'] = BUILTIN.getInfoLabel('Folderpath','Player')
        sysInfo['chpath']   = BUILTIN.getInfoLabel('Filenameandpath','Player')
        if not sysInfo.get('fitem'): sysInfo.update({'fitem':decodePlot(BUILTIN.getInfoLabel('Plot','VideoPlayer'))})
        if not sysInfo.get('nitem'): sysInfo.update({'nitem':decodePlot(BUILTIN.getInfoLabel('NextPlot','VideoPlayer'))})
        sysInfo.update({'citem':combineDicts(sysInfo.get('citem',{}),__update(sysInfo.get('citem',{}).get('id'))),'runtime':int(self.getPlayerTime())}) #still needed for adv. rules?
        if not sysInfo.get('callback'): sysInfo['callback'] = self.jsonRPC.getCallback(sysInfo)
        self.log('getPlayerSysInfo, sysInfo = %s'%(sysInfo))
        PROPERTIES.setEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID),encodeString(dumpJSON(sysInfo)))
        return sysInfo
        
        
    def getPlayerItem(self):
        try:    return self.getPlayingItem()
        except: return xbmcgui.ListItem()


    def getPlayerFile(self):
        try:    return self.getPlayingFile()
        except: return self.sysInfo.get('fitem',{}).get('file')


    def getPlayerTime(self):
        try:    return (self.getTimeLabel('Duration') or self.getTotalTime())
        except: return (self.sysInfo.get('fitem',{}).get('runtime') or -1)
            
       
    def getPlayedTime(self):
        try:    return (self.getTimeLabel('Time') or self.getTime()) #getTime retrieves Guide times not actual media time.
        except: return -1
       
            
    def getRemainingTime(self):
        try:    return self.getPlayerTime() - self.getPlayedTime()
        except: return (self.getTimeLabel('TimeRemaining') or -1)

       
    def getPlayerProgress(self):
        try:    return int((self.getRemainingTime() / self.getPlayerTime()) * 100)
        except: return int((BUILTIN.getInfoLabel('Progress','Player') or '-1'))


    def getTimeLabel(self, prop: str='TimeRemaining') -> int and float: #prop='EpgEventElapsedTime'
        if self.isPlaying(): return timeString2Seconds(BUILTIN.getInfoLabel('%s(hh:mm:ss)'%(prop),'Player'))


    def setTrakt(self, state: bool=SETTINGS.getSettingBool('Disable_Trakt')):
        self.log('setTrakt, disable trakt = %s'%(state))
        # https://github.com/trakt/script.trakt/blob/d45f1363c49c3e1e83dabacb70729cc3dec6a815/resources/lib/kodiUtilities.py#L104
        if state: PROPERTIES.setEXTPropertyBool('script.trakt.paused',state)
        else:     PROPERTIES.clrEXTProperty('script.trakt.paused')


    def setSubtitles(self, state: bool=True):
        hasSubtitle = BUILTIN.hasSubtitle()
        self.log('setSubtitles, show subtitles = %s, hasSubtitle = %s'%(state,hasSubtitle))
        if not hasSubtitle: state = False
        self.showSubtitles(state)


    def _onPlay(self):
        oldInfo = self.sysInfo
        sysInfo = self.getPlayerSysInfo()
        newChan = oldInfo.get('chid',random.random()) != sysInfo.get('chid')
        self.log('_onPlay, [%s], mode = %s, isPlaylist = %s, new channel = %s'%(sysInfo.get('citem',{}).get('id'), sysInfo.get('mode'), sysInfo.get('isPlaylist',False), newChan))
        if newChan: #New channel
            self.sysInfo = self.runActions(RULES_ACTION_PLAYER_START, sysInfo.get('citem',{}), sysInfo, inherited=self)
            self.setTrakt(self.disableTrakt)
            self.setSubtitles(self.lastSubState) #todo allow rules to set sub preference per channel.
            # self.toggleRestart(self.enableOverlay)
            self.toggleOverlay(self.enableOverlay)
        else: #New Program/Same Channel
            self.sysInfo = sysInfo
            if self.sysInfo.get('radio',False): timerit(BUILTIN.executebuiltin)(0.5,['ReplaceWindow(visualisation)'])
            else:                               timerit(BUILTIN.executebuiltin)(0.5,['ReplaceWindow(fullscreenvideo)'])
            self.toggleInfo(self.infoOnChange)
            
        self.jsonRPC.quePlaycount(oldInfo.get('fitem',{}),self.rollbackPlaycount)
        self.jsonRPC._setRuntime(self.sysInfo.get('fitem',{}),self.sysInfo.get('runtime'),self.saveDuration)
            
            
    def _onChange(self):
        if not self.sysInfo.get('isPlaylist',False):
            self.log('_onChange, [%s], isPlaylist = %s, callback = %s'%(self.sysInfo.get('citem',{}).get('id'),self.sysInfo.get('isPlaylist',False),self.sysInfo.get('callback')))
            self.toggleBackground(self.enableOverlay)
            self.toggleOverlay(False)
            self.toggleRestart(False)
            self.toggleOnNext(False)
            self.toggleInfo(False)
            BUILTIN.executebuiltin('PlayMedia(%s)'%(self.sysInfo.get('callback')))
        elif self.sysInfo: #isPlaylist
            ...
        
        
    def _onStop(self):
        if self.sysInfo:
            self.log('_onStop, id = %s'%(self.sysInfo.get('citem',{}).get('id')))
            self.toggleBackground(False)
            self.toggleOverlay(False)
            self.toggleRestart(False)
            self.toggleOnNext(False)
            self.toggleInfo(False)
            self.setTrakt(False)
            if self.sysInfo.get('isPlaylist',False): xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
            self.jsonRPC.quePlaycount(self.sysInfo.get('fitem',{}),self.rollbackPlaycount)
            self.sysInfo = self.runActions(RULES_ACTION_PLAYER_STOP, self.sysInfo.get('citem',{}), {}, inherited=self)
    

    def _onError(self): #todo evaluate potential for error handling.
        if REAL_SETTINGS.getSetting('Debug_Enable').lower() == 'true':
            self.log('_onError, playing file = %s'%(self.getPlayerFile()))
            DIALOG.notificationDialog(LANGUAGE(32000))
            timerit(BUILTIN.executebuiltin)(0.5,['Number(0)'])
            self.stop()
            

    def toggleBackground(self, state: bool=SETTINGS.getSettingBool('Overlay_Enable')):
        if state and self.background is None and self.service.monitor.isIdle:
            self.log("toggleBackground, state = %s"%(state))
            BUILTIN.executebuiltin("Dialog.Close(all)")
            self.background = Background(BACKGROUND_XML, ADDON_PATH, "default", player=self)
            self.background.show()
        elif not state and hasattr(self.background,'close'):
            self.log("toggleBackground, state = %s"%(state))
            self.background = self.background.close()
        self.log("toggleBackground, background = %s"%(self.background))


    def toggleOverlay(self, state: bool=SETTINGS.getSettingBool('Overlay_Enable')):
        if state and self.overlay is None:
            self.log("toggleOverlay, state = %s"%(state))
            self.overlay = Overlay(player=self)
            self.overlay.open()
        elif not state and hasattr(self.overlay,'close'):
            self.log("toggleOverlay, state = %s"%(state))
            self.overlay = self.overlay.close()
        self.log("toggleOverlay, overlay = %s"%(self.overlay))


    def toggleRestart(self, state: bool=SETTINGS.getSettingBool('Overlay_Enable')):
        if state and self.restart is None:
            self.log("toggleRestart, state = %s"%(state))
            self.restart = Restart(RESTART_XML, ADDON_PATH, "default", "1080i", player=self)
            self.restart.open()
        elif not state and hasattr(self.restart,'onClose'):
            self.log("toggleRestart, state = %s"%(state))
            self.restart = self.restart.onClose()
        self.log("toggleRestart, restart = %s"%(self.restart))
        
        
    def toggleOnNext(self, state: bool=SETTINGS.getSettingBool('Overlay_Enable')):
        if state and self.onnext is None:
            self.log("toggleOnNext, state = %s"%(state))
            self.onnext = OnNext(ONNEXT_XML, ADDON_PATH, "default", "1080i", player=self)
            self.onnext.open()
        elif hasattr(self.onnext,'onClose'):
            self.log("toggleOnNext, state = %s"%(state))
            self.onnext = self.onnext.onClose()
        self.log("toggleOnNext, onnext = %s"%(self.onnext))
    
        
    def toggleInfo(self, state: bool=SETTINGS.getSettingBool('Enable_OnInfo')):
        if state and not BUILTIN.getInfoLabel('Genre','VideoPlayer') in FILLER_TYPE:
            self.log('toggleInfo, state = %s'%(state))
            timerit(self.toggleInfo)(float(OSD_TIMER),[False])
            BUILTIN.executebuiltin('ActivateWindow(fullscreeninfo)')
        elif not state and BUILTIN.getInfoBool('IsVisible(fullscreeninfo)','Window'):
            self.log('toggleInfo, state = %s'%(state))
            BUILTIN.executebuiltin('Action(back)')
            BUILTIN.executebuiltin("Dialog.Close(fullscreeninfo)")


class Monitor(xbmc.Monitor):
    idleTime   = 0
    isIdle     = False
    
    def __init__(self, service=None):
        self.log('__init__')
        xbmc.Monitor.__init__(self)
        self.service = service
        self.jsonRPC = service.jsonRPC
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def chkIdle(self):
        def __chkIdle():
            try:    self.idleTime = BUILTIN.getIdle()
            except: self.idleTime = -1
            self.isIdle = (self.idleTime > OSD_TIMER)
            self.log('__chkIdle, isIdle = %s, idleTime = %s'%(self.isIdle, self.idleTime))

        def __chkPlayback():
            if self.service.player.pendingPlay > 0:
                pendingTime = (time.time() - self.service.player.pendingPlay)
                if not BUILTIN.isBusyDialog() and pendingTime > 60: self.service.player.onPlayBackError()

        def __chkResumeTime():
            if self.service.player.sysInfo.get('isPlaylist',False):
                file = self.service.player.getPlayingFile()
                if self.service.player.sysInfo.get('fitem',{}).get('file') == file:
                    self.service.player.sysInfo.setdefault('resume',{}).update({"position":self.service.player.getTime(),"total":self.service.player.getPlayerTime(),"file":file})

        def __chkSleepTimer():
            if self.service.player.sleepTime > 0 and (self.idleTime > (self.service.player.sleepTime * 10800)):
                if not PROPERTIES.isRunning('__chkSleepTimer'):
                    with PROPERTIES.chkRunning('__chkSleepTimer'):
                        if self.sleepTimer(): self.service.player.stop()
        
        def __chkBackground():
            remaining = floor(self.service.player.getRemainingTime())
            played    = ceil(self.service.player.getPlayedTime())
            self.log('__chkBackground, isIdle = %s, remaining = %s, played = %s'%(self.isIdle, remaining, played))
            if self.isIdle and remaining < 30:  self.service.player.toggleBackground(self.service.player.enableOverlay)
            elif remaining > 30 and played > 3: self.service.player.toggleBackground(False)

        def __chkOverlay():
            played = ceil(self.service.player.getPlayedTime())
            self.log('__chkOverlay, isIdle = %s, played = %s'%(self.isIdle, played))
            if self.isIdle and played > 30: 
                self.service.player.toggleOverlay(self.service.player.enableOverlay)

        def __chkOnNext():
            totalTime = int(self.service.player.getPlayerTime() * (self.service.player.maxProgress / 100))
            threshold = abs((totalTime - (totalTime * .75)) - FIFTEEN)
            remaining = ceil(self.service.player.getRemainingTime())
            self.log('__chkOnNext, isIdle = %s, remaining = %s'%(self.isIdle, remaining))
            if self.isIdle and remaining <= threshold and remaining > 0 and self.service.player.background is None: 
                self.service.player.toggleOnNext(self.service.player.enableOverlay)
                 
        __chkIdle()
        if self.service.player.isPlaying() and self.service.player.isPseudoTV:
            __chkPlayback()
            __chkResumeTime()
            __chkSleepTimer()
            __chkBackground()
            __chkOverlay()
            __chkOnNext()


    def sleepTimer(self):
        self.log('sleepTimer')
        sec = 0
        cnx = False
        inc = int(100/FIFTEEN)
        xbmc.playSFX(NOTE_WAV)
        dia = DIALOG.progressDialog(message=LANGUAGE(30078))
        while not self.abortRequested() and (sec < FIFTEEN):
            sec += 1
            msg = '%s\n%s'%(LANGUAGE(32039),LANGUAGE(32040)%(FIFTEEN-sec))
            dia = DIALOG.progressDialog((inc*sec),dia, msg)
            if self.waitForAbort(1.0) or dia is None:
                cnx = True
                break
        DIALOG.progressDialog(100,dia)
        return not bool(cnx)


    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            

    def onSettingsChanged(self):
        self.log('onSettingsChanged')
        if self.service: timerit(self.onSettingsChangedTimer)(15.0)
        
        
    def onSettingsChangedTimer(self):
        self.log('onSettingsChangedTimer') 
        self.service.tasks._que(self._onSettingsChanged,1)
                
                
    def _onSettingsChanged(self):
        self.log('_onSettingsChanged')
        self.service.player.__init__(self.service)
        self.service.currentSettings = self.service.tasks.chkSettingsChange(self.service.currentSettings) #check for settings change, take action if needed
        

class Service():
    currentSettings  = []
    pendingSuspend   = PROPERTIES.setPendingSuspend(False)
    pendingInterrupt = PROPERTIES.setPendingInterrupt(False)
    pendingShutdown  = PROPERTIES.setPendingShutdown(False)
    pendingRestart   = PROPERTIES.setPendingRestart(False)

    def __init__(self):
        self.log('__init__')        
        self.jsonRPC           = JSONRPC(service=self)
        self.player            = Player(service=self)
        self.monitor           = Monitor(service=self)
        self.tasks             = Tasks(service=self)
                
        self.tasks.service     = self
        self.monitor.service   = self
        self.player.service    = self
        self.jsonRPC.service   = self
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def __playing(self) -> bool:
        if self.player.isPlaying() and not self.player.runWhilePlaying: return True
        return False
    
    
    def __shutdown(self, wait=1.0) -> bool:
        pendingShutdown = (self.monitor.waitForAbort(wait) | PROPERTIES.isPendingShutdown())
        if pendingShutdown != self.pendingShutdown:
            self.pendingShutdown = PROPERTIES.setPendingShutdown(pendingShutdown)
            self.log('__shutdown, pendingShutdown = %s, wait = %s'%(self.pendingShutdown,wait))
        return self.pendingShutdown
    
    
    def __restart(self) -> bool:
        pendingRestart = (self.pendingRestart | PROPERTIES.isPendingRestart())
        if pendingRestart != self.pendingRestart:
            self.pendingRestart = PROPERTIES.setPendingRestart(pendingRestart)
            self.log('__restart, pendingRestart = %s'%(self.pendingRestart))
        return self.pendingRestart
         

    def _interrupt(self) -> bool: #break
        pendingInterrupt = (self.pendingShutdown | self.pendingRestart | PROPERTIES.isInterruptActivity() | BUILTIN.isSettingsOpened())
        if pendingInterrupt != self.pendingInterrupt:
            self.pendingInterrupt = PROPERTIES.setPendingInterrupt(pendingInterrupt)
            self.log('_interrupt, pendingInterrupt = %s'%(self.pendingInterrupt))
        return self.pendingInterrupt
    

    def _suspend(self) -> bool: #continue
        pendingSuspend = (self.__playing() | PROPERTIES.isSuspendActivity() | BUILTIN.isScanning())
        if pendingSuspend != self.pendingSuspend:
            self.pendingSuspend = PROPERTIES.setPendingSuspend(pendingSuspend)
            self.log('_suspend, pendingSuspend = %s'%(self.pendingSuspend))
        return self.pendingSuspend
        
        
    def __tasks(self):
        self.tasks._chkEpochTimer('chkQueTimer',self.tasks._chkQueTimer,FIFTEEN)


    def _start(self):
        self.log('_start')
        if DIALOG.notificationWait('%s...'%(LANGUAGE(32054)),wait=OSD_TIMER):
            self.currentSettings = dict(SETTINGS.getCurrentSettings())
            self.tasks._initialize()
            if self.player.isPlaying() and self.player.overlay is None: self.player.onAVStarted()
            while not self.monitor.abortRequested():
                self.monitor.chkIdle()
                if    self.__shutdown(): break
                elif  self.__restart():  break
                else: self.__tasks()
            self._stop(self.pendingRestart)


    def _stop(self, pendingRestart: bool=False):
        if self.player.isPlaying(): self.player.onPlayBackStopped()
        with PROPERTIES.interruptActivity():
            for thread in thread_enumerate():
                if thread.name != "MainThread" and thread.is_alive():
                    if hasattr(thread, 'cancel'): thread.cancel()
                    try: thread.join(1.0)
                    except: pass
                    self.log('_stop, closing %s...'%(thread.name))
            
        if pendingRestart: 
            self.log('_stop, finished: restarting!')
            Service()._start()
        else: 
            self.log('_stop, finished: exiting!')
            sys.exit()