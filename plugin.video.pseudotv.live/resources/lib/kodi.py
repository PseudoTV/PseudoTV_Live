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
import platform, pyqrcode, threading, copy

from ast                 import literal_eval
from uuid                import uuid1, uuid4, UUID
from constants           import *
from logger              import log
from cache               import Cache, cacheit
from fileaccess          import FileAccess, FileLock
from infotagger.listitem import ListItemInfoTag
from json2html           import Json2Html
from pool                import debounceit, timeit, poolit, executeit, timerit, threadit, ExecutorPool


def _getGlobals():
    """Resolve dynamic helpers after variables.py has finished initializing."""
    from variables import Globals
    return Globals

class Settings(object):
    dialog = None
    def __init__(self, service):
        from instances import Instances
        self.pool      = service.pool
        self.jsonRPC   = service.jsonRPC
        self.cache     = service.cache
        self.monitor   = service.monitor
        self.instances = Instances(settings=self)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def getRealSettings(self, id=ADDON_ID):
        try:              return xbmcaddon.Addon(id)
        except Exception: return REAL_SETTINGS


    #GET
    def _getSetting(self, func, key):
        try: 
            value = func(key)
            self.log(f'[{ADDON_ID}] {func.__name__}, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
            return value
        except Exception as e: self.log("_getSetting, failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
      
      
    def getSetting(self, key):
        return self._getSetting(self.getRealSettings().getSetting,key)
        
        
    def getSettingBool(self, key):
        return self._getSetting(self.getRealSettings().getSettingBool,key)


    def getSettingInt(self, key):
        return self._getSetting(self.getRealSettings().getSettingInt,key)
              
              
    def getSettingNumber(self, key): 
        return self._getSetting(self.getRealSettings().getSettingNumber,key)
        
        
    def getSettingString(self, key):
        return self._getSetting(self.getRealSettings().getSettingString,key)


    def getSettingFloat(self, key):
        return float(self.getSetting(key))
              
              
    def getSettingList(self, key):
        return [value for value in self.getSetting(key).split('|')]
       
       
    def getSettingBoolList(self, key):
        return [value.lower() == "true" for value in self.getSetting(key).split('|')]
        
        
    def getSettingIntList(self, key):
        return [int(value) for value in self.getSetting(key).split('|') if isinstance(value,int)]
        
        
    def getSettingNumberList(self, key):
        return [literal_eval(value) for value in self.getSetting(key).split('|')]
        

    def getSettingFloatList(self, key):
        return [float(value) for value in self.getSetting(key).split('|') if isinstance(value,float)]
        

    def getSettingDict(self, key):
        return FileAccess._decodeString(self.getSetting(key))
    
    
    def getCacheSetting(self, key, checksum=ADDON_VERSION, default=None):
        value = self.cache.get(key, checksum)
        self.log(f'[{ADDON_ID}] getCacheSetting, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return (value or default)
        
        
    def getEXTSetting(self, id, key):
        value = xbmcaddon.Addon(id).getSetting(key)
        self.log(f'[{ADDON_ID}] getEXTSetting, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return value
        
        
    #CLR
    def clrCacheSetting(self, key):
        self.cache.clr(key)
    
    
    #SET
    def _setSetting(self, func, key, value):
        try:
            if str(self.getSetting(key)).lower() != str(value).lower(): func(key,value)
            self.log(f'[{ADDON_ID}] {func.__name__}, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        except Exception as e: self.log("_setSetting, failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
            
        
    def setSetting(self, key, value=""):
        self._setSetting(self.getRealSettings().setSetting,key,str(value))
        return value
            
            
    def setSettingBool(self, key, value):
        return self._setSetting(self.getRealSettings().setSettingBool,key,value)
        
        
    def setSettingInt(self, key, value):  
        return self._setSetting(self.getRealSettings().setSettingInt,key,value)
                   
                   
    def setSettingNumber(self, key, value):  
        return self._setSetting(self.getRealSettings().setSettingNumber,key,value)
        
             
    def setSettingString(self, key, value):  
        return self._setSetting(self.getRealSettings().setSettingString,key,value)


    def setSettingBoolList(self, key, value):
        return self.setSetting(key,('|').join(value))
        
        
    def setSettingIntList(self, key, value):  
        return self.setSetting(key,('|').join(value))
         
            
    def setSettingNumberList(self, key, value):  
        return self.setSetting(key,('|').join(value))
        

    def setSettingList(self, key, values):
        return self.setSetting(key,('|').join(value))
                   
                   
    def setSettingFloat(self, key, value):  
        return self.setSetting(key,value)
        
        
    def setSettingDict(self, key, values):
        return self.setSetting(key,FileAccess._encodeString(values))
            
            
    def setCacheSetting(self, key, value=None, checksum=ADDON_VERSION, life=datetime.timedelta(days=28)):
        self.log(f'[{ADDON_ID}] setCacheSetting, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return self.cache.set(key, value, checksum, life)
  
  
    def setEXTSetting(self, id, key, value):
        self.log(f'[{ADDON_ID}] setEXTSetting, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return xbmcaddon.Addon(id).setSetting(key,value)


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def getIP(self, default='0.0.0.0'):
        IP = (xbmc.getIPAddress() or gethostbyname(gethostname()) or default)
        log('getIP, IP = %s'%(IP))
        return IP
    
    
    def hasAddon(self, id, install=None, enable=None, force=None, notify=False):
        def __getIDbyPath(url):
            try:
                if   url.startswith('special://profile/addon_data/'):      return re.compile('special://profile/addon_data/(.*?)', re.IGNORECASE).search(url).group(1)
                elif url.startswith('special://home/addons/'):             return re.compile('special://home/addons/(.*?)/resources', re.IGNORECASE).search(url).group(1)
                elif url.startswith(('plugin://','resource://','pvr://')): return re.compile('(.*)://(.*?)/', re.IGNORECASE).search(url).group(2)
            except Exception: pass
            return url
            
        def __hasADDON(id):
            if not id: return False
            hasAddon  = self.dialog.builtin.getInfoBool('System.HasAddon(%s)'%(id))
            isEnabled = self.dialog.builtin.getInfoBool('System.AddonIsEnabled(%s)'%(id))
            self.log(f'[{id}] hasAddon = {hasAddon}, isEnabled = {isEnabled}, Kodi Override = {bypass}')
            if hasAddon:
                if isEnabled: return True
                elif enable:
                    if not force:
                        if not self.dialog.yesnoDialog(message=LANGUAGE(32156)%(id)):
                            self.log('[%s] hasAddon, (Not Enabled!)'%(id))
                            return isEnabled
                    self.dialog.builtin.executebuiltin(f'EnableAddon({id})',wait=True)
                elif notify: self.dialog.notificationDialog(LANGUAGE(32264)%(id))
            elif install: self.dialog.builtin.executebuiltin(f'InstallAddon({id})',wait=True)
            elif notify:  self.dialog.notificationDialog(LANGUAGE(32034)%(id))
            return self.dialog.builtin.getInfoBool(f'System.HasAddon({id})')
        
        bypass = self.getSettingBool('Enable_Kodi_Access')
        if install is None: install = bypass
        if enable  is None: enable  = bypass
        if force   is None: force   = bypass
        if '://' in id: id = __getIDbyPath(id)
        return __hasADDON(id)
            
            
    @cacheit(expiration=datetime.timedelta(minutes=15))
    def getAddonDetails(self, id=ADDON_ID):
        try:
            if not id: raise Exception("Missing ID")
            addon = xbmcaddon.Addon(id)
            properties = ['name', 'version', 'summary', 'description', 'path', 'author', 'icon', 'disclaimer', 'fanart', 'changelog', 'id', 'profile', 'stars', 'type']
            return dict([(property,addon.getAddonInfo(property)) for property in properties])
        except Exception:
            from jsonrpc import JSONRPC
            return JSONRPC().getAddonDetails(id)


    def getMYUUID(self):
        def __genUUID(seed=None):
            if seed:
                m = hashlib.md5()
                m.update(seed.encode(DEFAULT_ENCODING))
                return str(UUID(m.hexdigest()))
            return str(uuid1(clock_seq=70420))
            
        friendly = self.dialog.properties.getFriendlyName()
        uuid = self.getCacheSetting('MY_UUID', checksum=friendly, default=None)
        if not uuid: uuid = self.setCacheSetting('MY_UUID', __genUUID(seed=self.dialog.properties.getFriendlyName()), checksum=friendly)
        return uuid


    @cacheit(expiration=datetime.timedelta(minutes=5))
    def getBonjour(self):
        def __getResumeURLs(remote):
            keys = self.getCacheSetting(RESUME_INDEX, FileAccess._getMD5(RESUME_INDEX), default={})
            return ['http://%s/filelist/%s'%(remote,key) for key in keys]
            
        def __getChannels():
            from channels import Channels
            return Channels().getChannels()
            
        host    = self.property.getRemoteHost()
        payload = {'id'       :ADDON_ID,
                   'host'     :host,
                   'uuid'     :self.getMYUUID(),
                   'name'     :self.dialog.properties.getFriendlyName(),
                   'version'  :ADDON_VERSION,
                   'machine'  :platform.machine(),
                   'platform' :self.dialog.builtin.getInfoLabel('System.OSVersionInfo'),
                   'build'    :self.dialog.builtin.getInfoLabel('System.BuildVersion'),
                   'python'   :platform.python_version(),
                   'remotes'  : {'m3u'     :'http://%s/%s'%(host,M3UFLE),
                                 'xmltv'   :'http://%s/%s'%(host,XMLTVFLE),
                                 'genre'   :'http://%s/%s'%(host,GENREFLE),
                                 'bonjour' :'http://%s/api/%s'%(host,BONJOURFLE),
                                 'servers' :'http://%s/api/%s'%(host,SERVERFLE),
                                 'library' :'http://%s/api/%s'%(host,LIBRARYFLE),
                                 'channels':'http://%s/api/%s'%(host,CHANNELFLE),
                                 'logs'    :'http://%s/api/%s'%(host,LOGSFLE),
                                 'resume'  : __getResumeURLs(host)},
                   'settings' : {'Resource_Logos'    :self.getSetting('Resource_Logos').split('|'),
                                 'Resource_Bumpers'  :self.getSetting('Resource_Bumpers').split('|'),
                                 'Resource_Ratings'  :self.getSetting('Resource_Ratings').split('|'),
                                 'Resource_Adverts'  :self.getSetting('Resource_Adverts').split('|'),
                                 'Resource_Trailers' :self.getSetting('Resource_Trailers').split('|')}}
                   
        payload['md5']     = FileAccess._getMD5(FileAccess.dumpJSON(payload))
        payload['updated'] = datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
        self.log(f"getBonjour:\npayload = %s"%(payload))
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
                                  # 'programmes':[{'id':key,'end-time':epochTime(time.time(),tz=False).strftime(DTFORMAT)} for key, value in list(dict(xmltv.loadStopTimes()).items())]}
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
        # return Json2Html().convert(self.getPayload(inclDebug=True))


    def hasAutotuned(self):
        return self.dialog.properties.setProperty('has.Autotuned',self.getCacheSetting('has.Autotuned', default=False))
        
        
    def setAutotuned(self, state=True):
        max_guide_days = int(REAL_SETTINGS.getSetting('Max_Days') or "3")
        return self.dialog.properties.setProperty('has.Autotuned',self.setCacheSetting('has.Autotuned', state, life=datetime.timedelta(days=max_guide_days)))


    def hasPVRInstance(self, instanceName=ADDON_NAME):
        instancePath = self.instances.getPVRInstancePath(instanceName)
        if FileAccess.exists(instancePath):
            self.log('[%s] hasPVRInstance, instanceName = %s, path = %s'%(PVR_CLIENT_ID,instanceName, instancePath))
            return instancePath
        

    def setPVRPath(self, path, instanceName=ADDON_NAME):
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
        settings.update(nsettings)
        if self.chkPVRChanges(instanceName, settings.copy()):
            self.log('[%s] setPVRPath, %s settings = %s'%(PVR_CLIENT_ID, instanceName, nsettings))
            return self.instances.setSettings(instanceName, settings)
        
                
    def setPVRLocal(self, host, instanceName=ADDON_NAME):
        settings  = self.instances.getSettings(instanceName)
        processID = self.dialog.properties.getProcessID()
        nsettings = {'kodi_addon_instance_name'   : '%s - %s'%(ADDON_NAME,instanceName),
                     'kodi_addon_instance_enabled':'true',
                     'm3uPathType'                :'1',
                     # 'm3uUrl'                     :'http://%s/%s.%s'%(host,M3UFLE,processID),
                     'm3uUrl'                     :'http://%s/%s'%(host,M3UFLE),
                     'm3uCache'                   :'true',
                     'epgPathType'                :'1',
                     'epgUrl'                     :'http://%s/%s'%(host,XMLTVFLE),
                     'epgCache'                   :'true',
                     'genresPathType'             :'1',
                     'genresUrl'                  :'http://%s/%s'%(host,GENREFLE),
                     'logoPathType'               :'1',
                     'logoBaseUrl'                :'http://%s/logos'%(host)}
        settings.update(nsettings)
        if self.chkPVRChanges(instanceName, settings.copy()):
            self.log('[%s] setPVRLocal, %s settings = %s'%(PVR_CLIENT_ID, instanceName, nsettings))
            return self.instances.setSettings(instanceName, settings)
        
        
    def setPVRRemote(self, host, instanceName=ADDON_NAME, cache=True):
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


    def chkPVRChanges(self, instanceName=ADDON_NAME, nsettings={}, prompt=None):
        if prompt is None: prompt = not bool(self.getSettingBool('Enable_Kodi_Access'))
        changes = []
        if self.hasPVRInstance(instanceName):
            xsettings = self.instances.getSettings(instanceName)
            for setting, value in list(nsettings.items()):
                if    str(value).lower() == str(xsettings.get(setting,'')).lower(): nsettings.pop(setting)
                else: changes.append('%s: [COLOR=dimgray][B]%s[/B][/COLOR] => [COLOR=green][B]%s[/B][/COLOR]'%(setting,str(xsettings.get(setting)),str(value)))

        if len(nsettings) > 0:
            if prompt:
                self.dialog.textviewer('%s\n\n%s'%(LANGUAGE(32035)%(PVR_CLIENT_NAME),'[CR]'.join(changes)))
                if not self.dialog.yesnoDialog((LANGUAGE(32036)%addon.getAddonInfo('name'))):
                    self.dialog.notificationDialog(LANGUAGE(32046))
                    return False
            self.log('[%s] chkPVRChanges, instanceName = %s, prompt = %s, changes = %s'%(PVR_CLIENT_ID,instanceName,prompt,nsettings))
            return True
        self.log('[%s] chkPVRChanges, no changes detected!'%(PVR_CLIENT_ID))
        return False
        

    def getCurrentSettings(self):
        settings = ['User_Folder', 'Debug_Enable', 'TCP_PORT', 'Enable_Autotune', 'Remove_BG_APIKEY', 'Open_Router_APIKEY', 'Enable_Kodi_Access']
        return dict([(setting,self.getSetting(setting)) for setting in settings])
              
              
    def restoreSettings(self, settings={}):
        return any([self.setSetting(k,v) for k,v in list(settings.items())])


    def getFileCRC(self, file):
        try:
            fle = FileAccess.open(file,'r')
            crc = binascii.crc32(fle.read().encode(DEFAULT_ENCODING))
        except Exception as e:
            self.log("getFileCRC, failed! %s"%(file,e), xbmc.LOGERROR)
            return False
        finally:
            fle.close()
        name  = 'getFileCRC.%s'%(FileAccess._getMD5(file))
        cache = self.getCacheSetting(name, checksum=crc)
        if not cache or cache != crc:
            self.setCacheSetting(name, crc, checksum=crc)
            return True
        return False
            
            
    def getLogs(self, time=None):
        if time is None: time = datetime.datetime.fromtimestamp(time.time())
        return self.getCacheSetting('LOGS', FileAccess._getMD5(time.strftime('%Y%m%d')), default={})
        
        
    def setLogs(self, key, event):
        time = datetime.datetime.fromtimestamp(time.time())
        logs = self.getLogs(time)
        logs.setdefault(key,[]).append(f'{time.strftime(DTFORMAT)} - {event}')
        self.setCacheSetting('LOGS', logs, FileAccess._getMD5(time.strftime('%Y%m%d')), datetime.timedelta(days=2))
            
            
    def showDialog(self, silent=None):
        #True Show/False Silent
        if self.getSettingBool('Debug_Enable'): return True
        if silent: return False
        if not self.dialog.builtin.isPlaying(): return True
        return self.getSettingBool('Notify_While_Playing')
            
            
class Properties(object):
    dialog = None
    def __init__(self, service, winID=10131):
        self.pool       = service.pool
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.cache
        self.monitor    = service.monitor
        self.winID      = winID
        self.window     = xbmcgui.Window(winID)
        self._memory_cache = OrderedDict()
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def getProcessID(self):
        processID = self.getEXTProperty('%s.ProcessID'%(ADDON_ID))
        if not processID: processID = self.setProcessID()
        return processID


    def setProcessID(self):
        self._clrTrash(self.getEXTProperty('%s.ProcessID'%(ADDON_ID),None))
        return self.setEXTProperty('%s.ProcessID'%(ADDON_ID),FileAccess._getMD5(uuid4()))
        

    def _clrTrash(self, processID=None): #clear abandoned properties after processID change
        if processID:
            tmpDCT = self._getTrash()
            if processID in tmpDCT:
                self.log('_clrTrash, processID = %s'%(processID))
                tmpLST = tmpDCT.pop(processID)
                for prop in tmpLST:
                    self.clrProperty(prop)


    def _getTrash(self):
        try:    return (FileAccess._decodeString(self.getEXTProperty('%s.TRASH'%(ADDON_ID),{})) or {})
        except: return {}


    def _setTrash(self, key, processID): #catalog instance properties that are abandoned
        tmpDCT = self._getTrash()
        if key not in tmpDCT.setdefault(processID,[]):
            tmpDCT.setdefault(processID,[]).append(key)
            self.setEXTProperty('%s.TRASH'%(ADDON_ID),str(FileAccess._encodeString(tmpDCT)))

        
    def _getKey(self, key, useInstance=True):
        if not key.startswith(ADDON_ID): key = '%s.%s'%(ADDON_ID,key)
        if useInstance: 
            thid = threading.get_ident()
            pid  = self.getProcessID()
            key  = '%s.%s.%s'%(key,pid,thid)
            self._setTrash(key, pid)
            return key, thid
        return key, '-1'


    #GET
    def getProperty(self, key, default=''):
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
            
        
    def getEXTProperty(self, key, default=''):
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
        
        
    def clrProperty(self, key):
        key, thid = self._getKey(key)
        self.log(f'[{self.winID}] clrProperty [{thid}], key = {key}')
        self._memory_cache.pop(key, None)
        return self.window.clearProperty(key)


    def clrEXTProperty(self, key):
        self.log('[%s] clrEXTProperty, key = %s'%('10000', key))
        self._memory_cache.pop(key, None)
        return xbmcgui.Window(10000).clearProperty(key)
        
        
    #SET
    def setProperty(self, key, value):
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
        
        
    def setEXTProperty(self, key, value):
        if value is None or value == '': return value
        self._memory_cache[key] = copy.deepcopy(value)
        self._memory_cache.move_to_end(key)
        if len(self._memory_cache) > MAX_CACHE_SIZE: oldest_key, _ = self._memory_cache.popitem(last=False)
        xbmcgui.Window(10000).setProperty(key,str(value))
        if not '.TRASH' in key: self.log(f'[10000] setEXTProperty, key = {key}, value = {str(value)[:128]}, type = {type(value).__name__}')
        return value


    def setTrakt(self, state=False):
        self.log('setTrakt, disable trakt = %s'%(state))
        # https://github.com/trakt/script.trakt/blob/d45f1363c49c3e1e83dabacb70729cc3dec6a815/resources/lib/kodiUtilities.py#L104
        if state: self.setEXTProperty('script.trakt.paused',state)
        else:     self.clrEXTProperty('script.trakt.paused')


    @debounceit(SERVICE_INTERVAL)
    def setPropTimer(self, key, state=True):
        if not key.startswith(ADDON_ID): key = '%s.%s'%(ADDON_ID, key)
        return self.setEXTProperty(key,state)


    def getPropTimer(self, key, state=True, default=False):
        if not key.startswith(ADDON_ID): key = '%s.%s'%(ADDON_ID, key)
        return self.getEXTProperty(key,default)


    def setRemoteHost(self, value):
        return self.setEXTProperty('%s.Remote_Host'%(ADDON_ID),value)
        
        
    def getRemoteHost(self):
        remote = self.getEXTProperty('%s.Remote_Host'%(ADDON_ID))
        if not remote: remote = self.setRemoteHost('%s:%s'%(self.dialog.settings.getIP(),self.dialog.settings.getSettingInt('TCP_PORT')))
        return remote


    def setHasChannels(self, key=None, channelDATA=None):
        if key is None: key = CHANNELAUTOTUNE_KEY if self.dialog.settings.getSettingBool('Enable_Autotune') else CHANNEL_KEY
        if channelDATA is None: channelDATA = Channels(key).channelDATA
        chanLST = self.dialog.settings.getCacheSetting('%s.has.Channels'%(ADDON_ID), default={})
        if len(channelDATA.get('channels',[])) > 0: 
            channelDATA.update({'updated': datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)})
            chanLST.setdefault(key,{}).update(channelDATA)
        elif key in chanLST: chanLST.pop(key)
        return self.dialog.settings.setCacheSetting('%s.has.Channels'%(ADDON_ID),chanLST,life=-1).get(key)
        
        
    def hasChannels(self, key=None, path=None):
        if key is None: key = CHANNELAUTOTUNE_KEY if self.dialog.settings.getSettingBool('Enable_Autotune') else CHANNEL_KEY
        if not path is None: 
            if FileAccess.exists(path): channelDATA = FileAccess.getJSON(path)
        else:                           channelDATA = self.dialog.settings.getCacheSetting('%s.has.Channels'%(ADDON_ID), default={}).get(key,{})
        return len(channelDATA.get('channels',[])) > 0
        

    def setBackup(self, key=CHANNELBACKUP_KEY, channels=None):
        backups = self.dialog.settings.getCacheSetting('%s.has.backups'%(ADDON_ID), default={})
        if channels is None: channels = Channels(key).getChannels()
        if len(channels) > 0: backups.setdefault(key,{}).update({'name':key, 'channels': channels, 'updated':(backups.get(key,{}).get('updated') or datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT))})
        elif key in backups:  backups.pop(key)
        return self.dialog.settings.setCacheSetting('%s.has.backups'%(ADDON_ID),backups,life=-1).get(key)


    def hasBackup(self, key=CHANNELBACKUP_KEY, path=None):
        if not path is None: 
            if FileAccess.exists(path): return FileAccess.getJSON(path)
        else:                           return self.dialog.settings.getCacheSetting('%s.has.backups'%(ADDON_ID), default={}).get(key)


    def hasBackups(self):
        return len(list(self.dialog.settings.getCacheSetting('%s.has.backups'%(ADDON_ID), default={}).keys())) > 0


    def hasLibrary(self, type=None):
        if not type is None: return self.getEXTProperty('%s.has.%s'%(ADDON_ID,type),False)
        return any(self.getEXTProperty('%s.has.%s'%(ADDON_ID,t),False) for t in AUTOTUNE_TYPES)
        
        
    def setHasLibrary(self, type, state=True):
        return self.setEXTProperty('%s.has.%s'%(ADDON_ID,type),state)
        
        
    def setHasServers(self, state=True):
        return self.setEXTProperty('%s.has.Servers'%(ADDON_ID),state)
        

    def hasServers(self):
        return self.getEXTProperty('%s.has.Servers'%(ADDON_ID),False)
        
                
    def setEnabledServers(self, state=True):
        return self.setEXTProperty('%s.has.Enabled_Servers'%(ADDON_ID),state)
        
        
    def hasEnabledServers(self):
        return self.getEXTProperty('%s.has.Enabled_Servers'%(ADDON_ID),False)
        
        
    def setPendingShutdown(self, state=True):
        return self.setEXTProperty('%s.SERVICE.pendingShutdown'%(ADDON_ID),state)
        

    def isPendingShutdown(self):
        value = self.getEXTProperty('%s.SERVICE.pendingShutdown'%(ADDON_ID),False)
        return value
        
                
    def setPendingRestart(self, state=True):
        return self.setEXTProperty('%s.SERVICE.pendingRestart'%(ADDON_ID),state)


    def isPendingRestart(self):
        value = self.getEXTProperty('%s.SERVICE.pendingRestart'%(ADDON_ID),False)
        return value


    @contextmanager
    def chkRunning(self, key):
        try:
            if not self.isRunning(key):
                self.setRunning(key,True)
                yield False
            else:
                yield True
        finally:
            self.setRunning(key,False)
            
            
    def setRunning(self, key, state=True):
        return self.setEXTProperty('%s.%s.Running'%(ADDON_ID,key),state)
        
        
    def isRunning(self, key):
        return self.getEXTProperty('%s.%s.Running'%(ADDON_ID,key),False)


    @contextmanager
    def lockActivity(self, state=True):
        try:
            if not self.isLockActivity():
                self.setLockActivity(True)
                yield True
            else:
                yield False
        finally:
            self.setLockActivity(False)
            

    def setLockActivity(self, state=True): # context state
        return self.setEXTProperty('%s.lockActivity'%(ADDON_ID),state)


    def isLockActivity(self):# context state
        return self.getEXTProperty('%s.lockActivity'%(ADDON_ID),False)


    @contextmanager
    def interruptActivity(self, wait=-1): #quit background task
        while not self.monitor.abortRequested() and (self.isInterruptActivity() or self.isLockActivity()):
            if wait > 0: wait -= CPU_CYCLE #wait -1 runs indefinitely. 
            if self.monitor.waitForAbort(CPU_CYCLE) or int(wait) == 0: break
        self.setPendingInterrupt(self.setInterruptActivity(True))
        try: yield
        finally: 
            self.setPendingInterrupt(self.setInterruptActivity(False))
        
           
    def setInterruptActivity(self, state=True): # context state
        return self.setProperty('%s.interruptActivity'%(ADDON_ID),state)
        

    def isInterruptActivity(self): # context state
        return self.getProperty('%s.interruptActivity'%(ADDON_ID),False)


    def setPendingInterrupt(self, state=True): # interrupt state
        return self.setEXTProperty('%s.pendingInterrupt'%(ADDON_ID),state)


    def isPendingInterrupt(self):  # interrupt state
        return self.getEXTProperty('%s.pendingInterrupt'%(ADDON_ID),False)

        
    @contextmanager
    def suspendActivity(self, wait=-1): #pause background task.
        while not self.monitor.abortRequested() and (self.isSuspendActivity() or self.isLockActivity()):
            if wait > 0: wait -= CPU_CYCLE #wait -1 runs indefinitely. 
            if self.monitor.waitForAbort(CPU_CYCLE) or int(wait) == 0: break
        self.setPendingSuspend(self.setSuspendActivity(True))
        try: yield
        finally: self.setPendingSuspend(self.setSuspendActivity(False))


    def setSuspendActivity(self, state=True): # context state
        return self.setProperty('%s.suspendActivity'%(ADDON_ID),state)


    def isSuspendActivity(self): # context state
        return self.getProperty('%s.suspendActivity'%(ADDON_ID),False)
        
        
    def setPendingSuspend(self, state=True): # suspend state
        return self.setEXTProperty('%s.pendingSuspend'%(ADDON_ID),state)
        
        
    def isPendingSuspend(self): # suspend state
        return self.getEXTProperty('%s.pendingSuspend'%(ADDON_ID),False)


    @contextmanager
    def legacy(self): #toggle legacy property from older pseudotv project that may still be used by third-party plugins.
        try: 
            if not self.isPseudoTVRunning():
                self.setEXTProperty('PseudoTVRunning',True)
                yield True
            else:
                yield False
        finally: 
            self.setEXTProperty('PseudoTVRunning',False)


    def isPseudoTVRunning(self):
        return self.getEXTProperty('PseudoTVRunning',False)


    def getFriendlyName(self):
        friendly = self.getEXTProperty('%s.Instance_Name'%(ADDON_ID))
        if not friendly or friendly == LANGUAGE(32105):
            from jsonrpc import JSONRPC
            friendly = self.setEXTProperty('%s.Instance_Name'%(ADDON_ID), JSONRPC().inputFriendlyName())
        return friendly
        
        
    def preemptActivity(self, msg, func, *args, **kwargs):
        results      = None
        orgSuspend   = self.isPendingSuspend()
        orgInterrupt = self.isPendingInterrupt()
        while not self.monitor.abortRequested():
            isSuspend   = self.isPendingSuspend()
            isInterrupt = self.isPendingInterrupt()
            isBuilding  = self.isRunning('Builder.buildChannels')
            
            Dialog().notificationDialog(msg)
            self.log('preemptActivity, isInterrupt = %s, isSuspend = %s, isBuilding = %s'%(isInterrupt,isSuspend,isBuilding))
            if not isInterrupt and any([isSuspend, isBuilding]): #force interrupt.
                if isSuspend:  self.setPendingSuspend(False)   #release suspension 
                if isBuilding: self.setPendingInterrupt(True)  #interrupt building.
            elif isInterrupt and not isBuilding: self.setPendingInterrupt(False)#release interrupt.
            elif not isInterrupt and not any([isSuspend, isBuilding]):
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
    def __init__(self, service):
        self.pool       = service.pool
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.cache
        self.monitor    = service.monitor
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def getListItem(self, label='', label2='', path='', offscreen=False):
        return xbmcgui.ListItem(label,label2,path,offscreen)


    def infoTagVideo(self, offscreen=False):
        return xbmc.InfoTagVideo(offscreen)


    def InfoTagMusic(self, offscreen=False):
        return xbmc.InfoTagVideo(offscreen)


    def buildDictListItem(self, listitem):
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
                
        
        # item['fitem'] = Globals._decodePlot(item.get('Plot'))
        return item


    def buildItemListItem(self, item, media='video', offscreen=False, playable=True):
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
                art['poster'] = _getGlobals()._getThumb(info,opt=1)
                art['fanart'] = _getGlobals()._getThumb(info)
                
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
        except Exception as e: log("buildItemListItem, failed! %s\n%s"%(e,item), xbmc.LOGERROR)
            
                     
    def buildMenuListItem(self, label="", label2="", icon=ICON, url="", info={}, art={}, props={}, offscreen=False, media='video'):
        if not art: art = {'thumb':icon,'logo':icon,'icon':icon}
        listitem = self.getListItem(label, label2, url, offscreen=offscreen)
        listitem.setIsFolder(True)
        listitem.setPath(url)
        listitem.setArt(art)
        if info:
            infoTag = ListItemInfoTag(listitem, media)
            infoTag.set_info(self.cleanInfo(info,media))
        [listitem.setProperty(key, self.cleanProp(pvalue)) for key, pvalue in list(props.items())]
        return listitem
               
           
    def cleanInfo(self, ninfo, media='video', properties={}):
        LISTITEM_TYPES = MUSIC_LISTITEM_TYPES if media == 'music' else VIDEO_LISTITEM_TYPES  
        tmpInfo = ninfo.copy()
        for key, value in list(tmpInfo.items()):
            types = LISTITEM_TYPES.get(key,None)
            if not types:# key not in json enum schema, add to customproperties
                ninfo.pop(key)
                properties[key] = value
                continue
                
            elif not isinstance(value,types):# convert to schema type
                for type in types:
                    try:   ninfo[key] = type(value)
                    except Exception as e: self.log("cleanInfo failed! %s\nkey = %s, value = %s, type = %s\n%s"%(e,key,value,type,ninfo), xbmc.LOGWARNING)
                     
            if isinstance(ninfo[key],list):
                for n in ninfo[key]:
                    if isinstance(n,dict): n, properties = self.cleanInfo(n,media,properties)
            if isinstance(ninfo[key],dict): ninfo[key], properties = self.cleanInfo(ninfo[key],media,properties)
        return ninfo, properties


    def cleanProp(self, pvalue):
        if       isinstance(pvalue,dict): return FileAccess.dumpJSON(pvalue)
        elif     isinstance(pvalue,list): return '|'.join(map(str, pvalue))
        elif not isinstance(pvalue,str):  return str(pvalue)
        else:                             return pvalue
            
    
class Builtin(object):
    dialog = None
    def __init__(self, service):
        self.lock       = Lock()
        self.busy       = None
        self.pool       = service.pool
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.cache
        self.monitor    = service.monitor
    
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def hasPVR(self):
        return self.getInfoBool('Pvr.HasTVChannels')
        
        
    def hasRadio(self):
        return self.getInfoBool('Pvr.HasRadioChannels')


    def hasMusic(self):
        return self.getInfoBool('Library.HasContent(Music)')
        
        
    def hasTV(self):
        return self.getInfoBool('Library.HasContent(TVShows)')
        
        
    def hasMovie(self):
        return self.getInfoBool('Library.HasContent(Movies)')
                

    def hasMedia(self) -> bool:
        return self.getInfoBool('Player.hasMedia')


    def hasGame(self) -> bool:
        return self.getInfoBool('Player.HasGame')


    def hasDuration(self) -> bool:
        return self.getInfoBool('Player.HasDuration')


    def hasEPG(self) -> bool:
        return self.getInfoBool('VideoPlayer.HasEpg','')

  
    def hasSubtitle(self):
        return self.getInfoBool('VideoPlayer.HasSubtitles')


    def isSubtitle(self):
        return self.getInfoBool('VideoPlayer.SubtitlesEnabled')


    def isPlaylistRandom(self):
        return self.getInfoLabel('Playlist.Random').lower() == 'on' # Disable auto playlist shuffling if it's on
        
        
    def isPlaylistRepeat(self):
        return self.getInfoLabel('Playlist.IsRepeat').lower() == 'true' # Disable auto playlist repeat if it's on #todo


    def isPaused(self):
        return self.getInfoBool('Player.Paused')
                
                
    def isRecording(self):
        return self.getInfoBool('Pvr.IsRecording')
        
        
    def isScanning(self):
        return (self.getInfoBool('Library.IsScanningVideo') & self.getInfoBool('Library.IsScanningMusic'))
          
                      
    def isSettingsOpened(self) -> bool:
        return any([self.getInfoBool('Window.IsVisible(addonsettings)'),self.getInfoBool('Window.IsVisible(selectdialog)')])


    def isPlaying(self):
        return self.getInfoBool('Player.Playing')


    def isPVRPlaying(self) -> bool:
        return any([self.getInfoBool('Pvr.IsPlayingTv'),self.getInfoBool('Pvr.IsPlayingRadio'),self.getInfoBool('Pvr.IsPlayingRecording'),self.getInfoBool('Pvr.IsPlayingActiveRecording')])


    def isBusyDialog(self):
        return any([self.dialog.properties.isRunning('BUSY_OVERLAY'),self.getInfoBool('Window.IsActive(busydialognocancel)'),self.getInfoBool('Window.IsActive(busydialog)')])


    def closeBusyDialog(self):
        if hasattr(self.busy, 'close'):
            self.busy = self.busy.close()
        elif self.getInfoBool('Window.IsActive(busydialognocancel)'):
            self.executebuiltin('Dialog.Close(busydialognocancel)')
        elif self.getInfoBool('Window.IsActive(busydialog)'):
            self.executebuiltin('Dialog.Close(busydialog)')


    @contextmanager
    def busy_dialog(self, cancel=False, lock=False):
        if not self.isBusyDialog() and not cancel:
            try: 
                if self.busy is None:
                    from overlay import Busy 
                    try:               self.busy = Busy(BUSY_XML, ADDON_PATH, "default", isLocked=lock)
                    except Exception:  self.busy = None
                    finally: self.busy.show()
                elif cancel and hasattr(self.busy, 'close'):
                    self.busy = self.busy.close()
                yield
            finally:
                if hasattr(self.busy, 'close'):
                    self.busy = self.busy.close()
        else: yield


    def getIdle(self):
        with self.lock:
            try:              return int(xbmc.getGlobalIdleTime() or '0')
            except Exception: return 0
            

    def getInfoLabel(self, key, default=''):
        with self.lock:
            value   = None
            pattern = r"^[a-zA-Z0-9]+\.[a-zA-Z0-9]+(?:\(.*\))?$"
            if re.match(pattern, key):
                value = xbmc.getInfoLabel(key)
                if value == "Busy": 
                    if not self.monitor.waitForAbort(0.5): return self.getInfoLabel(key,default)
                self.log('getInfoLabel, key = %s, value = %s'%(key,value))
            else: self.log('getInfoLabel failed!, key = %s'%(key))
            return (value or default)


    def getInfoBool(self, key):
        with self.lock:
            value   = False
            pattern = r"^[a-zA-Z0-9]+\.[a-zA-Z0-9]+(?:\(.*\))?$"
            if re.match(pattern, key):
                value = xbmc.getCondVisibility(key)
                self.log('getInfoBool, key = %s, value = %s'%(key,value))
            else: self.log('getInfoBool failed!, key = %s'%(key))
            return value or False
        
        
    def executewindow(self, key, wait=False, delay=False, condition=None):
        with self.lock:
            return self.executebuiltin(key,wait,delay,condition)
        
        
    def executebuiltin(self, key, wait=False, delay=None, condition=None):
        if not condition is None and not condition(): return False
        with self.lock:
            self.log('executebuiltin, key = %s, wait = %s, delay = %s, condition = %s):'%(key,wait,delay,condition))
            if delay is None: return xbmc.executebuiltin('%s'%(key),wait)
            return timerit(xbmc.executebuiltin)(delay,*(key,wait,None,condition))
        
        
    def executescript(self, path, condition=None):
        if not condition is None and not condition(): return False
        with self.lock:
            self.log('executescript, path = %s'%(path))
            xbmc.executescript('%s'%(path))
            return True


    def executeJSONRPC(self, request):
        with self.lock:
            response = xbmc.executeJSONRPC(FileAccess.dumpJSON(request))
            self.log('executeJSONRPC\nrequest = %s'%(request))
            self.monitor.waitForAbort(float(REAL_SETTINGS.getSetting('API_Delay')))
            return response
    

    def getResolution(self):
        WH, WIN = self.getInfoLabel('System.ScreenResolution').split(' - ')
        return (1920,1080), WIN #tuple(int(x) for x in WH.split('x')), WIN



class Dialog(object):
    dialog = xbmcgui.Dialog()
    dialog_lock = Lock()
    
    def __init__(self):
        from _services import Service
        self.service    = Service()
        self.pool       = self.service.pool
        self.jsonRPC    = self.service.jsonRPC
        self.cache      = self.service.cache
        self.monitor    = self.service.monitor
        self.settings   = Settings(self.service)
        self.properties = Properties(self.service)
        self.listitems  = ListItems(self.service)
        self.builtin    = Builtin(self.service)

        self.settings.dialog   = self
        self.properties.dialog = self
        self.listitems.dialog  = self
        self.builtin.dialog    = self
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def toggleInfoMonitor(self, state=False, wait=0.5):
        self.log('toggleInfoMonitor, state = %s'%(state))
        self.properties.setRunning('Kodi.toggleInfoMonitor',state)
        if state: timerit(self.doInfoMonitor)(0.1)
            

    def doInfoMonitor(self):
        self.properties.clrEXTProperty('%s.montiorList'%(ADDON_ID))
        while not self.monitor.abortRequested() and self.properties.isRunning('Kodi.toggleInfoMonitor'):
            if self.monitor.waitForAbort(float(self.SETTINGS.getSetting('API_Delay'))): break
            self.fillInfoMonitor()
                    

    def fillInfoMonitor(self, type='ListItem'):
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


    def getInfoMonitor(self):
        return self.properties.getEXTProperty('%s.montiorList'%(ADDON_ID),{}).get('info',[])
    
    
    def setInfoMonitor(self, items):
        return self.properties.setEXTProperty('%s.montiorList'%(ADDON_ID),{'info':list(_getGlobals()._setDictLST(items))})


    def colorDialog(self, colorlist=[], preselect="", colorfile="", heading=ADDON_NAME):
        return self.dialog.colorpicker(heading, preselect, colorfile, colorlist)
    
    
    def _closeOkDialog(self):
        if self.builtin.getInfoBool('Window.IsActive(okdialog)'):
            self.builtin.executebuiltin('Dialog.Close(okdialog)')
        
        
    def _okDialog(self, msg, heading, autoclose):
        return timerit(self.okDialog)(0.1,*(msg, heading, autoclose))


    def okDialog(self, msg, heading=ADDON_NAME, autoclose=AUTOCLOSE_DELAY, usethread=False):
        if usethread: return self._okDialog(msg, heading, autoclose)
        else:
            if autoclose > 0: timerit(self._closeOkDialog)(autoclose)
            return self.dialog.ok(heading, msg)
            
            
    def qrDialog(self, url, msg, heading='%s - %s'%(ADDON_NAME,LANGUAGE(30158)), autoclose=AUTOCLOSE_DELAY):
        class QRCode(xbmcgui.WindowXMLDialog):
            def __init__(self, *args, **kwargs):
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

            def onClick(self, controlId):
                if controlId == 40003:
                    self.onClose()

            def onClose(self):
                if self.acThread.is_alive():
                    if hasattr(self.acThread, 'cancel'): self.acThread.cancel()
                    try: self.acThread.join()
                    except Exception: pass
                self.close()

        if not self.properties.isRunning('Dialog.qrDialog'):
            with self.properties.chkRunning('Dialog.qrDialog'):
                with self.builtin.busy_dialog():
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
            def __init__(self, *args, **kwargs):
                self.head = kwargs.get('head','')
                self.text = kwargs.get('text','')
                self.doModal()
            
            def onInit(self):
                self.getControl(1).setLabel(self.head)
                self.textbox = self.getControl(5)

            def onClick(self, control_id): pass
            
            def onFocus(self, control_id): pass
            
            def onAction(self, action):
                if action in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK]: self.close()

            def _updateText(self, txt):
                try:
                    self.textbox.setText(txt)
                    self.builtin.executebuiltin('SetFocus(3000)')
                    self.builtin.executebuiltin('AlarmClock(down,Action(down),.5,true,false)')
                except Exception: pass
                
        return TEXTVIEW("DialogTextViewer.xml", os.getcwd(), "Default")


    def _textViewer(self, msg, heading, usemono, autoclose):
        return timerit(self.textviewer)(0.1,*(msg, heading, usemono, autoclose))
        
        
    def textviewer(self, msg, heading=ADDON_NAME, usemono=False, autoclose=AUTOCLOSE_DELAY, usethread=False, custom=False):
        # if custom: return self._customTextViewer(msg,heading,autoclose)
        if usethread: return self._textViewer(msg, heading, usemono, autoclose)
        else:
            if autoclose > 0: timerit(self._closeTextViewer)(autoclose)
            self.dialog.textviewer(heading, msg, usemono)
            return True
            
        
    def yesnoDialog(self, message, heading=ADDON_NAME, nolabel='', yeslabel='', customlabel='', autoclose=AUTOCLOSE_DELAY): 
        if customlabel:
            # Returns the integer value for the selected button (-1:cancelled, 0:no, 1:yes, 2:custom)
            return self.dialog.yesnocustom(heading, message, customlabel, nolabel, yeslabel, (autoclose*1000))
        else: 
            # Returns True if 'Yes' was pressed, else False.
            return self.dialog.yesno(heading, message, nolabel, yeslabel, (autoclose*1000))


    def _notificationWait(self, message, header, wait):
        return timerit(self.notificationWait)(0.1,*(message, header, wait))


    def notificationWait(self, message, header=ADDON_NAME, wait=4, silent=None, usethread=False):
        if silent is None: silent = not self.settings.showDialog(silent)
        if usethread: return self._notificationWait(message, header, wait)
        else:
            with self._progressDialog(message, header, silent) as pDialog:
                for idx in range(int(wait)):
                    pDialog = self._updateProgress(pDialog,int(idx*100//wait))
                    if pDialog is None or self.monitor.waitForAbort(1.0): break
                if hasattr(pDialog, 'close'): pDialog.close()
        return True
        

    @contextmanager
    def _progressDialog(self, message='', header=ADDON_NAME, silent=None, background=True):
        if silent is None: silent = not self.settings.showDialog(silent)
        dlg = None
        with self.dialog_lock:
            if not silent and not self.properties.isRunning('_progressDialog'):
                self.properties.setRunning('_progressDialog', True) 
                if background: dlg = xbmcgui.DialogProgressBG()
                else:          dlg = xbmcgui.DialogProgress()
                try:
                    dlg.create(header, message)
                    self.log(f'_progressDialog [0% - {dlg}] silent = {silent}\nheader = {header}\nmessage = {message}')
                except Exception as e:
                    self.log(f'_progressDialog, failed! to create dialog: {e}')
                    self.properties.setRunning('_progressDialog', False)
                    dlg = None
        try:
            if dlg is not None: yield dlg
            else:               yield True
        finally:
            if dlg is not None:
                with self.dialog_lock:
                    try:
                        dlg.close()
                        self.log(f'_progressDialog [100% - {dlg}] silent = {silent}\nheader = {header}\nmessage = {message}')
                    except Exception: pass
                    finally: self.properties.setRunning('_progressDialog', False)


    def _updateProgress(self, dlg=None, percent=1, message='', header=ADDON_NAME):
        if dlg is None or isinstance(dlg, bool): return dlg
        try:
            if isinstance(dlg, xbmcgui.DialogProgressBG):
                if dlg.isFinished(): return None
                elif hasattr(dlg, 'update'):
                    self.log(f'_updateProgress [{percent}% - {dlg}]\nheader = {header}\nmessage = {message}')
                    dlg.update(percent, header, message)
                    
            elif isinstance(dlg, xbmcgui.DialogProgress):
                if dlg.iscanceled(): return None
                elif hasattr(dlg, 'update'):
                    try:
                        match = re.compile(r'(.*?): (.*?)\%', re.IGNORECASE).search(message)
                        if match:
                            message = '%s: %s' % (header.replace('%s, ' % (ADDON_NAME), ''), match.group(1))
                            percent = int(match.group(2))
                    except Exception: pass
                    self.log(f'_updateProgress [{percent}% - {dlg}]\nheader = {header}\nmessage = {message}')
                    dlg.update(percent, message)
        except Exception as e:
            self.log(f'_updateProgress, failed! Thread error during progress update: {e}')
            return None
        return dlg
        
        
    def progressDialog(self, percent=0, control=None, message='', header=ADDON_NAME):
        if control is None and int(percent) == 0:
            with self.dialog_lock:
                control = xbmcgui.DialogProgress()
                control.create(header, message)  
        elif control:
            try:
                if int(percent) == 100 or control.iscanceled(): 
                    with self.dialog_lock:
                        control.close()
                        return None
                elif hasattr(control, 'update'): 
                    control.update(int(percent), message)
            except Exception:
                return None
        return control
        
        
    def progressBGDialog(self, percent=0, control=None, message='', header=ADDON_NAME):
        if control is None and int(percent) == 0:
            with self.dialog_lock:
                control = xbmcgui.DialogProgressBG()
                control.create(header, message)
        elif control:
            try:
                if int(percent) == 100 or control.isFinished(): 
                    with self.dialog_lock:
                        control.close()
                        return None
                elif hasattr(control, 'update'): 
                    control.update(int(percent), header, message)
            except Exception:
                return None
        return control

                
    def infoDialog(self, listitem):
        self.dialog.info(listitem)
        
    
    def _notificationDialog(self, message, header, sound, time, icon, silent):
        threadit(self.notificationDialog)(message, header, sound, time, icon, silent)


    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=PROMPT_DELAY, icon=LOGO_COLOR, silent=None, usethread=False):
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
        
             
    def customSelect(self, items, header, preselect, useDetails, autoclose, multi): #todo
        class DialogSelect(xbmcgui.WindowXMLDialog):
            def __init__(self, *args, **kwargs):
                xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

            def onInit(self):
                log("DialogSelect: onInit")
                #todo get list control, convert items to listitems, additems to list control.
               
            def onAction(self, act):
                actionId = act.getId()
                log('DialogSelect: onAction: actionId = %s'%(actionId))
                if actionId in ACTION_PREVIOUS_MENU: self.close()
                else: pass
                
        if not self.properties.isRunning('SELECT_OVERLAY'):
            dialogSelect = DialogSelect(DIALOG_SELECT, ADDON_PATH, "default")
            dialogSelect.doModal()
            del dialogSelect
        

    def selectDialog(self, items, header=ADDON_NAME, preselect=None, useDetails=True, autoclose=SELECT_DELAY, multi=True, custom=False):
        self.log('selectDialog, items = %s, header = %s, preselect = %s, useDetails = %s, autoclose = %s, multi = %s, custom = %s'%(len(items),header,preselect,useDetails,autoclose,multi,custom))
        if custom: return self.customSelect(items, header, preselect, useDetails, autoclose, multi)
        elif multi == True:
            if not preselect: preselect = [-1]
            with self.dialog_lock:
                select = self.dialog.multiselect(header, items, (autoclose*1000), preselect, useDetails)
            if select == [-1]: return
        else:
            if not preselect: preselect = -1
            elif isinstance(preselect,list) and len(preselect) > 0: preselect = preselect[0]
            with self.dialog_lock:
                select = self.dialog.select(header, items, (autoclose*1000), preselect, useDetails)
            if select == -1: return
        return select
      
      
    def inputDialog(self, message, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
        ## - key: xbmcgui.INPUT_ALPHANUM (standard keyboard)
        ## - key: xbmcgui.INPUT_NUMERIC (format: #)
        ## - key: xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
        ## - key: xbmcgui.INPUT_TIME (format: HH:MM)
        ## - key: xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
        ## - key: xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
        ## - opt: xbmcgui.PASSWORD_VERIFY (verifies an existing (default) md5 hashed password)
        ## - opt: xbmcgui.ALPHANUM_HIDE_INPUT (masks input)
        with self.dialog_lock:
            return self.dialog.input(message, default, key, opt, close)
        

    def importSTRM(self, strm):
        try:
            with self.builtin.busy_dialog():
                fle   = FileAccess.open(strm,'r')
                lines = fle.readlines()
                fle.close()
                paths = [line for line in lines if not line.startswith('#') and '://' in line]
                if len(paths) == 0: return self.notificationDialog(LANGUAGE(32018)%(LANGUAGE(30047)))
            select = self.selectDialog(paths, LANGUAGE(32080), useDetails=False, multi=False)
            self.log("importSTRM, strm = %s paths = %s"%(strm,paths))
            if not select is None: return paths[select]
        except Exception as e: self.log("importSTRM, failed! %s\n%s"%(e,strm), xbmc.LOGERROR)
             
               
    def _resourcePath(self, id=[], content='videos', ftype=''):
        if not id: id = self.browseResources(id, content, ftype, multi=False)
        path = 'special://home/addons/%s/resources/'%(id)
        self.log("_resourcePath [%s], content = %s, ftype = %s, path = %s"%(id, content, ftype,path))
        return path
        

    def browseResources(self, ids=[], content='videos', ftype='', multi=True):
        #todo when no resources avail take user to Image Collections repo.
        self.log("browseResources, ids = %s, content = %s, ftype = %s, multi = %s"%(ids, content, ftype, multi))
        #todo selectDialog content and ftype.
        def __buildMenuItem(resource):
            return self.listitems.buildMenuListItem(resource['name'],resource['description'],resource['thumbnail'],url=resource['addonid'])
             
        def __getResources():
            return jsonRPC.getAddons({"enabled":True})
        
        from jsonrpc import JSONRPC
        lizLST  = []
        jsonRPC = JSONRPC()
        with self.builtin.busy_dialog():
            lizLST.extend(poolit(__buildMenuItem)([result for result in __getResources() if result.get('addonid').startswith('resource.%s.%s'%(content,ftype))]))
            del jsonRPC
            
        selects = self.selectDialog(lizLST, 'Select one or more resources', preselect=_getGlobals()._findItemsInLST(lizLST,ids,'getPath'), multi=multi)
        if selects is None:                return
        elif not isinstance(selects,list): return lizLST[selects].getPath()
        else:                              return [lizLST[select].getPath() for select in selects]


    def browseSources(self, type=0, heading=ADDON_NAME, default='', shares='', mask='', useThumbs=True, treatAsFolder=False, multi=False, monitor=False, include=[], exclude=[]):
        self.log('browseSources, type = %s, heading= %s, shares= %s, useThumbs= %s, treatAsFolder= %s, default= %s, mask= %s, include= %s, exclude= %s'%(type,heading,shares,useThumbs,treatAsFolder,default,mask,len(include),exclude))
        def __buildMenuItem(option):
            return self.listitems.buildMenuListItem(option['label'],option['label2'],_getGlobals()._getDummyIcon(str(option['idx'])))

        with self.builtin.busy_dialog():
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
            options = _getGlobals()._setDictLST(options)
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
        idx     = options[select]['idx']
        if type == 0:
            if   "resource." in default or options[select]["idx"] == 22: return self._resourcePath(default, {xbmc.getSupportedMedia('video'):'videos',xbmc.getSupportedMedia('picture'):'images'}.get(mask,xbmc.getSupportedMedia('video')))
        elif type == 1:
            if   "?xsp="     in default or options[select]["idx"] == 15: return self.buildDXSP(default)
            elif ".strm"     in default or options[select]["idx"] == 16: return self.importSTRM(default)
            elif "resource." in default or options[select]["idx"] == 22: default = self._resourcePath(default, {xbmc.getSupportedMedia('video'):'videos',xbmc.getSupportedMedia('picture'):'images'}.get(mask,xbmc.getSupportedMedia('video')))
        return self.browseDialog(type, heading, default, shares, mask, useThumbs, treatAsFolder, multi, monitor)
            
    
    def browseDialog(self, type=0, heading=ADDON_NAME, default='', shares='', mask='', useThumbs=True, treatAsFolder=False, multi=False, monitor=False):
        self.log('browseDialog, type = %s, heading= %s, shares= %s, useThumbs= %s, treatAsFolder= %s, default= %s\nmask= %s'%(type,heading,shares,useThumbs,treatAsFolder,default,mask))
        # https://xbmc.github.io/docs.kodi.tv/master/kodi-base/d6/de8/group__python___dialog.html#ga856f475ecd92b1afa37357deabe4b9e4
        # https://xbmc.github.io/docs.kodi.tv/master/kodi-base/d6/de8/group__python___dialog.html#gafa1e339e5a98ae4ea4e3d3bb3e1d028c
        self.toggleInfoMonitor(monitor)
        with self.dialog_lock:
            if multi == True and type > 0:  retval = self.dialog.browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)
            else:                           retval = self.dialog.browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        self.toggleInfoMonitor(False)
        if not retval is None and retval != default:
            return retval
        

    def multiBrowse(self, paths: list=[], header=ADDON_NAME, exclude=[], monitor=True):
        self.log('multiBrowse, IN paths = %s'%(paths))
        def __buildListItem(item): #label: str="", label2: str="", icon: str=LOGO_COLOR, paths: list=[], items: dict={}
            idx = pathLST.index(item)
            return self.listitems.buildMenuListItem('%s|'%(idx+1), item, _getGlobals()._getDummyIcon(str(idx+1)), url='|'.join(item), props={'idx':idx+1})

        select  = -1
        epaths  = paths.copy()
        pathLST = list([_f for _f in paths if _f])
        lastOPT = None
        while not self.monitor.abortRequested() and not select is None:
            with self.builtin.busy_dialog():
                npath  = None
                lizLST = poolit(__buildListItem)(pathLST)
                lizLST.insert(0,__buildListItem('',LANGUAGE(33113),icon=ICON,items={'key':'add','idx':0}))
                if len(pathLST) > 0 and epaths != pathLST: lizLST.insert(1,__buildListItem('[B]%s[/B]'%(LANGUAGE(32059)),LANGUAGE(33114),icon=ICON,items={'key':'save'}))
            
            select = self.selectDialog(lizLST, header, preselect=lastOPT, multi=False)
            if not select is None:
                key, path = lizLST[select].getProperty('key'), lizLST[select].getPath()
                try:    lastOPT = int(lizLST[select].getProperty('idx'))
                except Exception: lastOPT = -1
                if key == 'add': 
                    with self.builtin.busy_dialog():
                        npath = self.browseSources(heading=LANGUAGE(32080), exclude=exclude, monitor=monitor)
                        if npath: pathLST.append(npath)
                elif key == 'save': 
                    paths = pathLST
                    break
                elif path in pathLST:
                    retval = self.yesnoDialog(LANGUAGE(32102), customlabel=LANGUAGE(32103))
                    if retval in [1,2]: pathLST.pop(pathLST.index(path))
                    if retval == 2:
                        with self.builtin.busy_dialog():
                            npath = self.browseSources(heading=LANGUAGE(32080), default=path, monitor=monitor, exclude=exclude)
                            pathLST.append(npath)
        self.log('multiBrowse, OUT paths = %s'%(paths))
        return paths
           
           
    def buildDXSP(self, path=''):
        # https://github.com/xbmc/xbmc/blob/master/xbmc/playlists/SmartPlayList.cpp
        
        def __mtype(params={"type":"","rules":{"and":[],"or":[]},"order":{"direction":"ascending","method":"random","ignorearticle":True,"useartistsortname":True}}):
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
            
        def __andor(params={}):
            enumLST = list(sorted(['and', 'or']))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Conjunction",preselect=(enumLST.index(list(params.get('rules',{}).keys())) if params.get('rules',{}) else -1),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]
                  
        def __order(params={}):
            enums   = jsonRPC.getEnums("List.Sort",type="order") 
            enumLST = list(sorted([_f for _f in enums if _f]))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select order",preselect=enumLST.index(params.get('order',{}).get('direction','ascending')),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]
            
        def __method(params={}):
            enums   = jsonRPC.getEnums("List.Sort",type="method") 
            enumLST = list(sorted([_f for _f in enums if _f]))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select method",preselect=enumLST.index(params.get('order',{}).get('method','random')),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]
            
        def __field(params={}, rule={}):
            if   params.get('type') == 'songs':       enums = jsonRPC.getEnums("List.Filter.Fields.Songs"   , type='items')
            elif params.get('type') == 'albums':      enums = jsonRPC.getEnums("List.Filter.Fields.Albums"  , type='items')
            elif params.get('type') == 'artists':     enums = jsonRPC.getEnums("List.Filter.Fields.Artists" , type='items')
            elif params.get('type') == 'tvshows':     enums = jsonRPC.getEnums("List.Filter.Fields.TVShows" , type='items')
            elif params.get('type') == 'episodes':    enums = jsonRPC.getEnums("List.Filter.Fields.Episodes", type='items')
            elif params.get('type') == 'movies':      enums = jsonRPC.getEnums("List.Filter.Fields.Movies"  , type='items')
            elif params.get('type') == 'musicvideos': enums = jsonRPC.getEnums("List.Filter.Fields.MusicVideos")
            else: return
            enumLST = list(sorted([_f for _f in enums if _f]))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Filter",preselect=(enumLST.index(rule.get('field')) if rule.get('field') else -1),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]

        def __operator(params={}, rule={}):
            enumLST = sorted(jsonRPC.getEnums("List.Filter.Operators"))
            if rule.get("field") != 'date':
                if 'inthelast'    in enumLST: enumLST.remove('inthelast')
                if 'notinthelast' in enumLST: enumLST.remove('notinthelast')
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Operator",preselect=(enumLST.index(rule.get('operator')) if rule.get('operator') else -1),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]

        def __value(params={}, rule={}):
            return self.getValue(params, rule)
            
        def __getRule(params={}, rule={"field":"","operator":"","value":[]}):
            enumSEL = -1
            while not self.monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value),icon=_getGlobals()._getDummyIcon(_getGlobals()._getAbbr(key.title())),props={'key':key,'value':value}) for key, value in list(rule.items())]
                enumSEL = self.selectDialog(enumLST,header="Select method",preselect=-1, multi=False)
                if not enumSEL is None: rule.update({enumLST[enumSEL].getProperty('key'):({"field":field,"operator":operator,"value":value}[enumLST[enumSEL].getProperty('key')])(params,rule)})
            return rule
            
        def __getRules(params={}):
            enumSEL = -1
            eparams = params.copy()
            while not self.monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),FileAccess.dumpJSON(params.get('rules',{}).get(key,[])),icon=_getGlobals()._getDummyIcon(_getGlobals()._getAbbr(key.title())),props={'key':key}) for key in ["and","or"]]
                enumSEL = self.selectDialog(enumLST,header="Edit Rules",multi=False)
                if not enumSEL is None:
                    if enumLST[enumSEL].getLabel() in ['And','Or']:
                        CONSEL  = -1
                        CONLKEY = enumLST[enumSEL].getProperty('key')
                        ruleLST = params.get('rules',{}).get(CONLKEY,[])
                        while not self.monitor.abortRequested() and not CONSEL is None:
                            andLST = [self.listitems.buildMenuListItem('%s|'%(idx+1),FileAccess.dumpJSON(value),icon=_getGlobals()._getDummyIcon(str(idx+1)),props={'idx':str(idx)}) for idx, value in enumerate(ruleLST)]
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

        def __getOrder(params={}):
            enumSEL = -1
            while not self.monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value).title(),icon=_getGlobals()._getDummyIcon(_getGlobals()._getAbbr(key.title()))) for key, value in list(params.get('order',{}).items())]
                enumLST.insert(0,self.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32174)),"",icon=ICON,props={'key':'save'}))
                enumSEL = self.selectDialog(enumLST,header="Edit Selection",preselect=-1,multi=False)
                if not enumSEL is None:
                    if   enumLST[enumSEL].getLabel() == 'Direction': params['order'].update({'direction':__order(params)})
                    elif enumLST[enumSEL].getLabel() == 'Method':    params['order'].update({'method':__method(params)})
                    elif enumLST[enumSEL].getProperty('key') == 'save': break
                    else: params['order'].update({enumLST[enumSEL].getLabel().lower(): not enumLST[enumSEL].getLabel2() == 'True'})
            return params

        from jsonrpc import JSONRPC
        jsonRPC = JSONRPC()
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
        del jsonRPC
        
        if len(params.get('rules',{}).get('and',[]) or params.get('rules',{}).get('and',[])) > 0:
            url = '%s?xsp=%s'%(path,FileAccess.dumpJSON(params))
            self.log('buildDXSP, returning %s'%(url))
            return url


    def getValue(self, params={}, rule={}):
        # etype  = params.get("type")
        # efield = str(rule.get("field")).lower()
        # evalue = ','.join([Globals._unquoteString(value) for value in rule.get('value',[])])
        # LIST_SORT_ACTIONS = {"none"           : (),
                             # "label"          : (self.inputDialog,{message='Enter %s Value (Separate multiple values by ',' ex. Action,Comedy)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_ALPHANUM}),
                             # "albumtype"      : (self.inputDialog,{message='Enter %s Value (Separate multiple values by ',' ex. Action,Comedy)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_ALPHANUM}),
                             # "country"        : (self.inputDialog,{message='Enter %s Value (Separate multiple values by ',' ex. Action,Comedy)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_ALPHANUM}),
                             # "originaltitle"  : (self.inputDialog,{message='Enter %s Value (Separate multiple values by ',' ex. Action,Comedy)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_ALPHANUM}),
                             # "productioncode" : (self.inputDialog,{message='Enter %s Value (Separate multiple values by ',' ex. Action,Comedy)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_ALPHANUM}),
                             # "mpaa"           : (self.inputDialog,{message='Enter %s Value (Separate multiple values by ',' ex. Action,Comedy)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_ALPHANUM}),
                             # "votes"          : (self.inputDialog,{message='Enter %s Value (Separate multiple values by ',' ex. Action,Comedy)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_ALPHANUM}),
                             # "sorttitle"      : (self.inputDialog,{message='Enter %s Value (Separate multiple values by ',' ex. Action,Comedy)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_ALPHANUM}),
                             # "time"           : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_TIME}),
                             # "date"           : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_DATE})
                             # "originaldate"   : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_DATE}),
                             # "dateadded"      : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_DATE}),
                             # "lastplayed"     : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "listeners"      : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "size"           : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "track"          : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "programcount"   : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "totalepisodes"  : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "watchedepisodes": (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "episode"        : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "season"         : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "playcount"      : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "year"           : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "rating"         : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "userrating"     : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "bpm"            : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "totaldiscs"     : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "bitrate"        : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "top250"         : (self.inputDialog,{message='Enter %s Value (Format ex. ####)'%(efield.title()),default=evalue,key=xbmcgui.INPUT_NUMERIC}),
                             # "file"           : (self.browseDialog,{type=1,heading="",default=rule.get('value',[]),multi=True}),
                             # "path"           : (self.browseDialog,{type=0,heading="",default=rule.get('value',[]),multi=True}),
                             # "drivetype"      : (self.browseDialog,{type=0,heading="",default=rule.get('value',[]),multi=True}),
                             # "random"         : (),
                             # "tvshowstatus"   : (),
                             # "playlist"       : (),
                             # "genre"          : (self.selectDialog,({list=jsonRPC.getVideoGenres,jsonRPC.getMusicGenres)),
                             # "tvshowtitle"    : (self.selectDialog,(jsonRPC.getTVshows,)),
                             # "title"          : (self.selectDialog,(jsonRPC.getMovies)),
                             # "artist"         : (self.selectDialog,jsonRPC.getArtists),
                             # "album"          : (self.selectDialog,jsonRPC.getAlbums),
                             # "studio"         : (self.selectDialog,(jsonRPC.getMovieStudios,jsonRPC.getNetworks))}

        def __getInput():  return self.inputDialog("Enter Value\nSeparate by ',' ex. Action,Comedy",','.join([_getGlobals()._unquoteString(value) for value in rule.get('value',[])]))
        def __getBrowse(): return self.browseSources(default='|'.join([_getGlobals()._unquoteString(value) for value in rule.get('value',[])]))
        def __getSelect(): return self.notificationDialog(LANGUAGE(32020))
        enumLST = sorted(['Enter', 'Browse', 'Select'])
        enumKEY = {'Enter':{'func':__getInput},'Browse':{'func':__getBrowse},'Select':{'func':__getSelect}}
        enumSEL = self.selectDialog(enumLST,header="Select Input",useDetails=False, multi=False)
        if not enumSEL is None: return [_getGlobals()._quoteString(value) for value in (enumKEY[enumLST[enumSEL]].get('func')()).split(',')]
        
