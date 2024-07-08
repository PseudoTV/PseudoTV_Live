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
    def __init__(self, sysARG: dict, listitem: xbmcgui.ListItem=xbmcgui.ListItem()):
        log('Create: __init__, sysARG = %s'%(sysARG))
        if not listitem.getPath(): return DIALOG.notificationDialog(LANGUAGE(32030))
        if DIALOG.yesnoDialog('Would you like to add:\n[B]%s[/B]\nto the first available %s channel?'%(listitem.getLabel(),ADDON_NAME)):
            if not isRunning('MANAGER_RUNNING'):
                with setRunning('MANAGER_RUNNING'), busy_dialog(), suspendActivity():
                    manager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", start=False)
                    channelData = manager.newChannel
                    channelData['type']     = 'Custom'
                    channelData['favorite'] = True
                    channelData['number']   = manager.getFirstAvailChannel()
                    channelData['radio']    = True if listitem.getPath().startswith('musicdb://') else False
                    channelData['name'], channelData   = manager.validateLabel(cleanLabel(listitem.getLabel()),channelData)
                    path, channelData   = manager.validatePath(unquoteString(listitem.getPath()),channelData,spinner=False)
                    if path is None: return
                    channelData['path'] = [path.strip('/')] 
                    channelData['id'] = getChannelID(channelData['name'], channelData['path'], channelData['number'])
                    manager.channels.addChannel(channelData)
                    manager.channels.setChannels()
                    forceUpdateTime('chkChannels')
                    manager.closeManager()
                    del manager
                manager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", channel=channelData['number'])
                del manager
                
if __name__ == '__main__': 
    Create(sys.argv,listitem=sys.listitem)