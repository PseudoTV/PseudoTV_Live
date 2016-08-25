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

import xbmc, xbmcgui, xbmcplugin, xbmcvfs, xbmcaddon

from Globals import * 
from FileAccess import *  
from ChannelList import ChannelList
from utils import *

try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
      
      
class APP(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log('__init__')
        self.chanlist = ChannelList()
        
        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('APP: ' + msg, level)


    def onFocus(self, controlid):
        self.log('onFocus')
        
        
    def onInit(self):
        self.log('onInit')
        self.PanelPlugins = self.getControl(500)
        self.PanelItems = self.getControl(501)
        self.fillPlugins()
        self.setFocus(self.PanelPlugins)
       
        
    def onClick(self, controlid):
        self.log('onClick ' + str(controlid))
        if controlid == 500:
            playitem = self.PanelPlugins.getListItem(self.PanelPlugins.getSelectedPosition())
            self.chanlist.fillListItems('plugin://'+ playitem.getProperty('mediapath'))
            self.setFocus(self.PanelItems)
            # xbmc.executebuiltin('Container.Refresh') 
        elif controlid in [6001,6002,6003,6004]:
            if controlid == 6001:
                self.log('ACTION_TELETEXT_RED')
                self.MyOverlayWindow.windowSwap('EPG')
            elif controlid == 6002:
                self.log('ACTION_TELETEXT_GREEN')
                self.MyOverlayWindow.windowSwap('DVR')
            elif controlid == 6003:
                self.log('ACTION_TELETEXT_YELLOW')
                self.MyOverlayWindow.windowSwap('VOD')
            elif controlid == 6004:
                self.log('ACTION_TELETEXT_BLUE') 
                self.MyOverlayWindow.windowSwap('APP')

                
    def onAction(self, act):
        self.log('onAction ' + str(act.getId()))
        action = act.getId()
        if action in ACTION_PREVIOUS_MENU:
            self.closeAPP()  
        
        elif action == ACTION_TELETEXT_RED:
            self.log('ACTION_TELETEXT_RED')
            self.MyOverlayWindow.windowSwap('EPG')
        
        elif action == ACTION_TELETEXT_GREEN:
            self.log('ACTION_TELETEXT_GREEN')
            self.MyOverlayWindow.windowSwap('DVR')
        
        elif action == ACTION_TELETEXT_YELLOW:
            self.log('ACTION_TELETEXT_YELLOW')
            self.MyOverlayWindow.windowSwap('VOD')
                
        elif action == ACTION_TELETEXT_BLUE:
            self.log('ACTION_TELETEXT_BLUE')
            self.MyOverlayWindow.windowSwap('APP')
            
        if action in ACTION_PREVIOUS_MENU:
            print 'ACTION_PREVIOUS_MENU'
        
        elif action in ACTION_MOVE_DOWN: 
            print 'ACTION_MOVE_DOWN'
                
        elif action in ACTION_MOVE_UP:
            print 'ACTION_MOVE_UP'

        elif action in ACTION_MOVE_LEFT: 
            print 'ACTION_MOVE_LEFT'
        
        elif action in ACTION_MOVE_RIGHT:
            print 'ACTION_MOVE_RIGHT'
            
        elif action in ACTION_PAGEDOWN: 
            print 'ACTION_PAGEDOWN'
                 
        elif action in ACTION_PAGEUP: 
            print 'ACTION_PAGEUP'
 
        elif action in ACTION_SELECT_ITEM:
            print 'ACTION_SELECT_ITEM'
                
                
    def closeAPP(self):
        self.log('closeAPP')     
        if self.MyOverlayWindow.channelThread.isAlive():
            self.MyOverlayWindow.channelThread.unpause()
        self.close()
        
        
    def fillPlugins(self, type='video'):
        self.log('fillPlugins, type = ' + type)
        json_query = ('{"jsonrpc":"2.0","method":"Addons.GetAddons","params":{"type":"xbmc.addon.%s","properties":["name","path","thumbnail","description","fanart","summary"]}, "id": 1 }'%type)
        json_detail = self.chanlist.sendJSON(json_query)
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
                description = self.chanlist.cleanLabels(descriptions.group(1))
            else:
                description = ''
            if names and paths:
                name = self.chanlist.cleanLabels(names.group(1))
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
                    self.PanelPlugins.addItem(self.Items) 
    

    def fillListItems(self, url, type='video', file_type=False):
        self.log('fillListItems')
        self.Items = []
        if not file_type:
            detail = uni(self.chanlist.requestList(url, type))
        else:
            detail = uni(self.chanlist.requestItem(url, type))
        for f in detail:
            files = re.search('"file" *: *"(.*?)",', f)
            filetypes = re.search('"filetype" *: *"(.*?)",', f)
            labels = re.search('"label" *: *"(.*?)",', f)
            thumbnails = re.search('"thumbnail" *: *"(.*?)",', f)
            fanarts = re.search('"fanart" *: *"(.*?)",', f)
            descriptions = re.search('"description" *: *"(.*?)",', f)
            
            if filetypes and labels and files:
                filetype = filetypes.group(1)
                name = self.chanlist.cleanLabels(labels.group(1))
                file = (files.group(1).replace("\\\\", "\\"))
                
                if not descriptions:
                    description = ''
                else:
                    description = self.chanlist.cleanLabels(descriptions.group(1))
                
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
        