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
from typing import Any, Optional, Union, Iterator, Callable
from variables   import *
from _services   import _Service
from fileaccess  import FileAccess
from cache       import cacheit
from pool        import debounceit, timerit, poolit, threadit
from instances   import Instances
import threading

_Globals = None
def _globals() -> Any:
    global _Globals
    if _Globals is None:
        from variables import Globals as _Globals
    return _Globals

_ADDON_DATA_RE  = re.compile(r'special://profile/addon_data/(.*?)', re.IGNORECASE)
_ADDON_HOME_RE  = re.compile(r'special://home/addons/(.*?)/resources', re.IGNORECASE)
_ADDON_PROTO_RE = re.compile(r'(.*)://(.*?)/', re.IGNORECASE)
_PROGRESS_RE    = re.compile(r'(.*?):\s+(\d+)\%', re.IGNORECASE)
_PROGRESS_THROTTLE = {}

class Settings(object):
    dialog = None
    
    def __init__(self, service: Optional[_Service] = None):
        if service is None: service = _Service()
        self.pool      = service.pool
        self.cache     = service.cache
        self.jsonRPC   = service.jsonRPC
        self.monitor   = service.monitor
        self.instances = Instances(settings=self)

        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s'%(self.__class__.__name__,msg),level)
        


    def _getRealSettings(self, id: str = ADDON_ID) -> xbmcaddon.Addon:
        try: return xbmcaddon.Addon(id)
        except Exception as e: 
            self.log(f'_getRealSettings, failed to create Addon({id}), falling back to REAL_SETTINGS: {e}', xbmc.LOGWARNING)
            return REAL_SETTINGS

    #GET


    def _getSetting(self, func: Callable, key: str) -> Any:
        try: 
            value = func(key)
            self.log(f'[{ADDON_ID}] {func.__name__}, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
            return value
        except Exception as e: self.log("_getSetting, failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
      
      
    def getSetting(self, key: str) -> str:
        return self._getSetting(self._getRealSettings().getSetting,key)
        
        
    def getSettingBool(self, key: str) -> bool:
        return self._getSetting(self._getRealSettings().getSettingBool,key)


    def getSettingInt(self, key: str) -> int:
        return self._getSetting(self._getRealSettings().getSettingInt,key)
              
              
    def getSettingNumber(self, key: str) -> float:
        return self._getSetting(self._getRealSettings().getSettingNumber,key)
        
        
    def getSettingString(self, key: str) -> str:
        return self._getSetting(self._getRealSettings().getSettingString,key)


    def getSettingFloat(self, key: str) -> float:
        return float(self.getSetting(key))
              
              
    def getSettingList(self, key: str) -> list:
        return [value for value in self.getSetting(key).split('|')]
       
       
    def getSettingBoolList(self, key: str) -> list:
        return [value.lower() == "true" for value in self.getSetting(key).split('|')]
        
        
    def getSettingIntList(self, key: str) -> list:
        return [int(value) for value in self.getSetting(key).split('|') if isinstance(value,int)]
        
        
    def getSettingNumberList(self, key: str) -> list:
        return [literal_eval(value) for value in self.getSetting(key).split('|')]
        


    def getSettingFloatList(self, key: str) -> list:
        return [float(value) for value in self.getSetting(key).split('|') if isinstance(value,float)]
        


    def getSettingDict(self, key: str) -> dict:
        return FileAccess._decodeString(self.getSetting(key))
    
    
    def getCacheSetting(self, key: str, checksum: Optional[str] = None, default: Any = None) -> Any:
        if checksum is None: checksum = ADDON_VERSION
        value = self.cache.get(key, checksum)
        self.log(f'[{ADDON_ID}] getCacheSetting, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return (value or default)
        
        
    def getEXTSetting(self, id: str, key: str) -> str:
        value = xbmcaddon.Addon(id).getSetting(key)
        self.log(f'[{ADDON_ID}] getEXTSetting, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return value
        
        
    #CLR
    def clrCacheSetting(self, key: str):
        self.cache.clr(key)
    
    
    #SET
    def _setSetting(self, func: Callable, key: str, value: Any):
        try:
            func(key, value)
            self.log(f'[{ADDON_ID}] {func.__name__}, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        except Exception as e: self.log("_setSetting, failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
            
        
    def setSetting(self, key: str, value: str = "") -> str:
        self._setSetting(self._getRealSettings().setSetting,key,str(value))
        return value
            
            
    def setSettingBool(self, key: str, value: bool):
        return self._setSetting(self._getRealSettings().setSettingBool,key,value)
        
        
    def setSettingInt(self, key: str, value: int):
        return self._setSetting(self._getRealSettings().setSettingInt,key,value)
                   
                   
    def setSettingNumber(self, key: str, value: float):
        return self._setSetting(self._getRealSettings().setSettingNumber,key,value)
        
             
    def setSettingString(self, key: str, value: str):
        return self._setSetting(self._getRealSettings().setSettingString,key,value)


    def setSettingBoolList(self, key: str, value: list) -> str:
        return self.setSetting(key,('|').join(value))
        
        
    def setSettingIntList(self, key: str, value: list) -> str:
        return self.setSetting(key,('|').join(value))
         
            
    def setSettingNumberList(self, key: str, value: list) -> str:
        return self.setSetting(key,('|').join(value))
        


    def setSettingList(self, key: str, values: list) -> str:
        return self.setSetting(key,('|').join(values))
                   
                   
    def setSettingFloat(self, key: str, value: float) -> str:
        return self.setSetting(key,value)
        
        
    def setSettingDict(self, key: str, values: dict) -> str:
        return self.setSetting(key,FileAccess._encodeString(values))
            
            
    def setCacheSetting(self, key: str, value: Any = None, checksum: Optional[str] = None, life: datetime.timedelta = datetime.timedelta(days=28)) -> bool:
        if checksum is None: checksum = ADDON_VERSION
        self.log(f'[{ADDON_ID}] setCacheSetting, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return self.cache.set(key, value, checksum, life)
  
  
    def setEXTSetting(self, id: str, key: str, value: str):
        self.log(f'[{ADDON_ID}] setEXTSetting, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return xbmcaddon.Addon(id).setSetting(key,value)


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def getIP(self, default: str = '0.0.0.0') -> str:
        IP = (xbmc.getIPAddress() or gethostbyname(gethostname()) or default)
        self.log('getIP, IP = %s'%(IP))
        return IP
    
    
    def hasAddon(self, id: str, install: Optional[bool] = None, enable: Optional[bool] = None, force: Optional[bool] = None, notify: bool = False) -> bool:
        def __getIDbyPath(url: str) -> str:
            try:
                if   url.startswith('special://profile/addon_data/'):      return _ADDON_DATA_RE.search(url).group(1)
                elif url.startswith('special://home/addons/'):             return _ADDON_HOME_RE.search(url).group(1)
                elif url.startswith(('plugin://','resource://','pvr://')): return _ADDON_PROTO_RE.search(url).group(2)
            except Exception as e: self.log('__getIDbyPath regex failed: %s' % e, xbmc.LOGDEBUG)
            return url
            
        def __hasADDON(id: str) -> bool:
            if not id: return False
            hasAddon  = self.dialog.builtin.getInfoBool('System.HasAddon(%s)'%(id))
            isEnabled = self.dialog.builtin.getInfoBool('System.AddonIsEnabled(%s)'%(id))
            self.log(f'[{id}] hasAddon = {hasAddon}, isEnabled = {isEnabled}, Kodi Override = {bypass}')
            if hasAddon:
                if isEnabled: return True
                elif enable:
                    if not force:
                        if not self.dialog.yesnoDialog(message=LANGUAGE(32156).format(name=id)):
                            self.log('[%s] hasAddon, (Not Enabled!)'%(id))
                            return isEnabled
                    self.dialog.builtin.executebuiltin(f'EnableAddon({id})',wait=True)
                elif notify: self.dialog.notificationDialog(LANGUAGE(32264).format(name=id))
            elif install: self.dialog.builtin.executebuiltin(f'InstallAddon({id})',wait=True)
            elif notify:  self.dialog.notificationDialog(LANGUAGE(32034).format(name=id))
            return self.dialog.builtin.getInfoBool(f'System.HasAddon({id})')
        
        bypass = self.getSettingBool('Enable_Kodi_Access')
        if install is None: install = bypass
        if enable  is None: enable  = bypass
        if force   is None: force   = bypass
        if '://' in id: id = __getIDbyPath(id)
        return __hasADDON(id)
            
            
    @cacheit(expiration=datetime.timedelta(minutes=15))
    def getAddonDetails(self, id: str = ADDON_ID) -> dict:
        try:
            if not id: raise Exception("Missing ID")
            addon = xbmcaddon.Addon(id)
            properties = ['name', 'version', 'summary', 'description', 'path', 'author', 'icon', 'disclaimer', 'fanart', 'changelog', 'id', 'profile', 'stars', 'type']
            return dict([(property,addon.getAddonInfo(property)) for property in properties])
        except Exception:
            return self.jsonRPC.getAddonDetails(id)


    def getMYUUID(self) -> str:
        def __genUUID(seed: Optional[str] = None) -> str:
            if seed:
                m = hashlib.md5()
                m.update(seed.encode(DEFAULT_ENCODING))
                return str(UUID(m.hexdigest()))
            return str(uuid1(clock_seq=70420))
            
        friendly = self.dialog.properties.getFriendlyName()
        uuid = self.getCacheSetting('MY_UUID', checksum=friendly, default=None)
        if not uuid: uuid = self.setCacheSetting('MY_UUID', __genUUID(seed=self.dialog.properties.getFriendlyName()), checksum=friendly)
        return uuid


    def getBonjour(self) -> dict:
        def __getResumeURLs(remote: str) -> list:
            keys = self.getCacheSetting(RESUME_INDEX, FileAccess._getMD5(RESUME_INDEX), default={})
            return ['http://%s/filelist/%s'%(remote,key) for key in keys]
            
        host    = self.dialog.properties.getRemoteHost()
        payload = {'id'       :ADDON_ID,
                   'host'     :host,
                   'uuid'     :self.getMYUUID(),
                   'name'     :self.dialog.properties.getFriendlyName(),
                   'version'  :ADDON_VERSION,
                   'machine'  :platform.machine(),
                   'platform' :self.dialog.builtin.getInfoLabel('System.OSVersionInfo',retries=3),
                   'build'    :self.dialog.builtin.getInfoLabel('System.BuildVersion',retries=3),
                   'python'   :platform.python_version(),
                   'remotes'  : {'m3u'     :'http://%s/%s'%(host,M3UFLE),
                                 'xmltv'   :'http://%s/%s'%(host,XMLTVFLE),
                                 'genre'   :'http://%s/%s'%(host,GENREFLE),
                                 'bonjour' :'http://%s/api/%s'%(host,BONJOURFLE),
                                 'servers' :'http://%s/api/%s'%(host,SERVERFLE),
                                 'library' :'http://%s/api/%s'%(host,LIBRARYFLE),
                                 'channels':'http://%s/api/%s'%(host,CHANNELFLE),
                                 'pvr'     :'http://%s/api/%s'%(host,PVRFLE),
                                 'logs'    :'http://%s/api/%s'%(host,LOGSFLE),
                                 'resume'  : __getResumeURLs(host)},
                                 'settings' : {'Resource_Logos'    :self.getSetting('Resource_Logos').split('|'),
                                  'Resource_Bumpers'  :self.getSetting('Resource_Bumpers').split('|'),
                                  'Resource_Ratings'  :self.getSetting('Resource_Ratings').split('|'),
                                  'Resource_Adverts'  :self.getSetting('Resource_Adverts').split('|'),
                                  'Resource_Trailers' :self.getSetting('Resource_Trailers').split('|')}}
                   
        # MD5 from stable fields only (exclude volatile 'md5', 'updated', 'resume')
        stable = {k: v for k, v in payload.items() if k not in ('md5', 'updated', 'resume')}
        payload['md5']     = FileAccess._getMD5(FileAccess.dumpJSON(stable))
        payload['updated'] = datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
        self.log("getBonjour:\npayload = %s"%(payload))
        return payload


    # @cacheit(expiration=datetime.timedelta(minutes=5))
    # def getPayload(self, inclDebug: bool=False):
        # self.log("getPayload, inclDebug! %s"%(inclDebug))
        # def __getMeta(payload):
            # from m3u         import M3U
            # from xmltvs      import XMLTVS
            # from library     import Library
            # from multiroom   import Multiroom
            # xmltv = XMLTVS()
            # payload.pop('updated')
            # payload.pop('md5')
            # payload['m3u'] = M3U().getM3U()
            # stations = xmltv.getChannels()
            # recordings = xmltv.getRecordings()
            # payload['xmltv']   = {'stations'  :[{'id':station.get('id'),'display-name':station.get('display-name',[['','']])[0][0],'icon':station.get('icon',[{'src':LOGO}])[0].get('src',LOGO)} for station in stations],
                                  # 'recordings':[{'id':recording.get('id'),'display-name':recording.get('display-name',[['','']])[0][0],'icon':recording.get('icon',[{'src':LOGO}])[0].get('src',LOGO)} for recording in recordings], 
                                  # 'programmes':[{'id':key,'end-time':_globals()._epochTime(time.time(),tz=False).strftime(DTFORMAT)} for key, value in list(dict(xmltv.loadStopTimes()).items())]}
            # payload['library'] = Library().getLibrary()
            # payload['servers'] = Multiroom().getServers()
            # del xmltv
            # return payload

        # payload = __getMeta(self.getBonjour())
        # if inclDebug: payload['debug'] = FileAccess.loadJSON(self.property.getProperty('debug.log')).get('DEBUG',{})
        # payload['updated']   = datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
        # payload['md5']       = FileAccess._getMD5(FileAccess.dumpJSON(payload))
        # return payload

            
    # @cacheit(expiration=datetime.timedelta(minutes=5))
    # def getPayloadUI(self):
        # return self.getPayload(inclDebug=True)


    def hasAutotuned(self) -> bool:
        return self.dialog.properties.setProperty('has.Autotuned',self.getCacheSetting('has.Autotuned', default=False))
        
        
    def setAutotuned(self, state: bool = True) -> bool:
        return self.dialog.properties.setProperty('has.Autotuned',self.setCacheSetting('has.Autotuned', state, life=datetime.timedelta(days=MAX_GUIDEDAYS)))


    def setPVRPath(self, path: str, instanceName: str = ADDON_NAME):
        settings  = self.instances.getSettings(instanceName)
        nsettings = {'kodi_addon_instance_name'   : '%s - %s'%(ADDON_NAME,instanceName),
                     'kodi_addon_instance_enabled':'true',
                     'm3uPathType'                :'0',
                     'm3uPath'                    :os.path.join(path,M3UFLE),
                     'm3uCache'                   :'false',
                     'epgPathType'                :'0',
                     'epgPath'                    :os.path.join(path,XMLTVFLE),
                     'epgCache'                   :'true',
                     'genresPathType'             :'0',
                     'genresPath'                 :os.path.join(path,GENREFLE),
                     'logoPathType'               :'0',
                     'logoPath'                   :os.path.join(path,'logos')}
        settings.update(self.instances.IPTV_SIMPLE_SETTINGS())
        settings.update(nsettings)
        if self.chkPVRChanges(instanceName, settings.copy()):
            self.log('[%s] setPVRPath, %s settings = %s'%(PVR_CLIENT_ID, instanceName, nsettings))
            return self.instances.setSettings(instanceName, settings)
        
                
    def setPVRLocal(self, host: str, instanceName: str = ADDON_NAME):
        settings  = self.instances.getSettings(instanceName)
        nsettings = {'kodi_addon_instance_name'   : '%s - %s'%(ADDON_NAME,instanceName),
                     'kodi_addon_instance_enabled':'true',
                     'm3uPathType'                :'1',
                     # 'm3uUrl'                     :'http://%s/%s.%s'%(host,M3UFLE,processID),
                     'm3uUrl'                     :'http://%s/%s'%(host,M3UFLE),
                     'm3uCache'                   :'false',
                     'epgPathType'                :'1',
                     'epgUrl'                     :'http://%s/%s'%(host,XMLTVFLE),
                     'epgCache'                   :'true',
                     'genresPathType'             :'1',
                     'genresUrl'                  :'http://%s/%s'%(host,GENREFLE),
                     'logoPathType'               :'1',
                     'logoBaseUrl'                :'http://%s/logos'%(host)}
        settings.update(self.instances.IPTV_SIMPLE_SETTINGS())
        settings.update(nsettings)
        if self.chkPVRChanges(instanceName, settings.copy()):
            self.log('[%s] setPVRLocal, %s settings = %s'%(PVR_CLIENT_ID, instanceName, nsettings))
            return self.instances.setSettings(instanceName, settings)
        
        
    def setPVRRemote(self, host: str, instanceName: str = ADDON_NAME, cache: bool = True):
        settings  = self.instances.getSettings(instanceName)
        nsettings = {'kodi_addon_instance_name'   : '%s - %s'%(ADDON_NAME,instanceName),
                     'kodi_addon_instance_enabled':'true',
                     'm3uPathType'                :'1',
                     'm3uUrl'                     :'http://%s/%s'%(host,M3UFLE),
                     'm3uCache'                   :'%s'%(str(cache).lower()),
                     'epgPathType'                :'1',
                     'epgUrl'                     :'http://%s/%s'%(host,XMLTVFLE),
                     'epgCache'                   :'%s'%(str(cache).lower()),
                     'genresPathType'             :'1',
                     'genresUrl'                  :'http://%s/%s'%(host,GENREFLE),
                     'logoPathType'               :'1',
                     'logoBaseUrl'                :'http://%s/logos'%(host)}
        settings.update(nsettings)
        if self.chkPVRChanges(instanceName, settings.copy()):
            self.log('[%s] setPVRRemote, %s settings = %s'%(PVR_CLIENT_ID, instanceName, nsettings))
            return self.instances.setSettings(instanceName, settings)


    def chkPVRChanges(self, instanceName: str = ADDON_NAME, nsettings: dict = {}, prompt: Optional[bool] = None) -> bool:
        if prompt is None: prompt = not bool(self.getSettingBool('Enable_Kodi_Access'))
        changes = []
        if self.instances.hasPVRInstance(instanceName):
            xsettings = self.instances.getSettings(instanceName)
            for setting, value in list(nsettings.items()):
                if    str(value).lower() == str(xsettings.get(setting,'')).lower(): nsettings.pop(setting)
                else: changes.append('%s: [COLOR=dimgray][B]%s[/B][/COLOR] => [COLOR=green][B]%s[/B][/COLOR]'%(setting,str(xsettings.get(setting)),str(value)))

        if len(nsettings) > 0:
            if prompt:
                self.dialog.textviewer('%s\n\n%s'%(LANGUAGE(32035).format(name=PVR_CLIENT_NAME),'[CR]'.join(changes)))
                if not self.dialog.yesnoDialog((LANGUAGE(32036).format(name=addon.getAddonInfo('name')))):
                    self.dialog.notificationDialog(LANGUAGE(32046))
                    return False
            self.log('[%s] chkPVRChanges, instanceName = %s, prompt = %s, changes = %s'%(PVR_CLIENT_ID,instanceName,prompt,nsettings))
            return True
        self.log('[%s] chkPVRChanges, no changes detected!'%(PVR_CLIENT_ID))
        return False
        


    def getCurrentSettings(self) -> dict:
        settings = ['User_Folder', 'Debug_Enable', 'TCP_PORT', 'Enable_Autotune', 'Remove_BG_APIKEY', 'Open_Router_APIKEY', 'Enable_Kodi_Access']
        return dict([(setting,self.getSetting(setting)) for setting in settings])
              
              
    def restoreSettings(self, settings: dict = {}) -> bool:
        return any(self.setSetting(k,v) for k,v in list(settings.items()))


    def getFileCRC(self, file: str) -> bool:
        try:
            fle = FileAccess.open(file,'r')
            crc = binascii.crc32(fle.read().encode(DEFAULT_ENCODING))
        except Exception as e:
            self.log("getFileCRC, failed! %s %s"%(file,e), xbmc.LOGERROR)
            return False
        finally:
            fle.close()
        name  = 'getFileCRC.%s'%(FileAccess._getMD5(file))
        cache = self.getCacheSetting(name, checksum=crc)
        if not cache or cache != crc:
            self.setCacheSetting(name, crc, checksum=crc)
            return True
        return False
            
            
    def getLogs(self, time: Optional[datetime.datetime] = None) -> dict:
        if time is None: time = datetime.datetime.fromtimestamp(time.time())
        return self.getCacheSetting('LOGS', FileAccess._getMD5(time.strftime('%Y%m%d')), default={})
        
        
    def setLogs(self, key: str, event: str):
        time = datetime.datetime.fromtimestamp(time.time())
        logs = self.getLogs(time)
        logs.setdefault(key,[]).append(f'{time.strftime(DTFORMAT)} - {event}')
        self.setCacheSetting('LOGS', logs, FileAccess._getMD5(time.strftime('%Y%m%d')), datetime.timedelta(days=2))
            
            
    def showDialog(self, silent: Optional[bool] = None) -> bool:
        #True Show/False Silent
        if self.getSettingBool('Debug_Enable'): return True
        if silent: return False
        if not self.dialog.builtin.isPlaying(): return True
        return self.getSettingBool('Notify_While_Playing')
            
            
class Properties(object):
    dialog = None


    def __init__(self, service: Optional[_Service] = None, winID: int = 10131):
        if service is None: service = _Service()
        self.pool       = service.pool
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.cache
        self.monitor    = service.monitor
        self.winID      = winID
        self.window     = xbmcgui.Window(winID)
        self._memory_cache = OrderedDict()

        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s'%(self.__class__.__name__,msg),level)


    def getProcessID(self) -> str:
        processID = self.getEXTProperty('%s.ProcessID'%(ADDON_ID))
        if not processID: processID = self.setProcessID()
        return processID


    def setProcessID(self) -> str:
        self._clrTrash(self.getEXTProperty('%s.ProcessID'%(ADDON_ID),None))
        return self.setEXTProperty('%s.ProcessID'%(ADDON_ID),FileAccess._getMD5(uuid4()))
        


    def _clrTrash(self, processID: Optional[str] = None):
        """Clear abandoned properties after processID change."""
        if processID:
            tmpDCT = self._getTrash()
            if processID in tmpDCT:
                self.log('_clrTrash, processID = %s'%(processID))
                tmpLST = tmpDCT.pop(processID)
                for prop in tmpLST:
                    self.clrProperty(prop)


    def _getTrash(self) -> dict:
        try:    return (FileAccess._decodeString(self.getEXTProperty('%s.TRASH'%(ADDON_ID),{})) or {})
        except Exception as e: 
            LOG('Properties: _getTrash, failed!\n%s' % e, xbmc.LOGDEBUG)
            return {}


    def _setTrash(self, key: str, processID: str):
        """Catalog instance properties that are abandoned."""
        tmpDCT = self._getTrash()
        if key not in tmpDCT.setdefault(processID,[]):
            tmpDCT.setdefault(processID,[]).append(key)
            self.setEXTProperty('%s.TRASH'%(ADDON_ID),str(FileAccess._encodeString(tmpDCT)))

        
    def _getKey(self, key: str, useInstance: bool = True) -> tuple:
        if not key.startswith(ADDON_ID): key = '%s.%s'%(ADDON_ID,key)
        if useInstance: 
            thid = threading.get_ident()
            pid  = self.getProcessID()
            key  = '%s.%s.%s'%(key,pid,thid)
            self._setTrash(key, pid)
            return key, thid
        return key, '-1'


    #GET


    def getProperty(self, key: str, default: str = '') -> str:
        thid = None
        try:
            key, thid = self._getKey(key)
            if key in self._memory_cache: 
                self._memory_cache.move_to_end(key)
                return self._memory_cache[key]
            value = self.window.getProperty(key)
            if not value: return default
            try: value = FileAccess._decodeString(value)
            except (ValueError, SyntaxError): pass
            self.log(f'[{self.winID}] getProperty [{thid}], key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
            self._memory_cache[key] = value
            return value
        except Exception as e: 
            self.log(f"[{self.winID}] getProperty [{thid}], failed! {e} - key = [{key}]", xbmc.LOGERROR)
            return default
            
        
    def getEXTProperty(self, key: str, default: Any = '') -> Any:
        try:
            if key in self._memory_cache: 
                self._memory_cache.move_to_end(key)
                return self._memory_cache[key]
            value = xbmcgui.Window(10000).getProperty(key)
            if not value: return default
            if isinstance(value, str):
                if not value.startswith(('[', '{', '(', 'True', 'False', 'None')) and not value.isdigit():
                    if not '.TRASH' in key: self.log(f'[10000] getEXTProperty, key = {key}, value = {str(value)[:128]}, type = str')
                    self._memory_cache[key] = value
                    return value
            try: value = literal_eval(value)
            except (ValueError, SyntaxError): pass
            if not '.TRASH' in key: self.log(f'[10000] getEXTProperty, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
            self._memory_cache[key] = value
            return value
        except Exception as e: 
            self.log("[%s] getEXTProperty, failed! %s - key = %s, value = %s"%('10000', e, key, str(locals().get('value', default))[:128]), xbmc.LOGERROR)
            return default
        
        
    #CLEAR


    def clrProperties(self):
        self.log('clrProperties')
        self._memory_cache = OrderedDict()
        return self.window.clearProperties()
        
        
    def clrProperty(self, key: str):
        key, thid = self._getKey(key)
        self.log(f'[{self.winID}] clrProperty [{thid}], key = {key}')
        self._memory_cache.pop(key, None)
        return self.window.clearProperty(key)


    def clrEXTProperty(self, key: str):
        self.log('[%s] clrEXTProperty, key = %s'%('10000', key))
        self._memory_cache.pop(key, None)
        return xbmcgui.Window(10000).clearProperty(key)
        
        
    #SET


    def setProperty(self, key: str, value: Any) -> Any:
        key, thid = self._getKey(key)
        if value is None or value == '':
            self.clrProperty(key)
            return value
        try:
            encoded_str = str(FileAccess._encodeString(value))
            self.window.setProperty(key,encoded_str)
            self._memory_cache[key] = FileAccess._decodeString(encoded_str)
            self._memory_cache.move_to_end(key)
            if len(self._memory_cache) > MAX_CACHE_SIZE: oldest_key, _ = self._memory_cache.popitem(last=False)
            self.log(f'[{self.winID}] setProperty [{thid}], key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        except Exception as e: self.log(f"[{self.winID}] setProperty [{thid}], failed! {e} - key = {key}, value = {str(value)[:128]}", xbmc.LOGERROR)
        return value
        
        
    def setEXTProperty(self, key: str, value: Any) -> Any:
        if value is None or value == '': return value
        self._memory_cache[key] = copy.deepcopy(value)
        self._memory_cache.move_to_end(key)
        if len(self._memory_cache) > MAX_CACHE_SIZE: oldest_key, _ = self._memory_cache.popitem(last=False)
        xbmcgui.Window(10000).setProperty(key,str(value))
        if not '.TRASH' in key: self.log(f'[10000] setEXTProperty, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return value


    def setTrakt(self, state: bool = False):
        self.log('setTrakt, disable trakt = %s'%(state))
        # https://github.com/trakt/script.trakt/blob/d45f1363c49c3e1e83dabacb70729cc3dec6a815/resources/lib/kodiUtilities.py#L104
        if state: self.setEXTProperty('script.trakt.paused',state)
        else:     self.clrEXTProperty('script.trakt.paused')


    @debounceit(OSD_TIMER)
    def setPropTimer(self, key: str, state: bool = True, args: tuple = (), kwargs: dict = None) -> Any:
        if not key.startswith(ADDON_ID): key = '%s.%s'%(ADDON_ID, key)
        value = FileAccess.dumpJSON({'s': state, 'a': list(args), 'k': kwargs or {}})
        return self.setEXTProperty(key, value)


    def getPropTimer(self, key: str, state: bool = True, default: bool = False) -> tuple:
        if not key.startswith(ADDON_ID): key = '%s.%s'%(ADDON_ID, key)
        raw = self.getEXTProperty(key, default)
        if isinstance(raw, bool): return raw, [], {}
        try:
            data = FileAccess.loadJSON(raw)
            return data.get('s', default), data.get('a', []), data.get('k', {})
        except Exception:
            return raw, [], {}


    def setRemoteHost(self, value: str) -> str:
        return self.setEXTProperty('%s.Remote_Host'%(ADDON_ID),value)
        
        
    def getRemoteHost(self) -> str:
        remote = self.getEXTProperty('%s.Remote_Host'%(ADDON_ID))
        if not remote: remote = self.setRemoteHost('%s:%s'%(self.dialog.settings.getIP(),self.dialog.settings.getSettingInt('TCP_PORT')))
        return remote


    def setHasChannels(self, key: Optional[str] = None, channelDATA: Optional[dict] = None) -> Any:
        if key is None: key = CHANNELAUTOTUNE_KEY if self.dialog.settings.getSettingBool('Enable_Autotune') else CHANNEL_KEY
        if channelDATA is None: channelDATA = Channels(key).channelDATA
        chanLST = self.dialog.settings.getCacheSetting('%s.has.Channels'%(ADDON_ID), default={})
        if len(channelDATA.get('channels',[])) > 0: 
            channelDATA.update({'updated': datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)})
            chanLST.setdefault(key,{}).update(channelDATA)
        elif key in chanLST: chanLST.pop(key)
        return self.dialog.settings.setCacheSetting('%s.has.Channels'%(ADDON_ID),chanLST,life=-1).get(key)
        
        
    def hasChannels(self, key: Optional[str] = None, path: Optional[str] = None) -> bool:
        if key is None: key = CHANNELAUTOTUNE_KEY if self.dialog.settings.getSettingBool('Enable_Autotune') else CHANNEL_KEY
        if not path is None: 
            if FileAccess.exists(path): channelDATA = FileAccess.getJSON(path)
        else:                           channelDATA = self.dialog.settings.getCacheSetting('%s.has.Channels'%(ADDON_ID), default={}).get(key,{})
        return len(channelDATA.get('channels',[])) > 0
        


    def setBackup(self, key: str = CHANNELBACKUP_KEY, channels: Optional[list] = None) -> Any:
        backups = self.dialog.settings.getCacheSetting('%s.has.backups'%(ADDON_ID), default={})
        if channels is None: channels = Channels(key).getChannels()
        if len(channels) > 0: backups.setdefault(key,{}).update({'name':key, 'channels': channels, 'updated':(backups.get(key,{}).get('updated') or datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT))})
        elif key in backups:  backups.pop(key)
        return self.dialog.settings.setCacheSetting('%s.has.backups'%(ADDON_ID),backups,life=-1).get(key)


    def hasBackup(self, key: str = CHANNELBACKUP_KEY, path: Optional[str] = None) -> Optional[dict]:
        if not path is None: 
            if FileAccess.exists(path): return FileAccess.getJSON(path)
        else:                           return self.dialog.settings.getCacheSetting('%s.has.backups'%(ADDON_ID), default={}).get(key)


    def hasBackups(self) -> bool:
        return len(list(self.dialog.settings.getCacheSetting('%s.has.backups'%(ADDON_ID), default={}).keys())) > 0


    def hasLibrary(self, type: Optional[str] = None) -> bool:
        if not type is None: return self.getEXTProperty('%s.has.%s'%(ADDON_ID,type),False)
        return any(self.getEXTProperty('%s.has.%s'%(ADDON_ID,t),False) for t in AUTOTUNE_TYPES)
        
        
    def setHasLibrary(self, type: str, state: bool = True) -> Any:
        return self.setEXTProperty('%s.has.%s'%(ADDON_ID,type),state)
        
        
    def setHasServers(self, state: bool = True) -> Any:
        return self.setEXTProperty('%s.has.Servers'%(ADDON_ID),state)
        


    def hasServers(self) -> bool:
        return self.getEXTProperty('%s.has.Servers'%(ADDON_ID),False)
        
                
    def setEnabledServers(self, state: bool = True) -> Any:
        return self.setEXTProperty('%s.has.Enabled_Servers'%(ADDON_ID),state)
        
        
    def hasEnabledServers(self) -> bool:
        return self.getEXTProperty('%s.has.Enabled_Servers'%(ADDON_ID),False)
        
        
    def setPendingShutdown(self, state: bool = True) -> Any:
        return self.setEXTProperty('%s.SERVICE.pendingShutdown'%(ADDON_ID),state)
        


    def isPendingShutdown(self) -> bool:
        value = self.getEXTProperty('%s.SERVICE.pendingShutdown'%(ADDON_ID),False)
        self.clrEXTProperty(f'{ADDON_ID}.SERVICE.pendingShutdown')
        return value
        
                
    def setPendingRestart(self, state: bool = True) -> Any:
        return self.setEXTProperty('%s.SERVICE.pendingRestart'%(ADDON_ID),state)


    def isPendingRestart(self) -> bool:
        value = self.getEXTProperty('%s.SERVICE.pendingRestart'%(ADDON_ID),False)
        self.clrEXTProperty(f'{ADDON_ID}.SERVICE.pendingRestart')
        return value


    @contextmanager
    def chkRunning(self, key: str) -> Iterator[bool]:
        try:
            if not self.isRunning(key):
                self.setRunning(key,True)
                yield False
            else:
                yield True
        finally:
            self.setRunning(key,False)
            
            
    def setRunning(self, key: str, state: bool = True) -> Any:
        return self.setEXTProperty('%s.%s.Running'%(ADDON_ID,key),state)
        
        
    def isRunning(self, key: str) -> bool:
        return self.getEXTProperty('%s.%s.Running'%(ADDON_ID,key),False)


    @contextmanager
    def lockActivity(self, state: bool = True) -> Iterator[bool]:
        try:
            if not self.isLockActivity():
                self.setLockActivity(True)
                yield True
            else:
                yield False
        finally:
            self.setLockActivity(False)
            


    def setLockActivity(self, state: bool = True) -> Any:
        """Context state for locking activity."""
        return self.setEXTProperty('%s.lockActivity'%(ADDON_ID),state)


    def isLockActivity(self) -> bool:
        """Context state for locking activity."""
        return self.getEXTProperty('%s.lockActivity'%(ADDON_ID),False)


    @contextmanager
    def interruptActivity(self, wait: int = -1) -> Iterator:
        """Quit background task, wait -1 runs indefinitely."""
        while not self.monitor.abortRequested() and (self.isInterruptActivity() or self.isLockActivity()) and wait > 0:
            if wait > 0: wait -= CPU_CYCLE
            if self.monitor.waitForAbort(CPU_CYCLE) or int(wait) == 0: break
        self.setPendingInterrupt(self.setInterruptActivity(True))
        try: yield
        finally: 
            self.setPendingInterrupt(self.setInterruptActivity(False))
        
           
    def setInterruptActivity(self, state: bool = True) -> Any:
        """Context state for interrupting activity."""
        return self.setProperty('%s.interruptActivity'%(ADDON_ID),state)
        


    def isInterruptActivity(self) -> bool:
        """Context state for interrupting activity."""
        return self.getProperty('%s.interruptActivity'%(ADDON_ID),False)


    def setPendingInterrupt(self, state: bool = True) -> Any:
        """Interrupt state."""
        return self.setEXTProperty('%s.pendingInterrupt'%(ADDON_ID),state)


    def isPendingInterrupt(self) -> bool:
        """Interrupt state."""
        return self.getEXTProperty('%s.pendingInterrupt'%(ADDON_ID),False)

        
    @contextmanager
    def suspendActivity(self, wait: int = 30) -> Iterator:
        """Pause background task, wait seconds before yielding anyway."""
        deadline = time.time() + max(wait, 0)
        while not self.monitor.abortRequested() and (self.isSuspendActivity() or self.isLockActivity()):
            if self.monitor.waitForAbort(CPU_CYCLE) or time.time() >= deadline: break
        self.setPendingSuspend(self.setSuspendActivity(True))
        try: yield
        finally: self.setPendingSuspend(self.setSuspendActivity(False))


    def setSuspendActivity(self, state: bool = True) -> Any:
        """Context state for suspend activity."""
        return self.setProperty('%s.suspendActivity'%(ADDON_ID),state)


    def isSuspendActivity(self) -> bool:
        """Context state for suspend activity."""
        return self.getProperty('%s.suspendActivity'%(ADDON_ID),False)
        
        
    def setPendingSuspend(self, state: bool = True) -> Any:
        """Suspend state."""
        return self.setEXTProperty('%s.pendingSuspend'%(ADDON_ID),state)
        
        
    def isPendingSuspend(self) -> bool:
        """Suspend state."""
        return self.getEXTProperty('%s.pendingSuspend'%(ADDON_ID),False)


    @contextmanager
    def legacy(self) -> Iterator[bool]:
        """Toggle legacy property from older pseudotv project that may still be used by third-party plugins."""
        try: 
            if not self.isPseudoTVRunning():
                self.setEXTProperty('PseudoTVRunning',True)
                yield True
            else:
                yield False
        finally: 
            self.setEXTProperty('PseudoTVRunning',False)


    def isPseudoTVRunning(self) -> bool:
        return self.getEXTProperty('PseudoTVRunning',False)


    def getFriendlyName(self) -> str:
        friendly = self.getEXTProperty('%s.Instance_Name'%(ADDON_ID))
        if not friendly or friendly == LANGUAGE(32105):
            friendly = self.setEXTProperty('%s.Instance_Name'%(ADDON_ID), self.jsonRPC.inputFriendlyName())
        return friendly
        
        
    def preemptActivity(self, msg: str, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute a function while preempting suspend/interrupt activity states."""
        results      = None
        orgSuspend   = self.isPendingSuspend()
        orgInterrupt = self.isPendingInterrupt()
        while not self.monitor.abortRequested():
            isSuspend   = self.isPendingSuspend()
            isInterrupt = self.isPendingInterrupt()
            isBuilding  = self.isRunning('Builder.buildChannels')
            
            Dialog().notificationDialog(msg)
            self.log('preemptActivity, isInterrupt = %s, isSuspend = %s, isBuilding = %s'%(isInterrupt,isSuspend,isBuilding))
            if not isInterrupt and any((isSuspend, isBuilding)): #force interrupt.
                if isSuspend:  self.setPendingSuspend(False)   #release suspension 
                if isBuilding: self.setPendingInterrupt(True)  #interrupt building.
            elif isInterrupt and not isBuilding: self.setPendingInterrupt(False)#release interrupt.
            elif not isInterrupt and not any((isSuspend, isBuilding)):
                with self.lockActivity():
                    try: results = func(*args, **kwargs)
                    except Exception as e: self.log("preemptActivity, failed! %s"%(e), xbmc.LOGERROR)
                    break
            if self.monitor.waitForAbort(CPU_CYCLE): break
        
        self.setPendingSuspend(orgSuspend)
        self.setPendingInterrupt(orgInterrupt)
        return results


class ListItems(object):
    dialog = None
    
    # =========================================================================
    # Listitem InfoTag Type Definitions
    # Maps ListItem property names to their expected Python types.
    # Used by cleanInfo() to validate and coerce metadata before set_info().
    # =========================================================================
    class ListitemTypes:
        """Kodi ListItem InfoTag type validation maps."""
        
        MUSIC = {'tracknumber'             : (int,),  #integer (8)
                 'discnumber'              : (int,),  #integer (2)
                 'duration'                : (int,),  #integer (245) - duration in seconds
                 'year'                    : (int,),  #integer (1998)
                 'genre'                   : (tuple,list),  
                 'album'                   : (str,),  
                 'artist'                  : (str,),  
                 'title'                   : (str,),  
                 'rating'                  : (float,),#float - range is between 0 and 10
                 'userrating'              : (int,),  #integer - range is 1..10
                 'lyrics'                  : (str,),
                 'playcount'               : (int,),  #integer (2) - number of times this item has been played
                 'lastplayed'              : (str,),  #string (Y-m-d h:m:s = 2009-04-05 23:16:04)
                 'mediatype'               : (str,),  #string - "music", "song", "album", "artist"
                 'dbid'                    : (int,),  #integer (23) - Only add this for items which are part of the local db. You also need to set the correct 'mediatype'!
                 'listeners'               : (int,),  #integer (25614)
                 'musicbrainztrackid'      : (str,list),
                 'musicbrainzartistid'     : (str,list),
                 'musicbrainzalbumid'      : (str,list),
                 'musicbrainzalbumartistid': (str,list),
                 'comment'                 : (str,),  
                 'count'                   : (int,),  #integer (12) - can be used to store an id for later, or for sorting purposes
                 # 'size'                    : (int,), #long (1024) - size in bytes
                 'date'                    : (str,),} #string (d.m.Y / 01.01.2009) - file date

        VIDEO = {'genre'                   : (tuple,list),
                 'country'                 : (str,list),
                 'year'                    : (int,),  #integer (2009)
                 'episode'                 : (int,),  #integer (4)
                 'season'                  : (int,),  #integer (1)
                 'sortepisode'             : (int,),  #integer (4)
                 'sortseason'              : (int,),  #integer (1)
                 'episodeguide'            : (str,),
                 'showlink'                : (str,list),
                 'top250'                  : (int,),  #integer (192)
                 'setid'                   : (int,),  #integer (14)
                 'tracknumber'             : (int,),  #integer (3)
                 'rating'                  : (float,),#float (6.4) - range is 0..10
                 'userrating'              : (int,),  #integer (9) - range is 1..10 (0 to reset)
                 'playcount'               : (int,),  #integer (2) - number of times this item has been played
                 'overlay'                 : (int,),  #integer (2) - range is 0..7. See Overlay icon types for values
                 'cast'                    : (list,),
                 'castandrole'             : (list,tuple),
                 'director'                : (str,list),
                 'mpaa'                    : (str,),
                 'plot'                    : (str,),
                 'plotoutline'             : (str,),
                 'title'                   : (str,),
                 'originaltitle'           : (str,),
                 'sorttitle'               : (str,),
                 'duration'                : (int,),  #integer (245) - duration in seconds
                 'studio'                  : (str,list),
                 'tagline'                 : (str,),
                 'writer'                  : (str,list),
                 'tvshowtitle'             : (str,list),
                 'premiered'               : (str,),  #string (2005-03-04)
                 'status'                  : (str,),
                 'set'                     : (str,),
                 'setoverview'             : (str,),
                 'tag'                     : (str,list),
                 'imdbnumber'              : (str,),  #string (tt0110293) - IMDb code
                 'code'                    : (str,),  #string (101) - Production code
                 'aired'                   : (str,),  #string (2008-12-07) 
                 'credits'                 : (str,list),
                 'lastplayed'              : (str,),  #string (Y-m-d h:m:s = 2009-04-05 23:16:04)
                 'album'                   : (str,),
                 'artist'                  : (list,),
                 'votes'                   : (str,),
                 'path'                    : (str,),
                 'trailer'                 : (str,),
                 'dateadded'               : (str,),  #string (Y-m-d h:m:s = 2009-04-05 23:16:04)
                 'mediatype'               : (str,),  #mediatype	string - "video", "movie", "tvshow", "season", "episode" or "musicvideo"
                 'dbid'                    : (int,),  #integer (23) - Only add this for items which are part of the local db. You also need to set the correct 'mediatype'!
                 'count'                   : (int,),  #integer (12) - can be used to store an id for later, or for sorting purposes
                 # 'size'                    : (int,),  #long (1024) - size in bytes
                 'date'                    : (str,),} #string (d.m.Y / 01.01.2009) - file date
    
    def __init__(self, service: Optional[_Service] = None):
        if service is None: service = _Service()
        self.pool       = service.pool
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.cache
        self.monitor    = service.monitor


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def getListItem(self, label: str = '', label2: str = '', path: str = '', offscreen: bool = False) -> xbmcgui.ListItem:
        return xbmcgui.ListItem(label,label2,path,offscreen)


    def infoTagVideo(self, offscreen: bool = False) -> xbmc.InfoTagVideo:
        return xbmc.InfoTagVideo(offscreen)


    def InfoTagMusic(self, offscreen: bool = False) -> xbmc.InfoTagMusic:
        return xbmc.InfoTagMusic(offscreen)


    def buildDictListItem(self, listitem: xbmcgui.ListItem) -> dict:
        item = {'label'       : listitem.getLabel(),
                'label2'      : listitem.getLabel2(),
                'file'        : listitem.getPath(),
                'isFolder'    : listitem.isFolder(),
                'isSelected'  : listitem.isSelected(),
                'dateadded'   : listitem.getDateTime(),
                'videoInfoTag': listitem.getVideoInfoTag(),#todo expand
                'musicInfoTag': listitem.getMusicInfoTag(),#todo expand
                'uniqueid '   : {},
                'art'         : {},
                'rating'      : {},
                'votes'       : {},
                'properties'  : {}}
                      
        for key in ['imdb','tvdb','tmdb','anidb']:
            uid = listitem.getUniqueID(key)
            if uid: item['uniqueID'][key] = uid
            rat = listitem.getRating(key)
            if rat: item['rating'][key] = rat
            vot = listitem.getVotes(key)
            if vot: item['votes'][key] = vot
            
        for key in  ['thumb', 'poster', 'banner', 'fanart', 'clearart', 'clearlogo', 'landscape', 'icon']:
            val = listitem.getArt(key)
            if val: item['art'][key] = val
                
        for key in self.getEnums("List.Fields.Files", type='items') + ['citem','catchup-id','stop','start','idx','friendly','plot','customproperties','runtime','originalpath','remote']:
            val = listitem.getProperty(key)
            if val: item[key] = val
            
        for prop in ['StartOffset', 'IsPlayable', 'AspectRatio']:
            val = listitem.getProperty(prop)
            if val: item['properties'][prop] = val
                
        # item['fitem'] = _globals()._decodePlot(item.get('Plot'))
        return item


    def buildItemListItem(self, item: dict, media: str = 'video', offscreen: bool = False, playable: bool = True) -> Optional[xbmcgui.ListItem]:
        try:
            info       = item.copy()
            art        = (info.pop('art'              ,{}) or {})
            cast       = (info.pop('cast'             ,[]) or [])
            uniqueid   = (info.pop('uniqueid'         ,{}) or {})
            streamInfo = (info.pop('streamdetails'    ,{}) or {})
            properties = (info.pop('customproperties' ,{}) or {})
            if 'citem'   in info: properties.update({'citem'  :info.pop('citem')})   # write dump to single key
            if 'pvritem' in info: properties.update({'pvritem':info.pop('pvritem')}) # write dump to single key
          
            if media != 'video': #unify default artwork for music.
                art['poster'] = _globals()._getThumb(info,opt=1)
                art['fanart'] = _globals()._getThumb(info)
                
            listitem = self.getListItem(info.pop('label',''), info.pop('label2',''), info.pop('file',''), offscreen=offscreen)
            listitem.setArt(art)
            
            infoTag = ListItemInfoTag(listitem, media)
            info, properties = self.cleanInfo(info,media,properties)
            infoTag.set_info(info)
            if not media.lower() == 'music': 
                infoTag.set_cast(cast)
                infoTag.set_unique_ids(uniqueid)
                
            for ainfo in streamInfo.get('audio',[]):    infoTag.add_stream_info('audio'   , ainfo)
            for vinfo in streamInfo.get('video',[]):    infoTag.add_stream_info('video'   , vinfo)
            for sinfo in streamInfo.get('subtitle',[]): infoTag.add_stream_info('subtitle', sinfo)
            
            for key, pvalue in list(properties.items()): listitem.setProperty(key, self.cleanProp(pvalue))
            if playable: listitem.setProperty("IsPlayable","true")
            else:        listitem.setIsFolder(True)
            return listitem
        except Exception as e: LOG("ListItems: buildItemListItem, failed!\n%s\n%s"%(e,item), xbmc.LOGERROR)
            
                     
    def buildMenuListItem(self, label: str = "", label2: str = "", icon: str = ICON, url: str = "", info: dict = {}, art: dict = {}, props: dict = {}, offscreen: bool = False, media: str = 'video') -> xbmcgui.ListItem:
        if not art: art = {'thumb':icon,'logo':icon,'icon':icon}
        listitem = self.getListItem(label, label2, url, offscreen=offscreen)
        listitem.setIsFolder(True)
        listitem.setPath(url)
        listitem.setArt(art)
        if info:
            infoTag = ListItemInfoTag(listitem, media)
            info, _ = self.cleanInfo(info,media)
            infoTag.set_info(info)
        [listitem.setProperty(key, self.cleanProp(pvalue)) for key, pvalue in list(props.items())]
        return listitem
               
           
    def cleanInfo(self, ninfo: dict, media: str = 'video', properties: Optional[dict] = None) -> tuple:
        """Validate and coerce info dict values to match Kodi InfoTag type schema.
        
        Unknown keys are moved to properties (custom listitem properties).
        Known keys with wrong types are converted when possible.
        None values are stripped (Kodi set_info ignores them).
        Nested dicts/lists of dicts are recursed.
        
        Args:
            ninfo:   dict of info metadata (modified in-place and returned)
            media:   'video' or 'music' — selects the ListitemTypes schema
            properties: dict to collect custom properties (created on first call)
        
        Returns:
            (ninfo, properties) tuple
        """
        if properties is None: properties = {}
        schema = ListItems.ListitemTypes.MUSIC if media == 'music' else ListItems.ListitemTypes.VIDEO
        keys_to_pop = []
        for key, value in list(ninfo.items()):
            types = schema.get(key)
            if types is None: # unknown key — move to custom properties
                keys_to_pop.append(key)
                properties[key] = value
                continue
            if value is None: # Kodi set_info ignores None; strip it
                keys_to_pop.append(key)
                continue
            if isinstance(value, types): # already correct type
                pass
            else: # attempt type coercion — try each type in schema order
                converted = False
                for typ in types:
                    try:
                        ninfo[key] = typ(value)
                        converted = True
                        break
                    except (ValueError, TypeError):
                        continue
                if not converted: # could not coerce — strip bad value
                    self.log("cleanInfo, type coercion failed: key=%s, value=%s, types=%s"%(key, repr(value), types), xbmc.LOGDEBUG)
                    keys_to_pop.append(key)
                    continue
            # recurse into nested structures
            if isinstance(ninfo[key], dict):
                ninfo[key], properties = self.cleanInfo(ninfo[key], media, properties)
            elif isinstance(ninfo[key], list):
                for idx, item in enumerate(ninfo[key]):
                    if isinstance(item, dict):
                        ninfo[key][idx], properties = self.cleanInfo(item, media, properties)
        for key in keys_to_pop: ninfo.pop(key, None)
        return ninfo, properties


    def cleanProp(self, pvalue: Any) -> str:
        if       isinstance(pvalue,dict): return FileAccess.dumpJSON(pvalue)
        elif     isinstance(pvalue,list): return '|'.join(map(str, pvalue))
        elif not isinstance(pvalue,str):  return str(pvalue)
        else:                             return pvalue
            
    
class Builtin(object):
    dialog = None


    def __init__(self, service: Optional[_Service] = None):
        if service is None: service = _Service()
        self.lock       = Lock()
        self.busy       = None
        self.pool       = service.pool
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.cache
        self.monitor    = service.monitor
        
    
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s'%(self.__class__.__name__,msg),level)
                  


    def hasPVR(self) -> bool:
        return self.getInfoBool('Pvr.HasTVChannels')
        
        
    def hasRadio(self) -> bool:
        return self.getInfoBool('Pvr.HasRadioChannels')


    def hasMusic(self) -> bool:
        return self.getInfoBool('Library.HasContent(Music)')
        
        
    def hasTV(self) -> bool:
        return self.getInfoBool('Library.HasContent(TVShows)')
        
        
    def hasMovie(self) -> bool:
        return self.getInfoBool('Library.HasContent(Movies)')
                


    def hasMedia(self) -> bool:
        return self.getInfoBool('Player.hasMedia')


    def hasGame(self) -> bool:
        return self.getInfoBool('Player.HasGame')


    def hasDuration(self) -> bool:
        return self.getInfoBool('Player.HasDuration')


    def hasEPG(self) -> bool:
        return self.getInfoBool('VideoPlayer.HasEpg','')

  
    def hasSubtitle(self) -> bool:
        return self.getInfoBool('VideoPlayer.HasSubtitles')


    def isSubtitle(self) -> bool:
        return self.getInfoBool('VideoPlayer.SubtitlesEnabled')


    def isPlaylistRandom(self) -> bool:
        return self.getInfoLabel('Playlist.Random').lower() == 'on' # Disable auto playlist shuffling if it's on
        
        
    def isPlaylistRepeat(self) -> bool:
        return self.getInfoLabel('Playlist.IsRepeat').lower() == 'true' # Disable auto playlist repeat if it's on #todo


    def isPaused(self) -> bool:
        return self.getInfoBool('Player.Paused')
                
                
    def isRecording(self) -> bool:
        return self.getInfoBool('Pvr.IsRecording')
        
        
    def isScanning(self) -> bool:
        return (self.getInfoBool('Library.IsScanningVideo') & self.getInfoBool('Library.IsScanningMusic'))
          
                      
    def isSettingsOpened(self) -> bool:
        return any((self.getInfoBool('Window.IsVisible(addonsettings)'),self.getInfoBool('Window.IsVisible(selectdialog)')))


    def isPlaying(self) -> bool:
        return self.getInfoBool('Player.Playing')


    def isPVRPlaying(self) -> bool:
        return any((self.getInfoBool('Pvr.IsPlayingTv'),self.getInfoBool('Pvr.IsPlayingRadio'),self.getInfoBool('Pvr.IsPlayingRecording'),self.getInfoBool('Pvr.IsPlayingActiveRecording')))


    def isBusyDialog(self) -> bool:
        return any((self.dialog.properties.isRunning('BUSY_OVERLAY'),self.getInfoBool('Window.IsActive(busydialognocancel)'),self.getInfoBool('Window.IsActive(busydialog)')))

        
    def _isScanning(self) -> bool:
        return (self.getInfoBool('Library.IsScanningVideo') &  self.getInfoBool('Library.IsScanningMusic'))


    def _isSettingsOpened(self) -> bool:
        return any((self.getInfoBool('Window.IsVisible(addonsettings)'), self.getInfoBool('Window.IsVisible(selectdialog)')))


    def closeBusyDialog(self):
        if hasattr(self.busy, 'close'):
            self.busy = self.busy.close()
        elif self.getInfoBool('Window.IsActive(busydialognocancel)'):
            self.executebuiltin('Dialog.Close(busydialognocancel)')
        elif self.getInfoBool('Window.IsActive(busydialog)'):
            self.executebuiltin('Dialog.Close(busydialog)')


    @contextmanager
    def busyDialog(self, cancel: bool = False, lock: bool = False) -> Iterator:
        if not self.isBusyDialog() and not cancel:
            try: 
                if self.busy is None:
                    from overlay import Busy
                    try:               self.busy = Busy(BUSY_XML, ADDON_PATH, "default", isLocked=lock)
                    except Exception:  self.busy = None
                    finally:
                        if hasattr(self.busy, 'show'): 
                            self.busy.show()
                elif cancel and hasattr(self.busy, 'close'):
                    self.busy = self.busy.close()
                yield
            finally:
                if hasattr(self.busy, 'close'):
                    self.busy = self.busy.close()
        else: yield

    busy_dialog = busyDialog


    def getIdle(self) -> int:
        with self.lock:
            try:              return int(xbmc.getGlobalIdleTime() or '0')
            except Exception: return 0
            


    def getInfoLabel(self, key: str, default: str = '', retries: int = 5) -> str:
        with self.lock:
            value   = None
            pattern = r"^[a-zA-Z0-9]+\.[a-zA-Z0-9]+(?:\(.*\))?$"
            if re.match(pattern, key):
                for attempt in range(retries):
                    value = xbmc.getInfoLabel(key)
                    if value != "Busy": break
                    self.log('getInfoLabel, key = %s, busy (attempt %d/%d)'%(key,attempt+1,retries))
                    if self.monitor.waitForAbort(0.5): break
                self.log('getInfoLabel, key = %s, value = %s'%(key,value))
            else: self.log('getInfoLabel failed!, key = %s'%(key))
            return (value or default)


    def getInfoBool(self, key: str) -> bool:
        with self.lock:
            value   = False
            pattern = r"^[a-zA-Z0-9]+\.[a-zA-Z0-9]+(?:\(.*\))?$"
            if re.match(pattern, key):
                value = xbmc.getCondVisibility(key)
                self.log('getInfoBool, key = %s, value = %s'%(key,value))
            else: self.log('getInfoBool failed!, key = %s'%(key))
            return value or False
        
        
    def executewindow(self, key: str, wait: bool = False, delay: bool = False, condition: Optional[Callable] = None) -> Any:
        with self.lock:
            return self.executebuiltin(key,wait,delay,condition)
        
        
    def executebuiltin(self, key: str, wait: bool = False, delay: Optional[float] = None, condition: Optional[Callable] = None) -> Any:
        if not condition is None and not condition(): return False
        with self.lock:
            self.log('executebuiltin, key = %s, wait = %s, delay = %s, condition = %s):'%(key,wait,delay,condition))
            if delay is None: return xbmc.executebuiltin('%s'%(key),wait)
            return timerit(xbmc.executebuiltin)(delay,*(key,wait,None,condition))
        
        
    def executescript(self, path: str, condition: Optional[Callable] = None) -> bool:
        if not condition is None and not condition(): return False
        with self.lock:
            self.log('executescript, path = %s'%(path))
            xbmc.executescript('%s'%(path))
            return True


    def executeJSONRPC(self, request: dict) -> str:
        with self.lock:
            response = xbmc.executeJSONRPC(FileAccess.dumpJSON(request))
            self.log('executeJSONRPC\nrequest = %s'%(request))
            self.monitor.waitForAbort(float(_globals().settings.getSetting('API_Delay')))
            return response
    


    def getResolution(self) -> tuple:
        WH, WIN = self.getInfoLabel('System.ScreenResolution').split(' - ')
        return (1920,1080), WIN #tuple(int(x) for x in WH.split('x')), WIN


    def parseKodiLog(self, lines: int = 500) -> dict:
        """Parse Kodi log file for project logs and relevant system data."""
        log_path = FileAccess.translatePath('special://logpath/kodi.log')
        result = {'project': [], 'errors': [], 'system': {}, 'summary': {}}
        
        if not FileAccess.exists(log_path):
            self.log('parseKodiLog, log file not found: %s' % log_path, xbmc.LOGWARNING)
            return result
        try:
            fle = FileAccess.open(log_path, 'r')
            all_lines = fle.readlines()[-lines:]  # Read last N lines
            fle.close()
        except Exception as e:
            self.log('parseKodiLog, failed to read log: %s' % e, xbmc.LOGERROR)
            return result

        project_prefix = f'{ADDON_ID}-'
        error_count = 0
        warning_count = 0
        project_count = 0
        
        for line in all_lines:
            line = line.strip()
            if not line: continue
            if 'error' in line.lower():     error_count += 1
            elif 'warning' in line.lower(): warning_count += 1
                
            if project_prefix in line:
                project_count += 1
                try:
                    parts = line.split(project_prefix, 1)
                    if len(parts) == 2: result['project'].append(re.sub(r'\x1b\[[0-9;]*m', '', parts[1]))
                except Exception:
                    result['project'].append(line)
                    
            elif 'error' in line.lower() and ('pseudotv' in line.lower() or 'pvr' in line.lower()):
                try: result['errors'].append(re.sub(r'\x1b\[[0-9;]*m', '', line)[-200:])  # Last 200 chars
                except Exception: pass

        # System info
        result['system'] = {
               'version': ADDON_VERSION,
               'build': self.getInfoLabel('System.BuildVersion'),
               'os': self.getInfoLabel('System.OSVersionInfo'),
               'memory_free': self.getInfoLabel('System.FreeMemory'),
               'cpu_count': os.cpu_count(),
               'python': platform.python_version(),
               'platform': platform.machine(),
               'log_path': log_path,
               'log_lines': len(all_lines)
               }
        
        # Summary
        result['summary'] = {
               'project_logs': project_count,
               'total_errors': error_count,
               'total_warnings': warning_count,
               'last_modified': datetime.datetime.fromtimestamp(os.path.getmtime(log_path)).strftime(DTFORMAT) if FileAccess.exists(log_path) else None
               }
        self.log('parseKodiLog, project=%d, errors=%d, warnings=%d, lines=%d' % (project_count, error_count, warning_count, len(all_lines)))
        return result



class Dialog(object):
    _dialog_count = 0
    _dialog_lock  = Lock()
    _update_lock  = Lock()
    _count_lock   = Lock()
    dialog        = xbmcgui.Dialog()
    
    def __init__(self, service: Optional[_Service] = None):
        if service is None: service = _Service()
        self.service    = service
        self.pool       = service.pool
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.cache
        self.monitor    = service.monitor
        self.settings   = Settings(service)
        self.properties = Properties(service)
        self.listitems  = ListItems(service)
        self.builtin    = Builtin(service)

        self.settings.dialog   = self
        self.properties.dialog = self
        self.listitems.dialog  = self
        self.builtin.dialog    = self


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s'%(self.__class__.__name__,msg),level)


    def toggleInfoMonitor(self, state: bool = False, wait: float = 0.5):
        self.log('toggleInfoMonitor, state = %s'%(state))
        self.properties.setRunning('Kodi.toggleInfoMonitor',state)
        if state: timerit(self.doInfoMonitor)(0.1)
            


    def doInfoMonitor(self):
        self.properties.clrEXTProperty('%s.montiorList'%(ADDON_ID))
        while not self.monitor.abortRequested() and self.properties.isRunning('Kodi.toggleInfoMonitor'):
            if self.monitor.waitForAbort(float(_globals().settings.getSetting('API_Delay'))): break
            self.fillInfoMonitor()
                    


    def fillInfoMonitor(self, type: str = 'ListItem'):
        try:
            item = {'label'       :self.builtin.getInfoLabel('%s.Label'%type),
                    'label2'      :self.builtin.getInfoLabel('%s.Label2'%type),
                    'set'         :self.builtin.getInfoLabel('%s.Set'%type),
                    'path'        :self.builtin.getInfoLabel('%s.Path'%type),
                    'genre'       :self.builtin.getInfoLabel('%s.Genre'%type),
                    'studio'      :self.builtin.getInfoLabel('%s.Studio'%type),
                    'title'       :self.builtin.getInfoLabel('%s.Title'%type),
                    'tvshowtitle' :self.builtin.getInfoLabel('%s.TVShowTitle'%type),
                    'plot'        :self.builtin.getInfoLabel('%s.Plot'%type),
                    'addonname'   :self.builtin.getInfoLabel('%s.AddonName'%type),
                    'artist'      :self.builtin.getInfoLabel('%s.Artist'%type),
                    'album'       :self.builtin.getInfoLabel('%s.Album'%type),
                    'albumartist' :self.builtin.getInfoLabel('%s.AlbumArtist'%type),
                    'foldername'  :self.builtin.getInfoLabel('%s.FolderName'%type),
                    'logo'        :(self.builtin.getInfoLabel('%s.Art(tvshow.clearlogo)'%type) or  self.builtin.getInfoLabel('%s.Art(clearlogo)'%type) or
                                    self.builtin.getInfoLabel('%s.Icon'%type) or self.builtin.getInfoLabel('%s.Thumb'%type))}
            if item.get('label'):
                montiorList = self.getInfoMonitor()
                if item.get('label') not in montiorList: montiorList.insert(0,item)
                self.setInfoMonitor(montiorList)
        except Exception as e: self.log("fillInfoMonitor, failed! %s"%(e), xbmc.LOGERROR)


    def getInfoMonitor(self) -> list:
        return self.properties.getEXTProperty('%s.montiorList'%(ADDON_ID),{}).get('info',[])
    
    
    def setInfoMonitor(self, items: list) -> Any:
        return self.properties.setEXTProperty('%s.montiorList'%(ADDON_ID),{'info':list(_globals()._setDictLST(items))})


    def colorDialog(self, colorlist: list = [], preselect: str = "", colorfile: str = "", heading: str = ADDON_NAME) -> Any:
        return self.dialog.colorpicker(heading, preselect, colorfile, colorlist)
    
    
    def _closeOkDialog(self):
        if self.builtin.getInfoBool('Window.IsActive(okdialog)'):
            self.builtin.executebuiltin('Dialog.Close(okdialog)')
        
        
    def _okDialog(self, msg: str, heading: str, autoclose: int) -> Any:
        return timerit(self.okDialog)(0.1,*(msg, heading, autoclose))


    def okDialog(self, msg: str, heading: str = ADDON_NAME, autoclose: int = AUTOCLOSE_DELAY, usethread: bool = False) -> bool:
        if usethread: return self._okDialog(msg, heading, autoclose)
        else:
            if autoclose > 0: timerit(self._closeOkDialog)(autoclose)
            return self.dialog.ok(heading, msg)
            
            
    def qrDialog(self, url: str, msg: str, heading: str = '%s - %s'%(ADDON_NAME,LANGUAGE(30158)), autoclose: int = AUTOCLOSE_DELAY) -> Optional[bool]:
        class QRCode(xbmcgui.WindowXMLDialog):
            def __init__(self, *args: Any, **kwargs: Any):
                self.header    = kwargs["header"]
                self.image     = kwargs["image"]
                self.text      = kwargs["text"]
                self.acThread  = Timer(kwargs["atclose"], self.onClose)

            def onInit(self):
                self.getControl(40000).setLabel(self.header)
                self.getControl(40001).setImage(self.image)
                self.getControl(40002).setText(self.text)
                self.getControl(40003).setLabel(LANGUAGE(32062))
                self.setFocus(self.getControl(40003))
                self.acThread.name = "acThread"
                self.acThread.daemon=True
                self.acThread.start()

            def onClick(self, controlId: int):
                if controlId == 40003:
                    self.onClose()

            def onClose(self):
                if self.acThread.is_alive():
                    if hasattr(self.acThread, 'cancel'): self.acThread.cancel()
                    try: self.acThread.join()
                    except Exception as e: self.log('onClose thread join failed: %s' % e, xbmc.LOGDEBUG)
                self.close()

        if not self.properties.isRunning('Dialog.qrDialog'):
            with self.properties.chkRunning('Dialog.qrDialog'):
                with self.builtin.busyDialog():
                    imagefile = os.path.join(FileAccess.translatePath(TEMP_LOC),'%s.png'%(FileAccess._getMD5(str(url.split('/')[-1]))))
                    if not FileAccess.exists(imagefile):
                        qrIMG = pyqrcode.create(url)
                        qrIMG.png(imagefile, scale=10)
                        
            qr = QRCode( "plugin.video.pseudotv.live.qrcode.xml" , ADDON_PATH, "default", image=imagefile, text=msg, header=heading, atclose=autoclose)
            qr.doModal()
            del qr
            return True

        
    def _closeTextViewer(self):
        if self.builtin.getInfoBool('Window.IsActive(textviewer)'):
            self.builtin.executebuiltin('Dialog.Close(textviewer)')
        
        
    def _customTextViewer():
        class TEXTVIEW(xbmcgui.WindowXMLDialog):
            textbox = None
            def __init__(self, *args: Any, **kwargs: Any):
                self.head = kwargs.get('head','')
                self.text = kwargs.get('text','')
                self.doModal()
            
            def onInit(self):
                self.getControl(1).setLabel(self.head)
                self.textbox = self.getControl(5)

            def onClick(self, control_id: int): pass
            
            def onFocus(self, control_id: int): pass
            
            def onAction(self, action: Any):
                if action in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK]: self.close()

            def _updateText(self, txt: str):
                try:
                    self.textbox.setText(txt)
                    self.builtin.executebuiltin('SetFocus(3000)')
                    self.builtin.executebuiltin('AlarmClock(down,Action(down),.5,true,false)')
                except Exception as e: self.log('_updateText failed: %s' % e, xbmc.LOGDEBUG)
                
        return TEXTVIEW("DialogTextViewer.xml", os.getcwd(), "Default")


    def _textViewer(self, msg: str, heading: str, usemono: bool, autoclose: int) -> Any:
        return timerit(self.textviewer)(0.1,*(msg, heading, usemono, autoclose))
        
        
    def textviewer(self, msg: str, heading: str = ADDON_NAME, usemono: bool = False, autoclose: int = AUTOCLOSE_DELAY, usethread: bool = False, custom: bool = False) -> bool:
        # if custom: return self._customTextViewer(msg,heading,autoclose)
        if usethread: return self._textViewer(msg, heading, usemono, autoclose)
        else:
            if autoclose > 0: timerit(self._closeTextViewer)(autoclose)
            self.dialog.textviewer(heading, msg, usemono)
            return True
            
        
    def yesnoDialog(self, message: str, heading: str = ADDON_NAME, nolabel: str = '', yeslabel: str = '', customlabel: str = '', autoclose: int = AUTOCLOSE_DELAY) -> Union[int, bool]:
        if customlabel:
            # Returns the integer value for the selected button (-1:cancelled, 0:no, 1:yes, 2:custom)
            return self.dialog.yesnocustom(heading, message, customlabel, nolabel, yeslabel, (autoclose*1000))
        else: 
            # Returns True if 'Yes' was pressed, else False.
            return self.dialog.yesno(heading, message, nolabel, yeslabel, (autoclose*1000))


    def notificationWait(self, message: str, header: str = ADDON_NAME, wait: int = 4, silent: Optional[bool] = None, usethread: bool = False) -> bool:
        if silent is None: silent = not self.settings.showDialog(silent)
        if usethread: return timerit(self.notificationWait)(0.1, *(message, header, wait))
        status = True
        with self._progressDialog(message, header, silent) as pDialog:
            if pDialog is None: return
            remaning = int(wait)
            while not self.monitor.abortRequested() and remaning > 0:
                self._updateProgress(pDialog, int((abs(wait - remaning) * 100) // wait))
                if self.monitor.waitForAbort(1.0): 
                    status = False
                    break
                if isinstance(pDialog, xbmcgui.DialogProgress) and pDialog.iscanceled(): 
                    status = False
                    break
                if isinstance(pDialog, xbmcgui.DialogProgressBG) and pDialog.isFinished(): 
                    status = False
                    break
                remaning -= 1
            if hasattr(pDialog, 'close'): 
                pDialog.close()
        return status

    @contextmanager
    def _progressDialog(self, message: str = '', header: str = ADDON_NAME, silent: Optional[bool] = None, background: bool = True) -> Iterator:
        if silent is None: silent = not self.settings.showDialog(silent)
        dlg = None
        if not silent and dlg is None:
            with self._count_lock:
                Dialog._dialog_count += 1
                self.properties.setRunning('_progressDialog', True)
            try:
                if background: dlg = xbmcgui.DialogProgressBG()
                else:          dlg = xbmcgui.DialogProgress()
                dlg.create(header, message)
                if threading.current_thread() is not threading.main_thread():
                    self.monitor.waitForAbort(0.1)
                self.log(f'_progressDialog [0% - {dlg}] silent = {silent}\nheader = {header}\nmessage = {message}')
            except Exception as e:
                self.log(f'_progressDialog, failed! to create dialog: {e}')
                dlg = None
        try:
            if not dlg is None: yield dlg
            else:               yield True
        except Exception as e: self.log(f'_progressDialog, failed! {e}\n{traceback.format_exc()}')
        finally:
            if hasattr(dlg, 'close'): dlg.close()
            self.log(f'_progressDialog [100% - {dlg}] silent = {silent}\nheader = {header}\nmessage = {message}')
            with self._count_lock:
                Dialog._dialog_count = max(0, Dialog._dialog_count - 1)
                if Dialog._dialog_count <= 0:
                    Dialog._dialog_count = 0
                    self.properties.setRunning('_progressDialog', False)


    def _updateProgress(self, dlg: Optional[Any] = None, percent: int = 1, message: str = '', header: str = ADDON_NAME, wait: int = 0) -> Optional[Any]:
        """Update a progress dialog with the given percentage and message.
        
        Args:
            dlg: DialogProgressBG or DialogProgress instance, or None/bool to skip.
            percent: 0-100 progress value.
            message: Status message to display.
            header: Dialog title/header text.
            wait: Unused (legacy parameter).
        
        Returns:
            The dialog instance on success, or None if dialog is None/bool/failed.
            Always calls update() for DialogProgressBG — isFinished() can return True
            immediately after create() on some platforms.
        
        Example:
            self.pDialog = _globals().dialog._updateProgress(self.pDialog, 50, "Halfway done")
        """
        if dlg is None or isinstance(dlg, bool): return dlg
        try:
            if isinstance(dlg, xbmcgui.DialogProgressBG):
                if hasattr(dlg, 'update'):
                    self.log(f'_updateProgress [BG {percent}%] {header}: {message}', xbmc.LOGDEBUG)
                    dlg.update(percent, header, message)
                    # Yield to Kodi's UI thread so the dialog actually renders.
                    # Without this, update() calls from non-main threads are queued
                    # but never processed, resulting in a stuck 0% → 100% jump.
                    self.monitor.waitForAbort(0.1)
                    
            elif isinstance(dlg, xbmcgui.DialogProgress):
                if dlg.iscanceled(): return None
                elif hasattr(dlg, 'update'):
                    try:
                        match = _PROGRESS_RE.search(message)
                        if match:
                            message = '%s: %s' % (header.replace('%s, ' % (ADDON_NAME), ''), match.group(1))
                            percent = int(match.group(2))
                    except Exception as e: pass
                    self.log(f'_updateProgress [FG {percent}%] {message}', xbmc.LOGDEBUG)
                    dlg.update(percent, message)
                    self.monitor.waitForAbort(0.1)
        except Exception as e:
            return None
        return dlg
        
        
    def _updateProgressThrottled(self, dlg: Optional[Any] = None, percent: int = 1, message: str = '', header: str = ADDON_NAME, min_interval: float = 0.05) -> Optional[Any]:
        """Throttled version of _updateProgress — skips updates faster than min_interval.
        
        Prevents excessive UI updates during rapid loops (e.g., per-file buildFiles).
        Each dialog is tracked independently by id(dlg).
        
        Args:
            dlg: DialogProgressBG or DialogProgress instance.
            percent: 0-100 progress value.
            message: Status message to display.
            header: Dialog title/header text.
            min_interval: Minimum seconds between updates (default 0.05 = 50ms).
        
        Returns:
            The dialog instance (always, even on throttle skip — never returns None).
        
        Example:
            # Inside a fast loop — only updates UI every 50ms
            self.pDialog = _globals().dialog._updateProgressThrottled(self.pDialog, self.pCount, "Processing...")
        """
        if dlg is None or isinstance(dlg, bool): return dlg
        now = time.time()
        dlg_id = id(dlg)
        last = _PROGRESS_THROTTLE.get(dlg_id, 0)
        if (now - last) >= min_interval:
            _PROGRESS_THROTTLE[dlg_id] = now
            return self._updateProgress(dlg, percent, message, header)
        return dlg
        
        
    def progressDialog(self, percent: int = 0, control: Optional[xbmcgui.DialogProgress] = None, message: str = '', header: str = ADDON_NAME) -> Optional[xbmcgui.DialogProgress]:
        if control is None and int(percent) == 0:
            control = xbmcgui.DialogProgress()
            control.create(header, message)  
        elif control:
            with self._update_lock:
                try:
                    if int(percent) == 100 or control.iscanceled(): 
                        control.close()
                        return None
                    elif hasattr(control, 'update'): 
                        control.update(int(percent), message)
                except Exception:
                    return None
        return control
        
        
    def progressBGDialog(self, percent: int = 0, control: Optional[xbmcgui.DialogProgressBG] = None, message: str = '', header: str = ADDON_NAME) -> Optional[xbmcgui.DialogProgressBG]:
        if control is None and int(percent) == 0:
            control = xbmcgui.DialogProgressBG()
            control.create(header, message)
        elif control:
            with self._update_lock:
                try:
                    if int(percent) == 100 or control.isFinished(): 
                        control.close()
                        return None
                    elif hasattr(control, 'update'): 
                        control.update(int(percent), header, message)
                except Exception:
                    return None
        return control

                
    def infoDialog(self, listitem: xbmcgui.ListItem):
        self.dialog.info(listitem)
        
    
    def _notificationDialog(self, message: str, header: str, sound: bool, time: int, icon: str, silent: bool):
        threadit(self.notificationDialog)(message, header, sound, time, icon, silent)


    def notificationDialog(self, message: str, header: str = ADDON_NAME, sound: bool = False, time: int = PROMPT_DELAY, icon: str = LOGO_COLOR, silent: Optional[bool] = None, usethread: bool = False) -> bool:
        if silent is None: silent = not self.settings.showDialog(silent)
        self.log('notificationDialog: %s, silent = %s'%(message,silent))
        if not silent:
            if usethread: self._notificationDialog(message, header, sound, time, icon, silent)
            else:
                ## - Builtin Icons:
                ## - xbmcgui.NOTIFICATION_INFO
                ## - xbmcgui.NOTIFICATION_WARNING
                ## - xbmcgui.NOTIFICATION_ERROR
                try: self.dialog.notification(header, message, icon, time*1000, sound=False)
                except Exception: self.builtin.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time*1000, icon))
        return True
        
             
    def customSelect(self, items: list, header: str, preselect: Any, useDetails: bool, autoclose: int, multi: bool):
        """Custom select dialog placeholder (todo)."""
        class DialogSelect(xbmcgui.WindowXMLDialog):
            def __init__(self, *args: Any, **kwargs: Any):
                xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

            def onInit(self):
                LOG("DialogSelect: onInit")
                #todo get list control, convert items to listitems, additems to list control.
               
            def onAction(self, act: Any):
                actionId = act.getId()
                LOG('DialogSelect: onAction, actionId = %s'%(actionId))
                if actionId in ACTION_PREVIOUS_MENU: self.close()
                else: pass
                
        if not self.properties.isRunning('SELECT_OVERLAY'):
            dialogSelect = DialogSelect(DIALOG_SELECT, ADDON_PATH, "default")
            dialogSelect.doModal()
            del dialogSelect
        


    def selectDialog(self, items: list, header: str = ADDON_NAME, preselect: Optional[Any] = None, useDetails: bool = True, autoclose: int = SELECT_DELAY, multi: bool = True, custom: bool = False) -> Optional[Union[int, list]]:
        self.log('selectDialog, items = %s, header = %s, preselect = %s, useDetails = %s, autoclose = %s, multi = %s, custom = %s'%(len(items),header,preselect,useDetails,autoclose,multi,custom))
        if custom: return self.customSelect(items, header, preselect, useDetails, autoclose, multi)
        elif multi == True:
            if not preselect: preselect = [-1]
            with self._dialog_lock:
                select = self.dialog.multiselect(header, items, (autoclose*1000), preselect, useDetails)
            if select == [-1]: return
        else:
            if not preselect: preselect = -1
            elif isinstance(preselect,list) and len(preselect) > 0: preselect = preselect[0]
            with self._dialog_lock:
                select = self.dialog.select(header, items, (autoclose*1000), preselect, useDetails)
            if select == -1: return
        return select
      
      
    def inputDialog(self, message: str, default: str = '', key: int = xbmcgui.INPUT_ALPHANUM, opt: int = 0, close: int = 0) -> str:
        ## - key: xbmcgui.INPUT_ALPHANUM (standard keyboard)
        ## - key: xbmcgui.INPUT_NUMERIC (format: #)
        ## - key: xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
        ## - key: xbmcgui.INPUT_TIME (format: HH:MM)
        ## - key: xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
        ## - key: xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
        ## - opt: xbmcgui.PASSWORD_VERIFY (verifies an existing (default) md5 hashed password)
        ## - opt: xbmcgui.ALPHANUM_HIDE_INPUT (masks input)
        with self._dialog_lock:
            return self.dialog.input(message, default, key, opt, close)
        


    def importSTRM(self, strm: str) -> Optional[str]:
        try:
            with self.builtin.busyDialog():
                fle   = FileAccess.open(strm,'r')
                lines = fle.readlines()
                fle.close()
                paths = [line for line in lines if not line.startswith('#') and '://' in line]
                if len(paths) == 0: return self.notificationDialog(LANGUAGE(32018).format(type=LANGUAGE(30047)))
            select = self.selectDialog(paths, LANGUAGE(32080), useDetails=False, multi=False)
            self.log("importSTRM, strm = %s paths = %s"%(strm,paths))
            if not select is None: return paths[select]
        except Exception as e: self.log("importSTRM, failed! %s\n%s"%(e,strm), xbmc.LOGERROR)
             
               
    def _resourcePath(self, id: list = [], content: str = 'videos', ftype: str = '') -> str:
        if not id: id = self.browseResources(id, content, ftype, multi=False)
        path = 'special://home/addons/%s/resources/'%(id)
        self.log("_resourcePath [%s], content = %s, ftype = %s, path = %s"%(id, content, ftype,path))
        return path
        


    def browseResources(self, ids: list = [], content: str = 'videos', ftype: str = '', multi: bool = True) -> Optional[Union[str, list]]:
        #todo when no resources avail take user to Image Collections repo.
        self.log("browseResources, ids = %s, content = %s, ftype = %s, multi = %s"%(ids, content, ftype, multi))
        #todo selectDialog content and ftype.
        def __buildMenuItem(resource: dict) -> xbmcgui.ListItem:
            return self.listitems.buildMenuListItem(resource['name'],resource['description'],resource['thumbnail'],url=resource['addonid'])
             
        def __getResources() -> list:
            return self.jsonRPC.getAddons({"enabled":True})
        
        lizLST  = []
        with self.builtin.busyDialog():
            lizLST.extend(poolit(__buildMenuItem)([result for result in __getResources() if result.get('addonid').startswith('resource.%s.%s'%(content,ftype))]))

        selects = self.selectDialog(lizLST, LANGUAGE(30237), preselect=_globals()._findItemsInLST(lizLST,ids,'getPath'), multi=multi)
        if selects is None:                return
        elif not isinstance(selects,list): return lizLST[selects].getPath()
        else:                              return [lizLST[select].getPath() for select in selects]


    def browseSources(self, type: int = 0, heading: str = ADDON_NAME, default: str = '', shares: str = '', mask: str = '', useThumbs: bool = True, treatAsFolder: bool = False, multi: bool = False, monitor: bool = False, include: list = [], exclude: list = []) -> Optional[str]:
        self.log('browseSources, type = %s, heading= %s, shares= %s, useThumbs= %s, treatAsFolder= %s, default= %s, mask= %s, include= %s, exclude= %s'%(type,heading,shares,useThumbs,treatAsFolder,default,mask,len(include),exclude))
        def __buildMenuItem(option: dict) -> xbmcgui.ListItem:
            return self.listitems.buildMenuListItem(option['label'],option['label2'],_globals()._getDummyIcon(str(option['idx'])))

        with self.builtin.busyDialog():
            optlabel = "%s"%({'0':'Folders','1':'Files'}[str(type)]) if multi else "%s"%({'0':'Folder','1':'File'}[str(type)])
            opts = [{"idx":10, "label":'%s %s'%(LANGUAGE(32196),optlabel) , "label2":"library://video/"                      , "default":"library://video/"                   , "shares":"video"   , "mask":xbmc.getSupportedMedia('video')   , "type":0    , "multi":multi},
                    {"idx":11, "label":'%s %s'%(LANGUAGE(32207),optlabel) , "label2":"library://music/"                      , "default":"library://music/"                   , "shares":"music"   , "mask":xbmc.getSupportedMedia('music')   , "type":0    , "multi":multi},
                    {"idx":12, "label":LANGUAGE(32191)                    , "label2":"special://profile/playlists/video/"    , "default":"special://profile/playlists/video/" , "shares":""        , "mask":".xsp"                            , "type":1    , "multi":False},
                    {"idx":13, "label":LANGUAGE(32192)                    , "label2":"special://profile/playlists/music/"    , "default":"special://profile/playlists/music/" , "shares":""        , "mask":".xsp"                            , "type":1    , "multi":False},
                    {"idx":15, "label":LANGUAGE(32195)                    , "label2":"Dynamic SmartPlaylists"                , "default":""                                   , "shares":""        , "mask":""                                , "type":1    , "multi":False},
                    {"idx":16, "label":'STRM %s'%(LANGUAGE(32194))        , "label2":"Import paths from STRM file"           , "default":""                                   , "shares":"files"   , "mask":".strm"                           , "type":1    , "multi":False},
                    {"idx":17, "label":LANGUAGE(32206)                    , "label2":"Import files from Basic Playlist"      , "default":""                                   , "shares":""        , "mask":"|".join(BASIC_PLAYLISTS)         , "type":1    , "multi":False},
                    {"idx":18, "label":'%s %s'%(LANGUAGE(32198),optlabel) , "label2":""                                      , "default":""                                   , "shares":"files"   , "mask":mask                              , "type":type , "multi":multi},
                    {"idx":19, "label":'%s %s'%(LANGUAGE(32199),optlabel) , "label2":""                                      , "default":""                                   , "shares":"local"   , "mask":mask                              , "type":type , "multi":multi},
                    {"idx":20, "label":'%s %s'%(LANGUAGE(32200),optlabel) , "label2":""                                      , "default":""                                   , "shares":shares    , "mask":mask                              , "type":type , "multi":multi},
                    {"idx":21, "label":LANGUAGE(32201)                    , "label2":""                                      , "default":""                                   , "shares":"pictures", "mask":xbmc.getSupportedMedia('picture') , "type":1    , "multi":False},
                    {"idx":22, "label":LANGUAGE(32202)                    , "label2":"Image & Video Resources"               , "default":""                                   , "shares":shares    , "mask":mask                              , "type":type , "multi":multi}]

            options = include.copy()
            options.extend([opt for opt in opts if not opt.get('idx',-1) in exclude])
            options = _globals()._setDictLST(options)
            if default: options.insert(0,{"idx":0, "label":LANGUAGE(32203), "label2":default, "default":default, "shares":shares, "mask":mask, "type":type, "multi":multi})
            
            lizLST = []
            lizLST.extend(poolit(__buildMenuItem)(sorted(options, key=itemgetter('idx'))))
        select = self.selectDialog(lizLST, LANGUAGE(32089), multi=False)
        if select is None: return
        default = options[select]['default']
        shares  = options[select]['shares']
        mask    = options[select]['mask']
        type    = options[select]['type']
        multi   = options[select]['multi']
        if type == 0:
            if   "resource." in default or options[select]["idx"] == 22: return self._resourcePath(default, {xbmc.getSupportedMedia('video'):'videos',xbmc.getSupportedMedia('picture'):'images'}.get(mask,xbmc.getSupportedMedia('video')))
        elif type == 1:
            if   "?xsp="     in default or options[select]["idx"] == 15: return self.buildDXSP(default)
            elif ".strm"     in default or options[select]["idx"] == 16: return self.importSTRM(default)
            elif "resource." in default or options[select]["idx"] == 22: default = self._resourcePath(default, {xbmc.getSupportedMedia('video'):'videos',xbmc.getSupportedMedia('picture'):'images'}.get(mask,xbmc.getSupportedMedia('video')))
        return self.browseDialog(type, heading, default, shares, mask, useThumbs, treatAsFolder, multi, monitor)
            
    
    def browseDialog(self, type: int = 0, heading: str = ADDON_NAME, default: str = '', shares: str = '', mask: str = '', useThumbs: bool = True, treatAsFolder: bool = False, multi: bool = False, monitor: bool = False) -> Optional[str]:
        self.log('browseDialog, type = %s, heading= %s, shares= %s, useThumbs= %s, treatAsFolder= %s, default= %s\nmask= %s'%(type,heading,shares,useThumbs,treatAsFolder,default,mask))
        # https://xbmc.github.io/docs.kodi.tv/master/kodi-base/d6/de8/group__python___dialog.html#ga856f475ecd92b1afa37357deabe4b9e4
        # https://xbmc.github.io/docs.kodi.tv/master/kodi-base/d6/de8/group__python___dialog.html#gafa1e339e5a98ae4ea4e3d3bb3e1d028c
        self.toggleInfoMonitor(monitor)
        with self._dialog_lock:
            if multi == True and type > 0:  retval = self.dialog.browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)
            else:                           retval = self.dialog.browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        self.toggleInfoMonitor(False)
        if not retval is None and retval != default:
            return retval
        


    def multiBrowse(self, paths: list = [], header: str = ADDON_NAME, exclude: list = [], monitor: bool = True) -> list:
        self.log('multiBrowse, IN paths = %s'%(paths))
        def __buildListItem(item: str) -> xbmcgui.ListItem:
            idx = pathLST.index(item)
            return self.listitems.buildMenuListItem('%s|'%(idx+1), item, _globals()._getDummyIcon(str(idx+1)), url='|'.join(item), props={'idx':idx+1})

        select  = -1
        epaths  = paths.copy()
        pathLST = list([_f for _f in paths if _f])
        lastOPT = None
        while not self.monitor.abortRequested() and not select is None:
            with self.builtin.busyDialog():
                npath  = None
                lizLST = poolit(__buildListItem)(pathLST)
                lizLST.insert(0,__buildListItem(f'[COLOR=white][B]{LANGUAGE(34067)}[/B][/COLOR]','',icon=ICON,items={'key':'add','idx':0}))
                if len(pathLST) > 0 and epaths != pathLST: lizLST.insert(1,__buildListItem('[B]%s[/B]'%(LANGUAGE(32059)),LANGUAGE(33114),icon=ICON,items={'key':'save'}))
            
            select = self.selectDialog(lizLST, header, preselect=lastOPT, multi=False)
            if not select is None:
                key, path = lizLST[select].getProperty('key'), lizLST[select].getPath()
                try:    lastOPT = int(lizLST[select].getProperty('idx'))
                except Exception: lastOPT = -1
                if key == 'add': 
                    with self.builtin.busyDialog():
                        npath = self.browseSources(heading=LANGUAGE(32080), exclude=exclude, monitor=monitor)
                        if npath: pathLST.append(npath)
                elif key == 'save': 
                    paths = pathLST
                    break
                elif path in pathLST:
                    retval = self.yesnoDialog(LANGUAGE(32102), customlabel=LANGUAGE(32103))
                    if retval in [1,2]: pathLST.pop(pathLST.index(path))
                    if retval == 2:
                        with self.builtin.busyDialog():
                            npath = self.browseSources(heading=LANGUAGE(32080), default=path, monitor=monitor, exclude=exclude)
                            pathLST.append(npath)
        self.log('multiBrowse, OUT paths = %s'%(paths))
        return paths
           
           
    def buildDXSP(self, path: str = '') -> Optional[str]:
        # https://github.com/xbmc/xbmc/blob/master/xbmc/playlists/SmartPlayList.cpp
        
        def __mtype(params: dict = None) -> tuple:
            if params is None: params = {"type":"","rules":{"and":[],"or":[]},"order":{"direction":"ascending","method":"random","ignorearticle":True,"useartistsortname":True}}
            path    = ''
            enumLST = list(sorted(["albums", "artists", "episodes", "mixed", "movies", "musicvideos", "songs", "tvshows"]))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Media Type",preselect=(enumLST.index(params.get('type','')) if params.get('type') else -1),useDetails=False, multi=False)
            if not enumSEL is None:
                params['type'] = enumLST[enumSEL]
                if params['type'] in MUSIC_TYPES: db = 'musicdb'
                else:                             db = 'videodb'
                
                if   params['type'] == 'episodes':                         path = f"{db}://tvshows//titles/-1/-1/-1/"
                elif params['type'] in ['movies','tvshows','musicvideos']: path = f"{db}://{params['type']}/titles/"
                elif params['type'] in ['albums','artists','songs']:       path = f"{db}://songs/"
                else:                                                      path = ''
            return path, params
            
        def __andor(params: dict = {}) -> Optional[str]:
            enumLST = list(sorted(['and', 'or']))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Conjunction",preselect=(enumLST.index(list(params.get('rules',{}).keys())) if params.get('rules',{}) else -1),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]
                  
        def __order(params: dict = {}) -> Optional[str]:
            enums   = self.jsonRPC.getEnums("List.Sort",type="order") 
            enumLST = list(sorted([_f for _f in enums if _f]))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select order",preselect=enumLST.index(params.get('order',{}).get('direction','ascending')),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]
            
        def __method(params: dict = {}) -> Optional[str]:
            enums   = self.jsonRPC.getEnums("List.Sort",type="method") 
            enumLST = list(sorted([_f for _f in enums if _f]))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select method",preselect=enumLST.index(params.get('order',{}).get('method','random')),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]
            
        def __field(params: dict = {}, rule: dict = {}) -> Optional[str]:
            if   params.get('type') == 'songs':       enums = self.jsonRPC.getEnums("List.Filter.Fields.Songs"   , type='items')
            elif params.get('type') == 'albums':      enums = self.jsonRPC.getEnums("List.Filter.Fields.Albums"  , type='items')
            elif params.get('type') == 'artists':     enums = self.jsonRPC.getEnums("List.Filter.Fields.Artists" , type='items')
            elif params.get('type') == 'tvshows':     enums = self.jsonRPC.getEnums("List.Filter.Fields.TVShows" , type='items')
            elif params.get('type') == 'episodes':    enums = self.jsonRPC.getEnums("List.Filter.Fields.Episodes", type='items')
            elif params.get('type') == 'movies':      enums = self.jsonRPC.getEnums("List.Filter.Fields.Movies"  , type='items')
            elif params.get('type') == 'musicvideos': enums = self.jsonRPC.getEnums("List.Filter.Fields.MusicVideos", type='items')
            elif params.get('type') == 'mixed':       enums = self.jsonRPC.getEnums("List.Filter.Fields.Movies"  , type='items')
            else: return
            enumLST = list(sorted([_f for _f in enums if _f]))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Filter",preselect=(enumLST.index(rule.get('field')) if rule.get('field') else -1),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]

        def __operator(params: dict = {}, rule: dict = {}) -> Optional[str]:
            enumLST = sorted(self.jsonRPC.getEnums("List.Filter.Operators"))
            date_fields = ['lastplayed','dateadded','datemodified','datenew','airdate','time']
            if rule.get("field") not in date_fields:
                if 'inthelast'    in enumLST: enumLST.remove('inthelast')
                if 'notinthelast' in enumLST: enumLST.remove('notinthelast')
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Operator",preselect=(enumLST.index(rule.get('operator')) if rule.get('operator') else -1),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]

        def __value(params: dict = {}, rule: dict = {}) -> Optional[list]:
            return self.getValue(params, rule)
            
        def __getRule(params: dict = {}, rule: dict = {"field":"","operator":"","value":[]}) -> dict:
            enumSEL = -1
            while not self.monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value),icon=_globals()._getDummyIcon(_globals()._getAbbr(key.title())),props={'key':key,'value':value}) for key, value in list(rule.items())]
                enumSEL = self.selectDialog(enumLST,header="Select method",preselect=-1, multi=False)
                if not enumSEL is None: rule.update({enumLST[enumSEL].getProperty('key'):({"field":__field,"operator":__operator,"value":__value}[enumLST[enumSEL].getProperty('key')])(params,rule)})
            return rule
            
        def __getRules(params: dict = {}) -> dict:
            enumSEL = -1
            eparams = params.copy()
            while not self.monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),FileAccess.dumpJSON(params.get('rules',{}).get(key,[])),icon=_globals()._getDummyIcon(_globals()._getAbbr(key.title())),props={'key':key}) for key in ["and","or"]]
                enumSEL = self.selectDialog(enumLST,header="Edit Rules",multi=False)
                if not enumSEL is None:
                    if enumLST[enumSEL].getLabel() in ['And','Or']:
                        CONSEL  = -1
                        CONLKEY = enumLST[enumSEL].getProperty('key')
                        ruleLST = params.get('rules',{}).get(CONLKEY,[])
                        while not self.monitor.abortRequested() and not CONSEL is None:
                            andLST = [self.listitems.buildMenuListItem('%s|'%(idx+1),FileAccess.dumpJSON(value),icon=_globals()._getDummyIcon(str(idx+1)),props={'idx':str(idx)}) for idx, value in enumerate(ruleLST)]
                            andLST.insert(0,self.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32173)),"",icon=ICON,props={'key':'add'}))
                            if len(ruleLST) > 0 and eparams != params: andLST.insert(1,self.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32174)),"",icon=ICON,props={'key':'save'}))
                            CONSEL = self.selectDialog(andLST,header="Edit Rules",multi=False)
                            if not CONSEL is None:
                                if   andLST[CONSEL].getProperty('key') == 'add': ruleLST.append(__getRule(params,{"field":"","operator":"","value":[]}))
                                elif andLST[CONSEL].getProperty('key') == 'save': 
                                    params.setdefault('rules',{})[CONLKEY] = ruleLST
                                    break
                                elif sorted(FileAccess.loadJSON(andLST[CONSEL].getLabel2())) in [sorted(andd) for andd in ruleLST]:
                                    retval = self.yesnoDialog(LANGUAGE(32175), customlabel=LANGUAGE(32176))
                                    if retval in [1,2]: ruleLST.pop(int(andLST[CONSEL].getProperty('idx')))
                                    if retval == 2:     ruleLST.append(__getRule(params,FileAccess.loadJSON(andLST[CONSEL].getLabel2())))
                                else:                   ruleLST.append(__getRule(params,FileAccess.loadJSON(andLST[CONSEL].getLabel2())))
            return params

        def __getOrder(params: dict = {}) -> dict:
            enumSEL = -1
            while not self.monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value).title(),icon=_globals()._getDummyIcon(_globals()._getAbbr(key.title()))) for key, value in list(params.get('order',{}).items())]
                enumLST.insert(0,self.listitems.buildMenuListItem(f'[COLOR=white][B]{LANGUAGE(32174)}[/B][/COLOR]',"",icon=ICON,props={'key':'save'}))
                enumSEL = self.selectDialog(enumLST,header="Edit Selection",preselect=-1,multi=False)
                if not enumSEL is None:
                    if   enumLST[enumSEL].getLabel() == 'Direction': params['order'].update({'direction':__order(params)})
                    elif enumLST[enumSEL].getLabel() == 'Method':    params['order'].update({'method':__method(params)})
                    elif enumLST[enumSEL].getProperty('key') == 'save': break
                    else: params['order'].update({enumLST[enumSEL].getLabel().lower(): not enumLST[enumSEL].getLabel2() == 'True'})
            return params

        try:
            path, params = path.split('?xsp=')
            params = FileAccess.loadJSON(params)
        except Exception:
            path, params = __mtype()
        self.log('buildDXSP, path = %s, params = %s'%(path,params))
        
        enumSEL = -1
        while not self.monitor.abortRequested() and not enumSEL is None:
            enumLST = [self.listitems.buildMenuListItem('Path',path,icon=ICON),self.listitems.buildMenuListItem('Order',FileAccess.dumpJSON(params.get('order',{})),icon=ICON),self.listitems.buildMenuListItem('Rules',FileAccess.dumpJSON(params.get('rules',{})),icon=ICON)]
            enumSEL = self.selectDialog(enumLST,header="Edit Dynamic Path", multi=False)
            if not enumSEL is None:
                if   enumLST[enumSEL].getLabel() == 'Path':  path, params = __mtype(params)
                elif enumLST[enumSEL].getLabel() == 'Order': params = __getOrder(params)
                elif enumLST[enumSEL].getLabel() == 'Rules': params = __getRules(params)
        
        rules = params.get('rules', {})
        if len(rules.get('and', [])) > 0 or len(rules.get('or', [])) > 0:
            url = '%s?xsp=%s'%(path,FileAccess.dumpJSON(params))
            self.log('buildDXSP, returning %s'%(url))
            return url


    def getValue(self, params: dict = {}, rule: dict = {}) -> Optional[list]:
        def __getInput() -> str:  return self.inputDialog("Enter Value\nSeparate by ',' ex. Action,Comedy",','.join([_globals()._unquoteString(value) for value in rule.get('value',[])]))
        def __getBrowse() -> str: return self.browseSources(default='|'.join([_globals()._unquoteString(value) for value in rule.get('value',[])]))
        def __getSelect() -> Any: return self.notificationDialog(LANGUAGE(32020))
        enumLST = sorted(['Enter', 'Browse', 'Select'])
        enumKEY = {'Enter':{'func':__getInput},'Browse':{'func':__getBrowse},'Select':{'func':__getSelect}}
        enumSEL = self.selectDialog(enumLST,header="Select Input",useDetails=False, multi=False)
        if not enumSEL is None: return [_globals()._quoteString(value) for value in (enumKEY[enumLST[enumSEL]].get('func')()).split(',')]
        
class Kodi(object):
    _instance = None 
    
    def __new__(cls) -> 'Kodi':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, service: Optional[_Service] = None):
        if service is None: service = _Service()
        self.dialog     = Dialog(service)
        self.settings   = self.dialog.settings
        self.properties = self.dialog.properties
        self.listitems  = self.dialog.listitems
        self.builtin    = self.dialog.builtin
