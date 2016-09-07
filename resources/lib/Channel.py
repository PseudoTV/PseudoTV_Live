#   Copyright (C) 2015 Jason Anderson, Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

from Playlist import Playlist
from Globals import *
from Rules import *


class Channel:
    def __init__(self):
        self.Playlist = Playlist()
        self.name = ''
        self.playlistPosition = 0
        self.showTimeOffset = 0
        self.lastAccessTime = 0
        self.totalTimePlayed = 0
        self.fileName = ''
        self.isPaused = False
        self.isValid = False
        self.isRandom = False
        self.isReverse = False
        self.mode = 0
        self.ruleList = []
        self.channelNumber = 0
        self.isSetup = False
        self.hasChanged = False


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('Channel: ' + msg, level)


    def setPlaylist(self, filename):
        return self.Playlist.load(filename)


    def loadRules(self, channel):
        del self.ruleList[:]
        listrules = RulesList()
        self.channelNumber = channel
        
        try:
            rulecount = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rulecount'))

            for i in range(rulecount):
                ruleid = int(ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_id'))

                for rule in listrules.ruleList:
                    if rule.getId() == ruleid:
                        self.ruleList.append(rule.copy())

                        for x in range(rule.getOptionCount()):
                            self.ruleList[-1].optionValues[x] = ADDON_SETTINGS.getSetting('Channel_' + str(channel) + '_rule_' + str(i + 1) + '_opt_' + str(x + 1))

                        self.log("Added rule - " + self.ruleList[-1].getTitle())
                        break
        except Exception,e:
            self.ruleList = []


    def setPaused(self, paused):
        self.isPaused = paused


    def setShowTime(self, thetime):
        self.showTimeOffset = thetime // 1


    def setShowPosition(self, show):
        show = int(show)
        self.playlistPosition = self.fixPlaylistIndex(show)


    def setAccessTime(self, thetime):
        self.lastAccessTime = thetime // 1

        
    def getNextDuration(self):
        return self.getItemDuration(self.playlistPosition + 1)
        

    def getCurrentDuration(self):
        return self.getItemDuration(self.playlistPosition)


    def getItemDuration(self, index):
        return self.Playlist.getduration(self.fixPlaylistIndex(index))


    def getTotalDuration(self):
        return self.Playlist.totalDuration

        
    def getNextLiveID(self):
        return self.getItemLiveID(self.playlistPosition + 1)
        

    def getCurrentLiveID(self):
        return self.getItemLiveID(self.playlistPosition)


    def getItemLiveID(self, index):
        return self.Playlist.getLiveID(self.fixPlaylistIndex(index))

        
    def getNexttimestamp(self):
        return self.getItemtimestamp(self.playlistPosition + 1)
        
        
    def getCurrenttimestamp(self):
        return self.getItemtimestamp(self.playlistPosition)


    def getItemtimestamp(self, index):
        return self.Playlist.gettimestamp(self.fixPlaylistIndex(index))

        
    def getNextgenre(self):
        return self.getItemgenre(self.playlistPosition + 1)
        
        
    def getCurrentgenre(self):
        return self.getItemgenre(self.playlistPosition)


    def getItemgenre(self, index):
        return self.Playlist.getgenre(self.fixPlaylistIndex(index))


    def getNextDescription(self):
        return self.getItemDescription(self.playlistPosition + 1)
        
        
    def getCurrentDescription(self):
        return self.getItemDescription(self.playlistPosition)


    def getItemDescription(self, index):
        return self.Playlist.getdescription(self.fixPlaylistIndex(index))


    def getNextEpisodeTitle(self):
        return self.getItemEpisodeTitle(self.playlistPosition + 1)
        
        
    def getCurrentEpisodeTitle(self):
        return self.getItemEpisodeTitle(self.playlistPosition)


    def getItemEpisodeTitle(self, index):
        return self.Playlist.getepisodetitle(self.fixPlaylistIndex(index))


    def getNexttTitle(self):
        return self.getItemTitle(self.playlistPosition + 1)
        
        
    def getCurrentTitle(self):
        return self.getItemTitle(self.playlistPosition)


    def getItemTitle(self, index):
        return self.Playlist.getTitle(self.fixPlaylistIndex(index))


    def getNextFilename(self):
        return self.getItemFilename(self.playlistPosition + 1)
        
        
    def getCurrentFilename(self):
        return self.getItemFilename(self.playlistPosition)


    def getItemFilename(self, index):
        return self.Playlist.getfilename(self.fixPlaylistIndex(index))


    def fixPlaylistIndex(self, index):
        if self.Playlist.size() == 0:
            return index

        while index >= self.Playlist.size():
            index -= self.Playlist.size()

        while index < 0:
            index += self.Playlist.size()
        return index


    def addShowPosition(self, addition):
        self.setShowPosition(self.playlistPosition + addition)