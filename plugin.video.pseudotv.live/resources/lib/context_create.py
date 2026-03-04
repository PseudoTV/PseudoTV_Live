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
def _open(fitem):
    log('Create: open')
    if not PROPERTIES.isRunning('Create.open') and not PROPERTIES.isRunning('Library.updateLibrary'):
        with PROPERTIES.chkRunning('Create.open'), BUILTIN.busy_dialog(cancel=PROPERTIES.isRunning('Manager'), lock=True):
            try: manager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=fitem.get('citem',{}).get('number',1))
            except Exception as e:
                log("Create: open, failed! %s"%(e), xbmc.LOGERROR)
                PROPERTIES.setRunning('Create.open',False)
            finally:del manager
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
                    manager.channels.addChannel(manager.setLogo(citem['name'], citem))
                    if manager.channels.setChannels(): timerit(PROPERTIES.setPropTimer)(FIFTEEN,['chkChanged'])#trigger channel building
                    manager.closeManager()
                    manager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=citem['number'])
                del manager

if __name__ == '__main__': 
    log('Create: __main__, param = %s'%(sys.argv))
    try:              mode = sys.argv[1]
    except Exception: mode = ''
    try:
        if   mode == 'manager': _open(Globals._decodePlot(BUILTIN.getInfoLabel('Plot')))
        elif mode == 'select':  
            values = SETTINGS.getSettingList('Select_server')
            values = [cleanLabel(value) for value in values]
            values.insert(0,LANGUAGE(30022)) #Auto
            values.insert(1,LANGUAGE(32069)) #Ask
            select = DIALOG.selectDialog(values, '%s for Channel Setup'%(LANGUAGE(30173)), Globals._findItemsInLST(values, [SETTINGS.getSetting('Default_Channels')])[0], False, SELECT_DELAY, False)
            if not select is None: SETTINGS.setSetting('Default_Channels',values[select])
            else:                  SETTINGS.setSetting('Default_Channels',LANGUAGE(30022))
        else: _add(sys.argv,sys.listitem)
    except Exception as e: 
        log('Create: __main__, failed! %s' % e, xbmc.LOGERROR)
        Globals._notificationDialog(LANGUAGE(30079))