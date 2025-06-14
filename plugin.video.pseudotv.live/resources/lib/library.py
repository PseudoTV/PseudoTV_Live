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

from globals    import *
from predefined import Predefined
from resources  import Resources
from channels   import Channels

#constants
REG_KEY = 'PseudoTV_Recommended.%s'

class Service:
    from jsonrpc import JSONRPC
    player  = PLAYER()
    monitor = MONITOR()
    jsonRPC = JSONRPC()
    def _interrupt(self) -> bool:
        return PROPERTIES.isPendingInterrupt()
    def _suspend(self) -> bool:
        return PROPERTIES.isPendingSuspend()
        
        
class Library:
    def __init__(self, service=None):
        if service is None: service = Service()
        self.service      = service
        self.jsonRPC      = service.jsonRPC
        self.cache        = service.jsonRPC.cache
        self.predefined   = Predefined()
        self.channels     = Channels()
        self.resources    = Resources(service=self.service)
        
        self.pCount  = 0
        self.pDialog = None
        self.pMSG    = ''
        self.pHeader = ''
        
        self.libraryDATA  = getJSON(LIBRARYFLE_DEFAULT)
        self.libraryTEMP  = self.libraryDATA['library'].pop('Item')
        self.libraryDATA.update(self._load())


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
        
        
    def enableByName(self, type, names=[]):
        self.log('enableByName, type = %s, names = %s'%(type, names))
        items = self.getLibrary(type)
        for name in names:
            for item in items:
                if name.lower() == item.get('name','').lower(): item['enabled'] = True
                else:                                           item['enabled'] = False
        return self.setLibrary(type, items)
        
        
    def setLibrary(self, type, items=[]):
        self.log('setLibrary, type = %s, items = %s'%(type,len(items)))
        self.libraryDATA['library'][type] = items
        enabled = self.getEnabled(type, items)
        PROPERTIES.setEXTPropertyBool('%s.has.%s'%(ADDON_ID,slugify(type)),len(items) > 0)
        PROPERTIES.setEXTPropertyBool('%s.has.%s.enabled'%(ADDON_ID,slugify(type)),len(enabled) > 0)
        SETTINGS.setSetting('Select_%s'%(slugify(type)),'[COLOR=orange][B]%s[/COLOR][/B]/[COLOR=dimgray]%s[/COLOR]'%(len(enabled),len(items)))
        return self._save()


    def getEnabled(self, type, items=None):
        if items is None: items = self.getLibrary(type)
        return [item for item in items if item.get('enabled',False)]


    def updateLibrary(self, force: bool=False) -> bool:  
        def __funcs():
            return {
                     "Playlists"    :{'func':self.getPlaylists   ,'life':datetime.timedelta(minutes=FIFTEEN)},
                     "TV Networks"  :{'func':self.getNetworks    ,'life':datetime.timedelta(days=MAX_GUIDEDAYS)},
                     "TV Shows"     :{'func':self.getTVShows     ,'life':datetime.timedelta(hours=MAX_GUIDEDAYS)},
                     "TV Genres"    :{'func':self.getTVGenres    ,'life':datetime.timedelta(days=MAX_GUIDEDAYS)},
                     "Movie Genres" :{'func':self.getMovieGenres ,'life':datetime.timedelta(days=MAX_GUIDEDAYS)},
                     "Movie Studios":{'func':self.getMovieStudios,'life':datetime.timedelta(days=MAX_GUIDEDAYS)},
                     "Mixed Genres" :{'func':self.getMixedGenres ,'life':datetime.timedelta(days=MAX_GUIDEDAYS)},
                     "Mixed"        :{'func':self.getMixed       ,'life':datetime.timedelta(minutes=FIFTEEN)},
                     "Recommended"  :{'func':self.getRecommend   ,'life':datetime.timedelta(hours=MAX_GUIDEDAYS)},
                     "Services"     :{'func':self.getServices    ,'life':datetime.timedelta(hours=MAX_GUIDEDAYS)},
                     "Music Genres" :{'func':self.getMusicGenres ,'life':datetime.timedelta(days=MAX_GUIDEDAYS)}
                     }
                     
        def __fill(type, func):
            try: items = func()
            except Exception as e:
                self.log("__fill, %s failed! %s"%(type,e), xbmc.LOGERROR)
                items = []
            self.log('__fill, returning %s (%s)'%(type,len(items)))
            return items

        def __update(type, items, existing=[]):
            if not existing: existing = self.channels.getType(type)
            self.log('__update, type = %s, items = %s, existing = %s'%(type,len(items),len(existing)))
            for item in items:
                if not item.get('enabled',False):
                    for eitem in existing:
                        if getChannelSuffix(item.get('name'), type).lower() == eitem.get('name','').lower():
                            if eitem['logo'] not in [LOGO,COLOR_LOGO] and item['logo'] in [LOGO,COLOR_LOGO]: item['logo'] = eitem['logo']
                            item['enabled'] = True
                            break
                item['logo'] = self.resources.getLogo(item,item.get('logo',LOGO)) #update logo
                entry = self.libraryTEMP.copy()
                entry.update(item)
                yield entry

        if force: #clear library cache.
            with BUILTIN.busy_dialog():
                for label, params in list(__funcs().items()):
                    DIALOG.notificationDialog(LANGUAGE(30070)%(label),time=5)
                    self.cache.clear("%s.%s"%(self.__class__.__name__,params['func'].__name__),wait=5)
                
        
        complete = True 
        types     =  list(__funcs().keys())

        for idx, type in enumerate(types):
            self.pMSG    = type
            self.pCount  = int(idx*100//len(types))
            self.pHeader = '%s, %s %s'%(ADDON_NAME,LANGUAGE(32028),LANGUAGE(32041))
            self.pDialog = DIALOG.progressBGDialog(header=self.pHeader)
            
            if (self.service._interrupt() or self.service._suspend()) and PROPERTIES.hasFirstRun():
                self.log("updateLibrary, _interrupt")
                complete = False
                self.pDialog  = DIALOG.progressBGDialog(self.pCount, self.pDialog, '%s: %s'%(LANGUAGE(32144),LANGUAGE(32213)), self.pHeader)
                break
                
            self.pDialog  = DIALOG.progressBGDialog(self.pCount, self.pDialog, self.pMSG, self.pHeader)
            cacheResponse = self.cache.get("%s.%s"%(self.__class__.__name__,__funcs()[type]['func'].__name__))
            if not cacheResponse:
                self.pHeader  = '%s, %s %s'%(ADDON_NAME,LANGUAGE(32022),LANGUAGE(32041))
                cacheResponse = self.cache.set("%s.%s"%(self.__class__.__name__,__funcs()[type]['func'].__name__), __fill(type, __funcs()[type]['func']), expiration=__funcs()[type]['life'])
                
            if complete:
                self.setLibrary(type, list(__update(type,cacheResponse,self.getEnabled(type))))
                self.log("updateLibrary, type = %s, saved items = %s"%(type,len(cacheResponse)))
                
            self.pDialog = DIALOG.progressBGDialog(100, self.pDialog, header='%s, %s %s'%(ADDON_NAME,LANGUAGE(32041),LANGUAGE(32025)))
            
        self.log('updateLibrary, force = %s, complete = %s'%(force,  complete))
        return complete
        

    def resetLibrary(self, ATtypes=AUTOTUNE_TYPES):
        self.log('resetLibrary')
        for ATtype in ATtypes: 
            items = self.getLibrary(ATtype)
            for item in items:
                item['enabled'] = False #disable everything before selecting new items.
            self.setLibrary(ATtype, items)


    def updateProgress(self, percent, message, header):
        if self.pDialog: self.pDialog = DIALOG.progressBGDialog(percent, self.pDialog, message=message, header=header)


    def getNetworks(self):
        return self.getTVInfo().get('studios',[])
        
        
    def getTVGenres(self):
        return self.getTVInfo().get('genres',[])
 
 
    def getTVShows(self):
        return self.getTVInfo().get('shows',[])
        
        
    def getMovieStudios(self):
        return self.getMovieInfo().get('studios',[])
        
        
    def getMovieGenres(self):
        return self.getMovieInfo().get('genres',[])
              
 
    def getMusicGenres(self):
        return self.getMusicInfo().get('genres',[])
 
         
    def getMixedGenres(self):
        MixedGenreList = []
        tvGenres    = self.getTVGenres()
        movieGenres = self.getMovieGenres()
        for tv in [tv for tv in tvGenres for movie in movieGenres if tv.get('name','').lower() == movie.get('name','').lower()]:
            MixedGenreList.append({'name':tv.get('name'),'type':"Mixed Genres",'path':self.predefined.createGenreMixedPlaylist(tv.get('name')),'logo':tv.get('logo'),'rules':{"800":{"values":{"0":tv.get('name')}}}})
        self.log('getMixedGenres, genres = %s' % (len(MixedGenreList)))
        return sorted(MixedGenreList,key=itemgetter('name'))
    

    def getMixed(self):
        MixedList = []
        MixedList.append({'name':LANGUAGE(32001), 'type':"Mixed",'path':self.predefined.createMixedRecent()  ,'logo':self.resources.getLogo({'name':LANGUAGE(32001),'type':"Mixed"})}) #"Recently Added"
        MixedList.append({'name':LANGUAGE(32002), 'type':"Mixed",'path':self.predefined.createSeasonal()     ,'logo':self.resources.getLogo({'name':LANGUAGE(32002),'type':"Mixed"}),'rules':{"800":{"values":{"0":LANGUAGE(32002)}}}}) #"Seasonal"
        MixedList.extend(self.getPVRRecordings())#"PVR Recordings"
        MixedList.extend(self.getPVRSearches())  #"PVR Searches"
        self.log('getMixed, mixed = %s' % (len(MixedList)))
        return sorted(MixedList,key=itemgetter('name'))


    def getPVRRecordings(self):
        recordList    = []
        json_response = self.jsonRPC.getPVRRecordings()
        paths = [item.get('file') for idx, item in enumerate(json_response) if item.get('label','').endswith('(%s)'%(ADDON_NAME))]
        if len(paths) > 0: recordList.append({'name':LANGUAGE(32003),'type':"Mixed",'path':[paths],'logo':self.resources.getLogo({'name':LANGUAGE(32003),'type':"Mixed"})})
        self.log('getPVRRecordings, recordings = %s' % (len(recordList)))
        return sorted(recordList,key=itemgetter('name'))


    def getPVRSearches(self):
        searchList    = []
        json_response = self.jsonRPC.getPVRSearches()
        for idx, item in enumerate(json_response):
            if not item.get('file'): continue
            searchList.append({'name':"%s (%s)"%(item.get('label',LANGUAGE(32241)),LANGUAGE(32241)),'type':"Mixed",'path':[item.get('file')],'logo':self.resources.getLogo({'name':item.get('label',LANGUAGE(32241)),'type':"Mixed"})})
        self.log('getPVRSearches, searches = %s' % (len(searchList)))
        return sorted(searchList,key=itemgetter('name'))
                

    def getPlaylists(self):
        PlayList = []
        for type in ['video','mixed','music']:
            self.updateProgress(self.pCount,'%s: %s'%(self.pMSG,LANGUAGE(32140)),self.pHeader)
            results = self.jsonRPC.getSmartPlaylists(type)
            for idx, result in enumerate(results):
                self.updateProgress(self.pCount,'%s (%s): %s%%'%(self.pMSG,type.title(),int((idx)*100//len(results))),self.pHeader)
                if not result.get('label'): continue
                logo = result.get('thumbnail')
                if not logo: logo = self.resources.getLogo({'name':result.get('label',''),'type':"Custom"})
                PlayList.append({'name':result.get('label'),'type':"%s Playlist"%(type.title()),'path':[result.get('file')],'logo':logo})
        self.log('getPlaylists, PlayList = %s' % (len(PlayList)))
        PlayList = sorted(PlayList,key=itemgetter('name'))
        PlayList = sorted(PlayList,key=itemgetter('type'))
        return PlayList


    @cacheit()
    def getTVInfo(self, sortbycount=True):
        self.log('getTVInfo')
        if BUILTIN.hasTV():
            NetworkList   = Counter()
            ShowGenreList = Counter()
            TVShows       = Counter()
            self.updateProgress(self.pCount,'%s: %s'%(self.pMSG,LANGUAGE(32140)),self.pHeader)
            json_response = self.jsonRPC.getTVshows()
            
            for idx, info in enumerate(json_response):
                self.updateProgress(self.pCount,'%s: %s%%'%(self.pMSG,int((idx)*100//len(json_response))),self.pHeader)
                if not info.get('label'): continue
                TVShows.update({json.dumps({'name': info.get('label'), 'type':"TV Shows", 'path': self.predefined.createShowPlaylist(info.get('label')), 'logo': info.get('art', {}).get('clearlogo', ''),'rules':{"800":{"values":{"0":info.get('label')}}}}): info.get('episode', 0)})
                NetworkList.update([studio for studio in info.get('studio', [])])
                ShowGenreList.update([genre for genre in info.get('genre', [])])

            if sortbycount:
                TVShows       = [json.loads(x[0]) for x in sorted(TVShows.most_common(250))]
                NetworkList   = [x[0] for x in sorted(NetworkList.most_common(50))]
                ShowGenreList = [x[0] for x in sorted(ShowGenreList.most_common(25))]
            else:
                TVShows = (sorted(map(json.loads, list(TVShows.keys())), key=itemgetter('name')))
                del TVShows[250:]
                NetworkList = (sorted(set(list(NetworkList.keys()))))
                del NetworkList[250:]
                ShowGenreList = (sorted(set(list(ShowGenreList.keys()))))
                
            #search resources for studio/genre logos
            nNetworkList = []
            for idx, network in enumerate(NetworkList):
                self.updateProgress(self.pCount,'%s: %s%%'%(self.pMSG,int((idx)*100//len(NetworkList))),self.pHeader)
                nNetworkList.append({'name':network, 'type':"TV Networks", 'path': self.predefined.createNetworkPlaylist(network),'logo':self.resources.getLogo({'name':network,'type':"TV Networks"}),'rules':{"800":{"values":{"0":network}}}})
            NetworkList = nNetworkList
            
            nShowGenreList = []
            for idx, tvgenre in enumerate(ShowGenreList):
                self.updateProgress(self.pCount,'%s: %s%%'%(self.pMSG,int((idx)*100//len(ShowGenreList))),self.pHeader)
                nShowGenreList.append({'name':tvgenre, 'type':"TV Genres"  , 'path': self.predefined.createTVGenrePlaylist(tvgenre),'logo':self.resources.getLogo({'name':tvgenre,'type':"TV Genres"}),'rules':{"800":{"values":{"0":tvgenre}}}})
            ShowGenreList = nShowGenreList
            
        else: NetworkList = ShowGenreList = TVShows = []
        self.log('getTVInfo, networks = %s, genres = %s, shows = %s' % (len(NetworkList), len(ShowGenreList), len(TVShows)))
        return {'studios':NetworkList,'genres':ShowGenreList,'shows':TVShows}


    @cacheit()
    def getMovieInfo(self, sortbycount=True):
        self.log('getMovieInfo')
        if BUILTIN.hasMovie():     
            StudioList     = Counter()
            MovieGenreList = Counter()
            self.updateProgress(self.pCount,'%s: %s'%(self.pMSG,LANGUAGE(32140)),self.pHeader)
            json_response = self.jsonRPC.getMovies() #we can't parse for genres directly from Kodi json ie.getGenres; because we need the weight of each genre to prioritize list.

            for idx, info in enumerate(json_response):
                StudioList.update([studio for studio in info.get('studio', [])])
                MovieGenreList.update([genre for genre in info.get('genre', [])])
                
            if sortbycount:
                StudioList     = [x[0] for x in sorted(StudioList.most_common(25))]
                MovieGenreList = [x[0] for x in sorted(MovieGenreList.most_common(25))]
            else:
                StudioList = (sorted(set(list(StudioList.keys()))))
                del StudioList[250:]
                MovieGenreList = (sorted(set(list(MovieGenreList.keys()))))
                
            #search resources for studio/genre logos
            nStudioList = []
            for idx, studio in enumerate(StudioList):
                self.updateProgress(self.pCount,'%s: %s%%'%(self.pMSG,int((idx)*100//len(StudioList))),self.pHeader)
                nStudioList.append({'name':studio, 'type':"Movie Studios", 'path': self.predefined.createStudioPlaylist(studio)    ,'logo':self.resources.getLogo({'name':studio,'type':"Movie Studios"}),'rules':{"800":{"values":{"0":studio}}}})
            StudioList = nStudioList
            
            nMovieGenreList = []
            for idx, genre in enumerate(MovieGenreList):
                self.updateProgress(self.pCount,'%s: %s%%'%(self.pMSG,int((idx)*100//len(MovieGenreList))),self.pHeader)
                nMovieGenreList.append({'name':genre,  'type':"Movie Genres" , 'path': self.predefined.createMovieGenrePlaylist(genre) ,'logo':self.resources.getLogo({'name':genre,'type':"Movie Genres"}) ,'rules':{"800":{"values":{"0":genre}}}})   
            MovieGenreList = nMovieGenreList
            
        else: StudioList = MovieGenreList = []
        self.log('getMovieInfo, studios = %s, genres = %s' % (len(StudioList), len(MovieGenreList)))
        return {'studios':StudioList,'genres':MovieGenreList}
        
        
    @cacheit()
    def getMusicInfo(self, sortbycount=True):
        self.log('getMusicInfo')
        if BUILTIN.hasMusic():
            MusicGenreList = Counter()
            self.updateProgress(self.pCount,'%s: %s'%(self.pMSG,LANGUAGE(32140)),self.pHeader)
            json_response = self.jsonRPC.getMusicGenres()
            
            for idx, info in enumerate(json_response):
                MusicGenreList.update([genre.strip() for genre in info.get('label','').split(';')])
            
            if sortbycount:
                MusicGenreList = [x[0] for x in sorted(MusicGenreList.most_common(50))]
            else:
                MusicGenreList = (sorted(set(list(MusicGenreList.keys()))))
                del MusicGenreList[250:]
                MusicGenreList = (sorted(set(list(MusicGenreList.keys()))))

            #search resources for studio/genre logos
            nMusicGenreList = []
            for idx, genre in enumerate(MusicGenreList):
                self.updateProgress(self.pCount,'%s: %s%%'%(self.pMSG,int((idx)*100//len(MusicGenreList))),self.pHeader)
                nMusicGenreList.append({'name':genre, 'type':"Music Genres", 'path': self.predefined.createMusicGenrePlaylist(genre),'logo':self.resources.getLogo({'name':genre,'type':"Music Genres"})})
            MusicGenreList = nMusicGenreList

        else: MusicGenreList = []
        self.log('getMusicInfo, found genres = %s' % (len(MusicGenreList)))
        return {'genres':MusicGenreList}
        
        
    def getRecommend(self):
        self.log('getRecommend')
        PluginList = []
        WhiteList  = self.getWhiteList()
        AddonsList = self.searchRecommended()
        for addonid, item in list(AddonsList.items()):
            if addonid not in WhiteList: continue
            items = item.get('data',{}).get('vod',[])
            items.extend(item.get('data',{}).get('live',[]))
            for vod in items:
                path = vod.get('path')
                if not isinstance(path,list): path = [path]
                PluginList.append({'id':item['meta'].get('name'), 'name':vod.get('name'), 'type':"Recommended", 'path': path, 'logo':vod.get('icon',item['meta'].get('thumbnail'))})
        self.log('getRecommend, found (%s) vod items.' % (len(PluginList)))
        PluginList = sorted(PluginList,key=itemgetter('name'))
        PluginList = sorted(PluginList,key=itemgetter('id'))
        return PluginList
            

    def getRecommendInfo(self, addonid):
        self.log('getRecommendInfo, addonid = %s'%(addonid))
        return self.searchRecommended().get(addonid,{})
        

    def searchRecommended(self):
        return {} #todo
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


    def getServices(self):
        self.log('getServices')
        return []


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


    def clearBlackList(self):
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
