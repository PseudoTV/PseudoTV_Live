 #   Copyright (C) 2026 Lunatixz
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
    def __init__(self, channels=None, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.channels = channels
        self.sysARG   = sysARG
        
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getBackups(self):
        keys = [CHANNELBACKUP_KEY,CHANNELCHANGED_KEY,CHANNELLATEST_KEY]
        return list(filter(None,[PROPERTIES.setBackup(key, self.getChannels(key)) for key in keys]))
        
        
    def backupChannels(self, key: str=CHANNELBACKUP_KEY, silent=True) -> bool:
        channels = self.getChannels()
        if len(channels) > 0:
            self.log('backupChannels, key = %s, channels = %s'%(key, len(channels)))
            with BUILTIN.busy_dialog(silent):
                if SETTINGS.setCacheSetting(key, self._setChannels(channels), FileAccess._getMD5(key)):
                    if not silent: DIALOG.notificationDialog('%s %s\n%s'%(LANGUAGE(32110),LANGUAGE(32025), key))
                    PROPERTIES.setBackup(key, channels)
                    return True
        return False
                    
            
    def recoverChannels(self, key: str=CHANNELBACKUP_KEY) -> bool:
        channels = Channels(key).getChannels()
        if len(channels) > 0:
            self.log('recoverChannels, key = %s, channels = %s'%(key, len(channels)))
            if DIALOG.yesnoDialog('%s'%(LANGUAGE(32109)%(len(self.getChannels()),len(channels),key))): 
                with BUILTIN.busy_dialog(), PROPERTIES.interruptActivity():
                    if SETTINGS.setCacheSetting(CHANNEL_KEY, self._setChannels(channels), FileAccess._getMD5(CHANNEL_KEY), -1):
                        DIALOG.notificationDialog('%s %s\n%s'%(LANGUAGE(32112),LANGUAGE(32025), key))
                        PROPERTIES.setPendingRestart()
                        PROPERTIES.setBackup(key, channels)
                        return True
        return False
            
            
    def _getImport(self, file=CHANNEL_BACKUP_FLE):
        if FileAccess.exists(file):
            return dict(os.path.basename(file).title(), {'name':file, 'channels': FileAccess.getJSON(file).get('channels',[]), 'updated':self.getFileDate(file)})
        
            
    def getImports(self):
        keys = [CHANNELFLEPATH,CHANNEL_BACKUP_FLE]
        return list(filter(None,[self._getImport(key) for key in keys]))
        
            
    def hasImports(self):
        return len(self.getImports()) > 0
            
            
    def exportChannels(self, file=CHANNEL_BACKUP_FLE):
        with BUILTIN.busy_dialog():
            if FileAccess.setJSON(file, self._setChannels(self.getChannels())):
                DIALOG.notificationDialog('%s %s\n%s'%(LANGUAGE(32110),LANGUAGE(32025),file))
        
        
    def importChannels(self, file=CHANNEL_BACKUP_FLE):
        if file is None: file = DIALOG.browseSources(1,default=file,mask="files")
        if self.hasImport(file):
            channels = FileAccess.getJSON(file).get('channels',[])
            if len(channels) > 0:
                self.log('importChannels, file = %s, channels = %s'%(file, len(channels)))
                if DIALOG.yesnoDialog('%s'%(LANGUAGE(32109)%(len(self.getChannels()),len(channels),file))): 
                    with BUILTIN.busy_dialog(), PROPERTIES.interruptActivity():
                        if SETTINGS.setCacheSetting(CHANNEL_KEY, self._setChannels(channels), FileAccess._getMD5(CHANNEL_KEY), -1):
                            DIALOG.notificationDialog('%s %s\n%s'%(LANGUAGE(32112),LANGUAGE(32025),file))
                            PROPERTIES.setPendingRestart()
                            PROPERTIES.setBackup(CHANNEL_KEY, channels)
                            return True
        return False

                # if not DIALOG.yesnoDialog('%s\n%s?'%(LANGUAGE(32108),SETTINGS.getSetting('Backup_Channels'))): 
                        # SETTINGS.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(32106),datetime.datetime.now().strftime(BACKUP_TIME_FORMAT)))
                        # SETTINGS.setSetting('Recover_Backup','%s [B]%s[/B] Channels?'%(LANGUAGE(32107),len(channels)))

    @staticmethod
    def _setChannels(channels):
        channelDATA = FileAccess.getJSON(CHANNELFLE_DEFAULT).copy()
        channelDATA['name']     = PROPERTIES.getFriendlyName()
        channelDATA['uuid']     = SETTINGS.getMYUUID()
        channelDATA['channels'] = channels
        channelDATA['updated']  = datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
        return channelDATA
        

    @staticmethod
    def getFileDate(file: str) -> str:
        try:              return epochTime(pathlib.Path(FileAccess.translatePath(file)).stat().st_mtime,tz=False).strftime(BACKUP_TIME_FORMAT)
        except Exception: return datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
            
            
    @staticmethod
    def _selectRestore(msg, items=[]):
        def __buildMenuItem(item): #build menu item
            return LISTITEMS.buildMenuListItem(item.get('name'),f'Channels ({item.get("channels",[])}) - Updated [{item.get("updated","Unknown")}]')
      
        with BUILTIN.busy_dialog():
            log(f'selectImports, imports = {len(imports)}')
            lizLST = poolit(__buildMenuItem)(list(imports.values()))
            if len(lizLST) > 0 and not PROPERTIES.isRunning('Backup.select'):
                with PROPERTIES.chkRunning('Backup.select'):
                    select = DIALOG.selectDialog(lizLST,f'{LANGUAGE(32067)} {msg}',multi=False)
                    if not select is None: 
                        channels = lizLST[select].get('channels',[])
                        if len(channels) > 0: return lizLST[select].get('name')
            
            
    def selectImports(self):
        try:              return (self.importChannels(self._selectRestore(LANGUAGE(32194),self.getImports())) or False)
        except Exception: return False
            
            
    def selectBackups(self):
        try:              return (self.recoverChannels(self._selectRestore(LANGUAGE(32110),self.getBackups())) or False)
        except Exception: return False
            
            
    def getChannels(self, key=CHANNEL_KEY):
        if not self.channels is None: return self.channels.getChannels()
        return Channels(key).getChannels()
        
        
    @threadit
    def run(self):  
        with BUILTIN.busy_dialog():
            ctl = (0,1) #settings return focus
            try:
                param = self.sysARG[1]
                if len(sself.sysARG) > 2: args = sys.argv[2]
            except Exception:
                param = None
                args  = None
            if   param == 'Export_Channels': self.exportChannels()
            elif param == 'Backup_Channels': self.backupChannels()
            elif param == 'Select_Imports':  self.selectImports()
            elif param == 'Select_Backups':  self.selectBackups()
            return Globals._openSettings(ctl)
        
if __name__ == '__main__': Backup(sys.argv).run()