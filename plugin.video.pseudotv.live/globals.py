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

import _strptime, os, sys, re, platform, subprocess, traceback, random, difflib, six, hashlib
import datetime, time, json, threading, codecs, base64, struct, binascii, shutil, types

from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from itertools import repeat, cycle, chain
from six.moves import urllib
from contextlib import contextmanager
from simplecache import use_cache, SimpleCache
from xml.dom.minidom import parse, parseString, Document
from xml.etree.ElementTree import ElementTree, Element, SubElement, tostring

try:
    from multiprocessing import cpu_count 
    from multiprocessing.pool import ThreadPool 
    ENABLE_POOL = True
    CORES = cpu_count()
except: ENABLE_POOL = False
    
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if PY3: 
    basestring = str
    unicode = str
    
# Plugin Info
ADDON_ID       = 'plugin.video.pseudotv.live'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

PVR_CLIENT     = 'pvr.iptvsimple'
USER_LOC       = (REAL_SETTINGS.getSetting('User_Folder') or SETTINGS_LOC)
XMLTVFLE       = os.path.join(USER_LOC,'%s.xml'%('pseudotv'))
M3UFLE         = os.path.join(USER_LOC,'%s.m3u'%('pseudotv'))
LOGO_LOC       = os.path.join(USER_LOC,'logos')
LOCK_LOC       = SETTINGS_LOC
CHANNELFLE     = os.path.join(USER_LOC,'channels.json')
CHANNELFLE_DEFAULT = os.path.join(ADDON_PATH,'channels.json')
GENREFLE         = os.path.join(USER_LOC,'genres.xml')
GENREFLE_DEFAULT = os.path.join(ADDON_PATH,'genres.xml')

DTFORMAT       = '%Y%m%d%H%M%S'
EPG_HRS        = 10800  # 3hr in seconds, Min. EPG guidedata
MIN_ENTRIES    = 12
JSON_FILE_ENUM = ["title","artist","albumartist","genre","year","rating","album","track","duration","comment","lyrics","musicbrainztrackid","musicbrainzartistid","musicbrainzalbumid","musicbrainzalbumartistid","playcount","fanart","director","trailer","tagline","plot","plotoutline","originaltitle","lastplayed","writer","studio","mpaa","cast","country","imdbnumber","premiered","productioncode","runtime","set","showlink","streamdetails","top250","votes","firstaired","season","episode","showtitle","thumbnail","file","resume","artistid","albumid","tvshowid","setid","watchedepisodes","disc","tag","art","genreid","displayartist","albumartistid","description","theme","mood","style","albumlabel","sorttitle","episodeguide","uniqueid","dateadded","size","lastmodified","mimetype","specialsortseason","specialsortepisode"]
JSON_FILES     = ["title","artist","albumartist","genre","year","rating","album","track","duration","lyrics","playcount","director","trailer","tagline","plot","plotoutline","originaltitle","lastplayed","writer","studio","mpaa","cast","country","premiered","runtime","set","streamdetails","top250","votes","firstaired","season","episode","showtitle","file","resume","artistid","albumid","tvshowid","setid","watchedepisodes","disc","tag","displayartist","description","theme","mood","style","albumlabel","sorttitle","uniqueid","dateadded","size","lastmodified"]
JSON_OPERATORS = ["contains","doesnotcontain","is","isnot","startswith","endswith","greaterthan","lessthan","true","false"]
JSON_ORDER     = ['ascending','descending']
JSON_METHOD    = ["none","label","date","size","file","path","drivetype","title","track","time","artist","album","albumtype","genre","country","year","rating","votes","top250","programcount","playlist","episode","season","totalepisodes","watchedepisodes","tvshowstatus","showtitle","tvshowtitle","sorttitle","productioncode","mpaa","studio","dateadded","lastplayed","playcount","listeners","bitrate","random"] 
ITEM_TYPES     = ['genre','country','year','episode','season','sortepisode','sortseason','episodeguide','top250','setid','tracknumber','rating','userrating','watched','playcount','director','mpaa','plot','plotoutline','title','originaltitle','sorttitle','duration','studio','tagline','writer','tvshowtitle','premiered','set','tag','imdbnumber','aired','credits','lastplayed','album','artist','votes','path','trailer','dateadded','mediatype','dbid']
ART_PARAMS     = ["thumb","logo","poster","fanart","banner","landscape","clearart","clearlogo"]
IMAGE_LOC      = os.path.join(ADDON_PATH,'resources','skins','default','media')
LOGO           = os.path.join(IMAGE_LOC,'logo.png')
LANG           = 'en' #todo
CHAN_TYPES     = ['TV_Shows','TV_Networks','TV_Genres','MOVIE_Genres','MIXED_Genres','MOVIE_Studios'] 

# Maximum is 10 for this
RULES_PER_PAGE = 7
RULES_ACTION_START = 1
RULES_ACTION_JSON = 2
RULES_ACTION_FINAL_MADE = 32
RULES_ACTION_FINAL_LOADED = 64


def getSetting(key):
    # REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
    return REAL_SETTINGS.getSetting(key)
    
def getSettingBool(key):
    # REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
    try:
        return REAL_SETTINGS.getSettingBool(key)
    except:
        return REAL_SETTINGS.getSetting(key) == "true" 
    
def getSettingInt(key):
    # REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
    try: 
        return REAL_SETTINGS.getSettingInt(key)
    except:
        return int(REAL_SETTINGS.getSetting(key))

EXT_IMPORT       = getSetting('User_Import') == 'true'
EXT_IMPORT_M3U   = getSetting('Import_M3U')
EXT_IMPORT_XMLTV = getSetting('Import_XMLTV')

PARSE_DURATION   = getSetting('Parse_Duration') == 'true'
STORE_DURATION   = getSetting('Store_Duration') == 'true'
STRICT_DURATION  = getSetting('Strict_Duration') == 'true'    

UPDATE_OFFSET  = 3600#int((REAL_SETTINGS.getSettingInt('Update_Time') * 60) * 60) #seconds
INCLUDE_EXTRAS = False #todo user global
INCLUDE_STRMS  = False #todo user global

@contextmanager
def busy_dialog():
    log('globals: busy_dialog')
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try: yield
    finally: xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

def notificationDialog(message, header=ADDON_NAME, sound=False, time=4000, icon=ICON):
    log('globals: notificationDialog: ' + message)
    try: xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
    except Exception as e:
        log("globals: notificationDialog Failed! " + str(e), xbmc.LOGERROR)
        xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))

def yesnoDialog(message, heading=ADDON_NAME, nolabel='', yeslabel='', customlabel='', autoclose=0):
    return xbmcgui.Dialog().yesno(heading, message, nolabel, yeslabel, customlabel, autoclose)

def ProgressDialogBG(percent=0, control=None, message='', header=ADDON_NAME):
    if percent == 0 and control is None:
        control = xbmcgui.DialogProgressBG()
        control.create(header, message)
    elif control:
        if percent == 100 or control.isFinished(): return control.close()
        else: control.update(percent, message)
    return control
    
def log(msg, level=xbmc.LOGDEBUG):
    if not getSettingBool('Enable_Debugging') and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg = '%s, %s'%((msg),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,(msg)),level)
    
def hasPVR():
    return bool(xbmc.getCondVisibility('Pvr.HasTVChannels'))
    
def hasMusic():
    return bool(xbmc.getCondVisibility('Library.HasContent(Music)'))
    
def hasTV():
    return bool(xbmc.getCondVisibility('Library.HasContent(TVShows)'))
    
def hasMovie():
    return bool(xbmc.getCondVisibility('Library.HasContent(Movies)'))

def setBusy(state):
    setProperty("RUNNING",str(state))
    
def isBusy():
    return (getProperty("RUNNING") == "True")
    
def removeDUPS(lst):
    list_of_strings = [dumpJSON(d) for d in lst]
    list_of_strings = set(list_of_strings)
    return [loadJSON(s) for s in list_of_strings]
  
def dumpJSON(string, sortkey=True):
    return (json.dumps(string, sort_keys=sortkey))
    
def loadJSON(string):
    if not string: return {}
    try: return json.loads(string, strict=False)
    except Exception as e: log("globals: loadJSON failed! %s \n %s"%(e,string), xbmc.LOGERROR)
    return {}
    
def sendJSON(command):
    log('globals: sendJSON, command = %s'%(command))
    response = loadJSON(xbmc.executeJSONRPC(command))
    log('globals: sendJSON, response = %s'%(response))
    return response

def buildMenuListItem(label1="", label2="", iconImage=ICON, url="", infoItem=None, artItem=None, oscreen=True):
    listitem = xbmcgui.ListItem(label1, label2, path=url, offscreen=oscreen)
    if iconImage is None: iconImage=LOGO
    if infoItem: listitem.setInfo(infoItem)
    else: listitem.setInfo('video', {'mediatype': 'video',
                                     'Label' : label1,
                                     'Label2': label2,
                                     'Title' : label1})
    if artItem: listitem.setArt(artItem)
    else: listitem.setArt({'thumb': iconImage,
                           'clearlogo': iconImage})
    return listitem
    
def selectDialog(list, header=ADDON_NAME, autoclose=0, preselect=None, useDetails=True, multi=True):
    if multi == True:
        if preselect is None: preselect = []
        select = xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
    else:
        if preselect is None:  preselect = -1
        select = xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
    if select is not None: return select

def brutePVR():
    sendJSON('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":%s,"enabled":%s}, "id": 1}'%(PVR_CLIENT,'false'))
    xbmc.sleep(1000)
    sendJSON('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":%s,"enabled":%s}, "id": 1}'%(PVR_CLIENT,'true'))

def configurePVR():
    #todo add yesno prompt
    try:
        try: addon = xbmcaddon.Addon(PVR_CLIENT)
        except: 
            sendJSON('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":%s,"enabled":%s}, "id": 1}'%(PVR_CLIENT,'true'))
            xbmc.sleep(1000)
            addon = xbmcaddon.Addon(PVR_CLIENT)
            
        addon.setSetting('m3uRefreshMode', '1')
        addon.setSetting('m3uRefreshHour', '%s'%(int((UPDATE_OFFSET/60)/60)))
        addon.setSetting('m3uRefreshIntervalMins', '30')
        addon.setSetting('logoFromEpg', '1')
        addon.setSetting('logoPathType', '0')
        addon.setSetting('logoPath',  LOGO_LOC)
        addon.setSetting('m3uPathType', '0')
        addon.setSetting('m3uPath', M3UFLE)
        addon.setSetting('epgPathType', '0')
        addon.setSetting('epgPath', XMLTVFLE)
        addon.setSetting('epgTimeShift', '0')
        addon.setSetting('epgTSOverride', 'false')
        addon.setSetting('startNum', '1')
        addon.setSetting('useEpgGenreText', 'true')
        addon.setSetting('genresPathType', '0')
        addon.setSetting('genresPath', GENREFLE)
    except: notificationDialog(LANGUAGE(30049)%(PVR_CLIENT))
    
def hasSubtitle():
    return xbmc.getCondVisibility('VideoPlayer.HasSubtitles') == 1

def strpTime(datestring, format='%Y-%m-%d %H:%M:%S'):
    try: return datetime.datetime.strptime(datestring, format)
    except TypeError: return datetime.datetime.fromtimestamp(time.mktime(time.strptime(datestring, format)))

def getLocalTime():
    offset = (datetime.datetime.utcnow() - datetime.datetime.now())
    return time.time() + offset.total_seconds()

def getDeltaTime(time):
    datetime.datetime.fromtimestamp(time) + datetime.timedelta(time)

def escapeDirJSON(path):
    mydir = path
    if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
    return mydir
        
def convertListItemInfo(key, value):
    infomap = {'year':str}
    converter = infomap.get(key,None)
    if infomap.get(key,None) and value: value = converter(value) 
    if value: return value
        
def buildItemListItem(item, mType='video', oscreen=True, playable=True):
    info = item.copy()
    art  = info.get('art',{})
    streamInfo = item.get('streamdetails',{})
    info.pop('art',{})
    info.pop('streamdetails',{})
    listitem = xbmcgui.ListItem(offscreen=oscreen)
    [info.pop(key,{}) for key in list(info) if key.lower() not in ITEM_TYPES]
    [art.pop(key,{})  for key in list(art)  if key.lower() not in ART_PARAMS]
    [listitem.addStreamInfo(key, value) for key, values in streamInfo.items() for value in values]
    filepath = (item.get('file','') or item.get('url','') or item.get('path',''))
    listitem.setPath(filepath)
    listitem.setInfo(type=mType, infoLabels=info)
    listitem.setArt(art)
    listitem.setLabel2(info.get('label2',''))
    if playable: listitem.setProperty("IsPlayable","true")
    return listitem
    
    # item = {'streamdetails':[]}
    # 
    # 
    # for key, value in info.items(): item[key] = convertListItemInfo(key, value)
    # # for key, value in streamInfo.items(): item['streamdetails'][key] = convertListItemInfo(key, value)
    # listitem.setInfo(type=mType, infoLabels=item)
    
    
    # [info.pop(key,{}) for key in info.keys() if key.lower() not in ]
    # [listitem.addStreamInfo(key, value) for key, values in streamInfo.items() for value in values]
    # https://github.com/willforde/script.module.codequick/blob/master/script.module.codequick/lib/codequick/listing.py #todo improve using quickcode?
    
    # listitem.setArt(art)
    # listitem.setLabel2(info.get('label2',''))
    # if playable: listitem.setProperty("IsPlayable","true")
    # listitem.setProperty("ChannelName",self.name)
    # listitem.setProperty("ChannelType",str(self.chtype))
    # listitem.setProperty("ChannelNumber",str(self.channelNumber))
    # listitem.setProperty("ChannelLogo",self.logo)
    # listitem.setProperty("IsInternetStream","true")
    # listitem.setProperty("TimeStamp"  ,datetime.datetime.fromtimestamp(self.getItemTimestamp(index)).strftime("%Y-%m-%d %I:%M %p"))
    # return listitem
        
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
         
def getThumb(file):
    return (file['art'].get('tvshow.landscape','') or 
            file['art'].get('tvshow.fanart','')    or 
            file['art'].get('tvshow.poster','')    or
            file['art'].get('tvshow.thumb','')     or 
            file['art'].get('landscape','')        or
            file['art'].get('fanart','')           or 
            file['art'].get('poster','')           or
            file['art'].get('thumb','')            or
            FANART)

def getProperty(key, id=10000):
    try: 
        key = '%s.%s'%(ADDON_ID,key)
        value = xbmcgui.Window(id).getProperty(key)
        if value: log("globals: getProperty, key = " + key + ", value = " + value)
        return value
    except Exception as e: return ''
          
def setProperty(key, value, id=10000):
    key = '%s.%s'%(ADDON_ID,key)
    log("globals: setProperty, key = " + key + ", value = " + value)
    try: xbmcgui.Window(id).setProperty(key, value)
    except Exception as e: log("globals: setProperty, Failed! " + str(e), xbmc.LOGERROR)

def clearProperty(key, id=10000):
    key = '%s.%s'%(ADDON_ID,key)
    xbmcgui.Window(id).clearProperty(key)

def assertLST(lst1,lst2): #test if both lists match. 
    assertBool = len(diffLST(lst1,lst2)) == 0
    log('globals: assertLST = %s'%(assertBool))
    return assertBool
    
def diffLST(lst1, lst2): 
    difference = (list(set(lst1) - set(lst2)))
    log('globals: diffLST = %s'%(difference))
    return difference
    
def assertDICT(dict1,dict2): #test if both dicts match. 
    assertBool = len(diffDICT(dict1,dict2)) == 0
    log('globals: assertDICT = %s'%(assertBool))
    return assertBool
    
def diffDICT(dict1, dict2): 
    intersec = [item for item in dict1 if item in dict2]
    difference = [item for item in chain(dict1,dict2) if item not in intersec]
    log('globals: diffDICT = %s'%(dumpJSON(difference)))
    return difference

def isPseudoTV():
    #todo improve check
    return xbmc.getInfoLabel("VideoPlayer.Writer").find('"data"') >= 0
  
def setCurrentChannelItem(item):
    setProperty('channel_item',dumpJSON(item))
    
def getCurrentChannelItem():  
    return loadJSON(getProperty('channel_item'))
  
def clearCurrentChannelItem():
    clearProperty('channel_item')
  
def getChannelID(name, path):
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s'%(name, hashlib.md5(path.encode('utf-8')))
    return '%s@%s'%((binascii.hexlify(tmpid.encode("utf-8"))[:32]).decode("utf-8"),slugify(ADDON_NAME))

def slugify(text):
    non_url_safe = [' ','"', '#', '$', '%', '&', '+',',', '/', ':', ';', '=', '?','@', '[', '\\', ']', '^', '`','{', '|', '}', '~', "'"]
    non_url_safe_regex = re.compile(r'[{}]'.format(''.join(re.escape(x) for x in non_url_safe)))
    text = non_url_safe_regex.sub('', text).strip()
    text = u'_'.join(re.split(r'\s+', text))
    return text

def interleave(*args): #interleave multi-lists, while preserving order
    try:
        iters = list(map(iter, args))
        while iters:
            it = random.choice(iters)
            try:
                yield next(it)
            except StopIteration:
                iters.remove(it)
    except:
        return chain.from_iterable(args)
        
def isSubtitle():
    return bool(xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled'))
    
def installAddon(id):
    if xbmc.getCondVisibility('System.HasAddon("%s")'%(id)) == 1: return
    xbmc.executebuiltin('InstallAddon("%s")'%(id))
        
def getRandomPage(limit,total=50):
    page = random.randrange(0, total, limit)
    log('global: getRandomPage, page = %s'%(page))
    return page, page+limit
    
def isPlaylistRandom():
    return xbmc.getInfoLabel('Playlist.Random').lower() == 'random' # Disable auto playlist shuffling if it's on
      
def findItemsinListItem(listitems, values, key='getLabel', index=True):
    log("globals: findItemsinListItem, values = %s, key = %s, index = %s"%(values, key, index))
    found = []
    if len(values[0]) == 0: return [-1]
    for idx, item in enumerate(listitems):
        for value in values:
            if key == 'getLabel':
                if item.getLabel().lower() == value.lower():
                    found.append(idx if index else item)
            elif key == 'getLabel2':
                if item.getLabel2().lower() == value.lower():
                    found.append(idx if index else item)
    log("globals: findItemsinListItem, found = %s"%(found))
    return found

def rollbackTime(stime,offset=30): # round the given time down to the nearest
    n = datetime.datetime.fromtimestamp(stime)
    delta = datetime.timedelta(minutes=offset)
    remaining = offset - n.minute 
    if n.minute > (offset-1): n = n.replace(minute=offset, second=0, microsecond=0)
    else: n = n.replace(minute=0, second=0, microsecond=0)
    return time.mktime(n.timetuple())

def pagination(list, end):
    for start in xrange(0, len(list), end):
        yield seq[start:start+end]
        
class PoolHelper:
    def __init__(self):
        if ENABLE_POOL: 
            self.pool = ThreadPool(CORES)
            log("PoolHelper: CPU CORES = " + str(CORES))
        else: log("PoolHelper: ThreadPool Disabled")
        

    def runSelf(self, func):
        func()
        
        
    def poolList(self, method, items=None, args=None, chunk=25):
        log("PoolHelper: poolList")
        results = []
        if ENABLE_POOL:
            if items is None: results = self.pool.imap_unordered(self.runSelf, method, chunksize=chunk)
            elif args is not None: results = self.pool.imap_unordered(method, zip(items,repeat(args)))
            else: results = self.pool.imap_unordered(method, items, chunksize=chunk)
            self.pool.close()   
            self.pool.join()
        else:
            if items is None: [self.runSelf(func) for func in method]
            elif args is not None: results = [method((item, args)) for item in items]
            else: results = [method(item) for item in items]
        results = filter(None, results)
        return results