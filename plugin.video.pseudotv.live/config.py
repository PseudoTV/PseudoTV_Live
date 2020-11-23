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
from resources.lib.recommended import Recommended

class Config:
    def __init__(self, sysARG=sys.argv, cache=None):
        self.log('__init__, sysARG = ' + str(sysARG))
        self.sysARG    = sysARG
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.jsonRPC         = JSONRPC(self.cache)
        self.channels        = Channels(self.cache)
        self.m3u             = M3U(self.cache)
        self.recommended     = Recommended(self.cache, self)
        self.predefined      = Predefined(self.cache, self)
        
        self.autoTune_busy   = False
        self.InitThread      = threading.Timer(0.5, self.startInitThread)
        self.serviceThread   = threading.Timer(0.5, self.runServiceThread)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)

    
    def startInitThread(self): 
        self.log('startInitThread')
        if self.InitThread.isAlive(): 
            self.InitThread.cancel()
        self.InitThread = threading.Timer(5.0, self.runInitThread)
        self.InitThread.name = "InitThread"
        self.InitThread.start()


    def runInitThread(self):
        self.log('runInitThread')
        if not FileAccess.exists(LOGO_LOC):
            FileAccess.makedirs(LOGO_LOC)
        if not FileAccess.exists(CACHE_LOC):
            FileAccess.makedirs(CACHE_LOC)
        if not FileAccess.exists(PLS_LOC):
            FileAccess.makedirs(PLS_LOC)
            
        for func in [chkPVR,
                     chkVersion]: func()            
            
            
    def startServiceThread(self, wait=5.0):
        self.log('startServiceThread, wait = %s'%(wait))
        if self.serviceThread.isAlive(): 
            self.serviceThread.cancel()
        self.serviceThread = threading.Timer(wait, self.runServiceThread)
        self.serviceThread.name = "serviceThread"
        self.serviceThread.start()
        
                
    def runServiceThread(self):
        if isBusy(): return self.startServiceThread(15.0)
        self.log('runServiceThread, started')
        setBusy(True)
        for func in [self.chkRecommendedAddons,
                     self.chkPredefinedSelection,
                     self.predefined.buildPredefinedItems]: func()
        setBusy(False)
        self.log('runServiceThread, finished')
        return self.startServiceThread(3600.0)
                   
        
    def chkRecommendedAddons(self):
        if self.channels.isClient: return
        self.log('chkRecommendedAddons')
        if self.recommended.importPrompt():
            self.rebuildRecommended()
        
              
    def rebuildRecommended(self):
        self.log('rebuildRecommended')
        self.recommended.reset()

            
    def autoTune(self):
        if self.autoTune_busy: return
        self.autoTune_busy = True
        if not yesnoDialog(LANGUAGE(30132)%(ADDON_NAME)): 
            self.autoTune_busy = False
            return False
        busy = ProgressBGDialog(message='%s...'%(LANGUAGE(30102)))
        types = CHAN_TYPES.copy()
        types.pop(types.index(LANGUAGE(30033))) #remove "imports" from autotune list
        for idx, type in enumerate(types):
            self.log('autoTune, type = %s'%(type))
            busy = ProgressBGDialog((idx*100//len(CHAN_TYPES)), busy, '%s: %s'%(LANGUAGE(30102),type))
            self.selectPredefined(type,autoTune=3)
            xbmc.sleep(1000)
        ProgressBGDialog(100, busy, '%s...'%(LANGUAGE(30102)))
        self.autoTune_busy = False
        return True
 
 
    def selectPredefined(self, type=None, autoTune=None):
        self.log('selectPredefined, type = %s, autoTune = %s'%(type,autoTune))
        setBusy(True)
        escape = autoTune is not None
        with busy_dialog(escape):
            items = self.predefined.getPredefinedItems(type,enabled=False)
            if not items: 
                setBusy(False)
                if autoTune is None:
                    self.setPredefinedSelection([],type)
                    notificationDialog(LANGUAGE(30103)%(type))
                return
                
            pitems = self.predefined.getPredefinedItems(type,enabled=True) # existing predefined
            listItems = (PoolHelper().poolList(self.buildPoolListitem,items,type))
        if autoTune is None:
            select = selectDialog(listItems,'Select %s'%(type),preselect=findItemsIn(listItems,pitems,val_key='name'))
        else:
            if autoTune > len(items): autoTune = len(items)
            select = random.sample(list(set(range(0,len(items)))),autoTune)
        if select:
            selects = findItemsIn(items,[listItems[idx].getLabel() for idx in select],item_key='name')
            self.predefined.savePredefinedItems(list(self.predefined.enableChannels(type, items, selects)),type)
            self.setPredefinedSelection(select,type)
            if type == LANGUAGE(30033):
                self.predefined.buildImports()
            else:
                self.predefined.buildPredefinedChannels()
        setBusy(False)


    def setPredefinedSelection(self, items, type):
        self.log('setPredefinedSelection, type = %s, items = %s'%(type,items))
        return setSetting('Select_%s'%(type.replace(' ','_')),'(%s) Selected'%(len(list(filter(lambda x: x != '',items)))))
        
            
    def chkPredefinedSelection(self):
        for type in CHAN_TYPES:
            self.log('chkPredefinedSelection, type = %s'%(type))
            if len(self.predefined.getPredefinedItems(type, enabled=False)) > 0: setProperty('has.%s'%(type.replace(' ','_')),'true')
            self.setPredefinedSelection(self.predefined.getPredefinedItems(type, enabled=True),type)
        self.predefined.buildPredefinedChannels()
        self.predefined.buildImports()
        
            
    def clearPredefinedSelection(self):
        self.log('clearPredefinedSelection')
        # clear predefined selections for all types.
        if not yesnoDialog('%s?'%(LANGUAGE(30077))): return
        setBusy(True)
        [self.predefined.savePredefinedItems(list(self.predefined.enableChannels(type, self.predefined.getPredefinedItems(type, enabled=False), [])),type) for type in CHAN_TYPES]
        [self.setPredefinedSelection([], type) for type in CHAN_TYPES]
        setBusy(False)
        return notificationDialog(LANGUAGE(30053))


    def clearUserChannels(self):
        self.log('clearUserChannels') 
        if not yesnoDialog('%s?'%(LANGUAGE(30093))): return
        return self.channels.delete()


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
        return buildMenuListItem(item['name'],type,iconImage=item['logo'])

    
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
        else: self.selectPredefined(param.replace('_',' '))
        return REAL_SETTINGS.openSettings()
            
if __name__ == '__main__': Config(sys.argv).run()