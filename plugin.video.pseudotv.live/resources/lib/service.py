#   Copyright (C) 2022 Lunatixz
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
from overlay    import Overlay, Background
from rules      import RulesList
from tasks      import Tasks
from threading  import enumerate as thread_enumerate

class Player(xbmc.Player):
    pvritem      = {}
    background   = None
    myService    = False
    pendingPlay  = False
    isPseudoTV   = False
    lastSubState = False
    rules        = RulesList()
    runActions   = rules.runActions
    
    def __init__(self):
        self.log('__init__')
        xbmc.Player.__init__(self)
        
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
        self.pendingPlay = True
        

    def onAVChange(self):
        self.log('onAVChange')
        self.lastSubState = isSubtitle()
            
        
    def onAVStarted(self):
        self.pendingPlay = False
        self.pvritem     = self.getPlayerPVRitem()
        self.isPseudoTV  = self.isPseudoTVPlaying()
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
        self.pvritem     = {}
        self.isPseudoTV  = False
        self.pendingPlay = False
        
        
    def isPseudoTVPlaying(self):
        if self.pvritem.get('channelid'): return True
        elif self.pvritem.get('citem',{}).get('id'): return True
        else: return False
        
        
    def getPlayerPVRitem(self):
        pvritem = loadJSON((self.getPlayingItem().getProperty('pvritem') or '{"citem":{}}')) #Kodi v20.
        self.log('getPlayerPVRitem, pvritem = %s'%(pvritem))
        return pvritem
        
        
    def getPlayerCitem(self):
        try:
            citem = loadJSON(self.getPlayerPVRitem().getProperty('citem')) #Kodi v20.
            if not citem: raise Exception('getPlayerCitem, trying writer')
        except: citem = decodeWriter(BUILTIN.getInfoLabel('Writer','VideoPlayer')).get('citem',{})
        self.log('getPlayerCitem, citem = %s'%(citem))
        return citem
        
        
    def getCallback(self):
        # self.playingPVRitem.update(self.getPVRitem())
        # callback = 'pvr://channels/tv/All%20channels/{pvr}_{id}.pvr'.format(pvr=PVR_CLIENT_ID,id=self.playingPVRitem.get('uniqueid',-1))
        callback = BUILTIN.getInfoLabel('Filenameandpath','Player')
        self.log('getCallback, callback = %s\n%s\n%s'%(callback,BUILTIN.getInfoLabel('Folderpath','Player'),BUILTIN.getInfoLabel('Filename','Player')))
        return callback
        
        
    def getPlayerFile(self):
        try:    return self.getPlayingFile()
        except: return ''


    def getPlayerTime(self):
        try:    return self.getTotalTime()
        except: return 0
                
                
    def getPlayerProgress(self):
        try:    return float(BUILTIN.getInfoLabel('Player.Progress'))
        except: return 0.0


    def getElapsedTime(self):
        try:    return int(self.getTime() // 1000)
        except: return 0


    def getTimeRemaining(self, prop='TimeRemaining'): #prop='EpgEventElapsedTime'
        return kodiLabel2Seconds(BUILTIN.getInfoLabel('%s(hh:mm:ss)'%(prop),'Player'))


    def setSubtitles(self, state):
        hasSubtitle = hasSubtitle()
        self.log('setSubtitles, state = %s, hasSubtitle = %s'%(state,hasSubtitle))
        if not hasSubtitle: state = False
        self.showSubtitles(state)

   
    def _onPlay(self):
        self.log('_onPlay')
        self.toggleBackground(False)
        BUILTIN.executebuiltin('ReplaceWindow(fullscreenvideo)')
        if self.pvritem.get('citem',{}).get('id') != self.pvritem.get('citem',{}).get('id',random.random()): #playing new channel
            self.pvritem = self.runActions(RULES_ACTION_PLAYER_START, self.pvritem.get('citem'), self.pvritem, inherited=self)
            self.setSubtitles(self.lastSubState) #todo allow rules to set sub preference per channel. 
        if not self.pvritem.get('callback'): self.pvritem['callback'] = self.getCallback()

        
    def _onChange(self):
        self.log('_onChange, channelid = %s,'%(self.pvritem.get("channelid",'')))
        self.toggleBackground(True)
        if not self.pvritem: self._onStop()
        else:
            try:
                if self.pvritem.get('isPlaylist',False):
                    broadcastnext = self.pvritem['broadcastnext']
                    self.pvritem['broadcastnow']  = broadcastnext.pop(0)
                    self.pvritem['broadcastnext'] = broadcastnext
                    self.log('_onChange, isPlaylist = %s, broadcastnext = %s'%(self.pvritem.get('isPlaylist'), len(self.pvritem['broadcastnext'])))
                    if len(broadcastnext) == 0: raise Exception('Empty broadcastnext')
                else: raise Exception('Using callback')
                # JSONRPC().playerOpen('{"item":{"channelid":%s}}'%(self.pvritem["channelid"])) #slower than playmedia
                # JSONRPC().playerOpen('{"item":{"broadcastid":%s}}'%(self.pvritem['broadcastnow']["broadcastid"])) #calls catchup vod
            except Exception as e:
                self.runActions(RULES_ACTION_PLAYER_STOP, self.pvritem.get('citem',{}), inherited=self)
                self.log('_onChange, callback = %s: %s'%(self.pvritem.get('callback'),e))
                BUILTIN.executebuiltin('PlayMedia(%s)'%(self.pvritem.get('callback')))
        
        
    def _onStop(self):
        self.log('_onStop')
        self.toggleBackground(False)
        self.runActions(RULES_ACTION_PLAYER_STOP, self.pvritem.get('citem',{}), inherited=self)
        PROPERTIES.clearEXTProperty('%s.lastNOWITEM'%(ADDON_ID))
        if self.pvritem.get('isPlaylist',False): xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()


    def _onError(self, pvritem):
        self.log('_onError, playing file = %s'%(self.getPlayerFile()))
        self.onPlayBackStopped()
        
        
    def toggleBackground(self, state=True):
        self.log('toggleBackground, state = %s'%(state))
        if state and self.background is None:
            self.background = Background("%s.background.xml"%(ADDON_ID), ADDON_PATH, "default", player=self, runActions=self.runActions)
            self.background.show()
        elif not state and hasattr(self.background, 'close'):
            self.background.close()
            self.background = None
            if self.isPlaying():
                BUILTIN.executebuiltin('ActivateWindow(fullscreenvideo)')
                    

class Monitor(xbmc.Monitor):
    isIdle   = False
    idleTime = 0
    overlay  = None
    
    
    def __init__(self):
        self.log('__init__')
        xbmc.Monitor.__init__(self)
        self.pendingSuspend   = False
        self.pendingInterrupt = False
        
        self.sleepTime = (SETTINGS.getSettingInt('Idle_Timer') or 0)
        self.enableOverlay = (SETTINGS.getSettingBool('Enable_Overlay') or True)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getIdle(self):
        try: idleTime = (int(xbmc.getGlobalIdleTime()) or 0)
        except: #Kodi raises error after sleep.
            self.log('getIdleTime, Kodi waking up from sleep...')
            idleTime = 0
        idleState = (idleTime > OVERLAY_DELAY)
        if (idleTime == 0 or idleTime <= 5): self.log("getIdle, idleState = %s, idleTime = %s"%(idleState,idleTime))
        return idleState, idleTime


    def chkIdle(self):
        self.isIdle, self.idleTime = self.getIdle()
        if self.myService.player.isPseudoTV: 
            if self.sleepTime > 0 and (self.idleTime > (self.sleepTime * 10800)): #3hr increments
                if self.triggerSleep(): return False
            if self.isIdle: self.toggleOverlay(True)
            else:           self.toggleOverlay(False)
        return self.isIdle
        
        
    def toggleOverlay(self, state):
        self.log("toggleOverlay, state = %s"%(state))
        if state and self.overlay is None:
            conditions = self.enableOverlay & self.myService.player.isPlaying() & self.myService.player.isPseudoTV
            if conditions:
                self.overlay = Overlay(player=self.myService.player, runActions=self.myService.player.runActions)
                self.overlay.open()
        elif not state and hasattr(self.overlay, 'close'):
            self.overlay.close()
            self.overlay = None


    def triggerSleep(self):
        conditions = not isPaused() & self.myService.player.isPlaying() & self.myService.player.isPseudoTV
        self.log("triggerSleep, conditions = %s"%(conditions))
        if not conditions: return
        if self.sleepTimer():
            self.myService.player.stop()
            return True
        
        
    def sleepTimer(self):
        self.log('sleepTimer')
        sec = 0
        cnx = False
        inc = int(100/OVERLAY_DELAY)
        playSFX(NOTE_WAV)
        dia = DIALOG.progressDialog(message=LANGUAGE(30078))
        while not self.abortRequested() and (sec < OVERLAY_DELAY):
            sec += 1
            msg = '%s\n%s'%(LANGUAGE(32039),LANGUAGE(32040)%((OVERLAY_DELAY-sec)))
            dia = DIALOG.progressDialog((inc*sec),dia, msg)
            if self.waitForAbort(1) or dia is None:
                cnx = True
                break
        DIALOG.progressDialog(100,dia)
        return not bool(cnx)

        
    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def isSettingsOpened(self):
        isSettingDialog = (PROPERTIES.getPropertyBool('addonsettings') or BUILTIN.getInfoBool('IsVisible(addonsettings)','Window'))
        isSelectDialog  = (PROPERTIES.getPropertyBool('selectdialog')  or BUILTIN.getInfoBool('IsVisible(selectdialog)' ,'Window'))
        state = (isSettingDialog | isSelectDialog)
        self.log("isSettingsOpened, state = %s"%(state))
        return state

  
    def onSettingsChanged(self):
        self.log('onSettingsChanged')
        timerit(self.onSettingsChangedTimer)(15.0)
        
        
    def onSettingsChangedTimer(self):
        self.log('onSettingsChangedTimer')
        self.myService._que(self.myService.monitor._onSettingsChanged,1)
                
                
    def _onSettingsChanged(self):
        self.log('_onSettingsChanged')
        self.myService.currentChannels = self.myService.tasks.chkChannelChange(self.myService.currentChannels)  #check for channel change, rebuild if needed.
        self.myService.currentSettings = self.myService.tasks.chkSettingsChange(self.myService.currentSettings) #check for settings change, take action if needed.


class Service():
    setClient(isClient())
    currentChannels = []
    currentSettings = []
    
    queue    = PriorityQueue()
    player   = Player()
    monitor  = Monitor()
    tasks    = Tasks()
    
    def __init__(self):
        self.log('__init__')
        DIALOG.notificationWait(LANGUAGE(32054),wait=OVERLAY_DELAY)#startup delay; give Kodi PVR time to initialize. 
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _interrupt(self, wait=.001) -> bool: #break
        self.monitor.pendingInterrupt = (self.monitor.pendingInterrupt | self.monitor.waitForAbort(wait) | self._restart())
        self.log('_interrupt, pendingInterrupt = %s'%(self.monitor.pendingInterrupt))
        return self.monitor.pendingInterrupt


    def _suspend(self) -> bool: #continue
        self.monitor.pendingSuspend = (self.monitor.isSettingsOpened() | isPendingSuspend())
        self.log('_suspend, pendingSuspend = %s'%(self.monitor.pendingSuspend))
        return self.monitor.pendingSuspend


    def _restart(self) -> bool:
        return isPendingRestart()
         
         
    def _playing(self) -> bool:
        if self.player.isPlaying() and not SETTINGS.getSettingBool('Run_While_Playing'): return True
        return False
    
         
    def _run(self):
        self.monitor.chkIdle()
   
        
    def _tasks(self):
        self.tasks.chkQueTimer()
        self._queue()
        
        
    def _queue(self):
        try:
            priority, randomheap, package = self.queue.get(block=False)
            try:
                func, args, kwargs = package
                self.log("_queue, priority = %s, func = %s"%(priority,func.__name__))
                func(*args,**kwargs)
            except Exception as e:
                self.log("_queue, func = %s failed! %s"%(func.__name__,e), xbmc.LOGERROR)
        except Empty: self.log("_queue, empty!")


    def _que(self, func, priority=3, *args, **kwargs):
        try:  # priority 1 Highest, 5 Lowest
            self.queue.put((self.queue.qsize()+priority, random.random(), (func, args, kwargs)), block=False)
            self.log('_que, func = %s, args = %s, kwargs = %s' % (func.__name__, args, kwargs))
        except TypeError: pass
        except Exception as e:
            self.log("_que, failed! %s" % (e), xbmc.LOGERROR)


    def _initialize(self):
        self.log('_initialize')
        if self.player.isPlaying(): self.player.onAVStarted() #if playback already in-progress run onAVStarted tasks.
        self.currentSettings = dict(SETTINGS.getCurrentSettings()) #startup settings
        self.player.myService  = self
        self.monitor.myService = self
        self.tasks.myService   = self
        self.tasks._startProcess()
        
        
    def start(self):
        self.log('start')
        self._initialize()
        while not self.monitor.abortRequested():
            self._run()
            if    self._interrupt(wait=1): break
            elif  self._suspend(): continue
            else: self._tasks()
        self.stop()


    def stop(self):
        for thread in thread_enumerate():
            try: 
                if thread.name != "MainThread":
                    try: 
                        thread.cancel()
                        thread.join(1.0)
                        self.log("_stop, joining thread %s"%(thread.name))
                    except: pass
            except Exception as e: log("_start, failed! %s"%(e), xbmc.LOGERROR)
        self.log('_stop, finished, exiting %s...'%(ADDON_NAME))
        if self._restart(): Service().start()

  
if __name__ == '__main__': Service().start()