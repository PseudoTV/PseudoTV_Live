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
# -*- coding: utf-8 -*-
from contextlib  import contextmanager
from typing import Any, Optional, Iterator
from variables   import *
from videoparser import VideoParser
from _services   import _Service

# Lazy import to avoid circular dependency (variables.py defines Globals after kodi.py loads)
_Globals = None
def _globals() -> Any:
    global _Globals
    if _Globals is None:
        from variables import Globals as _Globals
    return _Globals

class JSONRPC(object):


    def __init__(self, service: Optional['_Service'] = None):
        self.runtimeThreshold = 15 #todo user setting % of allowed difference between runtime and duration before overriding runtime.
        if service is None: service = _Service()
        self.service     = service
        self.pool        = service.pool
        self.cache       = service.cache
        self.videoParser = VideoParser()
        self._session    = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)


    def log(self, msg: str, level: Optional[int] = None):
        if level is None: level = xbmc.LOGDEBUG
        LOG('%s: %s' % (self.__class__.__name__, msg), level)


    def requestURL(self, url: str, params: Optional[dict] = None, payload: Optional[dict] = None, header: Optional[dict] = None, timeout: Optional[int] = None, file: Optional[Any] = None, life: Optional[datetime.timedelta] = None) -> Any:
        """Make HTTP request with caching and retry queue for failed posts."""
        if params is None:  params  = {}
        if payload is None: payload = {}
        if header is None:  header  = {}
        if timeout is None: timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        if life is None:    life = datetime.timedelta(minutes=15)

        def __error(result: Optional[dict] = None) -> dict:
            if result is None: result = {}
            return result
        def __getCache() -> dict:       return (self.cache.get('requestURL.%s'%(FileAccess._getMD5((url,params,payload,file)))) or {})
        def __setCache() -> Any:       return self.cache.set('requestURL.%s'%(FileAccess._getMD5((url,params,payload,file))), results, expiration=life)
        def __setQueue(): 
            if hasattr(self.service,'postQue'): 
                self.service.postQue.add((url, params, payload, header, timeout, file, life))
            
        results = None

        try:
            headers = HEADER.copy()
            headers.update(header)
            if payload: response = self._session.post(url, json=payload, files=file, headers=headers, timeout=timeout)
            else:       response = self._session.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()  # Raise an exception for HTTP errors
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/json' in content_type: results = response.json()
            else:                                  results = response.content
            self.log("requestURL %s, status=%s, type=%s" % (url, response.status_code, type(results).__name__))
            if results: return __setCache()
        except Exception as e: 
            self.log("requestURL %s failed: %s" % (url, e))
            __getCache()
        finally: #retry failed post
            if results is None and payload: __setQueue()
        return results 
        
        
    def sendRemote(self, param: dict, ip: Optional[str] = None, timeout: Optional[int] = None) -> Optional[dict]:
        """Send JSON-RPC command via raw TCP socket to Kodi webserver."""
        if ip is None: ip = (xbmc.getIPAddress() or gethostbyname(gethostname()) or '0.0.0.0')
        if timeout is None: timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        try:
            command = param
            command["jsonrpc"] = "2.0"
            command["id"] = f"{ADDON_ID}.remote"
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(float(timeout))
            sock.connect((ip, 9090))
            sock.sendall(command.encode(DEFAULT_ENCODING))
            return FileAccess.loadJSON(sock.recv(4096).decode(DEFAULT_ENCODING))
        except socket.timeout:
            self.log("sendRemote to %s timed out (timeout=%ds)" % (ip, timeout), xbmc.LOGERROR)
            return None
        finally:
            sock.close()
        


    def sendJSON(self, param: dict, timeout: Optional[int] = None) -> dict:
        command = param
        command["jsonrpc"] = "2.0"
        command["id"] = f"{ADDON_ID}.local"
        if timeout is None: timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        try:
            response = FileAccess.loadJSON(self.pool.executor(xbmc.executeJSONRPC,timeout,FileAccess.dumpJSON(command))) or {}
        except Exception as e:
            self.log('sendJSON, failed to parse response: %s' % e, xbmc.LOGWARNING)
            response = {}
        if response and response.get('error'):
            self.log('sendJSON %s error: %s' % (param.get('method','?'), response.get('error',{}).get('message',LANGUAGE(30079))), xbmc.LOGWARNING)
            response.setdefault('result',{})['error'] = response.pop('error') #move to result for processing in builder.
        return response


    def queueJSON(self, param: dict):
        if hasattr(self.service,'jsonQue'): self.service.jsonQue.append(param)
        
        
    def cacheJSON(self, param: dict, life: Optional[datetime.timedelta] = None, checksum: Optional[str] = None, timeout: Optional[int] = None) -> dict:
        if checksum is None: checksum = ADDON_VERSION
        if life is None: life = datetime.timedelta(minutes=5)
        if timeout is None: timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        cacheName = 'cacheJSON.%s'%(FileAccess._getMD5(FileAccess.dumpJSON(param)))
        cacheResponse = self.cache.get(cacheName, checksum=checksum)
        if not cacheResponse:
            cacheResponse = self.sendJSON(param,timeout=timeout)
            if cacheResponse.get('result',{}): self.cache.set(cacheName, cacheResponse, checksum=checksum, expiration=life)
        return cacheResponse


    def walkFileDirectory(self, path: str, media: str = 'video', limit: Optional[int] = None, depth: Optional[int] = None, checksum: Optional[str] = None, expiration: Optional[datetime.timedelta] = None, dir: Optional[dict] = None) -> dict:
        if dir is None: dir = {'label':'resources'}
        if limit is None: limit = CHANNEL_LIMIT * depth
        if depth is None: depth = int(REAL_SETTINGS.getSetting('Recursive_Depth') or "0")
        if checksum is None: checksum = ADDON_VERSION
        if expiration is None: expiration = datetime.timedelta(minutes=15)
        walk = {}
        walk_depth = depth
        subs = []
        self.log('walkFileDirectory, walking %s, limit = %s, depth = %s'%(path,limit,depth))
        items, limits, errors = self.getDirectory({"directory":path,"media":media},True,checksum,expiration)
        for item in items:
            if self.service.interrupt(): break
            elif item.get('filetype') == 'file' and limit > 0:
                limit -= 1
                accurate = bool(int(REAL_SETTINGS.getSetting('Duration_Type') or "0"))
                item['duration'] = self.getDuration(item.get('file'),item,accurate)
                walk.setdefault(dir.get('label','root'),[]).append(item)
            elif item.get('filetype') == 'directory' and walk_depth > 0:
                walk_depth -= 1
                subs.append(item)
        for sub in subs:
            if sub.get('file') and limit > 0 and not self.service.monitor.waitForAbort(CPU_CYCLE):
                walk.update(self.walkFileDirectory(sub.get('file'), media, limit, depth, checksum, expiration, dir=sub))
        self.log('walkFileDirectory, walking finished')
        return walk
                


    def walkListDirectory(self, path: str, exts: Optional[list] = None, depth: Optional[int] = None, checksum: Optional[str] = None, expiration: Optional[datetime.timedelta] = None) -> dict:
        if exts is None: exts = []
        if checksum is None: checksum = ADDON_VERSION
        if expiration is None: expiration = datetime.timedelta(minutes=15)
        accurate_duration = bool(int(REAL_SETTINGS.getSetting('Duration_Type') or "0"))
        if depth is None: depth = int(REAL_SETTINGS.getSetting('Recursive_Depth') or "0")
        def __(path: str, f: str) -> Optional[dict]:
            if exts and f.lower().endswith(tuple(exts)): return
            fullpath = os.path.join(path,f)
            return {'label': os.path.basename(path.rstrip('/')),
                    'filetype': 'file',
                    'title': path,
                    'file': fullpath,
                    'duration':self.getDuration(fullpath, accurate=accurate_duration)}
        walk = {}
        path = path.replace('\\','/')
        subs, files = self.getListDirectory(path,checksum,expiration)
        self.log('walkListDirectory, walking %s, found = (%s,%s), depth = %s'%(path,len(subs),len(files),depth))
        items = [__(path, _f) for _f in files if _f]
        if items: walk.setdefault(path,[]).extend([_i for _i in items if _i])
        for sub in subs:
            if depth <= 0: break
            depth -= 1
            walk.update(self.walkListDirectory(os.path.join(path,sub), exts, depth, checksum, expiration))
        return walk
                
          
    def getListDirectory(self, path: str, checksum: Optional[str] = None, expiration: Optional[datetime.timedelta] = None) -> tuple:
        if checksum is None: checksum = ADDON_VERSION
        if expiration is None: expiration = datetime.timedelta(minutes=15)
        cacheName = 'getListDirectory.%s'%(FileAccess._getMD5(path))
        results   = self.cache.get(cacheName, checksum)
        if results is None:
            try:
                results  = self.cache.set(cacheName, FileAccess.listdir(path), checksum, expiration)
                self.log('getListDirectory path = %s, checksum = %s'%(path, checksum))
            except Exception as e:
                self.log("getListDirectory, failed! %s\npath = %s"%(e,path), xbmc.LOGERROR)
                results = [],[]
        return results


    def getIntrospect(self, id: str) -> dict:
        param = {"method":"JSONRPC.Introspect","params":{"filter":{"id":id,"type":"method"}}}
        return self.cacheJSON(param,datetime.timedelta(days=28),self.getInfoLabel('System.BuildVersion')).get('result',{})


    def getEnums(self, id: str, type: str = '', key: str = 'enums') -> Any:
        self.log('getEnums id = %s, type = %s, key = %s' % (id, type, key))
        param = {"method":"JSONRPC.Introspect","params":{"getmetadata":True,"filterbytransport":True,"filter":{"getreferences":False,"id":id,"type":"type"}}}
        json_response = self.cacheJSON(param,datetime.timedelta(days=28),self.getInfoLabel('System.BuildVersion')).get('result',{}).get('types',{}).get(id,{})
        return (json_response.get('properties',{}).get(type,{}).get(key) or json_response.get(type,{}).get(key) or json_response.get(key,[]))


    def notifyAll(self, message: str, data: Any, sender: Optional[str] = None) -> bool:
        if sender is None: sender = ADDON_ID
        param = {"method":"JSONRPC.NotifyAll","params":{"sender":sender,"message":message,"data":[data]}}
        return self.sendJSON(param).get('result') == 'OK'


    def playerOpen(self, params: Optional[dict] = None) -> bool:
        if params is None: params = {}
        param = {"method":"Player.Open","params":params}
        return self.sendJSON(param).get('result') == 'OK'


    def getSetting(self, category: str, section: str, cache: bool = False) -> list:
        param = {"method":"Settings.getSettings","params":{"filter":{"category":category,"section":section}}}
        if cache: return self.cacheJSON(param).get('result',{}).get('settings',[])
        else:     return self.sendJSON(param).get('result',{}).get('settings',[])


    def getSettingValue(self, key: str, default: Any = '', cache: bool = False) -> Any:
        param = {"method":"Settings.getSettingValue","params":{"setting":key}}
        if cache: value = self.cacheJSON(param).get('result',{}).get('value')
        else:     value = self.sendJSON(param).get('result',{}).get('value')
        self.log(f'[{ADDON_ID}] getSettingValue, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return value  or default


    def setSettingValue(self, key: str, value: Any, queue: bool = False):
        param = {"method":"Settings.SetSettingValue","params":{"setting":key,"value":value}}
        if queue: self.queueJSON(param)
        else:     self.sendJSON(param)
        self.log(f'[{ADDON_ID}] setSettingValue, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        


    def getSources(self, media: str = 'video', cache: bool = True) -> list:
        param = {"method":"Files.GetSources","params":{"media":media}}
        if cache: return self.cacheJSON(param).get('result',{}).get('sources', [])
        else:     return self.sendJSON(param).get('result',{}).get('sources', [])


    def getAddonDetails(self, addonid: Optional[str] = None, cache: bool = True) -> dict:
        if addonid is None: addonid = ADDON_ID
        param = {"method":"Addons.GetAddonDetails","params":{"addonid":addonid,"properties":self.getEnums("Addon.Fields", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('addon', {})
        else:     return self.sendJSON(param).get('result',{}).get('addon', {})


    def getAddons(self, param: Optional[dict] = None, cache: bool = True) -> list:
        if param is None: param = {"content":"video","enabled":True,"installed":True}
        param["properties"] = self.getEnums("Addon.Fields", type='items')
        param = {"method":"Addons.GetAddons","params":param}
        if cache: return self.cacheJSON(param).get('result',{}).get('addons', [])
        else:     return self.sendJSON(param).get('result',{}).get('addons', [])


    def getSongs(self, cache: bool = True) -> list:
        param = {"method":"AudioLibrary.GetSongs","params":{"properties":self.getEnums("Audio.Fields.Song", type='items')}}
        timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        if cache: return self.cacheJSON(param, timeout).get('result',{}).get('songs', [])
        else:     return self.sendJSON(param, timeout).get('result',{}).get('songs', [])


    def getArtists(self, cache: bool = True) -> list:
        param = {"method":"AudioLibrary.GetArtists","params":{"properties":self.getEnums("Audio.Fields.Artist", type='items')}}
        timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        if cache: return self.cacheJSON(param, timeout).get('result',{}).get('artists', [])
        else:     return self.sendJSON(param, timeout).get('result',{}).get('artists', [])


    def getAlbums(self, cache: bool = True) -> list:
        param = {"method":"AudioLibrary.GetAlbums","params":{"properties":self.getEnums("Audio.Fields.Album", type='items')}}
        timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        if cache: return self.cacheJSON(param, timeout).get('result',{}).get('albums', [])
        else:     return self.sendJSON(param, timeout).get('result',{}).get('albums', [])

     
    def getEpisode(self, tvshowid: int, season: int, episode: Optional[int] = None, cache: bool = True) -> list:
        if not episode is None: filter = {"field":"episode","operator":"is","value":str(episode)}
        else:                   filter = {}
        param = {"method":"VideoLibrary.GetEpisodes","params":{"tvshowid":tvshowid,"season":season,"properties":self.getEnums("Video.Fields.Episode", type='items'),"filter":filter}}
        if cache: return self.cacheJSON(param).get('result',{}).get('episodes', [])
        else:     return self.sendJSON(param).get('result',{}).get('episodes', [])
  
  
    def getEpisodes(self, cache: bool = True) -> list:
        param = {"method":"VideoLibrary.GetEpisodes","params":{"properties":self.getEnums("Video.Fields.Episode", type='items')}}
        timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        if cache: return self.cacheJSON(param, timeout).get('result',{}).get('episodes', [])
        else:     return self.sendJSON(param, timeout).get('result',{}).get('episodes', [])


    def getTVshows(self, cache: bool = True) -> list:
        param = {"method":"VideoLibrary.GetTVShows","params":{"properties":self.getEnums("Video.Fields.TVShow", type='items')}}
        timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        if cache: return self.cacheJSON(param, timeout).get('result',{}).get('tvshows', [])
        else:     return self.sendJSON(param, timeout).get('result',{}).get('tvshows', [])


    def getMovie(self, uniqueid: Any, title: str, year: int, cache: bool = True) -> list:
        param = {"method":"VideoLibrary.GetMovies","params":{"properties":self.getEnums("Video.Fields.Movie", type='items'),"filter":{"and":[{"field":"title","operator":"is","value":title},{"field":"year","operator":"is","value":str(year)}]}}}
        if cache: return self.cacheJSON(param).get('result',{}).get('movies', [])
        else:     return self.sendJSON(param).get('result',{}).get('movies', [])


    def getMovies(self, cache: bool = True) -> list:
        param = {"method":"VideoLibrary.GetMovies","params":{"properties":self.getEnums("Video.Fields.Movie", type='items')}}
        timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        if cache: return self.cacheJSON(param, timeout).get('result',{}).get('movies', [])
        else:     return self.sendJSON(param, timeout).get('result',{}).get('movies', [])


    def getVideoGenres(self, type: str = "movie", cache: bool = True) -> list: #type = "movie"/"tvshow"
        param = {"method":"VideoLibrary.GetGenres","params":{"type":type,"properties":self.getEnums("Library.Fields.Genre", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('genres', [])
        else:     return self.sendJSON(param).get('result',{}).get('genres', [])


    def getMusicGenres(self, cache: bool = True) -> list:
        param = {"method":"AudioLibrary.GetGenres","params":{"properties":self.getEnums("Library.Fields.Genre", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('genres', [])
        else:     return self.sendJSON(param).get('result',{}).get('genres', [])


    def getTextures(self, cache: bool = True) -> list:
        param = {"method":"Textures.GetTextures","params":{"properties":self.getEnums("Textures.Fields.Texture", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('textures', [])
        else:     return self.sendJSON(param).get('result',{}).get('textures', [])
            
        
    def getDirectory(self, param: Optional[dict] = None, cache: bool = True, checksum: Optional[str] = None, expiration: Optional[datetime.timedelta] = None) -> tuple:
        if param is None: param = {}
        if _globals().properties.isPendingSuspend(): return [],{},{}
        if checksum is None: checksum = ADDON_VERSION
        if expiration is None: expiration = datetime.timedelta(minutes=15)
        param["properties"] = self.getEnums("List.Fields.Files", type='items') #todo change enums from files to media specific? 
        param   = {"method":"Files.GetDirectory","params":param}
        timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        if cache: results = self.cacheJSON(param, expiration, checksum, timeout).get('result',{})
        else:     results = self.sendJSON(param, timeout).get('result',{})
        if 'filedetails' in results: return results.get('filedetails',[]), results.get('limits',{}), results.get('error',{})
        else:                        return results.get('files',[]), results.get('limits',{}), results.get('error',{})


    def getLibrary(self, method: str, param: Optional[dict] = None, key: Optional[str] = None, cache: bool = True) -> tuple:
        if param is None: param = {}
        param   = {"method":method,"params":param}
        timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        if cache: results = self.cacheJSON(param, timeout).get('result',{})
        else:     results = self.sendJSON(param, timeout).get('result',{})
        return results.get((key or list(results.keys())[0]),[]), results.get('limits',{}), results.get('error',{})
        
        
    def getMPAA(self, type: str = 'movie', incItem: bool = False) -> list:
        def __parse(items: list) -> Iterator[dict]: 
            for item in items:
                yield {'label':_globals()._cleanMPAA(item.get("mpaa","NR")),'item':item if incItem else {}}
        if   type == 'movie':  return list(__parse(self.getMovies()))
        elif type == 'tvshow': return list(__parse(self.getTVshows()))


    def getStreamDetails(self, path: str, media: str = 'video') -> dict:
        if _globals()._isStack(path): path = _globals()._splitStacks(path)[0]
        param = {"method":"Files.GetFileDetails","params":{"file":path,"media":media,"properties":["streamdetails"]}}
        return self.cacheJSON(param, life=datetime.timedelta(days=MAX_GUIDEDAYS), checksum=FileAccess._getMD5(path)).get('result',{}).get('filedetails',{}).get('streamdetails',{})


    def getFileDetails(self, file: str, media: str = 'video', properties: list = ["duration","runtime"]) -> dict:
        return self.cacheJSON({"method":"Files.GetFileDetails","params":{"file":file,"media":media,"properties":properties}})


    def getViewMode(self) -> dict:
        default = {"nonlinearstretch":False,"pixelratio":1,"verticalshift":0,"viewmode":"custom","zoom": 1.0}
        return self.cacheJSON({"method":"Player.GetViewMode","params":{}},datetime.timedelta(seconds=15)).get('result',default)
        


    def setViewMode(self, params: Optional[dict] = None) -> dict:
        if params is None: params = {}
        return self.sendJSON({"method":"Player.SetViewMode","params":params})


    def getPlayerItem(self, playlist: bool = False) -> Any:
        self.log('getPlayerItem, playlist = %s' % (playlist))
        if playlist: param = {"method":"Playlist.GetItems","params":{"playlistid":self.getActivePlaylist(),"properties":self.getEnums("List.Fields.All", type='items')}}
        else:        param = {"method":"Player.GetItem"   ,"params":{"playerid":self.getActivePlayer()    ,"properties":self.getEnums("List.Fields.All", type='items')}}
        result = self.sendJSON(param).get('result',{})
        return (result.get('item', {}) or result.get('items', []))


    def getPVRClients(self) -> list:
        param = {"method":"PVR.GetClients","params":{}}
        return self.sendJSON(param).get('result',{}).get('clients',[])


    def getPVRClient(self, id: Optional[str] = None) -> Optional[dict]:
        if id is None: id = PVR_CLIENT_ID
        results = self.getPVRClients()
        return next((result for result in results if result.get('addonid','').lower() == id.lower()),None)


    def getPVRChannelGroups(self, match: Optional[str] = None, radio: bool = False) -> Any:
        if match is None: match = ADDON_NAME
        param   = {"method":"PVR.GetChannelGroups","params":{"channeltype":{True:'radio',False:'tv'}[radio]}}
        results = self.sendJSON(param).get('result',{}).get('channelgroups', [])
        if match is None: return results
        return next((result for result in results if result.get('label').lower() == match.lower()), None)

        
    def getPVRChannelGroupDetails(self, id: int) -> list:
        param = {"method":"PVR.GetChannelGroupDetails","params":{"channelgroupid":1,"channels":{"limits":{"end":0,"start":0},"properties":self.getEnums("PVR.Fields.Channel", type='items')}}}
        return self.sendJSON(param).get('result',{}).get('channelgroupdetails', {}).get('channels',[])
        


    def PVRScan(self, id: int) -> dict:
        param = {"method":"PVR.Scan","params":{"clientid":id}}
        return self.sendJSON(param).get('result',{})
        
        
    def getPVRChannels(self, radio: bool = False) -> list:
        param = {"method":"PVR.GetChannels","params":{"channelgroupid":{True:'allradio',False:'alltv'}[radio],"properties":self.getEnums("PVR.Fields.Channel", type='items')}}
        return self.sendJSON(param).get('result',{}).get('channels', [])


    def getPVRChannelsDetails(self, id: int) -> list:
        param = {"method":"PVR.GetChannelDetails","params":{"channelid":id,"properties":self.getEnums("PVR.Fields.Channel", type='items')}}
        return self.sendJSON(param).get('result',{}).get('channels', [])


    def getPVRBroadcasts(self, id: int) -> list:
        param = {"method":"PVR.GetBroadcasts","params":{"channelid":id,"properties":self.getEnums("PVR.Fields.Broadcast", type='items')}}
        return self.sendJSON(param).get('result',{}).get('broadcasts', [])


    def getPVRBroadcastDetails(self, id: int) -> list:
        param = {"method":"PVR.GetBroadcastDetails","params":{"broadcastid":id,"properties":self.getEnums("PVR.Fields.Broadcast", type='items')}}
        return self.sendJSON(param).get('result',{}).get('broadcastdetails', [])


    def getPVRRecordings(self, media: str = 'video', cache: bool = True) -> list:
        param = {"method":"Files.GetDirectory","params":{"directory":"pvr://recordings/tv/active/","media":media,"properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('files', [])
        else:     return self.sendJSON(param).get('result',{}).get('files', [])

    
    def getPVRSearches(self, media: str = 'video', cache: bool = True) -> list:
        param = {"method":"Files.GetDirectory","params":{"directory":"pvr://search/tv/savedsearches/","media":media,"properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('files', [])
        else:     return self.sendJSON(param).get('result',{}).get('files', [])
        
        
    def getPVRSearchItems(self, id: int, media: str = 'video', cache: bool = True) -> list:
        param = {"method":"Files.GetDirectory","params":{"directory":f"pvr://search/tv/savedsearches/{id}/","media":media,"properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('files', [])
        else:     return self.sendJSON(param).get('result',{}).get('files', [])
    
    
    def getSmartPlaylists(self, type: str = 'video', cache: bool = True) -> list:
        param = {"method":"Files.GetDirectory","params":{"directory":f"special://profile/playlists/{type}/","media":"video","properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('files', [])
        else:     return self.sendJSON(param).get('result',{}).get('files', [])
        
        
    def getInfoLabel(self, key: str, cache: bool = False) -> Optional[str]:
        param = {"method":"XBMC.GetInfoLabels","params":{"labels":[key]}}
        if cache: return self.cacheJSON(param).get('result',{}).get(key)
        else:     return self.sendJSON(param).get('result',{}).get(key)


    def getInfoBool(self, key: str, cache: bool = False) -> Optional[bool]:
        param = {"method":"XBMC.GetInfoBooleans","params":{"booleans":[key]}}
        if cache: return self.cacheJSON(param).get('result',{}).get(key)
        else:     return self.sendJSON(param).get('result',{}).get(key)
    
    
    def DBIDtoLabel(self, path: str) -> str:
        self.log('DBIDtoLabel, IN = %s'%(path))
        match = re.search(r"(.*?)/(\d+)/", path)
        if match:
            items = self.getDirectory({"directory":match.group(1),"media":"video"})[0]
            for item in items:
                if int(match.group(2)) == item.get('id'):
                    self.log('DBIDtoLabel, path = %s, id = %s, label = %s'%(match.group(1),match.group(2),item['label']))
                    path = item['label']
                    break
        self.log('DBIDtoLabel, OUT = %s'%(path))
        return path
        
        
    def _setRuntime(self, item: Optional[dict] = None, runtime: int = 0, save: Optional[bool] = None): #set runtime collected by player, accurate meta.
        if item is None: item = {}
        if save is None: save = REAL_SETTINGS.getSetting('Store_Duration') == 'true'
        runtime = round(runtime)
        md5 = FileAccess._getMD5(item.get('file'))
        self.cache.set('getRuntime.%s'%(md5), runtime, checksum=md5, expiration=datetime.timedelta(days=28))
        if not item.get('file','plugin://').startswith(tuple(VFS_TYPES)) and save and runtime > 0: self.queDuration(item, runtime=runtime)
    
        
    def _getRuntime(self, item: Optional[dict] = None) -> int: #get runtime collected by player, else less accurate provider meta
        if item is None: item = {}
        file_key = item.get('file')
        md5 = FileAccess._getMD5(file_key)
        runtime = self.cache.get('getRuntime.%s'%(md5), checksum=md5)
        return round(runtime or item.get('resume',{}).get('total') or item.get('runtime') or item.get('duration') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration') or 0)
        


    def _setDuration(self, path: str, item: Optional[dict] = None, duration: int = 0, save: Optional[bool] = None) -> int: #set VideoParser cache
        if item is None: item = {}
        if save is None: save = REAL_SETTINGS.getSetting('Store_Duration') == 'true'
        duration = round(duration)
        md5 = FileAccess._getMD5(path)
        self.cache.set('getDuration.%s'%(md5), duration, checksum=md5, expiration=datetime.timedelta(days=28))
        if save and item: self.queDuration(item, duration)
        return duration

    
    def _getDuration(self, path: str) -> int: #get VideoParser cache
        md5 = FileAccess._getMD5(path)
        return round(self.cache.get('getDuration.%s'%(md5), checksum=md5) or self._getRuntime({'file':path}))


    def getDuration(self, path: str, item: Optional[dict] = None, accurate: Optional[bool] = None, save: Optional[bool] = None) -> int:
        """Resolve video duration from player runtime, VideoParser, and metadata fallbacks."""
        if item is None: item = {}
        if accurate is None: accurate = bool(int(REAL_SETTINGS.getSetting('Duration_Type') or "0"))
        if save is None: save = REAL_SETTINGS.getSetting('Store_Duration') == 'true'
        def __parseDuration(runtime: int, path: str, item: Optional[dict] = None, save: bool = False) -> int:
            if item is None: item = {}
            duration = self.videoParser.getVideoLength(path.replace("\\\\", "\\"), item, self)
            if   runtime == 0: runtime = duration
            elif round(_globals()._percentDiff(runtime, duration)) <= self.runtimeThreshold: runtime = duration
            if save and duration != runtime: self.queDuration(item, runtime)
            return runtime
            
        if not item: item = {'file':path}
        runtime = self._getRuntime(item) #player runtime, fallback meta provider runtime
        if runtime == 0 or accurate:
            duration = 0
            if _globals()._isStack(path):# handle "stacked" videos
                for file in _globals()._splitStacks(path): duration += __parseDuration(runtime, file)
            else: duration = __parseDuration(runtime, path, item, save)
            if duration > 0: runtime = duration
        self.log(f"getDuration [{runtime}], {path}, accurate = {accurate}, save ={save}")
        return runtime


    def getTotDuration(self, items: Optional[list] = None, accurate: Optional[bool] = None) -> int:
        if items is None: items = []
        if accurate is None: accurate = bool(int(REAL_SETTINGS.getSetting('Duration_Type') or "0"))
        total = sum((self.getDuration(item.get('file'),item,accurate) for item in items))
        self.log("getTotDuration, items = %s, total = %s" % (len(items), total))
        return total


    def queDuration(self, item: Optional[dict] = None, duration: int = 0, runtime: int = 0):
        """Queue a JSON-RPC command to update media item duration/runtime."""
        if item is None: item = {}
        mtypes = {'video'      : {"method":"Files.SetFileDetails"             ,"params":{"file"        :item.get('file',"")         ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'movie'      : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'movies'     : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('movieid',-1)      ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'episode'    : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'episodes'   : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('episodeid',-1)    ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'musicvideo' : {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'musicvideos': {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('musicvideoid',-1) ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'song'       : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'songs'      : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('songid',-1)       ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}}}
        
        if not item.get('file','plugin://').startswith(tuple(VFS_TYPES)):
            try:
                mtype = mtypes.get(item.get('type'))
                if mtype and mtype.get('params'):
                    if   duration == 0: mtype['params'].pop('resume')  
                    elif runtime  == 0: mtype['params'].pop('runtime') 
                    id = (item.get('id') or item.get('movieid') or item.get('episodeid') or item.get('musicvideoid') or item.get('songid'))
                    self.log('[%s] queDuration, media = %s, duration = %s, runtime = %s'%(id,item['type'],duration,runtime))
                    self.queueJSON(mtype)
            except Exception as e: self.log("queDuration, failed! %s\nmtype = %s\nitem = %s"%(e,mtype,item), xbmc.LOGERROR)
        
        
    def quePlaycount(self, item: Optional[dict] = None, save: Optional[bool] = None):
        if item is None: item = {}
        if save is None: save = REAL_SETTINGS.getSetting('Rollback_Watched') == 'true'
        param = {'video'      : {"method":"Files.SetFileDetails"             ,"params":{"file"        :item.get('file',"")         ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'movie'      : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('id',-1)           ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'movies'     : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('movieid',-1)      ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'episode'    : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('id',-1)           ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'episodes'   : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('episodeid',-1)    ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'musicvideo' : {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('id',-1)           ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'musicvideos': {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('musicvideoid',-1) ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'song'       : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('id',-1)           ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'songs'      : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('songid',-1)       ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}}}

        if not item.get('file','plugin://').startswith(tuple(VFS_TYPES)):
            try:
                params = param.get(item.get('type'))
                self.log('quePlaycount, params = %s'%(params.get('params',{})))
                if hasattr(self.service, 'jsonQue'): self.service.jsonQue.append(params)
            except Exception as e: self.log('quePlaycount failed: %s' % e, xbmc.LOGDEBUG)
                
                
    def requestList(self, citem: dict, path: str, media: str = 'video', page: Optional[int] = None, sort: Optional[dict] = None, filter: Optional[dict] = None, limits: Optional[dict] = None, query: Optional[dict] = None) -> tuple:
        """Build paginated request list with auto-pagination and cache thresholds."""
        if _globals().properties.isPendingSuspend(): return [],{},{}
        if page is None:   page = int(REAL_SETTINGS.getSetting('Page_Limit') or "50")
        if sort is None:   sort = {}
        if filter is None: filter = {}
        if limits is None: limits = {"end": -1, "start": 0, "total": 0}
        if query is None:  query = {}

        ch_id = citem.get('id')
        param = {}
        
        # Library Query or VFS File Directory
        if query:
            getDirectory = False
            param['filter'] = query.get('filter', {})
            
            enum_key = query.get('enum')
            if enum_key:
                param["properties"] = self.getEnums(enum_key, type='items')
        else:
            getDirectory = True
            param["media"] = media
            param["directory"] = path
            param["properties"] = self.getEnums("List.Fields.Files", type='items')
        self.log(f"requestList, id: {ch_id}, getDirectory = {getDirectory}, media = {media}, limit = {page}, sort = {sort}, query = {query}, limits = {limits}\npath = {path}")
        
        # Process Auto-Pagination and Cache Thresholds
        if limits.get('end', -1) == -1:
            limits = self.autoPagination(ch_id, path, query)
            self.log(f'[{ch_id}] requestList, autoPagination limits = {limits}')
            
            if limits.get('total', 0) > page and sort.get("method", "") == "random":
                limits = self.randomPagination(page, limits)
                self.log(f'[{ch_id}] requestList, generating random limits = {limits}')

        if limits.get('start', 0) >= 0:
            current_end = limits.get('end', 0)
            param["limits"] = {
                "start": 0 if current_end == -1 else current_end,
                "end": page
            }
            
        param["sort"] = sort
        self.log(f'[{ch_id}] requestList, page = {page}\nparam = {param}')
        
        items, errors = [], {}
        with self.detectRPCCrash(citem):
            if getDirectory:
                items, limits, errors = self.getDirectory(param)
            else:
                items, limits, errors = self.getLibrary(query.get('method'), param, query.get('key'), cache=False)

        if not isinstance(items, list):
            items = []

        total_records  = limits.get('total', 0)
        start_boundary = limits.get('start', 0)
        end_boundary   = limits.get('end', 0)
        if end_boundary >= total_records or start_boundary >= total_records:
            self.log(f'[{ch_id}] requestList, exceeding boundaries. Resetting limits to 0')
            limits = {"end": 0, "start": 0, "total": total_records}
              
        if len(items) == 0 and total_records > 0 and end_boundary > 0:
            self.log(f"[{ch_id}] requestList, items empty but total count exists. Retrying with fresh bounds at 0.")
            fallback_limits = {"end": 0, "start": 0, "total": total_records}
            return self.requestList(citem, path, media, page, sort, filter, fallback_limits, query)
        else:          
            self.autoPagination(ch_id, path, query, limits)
            self.log(f"[{ch_id}] requestList, return items = {len(items)}")
            return items, limits, errors


    def resetPagination(self, id: str, path: str, query: Optional[dict] = None, limits: Optional[dict] = None) -> dict:
        if query is None: query = {}
        if limits is None: limits = {"end": 0, "start": 0, "total":0}
        return self.autoPagination(id, path, query, limits)
            
            
    def autoPagination(self, id: str, path: str, query: Optional[dict] = None, limits: Optional[dict] = None) -> dict:
        if query is None: query = {}
        if limits is None: limits = {}
        if not limits: return (self.cache.get('autoPagination.%s.%s.%s'%(id,FileAccess._getMD5(path),FileAccess._getMD5(FileAccess.dumpJSON(query))), checksum=id) or {"end": 0, "start": 0, "total":0})
        else:          return  self.cache.set('autoPagination.%s.%s.%s'%(id,FileAccess._getMD5(path),FileAccess._getMD5(FileAccess.dumpJSON(query))), limits, checksum=id, expiration=datetime.timedelta(days=28))
            
             
    def randomPagination(self, page: Optional[int] = None, limits: Optional[dict] = None, start: int = 0) -> dict:
        if limits is None: limits = {}
        if page is None: page = int(REAL_SETTINGS.getSetting('Page_Limit') or "50")
        if limits.get('total',0) > page: start = random.randrange(0, (limits.get('total',0)-page), page)
        return {"end": start, "start": start, "total":limits.get('total',0)}
        

    @contextmanager
    def detectRPCCrash(self, citem: dict) -> Iterator[None]:
        """Context manager to save/restore channel item on JSON-RPC crash."""
        REAL_SETTINGS.setSetting('KODI.CRASH.JSONRPC.CITEM', FileAccess.dumpJSON(citem))
        try: yield
        except Exception as e: self.log('detectRPCCrash: %s' % e, xbmc.LOGDEBUG)
        finally:
            REAL_SETTINGS.setSetting('KODI.CRASH.JSONRPC.CITEM', '')


    def getLocalHost(self, local: bool = False) -> str:
        port     = 80
        username = 'kodi'
        password = ''
        secure   = False
        enabled  = True
        settings = self.getSetting('control','services',cache=True)
        for setting in settings:
            if setting.get('id','').lower() == 'services.webserver' and not setting.get('value'):
                enabled = False
                Dialog().notificationDialog(LANGUAGE(32131))
                break
            if   setting.get('id','').lower() == 'services.webserverusername': username = setting.get('value')
            elif setting.get('id','').lower() == 'services.webserverport':     port     = setting.get('value')
            elif setting.get('id','').lower() == 'services.webserverpassword': password = setting.get('value')
            elif setting.get('id','').lower() == 'services.webserverssl' and setting.get('value'): secure = True
        username = '{0}:{1}@'.format(username, password) if username and password else ''
        protocol = 'https' if secure else 'http'
        if local: ip = 'localhost'
        else:     ip = (xbmc.getIPAddress() or gethostbyname(gethostname()) or '0.0.0.0')
        webURL =  '{0}://{1}{2}:{3}'.format(protocol,username,ip,port)
        self.log("getLocalHost; returning %s"%(webURL))
        return webURL


    def padItems(self, files: list, page: Optional[int] = None) -> list:
        if page is None: page = int(REAL_SETTINGS.getSetting('Page_Limit') or "50")
        # Balance media limits, by filling with duplicates to meet min. pagination.
        self.log("padItems; files In = %s"%(len(files)))
        if len(files) < page:
            iters = cycle(files)
            while not self.service.monitor.abortRequested() and (len(files) < page and len(files) > 0):
                item = next(iters).copy()
                if   self.service.interrupt(): break
                elif self.getDuration(item.get('file'),item) == 0:
                    try: files.pop(files.index(item))
                    except Exception: break
                else: files.append(item)
        self.log("padItems; files Out = %s"%(len(files)))
        return files


    def inputFriendlyName(self) -> str:
        friendly = self.getSettingValue("services.devicename")
        self.log("inputFriendlyName, name = %s"%(friendly))
        if not friendly or friendly.lower() == 'kodi':
            if Dialog().okDialog(LANGUAGE(32132).format(name=friendly)):
                friendly = Dialog().inputDialog(LANGUAGE(30122), friendly)
                if not friendly or friendly.lower() == 'kodi':
                    return self.inputFriendlyName()
                else:
                    self.setSettingValue("services.devicename",friendly,queue=False)
                    self.log('inputFriendlyName, setting device name = %s'%(friendly))
        return friendly
           
           
    def getCallback(self, sysInfo: Optional[dict] = None) -> str:
        """Resolve channel playback callback URL from PVR data."""
        if sysInfo is None: sysInfo = {}
        chid  = sysInfo.get('chid')
        mode  = sysInfo.get('mode', '').lower()
        radio = sysInfo.get('radio', False)
        citem = sysInfo.get('citem', {})
        self.log('[%s] getCallback, mode = %s, radio = %s, isPlaylist = %s' % 
                 (chid, mode, radio, sysInfo.get('isPlaylist', False)))

        if mode == 'live' and sysInfo.get('chpath'):
            callback = sysInfo.get('chpath')
        elif sysInfo.get('isPlaylist'):
            callback = citem.get('url')
        elif mode in ('vod', 'broadcast') and sysInfo.get('nitem', {}).get('file'):
            callback = sysInfo.get('nitem', {}).get('file')
        else:
            callback = sysInfo.get('callback', '')

        if not callback:
            target_id = chid or citem.get('id')
            dir_type  = 'radio' if radio else 'tv'
            results, _, _ = self.getDirectory(param={"directory": f"pvr://channels/{dir_type}/"},cache=False)
            
            for result in results:
                label = result.get('label', '')
                if label.startswith(ADDON_NAME) or label.startswith('All channels'):
                    channels, _, _ = self.getDirectory(param={"directory": result.get('file')},checksum=ADDON_VERSION,expiration=datetime.timedelta(minutes=15))
                    
                    for item in channels:
                        fitem_id = _globals()._decodePlot(item.get('plot', '')).get('citem', {}).get('id')
                        if fitem_id == target_id:
                            callback = item.get('file')
                            self.log('[%s] getCallback: matched file' % chid)
                            break
                if callback: break
        self.log('getCallback: returning callback = %s' % callback)
        return callback


    def matchChannel(self, chname: str, id: str, radio: bool = False, extend: bool = True) -> Optional[dict]:
        """Match a channel name/id against PVR channels, optionally extending with broadcast data."""
        self.log('[%s] matchChannel, chname = %s, radio = %s' % (id, chname, radio))
        cacheName     = 'matchChannel.%s' % (FileAccess._getMD5('%s.%s.%s.%s' % (chname, id, radio, extend)))
        cacheResponse = (self.cache.get(cacheName, checksum=ADDON_VERSION) or {})
        if cacheResponse: return cacheResponse
            
        pvrItem  = None
        channels = self.getPVRChannels(radio)
        for channel in channels:
            if channel.get('label', '').lower() == chname.lower():
                for key in ('broadcastnow', 'broadcastnext'):
                    b_info = channel.get(key)
                    if b_info and _globals()._decodePlot(b_info.get('plot', '')).get('citem', {}).get('id') == id:
                        channel['broadcastnext'] = [channel.get('broadcastnext', {})]
                        self.log('[%s] matchChannel: __match, found pvritem' % id)
                        pvrItem = channel
                        break
            if pvrItem: break

        if pvrItem and extend:
            channel_id    = pvrItem.get('channelid')
            broadcasts    = self.getPVRBroadcasts(channel_id) if channel_id else []
            broadcastpast = []
            broadcastnext = []
            broadcastnow = None
            for b in broadcasts:
                prog = b.get('progresspercentage', 0)
                if prog == 100:      broadcastpast.append(b)
                elif 0 < prog < 100: broadcastnow = b
                elif prog == 0:      broadcastnext.append(b)

            if broadcastpast:
                broadcastpast.sort(key=itemgetter('starttime'))
                pvrItem['broadcastpast'] = broadcastpast
            if broadcastnext:
                broadcastnext.sort(key=itemgetter('starttime'))
                pvrItem['broadcastnext'] = broadcastnext
            elif 'broadcastnext' in pvrItem: pass 
            self.log('matchChannel: __extend, broadcastnext = %s entries' % len(pvrItem.get('broadcastnext', [])))
        self.cache.set(cacheName, pvrItem, checksum=ADDON_VERSION, expiration=datetime.timedelta(seconds=15))
        return pvrItem
        
        
    def getNextItem(self, citem: Optional[dict] = None, nitem: Optional[dict] = None) -> dict:
        if citem is None: citem = {}
        if nitem is None: nitem = {}
        if not _globals()._isFiller(nitem): return nitem
            
        n_id = _globals()._decodePlot(nitem.get('plot', '')).get('id')
        next_items = self.matchChannel(citem.get('name', ''), citem.get('id', ''), citem.get('radio', False)).get('broadcastnext', [])
        found_idx = -1
        for i, item in enumerate(next_items):
            fitem = _globals()._decodePlot(item.get('plot', ''))
            if fitem.get('start') == nitem.get('start') and fitem.get('id') == n_id:
                found_idx = i
                break
                
        if found_idx != -1:
            for i in range(found_idx, len(next_items)):
                candidate = next_items[i]
                if not _globals()._isFiller(candidate):
                    return _globals()._decodePlot(candidate.get('plot', ''))
        return {}
        


    def toggleShowLog(self, state: bool = False):
        self.log('toggleShowLog, state = %s'%(state))
        if self.getSettingValue("debug.showloginfo") != state:
            self.setSettingValue("debug.showloginfo",state,queue=False)


    def addTrailer(self, item: dict) -> Optional[bool]:
        if   'movieid' in item: key = 'movies'
        elif 'tvshowid'in item: key = 'tvshows'
        else: return
        fitem = item.copy()
        dur = self.getDuration(fitem.get('trailer'), accurate=bool(int(REAL_SETTINGS.getSetting('Duration_Type') or "0")), save=False)
        if dur > 0:
            trailers = self.getTrailers()
            if 'streamdetails' in fitem: fitem.pop('streamdetails')
            fitem.update({'label':'%s - %s'%(fitem.get("label",""),LANGUAGE(30187)),
                         'episodetitle':'%s - %s'%(fitem.get("episodetitle",""),LANGUAGE(30187)),
                         'episodelabel':'%s - %s'%(fitem.get("episodelabel",""),LANGUAGE(30187)),
                         'duration':dur, 
                         'file':fitem.get('trailer'),
                         'added':time.time()})#todo remove old entries.
            self.log(f'addTrailer [{key}] {fitem.get('duration',0)}, {fitem.get('file')}')
            for genre in (fitem.get('genre',[]) or ['resources']):
                if fitem not in trailers.setdefault(key,{}).setdefault(genre.lower(),[]):
                    trailers.setdefault(key,{}).setdefault(genre.lower(),[]).append(fitem)
            return self.setTrailers(trailers)
                
                
    def setTrailers(self, trailers: Optional[dict] = None) -> bool:
        if trailers is None: trailers = {'movies':{},'tvshows':{}}
        self.log(f'setTrailers [Movies] = {len(trailers.get('movies',{}))}')
        self.log(f'setTrailers [TVShows] = {len(trailers.get('tvshows',{}))}')
        return self.cache.set('trailers', trailers, expiration=datetime.timedelta(days=365))
                                
                        
    def getTrailers(self, genre: Optional[str] = None) -> Any:
        #todo clean old trailers by "added" epoch
        trailers = self.cache.get('trailers') or {'movies':{},'tvshows':{}}
        self.log(f'getTrailers [Movies] = {len(trailers.get('movies',{}))}')
        self.log(f'getTrailers [TVShows] = {len(trailers.get('tvshows',{}))}')
        if not genre is None: return trailers.get(genre,[])
        return trailers #return all
        
        
        