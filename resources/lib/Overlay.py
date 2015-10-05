#   Copyright (C) 2015 Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon
import os, sys, re
import datetime, time, threading, _strptime
import random, traceback


from Playlist import Playlist
from Globals import *
from Channel import Channel
from EPGWindow import EPGWindow
from DVR import DVR
from Ondemand import Ondemand
from APPS import APPS
from ChannelList import ChannelList
from ChannelListThread import ChannelListThread
from FileAccess import FileLock, FileAccess
from Migrate import Migrate
from Artdownloader import *
from Upnp import Upnp
from utils import *
from Migrate import Migrate

try:
    from PIL import Image
    from PIL import ImageEnhance
except:
    REAL_SETTINGS.setSetting("UNAlter_ChanBug","true")
    
try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass

sys.setrecursionlimit(10000)

class MyPlayer(xbmc.Player):
    
    def __init__(self):
        self.log('__init__')
        xbmc.Player.__init__(self, xbmc.PLAYER_CORE_AUTO)
        self.channelList = ChannelList()
        self.stopped = False
        self.ignoreNextStop = False        
        
        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Player: ' + msg, level)
    
    
    def logDebug(self, msg, level = xbmc.LOGDEBUG, notify = False):
        if isDebug() == True:
            log('Player: ' + msg, level) 
            if notify == True:
                DebugNotify(msg)
    
    
    def getPlayerFile(self):
        return (xbmc.Player().getPlayingFile()).replace("\\\\","\\")
    
    
    def getPlayerTime(self):
        try:
            time = int(self.getTime())
        except:
            time = 0
        self.logDebug('getPlayerTime = ' + str(time))
        return time
    
    
    def getPlayerTitle(self):
        try:
            title = xbmc.getInfoLabel('Player.Title')
            if not title:
                title = xbmc.getInfoLabel('VideoPlayer.Title')
        except:
            title = 'NA'
        self.logDebug('getPlayerTitle = ' + title)
        return title
        
    
    def isActuallyPlaying(self):
        ActuallyPlaying = False
        if self.isPlaybackPaused == True:
            return True
            
        if self.isPlaybackValid() == True:
            start_time = self.getPlayerTime()
            start_title = self.getPlayerTitle()            
            xbmc.sleep(251)
            sample_time = self.getPlayerTime()
            sample_title = self.getPlayerTitle()
            if start_title == sample_title:
                if sample_time > start_time:
                    ActuallyPlaying   = True
            else:
                self.isActuallyPlaying()
            self.logDebug('isActuallyPlaying = ' + str(ActuallyPlaying))
        return ActuallyPlaying
            
  
    def isPlaybackValid(self):
        PlaybackStatus = False
        xbmc.sleep(10)
        if self.isPlaying():
            PlaybackStatus = True
        self.logDebug('isPlaybackValid, PlaybackStatus = ' + str(PlaybackStatus))
        return PlaybackStatus
    
    
    def isPlaybackPaused(self):
        Paused = bool(xbmc.getCondVisibility("Player.Paused"))
        self.log('isPlaybackPaused = ' + str(Paused))
        return Paused

    
    def resumePlayback(self):
        self.logDebug('resumePlayback')
        xbmc.sleep(10)
        if self.isPlaybackPaused():
            xbmc.Player().pause()

    
    def onPlayBackPaused(self):
        self.log('onPlayBackPaused')
        self.overlay.Paused()

        
    def onPlayBackResumed(self):
        self.log('onPlayBackResumed')
        self.overlay.Resume()
    
    
    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        # close/reopen window after playback change to correct videowindow bug.
        if getProperty("PTVL.%s_Opened" % self.overlay.isWindowOpen()) == "true" and getProperty("PTVL.VideoWindow") == "true":
            self.log('onPlayBackStarted, Force Window Reload')
            self.overlay.windowSwap(self.overlay.isWindowOpen())

        # if playback starts paused, resume automatically.
        self.resumePlayback()
        if self.isPlaybackValid():
            self.overlay.clearProp()
            if self.overlay.infoOnChange == True and self.overlay.infoOnChangeUnlocked == True:
                self.overlay.waitForVideoPlayback(self.overlay.InfTimer)
            else:
                self.overlay.setShowInfo()
            self.overlay.showChannelLabel(self.overlay.currentChannel)
            
            if self.overlay.UPNP:
                self.overlay.UPNPcontrol('play', self.getPlayerFile(), self.getPlayerTime())
        self.overlay.background.setVisible(False) 
            # devise a way to detect ondemand playback todo
            # file = xbmc.Player().getPlayingFile()
            # file = file.replace("\\\\","\\")
            
            # if self.overlay.OnDemand == False:
                # if int(getProperty("OVERLAY.Chtype")) <= 7 and file[0:4] != 'http':    
                    # if len(getProperty("OVERLAY.Mediapath")) > 0 and (((getProperty("OVERLAY.Mediapath"))[-4:].lower() != 'strm') or ((getProperty("OVERLAY.Mediapath"))[0:6] != 'plugin')):
                        # print file.lower()
                        # print (getProperty("OVERLAY.Mediapath")).lower()
                        # if file.lower() != (getProperty("OVERLAY.Mediapath")).lower():
                            # self.overlay.OnDemand = True  
                # else:
                # if len(getProperty("OVERLAY.Mediapath")) > 0 and len(getProperty("OVERLAY.LastMediapath")) > 0:
                    # if (getProperty("OVERLAY.Mediapath")).lower() != (getProperty("OVERLAY.LastMediapath")).lower():
                        # self.overlay.OnDemand = True    
            # setProperty("OVERLAY.LastMediapath",(getProperty("OVERLAY.Mediapath")))                       
            # self.log('onPlayBackStarted, OnDemand = '+ str(self.overlay.OnDemand))           
            # Close epg after starting ondemand
            # if getProperty("PTVL.EPG_Opened") == "true" and  getProperty("PTVL.VideoWindow") == "true" and self.overlay.OnDemand == True:
                # self.log('onPlayBackStarted, Force Close EPG')
                # self.overlay.myEPG.closeEPG()
            # # Force showinfo ondemand
            # if self.overlay.OnDemand == True:
                # self.overlay.showInfo(self.overlay.InfTimer)
            # self.overlay.setShowInfo()
            
            
    def onDemandEnded(self):
        self.log('onDemandEnded') 
        #Force next playlist item after impromptu ondemand playback
        if self.overlay.OnDemand == True:
            self.overlay.OnDemand = False  
            xbmc.executebuiltin("PlayerControl(SmallSkipForward)")
            
            
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        self.overlay.setWatchedStatus()
        self.onDemandEnded()
        
            
    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        if self.stopped == False:
            self.log('Playback stopped')
            self.onDemandEnded()

            if self.ignoreNextStop == False:
                # start sleeptimer to shutdown pseudotvlive
                if self.overlay.sleepTimeValue == 0:
                    self.overlay.sleepTimer = threading.Timer(1.0, self.overlay.sleepAction)                   
                self.overlay.sleepTimeValue = 1
                self.overlay.startSleepTimer()
                self.stopped = True
            else:
                self.ignoreNextStop = False
            self.overlay.setWatchedStatus()

            
# overlay window to catch events and change channels
class TVOverlay(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.log('__init__')
        # initialize all variables
        self.channels = []
        self.Player = MyPlayer()
        self.Player.overlay = self
        self.inputChannel = -1
        self.channelLabel = [] 
        self.OnNowTitleLst = []   
        self.OnNowArtLst = [] 
        self.ReminderLst = []
        self.lastActionTime = 0  
        self.quickflipCount = 0
        self.actionSemaphore = threading.BoundedSemaphore()
        self.channelThread = ChannelListThread()
        self.channelThread.myOverlay = self 
        self.timeStarted = 0   
        self.infoOnChange = True  
        self.infoOnChangeUnlocked = True  
        self.settingReminder = False
        self.showingPop = False
        self.showingInfo = False
        self.showingMoreInfo = False
        self.showingMenu = False
        self.showingStartover = False  
        self.showingNextAired = False  
        self.showingMenuAlt = False
        self.showingBrowse = False
        self.OnInput = False
        self.DisableOverlay = False
        self.infoOffset = 0
        self.invalidatedChannelCount = 0  
        self.showChannelBug = False
        self.showNextItem = False
        self.notificationLastChannel = 0 
        self.notificationLastShow = 0
        self.notificationShowedNotif = False
        self.isExiting = False
        self.maxChannels = 0
        self.triggercount = 0
        self.notPlayingCount = 0 
        self.lastActionCount = 0
        self.ignoreInfoAction = False
        self.shortItemLength = 120
        self.runningActionChannel = 0
        self.channelDelay = 0
        self.channelbugcolor = CHANBUG_COLOR
        self.showSeasonEpisode = REAL_SETTINGS.getSetting("ShowSeEp") == "true"
        self.InfTimer = INFOBAR_TIMER[int(REAL_SETTINGS.getSetting('InfoTimer'))]
        self.Artdownloader = Artdownloader()
        self.notPlayingAction = 'Up'
        self.ActionTimeInt = float(REAL_SETTINGS.getSetting("ActionTimeInt"))
        self.PlayTimeoutInt = float(REAL_SETTINGS.getSetting("PlayTimeoutInt"))
        self.Browse = ''
        self.MUTE = REAL_SETTINGS.getSetting('enable_mute') == "true"
        self.quickflipEnabled = REAL_SETTINGS.getSetting('quickflip') == "true"
        self.OnDemand = False 
        self.FavChanLst = (REAL_SETTINGS.getSetting("FavChanLst")).split(',')
        self.DirectInput = REAL_SETTINGS.getSetting("DirectInput") == "true"
        setProperty("PTVL.BackgroundLoading_Finished","false") 
        
        if REAL_SETTINGS.getSetting("UPNP1") == "true" or REAL_SETTINGS.getSetting("UPNP2") == "true" or REAL_SETTINGS.getSetting("UPNP3") == "true":
            self.UPNP = True
        else:
            self.UPNP = False
            
        for i in range(3):
            self.channelLabel.append(xbmcgui.ControlImage(50 + (50 * i), 50, 50, 50, IMAGES_LOC + 'solid.png', colorDiffuse = self.channelbugcolor))
            self.addControl(self.channelLabel[i])
            self.channelLabel[i].setVisible(False)
        self.doModal()
        self.log('__init__ return')

        
    def resetChannelTimes(self):
        for i in range(self.maxChannels):
            self.channels[i].setAccessTime(self.timeStarted - self.channels[i].totalTimePlayed)


    # override the doModal function so we can setup everything first
    def onInit(self):
        self.log('onInit')
        self.log('PTVL Version = ' + ADDON_VERSION)   
        self.background = self.getControl(101)
        self.background.setLabel('Please Wait')
        setProperty("OVERLAY.LOGOART",THUMB) 
        self.background.setVisible(True)
        self.getControl(102).setVisible(False)
        self.getControl(104).setVisible(False)
        self.getControl(222).setVisible(False)
        self.getControl(119).setVisible(False)
        self.getControl(130).setVisible(False)
        self.getControl(120).setVisible(False)
        self.channelList = ChannelList() 
        self.Upnp = Upnp()   
        dlg = xbmcgui.Dialog()
            
        try:
            Normal_Shutdown = REAL_SETTINGS.getSetting('Normal_Shutdown') == "true"
        except:
            REAL_SETTINGS.setSetting('Normal_Shutdown', "true")
            Normal_Shutdown = REAL_SETTINGS.getSetting('Normal_Shutdown') == "true"
            
        self.egTrigger('PseudoTV_Live - Starting')            
        # Clear Setting2 for fresh autotune
        if REAL_SETTINGS.getSetting("Autotune") == "true" and REAL_SETTINGS.getSetting("Warning1") == "true":
            self.log('Autotune onInit') 
            try:
                self.getControl(101).setLabel('Initializing, Autotuning')
            except:
                pass
            #Reserve channel check            
            if REAL_SETTINGS.getSetting("reserveChannels") == "false":
                self.log('Autotune not reserved') 
                if getSize(SETTINGS_FLE) > 100:
                    Backup(SETTINGS_FLE, SETTINGS_FLE_PRETUNE)

                    if FileAccess.exists(SETTINGS_FLE_PRETUNE):
                        self.log('Autotune, Back Complete!')
                        f = FileAccess.open(SETTINGS_FLE, "w")
                        f.write('\n')
                        self.log('Autotune, Setting2 Deleted...')
                        f.close()

        if FileAccess.exists(GEN_CHAN_LOC) == False:
            try:
                FileAccess.makedirs(GEN_CHAN_LOC)
            except:
                self.Error('Unable to create the cache directory')
                return

        if FileAccess.exists(MADE_CHAN_LOC) == False:
            try:
                FileAccess.makedirs(MADE_CHAN_LOC)
            except:
                self.Error('Unable to create the storage directory')
                return
                
        if FileAccess.exists(ART_LOC) == False:
            try:
                FileAccess.makedirs(ART_LOC)
            except:
                self.Error('Unable to create the artwork directory')
                return
        
        if REAL_SETTINGS.getSetting("SyncXMLTV_Enabled") == "true" and isDon() == True:  
            self.background.setLabel('Initializing: XMLTV Service')
            SyncXMLTV(REAL_SETTINGS.getSetting('PTVLXML_FORCE') == "true")
            
        if self.UPNP == True:
            self.background.setLabel('Initializing: Video Mirroring')
            self.UPNPcontrol('stop')
            time.sleep(5)
            
        updateDialog = xbmcgui.DialogProgress()
        updateDialog.create("PseudoTV Live", "Initializing")
        self.background.setLabel('Initializing: Channel Configurations')
        self.backupFiles(updateDialog)
        ADDON_SETTINGS.loadSettings()
        
        if CHANNEL_SHARING == True:
            FileAccess.makedirs(LOCK_LOC)
            REAL_SETTINGS.setSetting("IncludeBCTs","false")
            updateDialog.update(70, "Initializing", "Checking Other Instances")
            self.background.setLabel('Initializing: Channel Sharing')
            self.isMaster = GlobalFileLock.lockFile("MasterLock", False)
        else:
            self.isMaster = True

        updateDialog.update(85, "Initializing", "PseudoTV Live")
        self.background.setLabel('Initializing: PseudoTV Live')

        if self.isMaster:
            migratemaster = Migrate()     
            migratemaster.migrate()
            
        # Overylay timers
        self.channelLabelTimer = threading.Timer(2.5, self.hideChannelLabel)
        self.channelLabelTimer.name = "ChannelLabel"
        self.playerTimer = threading.Timer(self.PlayTimeoutInt, self.playerTimerAction)
        self.playerTimer.name = "PlayerTimer"
        
        self.myEPG = EPGWindow("script.pseudotv.live.EPG.xml", ADDON_PATH, Skin_Select)
        self.myDVR = DVR("script.pseudotv.live.DVR.xml", ADDON_PATH, Skin_Select)
        self.myOndemand = Ondemand("script.pseudotv.live.Ondemand.xml", ADDON_PATH, Skin_Select)
        self.myApps = APPS("script.pseudotv.live.Apps.xml", ADDON_PATH, Skin_Select)

        self.myEPG.MyOverlayWindow = self
        self.myDVR.MyOverlayWindow = self
        self.myOndemand.MyOverlayWindow = self
        self.myApps.MyOverlayWindow = self
                    
        # Don't allow any actions during initialization
        self.actionSemaphore.acquire()
        self.timeStarted = time.time() 
        updateDialog.update(95, "Initializing", "Channels")
        self.background.setLabel('Initializing: Channels')
        updateDialog.close()

        if self.readConfig() == False:
            return
        
        self.myEPG.channelLogos = self.channelLogos
        self.maxChannels = len(self.channels)

        if self.maxChannels == 0 and REAL_SETTINGS.getSetting("Autotune") == "false":
            autoTune = False
            dlg = xbmcgui.Dialog()     
                
            if dlg.yesno("No Channels Configured", "Would you like PseudoTV Live to Auto Tune Channels?"):
                REAL_SETTINGS.setSetting("Autotune","true")
                REAL_SETTINGS.setSetting("Warning1","true")
                REAL_SETTINGS.setSetting("MEDIA_LIMIT","1")
                REAL_SETTINGS.setSetting("PVR_Listing","0")
                REAL_SETTINGS.setSetting("autoFindLivePVR","true")
                REAL_SETTINGS.setSetting("autoFindNetworks","true")
                REAL_SETTINGS.setSetting("autoFindMovieGenres","true")
                REAL_SETTINGS.setSetting("autoFindRecent","true")
                autoTune = True
                
                if autoTune:
                    xbmc.executebuiltin('XBMC.AlarmClock( Restarting PseudoTV Live, XBMC.RunScript(' + ADDON_PATH + '/default.py),0.5,true)')
                    self.end()
                    return
            else:
                REAL_SETTINGS.setSetting("Autotune","false")
                REAL_SETTINGS.setSetting("Warning1","false")
                self.Error('Unable to find any channels. \nPlease go to the Addon Settings to configure PseudoTV Live.')
                REAL_SETTINGS.openSettings()
                self.end()
                return 
            del dlg
        else:
            if self.maxChannels == 0:
                self.Error('Unable to find any channels. Please configure the addon.')
                REAL_SETTINGS.openSettings()
                self.end()
                return

        found = False

        for i in range(self.maxChannels):
            if self.channels[i].isValid:
                found = True
                break

        if found == False:
            self.Error("Unable to populate channels. Please verify that you", "have scraped media in your library and that you have", "properly configured channels.")
            return

        # Auto-off startup timer
        if self.sleepTimeValue > 0:
            self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)

        self.notificationTimer = threading.Timer(NOTIFICATION_CHECK_TIME, self.notificationAction)
        
        try:
            if self.forceReset == False:
                self.currentChannel = self.fixChannel(int(REAL_SETTINGS.getSetting("CurrentChannel")))
            else:
                raise exception()
        except:
            self.currentChannel = self.fixChannel(1)
        self.resetChannelTimes()

        if self.backgroundUpdating < 2 or self.isMaster == False:
            self.channelThread.name = "ChannelThread"
            self.channelThread.start()
        else:
            # self.ArtServiceThread = threading.Timer(float(self.InfTimer), self.ArtService)
            # self.ArtServiceThread.name = "ArtServiceThread"
            # self.ArtServiceThread.start()
            setProperty("PTVL.BackgroundLoading_Finished","true")
                
            if REAL_SETTINGS.getSetting("EnableSettop") == "true":
                self.log('onInit, Settop Enabled')
                self.channelThread_Timer = threading.Timer(float(SETTOP_REFRESH), self.Settop)
                self.channelThread_Timer.name = "channelThread_Timer"
                self.channelThread_Timer.start() 
        
        self.background.setVisible(False)   
        if REAL_SETTINGS.getSetting('INTRO_PLAYED') != 'true':    
            self.Player.play(INTRO)
            time.sleep(17)
            REAL_SETTINGS.setSetting("INTRO_PLAYED","true")    
        self.background.setVisible(True)
        
        self.playerTimer.start()
        self.setChannel(self.currentChannel)
        self.startSleepTimer()
        self.startNotificationTimer()
        self.actionSemaphore.release()
        self.loadReminder()
        self.FEEDtoggle()
        REAL_SETTINGS.setSetting('Normal_Shutdown', "false")
        
        # if REAL_SETTINGS.getSetting('StartupMessage') == "false":
            # self.message('')
            # REAL_SETTINGS.setSetting('StartupMessage', 'true')
        
        #Set button labels
        self.getControl(1000).setLabel('Now Watching')
        self.getControl(1001).setLabel('OnNow')
        self.getControl(1002).setLabel('Browse')
        self.getControl(1003).setLabel('Search')
        self.getControl(1004).setLabel('Last Channel')
        self.getControl(1005).setLabel('Favorites')
        self.getControl(1006).setLabel('EPGType')  
        self.getControl(1007).setLabel('Mute')
        self.getControl(1008).setLabel('Subtitle')
        self.getControl(1009).setLabel('Player Settings')
        self.getControl(1010).setLabel('Sleep')
        self.getControl(1011).setLabel('Exit')
        self.log('onInit return')
    

    def Settop(self):
        self.log('Settop')
        setProperty("PTVL.BackgroundLoading_Finished","false")
        self.egTrigger('PseudoTV_Live - Refreshing Channels') 
        curtime = time.time()
        
        if REAL_SETTINGS.getSetting("SyncXMLTV_Enabled") == "true" and isDon() == True:  
            SyncXMLTV(REAL_SETTINGS.getSetting('PTVLXML_FORCE') == "true")
            
        if CHANNEL_SHARING == True and self.isMaster:
            GlobalFileLock.unlockFile('MasterLock')
        GlobalFileLock.close()
        
        if self.isMaster:
            ADDON_SETTINGS.setSetting('LastExitTime', str(int(curtime)))
        
        if self.timeStarted > 0 and self.isMaster:
            validcount = 0
        
            for i in range(self.maxChannels):
                if self.channels[i].isValid:
                    validcount += 1
        
            if validcount > 0:
                for i in range(self.maxChannels):
                    if self.channels[i].isValid:
                        if self.channels[i].mode & MODE_RESUME == 0:
                            ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(int(curtime - self.timeStarted + self.channels[i].totalTimePlayed)))
                        else:
                            if i == self.currentChannel - 1:
                                # Determine pltime...the time it at the current playlist position
                                pltime = 0
                                self.log("position for current playlist is " + str(self.lastPlaylistPosition))
                                for pos in range(self.lastPlaylistPosition):
                                    pltime += self.channels[i].getItemDuration(pos)
                                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(pltime + self.lastPlayTime))
                            else:
                                tottime = 0
                                for j in range(self.channels[i].playlistPosition):
                                    tottime += self.channels[i].getItemDuration(j)
                                tottime += self.channels[i].showTimeOffset
                                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(int(tottime)))
                self.storeFiles()
                
        self.channels = []
        ADDON_SETTINGS.loadSettings()
        
        if CHANNEL_SHARING == True:
            self.isMaster = GlobalFileLock.lockFile("MasterLock", False)
        else:
            self.isMaster = True
        
        self.backupFiles()
        self.timeStarted = time.time()
        self.channels = self.channelList.setupList(True)  
        # self.maxChannels = len(self.channels)   
        self.resetChannelTimes()
        self.log('Settop, self.maxChannels = ' + str(self.maxChannels))
        time.sleep(2)
        
        if self.backgroundUpdating < 2 or self.isMaster == False:
            self.channelThread = ChannelListThread()
            self.channelThread.myOverlay = self
            self.channelThread.name = "ChannelThread"
            self.channelThread.start()   
        # setShowInfo after update to refresh playlist position
        self.setShowInfo()
        if NOTIFY == True:
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Settop Update Started", 1000, THUMB) )

        
    # setup all basic configuration parameters, including creating the playlists that
    # will be used to actually run this thing
    def readConfig(self):
        self.log('readConfig')
        # Sleep setting is in 30 minute increments...so multiply by 30, and then 60 (min to sec)
        self.sleepTimeValue = int(REAL_SETTINGS.getSetting('AutoOff')) * 1800
        self.log('Auto off is ' + str(self.sleepTimeValue))
        self.sleepTimeMode = int(REAL_SETTINGS.getSetting("AutoOff_Mode"))
        self.log('Auto off Mode is ' + str(self.sleepTimeMode))
        self.infoOnChange = REAL_SETTINGS.getSetting("InfoOnChange") == "true"
        self.log('Show info label on channel change is ' + str(self.infoOnChange))
        self.showChannelBug = REAL_SETTINGS.getSetting("ShowChannelBug") == "true"
        self.log('Show channel bug - ' + str(self.showChannelBug))
        self.forceReset = REAL_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.channelResetSetting = REAL_SETTINGS.getSetting('ChannelResetSetting')
        self.log("Channel reset setting - " + str(self.channelResetSetting))
        self.backgroundUpdating = int(REAL_SETTINGS.getSetting("ThreadMode"))
        self.hideShortItems = REAL_SETTINGS.getSetting("HideClips") == "true"
        self.log("Hide Short Items - " + str(self.hideShortItems))
        self.shortItemLength = SHORT_CLIP_ENUM[int(REAL_SETTINGS.getSetting("ClipLength"))]
        self.log("Short item length - " + str(self.shortItemLength))
        self.channelDelay = int(REAL_SETTINGS.getSetting("ChannelDelay")) * 250
        
        if REAL_SETTINGS.getSetting("EnableSettop") == "true":
            self.backgroundUpdating = 0
            
        if int(REAL_SETTINGS.getSetting("EnableComingUp")) > 0:
            self.showNextItem = True
            
        self.channelLogos = LOGO_LOC
        if FileAccess.exists(self.channelLogos) == False:
            FileAccess.makedirs(self.channelLogos)
        self.log('Channel logo folder - ' + self.channelLogos)
        
        self.channelList = ChannelList()
        self.channelList.myOverlay = self
        self.channels = self.channelList.setupList()

        if self.channels is None:
            self.log('readConfig No channel list returned')
            self.end()
            return False

        self.Player.stop()
        self.log('readConfig return')
        return True

        
    # handle fatal errors: log it, show the dialog, and exit
    def Error(self, line1, line2 = '', line3 = ''):
        self.log('FATAL ERROR: ' + line1 + " " + line2 + " " + line3, xbmc.LOGFATAL)
        dlg = xbmcgui.Dialog()
        dlg.ok('Error', line1, line2, line3)
        del dlg
        self.end()


    def backupFiles(self, updatedlg=False):
        self.log('backupFiles')

        if CHANNEL_SHARING == False:
            return
            
        if updatedlg:
            updatedlg.update(1, "Initializing", "Copying Channels...")
        realloc = REAL_SETTINGS.getSetting('SettingsFolder')
        FileAccess.copy(realloc + '/settings2.xml', SETTINGS_LOC + '/settings2.xml')
        realloc = xbmc.translatePath(os.path.join(realloc, 'cache')) + '/'

        for i in range(999):
            FileAccess.copy(realloc + 'channel_' + str(i) + '.m3u', CHANNELS_LOC + 'channel_' + str(i) + '.m3u')
            if updatedlg:
                updatedlg.update(int(i * .07) + 1, "Initializing", "Copying Channels...")

                
    def storeFiles(self):
        self.log('storeFiles')

        if CHANNEL_SHARING == False:
            return

        realloc = REAL_SETTINGS.getSetting('SettingsFolder')
        FileAccess.copy(SETTINGS_LOC + '/settings2.xml', realloc + '/settings2.xml')
        realloc = xbmc.translatePath(os.path.join(realloc, 'cache')) + '/'

        for i in range(self.maxChannels):
            if self.channels[i].isValid:
                FileAccess.copy(CHANNELS_LOC + 'channel_' + str(i) + '.m3u', realloc + 'channel_' + str(i) + '.m3u')

                
    def message(self, data):
        self.log('Dialog message: ' + data)
        dlg = xbmcgui.Dialog()
        dlg.ok('PseudoTV Live Announcement:', data)
        del dlg


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('TVOverlay: ' + msg, level)

        
    def logDebug(self, msg, level = xbmc.LOGDEBUG, notify = False):
        if isDebug() == True:
            log('TVOverlay: ' + msg, level) 
            if notify == True:
                DebugNotify(msg)

            
    def setOnNowArt(self):
        self.log('setOnNowArt')
        try:    
            pos = self.list.getSelectedPosition()
            id = str(self.channelList.getEnhancedIDs(self.OnNowArtLst[pos][0], (self.channelList.cleanLabels(self.OnNowArtLst[pos][1])).split('| ')[1], self.OnNowArtLst[pos][2], self.OnNowArtLst[pos][5]))
            self.setArtwork(self.OnNowArtLst[pos][0], self.OnNowArtLst[pos][3], self.OnNowArtLst[pos][4], id, self.OnNowArtLst[pos][6], self.OnNowArtLst[pos][7], self.OnNowArtLst[pos][8], self.OnNowArtLst[pos][9], self.OnNowArtLst[pos][10])   
        except Exception,e:
            self.log('setOnNowArt, Failed!, ' + str(e))
            pass  
  
  
    def setOnNow(self):
        self.log('setOnNow')   
        self.OnNowTitleLst = []        
        self.OnNowArtLst = []
        curtime = time.time()
        ChannelChk = 0 
        for Channel in range(999):
            try:
                chtype = self.getChtype(Channel + 1)
                timedif = (curtime - self.channels[Channel].lastAccessTime)
                ChannelChk = int(self.channels[Channel].getCurrentDuration())
                if ChannelChk == 0:
                    raise exception()
                    
                #same logic as in setchannel; loop till we get the current show
                if chtype == 8 and len(self.channels[Channel].getItemtimestamp(0)) > 0:
                    self.channels[Channel].setShowPosition(0)
                    tmpDate = self.channels[Channel].getItemtimestamp(0)
                     
                    try:#sloppy fix, for threading issue with strptime.
                        t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
                    except:
                        t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
                     
                    epochBeginDate = time.mktime(t)
                    position = self.channels[Channel].playlistPosition

                    #loop till we get to the current show this is done to display the correct show on the info listing for Live TV types
                    while epochBeginDate + self.channels[Channel].getCurrentDuration() < time.time():
                        epochBeginDate += self.channels[Channel].getCurrentDuration()
                        self.channels[Channel].addShowPosition(1)
                        position = self.channels[Channel].playlistPosition
                else:
                    position = self.channels[Channel].playlistPosition
 
                label = self.channels[Channel].getItemTitle(position)  
                if not label:
                    self.log('setOnNow, no label')
                    raise exception()
                    
                year, label, showtitle = getTitleYear(label)
                mediapath = (self.channels[Channel].getItemFilename(position))
                myLiveID = self.channels[Channel].getItemLiveID(position)
                genre = self.channels[Channel].getItemLiveID(position)
                ChanColor = (self.channelbugcolor).replace('0x','')
                
                if self.isChanFavorite(Channel+1):
                    ChanColor = 'gold'   
                title = ("[COLOR=%s][B]%d|[/B][/COLOR] %s" % (ChanColor, Channel+1, label))
                self.OnNowTitleLst.append(title)
                
                # prepare artwork
                chname = self.getChname(Channel)
                type = (self.channelList.unpackLiveID(myLiveID))[0]
                id = (self.channelList.unpackLiveID(myLiveID))[1]
                dbid, epid = splitDBID((self.channelList.unpackLiveID(myLiveID))[2])
                rating = (self.channelList.unpackLiveID(myLiveID))[5]
                mpath = getMpath(mediapath)
                Art = [type, title, year, chtype, chname, id, dbid, mpath, EXTtype(getProperty("OVERLAY.type3")), 'type3ART', 'OVERLAY']
                self.logDebug('setOnNow, Art = ' + str(Art))
                self.OnNowArtLst.append(Art)
            except:
                pass
        self.log('setOnNow return')     


    def channelUp(self):
        self.log('channelUp')
        self.notPlayingAction = 'Up'
        if self.maxChannels == 1:
            return           
        self.setChannel(self.fixChannel(self.currentChannel + 1), self.quickflipEnabled)
        self.log('channelUp return')
        
        
    def channelDown(self):
        self.log('channelDown')
        self.notPlayingAction = 'Down'     
        if self.maxChannels == 1:
            return
        self.setChannel(self.fixChannel(self.currentChannel - 1, False), self.quickflipEnabled)      
        self.log('channelDown return')  
            

    def lastActionTrigger(self, force=None):
        self.lastActionCount += 1
        if self.lastActionCount == 3:
            self.lastActionTrigger('Last')
        elif self.lastActionCount > 3:
            return
        if force:
            self.notPlayingAction = force
        self.logDebug("lastActionTrigger = " + self.notPlayingAction)
        if self.notPlayingAction == 'Down':
            self.background.setLabel("Changing Channel Down")
            self.setChannel(self.fixChannel(self.currentChannel - 1, False), self.quickflipEnabled)
        elif self.notPlayingAction == 'Last':
            self.background.setLabel("Returning to Previous Channel")
            self.setChannel(self.fixChannel(self.getLastChannel()))
        else:
            self.background.setLabel("Changing Channel Up")
            self.setChannel(self.fixChannel(self.currentChannel + 1, True), self.quickflipEnabled)
        
      
    def setInvalidateChannel(self, channel=None):
        if not channel:
            channel = self.currentChannel
        self.channels[channel - 1].isValid = False
                    
                    
    def InvalidateChannel(self, channel):
        self.log("InvalidateChannel" + str(channel))
        if channel < 1 or channel > self.maxChannels:
            self.log("InvalidateChannel invalid channel " + str(channel))
            return
        self.setInvalidateChannel(channel)
        self.invalidatedChannelCount += 1
        if self.invalidatedChannelCount > 3:
            self.Error("Exceeded 3 invalidated channels. Exiting.")
            return
        remaining = 0
        for i in range(self.maxChannels):
            if self.channels[i].isValid:
                remaining += 1
        if remaining == 0:
            self.Error("No channels available. Exiting.")
            return
        self.setChannel(self.fixChannel(channel))
    
    
    # return a valid channel in the proper range
    def fixChannel(self, channel, increasing = True):
        # correct issue with setlabel which is returning -1 todo track down issue
        if channel == -1:
            return
        while channel < 1 or channel > self.maxChannels:
            if channel < 1: channel = self.maxChannels + channel
            if channel > self.maxChannels: channel -= self.maxChannels     
        if increasing:
            direction = 1
        else:
            direction = -1
        if self.channels[channel - 1].isValid == False:
            return self.fixChannel(channel + direction, increasing)
        return channel
        
            
    # set the channel, the proper show offset, and time offset
    def setChannel(self, channel, quickflip=False):
        self.log('setChannel, channel = ' + str(channel))
        if channel == -1:
            return
        elif self.currentChannel != self.getLastChannel():
            self.setLastChannel()

        self.notPlayingCount = 0 
        self.background.setVisible(True)
        self.getControl(102).setVisible(False)
        self.getControl(120).setVisible(False)
        self.getControl(103).setImage('NA.png')
        timedif = 0
        self.seektime = 0
        self.infoOffset = 0
        self.quickflipCount = 0
        self.lastActionTime = 0
        
        if self.OnDemand == True:
            self.OnDemand = False
        self.runActions(RULES_ACTION_OVERLAY_SET_CHANNEL, channel, self.channels[channel - 1])

        if self.Player.stopped:
            self.log('setChannel, player already stopped', xbmc.LOGERROR);
            return

        if channel < 1 or channel > self.maxChannels:
            self.log('setChannel, invalid channel ' + str(channel), xbmc.LOGERROR)
            return

        if self.channels[channel - 1].isValid == False:
            self.log('setChannel, channel not valid ' + str(channel), xbmc.LOGERROR)
            return

        self.setWatchedStatus()
        # first of all, save playing state, time, and playlist offset for the currently playing channel
        if self.Player.isPlaying():
            chtype_old = int(ADDON_SETTINGS.getSetting('Channel_' + str(self.currentChannel) + '_type'))
            if chtype_old != 8 and chtype_old != 9 and channel != self.currentChannel:
                self.channels[self.currentChannel - 1].setPaused(xbmc.getCondVisibility('Player.Paused'))
                # Automatically pause in serial mode
                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE > 0:
                    self.channels[self.currentChannel - 1].setPaused(True)
                self.channels[self.currentChannel - 1].setShowTime(self.Player.getTime())
                self.channels[self.currentChannel - 1].setShowPosition(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition())
                self.channels[self.currentChannel - 1].setAccessTime(time.time())
            else:
                self.channels[self.currentChannel - 1].setPaused(False)
        self.currentChannel = channel      
        chname = self.getChname(self.currentChannel - 1)
        chtype = self.getChtype(self.currentChannel)
        self.background.setLabel(('Loading: %s') % chname)
        
        if FileAccess.exists(os.path.join(self.channelLogos,chname + '.png')):
            chlogo = xbmc.translatePath(os.path.join(self.channelLogos,chname + '.png'))
        else:
            chlogo = 'logo.png'
        setProperty("OVERLAY.LOGOART",chlogo)
                             
        if chname == 'PseudoCinema':
            self.Cinema_Mode = True
        else:
            self.Cinema_Mode = False
                 
        # now load the proper channel playlist
        xbmc.PlayList(xbmc.PLAYLIST_MUSIC).clear()
        self.logDebug("setChannel, loading playlist = " + ascii(self.channels[channel - 1].fileName));
        if xbmc.PlayList(xbmc.PLAYLIST_MUSIC).load(self.channels[channel - 1].fileName) == False:
            self.log("setChannel, Error loading playlist", xbmc.LOGERROR)
            self.InvalidateChannel(channel)
            return
            
        # Disable auto playlist shuffling if it's on
        if xbmc.getInfoLabel('Playlist.Random').lower() == 'random':
            self.log('setChannel, Random on.  Disabling.')
            xbmc.PlayList(xbmc.PLAYLIST_MUSIC).unshuffle()
        
        # Enable auto playlist repeat
        self.log("setChannel, repeatall enabled");
        xbmc.executebuiltin("PlayerControl(repeatall)")
        
        curtime = time.time()
        timedif = (curtime - self.channels[self.currentChannel - 1].lastAccessTime)
        if self.channels[self.currentChannel - 1].isPaused == False:
            # adjust the show and time offsets to properly position inside the playlist
            #for Live TV get the first item in playlist convert to epoch time  add duration until we get to the current item
            if chtype == 8 and len(self.channels[self.currentChannel - 1].getItemtimestamp(0)) > 0:
                self.channels[self.currentChannel - 1].setShowPosition(0)
                tmpDate = self.channels[self.currentChannel - 1].getItemtimestamp(0)
                self.logDebug("setChannel, overlay tmpdate " + str(tmpDate))
                
                try:#sloppy fix, for threading issue with strptime.
                    t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
                except:
                    t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')

                epochBeginDate = time.mktime(t)
                #beginDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
                #index till we get to the current show
                while epochBeginDate + self.channels[self.currentChannel - 1].getCurrentDuration() <  curtime:
                    self.logDebug('setChannel, livetv while loop')
                    self.logDebug('setChannel, ' + str(epochBeginDate + self.channels[self.currentChannel - 1].getCurrentDuration() ) + ' < ' + str(curtime))
                    self.logDebug('setChannel, epoch '+ str(epochBeginDate) + ', ' + 'time ' + str(curtime))
                    epochBeginDate += self.channels[self.currentChannel - 1].getCurrentDuration()
                    self.channels[self.currentChannel - 1].addShowPosition(1)
            else:#loop for other channel types
                while self.channels[self.currentChannel - 1].showTimeOffset + timedif > self.channels[self.currentChannel - 1].getCurrentDuration():
                    self.logDebug('setChannel, everything while loop')
                    self.logDebug('setChannel, ' + str(self.channels[self.currentChannel - 1].showTimeOffset + timedif) + ' > ' + str(self.channels[self.currentChannel - 1].getCurrentDuration()))
                    timedif -= self.channels[self.currentChannel - 1].getCurrentDuration() - self.channels[self.currentChannel - 1].showTimeOffset
                    self.channels[self.currentChannel - 1].addShowPosition(1)
                    self.channels[self.currentChannel - 1].setShowTime(0)
        
        mediapath = self.channels[self.currentChannel - 1].getItemFilename(self.channels[self.currentChannel - 1].playlistPosition)
        if quickflip == True and self.maxChannels > 1:
            self.log("setChannel, about to quickflip");
            self.logDebug("setChannel, chtype = " + str(chtype))
            if self.quickflipCount > int(self.maxChannels/4):
                self.quickflipEnabled = False
                self.Error("Quickflip temporarily disabled")
            elif mediapath[-4:].lower() == 'strm' or (chtype == 15 and mediapath.lower().startswith(('plugin'))):
                self.background.setLabel(('Quickflip: %s') % chname)
                self.quickflipCount += 1
                self.lastActionTrigger()
                return
           
        # First, check to see if the video is a strm
        if chtype in [8,9,15] or mediapath[-4:].lower() == 'strm':
            self.Player.ignoreNextStop = True
            self.log("setChannel, ignoreNextStop")
        xbmc.sleep(self.channelDelay)  
        
        # Mute the channel before changing
        if self.MUTE:
            self.log("setChannel, about to mute");
            xbmc.executebuiltin("Mute()");
                    
        if mediapath.startswith('plugin') and chtype in [8,9]:      
            if not mediapath.startswith('PlayMedia'):
                mediapath = ('PlayMedia('+mediapath+')')
            if mediapath.startswith('PlayMedia'):
                self.playsetresolved(mediapath, 'PlayMedia')
            # else:
                # self.playsetresolved(mediapath)
        else:
            setProperty("PTVL.Current_PlaylistPosition",str(self.channels[self.currentChannel - 1].playlistPosition))
            self.Player.playselected(int(getProperty("PTVL.Current_PlaylistPosition")))
        self.log("setChannel, playing file = " + ascii(mediapath));
        
        # set the time offset
        self.channels[self.currentChannel - 1].setAccessTime(curtime)
        # set the show offset
        if self.channels[self.currentChannel - 1].isPaused:
            self.channels[self.currentChannel - 1].setPaused(False)
            
            try:
                self.Player.seekTime(self.channels[self.currentChannel - 1].showTimeOffset)
                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE == 0:
                    self.Player.pause()
                    if self.waitForVideoPaused() == False:
                        xbmc.executebuiltin("Mute()");
                        return
            except:
                self.log('setChannel, Exception during seek on paused channel', xbmc.LOGERROR)
        else:       
            if chtype != 8 and chtype != 9 and not mediapath.startswith('PlayMedia'):
                self.log("setChannel, about to seeking")
                seektime1 = self.channels[self.currentChannel - 1].showTimeOffset + timedif + int((time.time() - curtime))
                seektime2 = self.channels[self.currentChannel - 1].showTimeOffset + timedif
                overtime = float((int(self.channels[self.currentChannel - 1].getItemDuration(self.channels[self.currentChannel - 1].playlistPosition))/10)*int(REAL_SETTINGS.getSetting("StreamOverTime")))
                startovertime = float((int(self.channels[self.currentChannel - 1].getItemDuration(self.channels[self.currentChannel - 1].playlistPosition))/10)*int(REAL_SETTINGS.getSetting("StartOverTime")))
                self.logDebug("setChannel, seektime1 = " + str(seektime1))
                self.logDebug("setChannel, seektime2 = " + str(seektime2))
                self.logDebug("setChannel, overtime = " + str(overtime))
                self.logDebug("setChannel, startovertime = " + str(startovertime))
                
                if mediapath[-4:].lower() == 'strm' or chtype == 15:
                    self.seektime = self.SmartSeek(mediapath, seektime1, seektime2, overtime)
                else:
                    try:
                        self.Player.seekTime(seektime1)
                        self.seektime = seektime1
                        self.log("setChannel, using seektime1")
                    except:
                        self.log("setChannel, Unable to set proper seek time, trying different value")
                        try:
                            self.Player.seekTime(seektime2)
                            self.seektime = seektime2
                            self.log("setChannel, using seektime2")
                        except:
                            self.log('setChannel, Exception during seek', xbmc.LOGERROR)
                            
                if self.seektime > startovertime: 
                    self.toggleShowStartover(True)
                else:
                    self.toggleShowStartover(False)
                
        if self.UPNP:
            self.UPNPcontrol('play', mediapath, self.seektime)
        
        # Unmute
        if self.MUTE:
            self.log("setChannel, Finished, unmuting");
            xbmc.executebuiltin("Mute()");
            
        self.logDebug("setChannel,self.seektime = " + str(self.seektime))
        self.getControl(517).setLabel(str(self.Player.getPlayerTime()))
        self.lastActionTime = time.time()
        self.runActions(RULES_ACTION_OVERLAY_SET_CHANNEL_END, channel, self.channels[channel - 1])   
        self.infoOnChangeUnlocked = True
        self.egTrigger('PseudoTV_Live - Loading: %s' % chname)
        self.log('setChannel, setChannel return')
               
        
    def SmartSeek(self, mediapath, seektime1, seektime2, overtime):
        self.log("SmartSeek")
        seektime = 0
        if seektime1 < overtime:
            try:
                self.Player.seekTime(seektime1)
                seektime = seektime1
                self.logDebug("seektime1 = " + str(seektime))
            except:
                self.log("Unable to set proper seek time, trying different value")
                if seektime2 < overtime:
                    try:
                        self.Player.seekTime(seektime2)
                        seektime = seektime2
                        self.logDebug("seektime2 = " + str(seektime))
                    except:
                        self.log('Exception during seek', xbmc.LOGERROR)
                        seektime = 0
        if seektime == 0 and DEBUG == 'true':
            self.logDebug('overtime ' + str(overtime))
            DebugNotify("Overriding Seektime")
        return seektime    

        
    # def UPNPcontrol(self, func, file='', seektime=0):
        # self.log('UPNPcontrol') 
        # try:
            # self.UPNPcontrolTimer = threading.Timer(float(REAL_SETTINGS.getSetting("UPNP_OFFSET")), self.UPNPcontrol_thread, [func, file, seektime])
            # self.UPNPcontrolTimer.name = "UPNPcontrol"       
            # if self.UPNPcontrolTimer.isAlive():
                # self.UPNPcontrolTimer.cancel()
            # self.UPNPcontrolTimer.start()
        # except Exception,e:
            # self.log('UPNPcontrol, Failed!, ' + str(e))
            # pass 
    

    def UPNPcontrol(self, func, file='', seektime=0):
        if func == 'play':
            self.PlayUPNP(file, seektime)
        elif func == 'stop':
            self.StopUPNP()
        elif func == 'resume':
            self.ResumeUPNP()
        elif func == 'pause':
            self.PauseUPNP()
        elif func == 'rwd':
            self.RWUPNP()
        elif func == 'fwd':
            self.FFUPNP()

              
    def FFUPNP(self):
        self.log("FFUPNP")
        if REAL_SETTINGS.getSetting("UPNP1") == "true":
            self.log('onAction, UPNP1 FF')
            self.Upnp.FFUPNP(IPP1)
        if REAL_SETTINGS.getSetting("UPNP2") == "true":
            self.log('onAction, UPNP2 FF')
            self.Upnp.FFUPNP(IPP2)
        if REAL_SETTINGS.getSetting("UPNP3") == "true":
            self.log('onAction, UPNP3 FF')
            self.Upnp.FFUPNP(IPP3)
        
        
    def RWUPNP(self):
        self.log("RWUPNP")
        if REAL_SETTINGS.getSetting("UPNP1") == "true":
            self.log('onAction, UPNP1 RW')
            self.Upnp.RWUPNP(IPP1)
        if REAL_SETTINGS.getSetting("UPNP2") == "true":
            self.log('onAction, UPNP2 RW')
            self.Upnp.RWUPNP(IPP2)
        if REAL_SETTINGS.getSetting("UPNP3") == "true":
            self.log('onAction, UPNP3 RW')
            self.Upnp.RWUPNP(IPP3)
    
    def PauseUPNP(self):
        self.log("PauseUPNP")
        if REAL_SETTINGS.getSetting("UPNP1") == "true":
            self.Upnp.PauseUPNP(IPP1)
        if REAL_SETTINGS.getSetting("UPNP2") == "true":
            self.Upnp.PauseUPNP(IPP2)
        if REAL_SETTINGS.getSetting("UPNP3") == "true":
            self.Upnp.PauseUPNP(IPP3)
    

    def ResumeUPNP(self):
        self.log("ResumeUPNP")
        if REAL_SETTINGS.getSetting("UPNP1") == "true":
            self.Upnp.ResumeUPNP(IPP1)
        if REAL_SETTINGS.getSetting("UPNP2") == "true":
            self.Upnp.ResumeUPNP(IPP2)
        if REAL_SETTINGS.getSetting("UPNP3") == "true":
            self.Upnp.ResumeUPNP(IPP3)
    
    
    def PlayUPNP(self, file, seektime):
        self.log("PlayUPNP")
        file = file.replace("\\\\","\\")
        try:
            if REAL_SETTINGS.getSetting("UPNP1") == "true":
                self.log('UPNP1 Sharing')
                self.Upnp.SendUPNP(IPP1, file, seektime)
            if REAL_SETTINGS.getSetting("UPNP2") == "true":
                self.log('UPNP2 Sharing')
                self.Upnp.SendUPNP(IPP2, file, seektime)
            if REAL_SETTINGS.getSetting("UPNP3") == "true":
                self.log('UPNP3 Sharing')
                self.Upnp.SendUPNP(IPP3, file, seektime)
        except:
            pass 

            
    def StopUPNP(self):
        self.log("StopUPNP")
        try:
            if REAL_SETTINGS.getSetting("UPNP1") == "true":
                self.Upnp.StopUPNP(IPP1)
            if REAL_SETTINGS.getSetting("UPNP2") == "true":
                self.Upnp.StopUPNP(IPP2)
            if REAL_SETTINGS.getSetting("UPNP3") == "true":
                self.Upnp.StopUPNP(IPP3)
        except:
            pass
              
              
    def waitForVideoPlayback(self, timer):
        self.log("waitForVideoPlayback")           
        while self.Player.isActuallyPlaying() == False:
            xbmc.sleep(1)
        self.showInfo(timer)
        self.infoOnChangeUnlocked = False
              
              
    def waitForVideoPaused(self):
        self.log('waitForVideoPaused')
        sleeptime = 0
        while sleeptime < TIMEOUT:
            xbmc.sleep(100)
            if self.Player.isPlaying():
                if xbmc.getCondVisibility('Player.Paused'):
                    break
            sleeptime += 100
        else:
            self.log('Timeout waiting for pause', xbmc.LOGERROR)
            return False
        self.log('waitForVideoPaused return')
        return True

        
    def setShowInfo(self):
        self.log('setShowInfo')
        chtype = self.getChtype(self.currentChannel)
        
        if self.infoOffset > 0:
            self.getControl(502).setLabel('COMING UP:') 
            self.getControl(515).setVisible(False)    
        elif self.infoOffset < 0:
            self.getControl(502).setLabel('ALREADY SEEN:') 
            self.getControl(515).setVisible(False)    
        elif self.infoOffset == 0:
            self.getControl(502).setLabel('NOW WATCHING:')
            self.getControl(515).setVisible(True)    

        if self.OnDemand == True:
            position = -999
            mediapath = self.Player.getPlayingFile()
        
        # elif chtype not in [0,2,4,5] and self.hideShortItems and self.infoOffset != 0:
        elif self.hideShortItems and self.infoOffset != 0:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
            curoffset = 0
            modifier = 1
            if self.infoOffset < 0:
                modifier = -1

            while curoffset != abs(self.infoOffset):
                position = self.channels[self.currentChannel - 1].fixPlaylistIndex(position + modifier)
                if self.channels[self.currentChannel - 1].getItemDuration(position) >= self.shortItemLength:
                    curoffset += 1    
                    
            mediapath = (self.channels[self.currentChannel - 1].getItemFilename(position))
        else:
            #same logic as in setchannel; loop till we get the current show
            if chtype == 8 and len(self.channels[self.currentChannel - 1].getItemtimestamp(0)) > 0:
                self.channels[self.currentChannel - 1].setShowPosition(0)
                tmpDate = self.channels[self.currentChannel - 1].getItemtimestamp(0)
                 
                try:#sloppy fix, for threading issue with strptime.
                    t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
                except:
                    t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
 
                epochBeginDate = time.mktime(t)
                position = self.channels[self.currentChannel - 1].playlistPosition
                #beginDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
                #loop till we get to the current show this is done to display the correct show on the info listing for Live TV types
                
                while epochBeginDate + self.channels[self.currentChannel - 1].getCurrentDuration() <  time.time():
                    epochBeginDate += self.channels[self.currentChannel - 1].getCurrentDuration()
                    self.channels[self.currentChannel - 1].addShowPosition(1)
                    position = self.channels[self.currentChannel - 1].playlistPosition
            else: #original code
                position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + self.infoOffset
            mediapath = (self.channels[self.currentChannel - 1].getItemFilename(position))   
        self.log('setShowInfo, setshowposition = ' + str(position))  
        chname = self.getChname(self.currentChannel - 1)
        chnum = str(self.currentChannel)
        self.SetMediaInfo(chtype, chname, chnum, mediapath, position)
        
        
    def SetMediaInfo(self, chtype, chname, chnum, mediapath, position, tmpstr=None):
        self.log('SetMediaInfo')
        mpath = getMpath(mediapath)
                
        #setCore props
        setProperty("OVERLAY.Chtype",str(chtype))
        setProperty("OVERLAY.Mediapath",mediapath)
        setProperty("OVERLAY.Chname",chname)
        setProperty("OVERLAY.Chnum",chnum)
        setProperty("OVERLAY.Mpath",mpath)  
        
        #OnDemand Set Player info, else Playlist
        if position == -999:
            if tmpstr != None:
                tmpstr = tmpstr.split('//')
                title = tmpstr[0]
                SEtitle = ('[COLOR=%s][B]OnDemand[/B][/COLOR]' % ((self.channelbugcolor).replace('0x','')))
                Description = tmpstr[2]
                genre = tmpstr[3]
                timestamp = tmpstr[4]
                LiveID = self.channelList.unpackLiveID(tmpstr[5])
                self.getControl(506).setImage(IMAGES_LOC + 'ondemand.png')
                if self.showChannelBug == True:
                    self.getControl(103).setImage(self.Artdownloader.FindBug('0','OnDemand'))
                try:
                    SetProperty('OVERLAY.type1ART',(IMAGES_LOC + 'ondemand.png'))
                    SetProperty('OVERLAY.type2ART',(IMAGES_LOC + 'ondemand.png'))
                except:
                    pass
            else:
                self.getTMPSTRTimer = threading.Timer(0.1, self.getTMPSTR_Thread, [chtype, chname, chnum, mediapath, position])
                self.getTMPSTRTimer.name = "getTMPSTRTimer"               
                if self.getTMPSTRTimer.isAlive():
                    self.getTMPSTRTimer.cancel()
                self.getTMPSTRTimer.start()  
                return
        else:
            title = (self.channels[self.currentChannel - 1].getItemTitle(position))
            SEtitle = self.channels[self.currentChannel - 1].getItemEpisodeTitle(position)
            Description = (self.channels[self.currentChannel - 1].getItemDescription(position))
            genre = (self.channels[self.currentChannel - 1].getItemgenre(position))
            timestamp = (self.channels[self.currentChannel - 1].getItemtimestamp(position))
            myLiveID = (self.channels[self.currentChannel - 1].getItemLiveID(position))
            LiveID = self.channelList.unpackLiveID(myLiveID)

            if FileAccess.exists(self.channelLogos + (self.channels[self.currentChannel - 1].name) + '.png'):
                self.getControl(506).setImage(self.channelLogos + (self.channels[self.currentChannel - 1].name) + '.png') 
            else:
                self.getControl(506).setImage('logo.png')
        try:
            SEinfo = SEtitle.split(' -')[0]
            season = int(SEinfo.split('x')[0])
            episode = int(SEinfo.split('x')[1])
        except:
            season = 0
            episode = 0   
        try:
            if self.showSeasonEpisode and season != 0 and episode != 0:
                eptitles = SEtitle.split('- ')
                eptitle = (eptitles[1] + (' - ' + eptitles[2] if len(eptitles) > 2 else ''))
                swtitle = ('S' + ('0' if season < 10 else '') + str(season) + 'E' + ('0' if episode < 10 else '') + str(episode) + ' - ' + (eptitle)).replace('  ',' ')
            else:
                swtitle = SEtitle   
        except:
            swtitle = SEtitle
        
        self.getControl(503).setLabel((title).replace("*NEW*",""))
        self.getControl(504).setLabel(swtitle)
        self.getControl(505).setLabel(Description)

        ##LIVEID##
        type = LiveID[0]
        id = LiveID[1]
        dbid, epid = splitDBID(LiveID[2])
        playcount = int(LiveID[4])  
        rating = LiveID[5]
        year, title, showtitle = getTitleYear(title)
        
        # SetProperties
        setProperty("OVERLAY.TimeStamp",timestamp)
        self.setProp(showtitle, year, chtype, id, genre, rating, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, playcount, season, episode)
        
            
    # Display the current channel based on self.currentChannel.
    # Start the timer to hide it.
    def showChannelLabel(self, channel):
        self.log('showChannelLabel ' + str(channel))
        if self.channelLabelTimer.isAlive():
            self.channelLabelTimer.cancel()
            self.channelLabelTimer = threading.Timer(2.5, self.hideChannelLabel)
            self.channelLabelTimer.name = "ChannelLabel"

        tmp = self.inputChannel
        self.inputChannel = tmp
        curlabel = 0
        if channel > 99:
            if FileAccess.exists(IMAGES_LOC):
                self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str(channel // 100) + '.png')
            self.channelLabel[curlabel].setVisible(True)
            curlabel += 1

        if channel > 9:
            if FileAccess.exists(IMAGES_LOC):
                self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str((channel % 100) // 10) + '.png')
            self.channelLabel[curlabel].setVisible(True)
            curlabel += 1

        self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str(channel % 10) + '.png')
        self.channelLabel[curlabel].setVisible(True)

        # if self.inputChannel == -1 and self.infoOnChange == True:
            # self.infoOffset = 0
            # self.showInfo(5.0)
        
        if self.showChannelBug == True:
            chtype = self.getChtype(self.currentChannel)     
            chname = self.getChname(self.currentChannel - 1)
            self.getControl(103).setImage(self.Artdownloader.FindBug(chtype, chname))
        self.getControl(300).setLabel(self.channels[self.currentChannel - 1].name)

        if xbmc.getCondVisibility('Player.ShowInfo'):
            json_query = '{"jsonrpc": "2.0", "method": "Input.Info", "id": 1}'
            self.ignoreInfoAction = True
            self.channelList.sendJSON(json_query);
            
        self.channelLabelTimer.start()
        self.startNotificationTimer(10.0)
        self.log('showChannelLabel return')

        
    # Called from the timer to hide the channel label.
    def hideChannelLabel(self):
        self.log('hideChannelLabel')
        self.channelLabelTimer = threading.Timer(2.5, self.hideChannelLabel)
        
        for i in range(3):
            self.channelLabel[i].setVisible(False)

        if self.DirectInput == True:
            inputChannel = self.inputChannel
            if inputChannel != self.currentChannel:
                self.GotoChannelTimer = threading.Timer(0.5, self.setChannel, [inputChannel])
                self.GotoChannelTimer.name = "GotoChannel"
                if self.GotoChannelTimer.isAlive():
                    self.GotoChannelTimer.cancel()
                self.GotoChannelTimer.start()
                
        self.inputChannel = -1
        self.log('hideChannelLabel return')

            
    def closePVRdialog(self):
        xbmc.executebuiltin("Dialog.Close(numericinput[,true])")
        # if getProperty("OVERLAY.Mediapath").startswith('pvr'):
            # if self.CloseDialog(['Done']) == True:
            # xbmc.executebuiltin("Action(Close[,numericinput])")
            
   
    def SideBarAction(self, type='OnDemand'):
        self.log('SideBarAction')        
        if type == 'Now Playing': 
            self.showingBrowse = True
            self.getExtendedInfo()
        elif type == 'Browse':     
            self.showingBrowse = True
            extTypes = ['.avi', '.flv', '.mkv', '.mp4', '.strm', '.ts']
            self.Browse = browse(1,'Browse Videos', 'video', '.avi|.flv|.mkv|.mp4|.strm|.ts', True, True, 'special://videoplaylists')
            Browse_FILE, Browse_EXT = os.path.splitext(self.Browse)
            if Browse_EXT.lower() in extTypes:
                self.log("onClick, Browse = " + self.Browse)
                self.OnDemand = True
                self.Player.play(self.Browse)
                self.infoOnChangeUnlocked = True
        elif type == 'Search':
            self.showingBrowse = True
            xbmc.executebuiltin("XBMC.RunScript(script.globalsearch)")
        else:
            self.showingBrowse = True
            xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo)")
        self.showingBrowse = False
        
        
    def ContextMenuAction(self, type, pType='OVERLAY'):
        self.log("ContextMenuAction, type = " + type + ", pType = " + pType)
        if type == 'MoreInfo':
            self.getExtendedInfo('MoreInfo', pType)
        elif type == 'Similar':
            Comingsoon()
        elif type == 'Record':
            Comingsoon()
        elif type == 'Reminder':
            self.setReminder(getProperty(("%s.TimeStamp")%pType), getProperty(("%s.Title")%pType), int(getProperty(("%s.Chnum")%pType)))
        
        
    def getExtendedInfo(self, type='', pType='OVERLAY'):
        self.log("getExtendedInfo, type = " + type + ", pType = " + pType)  
        if getProperty(("%s.Type")%pType) == 'tvshow':
            dbtype = 'tvdb_id'
            title = 'tvshow'
            info = 'extendedtvinfo'    
        else:
            dbtype = 'imdb_id'
            title = 'name'  
            info = 'extendedinfo'
            
        if type == 'MoreInfo':
            if getProperty(("%s.Type")%pType) == 'youtube':
                YTtype = int(ADDON_SETTINGS.getSetting('Channel_' + getProperty(("%s.Chnum")%pType) + '_2'))
                YTinfo = ADDON_SETTINGS.getSetting('Channel_' + getProperty(("%s.Chnum")%pType) + '_1')
                if YTtype == 1:
                    info = 'youtubeusersearch'
                    if YTinfo[0:2] == 'UC':
                        return               
                elif YTtype == 2:
                    info = 'youtubeplaylist'   
                print YTtype, info, YTinfo
                return xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=%s,id=%s)" % (info, YTinfo)) 

            elif getProperty(("%s.Type")%pType) == 'tvshow':
                if (getProperty(("%s.DBID")%pType) != '0' or getProperty(("%s.ID")%pType) != '0') and getProperty(("%s.Season")%pType) != '0' and getProperty(("%s.Episode")%pType) != '0':
                    info = 'seasoninfo'
                    return xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=%s,dbid=%s,%s=%s,%s=%s,season=%s)" % (info, getProperty(("%s.DBID")%pType), title, getProperty(("%s.Title")%pType), dbtype, getProperty(("%s.ID")%pType), getProperty(("%s.Season")%pType)))
        elif getProperty(("%s.ID")%pType) != '0':
            return xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=%s,%s=%s,%s=%s)" % (info, title, getProperty(("%s.Title")%pType), dbtype, getProperty(("%s.ID")%pType))) 

        
    def hideInfo(self):
        self.log('hideInfo')
        # self.DisableOverlay = False
        self.showingInfo = False 
        self.getControl(102).setVisible(False)
        self.infoOffset = 0
        self.toggleShowStartover(False)
                          
        
    def toggleShowStartover(self, state):
        self.log('toggleShowStartover')
        if state == True:
            self.getControl(104).setVisible(True)
            self.showingStartover = True
        else:
            self.getControl(104).setVisible(False)
            self.showingStartover = False

            
    def showInfo(self, timer):
        self.log("showInfo")  
        try:
            if self.infoTimer.isAlive():
                self.infoTimer.cancel()
        except:
            pass
        self.infoTimer = threading.Timer(timer, self.hideInfo)
        self.infoTimer.name = "InfoTimer"
        
        if self.hideShortItems:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + self.infoOffset
            if self.getChtype(self.currentChannel) <= 7 and self.channels[self.currentChannel - 1].getItemDuration(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()) < self.shortItemLength:
                return
                
        self.hidePOP()
        self.setShowInfo()
        self.getControl(222).setVisible(False)
        self.getControl(102).setVisible(True)
        self.showingInfo = True

        if xbmc.getCondVisibility('Player.ShowInfo'):
            json_query = '{"jsonrpc": "2.0", "method": "Input.Info", "id": 1}'
            self.ignoreInfoAction = True
            self.channelList.sendJSON(json_query);  
        self.infoTimer.start()


    def showMenu(self):
        self.log("showMenu")
        try:
            #Set button labels
            self.getControl(1005).setLabel(self.chkChanFavorite())
            if self.showingMenu == False:    
                #Set first button focus, show menu
                self.showingMenu = True
                self.getControl(119).setVisible(True)
                xbmc.sleep(100) 
                self.setFocusId(1001) 
            self.MenuControlTimer = threading.Timer(self.InfTimer, self.MenuControl,['Menu',self.InfTimer,True])           
            self.MenuControlTimer.name = "MenuControlTimer"  
            self.MenuControlTimer.start() 
        except:
            pass

            
    def showOnNow(self):
        self.log("showOnNow")
        self.setOnNow()
        try:
            if not self.showingMenuAlt:
                show_busy_dialog()
                curchannel = 0
                self.showingMenuAlt = True
                
                if len(self.OnNowTitleLst) == 0:
                    self.setOnNow()
                    
                sidex, sidey = self.getControl(132).getPosition()
                sidew = self.getControl(132).getWidth()
                sideh = self.getControl(132).getHeight()
                listWidth = self.getControl(132).getLabel()
                tabHeight = self.getControl(1001).getHeight()
                self.list = xbmcgui.ControlList(sidex, sidey, sidew, sideh, 'font12', self.myEPG.textcolor, MEDIA_LOC + BUTTON_NO_FOCUS, MEDIA_LOC + BUTTON_FOCUS, self.myEPG.focusedcolor, 1, 1, 1, 0, tabHeight, 0, tabHeight/2)
                self.addControl(self.list)
                self.list.addItems(items=self.OnNowTitleLst)
                
                for i in range(len(self.OnNowTitleLst)):
                    item = self.OnNowTitleLst[i]
                    channel = int(self.channelList.cleanLabels(item.split('|')[0]))
                    if channel == self.currentChannel:
                        break
                    
                self.list.selectItem(i)
                self.getControl(130).setVisible(True)
                hide_busy_dialog()
                xbmc.sleep(100)
                self.list.setVisible(True)
                self.setFocus(self.list)
                self.setOnNowArt()
                self.MenuControlTimer = threading.Timer(self.InfTimer, self.MenuControl,['MenuAlt',self.InfTimer,True])           
                self.MenuControlTimer.name = "MenuControlTimer"  
                self.MenuControlTimer.start() 
        except Exception,e:
            self.log("showOnNow, Failed! " + str(e), XBMC.LOGERROR)


    def ShowMoreInfo(self):
        self.log('ShowMoreInfo')
        try:
            self.getControl(1012).setLabel('More Info')
            self.getControl(1013).setLabel('Find Similar')
            self.getControl(1014).setLabel('Record Show')
            self.getControl(1015).setLabel('Set Reminder')
            
            if not self.showingMoreInfo:
                self.hideInfo()
                self.showingMoreInfo = True   
                self.getControl(222).setVisible(True) 
                xbmc.sleep(100) 
                self.setFocusId(1012)
                
            self.MenuControlTimer = threading.Timer(self.InfTimer, self.MenuControl,['MoreInfo',self.InfTimer,True])           
            self.MenuControlTimer.name = "MenuControlTimer"  
            self.MenuControlTimer.start() 
        except Exception,e:
            self.log("ShowMoreInfo, Failed! " + str(e), XBMC.LOGERROR)

            
    def hidePOP(self):
        self.log("hidePOP")           
        self.getControl(120).setVisible(False)
        self.getControl(103).setVisible(True)
        xbmc.sleep(100)
        self.DisableOverlay = False
        self.showingPop = False
        
                     
    def showPOP(self, timer):
        self.log("showPOP")
        self.popTimer = threading.Timer(timer, self.hidePOP)
        self.popTimer.name = "popTimer"
        if self.popTimer.isAlive():
            self.popTimer.cancel()
        
        #disable channel bug
        self.getControl(103).setVisible(False)
        if self.hideShortItems:
            #Skip short videos
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + self.infoOffset
            if self.getChtype(self.currentChannel) <= 7 and self.channels[self.currentChannel - 1].getItemDuration(position) < self.shortItemLength:
                return

        self.showingPop = True
        self.DisableOverlay = True
        self.getControl(120).setVisible(True)
        self.popTimer.start()
    
            
    def SleepButton(self, silent=False):
        self.sleepTimeValue = (self.sleepTimeValue + 1800)
        #Disable when max sleep reached
        if self.sleepTimeValue > 14400:
            self.sleepTimeValue = 0
            
        if self.sleepTimeValue != 0:
            Stime = self.sleepTimeValue / 60
            SMSG = 'Sleep in ' + str(Stime) + ' minutes'
        else: 
            SMSG = 'Sleep Disabled'
        self.startSleepTimer()

        if silent == False:
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", SMSG, 1000, THUMB) )    

            
    def IdleTimer(self):
        self.log("IdleTimer")   
        if REAL_SETTINGS.getSetting("Idle_Screensaver") == "true":   
            IdleSeconds = 180 #3min
            PausedPlayback = bool(xbmc.getCondVisibility("Player.Paused"))
            ActivePlayback = bool(xbmc.Player().isPlaying())
            xbmcIdle = int(xbmc.getGlobalIdleTime())
            showingEPG = getProperty("PTVL.EPG_Opened") == "true"
            if xbmcIdle >= IdleSeconds:
                if getProperty("PTVL.Idle_Opened") != "true" and (showingEPG or PausedPlayback):
                    self.log("IdleTimer, Starting Idle ScreenSaver")                      
                    xbmc.executebuiltin('XBMC.RunScript(' + ADDON_PATH + '/resources/lib/idle.py)')
                elif getProperty("PTVL.Idle_Opened") == "true" and (not showingEPG or not PausedPlayback):
                    self.log("IdleTimer, Closing Idle ScreenSaver")      
                    xbmc.executebuiltin("action(leftclick)")
            self.logDebug("IdleTimer, Idle_Opened = " + str(getProperty("PTVL.Idle_Opened")) + ", XBMCidle = " + str(xbmcIdle) + ", IdleSeconds = " + str(IdleSeconds) + ', PausedPlayback = ' + str(PausedPlayback) + ', showingEPG = ' + str(showingEPG) + ', ActivePlayback = ' + str(ActivePlayback))
          
          
    def onFocus(self, controlId):
        self.log('onFocus ' + str(controlId))
        
        
    def onClick(self, controlId):
        self.log('onClick ' + str(controlId))
        # Since onAction isnt always called from the same thread (weird),
        # ignore all actions if we're in the middle of processing one
        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return

        lastaction = time.time() - self.lastActionTime
 
        # during certain times we just want to discard all input
        if lastaction < 2:
            self.log('Not allowing actions')
            action = ACTION_INVALID
        if controlId == 1000:
            if self.showingMenu:
                self.log("Now Playing")
                self.SideBarAction('Now Playing')
        elif controlId == 1001:
            if self.showingMenu:
                self.log("OnNow")
                self.MenuControl('MenuAlt',self.InfTimer)
        elif controlId == 1002:
            if self.showingMenu:
                self.log("Browse")
                self.SideBarAction('Browse')
        elif controlId == 1003:
            if self.showingMenu:
                self.log("Search")
                self.SideBarAction('Search')
        elif controlId == 1004:
            if self.showingMenu:
                self.log("LastChannel")
                self.setChannel((self.getLastChannel()))
                self.MenuControl('Menu',self.InfTimer,True) 
        elif controlId == 1005:
            if self.showingMenu:
                self.log("ChannelFavorite")
                self.setChanFavorite()
                self.MenuControl('Menu',self.InfTimer)           
        elif controlId == 1006:
            if self.showingMenu:
                self.log("EPGType")
                self.EPGtypeToggle()
                self.MenuControl('Menu',self.InfTimer)    
        elif controlId == 1007:
            if self.showingMenu:
                self.log("Mute")
                xbmc.executebuiltin("Mute()");
                self.MenuControl('Menu',self.InfTimer)
        elif controlId == 1008:
            if self.showingMenu:
                self.log("Subtitle")
                # xbmc.executebuiltin("ActivateWindow(10153)")
                xbmc.executebuiltin("ActivateWindow(SubtitleSearch)")
                self.MenuControl('Menu',self.InfTimer)  
        elif controlId == 1009:
            if self.showingMenu:
                self.log("VideoMenu")
                xbmc.executebuiltin("ActivateWindow(videoosd)")
                xbmc.sleep(100)
                self.MenuControl('Menu',self.InfTimer,True)       
        elif controlId == 1010:
            if self.showingMenu:
                self.log("Sleep")
                self.SleepButton(True)    
                self.MenuControl('Menu',self.InfTimer)       
        elif controlId == 1011:
            if self.showingMenu:
                self.log("Exit")
                if dlg.yesno("Exit?", "Are you sure you want to exit PseudoTV Live?"):
                    self.MenuControl('Menu',self.InfTimer,True)
                    self.end()
                else:
                    self.MenuControl('Menu',self.InfTimer)           
        elif controlId == 1012:
            self.log("More Info")
            if self.showingMoreInfo:
                self.ContextMenuAction('MoreInfo')   
        elif controlId == 1013:
            self.log("Find Similar")
            if self.showingMoreInfo:
                self.ContextMenuAction('Similar')   
        elif controlId == 1014:
            self.log("Record Show")
            if self.showingMoreInfo:
                self.ContextMenuAction('Record')             
        elif controlId == 1015:
            self.log("Set Reminder")
            if self.showingMoreInfo:
                self.ContextMenuAction('Reminder')
        self.actionSemaphore.release()
        self.log('onClick return')
    
    
    def onControl(self, controlId):
        self.log('onControl ' + str(controlId))
        pass

        
    # Handle all input while videos are playing
    def onAction(self, act):
        action = act.getId()
        self.log('onAction ' + str(action))
        self.OnAction = True
        self.playSFX(action)    
        
        if self.Player.stopped:
            self.log('onAction, Unable player is stopped')
            return
        # Since onAction isnt always called from the same thread (weird),
        # ignore all actions if we're in the middle of processing one
        if self.actionSemaphore.acquire(False) == False:
            self.log('onAction, Unable to get semaphore')
            return
       
        lastaction = time.time() - self.lastActionTime
        # during certain times we just want to discard all input
        if lastaction < 2 and self.showingStartover == False:
            self.log('onAction, Not allowing actions')
            action = ACTION_INVALID

        if action == ACTION_SELECT_ITEM:
            if self.showingStartover == True:
                self.log('onAction, showingStartover')
                self.showingStartover = False
                self.Player.playselected(int(getProperty("PTVL.Current_PlaylistPosition")))
            elif self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer,True)
                try:
                    item = self.list.getSelectedItem()
                    channel = (((item.getLabel()).split('|')[0]).replace('[B]',''))
                    channel = re.sub('\[COLOR=(.+?)\]', '', channel)
                    self.setChannel((int(channel)))
                except:
                    pass  
                self.MenuControl('Menu',self.InfTimer,True) 
            elif self.showingBrowse:
                return
            elif self.showingInfo and self.infoOffset > 0:
                    self.selectShow()
            elif not self.showingMenu and not self.showingMoreInfo and not self.showingBrowse and not self.settingReminder:
                # If we're manually typing the channel, set it now
                if self.inputChannel > 0:
                    if self.inputChannel != self.currentChannel and self.inputChannel <= self.maxChannels:
                        self.setChannel((self.inputChannel))
                    self.inputChannel = -1
                else:
                    # Otherwise, show the EPG
                    if self.channelThread.isAlive():
                        self.channelThread.pause()

                    if self.notificationTimer.isAlive():
                        self.notificationTimer.cancel()
                        self.notificationTimer = threading.Timer(NOTIFICATION_CHECK_TIME, self.notificationAction)

                    # Auto-off reset after EPG activity.
                    self.startSleepTimer()
                            
                    self.hideInfo()
                    self.hidePOP()
                    self.newChannel = 0
                    # self.close
                    self.windowSwap('EPG')

                    if self.channelThread.isAlive():
                        self.channelThread.unpause()
                    self.startNotificationTimer()

                    if self.newChannel != 0:
                        self.setChannel((self.newChannel))
                
        elif action == ACTION_MOVE_UP or action == ACTION_PAGEUP:
            if self.showingMenuAlt:
                self.setOnNowArt()
                self.MenuControl('MenuAlt',self.InfTimer)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer)
            elif not self.showingMoreInfo:
                self.channelUp()
                
        elif action == ACTION_MOVE_DOWN or action == ACTION_PAGEDOWN:
            if self.showingMenuAlt:
                self.setOnNowArt()
                self.MenuControl('MenuAlt',self.InfTimer)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer)
            elif not self.showingMoreInfo:
                self.channelDown()

        elif action == ACTION_MOVE_LEFT:   
            self.log("onAction, ACTION_MOVE_LEFT")
            if self.showingMenuAlt == True:
                self.MenuControl('MenuAlt',self.InfTimer,True)
            elif self.showingMenu == True:
                self.MenuControl('Menu',self.InfTimer,True)
            elif self.showingInfo == True:
                self.infoOffset -= 1
                if self.infoOffset < 0:
                    self.MenuControl('Menu',self.InfTimer)
                elif not self.showingMenu:
                    self.showInfo(self.InfTimer)
            elif self.showingInfo == False and int(getProperty("OVERLAY.Chtype")) != 8 and int(getProperty("OVERLAY.Chtype")) != 9 and (getProperty("OVERLAY.Mediapath"))[0:4] != 'rtmp' and (getProperty("OVERLAY.Mediapath"))[0:4] != 'rtsp' and not getProperty("OVERLAY.Mediapath").startswith('PlayMedia'):
                xbmc.executebuiltin("ActivateWindow(10115)")
                xbmc.executebuiltin("PlayerControl(SmallSkipBackward)")
                self.log("onAction, SmallSkipBackward")
                self.UPNPcontrol('rwd')
                    
        elif action == ACTION_MOVE_RIGHT:
            self.log("onAction, ACTION_MOVE_RIGHT")
            if self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer,True)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer,True)
            elif self.showingInfo and not self.showingStartover:
                self.infoOffset += 1
                self.showInfo(self.InfTimer)
            elif int(getProperty("OVERLAY.Chtype")) != 8 and int(getProperty("OVERLAY.Chtype")) != 9 and (getProperty("OVERLAY.Mediapath"))[0:4] != 'rtmp' and (getProperty("OVERLAY.Mediapath"))[0:4] != 'rtsp' and not getProperty("OVERLAY.Mediapath").startswith('PlayMedia'):
                xbmc.executebuiltin("ActivateWindow(10115)")
                xbmc.executebuiltin("PlayerControl(SmallSkipForward)")
                self.log("onAction, SmallSkipForward")
                self.UPNPcontrol('fwd')
       
        elif action in ACTION_PREVIOUS_MENU:
            if self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer,True)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer,True)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer,True)
            elif self.showingInfo:
                self.hideInfo()
            else:        
                dlg = xbmcgui.Dialog()

                if dlg.yesno("Exit?", "Are you sure you want to exit PseudoTV Live?"):
                    self.end()
                    return  # Don't release the semaphore         
                del dlg
        
        elif action == ACTION_SHOW_INFO:   
            if self.ignoreInfoAction:
                self.ignoreInfoAction = False
            else:
                if self.showingInfo:
                    self.hideInfo()
            
                    if xbmc.getCondVisibility('Player.ShowInfo'):
                        json_query = '{"jsonrpc": "2.0", "method": "Input.Info", "id": 1}'
                        self.ignoreInfoAction = True
                        self.channelList.sendJSON(json_query);
                else:
                    self.showInfo(self.InfTimer)         

        elif action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
            self.closePVRdialog()
            self.notPlayingAction = 'Last'
            if self.inputChannel < 0:
                self.inputChannel = action - ACTION_NUMBER_0
            else:
                if self.inputChannel < 100:
                    self.inputChannel = self.inputChannel * 10 + action - ACTION_NUMBER_0
            self.showChannelLabel(self.inputChannel)
        
        elif action == ACTION_SHOW_SUBTITLES:
            xbmc.executebuiltin("ActivateWindow(SubtitleSearch)")
            
        elif action == ACTION_AUDIO_NEXT_LANGUAGE:#notworking
            xbmc.executebuiltin("ActivateWindow(NextSubtitle)")
            
        elif action == ACTION_SHOW_CODEC:
            xbmc.executebuiltin("ActivateWindow(CodecInfo)")
            
        elif action == ACTION_ASPECT_RATIO:
            self.SleepButton()
            
        elif action == ACTION_RECORD:
            self.log('onAction, ACTION_RECORD')
        
        elif action == ACTION_SHIFT: #Last channel button
            self.log('onAction, ACTION_SHIFT')
            self.setChannel((self.getLastChannel()))

        elif action == ACTION_SYMBOLS:
            self.log('onAction, ACTION_SYMBOLS')
            self.setChannel((self.Jump2Favorite()))
            
        elif action == ACTION_CURSOR_LEFT:
            self.log('onAction, ACTION_CURSOR_LEFT')
            
        elif action == ACTION_CURSOR_RIGHT:
            self.log('onAction, ACTION_CURSOR_RIGHT')

        elif action == ACTION_CONTEXT_MENU:
            self.log('onAction, ACTION_CONTEXT_MENU')
            if not self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer,True)

        self.actionSemaphore.release()
        self.OnAction = False
        self.log('onAction return')

             
    def SleepTimerCountdown(self, sleeptime):
        self.log("SleepTimerCountdown")
        if sleeptime == 0:
            self.getControl(1010).setLabel('Sleep')
        else:
            self.getControl(1010).setLabel('Sleep (%s)' % str(sleeptime))
        
            self.SleepTimerCountdownTimer = threading.Timer(60.0, self.SleepTimerCountdown, [sleeptime-1])
            self.SleepTimerCountdownTimer.name = "SleepTimerCountdownTimer"
            
            if self.SleepTimerCountdownTimer.isAlive():
                self.SleepTimerCountdownTimer.cancel()
            else:
                self.SleepTimerCountdownTimer.start()
            
            
    # Reset the sleep timer
    def startSleepTimer(self):
        self.SleepTimerCountdown(self.sleepTimeValue/60)
        try:
            if self.sleepTimeValue == 0:
                if self.sleepTimer.isAlive():
                    self.sleepTimer.cancel()
                return
            else:
                # Cancel the timer if it is still running
                if self.sleepTimer.isAlive():
                    self.sleepTimer.cancel()
                    self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)
                    
                if self.Player.stopped == False:
                    self.sleepTimer.name = "SleepTimer"
                    self.sleepTimer.start()
        except:
            pass
    
    
    def startNotificationTimer(self, timertime = NOTIFICATION_CHECK_TIME):
        self.log("startNotificationTimer")
        self.notificationTimer = threading.Timer(timertime, self.notificationAction)
        self.notificationTimer.name = "NotificationTimer"
        if self.notificationTimer.isAlive():
            self.notificationTimer.cancel()

        if self.Player.stopped == False:
            self.notificationTimer.start()

            
    # This is called when the sleep timer expires
    def sleepAction(self):
        self.log("sleepAction")
        self.actionSemaphore.acquire()
#        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)
        # TODO: show some dialog, allow the user to cancel the sleep
        # perhaps modify the sleep time based on the current show
        if self.sleepTimeMode == 0:
            self.end()
        elif self.sleepTimeMode == 1:
            xbmc.executebuiltin( "XBMC.AlarmClock(shutdowntimer,XBMC.Quit(),%d,false)" % ( 5.0, ) )
            self.end()
        elif self.sleepTimeMode == 2:
            xbmc.executebuiltin( "XBMC.AlarmClock(shutdowntimer,XBMC.Suspend(),%d,false)" % ( 5.0, ) )
            # self.end()
        elif self.sleepTimeMode == 3:
            xbmc.executebuiltin( "XBMC.AlarmClock(shutdowntimer,XBMC.Powerdown(),%d,false)" % ( 5.0, ) )
            self.end()
        elif self.sleepTimeMode == 4:
            self.egTrigger('PseudoTV_Live - Sleeping')
        elif self.sleepTimeMode == 5:
            xbmc.executebuiltin("CECStandby()"); 
            

    # Run rules for a channel
    def runActions(self, action, channel, parameter):
        self.log("runActions " + str(action) + " on channel " + str(channel))

        if channel < 1:
            return

        self.runningActionChannel = channel
        index = 0

        for rule in self.channels[channel - 1].ruleList:
            if rule.actions & action > 0:
                self.runningActionId = index
                parameter = rule.runAction(action, self, parameter)

            index += 1

        self.runningActionChannel = 0
        self.runningActionId = 0
        return parameter


    def notificationAction(self):
        self.log("notificationAction")
        ClassicPOPUP = False
        docheck = False
        
        if self.Player.isPlaying():
            if self.notificationLastChannel != self.currentChannel:
                docheck = True
            else:
                if self.notificationLastShow != xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition():
                    docheck = True
                else:
                    if self.notificationShowedNotif == False:
                        docheck = True

            if docheck == True:
                self.notificationLastChannel = self.currentChannel
                self.notificationLastShow = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
                self.notificationShowedNotif = False

                if self.hideShortItems:
                    # Don't show any notification if the current show is < 60 seconds
                    if self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) < self.shortItemLength:
                        self.notificationShowedNotif = True
                        
                timedif = self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) - self.Player.getTime()
                if self.notificationShowedNotif == False and timedif < NOTIFICATION_TIME_BEFORE_END and timedif > NOTIFICATION_DISPLAY_TIME:
                    nextshow = self.channels[self.currentChannel - 1].fixPlaylistIndex(self.notificationLastShow + 1)
                    
                    if self.hideShortItems:
                        # Find the next show that is >= 60 seconds long
                        while nextshow != self.notificationLastShow:
                            if self.channels[self.currentChannel - 1].getItemDuration(nextshow) >= self.shortItemLength:
                                break
                            nextshow = self.channels[self.currentChannel - 1].fixPlaylistIndex(nextshow + 1)
                            
                    self.log('notification.init')     
                    mediapath = (self.channels[self.currentChannel - 1].getItemFilename(nextshow))
                    chname = self.getChname(self.currentChannel - 1)
                    ChannelLogo = (self.channelLogos + (self.channels[self.currentChannel - 1].name) + '.png')
                    chtype = self.getChtype(self.currentChannel)
                    ShowTitle = self.channels[self.currentChannel - 1].getItemTitle(nextshow).replace(',', '')
                    myLiveID = self.channels[self.currentChannel - 1].getItemLiveID(nextshow)
                    type = (self.channelList.unpackLiveID(myLiveID))[0]
                    id = (self.channelList.unpackLiveID(myLiveID))[1]
                    dbid, epid = splitDBID((self.channelList.unpackLiveID(myLiveID))[2])
                    mpath = getMpath(mediapath)
                    
                    try:
                        ShowEpisode = (self.channels[self.currentChannel - 1].getItemEpisodeTitle(nextshow).replace(',', ''))
                        ShowEpisode = ShowEpisode.split("- ")[1]
                    except:
                        ShowEpisode = (self.channels[self.currentChannel - 1].getItemEpisodeTitle(nextshow).replace(',', ''))
                        pass

                    #ArtType for Classic
                    if REAL_SETTINGS.getSetting("EnableComingUp") == "3":
                        self.log('notification, Classic')  
                        ArtType = {}
                        ArtType['0'] = 'poster'
                        ArtType['1'] = 'fanart' 
                        ArtType['2'] = 'landscape'        
                        ArtType['3'] = 'logo'       
                        ArtType['4'] = 'clearart'              
                        ArtType = EXTtype(ArtType[REAL_SETTINGS.getSetting('ComingUpArtwork')]) #notification art type for classic

                    #ArtType for Popup
                    elif REAL_SETTINGS.getSetting("EnableComingUp") == "2":
                        self.log('notification, Popup')  
                        try:
                            ArtType = EXTtype(getProperty("OVERLAY.type4"))
                            self.getControl(124).setLabel(ShowTitle)
                            self.getControl(125).setLabel(ShowEpisode)
                        except:
                            #No Overlay Popup code in skin, default to Cassic Popup
                            ClassicPOPUP = True
                            pass

                    # Execute notification
                    if self.showNextItem == True:
                        # Classic/Popup note
                        if REAL_SETTINGS.getSetting("EnableComingUp") != "1":
                            self.log('notification, classic/popup')
                            NotifyTHUMB = self.setArtwork(type, chtype, chname, id, dbid, mpath, ArtType, 'type4ART', 'OVERLAY')   
                            self.log("notification.plugin.NotifyTHUMB = " + NotifyTHUMB)           
                            if self.showingInfo == False and self.notificationShowedNotif == False:
                                if REAL_SETTINGS.getSetting("EnableComingUp") == "3" or ClassicPOPUP == True:
                                    xbmc.executebuiltin('XBMC.Notification(%s, %s, %s, %s)' % ('Coming Up: '+ShowTitle, self.channels[self.currentChannel - 1].getItemTitle(nextshow).replace(',', ''), str(NOTIFICATION_DISPLAY_TIME * 2000), NotifyTHUMB))
                                else:
                                    self.showPOP(self.InfTimer + 2.5)
                                self.notificationShowedNotif = True

                        # Overlay notification
                        else:
                            self.log('notification, Overlay') 
                            self.infoOffset = ((nextshow) - self.notificationLastShow)
                            self.log('notification, Overlay infoOffset = ' + str(self.infoOffset))
                            self.showInfo(self.InfTimer)
                            self.notificationShowedNotif = True
        self.startNotificationTimer()

            
    def currentWindow(self):
        currentWindow = ''
        # return current window label via json, xbmcgui.getCurrentWindowId does not return accurate id.
        json_query = ('{"jsonrpc": "2.0", "method":"GUI.GetProperties","params":{"properties":["currentwindow"]}, "id": 1}')
        json_detail = self.channelList.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
        
        for f in file_detail:
            id = re.search('"label" *: *"(.*?)"', f)
            if id and len(id.group(1)) > 0:
                currentWindow = id.group(1)
                break
        return currentWindow
        
    
    def CloseDialog(self, type=['Progress dialogue','Dialogue OK']):
        curwindow = self.currentWindow()
        self.logDebug("CloseDialog, type = " + str(type) + ", currentwindow = " + curwindow)
        if curwindow in type:
            json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"select"},"id":1}'
            self.channelList.sendJSON(json_query);                  
            DebugNotify("Dialogue Closed")
            return True
        # "Working" Busy dialogue doesn't report a label.
        elif curwindow == "":
            if self.Player.ignoreNextStop == True and self.Player.isPlaybackValid() == False:
                self.logDebug("PlayerTimedOut, Playback Failed: STOPPING!")
                json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"stop"},"id":1}'
                self.channelList.sendJSON(json_query);                 
                DebugNotify("Playback Failed, STOPPING!") 
                return True
        return False

        
    def playbackFailedAction(self, channel=None):
        if not channel:
            channel = self.currentChannel
        # ChanOffset = 0
        # PosOffset = 0
        # Valid = False
        # while Valid == False:
            # chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel + 1 + ChanOffset) + '_type'))
            # mediapath = self.channels[channel - 1 + ChanOffset].getItemFilename(self.channels[channel - 1 + ChanOffset].playlistPosition + PosOffset)
            # ChanOffset += 1
        # if chtype in [8,9]:
            # self.lastActionTrigger()
        # elif chtype == 15 or mediapath[-4:].lower() == 'strm':
            # self.lastActionTrigger()
        # else:
            # self.lastActionTrigger()

            
    def playerTimerAction(self):
        self.logDebug("playerTimerAction")
        if self.isExiting == False:
            self.playerTimer = threading.Timer(self.ActionTimeInt, self.playerTimerAction)  
            self.playerTimer.name = "PlayerTimer"
            if self.playerTimer.isAlive():
                self.playerTimer.cancel()

            # lazy 60-120 second cronjob
            self.triggercount += 1
            if self.triggercount == 30:
                self.triggercount = 0      
                GA_Request()
            self.IdleTimer()
                
            try:
                # Resume playback for live streams, except pvr backend which has timeshift buffer.
                if int(getProperty("OVERLAY.Chtype")) in [8, 9] and not getProperty("OVERLAY.Mediapath").startswith('pvr://'):
                    self.Player.resumePlayback()
            except:
                pass
                
            if self.Player.isPlaybackValid() == True:
                self.lastPlayTime = self.Player.getPlayerTime()
                self.lastPlaylistPosition = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
                self.notPlayingCount = 0   
                self.lastActionCount = 0
            else:        
                self.notPlayingCount += 1
                self.logDebug("notPlayingCount = " + str(self.notPlayingCount) + "/" + str(int(round((self.PlayTimeoutInt/int(self.ActionTimeInt))))), notify=True)
                
            self.playerTimer.start()
                 
            # if isLowPower() != True:
                # if self.CloseDialog(['Dialogue OK']) == True:
                    # if self.Player.isActuallyPlaying() == False:    
                        # return self.lastActionTrigger()
                        
            if self.notPlayingCount >= int(round((self.PlayTimeoutInt/int(self.ActionTimeInt)))): 
                self.CloseDialog()
                if self.Player.isActuallyPlaying() == False:
                    return self.lastActionTrigger()

     
    def Paused(self, action=False):
        self.log('Paused')
        self.background.setVisible(True)
        self.background.setLabel('Paused')   
        if action and self.Player.isPlaying():
            json_query = ('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1}, "id": 1}')
            self.channelList.sendJSON(json_query)
        self.UPNPcontrol('pause')
    
    
    def Resume(self, action=False):
        self.log('Resume')
        self.background.setVisible(False)
        self.showInfo(self.InfTimer)      
        if action and self.Player.isPlaybackPaused():
            json_query = ('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1}, "id": 1}')
            self.channelList.sendJSON(json_query) 
        self.UPNPcontrol('resume')
    
    
    def setLastChannel(self, channel=None):
        self.log('setLastChannel') 
        if not channel:
            try:
                channel = self.currentChannel
            except:
                channel = 1
        REAL_SETTINGS.setSetting('LastChannel', str(channel))
        
    
    def getLastChannel(self):
        self.log('getLastChannel') 
        try:
            LastChannel = int(REAL_SETTINGS.getSetting('LastChannel'))
        except:
            LastChannel = 1
        return LastChannel
        
        
    def showReminder(self, tmpDate, title, channel, record):
        self.log('showReminder')
        Notify_Time, epochBeginDate = self.cleanReminderTime(tmpDate)
        if REAL_SETTINGS.getSetting("AutoJump") == "true":
            if handle_wait(15,"Show Reminder",'[B]%s[/B] on channel [B]%s[/B] at [B]%s[/B] ?'%(title,str(channel),str(Notify_Time))) == True:
                self.setChannel(self.fixChannel(channel))
        else:
            for i in range(15):
                xbmc.executebuiltin("Notification([B]%s[/B] on, channel [B]%s[/B] starts in %s's, %d, %s)" % (title,str(channel),str(15-i), 1000, THUMB) )
        self.removeReminder(tmpDate, title, channel, record)
            
            
    def removeReminder(self, tmpDate, title, channel, record, auto=True):
        self.log('removeReminder')
        Notify_Time, epochBeginDate = self.cleanReminderTime(tmpDate)
        if auto == False:
            if not dlg.yesno("PseudoTV Live", 'Would you like to remove the reminder for [B]%s[/B] on channel [B]%s[/B] at [B]%s[/B] ?'%(title,str(channel),str(Notify_Time))):
                return
        ReminderLst = str(tmpDate)+','+title+','+str(channel)+','+str(record)
        self.ReminderLst = removeStringElem(self.ReminderLst, ReminderLst)
        self.ReminderLst = sorted_nicely(self.ReminderLst)
        newReminderLst = ('|'.join(self.ReminderLst))
        REAL_SETTINGS.setSetting("ReminderLst",newReminderLst)
            
            
    def saveReminder(self, tmpDate, title, channel, record):
        self.log('saveReminder')
        ReminderLst = str(tmpDate)+','+title+','+str(channel)+','+str(record)
        self.ReminderLst.append(ReminderLst)
        self.ReminderLst = sorted_nicely(self.ReminderLst)
        newReminderLst = ('|'.join(self.ReminderLst))
        REAL_SETTINGS.setSetting("ReminderLst",newReminderLst)
                
                
    def loadReminder(self):
        self.log('loadReminder')
        try:
            ReminderLst = (REAL_SETTINGS.getSetting("ReminderLst")).split('|')
        except:
            ReminderLst = (REAL_SETTINGS.getSetting("ReminderLst"))
            
        if ReminderLst:
            for n in range(len(ReminderLst)):
                try:
                    lineLST = (ReminderLst[n]).split(',')
                    self.log('loadReminder, Loading ' + str(n) + '/' + str(len(ReminderLst)) + ':' + str(lineLST))    
                    try:#sloppy fix, for threading issue with strptime.
                        t = time.strptime(lineLST[0], '%Y-%m-%d %H:%M:%S')
                    except:
                        t = time.strptime(lineLST[0], '%Y-%m-%d %H:%M:%S')   
                    epochBeginDate = time.mktime(t)             
                    now = time.time()
                    if epochBeginDate > now:
                        self.setReminder(lineLST[0], lineLST[1], int(lineLST[2]), lineLST[3], auto=True)
                    else:
                        self.removeReminder(lineLST[0],lineLST[1],lineLST[2],lineLST[3])
                except:
                    pass
            
            
    def isReminder(self, tmpDate, title, channel):
        self.log('isReminder')
        ReminderLst = str(tmpDate)+','+title+','+str(channel)
        if self.ReminderLst and len(self.ReminderLst) > 0:
            for n in range(len(self.ReminderLst)):
                try:
                    lineLST = (self.ReminderLst[n]).replace(',True','').replace(',False','')
                    if lineLST == ReminderLst:
                        self.logDebug('isReminder, True: ' + str(lineLST) + ' == ' + str(ReminderLst))
                        return True
                except:
                    pass
        return False
            
            
    def cleanReminderTime(self, tmpDate):
        try:#sloppy fix, for threading issue with strptime.
            t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
        except:
            t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
        Notify_Time = time.strftime('%I:%M%p, %A', t)
        epochBeginDate = time.mktime(t)
        return Notify_Time, epochBeginDate
            
            
    def setReminder(self, tmpDate, title, channel, record=False, auto=False):
        self.log('setReminder')
        if len(tmpDate) > 0:                
            self.settingReminder = True
            Notify_Time, epochBeginDate = self.cleanReminderTime(tmpDate)
            if auto == False: 
                if self.isReminder(tmpDate, title, channel) == True:
                    self.removeReminder(tmpDate, title, channel, record, auto=False)
                else:
                    if dlg.yesno("PseudoTV Live", "Would you like to set a reminder for [B]%s[/B] on channel [B]%s[/B] at [B]%s[/B] ?"%(title,str(channel),str(Notify_Time))):
                        auto = True
            if auto == True:
                now = time.time()
                reminder_time = round(((epochBeginDate - now) / 60) - .25)#In minutes
                reminder_Threadtime = float(int(reminder_time)*60)#In seconds
                # if int(reminder_Threadtime) > 0:
                self.log('setReminder, setting ' + str([tmpDate, title, channel, record]))
                self.ReminderTimer = threading.Timer(reminder_Threadtime, self.showReminder, [tmpDate, title, channel, record])
                self.ReminderTimer.name = "ReminderTimer"  
                if self.ReminderTimer.isAlive():
                    self.ReminderTimer.cancel()
                    self.ReminderTimer.join()
                self.ReminderTimer.start()
                xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live","Reminder Set for " + str(Notify_Time), 4000, THUMB) )
                self.saveReminder(tmpDate, title, channel, record)
            self.settingReminder = False
        else:
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live","Reminders only available for LiveTV", 1000, THUMB) )

            
    def getTMPSTR_Thread(self, chtype, chname, chnum, mediapath, position):
        self.log('getTMPSTR_Thread') 
        tmpstr = self.channelList.getFileList(self.channelList.requestItem(mediapath), self.currentChannel, '1')
        setProperty("OVERLAY.OnDemand_tmpstr",str(tmpstr))
        return self.SetMediaInfo(chtype, chname, chnum, mediapath, position, tmpstr)

        
    def EPGtypeToggle(self):
        self.log('EPGtype')     
        ColorType = REAL_SETTINGS.getSetting('EPGcolor_enabled')
 
        if ColorType == '0':
            REAL_SETTINGS.setSetting("EPGcolor_enabled", "1")
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "EPG Color by Genre ", 1000, THUMB) )
        elif ColorType == '1':
            REAL_SETTINGS.setSetting("EPGcolor_enabled", "2")
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "EPG Color by Chtype", 1000, THUMB) )
        elif ColorType == '2':
            REAL_SETTINGS.setSetting("EPGcolor_enabled", "3")
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "EPG Color by Rating", 1000, THUMB) )
        elif ColorType == '3':
            REAL_SETTINGS.setSetting("EPGcolor_enabled", "0")
            xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "EPG Color Disabled", 1000, THUMB) )

         
    def MenuControl(self, type, timer, hide=False):
        self.log("MenuControl, type = " + type + ", hide = " + str(hide))
        try:
            if self.MenuControlTimer.isAlive():
                self.MenuControlTimer.cancel()
        except:
            pass
        
        if hide == True:
            self.DisableOverlay = False
        # elif self.DisableOverlay == True and type != 'MenuAlt':
            # return
        else:
            self.hideInfo()
            self.hidePOP()
            self.DisableOverlay = True
                
        if type == 'Menu':
            if hide == True:
                try:
                    self.showingMenu = False 
                    self.infoOffset = 0        
                    self.getControl(119).setVisible(False)            
                except:
                    pass
            else:
                self.showMenu() 
                
        elif type == 'MenuAlt':
            if hide == True:
                try:
                    self.showingMenuAlt = False                   
                    self.setFocusId(1001)  
                    self.list.setVisible(False)   
                    self.getControl(130).setVisible(False)
                    self.MenuControl('Menu',self.InfTimer)
                except:
                    pass
            else:
                self.showOnNow()
                
        elif type == 'Info':
            if hide == True:
                try:
                    self.hideInfo()
                except:
                    pass
            else:
                self.showInfo(timer)
                
        elif type == 'MoreInfo':
            if hide == True:
                try:
                    self.showingMoreInfo = False
                    self.infoOffset = 0     
                    self.getControl(222).setVisible(False)
                except:
                    pass
            else:
                self.ShowMoreInfo()
                
                
    def Jump2Favorite(self):
        NextFav = self.FavChanLst[0]
        for n in range(len(self.FavChanLst)):
            if int(self.FavChanLst[n]) > self.currentChannel:
                NextFav = self.FavChanLst[n]
                break   
        return self.fixChannel(int(NextFav))

        
    def chkChanFavorite(self):
        if str(self.currentChannel) in self.FavChanLst:
            return 'Remove Favorite'
        else:
            return 'Set Favorite'
                

    def isChanFavorite(self, chan):
        Favorite = False
        if str(chan) in self.FavChanLst:
            Favorite = True
        return Favorite
        
        
    def setChanFavorite(self, chan=None):
        if not chan:
            chan = self.currentChannel
        if self.isChanFavorite(chan):
            MSG = "Channel %s removed from favourites" % str(chan)
            self.FavChanLst = removeStringElem(self.FavChanLst, str(chan))
        else:
            MSG = "Channel %s added to favourites" % str(chan)
            self.FavChanLst.append(str(chan))
            
        infoDialog(MSG)
        self.FavChanLst = removeStringElem(self.FavChanLst)
        self.FavChanLst = sorted_nicely(self.FavChanLst)
        newFavChanLst = (','.join(self.FavChanLst))
        REAL_SETTINGS.setSetting("FavChanLst",newFavChanLst)
                
                
    # def setSeekBarTime(self):
        # timex, timey = self.getControl(515).getPosition()
        # self.getControl(516).setPosition(timex/2, timey)
          
          
    def FEEDtoggle(self):
        self.log("FEEDtoggle") 
        UpdateRSS()
        if getProperty("PTVL.FEEDtoggle") == "true":
            setProperty("PTVL.FEEDtoggle","false")
        else:
            setProperty("PTVL.FEEDtoggle","true")
        self.FEEDtoggleTimer = threading.Timer(900.0, self.FEEDtoggle)
        self.FEEDtoggleTimer.name = "FEEDtoggleTimer"
        self.FEEDtoggleTimer.start()
     
     
    def selectShow(self):
        self.log("selectShow")
        modifier = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
        self.Player.playselected(self.channels[self.currentChannel - 1].fixPlaylistIndex(self.infoOffset + modifier))
     
    
    def egTrigger_Thread(self, message, sender):
        self.log("egTrigger_Thread")
        json_query = ('{"jsonrpc": "2.0", "method": "JSONRPC.NotifyAll", "params": {"sender":"%s","message":"%s"}, "id": 1}' % (sender, message))
        self.channelList.sendJSON(json_query)
        
        
    def egTrigger(self, message, sender='PTVL'):
        self.log("egTrigger")
        try:
            self.egTriggerTimer = threading.Timer(0.5, self.egTrigger_Thread, [message, sender])
            self.egTriggerTimer.name = "egTriggerTimer"       
            if self.egTriggerTimer.isAlive():
                self.egTriggerTimer.cancel()
            self.egTriggerTimer.start()
        except Exception,e:
            self.log('egTrigger, Failed!, ' + str(e))
            pass 
            
            
    def playSFX(self, action):
        self.log("playSFX")
        if REAL_SETTINGS.getSetting("SFX_Enabled") != "true":
            return
        elif action in [ACTION_MOVE_DOWN, ACTION_MOVE_UP, ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT, ACTION_PAGEDOWN, ACTION_PAGEUP]:
            print MOVE_SFX
            xbmc.playSFX(MOVE_SFX)
     
        
    def setProp(self, title, year, chtype, id, genre, rating, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, playcount, season, episode, pType='OVERLAY'):
        self.log("setProp")
        self.setPropTimer = threading.Timer(0.1, self.setProp_thread, [title, year, chtype, id, genre, rating, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, playcount, season, episode, pType])
        self.setPropTimer.name = "setPropTimer"       
        if self.setPropTimer.isAlive():
            self.setPropTimer.cancel()
        self.setPropTimer.start()

        
    def setProp_thread(self, title, year, chtype, id, genre, rating, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, playcount, season, episode, pType):
        self.log("setProp_thread")

        # core info
        setProperty("%s.Chtype"%pType,str(chtype))
        setProperty("%s.Mediapath"%pType,mediapath)
        setProperty("%s.Playcount"%pType,str(playcount))
        # playlist info
        setProperty("%s.Title"%pType,title)
        setProperty("%s.Mpath"%pType,mpath)
        setProperty("%s.Chname"%pType,chname)
        setProperty("%s.SEtitle"%pType,SEtitle)
        setProperty("%s.Type"%pType,type)
        setProperty("%s.DBID"%pType,dbid)
        setProperty("%s.EPID"%pType,epid)
        setProperty("%s.Description"%pType,Description)
        setProperty("%s.Season"%pType,str(season))
        setProperty("%s.Episode"%pType,str(episode)) 
        # getEnhancedGuideData, else use LiveID
        showtitle, cleantitle, year, id, genre, rating, tagline = self.channelList.getEnhancedGuideData(title, year, id, genre, rating, type)
        # core epg info
        setProperty("%s.Year"%pType,str(year))
        setProperty("%s.Genre"%pType,genre)
        setProperty("%s.Rating"%pType,rating)
        # extended info
        setProperty("%s.Showtitle"%pType,showtitle)
        setProperty("%s.Cleantitle"%pType,cleantitle)
        setProperty("%s.ID"%pType,str(id))
        setProperty("%s.Tagline"%pType,tagline)
        self.setArtwork(type, chtype, chname, id, dbid, mpath, EXTtype(getProperty(("%s.type1")%pType)), 'type1ART', pType)
        self.setArtwork(type, chtype, chname, id, dbid, mpath, EXTtype(getProperty(("%s.type2")%pType)), 'type2ART', pType)
        self.isNEW_Thread(pType)
        self.isManaged_Thread(pType)
        getRSSFeed(getProperty("OVERLAY.Genre"))

            
    def setArtwork(self, type, chtype, chname, id, dbid, mpath, typeEXT, typeART='type1ART', pType='OVERLAY'):
        self.log('setArtwork')  
        # print type, chtype, chname, id, dbid, mpath, typeEXT, typeART, pType
        try:
            self.ArtThread = threading.Timer(0.1, self.findArtwork_Thread, [type, chtype, chname, id, dbid, mpath, typeEXT, typeART, pType])
            self.ArtThread.name = "ArtThread"     
            if self.ArtThread.isAlive():
                self.ArtThread.cancel()
                # self.ArtThread.join()
            self.ArtThread.start()
        except Exception,e:
            self.log('setArtwork, Failed!, ' + str(e))
            pass  
    
     
    def findArtwork_Thread(self, type, chtype, chname, id, dbid, mpath, typeEXT, key, pType):
        self.log('findArtwork_Thread, chtype = ' + str(chtype) + ', id = ' + str(id) +  ', dbid = ' + str(dbid) + ', typeEXT = ' + typeEXT + ', key = ' + key + ', pType = ' + str(pType))  
        try:
            setImage = self.Artdownloader.FindArtwork(type, chtype, chname, id, dbid, mpath, typeEXT)
            if FileAccess.exists(setImage) == False:
                setImage = self.Artdownloader.SetDefaultArt(chname, mpath, typeEXT)
            self.logDebug('findArtwork_Thread, setImage = ' + setImage)   
            setProperty(("%s.%s" %(pType, key)),setImage)
        except Exception,e:
            self.log('findArtwork_Thread, Failed!, ' + str(e))
            pass
    
    
    def isNEW_Thread(self, pType):
        self.log("isNEW_Thread")
        try:
            chtype = int(getProperty("%s.Chtype"%pType))
            mediapath = getProperty("%s.Mediapath"%pType)
            playcount = int(getProperty("%s.Playcount"%pType))
            
            if playcount > 0:
                return setProperty("%s.isNEW"%pType,MEDIA_LOC + 'OLD.png')
            elif chtype == 8 and playcount == 0:
                return setProperty("%s.isNEW"%pType,MEDIA_LOC + 'NEW.png')
            elif chtype < 7:
                json_query = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"video","properties":["playcount"]}, "id": 1 }' % mediapath)
                json_folder_detail = self.channelList.sendJSON(json_query)
                file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
                for f in file_detail:
                    try:
                        playcounts = re.search('"playcount" *: *([\d.]*\d+),', f)
                        if playcounts != None and len(playcounts.group(1)) > 0:
                            playcount = int(playcounts.group(1))
                            if playcount == 0:
                                return setProperty("%s.isNEW"%pType,MEDIA_LOC + 'NEW.png')
                    except:
                        pass 
            # todo parse youtube watched status? create custom db to track watched status?
        except:
            pass
        return setProperty("%s.isNEW"%pType,MEDIA_LOC + 'OLD.png')

      
    def isNew(self, pType='OVERLAY'):
        self.log('isNew') 
        try:
            if isLowPower() != True:
                self.isNewTimer = threading.Timer(0.1, self.isNEW_Thread, [pType])
                self.isNewTimer.name = "isNewTimer"       
                if self.isNewTimer.isAlive():
                    self.isNewTimer.cancel()
                self.isNewTimer.start()
        except Exception,e:
            self.log('isNew, Failed!, ' + str(e))
            pass 
            
     
    def isManaged_Thread(self, pType):
        self.log("isManaged_Thread")
        # setProperty("%s.isManaged"%pType,str(Managed))
            # if imdbnumber != 0:
        # Managed = self.cpManaged(showtitles, imdbnumber)   
                  
            # if imdbnumber != 0:
                # Managed = self.sbManaged(imdbnumber)      
        
        # #Sickbeard/Couchpotato
        # try:
            # if getProperty("%s.isManaged"%pType) == 'true':
                # if type == 'tvshow':
                    # setProperty("%s.isManaged"%pType,IMAGES_LOC + 'SB.png')
                # elif type == 'movie':
                    # setProperty("%s.isManaged"%pType,IMAGES_LOC + 'CP.png')                          
            # else:
                # setProperty("%s.isManaged"%pType,IMAGES_LOC + 'NA.png') 
        # except Exception,e:
            # self.log('Sickbeard/Couchpotato failed!, ' + str(e))
            # pass  
          
          
    def isManaged(self, pType='OVERLAY'):
        self.log('isManaged') 
        try:
            if isLowPower() != True:
                self.isManagedTimer = threading.Timer(0.1, self.isManaged_Thread, [pType])
                self.isManagedTimer.name = "isManagedTimer"       
                if self.isManagedTimer.isAlive():
                    self.isManagedTimer.cancel()
                self.isManagedTimer.start()
        except Exception,e:
            self.log('isNew, Failed!, ' + str(e))
            pass 
            
            
    # Adapted from lamdba's plugin
    def setWatchedStatus_Thread(self, type, title, year, id, dbid, epid, season, episode, playcount):
        self.log('setWatchedStatus_Thread')
        if type == 'movie':
            try:
                json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : %s, "playcount" : %s }, "id": 1 }' % (str(dbid), str(playcount)))
                self.channelList.sendJSON(json_query);  
            except Exception,e:
                self.log('setWatchedStatus, MOVIE:DBID Failed! ' + str(e))
            try:
                from metahandler import metahandlers
                metaget = metahandlers.MetaData(preparezip=False)
                metaget.get_meta('movie', title ,year=str(year))
                metaget.change_watched(type, '', id, season='', episode='', year='', watched=playcount)
            except Exception,e:
                self.log('setWatchedStatus, MOVIE:META Failed! ' + str(e))
            # try:
                # if trakt.getTraktAddonMovieInfo() == False: trakt.markMovieAsWatched(self.imdb)
                # trakt.syncMovies()
            # except:
                # pass
        elif type in ['episode','tvshow']:
            try:
                json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "playcount" : %s }, "id": 1 }' % (str(epid), str(playcount)))
                self.channelList.sendJSON(json_query);  
            except Exception,e:
                self.log('setWatchedStatus, TV:DBID Failed! ' + str(e))
            try:
                from metahandler import metahandlers
                metaget = metahandlers.MetaData(preparezip=False)
                metaget.get_meta('tvshow', title, imdb_id=id)
                metaget.get_episode_meta(title, id, season, episode)
                metaget.change_watched(type, '', id, season=season, episode=episode, year='', watched=playcount)
            except Exception,e:
                self.log('setWatchedStatus, TV:META Failed! ' + str(e))
            # try:
                # if trakt.getTraktAddonEpisodeInfo() == False: trakt.markEpisodeAsWatched(self.tvdb, self.season, self.episode)
                # trakt.syncTVShows()
            # except:
                # pass


    def setWatchedStatus(self):
        self.log('setWatchedStatus')
        if REAL_SETTINGS.getSetting("Disable_Watched") == "true" and isLowPower() != True:
            try:
                type = getProperty("OVERLAY.Type")
                title = getProperty("OVERLAY.Cleantitle")
                id = getProperty("OVERLAY.ID")
                dbid = int(getProperty("OVERLAY.DBID"))
                epid = int(getProperty("OVERLAY.EPID"))
                season = int(getProperty("OVERLAY.Season"))
                episode = int(getProperty("OVERLAY.Episode"))
                year = int(getProperty("OVERLAY.Year"))
                playcount = int(getProperty("OVERLAY.Playcount"))   
                self.ChangeWatchedTimer = threading.Timer(0.5, self.setWatchedStatus_Thread, [type, title, year, id, dbid, epid, season, episode, playcount])
                self.ChangeWatchedTimer.name = "ChangeWatchedTimer"
                if self.ChangeWatchedTimer.isAlive():
                    self.ChangeWatchedTimer.cancel()
                    self.ChangeWatchedTimer.join()
                self.ChangeWatchedTimer.start() 
            except:
                pass

                
    def clearProp(self, pType='OVERLAY'):
        self.log("clearProp")   
        clearProperty("%s.type1ART"%pType)
        clearProperty("%s.type2ART"%pType)    
        clearProperty("%s.Year"%pType)
        clearProperty("%s.ID"%pType)
        clearProperty("%s.Genre"%pType)
        clearProperty("%s.Rating"%pType)
        clearProperty("%s.Tagline"%pType)
        clearProperty("%s.Title"%pType)
        clearProperty("%s.Showtitle"%pType)
        clearProperty("%s.Cleantitle"%pType)
        clearProperty("%s.Chtype"%pType)
        clearProperty("%s.Mpath"%pType)
        clearProperty("%s.Mediapath"%pType)
        clearProperty("%s.Chname"%pType)
        clearProperty("%s.SEtitle"%pType)
        clearProperty("%s.Type"%pType)
        clearProperty("%s.DBID"%pType)
        clearProperty("%s.EPID"%pType)
        clearProperty("%s.Description"%pType)
        clearProperty("%s.Playcount"%pType)
        clearProperty("%s.Season"%pType)
        clearProperty("%s.Episode"%pType)
        clearProperty("%s.isNEW"%pType)
        clearProperty("%s.isManaged"%pType)

          
    def end(self):
        self.log('end')    
        self.background.setVisible(True)
        self.isExiting = True 
        # Prevent the player from setting the sleep timer
        self.Player.stopped = True
        self.background.setLabel('Exiting: PseudoTV Live')
        setProperty("OVERLAY.LOGOART",THUMB) 
        xbmc.executebuiltin("PlayerControl(repeatoff)")
        curtime = time.time()
        updateDialog = xbmcgui.DialogProgress()
        updateDialog.create("PseudoTV Live", "Exiting")
        self.UPNPcontrol('stop')

        if CHANNEL_SHARING == True and self.isMaster:
            updateDialog.update(0, "Exiting", "Removing File Locks")
            self.background.setLabel('Exiting: Removing File Locks')
            GlobalFileLock.unlockFile('MasterLock')
        GlobalFileLock.close()
        
        # destroy window
        try:
            del self.myDVR
            del self.myApps
            del self.myOndemand
        except:
            pass
            
        # active threads are a pain to monitor, encapsulate in tries to avoid calling inactive threads.
        try:
            if self.playerTimer.isAlive():
                self.playerTimer.cancel()
                self.playerTimer.join()

            if self.Player.isPlaying():
                self.lastPlayTime = self.Player.getTime()
                self.lastPlaylistPosition = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
                self.Player.stop()
        except:
            pass

        updateDialog.update(1, "Exiting", "Stopping Timers")
        self.background.setLabel('Exiting: Stopping Timers')
        
        try:
            if self.channelLabelTimer.isAlive():
                self.channelLabelTimer.cancel()
                self.channelLabelTimer.join()
        except:
            pass
        try:
            if self.GotoChannelTimer.isAlive():
                self.GotoChannelTimer.cancel()
        except:
            pass
            
        updateDialog.update(2)

        try:
            if self.notificationTimer.isAlive():
                self.notificationTimer.cancel()
                self.notificationTimer.join()
        except:
            pass
        try:
            if self.infoTimer.isAlive():
                self.infoTimer.cancel()
                self.infoTimer.join()
        except:
            pass

        try:
            if self.popTimer.isAlive():
                self.popTimer.cancel()
                self.infoTimer.join()
        except:
            pass
            
        updateDialog.update(3)

        try:
            if self.sleepTimeValue > 0:
                if self.sleepTimer.isAlive():
                    self.sleepTimer.cancel()
        except:
            pass

        updateDialog.update(4, "Exiting", "Stopping Threads")  
        self.background.setLabel('Exiting: Stopping Threads')
          
        try:
            if self.MenuControlTimer.isAlive():
                self.MenuControlTimer.cancel()
        except:
            pass
        try:
            if self.getTMPSTRTimer.isAlive():
                self.getTMPSTRTimer.cancel()
        except:
            pass
        try:
            if self.channelThread_Timer.isAlive():
                self.channelThread_Timer.cancel()
        except:
            pass    
        try:
            if self.FEEDtoggleTimer.isAlive():
                self.FEEDtoggleTimer.cancel()
        except:
            pass 
        try:
            if self.ReminderTimer.isAlive():
                self.ReminderTimer.cancel()
                self.ReminderTimer.join()
        except:
            pass   
        try:
            if self.ChangeWatchedTimer.isAlive():
                self.ChangeWatchedTimer.cancel()
                self.ChangeWatchedTimer.join()
        except:
            pass 
        try:
            if download_silentThread.isAlive():
                download_silentThread.cancel()
        except:
            pass   
        try:
            if self.ArtdownloaderDownloadArtTimer.isAlive():
                self.ArtdownloaderDownloadArtTimer.cancel()
        except:
            pass   

        updateDialog.update(5, "Exiting", "Stopping Artwork Threads")
        self.background.setLabel('Exiting: Stopping Artwork Threads')  
            
        try: 
            if self.ArtThread.isAlive():
                self.ArtThread.cancel()
        except:
            pass 
        try:
            if self.isNewTimer.isAlive():
                self.isNewTimer.cancel()
        except:
            pass  
        try:
            if self.isManagedTimer.isAlive():
                self.isManagedTimer.cancel()
        except:
            pass   
        try:
            if self.setPropTimer.isAlive():
                self.setPropTimer.cancel()
        except:
            pass   

        updateDialog.update(6)

        if self.channelThread.isAlive():
            for i in range(30):
                try:
                    self.channelThread.join(1.0)
                except:
                    pass

                if self.channelThread.isAlive() == False:
                    break

                updateDialog.update(7 + i, "Exiting", "Stopping Channel Threads")
                self.background.setLabel('Exiting: Stopping Channel Threads')  

            if self.channelThread.isAlive():
                self.log("Problem joining channel thread", xbmc.LOGERROR)

        if self.isMaster:
            try:#Set Startup Channel
                SUPchannel = int(REAL_SETTINGS.getSetting('SUPchannel'))                
                if SUPchannel == 0:
                    REAL_SETTINGS.setSetting('CurrentChannel', str(self.currentChannel))    
            except:
                pass
            ADDON_SETTINGS.setSetting('LastExitTime', str(int(curtime)))

        if self.timeStarted > 0 and self.isMaster:
            updateDialog.update(35, "Exiting", "Saving Settings")
            self.background.setLabel('Exiting: Saving Settings')  
            validcount = 0

            for i in range(self.maxChannels):
                if self.channels[i].isValid:
                    validcount += 1
            
            if validcount > 0:
                incval = 65.0 / float(validcount)

                for i in range(self.maxChannels):
                    updateDialog.update(35 + int((incval * i)))
                    self.background.setLabel('Exiting: Saving Settings (' + str(int((incval * i))/10) + '%)')
                    
                    if self.channels[i].isValid:
                        chtype = self.getChtype(i + 1)
                        if self.channels[i].mode & MODE_RESUME == 0:
                            ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(int(curtime - self.timeStarted + self.channels[i].totalTimePlayed)))
                        else:
                            if i == self.currentChannel - 1:
                                # Determine pltime...the time it at the current playlist position
                                pltime = 0
                                self.log("position for current playlist is " + str(self.lastPlaylistPosition))
                                for pos in range(self.lastPlaylistPosition):
                                    pltime += self.channels[i].getItemDuration(pos)
                                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(pltime + self.lastPlayTime))  
                            else:
                                tottime = 0
                                for j in range(self.channels[i].playlistPosition):
                                    tottime += self.channels[i].getItemDuration(j)
                                tottime += self.channels[i].showTimeOffset
                                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_time', str(int(tottime)))
                self.storeFiles()
        
        self.egTrigger('PseudoTV_Live - Exiting')
        REAL_SETTINGS.setSetting('LogoDB_Override', "false") 
        REAL_SETTINGS.setSetting('Normal_Shutdown', "true")
        self.background.setLabel('Exiting: Shutting Down')  
        updateDialog.close()
        self.close()


    def isWindowOpen(self):
        if getProperty("PTVL.EPG_Opened") == "true":
            return 'EPG'
        elif getProperty("PTVL.DVR_Opened") == "true":
            return 'DVR'
        elif getProperty("PTVL.OnDemand_Opened") == "true":
            return 'OnDemand'
        elif getProperty("PTVL.APPS_Opened") == "true":
            return 'APPS'
            
        
    def windowSwap(self, window):
        self.log('windowSwap = ' + window)
        # close open window
        if getProperty("PTVL.EPG_Opened") == "true":
            self.myEPG.closeEPG()
        elif getProperty("PTVL.DVR_Opened") == "true":
            self.myDVR.closeDVR()
        elif getProperty("PTVL.OnDemand_Opened") == "true":
            self.myOndemand.closeOndemand()
        elif getProperty("PTVL.APPS_Opened") == "true":
            self.myApps.closeAPPS()
        xbmc.sleep(55)
        # open new window
        if window.upper() == 'EPG':
            self.myEPG.doModal()
        elif window.upper() == 'DVR':
            self.myDVR.doModal()
        elif window.upper() == 'ONDEMAND':
            self.myOndemand.doModal()
        elif window.upper() == 'APPS':
            self.myApps.doModal()

          
    def getChtype(self, channel):
        try:
            Chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
        except:
            Chtype = 0
        self.logDebug('getChtype, channel = '+str(channel)+', Chtype = ' + str(Chtype))
        return Chtype
           
           
    def getChname(self, channel):
        try:
            Chname = self.channels[channel].name
        except:
            Chname = ''
        self.logDebug('getChname, channel = '+str(channel)+', Chname = ' + Chname)
        return Chname
           
           
    def toggleSetVisible(self, key):
        if self.getControl(key).getVisible == True:
            self.setVisible(key, False)
        else:
            self.setVisible(key, True)
            
            
    def setVisible(self, key, state):
        self.getControl(key).setVisible(state)
        
        
    def playsetresolved(self, url, setresolved=True):
        if setresolved == True:
            item = xbmcgui.ListItem(getProperty("OVERLAY.Title"), iconImage=getProperty("OVERLAY.LOGOART"))
            item.setInfo(type='Video', infoLabels={'Title':getProperty("OVERLAY.Title")})
            item.setProperty("IsPlayable","true")
            item.setPath(url)
            self.Player.play(item)
            # xbmcplugin.setResolvedUrl(pluginhandle, True, )
        elif setresolved == 'PlayMedia':
            # if not mediapath.startswith('PlayMedia'):
            # mediapath = ('PlayMedia('+mediapath+')')
            xbmc.executebuiltin(tidy(url).replace(',', ''))
        else:
            xbmc.executebuiltin('XBMC.RunPlugin('+url+')')
# xbmc.executebuiltin('StartAndroidActivity("com.netflix.mediaclient"),return')
# call weather
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"weather"},"id":18}
# set fullscreen
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.SetFullscreen","params":{"fullscreen":true},"id":19}
# call vod
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"videoosd"},"id":5}
# call a/settings2
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"osdaudiosettings"},"id":17}
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"osdvideosettings"},"id":16}