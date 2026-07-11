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

from variables    import *
from library    import Library
from channels   import Channels
from typing import Optional

class Backup(object):
    def __init__(self, channels: Optional[Channels] = None, sysARG: list = sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.channels = channels
        self.sysARG   = sysARG


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def getBackups(self) -> list:
        keys = [CHANNELBACKUP_KEY,CHANNELCHANGED_KEY,CHANNELLATEST_KEY]
        return list(filter(None,[Globals.properties.setBackup(key, self.getChannels(key)) for key in keys]))


    def backupChannels(self, key: str=CHANNELBACKUP_KEY, silent: bool = True) -> bool:
        channels = self.getChannels()
        if len(channels) > 0:
            self.log('backupChannels, key = %s, channels = %s'%(key, len(channels)))
            with Globals.builtin.busy_dialog(silent):
                if Globals.settings.setCacheSetting(key, self._setChannels(channels), FileAccess._getMD5(key)):
                    if not silent: Globals.dialog.notificationDialog('%s %s\n%s'%(LANGUAGE(32110),LANGUAGE(32025), key))
                    Globals.properties.setBackup(key, channels)
                    return True
        return False


    def recoverChannels(self, key: str=CHANNELBACKUP_KEY) -> bool:
        channels = Channels(key).getChannels()
        if len(channels) > 0:
            self.log('recoverChannels, key = %s, channels = %s'%(key, len(channels)))
            if Globals.dialog.yesnoDialog('%s'%(LANGUAGE(32109)%(len(self.getChannels()),len(channels),key))):
                with Globals.builtin.busy_dialog(), Globals.properties.interruptActivity():
                    if Globals.settings.setCacheSetting(CHANNEL_KEY, self._setChannels(channels), FileAccess._getMD5(CHANNEL_KEY), -1):
                        Globals.dialog.notificationDialog('%s %s\n%s'%(LANGUAGE(32112),LANGUAGE(32025), key))
                        Globals.properties.setPendingRestart()
                        Globals.properties.setBackup(key, channels)
                        return True
        return False


    def _getImport(self, file: str = CHANNEL_BACKUP_FLE) -> dict:
        if FileAccess.exists(file):
            return {os.path.basename(file).title(): { 'name': file, 'channels': FileAccess.getJSON(file).get('channels', []), 'updated': self.getFileDate(file)}}
        return {}


    def getImports(self) -> dict:
        return {os.path.basename(key).title(): self._getImport(key)[os.path.basename(key).title()]
                for key in [CHANNEL_EXPORT_FLE, CHANNEL_BACKUP_FLE]
                if key and FileAccess.exists(key)}


    def hasImports(self) -> bool:
        return len(self.getImports()) > 0


    def exportChannels(self, file: str = CHANNEL_BACKUP_FLE):
        with Globals.builtin.busy_dialog():
            if FileAccess.setJSON(file, self._setChannels(self.getChannels())):
                Globals.dialog.notificationDialog('%s %s\n%s'%(LANGUAGE(32110),LANGUAGE(32025),file))


    def importChannels(self, file: str = CHANNEL_BACKUP_FLE) -> bool:
        if file is None: file = Globals.dialog.browseSources(1,default=file,mask="files")
        if FileAccess.exists(file):
            channels = FileAccess.getJSON(file).get('channels',[])
            if len(channels) > 0:
                self.log('importChannels, file = %s, channels = %s'%(file, len(channels)))
                if Globals.dialog.yesnoDialog('%s'%(LANGUAGE(32109)%(len(self.getChannels()),len(channels),file))):
                    with Globals.builtin.busy_dialog(), Globals.properties.interruptActivity():
                        if Globals.settings.setCacheSetting(CHANNEL_KEY, self._setChannels(channels), FileAccess._getMD5(CHANNEL_KEY), -1):
                            Globals.dialog.notificationDialog('%s %s\n%s'%(LANGUAGE(32112),LANGUAGE(32025),file))
                            Globals.properties.setPendingRestart()
                            Globals.properties.setBackup(CHANNEL_KEY, channels)
                            return True
        return False

                # if not Globals.dialog.yesnoDialog('%s\n%s?'%(LANGUAGE(32108),Globals.settings.getSetting('Backup_Channels'))):
                        # Globals.settings.setSetting('Backup_Channels' ,'%s: %s'%(LANGUAGE(32106),datetime.datetime.now().strftime(BACKUP_TIME_FORMAT)))
                        # Globals.settings.setSetting('Recover_Backup','%s [B]%s[/B] Channels?'%(LANGUAGE(32107),len(channels)))

    @staticmethod
    def _setChannels(channels: list) -> dict:
        channelDATA = FileAccess.getJSON(CHANNELFLE_DEFAULT).copy()
        channelDATA['name']     = Globals.properties.getFriendlyName()
        channelDATA['uuid']     = Globals.settings.getMYUUID()
        channelDATA['channels'] = channels
        channelDATA['updated']  = datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
        return channelDATA


    @staticmethod
    def getFileDate(file: str) -> str:
        try:              return Globals._epochTime(pathlib.Path(FileAccess.translatePath(file)).stat().st_mtime,tz=False).strftime(BACKUP_TIME_FORMAT)
        except Exception: return datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)


    @staticmethod
    def _selectRestore(msg: str, items: list = []) -> Optional[str]:
        def __buildMenuItem(item: dict): #build menu item
            return Globals.listitems.buildMenuListItem(item.get('name'),f'Channels ({item.get("channels",[])}) - Updated [{item.get("updated","Unknown")}]')

        with Globals.builtin.busy_dialog():
            LOG(f'selectImports, imports = {len(imports)}')
            lizLST = poolit(__buildMenuItem)(list(imports.values()))
            if len(lizLST) > 0 and not Globals.properties.isRunning('Backup.select'):
                with Globals.properties.chkRunning('Backup.select'):
                    select = Globals.dialog.selectDialog(lizLST,f'{LANGUAGE(32067)} {msg}',multi=False)
                    if not select is None:
                        channels = lizLST[select].get('channels',[])
                        if len(channels) > 0: return lizLST[select].get('name')


    def selectImports(self) -> bool:
        try:              return (self.importChannels(self._selectRestore(LANGUAGE(32194),self.getImports())) or False)
        except Exception: return False


    def selectBackups(self) -> bool:
        try:              return (self.recoverChannels(self._selectRestore(LANGUAGE(32110),self.getBackups())) or False)
        except Exception: return False


    def getChannels(self, key: str = CHANNEL_KEY) -> list:
        if not self.channels is None: return self.channels.getChannels()
        return Channels(key).getChannels()


    @threadit
    def run(self):
        with Globals.builtin.busy_dialog():
            ctl = (0,1) #settings return focus
            try:
                param = self.sysARG[1]
                if len(self.sysARG) > 2: args = sys.argv[2]
            except Exception as e:
                self.log(f'run, failed to parse sysARG: {e}', xbmc.LOGWARNING)
                param = None
                args  = None
            if   param == 'Export_Channels': self.exportChannels()
            elif param == 'Backup_Channels': self.backupChannels()
            elif param == 'Select_Imports':  self.selectImports()
            elif param == 'Select_Backups':  self.selectBackups()
            return Globals._openSettings(ctl)

if __name__ == '__main__': Backup(sys.argv).run()
