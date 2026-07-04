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
from constants   import *
from fileaccess  import FileAccess, FileLock
from kodi        import Kodi, Settings, Properties, ListItems, Builtin, Dialog
from pool        import debounceit, timeit, poolit, executeit, timerit, threadit, ExecutorPool

MIN_GUIDEDAYS   = int((REAL_SETTINGS.getSetting('Min_Days')    or "1"))
MAX_GUIDEDAYS   = int((REAL_SETTINGS.getSetting('Max_Days')    or "3"))
OSD_TIMER       = int((REAL_SETTINGS.getSetting('OSD_Timer')   or "5"))

CACHE_LOC       = os.path.join(REAL_SETTINGS.getSetting('User_Folder'))
LOGO_LOC        = os.path.join(CACHE_LOC,'logos')
FILLER_LOC      = os.path.join(CACHE_LOC,'fillers')
M3UFLEPATH      = os.path.join(CACHE_LOC,M3UFLE)
XMLTVFLEPATH    = os.path.join(CACHE_LOC,XMLTVFLE)
GENREFLEPATH    = os.path.join(CACHE_LOC,GENREFLE)
PROVIDERFLEPATH = os.path.join(CACHE_LOC,PROVIDERFLE)

class Globals:
    kodi       = Kodi()
    dialog     = KODI.dialog
    properties = KODI.properties
    settings   = KODI.settings
    listitems  = KODI.listitems
    builtin    = KODI.builtin

    @staticmethod
    def _log(event, level=xbmc.LOGDEBUG):
        if REAL_SETTINGS.getSetting('Debug_Enable') == 'true' or level >= 3:
            DEBUG_NAMES  = {0: 'LOGDEBUG', 1: 'LOGINFO', 2: 'LOGWARNING', 3: 'LOGERROR', 4: 'LOGFATAL'}
            DEBUG_LEVELS = {0: xbmc.LOGDEBUG, 1: xbmc.LOGINFO, 2: xbmc.LOGWARNING, 3: xbmc.LOGERROR, 4: xbmc.LOGFATAL}
            DEBUG_LEVEL  = DEBUG_LEVELS[int((REAL_SETTINGS.getSetting('Debug_Level') or "3"))]
            if level >= 3: event = '%s\n%s' % (event, traceback.format_exc())
            event = '%s-%s-%s' % (ADDON_ID, ADDON_VERSION, event)
            if level >= DEBUG_LEVEL:
                xbmc.log(event, level)
                
    @staticmethod
    def _encodePlot(plot, text):
        return '%s [COLOR item="%s"][/COLOR]'%(plot,FileAccess._encodeString(text))
        
    @staticmethod
    def _decodePlot(text: str = '') -> dict:
        if isinstance(text, str):
            plot = re.search(r'\[COLOR item=\"(.+?)\"]\[/COLOR]', text)
            if plot: return FileAccess._decodeString(plot.group(1))
        return {}
        
    @staticmethod
    def _escapeString(text, table=HTML_ESCAPE):
        return escape(text,table)
    
    @staticmethod
    def _unescapeString(text, table=HTML_ESCAPE):
        return unescape(text,{v:k for k, v in list(table.items())})

    @staticmethod
    def _quoteString(text):
        return urllib.parse.quote(text)

    @staticmethod
    def _unquoteString(text):
        return urllib.parse.unquote(text)
    
    @staticmethod
    def _getAbbr(text):
        words = text.split(' ')
        if len(words) > 1: return '%s.%s.'%(words[0][0].upper(),words[1][0].upper())
        else:              return words[0][0].upper()
	   
    @staticmethod
    def _slugify(s, lowercase=False):
        if lowercase: s = s.lower()
        s = s.strip()
        s = re.sub(r'[^\w\s-]', '', s)
        s = re.sub(r'[\s_-]+', '_', s)
        s = re.sub(r'^-+|-+$', '', s)
        return s
            
    @staticmethod
    def _notificationDialog(msg, header=ADDON_NAME, time=PROMPT_DELAY, logo=LOGO_COLOR):
        xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, msg, time*1000, logo))
        
    @staticmethod
    def _getInfoBool(key, param='Library'):
        return (xbmc.getCondVisibility('%s.%s'%(param,key)) or False)
        
    @staticmethod
    def _getInfoLabel(key, default=''):
        return (xbmc.getInfoLabel(key) or default)
        
    @staticmethod
    def _openSettings(ctl=(0,1), id=ADDON_ID):
        xbmc.executebuiltin(f'Addon.OpenSettings({id})')
        xbmc.sleep(100)
        xbmc.executebuiltin('SetFocus(%i)'%(ctl[0]-200))
        xbmc.sleep(50)
        xbmc.executebuiltin('SetFocus(%i)'%(ctl[1]-180))
        return True

    @staticmethod
    def _openGuide(instanceName=ADDON_NAME):
        def __match(match):
            for name in FileAccess.listdir('pvr://channels/tv/')[0]:
                if name.lower().startswith(self._quoteString(match.lower())):
                    return match, 'pvr://channels/tv/%s'%(name)
            return match, __match('All channels')
        if self._getInfoBool('HasTVChannels','Pvr'):
            try:
                instanceName, path = __match(instanceName)
                xbmc.executebuiltin("ReplaceWindow(TVGuide,%s)"%(path))
            except Exception: xbmc.executebuiltin("ReplaceWindow(TVGuide)")
        else: self._openSettings()
          
    @staticmethod  
    def _getThumb(item={}, opt=0): #unify thumbnail artwork
        art  = None
        keys = {0:['landscape','fanart','thumb','thumbnail','poster','clearlogo','logo','logos','clearart','keyart,icon'],
                1:['poster','clearlogo','logo','logos','clearart','keyart','landscape','fanart','thumb','thumbnail','icon']}[opt]
        for key in keys:
            art = (item.get('art',{}).get('album.%s'%(key))       or 
                   item.get('art',{}).get('albumartist.%s'%(key)) or 
                   item.get('art',{}).get('artist.%s'%(key))      or 
                   item.get('art',{}).get('season.%s'%(key))      or 
                   item.get('art',{}).get('tvshow.%s'%(key))      or 
                   item.get('art',{}).get(key)                    or
                   item.get(key))
            if art: return art
        return {0:LOGO_LANDSCAPE,1:LOGO_POSTER}[opt]

    @staticmethod
    def _getDummyIcon(text, background=COLOR_BACKGROUND, color=COLOR_TEXT):
        if not isinstance(text, (str,bytes)): text = str(text)
        url  = f'https://dummyimage.com/512x512/{background}/{color}.png&text={self._quoteString(text)}'
        file = os.path.join(TEMP_LOC,f'{FileAccess._getMD5(url)}.png')
        if   FileAccess.exists(file):      return file
        elif FileAccess.setURL(url, file): return file
        return ICON
          
    @staticmethod
    def _cleanImage(image=''):
        if image is None: image = ''
        if not image.startswith(('image://','resource://','special://','smb://','nfs://','https://','http://')):
            realPath = FileAccess.translatePath('special://home/addons/')
            if image.startswith(realPath):# convert real path. to vfs
                image = image.replace(realPath,'special://home/addons/').replace('\\','/')
            elif image.startswith(realPath.replace('\\','/')):
                image = image.replace(realPath.replace('\\','/'),'special://home/addons/').replace('\\','/')
        return image.strip('/')

    @staticmethod  
    def _findItemsInLST(items, values, item_key='getLabel', val_key='', index=True):
        if not values: return [-1]
        if not isinstance(values,list): values = [values]
        matches = []
        def _match(fkey,fvalue):
            if str(fkey).lower() == str(fvalue).lower():
                matches.append(idx if index else item)
                        
        for value in values:
            if isinstance(value,dict): 
                value = value.get(val_key,'')
                
            for idx, item in enumerate(items): 
                if isinstance(item,xbmcgui.ListItem): 
                    if item_key == 'getLabel':  
                        _match(item.self._getLabel() ,value)
                    elif item_key == 'getLabel2': 
                        _match(item.getLabel2(),value)
                    elif item_key == 'getPath': 
                        _match(item.getPath(),value)
                elif isinstance(item,dict):       
                    _match(item.get(item_key,''),value)
                else: _match(item,value)
        return matches
        
    @staticmethod  
    def _setDictLST(lst=[]): #set lst of dicts then return
        return [FileAccess.loadJSON(s) for s in list(OrderedDict.fromkeys([FileAccess.dumpJSON(d) for d in lst]))]
    
    @staticmethod  
    def _mergeDict(dict1={},dict2={},key='label'):
        # dict = [{ "key": ""}, {"key": ""}]
        return list({d[key]: d for d in dict1 + dict2}.values())
        
    @staticmethod  
    def _mergeDictLST(dict1={},dict2={}):
        # dict = { "key": [], "key": []}
        for k, v in list(dict2.items()):
            dict1.setdefault(k,[]).extend(v)
            self.self._setDictLST(dict1)
        return dict1
        
    @staticmethod  
    def _lstSetDictLst(lst=[]):
        items = dict()
        for key, dictlst in list(lst.items()):
            if isinstance(dictlst, list): dictlst = self.self._setDictLST(dictlst)
            items[key] = dictlst
        return items
        
    @staticmethod  
    def diffLSTDICT(old, new):
        set1 = {FileAccess.dumpJSON(d, sortkey=True) for d in old}
        set2 = {FileAccess.dumpJSON(d, sortkey=True) for d in new}
        return {"added": [FileAccess.loadJSON(s) for s in set2 - set1], "removed": [FileAccess.loadJSON(s) for s in set1 - set2]}
            
    @staticmethod  
    def _cleanGroups(citem={}):
        if REAL_SETTINGS.getSetting('Enable_Grouping') == "true":
            #Default
            if ADDON_NAME not in citem.get('group'): citem.setdefault('group',[]).append(ADDON_NAME)
            #Favorites
            if citem.get('favorite',False) and not LANGUAGE(32019) in citem['group']:   citem['group'].append(LANGUAGE(32019))
            elif not citem.get('favorite',False) and LANGUAGE(32019) in citem['group']: citem['group'].remove(LANGUAGE(32019))
            #Type
            if citem.get('type') not in citem.get('group'): citem['group'].append(citem.get('type'))
            #Genre
            if citem.get('type') in [LANGUAGE(32006),LANGUAGE(32007),LANGUAGE(32009)]:#"TV Genres","Movie Genres","Mixed Genres"
                citem['group'].append(citem.get('type').replace(f' {LANGUAGE(32014)}','').replace(f' {LANGUAGE(32015)}','').replace(f' {LANGUAGE(32010)}',''))
        else: citem['group'] = [ADDON_NAME]
        citem['group'] = sorted(set(citem['group']))
        return citem
             
    @staticmethod
    def _randomShuffle(items):
        if isinstance(items, dict):
            return {key: self._randomShuffle(items[key]) for key in self._randomShuffle(list(items.keys()))}
        elif isinstance(items, (list, tuple)):
            if not items: return [] if isinstance(items, list) else ()
            shuffled_list = random.sample(items, len(items))
            result = [self._randomShuffle(item) for item in shuffled_list]
            return tuple(result) if isinstance(items, tuple) else result
        return items

    @staticmethod
    def _randomSamples(items: Sequence[Any] = None, x: int = -1) -> list:
        if items is None: return []
        try: items_list = list(items)
        except TypeError: return items
        return random.sample(items_list, len(items_list) if x < 0 or x > len(items_list) else x)
        
    @staticmethod
    def double_urlencode(text):
        text = self.single_urlencode(text)
        text = self.single_urlencode(text)
        return text

    @staticmethod  
    def single_urlencode(text):
        text = urllib.parse.urlencode({'blahblahblah':text})
        text = text[13:]
        return text
        
    @staticmethod
    def _getCountry(type=xbmc.ISO_639_1):
        try: return xbmc.getLanguage(type, region=True).split('-')[1].upper() # Results in "US", "GB", etc.
        except Exception: return "GB"
            
    @staticmethod
    def _getLanguage(type=xbmc.ISO_639_1):
        local = xbmc.getLanguage(type, region=True).replace('_', '-')
        parts = local.split('-')
        if len(parts) == 2:
            return f"{parts[0].lower()}-{parts[1].upper()}"
        return local.lower()
            
    @staticmethod
    def _cleanMPAA(mpaa):
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
        
    @staticmethod
    def _percentDiff(org, new):
        try: return (abs(round(org) - round(new)) / round(new)) * 100.0
        except ZeroDivisionError: return -1
            
    @staticmethod
    def _isStack(path): #is path a stack
        return path.startswith('stack://')

    @staticmethod
    def _splitStacks(path): #split stack path for indv. files.
        if not self._isStack(path): return [path]
        return [_f for _f in ((path.split('stack://')[1]).split(' , ')) if _f]

    @staticmethod
    def _isFiller(item={}):
        lowers = map(str.lower, ROLL_TYPES)
        genres = item.get('genre',[])
        if not isinstance(genres,list) and ' / ' in genres: genres = genres.split(' / ')
        return any(genre.lower() in lowers for genre in genres)

    @staticmethod
    def _validString(s):
        return "".join(x for x in s if (x.isalnum() or x not in '\\/:*?"<>|'))
        
    @staticmethod
    def _stripNumber(s):
        return re.sub(r'\d+','',s)
    
    @staticmethod
    def _stripRegion(s):
        match = re.compile(r'(.*) \((.*)\)', re.IGNORECASE).search(s)
        try:    return match.group(1)
        except Exception: return s

    @staticmethod
    def _splitYear(label):
        try:
            match = re.compile(r'(.*) \((.*)\)', re.IGNORECASE).search(label)
            if match and match.group(2):
                label, year = match.groups()
                if year.isdigit():
                    return label, int(year)
        except Exception: pass
        return label, None

    @staticmethod
    def _chanceBool(percent=25):
        return random.randrange(100) < percent

    @staticmethod
    def _getChannelID(name, path, number, uuid=None):
        if uuid is None: uuid = self.SETTINGS.getMYUUID()
        if isinstance(path, list): path = '|'.join(path)
        tmpid = '%s.%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)),uuid)
        return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:32]).decode(DEFAULT_ENCODING),self._slugify(ADDON_NAME))
    
    @staticmethod
    def _getRecordID(name, path, number, uuid=None):
        if uuid is None: uuid = self.SETTINGS.getMYUUID()
        if isinstance(path, list): path = '|'.join(path)
        tmpid = '%s.%s.%s.%s'%(number, name, hashlib.md5(path.encode(DEFAULT_ENCODING)),uuid)
        return '%s@%s'%((binascii.hexlify(tmpid.encode(DEFAULT_ENCODING))[:16]).decode(DEFAULT_ENCODING),self._slugify(ADDON_NAME))

    @staticmethod
    def _getChannelSuffix(name, type):
        name = self._validString(name)
        if   type == "TV Genres"    and not LANGUAGE(32014).lower() in name.lower(): suffix = LANGUAGE(32014) #TV
        elif type == "Movie Genres" and not LANGUAGE(32015).lower() in name.lower(): suffix = LANGUAGE(32015) #Movies
        elif type == "Mixed Genres" and not LANGUAGE(32010).lower() in name.lower(): suffix = LANGUAGE(32010) #Mixed
        elif type == "Music Genres" and not LANGUAGE(32016).lower() in name.lower(): suffix = LANGUAGE(32016) #Music
        else: return name
        return '%s %s'%(name,suffix)
     
    @staticmethod
    def _cleanChannelSuffix(name, type):
        if   type == "TV Genres"    : name = name.split(' %s'%LANGUAGE(32014))[0]#TV
        elif type == "Movie Genres" : name = name.split(' %s'%LANGUAGE(32015))[0]#Movies
        elif type == "Mixed Genres" : name = name.split(' %s'%LANGUAGE(32010))[0]#Mixed
        elif type == "Music Genres" : name = name.split(' %s'%LANGUAGE(32016))[0]#Music
        return name
                
    @staticmethod
    def _getLabel(item, addYear=False):
        label = (item.get('name') or item.get('label') or item.get('showtitle') or item.get('title'))
        if not label: return ''
        label, year = self._splitYear(label)
        year = (item.get('year') or year)
        if year and addYear: return '%s (%s)'%(label, year)
        return label
       
    @staticmethod
    def _hasFile(file):
        if not file.startswith(tuple(VFS_TYPES + WEB_TYPES)): state = FileAccess.exists(file)
        elif   file.startswith('plugin://'):                  state = self.SETTINGS.hasAddon(file)
        else:                                                 state = True
        log("Globals: hasFile, file = %s (%s)"%(file,state))
        return state    

    @staticmethod
    def _roundTimeDown(dt=None, offset=30): # round the given time down to the nearest
        if dt is None: dt = time.time()
        offset_seconds = offset * 60
        return (dt // offset_seconds) * offset_seconds
        
    @staticmethod
    def _roundTimeUp(dt=None, roundTo=60):
        if dt is None: dt = time.time()
        round_seconds = roundTo * 60
        return ((dt + round_seconds - 1) // round_seconds) * round_seconds
       
    @staticmethod
    def _strpTime(datestring, format=DTJSONFORMAT): #convert pvr infolabel datetime string to datetime obj, thread safe!
        try:              return datetime.datetime.strptime(datestring, format)
        except TypeError: return datetime.datetime.fromtimestamp(ime.mktime(time.strptime(datestring, format)))
        except Exception:           return ''
       
    @staticmethod
    def _epochTime(timestamp, tz=True): #convert pvr json datetime string to datetime obj
        if tz: timestamp -= self._getTimeoffset()
        return datetime.datetime.fromtimestamp(timestamp)

    @staticmethod
    def _getTimeoffset():
        return (int((datetime.datetime.now() - datetime.datetime.utcnow()).days * 86400 + round((datetime.datetime.now() - datetime.datetime.utcnow()).seconds, -1)))
        
    @staticmethod
    def _getUTCstamp():
        return time.time() - self._getTimeoffset()

    @staticmethod
    def _getGMTstamp():
        return time.time()

    @staticmethod
    def _escapeDirJSON(path):
        mydir = path
        if (mydir.find(":")): mydir = mydir.replace("\\", "\\\\")
        return mydir

    @staticmethod
    def _KODI_LIVETV_SETTINGS(): #recommended Kodi LiveTV settings
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

    @staticmethod
    def _isRadio(item):
        if item.get('radio',False) or item.get('type') == "Music Genres": return True
        for path in item.get('path',[item.get('file','')]):
            if path.lower().startswith(('musicdb://','special://profile/playlists/music/','special://musicplaylists/')): return True
        return False

    @staticmethod
    def _cleanLabel(text):
        text = re.sub(r'\[COLOR=(.+?)\]', '', text)
        text = re.sub(r'\[/COLOR\]', '', text)
        text = text.replace("[B]",'').replace("[/B]",'')
        text = text.replace("[I]",'').replace("[/I]",'')
        return text.replace(":",'')

    @staticmethod
    def _combineDicts(dict1={}, dict2={}):
        return {**dict1, **dict2}
        
    @staticmethod
    def _setDictLST(lst=[]):
        items = {}
        for key, dictlst in list(lst.items()):
            if isinstance(dictlst, list): dictlst = self.self._setDictLST(dictlst)
            items[key] = dictlst
        return items
        
    @staticmethod
    def _compareDict(dict1,dict2,sortKey):
        a = sorted(dict1, key=itemgetter(sortKey))
        b = sorted(dict2, key=itemgetter(sortKey))
        return a == b
        
    @staticmethod
    def _subZoom(number,percentage,multi=100):
        return round(number * (percentage*multi) / 100)
        
    @staticmethod
    def _addZoom(number,percentage,multi=100):
        return round((number - (number * (percentage*multi) / 100)) + number)
       
    @staticmethod
    def _frange(start,stop,inc):
        return [x/10.0 for x in range(start,stop,inc)]
        
    @staticmethod
    def _timeString2Seconds(string): #hh:mm:ss
        try:    return int(sum(x*y for x, y in zip(list(map(float, string.split(':')[::-1])), (1, 60, 3600, 86400))))
        except Exception: return -1

    @staticmethod
    def _chunkLst(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    @staticmethod
    def _chunkDict(items, n):
        it = iter(items)
        for i in range(0, len(items), n):
            yield {k:items[k] for k in islice(it, n)}
        
    @staticmethod
    def _roundupDIV(p, q):
        try:
            d, r = divmod(p, q)
            if r: d += 1
            return d
        except ZeroDivisionError: 
            return 1
       
    @staticmethod
    def _interleave(seqs, sets=1, repeats=False): 
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

    @staticmethod
    def _pagination(list, end):
        for start in range(0, len(list), end):
            yield seq[start:start+end]

    @staticmethod
    def _isCenterlized():
        default = f'special://profile/addon_data/{ADDON_ID}/cache'
        if REAL_SETTINGS.getSetting('User_Folder') == default: return True
        return False
    
    @staticmethod
    def _isShort(item={}, minDuration=None):
        if minDuration is None: minDuration = self.SETTINGS.getSettingInt('Seek_Tolerance')
        if item.get('duration', minDuration) < minDuration: return True
        else: return False
   
    @staticmethod
    def _isEnding(progress=100):
        if progress >= self.SETTINGS.getSettingInt('Seek_Threshold'): return True
        else: return False

    @staticmethod
    def _chkLogo(old, new=LOGO):
        if new.endswith('wlogo.png') and not old.endswith('wlogo.png'): return old
        return new
        
    @staticmethod
    def _parseSE(filename):
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

    @staticmethod
    def _hasURLencoding(s):
        return bool(re.search(r'%[0-9a-fA-F]{2}', s))
    
    @staticmethod
    def __escape_html(s): 
        return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")