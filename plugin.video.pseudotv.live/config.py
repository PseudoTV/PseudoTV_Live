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
from resources.lib.parser      import Channels, M3U
from resources.lib.jsonrpc     import JSONRPC
from resources.lib.predefined  import Predefined 

class Config:
    def __init__(self, sysARG=sys.argv, cache=None):
        self.log('__init__, sysARG = ' + str(sysARG))
        self.sysARG    = sysARG
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.jsonRPC       = JSONRPC(self.cache)
        self.channels      = Channels(self.cache)
        self.m3u           = M3U(self.cache)
        self.predefined    = Predefined(self.cache)
        self.recommended   = self.channels.recommended
        
        self.TV_Shows      = []
        self.TV_Info       = [[],[]]
        self.MOVIE_Info    = [[],[]]
        self.MUSIC_Info    = []
        self.IPTV_Items    = []
        self.Recommended_Items = []
        
        self.InitThread      = threading.Timer(0.5, self.runInit)
        self.serviceThread   = threading.Timer(0.5, self.runThread)
        
        
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
        if chkVersion():
            showChangelog()
            


    def startServiceThread(self, wait=5.0):
        self.log('startServiceThread, wait = %s'%(wait))
        if self.serviceThread.isAlive(): 
            self.serviceThread.cancel()
        self.serviceThread = threading.Timer(wait, self.runThread)
        self.serviceThread.name = "serviceThread"
        self.serviceThread.start()
        
                
    def runThread(self):
        if isBusy(): return self.startServiceThread(900) # 15mins
        self.log('runThread, started')
        self.chkPredefinedSelection() # fill selection text.
        self.chkRecommendedAddons()   # scan addons for recommended payload
        DBItems = self.getItems()     # spool cache
        [self.jsonRPC.getLogo(channel,key) for key, value in DBItems.items() for channel in value] # cache logos
        self.log('runThread, finished')
        return self.startServiceThread(3600) # 1hr
                   
        
    def chkRecommendedAddons(self):
        if self.channels.isClient: return
        self.log('chkRecommendedAddons')
        if self.recommended.importPrompt():
            self.rebuildRecommended()
        
              
    def rebuildRecommended(self):
        self.log('rebuildRecommended')
        self.recommended.reset()
            
            
    def getRecommended(self):
        self.log('getRecommended')
        if len(self.Recommended_Items) == 0: 
            self.Recommended_Items = self.recommended.fillRecommended()
        self.Recommended_Items.sort(key=lambda x:x['item']['name'])
        recommended = [recommended['item']['name'] for recommended in self.Recommended_Items]
        self.log('getRecommended, found = %s'%(len(recommended)))
        return recommended
        
         
    def getIPTV(self):
        self.log('getIPTV')
        if len(self.IPTV_Items) == 0: 
            self.IPTV_Items = self.recommended.getDataType()
        self.IPTV_Items.sort(key=lambda x:x['item']['name'])
        iptv = [item['item']['name'] for item in self.IPTV_Items]
        self.log('getIPTV, found = %s'%(len(iptv)))
        return iptv
        
        
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
        items = {'TV Shows'         :self.getTVShows(),
                 'TV Networks'      :self.getTVInfo()[0],
                 'TV Genres'        :self.getTVInfo()[1],
                 'Movie Genres'     :self.getMovieInfo()[1],
                 'Movie Studios'    :self.getMovieInfo()[0],
                 'Mixed Genres'     :self.makeMixedList(self.getTVInfo()[1], self.getMovieInfo()[1]),
                 'Mixed'            :self.getMixedMisc(),
                 'Music Genres'     :self.getMusicGenres(),
                 'Recommended'      :self.getRecommended(),
                 'IPTV'             :self.getIPTV()}
        if param is not None: return items[param]
        return items
        
        
    def autoTune(self):
        self.log('autoTune')
        if not yesnoDialog(LANGUAGE(30132)%(ADDON_NAME)): return False
        busy = ProgressBGDialog(message='%s...'%(LANGUAGE(30102)))
        types = CHAN_TYPES.copy()
        types.pop(types.index('IPTV'))
        for idx, type in enumerate(types): 
            busy = ProgressBGDialog((idx*100//len(CHAN_TYPES)), busy, '%s: %s'%(LANGUAGE(30102),type))
            self.selectPredefined(type,autoTune=3)
        ProgressBGDialog(100, busy, '%s...'%(LANGUAGE(30102)))
        return True
 
 
    def selectPredefined(self, param=None, autoTune=None):
        self.log('selectPredefined, param = %s, autoTune = %s'%(param,autoTune))
        setBusy(True)
        escape = autoTune is not None
        with busy_dialog(escape):
            type  = param.replace('_',' ')
            items = self.getItems(type)
            if not items: 
                setBusy(False)
                if autoTune is None:
                    self.setPredefinedSelection([],type)
                    notificationDialog(LANGUAGE(30103)%(type))
                return
                
            pitems    = list(self.predefined.getChannelbyKey(type,'name')) # existing predefined
            listItems = list(PoolHelper().poolList(self.buildPoolListitem,items,type))
        if autoTune is None:
            select = selectDialog(listItems,'Select %s'%(type),preselect=findItemsIn(listItems,pitems))
        else:
            if autoTune > len(items): autoTune = len(items)
            select = random.sample(list(set(range(0,len(items)))),autoTune)
        if select is not None:
            self.predefined.setChannels([listItems[idx].getLabel() for idx in select], type)
            self.setPredefinedSelection(select,type)
        setBusy(False)


    def setPredefinedSelection(self, items, type):
        # set predefined selections.
        self.log('setPredefinedSelection, type = %s, items = %s'%(type,items))
        return setSetting('Select_%s'%(type.replace(' ','_')),'(%s) Selected'%(len(list(filter(lambda x: x != '',items)))))
        
            
    def chkPredefinedSelection(self):
        self.log('chkPredefinedSelection')
        [self.setPredefinedSelection(list(self.predefined.getChannelbyKey(type,'name')),type) for type in CHAN_TYPES]
        
            
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
            setSetting('Import_M3U',' ')
            setSetting('Import_XMLTV',' ')
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


    def buildPoolListitem(self, data):
        item, type = data
        return buildMenuListItem(item,type,iconImage=self.jsonRPC.getLogo(item,type))

    
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
        else: self.selectPredefined(param)
        return REAL_SETTINGS.openSettings()
            
if __name__ == '__main__': Config(sys.argv).run()