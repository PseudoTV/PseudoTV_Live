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
from overlay    import Overlay, Restart, Background
from rules      import RulesList
from tasks      import Tasks
from jsonrpc    import JSONRPC


class Player(xbmc.Player):
    sysInfo      = {}
    isPseudoTV   = False
    pendingStop  = False
    pendingPlay  = -1
    lastSubState = False
    restart      = None
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
        self.log('__init__')
        xbmc.Player.__init__(self)
        self.service           = service
        self.jsonRPC           = service.jsonRPC
        self.enableOverlay     = SETTINGS.getSettingBool('Overlay_Enable')
        self.infoOnChange      = SETTINGS.getSettingBool('Enable_OnInfo')
        self.disableTrakt      = SETTINGS.getSettingBool('Disable_Trakt')
        self.rollbackPlaycount = SETTINGS.getSettingBool('Rollback_Watched')
        self.saveDuration      = SETTINGS.getSettingBool('Store_Duration')
        self.sleepTime         = SETTINGS.getSettingInt('Idle_Timer')
        self.restartPercentage = SETTINGS.getSettingInt('Restart_Percentage')
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onPlayBackStarted(self):
        self.pendingStop = True
        self.pendingPlay = time.time()
        self.log('onPlayBackStarted, pendingStop = %s, pendingPlay = %s'%(self.pendingStop,self.pendingPlay))
        

    def onAVChange(self):
        self.lastSubState = BUILTIN.isSubtitle()
        self.isPseudoTV   = self.isPseudoTVPlaying()
        self.log('onAVChange, pendingStop = %s, isPseudoTV = %s'%(self.pendingStop,self.isPseudoTV))
        self.service.monitor.chkIdle()
        if self.isPseudoTV: self._onChange(self.sysInfo.get('isPlaylist',False),True)
        else:               self._onStop()

        
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
        if self.isPseudoTV: self._onError()
        self.isPseudoTV = False
        
        
    def onPlayBackEnded(self):
        self.pendingStop = False
        self.pendingPlay = -1
        self.log('onPlayBackEnded, pendingStop = %s, isPseudoTV = %s'%(self.pendingStop,self.isPseudoTV))
        self.service.monitor.toggleBackground()
        if self.isPseudoTV: self._onChange(self.sysInfo.get('isPlaylist',False))
        
        
    def onPlayBackStopped(self):
        self.pendingStop = False
        self.pendingPlay = -1
        self.log('onPlayBackStopped, pendingStop = %s, isPseudoTV = %s'%(self.pendingStop,self.isPseudoTV))
        if self.isPseudoTV: self._onStop()
        self.isPseudoTV = False
        
        
    def isPseudoTVPlaying(self):
        chid  = loadJSON(decodeString(self.getPlayerItem().getProperty('sysInfo'))).get('chid','')
        state = '@%s'%(slugify(ADDON_NAME)) in chid
        self.log('isPseudoTVPlaying = %s, id = %s'%(state,chid))
        return state
        
        
    def getChannelItem(self, id):
        self.log('getChannelItem, id = %s'%(id))
        for citem in self.service.currentChannels:
            if citem.get('id',random.random()) == id: return citem
        return {}
        
        
    def getPlayerSysInfo(self):
        sysInfo = loadJSON(decodeString(self.getPlayerItem().getProperty('sysInfo')))
        sysInfo['chfile']   = BUILTIN.getInfoLabel('Filename','Player')
        sysInfo['chfolder'] = BUILTIN.getInfoLabel('Folderpath','Player')
        sysInfo['chpath']   = BUILTIN.getInfoLabel('Filenameandpath','Player')
        if not sysInfo.get('fitem'): sysInfo.update({'fitem':decodePlot(BUILTIN.getInfoLabel('Plot','VideoPlayer'))})
        if not sysInfo.get('nitem'): sysInfo.update({'nitem':decodePlot(BUILTIN.getInfoLabel('NextPlot','VideoPlayer'))})
        sysInfo.update({'citem':combineDicts(sysInfo.get('citem',{}),self.getChannelItem(sysInfo.get('citem',{}).get('id'))),'runtime':int(self.getPlayerTime())})
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
        try:    return self.getTotalTime()
        except: return (self.sysInfo.get('fitem',{}).get('runtime') or -1)
            
            
    def getRemainingTime(self):
        try:    return self.getTotalTime() - self.getTime()
        except: return -1

       
    def getPlayedTime(self):
        try:    return self.getTime()
        except: return -1
       
       
    def getPlayerProgress(self):
        try:    return int((self.getRemainingTime() / self.getPlayerTime()) * 100)
        except: return int((BUILTIN.getInfoLabel('Progress','Player') or '-1'))


    def getTimeLabel(self, prop: str='TimeRemaining') -> int and float: #prop='EpgEventElapsedTime'
        if self.isPlaying(): return timeString2Seconds(BUILTIN.getInfoLabel('%s(hh:mm:ss)'%(prop),'Player'))
        else:                return -1


    def setTrakt(self, state: bool=SETTINGS.getSettingBool('Disable_Trakt')):
        self.log('setTrakt, state = %s'%(state))
        # https://github.com/trakt/script.trakt/blob/d45f1363c49c3e1e83dabacb70729cc3dec6a815/resources/lib/kodiUtilities.py#L104
        if state: PROPERTIES.setEXTPropertyBool('script.trakt.paused',state)
        else:     PROPERTIES.clrEXTProperty('script.trakt.paused')


    def setSubtitles(self, state: bool=True):
        hasSubtitle = BUILTIN.hasSubtitle()
        self.log('setSubtitles, state = %s, hasSubtitle = %s'%(state,hasSubtitle))
        if not hasSubtitle: state = False
        self.showSubtitles(state)


    def setPlaycount(self, state: bool=SETTINGS.getSettingBool('Rollback_Watched'), fitem: dict={}):
        self.log('setPlaycount, state = %s, file = %s, playcount = %s'%(state,fitem.get('file'),fitem.get('playcount',0)))
        if state: self.jsonRPC.quePlaycount(fitem)


    def setRuntime(self, state: bool=SETTINGS.getSettingBool('Store_Duration'), fitem: dict={}, runtime=0):
        self.log('setRuntime, state = %s, file = %s, runtime = %s'%(state,fitem.get('file'),runtime))
        if not fitem.get('file','').startswith(tuple(VFS_TYPES)): self.jsonRPC._setRuntime(fitem, int(runtime), state)
        

    def _onPlay(self):
        oldInfo = self.sysInfo
        sysInfo = self.getPlayerSysInfo() #get current sysInfo
        #items that only run once per channel change. ie. set adv. rules and variables. 
        self.log('_onPlay, [%s], mode = %s, chid = %s, isPlaylist = %s'%(sysInfo.get('citem',{}).get('id'),sysInfo.get('mode'),sysInfo.get('chid'),sysInfo.get('isPlaylist',False)))
        if sysInfo.get('chid') == oldInfo.get('chid',random.random()):#New Program
            self.sysInfo = sysInfo
            self.toggleInfo(self.infoOnChange)
            self.service.monitor.toggleBackground(False)
        else: #New channel
            self.sysInfo = self.runActions(RULES_ACTION_PLAYER_START, self.sysInfo.get('citem',{}), sysInfo, inherited=self)
            self.setRuntime(self.saveDuration,self.sysInfo.get('fitem',{}),self.sysInfo.get('runtime'))
            self.setSubtitles(self.lastSubState) #todo allow rules to set sub preference per channel.
            self.setTrakt(self.disableTrakt)
            self.toggleRestart(bool(self.restartPercentage))
            
            if self.sysInfo.get('radio',False): timerit(BUILTIN.executebuiltin)(0.5,['ReplaceWindow(visualisation)'])
            else:                               timerit(BUILTIN.executebuiltin)(0.5,['ReplaceWindow(fullscreenvideo)'])
                
                
    def _onChange(self, isPlaylist=False, onAVChange=False):
        oldInfo = self.sysInfo
        self.log('_onChange, [%s], isPlaylist = %s, callback = %s'%(oldInfo.get('citem',{}).get('id'),oldInfo.get('isPlaylist'),oldInfo.get('callback')))
        if isPlaylist:
            while not self.service.monitor.abortRequested() and self.isPlaying():
                sysInfo = self.getPlayerSysInfo()
                if   sysInfo.get('fitem'): break
                elif self.monitor.waitForAbort(0.001): break
                self.log('_onChange, [%s], waiting for getPlayerSysInfo refresh'%(oldInfo.get('citem',{}).get('id')))
                
            if oldInfo.get('fitem',{}).get('label') != sysInfo.get('fitem',{}).get('label',str(random.random())):
                self.toggleInfo(False)
                self.toggleRestart(False)
                self.setPlaycount(self.rollbackPlaycount,oldInfo.get('fitem',{}))
                self.setRuntime(self.saveDuration,sysInfo.get('fitem',{}),sysInfo.get('runtime'))
                self.sysInfo = self.runActions(RULES_ACTION_PLAYER_CHANGE, sysInfo.get('citem',{}), sysInfo, inherited=self)
                self.toggleInfo(self.infoOnChange)
                return
                
        elif onAVChange: return
        elif oldInfo.get('callback'):
            self.toggleInfo(False)
            self.toggleRestart(False)
            self.setPlaycount(self.rollbackPlaycount,oldInfo.get('fitem',{}))
            threadit(BUILTIN.executebuiltin)('PlayMedia(%s)'%(oldInfo['callback']))
        else: self._onStop()
    
        
    def _onStop(self):
        self.log('_onStop, id = %s'%(self.sysInfo.get('citem',{}).get('id')))
        self.setTrakt(False)
        self.toggleInfo(False)
        self.toggleRestart(False)
        self.service.monitor.toggleBackground(False)
        self.service.monitor.toggleOverlay(False)
        self.setPlaycount(self.rollbackPlaycount,self.sysInfo.get('fitem',{}))
        if self.sysInfo.get('isPlaylist'): xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
        self.sysInfo = self.runActions(RULES_ACTION_PLAYER_STOP, self.sysInfo.get('citem',{}), {}, inherited=self)
        

    def _onError(self): #todo evaluate potential for error handling.
        self.log('_onError, playing file = %s'%(self.getPlayerFile()))
        if REAL_SETTINGS.getSetting('Debug_Enable').lower() == 'true':
            DIALOG.notificationDialog(LANGUAGE(32000))
            timerit(BUILTIN.executebuiltin)(0.5,['Number(0)'])
            self.stop()
            
    
    def toggleInfo(self, state: bool=True):
        if state and self.service.player.enableOverlay:
            if not BUILTIN.getInfoLabel('Genre','VideoPlayer') in FILLER_TYPE:
                self.log('toggleInfo, state = %s'%(state))
                timerit(self.toggleInfo)(float(OSD_TIMER),[False])
                BUILTIN.executebuiltin('ActivateWindow(fullscreeninfo)')
        elif not state and BUILTIN.getInfoBool('IsVisible(fullscreeninfo)','Window'):
            self.log('toggleInfo, state = %s'%(state))
            BUILTIN.executebuiltin('Action(back)')  

                 
    def toggleRestart(self, state: bool=True):
        if state and self.service.player.enableOverlay and not BUILTIN.getInfoLabel('Genre','VideoPlayer') in FILLER_TYPE:
            progress = self.getPlayerProgress()
            seekTHD = SETTINGS.getSettingInt('Seek_Threshold')
            self.log('toggleRestart, state = %s, progress = %s, restartPercentage = %s, seekTHD = %s'%(state,progress,self.restartPercentage,seekTHD))
            if not PROPERTIES.isRunning('OVERLAY_RESTART') and (progress >= self.restartPercentage and progress < seekTHD) and self.sysInfo.get('fitem'):
                self.restart = Restart(RESTART_XML, ADDON_PATH, "default", "1080i", player=self)
                self.restart.doModal()
        elif not state and hasattr(self.restart,'onClose'):
            self.log("toggleRestart, state = %s"%(state))
            self.restart = self.restart.onClose()


class Monitor(xbmc.Monitor):
    idleTime   = 0
    isIdle     = False
    overlay    = None
    background = None
    
    def __init__(self, service=None):
        self.log('__init__')
        xbmc.Monitor.__init__(self)
        self.service = service
        self.jsonRPC = service.jsonRPC
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def chkIdle(self):
        def __chkIdle():
            try: self.idleTime = BUILTIN.getIdle()
            except: #Kodi raises error after sleep.
                self.log('__chkIdle, Kodi waking up from sleep...')
                self.idleTime = 0
            self.isIdle = (self.idleTime > OSD_TIMER)
            if SETTINGS.getSettingBool('Debug_Enable'): self.log('__chkIdle, isIdle = %s, idleTime = %s'%(self.isIdle, self.idleTime))

        def __chkPlayback():
            if self.service.player.isPseudoTV and self.service.player.isPlaying() and self.service.player.pendingPlay > 0:
                pendingTime = (time.time() - self.service.player.pendingPlay)
                if not BUILTIN.isBusyDialog() and pendingTime > 60:
                    self.log('__chkPlayback, pendingPlay Error (%s)\nsysInfo = %s'%(pendingTime,self.service.player.sysInfo))
                    self.service.player.onPlayBackError()

        def __chkResumeTime():
            if self.service.player.isPseudoTV and self.service.player.isPlaying() and self.service.player.sysInfo.get('isPlaylist',False):
                file = self.service.player.getPlayingFile()
                if self.service.player.sysInfo.get('fitem',{}).get('file') == file:
                    self.service.player.sysInfo.setdefault('resume',{}).update({"position":self.service.player.getTime(),"total":self.service.player.getPlayerTime(),"file":file})
                    self.log('__chkResumeTime, resume = %s'%(self.service.player.sysInfo['resume']))

        def __chkSleepTimer():
            if self.service.player.isPseudoTV and self.service.player.isPlaying() and self.service.player.sleepTime > 0 and (self.idleTime > (self.service.player.sleepTime * 10800)):
                self.log('__chkSleepTimer, sleepTime = %s'%(self.service.player.sleepTime))
                self.triggerSleep()
        
        def __chkBackground():
            if self.service.player.isPseudoTV and self.service.player.isPlaying() and round(self.service.player.getRemainingTime()) < 5:
                self.toggleBackground()
        
        def __chkOverlay():
            if self.service.player.isPseudoTV and self.service.player.isPlaying() and self.isIdle: self.toggleOverlay(self.service.player.enableOverlay)
            elif self.overlay:                                                                     self.toggleOverlay(False)
        
        __chkIdle()
        __chkPlayback()
        __chkBackground()
        __chkResumeTime()
        __chkSleepTimer()
        __chkOverlay()


    def toggleOverlay(self, state: bool=True):
        if state and self.overlay is None:
            self.log("toggleOverlay, state = %s"%(state))
            self.overlay = Overlay(jsonRPC=self.jsonRPC,player=self.service.player)
            self.overlay.open()
        elif not state and hasattr(self.overlay, 'close'):
            self.log("toggleOverlay, state = %s"%(state))
            self.overlay = self.overlay.close()
            
            
    def toggleBackground(self, state: bool=True):
        if state and self.background is None:
            self.log("toggleOverlay, state = %s"%(state))
            self.background = Background(BACKGROUND_XML, ADDON_PATH, "default", player=self.service.player)
            self.background.show()
        elif not state and hasattr(self.background,'onClose'):
            self.log("toggleOverlay, state = %s"%(state))
            self.background = self.background.onClose()


    def triggerSleep(self):
        if not PROPERTIES.isRunning('triggerSleep'):
            with PROPERTIES.chkRunning('triggerSleep'):
                if self.sleepTimer():
                    self.service.player.stop()
                    return True
        
        
    def sleepTimer(self):
        self.log('sleepTimer')
        sec = 0
        cnx = False
        inc = int(100/FIFTEEN)
        timerit(xbmc.playSFX)(0.5,[NOTE_WAV])
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
        self.service.currentChannels = self.service.tasks.chkChannelChange(self.service.currentChannels)  #check for channel change, rebuild if needed
        self.service.currentSettings = self.service.tasks.chkSettingsChange(self.service.currentSettings) #check for settings change, take action if needed
        

class Service():
    currentChannels  = []
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
        
        self.currentChannels   = self.tasks.getChannels()
        self.currentSettings   = dict(SETTINGS.getCurrentSettings())
        self.runWhilePlaying   = SETTINGS.getSettingBool('Run_While_Playing')
        
        self.jsonRPC.service   = self
        self.player.service    = self
        self.monitor.service   = self
        self.tasks.service     = self
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def __playing(self) -> bool:
        if self.player.isPlaying() and not self.runWhilePlaying: return True
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
           
                
    def __initialize(self):
        self.log('__initialize')
        if self.player.isPlaying(): self.player.onAVStarted()
        self.tasks._initialize()
        

    def _start(self):
        self.log('_start')
        self.__initialize()
        while not self.monitor.abortRequested():
            self.monitor.chkIdle()
            if    self.__shutdown(): break
            elif  self.__restart(): break
            else: self.__tasks()
        self._stop()


    def _stop(self):
        with PROPERTIES.interruptActivity():
            for thread in thread_enumerate():
                if thread.name != "MainThread" and thread.is_alive():
                    if hasattr(thread, 'cancel'): thread.cancel()
                    try: thread.join(1.0)
                    except: pass
                    self.log('_stop, closing %s...'%(thread.name))
            
        if self.pendingRestart: 
            self.log('_stop, finished: restarting!')
            Service()._start()
        else: 
            self.log('_stop, finished: exiting!')
            sys.exit()

if __name__ == '__main__': Service()._start()