#   Copyright (C) 2020 Lunatixz
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
from resources.lib.resources   import Resources
from resources.lib.videoparser import VideoParser


class Worker(BaseWorker):
    def do_sendJSON(self, param):
        log('Worker: do_sendJSON, param = %s'%(param))
        sendJSON(param)
     
     
class JSONRPC:
    def __init__(self, cache=None, builder=None):
        self.log('__init__')
        if cache is None:
            self.cache = Cache()
        else: 
            self.cache = cache
            
        self.myPlayer      = MY_PLAYER
        self.myMonitor     = MY_MONITOR
        self.myProcess     = Worker()
        
        if builder is None:
            from resources.lib.parser import Writer
            self.writer    = Writer(cache=self.cache)
        else:
            self.writer    = builder.writer
        self.dialog        = self.writer.dialog
        
        self.pool          = PoolHelper()
        self.videoParser   = VideoParser()
        self.resources     = Resources(self)
        self.processThread = threading.Timer(15.0, self.myProcess.start)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
        
    def startProcess(self):
        #thread egg-timer, start on last call.
        if self.processThread.is_alive():
            self.processThread.cancel()
            self.processThread.join()
        self.processThread = threading.Timer(30.0, self.myProcess.start)
        self.processThread.name = "processThread"
        self.processThread.start()


    def getLogo(self, name, type=LANGUAGE(30171), path=None, item=None, featured=False):
        return self.resources.getLogo(name,type,path,item,featured)
        
        
    @cacheit()
    def getPluginMeta(self, plugin):
        return getPluginMeta(plugin)


    @cacheit()
    def getListDirectory(self, path, version=ADDON_VERSION):
        self.log('getListDirectory path = %s, version = %s'%(path,version))
        try:    return FileAccess.listdir(path)
        except: return [],[]


    def listVFS(self, path, media='video', force=False, version=ADDON_VERSION):
        self.log('listVFS path = %s, version = %s'%(path,version))
        json_response = self.getDirectory('{"directory":"%s","media":"%s","properties":["duration","runtime"]}'%(path,media),cache=False).get('files',[])
        files = []
        for item in json_response:
            file = item['file']
            if item['filetype'] == 'file':
                dur = self.parseDuration(file, item)
                if dur == 0 and not force: continue
                files.append({'label':item['label'],'duration':dur,'path':path,'file':file})
            else: files.extend(self.listVFS(file,media,force,version))
        return files


    def playableVFS(self, path, media='video', chkSeek=False):
        self.log('playableVFS, path = %s, media = %s'%(path,media))
        dirs  = []
        json_response = self.requestList(str(random.random()), path, media)
        for item in json_response:
            file     = item.get('file','')
            fileType = item.get('filetype','file')
            if fileType == 'file':
                dur = self.getDuration(file, item)
                vfs = {'file':file,'duration':dur}
                if chkSeek: vfs['seek'] = self.chkSeeking(file, dur)
                if dur > 0: return vfs
            else: dirs.append(file)
        for dir in dirs: return self.playableVFS(dir, media)
        return {}


    def cacheJSON(self, command, life=datetime.timedelta(minutes=15)):
        cacheName = 'cacheJSON.%s'%(command)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            cacheResponse = sendJSON(command)
            self.cache.set(cacheName, cacheResponse, expiration=life)
        return cacheResponse


    def getActivePlayer(self, return_item=False):
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1}')
        json_response = (sendJSON(json_query))
        item = json_response.get('result',[])
        if item: id = item[0].get('playerid',1)
        else:    id = 1 #guess
        self.log("getActivePlayer, id = %s"%(id))
        if return_item: return item
        return id
        
        
    def getPlayerItem(self, playlist=False):
        self.log('getPlayerItem, playlist = %s'%(playlist))
        if playlist: json_query = '{"jsonrpc":"2.0","method":"Playlist.GetItems","params":{"playlistid":%s,"properties":["runtime","title","plot","genre","year","studio","mpaa","season","episode","showtitle","thumbnail","file"]},"id":1}'%(self.getActivePlaylist())
        else:        json_query = '{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":%s,"properties":["file","writer","channel","channels","channeltype","mediapath"]}, "id": 1}'%(self.getActivePlayer())
        result = sendJSON(json_query).get('result',{})
        return (result.get('item',{}) or result.get('items',{}))
           

    def getPVRChannels(self, radio=False):
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetChannels","params":{"channelgroupid":"%s","properties":["icon","channeltype","channelnumber","broadcastnow","broadcastnext"]}, "id": 1}'%({True:'allradio',False:'alltv'}[radio]))
        return sendJSON(json_query).get('result',{}).get('channels',[])

        
    def getPVRBroadcasts(self, id):
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetBroadcasts","params":{"channelid":%s,"properties":["title","plot","starttime","runtime","progress","progresspercentage","episodename","writer","director"]}, "id": 1}'%(id))
        return sendJSON(json_query).get('result',{}).get('broadcasts',[])
        
        
    def getResources(self, params='{"type":"kodi.resource.images","properties":["path","name","version","summary","description","thumbnail","fanart","author"]}', cache=True):
        return self.getAddons(params,cache)

        
    def getAddons(self, params='{"type":"xbmc.addon.video","enabled":true,"properties":["name","version","description","summary","path","author","thumbnail","disclaimer","fanart","dependencies","extrainfo"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"Addons.GetAddons","params":%s,"id":1}'%(params))
        if cache: return self.cacheJSON(json_query).get('result',{}).get('addons',[])
        else:     return sendJSON(json_query).get('result',{}).get('addons',[])
        
        
    def getSongs(self, params='{"properties":["genre"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"AudioLibrary.GetSongs","params":%s,"id":1}'%(params))
        if cache: return self.cacheJSON(json_query,life=datetime.timedelta(days=getSettingInt('Max_Days'))).get('result',{}).get('songs',[])
        else:     return sendJSON(json_query).get('result',{}).get('songs',[])


    def getTVshows(self, params='{"properties":["title","genre","year","studio","art","file"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":%s,"id":1}'%(params))
        if cache: return self.cacheJSON(json_query,life=datetime.timedelta(hours=getSettingInt('Max_Days'))).get('result',{}).get('tvshows',[])
        else:     return sendJSON(json_query).get('result',{}).get('tvshows',[])
        
        
    def getMovies(self, params='{"properties":["title","genre","year","studio","art","file"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":%s,"id":1}'%(params))
        if cache: return self.cacheJSON(json_query,life=datetime.timedelta(days=getSettingInt('Max_Days'))).get('result',{}).get('movies',[])
        else:     return sendJSON(json_query).get('result',{}).get('movies',[])


    def getDirectory(self, params='', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":%s,"id":1}'%(params))
        if cache: return self.cacheJSON(json_query,life=datetime.timedelta(days=getSettingInt('Max_Days'))).get('result',{})
        else:     return sendJSON(json_query).get('result',{})
        
        
    def getStreamDetails(self, path, media='video'):
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"%s","properties":["streamdetails"]},"id":1}'%((path),media))
        return self.cacheJSON(json_query, life=datetime.timedelta(days=getSettingInt('Max_Days'))).get('result',{}).get('filedetails',{}).get('streamdetails',{})
        
        
    def getSettingValue(self, params=''):
        json_query = ('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":%s,"id":1}'%(params))
        return sendJSON(json_query)
        
        
    def setSettingValue(self, params=''):
        json_query = ('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":%s,"id":1}'%(params))
        return sendJSON(json_query)
    

    def setDuration(self, media, dbid, dur):
        self.startProcess()
        self.log('setDuration, media = %s, dbid = %s, dur = %s'%(media, dbid, dur))
        param = {'movie'  :'{"jsonrpc": "2.0", "method":"VideoLibrary.SetMovieDetails"  ,"params":{"movieid"   : %i, "runtime" : %i }, "id": 1}'%(dbid,dur),
                 'episode':'{"jsonrpc": "2.0", "method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid" : %i, "runtime" : %i }, "id": 1}'%(dbid,dur)}
        self.myProcess.send('sendJSON', param[media])

        
    def chkSeeking(self, file, dur):
        if not file.startswith(('plugin://','upnp://')): return True
        #todo test seek for support disable via adv. rule if fails.
        self.dialog.notificationDialog(LANGUAGE(30142))
        liz = xbmcgui.ListItem('Seek Test',path=file)
        playpast = False
        progress = int(dur/2)
        liz.setProperty('totaltime'  , str(dur))
        liz.setProperty('resumetime' , str(progress))
        liz.setProperty('startoffset', str(progress))
        liz.setProperty("IsPlayable" , "true")
        if self.myPlayer.isPlaying(): return True #todo prompt to stop playback and test.
        self.myPlayer.play(file,liz,windowed=True)
        while not self.myMonitor.abortRequested():
            self.log('chkSeeking seeking')
            if self.myMonitor.waitForAbort(2): break
            elif not self.myPlayer.isPlaying(): break
            if int(self.myPlayer.getTime()) > progress:
                self.log('chkSeeking seeking complete')
                playpast = True
                break
        while not self.myMonitor.abortRequested() and self.myPlayer.isPlaying():
            if self.myMonitor.waitForAbort(1): break
            self.log('chkSeeking stopping playback')
            self.myPlayer.stop()
        msg = LANGUAGE(30143) if playpast else LANGUAGE(30144)
        self.log('chkSeeking file = %s %s'%(file,msg))
        self.dialog.notificationDialog(msg)
        return playpast


    def getMovieInfo(self, sortbycount=True):
        self.log('getMovieInfo')
        if not hasMovie(): return [], []
        cacheName     = 'getMovieInfo.%s'%(sortbycount)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            StudioList     = collections.Counter()
            MovieGenreList = collections.Counter()
            json_response  = self.getMovies(cache=False)
            for info in json_response:
                StudioList.update([studio for studio in info.get('studio',[])])
                MovieGenreList.update([genre for genre in info.get('genre' ,[])])
            if sortbycount: 
                StudioList     = [x[0] for x in sorted(StudioList.most_common(25))]
                MovieGenreList = [x[0] for x in sorted(MovieGenreList.most_common(25))]
            else:
                StudioList     = (sorted(set(list(StudioList.keys()))))
                del StudioList[250:]
                MovieGenreList = (sorted(set(list(MovieGenreList.keys()))))
                
            cacheResponse  = {'StudioList':StudioList, 
                              'MovieGenreList':MovieGenreList}
            self.cache.set(cacheName, cacheResponse, expiration=datetime.timedelta(days=getSettingInt('Max_Days')))
        else:
            StudioList     = cacheResponse.get('StudioList')
            MovieGenreList = cacheResponse.get('MovieGenreList')
        self.log('getMovieInfo, studios = %s, genres = %s'%(len(StudioList),len(MovieGenreList)))
        return StudioList, MovieGenreList
        
        
    def getTVInfo(self, sortbycount=True, art='poster'):
        self.log('getTVInfo')
        if not hasTV(): return [], [], []
        cacheName     = 'getTVInfo.%s.%s'%(sortbycount,art)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            NetworkList   = collections.Counter()
            ShowGenreList = collections.Counter()
            TVShows       = []
            json_response = self.getTVshows(cache=False)
            for info in json_response:
                label = getLabel(info)
                if not label: continue
                TVShows.append({'label':label,'item':info,'logo':info.get('art',{}).get(art,'')})
                NetworkList.update([studio  for studio in info.get('studio',[])])
                ShowGenreList.update([genre for genre  in info.get('genre' ,[])])
            if sortbycount: 
                NetworkList   = [x[0] for x in sorted(NetworkList.most_common(50))]
                ShowGenreList = [x[0] for x in sorted(ShowGenreList.most_common(25))]
            else:
                NetworkList   = (sorted(set(list(NetworkList.keys()))))
                del NetworkList[250:]
                ShowGenreList = (sorted(set(list(ShowGenreList.keys()))))
            TVShows = (sorted(TVShows, key=lambda k: k['label']))
            
            cacheResponse = {'NetworkList':NetworkList,
                             'ShowGenreList':ShowGenreList,
                             'TVShows':TVShows}
            self.cache.set(cacheName, cacheResponse, expiration=datetime.timedelta(hours=getSettingInt('Max_Days')))
        else:
            NetworkList   = cacheResponse.get('NetworkList')
            ShowGenreList = cacheResponse.get('ShowGenreList')
            TVShows       = cacheResponse.get('TVShows')
        self.log('getTVInfo, networks = %s, genres = %s, shows = %s'%(len(NetworkList),len(ShowGenreList),len(TVShows)))
        return NetworkList, ShowGenreList, TVShows


    def getMusicInfo(self, sortbycount=True):
        if not hasMusic(): return []
        cacheName     = 'getMusicInfo.%s'%(sortbycount)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            MusicGenreList = collections.Counter()
            json_response  = self.getSongs(cache=False)
            for info in json_response:
                MusicGenreList.update([genre for genre in info.get('genre',[])])
            if sortbycount: 
                MusicGenreList = [x[0] for x in sorted(MusicGenreList.most_common(25))]
            else:           
                MusicGenreList = (sorted(set(list(MusicGenreList.keys()))))
                del MusicGenreList[250:]
                
            cacheResponse = {'MusicGenreList':MusicGenreList}
            self.cache.set(cacheName, cacheResponse, expiration=datetime.timedelta(days=getSettingInt('Max_Days')))
        else:
            MusicGenreList = cacheResponse.get('MusicGenreList')
        self.log('getMusicInfo, found genres = %s'%(len(MusicGenreList)))
        return MusicGenreList


    def getDuration(self, path, item={}, accurate=None):
        if accurate is None: accurate = bool(getSettingInt('Duration_Type'))
        self.log("getDuration, accurate = %s, path = %s"%(accurate,path))
        duration = 0
        runtime  = int(item.get('runtime','') or item.get('duration','') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration','') or '0')
        if (runtime == 0 | accurate):
            if path.startswith(('plugin://','upnp://','pvr://')): #no additional parsing needed item(runtime) has only meta available.
                duration = 0
            elif isStack(path): #handle "stacked" videos:
                paths = splitStacks(path)
                for file in paths: duration += self.parseDuration(file)
            else: duration = self.parseDuration(path, item)
            if duration > 0: runtime = duration
        self.log("getDuration, path = %s, runtime = %s"%(path,runtime))
        return runtime 
        
        
    def parseDuration(self, path, item={}, save=None):
        cacheName = '%s.parseDuration.%s'%(ADDON_ID,path)#by providing ADDON_ID here, bypassing version render in cache.py. Cache safe between upgrades.
        duration  = self.cache.get(cacheName)
        runtime   = int(item.get('runtime','') or item.get('duration','') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration','') or '0')
        if not duration:
            try:
                duration = self.videoParser.getVideoLength(path.replace("\\\\", "\\"),item)
                self.cache.set(cacheName, duration, expiration=datetime.timedelta(days=28))
            except Exception as e: 
                log("parseDuration, Failed! " + str(e), xbmc.LOGERROR)
                duration = 0
                
        ## duration diff. safe guard, how different are the two values? if > 45. don't save to Kodi.
        rundiff = int(percentDiff(runtime,duration))
        runsafe = (rundiff <= 45 and (rundiff != 0 or rundiff != 100))
        self.log("parseDuration, path = %s, runtime = %s, duration = %s, difference = %s, safe = %s"%(path,runtime,duration,rundiff,runsafe))
        ## save parsed duration to Kodi database, if enabled.
        if save is None: save = getSettingBool('Store_Duration')
        if save and runsafe and (item.get('id',-1) > 0):
            self.setDuration(item['type'], item.get('id',-1), duration)
        if runsafe: runtime = duration
        self.log("parseDuration, returning runtime = %s"%(runtime))
        return runtime
       
       
    def requestList(self, id, path, media='video', page=PAGE_LIMIT, sort={}, filter={}, limits={}):
        limits = self.writer.autoPagination(id, path, limits)
        params                      = {}
        params['limits']            = {}
        params['directory']         = escapeDirJSON(path)
        params['media']             = media
        params['properties']        = JSON_FILE_ENUM
        params['limits']['start']   = limits.get('end',0)
        params['limits']['end']     = limits.get('end',0) + page
        
        if sort:   params['sort']   = sort
        if filter: params['filter'] = filter
        
        self.log('requestList, id = %s, path = %s, params = %s, page = %s'%(id,path,params,page))
        results = self.getDirectory(dumpJSON(params))
        if 'filedetails' in results: key = 'filedetails'
        else:                        key = 'files'
            
        items   = results.get(key,[])
        limits  = results.get('limits',params['limits'])
        self.log('requestList, id = %s, response items = %s, key = %s, limits = %s'%(id,len(items),key,limits))
        
        if limits.get('end',0) >= limits.get('total',0): # restart page, exceeding boundaries.
            self.log('requestList, id = %s, resetting page to 0'%(id))
            limits = {"end": 0, "start": 0, "total": limits.get('total',0)}
        self.writer.autoPagination(id, path, limits)
        
        if len(items) == 0 and limits.get('start',0) > 0 and limits.get('total',0) > 0:
            self.log("requestList, id = %s, trying again at start page 0"%(id))
            return self.requestList(id, path, media, page, sort, filter, limits)
        self.log("requestList, id = %s, return items = %s"%(id,len(items)))
        return items
        
        
    def matchPVRPath(self, channelid=-1):
        self.log('matchPVRPath, channelid = %s'%(channelid))
        pvrPaths = ['pvr://channels/tv/%s/'%(urllib.parse.quote(ADDON_NAME)),
                    'pvr://channels/tv/All%20channels/',
                    'pvr://channels/tv/*']
                    
        for path in pvrPaths:
            json_response = self.getDirectory('{"directory":"%s","properties":["file"]}'%(path),cache=False).get('files',[])
            if not json_response: continue
            item = list(filter(lambda k:k.get('id',-1) == channelid, json_response))
            if item: 
                self.log('matchPVRPath, path found: %s'%(item[0].get('file','')))
                return item[0].get('file','')
        self.log('matchPVRPath, path not found \n%s'%(dumpJSON(json_response)))
        return ''
        
        
    def matchPVRChannel(self, chname, id, radio=False): # Convert PseudoTV Live channelID into a Kodi channelID for playback
        try: 
            channels = self.getPVRChannels(radio)
            for channel in channels:
                if channel.get('label') == chname:
                    for key in ['broadcastnow','broadcastnext']:
                        writer = getWriter(channel.get(key,{}).get('writer',''))
                        citem  = writer.get('citem',{}) 
                        if citem.get('id','') == id:
                            log('matchPVRChannel, match found! id = %s'%(id))
                            return channel
            return {}
        except Exception as e: 
            log("matchPVRChannel, chname = %s, id = %s failed! %s\n%s"%(chname,id,e,channels), xbmc.LOGERROR)
            return {}
        
        
    def fillPVRbroadcasts(self, channelItem):
        channelItem['broadcastnext'] = []
        json_response = self.getPVRBroadcasts(channelItem['channelid'])
        for idx, item in enumerate(json_response):
            if item['progresspercentage'] == 100: continue
            elif item['progresspercentage'] > 0: 
                broadcastnow = channelItem['broadcastnow']
                channelItem.pop('broadcastnow')
                item.update(broadcastnow) 
                channelItem['broadcastnow'] = item
            elif item['progresspercentage'] == 0: 
                channelItem['broadcastnext'].append(item)
        self.log('fillPVRbroadcasts, found broadcastnext = %s'%(len(channelItem['broadcastnext'])))
        return channelItem
        
        
    def getPVRposition(self, chname, id, radio=False, isPlaylist=False):
        self.log('getPVRposition, chname = %s, id = %s, isPlaylist = %s'%(chname,id,isPlaylist))
        channelItem = self.matchPVRChannel(chname, id, radio)
        channelItem['citem'] = {'name':chname,'id':id,'radio':radio}
        channelItem['isPlaylist'] = isPlaylist
        if isPlaylist: channelItem = self.fillPVRbroadcasts(channelItem)
        else:          channelItem['broadcastnext'] = [channelItem.get('broadcastnext',[])]
        return channelItem