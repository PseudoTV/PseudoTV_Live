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

import os, sys, re, json, struct, errno 
import shutil, subprocess
import codecs, random
import uuid, base64, binascii, hashlib
import time, datetime

from threading  import Thread, Event
from queue      import Empty, PriorityQueue

from variables   import *
from kodi_six    import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from contextlib  import contextmanager, closing
from socket      import gethostbyname, gethostname
from itertools   import cycle, chain, zip_longest, islice
from xml.sax.saxutils import escape, unescape
from ast         import literal_eval

from logger      import *
from cache       import Cache, cacheit
from pool        import killJSON, killit, timeit, poolit, threadit, timerit
from kodi        import *
from fileaccess  import FileAccess, FileLock
from collections import Counter, OrderedDict
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

@contextmanager
def setRunning(key):
    PROPERTIES.setEXTProperty('%s.%s'%(ADDON_ID,key),'true')
    try: yield
    finally:
        PROPERTIES.setEXTProperty('%s.%s'%(ADDON_ID,key),'false')

def isRunning(key):
    return PROPERTIES.getEXTProperty('%s.%s'%(ADDON_ID,key)) == 'true'

@contextmanager
def suspendActivity(): #suspend/quit running background task.
    while not MONITOR.abortRequested():
        if MONITOR.waitForAbort(0.001): break
        elif not isPendingSuspend(): break
    setPendingSuspend(True)
    try: yield
    finally:
        setPendingSuspend(False)

def isPendingSuspend():
    return PROPERTIES.getEXTProperty('%s.pendingSuspend'%(ADDON_ID)) == 'true'

def setPendingSuspend(state=True):
    PROPERTIES.setEXTProperty('%s.pendingSuspend'%(ADDON_ID),str(state).lower())

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
    try:
        message_bytes = base64.b64decode(base64_bytes.encode(DEFAULT_ENCODING))
        return message_bytes.decode(DEFAULT_ENCODING)
    except:
        pass

def escapeString(text, table=HTML_ESCAPE):
    return escape(text,table)
    
def unescapeString(text, table=HTML_ESCAPE):
    return unescape(text,{v:k for k, v in list(table.items())})

def getJSON(file):
    fle  = (FileAccess.open(file, 'r') or '')
    try:    data = loadJSON(fle.read())
    except: data = {}
    fle.close()
    return data
    
def setJSON(file, data):
    with FileLock():
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

def removeDUPDICT(d):
    return [dict(t) for t in {tuple(d.items()) for d in l}]

def diffLSTDICT(old, new):
    sOLD = set([dumpJSON(e) for e in old])
    sNEW = set([dumpJSON(e) for e in new])
    sDIFF = sOLD.symmetric_difference(sNEW)
    return setDictLST([loadJSON(e) for e in sDIFF])

def setInstanceID():
    PROPERTIES.setEXTProperty('%s.InstanceID'%(ADDON_ID),uuid.uuid4())

def getInstanceID():
    instanceID = PROPERTIES.getEXTProperty('%s.InstanceID'%(ADDON_ID))
    if not instanceID: setInstanceID()
    return PROPERTIES.getEXTProperty('%s.InstanceID'%(ADDON_ID))

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
 
def hasAddon(id, install=False, enable=False, force=False, notify=False):
    if BUILTIN.getInfoBool('HasAddon(%s)'%(id),'System'):
        if BUILTIN.getInfoBool('AddonIsEnabled(%s)'%(id),'System'): return True
        elif enable: 
            if not force:
                if not DIALOG.yesnoDialog(message=LANGUAGE(32156)%(id),autoclose=90): return False
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
    
def pagination(list, end):
    for start in range(0, len(list), end):
        yield seq[start:start+end]
        
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
        random.seed(random.randint(0,999999999999)) #reseed random for a "greater random effect".
        random.shuffle(items)
    return items
    
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
    for _, x in sorted(chain(*distributions), key=operator.itemgetter(0)):
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
    return [_f for _f in ((path.split('stack://')[1]).split(' , ')) if _f]
            
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
            'pvrplayback.autoplaynextprogramme'  :'true',
            # 'pvrmenu.iconpath':'',
            # 'pvrplayback.switchtofullscreenchanneltypes':1,
            # 'pvrplayback.confirmchannelswitch':'true',
            # 'epg.selectaction':2,
            # 'epg.epgupdate':120,
           'pvrmanager.startgroupchannelnumbersfromone':'false'}

def IPTV_SIMPLE_SETTINGS(): #recommended IPTV Simple settings
    CLIENT_MODE = SETTINGS.getSettingInt('Client_Mode')
    return {'kodi_addon_instance_name'    :ADDON_NAME,
            'kodi_addon_instance_enabled' :'true',
            'm3uRefreshMode'              :'1',
            'm3uRefreshIntervalMins'      :'15',
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
            'defaultProviderName'         :ADDON_NAME,
            # 'providerMappingFile'         :PROVIDERFLEPATH,#todo
            # 'useEpgGenreText'             :'true',
            'logoFromEpg'                 :'1',
            'catchupEnabled'              :'true',
            'catchupPlayEpgAsLive'        :'false',
            'allChannelsCatchupMode'      :'0',
            'numberByOrder'               :'false',
            'startNum'                    :'1',
            # 'epgTSOverride'               :'false',
            # 'useFFmpegReconnect'          :'true',
            # 'useInputstreamAdaptiveforHls':'true'
            }

def togglePVR(state=True, reverse=False, waitTime=15):
    log('globals: togglePVR, state = %s, reverse = %s, waitTime = %s'%(state,reverse,waitTime))
    BUILTIN.executebuiltin('ActivateWindow(home)')
    isEnabled = BUILTIN.getInfoBool('AddonIsEnabled(%s)'%(PVR_CLIENT_ID),'System')
    if (state and isEnabled) or (not state and not isEnabled): return
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":%s}, "id": 1}'%(PVR_CLIENT_ID,str(state).lower()))
    xbmc.sleep(250)
    if reverse: timerit(togglePVR)(waitTime,[not bool(state)])
    else: waitTime = int(PROMPT_DELAY/1000)
    DIALOG.notificationWait('%s: %s'%(PVR_CLIENT_NAME,LANGUAGE(32125)),wait=waitTime)
              
def bruteForcePVR(msg=''):
    if (BUILTIN.getInfoBool('IsPlayingTv','Pvr') | BUILTIN.getInfoBool('IsPlayingRadio','Pvr')): msg = LANGUAGE(32128)
    if DIALOG.yesnoDialog('%s\n%s?\n%s'%(LANGUAGE(32129)%(PVR_CLIENT_NAME),(LANGUAGE(32121)%(PVR_CLIENT_NAME)),msg)):
        brutePVR(True)
              
def brutePVR(override=False, waitTime=15):
    if not override:
        if not DIALOG.yesnoDialog('%s?'%(LANGUAGE(32121)%(xbmcaddon.Addon(PVR_CLIENT_ID).getAddonInfo('name')))): return
    togglePVR(False,True,waitTime)
    if MONITOR.waitForAbort(waitTime): return False
    return True
     
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
    
def isPaused():
    return BUILTIN.getInfoBool('Player.Paused')
    
def isPendingRestart():
    state = PROPERTIES.getPropertyBool('pendingRestart')
    setPendingRestart(False)
    return state
    
def setPendingRestart(state=True):
    if state: DIALOG.notificationWait(LANGUAGE(32124))
    return PROPERTIES.setPropertyBool('pendingRestart',state)
                           
def hasAutotuned():
    return PROPERTIES.getPropertyBool('hasAutotuned')
    
def setAutotuned(state=True):
    if state == hasAutotuned(): return
    return PROPERTIES.setPropertyBool('hasAutotuned',state)
         
def hasFirstrun():
    return PROPERTIES.getPropertyBool('hasFirstrun')
    
def setFirstrun(state=True):
    if state == hasFirstrun(): return
    return PROPERTIES.setPropertyBool('hasFirstrun',state)

def isClient():
    client = PROPERTIES.getEXTProperty('%s.isClient'%(ADDON_ID)) == "true"
    return (client | bool(SETTINGS.getSettingInt('Client_Mode')))
   
def setClient(state=False,silent=True):
    PROPERTIES.setEXTProperty('%s.isClient'%(ADDON_ID),str(state).lower())
    if not silent and state: DIALOG.notificationWait(LANGUAGE(32115))
           
def getDiscovery():
    return loadJSON(PROPERTIES.getEXTProperty('%s.SERVER_DISCOVERY'%(ADDON_ID)))

def setDiscovery(servers={}):
    return PROPERTIES.setEXTProperty('%s.SERVER_DISCOVERY'%(ADDON_ID),dumpJSON(servers))

def chunkLst(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def chunkDict(items, n):
    it = iter(items)
    for i in range(0, len(items), n):
        yield {k:items[k] for k in islice(it, n)}

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
    return PROPERTIES.getEXTProperty('%s.isLowPower'%(ADDON_ID)) == 'true'

def getLowPower():
    if (BUILTIN.getInfoBool('Platform.Windows','System') | BUILTIN.getInfoBool('Platform.OSX','System') | SETTINGS.getSettingBool('Force_HighPower')):
        return False
    return True

def setLowPower(state=getLowPower()):
    PROPERTIES.setEXTProperty('%s.isLowPower'%(ADDON_ID),str(state).lower())
    return state

def forceUpdateTime(key):
    PROPERTIES.setPropertyInt(key,0)

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
              
def hasFile(file):
    if file.startswith(tuple(VFS_TYPES)):
        if file.startswith('plugin://'): return BUILTIN.getInfoBool('AddonIsEnabled(%s)'%(file),'System')
        else: return True
    else: return FileAccess.exists(file)

def timeString2Seconds(string): #hh:mm:ss
    try:    return int(sum(x*y for x, y in zip(list(map(float, string.split(':')[::-1])), (1, 60, 3600, 86400))))
    except: return 0
