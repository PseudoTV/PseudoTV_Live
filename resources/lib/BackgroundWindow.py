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
      
      
class BackgroundWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log('__init__')
        self.chanlist = ChannelList()
        
        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('BackgroundWindow: ' + msg, level)


    def onFocus(self, controlid):
        self.log('onFocus')
        
        
    def onInit(self):
        self.log('onInit')
        