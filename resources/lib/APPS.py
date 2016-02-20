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
      
      
class APPS(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log('__init__')
        self.chanlist = ChannelList()
        
        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('APPS: ' + msg, level)


    def onFocus(self, controlid):
        self.log('onFocus')
        
        
    def onInit(self):
        self.log('onInit')
        self.chanlist.PanelItems = self.getControl(500)
        self.chanlist.fillPlugins()
        self.setFocus(self.chanlist.PanelItems)
       
        
    def onClick(self, controlId):
        self.log('onClick ' + str(controlId))
        if controlId == 500:
            pos = self.chanlist.PanelItems.getSelectedPosition()
            playitem = self.chanlist.PanelItems.getListItem(pos)
            url = 'plugin://'+ playitem.getProperty('mediapath')
            self.chanlist.fillListItems(url)
            self.setFocus(self.chanlist.PanelItems)
            # xbmc.executebuiltin('Container.Refresh') 
            
            
    def onAction(self, act):
        self.log('onAction ' + str(act.getId()))
        action = act.getId()
        if action in ACTION_PREVIOUS_MENU:
            self.closeAPPS()  
        
        elif action == ACTION_TELETEXT_RED:
            self.log('ACTION_TELETEXT_RED')
            self.MyOverlayWindow.windowSwap('EPG')
        
        elif action == ACTION_TELETEXT_GREEN:
            self.log('ACTION_TELETEXT_GREEN')
            self.MyOverlayWindow.windowSwap('DVR')
        
        elif action == ACTION_TELETEXT_YELLOW:
            self.log('ACTION_TELETEXT_YELLOW')
            self.MyOverlayWindow.windowSwap('ONDEMAND')
                
        elif action == ACTION_TELETEXT_BLUE:
            self.log('ACTION_TELETEXT_BLUE')
            self.MyOverlayWindow.windowSwap('APPS')
            
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
                
                
    def closeAPPS(self):
        self.log('closeAPPS')
        self.close()