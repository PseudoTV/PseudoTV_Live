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
            
        self.predefined  = Predefined()
        self.recommended = Recommended(library=self)
        
        
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
        log('getTemplate')
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


    def setLibraryItems(self, type, items, setSetting=False):
        self.log('setLibraryItems, type = %s, items = %s'%(type,len(items)))
        if len(items) > 0: PROPERTIES.setPropertyBool('has.Predefined',True)
        self.vault.libraryItems.get('library',{})[type] = sorted(items, key=lambda k:k['name'])
        if setSetting: self.setSettings(type,items)
        return self.save()
        
        
    def setSettings(self, type, items):
        self.log('setSettings, type = %s, items = %s'%(type,len(items)))
        SETTINGS.setSetting('Select_Channels','[B]%s[/B] Channels'%(len(self.channels.getChannels())))
        SETTINGS.setSetting('Select_%s'%(type.replace(' ','_')),'[COLOR=orange][B]%s[/COLOR][/B]/[COLOR=dimgray]%s[/COLOR]'%(len(self.getEnabledItems(items)),len(items)))
        
        
    def clearLibraryItems(self, type=None):
        log('clearLibraryItems, type = %s'%(type))
        def setDisabled(item):
            item['enabled'] = False
            return item
            
        if type is None: types = CHAN_TYPES
        else:            types = [type]
        for type in types: 
            libraryItems = self.pool.poolList(setDisabled,self.getLibraryItems(type))
        return self.setLibraryItems(type,libraryItems,setSettings=True)
        
        
        
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
        log('chkLibraryItems, types = %s'%(types))
        
        for type in types:
            libraryItems = self.getLibraryItems(type) #all items, check if they exist to enable settings option.
            if libraryItems and len(libraryItems) > 0:
                hasContent = True
                PROPERTIES.setProperty('has.%s'%(type.replace(' ','_')),'true')
            else: 
                PROPERTIES.setProperty('has.%s'%(type.replace(' ','_')),'false')
            
        blackList = self.recommended.getBlackList()
        if len(blackList) > 0: 
            PROPERTIES.setPropertyBool('has.BlackList',len(blackList) > 0)
            SETTINGS.setSetting('Clear_BlackList','|'.join(blackList))
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
        results = {}
        funcs   = {LANGUAGE(30002):self.getNetworks,
                   LANGUAGE(30003):self.getTVShows,
                   LANGUAGE(30004):self.getTVGenres,
                   LANGUAGE(30005):self.getMovieGenres,
                   LANGUAGE(30007):self.getMovieStudios,
                   LANGUAGE(30006):self.getMixedGenres,
                   LANGUAGE(30080):self.getMixed,
                   LANGUAGE(30097):self.jsonRPC.getMusicInfo,
                   LANGUAGE(30026):self.recommended.fillRecommended,
                   LANGUAGE(30033):self.recommended.fillImports}
 
        busy = self.dialog.progressBGDialog()
        for idx, type in enumerate(CHAN_TYPES):
            if self.monitor.waitForAbort(0.01): break
            prog = int((idx*100)//len(CHAN_TYPES))
            if prog >= 100: prog == 99
            busy = self.dialog.progressBGDialog(prog, busy, '%s'%(type),header='%s, %s'%(ADDON_NAME,LANGUAGE(30160)))
            results.setdefault(type,[]).extend(funcs[type]())
        busy = self.dialog.progressBGDialog(100, busy, message=LANGUAGE(30053))
        return results


    def fillLibraryItems(self):
        ## parse kodi for items, convert to library item, parse for changed logo and vfs path. save to library.json
        fillItems = self.getfillItems()
        if not fillItems: return True
            
        busy = self.dialog.progressBGDialog()
        for pos, type in enumerate(CHAN_TYPES):
            results  = []
            fillItem = fillItems.get(type,[])
            existing = self.getLibraryItems(type, enabled=True)
            log('fillLibraryItems, type = %s, fillItem = %s, existing = %s'%(type, len(fillItem),len(existing)))
         
            for idx, item in enumerate(fillItem):
                fill = int((idx*100)//len(fillItem))
                prog = int((pos*100)//len(CHAN_TYPES))
                if prog >= 100: prog == 99
                busy = self.dialog.progressBGDialog(prog, busy, message='%s: %s'%(type,fill)+'%',header='%s, %s'%(ADDON_NAME,LANGUAGE(30159)))
                
                if isinstance(item,dict):
                    name = (item.get('name','') or item.get('label',''))
                    if not name: continue
                    logo = self.jsonRPC.getLogo(name, type, item.get('file',None), item)
                else: 
                    name = item
                    logo = self.jsonRPC.getLogo(name, type)

                enabled = len(list(filter(lambda k:k['name'] == name, existing))) > 0
                tmpItem = {'enabled':enabled,'name':name,'type':type,'logo':logo}
                if   type == LANGUAGE(30033): pass                           #Imports / "Recommended Services"
                elif type == LANGUAGE(30026): tmpItem['path'] = item['path'] #Recommended
                else: tmpItem['path'] = self.predefined.pathTypes[type](name)#Predefined
                results.append(tmpItem)
            self.setLibraryItems(type,results)
        busy = self.dialog.progressBGDialog(100, busy, message=LANGUAGE(30053))
        return True
        

    def buildLibraryListitem(self, data):
        if isinstance(data,tuple): data = list(data)
        return self.dialog.buildMenuListItem(data[0]['name'],data[1],iconImage=data[0]['logo'])


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
        whitelist = self.getWhiteList()
        whitelist.append(addonid)
        self.library.vault.libraryItems.get('recommended',{})['whitelist'] = list(set(whitelist))
        return True
        

    def addBlackList(self, addonid):
        self.log('addBlackList, addonid = %s'%(addonid))
        blacklist = self.getBlackList()
        blacklist.append(addonid)
        self.library.vault.libraryItems.get('recommended',{})['blacklist'] = list(set(blacklist))
        blackList = self.library.vault.libraryItems.get('recommended',{})['blacklist']
        if len(blackList) > 0: 
            PROPERTIES.setPropertyBool('has.BlackList',len(blackList) > 0)
            SETTINGS.setSetting('Clear_BlackList','|'.join(blackList))
        return True
    
    
    def clearBlackList(self):
        self.library.vault.libraryItems.get('recommended',{})['blacklist'] = []
        if self.library.save():
            blackList = self.getBlackList()
            PROPERTIES.setPropertyBool('has.BlackList',len(blackList) > 0)
            SETTINGS.setSetting('Clear_BlackList','|'.join(blackList))
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
            changed = self.importMulti(recommendedAddons)
        else: 
            changed = self.importSingles(recommendedAddons)
        # if changed: self.library.save()
        return True