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

class Create:
    def __init__(self, sysARG: dict={}, listitem: xbmcgui.ListItem=xbmcgui.ListItem(), fitem: dict={}):
        log('Create: __init__, sysARG = %s, fitem = %s\npath = %s'%(sysARG,fitem,listitem.getPath()))
        self.sysARG   = sysARG
        self.fitem    = fitem
        self.listitem = listitem
        
        
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
                    path, citem = manager.validatePaths(unquoteString(self.listitem.getPath()),citem)
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
                        PROPERTIES.setEpochTimer('chkChannels')#trigger channel building
                        del manager
                        manager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=citem['number'])
                    del manager
                
                
    def open(self):
        log('Create: open')
        if not PROPERTIES.isRunning('Create.open'):
            with PROPERTIES.chkRunning('Create.open'), BUILTIN.busy_dialog(lock=True):
                manager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=self.fitem.get('citem',{}).get('number',1))
            del manager
        
                
if __name__ == '__main__': 
    log('Create: __main__, param = %s'%(sys.argv))
    try:    mode = sys.argv[1]
    except: mode = ''
    try:    listitem = sys.listitem
    except: listitem = xbmcgui.ListItem()
    if mode == 'manager': Create(sys.argv,listitem,decodePlot(BUILTIN.getInfoLabel('Plot'))).open()
    else:                 Create(sys.argv,listitem,decodePlot(BUILTIN.getInfoLabel('Plot'))).add()
