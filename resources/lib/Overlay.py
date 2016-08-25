#   Copyright (C) 2016 Kevin S. Graer
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
from VOD import VOD
from APP import APP
from ChannelList import ChannelList
from ChannelListThread import ChannelListThread
from FileAccess import FileLock, FileAccess
from Migrate import Migrate
from Artdownloader import *
from Upnp import Upnp
from utils import *
from parsers import ustvnow

try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
   
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
    

    def getPlayerTotalTime(self):
        try:
            return self.getTotalTime()
        except:
            return 0
            
            
    def getPlayerTime(self):
        try:
            return self.getTime()
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
        sample_time = self.getPlayerTime()
        xbmc.sleep(time)
        if self.getPlayerTime() != sample_time:
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

        
    def IsInternetStream(self):
        return xbmc.getCondVisibility('Player.IsInternetStream')
    
    
    def isSomethingPlaying(self):
        if self.overlay.isExiting == True or self.isPlaybackPaused() == True:
            return True
        if isLowPower() == True:
            isKodiPlaying = self.isPlaybackValid()
        else:
            if self.ignoreNextStop == True and self.getPlayerFile().startswith(STREAM_TYPES):
                isKodiPlaying = self.isPlayingValid(250)
            else:
                isKodiPlaying = self.isPlaybackValid()
        self.log("isSomethingPlaying, = " + str(isKodiPlaying))
        return isKodiPlaying

        
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
        #Kryptons new video player broke videowindow control for dialog domodals..
        if getXBMCVersion() >= 17:
            setProperty("PTVL.VideoWindow","false")
       
        while self.isSomethingPlaying() == False:
            self.log("onPlaybackAction, waiting for VideoPlayback")
            xbmc.sleep(250)
        
        self.overlay.setMediaProp()
        if self.overlay.infoOnChange == True:
            self.overlay.showInfo()
        self.overlay.showChannelLabel(self.overlay.currentChannel)

        # send play command to upnp
        self.overlay.UPNPcontrol('play', self.getPlayerTitle(), self.getPlayerFile(), self.getPlayerTime())
        
        if self.overlay.getChtype(self.overlay.currentChannel) not in IGNORE_SEEKTIME_CHTYPE:
            # playback starts paused, resume automatically.
            self.resumePlayback()
          
        # Unmute
        self.overlay.setMute(False)
        self.overlay.setBackgroundVisible(False)
        
        # trakt scrob. playing show
        if REAL_SETTINGS.getSetting("TraktScrob") == "true":
            setTraktScrob()

                  
    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        self.stopped = False
        # show pip videowindow    
        setProperty("PTVL.VideoWindow","true")
        setProperty('PTVL.PLAYER_LOG',self.getPlayerFile())
        if self.isPlaybackValid() == True:
            # devise a way to detect ondemand playback todo   
            # fix for fullscreen video bug when playback is started while epg is opened.
            if self.overlay.isWindowOpen() != False:
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
        self.stopped = True
        
        # set static videowindow
        setProperty("PTVL.VideoWindow","false")
        self.overlay.setBackgroundVisible(True)
        self.overlay.UPNPcontrol('stop')
        
        # resume playlist after ondemand
        self.onDemandEnded()
        
        # clear trakt scrob.
        clearTraktScrob()

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
        self.cronTimer = threading.Timer(1.0, self.cronJob)
        self.playerTimer = threading.Timer(1.0, self.playerTimerAction)
        self.SeekTimer = threading.Timer(1.0, self.SeekTimerAction)
        self.notificationTimer = threading.Timer(1.0, self.notificationAction)

        # single queue timers
        self.setPropTimer = threading.Timer(0.1, self.setProp_thread)
        self.fillArtworkTimer = threading.Timer(0.1, self.fillArtwork_thread)
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
        self.ChannelGuideLst = [] 
        self.ReminderLst = []
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
        self.isChannelChanging = False       
        self.showingSleep = False
        self.showingReminder = False
        self.ignoreInfoAction = False
        self.OnDemand = False 
        self.showChannelBug = False
        self.showNextItem = False
        self.ignoreSeektime = False
        self.ignoreSeeking = False
        self.PinLocked = False
        self.PinNumber = '0000'
        self.inputChannel = -1
        self.seektime = 0
        self.lastActionTime = 0  
        self.timeStarted = 0  
        self.currentChannel = 1
        self.infoOffset = 0
        self.idleTimeValue = 0
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
        self.shortItemLength = 240
        self.runningActionChannel = 0
        self.channelDelay = 0
        self.cron_uptime = 0 
        self.progressStartTime = datetime.datetime.now()
        self.progressPercentage = 0
        self.progressPreviousPercentage = 0
        self.sleep_cntDown = IDLE_DELAY  
        self.channelbugcolor = CHANBUG_COLOR
        self.notPlayingAction = 'Up'
        self.Browse = ''
        self.clockMode = int(REAL_SETTINGS.getSetting("ClockMode"))
        self.showSeasonEpisode = REAL_SETTINGS.getSetting("ShowSeEp") == "true"
        self.InfTimer = INFOBAR_TIMER[int(REAL_SETTINGS.getSetting('InfoTimer'))] 
        self.FavChanLst = (REAL_SETTINGS.getSetting("FavChanLst")).split(',')
        self.DisablePlayback = REAL_SETTINGS.getSetting("DisablePlayback") == "true"    
        self.playActionTime = int(REAL_SETTINGS.getSetting("playActionTime"))
        self.log('playActionTime = ' + str(self.playActionTime))
  
        for i in range(3):
            self.channelLabel.append(xbmcgui.ControlImage(50 + (50 * i), 50, 50, 50, IMAGES_LOC + 'solid.png', colorDiffuse = self.channelbugcolor))
            self.addControl(self.channelLabel[i])
            self.channelLabel[i].setVisible(False)
            
        self.startTime = time.time()
        self.endTime = time.time()  
        self.monitor = xbmc.Monitor()
        self.Player = MyPlayer()
        self.Player.overlay = self
        self.actionSemaphore = threading.BoundedSemaphore()
        self.channelThread = ChannelListThread()
        self.channelThread.myOverlay = self 
        self.Artdownloader = Artdownloader()
        self.doModal()
        self.log('__init__ return')

        
    def resetChannelTimes(self):
        for i in range(self.maxChannels):
            self.channels[i].setAccessTime(self.timeStarted - self.channels[i].totalTimePlayed)
            

    # override the doModal function so we can setup everything first
    def onInit(self):
        self.log('onInit')
        self.log('PTVL Version = ' + ADDON_VERSION)   
        egTrigger('PseudoTV_Live - Starting')                
        self.migrate = Migrate()
        self.migrate.myOverlay = self
        self.channelList = ChannelList()
        self.channelList.myOverlay = self
        self.Upnp = Upnp()
        
        self.enableUPNP = False
        if len(self.Upnp.IPPlst) > 0:
            self.enableUPNP = True
          
        self.background = self.getControl(101)
        self.BackgroundProgress = self.getControl(99)
        self.BackgroundProgress.setVisible(False)
        self.setBackgroundStatus('Initializing: PseudoTV Live',0)
        setProperty("PTVL.LOGO",THUMB)
        setProperty("OVERLAY.LOGOART",THUMB)
        setProperty("PTVL.INIT_CHANNELSET","false")
                
        self.hidePOP()
        self.hideInfo()
        self.hideSleep()   
        self.setVisible(130,False) 
        self.setVisible(222,False)            
        self.setVisible(119,False) 
        self.setBackgroundVisible(True)
        self.BackgroundProgress.setVisible(True)
                  
        #xbmc.executeJSONRPC('{"jsonrpc":"2.0", "id":1, "method":"Settings.SetSettingValue","params":{"setting":"%s","value":%s}}' %('lookandfeel.enablerssfeeds','true'))()
        try:
            Normal_Shutdown = REAL_SETTINGS.getSetting('Normal_Shutdown') == "true"
        except:
            REAL_SETTINGS.setSetting('Normal_Shutdown', "true")
            Normal_Shutdown = REAL_SETTINGS.getSetting('Normal_Shutdown') == "true"
                    
        if REAL_SETTINGS.getSetting("Autotune") == "true" and REAL_SETTINGS.getSetting("Warning1") == "true":
            self.log('Autotune, onInit')       
            if getSize(SETTINGS_FLE) > SETTINGS_FLE_DEFAULT_SIZE:
                Backup(SETTINGS_FLE, SETTINGS_FLE_PRETUNE)

            #Reserve channel check
            if REAL_SETTINGS.getSetting("reserveChannels") == "false":  
                self.log('Autotune, not reserved')  
                FileAccess.delete(SETTINGS_FLE)
                self.log('Autotune, Setting2 Deleted...')

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

        self.UPNPcontrol('stop')
        self.backupFiles()
        ADDON_SETTINGS.loadSettings()
        
        if CHANNEL_SHARING == True:
            FileAccess.makedirs(LOCK_LOC)
            self.isMaster = GlobalFileLock.lockFile("MasterLock", False)
        else:
            self.isMaster = True

        if self.isMaster:
            self.migrate.autoTune()
               
        self.textureButtonFocusAlt = MEDIA_LOC + BUTTON_FOCUS_ALT
        self.timeButtonNoFocus = MEDIA_LOC + TIME_BUTTON
        
        self.myEPG = EPGWindow("script.pseudotv.live.EPG.xml", ADDON_PATH, Skin_Select)
        self.myDVR = DVR("script.pseudotv.live.DVR.xml", ADDON_PATH, Skin_Select)
        self.myVOD = VOD("script.pseudotv.live.VOD.xml", ADDON_PATH, Skin_Select)
        self.myApp = APP("script.pseudotv.live.APP.xml", ADDON_PATH, Skin_Select)
        self.myIdle = IDLE.GUI("script.pseudotv.live.Idle.xml", ADDON_PATH, "Default")
        
        self.myEPG.MyOverlayWindow = self
        self.myDVR.MyOverlayWindow = self
        self.myVOD.MyOverlayWindow = self
        self.myApp.MyOverlayWindow = self
                    
        # Don't allow any actions during initialization
        self.actionSemaphore.acquire()
        self.timeStarted = time.time() 

        if self.readConfig() == False:
            return
           
        self.myEPG.channelLogos = self.channelLogos
        self.maxChannels = len(self.channels)

        if self.maxChannels == 0 and REAL_SETTINGS.getSetting("Autotune") == "false":
            if yesnoDialog("No Channels Configured", "Would you like PseudoTV Live to Auto Tune Channels?") == True:
                REAL_SETTINGS.setSetting("Autotune","true")
                REAL_SETTINGS.setSetting("Warning1","true")
                REAL_SETTINGS.setSetting("autoFindNetworks","true")
                REAL_SETTINGS.setSetting("autoFindMovieGenres","true")
                REAL_SETTINGS.setSetting("autoFindRecent","true")
                
                if isPVR() != False:
                    REAL_SETTINGS.setSetting("autoFindLivePVR","true")
                    
                if isHDHR() != False:
                    REAL_SETTINGS.setSetting("autoFindLiveHDHR","true")
                    
                if isUSTVnow() != False:
                    REAL_SETTINGS.setSetting("autoFindUSTVNOW","true")
                    
                if isCompanionInstalled() == True and isLowPower() == False:
                    REAL_SETTINGS.setSetting("autoFindCommunity_PseudoNetworks","true")
                
                setProperty("Verified_Community", 'true')
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
        
        #INFO        
        self.currentPlayInfoBar = self.getControl(5007)
        self.currentPlayInfoBar_MAXwidth = self.currentPlayInfoBar.getWidth()
        self.currentPlayInfoTime = self.getControl(5006)
        self.currentPlayInfoTime_xpos, self.currentPlayInfoTime_ypos = self.currentPlayInfoTime.getPosition()
        
        #MOREINFO        
        self.currentPlayMoreInfoBar = self.getControl(5004)
        self.currentPlayMoreInfoBar_MAXwidth = self.currentPlayMoreInfoBar.getWidth()
        self.currentPlayMoreInfoTime = self.getControl(5005)
        self.currentPlayMoreInfoTime_xpos, self.currentPlayMoreInfoTime_ypos = self.currentPlayMoreInfoTime.getPosition()
   
        # self.OnNowLst = self.getControl(500)
        # self.OnNxtLst = self.getControl(501)

        if REAL_SETTINGS.getSetting('INTRO_PLAYED') != 'true':    
            self.setBackgroundVisible(False)
            self.setMute(False)
            self.Player.play(INTRO)
            time.sleep(17)
            self.setBackgroundVisible(True)
            REAL_SETTINGS.setSetting("INTRO_PLAYED","true")    

        try:
            if self.forceReset == False:
                self.currentChannel = self.fixChannel(int(REAL_SETTINGS.getSetting("CurrentChannel")))
            else:
                raise Exception()
        except Exception,e:
            self.currentChannel = self.fixChannel(1)
            
        self.resetChannelTimes()
        self.lastPlayingChannel = self.currentChannel
        REAL_SETTINGS.setSetting('Normal_Shutdown', "false")
        setProperty("PTVL.VideoWindow","false")  
            
        #start loop timers
        self.cronTimer.start()
        self.SeekTimer.start()
        self.playerTimer.start()
        self.notificationTimer.start()
        
        # start playing video
        if self.DisablePlayback == False:
            self.setChannel(self.fixChannel(self.currentChannel))

        self.idleReset() 
        self.loadReminder()
        self.FEEDtoggle()   
        self.fillChannelGuide()
                
        #Set button labels
        self.getControl(1000).setLabel('Now Watching')
        self.getControl(1001).setLabel('OnNow')
        self.getControl(1002).setLabel('Browse')
        self.getControl(1003).setLabel('Search')
        self.getControl(1004).setLabel('Last Channel')
        self.getControl(1005).setLabel(self.chkChanFavorite())
        self.getControl(1006).setLabel('EPGType')  
        self.getControl(1007).setLabel(self.chkMute())
        self.getControl(1008).setLabel(self.chkSub())
        self.getControl(1009).setLabel('Player Settings')
        self.getControl(1010).setLabel('Sleep')
        self.getControl(1011).setLabel('Exit') 
        
        if self.backgroundUpdating < 2 or self.isMaster == False:
            self.channelThread.name = "ChannelThread"
            if self.channelThread.isAlive() == False:
                self.channelThread.start()
        else:
            self.postBackgroundLoading()
        self.BackgroundProgress.setVisible(False)
        
        if self.DisablePlayback == True:
            self.openEPG()
        
        self.actionSemaphore.release() 
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
        self.showChannelBug = int(REAL_SETTINGS.getSetting("Enable_ChannelBug")) > 0
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

    
    def backupFiles(self):
        self.log('backupFiles')
        if CHANNEL_SHARING == True:
            realloc = REAL_SETTINGS.getSetting('SettingsFolder')
            FileAccess.copy(os.path.join(realloc,'settings2.xml'), os.path.join(SETTINGS_LOC,'settings2.xml'))
            realloc = xbmc.translatePath(os.path.join(realloc, 'cache',''))

            for i in range(CHANNEL_LIMIT):
                FileAccess.copy(os.path.join(realloc,'channel_' + str(i) + '.m3u'), os.path.join(CHANNELS_LOC,'channel_' + str(i) + '.m3u'))


                
    def storeFiles(self):
        self.log('storeFiles')
        if CHANNEL_SHARING == True:
            realloc = REAL_SETTINGS.getSetting('SettingsFolder')
            FileAccess.copy(os.path.join(SETTINGS_LOC,'settings2.xml'), os.path.join(realloc,'settings2.xml'))
            realloc = xbmc.translatePath(os.path.join(realloc,'cache',''))

            for i in range(self.maxChannels):
                if self.channels[i].isValid:
                    FileAccess.copy(os.path.join(CHANNELS_LOC,'channel_' + str(i) + '.m3u'), os.path.join(realloc,'channel_' + str(i) + '.m3u'))

                
    def message(self, data):
        self.log('Dialog message: ' + data)
        okDialog(data, header = 'PseudoTV Live - Announcement')

        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('TVOverlay: ' + msg, level)


    def fillOnNow(self, offdif=0):
        self.log('fillOnNow')
        self.OnNowLst = []
        self.OnNowLstItems = []
        for Channel in range(self.maxChannels):
            if self.channels[Channel].isValid == True:
                chnum = Channel + 1
                chtype = self.getChtype(chnum)
                chname = self.getChname(chnum)
                chlogo = self.getChlogo(chnum)
                
                # getinfo
                position = self.getPlaylistPOS(chtype, chnum, offdif)
                label = self.channels[Channel].getItemTitle(position)
                Description = self.channels[Channel].getItemDescription(position)
                genre = self.channels[Channel].getItemgenre(position)
                LiveID = self.channels[Channel].getItemLiveID(position)
                Duration = self.channels[Channel].getItemDuration(position) 
                timestamp = self.channels[Channel].getItemtimestamp(position) 
                mediapath = self.channels[Channel].getItemFilename(position) 
                mpath = getMpath(mediapath)
                SEtitle = self.channels[Channel].getItemEpisodeTitle(position) 
                season, episode, swtitle = SEinfo(SEtitle, self.showSeasonEpisode)
                
                type, id, dbepid, managed, playcount, rating, hd, cc, stars, year = self.channelList.unpackLiveID(LiveID)
                dbid, epid = splitDBID(dbepid)
                year, title, showtitle = getTitleYear(label, year)
                content_type = type.replace("tvshow","episode").replace("other","video").replace("music","musicvideo")   
                
                isNew = playcount == "0"
                isManaged = managed == "True"
                isHD = hd == "True"
                hasCC = cc == "True"
                Stars = float(stars)
                
                isFav = False
                ChanColor = (self.channelbugcolor).replace('0x','')
                if self.isChanFavorite(chnum):
                    isFav = True
                    ChanColor = 'gold'
                label = ("[COLOR=%s][B]%d|[/B][/COLOR] %s" % (ChanColor, chnum, title))

                # getart                     
                art = self.findArtwork(type, title, year, chtype, chname, id, dbid, mpath, getProperty("OVERLAY.ONNOW_TYPE"))
                poster, fanart = self.getArtwork(type, title, year, chtype, chname, id, dbid, mpath)
                
                # # listitem
                # thumbnail = removeNonAscii(thumbnails.group(1))
                # fanart = removeNonAscii(fanarts.group(1))
                # self.OnNowLstItems = xbmcgui.ListItem(label=name, thumbnailImage = thumbnail)
                # self.OnNowLstItems.setIconImage(thumbnail)
                # self.OnNowLstItems.setProperty("mediapath", path)
                # self.OnNowLstItems.setProperty("Fanart_Image", fanart)
                
                # infoList = {}
                # infoList['mediatype']     = type
                # infoList['mpaa']          = 'Unknown'
                # infoList['tvshowtitle']   =  name
                # infoList['title']         =  name
                # infoList['originaltitle'] = 'originaltitle'
                # infoList['sorttitle']     = 'sorttitle'
                # infoList['studio']        = 'Studio'
                # infoList['genre']         = 'Genre'
                # infoList['plot']          = 'Plot'
                # infoList['tagline']       = 'tagline'
                # infoList['code']          = 'code'
                # infoList['duration']      = 1
                # infoList['year']          = 1977
                # infoList['season']        = 3
                # infoList['episode']       = 4
                # infoList['playcount']     = 5
                # self.OnNowLstItems.setInfo('Video', infoList)    

                # infoArt = {}
                # infoArt['thumb']        = thumbnail
                # infoArt['poster']       = thumbnail
                # infoArt['banner']       = ''
                # infoArt['fanart']       = fanart
                # infoArt['clearart']     = ''
                # infoArt['clearlogo']    = ''
                # infoArt['landscape']    = fanart
                # infoList['icon']        = thumbnail
                # self.OnNowLstItems.setArt(infoArt)
                
                # dict property
                self.OnNowLst.append({'Chtype': chtype, 'Label': label, 'Chnum': chnum, 'Chname': chname, 'Type': type, 'Showtitle': showtitle, 'Cleantitle': title, 'Year': year, 'Title': title, 'SEtitle': SEtitle, 'SWtitle': swtitle,
                'Season': season, 'Episode': episode, 'Description': Description, 'Rating': rating, 'Managed': managed, 'Playcount': playcount, 'Genre': genre, 'content_type': content_type, 'ID': id, 'DBID': dbid, 'EPID': epid,
                'Mpath': mpath, 'Duration': Duration, 'Timestamp': timestamp, 'Mediapath': mediapath, 'Tagline': SEtitle, 'poster': poster, 'fanart': fanart, 'LOGOART': chlogo, 'ONNOW_ART': art})
        return self.OnNowLst 
         
         
    def fillChannelGuide(self):
        self.log('fillChannelGuide')
        self.ChannelGuideLst = []
        for Channel in range(self.maxChannels):
            if self.channels[Channel].isValid == True:
                chType = self.getChtype(Channel+1)
                chTypeLabel = getChanTypeLabel(self.getChtype(Channel+1))
                chNum = Channel+1
                chName = self.getChname(Channel+1)
                chLogo = self.getChlogo(Channel+1)
                label = ('%d| %s' %(chNum, chName))
                self.ChannelGuideLstItems = xbmcgui.ListItem(label)   
                self.ChannelGuideLstItems.setProperty('OVERLAY.ChannelGuide.Chtype',str(chType))
                self.ChannelGuideLstItems.setProperty('OVERLAY.ChannelGuide.ChtypeLabel',chTypeLabel)
                self.ChannelGuideLstItems.setProperty('OVERLAY.ChannelGuide.Chnum',str(chNum))
                self.ChannelGuideLstItems.setProperty('OVERLAY.ChannelGuide.Chname',chName)
                self.ChannelGuideLstItems.setProperty('OVERLAY.ChannelGuide.LOGOART',chLogo)
                self.ChannelGuideLstItems.setProperty('OVERLAY.ChannelGuide.Label',label)
                self.ChannelGuideLst.append({'Chtype': chType, 'ChtypeLabel': chTypeLabel, 'Chnum': chNum, 'Chname': chName, 'LOGOART': chLogo, 'Label': label})
        setProperty("OVERLAY.ChannelGuide", str(self.ChannelGuideLst))

        
    def showOnNow(self):
        self.log("showOnNow")
        if not self.showingMenuAlt:
            if len(self.OnNowLst) > 0:
                curchannel = 0
                self.showingMenuAlt = True
                
                # set Position
                sidex, sidey = self.getControl(132).getPosition()
                sidew = self.getControl(132).getWidth()
                sideh = self.getControl(132).getHeight()
                listWidth = self.getControl(132).getLabel()
                tabHeight = self.getControl(1001).getHeight()
                self.OnNowControlList = xbmcgui.ControlList(sidex, sidey, sidew, sideh, self.myEPG.textfont, self.myEPG.textcolor, MEDIA_LOC + BUTTON_NO_FOCUS, MEDIA_LOC + BUTTON_FOCUS, self.myEPG.focusedcolor, 1, 1, 1, 0, tabHeight, 0, tabHeight/2)
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
                        
                self.setVisible(130,True)
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
        if action == 'Down':
            return self.currentChannel - 1
        elif action == 'Current':
            return self.currentChannel
        elif action == 'Last':
            return self.getLastChannel()
        elif action == 'LastValid':
            return self.lastPlayingChannel
        else:
            return self.currentChannel + 1
        self.log("lastActionTrigger, action = " + action + " ,return")

            
    def setInvalidateChannel(self, channel):
        self.log("setInvalidateChannel, channel = " + str(channel))
        self.channels[channel - 1].isValid = False

                                  
    def InvalidateChannel(self, channel, newChannel=-1):
        self.log("InvalidateChannel, channel = " + str(channel) + ", newChannel = " + str(newChannel))
        if channel < 1 or channel > self.maxChannels:
            self.log("InvalidateChannel invalid channel " + str(channel))
            return
            
        self.setInvalidateChannel(channel)
        self.invalidatedChannelCount += 1
        if self.invalidatedChannelCount > 3:
            self.Error("Exceeded three invalidated channels. Exiting.")
            return

        remaining = 0
        for i in range(self.maxChannels):
            if self.channels[i].isValid:
                remaining += 1
        if remaining == 0:
            self.Error("No channels available. Exiting.")
            return
                
        if newChannel > 0:
            channel = newChannel
        self.setChannel(self.fixChannel(channel))
    

    def getPlaylistPOS(self, chtype, channel, offdif=0):
        self.log('getPlaylistPOS, infoOffset = ' + str(self.infoOffset) + ', offdif = ' + str(offdif))

        if self.OnDemand == True:
            position = -999
            
        # correct position to hideShortItems
        elif chtype <= 7:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + offdif
            curoffset = 0
            modifier = 1
            if self.infoOffset < 0:
                modifier = -1
            
            if self.hideShortItems:
                # HideShort and BCT
                self.log('getPlaylistPOS, hideShortItems + BCT position')
                while curoffset != abs(self.infoOffset):
                    position = self.channels[channel - 1].fixPlaylistIndex(position + modifier)
                    if self.channels[channel - 1].getItemDuration(position) > self.shortItemLength and (self.channels[channel - 1].getItemgenre(position)).lower() not in BCT_TYPES:
                        curoffset += 1
            else:
                # BCT
                self.log('getPlaylistPOS, BCT position')
                while curoffset != abs(self.infoOffset):
                    position = self.channels[channel - 1].fixPlaylistIndex(position + modifier)
                    if (self.channels[channel - 1].getItemgenre(position)).lower() not in BCT_TYPES:
                        curoffset += 1

        elif chtype == 8 and len(self.channels[channel - 1].getItemtimestamp(0)) > 0:
            self.log('getPlaylistPOS, livetv position') 
            self.channels[channel - 1].setShowPosition(0)
            epochBeginDate = datetime_to_epoch(self.channels[channel - 1].getItemtimestamp(0))
            
            # loop till we get to the current show this is done to display the correct show on the info listing for Live TV types
            position = self.channels[channel - 1].playlistPosition
            while epochBeginDate + self.channels[channel - 1].getCurrentDuration() <  time.time():
                epochBeginDate += self.channels[channel - 1].getCurrentDuration()
                self.channels[channel - 1].addShowPosition(1)
            position = self.channels[channel - 1].playlistPosition + self.infoOffset + offdif
        else:
            self.log('getPlaylistPOS, default position') 
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
        
        if channel < 1 or channel > self.maxChannels:
            self.log('setChannel, invalid channel ' + str(channel), xbmc.LOGERROR)
            return

        if self.channels[channel - 1].isValid == False:
            self.log('setChannel, channel not valid ' + str(channel), xbmc.LOGERROR)
            return  

        self.runActions(RULES_ACTION_OVERLAY_SET_CHANNEL, channel, self.channels[channel - 1])

        # check for channel lock
        if self.PinLocked == True:
            if self.PinSentry(channel) == False:
                return
               
        if self.currentChannel != self.getLastChannel():
            self.setLastChannel()
            
        self.idleReset()
        self.hidePOP()
        self.hideInfo()
        self.hideSleep()
        self.hideMenuControl('Menu')
        self.hideMenuControl('MenuAlt')
        self.hideMenuControl('MoreInfo')

        # first of all, save playing state, time, and playlist offset for the currently playing channel
        if self.Player.isPlaybackValid() == True:
            # if channel != self.currentChannel:
            # skip setPause for LiveTV
            if self.getChtype(self.currentChannel) not in IGNORE_SEEKTIME_CHTYPE:
                self.channels[self.currentChannel - 1].setPaused(xbmc.getCondVisibility('Player.Paused'))
                # Automatically pause in serial mode
                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE > 0:
                    self.channels[self.currentChannel - 1].setPaused(True)
            # set resume points
            self.channels[self.currentChannel - 1].setShowTime(self.Player.getPlayerTime())
            self.channels[self.currentChannel - 1].setShowPosition(self.channels[self.currentChannel - 1].playlistPosition)
            self.channels[self.currentChannel - 1].setAccessTime(time.time())

        # about to switch new channel
        self.isChannelChanging = True
        self.currentChannel = channel
        chname = self.getChname(self.currentChannel)
        chtype = self.getChtype(self.currentChannel)
        mediapath = self.channels[self.currentChannel - 1].getItemFilename(self.channels[self.currentChannel - 1].playlistPosition)
        self.log("setChannel, loading file = " + ascii(mediapath))
        
        self.infoOffset = 0
        self.lastActionTime = 0
        self.notPlayingCount = 0
   
        if self.OnDemand == True:
            self.OnDemand = False
                 
        self.Cinema_Mode = False
        if chname == 'PseudoCinema':
            self.Cinema_Mode = True

        self.Player.ignoreNextStop = False         
        # First, check to see if the video stop should be ignored
        if chtype in IGNORE_SEEKTIME_CHTYPE:#mediapath[-4:].lower() != 'strm':
            self.Player.ignoreNextStop = True
            self.log("setChannel, ignoreNextStop")

        if surfing == True and self.channelList.quickflipEnabled == True:  
            if chtype in [15,16] or mediapath[-4:].lower() == 'strm':
                self.log("setChannel, about to quickflip")
                if self.notPlayingAction == 'Up':
                    self.isChannelChanging = False
                    self.channelUp()
                    return
                elif self.notPlayingAction == 'Down':
                    self.isChannelChanging = False
                    self.channelDown()
                    return
                 
        # switch to new channel
        if self.channelThread.isAlive():
            self.channelThread.pause()
            
        setBackgroundLabel(('Loading: %s') % chname)
        setProperty("OVERLAY.LOGOART",self.getChlogo(channel))
        self.setBackgroundVisible(True)
        egTrigger('PseudoTV_Live - Loading: %s' % chname)
        
        # now load the proper channel playlist
        # xbmc.PlayList(xbmc.PLAYLIST_VIDEO).clear()
        xbmc.PlayList(xbmc.PLAYLIST_MUSIC).clear()
        self.log("about to load")  
        
        # Delay Playback
        xbmc.sleep(int(round((self.channelDelay/4))))
        
        self.log("setChannel, loading playlist = " + ascii(self.channels[self.currentChannel - 1].fileName))
        if xbmc.PlayList(xbmc.PLAYLIST_MUSIC).load(self.channels[self.currentChannel - 1].fileName) == False:
            self.log("setChannel, Error loading playlist", xbmc.LOGERROR)
            self.isChannelChanging = False
            self.InvalidateChannel(self.currentChannel)
            return
            
        # Disable auto playlist shuffling if it's on
        if xbmc.getInfoLabel('Playlist.Random').lower() == 'random':
            self.log('setChannel, Random on.  Disabling.')
            xbmc.PlayList(xbmc.PLAYLIST_MUSIC).unshuffle()
        
        # Enable auto playlist repeat
        self.log("setChannel, repeatall enabled")
        xbmc.executebuiltin("PlayerControl(RepeatAll)")
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
                   
        setBackgroundLabel(('Loading: %s') % chname,'Now Playing: %s' %self.channels[self.currentChannel - 1].getItemTitle(self.channels[self.currentChannel - 1].playlistPosition))
        
        # save current subtitle state to restore later
        subSave = bool(int(self.isSubtitle()) + int(REAL_SETTINGS.getSetting("EnableSubtitles") == "true"))
        self.log("setChannel, subSave = " + str(subSave))
        
        # disable subtitles to fix player seek delay
        self.disableSubtitle()
        
        # Delay Playback
        xbmc.sleep(int(round((self.channelDelay/2))))
        
        # Mute the channel before changing
        self.log("setChannel, about to mute")
        self.setMute(True)
        
        # Play Media
        self.isChannelChanging = False
        self.setPlayselected(chtype, mediapath)

        # Delay Playback
        xbmc.sleep(int(round((self.channelDelay/2))))
        self.Player.showSubtitles(subSave)
                
        # set the time offset
        self.channels[self.currentChannel - 1].setAccessTime(curtime)
        
        # set the show offset
        if self.channels[self.currentChannel - 1].isPaused:
            self.channels[self.currentChannel - 1].setPaused(False)
            
            try:
                if chtype not in IGNORE_SEEKTIME_CHTYPE and mediapath not in IGNORE_SEEKTIME_PLUGIN and self.ignoreSeektime == False:
                    self.Player.seekTime(self.channels[self.currentChannel - 1].showTimeOffset)
                else:
                    self.log("setChannel, isPaused Ignoring Seektime")
                    
                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE == 0:
                    self.Player.pause()
                    if self.waitForVideoPaused() == False:
                        return
            except Exception,e:
                self.log('setChannel failed!, Exception during seek on paused channel ' + str(e), xbmc.LOGERROR)
        else:
            if chtype not in IGNORE_SEEKTIME_CHTYPE and mediapath not in IGNORE_SEEKTIME_PLUGIN and self.ignoreSeektime == False:
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
                self.toggleShowStartover(False)
                if self.seektime > startovertime: 
                    self.toggleShowStartover(True)
            else:
                self.log("setChannel, Ignoring Seektime")  
                
        self.lastActionTime = time.time() 
        setProperty("PTVL.INIT_CHANNELSET","true")
        self.runActions(RULES_ACTION_OVERLAY_SET_CHANNEL_END, channel, self.channels[channel - 1])
        
        if self.channelThread.isAlive():
            self.channelThread.unpause()
        
        self.Player.onPlaybackAction()
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

        
    def UPNPcontrol(self, func, label='', file='', seektime=0):
        self.log('UPNPcontrol') 
        if self.enableUPNP == False:
            return
            
        if self.UPNPcontrolTimer.isAlive():
            self.UPNPcontrolTimer.cancel()
        self.UPNPcontrolTimer = threading.Timer(0.1, self.UPNPcontrol_thread, [func, label, file, seektime])
        self.UPNPcontrolTimer.name = "UPNPcontrol"   
        self.UPNPcontrolTimer.start()

                  
    def UPNPcontrol_thread(self, func, label='', file='', seektime=0):
        self.log('UPNPcontrol_thread')
        file = file.replace("\\\\","\\") 
        if func == 'play':
            self.Upnp.SendUPNP(label, file, seektime)
        elif func == 'stop':
            self.Upnp.StopUPNP()
        elif func == 'resume':
            self.Upnp.ResumeUPNP()
        elif func == 'pause':
            self.Upnp.PauseUPNP()
        elif func == 'rwd':
            self.Upnp.RWUPNP()
        elif func == 'fwd':
            self.Upnp.FFUPNP()
        elif func == 'chkplay':
            self.Upnp.chkUPNP(label, file, seektime)

                
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


    def setMediaInfo(self, chtype, chname, chnum, mediapath, position, tmpstr=None):
        self.log('setMediaInfo, pos = ' + str(position))
        mpath = getMpath(mediapath)

        #OnDemand Set Player info, else Playlist
        if position == -999:
            if tmpstr != None:
                duration = 0
                tmpstr = tmpstr.split('//')
                title = tmpstr[0]
                SEtitle = ('[COLOR=%s][B]OnDemand[/B][/COLOR]' % ((self.channelbugcolor).replace('0x','')))
                Description = tmpstr[2]
                genre = tmpstr[3]
                timestamp = tmpstr[4]
                myLiveID = tmpstr[5]
                
                self.getControl(203).setImage('NA.png')
                if self.showChannelBug == True:
                    self.getControl(203).setImage(self.Artdownloader.FindBug('0','OnDemand'))
            else:
                self.getTMPSTR(chtype, chname, chnum, mediapath, position)
                return 
        else:
            duration = (self.channels[self.currentChannel - 1].getItemDuration(position))
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
            self.setProp(label, year, chlogo, chtype, chnum, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, swtitle, playcount, season, episode, timestamp, duration, "OVERLAY.PLAYING")
        self.setProp(label, year, chlogo, chtype, chnum, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, swtitle, playcount, season, episode, timestamp, duration, "OVERLAY")
           
           
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

        # if curlabel == 0 and channel == 0:
            # self.channelLabel.setImage(IMAGES_LOC + 'label_last.png')
            # self.channelLabel.setVisible(True)
        # else:
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

        self.getControl(203).setImage('NA.png')
        if self.showChannelBug == True:
            self.getControl(203).setImage(self.Artdownloader.FindBug(self.getChtype(self.currentChannel), self.getChname(self.currentChannel)))
    
        if self.inputChannel == -1:
            self.infoOffset = 0
            
        self.hideKodiInfo()   
        self.channelLabelTimer = threading.Timer(2.0, self.hideChannelLabel)
        self.channelLabelTimer.name = "channelLabelTimer"
        self.channelLabelTimer.start()

        
    # Called from the timer to hide the channel label.
    def hideChannelLabel(self):
        self.log('hideChannelLabel')
        for i in range(3):
            self.channelLabel[i].setVisible(False)
        inputChannel = self.inputChannel
                         
        if inputChannel == 0:
            inputChannel = self.getLastChannel()
        
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
                self.log("SideBarAction, Browse = " + self.Browse)
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
        # # https://github.com/phil65/script.extendedinfo/blob/master/resources/lib/process.py
        # title = getProperty(("%s.Title")%pType)
        # type = getProperty(("%s.Type")%pType)
        # dbid = getProperty(("%s.DBID")%pType)
        # id = getProperty(("%s.ID")%pType)
        # self.log("getExtendedInfo, action = " + action + ", pType = " + pType + ", type = " + type)
        # self.log("getExtendedInfo, title = " + title + ", dbid = " + dbid + ", id = " + id)
        # if type == 'movie':
            # if dbid != '0' and len(dbid) < 6:
                # xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedinfo,dbid=%s,imdb_id=%s)" % (dbid,id))
            # elif id != '0':
                # xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedinfo,imdb_id=%s)" % (id))
            # else:
                # Unavailable()
        # elif type == 'tvshow':
            # if dbid != '0' and len(dbid) < 6:
                # xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedtvinfo,name=%s,dbid=%s,tvdb_id=%s)" % (title,dbid,id))
            # elif id != '0':
                # xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedtvinfo,name=%s,tvdb_id=%s)" % (title,id))
            # else:
                # Unavailable()
        # elif type == 'youtube':
            # YTtype = (ADDON_SETTINGS.getSetting('Channel_' + getProperty(("%s.Chnum")%pType) + '_2'))
            # YTinfo = ADDON_SETTINGS.getSetting('Channel_' + getProperty(("%s.Chnum")%pType) + '_1')
            # if YTtype in ['1','Channel']:
                # xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=youtubeusersearch,id=%s)" % YTinfo)
            # elif YTtype in ['2','Playlist']:
                # xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=youtubeplaylist,id=%s)" % YTinfo)
            # else:
                # Unavailable()
        Unavailable()
                
      
    def toggleShowStartover(self, state):
        self.log('toggleShowStartover, state = ' + str(state))
        self.showingStartover = state
        self.setVisible(104,state)
        
              
    def hideKodiInfo(self):
        self.log('hideKodiInfo')
        if xbmc.getCondVisibility('Player.ShowInfo'):
            json_query = '{"jsonrpc": "2.0", "method": "Input.Info", "id": 1}'
            self.ignoreInfoAction = True
            self.channelList.sendJSON(json_query)
        return
        

    def hideSleep(self):
        self.log('hideSleep')
        self.setVisible(7000,False)
        
        
    def showSleep(self):
        self.log('showSleep')
        self.playSFX('ACTION_ALERT')
        self.setVisible(7000,True)
        self.setFocus(7001)
        
          
    def hideInfo(self):
        self.log('hideInfo')
        self.infoOffset = 0 
        self.toggleShowStartover(False)
        self.setVisible(102,False)
        self.showingInfo = False
                          
              
    def showInfo(self):
        self.log("showInfo")
        self.showingInfo = True
        if self.infoTimer.isAlive():
            self.infoTimer.cancel()

        self.hidePOP()
        self.hideMenuControl('Menu')
        self.hideMenuControl('MenuAlt')
        self.hideMenuControl('MoreInfo')
        chtype = self.getChtype(self.currentChannel)
        
        if self.OnDemand == True:   
            position = -999
            mediapath = self.Player.getPlayingFile()
            setProperty("OVERLAY.DYNAMIC_LABEL",'ON DEMAND')   
            self.currentPlayInfoBar.setVisible(True)
            self.currentPlayMoreInfoBar.setVisible(True)
            self.currentPlayInfoTime.setVisible(True)
            self.currentPlayMoreInfoTime.setVisible(True)
        elif self.infoOffset > 0: 
            position = self.getPlaylistPOS(chtype, self.currentChannel)
            mediapath = (self.channels[self.currentChannel - 1].getItemFilename(position))
            setProperty("OVERLAY.DYNAMIC_LABEL",'COMING UP')
            self.currentPlayInfoBar.setVisible(False)
            self.currentPlayMoreInfoBar.setVisible(False)  
            self.currentPlayInfoTime.setVisible(False)
            self.currentPlayMoreInfoTime.setVisible(False) 
        elif self.infoOffset < 0:
            position = self.getPlaylistPOS(chtype, self.currentChannel)
            mediapath = (self.channels[self.currentChannel - 1].getItemFilename(position))
            setProperty("OVERLAY.DYNAMIC_LABEL",'ALREADY SEEN') 
            self.currentPlayInfoBar.setVisible(False)
            self.currentPlayMoreInfoBar.setVisible(False)  
            self.currentPlayInfoTime.setVisible(False)
            self.currentPlayMoreInfoTime.setVisible(False) 
        else:
            # position = self.getPlaylistPOS(chtype, self.currentChannel)
            position = self.channels[self.currentChannel - 1].playlistPosition
            mediapath = (self.channels[self.currentChannel - 1].getItemFilename(position))
            setProperty("OVERLAY.DYNAMIC_LABEL",'NOW WATCHING')      
            self.currentPlayInfoBar.setVisible(True)
            self.currentPlayMoreInfoBar.setVisible(True)
            self.currentPlayInfoTime.setVisible(True)
            self.currentPlayMoreInfoTime.setVisible(True)
            
        self.setMediaInfo(chtype, self.getChname(self.currentChannel), self.currentChannel, mediapath, position)     
        
        if self.Player.isPlaybackValid() == True:
            if self.infoOffset == 0:
                if chtype <= 7:
                    self.startTime = time.time() - self.Player.getPlayerTime()
                    self.endTime = (time.time() - self.Player.getPlayerTime()) + self.Player.getPlayerTotalTime()
                elif chtype == 8:    
                    tmpDate = self.channels[self.currentChannel - 1].getItemtimestamp(position)
                    self.startTime = datetime_to_epoch(tmpDate)
                    self.endTime = self.startTime + self.channels[self.currentChannel - 1].getItemDuration(position)
                else:
                    self.startTime = time.time()
                    self.endTime = time.time() + self.channels[self.currentChannel - 1].getItemDuration(position)                    
            else:
                self.startTime = self.endTime
                self.endTime += float(self.channels[self.currentChannel - 1].getItemDuration(position))
            self.setPlayingTime()

        self.setVisible(222,False)
        self.setVisible(102,True)
        self.hideKodiInfo()   
        
        self.infoTimer = threading.Timer(self.InfTimer, self.hideInfo)
        self.infoTimer.name = "InfoTimer"
        if isBackgroundVisible() == False:
            self.infoTimer.start()
        

    def showMenu(self):
        self.log("showMenu")
        #Set button labels
        self.getControl(1005).setLabel(self.chkChanFavorite())
        self.getControl(1007).setLabel(self.chkMute())
        self.getControl(1008).setLabel(self.chkSub())
        if self.showingMenu == False:
            #Set first button focus, show menu
            self.showingMenu = True
            self.setVisible(119,True)
            self.setFocus(1001)
        self.hideMenuControl('Menu')


    def showMoreInfo(self):
        self.log('showMoreInfo') 
        self.showingMoreInfo = True           
        self.getControl(1012).setLabel('More Info')
        self.getControl(1013).setLabel('Find Similar')
        self.getControl(1014).setLabel('Record Show')
        self.getControl(1015).setLabel('Set Reminder')
        
        self.hidePOP()
        self.hideInfo()
        self.setVisible(102,False)
        self.setVisible(222,True)
        self.setFocus(1012)
        self.hideMenuControl('MoreInfo')

            
    def hidePOP(self):
        self.log("hidePOP")   
        self.setVisible(120,False)
        self.setVisible(203,True)    
        xbmc.sleep(10)
        self.DisableOverlay = False
        self.showingPop = False
        
                     
    def showPOP(self):
        self.log("showPOP")
        self.showingPop = True
        if self.popTimer.isAlive():
            self.popTimer.cancel()
            
        # if self.isWindowOpen == False:
        self.setVisible(203,False)
        self.DisableOverlay = True
        self.setVisible(120,True)

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
        if self.showingStartover == True:
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

        # ignore all actions if we're in the middle of processing one
        # if self.isChannelChanging == True:
            # return
            
        # Since onAction isnt always called from the same thread (weird),
        # ignore all actions if we're in the middle of processing one
        if self.actionSemaphore.acquire(False) == False:
            self.log('Unable to get semaphore')
            return
            
        lastaction = time.time() - self.lastActionTime
        # during certain times we just want to discard all input
        if lastaction < 1 and self.showingStartover == False:
            self.log('onAction, Not allowing actions')
            action = ACTION_INVALID
        self.idleReset()

        if action in ACTION_SELECT_ITEM:
            self.log('onAction, ACTION_SELECT_ITEM')
            if not self.showingSleep and not self.showingReminder:
                self.SelectAction()
                
        elif action in ACTION_SHOW_EPG:
            self.log('onAction, ACTION_SHOW_EPG')
            self.openEPG()
            
        elif action in ACTION_NEXT_ITEM:
            self.log('onAction, ACTION_NEXT_ITEM')
            if self.getChtype(self.currentChannel) not in IGNORE_SEEKTIME_CHTYPE and not (self.channels[self.currentChannel - 1].getItemFilename(self.channels[self.currentChannel - 1].playlistPosition)).startswith(STREAM_TYPES):     
                self.SkipNext(True)

        elif action in ACTION_MOVE_UP or action in ACTION_PAGEUP:
            self.log('onAction, ACTION_MOVE_UP')
            if self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer)
            elif not self.showingMoreInfo and not self.showingSleep and not self.showingReminder:
                self.channelUp()
                
        elif action in ACTION_MOVE_DOWN or action in ACTION_PAGEDOWN:
            self.log('onAction, ACTION_MOVE_DOWN')
            if self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer)
            elif not self.showingMoreInfo and not self.showingSleep and not self.showingReminder:
                self.channelDown()

        elif action in ACTION_MOVE_LEFT:   
            self.log("onAction, ACTION_MOVE_LEFT")
            self.toggleShowStartover(False)

            if self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer,True)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer,True)
            elif self.showingInfo:
                self.infoOffset -= 1
                if self.infoOffset < 0:
                    self.infoOffset = 0
                    self.MenuControl('Menu',self.InfTimer)
                elif not self.showingMenu:
                    self.showInfo()
            elif self.showingInfo == False:
                #disable seeking for live/internet tv from non pvr sources.
                if self.getChtype(self.currentChannel) not in IGNORE_SEEKTIME_CHTYPE and not (self.channels[self.currentChannel - 1].getItemFilename(self.channels[self.currentChannel - 1].playlistPosition)).startswith(STREAM_TYPES):
                    self.log("onAction, SmallSkipBackward")
                    if getXBMCVersion() >= 15:
                        xbmc.executebuiltin("Seek("+str(self.seekBackward)+")")
                    else:
                        xbmc.executebuiltin("PlayerControl(SmallSkipBackward)")
                    self.UPNPcontrol('rwd')
                    
        elif action in ACTION_MOVE_RIGHT:
            self.log("onAction, ACTION_MOVE_RIGHT")
            self.toggleShowStartover(False)
                
            if self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer,True)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer,True)
            elif self.showingInfo:
                self.infoOffset += 1
                self.showInfo()
            
            elif self.showingInfo == False:
                #disable seeking for live/internet tv from non pvr sources.
                if self.getChtype(self.currentChannel) not in IGNORE_SEEKTIME_CHTYPE and not (self.channels[self.currentChannel - 1].getItemFilename(self.channels[self.currentChannel - 1].playlistPosition)).startswith(STREAM_TYPES):
                    self.log("onAction, SmallSkipForward")
                    if getXBMCVersion() >= 15:
                        xbmc.executebuiltin("Seek("+str(self.seekForward)+")")
                    else:
                        xbmc.executebuiltin("PlayerControl(SmallSkipForward)")
                    self.UPNPcontrol('fwd')
       
        elif action in ACTION_PREVIOUS_MENU:
            self.log('onAction, ACTION_PREVIOUS_MENU')
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
            self.log('onAction, ACTION_SHOW_INFO')
            if self.ignoreInfoAction:
                self.ignoreInfoAction = False
            else:
                if self.showingInfo:
                    self.hideInfo()
                    self.hideKodiInfo()   
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
                
        elif action == ACTION_MUTE:
            self.log('onAction, ACTION_MUTE')
            self.toggleSubtitles(False)
                 
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
        self.hideSleep()
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
        self.showSleep()

        
    def sleepAction(self):
        self.log("sleepAction")
        self.actionSemaphore.acquire()
        self.hideSleep()
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
            json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"stop"},"id":1}'
            self.channelList.sendJSON(json_query)  
        elif self.sleepTimeMode == 7:
            self.setChannel(self.fixChannel(self.PreferredChannel))

            
    def ReminderCancel(self):
        self.log("ReminderCancel")
        self.hideSleep()  
        xbmc.sleep(10)
        self.showingReminder = False
        
        
    def ReminderPrompt(self):
        self.log("ReminderPrompt")
        self.showingReminder = True    
        setProperty("PTVL.IDLE_LABEL","Are you [I]sure you're[/I]  still watching" + '"' + getProperty('OVERLAY.Title') + '"?\n "' + getProperty('PTVL.Reminder_title') + '" is about to begin on Channel ' + getProperty('PTVL.Reminder_chnum') + '.')
        self.getControl(7001).setLabel('Continue watching')  
        self.getControl(7002).setLabel('Channel Change in (%ds)' % IDLE_DELAY)
        self.IdleTimerCountdown(IDLE_DELAY)
        self.showSleep()
        
        
    def ReminderAction(self):
        self.log("ReminderAction")   
        self.hideSleep() 
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
        while not KODI_MONITOR.abortRequested():
            if self.isExiting == True:
                return
            time.sleep(2)
                
            if self.isChannelChanging == True or self.isWindowOpen() != False:
                self.log("notificationAction, sleep")
                time.sleep(2)
                continue
                
            self.log("notificationAction")
            if self.Player.isPlaybackValid() == True:  
                chtype = self.getChtype(self.currentChannel)
                chname = self.getChname(self.currentChannel)
                self.notificationLastChannel = self.currentChannel
                self.notificationLastShow = self.channels[self.currentChannel - 1].playlistPosition
                self.notificationShowedNotif = False
                
                # Don't show any notification if the current show is < shortItemLength
                if (chtype <= 7 or chtype >= 10) and self.hideShortItems:
                    if self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) < self.shortItemLength:
                        self.notificationShowedNotif = True
                self.log("notificationAction, notificationShowedNotif = " + str(self.notificationShowedNotif)) 
                
                if self.notificationShowedNotif == False:  
                    timedif = self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) - self.Player.getPlayerTime()
                    self.log("notificationAction, timedif = " + str(timedif))
                    
                    # Nextshow Info
                    nextshow_offset = 1
                    nextshow = self.getPlaylistPOS(chtype, self.currentChannel, nextshow_offset)
                    # Don't show any notification if the next show is a BCT
                    while self.channels[self.currentChannel - 1].getItemgenre(nextshow) in BCT_TYPES:
                        nextshow_offset += 1
                        nextshow = self.getPlaylistPOS(chtype, self.currentChannel, nextshow_offset)
                    
                    label = self.channels[self.currentChannel - 1].getItemTitle(nextshow).replace(',', '')
                    SEtitle = self.channels[self.currentChannel - 1].getItemEpisodeTitle(nextshow)         
                    Description = self.channels[self.currentChannel - 1].getItemDescription(nextshow)
                    genre = self.channels[self.currentChannel - 1].getItemgenre(nextshow)
                    LiveID = self.channels[self.currentChannel - 1].getItemLiveID(nextshow)
                    duration = self.channels[self.currentChannel - 1].getItemDuration(nextshow) 
                    timestamp = self.channels[self.currentChannel - 1].getItemtimestamp(nextshow) 
                    mediapath = self.channels[self.currentChannel - 1].getItemFilename(nextshow)  
                    type, id, dbepid, managed, playcount, rating, hd, cc, stars, year = self.channelList.unpackLiveID(LiveID)
                    dbid, epid = splitDBID(dbepid)
                    mpath = getMpath(mediapath)
                    chlogo = self.getChlogo(self.currentChannel)
                    year, title, showtitle = getTitleYear(label, year)
                    season, episode, swtitle = SEinfo(SEtitle, self.showSeasonEpisode) 
                    self.log("notificationAction, Setting Properties")
                    self.setProp(label, year, chlogo, chtype, self.currentChannel, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, swtitle, playcount, season, episode, timestamp, duration, 'OVERLAY.NEXT')

                    # If remaining time with in range, Notification Action.                      
                    if self.showNextItem and (timedif < NOTIFICATION_TIME_BEFORE_END and timedif > NOTIFICATION_DISPLAY_TIME):
                        if self.showingInfo == False and self.showingMoreInfo == False:
                            self.log("notificationAction, showing Coming up next")
                            ComingUpType = int(REAL_SETTINGS.getSetting("EnableComingUp"))
                            
                            # Notification Action
                            if ComingUpType == 3:
                                infoDialog(getProperty("OVERLAY.NEXT.SubTitle"),'Coming Up: '+getProperty("OVERLAY.NEXT.Title"), time=NOTIFICATION_DISPLAY_TIME, icon=getProperty("OVERLAY.LOGOART"))
                            # Info Overlay
                            elif ComingUpType == 1:
                                self.infoOffset = ((nextshow) - self.notificationLastShow)
                                self.showInfo()
                            else:                            
                                # Popup Overlay
                                self.showPOP()  
                            # sleep to prevent repeat notification
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

        
    def SeekTimerAction(self):
        while not KODI_MONITOR.abortRequested():
            if self.isExiting == True:
                return
            time.sleep(1)

            if isLowPower() == True:   
                self.currentPlayInfoBar.setVisible(False)
                self.currentPlayInfoTime.setVisible(False)
                self.currentPlayMoreInfoBar.setVisible(False)
                self.currentPlayMoreInfoTime.setVisible(False)
                return
                
            if self.isChannelChanging == True or self.isWindowOpen() != False:
                self.log("SeekTimerAction, sleep")
                time.sleep(1)
                continue
                
            self.setSeekBarTime()
                    

    def playerTimerAction(self):
        while not KODI_MONITOR.abortRequested():
            newChannel = -1   
            if self.isExiting == True:
                return
            time.sleep(2)
                
            if self.isChannelChanging == True:
                self.log("playerTimerAction, sleep")
                time.sleep(2)
                continue
                                        
            # disable dialog checks while system is taxed (low end hardware).
            if isLowPower() == False:
                if self.CloseDialog(['Dialogue OK']) == True:
                    self.log("playerTimerAction, CloseDialog = True") 
                    self.setChannel(self.fixChannel(self.lastActionTrigger()))
                    return
            try:    
                if self.Player.isSomethingPlaying() == False:
                    self.log("playerTimerAction, isSomethingPlaying = False")     
                    raise Exception() 

                # Reset variables when playback detected
                self.notPlayingCount = 0              
                self.lastPlayTime = self.Player.getPlayerTime()
                self.lastPlayingChannel = self.currentChannel
                self.lastPlaylistPosition = self.channels[self.currentChannel - 1].playlistPosition
                time.sleep(2)
                continue
            except Exception,e:
                self.notPlayingCount += 1

                #open epg when DisablePlayback is enabled.
                if self.DisablePlayback == True:
                    self.log("playerTimerAction, DisablePlayback = True") 
                    if self.notPlayingCount == 3:
                        self.openEPG()
                else:
                    if self.notPlayingCount > 3:
                        setBackgroundLabel(('Loading: %s (%ss)') % (self.getChname(self.currentChannel), str(self.playActionTime - self.notPlayingCount)))
                        self.log("playerTimerAction, notPlayingCount = " + str(self.notPlayingCount))

                        #First tier actions
                        if self.notPlayingCount > self.playActionTime:
                            if self.Player.ignoreNextStop == False:
                                self.log("playerTimerAction, Skipping to Next Program") 
                                setBackgroundLabel("Loading Error: Skipping to Next Program")
                                self.SkipNext()
                                pass
                            elif self.Player.ignoreNextStop == True:
                                self.log("playerTimerAction, Changing Channel")
                                setBackgroundLabel("Loading Error: Changing Channel")
                                newChannel = self.lastActionTrigger()
                            else:
                                self.log("playerTimerAction, Returning to last valid Channel")
                                setBackgroundLabel("Loading Error: Returning to last valid Channel")
                                newChannel = self.lastActionTrigger('LastValid')
                                    
                        if newChannel > 0:
                            if xbmc.getCondVisibility('Window.IsActive(busydialog)') == True and self.Player.isSomethingPlaying() == False:
                                self.ForceStop()
                            self.InvalidateChannel(self.currentChannel, newChannel)
           
           
    def SkipNext(self, noAction=False):
        self.log('SkipNext')
        setBackgroundLabel("Skipping Next")
        if noAction == False:
            xbmc.executebuiltin("PlayerControl(Next)")
        self.channels[self.currentChannel - 1].addShowPosition(1)
                    
     
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
            channel = self.currentChannel
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
                self.setVisible(119,False) 
            else:
                self.showMenu() 
                
        elif type == 'MenuAlt':
            if hide == True:
                self.showingMenuAlt = False                   
                self.setFocus(1001)         
                self.setVisible(130,False)
                self.MenuControl('Menu',self.InfTimer)
                xbmc.sleep(10)
            # else:
                # self.showOnNow()
                
        elif type == 'Info':
            if hide == True:
                self.hideInfo()
            else:
                self.showInfo()
                
        elif type == 'MoreInfo':
            if hide == True:      
                self.showingMoreInfo = False   
                self.setVisible(222,False)  
                self.infoOffset = 0
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
                
       
    def setPlayingTime(self):
        self.log("setPlayingTime")
        try:
            if self.getChtype(self.currentChannel) > 8:
                raise Exception()
        
            if self.clockMode == 0:
                st = datetime.datetime.fromtimestamp(float(self.startTime)).strftime("%I:%M%p").lower()
                et = datetime.datetime.fromtimestamp(float(self.endTime)).strftime("%I:%M%p").lower()
            else:
                st = datetime.datetime.fromtimestamp(float(self.startTime)).strftime("%H:%M")
                et = datetime.datetime.fromtimestamp(float(self.endTime)).strftime("%H:%M")

            setProperty('OVERLAY.Time','%s - %s' % (st, et))
        except Exception,e:
            clearProperty('OVERLAY.Time')
       
       
    # TODO add timebar and button update here         
    def setSeekBarTime(self):
        if self.showingInfo == True or self.showingMoreInfo == True:
            if self.Player.ignoreNextStop == True and self.Player.getPlayerFile().startswith(STREAM_TYPES):
                position = self.channels[self.currentChannel - 1].playlistPosition
                getPlayerTime = float(time.time() - self.startTime)
                getPlayerTotalTime = float(self.channels[self.currentChannel - 1].getItemDuration(position))
            else:
                getPlayerTime = self.Player.getPlayerTime()
                getPlayerTotalTime = self.Player.getPlayerTotalTime()

           # hide bar for content that doesn't produce progress details. Can't use setVisible because notice focus issue.
            if getPlayerTime < getPlayerTotalTime/30 or getPlayerTime > (getPlayerTotalTime/30)*29:            
                self.currentPlayInfoTime.setVisible(False)
                self.currentPlayMoreInfoTime.setVisible(False)
            elif self.infoOffset == 0:
                self.currentPlayInfoTime.setVisible(True)
                self.currentPlayMoreInfoTime.setVisible(True)
            
            if self.infoOffset == 0:
                self.currentPlayInfoBar.setVisible(True)
                self.currentPlayMoreInfoBar.setVisible(True)
                setProperty('OVERLAY.PLAYING.Time', str(datetime.timedelta(seconds=getPlayerTime)).split('.')[0])
                setProperty('OVERLAY.PLAYING.TimeRemaining', str(datetime.timedelta(seconds=(getPlayerTotalTime + getPlayerTime))).split('.')[0])
            
            if self.showingMoreInfo == True:
                try:
                    temp_xpos = self.currentPlayMoreInfoTime_xpos
                    MoreInfoTimeseekButton_ypos = self.currentPlayMoreInfoTime_ypos
                    self.currentPlayMoreInfoTime.setWidth(self.currentPlayMoreInfoTime.getWidth())
                    self.currentPlayMoreInfoTime.setHeight(self.currentPlayMoreInfoTime.getHeight())
                    seekButton_width = int(round(self.currentPlayMoreInfoTime.getWidth() / 2)) #find width of button and place in the middle.
                    seekBar_width = self.currentPlayMoreInfoBar.getWidth()
                    seekBar_xpos, temp_ypos = self.currentPlayMoreInfoBar.getPosition()
                    perPlayed = 100 - (((getPlayerTotalTime - getPlayerTime) / getPlayerTotalTime) * 100)
                    MoreInfoTimeseekButton_xpos = (seekBar_xpos + int(round((perPlayed * self.currentPlayMoreInfoBar_MAXwidth)/100))) - seekButton_width
                    self.currentPlayMoreInfoTime.setPosition(MoreInfoTimeseekButton_xpos, MoreInfoTimeseekButton_ypos)
                    self.currentPlayMoreInfoBar.setWidth(MoreInfoTimeseekButton_xpos - self.currentPlayMoreInfoTime_xpos)           
                except Exception,e:
                    self.log("setSeekBarTime, MoreInfo, failed " + str(e))
                    self.currentPlayMoreInfoBar.setVisible(False)
                    self.currentPlayMoreInfoTime.setVisible(False)
            else:
                try:
                    temp_xpos = self.currentPlayInfoTime_xpos
                    InfoTimeseekButton_ypos = self.currentPlayInfoTime_ypos
                    self.currentPlayInfoTime.setWidth(self.currentPlayInfoTime.getWidth())
                    self.currentPlayInfoTime.setHeight(self.currentPlayInfoTime.getHeight())
                    seekButton_width = int(round(self.currentPlayInfoTime.getWidth() / 2)) #find width of button and place in the middle.
                    seekBar_width = self.currentPlayInfoBar.getWidth()
                    seekBar_xpos, temp_ypos = self.currentPlayInfoBar.getPosition()
                    perPlayed = 100 - (((getPlayerTotalTime - getPlayerTime) / getPlayerTotalTime) * 100)
                    InfoTimeseekButton_xpos = (seekBar_xpos + int(round((perPlayed * self.currentPlayInfoBar_MAXwidth)/100))) - seekButton_width
                    self.currentPlayInfoTime.setPosition(InfoTimeseekButton_xpos, InfoTimeseekButton_ypos)
                    self.currentPlayInfoBar.setWidth(InfoTimeseekButton_xpos - self.currentPlayInfoTime_xpos)
                except Exception,e:
                    self.log("setSeekBarTime, Info, failed " + str(e))
                    self.currentPlayInfoBar.setVisible(False)
                    self.currentPlayInfoTime.setVisible(False)
                    
           # hide bar for content that doesn't produce progress details. Can't use setVisible because notice focus issue.
            if getPlayerTime < getPlayerTotalTime/30 or getPlayerTime > (getPlayerTotalTime/30)*29:            
                self.currentPlayInfoTime.setVisible(False)
                self.currentPlayMoreInfoTime.setVisible(False)


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
     
     
    def setProp(self, title, year, chlogo, chtype, chnum, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, subtitle, playcount, season, episode, timestamp, duration, pType='OVERLAY'):
        self.log("setProp, title = " + title + ', pType = ' + pType)
        try:
            if pType == 'EPG':
                time = 0.25
                if self.setPropTimer.isAlive():
                    self.setPropTimer.cancel()
            else:
                time = 0.1
                if self.setPropTimer.isAlive():
                    self.setPropTimer.join()
            self.setPropTimer = threading.Timer(time, self.setProp_thread, [title, year, chlogo, chtype, chnum, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, subtitle, playcount, season, episode, timestamp, duration, pType])
            self.setPropTimer.name = "setPropTimer"   
            if self.isExiting == False:    
                self.setPropTimer.start()
        except Exception,e:
            self.log('setProp failed! ' + str(e) + traceback.format_exc(),  xbmc.LOGERROR)
            
            
    def setProp_thread(self, title, year, chlogo, chtype, chnum, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, subtitle, playcount, season, episode, timestamp, duration, pType='OVERLAY'):
        self.log("setProp_thread, title = " + title + ', pType = ' + pType)  
        setProperty("%s.Chtype"%pType,str(chtype)) 
        setProperty("%s.Chnum"%pType,str(chnum))
        setProperty("%s.ChtypeLabel"%pType,getChanTypeLabel(self.getChtype(chnum)))
        setProperty("%s.TimeStamp"%pType,str(timestamp))
        setProperty("%s.Duration"%pType,str(duration))
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
        
        year, title, showtitle = getTitleYear(title, year)
        setProperty("%s.Cleantitle"%pType,title)
        setProperty("%s.Showtitle"%pType,showtitle)
        setProperty("%s.Year"%pType,str(year))
        setProperty("%s.ID"%pType,str(id))
        setProperty("%s.Tagline"%pType,subtitle)
        setProperty("%s.LOGOART"%pType,chlogo)

        # fill art properties
        self.fillArtwork(type, title, year, chtype, chname, id, dbid, mpath, pType)
        
        self.isNew(pType)
        self.isManaged(pType)
        # todo rss ticker that matches genre
        # if pType == 'OVERLAY':  
            # getRSSFeed(getProperty("OVERLAY.Genre")) 

  
    def fillArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, pType):
        if pType == 'EPG':
            time = 0.25
            if self.fillArtworkTimer.isAlive():
                self.fillArtworkTimer.cancel()
        else:
            time = 0.1
            if self.fillArtworkTimer.isAlive():
                self.fillArtworkTimer.join()
        self.fillArtworkTimer = threading.Timer(time, self.fillArtwork_thread, [type, title, year, chtype, chname, id, dbid, mpath, pType])
        self.fillArtworkTimer.name = "fillArtworkTimer"   
        if self.isExiting == False:    
            self.fillArtworkTimer.start()
            xbmc.sleep(1)
            
            
    def fillArtwork_thread(self, type, title, year, chtype, chname, id, dbid, mpath, pType):
        if pType == 'EPG':
            artTypes = self.artEPG_Types
        elif pType == 'OVERLAY.PLAYING':
            artTypes = list(set(self.artOVERLAY_Types + ['poster','fanart']))
        else:
            artTypes = self.artOVERLAY_Types
        self.log('fillArtwork_thread, pType = ' + pType + ' artTypes = ' + str(artTypes))
        
        for n in range(len(artTypes)):
            try:
                artType = (artTypes[n]).lower()
                self.setArtwork(type, title, year, chtype, chname, id, dbid, mpath, EXTtype(artType), artType, pType)
            except:
                pass
               
               
    def setArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, typeEXT, artType, pType='OVERLAY'):
        self.log('setArtwork, chtype = ' + str(chtype) + ', id = ' + str(id) +  ', dbid = ' + str(dbid) + ', typeEXT = ' + typeEXT + ', artType = ' + artType + ', pType = ' + str(pType))  
        try:
            clearProperty(("%s.%s" %(pType, artType)))
            setImage = self.findArtwork(type, title, year, chtype, chname, id, dbid, mpath, typeEXT) 
            setProperty(("%s.%s" %(pType, artType)),setImage)
        except Exception,e:
            self.log('setArtwork, failed! ' + str(e))
            
            
    # must be called by threaded function.
    def findArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, typeEXT):
        try:
            setImage = self.Artdownloader.FindArtwork(type, title, year, chtype, chname, id, dbid, mpath, typeEXT)
            self.log('findArtwork, setImage = ' + setImage)
            return uni(setImage)
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

                
    def clearArt(self, pType='OVERLAY'):
        self.log("clearArt, pType = " + str(pType))
        clearProperty("%s.poster"%pType)
        clearProperty("%s.banner"%pType)
        clearProperty("%s.fanart"%pType)
        clearProperty("%s.landscape"%pType)
        clearProperty("%s.clearart"%pType)
        clearProperty("%s.clearlogo"%pType)
        clearProperty("%s.LOGOART"%pType)
                
            
    def clearProp(self, pTypeLST):
        self.log("clearProp, pType = " + str(pTypeLST))
        for pType in pTypeLST:
            clearProperty("%s.Chtype"%pType)
            clearProperty("%s.Chnum"%pType)
            clearProperty("%s.ChtypeLabel"%pType)
            clearProperty("%s.TimeStamp"%pType)
            clearProperty("%s.Duration"%pType)
            clearProperty("%s.Mediapath"%pType)
            clearProperty("%s.Playcount"%pType)
            clearProperty("%s.Title"%pType)
            clearProperty("%s.Mpath"%pType)
            clearProperty("%s.Chname"%pType)
            clearProperty("%s.SEtitle"%pType)
            clearProperty("%s.Type"%pType)
            clearProperty("%s.DBID"%pType)
            clearProperty("%s.EPID"%pType)
            clearProperty("%s.Description"%pType)
            clearProperty("%s.Season"%pType)
            clearProperty("%s.Episode"%pType)
            clearProperty("%s.Genre"%pType)
            clearProperty("%s.Rating"%pType)
            clearProperty("%s.isHD"%pType)
            clearProperty("%s.hasCC"%pType)
            clearProperty("%s.Stars"%pType)
            clearProperty("%s.Cleantitle"%pType)
            clearProperty("%s.Showtitle"%pType)
            clearProperty("%s.Year"%pType)
            clearProperty("%s.ID"%pType)
            clearProperty("%s.Tagline"%pType)
            clearProperty("%s.isNEW"%pType)
            clearProperty("%s.isManaged"%pType)
            clearProperty("%s.Time"%pType)
            clearProperty("%s.Label"%pType)
        
        
    def clearAllProp(self):
        for prop in list(set(ALL_PROPERTIES)):
            clearProperty(prop)
        
        
    def isWindowOpen(self):
        if getProperty("PTVL.EPG_Opened") == "true":
            return 'EPG'
        elif getProperty("PTVL.DVR_Opened") == "true":
            return 'DVR'
        elif getProperty("PTVL.VOD_Opened") == "true":
            return 'VOD'
        elif getProperty("PTVL.APP_Opened") == "true":
            return 'APP'
        else:
            return False
            
        
    def windowSwap(self, window):
        self.log('windowSwap = ' + window)
        # avoid loading open window
        if window.upper() == self.isWindowOpen():
            return
            
        if getProperty("PTVL.EPG_Opened") == "true":
            self.myEPG.closeEPG()
        elif getProperty("PTVL.DVR_Opened") == "true":
            self.myDVR.closeDVR()
        elif getProperty("PTVL.VOD_Opened") == "true":
            self.myVOD.closeVOD()
        elif getProperty("PTVL.APP_Opened") == "true":
            self.myApp.closeAPP()
        # open new window
        if window.upper() == 'EPG':
            self.myEPG.doModal()
        elif window.upper() == 'DVR':
            self.myDVR.show()
        elif window.upper() == 'VOD':
            self.myVOD.show()
        elif window.upper() == 'APP':
            self.myApp.show()
          
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
        chlogo1 = xbmc.translatePath(os.path.join(self.channelLogos,self.getChname(channel) + '.gif'))
        chlogo2 = xbmc.translatePath(os.path.join(self.channelLogos,self.getChname(channel) + '.png'))

        if REAL_SETTINGS.getSetting('Enable_AnimLogo') == "true" and FileAccess.exists(chlogo1):
            return chlogo1
        elif FileAccess.exists(chlogo2):
            return chlogo2
        elif fallback == True:
            return THUMB
        else:
            return 'NA.png'

        
    def postBackgroundLoading(self):
        self.log('postBackgroundLoading')
        setProperty("PTVL.BackgroundLoading","false")

        
    def playStartOver(self):
        self.log('playStartOver')
        self.toggleShowStartover(False)
        self.Player.playselected(self.channels[self.currentChannel - 1].playlistPosition)
            
            
    def playOnNow(self):
        self.MenuControl('MenuAlt',self.InfTimer,True)
        self.MenuControl('Menu',self.InfTimer,True) 
        channel = int(self.channelList.cleanLabels(self.OnNowLst[self.OnNowControlList.getSelectedPosition()].split('|')[0]))
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

           
    def setPlayselected(self, chtype, url):
        self.log('setPlayselected, chtype = ' + str(chtype) + ', url = ' + url)
        try:
            if chtype not in IGNORE_SEEKTIME_CHTYPE or url.startswith(('plugin','pvr')) or url.endswith(('strm')):
                raise Exception()
            else:
                if url.startswith('PlayMedia'): 
                    # url = ('PlayMedia('+url+')')
                    xbmc.executebuiltin(tidy(url).replace(',', ''))
                else:
                    if url.startswith(('rtmp','rtsp')):
                        KOtime = int(self.playActionTime - 2)
                        if 'live=true' not in url:
                            url += ' live=true'
                        if 'timeout=' in url:
                            url = re.sub(r'timeout=\d',"timeout=%s" % KOtime,url) 
                        else:
                            url += ' timeout=%s' % KOtime

                    self.log('setPlayselected, using modified playback')
                    label = self.channels[self.currentChannel - 1].getItemTitle(self.channels[self.currentChannel - 1].playlistPosition)
                    SEtitle = self.channels[self.currentChannel - 1].getItemEpisodeTitle(self.channels[self.currentChannel - 1].playlistPosition)
                    Description = self.channels[self.currentChannel - 1].getItemDescription(self.channels[self.currentChannel - 1].playlistPosition)
                    genre = self.channels[self.currentChannel - 1].getItemgenre(self.channels[self.currentChannel - 1].playlistPosition)
                    LiveID = self.channels[self.currentChannel - 1].getItemLiveID(self.channels[self.currentChannel - 1].playlistPosition)
                    Duration = self.channels[self.currentChannel - 1].getItemDuration(self.channels[self.currentChannel - 1].playlistPosition) 
                    mediapath = self.channels[self.currentChannel - 1].getItemFilename(self.channels[self.currentChannel - 1].playlistPosition) 
                    type, id, dbepid, managed, playcount, rating, hd, cc, stars, year = self.channelList.unpackLiveID(LiveID)                                 
                    year, title, showtitle = getTitleYear(label, year)
                    season, episode, swtitle = SEinfo(SEtitle, self.showSeasonEpisode)
                    dbid, epid = splitDBID(dbepid)
                    mpath = getMpath(mediapath)
                    chname = self.getChname(self.currentChannel)
                    chlogo = self.getChlogo(self.currentChannel)
                    content_type = type.replace("tvshow","episode").replace("other","video").replace("youtube","video").replace("music","musicvideo")     
                    
                    if type in ['tvshow','episode','movie']:
                        poster, fanart = self.getArtwork(type, title, year, chtype, chname, id, dbid, mpath)
                    else:
                        poster = fanart = chlogo
                        
                    listitem = xbmcgui.ListItem(label, path=url)   
                    infoList = {}
                    infoList['mediatype']     = content_type
                    infoList['duration']      = Duration
                    infoList['mpaa']          = rating
                    infoList['tvshowtitle']   = swtitle
                    infoList['title']         = label
                    infoList['studio']        = chname
                    infoList['genre']         = genre
                    infoList['plot']          = Description
                    infoList['code']          = id
                    infoList['year']          = int(year)
                    infoList['season']        = int(season)
                    infoList['episode']       = int(episode)
                    infoList['playcount']     = int(playcount)
                    infoList['rating']        = float(stars)
                    
                    listitem.setInfo('Video', infoList)      
                    infoArt = {}
                    infoArt['thumb']        = poster
                    infoArt['poster']       = poster
                    infoArt['fanart']       = fanart
                    infoList['icon']        = chlogo
                    listitem.setArt(infoArt)
                    
                    # xbmc.PlayList(xbmc.PLAYLIST_MUSIC).clear()
                    # playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                    # playlist.clear()
                    # playlist.add(url, listitem)
                    # playlist.add(self.channelList.youtube_player + FAILED_TUBE)
                    # self.Player.play(playlist, listitem)
                    # self.Player.playselected(playlist)
                    self.Player.play(url, listitem)
        except Exception,e:
            self.log('setPlayselected, using standard playback')
            self.Player.playselected(self.channels[self.currentChannel - 1].playlistPosition)

            
    def isBackgroundVisible(self):
        return xbmc.getCondVisibility('Control.IsVisible(101)')

        
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
        while not KODI_MONITOR.abortRequested():
            if self.isExiting == True:
                return
            time.sleep(1)
            
            if self.isChannelChanging == True:
                self.log("cronJob, sleep")
                time.sleep(2)
                continue
            
            self.cron_uptime += 1
  
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
                setProperty("OVERLAY.OnNowLst", str(self.fillOnNow()))
                setProperty("OVERLAY.OnNextLst", str(self.fillOnNow(1)))
                
            # 10min job
            self.tenMin_Job += 1
            if self.tenMin_Job == 600:
                self.log("cronJob, uptime = " + str(self.cron_uptime/60))
                self.tenMin_Job = 0
                self.UPNPcontrol('chkplay', self.Player.getPlayerTitle(), self.Player.getPlayerFile(), self.Player.getPlayerTime())
                
            # 15min job
            self.fifteenMin_Job += 1
            if self.fifteenMin_Job == 900:
                self.fifteenMin_Job = 0
                self.fillChannelGuide()
                self.FEEDtoggle()
                purgeGarbage()

    
    def PinSentry(self, channel):
        self.log('PinSentry')
        invalidCNT = 0
        while invalidCNT < 3:
            pin = inputDialog("Enter %s's PIN (%s/3)" %(self.getChname(channel),invalidCNT+1), '' , xbmcgui.INPUT_ALPHANUM, xbmcgui.ALPHANUM_HIDE_INPUT)
            if pin == self.PinNumber:
                return True
            else:
                invalidCNT +=1
        self.setInvalidateChannel(channel)
        return False
            
            
    def chkMute(self):
        if self.isMute() == True:
            return 'UnMute'
        else:
            return 'Mute'
            

    def isMute(self):
        json_query = '{"jsonrpc":"2.0","method":"Application.GetProperties","params":{"properties":["muted"]},"id":1}'
        details = self.channelList.sendJSON(json_query)
        state = (re.search('"muted":(.*)',re.compile( "{(.*?)}", re.DOTALL ).findall(details)[0])).group(1) == 'true'
        self.log("isMute = " + str(state))
        return state
        
        
    def toggleMute(self):
        self.log("toggleMute")
        json_query = '{"jsonrpc":"2.0","method":"Application.SetMute","params":{"mute":"toggle"},"id":1}'
        self.channelList.sendJSON(json_query)
    
    
    def setMute(self, state):
        while self.isMute() != bool(state):
            self.log("setMute = " + str(state))
            json_query = '{"jsonrpc":"2.0","method":"Application.SetMute","params":{"mute":%s},"id":1}' %str(state).lower()
            self.channelList.sendJSON(json_query)
            xbmc.sleep(10)
        
        
    def isSubtitle(self):
        return xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled') 
        
        
    def disableSubtitle(self):
        self.log("disableSubtitle")
        if getXBMCVersion() >= 15:
            self.Player.showSubtitles(False)
        else:
            self.Player.disableSubtitles() 

            
    def hasSubtitle(self):
        self.log("hasSubtitle")
        return xbmc.getCondVisibility('VideoPlayer.HasSubtitles') 
         
         
    def chkSub(self):
        if self.isSubtitle() == True:
            return 'Disable Subtitles'
        else:
            if self.hasSubtitle() == True:
                return 'Enable Subtitles'
            else:
                return 'Find Subtitle'
            

    def toggleSubtitles(self, search=True):
        self.log("toggleSubtitles")
        if self.isChannelChanging == True:
            return
            
        SubState = not bool(self.isSubtitle())
        if SubState == True:
            if self.hasSubtitle() == False and search == True:
                xbmc.executebuiltin("ActivateWindow(SubtitleSearch)")
                return 
        self.Player.showSubtitles(SubState)        

        
    def openEPG(self):
        self.log("openEPG")
        if getProperty("PTVL.EPG_Opened") != "true":
            # Pause Background channel building while EPG is opened
            if self.channelThread.isAlive() and self.DisablePlayback == False:
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

    
    def setFocus(self, id, key=False):
        xbmc.sleep(25)
        if key == True:
            while self.isVisible(key) == False:
                xbmc.sleep(10)
        self.setFocusId(id)
            
            
    def isHasFocus(self, key):
        return xbmc.getCondVisibility('Control.HasFocus($s)'%key)


    def isVisible(self, key):
        return xbmc.getCondVisibility('Control.IsVisible($s)'%key)
        
        
    def setVisible(self, key, state):
        try:
            self.getControl(key).setVisible(state)
        except Exception,e:
            self.log('setVisible, failed ' + str(e))
            
            
    def setLabel(self, key, string):
        try:
            self.getControl(key).setLabel(string)
        except Exception,e:
            self.log('setLabel, failed ' + str(e))
            
            
    def showWeather(self):
        self.log("showWeather")
        json_query = '{"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"weather"},"id":1}'
        self.channelList.sendJSON(json_query)


    def end(self, action=False):
        self.log('end')
        egTrigger('PseudoTV_Live - Exiting')
        curtime = time.time()
        self.setLastChannel()
        self.setCurrentChannel() 
        xbmc.executebuiltin("PlayerControl(RepeatOff)")
        setProperty("OVERLAY.LOGOART",THUMB)
        self.BackgroundProgress.setVisible(True)
        self.setBackgroundStatus('Exiting: PseudoTV Live',0)
        self.setMute(False)
        self.setBackgroundVisible(True)
        
        if CHANNEL_SHARING == True and self.isMaster:
            GlobalFileLock.unlockFile('MasterLock')
        GlobalFileLock.close()
                            
        if self.Player.isPlaybackValid() == True:
            self.lastPlayTime = self.Player.getPlayerTime()
            # self.lastPlaylistPosition = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
            self.lastPlaylistPosition = self.channels[self.currentChannel - 1].playlistPosition
            self.UPNPcontrol('stop')
            self.Player.stop()

        # Prevent the player from setting the sleep/thread timers
        self.isExiting = True 
        self.Player.stopped = True
        self.setBackgroundStatus('Exiting: Stopping Timers')
            
        if self.channelLabelTimer.isAlive():
            self.channelLabelTimer.cancel()
                        
        if self.infoTimer.isAlive():
            self.infoTimer.cancel()
            
        if self.popTimer.isAlive():
            self.popTimer.cancel()
                        
        if self.MenuControlTimer.isAlive():
            self.MenuControlTimer.cancel()
                    
        if self.cronTimer.isAlive():
            self.cronTimer.cancel()

        if self.playerTimer.isAlive():
            self.playerTimer.cancel()
            
        if self.SeekTimer.isAlive():
            self.SeekTimer.cancel()

        if self.notificationTimer.isAlive():
            self.notificationTimer.cancel()
                 
        if self.setPropTimer.isAlive():
            self.setPropTimer.cancel()

        if self.fillArtworkTimer.isAlive():
            self.fillArtworkTimer.cancel()
    
        if self.GotoChannelTimer.isAlive():
            self.GotoChannelTimer.cancel()
        
        if self.UPNPcontrolTimer.isAlive():
            self.UPNPcontrolTimer.cancel()

        if self.getTMPSTRTimer.isAlive():
            self.getTMPSTRTimer.cancel()

        if self.ReminderTimer.isAlive():
            self.ReminderTimer.join()
            
        if self.ChangeWatchedTimer.isAlive():
            self.ChangeWatchedTimer.join()
                    
        if self.sleepTimer.isAlive():
            self.sleepTimer.cancel()
            
        if self.SleepTimerCountdownTimer.isAlive():
            self.SleepTimerCountdownTimer.cancel()
            
        if self.idleTimer.isAlive():
            self.idleTimer.cancel()
            
        if self.idleTimerCountdownTimer.isAlive():
            self.idleTimerCountdownTimer.cancel()

        try:
            if FindLogoThread.isAlive():
                FindLogoThread.cancel()
        except:
            pass
        try:     
            if UpdateRSSthread.isAlive():
                UpdateRSSthread.cancel()
        except:
            pass
        try:  
            if download_silentThread.isAlive():
                download_silentThread.cancel()
        except:
            pass
        try: 
            if egTriggerTimer.isAlive():
                egTriggerTimer.cancel()
        except:
            pass
            
        if self.channelThread.isAlive():
            for i in range(30):
                try:
                    self.setBackgroundStatus('Exiting: Stopping Channel Threads')
                    self.channelThread.join(1.0)
                except:
                    pass

                if self.channelThread.isAlive() == False:
                    break

            if self.channelThread.isAlive():
                self.log("Problem joining channel thread", xbmc.LOGERROR)

        if self.isMaster:
            ADDON_SETTINGS.setSetting('LastExitTime', str(int(curtime)))

        if self.timeStarted > 0 and self.isMaster:
            validcount = 0

            for i in range(self.maxChannels):
                self.setBackgroundStatus('Exiting: Saving Settings.')  
                if self.channels[i].isValid:
                    validcount += 1
            
            if validcount > 0:
                for i in range(self.maxChannels):   
                    self.setBackgroundStatus('Exiting: Saving Settings..')               
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

        REAL_SETTINGS.setSetting('Normal_Shutdown', "true")
        self.setBackgroundStatus('Exiting: Shutting Down',100)  
        setProperty("PseudoTVRunning", "False")
        clearProperty('SkinHelperShutdownRequested')
        self.clearProp(['OVERLAY','OVERLAY.PLAYING','OVERLAY.NEXT','OVERLAY.ONDEMAND','EPG','OVERLAY.ChannelGuide'])
        self.UPNPcontrol('stop')
        FileAccess.finish()
        
        if action == 'Restart':
            xbmc.executebuiltin('XBMC.AlarmClock( Restarting PseudoTV Live, XBMC.RunScript(' + ADDON_PATH + '/default.py),0.5,true)')
        elif action == 'Quit':
            xbmc.executebuiltin('XBMC.AlarmClock( Quiting Kodi, XBMC.Quit(),0.5,true)')
        elif action == 'Powerdown':
            xbmc.executebuiltin('XBMC.AlarmClock( Powering Down Device, XBMC.Powerdown(),0.5,true)')
        self.clearAllProp()
        self.close()

       
    def setBackgroundStatus(self, string1, progress=None, inc=0.5, string2=None, string3=None):
        if progress:
            self.progressPercentage = progress
        else:
            self.progressPercentage += inc
        if self.isBackgroundVisible() == True and self.isChannelChanging == False:
            setBackgroundLabel(string1,string2,string3)
            setBackgroundProgress(self.progressPercentage)
            self.ProgressUpdate(self.progressPercentage,self.BackgroundProgress)
      
      
   # Adapted from twinther's tvguide * https://github.com/twinther/script.tvguide/blob/master/gui.py#L763
    def ProgressUpdate(self, percentageComplete, control):
        self.log('ProgressUpdate, percentageComplete = ' + str(percentageComplete))
        if percentageComplete >= 100:
            self.progressPercentage = 0

        if percentageComplete < 1:
            if control:
                control.setPercent(1) 
            self.progressStartTime = datetime.datetime.now()
            self.progressPreviousPercentage = percentageComplete
        elif percentageComplete != self.progressPreviousPercentage:
            if control:
                control.setPercent(percentageComplete)
            self.progressPreviousPercentage = percentageComplete
            delta = datetime.datetime.now() - self.progressStartTime
            
            if percentageComplete < 20:
                setBackgroundLabel(string3="Calculating remaining time...")
            else:
                secondsLeft = int(delta.seconds) / float(percentageComplete) * (100.0 - percentageComplete)
                if secondsLeft > 30:
                    secondsLeft -= secondsLeft % 10
                    setBackgroundLabel(string3="Approximately %d seconds left..."% secondsLeft)
            
 #todo check streaming feed kodi player total runtime if greater than parsed runtime use it... helps catch preroll and commercials. 
# xbmc.executebuiltin('StartAndroidActivity("com.netflix.mediaclient"),return')
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"videoosd"},"id":5}
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"osdaudiosettings"},"id":17}
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"osdvideosettings"},"id":16}