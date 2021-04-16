  # Copyright (C) 2020 Lunatixz


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
from resources.lib.builder     import Builder
from resources.lib.config      import Config
from resources.lib.cache       import Cache
from resources.lib.concurrency import PoolHelper
from resources.lib.rules       import RulesList
from resources.lib.overlay     import Overlay


class Player(xbmc.Player):
    def __init__(self, service):
        self.log('__init__')
        xbmc.Player.__init__(self)
        self.myService          = service
        self.rules              = self.myService.rules
        
        self.pendingStart       = False
        self.pendingSeek        = False
        self.pendingStop        = False
        self.ruleList           = {}
        self.playingPVRitem     = {'channelid':-1}
        
        self.lastSubState       = isSubtitle()
        self.showOverlay        = SETTINGS.getSettingBool('Enable_Overlay')
        self.overlayWindow      = Overlay(OVERLAY_FLE, ADDON_PATH, "default", player=self)
        
        """
        xbmc.Player() trigger order
        Player: onPlayBackStarted
        Player: onAVChange
        Player: onAVStarted
        Player: onPlayBackSeek
        Player: onAVChange
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
        else:
            return self.getVideoInfoTag()


    def getPlayerTime(self):
        self.log('getPlayerTime')
        try:    return self.getTotalTime()
        except: return 0


    def getPVRTime(self):
        self.log('getPVRTime')
        try:    return (sum(x*y for x, y in zip(map(float, xbmc.getInfoLabel('PVR.EpgEventElapsedTime(hh:mm:ss)').split(':')[::-1]), (1, 60, 3600, 86400))))
        except: return 0


    def toggleSubtitles(self, state):
        self.log('toggleSubtitles, state = ' + str(state))
        if self.isPlaying():
            self.showSubtitles(state)
        
        
    def setSeekTime(self, seek):
        if not self.isPlayingVideo(): return
        self.log('setSeekTime, seek = %s'%(seek))
        self.seekTime(seek)
        
        
    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        self.lastSubState = isSubtitle()
        self.pendingStart = True
        self.playAction()
        

    def onAVChange(self):
        self.log('onAVChange')
        if self.pendingSeek and not self.pendingStart: #catch failed seekTime
            log('onAVChange, pendingSeek failed!',xbmc.LOGERROR)
            # self.setSeekTime(self.getPVRTime()) #onPlayBackSeek slow, false triggers! debug. 
            # self.toggleSubtitles(False)

        
    def onAVStarted(self):
        self.log('onAVStarted')
        self.pendingStart = False
        self.pendingStop  = True


    def onPlayBackSeek(self, seek_time, seek_offset):
        self.log('onPlayBackSeek, seek_time = %s, seek_offset = %s'%(seek_time,seek_offset))
        self.pendingSeek = False
        self.toggleSubtitles(self.lastSubState)
        
        
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        self.pendingStart = False
        self.pendingSeek  = False
        self.changeAction()
        

    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        self.pendingStart = False
        self.pendingSeek  = False
        self.pendingStop  = False
        self.stopAction()
        
        
    def onPlayBackError(self):
        self.log('onPlayBackError')
        self.pendingStart = False
        self.pendingSeek  = False
        self.stopAction()
        
        
    def playAction(self):
        setLegacyPseudoTV(True)# legacy setting to disable/enable support in third-party applications. 
        pvritem = getCurrentChannelItem()
        if pvritem.get('channelid',-1) == self.playingPVRitem.get('channelid',random.random()):
            self.log('playAction, no channel change')
        else:   
            self.log('playAction, channel changed')
            self.playingPVRitem = pvritem 
            self.ruleList = self.rules.loadRules([pvritem.get('citem',{})])
            pvritem = self.runActions(RULES_ACTION_PLAYER, (pvritem.get('citem',{})), pvritem)
            
            self.pendingSeek = int(pvritem.get('progress','0')) > 0
            if self.pendingSeek: 
                self.toggleSubtitles(False)
            self.log('playAction, pendingSeek = %s'%(self.pendingSeek))
           
        isPlaylist = self.playingPVRitem.get('isPlaylist',False)
        self.log('playAction, isPlaylist = %s'%(isPlaylist))
        if not isPseudoTV() and not isPlaylist:
            self.log('playAction, returning not PseudoTV Live channel')
            return self.stopAction()
        

    def updatePVRItem(self, pvritem=None):
        if pvritem is None: pvritem = self.playingPVRitem
        return self.myService.jsonRPC.getPVRposition(pvritem.get('name'), pvritem.get('id'), pvritem.get('isPlaylist'))
        # (self.myService.jsonRPC.matchPVRPath(pvritem.get('channelid',-1)) or self.myService.jsonRPC.getPlayerItem().get('mediapath',''))})


    def changeAction(self):
        if not getCurrentChannelItem(): 
            self.log('changeAction, returning channel_item not found.')
            return self.stopAction()
    
        isPlaylist = self.playingPVRitem.get('isPlaylist',False)
        callback   = self.playingPVRitem.get('callback','')
        
        if not isPlaylist: 
            clearCurrentChannelItem()
            self.log('changeAction, playing = %s'%(callback))
            xbmc.executebuiltin('PlayMedia(%s)'%callback)


    def stopAction(self):
        self.log('stopAction')
        clearCurrentChannelItem()
        self.toggleOverlay(False)
        setLegacyPseudoTV(False)


    def toggleOverlay(self, state):                                     
        if state and not isOverlay():
            if not (self.showOverlay & self.isPlaying() & hasPVRitem()): return
            self.log("toggleOverlay, show")
            self.overlayWindow.show()
        elif not state and isOverlay():
            self.log("toggleOverlay, close")
            self.overlayWindow.close()

    
class Monitor(xbmc.Monitor):
    def __init__(self, service):
        self.log('__init__')
        xbmc.Monitor.__init__(self)
        self.myService      = service
        self.pendingChange  = False
        self.lastSettings   = {}
        self.onChangeThread = threading.Timer(15.0, self.onChange)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def isSettingsOpened(self):
        if xbmcgui.getCurrentWindowDialogId() in [10140,12000,10126,10138]:
            return self.onSettingsChanged()
        return False


    def isPendingChange(self):
        # if isBusy() or self.isSettingsOpened(): return False
        return (self.pendingChange | PROPERTIES.getPropertyBool('pendingChange'))
    
    
    def setPendingChange(self, state):
        self.log('setPendingChange, state = %s'%(state))
        self.pendingChange = state
        PROPERTIES.setPropertyBool('pendingChange',state)


    def onSettingsChanged(self):
        ## Egg Timer, reset on each call.
        if self.onChangeThread.is_alive(): 
            self.onChangeThread.cancel()
            try: self.onChangeThread.join()
            except: pass
        self.onChangeThread = threading.Timer(15.0, self.onChange)
        self.onChangeThread.name = "onChangeThread"
        self.onChangeThread.start()
        return True
        
        
    def onChange(self):
        if isBusy(): return self.onSettingsChanged() # delay restart, changes still occurring.
        self.log('onChange')
        with busy():
            if self.hasSettingsChanged():
                self.setPendingChange(True)
            
            
    def chkPluginSettings(self):
        self.log('chkPluginSettings')
        for func in [chkPVR, 
                     chkMGR]: func()
        
        
    def chkSettings(self):
        self.log('chkSettings')
        self.chkPluginSettings()
        #priority settings that trigger chkUpdate on change.
        return {'User_Import'         :{'setting':SETTINGS.getSettingRefresh('User_Import')              ,'action':None},
                'Import_M3U_TYPE'     :{'setting':SETTINGS.getSettingRefresh('Import_M3U_TYPE')          ,'action':None},
                'Import_M3U_FILE'     :{'setting':SETTINGS.getSettingRefresh('Import_M3U_FILE')          ,'action':None},
                'Import_M3U_URL'      :{'setting':SETTINGS.getSettingRefresh('Import_M3U_URL')           ,'action':None},
                'Import_SLUG'         :{'setting':SETTINGS.getSettingRefresh('Import_SLUG')              ,'action':None},
                'User_Folder'         :{'setting':SETTINGS.getSettingRefresh('User_Folder')              ,'action':moveUser},
                'Select_Channels'     :{'setting':SETTINGS.getSettingRefresh('Select_Channels')     ,'action':None},
                'Select_TV_Networks'  :{'setting':SETTINGS.getSettingRefresh('Select_TV_Networks')  ,'action':None},
                'Select_TV_Shows'     :{'setting':SETTINGS.getSettingRefresh('Select_TV_Shows')     ,'action':None},
                'Select_TV_Genres'    :{'setting':SETTINGS.getSettingRefresh('Select_TV_Genres')    ,'action':None},
                'Select_Movie_Genres' :{'setting':SETTINGS.getSettingRefresh('Select_Movie_Genres') ,'action':None},
                'Select_Movie_Studios':{'setting':SETTINGS.getSettingRefresh('Select_Movie_Studios'),'action':None},
                'Select_Mixed_Genres' :{'setting':SETTINGS.getSettingRefresh('Select_Mixed_Genres') ,'action':None},
                'Select_Mixed'        :{'setting':SETTINGS.getSettingRefresh('Select_Mixed')        ,'action':None},
                'Select_Music_Genres' :{'setting':SETTINGS.getSettingRefresh('Select_Music_Genres') ,'action':None},
                'Select_Recommended'  :{'setting':SETTINGS.getSettingRefresh('Select_Recommended')  ,'action':None},
                'Select_Imports'      :{'setting':SETTINGS.getSettingRefresh('Select_Imports')      ,'action':None}}
        
        
    def hasSettingsChanged(self):
         #todo copy userfolder to new location
        if not self.lastSettings: return False
        currentSettings = self.chkSettings()
        differences = dict(diffDICT(self.lastSettings,currentSettings))
        if differences: 
            self.log('hasSettingsChanged, differences = %s'%(differences))
            self.lastSettings = currentSettings
            for key in differences.keys():
                func = currentSettings[key].get('action',None) 
                if func:
                    try: func()
                    except Exception as e: 
                        self.log("hasSettingsChanged, Failed! %s"%(e), xbmc.LOGERROR)
            return True
        return False
        
        
class Service:
    def __init__(self):
        self.log('__init__')
        self.cache         = Cache()
        self.dialog        = Dialog()   
        self.pool          = PoolHelper() 
        self.rules         = RulesList()  
        
        self.monitor       = Monitor(service=self)
        self.player        = Player(service=self)
        
        self.myBuilder     = Builder(service=self)
        self.writer        = self.myBuilder.writer
        self.channels      = self.myBuilder.writer.channels
        self.jsonRPC       = self.myBuilder.jsonRPC
        
        self.myConfig      = Config(sys.argv,service=self)
        
        self.startThread   = threading.Timer(1.0, hasVersionChanged)
        self.serviceThread = threading.Timer(0.5, self.runServiceThread)
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def startServiceThread(self, wait=30.0):
        self.log('startServiceThread, wait = %s'%(wait))
        if   self.writer.isClient(): return
        elif self.serviceThread.is_alive(): 
            self.serviceThread.cancel()
            try: self.serviceThread.join()
            except: pass
        self.serviceThread = threading.Timer(wait, self.runServiceThread)
        self.serviceThread.name = "serviceThread"
        self.serviceThread.start()
        
                
    def runServiceThread(self):
        if isBusy() or self.monitor.isSettingsOpened(): return self.startServiceThread()
        self.log('runServiceThread')
        self.monitor.setPendingChange(True)
        return self.startServiceThread(UPDATE_WAIT)
               

    def chkVersion(self):
        ## call in thread so prompt doesn't hold up service.
        if self.startThread.is_alive():
            self.startThread.cancel()
            try: self.startThread.join()
            except: pass
        self.startThread = threading.Timer(1.0, hasVersionChanged)
        self.startThread.name = "startThread"
        self.startThread.start()
           

    def chkBackup(self):
        self.log('chkBackup')
        PROPERTIES.setPropertyBool('has.Backup',self.myConfig.backup.hasBackup())


    def chkChannels(self):
        ## re-enable missing library.json items from channels.json
        self.log('chkChannels')
        return self.myConfig.recoverItemsFromChannels()
        
        
    def chkRecommended(self, lastUpdate=None):
        if chkUpdateTime('Last_Recommended',RECOMMENDED_OFFSET,lastUpdate):
            if self.myConfig.recommended.importPrompt():
                PROPERTIES.setProperty('Last_Recommended',str(time.time()))
            return True
        return False

            
    def chkPredefined(self, lastUpdate=None):
        if chkUpdateTime('Last_Predefined',PREDEFINED_OFFSET,lastUpdate):
            self.chkRecommended(lastUpdate=0)
            if self.myConfig.buildLibraryItems():
                PROPERTIES.setProperty('Last_Predefined',str(time.time()))
            return True
        return False
        
                
    def chkIdle(self):
        if getIdleTime() > OVERLAY_DELAY:
            self.player.toggleOverlay(True)
        else:
            self.player.toggleOverlay(False)
 

    def chkInfo(self):
        if not isCHKInfo(): return False
        self.monitor.waitForAbort(1) #adjust wait time to catch navigation meta. < 2secs? < 1sec. users report instability.
        return fillInfoMonitor()


    def chkUpdate(self, lastUpdate=None):
        if isBusy() or self.monitor.isSettingsOpened() or self.writer.isClient(): 
            return False
        
        with busy():
            conditions = [self.monitor.isPendingChange(),
                          chkUpdateTime('Last_Update',UPDATE_OFFSET,lastUpdate),
                          not FileAccess.exists(getUserFilePath(M3UFLE)),
                          not FileAccess.exists(getUserFilePath(XMLTVFLE))]
            
            if True in conditions:
                self.log('chkUpdate, lastUpdate = %s, conditions = %s'%(lastUpdate,conditions))
                self.monitor.setPendingChange(False)
                self.chkPredefined()
                
                if self.channels.reload():
                    channels = self.channels.getChannels()
                    if not channels:
                        if self.myConfig.autoTune(): #autotune
                            return self.chkUpdate(0) #force rebuild after autotune
                        self.log('chkUpdate, no channels found & autotuned recently')
                        return False #skip autotune if performed recently.
                    return self.updateChannels()
            return False
        
        
    def updateChannels(self):
        if self.myBuilder.buildService():
            self.log('updateChannels, finished buildService')
            PROPERTIES.setProperty('Last_Update',str(time.time()))
            return brutePVR(override=True)
        return False
                

    def initialize(self):
        setBusy(False) #reset value on 1st run.
        with busy():
            self.monitor.lastSettings = self.monitor.chkSettings()
            funcs = [initDirs,self.chkVersion,self.chkBackup,self.chkChannels]
            for func in funcs: func()
            return True

         
    def run(self, silent=False):
        self.log('run')
        self.monitor.waitForAbort(10) # startup delay
        
        if self.initialize():
            self.dialog.notificationProgress('%s...'%(LANGUAGE(30052)),wait=10)#startup delay
            self.monitor.waitForAbort(10) # service delay
            self.startServiceThread()
        
        while not self.monitor.abortRequested():
            if restartRequired(): break
            elif self.chkInfo(): continue # aggressive polling required (bypass waitForAbort)!
            elif self.monitor.waitForAbort(2): break
                
            if self.player.isPlaying():
                self.chkIdle()
            else:
                self.chkRecommended()
                
            if isBusy(): continue
            elif self.monitor.isSettingsOpened(): continue
            self.chkUpdate()
            
        self.closeThreads()
        if restartRequired():
            self.log('run, restarting buildService')
            setRestartRequired(False)
            self.run()
            
                
    def closeThreads(self):
        for thread in threading.enumerate():
            try: 
                if thread.name == "MainThread": continue
                self.log("closeThreads joining thread %s"%(thread.name))
                thread.cancel()
                try: thread_item.join(1.0)
                except: pass
            except Exception as e: log("closeThreads, Failed! %s"%(e), xbmc.LOGERROR)
        self.log('closeThreads finished, exiting %s...'%(ADDON_NAME))