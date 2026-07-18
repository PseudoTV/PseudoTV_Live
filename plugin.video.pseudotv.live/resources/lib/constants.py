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

import os, sys, re, struct
import json, pickle, platform
import random, base64, binascii, hashlib, heapq, zlib
import time, datetime, calendar, sqlite3
import requests, traceback, threading
import codecs, shutil, errno, copy

from functools             import partial, reduce, update_wrapper, wraps
from six.moves             import urllib 
from contextlib            import contextmanager, closing
from collections           import Counter, OrderedDict, defaultdict, deque
from ast                   import literal_eval
from io                    import BytesIO
from threading             import Lock, RLock, Thread, Event, Timer, current_thread
from xml.dom.minidom       import parse, Document
from xml.etree.ElementTree import ElementTree, Element, SubElement, XMLParser, fromstring, parse as ETparse
from typing                import Dict, List, Union, Optional, Any
from kodi_six              import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from socket                import gethostbyname, gethostname
from itertools             import cycle, chain, zip_longest, islice, repeat, count
from xml.sax.saxutils      import escape, unescape
from operator              import itemgetter
from math                  import ceil, floor, sqrt
from requests.adapters     import HTTPAdapter, Retry
from concurrent.futures    import ThreadPoolExecutor, as_completed

import pyqrcode

from uuid                import uuid1, uuid4, UUID
from infotagger.listitem import ListItemInfoTag


# =============================================================================
# Addon Identity
# =============================================================================
ADDON_ID            = 'plugin.video.pseudotv.live'          # Unique Kodi addon identifier
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)          # Raw xbmcaddon handle for addon settings
LANGUAGE            = REAL_SETTINGS.getLocalizedString      # Localized string lookup function
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')    # Human-readable addon name
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version') # Semver version string
ICON                = REAL_SETTINGS.getAddonInfo('icon')    # Addon icon path
FANART              = REAL_SETTINGS.getAddonInfo('fanart')  # Addon fanart path
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile') # User profile directory (special://)
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')    # Addon installation directory
ADDON_AUTHOR        = REAL_SETTINGS.getAddonInfo('author')  # Addon author name
ADDON_BRANCH        = 'master' if 'nightly' not in ADDON_VERSION else 'nightly'
ADDON_URL           = f'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/{ADDON_BRANCH}/plugin.video.pseudotv.live/addon.xml'
CHANGELOG_URL       = f'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/{ADDON_BRANCH}/plugin.video.pseudotv.live/changelog.txt'

# =============================================================================
# Kodi API References
# =============================================================================
PLAYER = xbmc.Player   # Kodi Player class reference (for instantiation)
_MONITOR_INSTANCE: Optional[xbmc.Monitor] = None

def MONITOR() -> xbmc.Monitor:
    """Singleton xbmc.Monitor — Kodi only allows one per process."""
    global _MONITOR_INSTANCE
    if _MONITOR_INSTANCE is None:
        _MONITOR_INSTANCE = xbmc.Monitor()
    return _MONITOR_INSTANCE

def _getTotalMEM() -> float:
    try:
        raw = xbmc.getInfoLabel('System.Memory')
        num = float("".join(c for c in raw if c.isdigit() or c == '.'))
        return num / 1024 if 'gb' in raw.lower() else num
    except Exception:
        return 4.0

def _getFreeMEM() -> int:
    try:
        raw_mem = xbmc.getInfoLabel('System.FreeMemory')
        return int("".join(c for c in raw_mem if c.isdigit()))
    except Exception:
        return 1024
# =============================================================================
# Performance & Threading
# =============================================================================

TOTAL_RAM_GB        = _getTotalMEM()
IS_CONSTRAINED_SOC  = TOTAL_RAM_GB <= 3.5
CPU_COUNT           = os.cpu_count() or 1                   # Number of CPU cores
if IS_CONSTRAINED_SOC:                                      # SoC Mode: Cap threads strictly to core count to protect limited RAM
    CPU_CYCLE      = 0.016
    THREAD_WORKERS = min(4, CPU_COUNT)
    QUEUE_CHUNK    = 8
    BATCH_SIZE     = 4
    MAX_CACHE_SIZE = 5000
else:                                                       # High-Performance Mode: Scale smoothly up to 32 threads
    CPU_CYCLE      = 0.016 if CPU_COUNT < 4 else 0.008      # Minimum sleep interval (~60Hz) Faster polling loops on multi-core systems
    THREAD_WORKERS = min(32, CPU_COUNT * 2)                 # Max thread pool workers (capped at 32) 2 threads per core, scaling smoothly up to a maximum of 32
    QUEUE_CHUNK    = max(4, 32 // CPU_COUNT)                # Queue Chunking: High-core machines grab smaller, nimbler chunks to avoid lock contention; Low-core machines grab larger chunks to minimize the overhead of fetching. 
    BATCH_SIZE     = 128 // QUEUE_CHUNK                     # Batch size for parallel operations Fewer cores run small, conservative batches; higher cores run larger parallel bursts.
    MAX_CACHE_SIZE = 1000 * CPU_COUNT                       # LRU cache Scale with available RAM/cores
    
# =============================================================================
# Service Timing (all values in seconds)
# =============================================================================
DISCOVERY_TIMER     = 60     # Zeroconf network discovery broadcast interval
DISCOVER_INTERVAL   = 30     # Time between discovery scans
SERVICE_INTERVAL    = 5.0    # Main service loop tick interval
TASK_INTERVAL       = 30.0   # Background task runner tick interval
SUSPEND_INTERVAL    = 2.5    # Pause/suspend polling interval
MIN_EPG_DURATION    = 10800  # Minimum EPG guide duration (3 hours in seconds)
TIMEOUT_EXECUTOR    = 1800   # Single executor task timeout (30 min)
TIMEOUT_EXECUTORS   = 300    # Total executor shutdown timeout (5 min)
ONNEXT_TIMER        = 15     # OnNext notification display duration (seconds)
DEBUG_TIMEOUT       = 900    # Debug log retention timeout (15 min)

# =============================================================================
# User-configurable Settings (read from addon settings)
# =============================================================================
MIN_GUIDEDAYS       = int((REAL_SETTINGS.getSetting('Min_Days')  or "1"))  # Minimum EPG guide days to fetch
MAX_GUIDEDAYS       = int((REAL_SETTINGS.getSetting('Max_Days')  or "3"))  # Maximum EPG guide days to fetch
OSD_TIMER           = int((REAL_SETTINGS.getSetting('OSD_Timer') or "5"))  # On-screen display timeout

# =============================================================================
# Date/Time Format Strings
# =============================================================================
DTFORMAT            = '%Y%m%d%H%M%S'        # Compact datetime (20090405231604)
DTZFORMAT           = '%Y%m%d%H%M%S +%z'    # Compact datetime with timezone
DTJSONFORMAT        = '%Y-%m-%d %H:%M:%S'   # ISO-like format for JSON serialization
BACKUP_TIME_FORMAT  = '%Y-%m-%d %I:%M %p'   # Human-readable backup timestamp

# =============================================================================
# File Locking
# =============================================================================
LOCK_MAX_FILE_TIMEOUT = 15   # Max seconds to wait for file lock acquisition
LOCK_MAX_FILE_DELAY   = 0.5  # Delay between file lock retry attempts

# =============================================================================
# UI Timing & Limits
# =============================================================================
LANG                = 'en'   # Default language (todo: parse kodi region settings)
DEFAULT_ENCODING    = "utf-8"
PROMPT_DELAY        = 4      # Dialog prompt auto-close delay (seconds)
AUTOCLOSE_DELAY     = 300    # Auto-close timeout for dialogs (5 minutes)
SELECT_DELAY        = 900    # Selection dialog timeout (15 minutes)
RADIO_ITEM_LIMIT    = 250    # Maximum radio/music items per channel
CHANNEL_LIMIT       = 999    # Maximum number of channels allowed
AUTOTUNE_CHANNEL_LIMIT = 25  # Max channels per autotune category
AUTOTUNE_CHANNEL_DEFAULT = 2 # Default channel count for autotune
FILLER_LIMIT        = 250    # Maximum filler items per channel
M3U_REFRESH         = 15     # M3U file refresh check interval (seconds)
M3U_INTERVAL        = 30     # M3U full reload interval (seconds)
M3U_TIMEOUT         = 30     # M3U network request timeout (seconds)
HTTP_TIMEOUT        = 30     # HTTP server file serving timeout (seconds)
LOGO_REFRESH        = 900

# =============================================================================
# Media Type Classifications
# =============================================================================
ROLL_TYPES          = ['Fillers',     # Genre labels that trigger filler roll detection
                       'Pre-Roll',
                       'Post-Roll']

AUTOTUNE_TYPES      = ["Playlists",   # Autotune source categories (order matches UI)
                       "TV Networks",
                       "TV Shows",
                       "TV Genres",
                       "Movie Genres",
                       "Movie Studios",
                       "Mixed Genres",
                       "Music Genres",
                       "Mixed Video",
                       "Mixed Music",
                       "Recommended",
                       "Services"]

GROUP_TYPES         = ['Addon',       # Channel grouping categories (includes autotune types)
                       'Custom',
                       'Directory', 
                       'TV', 
                       'Movies', 
                       'Music', 
                       'Miscellaneous', 
                       'PVR', 
                       'Plugin', 
                       'Radio', 
                       'Smartplaylist', 
                       'UPNP', 
                       'IPTV'] + AUTOTUNE_TYPES

DB_TYPES            = ["videodb://",  # Kodi library database URL prefixes
                       "musicdb://",
                       "library://",
                       "special://"]

WEB_TYPES           = ["http",        # Remote/web URL prefixes
                       "ftp://",
                       "pvr://"
                       "upnp://",]

VFS_TYPES           = ["plugin://",   # Kodi virtual filesystem URL prefixes
                       "pvr://",
                       "resource://",
                       "special://home/addons/resource"]
                       
TV_TYPES            = ['episode',     # Kodi media types for TV content
                       'episodes',
                       'tvshow',
                       'tvshows']
                       
MOVIE_TYPES         = ['movie',       # Kodi media types for movie content
                       'movies']
                       
MUSIC_TYPES         = ['songs',       # Kodi media types for music content
                       'albums',
                       'artists',
                       'music']

# =============================================================================
# Playlist File Extensions
# =============================================================================
KODI_PLAYLISTS      = [".xsp",        # Kodi smart playlist extensions
                       ".xml"]        # Kodi playlist node
                                           
BASIC_PLAYLISTS     = [".cue",        # Standard playlist file extensions
                       ".m3u",
                       ".m3u8",
                       ".strm",
                       ".pls",
                       ".wpl"] 

# =============================================================================
# HTML Entity Encoding
# =============================================================================
HTML_ESCAPE         = {"&": "&amp;",
                       '"': "&quot;",
                       "'": "&apos;",
                       ">": "&gt;",
                       "<": "&lt;"}    

# =============================================================================
# Channel Builder Types
# =============================================================================
IGNORE_CHTYPE       = ['TV Shows',    # Channel types excluded from certain build operations
                       'Mixed Video',
                       'Mixed Music',
                       'Recommended',
                       'Services',
                       'Music Genres']
                 
MOVIE_CHTYPE        = ["Movie Genres",# Channel types that contain movie content
                       "Movie Studios"]
                 
TV_CHTYPE           = ["TV Networks", # Channel types that contain TV content
                       "TV Genres",
                       "Mixed Genre"]

# Content type mapping for PVR On Demand (Kodi v23+)
# TODO: https://github.com/xbmc/xbmc/pull/25711
# MOVIE_CHTYPE channels → "movie" content type
# TV_CHTYPE channels    → "tvshow" content type
# radio=True channels   → "music" content type

# =============================================================================
# Plugin URL Templates (mode= parameter dispatches to handler)
# =============================================================================
TV_URL              = 'plugin://{addon}/?mode=tv&name={name}&chid={chid}.pvr'
RESUME_URL          = 'plugin://{addon}/?mode=resume&name={name}&chid={chid}.pvr'
RADIO_URL           = 'plugin://{addon}/?mode=radio&name={name}&chid={chid}&radio={radio}&vid={vid}.pvr'
LIVE_URL            = 'plugin://{addon}/?mode=live&name={name}&chid={chid}&vid={vid}&now={now}&start={start}&duration={duration}&stop={stop}.pvr'
BROADCAST_URL       = 'plugin://{addon}/?mode=broadcast&name={name}&chid={chid}&vid={vid}.pvr'
VOD_URL             = 'plugin://{addon}/?mode=vod&title={title}&chid={chid}&vid={vid}&name={name}.pvr'
DVR_URL             = 'plugin://{addon}/?mode=dvr&title={title}&chid={chid}&vid={vid}&seek={seek}&duration={duration}.pvr'

# =============================================================================
# PVR / IPTV Simple Client
# =============================================================================
PTVL_REPO           = 'repository.pseudotv'              # Kodi repository for PTVL
PVR_CLIENT_ID       = 'pvr.iptvsimple'                   # IPTV Simple Client addon ID
PVR_CLIENT_NAME     = 'IPTV Simple Client'               # Human-readable PVR client name
PVR_CLIENT_LOC      = 'special://profile/addon_data/%s'%(PVR_CLIENT_ID) # PVR addon data dir
PVR_SETTINGS_XML    = os.path.join(PVR_CLIENT_LOC,'settings.xml')        # PVR settings file
# ENABLE_ON_DEMAND  = True                               # TODO: Route VOD content to PVR On Demand API (Kodi v23+)

# =============================================================================
# Documentation Files
# =============================================================================
README_FLE    = os.path.join(ADDON_PATH,'README.md')
CHANGELOG_FLE = os.path.join(ADDON_PATH,'changelog.txt')
LICENSE_FLE   = os.path.join(ADDON_PATH,'LICENSE')

# =============================================================================
# Core Data File Names
# =============================================================================
MANAGERFLE          = 'manager.html'    # Channel manager HTML UI
M3UFLE              = 'pseudotv.m3u'    # M3U playlist export
XMLTVFLE            = 'pseudotv.xml'    # XMLTV EPG export
GENREFLE            = 'genres.xml'      # Genre mapping definitions
BONJOURFLE          = 'bonjour.json'    # Bonjour/Zeroconf service cache
LOGSFLE             = 'logs.json'       # Diagnostic log export
SERVERFLE           = 'servers.json'    # Multiroom server registry
CHANNELFLE          = 'channels.json'   # Channel configuration database
LIBRARYFLE          = 'library.json'    # Library content index
PVRFLE              = 'pvr.json'        # PVR sync status
TVGROUPFLE          = 'tv_groups.xml'    # TV channel group mappings
RADIOGROUPFLE       = 'radio_groups.xml' # Radio channel group mappings
PROVIDERFLE         = 'providers.xml'   # Content provider definitions

# =============================================================================
# Property / Setting Keys (used with Kodi Properties and settings cache)
# =============================================================================
CHANNEL_KEY         = 'Channels'                    # Root property key for channel data
CHANNELBACKUP_KEY   = f'{CHANNEL_KEY}.Backup'       # Backup snapshot key
CHANNELCHANGED_KEY  = f'{CHANNEL_KEY}.Changed'      # Dirty flag for pending changes
CHANNELLATEST_KEY   = f'{CHANNEL_KEY}.Latest'       # Latest build timestamp
CHANNELAUTOTUNE_KEY = f'{CHANNEL_KEY}.Autotune'     # Autotune status key

def getChannelKey():
    """Return the active channel key based on Enable_Autotune setting."""
    try: return CHANNELAUTOTUNE_KEY if REAL_SETTINGS.getSettingBool('Enable_Autotune') else CHANNEL_KEY
    except Exception: return CHANNEL_KEY
RESUME_INDEX        = 'Resume.Filelist.Index'       # Playback resume position index

# =============================================================================
# Supported File Extensions (queried from Kodi at import time)
# =============================================================================
VIDEO_EXTS          = xbmc.getSupportedMedia('video').split('|')[:-1]  # Video file extensions
MUSIC_EXTS          = xbmc.getSupportedMedia('music').split('|')[:-1]  # Music file extensions
IMAGE_EXTS          = xbmc.getSupportedMedia('picture').split('|')[:-1] # Image file extensions
IMG_EXTS            = ['.png','.jpg','.gif']  # Common image extensions for downloads
TEXTURES            = 'Textures.xbt'         # Kodi texture atlas bundle

# =============================================================================
# Directory Paths (relative to addon installation)
# =============================================================================
REMOTE_LOC          = os.path.join(ADDON_PATH,'remotes')                               # Remote/default config files
IMAGE_LOC           = os.path.join(ADDON_PATH,'resources','images')                    # Bundled images
MEDIA_LOC           = os.path.join(ADDON_PATH,'resources','skins','default','media')   # Skin media assets
SFX_LOC             = os.path.join(MEDIA_LOC,'sfx')                                    # Sound effects
TEMP_LOC            = os.path.join(SETTINGS_LOC,'temp')                                # Temporary file cache
BACKUP_LOC          = os.path.join(SETTINGS_LOC,'backup')                              # User backup directory

# =============================================================================
# Resolved File Paths
# =============================================================================
CHANNEL_EXPORT_FLE  = os.path.join(BACKUP_LOC,CHANNELFLE)                                    # Channel export path
CHANNEL_BACKUP_FLE  = os.path.join(BACKUP_LOC,'%s.json'%(CHANNELBACKUP_KEY.lower()))         # Channel backup path
SETTINGS_FLE        = os.path.join(SETTINGS_LOC,'settings.xml')                              # Kodi settings override
CACHE_FLE           = os.path.join(SETTINGS_LOC,'cache.db')                                  # SQLite cache database
YOUTUBE_COOKIES     = os.path.join(SETTINGS_LOC,'www.youtube.com_cookies.txt')               # YouTube auth cookies

# =============================================================================
# Sound Effects
# =============================================================================
BING_WAV            = os.path.join(SFX_LOC,'bing.wav')   # Notification alert sound
NOTE_WAV            = os.path.join(SFX_LOC,'notify.wav') # Subtle notification sound

# =============================================================================
# Remote/Default Config Files (shipped with addon)
# =============================================================================
M3UFLE_DEFAULT      = os.path.join(REMOTE_LOC,'m3u.json')          # M3U item template
SEASONS             = os.path.join(REMOTE_LOC,'seasons.json')      # Seasonal content definitions
HOLIDAYS            = os.path.join(REMOTE_LOC,'holidays.json')     # Holiday content definitions
GROUPFLE_DEFAULT    = os.path.join(REMOTE_LOC,'groups.xml')        # Default channel groups
MANAGERPATH         = os.path.join(REMOTE_LOC,MANAGERFLE)          # Default manager HTML
CHANNELFLE_DEFAULT  = os.path.join(REMOTE_LOC,CHANNELFLE)          # Default channel config
SERVERFLE_DEFAULT   = os.path.join(REMOTE_LOC,SERVERFLE)           # Default server config
LIBRARYFLE_DEFAULT  = os.path.join(REMOTE_LOC,LIBRARYFLE)          # Default library config
GENREFLE_DEFAULT    = os.path.join(REMOTE_LOC,GENREFLE)            # Default genre mappings
PROVIDERFLE_DEFAULT = os.path.join(REMOTE_LOC,PROVIDERFLE)         # Default provider config
INSTANCEFLE_DEFAULT = os.path.join(REMOTE_LOC,'instance-settings-1.xml') # Default instance settings

# =============================================================================
# UI Colors (ARGB hex or named)
# =============================================================================
PRIMARY_BACKGROUND        = 'FF11375C'   # Primary UI background color
SECONDARY_BACKGROUND      = '334F4F9E'   # Secondary/overlay background (semi-transparent)
DIALOG_TINT               = 'FF181B1E'   # Dialog window tint color
BUTTON_FOCUS              = 'FF2866A4'   # Focused button highlight color
SELECTED                  = 'FF5BE5EE'   # Selected item highlight color

COLOR_BACKGROUND          = '01416b'     # Default image placeholder background
COLOR_TEXT                = 'FFFFFF'     # Default text color (white)
COLOR_UNAVAILABLE_CHANNEL = 'dimgray'    # Channel status: unavailable
COLOR_AVAILABLE_CHANNEL   = 'white'      # Channel status: available
COLOR_LOCKED_CHANNEL      = 'orange'     # Channel status: locked by rule
COLOR_WARNING_CHANNEL     = 'red'        # Channel status: error/warning
COLOR_NEW_CHANNEL         = 'green'      # Channel status: newly created
COLOR_RADIO_CHANNEL       = 'cyan'       # Channel type: radio/music
COLOR_FAVORITE_CHANNEL    = 'yellow'     # Channel status: user favorite

# =============================================================================
# External URLs
# =============================================================================
URL_WIKI                  = 'https://github.com/PseudoTV/PseudoTV_Live/wiki'
URL_SUPPORT               = 'https://forum.kodi.tv/showthread.php?tid=346803'
URL_WIN_BONJOUR           = 'https://support.apple.com/en-us/106380'
URL_README                = 'https://github.com/PseudoTV/PseudoTV_Live/blob/master/plugin.video.pseudotv.live/README.md'

# =============================================================================
# Bundled Images / Media Assets
# =============================================================================
LOGO                = os.path.join(MEDIA_LOC,'wlogo.png')          # Default addon logo
LOGO_DIM            = os.path.join(MEDIA_LOC,'dimlogo.png')        # Dimmed logo for overlays
LOGO_COLOR          = os.path.join(MEDIA_LOC,'logo.png')           # Color logo for notifications
FANART_COLOR        = os.path.join(MEDIA_LOC,'fanart.jpg')         # Default fanart image
LOGO_POSTER         = os.path.join(MEDIA_LOC,'poster.png')         # Poster artwork
LOGO_LANDSCAPE      = os.path.join(MEDIA_LOC,'landscape.png')      # Landscape artwork
LOGO_SEASONAL       = os.path.join(MEDIA_LOC,'Seasonal.png')       # Seasonal/themed logo
ICON_WEB            = os.path.join(MEDIA_LOC,'logo.ico')           # Web favicon
LOGO_HOST           = 'http://github.com/PseudoTV/PseudoTV_Live/blob/master/plugin.video.pseudotv.live/resources/skins/default/media/logo.png?raw=true'

# =============================================================================
# Skin XML Dialog Filenames
# =============================================================================
BUSY_XML        = '%s.busy.xml'%(ADDON_ID)          # Busy spinner dialog
ONNEXT_XML      = '%s.onnext.xml'%(ADDON_ID)        # OnNext notification dialog
REPLAY_XML      = '%s.restart.xml'%(ADDON_ID)       # Replay/restart prompt dialog
BACKGROUND_XML  = '%s.background.xml'%(ADDON_ID)    # Background dialog
MANAGER_XML     = '%s.manager.xml'%(ADDON_ID)       # Channel manager dialog
OVERLAYTOOL_XML = '%s.overlaytool.xml'%(ADDON_ID)   # Overlay tool dialog
DIALOG_SELECT   = '%s.dialogselect.xml'%(ADDON_ID)  # Custom select dialog

# =============================================================================
# Kodi Action IDs (https://github.com/xbmc/xbmc/blob/master/xbmc/addons/kodi-dev-kit/include/kodi/c-api/gui/input/action_ids.h)
# =============================================================================
ACTION_MOVE_LEFT     = 1
ACTION_MOVE_RIGHT    = 2
ACTION_MOVE_UP       = 3
ACTION_MOVE_DOWN     = 4
ACTION_INVALID       = 999
ACTION_SELECT_ITEM   = [7,135]
ACTION_PREVIOUS_MENU = [92,10,110,521,ACTION_SELECT_ITEM]

# =============================================================================
# Rules System Action IDs
# Actions are dispatched by the Builder/Player/Overlay via runActions().
# Each constant defines a lifecycle hook where rule callbacks execute.
# =============================================================================
RULES_VERSION                              = 0.1  # Rules schema version

# --- Channel Builder Actions ---
RULES_ACTION_CHANNEL_CITEM                 = 1   # Persistent channel item modifications
RULES_ACTION_CHANNEL_START                 = 2   # Channel build start (set channel globals)
RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE   = 3   # Pre-build: initial file array (build bypass check)
RULES_ACTION_CHANNEL_BUILD_PATH            = 4   # Pre-parse: alter directory path before scanning
RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE    = 5   # Mid-build: file list before fillers/interleave
RULES_ACTION_CHANNEL_BUILD_FILELIST_POST   = 6   # Post-build: file list after fillers applied
RULES_ACTION_CHANNEL_BUILD_TIME_PRE        = 7   # Pre-schedule: file list before time-slot assignment
RULES_ACTION_CHANNEL_BUILD_TIME_POST       = 8   # Post-schedule: file list after time-slot assignment
RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST  = 9   # Post-build: file array before interleave/fillers
RULES_ACTION_CHANNEL_STOP                  = 10  # Channel build complete (restore channel globals)
RULES_ACTION_CHANNEL_TEMP_CITEM            = 11  # Temporary channel item modifications (rule injection)
RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN = 12  # Final file list return point
RULES_ACTION_CHANNEL_REQUEST_FILELIST_PRE  = 13  # Pre-request: file list before external fetch
RULES_ACTION_CHANNEL_REQUEST_FILELIST_POST = 14  # Post-request: file list after external fetch

# --- Player Actions ---
RULES_ACTION_PLAYER_START  = 20  # Playback started
RULES_ACTION_PLAYER_CHANGE = 21  # Playback changed or ended
RULES_ACTION_PLAYER_STOP   = 22  # Playback stopped

# --- Overlay/Background Actions ---
RULES_ACTION_OVERLAY_OPEN  = 30  # Overlay window opened
RULES_ACTION_OVERLAY_CLOSE = 31  # Overlay window closed

# --- Playback Actions ---
RULES_ACTION_PLAYBACK_RESUME = 40  # Pre-resume: trigger resume to receive a FileList

# =============================================================================
# HTTP Headers
# =============================================================================
HEADER = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"}


# =============================================================================
# Logging
# =============================================================================
_LOG_THROTTLE  = {}  # {(event, level): (last_log_timestamp, skip_count)} - for throttled log dedup
_LOG_LAST_KEY  = None  # last (event, level) key that was logged - for consecutive duplicate detection
LOG_MAX_LENGTH = 500  # max characters for log message string (traceback excluded)
DEBUG_NAMES    = {0: 'LOGDEBUG', 1: 'LOGINFO', 2: 'LOGWARNING', 3: 'LOGERROR', 4: 'LOGFATAL'}

def LOG(event: Any, level: int = xbmc.LOGDEBUG, throttle: float = float(SERVICE_INTERVAL)):
    """Central logging function. Checks Debug_Enable and Debug_Level settings.
    When level >= 3 (LOGERROR), appends traceback.format_exc() to the message.
    When throttle > 0, consecutive identical (event, level) pairs are suppressed,
    then a 'Skipped N duplicate messages..' line is logged when the sequence ends."""
    global _LOG_LAST_KEY
    if REAL_SETTINGS.getSetting('Debug_Enable') == 'true' or level >= 3:
        DEBUG_LEVELS = {0: xbmc.LOGDEBUG, 1: xbmc.LOGINFO, 2: xbmc.LOGWARNING, 3: xbmc.LOGERROR, 4: xbmc.LOGFATAL}
        DEBUG_LEVEL  = DEBUG_LEVELS[int((REAL_SETTINGS.getSetting('Debug_Level') or "3"))]
        if len(str(event)) > LOG_MAX_LENGTH: event = '%s...[TRUNCATED]' % str(event)[:LOG_MAX_LENGTH]
        if level >= 3: event = '%s\n%s' % (event, traceback.format_exc())
        if throttle > 0:
            now  = time.time()
            key  = (event, level)
            last_time, skip_count = _LOG_THROTTLE.get(key, (0, 0))
            if (now - last_time) < throttle:
                _LOG_THROTTLE[key] = (last_time, skip_count + 1)
                return
            elif _LOG_LAST_KEY is not None and _LOG_LAST_KEY != key:
                prev_time, prev_skip = _LOG_THROTTLE.get(_LOG_LAST_KEY, (0, 0))
                if prev_skip > 0:
                    skip_msg = 'Skipped %d duplicate messages..' % (prev_skip)
                    if level >= DEBUG_LEVEL: xbmc.log(skip_msg, level)
            _LOG_THROTTLE[key] = (now, 0)
            _LOG_LAST_KEY = key
        event = '%s-%s-%s' % (ADDON_ID, ADDON_VERSION, event)
        if level >= DEBUG_LEVEL:
            xbmc.log(event, level)
