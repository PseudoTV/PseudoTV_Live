#   Copyright (C) 2025 Lunatixz
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
from predefined  import Predefined
from resources   import Resources
from channels    import Channels

#constants
REG_KEY = 'PseudoTV_Recommended.%s'

class Service(object):
    from jsonrpc import JSONRPC
    jsonRPC = JSONRPC()
    monitor = MONITOR()
    def _shutdown(self, wait=1.0) -> bool:
        return (self.monitor.waitForAbort(wait) | PROPERTIES.isPendingShutdown())
    def _interrupt(self) -> bool:
        return (PROPERTIES.isPendingShutdown() | PROPERTIES.isPendingRestart() | PROPERTIES.isPendingInterrupt() | PROPERTIES.isInterruptActivity())
    def _suspend(self, wait=1.0) -> bool:
        pendingSuspend = PROPERTIES.isPendingSuspend()
        return pendingSuspend
    def _sleep(self, wait=1.0):
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) | self._interrupt()): return True
            else: wait -= CPU_CYCLE
        return False
        
class Library(object):
    channels   = Channels()
    predefined = Predefined()
    
    def __init__(self, service=None):
        if service is None: service = Service()
        self.service   = service
        self.jsonRPC   = service.jsonRPC
        self.cache     = service.jsonRPC.cache
        self.resources = Resources(service=self.service)
        
        self.pCount  = 0
        self.pDialog = None
        self.pMSG    = ''
        self.pHeader = ''
        
        self.libraryDATA = getJSON(LIBRARYFLE_DEFAULT)
        self.libraryTEMP = self.libraryDATA['library'].pop('Item')
        self.libraryDATA.update(self._load())

        self.AUTOTUNE = {"Playlists"    :{'func':self.getPlaylists   ,'life':datetime.timedelta(minutes=FIFTEEN)},
                         "TV Networks"  :{'func':self.getNetworks    ,'life':datetime.timedelta(days=MAX_GUIDEDAYS)},
                         "TV Shows"     :{'func':self.getTVShows     ,'life':datetime.timedelta(hours=MAX_GUIDEDAYS)},
                         "TV Genres"    :{'func':self.getTVGenres    ,'life':datetime.timedelta(days=MAX_GUIDEDAYS)},
                         "Movie Genres" :{'func':self.getMovieGenres ,'life':datetime.timedelta(days=MAX_GUIDEDAYS)},
                         "Movie Studios":{'func':self.getMovieStudios,'life':datetime.timedelta(days=MAX_GUIDEDAYS)},
                         "Mixed Genres" :{'func':self.getMixedGenres ,'life':datetime.timedelta(days=MAX_GUIDEDAYS)},
                         "Mixed"        :{'func':self.getMixed       ,'life':datetime.timedelta(minutes=FIFTEEN)},
                         "Recommended"  :{'func':self.getRecommend   ,'life':datetime.timedelta(hours=MAX_GUIDEDAYS)},
                         "Services"     :{'func':self.getServices    ,'life':datetime.timedelta(hours=MAX_GUIDEDAYS)},
                         "Music Genres" :{'func':self.getMusicGenres ,'life':datetime.timedelta(days=MAX_GUIDEDAYS)}}


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def _load(self, file=LIBRARYFLEPATH):
        return getJSON(file)
    
    
    def _save(self, file=LIBRARYFLEPATH):
        self.libraryDATA['uuid'] = SETTINGS.getMYUUID()
        return setJSON(file, self.libraryDATA)
        
  
    def getLibrary(self, type=None):
        self.log('getLibrary, type = %s'%(type))
        if type is None: return self.libraryDATA.get('library',{})
        else:            return self.libraryDATA.get('library',{}).get(type,[])

        
    def setLibrary(self, type, items=[]):
        self.log('setLibrary, type = %s, items = %s'%(type,len(items)))
        PROPERTIES.setLibrary(type,len(items) > 0)
        self.libraryDATA['library'][type] = items
        return self._save()


    def hasLibrary(self, type):
        return len(self.libraryDATA['library'].get(type,[])) > 0
        
        
    def updateLibrary(self, types, silent=False, complete=False):
        if not PROPERTIES.isRunning('Library.updateLibrary'):
            with PROPERTIES.chkRunning('Library.updateLibrary'):
                for type in types:
                    items = self.jsonRPC.cache.get("%s.%s"%(self.__class__.__name__,self.AUTOTUNE[type]['func'].__name__))
                    if items is None: 
                        self.pCount  = 0
                        self.pMSG    = type
                        self.pHeader = '%s, %s %s'%(ADDON_NAME,LANGUAGE(32022),LANGUAGE(32041))
                        with DIALOG._progressDialog(self.pMSG, self.pHeader, silent) as self.pDialog:
                            items = self.AUTOTUNE[type]['func']()
                    if items is None: self.service._que(self.service.tasks.chkLibrary,2,*(type,silent))
                    else:
                        complete = self.setLibrary(type,items)
                        self.log("updateLibrary, type = %s, items = %s, complete = %s"%(type,len(items),complete))
        return complete


    def clrLibraryCache(self, type):
        self.log('clrLibraryCache, type = %s'%(type))
        with BUILTIN.busy_dialog():
            DIALOG.notificationDialog(LANGUAGE(30070)%(type),time=5)
            self.cache.clear("%s.%s"%(self.__class__.__name__,self.AUTOTUNE[type]['func'].__name__),wait=5)


    def getPlaylists(self):
        PlayList = []
        types = ['video','music']
        for i, type in enumerate(types):
            self.pCount  = int(i*100//len(types))
            self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s'%(self.pMSG,LANGUAGE(32140)), header=self.pHeader)
            
            nPlayList = []
            results   = self.jsonRPC.getSmartPlaylists(type)
            for idx, result in enumerate(results):
                if self.service._interrupt():
                    self.log("getPlaylists, _interrupt")
                    return
                else:
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, '%s (%s): %s%%'%(self.pMSG,type.title(),int((idx)*100//len(results))), header=self.pHeader)
                    if not result.get('label') or (type == 'mixed' and not 'pseudotv' in result.get('label','').lower()): continue
                    nPlayList.append({'name':result.get('label'),'type':"%s Playlist"%(type.title()),'path':[result.get('file')],'logo':self.resources.getLogo({'name':result.get('label'),'type':"Custom"},fallback=result.get('thumbnail'))})
            self.log('getPlaylists, type = %s, PlayList = %s'%(type,len(nPlayList)))
            PlayList.extend(nPlayList)
        PlayList = sorted(PlayList,key=itemgetter('name'))
        PlayList = sorted(PlayList,key=itemgetter('type'))
        return PlayList

    
    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getNetworks(self):
        try:    return self.getTVInfo().get('studios',[])
        except: return []
        
        
    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getTVShows(self):
        try:    return self.getTVInfo().get('shows',[])
        except: return []
        
        
    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getTVGenres(self):
        try:    return self.getTVInfo().get('genres',[])
        except: return []
 
       
    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getMovieGenres(self):
        try:    return self.getMovieInfo().get('genres',[])
        except: return []
              
           
    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))  
    def getMovieStudios(self):
        try:    return self.getMovieInfo().get('studios',[])
        except: return []
        
         
    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getMixedGenres(self):
        MixedGenreList = []
        tvGenres    = self.getTVGenres()
        movieGenres = self.getMovieGenres()
        for tv in [tv for tv in tvGenres for movie in movieGenres if tv.get('name','').lower() == movie.get('name','').lower()]:
            MixedGenreList.append({'name':tv.get('name'),'type':"Mixed Genres",'path':self.predefined.createGenreMixedPlaylist(tv.get('name')),'logo':tv.get('logo')})
        self.log('getMixedGenres, genres = %s' % (len(MixedGenreList)))
        return sorted(MixedGenreList,key=itemgetter('name'))
    

    def getMixed(self):
        MixedList = []
        MixedList.append({'name':LANGUAGE(32001), 'type':"Mixed",'path':self.predefined.createMixedRecent()  ,'logo':self.resources.getLogo({'name':LANGUAGE(32001),'type':"Mixed"})}) #"Recently Added"
        MixedList.append({'name':LANGUAGE(32002), 'type':"Mixed",'path':self.predefined.createSeasonal()     ,'logo':self.resources.getLogo({'name':LANGUAGE(32002),'type':"Mixed"})}) #"Seasonal"
        MixedList.extend(self.getPVRRecordings())#"PVR Recordings"
        MixedList.extend(self.getPVRSearches())  #"PVR Searches"
        self.log('getMixed, mixed = %s' % (len(MixedList)))
        return sorted(MixedList,key=itemgetter('name'))


    def getRecommend(self):
        self.log('getRecommend')
        return []
        # PluginList = []
        # WhiteList  = self.getWhiteList()
        # self.pDialog  = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s'%(self.pMSG,LANGUAGE(32140)), header=self.pHeader)
        # AddonsList = self.searchRecommended()
        # for addonid, item in list(AddonsList.items()):
            # if addonid not in WhiteList: continue
            # items = item.get('data',{}).get('vod',[])
            # items.extend(item.get('data',{}).get('live',[]))
            # for vod in items:
                # path = vod.get('path')
                # if not isinstance(path,list): path = [path]
                # PluginList.append({'id':item['meta'].get('name'), 'name':vod.get('name'), 'type':"Recommended", 'path': path, 'logo':vod.get('icon',item['meta'].get('thumbnail'))})
        # self.log('getRecommend, found (%s) vod items.' % (len(PluginList)))
        # PluginList = sorted(PluginList,key=itemgetter('name'))
        # PluginList = sorted(PluginList,key=itemgetter('id'))
        # return PluginList
            

    def getServices(self):
        self.log('getServices')
        return []


    def getMusicGenres(self):
        try:    return self.getMusicInfo().get('genres',[])
        except: return []
 
 
    def getPVRRecordings(self):
        recordList    = []
        self.pDialog  = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s'%(self.pMSG,LANGUAGE(32140)), header=self.pHeader)
        json_response = self.jsonRPC.getPVRRecordings()
        paths = [item.get('file') for idx, item in enumerate(json_response) if item.get('label','').endswith('(%s)'%(ADDON_NAME))]
        if len(paths) > 0: recordList.append({'name':LANGUAGE(32003),'type':"Mixed",'path':[paths],'logo':self.resources.getLogo({'name':LANGUAGE(32003),'type':"Mixed"})})
        self.log('getPVRRecordings, recordings = %s' % (len(recordList)))
        return sorted(recordList,key=itemgetter('name'))


    def getPVRSearches(self):
        searchList = []
        json_response = self.jsonRPC.getPVRSearches()
        self.pDialog  = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s'%(self.pMSG,LANGUAGE(32140)), header=self.pHeader)
        for idx, item in enumerate(json_response):
            if self.service._interrupt():
                self.log("getPVRSearches, _interrupt")
                return
            elif not item.get('file'): continue
            else:
                searchList.append({'name':"%s (%s)"%(item.get('label',LANGUAGE(32241)),LANGUAGE(32241)),'type':"Mixed",'path':[item.get('file')],'logo':self.resources.getLogo({'name':item.get('label',LANGUAGE(32241)),'type':"Mixed"})})
        self.log('getPVRSearches, searches = %s' % (len(searchList)))
        searchList = sorted(searchList,key=itemgetter('name'))
        return searchList
                

    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getTVInfo(self, sortbycount=True):
        self.log('getTVInfo')
        NetworkList = ShowGenreList = TVShowList = []
        if BUILTIN.hasTV():
            TVShowList    = Counter()
            NetworkList   = Counter()
            ShowGenreList = Counter()
            
            self.pDialog  = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s'%(self.pMSG,LANGUAGE(32140)), header=self.pHeader)
            json_response = self.jsonRPC.getTVshows()
            for idx, info in enumerate(json_response):
                if self.service._interrupt():
                    self.log("getTVInfo, _interrupt")
                    return
                elif info.get('label'):
                    TVShowList.update({dumpJSON(info):info.get('episode',0)})
                    NetworkList.update([studio for studio in info.get('studio',[])])
                    ShowGenreList.update([genre for genre in info.get('genre',[])])
                    
            if sortbycount:
                TVShowList    = [loadJSON(x[0]) for x in sorted(TVShowList.most_common(25))]
                NetworkList   = [x[0] for x in sorted(NetworkList.most_common(25))]
                ShowGenreList = [x[0] for x in sorted(ShowGenreList.most_common(25))]
            else:
                TVShowList    = (sorted(map(loadJSON, list(TVShowList.keys())), key=itemgetter('name')))
                NetworkList   = (sorted(set(list(NetworkList.keys()))))
                ShowGenreList = (sorted(set(list(ShowGenreList.keys()))))

            #search resources for studio/genre logos
            nTVShowList = []
            for idx, show in enumerate(TVShowList):
                if self.service._interrupt():
                    self.log("getTVInfo, _interrupt")
                    return
                else:
                    self.pMSG    = LANGUAGE(32005)#"TV Shows"
                    self.pCount  = int(idx*100//len(TVShowList)) // 3
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s%%'%(self.pMSG,int((idx)*100//len(TVShowList))), header=self.pHeader)
                    nTVShowList.append({'name': show.get('label'), 'type':"TV Shows", 'path': self.predefined.createShowPlaylist(show.get('label')), 'logo': self.resources.getLogo({'name':show.get('label'),'type':"TV Shows"},show.get('art', {}).get('clearlogo', ''))})
            TVShowList = nTVShowList

            nNetworkList = []
            for idx, network in enumerate(NetworkList):
                if self.service._interrupt():
                    self.log("getTVInfo, _interrupt")
                    return
                else:
                    self.pMSG    = LANGUAGE(32004)#"TV Networks"
                    self.pCount  = 33 + int(idx*100//len(NetworkList)) // 3
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s%%'%(self.pMSG,int((idx)*100//len(NetworkList))), header=self.pHeader)
                    nNetworkList.append({'name':network, 'type':"TV Networks", 'path': self.predefined.createNetworkPlaylist(network),'logo':self.resources.getLogo({'name':network,'type':"TV Networks"})})
            NetworkList = nNetworkList
            
            nShowGenreList = []
            for idx, tvgenre in enumerate(ShowGenreList):
                if self.service._interrupt():
                    self.log("getTVInfo, _interrupt")
                    return
                else:
                    self.pMSG    = LANGUAGE(32006)#"TV Genres"
                    self.pCount  = 66 + int(idx*100//len(ShowGenreList)) // 3
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s%%'%(self.pMSG,int((idx)*100//len(ShowGenreList))), header=self.pHeader)
                    nShowGenreList.append({'name':tvgenre, 'type':"TV Genres"  , 'path': self.predefined.createTVGenrePlaylist(tvgenre),'logo':self.resources.getLogo({'name':tvgenre,'type':"TV Genres"})})
            ShowGenreList = nShowGenreList
        self.log('getTVInfo, networks = %s, genres = %s, shows = %s' % (len(NetworkList), len(ShowGenreList), len(TVShowList)))
        return {'studios':NetworkList,'genres':ShowGenreList,'shows':TVShowList}


    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getMovieInfo(self, sortbycount=True):
        self.log('getMovieInfo')
        StudioList = MovieGenreList = []
        if BUILTIN.hasMovie(): 
            StudioList     = Counter()
            MovieGenreList = Counter()
            self.pDialog   = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s'%(self.pMSG,LANGUAGE(32140)), header=self.pHeader)
            json_response  = self.jsonRPC.getMovies() #we can't parse for genres directly from Kodi json ie.getGenres; because we need the weight of each genre to prioritize list.

            for idx, info in enumerate(json_response):
                if self.service._interrupt():
                    self.log("getMovieInfo, _interrupt")
                    return
                else:
                    StudioList.update([studio for studio in info.get('studio', [])])
                    MovieGenreList.update([genre for genre in info.get('genre', [])])
                
            if sortbycount:
                StudioList     = [x[0] for x in sorted(StudioList.most_common(25))]
                MovieGenreList = [x[0] for x in sorted(MovieGenreList.most_common(25))]
            else:
                StudioList     = (sorted(set(list(StudioList.keys()))))
                MovieGenreList = (sorted(set(list(MovieGenreList.keys()))))
                
            #search resources for studio/genre logos
            nStudioList = []
            for idx, studio in enumerate(StudioList):
                if self.service._interrupt():
                    self.log("getMovieInfo, _interrupt")
                    return
                else:
                    self.pMSG    = LANGUAGE(32008)#"Movie Studios"
                    self.pCount  = int(idx*100//len(StudioList)) // 2
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s%%'%(self.pMSG,int((idx)*100//len(StudioList))), header=self.pHeader)
                    nStudioList.append({'name':studio, 'type':"Movie Studios", 'path': self.predefined.createStudioPlaylist(studio) ,'logo':self.resources.getLogo({'name':studio,'type':"Movie Studios"})})
            StudioList = nStudioList
            
            nMovieGenreList = []
            for idx, genre in enumerate(MovieGenreList):
                if self.service._interrupt():
                    self.log("getMovieInfo, _interrupt")
                    return
                else:
                    self.pMSG    = LANGUAGE(32007)#"Movie Genres"
                    self.pCount  = 50 + int(idx*100//len(MovieGenreList)) // 2
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s%%'%(self.pMSG,int((idx)*100//len(MovieGenreList))), header=self.pHeader)
                    nMovieGenreList.append({'name':genre,  'type':"Movie Genres" , 'path': self.predefined.createMovieGenrePlaylist(genre) ,'logo':self.resources.getLogo({'name':genre,'type':"Movie Genres"})})   
            MovieGenreList = nMovieGenreList
        self.log('getMovieInfo, studios = %s, genres = %s' % (len(StudioList), len(MovieGenreList)))
        return {'studios':StudioList,'genres':MovieGenreList}
        
        
    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getMusicInfo(self, sortbycount=True):
        self.log('getMusicInfo')
        MusicGenreList = []
        if BUILTIN.hasMusic(): 
            MusicGenreList = Counter()
            self.pDialog   = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s'%(self.pMSG,LANGUAGE(32140)), header=self.pHeader)
            json_response  = self.jsonRPC.getMusicGenres()
            
            for idx, info in enumerate(json_response):
                if self.service._interrupt():
                    self.log("getMusicInfo, _interrupt")
                    return
                else:
                    MusicGenreList.update([genre.strip() for genre in info.get('label','').split(';')])
            
            if sortbycount: MusicGenreList = [x[0] for x in sorted(MusicGenreList.most_common(25))]
            else:           MusicGenreList = (sorted(set(list(MusicGenreList.keys()))))

            #search resources for studio/genre logos
            nMusicGenreList = []
            for idx, genre in enumerate(MusicGenreList):
                if self.service._interrupt():
                    self.log("getMusicInfo, _interrupt")
                    return
                else:
                    self.pMSG    = LANGUAGE(32011)#"Music Genres"
                    self.pCount  = int(idx*100//len(MusicGenreList))
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, self.pMSG, header=self.pHeader)
                    nMusicGenreList.append({'name':genre, 'type':"Music Genres", 'path': self.predefined.createMusicGenrePlaylist(genre),'logo':self.resources.getLogo({'name':genre,'type':"Music Genres"})})
            MusicGenreList = nMusicGenreList
        self.log('getMusicInfo, found genres = %s' % (len(MusicGenreList)))
        return {'genres':MusicGenreList}
        
        
    def getRecommendInfo(self, addonid):
        self.log('getRecommendInfo, addonid = %s'%(addonid))
        return self.searchRecommended().get(addonid,{})
        

    def searchRecommended(self):
        ...#todo refactor feature
        # library.importPrompt() 
        # def _search(addonid):
            # cacheName = 'searchRecommended.%s'%(getMD5(addonid))
            # addonMeta = SETTINGS.getAddonDetails(addonid)
            # payload   = PROPERTIES.getEXTProperty(REG_KEY%(addonid))
            # if not payload: #startup services may not be broadcasting beacon; use last cached beacon instead.
                # payload = self.cache.get(cacheName, checksum=addonMeta.get('version',ADDON_VERSION), json_data=True)
            # else:
                # payload = loadJSON(payload)
                # self.cache.set(cacheName, payload, checksum=addonMeta.get('version',ADDON_VERSION), expiration=datetime.timedelta(days=MAX_GUIDEDAYS), json_data=True)
            
            # if payload:
                # self.log('searchRecommended, found addonid = %s, payload = %s'%(addonid,payload))
                # return addonid,{"data":payload,"meta":addonMeta}
                
        # addonList = sorted(list(set([_f for _f in [addon.get('addonid') for addon in list([k for k in self.jsonRPC.getAddons() if k.get('addonid','') not in self.getBlackList()])] if _f])))
        # return dict([_f for _f in [_search(addonid) for addonid in addonList] if _f])


    def getWhiteList(self):
        #whitelist - prompt shown, added to import list and/or manager dropdown.
        return self.libraryDATA.get('whitelist',[])
        
        
    def setWhiteList(self, data=[]):
        self.libraryDATA['whitelist'] = sorted(set(data))
        return self._save()
        
        
    def getBlackList(self):
        #blacklist - plugin ignored for the life of the list.
        return self.libraryDATA.get('blacklist',[])
    
        
    def setBlackList(self, data=[]):
        self.libraryDATA['blacklist'] = sorted(set(data))
        return self._save()
        
        
    def addWhiteList(self, addonid):
        self.log('addWhiteList, addonid = %s'%(addonid))
        whiteList = self.getWhiteList()
        whiteList.append(addonid)
        whiteList = sorted(set(whiteList))
        if len(whiteList) > 0: PROPERTIES.setEXTPropertyBool('%s.has.WhiteList'%(ADDON_ID),len(whiteList) > 0)
        return self.setWhiteList(whiteList)
        

    def addBlackList(self, addonid):
        self.log('addBlackList, addonid = %s'%(addonid))
        blackList = self.getBlackList()
        blackList.append(addonid)
        blackList = sorted(set(blackList))
        return self.setBlackList(blackList)


    def clrBlackList(self):
        return self.setBlackList()

               
    def importPrompt(self):
        addonList = self.searchRecommended()
        ignoreList = self.getWhiteList()
        ignoreList.extend(self.getBlackList()) #filter addons previously parsed.
        addonNames = sorted(list(set([_f for _f in [item.get('meta',{}).get('name') for addonid, item in list(addonList.items()) if not addonid in ignoreList] if _f])))
        self.log('importPrompt, addonNames = %s'%(len(addonNames)))
        
        try:
            if len(addonNames) > 1:
                retval = DIALOG.yesnoDialog('%s'%(LANGUAGE(32055)%(ADDON_NAME,', '.join(addonNames))), customlabel=LANGUAGE(32056))
                self.log('importPrompt, prompt retval = %s'%(retval))
                if   retval == 1: raise Exception('Single Entry')
                elif retval == 2: 
                    for addonid, item in list(addonList.items()):
                        if item.get('meta',{}).get('name') in addonNames:
                            self.addWhiteList(addonid)
            else: raise Exception('Single Entry')
        except Exception as e:
            self.log('importPrompt, %s'%(e))
            for addonid, item in list(addonList.items()):
                if item.get('meta',{}).get('name') in addonNames:
                    if not DIALOG.yesnoDialog('%s'%(LANGUAGE(32055)%(ADDON_NAME,item['meta'].get('name','')))):
                        self.addBlackList(addonid)
                    else:
                        self.addWhiteList(addonid)
                
        PROPERTIES.setEXTPropertyBool('%s.has.WhiteList'%(ADDON_ID),len(self.getWhiteList()) > 0)
        PROPERTIES.setEXTPropertyBool('%s.has.BlackList'%(ADDON_ID),len(self.getBlackList()) > 0)
        SETTINGS.setSetting('Clear_BlackList','|'.join(self.getBlackList()))