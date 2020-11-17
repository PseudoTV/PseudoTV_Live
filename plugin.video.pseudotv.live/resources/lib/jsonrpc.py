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
from resources.lib.filelist    import Filelist
from resources.lib.worker      import BaseWorker
 
class Worker(BaseWorker):
    def do_sendJSON(self, param):
        log('Worker: do_sendJSON, param = %s'%(param))
        sendJSON(param)
     
     
class JSONRPC:
    def __init__(self, cache=None):
        self.log('__init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.myPlayer      = MY_PLAYER
        self.myMonitor     = MY_MONITOR
        self.myProcess     = Worker()
        self.fileList      = Filelist(self.cache)
        self.fileList.jsonRPC = self
        
        self.resourcePacks = self.buildLogoResources()
        self.processThread = threading.Timer(30.0, self.myProcess.start)
        
        if not FileAccess.exists(LOGO_LOC):
            FileAccess.makedirs(LOGO_LOC)
        if not FileAccess.exists(CACHE_LOC):
            FileAccess.makedirs(CACHE_LOC)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
        
    def startProcess(self):
        #thread egg-timer, start on last call.
        if self.processThread.isAlive():
            self.processThread.cancel()
            self.processThread.join()
        self.processThread = threading.Timer(30.0, self.myProcess.start)
        self.processThread.name = "processThread"
        self.processThread.start()


    def cacheJSON(self, command, life=datetime.timedelta(minutes=15)):
        cacheName = '%s.cacheJSON.%s'%(ADDON_ID,command)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            cacheResponse = dumpJSON(sendJSON(command))
            self.cache.set(cacheName, cacheResponse, checksum=len(cacheResponse), expiration=life)
        return loadJSON(cacheResponse)
        
        
    def getActivePlayer(self, return_item=False):
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1}')
        json_response = (sendJSON(json_query))
        item = json_response.get('result',[{}])[0]
        id = item.get('playerid',1)
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
        if cache: return self.cacheJSON(json_query).get('result',{}).get('addons',[])
        else:     return sendJSON(json_query).get('result',{}).get('addons',[])
        
        
    def getSongs(self, params='{"properties":["genre"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"AudioLibrary.GetSongs","params":%s,"id":1}'%(params))
        if cache: return self.cacheJSON(json_query).get('result',{}).get('songs',[])
        else:     return sendJSON(json_query).get('result',{}).get('songs',[])


    def getTVshows(self, params='{"properties":["studio","genre","art","mpaa","file"]}', cache=True):
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":%s,"id":1}'%(params))
        if cache: return (self.cacheJSON(json_query)).get('result',{}).get('tvshows',[])
        else:     return sendJSON(json_query).get('result',{}).get('tvshows',[])
        
        
    def getMovies(self, params='{"properties":["studio","genre","art","mpaa","file"]}', cache=True):
        json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params":%s, "id": 1}'%(params))
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


    def buildResourcePath(self, path, file):
        if path.startswith('resource://'):
            path = path.replace('resource://','special://home/addons/') + '/resources/%s'%(file)
        else: 
            path = os.path.join(path,file)
        return path
        
    
    def buildBCTresource(self, path):
        resourceMap = {}
        self.log('buildBCTresource, path = %s'%(path))
        if path.startswith('resource://'):
            dirs, files = self.getResourcesFolders(path,self.getPluginMeta(path).get('version',''))
            resourceMap = {'path':path,'files':files,'dirs':dirs,'filepaths':[self.buildResourcePath(path,file) for file in files]}
        elif path.startswith('plugin://'):
            dirs, files = self.listVFS(path,self.getPluginMeta(path).get('version',''))
            resourceMap = {'path':path,'files':files,'dirs':dirs,'filepaths':files}
        return resourceMap
        
            
    def buildLogoResources(self):
        self.log('buildLogoResources')
        logos     = []
        radios    = ["resource://resource.images.musicgenreicons.text"]
        genres    = ["resource://resource.images.moviegenreicons.transparent"]
        studios   = ["resource://resource.images.studios.white/", 
                     "resource://resource.images.studios.coloured/"]
                     
        if USE_COLOR: studios.reverse()
        [logos.append({'type':['Music Genres'],'path':radio,'files': self.getResourcesFolders(radio, self.getPluginMeta(radio).get('version',''))[1]}) for radio in radios]
        [logos.append({'type':['TV Genres','Movie Genres','Mixed Genres','Custom'],'path':genre,'files': self.getResourcesFolders(genre, self.getPluginMeta(genre).get('version',''))[1]}) for genre  in genres]
        [logos.append({'type':['TV Networks','Movie Studios','Custom'],'path':studio,'files': self.getResourcesFolders(studio, self.getPluginMeta(studio).get('version',''))[1]}) for studio in studios]
        logos.append( {'type':['TV Shows','Custom'],'path':'','files': self.getTVshows()})
        logos.append( {'type':['Recommended','IPTV','Custom'],'path':'','files': self.getAddons()})
        self.log('buildLogoResources return')
        return logos


    @use_cache(1)
    def getPluginMeta(self, plugin):
        return getPluginMeta(plugin)


    @use_cache(28)
    def getResourcesFolders(self, path, version=None):
        self.log('getResourcesFolders path = %s, version = %s'%(path,version))
        try: 
            return FileAccess.listdir(path)
        except: 
            return [],[]


    @use_cache(7)
    def findLogo(self, channelname, channeltype, useColor, version=ADDON_VERSION):
        log('findLogo')
        for item in self.resourcePacks:
            if channeltype in item['type']:
                for file in item['files']:
                    if isinstance(file, dict):
                        #jsonrpc item
                        if channelname.lower() == (file.get('showtitle','').lower() or file.get('label','').lower() or file.get('name','').lower() or file.get('title','').lower()):
                            channellogo = (file.get('art',file).get('clearlogo','') or file.get('thumbnail',''))
                            if channellogo:
                                return channellogo
                    else:
                        #resource item
                        if os.path.splitext(file.lower())[0] == channelname.lower():
                            return os.path.join(item['path'],file)
        return None
        
        
    def prepareImage(self, channelname, logo, featured):
        log('prepareImage: channelname = %s, featured = %s'%(channelname,featured))
        if logo.startswith(ADDON_PATH):
            logo = logo.replace(ADDON_PATH,'special://home/addons/%s/'%(ADDON_ID)).replace('\\','/')
        if featured:
            localIcon = os.path.join(LOGO_LOC,'%s.png'%(channelname))
            if logo.startswith('resource://'): return logo #todo parse xbt and extract image?
            # if FileAccess.copy(logo, localIcon): return localIcon
        return logo
        
        
    def getLogo(self, channelname, type='Custom', path=None, featured=False):
        log('getLogo: channelname = %s, type = %s'%(channelname,type))
        localIcon = os.path.join(IMAGE_LOC,'%s.png'%(channelname))
        userIcon  = os.path.join(LOGO_LOC ,'%s.png'%(channelname))
        if FileAccess.exists(userIcon): # check user folder
            log('getLogo: using user logo = %s'%(userIcon))
            return self.prepareImage(channelname,userIcon,featured)
        elif FileAccess.exists(localIcon): # check plugin folder
            log('getLogo: using local logo = %s'%(localIcon))
            return self.prepareImage(channelname,localIcon,featured)
            
        icon = self.findLogo(channelname, type, USE_COLOR, ADDON_VERSION)
        if not icon:
            if isinstance(path, list) and len(path) > 0: 
                path = path[0]
            if path is not None:
                if path.startswith('plugin://'): 
                    icon = self.getPluginMeta(path).get('icon',LOGO)
            icon = (icon or LOGO)
        return self.prepareImage(channelname,icon,featured)
        
        
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
        liz.setProperty("IsPlayable" ,"true")
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


    @use_cache(1)
    def listVFS(self, path, version=None):
        self.log('listVFS path = %s, version = %s'%(path,version))
        json_response = self.getDirectory('{"directory":"%s","properties":["duration","runtime"]}'%(path),cache=False)
        dirs, files = [[],[]]
        for item in json_response:
            file = item['file']
            if item['filetype'] == 'file':
                if self.fileList.parseDuration(file, item) == 0: continue
                files.append(file)
            else: dirs.append(file)
        return dirs, files


    @use_cache(1) # check for duration data.
    def existsVFS(self, path, media='video'):
        self.log('existsVFS path = %s, media = %s'%(path,media))
        dirs  = []
        json_response = self.fileList.requestList(str(random.random()), path, media)
        for item in json_response:
            file = item.get('file','')
            fileType = item.get('filetype','file')
            if fileType == 'file':
                dur = self.fileList.getDuration(file, item)
                if dur > 0: return {'file':file,'duration':dur,'seek':self.chkSeeking(file, dur)}
            else: dirs.append(file)
        for dir in dirs: return self.existsVFS(dir, media)
        return None

        
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
        if sortbycount: genres.most_common(25)
        values = sorted(genres.items())
        [MusicGenreList.append(key) for key, value in values]
        MusicGenreList.sort(key=lambda x: x.lower())
        self.log('fillMusicInfo, found genres = %s'%(MusicGenreList))
        return MusicGenreList
        
        
    def fillTVShows(self):
        tvshows = []
        if not hasTV(): return tvshows
        json_response = self.getTVshows()
        for item in json_response: tvshows.append({'label':item['label'],'item':item,'thumb':item.get('art',{}).get('poster','')})
        self.log('fillTVShows, found = %s'%(len(tvshows)))
        return tvshows