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
import shutil, subprocess, io
import codecs, random
import uuid, base64, binascii, hashlib
import time, datetime
import heapq

from threading        import Lock, Thread, Event, Timer, BoundedSemaphore
from threading        import enumerate as thread_enumerate
from xml.dom.minidom  import parse, parseString, Document

from variables   import *
from kodi_six    import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from contextlib  import contextmanager, closing
from socket      import gethostbyname, gethostname
from itertools   import cycle, chain, zip_longest, islice
from xml.sax.saxutils import escape, unescape
from ast         import literal_eval
from operator    import itemgetter


from logger      import *
from cache       import Cache, cacheit
from pool        import killit, timeit, poolit, executeit, timerit, threadit
from kodi        import *
from fileaccess  import FileAccess, FileLock
from collections import defaultdict, Counter, OrderedDict
from six.moves   import urllib 
from socket      import timeout
from math        import ceil,  floor
from infotagger.listitem import ListItemInfoTag

MONITOR             = xbmc.Monitor()
PLAYER              = xbmc.Player()
DIALOG              = Dialog()
PROPERTIES          = DIALOG.properties
SETTINGS            = DIALOG.settings
LISTITEMS           = DIALOG.listitems
BUILTIN             = DIALOG.builtin

def setPendingRestart(state=True):
    if state: DIALOG.notificationDialog('%s\n%s'%(LANGUAGE(32157),LANGUAGE(32124)))
    return PROPERTIES.setEXTProperty('pendingRestart',str(state).lower())

def slugify(s, lowercase=False):
  if lowercase: s = s.lower()
  s = s.strip()
  s = re.sub(r'[^\w\s-]', '', s)
  s = re.sub(r'[\s_-]+', '_', s)
  s = re.sub(r'^-+|-+$', '', s)
  return s
        
def validString(s):
    return "".join( x for x in s if (x.isalnum() or x in "._- "))
        
def stripNumber(s):
    return re.sub(r'\d+','',s)
    
def stripRegion(s):
    try:
        match = re.compile('(.*) \((.*)\)', re.IGNORECASE).search(s)
        if match.group(1): return match.group(1)
    except: return s
    
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
    fle  = (FileAccess.open(file, 'r') or '')
    try:
        data = loadJSON(fle.read())
    except Exception as e:
        log('Globals: getJSON failed! %s'%(e), xbmc.LOGERROR)
        data = {}
    fle.close()
    return data

def setJSON(file, data):
    with FileLock():
        fle = FileAccess.open(file, 'w')
        fle.write(dumpJSON(data, idnt=4, sortkey=False))
        fle.close()
    return True

def getURL(url):
    try: return urllib.request.urlopen(url).read()
    except Exception as e: 
        log("getURL, failed! %s"%e, xbmc.LOGERROR)
     
def setURL(url, file):
    try:
        contents = urllib.request.urlopen(url).read()
        fle = FileAccess.open(file, 'w')
        fle.write(contents)
        fle.close()
        return FileAccess.exists(file)
    except Exception as e: 
        log("saveURL, failed! %s"%e, xbmc.LOGERROR)

def diffLSTDICT(old, new):
    sOLD = set([dumpJSON(e) for e in old])
    sNEW = set([dumpJSON(e) for e in new])
    sDIFF = sOLD.symmetric_difference(sNEW)
    return setDictLST([loadJSON(e) for e in sDIFF])

def getIP(wait=5):
    while not MONITOR.abortRequested() and wait > 0:
        ip = xbmc.getIPAddress()
        if ip: return ip
        elif (MONITOR.waitForAbort(1.0)): break
        else: wait -= 1
    return gethostbyname(gethostname())

def getChannelID(name, path, number):
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)))
    return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:32]).decode(DEFAULT_ENCODING),slugify(ADDON_NAME))
    
def getRecordID(name, path, number):
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)))
    return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:16]).decode(DEFAULT_ENCODING),slugify(ADDON_NAME))

def splitYear(label):
    try:
        match = re.compile('(.*) \((.*)\)', re.IGNORECASE).search(label)
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
    label = (item.get('name','') or item.get('label','') or item.get('showtitle','') or item.get('title',''))
    if not label: return ''
    label, year = splitYear(label)
    year = (item.get('year','') or year)
    if year and addYear: return '%s (%s)'%(label, year)
    return label
   
def hasFile(file):
    if file.startswith(tuple(VFS_TYPES)):
        if file.startswith('plugin://'): return hasAddon(file)
        else: return True
    else: return FileAccess.exists(file)

def hasAddon(id, install=False, enable=False, force=False, notify=False):
    id = getIDbyPath(id)
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
        random.seed(random.randint(0,999999999999)) #reseed random for a "greater sudo random".
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

def togglePVR(state=True, reverse=False, wait=15):
    log('globals: togglePVR, state = %s, reverse = %s, wait = %s'%(state,reverse,wait))
    if not (BUILTIN.getInfoBool('IsPlayingTv','Pvr') | BUILTIN.getInfoBool('IsPlayingRadio','Pvr') | BUILTIN.getInfoBool('IsPlayingRecording','Pvr')):
        isEnabled = BUILTIN.getInfoBool('AddonIsEnabled(%s)'%(PVR_CLIENT_ID),'System')
        if (state and isEnabled) or (not state and not isEnabled): return
        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":%s}, "id": 1}'%(PVR_CLIENT_ID,str(state).lower()))
        if reverse:
            timerit(togglePVR)(wait,[not bool(state)])
            DIALOG.notificationWait('%s: %s'%(PVR_CLIENT_NAME,LANGUAGE(32125)),wait=wait)

def isRadio(item):
    if item.get('radio',False) or item.get('type','') == "Music Genres": return True
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
    text = re.sub('\[COLOR=(.+?)\]', '', text)
    text = re.sub('\[/COLOR\]', '', text)
    text = text.replace("[B]",'').replace("[/B]",'')
    text = text.replace("[I]",'').replace("[/I]",'')
    return text.replace(":",'')
  
def cleanImage(image=LOGO):
    orgIMG = image
    if not image: image = LOGO
    if not image.startswith(('image://','resource://','special://')):
        realPath = xbmcvfs.translatePath('special://home/addons/')
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

def getIDbyPath(path):
    try:
        if   path.startswith('special://'): return re.compile('special://home/addons/(.*?)/resources', re.IGNORECASE).search(path).group(1)
        elif path.startswith('plugin://'):  return re.compile('plugin://(.*?)/', re.IGNORECASE).search(path).group(1)
    except Exception as e: log('Globals: getIDbyPath failed! %s'%(e), xbmc.LOGERROR)
    return path
    
def mergeDictLST(dict1,dict2):
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
       
def interleave(seqs): 
    #evenly interleave multi-lists of different sizes, while preserving seqs order
    #[1, 'a', 'A', 2, 'b', 'B', 3, 'c', 'C', 4, 'd', 'D', 'e', 'E']
    return [_f for _f in chain.from_iterable(zip_longest(*seqs)) if _f]
        
def intersperse(*seqs):
    #interleave multi-lists, while preserving order distribution
    def distribute(seq):
        for i, x in enumerate(seq, 1):
            yield i/(len(seq) + 1), x
    distributions = list(map(distribute, seqs))
    #['a', 'A', 1, 'b', 'B', 2, 'c', 'C', 3, 'd', 'D', 4, 'e', 'E']
    for _, x in sorted(chain(*distributions), key=itemgetter(0)):
        yield x
        
def distribute(*seq):
    #randomly distribute multi-lists of different sizes.
    #['a', 'A', 'B', 1, 2, 'C', 3, 'b', 4, 'D', 'c', 'd', 'e', 'E']
    iters = list(map(iter, seqs))
    while not MONITOR.abortRequested() and iters:
        it = random.choice(iters)
        try:   yield next(it)
        except StopIteration:
            iters.remove(it)
            
def percentDiff(org, new):
    try: return (abs(float(org) - float(new)) / float(new)) * 100.0
    except ZeroDivisionError: return -1
        
def pagination(list, end):
    for start in range(0, len(list), end):
        yield seq[start:start+end]
