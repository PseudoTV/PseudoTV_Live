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
from six.moves.BaseHTTPServer  import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver    import ThreadingMixIn
from socket                    import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, SO_REUSEADDR, SOCK_STREAM

HOST       = '0.0.0.0'
IP         = getIP()
CHUNK_SIZE = 64 * 1024

def chkPort(port=0, redirect=False):
    return port
    # try: #todo check port if unused and redirect allowed substitute?
        # with closing(socket(AF_INET, SOCK_STREAM)) as s:
            # s.bind(('127.0.0.1', port))
            # s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            # return s.getsockname()[1]
    # except Exception as e: 
        # log("chkPort, Failed! %s"%(e), xbmc.LOGERROR)
        
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
        sock = socket(AF_INET, SOCK_DGRAM) #create UDP socket
        sock.bind(('', UDP_PORT))
        sock.settimeout(0.5) # it take 0.5 secs to connect to a port !
        
        while not self.monitor.abortRequested():
            try:    
                data, addr = sock.recvfrom(1024) #wait for a packet
                if data.startswith(ADDON_ID.encode()):
                    response = data[len(ADDON_ID):]
                    if response and (getDiscovery() != response.decode()): 
                        self.log('_start, got service announcement from %s'%(response.decode()))
                        setDiscovery(response.decode())
            except: pass
                
            if (self.monitor.waitForAbort(1) or self.shutdown):
                break


class Announcement:
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
        data = '%s%s:%s'%(ADDON_ID,IP,TCP_PORT)
        sock = socket(AF_INET, SOCK_DGRAM) #create UDP socket
        sock.bind(('', 0))
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1) #this is a broadcast socket
        sock.settimeout(0.5) # it take 0.5 secs to connect to a port !
        self.log('_start, sending service announcement: %s'%(data[len(ADDON_ID):]))
        
        while not self.monitor.abortRequested():
            if not isClient():
                try:    sock.sendto(data.encode(), ('<broadcast>',UDP_PORT))
                except: pass
        
            if (self.monitor.waitForAbort(5) or self.shutdown):
                break

            
class RequestHandler(BaseHTTPRequestHandler):
    monitor = xbmc.Monitor()
    
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
        with xbmcvfs.File(path, 'rb') as f:
            while not self.monitor.abortRequested():
                chunk = f.read(CHUNK_SIZE).encode()
                if not chunk: break
                self.wfile.write(chunk)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class HTTP:
    started = False
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _stop(self):
        if not self.started: return
        try:
            self._server.shutdown()
            self._server.server_close()
            self._server.socket.close()
            self._httpd_thread.join()
            self.started = False
            self.log('_start, stopped!')
        except: pass
        
        
    def _start(self):
        try:
            #todo check port
            if (self.started or isClient()): return
            self.log("_start, %s:%s"%(IP, TCP_PORT))
            self._server = ThreadedHTTPServer((IP, TCP_PORT), RequestHandler)
            self._server.allow_reuse_address = True
            self._httpd_thread = threading.Thread(target=self._server.serve_forever)
            self._httpd_thread.start()
            self.started = True
        except Exception as e: 
            self.log("_start, Failed! %s"%(e), xbmc.LOGERROR)