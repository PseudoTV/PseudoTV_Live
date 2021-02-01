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
from manager                   import Manager

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


    def openChannelManager(self):
        chmanager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", config=self)
        del chmanager
            

    def autoTune(self):
        if not yesnoDialog(LANGUAGE(30132)%(ADDON_NAME)): 
            setPropertyBool('autotuned',True)
            return False
        busy  = ProgressBGDialog(message='%s...'%(LANGUAGE(30102)))
        types = list(filter(lambda k:k != LANGUAGE(30033), CHAN_TYPES)) #exclude Imports from autotuning.
        for idx, type in enumerate(types):
            self.log('autoTune, type = %s'%(type))
            busy = ProgressBGDialog((idx*100//len(types)), busy, '%s %s'%(LANGUAGE(30102),type))
            self.selectPredefined(type,autoTune=AUTOTUNE_ITEMS)
        ProgressBGDialog(100, busy, '%s...'%(LANGUAGE(30102)))
        setPropertyBool('autotuned',True)
        return True
 
 
    def selectPredefined(self, type=None, autoTune=None):
        self.log('selectPredefined, type = %s, autoTune = %s'%(type,autoTune))
        escape = autoTune is not None
        with busy_dialog(escape):
            items = self.library.getLibraryItems(type)
            if not items: 
                if autoTune is None:
                    self.library.clearLibraryItems(type) #clear stale meta type
                    notificationDialog(LANGUAGE(30103)%(type))
                return False
            pitems    = self.library.getLibraryItems(type,enabled=True) # existing predefined
            listItems = (PoolHelper().poolList(self.library.buildLibraryListitem,items,type))
            pselect   = findItemsIn(listItems,pitems,val_key='name')
            
        if autoTune is None:
            select = selectDialog(listItems,'Select %s'%(type),preselect=pselect)
        else:
            if autoTune > len(items): autoTune = len(items)
            select = random.sample(list(set(range(0,len(items)))),autoTune)
        if select:
            with busy_dialog(escape):
                selects = findItemsIn(items,[listItems[idx].getLabel() for idx in select],item_key='name')
                self.library.setEnableStates(type,selects)
                setPropertyBool('pendingChange',True)
                self.buildPredefinedChannels(type)
        return True


    def recoverPredefined(self): 
        # #todo if no library enabled, chk channels.json for predefined. prompt to recover and reenable in library.json
        return True
        # predefined   = self.channels.getPredefinedChannels()
        # libraryItems = []
        # libraryItems.extend([self.library.getLibraryItems(type,enabled=True) for type in CHAN_TYPES])
        # if len(predefined) > 0 and len(libraryItems) == 0:
        # if yesnoDialog
       

    def buildLibraryItems(self):
        funcs = [self.recoverPredefined,
                 self.library.fillLibraryItems,
                 self.library.chkLibraryItems]
        for func in funcs:
            if not func(): return False
        return self.buildPredefinedChannels()
        

    def buildPredefinedChannels(self, type=None):#convert enabled library items into channels.
        libraryItems = {}
        if type is None: types = CHAN_TYPES
        else: types = [type]
        for type in types:
            if type == LANGUAGE(30033): self.buildImports()            
            else: libraryItems[type] = self.library.getLibraryItems(type, enabled=True)
        return self.writer.buildPredefinedChannels(libraryItems)
        
        
    def buildImports(self):#convert enabled imports to channel items.
        imports  = self.recommended.findbyType(type='iptv')
        existing = self.library.getLibraryItems(LANGUAGE(30033), enabled=True)
        items = [item for item in imports for exists in existing if item['name'] == exists['name']]
        return self.writer.buildImports(items)

        
    def clearPredefined(self):
        self.log('clearPredefined')
        if isBusy(): return notificationDialog(LANGUAGE(30029))
        with busy_dialog():
            if not yesnoDialog('%s?'%(LANGUAGE(30077))): return
            setBusy(True)
            if self.library.clearLibraryItems():
                # self.buildPredefinedChannels()
                setPropertyBool('pendingChange',True)
                setPropertyBool('autotuned',False)
                setBusy(False)
                return notificationDialog(LANGUAGE(30053))
        return False
        

    def clearUserChannels(self):
        self.log('clearUserChannels')
        if isBusy(): return notificationDialog(LANGUAGE(30029))
        with busy():
            if not yesnoDialog('%s?'%(LANGUAGE(30093))): return
            if self.writer.clearChannels():
                setPropertyBool('pendingChange',True)
                setPropertyBool('autotuned',False)
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
            setSetting('Import_M3U'  ,'')
            setSetting('Import_XMLTV','')
            setSetting('Import_SLUG' ,'')
            setSetting('User_Import' ,'false')
        return notificationDialog(LANGUAGE(30053))
        

    def openEditor(self, file='newsmartplaylist://%s/', media='video'):
        if '%s' in file: file = file%(media)
        self.log('openEditor, file = %s, media = %s'%(file,media))
        with busy_dialog():
            xbmc.executebuiltin("ReplaceWindowAndFocus(smartplaylisteditor,%s,%s)"%(file,media))
            # com = "ReplaceWindowAndFocus(smartplaylisteditor,%s,%s)"%('special://videoplaylists/',media)
            # # com = "ReplaceWindowAndFocus(smartplaylisteditor,%s,%s)"%(file,media)
            # xbmc.executebuiltin(com)
            # xbmc.executebuiltin("ReplaceWindowAndFocus(smartplaylisteditor,%s,%s)"%(file,media))
        # return xbmc.executebuiltin("Action(Enter)")


    def openNode(self, file='', media='video'):
        # file = 'library://video/network-nbc.xml/'
        self.log('openNode, file = %s, media = %s'%(file,media))
        if file: file = '?ltype=%s&path=%s)'%(media,urllib.parse.quote(xbmcvfs.translatePath(file.strip('/').replace('library://','special://userdata/library/'))))
        xbmc.executebuiltin('RunPlugin(plugin://plugin.library.node.editor%s'%(file))
        # # (plugin://plugin.library.node.editor/?ltype=video&path=D%3a%2fKodi%2fportable_data%2fuserdata%2flibrary%2fvideo%2fnetwork-nbc.xml) 


    def selectResource(self, type):
        self.log('selectResource, type = %s'%(type)) 
        notificationDialog('Coming Soon')
        return REAL_SETTINGS.openSettings()

    
    def installResources(self):
        params = ['Resource_Logos','Resource_Ratings','Resource_Networks','Resource_Commericals','Resource_Trailers']
        for param in params:
            addons = getSetting(param).split(',')
            for addon in addons: installAddon(addon)
        return True
    
    def run(self): 
        param = self.sysARG[1]
        self.log('run, param = %s'%(param))
        if isBusy():
            notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            return REAL_SETTINGS.openSettings()
            
        if param == None: pass #opensettings                    
        elif param.startswith('Channel_Manager'):
            return self.openChannelManager()
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
        elif  param == 'Install_Resources':
            return self.installResources()
        else: 
            with busy():
                self.selectPredefined(param.replace('_',' '))
        return REAL_SETTINGS.openSettings()
            
if __name__ == '__main__': Config(sys.argv).run()