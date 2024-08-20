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
from jsonrpc    import JSONRPC
from server     import Discovery, Announcement

class Service:
    monitor = xbmc.Monitor()
    jsonRPC = JSONRPC()
    def _interrupt(self, wait: float=.001) -> bool:
        return self.monitor.waitForAbort(wait)
        
    def _suspend(self) -> bool:
        return PROPERTIES.isPendingSuspend()

class Multiroom:
    def __init__(self, sysARG=sys.argv, service=None):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG = sysARG
        if service is None: service = Service()
        self.service = service
        self.jsonRPC = service.jsonRPC
        self.uuid    = SETTINGS.getMYUUID()
        self.friendlyName = self.jsonRPC.getFriendlyName()
               
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def pairDiscovery(self, wait=300):
        if not PROPERTIES.isRunning('Multiroom'):
            added = False
            with PROPERTIES.setRunning('Multiroom'):
                self.log('pairDiscovery')
                sec = 0
                dia = DIALOG.progressBGDialog(message=LANGUAGE(32162)%(wait-sec))
                while not self.service.monitor.abortRequested() and (sec < wait):
                    sec += 1  
                    msg = LANGUAGE(32162)%(wait-sec)
                    if dia: dia = DIALOG.progressBGDialog(int((sec)*100//wait),dia, msg)
                    SETTINGS.setSetting('Bonjour_Status',(LANGUAGE(32158)%(wait-sec)))
                    payload = Discovery()._start()
                    added = self.addServer(payload)
                    if added: break
                    if self.service._interrupt(1.0) or dia is None: break
                SETTINGS.setSetting('Bonjour_Status',LANGUAGE(32149))
                if dia: DIALOG.progressBGDialog(100,dia)
            if added: self.sendResponse(payload)
        else: DIALOG.notificationDialog('Announcement Running, Try again later...')
            

    def pairAnnouncement(self, payload, silent=False, wait=900):
        if SETTINGS.getSetting('Bonjour_Status') !=LANGUAGE(32149): return DIALOG.notificationDialog(LANGUAGE(32148))
        if not PROPERTIES.isRunning('Multiroom'):
            with PROPERTIES.setRunning('Multiroom'):
                sec = 0
                inc = int(100/wait)
                if not silent: dia = DIALOG.progressDialog(message=(LANGUAGE(32163)%(self.friendlyName,(wait-sec))))
                else:          dia = False
                while not self.service.monitor.abortRequested() and (sec < wait):
                    self.log('pairAnnouncement, payload = %s, wait = %s, sec = %s'%(payload,wait,sec))
                    sec += 1
                    msg = (LANGUAGE(32163)%(self.friendlyName,(wait-sec)))
                    if dia: dia = DIALOG.progressDialog((inc*sec),dia, msg) 
                    Announcement(payload)
                    npayload = Discovery()._start()
                    if self.addServer(npayload): break
                    if self.service._interrupt(1.5) or dia is None: break
                if dia: DIALOG.progressDialog(100,dia)
        else: DIALOG.notificationDialog('Discovery Running, Try again later...')
    
    
    def getPayload(self):
        def __getSettings():
            return {'Resource_Logos'    :SETTINGS.getSetting('Resource_Logos'),
                    'Resource_Bumpers'  :SETTINGS.getSetting('Resource_Bumpers'),
                    'Resource_Ratings'  :SETTINGS.getSetting('Resource_Ratings'),
                    'Resource_Adverts'  :SETTINGS.getSetting('Resource_Adverts'),
                    'Resource_Trailers' :SETTINGS.getSetting('Resource_Trailers')}

        payload = {'id'      :ADDON_ID,
                   'version' :ADDON_VERSION,
                   'uuid'    :self.uuid,
                   'name'    :self.friendlyName,
                   'host'    :'%s:%s'%(getIP(),SETTINGS.getSettingInt('TCP_PORT')),
                   'settings':__getSettings()}
        payload['md5'] = getMD5(dumpJSON(payload))
        return payload


    def sendResponse(self, payload):
        npayload = self.getPayload()
        npayload['received'] = payload.get('host')
        self.log('sendResponse, npayload = %s'%(npayload))
        self.pairAnnouncement(npayload, silent=True, wait=300)


    def hasServers(self, servers={}):
        if not servers: servers = self.getDiscovery()
        servers = list(servers.keys())
        self.log('hasServers, servers = %s'%(len(servers)))
        if len(servers) > 0: SETTINGS.setSetting('Select_server','Found (%s'%(servers))
        PROPERTIES.setEXTProperty('%s.has.Servers'%(ADDON_ID),str(len(servers) > 0).lower())


    def getDiscovery(self):
        return getJSON(SERVER_LOC).get('servers',{})


    def setDiscovery(self, servers={}):
        self.hasServers(servers)
        return setJSON(SERVER_LOC,{"servers":servers})


    def chkPVRservers(self):
        changed = False
        servers = self.getDiscovery()
        headers = HEADER.copy()
        headers["Content-type"] = "application/vnd.apple.mpegurl"
        for server in list(servers.values()):
            server['online'] = True if getURL('http://%s/%s'%(server.get('host'),M3UFLE),headers) else False
            self.log('chkPVRservers, %s online = %s'%(server.get('name'),server['online']))
            if SETTINGS.hasPVRInstance(server.get('name')):
                if server.get('enabled',False): continue
                else: FileAccess.delete(os.path.join(PVR_CLIENT_LOC,'instance-settings-%s.xml'%(SETTINGS.gePVRInstance(instance))))
            else: changed = SETTINGS.setPVRRemote(server.get('host'),server.get('name'))
        self.setDiscovery(servers)
        return changed


    def addServer(self, payload={}):
        if payload:
            servers = self.getDiscovery()
            if not servers.get(payload.get('name')):
                self.log('addServer, payload = %s'%(payload))
                servers.update({payload.get('name'):payload})
                DIALOG.notificationDialog('%s: %s'%(LANGUAGE(32047),payload.get('name')))
                if self.setDiscovery(servers):
                    return True


    def delServer(self):
        self.log('delServer')
        def _build(payload):
            return LISTITEMS.buildMenuListItem(payload['name'],'%s - %s'%(payload['host'],{"True":"[COLOR=red]Offline[/COLOR]","False":"[COLOR=red]Offline[/COLOR]"}[str(payload.get('online',False))]),url=dumpJSON(payload))
      
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
        def _build(payload):
            return LISTITEMS.buildMenuListItem(payload['name'],'%s - %s'%(payload['host'],{"True":"[COLOR=red]Offline[/COLOR]","False":"[COLOR=red]Offline[/COLOR]"}[str(payload.get('online',False))]),url=dumpJSON(payload))
      
        with BUILTIN.busy_dialog():
            servers = self.getDiscovery()
            lizlst  = poolit(_build)(list(servers.values()))
            selects = DIALOG.selectDialog(lizlst,LANGUAGE(30130),preselect=[idx for idx, listitem in enumerate(lizlst) if loadJSON(listitem.getPath()).get('enabled',False)])
            if not selects is None:
                for idx, liz in enumerate(lizlst):
                    if idx in selects:
                        if not servers.get(liz.getLabel()).get('enabled',False): DIALOG.notificationDialog(LANGUAGE(30099)%(liz.getLabel()))
                        servers.get(liz.getLabel()).update({'enabled':True})
                    else:
                        if servers.get(liz.getLabel()).get('enabled',False): DIALOG.notificationDialog(LANGUAGE(30100)%(liz.getLabel()))
                        servers.get(liz.getLabel()).update({'enabled':False})
                if self.setDiscovery(servers):
                    return PROPERTIES.setEXTProperty('%s.chkDiscovery'%(ADDON_ID),'true')

            
    def run(self):
        ctl = (7,1) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))
        
        if param == 'Select_Server': 
            ctl = (6,7)
            self.selServer()
        elif param == 'Remove_server': 
            ctl = (6,6)
            self.delServer()
        elif param == 'Pair_Announcement': 
            ctl = (6,7)
            with PROPERTIES.suspendActivity():
                return self.pairAnnouncement(self.getPayload())
        return openAddonSettings(ctl)


if __name__ == '__main__': Multiroom(sys.argv).run()
    