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

import os, xbmc, xbmcgui, xbmcaddon, xbmcvfs

# Plugin Info
ADDON_ID = 'script.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC = REAL_SETTINGS.getAddonInfo('profile')
THUMB = (xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'images')) + '/' + 'icon.png')
AUTOSTART_TIMER = [0,5,10,15,20][int(REAL_SETTINGS.getSetting('Auto_Start'))]

def handle_wait(time_to_wait,header='AutoStart',title='AutoStart',string=None): #*Thanks enen92
    dlg = xbmcgui.DialogProgress()
    dlg.create("PseudoTV Live", header)
    secs=0
    percent=0
    increment = int(100 / time_to_wait)
    cancelled = False
    while secs < time_to_wait:
        secs += 1
        percent = increment*secs
        secs_left = str((time_to_wait - secs))
        if not string:
            remaining_display = "in " + str(secs_left) + " seconds, Cancel?" 
        else:
            remaining_display = string
        dlg.update(percent,title,remaining_display)
        xbmc.sleep(1000)
        if (dlg.iscanceled()):
            cancelled = True
            break
    if cancelled == True:
        return False
    else:
        dlg.close()
        return True

if AUTOSTART_TIMER != 0:
    xbmc.log('script.pseudotv.live-Service: autostart')
    xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (ADDON_NAME, "AutoStart Enabled", AUTOSTART_TIMER * 1000, THUMB))
    if handle_wait(AUTOSTART_TIMER) == True:
        xbmc.executebuiltin('RunScript("' + ADDON_PATH + '/default.py' + '")')