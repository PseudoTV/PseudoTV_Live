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
import os, sys, time, urllib

from resources.lib.Globals import *
from resources.lib.utils import *

def showInfo(addonID=None, type='changelog'):
    log('utilities: showInfo')
    try:
        if addonID:
            ADDON = xbmcaddon.Addon(addonID)
        else: 
            ADDON = xbmcaddon.Addon(ADDONID)
        if type == 'changelog':
            title = "PseudoTV Live - Changelog"
            f = open(ADDON.getAddonInfo('changelog'))
        elif type == 'readme':
            title = "PseudoTV Live - Readme"
            f = open(os.path.join(ADDON_PATH,'README.md'))
        elif type == 'disclaimer':
            title = "PseudoTV Live - Privacy Disclaimer"
            f = open(os.path.join(ADDON_PATH,'disclaimer'))
        elif type == 'settings':
            title = "PseudoTV Live - User Settings"
            f = open(os.path.join(ADDON_PATH,'settings'))
        text = f.read()
        f.close()
        textViewer(text, title)
    except:
        pass      
        
def DeleteSettings2():
    log('utilities: DeleteSettings2')
    if xbmcvfs.exists(SETTINGS_FLE):
        if yesnoDialog("Delete Current Channel Configurations?"):
            try:
                REAL_SETTINGS.setSetting("CurrentChannel","1")
                xbmcvfs.delete(SETTINGS_FLE)
                infoDialog("Channel Configurations Cleared")
            except:
                pass
                
    # Return to PTVL Settings
    REAL_SETTINGS.openSettings()
    
def addBypass():
    chnlst = ChannelList()
    chnlst.fillPluginList()
    BYPASS_LST = matchMselect(chnlst.pluginPathList, mselectDialog(chnlst.pluginNameList, header='Disable Seeking for specified Plugins'))
    REAL_SETTINGS.setSetting("BYPASS_LST",str(BYPASS_LST))
    
def ClearTempKey():
    log('utilities: ClearTempKey')
    
def ClearChanFavorites():
    log('utilities: ClearChanFavorites')
    REAL_SETTINGS.setSetting("FavChanLst","0")
    infoDialog("Channel Favourites Cleared")
    # Return to PTVL Settings
    REAL_SETTINGS.openSettings()
                   
def showChtype():
    log('utilities: showChtype')
    ChtypeLst = ['General','Custom Playlist','TV Network','Movie Studio','TV Genre','Movie Genre','Mixed Genre','TV Show','Directory','LiveTV','InternetTV','Youtube','RSS','Music','Music Videos','Exclusive','Plugin','UPNP']
    select = selectDialog(ChtypeLst, 'Select Channel Type')
    if select != -1:
        help(ChtypeLst[select])

if sys.argv[1] == '-SimpleDownloader':
    xbmcaddon.Addon(id='script.module.simple.downloader').openSettings()  
elif sys.argv[1] == '-showChangelog':
    showInfo(ADDON_ID, 'changelog') 
elif sys.argv[1] == '-showReadme':
    showInfo(ADDON_ID, 'readme') 
elif sys.argv[1] == '-showUserSettings':
    showInfo(ADDON_ID, 'settings') 
elif sys.argv[1] == '-showChtype':
    showChtype()
elif sys.argv[1] == '-showDisclaimer':
    showInfo(ADDON_ID, 'disclaimer') 
elif sys.argv[1] == '-DeleteSettings2':
    DeleteSettings2()
elif sys.argv[1] == '-backupSettings2':
    backupSettings2()
elif sys.argv[1] == '-restoreSettings2':
    restoreSettings2()
elif sys.argv[1] == '-purgeSettings2':
    purgeSettings2()
elif sys.argv[1] == '-repairSettings2':
    from resources.lib.Settings import *
    Setfun = Settings()
    Setfun.repairSettings()
elif sys.argv[1] == '-ClearTempKey':
    ClearTempKey()
elif sys.argv[1] == '-ClearChanFavorites':
    ClearChanFavorites()
elif sys.argv[1] == '-YTDownloader':
    xbmcaddon.Addon(id='script.module.youtube.dl').openSettings()  
elif sys.argv[1] == '-BYPASS_SEEK':
    addBypass()