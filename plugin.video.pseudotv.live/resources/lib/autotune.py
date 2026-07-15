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

# -*- coding: utf-8 -*-

from typing import Optional
from variables    import *
from manager    import Manager
from library    import Library
from channels   import Channels

class Autotune(object):    


    def __init__(self, sysARG: list = sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG  = sysARG 
        
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def _runTune(self, start: int = 1, count: Optional[int] = None) -> bool:                
        autoChannels = Globals.settings.getSettingBool('Autotuned_Channels')
        if not autoChannels:
            hasChannels  = Globals.properties.hasChannels()
            hasLibrary   = any(Globals.properties.hasLibrary(ty) for ty in AUTOTUNE_TYPES)
            if count is None: count = AUTOTUNE_CHANNEL_LIMIT
            self.log(f'_runTune, Count = {count}, hasChannels = {hasChannels}, hasLibrary = {hasLibrary}')
            
            if not hasChannels and hasLibrary:
                hasBackup  = Globals.properties.hasBackup()
                hasServers = Globals.properties.hasServers()
                self.log(f'_runTune, hasBackup = {hasBackup}, hasServers = {hasServers}')
                while not MONITOR().abortRequested():
                    retval = Globals.dialog.yesnoDialog(message='%s %s'%(LANGUAGE(32042).format(name=ADDON_NAME),LANGUAGE(32255)),customlabel=LANGUAGE(32254))
                    if retval == 0: #No
                        return True if hasChannels else Globals._openSettings()
                    elif retval == 1: #Yes
                        Globals.settings.setSettingBool('Autotuned_Channels',True)
                        break       
                    elif retval == 2:#Custom
                        menu = [Globals.listitems.buildMenuListItem(LANGUAGE(30107),LANGUAGE(33108),url='special://home/addons/%s/resources/lib/utilities.py, Channel_Manager'%(ADDON_ID))]
                        if hasBackup:  menu.append(Globals.listitems.buildMenuListItem('%s %s'%(LANGUAGE(32112),LANGUAGE(30108)),LANGUAGE(32111),url='special://home/addons/%s/resources/lib/backup.py, Recover_Backup'%(ADDON_ID)))
                        if hasServers: menu.append(Globals.listitems.buildMenuListItem(LANGUAGE(30173),LANGUAGE(32215),url='special://home/addons/%s/resources/lib/multiroom.py, Select_Server_Client'%(ADDON_ID)))
                        select = Globals.dialog.selectDialog(menu,multi=False)
                        if not select is None: return Globals.builtin.executescript(menu[select].getPath())
                    return False #Cancel
            else: return True
            
        with Globals.dialog._progressDialog("", LANGUAGE(30038)) as self.pDialog:
            items   = []
            manager = Manager(MANAGER_XML, ADDON_PATH, "default", start=False, channel=-1)
            library = Library()
            for idx, type in enumerate(AUTOTUNE_TYPES):
                self.pMSG    = type
                self.pCount  = int(idx*100//len(AUTOTUNE_TYPES))
                self.pDialog = Globals.dialog._updateProgress(self.pDialog, self.pCount, type, header='%s, %s'%(ADDON_NAME,LANGUAGE(32021)))
                items.extend(Globals._randomSamples(library.getLibrary(type),count))
            del library
            if items: manager._addChannels(start, Globals._randomShuffle(items))
            manager.closeManager()
        del manager
        return True
                
                    
    def clrLibrary(self):
        Library().clrLibraryCache()
        Globals.dialog.notificationDialog(LANGUAGE(32025))
       
       
    def clrBlacklist(self):
        Globals.settings.setSetting('Clear_BlackList','')
        Globals.dialog.notificationDialog(LANGUAGE(32025))
        
        
    def run(self):  
        with Globals.builtin.busy_dialog():
            ctl = (1,1) #settings return focus
            try:    param = self.sysARG[1]
            except Exception: param = None
            if param.replace('_',' ') in AUTOTUNE_TYPES:
                ctl = (1,AUTOTUNE_TYPES.index(param.replace('_',' '))+1)
                self.selectAutotune(param.replace('_',' '))
            elif param == 'Clear_Autotune' :  self.clrLibrary()
            elif param == 'Clear_BlackList':  self.clrBlacklist()
            elif param == None: return
            return Globals._openSettings(ctl)
        
if __name__ == '__main__': Autotune(sys.argv).run()
