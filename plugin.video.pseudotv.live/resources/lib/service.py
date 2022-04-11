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
from resources.lib.vault       import Vault
from resources.lib.parser      import Writer
from resources.lib.overlay     import Overlay
from resources.lib.server      import Discovery, Announcement, HTTP

class Player(xbmc.Player):
    def __init__(self, service=None):
        xbmc.Player.__init__(self)
        self.service        = service
        self.playingFile    = ''
        self.playingPVRitem = {}
        self.isPseudoTV     = isPseudoTV()
        self.lastSubState   = isSubtitle()
        self.showOverlay    = SETTINGS.getSettingBool('Enable_Overlay')
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def getInfoTag(self):
        self.log('getInfoTag')
        if self.isPlayingAudio():   return self.getMusicInfoTag()
        elif self.isPlayingVideo(): return self.getVideoInfoTag()

              
    def getPlayerLabel(self):
        return (xbmc.getInfoLabel('Player.Title') or xbmc.getInfoLabel('Player.Label') or '')
           
           
    def getPlayerFile(self):
        try:    return self.getPlayingFile()
        except: return self.playingPVRitem.get('broadcastnow',{}).get('playing','')
        
        
    def getPlayerTime(self):
        try:    return self.getTotalTime()
        except: return 0
                
                
    def getPlayerProgress(self):
        try:    return float(xbmc.getInfoLabel('Player.Progress'))
        except: return 0.0


    def getElapsedTime(self):
        try:    return int(self.getTime() // 1000)
        except: return 0


    def getTimeRemaining(self):
        try:    return int(sum(x*y for x, y in zip(map(float, xbmc.getInfoLabel('Player.TimeRemaining(hh:mm:ss)').split(':')[::-1]), (1, 60, 3600, 86400))))
        except: return 0
   
   
    def getPVRTime(self):
        try:    return (sum(x*y for x, y in zip(map(float, xbmc.getInfoLabel('PVR.EpgEventElapsedTime(hh:mm:ss)').split(':')[::-1]), (1, 60, 3600, 86400))))
        except: return 0


    def getPVRitem(self):
        try:    pvritem = self.getPlayingItem().getProperty('pvritem') #Kodi v20.
        except: pvritem = self.service.writer.jsonRPC.getPlayerItem(self.playingPVRitem.get('isPlaylist',False)).get('customproperties',{}).get('pvritem',{})
        self.log('getPVRitem, pvritem = %s'%(pvritem))
        if isinstance(pvritem,list): pvritem = pvritem[0] #playlists return list
        return loadJSON(pvritem)
        
                
    def updatePVRItem(self, pvritem=None):
        if pvritem is None: pvritem = self.getPVRitem()
        return self.service.writer.jsonRPC.getPVRposition(pvritem.get('name'), pvritem.get('id'), pvritem.get('isPlaylist'))
        
        
    def getPVRPath(self, pvritem=None):
        if pvritem is None: pvritem = self.getPVRitem()
        try:    return self.service.writer.jsonRPC.matchPVRPath(pvritem.get('channelid',-1))
        except: return self.service.writer.jsonRPC.getPlayerItem(pvritem.get('isPlaylist',False)).get('mediapath','')


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
        self.playAction()
        

    def onAVChange(self):
        self.log('onAVChange')
        self.isPseudoTV  = isPseudoTV()
        self.playingFile = self.getPlayerFile()
            
        
    def onAVStarted(self):
        self.log('onAVStarted')
        self.isPseudoTV = isPseudoTV()
        if not self.isPseudoTV:
            self.toggleOverlay(False)
        else:
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
            self.log('playAction, No Channel Change')
            self.playingPVRitem = pvritem
        else:   
            self.log('playAction, New Channel Started')
            self.lastSubState = isSubtitle()
            citem = self.getCitem()
            pvritem.get('citem',{}).update(citem)
            self.playingPVRitem = self.service.writer.rules.runActions(RULES_ACTION_PLAYER_START, citem, pvritem, inherited=self)
            if self.lastSubState: self.setSubtitles(False) #temp workaround for long existing kodi subtitle seek bug. Some movie formats don't properly seek when subtitles are enabled.

        self.playingFile = self.getPlayerFile()
        self.log('playAction, finished; isPlaylist = %s, isStack = %s'%(self.playingPVRitem.get('isPlaylist',False),self.playingPVRitem.get('broadcastnow',{}).get('isStack',False)))


    def changeAction(self):
        if not self.playingPVRitem: 
            self.log('changeAction, returning pvritem not found.')
            return self.stopAction()
        
        if self.playingPVRitem.get('isPlaylist',False):
            if self.playingPVRitem.get('broadcastnow',{}).get('isStack',False):
                self.log('changeAction, playing stack playlist')
                path = popStack(self.playingPVRitem.get('broadcastnow',{}).get('playing'))
                self.playingPVRitem['broadcastnow']['isStack'] = isStack(path)
                self.playingPVRitem['broadcastnow']['playing'] = path
            else:
                self.log('changeAction, playing playlist')
                broadcastnext = self.playingPVRitem['broadcastnext']
                self.playingPVRitem['broadcastnow']  = broadcastnext.pop(0)
                self.playingPVRitem['broadcastnext'] = broadcastnext
            return
            
        if not self.isPseudoTV: return
        self.isPseudoTV = False
        xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
        self.service.writer.rules.runActions(RULES_ACTION_PLAYER_STOP, self.playingPVRitem.get('citem',{}), inherited=self)
        callback = self.playingPVRitem.get('callback','')
        self.log('changeAction, playing callback = %s'%(callback))
        xbmc.executebuiltin('PlayMedia(%s)'%callback)


    def stopAction(self):
        self.log('stopAction')
        self.isPseudoTV = False
        self.toggleOverlay(False)
        self.service.writer.rules.runActions(RULES_ACTION_PLAYER_STOP, self.playingPVRitem.get('citem',{}), inherited=self)
        if self.playingPVRitem.get('isPlaylist',False):
            xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
        self.playingPVRitem = {}
        setLegacyPseudoTV(False)
        
        
    def toggleOverlay(self, state):
        if state and not isOverlay():
            conditions = [self.showOverlay,self.isPlaying(),self.isPseudoTV]
            self.log("toggleOverlay, state = %s, conditions = %s"%(state,conditions))
            if False in conditions: return
            self.service.overlayWindow.open()
        elif not state and isOverlay():
            self.log("toggleOverlay, state = %s"%(state))
            self.service.overlayWindow.close()

        
    def triggerSleep(self):
        conditions = [not isPaused(),self.isPlaying(),isPseudoTV()]
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
        dia = self.service.writer.dialog.progressDialog(message=LANGUAGE(30281))
        while not self.service.monitor.abortRequested() and (sec < OVERLAY_DELAY):
            sec += 1
            msg = '%s\n%s'%(LANGUAGE(30283),LANGUAGE(30284)%((OVERLAY_DELAY-sec)))
            dia = self.service.writer.dialog.progressDialog((inc*sec),dia, msg)
            if self.service.monitor.waitForAbort(1) or not dia:
                cnx = True
                break
        self.service.writer.dialog.progressDialog(100,dia)
        return not bool(cnx)

        
class Monitor(xbmc.Monitor):
    
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.lastSettings        = getPTV_SETTINGS()
        self.pendingChange       = False
        self.shutdown            = False
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def chkIdle(self):
        isIdle,idleTime = getIdle()
        sleepTime = SETTINGS.getSettingInt('Idle_Timer')
        if isPseudoTV():
            if sleepTime > 0 and (idleTime > (sleepTime * 10800)): #3hr increments
                if self.myService.player.triggerSleep(): return False
        
            if idleTime > OVERLAY_DELAY:
                self.myService.player.toggleOverlay(True)
            else:
                self.myService.player.toggleOverlay(False)
        return isIdle


    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def onSettingsChanged(self):
        self.log('onSettingsChanged')
        timerit(self._onSettingsChanged)(15.0)
                
                
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
    isLocked      = False
    isFirstRun    = True
    vault         = Vault()
    monitor       = Monitor()
    http          = HTTP(monitor)
    announcement  = Announcement(monitor)
    discovery     = Discovery(monitor)
    
    def __init__(self):
        self.player            = Player(service=self)
        self.writer            = Writer(service=self)
        self.overlayWindow     = Overlay(player=self.player)
        self.monitor.myService = self
        
        self.player.onPlayBackStarted()
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
        if not (isBusy() | isClient() | self.isLocked) and hasLibraryRun():
            self.isLocked = True
            hasChannels = len(self.writer.channels.getChannels()) > 0
            if hasChannels:
                self.isFirstRun = False
                conditions = [validateFiles(),
                              isUpdatePending(),
                              chkUpdateTime('Last_Update',UPDATE_OFFSET)]
                if True in conditions:
                    self.log('chkUpdatePending, conditions = %s'%(conditions))
                    with busy():
                        if self.writer.builder.buildService():
                            brutePVR(override=True)
            elif self.isFirstRun:
                setAutotuned(self.writer.autoTune())
            self.isLocked = False

 
    def _initialize(self):
        dia   = self.writer.dialog.progressBGDialog(message='%s...'%(LANGUAGE(30052)))#,chkResources
        funcs = [chkVersion,chkClient,initFolders,setInstanceID,self.chkBackup,chkRequiredSettings,updateIPTVManager]
        for idx, func in enumerate(funcs):
            dia = self.writer.dialog.progressBGDialog(int((idx)*100//len(funcs)),dia,'%s...'%(LANGUAGE(30052)))
            self.chkUtilites()
            try:    func()
            except: pass
        self.writer.dialog.progressBGDialog(100, dia)
        return True


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
            isIdle         = self.monitor.chkIdle()
            pendingStop    = isShutdownRequired()
            pendingRestart = isRestartRequired()
            
            if   (self.monitor.waitForAbort(waitForAbort) or pendingStop or pendingRestart): break
            elif (self.monitor.isSettingsOpened() or self.chkUtilites()): continue
            elif isIdle and not self.isLocked: self.chkUpdatePending()
                
        if pendingRestart: self._restart()
        else:              self._shutdown()
              
              
    def _restart(self):
        self._shutdown(restart=True)
        
        
    def _shutdown(self, restart=False):
        self.log('_shutdown, restart = %s'%(restart))
        del self.player
        del self.writer
        del self.overlayWindow
        if restart:
            self.writer.dialog.notificationWait(LANGUAGE(30311)%(ADDON_NAME))
            self.__init__()
        else:
            self.monitor.shutdown = True
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
    
    