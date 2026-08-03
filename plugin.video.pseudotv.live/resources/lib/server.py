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

from six.moves.BaseHTTPServer  import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver    import ThreadingMixIn
from typing                    import Any
from zeroconf                  import *
from variables                 import *
from channels                  import Channels
from library                   import Library
from resources                 import Resources
from multiroom                 import Multiroom
#todo proper REST API to handle server/client communication incl. sync/update triggers.
#todo incorporate experimental webserver UI to master branch.

ZEROCONF_SERVICE      = "_xbmc-jsonrpc-h._tcp.local."
COMPRESSION_THRESHOLD = 1024  # 1 KB
CHUNK_SIZE            = 4096 #4 KB

# Filtered-M3U render cache: pvr.iptvsimple polls the M3U repeatedly during
# builds, and each render re-parses the full M3U + 7MB XMLTV + channels.json.
# Cache the rendered bytes keyed by source file mtimes, so between builds the
# hot path is a single dict lookup instead of a 3-pass XMLTV parse.
_M3U_RENDER_CACHE = {'sig': None, 'data': None}
_XMLTV_RENDER_CACHE = {'sig': None, 'data': None}


def _m3u_render_signature() -> tuple:
    """Signature of the data the filtered M3U depends on.

    M3U/XMLTV now live in the SQLite cache, so the render cache keys off the data
    version tokens rather than file mtime/size. A data write bumps the token and
    invalidates the render; nothing else does.
    """
    def _sig(key: str, field: str):
        try:
            v = Globals.settings.getCacheSetting(key) or {}
            return v.get(field)
        except Exception:
            return None
    return (_sig(M3U_CACHE_KEY, 'version'), _sig(XMLTV_META_KEY, 'version'), Globals.getChannelKey())

class Discovery(Thread):
    class MyListener(object):
        def __init__(self, multiroom: Any = None):
            self.zServers  = {}
            self.zeroconf  = Zeroconf()
            self.multiroom = multiroom
            self.jsonRPC   = multiroom.jsonRPC

        def log(self, msg: str, level: int = xbmc.LOGDEBUG):
            LOG(f"{self.__class__.__name__}: {msg}", level)

        def removeService(self, zeroconf: Any, type: str, name: str):
            self.log("removeService, type = %s, name = %s"%(type,name))
            for server_name, server_info in list(self.zServers.items()):
                if server_info.get('name') == name:
                    self.zServers.pop(server_name, None)
                    break

        def addService(self, zeroconf: Any, type: str, name: str):
            INFO = self.zeroconf.getServiceInfo(type, name)
            if INFO:
                server  = INFO.getServer()
                address = INFO.getAddress()
                if not isinstance(address, bytes):
                    address = bytes(address)
                ip = socket.inet_ntop(socket.AF_INET, address)
                self.zServers[server] = {'type':type,'name':name,'server':server,'host':'%s:%d'%(ip,INFO.getPort()),'bonjour':'http://%s:%s/api/%s'%(ip,Globals.settings.getSettingInt('TCP_PORT'),BONJOURFLE)}
                self.log("addService, found %s @ %s (bonjour=%s)" % (server, self.zServers[server]['host'], self.zServers[server]['bonjour']))
                self.multiroom.addServer(self.jsonRPC.requestURL(self.zServers[server]['bonjour']))


    def __init__(self, service: Any = None, multiroom: Any = None):
        Thread.__init__(self)
        self.daemon    = True
        self.service   = service
        self.monitor   = service.monitor
        self.multiroom = multiroom
        self.start()


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def run(self):
        if not Globals.properties.isRunning('Discovery.run'):
            with Globals.properties.chkRunning('Discovery.run'):
                while not self.monitor.abortRequested():
                    try:
                        zcons = self.multiroom._getStatus()
                        self.log("run, zeroconf_enabled=%s" % zcons)
                        if zcons:
                            zconf = Zeroconf()
                            self.log("run, browsing for %s" % ZEROCONF_SERVICE)
                            ServiceBrowser(zconf, ZEROCONF_SERVICE, self.MyListener(multiroom=self.multiroom))
                            Globals.settings.setSetting('ZeroConf_Status','[COLOR=yellow][B]%s[/B][/COLOR]'%(LANGUAGE(32252)))
                            if self.monitor.waitForAbort(DISCOVER_INTERVAL): break
                            self.log("run, stopping browse for %s" % ZEROCONF_SERVICE)
                            zconf.close()
                        Globals.settings.setSetting('ZeroConf_Status',LANGUAGE(32211).format(color={True:'green',False:'red'}[zcons],text={True:LANGUAGE(32158),False:LANGUAGE(32253)}[zcons]))
                    except Exception as e:
                        self.log("run, zeroconf browse failed: %s" % e, xbmc.LOGERROR)
                        break
                    if self.monitor.waitForAbort(600):
                        self.log("run, abort requested during sleep", xbmc.LOGERROR)
                        break
                self.log("run, shutting down")


class MyHandler(BaseHTTPRequestHandler):
    def __init__(self, request: Any, client_address: Any, server: Any, service: Any):
        self.service   = service
        self.monitor   = service.monitor
        self.resources = Resources(service)

        try: BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        except Exception as e: self.log('__init__ failed: %s' % e, xbmc.LOGDEBUG)


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def _getFilteredM3U(self, allowed_ids=None):
        """Get filtered M3U content using M3U class render() + filter pipeline.

        Rendered output is cached keyed by source file mtimes — pvr.iptvsimple
        polls the M3U repeatedly during builds, and each render otherwise
        re-parses the full M3U + XMLTV + channels.json (3-pass parse of a 7MB+ file).
        """
        global _M3U_RENDER_CACHE
        sig = _m3u_render_signature()
        if _M3U_RENDER_CACHE['sig'] == sig:
            return _M3U_RENDER_CACHE['data']
        from io import BytesIO
        from m3u import M3U
        m3u = M3U()
        stations = m3u.getFilteredStations()
        buf = BytesIO()
        m3u.render(buf, stations=stations)
        data = buf.getvalue()
        # never cache an implausibly large render — a half-written M3U read
        # during a build once produced a 776MB blob that was then served on every poll
        # until the file changed. Cap at 20MB (legit filtered M3U with recordings stays
        # well under this); oversized output is served once but not cached.
        if len(data) > 20 * 1024 * 1024:
            self.log(f"_getFilteredM3U, render too large ({len(data)} bytes), not caching", xbmc.LOGWARNING)
            return data
        _M3U_RENDER_CACHE = {'sig': sig, 'data': data}
        return data


    def _getFilteredXMLTV(self):
        """Get XMLTV content with temporary placeholder programmes injected.

        Channels whose EPG doesn't reach the Min_Days horizon — including no-guide
        channels — get an informative placeholder so pvr.iptvsimple shows a non-empty
        row. Data is served from the SQLite cache (renderWithPlaceholders), not disk.

        Rendered output is cached keyed on the XMLTV data version token — pvr.iptvsimple
        polls the guide repeatedly, and a full re-render of a 10MB+ XMLTV per request
        was slow enough to make the window unresponsive.
        """
        global _XMLTV_RENDER_CACHE
        sig = self._xmltv_render_signature()
        if _XMLTV_RENDER_CACHE['sig'] == sig:
            return _XMLTV_RENDER_CACHE['data']
        from io import BytesIO
        from xmltvs import XMLTVS
        # Load XMLTV once and derive the served-station set from the same data so a
        # cache miss doesn't parse/load the 51MB guide twice.
        xmltv_obj = XMLTVS()
        stations = xmltv_obj.m3u.getFilteredStations(programmes=xmltv_obj.getProgrammes())
        buf = BytesIO()
        xmltv_obj.renderWithPlaceholders(buf, stations=stations)
        data = buf.getvalue()
        # don't cache implausibly large / empty renders
        if data and len(data) < 100 * 1024 * 1024:
            _XMLTV_RENDER_CACHE = {'sig': sig, 'data': data}
        return data

    def _xmltv_render_signature(self) -> tuple:
        """Signature of the data the served XMLTV depends on.

        Same inputs as the M3U render signature (XMLTV + M3U + channels.json) so
        both caches invalidate together — the served XMLTV mirrors the filtered
        M3U, so a change in channels.json or the M3U must re-render it too.
        """
        return _m3u_render_signature()


    def _getGenres(self) -> bytes:
        """Return rendered genres.xml bytes from the SQLite cache.

        Falls back to the on-disk export file (legacy) if the cache is empty and
        an export file exists.
        """
        try:
            data = Globals.settings.getCacheSetting(GENRES_CACHE_KEY)
            if data is not None:
                return data if isinstance(data, bytes) else bytes(data, DEFAULT_ENCODING)
        except Exception as e:
            self.log(f"_getGenres, cache read failed: {e}", xbmc.LOGDEBUG)
        if FileAccess.exists(GENREFLEPATH):
            try:
                with FileAccess.stream(GENREFLEPATH) as fle:
                    return fle.readBytes()
            except Exception as e:
                self.log(f"_getGenres, file fallback failed: {e}", xbmc.LOGDEBUG)
        return b''


    def do_HEAD(self):
        self.log('do_HEAD, incoming path = %s'%(self.path))
        self.send_response(200, "OK")
        self.send_header("Content-type", "*/*")
        self.end_headers()


    def do_POST(self):
        self.log('do_POST, incoming path = %s'%(self.path))
        def __verifyUUID(uuid: str):#lazy security check
            if uuid == Globals.settings.getMYUUID(): return True
            else:
                from multiroom  import Multiroom
                for server in list(Multiroom().serverData.values()):
                    if server.get('uuid') == uuid:
                        return True

        try:
            content_length = int(self.headers.get('content-length', 0))
            if content_length > 10 * 1024 * 1024:  # 10MB limit
                self.log(f'do_POST, request too large: {content_length} bytes', xbmc.LOGWARNING)
                return self.send_error(413, "Request Entity Too Large")
            incoming = FileAccess.loadJSON(self.rfile.read(content_length).decode(), skip_cache=True)
        except Exception as e: 
            self.log(f'do_POST, failed to parse incoming body: {e}', xbmc.LOGWARNING)
            incoming = {}

        if __verifyUUID(incoming.get('uuid')) and incoming.get('payload'):
            self.log('do_POST incoming uuid [%s] verified!'%(incoming.get('uuid')))
            if self.path.startswith('/api/'):
                if self.path == f'/api/{CHANNELFLE}':
                    channels = Channels(Globals.getChannelKey(), writable=True)
                    if channels.setChannels(list(channels._verify(incoming.get('payload')))):
                        Globals.dialog.notificationDialog(LANGUAGE(30085).format(name=LANGUAGE(30108),author=incoming.get('name',ADDON_NAME)))
                    del channels
                    self.send_response(200, "OK")
            elif self.path.startswith('/filelist/'):
                #filelist w/resume - paused channel rule
                if Globals.settings.setCacheSetting(self.path.replace('/filelist/',''), incoming.get('payload'), FileAccess._getMD5(self.path.replace('/filelist/','')), datetime.timedelta(days=84)):
                    Globals.dialog.notificationDialog(LANGUAGE(30085).format(name=LANGUAGE(30060),author=incoming.get('name',ADDON_NAME)))
                    self.send_response(200, "OK")
            else: return self.do_GET()


    def do_GET(self):
        self.log('do_GET, incoming path = %s' % (self.path))
        def __sendChunk(path: str, chunk: bytes, compress: bool = False):
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

        def __sendFile(path: str, compress: bool = False):
            with FileAccess.stream(path) as fle:
                __sendChunk(path, fle.readBytes(), compress)

        try:
            accept_encoding = self.headers.get("Accept-Encoding", "")
            use_compression = "gzip" in accept_encoding
            if self.path.startswith('/logos/'): # 302 Temporary Redirect
                image = self.resources.getImageCache(Globals._unquoteString(self.path.split("/logos/")[1]))
                self.send_response(302)
                self.send_header('Location', f'http://{Globals.properties.getRemoteHost()}/image/{Globals._quoteString(image)}')
                self.log(f'do_GET, redirecting to http://{Globals.properties.getRemoteHost()}/image/{Globals._quoteString(image)}')
                self.end_headers()
                return
            else: # 200 OK
                self.send_response(200)
                if   self.path == '/favicon.ico':                return __sendFile(ICON_WEB, use_compression)
                elif self.path.endswith(Globals.properties.getProcessID()): #force IPTV to reload fresh local meta.
                    if   M3UFLE.lower()   in self.path:          return __sendChunk(self.path, self._getFilteredM3U(), use_compression)
                    elif XMLTVFLE.lower() in self.path:          return __sendChunk(self.path, self._getFilteredXMLTV(), use_compression)
                    elif GENREFLE.lower() in self.path:          return __sendChunk(self.path, self._getGenres(), use_compression)
                    elif SEASONFLE.lower()  in self.path:        return __sendFile(SEASONS, use_compression)
                    elif HOLIDAYFLE.lower() in self.path:        return __sendFile(HOLIDAYS, use_compression)
                elif self.path.endswith(f'/{M3UFLE.lower()}'):   return __sendChunk(self.path, self._getFilteredM3U(), use_compression)
                elif self.path.endswith(f'/{XMLTVFLE.lower()}'): return __sendChunk(self.path, self._getFilteredXMLTV(), use_compression)
                elif self.path.endswith(f'/{GENREFLE.lower()}'): return __sendChunk(self.path, self._getGenres(), use_compression)
                elif self.path.endswith(f'/{SEASONFLE.lower()}'):  return __sendFile(SEASONS, use_compression)
                elif self.path.endswith(f'/{HOLIDAYFLE.lower()}'): return __sendFile(HOLIDAYS, use_compression)
                elif self.path.startswith('/filelist/'):         return __sendChunk(self.path, FileAccess.dumpJSON(Globals.settings.getCacheSetting(self.path.replace('/filelist/',''), FileAccess._getMD5(self.path.replace('/filelist/','')), default=[])).encode(encoding=DEFAULT_ENCODING), use_compression)
                elif self.path.startswith('/image/'):
                    img_path = Globals._unquoteString(self.path.split('/image/')[1])
                    if '..' in img_path: return self.send_error(400, "Invalid path")
                    if not img_path: return __sendFile(LOGO, False)  # dead placeholder -> LOGO var
                    return __sendFile(img_path, False)
                elif self.path.startswith('/api/'):
                    data = None
                    if   self.path == f'/api/{BONJOURFLE}': data = Globals.settings.getBonjour()
                    elif self.path == f'/api/{SERVERFLE}' : data = Multiroom(service=self.service).serverData
                    elif self.path == f'/api/{LIBRARYFLE}': data = Library(self.service).getLibrary()
                    elif self.path == f'/api/{CHANNELFLE}': data = Channels(Globals.getChannelKey()).getChannels()
                    elif self.path == f'/api/{PVRFLE}':     data = Globals.settings.instances.updatePVRStatus(Globals.properties.getRemoteHost(),Globals.properties.getFriendlyName())
                    elif self.path == f'/api/{LOGSFLE}':    data = Globals.builtin.parseKodiLog()
                    if not data is None:
                        return __sendChunk(self.path, FileAccess.dumpJSON(data,idnt=4).encode(encoding=DEFAULT_ENCODING), use_compression)
                elif self.path.endswith('.html'):
                    data = None
                    if self.path.lower() == f'/{MANAGERFLE.lower()}': data = Channels(Globals.getChannelKey())._channelManager()
                    if not data is None:
                        return __sendChunk(self.path, data, False)
            return self.send_error(404, "File Not Found [%s]" % self.path)
        except FileNotFoundError: self.send_error(404, "File Not Found [%s]" % self.path)
        except Exception as e:
            self.send_error(500, "Internal Server Error")
            self.log("do_GET, failed!\n%s"%(e), xbmc.LOGERROR)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    timeout = HTTP_TIMEOUT


class HTTP(Thread):
    httpd = None


    def __init__(self, service: Any = None):
        Thread.__init__(self)
        self.daemon = True
        self.service = service
        self.monitor = service.monitor
        self.start()


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def _chkPort(self, host: str, port: int = None) -> int:
        if port is None:
            port = Globals.settings.getSettingInt('TCP_PORT')
        def __isAvailable(host: str, tmpPort: int) -> bool:
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
        if tmpPort != port: Globals.dialog.notificationDialog(LANGUAGE(30097).format(port=port,available=tmpPort))
        self.log("_chkPort, port available = %s"%(tmpPort))
        return tmpPort


    def run(self):
        def __update(silent: bool = None):
            if silent is None: not Globals.settings.showDialog(silent)
            isRunning = Globals.properties.isRunning('HTTP.run')
            if not silent: Globals.dialog.notificationDialog('%s: %s'%(Globals.settings.getSetting('Remote_NAME'),LANGUAGE(32211).format(color={True:'green',False:'red'}[isRunning],text={True:LANGUAGE(32158),False:LANGUAGE(32253)}[isRunning])))
            Globals.settings.setSetting('Remote_Status',LANGUAGE(32211).format(color={True:'green',False:'red'}[isRunning],text={True:LANGUAGE(32158),False:LANGUAGE(32253)}[isRunning]))

        def __cancel(wait: float = 1.0):
            try:
                if self.httpd.is_alive():
                    if hasattr(self.httpd, 'cancel'): self.httpd.cancel()
                    try: self.httpd.join(wait)
                    except Exception as e: self.log('__cancel join failed: %s' % e, xbmc.LOGDEBUG)
                return self.httpd.is_alive()
            except Exception as e: self.log('__cancel failed: %s' % e, xbmc.LOGDEBUG)

        """Starts the threaded HTTP server with GZIP support."""
        if not Globals.properties.isRunning('HTTP.start'):
            Globals.properties.setRunning('HTTP.start',True)
            while not self.monitor.abortRequested():
                pendingRestart = Globals.properties.getEXTProperty('%s.HTTP.pendingRestart'%(ADDON_ID),False)
                if not Globals.properties.isRunning('HTTP.run'):
                    Globals.properties.setRunning('HTTP.run',True)
                    try:
                        host   = Globals.settings.getIP()
                        port   = self._chkPort(host, Globals.settings.getSettingInt('TCP_PORT'))
                        server = Globals.properties.setRemoteHost('%s:%s'%(host,port))
                        Globals.settings.setSetting('Remote_NAME' ,Globals.properties.getFriendlyName())
                        Globals.settings.setSetting('Remote_M3U'  ,'http://%s/%s'%(server,M3UFLE))
                        Globals.settings.setSetting('Remote_XMLTV','http://%s/%s'%(server,XMLTVFLE))
                        Globals.settings.setSetting('Remote_GENRE','http://%s/%s'%(server,GENREFLE))
                        self.log("run, http server @ %s"%(server),xbmc.LOGINFO)

                        ThreadedHTTPServer.allow_reuse_address = True
                        # bind all interfaces so the server answers on every
                        # advertised IP. Kodi's mDNS announces virtual/Hyper-V adapters
                        # (e.g. 172.20.32.1) in addition to the LAN IP; binding only the
                        # LAN IP made /api/bonjour.json unreachable on those, reporting
                        # "server unreachable". URLs still advertise the LAN host.
                        self._server = ThreadedHTTPServer(('0.0.0.0', port), partial(MyHandler,service=self.service))
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
                    self.monitor.waitForAbort(5)
                    self.log("run, _shutdown/pendingRestart", xbmc.LOGERROR)
                    break

            try: self._server.shutdown()
            except Exception as e: self.log('server shutdown failed: %s' % e, xbmc.LOGDEBUG)
            try: self._server.server_close()
            except Exception as e: self.log('server_close failed: %s' % e, xbmc.LOGDEBUG)
            self.log('run, http server shutdown, pendingRestart = %s, isAlive = %s'%(pendingRestart,__cancel()), xbmc.LOGINFO)
            if pendingRestart:
                Globals.properties.clrEXTProperty('%s.HTTP.pendingRestart'%(ADDON_ID))
                self.service._que(self.service.tasks.chkHTTP,1,M3U_REFRESH)
            __update(pendingRestart)
            Globals.properties.setRunning('HTTP.run',False)
            Globals.properties.setRunning('HTTP.start',False)
