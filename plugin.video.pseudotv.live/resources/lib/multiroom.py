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
#
# -*- coding: utf-8 -*-

from globals    import *
from server     import Discovery, Announcement

class Multiroom:
    client = setClient(isClient())
    
    def __init__(self, sysARG=sys.argv, monitor=None):
        self.log('__init__, sysARG = %s, isClient = %s'%(sysARG,self.client))
        self.sysARG = sysARG
        if monitor is None:
            self.monitor = MONITOR
        else:
            self.monitor = monitor

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def pairAnnouncement(self,wait=900):
        if not self.client and not isRunning('pairAnnouncement'):
            with setRunning('pairAnnouncement'):
                with suspendActivity():
                    self.log('pairAnnouncement')
                    sec = 0
                    inc = int(100/wait)
                    dia = DIALOG.progressDialog(message=LANGUAGE(30078))
                    while not self.monitor.abortRequested() and (sec < wait):
                        sec += 1
                        msg = LANGUAGE(32163)%(ADDON_NAME,LANGUAGE(30130),(wait-sec))
                        dia = DIALOG.progressDialog((inc*sec),dia, msg)
                        Announcement()
                        if self.monitor.waitForAbort(1) or dia is None:
                            break
                    DIALOG.progressDialog(100,dia)
        
            
    def pairDiscovery(self,wait=60):
        pair = None
        if self.client and not isRunning('pairDiscovery'):
            with setRunning('pairDiscovery'):
                with suspendActivity():
                    self.log('pairDiscovery')
                    sec = 0
                    inc = int(100/wait)
                    dia = DIALOG.progressDialog(message=LANGUAGE(30078))
                    while not self.monitor.abortRequested() and (sec < wait):
                        sec += 1
                        msg = LANGUAGE(32162)%(ADDON_NAME,(wait-sec))
                        dia = DIALOG.progressDialog((inc*sec),dia, msg)
                        pay = Discovery()._start()
                        print('pairDiscovery',pay)
                        if self.monitor.waitForAbort(1) or dia is None or pay:
                            break
                    DIALOG.progressDialog(100,dia)

                    # setSetting('Select_server',)
                    # servers = getDiscovery()
                    # if host not in servers and SETTINGS.getSettingInt('Client_Mode') == 1:
                        # DIALOG.notificationWait('%s - %s'%(LANGUAGE(32047),payload.get('name',host)))
                    # servers[host] = payload
                    # setDiscovery(servers)
                    # SETTINGS.chkDiscovery(servers)


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
            
        select = DIALOG.selectDialog(labels, header=LANGUAGE(32048), preselect=idx, useDetails=False, multi=False)
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
        elif param == 'Pair_Announcement': 
            ctl = (6,7)
            self.pairAnnouncement()
        elif param == 'Pair_Discovery': 
            ctl = (6,7)
            self.pairDiscovery()
        return openAddonSettings(ctl)


if __name__ == '__main__': Multiroom(sys.argv).run()
    