#   Copyright (C) 2022 Lunatixz
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

MIN_DIR_PARAMS = ["title", "showtitle", "episode", "season", "runtime", "duration",
                  "streamdetails", "year", "plot", "plotoutline","description", 
                  "art", "writer", "cast", "rating", "genre", "director", "mpaa",
                  "premiered", "playcount", "studio"]

class JSONRPC:
    def __init__(self):
        self.cache       = Cache()
        self.videoParser = VideoParser()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)
    
    
    @contextmanager
    def sendLocker(self):
        if PROPERTIES.getPropertyBool('sendLocker'):
            while not MONITOR.abortRequested():
                if MONITOR.waitForAbort(0.5): break
                elif not PROPERTIES.getPropertyBool('sendLocker'): break
        PROPERTIES.setPropertyBool('sendLocker',True)
        try: yield
        finally:
            PROPERTIES.setPropertyBool('sendLocker',False)


    def _sendJSON(self, command):
        self.log('_sendJSON, command = %s'%(command))
        results = loadJSON(xbmc.executeJSONRPC(dumpJSON(command)))
        if not BUILTIN.getInfoBool('Platform.Windows','System'):
            xbmc.sleep(SETTINGS.getSettingInt('JSONRPC_Delay')) #overcome overflow issue within Kodi JSONRPC. Windows Platform unaffected. Kodi will segfault when flooded with json requests.
        return results


    def sendJSON(self, param, timeout=15): #todo dynamic timeout based on parmas and timeout history.
        with self.sendLocker():
            self.log('sendJSON, timeout = %s'%(timeout))
            command = param
            command["jsonrpc"] = "2.0"
            command["id"] = ADDON_ID
            # response = killJSON(self._sendJSON)(timeout, command)
            response = self._sendJSON(command)
            if response.get('error'):
                self.log('sendJSON, failed! error = %s\n%s'%(dumpJSON(response.get('error')),command), xbmc.LOGWARNING)
                
        if response.get('error',{}).get('message','').startswith('JSONRPC timed out!'):
            if   timeout <= 15: return self.sendJSON(param, timeout=30)
            elif timeout >= 30: return self.queueJSON(param)
        return response


    def queueJSON(self, param):
        queuePool = SETTINGS.getCacheSetting('queuePool', json_data=True, default={})
        params = queuePool.setdefault('params',[])
        params.append(param)
        queuePool['params'] = setDictLST(params)
        self.log("queueJSON, queueing = %s"%(len(queuePool['params'])))
        SETTINGS.setCacheSetting('queuePool', queuePool, json_data=True)

        
    def cacheJSON(self, param, life=datetime.timedelta(minutes=15), checksum=ADDON_VERSION, timeout=15):
        cacheName = 'cacheJSON.%s'%(getMD5(dumpJSON(param)))
        cacheResponse = self.cache.get(cacheName, checksum=checksum, json_data=True)
        if not cacheResponse:
            cacheResponse = self.sendJSON(param,timeout)
            if cacheResponse.get('result',{}):
                self.cache.set(cacheName, cacheResponse, checksum=checksum, expiration=life, json_data=True)
        return cacheResponse


    def walkListDirectory(self, path, depth=3, verify_runtime=False, append_path=False, checksum=ADDON_VERSION, expiration=datetime.timedelta(days=int(SETTINGS.getSetting('Max_Days')))):
        dirs  = [path]
        files = []
        for idx, dir in enumerate(dirs):
            if MONITOR.waitForAbort(0.5) or idx > depth: break
            ndirs, nfiles = self.getListDirectory(dir, checksum, expiration)
            if append_path:
                dirs.extend([os.path.join(path,dir) for dir in ndirs])
                files.extend([os.path.join(path,fle) for fle in nfiles])
            else:
                dirs.extend(ndirs)
                files.extend(nfiles)
            if verify_runtime:
                for file in files:
                    if self.getDuration(file): return True
        self.log('walkListDirectory, return dirs = %s, files = %s\npath = %s'%(len(dirs), len(files),path))
        return dirs, files

        
    def getListDirectory(self, path, checksum=ADDON_VERSION, expiration=datetime.timedelta(days=int(SETTINGS.getSetting('Max_Days')))):
        cacheName = 'getListDirectory.%s'%(getMD5(path))
        results   = self.cache.get(cacheName, checksum)
        if not results:
            try:    
                results = FileAccess.listdir(path)
                self.cache.set(cacheName, results, checksum, expiration)
                self.log('getListDirectory path = %s, checksum = %s'%(path, checksum))
            except: 
                results = [],[]
        self.log('getListDirectory return dirs = %s, files = %s\n%s'%(len(results[0]), len(results[1]),path))
        return results


    @cacheit(checksum=BUILTIN.getInfoLabel('BuildVersion','System'),expiration=datetime.timedelta(days=28),json_data=True)
    def getIntrospect(self, id):
        param = {"method":"JSONRPC.Introspect","params":{"filter":{"id":id,"type":"method"}}}
        return self.sendJSON(param).get('result',{})


    @cacheit(checksum=BUILTIN.getInfoLabel('BuildVersion','System'),expiration=datetime.timedelta(days=28),json_data=True)
    def getEnums(self, id, type=''):
        self.log('getEnums id = %s, type = %s' % (id, type))
        param = {"method":"JSONRPC.Introspect","params":{"getmetadata":True,"filterbytransport":True,"filter":{"getreferences":False,"id":id,"type":"type"}}}
        json_response = self.sendJSON(param).get('result',{}).get('types',{}).get(id,{})
        return (json_response.get(type,{}).get('enums',[]) or json_response.get('enums',[]))


    def notifyAll(self, message, data, sender=ADDON_ID):
        param = {"method":"JSONRPC.NotifyAll","params":{"sender":sender,"message":message,"data":[data]}}
        return self.sendJSON(param).get('result') == 'OK'


    def playerOpen(self, params={}):
        param = {"method":"Player.Open","params":params}
        return self.sendJSON(param).get('result') == 'OK'


    def getSetting(self, category, section, cache=False):
        param = {"method":"Settings.GetSettings","params":{"filter":{"category":category,"section":section}}}
        if cache: return self.cacheJSON(param).get('result',{}).get('settings',[])
        else:     return self.sendJSON(param).get('result', {}).get('settings',[])


    def getSettingValue(self, key, cache=False):
        param = {"method":"Settings.GetSettingValue","params":{"setting":key}}
        if cache: return self.cacheJSON(param).get('result',{}).get('value','')
        else:     return self.sendJSON(param).get('result',{}).get('value','')


    def setSettingValue(self, key, value):
        param = {"method":"Settings.SetSettingValue","params":{"setting":key,"value":value}}
        self.queueJSON(param)


    def getSources(self, media='video', cache=True):
        param = {"method":"Files.GetSources","params":{"media":media}}
        if cache: return self.cacheJSON(param).get('result', {}).get('sources', [])
        else:     return self.sendJSON(param).get('result', {}).get('sources', [])


    def getAddonDetails(self, addonid=ADDON_ID, cache=True):
        param = {"method":"Addons.GetAddonDetails","params":{"addonid":addonid,"properties":self.getEnums("Addon.Fields", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('addon', {})
        else:     return self.sendJSON(param).get('result', {}).get('addon', {})


    def getAddons(self, param={"content":"video","enabled":True,"installed":True}, cache=True):
        param["properties"] = self.getEnums("Addon.Fields", type='items')
        param = {"method":"Addons.GetAddons","params":param}
        if cache: return self.cacheJSON(param).get('result', {}).get('addons', [])
        else:     return self.sendJSON(param).get('result', {}).get('addons', [])


    def getSongs(self, cache=True):
        param = {"method":"AudioLibrary.GetSongs","params":{"properties":self.getEnums("Audio.Fields.Song", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('songs', [])
        else:     return self.sendJSON(param).get('result', {}).get('songs', [])


    def getEpisodes(self, cache=True):
        param = {"method":"VideoLibrary.GetEpisodes","params":{"properties":self.getEnums("Video.Fields.Episode", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('tvshows', [])
        else:     return self.sendJSON(param).get('result', {}).get('tvshows', [])


    def getTVshows(self, cache=True):
        param = {"method":"VideoLibrary.GetTVShows","params":{"properties":self.getEnums("Video.Fields.TVShow", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('tvshows', [])
        else:     return self.sendJSON(param).get('result', {}).get('tvshows', [])


    def getMovies(self, cache=True):
        param = {"method":"VideoLibrary.GetMovies","params":{"properties":self.getEnums("Video.Fields.Movie", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('movies', [])
        else:     return self.sendJSON(param).get('result', {}).get('movies', [])


    def getVideoGenres(self, type="movie", cache=True): #type = "movie"/"tvshow"
        param = {"method":"VideoLibrary.GetGenres","params":{"type":type,"properties":self.getEnums("Library.Fields.Genre", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('genres', [])
        else:     return self.sendJSON(param).get('result', {}).get('genres', [])


    def getMusicGenres(self, cache=True):
        param = {"method":"AudioLibrary.GetGenres","params":{"properties":self.getEnums("Library.Fields.Genre", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('genres', [])
        else:     return self.sendJSON(param).get('result', {}).get('genres', [])


    def getDirectory(self, param={}, cache=True, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        param["properties"] = self.getEnums("List.Fields.Files", type='items')
        param = {"method":"Files.GetDirectory","params":param}
        if cache: return self.cacheJSON(param, expiration, checksum).get('result', {})
        else:     return self.sendJSON(param).get('result', {})
        
        
    def getLibrary(self, method, param={}, cache=True):
        param = {"method":method,"params":param}
        if cache: return self.cacheJSON(param).get('result', {})
        else:     return self.sendJSON(param).get('result', {})


    def getStreamDetails(self, path, media='video'):
        param = {"method":"Files.GetFileDetails","params":{"file":path,"media":media,"properties":["streamdetails"]}}
        return self.cacheJSON(param, life=datetime.timedelta(days=SETTINGS.getSettingInt('Max_Days')), checksum=getMD5(path)).get('result',{}).get('filedetails',{}).get('streamdetails',{})


    def getPlayerItem(self, playlist=False):
        self.log('getPlayerItem, playlist = %s' % (playlist))
        if playlist: param = {"method":"Playlist.GetItems","params":{"playlistid":self.getActivePlaylist(),"properties":self.getEnums("List.Fields.All", type='items')}}
        else:        param = {"method":"Player.GetItem"   ,"params":{"playerid":self.getActivePlayer()    ,"properties":self.getEnums("List.Fields.All", type='items')}}
        result = self.sendJSON(param).get('result', {})
        return (result.get('item', {}) or result.get('items', []))


    def getPVRChannels(self, radio=False):
        param = {"method":"PVR.GetChannels","params":{"channelgroupid":{True:'allradio',False:'alltv'}[radio],"properties":self.getEnums("PVR.Fields.Channel", type='items')}}
        return self.sendJSON(param).get('result', {}).get('channels', [])


    def getPVRChannelsDetails(self, id):
        param = {"method":"PVR.GetChannelDetails","params":{"channelid":id,"properties":self.getEnums("PVR.Fields.Channel", type='items')}}
        return self.sendJSON(param).get('result', {}).get('channels', [])


    def getPVRBroadcasts(self, id):
        param = {"method":"PVR.GetBroadcasts","params":{"channelid":id,"properties":self.getEnums("PVR.Fields.Broadcast", type='items')}}
        return self.sendJSON(param).get('result', {}).get('broadcasts', [])


    def getPVRBroadcastDetails(self, id):
        param = {"method":"PVR.GetBroadcastDetails","params":{"broadcastid":id,"properties":self.getEnums("PVR.Fields.Broadcast", type='items')}}
        return self.sendJSON(param).get('result', {}).get('broadcastdetails', [])


    def getDuration(self, path, item={}, accurate=bool(SETTINGS.getSettingInt('Duration_Type'))):
        self.log("getDuration, accurate = %s, path = %s" % (accurate, path))
        duration = 0
        runtime  = int(item.get('runtime', '') or item.get('duration', '') or (item.get('streamdetails', {}).get('video',[]) or [{}])[0].get('duration','') or '0')
        if (runtime == 0 or accurate):
            if not path.startswith(tuple(VFS_TYPES)):# no additional parsing needed item[runtime] has only meta available.
                if isStack(path):# handle "stacked" videos
                    paths = splitStacks(path)
                    for file in paths: 
                        duration += self.parseDuration(file)
                else: 
                    duration = self.parseDuration(path, item)
                if duration > 0: runtime = duration
        self.log("getDuration, path = %s, runtime = %s" % (path, runtime))
        return runtime


    def parseDuration(self, path, item={}, save=SETTINGS.getSettingBool('Store_Duration')):
        self.log("parseDuration, path = %s, save = %s" % (path, save))
        cacheCHK  = getMD5(path)
        cacheName = 'parseDuration.%s'%(cacheCHK)
        runtime   = int(item.get('runtime', '') or item.get('duration', '') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration','') or '0')
        duration  = self.cache.get(cacheName, checksum=cacheCHK, json_data=False)
        if not duration:
            try:
                duration = self.videoParser.getVideoLength(path.replace("\\\\", "\\"), item, self)
                if duration > 0:
                    self.cache.set(cacheName, duration, checksum=cacheCHK, expiration=datetime.timedelta(days=28),json_data=False)
            except Exception as e:
                log("parseDuration, failed! %s"%(e), xbmc.LOGERROR)
                duration = 0

        ## duration diff. safe guard, how different are the two values? if > 45% don't save to Kodi.
        rundiff = int(percentDiff(runtime, duration))
        runsafe = False
        if (rundiff <= 45 and rundiff > 0) or (rundiff == 100 and (duration == 0 or runtime == 0)) or (rundiff == 0 and (duration > 0 and runtime > 0)) or (duration > runtime):
            runsafe = True
        self.log("parseDuration, path = %s, runtime = %s, duration = %s, difference = %s%%, safe = %s" % (path, runtime, duration, rundiff, runsafe))
        ## save parsed duration to Kodi database, if enabled.
        if save and runsafe and (item.get('id', -1) > 0): self.queDuration(item['type'], item.get('id', -1), duration)
        if runsafe: runtime = duration
        self.log("parseDuration, returning runtime = %s" % (runtime))
        return runtime
  
  
    def queDuration(self, media, dbid, dur):
        self.log('queDuration, media = %s, dbid = %s, dur = %s' % (media, dbid, dur))
        param = {'movie'     : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid":dbid, "runtime":dur}},
                 'episode'   : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid":dbid, "runtime":dur}},
                 'musicvideo': {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":dbid, "runtime":dur}},
                 'song'      : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid":dbid, "runtime":dur}}}
        self.queueJSON(param[media])
        

    def requestList(self, citem, item, media='video', page=int(REAL_SETTINGS.getSetting('Page_Limit')), sort={}, filter={}, limits={}):
        getFile = True
        path    = item
        if isinstance(item, dict): #library json query
            getFile = False
            path    = item.get('value')
        
        self.log("requestList, id: %s, getFile = %s, limit = %s, sort = %s, filter = %s, limits = %s\npath = %s"%(citem['id'],getFile,page,sort,filter,limits,path))
        # todo use adv. channel rules to set autoPagination cache expiration & checksum to force refresh times.
        if not limits: 
            limits = self.autoPagination(citem['id'], path) #get
            total  = limits.get('total',0)
            if total > page and sort.get("method","") == "random" and not path.startswith(tuple(VFS_TYPES)):
                limits = self.randomPagination(page,total)
                self.log('requestList, id = %s generating random limits = %s'%(citem['id'],limits))

        param = {}
        param["limits"]          = {}
        param["limits"]["start"] = limits.get('end', 0)
        param["limits"]["end"]   = limits.get('end', 0) + page
        
        if sort:   param["sort"]   = sort
        if filter: param['filter'] = filter

        if getFile:
            param["properties"] = self.getEnums("List.Fields.Files", type='items')
            param["media"]      = media
            param["directory"]  = escapeDirJSON(path)
        else:
            param["properties"] = self.getEnums(item['enum'], type='items')
        self.log('requestList, id = %s, page = %s\nparam = %s'%(citem['id'], page, param))
        
        if getFile:
            results = self.getDirectory(param)
            limits  = results.get('limits', param["limits"])
            if 'filedetails' in results: key = 'filedetails'
            else:                        key = 'files'
        else:
            results = self.getLibrary(item['method'],param)
            limits  = results.pop('limits') 
            key     = list(results.keys())[0]
            
        items = results.get(key, [])
        total = limits.get('total',0)
        try:
            if param.get("directory","").startswith(tuple(VFS_TYPES)) and (len(items) > page and len(items) == total):
                #VFS paths ie.Plugin:// may fail to apply limits and return a full directory list. Instead use limits param to slice list.
                items = items[param["limits"]["start"]:param["limits"]["end"]]
                self.log('requestList, id = %s, items = %s sliced from VFS exceeding page %s'%(citem['id'], len(items), page))
        except Exception as e: self.log('requestList, id = %s, failed! to slice items %s'%(citem['id'],e), xbmc.LOGERROR)

        if len(items) > page:
            #in the rare (if at all possible) instance items may exceed expected limits, truncate size.
            items = items[:page]
            self.log('requestList, id = %s, items = %s truncated to %s'%(citem['id'], len(items), page))
        self.log('requestList, id = %s, items = %s, result limits = %s'%(citem['id'], len(items), limits))
        
        if (limits.get('end',0) >= total or limits.get('start',0) >= total):
            # restart page to 0, exceeding boundaries.
            self.log('requestList, id = %s, resetting limits to 0'%(citem['id']))
            limits = {"end": 0, "start": 0, "total": limits.get('total',0)}
        self.autoPagination(citem['id'], path, limits) #set 
        
        if (len(items) == 0 and total > 0) and not path.startswith(tuple(VFS_TYPES)):
            # retry last request with fresh limits.
            self.log("requestList, id = %s, trying again with start at 0"%(citem['id']))
            return self.requestList(citem, item, media, page, sort, filter, {"end": 0, "start": 0, "total": limits.get('total',0)})
        elif (len(items) > 0 and len(items) < page) and (total > 0 and total < page):
            # path total doesn't fill page limit; pad with duplicates.
            self.log("requestList, id = %s, padding items with duplicates"%(citem['id']))
            items = self.padItems(items)
            
        self.log("requestList, id = %s, return items = %s" % (citem['id'], len(items)))
        if not getFile: items = {key:items}
        return items


    def autoPagination(self, id, path, limits={}, checksum='', life=datetime.timedelta(days=28)):
        cacheName = 'autoPagination.%s.%s'%(id,getMD5(path))
        if not checksum: checksum = id
        if not limits:
            msg = 'get'
            limits = self.cache.get(cacheName, checksum=checksum, json_data=True, default={"end": 0, "start": 0, "total":0})
        else:
            msg = 'set'
            self.cache.set(cacheName, limits, checksum=checksum, expiration=life, json_data=True)
        self.log("%s autoPagination; id = %s, limits = %s, path = %s"%(msg,id,limits,path))
        return limits
            
             
    def randomPagination(self, page=int(REAL_SETTINGS.getSetting('Page_Limit')), total=0):
        if total > page: start = random.randrange(0, (total-page), page)
        else:            start = 0
        return {"end": start, "start": start, "total":total}
        

    @cacheit(checksum=getInstanceID())
    def buildWebBase(self, local=False):
        port     = 80
        username = 'kodi'
        password = ''
        secure   = False
        enabled  = True
        settings = self.getSetting('control','services')
        for setting in settings:
            if setting['id'] == 'services.webserver' and not setting['value']:
                enabled = False
                DIALOG.notificationDialog(LANGUAGE(32131))
                break
            if setting['id'] == 'services.webserverusername':
                username = setting['value']
            elif setting['id'] == 'services.webserverport':
                port = setting['value']
            elif setting['id'] == 'services.webserverpassword':
                password = setting['value']
            elif setting['id'] == 'services.webserverssl' and setting['value']:
                secure = True
            username = '{0}:{1}@'.format(username, password) if username and password else ''
        protocol = 'https' if secure else 'http'
        if local: ip = 'localhost'
        else:     ip = getIP()
        return '{0}://{1}{2}:{3}'.format(protocol,ip,username, port) 
            
            
    @cacheit(checksum=getInstanceID())
    def buildProvisional(self, value, type):
        self.log('buildProvisional, value = %s, type = %s'%(value,type))
        paths   = []
        for request in PROVISIONAL_TYPES.get(type,{}).get('path',[]):
            items = self.getDirectory(param={"directory":request}, cache=False).get('files',[])
            for item in items:
                if item.get('label') == value:
                    paths.append(item['file'])
                    break
        self.log('buildProvisional, return paths = %s'%(paths))
        return paths


    def padItems(self, items, page=int(REAL_SETTINGS.getSetting('Page_Limit'))):
        # Balance media limits, by filling with duplicates to meet min. pagination.
        self.log("padItems; items In = %s"%(len(items)))
        if len(items) < page:
            iters = cycle(items)
            while not MONITOR.abortRequested() and len(items) < page:
                item = next(iters).copy()
                items.append(item)
        self.log("padItems; items Out = %s"%(len(items)))
        return items
        
        
    def hasPVRSource(self):
        for item in self.getSources():
            if item.get('file','').lower().startswith('pvr://'):
                return True
        return False
               