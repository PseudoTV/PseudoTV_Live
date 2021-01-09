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
from resources.lib.fileaccess  import FileLock

REG_KEY = 'PseudoTV_Recommended.%s'

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
        with fileLocker(FileLock()):
            fle  = FileAccess.open(file, 'r')
            data = (loadJSON(fle.read()) or {})
            fle.close()
            return data
        
        
    def save(self):
        with fileLocker(FileLock()):
            fle = FileAccess.open(LIBRARYFLE, 'w')
            self.log('save, saving to %s'%(LIBRARYFLE))
            fle.write(dumpJSON(self.libraryItems, idnt=4, sortkey=False))
            fle.close()
        return self.reset() #force memory/file parity 

        
    def setPredefinedSelection(self, type, items):
        self.log('setPredefinedSelection, type = %s, items = %s'%(type,items))
        return setSetting('Select_%s'%(type.replace(' ','_')),'(%s) Selected'%(len(list(filter(lambda x: x != '',items)))))
       
       
    def getLibraryItems(self, type, enabled=False):
        self.log('getLibraryItems, type = %s, enabled = %s'%(type,enabled))
        items = self.libraryItems.get('library',{}).get(type,[])
        if enabled: 
            items = list(filter(lambda k:k.get('enabled',False) == True, items))
            self.setPredefinedSelection(type,items)#set 'Select_' setting count
        return sorted(items, key=lambda k: k['name'])
        

    def setLibraryItems(self, type, items):
        self.log('setLibraryItems, type = %s, items = %s'%(type,len(items)))
        self.libraryItems['library'][type] = sorted(items, key=lambda k:k['name'])
        self.setPredefinedSelection(type,self.getLibraryItems(type,enabled=True))
        return True


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
        
            
    def setEnableState(self, type, selects):
        items = self.getLibraryItems(type)
        self.log('setEnableState, type = %s, items = %s, selects = %s'%(type, len(items), selects))
        for idx, item in enumerate(items):
            if idx in selects: 
                item['enabled'] = True
            else:
                item['enabled'] = False
        if self.setLibraryItems(type,items):
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
        setSetting('Clear_BlackList','|'.join(self.recommended.getBlackList()))
        return hasContent
        
 
    def getMixed(self):
        return [LANGUAGE(30078),#"Recently Added"
                LANGUAGE(30141),#"Seasonal"
                LANGUAGE(30079)]#"PVR Recordings"
 
 
    def getRecommended(self):
        recommended = sorted(self.recommended.fillRecommended(),key=lambda x:x['item']['name'])
        return [item['item']['name'] for item in recommended]


    def getfillItems(self):
        log('getfillItems')
        Networks, TVGenres   = self.jsonRPC.getTVInfo()
        Studios, MovieGenres = self.jsonRPC.getMovieInfo()
        MixedGenres = [tv for tv in TVGenres for movie in MovieGenres if tv.lower() == movie.lower()]
        return {LANGUAGE(30002):Networks,
                LANGUAGE(30003):self.jsonRPC.fillTVShows(),
                LANGUAGE(30004):TVGenres,
                LANGUAGE(30005):MovieGenres,
                LANGUAGE(30007):Studios,
                LANGUAGE(30006):MixedGenres,
                LANGUAGE(30080):self.getMixed(),
                LANGUAGE(30097):self.jsonRPC.fillMusicInfo(),
                LANGUAGE(30026):self.getRecommended(),
                LANGUAGE(30033):self.recommended.findImports()}
        
        
    def fillLibraryItems(self):
        #parse library for items, convert to library item, parse for logo and vfs path. save to library.json
        busy = ProgressBGDialog(message='%s...'%(LANGUAGE(30158)))
        fillItems = self.getfillItems()
        for prog, type in enumerate(CHAN_TYPES):
            items     = []
            fillItem  = fillItems.get(type,[])
            progress  = (prog*100//len(CHAN_TYPES))
            busy      = ProgressBGDialog(progress, busy, '%s %s'%(LANGUAGE(30159),type))
            existing  = self.getLibraryItems(type, enabled=True)
            for idx, item in enumerate(fillItem):
                busy = ProgressBGDialog(progress, busy, '%s %s %s'%(LANGUAGE(30159),type,(idx*100//len(fillItem)))+'%')
                if isinstance(item,dict):
                    name = (item.get('name','')  or item.get('label',''))
                    if not name: 
                        log('fillLibraryItems, type = %s no name found item = %s'%(type,item))
                        continue
                else: name = item
                logo = self.jsonRPC.getLogo(name, type)
                enabled = len(list(filter(lambda k:k['name'] == name, existing))) > 0
                if type == LANGUAGE(30033):
                    items.append({'enabled':enabled,'name':name,'type':type,'logo':logo})
                else:
                    items.append({'enabled':enabled,'name':name,'type':type,'logo':logo,'path':self.predefined.pathTypes[type](name)})
            log('fillLibraryItems, type = %s, items = %s'%(type,len(items)))
            self.setLibraryItems(type,items)            
        ProgressBGDialog(100, busy, '%s...'%(LANGUAGE(30158)))
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
        setSetting('Clear_BlackList','|'.join(self.library.libraryItems['recommended']['blacklist']))
        return True
    
    
    def clearBlackList(self):
        self.library.libraryItems['recommended']['blacklist'] = []
        if self.library.save():
            setSetting('Clear_BlackList','|'.join(self.getBlackList()))
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
                return {'id':addonid,'data':loadJSON(data),'item':getPluginMeta(addonid)}
            
            
    def getRecommendedbyType(self, type='iptv'):
        self.log('getRecommendedbyType, type = %s'%(type))
        whiteList = self.getWhiteList()
        recommendedAddons = self.searchRecommendedAddons()
        return [item for item in recommendedAddons for addonid in whiteList if ((item.get('id','') == addonid) and (item['data'].get('type','').lower() == type.lower()))]
        
        
    def fillRecommended(self):
        self.log('fillRecommended')
        whiteList = self.getWhiteList()
        recommendedAddons = self.searchRecommendedAddons()
        return [item for item in recommendedAddons for addonid in whiteList if ((item.get('id','') == addonid) and (item['data'].get('type','').lower() != 'iptv'))]
        
        
    def importPrompt(self):
        self.log('importPrompt')
        ignoreList = self.getWhiteList()
        ignoreList.extend(self.getBlackList())
        recommendedAddons = self.searchRecommendedAddons()
        for addon in recommendedAddons:
            if not addon['id'] in ignoreList:
                if not yesnoDialog('%s'%(LANGUAGE(30147)%(ADDON_NAME,addon['item'].get('name','')))):                   
                    self.addBlackList(addon['id'])
                else:
                    self.addWhiteList(addon['id'])
        return True
          
          
    def resetImports(self):
        self.log('resetImports')
        # self.library.libraryItems['imports'] = []
        # return True


    def findImports(self):
        items = sorted(self.getRecommendedbyType(),key=lambda x:x['item']['name'])
        iptv = [item.get('item',{}).get('name') for item in items]
        self.log('findImports, found = %s'%(len(iptv)))
        return iptv

    # def getRecommended(self):
        # log('Channels: getRecommended')
        # return self.channelList.get('recommended',{})

        
    # def setRecommended(self, recommended):
        # log('Channels: setRecommended, recommended items = %s'%(len(recommended)))
        # self.channelList['recommended'] = recommended
        # return self.save()

    # def findImport(self, eitem, imports=None):
        # if imports is None:
            # imports = self.library.libraryItems['imports']
        # for idx, item in enumerate(imports):
            # if eitem.get('id','') == item.get('id',''): 
                # self.log('findImport, item = %s, found = %s'%(eitem,item))
                # return idx, item
        # return None, {}
        

    # def addImport(self, eitem):
        # self.log('addImport, item = %s'%(eitem))
        # imports = self.library.libraryItems['imports']
        # idx, item = self.findImport(eitem,imports)
        # if idx is None:
            # imports.append(eitem)
        # else:
            # imports[idx].update(eitem)
        # self.library.libraryItems['library']['imports'] = imports
        # return True