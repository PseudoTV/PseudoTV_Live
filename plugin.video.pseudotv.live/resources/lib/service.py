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
from overlay    import Overlay, Background, Replay
from rules      import RulesList
from tasks      import Tasks
from jsonrpc    import JSONRPC

class Player(xbmc.Player):
    sysInfo      = {}
    replay       = None
    background   = None
    isPseudoTV   = False
    lastSubState = False
    isIdle       = False
    minDuration  = None
    accurateDuration = None
    rules        = RulesList()
    runActions   = rules.runActions
    
    
    def __init__(self, service=None):
        self.log('__init__')
        xbmc.Player.__init__(self)
        self.service           = service
        self.jsonRPC           = service.jsonRPC
        self.lastSubState      = BUILTIN.isSubtitle()
        self.disableTrakt      = SETTINGS.getSettingBool('Disable_Trakt')
        self.rollbackPlaycount = SETTINGS.getSettingBool('Rollback_Watched')
        self.restartPercentage = SETTINGS.getSettingInt('Restart_Percentage')
        self.saveDuration      = SETTINGS.getSettingBool('Store_Duration')
        
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
              
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        self.onAVChange()
        

    def onAVChange(self):
        self.log('onAVChange')
        self.isIdle = self.service.monitor.chkIdle()

        
    def onAVStarted(self):
        self.isPseudoTV = self.isPseudoTVPlaying()
        self.log('onAVStarted, isPseudoTV = %s'%(self.isPseudoTV))
        if self.isPseudoTV: self._onPlay()
        
        
    def onPlayBackSeek(self, seek_time=None, seek_offset=None): #Kodi bug? `OnPlayBackSeek` no longer called by player during seek, issue limited to pvr?
        self.log('onPlayBackSeek, seek_time = %s, seek_offset = %s'%(seek_time,seek_offset))
    
    
    def onPlayBackError(self):
        self.log('onPlayBackError')
        if self.isPseudoTV: self._onError()
        
        
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        if self.isPseudoTV: self._onChange()
        
        
    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        if self.isPseudoTV: self._onStop()
        
        
    def isPseudoTVPlaying(self):
        state = loadJSON(decodeString(self.getPlayerItem().getProperty('sysInfo'))).get('chid') != None
        self.log('isPseudoTVPlaying = %s'%(state))
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
        sysInfo.update({'citem':combineDicts(sysInfo.get('citem',{}),self.getChannelItem(sysInfo.get('citem',{}).get('id'))),'runtime' :int(self.getPlayerTime())})
        if not sysInfo.get('callback'): sysInfo['callback'] = self.jsonRPC.getCallback(sysInfo)
        PROPERTIES.setEXTProperty('%s.lastPlayed.sysInfo'%(ADDON_ID),encodeString(dumpJSON(sysInfo)))
        self.log('getPlayerSysInfo, sysInfo = %s'%(sysInfo))
        return sysInfo
        

    def getPlayerItem(self):
        try:    return self.getPlayingItem()
        except: return xbmcgui.ListItem()


    def getPlayerFile(self):
        try:    return self.getPlayingFile()
        except: return ''


    def getPlayerTime(self):
        try:    return self.getTotalTime()
        except: return 0
                
                
    def getPlayerProgress(self):
        try:    return int((self.getTimeLabel()*100)//self.getPlayerTime())
        except: return -1


    def getElapsedTime(self):
        try:    return int(self.getTime() // 1000)
        except: return -1


    def getTimeLabel(self, prop: str='TimeRemaining') -> int and float: #prop='EpgEventElapsedTime'
        return timeString2Seconds(BUILTIN.getInfoLabel('%s(hh:mm:ss)'%(prop),'Player'))


    def setTrakt(self, state: bool=SETTINGS.getSettingBool('Disable_Trakt')):
        self.log('setTrakt, state = %s'%(state))
        # https://github.com/trakt/script.trakt/blob/d45f1363c49c3e1e83dabacb70729cc3dec6a815/resources/lib/kodiUtilities.py#L104
        PROPERTIES.setEXTProperty('script.trakt.paused',str(state).lower())


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
        self.log('_onPlay')
        self.toggleReplay(False)
        self.toggleBackground(False)
        oldInfo = self.sysInfo
        self.sysInfo = self.getPlayerSysInfo() #get current sysInfo
        
        #items that only run once per channel change. ie. set adv. rules and variables. 
        if self.sysInfo.get('chid') != oldInfo.get('chid',random.random()): #playing new channel
            self.runActions(RULES_ACTION_PLAYER_START, self.sysInfo.get('citem',{}), inherited=self)
            self.setRuntime(self.saveDuration,self.sysInfo.get('fitem',{}),self.sysInfo.get('runtime'))
            self.setPlaycount(self.rollbackPlaycount,oldInfo.get('fitem',{}))
            self.setSubtitles(self.lastSubState) #todo allow rules to set sub preference per channel.
            self.toggleReplay()
            self.setTrakt(self.disableTrakt)
            

    def _onChange(self):
        self.log('_onChange')
        self.toggleReplay(False)
        self.toggleBackground()
        oldInfo = self.sysInfo
        
        if oldInfo.get('isPlaylist'):
            sysInfo = self.getPlayerSysInfo()
            if not sysInfo.get('fitem') and self.isPlaying(): return self.service.tasks._que(self._onChange,1)
            elif sysInfo.get('fitem',{}).get('label') == oldInfo.get('nitem',{}).get('label',str(random.random())):
                self.sysInfo = sysInfo
                self.log('_onChange, updated sysInfo')
                self.runActions(RULES_ACTION_PLAYER_CHANGE, self.sysInfo.get('citem',{}), inherited=self)
                self.setRuntime(self.saveDuration,self.sysInfo.get('fitem',{}),sysInfo.get('runtime'))
                self.setPlaycount(self.rollbackPlaycount,oldInfo.get('fitem',{}))
                return
        self.log('_onChange, callback = %s'%(oldInfo['callback']))
        threadit(BUILTIN.executebuiltin)('PlayMedia(%s)'%(oldInfo['callback']))
    
        
    def _onStop(self):
        self.log('_onStop')
        self.setTrakt(False)
        self.setPlaycount(self.rollbackPlaycount,self.sysInfo.get('fitem',{}))
        if self.sysInfo.get('isPlaylist'): xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
        self.runActions(RULES_ACTION_PLAYER_STOP, self.sysInfo.get('citem',{}), inherited=self)
        self.sysInfo = {}
        self.isPseudoTV = False
        self.toggleReplay(False)
        self.toggleBackground(False)


    def _onError(self):
        self.log('_onError, playing file = %s'%(self.getPlayerFile()))
        self.onPlayBackStopped()


    def toggleReplay(self, state: bool=True):
        self.log('toggleReplay, state = %s, restartPercentage = %s'%(state,self.restartPercentage))
        if state and self.service.monitor.enableOverlay and bool(self.restartPercentage) and not self.isIdle and self.sysInfo.get('fitem'):
            progress = self.getPlayerProgress()
            if (progress >= self.restartPercentage and progress < SETTINGS.getSettingInt('Seek_Threshold')):
                self.replay = Replay(RESTART_XML, ADDON_PATH, "default", "1080i", player=self)
                self.replay.doModal()
        elif hasattr(self.replay, 'close'): self.replay.close()
        
        
    def toggleBackground(self, state: bool=True):
        self.log('toggleBackground, state = %s'%(state))
        if state:
            if hasattr(self.background, 'show'): self.background.show()
        else:
            if hasattr(self.background, 'close'):
                self.background = self.background.close()
                if self.isPlaying(): BUILTIN.executebuiltin('ReplaceWindow(fullscreenvideo)')
            self.background = Background(BACKGROUND_XML, ADDON_PATH, "default", player=self)
            
            
class Monitor(xbmc.Monitor):
    idleTime   = 0
    isIdle     = False
    window     = None
    overlay    = None
    
    
    def __init__(self, service=None):
        self.log('__init__')
        xbmc.Monitor.__init__(self)
        self.service          = service
        self.jsonRPC          = service.jsonRPC
        self.pendingSuspend   = False
        self.pendingInterrupt = False
        self.sleepTime        = (SETTINGS.getSettingInt('Idle_Timer')      or 0)
        self.enableOverlay    = (SETTINGS.getSettingBool('Overlay_Enable') or True)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getIdle(self):
        try: idleTime = (int(xbmc.getGlobalIdleTime()) or 0)
        except: #Kodi raises error after sleep.
            self.log('getIdle, Kodi waking up from sleep...')
            idleTime = 0
        idleState = (idleTime > OVERLAY_DELAY)
        return idleState, idleTime


    def chkIdle(self):
        self.isIdle, self.idleTime = self.getIdle()
        if self.sleepTime > 0 and (self.idleTime > (self.sleepTime * 10800)): #3hr increments
            if self.triggerSleep(): return False
        if self.isIdle: self.toggleOverlay(True)
        else:           self.toggleOverlay(False)
        return self.isIdle
        

    def toggleOverlay(self, state: bool=True):
        if state:
            conditions = self.enableOverlay & self.service.player.isPlaying() & self.service.player.isPseudoTV
            if not self.overlay and conditions:
                self.log("toggleOverlay, state = %s"%(state))
                self.overlay = Overlay(jsonRPC=self.jsonRPC,player=self.service.player)
                self.overlay.open()
        else:
            if hasattr(self.overlay, 'close'): 
                self.log("toggleOverlay, state = %s"%(state))
                self.overlay.close()
            self.overlay = None


    def triggerSleep(self):
        if not BUILTIN.isPaused():
            conditions = self.service.player.isPlaying() & self.service.player.isPseudoTV
            self.log("triggerSleep, conditions = %s"%(conditions))
            if not conditions: return
            if self.sleepTimer():
                self.service.player.stop()
                return True
        
        
    def sleepTimer(self):
        self.log('sleepTimer')
        sec = 0
        cnx = False
        inc = int(100/EPOCH_TIMER)
        playSFX(NOTE_WAV)
        dia = DIALOG.progressDialog(message=LANGUAGE(30078))
        while not self.abortRequested() and (sec < EPOCH_TIMER):
            if self.service._interrupt(): break
            sec += 1
            msg = '%s\n%s'%(LANGUAGE(32039),LANGUAGE(32040)%((EPOCH_TIMER-sec)))
            dia = DIALOG.progressDialog((inc*sec),dia, msg)
            if self.waitForAbort(1.0) or dia is None:
                cnx = True
                break
        DIALOG.progressDialog(100,dia)
        return not bool(cnx)

        
    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def isSettingsOpened(self) -> bool:
        state = (BUILTIN.getInfoBool('IsVisible(addonsettings)','Window') | BUILTIN.getInfoBool('IsVisible(selectdialog)' ,'Window'))
        self.log("isSettingsOpened, state = %s"%(state))
        return state

  
    def onSettingsChanged(self):
        self.log('onSettingsChanged')
        if self.service: timerit(self.onSettingsChangedTimer)(15.0)
        
        
    def onSettingsChangedTimer(self):
        self.log('onSettingsChangedTimer') 
        self.service.tasks._que(self._onSettingsChanged,1)
                
                
    def _onSettingsChanged(self):
        self.log('_onSettingsChanged')
        self.service.currentChannels = self.service.tasks.chkChannelChange(self.service.currentChannels)  #check for channel change, rebuild if needed
        self.service.currentSettings = self.service.tasks.chkSettingsChange(self.service.currentSettings) #check for settings change, take action if needed


class Service():
    PROPERTIES.getInstanceID()
    SETTINGS.getMYUUID()
    currentChannels = []
    currentSettings = []

    def __init__(self):
        self.log('__init__')
        self.pendingRestart    = False
        self.jsonRPC           = JSONRPC()
        self.player            = Player(service=self)
        self.monitor           = Monitor(service=self)
        self.tasks             = Tasks(service=self)
        
        self.currentChannels   = self.tasks.getChannels()
        self.currentSettings   = dict(SETTINGS.getCurrentSettings())
        self.runWhilePlaying   = SETTINGS.getSettingBool('Run_While_Playing')
        
        self.player.service  = self
        self.monitor.service = self
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _interrupt(self, wait=.001) -> bool: #break
        self.monitor.pendingInterrupt = (self.monitor.pendingInterrupt | self.monitor.waitForAbort(wait) | self.__restart())
        self.log('_interrupt, pendingInterrupt = %s'%(self.monitor.pendingInterrupt))
        return self.monitor.pendingInterrupt


    def _suspend(self) -> bool: #continue
        isPendingSuspend = PROPERTIES.getEXTProperty('%s.pendingSuspend'%(ADDON_ID)) == 'true'
        self.monitor.pendingSuspend = (self.monitor.isSettingsOpened() | isPendingSuspend | self.__playing())
        self.log('_suspend, pendingSuspend = %s'%(self.monitor.pendingSuspend))
        return self.monitor.pendingSuspend


    def __restart(self) -> bool:
        self.pendingRestart = PROPERTIES.getEXTProperty('pendingRestart') == 'true'
        self.log('__restart, pendingRestart = %s'%(self.pendingRestart))
        return self.pendingRestart
         
         
    def __playing(self) -> bool:
        if self.player.isPlaying() and not self.runWhilePlaying: return True
        return False
    

    def __tasks(self):
        self.log('__tasks')
        self.tasks._que(self.monitor.chkIdle,1)
        self.tasks._chkEpochTimer('chkQueTimer',self.tasks._chkQueTimer,EPOCH_TIMER)
           
                
    def __initialize(self):
        self.log('__initialize')
        if self.player.isPlaying(): self.player.onAVStarted()
        self.tasks._initialize()
        

    def _start(self):
        self.log('_start')
        self.__initialize()
        while not self.monitor.abortRequested():
            if    self._interrupt(1): break
            else: self.__tasks()
        self._stop()


    def _stop(self):
        for thread in thread_enumerate():
            if thread.name != "MainThread" and thread.is_alive():
                try:
                    thread.cancel()
                    thread.join(1.0)
                except: pass
        self.log('_stop, finished, exiting %s...'%(ADDON_NAME))
        if self.pendingRestart: Service()._start()

if __name__ == '__main__': Service()._start()