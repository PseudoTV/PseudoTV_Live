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

# -*- coding: utf-8 -*--

from globals    import *

class Predefined:
    def __init__(self):
        ...
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

        
    def getParams(self) -> dict:
        params = {}
        params["order"] = {"direction"        :"ascending",
                           "method"           :"random",
                           "ignorearticle"    :True,
                           "useartistsortname":True}
        return params.copy()


    def createRECOMMENDED(self, type: str) -> list:
        return []
        
    
    def createPVRRecordings(self) -> list:
        return ['pvr://recordings/tv/active/?xsp=%s'%(dumpJSON(self.getParams()))]
        
        
    def createMixedRecent(self) -> list:
        param = self.getParams()
        param["order"]["method"] = "episode"
        return ['videodb://recentlyaddedepisodes/?xsp=%s'%(dumpJSON(param)),
                'videodb://recentlyaddedmovies/?xsp=%s'%(dumpJSON(self.getParams()))]
        
        
    def createMusicRecent(self) -> list:
        return ['musicdb://recentlyaddedalbums/?xsp=%s'%(dumpJSON(self.getParams()))]
        
        
    def createNetworkPlaylist(self, network: str, method: str='episode') -> list:
        param = self.getParams()
        param["type"] = "episodes"
        param["order"]["method"] = method
        param.setdefault("rules",{}).setdefault("and",[]).append({"field":"studio","operator":"contains","value":[quoteString(network)]})
        return ['videodb://tvshows/studios/-1/-1/-1/?xsp=%s'%(dumpJSON(param))]


    def createShowPlaylist(self, show: str, method: str='episode') -> list:
        param = self.getParams()
        param["type"] = "episodes"
        param["order"]["method"] = method
        try:
            match = re.compile(r'(.*) \((.*)\)', re.IGNORECASE).search(show)
            year, title = int(match.group(2)), match.group(1)
            param.setdefault("rules",{}).setdefault("and",[]).extend([{"field":"year","operator":"is","value":[year]},{"field":"tvshow","operator":"is","value":[quoteString(title)]}])
        except:
            param.setdefault("rules",{}).setdefault("and",[]).append({"field":"tvshow","operator":"is","value":[quoteString(show)]})
        return ['videodb://tvshows/titles/-1/-1/-1/?xsp=%s'%(dumpJSON(param))]


    def createTVGenrePlaylist(self, genre: str, method: str='episode') -> list:
        param = self.getParams()
        param["type"] = "episodes"
        param["order"]["method"] = method
        param.setdefault("rules",{}).setdefault("and",[]).append({"field":"genre","operator":"contains","value":[quoteString(genre)]})
        return ['videodb://tvshows/genres/-1/-1/-1/?xsp=%s'%(dumpJSON(param))]


    def createMovieGenrePlaylist(self, genre: str, method: str='year') -> list:
        param = self.getParams()
        param["type"] = "movies"
        param["order"]["method"] = method
        param.setdefault("rules",{}).setdefault("and",[]).append({"field":"genre","operator":"contains","value":[quoteString(genre)]})
        return ['videodb://movies/genres/?xsp=%s'%(dumpJSON(param))]


    def createStudioPlaylist(self, studio: str, method: str='random') -> list:
        param = self.getParams()
        param["type"] = "movies"
        param["order"]["method"] = method
        param.setdefault("rules",{}).setdefault("and",[]).append({"field":"studio","operator":"contains","value":[quoteString(studio)]})
        return ['videodb://movies/studios/?xsp=%s'%(dumpJSON(param))]


    def createMusicGenrePlaylist(self, genre: str, method: str='random') -> list:
        param = self.getParams()
        param["type"] = "music"
        param["order"]["method"] = method
        param.setdefault("rules",{}).setdefault("and",[]).append({"field":"genre","operator":"contains","value":[quoteString(genre)]})
        return ['musicdb://songs/?xsp=%s'%(dumpJSON(param))]


    def createGenreMixedPlaylist(self, genre: str) -> list:
        mixed = self.createTVGenrePlaylist(genre)
        mixed.extend(self.createMovieGenrePlaylist(genre))
        return mixed
        
        
    def createSeasonal(self) -> list:
        return ["{Seasonal}"]
        
        
    def createProvisional(self, value: str) -> list:
        return ["{%s}"%(value)]