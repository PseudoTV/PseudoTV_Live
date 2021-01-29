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
from resources.lib.worker      import BaseWorker
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
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.myPlayer      = MY_PLAYER
        self.myMonitor     = MY_MONITOR
        self.myProcess     = Worker()
        
        if builder is None:
            from resources.lib.parser import Writer
            self.writer    = Writer(self.cache)
        else:
            self.writer    = builder.writer
        
        self.videoParser   = VideoParser()
        
        self.resources     = Resources(self.cache, self)
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
        
        
    @use_cache(1)
    def getPluginMeta(self, plugin):
        return getPluginMeta(plugin)


    @use_cache(28)
    def getListDirectory(self, path, version=ADDON_VERSION):
        self.log('getListDirectory path = %s, version = %s'%(path,version))
        try:    return FileAccess.listdir(path)
        except: return [],[]


    @use_cache(1)
    def listVFS(self, path, version=None):
        self.log('listVFS path = %s, version = %s'%(path,version))
        json_response = self.getDirectory('{"directory":"%s","properties":["duration","runtime"]}'%(path),cache=False)
        dirs, files = [[],[]]
        for item in json_response:
            file = item['file']
            if item['filetype'] == 'file':
                duration = self.parseDuration(file, item)
                if duration == 0: continue
                files.append({'label':item['label'],'duration':duration,'file':file})
            else: dirs.append(file)
        return dirs, files


    @use_cache(1) # check for duration data.
    def existsVFS(self, path, media='video'):
        self.log('existsVFS path = %s, media = %s'%(path,media))
        dirs  = []
        json_response = self.requestList(str(random.random()), path, media)
        for item in json_response:
            file = item.get('file','')
            fileType = item.get('filetype','file')
            if fileType == 'file':
                dur = self.getDuration(file, item)
                if dur > 0: return {'file':file,'duration':dur,'seek':self.chkSeeking(file, dur)}
            else: dirs.append(file)
        for dir in dirs: return self.existsVFS(dir, media)
        return None


    def cacheJSON(self, command, life=datetime.timedelta(minutes=29)):
        cacheName = '%s.cacheJSON.%s'%(ADDON_ID,command)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            cacheResponse = dumpJSON(sendJSON(command))
            self.cache.set(cacheName, cacheResponse, checksum=len(cacheResponse), expiration=life)
        return loadJSON(cacheResponse)
        
        
    def getActivePlayer(self, return_item=False):
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1}')
        json_response = (sendJSON(json_query))
        item = json_response.get('result',[])
        if item: 
            id = item[0].get('playerid',1)
        else: 
            self.log("getActivePlayer, Failed! no results")
            id = 1 #guess
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


    def getAddons(self, params='{"type":"xbmc.addon.video","enabled":true,"properties":["name","version","description","summary","path","author","thumbnail","disclaimer","fanart","dependencies","extrainfo"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"Addons.GetAddons","params":%s,"id":1}'%(params))
        if cache: 
            return self.cacheJSON(json_query).get('result',{}).get('addons',[])
        else:     
            return sendJSON(json_query).get('result',{}).get('addons',[])
        
        
    def getSongs(self, params='{"properties":["genre"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"AudioLibrary.GetSongs","params":%s,"id":1}'%(params))
        if cache: return self.cacheJSON(json_query).get('result',{}).get('songs',[])
        else:     return sendJSON(json_query).get('result',{}).get('songs',[])


    def getTVshows(self, params='{"properties":["title","genre","year","studio","art","file"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":%s,"id":1}'%(params))
        if cache: return (self.cacheJSON(json_query)).get('result',{}).get('tvshows',[])
        else:     return sendJSON(json_query).get('result',{}).get('tvshows',[])
        
        
    def getMovies(self, params='{"properties":["title","genre","year","studio","art","file"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovies","params":%s,"id":1}'%(params))
        if cache: return (self.cacheJSON(json_query)).get('result',{}).get('movies',[])
        else:     return sendJSON(json_query).get('result',{}).get('movies',[])


    def getDirectory(self, params='', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":%s,"id":1}'%(params))
        if cache: return self.cacheJSON(json_query)
        else:     return sendJSON(json_query)
        
        
    def getStreamDetails(self, path, media='video'):
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"%s","properties":["streamdetails"]},"id":1}'%((path),media))
        return self.cacheJSON(json_query, life=datetime.timedelta(days=7)).get('result',{}).get('filedetails',{}).get('streamdetails',{})
        
        
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
        notificationDialog(LANGUAGE(30142))
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
        notificationDialog(msg)
        return playpast

        
    def getMovieInfo(self, sortbycount=False):
        self.log('getMovieInfo')
        tmpStudios     = []
        StudioList     = []
        MovieGenreList = []
        if not hasMovie(): return StudioList, MovieGenreList
        
        json_response = self.getMovies()
        for info in json_response:
            genres = info.get('genre','')
            if genres:
                for genre in genres:
                    found = False
                    for g in range(len(MovieGenreList)):
                        itm = MovieGenreList[g]
                        if sortbycount: itm = itm[0]
                        if genre.lower() == itm.lower():
                            found = True
                            if sortbycount: MovieGenreList[g][1] += 1
                            break
                            
                    if not found:
                        if sortbycount: MovieGenreList.append([genre.replace('"','').strip(), 1])
                        else: MovieGenreList.append(genre.replace('"','').strip())

            studios = info.get('studio','')
            if studios:
                for studio in studios:
                    found = False
                    for i in range(len(tmpStudios)):
                        if tmpStudios[i][0].lower() == studio.lower():
                            tmpStudios[i][1] += 1
                            found = True
                            break
                    if found == False and len(studio) > 0: tmpStudios.append([studio, 1])

        maxcount = 0
        for i in range(len(tmpStudios)):
            if tmpStudios[i][1] > maxcount: maxcount = tmpStudios[i][1]

        bestmatch = 1
        lastmatch = 1000
        counteditems = 0

        for i in range(maxcount, 0, -1):
            itemcount = 0
            for j in range(len(tmpStudios)):
                if tmpStudios[j][1] == i: itemcount += 1
            if abs(itemcount + counteditems - 8) < abs(lastmatch - 8):
                bestmatch = i
                lastmatch = itemcount
            counteditems += itemcount

        if sortbycount:
            tmpStudios.sort(key=lambda x: x[1], reverse=True)
            MovieGenreList.sort(key=lambda x: x[1], reverse=True)
        else:
            tmpStudios.sort(key=lambda x: x[0].lower())
            MovieGenreList.sort(key=lambda x: x.lower())

        for i in range(len(tmpStudios)):
            if tmpStudios[i][1] >= bestmatch:
                if sortbycount: StudioList.append([tmpStudios[i][0], tmpStudios[i][1]])
                else: StudioList.append(tmpStudios[i][0])
        self.log('getMovieInfo, studios = %s, genres = %s'%(len(StudioList),len(MovieGenreList)))
        return StudioList, MovieGenreList


    def getTVInfo(self, sortbycount=False):
        self.log('getTVInfo')
        NetworkList   = []
        ShowGenreList = []
        if not hasTV(): return NetworkList, ShowGenreList
        #todo group/ignore networks with region marker ex. NBC (US)
        json_response = self.getTVshows()
        for info in json_response:
            networks = info.get('studio','')
            if networks:
                for network in networks:
                    found = False
                    for n in range(len(NetworkList)):
                        itm = NetworkList[n]
                        if sortbycount: itm = itm[0]
                        if network.lower() == itm.lower():
                            found = True
                            if sortbycount: NetworkList[n][1] += 1
                            break
                            
                    if found == False:
                        if sortbycount: NetworkList.append([network, 1])
                        else: NetworkList.append(network)

            genres = info.get('genre','')
            if genres:
                for genre in genres:
                    found = False
                    for g in range(len(ShowGenreList)):
                        itm = ShowGenreList[g]
                        if sortbycount: itm = itm[0]
                        if genre.lower() == itm.lower():
                            found = True
                            if sortbycount: ShowGenreList[g][1] += 1
                            break
                            
                    if found == False:
                        if sortbycount: ShowGenreList.append([genre, 1])
                        else: ShowGenreList.append(genre)

        if sortbycount:
            NetworkList.sort(key=lambda x: x[1], reverse = True)
            ShowGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            NetworkList.sort(key=lambda x: x.lower())
            ShowGenreList.sort(key=lambda x: x.lower())
        self.log('getTVInfo, networks = %s, genres = %s'%(len(NetworkList),len(ShowGenreList)))
        return NetworkList, ShowGenreList


    def fillMusicInfo(self, sortbycount=True):
        genres = []
        MusicGenreList = []
        if not hasMusic(): return MusicGenreList
        json_response = self.getSongs()
        [genres.extend(re.split(';|/|,',genre.strip())) for song in json_response for genre in song.get('genre',[])]
        genres = collections.Counter([genre for genre in genres if not genre.isdigit()])
        if sortbycount: 
            values = sorted(genres.most_common(25))
        else:
            values = sorted(genres.items())
        [MusicGenreList.append(key) for key, value in values]
        MusicGenreList.sort(key=lambda x: x.lower())
        self.log('fillMusicInfo, found genres = %s'%(MusicGenreList))
        return MusicGenreList
        
        
    def fillTVShows(self, art='poster'):
        tvshows = []
        if not hasTV(): return tvshows
        json_response = self.getTVshows()
        for item in json_response: 
            label = getLabel(item)
            if not label: continue
            tvshows.append({'label':label,'item':item,'logo':item.get('art',{}).get(art,'')})
        self.log('fillTVShows, found = %s'%(len(tvshows)))
        return tvshows
        
        
    def getDuration(self, path, item={}, accurate=None):
        if accurate is None: accurate = getSettingBool('Duration_Type') == 1
        self.log("getDuration, accurate = %s, path = %s"%(accurate,path))
        
        duration = 0
        runtime  = int(item.get('runtime','') or item.get('duration','') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration','') or '0')
        if path.startswith(('plugin://','upnp://','pvr://')): 
            return runtime
        
        if (runtime == 0 | accurate):
            if path.startswith('stack://'): #handle "stacked" videos:
                stack = (path.replace('stack://','').replace(',,',',')).split(' , ') #todo move to regex match
                for file in stack: duration += self.parseDuration(file, item)
            else: 
                duration = self.parseDuration(path, item)
            if duration > 0: runtime = duration
        self.log("getDuration, path = %s, runtime = %s"%(path,runtime))
        return runtime 
        
        
    def parseDuration(self, path, item={}, save=None):
        cacheName = '%s.parseDuration:.%s'%(ADDON_ID,path)
        duration  = self.cache.get(cacheName)
        runtime   = int(item.get('runtime','') or item.get('duration','') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration','') or '0')
        if duration is None:
            try:
                if path.startswith(('http','ftp')):
                    duration = 0
                elif path.startswith(('plugin://','upnp://','pvr://')):
                    duration = runtime
                else:
                    duration = self.videoParser.getVideoLength(path.replace("\\\\", "\\"))
            except Exception as e: 
                log("parseDuration, Failed! " + str(e), xbmc.LOGERROR)
                duration = 0
            self.cache.set(cacheName, duration, checksum=duration, expiration=datetime.timedelta(days=28))
        
        dbid    = item.get('id',-1)
        rundiff = int(percentDiff(runtime,duration))
        self.log("parseDuration, path = %s, runtime = %s, duration = %s, difference = %s"%(path,runtime,duration,rundiff))
        if save is None: save = getSettingBool('Store_Duration')
        if save and ((dbid > 0) & (runtime != duration) & (duration > 0) & (rundiff <= 45 or rundiff == 100)):
            self.setDuration(item['type'], dbid, duration)
        if ((rundiff > 45 and rundiff != 100) or rundiff == 0): duration = runtime
        self.log("parseDuration, returning duration = %s"%(duration))
        return duration
       
       
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
        json_response = self.getDirectory(dumpJSON(params))
        if 'filedetails' in json_response: 
            key = 'filedetails'
        else: 
            key = 'files'
            
        results = json_response.get('result',{})
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
            json_response = self.getDirectory('{"directory":"%s","properties":["file"]}'%(path),cache=False).get('result',{}).get('files',[])
            if json_response: break 
            
        if json_response:
            item = list(filter(lambda k:k.get('id',-1) == channelid, json_response))
            if item: 
                self.log('matchPVRPath, path found: %s'%(item[0].get('file','')))
                return item[0].get('file','')
        self.log('matchPVRPath, path not found \n%s'%(dumpJSON(json_response)))
        return ''
        
         
    def matchPVRChannel(self, chname, id, radio=False): # Convert PseudoTV Live channelID into a Kodi channelID for playback
        log('matchPVRChannel, chname = %s, id = %s'%(chname,id))
        channels = self.getPVRChannels(radio)
        for channel in channels:
            if channel.get('label') == chname:
                for key in ['broadcastnow','broadcastnext']:
                    writer = getWriter(channel.get(key,{}).get('writer',''))
                    citem  = writer.get('citem',{}) 
                    if citem.get('id','') == id:
                        log('matchPVRChannel, match found! id = %s'%(id))
                        return channel
        log('matchPVRChannel, no match found! \n%s'%(dumpJSON(channels)))
        return {}
        
        
    def fillPVRbroadcasts(self, channelItem):
        self.log('fillPVRbroadcasts')
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
        if isPlaylist:
            channelItem = self.fillPVRbroadcasts(channelItem)
        else: 
            channelItem['broadcastnext'] = [channelItem.get('broadcastnext',[])]
        return channelItem