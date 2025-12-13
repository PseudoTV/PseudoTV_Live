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
#
# -*- coding: utf-8 -*-

from globals    import *
from server     import Discovery

class Service:
    from jsonrpc import JSONRPC
    player  = PLAYER()
    monitor = MONITOR()
    jsonRPC = JSONRPC()
    def _shutdown(self, wait=1.0) -> bool:
        return (self._wait(wait) | PROPERTIES.isPendingShutdown())
    def _interrupt(self) -> bool:
        return PROPERTIES.isPendingInterrupt()
    def _suspend(self, wait=1.0) -> bool:
        return (self._wait(wait) | PROPERTIES.isPendingSuspend())
    def _wait(self, wait=1.0):
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) | PROPERTIES.isPendingShutdown() | PROPERTIES.isPendingRestart() | PROPERTIES.isPendingSuspend() | PROPERTIES.isPendingInterrupt()): return True
            else: wait -= CPU_CYCLE
        return False
        
            
class Multiroom:
    def __init__(self, sysARG=sys.argv, service=None):
        self.log('__init__, sysARG = %s'%(sysARG))
        if service is None: service = Service()
        self.service    = service
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.jsonRPC.cache
        self.sysARG     = sysARG
        self.uuid       = SETTINGS.getMYUUID()
        self.friendly   = PROPERTIES.getFriendlyName()
        self.remoteHost = PROPERTIES.getRemoteHost()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    @cacheit(checksum=PROPERTIES.getInstanceID(), expiration=datetime.timedelta(minutes=FIFTEEN))
    def _getStatus(self):
        self.log('_getStatus')
        return self.jsonRPC.getSettingValue("services.zeroconf",default=False)


    def _chkServers(self, servers={}):
        def __chkResources(settings):
            [SETTINGS.hasAddon(id,install=True,enable=True) for k,addons in list(settings.items()) for id in addons if id.startswith(('resource','plugin'))]
            
        def __chkResumeURLs(urls=[]):
            log('_chkResumeURLs, urls = %s'%(len(urls)))
            [requestURL(url, cache={"cache":SETTINGS.cacheDB, "json_data": True, "checksum":ADDON_VERSION, "life": datetime.timedelta(minutes=15)}) for url in urls]

        if not servers: servers = self.getDiscovery()
        PROPERTIES.setServers(len(servers) > 0)
        for server in list(servers.values()):
            online   = server.get('online',False)
            response = self.getRemote(server.get('remotes',{}).get('bonjour'))
            if response: server['online'] = True
            else:        server['online'] = False
            if server.get('enabled',False):
                if online != server.get('online',False): DIALOG.notificationDialog('%s: %s'%(server.get('name'),LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[server.get('online',False)])))
                __chkResources(server.get('settings'))
                __chkResumeURLs(server.get('remotes',{}).get('resume',[]))
        SETTINGS.setSetting('Select_server','|'.join([LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],server.get('name')) for server in self.getEnabled(servers)]))
        self.log('_chkServers, servers = %s'%(len(servers)))
        self.setDiscovery(servers)
        return servers


    def getDiscovery(self):
        servers = getJSON(SERVERFLEPATH).get('servers',{})
        if isinstance(servers,bool): servers = {} #temp fix remove after a by next build
        self.log('getDiscovery, servers = %s'%(len(servers)))
        return servers


    def setDiscovery(self, servers={}):
        self.log('setDiscovery, servers = %s'%(len(servers)))
        return setJSON(SERVERFLEPATH,{"servers":servers})
            
            
    def getEnabled(self, servers={}):
        if not servers: servers = self.getDiscovery()
        enabled = [server for server in list(servers.values()) if server.get('enabled',False)]
        PROPERTIES.setEnabledServers(len(enabled) > 0)
        self.log('getEnabled = %s'%(len(enabled)))
        return enabled
            

    def getRemote(self, remote):
        self.log("getRemote, remote = %s"%(remote))
        return requestURL(remote, header={'Accept':'application/json'}, cache={"cache":self.cache, "json_data": False, "checksum":self.uuid, "life": datetime.timedelta(days=MAX_GUIDEDAYS)})
        
         
    def addServer(self, payload={}):
        if isinstance(payload,dict):
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
                
                if self.setDiscovery(self._chkServers(servers)):
                    instancePath = SETTINGS.hasPVRInstance(server.get('name'))
                    if       payload.get('enabled',False) and not instancePath: changed = SETTINGS.setPVRRemote(payload.get('host'),payload.get('name'),cache=True)
                    elif not payload.get('enabled',False) and instancePath:     changed = FileAccess.delete(instancePath)
                    else:                                                       changed = False
                    if changed: PROPERTIES.setPropTimer('chkPVRRefresh')
                    self.log('addServer, payload changed = %s'%(changed))


    def _delServer(self, servers={}):
        self.log('_delServer')
        def __buildMenuItem(payload):
            idx = list(servers.values()).index(payload)
            return LISTITEMS.buildMenuListItem(payload.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[payload.get('online',False)]),payload.get('host'),len(payload.get('channels',[]))),icon=DUMMY_ICON.format(text=str(idx+1)),url=dumpJSON(payload))
      
        with BUILTIN.busy_dialog():
            if not servers: servers = self.getDiscovery()
            lizLST = list()
            lizLST.extend(poolit(__buildMenuItem)(list(servers.values())))

        selects = DIALOG.selectDialog(lizLST,LANGUAGE(32183))
        if not selects is None:
            with BUILTIN.busy_dialog():
                if self.setDiscovery(self._chkServers([servers.pop(liz.getLabel()) for idx, liz in enumerate(lizLST) if not idx in selects])):
                    return DIALOG.notificationDialog(LANGUAGE(30046))


    def _selServer(self):
        self.log('_selServer')
        def __buildMenuItem(payload): #build menu item
            idx = list(servers.values()).index(payload)
            return LISTITEMS.buildMenuListItem(payload.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[payload.get('online',False)]),payload.get('host'),len(payload.get('channels',[]))),icon=DUMMY_ICON.format(text=str(idx+1)),url=dumpJSON(payload))
      
        with BUILTIN.busy_dialog():
            servers = self.getDiscovery()
            lizLST  = list()
            lizLST.extend(poolit(__buildMenuItem)(list(servers.values())))
            if len(lizLST) > 0: lizLST.insert(0,LISTITEMS.buildMenuListItem('[COLOR=white][B]- %s[/B][/COLOR]'%(LANGUAGE(30046)),LANGUAGE(33046))) #remove server menu item
            else: return
            
        if not PROPERTIES.isRunning('Multiroom._selServer'):
            with PROPERTIES.chkRunning('Multiroom._selServer'):
                selects = DIALOG.selectDialog(lizLST,LANGUAGE(30130),preselect=[idx for idx, listitem in enumerate(lizLST) if loadJSON(listitem.getPath()).get('enabled',False)])
                if not selects is None:
                    if 0 in selects: return self._delServer(servers)
                    else:
                        changed = False
                        for idx, liz in enumerate(lizLST):
                            with BUILTIN.busy_dialog():
                                if   idx == 0: continue
                                elif idx in selects:
                                    if not servers[liz.getLabel()].get('enabled',False):
                                        changed = True
                                        servers[liz.getLabel()]['enabled'] = True
                                        DIALOG.notificationDialog(LANGUAGE(30099)%(liz.getLabel()))
                                    if not SETTINGS.hasPVRInstance(liz.getLabel()): 
                                        if SETTINGS.setPVRRemote(servers[liz.getLabel()].get('host'),liz.getLabel(),cache=True):
                                            timerit(PROPERTIES.setPropTimer)(1.0,['chkPVRRefresh'])
                                else:
                                    if servers[liz.getLabel()].get('enabled',False):
                                        changed = True
                                        servers[liz.getLabel()]['enabled'] = False
                                        DIALOG.notificationDialog(LANGUAGE(30100)%(liz.getLabel()))
                                    try: FileAccess.delete(SETTINGS.hasPVRInstance(liz.getLabel()))
                                    except: pass
                        if changed: self.setDiscovery(self._chkServers(servers))


    def _chkZeroConf(self):
        self.log('_chkZeroConf')
        if SETTINGS.getSetting('ZeroConf_Status') == '[COLOR=red][B]%s[/B][/COLOR]'%(LANGUAGE(32253)):
            if BUILTIN.getInfoLabel('Platform.Windows','System'): #prompt windows users to dl bonjour service.
                BUILTIN.executescript('special://home/addons/%s/resources/lib/utilities.py, Show_ZeroConf_QR'%(ADDON_ID))
            if DIALOG.yesnoDialog(message=LANGUAGE(30129)):
                if self.jsonRPC.setSettingValue("services.zeroconf",True,queue=False):
                    DIALOG.notificationDialog(LANGUAGE(32219)%(LANGUAGE(30035)))
                    self._chkDiscovery()
        else: DIALOG.notificationDialog(LANGUAGE(32219)%(LANGUAGE(30034)))
                    
            
    def _run(self):
        try:    param = self.sysARG[1]
        except: param = None
        if param == 'Enable_ZeroConf': 
            ctl = (5,1)
            self._chkZeroConf()
        elif param == 'Select_Server': 
            ctl = (5,11)
            self._selServer()
        elif param == 'Remove_server': 
            ctl = (5,12)
        return SETTINGS.openSettings(ctl)


if __name__ == '__main__': threadit(Multiroom(sys.argv)._run)
    