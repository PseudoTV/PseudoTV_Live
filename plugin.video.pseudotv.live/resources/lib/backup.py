 #   Copyright (C) 2024 Lunatixz
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
 
from globals    import *
from library    import Library
from channels   import Channels

BACKUP_TIME_FORMAT = '%Y-%m-%d %I:%M %p'

class Backup:
    def __init__(self, sysARG=sys.argv):
        self.sysARG = sysARG
        
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def getFileDate(self, file: str) -> str:
        try:    return datetime.datetime.fromtimestamp(pathlib.Path(xbmcvfs.translatePath(file)).stat().st_mtime).strftime(BACKUP_TIME_FORMAT)
        except: return LANGUAGE(32105) #Unknown
        
        
    def hasBackup(self, file: str=CHANNELFLE_BACKUP) -> bool:
        with busy_dialog():
            self.log('hasBackup')
            if FileAccess.exists(file):
                if file == CHANNELFLE_BACKUP:#main backup file, set meta.
                    PROPERTIES.setEXTProperty('%s.has.Backup'%(ADDON_ID),"true")
                    if (SETTINGS.getSetting('Backup_Channels') or 'Last Backup: Unknown') == 'Last Backup: Unknown':
                        SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(32106),self.getFileDate(file)))
                    if not SETTINGS.getSetting('Recover_Channels'):
                        SETTINGS.setSetting('Recover_Channels','%s [B]%s[/B] Channels?'%(LANGUAGE(32107),len(self.getChannels())))
                return True
            PROPERTIES.setEXTProperty('%s.has.Backup'%(ADDON_ID),"false")
            SETTINGS.setSetting('Backup_Channels' ,'')
            SETTINGS.setSetting('Recover_Channels','')
            return False
            
            
    def getChannels(self, file: str=CHANNELFLE_BACKUP) -> list:
        self.log('getChannels')
        channels = Channels()
        citems   = channels._load(file).get('channels',[])
        del channels
        return citems
        
        
    def backupChannels(self, file: str=CHANNELFLE_BACKUP) -> bool:
        self.log('backupChannels')
        if   isClient(): return DIALOG.notificationDialog(LANGUAGE(32058))
        elif FileAccess.exists(file):
            if not DIALOG.yesnoDialog('%s\n%s?'%(LANGUAGE(32108),SETTINGS.getSetting('Backup_Channels'))): 
                return False
                
        with busy_dialog():
            if FileAccess.copy(CHANNELFLEPATH,file):
                if file == CHANNELFLE_BACKUP: #main backup file, set meta.
                    PROPERTIES.setEXTProperty('%s.has.Backup'%(ADDON_ID),"true")
                    SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(32106),datetime.datetime.now().strftime(BACKUP_TIME_FORMAT)))
                    SETTINGS.setSetting('Recover_Channels','%s [B]%s[/B] Channels?'%(LANGUAGE(32107),len(self.getChannels())))
                return DIALOG.notificationDialog('%s %s'%(LANGUAGE(32110),LANGUAGE(32025)))
        return self.hasBackup()
        

    def recoverChannels(self, file: str=CHANNELFLE_BACKUP) -> bool:
        self.log('recoverChannels, file = %s'%(file))
        if   isClient(): return DIALOG.notificationDialog(LANGUAGE(32058))
        elif not DIALOG.yesnoDialog('%s'%(LANGUAGE(32109)%(SETTINGS.getSetting('Recover_Channels').replace(LANGUAGE(30216),''),SETTINGS.getSetting('Backup_Channels')))): 
            return False
            
        with busy_dialog(), suspendActivity():
            if FileAccess.move(CHANNELFLEPATH,CHANNELFLE_RESTORE):
                if FileAccess.copy(file,CHANNELFLEPATH):
                    library = Library()
                    library.resetLibrary()
                    del library
                    return setPendingRestart()
        
        
    def run(self):  
        ctl = (0,2) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))

        if   param == 'Backup_Channels':  self.backupChannels()
        elif param == 'Recover_Channels': self.recoverChannels()
        return openAddonSettings(ctl)
        
if __name__ == '__main__': Backup(sys.argv).run()