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
    def __init__(self, jsonRPC=None):
        log('Library: __init__')
        if jsonRPC is None:
            from resources.lib.jsonrpc import JSONRPC
            self.jsonRPC  = JSONRPC(self.cache)
        else:
            self.jsonRPC  = jsonRPC
            
        self.cache        = self.jsonRPC.cache
        self.myMonitor    = self.jsonRPC.myMonitor
        self.predefined   = Predefined()
        self.pool         = PoolHelper()
        self.dialog       = Dialog()
        self.recommended  = Recommended(self)
        
        self.libraryItems = self.getTemplate(ADDON_VERSION)
        self.libraryItems.update(self.load())
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def reset(self):
        self.log('reset')
        self.__init__()
        return True


    @cacheit()
    def getTemplate(self, version=ADDON_VERSION):
        log('getTemplate')
        return (self.load(LIBRARYFLE_DEFAULT) or {})


    def load(self, file=getUserFilePath(LIBRARYFLE)):
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
            filePath = getUserFilePath(LIBRARYFLE)
            fle = FileAccess.open(filePath, 'w')
            self.log('save, saving to %s'%(filePath))
            fle.write(dumpJSON(self.libraryItems, idnt=4, sortkey=False))
            fle.close()
        return self.reset() #force i/o parity 

        
    def setPredefinedSelection(self, type, items, total=0):
        self.log('setPredefinedSelection, type = %s, items = %s'%(type,len(items)))
        ## set 'Select_' setting count
        if len(items) > 0: setPropertyBool('has.Predefined',True)
        setSetting('Select_%s'%(type.replace(' ','_')),'[COLOR=orange][B]%s[/COLOR][/B]/[COLOR=dimgray]%s[/COLOR]'%(len(items),total))
        
       
    def getLibraryItems(self, type, enabled=False):
        self.log('getLibraryItems, type = %s, enabled = %s'%(type,enabled))
        def chkEnabled(item):
            if item.get('enabled',False): return item
            return None
        items = self.libraryItems.get('library',{}).get(type,[])
        if enabled: items = self.pool.genList(chkEnabled,items)
        return sorted(items, key=lambda k: k['name'])
        

    def getEnabledItems(self, items):
        self.log('getEnabledItems, items = %s'%(len(items)))
        def chkEnabled(item):
            if item.get('enabled',False): return item
            return None
        return sorted(self.pool.genList(chkEnabled,items), key=lambda k: k['name'])
            

    def setLibraryItems(self, type, items):
        self.log('setLibraryItems, type = %s, items = %s'%(type,len(items)))
        self.libraryItems['library'][type] = sorted(items, key=lambda k:k['name'])
        enabled = self.getLibraryItems(type,enabled=True)
        self.setPredefinedSelection(type,enabled,len(items))
        return True
        

    def clearLibraryItems(self, type=None):
        log('clearLibraryItems, type = %s'%(type))
        if type is None: types = CHAN_TYPES
        else: types = [type]
        for type in types: 
            libraryItems = self.getLibraryItems(type) 
            for item in libraryItems: 
                item['enabled'] = False
        if self.setLibraryItems(type,libraryItems):
            return self.save()
        return False
        
        
    def setEnableStates(self, type, selects):
        items = self.getLibraryItems(type)
        self.log('setEnableStates, type = %s, items = %s, selects = %s'%(type, len(items), selects))
        for idx, item in enumerate(items):
            if idx in selects: 
                item['enabled'] = True
            else: 
                item['enabled'] = False
        if self.setLibraryItems(type,items):
            return self.save()
        return False
        
   
    def chkLibraryItems(self, type=None):
        hasContent = False
        if type is None: types = CHAN_TYPES.copy()
        else:            types = [type]
        log('chkLibraryItems, types = %s'%(types))
        def setSettingStates(type):
            libraryItems = self.getLibraryItems(type) #all items, check if they exist to enable settings option.
            if libraryItems and len(libraryItems) > 0:
                hasContent = True
                setProperty('has.%s'%(type.replace(' ','_')),'true')
            else: 
                setProperty('has.%s'%(type.replace(' ','_')),'false')

        self.pool.genList(setSettingStates,types)
        blackList = self.recommended.getBlackList()
        if len(blackList) > 0: setPropertyBool('has.BlackList',len(blackList) > 0)
        setSetting('Clear_BlackList','|'.join(blackList))
        return True
        
 
    def getNetworks(self):
        return self.jsonRPC.getTVInfo()[0]
        
        
    def getTVGenres(self):
        return self.jsonRPC.getTVInfo()[1]
 
 
    def getTVShows(self):
        return self.jsonRPC.getTVInfo()[2]
 
 
    def getMovieStudios(self):
        return self.jsonRPC.getMovieInfo()[0]
        
        
    def getMovieGenres(self):
        return self.jsonRPC.getMovieInfo()[1]
        
        
    def getMixedGenres(self):
        return [tv for tv in self.getTVGenres() for movie in self.getMovieGenres() if tv.lower() == movie.lower()]
        
        
    def getMixed(self):
        return [LANGUAGE(30078),#"Recently Added"
                LANGUAGE(30141),#"Seasonal"
                LANGUAGE(30079)]#"PVR Recordings"
 
 
    def getfillItems(self):
        log('getfillItems')
        funcs = {LANGUAGE(30002):self.getNetworks,
                 LANGUAGE(30003):self.getTVShows,
                 LANGUAGE(30004):self.getTVGenres,
                 LANGUAGE(30005):self.getMovieGenres,
                 LANGUAGE(30007):self.getMovieStudios,
                 LANGUAGE(30006):self.getMixedGenres,
                 LANGUAGE(30080):self.getMixed,
                 LANGUAGE(30097):self.jsonRPC.getMusicInfo,
                 LANGUAGE(30026):self.recommended.fillRecommended,
                 LANGUAGE(30033):self.recommended.fillImports}
               
        def parseMeta(data):
            type, busy = data
            if self.myMonitor.waitForAbort(0.001): 
                return None
            prog = int((CHAN_TYPES.index(type)*100)//len(CHAN_TYPES))
            busy = self.dialog.progressBGDialog(prog, busy, '%s'%(type),header='%s, %s'%(ADDON_NAME,LANGUAGE(30160)))
            return type,funcs[type]()
            
        busy    = self.dialog.progressBGDialog()
        results = dict(self.pool.poolList(parseMeta,CHAN_TYPES,busy))
        busy    = self.dialog.progressBGDialog(100, busy, message=LANGUAGE(30053))
        return results
    
    
    def recoverItemsFromChannels(self, channels):
        log('recoverItemsFromChannels') #re-enable library.json items from channels.json
        if not channels: return True
        for type in CHAN_TYPES:
            if self.myMonitor.waitForAbort(0.001): return False
            echannels = list(filter(lambda k:k['type'] == type, channels)) # existing channels.
            if not echannels: continue
            selects = []
            items   = self.getLibraryItems(type)
            for idx, item in enumerate(items):
                if self.myMonitor.waitForAbort(0.001): return False
                for channel in channels:
                    if channel.get('name') == item.get('name'):
                        selects.append(idx)
                        break
            self.setEnableStates(type, selects)
        return True
                
                
    def fillLibraryItems(self):
        #parse kodi for items, convert to library item, parse for changed logo and vfs path. save to library.json
        def setItem(data):
            if self.myMonitor.waitForAbort(0.001): 
                return None
                
            items      = []
            type, busy = data
            fillItem   = fillItems.get(type,[])
            existing   = self.getLibraryItems(type, enabled=True)
            
            for idx, item in enumerate(fillItem):
                if self.myMonitor.waitForAbort(0.001):
                    return None
                    
                fillprog = int((idx*100)//len(fillItem))
                progress = int((CHAN_TYPES.index(type)*100)//len(CHAN_TYPES))
                busy = self.dialog.progressBGDialog(progress, busy, message='%s: %s'%(type,fillprog)+'%',header='%s, %s'%(ADDON_NAME,LANGUAGE(30159)))
                
                if isinstance(item,dict):
                    name = (item.get('name','') or item.get('label',''))
                    if not name: 
                        log('fillLibraryItems, type = %s no name found item = %s'%(type,item))
                        continue
                else: 
                    name = item
                    
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
            return self.setLibraryItems(type,items)
            
        fillItems = self.getfillItems()
        busy = self.dialog.progressBGDialog()
        self.pool.poolList(setItem,CHAN_TYPES,busy)
        busy = self.dialog.progressBGDialog(100, busy, message=LANGUAGE(30053))
        return self.save()
        
        
    def buildLibraryListitem(self, data):
        if isinstance(data,tuple): data = list(data)
        return buildMenuListItem(data[0]['name'],data[1],iconImage=data[0]['logo'])


class Recommended:
    def __init__(self, library=None):
        self.log('__init__')
        if library is None:
            return
            
        self.library  = library
        self.jsonRPC  = self.library.jsonRPC
        self.cache    = self.library.cache
        self.pool     = self.library.pool
        self.dialog   = self.library.dialog
        
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
        blackList = self.getBlackList()
        addonList = list(filter(lambda k:k.get('addonid','') not in blackList, self.jsonRPC.getAddons()))
        return (self.pool.poolList(self.searchRecommendedAddon, addonList))
        
        
    def searchRecommendedAddon(self, addon):
        addonid       = addon.get('addonid','')
        cacheName     = 'searchRecommendedAddon.%s'%(addonid)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            data = getEXTProperty(REG_KEY%(addonid))
            if data:
                self.log('searchRecommendedAddon, found addonid = %s, payload = %s'%(addonid,data))
                cacheResponse = {addonid:{"id":addonid,"data":loadJSON(data),"meta":getPluginMeta(addonid)}}
                self.cache.set(cacheName, cacheResponse, expiration=datetime.timedelta(days=getSettingInt('Max_Days')))
        return cacheResponse


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
        tmpLST = []
        whiteList = self.getWhiteList()
        recommendedAddons = self.searchRecommendedAddons()
        items = sorted((item.get(addonid) for item in recommendedAddons for addonid in whiteList if item.get(addonid,{})),key=lambda x:x['id'])
        [tmpLST.extend(item['data'][key]) for item in items for key in item['data'].keys() if key != 'iptv']
        tmpLST = sorted(tmpLST,key=lambda x:x.get('name'))
        tmpLST = sorted(tmpLST,key=lambda x:x['id'])
        self.log('fillRecommended, found = %s'%(len(tmpLST)))
        return tmpLST


    def importSingles(self, recommendedAddons):
        ignoreList = self.getWhiteList()
        ignoreList.extend(self.getBlackList())
        for item in recommendedAddons:
            addon = list(item.keys())[0]
            self.log('importSingles, adding %s'%(addon))
            if not addon in ignoreList:
                if not self.dialog.yesnoDialog('%s'%(LANGUAGE(30147)%(ADDON_NAME,item[addon]['meta'].get('name','')))):                   
                    self.addBlackList(addon)
                else: 
                    self.addWhiteList(addon)
        return True


    def importMulti(self, recommendedAddons):
        addons     = []
        ignoreList = self.getWhiteList()
        ignoreList.extend(self.getBlackList())
        for item in recommendedAddons: 
            addon = list(item.keys())[0]
            if not addon in ignoreList: 
                addons.append(item[addon]['meta'].get('name',''))
        
        if len(addons) > 0:
            retval = self.dialog.yesnoDialog('%s'%(LANGUAGE(30147)%(ADDON_NAME,', '.join(addons))), customlabel=LANGUAGE(30214))
            self.log('importMulti, retval = %s'%(retval))
            if   retval == 1: self.importSingles(recommendedAddons)
            elif retval == 2: 
                for item in recommendedAddons:
                    addon = list(item.keys())[0]
                    self.log('importMulti, adding %s'%(addon))
                    self.addWhiteList(addon)
        return True
        
        
    def importPrompt(self):
        recommendedAddons = self.searchRecommendedAddons()
        if len(recommendedAddons) > 1: 
            return self.importMulti(recommendedAddons)
        else: 
            return self.importSingles(recommendedAddons)