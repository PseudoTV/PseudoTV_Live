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
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import subprocess, os, sys, re, random
import datetime, time

from urllib import unquote, quote
from xml.dom.minidom import parse, parseString
from resources.lib.utils import *
from resources.lib.Globals import *
from resources.lib.ChannelList import ChannelList
from resources.lib.AdvancedConfig import AdvancedConfig

try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
     
class ConfigWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log("__init__")
        if getProperty("PseudoTVRunning") != "True":
            xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
            setProperty("PseudoTVRunning", "True")
            self.madeChanges = 0
            self.showingList = True
            self.channel = 0
            self.channel_type = 9999
            self.setting1 = ''
            self.setting2 = ''
            self.setting3 = ''
            self.setting4 = ''
            self.channame = ''
            self.savedRules = False
            self.DirName = []
            self.LockBrowse = False
            self.chnlst = ChannelList()
            self.chantype = ''
            self.optionList = []
            self.ChanTypeList = []
            self.FavChanLst = (REAL_SETTINGS.getSetting("FavChanLst")).split(',')
            self.newFavChanLst = (getProperty('newFavChanLst')).split(',')
            self.FavChanLst += self.newFavChanLst
            
            if (len(sys.argv) > 1 ):
                self.focusChannel = int(sys.argv[ 1 ].strip())-1
            else:
                self.focusChannel = None
            
            if CHANNEL_SHARING:
                realloc = REAL_SETTINGS.getSetting('SettingsFolder')
                xbmcvfs.copy(realloc + '/settings2.xml', SETTINGS_LOC + '/settings2.xml')

            ADDON_SETTINGS.loadSettings()
            ADDON_SETTINGS.disableWriteOnSave()
            self.doModal()
            self.log("__init__ return")
        else:
            infoDialog("Not available while running.")


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('ChannelConfig: ' + msg, level)


    def onInit(self):
        self.log("onInit")
        for i in range(NUMBER_CHANNEL_TYPES):
            try:
                self.getControl(120 + i).setVisible(False)
            except:
                pass
                
        self.prepareConfig()
        self.myRules = AdvancedConfig("script.pseudotv.live.AdvancedConfig.xml", ADDON_PATH, "Default")
        self.log("onInit return")
            

    def onFocus(self, controlId):
        pass


    def closeConfig(self, channel=0):
        setProperty("PseudoTVRunning", "False")
        if self.madeChanges == 1:
            if yesnoDialog("Changes Detected, Do you want to save all changes?"):
                self.writeChanges()
        if channel > 0:
            xbmc.executebuiltin('XBMC.AlarmClock( Restarting Configuration Manager, XBMC.RunScript(' + ADDON_PATH + '/config.py, %s),0.5,true)'%str(channel))
        self.close()
        
        
    def onAction(self, act):
        action = act.getId()

        if action in ACTION_PREVIOUS_MENU:
            if self.showingList == False:
                if yesnoDialog("Changes Detected, Do you want to save channel changes?"):
                    self.saveSettings()
                else:
                    self.cancelChan()
                self.hideChanDetails()
            else:
                self.closeConfig()
                
        # Delete button
        elif act.getButtonCode() == 61575 or action == ACTION_DELETE_ITEM:
            if self.showingList == True:
                self.deleteChannel(self.listcontrol.getSelectedPosition() + 1)
            else:
                self.clearLabel2([self.getFocusId()])
                
            
    def saveSettings(self):
        self.log("saveSettings channel " + str(self.channel))
        chantype = 9999
        chan = str(self.channel)
        set1 = ''
        set2 = ''
        set3 = ''
        set4 = ''

        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + chan + "_type"))
        except:
            self.log("Unable to get channel type")

        setting1 = "Channel_" + chan + "_1"
        setting2 = "Channel_" + chan + "_2"
        setting3 = "Channel_" + chan + "_3"
        setting4 = "Channel_" + chan + "_4"
        
        if chantype == 0:#Custom XSP
            ADDON_SETTINGS.setSetting(setting1, self.getControl(333).getLabel())
            if self.getControl(334).isSelected():
                self.setTVSort(chan)
                ADDON_SETTINGS.setSetting(setting2, str(MODE_ORDERAIRDATE))
            else:
                self.clearTVSort(chan)
                ADDON_SETTINGS.setSetting(setting2, "0")
                
        elif chantype == 1:#TV Network
            ADDON_SETTINGS.setSetting(setting1, self.getControl(140).getLabel2())
            if self.getControl(141).isSelected():
                ADDON_SETTINGS.setSetting(setting2, str(MODE_ORDERAIRDATE))
            else:
                ADDON_SETTINGS.setSetting(setting2, "0")
                
        elif chantype == 2:#Movie Studio
            ADDON_SETTINGS.setSetting(setting1, self.getControl(150).getLabel2())
            
        elif chantype == 3:#TV Genre
            ADDON_SETTINGS.setSetting(setting1, self.getControl(160).getLabel2())
            if self.getControl(161).isSelected():
                ADDON_SETTINGS.setSetting(setting2, str(MODE_ORDERAIRDATE))
            else:
                ADDON_SETTINGS.setSetting(setting2, "0")
                
        elif chantype == 4:#Movie Genre
            ADDON_SETTINGS.setSetting(setting1, self.getControl(170).getLabel2())
            
        elif chantype == 5:#Mixed Genre
            ADDON_SETTINGS.setSetting(setting1, self.getControl(180).getLabel2())
            if self.getControl(181).isSelected():
                ADDON_SETTINGS.setSetting(setting2, str(MODE_ORDERAIRDATE))
            else:
                ADDON_SETTINGS.setSetting(setting2, "0")
                
        elif chantype == 6:#TV Show
            ADDON_SETTINGS.setSetting(setting1, self.getControl(190).getLabel2())
            if self.getControl(191).isSelected():
                ADDON_SETTINGS.setSetting(setting2, str(MODE_ORDERAIRDATE))
            else:
                ADDON_SETTINGS.setSetting(setting2, "0")
                
        elif chantype == 7:#Directory
            ADDON_SETTINGS.setSetting(setting1, self.getControl(203).getLabel())
            ADDON_SETTINGS.setSetting(setting3, self.getControl(201).getLabel2())
            ADDON_SETTINGS.setSetting(setting4, self.getControl(202).getLabel2())
            
        elif chantype == 8: #LiveTV
            ADDON_SETTINGS.setSetting(setting1, self.getControl(214).getLabel2())
            ADDON_SETTINGS.setSetting(setting2, self.getControl(215).getLabel())
            ADDON_SETTINGS.setSetting(setting3, self.getControl(213).getLabel2())            
        
        elif chantype == 9: #InternetTV
            ADDON_SETTINGS.setSetting(setting1, '5400')
            ADDON_SETTINGS.setSetting(setting2, self.getControl(225).getLabel())
            ADDON_SETTINGS.setSetting(setting3, self.getControl(222).getLabel2())
            ADDON_SETTINGS.setSetting(setting4, self.getControl(223).getLabel2())
            
        elif chantype == 10: #Youtube
            ADDON_SETTINGS.setSetting(setting2, self.getControl(230).getLabel2())
            ADDON_SETTINGS.setSetting(setting1, self.getControl(231).getLabel2())
            ADDON_SETTINGS.setSetting(setting3, self.getControl(232).getLabel2())
            ADDON_SETTINGS.setSetting(setting4, self.getControl(233).getLabel2())
            
        elif chantype == 11: #RSS
            ADDON_SETTINGS.setSetting(setting1, self.getControl(240).getLabel2())
            ADDON_SETTINGS.setSetting(setting3, self.getControl(241).getLabel2())
            ADDON_SETTINGS.setSetting(setting4, self.getControl(242).getLabel2())

        elif chantype == 12: #Music Genre
            ADDON_SETTINGS.setSetting(setting1, self.getControl(250).getLabel2())
            if self.getControl(251).isSelected():
                ADDON_SETTINGS.setSetting(setting2, str(MODE_ORDERAIRDATE))
            else:
                ADDON_SETTINGS.setSetting(setting2, "0")
            
        elif chantype == 13: #Music Videos
            ADDON_SETTINGS.setSetting(setting1, self.getControl(260).getLabel())
            ADDON_SETTINGS.setSetting(setting2, self.getControl(261).getLabel())
            ADDON_SETTINGS.setSetting(setting3, self.getControl(262).getLabel())
            ADDON_SETTINGS.setSetting(setting4, self.getControl(263).getLabel())
            
        elif chantype == 14: #Exclusive
            ADDON_SETTINGS.setSetting(setting1, self.getControl(270).getLabel())
            ADDON_SETTINGS.setSetting(setting2, self.getControl(271).getLabel())
            ADDON_SETTINGS.setSetting(setting3, self.getControl(272).getLabel())
            ADDON_SETTINGS.setSetting(setting4, self.getControl(273).getLabel())
            
        elif chantype == 15: #Plugin
            ADDON_SETTINGS.setSetting(setting1, self.getControl(285).getLabel())
            ADDON_SETTINGS.setSetting(setting2, self.getControl(282).getLabel2())
            ADDON_SETTINGS.setSetting(setting3, self.getControl(283).getLabel2())
            ADDON_SETTINGS.setSetting(setting4, self.getControl(284).getLabel2())
            
        elif chantype == 16: #UPNP
            ADDON_SETTINGS.setSetting(setting1, self.getControl(294).getLabel())
            ADDON_SETTINGS.setSetting(setting2, self.getControl(291).getLabel2())
            ADDON_SETTINGS.setSetting(setting3, self.getControl(292).getLabel2())
            ADDON_SETTINGS.setSetting(setting4, self.getControl(293).getLabel2())
            
        elif chantype == 9999:#NULL
            ADDON_SETTINGS.setSetting(setting1, '')
            ADDON_SETTINGS.setSetting(setting2, '')
            ADDON_SETTINGS.setSetting(setting3, '')
            ADDON_SETTINGS.setSetting(setting4, '')

        if self.savedRules:
            self.saveRules(self.channel)

        # Check to see if the user changed anything
        set1 = ''
        set2 = ''
        set3 = ''
        set4 = ''

        try:
            set1 = ADDON_SETTINGS.getSetting(setting1)
            set2 = ADDON_SETTINGS.getSetting(setting2)
            set3 = ADDON_SETTINGS.getSetting(setting3)
            set4 = ADDON_SETTINGS.getSetting(setting4)
        except:
            pass

        if chantype != self.channel_type or set1 != self.setting1 or set2 or set3 != self.setting3 or set4 != self.setting4 or self.savedRules:
            self.madeChanges = 1
            ADDON_SETTINGS.setSetting('Channel_' + chan + '_changed', 'True')
        REAL_SETTINGS.setSetting("FavChanLst",getProperty('newFavChanLst'))
        self.log("saveSettings return")


    def cancelChan(self):
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_type", str(self.channel_type))
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_1", self.setting1)
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_2", self.setting2)
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_3", self.setting3)
        ADDON_SETTINGS.setSetting("Channel_" + str(self.channel) + "_4", self.setting4)


    def hideChanDetails(self):
        self.getControl(106).setVisible(False)
        
        for i in range(NUMBER_CHANNEL_TYPES):
            try:
                self.getControl(120 + i).setVisible(False)
            except:
                pass

        self.setFocusId(102)
        self.getControl(105).setVisible(True)
        self.showingList = True
        self.updateListing(self.channel)
        self.listcontrol.selectItem(self.channel - 1)


    def isChanFavorite(self, chan):
        Favorite = False
        if str(chan) in self.FavChanLst:
            Favorite = True
        return Favorite
        
        
    def chkChanFavorite(self, chan=None):
        if not chan:
            chan = self.channel
        if str(chan) in self.FavChanLst:
            return 'Remove Favorite'
        else:
            return 'Set Favorite'

        
    def setChanFavorite(self, chan=None):
        self.log("setChanFavorite")
        if not chan:
            chan = self.channel
            
        if self.isChanFavorite(chan):
            ChanColor = ''    
            MSG = "Channel %s removed from favourites" % str(chan)
            self.FavChanLst = removeStringElem(self.FavChanLst, str(chan))
        else:
            ChanColor = 'gold'
            MSG = "Channel %s added to favourites" % str(chan)
            self.FavChanLst.append(str(chan)) 

        self.FavChanLst = removeStringElem(self.FavChanLst)
        self.FavChanLst = sorted_nicely(self.FavChanLst)
        setProperty('newFavChanLst',','.join(self.FavChanLst))
        theitem = self.listcontrol.getListItem(chan - 1)
        theitem.setLabel("[COLOR=%s][B]%d[/COLOR]|[/B]" % (ChanColor, chan))
        self.updateListing(chan) 
        infoDialog(MSG) 
            
            
    def setChlogo(self, channel):
        self.log("setChlogo") 
        chname = self.getChname(channel)
        # if chname:
            # xbmc.executebuiltin("RunScript(script.tvlogo.downloader,/context/%s)" % (urllib.quote(chname)) )
        # else:
        # todo icon selectDialog from tvlogodb
        if chname:
            retval = browse(1, "Select %s's replacement logo" %(chname), "files", ".png")
            if retval and len(retval) > 0:
                if yesnoDialog("Replace Channel %s's Logo?"%(str(channel))):
                    GrabLogo(retval, chname, True)
                    theitem = self.listcontrol.getListItem(channel-1)
                    theitem.setProperty('chlogo',(xbmc.translatePath(retval)))     
                    cachedthumb = xbmc.getCacheThumbName(xbmc.translatePath(os.path.join(LOGO_LOC,(chname + '.png'))))
                    cachefile = xbmc.translatePath(os.path.join(ART_LOC, cachedthumb[0], cachedthumb[:-4] + ".png")).replace("\\", "/")
                    # delete old bug
                    try:
                        xbmcvfs.delete(cachefile)
                    except:
                        pass
            
            
    def openAdvRules(self):
        self.myRules.ruleList = self.ruleList
        self.myRules.doModal()
        if self.myRules.wasSaved == True:
            self.ruleList = self.myRules.ruleList
            self.savedRules = True
            
            
    def onClick(self, controlId):
        self.log("onClick " + str(controlId)) 
        self.savedRules = False
        self.channel = self.listcontrol.getSelectedPosition() + 1     
        
        if controlId == 102:        # Channel list entry selected
            self.getControl(105).setVisible(False)
            self.getControl(106).setVisible(True)
            self.changeChanType(self.channel)
            self.setFocusId(110)
            self.showingList = False
            
        if controlId == 9:
            self.setChlogo(self.listcontrol.getSelectedPosition() + 1)
            
        if controlId == 10:
            self.fillInDetails(self.listcontrol.getSelectedPosition() + 1)
            self.openAdvRules()
            self.saveSettings()
            self.updateListing(self.listcontrol.getSelectedPosition() + 1)
            self.listcontrol.selectItem(self.listcontrol.getSelectedPosition())
            
        if controlId == 11:
            self.setChanFavorite(self.listcontrol.getSelectedPosition() + 1)
        elif controlId == 16:
            self.changeChanNum(self.listcontrol.getSelectedPosition() + 1)
        elif controlId == 13:
            Comingsoon()
            # self.repairChanNum(self.listcontrol.getSelectedPosition() + 1)
        elif controlId == 14:
            self.deleteChannel(self.listcontrol.getSelectedPosition() + 1)
        elif controlId == 15:
            self.closeConfig()
        elif controlId == 110:      # Change channel type
            self.changeChanType(self.channel, True)
            self.resetLabels()
        elif controlId == 112:      # Ok button
            self.saveSettings()
            self.hideChanDetails()
        elif controlId == 113:      # Cancel button
            self.cancelChan()
            self.hideChanDetails()
        elif controlId == 555:      # Help Guide
            help((self.getControl(110).getLabel2()).replace('None','General'))
        elif controlId == 114:      # Rules button
            self.openAdvRules()
            self.saveSettings()
            self.updateListing(self.listcontrol.getSelectedPosition() + 1)
            self.listcontrol.selectItem(self.listcontrol.getSelectedPosition())
        elif controlId == 115:      # Submit button
            if yesnoDialog("Submit Current Channel Configuration?"):
                self.saveSettings()
                self.hideChanDetails()
                ADDON_SETTINGS.writeSettings()  
                self.listSubmit(self.channel)
                
        # Custom Playlist
        elif controlId == 330:      # Playlist-type channel, playlist button
            retval = browse(1, "Channel " + str(self.channel) + " Playlist", "files", ".xsp", False, False, "special://videoplaylists/")
            if ((retval and len(retval) > 0)) and '.xsp' in retval:
                retval = retval.replace("special://videoplaylists/","special://profile/playlists/video/")
                self.getControl(330).setLabel('Playlist:', label2=self.getSmartPlaylistName(retval))
                self.getControl(333).setLabel(retval)
                self.setFocusId(334)
                
        elif controlId == 331:      # Playlist-type Editor button
            smartplaylist = "special://profile/playlists/video/" + os.path.split(self.getControl(333).getLabel())[1]
            if len(self.getControl(333).getLabel()) > 0:
                if getXBMCVersion() > 15:
                    xbmc.executebuiltin( "ActivateWindow(10136,%s,%s)" % ((smartplaylist),'video'))
                else:
                    infoDialog("Kodi Jarvis Required")
            else:
                infoDialog("Select SmartPlaylist First")
                
        elif controlId == 332:      # Community Playlists button
            self.log("Community Playlists")
            try:
                XSPlist = fillGithubItems('https://github.com/PseudoTV/PseudoTV_Playlists',".xsp")
                select = selectDialog(XSPlist, 'Select Community Playlist')
                if select != -1:
                    XSPurl = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Playlists/master/' + ((XSPlist[select]).replace('&','&amp;').replace(' ','%20'))
                    XSPfile = xbmc.translatePath(os.path.join(XSP_LOC,XSPlist[select]))
                    download(XSPurl,XSPfile)
                    self.getControl(330).setLabel('Playlist:', label2=self.getSmartPlaylistName(XSPfile))
                    self.getControl(333).setLabel(XSPfile)
            except:
                pass
                
        elif controlId == 140:      # TV Network channel
            select = selectDialog(self.networkList, 'Select TV Network')
            if select != -1:
                self.getControl(140).setLabel('Network:', label2=self.networkList[select])
                self.setFocusId(141)
                
        elif controlId == 150:      # Movie Studio channel
            select = selectDialog(self.studioList, 'Select Movie Studio')
            if select != -1:
                self.getControl(150).setLabel('Studio:', label2=self.studioList[select])
                
        elif controlId == 160:      # TV Genre channel
            select = selectDialog(self.showGenreList, 'Select TV Genre')
            if select != -1:
                self.getControl(160).setLabel('Genre:', label2=self.showGenreList[select])
                self.setFocusId(161)
                
        elif controlId == 170:      # Movie Genre channel
            select = selectDialog(self.movieGenreList, 'Select Movie Genre')
            if select != -1:
                self.getControl(170).setLabel('Genre:', label2=self.movieGenreList[select])
        
        elif controlId == 180:      # Mixed Genre channel
            select = selectDialog(self.mixedGenreList, 'Select Mixed Genre')
            if select != -1:
                self.getControl(180).setLabel('Genre:', label2=self.mixedGenreList[select])
                self.setFocusId(181)
                
        elif controlId == 190:      # TV Show channel
            try:
                select = mselectDialog(self.showList, 'Select one or multiple TV Shows')
                if select != -1:
                    self.setChname((matchMselect(self.showList,select))[0])
                    self.getControl(190).setLabel('Shows:',label2='|'.join(matchMselect(self.showList,select)))
            except:
                select = selectDialog(self.showList, 'Select one TV Show')
                if select != -1:
                    self.setChname(self.showList[select])
                    self.getControl(190).setLabel('Show:',label2=self.showList[select])
            self.setFocusId(191)
                                
        #Directory
        elif controlId == 200:    # Directory channel, select
            retval = browse(0, "Channel " + str(self.channel) + " Directory", "files")
            if retval and len(retval) > 0:
                chname = self.chnlst.getChannelName(7, self.channel, retval)
                self.getControl(200).setLabel('Directory:',label2=chname)
                self.getControl(203).setLabel(retval)       
                self.setFocusId(201)
        elif controlId == 201:    # setLabel MediaLimit, select 
            self.setLimit(201)
            self.setFocusId(202)
        elif controlId == 202:    # setLabel SortOrder, select 
            self.setSort(202)
            
        #LiveTV
        elif controlId == 210:    # LiveTV Browse Sources
            self.LockBrowse = False
            self.clearLabel([215])  # Reset Paths
            select = selectDialog(self.SourceList, 'Select LiveTV Source')
            if select != -1:
                self.getControl(210).setLabel('Source:',label2=self.SourceList[select])
                self.setFocusId(211)
                xbmc.executebuiltin('SendClick(211)')
                
        elif controlId == 211:    # LiveTV Browse Folders
            if len(self.getControl(215).getLabel()) > 1:
                title, path = self.fillSources('LiveTV', self.getControl(210).getLabel2(), self.getControl(215).getLabel())
            else:
                title, path = self.fillSources('LiveTV', self.getControl(210).getLabel2())

            if path and len(path) > 0:             
                self.getControl(215).setLabel(path)
                              
                if self.getControl(210).getLabel2() in ['Plugin','UPNP']:
                    title, path = self.fillSources('LiveTV', self.getControl(210).getLabel2(), self.getControl(215).getLabel())
                    
                    if path and len(path) > 0:      
                        self.getControl(215).setLabel(path)
                    
                        if path.startswith('plugin://plugin.video.ustvnow'):
                            title = title.split(' - ')[0]
                            self.getControl(213).setLabel('Guidedata Type:', label2='ustvnow')
                            self.getControl(214).setLabel('Guidedata ID:', label2=title)
                else:
                    if self.getControl(210).getLabel2() in ['PVR','HDhomerun']:
                        chid, title = title.split(' - ')

                        if self.getControl(210).getLabel2() == 'PVR':
                            self.getControl(213).setLabel('Guidedata Type:', label2='pvr')
                            self.getControl(214).setLabel('Guidedata ID:', label2=chid)
                        
                self.setChname(title)  
                self.getControl(211).setLabel('Channel Name:', label2=title)
                self.getControl(212).setLabel('Guidedata Channel Name:', label2=title) 
                self.setFocusId(212) 
                
        elif controlId == 212:    # LiveTV Display Name, input
            retval = inputDialog('Enter Display Name',self.getControl(212).getLabel2())
            if retval and len(retval) > 0:
                self.setChname(retval)
                self.getControl(212).setLabel('Guidedata Channel Name:', label2=retval)
                self.setFocusId(213)
                xbmc.executebuiltin('SendClick(213)')
                
        elif controlId == 213:    # LiveTV XMLTV Name, Select
            self.getControl(213).setLabel('Guidedata Type:', label2=listXMLTV())
            self.setFocusId(214)
            xbmc.executebuiltin('SendClick(214)')
        
        elif controlId == 214:    # LiveTV Channel ID, select
            setting3 = self.getControl(213).getLabel2()
            if len(setting3) <= 1:
                infoDialog("Enter Channel Name & Guidedata Type")
            else:                              
                dname = self.chnlst.cleanLabels(self.getControl(212).getLabel2())
                dnameID, CHid = self.chnlst.findZap2itID(dname, xbmc.translatePath( xmltvflePath(setting3)))
                if 'XMLTV ERROR' not in dnameID:
                    self.getControl(214).setLabel('Guidedata ID:', label2=CHid)
                    self.getControl(212).setLabel('Guidedata Channel Name:', label2=self.chnlst.cleanLabels(dnameID))
                    
        # InternetTV
        elif controlId == 220:    # InternetTV Browse, select
            self.LockBrowse = False
            self.clearLabel([225])  # Reset Paths
            select = selectDialog(self.SourceList, 'Select InternetTV Source')
            if select != -1:
                self.getControl(220).setLabel('Source:',label2=self.SourceList[select])
                self.setFocusId(221)
                xbmc.executebuiltin('SendClick(221)')
      
        elif controlId == 221:    # InternetTV Browse Folders
            if len(self.getControl(225).getLabel()) > 1:
                title, path = self.fillSources('InternetTV', self.getControl(220).getLabel2(), self.getControl(225).getLabel())
            else:
                title, path = self.fillSources('InternetTV', self.getControl(220).getLabel2())

            if path and len(path) > 0:             
                self.getControl(225).setLabel(path)
                              
                if self.getControl(220).getLabel2() in ['Plugin','UPNP']:
                    title, path = self.fillSources('InternetTV', self.getControl(220).getLabel2(), self.getControl(225).getLabel())
                    
                    if path and len(path) > 0:      
                        self.getControl(225).setLabel(path)
                else:
                    if path.startswith('plugin://plugin.video.ustvnow'):
                        title = title.split(' - ')[0]
                        
                    if self.getControl(220).getLabel2() in ['PVR','HDhomerun']:
                        chid, title = title.split(' - ')
                        
                self.setChname(title)  
                self.getControl(221).setLabel('Channel Name:', label2=title)
                self.getControl(222).setLabel('Show Title:', label2=title)
                self.getControl(223).setLabel('Show Description:', label2=title)
                self.setFocusId(222)
                xbmc.executebuiltin('SendClick(222)')

        elif controlId == 222:    # InternetTV Show, input        
            retval = inputDialog('Enter Show Title',self.getControl(222).getLabel2())
            if retval and len(retval) > 0:
                self.setChname(retval)  
                self.getControl(222).setLabel('Show Title:', label2=retval)
                self.setFocusId(223)
                xbmc.executebuiltin('SendClick(223)')
        
        elif controlId == 223:    # InternetTV Description, input
            retval = inputDialog('Enter Show Description',self.getControl(223).getLabel2())
            if retval and len(retval) > 0:
                self.getControl(223).setLabel('Show Description:', label2=retval)
        #Youtube
        elif controlId == 230:  
            select = selectDialog(self.YoutubeList, 'Select Youtube Type')
            if select != -1:
                self.getControl(230).setLabel('Youtube Type:', label2=self.YoutubeList[select])
            
                if (self.getControl(230).getLabel2()).startswith('Seasonal'): 
                    today = datetime.datetime.now()
                    month = today.strftime('%B')
                    self.getControl(231).setLabel('Youtube ID:', label2=month)
                    self.getControl(232).setLabel('Media Limit:', label2="Global")
                    self.getControl(233).setLabel('Sort Order:', label2="Default")
                    self.setChname('Seasonal') 
                else:
                    self.setFocusId(231)
                    xbmc.executebuiltin('SendClick(231)')
                    self.setYoutubeEX(True)
                
        elif controlId == 231:    # Youtube ID, input            
            retval = inputDialog('Enter Youtube ID',self.getControl(231).getLabel2())
            if retval and len(retval) > 0:
                self.getControl(231).setLabel('Youtube ID:', label2=retval)     
                self.setChname(retval)            
                self.setFocusId(232)
                xbmc.executebuiltin('SendClick(232)')
                
        elif controlId == 232:    # Youtube MediaLimit, select 
            self.setLimit(232)              
            self.setFocusId(233)
            xbmc.executebuiltin('SendClick(233)')
            
        elif controlId == 233:    # Youtube SortOrder, select 
            self.setSort(233)  
        
        #RSS
        elif controlId == 240:    # RSS Feed URL, input
            retval = inputDialog('Enter feed url',self.getControl(240).getLabel2())
            if retval and len(retval) > 0:
                self.getControl(240).setLabel('RSS Feed:', label2=retval)   
                self.setFocusId(241)
                xbmc.executebuiltin('SendClick(241)')
 
        elif controlId == 241:    # RSS MediaLimit, select 
            self.setLimit(241)
            self.setFocusId(242)
            xbmc.executebuiltin('SendClick(242)')
            
        elif controlId == 242:    # RSS SortOrder, select 
            self.setSort(242)  

        #Music
        elif controlId == 250:      # Browse plugin list
            select = selectDialog(self.musicGenreList, 'Select Music Genre')
            if select != -1:
                self.getControl(250).setLabel('Genre:', label2=self.musicGenreList[select])
                self.setFocusId(251)
            
        #Plugin
        elif controlId == 280:      # Browse plugin list
            select = selectDialog(self.pluginNameList, 'Select Plugin')
            if select != -1:
                self.getControl(280).setLabel('Plugin:', label2=self.chnlst.cleanLabels((self.pluginNameList[select])))
                self.getControl(285).setLabel('plugin://' + self.pluginPathList[select])
                self.setChname(self.chnlst.cleanLabels(self.getControl(280).getLabel2()))     
                self.setFocusId(281)
                xbmc.executebuiltin('SendClick(281)')
                
        elif controlId == 281:      # Browse Plugin Directories
            # Recursive Browse
            if len(self.getControl(285).getLabel()) > 1:
                PluginDirNameLst, PluginDirPathLst = self.parsePlugin(self.chnlst.PluginInfo(self.getControl(285).getLabel()), 'Dir')
            # Firsttime Browse
            else:
                if len(self.getControl(280).getLabel2()) > 1:
                    PluginDirNameLst, PluginDirPathLst = self.parsePlugin(self.chnlst.PluginInfo(self.getControl(285).getLabel()), 'Dir')
                else:
                    infoDialog("Select Plugin First")
                
            loop = True
            while loop:
                select = selectDialog(PluginDirNameLst, 'Select [COLOR=red][D][/COLOR]irectory')
                if select != -1:
                    selectItem = PluginDirNameLst[select]
                    if not selectItem.startswith('[COLOR=green][F]'):
                        infoDialog("Select Directory")
                        loop = False
                        
                if PluginDirPathLst[select].startswith('plugin://plugin.video.ustvnow'):
                    selectItem = selectItem.split(' - ')[0]
                    
                # Return to menu
                if PluginDirPathLst[select] == 'Return':
                    return
                
                # Normal Navigation
                self.getControl(281).setLabel('Folder:', label2=self.chnlst.cleanLabels(selectItem))
                self.getControl(285).setLabel(PluginDirPathLst[select])        
                self.setChname(self.chnlst.cleanLabels(selectItem))
                self.setFocusId(282)
                xbmc.executebuiltin('SendClick(282)')
                
        elif controlId == 282:       # Plugin Exclude, input
            self.setExclude(282)
            self.setFocusId(283)
            xbmc.executebuiltin('SendClick(283)')
            
        elif controlId == 283:       # Plugin MediaLimit, select 
            self.setLimit(283)
            self.setFocusId(284)
            xbmc.executebuiltin('SendClick(284)')
            
        elif controlId == 284:      # Plugin SortOrder, select 
            self.setSort(284) 

        # UPNP
        elif controlId == 290:      # UPNP Path, select 
            # Recursive Browse
            if len(self.getControl(294).getLabel()) > 1:
                PluginDirNameLst, PluginDirPathLst = self.parsePlugin(self.chnlst.PluginInfo(self.getControl(294).getLabel()), 'Dir')
            # Firsttime Browse
            else:
                if len(self.getControl(290).getLabel2()) > 1:
                    PluginDirNameLst, PluginDirPathLst = self.parsePlugin(self.chnlst.PluginInfo('upnp://'), 'Dir')
                
            loop = True
            while loop:
                select = selectDialog(PluginDirNameLst, 'Select [COLOR=red][D][/COLOR]irectory')
                if select != -1:
                    selectItem = PluginDirNameLst[select]
                    if not selectItem.startswith('[COLOR=green][F]'):
                        infoDialog("Select Directory")
                        loop = False
                        
                # Return to menu
                if PluginDirPathLst[select] == 'Return':
                    return
        
                # Normal Navigation
                self.getControl(290).setLabel('UPNP Path:', label2=self.chnlst.cleanLabels(selectItem))
                self.getControl(294).setLabel(PluginDirPathLst[select])   
                self.setChname(self.chnlst.cleanLabels(selectItem))
                
        elif controlId == 291:       # UPNP Exclude, input
            self.setExclude(291)
            self.setFocusId(292)
            xbmc.executebuiltin('SendClick(292)')
            
        elif controlId == 292:       # UPNP MediaLimit, select 
            self.setLimit(292)
            self.setFocusId(293)
            xbmc.executebuiltin('SendClick(293)')
            
        elif controlId == 293:      # UPNP SortOrder, select 
            self.setSort(293) 
        
        self.log("onClick return")


    def changeListData(self, thelist, controlid, val):
        self.log("changeListData " + str(controlid) + ", " + str(val))
        curval = self.getControl(controlid).getLabel()
        found = False
        index = 0

        if len(thelist) == 0:
            self.getControl(controlid).setLabel('')
            self.log("changeListData return Empty list")
            return

        for item in thelist:
            if item == curval:
                found = True
                break
            index += 1
        if found == True:
            index += val
        while index < 0:
            index += len(thelist)
        while index >= len(thelist):
            index -= len(thelist)
        
        self.getControl(controlid).setLabel(thelist[index])
        
        # Disable Submit button for repo approval
        # if isCom() and thelist[index] not in ['PVR','HDhomerun','UPNP','Local Music','Local Video','User Subscription','User Favorites','Search Query','Raw gdata','Seasonal','Plugin','LiveTV','InternetTV']:
            # self.getControl(115).setVisible(True)
        # else:
        self.getControl(115).setVisible(False)
        self.log("changeListData return")


    def getSmartPlaylistName(self, fle):
        self.log("getSmartPlaylistName " + fle)
        fle = xbmc.translatePath(fle)

        try:
            xml = open(fle, "r")
        except:
            self.log('Unable to open smart playlist')
            return ''

        try:
            dom = parse(xml)
        except:
            xml.close()
            self.log("getSmartPlaylistName return unable to parse")
            return ''

        xml.close()

        try:
            plname = dom.getElementsByTagName('name')
            self.log("getSmartPlaylistName return " + plname[0].childNodes[0].nodeValue)
            return plname[0].childNodes[0].nodeValue
        except:
            self.playlist('Unable to find element name')

        self.log("getSmartPlaylistName return")


    def changeChanType(self, channel, change=False):
        self.log("changeChanType " + str(channel))
        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_type"))
        except:
            chantype = 9999
            self.log("Unable to get channel type")

        if change == True:
            select = selectDialog(self.ChanTypeList, 'Select Channel Type')
            if select != -1:
                chantype = select
                ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", str(chantype))      
        else:
            self.setting1 = ''
            self.setting2 = ''
            self.setting3 = ''
            self.setting4 = ''
            self.channel_type = chantype
            self.channame = self.getChname(channel)
            try:
                self.setting1 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_1")
                self.setting2 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_2")
                self.setting3 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_3")
                self.setting4 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_4")
            except:
                pass
                
        for i in range(NUMBER_CHANNEL_TYPES):
            if i == chantype:
                self.getControl(120 + i).setVisible(True)
                if chantype != 0:
                    self.getControl(110).controlDown(self.getControl(120 + ((i + 1) * 10)))
                else:
                    self.getControl(110).controlDown(self.getControl(330))
            else:
                try:
                    self.getControl(120 + i).setVisible(False)
                except:
                    pass
                    
        self.fillInDetails(channel)        
        self.log("changeChanType return")


    def fillInDetails(self, channel):
        self.log("fillInDetails " + str(channel))
        self.getControl(104).setLabel("Channel " + str(channel))
        
        chantype = 9999
        chansetting1 = ''
        chansetting2 = ''
        chansetting3 = ''
        chansetting4 = ''
        channame = ''
        
        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_type"))
            chansetting1 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_1")
            chansetting2 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_2")
            chansetting3 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_3")
            chansetting4 = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_4")
            channame = self.getChname(channel)
        except:
            self.log("Unable to get some setting")
        
        
        # Correct Youtube/Media Limit/Sort Values from old configurations
        if chantype in [7,10,11,13,15,16]:
            if chantype == 10:
                chansetting2 = chansetting2.replace('7','Multi Playlist').replace('8','Multi Channel').replace('3','User Subscription')
                chansetting2 = chansetting2.replace('4','User Favorites').replace('5','Search Query').replace('9','Raw gdata')
                chansetting2 = chansetting2.replace('31','Seasonal').replace('1','Channel').replace('2','Playlist')   
            chansetting3 = chansetting3.replace('0','Unlimited')
            if len(chansetting3) == 0:
                chansetting3 = chansetting3.replace('','Global')
            chansetting4 = chansetting4.replace('0','Default').replace('1','Random').replace('2','Reverse')
   
        self.getControl(110).setLabel('Channel Type:', label2=self.getChanTypeLabel(chantype))
        
        # Custom Playlist
        if chantype == 0:
            self.setFocusId(330)
            plname = self.getSmartPlaylistName(chansetting1)
            if len(chansetting1) != 0 and len(plname) != 0:
                self.getControl(330).setLabel('Playlist:', label2=plname)  
                self.getControl(333).setLabel(chansetting1)
                self.getControl(334).setSelected(chansetting2 == str(MODE_ORDERAIRDATE))
            else:
                self.getControl(330).setLabel('Playlist:', label2='Click to Browse')   
                xbmc.executebuiltin('SendClick(330)')
        
        elif chantype == 1:
            self.setFocusId(140)
            netname = self.findItemInList(self.networkList, chansetting1)
            if len(chansetting1) != 0 and len(netname) != 0:
                self.getControl(140).setLabel('Network:', label2=netname)
                self.getControl(141).setSelected(chansetting2 == str(MODE_ORDERAIRDATE))
            else:
                self.getControl(140).setLabel('Network:', label2='Click to Browse') 
                xbmc.executebuiltin('SendClick(140)')
                
        elif chantype == 2:
            self.setFocusId(150)
            stuname = self.findItemInList(self.studioList, chansetting1)
            if len(chansetting1) != 0 and len(stuname) != 0:
                self.getControl(150).setLabel('Studio:', label2=stuname)
            else:
                self.getControl(150).setLabel('Studio:', label2='Click to Browse') 
                xbmc.executebuiltin('SendClick(150)')
                
        elif chantype == 3:
            self.setFocusId(160)
            sgenname = self.findItemInList(self.showGenreList, chansetting1)
            if len(chansetting1) != 0 and len(sgenname) != 0:
                self.getControl(160).setLabel('Genre:', label2=sgenname)
                self.getControl(161).setSelected(chansetting2 == str(MODE_ORDERAIRDATE))
            else:
                self.getControl(160).setLabel('Genre:', label2='Click to Browse') 
                xbmc.executebuiltin('SendClick(160)')
                
        elif chantype == 4:
            self.setFocusId(170)
            mgenname = self.findItemInList(self.movieGenreList, chansetting1)
            if len(chansetting1) != 0 and len(mgenname) != 0:
                self.getControl(170).setLabel('Genre:', label2=mgenname)
            else:
                self.getControl(170).setLabel('Genre:', label2='Click to Browse') 
                xbmc.executebuiltin('SendClick(170)')
                
        elif chantype == 5:
            self.setFocusId(180)
            mxgenname = self.findItemInList(self.mixedGenreList, chansetting1)
            if len(chansetting1) != 0 and len(mxgenname) != 0:
                self.getControl(180).setLabel('Genre:', label2=mxgenname)
                self.getControl(181).setSelected(chansetting2 == str(MODE_ORDERAIRDATE))
            else:
                self.getControl(180).setLabel('Genre:', label2='Click to Browse')
                xbmc.executebuiltin('SendClick(180)')
                
        elif chantype == 6:
            self.setFocusId(190)
            # tvshow = chansetting1.split('|')
            # for n in range(len(tvshows)):
                # # reverse tvshow select to get len vaules to fill preselect
                # # https://github.com/phil65/xbmc/commit/c1a63ad618e3abc701810dd38b85653ad516bfc1
                # select = self.findItemLens(self.showList, tvshows[n])
            if len(chansetting1) != 0 and len(chansetting1) != 0:
                self.getControl(190).setLabel('Show:', label2=chansetting1)
                self.getControl(191).setSelected(chansetting2 == str(MODE_ORDERAIRDATE))
            else:
                self.getControl(190).setLabel('Show:', label2='Click to Browse')  
                xbmc.executebuiltin('SendClick(190)')      
                
        elif chantype == 7:
            self.setFocusId(200)
            if len(chansetting1) > 0:
                chname = self.chnlst.getChannelName(7, channel, chansetting1)
                self.getControl(200).setLabel('Directory:',label2=chname)
                self.getControl(201).setLabel('Media Limit:',label2=chansetting3)
                self.getControl(202).setLabel('Sort Order:',label2=self.findItemInList(self.SortOrderList, chansetting4))
                self.getControl(203).setLabel(chansetting1)   
            else:    
                self.getControl(200).setLabel('Directory:', label2='Click to Browse')
                xbmc.executebuiltin('SendClick(200)')
                
        elif chantype == 8:
            self.setFocusId(210)
            if len(chansetting2) != 0:
                self.getControl(215).setLabel(chansetting2)
                self.getControl(214).setLabel('Guidedata ID:', label2=chansetting1)
                self.getControl(213).setLabel('Guidedata Type:', label2=chansetting3)
                self.getControl(212).setLabel('Guidedata Channel Name:', label2=channame)
            else:
                self.getControl(210).setLabel('Source:', label2='Click to Browse')
                xbmc.executebuiltin('SendClick(210)')

        elif chantype == 9:
            self.setFocusId(220)
            if len(chansetting2) != 0:
                self.getControl(221).setLabel('Channel Name:', label2=channame)
                self.getControl(225).setLabel(chansetting2)
                self.getControl(222).setLabel('Show Title:', label2=chansetting3)
                self.getControl(223).setLabel('Show Description:', label2=chansetting4)
            else:
                self.getControl(210).setLabel('Source:', label2='Click to Browse')
                xbmc.executebuiltin('SendClick(220)')
            
        elif chantype == 10: 
            self.setFocusId(230)
            if len(chansetting2) != 0:
                self.getControl(230).setLabel('Youtube Type:', label2=(self.findItemInList(self.YoutubeList, chansetting2)))
                self.getControl(231).setLabel('Youtube ID:', label2=chansetting1)
                self.getControl(232).setLabel('Media Limit:', label2=chansetting3)
                self.getControl(233).setLabel('Sort Order:', label2=(self.findItemInList(self.SortOrderList, chansetting4)))
                self.setYoutubeEX()
            else:
                self.getControl(230).setLabel('Youtube Type:', label2='Click to Browse')
                xbmc.executebuiltin('SendClick(230)')

        elif chantype == 11:
            self.setFocusId(240)
            if len(chansetting2) != 0:
                self.getControl(240).setLabel('RSS Feed:', label2=chansetting1)
                self.getControl(241).setLabel('Media Limit:', label2=chansetting3)
                self.getControl(242).setLabel('Sort Order:', label2=(self.findItemInList(self.SortOrderList, chansetting4)))
            else:
                self.getControl(240).setLabel('RSS Feed:', label2='Click to Enter')
                xbmc.executebuiltin('SendClick(240)')
            
        elif chantype == 12:
            self.setFocusId(250)
            mugenname = self.findItemInList(self.musicGenreList, chansetting1)
            if len(chansetting1) != 0 and len(mugenname) != 0:
                self.getControl(250).setLabel('Genre:', label2=mugenname)
                self.getControl(250).setSelected(chansetting2 == str(MODE_ORDERAIRDATE))
            else:
                self.getControl(250).setLabel('Genre:', label2='Click to Browse')
                xbmc.executebuiltin('SendClick(250)')
                
        elif chantype == 13:
            self.getControl(260).setLabel(chansetting1)
            self.getControl(261).setLabel(chansetting2)
            self.getControl(262).setLabel(chansetting3)
            self.getControl(263).setLabel(chansetting4)
            
        elif chantype == 14:
            self.getControl(270).setLabel(chansetting1)
            self.getControl(271).setLabel(chansetting2)
            self.getControl(272).setLabel(chansetting3)
            self.getControl(273).setLabel(chansetting4)
            
        elif chantype == 15:
            self.setFocusId(280)
            if len(chansetting1) != 0:
                # Find and fill Plugin name and path
                try: 
                    PlugName = self.pluginNameList[self.findItemLens(self.pluginPathList, chansetting1.split('/')[2])]
                except:
                    PlugName = 'Click to Browse'
                self.getControl(280).setLabel('Plugin:', label2=PlugName)
                self.getControl(281).setLabel('Folder:', label2=channame)
                self.getControl(282).setLabel('Exclude:', label2=chansetting2)
                self.getControl(283).setLabel('Media Limit:', label2=chansetting3)
                self.getControl(284).setLabel('Sort Order:', label2=(self.findItemInList(self.SortOrderList, chansetting4)))
                self.getControl(285).setLabel(chansetting1)
            else:
                self.getControl(280).setLabel('Plugin:', label2='Click to Select')
                self.getControl(281).setLabel('Folder:', label2='Click to Browse')
                xbmc.executebuiltin('SendClick(280)')
                        
        elif chantype == 16:
            self.setFocusId(290)
            if len(chansetting1) != 0:
                self.getControl(290).setLabel('UPNP Path:', label2=self.chnlst.getChannelName(16, channel, chansetting1))
                self.getControl(291).setLabel('Exclude:', label2=chansetting2)
                self.getControl(292).setLabel('Media Limit:', label2=chansetting3)
                self.getControl(293).setLabel('Sort Order:', label2=(self.findItemInList(self.SortOrderList, chansetting4)))
                self.getControl(294).setLabel(chansetting1)
            else:
                self.getControl(290).setLabel('UPNP Path:', label2='Click to Browse')
                xbmc.executebuiltin('SendClick(290)')
                
        elif chantype == 17:#NONE
            self.log("fillInDetails return")
        else:
            xbmc.executebuiltin('SendClick(110)')
            
        self.loadRules(channel)
        self.log("fillInDetails return")
        
        
    def getRuleName(self, ruleindex):
        self.log("getRuleName")
        if ruleindex < 0 or ruleindex >= len(self.AdvRules.ruleList):
            return ""
        return self.AdvRules.ruleList[ruleindex].getName()

        
    def fillRules(self, channel):
        self.log("fillRules")
        from resources.lib.Rules import RulesList
        self.AdvRules = RulesList()
        ruleList = []
        ruleValue = [] 
        try:
            rulecount = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount'))
            for i in range(rulecount):
                ruleid = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_id'))
                ruleList.append(self.getRuleName(ruleid))     
        except:
            pass
        return ruleList
        
        
    def loadRules(self, channel):
        self.log("loadRules")
        self.ruleList = []
        self.myRules.allRules

        try:
            rulecount = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount'))
            for i in range(rulecount):
                ruleid = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_id'))

                for rule in self.myRules.allRules.ruleList:
                    if rule.getId() == ruleid:
                        self.ruleList.append(rule.copy())

                        for x in range(rule.getOptionCount()):
                            self.ruleList[-1].optionValues[x] = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_opt_' + str(x + 1))
                        foundrule = True
                        break
        except:
            self.ruleList = []
        

    def saveRules(self, channel):
        self.log("saveRules")
        rulecount = len(self.ruleList)
        ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_rulecount', str(rulecount))
        index = 1

        for rule in self.ruleList:
            ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_rule_' + str(index) + '_id', str(rule.getId()))

            for x in range(rule.getOptionCount()):
                ADDON_SETTINGS.setSetting('Channel_' + str(channel) + '_rule_' + str(index) + '_opt_' + str(x + 1), rule.getOptionValue(x))
            index += 1


    def findItemInList(self, thelist, item):
        loitem = item.lower()

        for i in thelist:
            if loitem == i.lower():
                return item

        if len(thelist) > 0:
            return thelist[0]
        return ''    
        
        
    def findItemLens(self, thelist, item):
        loitem = item.lower()

        for i in range(len(thelist)):
            line = (thelist[i]).lower()
            if line == loitem:
                return i
        return ''

        
    def fillChanTypeLabel(self):
        show_busy_dialog()
        for i in range(NUMBER_CHANNEL_TYPES + 1):
            self.ChanTypeList.append(self.getChanTypeLabel(i))
        hide_busy_dialog()
            
            
    def getChanTypeLabel(self, chantype):
        if chantype == 0:
            return "Custom Playlist"
        elif chantype == 1:
            return "TV Network"
        elif chantype == 2:
            return "Movie Studio"
        elif chantype == 3:
            return "TV Genre"
        elif chantype == 4:
            return "Movie Genre"
        elif chantype == 5:
            return "Mixed Genre"
        elif chantype == 6:
            return "TV Show"
        elif chantype == 7:
            return "Directory"
        elif chantype == 8:
            return "LiveTV"
        elif chantype == 9:
            return "InternetTV"
        elif chantype == 10:
            return "Youtube"
        elif chantype == 11:
            return "RSS"
        elif chantype == 12:
            return "Music"
        elif chantype == 13:
            return "Music Videos (Coming Soon)"
        elif chantype == 14:
            return "Exclusive (Coming Soon)"
        elif chantype == 15:
            return "Plugin"
        elif chantype == 16:
            return "UPNP"
        return 'None'

        
    def prepareConfig(self):
        self.log("prepareConfig")
        self.showList = []
        self.pluginPathList = []
        self.pluginNameList = []
        self.pluginIconList = []
        self.getControl(105).setVisible(False)
        self.getControl(106).setVisible(False)
        self.dlg = xbmcgui.DialogProgress()
        self.dlg.create("PseudoTV Live", "Preparing Configuration")
        
        show_busy_dialog()  
        self.dlg.update(5, "Preparing Configuration", "querying Music database")      
        self.chnlst.fillMusicInfo()     
        
        self.dlg.update(10, "Preparing Configuration", "querying TV database")
        self.chnlst.fillTVInfo()   
        
        self.dlg.update(15, "Preparing Configuration", "querying Movie database")
        self.chnlst.fillMovieInfo()
        
        self.dlg.update(20, "Preparing Configuration", "querying Plugin database")
        self.chnlst.fillPluginList()
        
        self.dlg.update(25, "Preparing Configuration", "querying PVR database")
        self.chnlst.fillPVR()
        
        self.dlg.update(30, "Preparing Configuration", "querying Favourites database")
        self.chnlst.fillFavourites()
        
        self.dlg.update(35, "Preparing Configuration", "querying HDhomerun devices")
        self.chnlst.fillHDHR()
        
        self.dlg.update(40, "Preparing Configuration", "querying Channel information")
        self.fillChanTypeLabel()
        
        self.dlg.update(45, "Preparing Configuration", "gathering data")
        hide_busy_dialog()
        self.mixedGenreList = sorted_nicely(removeStringElem(self.chnlst.makeMixedList(self.chnlst.showGenreList, self.chnlst.movieGenreList)))
        self.networkList = sorted_nicely(removeStringElem(self.chnlst.networkList))
        self.studioList = sorted_nicely(removeStringElem(self.chnlst.studioList))
        self.showGenreList = sorted_nicely(removeStringElem(self.chnlst.showGenreList))
        self.movieGenreList = sorted_nicely(removeStringElem(self.chnlst.movieGenreList))
        self.musicGenreList = sorted_nicely(removeStringElem(self.chnlst.musicGenreList))
        
        self.dlg.update(50, "Preparing Configuration", "sorting data")
        self.GenreLst = ['TV','Movies','Episodes','Sports','Kids','News','Music','Seasonal','Other']
        self.MediaLimitList = ['25','50','100','150','200','250','500','1000','5000','Unlimited','Global']
        self.SortOrderList = ['Default','Random','Reverse']
        self.ExternalPlaylistSources = ['Local File','URL']
        self.SourceList = ['PVR','HDhomerun','Community List (Coming Soon)','Local Video','Local Music','Plugin','UPNP','Kodi Favourites','Youtube Live','URL','M3U Playlist','XML Playlist','PLX Playlist']
        self.YoutubeList = ['Channel','Playlist','Multi Playlist','Multi Channel','Seasonal','Search Query']
        self.YTFilter = ['User Subscription','User Favorites','Search Query']
        
        self.dlg.update(55, "Preparing Configuration", "finalizing data")
        if isSFAV() == True:
            self.pluginPathList = ['plugin.program.super.favourites']
            self.pluginNameList = ['[COLOR=blue][B]Super Favourites[/B][/COLOR]']
            self.pluginIconList = ['']
        if isPlayOn() == True:
            self.pluginPathList = ['plugin.video.playonbrowser'] + self.pluginPathList
            self.pluginNameList = ['[COLOR=blue][B]Playon[/B][/COLOR]'] + self.pluginNameList
            self.pluginIconList = [''] + self.pluginIconList  
        if isUSTVnow() == True:
            self.pluginPathList = ['plugin.video.ustvnow/?mode=live'] + self.pluginPathList
            self.pluginNameList = ['[COLOR=blue][B]USTVnow[/B][/COLOR]'] + self.pluginNameList
            self.pluginIconList = [''] + self.pluginIconList
        if isPlugin('plugin.video.meta') == True:
            self.SourceList.append('Meta Plugin')
            
        self.dlg.update(60)
        self.SourceList = sorted_nicely(self.SourceList)
        self.pluginNameList = self.chnlst.pluginList[0]
        self.pluginPathList = self.chnlst.pluginList[1]
        self.pluginIconList = self.chnlst.pluginList[2]
        
        self.dlg.update(65)
        for i in range(len(self.chnlst.showList)):
            self.showList.append(self.chnlst.showList[i][0])
        self.showList =  sorted_nicely(removeStringElem(self.showList))
        
        self.dlg.update(70)
        self.mixedGenreList.sort(key=lambda x: x.lower())
        self.listcontrol = self.getControl(102)
        
        self.dlg.update(75)
        for i in range(CHANNEL_LIMIT):
            theitem = xbmcgui.ListItem()  
            ChanColor = ''      
            if self.isChanFavorite(i + 1):
                ChanColor = 'gold'
            theitem.setLabel("[COLOR=%s][B]%d[/COLOR]|[/B]" % (ChanColor, i + 1))
            self.listcontrol.addItem(theitem)

        self.dlg.update(85)
        self.dlg.update(90)
        self.dlg.update(95)
        self.updateListing()
        self.dlg.update(100, "Preparing Configuration", "Finished")
        self.getControl(105).setVisible(True)
        self.getControl(106).setVisible(False)
        self.setFocusId(102)
        self.dlg.close()
        
        if self.focusChannel and self.focusChannel > 0:
            self.listcontrol.selectItem(self.focusChannel)  
        self.log("prepareConfig return")

        
    def parsePlugin(self, DetailLST, type='all'):
        self.log("parsePlugin")
        show_busy_dialog()
        PluginNameLst = []
        PluginPathLst = []
        try:
            dirCount = 0
            fleCount = 0
            PluginNameLst = []
            PluginPathLst = []
            PluginDirNameLst = []
            PluginDirPathLst = []
            
            for i in range(len(DetailLST)):
                Detail = (DetailLST[i]).split(',')
                filetype = Detail[0]
                title = Detail[1]
                title = self.chnlst.cleanLabels(title)
                genre = Detail[2]
                dur = Detail[3]
                description = Detail[4]
                file = Detail[5]
                
                if filetype == 'directory':
                    dirCount += 1
                    Color = 'red'
                    fileInt = 'D'
                elif filetype == 'file':
                    fleCount += 1
                    Color = 'green'
                    fileInt = 'F'
                    
                PluginNameLst.append(('[COLOR=%s][%s] [/COLOR]' + title) % (Color,fileInt))
                PluginPathLst.append(file)   
        except:
            pass
        PluginNameLst.append('[B]Return to settings[/B]')
        PluginPathLst.append('Return')
        hide_busy_dialog()
        return PluginNameLst, PluginPathLst
         
         
    def resetLabels(self):
        self.log("resetLabels")
        
        
    def clearLabel(self, id=None):
        self.log("clearLabel, id = " + str(id))
        if id:
            for i in range(len(id)):
                lid = id[i]
                try:
                    self.getControl(lid).setLabel(' ') 
                    self.getControl(lid).setLabel('')
                except:
                    pass
        else:
            # clear all channel labels
            for i in range(NUMBER_CHANNEL_TYPES):
                if i >= 7:
                    base = (120 + ((i + 1) * 10))
                    for n in range(10):
                        id = base + n
                        try:
                            self.getControl(id).setLabel(' ') 
                            self.getControl(id).setLabel('')  
                        except:
                            pass
                            
                            
    def clearLabel2(self, id=None):
        self.log("clearLabel2, id = " + str(id))
        if id:
            for i in range(len(id)):
                lid = id[i]
                try:
                    self.getControl(lid).setLabel(label2=' ') 
                    self.getControl(lid).setLabel(label2='')
                except:
                    pass
        else:
            # clear all channel labels
            for i in range(NUMBER_CHANNEL_TYPES):
                if i >= 7:
                    base = (120 + ((i + 1) * 10))
                    for n in range(10):
                        id = base + n
                        try:
                            self.getControl(id).setLabel(label2=' ') 
                            self.getControl(id).setLabel(label2='')  
                        except:
                            pass

                     
    def setChannelReset(self, hours, channel=None):
        if not channel:
            channel = self.channel
        self.log("setChannelReset, channel = " + str(channel))
        foundChname = False
        try:
            rulecount = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount'))
        except:
            rulecount = 0
        # change existing rule
        for i in range(rulecount):
            try:
                if int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_rule_%s_id" %str(i+1))) == 13:
                    ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_rule_%s_opt_1" %str(i+1))
                    foundChname = True                  
                    break
            except:
                pass

        # no rule found create new one
        if foundChname == False:
            ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rulecount", str(rulecount + 1))
            ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rule_%s_id" %str(rulecount + 1), "13")
            ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rule_%s_opt_1" %str(rulecount + 1), str(hours))
        self.madeChanges = 1

 
    def getChname(self, channel=None):
        self.log("getChname")
        if not channel:
            channel = self.listcontrol.getSelectedPosition() + 1
        theitem = self.listcontrol.getListItem(channel-1)
        return theitem.getProperty('chname')


    def clearTVSort(self, channel=None):
        if not channel:
            channel = self.channel
        self.log("clearTVSort, channel = " + str(channel))
        try:
            rulecount = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount'))
        except:
            rulecount = 0
        for i in range(RULES_PER_PAGE):         
            try:
                if int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_rule_%s_id" %str(i+1))) == 12:
                    ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rule_%s_id" %str(i+1), "")
                    ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rulecount", str(rulecount - 1))          
                    self.madeChanges = 1
                    break
            except:
                pass  

    
    def setTVSort(self, channel=None):
        if not channel:
            channel = self.channel
        self.log("setTVSort, channel = " + str(channel))
        try:
            rulecount = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount'))
        except:
            rulecount = 0    
        # check for exisiting rule
        for i in range(RULES_PER_PAGE):         
            try:
                if int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_rule_%s_id" %str(i+1))) == 12:
                    return
            except:
                pass
        # set rule
        ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rulecount", str(rulecount + 1))
        ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rule_%s_id" %str(rulecount + 1), "12")              
        self.madeChanges = 1 

        
    def setChname(self, name, channel=None):
        if not channel:
            channel = self.channel
        self.log("setChname, channel = " + str(channel))
        foundChname = False
        try:
            rulecount = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount'))
        except:
            rulecount = 0
        # change existing rule
        for i in range(rulecount):   
            try:
                if int(ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_rule_%s_id" %str(i+1))) == 1:
                    self.log("setChname, existing channel rule found! #" + str(i+1))
                    ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rule_%s_opt_1" %str(i+1), name)
                    self.log("setChname, existing channel rule renamed! #" + str(i+1))
                    foundChname = True                
                    break
            except:
                pass
        # no rule found create new one
        if foundChname == False:
            self.log("setChname, creating channel rule #" + str(rulecount+1))
            ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rulecount", str(rulecount + 1))
            ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rule_%s_id" % str(rulecount + 1), "1")
            ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_rule_%s_opt_1" % str(rulecount + 1), name)                
        self.madeChanges = 1
        

    # def swapRules(self, old, new):     
        # for i in range(RULES_PER_PAGE):         
        # try:
            # if int(ADDON_SETTINGS.getSetting("Channel_" + str(old) + "_rule_%s_id" %str(i+1))):
                # for x in range(rule.getOptionCount()):
                    # self.ruleList[-1].optionValues[x] = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_opt_' + str(x + 1))

                # ADDON_SETTINGS.setSetting("Channel_" + str(old) + "_rule_%s_opt_1" %str(i+1), "")
        # except:
            # pass        
        
        
    def setExclude(self, key):
        # todo add multiselect dialog via jarvis & plugin/upnp browse
        retval = inputDialog('Enter Labels to Exclude',self.getControl(key).getLabel())
        if retval and len(retval) > 0:
            return self.getControl(key).setLabel(retval)

        
    def setLimit(self, key):
        select = selectDialog(self.MediaLimitList, 'Select Media Limit')
        if select != -1:
            return self.getControl(key).setLabel('Media Limit:',label2=self.MediaLimitList[select])
    
    
    def setSort(self, key):
        select = selectDialog(self.SortOrderList, 'Select Sorting Order')
        if select != -1:
            return self.getControl(key).setLabel('Sort Order:',label2=self.SortOrderList[select])

            
    def fillSources(self, type, source, path=None):
        self.log("fillSources, type = " + type + ", source = " + source + ", path = " + str(path))
        if path:
            self.log("fillSources, path = " + path)
        # Parse Source, return title, path
        try:
            if source == 'PVR':
                self.log("PVR")
                NameLst, PathLst, IconLst = self.chnlst.PVRList
                select = selectDialog(NameLst, 'Select Kodi PVR Channel')
                if select != -1:
                    name = self.chnlst.cleanLabels(NameLst[select])
                    path = PathLst[select]
                    if len(path) > 0:
                        return name, path

            if source == 'Meta Plugin':
                retval = inputDialog('Enter Live network name','')
                if retval and len(retval) > 0:
                    return retval, 'plugin://plugin.video.meta/live/'+retval
                     
            elif source == 'HDhomerun':
                self.log("HDhomerun")
                NameLst, PathLst = self.chnlst.HDHRList
                select = selectDialog(NameLst, 'Select HDhomerun Channel')
                if select != -1:
                    name = self.chnlst.cleanLabels(NameLst[select])
                    path = PathLst[select]
                    if len(path) > 0:
                        return name, path
                                    
            elif source == 'Local Video':
                self.log("Local Video")
                retval = browse(1, "Select File", "video", "|".join(MEDIA_TYPES))
                if retval and len(retval) > 0:
                    return retval, retval
                    
            elif source == 'Local Music':
                self.log("Local Music")
                retval = browse(1, "Select File", "music", "|".join(MUSIC_TYPES))
                if retval and len(retval) > 0:
                    return retval, retval
                    
            elif source == 'Plugin':
                self.log("Plugin")
                if path:
                    while not self.LockBrowse:
                        NameLst, PathLst = self.parsePlugin(self.chnlst.PluginInfo(path))
                        select = selectDialog(NameLst, 'Select [COLOR=green][F][/COLOR]ile')
                        if select != -1:
                            if (NameLst[select]).startswith('[COLOR=green][F]'):
                                self.LockBrowse = True
                                break

                            if PathLst[select] == 'Return':
                                self.LockBrowse = True
                                NameLst = []
                                PathLst = []
                            else:
                                path = PathLst[select]      
                    return self.chnlst.cleanLabels(NameLst[select]), PathLst[select]
                else:
                    select = selectDialog(self.pluginNameList, 'Select Plugin')
                    if select != -1:
                        return self.chnlst.cleanLabels((self.pluginNameList)[select]), 'plugin://' + (self.pluginPathList)[select]
           
            elif source == 'Playon':
                self.log("Playon")
                if path:
                    while not self.LockBrowse:
                        NameLst, PathLst = self.parsePlugin(self.chnlst.PluginInfo(path))
                        select = selectDialog(NameLst, 'Select [COLOR=green][F][/COLOR]ile')
                        if select != -1:
                            if (NameLst[select]).startswith('[COLOR=green][F]'):
                                self.LockBrowse = True
                                break

                            if PathLst[select] == 'Return':
                                self.LockBrowse = True
                                NameLst = []
                                PathLst = []
                            else:
                                path = PathLst[select]      
                    return self.chnlst.cleanLabels(NameLst[select]), PathLst[select]
                else:
                    NameLst, PathLst = self.parsePlugin(self.chnlst.PluginInfo('plugin://plugin.video.Playonbrowser'))
                    hide_busy_dialog()
                    select = selectDialog(NameLst, 'Select [COLOR=green][F][/COLOR]ile')
                    if select != -1:
                        return self.chnlst.cleanLabels(NameLst[select]), PathLst[select]
                    
            elif source == 'UPNP':
                self.log("UPNP")
                if path:
                    while not self.LockBrowse:
                        NameLst, PathLst = self.parsePlugin(self.chnlst.PluginInfo(path))
                        select = selectDialog(NameLst, 'Select [COLOR=green][F][/COLOR]ile')
                        if select != -1:
                            if (NameLst[select]).startswith('[COLOR=green][F]'):
                                self.LockBrowse = True
                                break

                            if PathLst[select] == 'Return':
                                self.LockBrowse = True
                                NameLst = []
                                PathLst = []
                            else:
                                path = PathLst[select]      
                    return self.chnlst.cleanLabels(NameLst[select]), PathLst[select]
                else:
                    NameLst, PathLst = self.parsePlugin(self.chnlst.PluginInfo('upnp://'))
                    select = selectDialog(NameLst, 'Select [COLOR=green][F][/COLOR]ile')
                    if select != -1:
                        return self.chnlst.cleanLabels(NameLst[select]), PathLst[select]
                    
            elif source == 'Kodi Favourites':
                self.log("Kodi Favourites")
                FavouritesNameList, FavouritesPathList = self.chnlst.FavouritesList
                select = selectDialog(FavouritesNameList, 'Select Favourites')
                if select != -1:
                    return FavouritesNameList[select], FavouritesPathList[select]  
                  
            elif source == 'Youtube Live':
                self.log("Youtube Live")
                input = inputDialog('Enter Youtube Live ID or URL')
                if len(input) > 0:
                    if not input.startswith('http'):
                        input = 'https://www.youtube.com/watch?v='+input
                    return input, input
                    
            elif source == 'URL':
                self.log("URL")
                input = inputDialog('Enter URL')
                if len(input) > 0:
                    return input, input
                     
            elif source == 'Community List':
                self.log("Community List")
                if isCompanionInstalled() == True:
                    fillLst = self.chnlst.fillExternalList(type, path)
                    select = selectDialog(fillLst[0], 'Select %s' % path)
                    if select != -1:
                        return fillLst[0][select], fillLst[1][select], fillLst[2][select], fillLst[3][select], fillLst[4][select]        
                else:
                    infoDialog("Community List requires the PseudoCompanion plugin available from the Lunatixz Repository") 
                    
            elif source == 'M3U Playlist':
                self.log("M3U")
                select = selectDialog(self.ExternalPlaylistSources, 'Select M3U Source')
                if select != -1:
                    if self.ExternalPlaylistSources[select] == 'Local File':
                        self.log("M3U, Local File")
                        retval = browse(1, "Select M3U Playlist", "video", ".m3u")
                        NameLst, PathLst = self.chnlst.ListTuning('M3U',retval)
                        
                    elif self.ExternalPlaylistSources[select] == 'URL':
                        self.log("M3U, URL")
                        input, input = self.fillSources('','URL')
                        NameLst, PathLst = self.chnlst.ListTuning('M3U',input)  
                        
                    if len(NameLst) > 0:
                        select = selectDialog(NameLst, 'Select M3U Feed')
                        if select != -1:
                            return NameLst[select], PathLst[select]  
                    else:
                        infoDialog("Invalid Selection") 
            elif source == 'XML Playlist':
                self.log("XML")
                select = selectDialog(self.ExternalPlaylistSources, 'Select XML Source')
                if select != -1:    
                    if self.ExternalPlaylistSources[select] == 'Local File':
                        self.log("XML, Local File")
                        retval = browse(1, "Select XML Playlist", "video", ".xml")
                        NameLst, PathLst = self.chnlst.ListTuning('XML',retval)
                    
                    elif self.ExternalPlaylistSources[select] == 'URL':
                        self.log("XML, URL")
                        input, input = self.fillSources('','URL')
                        NameLst, PathLst = self.chnlst.ListTuning('XML',input)  
                        
                    if len(NameLst) > 0:
                        select = selectDialog(NameLst, 'Select XML Feed')
                        if select != -1:    
                            return NameLst[select], PathLst[select]  
                    else:
                        infoDialog("Invalid Selection") 
            elif source == 'PLX Playlist':
                self.log("PLX")
                select = selectDialog(self.ExternalPlaylistSources, 'Select PLX Source')
                if select != -1:
                    if self.ExternalPlaylistSources[select] == 'Local File':
                        self.log("PLX, Local File")
                        retval = browse(1, "Select PLX Playlist", "video", ".plx")
                        NameLst, PathLst = self.chnlst.ListTuning('PLX',retval)
                    elif self.ExternalPlaylistSources[select] == 'URL':
                        self.log("PLX, URL")
                        input, input = self.fillSources('','URL')
                        NameLst, PathLst = self.chnlst.ListTuning('PLX',input)
                        
                    if len(NameLst) > 0:
                        select = selectDialog(NameLst, 'Select PLX Feed')
                        if select != -1:
                            return NameLst[select], PathLst[select]
                    else:
                        infoDialog("Invalid Selection") 
            else:
                return  
        except:
            hide_busy_dialog()
            

    def deleteChannel(self, curchan):
        self.log("deleteChannel")
        if( (self.showingList == True) and (ADDON_SETTINGS.getSetting("Channel_" + str(curchan) + "_type") != "9999")):
            if yesnoDialog("Are you sure you want to clear channel %s?" %str(curchan)):
                self.madeChanges = 1
                ADDON_SETTINGS.setSetting("Channel_" + str(curchan) + "_type", "9999")  
                ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rulecount','0')
                theitem = self.listcontrol.getListItem(curchan-1)
                theitem.setLabel2('')
                theitem.setProperty('chname','')
                self.updateListing(curchan)
                self.setFocusId(102)
                
                
    def changeChanNum(self, channel):
        if yesnoDialog("Move channel " + str(channel) + "?"):
            inuse = False
            while not inuse:
                retval = inputDialog('Enter channel ' + str(channel) + "'s new number", key=xbmcgui.INPUT_NUMERIC)
                if retval and len(retval) > 0:
                    try:
                        chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(retval) + "_type"))
                        if chantype == 9999:
                            raise Exception()
                        infoDialog("Channel "+str(retval)+" already in use")
                    except:
                        inuse = True
                        if yesnoDialog("Do you want to save channel " + str(channel) + " as " + str(retval) + " ?"):
                            self.changeChannelNum(channel, retval)
    
                            
    def changeChannelNum(self, old, new):
        self.log("changeChannelNum")
        show_busy_dialog()
        chantype = 9999
        setting1 = ''
        setting2 = ''
        setting3 = ''
        setting4 = ''        
        try:
            chantype = ADDON_SETTINGS.getSetting("Channel_" + str(old) + "_type")
        except:
            self.log("Unable to get channel type")
        
        # old
        setting1 = ADDON_SETTINGS.getSetting("Channel_" + str(old) + "_1")
        setting2 = ADDON_SETTINGS.getSetting("Channel_" + str(old) + "_2")
        setting3 = ADDON_SETTINGS.getSetting("Channel_" + str(old) + "_3")
        setting4 = ADDON_SETTINGS.getSetting("Channel_" + str(old) + "_4")
        self.loadRules(old)
        
        # delete old channel
        ADDON_SETTINGS.setSetting("Channel_" + str(old) + "_type", "9999") 
        ADDON_SETTINGS.setSetting('Channel_' + str(old) + '_rulecount','0')
        theitem = self.listcontrol.getListItem(old-1)
        theitem.setLabel2('')
        theitem.setProperty('chname','')
        self.updateListing(old)

        # write new channel
        ADDON_SETTINGS.setSetting("Channel_" + str(new) + "_type", chantype)
        ADDON_SETTINGS.setSetting("Channel_" + str(new) + "_1", setting1)
        ADDON_SETTINGS.setSetting("Channel_" + str(new) + "_2", setting2)
        ADDON_SETTINGS.setSetting("Channel_" + str(new) + "_3", setting3)
        ADDON_SETTINGS.setSetting("Channel_" + str(new) + "_4", setting4)  
        self.saveRules(new)
        
        #refresh and focus
        self.updateListing()    
        self.setFocusId(102) 
        self.listcontrol.selectItem(int(new)-1)  
        self.madeChanges = 1  
        hide_busy_dialog()

        
    def listSubmit(self, channel):
        self.log("listSubmit")        
        try:
            channame = self.getChname(channel)
            type = ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_type")
            setting1 = (ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_1"))
            setting2 = (ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_2"))
            setting3 = (ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_3"))
            setting4 = (ADDON_SETTINGS.getSetting("Channel_" + str(channel) + "_4"))
        except:
            pass
            
        # Custom XSP Playlist
        if str(type) == '0':
            if setting1 != '':
                plname = self.getSmartPlaylistName(setting1)
                if len(plname) != 0:   
                    self.listSubmisson("PseudoTVLive Submission: Chtype = " + str(type), 'Custom Playlist|' + setting1, xbmc.translatePath(setting1))
                else:
                    # todo retval = inputDialog('Enter Playlist Name')
                    # if retval and len(retval) > 0:
                    infoDialog("Please Edit Playlist Name.")
        else:
            # # prevent plugins not in kodis repo from being submitted.
            # if type in ['8','9','15'] and setting1.startswith('plugin'):
                # if isKodiRepo(setting1) == False:
                    # return
            select = selectDialog(self.GenreLst, 'Select Submission Genre Type')
            if select != -1:
                genre = self.GenreLst[select]
                
                #todo prompt for missing info
                #retval = inputDialog('Enter info')
                # if retval and len(retval) > 0:
                if setting1 == '':
                    setting1 = '""'
                if setting2 == '':
                    setting2 = '""'
                if setting3 == '':
                    setting3 = '""'
                if setting4 == '':
                    setting4 = '""'
                if channame == '':
                    channame = '""'

                # correct multitube format
                if type == '10':
                    setting1 = setting1.replace('|',',')     
                    
                self.optionList = [str(type), str(setting1), str(setting2), str(setting3), str(setting4), str(channame)]
                self.listSubmisson("PseudoTVLive Submission: Chtype = " + str(type) + ", Genre = " + str(genre), ('|').join(self.optionList))
        
        
    def listSubmisson(self, subject, body, attach=None):
        self.log("listSubmisson")  
        try:
            sender = (REAL_SETTINGS.getSetting('Gmail_User'))            
            if sender == 'email@gmail.com':
                okDialog('Enter your gmail address & password','Found in settings under the "Community" tab')
                return
            sendGmail(subject, body, attach)
            MSG = 'Submisson Complete'
            okDialog('Thank you for your submission, Please wait 24-48hrs to process your submission.','[COLOR=red]Warning!! repeat spammers will be banned!![/COLOR]')
        except Exception,e:
            self.log("listSubmisson, Failed! " + str(e))  
            ErrorNotify("Submission Failed!") 

            
    def setYoutubeEX(self, note=False):
        self.getControl(234).setVisible(True)
        if (self.getControl(230).getLabel2()) in ['Channel']:
            self.getControl(234).setLabel('Youtube ID ex. "vevo" or "UCcKfSNBlSTsfT-WgPmCVyXQ"')
            if note == True:
                infoDialog('Youtube ID ex. "vevo" or "UCcKfSNBlSTsfT-WgPmCVyXQ"',time=15000)
        elif (self.getControl(230).getLabel2()) in ['Playlist']:
            self.getControl(234).setLabel('Youtube ID ex. "PL4mjwxcyyfPhWcInmVVg3OsHnmMsPsecJ"')
            if note == True:
                infoDialog('Youtube ID ex. "PL4mjwxcyyfPhWcInmVVg3OsHnmMsPsecJ"',time=15000)
        elif (self.getControl(230).getLabel2()) in ['Multi Channel','Multi Playlist']:
            self.getControl(234).setLabel('Separate MultiTube with [COLOR=blue][B]|[/B][/COLOR], ex. ESPN[COLOR=blue][B]|[/B][/COLOR]ESPN2')
            if note == True:
                infoDialog('Separate MultiTube with [COLOR=blue][B]|[/B][/COLOR], ex. ESPN[COLOR=blue][B]|[/B][/COLOR]ESPN2',time=15000)
        elif (self.getControl(230).getLabel2()) == 'Search Query':
            self.getControl(234).setLabel('Search w/[COLOR=red]Safesearch [moderate|strict][/COLOR], ex. (Football+Soccer) or (Football Soccer) or ([COLOR=red]strict|[/COLOR]Dick+Cheney)')
            if note == True:
                infoDialog('Search w/[COLOR=red]Safesearch [moderate|strict][/COLOR], ex. (Football+Soccer) or (Football Soccer) or ([COLOR=red]strict|[/COLOR]Dick+Cheney)',time=15000)
        else:
            self.getControl(234).setVisible(False)
            
            
    def writeChanges(self):
        ADDON_SETTINGS.writeSettings()

        if CHANNEL_SHARING:
            realloc = REAL_SETTINGS.getSetting('SettingsFolder')
            xbmcvfs.copy(SETTINGS_LOC + '/settings2.xml', realloc + '/settings2.xml')

            
    def updateListing(self, channel = -1):
        self.log("updateListing")
        show_busy_dialog()
        start = 0
        end = CHANNEL_LIMIT

        if channel > -1:
            start = channel - 1
            end = channel

        for i in range(start, end):
            theitem = self.listcontrol.getListItem(i)
            chantype = 9999
            chansetting1 = ''
            chansetting2 = ''
            chansetting3 = ''
            chansetting4 = ''
            channame = ''
            newlabel = ''
            rules = ''

            try:
                chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_type"))
                chansetting1 = ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_1")
                chansetting2 = ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_2")
                chansetting3 = ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_3")
                chansetting4 = ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_4")
            except:
                pass
            
            if chantype != 9999:
                name = self.chnlst.getChannelName(chantype, i+1, chansetting1, False)
                channame = self.chnlst.getChannelName(chantype, i+1, chansetting1)
                theitem.setLabel2(getChanPrefix(chantype, name))
                theitem.setProperty('chlogo',(xbmc.translatePath(os.path.join(LOGO_LOC,channame+'.png'))))
                theitem.setProperty('chname',channame)
            theitem.setProperty('chtype',str(chantype))
            theitem.setProperty('chnum',str(i + 1))
            theitem.setProperty('isfav',self.chkChanFavorite(i + 1))
            
            # fill rule names
            rules = self.fillRules(i + 1)              
            if chantype in [0,1,3,5,6] and chansetting2 == str(MODE_ORDERAIRDATE):
                rules.append("Play TV Shows In Order")
            rules = '\n'.join(list(set(rules)))
            theitem.setProperty('chrules','[B]Channel Rules:[/B]\n'+rules)
        hide_busy_dialog()
        self.log("updateListing return")
   
__cwd__ = REAL_SETTINGS.getAddonInfo('path')

mydialog = ConfigWindow("script.pseudotv.live.ChannelConfig.xml", __cwd__, "Default")
del mydialog