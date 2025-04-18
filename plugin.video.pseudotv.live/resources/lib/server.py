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
import gzip, mimetypes, socket, time

from zeroconf                  import *
from globals                   import *
from functools                 import partial
from six.moves.BaseHTTPServer  import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver    import ThreadingMixIn
            
#todo proper REST API to handle server/client communication incl. sync/update triggers.
#todo incorporate experimental webserver UI to master branch.

ZEROCONF_SERVICE = "_xbmc-jsonrpc-h._tcp.local."

class Discovery:
    class MyListener(object):
        def __init__(self, multiroom=None):
            self.zServers  = dict()
            self.zeroconf  = Zeroconf()
            self.multiroom = multiroom

        def log(self, msg, level=xbmc.LOGDEBUG):
            return log('%s: %s'%(self.__class__.__name__,msg),level)

        def removeService(self, zeroconf, type, name):
            self.log("getService, type = %s, name = %s"%(type,name))
             
        def addService(self, zeroconf, type, name):
            info = self.zeroconf.getServiceInfo(type, name)
            if info:
                IP = socket.inet_ntoa(info.getAddress())
                if IP != SETTINGS.getIP():
                    server = info.getServer()
                    self.zServers[server] = {'type':type,'name':name,'server':server,'host':'%s:%d'%(IP,info.getPort()),'bonjour':'http://%s:%s/%s'%(IP,SETTINGS.getSettingInt('TCP_PORT'),BONJOURFLE)}
                    self.log("addService, found zeroconf %s @ %s using using bonjour %s"%(server,self.zServers[server]['host'],self.zServers[server]['bonjour']))
                    self.multiroom.addServer(requestURL(self.zServers[server]['bonjour'],json_data=True))
            
            
    def __init__(self, service=None, multiroom=None):
        self.service   = service
        self.multiroom = multiroom
        self._start()
                   

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _start(self):
        if not PROPERTIES.isRunning('Discovery'):
            with PROPERTIES.chkRunning('Discovery'):
                zconf = Zeroconf()
                zcons = self.multiroom._getStatus()
                self.log("_start, Multicast DNS Service Discovery (%s)"%(ZEROCONF_SERVICE))
                SETTINGS.setSetting('ZeroConf_Status','[COLOR=yellow][B]%s[/B][/COLOR]'%(LANGUAGE(32252)))
                ServiceBrowser(zconf, ZEROCONF_SERVICE, self.MyListener(multiroom=self.multiroom))
                self.service.monitor.waitForAbort(DISCOVER_INTERVAL)
                SETTINGS.setSetting('ZeroConf_Status',LANGUAGE(32211)%({True:'green',False:'red'}[zcons],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[zcons]))
                zconf.close()
                        
            
class RequestHandler(BaseHTTPRequestHandler):
    
    def __init__(self, request, client_address, server, monitor):
        self.monitor = monitor
        self.cache   = SETTINGS.cache
        try: BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        except: pass
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _set_headers(self, content='*/*', size=None, gzip=False):
        self.send_response(200, "OK")
        self.send_header("Content-type",content)
        if size: self.send_header("Content-Length", len(size))
        if gzip: self.send_header("Content-Encoding", "gzip")
        self.end_headers()


    def _gzip_encode(self, content):
        out = BytesIO()
        f = gzip.GzipFile(fileobj=out, mode='w', compresslevel=5)
        f.write(content)
        f.close()
        return out.getvalue()


    def do_HEAD(self):
        return self._set_headers()


    def do_POST(self):
        def _verifyUUID(uuid):
            if uuid == SETTINGS.getMYUUID(): return True
            else:
                from multiroom  import Multiroom
                for server in list(Multiroom().getDiscovery().values()):
                    if server.get('uuid') == uuid: return True
            
        self.log('do_POST, incoming path = %s'%(self.path))
        if not PROPERTIES.isRunning('do_POST'):
            with PROPERTIES.chkRunning('do_POST'), PROPERTIES.interruptActivity():
                if self.path.lower().endswith('.json'):
                    try:    incoming = loadJSON(self.rfile.read(int(self.headers['content-length'])).decode())
                    except: incoming = {}
                    if _verifyUUID(incoming.get('uuid')):
                        self.log('do_POST incoming uuid [%s] verified!'%(incoming.get('uuid')))
                        #channels - channel manager save
                        if self.path.lower() == '/%s'%(CHANNELFLE.lower()) and incoming.get('payload'):
                            from channels import Channels
                            if Channels().setChannels(list(Channels()._verify(incoming.get('payload')))):
                                DIALOG.notificationDialog(LANGUAGE(30085)%(LANGUAGE(30108),incoming.get('name',ADDON_NAME)))
                            return self.send_response(200, "OK")
                        #filelist w/resume - paused channel rule
                        elif self.path.lower().startswith('/filelist') and incoming.get('payload'):
                            if setJSON(os.path.join(TEMP_LOC,self.path.replace('/filelist/','')),incoming.get('payload')):
                                DIALOG.notificationDialog(LANGUAGE(30085)%(LANGUAGE(30060),incoming.get('name',ADDON_NAME)))
                            return self.send_response(200, "OK")
                        else: self.send_error(401, "Path Not found")
                    else: return self.send_error(401, "UUID Not verified!")
                else: return self.do_GET()
        
        
    def do_GET(self):
        def _sendChunk(path, content, chunk):
            self.log('do_GET, outgoing path = %s, content = %s'%(path, content))
            self._set_headers(content,chunk)
            self.log('do_GET, sending chunk, size = %s'%(len(chunk)))
            self.wfile.write(chunk)
            self.wfile.close()

        def _sendChunks(path, content):
            self._set_headers(content)
            self.log('do_GET, outgoing path = %s, content = %s'%(path, content))
            while not self.monitor.abortRequested():
                chunk = fle.read(64 * 1024).encode(encoding=DEFAULT_ENCODING)
                if not chunk or self.monitor.waitForAbort(0.001): break
                self.send_header('content-length', len(chunk))
                self.log('do_GET, sending = %s, chunk = %s'%(path, chunk))
                self.wfile.write(chunk)
            self.wfile.close()

        def _sendFile(path, content):
            self.log('do_GET, outgoing path = %s, content = %s'%(path, content))
            with xbmcvfs.File(path, "r") as fle:
                chunk = fle.read().encode(encoding=DEFAULT_ENCODING)
                self._set_headers(content,chunk)
                self.log('do_GET, sending = %s, size = %s'%(path,len(chunk)))
                self.wfile.write(chunk)
            self.wfile.close()

        def _sendZip(path, content):
            self.log('do_GET, outgoing path = %s, content = %s'%(path, content))
            with xbmcvfs.File(path, "r") as fle:
                if 'gzip' in self.headers.get('accept-encoding'):
                    data = self._gzip_encode(fle.read().encode(encoding=DEFAULT_ENCODING))
                    self._set_headers(content,data,True)
                    self.log('do_GET, sending = %s, gzip compressing'%(path))
                    self.wfile.write(data)
                    self.wfile.close()
                else: self._sendChunks(path, content)

        def _sendImage(path, content):
            self.log('do_GET, outgoing path = %s, content = %s'%(path, content))
            with xbmcvfs.File(path, "r") as fle:
                chunk = fle.readBytes()
                self._set_headers(content,chunk)
                self.log('do_GET, sending = %s, size = %s'%(path,len(chunk)))
                self.wfile.write(chunk)
            self.wfile.close()

        self.log('do_GET, incoming path = %s'%(self.path))
        if not PROPERTIES.isRunning('do_GET'):
            with PROPERTIES.chkRunning('do_GET'), PROPERTIES.interruptActivity():
                #Bonjour json/html
                if self.path.lower() == '/%s'%(BONJOURFLE.lower()):
                    chunk = dumpJSON(SETTINGS.getBonjour(inclChannels=True),idnt=4).encode(encoding=DEFAULT_ENCODING)
                    _sendChunk(self.path.lower(), "application/json", chunk)
                #Remotes Json/jtml
                elif self.path.lower().startswith('/remote'):
                    if self.path.lower().endswith('.json'):
                        _sendChunk(self.path.lower(), "application/json", dumpJSON(SETTINGS.getPayload(),idnt=4).encode(encoding=DEFAULT_ENCODING))
                    elif self.path.lower().endswith('.html'):
                        _sendChunk(self.path.lower(), "text/html", SETTINGS.getPayloadUI().encode(encoding=DEFAULT_ENCODING))
                    else: self.send_error(404, "Path Not found")
                #filelist - Paused Channels
                elif self.path.lower().startswith('/filelist') and self.path.lower().endswith('.json'):
                    _sendChunk(self.path.lower(), "application/json", dumpJSON(getJSON((os.path.join(TEMP_LOC,self.path.replace('/filelist/',''))))).encode(encoding=DEFAULT_ENCODING))
                #M3U - MPEG
                elif self.path.lower() == '/%s'%(M3UFLE.lower()):
                    _sendFile(M3UFLEPATH, "application/vnd.apple.mpegurl")
                #Genres - XML
                elif self.path.lower() == '/%s'%(GENREFLE.lower()):
                    _sendFile(GENREFLEPATH, "text/plain")
                #XMLTV - XML (Large)
                elif self.path.lower() == '/%s'%(XMLTVFLE.lower()):
                    _sendZip(XMLTVFLEPATH, "text/xml")
                #Images - image server
                elif self.path.lower().startswith("/images/"):
                    _sendImage(os.path.join(LOGO_LOC,unquoteString(self.path.replace('/images/',''))), mimetypes.guess_type(self.path[1:])[0])
                else: self.send_error(404, "Path Not found")
        
class HTTP:
    isRunning = False

    def __init__(self, service=None):
        self.log('__init__')
        self.service = service
        timerit(self._start)(0.1)
        
                    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def chkPort(self, port=0, redirect=False):
        try:
            state = False
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                s.bind(("127.0.0.1", port))
                state = True
        except Exception as e:
            self.log("chkPort, port = %s, failed! = %s"%(port,e))
            if redirect:
                try:
                    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                        s.bind(("127.0.0.1", 0))
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        port  = s.getsockname()[1]
                        state = True
                except Exception as e: self.log("chkPort, port = %s, failed! = %s"%(port,e))
            else: port = None
        self.log("chkPort, port = %s, available = %s"%(port,state))
        return port


    def _start(self):
        if self.service.monitor.waitForAbort(0.001): self._stop()
        elif not self.isRunning:
            try:
                IP  = SETTINGS.getIP()
                TCP = SETTINGS.getSettingInt('TCP_PORT')
                PORT= self.chkPort(TCP,redirect=True)
                if   PORT is None: raise Exception('Port: %s In-Use!'%(PORT))
                elif PORT != TCP: SETTINGS.setSettingInt('TCP_PORT',PORT)
                LOCAL_HOST = PROPERTIES.setRemoteHost('%s:%s'%(IP,PORT))
                self.log("_start, starting server @ %s"%(LOCAL_HOST),xbmc.LOGINFO)
                
                SETTINGS.setSetting('Remote_NAME' ,SETTINGS.getFriendlyName())
                SETTINGS.setSetting('Remote_M3U'  ,'http://%s/%s'%(LOCAL_HOST,M3UFLE))
                SETTINGS.setSetting('Remote_XMLTV','http://%s/%s'%(LOCAL_HOST,XMLTVFLE))
                SETTINGS.setSetting('Remote_GENRE','http://%s/%s'%(LOCAL_HOST,GENREFLE))
                
                self.isRunning = True
                self._server = ThreadedHTTPServer((IP, PORT), partial(RequestHandler,monitor=self.service.monitor))
                self._server.allow_reuse_address = True
                self._httpd_thread = Thread(target=self._server.serve_forever)
                self._httpd_thread.daemon=True
                self._httpd_thread.start()
            except Exception as e: self.log("_start, Failed! %s"%(e), xbmc.LOGERROR)
        DIALOG.notificationDialog('%s: %s'%(SETTINGS.getSetting('Remote_NAME'),LANGUAGE(32211)%({True:'green',False:'red'}[self.isRunning],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[self.isRunning])))
        SETTINGS.setSetting('Remote_Status',LANGUAGE(32211)%({True:'green',False:'red'}[self.isRunning],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[self.isRunning]))
        
        
    def _stop(self):
        try:
            if self.isRunning:
                self.log('_stop, shutting server down',xbmc.LOGINFO)
                self._server.shutdown()
                self._server.server_close()
                self._server.socket.close()
                if self._httpd_thread.is_alive():
                    try: self._httpd_thread.join(5)
                    except: pass
        except Exception as e: self.log("_stop, Failed! %s"%(e), xbmc.LOGERROR)
        self.isRunning = False


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

