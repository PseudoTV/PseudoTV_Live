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
from globals    import *
from manager    import Manager
from backup     import Backup

@threadit
def _open(fitem={}):
    log('Create: open')
    if not PROPERTIES.isRunning('Create.open'):
        with PROPERTIES.interruptActivity(), PROPERTIES.chkRunning('Create.open'), BUILTIN.busy_dialog(cancel=PROPERTIES.isRunning('Manager'), lock=True):
            try: manager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=fitem.get('citem',{}).get('number',1))
            except Exception as e:
                log("Create: open, failed! %s"%(e), xbmc.LOGERROR)
                PROPERTIES.setRunning('Create.open',False)
            finally:del manager
            return True
    else: DIALOG.notificationDialog(LANGUAGE(32129)%(ADDON_NAME))
            
@threadit  
def _add(sysARG, listitem: dict={}):
    log('Create: add')
    if not listitem: listitem = xbmcgui.ListItem(offscreen=True)
    path = listitem.getPath()
    if not path: return DIALOG.notificationDialog(LANGUAGE(32030))
    elif DIALOG.yesnoDialog('Would you like to add:\n[B]%s[/B]\nto the first available %s channel?'%(listitem.getLabel(),ADDON_NAME)):
        if not PROPERTIES.isRunning('Create.add'):
            with PROPERTIES.chkRunning('Create.add'):
                manager = Manager(MANAGER_XML, ADDON_PATH, "default", start=False, channel=-1)
                citem           = manager.newChannel
                citem['number'] = manager._findAvailChannel()
                citem['type']   = 'Custom'
                citem['group']  = [ADDON_NAME]
                path, citem = manager.validatePaths(Globals._unquoteString(path),citem)
                name, citem = manager.validateInputs('name',cleanLabel(listitem.getLabel()),citem)
                if not path is None:
                    citem['path']     = [path.strip('/')] 
                    citem['name']     = name
                    citem['id']       = getChannelID(citem['name'], citem['path'], citem['number'], SETTINGS.getMYUUID())
                    citem['favorite'] = True
                    citem['changed']  = True
                    citem['radio']    = True if path.startswith('musicdb://') else False
                    manager._addChannels(citem['number'], citem)
                    manager.closeManager()
                del manager
                PROPERTIES.setPropTimer('chkChanged')#refresh channel changed
                return DIALOG.notificationDialog("%s [B]%s[/B]: [B]%s[/B]\nAdded!"%(LANGUAGE(30223),citem['number'],citem['name']))

def _autotune(start=1, count=-1, automatic=False):
    if not automatic:
        hasLibrary  = PROPERTIES.hasLibrary()
        hasChannels = PROPERTIES.hasChannels()
        log(f'Create: _autotune, hasLibrary = {hasLibrary}, hasChannels = {hasChannels}')
        run_time = time.time()
        if not hasChannels and hasLibrary:
            hasImports = Backup().hasImports()
            hasBackups = PROPERTIES.hasBackups() 
            hasServers = PROPERTIES.hasServers()
            log(f'Create: _autotune, hasImport = {hasImports}, hasBackups = {hasBackups}, hasServers = {hasServers}')
            while not MONITOR().abortRequested():
                retval = DIALOG.yesnoDialog(message='%s\n%s'%(LANGUAGE(32042)%(ADDON_NAME),LANGUAGE(32255)),customlabel=LANGUAGE(32254))
                if retval == 0: #No 
                    SETTINGS.setSettingBool('Enable_Autotune',False)
                    return False if time.time() >= (run_time + AUTOCLOSE_DELAY) else True #return True if autoclose
                elif retval == 1:#Yes  
                    SETTINGS.setSettingBool('Enable_Autotune',True)
                    break
                elif retval == 2: #Custom
                    def __manager():  return _open()
                    def __settings(): return Globals._openSettings()
                    def __import():   return BUILTIN.executebuiltin(f'RunScript(special://home/addons/{ADDON_ID}/resources/lib/backup.py, Select_Imports)')
                    def __backup():   return BUILTIN.executebuiltin(f'RunScript(special://home/addons/{ADDON_ID}/resources/lib/backup.py, Select_Backups)')
                    def __server():   return BUILTIN.executebuiltin(f'RunScript(special://home/addons/{ADDON_ID}/resources/lib/multiroom.py, Select_Servers)')
                        
                    with BUILTIN.busy_dialog():
                        menu = [LISTITEMS.buildMenuListItem(LANGUAGE(30107),url='__manager'),
                                LISTITEMS.buildMenuListItem(LANGUAGE(33310),url='__settings')]
                        if hasImports: menu.append(LISTITEMS.buildMenuListItem('%s %s'%(LANGUAGE(32194),LANGUAGE(30108)),LANGUAGE(32111),url='__import'))
                        if getBackups: menu.append(LISTITEMS.buildMenuListItem('%s %s'%(LANGUAGE(32112),LANGUAGE(30108)),LANGUAGE(32111),url='__backup'))
                        if hasServers: menu.append(LISTITEMS.buildMenuListItem(LANGUAGE(30173),LANGUAGE(32215),url='__server'))
                    select = DIALOG.selectDialog(menu,multi=False)
                    if not select is None: 
                        try: return eval(menu[select].getPath())()
                        except Exception: log("Create: _autotune, failed! %s"%(e), xbmc.LOGERROR)
                return False #Cancel
        else: return True #Has No Channnels / No Kodi Library
        
    with DIALOG._progressDialog("", LANGUAGE(30038)) as pDialog:
        items   = []
        manager = Manager(MANAGER_XML, ADDON_PATH, "default", start=False, channel=-1)
        if count <= 0: count = AUTOTUNE_LIMIT
        for idx, type in enumerate(AUTOTUNE_TYPES):
            
            pDialog = DIALOG._updateProgress(pDialog, int(idx*100//len(AUTOTUNE_TYPES)), type, header='%s, %s'%(ADDON_NAME,LANGUAGE(32021)))
            samples = Globals._randomSamples(manager.getLibrary(type), count)
            items.extend([s for s in samples if s])
        manager._addChannels(start, Globals._randomShuffle(items))
        manager.closeManager()
        del manager
    PROPERTIES.setPropTimer('chkChanged')#refresh channel changed
    return True

if __name__ == '__main__': 
    log('Create: __main__, param = %s'%(sys.argv))
    try:              mode = sys.argv[1]
    except Exception: mode = ''
    try:
        if   mode == 'add':          _add(sys.argv,sys.listitem)
        elif mode == 'open_manager': _open(Globals._decodePlot(BUILTIN.getInfoLabel('ListItem.Plot')))
    except Exception as e: 
        log('Create: __main__, failed! %s' % e, xbmc.LOGERROR)
        Globals._notificationDialog(LANGUAGE(30079))