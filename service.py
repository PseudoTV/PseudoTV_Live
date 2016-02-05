#   Copyright (C) 2015 Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import os

# Plugin Info
ADDON_ID = 'script.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC = REAL_SETTINGS.getAddonInfo('profile')
THUMB = (xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'images')) + '/' + 'icon.png')

def autostart():
    xbmc.log('script.pseudotv.live-Service: autostart')
    infoDialog("AutoStart Enabled")
    AUTOSTART_TIMER = [0,5,10,15,20]#in seconds
    xbmc.sleep(AUTOSTART_TIMER[int(REAL_SETTINGS.getSetting('timer_amount'))] * 1000)
    xbmc.executebuiltin('RunScript("' + ADDON_PATH + '/default.py' + '")')

def ComCHK():
    xbmc.log('script.pseudotv.live-Service: ComCHK')    
    # Community users are required to supply their gmail info in-order to use the community submission tool, SEE DISCLAIMER!! 
    # Community List is free, not a membership. Users do not have to signup for anything, they supply their own email information only required to participate in the exchange of channel configurations.
    # Submission tool uses emails to submit channel configurations, which are then added to a public (github) list: https://github.com/PseudoTV/PseudoTV_Lists, https://github.com/PseudoTV/PseudoTV_Playlists
    # Community lists includes: Youtube, Vimeo, RSS, Kodi Smartplaylists. Submissions take 24-48hrs to reflect on git list.
    # Community list also includes: LiveTV (legal feeds ONLY!), InternetTV (legal feeds ONLY!) and user installed Kodi repository plugins (see isKodiRepo, isPlugin).
    # Lists can not contain illegal pirated links since they consist of Youtube/Vimeo and RSS xml links.
    if REAL_SETTINGS.getSetting("Community_Enabled") == "true" and REAL_SETTINGS.getSetting("Gmail_User") != "email@gmail.com":
        if REAL_SETTINGS.getSetting("Community_Verified") != "1": 
            REAL_SETTINGS.setSetting("Community_Verified", "1")
            REAL_SETTINGS.setSetting("AT_Community","true")
            infoDialog("Community List Activated")
        xbmcgui.Window(10000).setProperty("Verified_Community", 'true')
    else:
        if REAL_SETTINGS.getSetting("Community_Verified") != "0": 
            REAL_SETTINGS.setSetting("Community_Verified", "0")
            REAL_SETTINGS.setSetting("AT_Community","false")
        xbmcgui.Window(10000).setProperty("Verified_Community", 'false')
   
def chkChanges():
    xbmc.log('script.pseudotv.live-Service: chkChanges')
    ComCHK()
    
    CURR_BUMPER = REAL_SETTINGS.getSetting('bumpers')
    try:
        CURR_BUMPER = REAL_SETTINGS.getSetting('Last_bumpers')
    except:
        REAL_SETTINGS.setSetting('Last_bumpers', CURR_BUMPER)
    LAST_BUMPER = REAL_SETTINGS.getSetting('Last_bumpers')
    
    if CURR_BUMPER != LAST_BUMPER:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_bumpers', CURR_BUMPER)
        
    CURR_COMMERCIALS = REAL_SETTINGS.getSetting('commercials')
    try:
        CURR_COMMERCIALS = REAL_SETTINGS.getSetting('Last_commercials')
    except:
        REAL_SETTINGS.setSetting('Last_commercials', CURR_COMMERCIALS)
    LAST_COMMERCIALS = REAL_SETTINGS.getSetting('Last_commercials')
    
    if CURR_COMMERCIALS != LAST_COMMERCIALS:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_commercials', CURR_COMMERCIALS)
        
    CURR_TRAILERS = REAL_SETTINGS.getSetting('trailers')
    try:
        CURR_TRAILERS = REAL_SETTINGS.getSetting('Last_trailers')
    except:
        REAL_SETTINGS.setSetting('Last_trailers', CURR_TRAILERS)
    LAST_TRAILERS = REAL_SETTINGS.getSetting('Last_trailers')
    
    if CURR_TRAILERS != LAST_TRAILERS:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_trailers', CURR_TRAILERS)
    
    CURR_ENHANCED_DATA = REAL_SETTINGS.getSetting('EnhancedGuideData')
    try:
        LAST_ENHANCED_DATA = REAL_SETTINGS.getSetting('Last_EnhancedGuideData')
    except:
        REAL_SETTINGS.setSetting('Last_EnhancedGuideData', CURR_ENHANCED_DATA)
    LAST_ENHANCED_DATA = REAL_SETTINGS.getSetting('Last_EnhancedGuideData')
    
    if CURR_ENHANCED_DATA != LAST_ENHANCED_DATA:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_EnhancedGuideData', CURR_ENHANCED_DATA)
        
    CURR_MEDIA_LIMIT = REAL_SETTINGS.getSetting('MEDIA_LIMIT')
    try:
        LAST_MEDIA_LIMIT = REAL_SETTINGS.getSetting('Last_MEDIA_LIMIT')
    except:
        REAL_SETTINGS.setSetting('Last_MEDIA_LIMIT', CURR_MEDIA_LIMIT)
    LAST_MEDIA_LIMIT = REAL_SETTINGS.getSetting('Last_MEDIA_LIMIT')
    
    if CURR_MEDIA_LIMIT != LAST_MEDIA_LIMIT:
        REAL_SETTINGS.setSetting('ForceChannelReset', "true")
        REAL_SETTINGS.setSetting('Last_MEDIA_LIMIT', CURR_MEDIA_LIMIT)
           
#Service           
if xbmc.getCondVisibility('Window.IsActive(addonsettings)') != True:
    chkChanges()
    if REAL_SETTINGS.getSetting("Auto_Start") == "true":
        autostart()
    
monitor = xbmc.Monitor()
#settings monitor class causes severe performance issues, resorted to while loop
hasSomethingChanged = False
while not monitor.abortRequested():
    # Sleep/wait for abort for 10 seconds
    if monitor.waitForAbort(10):
        # Abort was requested while waiting. We should exit
        break
        
    if xbmcgui.Window(10000).getProperty("PseudoTVRunning") != "True":
        if xbmc.getCondVisibility('Window.IsActive(addonsettings)') == True:
            hasSomethingChanged = True
        if hasSomethingChanged == True:
            hasSomethingChanged = False
            chkChanges()