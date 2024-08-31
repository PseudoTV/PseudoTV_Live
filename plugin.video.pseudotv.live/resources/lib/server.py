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
from functools                 import partial
from six.moves.BaseHTTPServer  import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver    import ThreadingMixIn
from socket                    import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, SO_REUSEADDR, SOCK_STREAM
            
#todo proper REST API to handle server/client communication incl. sync/update triggers.
#todo incorporate experimental webserver UI to master branch.

class Discovery:
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def __decodeString(self, base64_bytes):
        message_bytes = base64.b64decode(base64_bytes.encode(DEFAULT_ENCODING))
        return message_bytes.decode(DEFAULT_ENCODING)
    
    
    def _start(self):
        if not PROPERTIES.isRunning('Discovery'):
            with PROPERTIES.setRunning('Discovery'):
                data = ''
                try: 
                    local ='%s:%s'%(getIP(),SETTINGS.getSettingInt('TCP_PORT'))
                    sock  = socket(AF_INET, SOCK_DGRAM) #create UDP socket
                    sock.bind(('', SETTINGS.getSettingInt('UDP_PORT')))
                    sock.settimeout(0.5) # it take 0.5 secs to connect to a port !
                    data, addr = sock.recvfrom(1024) #wait for a packet
                    data = data.decode(DEFAULT_ENCODING)
                except: pass #ignore except TimeoutError: timed out
                if data.startswith(ADDON_ID):
                    response = data[len(ADDON_ID):]
                    if response:
                        self.log('_start: response from %s\n%s'%(addr,response))
                        payload = loadJSON(self.__decodeString(response))
                        host = payload.get('host','')
                        if host != local and 'md5' in payload:
                            self.log('_start: discovered new server @ host = %s'%(host),xbmc.LOGINFO)
                            if payload.pop('md5') == getMD5(dumpJSON(payload)) or payload.pop('received') == local:
                                self.log('_start: discovered new server confirmed! received payload ',xbmc.LOGINFO)
                                return payload 
                else: self.log('_start: waiting for response...')
        return {}
        
                                
class Announcement:
    def __init__(self, payload={}):
        self._start(payload)
            
            
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def __encodeString(self, text):
        base64_bytes = base64.b64encode(text.encode(DEFAULT_ENCODING))
        return base64_bytes.decode(DEFAULT_ENCODING)

        
    def _start(self, payload):
        if not PROPERTIES.isRunning('Announcement'):
            with PROPERTIES.setRunning('Announcement'):
                try:
                    data = '%s%s'%(ADDON_ID,self.__encodeString(dumpJSON(payload)))
                    sock = socket(AF_INET, SOCK_DGRAM) #create UDP socket
                    sock.bind(('', 0))
                    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                    sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1) #this is a broadcast socket
                    sock.settimeout(0.5) # it take 0.5 secs to connect to a port !
                    sock.sendto(data.encode(), ('<broadcast>',SETTINGS.getSettingInt('UDP_PORT')))
                    self.log('_start, sending service announcements: %s\n%s'%(data[len(ADDON_ID):],data.encode()),xbmc.LOGINFO)
                except Exception as e: self.log('_start failed! %s'%(e),xbmc.LOGERROR)


class RequestHandler(BaseHTTPRequestHandler):
    CHUNK_SIZE = 64 * 1024
    
    def __init__(self, request, client_address, server, monitor):
        self.monitor = monitor
        try: BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        except (IOError, OSError) as e: self.log('__init__ failed! %s'%(e),xbmc.LOGERROR)
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _set_headers(self, content='*/*', size=None):
        self.send_response(200, "OK")
        self.send_header("Content-type",content)
        self.send_header("Connection",'close')
        if size:
            self.send_header("Content-Length", len(size))
        self.end_headers()


    def do_HEAD(self):
        return self._set_headers()


    def do_POST(self):
        return self.do_GET()
        
        
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
            content = "text/plain"
            
        if self.path.lower() == '/%s'%(XMLTVFLE.lower()):
            self.log('do_GET, sending = %s'%(path))
            self._set_headers(content)
            CHUNK_SIZE = 64 * 1024
            with FileLock():
                fle = FileAccess.open(path, "r")
                while not self.monitor.abortRequested():
                    chunk = fle.read(CHUNK_SIZE).encode(encoding=DEFAULT_ENCODING)
                    if not chunk or self.monitor.myService._interrupt(.001): break
                    self.wfile.write(chunk)
                fle.close()
                self.wfile.close()
        else:
            fle   = FileAccess.open(path, "r")
            chunk = fle.read().encode(encoding=DEFAULT_ENCODING)
            fle.close()
            self._set_headers(content,chunk)
            self.log('do_GET, sending = %s, size = %s'%(path,len(chunk)))
            self.wfile.write(chunk)
            self.wfile.close()
            
        
class HTTP:
    isRunning = False

    def __init__(self, service=None):
        self.log('__init__')
        self.service = service
        
                    
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
        try:
            if not self.isRunning:
                self.isRunning = True
                IP  = getIP()
                TCP = SETTINGS.getSettingInt('TCP_PORT')
                PORT= self.chkPort(TCP,redirect=True)
                if   PORT is None: raise Exception('Port: %s In-Use!'%(PORT))
                elif PORT != TCP: SETTINGS.setSettingInt('TCP_PORT',PORT)
                LOCAL_HOST ='%s:%s'%(IP,PORT)
                self.log("_start, starting server @ %s"%(LOCAL_HOST),xbmc.LOGINFO)
                SETTINGS.setSetting('Remote_M3U'  ,'http://%s/%s'%(LOCAL_HOST,M3UFLE))
                SETTINGS.setSetting('Remote_XMLTV','http://%s/%s'%(LOCAL_HOST,XMLTVFLE))
                SETTINGS.setSetting('Remote_GENRE','http://%s/%s'%(LOCAL_HOST,GENREFLE))
                
                self._server = ThreadedHTTPServer((IP, PORT), partial(RequestHandler,monitor=self.service.monitor))
                self._server.allow_reuse_address = True
                self._httpd_thread = Thread(target=self._server.serve_forever)
                self._httpd_thread.daemon=True
                self._httpd_thread.start()
            SETTINGS.setSetting('Remote_Status',{'True':'[COLOR=green]Online[/COLOR]','False':'[COLOR=red]Offline[/COLOR]'}[str(self.isRunning)])
        except Exception as e: 
            self.log("_start, Failed! %s"%(e), xbmc.LOGERROR)
        
        
    def _stop(self):
        try:
            if self.isRunning:
                self.log('_stop, shutting server down',xbmc.LOGINFO)
                self._server.shutdown()
                self._server.server_close()
                self._server.socket.close()
                if self._httpd_thread.is_alive():
                    self._httpd_thread.join(5)
        except Exception as e: self.log("_stop, Failed! %s"%(e), xbmc.LOGERROR)
        self.isRunning = False


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

