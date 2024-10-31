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

class Service:
    from jsonrpc import JSONRPC
    monitor = xbmc.Monitor()
    jsonRPC = JSONRPC()
    def _interrupt(self, wait: float=.0001) -> bool:
        return (PROPERTIES.isPendingInterrupt() | self.monitor.waitForAbort(wait))
    def _suspend(self) -> bool:
        return PROPERTIES.isPendingSuspend()
        
        
class Multiroom:
    def __init__(self, sysARG=sys.argv, service=None):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG = sysARG
        if service is None:
            service = Service()
        
        self.service    = service
        self.jsonRPC    = service.jsonRPC
        self.uuid       = SETTINGS.getMYUUID()
        self.friendly   = SETTINGS.getFriendlyName()
        self.remoteURL  = PROPERTIES.getRemoteURL()
        self.payload    = SETTINGS.getBonjour()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _chkAnnouncement(self):
        self.log('_chkAnnouncement')
        Announcement(service=self.service, payload=self.payload)


    def _chkDiscovery(self):
        self.log('_chkDiscovery')
        Discovery(service=self.service, multiroom=self)
                

    def hasServers(self, servers={}):
        if not servers: servers = self.getDiscovery()
        self.log('hasServers, servers = %s'%(len(servers)))
        SETTINGS.setSetting('Select_server','|'.join(['[COLOR=%s][B]%s[/B][/COLOR]'%({True:'green',False:'red'}[v.get('online',False)],v.get('name')) for v in [v for v in list(servers.values()) if v.get('enabled',False)]]))
        PROPERTIES.setServers(len(servers) > 0)
        PROPERTIES.setEXTProperty('%s.has.Enabled_Servers'%(ADDON_ID),str(len([v for v in list(servers.values()) if v.get('enabled',False)]) > 0).lower())
        return servers
        

    def getDiscovery(self):
        return getJSON(SERVER_LOC).get('servers',{})


    def setDiscovery(self, servers={}):
        return setJSON(SERVER_LOC,{"servers":self.hasServers(servers)})


    def _chkPVRservers(self):
        changed = False
        servers = self.getDiscovery()
        for server in list(servers.values()):
            online   = server.get('online',False)
            response = getURL('http://%s/%s'%(server.get('host'),REMOTEFLE),header={'Accept':'application/json'})
            if response: server.update(loadJSON(response))
            server['online'] = True if response else False
            if online != server['online']: DIALOG.notificationDialog(LANGUAGE(32211)%(server.get('name'),{True:'green',False:'red'}[server.get('online',False)],{True:'Online',False:'Offline'}[server.get('online',False)]))
            self.log('_chkPVRservers, %s: online = %s, last updated = %s'%(server.get('name'),server['online'],server.get('updated')))
            instancePath = SETTINGS.hasPVRInstance(server.get('name'))
            if       server.get('enabled',False) and not instancePath: changed = SETTINGS.setPVRRemote(server.get('host'),server.get('name'))
            elif not server.get('enabled',False) and instancePath: FileAccess.delete(instancePath)
        self.setDiscovery(servers)
        return changed


    def addServer(self, payload={}):
        if not payload: return False
        servers  = self.getDiscovery()
        self.log('addServer, payload = %s'%(payload))
        servers.update({payload.get('name'):payload})
        DIALOG.notificationDialog('%s: %s'%(LANGUAGE(32047),payload.get('name')))
        if self.setDiscovery(servers):
            return True


    def delServer(self):
        self.log('delServer')
        def _build(payload):
            return LISTITEMS.buildMenuListItem(payload['name'],'%s - %s: Channels (%s)'%({"True":"[COLOR=green][B]Online[/B][/COLOR]","False":"[COLOR=red][B]Offline[/B][/COLOR]"}[str(payload.get('online',False))],payload['host'],len(payload.get('channels',[]))))
      
        with BUILTIN.busy_dialog():
            servers = self.getDiscovery()
            lizlst  = poolit(_build)(list(servers.values()))

        selects = DIALOG.selectDialog(lizlst,LANGUAGE(32183))
        if not selects is None:
            [servers.pop(liz.getLabel()) for idx, liz in enumerate(lizlst) if idx in selects]
            if self.setDiscovery(servers):
                return DIALOG.notificationDialog(LANGUAGE(30046))


    def selServer(self):
        self.log('selServer')
        def __chkSettings(settings):
            [hasAddon(id,install=True,enable=True) for k,addons in list(settings.items()) for id in addons if id.startswith(('resource','plugin'))]

        def __build(payload):
            return LISTITEMS.buildMenuListItem(payload['name'],'%s - %s: Channels (%s)'%({"True":"[COLOR=green][B]Online[/B][/COLOR]","False":"[COLOR=red][B]Offline[/B][/COLOR]"}[str(payload.get('online',False))],payload['host'],len(payload.get('channels',[]))))
      
        with BUILTIN.busy_dialog():
            servers = self.getDiscovery()
            lizlst  = poolit(__build)(list(servers.values()))
            if len(lizlst) > 0: lizlst.insert(0,LISTITEMS.buildMenuListItem('[COLOR=white][B]- %s[/B][/COLOR]'%(LANGUAGE(30046)),LANGUAGE(33046)))
            
        selects = DIALOG.selectDialog(lizlst,LANGUAGE(30130),preselect=[idx for idx, listitem in enumerate(lizlst) if loadJSON(listitem.getPath()).get('enabled',False)])
        if not selects is None:
            if selects == [0]: return BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/multiroom.py,Remove_server)')
            else:
                lizlst.pop(0)
                for idx, liz in enumerate(lizlst):
                    instancePath = SETTINGS.hasPVRInstance(liz.getLabel())
                    if idx in selects:
                        if not servers[liz.getLabel()].get('enabled',False):
                            DIALOG.notificationDialog(LANGUAGE(30099)%(liz.getLabel()))
                            servers[liz.getLabel()]['enabled'] = True
                            __chkSettings(loadJSON(servers[liz.getLabel()].get('settings')))
                        if not instancePath: SETTINGS.setPVRRemote(servers[liz.getLabel()].get('host'),liz.getLabel())
                    else:
                        if servers[liz.getLabel()].get('enabled',False):
                            DIALOG.notificationDialog(LANGUAGE(30100)%(liz.getLabel()))
                            servers[liz.getLabel()]['enabled'] = False
                        if instancePath: FileAccess.delete(instancePath)
                self.setDiscovery(servers)

            
    def run(self):
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))
        
        if param == 'Select_Server': 
            ctl = (5,11)
            self.selServer()
        elif param == 'Remove_server': 
            ctl = (5,12)
            self.delServer()
        return openAddonSettings(ctl)


if __name__ == '__main__': Multiroom(sys.argv).run()
    