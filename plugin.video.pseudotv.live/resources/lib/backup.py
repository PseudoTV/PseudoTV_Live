 #   Copyright (C) 2025 Lunatixz
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

class Backup(object):
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG = sysARG
        
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def getFileDate(self, file: str) -> str:
        try:    return epochTime(pathlib.Path(FileAccess.translatePath(file)).stat().st_mtime,tz=False).strftime(BACKUP_TIME_FORMAT)
        except Exception: return LANGUAGE(32105) #Unknown
        
        
    def hasBackup(self, file=CHANNELFLE_BACKUP) -> bool:
        if file is None:
            files   = [CHANNELFLE_BACKUP, CHANNELFLE_LATEST, CHANNELFLE_CHANGED]
            backups = [file for file in files if FileAccess.exists(file)]
            try:    file = max(backups, key=os.path.getmtime)
            except Exception: return
            self.log('hasBackup, file = %s'%(file))
            
        if FileAccess.exists(file):
            if file == CHANNELFLE_BACKUP:#main backup file, set meta.
                PROPERTIES.setBackup(True)
                if not SETTINGS.getSetting('Backup_Channels'): SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(32106),self.getFileDate(file)))
                if not SETTINGS.getSetting('Recover_Backup'):  SETTINGS.setSetting('Recover_Backup','%s [B]%s[/B] Channels?'%(LANGUAGE(32107),len(self.getChannels(file))))
            return file
            
            
    def getChannels(self, file: str=CHANNELFLE_BACKUP) -> list:
        channels = Channels(file).getChannels()
        PROPERTIES.setHasChannels(len(channels)>0)
        self.log('getChannels, file = %s, channels = %s'%(file, len(channels)))
        return channels
        
        
    def backupChannels(self, file: str=CHANNELFLE_BACKUP, silent: bool=False) -> bool:
        self.log('backupChannels')
        if FileAccess.exists(file) and not silent:
            if not DIALOG.yesnoDialog('%s\n%s?'%(LANGUAGE(32108),SETTINGS.getSetting('Backup_Channels'))): 
                return False
                
        with BUILTIN.busy_dialog(), PROPERTIES.interruptActivity():
            if FileAccess.copy(CHANNELFLEPATH,file):
                if file == CHANNELFLE_BACKUP:#main backup file, set meta.
                    PROPERTIES.setBackup(True)
                    SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(32106),datetime.datetime.now().strftime(BACKUP_TIME_FORMAT)))
                    SETTINGS.setSetting('Recover_Backup','%s [B]%s[/B] Channels?'%(LANGUAGE(32107),len(self.getChannels(file))))
                DIALOG.notificationDialog('%s %s\n%s'%(LANGUAGE(32110),LANGUAGE(32025), os.path.basename(file)))
        if silent: return self.hasBackup(file)
        Globals._openSettings(ctl)
        

    def recoverChannels(self, file: str=CHANNELFLE_BACKUP) -> bool:
        self.log('recoverChannels, file = %s'%(file))
        if not DIALOG.yesnoDialog('%s'%(LANGUAGE(32109)%(SETTINGS.getSetting('Recover_Backup').replace(LANGUAGE(30216),''),SETTINGS.getSetting('Backup_Channels')))): 
            return False
        with BUILTIN.busy_dialog(), PROPERTIES.interruptActivity():
            FileAccess.move(CHANNELFLEPATH,CHANNELFLE_RESTORE)
            if FileAccess.copy(file,CHANNELFLEPATH):
                PROPERTIES.setPendingRestart()
        
    @threadit
    def run(self):  
        with BUILTIN.busy_dialog():
            ctl = (0,1) #settings return focus
            try:    param = self.sysARG[1]
            except Exception: param = None
            if   param == 'Recover_Backup':  self.recoverChannels()
            elif param == 'Backup_Channels': self.backupChannels()
        
if __name__ == '__main__': Backup(sys.argv).run()