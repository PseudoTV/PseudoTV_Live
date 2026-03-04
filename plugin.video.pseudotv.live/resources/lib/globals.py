#   Copyright (C) 2025 Lunatixz
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
from variables   import *
from kodi        import *
from pool        import debounceit, killit, timeit, poolit, executeit, timerit, threadit, ExecutorPool

DIALOG     = Dialog()
PROPERTIES = DIALOG.properties
SETTINGS   = DIALOG.settings
LISTITEMS  = DIALOG.listitems
BUILTIN    = DIALOG.builtin

def validString(s):
    return "".join(x for x in s if (x.isalnum() or x not in '\\/:*?"<>|'))
        
def stripNumber(s):
    return re.sub(r'\d+','',s)
    
def stripRegion(s):
    match = re.compile(r'(.*) \((.*)\)', re.IGNORECASE).search(s)
    try:    return match.group(1)
    except Exception: return s
    
def chanceBool(percent=25):
    return random.randrange(100) <= percent

def requestURL(url, params={}, payload={}, header=HEADER, timeout=FIFTEEN, cache=None, file=None):
    #cache = {"cache":None, "checksum":ADDON_VERSION, "life": datetime.timedelta(minutes=15)}
    def __error(result={}):                                                         return result
    def __getCache(key, cache, checksum):                return (cache.get('requestURL.%s'%(Globals._getMD5(key)), checksum) or __error())
    def __setCache(key, results, cache, checksum, life): return cache.set('requestURL.%s'%(Globals._getMD5(key)), results, checksum, life)
        
    results  = None
    session  = requests.Session()
    retries  = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter  = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    try:
        headers = HEADER.copy()
        headers.update(header)
        if payload: response = session.post(url, json=payload, files=file, headers=headers, timeout=timeout)
        else:       response = session.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()  # Raise an exception for HTTP errors
        try:    results = response.json()
        except Exception: results = response.content
        if isinstance(results,bytes): results = results.decode(DEFAULT_ENCODING)
        log("Globals: requestURL\nurl = %s, status = %s\nparams = %s\npayload = %s\nreturn type = %s"%(url,response.status_code,params,payload,type(results)))
        
        if results and not cache is None: 
            return __setCache('.'.join([url,FileAccess.dumpJSON(params),FileAccess.dumpJSON(payload),FileAccess.dumpJSON(header)]), 
                              results, cache["cache"], cache.get("checksum",ADDON_VERSION), cache.get("life",datetime.timedelta(minutes=15)))
        return results 
    except Exception as e: 
        log("Globals: requestURL, failed! %s, An error occurred: %s"%('Returning cache' if cache else 'No Response', e))
        return __getCache('.'.join([url,FileAccess.dumpJSON(params),FileAccess.dumpJSON(payload),FileAccess.dumpJSON(header)]), 
                          cache["cache"], cache.get("checksum",ADDON_VERSION)) if cache else __error()
    finally: #retry failed post
        if results is None and payload:
            posts = set(SETTINGS.getCacheSetting('postQue', revive=True) or [])
            posts.add((url, params, payload, header, timeout, None, file))
            SETTINGS.setCacheSetting('postQue', list(posts), checksum=ADDON_VERSION)

def getChannelID(name, path, number, uuid=None):
    if uuid is None: uuid = SETTINGS.getMYUUID()
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)),uuid)
    return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:32]).decode(DEFAULT_ENCODING),Globals._slugify(ADDON_NAME))
    
def getRecordID(name, path, number, uuid=None):
    if uuid is None: uuid = SETTINGS.getMYUUID()
    if isinstance(path, list): path = '|'.join(path)
    tmpid = '%s.%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)),uuid)
    return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:16]).decode(DEFAULT_ENCODING),Globals._slugify(ADDON_NAME))

def splitYear(label):
    try:
        match = re.compile(r'(.*) \((.*)\)', re.IGNORECASE).search(label)
        if match and match.group(2):
            label, year = match.groups()
            if year.isdigit():
                return label, int(year)
    except Exception: pass
    return label, None

def getChannelSuffix(name, type):
    name = validString(name)
    if   type == "TV Genres"    and not LANGUAGE(32014).lower() in name.lower(): suffix = LANGUAGE(32014) #TV
    elif type == "Movie Genres" and not LANGUAGE(32015).lower() in name.lower(): suffix = LANGUAGE(32015) #Movies
    elif type == "Mixed Genres" and not LANGUAGE(32010).lower() in name.lower(): suffix = LANGUAGE(32010) #Mixed
    elif type == "Music Genres" and not LANGUAGE(32016).lower() in name.lower(): suffix = LANGUAGE(32016) #Music
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
    if not file.startswith(tuple(VFS_TYPES + WEB_TYPES)): state = FileAccess.exists(file)
    elif   file.startswith('plugin://'):                  state = SETTINGS.hasAddon(file)
    else:                                                 state = True
    log("Globals: hasFile, file = %s (%s)"%(file,state))
    return state    

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
   
def strpTime(datestring, format=DTJSONFORMAT): #convert pvr infolabel datetime string to datetime obj, thread safe!
    try:              return datetime.datetime.strptime(datestring, format)
    except TypeError: return datetime.datetime.fromtimestamp(ime.mktime(time.strptime(datestring, format)))
    except Exception:           return ''
   
def epochTime(timestamp, tz=True): #convert pvr json datetime string to datetime obj
    if tz: timestamp -= getTimeoffset()
    return datetime.datetime.fromtimestamp(timestamp)

def getTimeoffset():
    return (int((datetime.datetime.now() - datetime.datetime.utcnow()).days * 86400 + round((datetime.datetime.now() - datetime.datetime.utcnow()).seconds, -1)))
    
def getUTCstamp():
    return time.time() - getTimeoffset()

def getGMTstamp():
    return time.time()

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

def isRadio(item):
    if item.get('radio',False) or item.get('type') == "Music Genres": return True
    for path in item.get('path',[item.get('file','')]):
        if path.lower().startswith(('musicdb://','special://profile/playlists/music/','special://musicplaylists/')): return True
    return False

def cleanLabel(text):
    text = re.sub(r'\[COLOR=(.+?)\]', '', text)
    text = re.sub(r'\[/COLOR\]', '', text)
    text = text.replace("[B]",'').replace("[/B]",'')
    text = text.replace("[I]",'').replace("[/I]",'')
    return text.replace(":",'')
  
def cleanImage(image=''):
    if image is None: image = ''
    else:
        if not image.startswith(('image://','resource://','special://','smb://','nfs://','https://','http://')):
            realPath = FileAccess.translatePath('special://home/addons/')
            if image.startswith(realPath):# convert real path. to vfs
                image = image.replace(realPath,'special://home/addons/').replace('\\','/')
            elif image.startswith(realPath.replace('\\','/')):
                image = image.replace(realPath.replace('\\','/'),'special://home/addons/').replace('\\','/')
    return image.strip('/')

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
    except Exception: 
        mpaa = mpaa.strip()
    return mpaa

def combineDicts(dict1={}, dict2={}):
    if dict1 and dict2:
        for k,v in list(dict1.items()):
            if dict2.get(k): k = dict2.pop(k)
        dict1.update(dict2)
    return dict1
    
def _setDictLST(lst=[]):
    items = {}
    for key, dictlst in list(lst.items()):
        if isinstance(dictlst, list): dictlst = Globals._setDictLST(dictlst)
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
    except Exception: return -1

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
       
def interleave(seqs, sets=1, repeats=False): 
    #evenly interleave multi-lists of different sizes, while preserving seq order and by sets of x
    # In         [[1,2,3,4],['a','b','c'],['A','B','C','D','E']]
    # repeats = False
    # Out sets=0 [1, 2, 3, 4, 'a', 'b', 'c', 'A', 'B', 'C', 'D', 'E']
    # Out sets=1 [1, 'a', 'A', 2, 'b', 'B', 3, 'c', 'C', 4, 'D', 'E']
    # Out sets=2 [1, 2, 'a', 'b', 'A', 'B', 3, 4, 'c', 'C', 'D', 'E']
    # repeats = True
    # Out sets=0 [1, 2, 3, 4, 'a', 'b', 'c', 'A', 'B', 'C', 'D', 'E']
    # Out sets=1 [1, 'a', 'A', 2, 'b', 'B', 3, 'c', 'C', 4, 'a', 'D', 1, 'b', 'E']
    # Out sets=2 [1, 2, 'a', 'b', 'A', 'B', 3, 4, 'c', 'a', 'C', 'D', 1, 2, 'b', 'c', 'E', 'A']
    if sets > 0:
        # if repeats:
            # # Create cyclical iterators for each list
            # cyclical_iterators = [cycle(lst) for lst in seqs]
            # interleaved = []
            # # Determine the length of the longest list
            # max_len = max((len(lst) for lst in seqs))
            # # Calculate the number of blocks needed
            # num_blocks = (max_len + sets - 1) // sets
            # # Interleave in blocks
            # for i in range(num_blocks):
                # for iterator in cyclical_iterators:
                    # # Use islice to take a block of elements from the current iterator
                    # block = list(islice(iterator, sets))
                    # interleaved.extend(block)
            # return interleaved
        # else:
        seqs = [list(zip_longest(*[iter(seqs)] * sets, fillvalue=None)) for seqs in seqs]
        return list([_f for _f in sum([_f for _f in chain.from_iterable(zip_longest(*seqs)) if _f], ()) if _f])
    else: return list(chain.from_iterable(seqs))
        
def percentDiff(org, new):
    try: return (abs(round(org) - round(new)) / round(new)) * 100.0
    except ZeroDivisionError: return -1
        
def pagination(list, end):
    for start in range(0, len(list), end):
        yield seq[start:start+end]

def isCenterlized():
    default = 'special://profile/addon_data/plugin.video.pseudotv.live/cache'
    if REAL_SETTINGS.getSetting('User_Folder') == default:
        return False
    return True
                
def isFiller(item={}):
    return any(genre.lower() in map(str.lower, PRE_POST_ROLL_TYPES) for genre in item.get('genre', []))

def isShort(item={}, minDuration=SETTINGS.getSettingInt('Seek_Tolerance')):
    if item.get('duration', minDuration) < minDuration: return True
    else: return False
   
def isEnding(progress=100):
    if progress >= SETTINGS.getSettingInt('Seek_Threshold'): return True
    else: return False

def chkLogo(old, new=LOGO):
    if new.endswith('wlogo.png') and not old.endswith('wlogo.png'): return old
    return new
    
def parseSE(filename):
    pattern = re.compile(
        r'(?:s|season)\s*(\d+)\s*(?:e|x|episode)\s*(\d+)|'  # s01e01, 1x01, Season 1 Episode 1
        r'(\d{1,2})[xX](\d{1,2})|'                          # 1x01 format
        r'(\d)(\d{2})(?!\d)'                                # 101 format (single digit season, two digit episode)
    , re.IGNORECASE)

    match = pattern.search(filename)
    if match:
        if match.group(1) is not None:
            return int(match.group(1)), int(match.group(2))
        elif match.group(3) is not None:
            return int(match.group(3)), int(match.group(4))
        elif match.group(5) is not None:
            return int(match.group(5)), int(match.group(6))
    return -1, -1

def hasURLencoding(s):
    return bool(re.search(r'%[0-9a-fA-F]{2}', s))