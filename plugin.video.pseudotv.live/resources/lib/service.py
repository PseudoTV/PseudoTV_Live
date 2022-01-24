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
from resources.lib.parser      import Writer

class Player(xbmc.Player):
    
    def __init__(self):
        self.log('__init__')
        xbmc.Player.__init__(self)
        self.ruleList        = {}
        self.playingPVRitem  = {}
        self.isPseudoTV      = isPseudoTV()
        self.lastSubState    = isSubtitle()
        self.showOverlay     = SETTINGS.getSettingBool('Enable_Overlay')
        
        """
        ##Player() trigger order##
        Player: onPlayBackStarted
        Player: onAVChange (if playing)
        Player: onAVStarted
        Player: onPlayBackSeek (if seek)
        Player: onAVChange (if seek)
        Player: onPlayBackError
        Player: onPlayBackEnded
        Player: onPlayBackStopped
        """
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def runActions(self, action, citem, parameter=None):
        self.log("runActions action = %s, channel = %s"%(action,citem))
        if citem.get('id',''):
            ruleList = self.ruleList.get(citem['id'],[])
            for rule in ruleList:
                if action in rule.actions:
                    self.log("runActions performing channel rule: %s"%(rule.name))
                    return rule.runAction(action, self, parameter)
        return parameter
        
        
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


    def getPlayerItem(self):
        self.log('getPlayerItem')
        try:    return self.getPlayingItem() #Kodi v20. todo
        except: return self.myService.writer.jsonRPC.getPlayerItem(self.playingPVRitem.get('isPlaylist',False))
        

    def getPVRitem(self):
        self.log('getPVRitem')
        playerItem = self.getPlayerItem()
        if isinstance(playerItem,list): playerItem = playerItem[0] #playlists return list
        return (loadJSON(playerItem.get('customproperties',{}).get('pvritem',{})))
        
        
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

        
    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        self.playAction()
        

    def onAVChange(self):
        self.log('onAVChange')
        
        
    def onAVStarted(self):
        self.log('onAVStarted')
        self.setSubtitles(self.lastSubState)


    def onPlayBackSeek(self, seek_time=None, seek_offset=None): #Kodi bug? `OnPlayBackSeek` no longer called by player during seek, limited to pvr?
        self.log('onPlayBackSeek, seek_time = %s, seek_offset = %s'%(seek_time,seek_offset))
        
        
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        self.changeAction()
        

    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        self.stopAction()
        
        
    def onPlayBackError(self):
        self.log('onPlayBackError')
        self.stopAction()
        
        
    def playAction(self):
        self.isPseudoTV = isPseudoTV()
        pvritem = self.getPVRitem()
        if not pvritem or not self.isPseudoTV: 
            self.log('playAction, returning missing pvritem or not PseudoTV!')
            return self.stopAction()
            
        self.showOverlay  = SETTINGS.getSettingBool('Enable_Overlay')
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
            citem = self.getCitem()
            self.ruleList = self.myService.writer.rules.loadRules([citem])
            pvritem = self.runActions(RULES_ACTION_PLAYER, citem, pvritem)
            
            #temp workaround for long existing kodi subtitle seek bug. Some movies formats don't properly seek when subtitles are enabled.
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
            # xbmc.executebuiltin("Action(SkipNext)")
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
        conditions = [not xbmc.getCondVisibility('Player.Paused'),self.isPlaying(),self.isPseudoTV]
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
        self.log('__init__')
        xbmc.Monitor.__init__(self)
        self.lastSettings   = {}
        self.lastTime       = None
        
        self.onChangeThread = threading.Timer(30.0, self.onChange)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def isSettingsOpened(self):
        return (isSettingDialog() | isSelectDialog() | isManagerRunning())


    def onSettingsChanged(self, wait=30.0):
        ## Egg Timer, reset on each call.
        if self.onChangeThread.is_alive(): 
            try: 
                self.onChangeThread.cancel()
                self.onChangeThread.join()
            except: pass
        self.onChangeThread = threading.Timer(wait, self.onChange)
        self.onChangeThread.name = "onChangeThread"
        self.onChangeThread.start()
        
        
    def onChange(self):
        if isBusy(): return self.onSettingsChanged(15.0) #try again later
        elif self.isSettingsOpened(): return #changes still occurring.
        self.log('onChange')
        with busy():
            if self.hasSettingsChanged():
                self.myService.writer.setPendingChangeTimer()
            
            
    def chkPluginSettings(self):
        self.log('chkPluginSettings')
        for func in [chkPVR, chkMGR]: func()
        return True
        
        
    def chkSettings(self):
        self.log('chkSettings')
        PROPERTIES.setPropertyInt('Idle_Timer',SETTINGS.getSettingInt('Idle_Timer'))
        PROPERTIES.setPropertyBool('isClient',SETTINGS.getSettingBool('Enable_Client'))
        SETTINGS.setSettingInt('Min_Days',(self.myService.writer.jsonRPC.getSettingValue('epg.pastdaystodisplay')   or SETTINGS.getSetting('Min_Days')))
        SETTINGS.setSettingInt('Max_Days',(self.myService.writer.jsonRPC.getSettingValue('epg.futuredaystodisplay') or SETTINGS.getSetting('Max_Days')))
        #priority settings that trigger chkUpdate on change.
        #todo chk resource addon installed after change:
        # ['Resource_Logos','Resource_Ratings','Resource_Bumpers','Resource_Commericals','Resource_Trailers']
        #todo proxy changes between ptvl and kodi pvr (past/future days) settings.
        return {'User_Import'         :{'setting':SETTINGS.getSetting('User_Import')         ,'action':None},
                'Enable_Client'       :{'setting':SETTINGS.getSetting('Enable_Client')       ,'action':setRestartRequired},
                'Import_M3U_TYPE'     :{'setting':SETTINGS.getSetting('Import_M3U_TYPE')     ,'action':None},
                'Import_M3U_FILE'     :{'setting':SETTINGS.getSetting('Import_M3U_FILE')     ,'action':None},
                'Import_M3U_URL'      :{'setting':SETTINGS.getSetting('Import_M3U_URL')      ,'action':None},
                'Import_Provider'     :{'setting':SETTINGS.getSetting('Import_Provider')     ,'action':None},
                'User_Folder'         :{'setting':SETTINGS.getSetting('User_Folder')         ,'action':moveUser},
                'Select_Channels'     :{'setting':SETTINGS.getSetting('Select_Channels')     ,'action':None},
                'Select_TV_Networks'  :{'setting':SETTINGS.getSetting('Select_TV_Networks')  ,'action':None},
                'Select_TV_Shows'     :{'setting':SETTINGS.getSetting('Select_TV_Shows')     ,'action':None},
                'Select_TV_Genres'    :{'setting':SETTINGS.getSetting('Select_TV_Genres')    ,'action':None},
                'Select_Movie_Genres' :{'setting':SETTINGS.getSetting('Select_Movie_Genres') ,'action':None},
                'Select_Movie_Studios':{'setting':SETTINGS.getSetting('Select_Movie_Studios'),'action':None},
                'Select_Mixed_Genres' :{'setting':SETTINGS.getSetting('Select_Mixed_Genres') ,'action':None},
                'Select_Mixed'        :{'setting':SETTINGS.getSetting('Select_Mixed')        ,'action':None},
                'Select_Music_Genres' :{'setting':SETTINGS.getSetting('Select_Music_Genres') ,'action':None},
                'Select_Recommended'  :{'setting':SETTINGS.getSetting('Select_Recommended')  ,'action':None},
                'Select_Imports'      :{'setting':SETTINGS.getSetting('Select_Imports')      ,'action':None},
                'Min_Days'            :{'setting':SETTINGS.getSetting('Min_Days')            ,'action':None},
                'Max_Days'            :{'setting':SETTINGS.getSetting('Max_Days')            ,'action':None}}
        
        
    def hasSettingsChanged(self): 
        #todo detect userfolder change, moveuser, add previous value to property?
        #todo copy userfolder to new location
        currentSettings = self.chkSettings()
        if not self.lastSettings:
            self.lastSettings = currentSettings
            self.log('hasSettingsChanged, lastSettings not found returning')
            return False
            
        # differences = dict(diffDICT(self.lastSettings,currentSettings))
        differences = None
        if differences: 
            self.chkPluginSettings()
            self.log('hasSettingsChanged, differences = %s'%(differences))
            self.lastSettings = currentSettings
            for key in differences.keys():
                func   = currentSettings[key].get('action',None)
                args   = currentSettings[key].get('args'  ,tuple)
                kwargs = currentSettings[key].get('kwargs',dict)
                try: func(*args,**kwargs)
                except Exception as e: 
                    if func: self.log("hasSettingsChanged, Failed! %s"%(e), xbmc.LOGERROR)
            return True
            
        if self.lastSettings != currentSettings:
            self.log('hasSettingsChanged, lazy pendingChange')
            return True #temp trigger, fix difference detect...
        
        
class Service:
    def __init__(self):
        self.log('__init__')
        self.monitor           = Monitor()
        self.player            = Player()
        self.writer            = Writer(service=self)
        self.player.myService  = self
        self.monitor.myService = self
        
        self.startThread       = threading.Timer(1.0, hasVersionChanged)
        self.serviceThread     = threading.Timer(0.5, self.runServiceThread)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

        
    def openChannelManager(self, chnum=1):
        self.log('openChannelManager, chnum = %s'%(chnum))
        with busy():
            from resources.lib.manager import Manager
            chmanager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default",writer=self.writer,channel=chnum)
            del chmanager
            self.writer.setPendingChangeTimer()
        
        
    def startServiceThread(self, wait=30.0):
        self.log('startServiceThread, wait = %s'%(wait))
        if self.serviceThread.is_alive(): 
            try: 
                self.serviceThread.cancel()
                self.serviceThread.join()
            except: pass
        self.serviceThread = threading.Timer(wait, self.runServiceThread)
        self.serviceThread.name = "serviceThread"
        self.serviceThread.start()
        
                
    def runServiceThread(self):
        if   isBusy() or self.monitor.isSettingsOpened(): return self.startServiceThread()
        elif isClient(): return self.startServiceThread(600.0) #wait and call again if isClient changes.
        self.log('runServiceThread')
        self.writer.triggerPendingChange()
        return self.startServiceThread(UPDATE_WAIT)


    def chkVersion(self):
        # call in thread so prompt does not hold up service.
        if self.startThread.is_alive():
            try: 
                self.startThread.cancel()
                self.startThread.join()
            except: pass
        self.startThread = threading.Timer(1.0, hasVersionChanged)
        self.startThread.name = "startThread"
        self.startThread.start()


    def chkChannels(self):
        self.log('chkChannels')
        # check channels.json for changes
        # re-enable missing library.json items from channels.json
        
        
    def chkRecommended(self, lastUpdate=None):
        if not isClient() and chkUpdateTime('Last_Recommended',RECOMMENDED_OFFSET,lastUpdate):
            self.log('chkRecommended, lastUpdate = %s'%(lastUpdate))
            self.writer.library.recommended.importPrompt()

            
    def chkPredefined(self, lastUpdate=None):
        if not isClient():
            self.log('chkPredefined, lastUpdate = %s'%(lastUpdate))
            self.chkRecommended(lastUpdate=0)#Force Check with lastUpdate=0
            self.writer.library.fillLibraryItems()

        
    def chkTime(self, lastTime=None): #todo func. to catch daylight savings and correct Kodi PVR Time.
        return False
        # with busy():
            # nowTime = time.time()
            # if lastTime is None: lastTime = nowTime
            # timeDiff = (nowTime - lastTime)
            # self.monitor.lastTime = nowTime
            # if timeDiff > (TIME_CHECK) or timeDiff < 0: 
                # return brutePVR(True)
        
        
    def chkIdle(self):
        idleTime  = getIdleTime()
        sleepTime = PROPERTIES.getPropertyInt('Idle_Timer')
        if isPseudoTV() and sleepTime > 0 and idleTime > (sleepTime * 10800): #3hr increments
            if self.player.triggerSleep(): return
        
        if  idleTime > OVERLAY_DELAY:
            self.player.toggleOverlay(True)
        else:
            self.player.toggleOverlay(False)


    def chkUpdate(self, lastUpdate=None):
        if (isBusy() | self.monitor.isSettingsOpened() | isClient()): 
            return False
        
        with busy():
            conditions = [isPendingChange(),
                          chkUpdateTime('Last_Update',UPDATE_OFFSET,lastUpdate),
                          not FileAccess.exists(getUserFilePath(M3UFLE)),
                          not FileAccess.exists(getUserFilePath(XMLTVFLE)),
                          not FileAccess.exists(getUserFilePath(CHANNELFLE)),
                          not FileAccess.exists(getUserFilePath(LIBRARYFLE))]
            
            if True in conditions:
                self.log('chkUpdate, lastUpdate = %s, conditions = %s'%(lastUpdate,conditions))
                if isPendingChange(): setPendingChange(False)
                updateIPTVManager()
                self.chkPredefined()
                
                channels = self.writer.channels.getChannels()
                if not channels:
                    if self.writer.autoTune(): #autotune
                        return self.chkUpdate(0) #force rebuild after autotune
                    self.log('chkUpdate, no channels found & autotuned recently')
                    return False #skip autotune if performed recently.
                    
                if self.writer.builder.buildService():
                    self.log('chkUpdate, update finished')
                    brutePVR(override=True)
                    


    def chkUtilites(self):
        param = doUtilities()
        if not param: return
        self.log('chkLibraryItems, doUtilities = %s'%(param))
        if param.startswith('Channel_Manager'):
            self.openChannelManager()
        elif  param == 'Clear_Userdefined':
            return self.writer.clearUserChannels()
        elif  param == 'Clear_Predefined':
            return self.writer.clearPredefined()
        elif  param == 'Clear_BlackList':
            return self.writer.clearBlackList()
        elif  param == 'Backup_Channels':
            self.writer.backup.backupChannels()
        elif  param == 'Recover_Channels':
            return self.writer.backup.recoverChannels()
        else:
            self.writer.selectPredefined(param.replace('_',' '))
        openAddonSettings()
            
    def initialize(self):
        self.monitor.lastSettings = self.monitor.chkSettings()
        with busy():
            funcs = [setInstanceID,
                     initDirs,
                     self.chkVersion,
                     self.monitor.chkPluginSettings,
                     chkResources,
                     self.writer.backup.hasBackup,
                     self.chkChannels]
            for func in funcs: func()
            return True

         
    def run(self):
        self.log('run')
        doRestart = False
        setBusy(False) #reset value on 1st run.
        self.monitor.waitForAbort(5) # startup delay
        
        if self.initialize():
            self.writer.dialog.notificationProgress('%s...'%(LANGUAGE(30052)),wait=5)
            self.startServiceThread()
        else:
            self.writer.dialog.notificationProgress('%s...'%(LANGUAGE(30100)),wait=5)
        
        while not self.monitor.abortRequested():
            isMaster  = not isClient()
            doRestart = isRestartRequired()
            setSelectDialog(getSelectDialog())
            setSettingDialog(getSettingDialog())
                        
            if   self.writer.dialog.chkInfoMonitor():       continue # aggressive polling required (bypass waitForAbort)!
            elif doRestart or self.monitor.waitForAbort(5): break
                
            if   self.player.isPlaying(): self.chkIdle()
            elif isMaster:                self.chkRecommended()
                   
            self.chkUtilites()
            self.chkTime(self.monitor.lastTime)
               
            if   isBusy() or self.monitor.isSettingsOpened(): continue
            elif isMaster: self.chkUpdate()
                
        self.closeThreads()
        if doRestart:
            self.log('run, restarting buildService')
            Service().run()
            
                
    def closeThreads(self):
        for thread in threading.enumerate():
            try: 
                if thread.name == "MainThread": continue
                self.log("closeThreads joining thread %s"%(thread.name))
                try: 
                    thread.cancel()
                    thread.join(1.0)
                except: log("closeThreads, %s Failed! %s"%(thread.name,e), xbmc.LOGERROR)
            except Exception as e: log("closeThreads, Failed! %s"%(e), xbmc.LOGERROR)
        self.log('closeThreads finished, exiting %s...'%(ADDON_NAME))
     
        
if __name__ == '__main__': Service().run()