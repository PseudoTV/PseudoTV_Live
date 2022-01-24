#   Copyright (C) 2022 Lunatixz
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
# -*- coding: utf-8 -*-

import time

from kodi_six               import xbmc, xbmcaddon
from resources.lib.kodi     import Properties

ADDON_ID      = 'plugin.video.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
DEBUG_ENABLED = REAL_SETTINGS.getSetting('Enable_Debugging') == "true"

def loadEvents():
    '''{
	 "events": {
		id: [{
			"event"    : "",
			"details"  : [],
			"timestamp": time.time,
			"level"    : xbmc.LOGDEBUG
	 	}]
	 }
    }'''
    return PROPERTIES.getPropertyDict('events')

def clearEvents():
    PROPERTIES.clearProperty('events')

def saveEvents(events):
    PROPERTIES.setPropertyDict('events',events)

def setChannelEvent(id, event, details=[], level=xbmc.LOGDEBUG):
    events = loadEvents()
    events.setdefault(id,[]).append({"event": event, "details": details, "timestamp": time.time(), "level": "%s"%(level)})
    saveEvents(events)
    
def getChannelEvents(id, level=None):
    events = loadEvents().get(id,[])
    if level: events = list(filter(lambda k:k['level'] == level,events))
    return events
    
def logit(label=None, level=None):
    def decorator(func):
        def decorated(*args, **kwargs):
            print('logit',args[1:],kwargs)
            
            # if level is None: 
            level = kwargs.get('level',xbmc.LOGDEBUG)
            details = []
            event   = '%s: %s'%(args[0].__class__.__name__, func.__name__)
            if label: '%s, %s'%(event,label)
                
            try:
                func(*args, **kwargs)
            except Exception as e:
                level=xbmc.LOGERROR
                if DEBUG_ENABLED: details.extend([kwargs,e,traceback.format_exc()])
                if kwargs.get('id') : setChannelEvent(kwargs.get('id'),event,details,level=level)
            if details: '%s, %s'%(event,details)
            xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,event),level)
        return decorated
    return decorator

