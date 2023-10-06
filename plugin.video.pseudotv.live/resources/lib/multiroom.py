#   Copyright (C) 2023 Lunatixz
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
#
# -*- coding: utf-8 -*-

from globals    import *
from server     import Discovery, Announcement

class Multiroom:
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG  = sysARG
        # announce = Announcement(service.monitor)
        # announce._run() #todo pairing setup.
        # discover = Discovery(service.monitor)
        # discover._run() #todo move all discovery functions to a setting button, part of user select server. include progress bar during scan.
      
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def chkDiscovery(self, servers, forced=False):
        current_server = self.getSetting('Remote_URL')
        if (not current_server or forced) and len(list(servers.keys())) == 1:
            #If one server found autoselect, set server host paths.
            self.log('chkDiscovery,setting server = %s, forced = %s'%(list(servers.keys())[0], forced))
            SETTINGS.setPVRRemote('http://%s'%(list(servers.keys())[0]))
            #sync client resources with server.
            for key, value in list((servers[list(servers.keys())[0]].get('settings',{})).items()):
                try:    self.setSetting(key, value)
                except: pass

            
    def selectServer(self):
        self.log('selectServer')
        labels  = []
        servers = getDiscovery()
        epoch   = time.time()
        current = SETTINGS.getSetting('Remote_URL').strip('http://')
        
        try:    idx = list(servers.keys()).index(current)
        except: idx = 0
            
        for server in servers:
            offline = '(Offline)' if epoch >= (servers[server].get('received',epoch) + UPDATE_WAIT) else ''
            color   = 'dimgray' if offline else 'white'
            labels.append('[COLOR=%s]%s %s[/COLOR]'%(color,servers[server].get('name'),offline))
            
        select = DIALOG.selectDialog(labels, header=LANGUAGE(32048), preselect=idx, useDetails=False, autoclose=90, multi=False)
        if select is not None:
            server = list(servers.keys())[select]
            SETTINGS.chkDiscovery({server:servers[server]}, forced=True)


    def run(self):  
        ctl = (7,1) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))
        
        if param == 'Select_Server': 
            ctl = (6,7)
            self.selectServer()
        return openAddonSettings(ctl)


if __name__ == '__main__': Multiroom(sys.argv).run()
    