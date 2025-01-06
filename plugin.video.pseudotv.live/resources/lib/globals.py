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

import os, sys, re, json, struct, errno, zlib
import shutil, subprocess, io, platform
import codecs, random
import uuid, base64, binascii, hashlib
import time, datetime
import heapq, requests, pyqrcode

from six.moves           import urllib 
from io                  import StringIO, BytesIO
from threading           import Lock, Thread, Event, Timer, BoundedSemaphore
from threading           import enumerate as thread_enumerate
from xml.dom.minidom     import parse, parseString, Document

from variables           import *
from kodi_six            import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from contextlib          import contextmanager, closing
from socket              import gethostbyname, gethostname
from itertools           import cycle, chain, zip_longest, islice
from xml.sax.saxutils    import escape, unescape
from operator            import itemgetter

from logger              import *
from cache               import Cache, cacheit
from pool                import killit, timeit, poolit, executeit, timerit, threadit
from kodi                import *
from fileaccess          import FileAccess, FileLock
from collections         import defaultdict, Counter, OrderedDict
from six.moves           import urllib 
from math                import ceil,  floor
from infotagger.listitem import ListItemInfoTag
from requests.adapters   import HTTPAdapter, Retry

DIALOG              = Dialog()
PROPERTIES          = DIALOG.properties
SETTINGS            = DIALOG.settings
LISTITEMS           = DIALOG.listitems
BUILTIN             = DIALOG.builtin

def slugify(s, lowercase=False):
  if lowercase: s = s.lower()
  s = s.strip()
  s = re.sub(r'[^\w\s-]', '', s)
  s = re.sub(r'[\s_-]+', '_', s)
  s = re.sub(r'^-+|-+$', '', s)
  return s
        
def validString(s):
    return "".join(x for x in s if (x.isalnum() or x not in '\\/:*?"<>|'))
        
def stripNumber(s):
    return re.sub(r'\d+','',s)
    
def stripRegion(s):
    match = re.compile(r'(.*) \((.*)\)', re.IGNORECASE).search(s)
    if match: return match.group(1)
    
def chanceBool(percent=25):
    return random.randrange(100) <= percent

def decodePlot(text: str = '') -> dict:
    plot = re.search(r'\[COLOR item=\"(.+?)\"]\[/COLOR]', text)
    if plot: return loadJSON(decodeString(plot.group(1)))
    return {}
    
def encodePlot(plot, text):
    return '%s [COLOR item="%s"][/COLOR]'%(plot,encodeString(dumpJSON(text)))
    
def escapeString(text, table=HTML_ESCAPE):
    return escape(text,table)
    
def unescapeString(text, table=HTML_ESCAPE):
    return unescape(text,{v:k for k, v in list(table.items())})

def getJSON(file):
    data = {}
    try: 
        fle  = FileAccess.open(file,'r')
        data = loadJSON(fle.read())
    except Exception as e: log('Globals: getJSON failed! %s\nfile = %s'%(e,file), xbmc.LOGERROR)
    fle.close()
    return data

def setJSON(file, data):
    with FileLock():
        fle = FileAccess.open(file, 'w')
        fle.write(dumpJSON(data, idnt=4, sortkey=False))
        fle.close()
    return True

def requestURL(url, params={}, data={}, header=HEADER, timeout=FIFTEEN, json_data=False, cache=None, checksum=ADDON_VERSION, life=datetime.timedelta(minutes=15)):
    def __error(json_data):
        return {} if json_data else ""
    
    def __getCache(key,json_data,cache,checksum):
        cacheName = 'requestURL.%s'%(key)
        return (cache.get(cacheName, checksum, json_data) or __error(json_data))
        
    def __setCache(key,data,json_data,cache,checksum,life):
        cacheName = 'requestURL.%s'%(key)
        return cache.set(cacheName, data, checksum, life, json_data)
    
    cacheKey = '.'.join([url,dumpJSON(params),dumpJSON(data),dumpJSON(header)])
    session  = requests.Session()
    retries  = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter  = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    try:
        headers = HEADER.copy()
        headers.update(header)
        if params: response = session.post(url, data=data, headers=headers, timeout=timeout)
        else:      response = session.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()  # Raise an exception for HTTP errors
        log("Globals: requestURL, url = %s, status = %s"%(url,response.status_code))
        if json_data: results = response.json()
        else:         results = response.content
        if results and cache: return __setCache(cacheKey,results,json_data,cache,checksum,life)
        else:                 return results
    except requests.exceptions.ConnectionError as e:
        log("Globals: requestURL, failed! Error connecting to the server: %s"%('Returning cache' if cache else 'No Response'))
        return __getCache(cacheKey,json_data,cache,checksum) if cache else __error(json_data)
    except requests.exceptions.HTTPError as e:
        log("Globals: requestURL, failed! HTTP error occurred: %s\n%s"%('Returning cache' if cache else 'No Response'))
        return __getCache(cacheKey,json_data,cache,checksum) if cache else __error(json_data)
    except requests.exceptions.RequestException as e:
        log("Globals: requestURL, failed! An error occurred: %s"%(e), xbmc.LOGERROR)
        return __error(json_data)
     
def setURL(url, file):
    try:
        contents = requestURL(url)
        fle = FileAccess.open(file, 'w')
        fle.write(contents)
        fle.close()
        return FileAccess.exists(file)
    except Exception as e: log('Globals: setURL failed! %s\nurl = %s'%(e,url), xbmc.LOGERROR)

def diffLSTDICT(old, new):
    sOLD = set([dumpJSON(e) for e in old])
    sNEW = set([dumpJSON(e) for e in new])
    sDIFF = sOLD.symmetric_difference(sNEW)
    return setDictLST([loadJSON(e) for e in sDIFF])

def getChannelID(name, path, number):
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)),SETTINGS.getMYUUID())
    return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:32]).decode(DEFAULT_ENCODING),slugify(ADDON_NAME))
    
def getRecordID(name, path, number):
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)))
    return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:16]).decode(DEFAULT_ENCODING),slugify(ADDON_NAME))

def splitYear(label):
    try:
        match = re.compile(r'(.*) \((.*)\)', re.IGNORECASE).search(label)
        if match and match.group(2):
            label, year = match.groups()
            if year.isdigit():
                return label, int(year)
    except: pass
    return label, None

def getChannelSuffix(name, type):
    name = validString(name)
    if   type == "TV Genres"    and not LANGUAGE(32014) in name: suffix = LANGUAGE(32014) #TV
    elif type == "Movie Genres" and not LANGUAGE(32015) in name: suffix = LANGUAGE(32015) #Movies
    elif type == "Mixed Genres" and not LANGUAGE(32010) in name: suffix = LANGUAGE(32010) #Mixed
    elif type == "Music Genres" and not LANGUAGE(32016) in name: suffix = LANGUAGE(32016) #Music
    else: return name
    return '%s %s'%(name,suffix)
 
def cleanChannelSuffix(name, type):
    if   type == "TV Genres"    : name = name.split(' %s'%LANGUAGE(32014))[0]#TV
    elif type == "Movie Genres" : name = name.split(' %s'%LANGUAGE(32015))[0]#Movies
    elif type == "Mixed Genres" : name = name.split(' %s'%LANGUAGE(32010))[0]#Mixed
    elif type == "Music Genres" : name = name.split(' %s'%LANGUAGE(32016))[0]#Music
    return name
            
def getLabel(item, addYear=False):
    label = (item.get('name') or item.get('label') or item.get('showtitle') or item.get('title'))
    if not label: return ''
    label, year = splitYear(label)
    year = (item.get('year') or year)
    if year and addYear: return '%s (%s)'%(label, year)
    return label
   
def hasFile(file):
    if file.startswith(tuple(VFS_TYPES)):
        if file.startswith('plugin://'): return hasAddon(file)
        else: return True
    else: return FileAccess.exists(file)

def hasAddon(id, install=False, enable=False, force=False, notify=False):
    if '://' in id: id = getIDbyPath(id)
    if BUILTIN.getInfoBool('HasAddon(%s)'%(id),'System'):
        if BUILTIN.getInfoBool('AddonIsEnabled(%s)'%(id),'System'): return True
        elif enable: 
            if not force:
                if not DIALOG.yesnoDialog(message=LANGUAGE(32156)%(id)): return False
            return BUILTIN.executebuiltin('EnableAddon(%s)'%(id),wait=True)
    elif install: return BUILTIN.executebuiltin('InstallAddon(%s)'%(id),wait=True)
    if notify: DIALOG.notificationDialog(LANGUAGE(32034)%(id))
    return False

def openAddonSettings(ctl=(0,1),id=ADDON_ID):
    BUILTIN.closeBusyDialog()
    BUILTIN.executebuiltin('Addon.OpenSettings(%s)'%id)
    xbmc.sleep(100)
    BUILTIN.executebuiltin('SetFocus(%i)'%(ctl[0]-200))
    xbmc.sleep(50)
    BUILTIN.executebuiltin('SetFocus(%i)'%(ctl[1]-180))
    return True

def diffRuntime(dur, roundto=15):
    def ceil_dt(dt, delta):
        return dt + (datetime.datetime.min - dt) % delta
    now = datetime.datetime.fromtimestamp(dur)
    return (ceil_dt(now, datetime.timedelta(minutes=roundto)) - now).total_seconds()

def roundTimeDown(dt, offset=30): # round the given time down to the nearest
    n = datetime.datetime.fromtimestamp(dt)
    delta = datetime.timedelta(minutes=offset)
    if n.minute > (offset-1): n = n.replace(minute=offset, second=0, microsecond=0)
    else: n = n.replace(minute=0, second=0, microsecond=0)
    return time.mktime(n.timetuple())
    
def roundTimeUp(dt=None, roundTo=60):
   if dt == None : dt = datetime.datetime.now()
   seconds = (dt.replace(tzinfo=None) - dt.min).seconds
   rounding = (seconds+roundTo/2) // roundTo * roundTo
   return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)
   
def strpTime(datestring, format=DTJSONFORMAT): #convert json pvr datetime string to datetime obj, thread safe!
    try:              return datetime.datetime.strptime(datestring, format)
    except TypeError: return datetime.datetime.fromtimestamp(time.mktime(time.strptime(datestring, format)))
    except:           return ''

def getTimeoffset():
    return (int((datetime.datetime.now() - datetime.datetime.utcnow()).days * 86400 + round((datetime.datetime.now() - datetime.datetime.utcnow()).seconds, -1)))
    
def getUTCstamp():
    return time.time() - getTimeoffset()

def getGMTstamp():
    return time.time()

def randomShuffle(items=[]):
    if len(items) > 0:
        #reseed random for a "greater sudo random"
        random.seed(random.randint(0,999999999999))
        random.shuffle(items)
    return items
    
def isStack(path): #is path a stack
    return path.startswith('stack://')

def splitStacks(path): #split stack path for indv. files.
    if not isStack(path): return [path]
    return [_f for _f in ((path.split('stack://')[1]).split(' , ')) if _f]

def escapeDirJSON(path):
    mydir = path
    if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
    return mydir
      
def KODI_LIVETV_SETTINGS(): #recommended Kodi LiveTV settings
    return {'pvrmanager.preselectplayingchannel' :'true',
            'pvrmanager.syncchannelgroups'       :'true',
            'pvrmanager.backendchannelorder'     :'true',
            'pvrmanager.usebackendchannelnumbers':'true',
            'pvrplayback.autoplaynextprogramme'  :'true',
            # 'pvrmenu.iconpath':'',
            # 'pvrplayback.switchtofullscreenchanneltypes':1,
            # 'pvrplayback.confirmchannelswitch':'true',
            # 'epg.selectaction':2,
            # 'epg.epgupdate':120,
           'pvrmanager.startgroupchannelnumbersfromone':'false'}

def togglePVR(state=True, reverse=False, wait=FIFTEEN):
    if SETTINGS.getSettingBool('Enable_PVR_RELOAD'):
        isEnabled = BUILTIN.getInfoBool('AddonIsEnabled(%s)'%(PVR_CLIENT_ID),'System')
        if (state and isEnabled) or (not state and not isEnabled): return
        elif not PROPERTIES.isRunning('togglePVR'):
            with PROPERTIES.setRunning('togglePVR'):
                log('globals: togglePVR, state = %s, reverse = %s, wait = %s'%(state,reverse,wait))
                xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":%s}, "id": 1}'%(PVR_CLIENT_ID,str(state).lower()))
            if not reverse: return
            MONITOR().waitForAbort(1.0)
            with BUILTIN.busy_dialog(): timerit(togglePVR)(wait,[not bool(state)])
            DIALOG.notificationWait('%s: %s'%(PVR_CLIENT_NAME,LANGUAGE(32125)),wait=wait)
    else: DIALOG.notificationWait(LANGUAGE(30023)%(PVR_CLIENT_NAME))
        
def isRadio(item):
    if item.get('radio',False) or item.get('type') == "Music Genres": return True
    for path in item.get('path',[item.get('file','')]):
        if path.lower().startswith(('musicdb://','special://profile/playlists/music/','special://musicplaylists/')): return True
    return False
    
def isMixed(item):
    for path in item.get('path',[item.get('file','')]):
        if path.lower().startswith('special://profile/playlists/mixed/'): return True
    return False
         
def playSFX(filename, cached=False):
    xbmc.playSFX(filename, useCached=cached)

def cleanLabel(text):
    text = re.sub(r'\[COLOR=(.+?)\]', '', text)
    text = re.sub(r'\[/COLOR\]', '', text)
    text = text.replace("[B]",'').replace("[/B]",'')
    text = text.replace("[I]",'').replace("[/I]",'')
    return text.replace(":",'')
  
def cleanImage(image=LOGO):
    if not image: image = LOGO
    if not image.startswith(('image://','resource://','special://','smb://','nfs://','https://','http://')):
        realPath = FileAccess.translatePath('special://home/addons/')
        if image.startswith(realPath):# convert real path. to vfs
            image = image.replace(realPath,'special://home/addons/').replace('\\','/')
        elif image.startswith(realPath.replace('\\','/')):
            image = image.replace(realPath.replace('\\','/'),'special://home/addons/').replace('\\','/')
    return image
            
def cleanGroups(citem, enableGrouping=SETTINGS.getSettingBool('Enable_Grouping')):
    if not enableGrouping:
        citem['group'] = [ADDON_NAME]
    else:
        citem['group'].append(ADDON_NAME)
        if citem.get('favorite',False) and not LANGUAGE(32019) in citem['group']:
            citem['group'].append(LANGUAGE(32019))
        elif not citem.get('favorite',False) and LANGUAGE(32019) in citem['group']:
             citem['group'].remove(LANGUAGE(32019))
    return sorted(set(citem['group']))
        
def cleanMPAA(mpaa):
    orgMPA = mpaa
    mpaa = mpaa.lower()
    if ':'      in mpaa: mpaa = re.split(':',mpaa)[1]       #todo prop. regex
    if 'rated ' in mpaa: mpaa = re.split('rated ',mpaa)[1]  #todo prop. regex
    #todo regex, detect other region rating formats
    # re.compile(':(.*)', re.IGNORECASE).search(text))
    text = mpaa.upper()
    try:
        text = re.sub('/ US', ''  , text)
        text = re.sub('Rated ', '', text)
        mpaa = text.strip()
    except: 
        mpaa = mpaa.strip()
    return mpaa

def getIDbyPath(url):
    try:
        if   url.startswith('special://'): return re.compile('special://home/addons/(.*?)/resources', re.IGNORECASE).search(url).group(1)
        elif url.startswith('plugin://'):  return re.compile('plugin://(.*?)/', re.IGNORECASE).search(url).group(1)
    except Exception as e: log('Globals: getIDbyPath failed! url = %s, %s'%(url,e), xbmc.LOGERROR)
    return url
    
def combineDicts(dict1={}, dict2={}):
    for k,v in list(dict1.items()):
        if dict2.get(k): k = dict2.pop(k)
    dict1.update(dict2)
    return dict1
    
def mergeDictLST(dict1={},dict2={}):
    for k, v in list(dict2.items()):
        dict1.setdefault(k,[]).extend(v)
        setDictLST()
    return dict1
    
def lstSetDictLst(lst=[]):
    items = dict()
    for key, dictlst in list(lst.items()):
        if isinstance(dictlst, list): dictlst = setDictLST(dictlst)
        items[key] = dictlst
    return items
    
def compareDict(dict1,dict2,sortKey):
    a = sorted(dict1, key=itemgetter(sortKey))
    b = sorted(dict2, key=itemgetter(sortKey))
    return a == b
    
def subZoom(number,percentage,multi=100):
    return round(number * (percentage*multi) / 100)
    
def addZoom(number,percentage,multi=100):
    return round((number - (number * (percentage*multi) / 100)) + number)
   
def frange(start,stop,inc):
    return [x/10.0 for x in range(start,stop,inc)]
    
def timeString2Seconds(string): #hh:mm:ss
    try:    return int(sum(x*y for x, y in zip(list(map(float, string.split(':')[::-1])), (1, 60, 3600, 86400))))
    except: return -1

def chunkLst(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def chunkDict(items, n):
    it = iter(items)
    for i in range(0, len(items), n):
        yield {k:items[k] for k in islice(it, n)}
    
def roundupDIV(p, q):
    try:
        d, r = divmod(p, q)
        if r: d += 1
        return d
    except ZeroDivisionError: 
        return 1
       
def interleave(seqs, sets=1): 
    #evenly interleave multi-lists of different sizes, while preserving seq order and by sets of x
    # In         [[1,2,3,4,5],['a','b','c','d'],['A','B','C','D','E']]
    # Out sets=0 [1, 2, 3, 4, 5, 'a', 'b', 'c', 'd', 'A', 'B', 'C', 'D', 'E']
    # Out sets=1 [1, 'a', 'A', 2, 'b', 'B', 3, 'c', 'C', 4, 'd', 'D', 5, 'E']
    # Out sets=2 [1, 2, 'a', 'b', 'A', 'B', 3, 4, 'c', 'd', 'C', 'D', 5, 'E']
    if sets > 0:
        seqs = [list(zip_longest(*[iter(seqs)] * sets, fillvalue=None)) for seqs in seqs]
        return list([_f for _f in sum([_f for _f in chain.from_iterable(zip_longest(*seqs)) if _f], ()) if _f])
    else: return list(chain.from_iterable(seqs))
        
def percentDiff(org, new):
    try: return (abs(float(org) - float(new)) / float(new)) * 100.0
    except ZeroDivisionError: return -1
        
def pagination(list, end):
    for start in range(0, len(list), end):
        yield seq[start:start+end]

def isCenterlized():
    default = 'special://profile/addon_data/plugin.video.pseudotv.live/cache'
    if REAL_SETTINGS.getSetting('User_Folder') == default:
        return False
    return True
                