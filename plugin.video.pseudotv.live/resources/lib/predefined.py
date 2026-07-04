#   Copyright (C) 2026 Lunatixz
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

from variables import *

class Predefined(object):
    @staticmethod
    def getTemplete():
        return {"type":"","rules":{"and":[],"or":[]},"order":{"direction":"ascending","method":"random","ignorearticle":True,"useartistsortname":True}}


    @staticmethod
    def createRECOMMENDED(type: str) -> list:
        return []
        

    @staticmethod
    def createMixedRecent() -> list:
        param = Predefined.getTemplete()
        tv = param.copy()
        tv["order"]["method"] = "episode"
        return ['videodb://recentlyaddedepisodes/?xsp=%s'%(FileAccess.dumpJSON(tv)),
                'videodb://recentlyaddedmovies/?xsp=%s'%(FileAccess.dumpJSON(param))]
        
        
    @staticmethod
    def createMusicRecent() -> list:
        param = Predefined.getTemplete()
        param["order"]["method"] = "dateadded"
        param["order"]["direction"] = "descending"
        return ['musicdb://songs/?xsp=%s'%(FileAccess.dumpJSON(param))]
        
        
    @staticmethod
    def createNetworkPlaylist(network: str, method: str='episode') -> list:
        param = Predefined.getTemplete()
        param["type"] = "episodes"
        param["order"]["method"] = method
        param.setdefault("rules",{}).setdefault("and",[]).append({"field":"studio","operator":"contains","value":[Globals._quoteString(network)]})
        return ['videodb://tvshows/studios/-1/-1/-1/?xsp=%s'%(FileAccess.dumpJSON(param))]


    @staticmethod
    def createShowPlaylist(show: str, method: str='episode') -> list:
        param = Predefined.getTemplete()
        param["type"] = "episodes"
        param["order"]["method"] = method
        try:
            match = re.compile(r'(.*) \((.*)\)', re.IGNORECASE).search(show)
            year, title = int(match.group(2)), match.group(1)
            param.setdefault("rules",{}).setdefault("and",[]).extend([{"field":"year","operator":"is","value":[year]},{"field":"tvshow","operator":"is","value":[Globals._quoteString(title)]}])
        except Exception:
            param.setdefault("rules",{}).setdefault("and",[]).append({"field":"tvshow","operator":"is","value":[Globals._quoteString(show)]})
        return ['videodb://tvshows/titles/-1/-1/-1/?xsp=%s'%(FileAccess.dumpJSON(param))]


    @staticmethod
    def createTVGenrePlaylist(genre: str, method: str='episode') -> list:
        param = Predefined.getTemplete()
        param["type"] = "episodes"
        param["order"]["method"] = method
        param.setdefault("rules",{}).setdefault("and",[]).append({"field":"genre","operator":"contains","value":[Globals._quoteString(genre)]})
        return ['videodb://tvshows/genres/-1/-1/-1/?xsp=%s'%(FileAccess.dumpJSON(param))]


    @staticmethod
    def createMovieGenrePlaylist(genre: str, method: str='random') -> list:
        param = Predefined.getTemplete()
        param["type"] = "movies"
        param["order"]["method"] = method
        param.setdefault("rules",{}).setdefault("and",[]).append({"field":"genre","operator":"contains","value":[Globals._quoteString(genre)]})
        return ['videodb://movies/genres/-1/-1/-1/?xsp=%s'%(FileAccess.dumpJSON(param))]


    @staticmethod
    def createStudioPlaylist(studio: str, method: str='random') -> list:
        param = Predefined.getTemplete()
        param["type"] = "movies"
        param["order"]["method"] = method
        param.setdefault("rules",{}).setdefault("and",[]).append({"field":"studio","operator":"contains","value":[Globals._quoteString(studio)]})
        return ['videodb://movies/studios/-1/-1/-1/?xsp=%s'%(FileAccess.dumpJSON(param))]


    @staticmethod
    def createMusicGenrePlaylist(genre: str, method: str='random') -> list:
        param = Predefined.getTemplete()
        param["type"] = "music"
        param["order"]["method"] = method
        param.setdefault("rules",{}).setdefault("and",[]).append({"field":"genre","operator":"contains","value":[Globals._quoteString(genre)]})
        return ['musicdb://songs/?xsp=%s'%(FileAccess.dumpJSON(param))]


    @staticmethod
    def createGenreMixedPlaylist(genre: str) -> list:
        mixed = Predefined.createTVGenrePlaylist(genre)
        mixed.extend(Predefined.createMovieGenrePlaylist(genre))
        return mixed
        
        
    @staticmethod
    def createSeasonal() -> list:
        return ["{Seasonal}"]
        
        
    @staticmethod
    def createProvisional(value: str) -> list:
        return ["{%s}"%(value)]