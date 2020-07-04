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
from globals import *
from plugin  import Plugin
from config  import Config
from overlay import GUI

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.playingChannelItem = {}
        self.usePlaylist    = bool(getSettingInt('Playback_Method'))
        self.overlayEnabled = getSettingBool('Enable_Overlay')
        self.playerOverlay  = GUI("overlay.xml", ADDON_PATH, "default")
        
        
    def getPlayerTime(self):
        try: return self.getTotalTime()
        except: return 0
        
        
    def getPVRTime(self):
        EpgEventElapsedTime = xbmc.getInfoLabel('PVR.EpgEventElapsedTime(hh:mm:ss)')
        return (sum(x*y for x, y in zip(map(float, EpgEventElapsedTime.split(':')[::-1]), (1, 60, 3600, 86400))))


    def toggleSubtitles(self, state):
        log('Player: toggleSubtitles, state = ' + str(state))
        self.showSubtitles(state)
        

    def onPlayBackSeek(self, seek_time, seek_offset):
        log('Player: onPlayBackSeek, seek_time = %s, seek_offset = %s'%(seek_time,seek_offset))
    

    def onAVStarted(self):
        log('Player: onAVStarted')
        self.playAction()


    def onPlayBackEnded(self):
        log('Player: onPlayBackEnded')
        self.changeAction()
        

    def onPlayBackStopped(self):
        log('Player: onPlayBackStopped')
        self.stopAction()
        
        
    def onPlayBackError(self):
        log('Player: onPlayBackError')
        self.stopAction()
        
        
    def playAction(self):
        log('Player: playAction')
        if not isPseudoTV(): return log('Player: playAction, returning not PseudoTV Live') #isPseudoTV check, todo added logic to exclude other playback sources
        currentChannelItem = getCurrentChannelItem()
        if self.playingChannelItem.get('channelid',-1) == currentChannelItem.get('channelid',random.random()): return log('Player: playAction, returning no channel change')
        self.playingChannelItem = currentChannelItem
        self.playingChannelItem['callback'] = self.myService.myConfig.jsonRPC.matchPVRPath(self.playingChannelItem['channelid'])


    def changeAction(self):
        if self.usePlaylist: return
        callback = self.playingChannelItem['callback']
        log('Player: changeAction, playing = %s'%(callback))
        xbmc.executebuiltin('PlayMedia(%s)'%callback)


    def stopAction(self):
        log('Player: stopAction')
        clearCurrentChannelItem()
        self.closeOverlay()


    def isOverlay(self):
        xbmc.sleep(2000)
        return getProperty('OVERLAY') == 'true'


    def startOverlay(self):
        if not self.overlayEnabled or self.isOverlay(): return
        log('Player: startOverlay')
        self.playerOverlay.show()
    
    
    def closeOverlay(self):
        if not self.isOverlay(): return
        log('Player: closeOverlay')
        self.playerOverlay.close()
    
    
class Monitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.pendingChange  = False
        self.onChangeThread = threading.Timer(0.5, self.onChange)
        
        
    def onNotification(self, sender, method, data):
        log("Monitor: onNotification, sender %s - method: %s  - data: %s" % (sender, method, data))
            
            
    def onSettingsChanged(self):
        if not self.pendingChange: return # only trigger when physical settings are opened
        log('Monitor: onSettingsChanged')
        if self.onChangeThread.isAlive(): self.onChangeThread.cancel() # do not stack threads, create single trigger timer.
        self.onChangeThread = threading.Timer(30.0, self.onChange)
        self.onChangeThread.name = "onChangeThread"
        self.onChangeThread.start()
        
        
    def onChange(self):
        if not self.pendingChange: return # last chance to cancel run.
        log('Monitor: onChange')
        if isBusy(): return self.onSettingsChanged() # delay check. todo build isBusy() to determine scanning or building.
        channelList = self.myService.getChannelList() # build new channelList, then test against last one.
        if not assertDICT(channelList,self.myService.channelList): 
            self.myService.channelList = channelList
            self.myService.updateChannels()
        self.setPendingChange(False)


    def setPendingChange(self, state):
        log('Monitor: setPendingChange, pendingChange = %s'%(state))
        self.pendingChange = state
        

class Service:
    def __init__(self):
        self.myMonitor   = Monitor()
        self.myMonitor.myService = self
        self.myPlayer    = Player()
        self.myPlayer.myService = self
        self.myConfig    = Config(sys.argv)
        self.myConfig.myService = self
        self.myPlugin    = Plugin(sys.argv)
        self.myBuilder   = self.myPlugin.myBuilder
        self.channelList = self.getChannelList()
        self.startService()


    def getChannelList(self):
        return self.myBuilder.createChannelItems()


    def checkIdle(self):
        if xbmc.getGlobalIdleTime() > getSettingInt('Seek_Tolerence'):
            if not self.myPlayer.isPlaying() and not isPseudoTV(): return
            self.myPlayer.startOverlay()
        else:
            self.myPlayer.closeOverlay()


    def chkUpdate(self):
        if self.myMonitor.pendingChange or isBusy(): return
        lastCheck = float(getSetting('Last_Scan') or 0)
        if (time.time() > (lastCheck + UPDATE_OFFSET)): self.updateChannels(self.channelList)
        
        
    def updateChannels(self, channels=None):
        log('Service: updateChannels')
        if channels is None: channels = self.channelList
        self.myBuilder.buildService(channels) #todo stagger builds? only update new channels or endtime check? ie. self.myBuilder.buildService(updated_channels)
        REAL_SETTINGS.setSetting('Last_Scan',str(time.time()))
        
        
    def startService(self):
        log('Service: startService')
        setBusy(False)
        self.myMonitor.setPendingChange(False)
        self.myConfig.startSpooler()
        self.updateChannels()
        
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(5): break
            if xbmcgui.getCurrentWindowDialogId() in [10140,12000]:
                log('Service: settings opened')
                self.myMonitor.setPendingChange(True)
                self.myMonitor.onSettingsChanged()
                continue
            elif self.myMonitor.pendingChange:
                log('Service: pending change')
                continue
            self.checkIdle()
            self.chkUpdate()                
        self.closeThreads()

                
    def closeThreads(self):
        log('Service: closeThreads')
        for thread in threading.enumerate():
            try: 
                if thread.name == "MainThread": continue
                log("closeThreads joining thread %s"%(thread.name))
                thread.cancel()
                thread.join(0.5)
            except Exception as e: log("closeThreads, Failed! %s"%(e), xbmc.LOGERROR)


if __name__ == '__main__': Service()