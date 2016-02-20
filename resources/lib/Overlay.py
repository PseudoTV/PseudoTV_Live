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

sys.setrecursionlimit(10000)

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
            title = 'NA'
        return title
        
    
    def isActuallyPlaying(self, time=500):
        ActuallyPlaying = False
        if self.overlay.isExiting == True or self.isPlaybackPaused() == True:
            return True
        if self.getPlayerFile().startswith('upnp'):
            return True

        if self.isPlaybackValid() == True:
            start_time = self.getPlayerTime()
            start_title = self.getPlayerTitle()
            xbmc.sleep(time)
            sample_time = self.getPlayerTime()
            sample_title = self.getPlayerTitle()
            if start_title == sample_title:
                if sample_time > start_time:
                    ActuallyPlaying = True
            self.log('isActuallyPlaying = ' + str(ActuallyPlaying))
        return ActuallyPlaying
            
  
    def isPlaybackValid(self):
        if self.overlay.isExiting == True:
            return True
        if self.getPlayerFile().startswith('upnp'):
            return True

        PlaybackStatus = False
        xbmc.sleep(10)
        if self.isPlaying():
            PlaybackStatus = True
        self.log('isPlaybackValid, PlaybackStatus = ' + str(PlaybackStatus))
        return PlaybackStatus
    
    
    def isPlaybackPaused(self):
        Paused = bool(xbmc.getCondVisibility("Player.Paused"))
        self.log('isPlaybackPaused = ' + str(Paused))
        return Paused

    
    def resumePlayback(self):
        self.log('resumePlayback')
        xbmc.sleep(10)
        if self.isPlaybackPaused():
            self.pause()

    
    def onPlayBackPaused(self):
        self.log('onPlayBackPaused')
        self.overlay.Paused()

        
    def onPlayBackResumed(self):
        self.log('onPlayBackResumed')
        self.overlay.Resume()
    
    
    def onPlaybackAction(self):
        self.overlay.waitForVideoPlayback(250)
        xbmc.sleep(10)
        self.overlay.setBackgroundVisible(False)
        self.overlay.showChannelLabel(self.overlay.currentChannel)
        if self.overlay.infoOnChange == True:
            self.overlay.showInfo(self.overlay.InfTimer)
        else:
            self.overlay.setShowInfo()
    
    
    def onPlayBackStarted(self):
        self.log('onPlayBackStarted')
        setProperty('PTVL.PLAYER_LOG',self.getPlayerFile())
        if self.isPlaybackValid() == True:
            # devise a way to detect ondemand playback todo
            # if len(getProperty("OVERLAY.Title")) > 0:
                # if (getProperty("OVERLAY.Title")).lower() != (self.getPlayerTitle()).lower():
                    # print 'ondemand'
                    # self.overlay.OnDemand = True  
                    # self.overlay.setShowInfo()
                    # self.overlay.showInfo(self.overlay.InfTimer)
                    
            if self.overlay.infoOnStart == True:
                self.overlay.showInfo(self.overlay.InfTimer)
            else:
                self.overlay.setShowInfo()

            if self.overlay.UPNP:
                self.overlay.UPNPcontrol('play', self.getPlayerFile(), self.getPlayerTime())
        
            # if playback starts paused, resume automatically.
            self.resumePlayback()

            # Close epg after start
            if getProperty("PTVL.VideoWindow") == "true" and self.overlay.isWindowOpen() != False:
                self.overlay.windowSwap(self.overlay.isWindowOpen())
                                
            
    def onDemandEnded(self):
        self.log('onDemandEnded') 
        #Force next playlist item after impromptu ondemand playback
        if self.overlay.OnDemand == True:
            self.overlay.OnDemand = False  
            xbmc.executebuiltin("PlayerControl(SmallSkipForward)")
            
            
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        self.onDemandEnded()
        self.overlay.setWatchedStatus()
        clearTraktScrob()
        
            
    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        if self.stopped == False:
            self.log('Playback stopped')
            self.onDemandEnded()
            clearTraktScrob()

            # if self.ignoreNextStop == False:
                # if self.overlay.sleepTimeValue == 0:
                    # self.overlay.sleepTimeValue = 1
                    # self.overlay.startSleepTimer()
                # self.stopped = True
            # else:
                # self.ignoreNextStop = False
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
        self.OnNowLst = []  
        self.OnNextLst = [] 
        self.OnNowArtLst = [] 
        self.OnNextArtLst = [] 
        self.ReminderLst = []
        self.lastActionTime = 0  
        self.actionSemaphore = threading.BoundedSemaphore()
        self.channelThread = ChannelListThread()
        self.channelThread.myOverlay = self 
        self.timeStarted = 0   
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
        self.FailedPlayingCount = 0 
        self.ignoreInfoAction = False
        self.shortItemLength = 120
        self.runningActionChannel = 0
        self.channelDelay = 0
        self.cron_uptime = 0
        self.channelbugcolor = CHANBUG_COLOR
        self.TraktScrob = REAL_SETTINGS.getSetting("TraktScrob") == "true"
        self.showSeasonEpisode = REAL_SETTINGS.getSetting("ShowSeEp") == "true"
        self.InfTimer = INFOBAR_TIMER[int(REAL_SETTINGS.getSetting('InfoTimer'))]
        self.Artdownloader = Artdownloader()
        self.notPlayingAction = 'Up'
        self.ActionTimeInt = float(REAL_SETTINGS.getSetting("ActionTimeInt"))
        self.PlayTimeoutInt = float(REAL_SETTINGS.getSetting("PlayTimeoutInt"))
        self.Browse = ''
        self.MUTE = REAL_SETTINGS.getSetting('enable_mute') == "true"
        self.quickflipEnabled = REAL_SETTINGS.getSetting('Enable_quickflip') == "true"
        self.OnDemand = False 
        self.FavChanLst = (REAL_SETTINGS.getSetting("FavChanLst")).split(',')
        self.DirectInput = REAL_SETTINGS.getSetting("DirectInput") == "true"
        self.SubState = REAL_SETTINGS.getSetting("EnableSubtitles") == "true"
        setProperty("PTVL.BackgroundLoading","true") 
                             
        try:
            self.ResetLST = eval(REAL_SETTINGS.getSetting("ResetLST"))
        except:
            self.ResetLST = []
        self.log('Channel Reset List is ' + str(self.ResetLST))
    
        try:
            self.BYPASSLST = ",".join(appendPlugin(eval(REAL_SETTINGS.getSetting("BYPASS_LST")) + PLUGIN_SEEK))
        except:
            self.BYPASSLST = ",".join(appendPlugin(PLUGIN_SEEK))
        self.log('Seek enabled Plugins is ' + self.BYPASSLST)

        if REAL_SETTINGS.getSetting("UPNP1") == "true" or REAL_SETTINGS.getSetting("UPNP2") == "true" or REAL_SETTINGS.getSetting("UPNP3") == "true":
            self.UPNP = True
        else:
            self.UPNP = False
            
        for i in range(3):
            try:
                self.channelLabel.append(xbmcgui.ControlImage(50 + (50 * i), 50, 50, 50, IMAGES_LOC + 'solid.png', colorDiffuse = self.channelbugcolor))
                self.addControl(self.channelLabel[i])
                self.channelLabel[i].setVisible(False)
            except:
                pass
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
        self.ustv = ustvnow.ustvnow()
        self.Upnp = Upnp()   
        dlg = xbmcgui.Dialog()
        self.background = self.getControl(101)
        setBackgroundLabel('Please Wait')
        self.getControl(119).setVisible(False)
        self.getControl(120).setVisible(False)
        self.getControl(102).setVisible(False)
        self.getControl(104).setVisible(False)
        self.getControl(222).setVisible(False)
        self.getControl(130).setVisible(False)
        setProperty("OVERLAY.LOGOART",THUMB) 
        setProperty("PTVL.INIT_CHANNELSET","false")
        self.setBackgroundVisible(True)
            
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

        if self.UPNP == True:
            setBackgroundLabel('Initializing: Video Mirroring')
            self.UPNPcontrol('stop')
            xbmc.sleep(10)
            
        updateDialog = xbmcgui.DialogProgressBG()
        updateDialog.create("PseudoTV Live", "Initializing")
        setBackgroundLabel('Initializing: Channel Configurations')
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
        setBackgroundLabel('Initializing: Channels')
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
                REAL_SETTINGS.setSetting('AT_LIMIT', "0")
                REAL_SETTINGS.setSetting('MEDIA_LIMIT', "0")
                REAL_SETTINGS.setSetting("autoFindLivePVR","true")
                REAL_SETTINGS.setSetting("autoFindNetworks","true")
                REAL_SETTINGS.setSetting("autoFindMovieGenres","true")
                REAL_SETTINGS.setSetting("autoFindRecent","true")
                
                if isUSTVnow() == True:
                    REAL_SETTINGS.setSetting("autoFindUSTVNOW","true")
                
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
            self.startSleepTimer()
            
        self.artOVERLAY_Types = list(set([getProperty("OVERLAY.type1"),getProperty("OVERLAY.type2"),getProperty("OVERLAY.type3"),getProperty("OVERLAY.type4")]))
        self.artEPG_Types = list(set([getProperty("EPG.type1"),getProperty("EPG.type2"),getProperty("EPG.type3"),getProperty("EPG.type4")]))


        if self.forceReset == False:
            self.currentChannel = self.fixChannel(int(REAL_SETTINGS.getSetting("CurrentChannel")))
        else:
            self.currentChannel = self.fixChannel(1)
        
        self.lastPlayingChannel = self.currentChannel
        self.resetChannelTimes()
        self.egTrigger('PseudoTV_Live - Starting')  
        
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
        
        self.startPlayerTimer()
        self.startNotificationTimer()
        self.setChannel(self.fixChannel(self.currentChannel))
        self.actionSemaphore.release()
        self.loadReminder()
        self.FEEDtoggle()
        self.startOnNowTimer()
        REAL_SETTINGS.setSetting('Normal_Shutdown', "false")
        setProperty("PTVL.VideoWindow","true")
                
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
        dlg = xbmcgui.Dialog()
        dlg.ok('PseudoTV Live Announcement:', data)
        del dlg


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('TVOverlay: ' + msg, level)

                
    def setOnNowArt(self):
        self.log('setOnNowArt')
        try:    
            pos = self.OnNowControlList.getSelectedPosition()
            setProperty("OVERLAY.ONNOW_ART",self.OnNowArtLst[pos])
        except Exception,e:
            self.log('setOnNowArt, Failed!, ' + str(e))

        
    def getOnNow(self, offdif=0):
        self.log('getOnNow')
        ChannelGuideLst = []
        OnNowDict = []
        OnNowLst = []
        OnNowArtLst = []
        
        if self.channelThread.isAlive():
            self.channelThread.pause()
            
        if getProperty("PTVL.ONNOW_RUNNING") != "true":
            setProperty("PTVL.ONNOW_RUNNING","true")
            try:
                for Channel in range(self.maxChannels):
                    if self.channels[Channel].isValid:
                        chnum = Channel + 1
                        chtype = self.getChtype(chnum)
                        chname = self.getChname(chnum)
                        chlogo = self.getChlogo(chnum)

                        if self.channels[Channel].isValid:
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
                self.log('getOnNow, Failed!, ' + str(e))
                
        if self.channelThread.isAlive():
            self.channelThread.unpause()
            
        setProperty("PTVL.ONNOW_RUNNING","false") 
        return OnNowLst, OnNowArtLst, OnNowDict
    
                 
    def setOnNow(self):
        self.log('setOnNow')
        self.startOnNowTimer()
        self.OnNowLst, self.OnNowArtLst, OnNowDict = self.getOnNow()
        setProperty("OVERLAY.OnNowLst", str(OnNowDict))
        self.setOnNext()
        
        
    def setOnNext(self):
        self.log('setOnNext')
        self.OnNextLst, self.OnNextArtLst, OnNextDict = self.getOnNow(1)
        setProperty("OVERLAY.OnNextLst", str(OnNextDict))

        
    def clearOnNow(self):
        self.log('clearOnNow')
        clearProperty("OVERLAY.OnNowLst")
        clearProperty("OVERLAY.OnNextLst")
        clearProperty("OVERLAY.ChannelGuide")

            
    def startOnNowTimer(self, timer=ONNOW_REFRESH):
        self.log("startOnNowTimer")
        if len(self.OnNowLst) < self.maxChannels:
            timer = int(round(timer / 2))
        self.startOnNowThread_Timer = threading.Timer(float(TimeRemainder(timer)), self.setOnNow)
        self.startOnNowThread_Timer.name = "startOnNowThread_Timer"
        if self.startOnNowThread_Timer.isAlive():
            self.startOnNowThread_Timer.cancel()
            self.startOnNowThread_Timer.join()
        if isLowPower() == False and self.Player.stopped == False and self.isExiting == False:
            self.startOnNowThread_Timer.start()        
            
            
    def showOnNow(self):
        self.log("showOnNow")
        if not self.showingMenuAlt:
            try:
                if self.MenuControlTimer.isAlive():
                    self.MenuControlTimer.cancel()
                    self.MenuControlTimer.join()
            except:
                pass
            self.MenuControlTimer = threading.Timer(self.InfTimer, self.MenuControl,['MenuAlt',self.InfTimer,True])           
            self.MenuControlTimer.name = "MenuControlTimer"  
                    
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
                xbmc.sleep(100)
                self.OnNowControlList.setVisible(True)
                self.setFocus(self.OnNowControlList)
                self.setOnNowArt()
            elif isLowPower() == True:      
                Unavailable()
            else:      
                TryAgain()
            self.MenuControlTimer.start()

            
    def channelUp(self):
        self.log('channelUp')
        self.notPlayingAction = 'Up'
        if self.maxChannels == 1:
            return           
        self.setChannel(self.fixChannel(self.currentChannel + 1))
        self.log('channelUp return')
        
        
    def channelDown(self):
        self.log('channelDown')
        self.notPlayingAction = 'Down'     
        if self.maxChannels == 1:
            return
        self.setChannel(self.fixChannel(self.currentChannel - 1, False))    
        self.log('channelDown return')  
            

    def lastActionTrigger(self):
        self.log("lastActionTrigger = " + self.notPlayingAction)
        if self.notPlayingAction == 'Down':
            setBackgroundLabel("Changing Channel Down")
            self.setChannel(self.fixChannel(self.currentChannel - 1, False))
        elif self.notPlayingAction == 'Current':
            setBackgroundLabel("Reloading Channel")
            self.setChannel(self.fixChannel(self.currentChannel))
        elif self.notPlayingAction == 'Last':
            setBackgroundLabel("Returning to Previous Channel")
            self.setChannel(self.fixChannel(self.getLastChannel()))
        elif self.notPlayingAction == 'LastValid':
            setBackgroundLabel("Returning to Previous Channel")
            self.setChannel(self.fixChannel(self.lastPlayingChannel))
        else:
            setBackgroundLabel("Changing Channel Up")
            self.setChannel(self.fixChannel(self.currentChannel + 1, True))
        return
      
      
    def setInvalidateChannel(self, channel=None):
        if not channel:
            channel = self.currentChannel
        self.channels[channel - 1].isValid = False
                    
                    
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
        
        infoOffset = self.infoOffset
        if infoOffset == 0 and offdif > 0:
            infoOffset += offdif


        if self.OnDemand == True:
            position = -999
        elif chtype <= 7 and self.hideShortItems and self.infoOffset != 0:
            position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + offdif
            curoffset = 0
            modifier = 1
            if self.infoOffset < 0:
                modifier = -1

            while curoffset != abs(self.infoOffset):
                position = self.channels[channel - 1].fixPlaylistIndex(position + modifier)
                if self.channels[channel - 1].getItemDuration(position) >= self.shortItemLength:
                    curoffset += 1
        else:
            if chtype == 8 and len(self.channels[channel - 1].getItemtimestamp(0)) > 0:
                self.channels[channel - 1].setShowPosition(0)
                tmpDate = self.channels[channel - 1].getItemtimestamp(0) 
                epochBeginDate = datetime_to_epoch(tmpDate)
                position = self.channels[channel - 1].playlistPosition
                #beginDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
                #loop till we get to the current show this is done to display the correct show on the info listing for Live TV types
                
                while epochBeginDate + self.channels[channel - 1].getCurrentDuration() <  time.time():
                    epochBeginDate += self.channels[channel - 1].getCurrentDuration()
                    self.channels[channel - 1].addShowPosition(1)
                position = self.channels[channel - 1].playlistPosition
                position += self.infoOffset + offdif
            else: #original code   
                position = self.channels[channel - 1].playlistPosition + self.infoOffset + offdif
                # position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition() + self.infoOffset + offdif
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
    def setChannel(self, channel):
        self.log('setChannel, channel = ' + str(channel))  
        if self.OnDemand == True:
            self.OnDemand = False

        if channel < 1 or channel > self.maxChannels:
            self.log('setChannel, invalid channel ' + str(channel), xbmc.LOGERROR)
            return
        elif self.channels[channel - 1].isValid == False:
            self.log('setChannel, channel not valid ' + str(channel), xbmc.LOGERROR)
            return  
        elif channel == -1:
            self.log('setChannel, null channel');
            return

        chname = self.getChname(channel)
        chtype = self.getChtype(channel)
            
        # quickflip prep
        mediapath = self.channels[channel - 1].getItemFilename(self.channels[channel - 1].playlistPosition)
        if self.quickflipEnabled == True and self.maxChannels > 1:
            if mediapath[-4:].lower() == 'strm' or chtype == 15:
                self.log("setChannel, about to quickflip");
                setBackgroundLabel(('Quickflip: %s') % chname)
                self.lastActionTrigger()
                return 
                
        if self.currentChannel != self.getLastChannel():
            self.setLastChannel()
          
        if chname == 'PseudoCinema':
            self.Cinema_Mode = True
        else:
            self.Cinema_Mode = False

        self.setBackgroundVisible(True)
        self.notPlayingCount = 0
        timedif = 0
        self.seektime = 0
        self.infoOffset = 0
        self.lastActionTime = 0
        self.runActions(RULES_ACTION_OVERLAY_SET_CHANNEL, channel, self.channels[channel - 1])
        
        # first of all, save playing state, time, and playlist offset for the currently playing channel
        if self.Player.isPlaying():
            chtype_old = self.getChtype(self.currentChannel)
            
            # skip setPause for LiveTV
            if chtype_old not in [8,9] and channel != self.currentChannel:
                self.channels[self.currentChannel - 1].setPaused(xbmc.getCondVisibility('Player.Paused'))
                # Automatically pause in serial mode
                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE > 0:
                    self.channels[self.currentChannel - 1].setPaused(True)
                self.channels[self.currentChannel - 1].setShowTime(self.Player.getTime())
                self.channels[self.currentChannel - 1].setShowPosition(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition())
                self.channels[self.currentChannel - 1].setAccessTime(time.time())
            else:
                self.channels[self.currentChannel - 1].setPaused(False)
                    
        self.getControl(102).setVisible(False)
        self.getControl(104).setVisible(False)
        self.getControl(119).setVisible(False)
        self.getControl(130).setVisible(False)
        self.getControl(222).setVisible(False)
        self.currentChannel = channel      
        setBackgroundLabel(('Loading: %s') % chname)
        self.clearProp()             
        # now load the proper channel playlist
        xbmc.PlayList(xbmc.PLAYLIST_MUSIC).clear()
        xbmc.sleep(10)
        
        setProperty("OVERLAY.LOGOART",self.getChlogo(channel))
        curtime = time.time()

        if self.channels[self.currentChannel - 1].isPaused == False:
            # adjust the show and time offsets to properly position inside the playlist
            #for Live TV get the first item in playlist convert to epoch time  add duration until we get to the current item
            if chtype == 8 and len(self.channels[self.currentChannel - 1].getItemtimestamp(0)) > 0:
                self.channels[self.currentChannel - 1].setShowPosition(0)
                tmpDate = self.channels[self.currentChannel - 1].getItemtimestamp(0)
                epochBeginDate = datetime_to_epoch(tmpDate)
                #beginDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
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
                           
        # First, check to see if the video stop should be ignored
        if chtype > 7 or mediapath[-4:].lower() == 'strm':
            self.Player.ignoreNextStop = True
            self.log("setChannel, ignoreNextStop")

        self.log("setChannel, loading playlist = " + ascii(self.channels[channel - 1].fileName));
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
        
        # Delay Playback
        xbmc.sleep(self.channelDelay) 
        
        # Mute the channel before changing
        if self.MUTE:
            self.log("setChannel, about to mute");
            self.setMute('true');
                    
        
        # Play Online Media (ie. fill-in meta)
        if mediapath.startswith(('http','pvr','rtmp','rtsp','hdhomerun','upnp','ustvnow')):
            self.setPlayselected(mediapath)
        # Play Local Media (ie. Has meta)
        else:
            # disable subtitles to fix player seek delay
            self.Player.disableSubtitles()
            self.Player.playselected(self.channels[self.currentChannel - 1].playlistPosition)
        self.Player.showSubtitles(REAL_SETTINGS.getSetting("EnableSubtitles") == "true")
        self.log("setChannel, playing file = " + ascii(mediapath));
        
        # set the time offset
        self.channels[self.currentChannel - 1].setAccessTime(curtime)
        
        # set the show offset
        if self.channels[self.currentChannel - 1].isPaused:
            self.channels[self.currentChannel - 1].setPaused(False)
            
            try:
                if chtype not in IGNORE_SEEKTIME:
                    self.Player.seekTime(self.channels[self.currentChannel - 1].showTimeOffset)
                if self.channels[self.currentChannel - 1].mode & MODE_ALWAYSPAUSE == 0:
                    self.Player.pause()
                    if self.waitForVideoPaused() == False:
                        if self.MUTE:
                            self.setMute('false');
                        return
            except:
                self.log('setChannel, Exception during seek on paused channel', xbmc.LOGERROR)
        else:       
            if chtype not in IGNORE_SEEKTIME:
                self.log("setChannel, about to seeking")
                seektime1 = self.channels[self.currentChannel - 1].showTimeOffset + timedif + int((time.time() - curtime))
                seektime2 = self.channels[self.currentChannel - 1].showTimeOffset + timedif
                startovertime = float((int(self.channels[self.currentChannel - 1].getItemDuration(self.channels[self.currentChannel - 1].playlistPosition))/10)*int(REAL_SETTINGS.getSetting("StartOverTime")))
                
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
                if self.seektime > startovertime: 
                    self.toggleShowStartover(True)
                else:
                    self.toggleShowStartover(False)
        
        self.Player.onPlaybackAction()
        if self.UPNP:
            self.UPNPcontrol('play', mediapath, self.seektime)
        
        # Unmute
        if self.MUTE:
            self.log("setChannel, Finished, unmuting");
            self.setMute('false');
            
        self.lastActionTime = time.time()
        self.egTrigger('PseudoTV_Live - Loading: %s' % chname)
        self.runActions(RULES_ACTION_OVERLAY_SET_CHANNEL_END, channel, self.channels[channel - 1])
        setProperty("PTVL.INIT_CHANNELSET","true")
        self.log('setChannel, setChannel return')

        
    def SmartSeek(self, mediapath, seektime1, seektime2, overtime):
        self.log("SmartSeek")
        seektime = 0
        # if mediapath.startswith((self.BYPASSLST)):
            # return seektime
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

        
    def UPNPcontrol(self, func, file='', seektime=0):
        self.log('UPNPcontrol') 
        self.UPNPcontrolTimer = threading.Timer(float(REAL_SETTINGS.getSetting("UPNP_OFFSET")), self.UPNPcontrol_thread, [func, file, seektime])
        self.UPNPcontrolTimer.name = "UPNPcontrol"   
        if self.UPNPcontrolTimer.isAlive():
            self.UPNPcontrolTimer.cancel()
        self.UPNPcontrolTimer.start()


    def UPNPcontrol_thread(self, func, file='', seektime=0):
        self.log('UPNPcontrol_thread') 
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
              

    def waitForVideoPlayback(self, time=250, act=True):
        self.log("waitForVideoPlayback")
        if act == False:
            while not (self.Player.isPlaying()):
                xbmc.sleep(10)
        else:
            while self.Player.isActuallyPlaying(time) == False:
                xbmc.sleep(10)
        return
              
              
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
        position = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
        chtype = self.getChtype(self.currentChannel)


        if self.OnDemand == True:
            self.toggleShowStartover(False)  
            self.getControl(5007).setVisible(False)   
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
            # setProperty('PTVL.TitleCHK',uni(self.Player.getPlayerTitle()))
        
        if self.OnDemand == True:
            position == -999
            mediapath = self.Player.getPlayingFile()
        else:
            position = self.getPlaylistPOS(chtype, self.currentChannel)
            mediapath = (self.channels[self.currentChannel - 1].getItemFilename(position))
        
        chname = self.getChname(self.currentChannel)
        if position >= 0:
            self.SetMediaInfo(chtype, chname, self.currentChannel, mediapath, position)
        
        
    def SetMediaInfo(self, chtype, chname, chnum, mediapath, position, tmpstr=None):
        self.log('SetMediaInfo, pos = ' + str(position))
        # self.clearProp()
        mpath = getMpath(mediapath)
                
        #setCore props
        setProperty("OVERLAY.Chtype",str(chtype))
        setProperty("OVERLAY.Mediapath",mediapath)
        setProperty("OVERLAY.Mpath",mpath)  
        setProperty("OVERLAY.Chname",chname)
        setProperty("OVERLAY.Chnum",str(chnum))
        
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
        
        season, episode, swtitle = SEinfo(SEtitle, self.showSeasonEpisode)
        type, id, dbepid, managed, playcount, rating, hd, cc, stars, year = self.channelList.unpackLiveID(myLiveID)
        dbid, epid = splitDBID(dbepid)
        year, title, showtitle = getTitleYear(label, year)
        
        # SetProperties
        setProperty("OVERLAY.TimeStamp",timestamp)
        self.setProp(label, year, chtype, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, swtitle, playcount, season, episode, "OVERLAY")
             

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
        # self.SetMediaInfo(chtype, chname, chnum, mediapath, position)
             
                         
    def startChannelLabelTimer(self, timer=2.5):
        self.log('startChannelLabelTimer')
        self.channelLabelTimer = threading.Timer(timer, self.hideChannelLabel)
        self.channelLabelTimer.name = "ChannelLabel"
        if self.channelLabelTimer.isAlive():
            self.channelLabelTimer.cancel()
        self.channelLabelTimer.start()
            
            
    # Display the current channel based on self.currentChannel.
    # Start the timer to hide it.
    def showChannelLabel(self, channel):
        self.log('showChannelLabel ' + str(channel))
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
        
        # if xbmc.getCondVisibility('Player.ShowInfo'):
            # json_query = '{"jsonrpc": "2.0", "method": "Input.Info", "id": 1}'
            # self.ignoreInfoAction = True
            # self.channelList.sendJSON(json_query);
            
        self.startChannelLabelTimer()
        self.log('showChannelLabel return')

        
    # Called from the timer to hide the channel label.
    def hideChannelLabel(self):
        self.log('hideChannelLabel')       
        for i in range(3):
            self.channelLabel[i].setVisible(False)

        if self.DirectInput == True:
            inputChannel = self.inputChannel
            if not inputChannel in [-1, self.currentChannel]:
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
        elif type == 'Search':
            self.showingBrowse = True
            self.MenuControl('Menu',self.InfTimer,True)
            xbmc.executebuiltin("XBMC.RunScript(script.skin.helper.service,action=videosearch)")
            # xbmc.executebuiltin("VideoLibrary.Search")
            # xbmc.executebuiltin("XBMC.RunScript(script.globalsearch)")
            
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
                if action == 'MoreInfo':
                    try:
                        season = int(getProperty(("%s.Season")%pType))
                        episode = int(getProperty(("%s.Episode")%pType))
                        xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedepisodeinfo,tvshow=%s,dbid=%s,season=%s,episode=%s)" % (title,dbid,season,episode))
                    except:
                        xbmc.executebuiltin("XBMC.RunScript(script.extendedinfo,info=extendedtvinfo,name=%s,dbid=%s,tvdb_id=%s)" % (title,dbid,id))
                else:
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
        xbmc.sleep(100)

                
    def hideInfo(self):
        self.log('hideInfo')
        self.showingInfo = False 
        self.getControl(102).setVisible(False)
        self.infoOffset = 0 
        self.toggleShowStartover(False)
                          
              
    def showInfo(self, timer):
        self.log("showInfo")
        try:
            #Kill thread so infoOffset can increment 
            try:
                if self.infoTimer.isAlive():
                    self.infoTimer.cancel()
            except:
                pass
            self.infoTimer = threading.Timer(timer, self.hideInfo)
            self.infoTimer.name = "InfoTimer"
            self.setShowInfo()
            self.hidePOP()
            self.getControl(222).setVisible(False)
            self.getControl(102).setVisible(True)
            self.showingInfo = True

            if xbmc.getCondVisibility('Player.ShowInfo'):
                json_query = '{"jsonrpc": "2.0", "method": "Input.Info", "id": 1}'
                self.ignoreInfoAction = True
                self.channelList.sendJSON(json_query);
            self.infoTimer.start()
        except:
            pass




    def showMenu(self):
        self.log("showMenu")
        try:
            if self.MenuControlTimer.isAlive():
                self.MenuControlTimer.cancel()
                self.MenuControlTimer.join()
        except:
            pass
        self.MenuControlTimer = threading.Timer(self.InfTimer, self.MenuControl,['Menu',self.InfTimer,True])           
        self.MenuControlTimer.name = "MenuControlTimer"  
        #Set button labels
        self.getControl(1005).setLabel(self.chkChanFavorite())
        self.getControl(1008).setLabel(self.chkSub())
        if self.showingMenu == False:    
            #Set first button focus, show menu
            self.showingMenu = True
            self.getControl(119).setVisible(True)
            xbmc.sleep(100) 
            self.setFocusId(1001) 
        self.MenuControlTimer.start() 

        
    def ShowMoreInfo(self):
        self.log('ShowMoreInfo')            
        self.MenuControlTimer = threading.Timer(self.InfTimer, self.MenuControl,['MoreInfo',self.InfTimer,True])           
        self.MenuControlTimer.name = "MenuControlTimer"  
        if self.MenuControlTimer.isAlive():
            self.MenuControlTimer.cancel()
            
        self.getControl(1012).setLabel('More Info')
        self.getControl(1013).setLabel('Find Similar')
        self.getControl(1014).setLabel('Record Show')
        self.getControl(1015).setLabel('Set Reminder')
        
        if not self.showingMoreInfo:
            self.hideInfo()
            self.showingMoreInfo = True   
            self.getControl(222).setVisible(True) 
            self.getControl(102).setVisible(False) 
            xbmc.sleep(100) 
            self.setFocusId(1012)
        self.MenuControlTimer.start() 

            
    def hidePOP(self):
        self.log("hidePOP")           
        self.getControl(120).setVisible(False)
        self.getControl(203).setVisible(True)
        xbmc.sleep(100)
        self.DisableOverlay = False
        self.showingPop = False
        
                     
    def showPOP(self, timer):
        self.log("showPOP")
        if isBackgroundVisible() == False:
            self.popTimer = threading.Timer(timer, self.hidePOP)
            self.popTimer.name = "popTimer"
            if self.popTimer.isAlive():
                self.popTimer.cancel()
            # if self.isWindowOpen == False:
            self.getControl(203).setVisible(False)
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
            infoDialog(SMSG)
            
            
    def IdleTimer(self):
        if REAL_SETTINGS.getSetting("Idle_Screensaver") == "true":   
            xbmcIdle = xbmc.getGlobalIdleTime()
            PausedPlayback = self.Player.isPlaybackPaused()
            ActivePlayback = self.Player.isPlaybackValid()
            EPGopened = self.isWindowOpen() != False
            IDLEopened = getProperty("PTVL.Idle_Opened") == "true"
            if xbmcIdle >= IDLE_TIMER:
                if IDLEopened == False and (EPGopened == True or PausedPlayback == True):
                    self.log("IdleTimer, Starting Idle ScreenSaver")                      
                    xbmc.executebuiltin('XBMC.RunScript(' + ADDON_PATH + '/resources/lib/idle.py)')
                # elif IDLEopened == False and (ActivePlayback == True and PausedPlayback == True):
                    # self.log("IdleTimer, Starting Idle ScreenSaver")                      
                    # xbmc.executebuiltin('XBMC.RunScript(' + ADDON_PATH + '/resources/lib/idle.py)')
                # if IDLEopened == True and PausedPlayback == False and ActivePlayback == True:
                    # self.log("IdleTimer, Closing Idle ScreenSaver")      
                    # xbmc.executebuiltin("action(leftclick)")
            self.log("IdleTimer, IDLEopened = " + str(IDLEopened) + ", XBMCidle = " + str(xbmcIdle) + ", IDLE_TIMER = " + str(IDLE_TIMER) + ', PausedPlayback = ' + str(PausedPlayback) + ', EPGopened = ' + str(EPGopened) + ', ActivePlayback = ' + str(ActivePlayback))
          
          
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
                xbmc.executebuiltin("Mute()");
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
        # elif controlId in ACTION_SHOW_EPG:
            # self.openEPG()         
        # elif controlId in ACTION_TOUCH_LONGPRESS:
            # self.openEPG()
        self.actionSemaphore.release()
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

        if action in ACTION_SELECT_ITEM:
            self.SelectAction()
                
        elif action in ACTION_MOVE_UP or action in ACTION_PAGEUP:
            if self.showingMenuAlt:
                self.setOnNowArt()
                self.MenuControl('MenuAlt',self.InfTimer)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer)
            elif not self.showingMoreInfo:
                self.channelUp()
                
        elif action in ACTION_MOVE_DOWN or action in ACTION_PAGEDOWN:
            if self.showingMenuAlt:
                self.setOnNowArt()
                self.MenuControl('MenuAlt',self.InfTimer)
            elif self.showingMoreInfo:
                self.MenuControl('MoreInfo',self.InfTimer)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer)
            elif not self.showingMoreInfo:
                self.channelDown()

        elif action in ACTION_MOVE_LEFT:   
            self.log("onAction, ACTION_MOVE_LEFT")
            if self.showingStartover:
                self.toggleShowStartover(False)
            if self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer,True)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer,True)
            elif self.showingInfo:
                self.infoOffset -= 1
                self.showInfo(self.InfTimer)
                if self.infoOffset < 0:
                    self.infoOffset = 0
                    self.setShowInfo()
                    self.MenuControl('Menu',self.InfTimer)
                elif not self.showingMenu:
                    self.showInfo(self.InfTimer)
            elif self.showingInfo == False and not int(getProperty("OVERLAY.Chtype")) in [8,9] and not getProperty("OVERLAY.Mediapath").startswith(("rtmp", "rtsp", "PlayMedia")):
                self.log("onAction, SmallSkipBackward")
                if getXBMCVersion() >= 15:
                    xbmc.executebuiltin("Seek("+str(self.seekBackward)+")")
                else:
                    xbmc.executebuiltin("PlayerControl(SmallSkipBackward)")
                self.UPNPcontrol('rwd')
                    
        elif action in ACTION_MOVE_RIGHT:
            self.log("onAction, ACTION_MOVE_RIGHT")
            if self.showingStartover:
                self.toggleShowStartover(False)
            if self.showingMenuAlt:
                self.MenuControl('MenuAlt',self.InfTimer,True)
            elif self.showingMenu:
                self.MenuControl('Menu',self.InfTimer,True)
            elif self.showingInfo:
                self.infoOffset += 1
                self.showInfo(self.InfTimer)
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
                dlg = xbmcgui.Dialog()

                if dlg.yesno("Exit?", "Are you sure you want to exit PseudoTV Live?"):
                    self.end()
                    return  # Don't release the semaphore         
                del dlg
        
        elif action in ACTION_SHOW_INFO:   
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
            self.setRecord()
        
        elif action == ACTION_SHIFT: #Last channel button
            self.log('onAction, ACTION_SHIFT')
            self.setChannel(self.fixChannel(self.getLastChannel()))

        elif action == ACTION_SYMBOLS:
            self.log('onAction, ACTION_SYMBOLS')
            self.setChannel(self.fixChannel(self.Jump2Favorite()))
            
        elif action == ACTION_CURSOR_LEFT:
            self.log('onAction, ACTION_CURSOR_LEFT')
            
        elif action == ACTION_CURSOR_RIGHT:
            self.log('onAction, ACTION_CURSOR_RIGHT')

        elif action in ACTION_CONTEXT_MENU:
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
            self.SleepTimerCountdownTimer.start()
            
            
    # Reset the sleep timer
    def startSleepTimer(self):
        self.SleepTimerCountdown(self.sleepTimeValue/60)
        self.sleepTimer = threading.Timer(self.sleepTimeValue, self.sleepAction)
        self.sleepTimer.name = "SleepTimer"
        if self.sleepTimer.isAlive():
            self.sleepTimer.cancel()
        if self.sleepTimeValue == 0:
            return
        else:
            if self.Player.stopped == False and self.isExiting == False:
                self.sleepTimer.start()
    
    
    def startNotificationTimer(self, timertime = NOTIFICATION_CHECK_TIME):
        self.log("startNotificationTimer")
        self.notificationTimer = threading.Timer(timertime, self.notificationAction)
        self.notificationTimer.name = "NotificationTimer"
        if self.notificationTimer.isAlive():
            self.notificationTimer.cancel()
        if self.Player.stopped == False and self.isExiting == False:
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
            self.end('Quit')
        elif self.sleepTimeMode == 2:
            xbmc.executebuiltin( "XBMC.AlarmClock(shutdowntimer,XBMC.Suspend(),%d,false)" % ( 5.0, ) )
        elif self.sleepTimeMode == 3:
            self.end('Powerdown')
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

        
    # def TitleCHK(self, title):
        # if title == getProperty('PTVL.TitleCHK'):
            # self.OnDemand = False
        # else:
            # self.OnDemand = True
        # self.log("TitleCHK, OnDemand = " + str(self.OnDemand))
        
        

    def notificationAction(self):
        self.log("notificationAction")
        docheck = False
        chtype = self.getChtype(self.currentChannel)
        chname = self.getChname(self.currentChannel)
        
        if self.showNextItem == False:
            return
        try:
            if self.Player.isPlaying():   
                # self.setSeekBarTime()    
                self.triggercount += 1
                if self.triggercount == int(round((ONNOW_REFRESH/NOTIFICATION_CHECK_TIME))):
                    self.triggercount = 0
                    self.setShowInfo()
                    purgeGarbage()
                    GA_Request()
                    if self.TraktScrob == True:
                        setTraktScrob
                        

                self.notificationLastChannel = self.currentChannel
                # self.notificationLastShow = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
                self.notificationLastShow = self.channels[self.currentChannel - 1].playlistPosition
                self.notificationShowedNotif = False
                
                if chtype <= 7 and self.hideShortItems:
                    # Don't show any notification if the current show is < shortItemLength
                    if self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) < self.shortItemLength:
                        self.notificationShowedNotif = True
                elif chtype >= 10 and self.hideShortItems:
                    # Don't show any notification if the current show is < BYPASS_EPG_SECONDS
                    if self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) < BYPASS_EPG_SECONDS:
                        self.notificationShowedNotif = True
                self.log("notificationAction, notificationShowedNotif = " + str(self.notificationShowedNotif)) 
                
                if self.notificationShowedNotif == False:  
                    timedif = self.channels[self.currentChannel - 1].getItemDuration(self.notificationLastShow) - self.Player.getTime()
                    self.log("notificationAction, timedif = " + str(timedif))
                    
                    # Nextshow Info
                    self.clearProp('OVERLAY.NEXT')
                    nextshow = self.getPlaylistPOS(chtype, self.currentChannel, 1)
                    ComingUpType = int(REAL_SETTINGS.getSetting("EnableComingUp"))
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
                    year, title, showtitle = getTitleYear(label, year)
                    season, episode, swtitle = SEinfo(SEtitle, self.showSeasonEpisode) 
                    self.log("notificationAction, Setting Properties")
                    self.setProp(label, year, chtype, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, swtitle, playcount, season, episode, 'OVERLAY.NEXT')

                    if timedif < NOTIFICATION_TIME_BEFORE_END and timedif > NOTIFICATION_DISPLAY_TIME:
                        self.log("notificationAction, showComingUp")

























                        if self.showingInfo == False and self.notificationShowedNotif == False:
                            self.notificationShowedNotif = True
                            # Notification
                            if ComingUpType == 3:
                                infoDialog(getProperty("OVERLAY.NEXT.SubTitle"),'Coming Up: '+getProperty("OVERLAY.NEXT.Title"), time=NOTIFICATION_DISPLAY_TIME, icon=getProperty("OVERLAY.LOGOART"))
                            # Popup Overlay
                            elif ComingUpType == 2:
                                self.showPOP(self.InfTimer + 2.5)  
                            # Info Overlay
                            elif ComingUpType == 1:
                                self.infoOffset = ((nextshow) - self.notificationLastShow)
                                self.showInfo(self.InfTimer)
                        xbmc.sleep(NOTIFICATION_TIME_BEFORE_END*1000)
        except:
            pass
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
        self.log("CloseDialog, type = " + str(type) + ", currentwindow = " + curwindow)
        if curwindow in type:
            self.setBackgroundVisible(True)
            json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"select"},"id":1}'
            self.channelList.sendJSON(json_query);   
            DebugNotify("Dialogue Closed")
            return True
        return False

        
    def ForceStop(self):
        curwindow = self.currentWindow()
        self.log("ForceStop, currentwindow = " + curwindow)
        # "Working" Busy dialogue doesn't report a label.
        if curwindow == "":
            if self.Player.ignoreNextStop == True:
                self.log("PlayerTimedOut, Playback Failed: STOPPING!")         
                json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"back"},"id":1}'
                self.channelList.sendJSON(json_query);       
                xbmc.sleep(10)
                json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"close"},"id":1}'
                self.channelList.sendJSON(json_query);  
                xbmc.sleep(10)  
                json_query = '{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"stop"},"id":1}'
                self.channelList.sendJSON(json_query);         
                DebugNotify("Playback Failed, STOPPING!") 
                return True
        return False
        

    def startPlayerTimer(self, timer=10.0):
        self.log("startPlayerTimer")
        self.playerTimer = threading.Timer(timer, self.playerTimerAction)
        self.playerTimer.name = "PlayerTimer"
        if self.playerTimer.isAlive():
            self.playerTimer.cancel()
        self.playerTimer.start()
        

    def playerTimerAction(self):
        self.log("playerTimerAction")
        if self.isExiting == False:           
            # check screensaver idle
            self.IdleTimer()     
            chtype = self.getChtype(self.currentChannel)
            
            # Resume playback for live streams, except pvr backend which has timeshift buffer.
            if chtype in [8,9] and not getProperty("OVERLAY.Mediapath").startswith('pvr://'):
                self.Player.resumePlayback()

            try:
                if isLowPower() == False:
                    if self.Player.isActuallyPlaying() == False:
                        raise Exception()
                else:
                    if self.Player.isPlaybackValid() == False:
                        raise Exception()
                        
                # self.TitleCHK(uni(self.Player.getPlayerTitle()))
                self.lastPlayTime = self.Player.getPlayerTime()
                self.lastPlaylistPosition = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()
                self.lastPlayingChannel = self.currentChannel
                self.notPlayingCount = 0  
                self.FailedPlayingCount = 0   
            except Exception,e:
                self.notPlayingCount += 1
                if self.notPlayingCount > int(round((self.PlayTimeoutInt/int(self.ActionTimeInt))))/2:
                    DebugNotify("notPlayingCount = " + str(self.notPlayingCount) + "/" + str(int(round((self.PlayTimeoutInt/int(self.ActionTimeInt))))))

            self.startPlayerTimer(self.ActionTimeInt)
            
            # disable dialog checks while system is taxed or on low end hardware
            if isLowPower() == False:
                if self.CloseDialog(['Dialogue OK']) == True:
                    self.lastActionTrigger() 
                    return
                    
            # if self.FailedPlayingCount == 3:     
                # self.notPlayingAction = 'LastValid'
                # self.lastActionTrigger()
                # return
                
            # If channel fails, wait, reload. If not playing, force close dialogs and kill failed playback. 
            # if self.notPlayingCount == int(round((self.PlayTimeoutInt/int(self.ActionTimeInt)))/2):
                # if self.Player.isActuallyPlaying() == False:
                    # self.setChannel(self.fixChannel(self.currentChannel))
            if self.notPlayingCount == int(round((self.PlayTimeoutInt/int(self.ActionTimeInt)))): 
                if self.Player.isActuallyPlaying() == False:
                    self.FailedPlayingCount += 1
                    if chtype > 7: 
                        self.channels[self.currentChannel - 1].isValid = False
                    self.CloseDialog()
                    # if self.CloseDialog() == False:
                        # self.ForceStop()
                    self.lastActionTrigger() 
     
                
    def SkipNext(self):
        self.log('SkipNext')
        try:
            Autoskip = getProperty("PTVL.Autoplay") == 'true'
            if Autoskip == True:
                return
            else:
                raise Exception()
        except Exception,e:
            xbmc.executebuiltin("PlayerControl(Next)")
                    
     
    def Paused(self, action=False):
        self.log('Paused')
        self.setBackgroundVisible(True)
        setBackgroundLabel('Paused')   
        if action and self.Player.isPlaying():
            json_query = ('{"jsonrpc":"2.0","method":"Player.PlayPause","params":{"playerid":1}, "id": 1}')
            self.channelList.sendJSON(json_query)
        self.UPNPcontrol('pause')
    
    
    def Resume(self, action=False):
        self.log('Resume')
        self.setBackgroundVisible(False)
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
            if not dlg.yesno("PseudoTV Live", 'Would you like to remove the reminder for [B]%s[/B] on channel [B]%s[/B] at [B]%s[/B] ?'%(title,chnum,str(Notify_Time))):
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

        if REAL_SETTINGS.getSetting("AutoJump") == "true":
            if handle_wait(REMINDER_COUNTDOWN,"Show Reminder",'[B]%s[/B] on channel [B]%s[/B] at [B]%s[/B] ?'%(title,chnum,str(Notify_Time))) == True:
                if self.currentChannel != int(chnum):
                    self.setChannel(self.fixChannel(int(chnum)))
        else:
            for i in range(REMINDER_COUNTDOWN):
                if i == 0:
                    alert = ALERT_SFX
                else:
                    alert = ''
                chlogo = self.getChlogo(channel)
                infoDialog("on channel " + str(channel) + " starts in " + str(15-i) +"sec",title, sound=alert, icon=chlogo)
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
                    if dlg.yesno("PseudoTV Live", "Would you like to set a reminder for [B]%s[/B] on channel [B]%s[/B] at [B]%s[/B] ?"%(title,chnum,str(Notify_Time))):
                        auto = True
            if auto == True:
                now = time.time()
                reminder_time = round(((epochBeginDate - now) - REMINDER_COUNTDOWN) / 60)#In minutes
                reminder_Threadtime = float(int(reminder_time)*60)#In seconds
                if reminder_Threadtime > 0:
                    self.log('setReminder, setting =' + str(reminder_dict))
                    self.ReminderTimer = threading.Timer(reminder_Threadtime, self.showReminder, [reminder_dict])
                    self.ReminderTimer.name = "ReminderTimer"
                    if self.ReminderTimer.isAlive():
                        self.ReminderTimer.cancel()
                        self.ReminderTimer.join()
                    infoDialog("Reminder Set for " + str(Notify_Time), icon=chlogo)
                    self.saveReminder(reminder_dict)
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
        self.getTMPSTRTimer = threading.Timer(0.1, self.getTMPSTR_Thread, [chtype, chname, chnum, mediapath, position])
        self.getTMPSTRTimer.name = "getTMPSTRTimer"               
        if self.getTMPSTRTimer.isAlive():
            self.getTMPSTRTimer.cancel()
            self.getTMPSTRTimer.join()
        self.getTMPSTRTimer.start()  
        
        
    def getTMPSTR_Thread(self, chtype, chname, chnum, mediapath, position):
        self.log('getTMPSTR_Thread') 
        tmpstr = self.channelList.getItem(self.channelList.requestItem(mediapath))
        setProperty("OVERLAY.OnDemand_tmpstr",str(tmpstr))
        self.SetMediaInfo(chtype, chname, chnum, mediapath, position, tmpstr)

        
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
                    self.OnNowControlList.setVisible(False)   
                    self.getControl(130).setVisible(False)
                    self.MenuControl('Menu',self.InfTimer)
                    xbmc.sleep(100)
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
                
                
    # def setSeekBarTime(self):
        # self.log("setSeekBarTime")
        # self.getControl(517).setLabel(str(self.Player.getPlayerTime()))
        # seekbar_width = self.getControl(5007).getWidth()
        # seekbar_xpos, seekbar_ypos = self.getControl(5007).getPosition()
        # remaining = int(xbmc.getInfoLabel("Player.TimeRemaining(ss)"))
        # duration = self.channels[self.currentChannel - 1].getItemDuration(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition())
        # print seekbar_width, seekbar_xpos, seekbar_ypos, remaining, duration
        # seekTime_ypos = ((duration/remaining) / seekbar_width) + seekbar_ypos
        # self.getControl(516).setPosition(seekbar_xpos, seekTime_ypos)
        # print seekTime_ypos
        # TODO add timebar and button update here
          
          
    def FEEDtoggle(self):
        self.log("FEEDtoggle")
        UpdateRSS() 
        self.FEEDtoggleTimer = threading.Timer(float(RSS_REFRESH), self.FEEDtoggle)
        self.FEEDtoggleTimer.name = "FEEDtoggleTimer"      

        if getProperty("PTVL.FEEDtoggle") == "true":
            setProperty("PTVL.FEEDtoggle","false")
        else:
            setProperty("PTVL.FEEDtoggle","true")
        self.FEEDtoggleTimer.start()
     

    def egTrigger_Thread(self, message, sender):
        self.log("egTrigger_Thread")
        json_query = ('{"jsonrpc": "2.0", "method": "JSONRPC.NotifyAll", "params": {"sender":"%s","message":"%s"}, "id": 1}' % (sender, message))
        self.channelList.sendJSON(json_query)
        
        
    def egTrigger(self, message, sender='PTVL'):
        self.log("egTrigger")
        self.egTriggerTimer = threading.Timer(0.5, self.egTrigger_Thread, [message, sender])
        self.egTriggerTimer.name = "egTriggerTimer"       
        if self.egTriggerTimer.isAlive():
            self.egTriggerTimer.cancel()
            self.egTriggerTimer.join()
        self.egTriggerTimer.start()
        
            
    def playSFX(self, action):
        self.log("playSFX")
        if REAL_SETTINGS.getSetting("SFX_Enabled") != "true":
            return
        elif action in [ACTION_SELECT_ITEM, ACTION_MOVE_DOWN, ACTION_MOVE_UP, ACTION_MOVE_LEFT, ACTION_MOVE_RIGHT]:
            xbmc.playSFX(SELECT_SFX)
        elif action in [ACTION_CONTEXT_MENU, ACTION_PAGEDOWN, ACTION_PAGEUP]:
            xbmc.playSFX(CONTEXT_SFX)
        elif action in [ACTION_PREVIOUS_MENU]:
            xbmc.playSFX(BACK_SFX)
            
     
    def setProp(self, title, year, chtype, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, subtitle, playcount, season, episode, pType='OVERLAY'):
        self.log("setProp, title = " + title + ', pType = ' + pType)
        self.setPropTimer = threading.Timer(0.1, self.setProp_thread, [title, year, chtype, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, subtitle, playcount, season, episode, pType])
        self.setPropTimer.name = "setPropTimer"       
        if self.setPropTimer.isAlive():
            self.setPropTimer.cancel()
            self.setPropTimer.join()
        if self.Player.stopped == False and self.isExiting == False:
            self.setPropTimer.start()

        
    def setProp_thread(self, title, year, chtype, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, subtitle, playcount, season, episode, pType):
        self.log("setProp_thread, title = " + title + ', pType = ' + pType)      
        setProperty("%s.Chtype"%pType,str(chtype))
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
        # extra info
        self.isNew(pType)
        self.isManaged(pType)
        # fill art properties
        self.fillArtwork(type, title, year, chtype, chname, id, dbid, mpath, pType)
        # todo rss ticker that matches genre
        # if pType == 'OVERLAY':  


            # getRSSFeed(getProperty("OVERLAY.Genre")) 
           
        
    def fillArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, pType):
        if pType == 'EPG':
            artTypes = self.artEPG_Types
        else:
            artTypes = self.artOVERLAY_Types
        
        self.log('fillArtwork, pType = ' + pType + ' artTypes = ' + str(artTypes))
        for n in range(len(artTypes)):
            try:
                artType = (artTypes[n]).lower()
                self.setArtwork(type, title, year, chtype, chname, id, dbid, mpath, EXTtype(artType), artType, pType)
            except:
                pass
        
        
    # set artwork properties parallel threading    
    def setArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, typeEXT, typeART, pType='OVERLAY'):
        self.log('setArtwork')
        self.ArtThread = threading.Timer(0.1, self.setArtwork_Thread, [type, title, year, chtype, chname, id, dbid, mpath, typeEXT, typeART, pType])
        self.ArtThread.name = "ArtThread"
        if self.ArtThread.isAlive():
            self.ArtThread.cancel()
            self.ArtThread.join()  
        if self.Player.stopped == False and self.isExiting == False:
            self.ArtThread.start()

    
    # set artwork properties
    def setArtwork_Thread(self, type, title, year, chtype, chname, id, dbid, mpath, typeEXT, key, pType):
        self.log('setArtwork_Thread, chtype = ' + str(chtype) + ', id = ' + str(id) +  ', dbid = ' + str(dbid) + ', typeEXT = ' + typeEXT + ', key = ' + key + ', pType = ' + str(pType))  
        try:
            setImage = self.findArtwork(type, title, year, chtype, chname, id, dbid, mpath, typeEXT) 
            setProperty(("%s.%s" %(pType, key)),setImage)
        except Exception,e:
            self.log('setArtwork_Thread, Failed!, ' + str(e))
            pass
    

    # return artwork image
    def findArtwork(self, type, title, year, chtype, chname, id, dbid, mpath, typeEXT):
        try:
            setImage = self.Artdownloader.FindArtwork(type, title, year, chtype, chname, id, dbid, mpath, typeEXT)
            if FileAccess.exists(setImage) == False:
                setImage = self.Artdownloader.SetDefaultArt(chname, mpath, typeEXT)
            setImage = uni(setImage)
            self.log('findArtwork, setImage = ' + setImage)   
            return setImage
        except Exception,e:
            self.log('findArtwork, Failed!, ' + str(e))
            pass
    
    
    def getArtwork(self, type, title, year, chtype, chname, id, dbid, mpath):
        poster = uni(self.findArtwork(type, title, year, chtype, chname, id, dbid, mpath, 'poster'))
        fanart = uni(self.findArtwork(type, title, year, chtype, chname, id, dbid, mpath, 'landscape'))
        return poster, fanart
    
    
    def isNew_Thread(self, pType):
        self.log("isNew_Thread")
        try:
            chtype = int(getProperty("%s.Chtype"%pType))
            mediapath = getProperty("%s.Mediapath"%pType)
            playcount = int(getProperty("%s.Playcount"%pType))
            
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
            # todo parse youtube watched status? create custom db to track watched status?
        except:
            pass
        setProperty("%s.isNEW"%pType,MEDIA_LOC + 'OLD.png')

      
    def isNew(self, pType='OVERLAY'):
        self.log('isNew') 
        if isLowPower() == False:
            self.isNewTimer = threading.Timer(0.5, self.isNew_Thread, [pType])
            self.isNewTimer.name = "isNewTimer"       
            if self.isNewTimer.isAlive():
                self.isNewTimer.cancel()
            self.isNewTimer.start()

     
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
        # if isLowPower() == False:
            # self.isManagedTimer = threading.Timer(0.5, self.isManaged_Thread, [pType])
            # self.isManagedTimer.name = "isManagedTimer"       
            # if self.isManagedTimer.isAlive():
                # self.isManagedTimer.cancel()
            # self.isManagedTimer.start()
            
            
    # Adapted from lamdba's plugin
    def setWatchedStatus_Thread(self, type, title, year, id, dbid, epid, season, episode, playcount):
        self.log('setWatchedStatus_Thread')
        if type == 'movie':
            json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid" : %s, "playcount" : %s }, "id": 1 }' % ((dbid), (playcount)))
            self.channelList.sendJSON(json_query);  
            try:
                from metahandler import metahandlers
                metaget = metahandlers.MetaData(preparezip=False)
                metaget.get_meta('movie', title ,year=year)
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
                json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "playcount" : %s }, "id": 1 }' % ((epid), (playcount)))
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
        # self.getControl(124).setLabel('Trakt')
        # self.getControl(125).setLabel('Test')
        # setProperty("OVERLAY.type4ART",'https://widgets.trakt.tv/users/f5b53eb814eb5335ca533f00dc74b330/watched/thumb@2x.jpg')  
        # self.showPOP(self.InfTimer + 2.5)

        
    def setWatchedStatus(self):
        self.log('setWatchedStatus')
        if REAL_SETTINGS.getSetting("Disable_Watched") == "true" and isLowPower() != True:
            try:
                type = getProperty("OVERLAY.Type")
                title = getProperty("OVERLAY.Cleantitle")
                id = getProperty("OVERLAY.ID")
                dbid = (getProperty("OVERLAY.DBID"))
                epid = (getProperty("OVERLAY.EPID"))
                season = (getProperty("OVERLAY.Season"))
                episode = (getProperty("OVERLAY.Episode"))
                year = (getProperty("OVERLAY.Year"))
                playcount = (getProperty("OVERLAY.Playcount"))
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

        
    def removeInvalid(self):
        self.log('removeInvalid')    
        for i in range(self.maxChannels):
            if self.channels[i].isValid == False:
                print i
                # todo remove invalid channel configurations?
                # setBackgroundLabel('Exiting: Removing Invalid Channels %s' %str(i))
                # chtype = self.getChtype(i)
                # ADDON_SETTINGS.setSetting('Channel_' + str(i) + '_type','9999')
          
          
    def end(self, action=False):
        self.log('end')
        # Prevent the player from setting the sleep timer
        self.Player.stopped = True
        self.setBackgroundVisible(True)        
        self.isExiting = True 
        self.clearOnNow()
        self.clearProp('OVERLAY.NEXT')
        self.clearProp('OVERLAY')
        self.clearProp('EPG')
        self.egTrigger('PseudoTV_Live - Exiting')
        setBackgroundLabel('Exiting: PseudoTV Live')
        setProperty("OVERLAY.LOGOART",THUMB) 
        xbmc.executebuiltin("PlayerControl(repeatoff)")
        curtime = time.time()
        updateDialog = xbmcgui.DialogProgressBG()
        updateDialog.create("PseudoTV Live", "Exiting")
        self.UPNPcontrol('stop')
        
        if CHANNEL_SHARING == True and self.isMaster:
            updateDialog.update(0, "Exiting", "Removing File Locks")
            setBackgroundLabel('Exiting: Removing File Locks')
            GlobalFileLock.unlockFile('MasterLock')
        GlobalFileLock.close()
        
        self.removeInvalid()
        
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
        setBackgroundLabel('Exiting: Stopping Timers')
        
        try:
            if self.startOnNowThread_Timer.isAlive():
                self.startOnNowThread_Timer.cancel()
        except:
            pass
        try:
            if self.channelLabelTimer.isAlive():
                self.channelLabelTimer.cancel()
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
        setBackgroundLabel('Exiting: Stopping Threads')
          
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
            if self.startOnNowTimer.isAlive():
                self.startOnNowTimer.cancel()
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
            if self.setOnNowThread.isAlive():
                self.setOnNowThread.cancel()
        except:
            pass  
        try:
            if self.UPNPcontrolTimer.isAlive():
                self.UPNPcontrolTimer.cancel()
        except:
            pass  

        updateDialog.update(5, "Exiting", "Stopping Artwork Threads")
        setBackgroundLabel('Exiting: Stopping Artwork Threads')  
            
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
                setBackgroundLabel('Exiting: Stopping Channel Threads')  

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
        xbmc.sleep(10)
        # open new window
        if window.upper() == 'EPG':
            self.myEPG.doModal()
        elif window.upper() == 'DVR':
            Comingsoon()
            self.myDVR.doModal()
        elif window.upper() == 'ONDEMAND':
            Comingsoon()
            self.myOndemand.doModal()
        elif window.upper() == 'APPS':
            Comingsoon()
            self.myApps.doModal()

          
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
        elif fallback:
            return THUMB
        else:
            return 'NA.png'

        
    def postBackgroundLoading(self):
        self.log('postBackgroundLoading')
        setProperty("PTVL.BackgroundLoading","false")


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
        try:
            if url.startswith(('http','pvr','rtmp','rtsp','hdhomerun','upnp')):
                if url.startswith(('rtmp','rtsp')):
                    toTime = str((int(round((self.PlayTimeoutInt/int(self.ActionTimeInt))))/4)*3)
                    if 'live=true' not in url:
                        url += ' live=true'
                    if 'timeout=' in url:
                        url = re.sub(r'timeout=\d',"timeout=%s" % toTime,url) 
                    else:
                        url += ' timeout=%s' % toTime

                self.log('setPlayselected, url = ' + url)
                listitem = xbmcgui.ListItem(getProperty("OVERLAY.Title"))
                listitem.setIconImage(getProperty("OVERLAY.LOGOART"))
                content_type = getProperty("OVERLAY.Type").replace("tvshow","episode").replace("other","video").replace("music","musicvideo")           
                    
                infoList = {}
                infoList['mediatype']     = content_type
                infoList['Duration']      = self.channels[self.currentChannel - 1].getItemDuration(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()) 
                infoList['MPAA']          = getProperty("OVERLAY.Rating")
                infoList['TVShowTitle']   = getProperty("OVERLAY.Cleantitle")
                infoList['Title']         = getProperty("OVERLAY.Title")
                infoList['originaltitle'] = getProperty("OVERLAY.Showtitle")
                infoList['sorttitle']     = getProperty("OVERLAY.Cleantitle")
                infoList['Studio']        = getProperty("OVERLAY.Chname")
                infoList['Genre']         = getProperty("OVERLAY.Genre")
                infoList['Plot']          = getProperty("OVERLAY.Description")
                infoList['tagline']       = getProperty("OVERLAY.Tagline")
                infoList['dateadded']     = getProperty("OVERLAY.TimeStamp")
                infoList['code']          = getProperty("OVERLAY.ID")
                infoList['Year']          = int(getProperty("OVERLAY.Year") or '0')
                infoList['Season']        = int(getProperty("OVERLAY.Season") or '0')
                infoList['Episode']       = int(getProperty("OVERLAY.Episode") or '0')
                infoList['playcount']     = int(getProperty("OVERLAY.Playcount") or '0')
 
                # infoList['mediatype']     = content_type
                # infoList['mpaa']          = 'Unknown'
                # infoList['tvshowtitle']   = 'TVShowTitle'
                # infoList['title']         = 'Title'
                # infoList['originaltitle'] = 'originaltitle'
                # infoList['sorttitle']     = 'sorttitle'
                # infoList['studio']        = 'Studio'
                # infoList['genre']         = 'Genre'
                # infoList['plot']          = 'Plot'
                # infoList['plotoutline']   = 'plotoutline'
                # infoList['tagline']       = 'tagline'
                # infoList['dateadded']     = 'dateadded'
                # infoList['premiered']     = 'premiered'
                # infoList['aired']         = 'aired'
                # infoList['code']          = 'code'
                # infoList['lastplayed']    = 'lastplayed'
                # infoList['album']         = 'album'
                # infoList['artist']        = ['artist']
                # infoList['votes']         = 'votes'
                
                
                # infoList['duration']      = 1
                # infoList['year']          = 1977
                # infoList['season']        = 3
                # infoList['episode']       = 4
                # infoList['playcount']     = 5

                # infoList['album']       = getProperty("OVERLAY.SEtitle")
                # infoList['artist']      = getProperty("OVERLAY.Title")
                listitem.setInfo('Video', infoList)    

                infoArt = {}
                infoArt['thumb']        = getProperty("OVERLAY.poster")
                infoArt['poster']       = getProperty("OVERLAY.poster")
                infoArt['banner']       = getProperty("OVERLAY.banner")
                infoArt['fanart']       = getProperty("OVERLAY.fanart")
                infoArt['clearart']     = getProperty("OVERLAY.clearart")
                infoArt['clearlogo']    = getProperty("OVERLAY.clearlogo")
                infoArt['landscape']    = getProperty("OVERLAY.landscape")
                infoList['icon']        = getProperty("OVERLAY.LOGOART")
                listitem.setArt(infoArt)  

                self.Player.play(url, listitem);
            elif url.startswith('ustvnow'):
                link = self.ustv.getChannellink(url.split('://')[1])
                if link.startswith(('rtmp','rtsp')):
                    self.setPlayselected(link)
                else:
                    self.lastActionTrigger()
            elif url.startswith(('plugin','PlayMedia')):
                if not url.startswith('PlayMedia'):
                    url = ('PlayMedia('+url+')')
                xbmc.executebuiltin(tidy(url).replace(',', ''))
            else:
                raise Exception()
        except Exception,e:
            self.log('setPlayselected, Failed! ' + str(e))
            self.Player.play(url)
        return





        

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
        

    def cronThread(self, timer=0.5):
        self.log("cronThread")
        cronThread_Timer = threading.Timer(timer, self.cronJob)
        cronThread_Timer.name = "cronThread_Timer"
        if cronThread_Timer.isAlive():
            cronThread_Timer.cancel()
            cronThread_Timer.join()
        cronThread_Timer.start()

        
    def cronJob(self):
        self.log("cronJob, uptime = " + str(self.cron_uptime))
        self.cron_uptime += 1 # life       
        time.sleep(0.5)
        self.cronThread(timer)
            
            
    def toggleMute(self):
        json_query = '{"jsonrpc":"2.0","method":"Application.SetMute","params":{"mute":"toggle"},"id":1}'
        self.channelList.sendJSON(json_query);
    
    
    def setMute(self, state):
        json_query = '{"jsonrpc":"2.0","method":"Application.SetMute","params":{"mute":%s},"id":1}' %state
        self.channelList.sendJSON(json_query);
                
                
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
        # Pause Background channel building while EPG is opened
        if self.channelThread.isAlive():
            self.channelThread.pause()

        # Auto-off reset after EPG activity.
        self.startSleepTimer()
                
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
        self.channelList.sendJSON(json_query);
        
        
# xbmc.executebuiltin('StartAndroidActivity("com.netflix.mediaclient"),return')
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"videoosd"},"id":5}
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"osdaudiosettings"},"id":17}
# http://localhost:9000/jsonrpc?request={"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"osdvideosettings"},"id":16}