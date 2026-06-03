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
from logger      import log
from fileaccess  import FileAccess, FileLock

#variables
PAGE_LIMIT          = int((REAL_SETTINGS.getSetting('Page_Limit')  or "25"))
MIN_GUIDEDAYS       = int((REAL_SETTINGS.getSetting('Min_Days')    or "1"))
MAX_GUIDEDAYS       = int((REAL_SETTINGS.getSetting('Max_Days')    or "3"))
OSD_TIMER           = int((REAL_SETTINGS.getSetting('OSD_Timer')   or "5"))
EPG_ARTWORK         = int((REAL_SETTINGS.getSetting('EPG_Artwork') or "0"))
RUNTIME_THRESHOLD   = 15 #todo user setting % of allowed difference between runtime and duration before overriding runtime.
#file paths
CACHE_LOC           = os.path.join(REAL_SETTINGS.getSetting('User_Folder'))
LOGO_LOC            = os.path.join(CACHE_LOC,'logos')
FILLER_LOC          = os.path.join(CACHE_LOC,'fillers')
M3UFLEPATH          = os.path.join(CACHE_LOC,M3UFLE)
XMLTVFLEPATH        = os.path.join(CACHE_LOC,XMLTVFLE)
GENREFLEPATH        = os.path.join(CACHE_LOC,GENREFLE)
PROVIDERFLEPATH     = os.path.join(CACHE_LOC,PROVIDERFLE)


class Globals:
    @staticmethod
    def _getEXTProperty(key, default=''):
        try:
            value = (xbmcgui.Window(10000).getProperty(key) or default)
            try: value = literal_eval(value)
            except (ValueError, SyntaxError): pass
            if not '.TRASH' in key: log(f'Globals: [10000] _getEXTProperty, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
            return value 
        except Exception as e: 
            log(f'Globals: [10000] _getEXTProperty, failed! key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}\n{e}')
            return default

    @staticmethod
    def _setEXTProperty(key, value):
        if not value is None: 
            xbmcgui.Window(10000).setProperty(key, value)
            if not '.TRASH' in key: log(f'Globals: [10000] _setEXTProperty, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return value

    @staticmethod
    def _clrEXTProperty(key):
        log(f'Globals: [10000] _clrEXTProperty, key = {key}')
        return xbmcgui.Window(10000).clearProperty(key)

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
                if name.lower().startswith(Globals._quoteString(match.lower())):
                    return match, 'pvr://channels/tv/%s'%(name)
            return match, __match('All channels')
        if Globals._getInfoBool('HasTVChannels','Pvr'):
            try:
                instanceName, path = __match(instanceName)
                xbmc.executebuiltin("ReplaceWindow(TVGuide,%s)"%(path))
            except Exception: xbmc.executebuiltin("ReplaceWindow(TVGuide)")
        else: Globals._openSettings()
          
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
        url  = f'https://dummyimage.com/512x512/{background}/{color}.png&text={Globals._quoteString(text)}'
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
                        _match(item.getLabel() ,value)
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
            Globals._setDictLST(dict1)
        return dict1
        
    @staticmethod  
    def _lstSetDictLst(lst=[]):
        items = dict()
        for key, dictlst in list(lst.items()):
            if isinstance(dictlst, list): dictlst = Globals._setDictLST(dictlst)
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
        if isinstance(items,dict):
            keys = Globals._randomShuffle(list(items.keys()))
            return {key: Globals._randomShuffle(items[key]) for key in keys}
        elif isinstance(items,list):
            if items:
                tmpItems = items[:]
                random.shuffle(tmpItems)
                return [Globals._randomShuffle(item) for item in tmpItems]
        return items

    @staticmethod  
    def _randomSamples(items=[], x=-1):
        if isinstance(items, list):
            if items and len(items) >= x: return random.sample(items, x)
            else:                         return random.sample(items, len(items))
        return items
        
    @staticmethod
    def double_urlencode(text):
        text = Globals.single_urlencode(text)
        text = Globals.single_urlencode(text)
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