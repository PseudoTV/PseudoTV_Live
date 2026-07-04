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
import gzip, mimetypes, socket, errno

from zeroconf                  import *
from variables                 import *
from channels                  import Channels
from library                   import Library
from resources                 import Resources
from six.moves.BaseHTTPServer  import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver    import ThreadingMixIn
#todo proper REST API to handle server/client communication incl. sync/update triggers.
#todo incorporate experimental webserver UI to master branch.

ZEROCONF_SERVICE      = "_xbmc-jsonrpc-h._tcp.local."
COMPRESSION_THRESHOLD = 1024  # 1 KB
CHUNK_SIZE            = 4096 #4 KB

class Discovery(Thread):
    class MyListener(object):
        def __init__(self, multiroom=None):
            self.zServers  = {}
            self.zeroconf  = Zeroconf()
            self.multiroom = multiroom
            self.jsonRPC   = multiroom.jsonRPC

        def log(self, msg, level=xbmc.LOGDEBUG):
            return Globals._log(f"{self.__class__.__name__}: {msg}", level)

        def removeService(self, zeroconf, type, name):
            self.log("removeService, type = %s, name = %s"%(type,name))
             
        def addService(self, zeroconf, type, name):
            INFO = self.zeroconf.getServiceInfo(type, name)
            if INFO:
                server  = INFO.getServer()
                address = INFO.getAddress()
                if not isinstance(address, bytes):
                    address = bytes(address)
                ip = socket.inet_ntop(socket.AF_INET, address)
                self.zServers[server] = {'type':type,'name':name,'server':server,'host':'%s:%d'%(ip,INFO.getPort()),'bonjour':'http://%s:%s/api/%s'%(ip,Globals.SETTINGS.getSettingInt('TCP_PORT'),BONJOURFLE)}
                self.log("addService, found zeroconf %s @ %s using bonjour %s"%(server,self.zServers[server]['host'],self.zServers[server]['bonjour']))
                self.multiroom.addServer(self.jsonRPC.requestURL(self.zServers[server]['bonjour']))
            
    def __init__(self, service=None, multiroom=None):
        Thread.__init__(self)
        self.daemon    = True
        self.service   = service
        self.monitor   = service.monitor
        self.multiroom = multiroom
        self.start()

    def log(self, msg, level=xbmc.LOGDEBUG):
        return Globals._log(f"{self.__class__.__name__}: {msg}", level)

    def run(self):
        if not Globals.PROPERTIES.isRunning('Discovery.run'):
            with Globals.PROPERTIES.chkRunning('Discovery.run'):
                while not self.monitor.abortRequested():
                    try: 
                        zcons = self.multiroom._getStatus()
                        self.log("run, starting ZEROCONF ENABLED (%s)"%(zcons))
                        if zcons:
                            zconf = Zeroconf()
                            self.log("run, Multicast DNS Service waiting for (%s)"%(ZEROCONF_SERVICE))
                            ServiceBrowser(zconf, ZEROCONF_SERVICE, self.MyListener(multiroom=self.multiroom))
                            Globals.SETTINGS.setSetting('ZeroConf_Status','[COLOR=yellow][B]%s[/B][/COLOR]'%(LANGUAGE(32252)))
                            if self.service._sleep(DISCOVER_INTERVAL): break
                            self.log("run, Multicast DNS Service stopping search for (%s)"%(ZEROCONF_SERVICE))
                            zconf.close()
                        Globals.SETTINGS.setSetting('ZeroConf_Status',LANGUAGE(32211)%({True:'green',False:'red'}[zcons],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[zcons]))
                    except Exception as e:
                        self.log("run, Multicast DNS Service failed! %s"%(e), xbmc.LOGERROR)
                        break
                    if self.service._sleep(600):
                        self.log("run, _sleep", xbmc.LOGERROR)
                        break
                self.log("run, shutting down...")


class MyHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server, service):
        self.service   = service
        self.monitor   = service.monitor
        self.resources = Resources(service)
        
        try: BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        except Exception: pass


    def log(self, msg, level=xbmc.LOGDEBUG):
        return Globals._log(f"{self.__class__.__name__}: {msg}", level)


    def do_HEAD(self):
        self.log('do_HEAD, incoming path = %s'%(self.path))
        self.send_response(200, "OK")
        self.send_header("Content-type", "*/*")
        self.end_headers()
        
        
    def do_POST(self):
        self.log('do_POST, incoming path = %s'%(self.path))
        def __verifyUUID(uuid):#lazy security check
            if uuid == Globals.SETTINGS.getMYUUID(): return True
            else:
                from multiroom  import Multiroom
                for server in list(Multiroom().getServers().values()):
                    if server.get('uuid') == uuid:
                        return True

        try:              incoming = FileAccess.loadJSON(self.rfile.read(int(self.headers['content-length'])).decode())
        except Exception: incoming = {}
        
        if __verifyUUID(incoming.get('uuid')) and incoming.get('payload'):
            self.log('do_POST incoming uuid [%s] verified!'%(incoming.get('uuid')))
            if self.path.startswith('/api/'):
                if self.path == f'/api/{CHANNELFLE}':
                    channels = Channels(writable=True)
                    if channels.setChannels(list(channels._verify(incoming.get('payload')))):
                        Globals.DIALOG.notificationDialog(LANGUAGE(30085)%(LANGUAGE(30108),incoming.get('name',ADDON_NAME)))
                    del channels
                    self.send_response(200, "OK")
            elif self.path.startswith('/filelist/'):
                #filelist w/resume - paused channel rule
                if Globals.SETTINGS.setCacheSetting(self.path.replace('/filelist/',''), incoming.get('payload'), FileAccess._getMD5(self.path.replace('/filelist/','')), datetime.timedelta(days=84)):
                    Globals.DIALOG.notificationDialog(LANGUAGE(30085)%(LANGUAGE(30060),incoming.get('name',ADDON_NAME)))
                    self.send_response(200, "OK")
            else: return self.do_GET()
                    
    
    def do_GET(self):
        self.log('do_GET, incoming path = %s' % (self.path))
        def __sendChunk(path, chunk, compress=False):
            if compress:
                chunk = gzip.compress(chunk, compresslevel=5)
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", len(chunk))
            
            # Determine Content-Type - force content types to support IPTV-Simple, else guess.
            if   path.endswith('.json'): content_type = "application/json"
            elif path.endswith('.m3u'):  content_type = "application/vnd.apple.mpegurl"
            elif path.endswith('.xml'):  content_type = "text/plain"
            elif path.endswith('.html'): content_type = "text/html"
            else:                        content_type = mimetypes.guess_type(path[1:])[0]
            if content_type is None:     content_type = "application/octet-stream"
            self.send_header("Content-type", content_type)
            self.end_headers() # Finalize headers before sending body
            self.log('do_GET, __sendChunk [%s], path = %s, compress = %s'%(content_type, path, compress))
            self.wfile.write(chunk)

        def __sendFile(path, compress=False):
            with FileAccess.stream(path) as fle:
                __sendChunk(path, fle.readBytes(), compress)
            
        try:
            accept_encoding = self.headers.get("Accept-Encoding", "")
            use_compression = "gzip" in accept_encoding
            if self.path.startswith('/logos/'): # 302 Temporary Redirect
                self.send_response(302)
                self.send_header('Location', f'http://{Globals.PROPERTIES.getRemoteHost()}/images/{Globals._quoteString(self.resources.getImageCache(Globals._unquoteString(self.path.split("/logos/")[1])))}')
                self.log(f'do_GET, redirecting to http://{Globals.PROPERTIES.getRemoteHost()}/images/{Globals._quoteString(image)}')
                self.end_headers()
                return
            else: # 200 OK
                self.send_response(200)
                if   self.path == '/favicon.ico':                return __sendFile(ICON_WEB, use_compression)
                elif self.path.endswith(Globals.PROPERTIES.getProcessID()): #force IPTV to reload fresh local meta.
                    if   M3UFLE.lower()   in self.path:          return __sendFile(M3UFLEPATH, use_compression)
                    elif XMLTVFLE.lower() in self.path:          return __sendFile(XMLTVFLEPATH, use_compression)
                    elif GENREFLE.lower() in self.path:          return __sendFile(GENREFLEPATH, use_compression)
                elif self.path.endswith(f'/{M3UFLE.lower()}'):   return __sendFile(M3UFLEPATH, use_compression) 
                elif self.path.endswith(f'/{XMLTVFLE.lower()}'): return __sendFile(XMLTVFLEPATH, use_compression)
                elif self.path.endswith(f'/{GENREFLE.lower()}'): return __sendFile(GENREFLEPATH, use_compression)
                elif self.path.startswith('/filelist/'):         return __sendChunk(self.path, FileAccess.dumpJSON(Globals.SETTINGS.getCacheSetting(self.path.replace('/filelist/',''), FileAccess._getMD5(self.path.replace('/filelist/','')), default=[])).encode(encoding=DEFAULT_ENCODING), use_compression)
                elif self.path.startswith('/image/'):            return __sendFile(Globals._unquoteString(self.path.split('/image/')[1]), False)
                elif self.path.startswith('/api/'):
                    data = None
                    if   self.path == f'/api/{BONJOURFLE}': data = Globals.SETTINGS.getBonjour()
                    elif self.path == f'/api/{SERVERFLE}' : data = self.service.tasks.Multiroom(service=self.service).getServers()
                    elif self.path == f'/api/{LIBRARYFLE}': data = Library(self.service).getLibrary()
                    elif self.path == f'/api/{CHANNELFLE}': data = Channels().getChannels()
                    elif self.path == f'/api/{LOGSFLE}'   : data = Globals.SETTINGS.getCacheSetting('LOGS', FileAccess._getMD5(datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d')), default={})
                    if not data is None:
                        return __sendChunk(self.path, FileAccess.dumpJSON(data,idnt=4).encode(encoding=DEFAULT_ENCODING), use_compression)
                elif self.path.endswith('.html'):
                    data = None
                    if self.path.lower() == f'/{MANAGERFLE.lower()}': data = Channels()._channelManager()
                    if not data is None: 
                        return __sendChunk(self.path, data, False)
            return self.send_error(404, "File Not Found [%s]" % self.path)
        except FileNotFoundError: self.send_error(404, "File Not Found [%s]" % self.path)
        except Exception as e: 
            self.send_error(500, "Internal Server Error")
            self.log("do_GET, failed!\n%s"%(e), xbmc.LOGERROR)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    
    
class HTTP(Thread):
    httpd = None
    
    def __init__(self, service=None):
        Thread.__init__(self)
        self.service = service
        self.monitor = service.monitor
        self.start()
        
                    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return Globals._log(f"{self.__class__.__name__}: {msg}", level)


    def _chkPort(self, host, port=None):
        if port is None:
            port = Globals.SETTINGS.getSettingInt('TCP_PORT')
        def __isAvailable(host, tmpPort):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind((host, tmpPort))
                    s.close()
                    return True
                except socket.error as e:
                    if e.errno == errno.EADDRINUSE: return False
                    raise e

        tmpPort = port
        while not self.monitor.abortRequested() and not __isAvailable(host, tmpPort):
            self.monitor.waitForAbort(0.5)
            if self.service.pendingShutdown: break
            else:
                self.log(f"_chkPort {tmpPort} is in use. Trying next port.")
                tmpPort += 1
        if tmpPort != port: Globals.DIALOG.notificationDialog(LANGUAGE(30097)%(port,tmpPort))
        self.log("_chkPort, port available = %s"%(tmpPort))
        return tmpPort
        

    def run(self):  
        def __update(silent=None):
            if silent is None: not Globals.SETTINGS.showDialog(silent)
            isRunning = Globals.PROPERTIES.isRunning('HTTP.run')
            if not silent: Globals.DIALOG.notificationDialog('%s: %s'%(Globals.SETTINGS.getSetting('Remote_NAME'),LANGUAGE(32211)%({True:'green',False:'red'}[isRunning],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[isRunning])))
            Globals.SETTINGS.setSetting('Remote_Status',LANGUAGE(32211)%({True:'green',False:'red'}[isRunning],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[isRunning]))

        def __cancel(wait=1.0):
            try:
                if self.httpd.is_alive():
                    if hasattr(self.httpd, 'cancel'): self.httpd.cancel()
                    try: self.httpd.join(wait)
                    except Exception: pass
                return self.httpd.is_alive()
            except Exception: pass
            
        """Starts the threaded HTTP server with GZIP support."""
        if not Globals.PROPERTIES.isRunning('HTTP.start'):
            Globals.PROPERTIES.setRunning('HTTP.start',True)
            while not self.monitor.abortRequested():
                pendingRestart = Globals.PROPERTIES.getEXTProperty('%s.HTTP.pendingRestart'%(ADDON_ID),False)
                if not Globals.PROPERTIES.isRunning('HTTP.run'):
                    Globals.PROPERTIES.setRunning('HTTP.run',True)
                    try: 
                        host   = Globals.SETTINGS.getIP()
                        port   = self._chkPort(host, Globals.SETTINGS.getSettingInt('TCP_PORT'))
                        server = Globals.PROPERTIES.setRemoteHost('%s:%s'%(host,port))
                        Globals.SETTINGS.setSetting('Remote_NAME' ,Globals.PROPERTIES.getFriendlyName())
                        Globals.SETTINGS.setSetting('Remote_M3U'  ,'http://%s/%s'%(server,M3UFLE))
                        Globals.SETTINGS.setSetting('Remote_XMLTV','http://%s/%s'%(server,XMLTVFLE))
                        Globals.SETTINGS.setSetting('Remote_GENRE','http://%s/%s'%(server,GENREFLE))
                        self.log("run, http server @ %s"%(server),xbmc.LOGINFO)
                        
                        ThreadedHTTPServer.allow_reuse_address = True
                        self._server = ThreadedHTTPServer((host, port), partial(MyHandler,service=self.service))
                        try: self._server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        except Exception as e: self.log("run, http server failed to set SO_REUSEADDR: %s" % e, xbmc.LOGWARNING)

                        self.httpd = Thread(target=self._server.serve_forever)
                        self.httpd.name = f"{ADDON_ID}.HTTP.run"
                        self.httpd.daemon=True
                        self.httpd.start()
                        __update(pendingRestart)
                    except Exception as e:
                        self.log("run, http server failed! %s"%(e), xbmc.LOGERROR)
                        break
                elif self.service.pendingShutdown or pendingRestart:
                    self.monitor.waitForAbort(M3U_REFRESH)
                    self.log("run, _shutdown/pendingRestart", xbmc.LOGERROR)
                    break
                    
            try: self._server.shutdown()
            except Exception: pass
            self.log('run, http server shutdown, pendingRestart = %s, isAlive = %s'%(pendingRestart,__cancel()), xbmc.LOGINFO)
            if pendingRestart: 
                Globals.PROPERTIES.clrEXTProperty('%s.HTTP.pendingRestart'%(ADDON_ID))
                self.service._que(self.service.tasks.chkHTTP,1,M3U_REFRESH)
            __update(pendingRestart)
            Globals.PROPERTIES.setRunning('HTTP.run',False)
            Globals.PROPERTIES.setRunning('HTTP.start',False)
