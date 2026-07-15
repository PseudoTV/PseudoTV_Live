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
from typing import Dict, Optional
from variables   import *
from fileaccess  import FileAccess
from pool        import debounceit

_INSTANCE_NAME_RE = re.compile(r'<setting id=\"kodi_addon_instance_name\" default=\"true\">(.*?)\</setting>', re.IGNORECASE)
_INSTANCE_NAME2_RE = re.compile(r'<setting id=\"kodi_addon_instance_name\">(.*?)\</setting>', re.IGNORECASE)
        
class Instances(object):


    def __init__(self, settings: Any):
        self.settings        = settings
        self._cached_status  = None
        self._log_dirty      = True


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def _load(self, file: str = INSTANCEFLE_DEFAULT) -> Dict[str, Optional[str]]:
        """Load settings from an XML file, merging with default IPTV Simple settings."""
        settings = self.IPTV_SIMPLE_SETTINGS()
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
        
    def getSettings(self, instanceName: str = ADDON_NAME) -> Dict[str, Optional[str]]:
        self.log(f"getSettings {instanceName}")
        return self._load(self.getPVRInstancePath(instanceName))
        
    # def setSettings(self, instanceName=ADDON_NAME, settings={}, silent=None):
        # # https://github.com/xbmc/xbmc/pull/23648 todo proper instance api support when merged.
        # addon = xbmcaddon.Addon(PVR_CLIENT_ID)
        # instance_id = self.getPVRInstanceID(instanceName)
        # settings_handle = addon.getSettings(instance_id)
        # for key, value in settings.items():
            # settings_handle.setString(key, value)
        # addon.setInstanceState(instance_id, True, instanceName)
            
    def setSettings(self, instanceName: str = ADDON_NAME, settings: Dict[str, str] = {}, silent: Optional[bool] = None):
        ### kodi api hack | unreliable in piers
        # if isinstance(addon, xbmcaddon.Addon):
            # if FileAccess.exists(PVR_SETTINGS_XML): 
                # FileAccess.delete(PVR_SETTINGS_XML)
                
            # for setting, value in list(settings.items()): 
                # try: 
                    # addon.setSetting(setting,value)
                    # self.log('[%s] setSettings, %s = %s'%(PVR_CLIENT_ID,setting,value))
                # except Exception as e: self.log(f'setSettings failed! {setting}:{value}')
                
            # if FileAccess.exists(PVR_SETTINGS_XML):
                # instancePath = self.getPVRInstancePath(self.settings.properties.getFriendlyName())
                # if FileAccess.exists(instancePath): FileAccess.delete(instancePath)
                # if FileAccess.move(PVR_SETTINGS_XML, instancePath):
                    # self.settings.Globals.dialog.notificationDialog((LANGUAGE(32037).format(name=addon.getAddonInfo('name'))))
                    # self.triggerReload()
        ###
        if silent is None: silent = self.settings.getSettingBool('Enable_Kodi_Access')
        addon = self.settings.hasAddon(PVR_CLIENT_ID,notify=True)
        if self._save(self.getPVRInstancePath(instanceName),settings):
            self.triggerReload()
            if not silent: 
                    Globals.dialog.notificationDialog((LANGUAGE(32037).format(name=addon.getAddonInfo('name'))))
        
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
                
    @debounceit(M3U_REFRESH * 2)
    def triggerReload(self):
        """Trigger IPTV Simple to reload M3U/XMLTV by toggling cache settings.
        
        Toggles both m3uCache and epgCache to force IPTV Simple to re-read files.
        IPTV Simple's Process() loop picks up the change within seconds.
        """
        try:
            addon = xbmcaddon.Addon(PVR_CLIENT_ID)
            m3u_current = addon.getSetting('m3uCache')
            epg_current = addon.getSetting('epgCache')
            addon.setSetting('m3uCache', 'false' if m3u_current == 'true' else 'true')
            addon.setSetting('epgCache', 'false' if epg_current == 'true' else 'true')
            self.log(f"triggerReload, toggled m3uCache={m3u_current}, epgCache={epg_current}", xbmc.LOGINFO)
        except Exception as e:
            self.log(f"triggerReload, error: {e}", xbmc.LOGDEBUG)

    @debounceit(M3U_REFRESH * 2)
    def togglePVRBackend(self, state: bool=False):
        """Toggle PVR backend addon on/off for a full reload.
        
        When re-enabling, sets m3uCache/epgCache to true to force fresh file reads.
        """
        current_state = Globals.builtin.getInfoBool(f"System.AddonIsEnabled({PVR_CLIENT_ID})")
        if current_state == state: return
        self.log(f"togglePVRBackend, transitioning target state to = {state}")
        notification_msg = f"{PVR_CLIENT_NAME}: {LANGUAGE(32125)}"
        Globals.dialog.notificationWait(notification_msg, wait=M3U_REFRESH, usethread=True)
        try:
            payload = { "method": "Addons.SetAddonEnabled", "params": {"addonid": PVR_CLIENT_ID, "enabled": state} }
            self.settings.jsonRPC.sendJSON(payload)
        except Exception as e:
            self.log(f"togglePVRBackend, sendJSON error: {e}", xbmc.LOGDEBUG)
        self.monitor.waitForAbort(M3U_REFRESH)
        Globals.settings.instances.togglePVRBackend(True)
        if state: self.triggerReload()


    def updatePVRStatus(self, host: str, friendly_name: str, wait: int=60) -> dict:
        """Return cached PVR status. M3U/XMLTV data updated by builder.
        TODO: https://github.com/xbmc/xbmc/pull/25711 - Add On Demand status tracking when PVR On Demand API lands (Kodi v23+).
        """
        if host is None: host = Globals.properties.getRemoteHost()
        if friendly_name is None: friendly_name = Globals.properties.getFriendlyName()
        self.log(f"updatePVRStatus, friendly_name = {friendly_name}")
        if self._cached_status is None:
            self._cached_status = {
                'name': friendly_name,
                'm3u':   {'url'        : 'http://%s/%s'%(host, M3UFLE), 
                          'channel_ids': set(), 
                          'last_write' : None, 
                          'sync_state' : 'unknown'},
                          
                'xmltv': {'url'        : 'http://%s/%s'%(host, XMLTVFLE), 
                          'channel_ids': set(), 
                          'last_write' : None, 
                          'sync_state' : 'unknown', 
                          'programmes' : -1},
                'log':   {'pvr_connected'     : False,
                          'm3u_errors'        : [],
                          'epg_errors'        : [],
                          'connection_events' : [],
                          'pvr_channel_ids'   : [],
                          'pvr_provider'      : None,
                          'connect_failed'    : False,
                          'url_check_failed'  : False,
                          'load_playlist'     : {'started': False, 'total_channels': 0, 'channels': [], 'groups': {}, 'providers': {}, 'media_items': 0},
                          'load_epg'          : {'started': False, 'channels': {}, 'epg_channel_count': 0, 'epg_entry_count': 0},
                          'load_genres'       : {'genres_count': 0},
                          'get_channels'      : {'channels': {}},
                          'get_group_members' : {'channels': {}},
                          'get_channel_groups': {'groups': {}},
                          'channels_available': 0,
                          'radio_available'   : 0,
                          'pvr_errors'        : [],
                          'last_update'       : -1},
                          
                'notifications': {'last_event': None, 
                                  'last_time': None, 
                                  'events': []},
                'in_sync': False  # True when PVR loaded IDs == M3U IDs == XMLTV IDs (computed by _computeDerived)
            }
        status = self._cached_status
        try:
            if status['log']['pvr_connected'] and status['in_sync']: wait = 300
            if self._log_dirty or (time.time() - status['log']['last_update']) > wait:
                pvr_log = self.parsePVRLog(host, friendly_name)
                # Merge parsed PVR channel IDs with existing ones (log window may not cover all entries)
                existing_ids = status['log'].get('pvr_channel_ids', [])
                new_ids = pvr_log.get('pvr_channel_ids', [])
                pvr_log['pvr_channel_ids'] = list(dict.fromkeys(existing_ids + new_ids))
                status['log'].update(pvr_log)
                status['log']['last_update'] = time.time()
                self._log_dirty = False
            self._computeDerived(status)
            m3u_count = len(status['m3u'].get('channel_ids', set()))
            xmltv_count = len(status['xmltv'].get('channel_ids', set()))
            xmltv_progs = status['xmltv'].get('programmes', 0)
            self.log(f"updatePVRStatus, m3u={m3u_count}ch/{status['m3u']['sync_state']}, xmltv={xmltv_count}ch/{xmltv_progs}prog/{status['xmltv']['sync_state']}, pvr_connected={status['log']['pvr_connected']}")
            if status['m3u']['unloaded_by_pvr']:
                self.log(f"updatePVRStatus, M3U channels missing from PVR client: {status['m3u']['unloaded_by_pvr']}", xbmc.LOGWARNING)
            if status['m3u'].get('missing_epg'):
                self.log(f"updatePVRStatus, {len(status['m3u']['missing_epg'])} channels with no EPG data: {status['m3u']['missing_epg']}", xbmc.LOGWARNING)
            # Trigger PVR refresh when out of sync (non-blocking, debounced via prop timer)
            if not status.get('in_sync', False) and status['log'].get('pvr_connected', False):
                xbmcgui.Window(10000).setProperty('%s.chkPVRRefresh' % ADDON_ID, FileAccess.dumpJSON({'s': True, 'a': [], 'k': {}})) #globals hasn't finished __init__
            # Convert sets to lists for JSON serialization (json.dumps raises TypeError on sets)
            status['m3u']['channel_ids'] = list(status['m3u'].get('channel_ids', set()))
            status['xmltv']['channel_ids'] = list(status['xmltv'].get('channel_ids', set()))
            return status
        except Exception as e:
            self.log(f"updatePVRStatus, error: {e}", xbmc.LOGDEBUG)
            return status


    def setLogDirty(self):
        """Mark log status as needing reparse."""
        self._log_dirty = True


    def _computeDerived(self, status: dict):
        """Compute derived status fields from raw M3U/XMLTV/log data.

        Status dict structure (set by updatePVRStatus, m3u.py, xmltvs.py, services.py):
          status['m3u']:
            'url'             - str   - M3U URL served by HTTP server
            'channel_ids'     - set   - channel IDs from saved M3U (set by m3u.py after write)
            'last_write'      - float - timestamp of last M3U file write (set by m3u.py)
            'channels'        - int   - channel count 
            'sync_state'      - str   - 'fresh'/'stale'/'outdated'/'unknown' 
            'missing_epg'     - list  - channel IDs loaded by PVR but with no EPG data 
            'unloaded_by_pvr' - list  - channel IDs not loaded by PVR client 

          status['xmltv']:
            'url'                - str   - XMLTV URL served by HTTP server
            'channel_ids'        - set   - channel IDs from saved XMLTV (set by xmltvs.py after write)
            'last_write'         - float - timestamp of last XMLTV file write (set by xmltvs.py)
            'programmes'         - int   - total programme count (set by xmltvs.py)
            'channels'           - int   - channel count 
            'sync_state'         - str   - 'fresh'/'stale'/'outdated'/'unknown' 
            'missing_from_local' - list  - XMLTV channel IDs not in local M3U 
            'empty_channels'     - list  - XMLTV channel IDs with no programmes 

          status['log']:
            'pvr_connected'     - bool  - is PVR client connected
            'm3u_errors'        - list  - M3U load error strings
            'epg_errors'        - list  - EPG load error strings
            'connection_events' - list  - connection state change dicts
            'pvr_channel_ids'   - list  - channel IDs from our addon only, filtered by slug
            'pvr_provider'      - str   - full provider name, e.g. 'PseudoTV Live (Kodi Desktop)'
            'connect_failed'    - bool  - connection attempt failed
            'url_check_failed'  - bool  - URL connection check failed
            'load_playlist'     - dict  - LoadPlayList parsed data (started, total_channels, channels, groups, providers, media_items)
            'load_epg'          - dict  - LoadChannelEpgs parsed data (started, channels, epg_channel_count, epg_entry_count)
            'load_genres'       - dict  - LoadGenres parsed data (genres_count)
            'get_channels'      - dict  - GetChannels parsed data (channels: {name: {ChannelId, ChannelNumber}})
            'get_group_members' - dict  - GetChannelGroupMembers parsed data (channels: {name: {ChannelId, ChannelNumber}})
            'get_channel_groups'- dict  - GetChannelGroups parsed data (groups: {name: {id, type, radio}})
            'channels_available'- int   - channels available count from PVR
            'radio_available'   - int   - radio channels available count from PVR
            'last_update'       - float - timestamp of last log parse
            'pvr_errors'        - list  - combined m3u_errors + epg_errors 

          status['notifications']:
            'last_event' - str  - last PVR notification method name (set by services.py)
            'last_time'  - float - timestamp of last PVR notification (set by services.py)
            'events'     - list  - last 50 notification dicts (set by services.py)

          status['in_sync'] - bool - True when PVR loaded IDs == M3U IDs == XMLTV IDs 

          status['last_update'] - float - timestamp of last updatePVRStatus call
        """
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

        # M3U channels not in XMLTV (missing EPG data - channels without guide info)
        status['m3u']['missing_epg'] = list(m3u_ids - xmltv_ids)

        # XMLTV channels not in local M3U (orphans from PVR or stale data)
        status['xmltv']['missing_from_local'] = list(xmltv_ids - m3u_ids)

        # M3U channels not loaded by PVR (set difference: our IDs minus PVR's loaded IDs)
        pvr_ids = set(status['log'].get('pvr_channel_ids', []))
        channels_loaded = status['log'].get('load_playlist', {}).get('total_channels', 0)
        m3u_id_list = list(m3u_ids)
        if m3u_ids and pvr_ids:
            status['m3u']['unloaded_by_pvr'] = list(m3u_ids - pvr_ids)
        elif m3u_ids and channels_loaded > 0 and channels_loaded < len(m3u_id_list):
            # Fallback: no parsed IDs, use count-based estimate
            status['m3u']['unloaded_by_pvr'] = m3u_id_list[channels_loaded:]
        else:
            status['m3u']['unloaded_by_pvr'] = []

        # Channels loaded by PVR but with no EPG data (guide entries missing)
        pvr_ids_set  = set(status['log'].get('pvr_channel_ids', []))
        epg_ids_set  = set(status['log'].get('load_epg', {}).get('channels', {}).keys())
        status['m3u']['missing_epg'] = list(pvr_ids_set - epg_ids_set)

        # XMLTV channels with no programmes (placeholder - needs per-channel programme counts)
        status['xmltv']['empty_channels'] = []

        # Combined PVR error list from M3U and EPG load failures
        status['log']['pvr_errors'] = status['log'].get('m3u_errors', []) + status['log'].get('epg_errors', [])

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
        }

        expected_provider = f"{ADDON_NAME} ({friendly_name})" if friendly_name else None
        expected_slug = re.sub(r'[\s_-]+', '_', re.sub(r'[^\w\s-]', '', ADDON_NAME.strip()))

        try:
            fle = FileAccess.open(log_path, 'r')
            all_lines = fle.readlines()
            fle.close()

            in_load_playlist = False
            current_extinf = None

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
                if 'ConnectionLost' in line:
                    result['pvr_connected'] = False
                if 'ConnectionEstablished' in line:
                    result['pvr_connected'] = True
                if 'unable to connect to' in line:
                    result['connect_failed'] = True
                if 'Check Unable to open url' in line:
                    result['url_check_failed'] = True

                # --- M3U / EPG load errors ---
                if 'Unable to load playlist cache file' in line:
                    if host and host in line:
                        result['m3u_errors'].append(line[-200:])
                if 'Unable to load EPG file' in line:
                    if host and host in line:
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
                m = re.search(r"GetChannels.*Channel Name\s+'([^']+)',\s+ChannelId\s+'(\d+)',\s+ChannelNumber\s+'(\d+)'", line)
                if m:
                    result['get_channels']['channels'][m.group(1)] = {
                        'ChannelId': int(m.group(2)),
                        'ChannelNumber': int(m.group(3))
                    }

                # ===== GetChannelGroupMembers =====
                m = re.search(r"GetChannelGroupMembers.*Channel Name\s+'([^']+)',\s+ChannelId\s+'(\d+)',\s+ChannelNumber\s+'(\d+)'", line)
                if m:
                    result['get_group_members']['channels'][m.group(1)] = {
                        'ChannelId': int(m.group(2)),
                        'ChannelNumber': int(m.group(3))
                    }

                # ===== GetChannelGroups =====
                m = re.search(r"GetChannelGroups.*ChannelGroup Name\s+'([^']+)',\s+Id\s+'(\d+)',\s+Type\s+'(\d+)',\s+Radio\s+'(\d+)'", line)
                if m:
                    result['get_channel_groups']['groups'][m.group(1)] = {
                        'id': int(m.group(2)),
                        'type': int(m.group(3)),
                        'radio': int(m.group(4))
                    }

                # ===== channels_available / radio_available =====
                m = re.search(r"Channels Available:\s*(\d+)", line)
                if m: result['channels_available'] = int(m.group(1))
                m = re.search(r"Radio Available:\s*(\d+)", line)
                if m: result['radio_available'] = int(m.group(1))

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
            return result
        except Exception as e:
            self.log(f"parsePVRLog, error: {e}", xbmc.LOGDEBUG)
            return result
