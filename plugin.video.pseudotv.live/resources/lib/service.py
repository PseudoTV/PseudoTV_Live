  # Copyright (C) 2022 Lunatixz


# This file is part of PseudoTV Live.

# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
from resources.lib.globals     import *
from resources.lib.overlay     import Overlay
from resources.lib.vault       import Vault
from resources.lib.parser      import Writer
from resources.lib.server      import Discovery, Announcement, HTTP

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.playingPVRitem    = {}
        self.isPseudoTV        = isPseudoTV()
        self.lastSubState      = isSubtitle()
        self.showOverlay       = SETTINGS.getSettingBool('Enable_Overlay')


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def getInfoTag(self):
        self.log('getInfoTag')
        if self.isPlayingAudio():
            return self.getMusicInfoTag()
        elif self.isPlayingVideo():
            return self.getVideoInfoTag()

    
    def getPlayingFile(self):
        self.log('getPlayingFile')
        try:    return self.getPlayingFile()
        except: return ''

        
    def getPlayerTime(self):
        self.log('getPlayerTime')
        try:    return self.getTotalTime()
        except: return 0


    def getPVRTime(self):
        self.log('getPVRTime')
        try:    return (sum(x*y for x, y in zip(map(float, xbmc.getInfoLabel('PVR.EpgEventElapsedTime(hh:mm:ss)').split(':')[::-1]), (1, 60, 3600, 86400))))
        except: return 0


    def getPVRitem(self):
        try:    pvritem = self.getPlayingItem().getProperty('pvritem') #Kodi v20. todo
        except: pvritem = self.myService.writer.jsonRPC.getPlayerItem(self.playingPVRitem.get('isPlaylist',False)).get('customproperties',{}).get('pvritem',{})
        self.log('getPVRitem, pvritem = %s'%(pvritem))
        if isinstance(pvritem,list): pvritem = pvritem[0] #playlists return list
        return loadJSON(pvritem)
        
        
    def getCitem(self):
        self.log('getCitem')
        self.playingPVRitem.update(self.getPVRitem())
        return self.playingPVRitem.get('citem',{})
        
        
    def getCallback(self):
        self.playingPVRitem.update(self.getPVRitem())
        callback = 'pvr://channels/tv/All%20channels/pvr.iptvsimple_{id}.pvr'.format(id=self.playingPVRitem.get('uniqueid',-1))
        self.log('getCallback, callback = %s'%(callback))
        return callback


    def setSeekTime(self, seek):
        if not self.isPlaying: return
        self.log('setSeekTime, seek = %s'%(seek))
        self.seekTime(seek)
        
        
    def setSubtitles(self, state):
        self.log('setSubtitles, state = %s'%(state))
        if (state and not hasSubtitle()): return
        elif self.isPseudoTV: self.showSubtitles(state)

        
        """ Player() Trigger Order
        Player: onPlayBackStarted
        Player: onAVChange (if playing)
        Player: onAVStarted
        Player: onPlayBackSeek (if seek)
        Player: onAVChange (if seek)
        Player: onPlayBackError
        Player: onPlayBackEnded
        Player: onPlayBackStopped
        """
    
    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        self.isPseudoTV = isPseudoTV()
        self.playAction()
        

    def onAVChange(self):
        self.log('onAVChange')
        self.isPseudoTV = isPseudoTV()
        
        
    def onAVStarted(self):
        self.log('onAVStarted')
        self.isPseudoTV = isPseudoTV()
        self.setSubtitles(self.lastSubState)


    def onPlayBackSeek(self, seek_time=None, seek_offset=None): #Kodi bug? `OnPlayBackSeek` no longer called by player during seek, limited to pvr?
        self.log('onPlayBackSeek, seek_time = %s, seek_offset = %s'%(seek_time,seek_offset))
        
        
    def onPlayBackError(self):
        self.log('onPlayBackError')
        self.stopAction()

        
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        self.changeAction()
        

    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        self.stopAction()
        
        
    def playAction(self):
        self.isPseudoTV = isPseudoTV()
        pvritem = self.getPVRitem()
        if not pvritem or not self.isPseudoTV: 
            self.log('playAction, returning missing pvritem or not PseudoTV!')
            return self.stopAction()
            
        self.showOverlay = SETTINGS.getSettingBool('Enable_Overlay')
        setLegacyPseudoTV(True)# legacy setting to disable/enable support in third-party applications. 
        if not pvritem.get('callback') or pvritem.get('callback','').endswith(('-1.pvr','None.pvr')):
            pvritem['callback'] = self.getCallback()
            self.log('playAction, updating callback to = %s'%(pvritem['callback']))

        if pvritem.get('channelid',-1) == self.playingPVRitem.get('channelid',random.random()):
            self.log('playAction, no channel change')
            self.playingPVRitem = pvritem
        else:   
            self.log('playAction, channel changed')
            self.playingPVRitem = pvritem
            citem   = self.getCitem()
            pvritem = self.myService.writer.rules.runActions(RULES_ACTION_PLAYER, citem, pvritem, inherited=self)
            #temp workaround for long existing kodi subtitle seek bug. Some movie formats don't properly seek when subtitles are enabled.
            self.lastSubState = isSubtitle()
            if self.lastSubState: self.setSubtitles(False)
        self.log('playAction, finished; isPlaylist = %s'%(self.playingPVRitem.get('isPlaylist',False)))
        
                
    def updatePVRItem(self, pvritem=None):
        if pvritem is None: pvritem = self.playingPVRitem
        return self.myService.writer.jsonRPC.getPVRposition(pvritem.get('name'), pvritem.get('id'), pvritem.get('isPlaylist'))
        # (self.myService.writer.jsonRPC.matchPVRPath(pvritem.get('channelid',-1)) or self.myService.writer.jsonRPC.getPlayerItem().get('mediapath',''))})


    def changeAction(self):
        if not self.playingPVRitem: 
            self.log('changeAction, returning pvritem not found.')
            return self.stopAction()
        
        if self.playingPVRitem.get('isPlaylist',False):
            self.log('changeAction, playing playlist')
            #todo pop broadcastnext? keep pvritem in sync with playlist pos?
        else:
            self.isPseudoTV = False
            xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
            callback = self.playingPVRitem.get('callback','')
            self.log('changeAction, playing = %s'%(callback))
            xbmc.executebuiltin('PlayMedia(%s)'%callback)


    def stopAction(self):
        self.log('stopAction')
        self.isPseudoTV = False
        self.toggleOverlay(False)
        if self.playingPVRitem.get('isPlaylist',False):
            xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
        self.playingPVRitem = {}
        setLegacyPseudoTV(False)
        
        
    def toggleOverlay(self, state):
        overlayWindow = Overlay(OVERLAY_FLE, ADDON_PATH, "default", service=self.myService)
        if state and not isOverlay():
            conditions = [self.showOverlay,self.isPlaying(),self.isPseudoTV]
            self.log("toggleOverlay, conditions = %s"%(conditions))
            if False in conditions: return
            self.log("toggleOverlay, show")
            overlayWindow.show()
        elif not state and isOverlay():
            self.log("toggleOverlay, close")
            overlayWindow.close()
            del overlayWindow

        
    def triggerSleep(self):
        conditions = [not isPaused(),self.isPlaying(),self.isPseudoTV]
        self.log("triggerSleep, conditions = %s"%(conditions))
        if False in conditions: return
        if self.sleepTimer():
            self.stop()
            return True
        
        
    def sleepTimer(self):
        self.log('sleepTimer')
        sec = 0
        cnx = False
        inc = int(100/OVERLAY_DELAY)
        dia = self.myService.writer.dialog.progressDialog(message=LANGUAGE(30281))
        while not self.myService.monitor.abortRequested() and (sec < OVERLAY_DELAY):
            sec += 1
            msg = '%s\n%s'%(LANGUAGE(30283),LANGUAGE(30284)%((OVERLAY_DELAY-sec)))
            dia = self.myService.writer.dialog.progressDialog((inc*sec),dia, msg)
            if self.myService.monitor.waitForAbort(1) or not dia:
                cnx = True
                break
        self.myService.writer.dialog.progressDialog(100,dia)
        return not bool(cnx)

        
class Monitor(xbmc.Monitor):    
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.lastSettings        = getPTV_SETTINGS()
        self.pendingChange       = False
        self.pendingChangeThread = threading.Timer(30.0, self._onSettingsChanged)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def chkIdle(self):
        isIdle,idleTime = getIdle()
        sleepTime = SETTINGS.getSettingInt('Idle_Timer')
        if self.myService.player.isPseudoTV:
            if sleepTime > 0 and (idleTime > (sleepTime * 10800)): #3hr increments
                if self.myService.player.triggerSleep(): return
            
            if idleTime > OVERLAY_DELAY:
                self.myService.player.toggleOverlay(True)
            else: 
                self.myService.player.toggleOverlay(False)
        return isIdle


    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def onSettingsChanged(self):
        self.log('onSettingsChanged')
        if self.pendingChangeThread.is_alive(): 
            try: 
                self.pendingChangeThread.cancel()
                self.pendingChangeThread.join()
            except: pass
                
        self.pendingChangeThread = threading.Timer(15.0, self._onSettingsChanged)
        self.pendingChangeThread.name = "pendingChangeThread"
        self.pendingChangeThread.start()
                
                
    def _onSettingsChanged(self):
        self.log('_onSettingsChanged')
        lastSettings    = self.lastSettings.copy()
        currentSettings = getPTV_SETTINGS()
        self.lastSettings = currentSettings
        if chkSettings(lastSettings,currentSettings):
            self.myService.writer.dialog.notificationDialog(LANGUAGE(30356))
            return setRestartRequired()
                    
                    
    def isSettingsOpened(self):
        state = (isSettingDialog() | isSelectDialog() | isManagerRunning())
        if state: self.log('isSettingsOpened = %s'%state)
        return state

  
class Service:
    isFirstRun   = True
    vault        = Vault()
    monitor      = Monitor()
    player       = Player()
    http         = HTTP()
    announcement = Announcement(monitor)
    discovery    = Discovery(monitor)
    
    def __init__(self):
        self.writer            = Writer(service=self)
        self.player.myService  = self
        self.monitor.myService = self
        
        if self._initialize():
            self._startup()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

        
    def openChannelManager(self, chnum=1):
        self.log('openChannelManager, chnum = %s'%(chnum))
        with busy():
            from resources.lib.manager import Manager
            chmanager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default",writer=self.writer,channel=chnum)
            del chmanager


    def chkBackup(self):
        return self.writer.backup.hasBackup()


    def chkUtilites(self):
        ctl   = (0,1)
        param = doUtilities()
        if not param: return False
        self.log('chkUtilites, doUtilities = %s'%(param))
        try:
            if param.startswith('Channel_Manager'):
                ctl = (0,1)
                self.openChannelManager()
            elif  param == 'Clear_Userdefined':
                return self.writer.clearUserChannels()
            elif  param == 'Clear_Predefined':
                ctl = (1,12)
                self.writer.clearPredefined()
            elif  param == 'Clear_BlackList':
                ctl = (1,12)
                self.writer.clearBlackList()
            elif  param == 'Backup_Channels':
                ctl = (0,4)
                self.writer.backup.backupChannels()
            elif  param == 'Recover_Channels':
                ctl = (0,5)
                self.writer.backup.recoverChannels()
            else:
                self.writer.selectPredefined(param.replace('_',' '))
                try:    ctl = (1,CTL_PARAMS[param])
                except: ctl = (1,1)
        except Exception as e: log("chkUtilites, Failed! %s"%(e), xbmc.LOGERROR)
        return openAddonSettings(ctl)
        
                       
    def chkUpdatePending(self):
        if not (isBusy() | isClient()) and hasLibraryRun():
            hasChannels = len(self.writer.channels.getChannels()) > 0
            if hasChannels:
                self.isFirstRun = False
                conditions = [validateFiles(),
                              isUpdatePending(),
                              chkUpdateTime('Last_Update',UPDATE_OFFSET)]
                self.log('chkUpdatePending, conditions = %s'%(conditions))
                if True in conditions:
                    with busy():
                        if self.writer.builder.buildService():
                            brutePVR(override=True)
            elif self.isFirstRun:
                setAutotuned(self.writer.autoTune())
            
            
    def _initialize(self):
        dia   = self.writer.dialog.progressBGDialog(message='%s...'%(LANGUAGE(30052)))
        funcs = [chkVersion,chkDiscovery,initFolders,setInstanceID,self.chkBackup,chkResources,chkRequiredSettings,updateIPTVManager]
        for idx, func in enumerate(funcs):
            dia = self.writer.dialog.progressBGDialog(int((idx+1)*100//len(funcs)),dia,'%s...'%(LANGUAGE(30052)))
            self.chkUtilites()
            func()
        return True


    def _restart(self):
        self.log('_restart')
        self.http._stop()
        self.writer.dialog.notificationWait(LANGUAGE(30311)%(ADDON_NAME))     
        self.__init__()
        
        
    def _tasks(self):
        self.http._start()
        chkDiscovery(getDiscovery())
        
              
    def _startup(self, waitForAbort=5, waitForStartup=15):
        self.log('_startup')
        pendingStop    = isShutdownRequired()
        pendingRestart = isRestartRequired()
        
        while not self.monitor.abortRequested() and waitForStartup > 0: #15s startup delay w/utility check.
            self.chkUtilites()
            waitForStartup -= 1
            if self.monitor.waitForAbort(1):
                self._shutdown()
        
        while not self.monitor.abortRequested():
            self._tasks()
            
            isIdle         = self.monitor.chkIdle()
            pendingStop    = isShutdownRequired()
            pendingRestart = isRestartRequired()
            
            if   (self.monitor.waitForAbort(waitForAbort) or pendingStop or pendingRestart): break
            elif (self.monitor.isSettingsOpened() or self.chkUtilites()): continue
            elif isIdle: 
                self.chkUpdatePending()
            
        if pendingRestart: 
            self._restart()
        else:              
            self._shutdown()
              
          
    def _shutdown(self):
        self.http._stop()
        self.discovery._stop()
        self.announcement._stop()
        for thread in threading.enumerate():
            try: 
                if thread.name == "MainThread": continue
                self.log("_shutdown joining thread %s"%(thread.name))
                try: 
                    thread.cancel()
                    thread.join(1.0)
                except: pass
            except Exception as e: log("closeThreads, Failed! %s"%(e), xbmc.LOGERROR)
        self.log('_shutdown finished, exiting %s...'%(ADDON_NAME))

if __name__ == '__main__': Service()
    
    