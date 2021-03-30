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
from resources.lib.manager     import Manager

class Config:
    def __init__(self, sysARG=sys.argv, service=None):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG = sysARG
        
        if service is None:
            from resources.lib.jsonrpc import JSONRPC
            from resources.lib.parser  import Writer
            self.jsonRPC     = JSONRPC()
            self.writer      = Writer(cache=self.jsonRPC.cache)
        else:
            self.jsonRPC     = service.jsonRPC
            self.writer      = service.writer
            
        self.library         = Library(self.jsonRPC)
        self.pool            = self.library.pool
        self.dialog          = self.library.dialog
        self.recommended     = self.library.recommended
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def openChannelManager(self):
        chmanager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", config=self,sysARG=self.sysARG,channel=1)
        del chmanager
            

    def autoTune(self):
        status = False
        if getPropertyBool('autotuned'): return False
        if self.dialog.yesnoDialog(LANGUAGE(30132)%(ADDON_NAME)):
            busy  = self.dialog.progressBGDialog()
            types = list(filter(lambda k:k != LANGUAGE(30033), CHAN_TYPES)) #exclude Imports from autotuning.
            for idx, type in enumerate(types):
                self.log('autoTune, type = %s'%(type))
                busy = self.dialog.progressBGDialog((idx*100//len(types)), busy, '%s'%(type),header='%s, %s'%(ADDON_NAME,LANGUAGE(30102)))
                self.selectPredefined(type,autoTune=AUTOTUNE_LIMIT)
            self.dialog.progressBGDialog(100, busy, '%s...'%(LANGUAGE(30053)))
            status = True
        setPropertyBool('autotuned',True)
        return status
 
 
    def selectPredefined(self, type=None, autoTune=None):
        self.log('selectPredefined, type = %s, autoTune = %s'%(type,autoTune))
        setBusy(True)
        escape = autoTune is not None
        with busy_dialog(escape):
            items = self.library.getLibraryItems(type)
            if not items:
                self.dialog.notificationDialog(LANGUAGE(30103)%(type))
                # self.library.clearLibraryItems(type) #clear stale meta type
                setBusy(False)
                return False
                
            pitems    = self.library.getEnabledItems(items) # existing predefined
            listItems = self.pool.poolList(self.library.buildLibraryListitem,items,type)
            pselect   = findItemsIn(listItems,pitems,val_key='name')
                    
        if autoTune is None:
            select = self.dialog.selectDialog(listItems,'Select %s'%(type),preselect=pselect)
        else:
            if autoTune > len(items): autoTune = len(items)
            select = random.sample(list(set(range(0,len(items)))),autoTune)
            
        if select:
            with busy_dialog(escape):
                pselect = findItemsIn(items,[listItems[idx].getLabel() for idx in select],item_key='name')
                self.library.setEnableStates(type,pselect)
                self.buildPredefinedChannels(type) #save changes, #todo slow fucn, try to unify to single call?
        
        setBusy(False)
        return True


    def buildLibraryItems(self):
        funcs = [self.recoverLibraryFromChannels,
                 self.library.fillLibraryItems,
                 self.library.chkLibraryItems]
        for func in funcs: func()
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
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30077))): return False
            if self.library.clearLibraryItems():
                # self.buildPredefinedChannels()
                setPropertyBool('autotuned',False)
                setPropertyBool('restartRequired',True)
                return self.dialog.notificationDialog(LANGUAGE(30053))
            return False
        

    def clearUserChannels(self):
        self.log('clearUserChannels')
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30093))): return False
            if self.writer.clearChannels():
                setPropertyBool('autotuned',False)
                setPropertyBool('restartRequired',True)
                return self.dialog.notificationDialog(LANGUAGE(30053))
            return False


    def clearBlackList(self):
        self.log('clearBlackList') 
        if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30154))): return False
        return self.recommended.clearBlackList()
        

    def userGroups(self):
        self.log('userGroups')
        retval = self.dialog.inputDialog(LANGUAGE(30076), default=getSetting('User_Groups'))
        if not retval: return
        setSetting('User_Groups',retval)
        self.dialog.notificationDialog(LANGUAGE(30053))


    def clearImport(self):
        self.log('clearImport') 
        with busy_dialog():
            setSetting('Import_M3U'       ,'')
            setSetting('Import_M3U_FILE'  ,'')
            setSetting('Import_M3U_URL'   ,'')
            setSetting('Import_XMLTV'     ,'')
            setSetting('Import_XMLTV_FILE','')
            setSetting('Import_XMLTV_URL' ,'')
            setSetting('Import_SLUG'      ,'')
            setSetting('User_Import'      ,'false')
            setPropertyBool('restartRequired',True)
            return self.dialog.notificationDialog(LANGUAGE(30053))
        

    def openEditor(self, file='newsmartplaylist://{type}/', media='video'):
        ## smartplaylisteditor	
        ## WINDOW_DIALOG_SMART_PLAYLIST_EDITOR	
        ## 10136	
        ## SmartPlaylistEditor.xml
        file = file.format(type=media)
        self.log('openEditor, file = %s, media = %s'%(file,media))
        with busy_dialog():
            xbmc.executebuiltin("ActivateWindow(10136,return)")
            xbmc.sleep(500)
            xbmc.executebuiltin("Action(Back)")
            xbmc.sleep(500)
        xbmc.executebuiltin("ReplaceWindowAndFocus(smartplaylisteditor,%s,%s)"%(file,media))
        #todo create custom plugin to handle editing/creating smartplaylists, call like library node.
        

    def openNode(self, file='', media='video'):
         #todo create PR to library node to accept node for edit through plugin call.
        # file = 'library://video/network-nbc.xml/'
        self.log('openNode, file = %s, media = %s'%(file,media))
        if file: file = '?ltype=%s&path=%s)'%(media,urllib.parse.quote(xbmcvfs.translatePath(file.strip('/').replace('library://','special://userdata/library/'))))
        xbmc.executebuiltin('RunPlugin(plugin://plugin.library.node.editor%s'%(file))
        # # (plugin://plugin.library.node.editor/?ltype=video&path=D%3a%2fKodi%2fportable_data%2fuserdata%2flibrary%2fvideo%2fnetwork-nbc.xml) 


    def installResources(self):
        found  = []
        params = ['Resource_Logos','Resource_Ratings','Resource_Networks','Resource_Commericals','Resource_Trailers']
        for param in params:
            addons = getSetting(param).split(',')
            for addon in addons: found.append(installAddon(addon))
        if True in found: return True
        return self.dialog.notificationDialog(LANGUAGE(30192))
        
        
    def openAddonSettings(self,ctl=(None,None),id=ADDON_ID):
        self.log('openAddonSettings, ctl = %s, id = %s'%(ctl,id))
        ## ctl[0] is the Category (Tab) offset (0=first, 1=second, 2...etc)
        ## ctl[1] is the Setting (Control) offset (0=first, 1=second, 2...etc)# addonId is the Addon ID
        ## Example: self.openAddonSettings((2,3),'plugin.video.name')
        ## This will open settings dialog focusing on fourth setting (control) inside the third category (tab)
        xbmc.executebuiltin('Addon.OpenSettings(%s)'%id)
        xbmc.executebuiltin('SetFocus(%i)'%(ctl[0]+100))
        xbmc.executebuiltin('SetFocus(%i)'%(ctl[1]+80))
        return True
        
        
    def backupChannels(self):
        self.log('backupChannels')
        if   isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029))
        elif FileAccess.exists(CHANNELFLE_BACKUP):
            if not self.dialog.yesnoDialog('%s\n%s?'%(LANGUAGE(30212),getSetting('Backup_Channels'))): return False
                
        with busy():
            if FileAccess.copy(getUserFilePath(CHANNELFLE),CHANNELFLE_BACKUP):
                setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(30215),datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')))
                setSetting('Recover_Channels','%s [B]%s[/B] Channels'%(LANGUAGE(30211),len(self.writer.channels.load(CHANNELFLE_BACKUP).get('channels',[]))))
                return self.dialog.notificationDialog(LANGUAGE(30053))
            return False
        
        
    def recoverChannels(self):
        self.log('recoverChannels')
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029))
        elif not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30213)%(getSetting('Recover_Channels').replace(LANGUAGE(30211),''),getSetting('Backup_Channels')))): return False
        with busy_dialog():
            setBusy(True)
            CONFIGFLE = getUserFilePath(CHANNELFLE)
            if FileAccess.move(CONFIGFLE,CHANNELFLE_RESTORE):
                if FileAccess.copy(CHANNELFLE_BACKUP,CONFIGFLE):
                    # setPropertyBool('restartRequired',True)
                    toggleADDON(ADDON_ID,'false',reverse=True)
            setBusy(False)
            return True
        
        
    def recoverLibraryFromChannels(self):
        self.log('recoverLibraryFromChannels') #re-enable library.json items from channels.json
        if self.writer.channels.load(getUserFilePath(CHANNELFLE)):
            return self.library.recoverItemsFromChannels(self.writer.channels.getPredefinedChannels())
        return False
        
        
    def hasBackup(self):
        self.log('hasBackup')
        if not FileAccess.exists(CHANNELFLE_BACKUP):
            setSetting('Backup_Channels' ,'')
            setSetting('Recover_Channels','')
            return False
        else:
            if not getSetting('Backup_Channels'):
                setSetting('Backup_Channels' ,'%s: Unknown'%(LANGUAGE(30215)))
            if not getSetting('Recover_Channels'):
                setSetting('Recover_Channels','%s [B]%s[/B] Channels'%(LANGUAGE(30211),len(self.writer.channels.load(CHANNELFLE_BACKUP).get('channels',[]))))
            return True
            
            
    def run(self): 
        ctl = (0,0) #settings return focus
        param = self.sysARG[1]
        self.log('run, param = %s'%(param))
        if isBusy():
            self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            return REAL_SETTINGS.openSettings()
                             
        if param.startswith('Channel_Manager'):
            return self.openChannelManager()
        elif  param == 'Clear_Import':
            ctl = (6,8)
            self.clearImport()
        elif  param == 'Clear_Userdefined':
            ctl = (0,4)
            self.clearUserChannels()
        elif  param == 'Clear_Predefined':
            ctl = (1,12)
            self.clearPredefined()
        elif  param == 'Clear_BlackList':
            ctl = (1,13)
            self.clearBlackList()
        elif  param == 'User_Groups':
            ctl = (2,2)
            self.userGroups()
        elif  param == 'Open_Editor':
            ctl = (0,6)
            return self.openEditor()
        elif  param == 'Install_Resources':
            ctl = (5,10)
            self.installResources()
        elif  param == 'Backup_Channels':
            ctl = (0,2)
            self.backupChannels()
        elif  param == 'Recover_Channels':
            ctl = (0,3)
            self.recoverChannels()
        else:
            ctl = (1,1)
            self.selectPredefined(param.replace('_',' '))
        return self.openAddonSettings(ctl)
            
if __name__ == '__main__': Config(sys.argv).run()