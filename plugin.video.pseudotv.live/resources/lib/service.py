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
        self.pendingSeek = False
        self.toggleSubtitles(False)
        xbmc.sleep(100)
        self.seekTime(seek)
        self.toggleSubtitles(self.lastSubState)
        
        
    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        self.pendingStart = True
        self.playAction()
        

    def onAVChange(self):
        self.log('onAVChange')
        if self.pendingSeek and not self.pendingStart: #catch failed seekTime
            log('pendingSeek, failed!',xbmc.LOGERROR) # self.setSeekTime(self.getPVRTime())

        
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
        
        self.lastSubState = isSubtitle()
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
        self.lastUserM3U    = getSetting('Import_M3U')
        self.onChangeThread = threading.Timer(0.5, self.onChange)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def chkPendingChange(self):
        if   xbmcgui.getCurrentWindowDialogId() in [10140,12000,10126]: return True
        elif getSetting('Import_M3U') != self.lastUserM3U:
            self.lastUserM3U = getSetting('Import_M3U')
            return True #todo check other settings for change
        return False


    def isPendingChange(self):
        return (self.pendingChange | getPropertyBool('pendingChange'))
    
    
    def setPendingChange(self, state):
        self.log('setPendingChange, state = %s'%(state))
        self.pendingChange = state
        setPropertyBool('pendingChange',state)


    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def onSettingsChanged(self):
        setPropertyBool('isPlaylist',bool(getSettingInt('Playback_Method')))
        if not self.isPendingChange(): return
        self.log('onSettingsChanged')
        if self.onChangeThread.is_alive(): 
            self.onChangeThread.cancel()
        self.onChangeThread = threading.Timer((float((UPDATE_OFFSET//4)/60)), self.onChange)
        self.onChangeThread.name = "onChangeThread"
        self.onChangeThread.start()
        
        
    def onChange(self):
        if not self.isPendingChange(): return # last chance to cancel.
        elif isBusy(): return self.onSettingsChanged() # delay restart, still pending change.
        self.log('onChange')
        self.myService.chkUpdate('0')
        self.setPendingChange(False)


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
        
        self.myPlugin      = Plugin(sys.argv,service=self)     
        self.myConfig      = Config(sys.argv,service=self)        

        self.InitThread    = threading.Timer(0.5, self.startInitThread)
        self.serviceThread = threading.Timer(0.5, self.runServiceThread)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def startInitThread(self): 
        self.log('startInitThread')
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
        if getIdleTime() > OVERLAY_DELAY: #15sec. overlay delay...
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
            if lastUpdate is None: 
                lastUpdate = (getProperty('Last_Update') or '0')
                
            conditions = [self.myMonitor.isPendingChange(),
                          not FileAccess.exists(M3UFLE),
                          not FileAccess.exists(XMLTVFLE),
                          (time.time() > (float(lastUpdate or '0') + UPDATE_OFFSET))]
            self.log('chkUpdate, lastUpdate = %s, conditions = %s'%(lastUpdate,conditions))
            
            if True in conditions:
                if not self.myBuilder.getChannels():
                    if self.myConfig.autoTune():   #autotune
                        return self.chkUpdate('0') #force rebuild after autotune
                    self.log('chkUpdate, no channels found & autotuned recently')
                    return False #skip autotune if performed recently.
                    # if self.writer.recoverChannels(): 
                    # return self.chkUpdate('0')
                return self.updateChannels()
            return False
        
        
    def updateChannels(self):
        self.log('updateChannels')
        if self.myBuilder.buildService(): 
            setProperty('Last_Update',str(time.time()))
            return brutePVR(override=True)
        return False
                 
         
    def run(self, silent=False):
        self.log('run')
        setBusy(False)
        if notificationProgress('%s...'%(LANGUAGE(30052))): initDirs()
        for initThread in [self.startInitThread, self.startServiceThread]: initThread()
        self.myMonitor.waitForAbort(15)#ensure threads are active before main service starts. cheaper then another while loop.
        while not self.myMonitor.abortRequested():
            if   self.chkInfo(): continue # aggressive polling required!
            elif self.myMonitor.waitForAbort(2): break
            self.chkIdle()
            
            if self.myMonitor.chkPendingChange(): # detect settings change. 
                self.myMonitor.setPendingChange(True)
                continue
            elif isBusy() or self.myMonitor.isPendingChange():
                continue
                
            self.chkRecommended()
            self.chkUpdate()
            
        self.closeThreads()
                
                
    def closeThreads(self):
        self.log('closeThreads')
        for thread in threading.enumerate():
            try: 
                if thread.name == "MainThread": continue
                log("closeThreads joining thread %s"%(thread.name))
                thread.cancel()
                thread.join(1.0)
            except Exception as e: log("closeThreads, Failed! %s"%(e), xbmc.LOGERROR)
        self.log('closeThreads, exiting %s'%(ADDON_NAME))