#   Copyright (C) 2024 Lunatixz
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
        if not self.listitem.getPath(): return DIALOG.notificationDialog(LANGUAGE(32030))
        if DIALOG.yesnoDialog('Would you like to add:\n[B]%s[/B]\nto the first available %s channel?'%(self.listitem.getLabel(),ADDON_NAME)):
            if not PROPERTIES.isRunning('MANAGER_RUNNING'):
                with PROPERTIES.setRunning('MANAGER_RUNNING'), BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
                    manager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", start=False)
                    channelData = manager.newChannel
                    channelData['type']     = 'Custom'
                    channelData['favorite'] = True
                    channelData['number']   = manager.getFirstAvailChannel()
                    channelData['radio']    = True if self.listitem.getPath().startswith('musicdb://') else False
                    channelData['name'], channelData = manager.validateLabel(cleanLabel(self.listitem.getLabel()),channelData)
                    path, channelData   = manager.validatePath(unquoteString(self.listitem.getPath()),channelData,spinner=False)
                    if path is None: return
                    channelData['path'] = [path.strip('/')] 
                    channelData['id'] = getChannelID(channelData['name'], channelData['path'], channelData['number'])
                    manager.channels.addChannel(channelData)
                    manager.channels.setChannels()
                    PROPERTIES.forceUpdateTime('chkChannels')
                    manager.closeManager()
                    del manager
                manager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", channel=channelData['number'])
                del manager
                
                
    def open(self):
        if not PROPERTIES.isRunning('MANAGER_RUNNING'):
            with PROPERTIES.setRunning('MANAGER_RUNNING'), BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
                manager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", channel=self.fitem.get('citem',{}).get('number',1))
            del manager
        
                
if __name__ == '__main__': 
    param = sys.argv[1]
    log('Create: __main__, param = %s'%(param))
    if param == 'manage': Create(sys.argv,listitem=sys.listitem,fitem=decodePlot(BUILTIN.getInfoLabel('Plot'))).open()
    else:                 Create(sys.argv,listitem=sys.listitem,fitem=decodePlot(BUILTIN.getInfoLabel('Plot'))).add()