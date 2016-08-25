#   Copyright (C) 2016 Kevin S. Graer
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

import sys, os
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

from resources.lib.utils import *
from resources.lib.Globals import *
from resources.lib.ChannelList import ChannelList

class Main:
  
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('capture: ' + msg, level)

        
    def __init__(self):
        self.log("__init__")
        setProperty("PseudoTVConfigRunning", "True")
        
        while getProperty("PseudoTVService") == "True":
            xbmc.sleep(25)
            
        self.chnlst = ChannelList()
        self.chnlst.fillPVR() 
        
        # InfoLabel Parameters  
        self.Label       = xbmc.getInfoLabel('ListItem.Label')
        self.Path        = xbmc.getInfoLabel('ListItem.FolderPath')
        self.FileName    = xbmc.getInfoLabel('ListItem.FilenameAndPath')
        self.DBIDType    = xbmc.getInfoLabel('ListItem.DBTYPE')
        self.AddonName   = xbmc.getInfoLabel('Container.PluginName')
        self.AddonType   = xbmc.getInfoLabel('Container.Property(addoncategory)')
        self.Description = xbmc.getInfoLabel('ListItem.Property(Addon.Description)')
        self.plot        = xbmc.getInfoLabel('ListItem.Plot')
        self.plotOutline = xbmc.getInfoLabel('ListItem.PlotOutline')
        self.isPlayable  = xbmc.getInfoLabel('ListItem.Property(IsPlayable)').lower() == 'true'
        self.isFolder    = xbmc.getCondVisibility('ListItem.IsFolder') == 1
 
        if not self.plot:
            if self.plotOutline:
                self.Description = self.plotOutline
            elif not self.Description:
                self.Description = self.Label
        else:  
            self.Description = self.plot
          
        if self.AddonName:
            ADDON = xbmcaddon.Addon(id=self.AddonName)
            ADDON_ID = ADDON.getAddonInfo('id')
            self.AddonName = ADDON.getAddonInfo('name')
            
        self.Label = self.chnlst.cleanLabels(self.Label)
        self.Description  = self.chnlst.cleanLabels(self.Description)
        self.AddonName = self.chnlst.cleanLabels(self.AddonName)
        self.log("%s, %s, %s, %s, %s, %s, %s, %s, %s"%(self.Label,self.Path,self.FileName,self.DBIDType,self.AddonName,self.AddonType,self.Description,str(self.isPlayable),str(self.isFolder)))       
        self.ImportChannel()
          
   
    def onInit(self):
        self.log("onInit")
        chkLowPower()
        
        
    def ImportChannel(self):
        self.log("ImportChannel")
        show_busy_dialog()
        self.chantype = 9999
        self.setting1 = ''
        self.setting2 = ''
        self.setting3 = ''
        self.setting4 = ''
        self.channame = ''
        self.theitem = []
        self.itemlst = []
        ADDON_SETTINGS.loadSettings()
        
        for i in range(CHANNEL_LIMIT):
            self.theitem.append(str(i + 1))

        self.updateListing()
        hide_busy_dialog()
        available = False

        if len(self.itemlst) == 0:
            setProperty("PTVL.CM.LASTCHAN","0")      
        try:
            Lastchan = int(getProperty("PTVL.CM.LASTCHAN"))
            self.log("ImportChannel, Lastchan = " + str(Lastchan))
            self.nitemlst = self.itemlst
            self.itemlst = self.nitemlst[Lastchan:] + self.nitemlst[:Lastchan]
        except:
            pass
            
        while not available:
            select = selectDialog(self.itemlst, 'Select Channel Number')
            if select != -1:
                # self.channel = select + 1
                self.channel = int(self.chnlst.cleanLabels((self.itemlst[select]).split(' - ')[0]))
                if not (self.itemlst[select]).startswith('[COLOR=dimgrey]'):
                    available = True
                    
                    # determine chtype
                    if self.AddonName == 'PseudoCompanion' and self.Label.startswith('Cinema Theme'):
                        self.chantype = 14
                    elif self.Path[-3:].lower() == 'xsp':
                        self.chantype = 0
                    elif self.Path.lower().startswith('plugin://plugin.video.youtube/channel/'):
                        self.chantype = 10
                        self.YTtype = 1
                    elif self.Path.lower().startswith(('plugin://plugin.video.youtube/playlist/','plugin://plugin.video.spotitube/?limit&mode=listyoutubeplaylist')):
                        self.chantype = 10
                        self.YTtype = 2
                    elif self.Path.lower().startswith(('plugin', 'http', 'rtmp', 'pvr', 'hdhomerun', 'upnp')):
                        if self.isPlayable == True:
                            if yesnoDialog('Add source as', no="LiveTV", yes="InternetTV"):
                                self.chantype = 8
                            else:
                                self.chantype = 9
                        else:
                            if self.Path.lower().startswith(('pvr')) and self.Label.startswith('Channels'):
                                self.chantype = 8
                                return self.buildNetworks(self.Path+'tv/All channels/')
                            elif self.Path.lower().startswith(('pvr')):
                                self.chantype = 8
                            elif self.isFolder == True and self.Label.lower() in ['pseudonetworks','networks','channels'] and self.Path.lower().startswith(('plugin')):
                                self.chantype = 15
                                return self.buildNetworks(self.Path)
                            elif self.isFolder == True and self.Path.lower().startswith(('plugin')):
                                self.chantype = 15
                            elif self.isFolder == True and self.Path.lower().startswith(('upnp')):
                                self.chantype = 16
                    elif self.isFolder == True:
                        if self.DBIDType == 'tvshow':
                            self.chantype = 6
                        elif self.DBIDType == '':
                            self.chantype = 7    
                    else:
                        infoDialog("Not a valid source")                    
                    self.buildChannel()
                else:
                    infoDialog("Channel "+str(self.channel)+" already in use")
            else:
                available = True
        self.log("chantype = "+str(self.chantype))
            
            
    # export bulk channels, add subfolders as channels.
    def buildNetworks(self, url):
        self.log("buildNetworks, url = " + url)
        detail = uni(self.chnlst.requestList(url))
        if yesnoDialog('Add %d Channels?' % len(detail)):
            show_busy_dialog()
            
            for f in detail:
                files = re.search('"file" *: *"(.*?)",', f)
                filetypes = re.search('"filetype" *: *"(.*?)",', f)
                labels = re.search('"label" *: *"(.*?)",', f)
                if filetypes and labels and files:
                    filetype = filetypes.group(1)
                    name = self.chnlst.cleanLabels(labels.group(1))
                    file = (files.group(1).replace("\\\\", "\\"))
                    
                    if filetype == 'directory':
                        if self.chantype == 15:
                            self.setting1 = file
                            self.setting2 = ''
                            self.setting3 = ''
                            self.setting4 = '1'
                            self.channame = name
                            self.saveSettings()
                            self.fixChannel(self.channel)
                            
                    elif filetype == 'file':
                        if self.chantype == 8:
                            self.setting1 = name
                            self.setting2 = file
                            self.setting3 = 'pvr'
                            self.setting4 = ''
                            self.channame = name
                            self.saveSettings()
                            self.fixChannel(self.channel)
            hide_busy_dialog()
            self.openManager()
    
    
    # find next available channel when exporting bulk channels.
    def fixChannel(self, channel):
        while self.getChtype(self.channel+1) != 9999:
            self.channel +=1
        
            
    def buildChannel(self):
        self.log("buildChannel, chantype = " + str(self.chantype))
        self.addonDirectoryPath = []
        
        if self.chantype == 0:
            self.setting1 = xbmc.translatePath(self.Path)
            self.setting2 = '4'
            self.channame = self.chnlst.getSmartPlaylistName(self.Path)
        
        elif self.chantype == 6:
            self.setting1 = self.Label
            self.setting2 = '4'
            self.channame = self.Label
            
        elif self.chantype == 7:
            self.setting1 = xbmc.translatePath(self.Path)
            self.setting3 = ''
            self.setting4 = '0'
            self.channame = self.Label
            
        elif self.chantype == 8:
            XMLTV = listXMLTV()
            xmltvFle = False
            if XMLTV:
                xmltvFle = xmltvflePath(XMLTV)
                if xmltvFle:
                    self.channame, self.setting1 = self.chnlst.findZap2itID(self.chnlst.cleanLabels(self.Label), xbmc.translatePath(xmltvFle))
                    self.channame = self.Label
                    self.setting2 = self.Path
                    self.setting3 = XMLTV
            else:
                return
                # self.chantype = 9
                # self.buildChannel()
            
        elif self.chantype == 9:
            self.setting1 = '5400'
            self.setting2 = self.Path
            self.setting3 = self.Label
            self.setting4 = self.Description
            self.channame = self.Label +' - '+ self.AddonName
            
        elif self.chantype == 10:
            if self.YTtype == 1:
                self.setting1 = ((self.Path).replace('plugin://plugin.video.youtube/channel/','')).replace('/','')
            elif self.YTtype == 2:
                self.setting1 = ((self.Path).replace('plugin://plugin.video.','').replace('youtube/playlist/','').replace('spotitube/?limit&mode=listyoutubeplaylist&type=browse&url=','')).replace('/','')
            self.setting2 = str(self.YTtype)
            self.setting3 = '500'
            self.setting4 = '0'
            
            if self.Label.startswith('UC'):
                self.channame = self.chnlst.getYoutubeChname(self.Label) 
            else:
                self.channame = self.Label
            
        elif self.chantype == 14:
            if self.Label.startswith('Cinema Theme'):
                self.setting1 = 'cinema'
                self.setting2 = self.Path
                self.setting3 = self.Label
                self.setting4 = ''
                self.channame = 'PseudoCinema'   
            
        elif self.chantype == 15:
            self.setting1 = self.Path
            self.setting2 = ''
            self.setting3 = PLUGINUPNP_MAXPARSE
            self.setting4 = '0'
            self.channame = self.Label
            
        elif self.chantype == 16:
            self.setting1 = self.Path
            self.setting2 = ''
            self.setting3 = ''
            self.setting4 = '0'
            self.channame = self.Label
            
        self.saveSettings()
        self.openManager()
        
        
    def openManager(self):
        if yesnoDialog('Channel Successfully Added', 'Open Channel Manager?'):
            xbmc.executebuiltin("RunScript("+ADDON_PATH+"/config.py, %s)" %str(self.channel))
        else:
            setProperty("PseudoTVConfigRunning", "False")

            
    def getChtype(self, channel):
        self.log("getChtype")
        try:
            chantype = int(ADDON_SETTINGS.getSetting("Channel_" + str(channel - 1) + "_type"))
        except:
            chantype = 9999
        return chantype
        
        
    def updateListing(self, channel = -1):
        self.log("updateListing")
        start = 0
        end = CHANNEL_LIMIT

        if channel > -1:
            start = channel - 1
            end = channel

        for i in range(start, end):
            try:
                theitem = self.theitem[i]
                chantype = 9999
                chansetting1 = ''
                chansetting2 = ''
                chansetting3 = ''
                chansetting4 = ''
                channame = ''

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
                    channame = getChanPrefix(chantype, name)
                    
                if channame:
                    channame = '[COLOR=dimgrey][B]'+ theitem +'[/B] - '+ channame+'[/COLOR]'
                else:
                    channame = '[COLOR=blue][B]'+theitem+'[/B][/COLOR]'
                self.itemlst.append(channame)
            except:
                pass
        self.log("updateListing return")
             
             
    def saveSettings(self):
        self.log("saveSettings channel " + str(self.channel))
        chantype = 9999
        chan = str(self.channel)
        setProperty("PTVL.CM.LASTCHAN",chan)

        chantype = "Channel_" + chan + "_type"
        setting1 = "Channel_" + chan + "_1"
        setting2 = "Channel_" + chan + "_2"
        setting3 = "Channel_" + chan + "_3"
        setting4 = "Channel_" + chan + "_4"

        ADDON_SETTINGS.setSetting(chantype, str(self.chantype))
        ADDON_SETTINGS.setSetting(setting1, self.setting1)
        ADDON_SETTINGS.setSetting(setting2, self.setting2)
        ADDON_SETTINGS.setSetting(setting3, self.setting3)
        ADDON_SETTINGS.setSetting(setting4, self.setting4)    
        ADDON_SETTINGS.setSetting("Channel_" + chan + "_changed", "True")
        # set chname rule
        if chantype > 7:
            ADDON_SETTINGS.setSetting("Channel_" + chan + "_rulecount", "1")
            ADDON_SETTINGS.setSetting("Channel_" + chan + "_rule_1_id", "1")
            ADDON_SETTINGS.setSetting("Channel_" + chan + "_rule_1_opt_1", self.channame)    
            
        # set PseudoCinema rules
        if chantype == 14 and self.channame == 'PseudoCinema':
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rulecount", "5")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_id", "1")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_1_opt_1", "PseudoCinema")  
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_2_id", "8")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_3_id", "14")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_3_opt_1", "No")  
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_4_id", "17")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_4_opt_1", "No")  
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_5_id", "15")
            ADDON_SETTINGS.setSetting("Channel_" + str(channelNum) + "_rule_5_opt_1", "No") 
            
        if chantype in [15,16]:
            ADDON_SETTINGS.setSetting("Channel_" + chan + "_rulecount", "2")
            ADDON_SETTINGS.setSetting("Channel_" + chan + "_rule_2_id", "20")
            ADDON_SETTINGS.setSetting("Channel_" + chan + "_rule_2_opt_1", str(MINFILE_DURATION))   
        self.log("saveSettings return")
                
if (__name__ == "__main__"):
    Main()
xbmc.log('PseudoTV Live Export Finished')