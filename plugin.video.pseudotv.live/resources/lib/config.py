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
from resources.lib.plugin      import Plugin
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
        
        self.writer      = Writer(inherited=self)
        self.channels    = self.writer.channels
        
        self.library     = self.writer.library
        self.recommended = self.library.recommended
        
        self.jsonRPC     = self.writer.jsonRPC
        self.resources   = self.jsonRPC.resources
        
        self.backup      = Backup(self)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def openChannelManager(self, chnum=1):
        self.log('openChannelManager, chnum = %s'%(chnum))
        if isClient(): return
        chmanager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", sysARG=self.sysARG,config=self,channel=chnum)
        del chmanager
        PROPERTIES.setPropertyBool('Config.Running',False)


    def openChannelWidgets(self, chnum=1):
        self.log('openChannelWidgets, chnum = %s'%(chnum))
        chmanager = Widgets("%s.widgets.xml"%(ADDON_ID), ADDON_PATH, "default", sysARG=self.sysARG,config=self,channel=chnum)
        del chmanager
        PROPERTIES.setPropertyBool('Config.Running',False)


    def autoTune(self):
        if (isClient() | getAutoTuned()): return False #already ran or dismissed by user, check on next reboot.
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
        types.remove(LANGUAGE(30033)) #exclude Imports from auto tuning. ie. Recommended Services
        for idx, type in enumerate(types):
            self.log('autoTune, type = %s'%(type))
            busy = self.dialog.progressBGDialog((idx*100//len(types)), busy, '%s'%(type),header='%s, %s'%(ADDON_NAME,LANGUAGE(30102)))
            self.library.selectPredefined(type,AUTOTUNE_LIMIT)
        self.dialog.progressBGDialog(100, busy, '%s...'%(LANGUAGE(30053)))
        setAutoTuned()
        return True


    def clearPredefined(self):
        self.log('clearPredefined')
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30077))): return False
            if self.library.clearLibraryItems():
                setAutoTuned(False)
                setPendingChange()
                return self.dialog.notificationDialog(LANGUAGE(30053))
    

    def clearUserChannels(self):
        self.log('clearUserChannels')
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30093))): return False
            if self.writer.clearChannels(all=False):
                setAutoTuned(False)
                setRestartRequired()
                return self.dialog.notificationDialog(LANGUAGE(30053))


    def clearBlackList(self):
        self.log('clearBlackList') 
        if isBusy(): return self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        with busy():
            if not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30154))): 
                return False
            return self.recommended.clearBlackList()


    def run(self): 
        ctl = (0,0) #settings return focus
        try:    param = self.sysARG[1]
        except: param = ''
        self.log('run, param = %s'%(param))
        if isBusy():
            self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            return SETTINGS.openSettings()
                             
        if param.startswith('Channel_Manager'):
            return self.openChannelManager()
        elif  param == 'Clear_Userdefined':
            ctl = (0,4)
            self.clearUserChannels()
        elif  param == 'Clear_Predefined':
            ctl = (1,12)
            self.clearPredefined()
        elif  param == 'Clear_BlackList':
            ctl = (1,13)
            self.clearBlackList()
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
            with busy():  
                self.library.selectPredefined(param.replace('_',' '))
        return openAddonSettings(ctl)
            
            
if __name__ == '__main__': Config(sys.argv).run()