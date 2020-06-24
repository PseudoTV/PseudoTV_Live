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

# -*- coding: utf-8 -*-
from globals import *
from parsers import JSONRPC

class Config:
    def __init__(self, sysARG):
        log('__init__, sysARG = ' + str(sysARG))
        self.sysARG        = sysARG
        self.jsonRPC       = JSONRPC()
        self.TV_Shows      = []
        self.TV_Info       = [[],[]]
        self.MOVIE_Info    = [[],[]]
        self.spoolThread   = threading.Timer(0.5, self.spoolItems)
        

    def startSpooler(self, wait=5.0):
        log('Config: startSpooler')
        if self.spoolThread.isAlive(): self.spoolThread.cancel()
        self.spoolThread = threading.Timer(wait, self.spoolItems)
        self.spoolThread.name = "spoolThread"
        self.spoolThread.start()
        
                
    def spoolItems(self):
        if isBusy(): return self.startSpooler(1800)
        log('Config: spoolItems started')
        setBusy(True)
        self.checkConfigSelection() # check channel config, fill labels in settings.xml
        DBItems = self.getItems() # spool cache
        [self.jsonRPC.getLogo(channel,key.replace('_',' ')) for key, value in DBItems.items() for channel in value] # cache logos
        setBusy(False)
        log('Config: spoolItems finished')
        return self.startSpooler(3600)# 1hr timer?
           
           
    def getTVShows(self):
        if len(self.TV_Shows) == 0: self.TV_Shows = self.jsonRPC.fillTVShows()
        self.TV_Shows.sort(key=lambda x:x['label'])
        shows = [show['label'] for show in self.TV_Shows]
        log('Config: getTVShows, found = %s'%(len(shows)))
        return shows
 
 
    def getTVInfo(self):
        if (len(self.TV_Info[0]) == 0 or len(self.TV_Info[1]) == 0): self.TV_Info = self.jsonRPC.getTVInfo()
        log('Config: getTVInfo, networks = %s, genres = %s'%(len(self.TV_Info[0]),len(self.TV_Info[1])))
        return self.TV_Info
 
 
    def getMovieInfo(self):
        if (len(self.MOVIE_Info[0]) == 0 or len(self.MOVIE_Info[1]) == 0): self.MOVIE_Info = self.jsonRPC.getMovieInfo()
        log('Config: getMovieInfo, studios = %s, genres = %s'%(len(self.MOVIE_Info[0]),len(self.MOVIE_Info[1])))
        return self.MOVIE_Info
 
 
    def makeMixedList(self, list1, list2):
        newlist = []
        for item in list1:
            curitem = item.lower()
            for a in list2:
                if curitem == a.lower():
                    newlist.append(item)
                    break
        log('Config: makeMixedList, genres = %s'%(len(newlist)))
        return newlist
        
           
    def getItems(self, param=None):
        items = {'TV_Shows'     :self.getTVShows(),
                 'TV_Networks'  :self.getTVInfo()[0],
                 'TV_Genres'    :self.getTVInfo()[1],
                 'MOVIE_Genres' :self.getMovieInfo()[1],
                 'MIXED_Genres' :self.makeMixedList(self.getTVInfo()[1], self.getMovieInfo()[1]),
                 'MOVIE_Studios':self.getMovieInfo()[0]}
        if param is not None: return items[param]
        return items
        
        
    def buildPoolListitem(self, data):
        return buildMenuListItem(data[0],data[1],iconImage=self.jsonRPC.getLogo(data[0],data[1]))
    
    
    def checkConfigSelection(self):
        log('Config: checkConfigSelection') 
        [self.buildConfigSelection(getSetting('Setting_%s'%(param)).split('|'),param) for param in CHAN_TYPES]
    
    
    def buildConfigSelection(self, items, type):
        lens = len(list(filter(lambda x: x != '',items)))
        log('Config: buildConfigSelection, type = %s, items = %s'%(type,items))
        REAL_SETTINGS.setSetting('Select_%s'%(type),'(%s) Selected'%(lens))
        REAL_SETTINGS.setSetting('Setting_%s'%(type),'|'.join(items))
        return True
        
        
    def ClearConfigSelection(self):
        [self.buildConfigSelection(type,[]) for type in CHAN_TYPES]
        return True


    def clearImport(self):
        REAL_SETTINGS.setSetting('User_Import','false')
        REAL_SETTINGS.setSetting('Import_M3U',' ')
        REAL_SETTINGS.setSetting('Import_XMLTV',' ')
        return


    def openSettings(self,addonID):
        return xbmcaddon.Addon(id=addonID).openSettings()


    def run(self): 
        param = self.sysARG[1]
        log('Config: run, param = %s'%(param))
        if isBusy():
            notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            return REAL_SETTINGS.openSettings()
        if param == None: return REAL_SETTINGS.openSettings()
        if param == 'Clear_Import': self.clearImport()
        if param.startswith('Open_Settings'): self.openSettings(param.split('|')[1])
        else:
            setBusy(True)
            with busy_dialog():
                type      = param.replace('_',' ')
                items     = self.getItems(param)
                pitems    = getSetting('Setting_%s'%(param)).split('|')
                listItems = list(PoolHelper().poolList(self.buildPoolListitem,items,type))
            select = selectDialog(listItems,'Select %s'%(type),preselect=findItemsinListItem(listItems,pitems))
            if select is not None: 
                sitems = [listItems[idx].getLabel() for idx in select]
                self.buildConfigSelection(sitems,param)
            setBusy(False)
        REAL_SETTINGS.openSettings()
            
if __name__ == '__main__': Config(sys.argv).run()