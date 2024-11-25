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
    def _interrupt(self) -> bool:
        return PROPERTIES.isPendingInterrupt()
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
        self.cache      = service.jsonRPC.cache
        self.uuid       = SETTINGS.getMYUUID()
        self.friendly   = SETTINGS.getFriendlyName()
        self.remoteHost = PROPERTIES.getRemoteHost()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _chkDiscovery(self):
        self.log('_chkDiscovery')
        Discovery(service=self.service, multiroom=self)
                

    def chkServers(self, servers={}):
        def __chkSettings(settings):
            [hasAddon(id,install=True,enable=True) for k,addons in list(settings.items()) for id in addons if id.startswith(('resource','plugin'))]
            
        if not servers: servers = self.getDiscovery()
        PROPERTIES.setServers(len(servers) > 0)
        for server in list(servers.values()):
            online = server.get('online',False)
            if self.getRemote(server.get('remotes',{}).get('bonjour')): server['online'] = True
            else:                                                server['online'] = False
            if server.get('enabled',False):
                if online != server.get('online',False): DIALOG.notificationDialog('%s: %s'%(server.get('name'),LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],{True:'Online',False:'Offline'}[server.get('online',False)])))
                __chkSettings(loadJSON(server.get('settings')))
        SETTINGS.setSetting('Select_server','|'.join([LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],server.get('name')) for server in self.getEnabled(servers)]))
        self.log('chkServers, servers = %s'%(len(servers)))
        return servers


    def getDiscovery(self):
        return getJSON(SERVER_LOC).get('servers',{})


    def setDiscovery(self, servers={}):
        return setJSON(SERVER_LOC,{"servers":self.chkServers(servers)})
            
            
    def getEnabled(self, servers={}):
        if not servers: servers = self.getDiscovery()
        enabled = [server for server in list(servers.values()) if server.get('enabled',False)]
        PROPERTIES.setEnabledServers(len(enabled) > 0)
        return enabled
            
            
    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN), json_data=True)
    def getURL(self, remote):
        return getURL(remote,header={'Accept':'application/json'},json_data=True)


    def getRemote(self, remote):
        self.log("getRemote, remote = %s"%(remote))
        cacheName = 'getRemote.%s'%(remote)
        response  = self.getURL(remote)
        if response: return self.cache.set(cacheName, response, checksum=self.uuid, expiration=datetime.timedelta(days=MAX_GUIDEDAYS), json_data=True)
        else:        return self.cache.get(cacheName, checksum=self.uuid, json_data=True) #retrieve cached response incase server is temporarily offline
        
         
    def addServer(self, payload={}):
        self.log('addServer, payload = %s'%(payload))
        if payload and payload.get('name'):
            payload['online'] = True
            servers = self.getDiscovery()
            server  = servers.get(payload.get('name'),{})
            if not server: 
                payload['enabled'] = not bool(SETTINGS.getSettingBool('Debug_Enable'))  #set enabled by default when not debugging.
                self.log('addServer, adding server = %s'%(payload))
                DIALOG.notificationDialog('%s: %s'%(LANGUAGE(32047),payload.get('name')))
                servers[payload['name']] = payload
            else:
                payload['enabled'] = server.get('enabled',False)
                if payload.get('md5',server.get('md5')) != server.get('md5'): 
                    self.log('addServer, updating server = %s'%(server))
                    servers.update({payload['name']:payload})
            
            if self.setDiscovery(servers):
                instancePath = SETTINGS.hasPVRInstance(server.get('name'))
                if       payload.get('enabled',False) and not instancePath: changed = SETTINGS.setPVRRemote(payload.get('host'),payload.get('name'))
                elif not payload.get('enabled',False) and instancePath:     changed = FileAccess.delete(instancePath)
                else:                                                       changed = False
                if changed: PROPERTIES.setEpochTimer('chkPVRRefresh')
                self.log('addServer, payload changed, chkPVRRefresh = %s'%(changed))
            return True


    def delServer(self, servers={}):
        self.log('delServer')
        def __build(idx, payload):
            return LISTITEMS.buildMenuListItem(payload.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:'Online',False:'Offline'}[payload.get('online',False)]),payload.get('host'),len(payload.get('channels',[]))),icon=DUMMY_ICON.format(text=str(idx+1)),url=dumpJSON(payload))
      
        with BUILTIN.busy_dialog():
            if not servers: servers = self.getDiscovery()
            lizlst  = [__build(idx, server) for idx, server in enumerate(list(servers.values()))]

        selects = DIALOG.selectDialog(lizlst,LANGUAGE(32183))
        if not selects is None:
            [servers.pop(liz.getLabel()) for idx, liz in enumerate(lizlst) if idx in selects]
            if self.setDiscovery(servers):
                return DIALOG.notificationDialog(LANGUAGE(30046))


    def selServer(self):
        self.log('selServer')
        def __build(idx, payload):
            return LISTITEMS.buildMenuListItem(payload.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:'Online',False:'Offline'}[payload.get('online',False)]),payload.get('host'),len(payload.get('channels',[]))),icon=DUMMY_ICON.format(text=str(idx+1)),url=dumpJSON(payload))
      
        with BUILTIN.busy_dialog():
            servers = self.getDiscovery()
            lizlst  = [__build(idx, server) for idx, server in enumerate(list(servers.values()))]
            if len(lizlst) > 0: lizlst.insert(0,LISTITEMS.buildMenuListItem('[COLOR=white][B]- %s[/B][/COLOR]'%(LANGUAGE(30046)),LANGUAGE(33046)))
            else: return
            
        selects = DIALOG.selectDialog(lizlst,LANGUAGE(30130),preselect=[idx for idx, listitem in enumerate(lizlst) if loadJSON(listitem.getPath()).get('enabled',False)])
        if not selects is None:
            if 0 in selects: return self.delServer(servers)
            else:
                for idx, liz in enumerate(lizlst):
                    if idx == 0: continue
                    instancePath = SETTINGS.hasPVRInstance(liz.getLabel())
                    if idx in selects:
                        if not servers[liz.getLabel()].get('enabled',False):
                            DIALOG.notificationDialog(LANGUAGE(30099)%(liz.getLabel()))
                            servers[liz.getLabel()]['enabled'] = True
                        if not instancePath: 
                            if SETTINGS.setPVRRemote(servers[liz.getLabel()].get('host'),liz.getLabel()): PROPERTIES.setEpochTimer('chkPVRRefresh')
                    else:
                        if servers[liz.getLabel()].get('enabled',False):
                            DIALOG.notificationDialog(LANGUAGE(30100)%(liz.getLabel()))
                            servers[liz.getLabel()]['enabled'] = False
                        if instancePath: FileAccess.delete(instancePath)
                with BUILTIN.busy_dialog():
                    return self.setDiscovery(servers)


    def enableZeroConf(self):
        self.log('enableZeroConf')
        if SETTINGS.getSetting('ZeroConf_Status') == '[COLOR=red][B]Offline[/B][/COLOR]':
            if BUILTIN.getInfoLabel('Platform.Windows','System'): 
                return BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/utilities.py, Show_ZeroConf_QR)')
            elif DIALOG.yesnoDialog(message=LANGUAGE(30129)):
                if self.jsonRPC.setSettingValue("services.zeroconf","true"):
                    DIALOG.notificationDialog(LANGUAGE(32219)%('ZeroConf'))
                    PROPERTIES.forceUpdateTime('chkKodiSettings')
        else: DIALOG.notificationDialog(LANGUAGE(32219)%('ZeroConf Already'))
                    
            
    def run(self):
        try:    param = self.sysARG[1]
        except: param = None
        if param == 'Enable_ZeroConf': 
            ctl = (5,1)
            self.enableZeroConf()
        elif param == 'Select_Server': 
            ctl = (5,11)
            self.selServer()
        elif param == 'Remove_server': 
            ctl = (5,12)
        return openAddonSettings(ctl)


if __name__ == '__main__': Multiroom(sys.argv).run()
    