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

class Library:
    def __init__(self, writer=None):
        self.log('__init__')
        if writer:
            self.writer = writer
        else:
            from resources.lib.writer import Writer
            self.writer = Writer()
            
        self.channels   = self.writer.channels
        self.vault      = self.writer.vault
        self.cache      = self.writer.cache
        self.dialog     = self.writer.dialog
        self.pool       = self.writer.pool
        self.monitor    = self.writer.monitor
        self.jsonRPC    = self.writer.jsonRPC
        self.filelock   = self.writer.GlobalFileLock
        
        if not self.vault.libraryItems: 
            self.reload()
        else:
            self.withdraw()
            
        self.predefined    = Predefined()
        self.recommended   = Recommended(library=self)
        self.serviceThread = threading.Timer(0.5, self.triggerPendingChange)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def clear(self):
        self.log('clear')
        self.vault.libraryItems = {}
        return self.deposit()
        

    def reload(self):
        self.log('reload')
        self.vault.libraryItems = self.getTemplate()
        self.vault.libraryItems.update(self.load())
        return self.deposit()
        
        
    def deposit(self):
        self.log('deposit')
        self.vault.set_libraryItems(self.vault.libraryItems)
        return True
        
    
    def withdraw(self):
        self.log('withdraw')
        return self.vault.get_libraryItems()
     

    def load(self, file=getUserFilePath(LIBRARYFLE)):
        self.log('load file = %s'%(file))
        with fileLocker(self.filelock):
            if not FileAccess.exists(file): 
                file = LIBRARYFLE_DEFAULT
            fle  = FileAccess.open(file, 'r')
            data = (loadJSON(fle.read()) or {})
            fle.close()
            return data
        
        
    def save(self):
        filePath = getUserFilePath(LIBRARYFLE)
        self.log('save, saving to %s'%(filePath))
        with fileLocker(self.filelock):
            fle = FileAccess.open(filePath, 'w')
            fle.write(dumpJSON(self.vault.libraryItems, idnt=4, sortkey=False))
            fle.close()
            return self.reload()


    @cacheit(checksum=ADDON_VERSION,json_data=True)
    def getTemplate(self):
        self.log('getTemplate')
        return (self.load(LIBRARYFLE_DEFAULT) or {})

        
    def getLibraryItems(self, type, enabled=False):
        self.log('getLibraryItems, type = %s, enabled = %s'%(type,enabled))
        items = self.vault.libraryItems.get('library',{}).get(type,[])
        if enabled: return self.getEnabledItems(items)
        return sorted(items, key=lambda k: k['name'])
        

    def getEnabledItems(self, items):
        self.log('getEnabledItems, items = %s'%(len(items)))
        def chkEnabled(item):
            if item.get('enabled',False): 
                return item
            else:
                return None
        return sorted(self.pool.poolList(chkEnabled,items), key=lambda k: k['name'])
        # return sorted(filter(lambda k:k.get('enabled',False) == True, items), key=lambda k: k.get('name'))


    def setLibraryItems(self, type, items):
        self.log('setLibraryItems, type = %s, items = %s'%(type,len(items)))
        if len(items) > 0: PROPERTIES.setPropertyBool('has.Predefined',True)
        self.vault.libraryItems.get('library',{})[type] = sorted(items, key=lambda k:k['name'])
        SETTINGS.setSetting('Select_%s'%(type.replace(' ','_')),'[COLOR=orange][B]%s[/COLOR][/B]/[COLOR=dimgray]%s[/COLOR]'%(len(self.getEnabledItems(items)),len(items)))
        return self.save()

        
    def clearLibraryItems(self, type=None):
        self.log('clearLibraryItems, type = %s'%(type))
        def setDisabled(item):
            item['enabled'] = False
            return item
            
        if type is None: types = CHAN_TYPES
        else:            types = [type]
        for type in types:
            self.setLibraryItems(type,self.pool.poolList(setDisabled,self.getLibraryItems(type)))
        return True
        
        
    def setEnableStates(self, type, selects, items=None):
        if items is None: items = self.getLibraryItems(type)
        self.log('setEnableStates, type = %s, items = %s, selects = %s'%(type, len(items), selects))
        for idx, item in enumerate(items):
            if idx in selects: 
                item['enabled'] = True
            else: 
                item['enabled'] = False
        return self.setLibraryItems(type,items)
        
   
    def chkLibraryItems(self, type=None):
        hasContent = False
        if not type is None: 
            types = [type]
        else: 
            types = CHAN_TYPES.copy()
        self.log('chkLibraryItems, types = %s'%(types))
        
        for type in types:
            libraryItems = self.getLibraryItems(type) #all items, check if they exist to enable settings option.
            if libraryItems and len(libraryItems) > 0:
                hasContent = True
                PROPERTIES.setProperty('has.%s'%(type.replace(' ','_')),'true')
            else: 
                PROPERTIES.setProperty('has.%s'%(type.replace(' ','_')),'false')
                
        self.recommended.setWhiteList(self.recommended.getWhiteList())
        self.recommended.setBlackList(self.recommended.getBlackList())
        return True
        
 
    @cacheit()
    def getNetworks(self):
        return self.jsonRPC.getTVInfo().get('studios',[])
        
        
    @cacheit()
    def getTVGenres(self):
        return self.jsonRPC.getTVInfo().get('genres',[])
 
 
    @cacheit(expiration=datetime.timedelta(hours=REAL_SETTINGS.getSettingInt('Max_Days')))
    def getTVShows(self):
        return self.jsonRPC.getTVInfo().get('shows',[])
 
 
    @cacheit()
    def getMovieStudios(self):
        return self.jsonRPC.getMovieInfo().get('studios',[])
        
        
    @cacheit()
    def getMovieGenres(self):
        return self.jsonRPC.getMovieInfo().get('genres',[])
              
 
    @cacheit()
    def getMusicGenres(self):
        return self.jsonRPC.getMusicInfo().get('genres',[])
 
         
    def getMixedGenres(self):
        return [tv for tv in self.getTVGenres() for movie in self.getMovieGenres() if tv.lower() == movie.lower()]


    def getMixed(self):
        return [LANGUAGE(30078),#"Recently Added"
                LANGUAGE(30141),#"Seasonal"
                LANGUAGE(30079)]#"PVR Recordings"


    def fillTypeItems(self, type):
        funcs = {LANGUAGE(30002):self.getNetworks,
                 LANGUAGE(30003):self.getTVShows,
                 LANGUAGE(30004):self.getTVGenres,
                 LANGUAGE(30005):self.getMovieGenres,
                 LANGUAGE(30007):self.getMovieStudios,
                 LANGUAGE(30006):self.getMixedGenres,
                 LANGUAGE(30080):self.getMixed,
                 LANGUAGE(30097):self.getMusicGenres,
                 LANGUAGE(30026):self.recommended.fillRecommended,
                 LANGUAGE(30033):self.recommended.fillImports}
        return funcs[type]()


    def fillLibraryItems(self, logoLookup=False):
        ## parse kodi for items, convert to library item, parse for changed logo and vfs path. save to library.json
        def fillType(type, busy):
            if not self.monitor.waitForAbort(0.01): 
                items     = self.fillTypeItems(type)
                existing  = self.getLibraryItems(type)
                cacheName = 'fillType.%s.%s'%(type,len(items))
                results   = self.cache.get(cacheName, checksum=len(items), json_data=True)
                if not results or not existing:
                    results  = []
                    if type == LANGUAGE(30003): #meta doesn't need active refresh, except for tv shows which may change more often than genres.
                        life = datetime.timedelta(hours=REAL_SETTINGS.getSettingInt('Max_Days'))
                    else:
                        life = datetime.timedelta(days=REAL_SETTINGS.getSettingInt('Max_Days'))
                        
                    enabled  = self.getEnabledItems(existing)
                    self.log('fillType, type = %s, items = %s, existing = %s, enabled = %s'%(type, len(items),len(existing),len(enabled)))
                    
                    # if not items and enabled:
                        # self.log('fillType, something went wrong no items; substitute existing.')
                        # items = enabled.copy()
                
                    for idx, item in enumerate(items):
                        if self.monitor.waitForAbort(0.01):
                            return
                            
                        fill = int((idx*100)//len(items))
                        prog = int((CHAN_TYPES.index(type)*100)//len(CHAN_TYPES))
                        busy = self.dialog.progressBGDialog(prog, busy, message='%s: %s'%(type,fill)+'%',header='%s, %s'%(ADDON_NAME,LANGUAGE(30159)))

                        if isinstance(item,dict):
                            name = (item.get('name','') or item.get('label',''))
                            if not name: continue
                            if type in [LANGUAGE(30026),LANGUAGE(30033)]: 
                                logo = item.get('icon','')
                            else: 
                                logo = self.jsonRPC.getLogo(name, type, item.get('file',None), item)
                        else: 
                            name = item
                            logo = self.jsonRPC.getLogo(name, type)

                        tmpItem = {'enabled':len(list(filter(lambda k:k['name'] == name, enabled))) > 0,
                                   'name':name,
                                   'type':type,
                                   'logo':logo}
                                   
                        if    type == LANGUAGE(30026): tmpItem['path'] = item['path'] #Recommended
                        elif  type == LANGUAGE(30033): tmpItem['item'] = item
                        else: tmpItem['path'] = self.predefined.pathTypes[type](name) #Predefined
                        results.append(tmpItem)
                        
                    if results: #only cache found items.
                        self.setLibraryItems(type,results)
                        self.cache.set(cacheName, results, checksum=len(items), expiration=life, json_data=True)

        busy = self.dialog.progressBGDialog(header='%s, %s'%(ADDON_NAME,LANGUAGE(30159)))
        for type in CHAN_TYPES: fillType(type,busy)
        busy = self.dialog.progressBGDialog(100, busy, message=LANGUAGE(30053))
        return True
        

    def buildLibraryListitem(self, data):
        if isinstance(data,tuple): data = list(data)
        return self.dialog.buildMenuListItem(data[0]['name'],data[1],iconImage=data[0]['logo'])


    def selectPredefined(self, type=None, autoTune=None):
        self.log('selectPredefined, type = %s, autoTune = %s'%(type,autoTune))
        if isClient(): return
        escape = autoTune is not None
        with busy_dialog(escape):
            items = self.getLibraryItems(type)
            if not items:
                self.dialog.notificationDialog(LANGUAGE(30103)%(type))
                setBusy(False)
                return
            listItems = self.pool.poolList(self.buildLibraryListitem,items,type)
            
        if autoTune:
            if autoTune > len(items): autoTune = len(items)
            select = random.sample(list(set(range(0,len(items)))),autoTune)
        else:
            select = self.dialog.selectDialog(listItems,LANGUAGE(30272)%(type),preselect=list(self.matchLizIDX(listItems,self.getEnabledItems(items))))

        if not select is None:
            with busy_dialog(escape):
                self.setEnableStates(type,list(self.matchDictIDX(items,[listItems[idx] for idx in select])),items)
                self.writer.convertLibraryItems(type)
                self.setPendingChangeTimer()


    def matchLizIDX(self, listitems, selects, key='name', retval=False):
        for select in selects:
            for idx, listitem in enumerate(listitems):
                if select.get(key) == listitem.getLabel():
                    if retval: yield listitem
                    else:      yield idx


    def matchDictIDX(self, items, listitems, key='name', retval=False):
        for listitem in listitems:
            for idx, item in enumerate(items):
                if listitem.getLabel() == item.get(key):
                    if retval: yield item
                    else:      yield idx


    def setPendingChangeTimer(self, wait=30.0):
        self.log('setPendingChangeTimer, wait = %s'%(wait))
        if self.serviceThread.is_alive(): 
            try: 
                self.serviceThread.cancel()
                self.serviceThread.join()
            except: pass
        self.serviceThread = threading.Timer(wait, self.triggerPendingChange)
        self.serviceThread.name = "serviceThread"
        self.serviceThread.start()
        
        
    def triggerPendingChange(self):
        self.log('triggerPendingChange')
        if isBusy(): self.setPendingChangeTimer()
        else:        setPendingChange()
        
        
class Recommended:
    def __init__(self, library):
        self.log('__init__')
        self.library  = library
        self.cache    = library.cache
        self.dialog   = library.dialog
        self.pool     = library.pool
        self.jsonRPC  = library.jsonRPC


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def getRecommendedItems(self):
        return self.library.vault.libraryItems.get('recommended',{})


    def getWhiteList(self):
        #whitelist - prompt shown, added to import list and/or manager dropdown.
        return list(set(self.getRecommendedItems().get('whitelist',[])))
        
        
    def getBlackList(self):
        #blacklist - plugin ignored for the life of the list.
        return list(set(self.getRecommendedItems().get('blacklist',[])))
    
    
    def addWhiteList(self, addonid):
        self.log('addWhiteList, addonid = %s'%(addonid))
        whiteList = self.getWhiteList()
        whiteList.append(addonid)
        self.library.vault.libraryItems.get('recommended',{})['whitelist'] = list(set(whiteList))
        if len(whiteList) > 0: 
            PROPERTIES.setPropertyBool('has.WhiteList',len(whiteList) > 0)
        return True
        
        
    def setWhiteList(self, whiteList):
        if len(whiteList) > 0: 
            PROPERTIES.setPropertyBool('has.WhiteList',len(whiteList) > 0)
        return whiteList
        

    def addBlackList(self, addonid):
        self.log('addBlackList, addonid = %s'%(addonid))
        blackList = self.getBlackList()
        blackList.append(addonid)
        self.library.vault.libraryItems.get('recommended',{})['blacklist'] = list(set(blackList))
        self.setBlackList(self.library.vault.libraryItems.get('recommended',{})['blacklist'])
        return True
    
    
    def setBlackList(self, blackList):
        if len(blackList) > 0: 
            PROPERTIES.setPropertyBool('has.BlackList',len(blackList) > 0)
            SETTINGS.setSetting('Clear_BlackList','|'.join(blackList))
        return blackList
        
    
    def clearBlackList(self):
        self.library.vault.libraryItems.get('recommended',{})['blacklist'] = []
        if self.library.save(): self.setBlackList(self.getBlackList())
        return True
        
      
    def searchRecommendedAddons(self):
        if not SETTINGS.getSettingBool('Enable_Recommended'): return []
        blackList = self.getBlackList()
        addonList = list(filter(lambda k:k.get('addonid','') not in blackList, self.jsonRPC.getAddons()))
        return self.pool.poolList(self.searchRecommendedAddon, addonList)
        
        
    @cacheit(expiration=datetime.timedelta(minutes=30),json_data=True)
    def searchRecommendedAddon(self, addon):
        addonid   = addon.get('addonid','')
        cacheName = 'searchRecommendedAddon.%s'%(addonid)
        addonData = PROPERTIES.getEXTProperty(REG_KEY%(addonid))
        if addonData:
            self.log('searchRecommendedAddon, found addonid = %s, payload = %s'%(addonid,addonData))
            return {addonid:{"id":addonid,"data":loadJSON(addonData),"meta":getPluginMeta(addonid)}}
        return None
        

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
                if not self.dialog.yesnoDialog('%s'%(LANGUAGE(30147)%(ADDON_NAME,item[addon]['meta'].get('name',''))), autoclose=15000):  
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
            retval = self.dialog.yesnoDialog('%s'%(LANGUAGE(30147)%(ADDON_NAME,', '.join(addons))), customlabel=LANGUAGE(30214), autoclose=15000)
            self.log('importMulti, retval = %s'%(retval))
            if   retval == 1: return self.importSingles(recommendedAddons)
            elif retval == 2: 
                for item in recommendedAddons:
                    addon = list(item.keys())[0]
                    self.log('importMulti, adding %s'%(addon))
                    self.addWhiteList(addon)
                return True
            else:
                return False


    def importPrompt(self):
        recommendedAddons = self.searchRecommendedAddons()
        if len(recommendedAddons) > 1: 
            changed = self.importMulti(recommendedAddons)
        else: 
            changed = self.importSingles(recommendedAddons)
        if changed: self.library.save()
        return changed