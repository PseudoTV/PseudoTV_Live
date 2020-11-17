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
from resources.lib.rules   import *
from resources.lib.parser  import Channels
from resources.lib.jsonrpc import JSONRPC

class Predefined:
    def __init__(self, cache=None):
        self.log('__init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.jsonRPC  = JSONRPC(self.cache)
        self.channels = Channels(self.cache)
        self.types    = {'TV Networks'       : self.createNetworkPlaylist,
                         'TV Shows'          : self.createShowPlaylist,
                         'TV Genres'         : self.createTVGenrePlaylist,
                         'Movie Genres'      : self.createMovieGenrePlaylist,
                         'Movie Studios'     : self.createStudioPlaylist,
                         'Mixed Genres'      : self.createGenreMixedPlaylist,
                         'Mixed'             : self.createMixedOther,
                         'Recommended'       : self.createRECOMMENDED,
                         'Music Genres'      : self.createMusicGenrePlaylist}
                        
        self.others   = {LANGUAGE(30078) : self.createMixedRecent,
                         LANGUAGE(30141) : self.createSeasonal,
                         LANGUAGE(30079) : self.createPVRRecordings} # home for misc. predefined channel paths. todo seasonal channel
        
        self.exclude_specials = ',{"field":"season","operator":"greaterthan","value":"0"},{"field":"episode","operator":"greaterthan","value":"0"}'
        log('__init__, exclude_specials = %s'%(self.exclude_specials))
    
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
        
    def getChannelPostfix(self, name, type):
        suffix = ''
        if   type == 'TV Genres':    suffix = ' TV'
        elif type == 'Movie Genres': suffix = ' Movies'
        return '%s%s'%(name,suffix)
               
    
    def groupChannelTypes(self):
        self.log('groupChannelTypes')
        items    = {}
        channels = self.channels.getPredefined()
        for type in CHAN_TYPES:  items[type] = []
        for channel in channels: 
            if channel.get('type','') in CHAN_TYPES: 
                items[channel.get('type','')].append(channel)
        return items
        
        
    def groupImports(self):
        self.log('groupImports')
        items  = {'IPTV':[]}
        imports = self.channels.getImports()
        for item in imports: items['IPTV'].append(item)
        return items


    def getChannelbyKey(self, type, key='name'):
        self.log('getChannelbyKey, type = %s, key = %s'%(type,key))
        if type == 'IPTV':
            predefined = self.groupImports()
        else:
            predefined = self.groupChannelTypes()
        for channel in predefined[type]: 
            yield channel.get(key,'')
    
    
    def buildAvailableRange(self, type, blist, size=1):
        start = ((CHANNEL_LIMIT+1)*(CHAN_TYPES.index(type)+1))
        stop  = (start + CHANNEL_LIMIT)
        return random.sample(list(set(range(start,stop)).difference(blist)),size)
        
        
    def findChannel(self, citem, type, channels=None):
        self.log('findChannel, item = %s, type = %s'%(citem,type))
        if channels is None:
            channels = self.groupChannelTypes[type]
        for idx, item in enumerate(channels):
            if (item['id'] == citem['id']) or (item['type'].lower() == citem['type'].lower() and item['name'].lower() == citem['name'].lower() and item['path'] == citem['path']):
                return idx, item
        return None, {}
        
        
    def setChannels(self, items, type):
        self.log('setChannels, type = %s, items = %s'%(type,items))
        # save predefined selections to channels.json. preserve existing channel numbers, remove missing, update existing.
        if self.channels.reset():
            if type == 'IPTV':
                imports = self.channels.recommended.getData()
                if self.channels.resetImports():
                    [self.channels.addImport(item['data']) for item in imports for name in items if item['item'].get('name','').lower() == name.lower()]
            else:
                existing = self.groupChannelTypes()[type] # existing channels, avoid duplicates, aid in removal.
                reserved = list(self.getChannelbyKey(type,'number')) # channel numbers in-use.
                chnums   = self.buildAvailableRange(type,reserved,len(items)) # create sample array of channel numbers in a given field, minus existing numbers.
                self.log('setChannels, building %s, found %s'%(type,items))
                
                for idx, item in enumerate(items):
                    if not item: continue
                    citem = self.channels.getCitem() #template 
                    citem.update({'number' :chnums[idx],
                                  'name'   :self.getChannelPostfix(item, type),
                                  'path'   :self.types[type](item),
                                  'type'   :type,
                                  'logo'   :self.jsonRPC.getLogo(item, type, featured=True),
                                  'group'  :[type]})
                                  
                    citem['radio']   = (type == 'Music Genres' or 'musicdb://' in citem['path'])
                    citem['catchup'] = ('vod' if not citem['radio'] else '')
                    citem['id']      = getChannelID(citem['name'], citem['path'], citem['number'])
                    match, eitem = self.findChannel(citem, type, existing)
                    if match is not None:# copy existing static values to dynamic channel
                        citem['number'] = eitem['number']
                        citem['rules']  = eitem['rules']
                        existing.pop(match)
                    citem['id'] = getChannelID(citem['name'], citem['path'], citem['number']) #id must represent current values.
                    self.channels.add(citem)
                [self.channels.remove(eitem) for eitem in existing] # removed abandoned channels
            return self.channels.save()
        
        
    def createMixedOther(self, type):
        return self.others[type]()
        
        
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
        return ['plugin://script.embuary.helper/?info=getseasonal&amp;list={list}&limit={limit}']