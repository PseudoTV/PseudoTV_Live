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

# -*- coding: utf-8 -*--

from resources.lib.globals import *

class Predefined:
    def __init__(self, cache=None, config=None):
        self.log('__init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.myConfig    = config
        self.recommended = self.myConfig.recommended
        self.channels    = self.myConfig.channels
        self.jsonRPC     = self.myConfig.jsonRPC
        
        self.TV_Shows          = []
        self.TV_Info           = [[],[]]
        self.MOVIE_Info        = [[],[]]
        self.MUSIC_Info        = []
        self.IPTV_Items        = []
        self.Recommended_Items = []
        self.cItemTemplate     = self.channels.getCitem() #template 

        self.pathTypes = {LANGUAGE(30002)  : self.createNetworkPlaylist,
                          LANGUAGE(30003)  : self.createShowPlaylist,
                          LANGUAGE(30004)  : self.createTVGenrePlaylist,
                          LANGUAGE(30005)  : self.createMovieGenrePlaylist,
                          LANGUAGE(30007)  : self.createStudioPlaylist,
                          LANGUAGE(30006)  : self.createGenreMixedPlaylist,
                          LANGUAGE(30080)  : self.createMixedOther,
                          LANGUAGE(30026)  : self.createRECOMMENDED,
                          LANGUAGE(30097)  : self.createMusicGenrePlaylist}
                        
        self.mixedPaths = {LANGUAGE(30078) : self.createMixedRecent,
                           LANGUAGE(30141) : self.createSeasonal,
                           LANGUAGE(30079) : self.createPVRRecordings} # home for misc. predefined channel paths.
        
        self.exclude_specials = ',{"field":"season","operator":"greaterthan","value":"0"},{"field":"episode","operator":"greaterthan","value":"0"}'
        log('__init__, exclude_specials = %s'%(self.exclude_specials))
    
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def createMixedOther(self, type):
        return self.mixedPaths[type]()
        
        
    def createRECOMMENDED(self, type):
        return []
        
    
    def createPVRRecordings(self):
        return 'pvr://recordings/tv/active/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"random"}}'
        
        
    def createMixedRecent(self):
        return ['videodb://recentlyaddedepisodes/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"episode"}}',
                'videodb://recentlyaddedmovies/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"random"}}']
        
        
    def createMusicRecent(self):
        return 'musicdb://recentlyaddedalbums/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"random"}}'
        
        
    def createNetworkPlaylist(self, network, method='episode'):
        return 'videodb://tvshows/studios/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"studio","operator":"is","value":["%s"]}%s]},"type":"episodes"}'%(method,urllib.parse.quote(network),self.exclude_specials)
        

    def createShowPlaylist(self, show, method='episode'):
        return 'videodb://tvshows/titles/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"tvshow","operator":"is","value":["%s"]}%s]},"type":"episodes"}'%(method,urllib.parse.quote(show),self.exclude_specials)


    def createTVGenrePlaylist(self, genre, method='episode'):
        return 'videodb://tvshows/titles/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"is","value":["%s"]}%s]},"type":"episodes"}'%(method,urllib.parse.quote(genre),self.exclude_specials)


    def createMovieGenrePlaylist(self, genre, method='random'):
        return 'videodb://movies/titles/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"is","value":["%s"]}]},"type":"movies"}'%(method,urllib.parse.quote(genre))


    def createStudioPlaylist(self, studio, method='random'):
        return 'videodb://movies/titles/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"studio","operator":"is","value":["%s"]}]},"type":"movies"}'%(method,urllib.parse.quote(studio))


    def createMusicGenrePlaylist(self, genre, method='random'):
        return 'musicdb://songs/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"contains","value":["%s"]}]},"type":"music"}'%(method,urllib.parse.quote(genre))


    def createGenreMixedPlaylist(self, genre):
        return [self.createTVGenrePlaylist(genre),self.createMovieGenrePlaylist(genre)]
        
        
    def createSeasonal(self):
        return 'plugin://script.embuary.helper/?info=getseasonal&amp;list={list}&limit={limit}'
        

    def getfillItems(self, type=None):
        #heavy call functions init. #todo improve by converting to dict not lists, don't call methods during call.
        items = {LANGUAGE(30002):self.getTVInfo()[0],
                 LANGUAGE(30003):self.getTVShows(),
                 LANGUAGE(30004):self.getTVInfo()[1],
                 LANGUAGE(30005):self.getMovieInfo()[1],
                 LANGUAGE(30007):self.getMovieInfo()[0],
                 LANGUAGE(30006):self.makeMixedList(self.getTVInfo()[1], self.getMovieInfo()[1]),
                 LANGUAGE(30080):self.getMixedMisc(),
                 LANGUAGE(30097):self.getMusicGenres(),
                 LANGUAGE(30026):self.getRecommended(),
                 LANGUAGE(30033):self.getImports()}
        if type is not None: return items[type]
        return items
                
        
    def groupImports(self):
        self.log('groupImports')
        items = {LANGUAGE(30033):[]}
        imports = self.channels.getImports()
        for item in imports: items[LANGUAGE(30033)].append(item)
        return items


    def getImports(self):
        self.log('getImports')
        if len(self.IPTV_Items) == 0: 
            self.IPTV_Items = self.recommended.getDataType()
        self.IPTV_Items.sort(key=lambda x:x['item']['name'])
        iptv = [item.get('item',{}).get('name') for item in self.IPTV_Items]
        self.log('getImports, found = %s'%(len(iptv)))
        return iptv
        
        
    def getRecommended(self):
        self.log('getRecommended')
        if len(self.Recommended_Items) == 0: 
            self.Recommended_Items = self.recommended.fillRecommended()
        self.Recommended_Items.sort(key=lambda x:x['item']['name'])
        recommended = [recommended['item']['name'] for recommended in self.Recommended_Items]
        self.log('getRecommended, found = %s'%(len(recommended)))
        return recommended


    def getTVShows(self):
        if len(self.TV_Shows) == 0: 
            self.TV_Shows = self.jsonRPC.fillTVShows()
        self.TV_Shows.sort(key=lambda x:x['label'])
        shows = [show['label'] for show in self.TV_Shows]
        self.log('getTVShows, found = %s'%(len(shows)))
        return shows
 
 
    def getTVInfo(self):
        if (len(self.TV_Info[0]) == 0 or len(self.TV_Info[1]) == 0): 
            self.TV_Info = self.jsonRPC.getTVInfo()
        self.log('getTVInfo, networks = %s, genres = %s'%(len(self.TV_Info[0]),len(self.TV_Info[1])))
        return self.TV_Info
 
 
    def getMovieInfo(self):
        if (len(self.MOVIE_Info[0]) == 0 or len(self.MOVIE_Info[1]) == 0): 
            self.MOVIE_Info = self.jsonRPC.getMovieInfo()
        self.log('getMovieInfo, studios = %s, genres = %s'%(len(self.MOVIE_Info[0]),len(self.MOVIE_Info[1])))
        return self.MOVIE_Info
 
 
    def getMixedMisc(self):
        return [LANGUAGE(30078),LANGUAGE(30141),LANGUAGE(30079)]
 
 
    def getMusicGenres(self):
        if len(self.MUSIC_Info) == 0: 
            self.MUSIC_Info = self.jsonRPC.fillMusicInfo()
        self.log('getMusicGenres, genres = %s'%(len(self.MUSIC_Info)))
        return self.MUSIC_Info
        

    def makeMixedList(self, list1, list2):
        newlist = []
        for item in list1:
            for a in list2:
                if item.lower() == a.lower():
                    newlist.append(item)
                    break
        self.log('makeMixedList, genres = %s'%(','.join(newlist)))
        return newlist
        
        
    def getChannelPostfix(self, name, type):
        if   type == LANGUAGE(30004): suffix = LANGUAGE(30155) #tv
        elif type == LANGUAGE(30005): suffix = LANGUAGE(30156) #movie
        elif type == LANGUAGE(30097): suffix = LANGUAGE(30157) #music
        else: return name
        return '%s %s'%(name,suffix)
               

    def getChannelsbyKey(self, type, key='name', predefined=None):
        self.log('getChannelsbyKey, type = %s, key = %s'%(type,key))
        if type == LANGUAGE(30033):
            predefined = self.groupImports()
        else:
            predefined = self.groupChannelsbyType()
        for channel in predefined[type]: 
            yield channel.get(key,'')
    
    
    def buildAvailableRange(self, type, blist, size=1):
        start = ((CHANNEL_LIMIT+1)*(CHAN_TYPES.index(type)+1))
        stop  = (start + CHANNEL_LIMIT)
        return list(set(range(start,stop)).difference(blist))
            

    def groupChannelsbyType(self):
        self.log('groupChannelsbyType')
        items    = {}
        channels = self.channels.getPredefinedChannels()
        for type in CHAN_TYPES:  items[type] = []
        for channel in channels: 
            if channel.get('type','') in CHAN_TYPES: 
                items[channel.get('type','')].append(channel)
        return items
        
        
    def findChannel(self, citem, type, channels=None):
        self.log('findChannel, item = %s, type = %s'%(citem,type))
        if channels is None:
            channels = self.groupChannelsbyType()[type]
        for idx, item in enumerate(channels):
            if (item['id'] == citem['id']) or (item['type'].lower() == citem['type'].lower() and item['name'].lower() == citem['name'].lower() and item['path'].lower() == citem['path'].lower()):
                return idx, item
        return None, {}
        
        
    def buildPredefinedItems(self):        
        busy = ProgressBGDialog(message='%s...'%(LANGUAGE(30158)))
        for idx, type in enumerate(CHAN_TYPES):
            self.log('buildPredefinedItems, type = %s'%(type))
            busy     = ProgressBGDialog((idx*100//len(CHAN_TYPES)), busy, LANGUAGE(30159)%(type))
            existing = self.getPredefinedItems(type,enabled=False)
            items    = self.getfillItems(type) #current items
            bpitems  = (PoolHelper().poolList(self.buildPredefinedItem,items,[type,existing]))
            self.savePredefinedItems(bpitems,type)
        ProgressBGDialog(100, busy, '%s...'%(LANGUAGE(30158)))
            
            
    def buildPredefinedItem(self, data):
        name, meta = data
        type, existing = meta
        enabled = False
        eitem = list(filter(lambda e:e.get('name','') == name, existing))
        if eitem: enabled = eitem[0].get('enabled',False)
        return {'enabled':enabled,'name':name,'type':type,'logo':self.jsonRPC.getLogo(name, type)}
    

    def savePredefinedItems(self, items, type):
        self.log('savePredefinedItems, type = %s, items = %s'%(type, len(items)))
        return self.channels.setPredefinedItems(type, items)


    def buildImports(self):
        self.log('buildImports')
        if len(self.IPTV_Items) == 0: 
            self.IPTV_Items = self.recommended.getDataType()
        imports = self.getPredefinedItems(LANGUAGE(30033), enabled=True) #current items
        print(self.IPTV_Items,imports)
        return self.channels.setImports([item['data'] for item in self.IPTV_Items for eimport in imports if ((item.get('data',{}).get('name','').startswith(eimport.get('name'))) and (item['data'].get('type','').lower() == 'iptv'))])


    def buildPredefinedChannels(self):
        predefined = []
        existing = self.groupChannelsbyType() # existing channels, avoid duplicates, aid in removal.
        types = list(filter(lambda k:k != LANGUAGE(30033), CHAN_TYPES))
        for type in types:
            self.log('buildPredefinedList, type = %s'%(type))
            echannels = existing[type]
            enumbers  = [echannel.get('number') for echannel in echannels if echannel.get('number',0) > 0] #existing channel numbers
            items     = self.getPredefinedItems(type, enabled=True) #current items
            citems    = sorted(PoolHelper().poolList(self.buildPredefinedChannel,items,type), key=lambda k: k['name'])
            numbers   = iter(self.buildAvailableRange(type,enumbers,len(items))) #list of available channel numbers 
            
            for citem in citems:
                match, eitem = self.findChannel(citem, type, echannels)
                if match is not None:
                    for key in ['rules','number','favorite','page']: #update new citems with existing values.
                        citem[key] = eitem[key]
                else: citem['number'] = next(numbers,0)
                predefined.append(citem)
        return self.setPredefinedChannels(predefined)
          
          
    def buildPredefinedChannel(self, data):
        item, type = data
        if type not in self.pathTypes.keys(): return None
        citem = self.cItemTemplate.copy()
        del citem['xmltv'] #not needed for predefined channel
        citem.update({'name'   :self.getChannelPostfix(item['name'], type),
                      'path'   :self.pathTypes[type](item['name']),
                      'type'   :item['type'],
                      'logo'   :item['logo'],
                      'group'  :[type]})
                      
        citem['radio']   = (type == LANGUAGE(30097) or 'musicdb://' in citem['path'])
        citem['catchup'] = ('vod' if not citem['radio'] else '')
        citem['id']      = getChannelID(citem['name'], citem['path'], citem['number'])
        return citem
                             
                    
    def setPredefinedChannels(self, channels):
        self.log('setPredefinedChannels, channels = %s'%(len(channels)))
        return self.channels.setPredefinedChannels(channels)
        

    def getPredefinedItems(self, type, enabled=True):
        self.log('getPredefinedItems, type = %s, enabled = %s'%(type,enabled))
        items = self.channels.getPredefinedItems(type)
        if enabled:
            items = list(filter(lambda k:k.get('enabled',False) == True, items))
        return sorted(items, key=lambda k: k['name'])


    def enableChannels(self, type, items, selects):
        self.log('enableChannels, type = %s, items = %s, selects = %s'%(type, len(items), selects))
        for idx, item in enumerate(items):
            if idx in selects:
                item['enabled'] = True
            else:
                item['enabled'] = False
            yield item