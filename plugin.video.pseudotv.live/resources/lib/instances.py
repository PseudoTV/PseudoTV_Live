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
from globals    import *
        
class Instances(object):
    def __init__(self, settings):
        self.settings   = settings
        self.properties = settings.properties
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _load(self, file=INSTANCEFLE_DEFAULT):
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
            
            
    def _save(self, file, nsettings={}):
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
        
        
    def getSettings(self, instanceName=ADDON_NAME):
        self.log(f"getSettings {instanceName}")
        return self._load(self.getPVRInstancePath(instanceName))
        
        
    def setSettings(self, instanceName=ADDON_NAME, settings={}, silent=None):
        # https://github.com/xbmc/xbmc/pull/23648 todo proper instance api support when merged.
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
                # instancePath = self.getPVRInstancePath(self.properties.getFriendlyName())
                # if FileAccess.exists(instancePath): FileAccess.delete(instancePath)
                # if FileAccess.move(PVR_SETTINGS_XML, instancePath):
                    # self.settings.dialog.notificationDialog((LANGUAGE(32037)%(addon.getAddonInfo('name'))))
                    # self.properties.setPropTimer('chkPVRRefresh')
        ###
        if silent is None: silent = self.settings.getSettingBool('Enable_Kodi_Access')
        addon = self.settings.hasAddon(PVR_CLIENT_ID,notify=True)
        if self._save(self.getPVRInstancePath(instanceName),settings):
            if not silent: 
                self.settings.dialog.notificationDialog((LANGUAGE(32037)%(addon.getAddonInfo('name'))))
            self.properties.setPropTimer('chkPVRRefresh')
        

    def getPVRInstanceID(self, instanceName=ADDON_NAME):
        #return id within IPTV-Simples limit (32-bit integer).
        return zlib.crc32(instanceName.encode(DEFAULT_ENCODING)) % 2147483648
        
        
    def getPVRInstancePath(self, instanceName=ADDON_NAME):
        instancePath = os.path.join(PVR_CLIENT_LOC,f'instance-settings-{self.getPVRInstanceID(instanceName)}.xml')
        self.log(f"getPVRInstancePath {instanceName} => {instancePath}")
        return instancePath
        
        
    def chkInstances(self, instanceName=ADDON_NAME):
        self.log(f"chkInstances {instanceName}")
        if not self.settings.hasPVRInstance(instanceName):
            #clean abandoned configurations.
            files = [filename for filename in FileAccess.listdir(PVR_CLIENT_LOC)[1] if filename.endswith('.xml')]
            for file in files:
                if file.startswith('instance-settings-'):
                    try:
                        fle = FileAccess.open(os.path.join(PVR_CLIENT_LOC,file), "r")
                        xml = fle.read()
                        fle.close()
                        match = re.compile(r'<setting id=\"kodi_addon_instance_name\" default=\"true\">(.*?)\</setting>', re.IGNORECASE).search(xml)
                        try: name = match.group(1)
                        except Exception:
                            match = re.compile(r'<setting id=\"kodi_addon_instance_name\">(.*?)\</setting>', re.IGNORECASE).search(xml)
                            try: name = match.group(1)
                            except Exception: name = ""
                            
                        if instanceName.lower() == name.replace('%s - '%(ADDON_NAME),'').lower():
                            #auto remove any duplicate entries with the same instance name.
                            FileAccess.delete(os.path.join(PVR_CLIENT_LOC,file))
                            self.log('[%s] chkInstances, removing duplicate entry %s'%(PVR_CLIENT_ID,file))
                    except Exception as e:
                        self.log('[%s] chkInstances, path = %s, failed to open file = %s\n%s'%(PVR_CLIENT_ID,PVR_CLIENT_LOC,file,e))
                        continue


    def IPTV_SIMPLE_SETTINGS(self): #recommended IPTV Simple settings
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