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

class Backup:
    def __init__(self, writer=None):
        self.log('__init__')
        if writer is None:
            from resources.lib.parser import Writer
            writer = Writer()
        self.writer = writer
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def getFileDate(self, file):
        try:
            fname = pathlib.Path(file)
            mtime = datetime.datetime.fromtimestamp(fname.stat().st_mtime)
            stime = mtime.strftime('%Y-%m-%d %I:%M %p')
            self.log('getFileDate, modified %s on %s'%(file,stime))
            return stime
        except:
            return LANGUAGE(30285) #Unknown
        
        
    def hasBackup(self):
        self.log('hasBackup')
        with busy():
            if isClient(): return False
            elif FileAccess.exists(CHANNELFLE_BACKUP):
                PROPERTIES.setPropertyBool('has.Backup',True)
                if not SETTINGS.getSetting('Backup_Channels'):
                    SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(30215),self.getFileDate(CHANNELFLE_BACKUP)))
                if not SETTINGS.getSetting('Recover_Channels'):
                    SETTINGS.setSetting('Recover_Channels','%s [B]%s[/B] Channels?'%(LANGUAGE(30211),len(self.writer.channels.load(CHANNELFLE_BACKUP).get('channels',[]))))
                return True
            else:
                PROPERTIES.setPropertyBool('has.Backup',False)
                SETTINGS.setSetting('Backup_Channels'  ,'')
                SETTINGS.setSetting('Recover_Channels' ,'')
                return False


    def backupChannels(self):
        self.log('backupChannels')
        if   isClient(): return False
        elif isBusy():   return self.writer.dialog.notificationDialog(LANGUAGE(30029))
        elif FileAccess.exists(CHANNELFLE_BACKUP):
            if not self.writer.dialog.yesnoDialog('%s\n%s?'%(LANGUAGE(30212),SETTINGS.getSetting('Backup_Channels'))): 
                return False
                
        with busy():
            if FileAccess.copy(getUserFilePath(CHANNELFLE),CHANNELFLE_BACKUP):
                PROPERTIES.setPropertyBool('has.Backup',True)
                SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(30215),datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')))
                SETTINGS.setSetting('Recover_Channels','%s [B]%s[/B] Channels?'%(LANGUAGE(30211),len(self.writer.channels.load(CHANNELFLE_BACKUP).get('channels',[]))))
                return self.writer.dialog.notificationDialog(LANGUAGE(30053))
            else: self.hasBackup()
            return False
        
        
    def recoverChannels(self, file=CHANNELFLE_BACKUP):
        self.log('recoverChannels, file = %s'%(file))
        if isBusy(): 
            self.writer.dialog.notificationDialog(LANGUAGE(30029))
            return False
        elif isClient(): return False
        elif not self.writer.dialog.yesnoDialog('%s?'%(LANGUAGE(30213)%(SETTINGS.getSetting('Recover_Channels').replace(LANGUAGE(30211),''),SETTINGS.getSetting('Backup_Channels')))): 
            return False
        
        with busy_dialog():
            with busy():
                self.writer.recoverChannelsFromBackup(file)
        setRestartRequired()
        return True