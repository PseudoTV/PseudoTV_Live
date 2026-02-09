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
from globals     import *
from manager     import Manager

class Create(object):
    def __init__(self, sysARG={}, listitem=None, fitem=None):
        self.sysARG   = sysARG
        self.fitem    = (fitem or {})
        self.listitem = (listitem or xbmcgui.ListItem())
        
               
    def open(self):
        log('Create: open')
        if not PROPERTIES.isRunning('Create.open') and not PROPERTIES.isRunning('Library.updateLibrary'):
            with PROPERTIES.chkRunning('Create.open'):
                try: manager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=self.fitem.get('citem',{}).get('number',1))
                except Exception as e:
                    log("Create: open, failed! %s"%(e), xbmc.LOGERROR)
                    PROPERTIES.setRunning('Create.open',False)
                finally:del manager
        else: DIALOG.notificationDialog(LANGUAGE(32057)%(ADDON_NAME))
            
            
    def add(self):
        log('Create: add')
        if not self.listitem.getPath(): return DIALOG.notificationDialog(LANGUAGE(32030))
        elif DIALOG.yesnoDialog('Would you like to add:\n[B]%s[/B]\nto the first available %s channel?'%(self.listitem.getLabel(),ADDON_NAME)):
            if not PROPERTIES.isRunning('Create.add'):
                with PROPERTIES.chkRunning('Create.add'), BUILTIN.busy_dialog(lock=True):
                    manager = Manager(MANAGER_XML, ADDON_PATH, "default", start=False, channel=-1)
                    citem           = manager.newChannel
                    citem['number'] = manager.getFirstChannel()
                    citem['type']   = 'Custom'
                    path, citem = manager.validatePaths(Globals._unquoteString(self.listitem.getPath()),citem)
                    name, citem = manager.validateInputs('name',cleanLabel(self.listitem.getLabel()),citem)
                    if not path is None:
                        citem['path']     = [path.strip('/')] 
                        citem['name']     = name
                        citem['id']       = getChannelID(citem['name'], citem['path'], citem['number'], SETTINGS.getMYUUID())
                        citem['favorite'] = True
                        citem['changed']  = True
                        citem['radio']    = True if path.startswith('musicdb://') else False
                        manager.channels.addChannel(manager.setLogo(citem['name'], citem))
                        manager.channels.setChannels()
                        manager.closeManager()
                        timerit(PROPERTIES.setPropTimer)(FIFTEEN,['chkChannels'])#trigger channel building
                        del manager
                        manager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=citem['number'])
                    del manager

                
if __name__ == '__main__': 
    log('Create: __main__, param = %s'%(sys.argv))
    try:    mode = sys.argv[1]
    except: mode = ''
    if   mode == 'manager': 
        with BUILTIN.busy_dialog():
            Create().open()
    elif mode == 'select':  
        with BUILTIN.busy_dialog():
            values = SETTINGS.getSettingList('Select_server')
            values = [cleanLabel(value) for value in values]
            values.insert(0,LANGUAGE(30022)) #Auto
            values.insert(1,LANGUAGE(32069)) #Ask
        select = DIALOG.selectDialog(values, '%s for Channel Setup'%(LANGUAGE(30173)), Globals._findItemsInLST(values, [SETTINGS.getSetting('Default_Channels')])[0], False, SELECT_DELAY, False)
        if not select is None: SETTINGS.setSetting('Default_Channels',values[select])
        else:                  SETTINGS.setSetting('Default_Channels',LANGUAGE(30022))
    else: Create(sys.argv,sys.listitem,Globals._decodePlot(BUILTIN.getInfoLabel('Plot'))).add()