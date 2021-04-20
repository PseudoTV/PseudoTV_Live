 #   Copyright (C) 2021 Lunatixz
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
# https://github.com/kodi-community-addons/script.module.simplecache/blob/master/README.md
# -*- coding: utf-8 -*-
 
from resources.lib.globals     import *
from resources.lib.parser      import Writer

class Backup:
    def __init__(self, config):
        self.log('__init__')
        self.writer = config.writer
        self.dialog = config.dialog
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def hasBackup(self):
        self.log('hasBackup')
        with busy():
            if not FileAccess.exists(CHANNELFLE_BACKUP):
                SETTINGS.setSetting('Backup_Channels' ,'')
                SETTINGS.setSetting('Recover_Channels','')
                return False
            else:
                if not SETTINGS.getSetting('Backup_Channels'):
                    SETTINGS.setSetting('Backup_Channels' ,'%s: Unknown'%(LANGUAGE(30215)))
                if not SETTINGS.getSetting('Recover_Channels'):
                    SETTINGS.setSetting('Recover_Channels','%s [B]%s[/B] Channels?'%(LANGUAGE(30211),len(self.writer.channels.load(CHANNELFLE_BACKUP).get('channels',[]))))
                return True
            
            
    def backupChannels(self):
        self.log('backupChannels')
        if isBusy(): 
            return self.dialog.notificationDialog(LANGUAGE(30029))
        elif FileAccess.exists(CHANNELFLE_BACKUP):
            if not self.dialog.yesnoDialog('%s\n%s?'%(LANGUAGE(30212),SETTINGS.getSetting('Backup_Channels'))): 
                return False
                
        with busy():
            if FileAccess.copy(getUserFilePath(CHANNELFLE),CHANNELFLE_BACKUP):
                SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(30215),datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')))
                SETTINGS.setSetting('Recover_Channels','%s [B]%s[/B] Channels?'%(LANGUAGE(30211),len(self.writer.channels.load(CHANNELFLE_BACKUP).get('channels',[]))))
                PROPERTIES.setPropertyBool('has.Backup',self.hasBackup())
                return self.dialog.notificationDialog(LANGUAGE(30053))
            return False
        
        
    def recoverChannels(self, file=CHANNELFLE_BACKUP):
        """
        Recover Channel backup, restart service by toggling enabled.
        """
        self.log('recoverChannels')
        if isBusy(): 
            return self.dialog.notificationDialog(LANGUAGE(30029))
        elif not self.dialog.yesnoDialog('%s?'%(LANGUAGE(30213)%(SETTINGS.getSetting('Recover_Channels').replace(LANGUAGE(30211),''),SETTINGS.getSetting('Backup_Channels')))): 
            return False
            
        with busy_dialog():
            setBusy(True)
            CONFIGFLE = getUserFilePath(CHANNELFLE)
            if FileAccess.move(CONFIGFLE,CHANNELFLE_RESTORE):
                if FileAccess.copy(file,CONFIGFLE):
                    # PROPERTIES.setPropertyBool('restartRequired',True)
                    toggleADDON(ADDON_ID,'false',reverse=True)
            setBusy(False)
            return True