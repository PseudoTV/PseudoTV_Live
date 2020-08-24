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
from resources.lib.globals import *
from plugin                import Plugin
from config                import Config
from resources.lib.overlay import Overlay

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.playingChannelItem = {'channelid':-1}
        self.overlayWindow      = Overlay(OVERLAY_FLE, ADDON_PATH, "default")
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getPlayerTime(self):
        try:    return self.getTotalTime()
        except: return 0


    def getPVRTime(self):
        self.log('getPVRTime')
        EpgEventElapsedTime = xbmc.getInfoLabel('PVR.EpgEventElapsedTime(hh:mm:ss)')
        return (sum(x*y for x, y in zip(map(float, EpgEventElapsedTime.split(':')[::-1]), (1, 60, 3600, 86400))))


    def toggleSubtitles(self, state):
        self.log('toggleSubtitles, state = ' + str(state))
        self.showSubtitles(state)
        

    def onPlayBackSeek(self, seek_time, seek_offset):
        self.log('onPlayBackSeek, seek_time = %s, seek_offset = %s'%(seek_time,seek_offset))
    

    def onAVStarted(self):
        self.log('onAVStarted')
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
            return self.log('playAction, returning not PseudoTV Live') #isPseudoTV check, todo added logic to exclude other playback sources
        
        setProperty('PseudoTVRunning','True') # legacy setting to disable/enable support in third-party applications. 
        currentChannelItem = getCurrentChannelItem()
        currentChannelId   = currentChannelItem.get('channelid',-1)
        lastChannelId      = self.playingChannelItem.get('channelid',random.random())
        if not currentChannelItem.get('callback',''):
            currentChannelItem['callback'] = (self.myService.jsonRPC.matchPVRPath(currentChannelId) or self.myService.jsonRPC.getPlayerItem().get('mediapath',''))
        
        if lastChannelId == currentChannelId: 
            self.log('playAction, no channel change')
        else:   
            self.playingChannelItem = currentChannelItem
            setCurrentChannelItem(self.playingChannelItem)
        self.log('playAction, lastChannelId = %s, currentChannelId = %s, callback = %s'%(lastChannelId,currentChannelId,currentChannelItem['callback']))


    def isPlaylist(self):
        return self.playingChannelItem.get('isPlaylist',False)


    def changeAction(self):
        isplaylist = self.isPlaylist()
        callback   = self.playingChannelItem.get('callback','')
        if not isplaylist: clearCurrentChannelItem()
        if isplaylist or not callback: 
            self.log('changeAction, ignore playlist or missing callback')
            return
        self.log('changeAction, playing = %s'%(callback))
        xbmc.executebuiltin('PlayMedia(%s)'%callback)
        

    def stopAction(self):
        self.log('stopAction')
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
        if isBusy(): return self.onSettingsChanged() # delay check, still pending change.
        self.myService.serverStopped = True
        self.setPendingChange(False)


    def setPendingChange(self, state):
        self.log('setPendingChange, pendingChange = %s'%(state))
        self.pendingChange = state
        

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
        self.myBuilder     = self.myPlugin.myBuilder
        self.jsonRPC       = self.myBuilder.jsonRPC
        self.channelList   = self.getChannelList()
        self.serverStopped = False
        self.startService()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

    
    def initalizeChannels(self):
        self.log('initalizeChannels')
        channelList = []
        if self.myPredefined.buildPredefinedChannels(): 
            channelList = self.getChannelList()
        if len(channelList) == 0: 
            if self.myConfig.autoTune(): 
                channelList = self.getChannelList()
        return channelList


    def getChannelList(self):
        self.log('getChannelList')
        return sorted(self.myBuilder.createChannelItems(), key=lambda k: k['number'])
        

    def getSeekTol(self):
        try: return getSettingInt('Seek_Tolerance')
        except: return 30 #Kodi raises error after sleep. # todo debug
        
        
    def chkIdle(self):
        if xbmc.getGlobalIdleTime() > self.getSeekTol():
            self.myPlayer.toggleOverlay(True)
        else:
            self.myPlayer.toggleOverlay(False)


    def chkUpdate(self):
        if self.myMonitor.pendingChange or isBusy(): return
        lastCheck = float(getSetting('Last_Scan') or 0)
        if (time.time() > (lastCheck + UPDATE_OFFSET)):
            clearProperty("USER_LOG")
            if self.updateChannels(update=True):
                setSetting('Last_Scan',str(time.time()))
        
        
    def updateChannels(self, channels=[], update=False):
        self.log('updateChannels, channels = %s, update = %s'%(len(channels), update))
        if len(channels) == 0: channels = self.getChannelList()
        unchanged, difference = assertDICT(self.channelList,channels,return_diff=True)
        self.log('updateChannels, unchanged = %s, difference = %s'%(unchanged,len(difference)))
        # if not update and unchanged: return
        # elif update and len(difference) == 0: return
        # if unchanged: return
        self.channelList = channels
        if self.myBuilder.buildService(channels, update): return True
        return False
        
        
    def chkInfo(self):
        if not isCHKInfo() or self.myMonitor.waitForAbort(.1): return False
        return fillInfoMonitor()
        

    def startService(self, silent=False):
        self.log('startService')
        setBusy(False)
        self.serverStopped = False
        self.myMonitor.setPendingChange(False)
        checkPVR()
        
        if not silent: 
            msg = ': %s'%LANGUAGE(30099) if self.myBuilder.m3u.isClient() else ''
            notificationProgress(LANGUAGE(30052)%(msg))
        
        self.updateChannels(self.initalizeChannels())
        self.myConfig.startSpooler()
        
        while not self.myMonitor.abortRequested():
            if   self.chkInfo(): continue # aggressive timing.
            elif self.myMonitor.waitForAbort(2) or self.serverStopped: break
            elif xbmcgui.getCurrentWindowDialogId() in [10140,12000,10126]: # detect upcoming channel change. 
                self.log('settings opened')
                self.myMonitor.setPendingChange(True)
                self.myMonitor.onSettingsChanged()
                continue
            elif self.myMonitor.pendingChange:
                self.log('pending change')
                continue
            self.chkIdle()
            self.chkUpdate()
            
        # restart service after change
        if self.serverStopped:
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
                thread.join(0.5)
            except Exception as e: log("closeThreads, Failed! %s"%(e), xbmc.LOGERROR)
        self.log('closeThreads, exiting %s'%(ADDON_NAME))


if __name__ == '__main__': Service()