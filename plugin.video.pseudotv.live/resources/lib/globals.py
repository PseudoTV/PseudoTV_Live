#   Copyright (C) 2020 Lunatixz
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
import json, codecs, collections, uuid, subprocess

from kodi_six                  import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode
from itertools                 import repeat, cycle, chain, zip_longest
from six.moves                 import urllib
from contextlib                import contextmanager
from xml.dom.minidom           import parse, parseString, Document
from xml.etree.ElementTree     import ElementTree, Element, SubElement, tostring, XMLParser
from resources.lib.fileaccess  import FileAccess, FileLock
from resources.lib.kodi        import Settings, Properties, Dialog
from resources.lib.cache       import cacheit
from resources.lib.events      import logit
from operator                  import itemgetter
from collections               import deque
from fuzzywuzzy                import process as FuzzyProcess

try:
    from multiprocessing import Thread, Queue, Empty, PriorityQueue
    Queue() # importing Queue does not raise importError on android, call directly.
except:
    from threading import Thread
    from queue     import Queue, Empty, PriorityQueue

PY3 = sys.version_info[0] == 3
if PY3: 
    basestring = str
    unicode = str
    
# Plugin Info
ADDON_ID            = 'plugin.video.pseudotv.live'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE            = REAL_SETTINGS.getLocalizedString
SETTINGS            = Settings()
PROPERTIES          = Properties()

OVERLAY_FLE         = "%s.overlay.xml"%(ADDON_ID)
README_FLE          = os.path.join(ADDON_PATH,'readme.md')
CHANGELOG_FLE       = os.path.join(ADDON_PATH,'changelog.txt')
CHANNELFLE_DEFAULT  = os.path.join(ADDON_PATH,'channels.json')

LIBRARYFLE_DEFAULT  = os.path.join(ADDON_PATH,'library.json')
GENREFLE_DEFAULT    = os.path.join(ADDON_PATH,'genres.xml')
GROUPFLE_DEFAULT    = os.path.join(ADDON_PATH,'groups.xml')
PROVIDERFLE_DEFAULT = os.path.join(ADDON_PATH,'providers.xml')
SETTINGS_FLE        = os.path.join(SETTINGS_LOC,'settings.xml')
CHANNELFLE_BACKUP   = os.path.join(SETTINGS_LOC,'channels.backup')
CHANNELFLE_RESTORE  = os.path.join(SETTINGS_LOC,'channels.restore')

VIDEO_EXTS          = xbmc.getSupportedMedia('video').split('|')
MUSIC_EXTS          = xbmc.getSupportedMedia('music').split('|')
IMAGE_EXTS          = xbmc.getSupportedMedia('picture').split('|')

IMAGE_LOC           = os.path.join(ADDON_PATH,'resources','images')
MEDIA_LOC           = os.path.join(ADDON_PATH,'resources','skins','default','media')
COLOR_LOGO          = os.path.join(MEDIA_LOC,'logo.png')
MONO_LOGO           = os.path.join(MEDIA_LOC,'wlogo.png')
HOST_LOGO           = 'https://github.com/PseudoTV/PseudoTV_Live/raw/master/plugin.video.pseudotv.live/resources/skins/default/media/logo.png'

PVR_URL             = 'plugin://{addon}/?mode=play&name={name}&id={id}&radio={radio}.pvr'
VOD_URL             = 'plugin://{addon}/?mode=vod&name={name}&id={id}&channel={channel}&radio={radio}.pvr'

ADDON_REPOSITORY    = 'repository.pseudotv'
PVR_CLIENT          = 'pvr.iptvsimple'
PVR_MANAGER         = 'service.iptv.manager'
LANG                = 'en' #todo
DTFORMAT            = '%Y%m%d%H%M%S'
DTZFORMAT           = '%Y%m%d%H%M%S +%z'
DEFAULT_ENCODING    = 'utf-8'

MAX_IMPORT          = 5
EPG_HRS             = 10800 #3hr in Secs., Min. EPG guidedata
RADIO_ITEM_LIMIT    = 250
CLOCK_SEQ           = 70420
UPDATE_OFFSET       = 10800 #3hr in secs.
LIBRARY_OFFSET      = 3600
RECOMMENDED_OFFSET  = 900   #15mins in secs.
PREDEFINED_OFFSET   = ((SETTINGS.getSettingInt('Max_Days') * 60) * 60)
UPDATE_WAIT         = 3600  #1hr in secs.
AUTOTUNE_LIMIT      = 3     #auto items per type.
CHANNEL_LIMIT       = 999   #hard limit, do not exceed!
OVERLAY_DELAY       = 15    #secs
CHAN_TYPES          = [LANGUAGE(30002),LANGUAGE(30003),LANGUAGE(30004),LANGUAGE(30005),LANGUAGE(30007),LANGUAGE(30006),LANGUAGE(30080),LANGUAGE(30026),LANGUAGE(30097),LANGUAGE(30033)]#Limit is 10
GROUP_TYPES         = ['Addon', 'Directory', 'Favorites', 'Mixed', LANGUAGE(30006), 'Mixed Movies', 'Mixed TV', LANGUAGE(30005), LANGUAGE(30007), 'Movies', 'Music', LANGUAGE(30097), 'Other', 'PVR', 'Playlist', 'Plugin', 'Radio', LANGUAGE(30026), 'Smartplaylist', 'TV', LANGUAGE(30004), LANGUAGE(30002), LANGUAGE(30003), 'UPNP', 'IPTV']
BCT_TYPES           = ['bumpers','ratings','commercials','trailers']
PRE_ROLL            = ['bumpers','ratings']
POST_ROLL           = ['commercials','trailers']

# jsonrpc
ART_PARAMS          = ["thumb","icon","poster","fanart","banner","landscape","clearart","clearlogo"]

#per channel rule limit
RULES_PER_PAGE                   = 10
#builder
RULES_ACTION_CHANNEL_CREATION    = 1 
RULES_ACTION_START               = 2
RULES_ACTION_CHANNEL_START       = 3
RULES_ACTION_CHANNEL_JSON        = 4
RULES_ACTION_CHANNEL_ITEM        = 5
RULES_ACTION_CHANNEL_LIST        = 6
RULES_ACTION_CHANNEL_STOP        = 7
RULES_ACTION_CHANNEL_PRE_TIME    = 8
RULES_ACTION_CHANNEL_POST_TIME   = 9
RULES_ACTION_STOP                = 10
#player
RULES_ACTION_PLAYBACK            = 11
RULES_ACTION_PLAYER              = 12
#overlay
RULES_ACTION_OVERLAY             = 20

#overlay globals
NOTIFICATION_CHECK_TIME          = 15.0 #seconds
NOTIFICATION_TIME_REMAINING      = 900  #seconds
NOTIFICATION_PLAYER_PROG         = 85   #percent
NOTIFICATION_DISPLAY_TIME        = 30   #seconds
CHANNELBUG_CHECK_TIME            = 15.0 #seconds

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

def log(msg, level=xbmc.LOGDEBUG):
    if not SETTINGS.getSetting('Enable_Debugging') == "true" and level != xbmc.LOGERROR: return
    if not isinstance(msg,basestring): msg = str(msg)
    if level == xbmc.LOGERROR: msg = '%s\n%s'%((msg),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)

def getUserFilePath(file=None):
    path = SETTINGS.getSetting('User_Folder')
    if file: return os.path.join(path,file)
    else: return path
  
def unquote(text):
    return urllib.parse.unquote(text)
    
def quote(text):
    return urllib.parse.quote(text)

PAGE_LIMIT       = SETTINGS.getSettingInt('Page_Limit')
MIN_ENTRIES      = int(PAGE_LIMIT//2)
LOGO             = (COLOR_LOGO if bool(SETTINGS.getSettingInt('Color_Logos')) else MONO_LOGO).replace(ADDON_PATH,'special://home/addons/%s/'%(ADDON_ID)).replace('\\','/')

USER_LOC         = getUserFilePath()
LOCK_LOC         = USER_LOC
XMLTVFLE         = '%s.xml'%('pseudotv')
M3UFLE           = '%s.m3u'%('pseudotv')

CHANNELFLE       = 'channels.json'
LIBRARYFLE       = 'library.json'
GENREFLE         = 'genres.xml'
TVGROUPFLE       = 'tv_groups.xml'
RADIOGROUPFLE    = 'radio_groups.xml'
PROVIDERFLE      = 'providers.xml'

CACHE_LOC        = os.path.join(USER_LOC ,'cache')
PLS_LOC          = os.path.join(CACHE_LOC,'playlists')
LOGO_LOC         = os.path.join(CACHE_LOC,'logos')

TEMP_LOC         = os.path.join(SETTINGS_LOC,'temp')
BACKUP_LOC       = os.path.join(SETTINGS_LOC,'backup')

MGR_SETTINGS     = {'refresh_interval':'1',
                    'iptv_simple_restart':'false'}
                    
PVR_SETTINGS     = {'m3uRefreshMode':'1','m3uRefreshIntervalMins':'10','m3uRefreshHour':'0',
                    'logoPathType':'0','logoPath':LOGO_LOC,
                    'm3uPathType':'0','m3uPath':getUserFilePath(M3UFLE),
                    'epgPathType':'0','epgPath':getUserFilePath(XMLTVFLE),
                    'genresPathType':'0','genresPath':getUserFilePath(GENREFLE),
                    # 'tvGroupMode':'0','customTvGroupsFile':getUserFilePath(TVGROUPFLE),#todo
                    # 'radioGroupMode':'0','customRadioGroupsFile':getUserFilePath(RADIOGROUPFLE),#todo
                    'enableProviderMappings':'true','defaultProviderName':ADDON_NAME,'providerMappingFile':getUserFilePath(PROVIDERFLE),#todo
                    'useEpgGenreText':'true', 'logoFromEpg':'1',
                    'catchupEnabled':'true','allChannelsCatchupMode':'0',
                    'numberByOrder':'false','startNum':'1',
                    'epgTimeShift':'0','epgTSOverride':'false',
                    'useFFmpegReconnect':'true','useInputstreamAdaptiveforHls':'true'}
                    
JSON_SETTINGS    = {'pvrmanager.preselectplayingchannel':'true',
                    'pvrmanager.syncchannelgroups':'true',
                    'pvrmanager.backendchannelorder':'true',
                    'pvrmanager.usebackendchannelnumbers':'true',
                    # 'pvrmenu.iconpath':'',
                    # 'pvrplayback.switchtofullscreenchanneltypes':1,
                    # 'pvrplayback.confirmchannelswitch':'true',
                    # 'epg.selectaction':2,
                    # 'epg.epgupdate':120,
                    'pvrmanager.startgroupchannelnumbersfromone':'false'}


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
        try: yield
        finally: 
            setBusy(False)

@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try: yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

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
 
def getRandomPage(limit,total=50):
    page = random.randrange(0, total, limit)
    return page, page+limit
  
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

def initDirs():
    dirs = [CACHE_LOC,LOGO_LOC,PLS_LOC,LOCK_LOC]
    [FileAccess.makedirs(dir) for dir in dirs if not FileAccess.exists(dir)]
    return True

def moveUser(oldFolder, newFolder): #todo finish
    if PROPERTIES.getPropertyBool('isClient'): return
    log('globals: moveUser, oldFolder = %s, newFolder = %s'%(oldFolder,newFolder))
    MoveLST = [M3UFLE,XMLTVFLE,CHANNELFLE,LIBRARYFLE,GENREFLE,CACHE_LOC]
    if not Dialog().yesnoDialog('Centralized file location changed from\n%s to\%s move files?'%(oldFolder,newFolder)): return
    dia = Dialog().progressDialog(message='Preparing to move files...')
    for idx, file in enumerate(MoveLST):
        pnt = int(((idx+1)*100)//len(MoveLST))
        dia = Dialog().progressDialog(pnt, dia, message='Moving %s...'%(file))
        oldFilePath = os.path.join(oldFolder,file)
        newFilePath = os.path.join(newFolder,file)
        if FileAccess.exists(oldFilePath):
            if FileAccess.copy(oldFilePath,newFilePath):
                dia = Dialog().progressDialog(pnt, dia, message='Moving %s complete'%(file))
                continue
        dia = Dialog().progressDialog(pnt, dia, message='Moving %s failed!'%(file))
    return Dialog().notificationDialog(LANGUAGE(30053))

def dumpJSON(item, idnt=None, sortkey=True):
    try: 
        if not item:
            return ''
        elif hasattr(item, 'read'):
            return json.dump(item, indent=idnt, sort_keys=sortkey)
        elif not isinstance(item,basestring):
            return json.dumps(item, indent=idnt, sort_keys=sortkey)
        elif isinstance(item,basestring):
            return item
    except Exception as e: log("globals: dumpJSON failed! %s\n%s"%(e,item), xbmc.LOGERROR)
    return ''
    
def loadJSON(item):
    try: 
        if not item:
            return {}
        elif hasattr(item, 'read'):
            return json.load(item)
        elif isinstance(item,basestring):
            return json.loads(item)
        elif isinstance(item,dict):
            return item
    except Exception as e: log("globals: loadJSON failed! %s\n%s"%(e,item), xbmc.LOGERROR)
    return {}#except json.decoder.JSONDecodeError:,ValueError:
    
def sendJSON(command):
    log('globals: sendJSON, command = %s'%(command))
    return loadJSON(xbmc.executeJSONRPC(command))

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
    
def isSSD():
    #TODO DETECT SSD/FLASH
    return (USER_LOC)

def getIdleTime():
    try: return (int(xbmc.getGlobalIdleTime()) or 0)
    except: return 0 #Kodi raises error after sleep.

def isLegacyPseudoTV(): # legacy setting to disable/enable support in third-party applications. 
    return PROPERTIES.getEXTProperty('PseudoTVRunning') == "True"

def setLegacyPseudoTV(state):
    return PROPERTIES.setEXTProperty('PseudoTVRunning',state)

def setBusy(state):
    return PROPERTIES.setPropertyBool("BUSY.RUNNING",state)
    
def isBusy():
    return PROPERTIES.getPropertyBool("BUSY.RUNNING")

def isOverlay():
    return PROPERTIES.getPropertyBool('OVERLAY')

def isDialog():
    return PROPERTIES.getPropertyBool('isDialog')

def setDialog(state):
    return PROPERTIES.setPropertyBool('isDialog',state)

def doUtilities():
    param = PROPERTIES.getProperty('utilities')
    PROPERTIES.clearProperty('utilities')
    return param
    
def setUtilities(key):
    return PROPERTIES.setProperty('utilities',key)

def isRestartRequired():
    state = PROPERTIES.getPropertyBool('restartRequired')
    setRestartRequired(False)
    return state
        
def setRestartRequired(state=True):
    return PROPERTIES.setPropertyBool('restartRequired',state)
       
def isShutdownRequired():
    state = PROPERTIES.getPropertyBool('shutdownRequired')
    setServiceStop(False)
    return state
                 
def setServiceStop(state=True):
    return PROPERTIES.setPropertyBool('shutdownRequired',state)
       
def isSelectOpened():
    return PROPERTIES.getPropertyBool('selectOpened')
                 
def setSelectOpened(state=True):
    return PROPERTIES.setPropertyBool('selectOpened',state)
       
def isManagerRunning():
    return PROPERTIES.getPropertyBool('managerRunning')
    
def setManagerRunning(state=True):
    return PROPERTIES.setPropertyBool('managerRunning',state)
    
def isClient():
    return PROPERTIES.getPropertyBool('isClient')

def isPendingChange():
    return PROPERTIES.getPropertyBool('pendingChange')
    
def setPendingChange(state=True):
    return PROPERTIES.setPropertyBool('pendingChange',state)
    
def hasAutoTuned():
    return PROPERTIES.getPropertyBool('autotuned')
    
def setAutoTuned(state=True):
    return PROPERTIES.setPropertyBool('autotuned',state)
    
def hasAutotuned():
    return PROPERTIES.getPropertyBool('autotuned')
    
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
    
def hasVersionChanged(cleanStart=False):
    lastVersion = (SETTINGS.getCacheSetting('lastVersion') or 'v.0.0.0')
    if ADDON_VERSION != lastVersion:
        SETTINGS.setCacheSetting('lastVersion',ADDON_VERSION)
        showChangelog()

def chkUpdateTime(key, wait, lastUpdate=None):
    state = False
    def getValue(key):
        value = PROPERTIES.getProperty(key)
        if value: #todo debug property returning string tuple (1628009030, 1627922630, 347) !?
            if ', ' in value: value = value.split(', ')[1]
        else:
            value = SETTINGS.getCacheSetting(key)
        return (value or 0)
            
    epoch = time.time()
    if lastUpdate is None: lastUpdate = float(getValue(key))
    if (epoch >= (lastUpdate + wait)):
        PROPERTIES.setPropertyInt(key,int(epoch))
        SETTINGS.setCacheSetting(key,int(epoch))
        state = True
    log('chkUpdateTime, key = %s, lastUpdate = %s, update now = %s'%(key,lastUpdate,state))
    return state

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
        readme = convertMD2TXT(xbmcvfs.File(README_FLE).read())
        Dialog().textviewer(readme, heading=(LANGUAGE(30273)%(ADDON_NAME,ADDON_VERSION)),usemono=True)

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
        changelog = addColor(xbmcvfs.File(CHANGELOG_FLE).read())
        Dialog().textviewer(changelog, heading=(LANGUAGE(30134)%(ADDON_NAME,ADDON_VERSION)),usemono=True)

def loadGuide():
    xbmc.executebuiltin("Dialog.Close(all)")
    xbmc.executebuiltin("ActivateWindow(TVGuide,pvr://channels/tv/%s,return)"%(quote(ADDON_NAME)))

def openAddonSettings(ctl=(1,1),id=ADDON_ID):
    log('openAddonSettings, ctl = %s, id = %s'%(ctl,id))
    ## ctl[0] is the Category (Tab) offset (0=first, 1=second, 2...etc)
    ## ctl[1] is the Setting (Control) offset (0=first, 1=second, 2...etc)# addonId is the Addon ID
    ## Example: openAddonSettings((2,3),'plugin.video.name')
    ## This will open settings dialog focusing on fourth setting (control) inside the third category (tab)
    xbmc.executebuiltin('Addon.OpenSettings(%s)'%id)
    xbmc.sleep(500)
    xbmc.executebuiltin('SetFocus(%i)'%(ctl[0]+100))
    xbmc.sleep(100)
    xbmc.executebuiltin('SetFocus(%i)'%(ctl[1]+80))
    return True
   
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

def installAddon(id, silent=False):
    if hasAddon(id):
        if not addonEnabled(id): toggleADDON(id)
    else:
        xbmc.executebuiltin('InstallAddon("%s")'%(id))
        if not silent: Dialog().notificationDialog('%s %s...'%(LANGUAGE(30193),id))
 
def chkResources(silent=True):
    log('globals: chkResources, silent = %s'%(silent)) 
    if hasAddon(ADDON_REPOSITORY) and not isClient(): 
        params  = ['Resource_Logos','Resource_Ratings','Resource_Bumpers','Resource_Commericals','Resource_Trailers']
        missing = [addon for param in params for addon in SETTINGS.getSetting(param).split(',') if not hasAddon(addon)]
        for addon in missing:
            installAddon(addon, silent)
            if xbmc.Monitor().waitForAbort(15): break
    elif not silent: 
        Dialog().notificationDialog(LANGUAGE(30307)%(ADDON_NAME))

def addonEnabled(id):
    return xbmc.getCondVisibility("System.AddonIsEnabled(%s)"%id)

def toggleADDON(id, state=True, reverse=False):
    log('globals: toggleADDON, id = %s, state = %s, reverse = %s'%(id,state,reverse))
    sendJSON('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":%s}, "id": 1}'%(id,str(state).lower()))
    if reverse:
        if id == ADDON_ID: 
            xbmc.executebuiltin("AlarmClock(Re-enable,%s(%s),00:04)"%({'EnableAddon':False,'DisableAddon':True}[state],id))
        else: 
            xbmc.sleep(4000)
            toggleADDON(id, not bool(state))
    
def brutePVR(override=False):
    if (xbmc.getCondVisibility("Pvr.IsPlayingTv") or xbmc.getCondVisibility("Player.HasMedia")): return
    elif not override:
        if not Dialog().yesnoDialog('%s ?'%(LANGUAGE(30065)%(getPluginMeta(PVR_CLIENT).get('name','')))): return
    # setInstanceID()
    toggleADDON(PVR_CLIENT,False,reverse=True)
    return True

def getPVR(id=PVR_CLIENT):
    try: return xbmcaddon.Addon(id)
    except: # backend disabled?
        toggleADDON(id)
        xbmc.sleep(2000)
        try:    return xbmcaddon.Addon(id)
        except: return None

def setJsonSettings():
    for key in JSON_SETTINGS.keys():
        JSON_SETTINGS[key]

def chkMGR():
    return chkPVR(PVR_MANAGER, MGR_SETTINGS)

def chkPVR(id=PVR_CLIENT, values=PVR_SETTINGS):
    log('globals: chkPVR, id = %s'%(id))
    #check for min. settings' required
    addon = getPVR(id)
    if addon is None: return Dialog().notificationDialog(LANGUAGE(30217)%id)
    for setting, value in values.items():
        if not str(addon.getSetting(setting)) == str(value): 
            return configurePVR(id,values,SETTINGS.getSettingBool('Enable_Config'))
    return True
    
def configurePVR(id=PVR_CLIENT,values=PVR_SETTINGS,override=False):
    log('globals: configurePVR')
    if not override:
        if not Dialog().yesnoDialog('%s ?'%(LANGUAGE(30012)%(getPluginMeta(id).get('name','')))): return
    try:
        addon = getPVR(id)
        if addon is None: return False
        for setting, value in values.items(): 
            addon.setSetting(setting, value)
    except: return Dialog().notificationDialog(LANGUAGE(30049)%(id))
    if override: return True
    return Dialog().notificationDialog(LANGUAGE(30053))

def refreshMGR():
    if getPVR(PVR_MANAGER):
        xbmc.executebuiltin('RunScript(service.iptv.manager,refresh)')

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

def diffLST(old, new): 
    return list(set(old) - set(new))
    
def diffLSTDICT(old,new):
    return [i for i in old + new if i not in old or i not in new]
    
def diffDICT(old,new):
    #(dict(diffDICT(old,new)))
    intersec = list(set(list(old.keys()) +  list(new.keys())))
    for inter in intersec:
        if (hasattr(old.get(inter),'get')):
            diff = (dict((set(chain(old.get(inter,{}).items(),new.get(inter,{}).items())) - set(old.get(inter,{}).items()))) or None)
        else:
            diff = (list((set(chain(old.get(inter,''),new.get(inter,''))) - set(old.get(inter,'')))) or None)
        if diff: 
            yield inter,diff

def mergeDICT(dict1, dict2):
    return [{**u, **v} for u, v in zip_longest(dict1, dict2, fillvalue={})]

def removeDupDictFromList(list):
    return [i for n, i in enumerate(list) if i not in list[n + 1:]]

def removeDUPSLST(lst):
    list_of_strings = [dumpJSON(d) for d in lst]
    list_of_strings = set(list_of_strings)
    return [loadJSON(s) for s in list_of_strings]

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

def setWriter(writer, fileItem):
    return '%s [COLOR item="%s"][/COLOR]'%(writer,encodeString(dumpJSON(fileItem)))

def getWriter(text):
    if isinstance(text, list): text = text[0]
    if isinstance(text, basestring):
        writer = re.search(r'\[COLOR item=\"(.+?)\"]\[/COLOR]', text)
        if writer: return loadJSON(decodeString(writer.group(1)))
    return {}

def getWriterfromString(condition='ListItem'):
    return getWriter(xbmc.getInfoLabel('%s.Writer'%(condition)))
    
def hasChannelData(condition='ListItem'):
    return getWriterfromString(condition).get('citem',{}).get('number',-1) > 0

def getChannelID(name, path, number):
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)))
    return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:32]).decode(DEFAULT_ENCODING),slugify(ADDON_NAME))

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

def getMD5(text):
    if not isinstance(text,str): text = str(text)
    hash_object = hashlib.md5(text.encode())
    return hash_object.hexdigest()

def setInstanceID():
    PROPERTIES.setProperty('InstanceID',uuid.uuid4())

def getInstanceID():
    return (PROPERTIES.getProperty('InstanceID') or str(uuid.uuid4()))

def genUUID(seed=None):
    if seed:
        m = hashlib.md5()
        m.update(seed.encode(DEFAULT_ENCODING))
        return str(uuid.UUID(m.hexdigest()))
    return str(uuid.uuid1(clock_seq=CLOCK_SEQ))

def getIP():
    return (xbmc.getIPAddress() or None)

def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text

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
        while iters and not xbmc.Monitor().abortRequested():
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
    return xbmc.getCondVisibility('VideoPlayer.HasSubtitles')

def isSubtitle():
    return xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled')

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
