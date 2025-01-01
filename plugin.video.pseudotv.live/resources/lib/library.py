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
    monitor = xbmc.Monitor()
    jsonRPC = JSONRPC()
    def _interrupt(self) -> bool:
        return PROPERTIES.isPendingInterrupt()
    def _suspend(self) -> bool:
        return PROPERTIES.isPendingSuspend()
        
        
class Library:
    def __init__(self, service=None):
        if service is None: service = Service()
        self.service      = service
        self.parserCount  = 0
        self.parserMSG    = ''
        self.parserDialog = None
        self.jsonRPC      = service.jsonRPC
        self.cache        = service.jsonRPC.cache
        self.predefined   = Predefined()
        self.channels     = Channels()
        self.resources    = Resources(self.jsonRPC)
        self.libraryDATA  = getJSON(LIBRARYFLE_DEFAULT)
        self.libraryTEMP  = self.libraryDATA['library'].pop('Item')
        self.libraryDATA.update(self._load())

        self.libraryFUNCS = {"Playlists"    :self.getPlaylists,
                             "TV Networks"  :self.getNetworks,
                             "TV Shows"     :self.getTVShows,
                             "TV Genres"    :self.getTVGenres,
                             "Movie Genres" :self.getMovieGenres,
                             "Movie Studios":self.getMovieStudios,
                             "Mixed Genres" :self.getMixedGenres,
                             "Mixed"        :self.getMixed,
                             "Recommended"  :self.getRecommend,
                             "Services"     :self.getServices,
                             "Music Genres" :self.getMusicGenres}
             

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

    
    def _load(self, file=LIBRARYFLEPATH):
        return getJSON(file)
    
    
    def _save(self, file=LIBRARYFLEPATH):
        return setJSON(file, self.libraryDATA)
        
        
    def getTemplate(self):
        return self.libraryDATA.get('library',{}).get('Item',{}).copy()
        
        
    def getLibrary(self, type=None):
        self.log('getLibrary, type = %s'%(type))
        if type is None: return self.libraryDATA.get('library',{})
        else:            return self.libraryDATA.get('library',{}).get(type,[])
        
        
    def setLibrary(self, type, items=[]):
        self.log('setLibrary')
        self.libraryDATA['uuid'] = SETTINGS.getMYUUID()
        self.libraryDATA['library'][type] = items
        PROPERTIES.setEXTPropertyBool('%s.has.%s'%(ADDON_ID,slugify(type)),len(items) > 0)
        SETTINGS.setSetting('Select_%s'%(slugify(type)),'[COLOR=orange][B]%s[/COLOR][/B]/[COLOR=dimgray]%s[/COLOR]'%(len(self.getEnabled(type)),len(items)))
        return self._save()


    def getEnabled(self, type):
        items = self.getLibrary(type)
        return [item for item in items if item.get('enabled',False)]


    def updateLibrary(self, force: bool=False) -> bool:
        def __clear():
            for label, func in list(self.libraryFUNCS.items()):
                cacheName = "%s.%s"%(self.__class__.__name__,func.__name__)
                DIALOG.notificationDialog(LANGUAGE(30070)%(label),time=5)
                self.cache.clear(cacheName,wait=5)
                
        def __update(type, item):
            #check existing library for enabled itemss
            [item.update({'enabled':True}) for eitem in self.getEnabled(type) if getChannelSuffix(item.get('name'), type).lower() == eitem.get('name').lower()]
            #check existing channels for enabled items
            [item.update({'enabled':True}) for channel in self.channels.getType(type) if getChannelSuffix(item.get('name'), type).lower() == channel.get('name').lower()]
            entry = self.getTemplate()
            entry.update(item)
            return entry
            
        def _fill(type, func):
            try:
                items = func()
                if items: self.cache.set(cacheName, items, expiration=datetime.timedelta(hours=MAX_GUIDEDAYS))
            except Exception as e:
                self.log("fillItems, %s failed! %s"%(type,e), xbmc.LOGERROR)
                items = []
            self.log('_fill, returning %s (%s)'%(type,len(items)))
            return items

        if force: #clear library cache.
            with BUILTIN.busy_dialog():
                __clear()
                
        complete = True 
        self.parserDialog = DIALOG.progressBGDialog(header='%s, %s'%(ADDON_NAME,LANGUAGE(32041)))
        
        types = AUTOTUNE_TYPES
        for idx, type in enumerate(types):
            if self.service._interrupt():
                complete = False
                break
            elif self.service._suspend():
                types.insert(idx, type)
                self.service.monitor.waitForAbort(SUSPEND_TIMER)
                continue
            else:
                msg = LANGUAGE(30014)
                func = self.libraryFUNCS[type]
                cacheName = "%s.%s"%(self.__class__.__name__,func.__name__)
                items = self.cache.get(cacheName)
                if not items: msg = LANGUAGE(32022)
                self.parserMSG    = AUTOTUNE_TYPES[idx]
                self.parserCount  = int(idx*100//len(AUTOTUNE_TYPES))
                self.parserDialog = DIALOG.progressBGDialog(self.parserCount,self.parserDialog,self.parserMSG,header='%s, %s'%(ADDON_NAME,'%s %s'%(msg,LANGUAGE(32041))))
                if not items: items = _fill(type, func)
                self.setLibrary(type, [__update(type,item) for item in items])

        self.parserDialog = DIALOG.progressBGDialog(100,self.parserDialog,LANGUAGE(32025)) 
        self.log('updateLibrary, force = %s, complete = %s'%(force,  complete))
        return  complete
        

    def resetLibrary(self, ATtypes=AUTOTUNE_TYPES):
        self.log('resetLibrary')
        for ATtype in ATtypes: 
            items = self.getLibrary(ATtype)
            for item in items: item['enabled'] = False #disable everything before selecting new items.
            self.setLibrary(ATtype, items)


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
        for tv in [tv for tv in self.getTVGenres() for movie in self.getMovieGenres() if tv.get('name','').lower() == movie.get('name','').lower()]:
            rules = {"800":{"values":{"0":tv.get('name')}}}
            MixedGenreList.append({'name':tv.get('name'),'type':"Mixed Genres",'path':self.predefined.createGenreMixedPlaylist(tv.get('name')),'logo':tv.get('logo'),'rules':rules})
        self.log('getMixedGenres, genres = %s' % (len(MixedGenreList)))
        return sorted(MixedGenreList,key=itemgetter('name'))


    def getMixed(self):
        def __hasRecordings():
            return self.jsonRPC.walkListDirectory('pvr://recordings/tv/active/',appendPath=True)
               
        MixedList = []
        if BUILTIN.hasTV() or BUILTIN.hasMovie():
            MixedList.append({'name':LANGUAGE(32001), 'type':"Mixed",'path':self.predefined.createMixedRecent()  ,'logo':self.resources.getLogo(LANGUAGE(32001),"Mixed")}) #"Recently Added"
            rules = {"800":{"values":{"0":LANGUAGE(32002)}}}
            MixedList.append({'name':LANGUAGE(32002), 'type':"Mixed",'path':self.predefined.createSeasonal()     ,'logo':self.resources.getLogo(LANGUAGE(32002),"Mixed"),'rules':rules}) #"Seasonal"

        # if __hasRecordings(): #broken paths no longer play, Kodi jsonrpc doesn't return valid file and uses unknown vfs assignment
            # MixedList.append({'name':LANGUAGE(32003), 'type':"Mixed",'path':self.predefined.createPVRRecordings(),'logo':self.resources.getLogo(LANGUAGE(32003),"Mixed")}) #"PVR Recordings"
        
        self.log('getMixed, mixed = %s' % (len(MixedList)))
        return sorted(MixedList,key=itemgetter('name'))
    
    
    @cacheit(expiration=datetime.timedelta(minutes=5),json_data=True)
    def getPlaylists(self):
        PlayList = []
        types    = ['video','mixed','music']
        for type in types:
            results = self.jsonRPC.getDirectory(param={"directory":"special://profile/playlists/%s"%(type)})
            for idx, result in enumerate(results.get('files',[])):
                if not self.parserDialog is None:
                    self.parserDialog = DIALOG.progressBGDialog(self.parserCount,self.parserDialog,'%s (%s): %s'%(self.parserMSG,type.title(),int((idx+1)*100//len(results.get('files',[]))))+'%','%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(30014),LANGUAGE(32041))))
                
                if not result.get('label'): continue
                logo = result.get('thumbnail')
                if not logo: logo = self.resources.getLogo(result.get('label'),"Custom")
                PlayList.append({'name':result.get('label'),'type':"%s Playlist"%(type.title()),'path':[result.get('file')],'logo':logo})
        self.log('getPlaylists, PlayList = %s' % (len(PlayList)))
        PlayList = sorted(PlayList,key=itemgetter('name'))
        PlayList = sorted(PlayList,key=itemgetter('type'))
        return PlayList


    @cacheit(expiration=datetime.timedelta(minutes=15),json_data=True)
    def getTVInfo(self, sortbycount=True):
        self.log('getTVInfo')
        if BUILTIN.hasTV():
            NetworkList   = Counter()
            ShowGenreList = Counter()
            TVShows       = Counter()
            json_response = self.jsonRPC.getTVshows()
            
            for idx, info in enumerate(json_response):
                if not self.parserDialog is None:
                    self.parserDialog = DIALOG.progressBGDialog(self.parserCount,self.parserDialog,'%s: %s'%(self.parserMSG,int((idx+1)*100//len(json_response)))+'%','%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(30014),LANGUAGE(32041))))
                
                if not info.get('label'): continue
                TVShows.update({json.dumps({'name': info.get('label'), 'type':"TV Shows", 'path': self.predefined.createShowPlaylist(info.get('label')), 'logo': info.get('art', {}).get('clearlogo', ''),'rules':{"800":{"values":{"0":info.get('label')}}}}): info.get('episode', 0)})
                NetworkList.update([studio for studio in info.get('studio', [])])
                ShowGenreList.update([genre for genre in info.get('genre', [])])

            if sortbycount:
                TVShows = [json.loads(x[0]) for x in sorted(TVShows.most_common(250))]
                NetworkList = [x[0] for x in sorted(NetworkList.most_common(50))]
                ShowGenreList = [x[0] for x in sorted(ShowGenreList.most_common(25))]
            else:
                TVShows = (sorted(map(json.loads, list(TVShows.keys())), key=itemgetter('name')))
                del TVShows[250:]
                NetworkList = (sorted(set(list(NetworkList.keys()))))
                del NetworkList[250:]
                ShowGenreList = (sorted(set(list(ShowGenreList.keys()))))
                
            #search resources for studio/genre logos
            nNetworkList = []
            for network in NetworkList:
                rules = {"800":{"values":{"0":network}}}
                nNetworkList.append({'name':network, 'type':"TV Networks", 'path': self.predefined.createNetworkPlaylist(network),'logo':self.resources.getLogo(network,"TV Networks"),'rules':rules})
            NetworkList = nNetworkList
            
            nShowGenreList = []
            for tvgenre in ShowGenreList:
                rules = {"800":{"values":{"0":tvgenre}}}
                nShowGenreList.append({'name':tvgenre, 'type':"TV Genres"  , 'path': self.predefined.createTVGenrePlaylist(tvgenre),'logo':self.resources.getLogo(tvgenre,"TV Genres"),'rules':rules})
            ShowGenreList = nShowGenreList
            
        else: NetworkList = ShowGenreList = TVShows = []
        self.log('getTVInfo, networks = %s, genres = %s, shows = %s' % (len(NetworkList), len(ShowGenreList), len(TVShows)))
        return {'studios':NetworkList,'genres':ShowGenreList,'shows':TVShows}


    @cacheit(expiration=datetime.timedelta(minutes=15),json_data=True)
    def getMovieInfo(self, sortbycount=True):
        self.log('getMovieInfo')
        if BUILTIN.hasMovie():        
            StudioList     = Counter()
            MovieGenreList = Counter()
            json_response  = self.jsonRPC.getMovies() #we can't parse for genres directly from Kodi json ie.getGenres; because we need the weight of each genre to prioritize list.

            for idx, info in enumerate(json_response):
                if not self.parserDialog is None:
                    self.parserDialog = DIALOG.progressBGDialog(self.parserCount,self.parserDialog,'%s: %s'%(self.parserMSG,int((idx+1)*100//len(json_response)))+'%','%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(30014),LANGUAGE(32041))))
                    
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
            StudioList     = [{'name':studio, 'type':"Movie Studios", 'path': self.predefined.createStudioPlaylist(studio)    ,'logo':self.resources.getLogo(studio,"Movie Studios"),'rules':{"800":{"values":{"0":studio}}}} for studio in StudioList]
            MovieGenreList = [{'name':genre,  'type':"Movie Genres" , 'path': self.predefined.createMovieGenrePlaylist(genre) ,'logo':self.resources.getLogo(genre ,"Movie Genres") ,'rules':{"800":{"values":{"0":genre}}}}  for genre  in MovieGenreList]
            
        else: StudioList = MovieGenreList = []
        self.log('getMovieInfo, studios = %s, genres = %s' % (len(StudioList), len(MovieGenreList)))
        return {'studios':StudioList,'genres':MovieGenreList}
        
        
    @cacheit(expiration=datetime.timedelta(minutes=15),json_data=True)
    def getMusicInfo(self, sortbycount=True):
        self.log('getMusicInfo')
        if BUILTIN.hasMusic():
            MusicGenreList = Counter()
            json_response  = self.jsonRPC.getMusicGenres()
            
            for idx, info in enumerate(json_response):
                if not self.parserDialog is None:
                    self.parserDialog = DIALOG.progressBGDialog(self.parserCount,self.parserDialog,'%s: %s'%(self.parserMSG,int((idx+1)*100//len(json_response)))+'%','%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(30014),LANGUAGE(32041))))
                
                MusicGenreList.update([genre.strip() for genre in info.get('label','').split(';')])
            
            if sortbycount:
                MusicGenreList = [x[0] for x in sorted(MusicGenreList.most_common(50))]
            else:
                MusicGenreList = (sorted(set(list(MusicGenreList.keys()))))
                del MusicGenreList[250:]
                MusicGenreList = (sorted(set(list(MusicGenreList.keys()))))

            #search resources for studio/genre logos
            MusicGenreList = [{'name':genre, 'type':"Music Genres", 'path': self.predefined.createMusicGenrePlaylist(genre),'logo':self.resources.getLogo(genre,"Music Genres")} for genre in MusicGenreList]

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
            # addonMeta = self.jsonRPC.getAddonDetails(addonid)
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
