#   Copyright (C) 2026 Lunatixz
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

from variables     import *
from _services   import _Service

class Multiroom(object):
    def __init__(self, sysARG=sys.argv, service=None):
        if service is None: return
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG     = sysARG
        self.service    = service
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.cache
        self.serverData = FileAccess.getJSON(SERVERFLE_DEFAULT)
        self.serverTEMP = self.serverData.get('servers',[{}]).pop("friendly")
        self.serverKEY  = f'Servers.{self.serverData.get("version",ADDON_VERSION)}'
        self.serverData.update(self._load())


    def log(self, msg, level=xbmc.LOGDEBUG):
        return Globals._log(f"{self.__class__.__name__}: {msg}", level)


    def _getStatus(self):
        self.log('_getStatus')
        return self.jsonRPC.getSettingValue("services.zeroconf",default=False,cache=True)


    def _load(self) -> dict:
        servers = Globals.SETTINGS.getCacheSetting(self.serverKEY, FileAccess._getMD5(self.serverKEY), default={})
        Globals.PROPERTIES.setHasServers(len(servers.get('servers',{})) > 0)
        Globals.SETTINGS.setSetting('Select_server','|'.join([LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],server.get('name')) for server in self.getEnabled(servers.get('servers',{}))]))
        self.log('_load, servers = %s'%(len(servers.get('servers',{}))))
        return servers

       
    def _save(self) -> bool:
        self.log('_save, servers = %s'%(len(self.serverData.get('servers',{}))))
        return Globals.SETTINGS.setCacheSetting(self.serverKEY, self.serverData, FileAccess._getMD5(self.serverKEY), -1)
            
            
    def getServers(self):
        return self.serverData.get('servers',{})


    def _setServers(self, servers=None):
        if servers is None: servers = self.serverData['servers']
        self.serverData["servers"] = servers
        Globals.PROPERTIES.setHasServers(len(servers) > 0)
        Globals.SETTINGS.setSetting('Select_server','|'.join([LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],server.get('name')) for server in self.getEnabled(servers)]))
        self.log('_setServers, servers = %s'%(len(servers)))
        return self._save()
            
            
    def getEnabled(self, servers=None):
        if servers is None: servers = self.getServers()
        enabled = [server for server in list(servers.values()) if server.get('enabled',False)]
        Globals.PROPERTIES.setEnabledServers(len(enabled) > 0)
        self.log('getEnabled = %s'%(len(enabled)))
        return enabled
            

    def getRemote(self, remote):
        self.log("getRemote, remote = %s"%(remote))
        return self.jsonRPC.requestURL(remote, header={'Accept':'application/json'})
        
        
    def addServer(self, payload={}):
        if isinstance(payload,dict) and payload.get('name') and payload.get('host'):
            payload['online'] = True
            servers = self.getServers()
            server  = servers.get(payload.get('name'),{})
            if not server: 
                payload['enabled'] = True
                servers[payload['name']] = payload
                self.log('addServer, adding server = %s'%(payload))
                if payload.get('host') != Globals.PROPERTIES.getRemoteHost(): 
                    Globals.SETTINGS.setPVRRemote(payload.get('host'),payload.get('name')) #add Remote IPTV Simple config
                    Globals.DIALOG.notificationDialog('[B]%s:[/B] %s'%(LANGUAGE(32047),payload.get('name')))
                self._setServers(servers)
            else:
                instancePath = Globals.SETTINGS.instances.hasPVRInstance(server.get('name'))
                payload['enabled'] = server.get('enabled',False)
                if instancePath is None or (payload.get('md5') != server.get('md5',str(random.random()))):#something changed!
                    if payload['enabled']:
                        if payload['online'] != server.get('online',False):
                            Globals.DIALOG.notificationDialog('%s: %s'%(server.get('name'),LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[server.get('online',False)])))
                        if payload.get('host') != Globals.PROPERTIES.getRemoteHost(): 
                            Globals.SETTINGS.setPVRRemote(payload.get('host'),payload.get('name')) #update Remote IPTV Simple config
                        if payload.get('settings') != server.get('settings'):
                            [Globals.SETTINGS.hasAddon(id) for _,addons in list(payload.get('settings',{}).items()) for id in addons if id.startswith(('resource','plugin'))]
                        if payload.get('resume') != server.get('resume'): 
                            [self.getRemote(url) for url in payload.get('resume',[])]
                    else: FileAccess.delete(instancePath) #del IPTV Simple config
                    servers[payload['name']] = payload
                    self.log('addServer, updating server = %s'%(payload))
                    self._setServers(servers)

    def _delServer(self, servers={}):
        self.log('_delServer')
        def __buildMenuItem(payload):
            idx = list(servers.values()).index(payload)
            return Globals.LISTITEMS.buildMenuListItem(payload.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[payload.get('online',False)]),payload.get('host'),len(payload.get('channels',[]))),icon=Globals._getDummyIcon(str(idx+1)),url=FileAccess.dumpJSON(payload))
      
        with Globals.BUILTIN.busy_dialog():
            if not servers: servers = self.getServers()
            lizLST = poolit(__buildMenuItem)(list(servers.values()))

        selects = Globals.DIALOG.selectDialog(lizLST,LANGUAGE(32183))
        if not selects is None:
            with Globals.BUILTIN.busy_dialog():
                if self. _setServers([servers.pop(liz.Globals._getLabel()) for idx, liz in enumerate(lizLST) if not idx in selects]):
                    return Globals.DIALOG.notificationDialog(LANGUAGE(30046))


    def _selServer(self):
        self.log('_selServer')
        def __buildMenuItem(payload): #build menu item
            return Globals.LISTITEMS.buildMenuListItem(payload.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[payload.get('online',False)],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[payload.get('online',False)]),payload.get('host'),len(payload.get('channels',[]))),icon=Globals._getDummyIcon(str(list(servers.values()).index(payload)+1)),url=FileAccess.dumpJSON(payload))
      
        with Globals.BUILTIN.busy_dialog():
            friendly = Globals.PROPERTIES.getFriendlyName()
            servers  = self.getServers()
            if friendly in servers: servers.pop(friendly)
            lizLST = []
            lizLST.extend(poolit(__buildMenuItem)(list(servers.values())))
            if len(lizLST) > 0: lizLST.insert(0,Globals.LISTITEMS.buildMenuListItem('[COLOR=white][B]- %s[/B][/COLOR]'%(LANGUAGE(30046)),LANGUAGE(33046))) #remove server menu item
            else: return
            
        if not Globals.PROPERTIES.isRunning('Multiroom._selServer'):
            with Globals.PROPERTIES.chkRunning('Multiroom._selServer'):
                selects = Globals.DIALOG.selectDialog(lizLST,LANGUAGE(30130),preselect=[idx for idx, listitem in enumerate(lizLST) if FileAccess.loadJSON(listitem.getPath()).get('enabled',False)])
                if not selects is None:
                    if 0 in selects: return self._delServer(servers)
                    else:
                        changed = False
                        for idx, liz in enumerate(lizLST):
                            with Globals.BUILTIN.busy_dialog():
                                if   idx == 0: continue
                                elif idx in selects:
                                    if not servers[liz.Globals._getLabel()].get('enabled',False):
                                        changed = True
                                        servers[liz.Globals._getLabel()]['enabled'] = True
                                        Globals.DIALOG.notificationDialog(LANGUAGE(30099)%(liz.Globals._getLabel()))
                                    if not Globals.SETTINGS.instances.hasPVRInstance(liz.Globals._getLabel()): 
                                        if Globals.SETTINGS.setPVRRemote(servers[liz.Globals._getLabel()].get('host'),liz.Globals._getLabel()):
                                            Globals.PROPERTIES.setPropTimer('chkPVRRefresh')#refresh pvr guide
                                else:
                                    if servers[liz.Globals._getLabel()].get('enabled',False):
                                        changed = True
                                        servers[liz.Globals._getLabel()]['enabled'] = False
                                        Globals.DIALOG.notificationDialog(LANGUAGE(30100)%(liz.Globals._getLabel()))
                                    try: FileAccess.delete(Globals.SETTINGS.instances.hasPVRInstance(liz.Globals._getLabel()))
                                    except Exception: pass
                        if changed: self._setServers(servers)


    def _chkZeroConf(self):
        self.log('_chkZeroConf')
        if Globals.SETTINGS.getSetting('ZeroConf_Status') == '[COLOR=red][B]%s[/B][/COLOR]'%(LANGUAGE(32253)):
            if Globals.BUILTIN.getInfoLabel('System.Platform.Windows'): #prompt windows users to dl bonjour service.
                Globals.BUILTIN.executescript('special://home/addons/%s/resources/lib/utilities.py, Show_ZeroConf_QR'%(ADDON_ID))
            if Globals.DIALOG.yesnoDialog(message=LANGUAGE(30129)):
                if self.jsonRPC.setSettingValue("services.zeroconf",True,queue=False):
                    Globals.DIALOG.notificationDialog(LANGUAGE(32219)%(LANGUAGE(30035)))
                    self.service._que(self.service.tasks.chkDiscovery, 1)
        else: Globals.DIALOG.notificationDialog(LANGUAGE(32219)%(LANGUAGE(30034)))
                            
        
    @threadit
    @staticmethod
    def _run(self):
        try:    param = self.sysARG[1]
        except Exception: param = None
        if param == 'Enable_ZeroConf': 
            ctl = (5,1)
            self._chkZeroConf()
        elif param == 'Select_Server': 
            ctl = (5,11)
            self._selServer()
        elif param == 'Select_Servers': 
            ctl = (5,11)
            Globals.SETTINGS.setSettingBool('Enable_Client',True)
            self._selServer()
        elif param == 'Remove_server': 
            ctl = (5,12)
        return Globals._openSettings(ctl)


if __name__ == '__main__': Multiroom(sys.argv, _Service())._run()
    