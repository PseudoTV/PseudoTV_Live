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

# -*- coding: utf-8 -*-
from typing import Optional
from variables  import *
from manager    import Manager
from backup     import Backup

@threadit
def _open(fitem: Optional[dict] = {}):
    LOG('Create: open')
    if not Globals.properties.isRunning('Create.open'):
        with Globals.properties.interruptActivity(), Globals.properties.chkRunning('Create.open'), Globals.builtin.busy_dialog(cancel=Globals.properties.isRunning('Manager'), lock=True):
            try: manager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=fitem.get('citem',{}).get('number',1))
            except Exception as e:
                LOG("Create: open, failed! %s"%(e), xbmc.LOGERROR)
                Globals.properties.setRunning('Create.open',False)
            finally:del manager
            return True
    else: Globals.dialog.notificationDialog(LANGUAGE(32129).format(name=ADDON_NAME))
            
@threadit  
def _add(sysARG: list, listitem: Optional[dict] = {}):
    LOG('Create: add')
    if not listitem: listitem = xbmcgui.ListItem(offscreen=True)
    path = listitem.getPath()
    if not path: return Globals.dialog.notificationDialog(LANGUAGE(32030))
    elif Globals.dialog.yesnoDialog(LANGUAGE(30234).format(name=listitem.getLabel(), addon=ADDON_NAME)):
        if not Globals.properties.isRunning('Create.add'):
            with Globals.properties.chkRunning('Create.add'):
                manager = Manager(MANAGER_XML, ADDON_PATH, "default", start=False, channel=-1)
                citem           = manager.newChannel
                citem['number'] = manager._findAvailChannel()
                citem['type']   = 'Custom'
                citem['group']  = [ADDON_NAME]
                path, citem = manager.validatePaths(Globals._unquoteString(path),citem)
                name, citem = manager.validateInputs('name',Globals._cleanLabel(listitem.getLabel()),citem)
                if not path is None:
                    citem['path']     = [path.strip('/')] 
                    citem['name']     = name
                    citem['id']       = Globals._getChannelID(citem['name'], citem['path'], citem['number'], Globals.settings.getMYUUID())
                    citem['favorite'] = True
                    citem['changed']  = True
                    citem['radio']    = True if path.startswith('musicdb://') else False
                    manager._addChannels(citem['number'], [citem])
                    manager.closeManager()
                del manager
                Globals.properties.setPropTimer('chkChanged')# Refresh Channel Changed!
                return Globals.dialog.notificationDialog("%s [B]%s[/B]: [B]%s[/B]\nAdded!"%(LANGUAGE(30223),citem['number'],citem['name']))

def _autotune(start: int = 1, count: int = -1, automatic: bool = False):
    run_time    = time.time()
    auto_tune   = Globals.settings.getSettingBool('Enable_Autotune')
    hasLibrary  = Globals.properties.hasLibrary()
    hasChannels = Globals.properties.hasChannels()
    hasImports  = Backup().hasImports()
    hasBackups  = Globals.properties.hasBackups() 
    hasServers  = Globals.properties.hasServers()
    LOG(f'Create: _autotune, auto_tune = {auto_tune}, hasLibrary = {hasLibrary}, hasChannels = {hasChannels}, hasImport = {hasImports}, hasBackups = {hasBackups}, hasServers = {hasServers}')
    if not hasChannels and hasLibrary:
        if not auto_tune: #prompt user to autotune.
            while not MONITOR().abortRequested():
                wait   = AUTOCLOSE_DELAY
                retval = Globals.dialog.yesnoDialog(message='%s %s'%(LANGUAGE(32042).format(name=ADDON_NAME),LANGUAGE(32255)),customlabel=LANGUAGE(32254),autoclose=wait)
                if retval == 0: #No 
                    Globals.settings.setSettingBool('Enable_Autotune',False)
                    return False if time.time() >= (run_time + wait) else True #return True if autoclose ie. no user input.
                elif retval == 1:#Yes  
                    Globals.settings.setSettingBool('Enable_Autotune',True)
                    break
                elif retval == 2: #Custom
                    def __manager():  return _open()
                    def __settings(): return Globals._openSettings()
                    def __import():   return Globals.builtin.executebuiltin(f'RunScript(special://home/addons/{ADDON_ID}/resources/lib/backup.py, Select_Imports)')
                    def __backup():   return Globals.builtin.executebuiltin(f'RunScript(special://home/addons/{ADDON_ID}/resources/lib/backup.py, Select_Backups)')
                    def __server():   return Globals.builtin.executebuiltin(f'RunScript(special://home/addons/{ADDON_ID}/resources/lib/multiroom.py, Select_Servers)')
                        
                    with Globals.builtin.busy_dialog():
                        menu = [Globals.listitems.buildMenuListItem(LANGUAGE(30107),url='__manager'),
                                Globals.listitems.buildMenuListItem(LANGUAGE(33108),url='__settings')]
                        if hasImports: menu.append(Globals.listitems.buildMenuListItem('%s %s'%(LANGUAGE(32194),LANGUAGE(30108)),LANGUAGE(32111),url='__import'))
                        if hasBackups: menu.append(Globals.listitems.buildMenuListItem('%s %s'%(LANGUAGE(32112),LANGUAGE(30108)),LANGUAGE(32111),url='__backup'))
                        if hasServers: menu.append(Globals.listitems.buildMenuListItem(LANGUAGE(30173),LANGUAGE(32215),url='__server'))
                    select = Globals.dialog.selectDialog(menu,multi=False)
                    if not select is None: 
                        try: return eval(menu[select].getPath())()
                        except Exception as e: LOG("Create: _autotune, failed! %s"%(e), xbmc.LOGERROR)
                return False #Cancel
        
        with Globals.dialog._progressDialog("", LANGUAGE(30038)) as pDialog:
            items   = []
            manager = Manager(MANAGER_XML, ADDON_PATH, "default", start=False, channel=-1)
            if count <= 0: count = AUTOTUNE_CHANNEL_LIMIT
            for idx, type in enumerate(AUTOTUNE_TYPES):
                
                pDialog = Globals.dialog._updateProgress(pDialog, int(idx*100//len(AUTOTUNE_TYPES)), type, header='%s, %s'%(ADDON_NAME,LANGUAGE(32021)))
                samples = Globals._randomSamples(manager.getLibrary(type), count)
                items.extend([s for s in samples if s])
            if items: manager._addChannels(start, Globals._randomShuffle(items))
            manager.closeManager()
            del manager
        Globals.properties.setPropTimer('chkChanged')# Refresh Channel Changed!
        return True

if __name__ == '__main__': 
    LOG('Create: __main__, param = %s'%(sys.argv))
    try:              mode = sys.argv[1]
    except Exception: mode = ''
    try:
        if   mode == 'add':          _add(sys.argv,sys.listitem)
        elif mode == 'open_manager': _open(Globals._decodePlot(Globals.builtin.getInfoLabel('ListItem.Plot')))
    except Exception as e: 
        LOG('Create: __main__, failed! %s' % e, xbmc.LOGERROR)
        Globals._notificationDialog(LANGUAGE(30079))