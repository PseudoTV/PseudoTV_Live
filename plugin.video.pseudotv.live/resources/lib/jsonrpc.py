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

class JSONRPC:
    def __init__(self):
        self.cache = SETTINGS.cacheDB
        self.videoParser = VideoParser()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)
    
    
    @contextmanager
    def sendLocker(self): #kodi jsonrpc not thread safe avoid request collision during threading.
        if PROPERTIES.getPropertyBool('sendLocker'):
            while not MONITOR.abortRequested():
                if not PROPERTIES.getPropertyBool('sendLocker'): break
                elif MONITOR.waitForAbort(.001): break
                self.log('sendLocker, waiting...')
        PROPERTIES.setPropertyBool('sendLocker',True)
        try: yield self.log('sendLocker, Locked!')
        finally:
            MONITOR.waitForAbort(float(SETTINGS.getSettingInt('RPC_Delay')/1000))
            PROPERTIES.setPropertyBool('sendLocker',False)


    def sendJSON(self, param, timeout=30):
        with self.sendLocker():
            command = param
            command["jsonrpc"] = "2.0"
            command["id"] = ADDON_ID
            self.log('sendJSON, command = %s'%(dumpJSON(command)))
            response = loadJSON(xbmc.executeJSONRPC(dumpJSON(command)))#(killit( or {'error':{'message':'JSONRPC timed out!'}})
            if response.get('error'):
                self.log('sendJSON, failed! error = %s\n%s'%(dumpJSON(response.get('error')),command), xbmc.LOGWARNING)
                response.setdefault('result',{})['error'] = response.pop('error')
            return response


    def queueJSON(self, param):
        queuePool = (SETTINGS.getCacheSetting('queuePool', json_data=True) or {})
        params = queuePool.setdefault('params',[])
        params.append(param)
        queuePool['params'] = sorted(setDictLST(params), key=lambda d: d.get('params',{}).get('playcount',-1))
        queuePool['params'] = sorted(setDictLST(params), key=lambda d: d.get('params',{}).get('setting',''))
        queuePool['params'].reverse() #prioritize setsetting,playcount rollback over duration amendments.
        self.log("queueJSON, saving = %s\n%s"%(len(queuePool['params']),param))
        SETTINGS.setCacheSetting('queuePool', queuePool, json_data=True)

        
    def cacheJSON(self, param, life=datetime.timedelta(minutes=15), checksum=ADDON_VERSION, timeout=15):
        cacheName = 'cacheJSON.%s'%(getMD5(dumpJSON(param)))
        cacheResponse = self.cache.get(cacheName, checksum=checksum, json_data=True)
        if not cacheResponse:
            cacheResponse = self.sendJSON(param,timeout)
            if cacheResponse.get('result',{}): self.cache.set(cacheName, cacheResponse, checksum=checksum, expiration=life, json_data=True)
        return cacheResponse


    def walkFileDirectory(self, path, media='files', depth=5, chkDuration=False, retItem=False, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        walk = dict()
        self.log('walkFileDirectory, walking %s, depth = %s'%(path,depth))
        for idx, item in enumerate(self.getDirectory({"directory":path,"media":media},True,checksum,expiration).get('files',[])):
            if item.get('filetype') == 'file':
                if chkDuration:
                    item['duration'] = self.getDuration(item.get('file'),item, accurate=bool(SETTINGS.getSettingInt('Duration_Type')))
                    if item['duration'] == 0: continue
                walk.setdefault(path,[]).append(item if retItem else item.get('file'))
            elif item.get('filetype') == 'directory' and depth > 0:
                depth -= 1
                walk.update(self.walkFileDirectory(item.get('file'), media, depth, chkDuration, retItem, checksum, expiration))
        return walk
                

    def walkListDirectory(self, path, exts='', depth=5, chkDuration=False, appendPath=False, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        def _chkfile(path, f):
            if exts and not f.lower().endswith(tuple(exts)): return
            if chkDuration:
                dur = self.getDuration(os.path.join(path,f), accurate=bool(SETTINGS.getSettingInt('Duration_Type')))
                if dur == 0: return
            return {True:os.path.join(path,f).replace('\\','/'),False:f}[appendPath]
            
        def _parseXBT(resource):
            self.log('walkListDirectory, parsing XBT = %s'%(resource))
            walk.setdefault(resource,[]).extend(self.getListDirectory(resource,checksum,expiration)[1])
            return walk

        walk = dict()
        path = path.replace('\\','/')
        subs, files = self.getListDirectory(path,checksum,expiration)
        if len(files) > 0 and TEXTURES in files: return _parseXBT(re.sub('/resources','',path).replace('special://home/addons/','resource://'))
        nfiles = [_f for _f in [_chkfile(path, file) for file in files] if _f]
        self.log('walkListDirectory, walking %s, found = %s, appended = %s, depth = %s, ext = %s'%(path,len(files),len(nfiles),depth,exts))
        walk.setdefault(path,[]).extend(nfiles)
        
        for sub in subs:
            if depth == 0:break
            depth -= 1
            walk.update(self.walkListDirectory(os.path.join(path,sub), exts, depth, chkDuration, appendPath, checksum, expiration))
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
    def getEnums(self, id, type='', key='enums'):
        self.log('getEnums id = %s, type = %s, key = %s' % (id, type, key))
        param = {"method":"JSONRPC.Introspect","params":{"getmetadata":True,"filterbytransport":True,"filter":{"getreferences":False,"id":id,"type":"type"}}}
        json_response = loadJSON(self.sendJSON(param).get('result',{}).get('types',{}).get(id,{}))
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
        else:     return self.sendJSON(param).get('result', {}).get('settings',[])


    def getSettingValue(self, key, cache=False):
        param = {"method":"Settings.GetSettingValue","params":{"setting":key}}
        if cache: return self.cacheJSON(param).get('result',{}).get('value','')
        else:     return self.sendJSON(param).get('result',{}).get('value','')


    def setSettingValue(self, key, value):
        param = {"method":"Settings.SetSettingValue","params":{"setting":key,"value":value}}
        self.queueJSON(param)


    def getSources(self, media='video', cache=False):
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


    def getArtists(self, cache=True):
        param = {"method":"AudioLibrary.GetArtists","params":{"properties":self.getEnums("Audio.Fields.Artist", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('artists', [])
        else:     return self.sendJSON(param).get('result', {}).get('artists', [])


    def getAlbums(self, cache=True):
        param = {"method":"AudioLibrary.GetAlbums","params":{"properties":self.getEnums("Audio.Fields.Album", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('albums', [])
        else:     return self.sendJSON(param).get('result', {}).get('albums', [])


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
        #todo carry over "error" to requestlist for user message.
        if cache: return self.cacheJSON(param, expiration, checksum).get('result', {})
        else:     return self.sendJSON(param).get('result', {})
        
        
    def getLibrary(self, method, param={}, cache=True):
        param = {"method":method,"params":param}
        if cache: return self.cacheJSON(param).get('result', {})
        else:     return self.sendJSON(param).get('result', {})


    def getStreamDetails(self, path, media='video'):
        if isStack(path): path = splitStacks(path)[0]
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

    
    def _setRuntime(self, item={}, runtime=0, save=SETTINGS.getSettingBool('Store_Duration')):
        self.cache.set('getRuntime.%s'%(getMD5(item.get('file'))), runtime, checksum=getMD5(item.get('file')), expiration=datetime.timedelta(days=28), json_data=False)
        if save and item: self.queDuration(item, runtime=runtime)
        return runtime
    
        
    def _getRuntime(self, item={}):
        runtime = self.cache.get('getRuntime.%s'%(getMD5(item.get('file'))), checksum=getMD5(item.get('file')), json_data=False)
        return (runtime or item.get('resume',{}).get('total') or item.get('runtime') or item.get('duration') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration') or 0)
        

    def _setDuration(self, path, item={}, duration=0, save=SETTINGS.getSettingBool('Store_Duration')):
        self.cache.set('getDuration.%s'%(getMD5(path)), duration, checksum=getMD5(path), expiration=datetime.timedelta(days=28), json_data=False)
        if save and item: self.queDuration(item, duration)
        return duration

    
    def _getDuration(self, path):
        return (self.cache.get('getDuration.%s'%(getMD5(path)), checksum=getMD5(path), json_data=False) or 0)


    def getDuration(self, path, item={}, accurate=bool(SETTINGS.getSettingInt('Duration_Type')), save=SETTINGS.getSettingBool('Store_Duration')):
        self.log("getDuration, accurate = %s, path = %s, save = %s" % (accurate, path, save))
        if not item: item = {'file':path}
        runtime = self._getRuntime(item)
        if runtime == 0 or accurate:
            if isStack(path):# handle "stacked" videos
                for file in splitStacks(path): duration += self.__parseDuration(runtime, file)
            else: duration = self.__parseDuration(runtime, path, item, save)
            if duration > 0: runtime = duration
        self.log("getDuration, returning path = %s, runtime = %s" % (path, runtime))
        return runtime


    def __parseDuration(self, runtime, path, item={}, save=SETTINGS.getSettingBool('Store_Duration')):
        self.log("__parseDuration, runtime = %s, path = %s, save = %s" % (runtime, path, save))
        duration = self.videoParser.getVideoLength(path.replace("\\\\", "\\"), item, self)
        if not path.startswith(tuple(VFS_TYPES)):
            ## duration diff. safe guard, how different are the two values? if > 45% don't save to Kodi.
            rundiff = int(percentDiff(runtime, duration))
            runsafe = False
            if (rundiff <= 45 and rundiff > 0) or (rundiff == 100 and (duration == 0 or runtime == 0)) or (rundiff == 0 and (duration > 0 and runtime > 0)) or (duration > runtime): runsafe = True
            self.log("__parseDuration, path = %s, runtime = %s, duration = %s, difference = %s%%, safe = %s" % (path, runtime, duration, rundiff, runsafe))
            ## save parsed duration to Kodi database, if enabled.
            if runsafe:
                runtime = duration
                # if save and not path.startswith(tuple(VFS_TYPES)): self.queDuration(item, duration)
        else: runtime = duration
        self.log("__parseDuration, returning runtime = %s" % (runtime))
        return runtime
  
  
    def queDuration(self, item={}, duration=0, runtime=0):
        param = {'video'      : {},
                 'movie'      : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                 'movies'     : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('movieid',-1)      ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                 'episode'    : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                 'episodes'   : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('episodeid',-1)    ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                 'musicvideo' : {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                 'musicvideos': {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('musicvideoid',-1) ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                 'song'       : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                 'songs'      : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('songid',-1)       ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}}}
        try:
            params = param.get(item.get('type'))
            if params:
                if   duration == 0: param['params'].pop('resume')
                elif runtime  == 0: param['params'].pop('runtime')
                id = (item.get('id') or item.get('movieid') or item.get('episodeid') or item.get('musicvideoid') or item.get('songid'))
                self.log('queDuration, id = %s, media = %s, duration = %s, runtime = %s'%(id,item['type'],duration,runtime))
                self.queueJSON(params)
        except Exception as e: self.log("queDuration, failed! %s\nitem = %s"%(e,item), xbmc.LOGERROR)
        
        
    def quePlaycount(self, item):
        param = {'video'      : {},
                 'movie'      : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('id',-1)           ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'movies'     : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('movieid',-1)      ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'episode'    : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('id',-1)           ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'episodes'   : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('episodeid',-1)    ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'musicvideo' : {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('id',-1)           ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'musicvideos': {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('musicvideoid',-1) ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'song'       : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('id',-1)           ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}},
                 'songs'      : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('songid',-1)       ,"playcount": item.get('playcount',0),"resume": {"position": item.get('position',0.0),"total": item.get('total',0.0)}}}}
        try:
            if not item.get('file','').startswith(tuple(VFS_TYPES)):
                params = param.get(item.get('type'))
                if params:
                    id = (item.get('id') or item.get('movieid') or item.get('episodeid') or item.get('musicvideoid') or item.get('songid'))
                    self.log('quePlaycount, id = %s, media = %s, playcount = %s, resume = %s'%(id,item['type'],item.get('playcount',0),item.get('resume',{})))
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
        self.log("requestList, id: %s, getDirectory = %s, media = %s, limit = %s, sort = %s, query = %s, limits = %s\npath = %s"%(citem['id'],getDirectory,media,page,sort,query,limits,path))
        
        if limits.get('end',-1) == -1: #global default, replace with autoPagination.
            limits = self.autoPagination(citem['id'], '|'.join([path,dumpJSON(query)])) #get
            self.log('requestList, id = %s autoPagination limits = %s'%(citem['id'],limits))
            if limits.get('total',0) > page and sort.get("method","") == "random":
                limits = self.randomPagination(page,limits)
                self.log('requestList, id = %s generating random limits = %s'%(citem['id'],limits))

        param["limits"]          = {}
        param["limits"]["start"] = 0 if limits.get('end', 0) == -1 else limits.get('end', 0)
        param["limits"]["end"]   = abs(limits.get('end', 0) + page)
        param["sort"] = sort
        self.log('requestList, id = %s, page = %s\nparam = %s'%(citem['id'], page, param))
        
        if getDirectory:
            results = self.getDirectory(param, cache=False)
            if 'filedetails' in results: key = 'filedetails'
            else:                        key = 'files'
        else:
            results = self.getLibrary(query['method'],param, cache=False)
            key = query.get('key',list(results.keys())[0])
            
        limits = results.get('limits', param["limits"])
        if (limits.get('end',0) >= limits.get('total',0) or limits.get('start',0) >= limits.get('total',0)):
            # restart page to 0, exceeding boundaries.
            self.log('requestList, id = %s, resetting limits to 0'%(citem['id']))
            limits = {"end": 0, "start": 0, "total": limits.get('total',0)}
        self.autoPagination(citem['id'], '|'.join([path,dumpJSON(query)]), limits) #set 
        
        errors = results.get('error',{})
        items  = results.get(key, [])
        
        if len(items) == 0 and limits.get('total',0) > 0:
            # retry last request with fresh limits.
            self.log("requestList, id = %s, trying again with start limits at 0"%(citem['id']))
            return self.requestList(citem, path, media, page, sort, {"end": 0, "start": 0, "total": limits.get('total',0)}, query)
        else:
            self.log("requestList, id = %s, return items = %s" % (citem['id'], len(items)))
            return items, limits, errors


    def autoPagination(self, id, path, limits={}):
        cacheName = 'autoPagination.%s.%s'%(id,getMD5(path))
        if not limits:
            msg = 'get'
            limits = (self.cache.get(cacheName, checksum=id, json_data=True) or {"end": 0, "start": 0, "total":0})
        else:
            msg = 'set'
            self.cache.set(cacheName, limits, checksum=id, expiration=datetime.timedelta(days=28), json_data=True)
        self.log("%s autoPagination; id = %s, limits = %s, path = %s"%(msg,id,limits,path))
        return limits
            
             
    def randomPagination(self, page=SETTINGS.getSettingInt('Page_Limit'), limits={}):
        total = limits.get('total',0)
        if total > page: start = random.randrange(0, (total-page), page)
        else:            start = 0
        return {"end": start, "start": start, "total":total}
        

    @cacheit(checksum=PROPERTIES.getInstanceID())
    def buildWebBase(self, local=False):
        port     = 80
        username = 'kodi'
        password = ''
        secure   = False
        enabled  = True
        for setting in self.getSetting('control','services'):
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
        else:     ip = getIP()
        webURL =  '{0}://{1}{2}:{3}'.format(protocol,username,ip, port)
        self.log("buildWebBase; returning %s"%(webURL))
        return webURL
            
            
    def padItems(self, files, page=SETTINGS.getSettingInt('Page_Limit')):
        # Balance media limits, by filling with duplicates to meet min. pagination.
        self.log("padItems; files In = %s"%(len(files)))
        if len(files) < page:
            iters = cycle(files)
            while not MONITOR.abortRequested() and (len(files) < page and len(files) > 0):
                item = next(iters).copy()
                if self.getDuration(item.get('file'),item) == 0:
                    try: files.pop(files.index(item))
                    except: break
                else: files.append(item)
        self.log("padItems; files Out = %s"%(len(files)))
        return files


    @cacheit(expiration=datetime.timedelta(seconds=EPOCH_TIMER),json_data=False)
    def InputFriendlyName(self):
        with PROPERTIES.suspendActivity():
            fn = self.getSettingValue("services.devicename")
            self.log("InputFriendlyName, name = %s"%(fn))
            if not fn or fn.lower() == 'kodi':
                if DIALOG.okDialog(LANGUAGE(32132)%(fn)):
                    input = DIALOG.inputDialog(LANGUAGE(30122), fn)
                    if not input or input.lower() == 'kodi':
                        return self.InputFriendlyName()
                    else:
                        self.setSettingValue("services.devicename",input)
                        self.log('InputFriendlyName, setting device name = %s'%(input))
                        return input
            return fn
            
            
    def getCallback(self, sysInfo={}):
        self.log('getCallback, id = %s, radio = %s, isPlaylist = %s'%(sysInfo.get('chid'),sysInfo.get('radio',False),sysInfo.get('isPlaylist',False)))
        def _matchJSON():#requires 'pvr://' json whitelisting.
            results = self.getDirectory(param={"directory":"pvr://channels/{dir}/".format(dir={'True':'radio','False':'tv'}[str(sysInfo.get('radio',False))])}, cache=False).get('files',[])
            for dir in [ADDON_NAME,'All channels']: #todo "All channels" may not work with non-English translations!
                for result in results:
                    if result.get('label','').lower().startswith(dir.lower()):
                        self.log('getCallback: _matchJSON, found dir = %s'%(result.get('file')))
                        channels = self.getDirectory(param={"directory":result.get('file')},checksum=PROPERTIES.getInstanceID(),expiration=datetime.timedelta(minutes=EPOCH_TIMER)).get('files',[])
                        for item in channels:
                            if item.get('label','').lower() == sysInfo.get('name','').lower() and decodePlot(item.get('plot','')).get('citem',{}).get('id') == sysInfo.get('chid'):
                                self.log('getCallback: _matchJSON, id = %s, found file = %s'%(sysInfo.get('chid'),item.get('file')))
                                return item.get('file')
                                
        if sysInfo.get('mode','').lower() == 'live' and sysInfo.get('chpath'): callback = sysInfo.get('chpath')
        else: callback = _matchJSON()
        self.log('getCallback: returning callback = %s'%(callback))
        return callback
        
        
        