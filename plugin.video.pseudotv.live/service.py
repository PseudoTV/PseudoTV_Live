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
        self.overlayWindow      = GUI(OVERLAY_FLE, ADDON_PATH, "default")
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getPlayerTime(self):
        try: return self.getTotalTime()
        except: return 0
        
        
    def getPlayerItem(self, playlist=False):
        self.log('getPlayerItem, playlist = %s'%(playlist))
        if playlist: json_query = '{"jsonrpc":"2.0","method":"Playlist.GetItems","params":{"playlistid":%s,"properties":["runtime","title","plot","genre","year","studio","mpaa","season","episode","showtitle","thumbnail","file"]},"id":1}'%(self.myService.myConfig.jsonRPC.getActivePlaylist())
        else:        json_query = '{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":%s,"properties":["file","writer","channel","channels","channeltype","mediapath"]}, "id": 1}'%(self.myService.myConfig.jsonRPC.getActivePlayer())
        result = sendJSON(json_query).get('result',{})
        return (result.get('item',{}) or result.get('items',{}))
           

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


    def isPlaylist(self):
        return bool(getSettingInt('Playback_Method'))


    def changeAction(self):
        if self.isPlaylist(): 
            self.pendingStop = True
        else:
            self.pendingStop = False
            setProperty('PseudoTVRunning','False')
            callback = self.playingChannelItem['callback']
            self.log('changeAction, playing = %s'%(callback))
            xbmc.executebuiltin('PlayMedia(%s)'%callback)
        

    def stopAction(self):
        # if self.pendingStop: return #playlist triggers false stop at media end, catch and reject call? needs debugging.
        self.log('stopAction')
        setProperty('PseudoTVRunning','False')
        clearCurrentChannelItem()
        self.toggleOverlay(False)


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
        self.myService.serverStop = True
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
        self.serverStop  = False
        self.startService()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


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
            self.updateChannels(update=True)
        
        
    def updateChannels(self, update=False):
        channelList = self.getChannelList() # build new channelList, test against last one.
        unchanged, difference = assertDICT(channelList,self.channelList,return_diff=True)
        self.channelList = channelList #todo only update changed (difference)?              
        self.log('updateChannels, channel count = %s, update = %s'%(len(self.channelList), update))
        self.myBuilder.buildService(self.channelList, update) 
        setSetting('Last_Scan',str(time.time()))
        
        
    def chkInfo(self):
        if not getProperty('chkInfo'): return False
        self.sysListitem = sysListItem()
        return True
          

    def startService(self, silent=False):
        self.log('startService')
        setBusy(False)
        self.serverStop = False
        self.myMonitor.setPendingChange(False)
        checkPVR()
        self.myConfig.startSpooler()
        
        if not silent: 
            notificationProgress(LANGUAGE(30052))
            
        if self.myConfig.predefined.buildChannelList():
            self.updateChannels()
            
        while not self.myMonitor.abortRequested():
            if   self.chkInfo(): continue # aggressive timing.
            elif self.myMonitor.waitForAbort(self.wait) or self.serverStop: break
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
        if self.serverStop:
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


if __name__ == '__main__': Service()