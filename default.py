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
    
import os, sys, re, shutil, threading
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
    
from resources.lib.Globals import *
from resources.lib.utils import *

# Script constants
__scriptname__ = "PseudoTV Live"
__author__     = "Lunatixz, Jason102"
__url__        = "https://github.com/Lunatixz/script.pseudotv.live"
__settings__   = xbmcaddon.Addon(id='script.pseudotv.live')
__cwd__        = __settings__.getAddonInfo('path')
__version__    = __settings__.getAddonInfo('version')
__language__   = __settings__.getLocalizedString
       
def PseudoTV():
    try:
        setProperty("PseudoTVRunning", "True")
        import resources.lib.Overlay as Overlay
        if hasVersionChanged(__version__) == True: 
            HandleUpgrade()            
        preStart()
        MyOverlayWindow = Overlay.TVOverlay("script.pseudotv.live.TVOverlay.xml", __cwd__, Skin_Select)

        for curthread in threading.enumerate():
            log("Active Thread: " + str(curthread.name), xbmc.LOGERROR)
            if curthread.name != "MainThread":
                try:
                    curthread.join()      
                except: 
                    pass
                log("Joined " + curthread.name)               
                
        del MyOverlayWindow
    except Exception,e:
        log('default: PseudoTV Overlay Failed! ' + str(e))
        buggalo.onExceptionRaised()
    setProperty("PseudoTVRunning", "False")
        
#Start PseudoTV
# Adapting a solution from ronie (http://forum.xbmc.org/showthread.php?t=97353)
if getProperty("PseudoTVRunning") != "True":
    PseudoTV()
else:
    log('default: Already running, exiting', xbmc.LOGERROR)
    ErrorNotify("Already running please wait and try again later.")