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
import gzip, mimetypes, socket, errno, queue, re

from six.moves.BaseHTTPServer  import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver    import ThreadingMixIn
from typing                    import Any, Optional
from zeroconf                  import *
from variables                 import *
from channels                  import Channels
from webpoint                  import ChannelManager, WebPoint
from library                   import Library
from resources                 import Resources
from multiroom                 import Multiroom
from rules                     import RulesList
from xmltvs                    import renderFilteredM3U, renderFilteredXMLTV, getFilteredGenres
#todo proper REST API to handle server/client communication incl. sync/update triggers.
#todo incorporate experimental webserver UI to master branch.

ZEROCONF_SERVICE      = "_xbmc-jsonrpc-h._tcp.local."
COMPRESSION_THRESHOLD = 1024  # 1 KB
CHUNK_SIZE            = 4096 #4 KB

# Server-Sent Events bus: API handlers / service can publish events that the
# /api/events stream relays to connected browsers (build progress, saves, ...).
_EVENTS = queue.Queue()

def _publish(event: dict):
    if _EVENTS.qsize() > 200:
        try: _EVENTS.get_nowait()
        except Exception: pass
    _EVENTS.put(event)


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
        self.service    = service
        self.monitor    = service.monitor
        self.resources  = Resources(service)
        self.cm         = ChannelManager(service)
        self.wp         = WebPoint(service)
        # Cache the rule dispatcher on the service keyed by (channel key, channel
        # count) — rebuilding RulesList (loadRules over every channel) on each HTTP
        # request was wasteful under pvr.iptvsimple polling. Channels are reloaded
        # per request so autotune/build results show up even when the key is stable.
        ch_key = Globals.getChannelKey()
        self.channels = Channels(ch_key).getChannels()
        sig = (ch_key, len(self.channels))
        cached = getattr(service, '_serve_rules', None)
        if not cached or cached[0] != sig:
            service._serve_rules = (sig, RulesList(self.channels).runActions, self.channels)
        self.runActions = service._serve_rules[1]

        try: BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        except Exception as e: self.log('__init__ failed: %s' % e, xbmc.LOGDEBUG)


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    # ======================= response helpers =======================
    def _path(self) -> str:
        return self.path.split('?', 1)[0]


    def _query(self) -> dict:
        q = {}
        if '?' in self.path:
            for pair in self.path.split('?', 1)[1].split('&'):
                if not pair: continue
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    q[Globals._unquoteString(k)] = Globals._unquoteString(v)
                else:
                    q[Globals._unquoteString(pair)] = ''
        return q


    def _send(self, data: Any, path: str = '', code: int = 200, ctype: Optional[str] = None, compress: bool = False, cors: bool = False, gz: bool = False):
        if isinstance(data, str): data = data.encode(DEFAULT_ENCODING)
        if compress and not gz:
            data = gzip.compress(data, compresslevel=5)
        if ctype is None:
            ctype = {'.json':'application/json', '.m3u':'application/vnd.apple.mpegurl',
                     '.xml':'application/xml', '.html':'text/html'}.get(
                        os.path.splitext(path)[1].lower(), mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_response(code)  # status line must precede any headers
        if compress or gz:
            self.send_header("Content-Encoding", "gzip")
        if cors:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", len(data))
        self.send_header("Content-type", ctype)
        if ctype == 'text/html':
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.log('do_GET, __sendChunk [%s], path = %s, compress = %s' % (ctype, path, compress))
        if not getattr(self, '_head_only', False):
            self.wfile.write(data)


    def _sendJSON(self, obj: Any, code: int = 200, cors: bool = True):
        self._send(FileAccess.dumpJSON(obj, idnt=4).encode(DEFAULT_ENCODING), 'api.json', code=code, ctype='application/json', cors=cors)


    def _sendError(self, code: int, msg: str):
        self._sendJSON({'error': msg, 'status': code}, code=code)


    def _sendFile(self, path: str, compress: bool = False):
        with FileAccess.stream(path) as fle:
            self._send(fle.readBytes(), path, compress=compress)


    def _serveImage(self, img: str):
        """Serve an image for a Kodi VFS path / URL. Serves loose files directly,
        re-encodes xbt raw pixels to PNG, and falls back to skin media. Always a
        200 with an image content-type — redirects break Kodi's mime-type probe."""
        # Cache values may hold Kodi-encoded paths (smb%3a%2f..) plus a URL-encode
        # layer from the browser — decode until stable to reach the real path.
        while True:
            prev = img
            img = Globals._unquoteString(img)
            if img == prev: break
        if re.search(r'(^|[\\/])\.\.([\\/]|$)', img): return self._sendError(400, 'Invalid path')
        if not img: return self._sendFile(LOGO, False)
        # legacy cache entries wrapped resource:// in image:// — unwrap.
        if img.startswith('image://'):
            img = img[len('image://'):]
        # loose files (root/media/resources) resolve via addon path.
        if img.startswith('resource://'):
            try:
                addon_id, rest = img[len('resource://'):].split('/', 1)
                if Globals.settings.hasAddon(addon_id):
                    addon = Globals.settings.getAddonDetails(addon_id).get('path', '')
                    real = os.path.join(addon, rest.replace('/', os.sep))
                    if FileAccess.exists(real): return self._sendFile(real, False)
            except Exception as e:
                self.log('resource image resolve failed: %s' % e, xbmc.LOGDEBUG)
        if FileAccess.exists(img):
            data = self.resources._readImage(img)
            if data:
                if data[:8] == b'\x89PNG\r\n\x1a\n':
                    return self._send(data, img, ctype='image/png')
                # xbt-backed resource:// returns raw unpacked pixels —
                # re-encode to PNG so browsers can render it.
                png = self.resources._xbtToPNG(img, data)
                if png: return self._send(png, 'xbt.png', ctype='image/png')
                return self._send(data, img)
        full = os.path.join(MEDIA_LOC, os.path.basename(img.replace('\\', '/')))
        if FileAccess.exists(full): return self._sendFile(full, False)
        # Resolved path doesn't exist (stale cache / deleted generated logo) —
        # degrade to the default addon logo instead of 404 so Kodi's mime probe
        # never breaks on a vanished image.
        self.log('_serveImage, missing image [%s], serving default logo' % img, xbmc.LOGDEBUG)
        if FileAccess.exists(LOGO): return self._sendFile(LOGO, False)
        return self._sendError(404, 'File Not Found [%s]' % self.path)


    def _readJSON(self) -> dict:
        content_length = int(self.headers.get('content-length', 0) or 0)
        if content_length > 10 * 1024 * 1024:
            raise ValueError('request too large')
        raw = self.rfile.read(content_length)
        return FileAccess.loadJSON(raw.decode(DEFAULT_ENCODING) if raw else '', skip_cache=True)


    # ======================= HTML templating =======================
    @staticmethod
    def _jsonScript(obj: Any) -> str:
        """JSON literal safe to inject into an inline <script> block."""
        s = FileAccess.dumpJSON(obj, sortkey=True)
        return s.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')\
                .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


    def _templateHTML(self, html: str, name: str) -> bytes:
        remote   = Globals.properties.getRemoteHost()
        channels = Channels(Globals.getChannelKey())
        html = html.replace('{{ remote_host }}', remote)
        html = html.replace('{{ media_loc }}', MEDIA_LOC)
        html = html.replace('{{ channel_limit }}', str(CHANNEL_LIMIT))
        html = html.replace('{{ CHANNEL_LIMIT|safe }}', str(CHANNEL_LIMIT))
        html = html.replace('{{ servers_json|safe }}', self._jsonScript(Multiroom(service=self.service).serverData))
        html = html.replace('{{ channels_json|safe }}', self._jsonScript(channels.getChannels()))
        html = html.replace('{{ template_json|safe }}', self._jsonScript(channels.getTemplate()))
        if '{{ xmltv_data|safe }}' in html:
            xml = renderFilteredXMLTV(self.channels, self.runActions).decode(DEFAULT_ENCODING, 'replace')
            xml = xml.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${').replace('</script', '<\\/script')
            html = html.replace('{{ xmltv_data|safe }}', xml)
        html = html.replace('{json}', '{}')
        html = html.replace('{uuid}', Globals.settings.getMYUUID())
        return html.encode(DEFAULT_ENCODING)


    def _serveHTML(self, name: str):
        with FileAccess.stream(os.path.join(REMOTE_LOC, name)) as fle:
            html = fle.read()
        if isinstance(html, bytes): html = html.decode(DEFAULT_ENCODING, 'replace')
        self._send(self._templateHTML(html, name), name, ctype='text/html')


    # ======================= channel save / helpers =======================
    # ======================= channel manager (delegates to ChannelManager) =======================


    def do_HEAD(self):
        self.log('do_HEAD, incoming path = %s' % (self.path))
        # Mirror GET so HEAD mime probes (Kodi's GetMimeType) see the real
        # content-type instead of a hardcoded */*.
        self._head_only = True
        try:
            self.do_GET()
        finally:
            self._head_only = False


    def do_OPTIONS(self):
        """CORS preflight for the browser API clients (channels_new.html, etc.)."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()


    def _authorized(self, incoming: Optional[dict] = None) -> bool:
        """Guard mutating POST endpoints with the instance UUID.

        Accepts the per-install UUID (Globals.getMYUUID) either as a bearer token
        (`Authorization: Bearer <uuid>`) or in the existing `uuid` body field the
        web UI already sends. The UUID is auto-generated per install, needs no
        setup, and is already exposed to the browser via /api/bonjour.json and
        the {uuid} template placeholder. No shared secret to misconfigure.
        """
        if incoming is None: incoming = {}
        try:
            expected = Globals.settings.getMYUUID()
        except Exception:
            return True  # UUID unavailable — don't lock the user out
        if not expected:
            return True  # no UUID yet — behave as before
        auth = self.headers.get('Authorization', '')
        if auth.strip().lower() == ('bearer %s' % expected).lower():
            return True
        body_uuid = incoming.get('uuid')
        return bool(body_uuid) and str(body_uuid) == expected


    def do_POST(self):
        self.log('do_POST, incoming path = %s' % (self.path))
        path = self._path()
        try:
            incoming = self._readJSON()
        except Exception as e:
            self.log(f'do_POST, failed to parse incoming body: {e}', xbmc.LOGWARNING)
            incoming = {}
        if not self._authorized(incoming):
            self.log('do_POST, unauthorized write attempt: %s' % path, xbmc.LOGWARNING)
            return self._sendError(401, 'unauthorized')

        if path.startswith('/api/'):
            return self._apiPOST(path, incoming)

        if path == '/remote/form.json':  # generic payload editor (form.html)
            payload = incoming.get('payload')
            if isinstance(payload, list):
                p, code = self.cm.saveChannels(payload)
                return self._sendJSON(p, code)
            if isinstance(payload, dict) and isinstance(payload.get('channels'), list):
                p, code = self.cm.saveChannels(payload.get('channels'))
                return self._sendJSON(p, code)
            if isinstance(payload, dict) and ('resume' in payload or 'filelist' in payload):
                Globals.settings.setCacheSetting('form.payload', payload, FileAccess._getMD5('form.payload'), datetime.timedelta(days=84))
                return self._sendJSON({'status': 'ok'})
            return self._sendError(400, 'unrecognized payload')

        if path.startswith('/filelist/'):  # resume data
            if incoming.get('uuid') and not self.cm.verifyUUID(incoming.get('uuid')):
                return self._sendError(403, 'invalid uuid')
            key = path.replace('/filelist/', '')
            Globals.settings.setCacheSetting(key, incoming.get('payload'), FileAccess._getMD5(key), datetime.timedelta(days=84))
            return self._sendJSON({'status': 'ok'})

        return self._sendError(404, 'unknown endpoint: %s' % path)


    def _apiPOST(self, path: str, incoming: dict):
        if path == '/api/save':
            payload, code = self.cm.saveChannel(incoming.get('payload', incoming))
            return self._sendJSON(payload, code)
        if path in (f'/api/{CHANNELFLE}', '/api/channels'):
            if incoming.get('uuid') and not self.cm.verifyUUID(incoming.get('uuid')):
                return self._sendError(403, 'invalid uuid')
            _publish({'type': 'channels.saved', 'count': len(incoming.get('payload', incoming.get('channels', [])) or [])})
            payload, code = self.cm.saveChannels(incoming.get('payload', incoming.get('channels')))
            return self._sendJSON(payload, code)
        if path == '/api/settings':
            return self._updateSettings(incoming.get('payload', incoming))
        if path == '/api/actions':
            return self._runAction(incoming)
        if path == '/api/imports':
            p, code = self.wp.manageImports('POST', incoming)
            return self._sendJSON(p, code)
        if path == '/api/backups':
            p, code = self.wp.manageBackups('POST', incoming)
            return self._sendJSON(p, code)
        if path == '/api/seasons':
            ok = self.wp.seasonal().setSeasonsData(incoming.get('payload', incoming))
            if ok: self.wp.syncSeasonalToRemotes('seasons', incoming.get('payload', incoming))
            _publish({'type': 'seasons.saved'})
            return self._sendJSON({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        if path == '/api/holidays':
            ok = self.wp.seasonal().setHolidaysData(incoming.get('payload', incoming))
            if ok: self.wp.syncSeasonalToRemotes('holidays', incoming.get('payload', incoming))
            _publish({'type': 'holidays.saved'})
            return self._sendJSON({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        if path == '/api/channel/validate':
            citem = incoming.get('payload', incoming)
            return self._sendJSON({'citem': self.cm.validateChannel(citem) if isinstance(citem, dict) else {}})
        if path == '/api/groups':
            return self._sendJSON(self.cm.addGroup(incoming))
        if path.startswith('/api/channels/'):
            payload, code = self.cm.channelCRUD('PUT', path, incoming)
            if code == 200:
                cid = Globals._unquoteString(path.split('/api/channels/', 1)[1])
                _publish({'type': 'channel.updated', 'id': cid})
            return self._sendJSON(payload, code)
        return self._sendError(404, 'unknown api: %s' % path)


    def _apiGET(self, path: str, query: dict, compress: bool):
        ch_key = Globals.getChannelKey()
        routes = {
            f'/api/{BONJOURFLE}': lambda: Globals.settings.getBonjour(),
            f'/api/{SERVERFLE}':  lambda: self.wp.serversPayload(),
            f'/api/{LIBRARYFLE}': lambda: Library(self.service).getLibrary(),
            f'/api/{CHANNELFLE}': lambda: self.cm.channels(),
            f'/api/{PVRFLE}':     lambda: dict(Globals.settings.instances.updatePVRStatus(Globals.properties.getRemoteHost(), Globals.properties.getFriendlyName()),
                                               playback=self.wp.playbackJSON()),
            f'/api/{LOGSFLE}':    lambda: Globals.builtin.parseKodiLog(),
            '/api/channels':      lambda: self.cm.channels(),
            '/api/template':      lambda: Channels(ch_key).getTemplate(),
            '/api/bonjour':       lambda: Globals.settings.getBonjour(),
            '/api/settings':      lambda: self.cm.currentSettings(),
            '/api/rules':         lambda: self.wp.rulesJSON(),
            '/api/system':        lambda: self.wp.systemInfo(),
            '/api/playback':      lambda: self.wp.playbackJSON(),
            '/api/build':         lambda: self.wp.buildStatus(),
            '/api/guide':         lambda: self.wp.guideJSON(query.get('page', 0)),
            '/api/imports':       lambda: self.wp.manageImports('GET')[0],
            '/api/backups':       lambda: self.wp.manageBackups('GET')[0],
            '/api/groups':        lambda: self.cm.groups(),
            '/api/seasons':       lambda: self.wp.seasonal().getSeasonsData(),
            '/api/holidays':      lambda: self.wp.seasonal().getHolidaysData(),
            '/api/resume':        lambda: self.wp.resumeJSON(),
        }
        if path in routes:
            return self._sendJSON(routes[path](), cors=True)
        if path == '/api/xmltv':
            return self._send(renderFilteredXMLTV(self.channels, self.runActions), path, ctype='application/xml', compress=compress, cors=True)
        if path == '/api/logo_search':
            return self._sendJSON(self.cm.searchLogo(query.get('q', '')))
        if path == '/api/logo_lookup':
            return self._sendJSON(self.cm.lookupLogo(query.get('name', ''), query.get('type', '')))
        if path == '/api/logo_select':
            return self._sendJSON(self.cm.selectLogo(query.get('name', ''), query.get('type', '')))
        if path == '/api/browse':
            return self._sendJSON(self.cm.browsePath(query.get('path', '')))
        if path == '/api/events':
            return self._sse()
        if path.startswith('/api/channels/'):
            payload, code = self.cm.channelCRUD('GET', path)
            return self._sendJSON(payload, code)
        return self._sendError(404, 'unknown api: %s' % path)


    # ======================= extended API endpoints =======================
    def _updateSettings(self, data: dict):
        if not isinstance(data, dict): return self._sendError(400, 'invalid payload')
        for k, v in data.items():
            try:
                if   isinstance(v, bool): Globals.settings.setSettingBool(k, v)
                elif isinstance(v, int):  Globals.settings.setSettingInt(k, v)
                else:                     Globals.settings.setSetting(k, str(v))
            except Exception as e:
                self.log('settings update failed %s: %s' % (k, e), xbmc.LOGDEBUG)
        # Kodi doesn't emit onSettingsChanged for API-driven setting changes, so
        # disabling autotune here never triggered the migrate+restart. Do it now.
        if data.get('Enable_Autotune') is False:
            self.cm.migrateAutotune()
        _publish({'type': 'settings.updated', 'keys': list(data.keys())})
        return self._sendJSON({'status': 'ok'})


    def _runAction(self, incoming: dict):
        payload = incoming.get('payload', incoming)
        action = incoming.get('action') or (payload.get('action') if isinstance(payload, dict) else None)
        if not action: return self._sendError(400, 'missing action')
        tasks = self.service.tasks
        try:
            if   action == 'build':
                self.service._que(tasks.chkChannels, 3, 0, 0, *(None, None))
            elif action == 'reload':
                Globals.properties.setPropTimer('chkPVRRefresh')
            elif action == 'rebuild':
                try:
                    from m3u import clearM3UCache
                    from xmltvs import clearXMLTVCache
                    clearM3UCache(); clearXMLTVCache()
                except Exception: pass
                self.service._que(tasks.chkChannels, 3, 0, 0, *(None, None))
            elif action == 'restart':
                Globals.properties.setPendingRestart()
            elif action == 'sync':
                self.service._que(tasks.chkPVRSync, 3)
            elif action == 'autotune':
                from context_create import _autotune
                self.service._que(_autotune, 3)
            else:
                return self._sendError(400, 'unknown action: %s' % action)
        except Exception as e:
            self.log('action %s failed: %s' % (action, e), xbmc.LOGERROR)
            return self._sendError(500, str(e))
        _publish({'type': 'action', 'action': action})
        return self._sendJSON({'status': 'ok', 'action': action})


    def _sse(self):
        """Server-Sent Events stream — relays _publish() events to browsers."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        try:
            while not self.monitor.abortRequested():
                self.wfile.write(b': ping\n\n')
                self.wfile.flush()
                while True:
                    try: ev = _EVENTS.get_nowait()
                    except queue.Empty: break
                    self.wfile.write(('data: %s\n\n' % FileAccess.dumpJSON(ev)).encode(DEFAULT_ENCODING))
                    self.wfile.flush()
                if self.monitor.waitForAbort(10): break
        except Exception as e:
            self.log('sse ended: %s' % e, xbmc.LOGDEBUG)


    def do_GET(self):
        self.log('do_GET, incoming path = %s' % (self.path))
        path     = self._path()
        query    = self._query()
        compress = 'gzip' in self.headers.get("Accept-Encoding", "")
        try:
            # --- logos: serve the cached image inline (Kodi's CCurlFile::GetMimeType
            # won't follow a 302, so redirecting yields */* and hides the logo) ---
            if path.startswith('/logos/'):
                name = Globals._unquoteString(path.split("/logos/")[1])
                image = self.resources.getImageCache(name)
                if isinstance(image, str) and image.startswith(('http://', 'https://')):
                    # self-hosted /image/ URL -> reuse the /image/ serving logic
                    image = image.split('/image/', 1)[1] if '/image/' in image else image
                return self._serveImage(image)

            # --- skin media: /images/... (HTML injects {{ media_loc }} as a full path) ---
            if path.startswith('/images/'):
                rel = Globals._unquoteString(path.split('/images/', 1)[1])
                if '..' in rel: return self._sendError(400, 'Invalid path')
                full = os.path.join(MEDIA_LOC, os.path.basename(rel.replace('\\', '/')))
                if not FileAccess.exists(full): return self._sendError(404, 'File Not Found [%s]' % self.path)
                return self._sendFile(full, compress)

            # --- remotes static: /remote/... (form.html payload editor, etc.) ---
            if path.startswith('/remote/'):
                rel = Globals._unquoteString(path.split('/remote/', 1)[1])
                if '..' in rel: return self._sendError(400, 'Invalid path')
                full = os.path.join(REMOTE_LOC, rel)
                if not FileAccess.exists(full): return self._sendError(404, 'File Not Found [%s]' % self.path)
                return self._sendFile(full, compress)

            # --- image cache (plus skin-media fallback for {{ media_loc }} injection) ---
            if path.startswith('/image/'):
                return self._serveImage(path.split('/image/')[1])

            # --- core feed files ---
            if path == '/favicon.ico': return self._sendFile(ICON_WEB, compress)
            if path.endswith(Globals.properties.getProcessID()):
                if   M3UFLE.lower() in path:  return self._send(renderFilteredM3U(self.channels, self.runActions, compress), path, ctype='application/vnd.apple.mpegurl', gz=compress, cors=True)
                elif XMLTVFLE.lower() in path:return self._send(renderFilteredXMLTV(self.channels, self.runActions, compress), path, ctype='application/xml', gz=compress, cors=True)
                elif GENREFLE.lower() in path:return self._send(getFilteredGenres(), path, ctype='application/xml', compress=compress, cors=True)
                elif SEASONFLE.lower()  in path: return self._send(FileAccess.dumpJSON(self.wp.seasonal().getSeasonsData()), path, ctype='application/json', compress=compress, cors=True)
                elif HOLIDAYFLE.lower() in path: return self._send(FileAccess.dumpJSON(self.wp.seasonal().getHolidaysData()), path, ctype='application/json', compress=compress, cors=True)
            if   path.endswith(f'/{M3UFLE.lower()}'):  return self._send(renderFilteredM3U(self.channels, self.runActions, compress), path, ctype='application/vnd.apple.mpegurl', gz=compress, cors=True)
            elif path.endswith(f'/{XMLTVFLE.lower()}'):return self._send(renderFilteredXMLTV(self.channels, self.runActions, compress), path, ctype='application/xml', gz=compress, cors=True)
            elif path.endswith(f'/{GENREFLE.lower()}'):return self._send(getFilteredGenres(), path, ctype='application/xml', compress=compress, cors=True)
            elif path.endswith(f'/{SEASONFLE.lower()}'):return self._send(FileAccess.dumpJSON(self.wp.seasonal().getSeasonsData()), path, ctype='application/json', compress=compress, cors=True)
            elif path.endswith(f'/{HOLIDAYFLE.lower()}'):return self._send(FileAccess.dumpJSON(self.wp.seasonal().getHolidaysData()), path, ctype='application/json', compress=compress, cors=True)
            elif path.endswith(f'/{EXTERNALFEEDFLE.lower()}'): return self._sendFile(EXTERNALFEED, compress)
            elif path.startswith('/filelist/'):
                key = path.replace('/filelist/', '')
                data = Globals.settings.getCacheSetting(key, FileAccess._getMD5(key), default=[])
                return self._send(FileAccess.dumpJSON(data).encode(DEFAULT_ENCODING), path, ctype='application/json', compress=compress, cors=True)

            # --- REST API ---
            if path.startswith('/api/'):
                return self._apiGET(path, query, compress)

            # --- HTML pages ---
            if path in ('', '/') or path.endswith('.html'):
                name = 'manager.html'
                for candidate in (MANAGERFLE, 'channels.html', 'channels_new.html', 'form.html'):
                    if path.endswith('/' + candidate) or path == '/' + candidate:
                        name = candidate
                        break
                return self._serveHTML(name)

            return self._sendError(404, "File Not Found [%s]" % self.path)
        except FileNotFoundError:
            self._sendError(404, "File Not Found [%s]" % self.path)
        except Exception as e:
            self.log("do_GET, failed!\n%s" % (e), xbmc.LOGERROR)
            try: self._sendError(500, "Internal Server Error")
            except Exception as e2: self.log("do_GET, error response failed: %s" % e2, xbmc.LOGDEBUG)


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


    def _chkPort(self, host: str, port: int = None, silent: Optional[bool] = None) -> int:
        if port is None:
            port = Globals.settings.getSettingInt('TCP_PORT')
        if silent is None:
            silent = not Globals.settings.showDialog(silent)
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
        if tmpPort != port: Globals.dialog.notificationDialog(LANGUAGE(30097).format(port=port,available=tmpPort), silent=silent)
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
