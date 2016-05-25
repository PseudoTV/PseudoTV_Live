#   Copyright (C) 2015 Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import os, sys, re
import datetime, time, threading, _strptime
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import IDLE

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
from parsers import ustvnow

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
    
from FileAccess import FileLock
GlobalFileLock = FileLock()

class MyPlayer(xbmc.Player):
    
    def __init__(self):
        self.log('__init__')
        xbmc.Player.__init__(self, xbmc.Player())
        self.stopped = False
        self.ignoreNextStop = False
        
        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Player: ' + msg, level)

        
    def getPlayerFile(self):
        try:
            return (self.getPlayingFile()).replace("\\\\","\\")
        except:
            return ''
    

    def getPlayerTotTime(self):
        try:
            return int(self.getTotalTime())
        except:
            return 0
            
            
    def getPlayerTime(self):
        try:
            return int(self.getTime())
        except:
            return 0
    
    
    def getPlayerTitle(self):
        try:
            title = xbmc.getInfoLabel('Player.Title')
            if not title:
                title = xbmc.getInfoLabel('VideoPlayer.Title')
        except:
            title = ''
        return title
        
        
    def isPlayingValid(self, time=500):
        Playing = False
        if self.isPlaybackPaused() == True:
            Playing = True
        else:
            if self.isPlaybackValid() == True:
                sample_time = self.getPlayerTime()
                xbmc.sleep(time)
                if self.getPlayerTime() > sample_time:
                    Playing = True
        self.log('isPlayingValid = ' + str(Playing))
        return Playing
        
        
    def isPlaybackValid(self):
        Playing = False
        xbmc.sleep(10)
        if self.isPlaying():
            Playing = True
        self.log('isPlaybackValid = ' + str(Playing))
        return Playing

    
    def isSomethingPlaying(self):
        if self.overlay.isExiting == True:
            return True
            
        if isLowPower() == True:
            isKodiPlaying = self.isPlaybackValid()
        else:
            isKodiPlaying = self.isPlayingValid()
        self.log("isSomethingPlaying, = " + str(isKodiPlaying))
        return isKodiPlaying
        
        
    def waitForVideoPlayback(self):
        self.log("waiting for VideoPlayback")
        while self.isSomethingPlaying() == False:
            xbmc.sleep(10)
        return
    
    
    def isPlaybackPaused(self):
        Paused = bool(xbmc.getCondVisibility("Player.Paused"))
        self.log('isPlaybackPaused = ' + str(Paused))
        return Paused

    
    def resumePlayback(self):
        self.log('resumePlayback')
        if self.isPlaybackPaused():
            self.pause()

    
    def onPlayBackPaused(self):
        self.log('onPlayBackPaused')
        self.overlay.Paused()

        
    def onPlayBackResumed(self):
        self.log('onPlayBackResumed')
        self.overlay.Resume()
    
    
    def onPlaybackAction(self):
        # self.waitForVideoPlayback()
        # show pip videowindow
        setProperty("PTVL.VideoWindow","true")
        if self.overlay.infoOnChange == True:
            self.overlay.showInfo()
        else:
            self.overlay.setShowInfo()
        self.overlay.showChannelLabel(self.overlay.currentChannel)
        
        # playback starts paused, resume automatically.
        self.resumePlayback()
        
        self.overlay.setBackgroundVisible(False)
        
        # send play command to upnp
        self.overlay.UPNPcontrol('play', self.getPlayerFile(), self.getPlayerTime())
        
        # trakt scrob. playing show
        if REAL_SETTINGS.getSetting("TraktScrob") == "true":
            setTraktScrob()

                  
    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        setProperty('PTVL.PLAYER_LOG',self.getPlayerFile())
        if self.isPlaybackValid() == True:
            # devise a way to detect ondemand playback todo   
            # fix for fullscreen video bug when playback is started while epg is opened.
            if getProperty("PTVL.VideoWindow") == "true" and self.overlay.isWindowOpen() != False:
                self.overlay.windowSwap(self.overlay.isWindowOpen())
            self.onPlaybackAction()


    def onDemandEnded(self):
        self.log('onDemandEnded') 
        #Force next playlist item after impromptu ondemand playback
        if self.overlay.OnDemand == True:
            self.overlay.OnDemand = False  
            xbmc.executebuiltin("PlayerControl(SmallSkipForward)")
            
            
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        # resume playlist after ondemand
        self.onDemandEnded()
        # clear trakt scrob.
        clearTraktScrob()
            
            
    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        # set static videowindow
        setProperty("PTVL.VideoWindow","false")
        self.overlay.clearProp('OVERLAY.PLAYING')
        self.overlay.setBackgroundVisible(True)
        
        # resume playlist after ondemand
        self.onDemandEnded()
        
        # clear trakt scrob.
        clearTraktScrob()
        
        # reset ignoreNextStop
        if self.ignoreNextStop == True:
            self.ignoreNextStop = False

        if self.overlay.DisablePlayback == True and getProperty("PTVL.EPG_Opened") == "false":
            self.overlay.openEPG()

            
# overlay window to catch events and change channels
class TVOverlay(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.log('__init__')
        sys.setcheckinterval(25)
        # initialize all timers
        # hide timers
        self.channelLabelTimer = threading.Timer(2.0, self.hideChannelLabel)
        self.infoTimer = threading.Timer(2.0, self.hideInfo)
        self.popTimer = threading.Timer(2.0, self.hidePOP)
        self.MenuControlTimer = threading.Timer(2.0, self.MenuControl)      
        
        # loop timers 
        self.playerTimer = threading.Timer(1.0, self.playerTimerAction)
        self.cronTimer = threading.Timer(1.0, self.cronJob)
        self.notificationTimer = threading.Timer(60.0, self.notificationAction)

        # single queue timers
        self.setPropTimer = threading.Timer(0.1, self.setProp_thread)
        self.setArtworkTimer = threading.Timer(0.1, self.setArtwork_Thread)
        self.GotoChannelTimer = threading.Timer(0.1, self.setChannel)
        self.UPNPcontrolTimer = threading.Timer(2.0, self.UPNPcontrol_thread)
        self.getTMPSTRTimer = threading.Timer(0.1, self.getTMPSTR_Thread)
        self.ReminderTimer = threading.Timer(2.0, self.showReminder)      
        self.ChangeWatchedTimer = threading.Timer(5.0, self.setWatchedStatus_Thread)
        self.sleepTimer = threading.Timer(2.0, self.sleepPrompt)
        self.SleepTimerCountdownTimer = threading.Timer(60.0, self.SleepTimerCountdown)
        self.idleTimer = threading.Timer(2.0, self.sleepPrompt)
        self.idleTimerCountdownTimer = threading.Timer(1.0, self.IdleTimerCountdown)
        
        # initialize all variables
        self.channels = []
        self.channelLabel = [] 
        self.OnNowLst = []  
        self.OnNextLst = [] 
        self.OnNowArtLst = [] 
        self.OnNextArtLst = [] 
        self.ReminderLst = [] 
        self.hideShortInfo = False
        self.infoOnChange = True  
        self.infoOnStart = False
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
        self.notificationShowedNotif = False
        self.isExiting = False       
        self.showingSleep = False
        self.showingReminder = False
        self.ignoreInfoAction = False
        self.OnDemand = False 
        self.showChannelBug = False
        self.showNextItem = False
        self.ignoreSeektime = False
        self.inputChannel = -1
        self.seektime = 0
        self.lastActionTime = 0  
        self.timeStarted = 0  
        self.currentChannel = 1
        self.infoOffset = 0
        self.invalidatedChannelCount = 0  
        self.sleepTimeValue = 0
        self.notificationLastChannel = 0 
        self.notificationLastShow = 0
        self.maxChannels = 0
        self.fifteenMin_Job = 0
        self.tenMin_Job = 0
        self.fiveMin_Job = 0
        self.twoMin_Job = 0
        self.oneMin_Job = 0
        self.notPlayingCount = 0 
        self.FailedPlayingCount = 0 
        self.shortItemLength = 240
        self.runningActionChannel = 0
        self.channelDelay = 0
        self.cron_uptime = 0
        self.sleep_cntDown = IDLE_DELAY  
        self.channelbugcolor = CHANBUG_COLOR
        self.notPlayingAction = 'Up'
        self.Browse = ''
        self.showSeasonEpisode = REAL_SETTINGS.getSetting("ShowSeEp") == "true"
        self.InfTimer = INFOBAR_TIMER[int(REAL_SETTINGS.getSetting('InfoTimer'))] 
        self.ActionTimeInt = float(REAL_SETTINGS.getSetting("ActionTimeInt"))
        self.PlayTimeoutInt = float(REAL_SETTINGS.getSetting("PlayTimeoutInt"))
        self.MUTE = REAL_SETTINGS.getSetting('enable_mute') == "true"
        self.FavChanLst = (REAL_SETTINGS.getSetting("FavChanLst")).split(',')
        self.DirectInput = REAL_SETTINGS.getSetting("DirectInput") == "true"
        self.SubState = REAL_SETTINGS.getSetting("EnableSubtitles") == "true"
        self.DisablePlayback = REAL_SETTINGS.getSetting("DisablePlayback") == "true"   
        setProperty("PTVL.BackgroundLoading","true") 
        self.log('ActionTimeInt = ' + str(self.ActionTimeInt))
        self.log('PlayTimeoutInt = ' + str(self.PlayTimeoutInt))
              
        if REAL_SETTINGS.getSetting("UPNP1") == "true" or REAL_SETTINGS.getSetting("UPNP2") == "true" or REAL_SETTINGS.getSetting("UPNP3") == "true":
            self.enableUPNP = True
        else:
            self.enableUPNP = False
            
        for i in range(3):
            try:
                self.channelLabel.append(xbmcgui.ControlImage(50 + (50 * i), 50, 50, 50, IMAGES_LOC + 'solid.png', colorDiffuse = self.channelbugcolor))
                self.addControl(self.channelLabel[i])
                self.channelLabel[i].setVisible(False)
            except:
                pass
              
        self.monitor = xbmc.Monitor()
        self.Player = MyPlayer()
        self.Player.overlay = self
        self.actionSemaphore = threading.BoundedSemaphore()
        self.channelThread = ChannelListThread()
        self.channelThread.myOverlay = self 
        self.Artdownloader = Artdownloader()
        self.IPPlst = self.chkUPNP() # collect upnp mirror ips
        self.doModal()
        self.log('__init__ return')

        
    def resetChannelTimes(self):
        for i in range(self.maxChannels):
            self.channels[i].setAccessTime(self.timeStarted - self.channels[i].totalTimePlayed)
            

    # override the doModal function so we can setup everything first
    def onInit(self):
        self.log('onInit')
        self.log('PTVL Version = ' + ADDON_VERSION)   
        self.channelList = ChannelList()
        self.Upnp = Upnp()
        self.background = self.getControl(101)
        setBackgroundLabel('Please Wait')
        self.getControl(119).setVisible(False)
        self.getControl(120).setVisible(False)
        self.getControl(102).setVisible(False)
        self.getControl(104).setVisible(False)
        self.getControl(222).setVisible(False)
        self.getControl(130).setVisible(False)
        self.getControl(7000).setVisible(False)
        setProperty("OVERLAY.LOGOART",THUMB)
        setProperty("PTVL.INIT_CHANNELSET","false")
        self.setBackgroundVisible(True)
                  
        #xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"%s","value":%s}}' %('lookandfeel.enablerssfeeds','true'))()
        try:
            Normal_Shutdown = REAL_SETTINGS.getSetting('Normal_Shutdown') == "true"
        except:
            REAL_SETTINGS.setSetting('Normal_Shutdown', "true")
            Normal_Shutdown = REAL_SETTINGS.getSetting('Normal_Shutdown') == "true"
                    
        # Clear Setting2 for fresh autotune
        if REAL_SETTINGS.getSetting("Autotune") == "true" and REAL_SETTINGS.getSetting("Warning1") == "true":
            self.log('Autotune onInit') 
            setBackgroundLabel('Initializing, Autotuning')

            #Reserve channel check            
            if REAL_SETTINGS.getSetting("reserveChannels") == "false":
                self.log('Autotune not reserved') 
                if getSize(SETTINGS_FLE) > SETTINGS_FLE_DEFAULT_SIZE:
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

        updateDialog = xbmcgui.DialogProgressBG()
        updateDialog.create("PseudoTV Live", "Initializing")
        setBackgroundLabel('Initializing: Video Mirroring')
        setBackgroundLabel('Initializing: Channel Configurations')
        self.UPNPcontrol('stop')
        self.backupFiles(updateDialog)
        ADDON_SETTINGS.loadSettings()
        
        if CHANNEL_SHARING == True:
            FileAccess.makedirs(LOCK_LOC)
            REAL_SETTINGS.setSetting("IncludeBCTs","false")
            updateDialog.update(70, "Initializing", "Checking Other Instances")
            setBackgroundLabel('Initializing: Channel Sharing')
            self.isMaster = GlobalFileLock.lockFile("MasterLock", False)
        else:
            self.isMaster = True

        updateDialog.update(85, "Initializing", "PseudoTV Live")
        setBackgroundLabel('Initializing: PseudoTV Live')

        if self.isMaster:
            migratemaster = Migrate()     
            migratemaster.migrate()
            
        self.textureButtonFocusAlt = MEDIA_LOC + BUTTON_FOCUS_ALT
        self.timeButtonNoFocus = MEDIA_LOC + TIME_BUTTON
        self.currentPlayInfoTime = self.getControl(5006)
        self.currentPlayInfoTime_xpos, self.currentPlayInfoTime_ypos = self.getControl(5006).getPosition()

        self.myEPG = EPGWindow("script.pseudotv.live.EPG.xml", ADDON_PATH, Skin_Select)
        self.myDVR = DVR("script.pseudotv.live.DVR.xml", ADDON_PATH, Skin_Select)
        self.myOndemand = Ondemand("script.pseudotv.live.Ondemand.xml", ADDON_PATH, Skin_Select)
        self.myApps = APPS("script.pseudotv.live.Apps.xml", ADDON_PATH, Skin_Select)
        self.myIdle = IDLE.GUI("script.pseudotv.live.Idle.xml", ADDON_PATH, "Default")
        
        self.myEPG.MyOverlayWindow = self
        self.myDVR.MyOverlayWindow = self
        self.myOndemand.MyOverlayWindow = self
        self.myApps.MyOverlayWindow = self
                    
        # Don't allow any actions during initialization
        self.actionSemaphore.acquire()
        self.timeStarted = time.time() 
        updateDialog.update(95, "Initializing", "Channels")
        setBackgroundLabel('Initializing: Channels')
        updateDialog.close()

        if self.readConfig() == False:
            return
        
        self.myEPG.channelLogos = self.channelLogos
        self.maxChannels = len(self.channels)

        if self.maxChannels == 0 and REAL_SETTINGS.getSetting("Autotune") == "false":
            autoTune = False
            if yesnoDialog("No Channels Configured", "Would you like PseudoTV Live to Auto Tune Channels?") == True:
                REAL_SETTINGS.setSetting("Autotune","true")
                REAL_SETTINGS.setSetting("Warning1","true")
                REAL_SETTINGS.setSetting('AT_LIMIT', "0")
                REAL_SETTINGS.setSetting("autoFindLivePVR","true")
                REAL_SETTINGS.setSetting("autoFindNetworks","true")
                REAL_SETTINGS.setSetting("autoFindMovieGenres","true")
                REAL_SETTINGS.setSetting("autoFindRecent","true")
                
                if isUSTVnow() == True:
                    REAL_SETTINGS.setSetting("autoFindUSTVNOW","true")
                    
                if isCompanionInstalled() == True:
                    REAL_SETTINGS.setSetting("autoFindCommunity_PseudoNetworks","true")
                
                #TEMP isCom pass
                setProperty("Verified_Community", 'true')
                REAL_SETTINGS.setSetting("autoFindCommunity_Youtube_Networks","true")
                REAL_SETTINGS.setSetting("autoFindCommunity_RSS","true")
                autoTune = True
                
                if autoTune:
                    self.end('Restart')
                    return
            else:
                REAL_SETTINGS.setSetting("Autotune","false")
                REAL_SETTINGS.setSetting("Warning1","false")
                self.Error('Unable to find any channels. \nPlease go to the Addon Settings to configure PseudoTV Live.')
                REAL_SETTINGS.openSettings()
                self.end()
                return 
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

        self.artOVERLAY_Types = list(set([getProperty("OVERLAY.type1"),getProperty("OVERLAY.type2"),getProperty("OVERLAY.type3"),getProperty("OVERLAY.type4")]))
        self.artEPG_Types = list(set([getProperty("EPG.type1"),getProperty("EPG.type2"),getProperty("EPG.type3"),getProperty("EPG.type4")]))

        try:
            if self.forceReset == False:
                self.currentChannel = self.fixChannel(int(REAL_SETTINGS.getSetting("CurrentChannel")))
            else:
                self.currentChannel = self.fixChannel(1)
        except:
            self.currentChannel = self.fixChannel(1)
        self.lastPlayingChannel = self.currentChannel
        
        if self.backgroundUpdating < 2 or self.isMaster == False:
            self.channelThread.name = "ChannelThread"
            self.channelThread.start()
        else:
            self.postBackgroundLoading()
        
        if REAL_SETTINGS.getSetting('INTRO_PLAYED') != 'true':    
            self.setBackgroundVisible(False)
            self.Player.play(INTRO)
            time.sleep(17)
            self.setBackgroundVisible(True)
            REAL_SETTINGS.setSetting("INTRO_PLAYED","true")    
        self.resetChannelTimes()
        
        # start playing video
        if self.DisablePlayback == False:
            self.channelThreadpause = True
            self.setChannel(self.fixChannel(self.currentChannel))
            setProperty("PTVL.VideoWindow","true")
        else:
            self.channelThreadpause = False
            setProperty("PTVL.VideoWindow","false")
            
        self.idleReset() 
        self.actionSemaphore.release()
        self.loadReminder()
        self.FEEDtoggle()   
        REAL_SETTINGS.setSetting('Normal_Shutdown', "false")
                
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
                
        #start loop timers
        self.playerTimer.start()
        self.cronTimer.start()
        self.notificationTimer.start()
        
        if self.DisablePlayback == True:
            self.openEPG()
        
        egTrigger('PseudoTV_Live - Starting')  
        self.log('onInit return')
            

    # setup all basic configuration parameters, including creating the playlists that
    # will be used to actually run this thing
    def readConfig(self):
        self.log('readConfig')
        # Sleep setting is in 30 minute increments...so multiply by 30, and then 60 (min to sec)
        self.idleTimeValue = int(REAL_SETTINGS.getSetting('AutoOff')) * 1800
        self.log('Auto off is ' + str(self.idleTimeValue))
        self.sleepTimeMode = int(REAL_SETTINGS.getSetting("AutoOff_Mode"))
        self.log('Auto off Mode is ' + str(self.sleepTimeMode))
        self.infoOnChange = REAL_SETTINGS.getSetting("InfoOnChange") == "true"
        self.log('Show info label on channel change is ' + str(self.infoOnChange))
        self.infoOnStart = REAL_SETTINGS.getSetting("infoOnStart") == "true"
        self.log('Show info label on vide start is ' + str(self.infoOnStart))
        self.showChannelBug = REAL_SETTINGS.getSetting("ShowChannelBug") == "true"
        self.log('Show channel bug - ' + str(self.showChannelBug))
        self.forceReset = REAL_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.backgroundUpdating = int(REAL_SETTINGS.getSetting("ThreadMode"))
        self.channelResetSetting = REAL_SETTINGS.getSetting('ChannelResetSetting')
        self.hideShortItems = REAL_SETTINGS.getSetting("HideClips") == "true"
        self.log("Hide Short Items - " + str(self.hideShortItems))
        self.shortItemLength = SHORT_CLIP_ENUM[int(REAL_SETTINGS.getSetting("ClipLength"))]
        self.log("Short item length - " + str(self.shortItemLength))
        self.seekForward = SEEK_FORWARD[int(REAL_SETTINGS.getSetting("SeekForward"))]
        self.seekBackward = SEEK_BACKWARD[int(REAL_SETTINGS.getSetting("SeekBackward"))]
        self.channelDelay = int(REAL_SETTINGS.getSetting("channelDelay")) * 250
        
        if SETTOP:
            self.backgroundUpdating = 0
            self.channelResetSetting = 0
        self.log('Background Updating is ' + str(self.backgroundUpdating))
        self.log('Channel Reset Setting is ' + str(self.channelResetSetting))
       
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
    def Error(self, line1= '', line2= '', line3= ''):
        self.log('FATAL ERROR: ' + line1 + " " + line2, xbmc.LOGFATAL)
        Error(line1, line2, line3)
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

        for i in range(CHANNEL_LIMIT):
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
        okDialog(data, header = 'PseudoTV Live - Announcement')

        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('TVOverlay: ' + msg, level)

                
    def setOnNowArt(self):
        self.log('setOnNowArt')
        try:    
            pos = self.OnNowControlList.getSelectedPosition()
            setProperty("OVERLAY.ONNOW_ART",self.OnNowArtLst[pos])
        except Exception,e:
            self.log('setOnNowArt, failed! ' + str(e))

        
    def getOnNow(self, offdif=0):
        self.log('getOnNow')
        ChannelGuideLst = []
        OnNowDict = []
        OnNowLst = []
        OnNowArtLst = []
        
        if getProperty("PTVL.ONNOW_RUNNING") != "true":
            setProperty("PTVL.ONNOW_RUNNING","true")
            try:
                for Channel in range(self.maxChannels):
                    if self.channels[Channel].isValid:
                        chnum = Channel + 1
                        chtype = self.getChtype(chnum)
                        chname = self.getChname(chnum)
                        chlogo = self.getChlogo(chnum)
                        
                        # prepare channel guide
                        channel_dict = {'Chtype': chtype, 'Chnum': chnum, 'Chname': chname, 'LOGOART': chlogo}
                        ChannelGuideLst.append(channel_dict)
                        
                        # prepare info
                        position = self.getPlaylistPOS(chtype, chnum, offdif)
                        label = self.channels[Channel].getItemTitle(position)
                        SEtitle = self.channels[Channel].getItemEpisodeTitle(position)
                        Description = self.channels[Channel].getItemDescription(position)
                        genre = self.channels[Channel].getItemgenre(position)
                        LiveID = self.channels[Channel].getItemLiveID(position)
                        Duration = self.channels[Channel].getItemDuration(position) 
                        timestamp = self.channels[Channel].getItemtimestamp(position) 
                        mediapath = self.channels[Channel].getItemFilename(position)  
                    
                        ChanColor = (self.channelbugcolor).replace('0x','')
                        if self.isChanFavorite(chnum):
                            ChanColor = 'gold'

                        # SepColor = (self.channelbugcolor).replace('0x','')
                        # if genre not in [COLOR_GRAY_TYPE + COLOR_ltGRAY_TYPE]:
                            # SepColor = self.getGenreColor(genre).replace('#','')+'00'
                            
                        # prepare artwork
                        type, id, dbepid, managed, playcount, rating, hd, cc, stars, year = self.channelList.unpackLiveID(LiveID)
                        year, title, showtitle = getTitleYear(label, year)
                        label = ("[COLOR=%s][B]%d|[/B][/COLOR] %s" % (ChanColor, chnum, title))
                        season, episode, swtitle = SEinfo(SEtitle, self.showSeasonEpisode)
                        dbid, epid = splitDBID(dbepid)
                        mpath = getMpath(mediapath)
                        content_type = type.replace("tvshow","episode").replace("other","video").replace("music","musicvideo")   
                        tagline = SEtitle                      
                        art = self.findArtwork(type, title, year, chtype, chname, id, dbid, mpath, getProperty("OVERLAY.ONNOW_TYPE"))
                        poster, fanart = self.getArtwork(type, title, year, chtype, chname, id, dbid, mpath)
                        OnNowLst.append(label)
                        OnNowArtLst.append(art)
                        onnow_dict = {'Chtype': chtype, 'Label': label, 'Chnum': chnum, 'Chname': chname, 'Type': type, 'Showtitle': showtitle, 'Cleantitle': title, 'Year': year, 'Title': title, 'SEtitle': SEtitle, 'SWtitle': swtitle,
                        'Season': season, 'Episode': episode, 'Description': Description, 'Rating': rating, 'Managed': managed, 'Playcount': playcount, 'Genre': genre, 'content_type': content_type, 'ID': id, 'DBID': dbid, 'EPID': epid,
                        'Mpath': mpath, 'Duration': Duration, 'Timestamp': timestamp, 'Mediapath': mediapath, 'Tagline': tagline, 'poster': poster, 'fanart': fanart, 'LOGOART': chlogo, 'ONNOW_ART': art}
                        OnNowDict.append(onnow_dict)

                setProperty("OVERLAY.ChannelGuide", str(ChannelGuideLst))
                del ChannelGuideLst[:]
            except Exception,e:
                self.log('getOnNow, failed! ' + str(e))
        setProperty("PTVL.ONNOW_RUNNING","false") 
        return OnNowLst, OnNowArtLst, OnNowDict
    
                 
    def setOnNow(self):
        self.log('setOnNow')
        if isLowPower() == True:
            return
            
        self.OnNowLst, self.OnNowArtLst, OnNowDict = self.getOnNow()
        setProperty("OVERLAY.OnNowLst", str(OnNowDict))
        self.OnNextLst, self.OnNextArtLst, OnNextDict = self.getOnNow(1)
        setProperty("OVERLAY.OnNextLst", str(OnNextDict))    
        

    def clearOnNow(self):
        self.log('clearOnNow')
        clearProperty("OVERLAY.OnNowLst")
        clearProperty("OVERLAY.OnNextLst")
        clearProperty("OVERLAY.ChannelGuide")

        
    def showOnNow(self):
        self.log("showOnNow")
        if not self.showingMenuAlt:
            if len(self.OnNowLst) > 0:
                show_busy_dialog()
                curchannel = 0
                self.showingMenuAlt = True
                
                # set Position
                sidex, sidey = self.getControl(132).getPosition()
                sidew = self.getControl(132).getWidth()
                sideh = self.getControl(132).getHeight()
                listWidth = self.getControl(132).getLabel()
                tabHeight = self.getControl(1001).getHeight()
                self.OnNowControlList = xbmcgui.ControlList(sidex, sidey, sidew, sideh, 'font12', self.myEPG.textcolor, MEDIA_LOC + BUTTON_NO_FOCUS, MEDIA_LOC + BUTTON_FOCUS, self.myEPG.focusedcolor, 1, 1, 1, 0, tabHeight, 0, tabHeight/2)
                self.addControl(self.OnNowControlList)
                # self.OnNowControlList = self.getControl(132)
                self.OnNowControlList.addItems(items=self.OnNowLst)
                
                # set focus on current channel
                for i in range(len(self.OnNowLst)):
                    item = self.OnNowLst[i]
                    channel = int(self.channelList.cleanLabels(item.split('|')[0]))
                    setProperty("OVERLAY.OnNow_Channel",str(channel))
                    if channel == self.currentChannel:
                        self.OnNowControlList.selectItem(i)
                        break

                self.getControl(130).setVisible(True)
                hide_busy_dialog()
                xbmc.sleep(10)
                self.OnNowControlList.setVisible(True)
                self.setFocus(self.OnNowControlList)
                self.setOnNowArt()
            elif isLowPower() == True:      
                Unavailable()
            else:      
                TryAgain()
            self.hideMenuControl('MenuAlt')

            
    def channelUp(self):
        self.log('channelUp')
        self.notPlayingAction = 'Up'
        if self.maxChannels == 1:
            return           
        self.setChannel(self.fixChannel(self.currentChannel + 1),True)
        self.log('channelUp return')
        
        
    def channelDown(self):
        self.log('channelDown')
        self.notPlayingAction = 'Down'     
        if self.maxChannels == 1:
            return
        self.setChannel(self.fixChannel(self.currentChannel - 1, False),True)    
        self.log('channelDown return')  
            

    def lastActionTrigger(self, action=None):
        if not action:
            action = self.notPlayingAction 
        self.log("lastActionTrigger = " + action)
        if action == 'Down':
            setBackgroundLabel("Changing Channel Down")
            self.setChannel(self.fixChannel(self.currentChannel - 1, False))
        elif action == 'Current':
            setBackgroundLabel("Reloading Channel")
            self.setChannel(self.fixChannel(self.currentChannel))
        elif action == 'Last':
            setBackgroundLabel("Returning to Previous Channel")
            self.setChannel(self.fixChannel(self.getLastChannel()))
        elif action == 'LastValid':
            setBackgroundLabel("Returning to Previous Channel")
            self.setChannel(self.fixChannel(self.lastPlayingChannel))
        else:
            setBackgroundLabel("Changing Channel Up")
            self.setChannel(self.fixChannel(self.currentChannel + 1, True))
      
      
    def setInvalidateChannel(self, channel=None):
        if not channel:
            channel = self.currentChannel
        self.channels[channel - 1].isValid = False
        # todo remove invalid channel configurations?
        # setBackgroundLabel('Exiting: Removing Invalid Channels %s' %str(i))
        # chtype = self.getChtype(i)
        # ADDON_SETTINGS.setSetting('Channel_' + str(i) + '_type','9999')
          
                    
                    
    def InvalidateChannel(self, channel):
        self.log("InvalidateChannel" + str(channel))
        try:
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
        except:
            self.setChannel(self.fixChannel(channel))
    

    def getPlaylistPOS(self, chtype, channel, offdif=0):
        self.log('getPlaylistPOS')   

        if self.OnDemand == True:
            position = -999
            
        # correct position to hideShortItems
        elif chtype <= 7 and self.hideShortItems:# and self.infoOffset != 0:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + self.infoOffset + offdif
            curoffset = 0
            modifier = 1
            if self.infoOffset < 0:
                modifier = -1

            while curoffset != abs(self.infoOffset):
                position = self.channels[channel - 1].fixPlaylistIndex(position + modifier)
                if self.channels[channel - 1].getItemDuration(position) >= self.shortItemLength:
                    curoffset += 1
                    
        elif chtype == 8 and len(self.channels[channel - 1].getItemtimestamp(0)) > 0:
            self.channels[channel - 1].setShowPosition(0)
            tmpDate = self.channels[channel - 1].getItemtimestamp(0) 
            epochBeginDate = datetime_to_epoch(tmpDate)
            position = self.channels[channel - 1].playlistPosition
            #beginDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
            #loop till we get to the current show this is done to display the correct show on the info listing for Live TV types
            
            while epochBeginDate + self.channels[channel - 1].getCurrentDuration() <  time.time():
                epochBeginDate += self.channels[channel - 1].getCurrentDuration()
                self.channels[channel - 1].addShowPosition(1)
            position = self.channels[channel - 1].playlistPosition + self.infoOffset + offdif
        else:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + self.infoOffset + offdif
        self.log('getPlaylistPOS, position = ' + str(position)) 
        return position
        

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
    def setChannel(self, channel, surfing=False):
        self.log('setChannel, channel = ' + str(channel))  
        if self.OnDemand == True:
            self.OnDemand = False

        if channel < 1 or channel > self.maxChannels:
            self.log('setChannel, invalid channel ' + str(channel), xbmc.LOGERROR)
            return
            
        if self.channels[channel - 1].isValid == False:
            self.log('setChannel, channel not valid ' + str(channel), xbmc.LOGERROR)
            return  
        
        chname = self.getChname(channel)
        chtype = self.getChtype(channel)

        if self.currentChannel != self.getLastChannel():
            self.setLastChannel()
          
        if chname == 'PseudoCinema':
            self.Cinema_Mode = True
        else:
            self.Cinema_Mode = False

        self.infoOffset = 0
        self.setBackgroundVisible(True)
        self.runActions(RULES_ACTION_OVERLAY_SET_CHANNEL, channel, self.channels[channel - 1])
        
        # first of all, save playing state, time, and playlist offset for the currently playing channel
        if self.Player.isPlaybackValid() == True:
            if channel != self.currentChannel:
                # skip setPause for LiveTV
                if self.getChtype(self.currentChannel) not in [8,9]:
                    self.channels[self.currentChannel - 1].setPaused(xbmc.getCondVisibility('Player.Paused'))
                    # Automatically pause in serial mode
                    if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE > 0:
                        self.channels[self.currentChannel - 1].setPaused(True)
                else:
                    self.channels[self.currentChannel - 1].setPaused(False)
                # set resume points
                self.channels[self.currentChannel - 1].setShowTime(self.Player.getTime())
                self.channels[self.currentChannel - 1].setShowPosition(self.channels[self.currentChannel - 1].playlistPosition)
                self.channels[self.currentChannel - 1].setAccessTime(time.time())

        # about to switch new channel
        self.idleReset()
        self.currentChannel = channel      
        mediapath = self.channels[self.currentChannel - 1].getItemFilename(self.channels[self.currentChannel - 1].playlistPosition)
        self.log("setChannel, playing file = " + ascii(mediapath))

        if surfing == True and self.channelList.quickflipEnabled == True:  
            if chtype in [15,16] or mediapath[-4:].lower() == 'strm':
                self.log("setChannel, about to quickflip")
                if self.notPlayingAction == 'Up':
                    self.channelUp()
                    return
                elif self.notPlayingAction == 'Down':
                    self.channelDown()
                    return
                 
        # switch to new channel
        self.getControl(102).setVisible(False)
        self.getControl(104).setVisible(False)
        self.getControl(119).setVisible(False)
        self.getControl(130).setVisible(False)
        self.getControl(222).setVisible(False)
        setBackgroundLabel(('Loading: %s') % chname)
        setProperty("OVERLAY.LOGOART",self.getChlogo(channel))
        self.clearProp()
        
        # now load the proper channel playlist
        xbmc.PlayList(xbmc.PLAYLIST_MUSIC).clear()
        self.log("about to load")  
        
        # Delay Playback
        xbmc.sleep(int(round((self.channelDelay/4))))
        
        self.log("setChannel, loading playlist = " + ascii(self.channels[self.currentChannel - 1].fileName))
        if xbmc.PlayList(xbmc.PLAYLIST_MUSIC).load(self.channels[self.currentChannel - 1].fileName) == False:
            self.log("setChannel, Error loading playlist", xbmc.LOGERROR)
            self.InvalidateChannel(self.currentChannel)
            return
            
        # Disable auto playlist shuffling if it's on
        if xbmc.getInfoLabel('Playlist.Random').lower() == 'random':
            self.log('setChannel, Random on.  Disabling.')
            xbmc.PlayList(xbmc.PLAYLIST_MUSIC).unshuffle()
        
        # Enable auto playlist repeat
        self.log("setChannel, repeatall enabled")
        xbmc.executebuiltin("PlayerControl(repeatall)")
        curtime = time.time()

        if self.channels[self.currentChannel - 1].isPaused == False:
            # adjust the show and time offsets to properly position inside the playlist
            #for Live TV get the first item in playlist convert to epoch time  add duration until we get to the current item
            if chtype == 8 and len(self.channels[self.currentChannel - 1].getItemtimestamp(0)) > 0:
                self.channels[self.currentChannel - 1].setShowPosition(0)
                tmpDate = self.channels[self.currentChannel - 1].getItemtimestamp(0)
                epochBeginDate = datetime_to_epoch(tmpDate)
                #index till we get to the current show
                while epochBeginDate + self.channels[self.currentChannel - 1].getCurrentDuration() < curtime:
                    epochBeginDate += self.channels[self.currentChannel - 1].getCurrentDuration()
                    self.channels[self.currentChannel - 1].addShowPosition(1)
            else:#loop for other channel types
                # adjust the show and time offsets to properly position inside the playlist
                timedif = curtime - self.channels[self.currentChannel - 1].lastAccessTime
                while self.channels[self.currentChannel - 1].showTimeOffset + timedif > self.channels[self.currentChannel - 1].getCurrentDuration():
                    timedif -= self.channels[self.currentChannel - 1].getCurrentDuration() - self.channels[self.currentChannel - 1].showTimeOffset
                    self.channels[self.currentChannel - 1].addShowPosition(1)
                    self.channels[self.currentChannel - 1].setShowTime(0)
                        
        # Delay Playback
        xbmc.sleep(int(round((self.channelDelay/4))))
                           
        # First, check to see if the video stop should be ignored
        if chtype in [8,9] or mediapath[-4:].lower() == 'strm':
            self.Player.ignoreNextStop = True
            self.log("setChannel, ignoreNextStop")

        # Mute the channel before changing
        if self.MUTE:
            self.log("setChannel, about to mute")
            self.setMute('true')
    
        # # Play Online Media (ie. fill-in meta)        
        # if chtype in [8,9]:
            # self.setPlayselected(mediapath)
        # # Play Local Media (ie. Has meta)
        # else: 
        
        # disable subtitles to fix player seek delay
        self.disableSub()
        
        # Delay Playback
        xbmc.sleep(int(round((self.channelDelay/4))))
        self.Player.playselected(self.channels[self.currentChannel - 1].playlistPosition)
        
        # Delay Playback
        xbmc.sleep(int(round((self.channelDelay/4))))
        self.Player.showSubtitles(REAL_SETTINGS.getSetting("EnableSubtitles") == "true")
                
        # set the time offset
        self.channels[self.currentChannel - 1].setAccessTime(curtime)
        
        # set the show offset
        if self.channels[self.currentChannel - 1].isPaused:
            self.channels[self.currentChannel - 1].setPaused(False)
            
            try:
                if chtype not in IGNORE_SEEKTIME:
                    self.Player.seekTime(self.channels[self.currentChannel - 1].showTimeOffset)
                else:
                    self.log("setChannel, isPaused Ignoring Seektime")
                    
                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE == 0:
                    self.Player.pause()
                    if self.waitForVideoPaused() == False:
                        if self.MUTE:
                            self.setMute('false')
                        return
            except:
                self.log('setChannel, Exception during seek on paused channel', xbmc.LOGERROR)
        else:
            if chtype not in IGNORE_SEEKTIME and self.ignoreSeektime == False:
                self.log("setChannel, about to seeking")
                seektime1 = self.channels[self.currentChannel - 1].showTimeOffset + timedif + int((time.time() - curtime))
                seektime2 = self.channels[self.currentChannel - 1].showTimeOffset + timedif
                startovertime = float((int(self.channels[self.currentChannel - 1].getItemDuration(self.channels[self.currentChannel - 1].playlistPosition))/10)*int(REAL_SETTINGS.getSetting("StartOverTime")))
                
                # Smartseek strms and plugins to avoid seeking media towards the end of runtime.
                if mediapath[-4:].lower() == 'strm' or chtype == 15:
                    overtime = float((int(self.channels[self.currentChannel - 1].getItemDuration(self.channels[self.currentChannel - 1].playlistPosition))/10)*int(REAL_SETTINGS.getSetting("StreamOverTime")))
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
                self.log("setChannel,self.seektime = " + str(self.seektime))        
                
                # toggle startover prompt
                if self.seektime > startovertime: 
                    self.toggleShowStartover(True)
                else:
                    self.toggleShowStartover(False)
            else:
                self.log("setChannel, Ignoring Seektime")
        self.Player.onPlaybackAction()
        
        # Unmute
        if self.MUTE:
            self.log("setChannel, Finished, unmuting")
            self.setMute('false')
            
        egTrigger('PseudoTV_Live - Loading: %s' % chname)
        self.runActions(RULES_ACTION_OVERLAY_SET_CHANNEL_END, channel, self.channels[channel - 1])
        setProperty("PTVL.INIT_CHANNELSET","true")
        self.log('setChannel, setChannel return')
        
        
    def SmartSeek(self, mediapath, seektime1, seektime2, overtime):
        self.log("SmartSeek")
        seektime = 0
        if seektime1 < overtime:
            try:
                self.Player.seekTime(seektime1)
                seektime = seektime1
                self.log("seektime1 = " + str(seektime))
            except:
                self.log("Unable to set proper seek time, trying different value")
                if seektime2 < overtime:
                    try:
                        self.Player.seekTime(seektime2)
                        seektime = seektime2
                        self.log("seektime2 = " + str(seektime))
                    except:
                        self.log('Exception during seek', xbmc.LOGERROR)
                        seektime = 0
        if seektime == 0 and DEBUG == 'true':
            self.log('overtime ' + str(overtime))
            DebugNotify("Overriding Seektime")
        return seektime    

    def chkUPNP(self):
        IPPlst = []
        #UPNP Clients
        if REAL_SETTINGS.getSetting("UPNP1") == "true":
            IPPlst.append(REAL_SETTINGS.getSetting("UPNP1_IPP"))
        if REAL_SETTINGS.getSetting("UPNP2") == "true":
            IPPlst.append(REAL_SETTINGS.getSetting("UPNP2_IPP"))
        if REAL_SETTINGS.getSetting("UPNP3") == "true":
            IPPlst.append(REAL_SETTINGS.getSetting("UPNP3_IPP"))
        self.log("chkUPNP = " + str(IPPlst))
        return IPPlst
              
        
    def UPNPcontrol(self, func, file='', seektime=0):
        self.log('UPNPcontrol') 
        if self.enableUPNP == False:
            return
            
        if self.UPNPcontrolTimer.isAlive():
            self.UPNPcontrolTimer.cancel()
        self.UPNPcontrolTimer = threading.Timer(0.1, self.UPNPcontrol_thread, [func, file, seektime])
        self.UPNPcontrolTimer.name = "UPNPcontrol"   
        self.UPNPcontrolTimer.start()

                  
    def UPNPcontrol_thread(self, func, file='', seektime=0):
        self.log('UPNPcontrol_thread')
        file = file.replace("\\\\","\\") 
        for i in range(len(self.IPPlst)):
            if func == 'play':
                self.Upnp.SendUPNP(self.IPPlst[i], file, seektime)
            elif func == 'stop':
                self.Upnp.StopUPNP(self.IPPlst[i])
            elif func == 'resume':
                self.Upnp.ResumeUPNP(self.IPPlst[i])
            elif func == 'pause':
                self.Upnp.PauseUPNP(self.IPPlst[i])
            elif func == 'rwd':
                self.Upnp.RWUPNP(self.IPPlst[i])
            elif func == 'fwd':
                self.Upnp.FFUPNP(self.IPPlst[i])


    def waitForVideoPaused(self):
        self.log('waitForVideoPaused')
        sleeptime = 0
        while sleeptime < TIMEOUT:
            xbmc.sleep(10)
            if self.Player.isPlaybackValid() == True:
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
        position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
        chtype = self.getChtype(self.currentChannel)
        
        if self.OnDemand == True:
            self.toggleShowStartover(False)    
            setProperty("OVERLAY.DYNAMIC_LABEL",'OnDemand')
        elif self.infoOffset > 0:
            self.toggleShowStartover(False)  
            self.getControl(5007).setVisible(False)   
            setProperty("OVERLAY.DYNAMIC_LABEL",'COMING UP')
        elif self.infoOffset < 0:
            self.toggleShowStartover(False)  
            self.getControl(5007).setVisible(False)   
            setProperty("OVERLAY.DYNAMIC_LABEL",'ALREADY SEEN') 
        elif self.infoOffset == 0:
            self.getControl(5007).setVisible(True)
            setProperty("OVERLAY.DYNAMIC_LABEL",'NOW WATCHING')
        
        if self.OnDemand == True:
            position == -999
            mediapath = self.Player.getPlayingFile()
        else:
            position = self.getPlaylistPOS(chtype, self.currentChannel)
            mediapath = (self.channels[self.currentChannel - 1].getItemFilename(position))
 
        if position >= 0:
            self.setMediaInfo(chtype, self.getChname(self.currentChannel), self.currentChannel, mediapath, position)

            
    def setMediaInfo(self, chtype, chname, chnum, mediapath, position, tmpstr=None):
        self.log('setMediaInfo, pos = ' + str(position))
        # self.clearProp()
        self.hideShortInfo = False
        mpath = getMpath(mediapath)
        #OnDemand Set Player info, else Playlist
        if position == -999:
            print tmpstr
            if tmpstr != None:
                tmpstr = tmpstr.split('//')
                title = tmpstr[0]
                SEtitle = ('[COLOR=%s][B]OnDemand[/B][/COLOR]' % ((self.channelbugcolor).replace('0x','')))
                Description = tmpstr[2]
                genre = tmpstr[3]
                timestamp = tmpstr[4]
                myLiveID = tmpstr[5]
                if self.showChannelBug == True:
                    self.getControl(203).setImage(self.Artdownloader.FindBug('0','OnDemand'))
            else:
                self.getTMPSTR(chtype, chname, chnum, mediapath, position)
                return 
        else:
            label = (self.channels[self.currentChannel - 1].getItemTitle(position))
            SEtitle = self.channels[self.currentChannel - 1].getItemEpisodeTitle(position)
            Description = (self.channels[self.currentChannel - 1].getItemDescription(position))
            genre = (self.channels[self.currentChannel - 1].getItemgenre(position))
            timestamp = (self.channels[self.currentChannel - 1].getItemtimestamp(position))
            myLiveID = (self.channels[self.currentChannel - 1].getItemLiveID(position))
        
        chlogo = self.getChlogo(chnum)
        season, episode, swtitle = SEinfo(SEtitle, self.showSeasonEpisode)
        type, id, dbepid, managed, playcount, rating, hd, cc, stars, year = self.channelList.unpackLiveID(myLiveID)
        dbid, epid = splitDBID(dbepid)
        year, title, showtitle = getTitleYear(label, year)
        
        # SetProperties
        if self.infoOffset == 0:
            self.setProp_thread(label, year, chlogo, chtype, chnum, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, swtitle, playcount, season, episode, timestamp, "OVERLAY.PLAYING")
            if self.channels[self.currentChannel - 1].getItemDuration(position) < self.shortItemLength:
                self.hideShortInfo = True
            elif SEtitle in BCT_TYPES:
                self.hideShortInfo = True
        self.setProp_thread(label, year, chlogo, chtype, chnum, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, swtitle, playcount, season, episode, timestamp, "OVERLAY")
           

    def setMediaProp(self):
        chnum = self.currentChannel
        chtype = self.getChtype(chnum)
        chname = self.getChname(chnum)
        if self.OnDemand == True:
            position = -999
            mediapath = self.Player.getPlayingFile()
        else:
            position = self.getPlaylistPOS(chtype, chnum)
            mediapath = (self.channels[chnum - 1].getItemFilename(position))   
        self.setMediaInfo(chtype, chname, chnum, mediapath, position)
             

    # Display the current channel based on self.currentChannel.
    # Start the timer to hide it.
    def showChannelLabel(self, channel):
        self.log('showChannelLabel ' + str(channel))   
        if self.channelLabelTimer.isAlive():
            self.channelLabelTimer.cancel()
        
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

        if self.inputChannel == -1:
            self.infoOffset = 0
        
        chname = self.getChname(self.currentChannel)
        if self.showChannelBug == True:
            chtype = self.getChtype(self.currentChannel)     
            self.getControl(203).setImage(self.Artdownloader.FindBug(chtype, chname))
        
        if xbmc.getCondVisibility('Player.ShowInfo'):
            json_query = '{"jsonrpc": "2.0", "method": "Input.Info", "id": 1}'
            self.ignoreInfoAction = True
            self.channelList.sendJSON(json_query)
        
        self.channelLabelTimer = threading.Timer(2.0, self.hideChannelLabel)
        self.channelLabelTimer.name = "channelLabelTimer"
        self.channelLabelTimer.start()

        
    # Called from the timer to hide the channel label.
    def hideChannelLabel(self):
        self.log('hideChannelLabel')
        for i in range(3):
            self.channelLabel[i].setVisible(False)

        if self.DirectInput == True:
            inputChannel = self.inputChannel
            if not inputChannel in [-1, self.currentChannel]:
                if self.GotoChannelTimer.isAlive():
                    self.GotoChannelTimer.cancel()
                self.GotoChannelTimer = threading.Timer(0.5, self.setChannel, [inputChannel])
                self.GotoChannelTimer.name = "GotoChannel"
                self.GotoChannelTimer.start()
        self.inputChannel = -1
        self.log('hideChannelLabel return')


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
        elif type == 'Search':
            self.showingBrowse = True
            self.MenuControl('Menu',self.InfTimer,True)
            if int(REAL_SETTINGS.getSetting("Search_Option")) == 0:
                xbmc.executebuiltin("XBMC.RunScript(script.globalsearch)")
            elif int(REAL_SETTINGS.getSetting("Search_Option")) == 1:
                xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedinfo,name=%s)" % inputDialog('Enter Search String'))
        else:
            self.showingBrowse = True
            xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo)")
        xbmc.sleep(10)
        self.showingBrowse = False
        
        
    def ContextMenuAction(self, type, pType='OVERLAY'):
        self.log("ContextMenuAction, type = " + type + ", pType = " + pType)
        if type == 'MoreInfo':
            self.getExtendedInfo('MoreInfo', pType)
        elif type == 'Similar':
            Comingsoon()
        elif type == 'Record':
            self.setRecord()
        elif type == 'Reminder':
            self.setReminder(pType=pType)
        
        
    def getExtendedInfo(self, action='', pType='OVERLAY'):
        # https://github.com/phil65/script.extendedinfo/blob/master/resources/lib/process.py
        title = getProperty(("%s.Title")%pType)
        type = getProperty(("%s.Type")%pType)
        dbid = getProperty(("%s.DBID")%pType)
        id = getProperty(("%s.ID")%pType)
        self.log("getExtendedInfo, action = " + action + ", pType = " + pType + ", type = " + type)
        self.log("getExtendedInfo, title = " + title + ", dbid = " + dbid + ", id = " + id)
        if type == 'movie':
            if dbid != '0' and len(dbid) < 6:
                xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedinfo,dbid=%s,imdb_id=%s)" % (dbid,id))
            elif id != '0':
                xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedinfo,imdb_id=%s)" % (id))
            else:
                Unavailable()
        elif type == 'tvshow':
            if dbid != '0' and len(dbid) < 6:
                xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedtvinfo,name=%s,dbid=%s,tvdb_id=%s)" % (title,dbid,id))
            elif id != '0':
                xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedtvinfo,name=%s,tvdb_id=%s)" % (title,id))
            else:
                Unavailable()
        elif type == 'youtube':
            YTtype = (ADDON_SETTINGS.getSetting('Channel_' + getProperty(("%s.Chnum")%pType) + '_2'))
            YTinfo = ADDON_SETTINGS.getSetting('Channel_' + getProperty(("%s.Chnum")%pType) + '_1')
            if YTtype in ['1','Channel']:
                xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=youtubeusersearch,id=%s)" % YTinfo)
            elif YTtype in ['2','Playlist']:
                xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=youtubeplaylist,id=%s)" % YTinfo)
            else:
                Unavailable()
                
      
    def toggleShowStartover(self, state):
        self.log('toggleShowStartover')
        if state == True:
            self.getControl(104).setVisible(True)
            self.showingStartover = True
        else:
            self.getControl(104).setVisible(False)
            self.showingStartover = False
        xbmc.sleep(10)

                
    def hideInfo(self):
        self.log('hideInfo')
        self.toggleShowStartover(False)
        self.getControl(102).setVisible(False)
        self.showingInfo = False 
        self.infoOffset = 0 
                          
              
    def showInfo(self):
        self.log("showInfo")
        if self.infoTimer.isAlive():
            self.infoTimer.cancel()
        
        if self.hideShortInfo == True:
            return

        if xbmc.getCondVisibility('Player.ShowInfo'):
            json_query = '{"jsonrpc": "2.0", "method": "Input.Info", "id": 1}'
            self.ignoreInfoAction = True
            self.channelList.sendJSON(json_query)
            
        self.setShowInfo()
        if not self.showingInfo:
            self.hidePOP()
            self.showingInfo = True
            self.getControl(222).setVisible(False)
            self.getControl(102).setVisible(True)
            
        self.infoTimer = threading.Timer(self.InfTimer, self.hideInfo)
        self.infoTimer.name = "InfoTimer"
        if isBackgroundVisible() == False:
            self.infoTimer.start()


    def showMenu(self):
        self.log("showMenu")
        #Set button labels
        self.getControl(1005).setLabel(self.chkChanFavorite())
        self.getControl(1008).setLabel(self.chkSub())
        if self.showingMenu == False:    
            #Set first button focus, show menu
            self.showingMenu = True
            self.getControl(119).setVisible(True)
            xbmc.sleep(10) 
            self.setFocusId(1001) 
        self.hideMenuControl('Menu')


    def showMoreInfo(self):
        self.log('showMoreInfo')            
        self.getControl(1012).setLabel('More Info')
        self.getControl(1013).setLabel('Find Similar')
        self.getControl(1014).setLabel('Record Show')
        self.getControl(1015).setLabel('Set Reminder')
        
        if not self.showingMoreInfo:
            self.hideInfo()
            self.showingMoreInfo = True   
            self.getControl(102).setVisible(False)
            self.getControl(222).setVisible(True) 
            xbmc.sleep(10) 
            self.setFocusId(1012)
        self.hideMenuControl('MoreInfo')

            
    def hidePOP(self):
        self.log("hidePOP")  
        if self.popTimer.isAlive():
            self.popTimer.cancel()         
        self.getControl(120).setVisible(False)
        self.getControl(203).setVisible(True)
        xbmc.sleep(10)
        self.DisableOverlay = False
        self.showingPop = False
        
                     
    def showPOP(self):
        self.log("showPOP")
        if self.popTimer.isAlive():
            self.popTimer.cancel()
            
        # if self.isWindowOpen == False:
        self.getControl(203).setVisible(False)
        self.showingPop = True
        self.DisableOverlay = True
        self.getControl(120).setVisible(True)

        self.popTimer = threading.Timer(self.InfTimer + 2.5, self.hidePOP)
        self.popTimer.name = "popTimer"
        if isBackgroundVisible() == False:
            self.popTimer.start()
    
            
    def ScrSavTimer(self):
        if REAL_SETTINGS.getSetting("Idle_Screensaver") == "true": 
            IDLEopened = getProperty("PTVL.Idle_Opened") == "true" 
            xbmcIdle = xbmc.getGlobalIdleTime()
            PausedPlayback = self.Player.isPlaybackPaused()
            ActivePlayback = self.Player.isPlaybackValid()
            EPGopened = self.isWindowOpen() != False
            if xbmcIdle >= IDLE_TIMER and IDLEopened == False:
                if EPGopened == True:
                    self.log("ScrSavTimer, Starting Idle ScreenSaver; EPG Open")                      
                    self.myIdle.doModal()
                    xbmc.executebuiltin("action(leftclick)")
                elif ActivePlayback == True and PausedPlayback == True:
                    self.log("ScrSavTimer, Starting Idle ScreenSaver; Playback Paused")                      
                    self.myIdle.doModal()
                    xbmc.executebuiltin("action(leftclick)")   
            self.log("ScrSavTimer, IDLEopened = " + str(IDLEopened) + ", XBMCidle = " + str(xbmcIdle) + ", IDLE_TIMER = " + str(IDLE_TIMER) + ', PausedPlayback = ' + str(PausedPlayback) + ', ActivePlayback = ' + str(ActivePlayback) + ', EPGopened = ' + str(EPGopened) )
          
          
    def onFocus(self, controlId):
        self.log('onFocus ' + str(controlId))
        
        
    def onClick(self, controlId):
        self.log('onClick ' + str(controlId))
        self.playSFX('ACTION_CLICK')
        
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
                self.setChannel(self.fixChannel(self.getLastChannel()))
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
                xbmc.executebuiltin("Mute()")
                self.MenuControl('Menu',self.InfTimer)
        elif controlId == 1008:
            if self.showingMenu:
                self.log("Subtitle")
                self.toggleSubtitles()
                # xbmc.executebuiltin("ActivateWindow(10153)")
                # xbmc.executebuiltin("ActivateWindow(SubtitleSearch)")
                self.MenuControl('Menu',self.InfTimer)  
        elif controlId == 1009:
            if self.showingMenu:
                self.log("VideoMenu")
                xbmc.executebuiltin("ActivateWindow(videoosd)")
                xbmc.sleep(10)
                self.MenuControl('Menu',self.InfTimer,True)       
        elif controlId == 1010:
            if self.showingMenu:
                self.log("Sleep")
                self.SleepButton(True)    
                self.MenuControl('Menu',self.InfTimer)     
                
        elif controlId == 1011:
            if self.showingMenu:
                self.log("Exit")
                if yesnoDialog("Are you sure you want to exit PseudoTV Live?", header='PseudoTV Live - Exit?') == True:
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
        elif controlId == 7001:
            if self.showingSleep:
                self.log("Sleep Cancel")
                self.sleepCancel()
            elif self.showingReminder:
                self.ReminderCancel()  
        elif controlId == 7002:
            if self.showingSleep:
                self.log("Sleep Action")
                self.sleepAction()
            elif self.showingReminder:
                self.ReminderAction()
        self.log('onClick return')
    
    
    def onControl(self, controlId):    
        self.log('onControl ' + str(controlId))
        

    # todo move to actionhandler mod?
    # https://github.com/phil65/script.module.actionhandler
    def SelectAction(self):
        if self.showingStartover:
            self.playStartOver()
        elif self.showingMenuAlt:
            self.playOnNow()
        elif self.showingBrowse:
            return
        elif self.showingInfo and self.infoOffset > 0:
            self.playSelectShow()
        elif not self.showingMenu and not self.showingMoreInfo and not self.showingBrowse and not self.settingReminder:
            self.playInputChannel()
        return
    
    
    # Handle all input while videos are playing
    def onAction(self, act):
        action = act.getId()
        self.log('onAction ' + str(action))
        self.playSFX(action) 
            
        # Since onAction isnt always called from the same thread (weird),
        # ignore all actions if we're in the middle of processing one
        if self.actionSemaphore.acquire(False) == False:
            self.log('onAction, Unable to get semaphore')
            return
       
        lastaction = time.time() - self.lastActionTime
        # during certain times we just want to discard all input
        if lastaction < 1 and self.showingStartover == False:
            self.log('onAction, Not allowing actions')
            action = ACTION_INVALID
        self.idleReset()

        if action in ACTION_SELECT_ITEM:
            if not self.showingSleep and not self.showingReminder:
                self.SelectAction()
                
        elif action in ACTION_SHOW_EPG:
            self.openEPG()
                
        elif action in ACTION_MOVE_UP or action in ACTION_PAGEUP:
            if self.showingMenuAlt:
                self.setOnNowArt()
                self.MenuControl('MenuAlt',self.InfTimer)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer)
            elif not self.showingMoreInfo and not self.showingSleep and not self.showingReminder:
                self.channelUp()
                
        elif action in ACTION_MOVE_DOWN or action in ACTION_PAGEDOWN:
            if self.showingMenuAlt:
                self.setOnNowArt()
                self.MenuControl('MenuAlt',self.InfTimer)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer)
            elif not self.showingMoreInfo and not self.showingSleep and not self.showingReminder:
                self.channelDown()

        elif action in ACTION_MOVE_LEFT:   
            self.log("onAction, ACTION_MOVE_LEFT")
            if self.showingStartover == True:
                self.toggleShowStartover(False)
                
            if self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer,True)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer,True)
            elif self.showingInfo:
                self.infoOffset -= 1
                self.showInfo()
                if self.infoOffset < 0:
                    self.infoOffset = 0
                    self.clearProp('OVERLAY')
                    self.MenuControl('Menu',self.InfTimer)
                elif not self.showingMenu:
                    self.showInfo()
            elif self.showingInfo == False and not int(getProperty("OVERLAY.Chtype")) in [8,9] and not getProperty("OVERLAY.Mediapath").startswith(("rtmp", "rtsp", "PlayMedia")):
                self.log("onAction, SmallSkipBackward")
                if getXBMCVersion() >= 15:
                    xbmc.executebuiltin("Seek("+str(self.seekBackward)+")")
                else:
                    xbmc.executebuiltin("PlayerControl(SmallSkipBackward)")
                self.UPNPcontrol('rwd')
                    
        elif action in ACTION_MOVE_RIGHT:
            self.log("onAction, ACTION_MOVE_RIGHT")
            if self.showingStartover == True:
                self.toggleShowStartover(False)
                
            if self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer,True)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer,True)
            elif self.showingInfo:
                self.infoOffset += 1
                self.showInfo()
            elif self.showingInfo == False and not int(getProperty("OVERLAY.Chtype")) in [8,9] and not getProperty("OVERLAY.Mediapath").startswith(("rtmp", "rtsp", "PlayMedia")):
                self.log("onAction, SmallSkipForward")
                if getXBMCVersion() >= 15:
                    xbmc.executebuiltin("Seek("+str(self.seekForward)+")")
                else:
                    xbmc.executebuiltin("PlayerControl(SmallSkipForward)")
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
                if yesnoDialog("Are you sure you want to exit PseudoTV Live?", header='PseudoTV Live - Exit?') == True:
                    self.end()
                    return  # Don't release the semaphore
        
        elif action in ACTION_SHOW_INFO:   
            if self.ignoreInfoAction:
                self.ignoreInfoAction = False
            else:
                if self.showingInfo:
                    self.hideInfo()
            
                    if xbmc.getCondVisibility('Player.ShowInfo'):
                        json_query = '{"jsonrpc": "2.0", "method": "Input.Info", "id": 1}'
                        self.ignoreInfoAction = True
                        self.channelList.sendJSON(json_query)
                else:
                    self.showInfo()         

        elif action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
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
            self.setRecord()
        
        elif action == ACTION_SHIFT: #Last channel button
            self.log('onAction, ACTION_SHIFT')
            self.setChannel(self.fixChannel(self.getLastChannel()))

        elif action == ACTION_SYMBOLS:
            self.log('onAction, ACTION_SYMBOLS')
            self.setChannel(self.fixChannel(self.Jump2Favorite()))

        elif action in ACTION_CONTEXT_MENU:
            self.log('onAction, ACTION_CONTEXT_MENU')
            if not self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer,True)
        self.actionSemaphore.release()     
        self.log('onAction return')

        
    def SleepButton(self, silent=False):
        self.sleepTimeValue += 1800
        #Disable when max sleep reached
        if self.sleepTimeValue > 14400:
            self.sleepTimeValue = 0 
        if self.sleepTimeValue != 0:
            Stime = self.sleepTimeValue / 60
            SMSG = ('Sleep (%sm)' % str(Stime))
        else: 
            SMSG = 'Sleep Disabled'
        self.resetSleepTimer()
        if silent == False:
            infoDialog(SMSG)
            

    # Reset the sleep timer
    def resetSleepTimer(self):
        if self.sleepTimer.isAlive():
            self.sleepTimer.cancel()
        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepPrompt)
        self.sleepTimer.name = "SleepTimer"
        self.SleepTimerCountdown(self.sleepTimeValue/60)
        if self.sleepTimeValue != 0:
            if self.isExiting == False:
                self.sleepTimer.start()
    
     
    def SleepTimerCountdown(self, sleeptime):
        self.log("SleepTimerCountdown")
        if self.SleepTimerCountdownTimer.isAlive():
            self.SleepTimerCountdownTimer.cancel()
            
        if sleeptime == 0:
            self.getControl(1010).setLabel('Sleep')
        else:
            self.getControl(1010).setLabel('Sleep (%sm)' % str(sleeptime))
            self.SleepTimerCountdownTimer = threading.Timer(60.0, self.SleepTimerCountdown, [sleeptime-1])
            self.SleepTimerCountdownTimer.name = "SleepTimerCountdownTimer"
            self.SleepTimerCountdownTimer.start()
            

    def startIdleTimer(self):
        if self.idleTimer.isAlive():
            self.idleTimer.cancel()
        self.idleTimer = threading.Timer(self.idleTimeValue, self.sleepPrompt)
        self.idleTimer.name = "idleTimer"
        if self.idleTimeValue > 0:
            if self.isExiting == False:
                self.idleTimer.start()
    
    
    def IdleTimerCountdown(self, idletime):
        self.log("IdleTimerCountdown")
        if self.idleTimerCountdownTimer.isAlive():
            self.idleTimerCountdownTimer.cancel()
            
        if idletime > 0:
            if self.showingSleep:
                self.getControl(7002).setLabel('Sleep in (%ds)' % idletime)
            elif self.showingReminder:
                self.getControl(7002).setLabel('Channel Change in (%ds)' % idletime)
            self.idleTimerCountdownTimer = threading.Timer(1.0, self.IdleTimerCountdown, [idletime-1])
            self.idleTimerCountdownTimer.name = "idleTimerCountdownTimer"
            xbmc.sleep(10)
            self.idleTimerCountdownTimer.start()          
        elif idletime == 0:
            if self.showingSleep:
                self.sleepAction()
            elif self.showingReminder:
                self.ReminderAction()
            
            
    def idleReset(self):
        self.log("idleReset")
        # Auto-off reset after activity.
        if self.idleTimeValue > 0:
            self.startIdleTimer()
        self.lastActionTime = time.time() 
            
            
    def sleepCancel(self):
        self.log("sleepCancel")
        # cancel sleep action
        if self.idleTimerCountdownTimer.isAlive():
            self.idleTimerCountdownTimer.cancel()
            
        # cancel sleep button
        if self.sleepTimeValue > 0:
            self.sleepTimeValue = 0

        self.idleReset()
        # hide sleep prompt
        self.getControl(7000).setVisible(False)  
        xbmc.sleep(10)
        self.showingSleep = False
            
            
    # This is called when the sleep timer expires    
    def sleepPrompt(self):
        self.log("sleepPrompt")
        self.showingSleep = True  
        setProperty("PTVL.IDLE_LABEL","Are you [I]sure you're[/I]  still watching" + '"' + getProperty('OVERLAY.Title') + '"?')
        self.getControl(7001).setLabel('Continue watching')  
        self.getControl(7002).setLabel('Sleep in (%ds)' % IDLE_DELAY)
        self.IdleTimerCountdown(IDLE_DELAY)
        self.getControl(7000).setVisible(True)    
        self.setFocusId(7001)
        self.playSFX('ACTION_ALERT')

        
    def sleepAction(self):
        self.log("sleepAction")
        # hide sleep prompt
        self.getControl(7000).setVisible(False)
        self.showingSleep = False
        
        if self.sleepTimeMode == 0:
            self.end()
        elif self.sleepTimeMode == 1:
            self.end('Quit')
        elif self.sleepTimeMode == 2:
            xbmc.executebuiltin( "XBMC.AlarmClock(shutdowntimer,XBMC.Suspend(),%d,false)" % ( 5.0, ) )
        elif self.sleepTimeMode == 3:
            self.end('Powerdown')
        elif self.sleepTimeMode == 4:
            egTrigger('PseudoTV_Live - Sleeping')
        elif self.sleepTimeMode == 5:
            xbmc.executebuiltin("CECStandby()") 
        elif self.sleepTimeMode == 6:
            self.DisablePlayback = True
            self.channelThreadpause = False
            json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"stop"},"id":1}'
            self.channelList.sendJSON(json_query)  
        elif self.sleepTimeMode == 7:
            self.setChannel(self.fixChannel(self.PreferredChannel))

            
    def ReminderCancel(self):
        self.log("ReminderCancel")
        self.getControl(7000).setVisible(False)  
        xbmc.sleep(10)
        self.showingReminder = False
        
        
    def ReminderPrompt(self):
        self.log("ReminderPrompt")
        self.showingReminder = True    
        setProperty("PTVL.IDLE_LABEL","Are you [I]sure you're[/I]  still watching" + '"' + getProperty('OVERLAY.Title') + '"?\n "' + getProperty('PTVL.Reminder_title') + '" is about to begin on Channel ' + getProperty('PTVL.Reminder_chnum') + '.')
        self.getControl(7001).setLabel('Continue watching')  
        self.getControl(7002).setLabel('Channel Change in (%ds)' % IDLE_DELAY)
        self.IdleTimerCountdown(IDLE_DELAY)
        self.getControl(7000).setVisible(True)  
        self.setFocusId(7001)
        self.playSFX('ACTION_ALERT')
        
        
    def ReminderAction(self):
        self.log("ReminderAction")
        self.getControl(7000).setVisible(False)
        self.setChannel(self.fixChannel(int(getProperty('PTVL.Reminder_chnum'))))
        xbmc.sleep(10)
        self.showingReminder = False
        
        
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

        
    # def TitleCHK(self, title):
        # if title == getProperty('PTVL.TitleCHK'):
            # self.OnDemand = False
        # else:
            # self.OnDemand = True
        # self.log("TitleCHK, OnDemand = " + str(self.OnDemand))

        
    def notificationAction(self):        
        while True:
            if self.isExiting == True:
                break
                
            self.log("notificationAction")
            chtype = self.getChtype(self.currentChannel)
            chname = self.getChname(self.currentChannel)
            
            if self.showNextItem == False:
                continue

            if self.Player.isPlaybackValid() == True:  
                self.notificationLastChannel = self.currentChannel
                self.notificationLastShow = self.channels[self.currentChannel - 1].playlistPosition
                self.notificationShowedNotif = False
                
                if (chtype <= 7 or chtype >= 10) and self.hideShortItems:
                    # Don't show any notification if the current show is < shortItemLength
                    if self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) < self.shortItemLength:
                        self.notificationShowedNotif = True

                self.log("notificationAction, notificationShowedNotif = " + str(self.notificationShowedNotif)) 
                if self.notificationShowedNotif == False:  
                    timedif = self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) - self.Player.getTime()
                    self.log("notificationAction, timedif = " + str(timedif))
                    
                    # Nextshow Info
                    self.clearProp('OVERLAY.NEXT')
                    nextshow_offset = 1
                    nextshow = self.getPlaylistPOS(chtype, self.currentChannel, nextshow_offset)
                    ComingUpType = int(REAL_SETTINGS.getSetting("EnableComingUp"))

                    # Don't show any notification if the next show is a BCT
                    while self.channels[self.currentChannel - 1].getItemgenre(nextshow) in BCT_TYPES:
                        nextshow_offset += 1
                        nextshow = self.getPlaylistPOS(chtype, self.currentChannel, nextshow_offset)
                    
                    label = self.channels[self.currentChannel - 1].getItemTitle(nextshow).replace(',', '')
                    SEtitle = self.channels[self.currentChannel - 1].getItemEpisodeTitle(nextshow)         
                    Description = self.channels[self.currentChannel - 1].getItemDescription(nextshow)
                    genre = self.channels[self.currentChannel - 1].getItemgenre(nextshow)
                    LiveID = self.channels[self.currentChannel - 1].getItemLiveID(nextshow)
                    Duration = self.channels[self.currentChannel - 1].getItemDuration(nextshow) 
                    timestamp = self.channels[self.currentChannel - 1].getItemtimestamp(nextshow) 
                    mediapath = self.channels[self.currentChannel - 1].getItemFilename(nextshow)  
                    type, id, dbepid, managed, playcount, rating, hd, cc, stars, year = self.channelList.unpackLiveID(LiveID)
                    dbid, epid = splitDBID(dbepid)
                    mpath = getMpath(mediapath)
                    chlogo = self.getChlogo(self.currentChannel)
                    year, title, showtitle = getTitleYear(label, year)
                    season, episode, swtitle = SEinfo(SEtitle, self.showSeasonEpisode) 
                    
                    self.log("notificationAction, Setting Properties")
                    self.setProp_thread(label, year, chlogo, chtype, self.currentChannel, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, swtitle, playcount, season, episode, timestamp, 'OVERLAY.NEXT')

                    if timedif < NOTIFICATION_TIME_BEFORE_END and timedif > NOTIFICATION_DISPLAY_TIME:
                        self.log("notificationAction, showComingUp")
                        
                        if self.notificationShowedNotif == False and (self.showingInfo == False or self.showingMoreInfo == False):
                            # Notification
                            if ComingUpType == 3:
                                infoDialog(getProperty("OVERLAY.NEXT.SubTitle"),'Coming Up: '+getProperty("OVERLAY.NEXT.Title"), time=NOTIFICATION_DISPLAY_TIME, icon=getProperty("OVERLAY.LOGOART"))
                            # Popup Overlay
                            elif ComingUpType == 2:
                                self.showPOP()  
                            # Info Overlay
                            elif ComingUpType == 1:
                                self.infoOffset = ((nextshow) - self.notificationLastShow)
                                self.showInfo()
                        time.sleep(NOTIFICATION_TIME_BEFORE_END)
                    else:
                        time.sleep(NOTIFICATION_CHECK_TIME)
                
                
    def CloseDialog(self, type=['Progress dialogue','Dialogue OK']):
        curwindow = currentWindow()
        self.log("CloseDialog, type = " + str(type) + ", currentwindow = " + curwindow)
        if curwindow in type:
            self.setBackgroundVisible(True)
            json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"select"},"id":1}'
            self.channelList.sendJSON(json_query)   
            DebugNotify("Dialogue Closed")
            return True
        return False

        
    def ForceStop(self):
        curwindow = currentWindow()
        self.log("ForceStop, currentwindow = " + curwindow)
        # "Working" Busy dialogue doesn't report a label.
        if curwindow == "":
            if self.Player.ignoreNextStop == True:
                self.log("PlayerTimedOut, Playback Failed: STOPPING!")         
                json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"back"},"id":1}'
                self.channelList.sendJSON(json_query)       
                xbmc.sleep(10)
                json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"close"},"id":1}'
                self.channelList.sendJSON(json_query)  
                xbmc.sleep(10)  
                json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"stop"},"id":1}'
                self.channelList.sendJSON(json_query)         
                DebugNotify("Playback Failed, STOPPING!") 
                return True
        return False

        
    def playerTimerAction(self):
        while True:
            if self.isExiting == True:
                break
            try:
                playActionTime = int(round((self.PlayTimeoutInt/int(self.ActionTimeInt))))
                if self.Player.isSomethingPlaying() == False:
                    raise Exception()    
                self.notPlayingCount = 0  
                self.FailedPlayingCount = 0   
                self.lastPlayTime = self.Player.getPlayerTime()
                self.lastPlaylistPosition = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
                self.lastPlayingChannel = self.currentChannel
            except Exception,e:
                self.notPlayingCount += 1
                if self.DisablePlayback == True:
                    if self.notPlayingCount == 3:
                        self.openEPG()
                else:
                    if self.notPlayingCount > int(round((playActionTime/8)*6)):
                        OptNotify("notPlayingCount = " + str(self.notPlayingCount) + "/" + str(playActionTime))

                    # 3peat lastActionTrigger set known vaild channel
                    if self.FailedPlayingCount == 3:     
                        self.CloseDialog()
                        self.lastActionTrigger('LastValid')
                        
                    # retry failed channel near the end
                    if self.notPlayingCount == playActionTime - 2:
                        self.CloseDialog()
                        self.lastActionTrigger('Current')
                            
                    # channel failed, lastActionTrigger, temp disable failed channel
                    elif self.notPlayingCount >= playActionTime:
                        self.FailedPlayingCount += 1
                        if self.ignoreNextStop == False:
                            self.CloseDialog()
                            self.SkipNext()
                        else:
                            self.setInvalidateChannel()
                            self.CloseDialog()
                            self.lastActionTrigger() 
                            
            # disable dialog checks while system is taxed or on low end hardware
            if isLowPower() == False:
                if self.CloseDialog(['Dialogue OK']) == True:
                    self.lastActionTrigger()
            time.sleep(int(self.ActionTimeInt))
           
           
    def SkipNext(self):
        self.log('SkipNext')
        setBackgroundLabel("Skipping Next")
        xbmc.executebuiltin("PlayerControl(Next)")
                    
     
    def Paused(self, action=False):
        self.log('Paused')
        self.setBackgroundVisible(True)
        setBackgroundLabel('Paused')   
        if action and self.Player.isPlaybackValid() == True:
            json_query = ('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1}, "id": 1}')
            self.channelList.sendJSON(json_query)
        self.UPNPcontrol('pause')
    
    
    def Resume(self, action=False):
        self.log('Resume')
        self.setBackgroundVisible(False)
        self.showInfo()      
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
        

    def cleanReminderTime(self, tmpDate):
        try:#sloppy fix, for threading issue with strptime.
            t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
        except:
            t = time.strptime(tmpDate, '%Y-%m-%d %H:%M:%S')
        Notify_Time = time.strftime('%I:%M%p, %A', t)
        epochBeginDate = time.mktime(t)
        return Notify_Time, epochBeginDate


    def isReminder(self, chtype=9999, chnum=-1, tmpDate=None, reminder_dict=None, pType='OVERLAY'):
        self.log('isReminder, self.ReminderLst')
        if reminder_dict:
            chtype  = reminder_dict['Chtype']
            chnum   = reminder_dict['Chnum']
            tmpDate = reminder_dict['TimeStamp']

        if self.ReminderLst and len(self.ReminderLst) > 0:
            for n in range(len(self.ReminderLst)):
                lineLST = self.ReminderLst[n]
                self.log('isReminder, lineLST = ' + str(lineLST))
                nchtype  = lineLST['Chtype']
                nchnum   = lineLST['Chnum']
                ntmpDate = lineLST['TimeStamp']
                if nchtype == chtype and nchnum == chnum and tmpDate == ntmpDate:
                    self.log('isReminder, True: ' + str(lineLST) + ' == ' + str(reminder_dict))
                    return True
        return False


    def removeReminder(self, reminder_dict, auto=True):
        self.log('removeReminder')
        title   = reminder_dict['Title']
        chtype  = reminder_dict['Chtype']
        chnum   = reminder_dict['Chnum']
        tmpDate = reminder_dict['TimeStamp']
        Notify_Time, epochBeginDate = self.cleanReminderTime(tmpDate)
        
        if auto == False:
            if yesnoDialog('Would you like to remove the reminder for [B]%s[/B] on channel [B]%s[/B] at [B]%s[/B] ?'%(title,chnum,str(Notify_Time)), header='PseudoTV Live - Reminder') == True:
                return

        if self.ReminderLst and len(self.ReminderLst) > 0:
            for n in range(len(self.ReminderLst)):
                lineLST = self.ReminderLst[n]
                nchtype  = lineLST['Chtype']
                nchnum   = lineLST['Chnum']
                ntmpDate = lineLST['TimeStamp']

                if nchtype == chtype and nchnum == chnum and tmpDate == ntmpDate:
                    self.ReminderLst.pop(n)
                    self.saveReminder()
                    break


    def showReminder(self, reminder_dict):
        self.log('showReminder')
        record    = (reminder_dict['Record']) == 'True'
        title   = reminder_dict['Title']
        chtype  = reminder_dict['Chtype']
        chnum   = reminder_dict['Chnum']
        chlogo  = reminder_dict['LOGOART']
        tmpDate = reminder_dict['TimeStamp']
        Notify_Time, epochBeginDate = self.cleanReminderTime(tmpDate)
        setProperty('PTVL.Reminder_title',title)
        setProperty('PTVL.Reminder_chnum',str(chnum))
        setProperty('PTVL.Reminder_chlogo',chlogo)
        setProperty('PTVL.Reminder_time',str(Notify_Time))
        
        if REAL_SETTINGS.getSetting("AutoJump") == "true":
            if self.currentChannel != int(chnum):
                self.ReminderPrompt()
        else:
            for i in range(REMINDER_COUNTDOWN):
                if i == 0:
                    alert = ALERT_SFX
                else:
                    alert = ''
                chlogo = self.getChlogo(channel)
                infoDialog("on channel " + str(channel) + " starts in " + str(IDLE_DELAY-i) +"sec",title, sound=alert, icon=chlogo)
        self.removeReminder(reminder_dict)



    def loadReminder(self):
        self.log('loadReminder')
        try:
            ReminderLst = eval(REAL_SETTINGS.getSetting("ReminderLst"))
        except:
            ReminderLst = (REAL_SETTINGS.getSetting("ReminderLst"))

        if ReminderLst and len(ReminderLst) > 0:
            for n in range(len(ReminderLst)):
                lineLST = ReminderLst[n]
                tmpDate = lineLST['TimeStamp']
                Notify_Time, epochBeginDate = self.cleanReminderTime(tmpDate)
                self.log('loadReminder, Loading ' + str(n) + '/' + str(len(ReminderLst)) + ':' + str(lineLST))

                now = time.time()
                if epochBeginDate > now:
                    self.setReminder(auto=True,reminder_dict=lineLST)
                else:
                    self.removeReminder(lineLST)


    def saveReminder(self, reminder_dict=None):
        self.log('saveReminder')
        if reminder_dict:
            self.ReminderLst.append(reminder_dict)
        setProperty("PTVL.ReminderLst", str(self.ReminderLst))
        REAL_SETTINGS.setSetting("ReminderLst", str(self.ReminderLst))


    def setReminder(self, auto=False, record=False, reminder_dict=None, pType='OVERLAY'):
        self.log('setReminder')
        if reminder_dict:
            record  =  reminder_dict['Record'] == 'True'
            chtype  =  reminder_dict['Chtype']
            tmpDate =  reminder_dict['TimeStamp']
            title   =  reminder_dict['Title']
            SEtitle =  reminder_dict['SEtitle']
            chnum   =  reminder_dict['Chnum']
            chname  =  reminder_dict['Chname']
            poster  =  reminder_dict['poster']
            fanart  =  reminder_dict['fanart']
            chlogo  =  reminder_dict['LOGOART']
        else:
            chtype  = getProperty(("%s.Chtype")%pType)
            tmpDate = getProperty(("%s.TimeStamp")%pType)
            title   = getProperty(("%s.Title")%pType)
            SEtitle = getProperty(("%s.SEtitle")%pType)
            chnum   = getProperty(("%s.Chnum")%pType)
            chname  = getProperty(("%s.Chname")%pType)
            poster  = getProperty(("%s.poster")%pType)
            fanart  = getProperty(("%s.landscape")%pType)
            chlogo  = getProperty(("%s.LOGOART")%pType)

        reminder_dict = {'Chtype': chtype, 'TimeStamp': tmpDate, 'Record': str(record), 'Title': title, 'SEtitle': SEtitle, 'Chnum': chnum, 'Chname': chname, 'poster': poster, 'fanart': fanart, 'LOGOART': chlogo}

        if int(chtype) == 8 and len(tmpDate) > 0:
            self.settingReminder = True
            Notify_Time, epochBeginDate = self.cleanReminderTime(tmpDate)

            if auto == False:
                if self.isReminder(reminder_dict=reminder_dict) == True:
                    self.removeReminder(reminder_dict, False)
                else:
                    if yesnoDialog("Would you like to set a reminder for [B]%s[/B] on channel [B]%s[/B] at [B]%s[/B] ?"%(title,chnum,str(Notify_Time)), header='PseudoTV Live - Reminder') == True:
                        auto = True
                    
            if auto == True:
                now = time.time()
                reminder_time = round(((epochBeginDate - now) - REMINDER_COUNTDOWN) / 60)#In minutes
                reminder_Threadtime = float((int(reminder_time)*60) - REMINDER_DELAY)#In seconds
                if reminder_Threadtime > 0:
                    if self.ReminderTimer.isAlive():
                        self.ReminderTimer.join()
                        self.ReminderTimer.cancel()
                    self.log('setReminder, setting =' + str(reminder_dict))
                    infoDialog("Reminder Set for " + str(Notify_Time), icon=chlogo)
                    self.saveReminder(reminder_dict)
                    self.ReminderTimer = threading.Timer(reminder_Threadtime, self.showReminder, [reminder_dict])
                    self.ReminderTimer.name = "ReminderTimer"
                    if self.isExiting == False:
                        self.ReminderTimer.start()
                else:
                    infoDialog("on channel " + chnum + " has already started",title, sound=ERROR_SFX, icon=self.getChlogo(chnum))
            self.settingReminder = False
        else:
            infoDialog("Reminders only available for LiveTV", sound=ERROR_SFX)
            if auto == True:
                self.removeReminder(reminder_dict)

                
    def getTMPSTR(self, chtype, chname, chnum, mediapath, position):
        self.log('getTMPSTR')         
        if self.getTMPSTRTimer.isAlive():
            self.getTMPSTRTimer.join() 
            self.getTMPSTRTimer.cancel()
        self.getTMPSTRTimer = threading.Timer(0.1, self.getTMPSTR_Thread, [chtype, chname, chnum, mediapath, position])
        self.getTMPSTRTimer.name = "getTMPSTRTimer" 
        if self.isExiting == False:
            self.getTMPSTRTimer.start()  
        
        
    def getTMPSTR_Thread(self, chtype, chname, chnum, mediapath, position):
        self.log('getTMPSTR_Thread') 
        tmpstr = self.channelList.getItem(self.channelList.requestItem(mediapath))
        setProperty("OVERLAY.OnDemand_tmpstr",str(tmpstr))
        self.setMediaInfo(chtype, chname, chnum, mediapath, position, tmpstr)

        
    def EPGtypeToggle(self):
        self.log('EPGtype')     
        ColorType = REAL_SETTINGS.getSetting('EPGcolor_enabled')
 
        if ColorType == '0':
            REAL_SETTINGS.setSetting("EPGcolor_enabled", "1")
            infoDialog("EPG Color by Genre")
        elif ColorType == '1':
            REAL_SETTINGS.setSetting("EPGcolor_enabled", "2")
            infoDialog("EPG Color by Chtype")
        elif ColorType == '2':
            REAL_SETTINGS.setSetting("EPGcolor_enabled", "3")
            infoDialog("EPG Color by Rating")
        elif ColorType == '3':
            REAL_SETTINGS.setSetting("EPGcolor_enabled", "0")
            infoDialog("EPG Color Disabled")
           
           
    def hideMenuControl(self, type):
        self.log("hideMenuControl")
        if self.MenuControlTimer.isAlive():
            self.MenuControlTimer.cancel()            
        self.MenuControlTimer = threading.Timer(self.InfTimer, self.MenuControl,[type,self.InfTimer,True])           
        self.MenuControlTimer.name = "MenuControlTimer"  
        self.MenuControlTimer.start()
            
                     
    def MenuControl(self, type, timer, hide=False):
        self.log("MenuControl, type = " + type + ", hide = " + str(hide))
        if self.MenuControlTimer.isAlive():
            self.MenuControlTimer.cancel()
        
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
                self.showingMenu = False  
                self.getControl(119).setVisible(False) 
            else:
                self.showMenu() 
                
        elif type == 'MenuAlt':
            if hide == True:
                self.showingMenuAlt = False                   
                self.setFocusId(1001)  
                self.OnNowControlList.setVisible(False)   
                self.getControl(130).setVisible(False)
                self.MenuControl('Menu',self.InfTimer)
                xbmc.sleep(10)
            else:
                self.showOnNow()
                
        elif type == 'Info':
            if hide == True:
                self.hideInfo()
            else:
                self.showInfo(timer)
                
        elif type == 'MoreInfo':
            if hide == True:
                self.showingMoreInfo = False           
                self.getControl(222).setVisible(False)
            else:
                self.showMoreInfo()
                
                
    def Jump2Favorite(self):
        NextFav = self.FavChanLst[0]
        for n in range(len(self.FavChanLst)):
            if int(self.FavChanLst[n]) > self.currentChannel:
                NextFav = self.FavChanLst[n]
                break   
        return self.fixChannel(int(NextFav))

        
    def chkChanFavorite(self, chan=None):
        if not chan:
            chan = self.currentChannel
        if str(chan) in self.FavChanLst:
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
                
       
    # TODO add timebar and button update here         
    def setSeekBarTime(self):
        if self.Player.isPlaybackValid():
            # self.removeControls([self.currentPlayInfoTime])
            # hide bar for content that doesn't produce progress details. Can't use setVisible because notice focus issue.
            if self.Player.getPlayerFile().startswith(('http','pvr','rtmp','rtsp','hdhomerun','upnp')) and self.Player.getTime() <= 0:
                self.log("setSeekBarTime, Missing")
                seekButton_xpos = -1000
                seekButton_ypos = -1000
            elif self.Player.getTime() < self.Player.getTotalTime()/30 or self.Player.getTime() > (self.Player.getTotalTime()/30)*29:
                self.log("setSeekBarTime, Hidden")
                seekButton_xpos = -1000
                seekButton_ypos = -1000
            else:
                # if self.showingMoreInfo == True:
                    # try:
                        # temp_xpos = self.currentPlayMoreInfoTime_xpos
                        # seekButton_ypos = self.currentPlayMoreInfoTime_ypos
                        # self.log("setSeekBarTime, MoreInfo")
                        # self.currentPlayInfoTime.setWidth(self.getControl(5005).getWidth())
                        # self.currentPlayInfoTime.setHeight(self.getControl(5005).getHeight())
                        # seekButton_width = int(round(self.getControl(5005).getWidth() / 2)) #find width of button and place in the middle.
                        # seekBar_width = self.getControl(5004).getWidth()
                        # seekBar_xpos, temp_ypos = self.getControl(5004).getPosition()
                        # perPlayed = 100 - (((self.Player.getTotalTime() - self.Player.getTime()) / self.Player.getTotalTime()) * 100)
                        # seekButton_xpos = (temp_xpos + int(round((perPlayed * seekBar_width)/100))) - seekButton_width
                    # except Exception,e:
                        # self.log("setSeekBarTime, failed! " + str(e))
                        # perPlayed = 0
                        # seekButton_xpos = -1000
                        # seekButton_ypos = -1000
                # else:
                try:
                    self.log("setSeekBarTime, Info")
                    temp_xpos = self.currentPlayInfoTime_xpos
                    seekButton_ypos = self.currentPlayInfoTime_ypos
                    self.currentPlayInfoTime.setWidth(self.getControl(5006).getWidth())
                    self.currentPlayInfoTime.setHeight(self.getControl(5006).getHeight())
                    seekButton_width = int(round(self.getControl(5006).getWidth() / 2)) #find width of button and place in the middle.
                    seekBar_width = self.getControl(5007).getWidth()
                    seekBar_xpos, temp_ypos = self.getControl(5007).getPosition()
                    perPlayed = 100 - (((self.Player.getTotalTime() - self.Player.getTime()) / self.Player.getTotalTime()) * 100)
                    seekButton_xpos = (temp_xpos + int(round((perPlayed * seekBar_width)/100))) - seekButton_width
                except Exception,e:
                    self.log("setSeekBarTime, failed! " + str(e))
                    perPlayed = 0
                    seekButton_xpos = -1000
                    seekButton_ypos = -1000
                        
            self.currentPlayInfoTime.setPosition(seekButton_xpos, seekButton_ypos)
            # if getProperty('OVERLAY.PROGBAR_TYPE') == 'Player.TimeRemaining':
                # self.currentPlayInfoTime.setLabel(str(xbmc.getInfoLabel('Player.TimeRemaining')))
            # else:
                # self.currentPlayInfoTime.setLabel(str(xbmc.getInfoLabel('Player.Time')))
          
          
    def FEEDtoggle(self):
        self.log("FEEDtoggle")
        UpdateRSS() 
        if getProperty("PTVL.FEEDtoggle") == "true":
            setProperty("PTVL.FEEDtoggle","false")
        else:
            setProperty("PTVL.FEEDtoggle","true")

            
    def playSFX(self, action):
        self.log("playSFX")
        if REAL_SETTINGS.getSetting("SFX_Enabled") != "true":
            return
        elif action in ['ACTION_CLICK', ACTION_SELECT_ITEM, ACTION_MOVE_DOWN, ACTION_MOVE_UP, ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT]:
            xbmc.playSFX(SELECT_SFX)
        elif action in [ACTION_CONTEXT_MENU, ACTION_PAGEDOWN, ACTION_PAGEUP]:
            xbmc.playSFX(CONTEXT_SFX)
        elif action in [ACTION_PREVIOUS_MENU]:
            xbmc.playSFX(BACK_SFX)
        elif action in ['ACTION_ALERT']:
            xbmc.playSFX(ALERT_SFX)
     
     
    def setProp(self, title, year, chlogo, chtype, chnum, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, subtitle, playcount, season, episode, timestamp, pType='OVERLAY'):
        self.log("setProp, title = " + title + ', pType = ' + pType)
        if pType == 'EPG':
            if self.setPropTimer.isAlive():
                self.setPropTimer.cancel()
        else:
            if self.setPropTimer.isAlive():
                self.setPropTimer.join()
        self.setPropTimer = threading.Timer(0.1, self.setProp_thread, [title, year, chlogo, chtype, chnum, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, subtitle, playcount, season, episode, timestamp, pType])
        self.setPropTimer.name = "setPropTimer"   
        if self.isExiting == False:    
            self.setPropTimer.start()

            
    def setProp_thread(self, title, year, chlogo, chtype, chnum, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, subtitle, playcount, season, episode, timestamp, pType='OVERLAY'):
        self.log("setProp_thread, title = " + title + ', pType = ' + pType)      
        setProperty("%s.Chtype"%pType,str(chtype)) 
        setProperty("%s.Chnum"%pType,str(chnum))
        setProperty("%s.TimeStamp"%pType,str(timestamp))
        setProperty("%s.Mediapath"%pType,mediapath)
        setProperty("%s.Playcount"%pType,str(playcount))
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
        setProperty("%s.Genre"%pType,genre)
        setProperty("%s.Rating"%pType,rating)
        setProperty("%s.isHD"%pType,hd)
        setProperty("%s.hasCC"%pType,cc)
        setProperty("%s.Stars"%pType,stars)
        # extended info
        year, title, showtitle = getTitleYear(title, year)
        setProperty("%s.Cleantitle"%pType,title)
        setProperty("%s.Showtitle"%pType,showtitle)
        setProperty("%s.Year"%pType,str(year))
        setProperty("%s.ID"%pType,str(id))
        setProperty("%s.Tagline"%pType,subtitle)
        setProperty("%s.LOGOART"%pType,chlogo)
        # fill art properties
        self.fillArtwork(type, title, year, chtype, chname, id, dbid, mpath, pType)
        # extra info
        if isLowPower() == False:
            self.isNew(pType)
            self.isManaged(pType)
        # todo rss ticker that matches genre
        # if pType == 'OVERLAY':  
            # getRSSFeed(getProperty("OVERLAY.Genre")) 
           
        
    def fillArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, pType):
        if pType == 'EPG':
            artTypes = self.artEPG_Types
        elif pType == 'OVERLAY.PLAYING':
            artTypes = list(set(self.artOVERLAY_Types + ['poster','fanart']))
        else:
            artTypes = self.artOVERLAY_Types
        
        self.log('fillArtwork, pType = ' + pType + ' artTypes = ' + str(artTypes))
        for n in range(len(artTypes)):
            try:
                artType = (artTypes[n]).lower()
                self.setArtwork(type, title, year, chtype, chname, id, dbid, mpath, EXTtype(artType), artType, pType)
            except:
                pass
                

    def setArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, typeEXT, artType, pType='OVERLAY'):
        self.log('setArtwork, chtype = ' + str(chtype) + ', id = ' + str(id) +  ', dbid = ' + str(dbid) + ', typeEXT = ' + typeEXT + ', artType = ' + artType + ', pType = ' + str(pType))  
        if pType == 'EPG':
            if self.setArtworkTimer.isAlive():
                self.setArtworkTimer.cancel()
            self.setArtworkTimer = threading.Timer(0.1, self.setArtwork_Thread, [type, title, year, chtype, chname, id, dbid, mpath, typeEXT, artType, pType])
            self.setArtworkTimer.name = "setArtworkTimer"   
            if self.isExiting == False:    
                self.setArtworkTimer.start()
        else:
            self.setArtwork_Thread(type, title, year, chtype, chname, id, dbid, mpath, typeEXT, artType, pType)
            
          
    def setArtwork_Thread(self, type, title, year, chtype, chname, id, dbid, mpath, typeEXT, artType, pType='OVERLAY'):
        self.log('setArtwork_Thread, chtype = ' + str(chtype) + ', id = ' + str(id) +  ', dbid = ' + str(dbid) + ', typeEXT = ' + typeEXT + ', artType = ' + artType + ', pType = ' + str(pType))  
        try:
            setImage = self.findArtwork(type, title, year, chtype, chname, id, dbid, mpath, typeEXT) 
            setProperty(("%s.%s" %(pType, artType)),setImage)
        except Exception,e:
            self.log('setArtwork_Thread, failed! ' + str(e))
            
            
    # must be called by threaded function.
    def findArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, typeEXT):
        try:
            setImage = self.Artdownloader.FindArtwork(type, title, year, chtype, chname, id, dbid, mpath, typeEXT)
            if FileAccess.exists(setImage) == False:
                setImage = self.Artdownloader.SetDefaultArt(chname, mpath, typeEXT)
            setImage = uni(setImage)
            self.log('findArtwork, setImage = ' + setImage)   
            return setImage
        except Exception,e:
            self.log('findArtwork, failed! ' + str(e))
    
    
    def getArtwork(self, type, title, year, chtype, chname, id, dbid, mpath):
        poster = uni(self.findArtwork(type, title, year, chtype, chname, id, dbid, mpath, 'poster'))
        fanart = uni(self.findArtwork(type, title, year, chtype, chname, id, dbid, mpath, 'landscape'))
        return poster, fanart
    
         
    def isNew(self, pType='OVERLAY'):
        self.log("isNew")
        try:
            try:
                chtype = int(getProperty("%s.Chtype"%pType))
            except:
                chtype = 8
                
            mediapath = getProperty("%s.Mediapath"%pType)
            
            try:
                playcount = int(getProperty("%s.Playcount"%pType))
            except:
                playcount = 1
                
            if playcount > 0:
                setProperty("%s.isNEW"%pType,MEDIA_LOC + 'OLD.png')
                return 
            elif chtype == 8 and playcount == 0:
                setProperty("%s.isNEW"%pType,MEDIA_LOC + 'NEW.png')
                return 
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
                                setProperty("%s.isNEW"%pType,MEDIA_LOC + 'NEW.png')
                                return 
                    except:
                        pass 
            # todo parse youtube watched status? check metahandler playcount
        except Exception,e:
            self.log('isNew_Thread, failed! ' + str(e))
            self.log(traceback.format_exc(), xbmc.LOGERROR)
        setProperty("%s.isNEW"%pType,MEDIA_LOC + 'OLD.png')

        
    def isManaged(self, pType='OVERLAY'):
        self.log('isManaged') 
        try:
            # if isLowPower() == False:
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
            setProperty("%s.isManaged"%pType,IMAGES_LOC + 'NA.png') 
        except Exception,e:
            self.log('isManaged_Thread, failed! ' + str(e))
            self.log(traceback.format_exc(), xbmc.LOGERROR)
          
          
    # Adapted from lamdba's plugin
    def setWatchedStatus_Thread(self, type, title, year, id, dbid, epid, season, episode, playcount):
        self.log('setWatchedStatus_Thread')
        if type == 'movie':
            json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : %s, "playcount" : %s }, "id": 1 }' % ((dbid), (playcount)))
            self.channelList.sendJSON(json_query)  
            try:
                from metahandler import metahandlers
                metaget = metahandlers.MetaData(preparezip=False)
                metaget.get_meta('movie', title ,year=year)
                metaget.change_watched(type, '', id, season='', episode='', year='', watched=playcount)
            except Exception,e:
                self.log('setWatchedStatus, MOVIE:META failed! ' + str(e))
            # try:
                # if trakt.getTraktAddonMovieInfo() == False: trakt.markMovieAsWatched(self.imdb)
                # trakt.syncMovies()
            # except:
                # pass
        elif type in ['episode','tvshow']:
            try:
                json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "playcount" : %s }, "id": 1 }' % ((epid), (playcount)))
                self.channelList.sendJSON(json_query)  
            except Exception,e:
                self.log('setWatchedStatus, TV:DBID failed! ' + str(e))
            try:
                from metahandler import metahandlers
                metaget = metahandlers.MetaData(preparezip=False)
                metaget.get_meta('tvshow', title, imdb_id=id)
                metaget.get_episode_meta(title, id, season, episode)
                metaget.change_watched(type, '', id, season=season, episode=episode, year='', watched=playcount)
            except Exception,e:
                self.log('setWatchedStatus, TV:META failed! ' + str(e))
            # try:
                # if trakt.getTraktAddonEpisodeInfo() == False: trakt.markEpisodeAsWatched(self.tvdb, self.season, self.episode)
                # trakt.syncTVShows()
            # except:
                # pass
        # self.getControl(124).setLabel('Trakt')
        # self.getControl(125).setLabel('Test')
        # setProperty("OVERLAY.type4ART",'https://widgets.trakt.tv/users/f5b53eb814eb5335ca533f00dc74b330/watched/thumb@2x.jpg')  
        # self.showPOP(self.InfTimer + 2.5)

        
    def setWatchedStatus(self):
        self.log('setWatchedStatus')
        if REAL_SETTINGS.getSetting("Disable_Watched") == "true":
            if self.ChangeWatchedTimer.isAlive():
                self.ChangeWatchedTimer.join()
                self.ChangeWatchedTimer.cancel()
                
            type = getProperty("OVERLAY.Type")
            title = getProperty("OVERLAY.Cleantitle")
            id = getProperty("OVERLAY.ID")
            dbid = (getProperty("OVERLAY.DBID"))
            epid = (getProperty("OVERLAY.EPID"))
            season = (getProperty("OVERLAY.Season"))
            episode = (getProperty("OVERLAY.Episode"))
            year = (getProperty("OVERLAY.Year"))
            playcount = (getProperty("OVERLAY.Playcount"))
            self.ChangeWatchedTimer = threading.Timer(5.0, self.setWatchedStatus_Thread, [type, title, year, id, dbid, epid, season, episode, playcount])
            self.ChangeWatchedTimer.name = "ChangeWatchedTimer"
            if self.isExiting == False:
                self.ChangeWatchedTimer.start() 

            
    def clearProp(self, pType='OVERLAY'):
        self.log("clearProp")
        clearProperty("%s.poster"%pType)
        clearProperty("%s.banner"%pType)
        clearProperty("%s.fanart"%pType)
        clearProperty("%s.clearart"%pType)
        clearProperty("%s.clearlogo"%pType)
        clearProperty("%s.landscape"%pType)
        clearProperty("%s.Year"%pType)
        clearProperty("%s.ID"%pType)
        clearProperty("%s.Genre"%pType)
        clearProperty("%s.Rating"%pType)
        clearProperty("%s.Tagline"%pType)
        clearProperty("%s.Title"%pType)
        clearProperty("%s.TimeStamp"%pType)
        clearProperty("%s.Showtitle"%pType)
        clearProperty("%s.Cleantitle"%pType)
        clearProperty("%s.Chtype"%pType)
        clearProperty("%s.Chname"%pType)
        clearProperty("%s.Chnum"%pType)
        clearProperty("%s.Mpath"%pType)
        clearProperty("%s.Mediapath"%pType)
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
        clearProperty("%s.isHD"%pType)
        clearProperty("%s.hasCC"%pType)
        clearProperty("%s.Stars"%pType)

        
    def isWindowOpen(self):
        if getProperty("PTVL.EPG_Opened") == "true":
            return 'EPG'
        elif getProperty("PTVL.DVR_Opened") == "true":
            return 'DVR'
        elif getProperty("PTVL.OnDemand_Opened") == "true":
            return 'OnDemand'
        elif getProperty("PTVL.APPS_Opened") == "true":
            return 'APPS'
        else:
            return False
            
        
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
        # open new window
        if window.upper() == 'EPG':
            self.myEPG.doModal()
        elif window.upper() == 'DVR':
            self.myDVR.show()
        elif window.upper() == 'ONDEMAND':
            self.myOndemand.show()
        elif window.upper() == 'APPS':
            self.myApps.show()
          
    def getChtype(self, channel):
        try:
            chtype = self.channels[channel-1].type
        except:
            chtype = self.channelList.getChtype(channel)
        return chtype
           
           
    def getChname(self, channel):
        try:
            chname = self.channels[channel-1].name
        except:
            chname = self.channelList.getChname(channel)
        return chname

        
    def getChlogo(self, channel, fallback=True):
        try:
            chlogo = xbmc.translatePath(os.path.join(self.channelLogos,self.getChname(channel) + '.png'))
        except:
            chlogo = ''
        if FileAccess.exists(chlogo):
            return chlogo
        elif fallback == True:
            return THUMB
        else:
            return 'NA.png'

        
    def postBackgroundLoading(self):
        self.log('postBackgroundLoading')
        setProperty("PTVL.BackgroundLoading","false")
        # if isLowPower() == False:
            # self.channelThreadpause = False


    def playStartOver(self):
        self.log('playStartOver')
        playPOS = self.channels[self.currentChannel - 1].playlistPosition
        self.Player.playselected(playPOS)
        self.toggleShowStartover(False)
            
            
    def playOnNow(self):
        pos = self.OnNowControlList.getSelectedPosition()
        item = self.OnNowLst[pos]
        self.MenuControl('MenuAlt',self.InfTimer,True)
        self.MenuControl('Menu',self.InfTimer,True) 
        channel = int(self.channelList.cleanLabels(item.split('|')[0]))
        self.log('playOnNow, channel = ' + str(channel))
        if self.currentChannel != channel:
            self.setChannel(self.fixChannel(int(channel)))
            
         
    def playSelectShow(self):
        self.log("playSelectShow")
        cur_position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
        new_position = cur_position + self.infoOffset
        if cur_position != new_position:
            self.hideInfo()
            self.Player.playselected(self.channels[self.currentChannel - 1].fixPlaylistIndex(new_position))
            
    
    def playInputChannel(self):
        self.log("playInputChannel")
        # If we're manually typing the channel, set it now
        if self.inputChannel > 0:
            if self.inputChannel != self.currentChannel and self.inputChannel <= self.maxChannels:
                self.setChannel(self.fixChannel(self.inputChannel))
            self.inputChannel = -1
        else:
            # Otherwise, show the EPG
            self.openEPG()
        return

           
    def setPlayselected(self, url):
        self.log('setPlayselected, url = ' + url)
        try:
            if url.startswith(('rtmp','rtsp')):
                toTime = str((int(round((self.PlayTimeoutInt/int(self.ActionTimeInt))))/4)*3)
                if 'live=true' not in url:
                    url += ' live=true'
                if 'timeout=' in url:
                    url = re.sub(r'timeout=\d',"timeout=%s" % toTime,url) 
                else:
                    url += ' timeout=%s' % toTime
            elif url.startswith(('plugin')):
                url = ('PlayMedia('+url+')')  
                    
            if url.startswith(('plugin','PlayMedia')):
                xbmc.executebuiltin(tidy(url).replace(',', ''))   
            
            else:
                raise Exception()
                
            # if url.startswith(('http','pvr','rtmp','rtsp','hdhomerun','upnp')):
        
                # listitem = xbmcgui.ListItem(getProperty("OVERLAY.Title"))
                # content_type = getProperty("OVERLAY.Type").replace("tvshow","episode").replace("other","video").replace("youtube","video").replace("music","musicvideo")     

                # infoList = {}
                # # infoList['mediatype']     = (content_type or 'episode')
                # # infoList['duration']      = self.channels[self.currentChannel - 1].getItemDuration(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()) 
                # # infoList['mpaa']          = getProperty("OVERLAY.Rating")
                # # infoList['tvshowtitle']   = getProperty("OVERLAY.Cleantitle")
                # # infoList['title']         = getProperty("OVERLAY.Title")
                # # infoList['originaltitle'] = getProperty("OVERLAY.Showtitle")
                # # infoList['sorttitle']     = getProperty("OVERLAY.Cleantitle")
                # # infoList['studio']        = getProperty("OVERLAY.Chname")
                # # infoList['genre']         = getProperty("OVERLAY.Genre")
                # # infoList['plot']          = getProperty("OVERLAY.Description")
                # # infoList['tagline']       = getProperty("OVERLAY.Tagline")
                # # infoList['dateadded']     = getProperty("OVERLAY.TimeStamp")
                # # infoList['code']          = getProperty("OVERLAY.ID")
                # # infoList['year']          = int(getProperty("OVERLAY.Year") or '0')
                # # infoList['season']        = int(getProperty("OVERLAY.Season") or '0')
                # # infoList['episode']       = int(getProperty("OVERLAY.Episode") or '0')
                # # infoList['playcount']     = int(getProperty("OVERLAY.Playcount") or '0')
                # # infoList['rating']        = float(getProperty("OVERLAY.Stars") or '0.0')
                # # listitem.setInfo('Video', infoList)    

                # infoArt = {}
                # # infoArt['thumb']        = getProperty("OVERLAY.poster")
                # # infoArt['poster']       = getProperty("OVERLAY.poster")
                # # infoArt['banner']       = getProperty("OVERLAY.banner")
                # # infoArt['fanart']       = getProperty("OVERLAY.fanart")
                # # infoArt['clearart']     = getProperty("OVERLAY.clearart")
                # # infoArt['clearlogo']    = getProperty("OVERLAY.clearlogo")
                # # infoArt['landscape']    = getProperty("OVERLAY.landscape")
                # # infoList['icon']        = getProperty("OVERLAY.LOGOART")
                # # listitem.setArt(infoArt)
                # self.Player.play(url, listitem) 
        except Exception,e:
            self.log('setPlayselected, failed! ' + str(e))
            self.Player.play(url)

        
    def setBackgroundVisible(self, val):
        self.background.setVisible(val)
        setProperty("OVERLAY.BackgroundVisible",str(val)) 

        
    def setRecord(self, channel=None):
        self.log("setRecord")#todo
        if not channel:
            channel = self.currentChannel
        Comingsoon()
        
        
    def isRecord(self, chtype, channel, timestamp, pType='OVERLAY'):
        self.log("isRecord")#todo
        return False
        
        
    def cronJob(self):
        self.log("cronJob")
        while True:
            if self.isExiting == True:
                break
                
            self.cron_uptime += 1 # life  
            if self.showingInfo:
                self.setSeekBarTime()
                                   
            # 1min job
            self.oneMin_Job += 1
            if self.oneMin_Job == 60:
                self.oneMin_Job = 0
                self.ScrSavTimer()
                
            # 2min job
            self.twoMin_Job += 1
            if self.twoMin_Job == 120:
                self.twoMin_Job = 0
                GA_Request() 
                
            # 5min job
            self.fiveMin_Job += 1
            if self.fiveMin_Job == 300:
                self.fiveMin_Job = 0
                self.setOnNow()
                
            # 10min job
            self.tenMin_Job += 1
            if self.tenMin_Job == 600:
                self.log("cronJob, uptime = " + str(self.cron_uptime/60))
                self.tenMin_Job = 0
                
            # 15min job
            self.fifteenMin_Job += 1
            if self.fifteenMin_Job == 900:
                self.fifteenMin_Job = 0
                self.FEEDtoggle()
                purgeGarbage()
                
            time.sleep(1)
            

    def toggleMute(self):
        json_query = '{"jsonrpc":"2.0","method":"Application.SetMute","params":{"mute":"toggle"},"id":1}'
        self.channelList.sendJSON(json_query)
    
    
    def setMute(self, state):
        json_query = '{"jsonrpc":"2.0","method":"Application.SetMute","params":{"mute":%s},"id":1}' %state
        self.channelList.sendJSON(json_query)
                

    def disableSub(self):
        if getXBMCVersion() >= 15:
            self.Player.showSubtitles(False)
        else:
            self.Player.disableSubtitles() 

            
    def hasSubtitle(self):
        self.log("hasSubtitle")
        if len(self.Player.getAvailableSubtitleStreams()) > 0:
            return True
        else:
            return False

            
    def chkSub(self):
        if self.SubState == True:
            return 'Disable Subtitles'
        else:
            if self.hasSubtitle() == True:
                return 'Enable Subtitles'
            else:
                return 'Find Subtitle'
            

    def toggleSubtitles(self):
        self.log("toggleSubtitles")
        self.SubState = not bool(self.SubState)
        if self.SubState == True:
            if self.hasSubtitle() == False:
                xbmc.executebuiltin("ActivateWindow(SubtitleSearch)")
                return 
        self.Player.showSubtitles(self.SubState)        

        
    def openEPG(self):
        self.log("openEPG")
        if getProperty("PTVL.EPG_Opened") != "true":
            # Pause Background channel building while EPG is opened
            if self.channelThread.isAlive() and self.channelThreadpause == True:
                self.channelThread.pause()
                
            self.hideInfo()
            self.hidePOP()
            self.newChannel = 0
            self.windowSwap('EPG')

            # Resume Background channel building
            if self.channelThread.isAlive():
                self.channelThread.unpause()

            if self.newChannel != 0:
                self.setChannel(self.fixChannel(self.newChannel))
            return

            
    def setCurrentChannel(self):
        #Set Current Channel
        SUPchannel = int(REAL_SETTINGS.getSetting('SUPchannel'))                
        if SUPchannel == 0:
            REAL_SETTINGS.setSetting('CurrentChannel', str(self.currentChannel))
            
            
    def getGenreColor(self, genre):
        if genre in COLOR_RED_TYPE:
            return COLOR_RED
        elif genre in COLOR_GREEN_TYPE:
            return COLOR_GREEN
        elif genre in COLOR_mdGREEN_TYPE:
            return COLOR_mdGREEN
        elif genre in COLOR_BLUE_TYPE:
            return COLOR_BLUE
        elif genre in COLOR_ltBLUE_TYPE:
            return COLOR_ltBLUE
        elif genre in COLOR_CYAN_TYPE:
            return COLOR_CYAN
        elif genre in COLOR_ltCYAN_TYPE:
            return COLOR_ltCYAN
        elif genre in COLOR_PURPLE_TYPE:
            return COLOR_PURPLE
        elif genre in COLOR_ltPURPLE_TYPE:
            return COLOR_ltPURPLE
        elif genre in COLOR_ORANGE_TYPE:
            return COLOR_ORANGE
        elif genre in COLOR_YELLOW_TYPE:
            return COLOR_YELLOW
        elif genre in COLOR_GRAY_TYPE:
            return COLOR_GRAY
        else:#Unknown 
            return COLOR_ltGRAY
           
            
    def showWeather(self):
        self.log("showWeather")
        json_query = '{"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"weather"},"id":1}'
        self.channelList.sendJSON(json_query)


    def end(self, action=False):
        self.log('end')
        self.setBackgroundVisible(True)  
        self.clearOnNow()
        self.clearProp('EPG')
        self.clearProp('OVERLAY')
        self.clearProp('OVERLAY.NEXT')
        self.clearProp('OVERLAY.PLAYING')
        self.UPNPcontrol('stop')
        egTrigger('PseudoTV_Live - Exiting')
        setBackgroundLabel('Exiting: PseudoTV Live')
        setProperty("OVERLAY.LOGOART",THUMB) 
        xbmc.executebuiltin("PlayerControl(repeatoff)")
        curtime = time.time()
        self.setLastChannel()
        self.setCurrentChannel() 
        updateDialog = xbmcgui.DialogProgressBG()
        updateDialog.create("PseudoTV Live", "Exiting")
        
        if CHANNEL_SHARING == True and self.isMaster:
            updateDialog.update(0, "Exiting", "Removing File Locks")
            setBackgroundLabel('Exiting: Removing File Locks')
            GlobalFileLock.unlockFile('MasterLock')
        GlobalFileLock.close()
                
        # destroy window
        del self.myDVR
        del self.myApps
        del self.myIdle
        del self.myOndemand
            
        if self.Player.isPlaybackValid() == True:
            self.lastPlayTime = self.Player.getTime()
            self.lastPlaylistPosition = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
            self.Player.stop()

        # Prevent the player from setting the sleep timer      
        self.isExiting = True 
        self.Player.stopped = True
        updateDialog.update(1, "Exiting", "Stopping Timers")
        setBackgroundLabel('Exiting: Stopping Timers')

        if self.UPNPcontrolTimer.isAlive():
            self.UPNPcontrolTimer.cancel()
            
        if self.channelLabelTimer.isAlive():
            self.channelLabelTimer.cancel()
            
        if self.GotoChannelTimer.isAlive():
            self.GotoChannelTimer.cancel()

        if self.cronTimer.isAlive():
            self.cronTimer.cancel()

        updateDialog.update(2)

        if self.notificationTimer.isAlive():
            self.notificationTimer.cancel()
            
        if self.infoTimer.isAlive():
            self.infoTimer.cancel()
            
        if self.popTimer.isAlive():
            self.popTimer.cancel()
            
        updateDialog.update(3)
        
        if self.sleepTimer.isAlive():
            self.sleepTimer.cancel()
            
        if self.SleepTimerCountdownTimer.isAlive():
            self.SleepTimerCountdownTimer.cancel()
            
        if self.idleTimer.isAlive():
            self.idleTimer.cancel()
            
        if self.idleTimerCountdownTimer.isAlive():
            self.idleTimerCountdownTimer.cancel()
            
        updateDialog.update(4, "Exiting", "Stopping Threads")  
        setBackgroundLabel('Exiting: Stopping Threads')

        if self.playerTimer.isAlive():
            self.playerTimer.cancel()
            
        if self.MenuControlTimer.isAlive():
            self.MenuControlTimer.cancel()
            
        if self.getTMPSTRTimer.isAlive():
            self.getTMPSTRTimer.cancel()
            
        if self.ReminderTimer.isAlive():
            self.ReminderTimer.cancel()
            self.ReminderTimer.join()
            
        if self.ChangeWatchedTimer.isAlive():
            self.ChangeWatchedTimer.cancel()
            self.ChangeWatchedTimer.join()
            
        updateDialog.update(5, "Exiting", "Stopping Meta Threads")
        setBackgroundLabel('Exiting: Stopping Meta Threads')  
            
        if self.setPropTimer.isAlive():
            self.setPropTimer.cancel()
            self.setPropTimer.join()
            
        if self.setArtworkTimer.isAlive():
            self.setArtworkTimer.cancel()
            self.setArtworkTimer.join()

        try:
            if FindLogoThread.isAlive():
                FindLogoThread.cancel()
                FindLogoThread.join()
                
            if download_silentThread.isAlive():
                download_silentThread.cancel()
                download_silentThread.join()
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
                setBackgroundLabel('Exiting: Stopping Channel Threads')  

            if self.channelThread.isAlive():
                self.log("Problem joining channel thread", xbmc.LOGERROR)

        if self.isMaster:
            ADDON_SETTINGS.setSetting('LastExitTime', str(int(curtime)))

        if self.timeStarted > 0 and self.isMaster:
            updateDialog.update(35, "Exiting", "Saving Settings")
            setBackgroundLabel('Exiting: Saving Settings')  
            validcount = 0

            for i in range(self.maxChannels):
                if self.channels[i].isValid:
                    validcount += 1
            
            if validcount > 0:
                incval = 65.0 / float(validcount)

                for i in range(self.maxChannels):
                    updateDialog.update(35 + int((incval * i)))
                    setBackgroundLabel('Exiting: Saving Settings (' + str(int((incval * i))/10) + '%)')
                    
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

        REAL_SETTINGS.setSetting('LogoDB_Override', "false") 
        REAL_SETTINGS.setSetting('Normal_Shutdown', "true")
        setBackgroundLabel('Exiting: Shutting Down')
        setProperty("PseudoTVRunning", "False")
        clearProperty('SkinHelperShutdownRequested')
        FileAccess.finish()
        updateDialog.close()
        self.setExitAction(action)
        self.close()


    def setExitAction(self, action):
        if action == 'Restart':
            xbmc.executebuiltin('XBMC.AlarmClock( Restarting PseudoTV Live, XBMC.RunScript(' + ADDON_PATH + '/default.py),0.5,true)')
        elif action == 'Quit':
            xbmc.executebuiltin('XBMC.AlarmClock( Quiting Kodi, XBMC.Quit(),0.5,true)')
        elif action == 'Powerdown':
            xbmc.executebuiltin('XBMC.AlarmClock( Powering Down Device, XBMC.Powerdown(),0.5,true)')
            
 
# xbmc.executebuiltin('StartAndroidActivity("com.netflix.mediaclient"),return')
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"videoosd"},"id":5}
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"osdaudiosettings"},"id":17}
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"osdvideosettings"},"id":16}