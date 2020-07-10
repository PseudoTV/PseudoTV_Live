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

from resources.lib.parser  import JSONRPC
from resources.lib.rules   import *
from resources.lib.globals import *

class Predefined:
    def __init__(self): 
        self.jsonRPC = JSONRPC()
        self.types    = {'TV_Networks'   : self.createNetworkPlaylist,
                         'TV_Genres'     : self.createTVGenrePlaylist,
                         'MOVIE_Genres'  : self.createMovieGenrePlaylist,
                         'MIXED_Genres'  : self.createGenreMixedPlaylist,
                         'MOVIE_Studios' : self.createStudioPlaylist,
                         'TV_Shows'      : self.createShowPlaylist,
                         'MIXED_Other'   : self.createMixedOther,
                         'MUSIC_Genres'  : self.createMusicGenrePlaylist}
                        
        self.others   = {LANGUAGE(30078) : self.createMixedRecent,
                         LANGUAGE(30079) : self.createPVRRecordings} # home for misc. predefined channel paths. todo seasonal channel

        if INCLUDE_EXTRAS:
            self.specials = ',{"field":"season","operator":"greaterthan","value":"0"},{"field":"episode","operator":"greaterthan","value":"0"}'
        else:
            self.specials = ''
        log('__init__, specials = %s'%(self.specials))
    
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def buildChannelList(self):
        channels = []
        for type, func in self.types.items():
            chitems = []
            items = sorted(getSetting('Setting_%s'%(type)).split('|'))
            log('buildChannelList, building %s, found %s'%(type,items))
            for item in items:
                if len(item) == 0: continue
                type     = type.replace('_',' ')
                chpath   = func(item)
                radio    = type == 'MUSIC Genres'
                chnumber = random.sample(CHANNEL_RANGE,1)[0]# assign random channel number to dynamic predefined channels
                chlogo   = self.jsonRPC.getLogo(item, type, featured=True)
                chname   = self.getChannelSuffix(item, type)
                chgroups = [type]
                chitems.append({'name':chname,'number':chnumber,'path':chpath,'logo':chlogo,'type':type,'radio':radio,'groups':chgroups})
            channels.extend(sorted(chitems, key=lambda k: k['name']))
        return channels
        

    def getChannelSuffix(self, name, type):
        suffix = ''
        if   type == 'TV Genres':    suffix = ' TV'
        elif type == 'MOVIE Genres': suffix = ' Movies'
        return '%s%s'%(name,suffix)
        
        
    def createMixedOther(self, type):
        return self.others[type]()
        
    
    def createPVRRecordings(self):
        return 'pvr://recordings/tv/active/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"random"}}'
        
        
    def createMixedRecent(self):
        return ['videodb://recentlyaddedepisodes/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"episode"}}',
                'videodb://recentlyaddedmovies/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"random"}}']
        
        
    def createMusicRecent(self):
        return 'musicdb://recentlyaddedalbums/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"random"}}'
        
        
    def createNetworkPlaylist(self, network, method='episode'):
        return 'videodb://tvshows/studios/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"studio","operator":"is","value":["%s"]}%s]},"type":"episodes"}'%(method,urllib.parse.quote(network),self.specials)
        

    def createShowPlaylist(self, show, method='episode'):
        return 'videodb://tvshows/titles/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"tvshow","operator":"is","value":["%s"]}%s]},"type":"episodes"}'%(method,urllib.parse.quote(show),self.specials)


    def createTVGenrePlaylist(self, genre, method='episode'):
        return 'videodb://tvshows/titles/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"is","value":["%s"]}%s]},"type":"episodes"}'%(method,urllib.parse.quote(genre),self.specials)


    def createMovieGenrePlaylist(self, genre, method='random'):
        return 'videodb://movies/titles/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"is","value":["%s"]}]},"type":"movies"}'%(method,urllib.parse.quote(genre))


    def createStudioPlaylist(self, studio, method='random'):
        return 'videodb://movies/titles/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"studio","operator":"is","value":["%s"]}]},"type":"movies"}'%(method,urllib.parse.quote(studio))


    def createMusicGenrePlaylist(self, genre, method='random'):
        return 'musicdb://songs/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"is","value":["%s"]}]},"type":"music"}'%(method,urllib.parse.quote(genre))


    def createGenreMixedPlaylist(self, genre):
        return [self.createTVGenrePlaylist(genre),self.createMovieGenrePlaylist(genre)]