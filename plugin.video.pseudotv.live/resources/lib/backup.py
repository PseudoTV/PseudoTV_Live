 #   Copyright (C) 2022 Lunatixz
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

BACKUP_TIME_FORMAT = '%Y-%m-%d %I:%M %p'

class Backup:
    def __init__(self, writer=None):
        if writer is None:
            from resources.lib.parser import Writer
            writer = Writer()
        self.writer = writer
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def getFileDate(self, file):
        try:
            fname = pathlib.Path(xbmcvfs.translatePath(file))
            mtime = datetime.datetime.fromtimestamp(fname.stat().st_mtime)
            stime = mtime.strftime(BACKUP_TIME_FORMAT)
            self.log('getFileDate, modified %s on %s'%(file,stime))
            return stime
        except:
            return LANGUAGE(30285) #Unknown
        
        
    def hasBackup(self):
        with busy():
            self.log('hasBackup')
            if FileAccess.exists(CHANNELFLE_BACKUP) and not isClient():
                PROPERTIES.setPropertyBool('has.Backup',True)
                backup_channel = (SETTINGS.getSetting('Backup_Channels') or 'Last Backup: Unknown')
                if backup_channel == 'Last Backup: Unknown':
                    SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(30215),self.getFileDate(CHANNELFLE_BACKUP)))
                if not SETTINGS.getSetting('Recover_Channels'):
                    SETTINGS.setSetting('Recover_Channels','%s [B]%s[/B] Channels?'%(LANGUAGE(30216),len(self.getChannels())))
                return True

            PROPERTIES.setPropertyBool('has.Backup',False)
            SETTINGS.setSetting('Backup_Channels'  ,'')
            SETTINGS.setSetting('Recover_Channels' ,'')
            return False
            
            
    def getChannels(self):
        self.log('getChannels')
        return self.writer.vault._load(CHANNELFLE_BACKUP).get('channels',[])


    def backupChannels(self):
        self.log('backupChannels')
        if   isClient(): return self.writer.dialog.notificationDialog(LANGUAGE(30288))
        elif isBusy():   return self.writer.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        elif FileAccess.exists(CHANNELFLE_BACKUP):
            if not self.writer.dialog.yesnoDialog('%s\n%s?'%(LANGUAGE(30212),SETTINGS.getSetting('Backup_Channels'))): 
                return False
                
        with busy():
            if FileAccess.copy(CHANNELFLEPATH,CHANNELFLE_BACKUP):
                PROPERTIES.setPropertyBool('has.Backup',True)
                SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(30215),datetime.datetime.now().strftime(BACKUP_TIME_FORMAT)))
                SETTINGS.setSetting('Recover_Channels','%s [B]%s[/B] Channels?'%(LANGUAGE(30216),len(self.getChannels())))
                return self.dialog.notificationDialog('%s %s'%(LANGUAGE(30200),LANGUAGE(30053)))
        return self.hasBackup()
        
        
    def recoverChannels(self, file=CHANNELFLE_BACKUP):
        self.log('recoverChannels, file = %s'%(file))
        if   isClient(): return self.writer.dialog.notificationDialog(LANGUAGE(30288))
        elif isBusy(): 
            self.writer.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            return False
        elif not self.writer.dialog.yesnoDialog('%s'%(LANGUAGE(30213)%(SETTINGS.getSetting('Recover_Channels').replace(LANGUAGE(30216),''),SETTINGS.getSetting('Backup_Channels')))): 
            return False
        
        with busy_dialog(), busy():
            self.writer.recoverChannelsFromBackup(file)
        return True