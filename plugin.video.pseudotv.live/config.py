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
from resources.lib.globals     import *
from resources.lib.parser      import JSONRPC, Channels, M3U
from resources.lib.predefined  import Predefined 
from resources.lib.recommended import Recommended 

class Config:
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = ' + str(sysARG))
        self.sysARG        = sysARG
        self.jsonRPC       = JSONRPC()
        self.channels      = Channels()
        self.m3u           = M3U()
        self.predefined    = Predefined()
        self.recommended    = Recommended()
        self.TV_Shows      = []
        self.TV_Info       = [[],[]]
        self.MOVIE_Info    = [[],[]]
        self.MUSIC_Info    = []
        self.InitThread    = threading.Timer(0.5, self.runInit)
        self.spoolThread   = threading.Timer(0.5, self.spoolItems)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)

    
    def runInitThread(self): 
        #startup thread, don't let processes (ie prompts) hold up channel building.
        self.log('runInitThread')
        if self.InitThread.isAlive(): 
            self.InitThread.cancel()
        self.InitThread = threading.Timer(5.0, self.runInit)
        self.InitThread.name = "InitThread"
        self.InitThread.start()


    def runInit(self):
        self.log('runInit')
        chkPVR()
        chkVersion()


    def startSpooler(self, wait=5.0):
        self.log('startSpooler, wait = %s'%(wait))
        if self.spoolThread.isAlive(): 
            self.spoolThread.cancel()
        self.spoolThread = threading.Timer(wait, self.spoolItems)
        self.spoolThread.name = "spoolThread"
        self.spoolThread.start()
        
                
    def spoolItems(self):
        if isBusy(): return self.startSpooler(900) # 15mins
        self.log('spoolItems, started')
        self.chkPredefinedSelection() # check channel config, fill labels in settings.xml
        self.rebuildRecommended() # rebuild recommended list
        DBItems = self.getItems() # spool cache
        [self.jsonRPC.getLogo(channel,key.replace('_',' ')) for key, value in DBItems.items() for channel in value] # cache logos
        self.log('spoolItems, finished')
        return self.startSpooler(3600) # 1hr
           
              
    def rebuildRecommended(self):
        self.recommended.reset()
            
            
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
        
        
    def getRecommended(self):
        return []
        
 
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
                 'MUSIC_Genres' :self.getMusicGenres(),
                 'RECOMMENDED_Other':self.getRecommended()}
        if param is not None: return items[param]
        return items
        
        
    def autoTune(self):
        self.log('autoTune')
        if not yesnoDialog(LANGUAGE(30132)%(ADDON_NAME)): return False
        busy = ProgressBGDialog(message='%s...'%(LANGUAGE(30102)))
        for idx, type in enumerate(CHAN_TYPES): 
            busy = ProgressBGDialog((idx*100//len(CHAN_TYPES)), busy, '%s: %s'%(LANGUAGE(30102),type.replace('_',' ')))
            self.buildPredefined(type,autoTune=3)
        ProgressBGDialog(100, busy, '%s...'%(LANGUAGE(30102)))
        return self.predefined.buildPredefinedChannels()
        
        
    def buildPredefined(self, param=None, autoTune=None):
        self.log('buildPredefined, param = %s, autoTune = %s'%(param,autoTune))
        setBusy(True)
        escape = autoTune is not None
        with busy_dialog(escape):
            type      = param.replace('_',' ')
            items     = self.getItems(param)
            if not items: 
                setBusy(False)
                if autoTune is None: 
                    notificationDialog(LANGUAGE(30103)%(type))
                return
                
            pitems    = getSetting('Setting_%s'%(param)).split('|')
            listItems = list(PoolHelper().poolList(self.buildPoolListitem,items,type))
        if autoTune is None:
            select = selectDialog(listItems,'Select %s'%(type),preselect=findItemsIn(listItems,pitems))
        else:
            if autoTune > len(items): autoTune = len(items)
            select = random.sample(list(set(range(0,len(items)))),autoTune)
        if select is not None:
            sitems = [listItems[idx].getLabel() for idx in select]
            self.setPredefinedSelection(sitems,param)
        setBusy(False)
        

    def buildPoolListitem(self, data):
        return buildMenuListItem(data[0],data[1],iconImage=self.jsonRPC.getLogo(data[0],data[1]))
    
    
    def chkPredefinedSelection(self):
        self.log('chkPredefinedSelection')
        if self.channels.isClient:
            [self.setPredefinedSelection(param,type) for type, param in self.getPredefinedSelection().items()]
        else:
            [self.setPredefinedSelection(getSetting('Setting_%s'%(param)).split('|'),param) for param in CHAN_TYPES]
    
    
    def getPredefinedSelection(self):
        self.log('getPredefinedSelection')
        items    = {}
        channels = self.channels.getPredefined()
        for type in CHAN_TYPES:  items[type] = []
        for channel in channels: items[channel['type'].replace(' ','_')].append(channel['name'])
        return items


    def checkPredefinedChannels(self):
        self.log('checkPredefinedChannels') 
        chitems = {}
        chitems[type] =[sorted(getSetting('Setting_%s'%(type)).split('|')) for type in CHAN_TYPES]
        return chitems
    
    
    def setPredefinedSelection(self, items, type):
        # set predefined selections.
        lens = len(list(filter(lambda x: x != '',items)))
        self.log('setPredefinedSelection, type = %s, items = %s'%(type,items))
        setSetting('Select_%s'%(type),'(%s) Selected'%(lens))
        setSetting('Setting_%s'%(type),'|'.join(items))
        return
        
        
    def clearPredefinedSelection(self):
        self.log('clearPredefinedSelection')
        # clear predefined selections for all types.
        if not yesnoDialog('%s?'%(LANGUAGE(30077))): return
        [self.setPredefinedSelection([], type) for type in CHAN_TYPES]
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
        with busy_dialog():
            [(setSetting('Import_M3U%s'%(n+1),' '),setSetting('Import_XMLTV%s'%(n+1),' ')) for n in range(MAX_IMPORT)]
            setSetting('User_Import','false')
        return notificationDialog(LANGUAGE(30053))
        

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
            
        if param == None:                     
            return REAL_SETTINGS.openSettings()
        elif  param.startswith('Select_Resource'):
            return self.selectResource(param.split('_')[2])
        elif  param == 'Clear_Import':           
            self.clearImport()
        elif  param == 'Clear_Predefined':       
            self.clearPredefinedSelection()
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