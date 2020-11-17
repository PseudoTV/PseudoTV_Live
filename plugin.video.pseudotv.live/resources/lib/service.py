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
from plugin                    import Plugin
from config                    import Config
from resources.lib.overlay     import Overlay

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.pendingStop        = False
        self.pendingSeek        = False
        self.lastSubState       = isSubtitle()
        self.playingChannelItem = {'channelid':-1}
        self.overlayWindow      = Overlay(OVERLAY_FLE, ADDON_PATH, "default")
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


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
        self.pendingSeek = False
        
        
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
            self.stopAction()
            return self.log('playAction, returning not PseudoTV Live')
        
        self.toggleSubtitles(False)
        setProperty('PseudoTVRunning','True') # legacy setting to disable/enable support in third-party applications. 
        
        currentChannelItem = getCurrentChannelItem()
        currentChannelId   = currentChannelItem.get('channelid',-1)
        lastChannelId      = self.playingChannelItem.get('channelid',random.random())
        if not currentChannelItem.get('callback',''):
            currentChannelItem['callback'] = (self.myService.myPlugin.pvr.matchPVRPath(currentChannelId) or self.myService.jsonRPC.getPlayerItem().get('mediapath',''))
        
        if lastChannelId == currentChannelId: 
            self.log('playAction, no channel change')
            self.playingChannelItem.update(currentChannelItem)
        else:   
            self.log('playAction, new channel change')
            self.playingChannelItem = currentChannelItem
            self.pendingSeek = currentChannelItem.get('progress',0) > 0
        setCurrentChannelItem(self.playingChannelItem)
        self.log('playAction, lastChannelId = %s, currentChannelId = %s, callback = %s'%(lastChannelId,currentChannelId,currentChannelItem['callback']))


    def isPlaylist(self):
        return self.playingChannelItem.get('isPlaylist',False)


    def changeAction(self):
        if not getCurrentChannelItem(): 
            self.stopAction()
            return self.log('changeAction, ignore not PseudoTV Live')
    
        isplaylist = self.isPlaylist()
        callback   = self.playingChannelItem.get('callback','')
        if not isplaylist: clearCurrentChannelItem()
        if (isplaylist or not callback): 
            self.log('changeAction, ignore playlist or missing callback')
            return
        self.log('changeAction, playing = %s'%(callback))
        xbmc.executebuiltin('PlayMedia(%s)'%callback)
        

    def stopAction(self):
        self.log('stopAction')
        self.pendingSeek = False
        clearCurrentChannelItem()
        self.toggleOverlay(False)
        setProperty('PseudoTVRunning','False')


    def overlayOpened(self):
        xbmc.sleep(500) # sleep to catch doModal delay.
        return getProperty('OVERLAY') == 'true'


    def isOverlay(self):
        return getSettingBool('Enable_Overlay')

    
    def toggleOverlay(self, state):
        if state and not self.overlayOpened():
            conditions = [self.isOverlay(),self.isPlaying(),isPseudoTV()]
            if (False in conditions): return
            self.log("toggleOverlay, show")
            self.overlayWindow.show()
        elif not state and self.overlayOpened():
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
        self.log('onSettingsChanged')
        if self.onChangeThread.isAlive(): self.onChangeThread.cancel()
        self.onChangeThread = threading.Timer(30.0, self.onChange)
        self.onChangeThread.name = "onChangeThread"
        self.onChangeThread.start()
        
        
    def onChange(self):
        if not self.pendingChange: return # last chance to cancel.
        self.log('onChange')
        if isBusy(): return self.onSettingsChanged() # delay restart, still pending change.
        self.myService.serverRestart = True
        self.pendingChange = False


class Service:
    def __init__(self):
        self.myMonitor     = Monitor()
        self.myMonitor.myService = self
        self.myPlayer      = Player()
        self.myPlayer.myService = self
        self.myConfig      = Config(sys.argv)
        self.myConfig.myService = self
        self.myPredefined  = self.myConfig.predefined
        self.myPlugin      = Plugin(sys.argv)
        self.myBuilder     = self.myPlugin.builder
        self.jsonRPC       = self.myBuilder.jsonRPC
        self.channelList   = self.myBuilder.getChannelList()
        self.serverRestart = False


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

    
    def initalizeChannels(self):
        self.log('initalizeChannels')
        channelList = self.myBuilder.getChannelList()
        if not channelList and not self.myConfig.channels.isClient:
            if self.myConfig.autoTune():
                channelList = self.myBuilder.getChannelList()
        return channelList


    def getSeekTol(self):
        try: return getSettingInt('Seek_Tolerance')
        except: return 30 #Kodi raises error after sleep. # todo debug
        
        
    def getIdleTime(self):
        try: return (xbmc.getGlobalIdleTime() or 0)
        except: return 0 #Kodi raises error after sleep. # todo debug
    
        
    def chkIdle(self):
        if self.getIdleTime() > self.getSeekTol():
            self.myPlayer.toggleOverlay(True)
        else:
            self.myPlayer.toggleOverlay(False)


    def chkUpdate(self):
        if self.myMonitor.pendingChange or isBusy(): return
        lastCheck = float(getSetting('Last_Scan') or 0)
        conditions = [not xbmcvfs.exists(M3UFLE), not xbmcvfs.exists(XMLTVFLE), (time.time() > (lastCheck + UPDATE_OFFSET))]
        if True in conditions:
            self.updateChannels(update=True)
        
        
    def updateChannels(self, channels=[], update=False):
        if len(channels) == 0: 
            channels = self.myBuilder.getChannelList()
        unchanged, difference = assertDICT(self.channelList,channels,return_diff=True)
        self.log('updateChannels, channels = %s, update = %s, unchanged = %s, difference = %s'%(len(channels), update, unchanged,len(difference)))
        self.channelList = channels
        if self.myBuilder.buildService(channels, update):
            setSetting('Last_Scan',str(time.time()))
            return True
        else:
            if self.initalizeChannels():
                return True
        return False
        
        
    def chkInfo(self):
        if not isCHKInfo(): return False
        self.myMonitor.waitForAbort(.1)
        return fillInfoMonitor()


    def serviceActions(self):
        self.chkIdle()
        self.chkUpdate()
        

    def startService(self, silent=False):
        self.log('startService')
        setBusy(False)
        self.serverRestart = False
        self.myMonitor.pendingChange = False
        self.myConfig.runInitThread()
        
        if not silent: 
            msg = ': %s'%LANGUAGE(30099) if getClient() else ''
            notificationProgress(LANGUAGE(30052)%(msg))
        
        self.updateChannels(channels=self.initalizeChannels())
        self.myConfig.startServiceThread()
        
        while not self.myMonitor.abortRequested():
            if self.chkInfo(): continue # aggressive polling.
            elif self.myMonitor.waitForAbort(5) or self.serverRestart: break
            elif xbmcgui.getCurrentWindowDialogId() in [10140,12000,10126]: # detect settings change. 
                self.log('settings opened')
                self.myMonitor.pendingChange = True
                self.myMonitor.onSettingsChanged()
                continue
            elif self.myMonitor.pendingChange:
                self.log('pending change')
                continue
            self.serviceActions()
            
        # restart service
        if self.serverRestart:
            self.startService(silent=True)
        else:
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