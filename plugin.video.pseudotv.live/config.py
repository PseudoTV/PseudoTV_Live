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
from resources.lib.library     import Library

class Config:
    def __init__(self, sysARG=sys.argv, cache=None, service=None):
        self.log('__init__, sysARG = ' + str(sysARG))
        self.sysARG    = sysARG
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache

        if service is None:
            from resources.lib.jsonrpc import JSONRPC
            from resources.lib.parser  import Writer
            self.jsonRPC     = JSONRPC(self.cache)
            self.writer      = Writer(self.cache)
        else:
            self.jsonRPC     = service.jsonRPC
            self.writer      = service.writer
        
        self.library         = Library(self.cache, self.jsonRPC)
        self.recommended     = self.library.recommended
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)

            
    def getLibraryItems(self, type, enabled=False):
        if self.library.reset():
            return self.library.getLibraryItems(type, enabled)
            
            
    def autoTune(self):
        if not yesnoDialog(LANGUAGE(30132)%(ADDON_NAME)): 
            setProperty('autotuned','true')
            return False
        busy  = ProgressBGDialog(message='%s...'%(LANGUAGE(30102)))
        types = list(filter(lambda k:k != LANGUAGE(30033), CHAN_TYPES)) #exclude Imports from autotuning.
        for idx, type in enumerate(types):
            self.log('autoTune, type = %s'%(type))
            busy = ProgressBGDialog((idx*100//len(types)), busy, '%s %s'%(LANGUAGE(30102),type))
            self.selectPredefined(type,autoTune=AUTOTUNE_ITEMS)
        ProgressBGDialog(100, busy, '%s...'%(LANGUAGE(30102)))
        setProperty('autotuned','true')
        return True
 
 
    def selectPredefined(self, type=None, autoTune=None):
        self.log('selectPredefined, type = %s, autoTune = %s'%(type,autoTune))
        escape = autoTune is not None
        with busy_dialog(escape):
            items = self.getLibraryItems(type)
            if not items: 
                if autoTune is None:
                    clearLibraryItems(type)
                    notificationDialog(LANGUAGE(30103)%(type))
                return False
                
            pitems = self.getLibraryItems(type,enabled=True) # existing predefined
            listItems = (PoolHelper().poolList(self.library.buildLibraryListitem,items,type))
        if autoTune is None:
            select = selectDialog(listItems,'Select %s'%(type),preselect=findItemsIn(listItems,pitems,val_key='name'))
        else:
            if autoTune > len(items): autoTune = len(items)
            select = random.sample(list(set(range(0,len(items)))),autoTune)
        if select:
            with busy_dialog(escape):
                selects = findItemsIn(items,[listItems[idx].getLabel() for idx in select],item_key='name')
                self.library.setEnableState(type,selects)
                self.buildPredefinedChannels(type)
        return True


    def repairLibraryItems(self):
        if self.library.fillLibraryItems():
            self.library.chkLibraryItems()
            return self.buildPredefinedChannels()
        return False
        

    def buildPredefinedChannels(self, type=None):#convert enabled library items into channels.
        libraryItems = {}
        if type is None: types = CHAN_TYPES
        else: types = [type]
        for type in types:
            if type == LANGUAGE(30033): self.buildImports()            
            else: libraryItems[type] = self.getLibraryItems(type, enabled=True)
        return self.writer.buildPredefinedChannels(libraryItems)
        
        
    def buildImports(self):#convert enabled imports to channel items.
        return self.writer.buildImports(self.recommended.getRecommendedbyType(type='iptv'), self.getLibraryItems(LANGUAGE(30033), enabled=True))
        
        
    def clearPredefined(self):
        self.log('clearPredefined')
        if isBusy(): return notificationDialog(LANGUAGE(30029))
        with busy_dialog():
            if not yesnoDialog('%s?'%(LANGUAGE(30077))): return
            setBusy(True)
            if self.library.clearLibraryItems():
                self.buildPredefinedChannels()
                setProperty('pendingChange','true')
                setProperty('autotuned','false')
                setBusy(False)
                return notificationDialog(LANGUAGE(30053))
        return False
        

    def clearUserChannels(self):
        self.log('clearUserChannels')
        if isBusy(): return notificationDialog(LANGUAGE(30029))
        with busy():
            if not yesnoDialog('%s?'%(LANGUAGE(30093))): return
            if self.writer.clearChannels():
                setProperty('pendingChange','true')
                setProperty('autotuned','false')
                return notificationDialog(LANGUAGE(30053))


    def clearBlackList(self):
        self.log('clearBlackList') 
        if not yesnoDialog('%s?'%(LANGUAGE(30154))): return
        return self.recommended.clearBlackList()
        

    def userGroups(self):
        self.log('userGroups')
        retval = inputDialog(LANGUAGE(30076), default=getSetting('User_Groups'))
        if not retval: return
        setSetting('User_Groups',retval)
        notificationDialog(LANGUAGE(30053))


    def clearImport(self):
        self.log('clearImport') 
        with busy_dialog():
            setSetting('Import_M3U','')
            setSetting('Import_XMLTV','')
            setSetting('User_Import','false')
        return notificationDialog(LANGUAGE(30053))
        

    def openEditor(self, file='temp.xsp', media='video'):
        self.log('openEditor, file = %s, media = %s'%(file,media)) 
        return xbmc.executebuiltin("ActivateWindow(smartplaylisteditor,video)")
        # path='special://profile/playlists/%s/%s'%(media,file)
        # return xbmc.executebuiltin("ActivateWindow(10136,%s,%s)"%(path,media))


    def openPlugin(self,addonID):
        self.log('openPlugin, addonID = %s'%(addonID)) 
        return xbmc.executebuiltin('RunAddon(%s, newsmartplaylist://video/)'%addonID)


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
            self.clearPredefined()
        elif  param == 'Clear_Userdefined':
            self.clearUserChannels()
        elif  param == 'Clear_BlackList':
            self.clearBlackList()
        elif  param == 'User_Groups':
            self.userGroups()
        elif  param == 'Open_Editor':
            return self.openEditor()
        elif  param.startswith('Open_Settings'): 
            return self.openSettings(param.split('|')[1])
        elif  param.startswith('Open_Plugin'):   
            return self.openPlugin(param.split('|')[1])
        else: 
            with busy():
                self.selectPredefined(param.replace('_',' '))
        return REAL_SETTINGS.openSettings()
            
if __name__ == '__main__': Config(sys.argv).run()