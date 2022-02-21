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

import os, sys, re, struct, shutil, traceback, threading, decimal, pathlib
import datetime, time, _strptime, base64, binascii, random, hashlib
import json, codecs, collections, uuid, queue

from kodi_six                  import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from itertools                 import cycle, chain, zip_longest
from six.moves                 import urllib 
from contextlib                import contextmanager, closing
from xml.dom.minidom           import parse, Document
from resources.lib.fileaccess  import FileAccess
from resources.lib.kodi        import Settings, Properties, Dialog
from resources.lib.cache       import cacheit
from socket                    import gethostbyname, gethostname

#info
ADDON_ID            = 'plugin.video.pseudotv.live'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')

#
LANGUAGE            = REAL_SETTINGS.getLocalizedString
SETTINGS            = Settings()
PROPERTIES          = Properties()

#folders
IMAGE_LOC           = os.path.join(ADDON_PATH,'resources','images')
MEDIA_LOC           = os.path.join(ADDON_PATH,'resources','skins','default','media')
BACKUP_LOC          = os.path.join(SETTINGS_LOC,'backup')

#files
XMLTVFLE            = '%s.xml'%('pseudotv')
M3UFLE              = '%s.m3u'%('pseudotv')
CHANNELFLE          = 'channels.json'
LIBRARYFLE          = 'library.json'
GENREFLE            = 'genres.xml'
TVGROUPFLE          = 'tv_groups.xml'
RADIOGROUPFLE       = 'radio_groups.xml'
PROVIDERFLE         = 'providers.xml'

#switches      
USER_LOC            = (SETTINGS.getSetting('User_Folder') or os.path.join(SETTINGS_LOC,'cache'))
DEBUG_ENABLED       = SETTINGS.getSettingBool('Enable_Debugging')
PAGE_LIMIT          = SETTINGS.getSettingInt('Page_Limit')
PREDEFINED_OFFSET   = ((SETTINGS.getSettingInt('Max_Days') * 60) * 60)
   
CHANNELFLEPATH      = os.path.join(SETTINGS_LOC,CHANNELFLE)
LIBRARYFLEPATH      = os.path.join(SETTINGS_LOC,LIBRARYFLE)
SETTINGS_FLE        = os.path.join(SETTINGS_LOC,'settings.xml')
CHANNELFLE_BACKUP   = os.path.join(SETTINGS_LOC,'channels.backup')
CHANNELFLE_RESTORE  = os.path.join(SETTINGS_LOC,'channels.restore')

CACHE_LOC           = USER_LOC
PLS_LOC             = os.path.join(USER_LOC,'playlists')
LOGO_LOC            = os.path.join(USER_LOC,'logos')
M3UFLEPATH          = os.path.join(USER_LOC,M3UFLE)
XMLTVFLEPATH        = os.path.join(USER_LOC,XMLTVFLE)
GENREFLEPATH        = os.path.join(USER_LOC,GENREFLE)
PROVIDERFLEPATH     = os.path.join(USER_LOC,PROVIDERFLE)

UDP_PORT            = SETTINGS.getSettingInt('UDP_PORT')
TCP_PORT            = SETTINGS.getSettingInt('TCP_PORT')

#remotes
IMPORT_ASSET        = os.path.join(ADDON_PATH,'remotes','asset.json')
GROUPFLE_DEFAULT    = os.path.join(ADDON_PATH,'remotes','groups.xml')
LIBRARYFLE_DEFAULT  = os.path.join(ADDON_PATH,'remotes',LIBRARYFLE)
CHANNELFLE_DEFAULT  = os.path.join(ADDON_PATH,'remotes',CHANNELFLE)
GENREFLE_DEFAULT    = os.path.join(ADDON_PATH,'remotes',GENREFLE)
PROVIDERFLE_DEFAULT = os.path.join(ADDON_PATH,'remotes',PROVIDERFLE)

#docs
README_FLE          = os.path.join(ADDON_PATH,'README.md')
CHANGELOG_FLE       = os.path.join(ADDON_PATH,'changelog.txt')
LICENSE_FLE         = os.path.join(ADDON_PATH,'LICENSE')

#resources
OVERLAY_FLE         = "%s.overlay.xml"%(ADDON_ID)
COLOR_LOGO          = os.path.join(MEDIA_LOC,'logo.png')
MONO_LOGO           = os.path.join(MEDIA_LOC,'wlogo.png')
LOGO                = (COLOR_LOGO if bool(SETTINGS.getSettingInt('Color_Logos')) else MONO_LOGO).replace(ADDON_PATH,'special://home/addons/%s/'%(ADDON_ID)).replace('\\','/')
HOST_LOGO           = 'http://github.com/PseudoTV/PseudoTV_Live/blob/master/plugin.video.pseudotv.live/resources/skins/default/media/logo.png?raw=true'
PVR_URL             = 'plugin://{addon}/?mode=play&name={name}&id={id}&radio={radio}.pvr'
VOD_URL             = 'plugin://{addon}/?mode=vod&name={name}&id={id}&channel={channel}&radio={radio}.pvr'

#constants
LANG                = 'en' #todo parse kodi region settings
DTFORMAT            = '%Y%m%d%H%M%S'
DTZFORMAT           = '%Y%m%d%H%M%S +%z'
DEFAULT_ENCODING    = 'utf-8'

RULES_PER_PAGE      = 10
MAX_IMPORT          = 5
CLOCK_SEQ           = 70420
UPDATE_WAIT         = 3600  #1hr in secs.
EPG_HRS             = 10800 #3hr in Secs., Min. EPG guidedata
OVERLAY_DELAY       = 15    #secs
MIN_ENTRIES         = int(PAGE_LIMIT//2)

TIME_CHECK          = 90
RADIO_ITEM_LIMIT    = 250
AUTOTUNE_LIMIT      = 3     #auto items per type.
CHANNEL_LIMIT       = 999   #hard limit, do not exceed!

UPDATE_OFFSET       = 10800 #3hr in secs.
LIBRARY_OFFSET      = 3600
RECOMMENDED_OFFSET  = 900   #15mins in secs.
PROMPT_DELAY        = 4000  #msecs 

VIDEO_EXTS          = xbmc.getSupportedMedia('video').split('|')
MUSIC_EXTS          = xbmc.getSupportedMedia('music').split('|')
IMAGE_EXTS          = xbmc.getSupportedMedia('picture').split('|')

#builder
RULES_ACTION_CHANNEL       = 1 
RULES_ACTION_BUILD_START   = 2
RULES_ACTION_CHANNEL_START = 3
RULES_ACTION_CHANNEL_JSON  = 4
RULES_ACTION_CHANNEL_ITEMS = 5
RULES_ACTION_CHANNEL_STOP  = 6
RULES_ACTION_PRE_TIME      = 7
RULES_ACTION_POST_TIME     = 8
RULES_ACTION_BUILD_STOP    = 9
#player
RULES_ACTION_PLAYBACK      = 11
RULES_ACTION_PLAYER        = 12
#overlay
RULES_ACTION_OVERLAY       = 21

#overlay globals
NOTIFICATION_CHECK_TIME     = 15.0 #seconds
NOTIFICATION_TIME_REMAINING = 900  #seconds
NOTIFICATION_PLAYER_PROG    = 85   #percent
NOTIFICATION_DISPLAY_TIME   = 30   #seconds
CHANNELBUG_CHECK_TIME       = 15.0 #seconds

# Actions
ACTION_MOVE_LEFT     = 1
ACTION_MOVE_RIGHT    = 2
ACTION_MOVE_UP       = 3
ACTION_MOVE_DOWN     = 4
ACTION_SELECT_ITEM   = 7
ACTION_SHOW_INFO     = [11,24,401]
ACTION_PREVIOUS_MENU = [10,110,521] #+ [9, 92, 216, 247, 257, 275, 61467, 61448]

# Windows
FILE_MANAGER	     = 10003
YESNO_DIALOG	     = 10100
VIRTUAL_KEYBOARD     = 10103
CONTEXT_MENU      	 = 10106
NUMERIC_INPUT        = 10109
FILE_BROWSER         = 10126
BUSY_DIALOG          = 10138
ADDON_SETTINGS       = 10140
BUSY_DIALOG_NOCANCEL = 10160
SELECT_DIALOG        = 12000
OK_DIALOG            = 12002
ADDON_DIALOG         = 13001

GROUP_TYPES         = ['Addon', 'Directory', 'Favorites', 'Mixed', LANGUAGE(30006), 'Mixed Movies', 'Mixed TV', LANGUAGE(30005), LANGUAGE(30007), 'Movies', 'Music', LANGUAGE(30097), 'Other', 'PVR', 'Playlist', 'Plugin', 'Radio', LANGUAGE(30026), 'Smartplaylist', 'TV', LANGUAGE(30004), LANGUAGE(30002), LANGUAGE(30003), 'UPNP', 'IPTV']
BCT_TYPES           = ['bumpers','ratings','commercials','trailers']
PRE_ROLL            = ['bumpers','ratings']
POST_ROLL           = ['commercials','trailers']

# jsonrpc
TV_TYPES            = ['episode','tvshow']
MOVIE_TYPES         = ['movie','movies']
MUSIC_TYPES         = ['songs','albums','artists','music']
ART_PARAMS          = ["thumb","icon","poster","fanart","banner","landscape","clearart","clearlogo"]
VFS_TYPES           = ["plugin://","pvr://","upnp://","resource://"]

ADDON_REPOSITORY    = ['repository.pseudotv','repository.lunatixz']
PVR_CLIENT          = 'pvr.iptvsimple'
PVR_MANAGER         = 'service.iptv.manager'
MGR_SETTINGS        = {'refresh_interval'   :'1',
                       'iptv_simple_restart':'false'}
                    
CHAN_TYPES          = [LANGUAGE(30002),LANGUAGE(30003),LANGUAGE(30004),
                       LANGUAGE(30005),LANGUAGE(30007),LANGUAGE(30006),
                       LANGUAGE(30080),LANGUAGE(30026),LANGUAGE(30097),
                       LANGUAGE(30033)]#Limit is 10
                       
JSON_SETTINGS       = {'pvrmanager.preselectplayingchannel' :'true',
                       'pvrmanager.syncchannelgroups'       :'true',
                       'pvrmanager.backendchannelorder'     :'true',
                       'pvrmanager.usebackendchannelnumbers':'true',
                       # 'pvrmenu.iconpath':'',
                       # 'pvrplayback.switchtofullscreenchanneltypes':1,
                       # 'pvrplayback.confirmchannelswitch':'true',
                       # 'epg.selectaction':2,
                       # 'epg.epgupdate':120,
                       'pvrmanager.startgroupchannelnumbersfromone':'false'}

LOG_TYPE            = {0:{'level':xbmc.LOGDEBUG  ,'weight':4,'description':"In depth information about the status of Kodi. This information can pretty much only be deciphered by a developer or long time Kodi power user."},
                       1:{'level':xbmc.LOGINFO   ,'weight':3,'description':"Something has happened. It's not a problem, we just thought you might want to know. Fairly excessive output that most people won't care about."},
                       2:{'level':xbmc.LOGWARNING,'weight':2,'description':"Something potentially bad has happened. If Kodi did something you didn't expect, this is probably why. Watch for errors to follow."},
                       3:{'level':xbmc.LOGERROR  ,'weight':1,'description':"This event is bad. Something has failed. You likely noticed problems with the application be it skin artifacts, failure of playback a crash, etc."}}

def getPVR_SETTINGS(): 
    return {'m3uRefreshMode'              :'1',
            'm3uRefreshIntervalMins'      :'5',
            'm3uRefreshHour'              :'0',
            'm3uCache'                    :'true',
            'logoPathType'                :'0',
            'logoPath'                    :LOGO_LOC,
            'm3uPathType'                 :'%s'%('1' if SETTINGS.getSettingInt('Client_Mode') == 2 else '0'),
            'm3uPath'                     :M3UFLEPATH,
            'm3uUrl'                      :PROPERTIES.getProperty('M3U_URL'),
            'epgPathType'                 :'%s'%('1' if SETTINGS.getSettingInt('Client_Mode') == 2 else '0'),
            'epgPath'                     :XMLTVFLEPATH,
            'epgUrl'                      :PROPERTIES.getProperty('XMLTV_URL'),
            'epgCache'                    :'true',
            'genresPathType'              :'%s'%('1' if SETTINGS.getSettingInt('Client_Mode') == 2 else '0'),
            'genresPath'                  :GENREFLEPATH,
            'genresUrl'                   :PROPERTIES.getProperty('GENRE_URL'),
            # 'tvGroupMode'                 :'0',
            # 'customTvGroupsFile'          :(TVGROUPFLE),#todo
            # 'radioGroupMode'              :'0',
            # 'customRadioGroupsFile'       :(RADIOGROUPFLE),#todo
            'enableProviderMappings'      :'true',
            'defaultProviderName'         :ADDON_NAME,
            'providerMappingFile'         :PROVIDERFLEPATH,#todo
            'useEpgGenreText'             :'true',
            'logoFromEpg'                 :'1',
            'catchupEnabled'              :'true',
            'allChannelsCatchupMode'      :'0',
            'numberByOrder'               :'false',
            'startNum'                    :'1',
            'epgTimeShift'                :'0',
            'epgTSOverride'               :'false',
            'useFFmpegReconnect'          :'true',
            'useInputstreamAdaptiveforHls':'true'}


def getPTV_SETTINGS(): 
    return {'User_Import'         :SETTINGS.getSetting('User_Import'),
            'Import_M3U_TYPE'     :SETTINGS.getSetting('Import_M3U_TYPE'),
            'Import_M3U_FILE'     :SETTINGS.getSetting('Import_M3U_FILE'),
            'Import_M3U_URL'      :SETTINGS.getSetting('Import_M3U_URL'),
            'Import_Provider'     :SETTINGS.getSetting('Import_Provider'),
            'User_Folder'         :SETTINGS.getSetting('User_Folder'),
            'Client_Mode'         :SETTINGS.getSetting('Client_Mode'),
            'UDP_PORT'            :SETTINGS.getSetting('UDP_PORT'),
            'TDP_PORT'            :SETTINGS.getSetting('TDP_PORT')}
             
@contextmanager
def fileLocker(globalFileLock):
    globalFileLock.lockFile("MasterLock")
    try: yield
    finally: 
        globalFileLock.unlockFile('MasterLock')
        globalFileLock.close()

@contextmanager
def busy():
    if isBusy(): yield
    else:
        setBusy(True)
        try:     yield
        finally: setBusy(False)

@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:     yield
    finally: xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

def log(event, level=xbmc.LOGDEBUG): #todo unifiy all logs to its own class to handle events/exceptions.
    if not DEBUG_ENABLED and level != xbmc.LOGERROR: return
    if not isinstance(event,str): msg = str(event)
    if level == xbmc.LOGERROR: event = '%s\n%s'%((event),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,event),level)
    
def chkSettings(last,current):
    changed = set()
    for key,value in last.items():
        if value != current[key]:
            if key == 'User_Folder': 
                if moveUser(value,current[key]):
                    Dialog().notificationDialog(LANGUAGE(30183))
                    toggleADDON(ADDON_ID, state=False, reverse=True)
                    return False
            elif key in ['UDP_PORT','TCP_PORT']: 
                Dialog().notificationDialog(LANGUAGE(30183))
                toggleADDON(ADDON_ID, state=False, reverse=True)
                return False
            changed.add(True)
    if True in list(changed): return True
       
def initFolders():
    [FileAccess.makedirs(dir) for dir in [SETTINGS_LOC,USER_LOC,PLS_LOC,LOGO_LOC] if not FileAccess.exists(dir)]
 
def validateFiles():
    initFolders()
    results = [FileAccess.exists(path)      for path in [CHANNELFLEPATH, LIBRARYFLEPATH]]
    results.extend([FileAccess.exists(path) for path in [M3UFLEPATH, XMLTVFLEPATH]])
    if False in results: return True
    else:                return False
        
def chkUpdateTime(key, wait, lastUpdate=None):
    state = False
    if lastUpdate is None: lastUpdate = float((SETTINGS.getCacheSetting(key,checksum=getInstanceID()) or 0))
    epoch = time.time()
    if (epoch >= (lastUpdate + wait)):
        SETTINGS.setCacheSetting(key,int(epoch),checksum=getInstanceID())
        state = True
    log('globals: chkUpdateTime, key = %s, lastUpdate = %s, update now = %s'%(key,lastUpdate,state))
    return state
    
def isLegacyPseudoTV(): # legacy setting to disable/enable support in third-party applications. 
    return PROPERTIES.getEXTProperty('PseudoTVRunning') == "True"

def setLegacyPseudoTV(state):
    return PROPERTIES.setEXTProperty('PseudoTVRunning',state)
    
def setBusy(state):
    return PROPERTIES.setPropertyBool("BUSY.WORKING",state)
    
def isBusy():
    return PROPERTIES.getPropertyBool("BUSY.WORKING")
    
def isPaused():
    return xbmc.getCondVisibility('Player.Paused')

def hasLibraryRun():
    return PROPERTIES.getEXTProperty('hasLibraryRun') == "True"

def setLibraryRun(state):
    return PROPERTIES.setEXTProperty('hasLibraryRun',state)
    
def isUpdatePending():
    state = PROPERTIES.getPropertyBool('isUpdatePending')
    PROPERTIES.clearProperty('isUpdatePending')
    return state
    
def setUpdatePending(state=True):
    return PROPERTIES.setPropertyBool('isUpdatePending',state)
    
def isRestartRequired():
    state = PROPERTIES.getPropertyBool('restartRequired')
    PROPERTIES.clearProperty('restartRequired')
    return state
        
def setRestartRequired(state=True):
    return PROPERTIES.setPropertyBool('restartRequired',state)
       
def isShutdownRequired():
    state = PROPERTIES.getPropertyBool('shutdownRequired')
    PROPERTIES.clearProperty('shutdownRequired')
    return state
                 
def setServiceStop(state=True):
    return PROPERTIES.setPropertyBool('shutdownRequired',state)
         
def hasAutotuned():
    return PROPERTIES.getPropertyBool('hasAutotuned')
    
def setAutotuned(state=True):
    return PROPERTIES.setPropertyBool('hasAutotuned',state)
    
def isOverlay():
    return PROPERTIES.getPropertyBool('OVERLAY')

def isManagerRunning():
    return PROPERTIES.getPropertyBool('managerRunning')
    
def setManagerRunning(state=True):
    return PROPERTIES.setPropertyBool('managerRunning',state)
    
def getSettingDialog():
    return xbmc.getCondVisibility("Window.IsVisible(addonsettings)")
    
def isSettingDialog():
    return (PROPERTIES.getPropertyBool('addonsettings') or getSettingDialog())
    
def setSettingDialog(state=True):
    return PROPERTIES.setPropertyBool('addonsettings',state)

def getSelectDialog():
    return xbmc.getCondVisibility("Window.IsVisible(selectdialog)")
        
def isSelectDialog():
    return (PROPERTIES.getPropertyBool('selectdialog') or getSelectDialog())

def setSelectDialog(state=True):
    return PROPERTIES.setPropertyBool('selectdialog',state)

def isYesNoDialog():
    return (xbmc.getCondVisibility("Window.IsVisible(yesnodialog)"))
    
def isKeyboardDialog():
    return (xbmc.getCondVisibility("Window.IsVisible(virtualkeyboard)"))
    
def isFileDialog():
    return (xbmc.getCondVisibility("Window.IsVisible(filebrowser)"))

def hasPVR():
    return xbmc.getCondVisibility('Pvr.HasTVChannels')
    
def hasMusic():
    return xbmc.getCondVisibility('Library.HasContent(Music)')
    
def hasTV():
    return xbmc.getCondVisibility('Library.HasContent(TVShows)')
    
def hasMovie():
    return xbmc.getCondVisibility('Library.HasContent(Movies)')
 
def hasPVRAddon():
    return xbmc.getCondVisibility("System.HasPVRAddon")
         
def hasAddon(id):
    if not id: return True
    return xbmc.getCondVisibility("System.HasAddon(%s)"%id)
    
def isClient():
    return (PROPERTIES.getPropertyBool('isClient') or SETTINGS.getSettingInt('Client_Mode') > 0)
    
def doUtilities():
    param = PROPERTIES.getProperty('utilities')
    PROPERTIES.clearProperty('utilities')
    return param
    
def getDiscovery():
    return PROPERTIES.getProperty('discovery')

def setDiscovery( value):
    return PROPERTIES.setProperty('discovery',value)

def setInstanceID():
    PROPERTIES.setProperty('InstanceID',uuid.uuid4())

def getInstanceID():
    instanceID = PROPERTIES.getProperty('InstanceID') 
    if not instanceID: setInstanceID()
    return PROPERTIES.getProperty('InstanceID')
  
def getMD5(text):
    if not isinstance(text,str): text = str(text)
    hash_object = hashlib.md5(text.encode())
    return hash_object.hexdigest()
  
def genUUID(seed=None):
    if seed:
        m = hashlib.md5()
        m.update(seed.encode(DEFAULT_ENCODING))
        return str(uuid.UUID(m.hexdigest()))
    return str(uuid.uuid1(clock_seq=CLOCK_SEQ))

def getIP(wait=5):
    while not xbmc.Monitor().abortRequested() and wait > 0:
        ip = (xbmc.getIPAddress() or gethostbyname(gethostname()))
        if ip: return ip
        elif (xbmc.Monitor().waitForAbort(1)): break
        else: wait -= 1
    return
            
def getMYUUID():
    uuid = SETTINGS.getCacheSetting('MY_UUID')
    if not uuid: 
        uuid = genUUID(seed=getIP())
        SETTINGS.setCacheSetting('MY_UUID',uuid)
    return uuid

def getUUID(channelList={}):
    return channelList.get('uuid',getMYUUID())
        
def chkDiscovery(SERVER_HOST=None):
    PROPERTIES.setPropertyBool('isClient',SETTINGS.getSettingInt('Client_Mode') > 0)
    CLIENT      = isClient()
    SERVER_PAST = PROPERTIES.getProperty('SERVER_HOST')
    LOCAL_HOST  = PROPERTIES.getProperty('LOCAL_HOST')
    if not SERVER_HOST:
        SERVER_HOST = (getDiscovery() or LOCAL_HOST)
        
    if not CLIENT and SERVER_PAST == LOCAL_HOST:
        return CLIENT
    elif SERVER_PAST != SERVER_HOST:
        SETTINGS.setSetting('Network_Path',USER_LOC)
        SETTINGS.setSetting('Remote_URL'  ,'http://%s'%(SERVER_HOST))
        SETTINGS.setSetting('Remote_M3U'  ,'http://%s/%s'%(SERVER_HOST,M3UFLE))
        SETTINGS.setSetting('Remote_XMLTV','http://%s/%s'%(SERVER_HOST,XMLTVFLE))
        SETTINGS.setSetting('Remote_GENRE','http://%s/%s'%(SERVER_HOST,GENREFLE))
        
        PROPERTIES.setProperty('SERVER_HOST',SERVER_HOST)
        PROPERTIES.setProperty('M3U_URL'  ,'http://%s/%s'%(SERVER_HOST,M3UFLE))
        PROPERTIES.setProperty('XMLTV_URL','http://%s/%s'%(SERVER_HOST,XMLTVFLE))
        PROPERTIES.setProperty('GENRE_URL','http://%s/%s'%(SERVER_HOST,GENREFLE))
        log('global: chkDiscovery, isClient = %s, server = %s'%(CLIENT,SERVER_HOST))
    return CLIENT

def getIdle():
    idleTime  = getIdleTime()
    idleState = (idleTime > 0)
    if (idleTime == 0 or idleTime <= 5): log("globals: getIdle, idleState = %s, idleTime = %s"%(idleState,idleTime))
    return idleState,idleTime
    
        
def getIdleTime():
    try: return (int(xbmc.getGlobalIdleTime()) or 0)
    except: #Kodi raises error after sleep.
        log('globals: getIdleTime, Kodi waking up from sleep...')
        return 0
 
def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text
                   
def unquote(text):
    return urllib.parse.unquote(text)
    
def quote(text):
    return urllib.parse.quote(text)
      
def splitYear(label):
    try:
        match = re.compile('(.*) \((.*)\)', re.IGNORECASE).search(label)
        if match:
            if match.group(2): return match.groups()
    except: pass
    return label, None
   
def getLabel(item):
    label = (item.get('name','') or item.get('label','') or item.get('showtitle','') or item.get('title',''))
    if not label: return ''
    label, year = splitYear(label)
    year = (item.get('year','') or year)
    if year: return '%s (%s)'%(label, year)
    return label
    
def dumpJSON(item, idnt=None, sortkey=True):
    try: 
        if not item:
            return ''
        elif hasattr(item, 'read'):
            return json.dump(item, indent=idnt, sort_keys=sortkey)
        elif not isinstance(item,str):
            return json.dumps(item, indent=idnt, sort_keys=sortkey)
        elif isinstance(item,str):
            return item
    except Exception as e: log("globals: dumpJSON failed! %s\n%s"%(e,item), xbmc.LOGERROR)
    return ''
    
def loadJSON(item):
    try: 
        if not item:
            return {}
        elif hasattr(item, 'read'):
            return json.load(item)
        elif isinstance(item,str):
            return json.loads(item)
        elif isinstance(item,dict):
            return item
    except Exception as e: log("globals: loadJSON failed! %s"%(e), xbmc.LOGERROR)
    return {}#except json.decoder.JSONDecodeError:,ValueError:

def sendJSON(command):
    log('globals: sendJSON, command = %s'%(command))
    return loadJSON(xbmc.executeJSONRPC(command))

def installAddon(id, silent=False):
    if hasAddon(id):
        if not addonEnabled(id): toggleADDON(id)
    else:
        xbmc.executebuiltin('InstallAddon("%s")'%(id))
        if not silent: Dialog().notificationDialog('%s %s...'%(LANGUAGE(30193),id))

def addonEnabled(id):
    return xbmc.getCondVisibility("System.AddonIsEnabled(%s)"%id)

def getPluginMeta(id):
    try:
        if id.startswith(('plugin://','resource://')):
            id =  splitall(id.replace('plugin://','').replace('resource://','')).strip()
        pluginID = xbmcaddon.Addon(id)
        meta = {'type':pluginID.getAddonInfo('type'),'label':pluginID.getAddonInfo('name'),'name':pluginID.getAddonInfo('name'), 'version':pluginID.getAddonInfo('version'), 'path':pluginID.getAddonInfo('path'), 'author':pluginID.getAddonInfo('author'), 'icon':pluginID.getAddonInfo('icon'), 'fanart':pluginID.getAddonInfo('fanart'), 'id':pluginID.getAddonInfo('id'), 'description':(pluginID.getAddonInfo('description') or pluginID.getAddonInfo('summary'))}
        log('globals: getPluginMeta, plugin meta = %s'%(meta))
        return meta
    except Exception as e: log("globals: getPluginMeta, Failed! %s"%(e), xbmc.LOGERROR)
    return {}

def toggleADDON(id, state=True, reverse=False):
    log('globals: toggleADDON, id = %s, state = %s, reverse = %s'%(id,state,reverse))
    sendJSON('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":%s}, "id": 1}'%(id,str(state).lower()))
    if reverse:
        if id == ADDON_ID: 
            xbmc.executebuiltin("AlarmClock(Re-enable,%s(%s),00:04)"%({False:'EnableAddon',True:'DisableAddon'}[state],id))
        else: 
            xbmc.sleep(PROMPT_DELAY)
            toggleADDON(id, not bool(state))
    
def getPlugin(id=PVR_CLIENT):
    try: return xbmcaddon.Addon(id)
    except: # backend disabled?
        toggleADDON(id)
        xbmc.sleep(2000)
        try:    return xbmcaddon.Addon(id)
        except: return None

def chkRequiredSettings():
    funcs = [chkPVR,chkMGR]
    for func in funcs: func()

def chkMGR():
    return chkPluginSettings(PVR_MANAGER, MGR_SETTINGS)

def chkPVR():
    return chkPluginSettings(PVR_CLIENT, getPVR_SETTINGS())

def chkPluginSettings(id, values):
    log('globals: chkPluginSettings, id = %s'%(id))
    addon = getPlugin(id)
    if addon  is None: return Dialog().notificationDialog(LANGUAGE(30217)%id)
    for setting, value in values.items():
        if not str(addon.getSetting(setting)) == str(value): 
            return setPlugin(id,values,SETTINGS.getSettingBool('Enable_Config'))
    return True
    
def setPVR():
    return setPlugin(PVR_CLIENT,getPVR_SETTINGS())
    
def setPlugin(id,values,override=False):
    log('globals: setPlugin')
    if not override:
        if not Dialog().yesnoDialog('%s ?'%(LANGUAGE(30012)%(getPluginMeta(id).get('name','')))): return
    try:
        addon = getPlugin(id)
        if addon  is None: return False
        for setting, value in values.items(): 
            addon.setSetting(setting, value)
    except: return Dialog().notificationDialog(LANGUAGE(30049)%(id))
    if override: return True
    return True
    
def brutePVR(override=False):
    if (xbmc.getCondVisibility("Pvr.IsPlayingTv") or xbmc.getCondVisibility("Pvr.IsPlayingRadio")): return
    elif not override:
        if not Dialog().yesnoDialog('%s ?'%(LANGUAGE(30065)%(getPluginMeta(PVR_CLIENT).get('name','')))): return
    toggleADDON(PVR_CLIENT,False,reverse=True)
    return True
    
def refreshMGR():
    if getPlugin(PVR_MANAGER):
        xbmc.executebuiltin('RunScript(service.iptv.manager,refresh)')

def chkResources(silent=True):
    log('globals: chkResources, silent = %s'%(silent)) 
    chkRepo = [hasAddon(repo) for repo in ADDON_REPOSITORY]
    if True in chkRepo:
        params  = ['Resource_Logos','Resource_Ratings','Resource_Bumpers','Resource_Commericals','Resource_Trailers']
        missing = [addon for param in params for addon in SETTINGS.getSetting(param).split(',') if not hasAddon(addon)]
        for addon in missing:
            installAddon(addon, silent)
            if xbmc.Monitor().waitForAbort(15): break
    elif not silent: 
        Dialog().notificationDialog(LANGUAGE(30307)%(ADDON_NAME))



























def chkFiles():
    ...
# not FileAccess.exists(getUserFilePath(M3UFLE)),
# not FileAccess.exists(getUserFilePath(XMLTVFLE)),
# not FileAccess.exists(getUserFilePath(CHANNELFLE)),
# not FileAccess.exists(getUserFilePath(LIBRARYFLE))]
    

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

def hasVersionChanged():
    if ADDON_VERSION != (SETTINGS.getCacheSetting('lastVersion') or 'v.0.0.0'):
        SETTINGS.setCacheSetting('lastVersion',ADDON_VERSION)
        return True

def cleanAbandonedLocks():
    ... #todo remove .locks
     
def roundTimeDown(thetime, offset=30): # round the given time down to the nearest
    n = datetime.datetime.fromtimestamp(thetime)
    delta = datetime.timedelta(minutes=offset)
    if n.minute > (offset-1): n = n.replace(minute=offset, second=0, microsecond=0)
    else: n = n.replace(minute=0, second=0, microsecond=0)
    return time.mktime(n.timetuple())
    # if n.minute < (offset): n = n.replace(minute=0, second=0, microsecond=0)
    # else: n = n.replace(minute=offset, second=0, microsecond=0)
    # return time.mktime(n.timetuple())
    
def roundTimeUp(thetime, offset=30): # round the given time up to the nearest
    n = datetime.datetime.fromtimestamp(thetime)
    delta = datetime.timedelta(minutes=offset)
    n = (n + (datetime.datetime.min - n) % delta)
    return time.mktime(n.timetuple())
    
def roundupDIV(p, q):
    try:
        d, r = divmod(p, q)
        if r: d += 1
        return d
    except ZeroDivisionError: 
        return 1

def pagination(list, end):
    for start in range(0, len(list), end):
        yield seq[start:start+end]

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def padLST(lst, targetLen):
    if len(lst) == 0: return lst
    lst.extend(list([random.choice(lst) for n in range(targetLen - len(lst))]))
    return lst[:targetLen]

def percentDiff(org, new):
    try: return (abs(float(org) - float(new)) / float(new)) * 100.0
    except ZeroDivisionError: return 0

def moveUser(oldFolder, newFolder):
    if isClient(): return
    log('globals: moveUser, oldFolder = %s, newFolder = %s'%(oldFolder,newFolder))
    files = [M3UFLE,XMLTVFLE,GENREFLE]
    dia   = Dialog().progressDialog(message='Preparing to move files...')#todo move to string.po
    FileAccess.copy(os.path.join(oldFolder,'logos'),os.path.join(newFolder,'logos'))
    for idx, file in enumerate(files):
        pnt = int(((idx+1)*100)//len(files))
        dia = Dialog().progressDialog(pnt, dia, message='%s %s'%('Moving',file))#todo move to string.po
        oldFilePath = os.path.join(oldFolder,file)
        newFilePath = os.path.join(newFolder,file)
        if FileAccess.exists(oldFilePath):
            dia = Dialog().progressDialog(pnt, dia, message='%s %s'%('Moving',file))#todo move to string.po
            if FileAccess.copy(oldFilePath,newFilePath):
                dia = Dialog().progressDialog(pnt, dia, message='%s %s %s'%('Moving',file,LANGUAGE(30053)))#todo move to string.po
                continue
        dia = Dialog().progressDialog(pnt, dia, message='Moving %s failed!'%(file))#todo move to string.po
    return True
    
def escapeDirJSON(path):
    mydir = path
    if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
    return mydir

def splitall(plugin):
    plugin = [plugin]
    while not xbmc.Monitor().abortRequested():
        last   = plugin
        plugin = os.path.split(plugin[0])
        if not plugin[0]: break
    return last[0]
    
def updateIPTVManager():
    if getPluginMeta(PVR_MANAGER).get('version') == "0.2.3a+matrix.1":
        xbmc.executebuiltin("RunScript(%s,update)"%(PVR_MANAGER))

def showReadme():
    def convertMD2TXT(md):
        markdown = (re.sub(r'(\[[^][]*]\([^()]*\))|^(#+)(.*)', lambda x:x.group(1) if x.group(1) else "[COLOR=cyan][B]{1} {0} {1}[/B][/COLOR]".format(x.group(3),('#'*len(x.group(2)))), md, flags=re.M))
        markdown = (re.sub(r'`(.*?)`', lambda x:x.group(1) if not x.group(1) else '"[I]{0}[/I]"'.format(x.group(1)), markdown, flags=re.M))
        markdown = re.sub(r'\[!\[(.*?)\]\((.*?)\)]\((.*?)\)', lambda x:x.group(1) if not x.group(1) else '[B]{0}[/B]\n[I]{1}[/I]'.format(x.group(1),x.group(3)), markdown, flags=re.M)
        markdown = re.sub(r'\[(.*?)\]\((.*?)\)', lambda x:x.group(1) if not x.group(2) else '- [B]{0}[/B]\n[I]{1}[/I]'.format(x.group(1),x.group(2)), markdown, flags=re.M)
        markdown = re.sub(r'\[(.*?)\]\((.*?)\)', lambda x:x.group(1) if not x.group(1) else '- [B]{0}[/B]'.format(x.group(1)), markdown, flags=re.M)
        markdown = '\n'.join(list(filter(lambda filelist:filelist[:2] not in ['![','[!','!.','!-','ht'], markdown.split('\n'))))
        return markdown
        
    with busy_dialog(): 
        Dialog().textviewer(convertMD2TXT(xbmcvfs.File(README_FLE).read()), heading=(LANGUAGE(30273)%(ADDON_NAME,ADDON_VERSION)),usemono=True,usethread=True)

def chkVersion():
    if hasVersionChanged():
        showChangelog()

def showChangelog():
    def addColor(text):
        text = text.replace('-Added'      ,'[COLOR=green][B]-Added:[/B][/COLOR]')
        text = text.replace('-Optimized'  ,'[COLOR=yellow][B]-Optimized:[/B][/COLOR]')
        text = text.replace('-Improved'   ,'[COLOR=yellow][B]-Improved:[/B][/COLOR]')
        text = text.replace('-Refactored' ,'[COLOR=yellow][B]-Refactored:[/B][/COLOR]')
        text = text.replace('-Tweaked'    ,'[COLOR=yellow][B]-Tweaked:[/B][/COLOR]')
        text = text.replace('-Updated'    ,'[COLOR=yellow][B]-Updated:[/B][/COLOR]')
        text = text.replace('-Changed'    ,'[COLOR=yellow][B]-Changed:[/B][/COLOR]')
        text = text.replace('-Notice'     ,'[COLOR=orange][B]-Notice:[/B][/COLOR]')
        text = text.replace('-Fixed'      ,'[COLOR=orange][B]-Fixed:[/B][/COLOR]')
        text = text.replace('-Removed'    ,'[COLOR=red][B]-Removed:[/B][/COLOR]')
        text = text.replace('-Important'  ,'[COLOR=red][B]-Important:[/B][/COLOR]')
        text = text.replace('-Warning'    ,'[COLOR=red][B]-Warning:[/B][/COLOR]')
        return text
        
    with busy_dialog(): 
        Dialog().textviewer(addColor(xbmcvfs.File(CHANGELOG_FLE).read()), heading=(LANGUAGE(30134)%(ADDON_NAME,ADDON_VERSION)),usemono=True,usethread=True)

def loadGuide():
    xbmc.executebuiltin("Dialog.Close(all)")
    xbmc.executebuiltin("ActivateWindow(TVGuide,pvr://channels/tv/%s,return)"%(quote(ADDON_NAME)))

def openAddonSettings(ctl=(0,1),id=ADDON_ID):
    log('openAddonSettings, ctl = %s, id = %s'%(ctl,id))
    ## ctl[0] is the Category (Tab) offset (0=first, 1=second, 2...etc)
    ## ctl[1] is the Setting (Control) offset (1=first, 2=second, 3...etc)# addonId is the Addon ID
    ## Example: openAddonSettings((2,3),'plugin.video.name')
    ## This will open settings dialog focusing on fourth setting (control) inside the third category (tab)
    xbmc.sleep(100)
    xbmc.executebuiltin('Addon.OpenSettings(%s)'%id)
    xbmc.sleep(100)
    xbmc.executebuiltin('SetFocus(%i)'%(ctl[0]-100))
    xbmc.sleep(100)
    xbmc.executebuiltin('SetFocus(%i)'%(ctl[1]-80))
    return True
    

def setJsonSettings():
    for key in JSON_SETTINGS.keys():
        JSON_SETTINGS[key]

def strpTime(datestring, format='%Y-%m-%d %H:%M:%S'): #convert json pvr datetime string to datetime obj, thread safe!
    try:              return datetime.datetime.strptime(datestring, format)
    except TypeError: return datetime.datetime.fromtimestamp(time.mktime(time.strptime(datestring, format)))
    except:           return ''
        
def getLocalTime():
    offset = (datetime.datetime.utcnow() - datetime.datetime.now())
    return time.time() + offset.total_seconds() #returns timestamp

def makeTimestamp(dateOBJ):
    return time.mktime(dateOBJ)

def isHD(item):
    if 'isHD' in item: return item['isHD']
    elif 'streamdetails' in item: 
        item = item.get('streamdetails',{})
        if 'video' in item and len(item.get('video')) > 0:
            videowidth  = int(item['video'][0]['width']  or '0')
            videoheight = int(item['video'][0]['height'] or '0')
            if videowidth >= 1280 and videoheight >= 720: return True  
    return False

def is3D(item):
    if 'is3D' in item: return item['is3D']
    if 'streamdetails' in item: item = item.get('streamdetails',{})
    if 'video' in item and item.get('video') != [] and len(item.get('video')) > 0:
        stereomode = (item['video'][0]['stereomode'] or '')
        if len(stereomode) > 0: return True
    return False
   
def stripNumber(label):
    return re.sub(r'\d+','',label)
    
def stripRegion(label):
    try:
        match = re.compile('(.*) \((.*)\)', re.IGNORECASE).search(label)
        if match:
            if match.group(1): 
                return match.group(1)
    except: pass
    return label

def getThumb(item,opt=0): #unify thumbnail artwork
    keys = {0:['landscape','fanart','thumb','thumbnail','poster','clearlogo','logo','folder','icon'],
            1:['poster','clearlogo','logo','landscape','fanart','thumb','thumbnail','folder','icon']}[opt]
    for key in keys:
        art = (item.get('art',{}).get('album.%s'%(key),'')       or 
               item.get('art',{}).get('albumartist.%s'%(key),'') or 
               item.get('art',{}).get('artist.%s'%(key),'')      or 
               item.get('art',{}).get('season.%s'%(key),'')      or 
               item.get('art',{}).get('tvshow.%s'%(key),'')      or 
               item.get('art',{}).get(key,'')                    or
               item.get(key,''))
        if art: return art
    return {0:FANART,1:COLOR_LOGO}[opt]

def findItemsInLST(items, values, item_key='getLabel', val_key='', index=True):
    log("findItemsInLST, values = %s, item_key = %s, val_key = %s, index = %s"%(len(values), item_key, val_key, index))
    if not values:
        return [-1]
           
    matches = []
    def match(fkey,fvalue):
        if fkey.lower() == fvalue.lower():
            matches.append(idx if index else item)
                    
    for value in values:
        if isinstance(value,dict): 
            value = value.get(val_key,'')
            
        for idx, item in enumerate(items): 
            if isinstance(item,xbmcgui.ListItem): 
                if item_key == 'getLabel':  
                    match(item.getLabel() ,value)
                elif item_key == 'getLabel2': 
                    match(item.getLabel2(),value)
            elif isinstance(item,dict):       
                match(item.get(item_key,''),value)
            else: 
                match(item,value)
    log("findItemsInLST, matches = %s"%(matches))
    return matches

def setDictLST(lst):
    sLST = set([dumpJSON(e) for e in lst])
    return [loadJSON(e) for e in sLST]

def diffLSTDICT(old, new):
    sOLD = set([dumpJSON(e) for e in old])
    sNEW = set([dumpJSON(e) for e in new])
    sDIFF = sOLD.symmetric_difference(sNEW)
    return setDictLST([loadJSON(e) for e in sDIFF])

def cleanLabel(text):
    text = re.sub('\[COLOR=(.+?)\]', '', text)
    text = re.sub('\[/COLOR\]', '', text)
    text = text.replace("[B]",'').replace("[/B]",'')
    text = text.replace("[I]",'').replace("[/I]",'')
    return text.replace(":",'')

def isPseudoTV(condition='VideoPlayer'):
    isPseudoTV = hasChannelData(condition) #condition set only while playing
    log('globals: isPseudoTV = %s'%(isPseudoTV))
    return isPseudoTV

def hasChannelData(condition='ListItem'):
    return getWriterfromString(condition).get('citem',{}).get('number',-1) > 0

def getWriterfromString(condition='ListItem'):
    return getWriter(xbmc.getInfoLabel('%s.Writer'%(condition)))
    
def getChannelID(name, path, number):
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)))
    return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:32]).decode(DEFAULT_ENCODING),slugify(ADDON_NAME))

def getWriter(text):
    if isinstance(text, list): text = text[0]
    if isinstance(text, str):
        writer = re.search(r'\[COLOR item=\"(.+?)\"]\[/COLOR]', text)
        if writer: return loadJSON(decodeString(writer.group(1)))
    return {}

def setWriter(writer, fileItem):
    return '%s [COLOR item="%s"][/COLOR]'%(writer,encodeString(dumpJSON(fileItem)))

def encodeString(text):
    base64_bytes = base64.b64encode(text.encode(DEFAULT_ENCODING))
    return base64_bytes.decode(DEFAULT_ENCODING)

def decodeString(base64_bytes):
    message_bytes = base64.b64decode(base64_bytes.encode(DEFAULT_ENCODING))
    return message_bytes.decode(DEFAULT_ENCODING)

def getGroups(add=False):
    if SETTINGS.getSetting('User_Groups'): GROUP_TYPES.extend(SETTINGS.getSetting('User_Groups').split('|'))
    if add: GROUP_TYPES.insert(0,'+Add')
    return sorted(set(GROUP_TYPES))

def saveURL(url, file):
    try:
        contents = urllib.request.urlopen(url).read()
        fle = FileAccess.open(file, 'w')
        fle.write(contents)
        fle.close()
    except Exception as e: 
        log("saveURL, Failed! %s"%e, xbmc.LOGERROR)
    
def interleave(*args): #interleave multi-lists, while preserving order
    try:
        iters = list(map(iter, args))
        while not xbmc.Monitor().abortRequested() and iters:
            it = random.choice(iters)
            try: yield next(it)
            except StopIteration:
                iters.remove(it)
    except Exception as e: 
        log("interleave, Failed! %s"%(e), xbmc.LOGERROR)
        yield list(chain.from_iterable(zip_longest(*args)))[0]

def isStack(path,file=None):
    if file is not None: 
        return path.startswith('stack://%s'%(file))
    else:
        return path.startswith('stack://')

def hasStack(path,file=None):
    if isStack(path,file): return splitStacks(path)
    return None

def splitStacks(path): #split stack for indv. files.
    log('splitStacks, path = %s'%(path))
    return (path.split('stack://')[1]).split(' , ')
                                      
def stripStack(path, file): #strip pre-rolls from stack, return file.
    log('stripStack, path = %s, file = %s'%(path,file))
    paths = path.split(' , ')
    for idx, path in enumerate(paths.copy()):
        if not path == file: paths.pop(idx)
        elif path == file: break
    return paths
    
def buildStack(paths):
    stack = 'stack://%s'
    return stack%(' , '.join(paths))
    
def cleanMPAA(mpaa):
    mpaa = mpaa.lower()
    if ':'      in mpaa: mpaa = re.split(':',mpaa)[1]       #todo prop. regex
    if 'rated ' in mpaa: mpaa = re.split('rated ',mpaa)[1]  #todo prop. regex
    #todo regex, detect other region rating formats
    # re.compile(':(.*)', re.IGNORECASE).search(text))
    text = mpaa.upper()
    try:
        text = re.sub('/ US', ''  , text)
        text = re.sub('Rated ', '', text)
        return text.strip()
    except: 
        return mpaa.strip()
                
def cleanResourcePath(path):
    if path.startswith('resource://'):
        return (path.replace('resource://','special://home/addons/'))
    return path

def hasSubtitle():
    state = xbmc.getCondVisibility('VideoPlayer.HasSubtitles')
    log('globals: hasSubtitle = %s'%(state))
    return state

def isSubtitle():
    state = xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled')
    log('globals: isSubtitle = %s'%(state))
    return state

def isPlaylistRandom():
    return xbmc.getInfoLabel('Playlist.Random').lower() == 'on' # Disable auto playlist shuffling if it's on
    
def isPlaylistRepeat():
    return xbmc.getInfoLabel('Playlist.IsRepeat').lower() == 'true' # Disable auto playlist repeat if it's on #todo

def titleLabels(list):
     return [str(item).title() for item in list]

def getChannelSuffix(name, type):
    if name.endswith((LANGUAGE(30155),LANGUAGE(30157),LANGUAGE(30156),LANGUAGE(30177))): return name  
    elif type == LANGUAGE(30004): suffix = LANGUAGE(30155) #TV
    elif type == LANGUAGE(30097): suffix = LANGUAGE(30157) #Music
    elif type == LANGUAGE(30005): suffix = LANGUAGE(30156) #Movies
    else: return name
    return '%s %s'%(name,suffix)
 
def cleanChannelSuffix(name, type):
    if   type == LANGUAGE(30004): name = name.split(' %s'%LANGUAGE(30155))[0]#TV
    elif type == LANGUAGE(30097): name = name.split(' %s'%LANGUAGE(30157))[0]#Music
    elif type == LANGUAGE(30005): name = name.split(' %s'%LANGUAGE(30156))[0]#Movie
    return name
            
def unquoteImage(imagestring):
    # imagestring = http://192.168.0.53:8080/image/image%3A%2F%2Fsmb%253a%252f%252f192.168.0.51%252fTV%252fCosmos%2520A%2520Space-Time%2520Odyssey%252fposter.jpg%2F
    # extracted thumbnail images need to keep their 'image://' encoding
    if imagestring.startswith('image://') and not imagestring.startswith(('image://video', 'image://music')):
        return unquote(imagestring[8:-1])
    return imagestring

def quoteImage(imagestring):
     # imagestring = http://192.168.0.53:8080/image/image%3A%2F%2Fsmb%253a%252f%252f192.168.0.51%252fTV%252fCosmos%2520A%2520Space-Time%2520Odyssey%252fposter.jpg%2F                                                   
    if imagestring.startswith('image://'): return imagestring
    # Kodi goes lowercase and doesn't encode some chars
    result = 'image://{0}/'.format(quote(imagestring, '()!'))
    result = re.sub(r'%[0-9A-F]{2}', lambda mo: mo.group().lower(), result)
    return result
        

# def syncCustom(): #todo sync user created smartplaylists/nodes for multi-room.
    # for type in ['library','playlists']:
        # for media in ['video','music','mixed']:
            # path  = 'special://userdata/%s/%s/'%(type,media)
            # files = FileAccess.listdir(path)[1]
            # for file in files:
                # orgpath  = os.path.join(path,file)
                # copypath = os.path.join(getUserFilePath(),'cache','playlists',type,media,file)
                # self.log('copyNodes, orgpath = %s, copypath = %s'%(orgpath,copypath))
                # yield FileAccess.copy(orgpath, copypath)

