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
from Artdownloader import *
from utils import *

try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
      
      
class VOD(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log('__init__')
        
        
    def onFocus(self, controlid):
        pass
        
        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('VOD: ' + msg, level)

    
    def onInit(self):
        self.log('onInit')
        
        
    def onClick(self, controlid):
        self.log('onClick ' + str(controlid))
        if controlid in [6001,6002,6003,6004]:
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
            self.closeVOD()   
            
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
        
        elif action == ACTION_MOVE_DOWN: 
            print 'ACTION_MOVE_DOWN'
                
        elif action == ACTION_MOVE_UP:
            print 'ACTION_MOVE_UP'

        elif action == ACTION_MOVE_LEFT: 
            print 'ACTION_MOVE_LEFT'
        
        elif action == ACTION_MOVE_RIGHT:
            print 'ACTION_MOVE_RIGHT'
            
        elif action == ACTION_PAGEDOWN: 
            print 'ACTION_PAGEDOWN'
                 
        elif action == ACTION_PAGEUP: 
            print 'ACTION_PAGEUP'
 
        elif action == ACTION_SELECT_ITEM:
            print 'ACTION_SELECT_ITEM'
                
           
    def closeVOD(self):
        self.log('closeVOD')   
        if self.MyOverlayWindow.channelThread.isAlive():
            self.MyOverlayWindow.channelThread.unpause()
        self.close()