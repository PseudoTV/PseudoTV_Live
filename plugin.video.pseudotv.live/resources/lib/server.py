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
from globals                   import *
from threading                 import Thread
from functools                 import partial
from six.moves.BaseHTTPServer  import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver    import ThreadingMixIn
from socket                    import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, SO_REUSEADDR, SOCK_STREAM
            
#todo proper REST API to handle server/client communication incl. sync/update triggers.
#todo incorporate experimental webserver UI to master branch.

class Discovery:
    isRunning = False
    
    def __init__(self, monitor):
        self.log('__init__')
        self.monitor = monitor
        self.startThread = Thread(target=self._start)
        self.startThread.daemon = True
        self.startThread.start()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _start(self):
        IP  = getIP()
        TCP = SETTINGS.getSettingInt('TCP_PORT')
        UDP = SETTINGS.getSettingInt('UDP_PORT')
        
        self.isRunning = True
        data  = ''
        local ='%s:%s'%(IP,TCP)
        sock  = socket(AF_INET, SOCK_DGRAM) #create UDP socket
        sock.bind(('', UDP))
        sock.settimeout(0.5) # it take 0.5 secs to connect to a port !
        
        while not self.monitor.abortRequested():
            if self.monitor.myService._interrupt(1): break
            elif not isClient(): break
            else:
                try: 
                    data, addr = sock.recvfrom(1024) #wait for a packet
                except: pass #ignore except TimeoutError: timed out
                print(data)
                if data.startswith(ADDON_ID):
                    response = data[len(ADDON_ID):]
                    if response:
                        self.log('_start: response = %s'%(response))
                        payload = loadJSON(decodeString(response.decode()))
                        host = payload.get('host','')
                        if host != local and 'md5' in payload:
                            self.log('_start: discovered server @ host = %s'%(host),xbmc.LOGINFO)
                            if payload.pop('md5') == getMD5(dumpJSON(payload)):
                                payload['received'] = time.time()
                                servers = getDiscovery()
                                if host not in servers and SETTINGS.getSettingInt('Client_Mode') == 1:
                                    DIALOG.notificationWait('%s - %s'%(LANGUAGE(32047),payload.get('name',host)))
                                servers[host] = payload
                                setDiscovery(servers)
                                SETTINGS.chkDiscovery(servers)
        self.isRunning = False


class Announcement:
    isRunning = False
    
    def __init__(self, monitor):
        self.log('__init__')
        self.monitor = monitor
        self.startThread = Thread(target=self._start)
        self.startThread.daemon = True
        self.startThread.start()
        
            
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def getSettings(self):
        return {'Resource_Logos'      :SETTINGS.getSetting('Resource_Logos'),
                'Resource_Ratings'    :SETTINGS.getSetting('Resource_Ratings'),
                'Resource_Bumpers'    :SETTINGS.getSetting('Resource_Bumpers'),
                'Resource_Commericals':SETTINGS.getSetting('Resource_Commericals'),
                'Resource_Trailers'   :SETTINGS.getSetting('Resource_Trailers')}


    def _start(self):
        IP  = getIP()
        TCP = SETTINGS.getSettingInt('TCP_PORT')
        UDP = SETTINGS.getSettingInt('UDP_PORT')
        
        payload = {'id'      :ADDON_ID,
                   'version' :ADDON_VERSION,
                   'name'    : BUILTIN.getInfoLabel('FriendlyName','System'),
                   'host'    :'%s:%s'%(IP,TCP),
                   'settings':self.getSettings()}
        payload['md5'] = getMD5(dumpJSON(payload))
        encodedPayload = encodeString(dumpJSON(payload))
        
        self.isRunning = True
        while not self.monitor.abortRequested():
            if self.monitor.myService._interrupt(15): break
            elif isClient(): break
            else:
                data = '%s%s'%(ADDON_ID,encodedPayload)
                sock = socket(AF_INET, SOCK_DGRAM) #create UDP socket
                sock.bind(('', 0))
                sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1) #this is a broadcast socket
                sock.settimeout(0.5) # it take 0.5 secs to connect to a port !
                self.log('_start, sending service announcements: %s'%(data[len(ADDON_ID):]),xbmc.LOGINFO)
                try:   sock.sendto(data.encode(), ('<broadcast>',UDP))
                except Exception as e: self.log('_start failed! %s'%(e),xbmc.LOGERROR)
        self.isRunning = False


class RequestHandler(BaseHTTPRequestHandler):
    CHUNK_SIZE = 64 * 1024
    
    def __init__(self, request, client_address, server, monitor):
        self.monitor = monitor
        try: BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        except (IOError, OSError) as e: pass
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

        
    def do_GET(self):
        self.log('do_GET, path = %s'%(self.path))
        if self.path.lower() == '/%s'%(M3UFLE.lower()):
            path    = M3UFLEPATH
            content = "application/vnd.apple.mpegurl"
        elif self.path.lower() == '/%s'%(XMLTVFLE.lower()):
            path    = XMLTVFLEPATH
            content = "text/xml"
        elif self.path.lower() == '/%s'%(GENREFLE.lower()):
            path    = GENREFLEPATH
            content = "text/xml"
        else: return
            
        self.send_response(200)
        self.send_header("Content-type",content)
        self.end_headers()
        
        self.log('do_GET, sending = %s'%(path))
        with FileLock():
            fle = FileAccess.open(path, "r")
            while not self.monitor.abortRequested():
                chunk = fle.read(self.CHUNK_SIZE).encode(encoding=DEFAULT_ENCODING)
                if not chunk or self.monitor.myService._interrupt(.001): break
                self.wfile.write(chunk)
            fle.close()
            
    def do_HEAD(self):
        return
        
        
    def do_POST(self):
        return self.do_GET()
        
        
class HTTP:
    isRunning = False

    def __init__(self, monitor=None):
        self.log('__init__')
        self.monitor = monitor
        self.startThread = Thread(target=self._start)
        self.startThread.daemon = True
        self.startThread.start()
        
                    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def chkPort(self, port=0, redirect=False):
        try:
            state = False
            with closing(socket(AF_INET, SOCK_STREAM)) as s:
                s.bind(("127.0.0.1", port))
                state = True
        except Exception as e:
            if redirect and (e.errno == errno.EADDRINUSE):
                with closing(socket(AF_INET, SOCK_STREAM)) as s:
                    s.bind(("127.0.0.1", 0))
                    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                    port  = s.getsockname()[1]
                    state = True
            else: port = None
        self.log("chkPort, port = %s, available = %s"%(port,state))
        return port


    def _start(self):
        while not self.monitor.abortRequested():
            if self.monitor.myService._interrupt(5): break
            elif isClient(): break
            elif self.isRunning: continue
            else:
                try:
                    self.isRunning = True
                    IP  = getIP()
                    TCP = SETTINGS.getSettingInt('TCP_PORT')
                    PORT= self.chkPort(TCP,redirect=True)
                    if PORT is None: raise Exception('Port: %s In-Use!'%(PORT))
                    elif PORT != TCP: SETTINGS.setSettingInt('TCP_PORT',PORT)
                    LOCAL_HOST ='%s:%s'%(IP,PORT)
                    self.log("_start, starting server @ %s"%(LOCAL_HOST),xbmc.LOGINFO)
                    PROPERTIES.setEXTProperty('%s.LOCAL_HOST'%(ADDON_ID),LOCAL_HOST)
                    SETTINGS.setSetting('Remote_URL'  ,'http://%s'%(LOCAL_HOST))
                    SETTINGS.setSetting('Remote_M3U'  ,'http://%s/%s'%(LOCAL_HOST,M3UFLE))
                    SETTINGS.setSetting('Remote_XMLTV','http://%s/%s'%(LOCAL_HOST,XMLTVFLE))
                    SETTINGS.setSetting('Remote_GENRE','http://%s/%s'%(LOCAL_HOST,GENREFLE))
                    
                    self._server = ThreadedHTTPServer((IP, PORT), partial(RequestHandler,monitor=self.monitor))
                    self._server.allow_reuse_address = True
                    self._httpd_thread = Thread(target=self._server.serve_forever)
                    self._httpd_thread.daemon = True
                    self._httpd_thread.start()
                except Exception as e: 
                    self.log("_start, Failed! %s"%(e), xbmc.LOGERROR)
                    break
        self._stop()
        
        
    def _stop(self):
        try:
            if self.isRunning:
                self.log('_stop, shutting server down',xbmc.LOGINFO)
                self._server.shutdown()
                self._server.server_close()
                self._server.socket.close()
                if self._httpd_thread.is_alive():
                    self._httpd_thread.join(5.5)
        except Exception as e: self.log("_stop, Failed! %s"%(e), xbmc.LOGERROR)
        self.isRunning = False


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

