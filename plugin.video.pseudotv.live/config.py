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
from resources.lib.globals import *
from resources.lib.parser  import JSONRPC, Channels

class Config:
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = ' + str(sysARG))
        self.sysARG        = sysARG
        self.jsonRPC       = JSONRPC()
        self.channels      = Channels()
        self.TV_Shows      = []
        self.TV_Info       = [[],[]]
        self.MOVIE_Info    = [[],[]]
        self.MUSIC_Info    = []
        self.spoolThread   = threading.Timer(0.5, self.spoolItems)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def startSpooler(self, wait=5.0):
        self.log('startSpooler, wait = %s'%(wait))
        if self.spoolThread.isAlive(): self.spoolThread.cancel()
        self.spoolThread = threading.Timer(wait, self.spoolItems)
        self.spoolThread.name = "spoolThread"
        self.spoolThread.start()
        
                
    def spoolItems(self):
        if isBusy(): 
            return self.startSpooler(900) # 15mins
        self.log('spoolItems, started')
        setBusy(True)
        self.checkConfigSelection() # check channel config, fill labels in settings.xml
        DBItems = self.getItems() # spool cache
        [self.jsonRPC.getLogo(channel,key.replace('_',' ')) for key, value in DBItems.items() for channel in value] # cache logos
        setBusy(False)
        self.log('spoolItems, finished')
        return self.startSpooler(3600)   # 1hr
           
                   
    def getTVShows(self):
        if len(self.TV_Shows) == 0: self.TV_Shows = self.jsonRPC.fillTVShows()
        self.TV_Shows.sort(key=lambda x:x['label'])
        shows = [show['label'] for show in self.TV_Shows]
        self.log('getTVShows, found = %s'%(len(shows)))
        return shows
 
 
    def getTVInfo(self):
        if (len(self.TV_Info[0]) == 0 or len(self.TV_Info[1]) == 0): self.TV_Info = self.jsonRPC.getTVInfo()
        self.log('getTVInfo, networks = %s, genres = %s'%(len(self.TV_Info[0]),len(self.TV_Info[1])))
        return self.TV_Info
 
 
    def getMovieInfo(self):
        if (len(self.MOVIE_Info[0]) == 0 or len(self.MOVIE_Info[1]) == 0): self.MOVIE_Info = self.jsonRPC.getMovieInfo()
        self.log('getMovieInfo, studios = %s, genres = %s'%(len(self.MOVIE_Info[0]),len(self.MOVIE_Info[1])))
        return self.MOVIE_Info
 
 
    def getMixedMisc(self):
        return [LANGUAGE(30078),LANGUAGE(30079)]
 
 
    def getMusicGenres(self):
        if len(self.MUSIC_Info) == 0: self.MUSIC_Info = self.jsonRPC.fillMusicInfo()
        self.log('getMusicGenres, genres = %s'%(len(self.MUSIC_Info)))
        return self.MUSIC_Info
        
 
    def makeMixedList(self, list1, list2):
        newlist = []
        for item in list1:
            curitem = item.lower()
            for a in list2:
                if curitem == a.lower():
                    newlist.append(item)
                    break
        self.log('makeMixedList, genres = %s'%(','.join(newlist)))
        return newlist
        
           
    def getItems(self, param=None):
        items = {'TV_Shows'     :self.getTVShows(),
                 'TV_Networks'  :self.getTVInfo()[0],
                 'TV_Genres'    :self.getTVInfo()[1],
                 'MOVIE_Genres' :self.getMovieInfo()[1],
                 'MIXED_Genres' :self.makeMixedList(self.getTVInfo()[1], self.getMovieInfo()[1]),
                 'MOVIE_Studios':self.getMovieInfo()[0],
                 'MIXED_Other'  :self.getMixedMisc(),
                 'MUSIC_Genres' :self.getMusicGenres()}
        if param is not None: return items[param]
        return items
        
        
    def buildPredefined(self, param=None):
        self.log('buildPredefined, param = %s'%(param)) 
        setBusy(True)
        with busy_dialog():
            type      = param.replace('_',' ')
            items     = self.getItems(param)
            pitems    = getSetting('Setting_%s'%(param)).split('|')
            listItems = list(PoolHelper().poolList(self.buildPoolListitem,items,type))
        select = selectDialog(listItems,'Select %s'%(type),preselect=findItemsIn(listItems,pitems))
        if select is not None:
            sitems = [listItems[idx].getLabel() for idx in select]
            self.buildConfigSelection(sitems,param)
        setBusy(False)
        

    def buildPoolListitem(self, data):
        return buildMenuListItem(data[0],data[1],iconImage=self.jsonRPC.getLogo(data[0],data[1]))
    
    
    def checkConfigSelection(self):
        self.log('checkConfigSelection') 
        [self.buildConfigSelection(getSetting('Setting_%s'%(param)).split('|'),param) for param in CHAN_TYPES]
    
    
    def buildConfigSelection(self, items, type):
        lens = len(list(filter(lambda x: x != '',items)))
        self.log('buildConfigSelection, type = %s, items = %s'%(type,items))
        setSetting('Select_%s'%(type),'(%s) Selected'%(lens))
        setSetting('Setting_%s'%(type),'|'.join(items))
        
        
    def ClearConfigSelection(self):
        self.log('ClearConfigSelection') 
        if not yesnoDialog('%s?'%(LANGUAGE(30077))): return
        [self.buildConfigSelection([], type) for type in CHAN_TYPES]
        return notificationDialog(LANGUAGE(30053))


    def clearUserChannels(self):
        self.log('clearUserChannels') 
        if not yesnoDialog('%s?'%(LANGUAGE(30093))): return
        return self.channels.delete()


    def userGroups(self):
        self.log('userGroups')
        retval = inputDialog(LANGUAGE(30076), default=getSetting('User_Groups'))
        if not retval: return
        setSetting('User_Groups',retval)
        notificationDialog(LANGUAGE(30053))


    def clearImport(self):
        self.log('clearImport') 
        setSetting('Import_M3U',' ')
        setSetting('Import_XMLTV',' ')
        setSetting('User_Import','false')
        return
        

    def openEditor(self, file='temp.xsp', media='video'):
        self.log('openEditor, file = %s, media = %s'%(file,media)) 
        return xbmc.executebuiltin("ActivateWindow(smartplaylisteditor,video)")
        # path='special://profile/playlists/%s/%s'%(media,file)
        # return xbmc.executebuiltin("ActivateWindow(10136,%s,%s)"%(path,media))


    def openPlugin(self,addonID):
        self.log('openPlugin, addonID = %s'%(addonID)) 
        return xbmc.executebuiltin('RunAddon(%s)'%addonID)


    def openSettings(self,addonID):
        self.log('openSettings, addonID = %s'%(addonID)) 
        return xbmcaddon.Addon(id=addonID).openSettings()


    def selectResource(self, type):
        self.log('selectResource, type = %s'%(type)) 
        notificationDialog('Coming Soon')
        return REAL_SETTINGS.openSettings()


    def run(self): 
        param = self.sysARG[1]
        self.log('run, param = %s'%(param))
        if isBusy():
            notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            return REAL_SETTINGS.openSettings()
            
        if    param == None:                     
            return REAL_SETTINGS.openSettings()
        elif  param.startswith('Select_Resource'):
            return self.selectResource(param.split('_')[2])
        elif  param == 'Clear_Import':           
            self.clearImport()
        elif  param == 'Clear_Predefined':       
            self.ClearConfigSelection()
        elif  param == 'Clear_Userdefined':      
            self.clearUserChannels()
        elif  param == 'User_Groups':
            self.userGroups()
        elif  param == 'Open_Editor':            
            return self.openEditor()
        elif  param.startswith('Open_Settings'): 
            return self.openSettings(param.split('|')[1])
        elif  param.startswith('Open_Plugin'):   
            return self.openPlugin(param.split('|')[1])
        else: self.buildPredefined(param)
        return REAL_SETTINGS.openSettings()
            
if __name__ == '__main__': Config(sys.argv).run()