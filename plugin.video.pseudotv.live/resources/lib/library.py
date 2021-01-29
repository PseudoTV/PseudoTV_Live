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
from resources.lib.predefined  import Predefined 

REG_KEY = 'PseudoTV_Recommended.%s'
GLOBAL_FILELOCK = FileLock()

class Library:
    def __init__(self, cache=None, jsonRPC=None):
        log('Library: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
        
        if jsonRPC is None:
            from resources.lib.jsonrpc import JSONRPC
            self.jsonRPC  = JSONRPC(self.cache)
        else:
            self.jsonRPC  = jsonRPC
        self.myMonitor    = self.jsonRPC.myMonitor
        
        self.predefined   = Predefined(self.cache)
        self.recommended  = Recommended(self.cache, self)
        
        self.libraryItems = self.getTemplate(ADDON_VERSION)
        self.libraryItems.update(self.load())
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def reset(self):
        self.log('reset')
        self.__init__()
        return True


    @use_cache(7)
    def getTemplate(self, version=ADDON_VERSION):
        log('getTemplate')
        return (self.load(LIBRARYFLE_DEFAULT) or {})


    def load(self, file=LIBRARYFLE):
        self.log('load file = %s'%(file))
        if not FileAccess.exists(file): 
            file = LIBRARYFLE_DEFAULT
        with fileLocker(GLOBAL_FILELOCK):
            fle  = FileAccess.open(file, 'r')
            data = (loadJSON(fle.read()) or {})
            fle.close()
            return data
        
        
    def save(self):
        with fileLocker(GLOBAL_FILELOCK):
            fle = FileAccess.open(LIBRARYFLE, 'w')
            self.log('save, saving to %s'%(LIBRARYFLE))
            fle.write(dumpJSON(self.libraryItems, idnt=4, sortkey=False))
            fle.close()
        return self.reset() #force memory/file parity 

        
    def setPredefinedSelection(self, type, items):
        self.log('setPredefinedSelection, type = %s, items = %s'%(type,len(items)))
        if len(items) > 0: setPropertyBool('has.Predefined',True)
        return setSetting('Select_%s'%(type.replace(' ','_')),'(%s) Selected'%(len(list(filter(lambda x: x != '',items)))))
       
       
    def getLibraryItems(self, type, enabled=False):
        self.log('getLibraryItems, type = %s, enabled = %s'%(type,enabled))
        items = self.libraryItems.get('library',{}).get(type,[])
        if enabled: items = list(filter(lambda k:k.get('enabled',False) == True, items))
        return sorted(items, key=lambda k: k['name'])
        

    def setLibraryItems(self, type, items):
        self.log('setLibraryItems, type = %s, items = %s'%(type,len(items)))
        self.libraryItems['library'][type] = sorted(items, key=lambda k:k['name'])
        return self.setPredefinedSelection(type,self.getLibraryItems(type,enabled=True))#set 'Select_' setting count


    def clearLibraryItems(self, type=None):
        log('clearLibraryItems, type = %s'%(type))
        if type is None:
            types = CHAN_TYPES
        else: 
            types = [type]
        for type in types: 
            libraryItems = self.getLibraryItems(type) 
            for item in libraryItems: 
                item['enabled'] = False
            self.setLibraryItems(type,libraryItems)
        return self.save()
        
            
    def setEnableStates(self, type, selects):
        items = self.getLibraryItems(type)
        self.log('setEnableStates, type = %s, items = %s, selects = %s'%(type, len(items), selects))
        for idx, item in enumerate(items):
            if idx in selects: 
                item['enabled'] = True
            else: 
                item['enabled'] = False
            self.setLibraryItems(type,items)
        return self.save()
        

    def chkLibraryItems(self, type=None):
        log('chkLibraryItems, type = %s'%(type))
        hasContent = False
        if type is None: types = CHAN_TYPES.copy()
        else: types = [type]
        for type in types:
            libraryItems = self.getLibraryItems(type) #all items, check if they exist to enable settings option.
            if libraryItems and len(libraryItems) > 0:
                hasContent = True
                setProperty('has.%s'%(type.replace(' ','_')),'true')
            else: 
                setProperty('has.%s'%(type.replace(' ','_')),'false')
        blackList = self.recommended.getBlackList()
        if len(blackList) > 0: setPropertyBool('has.BlackList',len(blackList) > 0)
        setSetting('Clear_BlackList','|'.join(blackList))
        # return hasContent
        return True
        
 
    def getNetworks(self):
        return self.jsonRPC.getTVInfo()[0]
        
        
    def getTVGenres(self):
        return self.jsonRPC.getTVInfo()[1]
 
 
    def getMovieStudios(self):
        return self.jsonRPC.getMovieInfo()[0]
        
        
    def getMovieGenres(self):
        return self.jsonRPC.getMovieInfo()[1]
        
        
    def getMixedGenres(self):
        TVGenres    = self.getTVGenres()
        MovieGenres = self.getMovieGenres()
        return [tv for tv in TVGenres for movie in MovieGenres if tv.lower() == movie.lower()]
        
        
    def getMixed(self):
        return [LANGUAGE(30078),#"Recently Added"
                LANGUAGE(30141),#"Seasonal"
                LANGUAGE(30079)]#"PVR Recordings"
 
 
    def getfillItems(self):
        log('getfillItems')
        busy = ProgressBGDialog(message='%s'%(LANGUAGE(30158)))
        funcs = {LANGUAGE(30002):self.getNetworks,
                 LANGUAGE(30003):self.jsonRPC.fillTVShows,
                 LANGUAGE(30004):self.getTVGenres,
                 LANGUAGE(30005):self.getMovieGenres,
                 LANGUAGE(30007):self.getMovieStudios,
                 LANGUAGE(30006):self.getMixedGenres,
                 LANGUAGE(30080):self.getMixed,
                 LANGUAGE(30097):self.jsonRPC.fillMusicInfo,
                 LANGUAGE(30026):self.recommended.fillRecommended,
                 LANGUAGE(30033):self.recommended.fillImports}
        for idx, type in enumerate(CHAN_TYPES):
            busy = ProgressBGDialog(((idx+1)*100//len(CHAN_TYPES)), busy, '%s'%(LANGUAGE(30158)))
            yield type,funcs[type]()
        
        
    def fillLibraryItems(self):
        #parse library for items, convert to library item, parse for logo and vfs path. save to library.json
        fillItems = dict(self.getfillItems())
        busy = ProgressBGDialog(message='%s...'%(LANGUAGE(30159)))
        for prog, type in enumerate(CHAN_TYPES):
            if self.myMonitor.waitForAbort(0.01): break
            items     = []
            fillItem  = fillItems.get(type,[])
            progress  = (prog*100//len(CHAN_TYPES))
            busy = ProgressBGDialog(progress, busy, '%s %s'%(LANGUAGE(30159),type))
            existing  = self.getLibraryItems(type, enabled=True)
            for idx, item in enumerate(fillItem):
                if self.myMonitor.waitForAbort(0.01): break
                busy = ProgressBGDialog(progress, busy, '%s %s %s'%(LANGUAGE(30159),type,(idx*100//len(fillItem)))+'%')
                if isinstance(item,dict):
                    name = (item.get('name','') or item.get('label',''))
                    if not name: 
                        log('fillLibraryItems, type = %s no name found item = %s'%(type,item))
                        continue
                else: name = item
                logo = self.jsonRPC.getLogo(name, type)
                if isinstance(item,dict): logo = (item.get('icon','') or logo)
                enabled = len(list(filter(lambda k:k['name'] == name, existing))) > 0
                tmpItem = {'enabled':enabled,'name':name,'type':type,'logo':logo}
                if   type == LANGUAGE(30033): pass                           #Imports / "Recommended Services"
                elif type == LANGUAGE(30026): tmpItem['path'] = item['path'] #Recommended
                else: tmpItem['path'] = self.predefined.pathTypes[type](name)#Predefined
                items.append(tmpItem)
                log('fillLibraryItems, type = %s, tmpItem = %s'%(type,tmpItem))
            log('fillLibraryItems, type = %s, items = %s'%(type,len(items)))
            self.setLibraryItems(type,items)         
        busy = ProgressBGDialog(100, busy, '%s...'%(LANGUAGE(30158)))   
        return self.save()
        
        
    def buildLibraryListitem(self, data):
        return buildMenuListItem(data[0]['name'],data[1],iconImage=data[0]['logo'])


class Recommended:
    def __init__(self, cache=None, library=None):
        self.log('__init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache

        if library is None: return
        self.library  = library
        self.jsonRPC  = self.library.jsonRPC
    
        self.recommendEnabled  = getSettingBool('Enable_Recommended')


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def getRecommendedItems(self):
        return self.library.libraryItems.get('recommended',{})


    def getWhiteList(self):
        #whitelist - prompt shown, added to import list and/or manager dropdown.
        return list(set(self.getRecommendedItems().get('whitelist',[])))
        
        
    def getBlackList(self):
        #blacklist - plugin ignored for the life of the list.
        return list(set(self.getRecommendedItems().get('blacklist',[])))
    
    
    def addWhiteList(self, addonid):
        self.log('addWhiteList, addonid = %s'%(addonid))
        whitelist = self.getWhiteList()
        whitelist.append(addonid)
        self.library.libraryItems['recommended']['whitelist'] = list(set(whitelist))
        return True
        

    def addBlackList(self, addonid):
        self.log('addBlackList, addonid = %s'%(addonid))
        blacklist = self.getBlackList()
        blacklist.append(addonid)
        self.library.libraryItems['recommended']['blacklist'] = list(set(blacklist))
        blackList = self.library.libraryItems['recommended']['blacklist']
        if len(blackList) > 0: setPropertyBool('has.BlackList',len(blackList) > 0)
        setSetting('Clear_BlackList','|'.join(blackList))
        return True
    
    
    def clearBlackList(self):
        self.library.libraryItems['recommended']['blacklist'] = []
        if self.library.save():
            blackList = self.getBlackList()
            setPropertyBool('has.BlackList',len(blackList) > 0)
            setSetting('Clear_BlackList','|'.join(blackList))
            return True
        return False
        
      
    def searchRecommendedAddons(self):
        self.log('searchRecommendedAddons')
        return (PoolHelper().poolList(self.searchRecommendedAddon, self.jsonRPC.getAddons()))
        
        
    def searchRecommendedAddon(self, addon):
        addonid   = addon.get('addonid','')
        blackList = self.getBlackList()
        if not addonid in blackList:
            data = xbmcgui.Window(10000).getProperty(REG_KEY%(addonid))
            if data:
                self.log('searchRecommendedAddon, found addonid = %s, payload = %s'%(addonid,data))
                return {addonid:{'id':addonid,'data':loadJSON(data),'meta':getPluginMeta(addonid)}}
            

    def findbyType(self, type='iptv'):
        self.log('findbyType, type = %s'%(type))
        whiteList = self.getWhiteList()
        recommendedAddons = self.searchRecommendedAddons()
        return sorted([item[addonid]['data'][type] for addonid in whiteList for item in recommendedAddons if item.get(addonid,{}).get('data',{}).get(type,[])],key=lambda x:x['name'])


    def fillImports(self):
        items = self.findbyType(type='iptv')
        self.log('fillImports, found = %s'%(len(items)))
        return items


    def fillRecommended(self):
        whiteList = self.getWhiteList()
        recommendedAddons = self.searchRecommendedAddons()
        items = sorted((item.get(addonid) for item in recommendedAddons for addonid in whiteList if item.get(addonid,{})),key=lambda x:x['id'])
        items = [item['data'][key] for item in items for key in item['data'].keys() if key != 'iptv']
        try:
            items = sorted(items[0],key=lambda x:x.get('name'))
            items = sorted(items,key=lambda x:x['id'])
        except: pass #empty list, lazy exception
        self.log('findRecommended, found = %s'%(len(items)))
        return items


    def importPrompt(self):
        self.log('importPrompt')
        ignoreList = self.getWhiteList()
        ignoreList.extend(self.getBlackList())
        recommendedAddons = self.searchRecommendedAddons()
        for item in recommendedAddons:
            addon = list(item.keys())[0]
            if not addon in ignoreList:
                if not yesnoDialog('%s'%(LANGUAGE(30147)%(ADDON_NAME,item[addon]['meta'].get('name','')))):                   
                    self.addBlackList(addon)
                else: 
                    self.addWhiteList(addon)
        return True