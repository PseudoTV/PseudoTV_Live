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
from resources.lib.overlay     import Overlay
from resources.lib.rules       import RulesList
from resources.lib.builder     import Builder
from plugin                    import Plugin
from config                    import Config

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.pendingStart       = False
        self.pendingSeek        = False
        self.pendingStop        = False
        self.rules              = RulesList()
        self.lastSubState       = isSubtitle()
        self.ruleList           = {}
        self.playingPVRitem     = {'channelid':-1}
        self.showOverlay        = getSettingBool('Enable_Overlay')
        self.overlayWindow      = Overlay(OVERLAY_FLE, ADDON_PATH, "default")
        
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
        if not isPseudoTV(): 
            self.log('playAction, returning not PseudoTV Live')
            return self.stopAction()
        
        self.toggleSubtitles(False)
        setLegacyPseudoTV(True)# legacy setting to disable/enable support in third-party applications. 
        pvritem = getCurrentChannelItem()                
        if (pvritem.get('citem',{}).get('path','') or None) is None:
            pvritem.update({'citem':self.myService.channels.findChannel(pvritem.get('citem',{}), self.myService.channels.getChannels())[1]})

        if (pvritem.get('callback','') or None) is None:
            pvritem.update({'callback':(self.myService.jsonRPC.matchPVRPath(pvritem.get('channelid',-1)) or self.myService.jsonRPC.getPlayerItem().get('mediapath',''))})

        if pvritem.get('channelid',-1) == self.playingPVRitem.get('channelid',random.random()):
            self.log('playAction, no channel change')
        else:   
            self.log('playAction, new channel change')
            self.showOverlay = getSettingBool('Enable_Overlay',xbmcaddon.Addon(id=ADDON_ID))
            self.ruleList = self.rules.loadRules([pvritem.get('citem',{})])
            pvritem = self.runActions(RULES_ACTION_PLAYER, (pvritem.get('citem',{})), pvritem)
            self.pendingSeek = int(pvritem.get('progress','0')) > 0
            self.log('playAction, pendingSeek = %s'%(self.pendingSeek))
            setCurrentChannelItem(pvritem)
            self.playingPVRitem = pvritem
            

    def changeAction(self):
        # means to update pvritem without plugin playback
        # pvritem = self.myService.jsonRPC.getPVRposition(self.playingPVRitem.get('name'), self.playingPVRitem.get('id'), self.playingPVRitem.get('isPlaylist'))
        if not getCurrentChannelItem(): 
            self.stopAction()
            return self.log('changeAction, ignore not PseudoTV Live')
    
        isPlaylist = self.isPlaylist()
        callback   = self.playingPVRitem.get('callback','')
        if not isPlaylist: clearCurrentChannelItem()
        elif (isPlaylist or not callback): 
            self.log('changeAction, ignore playlist or missing callback')
            return
            
        self.log('changeAction, playing = %s'%(callback))
        xbmc.executebuiltin('PlayMedia(%s)'%callback)


    def stopAction(self):
        self.log('stopAction')
        clearCurrentChannelItem()
        self.toggleOverlay(False)
        setLegacyPseudoTV(False)


    def isPlaylist(self):
        return self.playingPVRitem.get('isPlaylist',False)


    def toggleOverlay(self, state):                                     
        if state and not isOverlay():
            if not (self.showOverlay & self.isPlaying() & hasPVRitem()): return
            self.log("toggleOverlay, show")
            self.overlayWindow.show()
        elif not state and isOverlay():
            self.log("toggleOverlay, close")
            self.overlayWindow.close()

    
class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.pendingChange  = False
        self.lastSettings   = self.chkSettings()
        self.onChangeThread = threading.Timer(0.5, self.onChange)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def isSettingsOpened(self):
        if xbmcgui.getCurrentWindowDialogId() in [10140,12000,10126,10138]:
            self.onSettingsChanged()
            return True
        return False


    def isPendingChange(self):
        return (self.pendingChange | getPropertyBool('pendingChange'))
    
    
    def setPendingChange(self, state):
        self.log('setPendingChange, state = %s'%(state))
        self.pendingChange = state
        setPropertyBool('pendingChange',state)


    def onSettingsChanged(self):
        if self.onChangeThread.is_alive(): 
            self.onChangeThread.cancel()
        self.onChangeThread = threading.Timer(15.0, self.onChange)
        self.onChangeThread.name = "onChangeThread"
        self.onChangeThread.start()
        
        
    def onChange(self):
        if isBusy(): return self.onSettingsChanged() # delay restart, changes still occurring.
        self.log('onChange')
        if self.hasSettingsChanged():
            self.setPendingChange(True)
            
        
    def chkSettings(self):
        self.log('chkSettings')
        #priority settings that trigger chkUpdate on change.
        return {'User_Import'         :{'setting':getSetting('User_Import',xbmcaddon.Addon(id=ADDON_ID))         ,'action':None},
                'Import_M3U_TYPE'     :{'setting':getSetting('Import_M3U_TYPE',xbmcaddon.Addon(id=ADDON_ID))     ,'action':None},
                'Import_M3U_FILE'     :{'setting':getSetting('Import_M3U_FILE',xbmcaddon.Addon(id=ADDON_ID))     ,'action':None},
                'Import_M3U_URL'      :{'setting':getSetting('Import_M3U_URL',xbmcaddon.Addon(id=ADDON_ID))      ,'action':None},
                'Import_SLUG'         :{'setting':getSetting('Import_SLUG',xbmcaddon.Addon(id=ADDON_ID))         ,'action':None},
                'User_Folder'         :{'setting':getSetting('User_Folder',xbmcaddon.Addon(id=ADDON_ID))         ,'action':moveUser},
                'Select_Channels'     :{'setting':getSetting('Select_Channels',xbmcaddon.Addon(id=ADDON_ID))     ,'action':None},
                'Select_TV_Networks'  :{'setting':getSetting('Select_TV_Networks',xbmcaddon.Addon(id=ADDON_ID))  ,'action':None},
                'Select_TV_Shows'     :{'setting':getSetting('Select_TV_Shows',xbmcaddon.Addon(id=ADDON_ID))     ,'action':None},
                'Select_TV_Genres'    :{'setting':getSetting('Select_TV_Genres',xbmcaddon.Addon(id=ADDON_ID))    ,'action':None},
                'Select_Movie_Genres' :{'setting':getSetting('Select_Movie_Genres',xbmcaddon.Addon(id=ADDON_ID)) ,'action':None},
                'Select_Movie_Studios':{'setting':getSetting('Select_Movie_Studios',xbmcaddon.Addon(id=ADDON_ID)),'action':None},
                'Select_Mixed_Genres' :{'setting':getSetting('Select_Mixed_Genres',xbmcaddon.Addon(id=ADDON_ID)) ,'action':None},
                'Select_Mixed'        :{'setting':getSetting('Select_Mixed',xbmcaddon.Addon(id=ADDON_ID))        ,'action':None},
                'Select_Music_Genres' :{'setting':getSetting('Select_Music_Genres',xbmcaddon.Addon(id=ADDON_ID)) ,'action':None},
                'Select_Recommended'  :{'setting':getSetting('Select_Recommended',xbmcaddon.Addon(id=ADDON_ID))  ,'action':None},
                'Select_Imports'      :{'setting':getSetting('Select_Imports',xbmcaddon.Addon(id=ADDON_ID))      ,'action':None}}
        
        
    def hasSettingsChanged(self):
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
        self.myMonitor     = Monitor()
        self.myMonitor.myService = self
        
        self.myPlayer      = Player()
        self.myPlayer.myService = self
        
        self.myBuilder     = Builder()
        self.myBuilder.myService = self
        self.jsonRPC       = self.myBuilder.jsonRPC
        self.writer        = self.myBuilder.writer
        self.channels      = self.myBuilder.channels
        self.dialog        = self.myBuilder.dialog
        
        self.myPlugin      = Plugin(sys.argv,service=self)     
        self.myConfig      = Config(sys.argv,service=self)        

        self.InitThread    = threading.Timer(0.5, self.startInitThread)
        self.serviceThread = threading.Timer(0.5, self.runServiceThread)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def startInitThread(self): 
        self.log('startInitThread')
        setBusy(False)
        self.myMonitor.setPendingChange(False)
        if self.InitThread.is_alive(): self.InitThread.cancel()
        self.InitThread = threading.Timer(0.5, self.runInitThread)
        self.InitThread.name = "InitThread"
        self.InitThread.start()


    def runInitThread(self):
        self.log('runInitThread')
        for func in [chkPVR, chkMGR, chkVersion]: func()            
            
            
    def startServiceThread(self, wait=5.0):
        self.log('startServiceThread, wait = %s'%(wait))
        if   self.writer.isClient(): return
        elif self.serviceThread.is_alive(): self.serviceThread.cancel()
        self.serviceThread = threading.Timer(wait, self.runServiceThread)
        self.serviceThread.name = "serviceThread"
        self.serviceThread.start()
        
                
    def runServiceThread(self):
        if isBusy(): return self.startServiceThread(float((UPDATE_OFFSET//4)/60))
        with busy():
            self.log('runServiceThread, started')
            for func in [self.chkRecommended, self.chkPredefined, self.chkUpdate]: func()
            self.log('runServiceThread, finished')
            return self.startServiceThread(UPDATE_WAIT)
                   
        
    def chkRecommended(self):
        return self.myConfig.recommended.importPrompt()

            
    def chkPredefined(self):
        return self.myConfig.buildLibraryItems()
        
                
    def chkIdle(self):
        if getIdleTime() > OVERLAY_DELAY:
            self.myPlayer.toggleOverlay(True)
        else:
            self.myPlayer.toggleOverlay(False)
 

    def chkInfo(self):
        if not isCHKInfo(): return False
        self.myMonitor.waitForAbort(1) #adjust wait time to catch navigation meta. < 2secs? < 1sec. users report instability.
        return fillInfoMonitor()


    def chkUpdate(self, lastUpdate=None):
        if isBusy() or self.writer.isClient(): 
            return False
        
        with busy():
            self.chkRecommended()
            
            if lastUpdate is None: 
                lastUpdate = (getProperty('Last_Update') or '0')
                 
            conditions = [self.myMonitor.isPendingChange(),
                          not FileAccess.exists(getUserFilePath(M3UFLE)),
                          not FileAccess.exists(getUserFilePath(XMLTVFLE)),
                          (time.time() > (float(lastUpdate or '0') + UPDATE_OFFSET))]
            
            if True in conditions:
                self.log('chkUpdate, lastUpdate = %s, conditions = %s'%(lastUpdate,conditions)) 
                if self.myMonitor.isPendingChange():
                    self.myMonitor.setPendingChange(False)
                    
                if not self.myBuilder.getChannels():
                    if self.myConfig.autoTune():   #autotune
                        return self.chkUpdate('0') #force rebuild after autotune
                    self.log('chkUpdate, no channels found & autotuned recently')
                    return False #skip autotune if performed recently.
                return self.updateChannels()
            return False
        
        
    def updateChannels(self):
        if self.myBuilder.buildService():
            self.log('updateChannels, finished buildService')
            setProperty('Last_Update',str(time.time()))
            return brutePVR(override=True)
        return False
                 
         
    def run(self, silent=False):
        self.log('run')
        self.dialog.notificationProgress('%s...'%(LANGUAGE(30052)),funcs=[(initDirs,None,None),(self.myConfig.hasBackup,None,None)])
        for initThread in [self.startInitThread, self.startServiceThread]: initThread()
        self.myMonitor.waitForAbort(15)#ensure threads are active before main service starts. cheaper then another while loop.

        # self.dialog.notificationProgress('%s...'%(LANGUAGE(30052)),
                                 # funcs=[(initDirs,None,None),
                                        # (self.myConfig.hasBackup,None,None),
                                        # (self.startInitThread,None,None),
                                        # (self.startServiceThread,None,None)])
        
        while not self.myMonitor.abortRequested():
            if   self.chkInfo(): continue # aggressive polling required (bypass waitForAbort)!
            elif self.myMonitor.waitForAbort(2) or restartRequired(): break
            self.chkIdle()
            
            if self.myMonitor.isSettingsOpened() or isBusy(): continue
            self.chkUpdate()
            
        self.closeThreads()
        
        if restartRequired():
            self.log('run, restarting buildService')
            setRestartRequired(False)
            self.myMonitor.waitForAbort(30)
            self.run()
            
                
    def closeThreads(self):
        for thread in threading.enumerate():
            try: 
                if thread.name == "MainThread": continue
                self.log("closeThreads joining thread %s"%(thread.name))
                thread.cancel()
                thread.join(1.0)
            except Exception as e: log("closeThreads, Failed! %s"%(e), xbmc.LOGERROR)
        self.log('closeThreads finished, exiting %s...'%(ADDON_NAME))