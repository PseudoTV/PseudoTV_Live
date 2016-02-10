#   Copyright (C) 2015 Jason Anderson, Kevin S. Graer
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

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os, sys, re, unicodedata, traceback
import time, datetime, threading, _strptime, calendar
import httplib, urllib, urllib2, feedparser, socket
import base64, shutil, random, errno


from operator import itemgetter
from parsers import HDTrailers
from parsers import xmltv
from utils import *
from xml.etree import ElementTree as ET
from xml.dom.minidom import parse, parseString
from subprocess import Popen, PIPE, STDOUT
from Playlist import Playlist
from Globals import *
from Channel import Channel
from VideoParser import VideoParser
from FileAccess import FileAccess
from hdhr import hdhr
from apis import sickbeard
from apis import couchpotato
from apis import tvdb
from apis import tmdb
from datetime import date
from datetime import timedelta
from BeautifulSoup import BeautifulSoup
from parsers import ustvnow
from pyfscache import *

socket.setdefaulttimeout(30)

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json
    
# Commoncache plugin import
try:
    import StorageServer
except Exception,e:
    import storageserverdummy as StorageServer
    
try:
    from metahandler import metahandlers
except Exception,e:  
    ENHANCED_DATA = False
    xbmc.log("script.pseudotv.live-ChannelList: metahandler Import Failed" + str(e))    

class ChannelList:
    def __init__(self):
        self.xmlTvFile = ''
        self.networkList = []
        self.studioList = []
        self.mixedGenreList = []
        self.showGenreList = []
        self.movieGenreList = []
        self.movie3Dlist = []
        self.musicGenreList = []
        self.pluginPathList = []
        self.pluginNameList = []
        self.PVRList = []
        self.HDHRList = []
        self.showList = []
        self.channels = []
        self.file_detail_CHK = []
        self.cached_readXMLTV = []
        self.sleepTime = 0
        self.threadPaused = False
        self.runningActionChannel = 0
        self.runningActionId = 0
        self.enteredChannelCount = 0
        self.startDate = 0
        self.startTime = 0
        self.background = True    
        self.videoParser = VideoParser()
        self.ustv = ustvnow.ustvnow()
        random.seed() 

    def readConfig(self):
        self.startTime = time.time()
        self.forceReset = REAL_SETTINGS.getSetting('ForceChannelReset') == "true"
        self.log('Force Reset is ' + str(self.forceReset))
        self.startMode = int(REAL_SETTINGS.getSetting("StartMode"))
        self.log('Start Mode is ' + str(self.startMode))
        self.backgroundUpdating = int(REAL_SETTINGS.getSetting("ThreadMode"))
        self.channelResetSetting = int(REAL_SETTINGS.getSetting("ChannelResetSetting"))
        self.inc3D = REAL_SETTINGS.getSetting('Include3D') == "true"
        self.log("Include 3D is " + str(self.inc3D))
        self.incIceLibrary = REAL_SETTINGS.getSetting('IncludeIceLib') == "true"
        self.log("IceLibrary is " + str(self.incIceLibrary))
        self.incBCTs = REAL_SETTINGS.getSetting('IncludeBCTs') == "true"
        self.log("IncludeBCTs is " + str(self.incBCTs))
        self.tvdbAPI = tvdb.TVDB()
        self.tmdbAPI = tmdb.TMDB()  
        self.sbAPI = sickbeard.SickBeard(REAL_SETTINGS.getSetting('sickbeard.baseurl'),REAL_SETTINGS.getSetting('sickbeard.apikey'))
        self.cpAPI = couchpotato.CouchPotato(REAL_SETTINGS.getSetting('couchpotato.baseurl'),REAL_SETTINGS.getSetting('couchpotato.apikey'))
        self.Playlist_Limit = PlaylistLimit()
        self.findMaxChannels()

        if SETTOP:
            self.backgroundUpdating = 0
            self.channelResetSetting = 0
        self.log('Background Updating is ' + str(self.backgroundUpdating))
        self.log('Channel Reset Setting is ' + str(self.channelResetSetting))
            
        if self.forceReset:
            REAL_SETTINGS.setSetting("INTRO_PLAYED","false") # Intro Video Reset
            REAL_SETTINGS.setSetting('StartupMessage', 'false') # Startup Message Reset 
            REAL_SETTINGS.setSetting('ResetLST', '') # Reset ResetLST
            REAL_SETTINGS.setSetting('ReminderLst', '') # Reset Reminders
            REAL_SETTINGS.setSetting('FavChanLst', '') # Reset FavChannels
            REAL_SETTINGS.setSetting('ForceChannelReset', 'false') # Force Channel Reset
            self.forceReset = False

        try:
            self.lastResetTime = int(ADDON_SETTINGS.getSetting("LastResetTime"))
        except Exception,e:
            self.lastResetTime = 0
        try:
            self.lastExitTime = int(ADDON_SETTINGS.getSetting("LastExitTime"))
        except Exception,e:
            self.lastExitTime = int(time.time())
                      
        if self.backgroundUpdating > 0:
            self.updateDialog = xbmcgui.DialogProgress()
        else:
            self.updateDialog = xbmcgui.DialogProgressBG()

            
    def setupList(self, background=False):
        self.readConfig()
        foundvalid = False
        makenewlists = False
        self.background = background
        
        if self.background == False:
            self.updateDialog.create("PseudoTV Live", "Updating Channel List")
            self.updateDialog.update(0, "Updating Channel List", "")
            self.myOverlay.setBackgroundLabel("Initializing: Updating Channel List")
            self.updateDialogProgress = 0
        self.log("setupList, background = " + str(self.background))
        
        if self.backgroundUpdating > 0 and self.myOverlay.isMaster == True:
            makenewlists = True
            
        # Go through all channels, create their arrays, and setup the new playlist
        for i in range(self.maxChannels):
            if self.background == False:
                self.updateDialogProgress = i * 100 // self.enteredChannelCount
                self.updateDialog.update(self.updateDialogProgress, "Initializing: Channel " + str(i + 1), "waiting for file lock")
                self.myOverlay.setBackgroundLabel("Initializing: Channel List (" + str(int(i * 100 // self.maxChannels)) + "%)")
                setProperty('loading.progress',str(self.updateDialogProgress))
            self.channels.append(Channel())
            
            try:
                # If the user pressed cancel, stop everything and exit
                if self.updateDialog.iscanceled():
                    self.log('Update channels cancelled')
                    self.updateDialog.close()
                    return None
            except:
                pass
                
            self.setupChannel(i + 1, self.background, makenewlists, False)
            
            if self.channels[i].isValid:
                foundvalid = True

        if makenewlists == True:
            REAL_SETTINGS.setSetting('ForceChannelReset', 'false')

        if foundvalid == False and makenewlists == False:
            for i in range(self.maxChannels):
                if self.background == False:
                    self.updateDialogProgress = i * 100 // self.enteredChannelCount
                    self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(i + 1), "waiting for file lock")
                    self.myOverlay.setBackgroundLabel("Initializing: Updating Channel " + str(i + 1))
                self.setupChannel(i + 1, self.background, True, False)

                if self.channels[i].isValid:
                    foundvalid = True
                    break
        
        if self.background == False:
            self.updateDialog.update(100, "Update complete", "")
            self.myOverlay.setBackgroundLabel("Initializing: Complete")
            self.updateDialog.close()
        return self.channels 

        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelList: ' + msg, level)


    # Determine the maximum number of channels by opening consecutive
    # playlists until we don't find one
    def findMaxChannels(self):
        self.log('findMaxChannels')
        self.maxChannels = 0
        self.enteredChannelCount = 0
        if self.background == False:
            self.myOverlay.setBackgroundLabel('Initializing: PseudoTV Live')

        for i in range(CHANNEL_LIMIT):
            chtype = 9999
            chsetting1 = ''
            chsetting2 = ''
            chsetting3 = ''
            chsetting4 = ''
            
            try:
                chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_type'))
                chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_1')
                chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_2')
                chsetting3 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_3')
                chsetting4 = ADDON_SETTINGS.getSetting('Channel_' + str(i + 1) + '_4')
            except Exception,e:
                pass

            # todo move channel validation check here
            
            if chtype == 0:
                if FileAccess.exists(xbmc.translatePath(chsetting1)):
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1
            elif chtype <= 20:
                if len(chsetting1) > 0:
                    self.maxChannels = i + 1
                    self.enteredChannelCount += 1
   
            if self.forceReset and (chtype != 9999):
                ADDON_SETTINGS.setSetting('Channel_' + str(i + 1) + '_changed', "True")
                
            # find missing channel logos
            if FIND_LOGOS == True:
                if self.background == False:
                    self.myOverlay.setBackgroundLabel('Initializing: Searching for Channel logos (' + str((i + 1)/10) + '%)')
                if chtype not in [6,7,9999]:
                    if chtype <= 7 or chtype == 12:
                        chname = self.getChannelName(chtype, chsetting1)
                    else:
                        chname = self.getChannelName(chtype, (i + 1))
                    FindLogo(chtype, chname)
                    
        if self.background == False:
            self.myOverlay.setBackgroundLabel('Initializing: Channels') 
        self.log('findMaxChannels return ' + str(self.maxChannels))


    def sendJSON(self, command):
        self.log('sendJSON')
        data = ''
        try:
            data = xbmc.executeJSONRPC(uni(command))
        except UnicodeEncodeError:
            data = xbmc.executeJSONRPC(ascii(command))
        return uni(data)
        
     
    def setupChannel(self, channel, background = False, makenewlist = False, append = False):
        self.log('setupChannel ' + str(channel))
        returnval = False
        createlist = makenewlist
        chtype = 9999
        chsetting1 = ''
        chsetting2 = ''
        chsetting3 = ''
        chsetting4 = ''
        needsreset = False
        self.background = background
        self.settingChannel = channel
        
        try:
            chtype = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
            chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1')
            chsetting2 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_2')
            chsetting3 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_3')
            chsetting4 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_4')
        except:
            pass

        while len(self.channels) < channel:
            self.channels.append(Channel())

        if chtype == 9999:
            self.channels[channel - 1].isValid = False
            return False

        self.channels[channel - 1].type = chtype
        self.channels[channel - 1].isSetup = True
        self.channels[channel - 1].loadRules(channel)
        self.runActions(RULES_ACTION_START, channel, self.channels[channel - 1])

        try:
            needsreset = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_changed') == 'True'
        except:
            needsreset = False
                     
        # Handle LiveTV
        if chtype == 8:  
            # Force livetv rebuild
            forcerebuild = REAL_SETTINGS.getSetting('ForceLiveChannelReset') == "true"
            if channel in self.myOverlay.ResetLST or forcerebuild == True:
                self.log('setupChannel ' + str(channel) + ', forcerebuild = True')
                needsreset = True
                self.delResetLST(channel)
        elif chtype == 16:
            needsreset = True

        if needsreset:
            self.channels[channel - 1].isSetup = False
            
        self.log('setupChannel ' + str(channel) + ', needsreset = ' + str(needsreset))
        self.log('setupChannel ' + str(channel) + ', makenewlist = ' + str(makenewlist))
            
        # If possible, use an existing playlist
        # Don't do this if we're appending an existing channel
        # Don't load if we need to reset anyway
        if FileAccess.exists(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') and append == False and needsreset == False:
            try:
                self.channels[channel - 1].totalTimePlayed = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_time', True))
                createlist = True

                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Loading Channel " + str(channel), "reading playlist")
                else:
                    self.log('setupChannel, Loading Channel ' + str(channel) + ' reading playlist')

                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    self.channels[channel - 1].isValid = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    returnval = True

                    if self.channelResetSetting == 0:
                        # Reset livetv after 24hrs
                        if chtype == 8 and self.channels[channel - 1].totalTimePlayed < (60 * 60 * 24):
                            createlist = False
                        
                        # If this channel has been watched for longer than it lasts, reset the channel
                        if self.channels[channel - 1].totalTimePlayed < self.channels[channel - 1].getTotalDuration():
                            createlist = False

                    if self.channelResetSetting > 0 and self.channelResetSetting < 4:
                        timedif = time.time() - self.lastResetTime
                    
                        if self.channelResetSetting == 1 and timedif < (60 * 60 * 24):
                            createlist = False

                        if self.channelResetSetting == 2 and timedif < (60 * 60 * 24 * 7):
                            createlist = False

                        if self.channelResetSetting == 3 and timedif < (60 * 60 * 24 * 30):
                            createlist = False

                        if timedif < 0:
                            createlist = False

                    if self.channelResetSetting == 4:
                        createlist = False
            except Exception,e:
                self.log('setupChannel ' + str(channel) + ', _time Failed! ' + str(e))
                
        if createlist or needsreset:
            self.channels[channel - 1].isValid = False

            if makenewlist:
                try:
                    xbmcvfs.delete(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u')
                except:
                    self.log("Unable to delete " + 'channel_' + str(channel) + '.m3u', xbmc.LOGERROR)
                append = False

                if createlist:
                    ADDON_SETTINGS.setSetting('LastResetTime', str(int(time.time())))

        if append == False:
            if chtype == 6 and chsetting2 == str(MODE_ORDERAIRDATE):
                self.channels[channel - 1].mode = MODE_ORDERAIRDATE

            # if there is no start mode in the channel mode flags, set it to the default
            if self.channels[channel - 1].mode & MODE_STARTMODES == 0:
                if self.startMode == 0:
                    self.channels[channel - 1].mode |= MODE_RESUME
                elif self.startMode == 1:
                    self.channels[channel - 1].mode |= MODE_REALTIME
                elif self.startMode == 2:
                    self.channels[channel - 1].mode |= MODE_RANDOM

        if ((createlist or needsreset) and makenewlist) or append:
            if self.background == False:
                self.updateDialogProgress = (channel - 1) * 100 // self.enteredChannelCount
                self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "")
            else:
                self.log('setupChannel, Updating Channel ' + str(channel))
            
            if self.makeChannelList(channel, chtype, chsetting1, chsetting2, chsetting3, chsetting4, append) == True:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == True:
                    returnval = True
                    self.channels[channel - 1].fileName = CHANNELS_LOC + 'channel_' + str(channel) + '.m3u'
                    self.channels[channel - 1].isValid = True
                    
                    # Don't reset variables on an appending channel
                    if append == False:
                        self.channels[channel - 1].totalTimePlayed = 0
                        ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', '0')

                        if needsreset:
                            ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_changed', 'False')
                            self.channels[channel - 1].isSetup = True
                    
        self.runActions(RULES_ACTION_BEFORE_CLEAR, channel, self.channels[channel - 1])

        # Don't clear history when appending channels            
        if append == False and self.myOverlay.isMaster:
            self.clearPlaylistHistory(channel)
            
            if self.background == False:
                self.updateDialogProgress = (channel - 1) * 100 // self.enteredChannelCount
                self.updateDialog.update(self.updateDialogProgress, "Initializing: Channel " + str(channel), "clearing history")
            else:
                self.log('setupChannel, Initializing: Channel ' + str(channel) + " clearing history")
            
        if append == False:
            self.runActions(RULES_ACTION_BEFORE_TIME, channel, self.channels[channel - 1])

            if self.channels[channel - 1].mode & MODE_ALWAYSPAUSE > 0:
                self.channels[channel - 1].isPaused = True

            if self.channels[channel - 1].mode & MODE_RANDOM > 0:
                self.channels[channel - 1].showTimeOffset = random.randint(0, self.channels[channel - 1].getTotalDuration())

            if self.channels[channel - 1].mode & MODE_REALTIME > 0:
                timedif = int(self.myOverlay.timeStarted) - self.lastExitTime
                self.channels[channel - 1].totalTimePlayed += timedif

            if self.channels[channel - 1].mode & MODE_RESUME > 0:
                self.channels[channel - 1].showTimeOffset = self.channels[channel - 1].totalTimePlayed
                self.channels[channel - 1].totalTimePlayed = 0

            while self.channels[channel - 1].showTimeOffset > self.channels[channel - 1].getCurrentDuration():
                self.channels[channel - 1].showTimeOffset -= self.channels[channel - 1].getCurrentDuration()
                self.channels[channel - 1].addShowPosition(1)

        self.channels[channel - 1].name = self.getChannelName(chtype, chsetting1)

        if ((createlist or needsreset) and makenewlist) and returnval:
            self.runActions(RULES_ACTION_FINAL_MADE, channel, self.channels[channel - 1])
        else:
            self.runActions(RULES_ACTION_FINAL_LOADED, channel, self.channels[channel - 1])
            
        self.log('setupChannel ' + str(channel) + ', append = ' + str(append))
        self.log('setupChannel ' + str(channel) + ', createlist = ' + str(createlist))
        return returnval

        
    def clearPlaylistHistory(self, channel):
        self.log("clearPlaylistHistory")

        if self.channels[channel - 1].isValid == False:
            self.log("clearPlaylistHistory, channel " + str(channel) + " playlist not valid")
            return

        # if we actually need to clear anything
        if self.channels[channel - 1].totalTimePlayed > (60 * 60 * 24 * 2):
            try:
                fle = FileAccess.open(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', 'w')
            except:
                self.log("clearPlaylistHistory Unable to open the smart playlist", xbmc.LOGERROR)
                return

            flewrite = uni("#EXTM3U\n")
            tottime = 0
            timeremoved = 0

            for i in range(self.channels[channel - 1].Playlist.size()):
                tottime += self.channels[channel - 1].getItemDuration(i)

                if tottime > (self.channels[channel - 1].totalTimePlayed - (60 * 60 * 12)):
                    tmpstr = str(self.channels[channel - 1].getItemDuration(i)) + ','
                    tmpstr += self.channels[channel - 1].getItemTitle(i) + "//" + self.channels[channel - 1].getItemEpisodeTitle(i) + "//" + self.channels[channel - 1].getItemDescription(i) + "//" + self.channels[channel - 1].getItemgenre(i) + "//" + self.channels[channel - 1].getItemtimestamp(i) + "//" + self.channels[channel - 1].getItemLiveID(i)
                    tmpstr = uni(tmpstr[:2036])
                    tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                    tmpstr = uni(tmpstr) + uni('\n') + uni(self.channels[channel - 1].getItemFilename(i))
                    flewrite += uni("#EXTINF:") + uni(tmpstr) + uni("\n")
                else:
                    timeremoved = tottime
            fle.write(flewrite)
            fle.close()

            if timeremoved > 0:
                if self.channels[channel - 1].setPlaylist(CHANNELS_LOC + 'channel_' + str(channel) + '.m3u') == False:
                    self.channels[channel - 1].isValid = False
                else:
                    self.channels[channel - 1].totalTimePlayed -= timeremoved
                    # Write this now so anything sharing the playlists will get the proper info
                    ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_time', str(self.channels[channel - 1].totalTimePlayed))


    def getChannelName(self, chtype, opt):
        chname = ''
        if chtype <= 7 or chtype == 12:
            # opt = setting1
            if len(opt) == 0:
                return ''
            elif chtype == 0:
                return self.getSmartPlaylistName(opt)
            elif chtype == 1 or chtype == 2 or chtype == 6:
                return opt
            elif chtype == 3:
                return opt + " TV"
            elif chtype == 4:
                return opt + " Movies"
            elif chtype == 5:
                return opt + " Mixed"
            elif chtype == 12:
                return opt + " Music"
            elif chtype == 7:
                if opt[-1] == '/' or opt[-1] == '\\':
                    return os.path.split(opt[:-1])[1]
                else:
                    return os.path.split(opt)[1]
        else:
            #opt = channel number
            chname = self.getChname(opt)
            return chname
        return ''
        
        
    def getChtype(self, channel): 
        try:
            return int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_type'))
        except:
            return 9999
        
        
    def getChname(self, channel):
        for i in range(RULES_PER_PAGE):         
            try:
                if int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_rule_%s_id" %str(i+1))) == 1:
                    return ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_rule_%s_opt_1" %str(i+1))
            except:
                return ''

                
    # Open the smart playlist and read the name out of it...this is the channel name
    def getSmartPlaylistName(self, fle):
        self.log('getSmartPlaylistName')
        fle = xbmc.translatePath(fle)

        try:
            xml = FileAccess.open(fle, "r")
        except:
            self.log("getSmartPlaylistName Unable to open the smart playlist " + fle, xbmc.LOGERROR)
            return ''

        try:
            dom = parse(xml)
        except:
            self.log('getSmartPlaylistName Problem parsing playlist ' + fle, xbmc.LOGERROR)
            xml.close()
            return ''

        xml.close()

        try:
            plname = dom.getElementsByTagName('name')
            self.log('getSmartPlaylistName return ' + plname[0].childNodes[0].nodeValue)
            return plname[0].childNodes[0].nodeValue
        except:
            self.log("Unable to get the playlist name.", xbmc.LOGERROR)
            return ''
    
    
    # Based on a smart playlist, create a normal playlist that can actually be used by us
    def makeChannelList(self, channel, chtype, setting1, setting2, setting3, setting4, append = False):
        self.log('makeChannelList, CHANNEL: ' + str(channel))
        fileListCHK = False
        israndom = False  
        isreverse = False
        bctType = None
        fileList = []
        
        #Set Local Limit or Global
        if chtype in [7,10,11,15,16]:
            setting3 = setting3.replace('Unlimited','0')
            setting4 = setting4.replace('Default','0').replace('Random','1').replace('Reverse','2') 
            try:
                limit = int(setting3)
                if isLowPower() == True:
                    raise Exception()
            except Exception,e:
                limit = MEDIA_LIMIT
            self.log("makeChannelList, Overriding Global Parse-limit to " + str(limit))
        else:
            if chtype == 8:
                limit = 259200 #72hrs (seconds)
            elif chtype == 9:
                limit = int(86400 / int(setting1))
            elif MEDIA_LIMIT == 0:
                limit = 10000
            else:
                limit = MEDIA_LIMIT
            self.log("makeChannelList, Using Global Parse-limit " + str(limit))

        # Directory
        if chtype == 7:
            fileList = self.createDirectoryPlaylist(setting1, setting3, setting4, limit)     
            
        # LiveTV
        elif chtype == 8:
            if self.Valid_ok(setting2) == True:
                self.log("Building LiveTV Channel, " + setting1 + " , " + setting2 + " , " + setting3)
                # HDHomeRun #
                if setting2[0:9] == 'hdhomerun' and REAL_SETTINGS.getSetting('HdhomerunMaster') == "true":
                    #If you're using a HDHomeRun Dual and want Tuner 1 assign false. *Thanks Blazin912*
                    self.log("Building LiveTV using tuner0")
                    setting2 = re.sub(r'\d/tuner\d',"0/tuner0",setting2)
                elif setting2[0:9] == 'hdhomerun' and REAL_SETTINGS.getSetting('HdhomerunMaster') == "false":
                    self.log("Building LiveTV using tuner1")
                    setting2 = re.sub(r'\d/tuner\d',"1/tuner1",setting2) 
                fileList = self.buildLiveTVFileList(setting1, setting2, setting3, setting4, limit)
                
        # InternetTV  
        elif chtype == 9:
            if self.Valid_ok(setting2) == True:
                self.log("Building InternetTV Channel, " + setting1 + " , " + setting2 + " , " + setting3)
                fileList = self.buildInternetTVFileList(setting1, setting2, setting3, setting4, limit)

        # Youtube                          
        elif chtype == 10:
            if self.youtube_player_ok() != False:
                setting2 = correctYoutubeSetting2(setting2)
                self.log("Building Youtube Channel " + setting1 + " using type " + setting2 + "...")
                
                if setting2 == '31':
                    today = datetime.datetime.now()
                    month = today.strftime('%B')
                    if setting1.lower() != month.lower():
                        setting1 = month
                        ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", month)
                fileList = self.createYoutubeFilelist(setting1, setting2, setting3, setting4, limit)

        # RSS/iTunes/feedburner/Podcast   
        elif chtype == 11:
            if self.Valid_ok(setting1) == True:
                self.log("Building RSS Feed " + setting1 + " using type " + setting2 + "...")
                fileList = self.createRSSFileList(setting1, setting2, setting3, setting4, limit)      
                
        # MusicVideos
        elif chtype == 13:
            self.log("Building Music Videos")
            fileList = self.MusicVideos(setting1, setting2, setting3, setting4, limit)    
            
        # Extras
        elif chtype == 14:
            self.log("Extras, " + setting1 + "...")
            fileList = self.Extras(setting1, setting2, setting3, setting4, channel, limit)     
            
        # Direct Plugin
        elif chtype == 15:
            if self.Valid_ok(setting1) == True:
                self.log("Building Plugin Channel, " + setting1 + "...")
                fileList = self.buildPluginFileList(setting1, setting2, setting3, setting4, limit)    

        # Direct UPNP
        elif chtype == 16:
            if self.Valid_ok(setting1) == True:
                self.log("Building UPNP Channel, " + setting1 + "...")
                fileList = self.buildUPNPFileList(setting1, setting2, setting3, setting4, limit)  
                
        # LocalTV
        else:
            if chtype == 0:
                if FileAccess.copy(setting1, MADE_CHAN_LOC + os.path.split(setting1)[1]) == False:
                    if FileAccess.exists(MADE_CHAN_LOC + os.path.split(setting1)[1]) == False:
                        self.log("Unable to copy or find playlist " + setting1)
                        return False

                fle = MADE_CHAN_LOC + os.path.split(setting1)[1]
            else:
                fle = self.makeTypePlaylist(chtype, setting1, setting2)
           
            if len(fle) == 0:
                self.log('Unable to locate the playlist for channel ' + str(channel), xbmc.LOGERROR)
                return False

            try:
                xml = FileAccess.open(fle, "r")
            except Exception,e:
                self.log("makeChannelList Unable to open the smart playlist " + fle, xbmc.LOGERROR)
                return False

            try:
                dom = parse(xml)
            except Exception,e:
                self.log('makeChannelList Problem parsing playlist ' + fle, xbmc.LOGERROR)
                xml.close()
                return False
            xml.close()

            if self.getSmartPlaylistType(dom) == 'mixed':
                bctType = 'mixed'
                fileList = self.buildMixedFileList(dom, channel, 10000)
                
            elif self.getSmartPlaylistType(dom) == 'movies':
                bctType = 'movies'
                if REAL_SETTINGS.getSetting('Movietrailers') != 'true':
                    self.incBCTs == False
                fileList = self.buildFileList(fle, channel, 10000)
            
            elif self.getSmartPlaylistType(dom) == 'episodes':
                bctType = 'episodes'
                fileList = self.buildFileList(fle, channel, 10000)
                
            else:
                fileList = self.buildFileList(fle, channel, 10000)

            try:
                order = dom.getElementsByTagName('order')
                if order[0].childNodes[0].nodeValue.lower() == 'random':
                    israndom = True
            except Exception,e:
                pass

        try:
            if append == True:
                channelplaylist = FileAccess.open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "r")
                channelplaylist.seek(0, 2)
                channelplaylist.close()
            else:
                channelplaylist = FileAccess.open(CHANNELS_LOC + "channel_" + str(channel) + ".m3u", "w")
        except Exception,e:
            self.log('Unable to open the cache file ' + CHANNELS_LOC + 'channel_' + str(channel) + '.m3u', xbmc.LOGERROR)
            return False

        if append == False:
            #first queue m3u
            channelplaylist.write(uni("#EXTM3U\n"))
            
        if not fileList or len(fileList) == 0:  
            self.log("Unable to get information about channel " + str(channel), xbmc.LOGERROR)
            channelplaylist.close()
            return False

        # Set Media Sort
        if chtype in [7, 10, 11, 12, 13, 15, 16] and self.myOverlay.isMaster == True:
            if setting4 == '1':
                #RANDOM
                israndom = True
                isreverse = False
            elif setting4 == '2':
                #REVERSE ORDER
                israndom = False
                isreverse = True
            else:
                #DEFAULT
                israndom = False  
                isreverse = False
                
        msg = 'default'     
        if israndom:
            random.shuffle(fileList)
            msg = 'randomizing' 
        elif isreverse:
            fileList.reverse()
            msg = 'reversing'
        
        if append:
            if len(fileList) + self.channels[channel - 1].Playlist.size() > self.Playlist_Limit:
                fileList = fileList[:(self.Playlist_Limit - self.channels[channel - 1].Playlist.size())]
        else:
            if len(fileList) > self.Playlist_Limit:
                fileList = fileList[:self.Playlist_Limit]
        
        self.channels[channel - 1].isRandom = israndom
        self.channels[channel - 1].isReverse = isreverse
        self.log("makeChannelList, Using Media Sort " + msg)
        fileList = self.runActions(RULES_ACTION_LIST, channel, fileList)
        
        # inject BCT into filelist
        if self.incBCTs == True and bctType != None and self.myOverlay.isMaster == True:
            fileList = self.insertBCT(chtype, channel, fileList, bctType)
            
        # Write each entry into the new playlist
        for string in fileList:
            channelplaylist.write(uni("#EXTINF:") + uni(string) + uni("\n"))
         
        # cleanup   
        del fileList[:]
        channelplaylist.close()
        self.log('makeChannelList return')
        return True

        
    def makeTypePlaylist(self, chtype, setting1, setting2):
        if chtype == 1:
            if len(self.networkList) == 0:
                self.fillTVInfo()
            return self.createNetworkPlaylist(setting1)
            
        elif chtype == 2:
            if len(self.studioList) == 0:
                self.fillMovieInfo()
            return self.createStudioPlaylist(setting1)
            
        elif chtype == 3:
            if len(self.showGenreList) == 0:
                self.fillTVInfo()
            return self.createGenrePlaylist('episodes', chtype, setting1)
            
        elif chtype == 4:
            if len(self.movieGenreList) == 0:
                self.fillMovieInfo()
            return self.createGenrePlaylist('movies', chtype, setting1)
            
        elif chtype == 5:
            if len(self.mixedGenreList) == 0:
                if len(self.showGenreList) == 0:
                    self.fillTVInfo()

                if len(self.movieGenreList) == 0:
                    self.fillMovieInfo()

                self.mixedGenreList = self.makeMixedList(self.showGenreList, self.movieGenreList)
                self.mixedGenreList.sort(key=lambda x: x.lower())
            return self.createGenreMixedPlaylist(setting1)
            
        elif chtype == 6:
            if len(self.showList) == 0:
                self.fillTVInfo()
            return self.createShowPlaylist(setting1, setting2)    
            
        elif chtype == 12:
            if len(self.musicGenreList) == 0:
                self.fillMusicInfo()
            return self.createGenrePlaylist('songs', chtype, setting1)
        self.log('makeTypePlaylists invalid channel type: ' + str(chtype))
        return ''    


    def writeXSPHeader(self, fle, pltype, plname, match='one'):
        fle.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
        fle.write('<smartplaylist type="'+pltype+'">\n')
        fle.write('    <name>'+self.cleanString(plname)+'</name>\n')
        fle.write('    <match>'+match+'</match>\n')


    def writeXSPFooter(self, fle, limit, sort, order='ascending'):
        fle.write('    <limit>'+str(limit)+'</limit>\n')
        fle.write('    <order direction="'+order+'">'+sort+'</order>\n')
        fle.write('</smartplaylist>\n')
            
        
    def createNetworkPlaylist(self, network):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'network_' + network + '.xsp')
        
        try:
            fle = FileAccess.open(flename, "w")
        except:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "episodes", self.getChannelName(1, network))
        network = network.lower()
        added = False

        fle.write('    <rule field="tvshow" operator="is">\n')
        
        for i in range(len(self.showList)):
            if self.threadPause() == False:
                fle.close()
                return ''

            if self.showList[i][1].lower() == network:
                theshow = self.cleanString(self.showList[i][0])                
                fle.write('        <value>' + theshow + '</value>\n')            
                added = True
        
        fle.write('    </rule>\n')
        
        self.writeXSPFooter(fle, MEDIA_LIMIT, "random")
        fle.close()

        if added == False:
            return ''
        return flename


    def createShowPlaylist(self, show, setting2):
        order = 'random'

        try:
            setting = int(setting2)
            if setting & MODE_ORDERAIRDATE > 0:
                order = 'episode'
        except Exception,e:
            pass

        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Show_' + show + '_' + order + '.xsp')
        
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, 'episodes', self.getChannelName(6, show))
        show = self.cleanString(show)
        fle.write('    <rule field="tvshow" operator="is">\n')
        fle.write('        <value>' + show + '</value>\n')
        fle.write('    </rule>\n')
        
        self.writeXSPFooter(fle, MEDIA_LIMIT, order)
        fle.close()
        return flename

    
    def fillMixedGenreInfo(self):
        if len(self.mixedGenreList) == 0:
            if len(self.showGenreList) == 0:
                self.fillTVInfo()
            if len(self.movieGenreList) == 0:
                self.fillMovieInfo()

            self.mixedGenreList = self.makeMixedList(self.showGenreList, self.movieGenreList)
            self.mixedGenreList.sort(key=lambda x: x.lower())


    def makeMixedList(self, list1, list2):
        self.log("makeMixedList")
        newlist = []

        for item in list1:
            curitem = item.lower()

            for a in list2:
                if curitem == a.lower():
                    newlist.append(item)
                    break

        self.log("makeMixedList return " + str(newlist))
        return newlist

        
    def createGenreMixedPlaylist(self, genre):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'mixed_' + genre + '.xsp')
        
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        epname = os.path.basename(self.createGenrePlaylist('episodes', 3, genre))
        moname = os.path.basename(self.createGenrePlaylist('movies', 4, genre))
        self.writeXSPHeader(fle, 'mixed', self.getChannelName(5, genre))
        fle.write('    <rule field="playlist" operator="is">' + epname + '</rule>\n')
        fle.write('    <rule field="playlist" operator="is">' + moname + '</rule>\n')
        self.writeXSPFooter(fle, MEDIA_LIMIT, "random")
        fle.close()
        return flename


    def createGenrePlaylist(self, pltype, chtype, genre):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + pltype + '_' + genre + '.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, pltype, self.getChannelName(chtype, genre))
        genre = self.cleanString(genre)
        fle.write('    <rule field="genre" operator="is">\n')
        fle.write('        <value>' + genre + '</value>\n')
        fle.write('    </rule>\n')
        self.writeXSPFooter(fle, MEDIA_LIMIT, "random")
        fle.close()
        return flename


    def createStudioPlaylist(self, studio):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'Studio_' + studio + '.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "movies", self.getChannelName(2, studio))
        studio = self.cleanString(studio)
        fle.write('    <rule field="studio" operator="is">\n')
        fle.write('        <value>' + studio + '</value>\n')
        fle.write('    </rule>\n')
        self.writeXSPFooter(fle, MEDIA_LIMIT, "random")
        fle.close()
        return flename
        
        
    def createCinemaExperiencePlaylist(self):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'movies_CinemaExperience.xsp')
        twoyearsold = date.today().year - 2

        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''
        
        self.writeXSPHeader(fle, "movies", 'Cinema Experience', 'all')
        fle.write('    <rule field="videoresolution" operator="greaterthan">\n')
        fle.write('        <value>720</value>\n')
        fle.write('    </rule>\n')
        fle.write('    <rule field="playcount" operator="is">\n')
        fle.write('        <value>0</value>\n')
        fle.write('    </rule>\n')
        fle.write('    <rule field="year" operator="greaterthan">\n')
        fle.write('        <value>' + str(twoyearsold) + '</value>\n')
        fle.write('    </rule>\n')
        fle.write('    <group>none</group>\n')
        self.writeXSPFooter(fle, MEDIA_LIMIT, "random")
        fle.close()
        return flename
        
        
    def createRecentlyAddedTV(self):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'episodes_RecentlyAddedTV.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "episodes", 'Recently Added TV', 'all')
        self.writeXSPFooter(fle, MEDIA_LIMIT, "dateadded", "descending")
        fle.close()
        return flename
        
    
    def createRecentlyAddedMovies(self):
        flename = xbmc.makeLegalFilename(GEN_CHAN_LOC + 'movies_RecentlyAddedMovies.xsp')
        try:
            fle = FileAccess.open(flename, "w")
        except Exception,e:
            self.Error('Unable to open the cache file ' + flename, xbmc.LOGERROR)
            return ''

        self.writeXSPHeader(fle, "movies", 'Recently Added Movies', 'all')
        self.writeXSPFooter(fle, MEDIA_LIMIT, "dateadded", "descending")
        fle.close()
        return flename
        

    def createDirectoryPlaylist(self, setting1, setting3, setting4, limit):
        self.log("createDirectoryPlaylist")
        fileList = []
        LocalLST = []
        LocalFLE = ''
        filecount = 0 
        
        if not setting1.endswith('/'):
            setting1 = os.path.join(setting1,'')
        LocalLST = self.walk(setting1)

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "parsing Directories")
            
        for i in range(len(LocalLST)):         
            if self.threadPause() == False:
                del fileList[:]
                break
                
            LocalFLE = (LocalLST[i])[0]
            duration = self.getDuration(LocalFLE)
                                            
            if duration == 0 and LocalFLE[-4:].lower() == 'strm':
                duration = 3600
                self.log("createDirectoryPlaylist, no strm duration found defaulting to 3600")
                    
            if duration > 0:
                filecount += 1
                
                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding %s Videos" % str(filecount))
                    
                title = (os.path.split(LocalFLE)[1])
                title = os.path.splitext(title)[0].replace('.', ' ')
                description = LocalFLE.replace('//','/').replace('/','\\')
                GenreLiveID = ['Unknown', 'other', 0, 0, False, 1, 'NR', False, False, 0.0]
                tmpstr = self.makeTMPSTR(duration, title, 'Directory Video', description, GenreLiveID, LocalFLE)
                fileList.append(tmpstr)
                    
                if filecount >= limit:
                    break
                    
        if filecount == 0:
            self.log('Unable to access Videos files in ' + setting1)
            
        # cleanup   
        del LocalLST[:]
        return fileList

        
    # pack string for playlist
    def packGenreLiveID(self, GenreLiveID):
        self.log("packGenreLiveID, GenreLiveID = " + str(GenreLiveID))
        genre = GenreLiveID[0]
        LiveID = '|'.join(str(x) for x in GenreLiveID[1:])
        return genre, LiveID

        
    # unpack list for parsing
    def unpackLiveID(self, LiveID):
        self.log("unpackLiveID, LiveID = " + LiveID)
        LiveID = LiveID.split('|')
        return LiveID
    
    
    def makeTMPSTR(self, duration, showtitle, subtitle, description, GenreLiveID, file, timestamp=None):
        genre, LiveID = self.packGenreLiveID(GenreLiveID)
        showtitle = self.cleanLabels(showtitle)
        subtitle = self.cleanLabels(subtitle)
        description = self.cleanLabels(description)
        genre = self.cleanLabels(genre)
        file = self.cleanPlayableFile(file)
        if not timestamp:
            timestamp = datetime.datetime.now()
        timestamp = str(timestamp).split('.')[0]

        try:
            showtitle = (trim(showtitle, 350, ''))
        except Exception,e:
            self.log("showtitle Trim failed" + str(e))
            showtitle = (showtitle[:350])
        try:
            subtitle = (trim(subtitle, 350, ''))
        except Exception,e:
            self.log("subtitle Trim failed" + str(e))
            subtitle = (subtitle[:350])
        try:
            description = (trim(description, 350, '...'))
        except Exception,e:
            self.log("description Trim failed" + str(e))
            description = (description[:350])   
        tmpstr = str(duration) + ',' + showtitle + "//" + subtitle + "//" + description + "//" + genre + "//" + timestamp + "//" + LiveID + '\n' + file
        tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")                  
        return tmpstr

        
    def cleanPlayableFile(self, file):
        self.log('cleanPlayableFile')
        if self.youtube_player_ok() != False:
            self.youtube_player = self.youtube_player_ok()
            file = file.replace('http://www.youtube.com/watch?v=', self.youtube_player)
            file = file.replace('https://www.youtube.com/watch?v=', self.youtube_player)
            file = file.replace('plugin://plugin.video.bromix.youtube/play/?video_id=', self.youtube_player)
            file = file.replace('plugin://plugin.video.youtube/?action=play_video&videoid=', self.youtube_player)
        file = file.replace("\\\\", "\\")
        return file
        

    def cleanString(self, string):
        self.log("cleanString")
        newstr = uni(string)
        newstr = newstr.replace('&', '&amp;')
        newstr = newstr.replace('>', '&gt;')
        newstr = newstr.replace('<', '&lt;')
        newstr = newstr.replace('"', '&quot;')
        return uni(newstr)

    
    def uncleanString(self, string):
        self.log("uncleanString")
        newstr = uni(string)
        newstr = newstr.replace('&amp;', '&')
        newstr = newstr.replace('&gt;', '>')
        newstr = newstr.replace('&lt;', '<')
        newstr = newstr.replace('&quot;', '"')
        return uni(newstr)
              
              
    def cleanLabels(self, text, format=''):
        self.log('cleanLabels, IN = ' + text)
        text = uni(text)
        text = re.sub('\[COLOR (.+?)\]', '', text)
        text = re.sub('\[/COLOR\]', '', text)
        text = re.sub('\[COLOR=(.+?)\]', '', text)
        text = re.sub('\[color (.+?)\]', '', text)
        text = re.sub('\[/color\]', '', text)
        text = re.sub('\[Color=(.+?)\]', '', text)
        text = re.sub('\[/Color\]', '', text)
        text = text.replace("[]",'')
        text = text.replace("[UPPERCASE]",'')
        text = text.replace("[/UPPERCASE]",'')
        text = text.replace("[LOWERCASE]",'')
        text = text.replace("[/LOWERCASE]",'')
        text = text.replace("[B]",'')
        text = text.replace("[/B]",'')
        text = text.replace("[I]",'')
        text = text.replace("[/I]",'')
        text = text.replace('[D]','')
        text = text.replace('[F]','')
        text = text.replace("[CR]",'')
        text = text.replace("[HD]",'')
        text = text.replace("()",'')
        text = text.replace("[CC]",'')
        text = text.replace("[Cc]",'')
        text = text.replace("[Favorite]", "")
        text = text.replace("[DRM]", "")
        text = text.replace('(cc).','')
        text = text.replace('(n)','')
        text = text.replace("(SUB)",'')
        text = text.replace("(DUB)",'')
        text = text.replace('(repeat)','')
        text = text.replace("(English Subtitled)", "")    
        text = text.replace("*", "")
        text = text.replace("\n", "")
        text = text.replace("\r", "")
        text = text.replace("\t", "")
        text = text.replace("/",'')
        text = text.replace("\ ",'')
        text = text.replace("/ ",'')
        text = text.replace("\\",'/')
        text = text.replace("//",'/')
        text = text.replace('/"','')
        text = text.replace('*NEW*','')
        text = text.replace('plugin.video.','')
        text = text.replace('plugin.audio.','')

        if format == 'title':
            text = text.title().replace("'S","'s")
        elif format == 'upper':
            text = text.upper()
        elif format == 'lower':
            text = text.lower()
        else:
            text = text
            
        text = self.uncleanString(text.strip())
        self.log('cleanLabels, OUT = ' + text)
        return text
    
    
    def cleanRating(self, rating):
        self.log("cleanRating")
        rating = uni(rating)
        rating = self.cleanLabels(rating,'upper')
        rating = rating.replace('RATED ','')
        rating = rating.replace('US:','')
        rating = rating.replace('UK:','')
        rating = rating.replace('UNRATED','NR')
        rating = rating.replace('NOTRATED','NR')
        rating = rating.replace('UNKNOWN','NR')
        rating = rating.replace('N/A','NR')
        rating = rating.replace('NA','NR')
        rating = rating.replace('APPROVED','NR')
        rating = rating.replace('NOT RATED','NR')
        rating = rating.split(' ')[0]
        return uni(rating[0:5])

        
    def fillMusicInfo(self, sortbycount = False):
        self.log("fillMusicInfo")
        self.musicGenreList = []
        json_query = ('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties":["genre"]}, "id": 1}')
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "parsing Music")

        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.musicGenreList[:]
                return

            match = re.search('"genre" *: *\[(.*?)\]', f)
          
            if match:
                genres = match.group(1).split(',')
               
                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.musicGenreList)):
                        if self.threadPause() == False:
                            del self.musicGenreList[:]
                            return
                            
                        itm = self.musicGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.musicGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.musicGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.musicGenreList.append(genre.strip('"').strip())
    
        if sortbycount:
            self.musicGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            self.musicGenreList.sort(key=lambda x: x.lower())

        if (len(self.musicGenreList) == 0):
            self.log(json_folder_detail)

        self.log("found genres " + str(self.musicGenreList))
     
    
    def fillTVInfo(self, sortbycount = False):
        self.log("fillTVInfo")
        json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties":["studio", "genre"]}, "id": 1}')

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "parsing TV Shows")

        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.networkList[:]
                del self.showList[:]
                del self.showGenreList[:]
                return

            match = re.search('"studio" *: *\[(.*?)\]', f)
            network = ''

            if match:
                network = (match.group(1).split(','))[0]
                network = (network.strip('"').strip())
                found = False

                for item in range(len(self.networkList)):
                    if self.threadPause() == False:
                        del self.networkList[:]
                        del self.showList[:]
                        del self.showGenreList[:]
                        return

                    itm = self.networkList[item]

                    if sortbycount:
                        itm = itm[0]

                    if itm.lower() == network.lower():
                        found = True

                        if sortbycount:
                            self.networkList[item][1] += 1

                        break

                if found == False and len(network) > 0:
                    if sortbycount:
                        self.networkList.append([network, 1])
                    else:
                        self.networkList.append(network)

            match = re.search('"label" *: *"(.*?)",', f)

            if match:
                show = (match.group(1).strip())
                self.showList.append([show, network])
                
            match = re.search('"genre" *: *\[(.*?)\]', f)

            if match:
                genres = (match.group(1).split(','))
                
                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.showGenreList)):
                        if self.threadPause() == False:
                            del self.networkList[:]
                            del self.showList[:]
                            del self.showGenreList[:]
                            return

                        itm = self.showGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.showGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.showGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.showGenreList.append(genre.strip('"').strip())

        if sortbycount:
            self.networkList.sort(key=lambda x: x[1], reverse = True)
            self.showGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            self.networkList.sort(key=lambda x: x.lower())
            self.showGenreList.sort(key=lambda x: x.lower())

        if (len(self.showList) == 0) and (len(self.showGenreList) == 0) and (len(self.networkList) == 0):
            self.log(json_folder_detail)

        self.log("found shows " + str(self.showList))
        self.log("found genres " + str(self.showGenreList))
        self.log("fillTVInfo return " + str(self.networkList))


    def fillMovieInfo(self, sortbycount = False):
        self.log("fillMovieInfo")
        studioList = []
        json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties":["studio", "genre"]}, "id": 1}')

        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "parsing Movies")

        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)

        for f in detail:
            if self.threadPause() == False:
                del self.movieGenreList[:]
                del self.studioList[:]
                del studioList[:]
                break

            match = re.search('"genre" *: *\[(.*?)\]', f)

            if match:
                genres = match.group(1).split(',')

                for genre in genres:
                    found = False
                    curgenre = genre.lower().strip('"').strip()

                    for g in range(len(self.movieGenreList)):
                        itm = self.movieGenreList[g]

                        if sortbycount:
                            itm = itm[0]

                        if curgenre == itm.lower():
                            found = True

                            if sortbycount:
                                self.movieGenreList[g][1] += 1

                            break

                    if found == False:
                        if sortbycount:
                            self.movieGenreList.append([genre.strip('"').strip(), 1])
                        else:
                            self.movieGenreList.append(genre.strip('"').strip())

            match = re.search('"studio" *: *\[(.*?)\]', f)
           
            if match:
                studios = match.group(1).split(',')
                
                for studio in studios:
                    curstudio = studio.strip('"').strip()
                    found = False

                    for i in range(len(studioList)):
                        if studioList[i][0].lower() == curstudio.lower():
                            studioList[i][1] += 1
                            found = True
                            break

                    if found == False and len(curstudio) > 0:
                        studioList.append([curstudio, 1])

        maxcount = 0

        for i in range(len(studioList)):
            if studioList[i][1] > maxcount:
                maxcount = studioList[i][1]

        bestmatch = 1
        lastmatch = 1000
        counteditems = 0

        for i in range(maxcount, 0, -1):
            itemcount = 0

            for j in range(len(studioList)):
                if studioList[j][1] == i:
                    itemcount += 1

            if abs(itemcount + counteditems - 8) < abs(lastmatch - 8):
                bestmatch = i
                lastmatch = itemcount

            counteditems += itemcount

        if sortbycount:
            studioList.sort(key=lambda x: x[1], reverse=True)
            self.movieGenreList.sort(key=lambda x: x[1], reverse=True)
        else:
            studioList.sort(key=lambda x: x[0].lower())
            self.movieGenreList.sort(key=lambda x: x.lower())

        for i in range(len(studioList)):
            if studioList[i][1] >= bestmatch:
                if sortbycount:
                    self.studioList.append([studioList[i][0], studioList[i][1]])
                else:
                    self.studioList.append(studioList[i][0])

        if (len(self.movieGenreList) == 0) and (len(self.studioList) == 0):
            self.log(json_folder_detail)

        self.movieGenreList = (self.movieGenreList)
        self.studioList = (self.studioList)
        
        self.log("found genres " + str(self.movieGenreList))
        self.log("fillMovieInfo return " + str(self.studioList))

        
    # replace with json request info todo
    def isMedia3D(self, path):
        Media3D = False
        # if self.inc3D == True:
            # FILTER_3D = ['3d','sbs','fsbs','ftab','hsbs','h.sbs','h-sbs','htab','sbs3d','3dbd','halfsbs','half.sbs','half-sbs','fullsbs','full.sbs','full-sbs','3dsbs','3d.sbs']
            # for i in range(len(FILTER_3D)):
                # if FILTER_3D[i] in path.lower():   
                    # Media3D = True  
        self.log("isMedia3D = " + str(Media3D))                      
        return Media3D
          

    def buildFileList(self, dir_name, channel, limit, FleType = 'video'): ##fix music channel todo
        self.log("buildFileList")
        self.dircount = 0
        self.filecount = 0
        fileList = []
        self.file_detail_CHK = []
        self.startDate = self.startTime
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "querying Kodi database")

        fileList = self.getFileList(self.requestList(dir_name), channel, limit)
        self.log("buildFileList return")
        return fileList
  
  
    def buildPluginFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log('buildPluginFileList')
        self.dircount = 0
        self.filecount = 0
        fileList = []  
        self.file_detail_CHK = []
        self.startDate = self.startTime
        
        if setting1.endswith('/'):
            setting1 = setting1[:-1]
            
        PluginPath = (setting1.replace('plugin://','')).split('/')[0]
        PluginName = (xbmcaddon.Addon(id=PluginPath)).getAddonInfo('name')
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "parsing plugin - %s"%PluginName)
        
        try:
            excludeLST = setting2.split(',')
        except:
            excludeLST = []
            pass
  
        excludeLST += EX_FILTER
        excludeLST = removeStringElem(excludeLST)
        self.log('buildPluginFileList, excludeLST = ' + str(excludeLST))
        fileList = self.getFileList(self.requestList(setting1), self.settingChannel, limit, excludeLST)
        self.log("buildPluginFileList return")
        return fileList
        
        
    def buildUPNPFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log('buildUPNPFileList')
        Directs = ''
        self.dircount = 0
        self.filecount = 0
        fileList = []  
        self.file_detail_CHK = []
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "parsing upnp source")
        
        if setting1.endswith('/'):
            setting1 = setting1[:-1]
                    
        try:
            excludeLST = setting2.split(',')
        except:
            excludeLST = []
  
        excludeLST += EX_FILTER
        excludeLST = removeStringElem(excludeLST)
        self.log('buildUPNPFileList, excludeLST = ' + str(excludeLST))
        upnpID = 'upnp://' + (setting1.split('/')[2:-1])[0]
    
        # todo convert upnp:// to file/path names, store in setting1
        # ADDON_SETTINGS.setSetting("Channel_" + str(self.settingChannel) + "_1", setting1)
        
        # try:
            # Directs = (setting1.split('/')) # split folders
            # Directs = ([x.replace('%2F','/') for x in Directs if x != '']) # remove empty elements
            # PluginName = Directs[0]
            # Directs = Directs[2:]
        # except:
            # Directs = []
            # PluginName = setting1
            # pass
            # self.log('BuildUPNPFileList_NEW, Directs = ' + str(Directs))

            # if self.background == False:
                # self.updateDialog.update(self.updateDialogProgress, "Updating channel " + str(self.settingChannel), "Building Playon", 'parsing ' + str(PluginName))

            # Match = True
            # while Match:

                # DetailLST = self.PluginInfo(upnpID)

                # #Plugin listitems return parent list during error, catch repeat list and end loops.
                # if DetailLST_CHK == DetailLST:
                    # break
                # else:
                    # DetailLST_CHK = DetailLST

                # #end while when no more directories to walk
                # if len(Directs) <= 1:
                    # Match = False
                
                # try:
                    # for i in range(len(DetailLST)):
                        # Detail = (DetailLST[i]).split(',')
                        # filetype = Detail[0]
                        # title = Detail[1]
                        # genre = Detail[2]
                        # dur = Detail[3]
                        # description = Detail[4]
                        # file = Detail[5]
                                     
                        # if filetype == 'directory':
                            # if Directs[0].lower() == title.lower():
                                # self.log('BuildUPNPFileList_NEW, Directory Match: ' + Directs[0].lower() + ' = ' + title.lower())
                                # Directs.pop(0) #remove old directory, search next element
                                # upnpID = file
                                # break
                # except Exception,e:
                    # pass    
                
        # #all directories found, walk final folder
        # if len(Directs) == 0:
            # showList = self.PluginWalk(upnpID, excludeLST, limit, 'UPNP', 'video')
        # return showList

        fileList = self.getFileList(self.requestList(setting1), self.settingChannel, limit, excludeLST)
        self.log("buildUPNPFileList return")
        return fileList
          
 
    def getJsonLabels(self, url):
        self.log('getJsonLabels')
        Directs = []
        return Directs
            
    def buildMixedFileList(self, dom1, channel, limit):
        self.log('buildMixedFileList')
        fileList = []
        try:
            rules = dom1.getElementsByTagName('rule')
            order = dom1.getElementsByTagName('order')
        except Exception,e:
            self.log('buildMixedFileList Problem parsing playlist ' + filename, xbmc.LOGERROR)
            xml.close()
            
            return fileList

        for rule in rules:
            rulename = rule.childNodes[0].nodeValue

            if FileAccess.exists(xbmc.translatePath('special://profile/playlists/video/') + rulename):
                FileAccess.copy(xbmc.translatePath('special://profile/playlists/video/') + rulename, MADE_CHAN_LOC + rulename)
                fileList.extend(self.buildFileList(MADE_CHAN_LOC + rulename, channel, limit))
            else:
                fileList.extend(self.buildFileList(GEN_CHAN_LOC + rulename, channel, limit))

        self.log("buildMixedFileList returning")
        return fileList

        
    # *Thanks sphere, adapted from plugin.video.ted.talks
    # People still using Python <2.7 201303 :(
    def __total_seconds__(self, delta):
        try:
            return delta.total_seconds()
        except AttributeError:
            return int((delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10 ** 6)) / 10 ** 6


    def parsePVRDate(self, dateString):
        self.log("parsePVRDate") 
        if dateString is not None:
            t = time.strptime(dateString, '%Y-%m-%d %H:%M:%S')
            tmpDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
            timestamp = calendar.timegm(tmpDate.timetuple())
            local_dt = datetime.datetime.fromtimestamp(timestamp)
            assert tmpDate.resolution >= timedelta(microseconds=1)
            return local_dt.replace(microsecond=tmpDate.microsecond) 
        else:
            return None
   
   
    def parseUTCXMLTVDate(self, dateString):
        self.log("parseUTCXMLTVDate") 
        if dateString is not None:
            if dateString.find(' ') != -1:
                # remove timezone information
                dateString = dateString[:dateString.find(' ')]
            t = time.strptime(dateString, '%Y%m%d%H%M%S')
            tmpDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
            timestamp = calendar.timegm(tmpDate.timetuple())
            local_dt = datetime.datetime.fromtimestamp(timestamp)
            assert tmpDate.resolution >= timedelta(microseconds=1)
            return local_dt.replace(microsecond=tmpDate.microsecond) 
        else:
            return None
       
       
    def parseXMLTVDate(self, dateString, offset=0):
        self.log("parseXMLTVDate") 
        if dateString is not None:
            if dateString.find(' ') != -1:
                # remove timezone information
                dateString = dateString[:dateString.find(' ')]
            t = time.strptime(dateString, '%Y%m%d%H%M%S')
            d = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
            d += datetime.timedelta(hours = offset)
            return d
        else:
            return None
            
            
    def buildLiveTVFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log("buildLiveTVFileList")  
        showList = []
        # Validate XMLTV Data #
        if self.xmltv_ok(setting3) == True:
            chname = (self.getChannelName(8, self.settingChannel))
            if setting3 == 'pvr':
                showList = self.fillLiveTVPVR(setting1, setting2, setting3, setting4, chname, limit)
            else:   
                showList = self.fillLiveTV(setting1, setting2, setting3, setting4, chname, limit)
        if not showList:
            # Add channel to ResetLST, on next update force channel rebuild
            self.setResetLST(self.settingChannel)
            chname = (self.getChannelName(9, self.settingChannel))
            desc = 'Guidedata from ' + str(setting3) + ' is currently unavailable, please verify channel configuration.'
            showList = self.buildInternetTVFileList('5400', setting2, chname, desc, 24)
        return showList     
        
        
    def fillLiveTV(self, setting1, setting2, setting3, setting4, chname, limit):
        self.log("fillLiveTV")
        showList = []
        showcount = 0          
        try:
            # local or url xmltv file
            if setting3[0:4] == 'http':
                f = open_url(self.xmlTvFile)
            else:
                f = FileAccess.open(self.xmlTvFile, "r")
                
            # check if xmltv uses utc time
            if setting3.lower() in UTC_XMLTV:                      
                offset = ((time.timezone / 3600) - 5 ) * -1     
            else:
                offset = 0
                
            if self.background == False:
                self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding LiveTV, parsing " + chname)

            context = ET.iterparse(f, events=("start", "end")) 
            context = iter(context)
            event, root = context.next()

            for event, elem in context:
                if self.threadPause() == False:
                    del showList[:]
                    break
                              
                if showcount >= limit:
                    break
                try:    
                    id = 0
                    seasonNumber = 0
                    episodeNumber = 0
                    episodeName = ''
                    episodeDesc = ''
                    episodeGenre = ''
                    dd_progid = ''
                    type = ''
                    LiveID = 'tvshow|0|0|False|1|NR|'
                    thumburl = 0
                    
                    if event == "end":
                        if elem.tag == "programme":
                            channel = elem.get("channel")
                            if setting1 == channel:
                                self.log("fillLiveTV, setting1 = " + setting1 + ', channel id = ' + channel)
                                showtitle = elem.findtext('title')
                                description = elem.findtext("desc")
                                
                                icon = None
                                iconElement = elem.find("icon")
                                if iconElement is not None:
                                    icon = iconElement.get("src")
                                    if icon.startswith('http'):
                                        thumburl = encodeString(icon)
                                    elif icon.startswith('"photos"'):
                                        thumburl = encodeString(((cleanHTML(icon)).replace('"}]',"").replace("\/","//")).rsplit(':"', 1)[1])
                                    elif icon.startswith('&quot;photos&quot;:'):
                                        icon = (icon.split('&quot;photos&quot;:')[1]).replace('\/','/').replace('&quot;','')
                                        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(icon)
                                        for c in detail:
                                            if c.startswith('width:430,height:574,url:'):
                                                thumburl = encodeString(f.split('width:430,height:574,url:')[1])
                                                break
                                    
                                subtitle = elem.findtext("sub-title")
                                if not subtitle:                        
                                    subtitle = 'LiveTV'
                                if not description:
                                    if not subtitle:
                                        description = showtitle  
                                    else:
                                        description = subtitle

                                #Parse the category of the program
                                movie = False
                                genre = 'Unknown'
                                categories = ''
                                categoryList = elem.findall("category")
                                for cat in categoryList:
                                    categories += ', ' + cat.text
                                    if (cat.text).lower() == 'movie':
                                        movie = True
                                        genre = cat.text
                                    elif (cat.text).lower() == 'tvshow':
                                        genre = cat.text
                                    elif (cat.text).lower() == 'sports':
                                        genre = cat.text
                                    elif (cat.text).lower() == 'children':
                                        genre = 'Kids'
                                    elif (cat.text).lower() == 'kids':
                                        genre = cat.text
                                    elif (cat.text).lower() == 'news':
                                        genre = cat.text
                                    elif (cat.text).lower() == 'comedy':
                                        genre = cat.text
                                    elif (cat.text).lower() == 'drama':
                                        genre = cat.text
                                
                                #Trim prepended comma and space (considered storing all categories, but one is ok for now)
                                categories = categories[2:]                           
                                #If the movie flag was set, it should override the rest (ex: comedy and movie sometimes come together)
                                if movie == True:
                                    type = 'movie'
                                else:
                                    type = 'tvshow'
                                        
                                # todo improve v-chip, mpaa ratings
                                HD = False
                                for HDLst in elem.findall('video'):
                                    if HDLst.find('quality').text == 'HDTV':
                                        HD = True
                                        break
                                    
                                Stars = 0.0
                                for StarLst in elem.findall('star-rating'):
                                    Stars = convert_to_stars(convert_to_float((StarLst.find('value').text)))
                                    break    

                                rating = 'NR'
                                for ratLst in elem.findall('rating'):
                                    rating = self.cleanRating(StarLst.find('value'))
                                    break

                                CC = False
                                subtitles = elem.findtext("subtitles")
                                if subtitles:           
                                    CC = True
                                    
                                #filter unwanted id querying by title
                                if showtitle == ('Paid Programming') or subtitle == ('Paid Programming') or description == ('Paid Programming'):
                                    ignoreParse = True
                                else:
                                    ignoreParse = False
                                   
                                now = datetime.datetime.now() 
                                if setting3 in ['ptvlguide']:
                                    stopDate = self.parseUTCXMLTVDate(elem.get('stop'))
                                    startDate = self.parseUTCXMLTVDate(elem.get('start'))
                                else:
                                    stopDate = self.parseXMLTVDate(elem.get('stop'), offset)
                                    startDate = self.parseXMLTVDate(elem.get('start'), offset)
                                
                                #skip old shows that have already ended
                                if now > stopDate:
                                    continue
                                
                                #adjust the duration of the current show
                                if now > startDate and now <= stopDate:
                                    try:
                                        dur = ((stopDate - startDate).seconds)
                                    except Exception,e:
                                        dur = 3600  #60 minute default
                                        
                                #use the full duration for an upcoming show
                                if now < startDate:
                                    try:
                                        dur = (stopDate - startDate).seconds
                                    except Exception,e:
                                        dur = 3600  #60 minute default
                                                            
                                if type == 'tvshow' and dur == 10800:
                                    type = 'movie'
                                       
                                #Enable Enhanced Parsing for current and future shows only
                                if ignoreParse == False:   
                                    if (((now > startDate and now <= stopDate) or (now < startDate))):  
                                        
                                        if type == 'movie':
                                            try:
                                                year = elem.findtext('date')[0:4]
                                            except:
                                                year = 0      
                                        else:
                                            year = 0
                                            
                                        year, title, showtitle = getTitleYear(showtitle, year)            
                                        # if type == 'tvshow' and ENHANCED_DATA == True:
                                            # #Decipher the TVDB ID by using the Zap2it ID in dd_progid
                                            # episodeNumList = elem.findall("episode-num") 
                                            # for epNum in episodeNumList:
                                                # if epNum.attrib["system"] == 'dd_progid':
                                                    # dd_progid = epNum.text
                                            
                                            #The Zap2it ID is the first part of the string delimited by the dot
                                            #  Ex: <episode-num system="dd_progid">MV00044257.0000</episode-num>
                                            
                                            # dd_progid = dd_progid.split('.',1)[0]
                                            # id = self.getTVDBIDbyZap2it(dd_progid)

                                            # #Find Episode info by air date.
                                            # if id != 0:
                                                # #Date element holds the original air date of the program
                                                # airdateStr = elem.findtext('date')
                                                # if airdateStr != None:
                                                    # self.log('buildLiveTVFileList, tvdbid by airdate')
                                                    # try:
                                                        # #Change date format into the byAirDate lookup format (YYYY-MM-DD)
                                                        # t = time.strptime(airdateStr, '%Y%m%d')
                                                        # airDateTime = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
                                                        # airdate = airDateTime.strftime('%Y-%m-%d')
                                                        # #Only way to get a unique lookup is to use TVDB ID and the airdate of the episode
                                                        # episode = ET.fromstring(self.tvdbAPI.getEpisodeByAirdate(id, airdate))
                                                        # episode = episode.find("Episode")
                                                        # seasonNumber = episode.findtext("SeasonNumber")
                                                        # episodeNumber = episode.findtext("EpisodeNumber")
                                                        # episodeDesc = episode.findtext("Overview")
                                                        # episodeName = episode.findtext("EpisodeName")
                                                        # try:
                                                            # int(seasonNumber)
                                                            # int(episodeNumber)
                                                        # except:
                                                            # seasonNumber = 0
                                                            # episodeNumber = 0
                                                            
                                                        # if seasonNumber > 0:
                                                            # seasonNumber = '%02d' % int(seasonNumber)
                                                        
                                                        # if episodeNumber > 0:
                                                            # episodeNumber = '%02d' % int(episodeNumber)
                                                    # except Exception,e:
                                                        # pass       

                                #Read the "new" boolean for this program
                                if elem.find("new") != None:
                                    playcount = 0
                                elif "*" in showtitle:
                                    playcount = 0
                                    showtitle = showtitle.split(" *")[0]
                                elif '(n)' in description:
                                    playcount = 0
                                elif '(repeat)' in description:
                                    playcount = 1
                                else:
                                    playcount = 1                        

                                if type == 'tvshow':
                                    episodetitle = (('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'x' + ('0' if episodeNumber < 10 else '') + str(episodeNumber) + ' - '+ (subtitle)).replace('  ',' ')
                                    if str(episodetitle[0:5]) == '00x00':
                                        episodetitle = episodetitle.split("- ", 1)[-1]
                                    subtitle = episodetitle
                                    
                                GenreLiveID = [genre,type,id,thumburl,False,playcount,rating, HD, CC, Stars]
                                tmpstr = self.makeTMPSTR(dur, showtitle, subtitle, description, GenreLiveID, setting2, startDate)
                                showList.append(tmpstr)
                                showcount += dur

                                if self.background == False:
                                    self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding %s Videos" % str(showcount/60/60))
                    root.clear()   
                except:
                    pass
            f.close()                   
            if showcount == 0:
                self.log('Unable to find xmltv data for ' + setting1)
        except Exception,e:
            self.log("fillLiveTV Failed!" + str(e), xbmc.LOGERROR)
        return showList
        
            
    def fillLiveTVPVR(self, setting1, setting2, setting3, setting4, chname, limit):
        self.log("fillLiveTVPVR")
        showList = []
        showcount = 0
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetBroadcasts","params":{"channelid":%s,"properties":["title","plot","plotoutline","starttime","endtime","runtime","genre","episodename","episodenum","episodepart","firstaired","hastimer","parentalrating","thumbnail","rating"]}, "id": 1}' % setting1)
        json_folder_detail = self.sendJSON(json_query)
        detail = re.compile("{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        now = self.parsePVRDate((str(datetime.datetime.utcnow())).split(".")[0])
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding LiveTV, parsing " + chname)

        try:
            for f in detail:
                if self.threadPause() == False:
                    del showList[:]
                    return
                    
                titles = re.search('"title" *: *"(.*?)"', f)
                if titles and len(titles.group(1)) > 0:
                    showtitle = titles.group(1)
                else:
                    try:
                        labels = re.search('"label" *: *"(.*?)"', f)
                        showtitle = labels.group(1)
                    except:
                        showtitle = chname
                                    
                if showtitle:
                    startDates = re.search('"starttime" *: *"(.*?)",', f)
                    stopDates = re.search('"endtime" *: *"(.*?)",', f)
                    id = 0
                    seasonNumber = 0
                    episodeNumber = 0
                    hd = False
                    cc = False
                    
                    if startDates and len(startDates.group(1)) > 0 and stopDates and len(stopDates.group(1)) > 0:
                        startDate = self.parsePVRDate(startDates.group(1))
                        stopDate = self.parsePVRDate(stopDates.group(1))

                        if now > stopDate:
                            continue

                        runtimes = re.search('"runtime" *: *"(.*?)",', f)
                        #adjust the duration of the current show
                        if now > startDate and now <= stopDate:
                            if runtimes and len(runtimes.group(1)) > 0:
                                dur = int(runtimes.group(1)) * 60
                            else:
                                dur = int((stopDate - startDate).seconds)

                        #use the full duration for an upcoming show
                        if now < startDate:
                            if runtimes:
                                dur = int(runtimes.group(1)) * 60
                            else:
                                dur = ((stopDate - startDate).seconds)   
                 
                        years = re.search('"year" *: *([\d.]*\d+)', f)
                        # if possible find year by title
                        try:
                            year = int(years.group(1))
                        except:
                            year = 0
                        
                        ratings = re.search('"parentalrating" *: *"(.*?)"', f)   
                        if ratings != None and len(ratings.group(1)) > 0:
                            rating = self.cleanRating(ratings.group(1))
                        else:
                            rating = 'NR'
                            
                        starss = re.search('"rating" *: *"(.*?)"', f)   
                        if starss != None and len(starss.group(1)) > 0:
                            stars = float(starss.group(1))
                        else:
                            stars = 0.0

                        movie = False
                        genres = re.search('"genre" *: *"(.*?)",', f)
                        if genres and len(genres.group(1)) > 0:
                            genre = genres.group(1)
                            if genre.lower() == 'movie':
                                movie = True
                        else:
                            genre = 'Unknown'
                            
                        tvtypes = ['Episodic','Series','Sports','News','Paid Programming']
                        if dur >= 7200 and genre not in tvtypes:
                            movie = True
                            
                        if movie == True:
                            type = 'movie'
                        else:
                            type = 'tvshow'

                        try:
                            test = showtitle.split(" *")[1]
                            showtitle = showtitle.split(" *")[0]
                            playcount = 0
                        except Exception,e:
                            playcount = 1
                            pass

                        plots = re.search('"plot" *: *"(.*?)"', f)            
                        descriptions = re.search('"description" *: *"(.*?)",', f)
                        plotoutlines = re.search('"plotoutline" *: *"(.*?)",', f)
                        if plots and len(plots.group(1)) > 0:
                            theplot = (plots.group(1)).replace('\\','').replace('\n','')
                        elif descriptions and len(descriptions.group(1)) > 0:
                            theplot = (descriptions.group(1)).replace('\\','').replace('\n','')
                        elif plotoutlines and len(plotoutlines.group(1)) > 0:
                            theplot = (plotoutlines.group(1)).replace('\\','').replace('\n','')
                        else:
                            theplot = (titles.group(1)).replace('\\','').replace('\n','')
                        description = theplot
                        thumbs = re.search('"thumbnail" *: *"(.*?)"', f)
                        if thumbs and len(thumbs.group(1)) > 0:
                            thumburl = encodeString(thumbs.group(1))
                        else:
                            thumburl = 0
                            
                        # if type == 'tvshow':
                            # episodenames = re.search('"episodename" *: *"(.*?)"', f)
                            # if episodenames and len(episodenames) > 0:
                                # episodetitle = episodenames.group(1)
                            # else:
                                # episodetitle = 'LiveTV'
                                
                            # episodenums = re.search('"episodenum" *: *"(.*?)"', f)
                            # if episodenums and len(episodenums) > 0:
                                # episodenum = episodenums.group(1) 
                            # else:
                                # episodenum = 0 
                                
                            # episodeparts = re.search('"episodepart" *: *"(.*?)"', f)
                            # if episodeparts and len(episodeparts) > 0:
                                # episodepart = episodeparts.group(1)
                            # else:
                                # episodepart = 0 
                        # else:
                            # subtitle = 'LiveTV'

                        episodetitle = 'LiveTV'
                        subtitle = 'LiveTV'
                        #filter unwanted ids by title
                        if showtitle == ('Paid Programming') or description == ('Paid Programming'):
                            ignoreParse = True
                        else:
                            ignoreParse = False
                                                
                        #Enable Enhanced Parsing
                        if ignoreParse == False:
                            if (((now > startDate and now <= stopDate) or (now < startDate))):
                                
                                if subtitle == 'LiveTV':
                                    tagline = ''     
                                year, title, showtitle = getTitleYear(showtitle, year) 
                                
                        if seasonNumber > 0:
                            seasonNumber = '%02d' % int(seasonNumber)
                        
                        if episodeNumber > 0:
                            episodeNumber = '%02d' % int(episodeNumber)

                        if type == 'tvshow':
                            episodetitle = (('0' if seasonNumber < 10 else '') + str(seasonNumber) + 'x' + ('0' if episodeNumber < 10 else '') + str(episodeNumber) + ' - '+ (subtitle)).replace('  ',' ')
                            if str(episodetitle[0:5]) == '00x00':
                                episodetitle = episodetitle.split("- ", 1)[-1]
                            subtitle = episodetitle
                         
                        GenreLiveID = [genre,type,id,thumburl,False,playcount,rating,hd,cc,stars]
                        tmpstr = self.makeTMPSTR(dur, showtitle, subtitle, description, GenreLiveID, setting2, startDate)
                        showList.append(tmpstr)
                        showcount += dur
                        
                        if self.background == False:
                            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding %s Videos" % str(showcount/60/60))
                            
                        if showcount >= limit:
                            break
        
            if showcount == 0:
                self.log('Unable to find pvr guidedata for ' + setting1)
        except Exception,e:
            self.log("fillLiveTVPVR Failed!" + str(e), xbmc.LOGERROR) 
            pass
        return showList

        
    def buildInternetTVFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log('buildInternetTVFileList')
        showList = []
        showcount = 0
        dur = 0
        
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding InternetTV, parsing " + str(setting3))

        title = setting3
        description = setting4
        if not description:
            description = title
        # setting2 = (tidy(setting2)).replace(',', '')
        if setting1 != '':
            dur = setting1
        else:
            dur = 5400  #90 minute default
                
        GenreLiveID = ['Unknown','other',0,0,False,1,'NR',False, False, 0.0]
        tmpstr = self.makeTMPSTR(dur, title, "InternetTV", description, GenreLiveID, setting2)
        for i in range(limit):
            showList.append(tmpstr)
        return showList

        
    def createYoutubeFilelist(self, setting1, setting2, setting3, setting4, limit):
        self.log("createYoutubeFilelist")
        showList = []
        showcount = 0
        self.YT_VideoCount = 0
        self.YT_showList = []
        YTMSG = setting1
        if self.youtube_player_ok() != False:
            limit = int(limit)
            # if setting2 == '1' or setting2 == '3' or setting2 == '4':
            if setting2 == '1':
                YTMSG = 'Channel ' + setting1
                showList = self.getYoutubeVideos(1, setting1, '', limit, YTMSG)
            elif setting2 == '2':
                YTMSG = 'Playlist ' + setting1
                showList = self.getYoutubeVideos(2, setting1, '', limit, YTMSG)
            elif setting2 == '5':
                YTMSG = 'Search Querys'
                showList = self.getYoutubeVideos(5, setting1, '', limit, YTMSG)
            elif setting2 == '7':
                YTMSG = 'MultiTube Playlists'
                showList = self.BuildMultiYoutubeChannelNetwork(setting1, setting2, setting3, setting4, limit)
            elif setting2 == '8':
                YTMSG = 'MultiTube Channels'
                showList = self.BuildMultiYoutubeChannelNetwork(setting1, setting2, setting3, setting4, limit)
            elif setting2 == '31':
                YTMSG = 'Seasons Channel'
                showList = self.BuildseasonalYoutubeChannel(setting1, setting2, setting3, setting4, limit)    
        return showList

        
    def BuildseasonalYoutubeChannel(self, setting1, setting2, setting3, setting4, limit):
        self.log("BuildseasonalYoutubeChannel")
        tmpstr = ''
        showList = []
        linesLST = []
        genre_filter = [setting1.lower()]
        Playlist_List = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/youtube_playlists_networks.ini'
        linesLST = read_url_cached(Playlist_List, return_type='readlines')
        if linesLST:
            for i in range(len(linesLST)):
                try:
                    line = str(linesLST[i]).replace("\n","").replace('""',"")
                    line = line.split("|")
                
                    #If List Formatting is bad return
                    if len(line) == 7:  
                        genre = line[0]
                        chtype = line[1]
                        setting1 = (line[2]).replace(",","|")
                        setting2 = line[3]
                        setting3 = line[4]
                        setting4 = line[5]
                        channel_name = line[6]
                        CHname = channel_name
                        if genre.lower() in genre_filter:
                            channelList = setting1.split('|')              
                            for n in range(len(channelList)):
                                tmpstr = self.createYoutubeFilelist(channelList[n], '2', setting3, setting4, limit)
                                showList.extend(tmpstr) 
                except:
                    pass
        # cleanup   
        del linesLST[:]
        return showList
    
    
    def BuildMultiYoutubeChannelNetwork(self, setting1, setting2, setting3, setting4, limit):
        self.log("BuildMultiYoutubeChannelNetwork")
        tmpstr = ''
        showList = []  
        channelList = setting1.split('|')
        if setting2 == '7':
            for n in range(len(channelList)):
                Pluginvalid = self.youtube_ok(channelList[n], '2')
                if Pluginvalid != False:
                    self.YT_VideoCount = 0
                    nlimit = int(limit/len(channelList))
                    tmpstr = self.createYoutubeFilelist(channelList[n], '2', setting3, setting4, nlimit)
                    showList.extend(tmpstr)     
        else:
            for n in range(len(channelList)):
                Pluginvalid = self.youtube_ok(channelList[n], '1')
                if Pluginvalid != False:
                    self.YT_VideoCount = 0
                    nlimit = int(limit/len(channelList))
                    tmpstr = self.createYoutubeFilelist(channelList[n], '1', setting3, setting4, nlimit)
                    showList.extend(tmpstr)
        random.shuffle(showList)
        return showList[:limit]
    
    
    def getYoutubeDuration(self, YTID):
        self.log('getYoutubeDuration')
        return(self.getYoutubeMeta(YTID))[2]
    
    
    def parseYoutubeDuration(self, duration):
        try:
            dur = 0
            """ Parse and prettify duration from youtube duration format """
            DURATION_REGEX = r'P(?P<days>[0-9]+D)?T(?P<hours>[0-9]+H)?(?P<minutes>[0-9]+M)?(?P<seconds>[0-9]+S)?'
            NON_DECIMAL = re.compile(r'[^\d]+')
            duration_dict = re.search(DURATION_REGEX, duration).groupdict()
            converted_dict = {}
            # convert all values to ints, remove nones
            for a, x in duration_dict.iteritems():
                if x is not None:
                    converted_dict[a] = int(NON_DECIMAL.sub('', x))
            x = time.strptime(str(timedelta(**converted_dict)).split(',')[0],'%H:%M:%S')
            dur = int(self.__total_seconds__(datetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec)))
            self.log('parseYoutubeDuration, dur = ' + str(dur))
        except Exception,e:
            pass
        return dur
    
    
    def getVimeoMeta(self, VMID):
        self.log('getVimeoMeta')
        api = 'http://vimeo.com/api/v2/video/%s.xml' % VMID
        title = ''
        description = ''
        duration = 0
        thumburl = 0
        try:
            dom = parseString(read_url_cached(api))
            xmltitle = dom.getElementsByTagName('title')[0].toxml()
            title = xmltitle.replace('<title>','').replace('</title>','')
            xmldescription = dom.getElementsByTagName('description')[0].toxml()
            description = xmldescription.replace('<description>','').replace('</description>','')
            xmlduration = dom.getElementsByTagName('duration')[0].toxml()
            duration = int(xmlduration.replace('<duration>','').replace('</duration>',''))
            thumbnail_large = dom.getElementsByTagName('thumbnail_large')[0].toxml()
            thumburl = thumbnail_large.replace('<thumbnail_large>','').replace('</thumbnail_large>','')
        except:
            pass
        return title, description, duration, thumburl

        
    def getYoutubeMeta(self, YTID):
        self.log('getYoutubeMeta ' + YTID)
        try:
            YT_URL_Video = ('https://www.googleapis.com/youtube/v3/videos?key=%s&id=%s&part=snippet,id,statistics,contentDetails' % (YT_API_KEY, YTID))
            detail = re.compile("},(.*?)}", re.DOTALL ).findall(read_url_cached(YT_URL_Video))
            title = ''
            description = ''
            thumbnail = ''
            duration = 0
            Chname = ''
            Chcat = '31'
            for f in detail:
                items = re.search('"items" *:', f)
                titles = re.search('"title" *: *"(.*?)",', f)
                descriptions = re.search('"description" *: *"(.*?)",', f)
                durations = re.search('"duration" *: *"(.*?)",', f)
                thumbnails = re.search('"url" *: *"(.*?)",', f)
                Chnames = re.search('"channelTitle" *: *"(.*?)",', f)
                Chcats = re.search('"categoryId" *: *"(.*?)",', f)

                if durations:
                    duration = durations.group(1)
                    duration = self.parseYoutubeDuration(duration)
                if Chnames:
                    Chname = Chnames.group(1)
                if Chcats:
                    Chcat = Chcats.group(1)
                    
                if items:
                    if titles:
                        title = titles.group(1)
                    if descriptions:
                        description = descriptions.group(1)
                    if thumbnails:
                        thumbnail = thumbnails.group(1)
            if title:
                if not description:
                    description = title
                    
            if Chcat and len(Chcat) > 0:                        
                cats = {0 : '',
                    1 : 'Action & Adventure',
                    2 : 'Animation & Cartoons',
                    3 : 'Classic TV',
                    4 : 'Comedy',
                    5: 'Drama',
                    6 : 'Home & Garden',
                    7 : 'News',
                    8 : 'Reality & Game Shows',
                    9 : 'Science & Tech',
                    10 : 'Science Fiction',
                    11 : 'Soaps',
                    13 : 'Sports',
                    14 : 'Travel',
                    16 : 'Entertainment',
                    17 : 'Documentary',
                    20 : 'Nature',
                    21 : 'Beauty & Fashion',
                    23 : 'Food',
                    24 : 'Gaming',
                    25 : 'Health & Fitness',
                    26 : 'Learning & Education',
                    27 : 'Foreign Language',}
                try:
                    Genre = cats[int(Chcat)]
                except:
                    Genre = 'Unknown'
                    
                self.log("getYoutubeMeta, return")
                return [title, description, duration, thumbnail, Chname, Genre]
        except Exception,e:
            self.log('getYoutubeMeta, Failed! ' + str(e), xbmc.LOGERROR)

            
    def getYoutubeUserID(self, YTid):
        self.log("getYoutubeUserID, IN = " + YTid)
        YT_ID = 'UC'
        try:
            region = 'US' #todo
            lang = xbmc.getLanguage(xbmc.ISO_639_1)
            youtubeApiUrl = 'https://www.googleapis.com/youtube/v3/'
            youtubeChannelsApiUrl = (youtubeApiUrl + 'channels?key=%s&chart=mostPopular&regionCode=%s&hl=%s&' % (YT_API_KEY, region, lang))
            requestParametersChannelId = (youtubeChannelsApiUrl + 'forUsername=%s&part=id' % (YTid))
            f = read_url_cached(requestParametersChannelId)
            YT_IDS = re.search('"id" *: *"(.*?)"', f)
            if YT_IDS:
                YT_ID = YT_IDS.group(1)
            self.log("getYoutubeUserID, OUT = " + YT_ID)
        except Exception,e:
            self.log('getYoutubeUserID, Failed! ' + str(e), xbmc.LOGERROR)
        return YT_ID
            
            
    def getYoutubeVideos(self, YT_Type, YT_ID, YT_NextPG, limit, YTMSG):
        self.log("getYoutubeVideos, YT_Type = " + str(YT_Type) + ', YT_ID = ' + YT_ID) 
        region = 'US' #todo
        lang = xbmc.getLanguage(xbmc.ISO_639_1)
        Last_YT_NextPG = YT_NextPG      
        youtubeApiUrl = 'https://www.googleapis.com/youtube/v3/'
        youtubeChannelsApiUrl = (youtubeApiUrl + 'channels?key=%s&chart=mostPopular&regionCode=%s&hl=%s&' % (YT_API_KEY, region, lang))
        youtubeSearchApiUrl = (youtubeApiUrl + 'search?key=%s&chart=mostPopular&regionCode=%s&hl=%s&' % (YT_API_KEY, region, lang))
        youtubePlaylistApiUrl = (youtubeApiUrl + 'playlistItems?key=%s&chart=mostPopular&regionCode=%s&hl=%s&' % (YT_API_KEY, region, lang))
        requestChannelVideosInfo = (youtubeSearchApiUrl + 'channelId=%s&part=id&order=date&pageToken=%s&maxResults=50' % (YT_ID, YT_NextPG))
        requestPlaylistInfo = (youtubePlaylistApiUrl+ 'part=snippet&maxResults=50&playlistId=%s&pageToken=%s' % (YT_ID, YT_NextPG))
    
        if YT_Type == 5:
            try:
                safesearch, YT_ID = YT_ID.split('|')
            except:
                safesearch = 'none'
            requestSearchVideosInfo = (youtubeSearchApiUrl + 'safeSearch=%s&q=%s&part=snippet&order=date&pageToken=%s&maxResults=50' % (safesearch.lower(), YT_ID.replace(' ','%20'), YT_NextPG))
            
    # https://www.googleapis.com/youtube/v3/search?part=snippet&q=movies&type=channel&key=AIzaSyAnwpqhAmdRShnEHnxLiOUjymHlG4ecE7c movie channels
    # https://www.googleapis.com/youtube/v3/playlists?part=snippet&channelId=UCczhp4wznQWonO7Pb8HQ2MQ&key=AIzaSyAnwpqhAmdRShnEHnxLiOUjymHlG4ecE7c
    
        if YT_Type == 1:
            if YT_ID[0:2] != 'UC':
                YT_ID = self.getYoutubeUserID(YT_ID)
                return self.getYoutubeVideos(YT_Type, YT_ID, YT_NextPG, limit, YTMSG)  
            else:
                YT_URL_Search = requestChannelVideosInfo
                self.log("getYoutubeVideos, requestChannelVideosInfo = " + YT_URL_Search) 
        elif YT_Type == 2:
            YT_URL_Search = requestPlaylistInfo
            self.log("getYoutubeVideos, requestPlaylistInfo = " + YT_URL_Search) 
            
        elif YT_Type == 5:
            YT_URL_Search = requestSearchVideosInfo
            self.log("getYoutubeVideos, requestSearchVideosInfo = " + YT_URL_Search) 
            
        try:
            detail = re.compile( "{(.*?)}", re.DOTALL ).findall(read_url_cached(YT_URL_Search))
            if self.background == False:
                self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding Youtube, parsing " + str(YTMSG))     
            
            for f in detail:
                if self.threadPause() == False:
                    del self.YT_showList[:]
                    break
                try:
                    VidIDS = re.search('"videoId" *: *"(.*?)"', f)
                    YT_NextPGS = re.search('"nextPageToken" *: *"(.*?)"', f)
                    if YT_NextPGS:
                        YT_NextPG = YT_NextPGS.group(1)
                        
                    if VidIDS:
                        VidID = VidIDS.group(1)
                        YT_Meta = self.getYoutubeMeta(VidID)

                        if YT_Meta and YT_Meta[2] > 0: 
                            try:
                                Genre = cats[YT_Meta[5]]
                            except:
                                Genre = 'Unknown' 
                                
                            GenreLiveID = [Genre,'youtube',0,VidID,False,1,'NR',False, False, 0.0]
                            tmpstr = self.makeTMPSTR(YT_Meta[2], YT_Meta[0], "Youtube - " + YT_Meta[4], YT_Meta[1], GenreLiveID, self.youtube_player_ok() + VidID)   
                            self.log("createYoutubeFilelist, CHANNEL: " + str(self.settingChannel) + ", " + YT_Meta[0] + "  DUR: " + str(YT_Meta[2]))
                            self.YT_showList.append(tmpstr)
                            self.YT_VideoCount += 1
                            
                            if self.background == False:
                                self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding %s Videos" % str(self.YT_VideoCount))

                        if self.YT_VideoCount >= limit:
                            return self.YT_showList
                except:
                    pass
        except Exception,e:
            self.log('getYoutubeVideos, Failed!, ' + str(e))
                        
        if YT_NextPG == Last_YT_NextPG:
            return self.YT_showList
        else:
            if YT_NextPG and self.YT_VideoCount < limit:
                self.YT_showList += self.getYoutubeVideos(YT_Type, YT_ID, YT_NextPG, limit, YTMSG)
        return self.YT_showList
        
    
    def createRSSFileList(self, setting1, setting2, setting3, setting4, limit):
        self.log("createRSSFileList")
        fileList = []
        filecount = 0        
        self.youtube_player = self.youtube_player_ok()
        feed = feedparser.parse(setting1)
        
        for i in range(len(feed['entries'])):   
            if self.threadPause() == False:
                del fileList[:]
                break
            try:
                showtitle = feed.channel.title
                eptitle = feed.entries[i].title
                
                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding RSS, parsing " + showtitle)
                    
                # if 'author_detail' in feed.entries[i]:
                    # studio = feed.entries[i].author_detail['name']  
                # elif 'itunes:author' in feed.entries[i]:
                    # studio = feed.entries[i]['author']
                # else:
                    # self.log("createRSSFileList, Invalid author_detail")  

                try:
                    # todo parse itune:image
                    if 'media_thumbnail' in feed.entries[i]:
                        thumburl = encodeString(feed.entries[i].media_thumbnail[0]['url'])       
                    elif 'itunes:image' in feed.entries[i]:
                        thumburl = encodeString(feed.entries[i].itunes_image[0]['url'])
                    else:
                        raise Exception()
                except:
                    thumburl = 0
                    
                try:
                    epdesc = feed.channel.subtitle
                except Exception,e:
                    epdesc = ''
                
                if not epdesc:
                    epdesc = feed.entries[i]['subtitle']
                if not epdesc:
                    if feed.entries[i].summary_detail.value:
                        epdesc = feed.entries[i]['summary_detail']['value']
                    else:
                        epdesc = feed.entries[i]['blip_puredescription']      
                if not epdesc:
                    epdesc = showtitle + " - " + eptitle

                if 'media_content' in feed.entries[i]:
                    url = feed.entries[i].media_content[0]['url']
                else:
                    url = feed.entries[i].links[1]['href']
                
                try:
                    runtimex = feed.entries[i]['itunes_duration']
                except Exception,e:
                    runtimex = 0
                if runtimex == 0:
                    try:
                        runtimex = feed.entries[i]['blip_runtime']
                    except Exception,e:
                        runtimex = 0
                self.log("createRSSFileList, runtimex = " + str(runtimex)) 
                
                if feed.channel.has_key("tags"):
                    genre = feed.channel.tags[0]['term']
                    genre = uni(genre)
                else:
                    genre = "Unknown"

                try:
                    time = (str(feed.entries[i].published_parsed)).replace("time.struct_time", "")                        
                    showseason = [word for word in time.split() if word.startswith('tm_mon=')]
                    showseason = str(showseason)
                    showseason = showseason.replace("['tm_mon=", "")
                    showseason = showseason.replace(",']", "")
                    showepisodenum = [word for word in time.split() if word.startswith('tm_mday=')]
                    showepisodenum = str(showepisodenum)
                    showepisodenum = showepisodenum.replace("['tm_mday=", "")
                    showepisodenum = showepisodenum.replace(",']", "")
                    showepisodenuma = [word for word in time.split() if word.startswith('tm_hour=')]
                    showepisodenuma = str(showepisodenuma)
                    showepisodenuma = showepisodenuma.replace("['tm_hour=", "")
                    showepisodenuma = showepisodenuma.replace(",']", "")  
                    try:
                        hours, minutes, seconds = map(int, runtimex.split(':'))
                    except ValueError:
                        hours = 0
                        minutes, seconds = map(int, runtimex.split(':'))
                    runtime = (hours*3600) + (minutes*60) + seconds                    
                    self.log("createRSSFileList, runtime = " + str(runtime)) 
                except Exception,e:
                    pass
                
                if runtime == 0:
                    runtime = 800
                duration = int(runtime)
                url = url.replace("&amp;amp;feature=youtube_gdata", "").replace("http://www.youtube.com/watch?hd=1&v=", self.youtube_player).replace("http://www.youtube.com/watch?v=", self.youtube_player)
                GenreLiveID = [genre,'rss',0,thumburl,False,1,'NR',False, False, 0.0]
                tmpstr = self.makeTMPSTR(duration, eptitle, "RSS - " + showtitle, epdesc, GenreLiveID, url)
                fileList.append(tmpstr)
                filecount += 1
                                    
                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding %s Videos" % str(filecount))
                
                if filecount > limit:
                    break
            except Exception,e:
                pass
        return fileList
     
     
    def MusicVideos(self, setting1, setting2, setting3, setting4, limit):
        self.log("MusicVideos")
        showList = []
        if setting1 == '1':
            self.log("MusicVideos - LastFM")
            msg_type = "Last.FM"
            PluginCHK = self.youtube_player_ok()
            if PluginCHK != False:
                showList = self.lastFM(setting1, setting2, setting3, setting4, limit)
        elif setting1 == '2':
            self.log("MusicVideos - MyMusicTV")
            PluginCHK = self.plugin_ok('plugin.video.my_music_tv')
            if PluginCHK != False:
                msg_type = "My MusicTV"
                showList = self.myMusicTV(setting1, setting2, setting3, setting4, limit)             
        return showList
           

    def myMusicTV(self, setting1, setting2, setting3, setting4, limit):
        self.log("myMusicTV")
        # path = xbmc.translatePath("special://profile/addon_data/plugin.video.my_music_tv/cache/plist")
        # fle = os.path.join(path,setting2+".xml.plist")
        # showcount = 0
        # YTid = 0
        # MyMusicLST = []
        # type = 'musicvideo'
        
        # try:
            # if FileAccess.exists(fle):
                # f = FileAccess.open(fle, "r")
                # lineLST = f.readlines()
                # f.close()
                
                # if self.background == False:
                    # self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding My MusicTV, parsing " + setting2)

                # for n in range(len(lineLST)):
                    # if self.threadPause() == False:
                        # del fileList[:]
                        # break
                        
                    # line = lineLST[n].replace("['",'').replace("']",'').replace('["','').replace("\n",'')
                    # line = line.split(", ")
                    # title = line[0]
                    # link = line[1].replace("'",'')
                    # link = self.cleanPlayableFile(link)
                    
                    # try:
                        # id = str(os.path.split(link)[1]).split('?url=')[1]
                        # source = str(id).split('&mode=')[1]
                        # id = str(id).split('&mode=')[0]
                    # except:
                        # pass

                    # try:
                        # artist = title.split(' - ')[0]
                        # track = title.split(' - ')[1].replace("'",'')
                    # except:
                        # artist = title
                        # track = ''
                        # pass
                    
                    # # Parse each source for duration details todo
                    # #if source == 'playVevo':
                        # #playVevo()
                    # # def playVevo(id):
                        # # opener = urllib2.build_opener()
                        # # userAgent = "Mozilla/5.0 (Windows NT 6.1; rv:30.0) Gecko/20100101 Firefox/30.0"
                        # # opener.addheaders = [('User-Agent', userAgent)]
                        # # content = opener.open("http://videoplayer.vevo.com/VideoService/AuthenticateVideo?isrc="+id).read()
                        # # content = str(json.loads(content))
                        # # print content
                        
                    # if link.startswith('plugin://plugin.video.bromix.youtube') or mediapath.startswith('plugin://plugin.video.youtube'):
                        # link = self.cleanPlayableFile(link)
                        # YTid = link.split('id=')[1]
                        # type = 'youtube'
                        
                    # tmpstr = str(300) + ',' + artist + "//" + "My MusicTV" + "//" + track + "//" + 'Music' + "////" + type+'|0|'+YTid+'|False|1|NR|' + '\n' + link
                    # GenreLiveID = [Genre,'youtube',0,VidID,False,1,'NR'] 
                    # tmpstr = self.makeTMPSTR(YT_Meta[2]), YT_Meta[0], "Youtube - " + YT_Meta[4], YT_Meta[1], GenreLiveID, self.youtube_player_ok() + VidID)     
                    # MyMusicLST.append(tmpstr)
                    # showcount += 1    
                    
                    # if showcount > limit:
                        # break

                    # if self.background == False:
                        # self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding %s Videos" % str(showcount))
            # else:
                # self.log("myMusicTV, No MyMusic plist cache found = " + str(fle))
                
        # except Exception,e:  
            # pass  
        # return MyMusicLST

        
    def isXMLTVCurrent(self, xmlfle):
        self.log("isXMLTVCurrent, xmlfle = " + xmlfle)
        isCurrent = False
        now = datetime.datetime.now()
        try:
            # local or url xmltv file
            if xmlfle[0:4] == 'http':
                f = open_url(xmlfle)
            else:
                f = FileAccess.open(xmlfle, "r")
                
            # check if xmltv uses utc time
            if xmlfle.lower() in UTC_XMLTV:                      
                offset = ((time.timezone / 3600) - 5 ) * -1     
            else:
                offset = 0
                
            context = ET.iterparse(f, events=("start", "end")) 
            context = iter(context)
            event, root = context.next()

            for event, elem in context:
                try:
                    if event == "end":
                        if elem.tag == "programme":
                            if xmlfle.lower() in ['ptvlguide']:
                                stopDate = self.parseUTCXMLTVDate(elem.get('stop'))
                                startDate = self.parseUTCXMLTVDate(elem.get('start'))
                            else:
                                stopDate = self.parseXMLTVDate(elem.get('stop'), offset)
                                startDate = self.parseXMLTVDate(elem.get('start'), offset)
                            if (((now > startDate and now <= stopDate) or (now < startDate))):
                                isCurrent = True
                except:
                    pass
        except Exception,e:
            self.log("isXMLTVCurrent, Failed!" + str(e))
        self.log("isXMLTVCurrent, isCurrent = " + str(isCurrent))
        return isCurrent
                
                
    def xmltv_ok(self, path):
        self.log("xmltv_ok, setting3 = " + path)
        xmltvValid = False
        if path[0:4] == 'http':
            self.xmlTvFile = path
            return self.url_ok(path)
        elif path.lower() in ['pvr','zap2it','scheduledirect']:
            return True
        elif path.lower() == 'ustvnow':
            if self.ustv.getXMLTV() == True:
                self.xmlTvFile = USTVXML                
            else:
                return False
        elif path.lower() == 'ptvlguide':
            self.xmlTvFile = PTVLXML
        elif path != '':
            self.xmlTvFile = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('xmltvLOC'), str(path) +'.xml'))
        
        if FileAccess.exists(self.xmlTvFile):
            xmltvValid = True            
        return xmltvValid
           

    def Valid_ok(self, url):
        self.log("Valid_ok")
        #plugin check  
        if url[0:6] == 'plugin':  
            return self.plugin_ok(url) 
        #upnp check
        elif url[0:4] == 'upnp':
            return self.upnp_ok(url) 
        #Override Check# 
        elif REAL_SETTINGS.getSetting('Override_ok') == "true":
            return True 
        #rtmp check
        elif url[0:4] == 'rtmp':
            return self.rtmpDump(url)  
        #http check     
        elif url[0:4] == 'http':
            return self.url_ok(url)
        #strm check  
        elif url[-4:] == 'strm':         
            return self.strm_ok(url)
        #pvr check
        elif url[0:3] == 'pvr':
            return True  
        #udp check
        elif url[0:3] == 'udp':
            return True  
        #rtsp check
        elif url[0:4] == 'rtsp':
            return True  
        #HDHomeRun check
        elif url[0:9] == 'hdhomerun':
            return True  
  
  
    def upnp_ok(self, url):
        self.log("upnp_ok, " + str(url))
        upnpID = (url.split('/')[2:-1])[0]
        dirs, files = xbmcvfs.listdir(os.path.join('upnp://',''))
        if upnpID in dirs:
            return True
        else:
            return False
  
  
    def strm_ok(self, url):
        self.log("strm_ok, " + str(url))
        strmValid = False
        lines = ''
        try:
            f = FileAccess.open(url, "r")
            linesLST = f.readlines()
            self.log("strm_ok.Lines = " + str(linesLST))
            f.close()

            for i in range(len(set(linesLST))):
                lines = linesLST[i]
                strmValid = self.Valid_ok(lines)
                if strmValid == True:
                    return strmValid             
        except Exception,e:
            pass
        # if strmValid == False:
            # self.writeStrm_ok(url)
        return strmValid   

        
    def writeStrm_ok(self, url, fallback=INTRO_TUBE):
        self.log("writeStrm_ok, " + str(url))
        try:
            f = FileAccess.open(url, "w")
            for i in range(len(linesLST)):
                lines = linesLST[i]
                if lines != fallback:
                    f.write(lines + '\n')
                self.log("strm_ok, file write lines = " + str(lines))
            f.write(fallback)
            f.close()         
        except Exception,e:
            pass
        

    def getDuration(self, filename):
        self.log("getDuration")
        duration = 0
        duration = self.videoParser.getVideoLength(filename)
        # if duration == 0:
            # duration = self.getffprobeLength(filename)
        return duration
        
        
    def getffprobeLength(self, filename):
        self.log("getffprobeLength")
        try:
            FFPROBE = os.path.join(xbmc.translatePath(REAL_SETTINGS.getSetting('ffmpegPath')),'ffprobe.exe')
            result = subprocess.Popen([FFPROBE, filename])
            stdout = subprocess.PIPE, stderr = subprocess.STDOUT
            duration = [x for x in result.stdout.readlines() if "Duration" in x]
        except:
            duration = 0
        return duration
      
      
    def rtmpDump(self, stream):
        self.log("rtmpDump")
        rtmpValid = False
        try:
            # OSplat = REAL_SETTINGS.getSetting('os')
            # if OSplat == '0':
                # OSpath = 'androidarm/rtmpdump'
            # elif OSplat == '1':
                # OSpath = 'android86/rtmpdump'
            # elif OSplat == '2':
                # OSpath = 'atv1linux/rtmpdump'
            # elif OSplat == '3':
                # OSpath = 'atv1stock/rtmpdump'
            # elif OSplat == '4':
                # OSpath = 'atv2/rtmpdump'
            # elif OSplat == '5':
                # OSpath = 'ios/rtmpdump'
            # elif OSplat == '6':
                # OSpath = 'linux32/rtmpdump'
            # elif OSplat == '7':
                # OSpath = 'linux64/rtmpdump'
            # elif OSplat == '8':
                # OSpath = 'mac32/rtmpdump'
            # elif OSplat == '9':
                # OSpath = 'mac64/rtmpdump'
            # elif OSplat == '10':
                # OSpath = 'pi/rtmpdump'
            # elif OSplat == '11':
                # OSpath = 'win/rtmpdump.exe'
            # elif OSplat == '12':
                # OSpath = '/usr/bin/rtmpdump'
                
            url = urllib.unquote(stream)
            RTMPDUMP = xbmc.translatePath(REAL_SETTINGS.getSetting('rtmpdumpPath'))
            self.log("RTMPDUMP = " + RTMPDUMP)
            assert os.path.isfile(RTMPDUMP)
            
            if "playpath" in url:
                url = re.sub(r'playpath',"-y playpath",url)
                self.log("playpath url = " + str(url))
                command = [RTMPDUMP, '-B 1', '-m 2', '-r', url,'-o','test.flv']
                self.log("RTMPDUMP command = " + str(command))
            else:
                command = [RTMPDUMP, '-B 1', '-m 2', '-r', url,'-o','test.flv']
                self.log("RTMPDUMP command = " + str(command))
           
            CheckRTMP = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
            output = CheckRTMP.communicate()[0]
            
            if "ERROR: RTMP_ReadPacket" in output:
                self.log("rtmpDump, ERROR: RTMP_ReadPacket")
                rtmpValid = False 
            elif "ERROR: Problem accessing the DNS." in output:
                rtmpValid = False    
                self.log("rtmpDump, ERROR: Problem accessing the DNS.")
            elif "INFO: Connected..." in output:
                self.log("rtmpDump, INFO: Connected...")
                rtmpValid = True
            else:
                self.log("rtmpDump, ERROR?: Unknown response..." + str(output))
                rtmpValid = False
        except:
            pass
        self.log("rtmpValid = " + str(rtmpValid))
        return rtmpValid
        
                
    def url_ok(self, url):
        urlValid = False
        try:
            if open_url(url):
                urlValid = True
        except urllib2.HTTPError,e:
            self.log("url_ok, ERROR: HTTP URL NOT VALID, ERROR: " + str(e))
        self.log("urlValid = " + str(urlValid))
        return self.urlValid
        

    def plugin_ok(self, plugin):
        self.log("plugin_ok, plugin = " + plugin)
        return isPlugin(plugin)
        
        
    def youtube_ok(self, YTtype, YTid):
        # todo finish youtube channel/playlist check
        if self.youtube_player_ok() != False:
            return True
            # if YTtype == 1:
                # tmpstr = self.getYoutubeVideos(YTtype, YTid, '', 1, '')  
            # elif YTtype == 2:
                # tmpstr = self.getYoutubeVideos(YTtype, YTid, '', 1, '')
            # else:
                # return True
            # if len(tmpstr) > 0:
                # return True
        # return False

        
    def youtube_player_ok(self):
        try:
            return self.youtube_player
        except:
            self.log("youtube_player_ok")
            if self.plugin_ok('plugin.video.youtube') == True:
                self.youtube_player = 'plugin://plugin.video.youtube/?action=play_video&videoid='
            else:
                self.youtube_player = False
            self.log("youtube_player_ok = " + str(self.youtube_player))
            return self.youtube_player
           

    def insertBCT(self, chtype, channel, fileList, type):
        self.log("insertBCT, channel = " + str(channel))
        GenreLiveID = ['Unknown', 'other', 0, 0, False, 1, 'NR',False, False, 0.0]
        newFileList = []
        title = ''
        description = ''
        chsetting1 = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_1')

        # Parse BCT functions
        if chtype <= 7 or chtype == 12:
            chname = self.getChannelName(chtype, chsetting1)
        else:
            chname = self.getChannelName(chtype, channel)
        
        #Bumpers
        BumperLST = []
        BumpersType = REAL_SETTINGS.getSetting("bumpers")      
        if BumpersType != "0" and type != 'movies': 
            BumperLST = self.getBumperList(BumpersType, chname)
            
            if BumperLST and len(BumperLST) > 0:
                random.shuffle(BumperLST)
        
        #Ratings
        if BumpersType!= "0" and type == 'movies' and REAL_SETTINGS.getSetting('bumperratings') == 'true':
            fileList = self.getRatingList(chtype, chname, channel, fileList)

        #3D, insert "put glasses on" for 3D and use 3D ratings if enabled. todo
        if BumpersType!= "0" and type == 'movies' and REAL_SETTINGS.getSetting('bumper3d') == 'true':
            fileList = self.get3DList(chtype, chname, channel, fileList)
            
        #Commercial
        CommercialLST = []
        CommercialsType = REAL_SETTINGS.getSetting("commercials") 
        if CommercialsType != '0' and type != 'movies':
            CommercialLST = self.getCommercialList(CommercialsType)
            
            if CommercialLST and len(CommercialLST) > 0:
                random.shuffle(CommercialLST)

        #Trailers
        TrailerLST = []
        TrailersType = REAL_SETTINGS.getSetting("trailers")
        trailersgenre = REAL_SETTINGS.getSetting("trailersgenre")
        trailersHDnetType = REAL_SETTINGS.getSetting("trailersHDnetType")
        trailerschannel = REAL_SETTINGS.getSetting("trailerschannel")

        if REAL_SETTINGS.getSetting('trailers') != '0':
            TrailerLST = self.getTrailerList(chtype, chname, TrailersType, trailersgenre, trailersHDnetType, trailerschannel)
            if TrailerLST and len(TrailerLST) > 0:
                random.shuffle(TrailerLST)

        # Inject BCTs into filelist          
        for i in range(len(fileList)):
            bctDur = 0 #todo automatic time filler (round shows to the 30/60min intervals)
            newFileList.append(fileList[i])
            if len(BumperLST) > 0:
                for n in range(int(REAL_SETTINGS.getSetting("numbumpers")) + 1):
                    tmpstr = ''
                    if self.background == False:
                        self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Bumpers")
                    Bumper = random.choice(BumperLST)#random fill Bumper per show by user selected amount
                    BumperDur, BumperMedia = Bumper.split(',')
                    BumperDur = int(BumperDur)
                    bctDur += BumperDur
                    tmpstr = self.makeTMPSTR(BumperDur, chname, 'Bumper', 'Bumper', GenreLiveID, BumperMedia)
                    newFileList.append(tmpstr)

            if len(CommercialLST) > 0:
                for n in range(int(REAL_SETTINGS.getSetting("numcommercials")) + 1): 
                    tmpstr = ''   
                    if self.background == False:
                        self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Commercials")
                    Commercial = random.choice(CommercialLST)#random fill Commercial per show by user selected amount
                    CommercialDur, CommercialMedia = Commercial.split(',')
                    CommercialDur = int(CommercialDur)
                    bctDur += CommercialDur
                    tmpstr = self.makeTMPSTR(CommercialDur, chname, 'Commercial', 'Commercial', GenreLiveID, CommercialMedia)
                    newFileList.append(tmpstr)

            if len(TrailerLST) > 0:
                for n in range(int(REAL_SETTINGS.getSetting("numtrailers")) + 1):    
                    tmpstr = ''
                    if self.background == False:
                        self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Trailers")
                    trailer = random.choice(TrailerLST)#random fill trailers per show by user selected amount
                    trailerDur, trailerMedia = trailer.split(',') #duration of trailer
                    trailerDur = int(trailerDur)
                    bctDur += trailerDur
                    tmpstr = self.makeTMPSTR(trailerDur, chname, 'Trailer', 'Trailer', GenreLiveID, trailerMedia)
                    newFileList.append(tmpstr)
        # cleanup   
        del fileList[:]
        del BumperLST[:]
        del CommercialLST[:]
        del TrailerLST[:]
        return newFileList

        
    def getBumperList(self, BumpersType, chname):
        self.log("getBumperList")
        BumperCNT = 0
        BumperLST = []
        LocalBumperLST = []
        InternetBumperLST = []
        #Local
        if BumpersType == "1":  
            self.log("getBumperList, Local - " + chname)
            PATH = REAL_SETTINGS.getSetting('bumpersfolder')
            PATH = xbmc.translatePath(os.path.join(PATH,chname,''))
            self.log("getBumperList, Local - PATH = " + PATH)
            
            if FileAccess.exists(PATH):
                try:
                    LocalFLE = ''
                    LocalBumper = ''
                    LocalLST = self.walk(PATH)

                    for i in range(len(LocalLST)):  
                        filename = xbmc.translatePath(os.path.join(PATH,((LocalLST[i])[0])))
                        duration = self.getDuration(filename)
                        if duration > 0:
                            BumperCNT += 1
                            if self.background == False:
                                self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "querying %s Local Bumpers"%str(BumperCNT))
                            LocalBumper = (str(duration) + ',' + filename)
                            LocalBumperLST.append(LocalBumper)
                    BumperLST.extend(LocalBumperLST)                
                except: 
                    pass
        #Internet
        elif BumpersType == "2":
            self.log("getBumperList - Internet")
            self.vimeo_ok = self.plugin_ok('plugin.video.vimeo')
            self.youtube_player = self.youtube_player_ok()
            duration = 15
            if self.youtube_player != False:
                try:
                    Bumper_List = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/bumpers.ini'
                    linesLST = read_url_cached(Bumper_List, return_type='readlines')
                    for i in range(len(Bumper_List)):    
                        include = False                    
                        lines = str(linesLST[i]).replace('\n','')
                        lines = lines.split('|')
                        ChannelName = lines[0]
                        BumperNumber = lines[1]
                        BumperSource = lines[2].split('_')[0]
                        BumperID = lines[2].split('_')[1]

                        if chname.lower() == ChannelName.lower():
                            if BumperSource == 'vimeo':
                                if self.vimeo_ok == True:
                                    url = 'plugin://plugin.video.vimeo/?path=/root/video&action=play_video&videoid=' + BumperID
                                    duration = (self.getVimeoMeta(BumperID))[2]
                                    if duration > 0:
                                        include = True
                            elif BumperSource == 'youtube':
                                if self.youtube_player != False:
                                    url = self.youtube_player + BumperID
                                    duration = (self.getYoutubeMeta(BumperID))[2]
                                    if duration > 0:
                                        include = True
                            if include == True:
                                BumperCNT += 1
                                if self.background == False:
                                    self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "querying %s Internet Bumpers"%str(BumperCNT))
                                InternetBumper = (str(duration) + ',' + url)
                                InternetBumperLST.append(InternetBumper)
                    BumperLST.extend(InternetBumperLST)                
                except: 
                    pass
        # cleanup   
        del LocalBumperLST[:]
        del InternetBumperLST[:]
        return BumperLST   
        
        
    def getRatingList(self, chtype, chname, channel, fileList):
        self.log("getRatingList")
        newFileList = []
        self.youtube_player = self.youtube_player_ok()
        
        if self.youtube_player != False:
            URL = self.youtube_player + 'qlRaA8tAfc0'
            Ratings = (['NR','qlRaA8tAfc0'],['R','s0UuXOKjH-w'],['NC-17','Cp40pL0OaiY'],['PG-13','lSg2vT5qQAQ'],['PG','oKrzhhKowlY'],['G','QTKEIFyT4tk'],['18','g6GjgxMtaLA'],['16','zhB_xhL_BXk'],['12','o7_AGpPMHIs'],['6','XAlKSm8D76M'],['0','_YTMglW0yk'])
    
            for i in range(len(fileList)):
                newFileList.append(fileList[i])
                lineLST = (fileList[i]).split('movie|')[1]
                mpaa = (lineLST.split('\n')[0]).split('|')[4]
                
                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Ratings: " + str(mpaa))
                             
                ID = 'qlRaA8tAfc0'
                for i in range(len(Ratings)):
                    rating = Ratings[i]        
                    if mpaa == rating[0]:
                        ID = rating[1]
                URL = self.youtube_player + ID
                dur = (self.getYoutubeMeta(ID))[2]   
                GenreLiveID = ['Unknown', 'movie', 0, 0, False, 1, mpaa,False, False, 0.0]
                tmpstr = self.makeTMPSTR(dur, chname, 'Rating', 'Rating', GenreLiveID, URL)
                newFileList.append(tmpstr)
            # cleanup   
            del fileList[:]
            return newFileList
        else:
            return fileList
        
    
    def getCommercialList(self, CommercialsType):  
        self.log("getCommercialList") 
        duration = 0
        CommercialLST = []
        AsSeenOnCommercialLST = []    
        LocalCommercialLST = []
        YoutubeCommercialLST = []
        channel = self.settingChannel

        #Youtube - As Seen On TV
        if REAL_SETTINGS.getSetting('AsSeenOn') == 'true' and CommercialsType != '0':
            self.log("getCommercialList, AsSeenOn")
            try:      
                YoutubeLST = self.createYoutubeFilelist('PL_ikfJ-FJg77ioZ9nPuhJxuMe9GKu7plT|PL_ikfJ-FJg774gky7eu8DroAqCR_COS79|PL_ikfJ-FJg75N3Gn6DjL0ZArAcfcGigLY|PL_ikfJ-FJg765O5ppOPGTpQht1LwXmck4|PL_ikfJ-FJg75wIMSXOTdq0oMKm63ucQ_H|PL_ikfJ-FJg77yht1Z6Xembod33QKUtI2Y|PL_ikfJ-FJg77PW8AJ3yk5HboSwWatCg5Z|PL_ikfJ-FJg75v4dTW6P0m4cwEE4-Oae-3|PL_ikfJ-FJg76zae4z0TX2K4i_l5Gg-Flp|PL_ikfJ-FJg74_gFvBqCfDk2E0YN8SsGS8|PL_ikfJ-FJg758W7GVeTVZ4aBAcCBda63J', '7', '100', '1', limit)
                for i in range(len(YoutubeLST)): 
                
                    if self.background == False:
                        self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding AsSeenOnTV Commercials")

                    Youtube = YoutubeLST[i]
                    duration = Youtube.split(',')[0]
                    Commercial = Youtube.split('\n', 1)[-1]
                    
                    if Commercial != '' or Commercial != None:
                        AsSeenOnCommercial = (str(duration) + ',' + Commercial)
                        AsSeenOnCommercialLST.append(AsSeenOnCommercial)
                CommercialLST.extend(AsSeenOnCommercialLST)
            except Exception,e:
                self.log("getCommercialList Failed!" + str(e), xbmc.LOGERROR)
        
        #Local
        if CommercialsType == '1':
            self.log("getCommercialList, Local") 
            PATH = REAL_SETTINGS.getSetting('commercialsfolder')
            PATH = xbmc.translatePath(os.path.join(PATH,''))
            self.log("getCommercialList, Local - PATH = " + PATH)
            
            if FileAccess.exists(PATH): 
                try:
                    LocalFLE = ''
                    LocalCommercial = ''
                    LocalLST = self.walk(PATH)
                    
                    for i in range(len(LocalLST)):    
                        if self.background == False:
                            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Local Commercials")
                        filename = xbmc.translatePath(os.path.join(PATH,LocalLST[i][0]))
                        duration = self.getDuration(filename)
                        
                        if duration == 0:
                            duration = 30
                        
                        if duration > 0:
                            LocalCommercial = (str(duration) + ',' + filename)
                            LocalCommercialLST.append(LocalCommercial)
                    
                    CommercialLST.extend(LocalCommercialLST)      
                except Exception,e:
                    self.log("getCommercialList Failed!" + str(e), xbmc.LOGERROR)
                    
        #Youtube
        elif CommercialsType == '2':
            self.log("getCommercialList, Youtube") 
            try:
                YoutubeLST = self.createYoutubeFilelist(REAL_SETTINGS.getSetting('commercialschannel'), '2', '200', '2', '200')
                
                for i in range(len(YoutubeLST)):    
                    if self.background == False:
                        self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Youtube Commercials")
                    
                    Youtube = YoutubeLST[i]
                    duration = Youtube.split(',')[0]
                    Commercial = Youtube.split('\n', 1)[-1]
                    
                    if Commercial != '' or Commercial != None:
                        YoutubeCommercial = (str(duration) + ',' + Commercial)
                        YoutubeCommercialLST.append(YoutubeCommercial)
                
                CommercialLST.extend(YoutubeCommercialLST)
            except Exception,e:
                self.log("getCommercialList Failed!" + str(e), xbmc.LOGERROR)
                
        #Internet
        elif CommercialsType == '3':
            self.log("getCommercialList, Internet") 
            CommercialLST.extend(self.InternetCommercial())
        
        # cleanup   
        del AsSeenOnCommercialLST[:]
        del LocalCommercialLST[:]
        del YoutubeCommercialLST[:]
        return CommercialLST 
   
        
    def InternetCommercial(self):
        self.log("InternetCommercial")
        if self.background == False:
            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding Internet Commercials")     
        CommercialLST = splitStringItem(getProperty("PTVL.ADVERTS")) 
        
        if len(CommercialLST) > 0:
            random.shuffle(CommercialLST)
        return CommercialLST       

    
    def getTrailerList(self, chtype, chname, TrailersType, trailersgenre, trailersHDnetType, trailerschannel):
        self.log("getTrailerList")
        duration = 0
        TrailerLST = []
        LocalTrailerLST = []
        JsonTrailerLST = []
        YoutubeTrailerLST = []
        genre = ''
        channel = self.settingChannel
        self.youtube_player = self.youtube_player_ok()
        
        if chtype == '3' or chtype == '4' or chtype == '5':
            GenreChtype = True
        else:
            GenreChtype = False

        #Local
        if TrailersType == '1': 
            PATH = REAL_SETTINGS.getSetting('trailersfolder')
            PATH = xbmc.translatePath(os.path.join(PATH,''))
            self.log("getTrailerList, Local - PATH = " + PATH)
            
            if FileAccess.exists(PATH):
                try:
                    LocalFLE = ''
                    LocalTrailer = ''
                    LocalLST = self.walk(PATH)
                    
                    for i in range(len(LocalLST)):    
                        
                        if self.background == False:
                            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Local Trailers")
                        
                        LocalFLE = LocalLST[i]
                        
                        if '-trailer' in LocalFLE:
                            duration = self.getDuration(LocalFLE)
                            
                            if duration == 0:
                                duration = 120
                        
                            if duration > 0:
                                LocalTrailer = (str(duration) + ',' + LocalFLE)
                                LocalTrailerLST.append(LocalTrailer)
                                
                    TrailerLST.extend(LocalTrailerLST)                
                except Exception,e:
                    self.log("getTrailerList Failed!" + str(e), xbmc.LOGERROR)
                    
        #XBMC Library - Local Json
        if TrailersType == '2':
            self.log("getTrailerList, Local Json")
            json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":{"properties":["genre","trailer","runtime"]}, "id": 1}')
            genre = chname
            if self.youtube_player != False:
                try:
                    json_detail = self.sendJSON(json_query)
                    self.log('getTrailerList, json_detail using cache')

                    if REAL_SETTINGS.getSetting('trailersgenre') == 'true' and GenreChtype == True:
                        JsonLST = ascii(json_detail.split("},{"))
                        match = [s for s in JsonLST if genre in s]
                        
                        for i in range(len(match)):    
                            if self.background == False:
                                self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Library Genre Trailers")
                            duration = 120
                            json = (match[i])
                            trailer = json.split(',"trailer":"',1)[-1]
                            if ')"' in trailer:
                                trailer = trailer.split(')"')[0]
                            else:
                                trailer = trailer[:-1]
                            
                            if trailer != '' or trailer != None or trailer != '"}]}':
                                if 'http://www.youtube.com/watch?hd=1&v=' in trailer:
                                    trailer = trailer.replace("http://www.youtube.com/watch?hd=1&v=", self.youtube_player).replace("http://www.youtube.com/watch?v=", self.youtube_player)
                                JsonTrailer = (str(duration) + ',' + trailer)
                                if JsonTrailer != '120,':
                                    JsonTrailerLST.append(JsonTrailer)
                        TrailerLST.extend(JsonTrailerLST)
                    else:
                        JsonLST = (json_detail.split("},{"))
                        match = [s for s in JsonLST if 'trailer' in s]
                        for i in range(len(match)):    
                            if self.background == False:
                                self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Library Trailers")
                            duration = 120
                            json = (match[i])
                            trailer = json.split(',"trailer":"',1)[-1]
                            if ')"' in trailer:
                                trailer = trailer.split(')"')[0]
                            else:
                                trailer = trailer[:-1]
                            if trailer != '' or trailer != None or trailer != '"}]}':
                                if 'http://www.youtube.com/watch?hd=1&v=' in trailer:
                                    trailer = trailer.replace("http://www.youtube.com/watch?hd=1&v=", self.youtube_player).replace("http://www.youtube.com/watch?v=", self.youtube_player)
                                JsonTrailer = (str(duration) + ',' + trailer)
                                if JsonTrailer != '120,':
                                    JsonTrailerLST.append(JsonTrailer)
                        TrailerLST.extend(JsonTrailerLST)     
                except Exception,e:
                    self.log("getTrailerList Failed!" + str(e), xbmc.LOGERROR)
                    
        #Youtube
        if TrailersType == '3':
            self.log("getTrailerList, Youtube")
            try:
                YoutubeLST = self.createYoutubeFilelist(REAL_SETTINGS.getSetting('trailerschannel'), '2', '200', '2', '200')
                
                for i in range(len(YoutubeLST)):    
                    
                    if self.background == False:
                        self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Youtube Trailers")
                    
                    Youtube = YoutubeLST[i]
                    duration = Youtube.split(',')[0]
                    trailer = Youtube.split('\n', 1)[-1]
                    
                    if trailer != '' or trailer != None:
                        YoutubeTrailer = (str(duration) + ',' + trailer)
                        YoutubeTrailerLST.append(YoutubeTrailer)
                TrailerLST.extend(YoutubeTrailerLST)
            except Exception,e:
                self.log("getTrailerList Failed!" + str(e), xbmc.LOGERROR)
                
        #Internet
        if TrailersType == '4':
            self.log("getTrailerList, Internet")
            try:   
                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(channel), "adding Internet Trailers")
                TrailerLST = self.InternetTrailer()
            except Exception,e:
                self.log("getTrailerList Failed!" + str(e), xbmc.LOGERROR)
        # cleanup   
        del LocalTrailerLST[:]
        del JsonTrailerLST[:]
        del YoutubeTrailerLST[:]
        return TrailerLST
        
      
    def InternetTrailer(self, Cinema=False):
        self.log("InternetTrailer, Cinema = " + str(Cinema))
        TrailerLST = []
        duration = 0
        youtube_plugin = self.youtube_player_ok()
        TrailersCount = 0
        
        if Cinema == 1:
            TRes = '720p'
            Ttype = 'coming_soon'
            Tlimit = 90
        elif Cinema == 2:
            TRes = '720p'
            Ttype = 'opening'
            Tlimit = 90
        else:
            TResNum = {}
            TResNum['0'] = '480p'
            TResNum['1'] = '720p'
            TResNum['2'] = '1080p'
            TRes = (TResNum[REAL_SETTINGS.getSetting('trailersResolution')])

            Ttypes = {}
            Ttypes['0'] = 'latest'
            Ttypes['1'] = 'most_watched'
            Ttypes['2'] = 'coming_soon'
            Ttype = (Ttypes[REAL_SETTINGS.getSetting('trailersHDnetType')])

            T_Limit = [15,30,90,180,270,360]
            Tlimit = T_Limit[int(REAL_SETTINGS.getSetting('trailersTitleLimit'))]
        
        try:
            InternetTrailersLST1 = []
            limit = Tlimit
            loop = int(limit/15)
            global page
            page = None
            movieLST = []
            source = Ttype
            resolution = TRes
            n = 0
            
            if source == 'latest':
                page = 1

                for i in range(loop):
                    movies, has_next_page = HDTrailers.get_latest(page=page)
                    if has_next_page:
                        page = page + 1

                        for i, movie in enumerate(movies):
                            movie_id = movie['id']
                            movieLST.append(movie_id)
                    else:
                        break

            elif source == 'most_watched':
                movies, has_next_page = HDTrailers.get_most_watched()
            elif source == 'coming_soon':
                movies, has_next_page = HDTrailers.get_coming_soon()
            elif source == 'opening':
                movies, has_next_page = HDTrailers.get_opening_this_week()

            if source != 'latest':
                for i, movie in enumerate(movies):
                    if n >= loop:
                        break
                    movie_id=movie['id']
                    movieLST.append(movie_id)
                    n += 1

            for i in range(len(movieLST)):
                movie, trailers, clips = HDTrailers.get_videos(movieLST[i])
                videos = []
                videos.extend(trailers)
                items = []

                for i, video in enumerate(videos):
                    if resolution in video.get('resolutions'):
                        source = video['source']
                        url = video['resolutions'][resolution]

                        if not 'http://www.hd-trailers.net/yahoo-redir.php' in url:
                            playable_url = HDTrailers.get_playable_url(source, url)
                            playable_url = playable_url.replace('plugin://plugin.video.youtube/?action=play_video&videoid=', youtube_plugin)
                            try:
                                tubeID = playable_url.split('videoid=')[1]
                                duration = (self.getYoutubeMeta(tubeID))[2]
                            except:
                                duration = 120
                            InternetTrailers = (str(duration) + ',' + str(playable_url))
                            TrailerLST.append(InternetTrailers)  
                            TrailersCount += 1
                            if self.background == False:
                                self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "querying %s Internet Trailers"%str(TrailersCount))
        except Exception,e:
            self.log("InternetTrailer Failed! " + str(e))
            pass
        TrailerLST = sorted_nicely(TrailerLST)
        if TrailerLST and len(TrailerLST) > 0:
            random.shuffle(TrailerLST)
        return TrailerLST
    
    
    # Adapted from Ronie's screensaver.picture.slideshow * https://github.com/XBMC-Addons/screensaver.picture.slideshow/blob/master/resources/lib/utils.py    
    def walk(self, path):     
        self.log("walk " + path)
        VIDEO_TYPES = ('.avi', '.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov', '.mkv', '.flv', '.ts', '.m2ts', '.mts', '.strm')
        video = []
        folders = []
        # multipath support
        if path.startswith('multipath://'):
            # get all paths from the multipath
            paths = path[12:-1].split('/')
            for item in paths:
                folders.append(urllib.unquote_plus(item))
        else:
            folders.append(path)
        for folder in folders:
            if FileAccess.exists(xbmc.translatePath(folder)):
                # get all files and subfolders
                dirs,files = xbmcvfs.listdir(os.path.join(folder,''))
                # natural sort
                convert = lambda text: int(text) if text.isdigit() else text
                alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
                files.sort(key=alphanum_key)
                for item in files:
                    # filter out all video
                    if os.path.splitext(item)[1].lower() in VIDEO_TYPES:
                        video.append([os.path.join(folder,item), ''])
                for item in dirs:
                    # recursively scan all subfolders
                    video += self.walk(os.path.join(folder,item,'')) # make sure paths end with a slash
        # cleanup   
        del folders[:]
        return video
        
        
    def Extras(self, setting1, setting2, setting3, setting4, channel, limit):
        self.log("Extras")
        showList = []
        if setting1.lower() == 'popcorn':
            showList = splitStringItem(getProperty("PTVL.POPCORN")) 
        elif setting1.lower() == 'cinema':  
            showList = splitStringItem(getProperty("PTVL.CINEMA"))  
        return showList

    
    #Parse Plugin, return essential information. Not tmpstr
    def PluginInfo(self, path):
        self.log("PluginInfo") 
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","properties":["genre","runtime","description"]},"id":1}' % path)
        json_folder_detail = self.sendJSON(json_query)
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
        Detail = ''
        DetailLST = []
        PluginName = os.path.split(path)[0]

        #run through each result in json return
        for f in (file_detail):
            filetype = re.search('"filetype" *: *"(.*?)"', f)
            label = re.search('"label" *: *"(.*?)"', f)
            genre = re.search('"genre" *: *"(.*?)"', f)
            runtime = re.search('"runtime" *: *([0-9]*?),', f)
            description = re.search('"description" *: *"(.*?)"', f)
            file = re.search('"file" *: *"(.*?)"', f)

            #if core values have info, proceed
            if filetype and file and label:
                filetype = filetype.group(1)
                title = (label.group(1)).replace(',',' ')
                file = file.group(1)

                try:
                    genre = genre.group(1)
                except:
                    genre = 'Unknown'
                    pass

                if genre == '':
                    genre = 'Unknown'

                try:
                    runtime = runtime.group(1)
                except:
                    runtime = 0
                    pass

                if runtime == 0 or runtime == '':
                    runtime = 1800

                try:
                    description = (description.group(1)).replace(',',' ')
                except:
                    description = PluginName
                    pass

                if description == '':
                    description = PluginName

                if title != '':
                    Detail = ((filetype + ',' + title + ',' + genre + ',' + str(runtime) + ',' + description + ',' + file)).replace(',,',',')
                    DetailLST.append(Detail)                    
        return DetailLST

        
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

                if self.background == False:
                    self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "processing rule " + str(index + 1))

                parameter = rule.runAction(action, self, parameter)
            index += 1
        
        self.runningActionChannel = 0
        self.runningActionId = 0
        return parameter


    def threadPause(self):
        if threading.activeCount() > 1:
            while self.threadPaused == True and self.myOverlay.isExiting == False:
                time.sleep(self.sleepTime)
                
            # This will fail when using config.py
            try:
                if self.myOverlay.isExiting == True:
                    self.log("IsExiting")
                    return False
            except Exception,e:
                pass
        return True


    def escapeDirJSON(self, dir_name):
        mydir = uni(dir_name)
        if (mydir.find(":")):
            mydir = mydir.replace("\\", "\\\\")
        return mydir


    def getSmartPlaylistType(self, dom):
        self.log('getSmartPlaylistType')

        try:
            pltype = dom.getElementsByTagName('smartplaylist')
            return pltype[0].attributes['type'].value
        except Exception,e:
            self.log("Unable to get the playlist type.", xbmc.LOGERROR)
            return ''

     
    def readXMLTV(self, filename):
        self.log('readXMLTV')
        self.cached_readXMLTV = []
        if len(self.cached_readXMLTV) == 0:         
            try:
                # for key in xmltv.read_channels(FileAccess.open(filename, 'r')):
                    # name = map(itemgetter(0), key['display-name'])
                    # id   = key['id']
                    # name = name[0]
                # channel = name+' : '+id
                # self.cached_readXMLTV.append(channel)
                    
                if filename[0:4] == 'http':
                    self.log("findZap2itID, filename http = " + filename)
                    f = open_url(filename)
                else:
                    self.log("findZap2itID, filename local = " + filename)
                    f = open(filename, "r")
                context = ET.iterparse(f, events=("start", "end"))
                context = iter(context)
                event, root = context.next()
                for event, elem in context:
                    if event == "end":
                        if elem.tag == "channel":
                            id = ascii(elem.get("id"))
                            for title in elem.findall('display-name'):
                                name = ascii(title.text.replace('<display-name>','').replace('</display-name>','').replace('-DT','DT').replace(' DT','DT').replace('DT','').replace('-HD','HD').replace(' HD','HD').replace('HD','').replace('-SD','SD').replace(' SD','SD').replace('SD','').replace("'",'').replace(')',''))
                                channel = name+' : '+id
                                self.cached_readXMLTV.append(channel)
                f.close()
                return self.cached_readXMLTV
            except Exception,e:
                f.close()
                self.log("readXMLTV, Failed! " + str(e))
                return ['XMLTV ERROR : IMPROPER FORMATING']

                
    def findZap2itID(self, CHname, filename):
        self.log("findZap2itID, CHname = " + CHname)
        show_busy_dialog()
        orgCHname = CHname
        CHname = CHname.upper()
        XMLTVMatchlst = []
        sorted_XMLTVMatchlst = []
        found = False
        try:
            XMLTVMatchlst = self.readXMLTV(filename)
            try:
                CHnum = int(CHname.split(' ')[0])
                CHname = (CHname.split(' ')[1]).upper()
            except:
                CHnum = 0
                pass
            
            CHname = CHname.replace('-DT','DT').replace(' DT','DT').replace('DT','').replace('-HD','HD').replace(' HD','HD').replace('HD','').replace('-SD','SD').replace(' SD','SD').replace('SD','')
            matchLST = [CHname, 'W'+CHname, CHname+'HD', CHname+'DT', str(CHnum)+' '+CHname, orgCHname.upper(), 'W'+orgCHname.upper(), orgCHname.upper()+'HD', orgCHname.upper()+'DT', str(CHnum)+' '+orgCHname.upper(), orgCHname]
            self.log("findZap2itID, Cleaned CHname = " + CHname)
            
            sorted_XMLTVMatchlst = sorted_nicely(XMLTVMatchlst)
            for n in range(len(sorted_XMLTVMatchlst)):
                try:
                    CHid = '0'
                    found = False
                    dnameID = sorted_XMLTVMatchlst[n]
                    dname = dnameID.split(' : ')[0]
                    CHid = dnameID.split(' : ')[1]

                    if dname.upper() in matchLST: 
                        found = True
                        hide_busy_dialog()
                        return orgCHname, CHid
                except:
                    hide_busy_dialog()
                    pass
                    
            if not found:
                hide_busy_dialog()
                XMLTVMatchlst = []

                for s in range(len(sorted_XMLTVMatchlst)):
                    try:
                        dnameID = sorted_XMLTVMatchlst[s]
                        dname = dnameID.split(' : ')[0]
                        CHid = dnameID.split(' : ')[1]
                                        
                        try:
                            CHid = CHid.split(', icon')[0]
                        except:
                            pass
                            
                        line = '[COLOR=blue][B]'+dname+'[/B][/COLOR] : ' + CHid
                        if dname[0:3] != 'en':
                            XMLTVMatchlst.append(line)
                    except:
                        hide_busy_dialog()
                        pass
                        
                if XMLTVMatchlst:
                    select = selectDialog(XMLTVMatchlst, 'Select matching id to [B]%s[/B]' % orgCHname, 5000)
                    if select != -1:
                        dnameID = self.cleanString(XMLTVMatchlst[select])
                        CHid = dnameID.split(' : ')[1]
                        dnameID = dnameID.split(' : ')[0]
                        return dnameID, CHid
                    else:
                        return CHname, '0'
        except Exception,e:
            hide_busy_dialog()
            self.log("findZap2itID, Failed! " + str(e))
            
            
    def ListTuning(self, type, url, Random=False):
        # todo write proper parsers for m3u,xml,plx
        self.log('ListTuning')
        show_busy_dialog()
        SortIPTVList = []
        TMPIPTVList = []
        IPTVNameList = []
        IPTVPathList = []
        lst = []
        
        try:
            if url[0:4] == 'http':
                f = force_url(url)
                lst = f.readlines()
            else:
                f = FileAccess.open(url, "r")
                lst = f.readlines()
            f.close()
        except:
            pass
                
        if len(lst) == 0:
            return 
        lst = removeStringElem(PLXlst)

        if type == 'M3U':
            TMPIPTVList = self.IPTVtuning(lst)
        elif type == 'XML':
            TMPIPTVList = self.LSTVtuning(lst)
        elif type == 'PLX':
            TMPIPTVList = self.PLXtuning(lst)
        
        if len(TMPIPTVList) == 0:
            SortIPTVList = ['This list is empty or unavailable@#@ ']
        elif Random == True:
            SortIPTVList = TMPIPTVList
            random.shuffle(SortIPTVList)
        else:
            SortIPTVList = sorted_nicely(TMPIPTVList)

        for n in range(len(SortIPTVList)):
            if SortIPTVList[n] != None:
                IPTVNameList.append((SortIPTVList[n]).split('@#@')[0])   
                IPTVPathList.append((SortIPTVList[n]).split('@#@')[1])
        
        hide_busy_dialog()
        # cleanup   
        del SortIPTVList[:]
        del TMPIPTVList[:]
        return IPTVNameList, IPTVPathList

   
    def IPTVtuning(self, IPTVlst):
        self.log('IPTVtuning')   
        IPTVlist = ['M3U ERROR!! List Empty or Malformed!@#@ ']
        for iptv in range(len(IPTVlst)):
            if IPTVlst[iptv].startswith('#EXTINF:'):
                try:
                    title = (IPTVlst[iptv].split(',',1)[1]).replace('\r','').replace('\t','').replace('\n','')
                    link = (IPTVlst[iptv + 1]).replace('\r','').replace('\t','').replace('\n','')
                    channelid = title
                    title = title + ' IPTV'

                    if link[0:4] != 'http' and link[0:4] != 'rtmp' and link[0:4] != 'rtsp' and link[0:6] != 'plugin':
                        raise
                    IPTVlist.append(title+'@#@'+link)
                except:
                    pass
        return IPTVlist
        

    def LSTVtuning(self, LSTVlst):
        self.log('LSTVtuning') 
        LSTVlist = ['XML ERROR!! List Empty or Malformed!@#@ ']
        for lstv in range(len(LSTVlst)):
            if LSTVlst[lstv].startswith('<title>'):
                try:
                    title = (LSTVlst[lstv]).replace('\r','').replace('\t','').replace('\n','').replace('<title>','').replace('</title>','')
                    title = title + ' XML'

                    if LSTVlst[lstv+1].startswith('<link>'):
                        link = (LSTVlst[lstv+1]).replace('\r','').replace('\t','').replace('\n','').replace('<link>','').replace('</link>','')

                        if link[0:4] != 'http' and link[0:4] != 'rtmp' and link[0:4] != 'rtsp' and link[0:6] != 'plugin':
                            raise

                        if LSTVlst[lstv+2].startswith('<thumbnail>'):
                            logo = (LSTVlst[lstv+2]).replace('\r','').replace('\t','').replace('\n','').replace('<thumbnail>','').replace('</thumbnail>','')
                            
                            if logo[0:4] == 'http' and ENHANCED_DATA == True:
                                self.GrabLogo(logo, title)
                    LSTVlist.append(title+'@#@'+link)
                except:
                    pass
        return LSTVlist
    

    def PLXtuning(self, PLXlst):
        self.log('PLXtuning')
        PLXlist = ['PLX ERROR!! List Empty or Malformed!@#@ ']
        for PLX in range(len(PLXlst)):
            if 'name=' in PLXlst[PLX]:
                try:
                    title = (str(PLXlst[PLX])).replace('\r','').replace('\t','').replace('\n','').replace('name=','')
                    try:
                        title = title.split('  ')[0]
                    except:
                        pass
                    title = title + ' PLX'
                    
                    if 'thumb=' in PLXlst[PLX+1]:
                        logo = (PLXlst[PLX + 1]).replace('\r','').replace('\t','').replace('\n','').replace('thumb=','')
                        
                        if logo[0:4] == 'http' and ENHANCED_DATA == True:
                            self.GrabLogo(logo, title)
                            
                    if 'URL=' in PLXlst[PLX+2]:
                        link = (PLXlst[PLX + 2]).replace('\r','').replace('\t','').replace('\n','').replace('URL=','')
                        if link[0:4] != 'http' and link[0:4] != 'rtmp' and link[0:4] != 'rtsp':
                            raise
                    PLXlist.append(title+'@#@'+link)
                except:
                    pass
        return PLXlist

        
    def fillPluginList(self):
        self.log('fillPluginList')
        json_query = ('{"jsonrpc":"2.0","method":"Addons.GetAddons","params":{"type":"xbmc.addon.video","content":"video","enabled":true,"properties":["path","name"]}, "id": 1 }')
        json_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
        TMPpluginList = []
        try:
            for f in detail:
                names = re.search('"name" *: *"(.*?)",', f)
                paths = re.search('"addonid" *: *"(.*?)",', f)
                if names and paths:
                    name = self.cleanLabels(names.group(1))
                    path = paths.group(1)
                    if name.lower() not in ['super favourites','hdhomerun','pseudolibrary','pseudocompanion']:
                        TMPpluginList.append(name+','+path)  
                    
            SortedpluginList = sorted_nicely(TMPpluginList)
            for i in range(len(SortedpluginList)):
                self.pluginNameList.append((SortedpluginList[i]).split(',')[0])
                self.pluginPathList.append((SortedpluginList[i]).split(',')[1]) 
        except Exception,e:
            self.log("fillPluginList, Failed! " + str(e))

        if len(TMPpluginList) == 0:
            self.pluginNameList = ['No Kodi plugins unavailable!']
    

    def getPVRChannels(self):
        self.log("getPVRChannels")
        Channels = []
        json_detail = self.sendJSON('{"jsonrpc":"2.0","method":"PVR.GetChannels","params":{"channelgroupid":"alltv","properties":["thumbnail","channel"]},"id":2}')
        file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
        for f in file_detail:
            try:
                CHids = re.search('"channelid" *: *(.*?),', f)
                if CHids and len(CHids.group(1)) > 0:
                    CHnames = re.search('"label" *: *"(.*?)"', f)
                    CHthmbs = re.search('"thumbnail" *: *"(.*?)"', f)
                    CHid = CHids.group(1) or ''
                    CHname = CHnames.group(1) or ''
                    CHthmb = CHthmbs.group(1) or ''
                    Channels.append([CHid,CHname,unquote(CHthmb)])
            except:
                pass
        return Channels
        
        
    def getPVRLink(self, channel):
        self.log('getPVRLink')
        if getXBMCVersion() < 14:
            PVRverPath = "pvr://channels/tv/All TV channels/"
        else:
            PVRverPath = "pvr://channels/tv/All channels/"   
        PVRPath = xbmcvfs.listdir(PVRverPath)
        return os.path.join(PVRverPath,PVRPath[1][channel])

        
    def fillUSTVnow(self):
        self.log('fillUSTVnow')
        NameLst = []
        IconLst = []
        PathLst = []
        
        user = REAL_SETTINGS.getSetting('ustv_email')
        if user == "":
            return NameLst,PathLst,IconLst 
            
        channels = self.ustv.getChannelNames()
        for i in range(len(channels)):
            CHname = channels[i][0]
            NameLst.append(('[COLOR=blue][B]%s[/B][/COLOR] - %s') % (str(i+1), CHname))
            PathLst.append('ustvnow://'+ CHname)
            IconLst.append(channels[i][0])
        return NameLst,PathLst,IconLst
        
        
    def fillPVR(self):
        self.log('fillPVR')
        PVRNameList = []
        PVRPathList = []
        PVRIconList = []
        PVRChannels = self.getPVRChannels()
        
        for i in range(len(PVRChannels)):
            CHid = PVRChannels[i][0]
            CHname = self.cleanLabels(PVRChannels[i][1])
            thumb = PVRChannels[i][2]
            PVRNameList.append(('[COLOR=blue][B]%s[/B][/COLOR] - %s') % (str(i+1), CHname))
            PVRPathList.append(self.getPVRLink(i))
            PVRIconList.append(thumb)
        if len(PVRNameList) == 0:
            PVRNameList = ['Kodi PVR is empty or unavailable!']
        self.PVRList = [PVRNameList, PVRPathList, PVRIconList]

        
    def fillFavourites(self):
        self.log('fillFavourites')
        show_busy_dialog()
        json_query = ('{"jsonrpc":"2.0","method":"Favourites.GetFavourites","params":{"properties":["path","thumbnail"]},"id":1}')
        json_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
        TMPfavouritesList = []
        FavouritesNameList = []
        FavouritesPathList = []
        try:
            for f in detail:
                paths = re.search('"path" *: *"(.*?)",', f)
                names = re.search('"title" *: *"(.*?)",', f)
                types = re.search('"type" *: *"(.*?)"', f)
                if types != None and len(types.group(1)) > 0:
                    type = types.group(1)
                    if names and paths:
                        name = self.cleanLabels(names.group(1))
                        if type.lower() == 'media':
                            path = paths.group(1)
                            TMPfavouritesList.append(name+'@#@'+path) 
            SortedFavouritesList = sorted_nicely(TMPfavouritesList)
            for i in range(len(SortedFavouritesList)):  
                FavouritesNameList.append((SortedFavouritesList[i]).split('@#@')[0])  
                FavouritesPathList.append((SortedFavouritesList[i]).split('@#@')[1])          
        except Exception,e:
            self.log("fillFavourites, Failed! " + str(e))

        if len(TMPfavouritesList) == 0:
            FavouritesNameList = ['Kodi Favorites is empty or unavailable!']
        hide_busy_dialog() 
        return FavouritesNameList, FavouritesPathList
        
        
    def fillExternalList(self, type, source='', list='Community', Random=False):
        self.log('fillExternalList, type = ' + type + ', source = ' + source)
        show_busy_dialog()
        TMPExternalList = []
        ExternalNameList = []
        SortedExternalList = []
        ExternalSetting1List = []
        ExternalSetting2List = []
        ExternalSetting3List = []
        ExternalSetting4List = []
        RSSURL = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/rss.ini'
        YoutubeChannelURL = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/youtube_channels.ini'
        YoutubePlaylistURL = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/youtube_playlists.ini'
        YoutubeChannelNetworkURL = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/youtube_channels_networks.ini'
        YoutubePlaylistNetworkURL = 'http://raw.github.com/PseudoTV/PseudoTV_Lists/master/youtube_playlists_networks.ini'
        
        if type == 'LiveTV':
            url = LiveURL
        elif type == 'InternetTV':
            url = InternetURL
        elif type == 'Plugin':
            url = PluginURL
        elif type == 'YouTube':
            if source == 'Channel':
                url = YoutubeChannelURL
                id = '1'
            elif source == 'Playlist':
                url = YoutubePlaylistURL
                id = '2'
            elif source == 'Multi Playlist':
                url = YoutubePlaylistNetworkURL
                id = '7'
            elif source == 'Multi Channel': 
                url = YoutubeChannelNetworkURL
                id = '8'
        elif type == 'RSS':
            url = RSSURL
            id = '1'
        try:
            # responce = open_url(url).readlines()
            responce = read_url_cached(url, return_type='readlines')
            data = removeStringElem(responce)#remove empty lines
            for i in range(len(data)):
                Pluginvalid = False
                line = data[i].replace("\n","").replace('""',"")

                if type == 'RSS' or source == 'Channel' or source == 'Playlist':
                    line = line.split(",")
                else:
                    line = line.split("|")

                if len(line) == 7:
                    if not str(line).startswith(';'):
                        genre = (line[0])
                        chtype = (line[1])
                        setting_1 = (line[2])
                        setting_2 = (line[3])
                        setting_3 = (line[4])
                        setting_4 = (line[5])
                        channel_name = self.cleanLabels(line[6])
                        
                        if genre.lower() == 'tv':
                            genre = '[COLOR=yellow]'+genre+'[/COLOR]'
                        elif genre.lower() == 'movies':
                            genre = '[COLOR=cyan]'+genre+'[/COLOR]'
                        elif genre.lower() == 'episodes':
                            genre = '[COLOR=yellow]'+genre+'[/COLOR]'
                        elif genre.lower() == 'sports':
                            genre = '[COLOR=red]'+genre+'[/COLOR]'
                        elif genre.lower() == 'news':
                            genre = '[COLOR=green]'+genre+'[/COLOR]'
                        elif genre.lower() == 'kids':
                            genre = '[COLOR=orange]'+genre+'[/COLOR]'
                        elif genre.lower() == 'music':
                            genre = '[COLOR=purple]'+genre+'[/COLOR]'
                        elif genre.lower() == 'other':
                            genre = '[COLOR=grey]'+genre+'[/COLOR]'
                        genre = genre.upper()
                        
                        if chtype == '15':
                            Pluginvalid = self.plugin_ok(setting_1)
                            channel_name = (((setting_1.split('//')[1]).split('/')[0]).replace('plugin.video.','').replace('plugin.audio.','')).upper() + ': ' + genre + ' | ' + channel_name
                        
                        elif chtype == '9':
                            Pluginvalid = self.Valid_ok(setting_2)
                            channel_name = channel_name + ' - ' + genre
                        
                        elif chtype == '8':
                            Pluginvalid = self.Valid_ok(setting_2)                  
                            if setting_2[0:9].lower() != 'plugin://':
                                setting_2 = 'plugin://' + setting_2                     
                            if setting_2.startswith('plugin://'):    
                                channel_name = (((setting_2.split('//')[1]).split('/')[0]).replace('plugin.video.','').replace('plugin.audio.','')).upper() + ' - ' + channel_name
                            else:
                                channel_name =  'Internet - ' + channel_name
                            
                        elif chtype == '10':
                            if len(setting_2) == 0:
                                setting_2 = id
                            Pluginvalid = self.youtube_ok(setting_2, setting_1)
                            channel_name = channel_name + ' - ' + genre

                        if Pluginvalid != False:
                            TMPExternalList.append(channel_name+'@#@'+setting_1+'@#@'+setting_2+'@#@'+setting_3+'@#@'+setting_4)

                elif len(line) == 2:
                    if not str(line).startswith(';'):
                        setting_1 = line[0]
                        channel_name = line[1]
                        if setting_1.startswith('http'):
                            Pluginvalid = self.Valid_ok(setting_1)
                            if Pluginvalid != False:
                                TMPExternalList.append(channel_name+'@#@'+setting_1+'@#@'+id+'@#@'+'25'+'@#@'+'Default')
                        else:
                            if self.youtube_player_ok() != False:
                                TMPExternalList.append(channel_name+'@#@'+setting_1+'@#@'+id+'@#@'+'25'+'@#@'+'Default')
                
                elif len(line) == 3:
                    if not str(line).startswith(';'):
                        type = line[0]
                        url = line[1]
                        channel_name = line[2]
                        if type.lower() == source.lower():
                            if url.startswith('http'):
                                Pluginvalid = self.Valid_ok(url)
                                if Pluginvalid != False:
                                    # append as string element for easier sorting; todo dict, sort using keys.
                                    TMPExternalList.append(channel_name+'@#@'+url+'@#@'+''+'@#@'+''+'@#@'+'')
                                    
            if Random == True:
                SortedExternalList = TMPExternalList
                random.shuffle(SortedExternalList)
            else:
                SortedExternalList = sorted_nicely(TMPExternalList)
                
            for n in range(len(SortedExternalList)):
                if SortedExternalList[n] != None:
                    ExternalNameList.append((SortedExternalList[n]).split('@#@')[0])   
                    ExternalSetting1List.append((SortedExternalList[n]).split('@#@')[1])
                    ExternalSetting2List.append((SortedExternalList[n]).split('@#@')[2])
                    ExternalSetting3List.append((SortedExternalList[n]).split('@#@')[3])
                    ExternalSetting4List.append((SortedExternalList[n]).split('@#@')[4])
        except Exception,e:
            self.log("fillExternalList, Failed! " + str(e))

        if len(TMPExternalList) == 0:
            ExternalNameList = ['This list is empty or unavailable, Please try again later.']
        hide_busy_dialog() 
        return ExternalNameList, ExternalSetting1List, ExternalSetting2List, ExternalSetting3List, ExternalSetting4List
              
        
    def getHDHRChannels(self, favorite=False):
        self.log("getHDHRChannels")
        DupChk = []
        Channels = []
        FavChannels = []
        list = ''
        devices = hdhr.discover()
        for i in range(len(devices)):
            url = (str(devices[i]).split(':url=')[1]).replace('>','')
            try:
                list = list + open_url(url).read()
            except:
                pass
            file_detail = re.compile( "{(.*?)}", re.DOTALL ).findall(list)
            for f in file_detail:
                fav = False
                drm = False
                try:
                    match = re.search('"GuideName" *: *"(.*?)",', f)    
                    if match and len(match.group(1)) > 0:
                        chname = match.group(1)
                        links = re.search('"URL" *: *"(.*?)"', f)
                        chnums = re.search('"GuideNumber" *: *"([\d.]*\d+)"', f)
                        favs = re.search('"Favorite" *: *([\d.]*\d+)', f)
                        drms = re.search('"DRM" *: *([\d.]*\d+)', f)

                        if links != None and len(links.group(1)) > 0:
                            link = links.group(1)

                        if chnums != None and len(chnums.group(1)) > 0:
                            chnum = chnums.group(1)

                        if favs != None and len(favs.group(1)) > 0:
                            fav = bool(favs.group(1))
                            
                        if drms != None and len(drms.group(1)) > 0:
                            drm = bool(drms.group(1))
                                        
                        if fav == True and chname not in DupChk:
                            DupChk.append(chname)
                            FavChannels.append([chnum,chname,fav,drm,link])
                        Channels.append([chnum,chname,fav,drm,link])
                except:
                    pass
        del DupChk[:]
        if favorite == True:
            return FavChannels
        else:
            return Channels
         
                    
    def fillHDHR(self,favorite=False):
        self.log("fillHDHR")
        Favlist = []
        HDHRNameList = []
        HDHRPathList  = []
        HDHRChannels = self.getHDHRChannels(favorite)
        for i in range(len(HDHRChannels)):
            chnum = HDHRChannels[i][0]
            chname = self.cleanLabels(HDHRChannels[i][1])
            fav = HDHRChannels[i][2]
            drm = HDHRChannels[i][3]
            link = HDHRChannels[i][4]
            
            if fav == True:
                chname = chname+'[COLOR=gold] [Favorite][/COLOR]'
            if drm == True:
                chname = chname+'[COLOR=red] [DRM][/COLOR]' 
            chname = '[COLOR=blue][B]'+chnum+'[/B][/COLOR] - ' + chname
            
            HDHRNameList.append(chname)
            HDHRPathList.append(link)

        if len(HDHRNameList) == 0:
            HDHRNameList = ['HDHR ERROR: Unable to find device or favorite channels']
        
        # cleanup
        del HDHRChannels[:]
        self.HDHRList = [HDHRNameList, HDHRPathList]

        
    def sbManaged(self, tvdbid):
        self.log("sbManaged")
        sbManaged = False
        if REAL_SETTINGS.getSetting('sickbeard.enabled') == "true":
            try:
                sbManaged = self.sbAPI.isShowManaged(tvdbid)
            except Exception,e:
                self.log("sbManaged, Failed! " + str(e))
        return sbManaged


    def cpManaged(self, title, imdbid):
        self.log("cpManaged")
        cpManaged = False
        if REAL_SETTINGS.getSetting('couchpotato.enabled') == "true":
            try:
                r = str(self.cpAPI.getMoviebyTitle(title))
                r = r.split("u'")
                match = [s for s in r if imdbid in s][1]
                if imdbid in match:
                    cpManaged = True
            except Exception,e:
                self.log("cpManaged, Failed! " + str(e))
        return cpManaged
        

    def getYear(self, type, title):
        self.log("getYear")
        try:
            self.metaget = metahandlers.MetaData(preparezip=False)
            year = self.metaget.get_meta(type, title)['year']
            if not year:
                year = 0
        except Exception,e:
            year = 0
        return year
        

    def getTVDBID(self, title, year):
        self.log("getTVDBID")
        try:
            self.metaget = metahandlers.MetaData(preparezip=False)
            tvdbid = self.metaget.get_meta('tvshow', title, year=year)['tvdb_id']
            if not tvdbid:
                tvdbid = 0
        except Exception,e:
            tvdbid = 0
            self.log("getTVDBID, Failed! " + str(e))
        return tvdbid
         
         
    def getIMDBIDmovie(self, title, year=''):
        self.log("getIMDBIDmovie")
        try:
            self.metaget = metahandlers.MetaData(preparezip=False)
            imdbid = (self.metaget.get_meta('movie', title, year=year)['imdb_id'])
            if not imdbid:
                imdbid = 0
        except Exception,e:
            imdbid = 0
            self.log("getIMDBIDmovie, Failed! " + str(e))
        return imdbid

        
    def getGenre(self, type, title, year=''):
        self.log("getGenre")
        try:
            self.metaget = metahandlers.MetaData(preparezip=False)
            genre = self.metaget.get_meta(type, title, year=year)['genre']
            if ',' in genre:
                try:
                    genre = str(genre.split(',')[0])
                except:
                    pass
            elif '/' in genre:
                try:
                    genre = str(genre.split(' / ')[0])
                except:
                    pass
            if not genre:
                genre = 'Unknown'
        except Exception,e:
            genre = 'Unknown'
        self.log("getGenre, title = " + title + ", genre = " + genre)
        return genre
        

    def getRating(self, type, title, year=''):
        self.log("getRating")
        try:   
            self.metaget = metahandlers.MetaData(preparezip=False)
            rating = self.metaget.get_meta(type, title, year=year)['mpaa']
            if not rating:
                rating = 'NR'
        except Exception,e:
            rating = 'NR'
        return self.cleanRating(rating)
        

    def getTagline(self, title, year=''):
        self.log("getTagline")
        try:
            self.metaget = metahandlers.MetaData(preparezip=False)
            tagline = self.metaget.get_meta('movie', title, year=year)['tagline']
            if not tagline:
                tagline = ''
        except Exception,e:
            tagline = ''
            self.log("getTagline, Failed! " + str(e))
        return tagline
                
                          
    def getIMDBIDtv(self, title, year):
        self.log("getIMDBIDtv")
        try:
            self.metaget = metahandlers.MetaData(preparezip=False)
            imdbid = self.metaget.get_meta('tvshow', title, year=year)['imdb_id']
            if not imdbid:
                imdbid = 0
        except Exception,e:
            imdbid = 0
            self.log("getIMDBIDtv, Failed! " + str(e))
        return imdbid
        
        
    def getTVDBIDbyZap2it(self, dd_progid):
        self.log("getTVDBIDbyZap2it")
        try:
            tvdbid = self.tvdbAPI.getIdByZap2it(dd_progid)
            if not tvdbid or tvdbid == 'Empty':
                tvdbid = 0
        except Exception,e:
            tvdbid = 0
            self.log("getTVDBIDbyZap2it, Failed! " + str(e))
        return tvdbid
        
        
    def getEnhancedEPGdata(self, type, showtitle, year, genre, rating):
        cleantitle = showtitle
        if ENHANCED_DATA == True:
            year, cleantitle, showtitle = getTitleYear(showtitle, year)
            if year == 0 or year == '0':
                year = self.getYear(type, showtitle)
            if genre == 'Unknown':
                genre = self.getGenre(type, cleantitle, str(year))
            if rating == 'NR':
                rating = self.getRating(type, cleantitle, str(year))
        year, cleantitle, showtitle = getTitleYear(showtitle, year)
        self.log("getEnhancedEPGdata, return: cleantitle = " + cleantitle + ", year = " + str(year) + ", genre = " + genre + ", rating = " + rating)
        return showtitle, cleantitle, genre, rating, year
        
        
    def getEnhancedGuideData(self, showtitle, year, imdbnumber, genre, rating, type, tagline=''):
        cleantitle = showtitle
        if ENHANCED_DATA == True:
            showtitle, cleantitle, genre, rating, year = self.getEnhancedEPGdata(type, showtitle, year, genre, rating)
            imdbnumber = self.getEnhancedIDs(type, cleantitle, year, imdbnumber)
            if type == 'movie': 
                if not tagline:
                    tagline = self.getTagline(cleantitle, str(year))
            else:
                tagline = ''
                # tagline = seasontitle and info todo
        if imdbnumber == 0:
            imdbnumber = str(imdbnumber)
        self.log("getEnhancedGuideData, return: imdbnumber = " + imdbnumber + ", year = " + str(year) + ", genre = " + genre + ", rating = " + rating + ", tagline = " + tagline)
        return showtitle, cleantitle, year, imdbnumber, genre, rating, tagline

            
    def getEnhancedIDs(self, type, cleantitle, year, imdbnumber):
        if ENHANCED_DATA == True:
            if type == 'movie': 
                if imdbnumber == 0 or imdbnumber == '0':
                    imdbnumber = self.getIMDBIDmovie(cleantitle, str(year))
            else:
                if imdbnumber == 0 or imdbnumber == '0':
                    imdbnumber = self.getTVDBID(cleantitle, str(year))
        if imdbnumber == 0:
            imdbnumber = str(imdbnumber)
        self.log("getEnhancedIDs, return: id = " + imdbnumber)
        return imdbnumber
            

    # filelist cache is redundant to m3u, possible future use?
    def getFileListCache(self, chtype, channel, purge=False):
        self.log("getFileListCache")
        #Cache name
        cachetype = str(chtype) + ':' + str(channel)
        
        #Set Life of cache, value needs to be lower than reset time.
        if chtype <= 7 or chtype >= 10:
            life = (SETTOP_REFRESH - 900) / 60
        else:
            life = 18
            
        self.FileListCache = StorageServer.StorageServer(("plugin://script.pseudotv.live/%s" % cachetype),life)
        if purge == True:
            self.FileListCache.delete("%")

         
    def clearFileListCache(self, chtype=9999, channel=9999):
        self.log("clearFileListCache")
        if chtype == 9999 and channel == 9999:
            for n in range(CHANNEL_LIMIT):
                for i in range(NUMBER_CHANNEL_TYPES):
                    try:
                        self.getFileListCache(i+1, n+1, True)
                    except:
                        pass
            return True
        else:
            self.getFileListCache(chtype, channel, True)
            return True
            
                    
    def durationInSeconds(self, dur):
        self.log("durationInSeconds")
        if len(str(dur)) in [1,2]:
            return dur * 60
        elif len(str(dur)) == 3:
            ndur = dur * 60
            if ndur > MAXFILE_DURATION:
                return dur
            else:
                return ndur
        else:
            return dur
           

    def requestItem(self, file, fletype='video'):
        self.log("requestItem") 
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":1,"properties":["thumbnail","fanart","title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline","tvshowid","rating"]}, "id": 1}')
        json_folder_detail = self.sendJSON(json_query)
        return re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)
           
           
    def requestList(self, path, fletype='video'):
        self.log("requestList") 
        json_query = ('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "%s", "properties":["thumbnail","fanart","title","year","mpaa","imdbnumber","description","season","episode","playcount","genre","duration","runtime","showtitle","album","artist","plot","plotoutline","tagline","tvshowid","rating"]}, "id": 1}' % (self.escapeDirJSON(path), fletype))
        json_folder_detail = self.sendJSON(json_query)
        return re.compile( "{(.*?)}", re.DOTALL ).findall(json_folder_detail)      
 
 
    def fillPlugins(self, type='video'):
        self.log('fillPlugins, type = ' + type)
        json_query = ('{"jsonrpc":"2.0","method":"Addons.GetAddons","params":{"type":"xbmc.addon.%s","properties":["name","path","thumbnail","description","fanart","summary"]}, "id": 1 }'%type)
        json_detail = self.sendJSON(json_query)
        detail = re.compile( "{(.*?)}", re.DOTALL ).findall(json_detail)
        for f in detail:
            names = re.search('"name" *: *"(.*?)",', f)
            paths = re.search('"addonid" *: *"(.*?)",', f)
            thumbnails = re.search('"thumbnail" *: *"(.*?)",', f)
            fanarts = re.search('"fanart" *: *"(.*?)",', f)
            descriptions = re.search('"description" *: *"(.*?)",', f)
            if not descriptions:
                descriptions = re.search('"summary" *: *"(.*?)",', f)
            if descriptions:
                description = self.cleanLabels(descriptions.group(1))
            else:
                description = ''
            if names and paths:
                name = self.cleanLabels(names.group(1))
                path = paths.group(1)
                if type == 'video' and path.startswith('plugin.video'):
                    thumbnail = removeNonAscii(thumbnails.group(1))
                    fanart = removeNonAscii(fanarts.group(1))
                    self.Items = xbmcgui.ListItem(label=name, thumbnailImage = thumbnail)
                    self.Items.setIconImage(thumbnail)
                    self.Items.setProperty("mediapath", path)
                    self.Items.setProperty("Fanart_Image", fanart)
                    
                    infoList = {}
                    infoList['mediatype']     = type
                    infoList['mpaa']          = 'Unknown'
                    infoList['tvshowtitle']   =  name
                    infoList['title']         =  name
                    infoList['originaltitle'] = 'originaltitle'
                    infoList['sorttitle']     = 'sorttitle'
                    infoList['studio']        = 'Studio'
                    infoList['genre']         = 'Genre'
                    infoList['plot']          = 'Plot'
                    infoList['plotoutline']   = 'plotoutline'
                    infoList['tagline']       = 'tagline'
                    infoList['dateadded']     = 'dateadded'
                    infoList['premiered']     = 'premiered'
                    infoList['aired']         = 'aired'
                    infoList['code']          = 'code'
                    infoList['lastplayed']    = 'lastplayed'
                    # infoList['album']         = 'album'
                    # infoList['artist']        = ['artist']
                    # infoList['votes']         = 'votes'
                    infoList['duration']      = 1
                    infoList['year']          = 1977
                    infoList['season']        = 3
                    infoList['episode']       = 4
                    infoList['playcount']     = 5
                    self.Items.setInfo('Video', infoList)    

                    infoArt = {}
                    infoArt['thumb']        = thumbnail
                    infoArt['poster']       = thumbnail
                    infoArt['banner']       = ''
                    infoArt['fanart']       = fanart
                    infoArt['clearart']     = ''
                    infoArt['clearlogo']    = ''
                    infoArt['landscape']    = fanart
                    infoList['icon']        = thumbnail
                    self.Items.setArt(infoArt) 
                    self.PanelItems.addItem(self.Items) 
    
    
    def fillListItems(self, url, type='video', file_type=False):
        self.log('fillListItems')
        if not file_type:
            detail = uni(self.requestList(url, type))
        else:
            detail = uni(self.requestItem(url, type))
        for f in detail:
            files = re.search('"file" *: *"(.*?)",', f)
            filetypes = re.search('"filetype" *: *"(.*?)",', f)
            labels = re.search('"label" *: *"(.*?)",', f)
            thumbnails = re.search('"thumbnail" *: *"(.*?)",', f)
            fanarts = re.search('"fanart" *: *"(.*?)",', f)
            descriptions = re.search('"description" *: *"(.*?)",', f)
            
            if filetypes and labels and files:
                filetype = filetypes.group(1)
                name = self.cleanLabels(labels.group(1))
                file = (files.group(1).replace("\\\\", "\\"))
                
                if not descriptions:
                    description = ''
                else:
                    description = self.cleanLabels(descriptions.group(1))
                
                if thumbnails != None and len(thumbnails.group(1)) > 0:
                    thumbnail = thumbnails.group(1)
                else:
                    thumbnail = THUMB
                    
                if fanarts != None and len(fanarts.group(1)) > 0:
                    fanart = fanarts.group(1)
                else:
                    fanart = FANART
                    
                self.Items = xbmcgui.ListItem(label=name, thumbnailImage = thumbnail)
                
                if filetype == 'file':
                    self.Items.setProperty('IsPlayable', 'true')
                else:
                    self.Items.setProperty('IsPlayable', 'false')
                    
                self.Items.setIconImage(thumbnail)
                self.Items.setProperty("mediapath", file)
                self.Items.setProperty("Fanart_Image", fanart)
                
                infoList = {}
                infoList['mediatype']     = type
                infoList['mpaa']          = 'Unknown'
                infoList['tvshowtitle']   =  name
                infoList['title']         =  name
                infoList['originaltitle'] = 'originaltitle'
                infoList['sorttitle']     = 'sorttitle'
                infoList['studio']        = 'Studio'
                infoList['genre']         = 'Genre'
                infoList['plot']          = 'Plot'
                infoList['plotoutline']   = 'plotoutline'
                infoList['tagline']       = 'tagline'
                infoList['dateadded']     = 'dateadded'
                infoList['premiered']     = 'premiered'
                infoList['aired']         = 'aired'
                infoList['code']          = 'code'
                infoList['lastplayed']    = 'lastplayed'
                # infoList['album']         = 'album'
                # infoList['artist']        = ['artist']
                # infoList['votes']         = 'votes'
                infoList['duration']      = 1
                infoList['year']          = 1977
                infoList['season']        = 3
                infoList['episode']       = 4
                infoList['playcount']     = 5
                self.Items.setInfo('Video', infoList)    

                infoArt = {}
                infoArt['thumb']        = thumbnail
                infoArt['poster']       = thumbnail
                infoArt['banner']       = ''
                infoArt['fanart']       = fanart
                infoArt['clearart']     = ''
                infoArt['clearlogo']    = ''
                infoArt['landscape']    = fanart
                infoList['icon']        = thumbnail
                self.Items.setArt(infoArt) 
                self.PanelItems.addItem(self.Items) 
        
        
    def getFileList(self, file_detail, channel, limit, excludeLST=[]):
        self.log("getFileList")
        fileList = []
        seasoneplist = []
        dirlimit = limit

        #listitems return parent items during error, catch repeat list and return.
        if file_detail == self.file_detail_CHK:
            return
        else:
            self.file_detail_CHK = file_detail
        
        for f in file_detail:
            if self.threadPause() == False:
                del fileList[:]
                break
                    
            try:
                tmpstr = ''
                dur_accurate = False
                files = re.search('"file" *: *"(.*?)",', f)
                
                if files:
                    if not files.group(1).startswith(("plugin", "upnp")) and (files.group(1).endswith("/") or files.group(1).endswith("\\")):
                        fileList.extend(self.buildFileList(files.group(1), channel, limit))
                    else:
                        f = self.runActions(RULES_ACTION_JSON, channel, f)
                        filetypes = re.search('"filetype" *: *"(.*?)",', f)
                        labels = re.search('"label" *: *"(.*?)",', f)
                        
                        #if core variables, proceed
                        if filetypes and labels:
                            filetype = filetypes.group(1)
                            file = (files.group(1).replace("\\\\", "\\"))
                            label = self.cleanLabels(labels.group(1))

                            if label and label.lower() not in excludeLST:
                                # if file[0:4] != 'upnp':
                                if file.startswith('plugin%3A%2F%2F'):
                                    file = urllib.unquote(file).replace('",return)','')
                                
                                if filetype == 'file' and self.filecount < limit:
                                    self.log('getFileList, file')
                                    duration = re.search('"duration" *: *([0-9]*?),', f)
                                    
                                    # If duration returned, else 0
                                    try:
                                        dur = int(duration.group(1))
                                    except Exception,e:
                                        dur = 0
                                       
                                    # Less accurate duration
                                    if dur == 0:
                                        duration = re.search('"runtime" *: *([0-9]*?),', f)
                                        try:
                                            ladur = int(duration.group(1))
                                        except Exception,e:
                                            ladur = 0
                                            
                                    if dur == 0:
                                        if ladur != 0 and REAL_SETTINGS.getSetting('accurate_duration') == 'false':
                                            dur = ladur
                                        else:
                                            # Accurate duration
                                            if not file.startswith(("plugin", "upnp")) and isLowPower() == False:
                                                try:
                                                    dur = self.getDuration(file)
                                                    dur_accurate = True
                                                except Exception,e:
                                                    dur = 0
                                                    
                                            # Less accurate duration
                                            if dur == 0:
                                                dur = ladur
                                                                                                                               
                                    if  dur == 0 and file.startswith(("plugin", "upnp")):
                                        dur = 3600    
                                             
                                    # Remove any file types that we don't want (ex. IceLibrary, ie. Strms)
                                    if self.incIceLibrary == False:
                                        if file[-4:].lower() == 'strm':
                                            dur = 0
                                            
                                    self.log("getFileList, dur = " + str(dur))  

                                    if dur > 0:
                                        self.filecount += 1
                                        seasonval = -1
                                        epval = -1

                                        if self.background == False:
                                            self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "adding %s Videos" % str(self.filecount))                                           
                                        self.log('getFileList, filecount = ' + str(self.filecount) +'/'+ str(limit))
                                        
                                        titles = re.search('"label" *: *"(.*?)",', f)
                                        showtitles = re.search('"showtitle" *: *"(.*?)",', f)
                                        plots = re.search('"plot" *: *"(.*?)",', f)
                                        plotoutlines = re.search('"plotoutline" *: *"(.*?)",', f)
                                        years = re.search('"year" *: *([\d.]*\d+)', f)
                                        genres = re.search('"genre" *: *\[(.*?)\],', f)
                                        playcounts = re.search('"playcount" *: *([\d.]*\d+),', f)
                                        imdbnumbers = re.search('"imdbnumber" *: *"(.*?)",', f)
                                        ratings = re.search('"mpaa" *: *"(.*?)",', f)
                                        starss = re.search('"rating" *: *([\d.]*\d+),', f)
                                        descriptions = re.search('"description" *: *"(.*?)",', f)
                                        # streamdetails = re.search('"streamdetails" *: *{(.*?)},', f)

                                        #tvshow check
                                        if showtitles != None and len(showtitles.group(1)) > 0:
                                            type = 'tvshow'
                                            dbids = re.search('"tvshowid" *: *([\d.]*\d+),', f)
                                            epids = re.search('"id" *: *([\d.]*\d+),', f)
                                        else:
                                            type = 'movie'
                                            dbids = re.search('"id" *: *([\d.]*\d+),', f)  
                                            epids = None
                                        self.log("getFileList, type = " + type) 
                                        
                                        # if possible find year by title
                                        try:
                                            year = int(years.group(1))
                                        except:
                                            year = 0
                                        self.log("getFileList, year = " + str(year))  

                                        if genres != None and len(genres.group(1)) > 0:
                                            genre = ((genres.group(1).split(',')[0]).replace('"',''))
                                        else:
                                            genre = 'Unknown'
                                        self.log("getFileList, genre = " + str(genre))  
                                            
                                        if playcounts != None and len(playcounts.group(1)) > 0:
                                            playcount = int(playcounts.group(1))
                                        else:
                                            playcount = 1                             
                                        self.log("getFileList, playcount = " + str(playcount))  
                                        
                                        if ratings != None and len(ratings.group(1)) > 0:
                                            rating = self.cleanRating(ratings.group(1))
                                        else:
                                            rating = 'NR'
                                        self.log("getFileList, rating = " + str(rating))  
                                            
                                        if starss != None and len(starss.group(1)) > 0:
                                            stars = "%.1f" % round(float(starss.group(1)))
                                        else:
                                            stars = 0.0
                                        self.log("getFileList, stars = " + str(stars))  
                                            
                                        hd = False
                                        # if widths != None and len(widths.group(1)) > 0:
                                            # self.log("getFileList, width = " + str(widths.group(1)))
                                            # if int(widths.group(1)) >= 720:
                                                # hd = True
                                        # self.log("getFileList, hd = " + str(hd)) 

                                        if imdbnumbers != None and len(imdbnumbers.group(1)) > 0:
                                            imdbnumber = imdbnumbers.group(1)
                                        else:
                                            imdbnumber = 0
                                        self.log("getFileList, imdbnumber = " + str(imdbnumber))

                                        if epids != None and len(epids.group(1)) > 0:
                                            epid = int(epids.group(1))
                                        else:
                                            epid = 0
                                        self.log("getFileList, epid = " + str(epid))
                                        
                                        if dbids != None and len(dbids.group(1)) > 0:
                                            dbid = int(dbids.group(1))
                                        else:
                                            dbid = 0
                                        self.log("getFileList, dbid = " + str(dbid)) 
                                        
                                        if plots and len(plots.group(1)) > 0:
                                            theplot = (plots.group(1)).replace('\\','').replace('\n','')
                                        elif descriptions and len(descriptions.group(1)) > 0:
                                            theplot = (descriptions.group(1)).replace('\\','').replace('\n','')
                                        elif plotoutlines and len(plotoutlines.group(1)) > 0:
                                            theplot = (plotoutlines.group(1)).replace('\\','').replace('\n','')
                                        else:
                                            theplot = (titles.group(1)).replace('\\','').replace('\n','')
                                        description = theplot
                                        
                                        # This is a TV show
                                        if type == 'tvshow':
                                            season = re.search('"season" *: *([0-9]*?),', f)
                                            episode = re.search('"episode" *: *([0-9]*?),', f)
                                            swtitle = (titles.group(1)).replace('\\','')
                                            swtitle = (swtitle.split('.', 1)[-1]).replace('. ','')
                                            dbid = str(dbid) +':'+ str(epid)
                                            
                                            try:
                                                seasonval = int(season.group(1))
                                                epval = int(episode.group(1))
                                            except Exception,e:
                                                self.log("Season/Episode DB failed" + str(e))
                                                try:  
                                                    labelseasonepval = re.findall(r"(?:s|season)(\d{2})(?:e|x|episode|\n)(\d{2})", label.lower(), re.I)
                                                    seasonval = int(labelseasonepval[0][0])
                                                    epval = int(labelseasonepval[0][1])
                                                except Exception,e:
                                                    self.log("Season/Episode Label failed" + str(e))
                                                    seasonval = -1
                                                    epval = -1
                                                    
                                            if seasonval != -1 and epval != -1:
                                                try:
                                                    eptitles = swtitle.split(' - ')[1]
                                                except:
                                                    try:
                                                        eptitles = swtitle.split('.')[1]
                                                    except:
                                                        try:
                                                            eptitles = swtitle.split('. ')[1]
                                                        except:
                                                            eptitles = swtitle
                                                subtitle = (('0' if seasonval < 10 else '') + str(seasonval) + 'x' + ('0' if epval < 10 else '') + str(epval) + ' - ' + (eptitles)).replace('  ',' ')
                                            else:
                                                subtitle = swtitle.replace(' . ',' - ')

                                            if len(showtitles.group(1)) > 0:
                                                showtitle = showtitles.group(1)
                                            else:
                                                showtitle = labels.group(1)
                                        else:                  
                                            album = re.search('"album" *: *"(.*?)"', f)
                                            # This is a movie
                                            if not album or len(album.group(1)) == 0:
                                                dbid = str(dbid)
                                                
                                                if len(titles.group(1)) > 0:
                                                    showtitle = titles.group(1)
                                                else:
                                                    showtitle = labels.group(1)
                                                    
                                                taglines = re.search('"tagline" *: *"(.*?)"', f)
                                                if taglines and len(taglines.group(1)) > 50:
                                                    subtitle = ''
                                                    if description and len(description) < 50:
                                                        description = (taglines.group(1)).replace('\\','')
                                                elif taglines and len(taglines.group(1)) > 0:
                                                    subtitle = (taglines.group(1)).replace('\\','')
                                                else:
                                                    subtitle = ''# todo customize missing taglines by media type  
                                            else: #Music
                                                artist = re.search('"artist" *: *"(.*?)"', f)
                                                
                                                if album != None and len(album.group(1)) > 0:
                                                    albumTitle = album.group(1)
                                                else:
                                                    albumTitle = label.group(1)
                                                    
                                                if artist != None and len(artist.group(1)) > 0:
                                                    artistTitle = artist.group(1)
                                                else:
                                                    artistTitle = ''
                                                showtitle = artistTitle
                                                subtitle = albumTitle
                                                description = albumTitle
                                        
                                        if file.startswith('plugin'):
                                            #Remove PlayMedia to keep link from launching
                                            try:
                                                file = ((file.split('PlayMedia("'))[1]).replace('")','')
                                            except:
                                                pass
                                                
                                        # convert minutes to seconds when needed
                                        if dur_accurate == False:
                                            dur = self.durationInSeconds(dur)
                                        
                                        try:
                                            # epg can't handle overlarge controlbuttons, ignore oversized also ignore plugin "clips".
                                            if dur > MAXFILE_DURATION:
                                                self.log("getFileList, Failed! Duration exceeded MAXFILE_DURATION")
                                                raise Exception()
                                            elif file.startswith(("plugin", "upnp")) and dur < self.myOverlay.shortItemLength:
                                                self.log("getFileList, Failed! Duration under shortItemLength")
                                                raise Exception()
                                        except:
                                            pass

                                        # only enhance meta for viewable shows.
                                        if dur >= self.myOverlay.shortItemLength:
                                            showtitle, cleantitle, genre, rating, year = self.getEnhancedEPGdata(type, showtitle, year, genre, rating)
                                            if type == 'tvshow':
                                                showtitle = cleantitle # Use cleantitle without (year) for tvshows

                                        # accurate real-time scheduling does not apply to chtypes <= 7, only chtype = 8. Doesn't hurt to keep track of it anyway, future feature?
                                        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.startDate))
                                        self.startDate += dur
                                        
                                        GenreLiveID = [genre, type, imdbnumber, dbid, False, playcount, rating, hd, False, stars]
                                        tmpstr = self.makeTMPSTR(dur, showtitle, subtitle, description, GenreLiveID, file, timestamp)      
                                        
                                        if self.channels[channel - 1].mode & MODE_ORDERAIRDATE > 0:
                                            seasoneplist.append([seasonval, epval, tmpstr])
                                        else:
                                            # Filter 3D Media.
                                            if self.isMedia3D(file) == True:
                                                if type == 'movie':
                                                    self.movie3Dlist.append(tmpstr)
                                            else:
                                                fileList.append(tmpstr)     
                                
                                elif filetype == 'directory' and self.filecount < limit:
                                    self.log('getFileList, directory')

                                    if self.background == False:
                                        self.updateDialog.update(self.updateDialogProgress, "Updating Channel " + str(self.settingChannel), "searching Directory - %s" % label)
                                    
                                    if file[0:6] == 'plugin':
                                        #if no return, try unquote
                                        if not self.requestList(file):
                                            file = urllib.unquote(file).replace('",return)','')
                                            # todo fix super fav support
                                            # remove unwanted reference from super.favourites
                                            # try:
                                                # file = (file.split('ActivateWindow(10025,"')[1])
                                            # except:
                                                # pass
                                
                                    fileList.extend(self.getFileList(self.requestList(file), channel, limit, excludeLST))
                                    self.dircount += 1
                                    self.log('getFileList, dircount = ' + str(self.dircount) +'/'+ str(dirlimit))
                                    
                                elif self.filecount >= limit:
                                    break
                            else:
                                self.log('getFileList, ' + label.lower() + ' in excludeLST')                                        
            except Exception,e:
                self.log('getFileList, failed...' + str(e))
                self.log(traceback.format_exc(), xbmc.LOGERROR)
                
        if self.channels[channel - 1].mode & MODE_ORDERAIRDATE > 0:
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])
            for seepitem in seasoneplist:
                fileList.append(seepitem[2])

        # Stop playback when called during plugin parsing.
        if self.background == False and xbmc.Player().isPlaying():
            json_query = ('{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"stop"},"id":1}')
            self.sendJSON(json_query);  
                                                                               
        self.log("getFileList, fileList return = " + str(len(fileList)))      
        # cleanup  
        del seasoneplist[:]                 
        return fileList

        
    def getItem(self, mediapath):
        self.log('getItem') 
    
    
    def getStreamDetails(self, mediapath):
        self.log('getStreamDetails') 
        
        
    def setResetLST(self, channel=None):
        if not channel:
            channel = self.settingChannel
        self.myOverlay.ResetLST.append(channel)
        self.myOverlay.ResetLST = sorted(set(self.myOverlay.ResetLST))
        REAL_SETTINGS.setSetting('ResetLST', str(self.myOverlay.ResetLST))
        self.log('setResetLST added channel ' + str(channel))
        
        
    def delResetLST(self, channel=None):
        if not channel:
            channel = self.settingChannel
        if channel in self.myOverlay.ResetLST:
            self.myOverlay.ResetLST =  [x for x in self.myOverlay.ResetLST if x!=channel]
            REAL_SETTINGS.setSetting('ResetLST', str(self.myOverlay.ResetLST))
            self.log('delResetLST removed channel ' + str(channel))
            

    def dict2tmpstr(self, dList):
        self.log('dict2tmpstr')
        filelist = []
        self.startDate = self.startTime
        for i in range(dList):
            dict = dList[i]
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.startDate))
            self.startDate += int(dict['duration'])
            GenreLiveID = [dict['genre'], dict['type'], dict['id'], dict['thumburl'], False, 1, dict['rating'], dict['hd'], dict['cc'], dict['stars']]
            filelist.append(self.makeTMPSTR(dict['duration'], dict['title'], dict['subtitle'], dict['description'], GenreLiveID, dict['link'], timestamp))
        return filelist