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
    player  = PLAYER()
    monitor = MONITOR()
    jsonRPC = JSONRPC()
    def _interrupt(self) -> bool:
        return PROPERTIES.isPendingInterrupt()
    def _suspend(self) -> bool:
        return PROPERTIES.isPendingSuspend()
        
            
class Multiroom:
    def __init__(self, sysARG=sys.argv, service=None):
        self.log('__init__, sysARG = %s'%(sysARG))
        if service is None: service = Service()
        self.service    = service
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.jsonRPC.cache
        self.sysARG     = sysARG
        self.uuid       = SETTINGS.getMYUUID()
        self.friendly   = SETTINGS.getFriendlyName()
        self.remoteHost = PROPERTIES.getRemoteHost()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    @cacheit(checksum=PROPERTIES.getInstanceID(), expiration=datetime.timedelta(minutes=FIFTEEN))
    def _getStatus(self):
        return self.jsonRPC.getSettingValue("services.zeroconf",default=False)


    def _chkDiscovery(self):
        self.log('_chkDiscovery')
        Discovery(service=self.service, multiroom=self)
                

    def chkServers(self, servers={}):
        def __chkSettings(settings):
            [hasAddon(id,install=True,enable=True) for k,addons in list(settings.items()) for id in addons if id.startswith(('resource','plugin'))]
            
        if isinstance(servers,bool): servers = {} #temp fix remove after a by next build
        if not servers: servers = self.getDiscovery()
        PROPERTIES.setServers(len(servers) > 0)
        for server in list(servers.values()):
            online   = server.get('online',False)
            response = self.getRemote(server.get('remotes',{}).get('bonjour'))
            if response: server['online'] = True
            else:        server['online'] = False
            if server.get('enabled',False):
                if online != server.get('online',False): DIALOG.notificationDialog('%s: %s'%(server.get('name'),LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[server.get('online',False)])))
                __chkSettings(loadJSON(server.get('settings')))
        SETTINGS.setSetting('Select_server','|'.join([LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],server.get('name')) for server in self.getEnabled(servers)]))
        self.log('chkServers, servers = %s'%(len(servers)))
        self.setDiscovery(servers)
        return servers


    def getDiscovery(self):
        servers = getJSON(SERVER_LOC).get('servers',{})
        if isinstance(servers,bool): servers = {} #temp fix remove after a by next build
        return servers


    def setDiscovery(self, servers={}):
        return setJSON(SERVER_LOC,{"servers":servers})
            
            
    def getEnabled(self, servers={}):
        if not servers: servers = self.getDiscovery()
        enabled = [server for server in list(servers.values()) if server.get('enabled',False)]
        PROPERTIES.setEnabledServers(len(enabled) > 0)
        return enabled
            

    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN), json_data=True)
    def getRemote(self, remote):
        self.log("getRemote, remote = %s"%(remote))
        cacheName = 'getRemote.%s'%(remote)
        return requestURL(remote, header={'Accept':'application/json'}, json_data=True, cache=self.cache, checksum=self.uuid, life=datetime.timedelta(days=MAX_GUIDEDAYS))
        
         
    def addServer(self, payload={}):
        self.log('addServer, name = %s'%(payload.get('name')))
        if payload and payload.get('name') and payload.get('host'):
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
            
            if self.setDiscovery(self.chkServers(servers)):
                instancePath = SETTINGS.hasPVRInstance(server.get('name'))
                if       payload.get('enabled',False) and not instancePath: changed = SETTINGS.setPVRRemote(payload.get('host'),payload.get('name'))
                elif not payload.get('enabled',False) and instancePath:     changed = FileAccess.delete(instancePath)
                else:                                                       changed = False
                if changed: PROPERTIES.setPropTimer('chkPVRRefresh')
                self.log('addServer, payload changed, chkPVRRefresh = %s'%(changed))
            return True


    def delServer(self, servers={}):
        self.log('delServer')
        def __build(idx, payload):
            return LISTITEMS.buildMenuListItem(payload.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[payload.get('online',False)]),payload.get('host'),len(payload.get('channels',[]))),icon=DUMMY_ICON.format(text=str(idx+1)),url=dumpJSON(payload))
      
        with BUILTIN.busy_dialog():
            if not servers: servers = self.getDiscovery()
            lizlst  = [__build(idx, server) for idx, server in enumerate(list(servers.values()))]

        selects = DIALOG.selectDialog(lizlst,LANGUAGE(32183))
        if not selects is None:
            [servers.pop(liz.getLabel()) for idx, liz in enumerate(lizlst) if idx in selects]
            if self.setDiscovery(self.chkServers(servers)):
                return DIALOG.notificationDialog(LANGUAGE(30046))


    def selServer(self):
        self.log('selServer')
        def __build(idx, payload):
            return LISTITEMS.buildMenuListItem(payload.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[payload.get('online',False)]),payload.get('host'),len(payload.get('channels',[]))),icon=DUMMY_ICON.format(text=str(idx+1)),url=dumpJSON(payload))
      
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
                            if SETTINGS.setPVRRemote(servers[liz.getLabel()].get('host'),liz.getLabel()): PROPERTIES.setPropTimer('chkPVRRefresh')
                    else:
                        if servers[liz.getLabel()].get('enabled',False):
                            DIALOG.notificationDialog(LANGUAGE(30100)%(liz.getLabel()))
                            servers[liz.getLabel()]['enabled'] = False
                        if instancePath: FileAccess.delete(instancePath)
                with BUILTIN.busy_dialog():
                    return self.setDiscovery(self.chkServers(servers))


    def enableZeroConf(self):
        self.log('enableZeroConf')
        if SETTINGS.getSetting('ZeroConf_Status') == '[COLOR=red][B]%s[/B][/COLOR]'%(LANGUAGE(32253)):
            if BUILTIN.getInfoLabel('Platform.Windows','System'): 
                BUILTIN.executescript('special://home/addons/%s/resources/lib/utilities.py, Show_ZeroConf_QR'%(ADDON_ID))
            if DIALOG.yesnoDialog(message=LANGUAGE(30129)):
                with PROPERTIES.interruptActivity():
                    if self.jsonRPC.setSettingValue("services.zeroconf",True,queue=False):
                        DIALOG.notificationDialog(LANGUAGE(32219)%(LANGUAGE(30035)))
                        PROPERTIES.setEpochTimer('chkKodiSettings')
        else: DIALOG.notificationDialog(LANGUAGE(32219)%(LANGUAGE(30034)))
                    
            
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
        return SETTINGS.openSettings(ctl)


if __name__ == '__main__': timerit(Multiroom(sys.argv).run)(0.1)
    