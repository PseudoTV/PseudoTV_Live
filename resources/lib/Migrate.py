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

import subprocess, os, re, sys, time, datetime
import xbmcaddon, xbmc, xbmcgui, xbmcvfs
import Settings, ChannelList
import urllib, urllib2, httplib, random

from Globals import *
from xml.etree import ElementTree as ET
from FileAccess import FileAccess
from urllib import unquote
from utils import *
from parsers import  ustvnow

class Migrate:

    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Migrate: ' + msg, level)
          
   
    def onInit(self):
        self.log("onInit")
        chkLowPower()
        
        
    def migrate(self):
        self.log("migrate")
        chanlist = ChannelList.ChannelList()
        chanlist.background = True
        chanlist.forceReset = True
        chanlist.createlist = True
        
        # If Autotune is enabled direct to autotuning
        if REAL_SETTINGS.getSetting("Autotune") == "true" and REAL_SETTINGS.getSetting("Warning1") == "true":
            self.log("autoTune, migrate")
            if self.autoTune():
                return True

        
    def autoTune(self):
        self.log('autoTune')
        chanlist = ChannelList.ChannelList()
        Youtube = chanlist.youtube_player_ok()
        chanlist.background = True
        chanlist.makenewlists = True
        chanlist.forceReset = True
        
        self.updateDialog = xbmcgui.DialogProgress()
        self.updateDialog.create("PseudoTV Live", "Initializing: Autotuning")
        
        #Reserve channel check 
        channelNum = 1       
        if REAL_SETTINGS.getSetting("reserveChannels") == "true":
            self.log('autoTune, using reserve Channels')
            channelNum = 500
        baseNum = channelNum
        self.log('autoTune, Starting channelNum = ' + str(baseNum))
        
        # LiveTV - PVR
        self.updateDialogProgress = 0
        if REAL_SETTINGS.getSetting("autoFindLivePVR") == "true":
            self.log("autoTune, adding Live PVR Channels")
            channelNum = baseNum
            PVRChannels = chanlist.getPVRChannels()
            for i in range(len(PVRChannels)):
                try:
                    CHid = PVRChannels[i][0]
                    CHname = chanlist.cleanLabels(PVRChannels[i][1])
                    CHthmb = PVRChannels[i][2]
                    if REAL_SETTINGS.getSetting("respectChannels") == "true":
                        channelNum = self.chkChannelNum(int(CHid))
                    else:
                        channelNum = self.chkChannelNum(channelNum)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "8")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", CHid)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", chanlist.getPVRLink(i))
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", 'pvr')
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", CHname + ' PVR')
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")                        
                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding PVR Channels",CHname)  
                except:
                    pass
        
        # LiveTV - HDHomeRun
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindLiveHDHR")  == "true":
            self.log("autoTune, adding Live HDHomeRun Channels")
            channelNum = baseNum
            chanlist.cached_readXMLTV = []
            HDHRChannels = chanlist.getHDHRChannels(True)
            for i in range(len(HDHRChannels)):
                try:
                    CHid = HDHRChannels[i][0]
                    CHname = chanlist.cleanLabels(HDHRChannels[i][1])
                    link = HDHRChannels[i][4]
                    if REAL_SETTINGS.getSetting("respectChannels") == "true":
                        channelNum = self.chkChannelNum(int(CHid))
                    else:
                        channelNum = self.chkChannelNum(channelNum)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "8")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", CHid)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", link)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", "hdhomerun")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "2")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", CHname + ' HDHR')    
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "13")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_opt_1", "2") 
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")                        
                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding HDHomeRun Channels",CHname)  
                except Exception,e:
                    self.log("autoFindLiveHD 2, Failed! " + str(e))
         
        # LiveTV - USTVnow
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindUSTVNOW") == "true" and isUSTVnow() != False:
            self.log("autoTune, adding USTVnow Channels")
            channelNum = baseNum
            USTVChannels = chanlist.getUSTVChannels()
            for i in range(len(USTVChannels)):
                try:
                    name, path, thumb = USTVChannels[i]
                    chname = name + ' USTV'
                    channelNum = self.chkChannelNum(channelNum)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "8")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", name)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", path)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", "ustvnow")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "2")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", chname) 
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "13")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_opt_1", "2")   
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")                           
                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding USTVnow Channels",name)
                except:
                    pass

        # Custom Playlists
        if REAL_SETTINGS.getSetting("autoFindCustom") == "true":
            self.log("autoTune, adding Custom SmartPlaylists")
            channelNum = baseNum
            Music_path = 'special://profile/playlists/music'
            Mixed_path = 'special://profile/playlists/mixed'
            Video_path = 'special://profile/playlists/video'
            xsp_path = [Music_path, Mixed_path, Video_path]
            for path in xsp_path:
                xspLst = chanlist.walk(path,['.xsp'])
                for xsp in xspLst:
                    if xsp.endswith('.xsp') and len(re.findall("channel_",xsp)) != 0:
                        if REAL_SETTINGS.getSetting("respectChannels") == "true":
                            channelNum = self.chkChannelNum(int((re.findall("channel_(\d+)", xsp))[0]))
                        else:
                            channelNum = self.chkChannelNum(channelNum)
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "0")
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", xbmc.translatePath(xsp))
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                        self.updateDialog.update(self.updateDialogProgress,"PseudoTV Live","Found " + uni(chanlist.getSmartPlaylistName(xsp)),"")

        # Custom SuperFavs
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindSuperFav") == "true" :
            self.log("autoTune, adding Super Favourites")
            channelNum = baseNum
            plugin_details = chanlist.requestList('plugin://plugin.program.super.favourites')
            
            for SF in plugin_details:
                include = False
                
                try:
                    filetypes = re.search('"filetype" *: *"(.*?)"', SF)
                    labels = re.search('"label" *: *"(.*?)"', SF)
                    files = re.search('"file" *: *"(.*?)"', SF)

                    #if core variables have info proceed
                    if filetypes and files and labels:
                        filetype = filetypes.group(1)
                        file = (files.group(1))
                        label = (labels.group(1))
                        
                        if label.lower() not in SF_FILTER:
                            if filetype == 'directory':
                                if label.lower() in ['pseudotv']:
                                    plugin_details = chanlist.requestList(file)
                                    include = True
                                
                                elif label.lower().startswith('channel'):
                                    plugin_details = chanlist.requestList(file)
                                    include = True

                                if include == True:
                                    channelNum = self.chkChannelNum(channelNum)         
                                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "15")
                                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", file)
                                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "")
                                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(MEDIA_LIMIT))
                                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "0")
                                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", label)
                                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Super Favourites",label)   
                except:
                    pass
                  
        #TV - Networks/Genres
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if (REAL_SETTINGS.getSetting("autoFindNetworks") == "true" or REAL_SETTINGS.getSetting("autoFindTVGenres") == "true"):
            self.log("autoTune, Searching for TV Channels")
            chanlist.fillTVInfo()

        # need to add check for auto find network channels
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindNetworks") == "true":
            self.log("autoTune, adding TV Networks")
            channelNum = baseNum
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding TV Networks"," ")

            for i in range(len(chanlist.networkList)):
                channelNum = self.chkChannelNum(channelNum)
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "1")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1",uni(chanlist.networkList[i]))
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "4")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding TV Network",uni(chanlist.networkList[i]))
        
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindTVGenres") == "true":
            self.log("autoTune, adding TV Genres")
            channelNum = baseNum
            for i in range(len(chanlist.showGenreList)):
                if chanlist.showGenreList[i] != '':
                    channelNum = self.chkChannelNum(channelNum)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "3")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", uni(chanlist.showGenreList[i]))
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "4")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding TV Genres",uni(chanlist.showGenreList[i]) + " TV")
        
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if (REAL_SETTINGS.getSetting("autoFindStudios") == "true" or REAL_SETTINGS.getSetting("autoFindMovieGenres") == "true"):
            chanlist.fillMovieInfo()

        self.updateDialogProgress = 24
        if REAL_SETTINGS.getSetting("autoFindStudios") == "true":
            self.log("autoTune, adding Movie Studios")
            channelNum = baseNum
            for i in range(len(chanlist.studioList)):
                self.updateDialogProgress = self.updateDialogProgress + (10/len(chanlist.studioList))
                channelNum = self.chkChannelNum(channelNum)
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "2")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", uni(chanlist.studioList[i]))
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Movie Studios",uni(chanlist.studioList[i]))
                
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindMovieGenres") == "true":
            self.log("autoTune, adding Movie Genres")
            channelNum = baseNum
            for i in range(len(chanlist.movieGenreList)):
                self.updateDialogProgress = self.updateDialogProgress + (10/len(chanlist.movieGenreList))
                if chanlist.movieGenreList[i] != '':
                    channelNum = self.chkChannelNum(channelNum)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "4")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", uni(chanlist.movieGenreList[i]))
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Movie Genres","Found " + uni(chanlist.movieGenreList[i]) + " Movies")
                
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindMixGenres") == "true":
            chanlist.fillMixedGenreInfo()
        
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindMixGenres") == "true":
            self.log("autoTune, adding Mixed Genres")
            channelNum = baseNum
            for i in range(len(chanlist.mixedGenreList)):
                if chanlist.mixedGenreList[i] != '':
                    channelNum = self.chkChannelNum(channelNum)
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "5")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", uni(chanlist.mixedGenreList[i]))
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "4")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Mixed Genres",uni(chanlist.mixedGenreList[i]) + " Mix")
        
        #recent movie/tv
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100) 
        if REAL_SETTINGS.getSetting("autoFindRecent") == "true":
            self.log("autoTune, adding Recent TV/Movies")
            channelNum = baseNum
            channelNum = self.chkChannelNum(channelNum)
            TVflename = chanlist.createRecentlyAddedTV()
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "0")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", TVflename)
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "3")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "Recent TV")  
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "12")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_3_id", "13")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_3_opt_1", "4")  
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recent TV"," ")
            channelNum = self.chkChannelNum(channelNum)
            Movieflename = chanlist.createRecentlyAddedMovies()     
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "0")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", Movieflename)
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "2")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "Recent Movies")  
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "13")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_opt_1", "4")  
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recent Movies"," ")
           
        #3D movies
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100) 
        if REAL_SETTINGS.getSetting("autoFind3DMovies") == "true":
            self.log("autoTune, adding 3D Movies")
            channelNum = baseNum
            if len(chanlist.movie3Dlist) >= MEDIA_LIMIT:
                channelNum = self.chkChannelNum(channelNum)
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "0")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding 3D Movies"," ")
                
        #Music Genre
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindMusicGenres") == "true":
            self.log("autoTune, adding Music Genres")
            channelNum = baseNum
            chanlist.fillMusicInfo()
            for i in range(len(chanlist.musicGenreList)):
                channelNum = self.chkChannelNum(channelNum)
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "12")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", uni(chanlist.musicGenreList[i]))
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "4")
                ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Music Genres",uni(chanlist.musicGenreList[i]) + " Music")
        
        #Local Directory
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindVideosLocal") != "":
            self.log("autoTune, adding Local Videos")
            channelNum = baseNum 
            channelNum = self.chkChannelNum(channelNum)
            LocalVideo = str(REAL_SETTINGS.getSetting('autoFindVideosLocal'))  
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "7")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "" +LocalVideo+ "")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(MEDIA_LIMIT))
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "1")     
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Local Videos"," ")

        #Youtube - PseudoNetwork
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindCommunity_PseudoNetworks") == "true" and isCompanionInstalled() == True:
            self.log("autoTune, adding PseudoNetworks")
            channelNum = baseNum
            detail = uni(chanlist.requestList('plugin://plugin.video.pseudo.companion/?mode=3000&name=PseudoNetworks&previous=getOnlineMedia&url'))
            show_busy_dialog()
            for f in detail:
                files = re.search('"file" *: *"(.*?)",', f)
                filetypes = re.search('"filetype" *: *"(.*?)",', f)
                labels = re.search('"label" *: *"(.*?)",', f)
                if filetypes and labels and files:
                    filetype = filetypes.group(1)
                    name = chanlist.cleanLabels(labels.group(1))
                    file = (files.group(1).replace("\\\\", "\\"))
                    if filetype == 'directory':
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "15")
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", file)
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "")
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(MEDIA_LIMIT))
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "0")
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", name)  
                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                        self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding PseudoNetworks",name)
                        channelNum = self.chkChannelNum(channelNum)
                hide_busy_dialog()

        #Youtube - Seasonal
        self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        if REAL_SETTINGS.getSetting("autoFindCommunity_Youtube_Seasonal") == "true":
            channelNum = baseNum
            today = datetime.datetime.now()
            month = today.strftime('%B')
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "10")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", month)
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "31")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(MEDIA_LIMIT))
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "0")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "2")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "Seasonal Channel")  
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "13")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_opt_1", "168")  
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
            self.updateDialog.update(self.updateDialogProgress,"Auto Tune","adding Youtube Networks","Seasonal Channel")
            channelNum = self.chkChannelNum(channelNum)

        # #RSS
        # self.updateDialogProgress = int(round((CHANNEL_LIMIT - channelNum)/CHANNEL_LIMIT)*100)
        # if REAL_SETTINGS.getSetting("autoFindCommunity_RSS") == "true" and isCompanionInstalled() == True:
            # self.log("autoTune, adding Recommend RSS")
            # self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recommend RSS"," ")
            # NameLst, Option1LST, Option2LST, Option3LST, Option4LST = chanlist.fillExternalList('RSS','','',True)
            # channelNum = self.tuneList(channelNum, '11', fillLst[0], fillLst[1], fillLst[2], fillLst[3], fillLst[4])

        # #Reserve channel clear old            
        if REAL_SETTINGS.getSetting("reserveChannels") == "true":
            self.clearReserved(baseNum)
        
        # reset auto tune settings        
        REAL_SETTINGS.setSetting('Autotune', "false")
        REAL_SETTINGS.setSetting('Warning1', "false") 
        REAL_SETTINGS.setSetting("autoFindCustom","false")
        REAL_SETTINGS.setSetting("autoFindSuperFav","false") 
        REAL_SETTINGS.setSetting('autoFindLivePVR', "false")
        REAL_SETTINGS.setSetting('autoFindLiveHDHR', "0")
        REAL_SETTINGS.setSetting('autoFindUSTVNOW', "false")  
        REAL_SETTINGS.setSetting("autoFindNetworks","false")
        REAL_SETTINGS.setSetting("autoFindStudios","false")
        REAL_SETTINGS.setSetting("autoFindTVGenres","false")
        REAL_SETTINGS.setSetting("autoFindMovieGenres","false")
        REAL_SETTINGS.setSetting("autoFindMixGenres","false")
        REAL_SETTINGS.setSetting("autoFind3DMovies","false")    
        REAL_SETTINGS.setSetting("autoFindRecent","false")      
        REAL_SETTINGS.setSetting("autoFindMusicGenres","false")
        REAL_SETTINGS.setSetting("autoFindVideosLocal","")
        REAL_SETTINGS.setSetting("autoFindCommunity_PseudoNetworks","false")  
        REAL_SETTINGS.setSetting("ForceChannelReset","true")
        ADDON_SETTINGS.setSetting('LastExitTime', str(int(time.time())))
        ADDON_SETTINGS.writeSettings()
        self.log('autoTune, return')
        self.updateDialogProgress = 100
        self.updateDialog.close()
        
        
    def getChtype(self, channel):
        self.log("getChtype")
        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_type"))
        except:
            chantype = 9999
        return chantype
            
            
    # find next available channel
    def fixChannel(self, channel):
        self.log("fixChannel")
        while self.getChtype(channel) != 9999:
            channel +=1
        return channel
     
        
    def chkChannelNum(self, channelNum):
        self.log("chkChannelNum, channelNum = " + str(channelNum))
        if channelNum > CHANNEL_LIMIT:
            channelNum = int(round(channelNum/10))
        NumRange = range(1, CHANNEL_LIMIT+1)
        Numlst = NumRange[channelNum-1:] + NumRange[:channelNum-1]
        for Num in Numlst:
            if self.getChtype(Num) == 9999:
                return Num
        return CHANNEL_LIMIT
        
        
    def clearReserved(self, baseNum):
        self.log("clearReserved")
        channelNum = self.chkChannelNum(baseNum)
        for channel in range(channelNum, CHANNEL_LIMIT+1):
            ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", "9999")