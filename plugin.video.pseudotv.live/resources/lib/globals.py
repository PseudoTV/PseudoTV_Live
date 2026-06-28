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
from variables   import *
from pool        import debounceit, timeit, poolit, executeit, timerit, threadit, ExecutorPool

def validString(s):
    return "".join(x for x in s if (x.isalnum() or x not in '\\/:*?"<>|'))
        
def stripNumber(s):
    return re.sub(r'\d+','',s)
    
def stripRegion(s):
    match = re.compile(r'(.*) \((.*)\)', re.IGNORECASE).search(s)
    try:    return match.group(1)
    except Exception: return s
    
def chanceBool(percent=25):
    return random.randrange(100) < percent

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

def roundTimeDown(dt=None, offset=30): # round the given time down to the nearest
    if dt is None: dt = time.time()
    offset_seconds = offset * 60
    return (dt // offset_seconds) * offset_seconds
    
def roundTimeUp(dt=None, roundTo=60):
    if dt is None: dt = time.time()
    round_seconds = roundTo * 60
    return ((dt + round_seconds - 1) // round_seconds) * round_seconds
   
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
    return {**dict1, **dict2}
    
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
    default = f'special://profile/addon_data/{ADDON_ID}/cache'
    if REAL_SETTINGS.getSetting('User_Folder') == default: return True
    return False
    
def isFiller(item={}):
    lowers = map(str.lower, ROLL_TYPES)
    genres = item.get('genre',[])
    if not isinstance(genres,list) and ' / ' in genres: genres = genres.split(' / ')
    return any(genre.lower() in lowers for genre in genres)

def isShort(item={}, minDuration=None):
    if minDuration is None: minDuration = SETTINGS.getSettingInt('Seek_Tolerance')
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
        r'(?:s|season)\s*(?P<s>\d+)\s*(?:e|x|episode)\s*(?P<e>\d+)|' # S01E01
        r'(?P<s2>\d{1,2})[xX](?P<e2>\d{1,2})|'                       # 1x01
        r'(?<!\d)(?P<s3>\d)(?P<e3>\d{2})(?!\d)',                     # 101 (excludes 4-digit years)
        re.IGNORECASE)
    match = pattern.search(filename)
    if match:
        res = {k: v for k, v in match.groupdict().items() if v is not None}
        if 's'  in res: return int(res['s']), int(res['e'])
        if 's2' in res: return int(res['s2']), int(res['e2'])
        if 's3' in res: return int(res['s3']), int(res['e3'])
    return -1, -1

def hasURLencoding(s):
    return bool(re.search(r'%[0-9a-fA-F]{2}', s))
    
def _escape_html(s): 
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")