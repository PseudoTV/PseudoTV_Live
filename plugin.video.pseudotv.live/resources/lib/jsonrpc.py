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

from globals     import *
from videoparser import VideoParser

class Service(object):
    player  = PLAYER()
    monitor = MONITOR()
    def _shutdown(self, wait=CPU_CYCLE) -> bool:
        return PROPERTIES.isPendingShutdown() or self.monitor.waitForAbort(wait)
    def _restart(self) -> bool:
        return PROPERTIES.isPendingRestart()
    def _interrupt(self) -> bool:
        return any([PROPERTIES.isPendingInterrupt(),self._shutdown(),self._restart(),BUILTIN.isScanning()])
    def _suspend(self) -> bool:
        return any([PROPERTIES.isPendingSuspend(),BUILTIN.isSettingsOpened()])
    def _sleep(self, wait=CPU_CYCLE):
        while not self.monitor.abortRequested() and wait > 0:
            if any([self.monitor.waitForAbort(CPU_CYCLE),self._interrupt()]): return True
            else: wait -= CPU_CYCLE
        return False
    
    
class JSONRPC(object):
    cache       = SETTINGS.cache
    videoParser = VideoParser()
    
    def __init__(self, service=None):
        if service is None: service = Service()
        self.service = service


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)


    def requestURL(self, url, params={}, payload={}, header=HEADER, timeout=15, file=None, life=datetime.timedelta(minutes=15)):
        def __error(result={}): return result
        def __getCache():       return (self.cache.get('requestURL.%s'%(FileAccess._getMD5((url,params,payload,file)))) or {})
        def __setCache():       return self.cache.set('requestURL.%s'%(FileAccess._getMD5((url,params,payload,file))), results, expiration=life)
        def __setQueue(): 
            if hasattr(self.service,'postQue'): 
                self.service.postQue.add((url, params, payload, header, timeout, file, life))
            
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
            else:                                  results = response.content
            self.log("requestURL\nurl = %s, status = %s\nparams = %s\npayload = %s\nreturn type = %s"%(url,response.status_code,params,payload,type(results)))
            if results: return __setCache()
        except Exception as e: 
            self.log("requestURL, failed! %s"%(e))
            __getCache()
        finally: #retry failed post
            if results is None and payload: __setQueue()
        return results 
        

    def sendJSON(self, param):
        command = param
        command["jsonrpc"] = "2.0"
        command["id"] = ADDON_ID
        response = FileAccess.loadJSON(BUILTIN.executeJSONRPC(FileAccess.dumpJSON(command)))
        self.service.monitor.waitForAbort(float(SETTINGS.getSettingInt('RPC_Delay')))
        if response and response.get('error'):
            self.log('sendJSON, failed! error = %s\n%s'%(response.get('error',{}).get('message',LANGUAGE(30079)),param), xbmc.LOGWARNING)
            response.setdefault('result',{})['error'] = response.pop('error') #move to result for processing in builder.
        return response


    def sendRPC(self, param):
        #slower rpc, with proper timeout (killit) control via socket, internal rpc request requires thread killit which is hit or miss.
        command = param
        command["jsonrpc"] = "2.0"
        command["id"] = ADDON_ID
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(float(SETTINGS.getSettingInt('RPC_Wait'))) # This is the critical line
            sock.connect((SETTINGS.getIP(), 9090))
            sock.sendall(command.encode(DEFAULT_ENCODING))
            response = sock.recv(4096)
            self.service.monitor.waitForAbort(float(SETTINGS.getSettingInt('RPC_Delay')))
            return FileAccess.loadJSON(response.decode(DEFAULT_ENCODING))
        except socket.timeout:
            self.log("sendRPC, JSONRPC Timed out!", xbmc.LOGERROR)
            return None
        finally:
            sock.close()


    def queueJSON(self, param):
        if hasattr(self.service,'jsonQue'): self.service.jsonQue.add(param)
        
        
    def cacheJSON(self, param, life=datetime.timedelta(minutes=5), checksum=ADDON_VERSION):
        cacheName = 'cacheJSON.%s'%(FileAccess._getMD5(FileAccess.dumpJSON(param)))
        cacheResponse = self.cache.get(cacheName, checksum=checksum)
        if not cacheResponse:
            cacheResponse = self.sendJSON(param)
            if cacheResponse.get('result',{}): self.cache.set(cacheName, cacheResponse, checksum=checksum, expiration=life)
        return cacheResponse


    def walkFileDirectory(self, path, media='video', limit=None, depth=None, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15), dir={'label':'resources'}):
        if depth is None: depth = SETTINGS.getSettingInt('Recursive_Depth')
        if limit is None: limit = CHANNEL_LIMIT * depth
        walk = {}
        walk_depth = depth
        subs = []
        self.log('walkFileDirectory, walking %s, limit = %s, depth = %s'%(path,limit,depth))
        items, limits, errors = self.getDirectory({"directory":path,"media":media},True,checksum,expiration)
        for item in items:
            if self.service._interrupt(): break
            elif item.get('filetype') == 'file' and limit > 0:
                limit -= 1
                accurate = bool(SETTINGS.getSettingInt('Duration_Type'))
                item['duration'] = self.getDuration(item.get('file'),item,accurate)
                walk.setdefault(dir.get('label','root'),[]).append(item)
            elif item.get('filetype') == 'directory' and walk_depth > 0:
                walk_depth -= 1
                subs.append(item)
        [walk.update(self.walkFileDirectory(sub.get('file'), media, limit, depth, checksum, expiration, dir=sub)) for sub in subs if sub.get('file') and limit > 0 and not self.service._sleep(CPU_CYCLE)]
        self.log('walkFileDirectory, walking finished')
        return walk
                

    def walkListDirectory(self, path, exts=[], depth=None, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        if depth is None: depth = SETTINGS.getSettingInt('Recursive_Depth')
        def __(path, f):
            if exts and f.lower().endswith(tuple(exts)): return
            return {'label': os.path.basename(path.rstrip('/')),
                    'filetype': 'file',
                    'title': path,
                    'file': os.path.join(path,f),
                    'duration':self.getDuration(os.path.join(path,f), accurate=bool(SETTINGS.getSettingInt('Duration_Type')))}
        walk = {}
        path = path.replace('\\','/')
        subs, files = self.getListDirectory(path,checksum,expiration)
        self.log('walkListDirectory, walking %s, found = (%s,%s), depth = %s, append = %s'%(path,len(subs),len(files),depth,append))
        items = [__(path, _f) for _f in files if _f]
        if items: walk.setdefault(path,[]).extend([_i for _i in items if _i])
        for sub in subs:
            if depth <= 0: break
            depth -= 1
            walk.update(self.walkListDirectory(os.path.join(path,sub), exts, depth, checksum, expiration))
        return walk
                
          
    def getListDirectory(self, path, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
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


    def getIntrospect(self, id):
        param = {"method":"JSONRPC.Introspect","params":{"filter":{"id":id,"type":"method"}}}
        return self.cacheJSON(param,datetime.timedelta(days=28),BUILTIN.getInfoLabel('System.BuildVersion')).get('result',{})


    def getEnums(self, id, type='', key='enums'):
        self.log('getEnums id = %s, type = %s, key = %s' % (id, type, key))
        param = {"method":"JSONRPC.Introspect","params":{"getmetadata":True,"filterbytransport":True,"filter":{"getreferences":False,"id":id,"type":"type"}}}
        json_response = self.cacheJSON(param,datetime.timedelta(days=28),BUILTIN.getInfoLabel('System.BuildVersion')).get('result',{}).get('types',{}).get(id,{})
        return (json_response.get('properties',{}).get(type,{}).get(key) or json_response.get(type,{}).get(key) or json_response.get(key,[]))


    def notifyAll(self, message, data, sender=ADDON_ID):
        param = {"method":"JSONRPC.NotifyAll","params":{"sender":sender,"message":message,"data":[data]}}
        return self.sendJSON(param).get('result') == 'OK'


    def playerOpen(self, params={}):
        param = {"method":"Player.Open","params":params}
        return self.sendJSON(param).get('result') == 'OK'


    def getSetting(self, category, section, cache=False):
        param = {"method":"Settings.GetSettings","params":{"filter":{"category":category,"section":section}}}
        if cache: return self.cacheJSON(param).get('result',{}).get('settings',[])
        else:     return self.sendJSON(param).get('result',{}).get('settings',[])


    def getSettingValue(self, key, default='', cache=False):
        param = {"method":"Settings.GetSettingValue","params":{"setting":key}}
        if cache: return (self.cacheJSON(param).get('result',{}).get('value') or default)
        else:     return (self.sendJSON(param).get('result',{}).get('value')  or default)


    def setSettingValue(self, key, value, queue=False):
        param = {"method":"Settings.SetSettingValue","params":{"setting":key,"value":value}}
        if queue: self.queueJSON(param)
        else:     self.sendJSON(param)


    def getSources(self, media='video', cache=True):
        param = {"method":"Files.GetSources","params":{"media":media}}
        if cache: return self.cacheJSON(param).get('result',{}).get('sources', [])
        else:     return self.sendJSON(param).get('result',{}).get('sources', [])


    def getAddonDetails(self, addonid=ADDON_ID, cache=True):
        param = {"method":"Addons.GetAddonDetails","params":{"addonid":addonid,"properties":self.getEnums("Addon.Fields", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('addon', {})
        else:     return self.sendJSON(param).get('result',{}).get('addon', {})


    def getAddons(self, param={"content":"video","enabled":True,"installed":True}, cache=True):
        param["properties"] = self.getEnums("Addon.Fields", type='items')
        param = {"method":"Addons.GetAddons","params":param}
        if cache: return self.cacheJSON(param).get('result',{}).get('addons', [])
        else:     return self.sendJSON(param).get('result',{}).get('addons', [])


    def getSongs(self, cache=True):
        param = {"method":"AudioLibrary.GetSongs","params":{"properties":self.getEnums("Audio.Fields.Song", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('songs', [])
        else:     return self.sendJSON(param).get('result',{}).get('songs', [])


    def getArtists(self, cache=True):
        param = {"method":"AudioLibrary.GetArtists","params":{"properties":self.getEnums("Audio.Fields.Artist", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('artists', [])
        else:     return self.sendJSON(param).get('result',{}).get('artists', [])


    def getAlbums(self, cache=True):
        param = {"method":"AudioLibrary.GetAlbums","params":{"properties":self.getEnums("Audio.Fields.Album", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('albums', [])
        else:     return self.sendJSON(param).get('result',{}).get('albums', [])

     
    def getEpisode(self, tvshowid, season, episode=None, cache=True):
        if not episode is None: filter = {"field":"episode","operator":"is","value":str(episode)}
        else:                   filter = {}
        param = {"method":"VideoLibrary.GetEpisodes","params":{"tvshowid":tvshowid,"season":season,"properties":self.getEnums("Video.Fields.Episode", type='items'),"filter":filter}}
        if cache: return self.cacheJSON(param).get('result',{}).get('episodes', [])
        else:     return self.sendJSON(param).get('result',{}).get('episodes', [])
  
  
    def getEpisodes(self, cache=True):
        param = {"method":"VideoLibrary.GetEpisodes","params":{"properties":self.getEnums("Video.Fields.Episode", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('episodes', [])
        else:     return self.sendJSON(param).get('result',{}).get('episodes', [])


    def getTVshows(self, cache=True):
        param = {"method":"VideoLibrary.GetTVShows","params":{"properties":self.getEnums("Video.Fields.TVShow", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('tvshows', [])
        else:     return self.sendJSON(param).get('result',{}).get('tvshows', [])


    def getMovie(self, uniqueid, title, year, cache=True):
        param = {"method":"VideoLibrary.GetMovies","params":{"properties":self.getEnums("Video.Fields.Movie", type='items'),"filter":{"and":[{"field":"title","operator":"is","value":title},{"field":"year","operator":"is","value":str(year)}]}}}
        if cache: return self.cacheJSON(param).get('result',{}).get('movies', [])
        else:     return self.sendJSON(param).get('result',{}).get('movies', [])


    def getMovies(self, cache=True):
        param = {"method":"VideoLibrary.GetMovies","params":{"properties":self.getEnums("Video.Fields.Movie", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('movies', [])
        else:     return self.sendJSON(param).get('result',{}).get('movies', [])


    def getVideoGenres(self, type="movie", cache=True): #type = "movie"/"tvshow"
        param = {"method":"VideoLibrary.GetGenres","params":{"type":type,"properties":self.getEnums("Library.Fields.Genre", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('genres', [])
        else:     return self.sendJSON(param).get('result',{}).get('genres', [])


    def getMusicGenres(self, cache=True):
        param = {"method":"AudioLibrary.GetGenres","params":{"properties":self.getEnums("Library.Fields.Genre", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('genres', [])
        else:     return self.sendJSON(param).get('result',{}).get('genres', [])


    def getTextures(self, cache=True):
        param = {"method":"Textures.GetTextures","params":{"properties":self.getEnums("Textures.Fields.Texture", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('textures', [])
        else:     return self.sendJSON(param).get('result',{}).get('textures', [])
            
        
    def getDirectory(self, param={}, cache=True, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        param["properties"] = self.getEnums("List.Fields.Files", type='items') #todo change enums from files to media specific? 
        param = {"method":"Files.GetDirectory","params":param}
        if cache: results = self.cacheJSON(param, expiration, checksum).get('result',{})
        else:     results = self.sendJSON(param).get('result',{})
        if 'filedetails' in results: return results.get('filedetails',[]), results.get('limits',{}), results.get('error',{})
        else:                        return results.get('files',[]), results.get('limits',{}), results.get('error',{})


    def getLibrary(self, method, param={}, key=None, cache=True):
        param = {"method":method,"params":param}
        if cache: results = self.cacheJSON(param).get('result',{})
        else:     results = self.sendJSON(param).get('result',{})
        return results.get((key or list(results.keys())[0]),[]), results.get('limits',{}), results.get('error',{})
        
        
    def getMPAA(self, type='movie', incItem=False):
        def __parse(items): 
            for item in items:
                yield {'label':cleanMPAA(item.get("mpaa","NR")),'item':item if incItem else {}}
        if   type == 'movie':  return list(__parse(self.getMovies()))
        elif type == 'tvshow': return list(__parse(self.getTVshows()))


    def getStreamDetails(self, path, media='video'):
        if isStack(path): path = splitStacks(path)[0]
        param = {"method":"Files.GetFileDetails","params":{"file":path,"media":media,"properties":["streamdetails"]}}
        return self.cacheJSON(param, life=datetime.timedelta(days=MAX_GUIDEDAYS), checksum=FileAccess._getMD5(path)).get('result',{}).get('filedetails',{}).get('streamdetails',{})


    def getFileDetails(self, file, media='video', properties=["duration","runtime"]):
        return self.cacheJSON({"method":"Files.GetFileDetails","params":{"file":file,"media":media,"properties":properties}})


    def getViewMode(self):
        default = {"nonlinearstretch":False,"pixelratio":1,"verticalshift":0,"viewmode":"custom","zoom": 1.0}
        return self.cacheJSON({"method":"Player.GetViewMode","params":{}},datetime.timedelta(seconds=15)).get('result',default)
        

    def setViewMode(self, params={}):
        return self.sendJSON({"method":"Player.SetViewMode","params":params})


    def getPlayerItem(self, playlist=False):
        self.log('getPlayerItem, playlist = %s' % (playlist))
        if playlist: param = {"method":"Playlist.GetItems","params":{"playlistid":self.getActivePlaylist(),"properties":self.getEnums("List.Fields.All", type='items')}}
        else:        param = {"method":"Player.GetItem"   ,"params":{"playerid":self.getActivePlayer()    ,"properties":self.getEnums("List.Fields.All", type='items')}}
        result = self.sendJSON(param).get('result',{})
        return (result.get('item', {}) or result.get('items', []))


    def getPVRClients(self):
        param = {"method":"PVR.GetClients","params":{}}
        return self.sendJSON(param).get('result',{}).get('clients',[])


    def getPVRClient(self, id=PVR_CLIENT_ID):
        results = self.getPVRClients()
        return next((result for result in results if result.get('addonid','').lower() == id.lower()),None)


    def getPVRChannelGroups(self, match=ADDON_NAME, radio=False):
        param   = {"method":"PVR.GetChannelGroups","params":{"channeltype":{True:'radio',False:'tv'}[radio]}}
        results = self.sendJSON(param).get('result',{}).get('channelgroups', [])
        if match is None: return results
        return next((result for result in results if result.get('label').lower() == match.lower()), None)

        
    def getPVRChannelGroupDetails(self, id):
        param = {"method":"PVR.GetChannelGroupDetails","params":{"channelgroupid":1,"channels":{"limits":{"end":0,"start":0},"properties":self.getEnums("PVR.Fields.Channel", type='items')}}}
        return self.sendJSON(param).get('result',{}).get('channelgroupdetails', {}).get('channels',[])
        

    def PVRScan(self, id):
        param = {"method":"PVR.Scan","params":{"clientid":id}}
        return self.sendJSON(param).get('result',{})
        
        
    def getPVRChannels(self, radio=False):
        param = {"method":"PVR.GetChannels","params":{"channelgroupid":{True:'allradio',False:'alltv'}[radio],"properties":self.getEnums("PVR.Fields.Channel", type='items')}}
        return self.sendJSON(param).get('result',{}).get('channels', [])


    def getPVRChannelsDetails(self, id):
        param = {"method":"PVR.GetChannelDetails","params":{"channelid":id,"properties":self.getEnums("PVR.Fields.Channel", type='items')}}
        return self.sendJSON(param).get('result',{}).get('channels', [])


    def getPVRBroadcasts(self, id):
        param = {"method":"PVR.GetBroadcasts","params":{"channelid":id,"properties":self.getEnums("PVR.Fields.Broadcast", type='items')}}
        return self.sendJSON(param).get('result',{}).get('broadcasts', [])


    def getPVRBroadcastDetails(self, id):
        param = {"method":"PVR.GetBroadcastDetails","params":{"broadcastid":id,"properties":self.getEnums("PVR.Fields.Broadcast", type='items')}}
        return self.sendJSON(param).get('result',{}).get('broadcastdetails', [])


    def getPVRRecordings(self, media='video', cache=True):
        param = {"method":"Files.GetDirectory","params":{"directory":"pvr://recordings/tv/active/","media":media,"properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('files', [])
        else:     return self.sendJSON(param).get('result',{}).get('files', [])

    
    def getPVRSearches(self, media='video', cache=True):
        param = {"method":"Files.GetDirectory","params":{"directory":"pvr://search/tv/savedsearches/","media":media,"properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('files', [])
        else:     return self.sendJSON(param).get('result',{}).get('files', [])
        
        
    def getPVRSearchItems(self, id, media='video', cache=True):
        param = {"method":"Files.GetDirectory","params":{"directory":f"pvr://search/tv/savedsearches/{id}/","media":media,"properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('files', [])
        else:     return self.sendJSON(param).get('result',{}).get('files', [])
    
    
    def getSmartPlaylists(self, type='video', cache=True):
        param = {"method":"Files.GetDirectory","params":{"directory":f"special://profile/playlists/{type}/","media":"video","properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result',{}).get('files', [])
        else:     return self.sendJSON(param).get('result',{}).get('files', [])
        
        
    def getInfoLabel(self, key, cache=False):
        param = {"method":"XBMC.GetInfoLabels","params":{"labels":[key]}}
        if cache: return self.cacheJSON(param).get('result',{}).get(key)
        else:     return self.sendJSON(param).get('result',{}).get(key)


    def getInfoBool(self, key, cache=False):
        param = {"method":"XBMC.GetInfoBooleans","params":{"booleans":[key]}}
        if cache: return self.cacheJSON(param).get('result',{}).get(key)
        else:     return self.sendJSON(param).get('result',{}).get(key)
    
    
    def DBIDtoLabel(self, path):
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
        
        
    def _setRuntime(self, item={}, runtime=0, save=SETTINGS.getSettingBool('Store_Duration')): #set runtime collected by player, accurate meta.
        runtime = round(runtime)
        self.cache.set('getRuntime.%s'%(FileAccess._getMD5(item.get('file'))), runtime, checksum=FileAccess._getMD5(item.get('file')), expiration=datetime.timedelta(days=28))
        if not item.get('file','plugin://').startswith(tuple(VFS_TYPES)) and save and runtime > 0: self.queDuration(item, runtime=runtime)
    
        
    def _getRuntime(self, item={}): #get runtime collected by player, else less accurate provider meta
        runtime = self.cache.get('getRuntime.%s'%(FileAccess._getMD5(item.get('file'))), checksum=FileAccess._getMD5(item.get('file')))
        return round(runtime or item.get('resume',{}).get('total') or item.get('runtime') or item.get('duration') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration') or 0)
        

    def _setDuration(self, path, item={}, duration=0, save=SETTINGS.getSettingBool('Store_Duration')):#set VideoParser cache
        duration = round(duration)
        self.cache.set('getDuration.%s'%(FileAccess._getMD5(path)), duration, checksum=FileAccess._getMD5(path), expiration=datetime.timedelta(days=28))
        if save and item: self.queDuration(item, duration)
        return duration

    
    def _getDuration(self, path): #get VideoParser cache
        return round(self.cache.get('getDuration.%s'%(FileAccess._getMD5(path)), checksum=FileAccess._getMD5(path)) or self._getRuntime({'file':path}))


    def getDuration(self, path, item={}, accurate=bool(SETTINGS.getSettingInt('Duration_Type')), save=SETTINGS.getSettingBool('Store_Duration')): 
        def __parseDuration(runtime, path, item={}, save=SETTINGS.getSettingBool('Store_Duration')):
            duration = self.videoParser.getVideoLength(path.replace("\\\\", "\\"), item, self)
            if   runtime == 0: runtime = duration
            elif round(percentDiff(runtime, duration)) <= RUNTIME_THRESHOLD: runtime = duration
            if save and duration != runtime: self.queDuration(item, runtime)
            return runtime
            
        if not item: item = {'file':path}
        runtime = self._getRuntime(item) #player runtime, fallback meta provider runtime
        if runtime == 0 or accurate:
            duration = 0
            if isStack(path):# handle "stacked" videos
                for file in splitStacks(path): duration += __parseDuration(runtime, file)
            else: duration = __parseDuration(runtime, path, item, save)
            if duration > 0: runtime = duration
        self.log(f"getDuration [{runtime}], {path}, accurate = {accurate}, save ={save}")
        return runtime


    def getTotDuration(self, items=[], accurate=bool(SETTINGS.getSettingInt('Duration_Type'))):
        total = sum((self.getDuration(item.get('file'),item,accurate) for item in items))
        self.log("getTotDuration, items = %s, total = %s" % (len(items), total))
        return total


    def queDuration(self, item={}, duration=0, runtime=0):
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
                if mtype.get('params'):
                    if   duration == 0: mtype['params'].pop('resume')  #save file duration meta
                    elif runtime  == 0: mtype['params'].pop('runtime') #save player runtime meta
                    id = (item.get('id') or item.get('movieid') or item.get('episodeid') or item.get('musicvideoid') or item.get('songid'))
                    self.log('[%s] queDuration, media = %s, duration = %s, runtime = %s'%(id,item['type'],duration,runtime))
                    self.queueJSON(mtype['params'])
            except Exception as e: self.log("queDuration, failed! %s\nmtype = %s\nitem = %s"%(e,mtype,item), xbmc.LOGERROR)
        
        
    def quePlaycount(self, item={}, save=SETTINGS.getSettingBool('Rollback_Watched')):
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
                if hasattr(self.service,'_que'): self.service._que(self.sendJSON,1,0,0,params)
            except Exception: pass


    def requestList(self, citem, path, media='video', page=SETTINGS.getSettingInt('Page_Limit'), sort={}, filter={}, limits={}, query={}):
         # Query
         # {"method": "VideoLibrary.GetEpisodes",
         # "params": {
         # "properties": ["title"],
         # "sort": {"ignorearticle": true,
                  # "method": "label",
                  # "order": "ascending",
                  # "useartistsortname": true},
         # "limits": {"end": 0, "start": 0},
         # "filter": {"and": [{"field": "title", "operator": "contains", "value": "Star Wars"}]}}}

         ##################################
         # VFS Path
         # {"method": "Files.GetDirectory",
         # "params": {
         # "directory": "videodb://tvshows/studios/-1/-1/-1/",
         # "media": "video",
         # "properties": ["title"],
         # "sort": {"ignorearticle": true,
                  # "method": "label",
                  # "order": "ascending",
                  # "useartistsortname": true},
         # "limits": {"end": 25, "start": 0}}}
         
        param = {}
        if query: #library query
            getDirectory = False
            param['filter']     = query.get('filter',{})
            param["properties"] = self.getEnums(query['enum'], type='items')
        else: #vfs path
            getDirectory = True
            param["media"]      = media
            param["directory"]  = path#escapeDirJSON(path)
            param["properties"] = self.getEnums("List.Fields.Files", type='items')
        self.log("requestList, id: %s, getDirectory = %s, media = %s, limit = %s, sort = %s, query = %s, limits = %s\npath = %s"%(citem['id'],getDirectory,media,page,sort,query,limits,path))
        
        if limits.get('end',-1) == -1: #-1 unlimited, replace with autoPagination.
            limits = self.autoPagination(citem['id'], path, query) #get
            self.log('[%s] requestList, autoPagination limits = %s'%(citem['id'],limits))
            if limits.get('total',0) > page and sort.get("method","") == "random":
                limits = self.randomPagination(page,limits)
                self.log('[%s] requestList, generating random limits = %s'%(citem['id'],limits))

        if limits.get('start',0) >= 0: #-1 unlimited, ignore autoPagination.
            param["limits"] = {}
            param["limits"]["start"] = 0 if limits.get('end', 0) == -1 else limits.get('end', 0)
            param["limits"]["end"]   = abs(limits.get('end', 0) + page)
        
        param["sort"] = sort
        self.log('[%s] requestList, page = %s\nparam = %s'%(citem['id'], page, param))
        
        with self.detectRPCCrash(citem):
            if getDirectory: items, limits, errors = self.getDirectory(param)
            else:            items, limits, errors = self.getLibrary(query['method'],param,query.get('key'),cache=False)

        if (limits.get('end',0) >= limits.get('total',0) or limits.get('start',0) >= limits.get('total',0)):
            # restart page to 0, exceeding boundaries.
            self.log('[%s] requestList, resetting limits to 0'%(citem['id']))
            limits = {"end": 0, "start": 0, "total": limits.get('total',0)}
          
        if len(items) == 0 and limits.get('total',0) > 0:
            # retry last request with fresh limits when no items are returned.
            self.log("[%s] requestList, trying again with start limits at 0"%(citem['id']))
            return self.requestList(citem, path, media, page, sort, filter, {"end": 0, "start": 0, "total": limits.get('total',0)}, query)
        else:          
            self.autoPagination(citem['id'], path, query, limits) #set 
            self.log("[%s] requestList, return items = %s" % (citem['id'], len(items)))
            return items, limits, errors


    def resetPagination(self, id, path, query={}, limits={"end": 0, "start": 0, "total":0}):
        return self.autoPagination(id, path, query, limits)
            
            
    def autoPagination(self, id, path, query={}, limits={}):
        if not limits: return (self.cache.get('autoPagination.%s.%s.%s'%(id,FileAccess._getMD5(path),FileAccess._getMD5(FileAccess.dumpJSON(query))), checksum=id) or {"end": 0, "start": 0, "total":0})
        else:          return  self.cache.set('autoPagination.%s.%s.%s'%(id,FileAccess._getMD5(path),FileAccess._getMD5(FileAccess.dumpJSON(query))), limits, checksum=id, expiration=datetime.timedelta(days=28))
            
             
    def randomPagination(self, page=SETTINGS.getSettingInt('Page_Limit'), limits={}, start=0):
        if limits.get('total',0) > page: start = random.randrange(0, (limits.get('total',0)-page), page)
        return {"end": start, "start": start, "total":limits.get('total',0)}
        

    @contextmanager
    def detectRPCCrash(self, citem):
        SETTINGS.setCacheSetting('KODI.CRASH.JSONRPC.CITEM',citem)
        try: yield
        except Exception:pass
        finally:
            SETTINGS.setCacheSetting('KODI.CRASH.JSONRPC.CITEM',None)


    def getLocalHost(self, local=False):
        port     = 80
        username = 'kodi'
        password = ''
        secure   = False
        enabled  = True
        settings = self.getSetting('control','services',cache=True)
        for setting in settings:
            if setting.get('id','').lower() == 'services.webserver' and not setting.get('value'):
                enabled = False
                DIALOG.notificationDialog(LANGUAGE(32131))
                break
            if   setting.get('id','').lower() == 'services.webserverusername': username = setting.get('value')
            elif setting.get('id','').lower() == 'services.webserverport':     port     = setting.get('value')
            elif setting.get('id','').lower() == 'services.webserverpassword': password = setting.get('value')
            elif setting.get('id','').lower() == 'services.webserverssl' and setting.get('value'): secure = True
        username = '{0}:{1}@'.format(username, password) if username and password else ''
        protocol = 'https' if secure else 'http'
        if local: ip = 'localhost'
        else:     ip = SETTINGS.getIP()
        webURL =  '{0}://{1}{2}:{3}'.format(protocol,username,ip,port)
        self.log("getLocalHost; returning %s"%(webURL))
        return webURL


    def padItems(self, files, page=SETTINGS.getSettingInt('Page_Limit')):
        # Balance media limits, by filling with duplicates to meet min. pagination.
        self.log("padItems; files In = %s"%(len(files)))
        if len(files) < page:
            iters = cycle(files)
            while not self.service.monitor.abortRequested() and (len(files) < page and len(files) > 0):
                item = next(iters).copy()
                if   self.service._interrupt(): break
                elif self.getDuration(item.get('file'),item) == 0:
                    try: files.pop(files.index(item))
                    except Exception: break
                else: files.append(item)
        self.log("padItems; files Out = %s"%(len(files)))
        return files


    def inputFriendlyName(self):
        friendly = self.getSettingValue("services.devicename")
        self.log("inputFriendlyName, name = %s"%(friendly))
        if not friendly or friendly.lower() == 'kodi':
            if DIALOG.okDialog(LANGUAGE(32132)%(friendly)):
                with PROPERTIES.interruptActivity():
                    friendly = DIALOG.inputDialog(LANGUAGE(30122), friendly)
                if not friendly or friendly.lower() == 'kodi':
                    return self.inputFriendlyName()
                else:
                    self.setSettingValue("services.devicename",friendly,queue=False)
                    self.log('inputFriendlyName, setting device name = %s'%(friendly))
        return friendly
           
           
    def getCallback(self, sysInfo={}):
        self.log('[%s] getCallback, mode = %s, radio = %s, isPlaylist = %s'%(sysInfo.get('chid'),sysInfo.get('mode'),sysInfo.get('radio',False),sysInfo.get('isPlaylist',False)))
        def _matchJSON():#requires 'pvr://' json whitelisting
            results, limits, errors = self.getDirectory(param={"directory":"pvr://channels/{dir}/".format(dir={'True':'radio','False':'tv'}[str(sysInfo.get('radio',False))])}, cache=False)
            for dir in [ADDON_NAME,'All channels']: #todo "All channels" may not work with non-English translations!
                for result in results:
                    if result.get('label','').lower().startswith(dir.lower()):
                        self.log('getCallback: _matchJSON, found dir = %s'%(result.get('file')))
                        channels, limits, errors = self.getDirectory(param={"directory":result.get('file')},checksum=PROPERTIES.getProcessID(),expiration=datetime.timedelta(minutes=15))
                        for item in channels:
                            fitem = Globals._decodePlot(item.get('plot',''))
                            fitem_id = fitem.get('citem',{}).get('id')
                            if (fitem_id == sysInfo.get('chid') or fitem_id == sysInfo.get('citem',{}).get('id')):
                                self.log('[%s] getCallback: _matchJSON, found file = %s'%(sysInfo.get('chid'),item.get('file')))
                                return item.get('file')
   
        if sysInfo.get('mode','').lower() == 'live' and sysInfo.get('chpath'):
            callback = sysInfo.get('chpath')
        elif sysInfo.get('isPlaylist'):
            callback = sysInfo.get('citem',{}).get('url')
        elif sysInfo.get('mode','').lower() in ['vod','broadcast'] and sysInfo.get('nitem',{}).get('file'):
            callback = sysInfo.get('nitem',{}).get('file')
        else:
            callback = sysInfo.get('callback','')
        if not callback: callback = _matchJSON()
        self.log('getCallback: returning callback = %s'%(callback))
        return callback# or (('%s%s'%(self.sysARG[0],self.sysARG[2])).split('%s&'%(Globals._slugify(ADDON_NAME))))[0])
        
        
    def matchChannel(self, chname: str, id: str, radio: bool=False, extend=True):
        self.log('[%s] matchChannel, chname = %s, radio = %s'%(id,chname,radio))
        def __match():
            channels = self.getPVRChannels(radio)
            for channel in channels:
                if channel.get('label','').lower() == chname.lower():
                    for key in ['broadcastnow', 'broadcastnext']:
                        if Globals._decodePlot(channel.get(key,{}).get('plot','')).get('citem',{}).get('id') == id:
                            channel['broadcastnext'] = [channel.get('broadcastnext',{})]
                            self.log('[%s] matchChannel: __match, found pvritem = %s'%(id,channel))
                            return channel
                            
        def __extend(pvritem: dict={}) -> dict:
            channelItem = {}
            def _parseBroadcast(broadcast={}):
                if broadcast.get('progresspercentage',0) == 100:
                    channelItem.setdefault('broadcastpast',[]).append(broadcast)
                elif broadcast.get('progresspercentage',0) > 0 and broadcast.get('progresspercentage',100) < 100:
                    channelItem['broadcastnow'] = broadcast
                elif broadcast.get('progresspercentage',0) == 0 and broadcast.get('progresspercentage',100) < 100:
                    channelItem.setdefault('broadcastnext',[]).append(broadcast)
                    
            broadcasts = self.getPVRBroadcasts(pvritem.get('channelid',{}))
            [_parseBroadcast(broadcast) for broadcast in broadcasts]
            try:    pvritem['broadcastpast'] = sorted(channelItem.get('broadcastpast',[]), key=itemgetter('starttime'))
            except Exception: pvritem['broadcastpast'] = channelItem.get('broadcastpast',[])
            try:    pvritem['broadcastnext'] = sorted(channelItem.get('broadcastnext',pvritem['broadcastnext']), key=itemgetter('starttime'))
            except Exception: pvritem['broadcastnext'] = channelItem.get('broadcastnext',pvritem['broadcastnext'])
            self.log('matchChannel: __extend, broadcastnext = %s entries'%(len(pvritem['broadcastnext'])))
            return pvritem
            
        cacheName     = 'matchChannel.%s'%(FileAccess._getMD5('%s.%s.%s.%s'%(chname,id,radio,extend)))
        cacheResponse = (self.cache.get(cacheName, checksum=PROPERTIES.getProcessID()) or {})
        if not cacheResponse:
            pvrItem = __match()
            if pvrItem and extend: pvrItem = __extend(pvrItem)
            cacheResponse = self.cache.set(cacheName, pvrItem, checksum=PROPERTIES.getProcessID(), expiration=datetime.timedelta(seconds=15))
        return cacheResponse
        
        
    def getNextItem(self, citem={}, nitem={}): #return next broadcast ignoring fillers
        def __matchItem(nitem, nextitems):
            for idx, nextitem in enumerate(nextitems):
                fitem = Globals._decodePlot(nextitem.get('plot',''))
                if fitem.get('start') == nitem.get('start',str(random.random())) and fitem.get('id') == fitem.get('id',random.random()):
                    return nextitems[idx:]
            return []
            
        if not isFiller(nitem): return nitem
        broadcastnext = __matchItem(nitem, self.matchChannel(citem.get('name',''), citem.get('id',''), citem.get('radio',False)).get('broadcastnext',[]))
        for next in broadcastnext:
            if not isFiller(next): return Globals._decodePlot(next.get('plot',''))
        return {}
        

    def toggleShowLog(self, state=False):
        self.log('toggleShowLog, state = %s'%(state))
        if self.getSettingValue("debug.showloginfo") != state:
            self.setSettingValue("debug.showloginfo",state,queue=False)


    def addTrailer(self, item):
        if   'movieid' in item: key = 'movies'
        elif 'tvshowid'in item: key = 'tvshows'
        else: return
        fitem = item.copy()
        dur = self.getDuration(fitem.get('trailer'), accurate=bool(SETTINGS.getSettingInt('Duration_Type')), save=False)
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
                
                
    def setTrailers(self, trailers={'movies':{},'tvshows':{}}):
        self.log(f'setTrailers [Movies] = {len(trailers.get('movies',{}))}')
        self.log(f'setTrailers [TVShows] = {len(trailers.get('tvshows',{}))}')
        return SETTINGS.setCacheSetting('trailers', trailers)
                                
                        
    def getTrailers(self, genre=None):
        #todo clean old trailers by "added" epoch
        trailers = SETTINGS.getCacheSetting('trailers', default={'movies':{},'tvshows':{}})
        self.log(f'getTrailers [Movies] = {len(trailers.get('movies',{}))}')
        self.log(f'getTrailers [TVShows] = {len(trailers.get('tvshows',{}))}')
        if not genre is None: return trailers.get(genre,[])
        return trailers #return all
        
        
        