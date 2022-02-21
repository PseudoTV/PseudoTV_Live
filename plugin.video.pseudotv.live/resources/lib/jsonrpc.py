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
from resources.lib.globals     import *
from resources.lib.resource    import Resources
from resources.lib.videoparser import VideoParser

try:    from multiprocessing   import PriorityQueue
except: from queue             import PriorityQueue

class JSONRPC:
    # todo proper dispatch queue with callback to handle multi-calls to rpc. Kodi is known to crash during a rpc collisions. *use concurrent futures and callback.
    # https://codereview.stackexchange.com/questions/219148/json-messaging-queue-with-transformation-and-dispatch-rules

    def __init__(self, inherited=None):
        if inherited is None:
            from resources.lib.parser import Writer
            inherited = Writer()
        
        self.queueRunning = False
        self.writer       = inherited
        self.inherited    = inherited
        self.cache        = inherited.cache
        self.pool         = inherited.pool
        self.dialog       = inherited.dialog
        
        self.sendQueue    = PriorityQueue()
        self.videoParser  = VideoParser()
        self.resources    = Resources(jsonRPC=self)
        
        self.queueThread  = threading.Timer(1.0, self.startQueueWorker)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)


    @cacheit(checksum=xbmc.getInfoLabel('System.BuildVersion'),expiration=datetime.timedelta(days=28),json_data=True)
    def getIntrospect(self, id):
        json_query = ('{"jsonrpc":"2.0","method":"JSONRPC.Introspect","params":{"filter":{"id":"%s","type":"method"}},"id":1}'%(id))
        return self.sendJSON(json_query).get('result',{})


    @cacheit(checksum=xbmc.getInfoLabel('System.BuildVersion'),expiration=datetime.timedelta(days=28),json_data=True)
    def getEnums(self, id, type=''):
        self.log('getEnums id = %s, type = %s' % (id, type))
        json_query = ('{"jsonrpc":"2.0","method":"JSONRPC.Introspect","params": {"getmetadata": true, "filterbytransport": true,"filter": {"getreferences": false, "id":"%s","type":"type"}},"id":1}'%(id))
        json_response = self.sendJSON(json_query).get('result',{}).get('types',{}).get(id,{})
        return (json_response.get(type,{}).get('enums',[]) or json_response.get('enums',[]))


    @cacheit(checksum=getInstanceID(),json_data=True)
    def getPluginMeta(self, plugin):
        return getPluginMeta(plugin)


    def getListDirectory(self, path, checksum=ADDON_VERSION, expiration=datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Max_Days'))):
        self.log('getListDirectory path = %s, checksum = %s'%(path, checksum))
        cacheName = 'getListDirectory.%s'%(path)
        results   = self.cache.get(cacheName, checksum)
        if not results:
            try:    
                results = FileAccess.listdir(path)
                self.cache.set(cacheName, results, checksum, expiration)
            except: 
                results = [],[]
        return results


    def isVFSPlayable(self, path, media='video', chkSeek=True):
        self.log('isVFSPlayable, path = %s, media = %s' % (path, media))
        dirs = []
        json_response = self.requestList({'id':str(random.random())}, path, media)
        for item in json_response:
            file     = item.get('file', '')
            fileType = item.get('filetype', 'file')
            if fileType == 'file':
                item['duration'] = self.getDuration(file, item)
                if   item['duration'] == 0: continue
                elif chkSeek: 
                    item['seek'] = self.isVFSSeekable(file, item['duration'])
                return item
            else: dirs.append(file)
        for dir in dirs: return self.isVFSPlayable(dir, media)


    def isVFSSeekable(self, file, dur):
        if not file.startswith(tuple(VFS_TYPES)): return True
        elif self.inherited.player.isPlaying(): return True
        # todo test seek for support disable via adv. rule if fails.
        # todo set seeklock rule if seek == False  #Player.SeekEnabled todo verify seek
        
        self.dialog.notificationDialog(LANGUAGE(30142))
        liz = xbmcgui.ListItem('Seek Test', path=file)
        seekvalue = int(dur/2)
        liz.setProperty('totaltime'  , str(dur))
        liz.setProperty('resumetime' , str(seekvalue))
        liz.setProperty('startoffset', str(seekvalue))
        self.inherited.player.play(file, liz, windowed=True)
        
        while not self.inherited.monitor.abortRequested() and not self.inherited.player.isPlaying():
            if self.inherited.monitor.waitForAbort(.25): break
                
        state = xbmc.getCondVisibility('Player.SeekEnabled')
        if not state: state = int(self.inherited.player.getTime()) >= seekvalue
        if state: self.dialog.notificationDialog(LANGUAGE(30143))
        self.inherited.player.stop()
        self.log('isVFSSeekable, path = %s, state = %s' % (file, state))
        return state
        

    def sendButton(self, id):
        self.log('sendButton, id = %s'%(id))
        json_query = ('{"jsonrpc":"2.0","method":"Input.ButtonEvent","params":{"button":"%s","keymap":"KB"},"id":1}'%id)
        if 'OK' in self.sendJSON(json_query).get('result',''): return True
        
        
    def sendAction(self, id):
        self.log('sendAction, id = %s'%(id))
        json_query = ('{"jsonrpc":"2.0","method":"Input.ExecuteAction","params":{"action":"%s"},"id":1}'%id)
        if 'OK' in self.sendJSON(json_query).get('result',''):  return True  
            
            
    def openWindow(self, id):
        self.log('openWindow, id = %s'%(id))
        json_query = ('{"jsonrpc":"2.0","method":"GUI.ActivateWindow","params":{"window":"%s"},"id":1}'%id)
        if 'OK' in self.sendJSON(json_query).get('result',''): return True
        
            
    def sendJSON(self, command):
        if self.queueRunning: return self.pool.executor(sendJSON,command)
        else:                 return sendJSON(command)


    def cacheJSON(self, command, life=datetime.timedelta(minutes=15), checksum=ADDON_VERSION):
        cacheName = 'cacheJSON.%s'%(getMD5(dumpJSON(command)))
        cacheResponse = self.inherited.cache.get(cacheName, checksum=checksum, json_data=True)
        if not cacheResponse:
            cacheResponse = self.sendJSON(command)
            if cacheResponse.get('result',None):
                self.inherited.cache.set(cacheName, cacheResponse, checksum=checksum, expiration=life, json_data=True)
        return cacheResponse


    def queueJSON(self, param, heap=5):#heap = 1 top priority, heap = 10 lowest.
        self.sendQueue.put((heap,param))
        self.startQueueThread()
        

    def startQueueThread(self): #start well after buildService.
        if self.queueThread.is_alive(): 
            try: 
                self.queueThread.cancel()
                self.queueThread.join()
            except: pass
        self.queueThread = threading.Timer(900.0, self.startQueueWorker)
        self.queueThread.name = "queueThread"
        self.queueThread.start()


    def startQueueWorker(self):
        self.log('startQueueWorker, starting thread worker')
        self.queueRunning = True
        
        while not self.inherited.monitor.abortRequested():
            if self.inherited.monitor.waitForAbort(1) or self.sendQueue.empty(): break
            try: 
                self.sendJSON(self.sendQueue.get()[1])
            except self.sendQueue.Empty: pass
            except Exception as e: 
                self.log("startQueueWorker, sendQueue Failed! %s"%(e), xbmc.LOGERROR)
                
        self.queueRunning = False
        self.log('startQueueWorker, finishing thread worker')


    def getActivePlaylist(self):
        return 1  # todo


    def getActivePlayer(self, return_item=False):
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1}')
        json_response = self.sendJSON(json_query)
        try:    id = json_response.get('result',[{'playerid':1}])[0].get('playerid',1)
        except: id = 1
        self.log("getActivePlayer, id = %s" % (id))
        if return_item: return item
        return id


    def getPlayerItem(self, playlist=False):
        self.log('getPlayerItem, playlist = %s' % (playlist))
        if playlist: json_query = '{"jsonrpc":"2.0","method":"Playlist.GetItems","params":{"playlistid":%s,"properties":["runtime","title","plot","genre","year","studio","mpaa","season","episode","showtitle","thumbnail","uniqueid","file","customproperties"]},"id":1}'%(self.getActivePlaylist())
        else:        json_query = '{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":%s,"properties":["file","writer","channel","channels","channeltype","mediapath","uniqueid","customproperties"]}, "id": 1}'%(self.getActivePlayer())
        result = self.sendJSON(json_query).get('result', {})
        return (result.get('item', {}) or result.get('items', []))


    def getPVRChannels(self, radio=False):
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetChannels","params":{"channelgroupid":"%s","properties":["icon","channeltype","channelnumber","broadcastnow","broadcastnext","uniqueid"]}, "id": 1}'%({True:'allradio',False:'alltv'}[radio]))
        return self.sendJSON(json_query).get('result', {}).get('channels', [])


    def getPVRBroadcasts(self, id):
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetBroadcasts","params":{"channelid":%s,"properties":["title","plot","starttime","endtime","runtime","progress","progresspercentage","episodename","writer","director"]}, "id": 1}'%(id))
        return self.sendJSON(json_query).get('result', {}).get('broadcasts', [])


    def getResources(self,params='{"type":"kodi.resource.images","properties":["path","name","version","summary","description","thumbnail","fanart","author"]}',cache=True):
        return self.getAddons(params, cache)


    def getAddon(self, addonid=ADDON_ID, params='{"addonid":"%s","properties":["name","version","summary","description","path","author","deprecated","installed","enabled","rating","extrainfo","broken","dependencies","fanart","disclaimer","thumbnail"]}',cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"Addons.GetAddonDetails","params":%s,"id":1}'%(params%(addonid)))
        if cache: return self.cacheJSON(json_query).get('result', {}).get('addon', {})
        else:     return self.sendJSON(json_query).get('result', {}).get('addon', {})


    def getAddons(self,params='{"type":"xbmc.addon.video","enabled":true,"properties":["name","version","description","summary","path","author","thumbnail","disclaimer","fanart","dependencies","extrainfo"]}',cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"Addons.GetAddons","params":%s,"id":1}' % (params))
        if cache: return self.cacheJSON(json_query).get('result', {}).get('addons', [])
        else:     return self.sendJSON(json_query).get('result', {}).get('addons', [])


    def getSongs(self, params='{"properties":["genre"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"AudioLibrary.GetSongs","params":%s,"id":1}' % (params))
        if cache: return self.cacheJSON(json_query).get('result', {}).get('songs', [])
        else:     return self.sendJSON(json_query).get('result', {}).get('songs', [])


    def getTVshows(self, params='{"properties":["title","genre","year","studio","art","file","episode"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":%s,"id":1}' % (params))
        if cache: return self.cacheJSON(json_query).get('result', {}).get('tvshows', [])
        else:     return self.sendJSON(json_query).get('result', {}).get('tvshows', [])


    def getMovies(self, params='{"properties":["title","genre","year","studio","art","file"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":%s,"id":1}' % (params))
        if cache: return self.cacheJSON(json_query).get('result', {}).get('movies', [])
        else:     return self.sendJSON(json_query).get('result', {}).get('movies', [])


    def getDirectory(self, params='', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":%s,"id":1}' % (params))
        if cache: return self.cacheJSON(json_query).get('result', {})
        else:     return self.sendJSON(json_query).get('result', {})


    def getStreamDetails(self, path, media='video'):
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"%s","properties":["streamdetails"]},"id":1}' % ((path), media))
        return self.cacheJSON(json_query, life=datetime.timedelta(days=SETTINGS.getSettingInt('Max_Days')), checksum=getMD5(path)).get('result',{}).get('filedetails',{}).get('streamdetails',{})


    def getFileSize(self, path, media='video', real=False):
        if   path.startswith(tuple(VFS_TYPES)): return 0
        elif real:
            try:
                fle  = FileAccess.open(path,'r')
                size = fle.size()
                fle.close()
                return size
            except Exception as e: 
                self.log("getFileSize, Failed! %s"%(e), xbmc.LOGERROR)
                return 0
        else:
            json_query = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"%s","properties":["size"]},"id":1}' % ((path), media))
            return self.cacheJSON(json_query, life=datetime.timedelta(days=SETTINGS.getSettingInt('Max_Days')), checksum=getMD5(path)).get('result',{}).get('filedetails',{}).get('size',0)
            

    def getSetting(self, category, section):
        json_query = ('{"jsonrpc":"2.0","method":"Settings.GetSettings","params":{"filter":{"category":"%s","section":"%s"}},"id":1}'%(category, section))
        return self.sendJSON(json_query).get('result',{}).get('settings')


    def getSettingValue(self, key):
        json_query = ('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"%s"},"id":1}'%(key))
        return self.sendJSON(json_query).get('result',{}).get('value')


    def setSettingValue(self, key, value):
        json_query = ('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"%s","value":%s},"id":1}'%(key,value))
        return self.queueJSON(json_query,5)


    def getMovieInfo(self, sortbycount=True):
        self.log('getMovieInfo')
        if hasMovie():
            StudioList     = collections.Counter()
            MovieGenreList = collections.Counter()
            json_response  = self.getMovies()

            for info in json_response:
                StudioList.update([studio for studio in info.get('studio', [])])
                MovieGenreList.update([genre for genre in info.get('genre', [])])

            if sortbycount:
                StudioList = [x[0] for x in sorted(StudioList.most_common(25))]
                MovieGenreList = [x[0] for x in sorted(MovieGenreList.most_common(25))]
            else:
                StudioList = (sorted(set(list(StudioList.keys()))))
                del StudioList[250:]
                MovieGenreList = (sorted(set(list(MovieGenreList.keys()))))
                
        else: StudioList = MovieGenreList = []
        self.log('getMovieInfo, studios = %s, genres = %s' % (len(StudioList), len(MovieGenreList)))
        return {'studios':StudioList,'genres':MovieGenreList}


    def getTVInfo(self, sortbycount=True):
        self.log('getTVInfo')
        if hasTV():
            NetworkList   = collections.Counter()
            ShowGenreList = collections.Counter()
            TVShows       = collections.Counter()
            json_response = self.getTVshows()
            
            for info in json_response:
                label = getLabel(info)
                if not label: continue
                TVShows.update({json.dumps({'label': label, 'logo': info.get('art', {}).get('clearlogo', '')}): info.get('episode', 0)})
                NetworkList.update([studio for studio in info.get('studio', [])])
                ShowGenreList.update([genre for genre in info.get('genre', [])])

            if sortbycount:
                TVShows = [json.loads(x[0]) for x in sorted(TVShows.most_common(250))]
                NetworkList = [x[0] for x in sorted(NetworkList.most_common(50))]
                ShowGenreList = [x[0] for x in sorted(ShowGenreList.most_common(25))]
            else:
                TVShows = (sorted(map(json.loads, TVShows.keys()), key=lambda k: k['label']))
                del TVShows[250:]
                NetworkList = (sorted(set(list(NetworkList.keys()))))
                del NetworkList[250:]
                ShowGenreList = (sorted(set(list(ShowGenreList.keys()))))
                
        else: NetworkList = ShowGenreList = TVShows = []
        self.log('getTVInfo, networks = %s, genres = %s, shows = %s' % (len(NetworkList), len(ShowGenreList), len(TVShows)))
        return {'studios':NetworkList,'genres':ShowGenreList,'shows':TVShows}


    def getMusicInfo(self, sortbycount=True):
        if hasMusic():
            MusicGenreList = collections.Counter()
            json_response = self.getSongs()

            for info in json_response:
                MusicGenreList.update([genre for genre in info.get('genre', [])])

            if sortbycount:
                MusicGenreList = [x[0] for x in sorted(MusicGenreList.most_common(25))]
            else:
                MusicGenreList = (sorted(set(list(MusicGenreList.keys()))))
                del MusicGenreList[250:]
                
        else: MusicGenreList = []
        self.log('getMusicInfo, found genres = %s' % (len(MusicGenreList)))
        return {'genres':MusicGenreList}


    def getDuration(self, path, item={}, accurate=None):
        if accurate is None: accurate = bool(SETTINGS.getSettingInt('Duration_Type'))
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


    def parseDuration(self, path, item={}, save=None):
        cacheName = 'parseDuration.%s'%(getMD5(path))
        cacheCHK  = getMD5(path)
        runtime   = int(item.get('runtime', '') or item.get('duration', '') or
                       (item.get('streamdetails', {}).get('video', []) or [{}])[0].get('duration', '') or '0')
                       
        duration  = self.inherited.cache.get(cacheName, checksum=cacheCHK, json_data=False)
        if not duration:
            try:
                duration = self.videoParser.getVideoLength(path.replace("\\\\", "\\"), item)
                if duration > 0:
                    self.inherited.cache.set(cacheName, duration, checksum=cacheCHK, expiration=datetime.timedelta(days=28),json_data=False)
            except Exception as e:
                log("parseDuration, Failed! %s"%(e), xbmc.LOGERROR)
                duration = 0

        ## duration diff. safe guard, how different are the two values? if > 45. don't save to Kodi.
        rundiff = int(percentDiff(runtime, duration))
        runcond = [rundiff <= 45, rundiff != 0, rundiff != 100]
        runsafe = True if not False in runcond else False
        self.log("parseDuration, path = %s, runtime = %s, duration = %s, difference = %s%%, safe = %s" % (path, runtime, duration, rundiff, runsafe))
        ## save parsed duration to Kodi database, if enabled.
        if save is None: save = SETTINGS.getSettingBool('Store_Duration')
        if save and runsafe and (item.get('id', -1) > 0):
            self.queDuration(item['type'], item.get('id', -1), duration)
        if runsafe: runtime = duration
        self.log("parseDuration, returning runtime = %s" % (runtime))
        return runtime
  

    def queDuration(self, media, dbid, dur):
        self.log('queDuration, media = %s, dbid = %s, dur = %s' % (media, dbid, dur))
        param = {'movie'     : '{"jsonrpc": "2.0", "method":"VideoLibrary.SetMovieDetails"     ,"params":{"movieid"      : %i, "runtime" : %i }, "id": 1}' % (dbid, dur),
                 'episode'   : '{"jsonrpc": "2.0", "method":"VideoLibrary.SetEpisodeDetails"   ,"params":{"episodeid"    : %i, "runtime" : %i }, "id": 1}' % (dbid, dur),
                 'musicvideo': '{"jsonrpc": "2.0", "method":"VideoLibrary.SetMusicVideoDetails","params":{"musicvideoid" : %i, "runtime" : %i }, "id": 1}' % (dbid, dur),
                 'song'      : '{"jsonrpc": "2.0", "method":"AudioLibrary.SetSongDetails"      ,"params":{"songid"       : %i, "runtime" : %i }, "id": 1}' % (dbid, dur)}
        try: self.queueJSON(param[media],10)
        except Exception as e:
            log("queDuration, Failed! %s"%(e), xbmc.LOGERROR)
        
        
    def autoPagination(self, id, path, limits={}, checksum='', life=datetime.timedelta(days=28)):
        cacheName = 'autoPagination.%s.%s'%(id,getMD5(path))
        if not checksum: checksum = id
        if not limits:
            msg = 'get'
            limits = (self.cache.get(cacheName, checksum=checksum, json_data=True) or {"end": 0, "start": 0, "total":0})
        else:
            msg = 'set'
            self.cache.set(cacheName, limits, checksum=checksum, expiration=life, json_data=True)
        self.log("%s autoPagination; id = %s, path = %s, limits = %s"%(msg,id,path,limits))
        return limits
            
             
    def randomPagination(self, page, total=0):
        if total > 0: start = random.randrange(0, total, page)
        else:         start = 0
        end = start + page
        if end > total: end = total
        return {"end": end, "start": start, "total":total}
      

    def requestList(self, citem, path, media='video', page=PAGE_LIMIT, sort={}, filter={}, limits={}):
        # if self.writer.__class__.__name__ != 'Writer':
            # from resources.lib.parser import Writer
            # self.writer = Writer()

        # todo use adv. channel rules to set autoPagination cache expiration & checksum to force refresh times.
        id = citem['id']
        if not limits: 
            limits = self.autoPagination(id, path) #get
            total  = limits.get('total',0)
            if total > page and sort.get("method","") == "random" and not path.startswith(tuple(VFS_TYPES)):
                limits = self.randomPagination(page,total)
                self.log('requestList, id = %s generating random limits = %s'%(id,limits))
            
        params                      = {}
        params['limits']            = {}
        params['directory']         = escapeDirJSON(path)
        params['media']             = media
        params['properties']        = self.getEnums(id="List.Fields.Files", type='items')
        params['limits']['start']   = limits.get('end', 0)
        params['limits']['end']     = limits.get('end', 0) + page

        if sort:   params['sort']   = sort
        if filter: params['filter'] = filter

        self.log('requestList, id = %s, path = %s, page = %s, limits= %s'%(id, path, page, limits))
        results = self.getDirectory(dumpJSON(params))
        
        if 'filedetails' in results: key = 'filedetails'
        else:                        key = 'files'
            
        items  = results.get(key, [])
        # files  = list(filter(lambda f:f['filetype'] == 'file',items))
        # dirs   = list(filter(lambda f:f['filetype'] == 'directory',items))
        limits = results.get('limits', params['limits'])
        total  = limits.get('total',0)
        self.log('requestList, id = %s, items = %s, result limits = %s'%(id, len(items), limits))
        
        # restart page to 0, exceeding boundaries.
        if (limits.get('end',0) >= total or limits.get('start',0) > total):
            self.log('requestList, id = %s, resetting start to 0'%(id))
            limits = {"end": 0, "start": 0, "total": limits.get('total',0)}
            
        # retry request
        if (len(items) == 0 and total > 0) and not path.startswith(tuple(VFS_TYPES)):
            self.log("requestList, id = %s, trying again with start at 0"%(id))
            limits = {"end": 0, "start": 0, "total": limits.get('total',0)}
            return self.requestList(citem, path, media, page, sort, filter, limits)
            
        self.autoPagination(id, path, limits) #set 
        self.log("requestList, id = %s, return items = %s" % (id, len(items)))
        return items


    def matchPVRPath(self, channelid=-1):
        self.log('matchPVRPath, channelid = %s' % (channelid))
        pvrPaths = ['pvr://channels/tv/%s/'%(quote(ADDON_NAME)),
                    'pvr://channels/tv/All%20channels/',
                    'pvr://channels/tv/*']

        for path in pvrPaths:
            json_response = self.getDirectory('{"directory":"%s","properties":["file"]}'%(path), cache=False).get('files', [])
            if not json_response: continue
            item = list(filter(lambda k: k.get('id',random.random()) == channelid, json_response))
            if item:
                self.log('matchPVRPath, path found: %s'%(item[0].get('file','')))
                return item[0].get('file', '')
        self.log('matchPVRPath, path not found \n%s' % (dumpJSON(json_response)))
        return ''