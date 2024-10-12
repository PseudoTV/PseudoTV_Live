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
    if DEBUG_ENABLED or level >= 3:
        if level >= 3: event = '%s\n%s'%(event, traceback.format_exc())
        event = '%s-%s-%s'%(ADDON_ID, ADDON_VERSION, event)
        if level >= DEBUG_LEVEL:
            xbmc.log(event,level)
            try:    entries = json.loads(xbmcgui.Window(10000).getProperty('%s.debug.log'%(ADDON_NAME))).get('DEBUG',{})
            except: entries = {}
            entries.setdefault(DEBUG_NAMES[DEBUG_LEVEL],[]).append('%s - %s: %s'%(datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT),DEBUG_NAMES[level],event))
            xbmcgui.Window(10000).setProperty('%s.debug.log'%(ADDON_NAME),json.dumps({'DEBUG':entries}, indent=4))
        