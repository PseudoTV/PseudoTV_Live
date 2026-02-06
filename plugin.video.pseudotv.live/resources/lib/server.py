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
import gzip, mimetypes, socket, errno

from zeroconf                  import *
from globals                   import *
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

        def log(self, msg, level=xbmc.LOGDEBUG):
            return log('%s: %s'%(self.__class__.__name__,msg),level)

        def removeService(self, zeroconf, type, name):
            self.log("removeService, type = %s, name = %s"%(type,name))
             
        def addService(self, zeroconf, type, name):
            info = self.zeroconf.getServiceInfo(type, name)
            if info:
                IP = socket.inet_ntoa(info.getAddress())
                if IP != SETTINGS.getIP():
                    server = info.getServer()
                    self.zServers[server] = {'type':type,'name':name,'server':server,'host':'%s:%d'%(IP,info.getPort()),'bonjour':'http://%s:%s/%s'%(IP,SETTINGS.getSettingInt('TCP_PORT'),BONJOURFLE)}
                    self.log("addService, found zeroconf %s @ %s using bonjour %s"%(server,self.zServers[server]['host'],self.zServers[server]['bonjour']))
                    self.multiroom.addServer(requestURL(self.zServers[server]['bonjour'],cache={'cache':SETTINGS.cache,'json_data':True, "life": datetime.timedelta(seconds=300)}))
            
    def __init__(self, service=None, multiroom=None):
        Thread.__init__(self)
        self.daemon    = True
        self.service   = service
        self.monitor   = service.monitor
        self.multiroom = multiroom
        self.start()

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

    def run(self):
        try: 
            zcons = self.multiroom._getStatus()
            self.log("run, starting ZEROCONF ENABLED (%s)"%(zcons))
            if zcons:
                zconf = Zeroconf()
                self.log("run, Multicast DNS Service waiting for (%s)"%(ZEROCONF_SERVICE))
                SETTINGS.setSetting('ZeroConf_Status','[COLOR=yellow][B]%s[/B][/COLOR]'%(LANGUAGE(32252)))
                ServiceBrowser(zconf, ZEROCONF_SERVICE, self.MyListener(multiroom=self.multiroom))
                self.service._shutdown(DISCOVER_INTERVAL)
                self.log("run, Multicast DNS Service stopping search for (%s)"%(ZEROCONF_SERVICE))
                zconf.close()
            SETTINGS.setSetting('ZeroConf_Status',LANGUAGE(32211)%({True:'green',False:'red'}[zcons],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[zcons]))
            self.log("run, shutting down...")
        except Exception as e: self.log("run, Multicast DNS Service startup failed! %s"%(e), xbmc.LOGERROR)
                   

class MyHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server, service):
        self.service   = service
        self.monitor   = service.monitor
        self.resources = Resources(service)
        
        try: BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        except: pass


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def do_HEAD(self):
        self.log('do_HEAD, incoming path = %s'%(self.path))
        self.send_response(200, "OK")
        self.send_header("Content-type", "*/*")
        self.end_headers()
        
        
    def do_POST(self):
        self.log('do_POST, incoming path = %s'%(self.path))
        def __verifyUUID(uuid):#lazy security check
            if uuid == SETTINGS.getMYUUID(): return True
            else:
                from multiroom  import Multiroom
                for server in list(Multiroom().getDiscovery().values()):
                    if server.get('uuid') == uuid: return True

        if self.path.lower().endswith('.json'):
            try:    incoming = FileAccess.loadJSON(self.rfile.read(int(self.headers['content-length'])).decode())
            except: incoming = {}
            
            if __verifyUUID(incoming.get('uuid')):
                self.log('do_POST incoming uuid [%s] verified!'%(incoming.get('uuid')))
                #channels - channel manager save
                if self.path.lower() == '/%s'%(CHANNELFLE.lower()) and incoming.get('payload'):
                    from channels import Channels
                    if Channels().setChannels(list(Channels()._verify(incoming.get('payload')))):
                        DIALOG.notificationDialog(LANGUAGE(30085)%(LANGUAGE(30108),incoming.get('name',ADDON_NAME)))
                    self.send_response(200, "OK")
                #filelist w/resume - paused channel rule
                elif self.path.lower().startswith('/filelist') and incoming.get('payload'):
                    if FileAccess.setJSON(os.path.join(RESUME_LOC,self.path.replace('/filelist/','')),incoming.get('payload')):
                        DIALOG.notificationDialog(LANGUAGE(30085)%(LANGUAGE(30060),incoming.get('name',ADDON_NAME)))
                    self.send_response(200, "OK")
                elif self.path.startswith(('/manager','/wizard')) and self.path.lower().endswith('form.html'):
                    try:
                        # Prefer a hypothetical SETTINGS.setPayload if it exists
                        if hasattr(SETTINGS, 'setPayload'):
                            SETTINGS.setPayload(incoming.get('payload'))
                        else:
                            # Fallback: write to resume location as remote_payload.json
                            FileAccess.setJSON(os.path.join(RESUME_LOC, 'remote_payload.json'), incoming.get('payload'))
                        DIALOG.notificationDialog(LANGUAGE(30085)%(LANGUAGE(30108),incoming.get('name',ADDON_NAME)))
                        self.send_response(200, "OK")
                    except Exception as e:
                        self.log('do_POST, failed to save remote payload: %s'%(e), xbmc.LOGERROR)
                        self.send_error(500, "Failed to save payload")
                else: self.send_error(401, "Path Not found")
            else: self.send_error(401, "UUID Not verified!")
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
            
            if self.path.lower() == '/favicon.ico':
                self.send_response(204) # 204 No Content
                self.end_headers()
            elif self.path.startswith('/logos/'):
                self.send_response(302) # 302 Temporary Redirect
                chname = Globals._unquoteString(self.path.split('/logos/')[1])
                self.send_header('Location', f'http://{PROPERTIES.getRemoteHost()}/images/{Globals._quoteString(self.resources.getCache(chname))}')
                self.log(f'do_GET, redirecting to http://{PROPERTIES.getRemoteHost()}/images/{Globals._quoteString(image)}')
                self.end_headers()
            else:
                self.send_response(200)
                if   self.path.lower() == f'/{M3UFLE.lower()}':   __sendFile(M3UFLEPATH, use_compression)
                elif self.path.lower() == f'/{GENREFLE.lower()}': __sendFile(GENREFLEPATH, use_compression)
                elif self.path.lower() == f'/{XMLTVFLE.lower()}': __sendFile(XMLTVFLEPATH, use_compression)
                elif self.path.startswith('/images/'):            __sendFile(Globals._unquoteString(self.path.split('/images/')[1]), False)
                else:
                    chunk = b''
                    if   self.path.lower() == f'/{BONJOURFLE.lower()}': chunk = FileAccess.dumpJSON(SETTINGS.getBonjour(inclChannels=True),idnt=4).encode(encoding=DEFAULT_ENCODING)
                    elif self.path.startswith('/filelist'):             chunk = FileAccess.dumpJSON(FileAccess.getJSON((os.path.join(RESUME_LOC, self.path.replace('/filelist/',''))))).encode(encoding=DEFAULT_ENCODING)
                    elif self.path.startswith('/remote'):
                        if   self.path.endswith('.json'):               chunk = FileAccess.dumpJSON(SETTINGS.getPayload(),idnt=4).encode(encoding=DEFAULT_ENCODING)
                        elif self.path.endswith('.html'): 
                            use_compression = False
                            chunk = SETTINGS.getPayloadUI().encode(encoding=DEFAULT_ENCODING)
                        else: return self.send_error(404, "File Not Found [%s]" % self.path)
                    elif self.path.startswith(('/manager','/wizard')) and self.path.lower().endswith('form.html'):
                        def _escape_html(s):
                            return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")
                        use_compression = False
                        fle  = FileAccess.open(FORM_DEFAULT,'r')
                        html = fle.read()
                        fle.close()
                        html.format(json=_escape_html(FileAccess.dumpJSON(SETTINGS.getPayload(), idnt=4)), uuid=SETTINGS.getMYUUID())
                        chunk = html.encode(encoding=DEFAULT_ENCODING)
                    else: return self.send_error(404, "File Not Found [%s]" % self.path)
                    __sendChunk(self.path, chunk, use_compression)
        except FileNotFoundError: self.send_error(404, "File Not Found [%s]" % self.path)
        except Exception as e: self.send_error(500, "Internal Server Error")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    
    
class HTTP(object):
    httpd          = None
    pendingRestart = False
    
    def __init__(self, service=None):
        self.service = service
        self.monitor = service.monitor
        self.httpThread = Thread(target=self.run())
        self.httpThread.daemon = True
        self.httpThread.start()
        
                    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _chkPort(self, host, port=SETTINGS.getSettingInt('TCP_PORT')):
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
            if self.service._shutdown(0.5): break
            else:
                self.log(f"_chkPort {tmpPort} is in use. Trying next port.")
                tmpPort += 1
        if tmpPort != port: DIALOG.notificationDialog(LANGUAGE(30097)%(port,tmpPort))
        self.log("_chkPort, port available = %s"%(tmpPort))
        return tmpPort
        

    def _restart(self):
        self.pendingRestart = True
       

    def run(self, silent=False):  
        def __update(silent=True):
            isRunning = PROPERTIES.isRunning('HTTP.run')
            if not silent: DIALOG.notificationDialog('%s: %s'%(SETTINGS.getSetting('Remote_NAME'),LANGUAGE(32211)%({True:'green',False:'red'}[isRunning],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[isRunning])))
            SETTINGS.setSetting('Remote_Status',LANGUAGE(32211)%({True:'green',False:'red'}[isRunning],{True:LANGUAGE(32158),False:LANGUAGE(32253)}[isRunning]))

        def __cancel(wait=FIFTEEN):
            try:
                if self.httpd.is_alive():
                    if hasattr(self.httpd, 'cancel'): self.httpd.cancel()
                    try: self.httpd.join(wait)
                    except: pass
                return self.httpd.is_alive()
            except: pass
            
        def __stop(restart=False):
            try: self._server.shutdown()
            except: pass
            PROPERTIES.setRunning('HTTP.run',False)
            self.log('run, http server shutdown, restart = %s, isAlive = %s'%(restart,__cancel()), xbmc.LOGINFO)
            if restart:
                self.pendingRestart = False
                self.service._que(self.service.tasks.chkHTTP,1)
            else: __update(restart)
            
        """Starts the threaded HTTP server with GZIP support."""
        while not self.monitor.abortRequested():
            if not PROPERTIES.isRunning('HTTP.run'):
                try: 
                    PROPERTIES.setRunning('HTTP.run',True)
                    host   = SETTINGS.getIP()
                    port   = self._chkPort(host, SETTINGS.getSettingInt('TCP_PORT'))
                    server = PROPERTIES.setRemoteHost('%s:%s'%(host,port))
                    self.log("run, http server @ %s"%(server),xbmc.LOGINFO)
                    SETTINGS.setSetting('Remote_NAME' ,PROPERTIES.getFriendlyName())
                    SETTINGS.setSetting('Remote_M3U'  ,'http://%s/%s'%(server,M3UFLE))
                    SETTINGS.setSetting('Remote_XMLTV','http://%s/%s'%(server,XMLTVFLE))
                    SETTINGS.setSetting('Remote_GENRE','http://%s/%s'%(server,GENREFLE))
                    
                    ThreadedHTTPServer.allow_reuse_address = True
                    self._server = ThreadedHTTPServer((host, port), partial(MyHandler,service=self.service))
                    try: self._server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    except Exception as e: self.log("run, http server failed to set SO_REUSEADDR: %s" % e, xbmc.LOGWARNING)

                    self.httpd = Thread(target=self._server.serve_forever)
                    self.httpd.daemon=True
                    self.httpd.start()
                    __update(silent)
                except Exception as e:
                    self.log("run, http server startup failed! %s"%(e), xbmc.LOGERROR)
                    break
            elif self.service._shutdown(FIFTEEN): 
                self.log("run, _shutdown", xbmc.LOGERROR)
                break
        return __stop(self.pendingRestart)