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
from globals    import *
from manager    import Manager

@threadit
def _open(fitem={}):
    log('Create: open')
    if not PROPERTIES.isRunning('Create.open') and SETTINGS.hasAutotuned():
        with PROPERTIES.interruptActivity(), PROPERTIES.chkRunning('Create.open'), BUILTIN.busy_dialog(cancel=PROPERTIES.isRunning('Manager'), lock=True):
            try: manager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=fitem.get('citem',{}).get('number',1))
            except Exception as e:
                log("Create: open, failed! %s"%(e), xbmc.LOGERROR)
                PROPERTIES.setRunning('Create.open',False)
            finally:del manager
            return True
    else: DIALOG.notificationDialog(LANGUAGE(32057)%(ADDON_NAME))
            
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

def _auto(start=1, count=-1):
    if count <= 0: count = min(max(SETTINGS.getSettingInt('Autotune_Limit'), AUTOTUNE_CHANNEL_DEFAULT), AUTOTUNE_CHANNEL_LIMIT)
    autoChannels = SETTINGS.getSettingBool('Enable_Autotuned')
    if not autoChannels:
        hasLibrary  = any([PROPERTIES.hasLibrary(ty) for ty in AUTOTUNE_TYPES])
        hasChannels = PROPERTIES.hasChannels()
        log(f'Create: _auto, Count = {count}, hasLibrary = {hasLibrary}, hasChannels = {hasChannels}')
        
        if not hasChannels and hasLibrary:
            hasBackup  = PROPERTIES.hasBackup()
            hasServers = PROPERTIES.hasServers()
            log(f'Create: _auto, hasBackup = {hasBackup}, hasServers = {hasServers}')
            while not MONITOR().abortRequested():
                retval = DIALOG.yesnoDialog(message='%s\n%s'%(LANGUAGE(32042)%(ADDON_NAME),LANGUAGE(32255)),customlabel=LANGUAGE(32254))
                if   retval == 0: return True #No
                elif retval == 1:
                    SETTINGS.setSettingBool('Enable_Autotuned',True)
                    break #Yes  
                elif retval == 2: #Custom
                    def __manager():  return _open()
                    def __settings(): return Globals._openSettings()
                    def __recover():  return BUILTIN.executebuiltin(f'RunScript(special://home/addons/{ADDON_ID}/resources/lib/backup.py, Recover_Backup)')
                    def __server():   return BUILTIN.executebuiltin(f'RunScript(special://home/addons/{ADDON_ID}/resources/lib/multiroom.py, Select_Server_Client)')
                        
                    with BUILTIN.busy_dialog():
                        menu = [LISTITEMS.buildMenuListItem(LANGUAGE(30107),url='__manager'),
                                LISTITEMS.buildMenuListItem(LANGUAGE(33310),url='__settings')]
                        if hasBackup:  menu.append(LISTITEMS.buildMenuListItem('%s %s'%(LANGUAGE(32112),LANGUAGE(30108)),LANGUAGE(32111),url='__recover'))
                        if hasServers: menu.append(LISTITEMS.buildMenuListItem(LANGUAGE(30173),LANGUAGE(32215),url='__server'))
                    select = DIALOG.selectDialog(menu,multi=False)
                    if not select is None: 
                        try: return eval(menu[select].getPath())()
                        except Exception: log("Create: _auto, failed! %s"%(e), xbmc.LOGERROR)
                return False #Cancel
        else: return True #Has Channnels / No Kodi Library
        
    with DIALOG._progressDialog("", LANGUAGE(30038)) as pDialog:
        items   = []
        manager = Manager(MANAGER_XML, ADDON_PATH, "default", start=False, channel=-1)
        for idx, type in enumerate(AUTOTUNE_TYPES):
            pDialog = DIALOG._updateProgress(pDialog, int(idx*100//len(AUTOTUNE_TYPES)), type, header='%s, %s'%(ADDON_NAME,LANGUAGE(32021)))
            samples = manager.getLibrary(type)
            items.extend([s for s in samples if s])
        manager._addChannels(start, Globals._randomShuffle(items))
        manager.closeManager()
        del manager
    PROPERTIES.setPropTimer('chkChanged')#refresh channel changed
    return True
              
# @threadit      
# def _clrLibrary():
    # #elif mode == 'clear_autotune' : _clrLibrary()
    # DIALOG.notificationDialog(LANGUAGE(32025))
    # manager = Manager(MANAGER_XML, ADDON_PATH, "default", start=False, channel=-1)
    # manager.clrLibraryCache()
    # del manager       
    
# @threadit   
# def _clrBlacklist():
    # # elif mode == 'clear_blackList': _clrBlacklist()
    # DIALOG.notificationDialog(LANGUAGE(32025))
    # SETTINGS.setSetting('Clear_BlackList','')
        
if __name__ == '__main__': 
    log('Create: __main__, param = %s'%(sys.argv))
    try:              mode = sys.argv[1]
    except Exception: mode = ''
    try:
        if   mode == 'add':          _add(sys.argv,sys.listitem)
        elif mode == 'open_manager': _open(Globals._decodePlot(BUILTIN.getInfoLabel('Plot')))
    except Exception as e: 
        log('Create: __main__, failed! %s' % e, xbmc.LOGERROR)
        Globals._notificationDialog(LANGUAGE(30079))