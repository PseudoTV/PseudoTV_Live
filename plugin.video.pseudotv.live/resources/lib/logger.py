#   Copyright (C) 2026 Lunatixz
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
from kodi_six  import xbmc, xbmcaddon
from constants import *

def log(event, level=xbmc.LOGDEBUG):
    """
    Logs an event or message using Kodi's logging system.

    This function is designed to capture and log debug events based on the specified log level. 
    If debugging is enabled or the log level is critical (e.g., errors), the event will be 
    recorded in Kodi's log file. Additionally, it stores events in a custom debug window property 
    for debugging purposes.

    Args:
        event (str): The message or event to log.
        level (int, optional): The log level (default is xbmc.LOGDEBUG). Supported levels:
            - xbmc.LOGDEBUG: Debug messages (low priority).
            - xbmc.LOGINFO: Informational messages.
            - xbmc.LOGWARNING: Warnings.
            - xbmc.LOGERROR: Errors.
            - xbmc.LOGFATAL: Fatal errors.

    Behavior:
        - Logs the event if debugging is enabled or if the log level is above the configured threshold.
        - Appends a traceback for error-level logs (level >= xbmc.LOGERROR).
        - Formats the log message with the add-on ID and version for context.
        - Stores the log entry in the global debug window property for later retrieval if debugging is enabled.

    Example Usage:
        log("This is a debug message", xbmc.LOGDEBUG)
        log("An error occurred", xbmc.LOGERROR)

    Notes:
        - The `REAL_SETTINGS.getSetting('Debug_Enable')` setting determines whether to log debug-level messages.
        - The log entries are stored in a JSON object with timestamps and log levels for easy parsing.

    Returns:
        None
    """
    ADDON_ID      = 'plugin.video.pseudotv.live'
    REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
    ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
    if REAL_SETTINGS.getSetting('Debug_Enable') == 'true' or level >= 3:
        DEBUG_NAMES  = {0: 'LOGDEBUG', 1: 'LOGINFO', 2: 'LOGWARNING', 3: 'LOGERROR', 4: 'LOGFATAL'}
        DEBUG_LEVELS = {0: xbmc.LOGDEBUG, 1: xbmc.LOGINFO, 2: xbmc.LOGWARNING, 3: xbmc.LOGERROR, 4: xbmc.LOGFATAL}
        DEBUG_LEVEL  = DEBUG_LEVELS[int((REAL_SETTINGS.getSetting('Debug_Level') or "3"))]
        if level >= 3: event = '%s\n%s' % (event, traceback.format_exc())
        event = '%s-%s-%s' % (ADDON_ID, ADDON_VERSION, event)
        if level >= DEBUG_LEVEL:
            xbmc.log(event, level)
            