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
#
# -*- coding: utf-8 -*-

import os, sys, re, json, struct
import shutil, subprocess, traceback
import codecs, random
import uuid, base64, binascii, hashlib
import time, datetime

from kodi_six    import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from contextlib  import contextmanager, closing
from socket      import gethostbyname, gethostname
from itertools   import cycle, chain, zip_longest
from xml.sax.saxutils import escape, unescape
from ast         import literal_eval

from cache       import Cache, cacheit
from pool        import killJSON, killit, timeit, poolit, threadit, timerit
from kodi        import Dialog
from fileaccess  import FileAccess, FileLock
from collections import Counter, OrderedDict
from six.moves   import urllib 
from socket      import timeout
from math        import ceil,  floor
from infotagger.listitem import ListItemInfoTag

#info
ADDON_ID            = 'plugin.video.pseudotv.live'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
LANGUAGE            = REAL_SETTINGS.getLocalizedString


GLOBAL_FILELOCK     = FileLock()
MONITOR             = xbmc.Monitor()
PLAYER              = xbmc.Player()
DIALOG              = Dialog()
PROPERTIES          = DIALOG.properties
SETTINGS            = DIALOG.settings
LISTITEMS           = DIALOG.listitems
BUILTIN             = DIALOG.builtin

#constants
OVERLAY_DELAY       = 15    #secs
DTFORMAT            = '%Y%m%d%H%M%S'
DTZFORMAT           = '%Y%m%d%H%M%S +%z'
LANG                = 'en' #todo parse kodi region settings
DEFAULT_ENCODING    = "utf-8"
PROMPT_DELAY        = 4000 #msecs
RADIO_ITEM_LIMIT    = 250
CHANNEL_LIMIT       = 999
AUTOTUNE_LIMIT      = 3

AUTOTUNE_TYPES      = ["Playlists",
                       "TV Networks",
                       "TV Shows",
                       "TV Genres",
                       "Movie Genres",
                       "Movie Studios",
                       "Mixed Genres",
                       "Mixed",
                       "Recommended",
                       "Services",
                       "Music Genres"]
                          

PROVISIONAL_TYPES   = {"TV Networks"  :{"path":["videodb://tvshows/studios/"],
                                        "json":[{"method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","field":"studio","operator":"contains","sort":"episode"}]},
                       "TV Shows"     :{"path":["videodb://tvshows/titles/"],
                                        "json":[{"method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","field":"tvshow","operator":"is","sort":"episode"}]},
                       "TV Genres"    :{"path":["videodb://tvshows/genres/"],
                                        "json":[{"method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","field":"genre","operator":"contains","sort":"episode"}]},
                       "Movie Genres" :{"path":["videodb://movies/genres/"] ,
                                        "json":[{"method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie"  ,"field":"genre","operator":"contains","sort":"random"}]},
                       "Movie Studios":{"path":["videodb://movies/studios/"],
                                        "json":[{"method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie"  ,"field":"studio","operator":"contains","sort":"random"}]},
                       "Mixed Genres" :{"path":["videodb://tvshows/genres/",
                                                "videodb://movies/genres/"],
                                        "json":[{"method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","field":"genre","operator":"contains","sort":"episode"},
                                                {"method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie"  ,"field":"genre","operator":"contains","sort":"year"}]}}
                       
GROUP_TYPES         = ['Addon', 'Directory', 'TV', 'Movies', 'Music', 'Other', 'PVR', 'Plugin', 'Radio', 'Smartplaylist', 'UPNP', 'IPTV'] + AUTOTUNE_TYPES

VFS_TYPES           = ["plugin://",
                       "pvr://",
                       "upnp://",
                       "resource://"]
                       
TV_TYPES            = ['episode',
                       'episodes',
                       'tvshow',
                       'tvshows']
                       
MOVIE_TYPES         = ['movie',
                       'movies']
                       
MUSIC_TYPES         = ['songs',
                       'albums',
                       'artists',
                       'music']
            
HTML_ESCAPE         = {"&": "&amp;",
                       '"': "&quot;",
                       "'": "&apos;",
                       ">": "&gt;",
                       "<": "&lt;"}    

PVR_URL             = 'plugin://{addon}/?mode=play&name={name}&id={id}&radio={radio}.pvr'
VOD_URL             = 'plugin://{addon}/?mode=vod&name={name}&id={id}&channel={channel}&radio={radio}.pvr'
              
PTVL_REPO           = 'repository.pseudotv'
PVR_CLIENT          = 'pvr.iptvsimple'
      
#variables
DEBUG_ENABLED       = SETTINGS.getSetting('Enable_Debugging').lower() == 'true'
DEBUG_LEVELS        = {0:xbmc.LOGDEBUG,1:xbmc.LOGINFO,2:xbmc.LOGWARNING,3:xbmc.LOGERROR}
DEBUG_LEVEL         = DEBUG_LEVELS[int((SETTINGS.getSetting('Debugging_Level') or "1"))]
USER_LOC            = SETTINGS.getSetting('User_Folder')

#docs
README_FLE          = os.path.join(ADDON_PATH,'README.md')
CHANGELOG_FLE       = os.path.join(ADDON_PATH,'changelog.txt')
LICENSE_FLE         = os.path.join(ADDON_PATH,'LICENSE')

#folders
IMAGE_LOC           = os.path.join(ADDON_PATH,'resources','images')
MEDIA_LOC           = os.path.join(ADDON_PATH,'resources','skins','default','media')
SFX_LOC             = os.path.join(MEDIA_LOC,'sfx')
BACKUP_LOC          = os.path.join(SETTINGS_LOC,'backup')
CACHE_LOC           = os.path.join(SETTINGS_LOC,'cache')

#files
XMLTVFLE            = '%s.xml'%('pseudotv')
M3UFLE              = '%s.m3u'%('pseudotv')
CHANNELFLE          = 'channels.json'
LIBRARYFLE          = 'library.json'
GENREFLE            = 'genres.xml'
TVGROUPFLE          = 'tv_groups.xml'
RADIOGROUPFLE       = 'radio_groups.xml'
PROVIDERFLE         = 'providers.xml'

VIDEO_EXTS          = xbmc.getSupportedMedia('video').split('|')
MUSIC_EXTS          = xbmc.getSupportedMedia('music').split('|')
IMAGE_EXTS          = xbmc.getSupportedMedia('picture').split('|')
IMG_EXTS            = ['.png','.jpg','.gif']

#file paths
SETTINGS_FLE        = os.path.join(SETTINGS_LOC,'settings.xml')
CHANNELFLE_BACKUP   = os.path.join(SETTINGS_LOC,'channels.backup')
CHANNELFLE_RESTORE  = os.path.join(SETTINGS_LOC,'channels.restore')
PLS_LOC             = os.path.join(USER_LOC,'playlists')
LOGO_LOC            = os.path.join(USER_LOC,'logos')
TEMP_LOC            = os.path.join(USER_LOC,'temp')
M3UFLEPATH          = os.path.join(USER_LOC,M3UFLE)
XMLTVFLEPATH        = os.path.join(USER_LOC,XMLTVFLE)
GENREFLEPATH        = os.path.join(USER_LOC,GENREFLE)
PROVIDERFLEPATH     = os.path.join(USER_LOC,PROVIDERFLE)
CHANNELFLEPATH      = os.path.join(SETTINGS_LOC,CHANNELFLE)
LIBRARYFLEPATH      = os.path.join(SETTINGS_LOC,LIBRARYFLE)
BING_WAV            = os.path.join(SFX_LOC,'bing.wav')
NOTE_WAV            = os.path.join(SFX_LOC,'notify.wav')

#remotes
IMPORT_ASSET        = os.path.join(ADDON_PATH,'remotes','asset.json')
RULEFLE_DEFAULT     = os.path.join(ADDON_PATH,'remotes','rule.json')
M3UFLE_DEFAULT      = os.path.join(ADDON_PATH,'remotes','m3u.json')
GROUPFLE_DEFAULT    = os.path.join(ADDON_PATH,'remotes','groups.xml')
LIBRARYFLE_DEFAULT  = os.path.join(ADDON_PATH,'remotes',LIBRARYFLE)
CHANNELFLE_DEFAULT  = os.path.join(ADDON_PATH,'remotes',CHANNELFLE)
GENREFLE_DEFAULT    = os.path.join(ADDON_PATH,'remotes',GENREFLE)
PROVIDERFLE_DEFAULT = os.path.join(ADDON_PATH,'remotes',PROVIDERFLE)

#images

LOGO                = os.path.join(MEDIA_LOC,'wlogo.png')
COLOR_LOGO          = os.path.join(ADDON_PATH,'resources','skins','default','media','logo.png')
HOST_LOGO           = 'http://github.com/PseudoTV/PseudoTV_Live/blob/master/plugin.video.pseudotv.live/resources/skins/default/media/logo.png?raw=true'

#builder
RULES_ACTION_CHANNEL       = 1 
RULES_ACTION_BUILD_START   = 2
RULES_ACTION_CHANNEL_START = 3
RULES_ACTION_CHANNEL_CITEM = 4
RULES_ACTION_CHANNEL_FLIST = 5
RULES_ACTION_CHANNEL_STOP  = 6
RULES_ACTION_PRE_TIME      = 7
RULES_ACTION_POST_TIME     = 8
RULES_ACTION_BUILD_STOP    = 9
#player
RULES_ACTION_PLAYBACK      = 11
RULES_ACTION_PLAYER_START  = 12
RULES_ACTION_PLAYER_STOP   = 13
#overlay
RULES_ACTION_OVERLAY       = 21

#functions      
def setBusy(state=True):
    PROPERTIES.setPropertyBool('busyLocker',state)

def isBusy():
    return PROPERTIES.getPropertyBool('busyLocker')
  
@contextmanager
def busyLocker(set=False):
    while not MONITOR.abortRequested() and PROPERTIES.getPropertyBool('busyLocker'):
        if MONITOR.waitForAbort(0.001): break
    try: yield
    finally:
        PROPERTIES.setPropertyBool('busyLocker',False)

@contextmanager
def busy_dialog():
    if not isBusyDialog():
        BUILTIN.executebuiltin('ActivateWindow(busydialognocancel)')
    try: yield
    finally:
        if BUILTIN.getInfoBool('IsActive(busydialognocancel)','Window'):
            BUILTIN.executebuiltin('Dialog.Close(busydialognocancel)')

@contextmanager
def sudo_dialog(msg):
    dia = DIALOG.progressBGDialog(message=msg)
    try: 
        dia = DIALOG.progressBGDialog(int(time.time() % 60),dia)
        yield
    finally:
        DIALOG.progressBGDialog(100,dia) 

@contextmanager
def open_dialog():
    if not PROPERTIES.getPropertyBool('opendialog'):
        PROPERTIES.setPropertyBool('opendialog',True)
    try: yield
    finally:
        PROPERTIES.setPropertyBool('opendialog',False)

@contextmanager
def open_window():
    if not PROPERTIES.getPropertyBool('openwindow'):
        PROPERTIES.setPropertyBool('openwindow',True)
    try: yield
    finally:
        PROPERTIES.setPropertyBool('openwindow',False)

@contextmanager
def fileLocker(globalFileLock):
    globalFileLock.lockFile("MasterLock")
    try: yield
    finally: 
        globalFileLock.unlockFile('MasterLock')
        globalFileLock.close()

def log(event, level=xbmc.LOGDEBUG):
    if not DEBUG_ENABLED and level != xbmc.LOGERROR: return #todo use debug level filter
    if level == xbmc.LOGERROR: event = '%s\n%s'%(event,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,event),level)
    
def slugify(s, lowercase=False):
  if lowercase: s = s.lower()
  s = s.strip()
  s = re.sub(r'[^\w\s-]', '', s)
  s = re.sub(r'[\s_-]+', '_', s)
  s = re.sub(r'^-+|-+$', '', s)
  return s
        
def stripNumber(s):
    return re.sub(r'\d+','',s)
    
def stripRegion(s):
    try:
        match = re.compile('(.*) \((.*)\)', re.IGNORECASE).search(s)
        if match.group(1): return match.group(1)
    except: pass
    return s

def unquoteString(text):
    return urllib.parse.unquote(text)
    
def quoteString(text):
    return urllib.parse.quote(text)

def encodeString(text):
    base64_bytes = base64.b64encode(text.encode(DEFAULT_ENCODING))
    return base64_bytes.decode(DEFAULT_ENCODING)

def decodeString(base64_bytes):
    message_bytes = base64.b64decode(base64_bytes.encode(DEFAULT_ENCODING))
    return message_bytes.decode(DEFAULT_ENCODING)

def escapeString(text, table=HTML_ESCAPE):
    return escape(text,table)
    
def unescapeString(text, table=HTML_ESCAPE):
    return unescape(text,{v:k for k, v in list(table.items())})

def dumpJSON(item, idnt=None, sortkey=False, separators=(',', ':')):
    if not isinstance(item,str):
        return json.dumps(item, indent=idnt, sort_keys=sortkey, separators=separators)
    elif isinstance(item,str):
        return item
    return ''
    
def loadJSON(item):
    if isinstance(item,str):
        return json.loads(item)
    elif isinstance(item,dict):
        return item
    return {}
  
def getJSON(file):
    fle  = (FileAccess.open(file, 'r') or '')
    try:    data = loadJSON(fle.read())
    except: data = {}
    fle.close()
    return data
    
def setJSON(file, data):
    with fileLocker(GLOBAL_FILELOCK):
        fle = FileAccess.open(file, 'w')
        fle.write(dumpJSON(data, idnt=4, sortkey=False))
        fle.close()
    return True
    
def setURL(url, file):
    try:
        contents = urllib.request.urlopen(url).read()
        fle = FileAccess.open(file, 'w')
        fle.write(contents)
        fle.close()
        return FileAccess.exists(file)
    except Exception as e: 
        log("saveURL, failed! %s"%e, xbmc.LOGERROR)

def setDictLST(lst=[]):
    sLST = [dumpJSON(d) for d in lst]
    sLST = list(OrderedDict.fromkeys(sLST))
    return [loadJSON(s) for s in sLST]

def diffLSTDICT(old, new):
    sOLD = set([dumpJSON(e) for e in old])
    sNEW = set([dumpJSON(e) for e in new])
    sDIFF = sOLD.symmetric_difference(sNEW)
    return setDictLST([loadJSON(e) for e in sDIFF])

def setInstanceID():
    PROPERTIES.setEXTProperty('InstanceID',uuid.uuid4())

def getInstanceID():
    instanceID = PROPERTIES.getEXTProperty('InstanceID') 
    if not instanceID: setInstanceID()
    return PROPERTIES.getEXTProperty('InstanceID')
  
def getMD5(text,hash=0,hexit=True):
    if isinstance(text,dict):     text = dumpJSON(text)
    elif not isinstance(text,str):text = str(text)
    for ch in text: hash = (hash*281 ^ ord(ch)*997) & 0xFFFFFFFF
    if hexit: return hex(hash)[2:].upper().zfill(8)
    else:     return hash

def genUUID(seed=None):
    if seed:
        m = hashlib.md5()
        m.update(seed.encode(DEFAULT_ENCODING))
        return str(uuid.UUID(m.hexdigest()))
    return str(uuid.uuid1(clock_seq=70420))
    
def getIP(wait=5):
    while not MONITOR.abortRequested() and wait > 0:
        ip = xbmc.getIPAddress()
        if ip: return ip
        elif (MONITOR.waitForAbort(1)): break
        else: wait -= 1
    return gethostbyname(gethostname())
           
def getMYUUID():
    uuid = SETTINGS.getCacheSetting('MY_UUID')
    if not uuid: 
        uuid = genUUID(seed=getIP())
        SETTINGS.setCacheSetting('MY_UUID',uuid)
    return uuid
    
def getChannelID(name, path, number):
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)))
    return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:32]).decode(DEFAULT_ENCODING),slugify(ADDON_NAME))

def splitYear(s):
    try:
        match = re.compile('(.*) \((.*)\)', re.IGNORECASE).search(s)
        if match and match.group(2): return match.groups()
    except: pass
    return s, None

def getChannelSuffix(name, type):
    if   type == "TV Genres"    and not LANGUAGE(32014) in name: suffix = LANGUAGE(32014) #TV
    elif type == "Movie Genres" and not LANGUAGE(32015) in name: suffix = LANGUAGE(32015) #Movies
    elif type == "Mixed Genres" and not LANGUAGE(32010) in name: suffix = LANGUAGE(32010) #Mixed
    elif type == "Music Genres" and not LANGUAGE(32016) in name: suffix = LANGUAGE(32016) #Music
    else: return name
    return '%s %s'%(name,suffix)
 
def cleanChannelSuffix(name, type):
    if   type == "TV Genres"    : name = name.split(' %s'%LANGUAGE(32014))[0]#TV
    elif type == "Movie Genres" : name = name.split(' %s'%LANGUAGE(32015))[0]#Movie
    elif type == "Mixed Genres" : name = name.split(' %s'%LANGUAGE(32010))[0]#Mixed
    elif type == "Music Genres" : name = name.split(' %s'%LANGUAGE(32016))[0]#Music
    return name
            
def getLabel(item, addYear=False):
    label = (item.get('name','') or item.get('label','') or item.get('showtitle','') or item.get('title',''))
    if not label: return ''
    label, year = splitYear(label)
    year = (item.get('year','') or year)
    if year and addYear: return '%s (%s)'%(label, year)
    return label

def hasPVR():
    return BUILTIN.getInfoBool('HasTVChannels','Pvr')
    
def hasRadio():
    return BUILTIN.getInfoBool('HasRadioChannels','Pvr')

def hasMusic():
    return BUILTIN.getInfoBool('HasContent(Music)','Library')
    
def hasTV():
    return BUILTIN.getInfoBool('HasContent(TVShows)','Library')
    
def hasMovie():
    return BUILTIN.getInfoBool('HasContent(Movies)','Library')
 
def openAddonSettings(ctl=(0,1),id=ADDON_ID):
    ## ctl[0] is the Category (Tab) offset (0=first, 1=second, 2...etc)
    ## ctl[1] is the Setting (Control) offset (1=first, 2=second, 3...etc)# addonId is the Addon ID
    ## Example: openAddonSettings((2,3),'plugin.video.name')
    ## This will open settings dialog focusing on fourth setting (control) inside the third category (tab)
    BUILTIN.executebuiltin('Addon.OpenSettings(%s)'%id)
    xbmc.sleep(100)
    BUILTIN.executebuiltin('SetFocus(%i)'%(ctl[0]-100))
    xbmc.sleep(50)
    if ctl[1] >= 7: #fix next page focus
        BUILTIN.executebuiltin('Action(right)')
        xbmc.sleep(50)
        for page in range(floor(ctl[1]/7)):
            BUILTIN.executebuiltin('Action(down)')
            xbmc.sleep(50)
        BUILTIN.executebuiltin('Action(left)')
        xbmc.sleep(50)
        try:    ctl = (ctl[0],{8:7,11:9}[ctl[1]])
        except: ctl = (ctl[0],ctl[1] + 1)
    BUILTIN.executebuiltin('SetFocus(%i)'%(ctl[1]-80))
    
def pagination(list, end):
    for start in range(0, len(list), end):
        yield seq[start:start+end]
        
def roundTimeDown(thetime, offset=30): # round the given time down to the nearest
    n = datetime.datetime.fromtimestamp(thetime)
    delta = datetime.timedelta(minutes=offset)
    if n.minute > (offset-1): n = n.replace(minute=offset, second=0, microsecond=0)
    else: n = n.replace(minute=0, second=0, microsecond=0)
    return time.mktime(n.timetuple())
    
def strpTime(datestring, format='%Y-%m-%d %H:%M:%S'): #convert json pvr datetime string to datetime obj, thread safe!
    try:              return datetime.datetime.strptime(datestring, format)
    except TypeError: return datetime.datetime.fromtimestamp(time.mktime(time.strptime(datestring, format)))
    except:           return ''

def getLocalTime():
    offset = (datetime.datetime.utcnow() - datetime.datetime.now())
    return time.time() + offset.total_seconds() #returns timestamp

def randomShuffle(items=[]):
    if len(items) > 0:
        random.seed() #reseed random for a "greater random effect".
        random.shuffle(items)
    return items
    
def interleave(seqs): 
    #interleave multi-lists, while preserving seqs order
    #[1, 'a', 'A', 2, 'b', 'B', 3, 'c', 'C', 4, 'd', 'D', 'e', 'E']
    return [_f for _f in chain.from_iterable(zip_longest(*seqs)) if _f]
        
def intersperse(*seqs):
    #interleave multi-lists, while preserving order distribution
    def distribute(seq):
        for i, x in enumerate(seq, 1):
            yield i/(len(seq) + 1), x
    distributions = list(map(distribute, seqs))
    #['a', 'A', 1, 'b', 'B', 2, 'c', 'C', 3, 'd', 'D', 4, 'e', 'E']
    for _, x in sorted(chain(*distributions), key=operator.itemgetter(0)):
        yield x
        
def distribute(*seq):
    #randomly distribute multi-lists of different sizes.
    #['a', 'A', 'B', 1, 2, 'C', 3, 'b', 4, 'D', 'c', 'd', 'e', 'E']
    iters = list(map(iter, seqs))
    while not xbmc.Monitor().abortRequested() and iters:
        it = random.choice(iters)
        try:   yield next(it)
        except StopIteration:
            iters.remove(it)

def isStack(path,file=None): #is path a stack
    if file is not None: 
        return path.startswith('stack://%s'%(file))
    else:
        return path.startswith('stack://')

def hasStack(path,file=None): #does path has stack paths, return paths
    if isStack(path,file): 
        return splitStacks(path)

def splitStacks(path): #split stack path for indv. files.
    if not isStack(path): return [path]
    return list([_f for _f in ((path.split('stack://')[1]).split(' , ')) if _f])
            
def percentDiff(org, new):
    try: return (abs(float(org) - float(new)) / float(new)) * 100.0
    except ZeroDivisionError: return -1
    
def escapeDirJSON(path):
    mydir = path
    if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
    return mydir
      
def KODI_LIVETV_SETTINGS(): #recommended Kodi LiveTV settings
    return {'pvrmanager.preselectplayingchannel' :'true',
            'pvrmanager.syncchannelgroups'       :'true',
            'pvrmanager.backendchannelorder'     :'true',
            'pvrmanager.usebackendchannelnumbers':'true',
            # 'pvrmenu.iconpath':'',
            # 'pvrplayback.switchtofullscreenchanneltypes':1,
            # 'pvrplayback.confirmchannelswitch':'true',
            # 'epg.selectaction':2,
            # 'epg.epgupdate':120,
           'pvrmanager.startgroupchannelnumbersfromone':'false'}

def IPTV_SIMPLE_SETTINGS(): #recommended IPTV Simple settings
    # SETTINGS.getSettingInt('Client_Mode') #todo restore user setting.
    CLIENT_MODE = 0
    return {'m3uRefreshMode'              :'1',
            'm3uRefreshIntervalMins'      :'5',
            'm3uRefreshHour'              :'0',
            'm3uCache'                    :'true',
            'logoPathType'                :'0',
            'logoPath'                    :LOGO_LOC,
            'm3uPathType'                 :'%s'%('1' if CLIENT_MODE == 1 else '0'),
            'm3uPath'                     :M3UFLEPATH,
            'm3uUrl'                      :SETTINGS.getSetting('Remote_M3U'),
            'epgPathType'                 :'%s'%('1' if CLIENT_MODE == 1 else '0'),
            'epgPath'                     :XMLTVFLEPATH,
            'epgUrl'                      :SETTINGS.getSetting('Remote_XMLTV'),
            'epgCache'                    :'true',
            'genresPathType'              :'%s'%('1' if CLIENT_MODE == 1 else '0'),
            'genresPath'                  :GENREFLEPATH,
            'genresUrl'                   :SETTINGS.getSetting('Remote_GENRE'),
            # 'tvGroupMode'                 :'0',
            # 'customTvGroupsFile'          :(TVGROUPFLE),#todo
            # 'radioGroupMode'              :'0',
            # 'customRadioGroupsFile'       :(RADIOGROUPFLE),#todo
            # 'enableProviderMappings'      :'true',
            # 'defaultProviderName'         :ADDON_NAME,
            # 'providerMappingFile'         :PROVIDERFLEPATH,#todo
            # 'useEpgGenreText'             :'true',
            'logoFromEpg'                 :'1',
            'catchupEnabled'              :'true',
            'allChannelsCatchupMode'      :'0',
            'numberByOrder'               :'false',
            'startNum'                    :'1',
            'epgTimeShift'                :'0',
            # 'epgTSOverride'               :'false',
            # 'useFFmpegReconnect'          :'true',
            # 'useInputstreamAdaptiveforHls':'true'
            }

def chkPVREnabled():
    if PROPERTIES.getPropertyBool('%s.Disabled'%(PVR_CLIENT)):
        togglePVR(True,False)
         
def togglePVR(state=True, reverse=False, waitTime=15):
    log('globals: togglePVR, state = %s, reverse = %s, waitTime = %s'%(state,reverse,waitTime))
    try:    name = xbmcaddon.Addon(PVR_CLIENT).getAddonInfo('name')
    except: name = PVR_CLIENT
    PROPERTIES.setPropertyBool('%s.Disabled'%(PVR_CLIENT),not bool(state))
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":%s}, "id": 1}'%(PVR_CLIENT,str(state).lower()))
    waitMSG = '%s: %s'%(LANGUAGE(32125),name)
    if reverse: timerit(togglePVR)(waitTime,[not bool(state)])
    else: waitTime = int(PROMPT_DELAY/1000)
    DIALOG.notificationWait(waitMSG,wait=waitTime)
              
def forceBrute(msg=''):
    name = xbmcaddon.Addon(PVR_CLIENT).getAddonInfo('name')
    if (BUILTIN.getInfoBool('IsPlayingTv','Pvr') | BUILTIN.getInfoBool('IsPlayingRadio','Pvr')): msg = LANGUAGE(32128)
    if DIALOG.yesnoDialog('%s\n%s?\n%s'%(LANGUAGE(32129)%(name),(LANGUAGE(32121)%(name)),msg)):
        brutePVR(True)
              
def brutePVR(override=False, waitTime=15):
    if not override:
        if not DIALOG.yesnoDialog('%s?'%(LANGUAGE(32121)%(xbmcaddon.Addon(PVR_CLIENT).getAddonInfo('name')))): return
    togglePVR(False,True,waitTime)
    if MONITOR.waitForAbort(waitTime): return False
    return True
    
def setPluginSettings(id, values, override=SETTINGS.getSettingBool('Override_User')):
    try: addon = xbmcaddon.Addon(id)
    except:
        DIALOG.notificationDialog(LANGUAGE(32034)%(id))
        return False
    try:
        addon_name = addon.getAddonInfo('name')
        if not override:
            DIALOG.textviewer('%s\n%s'%((LANGUAGE(32035)%(addon_name)),('\n'.join(['%s: %s changing to [B]%s[/B]'%(s,v[0],v[1]) for s,v in list(values.items())]))))
            if not DIALOG.yesnoDialog((LANGUAGE(32036)%addon_name)): return
            
        if addon is None:
            DIALOG.notificationDialog(LANGUAGE(32034)%(id))
            return False
        for s, v in list(values.items()):
            if MONITOR.waitForAbort(1): return False
            addon.setSetting(s, v[1])
        DIALOG.notificationDialog((LANGUAGE(32037)%(id)))
    except: DIALOG.notificationDialog(LANGUAGE(32000))
    
def chkPluginSettings(id, values, silent=True):
    try: 
        changes = {}
        addon   = xbmcaddon.Addon(id)
        for s, v in list(values.items()):
            if MONITOR.waitForAbort(1): return False
            value = addon.getSetting(s)
            if str(value).lower() != str(v).lower(): 
                changes[s] = (value, v)
        if changes: setPluginSettings(id,changes)
        elif not silent: DIALOG.notificationDialog(LANGUAGE(32046))
    except:DIALOG.notificationDialog(LANGUAGE(32034)%(id))
         
def hasSubtitle():
    return BUILTIN.getInfoBool('HasSubtitles','VideoPlayer')

def isSubtitle():
    return BUILTIN.getInfoBool('SubtitlesEnabled','VideoPlayer')

def isPlaylistRandom():
    return BUILTIN.getInfoLabel('Random','Playlist').lower() == 'on' # Disable auto playlist shuffling if it's on
    
def isPlaylistRepeat():
    return BUILTIN.getInfoLabel('IsRepeat','Playlist').lower() == 'true' # Disable auto playlist repeat if it's on #todo
        
def decodeWriter(text):
    if isinstance(text,list): text = text[0]
    if isinstance(text, str):
        writer = re.search(r'\[COLOR item=\"(.+?)\"]\[/COLOR]', text)
        if writer: return loadJSON(decodeString(writer.group(1)))
    return {}
    
def encodeWriter(writer, text):
    return '%s [COLOR item="%s"][/COLOR]'%(writer,encodeString(dumpJSON(text)))
    
def isOverlay():
    return PROPERTIES.getPropertyBool('OVERLAY')
    
def setOverlay(state=True):
    PROPERTIES.setPropertyBool('OVERLAY',state)
        
def isBusyDialog():
    return (BUILTIN.getInfoBool('IsActive(busydialognocancel)','Window') | BUILTIN.getInfoBool('IsActive(busydialog)','Window'))
         
def closeBusyDialog():
    if BUILTIN.getInfoBool('IsActive(busydialognocancel)','Window'):
        BUILTIN.executebuiltin('Dialog.Close(busydialognocancel)')
    elif BUILTIN.getInfoBool('IsActive(busydialog)','Window'):
        BUILTIN.executebuiltin('Dialog.Close(busydialog)')
         
def hasAutotuned():
    return PROPERTIES.getPropertyBool('hasAutotuned')
    
def setAutotuned(state=True):
    return PROPERTIES.setPropertyBool('hasAutotuned',state)
         
def hasFirstrun():
    return PROPERTIES.getPropertyBool('hasFirstrun')
    
def setFirstrun(state=True):
    return PROPERTIES.setPropertyBool('hasFirstrun',state)

def isClient():
    client = PROPERTIES.getEXTProperty('plugin.video.pseudotv.live.isClient') == "true"
    return (client | bool(SETTINGS.getSettingInt('Client_Mode')))
   
def setClient(state=False,silent=True):
    if not silent and state: DIALOG.notificationDialog(LANGUAGE(32115)%(ADDON_NAME))
    PROPERTIES.setEXTProperty('plugin.video.pseudotv.live.isClient',str(state).lower())
           
def getDiscovery():
    return loadJSON(PROPERTIES.getEXTProperty('plugin.video.pseudotv.live.SERVER_DISCOVERY'))

def setDiscovery(servers):
    return PROPERTIES.setEXTProperty('plugin.video.pseudotv.live.SERVER_DISCOVERY',dumpJSON(servers))

def chkDiscovery(servers, forced=False):
    def setResourceSettings(settings):
        #Set resource settings on client.
        for key, value in list(settings.items()):
            try:    SETTINGS.setSettings(key, value)
            except: pass

    current_server = SETTINGS.getSetting('Remote_URL')
    if (not current_server or forced) and len(list(servers.keys())) == 1: #If one server found autoselect.
        server = list(servers.keys())[0]
        setServerSettings(server) #set server host paths.
        setResourceSettings(servers[server].get('settings',{})) #update client resources to server settings.
        # chkPluginSettings(PVR_CLIENT,IPTV_SIMPLE_SETTINGS()) #update pvr settings
            
def delServerSettings():
    SETTINGS.setSetting('Remote_URL'  ,'')
    SETTINGS.setSetting('Remote_M3U'  ,'')
    SETTINGS.setSetting('Remote_XMLTV','')
    SETTINGS.setSetting('Remote_GENRE','')
                     
def setServerSettings(host):
    SETTINGS.setSetting('Remote_URL'  ,'http://%s'%(host))
    SETTINGS.setSetting('Remote_M3U'  ,'http://%s/%s'%(host,M3UFLE))
    SETTINGS.setSetting('Remote_XMLTV','http://%s/%s'%(host,XMLTVFLE))
    SETTINGS.setSetting('Remote_GENRE','http://%s/%s'%(host,GENREFLE))
       
def chunkLst(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
        
def isRadio(item):
    if item.get('radio',False) or item.get('type','') == "Music Genres": return True
    for path in item.get('path',[]):
        if path.lower().startswith(('musicdb://','special://profile/playlists/music/','special://musicplaylists/')): return True
    return False
    
def roundupDIV(p, q):
    try:
        d, r = divmod(p, q)
        if r: d += 1
        return d
    except ZeroDivisionError: 
        return 1
                
def playSFX(filename, cached=False):
    xbmc.playSFX(filename, useCached=cached)
    
    
def isLowPower():
    if (BUILTIN.getInfoBool('Platform.Windows','System') | BUILTIN.getInfoBool('Platform.OSX','System')):
        return False
    return True
