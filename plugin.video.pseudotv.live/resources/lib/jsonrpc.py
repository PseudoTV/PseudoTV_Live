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

class Service:
    player  = PLAYER()
    monitor = MONITOR()
    def _interrupt(self) -> bool:
        return PROPERTIES.isPendingInterrupt()
    def _suspend(self) -> bool:
        return PROPERTIES.isPendingSuspend()
        
          
class JSONRPC:
    def __init__(self, service=None):
        if service is None: service = Service()
        self.service = service
        self.cache   = SETTINGS.cacheDB
        self.videoParser = VideoParser()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)


    def sendJSON(self, param, timeout=-1):
        command  = param
        command["jsonrpc"] = "2.0"
        command["id"] = ADDON_ID
        self.log('sendJSON, timeout = %s, command = %s'%(timeout,dumpJSON(command)))
        if timeout > 0: response = loadJSON((killit(BUILTIN.executeJSONRPC)(timeout,dumpJSON(command))) or {'error':{'message':'JSONRPC timed out!'}})
        else:           response = loadJSON(BUILTIN.executeJSONRPC(dumpJSON(command)))
        if response.get('error'):
            self.log('sendJSON, failed! error = %s\n%s'%(dumpJSON(response.get('error')),command), xbmc.LOGWARNING)
            response.setdefault('result',{})['error'] = response.pop('error')
        #throttle calls, low power devices suffer segfault during rpc flood
        self.service.monitor.waitForAbort(float(SETTINGS.getSettingInt('RPC_Delay')/1000))
        return response


    def queueJSON(self, param):
        queuePool = (SETTINGS.getCacheSetting('queueJSON', json_data=True) or {})
        params = queuePool.setdefault('params',[])
        params.append(param)
        queuePool['params'] = sorted(setDictLST(params), key=lambda d: d.get('params',{}).get('setting',''))
        queuePool['params'] = sorted(setDictLST(params), key=lambda d: d.get('params',{}).get('playcount',0))
        queuePool['params'].reverse() #prioritize setsetting,playcount rollback over duration amendments.
        self.log("queueJSON, saving = %s\n%s"%(len(queuePool['params']),param))
        SETTINGS.setCacheSetting('queueJSON', queuePool, json_data=True)

        
    def cacheJSON(self, param, life=datetime.timedelta(minutes=15), checksum=ADDON_VERSION, timeout=-1):
        cacheName = 'cacheJSON.%s'%(getMD5(dumpJSON(param)))
        cacheResponse = self.cache.get(cacheName, checksum=checksum, json_data=True)
        if not cacheResponse:
            cacheResponse = self.sendJSON(param, timeout)
            if cacheResponse.get('result',{}): self.cache.set(cacheName, cacheResponse, checksum=checksum, expiration=life, json_data=True)
        return cacheResponse


    def walkFileDirectory(self, path, media='video', depth=5, chkDuration=False, retItem=False, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        walk = dict()
        self.log('walkFileDirectory, walking %s, depth = %s'%(path,depth))
        items = self.getDirectory({"directory":path,"media":media},True,checksum,expiration).get('files',[])
        for idx, item in enumerate(items):
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
            if depth == 0: break
            depth -= 1
            walk.update(self.walkListDirectory(os.path.join(path,sub), exts, depth, chkDuration, appendPath, checksum, expiration))
        return walk
                
        
    def getListDirectory(self, path, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        cacheName = 'getListDirectory.%s'%(getMD5(path))
        results   = self.cache.get(cacheName, checksum)
        if not results:
            try:    
                results = self.cache.set(cacheName, FileAccess.listdir(path), checksum, expiration)
                self.log('getListDirectory path = %s, checksum = %s'%(path, checksum))
            except Exception as e:
                self.log("getListDirectory, failed! %s\npath = %s"%(e,path), xbmc.LOGERROR)
                results = [],[]
        self.log('getListDirectory return dirs = %s, files = %s\n%s'%(len(results[0]), len(results[1]),path))
        return results


    def getIntrospect(self, id):
        param = {"method":"JSONRPC.Introspect","params":{"filter":{"id":id,"type":"method"}}}
        return self.cacheJSON(param,datetime.timedelta(days=28),BUILTIN.getInfoLabel('BuildVersion','System')).get('result',{})


    def getEnums(self, id, type='', key='enums'):
        self.log('getEnums id = %s, type = %s, key = %s' % (id, type, key))
        param = {"method":"JSONRPC.Introspect","params":{"getmetadata":True,"filterbytransport":True,"filter":{"getreferences":False,"id":id,"type":"type"}}}
        json_response = self.cacheJSON(param,datetime.timedelta(days=28),BUILTIN.getInfoLabel('BuildVersion','System')).get('result',{}).get('types',{}).get(id,{})
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
        if cache: return self.cacheJSON(param).get('result', {}).get('episodes', [])
        else:     return self.sendJSON(param).get('result', {}).get('episodes', [])


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


    def getDirectory(self, param={}, cache=True, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15), timeout=-1):
        param["properties"] = self.getEnums("List.Fields.Files", type='items')
        param = {"method":"Files.GetDirectory","params":param}
        if cache: return self.cacheJSON(param, expiration, checksum, timeout).get('result', {})
        else:     return self.sendJSON(param, timeout).get('result', {})
        
        
    def getLibrary(self, method, param={}, cache=True):
        param = {"method":method,"params":param}
        if cache: return self.cacheJSON(param).get('result', {})
        else:     return self.sendJSON(param).get('result', {})


    def getStreamDetails(self, path, media='video'):
        if isStack(path): path = splitStacks(path)[0]
        param = {"method":"Files.GetFileDetails","params":{"file":path,"media":media,"properties":["streamdetails"]}}
        return self.cacheJSON(param, life=datetime.timedelta(days=MAX_GUIDEDAYS), checksum=getMD5(path)).get('result',{}).get('filedetails',{}).get('streamdetails',{})


    def getFileDetails(self, file, media='video', properties=["duration","runtime"]):
        return self.cacheJSON({"method":"Files.GetFileDetails","params":{"file":file,"media":media,"properties":properties}})


    def getViewMode(self):
        default = {"nonlinearstretch":False,"pixelratio":1,"verticalshift":0,"viewmode":"custom","zoom": 1.0}
        return self.cacheJSON({"method":"Player.GetViewMode","params":{}},datetime.timedelta(seconds=FIFTEEN)).get('result',default)
        

    def setViewMode(self, params={}):
        return self.sendJSON({"method":"Player.SetViewMode","params":params})


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


    def getPVRRecordings(self, media='video', cache=True):
        param = {"method":"Files.GetDirectory","params":{"directory":"pvr://recordings/tv/active/","media":media,"properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('files', [])
        else:     return self.sendJSON(param).get('result', {}).get('files', [])

    
    def getPVRSearches(self, media='video', cache=True):
        param = {"method":"Files.GetDirectory","params":{"directory":"pvr://search/tv/savedsearches/","media":media,"properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('files', [])
        else:     return self.sendJSON(param).get('result', {}).get('files', [])
        
        
    def getPVRSearchItems(self, id, media='video', cache=True):
        param = {"method":"Files.GetDirectory","params":{"directory":f"pvr://search/tv/savedsearches/{id}/","media":media,"properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('files', [])
        else:     return self.sendJSON(param).get('result', {}).get('files', [])
    
    
    def getSmartPlaylists(self, type='video', cache=True):
        param = {"method":"Files.GetDirectory","params":{"directory":f"special://profile/playlists/{type}/","media":"video","properties":self.getEnums("List.Fields.Files", type='items')}}
        if cache: return self.cacheJSON(param).get('result', {}).get('files', [])
        else:     return self.sendJSON(param).get('result', {}).get('files', [])
        
        
    def getInfoLabel(self, key, cache=False):
        param = {"method":"XBMC.GetInfoLabels","params":{"labels":[key]}}
        if cache: return self.cacheJSON(param).get('result', {}).get(key)
        else:     return self.sendJSON(param).get('result', {}).get(key)


    def getInfoBool(self, key, cache=False):
        param = {"method":"XBMC.GetInfoBooleans","params":{"booleans":[key]}}
        if cache: return self.cacheJSON(param).get('result', {}).get(key)
        else:     return self.sendJSON(param).get('result', {}).get(key)
    
    
    def _setRuntime(self, item={}, runtime=0, save=SETTINGS.getSettingBool('Store_Duration')): #set runtime collected by player, accurate meta.
        self.cache.set('getRuntime.%s'%(getMD5(item.get('file'))), runtime, checksum=getMD5(item.get('file')), expiration=datetime.timedelta(days=28), json_data=False)
        if not item.get('file','plugin://').startswith(tuple(VFS_TYPES)) and save and runtime > 0: self.queDuration(item, runtime=runtime)
    
        
    def _getRuntime(self, item={}): #get runtime collected by player, else less accurate provider meta
        runtime = self.cache.get('getRuntime.%s'%(getMD5(item.get('file'))), checksum=getMD5(item.get('file')), json_data=False)
        return (runtime or item.get('resume',{}).get('total') or item.get('runtime') or item.get('duration') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration') or 0)
        

    def _setDuration(self, path, item={}, duration=0, save=SETTINGS.getSettingBool('Store_Duration')):#set VideoParser cache
        self.cache.set('getDuration.%s'%(getMD5(path)), duration, checksum=getMD5(path), expiration=datetime.timedelta(days=28), json_data=False)
        if save and item: self.queDuration(item, duration)
        return duration

    
    def _getDuration(self, path): #get VideoParser cache
        return (self.cache.get('getDuration.%s'%(getMD5(path)), checksum=getMD5(path), json_data=False) or 0)


    def getDuration(self, path, item={}, accurate=bool(SETTINGS.getSettingInt('Duration_Type')), save=SETTINGS.getSettingBool('Store_Duration')):
        self.log("getDuration, accurate = %s, path = %s, save = %s" % (accurate, path, save))
        if not item: item = {'file':path}
        runtime = self._getRuntime(item)
        if runtime == 0 or accurate:
            duration = 0
            if isStack(path):# handle "stacked" videos
                for file in splitStacks(path): duration += self.__parseDuration(runtime, file)
            else: duration = self.__parseDuration(runtime, path, item, save)
            if duration > 0: runtime = duration
        self.log("getDuration, returning path = %s, runtime = %s" % (path, runtime))
        return runtime


    def getTotRuntime(self, items=[]):
        total = sum([self._getRuntime(item) for item in items])
        self.log("getTotRuntime, items = %s, total = %s" % (len(items), total))
        return total


    def getTotDuration(self, items=[]):
        total = sum([self.getDuration(item.get('file'),item) for item in items])
        self.log("getTotDuration, items = %s, total = %s" % (len(items), total))
        return total


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
                if save and not path.startswith(tuple(VFS_TYPES)): self.queDuration(item, duration)
        else: runtime = duration
        self.log("__parseDuration, returning runtime = %s" % (runtime))
        return runtime
  
  
    def queDuration(self, item={}, duration=0, runtime=0):
        mtypes = {'video'      : {},
                  'movie'      : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'movies'     : {"method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"     :item.get('movieid',-1)      ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'episode'    : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'episodes'   : {"method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"   :item.get('episodeid',-1)    ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'musicvideo' : {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'musicvideos': {"method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid":item.get('musicvideoid',-1) ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'song'       : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('id',-1)           ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}},
                  'songs'      : {"method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"      :item.get('songid',-1)       ,"runtime": runtime,"resume": {"position": item.get('position',0.0),"total": duration}}}}
        try:
            mtype = mtypes.get(item.get('type'))
            if mtype.get('params'):
                if   duration == 0: mtype['params'].pop('resume')  #save file duration meta
                elif runtime  == 0: mtype['params'].pop('runtime') #save player runtime meta
                id = (item.get('id') or item.get('movieid') or item.get('episodeid') or item.get('musicvideoid') or item.get('songid'))
                self.log('[%s] queDuration, media = %s, duration = %s, runtime = %s'%(id,item['type'],duration,runtime))
                self.queueJSON(mtype['params'])
        except Exception as e: self.log("queDuration, failed! %s\nmtype = %s\nitem = %s"%(e,mtype,item), xbmc.LOGERROR)
        
        
    def quePlaycount(self, item, save=SETTINGS.getSettingBool('Rollback_Watched')):
        param = {'video'      : {},
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
                self.queueJSON(params)
            except: pass


    def requestList(self, citem, path, media='video', page=SETTINGS.getSettingInt('Page_Limit'), sort={}, limits={}, query={}, smart_shuffle=False):
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
        
        if limits.get('end',-1) == -1: #-1 unlimited pagination, replace with autoPagination.
            limits = self.autoPagination(citem['id'], path, query) #get
            self.log('[%s] requestList, autoPagination limits = %s'%(citem['id'],limits))
            if limits.get('total',0) > page and sort.get("method","") == "random":
                limits = self.randomPagination(page,limits)
                self.log('[%s] requestList, generating random limits = %s'%(citem['id'],limits))

        param["limits"]          = {}
        # Removing limits for smart sort to get all episodes.
        if not smart_shuffle:
            param["limits"]["start"] = 0 if limits.get('end', 0) == -1 else limits.get('end', 0)
            param["limits"]["end"]   = abs(limits.get('end', 0) + page)
        param["sort"] = sort
        self.log('[%s] requestList, page = %s\nparam = %s'%(citem['id'], page, param))
        
        if getDirectory:
            results = self.getDirectory(param,timeout=float(SETTINGS.getSettingInt('RPC_Timer')*60))
            if 'filedetails' in results: key = 'filedetails'
            else:                        key = 'files'
        else:
            results = self.getLibrary(query['method'],param, cache=False)
            key = query.get('key',list(results.keys())[0])
            
        items, limits, errors = results.get(key,[]), results.get('limits',param["limits"]), results.get('error',{})
        if (limits.get('end',0) >= limits.get('total',0) or limits.get('start',0) >= limits.get('total',0)):
            # restart page to 0, exceeding boundaries.
            self.log('[%s] requestList, resetting limits to 0'%(citem['id']))
            limits = {"end": 0, "start": 0, "total": limits.get('total',0)}
        if smart_shuffle:
            items = self.smart_random_request(citem['id'], path, items, page, key)

        if len(items) == 0 and limits.get('total',0) > 0:
            # retry last request with fresh limits when no items are returned.
            self.log("[%s] requestList, trying again with start limits at 0"%(citem['id']))
            return self.requestList(citem, path, media, page, sort, {"end": 0, "start": 0, "total": limits.get('total',0)}, query)
        else:          
            self.autoPagination(citem['id'], path, query, limits) #set 
            self.log("[%s] requestList, return items = %s" % (citem['id'], len(items)))
            return items, limits, errors


    def resetPagination(self, id, path, query={}, limits={"end": 0, "start": 0, "total":0}):
        return self.autoPagination(id, path, query, limits)
            
            
    def autoPagination(self, id, path, query={}, limits={}):
        if not limits: return (self.cache.get('autoPagination.%s.%s.%s'%(id,getMD5(path),getMD5(dumpJSON(query))), checksum=id, json_data=True) or {"end": 0, "start": 0, "total":0})
        else:          return  self.cache.set('autoPagination.%s.%s.%s'%(id,getMD5(path),getMD5(dumpJSON(query))), limits, checksum=id, expiration=datetime.timedelta(days=28), json_data=True)
            
             
    def randomPagination(self, page=SETTINGS.getSettingInt('Page_Limit'), limits={}, start=0):
        if limits.get('total',0) > page: start = random.randrange(0, (limits.get('total',0)-page), page)
        return {"end": start, "start": start, "total":limits.get('total',0)}
        
    def smart_random_request(self, id, path, items, page, key=None):
        """Returns a list of random media items from the channel.

        The function takes a list of all media items of the channel and returns a subset of them in a random order.
        Handles mixed content (movies and TV shows) in the same channel.

        Args:
            id (str): Channel identifier
            path (str): Channel path
            items (list): A list containing all media items of the channel
            page (int): Number of items to return
            key (str, optional): Key for grouping items. Defaults to None.
        """
        
        start_time = time.time()
        self.log(f'smart_random_request; {id}: key = {key}', xbmc.LOGINFO)

        total_items = len(items)
        self.log(f'smart_random_request; {id}: {total_items} items.', xbmc.LOGINFO)

        if total_items <= 1:
            return items

        content_dict = self.group_items_by_id(items, key)

        # Create separate lists for movies and TV shows
        library_ids = []
        content_types = {}  # Track content type (movie/tvshow) for each library_id

        for library_id, content_list in content_dict.items():
            # Identify content type based on the presence of 'season' and 'episode' keys
            first_item = content_list[0]
            if 'season' in first_item and 'episode' in first_item:
                content_type = 'episode'
            else:
                content_type = 'movie'
            content_types[library_id] = content_type
            library_ids += [library_id] * len(content_list)
            self.log(f'smart_random_request; Content type for {library_id}: {content_type}', xbmc.LOGDEBUG)
            self.log(f'smart_random_request; Content size for {library_id}: {len(content_type)}', xbmc.LOGDEBUG)

        unique_library_ids = set(library_ids)
        self.log(f'smart_random_request; Unique library IDs: {len(unique_library_ids)}', xbmc.LOGDEBUG)

        # Load next_indices from memory
        channel_memory = self.channelMemory(id, path)
        self.log(f'smart_random_request; Channel memory for {id}: {channel_memory}', xbmc.LOGDEBUG)
        programs_memory = channel_memory.get('programs', {})

        # Clean up old memory entries
        for memory_id in list(programs_memory):
            if memory_id not in library_ids:
                del programs_memory[memory_id]

        next_indices = {}
        coming_next = []

        while len(coming_next) < page:
            next_library_id = random.choice(library_ids)
            content_type = content_types.get(next_library_id, '')
            self.log(f'smart_random_request; {id}, next program id: {next_library_id}, type: {content_type}', xbmc.LOGINFO)
            
            total_parts = len(content_dict[next_library_id])
            last_program_id = channel_memory.get('last_program_id')

            # Skip repeated content if we have other options
            if last_program_id == next_library_id and len(library_ids) > 1:
                # For TV shows, only skip if the show has only 1 episode
                if content_type == 'episode' and len(content_dict[next_library_id]) > 1:
                    # TV show has multiple episodes, so different episodes are allowed
                    pass
                else:
                    self.log(f"smart_random_request, Skipping {next_library_id} as it's the same as the last one.", xbmc.LOGINFO)
                    continue

            if content_type == 'movie':
                # Movie logic - no need for episode tracking
                next_content = content_dict[next_library_id][0]
                programs_memory[next_library_id] = {
                    'type': 'movie',
                    'title': next_content.get('title', ''),
                    'movieid': next_content.get('movieid', -1)
                }
            else:
                # TV Show logic
                i = next_indices.get(next_library_id)
                if i is None:
                    last_remembered_episode = programs_memory.get(next_library_id)
                    if last_remembered_episode is None:
                        self.log(f'No memory for library ID {next_library_id}. Initializing...', xbmc.LOGDEBUG)
                        programs_memory[next_library_id] = {}
                        i = 0
                    else:
                        # Only try to match season/episode if it's actually a TV show
                        if last_remembered_episode.get('type') != 'movie':
                            for i in range(len(content_dict[next_library_id])):
                                current_episode = content_dict[next_library_id][i]
                                if (current_episode.get('seasonid') == last_remembered_episode.get('seasonid') and 
                                    current_episode.get('episodeid') == last_remembered_episode.get('episodeid')):
                                    i += 1
                                    break
                            else:
                                self.log(f"smart_random_request, Resetting index for show {next_library_id}", level=xbmc.LOGINFO)
                                i = 0
                        else:
                            i = 0
                else:
                    i += 1

                if i >= total_parts:
                    self.log(f'smart_random_request, Resetting index as it reached the end of the list (i = {i}/{total_parts})...', xbmc.LOGINFO)
                    i = 0
                
                next_indices[next_library_id] = i
                next_content = content_dict[next_library_id][i]
                programs_memory[next_library_id] = next_content

            # Add the next content to our result list
            coming_next.append(dict(next_content))
            channel_memory['last_program_id'] = next_library_id

        # Update channel memory
        channel_memory['programs'] = programs_memory
        self.channelMemory(id, path, channel_index=channel_memory)

        end_time = time.time()
        self.log(f'smart_random_request; {id}: Time taken to return items: {end_time - start_time:.2f} seconds.', xbmc.LOGINFO)

        return coming_next


    def channelMemory(self, id, path, channel_index = {}, checksum='', life=datetime.timedelta(days=28)):
        """
        Manages the memory cache for a channel with the given ID and path.

        Retrieves or sets the channel's memory index based on the provided parameters.
        If `channel_index` is not provided, attempts to retrieve the existing index from cache.
        Validates the format of the loaded index to ensure it matches the expected structure.
        Logs the status and any exceptions encountered during cache operations.

        Args:
            id (str): Identifier for the channel.
            path (str): Path associated with the channel.
            channel_index (dict, optional): Index of programs for the channel. Defaults to an empty dictionary.
            checksum (str, optional): Checksum for cache validation. Defaults to an empty string.
            life (datetime.timedelta, optional): Expiration time for the cache entry. Defaults to 28 days.

        Returns:
            dict: The channel's memory index, either loaded from cache or newly set.
        """
        cacheName = 'channelMemory.%s.%s'%(id,getMD5(path))
        if not checksum: checksum = id
        if not channel_index:
            msg = 'get'
            channel_index = {'programs' : {}, 'last_program_id' : {}}
            # This gets the starting index for the  request, that's how the program keeps track of episodes.
            try:
                loaded_index = (self.cache.get(cacheName, checksum=checksum, json_data=False) or channel_index)
                # Validating format (in case there's been a cahnge to the format)
                loaded_index_keys = set(loaded_index)
                if loaded_index_keys == set(channel_index):
                    self.log("channelMemory; loaded index keys matched expected format. loaded_index_keys = %s"%(loaded_index_keys))
                    channel_index = loaded_index
                else:
                    self.log("channelMemory; loaded index keys did not match expected format. loaded_index_keys = %s"%(loaded_index_keys))
            except Exception as e:
                self.log(f'channelMemory; Failed loading cache: id = {id}, path = {path}, Error: {e}')
        else:
            msg = 'set'
            self.cache.set(cacheName, channel_index, checksum=checksum, expiration=life, json_data=False)
        self.log("%s channelMemory; id = %s, path = %s, channel_index = %s"%(msg,id,path,channel_index))
        return channel_index


    def group_items_by_id(self, items, key=None):
        """
        Creates a dictionary of programs where each key is a tvshowid
        (or showtitle if tvshowid is -1) and the value is a list of episodes
        sorted by firstaired, season, and episode.

        Parameters:
        items (list): a list of items to be processed into a programs dictionary
        key (str): if key is "episodes", the function will use the tvshowid of each item
            as the key in the programs dictionary, otherwise, it will use the id of the item

        Returns:
        dict: a dictionary of programs where each key is a tvshowid (or showtitle)
            and the value is a list of episodes sorted by firstaired, season, and episode
        """
        # Initialize an empty dictionary to store the programs
        programs = {}

        # Iterate over each item in the provided list
        for item in items:
            # If the key is "episodes" or the type of the item is 'episode'
            if key == "episodes" or item.get('type') == 'episode':
                self.log(f'group_items_by_id; item is an episode: {item}')
                # Set the id as the tvshowid of the item
                id = item['tvshowid']

                # If the tvshowid is -1, set the id as the showtitle of the item
                if id == -1:
                    self.log(f'group_items_by_id; episode tvshowid is -1: {item}!')
                    id = item['showtitle']
            else:
                # If the item is not an episode, set the id as the id of the item
                self.log(f'group_items_by_id; item is not an episode, using "id" for item: {item}')
                id = item.get('id')
                if not id:
                    id = item.get('movieid')
                
            self.log(f'group_items_by_id; id = {id}')



            # Check if there are already episodes for the id in the programs dictionary
            episodes = programs.get(id)
            if episodes == None:
                # If not, add a new entry with the id as the key and a list containing the item as the value
                programs[id] = [item]
            else:
                # If there are already episodes, append the item to the list of episodes
                episodes.append(item)

        # After all items have been processed, sort the items in each list in the programs dictionary
        # by their firstaired, season, and episode values
        for _, items in programs.items():
            items.sort(key=lambda seep: (seep.get('firstaired'), seep.get('season', 0), seep.get('episode', 0)))

        # Return the programs dictionary
        return programs

    @cacheit(checksum=PROPERTIES.getInstanceID())
    def buildWebBase(self, local=False):
        port     = 80
        username = 'kodi'
        password = ''
        secure   = False
        enabled  = True
        settings = self.getSetting('control','services')
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
        webURL =  '{0}://{1}{2}:{3}'.format(protocol,username,ip, port)
        self.log("buildWebBase; returning %s"%(webURL))
        return webURL
            
            
    def padItems(self, files, page=SETTINGS.getSettingInt('Page_Limit')):
        # Balance media limits, by filling with duplicates to meet min. pagination.
        self.log("padItems; files In = %s"%(len(files)))
        if len(files) < page:
            iters = cycle(files)
            while not self.service.monitor.abortRequested() and (len(files) < page and len(files) > 0):
                item = next(iters).copy()
                if   self.service.monitor.waitForAbort(0.0001): break
                elif self.getDuration(item.get('file'),item) == 0:
                    try: files.pop(files.index(item))
                    except: break
                else: files.append(item)
        self.log("padItems; files Out = %s"%(len(files)))
        return files


    def inputFriendlyName(self):
        friendly = self.getSettingValue("services.devicename")
        self.log("inputFriendlyName, name = %s"%(friendly))
        if not friendly or friendly.lower() == 'kodi':
            with PROPERTIES.interruptActivity():
                if DIALOG.okDialog(LANGUAGE(32132)%(friendly)):
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
            results = self.getDirectory(param={"directory":"pvr://channels/{dir}/".format(dir={'True':'radio','False':'tv'}[str(sysInfo.get('radio',False))])}, cache=False).get('files',[])
            for dir in [ADDON_NAME,'All channels']: #todo "All channels" may not work with non-English translations!
                for result in results:
                    if result.get('label','').lower().startswith(dir.lower()):
                        self.log('getCallback: _matchJSON, found dir = %s'%(result.get('file')))
                        channels = self.getDirectory(param={"directory":result.get('file')},checksum=PROPERTIES.getInstanceID(),expiration=datetime.timedelta(minutes=FIFTEEN)).get('files',[])
                        for item in channels:
                            if item.get('label','').lower() == sysInfo.get('name','').lower() and decodePlot(item.get('plot','')).get('citem',{}).get('id') == sysInfo.get('chid'):
                                self.log('[%s] getCallback: _matchJSON, found file = %s'%(sysInfo.get('chid'),item.get('file')))
                                return item.get('file')
                  
        if sysInfo.get('mode','').lower() == 'live' and sysInfo.get('chpath'):
            callback = sysInfo.get('chpath')
        elif sysInfo.get('isPlaylist'):
            callback = sysInfo.get('citem',{}).get('url')
        elif sysInfo.get('mode','').lower() == 'vod' and sysInfo.get('nitem',{}).get('file'):
            callback = sysInfo.get('nitem',{}).get('file')
        else:
            callback = sysInfo.get('callback','')
        if not callback: callback = _matchJSON()
        self.log('getCallback: returning callback = %s'%(callback))
        return callback# or (('%s%s'%(self.sysARG[0],self.sysARG[2])).split('%s&'%(slugify(ADDON_NAME))))[0])
        
        
    def matchChannel(self, chname: str, id: str, radio: bool=False, extend=True):
        self.log('[%s] matchChannel, chname = %s, radio = %s'%(id,chname,radio))
        def __match():
            channels = self.getPVRChannels(radio)
            for channel in channels:
                if channel.get('label','').lower() == chname.lower():
                    for key in ['broadcastnow', 'broadcastnext']:
                        if decodePlot(channel.get(key,{}).get('plot','')).get('citem',{}).get('id') == id:
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
            pvritem['broadcastnext'] = channelItem.get('broadcastnext',pvritem['broadcastnext'])
            self.log('matchChannel: __extend, broadcastnext = %s entries'%(len(pvritem['broadcastnext'])))
            return pvritem
            
        cacheName     = 'matchChannel.%s'%(getMD5('%s.%s.%s.%s'%(chname,id,radio,extend)))
        cacheResponse = (self.cache.get(cacheName, checksum=PROPERTIES.getInstanceID(), json_data=True) or {})
        if not cacheResponse:
            pvrItem = __match()
            if pvrItem:
                if extend: pvrItem = __extend(pvrItem)
                cacheResponse = self.cache.set(cacheName, pvrItem, checksum=PROPERTIES.getInstanceID(), expiration=datetime.timedelta(seconds=FIFTEEN), json_data=True)
            else: return {}
        return cacheResponse
        
        
    def getNextItem(self, citem={}, nitem={}): #return next broadcast ignoring fillers
        if not nitem: nitem = decodePlot(BUILTIN.getInfoLabel('NextPlot','VideoPlayer'))
        nextitems = sorted(self.matchChannel(citem.get('name',''), citem.get('id',''), citem.get('radio',False)).get('broadcastnext',[]), key=itemgetter('starttime'))
        for nextitem in nextitems:
            if not isFiller(nextitem): return decodePlot(nextitem.get('plot',''))
        return nitem
        

    def toggleShowLog(self, state=False):
        self.log('toggleShowLog, state = %s'%(state))
        if SETTINGS.getSettingBool('Enable_PVR_RELOAD'): #check that users allow alternations to kodi.
            opState = not bool(state)
            if self.getSettingValue("debug.showloginfo") == opState:
                self.setSettingValue("debug.showloginfo",state,queue=False)
            