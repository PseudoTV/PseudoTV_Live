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
        self.settings = settings

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
                    # self.settings.Globals.dialog.notificationDialog((LANGUAGE(32037)%(addon.getAddonInfo('name'))))
                    # self.triggerReload()
        ###
        if silent is None: silent = self.settings.getSettingBool('Enable_Kodi_Access')
        addon = self.settings.hasAddon(PVR_CLIENT_ID,notify=True)
        if self._save(self.getPVRInstancePath(instanceName),settings):
            self.triggerReload()
            if not silent: 
                Globals.dialog.notificationDialog((LANGUAGE(32037)%(addon.getAddonInfo('name'))))
        
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
        return {'startNum'                      :'1',
                'numberByOrder'                 :'false',
                'm3uRefreshMode'                :'1',
                'm3uRefreshIntervalMins'        :'%s'%(M3U_REFRESH),
                'm3uRefreshHour'                :'0',
                'connectioncheckinterval'       :'%s'%(M3U_INTERVAL),
                'connectionchecktimeout'        :'%s'%(M3U_TIMEOUT),
                'defaultProviderName'           :ADDON_NAME,
                'enableProviderMappings'        :'true',
                'providerMappingFile'           :PROVIDERFLE_DEFAULT,
                # 'tvGroupMode'                 :'0',
                # 'customTvGroupsFile'          :(TVGROUPFLE),#todo
                # 'radioGroupMode'              :'0',
                # 'customRadioGroupsFile'       :(RADIOGROUPFLE),#todo
                'useEpgGenreText'               :'true',
                'logoFromEpg'                   :'2',
                'mediaTitleSeasonEpisode'       :'true',
                'timeshiftEnabled'              :'false',
                'catchupEnabled'                :'true',
                'catchupPlayEpgAsLive'          :'false',
                'catchupWatchEpgEndBufferMins'  :'0',
                'catchupWatchEpgBeginBufferMins':'0',
                'useFFmpegReconnect'            :'false',
                'useInputstreamAdaptiveforHls'  :'false',
                'transformMulticastStreamUrls'  :'false',}
                
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
            self.log(f"triggerReload failed! {e}", xbmc.LOGERROR)

    @debounceit(M3U_REFRESH * 2)
    def togglePVRBackend(self, state: bool):
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
            self.log(f"togglePVRBackend, sendJSON failed: {e}", xbmc.LOGWARNING)
        if state:
            try:
                addon = xbmcaddon.Addon(PVR_CLIENT_ID)
                addon.setSetting('m3uCache', 'true')
                addon.setSetting('epgCache', 'true')
            except Exception: pass

    def chkPVRStatus(self) -> dict:
        """Check PVR sync status by parsing log and comparing file stats."""
        status = {
            'm3u':   {'file': None, 'channels': 0, 'last_write': None, 'sync_state': 'unknown'},
            'xmltv': {'file': None, 'programmes': 0, 'last_write': None, 'sync_state': 'unknown'},
            'log':   {'errors': 0, 'warnings': 0, 'pvr_errors': [], 'last_scan': None}
        }
        try:
            m3u_path = FileAccess.translatePath(os.path.join(SETTINGS_LOC, 'cache', 'pseudotv.m3u'))
            xmltv_path = FileAccess.translatePath(os.path.join(SETTINGS_LOC, 'cache', 'pseudotv.xml'))
            log_path = FileAccess.translatePath('special://logpath/kodi.log')
            
            if FileAccess.exists(m3u_path):
                try:
                    stat = os.stat(m3u_path)
                    status['m3u']['file'] = m3u_path
                    status['m3u']['last_write'] = stat.st_mtime
                    with FileAccess.open(m3u_path, 'r') as f:
                        status['m3u']['channels'] = f.read().count('#EXTINF')
                except Exception: pass
                    
            if FileAccess.exists(xmltv_path):
                try:
                    stat = os.stat(xmltv_path)
                    status['xmltv']['file'] = xmltv_path
                    status['xmltv']['last_write'] = stat.st_mtime
                    with FileAccess.open(xmltv_path, 'r') as f:
                        content = f.read()
                        status['xmltv']['channels'] = content.count('<channel')
                        status['xmltv']['programmes'] = content.count('<programme')
                except Exception: pass
                    
            if FileAccess.exists(log_path):
                try:
                    fle = FileAccess.open(log_path, 'r')
                    all_lines = fle.readlines()[-200:]
                    fle.close()
                    error_count = warning_count = 0
                    for line in all_lines:
                        line = line.strip()
                        if not line: continue
                        if 'error' in line.lower():     error_count += 1
                        elif 'warning' in line.lower(): warning_count += 1
                        if 'error' in line.lower() and ('pseudotv' in line.lower() or 'pvr' in line.lower()):
                            try: status['log']['pvr_errors'].append(re.sub(r'\x1b\[[0-9;]*m', '', line)[-200:])
                            except Exception: pass
                    status['log']['errors'] = error_count
                    status['log']['warnings'] = warning_count
                except Exception: pass
            
            m3u_age   = (time.time() - status['m3u']['last_write'])   if status['m3u']['last_write']   else float('inf')
            xmltv_age = (time.time() - status['xmltv']['last_write']) if status['xmltv']['last_write'] else float('inf')
            status['m3u']['sync_state']   = 'fresh' if m3u_age < 300 else ('stale' if m3u_age < 3600 else 'outdated')
            status['xmltv']['sync_state'] = 'fresh' if xmltv_age < 300 else ('stale' if xmltv_age < 3600 else 'outdated')
            
            m3u_channels   = status['m3u'].get('channels', 0)
            xmltv_channels = status['xmltv'].get('channels', 0)
            xmltv_programs = status['xmltv'].get('programmes', 0)
            self.log(f"chkPVRStatus, m3u={m3u_channels}ch/{status['m3u']['sync_state']}, xmltv={xmltv_channels}ch/{xmltv_programs}prog/{status['xmltv']['sync_state']}")
            return status
        except Exception as e:
            self.log(f"chkPVRStatus, failed: {e}", xbmc.LOGERROR)
            return status
