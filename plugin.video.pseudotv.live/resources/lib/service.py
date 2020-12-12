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
from resources.lib.rules       import RulesList
from plugin                    import Plugin
from config                    import Config
from resources.lib.overlay     import Overlay

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.pendingStop        = False
        # self.pendingSeek        = False
        self.rules              = RulesList()
        self.lastSubState       = isSubtitle()
        self.ruleList           = {}
        self.playingPVRitem     = {'channelid':-1}
        self.overlayWindow      = Overlay(OVERLAY_FLE, ADDON_PATH, "default")
        
        #global
        self.showOverlay        = getSettingBool('Enable_Overlay')
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def runActions(self, action, citem, parameter=None):
        self.log("runActions action = %s, channel = %s"%(action,citem))
        if not citem.get('id',''): return parameter
        ruleList = self.ruleList.get(citem['id'],[])
        for rule in ruleList:
            if action in rule.actions:
                self.log("runActions performing channel rule: %s"%(rule.name))
                parameter = rule.runAction(action, self, parameter)
        return parameter
        
        
    def getInfoTag(self):
        self.log('getInfoTag')
        if self.isPlayingAudio():
            return self.getMusicInfoTag()
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
        self.showSubtitles(state)
        
        
    def setSeekTime(self, seek):
        self.log('setSeekTime')
        return self.seekTime(seek)
        
        
    def onAVStarted(self):
        self.log('onAVStarted')
        # if self.pendingSeek: #catched failed seekTime
            # self.setSeekTime(self.getPVRTime())
        self.toggleSubtitles(self.lastSubState)


    def onAVChange(self):
        self.log('onAVChange')
        self.pendingStop = True #onAVChange called before onPlayBackEnded,onPlayBackStopped


    def onPlayBackSeek(self, seek_time, seek_offset):
        self.log('onPlayBackSeek, seek_time = %s, seek_offset = %s'%(seek_time,seek_offset))
        # self.pendingSeek = False
        
        
    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        self.pendingStop  = False
        self.lastSubState = isSubtitle()
        self.playAction()
        
        
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
        if not isPseudoTV(): 
            self.log('playAction, returning not PseudoTV Live')
            return self.stopAction()
            
        self.toggleSubtitles(False)
        setProperty('PseudoTVRunning','True') # legacy setting to disable/enable support in third-party applications. 
        
        pvritem = getCurrentChannelItem()                
        if (pvritem.get('citem',{}).get('path','') or None) is None:
            pvritem.update({'citem':self.myService.channels.findChannel(pvritem.get('citem',{}), self.myService.channels.getAllChannels())[1]})

        if (pvritem.get('callback','') or None) is None:
            pvritem.update({'callback':(self.myService.jsonRPC.matchPVRPath(pvritem.get('channelid',-1)) or self.myService.jsonRPC.getPlayerItem().get('mediapath',''))})

        if pvritem.get('channelid',-1) == self.playingPVRitem.get('channelid',random.random()):
            self.log('playAction, no channel change')
        else:   
            self.log('playAction, new channel change')
            self.ruleList = self.rules.loadRules([pvritem.get('citem',{})])
            pvritem = self.runActions(RULES_ACTION_PLAYER, (pvritem.get('citem',{})), pvritem)
            self.pendingSeek = pvritem.get('progress',0) > 0
            setCurrentChannelItem(pvritem)
            self.playingPVRitem = pvritem
            

    def changeAction(self):
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
        #means to update pvritem without plugin playback
        # pvritem = self.myService.jsonRPC.getPVRposition(self.playingPVRitem.get('name'), self.playingPVRitem.get('id'), self.playingPVRitem.get('isPlaylist'))
        
        
    def stopAction(self):
        self.log('stopAction')
        # self.pendingSeek = False
        clearCurrentChannelItem()
        self.toggleOverlay(False)
        setProperty('PseudoTVRunning','False')


    def isPlaylist(self):
        return self.playingPVRitem.get('isPlaylist',False)


    def isOverlay(self):
        xbmc.sleep(500) # sleep to catch doModal delay.
        return getProperty('OVERLAY') == 'true'


    def toggleOverlay(self, state):
        if state and not self.isOverlay():
            conditions = [self.showOverlay,
                          self.isPlaying(),
                          isPseudoTV()]
            if (False in conditions): return
            self.log("toggleOverlay, show")
            self.overlayWindow.show()
        elif not state and self.isOverlay():
            self.log("toggleOverlay, close")
            self.overlayWindow.close()

    
class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.pendingChange  = False
        self.onChangeThread = threading.Timer(0.5, self.onChange)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onNotification(self, sender, method, data):
        self.log("onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def onSettingsChanged(self):
        if not self.pendingChange: return # only trigger when settings dialog opened
        self.log('onSettingsChanged, pendingChange = %s'%(self.pendingChange))
        if self.onChangeThread.is_alive(): 
            self.onChangeThread.cancel()
        self.onChangeThread = threading.Timer(15.0, self.onChange)
        self.onChangeThread.name = "onChangeThread"
        self.onChangeThread.start()
        
        
    def onChange(self):
        if not self.pendingChange: return # last chance to cancel.
        elif isBusy(): return self.onSettingsChanged() # delay restart, still pending change.
        self.log('onChange, pendingChange = %s'%(self.pendingChange))
        REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID) #reinit, needed?
        self.myService.chkUpdate()
        self.pendingChange = False


class Service:
    def __init__(self):
        self.autoTune      = True
        self.myMonitor     = Monitor()
        self.myMonitor.myService = self
        
        self.myPlayer      = Player()
        self.myPlayer.myService = self
        
        self.myBuilder     = Builder()
        self.myBuilder.myService = self
        self.jsonRPC       = self.myBuilder.jsonRPC
        self.channels      = self.myBuilder.channels
        
        self.myConfig      = Config(sys.argv)
        self.myConfig.myService = self
        self.myPredefined  = self.myConfig.predefined
        
        self.myPlugin      = Plugin(sys.argv)
        self.myPlugin.myService = self
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getSeekTol(self):
        try: return getSettingInt('Seek_Tolerance')
        except: return 55 #Kodi raises error after sleep. # todo debug
        
        
    def getIdleTime(self):
        try: return (int(xbmc.getGlobalIdleTime()) or 0)
        except: return 0 #Kodi raises error after sleep. # todo debug
    
        
    def chkInfo(self):
        if not isCHKInfo(): return False
        self.myMonitor.waitForAbort(2) #adjust wait time to catch navigation meta. < 2secs? < 1 users report instability.
        return fillInfoMonitor()


    def chkIdle(self):
        if self.getIdleTime() > self.getSeekTol():
            self.myPlayer.toggleOverlay(True)
        else:
            self.myPlayer.toggleOverlay(False)


    def getAutoTune(self):
        self.log('getAutoTune')
        if not self.channels.isClient and not isBusy():
            if self.myConfig.autoTune():
                return self.myBuilder.getChannelList()
        return None
          
        
    def chkUpdate(self, lastUpdate='0'):
        if isBusy(): return False
        self.log('chkUpdate, lastUpdate = %s'%(lastUpdate))
        conditions = [self.myMonitor.pendingChange, 
                      not xbmcvfs.exists(M3UFLE), 
                      not xbmcvfs.exists(XMLTVFLE),
                      (time.time() > (float(lastUpdate or '0') + UPDATE_OFFSET))]
        if True in conditions:
            channels = self.myBuilder.getChannelList()
            if not channels and self.autoTune:
                self.autoTune = False
                channels = self.getAutoTune()
            return self.updateChannels(channels)
        return False
        
        
    def updateChannels(self, channels=None):
        if channels is None: channels = self.myBuilder.getChannelList()
        self.log('updateChannels, channels = %s'%(len(channels)))
        if channels:
            if self.myBuilder.buildService(channels): 
                setProperty('Last_Update',str(time.time()))
                return brutePVR(override=True)
        return False
                    

    def serviceActions(self):
        self.chkIdle()
        self.chkUpdate(lastUpdate=getProperty('Last_Update'))
        

    def startService(self, silent=False):
        self.log('startService')
        setBusy(False)
        notificationProgress(LANGUAGE(30052)%('...'))
        initThreads = [self.myConfig.startInitThread,
                       self.myConfig.startServiceThread]
                       
        for initThread in initThreads:
            initThread()
            
        self.myMonitor.waitForAbort(15)#insurance to ensure threads are active before main service starts. cheaper then another a while loop.
        while not self.myMonitor.abortRequested():
            if self.chkInfo(): continue # aggressive polling.
            elif self.myMonitor.waitForAbort(2): break
            elif xbmcgui.getCurrentWindowDialogId() in [10140,12000,10126]: # detect settings change. 
                self.log('settings opened')
                self.myMonitor.pendingChange = True
                self.myMonitor.onSettingsChanged()
                continue
            elif self.myMonitor.pendingChange:
                self.log('pending change')
                continue
            self.serviceActions()
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


if __name__ == '__main__': Service()