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
from resources.lib.overlay import GUI

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.pendingStop        = False
        self.playingChannelItem = {'channelid':-1}
        self.usePlaylist        = bool(getSettingInt('Playback_Method'))
        self.overlayEnabled     = getSettingBool('Enable_Overlay')
        self.playerOverlay      = GUI(OVERLAY_FLE, ADDON_PATH, "default")
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getPlayerTime(self):
        try: return self.getTotalTime()
        except: return 0
        
        
    def getPlayerItem(self):
        self.log('getPlayerItem')
        json_query = '{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":%s,"properties":["file","writer","channel","channels","channeltype","mediapath"]}, "id": 1}'%(self.myService.myConfig.jsonRPC.getActivePlayer())
        return sendJSON(json_query).get('result',{}).get('item',{})
        
        
    def getPlaylistItem(self):
        self.log('getPlaylistItem')
        json_query = '{"jsonrpc":"2.0","method":"Playlist.GetItems","params":{"playlistid":%s,"properties":["runtime","title","plot","genre","year","studio","mpaa","season","episode","showtitle","thumbnail","file"]},"id":1}'%(self.myService.myConfig.jsonRPC.getActivePlaylist())
        return sendJSON(json_query).get('result',{}).get('items',{})


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
            currentChannelItem['callback'] = (self.myService.jsonRPC.matchPVRPath(currentChannelId) or self.getPlayerItem().get('mediapath',''))
        
        if lastChannelId == currentChannelId: 
            self.log('playAction, no channel change')
        else:   
            self.playingChannelItem = currentChannelItem
            setCurrentChannelItem(self.playingChannelItem)
        self.log('playAction, lastChannelId = %s, currentChannelId = %s, callback = %s'%(lastChannelId,currentChannelId,currentChannelItem['callback']))


    def changeAction(self):
        if self.usePlaylist: 
            self.pendingStop = True
        else:
            self.pendingStop = False
            setProperty('PseudoTVRunning','False')
            callback = self.playingChannelItem['callback']
            self.log('changeAction, playing = %s'%(callback))
            xbmc.executebuiltin('PlayMedia(%s)'%callback)
        

    def stopAction(self):
        # if self.pendingStop: return
        self.log('stopAction')
        setProperty('PseudoTVRunning','False')
        clearCurrentChannelItem()
        self.closeOverlay()


    def isOverlay(self):
        xbmc.sleep(500) # sleep to catch doModal delay.
        return getProperty('OVERLAY') == 'true'


    def startOverlay(self):
        conditions = [self.overlayEnabled,self.isPlaying(),isPseudoTV()]
        if (False in conditions) or self.isOverlay(): return
        self.log('startOverlay')
        self.playerOverlay.show()
    
    
    def closeOverlay(self):
        if not self.isOverlay(): return
        self.log('closeOverlay')
        self.playerOverlay.close()
    
    
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
        if not self.pendingChange: return # only trigger when physical settings are opened
        self.log('onSettingsChanged')
        if self.onChangeThread.isAlive(): self.onChangeThread.cancel() # do not stack threads, create single trigger timer.
        self.onChangeThread = threading.Timer(30.0, self.onChange)
        self.onChangeThread.name = "onChangeThread"
        self.onChangeThread.start()
        
        
    def onChange(self):
        if not self.pendingChange: return # last chance to cancel run.
        self.log('onChange')
        if isBusy(): return self.onSettingsChanged() # delay check. todo build isBusy() to determine scanning or building.
        channelList   = self.myService.getChannelList() # build new channelList, then test against last one.
        unchanged, difference = assertDICT(channelList,self.myService.channelList,return_diff=True)
        if not unchanged: # check if both lists are the same, ie. unchanged
            self.myService.channelList = channelList
            self.myService.updateChannels(channelList, update=True) #todo only update changed (difference)?
        self.setPendingChange(False)


    def setPendingChange(self, state):
        self.log('setPendingChange, pendingChange = %s'%(state))
        self.pendingChange = state
        

class Service:
    def __init__(self):
        self.wait         = 5 #secs
        self.myMonitor   = Monitor()
        self.myMonitor.myService = self
        self.myPlayer    = Player()
        self.myPlayer.myService = self
        self.myConfig    = Config(sys.argv)
        self.myConfig.myService = self
        self.myPlugin    = Plugin(sys.argv)
        self.myBuilder   = self.myPlugin.myBuilder
        self.channelList = self.getChannelList()
        self.jsonRPC     = self.myBuilder.jsonRPC
        self.sysListitem = xbmcgui.ListItem()
        
        if CLIENT_MODE: 
            self.clientService()
        else: 
            self.startService()

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getChannelList(self):
        self.log('getChannelList')
        return sorted(self.myBuilder.createChannelItems(), key=lambda k: k['number'])
        

    def chkIdle(self):
        if xbmc.getGlobalIdleTime() > getSettingInt('Seek_Tolerance'):
            self.myPlayer.startOverlay()
        else:
            self.myPlayer.closeOverlay()


    def chkUpdate(self):
        if self.myMonitor.pendingChange or isBusy(): return
        lastCheck = float(getSetting('Last_Scan') or 0)
        if (time.time() > (lastCheck + UPDATE_OFFSET)):
            clearProperty("USER_LOG")
            self.updateChannels()
        
        
    def updateChannels(self, channels=None, reloadPVR=False, update=False):
        if channels is None: channels = self.channelList
        self.log('updateChannels, channel count = %s, reloadPVR = %s, update = %s'%(len(channels),reloadPVR,update))
        self.myBuilder.buildService(channels, reloadPVR, update)
        setSetting('Last_Scan',str(time.time()))
        
        
    def chkInfo(self):
        if not getProperty('chkInfo'):
            return False
        self.sysListitem = sysListItem()
        return True
          
          
    def startService(self):
        self.log('startService')
        # notificationDialog(LANGUAGE(30101))
        setBusy(False)
        self.myMonitor.setPendingChange(False)
        self.myConfig.startSpooler()
        self.updateChannels(reloadPVR=True)
        while not self.myMonitor.abortRequested():
            if   self.chkInfo(): continue # aggressive timing.
            elif self.myMonitor.waitForAbort(self.wait): break
            if xbmcgui.getCurrentWindowDialogId() in [10140,12000,10126]: # detect upcoming channel change. 
                self.log('settings opened')
                self.myMonitor.setPendingChange(True)
                self.myMonitor.onSettingsChanged()
                continue
            if self.myMonitor.pendingChange:
                self.log('pending change')
                continue
            self.chkIdle()
            self.chkUpdate()
        self.closeThreads()

                
    def clientService(self):
        self.log('clientService')
        notificationDialog(LANGUAGE(30100))
        setBusy(False)
        self.myMonitor.setPendingChange(False)
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(self.wait): 
                break
            self.chkIdle()
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


if __name__ == '__main__': Service()