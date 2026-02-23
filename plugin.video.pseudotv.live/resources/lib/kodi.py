#   Copyright (C) 2025 Lunatixz
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
import platform, pyqrcode

from uuid                import uuid1, uuid4, UUID
from variables           import *
from logger              import log
from cache               import Cache, cacheit
from fileaccess          import FileAccess, FileLock
from infotagger.listitem import ListItemInfoTag
from json2html           import Json2Html
from pool                import poolit, timerit, threadit

class Settings(object):
    monitor    = MONITOR()
    cacheDB    = Cache()
    cache      = Cache(mem_cache=True)
    
    def __init__(self):
        self.properties = Properties()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def getRealSettings(self, id=ADDON_ID):
        try:    return xbmcaddon.Addon(id)
        except: return REAL_SETTINGS


    #GET
    def _getSetting(self, func, key):
        try: 
            value = func(key)
            self.log('[%s] %s, key = %s, value = %s'%(ADDON_ID,func.__name__,key,'%s...'%((str(value)[:128]))))
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
        return FileAccess.loadJSON(Globals._decodeString(self.getSetting(key)))
    
    
    def getCacheSetting(self, key, checksum=ADDON_VERSION, revive=False):
        value = self.cacheDB.get(key, checksum)
        if value and revive: self.setCacheSetting(key, value, checksum)
        return value
        
        
    def getEXTSetting(self, id, key):
        value = xbmcaddon.Addon(id).getSetting(key)
        self.log('[%s] getEXTSetting, key = %s, value = %s'%(id,key,'%s...'%((str(value)[:128]))))
        return value
        
        
    #CLR
    def clrCacheSetting(self, key):
        self.cache.clear(key)
    
    
    #SET
    def _setSetting(self, func, key, value):
        try:
            if str(self.getSetting(key)).lower() != str(value).lower(): func(key, value)
            self.log('[%s] %s, key = %s, value = %s'%(ADDON_ID,func.__name__,key,'%s...'%((str(value)[:128]))))
        except Exception as e: self.log("_setSetting, failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
            
        
    def setSetting(self, key, value=""):  
        if self.getSetting(key) != str(value): #Kodi setsetting() can tax system performance. i/o issue? block unneeded saves.
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
        return self.setSetting(key,Globals._encodeString(FileAccess.dumpJSON(values)))
            
            
    def setCacheSetting(self, key, value, checksum=ADDON_VERSION, life=datetime.timedelta(days=84)):
        return self.cacheDB.set(key, value, checksum, life)
            

    def setEXTSetting(self, id, key, value):
        self.log('[%s] setEXTSetting, key = %s, value = %s'%(id,key,'%s...'%((str(value)[:128]))))
        return xbmcaddon.Addon(id).setSetting(key,value)


    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getIP(self, default='0.0.0.0'):
        IP = (xbmc.getIPAddress() or gethostbyname(gethostname()) or default)
        log('getIP, IP = %s'%(IP))
        return IP
    
    
    def hasAddon(self, id, install=False, enable=False, force=False, notify=False):
        def __getIDbyPath(url):
            try:
                if   url.startswith('special://profile/addon_data/'):      return re.compile('special://profile/addon_data/(.*?)', re.IGNORECASE).search(url).group(1)
                elif url.startswith('special://home/addons/'):             return re.compile('special://home/addons/(.*?)/resources', re.IGNORECASE).search(url).group(1)
                elif url.startswith(('plugin://','resource://','pvr://')): return re.compile('(.*)://(.*?)/', re.IGNORECASE).search(url).group(2)
            except: pass
            return url
            
        if '://' in id: id = __getIDbyPath(id)
        hasAddon  = self.builtin.getInfoBool('HasAddon(%s)'%(id),'System')
        isEnabled = self.builtin.getInfoBool('AddonIsEnabled(%s)'%(id),'System')
        self.log(f'[{id}] hasAddon = {hasAddon}, isEnabled = {isEnabled}')
        
        if hasAddon:
            if enable and not isEnabled:
                if not force:
                    if not self.dialog.yesnoDialog(message=LANGUAGE(32156)%(id)):
                        self.log('[%s] hasAddon, (Not Enabled!)'%(id))
                        return
                self.builtin.executebuiltin('EnableAddon(%s)'%(id),wait=True)
            try:    return xbmcaddon.Addon(id)
            except: return False
        elif install:
            if self.builtin.executebuiltin('InstallAddon(%s)'%(id),wait=True):
                return self.hasAddon(id, False, enable, force, notify)
        if notify: self.dialog.notificationDialog(LANGUAGE(32034)%(id))
        
        
    def getAddonDetails(self, id=ADDON_ID):
        try:
            addon = xbmcaddon.Addon(id)
            properties = ['name', 'version', 'summary', 'description', 'path', 'author', 'icon', 'disclaimer', 'fanart', 'changelog', 'id', 'profile', 'stars', 'type']
            return dict([(property,addon.getAddonInfo(property)) for property in properties])    
        except:
            from jsonrpc import JSONRPC
            return JSONRPC().getAddonDetails(id)


    def getMYUUID(self):
        def __genUUID(seed=None):
            if seed:
                m = hashlib.md5()
                m.update(seed.encode(DEFAULT_ENCODING))
                return str(UUID(m.hexdigest()))
            return str(uuid1(clock_seq=70420))
            
        friendly = self.properties.getFriendlyName()
        uuid = self.getCacheSetting('MY_UUID', checksum=friendly, revive=True)
        if not uuid: uuid = self.setCacheSetting('MY_UUID', __genUUID(seed=self.properties.getFriendlyName()), checksum=friendly)
        return uuid


    def _getResumeURLs(self):
        for file in FileAccess.listdir(RESUME_LOC)[1]:
            yield 'http://%s/filelist/%s'%(self.properties.getRemoteHost(),file)


    @cacheit(expiration=datetime.timedelta(minutes=5))
    def getBonjour(self, inclChannels=False):
        self.log("getBonjour, inclChannels = %s"%(inclChannels))
        payload = {'id'      :ADDON_ID,
                   'uuid'    :self.getMYUUID(),
                   'version' :ADDON_VERSION,
                   'python'  :platform.python_version(),
                   'machine' :platform.machine(),
                   'platform':self.builtin.getInfoLabel('OSVersionInfo','System'),
                   'build'   :self.builtin.getInfoLabel('BuildVersion','System'),
                   'name'    :self.properties.getFriendlyName(),
                   'host'    :self.property.getRemoteHost()}
                   
        payload['remotes']   = {'bonjour':'http://%s/%s'%(payload['host'],BONJOURFLE),
                                'remote' :'http://%s/%s'%(payload['host'],REMOTEFLE),
                                'm3u'    :'http://%s/%s'%(payload['host'],M3UFLE),
                                'xmltv'  :'http://%s/%s'%(payload['host'],XMLTVFLE),
                                'genre'  :'http://%s/%s'%(payload['host'],GENREFLE),
                                'resume' : list(self._getResumeURLs())}
                              
        payload['settings']  = {'Resource_Logos'    :self.getSetting('Resource_Logos').split('|'),
                                'Resource_Bumpers'  :self.getSetting('Resource_Bumpers').split('|'),
                                'Resource_Ratings'  :self.getSetting('Resource_Ratings').split('|'),
                                'Resource_Adverts'  :self.getSetting('Resource_Adverts').split('|'),
                                'Resource_Trailers' :self.getSetting('Resource_Trailers').split('|')}
                                
        if inclChannels: 
            from channels    import Channels
            payload['channels'] = Channels().getChannels()
        payload['updated'] = datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
        payload['md5']     = Globals._getMD5(FileAccess.dumpJSON(payload))
        return payload
    
    
    @cacheit(expiration=datetime.timedelta(minutes=5))
    def getPayload(self, inclDebug: bool=False):
        self.log("getPayload, inclDebug! %s"%(inclDebug))
        def __getMeta(payload):
            from m3u         import M3U
            from xmltvs      import XMLTVS
            from library     import Library
            from multiroom   import Multiroom
            xmltv = XMLTVS()
            payload.pop('updated')
            payload.pop('md5')
            payload['m3u'] = M3U().getM3U()
            stations = xmltv.getChannels()
            recordings = xmltv.getRecordings()
            payload['xmltv']   = {'stations'  :[{'id':station.get('id'),'display-name':station.get('display-name',[['','']])[0][0],'icon':station.get('icon',[{'src':LOGO}])[0].get('src',LOGO)} for station in stations],
                                  'recordings':[{'id':recording.get('id'),'display-name':recording.get('display-name',[['','']])[0][0],'icon':recording.get('icon',[{'src':LOGO}])[0].get('src',LOGO)} for recording in recordings], 
                                  'programmes':[{'id':key,'end-time':epochTime(time.time(),tz=False).strftime(DTFORMAT)} for key, value in list(dict(xmltv.loadStopTimes()).items())]}
            payload['library'] = Library().getLibrary()
            payload['servers'] = Multiroom().getDiscovery()
            del xmltv
            return payload

        payload = __getMeta(self.getBonjour(inclChannels=True))
        if inclDebug: payload['debug'] = FileAccess.loadJSON(self.property.getEXTProperty('%s.debug.log'%(ADDON_ID))).get('DEBUG',{})
        payload['updated']   = epochTime(time.time(),tz=False).strftime(DTFORMAT)
        payload['md5']       = Globals._getMD5(FileAccess.dumpJSON(payload))
        return payload

            
    @cacheit(expiration=datetime.timedelta(minutes=5))
    def getPayloadUI(self):
        return Json2Html().convert(self.getPayload(inclDebug=True))


    def hasAutotuned(self):
        return self.properties.setEXTPropertyBool('has.Autotuned',self.getCacheSetting('has.Autotuned'))
        
        
    def setAutotuned(self, state=True):
        return self.properties.setEXTPropertyBool('has.Autotuned',self.setCacheSetting('has.Autotuned',state))


    def setWizardRun(self, state=True):
        return self.setCacheSetting('has.wizardRun',state)


    def hasWizardRun(self):
        return self.getCacheSetting('has.wizardRun', revive=True)

       
    def _IPTV_SIMPLE_SETTINGS(self): #recommended IPTV Simple settings
        return {'kodi_addon_instance_name'      :ADDON_NAME,
                'kodi_addon_instance_enabled'   :'false',
                'm3uPathType'                   :'0',
                'm3uPath'                       :M3UFLEPATH,
                'm3uUrl'                        :'',
                'm3uCache'                      :'false',
                'startNum'                      :'1',
                'numberByOrder'                 :'false',
                'm3uRefreshMode'                :'1',
                'm3uRefreshIntervalMins'        :'%s'%(M3U_REFRESH),
                'm3uRefreshHour'                :'0',
                'connectioncheckinterval'       :'10',
                'connectionchecktimeout'        :'20',
                'defaultProviderName'           :ADDON_NAME,
                'enableProviderMappings'      :'true',
                # 'providerMappingFile'         :PROVIDERFLEPATH,#todo
                # 'tvGroupMode'                 :'0',
                # 'customTvGroupsFile'          :(TVGROUPFLE),#todo
                # 'radioGroupMode'              :'0',
                # 'customRadioGroupsFile'       :(RADIOGROUPFLE),#todo
                'epgPathType'                   :'0',
                'epgPath'                       :XMLTVFLEPATH,
                'epgUrl'                        :'',
                'epgCache'                      :'true',
                'genresPathType'                :'0',
                'genresPath'                    :GENREFLEPATH,
                'genresUrl'                     :'',
                'useEpgGenreText'               :'true',
                'logoPathType'                  :'0',
                'logoPath'                      :LOGO_LOC,
                'logoBaseUrl'                   :'',
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


    def setPVRPath(self, path, instance=ADDON_NAME, prompt=None):
        settings  = self._IPTV_SIMPLE_SETTINGS()
        nsettings = {'m3uPathType'                :'0',
                     'm3uCache'                   :'false',
                     'm3uPath'                    :os.path.join(path,M3UFLE),
                     'epgPathType'                :'0',
                     'epgCache'                   :'false',
                     'epgPath'                    :os.path.join(path,XMLTVFLE),
                     'genresPathType'             :'0',
                     'genresPath'                 :os.path.join(path,GENREFLE),
                     'logoPathType'               :'0',
                     'logoPath'                   :os.path.join(path,'logos'),
                     'kodi_addon_instance_name'   : '%s - %s'%(ADDON_NAME,instance),
                     'kodi_addon_instance_enabled':'true'}
        settings.update(nsettings)
        self.log('[%s] setPVRRemote, %s settings = %s'%(PVR_CLIENT_ID, instance, nsettings))
        return self.chkPluginSettings(settings, instance, prompt)
        
        
    def setPVRRemote(self, host, instance=ADDON_NAME, prompt=None, cache=True):
        settings  = self._IPTV_SIMPLE_SETTINGS()
        nsettings = {'m3uPathType'                :'1',
                     'm3uCache'                   :'%s'%(str(cache)),
                     'm3uUrl'                     :'http://%s/%s'%(host,M3UFLE),
                     'epgPathType'                :'1',
                     'epgCache'                   :'%s'%(str(cache)),
                     'epgUrl'                     :'http://%s/%s'%(host,XMLTVFLE),
                     'genresPathType'             :'1',
                     'genresUrl'                  :'http://%s/%s'%(host,GENREFLE),
                     'logoPathType'               :'1',
                     'logoBaseUrl'                :'http://%s/logos'%(host),
                     'kodi_addon_instance_name'   : '%s - %s'%(ADDON_NAME,instance),
                     'kodi_addon_instance_enabled':'true'}
        settings.update(nsettings)
        self.log('[%s] setPVRRemote, %s settings = %s, cache = %s'%(PVR_CLIENT_ID, instance, nsettings, cache))
        return self.chkPluginSettings(settings, instance, prompt)
        
        
    def hasPVRInstance(self, instance=ADDON_NAME):
        instancePath = os.path.join(PVR_CLIENT_LOC,'instance-settings-%s.xml'%(self.gePVRInstance(instance)))
        if FileAccess.exists(instancePath):
            self.log('[%s] hasPVRInstance, instance = %s, path = %s'%(PVR_CLIENT_ID,instance, instancePath))
            return instancePath
        
        
    def gePVRInstance(self, instance=ADDON_NAME):
        return int(re.sub("[^0-9]", "", Globals._getMD5(instance))) * 2
        
        
    def findPVRInstance(self, instance=ADDON_NAME):
        found = self.hasPVRInstance(instance)
        if not found:
            for file in [filename for filename in FileAccess.listdir(PVR_CLIENT_LOC)[1] if filename.endswith('.xml')]:
                if file.startswith('instance-settings-'):
                    try:
                        xml = FileAccess.open(os.path.join(PVR_CLIENT_LOC,file), "r")
                        txt = xml.read()
                        xml.close()
                    except Exception as e:
                        self.log('[%s] findPVRInstance, path = %s, failed to open file = %s\n%s'%(PVR_CLIENT_ID,PVR_CLIENT_LOC,file,e))
                        continue
                            
                    match = re.compile(r'<setting id=\"kodi_addon_instance_name\" default=\"true\">(.*?)\</setting>', re.IGNORECASE).search(txt)
                    try: name = match.group(1)
                    except:
                        match = re.compile(r'<setting id=\"kodi_addon_instance_name\">(.*?)\</setting>', re.IGNORECASE).search(txt)
                        try:    name = match.group(1)
                        except: name = None
                        
                    if instance.lower() == str(name).lower():
                        if not found: found = os.path.join(PVR_CLIENT_LOC,file)
                        else: #auto remove any duplicate entries with the same instance name.
                            FileAccess.delete(os.path.join(PVR_CLIENT_LOC,file))
                            self.log('[%s] findPVRInstance, removing duplicate entry %s'%(PVR_CLIENT_ID,file))
                    self.log('[%s] findPVRInstance, found %s file = %s'%(PVR_CLIENT_ID,name,found))
        return found


    def getPVRInstanceSettings(self, instance):
        instanceConf = {}
        instancePath = self.hasPVRInstance(instance)
        self.log('[%s] getPVRInstanceSettings, instance = %s, path = %s'%(PVR_CLIENT_ID,instance,instancePath))
        if instancePath:
            fle = FileAccess.open(instancePath,'r')
            lines = fle.readlines()
            for line in lines:
                if not 'id="' in line: continue
                match = re.compile(r'<setting id=\"(.*)\" default=\"(.*)\">(.*?)\</setting>', re.IGNORECASE).search(line)
                try: 
                    instanceConf[match.group(1)] = match.group(3)
                    self.log('[%s] getPVRInstanceSettings, setting = %s, value = %s'%(PVR_CLIENT_ID,match.group(1),match.group(3)))
                except:
                    match = re.compile(r'<setting id=\"(.*)\">(.*?)\</setting>', re.IGNORECASE).search(line)
                    try:
                        instanceConf[match.group(1)] = match.group(2)
                        self.log('[%s] getPVRInstanceSettings, setting = %s, value = %s'%(PVR_CLIENT_ID,match.group(1),match.group(2)))
                    except: pass
            fle.close()
        return instanceConf
        
        
    def chkPluginSettings(self, nsettings, instance=ADDON_NAME, prompt=None):
        if prompt is None: prompt = not bool(self.getSettingBool('Enable_Kodi_Access'))
        self.log('[%s] chkPluginSettings, instance = %s, prompt = %s'%(PVR_CLIENT_ID,instance,prompt))
        addon = self.hasAddon(PVR_CLIENT_ID,enable=True,notify=True)
        if addon:
            message   = []
            osettings = self._IPTV_SIMPLE_SETTINGS()
            osettings.update(self.getPVRInstanceSettings(instance))
            for setting, nvalue in list(nsettings.items()):
                ovalue = (osettings.get(setting) or '')
                if str(nvalue).lower() != str(ovalue).lower(): 
                    osettings[setting] = nvalue
                    self.log('[%s] chkPluginSettings, setting = %s, current value = %s => %s'%(PVR_CLIENT_ID,setting,ovalue,nvalue))
                    message.append('Modifying %s: [COLOR=dimgray][B]%s[/B][/COLOR] => [COLOR=green][B]%s[/B][/COLOR]'%(setting,ovalue,nvalue))

            if len(message) > 0:
                if prompt:
                    self.dialog.textviewer('%s\n\n%s'%(LANGUAGE(32035)%(addon.getAddonInfo('name')),'[CR]'.join(message)))
                    if not self.dialog.yesnoDialog((LANGUAGE(32036)%addon.getAddonInfo('name'))):
                        self.dialog.notificationDialog(LANGUAGE(32046))
                        return False
                return self.setPVRInstanceSettings(instance, osettings)
            self.log('[%s] chkPluginSettings, no changes detected!'%(PVR_CLIENT_ID))


    def setPVRInstanceSettings(self, instance=ADDON_NAME, settings={}):
        addon = self.hasAddon(PVR_CLIENT_ID,enable=True)
        if addon:
            for setting, value in list(settings.items()):
                self.log('[%s] setPVRInstanceSettings, %s = %s'%(PVR_CLIENT_ID,setting,value))
                try:   addon.setSetting(setting, value)
                except Exception as e: log("[%s] setPVRInstanceSettings, failed! %s"%(PVR_CLIENT_ID,e), xbmc.LOGERROR)

            # todo https://github.com/xbmc/xbmc/pull/23648
            defaultFile = os.path.join(PVR_CLIENT_LOC,'settings.xml')
            if FileAccess.exists(defaultFile):
                instanceFile = os.path.join(PVR_CLIENT_LOC,'instance-settings-%s.xml'%(self.gePVRInstance(instance)))
                if FileAccess.exists(instanceFile): FileAccess.delete(instanceFile)
                self.log('[%s] setPVRInstanceSettings, creating %s'%(PVR_CLIENT_ID,instanceFile))
                FileAccess.move(defaultFile, instanceFile)
                return self.dialog.notificationDialog((LANGUAGE(32037)%(addon.getAddonInfo('name'))))
        return True
        
        
    def getCurrentSettings(self):
        settings = ['User_Folder', 'Debug_Enable', 'TCP_PORT']
        return dict([(setting,self.getSetting(setting)) for setting in settings])
               

    def getFileCRC(self, file):
        def __getCRC32(text):
            return binascii.crc32(text.encode(DEFAULT_ENCODING))
        try:
            fle = FileAccess.open(file,'r')
            crc = __getCRC32(fle.read())
            fle.close()
            name  = 'getFileCRC.%s'%(Globals._getMD5(file))
            cache = self.getCacheSetting(name, checksum=crc, revive=True)
            if not cache or cache != crc:
                self.setCacheSetting(name, crc, checksum=crc)
                return True
            return False
        except Exception as e:
            self.log("getFileCRC, failed! %s"%(file,e), xbmc.LOGERROR)
            return False
        
class Properties(object):
    def __init__(self, winID=10000):
        self.log('__init__, winID = %s'%(winID))
        self.winID  = winID
        self.window = xbmcgui.Window(winID)


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def getInstanceID(self):
        instanceID = self.getEXTProperty('%s.InstanceID'%(ADDON_ID))
        if not instanceID: instanceID = self.setInstanceID()
        return instanceID


    def setInstanceID(self):
        self._clearTrash(self.getEXTProperty('%s.InstanceID'%(ADDON_ID)))
        return self.setEXTProperty('%s.InstanceID'%(ADDON_ID),Globals._getMD5(uuid4()))


    def _clearTrash(self, instanceID=None): #clear abandoned properties after instanceID change
        if instanceID is None: instanceID = self.getInstanceID()
        tmpDCT = FileAccess.loadJSON(self.getEXTProperty('%s.TRASH'%(ADDON_ID)))
        if instanceID in tmpDCT:
            self.log('_clearTrash, instanceID = %s'%(instanceID))
            tmpLST = tmpDCT.pop(instanceID)
            for prop in tmpLST:
                self.clrProperty(prop)
                self.clrEXTProperty(prop)


    def _setTrash(self, key): #catalog instance properties that are abandoned
        instanceID = self.getInstanceID()
        tmpDCT     = FileAccess.loadJSON(self.getEXTProperty('%s.TRASH'%(ADDON_ID)))
        if key not in tmpDCT.setdefault(instanceID,[]): tmpDCT.setdefault(instanceID,[]).append(key)
        self.setEXTProperty('%s.TRASH'%(ADDON_ID),FileAccess.dumpJSON(tmpDCT))
        return key

        
    def _getKey(self, key, useInstance=True):
        if self.winID == 10000 and not key.startswith(ADDON_ID): #create unique id
            if useInstance: return self._setTrash('%s.%s.%s'%(ADDON_ID,key,self.getInstanceID()))
            else:           return '%s.%s'%(ADDON_ID,key)
        return key


    #GET
    def getProperty(self, key):
        key   = self._getKey(key)
        return self.window.getProperty(key)
        
        
    def getPropertyBool(self, key):
        return self.getProperty(key).lower() == "true"
        
        
    def getPropertyInt(self, key, default=-1):
        return int((self.getProperty(key) or default))
            
        
    def getPropertyFloat(self, key, default=0.0):
        return float((self.getProperty(key) or default))
        
        
    def getPropertyList(self, key):
        return self.getProperty(key).split('|')

        
    def getPropertyDict(self, key=''):
        return FileAccess.loadJSON(Globals._decodeString(self.getProperty(key)))
        
        
    def getEXTProperty(self, key):
        return xbmcgui.Window(10000).getProperty(key)
        
        
    def getEXTPropertyBool(self, key):
        return (self.getEXTProperty(key) or '').lower() == "true"
        
        
    #CLEAR
    def clrProperties(self):
        self.log('clrProperties')
        return self.window.clearProperties()
        
        
    def clrProperty(self, key):
        return self.window.clearProperty(self._getKey(key))


    def clrEXTProperty(self, key):
        return xbmcgui.Window(10000).clearProperty(key)
        
        
    #SET
    def setProperty(self, key, value):
        key = self._getKey(key)
        self.log('[%s] setProperty, key = %s, value = %s'%(self.winID,key,'%s...'%((str(value)[:128]))))
        self.window.setProperty(key, str(value))
        return value
        
        
    def setPropertyBool(self, key, value):
        if value: self.setProperty(key, value)
        else:     self.clrProperty(key)
        return value
        
        
    def setPropertyInt(self, key, value):
        return self.setProperty(key, int(value))
                
                
    def setPropertyFloat(self, key, value):
        return self.setProperty(key, float(value))

    
    def setPropertyList(self, key, values):
        return self.setProperty(key, '|'.join(values))
        
        
    def setPropertyDict(self, key, value={}):
        return self.setProperty(key, Globals._encodeString(FileAccess.dumpJSON(value)))
        
                
    def setEXTProperty(self, key, value):
        if not '.TRASH' in key: self.log('[%s] setEXTProperty, key = %s, value = %s'%(10000,key,'%s...'%((str(value)[:128]))))
        xbmcgui.Window(10000).setProperty(key,str(value))
        return value
        
        
    def setEXTPropertyBool(self, key, value):
        return str(self.setEXTProperty(key,str(value).lower())).lower() == 'true'


    def setEpochTimer(self, key, time=0): #_chkEpochTimer trigger - Time = 0 == Run
        return self.setPropertyInt(key,time)


    def setPropTimer(self, key, state=True): #_chkPropTimer trigger - True == Run
        return self.setEXTPropertyBool('%s.%s'%(ADDON_ID,key),state)


    def setRemoteHost(self, value):
        return self.setEXTProperty('%s.Remote_Host'%(ADDON_ID),value)
        
        
    def getRemoteHost(self):
        remote = self.getEXTProperty('%s.Remote_Host'%(ADDON_ID))
        if not remote: remote = self.setRemoteHost('%s:%s'%(Settings().getIP(),Settings().getSettingInt('TCP_PORT')))
        return remote


    @contextmanager
    def chkRunning(self, key):
        if not self.isRunning(key):
            self.setRunning(key,True)
            try: yield True
            finally: self.setRunning(key,False)
        else: yield False
        
        
    def setTrakt(self, state=False):
        self.log('setTrakt, disable trakt = %s'%(state))
        # https://github.com/trakt/script.trakt/blob/d45f1363c49c3e1e83dabacb70729cc3dec6a815/resources/lib/kodiUtilities.py#L104
        if state: self.setEXTPropertyBool('script.trakt.paused',state)
        else:     self.clrEXTProperty('script.trakt.paused')


    def setRunning(self, key, state=True):
        return self.setEXTPropertyBool('%s.%s.Running'%(ADDON_ID,key),state)
        
        
    def isRunning(self, key):
        return self.getEXTPropertyBool('%s.%s.Running'%(ADDON_ID,key))


    def setInitRun(self, state=True):
        return self.setEXTPropertyBool('%s.Init.Run'%(ADDON_ID),state)


    def hasInitRun(self):
        return self.getEXTPropertyBool('%s.Init.Run'%(ADDON_ID))


    def setChannels(self, state=True):
        return self.setEXTPropertyBool('%s.has.Channels'%(ADDON_ID),state)


    def hasChannels(self):
        return self.getEXTPropertyBool('%s.has.Channels'%(ADDON_ID))


    def setBackup(self, state=True):
        return self.setEXTPropertyBool('%s.has.Backup'%(ADDON_ID),state)


    def hasBackup(self):
        return self.getEXTPropertyBool('%s.has.Backup'%(ADDON_ID))


    def hasLibrary(self, type):
        return self.getEXTPropertyBool('%s.has.%s'%(ADDON_ID,type))
        
        
    def setLibrary(self, type, state=True):
        return self.setEXTPropertyBool('%s.has.%s'%(ADDON_ID,type),state)
        
        
    def setServers(self, state=True):
        return self.setEXTPropertyBool('%s.has.Servers'%(ADDON_ID),state)
        

    def hasServers(self):
        return self.getEXTPropertyBool('%s.has.Servers'%(ADDON_ID))
        
                
    def setEnabledServers(self, state=True):
        return self.setEXTPropertyBool('%s.has.Enabled_Servers'%(ADDON_ID),state)
        
        
    def hasEnabledServers(self):
        return self.getEXTPropertyBool('%s.has.Enabled_Servers'%(ADDON_ID))
        
        
    def setPendingShutdown(self, state=True):
        return self.setEXTPropertyBool('%s.pendingShutdown'%(ADDON_ID),state)
        

    def isPendingShutdown(self):
        value = self.getEXTPropertyBool('%s.pendingShutdown'%(ADDON_ID))
        self.clrEXTProperty('%s.pendingShutdown'%(ADDON_ID))
        return value
        
                
    def setPendingRestart(self, state=True):
        return self.setEXTPropertyBool('%s.pendingRestart'%(ADDON_ID),state)


    def isPendingRestart(self):
        value = self.getEXTPropertyBool('%s.pendingRestart'%(ADDON_ID))
        self.clrEXTProperty('%s.pendingRestart'%(ADDON_ID))
        return value

     
    def setFirstRun(self, state=True):
        return self.setEXTPropertyBool('%s.has.firstRun'%(ADDON_ID),state)


    def hasFirstRun(self):
        return self.getEXTPropertyBool('%s.has.firstRun'%(ADDON_ID))


    @contextmanager
    def lockActivity(self, state=True):
        if not self.isLockActivity():
            self.setLockActivity(True)
            try: yield
            finally: self.setLockActivity(False)
        else: yield


    def setLockActivity(self, state=True): # context state
        return self.setEXTPropertyBool('%s.lockActivity'%(ADDON_ID),state)


    def isLockActivity(self):# context state
        return self.getEXTPropertyBool('%s.lockActivity'%(ADDON_ID))


    @contextmanager
    def interruptActivity(self): #quit background task
        if not self.isInterruptActivity() and not self.isLockActivity():
            self.setInterruptActivity(True)
            try: yield
            finally: self.setInterruptActivity(False)
        else: yield
        
           
    def setInterruptActivity(self, state=True): # context state
        return self.setEXTPropertyBool('%s.interruptActivity'%(ADDON_ID),state)
        

    def isInterruptActivity(self): # context state
        return self.getEXTPropertyBool('%s.interruptActivity'%(ADDON_ID))


    def setPendingInterrupt(self, state=True): # interrupt state
        return self.setEXTPropertyBool('%s.pendingInterrupt'%(ADDON_ID),state)


    def isPendingInterrupt(self):  # interrupt state
        return self.getEXTPropertyBool('%s.pendingInterrupt'%(ADDON_ID))

        
    @contextmanager
    def suspendActivity(self): #pause background task.
        if not self.isSuspendActivity() and not self.isLockActivity():
            self.setSuspendActivity(True)
            try: yield
            finally: self.setSuspendActivity(False)
        else: yield


    def setSuspendActivity(self, state=True): # context state
        return self.setEXTPropertyBool('%s.suspendActivity'%(ADDON_ID),state)


    def isSuspendActivity(self): # context state
        return self.getEXTPropertyBool('%s.suspendActivity'%(ADDON_ID))
        
        
    def setPendingSuspend(self, state=True): # suspend state
        return self.setEXTPropertyBool('%s.pendingSuspend'%(ADDON_ID),state)
        
        
    def isPendingSuspend(self): # suspend state
        return self.getEXTPropertyBool('%s.pendingSuspend'%(ADDON_ID))


    def recessActivity(self, msg, func, *args, **kwargs):
        orgSuspend   = self.isSuspendActivity()
        orgInterrupt = self.isInterruptActivity()
        while not self.monitor.abortRequested():
            isSuspend   = self.isSuspendActivity()
            isInterrupt = self.isInterruptActivity()
            isBuilding  = self.isRunning('Builder.buildChannels')
            if msg: Dialog().notificationDialog(msg)
            self.log('recessActivity, isInterrupt = %s, isSuspend = %s, isBuilding = %s'%(isInterrupt,isSuspend,isBuilding))
            if not isInterrupt and (isSuspend or isBuilding):
                if isSuspend:  self.setSuspendActivity(False)
                if isBuilding: self.setInterruptActivity(True)
            elif isInterrupt: self.setInterruptActivity(False)
            elif not isInterrupt and not any(set([isSuspend, isBuilding])):
                with self.lockActivity():
                    try: 
                        results = func(*args, **kwargs)
                        self.setSuspendActivity(orgSuspend)
                        self.setInterruptActivity(orgInterrupt)
                        return results
                    except Exception as e: 
                        self.log("recessActivity, failed! %s"%(e), xbmc.LOGERROR)
                        return
            if self.monitor.waitForAbort(SUSPEND_INTERVAL): return


    @contextmanager
    def legacy(self): #toggle legacy property from older pseudotv project that may still be used by third-party plugins.
        if not self.isPseudoTVRunning():
            self.setEXTPropertyBool('PseudoTVRunning',True)
            try: yield
            finally: self.setEXTPropertyBool('PseudoTVRunning',False)
        else: yield


    def isPseudoTVRunning(self):
        return self.getEXTPropertyBool('PseudoTVRunning')


    def getFriendlyName(self):
        friendly = self.getEXTProperty('Instance_Name')
        if not friendly or friendly == LANGUAGE(32105):
            from jsonrpc import JSONRPC
            friendly = self.setEXTProperty('Instance_Name', JSONRPC().inputFriendlyName())
        return friendly
        
        
    @contextmanager
    def setBackgroundLabel(self, text):
        self.setEXTProperty('%s.background.text'%(ADDON_ID),text)
        try: yield 
        finally:
            self.clrEXTProperty('%s.background.text'%(ADDON_ID))


class ListItems(object):
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def getListItem(self, label='', label2='', path='', offscreen=False):
        return xbmcgui.ListItem(label,label2,path,offscreen)


    def infoTagVideo(self, offscreen=False):
        return xbmc.InfoTagVideo(offscreen)


    def InfoTagMusic(self, offscreen=False):
        return xbmc.InfoTagVideo(offscreen)
        

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
                art['poster'] = (Globals._getThumb(info,opt=1) or COLOR_LOGO)
                art['fanart'] = (Globals._getThumb(info)       or FANART)
                
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
            
                     
    def buildMenuListItem(self, label="", label2="", icon=COLOR_LOGO, url="", info={}, art={}, props={}, offscreen=False, media='video'):
        if not art: art = {'thumb':icon,'logo':icon,'icon':icon}
        listitem = self.getListItem(label, label2, url, offscreen=offscreen)
        listitem.setIsFolder(True)
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
    busy = None
    json_lock = Lock()
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  
                  
    def hasSearches(self):
        from jsonrpc import JSONRPC
        return len(JSONRPC().getPVRSearches()) > 0
            
         
    def hasRecordings(self):
        from jsonrpc import JSONRPC
        return len(JSONRPC().getPVRRecordings()) > 0
               
     
    def hasPVR(self):
        return self.getInfoBool('HasTVChannels','Pvr')
        
        
    def hasRadio(self):
        return self.getInfoBool('HasRadioChannels','Pvr')


    def hasMusic(self):
        return self.getInfoBool('HasContent(Music)','Library')
        
        
    def hasTV(self):
        return self.getInfoBool('HasContent(TVShows)','Library')
        
        
    def hasMovie(self):
        return self.getInfoBool('HasContent(Movies)','Library')
                

    def hasMedia(self) -> bool:
        return self.getInfoBool('hasMedia','Player')


    def hasGame(self) -> bool:
        return self.getInfoBool('HasGame','Player')


    def hasDuration(self) -> bool:
        return self.getInfoBool('HasDuration','Player')


    def hasEPG(self) -> bool:
        return self.getInfoBool('HasEpg','VideoPlayer')

  
    def hasSubtitle(self):
        return self.getInfoBool('HasSubtitles','VideoPlayer')


    def isSubtitle(self):
        return self.getInfoBool('SubtitlesEnabled','VideoPlayer')


    def isPlaylistRandom(self):
        return self.getInfoLabel('Random','Playlist').lower() == 'on' # Disable auto playlist shuffling if it's on
        
        
    def isPlaylistRepeat(self):
        return self.getInfoLabel('IsRepeat','Playlist').lower() == 'true' # Disable auto playlist repeat if it's on #todo


    def isPaused(self):
        return self.getInfoBool('Paused','Player')
                
                
    def isRecording(self):
        return self.getInfoBool('IsRecording','Pvr')
        
        
    def isScanning(self):
        return (self.getInfoBool('IsScanningVideo','Library') & self.getInfoBool('IsScanningMusic','Library'))
          
                      
    def isSettingsOpened(self) -> bool:
        return (self.getInfoBool('IsVisible(addonsettings)','Window') | self.getInfoBool('IsVisible(selectdialog)' ,'Window'))


    def isPlaying(self):
        return self.getInfoBool('Playing','Player')


    def isPVRPlaying(self) -> bool:
        return (self.getInfoBool('IsPlayingTv','Pvr') | self.getInfoBool('IsPlayingRadio','Pvr') | self.getInfoBool('IsPlayingRecording','Pvr') | self.getInfoBool('IsPlayingActiveRecording','Pvr'))


    def isBusyDialog(self):
        return (self.properties.isRunning('BUSY_OVERLAY') | self.getInfoBool('IsActive(busydialognocancel)','Window') | self.getInfoBool('IsActive(busydialog)','Window'))


    def closeBusyDialog(self):
        if hasattr(self.busy, 'close'):
            self.busy = self.busy.close()
        elif self.getInfoBool('IsActive(busydialognocancel)','Window'):
            self.executebuiltin('Dialog.Close(busydialognocancel)')
        elif self.getInfoBool('IsActive(busydialog)','Window'):
            self.executebuiltin('Dialog.Close(busydialog)')


    @contextmanager
    def busy_dialog(self, cancel=False, lock=False):
        if not self.isBusyDialog() and not cancel:
            try: 
                if self.busy is None:
                    from overlay import Busy 
                    try:     self.busy = Busy(BUSY_XML, ADDON_PATH, "default", lock=lock)
                    except:  self.busy = None
                    finally: self.busy.show()
                yield
            finally:
                if hasattr(self.busy, 'close'):
                    self.busy = self.busy.close()
        else: yield


    def getIdle(self):
        try:    return int(xbmc.getGlobalIdleTime() or '0')
        except: return 0
            

    def getInfoLabel(self, key, param='ListItem', default=''):
        value = xbmc.getInfoLabel('%s.%s'%(param,key))
        if value == "Busy": 
            if not self.monitor.waitForAbort(1.0): return self.getInfoLabel(key,param,default)
        self.log('getInfoLabel, key = %s.%s, value = %s'%(param,key,value))
        return (value or default)
        

    def getInfoBool(self, key, param='Library'):
        value = (xbmc.getCondVisibility('%s.%s'%(param,key)) or False)
        self.log('getInfoBool, key = %s.%s, value = %s'%(param,key,value))
        return value
        
        
    def executewindow(self, key, wait=False, delay=False, condition=None):
        return self.executebuiltin(key,wait,delay,condition)
        
        
    def executebuiltin(self, key, wait=False, delay=False, condition=None):
        if not condition is None and not condition(): return False
        self.log('executebuiltin, key = %s, wait = %s, delay = %s, condition = %s):'%(key,wait,delay,condition))
        xbmc.executebuiltin('%s'%(key),wait)
        return True
        
        
    def executescript(self, path, condition=None):
        self.log('executescript, path = %s'%(path))
        if not condition is None and not condition(): return False
        xbmc.executescript('%s'%(path))
        return True


    def executeJSONRPC(self, request):
        with self.json_lock:
            response = xbmc.executeJSONRPC(FileAccess.dumpJSON(request))
            self.monitor.waitForAbort(float(self.settings.getSettingInt('RPC_Delay')/1000))
            self.log('executeJSONRPC, request = %s\nresponse = %s'%(request,response))
            return response
        

    def getResolution(self):
        WH, WIN = self.getInfoLabel('ScreenResolution','System').split(' - ')
        return (1920,1080), WIN #tuple(int(x) for x in WH.split('x')), WIN


class Dialog(object):
    monitor    = MONITOR()
    settings   = Settings()
    properties = Properties()
    listitems  = ListItems()
    builtin    = Builtin()
    dialog     = xbmcgui.Dialog()
    
    def __init__(self):
        self.settings.monitor   = self.monitor
        self.settings.property  = self.properties
        self.settings.builtin   = self.builtin
        self.properties.monitor = self.monitor
        self.builtin.monitor    = self.monitor
        self.builtin.properties = self.properties
        self.builtin.settings   = self.settings
        self.settings.dialog    = self
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def toggleInfoMonitor(self, state, wait=0.5):
        self.log('toggleInfoMonitor, state = %s'%(state))
        self.properties.setPropertyBool('chkInfoMonitor',state)
        if state:
            self.properties.clrProperty('monitor.montiorList')
            timerit(self.doInfoMonitor)(0.0001)


    def doInfoMonitor(self):
        while not self.monitor.abortRequested():
            if not self.fillInfoMonitor(): break
            elif self.monitor.waitForAbort(float(self.settings.getSettingInt('RPC_Delay')/1000)): break
            

    def fillInfoMonitor(self, type='ListItem'):
        #todo catch full listitem not singular properties.
        try:
            item = {'label'       :self.builtin.getInfoLabel('Label'       ,type),
                    'label2'      :self.builtin.getInfoLabel('Label2'      ,type),
                    'set'         :self.builtin.getInfoLabel('Set'         ,type),
                    'path'        :self.builtin.getInfoLabel('Path'        ,type),
                    'genre'       :self.builtin.getInfoLabel('Genre'       ,type),
                    'studio'      :self.builtin.getInfoLabel('Studio'      ,type),
                    'title'       :self.builtin.getInfoLabel('Title'       ,type),
                    'tvshowtitle' :self.builtin.getInfoLabel('TVShowTitle' ,type),
                    'plot'        :self.builtin.getInfoLabel('Plot'        ,type),
                    'addonname'   :self.builtin.getInfoLabel('AddonName'   ,type),
                    'artist'      :self.builtin.getInfoLabel('Artist'      ,type),
                    'album'       :self.builtin.getInfoLabel('Album'       ,type),
                    'albumartist' :self.builtin.getInfoLabel('AlbumArtist' ,type),
                    'foldername'  :self.builtin.getInfoLabel('FolderName'  ,type),
                    'logo'        :(self.builtin.getInfoLabel('Art(tvshow.clearlogo)',type) or 
                                    self.builtin.getInfoLabel('Art(clearlogo)'       ,type) or
                                    self.builtin.getInfoLabel('Icon'                 ,type) or
                                    self.builtin.getInfoLabel('Thumb'                ,type))}
            if item.get('label'):
                montiorList = self.getInfoMonitor()
                if item.get('label') not in montiorList: montiorList.insert(0,item)
                self.setInfoMonitor(montiorList)
            return self.properties.getPropertyBool('chkInfoMonitor')
        except Exception as e:
            self.log("fillInfoMonitor, failed! %s"%(e), xbmc.LOGERROR)
            return False


    def getInfoMonitor(self):
        return self.properties.getPropertyDict('monitor.montiorList').get('info',[])
    
    
    def setInfoMonitor(self, items):
        return self.properties.setPropertyDict('monitor.montiorList',{'info':list(Globals._setDictLST(items))})


    def colorDialog(self, colorlist=[], preselect="", colorfile="", heading=ADDON_NAME):
        return self.dialog.colorpicker(heading, preselect, colorfile, colorlist)
    
    
    def _closeOkDialog(self):
        if self.builtin.getInfoBool('IsActive(okdialog)','Window'):
            self.builtin.executebuiltin('Dialog.Close(okdialog)')
        
        
    def _okDialog(self, msg, heading, autoclose):
        return timerit(self.okDialog)(0.1,[msg, heading, autoclose])


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
                    except: pass
                self.close()

        if not self.properties.isRunning('Dialog.qrDialog'):
            with self.properties.chkRunning('Dialog.qrDialog'):
                with self.builtin.busy_dialog():
                    imagefile = os.path.join(FileAccess.translatePath(TEMP_IMAGE_LOC),'%s.png'%(Globals._getMD5(str(url.split('/')[-1]))))
                    if not FileAccess.exists(imagefile):
                        qrIMG = pyqrcode.create(url)
                        qrIMG.png(imagefile, scale=10)
                        
            qr = QRCode( "plugin.video.pseudotv.live.qrcode.xml" , ADDON_PATH, "default", image=imagefile, text=msg, header=heading, atclose=autoclose)
            qr.doModal()
            del qr
            return True

        
    def _closeTextViewer(self):
        if self.builtin.getInfoBool('IsActive(textviewer)','Window'):
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
                except: pass
                
        return TEXTVIEW("DialogTextViewer.xml", os.getcwd(), "Default")


    def _textViewer(self, msg, heading, usemono, autoclose):
        return timerit(self.textviewer)(0.1,[msg, heading, usemono, autoclose])
        
        
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
        return timerit(self.notificationWait)(0.1,[message, header, wait])


    def notificationWait(self, message, header=ADDON_NAME, wait=4, show=True, usethread=False):
        # if show is None: show = self.settings.getSettingBool('Notify_While_Playing')
        if usethread: return self._notificationWait(message, header, wait)
        else:
            with self._progressDialog(message, header, show==False) as pDialog:
                for idx in range(int(wait)):
                    pDialog = self._updateProgress(pDialog,int(idx*100//wait))
                    if pDialog is None or self.monitor.waitForAbort(1.0): break
                if hasattr(pDialog, 'close'): pDialog.close()
        return True
        

    @contextmanager
    def _progressDialog(self, message='', header=ADDON_NAME, silent=False, background=True):
        if not self.properties.isRunning('_progressDialog'):
            with self.properties.chkRunning('_progressDialog'):
                if not silent:
                    if background: dlg = xbmcgui.DialogProgressBG()
                    else:          dlg = xbmcgui.DialogProgress()
                    try:
                        dlg.create(header, message)
                        self.log(f'_progressDialog [0% - {dlg}] silent = {silent}\nheader = {header}\nmessage = {message}')
                        yield dlg
                    finally:
                        try:
                            dlg.close()
                            self.log(f'_progressDialog [100% - {dlg}] silent = {silent}\nheader = {header}\nmessage = {message}')
                        except Exception: pass
                else: yield True
        else: yield True


    def _updateProgress(self, dlg=None, percent=1, message='', header=ADDON_NAME):
        if isinstance(dlg, xbmcgui.DialogProgressBG):
            if   dlg.isFinished(): return None
            elif hasattr(dlg, 'update'):
                self.log(f'_updateProgress [{percent}% - {dlg}]\nheader = {header}\nmessage = {message}')
                dlg.update(percent, header, message)
        elif isinstance(dlg, xbmcgui.DialogProgress):
            if   dlg.iscanceled(): return None
            elif hasattr(dlg, 'update'):
                try:
                    match   = re.compile(r'(.*?): (.*?)\%', re.IGNORECASE).search(message)
                    message = '%s: %s'%(header.replace('%s, '%(ADDON_NAME),''),match.group(1))
                    percent = int(match.group(2))
                except: pass
                self.log(f'_updateProgress [{percent}% - {dlg}]\nheader = {header}\nmessage = {message}')
                dlg.update(percent, message)
        return dlg
        
        
    def progressDialog(self, percent=0, control=None, message='', header=ADDON_NAME):
        if control is None and int(percent) == 0:
            control = xbmcgui.DialogProgress()
            control.create(header, message)  
        elif control:
            if   int(percent) == 100 or control.iscanceled(): return control.close()
            elif hasattr(control, 'update'): control.update(int(percent), message)
        return control
        
        
    def progressBGDialog(self, percent=0, control=None, message='', header=ADDON_NAME):
        if control is None and int(percent) == 0:
            control = xbmcgui.DialogProgressBG()
            control.create(header, message)
        elif control:
            if   int(percent) == 100 or control.isFinished(): return control.close()
            elif hasattr(control,'update'): control.update(int(percent), header, message)
        return control

                
    def infoDialog(self, listitem):
        self.dialog.info(listitem)
        
    
    def _notificationDialog(self, message, header, sound, time, icon, show):
        threadit(self.notificationDialog)(message, header, sound, time, icon, show)


    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=PROMPT_DELAY, icon=COLOR_LOGO, show=True, usethread=False):
        # if show is None: show = self.settings.getSettingBool('Notify_While_Playing')
        self.log('notificationDialog: %s, show = %s'%(message,show))
        if usethread: return self._notificationDialog(message, header, sound, time, icon, show)
        else:
            ## - Builtin Icons:
            ## - xbmcgui.NOTIFICATION_INFO
            ## - xbmcgui.NOTIFICATION_WARNING
            ## - xbmcgui.NOTIFICATION_ERROR
            if show:
                try:    self.dialog.notification(header, message, icon, time*1000, sound=False)
                except: self.builtin.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time*1000, icon))
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
            select = self.dialog.multiselect(header, items, (autoclose*1000), preselect, useDetails)
            if select == [-1]: return
        else:
            if not preselect: preselect = -1
            elif isinstance(preselect,list) and len(preselect) > 0: preselect = preselect[0]
            select = self.dialog.select(header, items, (autoclose*1000), preselect, useDetails)
            if select == -1: return
        return select
      
      
    def inputDialog(self, message, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
        ## - xbmcgui.INPUT_ALPHANUM (standard keyboard)
        ## - xbmcgui.INPUT_NUMERIC (format: #)
        ## - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
        ## - xbmcgui.INPUT_TIME (format: HH:MM)
        ## - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
        ## - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
        return self.dialog.input(message, default, key, opt, close)
        
        
    def selectPredefined(self, type=None):
        self.log('selectPredefined, type = %s'%(type))
        

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
            
        selects = self.selectDialog(lizLST, 'Select one or more resources', preselect=Globals._findItemsInLST(lizLST,ids,'getPath'), multi=multi)
        if selects is None:                return
        elif not isinstance(selects,list): return lizLST[selects].getPath()
        else:                              return [lizLST[select].getPath() for select in selects]


    def browseSources(self, type=0, heading=ADDON_NAME, default='', shares='', mask='', useThumbs=True, treatAsFolder=False, multi=False, monitor=False, include=[], exclude=[]):
        self.log('browseSources, type = %s, heading= %s, shares= %s, useThumbs= %s, treatAsFolder= %s, default= %s, mask= %s, include= %s, exclude= %s'%(type,heading,shares,useThumbs,treatAsFolder,default,mask,len(include),exclude))
        def __buildMenuItem(option):
            return self.listitems.buildMenuListItem(option['label'],option['label2'],DUMMY_ICON.format(text=Globals._getAbbr(option['label'])))

        with self.builtin.busy_dialog():
            optlabel = "%s"%({'0':'Folders [Recursive]','1':'Files'}[str(type)]) if multi else "%s"%({'0':'Folder [Recursive]','1':'File'}[str(type)])
            opts = [{"idx":10, "label":'%s %s'%(LANGUAGE(32196),optlabel) , "label2":"library://video/"                      , "default":"library://video/"                   , "shares":"video"   , "mask":xbmc.getSupportedMedia('video')   , "type":0    , "multi":multi},
                    {"idx":11, "label":'%s %s'%(LANGUAGE(32207),optlabel) , "label2":"library://music/"                      , "default":"library://music/"                   , "shares":"music"   , "mask":xbmc.getSupportedMedia('music')   , "type":0    , "multi":multi},
                    {"idx":12, "label":LANGUAGE(32191)                    , "label2":"special://profile/playlists/video/"    , "default":"special://profile/playlists/video/" , "shares":""        , "mask":".xsp"                            , "type":1    , "multi":False},
                    {"idx":13, "label":LANGUAGE(32192)                    , "label2":"special://profile/playlists/music/"    , "default":"special://profile/playlists/music/" , "shares":""        , "mask":".xsp"                            , "type":1    , "multi":False},
                    {"idx":15, "label":LANGUAGE(32195)                    , "label2":"Dynamic SmartPlaylists"                , "default":""                                   , "shares":""        , "mask":""                                , "type":1    , "multi":False},
                    {"idx":16, "label":LANGUAGE(32194)                    , "label2":"Import paths from STRM file"           , "default":""                                   , "shares":"files"   , "mask":".strm"                           , "type":1    , "multi":False},
                    {"idx":17, "label":LANGUAGE(32206)                    , "label2":"Import files from Basic Playlist"      , "default":""                                   , "shares":""        , "mask":"|".join(BASIC_PLAYLISTS)         , "type":1    , "multi":False},
                    {"idx":18, "label":'%s %s'%(LANGUAGE(32198),optlabel) , "label2":""                                      , "default":""                                   , "shares":"files"   , "mask":mask                              , "type":type , "multi":multi},
                    {"idx":19, "label":'%s %s'%(LANGUAGE(32199),optlabel) , "label2":""                                      , "default":""                                   , "shares":"local"   , "mask":mask                              , "type":type , "multi":multi},
                    {"idx":20, "label":'%s %s'%(LANGUAGE(32200),optlabel) , "label2":""                                      , "default":""                                   , "shares":shares    , "mask":mask                              , "type":type , "multi":multi},
                    {"idx":21, "label":LANGUAGE(32201)                    , "label2":""                                      , "default":""                                   , "shares":"pictures", "mask":xbmc.getSupportedMedia('picture') , "type":1    , "multi":False},
                    {"idx":22, "label":LANGUAGE(32202)                    , "label2":"Image & Video Resources"               , "default":""                                   , "shares":shares    , "mask":mask                              , "type":type , "multi":multi}]

            options = include.copy()
            options.extend([opt for opt in opts if not opt.get('idx',-1) in exclude])
            options = Globals._setDictLST(options)
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
            if "resource."   in default or options[select]["idx"] == 22: return self._resourcePath(default, {xbmc.getSupportedMedia('video'):'videos',xbmc.getSupportedMedia('picture'):'images'}.get(mask,xbmc.getSupportedMedia('video')))
        elif type == 1:
            if   "?xsp="     in default or options[select]["idx"] == 15: return self.buildDXSP(default)
            elif ".strm"     in default or options[select]["idx"] == 16: return self.importSTRM(default)
            elif "resource." in default or options[select]["idx"] == 22: default = self._resourcePath(default, {xbmc.getSupportedMedia('video'):'videos',xbmc.getSupportedMedia('picture'):'images'}.get(mask,xbmc.getSupportedMedia('video')))
        elif mask == '?xsp=':                                            return self.selectPredefined(default)
        return self.browseDialog(type, heading, default, shares, mask, useThumbs, treatAsFolder, multi, monitor)
            
    
    def browseDialog(self, type=0, heading=ADDON_NAME, default='', shares='', mask='', useThumbs=True, treatAsFolder=False, multi=False, monitor=False):
        self.log('browseDialog, type = %s, heading= %s, shares= %s, useThumbs= %s, treatAsFolder= %s, default= %s\nmask= %s'%(type,heading,shares,useThumbs,treatAsFolder,default,mask))
        # https://xbmc.github.io/docs.kodi.tv/master/kodi-base/d6/de8/group__python___dialog.html#ga856f475ecd92b1afa37357deabe4b9e4
        # https://xbmc.github.io/docs.kodi.tv/master/kodi-base/d6/de8/group__python___dialog.html#gafa1e339e5a98ae4ea4e3d3bb3e1d028c
        if monitor: self.toggleInfoMonitor(True)
        if multi == True and type > 0:  retval = self.dialog.browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        else:                           retval = self.dialog.browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        if monitor: self.toggleInfoMonitor(False)
        if not retval is None and retval != default:
            return retval
        

    def multiBrowse(self, paths: list=[], header=ADDON_NAME, exclude=[], monitor=True):
        self.log('multiBrowse, IN paths = %s'%(paths))
        def __buildListItem(item): #label: str="", label2: str="", icon: str=COLOR_LOGO, paths: list=[], items: dict={}
            idx = pathLST.index(item)
            return self.listitems.buildMenuListItem('%s|'%(idx+1), item, DUMMY_ICON.format(text=str(idx+1)), url='|'.join(item), props={'idx':idx+1})

        select  = -1
        epaths  = paths.copy()
        pathLST = list([_f for _f in paths if _f])
        lastOPT = None
        while not self.monitor.abortRequested() and not select is None:
            with self.builtin.busy_dialog():
                npath  = None
                lizLST = []
                lizLST.extend(poolit(__buildListItem)(pathLST))
                lizLST.insert(0,__buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32100)),LANGUAGE(33113),icon=ICON,items={'key':'add','idx':0}))
                if len(pathLST) > 0 and epaths != pathLST: lizLST.insert(1,__buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32101)),LANGUAGE(33114),icon=ICON,items={'key':'save'}))
            
            select = self.selectDialog(lizLST, header, preselect=lastOPT, multi=False)
            if not select is None:
                key, path = lizLST[select].getProperty('key'), lizLST[select].getPath()
                try:    lastOPT = int(lizLST[select].getProperty('idx'))
                except: lastOPT = -1
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
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value),icon=DUMMY_ICON.format(text=Globals._getAbbr(key.title())),props={'key':key,'value':value}) for key, value in list(rule.items())]
                enumSEL = self.selectDialog(enumLST,header="Select method",preselect=-1, multi=False)
                if not enumSEL is None: rule.update({enumLST[enumSEL].getProperty('key'):({"field":field,"operator":operator,"value":value}[enumLST[enumSEL].getProperty('key')])(params,rule)})
            return rule
            
        def __getRules(params={}):
            enumSEL = -1
            eparams = params.copy()
            while not self.monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),FileAccess.dumpJSON(params.get('rules',{}).get(key,[])),icon=DUMMY_ICON.format(text=Globals._getAbbr(key.title())),props={'key':key}) for key in ["and","or"]]
                enumSEL = self.selectDialog(enumLST,header="Edit Rules",multi=False)
                if not enumSEL is None:
                    if enumLST[enumSEL].getLabel() in ['And','Or']:
                        CONSEL  = -1
                        CONLKEY = enumLST[enumSEL].getProperty('key')
                        ruleLST = params.get('rules',{}).get(CONLKEY,[])
                        while not self.monitor.abortRequested() and not CONSEL is None:
                            andLST = [self.listitems.buildMenuListItem('%s|'%(idx+1),FileAccess.dumpJSON(value),icon=DUMMY_ICON.format(text=str(idx+1)),props={'idx':str(idx)}) for idx, value in enumerate(ruleLST)]
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
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value).title(),icon=DUMMY_ICON.format(text=Globals._getAbbr(key.title()))) for key, value in list(params.get('order',{}).items())]
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
        except:
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

        def __getInput():  return self.inputDialog("Enter Value\nSeparate by ',' ex. Action,Comedy",','.join([Globals._unquoteString(value) for value in rule.get('value',[])]))
        def __getBrowse(): return self.browseSources(default='|'.join([Globals._unquoteString(value) for value in rule.get('value',[])]))
        def __getSelect(): return self.notificationDialog(LANGUAGE(32020))
        enumLST = sorted(['Enter', 'Browse', 'Select'])
        enumKEY = {'Enter':{'func':__getInput},'Browse':{'func':__getBrowse},'Select':{'func':__getSelect}}
        enumSEL = self.selectDialog(enumLST,header="Select Input",useDetails=False, multi=False)
        if not enumSEL is None: return [Globals._quoteString(value) for value in (enumKEY[enumLST[enumSEL]].get('func')()).split(',')]
        