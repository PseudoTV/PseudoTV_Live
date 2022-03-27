#   Copyright (C) 2022 Lunatixz
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

# -*- coding: utf-8 -*-
from resources.lib.globals     import *
from resources.lib.fileaccess  import FileLock
from six.moves.BaseHTTPServer  import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver    import ThreadingMixIn
from socket                    import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, SO_REUSEADDR, SOCK_STREAM

IP         = getIP()
HOST       = '0.0.0.0'
CHUNK_SIZE = 64 * 1024

def chkPort(port=0, redirect=False):
    try:
        with closing(socket(AF_INET, SOCK_STREAM)) as s:
            s.bind(("127.0.0.1", port))
            return port
    except socket.error as e:
        if redirect and (e.errno == errno.EADDRINUSE):
            with closing(socket(AF_INET, SOCK_STREAM)) as s:
                s.bind(("127.  0.0.1", 0))
                s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                port = s.getsockname()[1]
                log("server: chkPort, Port is already in-use: changing to %s"%(port))
        else: log("server: chkPort, Failed! %s"%(e), xbmc.LOGERROR)
        return port
        
def getSettings():
    return {'Resource_Logos'      :SETTINGS.getSetting('Resource_Logos'),
            'Resource_Ratings'    :SETTINGS.getSetting('Resource_Ratings'),
            'Resource_Bumpers'    :SETTINGS.getSetting('Resource_Bumpers'),
            'Resource_Commericals':SETTINGS.getSetting('Resource_Commericals'),
            'Resource_Trailers'   :SETTINGS.getSetting('Resource_Trailers')}

class Discovery:
    shutdown = False
    
    def __init__(self, monitor=None):
        if monitor is None:
            self.monitor = xbmc.Monitor()
        else:
            self.monitor = monitor
            
        self.startThread = threading.Thread(target=self._start)
        self.startThread.daemon = True
        self.startThread.start()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _stop(self):
        self.log('_stop')
        self.shutdown = True


    def _start(self):
        self.log('_start')
        local ='%s:%s'%(IP,SETTINGS.getSettingInt('TCP_PORT'))
        sock  = socket(AF_INET, SOCK_DGRAM) #create UDP socket
        sock.bind(('', SETTINGS.getSettingInt('UDP_PORT')))
        sock.settimeout(0.5) # it take 0.5 secs to connect to a port !
        
        while not self.monitor.abortRequested():
            if isClient():
                try:
                    data, addr = sock.recvfrom(1024) #wait for a packet
                    if data.startswith(ADDON_ID.encode()):
                        response = data[len(ADDON_ID):]
                        if response:
                            payload = loadJSON(decodeString(response.decode()))
                            host = payload.get('host','')
                            if host != local:
                                self.log('_start: discovered server @ host = %s'%(host))
                                md5 = payload['md5']
                                payload.update({'md5':'-1'})
                                if md5 == getMD5(dumpJSON(payload)):
                                    payload['received'] = time.time()
                                    servers = getDiscovery()
                                    if host not in servers:
                                        Dialog().notificationDialog('%s - %s'%(LANGUAGE(30207),payload.get('name',host)))
                                    servers[host] = payload
                                    setDiscovery(servers)
                                    chkDiscovery(servers)
                except: pass
                
            if (self.monitor.waitForAbort(1) or self.shutdown or self.monitor.shutdown):
                self.log('_start, shutting down')
                self.shutdown = False
                break


class Announcement:
    shutdown = False
    settings = getSettings()
    
    def __init__(self, monitor=None):
        if monitor is None:
            self.monitor = xbmc.Monitor()
        else:
            self.monitor = monitor
           
        self.startThread = threading.Thread(target=self._start)
        self.startThread.daemon = True
        self.startThread.start()
        
            
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def _stop(self):
        self.log('_stop')
        self.shutdown = True
        
        
    def _start(self):
        self.log('_start')
        payload = {'md5':'-1',
                   'id':ADDON_ID,
                   'version':ADDON_VERSION,
                   'name':xbmc.getInfoLabel('System.FriendlyName'),
                   'host':'%s:%s'%(IP,SETTINGS.getSettingInt('TCP_PORT')),
                   'settings':self.settings}
                   
        payload.update({'md5':getMD5(dumpJSON(payload))})
        data = '%s%s'%(ADDON_ID,encodeString(dumpJSON(payload)))
        sock = socket(AF_INET, SOCK_DGRAM) #create UDP socket
        sock.bind(('', 0))
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1) #this is a broadcast socket
        sock.settimeout(0.5) # it take 0.5 secs to connect to a port !
        self.log('_start, sending service announcements: %s'%(data[len(ADDON_ID):]))
        
        while not self.monitor.abortRequested():
            if not isClient():
                try:    sock.sendto(data.encode(), ('<broadcast>',SETTINGS.getSettingInt('UDP_PORT')))
                except: pass
        
            if (self.monitor.waitForAbort(5) or self.shutdown or self.monitor.shutdown):
                self.log('_start, shutting down')
                self.shutdown = False
                break

            
class RequestHandler(BaseHTTPRequestHandler):
    monitor = xbmc.Monitor()
    globalFileLock = FileLock()
    
    def __init__(self, request, client_address, server):
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
        self.send_header("Content-type", content)
        self.end_headers()
        
        self.log('do_GET, sending = %s'%(path))
        with busy(), xbmcvfs.File(path, 'rb') as f:#, fileLocker(self.globalFileLock)
            while not self.monitor.abortRequested():
                chunk = f.read(CHUNK_SIZE).encode(encoding=DEFAULT_ENCODING)
                if not chunk: break
                self.wfile.write(chunk)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class HTTP:
    started  = False
    restart  = False
    shutdown = False
    
    def __init__(self, monitor=None):
        if monitor is None:
            self.monitor = xbmc.Monitor()
        else:
            self.monitor = monitor
        self._start()
        
            
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _restart(self):
        self.log('_restart')
        self.restart = True
        

    def _stop(self):
        self.log('_stop')
        self.shutdown = True
        
        
    def _start(self):
        port = SETTINGS.getSettingInt('TCP_PORT')
        while not self.monitor.abortRequested():
            try:
                client   = isClient()
                TCP_PORT = SETTINGS.getSettingInt('TCP_PORT')
                if self.started: 
                    if    client: break
                    elif  port != TCP_PORT:
                        self._restart()
                        break
                    else: return
                elif client: return
                    
                port = chkPort(TCP_PORT,redirect=True)
                if port is None:
                    raise Exception('Port In-Use!')
                elif port != TCP_PORT:
                    SETTINGS.setSettingInt('TCP_PORT',port)
                    
                LOCAL_HOST ='%s:%s'%(IP,port)
                self.log("_start, %s"%(LOCAL_HOST))
                PROPERTIES.setProperty('LOCAL_HOST',LOCAL_HOST)
                
                self._server = ThreadedHTTPServer((IP, port), RequestHandler)
                self._server.allow_reuse_address = True
                self._httpd_thread = threading.Thread(target=self._server.serve_forever)
                self._httpd_thread.start()
                self.started = True
            except Exception as e: 
                self.log("_start, Failed! %s"%(e), xbmc.LOGERROR)
                
            if (self.monitor.waitForAbort(15) or self.shutdown or self.monitor.shutdown):
                self.shutdown = False
                self.log('_start, shutting down')
                break
        try:
            if self.started:
                self._server.shutdown()
                self._server.server_close()
                self._server.socket.close()
                self._httpd_thread.join()
                self.started = False
        except: pass
            
        if self.restart:
            self.restart = False
            self._start()