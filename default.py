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
    import resources.lib.Overlay as Overlay
    setProperty("PseudoTVRunning", "True")

    try:
        MyOverlayWindow = Overlay.TVOverlay("script.pseudotv.live.TVOverlay.xml", __cwd__, Skin_Select)
    except Exception,e:
        log('default: PseudoTV Overlay Failed! ' + str(e))
        Error('PseudoTV Live','Error loading "' + Skin_Select + '" skin!','Verify selected skin.') 
        return
        
    for curthread in threading.enumerate():
        # try:
        log("Active Thread: " + str(curthread.name), xbmc.LOGERROR)
        if curthread.name != "MainThread":
            try:
                curthread.join()      
            except: 
                pass
            log("Joined " + curthread.name)               
        # except: 
            # pass
            
    del MyOverlayWindow
    setProperty("PseudoTVRunning", "False")
    
# Adapting a solution from ronie (http://forum.xbmc.org/showthread.php?t=97353)
if getProperty("PseudoTVRunning") != "True":
    setProperty("PseudoTVRunning", "True")
    if hasVersionChanged(__version__) == True: 
        HandleUpgrade()
    else:
        chkVersion()
        if preStart() == True:
            #Start PseudoTV
            PseudoTV()
else:
    log('default: Already running, exiting', xbmc.LOGERROR)
    xbmc.executebuiltin("Notification( %s, %s, %d, %s)" % ("PseudoTV Live", "Already running please wait and try again later.", 4000, THUMB) )