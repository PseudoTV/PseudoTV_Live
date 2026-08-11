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
"""Channel-manager API used by the web manager (manager.html Channels tab).

Every method mirrors the Kodi-side manager.py flow (validateInputs, getPaths,
setName/Logo, browseSources) but returns HTTP-ready payloads. The HTTP server
wraps the (payload, code) tuples it receives.
"""
from typing import Any, Optional

from variables     import *
from channels      import Channels


class ChannelManager(object):

    def __init__(self, service: Any = None):
        self.service = service
        self.jsonRPC = getattr(service, 'jsonRPC', None)
        self._browse_flood = []  # [(ts, method)] recent browser JSON-RPC calls for flood detection


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    @staticmethod
    def _first(value: Any, default: str = ''):
        if isinstance(value, list):
            if not value: return default
            item = value[0]
            return item[0] if isinstance(item, (list, tuple)) and item else item
        return value if value is not None else default


    @staticmethod
    def _channelNum(cid) -> Any:
        """Channel number from the xmltv id (hex of 'NN.Name...@host')."""
        try:
            hexpart = str(cid).split('@')[0]
            decoded = bytes.fromhex(hexpart).decode('utf-8', 'replace') if hexpart else ''
            m = re.match(r'\d+', decoded)
            return int(m.group(0)) if m else ''
        except Exception:
            return ''


    @staticmethod
    def _coerce(value: Any, key: str = '') -> Any:
        """Coerce a form value back into a channel field type."""
        if isinstance(value, (bool, int, float)): return value
        if isinstance(value, list): return [ChannelManager._coerce(v) for v in value]
        if isinstance(value, dict): return {k: ChannelManager._coerce(v) for k, v in value.items()}
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


    @staticmethod
    def _redactCreds(url: str) -> str:
        """Strip user:pass@ from VFS URLs so credentials never leak to the manager."""
        try:
            if '://' in url:
                head, rest = url.split('://', 1)
                if '@' in rest:
                    rest = rest.split('@', 1)[1]
                    url = '%s://%s' % (head, rest)
        except Exception:
            pass
        return url


    def channels(self) -> list:
        return Channels(Globals.getChannelKey()).getChannels()


    def saveChannel(self, data: dict) -> tuple:
        if not isinstance(data, dict): return ({'error': 'invalid payload', 'status': 400}, 400)
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
        return ({'status': 'ok' if ok else 'error', 'number': num}, 200 if ok else 400)


    def validateChannel(self, citem: dict) -> dict:
        """Run the Manager.validateInputs-equivalent pipeline on one channel:
        name sanitize + length, setName fallback from path, path normalization,
        group cleaning, rules shape. Mirrors manager.py setName/validateInputs."""
        if not isinstance(citem, dict):
            return {}
        try:
            name = str(citem.get('name') or '').strip()
            if name and (1 < len(name) < 128):
                citem['name'] = Globals._validString(name)
            elif citem.get('path'):
                first = citem['path'][0] if isinstance(citem['path'], list) and citem['path'] else citem.get('path')
                if isinstance(first, str) and first.strip():
                    if first.rstrip('/').endswith(('.xml', '.xsp')):
                        try:
                            from xsp import XSP
                            citem['name'] = XSP().getName(first)
                        except Exception:
                            citem['name'] = os.path.basename(os.path.dirname(first)).strip('/')
                    else:
                        citem['name'] = os.path.basename(os.path.dirname(first)).strip('/')
            paths = citem.get('path')
            if isinstance(paths, str):
                citem['path'] = [paths] if paths else []
            elif not isinstance(paths, list):
                citem['path'] = []
            citem = Globals._cleanGroups(citem)
            if not isinstance(citem.get('rules'), dict):
                citem['rules'] = {}
            return citem
        except Exception as e:
            self.log('validateChannel failed: %s' % e, xbmc.LOGDEBUG)
            return citem


    def saveChannels(self, payload: Any) -> tuple:
        if not isinstance(payload, list): payload = [payload]
        chan = Channels(Globals.getChannelKey(), writable=True)
        try:
            # Verify config through the manager.py flow: _verify fills template keys
            # + rules migration, _validateChannel sanitizes name/setName/groups, then
            # addChannel dedups by id. Full-list save so manager deletions persist.
            cleaned = [self.validateChannel(c) for c in chan._verify(payload)]
            chan.channelDATA['channels'] = []
            for citem in cleaned:
                chan.addChannel(citem)
            ok = chan.setChannels()
        except Exception as e:
            self.log('save channels failed: %s' % e, xbmc.LOGDEBUG)
            return ({'status': 'error', 'error': str(e)}, 400)
        return ({'status': 'ok' if ok else 'error'}, 200 if ok else 400)


    def verifyUUID(self, uuid: str) -> bool:
        try:
            return uuid == Globals.settings.getMYUUID()
        except Exception:
            return False


    def groups(self) -> dict:
        """Available channel groups: shipped GROUP_TYPES plus User_Groups setting."""
        types = list(GROUP_TYPES)
        try:
            user = [g for g in str(Globals.settings.getSetting('User_Groups') or '').split('|') if g]
        except Exception:
            user = []
        return {'types': types, 'user': user}


    def addGroup(self, incoming: dict) -> dict:
        """Append a manually typed group to the User_Groups setting."""
        group = str((incoming.get('payload', incoming) or {}).get('group') or '').strip()
        if not group or group in GROUP_TYPES:
            return {'status': 'ok'}
        try:
            current = str(Globals.settings.getSetting('User_Groups') or '')
            groups = [g for g in current.split('|') if g]
            if group not in groups:
                groups.append(group)
                Globals.settings.setSetting('User_Groups', '|'.join(groups))
        except Exception as e:
            self.log('addGroup failed: %s' % e, xbmc.LOGDEBUG)
            return {'status': 'error'}
        return {'status': 'ok'}


    def browsePath(self, path: str = ''):
        """List media sources (root) or a directory's files/folders for the
        channel-path browser. Mirrors Manager.getPaths' browseSources (Kodi's
        'show all sources' browse). Uses the webserver JSON-RPC path so a slow
        network listing doesn't block Kodi's main thread."""
        jsonRPC = self.jsonRPC
        self._checkFlood(path)
        try:
            if not path:
                items, seen = [], set()
                for media in ('video', 'music', 'pictures', 'programs', 'files'):
                    try:
                        cmd = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetSources', 'params': {'media': media}}
                        result = (jsonRPC._httpJSONRPC(cmd, 15) or {}).get('result', {})
                        for s in result.get('sources', []):
                            fp = self._redactCreds(s.get('file', ''))
                            if fp and fp not in seen:
                                seen.add(fp)
                                items.append({'label': s.get('label', '') or fp, 'file': fp, 'dir': True})
                    except Exception as me:
                        self.log('browse sources (%s) failed: %s' % (media, me), xbmc.LOGDEBUG)
                return {'path': '', 'parent': None, 'items': items}
            cmd = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory',
                   'params': {'directory': path, 'media': 'files',
                              'properties': ['title', 'file']}}
            result = (jsonRPC._httpJSONRPC(cmd, 15) or {}).get('result', {})
            items = []
            for f in result.get('files', []):
                is_dir = f.get('filetype') == 'directory'
                fp = f.get('file', '')
                items.append({'label': f.get('label') or fp.rstrip('/\\').rsplit('/', 1)[-1] or fp,
                              'file': self._redactCreds(fp), 'dir': is_dir})
            parent = None
            stripped = path.rstrip('/\\')
            if stripped:
                sep = '/' if '/' in stripped else '\\'
                cut = stripped.rfind(sep)
                if cut > 0:
                    parent = stripped[:cut]
                else:
                    parent = '' if '://' in stripped else None
            return {'path': path, 'parent': parent, 'items': items}
        except Exception as e:
            self.log('browse failed: %s' % e, xbmc.LOGDEBUG)
            return {'path': path, 'parent': None, 'items': []}


    def _checkFlood(self, path: str):
        """Watch for the channel browser hammering Kodi's JSON-RPC web endpoint.

        A legit browser user walks the tree one click at a time (~1 req per
        browse). A flood is many requests in a few seconds — a stuck loop, an
        aggressive automation, or a compromised client. Non-blocking: just logs a
        throttled warning so a storm is visible in kodi.log without slowing it.
        """
        now = time.time()
        self._browse_flood = [t for t in self._browse_flood if now - t[0] <= 5.0]
        self._browse_flood.append((now, path))
        if len(self._browse_flood) >= 8:
            self._browse_flood = []
            self.log(f"_checkFlood, browser flood detected (8+ requests in 5s), last: {path}",
                     xbmc.LOGWARNING)


    def searchLogo(self, query: str) -> dict:
        q = (query or '').strip().lower()
        if not q: return {'url': ''}
        jsonRPC = self.jsonRPC
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
                if art.get(k): return {'url': art[k]}
        return {'url': ''}


    def lookupLogo(self, name: str, type: str = '') -> dict:
        if not name: return {'url': ''}
        try:
            from resources import Resources
            resources = Resources(self.service)
            url = resources.getLogo({'name': name, 'type': type or 'Custom'}, lookup=True)
            return {'url': url, 'name': name}
        except Exception as e:
            self.log('logo_lookup failed: %s' % e, xbmc.LOGDEBUG)
            return {'url': ''}


    def selectLogo(self, name: str, type: str = '') -> dict:
        if not name: return {'logos': []}
        try:
            from resources import Resources
            resources = Resources(self.service)
            logos = [l for l in (resources.selectLogo({'name': name, 'type': type or 'Custom'}) or []) if l]
            out = [{'name': logo, 'url': Globals._toWebImage(logo)} for logo in logos]
            return {'logos': out, 'name': name}
        except Exception as e:
            self.log('logo_select failed: %s' % e, xbmc.LOGDEBUG)
            return {'logos': []}


    def currentSettings(self) -> dict:
        settings = Globals.settings.getCurrentSettings()
        for k in ('Remote_NAME', 'Remote_M3U', 'Remote_XMLTV', 'Remote_GENRE', 'Min_Days',
                  'Max_Days', 'Enable_Grouping', 'Remote_Status', 'Enable_Executor'):
            try: settings[k] = Globals.settings.getSetting(k)
            except Exception: pass
        # Booleans the manager reads (autotune banner etc.) must be real bools —
        # a 'false' string is truthy in JS and always showed the disable banner.
        for k in ('Enable_Autotune', 'Enable_Executor'):
            try: settings[k] = Globals.settings.getSettingBool(k)
            except Exception: pass
        return settings


    def migrateAutotune(self) -> bool:
        """When autotune is disabled, copy the autotuned channels into the user key
        (only if the user list is empty) so disabling never leaves an empty set."""
        try:
            if Globals.settings.getSettingBool('Enable_Autotune'):
                return False
            autotune = Channels(CHANNEL_KEY_AUTOTUNE).getChannels()
            if not autotune:
                return False
            user = Channels(CHANNEL_KEY_USER)
            if user.getChannels():
                return False  # user already has channels — never clobber
            # Write through the Channels class (writable so _save persists) — this
            # uses the versioned key (Channels.1.0.0) that Channels() reads.
            Channels(CHANNEL_KEY_USER, writable=True).setChannels(autotune)
            Globals.properties.setBackup(CHANNEL_KEY_USER, autotune)
            Globals.properties.setPendingRestart()
            self.log('autotune disabled: copied %d channels to user config + pending restart' % len(autotune), xbmc.LOGINFO)
            return True
        except Exception as e:
            self.log('migrateAutotune failed: %s' % e, xbmc.LOGWARNING)
            return False


    def channelCRUD(self, method: str, path: str, incoming: Optional[dict] = None) -> Optional[tuple]:
        cid = Globals._unquoteString(path.split('/api/channels/', 1)[1])
        if not cid: return ({'error': 'missing channel id', 'status': 400}, 400)
        chan = Channels(Globals.getChannelKey(), writable=True)
        chans = chan.getChannels()
        if method == 'GET':
            for c in chans:
                if c.get('id') == cid: return (c, 200)
            return ({'error': 'channel not found', 'status': 404}, 404)
        if method == 'PUT':
            if not isinstance(incoming, dict): return ({'error': 'invalid payload', 'status': 400}, 400)
            channel = incoming.get('payload', incoming)
            if not isinstance(channel, dict): return ({'error': 'invalid channel', 'status': 400}, 400)
            for i, c in enumerate(chans):
                if c.get('id') == cid:
                    chans[i] = dict(c, **channel)
                    break
            else:
                channel['id'] = cid
                chans.append(channel)
            ok = chan.setChannels(list(chan._verify(chans)))
            return ({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        if method == 'DELETE':
            chans = [c for c in chans if c.get('id') != cid]
            ok = chan.setChannels(list(chan._verify(chans)))
            return ({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        return ({'error': 'method not allowed', 'status': 405}, 405)


class WebPoint(object):
    """HTML/web-manager endpoints that are exclusive to the browser UI (System
    Info, Guide, Now Playing, build widget, rules, imports/backups, server list).
    Returns HTTP-ready payloads; the HTTP server wraps them."""

    def __init__(self, service: Any = None):
        self.service = service
        self.jsonRPC = getattr(service, 'jsonRPC', None)
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    # ---- Seasonal/holiday sync to remote instances --------------------------
    # Seasons/holidays are local-first (stored in cache.db), but a user editing
    # them from the manager expects the change to reach every enabled PseudoTV
    # instance. On save we push the payload to all online remotes; offline ones
    # get the payload queued (cache.db) and flushed when they come back online.

    SEASONAL_SYNC_KEY = 'seasonal.syncQue'

    def _syncRemotes(self) -> list:
        """List of {name, host, uuid} enabled remote instances (excludes self)."""
        try:
            from multiroom import Multiroom
            mr = Multiroom(service=self.service)
            self_host = Globals.properties.getRemoteHost()
            remotes = []
            for name, srv in (mr.serverData.get('servers', {}) or {}).items():
                if not srv.get('enabled') or not srv.get('host'): continue
                if srv.get('host') == self_host: continue
                remotes.append({'name': name, 'host': srv['host'], 'uuid': srv.get('uuid', '')})
            return remotes
        except Exception as e:
            self.log('_syncRemotes failed: %s' % e, xbmc.LOGDEBUG)
            return []

    def _pushSeasonal(self, kind: str, payload: Any, remote: dict) -> bool:
        """POST one seasonal payload to one remote instance. Returns True on success."""
        try:
            if not self.jsonRPC: return False
            header = {'Content-Type': 'application/json'}
            if remote.get('uuid'): header['Authorization'] = 'Bearer %s' % remote['uuid']
            url = 'http://%s/api/%s' % (remote['host'], kind)
            result = self.jsonRPC.requestURL(url, payload={'payload': payload}, header=header, timeout=8)
            return result is not None
        except Exception as e:
            self.log('_pushSeasonal %s -> %s failed: %s' % (kind, remote.get('host'), e), xbmc.LOGDEBUG)
            return False

    def syncSeasonalToRemotes(self, kind: str, payload: Any):
        """Push a just-saved seasons/holidays payload to all enabled remotes.

        Online remotes receive it immediately; offline remotes are queued under
        SEASONAL_SYNC_KEY (by host) for flushSeasonalSync to deliver later.
        """
        try:
            remotes = self._syncRemotes()
            queued = Globals.settings.getCacheSetting(self.SEASONAL_SYNC_KEY, default={}) or {}
            for remote in remotes:
                if self._pushSeasonal(kind, payload, remote):
                    queued.get(remote['name'], {}).pop(kind, None)
                else:
                    queued.setdefault(remote['name'], {})[kind] = payload
            # drop empty per-name buckets
            for name in [n for n, v in queued.items() if not v]:
                queued.pop(name, None)
            Globals.settings.setCacheSetting(self.SEASONAL_SYNC_KEY, queued, life=-1)
            self.log('syncSeasonalToRemotes, %s pushed to %d remotes, %d queued' % (
                kind, len(remotes) - sum(1 for r in remotes if any(queued.get(r['name'], {}).values())), len(remotes)))
        except Exception as e:
            self.log('syncSeasonalToRemotes failed: %s' % e, xbmc.LOGDEBUG)

    def flushSeasonalSync(self):
        """Deliver queued seasonal payloads to remotes that have come back online."""
        try:
            queued = Globals.settings.getCacheSetting(self.SEASONAL_SYNC_KEY, default={}) or {}
            if not queued: return
            by_host = {r['name']: r for r in self._syncRemotes()}
            still = {}
            for name, kinds in queued.items():
                remote = by_host.get(name)
                if not remote:
                    still[name] = kinds  # no longer a configured/enabled remote — keep
                    continue
                for kind, payload in kinds.items():
                    if self._pushSeasonal(kind, payload, remote):
                        kinds.pop(kind, None)
                if kinds: still[name] = kinds
            Globals.settings.setCacheSetting(self.SEASONAL_SYNC_KEY, still, life=-1)
            self.log('flushSeasonalSync, %d queued deliveries remaining' % sum(len(v) for v in still.values()))
        except Exception as e:
            self.log('flushSeasonalSync failed: %s' % e, xbmc.LOGDEBUG)


    # ---- Playback resume list ------------------------------------------------
    # Resume entries are cached per-key under RESUME_INDEX (set of key names),
    # each key holding {'resume': {...}, 'filelist': [...]}. Expose them as a
    # flat list so the manager's Resume tab renders one entry per key without
    # N round-trips to /filelist/<key>.
    def resumeJSON(self) -> list:
        try:
            from constants import RESUME_INDEX
            keys = Globals.settings.getCacheSetting(RESUME_INDEX, FileAccess._getMD5(RESUME_INDEX), default=set()) or set()
            entries = []
            for key in keys:
                try:
                    data = Globals.settings.getCacheSetting(key, FileAccess._getMD5(key), default={}) or {}
                    resume = data.get('resume') or {}
                    filelist = data.get('filelist') or []
                    entries.append({
                        'key'    : key,
                        'url'    : 'http://%s/filelist/%s' % (Globals.properties.getRemoteHost(), key),
                        'file'   : resume.get('file', ''),
                        'idx'    : resume.get('idx', 0),
                        'position': resume.get('position', 0.0),
                        'total'  : resume.get('total', 0.0),
                        'instance': (resume.get('updated') or {}).get('instance', ''),
                        'time'   : (resume.get('updated') or {}).get('time', -1),
                        'count'  : len(filelist),
                    })
                except Exception as e:
                    self.log('resumeJSON, skip %s: %s' % (key, e), xbmc.LOGDEBUG)
            # most recent first
            entries.sort(key=lambda e: e.get('time', -1), reverse=True)
            return entries
        except Exception as e:
            self.log('resumeJSON failed: %s' % e, xbmc.LOGDEBUG)
            return []


    @staticmethod
    def first(value: Any, default: str = ''):
        if isinstance(value, list):
            if not value: return default
            item = value[0]
            return item[0] if isinstance(item, (list, tuple)) and item else item
        return value if value is not None else default

    @staticmethod
    def channelNum(cid) -> Any:
        try:
            hexpart = str(cid).split('@')[0]
            decoded = bytes.fromhex(hexpart).decode('utf-8', 'replace') if hexpart else ''
            m = re.match(r'\d+', decoded)
            return int(m.group(0)) if m else ''
        except Exception:
            return ''

    def serversPayload(self) -> dict:
        from multiroom import Multiroom
        data = Multiroom(service=self.service).serverData
        servers = data.setdefault('servers', {})
        try:
            local = Globals.settings.getBonjour()
            local['enabled'] = True
            local['online']  = True
            servers[local.get('name') or Globals.properties.getFriendlyName()] = local
        except Exception as e:
            self.log('serversPayload, local instance failed: %s' % e, xbmc.LOGDEBUG)
        return data

    def rulesJSON(self) -> list:
        from rules import RulesList
        out = []
        for rule in RulesList().allRules():
            out.append({'myId': rule.myId, 'name': rule.name, 'description': rule.description,
                        'optionLabels': rule.optionLabels, 'optionValues': rule.optionValues,
                        'selectBoxOptions': getattr(rule, 'selectBoxOptions', [])})
        return out

    def readFile(self, path: str, limit: int = 20000) -> str:
        try:
            with FileAccess.stream(path) as fle:
                txt = fle.read()
            if isinstance(txt, bytes): txt = txt.decode(DEFAULT_ENCODING, 'replace')
            return txt[:limit]
        except Exception:
            return ''

    def systemInfo(self) -> dict:
        import platform as _platform
        from channels import Channels
        info = {'name': Globals.properties.getFriendlyName(),
                'host': Globals.properties.getRemoteHost(),
                'addon': ADDON_NAME, 'version': ADDON_VERSION,
                'channel_key': Globals.getChannelKey(),
                'channels': len(Channels(Globals.getChannelKey()).getChannels()),
                'python': _platform.python_version(), 'machine': _platform.machine(),
                'os': _platform.platform(), 'uuid': Globals.settings.getMYUUID(),
                'author': ADDON_AUTHOR,
                'github': URL_GITHUB, 'wiki': URL_WIKI, 'support': URL_SUPPORT,
                'readme_url': URL_README, 'changelog_url': URL_CHANGELOG,
                'readme': self.readFile(README_FLE),
                'changelog': self.readFile(CHANGELOG_FLE)}
        try:
            from constants import TOTAL_RAM_GB, CPU_COUNT, IS_CONSTRAINED_SOC
            info.update({'ram_gb': TOTAL_RAM_GB, 'cpus': CPU_COUNT, 'constrained_soc': IS_CONSTRAINED_SOC})
        except Exception: pass
        return info

    def playbackJSON(self) -> dict:
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
            if not out['item'] and citem:
                out['item'] = {'title': citem.get('name'), 'thumb': citem.get('logo', ''),
                               'genre': citem.get('group')}
            try:
                cur = player.getTime(); total = player.getTotalTime()
                if cur is not None and total:
                    out['progress'] = {'time': max(0, int(cur)), 'total': int(total),
                                       'pct': max(0, min(100, int(cur * 100 / total)))}
            except Exception:
                pass
        except Exception as e:
            self.log('playbackJSON failed: %s' % e, xbmc.LOGDEBUG)
        return out

    def seasonal(self):
        from seasonal import Seasonal
        return Seasonal()

    def buildStatus(self) -> dict:
        queue = getattr(self.service, 'queue', None)
        running, pending, running_more = [], 0, 0
        if queue is not None:
            try:
                running = [getattr(task, 'func', None).__name__ for task in queue.running.values()]
                running = list(dict.fromkeys(n for n in running if n))
                running_more = max(0, len(running) - 4)
                running = running[:4]
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
            'running_more': running_more,
            'pending': pending,
            'idle': not building and not running and pending == 0,
        }

    def guideJSON(self, page: int = 0) -> dict:
        PAGE = 10
        try:
            from xmltvs import XMLTVS
            import datetime as _dt
            xml = XMLTVS()
            # Sort by channel number ascending so the guide reads top-to-bottom
            # like a real TV listing (Ch 1 first). Pagination slices this sorted
            # list, keeping pages contiguous in number order.
            def _num(ch):
                try: return int(self.channelNum(ch.get('id')))
                except Exception: return None
            channels = sorted(xml.getChannels(), key=lambda ch: (_num(ch) is None, _num(ch) if _num(ch) is not None else 0))
            total = len(channels)
            pages = max(1, -(-total // PAGE))
            try: page = max(0, min(int(page), pages - 1))
            except Exception: page = 0
            page_ch = channels[page * PAGE:(page + 1) * PAGE]
            ids = {ch.get('id') for ch in page_ch}
            day_start = _dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + _dt.timedelta(days=1)
            ds, de = day_start.strftime(DTFORMAT), day_end.strftime(DTFORMAT)
            out = {'channels': [], 'programmes': [], 'page': page, 'pages': pages, 'total': total}
            for ch in page_ch:
                icon = ch.get('icon') or []
                icon_src = icon[0].get('src') if isinstance(icon, list) and icon and isinstance(icon[0], dict) else (ch.get('logo') or '')
                cid = ch.get('id')
                out['channels'].append({'id': cid, 'name': self.first(ch.get('display-name')), 'logo': icon_src, 'num': self.channelNum(cid)})
            for p in xml.getProgrammes():
                start, stop = p.get('start'), p.get('stop')
                if p.get('channel') not in ids:
                    continue
                if not (start and stop and ds <= start < de):
                    continue
                icon = p.get('icon') or []
                icon_src = icon[0].get('src') if isinstance(icon, list) and icon and isinstance(icon[0], dict) else ''
                rating = p.get('rating')
                rating_v = rating[0].get('value') if isinstance(rating, list) and rating and isinstance(rating[0], dict) else ''
                stars = p.get('star-rating')
                stars_v = stars[0].get('value') if isinstance(stars, list) and stars and isinstance(stars[0], dict) else ''
                length = (p.get('length') or {}).get('length', '') if isinstance(p.get('length'), dict) else ''
                epnum = ''
                for val, sys_ in (p.get('episode-num') or []):
                    if sys_ == 'xmltv_ns':
                        epnum = val
                        break
                vid = ''
                cid = p.get('catchup-id') or ''
                if cid:
                    try:
                        m = re.search(r'[?&]vid=([^&]+)', cid)
                        if m:
                            decoded = FileAccess._decodeString(m.group(1))
                            if isinstance(decoded, str) and decoded.startswith(('http://', 'https://')):
                                vid = decoded
                    except Exception:
                        pass
                out['programmes'].append({
                    'channel': p.get('channel'),
                    'start': start, 'stop': stop,
                    'title': self.first(p.get('title')),
                    'sub-title': self.first(p.get('sub-title')),
                    'desc': self.first(p.get('desc')),
                    'icon': icon_src,
                    'vid': vid,
                    'genre': [self.first(g) for g in (p.get('category') or [])],
                    'length': length, 'stars': stars_v, 'rating': rating_v,
                    'date': p.get('date'), 'episode-num': epnum,
                    'credits': p.get('credits') or {},
                    'country': self.first(p.get('country')),
                    'language': self.first(p.get('language')),
                    'aspect': ((p.get('video') or [{}])[0].get('aspect', '') if isinstance(p.get('video'), list) else ''),
                })
            return out
        except Exception as e:
            self.log('guide failed: %s' % e, xbmc.LOGDEBUG)
            return {'channels': [], 'programmes': [], 'page': 0, 'pages': 1, 'total': 0}

    def manageImports(self, method: str, incoming: Optional[dict] = None) -> tuple:
        try:
            from backup import Backup
            backup = Backup()
            if method == 'GET':
                return ({'imports': backup.getImports()}, 200)
            fle = (incoming.get('payload', {}) or {}).get('file') if isinstance(incoming.get('payload'), dict) else incoming.get('file')
            ok = backup.importChannels(fle) if fle else False
            return ({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        except Exception as e:
            self.log('imports %s failed: %s' % (method, e), xbmc.LOGERROR)
            return ({'error': str(e), 'status': 500}, 500)

    def manageBackups(self, method: str, incoming: Optional[dict] = None) -> tuple:
        try:
            from backup import Backup
            backup = Backup()
            if method == 'GET':
                return ({'backups': backup.getBackups()}, 200)
            ok = backup.backupChannels()
            return ({'status': 'ok' if ok else 'error'}, 200 if ok else 400)
        except Exception as e:
            self.log('backups %s failed: %s' % (method, e), xbmc.LOGERROR)
            return ({'error': str(e), 'status': 500}, 500)
