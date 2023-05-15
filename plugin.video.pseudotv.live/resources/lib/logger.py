#   Copyright (C) 2023 Lunatixz
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
#
# -*- coding: utf-8 -*-
import traceback
from kodi_six    import xbmc, xbmcaddon

#info
ADDON_ID            = 'plugin.video.pseudotv.live'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
LANGUAGE            = REAL_SETTINGS.getLocalizedString

#variables
DEBUG_ENABLED       = REAL_SETTINGS.getSetting('Enable_Debugging').lower() == 'true'
DEBUG_LEVELS        = {0:xbmc.LOGDEBUG,1:xbmc.LOGINFO,2:xbmc.LOGWARNING,3:xbmc.LOGERROR}
DEBUG_LEVEL         = DEBUG_LEVELS[int((REAL_SETTINGS.getSetting('Debugging_Level') or "1"))]
DEBUG_CACHE         = REAL_SETTINGS.getSetting('Disable_Cache').lower() == 'true'
DEBUG_CACHE         = (DEBUG_ENABLED & DEBUG_CACHE) #Only enable DEBUG_CACHE when DEBUG_ENABLED

def log(event, level=xbmc.LOGDEBUG):
    if not DEBUG_ENABLED and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: event = '%s\n%s'%(event,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,event),level)
  