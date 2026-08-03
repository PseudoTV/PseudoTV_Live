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
import sys
from typing      import Dict, Optional
from variables   import *
from fileaccess  import FileAccess

_INSTANCE_NAME_RE = re.compile(r'<setting id=\"kodi_addon_instance_name\" default=\"true\">(.*?)\</setting>', re.IGNORECASE)
_INSTANCE_NAME2_RE = re.compile(r'<setting id=\"kodi_addon_instance_name\">(.*?)\</setting>', re.IGNORECASE)
_INSTANCE_ENABLED_RE = re.compile(r'<setting id=\"kodi_addon_instance_enabled\"', re.IGNORECASE)
_M3U_PATH_RE = re.compile(r'<setting id=\"m3uPath\"[^>]*>(.*?)\</setting>', re.IGNORECASE)
_M3U_URL_RE = re.compile(r'<setting id=\"m3uUrl\"[^>]*>(.*?)\</setting>', re.IGNORECASE)

# transient PVR load errors (e.g. pvr.iptvsimple fetching the XMLTV while
# the builder rewrites it) expire after this many seconds so they can't keep the
# PVR permanently out-of-sync. 15 min covers the reload+retry window comfortably.
PVR_ERROR_TTL = 15 * 60
        
class Instances(object):
    def __init__(self, settings: Any):
        self.settings        = settings
        self._cached_status  = None


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    _INSTANCE_DEFAULTS = {
        'kodi_addon_instance_name'   :'',
        'kodi_addon_instance_enabled':'',
        'm3uPathType'                :'',
        'm3uPath'                    :'',
        'm3uCache'                   :'',
        'epgPathType'                :'',
        'epgPath'                    :'',
        'epgCache'                   :'',
        'genresPathType'             :'',
        'genresPath'                 :'',
        'logoPathType'               :'',
        'logoPath'                   :''}

    def _load(self, file: str = INSTANCEFLE_DEFAULT) -> Dict[str, Optional[str]]:
        """Load settings from an XML file, merging with default IPTV Simple settings."""
        settings = self.IPTV_SIMPLE_SETTINGS()
        settings.update(self._INSTANCE_DEFAULTS)
        if FileAccess.exists(file):
            try:
                self.log(f"_load {file}")
                xml  = FileAccess.open(file, "r")
                root = ETparse(xml).getroot()
                for s in root.findall('setting'):
                    # val = (s.text or "").strip() or s.get('default')
                    val = (s.text or "").strip()
                    settings[s.get('id')] = val if val != "" else None
            except Exception as e: self.log(f"_load {file}, failed!\n{e}")
            finally: 
                if hasattr(xml,'close'): xml.close()
        return settings
            
            
    def _save(self, file: str, nsettings: Optional[Dict[str, Optional[str]]] = None) -> bool:
        """Save settings to an XML file, merging with existing settings."""
        if nsettings is None: nsettings = {}
        self.log(f"_save {file}")
        
        doc  = Document()
        root = doc.createElement('settings')
        root.setAttribute('version', '2')
        doc.appendChild(root)
        
        settings = self._load()
        settings.update(nsettings)
        
        for setting_id, value in settings.items():
            setting_node = doc.createElement('setting')
            setting_node.setAttribute('id', setting_id)
            setting_node.setAttribute('default', 'true')
            if value:
                text_node = doc.createTextNode(str(value))
                setting_node.appendChild(text_node)
            root.appendChild(setting_node)
            
        with FileAccess.stream(file, 'w') as fle:
            fle.write(doc.toprettyxml(indent="    ", encoding="utf-8"))
        return True
        
        
    def _set(self, instanceName: str = ADDON_NAME, settings: Dict[str, str] = {}, silent: Optional[bool] = None):
        if self._save(self.getPVRInstancePath(instanceName),settings):
            Globals = sys.modules['variables'].Globals
            Globals.properties.setPropTimer('chkPVRRefresh')
            if not silent: 
                Globals.dialog.notificationDialog((LANGUAGE(32037).format(name=self.settings.hasAddon(PVR_CLIENT_ID,notify=True).getAddonInfo('name'))))
        
        
    def _getPVRAddon(self):
        """Lazy xbmcaddon import to avoid circular import issues."""
        import xbmcaddon
        return xbmcaddon.Addon(PVR_CLIENT_ID)


    def _findPVRInstanceID(self, addon):
        #todo proper instance id lookup when new Kodi API available.
        ids = addon.getInstanceIds()
        non_zero = [i for i in ids if i > 0]
        if not non_zero:
            self.log(f"_findPVRInstanceID, no instance IDs found")
            return False
        instance_id = non_zero[0]
        self.log(f"_findPVRInstanceID, auto-detected instance_id={instance_id} from {ids}")
        return instance_id


    def _resolveInstanceID(self, addon):
        """Return cached pvr_instance_id from log, or auto-detect via getInstanceIds()."""
        instance_id = self._cached_status.get('log', {}).get('pvr_instance_id') if self._cached_status else None
        if instance_id is None: instance_id = self._findPVRInstanceID(addon)
        return instance_id
        
        
    def getSettings(self, instanceName: str = ADDON_NAME) -> Dict:
        """Kodi instance settings API w/direct read fallback.
        
        Uses getSettings(instance_id) to read from a specific pvr.iptvsimple
        instance. Ref: https://github.com/xbmc/xbmc/pull/23648
        
        Returns: Setting value string, or None if API not available.
        """
        self.log(f"getSettings {instanceName}")
        try:
            addon = self._getPVRAddon()
            if not addon.supportsInstanceSettings(): raise Exception(TypeError)
                
            instance_id    = self._resolveInstanceID(addon)
            settings       = self.settings.getPVRSettings()
            addon_settings = addon.getSettings(instance_id)
            for key, _ in list(settings.items()):
                if   hasattr(addon_settings, 'getString'): settings.update({key, addon_settings.getString(key)})
                elif hasattr(addon_settings, 'getBool'):   settings.update({key, str(addon_settings.getBool(key))})
                else:
                    self.log(f"getSettings, Settings object has no getBool/getString")
                    continue
            return settings
        except (TypeError, AttributeError):
            self.log(f"getSettings, instance API not available (waiting for Kodi #23648)")
            return self._load(self.getPVRInstancePath(instanceName))
        except Exception as e:
            self.log(f"getSettings, ERROR: {e}", xbmc.LOGERROR)
            return None
            
            
    def setSettings(self, instanceName: str = ADDON_NAME, settings: Dict[str, str] = {}, silent: Optional[bool] = None):
        """Kodi instance settings API w/direct write fallback.
        
        Uses the instance settings API from Kodi PR #23648 which adds
        getSettings(instance_id), getInstanceIds(), and supportsInstanceSettings()
        to xbmcaddon.Addon. This triggers SetInstanceSetting() on pvr.iptvsimple
        which sets m_reloadChannelsGroupsAndEPG = true, causing the Process() loop
        to call ReloadPlayList() + ReloadEPG().
        
        Ref: https://github.com/xbmc/xbmc/pull/23648
        """
        try:
            if silent is None: silent = self.settings.getSettingBool('Enable_Kodi_Access')
            addon = self._getPVRAddon()
            if not addon.supportsInstanceSettings():
                self.log(f"setSettings, addon does not support instance settings")
                raise Exception(TypeError)
            
            instance_id    = self._resolveInstanceID(addon)
            addon_settings = addon.getSettings(instance_id)
            for key, value in list(settings.items()):
                if   hasattr(addon_settings, 'setBool'):   addon_settings.setBool(key, value.lower() == 'true')
                elif hasattr(addon_settings, 'setString'): addon_settings.setString(key, value)
                else:
                    self.log(f"setSettings, Settings object has no setBool/setString")
                    continue
            return True
        except (TypeError, AttributeError):
            self.log(f"setSettings, instance API not available (waiting for Kodi #23648)")
            self._set(instanceName, settings, silent)
        except Exception as e:
            self.log(f"setSettings, ERROR: {e}", xbmc.LOGERROR)
            return False
        
        
    def getPVRInstanceID(self, instanceName: str = ADDON_NAME) -> int:
        #return id within IPTV-Simples limit (32-bit integer).
        return zlib.crc32(instanceName.encode(DEFAULT_ENCODING)) % 2147483648
        
        
    def getPVRInstancePath(self, instanceName: str = ADDON_NAME) -> str:
        instancePath = os.path.join(PVR_CLIENT_LOC,f'instance-settings-{self.getPVRInstanceID(instanceName)}.xml')
        self.log(f"getPVRInstancePath {instanceName} => {instancePath}")
        return instancePath
        
        
    def hasPVRInstance(self, instanceName: str = ADDON_NAME) -> Optional[str]:
        """Check if a PVR instance exists and return its path, or None if not found."""
        instancePath = self.getPVRInstancePath(instanceName)
        if FileAccess.exists(instancePath):
            self.log('[%s] hasPVRInstance, instanceName = %s, path = %s'%(PVR_CLIENT_ID,instanceName, instancePath))
            return instancePath
        
        
    def chkInstances(self, instanceName: str = ADDON_NAME):
        """Check and clean duplicate/abandoned PVR instances with the same name."""
        self.log(f"chkInstances {instanceName}")
        if not self.hasPVRInstance(instanceName):
            #clean abandoned configurations.
            files = [filename for filename in FileAccess.listdir(PVR_CLIENT_LOC)[1] if filename.endswith('.xml')]
            for file in files:
                if file.startswith('instance-settings-'):
                    try:
                        fle = FileAccess.open(os.path.join(PVR_CLIENT_LOC,file), "r")
                        xml = fle.read()
                        fle.close()
                        match = _INSTANCE_NAME_RE.search(xml)
                        try: name = match.group(1)
                        except Exception:
                            self.log(f'chkInstances, primary regex failed for {file}, trying fallback', xbmc.LOGDEBUG)
                            match = _INSTANCE_NAME2_RE.search(xml)
                            try: name = match.group(1)
                            except Exception: 
                                self.log(f'chkInstances, fallback regex also failed for {file}', xbmc.LOGDEBUG)
                                name = ""
                            
                        if instanceName.lower() == name.replace('%s - '%(ADDON_NAME),'').lower():
                            #auto remove any duplicate entries with the same instance name.
                            FileAccess.delete(os.path.join(PVR_CLIENT_LOC,file))
                            self.log('[%s] chkInstances, removing duplicate entry %s'%(PVR_CLIENT_ID,file))
                    except Exception as e:
                        self.log('[%s] chkInstances, path = %s, failed to open file = %s\n%s'%(PVR_CLIENT_ID,PVR_CLIENT_LOC,file,e))
                        continue


    def IPTV_SIMPLE_SETTINGS(self) -> Dict[str, str]:
        """Return default recommended IPTV Simple Client settings."""
        return {
            'kodi_addon_instance_enabled'   :'false',  # Disable by default
            
            # M3U playlist settings
            'startNum'                      :'1',      # First channel number
            'numberByOrder'                 :'false',  # Number by order in M3U (overrides tvg-chno)
            'm3uRefreshMode'                :'1',      # 0=disabled, 1=interval, 2=daily
            'm3uRefreshIntervalMins'        :'%s'%(M3U_REFRESH), # Minutes between M3U reloads
            'm3uRefreshHour'                :'0',      # Hour of day for daily refresh (0-23)
            'connectioncheckinterval'       :'%s'%(M3U_INTERVAL), # Seconds between connection checks
            'connectionchecktimeout'        :'%s'%(M3U_TIMEOUT),  # Seconds before connection times out

            # Provider mapping settings
            'defaultProviderName'           :ADDON_NAME,           # Provider name for unmapped channels
            'enableProviderMappings'        :'true',               # Enable provider name mapping
            'providerMappingFile'           :PROVIDERFLE_DEFAULT,  # Path to provider mapping XML

            # EPG settings
            'useEpgGenreText'               :'true',     # Use genre text from EPG instead of numeric IDs
            'logoFromEpg'                   :'2',        # 0=disabled, 1=from EPG, 2=from EPG or M3U
            'mediaTitleSeasonEpisode'       :'true',     # Parse title as Season/Episode from EPG

            # Catchup/timeshift settings
            'timeshiftEnabled'              :'false',    # Enable live TV timeshift buffer
            'catchupEnabled'                :'true',     # Enable VOD catchup replay
            'catchupPlayEpgAsLive'          :'false',    # Play catchup as live stream
            'catchupWatchEpgEndBufferMins'  :'0',        # End buffer in minutes for catchup
            'catchupWatchEpgBeginBufferMins':'0',        # Begin buffer in minutes for catchup

            # Streaming settings
            'useFFmpegReconnect'            :'false',    # Use FFmpeg for stream reconnection
            'useInputstreamAdaptiveforHls'  :'false',    # Use inputstream.adaptive for HLS
            'transformMulticastStreamUrls'  :'false',    # Transform multicast URLs to unicast
        }
                

    def togglePVRBackend(self, _phase: int = 0):
        """Full PVR reload — disable then re-enable pvr.iptvsimple.

        Runs synchronously (called on the queue thread) with bounded waits so it
        never spawns threads. Previously used timerit() to chain phases, which
        created a new threading.Timer every retry — on constrained SoC devices
        (Android) with a PVR that can't connect, this exhausted the OS thread
        pool ("can't start new thread") and crashed PseudoTV.

        Sequence (bounded):
          Phase 0: Disable addon, wait 3s for shutdown
          Phase 1: Re-enable addon, wait 5s for startup
          Phase 2: Poll Pvr.HasTVChannels/RadioChannels every 5s, max MAX_RETRIES
        The PVR_RELOADING property flag prevents overlapping cycles.
        Callers should check isPVRReloading() before calling.
        Refuses to disable during playback (crashes Kodi).
        """
        Globals = sys.modules['variables'].Globals
        MAX_RETRIES = 6  # 6 * 5s = 30s max wait for PVR to load, then give up

        # Prevent overlapping reload cycles
        if _phase == 0 and Globals.properties.isPVRReloading():
            self.log("togglePVRBackend, already reloading, skip", xbmc.LOGDEBUG)
            return

        # Safety: refuse to disable PVR during playback — crashes Kodi
        if _phase == 0 and xbmc.Player().isPlaying():
            self.log("togglePVRBackend, REFUSED: player active, cannot disable PVR during playback", xbmc.LOGWARNING)
            return

        # --- Phase 0: Disable ---
        if _phase == 0:
            Globals.properties.setPVRReloading(True)
            notification_msg = f"{PVR_CLIENT_NAME}: {LANGUAGE(32125)}"
            Globals.dialog.notificationWait(notification_msg, wait=3, usethread=True)
            try:
                payload = {"method": "Addons.SetAddonEnabled", "params": {"addonid": PVR_CLIENT_ID, "enabled": False}}
                self.settings.jsonRPC.sendJSON(payload)
            except Exception as e:
                self.log(f"togglePVRBackend, disable sendJSON error: {e}", xbmc.LOGERROR)
                Globals.properties.setPVRReloading(False)
                return
            self.log("togglePVRBackend, PVR disabled, waiting 3s then re-enabling")
            if MONITOR().waitForAbort(3): return
            # fall through to re-enable (Phase 1)

        # --- Phase 1: Re-enable ---
        if _phase <= 1:
            try:
                payload = {"method": "Addons.SetAddonEnabled", "params": {"addonid": PVR_CLIENT_ID, "enabled": True}}
                self.settings.jsonRPC.sendJSON(payload)
            except Exception as e:
                self.log(f"togglePVRBackend, enable sendJSON error: {e}", xbmc.LOGERROR)
                Globals.properties.setPVRReloading(False)
                return
            self.log("togglePVRBackend, PVR re-enabled, waiting 5s then checking load")
            if MONITOR().waitForAbort(5): return
            _phase = 2

        # --- Phase 2: Wait for PVR to fully load (bounded retries, every 5s) ---
        retry = 0
        while retry < MAX_RETRIES:
            if Globals.builtin.getInfoBool('Pvr.HasTVChannels') or Globals.builtin.getInfoBool('Pvr.HasRadioChannels'):
                self.log("togglePVRBackend, PVR fully loaded")
                Globals.properties.setPVRReloading(False)
                return
            retry += 1
            self.log(f"togglePVRBackend, PVR not loaded yet, retry {retry}/{MAX_RETRIES}", xbmc.LOGDEBUG)
            if MONITOR().waitForAbort(5): return
        self.log(f"togglePVRBackend, giving up after {MAX_RETRIES} retries — PVR did not load", xbmc.LOGWARNING)
        Globals.properties.setPVRReloading(False)


    def togglePVRReload(self, instanceName: str = ADDON_NAME, key: str = 'useEpgGenreText') -> bool:
        """Light PVR reload — flip a pvr.iptvsimple setting then restore.
        
        Reads the current value of `key`, sets it to the opposite, waits
        for the Process() loop to pick up the change (triggers M3U+EPG
        reload), then restores the original value.
        
        Ref: https://github.com/xbmc/xbmc/pull/23648
        
        Falls back to legacy addon.setSetting() when the instance API
        is not available (pre-#23648 Kodi).
        
        Returns: True if toggle succeeded, False otherwise.
        """
        reload_wait = 30  # seconds — enough for Process() loop to fire
        def _flip(val: str) -> str:
            return 'false' if val.lower() == 'true' else 'true'
        try:
            addon = self._getPVRAddon()
            if not addon.supportsInstanceSettings():
                self.log(f"togglePVRReload, addon does not support instance settings")
                raise Exception(TypeError)
            
            instance_id = self._resolveInstanceID(addon)
            addon_settings = addon.getSettings(instance_id)
            # Use getString/setString universally — works for both bool and string settings
            if hasattr(addon_settings, 'getString') and hasattr(addon_settings, 'setString'):
                org = addon_settings.getString(key)
                flipped = _flip(org)
                addon_settings.setString(key, flipped)
                self.log(f"togglePVRReload, set {key}={flipped} (was {org}), waiting {reload_wait}s then restoring")
                MONITOR().waitForAbort(reload_wait)
                addon_settings.setString(key, org)
            elif hasattr(addon_settings, 'getBool') and hasattr(addon_settings, 'setBool'):
                org = addon_settings.getBool(key)
                addon_settings.setBool(key, not org)
                self.log(f"togglePVRReload, set {key}={not org} (was {org}), waiting {reload_wait}s then restoring")
                MONITOR().waitForAbort(reload_wait)
                addon_settings.setBool(key, org)
            else:
                self.log(f"togglePVRReload, Settings object has no get/set methods")
                return False
            self.log(f"togglePVRReload, restored {key}={org}")
            return True
        except (TypeError, AttributeError):
            self.log(f"togglePVRReload, instance API not available (waiting for Kodi #23648)")
            try:
                addon = self._getPVRAddon()
                instance_id = self._resolveInstanceID(addon)
                if instance_id is None:
                    self.log(f"togglePVRReload, could not resolve instance ID for fallback", xbmc.LOGERROR)
                    return False
                instance_path = os.path.join(PVR_CLIENT_LOC, f'instance-settings-{instance_id}.xml')
                if not FileAccess.exists(instance_path):
                    self.log(f"togglePVRReload, instance settings file not found: {instance_path}", xbmc.LOGERROR)
                    return False
                settings = self._load(instance_path)
                org = settings.get(key, '')
                flipped = _flip(org)
                settings[key] = flipped
                self._save(instance_path, settings)
                self.log(f"togglePVRReload, set {key}={flipped} (was {org}) on instance {instance_id}, waiting {reload_wait}s then restoring")
                MONITOR().waitForAbort(reload_wait)
                settings[key] = org
                self._save(instance_path, settings)
                self.log(f"togglePVRReload, restored {key}={org}")
                # returning False — direct XML write doesn't trigger pvr.iptvsimple's
                # Process() loop. pvr.iptvsimple only monitors Kodi's in-memory settings API.
                # Returning False lets chkPVRRefresh fall back to togglePVRBackend.
                self.log(f"togglePVRReload, direct XML write may not trigger reload — returning False for brute fallback")
                return False
            except Exception as e:
                self.log(f"togglePVRReload, fallback ERROR: {e}", xbmc.LOGERROR)
                return False
        except Exception as e:
            self.log(f"togglePVRReload, ERROR: {e}", xbmc.LOGERROR)
            return False

    def _disableMigratedPVRInstance(self) -> bool:
        """Disable pvr.iptvsimple Migrated Config instance if it has empty m3u path/url.
        
        Kodi's Migrated Config (instance 0, settings.xml) has m3uPathType=URL
        but an empty m3uUrl, which blocks the entire PVR addon from connecting.
        Writes kodi_addon_instance_enabled=false to prevent this.
        
        Returns True if the file was modified (caller should trigger PVR reload).
        """
        try:
            settings_path = FileAccess.translatePath(f'special://userdata/addon_data/{PVR_CLIENT_ID}/settings.xml')
            if not FileAccess.exists(settings_path): return False
            with FileAccess.open(settings_path, 'r') as f:
                content = f.read()
            if not content: return False
            # Instance 0 (settings.xml) is always Kodi's Migrated Config — no name in file
            if 'instance-settings-' in settings_path: return False
            path_match = _M3U_PATH_RE.search(content)
            url_match  = _M3U_URL_RE.search(content)
            has_path = path_match and path_match.group(1).strip()
            has_url  = url_match  and url_match.group(1).strip()
            if has_path or has_url: return False
            if _INSTANCE_ENABLED_RE.search(content): return False
            content = content.replace('</settings>', '    <setting id="kodi_addon_instance_enabled">false</setting>\n</settings>')
            with FileAccess.open(settings_path, 'w') as f:
                f.write(content)
            self.log(f"_disableMigratedPVRInstance, disabled Migrated Config with empty m3u path/url", xbmc.LOGINFO)
            return True
        except Exception as e:
            self.log(f"_disableMigratedPVRInstance, error: {e}", xbmc.LOGDEBUG)
            return False


    def _chkRemoteInstances(self, host: str = None) -> list:
        """Cross-reference non-local pvr.iptvsimple instances with servers.json.

        pvr.iptvsimple instances pointing to a different host are either legitimate
        remote PseudoTV servers (present in servers.json AND enabled) or stale
        leftovers from an old machine IP. Enabled remotes are reported as
        "remote instance online"; anything else has its instance settings file
        deleted so it can't pollute Kodi's PVR or the local status (delServer).
        """
        remote = []
        try:
            from multiroom import Multiroom
            servers    = Multiroom().serverData.get('servers', {})
            enabled_by_host = {s.get('host'): s for s in servers.values() if s.get('enabled')}
            local_host = (host or '').split('/')[-1]
            files = FileAccess.listdir(PVR_CLIENT_LOC)[1] if FileAccess.exists(PVR_CLIENT_LOC) else []
            for file in files:
                if not (file.startswith('instance-settings-') and file.endswith('.xml')): continue
                path = os.path.join(PVR_CLIENT_LOC, file)
                try:
                    with FileAccess.open(path, 'r') as f: xml = f.read()
                    m_url  = _M3U_URL_RE.search(xml) or _M3U_PATH_RE.search(xml)
                    m_name = _INSTANCE_NAME_RE.search(xml) or _INSTANCE_NAME2_RE.search(xml)
                    url  = (m_url.group(1) or '').strip() if m_url else ''
                    name = (m_name.group(1) or file) if m_name else file
                    mh   = re.search(r'https?://([^/]+)', url)
                    inst_host = mh.group(1) if mh else ''
                    if not inst_host or inst_host == local_host:
                        continue  # local instance or no url — leave untouched
                    server = enabled_by_host.get(inst_host)
                    if server:
                        remote.append({'name': name, 'host': inst_host,
                                       'online': server.get('online', False), 'enabled': True})
                    else:
                        FileAccess.delete(path)
                        self.log(f"_chkRemoteInstances, removed stale pvr instance {file} -> {inst_host}", xbmc.LOGINFO)
                except Exception as e:
                    self.log(f"_chkRemoteInstances, {file} failed: {e}", xbmc.LOGDEBUG)
        except Exception as e:
            self.log(f"_chkRemoteInstances, error: {e}", xbmc.LOGDEBUG)
        return remote


    def updatePVRStatus(self, host: str, friendly_name: str, wait: int=60) -> dict:
        """Return cached PVR status. M3U/XMLTV data updated by builder.
        TODO: https://github.com/xbmc/xbmc/pull/25711 - Add On Demand status tracking when PVR On Demand API lands (Kodi v23+).
        """
        Globals = sys.modules['variables'].Globals
        if host is None: host = Globals.properties.getRemoteHost()
        if friendly_name is None: friendly_name = Globals.properties.getFriendlyName()
        self.log(f"updatePVRStatus, friendly_name = {friendly_name}")
        if self._disableMigratedPVRInstance():
            self.togglePVRBackend()
        if self._cached_status is None:
            self._cached_status = {
                'name': friendly_name,               # Instance friendly name (e.g., 'Kodi Desktop')
                'm3u':   {'url'        : 'http://%s/%s'%(host, M3UFLE),    # HTTP URL to M3U playlist
                          'channel_ids': set(),       # Channel IDs from saved M3U file (set by m3u.py)
                          'last_write' : None,        # Timestamp of last M3U file write (set by m3u.py)
                          'sync_state' : 'unknown',   # 'fresh'/'stale'/'outdated'/'unknown' (computed)
                          'channels'   : 0,           # M3U channel count (computed by _computeDerived)
                          'missing_epg': [],          # Channel IDs with no EPG data (computed)
                          'unloaded_by_pvr': []},     # Channel IDs not loaded by PVR (computed)
                          
                'xmltv': {'url'        : 'http://%s/%s'%(host, XMLTVFLE),  # HTTP URL to XMLTV file
                          'channel_ids': set(),       # Channel IDs from saved XMLTV file (set by xmltvs.py)
                          'last_write' : None,        # Timestamp of last XMLTV file write (set by xmltvs.py)
                          'sync_state' : 'unknown',   # 'fresh'/'stale'/'outdated'/'unknown' (computed)
                          'programmes' : -1,          # Total programme count (set by xmltvs.py)
                          'channels'   : 0,           # XMLTV channel count (computed by _computeDerived)
                          'missing_from_local': []},      # XMLTV IDs not in local M3U (computed)
                'log':   {'pvr_connected'     : False,         # PVR client connected state
                          'm3u_errors'        : [],            # M3U load error strings
                          'epg_errors'        : [],            # EPG load error strings
                          'connection_events' : [],            # Connection state change dicts {from, to, time}
                          'pvr_channel_ids'   : [],            # Hex channel IDs loaded by PVR (from parsePVRLog)
                          'pvr_provider'      : None,          # Provider name if addon channels found (e.g., 'PseudoTV Live (Kodi Desktop)')
                          'connect_failed'    : False,         # Connection attempt failed
                          'url_check_failed'  : False,         # URL connection check failed
                          'load_playlist'     : {'started': False, 'total_channels': 0, 'channels': [], 'groups': {}, 'providers': {}, 'media_items': 0},
                          'load_epg'          : {'started': False, 'channels': {}, 'epg_channel_count': 0, 'epg_entry_count': 0},
                          'load_genres'       : {'genres_count': 0},
                          'get_channels'      : {'channels': {}},
                          'get_group_members' : {'channels': {}},
                          'get_channel_groups': {'groups': {}},
                          'channels_available': 0,            # Non-radio channels available in PVR
                          'radio_available'   : 0,            # Radio channels available in PVR
                          'pvr_errors'        : [],            # Combined m3u_errors + epg_errors (computed)
                          'pvr_instance_id'   : None,          # Kodi PVR instance ID (CRC32 of name, from log)
                          'pvr_client_id'     : None,          # Kodi PVR client ID (from log)
                          'last_update'       : -1},           # Timestamp of last updatePVRStatus call
                          
                'notifications': {'last_event': None,   # Last PVR notification method name
                                  'last_time': None,    # Timestamp of last PVR notification
                                  'events': []},        # Last 50 notification dicts {method, data, time}
                # PVR event tracking — timestamps and counts per notification type
                # Updated by Monitor._logEvents when PVR sends notifications
                'pvr_events': {
                    'channel_update'  : {'last_time': 0, 'count': 0},  # OnChannelUpdate — channel list modified
                    'group_update'    : {'last_time': 0, 'count': 0},  # OnChannelGroupUpdate — group structure changed
                    'epg_update'      : {'last_time': 0, 'count': 0},  # OnEpgUpdate — EPG data updated
                    'recording_update': {'last_time': 0, 'count': 0},  # OnRecordingUpdate — recording added/removed
                    'timer_update'    : {'last_time': 0, 'count': 0},  # OnTimerUpdate — timer added/removed
                    'provider_update' : {'last_time': 0, 'count': 0},  # OnProviderUpdate — provider list changed
                    'scan_start'      : {'last_time': 0, 'count': 0},  # Scanner started (channel/epg scan)
                    'scan_stop'       : {'last_time': 0, 'count': 0},  # Scanner finished
                    'connection'      : {'last_time': 0, 'count': 0},  # ConnectionStateChange — PVR connection state
                },
                'in_sync': False  # True when PVR loaded IDs == M3U IDs == XMLTV IDs (computed by _computeDerived)
            }
            self._cached_status['remote_instances'] = []  # non-local pvr.iptvsimple instances (enabled servers.json entries)
        status = self._cached_status
        try:
            if status['log']['pvr_connected'] and status['in_sync']: wait = 300
            if Globals.properties.isLogDirty() or (time.time() - status['log']['last_update']) > wait:
                pvr_log = self.parsePVRLog(host, friendly_name)
                # Merge parsed PVR channel IDs with existing ones (log window may not cover all entries)
                existing_ids = status['log'].get('pvr_channel_ids', [])
                new_ids = pvr_log.get('pvr_channel_ids', [])
                pvr_log['pvr_channel_ids'] = list(dict.fromkeys(existing_ids + new_ids))
            status['log'].update(pvr_log)
            status['log']['last_update'] = time.time()
            # Merge log-derived pvr_events; notification-driven counts win when higher.
            if pvr_log.get('pvr_events'):
                for _k, _v in pvr_log['pvr_events'].items():
                    if _v.get('count', 0) > status['pvr_events'].get(_k, {}).get('count', 0):
                        status['pvr_events'][_k] = _v
            Globals.properties.setLogDirty(False)
            # cross-reference other pvr.iptvsimple instances — remote servers
            # (enabled in servers.json) are reported; stale leftovers are deleted.
            status['remote_instances'] = self._chkRemoteInstances(host)
            self._resolvePVRStatus(status)
            m3u_count = len(status['m3u'].get('channel_ids', set()))
            xmltv_count = len(status['xmltv'].get('channel_ids', set()))
            xmltv_progs = status['xmltv'].get('programmes', 0)
            self.log(f"updatePVRStatus, m3u={m3u_count}ch/{status['m3u']['sync_state']}, xmltv={xmltv_count}ch/{xmltv_progs}prog/{status['xmltv']['sync_state']}, pvr_connected={status['log']['pvr_connected']}")
            if status['m3u']['unloaded_by_pvr']:
                self.log(f"updatePVRStatus, M3U channels missing from PVR client: {status['m3u']['unloaded_by_pvr']}", xbmc.LOGWARNING)
            if status['m3u'].get('missing_epg'):
                self.log(f"updatePVRStatus, {len(status['m3u']['missing_epg'])} channels with no EPG data: {status['m3u']['missing_epg']}", xbmc.LOGWARNING)
            # Trigger PVR refresh when out of sync (non-blocking, debounced via prop timer)
            # Skip when M3U is empty — builder is running, _onDataChanged will trigger refresh.
            if not status.get('in_sync', False) and status['log'].get('pvr_connected', False) and m3u_count > 0:
                xbmcgui.Window(10000).setProperty('%s.chkPVRRefresh' % ADDON_ID, FileAccess.dumpJSON({'s': True, 'a': [], 'k': {}})) #globals hasn't finished __init__
            # Convert sets to lists for JSON serialization (json.dumps raises TypeError on sets)
            status['m3u']['channel_ids'] = list(status['m3u'].get('channel_ids', set()))
            status['xmltv']['channel_ids'] = list(status['xmltv'].get('channel_ids', set()))
            return status
        except Exception as e:
            self.log(f"updatePVRStatus, error: {e}", xbmc.LOGDEBUG)
            return status


    def _resolvePVRStatus(self, status: dict):
        """Resolve raw M3U/XMLTV/log data into unified status fields.

        Computes channel counts, sync states (fresh/stale/outdated),
        cross-source diffs (missing_from_local, unloaded_by_pvr, missing_epg),
        combined error lists, and the in_sync flag.
        """
        Globals = sys.modules['variables'].Globals
        now = time.time()
        FRESH_THRESHOLD  = 300   # 5 minutes - file was written recently
        STALE_THRESHOLD  = 3600  # 1 hour   - file exists but hasn't been refreshed

        # Ensure channel_ids are sets (updatePVRStatus converts to lists for JSON serialization)
        if not isinstance(status['m3u'].get('channel_ids'), set):
            status['m3u']['channel_ids'] = set(status['m3u'].get('channel_ids', []))
        if not isinstance(status['xmltv'].get('channel_ids'), set):
            status['xmltv']['channel_ids'] = set(status['xmltv'].get('channel_ids', []))

        # M3U channel count
        m3u_ids = status['m3u'].get('channel_ids', set())
        status['m3u']['channels'] = len(m3u_ids)

        # XMLTV channel count & programme count
        xmltv_ids = status['xmltv'].get('channel_ids', set())
        status['xmltv']['channels'] = len(xmltv_ids)

        # M3U sync_state: how recently was the M3U file written?
        m3u_last = status['m3u'].get('last_write')
        if m3u_ids and m3u_last is not None:
            age = now - m3u_last
            if   age < FRESH_THRESHOLD: status['m3u']['sync_state'] = 'fresh'
            elif age < STALE_THRESHOLD: status['m3u']['sync_state'] = 'stale'
            else:                       status['m3u']['sync_state'] = 'outdated'
        else:
            status['m3u']['sync_state'] = 'unknown'

        # XMLTV sync_state: how recently was the XMLTV file written?
        xmltv_last  = status['xmltv'].get('last_write')
        xmltv_progs = status['xmltv'].get('programmes', 0)
        if xmltv_ids and xmltv_progs > 0 and xmltv_last is not None:
            age = now - xmltv_last
            if   age < FRESH_THRESHOLD: status['xmltv']['sync_state'] = 'fresh'
            elif age < STALE_THRESHOLD: status['xmltv']['sync_state'] = 'stale'
            else:                       status['xmltv']['sync_state'] = 'outdated'
        else:
            status['xmltv']['sync_state'] = 'unknown'

        # XMLTV channels not in local M3U (orphans from PVR or stale data)
        status['xmltv']['missing_from_local'] = list(xmltv_ids - m3u_ids)

        # M3U channels not loaded by PVR (set difference: our IDs minus PVR's loaded IDs)
        pvr_ids = set(status['log'].get('pvr_channel_ids', []))
        channels_loaded = status['log'].get('load_playlist', {}).get('total_channels', 0)
        m3u_id_list = list(m3u_ids)
        if m3u_ids and pvr_ids:
            # pvr_channel_ids are hex-only (e.g., '312e506f...'),
            # but m3u_ids may have suffix (e.g., '312e506f...@PseudoTV_Live').
            # Strip suffix before comparison so the set difference works.
            m3u_hex = {i.split('@')[0] for i in m3u_ids}
            status['m3u']['unloaded_by_pvr'] = list(m3u_hex - pvr_ids)
        elif m3u_ids and channels_loaded > 0 and channels_loaded < len(m3u_id_list):
            # Fallback: no parsed IDs, use count-based estimate
            status['m3u']['unloaded_by_pvr'] = m3u_id_list[channels_loaded:]
        elif m3u_ids:
            # pvr_ids empty (startup before PVR loads, or mid-toggle) — only
            # mark channels unloaded if PVR genuinely has NO channels. Use the live
            # Pvr.HasTVChannels info as the source of truth; a transient parse gap
            # (empty pvr_channel_ids) must NOT trigger a full rebuild (Case #4).
            pvr_has_any = (Globals.builtin.getInfoBool('Pvr.HasTVChannels')
                           or Globals.builtin.getInfoBool('Pvr.HasRadioChannels'))
            status['m3u']['unloaded_by_pvr'] = list(m3u_ids) if not pvr_has_any else []
        else:
            status['m3u']['unloaded_by_pvr'] = []

        # Channels loaded by PVR but with no EPG data (guide entries missing)
        # pvr_channel_ids are hex-only (e.g., '312e506f...'), load_epg keys have suffix (e.g., '312e506f...@PseudoTV_Live')
        # Strip suffix from EPG keys to normalize the comparison
        pvr_ids_set  = set(status['log'].get('pvr_channel_ids', []))
        epg_ids_set  = {k.split('@')[0] for k in status['log'].get('load_epg', {}).get('channels', {}).keys()}
        status['m3u']['missing_epg'] = sorted(pvr_ids_set - epg_ids_set)

        # genres.xml existence — PVR needs this for genre text display
        # (genres now live in the SQLite cache; the export file is optional)
        GENREFLEPATH = sys.modules['variables'].GENREFLEPATH
        genres_exists = bool(Globals.settings.getCacheSetting(GENRES_CACHE_KEY)) or FileAccess.exists(GENREFLEPATH)
        genres_loaded = status['log'].get('load_genres', {}).get('genres_count', 0)
        status['xmltv']['genres_exists'] = genres_exists
        status['xmltv']['genres_loaded'] = genres_loaded

        # Combined PVR error list from M3U and EPG load failures
        status['log']['pvr_errors'] = status['log'].get('m3u_errors', []) + status['log'].get('epg_errors', [])
        if genres_exists and genres_loaded == 0:
            status['log']['pvr_errors'].append('genres.xml exists but PVR loaded 0 genres')

        # In sync: PVR loaded IDs match both M3U and XMLTV exactly
        pvr_set = set(status['log'].get('pvr_channel_ids', []))
        status['in_sync'] = bool(pvr_set and pvr_set == m3u_ids and pvr_set == xmltv_ids)


    def parsePVRLog(self, host: str = None, friendly_name: str = None) -> dict:
        """Parse kodi.log for IPTV Simple Client events specific to our addon instance.
        Returns a comprehensive status dict with connection, load, error, and channel info.

        Host filtering: log lines are pre-filtered by PVR_CLIENT_ID ('pvr.iptvsimple').
        For local instance, lines are additionally filtered by 'host' string.
        Lines from other instances (different host) are skipped.
        """
        from constants import PVR_CLIENT_ID, ADDON_NAME
        log_path = FileAccess.translatePath('special://logpath/kodi.log')
        if not FileAccess.exists(log_path): return {}

        result = {
            # Connection state: True if IPTV Simple has an active connection to the PVR backend
            'pvr_connected': True,
            # M3U load errors: trailing 200 chars of each "Unable to load playlist cache file" line for this host
            'm3u_errors': [],
            # EPG load errors: trailing 200 chars of each "Unable to load EPG file" line for this host
            'epg_errors': [],
            # Connection events: list of {from, to, time} dicts tracking IPTV Simple connection state transitions
            'connection_events': [],
            # PVR channel IDs: hex channel IDs parsed from M3U/EPG URLs that match our addon's slug (e.g., 'PseudoTV_Live')
            'pvr_channel_ids': [],
            # PVR provider: full provider string if our addon's channels were found (e.g., 'PseudoTV Live (Kodi Desktop)')
            'pvr_provider': None,
            # Connect failed: True if IPTV Simple logged "unable to connect to" for any backend
            'connect_failed': False,
            # URL check failed: True if IPTV Simple logged "Check Unable to open url" for any stream URL
            'url_check_failed': False,
            # PVR client instance ID (CRC32 of name) and client ID from "Creating PVR client" log lines
            'pvr_instance_id': None,
            'pvr_client_id': None,

            # --- LoadPlayList: data parsed from IPTV Simple's M3U playlist load phase ---
            'load_playlist': {
                # started: True if "LoadPlayList Start" was logged (playlist load began)
                'started': False,
                # total_channels: count from "Loaded N channels from 'filename.m3u'" log line
                'total_channels': 0,
                # channels: ordered list of channel dicts parsed from #EXTINF + Media Entry lines
                #   Each dict: {display_name, radio, group, tvg_id, tvg_name, tvg_logo, tvg_chno,
                #               provider, catchup, catchup_source, name, url}
                'channels': [],
                # groups: channels bucketed by group-title attribute {group_name: [channel_dicts]}
                'groups': {},
                # providers: channels bucketed by tvg-id prefix/provider {provider: [channel_dicts]}
                'providers': {},
                # media_items: count of "Adding channel or Media Entry" log lines (= channels with resolved URLs)
                'media_items': 0,
            },

            # --- LoadChannelEpgs: data parsed from IPTV Simple's EPG channel load phase ---
            'load_epg': {
                # started: True if "LoadChannelEpgs Start" was logged
                'started': False,
                # channels: EPG channels keyed by their EPG ID {epg_id: {name, display_names}}
                'channels': {},
                # epg_channel_count: number of EPG channels loaded (from "Loaded N channels with M entries")
                'epg_channel_count': 0,
                # epg_entry_count: total EPG programme entries across all channels
                'epg_entry_count': 0,
            },

            # --- LoadGenres: data parsed from IPTV Simple's genre mapping load phase ---
            'load_genres': {
                # genres_count: number of genre mappings loaded (from "Loaded N genres")
                'genres_count': 0,
            },

            # --- GetChannels: channels IPTV Simple reports to the PVR framework ---
            'get_channels': {
                # channels: channels keyed by their display name {name: {ChannelId, ChannelNumber}}
                #   Populated when PVR queries IPTV Simple for the full channel list
                'channels': {},
            },

            # --- GetChannelGroupMembers: channels within each PVR group ---
            'get_group_members': {
                # channels: channels keyed by display name {name: {ChannelId, ChannelNumber}}
                #   Populated when PVR queries IPTV Simple for channels in a specific group
                'channels': {},
            },

            # --- GetChannelGroups: PVR groups reported by IPTV Simple ---
            'get_channel_groups': {
                # groups: groups keyed by group name {group_name: {id, type, radio}}
                #   id = PVR internal group ID, type = group type (0=all channels), radio = 1 if radio group
                'groups': {},
            },

            # --- Summary counts from PVR's available channel listings ---
            # channels_available: total non-radio channels available in the PVR backend
            'channels_available': 0,
            # radio_available: total radio channels available in the PVR backend
            'radio_available': 0,
            # recordings_available: count from "GetRecordings - media available 'N'"
            'recordings_available': 0,
            # epg_update_thread: True if "EPGUpdate thread start" was logged
            'epg_update_thread': False,
            # providers_available: count from "GetProviders - providers available 'N'"
            'providers_available': 0,
            # pvr_events: event-type tallies derived from the parsed log. Kodi's
            # PVR notifications don't always reach the addon's onNotification, so
            # the log serves as a reliable source; updatePVRStatus merges these in
            # (notification-driven counts win when they are higher).
            'pvr_events': {
                'connection'    : {'count': 0, 'last_time': 0},
                'channel_update': {'count': 0, 'last_time': 0},
                'group_update'  : {'count': 0, 'last_time': 0},
                'epg_update'    : {'count': 0, 'last_time': 0},
            },
        }

        expected_provider = f"{ADDON_NAME} ({friendly_name})" if friendly_name else None
        expected_slug = re.sub(r'[\s_-]+', '_', re.sub(r'[^\w\s-]', '', ADDON_NAME.strip()))

        try:
            # read only the log tail since the last parse instead of the
            # entire (multi-MB) kodi.log on every PVR-status update. Channel IDs are
            # merged with the cached set in updatePVRStatus, so history is retained.
            fle = FileAccess.open(log_path, 'rb')
            try:
                fle.seek(0, 2)
                file_size = fle.tell()
                offset = getattr(self, '_pvr_log_offset', 0) or 0
                if offset > file_size:
                    offset = 0  # log rotated/truncated — re-read from the start
                fle.seek(offset)
                # VFSFile opens text-mode even for 'rb', so lines may be str
                # already — decode only when the stream actually yields bytes.
                all_lines = [ln.decode(DEFAULT_ENCODING, 'replace') if isinstance(ln, bytes) else ln for ln in fle.readlines()]
                self._pvr_log_offset = fle.tell()
            finally:
                fle.close()

            in_load_playlist = False
            current_extinf = None
            local_channel_ids = set()  # our instance's ChannelIds (from GetChannels)

            for line in all_lines:
                line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
                if not line: continue
                if PVR_CLIENT_ID.lower() not in line.lower(): continue

                # --- Connection state ---
                m = re.search(r'connection state change \((\d+) -> (\d+)\)', line)
                if m:
                    result['connection_events'].append({
                        'from': int(m.group(1)),
                        'to': int(m.group(2)),
                        'time': line[:23]
                    })
                if 'ConnectionLost' in line:           result['pvr_connected'] = False
                if 'ConnectionEstablished' in line:    result['pvr_connected'] = True
                # only count connection failures targeting OUR host — stale/remote
                # pvr.iptvsimple instances (old IPs) must not mark the local instance as
                # failed or force rebuilds. `host` is 'ip:port'; the failure line carries
                # the URL, so a dead remote instance's URL won't contain our host.
                # Both flags are time-bounded (PVR_ERROR_TTL) so a one-off startup blip
                # doesn't keep the instance permanently "out of sync".
                if 'unable to connect to' in line and (not host or host in line):
                    try:
                        err_ts = datetime.datetime.strptime(line[:23], '%Y-%m-%d %H:%M:%S.%f')
                        is_fresh = (time.time() - err_ts.timestamp()) <= PVR_ERROR_TTL
                    except Exception:
                        is_fresh = True
                    if is_fresh:
                        result['connect_failed'] = True
                if 'Check Unable to open url' in line and (not host or host in line):
                    try:
                        err_ts = datetime.datetime.strptime(line[:23], '%Y-%m-%d %H:%M:%S.%f')
                        is_fresh = (time.time() - err_ts.timestamp()) <= PVR_ERROR_TTL
                    except Exception:
                        is_fresh = True
                    if is_fresh:
                        result['url_check_failed'] = True

                # --- PVR client instance/client ID from "Creating PVR client" lines ---
                m = re.search(r'Creating PVR client:.*instanceId=(\d+),\s*clientId=(\d+)', line)
                if m:
                    result['pvr_instance_id'] = int(m.group(1))
                    result['pvr_client_id'] = int(m.group(2))

                # --- M3U / EPG load errors ---
                # only keep recent errors — transient "file missing or empty"
                # failures (pvr.iptvsimple polling while the builder rewrites the XMLTV)
                # used to linger forever, keeping PVR permanently out-of-sync and
                # disabling the stale-guide rebuild path in chkPVRSync.
                if ('Unable to load playlist cache file' in line or 'Unable to load EPG file' in line) and host and host in line:
                    try:
                        # kodi.log lines start with 'YYYY-MM-DD HH:MM:SS.mmm'
                        err_ts = datetime.datetime.strptime(line[:23], '%Y-%m-%d %H:%M:%S.%f')
                        is_fresh = (time.time() - err_ts.timestamp()) <= PVR_ERROR_TTL
                    except Exception:
                        is_fresh = True  # unparseable timestamp — keep the error
                    if is_fresh:
                        if 'Unable to load playlist cache file' in line:
                            result['m3u_errors'].append(line[-200:])
                        else:
                            result['epg_errors'].append(line[-200:])

                # ===== LoadPlayList =====
                if 'LoadPlayList Start' in line:
                    in_load_playlist = True
                    result['load_playlist']['started'] = True
                elif in_load_playlist and ('LoadPlayList finished' in line or 'LoadPlayList error' in line):
                    in_load_playlist = False

                # Parse #EXTINF lines
                if in_load_playlist:
                    m = re.match(r'#EXTINF:(.+?)(?:,(.*))?$', line)
                    if m:
                        attrs_str = m.group(1) or ''
                        display_name = (m.group(2) or '').strip()
                        entry = {'display_name': display_name, 'radio': False, 'group': '',
                                 'tvg_id': '', 'tvg_name': '', 'tvg_logo': '', 'tvg_chno': '',
                                 'provider': '', 'catchup': '', 'catchup_source': ''}
                        for attr_m in re.finditer(r'([\w-]+)="([^"]*)"', attrs_str):
                            key = attr_m.group(1)
                            val = attr_m.group(2)
                            if key in entry:
                                entry[key] = val
                        entry['radio'] = entry.get('radio', '').lower() == 'true' if isinstance(entry.get('radio'), str) else bool(entry.get('radio'))
                        current_extinf = entry

                # Finalize channel when Media Entry line follows #EXTINF
                if in_load_playlist and current_extinf:
                    media_m = re.search(r"Adding channel or Media Entry '([^']+)' with URL: '([^']+)'", line)
                    if media_m:
                        entry = current_extinf
                        entry['name'] = media_m.group(1)
                        entry['url'] = media_m.group(2)
                        result['load_playlist']['channels'].append(entry)
                        grp = entry.get('group', '') or 'Ungrouped'
                        result['load_playlist']['groups'].setdefault(grp, []).append(entry)
                        prov = entry.get('provider', '') or 'Unknown'
                        result['load_playlist']['providers'].setdefault(prov, []).append(entry)
                        result['load_playlist']['media_items'] += 1
                        current_extinf = None

                # Total channels loaded
                m = re.search(r"Loaded\s+(\d+)\s+channels\s+from\s+'([^']+)'", line)
                if m and 'playlist' in line.lower():
                    result['load_playlist']['total_channels'] = int(m.group(1))

                # ===== LoadChannelEpgs =====
                if 'LoadChannelEpgs Start' in line:
                    result['load_epg']['started'] = True
                m = re.search(r"Loaded channel EPG with id '([^']+)' with display names: '([^']+)'", line)
                if m:
                    epg_id = m.group(1)
                    display_name = m.group(2)
                    result['load_epg']['channels'][epg_id] = {'name': display_name, 'display_names': [display_name]}
                m = re.search(r"Loaded\s+(\d+)\s+channels\s+with\s+(\d+)\s+entries\s+from\s+'([^']+)'", line)
                if m and 'epg' in line.lower():
                    result['load_epg']['epg_channel_count'] = int(m.group(1))
                    result['load_epg']['epg_entry_count'] = int(m.group(2))

                # ===== LoadGenres =====
                m = re.search(r'Loaded\s+(\d+)\s+genres', line)
                if m and 'genre' in line.lower():
                    result['load_genres']['genres_count'] = int(m.group(1))

                # ===== GetChannels =====
                m = re.search(r"GetChannels.*(?:Channel Name|Transfer channel)\s+'([^']+)',\s+ChannelId\s+'(\d+)',\s+ChannelNumber[:\s]+'(\d+)'", line)
                if m:
                    result['get_channels']['channels'][m.group(1)] = {
                        'ChannelId': int(m.group(2)),
                        'ChannelNumber': int(m.group(3))
                    }
                    local_channel_ids.add(int(m.group(2)))

                # ===== GetChannelGroupMembers =====
                # iptvsimple v22: Transfer channel group 'GROUP' member 'NAME', ChannelId 'ID', ChannelOrder: 'N'
                m = re.search(r"GetChannelGroupMembers.*Transfer channel group\s+'([^']+)'\s+member\s+'([^']+)',\s+ChannelId\s+'(\d+)',\s+ChannelOrder[:\s]+'(\d+)'", line)
                if m:
                    ch_group, ch_name, ch_id, ch_order = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
                else:
                    m = re.search(r"GetChannelGroupMembers.*(?:Channel Name|Transfer channel)\s+'([^']+)',\s+ChannelId\s+'(\d+)',\s+ChannelNumber[:\s]+'(\d+)'", line)
                    if m:
                        ch_group, ch_name, ch_id, ch_order = '', m.group(1), int(m.group(2)), int(m.group(3))
                if m and ch_name and ch_id in local_channel_ids:  # only our local instance's channels
                    result['get_group_members']['channels'][ch_name] = {
                        'group': ch_group,
                        'ChannelId': ch_id,
                        'ChannelOrder': ch_order
                    }

                # ===== GetChannelGroups =====
                m = re.search(r"GetChannelGroups.*(?:ChannelGroup Name|Transfer channelGroup)\s+'([^']+)',\s+(?:ChannelGroup)?Id\s+'(\d+)',\s+(?:Type\s+'(\d+)',\s+)?Radio\s+'(\d+)'", line)
                if not m:
                    m = re.search(r"GetChannelGroups.*Transfer channelGroup\s+'([^']+)',\s+ChannelGroupId\s+'(\d+)'", line)
                if m:
                    result['get_channel_groups']['groups'][m.group(1)] = {
                        'id': int(m.group(2)),
                        'type': int(m.group(3)) if m.group(3) else 0,
                        'radio': int(m.group(4)) if m.group(4) else 0
                    }

                # ===== channels_available / radio_available =====
                m = re.search(r"channels available\s+'(\d+)',\s+radio\s*=\s*(\d+)", line)
                if m:
                    if int(m.group(2)) == 1: result['radio_available'] = int(m.group(1))
                    else:                    result['channels_available'] = int(m.group(1))
                m = re.search(r"Channels Available:\s*(\d+)", line)
                if m: result['channels_available'] = int(m.group(1))
                m = re.search(r"Radio Available:\s*(\d+)", line)
                if m: result['radio_available'] = int(m.group(1))

                # ===== recordings_available =====
                m = re.search(r"GetRecordings - media available\s+'(\d+)'", line)
                if m: result['recordings_available'] = int(m.group(1))

                # ===== epg_update_thread =====
                if 'EPGUpdate thread start' in line:
                    result['epg_update_thread'] = True

                # ===== providers_available =====
                m = re.search(r"GetProviders - providers available\s+'(\d+)'", line)
                if m: result['providers_available'] = int(m.group(1))

                # ===== Channel IDs from our addon (slug filter) =====
                m = re.search(r"Adding channel or Media Entry '([^']+)' with URL: .*?chid=([^&]+)", line)
                if m:
                    try:
                        full_id = urllib.parse.unquote(m.group(2))
                        parts = full_id.split('@')
                        chid = parts[0]
                        slug = parts[1] if len(parts) > 1 else None
                        if slug and slug == expected_slug:
                            result['pvr_provider'] = expected_provider
                            if chid and chid not in result['pvr_channel_ids']:
                                result['pvr_channel_ids'].append(chid)
                    except Exception: pass

                m = re.search(r"Loaded channel EPG with id '([^']+)'", line)
                if m:
                    parts = m.group(1).split('@')
                    chid = parts[0]
                    slug = parts[1] if len(parts) > 1 else None
                    if slug and slug == expected_slug:
                        result['pvr_provider'] = expected_provider
                        if chid and chid not in result['pvr_channel_ids']:
                            result['pvr_channel_ids'].append(chid)

            self.log(f"parsePVRLog, connected={result['pvr_connected']}, provider={result['pvr_provider']}, pvr_ids={len(result['pvr_channel_ids'])}, playlist_channels={result['load_playlist']['total_channels']}, epg_channels={result['load_epg']['epg_channel_count']}, get_channels={len(result['get_channels']['channels'])}, group_members={len(result['get_group_members']['channels'])}, channel_groups={len(result['get_channel_groups']['groups'])}, m3u_errors={len(result['m3u_errors'])}, epg_errors={len(result['epg_errors'])}")
            # Derive pvr_events from the parsed log (notifications are unreliable).
            result['pvr_events']['connection']['count'] = len(result['connection_events'])
            if result['connection_events']:
                try:
                    result['pvr_events']['connection']['last_time'] = datetime.datetime.strptime(result['connection_events'][-1]['time'], '%Y-%m-%d %H:%M:%S.%f').timestamp()
                except Exception: pass
            result['pvr_events']['channel_update']['count'] = len(result['get_channels']['channels'])
            result['pvr_events']['group_update']['count']   = len(result['get_channel_groups']['groups'])
            result['pvr_events']['epg_update']['count']     = result['load_epg']['epg_channel_count'] or len(result['load_epg']['channels'])
            return result
        except Exception as e:
            self.log(f"parsePVRLog, error: {e}", xbmc.LOGDEBUG)
            return result
