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
from resources.lib.parser      import Writer
from plugin                    import Plugin
from resources.lib.backup      import Backup
from resources.lib.manager     import Manager
from resources.lib.widgets     import Widgets


class Config:
    def __init__(self, sysARG=sys.argv, service=None):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG      = sysARG
        self.progDialog  = None
        self.progress    = None
        self.chanName    = None
        
        if service:
            self.service = service
            self.cache   = service.cache
            self.dialog  = service.dialog
            self.pool    = service.pool
            self.player  = service.player
            self.monitor = service.monitor
            self.rules   = service.rules
        else:
            from resources.lib.cache       import Cache
            from resources.lib.concurrency import PoolHelper
            from resources.lib.rules       import RulesList
            
            self.service = None
            self.cache   = Cache()
            self.dialog  = Dialog()   
            self.pool    = PoolHelper() 
            self.rules   = RulesList()
            self.player  = xbmc.Player()
            self.monitor = xbmc.Monitor()
            self.serviceThread = threading.Timer(0.5, self.triggerPendingChange)
        
        self.writer      = Writer(inherited=self)
        self.channels    = self.writer.channels
        
        self.library     = self.writer.library
        self.recommended = self.library.recommended
        
        self.jsonRPC     = self.writer.jsonRPC
        self.resources   = self.jsonRPC.resources
        
        self.backup      = Backup(config=self)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def openChannelManager(self, chnum=1):
        self.log('openChannelManager, chnum = %s'%(chnum))
        chmanager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", sysARG=self.sysARG,config=self,channel=chnum)
        del chmanager
        PROPERTIES.setPropertyBool('Config.Running',False)


    def openChannelWidgets(self, chnum=1):
        self.log('openChannelWidgets, chnum = %s'%(chnum))
        chmanager = Widgets("%s.widgets.xml"%(ADDON_ID), ADDON_PATH, "default", sysARG=self.sysARG,config=self,channel=chnum)
        del chmanager
        PROPERTIES.setPropertyBool('Config.Running',False)


    def findItemsInLST(self, items, values, item_key='getLabel', val_key='', index=True):
        self.log("findItemsInLST, values = %s, item_key = %s, val_key = %s, index = %s"%(len(values), item_key, val_key, index))
        if not values:
            return [-1]
               
        matches = []
        def match(fkey,fvalue):
            if fkey.lower() == fvalue.lower():
                matches.append(idx if index else item)
                        
        for value in values:
            if isinstance(value,dict): 
                value = value.get(val_key,'')
                
            for idx, item in enumerate(items): 
                if isinstance(item,xbmcgui.ListItem): 
                    if item_key == 'getLabel':  
                        match(item.getLabel() ,value)
                    elif item_key == 'getLabel2': 
                        match(item.getLabel2(),value)
                elif isinstance(item,dict):       
                    match(item.get(item_key,''),value)
                else:                             
                    match(item,value)
                    
        self.log("findItemsInLST, matches = %s"%(matches))
        return matches


    def autoTune(self):
        if   PROPERTIES.getPropertyBool('autotuned'): return False #already ran or dismissed by user, check on next reboot.
        elif self.backup.hasBackup():
            retval = self.dialog.yesnoDialog(LANGUAGE(30132)%(ADDON_NAME,LANGUAGE(30287)), yeslabel=LANGUAGE(30203),customlabel=LANGUAGE(30211))
            if   retval == 2: return self.writer.recoverChannelsFromBackup()
            elif retval != 1:
                setAutoTuned()
                return False
        else:
            if not self.dialog.yesnoDialog(LANGUAGE(30132)%(ADDON_NAME,LANGUAGE(30286))): 
                setAutoTuned()
                return False
       
        busy   = self.dialog.progressBGDialog()
        types  = CHAN_TYPES.copy()
        types.remove(LANGUAGE(30033)) #exclude Imports from auto tuning.
        
        for idx, type in enumerate(types):
            self.log('autoTune, type = %s'%(type))
            busy = self.dialog.progressBGDialog((idx*100//len(types)), busy, '%s'%(type),header='%s, %s'%(ADDON_NAME,LANGUAGE(30102)))
            self.selectPredefined(type,autoTune=AUTOTUNE_LIMIT)
            
        self.dialog.progressBGDialog(100, busy, '%s...'%(LANGUAGE(30053)))
        setAutoTuned()
        return True
 
 
    def selectPredefined(self, type=None, autoTune=None):
        self.log('selectPredefined, type = %s, autoTune = %s'%(type,autoTune))
        escape = autoTune is not None
        with busy_dialog(escape):
            setBusy(True)
            items = self.library.getLibraryItems(type)
            if not items:
                self.dialog.notificationDialog(LANGUAGE(30103)%(type))
                # self.library.clearLibraryItems(type) #clear stale meta type
                setBusy(False)
                return False
                
            pitems    = self.library.getEnabledItems(items) # existing predefined
            listItems = self.pool.poolList(self.library.buildLibraryListitem,items,type)
            pselect   = self.findItemsInLST(listItems,pitems,val_key='name')
                        
            if autoTune is None:
                select = self.dialog.selectDialog(listItems,LANGUAGE(30272)%(type),preselect=pselect)
            else:
                if autoTune > len(items): autoTune = len(items)
                select = random.sample(list(set(range(0,len(items)))),autoTune)
                
            if not select is None:
                with busy_dialog(escape):
                    pselect = self.findItemsInLST(items,[listItems[idx].getLabel() for idx in select],item_key='name')
                    self.library.setEnableStates(type,pselect,items)
                    self.writer.groupLibraryItems(type)
                    self.library.setTypeSettings(type, items)
                    self.setPendingChangeTimer()
            setBusy(False)
            return True


    def buildLibraryItems(self,myService):
        self.log('buildLibraryItems')
        if self.library.fillLibraryItems(myService):
            self.library.chkLibraryItems()
            return self.writer.groupLibraryItems()
        else: 
            return False


    def setPendingChangeTimer(self, wait=30.0):
        self.log('setPendingChangeTimer, wait = %s'%(wait))
        if self.service:
            self.service.startServiceThread()
        else:
            if self.serviceThread.is_alive(): 
                self.serviceThread.cancel()
                try: self.serviceThread.join()
                except: pass
            self.serviceThread = threading.Timer(wait, self.triggerPendingChange)
            self.serviceThread.name = "serviceThread"
            self.serviceThread.start()
        
        
    def triggerPendingChange(self):
        self.log('triggerPendingChange')
        if isBusy():
            self.setPendingChangeTimer()
        else:
            setPendingChange()

        
    def clearPredefined(self):
        self.log('clearPredefined')
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30077))): return False
            if self.library.clearLibraryItems():
                setAutoTuned(False)
                setPendingChange()
                return self.dialog.notificationDialog(LANGUAGE(30053))
        

    def clearUserChannels(self):
        self.log('clearUserChannels')
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30093))): 
                return False
            if self.writer.clearChannels(all=False):
                setAutoTuned(False)
                setRestartRequired()
                return self.dialog.notificationDialog(LANGUAGE(30053))


    def clearBlackList(self):
        self.log('clearBlackList') 
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30154))): 
                return False
            return self.recommended.clearBlackList()
        

    def userGroups(self):
        self.log('userGroups')
        with busy():
            retval = self.dialog.inputDialog(LANGUAGE(30076), default=SETTINGS.getSetting('User_Groups'))
            if not retval: return
            SETTINGS.setSetting('User_Groups',retval)
            return self.dialog.notificationDialog(LANGUAGE(30053))
            

    def clearImport(self):
        self.log('clearImport') 
        with busy_dialog():
            SETTINGS.setSetting('Import_M3U'       ,'')
            SETTINGS.setSetting('Import_M3U_FILE'  ,'')
            SETTINGS.setSetting('Import_M3U_URL'   ,'')
            SETTINGS.setSetting('Import_XMLTV'     ,'')
            SETTINGS.setSetting('Import_XMLTV_FILE','')
            SETTINGS.setSetting('Import_XMLTV_URL' ,'')
            SETTINGS.setSetting('Import_SLUG'      ,'')
            SETTINGS.setSetting('User_Import'      ,'false')
            setRestartRequired()
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


    def sleepTimer(self):
        self.log('sleepTimer')
        sec = 0
        cnx = False
        inc = int(100/OVERLAY_DELAY)
        dia = xbmcgui.DialogProgress()
        dia.create(ADDON_NAME,LANGUAGE(30281))
        
        while not self.monitor.abortRequested() and (sec < OVERLAY_DELAY):
            sec += 1
            msg = '%s\n%s'%(LANGUAGE(30283),LANGUAGE(30284)%((OVERLAY_DELAY-sec)))
            dia.update((inc*sec),msg)
            if self.monitor.waitForAbort(1) or dia.iscanceled():
                cnx = True
                break
        dia.close()
        return not bool(cnx)


    def installResources(self):
        found  = []
        params = ['Resource_Logos','Resource_Ratings','Resource_Networks','Resource_Commericals','Resource_Trailers']
        for param in params:
            addons = SETTINGS.getSetting(param).split(',')
            for addon in addons: found.append(installAddon(addon,manual=True))
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
        elif  param == 'Show_Readme':
            showReadme()
        elif  param == 'Show_Changelog':
            showChangelog()
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
            self.backup.backupChannels()
        elif  param == 'Recover_Channels':
            ctl = (0,3)
            self.backup.recoverChannels()
        else:
            ctl = (1,1)
            self.selectPredefined(param.replace('_',' '))
        return self.openAddonSettings(ctl)
            
if __name__ == '__main__': Config(sys.argv).run()