#   Copyright (C) 2013 Kevin S. Graer
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

import os, sys, re
import xbmcaddon, xbmc, xbmcgui, xbmcvfs
import Settings, pyfscache

from FileAccess import FileLock

# Commoncache plugin import
try:
    import StorageServer
except Exception,e:
    import storageserverdummy as StorageServer

# Plugin Info
ADDON_ID = 'script.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_ID = REAL_SETTINGS.getAddonInfo('id')
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
DEBUG = REAL_SETTINGS.getSetting('enable_Debug') == "true"

def log(msg, level = xbmc.LOGDEBUG):
    if DEBUG != True and level == xbmc.LOGDEBUG:
        return
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + uni(msg), level)

def utf(string, encoding = 'utf-8'):
    if isinstance(string, basestring):
        if not isinstance(string, unicode):
            string = unicode(string, encoding, 'ignore')
    return string
  
def ascii(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('ascii', 'ignore')
    return string
    
def uni(string):
    if isinstance(string, basestring):
        if isinstance(string, unicode):
           string = string.encode('utf-8', 'ignore' )
    return string

# API Keys
TVDB_API_KEY = REAL_SETTINGS.getSetting("TVDB_API")
TMDB_API_KEY = REAL_SETTINGS.getSetting("TMDB_API")
FANARTTV_API_KEY = REAL_SETTINGS.getSetting("FANTV_API")
YT_API_KEY = 'AIzaSyAnwpqhAmdRShnEHnxLiOUjymHlG4ecE7c'
GBOX_API_KEY = 'rKPHzBmsYrFYROD98HS0Bt6rScBccAVm'
LOGODB_API_KEY = '8332'

# Timers
AUTOSTART_TIMER = [0,5,10,15,20]#in seconds
ART_TIMER = [6,12,24,48,72]
SHORT_CLIP_ENUM = [15,30,60,90,120,240,360,480]#in seconds
INFOBAR_TIMER = [3,5,10,15,20,25]#in seconds
LIMIT_VALUES = [25,50,100,250,500,1000,5000,0]#Media Per/Channel, 0 = Unlimited
REFRESH_INT = [10800,21600,43200,86400]#in seconds (3|6|12|24hrs)
REFRESH_HOUR = [4,8,12,24]#in seconds (4|8|12|24hrs)
TIMEOUT = 15 * 1000
TOTAL_FILL_CHANNELS = 20
PREP_CHANNEL_TIME = 60 * 60 * 24 * 5
ALLOW_CHANNEL_HISTORY_TIME = 60 * 60 * 24 * 1
NOTIFICATION_CHECK_TIME = 5
NOTIFICATION_TIME_BEFORE_END = 240
NOTIFICATION_DISPLAY_TIME = 8

# Rules/Modes
RULES_ACTION_START = 1
RULES_ACTION_JSON = 2
RULES_ACTION_LIST = 4
RULES_ACTION_BEFORE_CLEAR = 8
RULES_ACTION_BEFORE_TIME = 16
RULES_ACTION_FINAL_MADE = 32
RULES_ACTION_FINAL_LOADED = 64
RULES_ACTION_OVERLAY_SET_CHANNEL = 128
RULES_ACTION_OVERLAY_SET_CHANNEL_END = 256
MODE_RESUME = 1
MODE_ALWAYSPAUSE = 2
MODE_ORDERAIRDATE = 4
MODE_RANDOM = 8
MODE_REALTIME = 16
MODE_SERIAL = MODE_RESUME | MODE_ALWAYSPAUSE | MODE_ORDERAIRDATE
MODE_STARTMODES = MODE_RANDOM | MODE_REALTIME | MODE_RESUME

# Maximum is 10
RULES_PER_PAGE = 7

#UPNP Clients
IPP1 = REAL_SETTINGS.getSetting("UPNP1_IPP")
IPP2 = REAL_SETTINGS.getSetting("UPNP2_IPP")
IPP3 = REAL_SETTINGS.getSetting("UPNP3_IPP")

#LOCATIONS
SETTINGS_LOC = REAL_SETTINGS.getAddonInfo('profile') #LOCKED
CHANNELS_LOC = os.path.join(SETTINGS_LOC, 'cache','') #LOCKED
REQUESTS_LOC = xbmc.translatePath(os.path.join(CHANNELS_LOC, 'requests','')) #LOCKED
MADE_CHAN_LOC = os.path.join(CHANNELS_LOC, 'stored','') #LOCKED
GEN_CHAN_LOC = os.path.join(CHANNELS_LOC, 'generated','') #LOCKED
IMAGES_LOC = xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'images',''))
PTVL_SKIN_LOC = os.path.join(ADDON_PATH, 'resources', 'skins', '') #Path to PTVL Skin folder
LOGO_LOC = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('ChannelLogoFolder'),'')) #Channel Logo location   
PVR_DOWNLOAD_LOC = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('PVR_Folder'),'')) #PVR Download location
XMLTV_LOC = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('xmltvLOC'),''))
XSP_LOC = xbmc.translatePath("special://profile/playlists/video/")
SFX_LOC = os.path.join(ADDON_PATH, 'resources','sfx','')
BACKUP_LOC = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'backups'))
MOUNT_LOC = xbmc.translatePath(os.path.join(CHANNELS_LOC, 'mountpnt',''))
mountedFS = False

#BASEURL
try:
    UPASS = REAL_SETTINGS.getSetting('Donor_UP')
except:
    UPASS = "Username:Password"

PTVLURL = 'http://pseudotvlive.com/ptvl/'
PTVLURLUP = 'http://%s@pseudotvlive.com/ptvl/' %UPASS

# Core Default Image Locations
DEFAULT_MEDIA_LOC =  xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', 'media',''))
DEFAULT_EPGGENRE_LOC = xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'skins', 'Default', 'media', 'epg-genres',''))

# CORE IMG FILENAMES
THUMB = IMAGES_LOC + 'icon.png'
INTRO = IMAGES_LOC + 'intro.mp4'
INTRO_TUBE = 'Y8WlAhpHzkM'

# EPG
TIME_BAR = 'pstvlTimeBar.png'
TIME_BUTTON = 'pstvlTimeButton.png'
BUTTON_FOCUS = 'pstvlButtonFocus.png'
BUTTON_NO_FOCUS = 'pstvlButtonNoFocus.png'
BUTTON_BACKGROUND_CONTEXT = 'pstvlContextBackground.png'
BUTTON_GAUSS_CONTEXT = 'pstvlBackground_gauss.png'
BUTTON_FOCUS_ALT = 'pstvlButtonFocusAlt.png'
BUTTON_NO_FOCUS_ALT = 'pstvlButtonNoFocusAlt.png'

#Channel Sharing location
if REAL_SETTINGS.getSetting('ChannelSharing') == "true":
    CHANNEL_SHARING = True
    LOCK_LOC = xbmc.translatePath(os.path.join(REAL_SETTINGS.getSetting('SettingsFolder'), 'cache',''))
else:
    CHANNEL_SHARING = False  
    LOCK_LOC = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'cache',''))
    
XMLTV_CACHE_LOC = xbmc.translatePath(os.path.join(LOCK_LOC, 'xmltv',''))
STRM_CACHE_LOC = xbmc.translatePath(os.path.join(LOCK_LOC, 'strm','')) 
ART_LOC = xbmc.translatePath(os.path.join(LOCK_LOC, 'artwork',''))

#ptvlguide
PTVLXML = os.path.join(XMLTV_CACHE_LOC, 'ptvlguide.xml')
PTVLXMLZIP = os.path.join(LOCK_LOC, 'ptvlguide.zip')
PTVLXMLURL = PTVLURL + 'ptvlguide.zip'

# SKIN SELECT
Skin_Select = 'Default'
MEDIA_LOC = xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'skins', Skin_Select, 'media',''))   
EPGGENRE_LOC = xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'skins', Skin_Select, 'media', 'epg-genres','')) 

#Double check core image folders
if not xbmcvfs.exists(MEDIA_LOC):
    print 'forcing default DEFAULT_MEDIA_LOC'
    MEDIA_LOC = DEFAULT_MEDIA_LOC 
if not xbmcvfs.exists(EPGGENRE_LOC):
    print 'forcing default DEFAULT_EPGGENRE_LOC'
    EPGGENRE_LOC = DEFAULT_EPGGENRE_LOC               
           
# Find XBMC Skin path
if xbmcvfs.exists(xbmc.translatePath(os.path.join('special://','skin','720p',''))):
    XBMC_SKIN_LOC = xbmc.translatePath(os.path.join('special://','skin','720p',''))
else:
    XBMC_SKIN_LOC = xbmc.translatePath(os.path.join('special://','skin','1080i',''))
    
# Find PTVL selected skin folder 720 or 1080i ?
if xbmcvfs.exists(os.path.join(PTVL_SKIN_LOC, Skin_Select, '720p','')):
    PTVL_SKIN_SELECT = xbmc.translatePath(os.path.join(PTVL_SKIN_LOC, Skin_Select, '720p', ''))
else:
    PTVL_SKIN_SELECT = xbmc.translatePath(os.path.join(PTVL_SKIN_LOC, Skin_Select, '1080i', ''))

# Globals
dlg = xbmcgui.Dialog()
ADDON_SETTINGS = Settings.Settings()
GlobalFileLock = FileLock()
NOTIFY = REAL_SETTINGS.getSetting('EnableNotify') == "true"
SETTOP = REAL_SETTINGS.getSetting("EnableSettop") == "true"
ENHANCED_DATA = REAL_SETTINGS.getSetting('EnhancedGuideData') == 'true'
FILELIST_LIMIT = [4096,8192,16384]
MAXFILE_DURATION = 16000
RSS_REFRESH = 900
ONNOW_REFRESH = 450

# Settings2 filepaths
SETTINGS_FLE = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.xml'))
SETTINGS_FLE_DEFAULT_SIZE = 100
SETTINGS_FLE_REPAIR = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.repair.xml'))
SETTINGS_FLE_PENDING = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.pending.xml'))
SETTINGS_FLE_LASTRUN = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.lastrun.xml'))
SETTINGS_FLE_PRETUNE = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'settings2.pretune.xml'))

# commoncache globals
daily = StorageServer.StorageServer("plugin://script.pseudotv.live/" + "daily",24)
weekly = StorageServer.StorageServer("plugin://script.pseudotv.live/" + "weekly",24 * 7)
monthly = StorageServer.StorageServer("plugin://script.pseudotv.live/" + "monthly",((24 * 7) * 4))

# commoncache artwork (Only needed for Artwork Spooler Service)
artwork = StorageServer.StorageServer("plugin://script.pseudotv.live/" + "artwork",((24 * 7) * 4))         #Artwork Purge
artwork1 = StorageServer.StorageServer("plugin://script.pseudotv.live/" + "artwork1",((24 * 7) * 4))       #Artwork Purge
artwork2 = StorageServer.StorageServer("plugin://script.pseudotv.live/" + "artwork2",((24 * 7) * 4))       #Artwork Purge
artwork3 = StorageServer.StorageServer("plugin://script.pseudotv.live/" + "artwork3",((24 * 7) * 4))       #Artwork Purge
artwork4 = StorageServer.StorageServer("plugin://script.pseudotv.live/" + "artwork4",((24 * 7) * 4))       #Artwork Purge
artwork5 = StorageServer.StorageServer("plugin://script.pseudotv.live/" + "artwork5",((24 * 7) * 4))       #Artwork Purge
artwork6 = StorageServer.StorageServer("plugin://script.pseudotv.live/" + "artwork6",((24 * 7) * 4))       #Artwork Purge

# pyfscache globals
cache_daily = pyfscache.FSCache(REQUESTS_LOC, days=1, hours=0, minutes=0)
cache_weekly = pyfscache.FSCache(REQUESTS_LOC, days=7, hours=0, minutes=0)
cache_monthly = pyfscache.FSCache(REQUESTS_LOC, days=31, hours=0, minutes=0)
    
if REAL_SETTINGS.getSetting('EnableSettop') == 'true': 
    SETTOP_REFRESH = REFRESH_INT[int(REAL_SETTINGS.getSetting('REFRESH_INT'))] 
else:
    SETTOP_REFRESH = 72000

try:
    MEDIA_LIMIT = LIMIT_VALUES[int(REAL_SETTINGS.getSetting('MEDIA_LIMIT'))]
except:
    MEDIA_LIMIT = 25
    xbmc.log('Channel Media Limit Failed!')
xbmc.log('Channel Media Limit is ' + str(MEDIA_LIMIT))

try:
    AT_LIMIT = LIMIT_VALUES[int(REAL_SETTINGS.getSetting('AT_LIMIT'))]
except:
    AT_LIMIT = 25
    xbmc.log('Autotune Channel Limit Failed!')
xbmc.log('Autotune Channel Limit is ' + str(AT_LIMIT))
            
# HEX COLOR OPTIONS 4 (Overlay CHANBUG, EPG Genre & CHtype) 
# http://www.w3schools.com/html/html_colornames.asp
COLOR_RED = '#FF0000'
COLOR_GREEN = '#008000'
COLOR_mdGREEN = '#3CB371'
COLOR_BLUE = '#0000FF'
COLOR_ltBLUE = '#ADD8E6'
COLOR_CYAN = '#00FFFF'
COLOR_ltCYAN = '##E0FFFF'
COLOR_PURPLE = '#800080'
COLOR_ltPURPLE = '#9370DB'
COLOR_ORANGE = '#FFA500'
COLOR_YELLOW = '#FFFF00'
COLOR_GRAY = '#808080'
COLOR_ltGRAY = '#D3D3D3'
COLOR_mdGRAY = '#696969'
COLOR_dkGRAY = '#A9A9A9'
COLOR_BLACK = '#000000'
COLOR_WHITE = '#FFFFFF'
COLOR_HOLO = 'FF0297eb'
COLOR_SMOKE = '#F5F5F5'

# EPG Chtype/Genre COLOR TYPES
COLOR_RED_TYPE = ['10', '17', 'TV-MA', 'R', 'NC-17', 'Youtube', 'Gaming', 'Sports', 'Sport', 'Sports Event', 'Sports Talk', 'Archery', 'Rodeo', 'Card Games', 'Martial Arts', 'Basketball', 'Baseball', 'Hockey', 'Football', 'Boxing', 'Golf', 'Auto Racing', 'Playoff Sports', 'Hunting', 'Gymnastics', 'Shooting', 'Sports non-event']
COLOR_GREEN_TYPE = ['5', 'News', 'Public Affairs', 'Newsmagazine', 'Politics', 'Entertainment', 'Community', 'Talk', 'Interview', 'Weather']
COLOR_mdGREEN_TYPE = ['9', 'Suspense', 'Horror', 'Horror Suspense', 'Paranormal', 'Thriller', 'Fantasy']
COLOR_BLUE_TYPE = ['Comedy', 'Comedy-Drama', 'Romance-Comedy', 'Sitcom', 'Comedy-Romance']
COLOR_ltBLUE_TYPE = ['2', '4', '14', '15', '16', 'Movie']
COLOR_CYAN_TYPE = ['8', 'Documentary', 'History', 'Biography', 'Educational', 'Animals', 'Nature', 'Health', 'Science & Tech', 'Learning & Education', 'Foreign Language']
COLOR_ltCYAN_TYPE = ['Outdoors', 'Special', 'Reality', 'Reality & Game Shows']
COLOR_PURPLE_TYPE = ['Drama', 'Romance', 'Historical Drama']
COLOR_ltPURPLE_TYPE = ['12', '13', 'LastFM', 'Vevo', 'VevoTV', 'Musical', 'Music', 'Musical Comedy']
COLOR_ORANGE_TYPE = ['11', 'TV-PG', 'TV-14', 'PG', 'PG-13', 'RSS', 'Animation', 'Animation & Cartoons', 'Animated', 'Anime', 'Children', 'Cartoon', 'Family']
COLOR_YELLOW_TYPE = ['1', '3', '6', 'TV-Y7', 'TV-Y', 'TV-G', 'G', 'Classic TV', 'Action', 'Adventure', 'Action & Adventure', 'Action and Adventure', 'Action Adventure', 'Crime', 'Crime Drama', 'Mystery', 'Science Fiction', 'Series', 'Western', 'Soap', 'Soaps', 'Variety', 'War', 'Law', 'Adults Only']
COLOR_GRAY_TYPE = ['Auto', 'Collectibles', 'Travel', 'Shopping', 'House Garden', 'Home & Garden', 'Home and Garden', 'Gardening', 'Fitness Health', 'Fitness', 'Home Improvement', 'How-To', 'Cooking', 'Fashion', 'Beauty & Fashion', 'Aviation', 'Dance', 'Auction', 'Art', 'Exercise', 'Parenting', 'Food', 'Health & Fitness']
COLOR_ltGRAY_TYPE = ['0', '7', 'NR', 'Consumer', 'Game Show', 'Other', 'Unknown', 'Religious', 'Anthology', 'None']

# http://developer.android.com/reference/android/graphics/Color.html
#               ['COLOR_HOLO', 'COLOR_CYAN', 'COLOR_GREEN', 'COLOR_GRAY', 'COLOR_ltGRAY', 'COLOR_WHITE']
COLOR_CHANNUM = ['0xFF0297eb', '0xC0C0C0C0', '0xff00ff00', '0xff888888', '0xffcccccc', '0xffffffff']
CHANBUG_COLOR = COLOR_CHANNUM[int(REAL_SETTINGS.getSetting('COLOR_CHANNUM'))]

#Actions
#https://github.com/xbmc/xbmc/blob/master/xbmc/input/Key.h
# https://github.com/xbmc/xbmc/blob/master/xbmc/input/ButtonTranslator.cpp
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_PAGEUP = 5
ACTION_PAGEDOWN = 6
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = [9, 10, 92, 247, 257, 275, 61467, 61448]
ACTION_DELETE_ITEM = 80
ACTION_SHOW_INFO = 11
ACTION_PAUSE = 12
ACTION_PLAYER_PLAYPAUSE = 249 #Play/pause. If playing it pauses, if paused it plays.
ACTION_STOP = 13
ACTION_OSD = 124
ACTION_NUMBER_0 = 58
ACTION_NUMBER_1 = 59
ACTION_NUMBER_2 = 60
ACTION_NUMBER_3 = 61
ACTION_NUMBER_4 = 62
ACTION_NUMBER_5 = 63
ACTION_NUMBER_6 = 64
ACTION_NUMBER_7 = 65
ACTION_NUMBER_8 = 66
ACTION_NUMBER_9 = 67
ACTION_INVALID = 999
ACTION_SHOW_SUBTITLES = 25 #turn subtitles on/off. 
ACTION_AUDIO_NEXT_LANGUAGE = 56 #Select next language in movie
ACTION_CONTEXT_MENU = 117
ACTION_RECORD = 170 #PVR Backend Record
ACTION_SHOW_CODEC = 27
ACTION_ASPECT_RATIO = 19 
ACTION_SHIFT = 118
ACTION_SYMBOLS = 119
ACTION_CURSOR_LEFT  = 120
ACTION_CURSOR_RIGHT = 121
#unused
ACTION_NEXT_ITEM = 14
ACTION_PREV_ITEM = 15
ACTION_STEP_FOWARD = 17
ACTION_STEP_BACK = 18
ACTION_BIG_STEP_FORWARD = 19
ACTION_BIG_STEP_BACK = 20
ACTION_PLAYER_FORWARD = 73
ACTION_PLAYER_REWIND = 74
ACTION_PLAYER_PLAY = 75
ACTION_PLAYER_PLAYPAUSE = 76
ACTION_TRIGGER_OSD = 243 #show autoclosing OSD. Can b used in videoFullScreen.xml window id=2005
ACTION_SHOW_MPLAYER_OSD = 83 #toggles mplayers OSD. Can be used in videofullscreen.xml window id=2005
ACTION_SHOW_OSD_TIME = 123 #displays current time, can be used in videoFullScreen.xml window id=2005
ACTION_MENU = 7
ACTION_TELETEXT_RED = 215
ACTION_TELETEXT_GREEN = 216
ACTION_TELETEXT_YELLOW = 217
ACTION_TELETEXT_BLUE = 218
#unused
#define ACTION_MUTE                   91
#define ACTION_CHANNEL_SWITCH         183 #last channel?
#define ACTION_TOGGLE_WATCHED         200 // Toggle watched status (videos)
#define ACTION_TOGGLE_DIGITAL_ANALOG  202 // switch digital <-> analog
#define ACTION_TRIGGER_OSD            243 // show autoclosing OSD. Can b used in videoFullScreen.xml window id=2005
#define ACTION_INPUT_TEXT             244
#define ACTION_STEREOMODE_TOGGLE      237 // turns 3d mode on/off

#UTC XMLTV - XMLTV that uses UTC w/ Offset timing (not local time).
UTC_XMLTV = []

# Plugin seek blacklist - Plugins that are known to use rtmp source which lockup xbmc during seek
BYPASS_SEEK = ['plugin.video.vevo_tv','plugin.video.g4tv','plugin.video.ustvnow']

# Duration in seconds "stacked" for chtypes >= 10
BYPASS_EPG_SECONDS = 900

# Force "stacked" EPG by channel name
FORCE_EPG_STACK =  ['PseudoCinema']

# Bypass "stacked" EPG by channel name
BYPASS_EPG_STACK = []

# Bypass Overlay "Coming up next" by channel name
BYPASS_COMINGUP = ['PseudoCinema']

# Plugin exclusion strings
SF_FILTER = ['isearch', 'iplay - kodi playlist manager','create new super folder','explore kodi favourites']
EX_FILTER = SF_FILTER + ['video resolver settings','<<','back','previous','home','search','find','clips','seasons','trailers']

# SFX
ALERT_SFX = os.path.join(SFX_LOC, 'alert.wav')
BACK_SFX = os.path.join(SFX_LOC, 'back.wav')
CONTEXT_SFX = os.path.join(SFX_LOC, 'context.wav')
ERROR_SFX = os.path.join(SFX_LOC, 'error.wav')
FAILED_SFX = os.path.join(SFX_LOC, 'failed.wav')
SELECT_SFX = os.path.join(SFX_LOC, 'select.wav')
PUSH_SFX = os.path.join(SFX_LOC, 'push.wav')