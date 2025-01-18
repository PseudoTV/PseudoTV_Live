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

import json,traceback

from globals import *

def log(event, level=xbmc.LOGDEBUG):
    if REAL_SETTINGS.getSetting('Debug_Enable') == 'true' or level >= 3:
        DEBUG_NAMES  = {0:'LOGDEBUG',1:'LOGINFO',2:'LOGWARNING',3:'LOGERROR',4:'LOGFATAL'}
        DEBUG_LEVELS = {0:xbmc.LOGDEBUG,1:xbmc.LOGINFO,2:xbmc.LOGWARNING,3:xbmc.LOGERROR,4:xbmc.LOGFATAL}
        DEBUG_LEVEL  = DEBUG_LEVELS[int((REAL_SETTINGS.getSetting('Debug_Level') or "3"))]
        
        if level >= 3: event = '%s\n%s'%(event, traceback.format_exc())
        event = '%s-%s-%s'%(ADDON_ID, ADDON_VERSION, event)
        if level >= DEBUG_LEVEL:
            xbmc.log(event,level)
            try:    entries = json.loads(xbmcgui.Window(10000).getProperty('%s.debug.log'%(ADDON_ID))).get('DEBUG',{})
            except: entries = {}
            entries.setdefault(DEBUG_NAMES[DEBUG_LEVEL],[]).append('%s - %s: %s'%(datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT),DEBUG_NAMES[level],event))
            try: xbmcgui.Window(10000).setProperty('%s.debug.log'%(ADDON_ID),json.dumps({'DEBUG':entries}, indent=4))
            except: pass
            if not xbmcgui.Window(10000).getProperty('%s.has.debug'%(ADDON_ID)) == 'true': xbmcgui.Window(10000).setProperty('%s.has.debug'%(ADDON_ID),'true')
        