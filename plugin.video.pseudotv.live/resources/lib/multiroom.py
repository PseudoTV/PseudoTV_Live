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
from server     import Discovery

class Service:
    from jsonrpc import JSONRPC
    monitor = xbmc.Monitor()
    jsonRPC = JSONRPC()
    def _interrupt(self, wait: float=.0001) -> bool:
        return (PROPERTIES.isInterrupt() | self.monitor.waitForAbort(wait))
    def _suspend(self) -> bool:
        return PROPERTIES.isSuspend()
        
        
class Multiroom:
    def __init__(self, sysARG=sys.argv, service=None):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG = sysARG
        if service is None:
            service = Service()
        
        self.service    = service
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.jsonRPC.cache
        self.uuid       = SETTINGS.getMYUUID()
        self.friendly   = SETTINGS.getFriendlyName()
        self.remoteURL  = PROPERTIES.getRemoteURL()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _chkDiscovery(self):
        self.log('_chkDiscovery')
        Discovery(service=self.service, multiroom=self)
                

    def hasServers(self, servers={}):
        if not servers: servers = self.getDiscovery()
        self.log('hasServers, servers = %s'%(len(servers)))
        enabledServers = [server for server in list(servers.values()) if server.get('enabled',False)]
        PROPERTIES.setServers(len(servers) > 0)
        PROPERTIES.setEnabledServers(len(enabledServers) > 0)
        SETTINGS.setSetting('Select_server','|'.join([LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],server.get('name')) for server in enabledServers]))
        return servers
        
            
    def getDiscovery(self):
        return getJSON(SERVER_LOC).get('servers',{})


    def setDiscovery(self, servers={}):
        return setJSON(SERVER_LOC,{"servers":self.hasServers(servers)})


    @cacheit(expiration=datetime.timedelta(minutes=30),json_data=True)   
    def getRemote(self, remote):
        self.log("getRemote, remote = %s"%(remote))
        cacheName = 'getRemote.%s'%(remote)
        response  = getURL(remote,header={'Accept':'application/json'},json_data=True)
        if response: 
            response = self.cache.set(cacheName, response, expiration=datetime.timedelta(days=MAX_GUIDEDAYS), json_data=True)
            response['online'] = True
        else:        
            response = (self.cache.get(cacheName, json_data=True) or {}) #retrieve cached response incase server is temporarily offline
            if not response: response['online'] = False
        return response
           
         
    def addServer(self, payload={}):
        if payload:
            servers = self.getDiscovery()
            server  = servers.get(payload.get('name'),{})
            if not server: 
                self.log('addServer, payload = %s'%(payload))
                payload['enabled'] = True #set enabled by default
                DIALOG.notificationDialog('%s: %s'%(LANGUAGE(32047),payload.get('name')))
            else:
                payload['enabled'] = server.get('enabled',False)
                if payload['enabled']:
                    DIALOG.notificationDialog('%s: %s'%(server.get('name'),LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:LANGUAGE(33130),False:LANGUAGE(30129)}[payload.get('online',False)])))
            servers.update({payload.get('name'):payload})
            if self.setDiscovery(servers):
                instancePath = SETTINGS.hasPVRInstance(server.get('name'))
                if       payload.get('enabled',False) and not instancePath: changed = SETTINGS.setPVRRemote(payload.get('host'),payload.get('name'))
                elif not payload.get('enabled',False) and instancePath:     changed = FileAccess.delete(instancePath)
                else:                                                       changed = False
                if changed: PROPERTIES.setEpochTimer('chkPVRRefresh')
            return True


    def delServer(self):
        self.log('delServer')
        def _build(payload):
            return LISTITEMS.buildMenuListItem(payload['name'],'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:LANGUAGE(33130),False:LANGUAGE(30129)}[payload.get('online',False)]),payload['host'],len(payload.get('channels',[]))))
      
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
            return LISTITEMS.buildMenuListItem(payload['name'],'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:LANGUAGE(33130),False:LANGUAGE(30129)}[payload.get('online',False)]),payload['host'],len(payload.get('channels',[]))))
      
        with BUILTIN.busy_dialog():
            servers = self.getDiscovery()
            lizlst  = poolit(__build)(list(servers.values()))
            if len(lizlst) > 0: lizlst.insert(0,LISTITEMS.buildMenuListItem('[COLOR=white][B]- %s[/B][/COLOR]'%(LANGUAGE(30046)),LANGUAGE(33046)))
            else: return
            
        selects = DIALOG.selectDialog(lizlst,LANGUAGE(30130),preselect=[idx for idx, listitem in enumerate(lizlst) if loadJSON(listitem.getPath()).get('enabled',False)])
        if not selects is None:
            if 0 in selects: return BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/multiroom.py,Remove_server)')
            else:
                for idx, liz in enumerate(lizlst):
                    if idx == 0: continue
                    instancePath = SETTINGS.hasPVRInstance(liz.getLabel())
                    if idx in selects:
                        if not servers[liz.getLabel()].get('enabled',False):
                            DIALOG.notificationDialog(LANGUAGE(30099)%(liz.getLabel()))
                            servers[liz.getLabel()]['enabled'] = True
                            __chkSettings(loadJSON(servers[liz.getLabel()].get('settings')))
                        if not instancePath: 
                            if SETTINGS.setPVRRemote(servers[liz.getLabel()].get('host'),liz.getLabel()): PROPERTIES.setEpochTimer('chkPVRRefresh')
                    else:
                        if servers[liz.getLabel()].get('enabled',False):
                            DIALOG.notificationDialog(LANGUAGE(30100)%(liz.getLabel()))
                            servers[liz.getLabel()]['enabled'] = False
                        if instancePath: FileAccess.delete(instancePath)
                return self.setDiscovery(servers)

            
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
    