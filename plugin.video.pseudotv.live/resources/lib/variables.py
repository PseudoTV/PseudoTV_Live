#   Copyright (C) 2024 Lunatixz
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

from constants import *

#variables
USER_LOC            = REAL_SETTINGS.getSetting('User_Folder')
DEBUG_ENABLED       = REAL_SETTINGS.getSetting('Enable_Debugging').lower() == 'true'
DEBUG_LEVELS        = {0:xbmc.LOGDEBUG,1:xbmc.LOGINFO,2:xbmc.LOGWARNING,3:xbmc.LOGERROR}
DEBUG_LEVEL         = DEBUG_LEVELS[int((REAL_SETTINGS.getSetting('Debugging_Level') or "1"))]
DEBUG_CACHE_ENABLED = REAL_SETTINGS.getSetting('Disable_Cache').lower() == 'true'
DEBUG_CACHE         = (DEBUG_ENABLED & DEBUG_CACHE_ENABLED) #Only enable DEBUG_CACHE when DEBUG_ENABLED

PAGE_LIMIT          = int((REAL_SETTINGS.getSetting('Page_Limit')  or "25"))
MIN_GUIDEDAYS       = int((REAL_SETTINGS.getSetting('Min_Days')    or "1"))
MAX_GUIDEDAYS       = int((REAL_SETTINGS.getSetting('Max_Days')    or "3"))
EPG_ARTWORK         = int((REAL_SETTINGS.getSetting('EPG_Artwork') or "0"))

#file paths
PLS_LOC             = os.path.join(USER_LOC,'playlists')
LOGO_LOC            = os.path.join(USER_LOC,'logos')
TEMP_LOC            = os.path.join(USER_LOC,'temp')
M3UFLEPATH          = os.path.join(USER_LOC,M3UFLE)
XMLTVFLEPATH        = os.path.join(USER_LOC,XMLTVFLE)
GENREFLEPATH        = os.path.join(USER_LOC,GENREFLE)
PROVIDERFLEPATH     = os.path.join(USER_LOC,PROVIDERFLE)
CHANNELFLEPATH      = os.path.join(USER_LOC,CHANNELFLE)
LIBRARYFLEPATH      = os.path.join(USER_LOC,LIBRARYFLE)