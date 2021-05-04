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
    def __init__(self):
        self.log('__init__')
        self.pathTypes  = {LANGUAGE(30002): self.createNetworkPlaylist,
                           LANGUAGE(30003): self.createShowPlaylist,
                           LANGUAGE(30004): self.createTVGenrePlaylist,
                           LANGUAGE(30005): self.createMovieGenrePlaylist,
                           LANGUAGE(30007): self.createStudioPlaylist,
                           LANGUAGE(30006): self.createGenreMixedPlaylist,
                           LANGUAGE(30080): self.createMixedOther,
                           LANGUAGE(30026): self.createRECOMMENDED,
                           LANGUAGE(30097): self.createMusicGenrePlaylist}
                        
        self.mixedPaths = {LANGUAGE(30078): self.createMixedRecent,
                           LANGUAGE(30141): self.createSeasonal,
                           LANGUAGE(30079): self.createPVRRecordings} # home for misc. predefined channel paths.
        
        self.exclude_specials = ',{"field":"season","operator":"greaterthan","value":"0"},{"field":"episode","operator":"greaterthan","value":"0"}'
        log('__init__, exclude_specials = %s'%(self.exclude_specials))
    
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def createMixedOther(self, type):
        return self.mixedPaths[type]()
        
        
    def createRECOMMENDED(self, type):
        return []
        
    
    @staticmethod
    def createPVRRecordings():
        return ['pvr://recordings/tv/active/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"random"}}']
        
        
    @staticmethod
    def createMixedRecent():
        return ['videodb://recentlyaddedepisodes/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"episode"}}',
                'videodb://recentlyaddedmovies/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"random"}}']
        
        
    @staticmethod
    def createMusicRecent():
        return ['musicdb://recentlyaddedalbums/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"random"}}']
        
        
    def createNetworkPlaylist(self, network, method='episode'):
        return ['videodb://tvshows/studios/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"studio","operator":"contains","value":["%s"]}%s]},"type":"episodes"}'%(method,urllib.parse.quote(network),self.exclude_specials)]
        

    def createShowPlaylist(self, show, method='episode'):
        match = re.compile('(.*) \((.*)\)', re.IGNORECASE).search(show)
        try:    return ['videodb://tvshows/titles/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"year","operator":"is","value":["%s"]},{"field":"tvshow","operator":"is","value":["%s"]}%s]},"type":"episodes"}'%(method,match.group(2),urllib.parse.quote(match.group(1)),self.exclude_specials)]
        except: return ['videodb://tvshows/titles/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"tvshow","operator":"is","value":["%s"]}%s]},"type":"episodes"}'%(method,urllib.parse.quote(show),self.exclude_specials)]


    def createTVGenrePlaylist(self, genre, method='episode'):
        return ['videodb://tvshows/titles/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"contains","value":["%s"]}%s]},"type":"episodes"}'%(method,urllib.parse.quote(genre),self.exclude_specials)]


    @staticmethod
    def createMovieGenrePlaylist(genre, method='random'):
        return ['videodb://movies/titles/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"contains","value":["%s"]}]},"type":"movies"}'%(method,urllib.parse.quote(genre))]


    @staticmethod
    def createStudioPlaylist(studio, method='random'):
        return ['videodb://movies/titles/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"studio","operator":"contains","value":["%s"]}]},"type":"movies"}'%(method,urllib.parse.quote(studio))]


    @staticmethod
    def createMusicGenrePlaylist(genre, method='random'):
        return ['musicdb://songs/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"contains","value":["%s"]}]},"type":"music"}'%(method,urllib.parse.quote(genre))]


    def createGenreMixedPlaylist(self, genre):
        mixed = self.createTVGenrePlaylist(genre)
        mixed.extend(self.createMovieGenrePlaylist(genre))
        return mixed
        
        
    @staticmethod
    def createSeasonal():
        return [LANGUAGE(30174)]