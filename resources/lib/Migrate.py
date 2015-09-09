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
import Settings, Globals, ChannelList
import urllib, urllib2, httplib, random

from Globals import *
from xml.etree import ElementTree as ET
from FileAccess import FileAccess
from urllib import unquote
from utils import *

class Migrate:

    def log(self, msg, level = xbmc.LOGDEBUG):
        Globals.log('Migrate: ' + msg, level)

        
    def logDebug(self, msg, level = xbmc.LOGDEBUG):
        if Globals.DEBUG == 'true':
            Globals.log('Migrate: ' + msg, level)
    
    
    def migrate(self):
        self.log("migrate")
        settingsFile = xbmc.translatePath(os.path.join(Globals.SETTINGS_LOC, 'settings2.xml'))    
        chanlist = ChannelList.ChannelList()
        chanlist.background = True
        chanlist.forceReset = True
        chanlist.createlist = True

        # If Autotune is enabled direct to autotuning
        if Globals.REAL_SETTINGS.getSetting("Autotune") == "true" and Globals.REAL_SETTINGS.getSetting("Warning1") == "true":
            self.log("autoTune, migrate")
            if self.autoTune():
                return True

        
    def autoTune(self):
        self.log('autoTune, Init')
        curtime = time.time()
        chanlist = ChannelList.ChannelList()
        chanlist.background = True
        chanlist.makenewlists = True
        chanlist.forceReset = True
        settingsFile = xbmc.translatePath(os.path.join(Globals.SETTINGS_LOC, 'settings2.xml'))   
        
        #Reserve channel check            
        if Globals.REAL_SETTINGS.getSetting("reserveChannels") == "true":
            print 'Reserved for Autotune'
            channelNum = 501
        else:
            channelNum = 1
        
        self.log('autoTune, Starting channelNum = ' + str(channelNum))
               
        updateDialogProgress = 0
        self.updateDialog = xbmcgui.DialogProgress()
        self.updateDialog.create("PseudoTV Live", "Auto Tune")
        Youtube = chanlist.youtube_player_ok()
        
        # Custom Playlists
        self.updateDialogProgress = 1
        if Globals.REAL_SETTINGS.getSetting("autoFindCustom") == "true" :
            self.log("autoTune, adding Custom Channel")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Custom Channels"," ")
            CChan = 0
            
            for CChan in range(999):
                if xbmcvfs.exists(xbmc.translatePath('special://profile/playlists/music') + '/Channel_' + str(CChan + 1) + '.xsp'):
                    self.log("autoTune, adding Custom Music Playlist Channel")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "12")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", str(xbmc.translatePath('special://profile/playlists/music/') + "Channel_" + str(CChan + 1) + '.xsp'))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", Globals.uni(chanlist.cleanString(chanlist.getSmartPlaylistName(xbmc.translatePath('special://profile/playlists/music') + '/Channel_' + str(CChan + 1) + '.xsp'))))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                    self.updateDialog.update(self.updateDialogProgress,"PseudoTV Live","Found " + Globals.uni(chanlist.getSmartPlaylistName(xbmc.translatePath('special://profile/playlists/music') + '/Channel_' + str(CChan + 1) + '.xsp')),"")
                    channelNum += 1
                elif xbmcvfs.exists(xbmc.translatePath('special://profile/playlists/mixed') + '/Channel_' + str(CChan + 1) + '.xsp'):
                    self.log("autoTune, adding Custom Mixed Playlist Channel")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", str(xbmc.translatePath('special://profile/playlists/mixed/') + "Channel_" + str(CChan + 1) + '.xsp'))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", Globals.uni(chanlist.cleanString(chanlist.getSmartPlaylistName(xbmc.translatePath('special://profile/playlists/mixed') + '/Channel_' + str(CChan + 1) + '.xsp'))))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                    self.updateDialog.update(self.updateDialogProgress,"PseudoTV Live","Found " + Globals.uni(chanlist.getSmartPlaylistName(xbmc.translatePath('special://profile/playlists/mixed') + '/Channel_' + str(CChan + 1) + '.xsp')),"")
                    channelNum += 1
                elif xbmcvfs.exists(xbmc.translatePath('special://profile/playlists/video') + '/Channel_' + str(CChan + 1) + '.xsp'):
                    self.log("autoTune, adding Custom Video Playlist Channel")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", str(xbmc.translatePath('special://profile/playlists/video/') + "Channel_" + str(CChan + 1) + '.xsp'))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", Globals.uni(chanlist.cleanString(chanlist.getSmartPlaylistName(xbmc.translatePath('special://profile/playlists/video') + '/Channel_' + str(CChan + 1) + '.xsp'))))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                    self.updateDialog.update(self.updateDialogProgress,"PseudoTV Live","Found " + Globals.uni(chanlist.getSmartPlaylistName(xbmc.translatePath('special://profile/playlists/video') + '/Channel_' + str(CChan + 1) + '.xsp')),"")
                    channelNum += 1

        # Custom SuperFavs
        self.updateDialogProgress = 5
        if Globals.REAL_SETTINGS.getSetting("autoFindSuperFav") == "true" :
            self.log("autoTune, adding Super Favourites")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Super Favourites"," ")
            SuperFav = chanlist.plugin_ok('plugin.program.super.favourites')
            SF = 0
            if SuperFav == True:
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
                                    SFmatch = unquote(file)
                                    SFmatch = SFmatch.split('Super+Favourites')[1].replace('\\','/')
                                    self.log("SFAutotune, SFmatch = " + SFmatch)
                                    print SFmatch.lower()
                                    if (SFmatch.lower()).startswith('/pseudotv_live'):
                                        plugin_details = chanlist.requestList(file)
                                        include = True
                                    elif (SFmatch[0:9]).lower() == '/channel_':
                                        plugin_details = chanlist.requestList(file)
                                        include = True
                                    if include == True:
                                        SFmatch = SFmatch.split('&')[0]
                                        SFname = SFmatch.replace('/PseudoTV_Live/','').replace('/','')
                                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "15")
                                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", unquote(file))
                                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "")
                                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(Globals.MEDIA_LIMIT))
                                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "0")
                                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", SFname)
                                        ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                                        self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Super Favourites",SFname)   
                                        channelNum += 1       
                    except:
                        pass
                
        # LiveTV - PVR
        self.updateDialogProgress = 10
        if Globals.REAL_SETTINGS.getSetting("autoFindLivePVR") == "true":
            self.log("autoTune, adding Live PVR Channels")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding PVR Channels"," ")
            PVRnum = 0
            chanlist.cached_readXMLTV = []
            try:
                PVRNameList, PVRPathList = chanlist.fillPVR()

                for PVRnum in range(len(PVRNameList)):
                    CHSetName = ''
                    CHzapit = ''
                    PVRName = chanlist.cleanLabels(PVRNameList[PVRnum], 'upper')
                    chid = PVRName.split(' - ')[0]
                    CHname = PVRName.split(' - ')[1]
                    path = PVRPathList[PVRnum]
                
                    if Globals.REAL_SETTINGS.getSetting("PVR_Listing") == '1':
                        listing = 'xmltv'
                        xmltvLOC = xbmc.translatePath(Globals.REAL_SETTINGS.getSetting("xmltvLOC"))
                        xmlTvFile = os.path.join(xmltvLOC, 'xmltv.xml')
                        if xbmcvfs.exists(xmlTvFile): 
                            CHSetName, CHzapit = chanlist.findZap2itID(CHname, xmlTvFile)
                    else:
                        listing = 'pvr'
                        CHSetName, CHzapit = chanlist.findZap2itID(CHname, listing)
                    
                    if not CHSetName:
                        CHSetName = CHname
                    if not CHzapit:
                        CHzapit = "NA"

                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "8")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", CHzapit)
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", path)
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", listing)
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", CHname + ' PVR')
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")                        
                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding PVR Channels",CHname)  
                    channelNum += 1 
            except:
                pass
        
        # LiveTV - HDHomeRun
        self.updateDialogProgress = 11
        if Globals.REAL_SETTINGS.getSetting("autoFindLiveHD") != "0":
            chanlist.cached_readXMLTV = []
            xmltvLOC = xbmc.translatePath(Globals.REAL_SETTINGS.getSetting("xmltvLOC"))
            xmlTvFile = os.path.join(xmltvLOC, 'xmltv.xml')
            
            # LiveTV - HDHomeRun - STRM
            if Globals.REAL_SETTINGS.getSetting("autoFindLiveHD") == "1" and Globals.REAL_SETTINGS.getSetting('autoFindLiveHDPath'):
                self.log("autoTune, adding Live HDHomeRun Strm Channels")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding HDHomeRun STRM Channels"," ")
                HDstrmPath = Globals.REAL_SETTINGS.getSetting('autoFindLiveHDPath') + '/'
                HDSTRMnum = 0
                
                try:                
                    LocalLST = str(xbmcvfs.listdir(HDstrmPath)[1]).replace("[","").replace("]","").replace("'","")
                    LocalLST = LocalLST.split(", ")
                    
                    for HDSTRMnum in range(len(LocalLST)):
                        if '.strm' in (LocalLST[HDSTRMnum]):
                            LocalFLE = (LocalLST[HDSTRMnum])
                            filename = (HDstrmPath + LocalFLE)
                            CHname = os.path.splitext(LocalFLE)[0]
                            CHSetName = ''
                            CHzapit = ''
                                    
                            if xbmcvfs.exists(xmlTvFile): 
                                CHSetName, CHzapit = chanlist.findZap2itID(CHname, xmlTvFile)
                                
                            if not CHSetName:
                                CHSetName = CHname
                            if not CHzapit:
                                CHzapit = "NA"
                                
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "8")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", CHzapit)
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", filename)
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", "xmltv")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", CHname + ' HDHR')   
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")                                                            
                            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding HDHomeRun STRM Channels",CHname)
                            channelNum += 1
                except Exception,e:
                    self.log("autoFindLiveHD 1, Failed! " + str(e))

            # LiveTV - HDHomeRun - UPNP
            elif Globals.REAL_SETTINGS.getSetting("autoFindLiveHD") == "2":
                self.log("autoTune, adding Live HDHomeRun UPNP Channels")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding HDHomeRun UPNP Channels"," ")
                HDUPNPnum = 0
                try:
                    HDHRNameList, HDHRPathList = chanlist.fillHDHR(True)
                    HDHRNameList = HDHRNameList[1:]
                    HDHRPathList = HDHRPathList[1:]
                    
                    for HDUPNPnum in range(len(HDHRNameList)):
                        HDHRname = HDHRNameList[HDUPNPnum]
                        CHSetName = ''
                        CHzapit = ''

                        CHid = HDHRname.split(' - ')[0]
                        CHname = HDHRname.split(' - ')[1]
                        CHname = chanlist.cleanLabels(CHname, 'upper')
                        path = HDHRPathList[HDUPNPnum]

                        if xbmcvfs.exists(xmlTvFile): 
                            CHSetName, CHzapit = chanlist.findZap2itID(CHname, xmlTvFile)
                                
                        if not CHSetName:
                            CHSetName = CHname
                        if not CHzapit:
                            CHzapit = "NA"
                                
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "8")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", CHzapit)
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", path)
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", "xmltv")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", CHname + ' HDHR')    
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")                        
                        self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding HDHomeRun UPNP Channels",CHname)  
                        channelNum += 1 
                except Exception,e:
                    self.log("autoFindLiveHD 2, Failed! " + str(e))
             
        # LiveTV - USTVnow
        self.updateDialogProgress = 13
        if Globals.REAL_SETTINGS.getSetting("autoFindUSTVNOW") == "true":
            self.log("autoTune, adding USTVnow Channels")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding USTVnow Channels"," ")
            USTVnum = 0
            chanlist.cached_readXMLTV = []
            USTVnow = chanlist.plugin_ok('plugin.video.ustvnow')
            
            if USTVnow == True:   
                try:
                    file_detail = chanlist.requestList("plugin://plugin.video.ustvnow/live?mode=live")
                    if not file_detail:         
                        file_detail = chanlist.requestList("plugin://plugin.video.ustvnow/live?mode=live")
                    for USTVnum in file_detail:      
                        files = re.search('"file" *: *"(.*?)"', USTVnum)
                        labels = re.search('"label" *: *"(.*?)"', USTVnum)
                        thumbnails = re.search('"thumbnail" *: *"(.*?)"', USTVnum)
                      
                        if files and labels:
                            file = files.group(1)
                            label = labels.group(1)
                            CHname = label.split(' - ')[0]
                            inSet = False
                                    
                            if thumbnails != None and len(thumbnails.group(1)) > 0:
                                thumbnail = thumbnails.group(1)
                                GrabLogo(thumbnail, CHname + ' USTV')
                                 
                            # CHSetName, CHzapit = chanlist.findZap2itID('USTVnow - ' + CHname, PTVLXML)
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "8")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "USTVnow - "+CHname)
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", file)
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", "ptvlguide")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", CHname + ' USTV')   
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")                           
                            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding USTVnow Channels",CHname)
                            channelNum += 1
                except:
                    pass

                    
        #TV - Networks/Genres
        self.updateDialogProgress = 20
        if (Globals.REAL_SETTINGS.getSetting("autoFindNetworks") == "true" or Globals.REAL_SETTINGS.getSetting("autoFindTVGenres") == "true"):
            self.log("autoTune, Searching for TV Channels")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","Searching for TV Channels"," ")
            chanlist.fillTVInfo()

        # need to add check for auto find network channels
        self.updateDialogProgress = 21
        if Globals.REAL_SETTINGS.getSetting("autoFindNetworks") == "true":
            self.log("autoTune, adding TV Networks")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding TV Networks"," ")

            for i in range(len(chanlist.networkList)):
                # channelNum = self.initialAddChannels(chanlist.networkList, 1, channelNum)
                # add network presets
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1",Globals.uni(chanlist.networkList[i]))
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "12")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding TV Network",Globals.uni(chanlist.networkList[i]))
                channelNum += 1
        
        self.updateDialogProgress = 22
        if Globals.REAL_SETTINGS.getSetting("autoFindTVGenres") == "true":
            self.log("autoTune, adding TV Genres")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding TV Genres","")

            # channelNum = self.initialAddChannels(chanlist.showGenreList, 3, channelNum)
            for i in range(len(chanlist.showGenreList)):
                # add network presets
                if chanlist.showGenreList[i] != '':
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "3")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", Globals.uni(chanlist.showGenreList[i]))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding TV Genres",Globals.uni(chanlist.showGenreList[i]) + " TV")
                    channelNum += 1
        
        self.updateDialogProgress = 23
        if (Globals.REAL_SETTINGS.getSetting("autoFindStudios") == "true" or Globals.REAL_SETTINGS.getSetting("autoFindMovieGenres") == "true"):
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","Searching for Movie Channels","")
            chanlist.fillMovieInfo()

        self.updateDialogProgress = 24
        if Globals.REAL_SETTINGS.getSetting("autoFindStudios") == "true":
            self.log("autoTune, adding Movie Studios")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Movie Studios"," ")

            for i in range(len(chanlist.studioList)):
                self.updateDialogProgress = self.updateDialogProgress + (10/len(chanlist.studioList))
                # add network presets
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "2")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", Globals.uni(chanlist.studioList[i]))
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Movie Studios",Globals.uni(chanlist.studioList[i]))
                channelNum += 1
                
        self.updateDialogProgress = 25
        if Globals.REAL_SETTINGS.getSetting("autoFindMovieGenres") == "true":
            self.log("autoTune, adding Movie Genres")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Movie Genres"," ")

            # channelNum = self.initialAddChannels(chanlist.movieGenreList, 4, channelNum)
            for i in range(len(chanlist.movieGenreList)):
                self.updateDialogProgress = self.updateDialogProgress + (10/len(chanlist.movieGenreList))
                # add network presets
                if chanlist.movieGenreList[i] != '':
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "4")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", Globals.uni(chanlist.movieGenreList[i]))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Movie Genres","Found " + Globals.uni(chanlist.movieGenreList[i]) + " Movies")
                    channelNum += 1
                
        self.updateDialogProgress = 26
        if Globals.REAL_SETTINGS.getSetting("autoFindMixGenres") == "true":
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","Searching for Mixed Channels"," ")
            chanlist.fillMixedGenreInfo()
        
        self.updateDialogProgress = 27
        if Globals.REAL_SETTINGS.getSetting("autoFindMixGenres") == "true":
            self.log("autoTune, adding Mixed Genres")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Mixed Genres","")

            for i in range(len(chanlist.mixedGenreList)):
                # add network presets
                if chanlist.mixedGenreList[i] != '':
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "5")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", Globals.uni(chanlist.mixedGenreList[i]))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                    self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Mixed Genres",Globals.uni(chanlist.mixedGenreList[i]) + " Mix")
                    channelNum += 1
        
        #recent movie/tv
        self.updateDialogProgress = 28  
        if Globals.REAL_SETTINGS.getSetting("autoFindRecent") == "true":
            self.log("autoTune, adding Recent TV/Movies")
            
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recent TV"," ")
            TVflename = chanlist.createRecentlyAddedTV()
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "0")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", TVflename)
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "3")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "Recent TV")  
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "12")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_3_id", "13")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_3_opt_1", "4")  
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
            channelNum += 1
            
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recent Movies"," ")
            Movieflename = chanlist.createRecentlyAddedMovies()     
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "0")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", Movieflename)
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "2")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "Recent Movies")  
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "13")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_opt_1", "4")  
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
            channelNum += 1
           
        #3D movies
        self.updateDialogProgress = 28  
        if Globals.REAL_SETTINGS.getSetting("autoFind3DMovies") == "true":
            self.log("autoTune, adding 3D Movies")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding 3D Movies"," ")
            if len(chanlist.movie3Dlist) >= Globals.MEDIA_LIMIT:
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                channelNum += 1
                
        #Music Genre
        self.updateDialogProgress = 50
        if Globals.REAL_SETTINGS.getSetting("autoFindMusicGenres") == "true":
            self.log("autoTune, adding Music Genres")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","Searching for Music Channels"," ")
            chanlist.fillMusicInfo()
            
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Music Genres"," ")
            for i in range(len(chanlist.musicGenreList)):
                # add network presets
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "12")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", Globals.uni(chanlist.musicGenreList[i]))
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Music Genres",Globals.uni(chanlist.musicGenreList[i]) + " Music")
                channelNum += 1
        
        #Music Videos - My Music
        self.updateDialogProgress = 53
        if Globals.REAL_SETTINGS.getSetting("autoFindMusicVideosMusicTV") == "true":
            self.log("autoTune, adding My MusicTV Music Videos")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding My MusicTV Music Videos"," ")
               
            MusicTV = False
            MusicTV = chanlist.plugin_ok('plugin.video.my_music_tv')
            
            if MusicTV == True:
                for i in range(999):
                    path = xbmc.translatePath("special://profile/addon_data/plugin.video.my_music_tv/cache/plist")
                    fle = os.path.join(path,"Channel_" + str(i) + ".xml.plist")
                    
                    if xbmcvfs.exists(xbmc.translatePath(fle)):
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "13")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "2")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "Channel_" + str(i))
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(Globals.MEDIA_LIMIT))
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "1")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "2")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "My MusicTV " + str(i))  
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "18")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_opt_1", "No")
                        Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                        self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding My MusicTV Music Videos","Channel " + str(i))
                        channelNum += 1
 
        #Music Videos - Last.fm user
        self.updateDialogProgress = 53
        if Globals.REAL_SETTINGS.getSetting("autoFindMusicVideosLastFM") == "true":
            self.log("autoTune, adding Last.FM Music Videos")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Last.FM Music Videos"," ")
               
            if Youtube != False:
                user = Globals.REAL_SETTINGS.getSetting("autoFindMusicVideosLastFMuser")
                
                # add Last.fm user presets
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "13")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", user)
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(Globals.MEDIA_LIMIT))
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "3")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "Last.FM")  
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "18")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_opt_1", "No")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_3_id", "13")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_3_opt_1", "24")  
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Last.FM Music Videos","User " + user)
                channelNum += 1

        #Music Videos - VevoTV
        self.updateDialogProgress = 58
        if Globals.REAL_SETTINGS.getSetting("autoFindMusicVideosVevoTV") == "true":
            self.log("autoTune, adding VevoTV Music Videos")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding VevoTV Music Videos"," ")
            
            VevoTV = False
            VevoTV = chanlist.plugin_ok('plugin.video.vevo_tv')
            
            if VevoTV == True:

                # add VevoTV presets
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "9")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "5400")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "plugin://plugin.video.vevo_tv/?url=TIVEVSTRUS00&mode=playOfficial")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", "VEVO TV (US: Hits)")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "Sit back and enjoy a 24/7 stream of music videos on VEVO TV.")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "VevoTV - Hits")  
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                channelNum += 1
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "9")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "5400")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "plugin://plugin.video.vevo_tv/?url=TIVEVSTRUS01&mode=playOfficial")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", "VEVO TV (US: Flow)")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "Sit back and enjoy a 24/7 stream of music videos on VEVO TV.")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "VevoTV - Flow")  
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                channelNum += 1
                self.logDebug('channelNum = ' + str(channelNum))
            
        #Music Videos - Local
        self.updateDialogProgress = 60
        if Globals.REAL_SETTINGS.getSetting("autoFindMusicVideosLocal") != "":
            self.log("autoTune, adding Local Music Videos")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Local Music Videos"," ")
            LocalVideo = str(Globals.REAL_SETTINGS.getSetting('autoFindMusicVideosLocal'))
            
            # add Local presets
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "7")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "" +LocalVideo+ "")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(Globals.MEDIA_LIMIT))
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "1")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "Music Videos")  
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")         
            channelNum += 1
            self.logDebug('channelNum = ' + str(channelNum))
        
        
        #Plugin - Youtube
        self.updateDialogProgress = 63
        if Globals.REAL_SETTINGS.getSetting("autoFindYoutube") == "true":
            self.log("autoTune, adding Youtube Favourites & Subscriptions")
            Username = Globals.REAL_SETTINGS.getSetting("autoFindYoutubeUser")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Youtube Favourites & Subscriptions","User " + Username)
            
            if Youtube != False:
            
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "10")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", Username)
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "3")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(Globals.MEDIA_LIMIT))
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", Username + "Subscriptions")  
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")    
                channelNum += 1
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "10")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", Username)
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "4")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(Globals.MEDIA_LIMIT))
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", Username + "Favourites")  
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                channelNum += 1
                self.logDebug('channelNum = ' + str(channelNum))
        
        #Recommend lists#
        self.genre_filter = []
        if Globals.REAL_SETTINGS.getSetting("CN_TV") == "true":
            self.genre_filter.append('TV') 
        if Globals.REAL_SETTINGS.getSetting("CN_Movies") == "true":
            self.genre_filter.append('Movies') 
        if Globals.REAL_SETTINGS.getSetting("CN_Episodes") == "true":
            self.genre_filter.append('Episodes') 
        if Globals.REAL_SETTINGS.getSetting("CN_Sports") == "true":
            self.genre_filter.append('Sports') 
        if Globals.REAL_SETTINGS.getSetting("CN_News") == "true":
            self.genre_filter.append('News') 
        if Globals.REAL_SETTINGS.getSetting("CN_Kids") == "true":
            self.genre_filter.append('Kids') 
        if Globals.REAL_SETTINGS.getSetting("CN_Music") == "true":
            self.genre_filter.append('Music') 
        if Globals.REAL_SETTINGS.getSetting("CN_Other") == "true":
            self.genre_filter.append('Other') 
        
        self.genre_filter = ([x.lower() for x in self.genre_filter if x != ''])
        print 'genre_filter', self.genre_filter
        
        #LiveTV
        self.updateDialogProgress = 70
        if Globals.REAL_SETTINGS.getSetting("autoFindCommunity_LiveTV") == "true" and isCom() == True:
            self.log("autoTune, adding Recommend LiveTV")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recommend LiveTV"," ")
            NameLst, Option1LST, Option2LST, Option3LST, Option4LST = chanlist.fillExternalList('LiveTV','','Community',True)            
            channelNum = self.tuneList(channelNum, '8', NameLst, Option1LST, Option2LST, Option3LST, Option4LST)
            
        #InternetTV
        self.updateDialogProgress = 71
        if Globals.REAL_SETTINGS.getSetting("autoFindCommunity_InternetTV") == "true" and isCom() == True:
            self.log("autoTune, adding Recommend InternetTV")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recommend InternetTV"," ")
            NameLst, Option1LST, Option2LST, Option3LST, Option4LST = chanlist.fillExternalList('InternetTV','','Community',True)            
            channelNum = self.tuneList(channelNum, '9', NameLst, Option1LST, Option2LST, Option3LST, Option4LST)

        if Youtube != False:  
            #Youtube - Channel
            self.updateDialogProgress = 72
            if Globals.REAL_SETTINGS.getSetting("autoFindCommunity_Youtube_Channels") == "true" and isCom() == True:
                self.log("autoTune, adding Recommend Youtube Channels")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recommend Youtube Channels"," ")
                NameLst, Option1LST, Option2LST, Option3LST, Option4LST = chanlist.fillExternalList('YouTube','Channel','',True)
                channelNum = self.tuneList(channelNum, '10', NameLst, Option1LST, Option2LST, Option3LST, Option4LST)
            
            #Youtube - Playlist
            self.updateDialogProgress = 73
            if Globals.REAL_SETTINGS.getSetting("autoFindCommunity_Youtube_Playlists") == "true" and isCom() == True:
                self.log("autoTune, adding Recommend Youtube Playlists")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recommend Youtube Playlists"," ")
                NameLst, Option1LST, Option2LST, Option3LST, Option4LST = chanlist.fillExternalList('YouTube','Playlist','',True)
                channelNum = self.tuneList(channelNum, '10', NameLst, Option1LST, Option2LST, Option3LST, Option4LST)
                
            #Youtube - Channel Network
            self.updateDialogProgress = 74
            if Globals.REAL_SETTINGS.getSetting("autoFindCommunity_Youtube_Networks") == "true" and isCom() == True:
                self.log("autoTune, adding Recommend Youtube Multi Channel")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recommend Youtube Multi Channel"," ")
                NameLst, Option1LST, Option2LST, Option3LST, Option4LST = chanlist.fillExternalList('YouTube','Multi Channel','',True)
                channelNum = self.tuneList(channelNum, '10', NameLst, Option1LST, Option2LST, Option3LST, Option4LST)
            
            #Youtube - Playlist Network
            self.updateDialogProgress = 75
            if Globals.REAL_SETTINGS.getSetting("autoFindCommunity_Youtube_Networks") == "true" and isCom() == True:
                self.log("autoTune, adding Recommend Youtube Multi Playlist")
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recommend Youtube Multi Playlist"," ")
                NameLst, Option1LST, Option2LST, Option3LST, Option4LST = chanlist.fillExternalList('YouTube','Multi Playlist','',True)
                channelNum = self.tuneList(channelNum, '10', NameLst, Option1LST, Option2LST, Option3LST, Option4LST)
            
            #Youtube - Seasonal
            self.updateDialogProgress = 76
            if Globals.REAL_SETTINGS.getSetting("autoFindCommunity_Youtube_Seasonal") == "true" and isCom() == True:
                today = datetime.datetime.now()
                month = today.strftime('%B')
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "10")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", month)
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", "31")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(Globals.MEDIA_LIMIT))
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "2")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "Seasonal Channel")  
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "13")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_opt_1", "168")  
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                self.updateDialog.update(self.updateDialogProgress,"Auto Tune","adding Youtube Networks","Seasonal Channel")
                channelNum += 1 
          
        #RSS
        self.updateDialogProgress = 77
        if Globals.REAL_SETTINGS.getSetting("autoFindCommunity_RSS") == "true" and isCom() == True:
            self.log("autoTune, adding Recommend RSS")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recommend RSS"," ")
            NameLst, Option1LST, Option2LST, Option3LST, Option4LST = chanlist.fillExternalList('RSS','','',True)
            channelNum = self.tuneList(channelNum, '11', NameLst, Option1LST, Option2LST, Option3LST, Option4LST)
            
        #Plugin
        self.updateDialogProgress = 78
        if Globals.REAL_SETTINGS.getSetting("autoFindCommunity_Plugins") == "true" and isCom() == True:
            self.log("autoTune, adding Recommend Plugins")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recommend Plugins"," ")
            NameLst, Option1LST, Option2LST, Option3LST, Option4LST = chanlist.fillExternalList('Plugin','','Community',True)
            channelNum = self.tuneList(channelNum, '15', NameLst, Option1LST, Option2LST, Option3LST, Option4LST)

        #UPNP
        self.updateDialogProgress = 79
        if Globals.REAL_SETTINGS.getSetting("autoFindCommunity_Playon") == "true" and isCom() == True:
            self.log("autoTune, adding Recommend UPNP")
            self.updateDialog.update(self.updateDialogProgress,"AutoTuning","adding Recommend UPNP"," ")
            NameLst, Option1LST, Option2LST, Option3LST, Option4LST = chanlist.fillExternalList('UPNP','','Community',True)
            channelNum = self.tuneList(channelNum, '16', NameLst, Option1LST, Option2LST, Option3LST, Option4LST)

        # Extras - Popcorn Movies
        self.updateDialogProgress = 80
        if Globals.REAL_SETTINGS.getSetting("autoFindPopcorn") == "true" and isDon() == True:
            self.log("autoTune, adding Popcorn Movies")
            self.updateDialog.update(self.updateDialogProgress,"Auto Tune","adding Popcorn Movies"," ")
            
            if Youtube != False:
            
                # AT_PopCat = ['action','adventure','animation','british','comedy','crime','disaster','documentary','drama','eastern','erotic','family','fan+film','fantasy','film+noir','foreign','history','holiday','horror','indie','kids','music','musical','mystery','neo-noir','road+movie','romance','science+fiction','short','sport','sports+film','suspense','thriller','tv+movie','war','western']
                # ATPopCat = AT_PopCat[int(Globals.REAL_SETTINGS.getSetting('autoFindPopcornGenre'))]
                   
                # AT_PopYear = ['2010-Now','2000-2010','1990-2000','1980-1990','1970-1980','1960-1970','1950-1960','1940-1950','1930-1940','1920-1930','1910-1920']
                # ATPopYear = AT_PopYear[int(Globals.REAL_SETTINGS.getSetting('autoFindPopcornYear'))]
                
                # AT_PopRes = ['480','720','1080']
                # ATPopRes = AT_PopRes[int(Globals.REAL_SETTINGS.getSetting('autoFindPopcornResoultion'))]    
                  
                # if Globals.REAL_SETTINGS.getSetting('autoFindPopcornPop') == "true":
                    # ATPopCat = 'pop|' + ATPopCat
                
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "14")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "popcorn")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", 'autotune')
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", '')
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", '')
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "Popcorn Movies")  
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                channelNum += 1
                
        # Extras - Cinema Experience 
        self.updateDialogProgress = 81
        if Globals.REAL_SETTINGS.getSetting("autoFindCinema") != "0" and isDon() == True:
            self.log("autoTune, adding Cinema Experience ")
            self.updateDialog.update(self.updateDialogProgress,"Auto Tune","adding Cinema Experience"," ")
            flename = chanlist.createCinemaExperiencePlaylist() #create playlist
            try:
                THEME_NAMES = ['Disabled','Default','IMAX']
                THEME = THEME_NAMES[int(Globals.REAL_SETTINGS.getSetting('autoFindCinema'))]
            except:
                THEME = 'IMAX'
            
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", "14")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", "cinema")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", flename)
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", THEME)
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", '')            
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "5")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "PseudoCinema")  
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "8")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_3_id", "14")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_3_opt_1", "No")  
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_4_id", "17")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_4_opt_1", "No")  
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_5_id", "15")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_5_opt_1", "No")    
            channelNum += 1
                  
        # Extras - IPTV
        self.updateDialogProgress = 82
        if Globals.REAL_SETTINGS.getSetting("autoFindIPTV_Source") != "0":
            self.log("autoTune, adding IPTV Channels")
            self.updateDialog.update(self.updateDialogProgress,"adding IPTV Channels","This could take a few minutes","Please Wait...")

            if Globals.REAL_SETTINGS.getSetting("autoFindIPTV_Source") == "1":
                IPTVurl = Globals.REAL_SETTINGS.getSetting('autoFindIPTV_Path_Local')
            else:
                IPTVurl = Globals.REAL_SETTINGS.getSetting('autoFindIPTV_Path_Online')
            
            NameLst, PathLst = chanlist.ListTuning('IPTV',IPTVurl)
            channelNum = self.tuneList(channelNum, '9', NameLst, '5400', PathLst, NameLst, 'IPTV M3U')

        # Extras - XML Playlist
        self.updateDialogProgress = 83
        if Globals.REAL_SETTINGS.getSetting("autoFindLive_Source") != "0":
            self.log("autoTune, adding XML Channels")
            self.updateDialog.update(self.updateDialogProgress,"adding XML Channels","This could take a few minutes","Please Wait...")

            if Globals.REAL_SETTINGS.getSetting("autoFindLive_Source") == "1":
                LSTVurl = Globals.REAL_SETTINGS.getSetting('autoFindLive_Path_Local')
            else:
                LSTVurl = Globals.REAL_SETTINGS.getSetting('autoFindLive_Path_Online')
            
            NameLst, PathLst = chanlist.ListTuning('LS',LSTVurl)
            channelNum = self.tuneList(channelNum, '9', NameLst, '5400', PathLst, NameLst, 'XML')

        # Extras - PLX Playlist
        self.updateDialogProgress = 83
        if Globals.REAL_SETTINGS.getSetting("autoFindPLX_Source") != "0":
            self.log("autoTune, adding PLX Channels")
            self.updateDialog.update(self.updateDialogProgress,"adding PLX Channels","This could take a few minutes","Please Wait...")
            PLXnum = 0
                        
            if Globals.REAL_SETTINGS.getSetting("autoFindPLX_Source") == "1":
                PLXurl = Globals.REAL_SETTINGS.getSetting('autoFindPLX_Path_Local')
            else:
                PLXurl = Globals.REAL_SETTINGS.getSetting('autoFindPLX_Path_Online')
            
            NameLst, PathLst = chanlist.ListTuning('PLX',PLXurl)
            channelNum = self.tuneList(channelNum, '9', NameLst, '5400', PathLst, NameLst, 'PLX')            
            
        Globals.ADDON_SETTINGS.writeSettings()

        
        self.updateDialogProgress = 100
        # reset auto tune settings        
        Globals.REAL_SETTINGS.setSetting('Autotune', "false")
        Globals.REAL_SETTINGS.setSetting('Warning1', "false") 
        Globals.REAL_SETTINGS.setSetting("autoFindCustom","false")
        Globals.REAL_SETTINGS.setSetting("autoFindSuperFav","false") 
        Globals.REAL_SETTINGS.setSetting('autoFindLivePVR', "false")
        Globals.REAL_SETTINGS.setSetting('autoFindLiveHD', "0")
        Globals.REAL_SETTINGS.setSetting('autoFindUSTVNOW', "false")  
        Globals.REAL_SETTINGS.setSetting("autoFindNetworks","false")
        Globals.REAL_SETTINGS.setSetting("autoFindStudios","false")
        Globals.REAL_SETTINGS.setSetting("autoFindTVGenres","false")
        Globals.REAL_SETTINGS.setSetting("autoFindMovieGenres","false")
        Globals.REAL_SETTINGS.setSetting("autoFindMixGenres","false")
        Globals.REAL_SETTINGS.setSetting("autoFind3DMovies","false")    
        Globals.REAL_SETTINGS.setSetting("autoFindRecent","false")      
        Globals.REAL_SETTINGS.setSetting("autoFindMusicGenres","false")
        Globals.REAL_SETTINGS.setSetting("autoFindMusicVideosMusicTV","false")
        Globals.REAL_SETTINGS.setSetting("autoFindMusicVideosLastFM","false")
        Globals.REAL_SETTINGS.setSetting("autoFindMusicVideosYoutube","false")
        Globals.REAL_SETTINGS.setSetting("autoFindMusicVideosVevoTV","false")
        Globals.REAL_SETTINGS.setSetting("autoFindMusicVideosLocal","")
        Globals.REAL_SETTINGS.setSetting("autoFindYoutube","false")
        Globals.REAL_SETTINGS.setSetting("autoFindCommunity_Plugins","false")
        Globals.REAL_SETTINGS.setSetting("autoFindCommunity_Playon","false")
        Globals.REAL_SETTINGS.setSetting("autoFindCommunity_Youtube_Networks","false")
        Globals.REAL_SETTINGS.setSetting("autoFindCommunity_Youtube_Seasonal","false")
        Globals.REAL_SETTINGS.setSetting("autoFindCommunity_LiveTV","false")
        Globals.REAL_SETTINGS.setSetting("autoFindCommunity_InternetTV","false")
        Globals.REAL_SETTINGS.setSetting("autoFindCommunity_RSS","false")
        Globals.REAL_SETTINGS.setSetting("autoFindCommunity_Youtube_Channels","false")
        Globals.REAL_SETTINGS.setSetting("autoFindCommunity_Youtube_Playlists","false")
        Globals.REAL_SETTINGS.setSetting("autoFindPopcorn","false")
        Globals.REAL_SETTINGS.setSetting("autoFindCinema","0")
        Globals.REAL_SETTINGS.setSetting("autoFindIPTV_Source","0")    
        Globals.REAL_SETTINGS.setSetting("autoFindLive_Source","0")    
        Globals.REAL_SETTINGS.setSetting("autoFindPLX_Source","0")    
        Globals.REAL_SETTINGS.setSetting("ForceChannelReset","true")
        Globals.ADDON_SETTINGS.setSetting('LastExitTime', str(int(curtime)))
        self.updateDialog.close()

        
    def tuneList(self, channelNum, chtype, NameLst, Option1LST, Option2LST, Option3LST, Option4LST):
        self.log('tuneList')
        filecount = 0
        chanlist = ChannelList.ChannelList()
        
        for i in range(len(NameLst)):
            found = True
            try:
                title = chanlist.cleanLabels(NameLst[i])
                try:
                    title = title.split(' - ')[0]
                    title = title.split(': ')[0]
                    genre = title.split(': ')[1]
                    print title, genre
                    if genre.lower() not in self.genre_filter:
                        found = False
                except:
                    pass
                
                if not found:
                    raise
                
                self.updateDialog.update(self.updateDialogProgress,"AutoTuning","",title)
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_type", str(chtype))
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_time", "0")
                if Option4LST == 'M3U' or Option4LST == 'XML' or Option4LST == 'PLX':
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", str(Option1LST))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", str(Option2LST[i]))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(Option3LST[i]))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", str(Option4LST))
                else:
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_1", str(Option1LST[i]).replace(',','|'))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_2", str(Option2LST[i]))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_3", str(Option3LST[i]))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_4", str(Option4LST[i]))
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", title)
                Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_changed", "true")
                channelNum += 1
                filecount += 1
                
                if filecount > Globals.AT_LIMIT:
                    break
                
            except Exception,e:
                self.log('tuneList Failed ' + str(e))
                pass

        return channelNum
        

    def initialAddChannels(self, thelist, chantype, currentchan):
        if len(thelist) > 0:
            counted = 0
            lastitem = 0
            curchancount = 1
            lowerlimit = 1
            lowlimitcnt = 0

            for item in thelist:
                if item[1] > lowerlimit:
                    if item[1] != lastitem:
                        if curchancount + counted <= 10 or counted == 0:
                            counted += curchancount
                            curchancount = 1
                            lastitem = item[1]
                        else:
                            break
                    else:
                        curchancount += 1

                    lowlimitcnt += 1

                    if lowlimitcnt == 3:
                        lowlimitcnt = 0
                        lowerlimit += 1
                else:
                    break

            if counted > 0:
                for item in thelist:
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(currentchan) + "_type", str(chantype))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(currentchan) + "_1", item[0])
                    counted -= 1
                    currentchan += 1

                    if counted == 0:
                        break
        return currentchan