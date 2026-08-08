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
import gzip, mimetypes, socket, errno, queue

from six.moves.BaseHTTPServer  import BaseHTTPRequestHandler, HTTPServer
from six.moves.socketserver    import ThreadingMixIn
from typing                    import Any, Optional
from zeroconf                  import *
from variables                 import *
from channels                  import Channels
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


    def _send(self, data: Any, path: str = '', code: int = 200, ctype: Optional[str] = None, compress: bool = False, cors: bool = False):
        if isinstance(data, str): data = data.encode(DEFAULT_ENCODING)
        if compress:
            data = gzip.compress(data, compresslevel=5)
        if ctype is None:
            ctype = {'.json':'application/json', '.m3u':'application/vnd.apple.mpegurl',
                     '.xml':'application/xml', '.html':'text/html'}.get(
                        os.path.splitext(path)[1].lower(), mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_response(code)  # status line must precede any headers
        if compress:
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
        if '..' in img: return self._sendError(400, 'Invalid path')
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
    @staticmethod
    def _coerce(value: Any, key: str = '') -> Any:
        """Coerce a form value back into a channel field type."""
        if isinstance(value, (bool, int, float)): return value
        if isinstance(value, list): return [MyHandler._coerce(v) for v in value]
        if isinstance(value, dict): return {k: MyHandler._coerce(v) for k, v in value.items()}
        if isinstance(value, str):
            s = value.strip()
            if key in ('path', 'group'):
                try:
                    v = literal_eval(s)
                    if isinstance(v, list): return v
                except Exception: pass
                return [s] if s else []
            low = s.lower()
            if low in ('on', 'true', '1'): return True
            if low in ('off', 'false', '0', ''): return False
            try: return int(s)
            except Exception: pass
            try: return float(s)
            except Exception: pass
            return value
        return value


    def _saveChannel(self, data: dict):
        if not isinstance(data, dict): return self._sendError(400, 'invalid payload')
        chan = Channels(Globals.getChannelKey(), writable=True)
        nchan = dict(chan.getTemplate())
        rules = {}
        for key, val in data.items():
            if key.startswith('rules.'):
                parts = key.split('.')
                if len(parts) >= 4 and parts[2] == 'values':
                    rid = parts[1]
                    rules.setdefault(rid, {}).setdefault('values', {})['.'.join(parts[3:])] = self._coerce(val)
                continue
            nchan[key] = self._coerce(val, key)
        nchan['rules'] = rules
        try: nchan['number'] = int(nchan.get('number', 0))
        except Exception: nchan['number'] = 0
        if isinstance(nchan.get('path'), str):
            nchan['path'] = [nchan['path']] if nchan['path'] else []
        if not nchan.get('id'):
            nchan['id'] = Globals._getChannelID(nchan.get('name', ''), nchan.get('path', []), nchan['number'], uuid=chan.channelDATA.get('uuid'))
        chans = chan.getChannels()
        num   = nchan['number']
        idx   = next((i for i, c in enumerate(chans) if c.get('number') == num or (nchan['id'] and c.get('id') == nchan['id'])), None)
        if idx is None: chans.append(nchan)
        else:           chans[idx] = dict(chans[idx], **nchan)
        ok = chan.setChannels(list(chan._verify(chans)))
        return self._sendJSON({'status': 'ok' if ok else 'error', 'number': num}, 200 if ok else 400)


    def _saveChannels(self, payload: Any):
        if not isinstance(payload, list): payload = [payload]
        chan = Channels(Globals.getChannelKey(), writable=True)
        ok = chan.setChannels(list(chan._verify(payload)))
        return self._sendJSON({'status': 'ok' if ok else 'error'}, 200 if ok else 400)


    def _searchLogo(self, query: str):
        q = (query or '').strip().lower()
        if not q: return self._sendJSON({'url': ''})
        jsonRPC = self.service.jsonRPC
        arts = []
        try:
            for method, key in (('VideoLibrary.GetMovies', 'movies'), ('VideoLibrary.GetTVShows', 'tvshows')):
                param = {"method": method, "params": {"properties": ["art", "title", "originaltitle"],
                                                      "filter": {"field": "title", "operator": "contains", "value": q}}}
                result = jsonRPC.sendJSON(param).get('result', {})
                arts.extend(item.get('art', {}) for item in result.get(key, []))
        except Exception as e:
            self.log('logo_search failed: %s' % e, xbmc.LOGDEBUG)
        for art in arts:
            for k in ('thumb', 'poster', 'icon', 'landscape', 'fanart'):
                if art.get(k): return self._sendJSON({'url': art[k]})
        return self._sendJSON({'url': ''})


    def _lookupLogo(self, name: str, type: str = ''):
        """Run the addon's full logo resolution (Resources.getLogo lookup=True):
        local folders -> resource addons -> TV show art -> generative. Caches the
        result so the static /logos/{name} URL serves it immediately after."""
        if not name: return self._sendJSON({'url': ''})
        try:
            from resources import Resources
            resources = Resources(self.service)
            url = resources.getLogo({'name': name, 'type': type or 'Custom'}, lookup=True)
            return self._sendJSON({'url': url, 'name': name})
        except Exception as e:
            self.log('logo_lookup failed: %s' % e, xbmc.LOGDEBUG)
            return self._sendJSON({'url': ''})


    def _serversPayload(self) -> dict:
        """serverData guaranteed to include the local instance (always enabled)
        alongside the enabled remote instances discovered via zeroconf."""
        data = Multiroom(service=self.service).serverData
        servers = data.setdefault('servers', {})
        try:
            local = Globals.settings.getBonjour()
            local['enabled'] = True
            local['online']  = True
            servers[local.get('name') or Globals.properties.getFriendlyName()] = local
        except Exception as e:
            self.log('_serversPayload, local instance failed: %s' % e, xbmc.LOGDEBUG)
        return data


    def _verifyUUID(self, uuid: str) -> bool:
        if uuid == Globals.settings.getMYUUID(): return True
        try:
            from multiroom import Multiroom
            return any(s.get('uuid') == uuid for s in list(Multiroom().serverData.values()))
        except Exception: return False


    # ======================= handlers =======================
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


    def do_POST(self):
        self.log('do_POST, incoming path = %s' % (self.path))
        path = self._path()
        try:
            incoming = self._readJSON()
        except Exception as e:
            self.log(f'do_POST, failed to parse incoming body: {e}', xbmc.LOGWARNING)
            incoming = {}

        if path.startswith('/api/'):
            return self._apiPOST(path, incoming)

        if path == '/remote/form.json':  # generic payload editor (form.html)
            payload = incoming.get('payload')
            if isinstance(payload, list):                        return self._saveChannels(payload)
            if isinstance(payload, dict) and isinstance(payload.get('channels'), list):
                return self._saveChannels(payload.get('channels'))
            if isinstance(payload, dict) and ('resume' in payload or 'filelist' in payload):
                Globals.settings.setCacheSetting('form.payload', payload, FileAccess._getMD5('form.payload'), datetime.timedelta(days=84))
                return self._sendJSON({'status': 'ok'})
            return self._sendError(400, 'unrecognized payload')

        if path.startswith('/filelist/'):  # resume data
            if incoming.get('uuid') and not self._verifyUUID(incoming.get('uuid')):
                return self._sendError(403, 'invalid uuid')
            key = path.replace('/filelist/', '')
            Globals.settings.setCacheSetting(key, incoming.get('payload'), FileAccess._getMD5(key), datetime.timedelta(days=84))
            return self._sendJSON({'status': 'ok'})

        return self._sendError(404, 'unknown endpoint: %s' % path)


    def _apiPOST(self, path: str, incoming: dict):
        if path == '/api/save':
            return self._saveChannel(incoming.get('payload', incoming))
        if path in (f'/api/{CHANNELFLE}', '/api/channels'):
            if incoming.get('uuid') and not self._verifyUUID(incoming.get('uuid')):
                return self._sendError(403, 'invalid uuid')
            _publish({'type': 'channels.saved', 'count': len(incoming.get('payload', incoming.get('channels', [])) or [])})
            return self._saveChannels(incoming.get('payload', incoming.get('channels')))
        if path == '/api/settings':
            return self._updateSettings(incoming.get('payload', incoming))
        if path == '/api/actions':
            return self._runAction(incoming)
        if path == '/api/imports':
            return self._manageImports('POST', incoming)
        if path == '/api/backups':
            return self._manageBackups('POST', incoming)
        if path == '/api/seasons':
            ok = self._seasonal().setSeasonsData(incoming.get('payload', incoming))
            _publish({'type': 'seasons.saved'})
            return self._sendJSON({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        if path == '/api/holidays':
            ok = self._seasonal().setHolidaysData(incoming.get('payload', incoming))
            _publish({'type': 'holidays.saved'})
            return self._sendJSON({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        if path.startswith('/api/channels/'):
            return self._channelCRUD('PUT', path, incoming)
        return self._sendError(404, 'unknown api: %s' % path)


    def _apiGET(self, path: str, query: dict, compress: bool):
        ch_key = Globals.getChannelKey()
        routes = {
            f'/api/{BONJOURFLE}': lambda: Globals.settings.getBonjour(),
            f'/api/{SERVERFLE}':  lambda: self._serversPayload(),
            f'/api/{LIBRARYFLE}': lambda: Library(self.service).getLibrary(),
            f'/api/{CHANNELFLE}': lambda: Channels(ch_key).getChannels(),
            f'/api/{PVRFLE}':     lambda: dict(Globals.settings.instances.updatePVRStatus(Globals.properties.getRemoteHost(), Globals.properties.getFriendlyName()),
                                               playback=self._playbackJSON()),
            f'/api/{LOGSFLE}':    lambda: Globals.builtin.parseKodiLog(),
            '/api/channels':      lambda: Channels(ch_key).getChannels(),
            '/api/template':      lambda: Channels(ch_key).getTemplate(),
            '/api/bonjour':       lambda: Globals.settings.getBonjour(),
            '/api/settings':      lambda: self._currentSettings(),
            '/api/rules':         lambda: self._rulesJSON(),
            '/api/system':        lambda: self._systemInfo(),
            '/api/playback':      lambda: self._playbackJSON(),
            '/api/build':         lambda: self._buildStatus(),
            '/api/guide':         lambda: self._guideJSON(),
            '/api/imports':       lambda: self._manageImports('GET'),
            '/api/backups':       lambda: self._manageBackups('GET'),
            '/api/seasons':       lambda: self._seasonal().getSeasonsData(),
            '/api/holidays':      lambda: self._seasonal().getHolidaysData(),
        }
        if path in routes:
            return self._sendJSON(routes[path](), cors=True)
        if path == '/api/xmltv':
            return self._send(renderFilteredXMLTV(self.channels, self.runActions), path, ctype='application/xml', compress=compress, cors=True)
        if path == '/api/logo_search':
            return self._searchLogo(query.get('q', ''))
        if path == '/api/logo_lookup':
            return self._lookupLogo(query.get('name', ''), query.get('type', ''))
        if path == '/api/events':
            return self._sse()
        if path.startswith('/api/channels/'):
            return self._channelCRUD('GET', path)
        return self._sendError(404, 'unknown api: %s' % path)


    # ======================= extended API endpoints =======================
    def _buildStatus(self) -> dict:
        """Channel-build progress + background queue summary for the manager widget."""
        queue = getattr(self.service, 'queue', None)
        running, pending = [], 0
        if queue is not None:
            try:
                running = [getattr(task, 'func', None).__name__ for task in queue.running.values()]
                pending = len(queue.heap)
            except Exception as e:
                self.log('buildStatus queue failed: %s' % e, xbmc.LOGDEBUG)
        build = getattr(self.service, 'buildState', None) or {}
        building = bool(build.get('running', False))
        return {
            'building': building,
            'pct': build.get('pct', 0),
            'channel': build.get('channel', ''),
            'logo': build.get('logo', ''),
            'built': build.get('built', 0),
            'total': build.get('total', 0),
            'running': running,
            'pending': pending,
            'idle': not building and not running and pending == 0,
        }


    def _currentSettings(self) -> dict:
        settings = Globals.settings.getCurrentSettings()
        for k in ('Remote_NAME', 'Remote_M3U', 'Remote_XMLTV', 'Remote_GENRE', 'Min_Days',
                  'Max_Days', 'Enable_Grouping', 'Remote_Status', 'Enable_Executor'):
            try: settings[k] = Globals.settings.getSetting(k)
            except Exception: pass
        return settings


    def _updateSettings(self, data: dict):
        if not isinstance(data, dict): return self._sendError(400, 'invalid payload')
        for k, v in data.items():
            try:
                if   isinstance(v, bool): Globals.settings.setSettingBool(k, v)
                elif isinstance(v, int):  Globals.settings.setSettingInt(k, v)
                else:                     Globals.settings.setSetting(k, str(v))
            except Exception as e:
                self.log('settings update failed %s: %s' % (k, e), xbmc.LOGDEBUG)
        _publish({'type': 'settings.updated', 'keys': list(data.keys())})
        return self._sendJSON({'status': 'ok'})


    def _rulesJSON(self) -> list:
        out = []
        for rule in RulesList().allRules():
            out.append({'myId': rule.myId, 'name': rule.name, 'description': rule.description,
                        'optionLabels': rule.optionLabels, 'optionValues': rule.optionValues,
                        'selectBoxOptions': getattr(rule, 'selectBoxOptions', [])})
        return out


    def _systemInfo(self) -> dict:
        import platform as _platform
        info = {'name': Globals.properties.getFriendlyName(),
                'host': Globals.properties.getRemoteHost(),
                'addon': ADDON_NAME, 'version': ADDON_VERSION,
                'channel_key': Globals.getChannelKey(), 'channels': len(self.channels),
                'python': _platform.python_version(), 'machine': _platform.machine(),
                'os': _platform.platform(), 'uuid': Globals.settings.getMYUUID(),
                'author': ADDON_AUTHOR,
                'github': URL_GITHUB, 'wiki': URL_WIKI, 'support': URL_SUPPORT,
                'readme_url': URL_README, 'changelog_url': URL_CHANGELOG,
                'readme': self._readFile(README_FLE),
                'changelog': self._readFile(CHANGELOG_FLE)}
        try:
            from constants import TOTAL_RAM_GB, CPU_COUNT, IS_CONSTRAINED_SOC
            info.update({'ram_gb': TOTAL_RAM_GB, 'cpus': CPU_COUNT, 'constrained_soc': IS_CONSTRAINED_SOC})
        except Exception: pass
        return info


    def _readFile(self, path: str, limit: int = 20000) -> str:
        try:
            with FileAccess.stream(path) as fle:
                txt = fle.read()
            if isinstance(txt, bytes): txt = txt.decode(DEFAULT_ENCODING, 'replace')
            return txt[:limit]
        except Exception:
            return ''


    def _playbackJSON(self) -> dict:
        """Lightweight live playback snapshot for the manager UI.

        Read from the running service's Player (playingItem keeps the current
        channel/item dicts fresh across channel changes). Everything returned is
        JSON-safe: sets/slices are normalized and only whitelisted keys kept.
        """
        player = getattr(self.service, 'player', None)
        out = {'is_playing': False, 'is_pseudotv': False, 'provider': None,
               'channel': None, 'item': {}}
        try:
            if player is None or not player.isPlaying(): return out
            item = dict(getattr(player, 'playingItem', None) or {})
            out['is_playing'] = True
            out['is_pseudotv'] = bool(item.get('isPseudoTV', False))
            citem = item.get('citem') or {}
            fitem = item.get('fitem') or {}
            out['channel'] = {'name': citem.get('name'), 'number': citem.get('number'),
                              'id': citem.get('id'), 'logo': citem.get('logo', '')}
            if out['is_pseudotv']:
                out['provider'] = "%s (%s)" % (ADDON_NAME, Globals.properties.getFriendlyName())
            else:
                out['provider'] = item.get('provider') or Globals.builtin.getInfoLabel('PVR.BackendName') or None
            out['item'] = {k: fitem.get(k) for k in
                           ('title', 'thumb', 'logo', 'plot', 'genre', 'year', 'runtime',
                            'season', 'episode', 'file') if fitem.get(k) is not None}
            if not out['item'] and citem:  # channel-level fallback for radio/unknown
                out['item'] = {'title': citem.get('name'), 'thumb': citem.get('logo', ''),
                               'genre': citem.get('group')}
        except Exception as e:
            self.log(f"_playbackJSON failed: {e}", xbmc.LOGDEBUG)
        return out


    def _seasonal(self):
        from seasonal import Seasonal
        return Seasonal()


    @staticmethod
    def _first(value: Any, default: str = ''):
        if isinstance(value, list):
            if not value: return default
            item = value[0]
            return item[0] if isinstance(item, (list, tuple)) and item else item
        return value if value is not None else default


    def _guideJSON(self) -> dict:
        try:
            from xmltvs import XMLTVS
            xml = XMLTVS()
            out = {'channels': [], 'programmes': []}
            for ch in xml.getChannels()[:300]:
                icon = ch.get('icon') or []
                icon_src = icon[0].get('src') if isinstance(icon, list) and icon and isinstance(icon[0], dict) else (ch.get('logo') or '')
                out['channels'].append({'id': ch.get('id'), 'name': self._first(ch.get('display-name')), 'logo': icon_src})
            for p in xml.getProgrammes()[:2000]:
                out['programmes'].append({'channel': p.get('channel'), 'start': p.get('start'), 'stop': p.get('stop'),
                                          'title': self._first(p.get('title')),
                                          'genre': [self._first(g) for g in (p.get('category') or [])]})
            return out
        except Exception as e:
            self.log('guide failed: %s' % e, xbmc.LOGDEBUG)
            return {'channels': [], 'programmes': []}


    def _channelCRUD(self, method: str, path: str, incoming: Optional[dict] = None):
        cid = Globals._unquoteString(path.split('/api/channels/', 1)[1])
        if not cid: return self._sendError(400, 'missing channel id')
        chan = Channels(Globals.getChannelKey(), writable=True)
        chans = chan.getChannels()
        if method == 'GET':
            for c in chans:
                if c.get('id') == cid: return self._sendJSON(c, cors=True)
            return self._sendError(404, 'channel not found')
        if method == 'PUT':
            if not isinstance(incoming, dict): return self._sendError(400, 'invalid payload')
            channel = incoming.get('payload', incoming)
            if not isinstance(channel, dict): return self._sendError(400, 'invalid channel')
            for i, c in enumerate(chans):
                if c.get('id') == cid:
                    chans[i] = dict(c, **channel)
                    break
            else:
                channel['id'] = cid
                chans.append(channel)
            ok = chan.setChannels(list(chan._verify(chans)))
            _publish({'type': 'channel.updated', 'id': cid})
            return self._sendJSON({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        if method == 'DELETE':
            chans = [c for c in chans if c.get('id') != cid]
            ok = chan.setChannels(list(chan._verify(chans)))
            _publish({'type': 'channel.deleted', 'id': cid})
            return self._sendJSON({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        return self._sendError(405, 'method not allowed')


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


    def _manageImports(self, method: str, incoming: Optional[dict] = None):
        try:
            from backup import Backup
            backup = Backup()
            if method == 'GET':
                return self._sendJSON({'imports': backup.getImports()}, cors=True)
            fle = (incoming.get('payload', {}) or {}).get('file') if isinstance(incoming.get('payload'), dict) else incoming.get('file')
            ok = backup.importChannels(fle) if fle else False
            return self._sendJSON({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        except Exception as e:
            self.log('imports %s failed: %s' % (method, e), xbmc.LOGERROR)
            return self._sendError(500, str(e))


    def _manageBackups(self, method: str, incoming: Optional[dict] = None):
        try:
            from backup import Backup
            backup = Backup()
            if method == 'GET':
                return self._sendJSON({'backups': backup.getBackups()}, cors=True)
            ok = backup.backupChannels()
            return self._sendJSON({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        except Exception as e:
            self.log('backups %s failed: %s' % (method, e), xbmc.LOGERROR)
            return self._sendError(500, str(e))


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
                if   M3UFLE.lower() in path:  return self._send(renderFilteredM3U(self.channels, self.runActions), path, ctype='application/vnd.apple.mpegurl', compress=compress, cors=True)
                elif XMLTVFLE.lower() in path:return self._send(renderFilteredXMLTV(self.channels, self.runActions), path, ctype='application/xml', compress=compress, cors=True)
                elif GENREFLE.lower() in path:return self._send(getFilteredGenres(), path, ctype='application/xml', compress=compress, cors=True)
                elif SEASONFLE.lower()  in path: return self._send(FileAccess.dumpJSON(self._seasonal().getSeasonsData()), path, ctype='application/json', compress=compress, cors=True)
                elif HOLIDAYFLE.lower() in path: return self._send(FileAccess.dumpJSON(self._seasonal().getHolidaysData()), path, ctype='application/json', compress=compress, cors=True)
            if   path.endswith(f'/{M3UFLE.lower()}'):  return self._send(renderFilteredM3U(self.channels, self.runActions), path, ctype='application/vnd.apple.mpegurl', compress=compress, cors=True)
            elif path.endswith(f'/{XMLTVFLE.lower()}'):return self._send(renderFilteredXMLTV(self.channels, self.runActions), path, ctype='application/xml', compress=compress, cors=True)
            elif path.endswith(f'/{GENREFLE.lower()}'):return self._send(getFilteredGenres(), path, ctype='application/xml', compress=compress, cors=True)
            elif path.endswith(f'/{SEASONFLE.lower()}'):return self._send(FileAccess.dumpJSON(self._seasonal().getSeasonsData()), path, ctype='application/json', compress=compress, cors=True)
            elif path.endswith(f'/{HOLIDAYFLE.lower()}'):return self._send(FileAccess.dumpJSON(self._seasonal().getHolidaysData()), path, ctype='application/json', compress=compress, cors=True)
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
        except FileNotFoundError: self._sendError(404, "File Not Found [%s]" % self.path)
        except Exception as e:
            self.log("do_GET, failed!\n%s" % (e), xbmc.LOGERROR)
            self._sendError(500, "Internal Server Error")


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
