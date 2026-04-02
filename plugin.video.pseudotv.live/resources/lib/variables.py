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
from constants   import *
from logger      import log
from fileaccess  import FileAccess, FileLock

#variables
PAGE_LIMIT          = int((REAL_SETTINGS.getSetting('Page_Limit')  or "25"))
MIN_GUIDEDAYS       = int((REAL_SETTINGS.getSetting('Min_Days')    or "1"))
MAX_GUIDEDAYS       = int((REAL_SETTINGS.getSetting('Max_Days')    or "3"))
OSD_TIMER           = int((REAL_SETTINGS.getSetting('OSD_Timer')   or "5"))
EPG_ARTWORK         = int((REAL_SETTINGS.getSetting('EPG_Artwork') or "0"))

#file paths
USER_LOC            = REAL_SETTINGS.getSetting('User_Folder')
LOGO_LOC            = os.path.join(USER_LOC,'logos')
FILLER_LOC          = os.path.join(USER_LOC,'fillers')
M3UFLEPATH          = os.path.join(USER_LOC,M3UFLE)
XMLTVFLEPATH        = os.path.join(USER_LOC,XMLTVFLE)
GENREFLEPATH        = os.path.join(USER_LOC,GENREFLE)
PROVIDERFLEPATH     = os.path.join(USER_LOC,PROVIDERFLE)
CHANNELFLEPATH      = os.path.join(USER_LOC,CHANNELFLE)
LIBRARYFLEPATH      = os.path.join(USER_LOC,LIBRARYFLE) 
SERVERFLEPATH       = os.path.join(USER_LOC,SERVERFLE)
AUTOTUNEFLEPATH     = os.path.join(USER_LOC,AUTOTUNEFLE)

class Globals:
    @staticmethod
    def _getProperty(key, default=''):
        value = (xbmcgui.Window(10000).getProperty('%s.%s'%(ADDON_ID, key)) or default)
        log(f'Globals: [10000] _getProperty, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return value 

    @staticmethod
    def _setProperty(key, value):
        xbmcgui.Window(10000).setProperty('%s.%s'%(ADDON_ID, key), value)
        log(f'Globals: [10000] _setProperty, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return value

    @staticmethod
    def _clrProperty(key):
        return xbmcgui.Window(10000).clearProperty('%s.%s'%(ADDON_ID, key))

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
    def _getInfoLabel(key, param='ListItem', default=''):
        return (xbmc.getInfoLabel('%s.%s'%(param,key)) or "")
        
    @staticmethod
    def _openSettings(ctl=(0,1), id=ADDON_ID):
        xbmc.executebuiltin(f'Addon.OpenSettings({id})')
        xbmc.sleep(100)
        xbmc.executebuiltin('SetFocus(%i)'%(ctl[0]-200))
        xbmc.sleep(50)
        xbmc.executebuiltin('SetFocus(%i)'%(ctl[1]-180))
        return True

    @staticmethod
    def _openGuide(instance=ADDON_NAME):
        def __match(match):
            for name in FileAccess.listdir('pvr://channels/tv/')[0]:
                if name.lower().startswith(Globals._quoteString(match.lower())):
                    return match, 'pvr://channels/tv/%s'%(name)
            return match, __match('All channels')
        if Globals._getInfoBool('HasTVChannels','Pvr'):
            try:
                instance, path = __match(instance)
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
        return Globals._buildWebImage(art, {0:LOGO_LANDSCAPE,1:LOGO_POSTER}[opt])

    @staticmethod  
    def _buildWebImage(image=None, fallback=LOGO):
        image = Globals._cleanImage(image)
        if not image: return fallback
        elif   image.startswith('image://'): image = '%s/image/%s'%(Globals._getProperty('%s.Local_Host'%(ADDON_ID)),Globals._quoteString(image))
        elif   image.startswith('http'):     image = 'http://%s/images/%s'%(Globals._getProperty('%s.Remote_Host'%(ADDON_ID)),Globals._quoteString(image))
        return image

    @staticmethod
    def _getDummyIcon(text, background=COLOR_BACKGROUND, color=COLOR_TEXT):
        if not isinstance(text, (str,bytes)): text = str(text)
        url  = f'https://dummyimage.com/512x512/{background}/{color}.png&text={Globals._quoteString(text)}'
        file = os.path.join(TEMP_IMAGE_LOC,f'{FileAccess._getMD5(url)}.png')
        if   FileAccess.exists(file):   return file
        elif Globals.setURL(url, file): return file
        return LOGO_COLOR
          
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
    def _mergeDictLST(dict1={},dict2={}):
        for k, v in list(dict2.items()):
            dict1.setdefault(k,[]).extend(v)
            Globals._setDictLST()
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
        if ADDON_NAME not in citem.get('group'): citem.setdefault('group',[]).append(ADDON_NAME)
        if REAL_SETTINGS.getSetting('Enable_Grouping') == "true":
            if citem.get('favorite',False) and not LANGUAGE(32019) in citem['group']: citem['group'].append(LANGUAGE(32019))
            elif not citem.get('favorite',False) and LANGUAGE(32019) in citem['group']: citem['group'].remove(LANGUAGE(32019))
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
            else:               return random.sample(items, len(items))
        return items
        
    @staticmethod
    def setURL(url, file):
        with FileLock(file):
            try:
                fle = FileAccess.open(file, 'w')
                fle.write(Globals.requestURL(url))
            except Exception as e: log('Globals: setURL failed! %s\nurl = %s'%(e,url), xbmc.LOGERROR)
            finally:
                if hasattr(fle, 'close'): fle.close()
        return FileAccess.exists(file)
        
    @staticmethod
    def requestURL(url, params={}, payload={}, header=HEADER, timeout=15, cache=None, file=None):
        #cache = {"cache":None, "checksum":ADDON_VERSION, "life": datetime.timedelta(minutes=15)}
        def __error(result={}):                              return result
        def __getCache(key, cache, checksum):                return (cache.get('requestURL.%s'%(FileAccess._getMD5(key)), checksum) or __error())
        def __setCache(key, results, cache, checksum, life): return cache.set('requestURL.%s'%(FileAccess._getMD5(key)), results, checksum, life)
            
        results = None
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        try:
            headers = HEADER.copy()
            headers.update(header)
            if payload: response = session.post(url, json=payload, files=file, headers=headers, timeout=timeout)
            else:       response = session.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()  # Raise an exception for HTTP errors
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/json' in content_type: results = response.json()
            else: results = response.content
            log("Globals: requestURL\nurl = %s, status = %s\nparams = %s\npayload = %s\nreturn type = %s"%(url,response.status_code,params,payload,type(results)))
            
            if results and not cache is None: 
                return __setCache('.'.join([url,FileAccess.dumpJSON(params),FileAccess.dumpJSON(payload),FileAccess.dumpJSON(header)]), 
                                  results, cache["cache"], cache.get("checksum",ADDON_VERSION), cache.get("life",datetime.timedelta(minutes=15)))
            return results 
        except Exception as e: 
            log("Globals: requestURL, failed! %s, An error occurred: %s"%('Returning cache' if cache else 'No Response', e))
            return __getCache('.'.join([url,FileAccess.dumpJSON(params),FileAccess.dumpJSON(payload),FileAccess.dumpJSON(header)]), 
                              cache["cache"], cache.get("checksum",ADDON_VERSION)) if cache else __error()
        # finally: #retry failed post
            # if results is None and payload:
                # Globals.queuePost(url, params, payload, header, timeout, None, file)
        
    # @staticmethod
    # def queuePost(url, params, payload, header, timeout, None, file):
        ...
        # posts = set(SETTINGS.getCacheSetting('postQue', revive=True) or [])
        # posts.add()
        # SETTINGS.setCacheSetting('postQue', list(posts), checksum=ADDON_VERSION)
