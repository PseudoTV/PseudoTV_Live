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
# -*- coding: utf-8 -*-

from globals     import *
from videoparser import VideoParser

MIN_DIR_PARAMS = ["title", "showtitle", "episode", "season", "runtime", "duration",
                  "streamdetails", "year", "plot", "plotoutline","description", 
                  "art", "writer", "cast", "rating", "genre", "director", "mpaa",
                  "premiered", "playcount", "studio"]

class JSONRPC:
    def __init__(self, cache=None):
        if cache is None: self.cache = Cache()
        else:             self.cache = cache
        self.videoParser = VideoParser()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)
    
    
    @contextmanager
    def sendLocker(self): #kodi jsonrpc not thread safe avoid request collision during threading.
        if PROPERTIES.getEXTProperty('%s.sendLocker'%(ADDON_ID)) == 'true':
            while not MONITOR.abortRequested():
                if not PROPERTIES.getEXTProperty('%s.sendLocker'%(ADDON_ID)) == 'true': break
                elif MONITOR.waitForAbort(0.001): break
        PROPERTIES.setEXTProperty('%s.sendLocker'%(ADDON_ID),'true')
        try: yield
        finally:
            PROPERTIES.setEXTProperty('%s.sendLocker'%(ADDON_ID),'false')


    def _sendJSON(self, command):
        self.log('_sendJSON, command = %s'%(command))
        results = loadJSON(xbmc.executeJSONRPC(dumpJSON(command)))
        MONITOR.waitForAbort(SETTINGS.getSettingInt('RPC_Delay')/1000)
        #overcome overflow issues within Kodi JSONRPC. Windows Platform unaffected. Kodi will segfault when flooded with json requests.
        return results


    def sendJSON(self, param, timeout=15): #todo dynamic timeout based on parmas and timeout history.
        with self.sendLocker():
            command = param
            command["jsonrpc"] = "2.0"
            command["id"] = ADDON_ID
            # response = killJSON(self._sendJSON)(timeout, command)
            response = self._sendJSON(command)
            if response.get('error'):
                self.log('sendJSON, failed! error = %s\n%s'%(dumpJSON(response.get('error')),command), xbmc.LOGWARNING)
                
        if response.get('error',{}).get('message','').startswith('JSONRPC timed out!'):
            if timeout <= 15: return self.sendJSON(param, timeout=30)
        return response


    def queueJSON(self, param):
        queuePool = SETTINGS.getCacheSetting('queuePool', json_data=True, default={})
        params = queuePool.setdefault('params',[])
        params.append(param)
        queuePool['params'] = sorted(setDictLST(params), key=lambda d: d.get('params',{}).get('playcount',-1))
        queuePool['params'].reverse() #prioritize playcount rollback over duration amendments.
        self.log("queueJSON, queueing = %s\n%s"%(len(queuePool['params']),param))
        SETTINGS.setCacheSetting('queuePool', queuePool, json_data=True)

        
    def cacheJSON(self, param, life=datetime.timedelta(minutes=15), checksum=ADDON_VERSION, timeout=15):
        cacheName = 'cacheJSON.%s'%(getMD5(dumpJSON(param)))
        cacheResponse = self.cache.get(cacheName, checksum=checksum, json_data=True)
        if not cacheResponse:
            cacheResponse = self.sendJSON(param,timeout)
            if cacheResponse.get('result',{}):
                self.cache.set(cacheName, cacheResponse, checksum=checksum, expiration=life, json_data=True)
        return cacheResponse


    def walkFileDirectory(self, path, exts=VIDEO_EXTS, depth=3, chkDuration=False, retItem=False, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        self.log('walkFileDirectory, path = %s, exts = %s'%(path,exts))
        walk = dict()
        dirs = [path]
        for idx, dir in enumerate(dirs):
            if MONITOR.waitForAbort(0.001) or idx > depth: break
            else:
                self.log('walkFileDirectory, walking %s/%s directory'%(idx,len(dirs)))
                for item in self.getDirectory(param={"directory":dir}).get('files',[]):
                    if not item.get('file') or not item.get('file','').endswith(tuple(exts)): continue
                    elif item.get('filetype') == 'directory': dirs.append(item.get('file'))
                    elif item.get('filetype') == 'file':
                        if chkDuration:
                            dur = self.getDuration(item.get('file'),item, accurate=True)
                            if dur == 0: continue
                            item['duration'] = dur
                        walk.setdefault(dir,[]).append(item if retItem else item.get('file'))
        return walk
                

    def walkListDirectory(self, path, exts=VIDEO_EXTS, depth=3, chkDuration=False, appendPath=False, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        def _chkfile(path, f):
            if chkDuration:
                if self.getDuration(os.path.join(path,f), accurate=True) == 0: return
            if appendPath: return os.path.join(path,f)
            else:          return f
            
        def _parseXBT():
            resource = path.replace('/resources','').replace('special://home/addons/','resource://')
            walk.setdefault(resource,[]).extend(self.getListDirectory(resource,checksum,expiration)[1])
            return walk
             
        self.log('walkListDirectory, path = %s, exts = %s'%(path,exts))
        walk = dict()
        path = path.replace('\\','/')
        dirs, files = self.getListDirectory(path,checksum,expiration)
        if TEXTURES in files: return _parseXBT()
        else: walk.setdefault(path,[]).extend(list(filter(None,[_chkfile(path, f) for f in files if f.endswith(tuple(exts))])))
        for idx, dir in enumerate(dirs): 
            if MONITOR.waitForAbort(0.001) or idx > depth: break
            else:
                self.log('walkListDirectory, walking %s/%s directory'%(idx,len(dirs)))
                walk.update(self.walkListDirectory(os.path.join(path, dir),exts,checksum))
        return walk
        
        
    def getListDirectory(self, path, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
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
        return self.cacheJSON(param, life=datetime.timedelta(days=MAX_GUIDEDAYS), checksum=getMD5(path)).get('result',{}).get('filedetails',{}).get('streamdetails',{})


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


    #@cacheit(expiration=datetime.timedelta(days=28))
    def parseYoutubeRuntime(self, id):
        runtime = 0
        #todo user api keys.
        # from youtube_requests import get_videos
        # https://github.com/anxdpanic/plugin.video.youtube/blob/master/resources/lib/youtube_requests.py#L62
        self.log("parseYoutubeRuntime, id = %s, runtime = %s" % (id, runtime))
        return runtime


    def getDuration(self, path, item={}, accurate=bool(SETTINGS.getSettingInt('Duration_Type'))):
        self.log("getDuration, accurate = %s, path = %s" % (accurate, path))
        runtime = (item.get('runtime') or item.get('duration') or item.get('streamdetails', {}).get('video',[{}])[0].get('duration') or 0)
        if not runtime and path.startswith(('plugin://plugin.video.youtube','plugin://plugin.video.tubed','plugin://plugin.video.invidious')):
            try:    runtime = self.parseYoutubeRuntime(path.split('?video_id=')[1])
            except: runtime = 0
        
        if (runtime == 0 or accurate):
            if not path.startswith(tuple(VFS_TYPES)):# no additional parsing needed item[runtime] has only meta available.
                duration = 0
                if isStack(path):# handle "stacked" videos
                    for file in splitStacks(path): 
                        duration += self.parseDuration(file)
                else: duration = self.parseDuration(path, item)
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
        if save and runsafe and item.get('type'): self.queDuration(item, duration)
        if runsafe: runtime = duration
        self.log("parseDuration, returning runtime = %s" % (runtime))
        return runtime
  
  
    def queDuration(self, item, dur):
        #overcome inconsistent keys from Kodis jsonRPC.
        param = {'video'      : {},
                 'movie'      : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('id',-1)           , "runtime": dur}},
                 'movies'     : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('movieid',-1)      , "runtime": dur}},
                 'episode'    : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('id',-1)           , "runtime": dur}},
                 'episodes'   : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('episodeid',-1)    , "runtime": dur}},
                 'musicvideo' : {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('id',-1)           , "runtime": dur}},
                 'musicvideos': {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('musicvideoid',-1) , "runtime": dur}},
                 'song'       : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('id',-1)           , "runtime": dur}},
                 'songs'      : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('songid',-1)       , "runtime": dur}}}
        try:
            params = param[item['type']]
            if -1 in params: raise Exception('no dbid found')
            elif params:
                self.log('queDuration, media = %s, dur = %s' % (item['type'], dur))
                self.queueJSON(params)
        except Exception as e: self.log("queDuration, failed! %s\nitem = %s"%(e,item), xbmc.LOGERROR)
        
        
    def quePlaycount(self, item):
        #overcome inconsistent keys from Kodis jsonRPC.
        param = {'video'      : {},
                 'movie'      : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('id',-1)           , "playcount": item.get('playcount',0), "resume": {"position": item.get('position',0), "total": item.get('total',0)}}},
                 'movies'     : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('movieid',-1)      , "playcount": item.get('playcount',0), "resume": {"position": item.get('position',0), "total": item.get('total',0)}}},
                 'episode'    : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('id',-1)           , "playcount": item.get('playcount',0), "resume": {"position": item.get('position',0), "total": item.get('total',0)}}},
                 'episodes'   : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('episodeid',-1)    , "playcount": item.get('playcount',0), "resume": {"position": item.get('position',0), "total": item.get('total',0)}}},
                 'musicvideo' : {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('id',-1)           , "playcount": item.get('playcount',0), "resume": {"position": item.get('position',0), "total": item.get('total',0)}}},
                 'musicvideos': {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('musicvideoid',-1) , "playcount": item.get('playcount',0), "resume": {"position": item.get('position',0), "total": item.get('total',0)}}},
                 'song'       : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('id',-1)           , "playcount": item.get('playcount',0), "resume": {"position": item.get('position',0), "total": item.get('total',0)}}},
                 'songs'      : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('songid',-1)       , "playcount": item.get('playcount',0), "resume": {"position": item.get('position',0), "total": item.get('total',0)}}}}
        try:
            params = param[item['type']]
            if -1 in params: raise Exception('no dbid found')
            elif params: 
                self.log('quePlaycount, media = %s, count = %s' % (item['type'],item.get('playcount',0)))
                self.queueJSON(params)
        except Exception as e: self.log("quePlaycount, failed! %s\nitem = %s"%(e,item), xbmc.LOGERROR)


    def requestList(self, citem, path, media='video', page=SETTINGS.getSettingInt('Page_Limit'), sort={}, limits={}, query={}):
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
            param["directory"]  = escapeDirJSON(path)
            param["properties"] = self.getEnums("List.Fields.Files", type='items')
        self.log("requestList, id: %s, getDirectory = %s, limit = %s, sort = %s, query = %s, limits = %s\npath = %s"%(citem['id'],getDirectory,page,sort,query,limits,path))
        
        if not limits: 
            limits = self.autoPagination(citem['id'], '|'.join([path,dumpJSON(query)])) #get
            if (limits.get('total',0) > page) and sort.get("method","") == "random" and not path.startswith(tuple(VFS_TYPES)):
                limits = self.randomPagination(page,limits.get('total',0))
                self.log('requestList, id = %s generating random limits = %s'%(citem['id'],limits))

        param["limits"]          = {}
        param["limits"]["start"] = limits.get('end', 0)
        param["limits"]["end"]   = limits.get('end', 0) + page
        if sort: param["sort"]   = sort
        self.log('requestList, id = %s, page = %s\nparam = %s'%(citem['id'], page, param))
        
        if getDirectory:
            results = self.getDirectory(param)
            if 'filedetails' in results: key = 'filedetails'
            else:                        key = 'files'
        else:
            results = self.getLibrary(query['method'],param)
            key = query.get('key',list(results.keys())[0])
            
        limits = results.get('limits', param["limits"])
        if (limits.get('end',0) >= limits.get('total',0) or limits.get('start',0) >= limits.get('total',0)):
            # restart page to 0, exceeding boundaries.
            self.log('requestList, id = %s, resetting limits to 0'%(citem['id']))
            limits = {"end": 0, "start": 0, "total": limits.get('total',0)}
        self.autoPagination(citem['id'], '|'.join([path,dumpJSON(query)]), limits) #set 
        
        items  = results.get(key, [])
        errors = {}
        try:
            if param.get("directory","").startswith(tuple(VFS_TYPES)) and (len(items) > page and len(items) == limits.get('total',0)):
                #VFS paths ie.Plugin:// may fail to apply limits and return a full directory list. Instead use limits param to slice list.
                items = items[param["limits"]["start"]:param["limits"]["end"]]
                self.log('requestList, id = %s, items = %s sliced from VFS exceeding page %s'%(citem['id'], len(items), page))
        except Exception as e: self.log('requestList, id = %s, failed! to slice items %s'%(citem['id'],e), xbmc.LOGERROR)

        self.log('requestList, id = %s, items = %s, result limits = %s'%(citem['id'], len(items), limits))
        if (len(items) == 0 and limits.get('total',0) > 0) and not path.startswith(tuple(VFS_TYPES)):
            # retry last request with fresh limits.
            self.log("requestList, id = %s, trying again with start at 0"%(citem['id']))
            return self.requestList(citem, path, media, page, sort, {"end": 0, "start": 0, "total": limits.get('total',0)}, query)
        elif (len(items) > 0 and len(items) < page) and (limits.get('total',0) > 0 and limits.get('total',0) < page):
            # path total doesn't fill page limit; pad with duplicates.
            self.log("requestList, id = %s, padding items with duplicates"%(citem['id']))
            items = self.padItems(items)
        elif (len(items) > 0 and len(items) < page) and (limits.get('total',0) > 0 and limits.get('total',0) > page):
            # path total doesn't fill page limit; re-run with new limits
            self.log("requestList, id = %s, extending items with new limits"%(citem['id']))
            items.extend(self.requestList(citem, path, media, page-len(items), sort, limits, query)[0])

        self.log("requestList, id = %s, return items = %s" % (citem['id'], len(items)))
        return items, limits, errors


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
            
             
    def randomPagination(self, page=SETTINGS.getSettingInt('Page_Limit'), total=0):
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
            
            
    def padItems(self, items, page=SETTINGS.getSettingInt('Page_Limit')):
        # Balance media limits, by filling with duplicates to meet min. pagination.
        self.log("padItems; items In = %s"%(len(items)))
        if len(items) < page:
            iters = cycle(items)
            while not MONITOR.abortRequested() and (len(items) < page and len(items) > 0):
                item = next(iters).copy()
                if self.getDuration(item.get('file'),item) == 0:
                    try: items.pop(items.index(item))
                    except: break
                else:
                    items.append(item)
        self.log("padItems; items Out = %s"%(len(items)))
        return items
