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
import pyqrcode, socket

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
from uuid                  import uuid1, uuid4, UUID
from infotagger.listitem   import ListItemInfoTag

# Shared reentrant lock for the guide/data classes (M3U, XMLTVS, Channels).
# The underlying SQLite cache already serializes DB writes in _Cache._lock, so
# these per-class locks only guard in-memory mutation. One shared lock reads
# clearer than a per-class RLock and still allows a class to call into another
# (e.g. XMLTVS -> m3u.delStation) reentrantly.
DATA_LOCK = RLock()

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
IS_CONSTRAINED_SOC  = TOTAL_RAM_GB <= 2.5
CPU_COUNT           = os.cpu_count() or 1                   # Number of CPU cores
if TOTAL_RAM_GB <= 2.5:                                      # Low-End SoC: Fire Stick, low-RAM boxes
    CPU_CYCLE      = 0.016
    THREAD_WORKERS = min(2, CPU_COUNT)
    QUEUE_CHUNK    = 8
    BATCH_SIZE     = 4
    MAX_CACHE_SIZE = 5000
elif TOTAL_RAM_GB <= 4.0:                                    # Mid-Range: Shield Pro, Apple TV
    CPU_CYCLE      = 0.016
    THREAD_WORKERS = min(4, CPU_COUNT)
    QUEUE_CHUNK    = max(4, 16 // CPU_COUNT)
    BATCH_SIZE     = 64 // QUEUE_CHUNK
    MAX_CACHE_SIZE = 8000
else:                                                        # High-Performance: Desktop
    CPU_CYCLE      = 0.016 if CPU_COUNT < 4 else 0.008
    THREAD_WORKERS = min(32, CPU_COUNT * 2)
    QUEUE_CHUNK    = max(4, 32 // CPU_COUNT)
    BATCH_SIZE     = 128 // QUEUE_CHUNK
    MAX_CACHE_SIZE = 1000 * CPU_COUNT
    
# =============================================================================
# Shared in-memory cache budget. ONE global number (GLOBAL_CACHE_MEM_MAX,
# chosen by available RAM / SoC) bounds the TOTAL memory all of the addon's
# in-memory caches may consume. Each cache is allotted a fraction of it; the
# fractions sum to <= 100% and a MemoryBudget singleton additionally refuses a
# stash when the combined usage would exceed the global cap. So no combination
# of caches (window-property mem cache, Properties LRU, M3U/XMLTV renders)
# can ever blow the budget.
# =============================================================================
GLOBAL_CACHE_MEM_MAX = (128 if IS_CONSTRAINED_SOC else 256 if TOTAL_RAM_GB <= 4.0 else 512) * 1024 * 1024
CACHE_MEM_MAX        = int(GLOBAL_CACHE_MEM_MAX * 0.30)  # _Cache window-property mem cache
PROPERTY_MEM_MAX     = int(GLOBAL_CACHE_MEM_MAX * 0.20)  # Properties._memory_cache
RENDER_CACHE_MAX     = int(GLOBAL_CACHE_MEM_MAX * 0.30)  # served M3U+XMLTV render caches (shared)
XMLTV_MEM_MAX        = int(GLOBAL_CACHE_MEM_MAX * 0.25)  # _XMLTV_HOLDER guide blob (programmes/channels)
JSON_CACHE_MEM_MAX   = int(GLOBAL_CACHE_MEM_MAX * 0.05)  # FileAccess._json_cache LRU
TVSHOWS_MEM_MAX      = int(GLOBAL_CACHE_MEM_MAX * 0.10)  # Resources._tvshows_by_title library index
THROTTLE_MAX         = 256                                                 # _PROGRESS_THROTTLE entry cap
CHECKSUM_CACHE_MAX   = 10000                                               # _Cache._checksum_cache entry cap
SETTINGS_CACHE_MAX   = 1000                                                # constants._SETTINGS_CACHE entry cap
    
# =============================================================================
# Service Timing (all values in seconds)
# =============================================================================
DISCOVERY_TIMER     = 60     # Zeroconf network discovery broadcast interval
DISCOVER_INTERVAL   = 30     # Time between discovery scans
SERVICE_INTERVAL    = 5.0    # Main service loop tick interval
TASK_INTERVAL       = 30.0   # Background task runner tick interval
QUEUE_BURST_DELAY   = 1.0    # Delay between chkQUES burst drains while consumables remain
SUSPEND_INTERVAL    = 2.5    # Pause/suspend polling interval
MIN_EPG_DURATION    = 10800  # Minimum EPG guide duration (3 hours in seconds)
TIMEOUT_EXECUTOR    = 1800   # Single executor task timeout (30 min)
TIMEOUT_EXECUTORS   = 300    # Total executor shutdown timeout (5 min)
ONNEXT_TIMER        = 15     # OnNext notification display duration (seconds)
DEBUG_TIMEOUT       = 900    # Debug log retention timeout (15 min)
YESNO_TIMEOUT       = 30     # YesNo Dialog timeout (30 Secs)

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
NOTIFY_AI_ERROR_INTERVAL = 300  # Min seconds between AI API error dialogs (don't spam)
NOTIFY_AI_DAILY_MAX  = 2     # Max AI failure dialogs per day (any AI error path)
AI_IMAGE_TIMEOUT    = 120    # OpenRouter image-generation request timeout (seconds)
AI_IMAGE_MAX_TOKENS = 4096   # Cap output tokens so image requests fit small key budgets
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
                       "pvr://",
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
SEASONFLE           = 'seasons.json'    # Seasonal content definitions (HTTP-exposed)
HOLIDAYFLE          = 'holidays.json'   # Holiday content definitions (HTTP-exposed)
EXTERNALFEEDFLE     = 'externalfeed.json' # ExternalFeed rule sample feed (HTTP-exposed)

# SQLite cache keys — M3U/XMLTV/genres data lives in cache.db (Phase 1 migration).
M3U_CACHE_KEY       = 'm3u.data'        # {'stations', 'recordings', 'updated', 'version'}
XMLTV_CHANNELS_KEY  = 'xmltv.channels'  # [channel dicts]
XMLTV_PROGRAMMES_KEY= 'xmltv.programmes'# [programme dicts]
XMLTV_RECORDINGS_KEY= 'xmltv.recordings'# [recording dicts]
XMLTV_META_KEY      = 'xmltv.meta'      # {'updated', 'version'} render-cache invalidation token
GENRES_CACHE_KEY    = 'genres.data'     # rendered genres.xml bytes

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
CHANNEL_KEY          = 'Channels'                    # Root property key for channel data
CHANNEL_KEY_USER     = f'{CHANNEL_KEY}'              # User created channels
CHANNEL_KEY_BACKUP   = f'{CHANNEL_KEY}.Backup'       # Backup snapshot key
CHANNEL_KEY_CHANGED  = f'{CHANNEL_KEY}.Changed'      # Dirty flag for pending changes
CHANNEL_KEY_LATEST   = f'{CHANNEL_KEY}.Latest'       # Latest build timestamp
CHANNEL_KEY_AUTOTUNE = f'{CHANNEL_KEY}.Autotune'     # Autotune status key
RESUME_INDEX         = 'Resume.Filelist.Index'       # Playback resume position index

SERVERS_KEY          = 'Servers'
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
CHANNEL_BACKUP_FLE  = os.path.join(BACKUP_LOC,'%s.json'%(CHANNEL_KEY_BACKUP.lower()))         # Channel backup path
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
# User-edited seasonal/holiday data persists in a version-keyed cache setting
# (writable cache.db in the profile dir), seeded from the shipped defaults.
# Never write to REMOTE_LOC — an addon update overwrites it.
SEASONS_KEY         = 'Seasonal.data'                               # User seasonal content cache key
HOLIDAYS_KEY        = 'Holiday.data'                                # User holiday content cache key
EXTERNALFEED        = os.path.join(REMOTE_LOC,EXTERNALFEEDFLE)     # ExternalFeed rule sample feed
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
URL_GITHUB                = 'https://github.com/PseudoTV/PseudoTV_Live'
URL_WIKI                  = 'https://github.com/PseudoTV/PseudoTV_Live/wiki'
URL_SUPPORT               = 'https://forum.kodi.tv/showthread.php?tid=346803'
URL_WIN_BONJOUR           = 'https://support.apple.com/en-us/106380'
URL_README                = f'https://github.com/PseudoTV/PseudoTV_Live/blob/{ADDON_BRANCH}/plugin.video.pseudotv.live/README.md'
URL_CHANGELOG             = f'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/{ADDON_BRANCH}/plugin.video.pseudotv.live/changelog.txt'

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
OVERLAY_XML     = '%s.overlay.xml'%(ADDON_ID)       # Unified overlay dialog (vignette + bug + on-next)
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
RULES_VERSION = 0.2  # Rules schema version

# Rule id migration: old myIds (pre-0.2, execution-order-irregular) -> the
# renumbered execution-ordered scheme. Applied lazily to saved channel rule
# dicts by Channels._verify / Backup.importChannels.
RULES_ID_MIGRATION = {
    2: 100, 50: 101, 51: 102, 52: 103, 53: 104, 54: 105, 55: 106,       # player
    1: 200, 3: 201, 4: 202,                                             # overlay
    3000: 300,                                                          # pause
    497: 400,                                                           # rebuild
    950: 505, 951: 506,                                                 # sort/limits
    800: 600,                                                           # seasonal
    999: 605, 998: 700, 1000: 701, 2999: 706, 505: 1100,                # random/order/even/pad/filter
}

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
RULES_ACTION_M3U_FILTER                    = 15  # Post-M3U http filter
RULES_ACTION_XMLTV_FILTER                  = 16  # Post-XMLTV http filter

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
_LOG_SETTINGS  = {'ts': 0, 'enable': False, 'level': 3}  # cached Debug_Enable/Level for LOG TTL
_LOG_SETTINGS_TTL = 5.0  # seconds to cache debug settings before re-reading from Kodi
_SETTINGS_CACHE = {}  # {(func_name, key): (value, timestamp)} - type-safe getSetting read cache
_SETTINGS_CACHE_TTL = 5.0  # seconds to cache setting reads before re-reading from Kodi
LOG_MAX_LENGTH = 500  # max characters for log message string (traceback excluded)
DEBUG_NAMES    = {0: 'LOGDEBUG', 1: 'LOGINFO', 2: 'LOGWARNING', 3: 'LOGERROR', 4: 'LOGFATAL'}

def LOG(event: Any, level: int = xbmc.LOGDEBUG, throttle: float = float(SERVICE_INTERVAL)):
    """Central logging function. Checks Debug_Enable and Debug_Level settings.
    When level >= 3 (LOGERROR), appends traceback.format_exc() to the message.
    When throttle > 0, consecutive identical (event, level) pairs are suppressed,
    then a 'Skipped N duplicate messages..' line is logged when the sequence ends."""
    global _LOG_LAST_KEY
    # Cache debug settings with a short TTL — getSetting() hits Kodi's C++ API on
    # every call, and LOG is called thousands of times during a build. When debug
    # is off (default) this short-circuits immediately after one cached read.
    _now = time.time()
    if _now - _LOG_SETTINGS['ts'] > _LOG_SETTINGS_TTL:
        _LOG_SETTINGS['ts']     = _now
        _LOG_SETTINGS['enable'] = REAL_SETTINGS.getSetting('Debug_Enable') == 'true'
        _LOG_SETTINGS['level']  = int((REAL_SETTINGS.getSetting('Debug_Level') or "3"))
    if not _LOG_SETTINGS['enable'] and level < 3: return
    DEBUG_LEVELS = {0: xbmc.LOGDEBUG, 1: xbmc.LOGINFO, 2: xbmc.LOGWARNING, 3: xbmc.LOGERROR, 4: xbmc.LOGFATAL}
    DEBUG_LEVEL  = DEBUG_LEVELS[_LOG_SETTINGS['level']]
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
