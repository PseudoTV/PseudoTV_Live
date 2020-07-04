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

from parsers import JSONRPC
from rules import *
from globals import *

class Predefined:
    def __init__(self): 
        self.jsonRPC = JSONRPC()
        self.types = {'TV_Networks'   : self.createNetworkPlaylist,
                      'TV_Genres'     : self.createTVGenrePlaylist,
                      'MOVIE_Genres'  : self.createMovieGenrePlaylist,
                      'MIXED_Genres'  : self.createGenreMixedPlaylist,
                      'MOVIE_Studios' : self.createStudioPlaylist,
                      'TV_Shows'      : self.createShowPlaylist}

    def loadRules(self, channelID):
        ruleList  = []
        listrules = RulesList()
        try:
            rulecount = int(getSetting('Channel_%s_rulecount'%(channelID)))
            for i in range(rulecount):
                ruleid = int(getSetting('Channel_%s_rule_%s_id'%(channelID,i + 1)))

                for rule in listrules.ruleList:
                    if rule.getId() == ruleid:
                        ruleList.append(rule.copy())

                        for x in range(rule.getOptionCount()):
                            ruleList[-1].optionValues[x] = getSetting('Channel_%s_rule_%s_opt_%s'%(channelID,i + 1,x + 1))
                        break
        except: ruleList = []
        return ruleList
        
        
    def buildChannelList(self):
        #todo build other types "recommended", "custom"
        return self.buildPredefinedChannels()
        
        
    def buildPredefinedChannels(self):
        channels = []
        for type, func in self.types.items():
            chitems = []
            items = getSetting('Setting_%s'%(type)).split('|')
            log('Predefined : buildPredefinedChannels, building %s, found %s'%(type,items))
            for item in items:
                if len(item) == 0: continue
                type     = type.replace('_',' ')
                chpath   = func(item)
                chrules  = []
                genre    = []
                chnumber = 0 # predefined are assigned 0
                chlogo   = self.jsonRPC.getLogo(item, type, featured=True)
                chname   = self.getChannelSuffix(item, type)
                chitems.append({'name':chname,'number':chnumber,'rules':chrules,'path':chpath,'logo':chlogo,'genre':genre,'type':type})
            channels.extend(sorted(chitems, key=lambda k: k['name']))
        return channels
        
        
    def buildCustomChannels(self):
        log('Predefined : buildCustomChannels')
        #item = {'name':chname,'rules':{},'path':chpath,'logo':chlogo}
        # item['type'] = 'Custom'
        # item['id']   = getChannelID(item['name'], item['path'])
        

    def getChannelSuffix(self, name, type):
        suffix = ''
        if   type == 'TV Genres':    suffix = ' TV'
        elif type == 'MOVIE Genres': suffix = ' Movies'
        return '%s%s'%(name,suffix)
        
        
    def createPVRRecordings(self):
        return 'pvr://recordings/tv/active/'
        
        
    def createMixedRecent(self):
        return ['videodb://recentlyaddedepisodes/','videodb://recentlyaddedmovies/']
        
        
    def createNetworkPlaylist(self, network, method='episode'):
        return 'videodb://tvshows/studios/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"studio","operator":"is","value":["%s"]}]},"type":"episodes"}'%(method,urllib.parse.quote(network))
        

    def createShowPlaylist(self, show, method='episode'):
        return 'videodb://tvshows/titles/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"tvshow","operator":"is","value":["%s"]}]},"type":"episodes"}'%(method,urllib.parse.quote(show))


    def createTVGenrePlaylist(self, genre, method='episode'):
        return 'videodb://tvshows/titles/-1/-1/-1/-1/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"is","value":["%s"]}]},"type":"episodes"}'%(method,urllib.parse.quote(genre))


    def createMovieGenrePlaylist(self, genre, method='random'):
        return 'videodb://movies/titles/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"genre","operator":"is","value":["%s"]}]},"type":"movies"}'%(method,urllib.parse.quote(genre))


    def createStudioPlaylist(self, studio, method='random'):
        return 'videodb://movies/titles/?xsp={"order":{"direction":"ascending","ignorefolders":0,"method":"%s"},"rules":{"and":[{"field":"studio","operator":"is","value":["%s"]}]},"type":"movies"}'%(method,urllib.parse.quote(studio))


    def createGenreMixedPlaylist(self, genre):
        return [self.createTVGenrePlaylist(genre),self.createMovieGenrePlaylist(genre)]