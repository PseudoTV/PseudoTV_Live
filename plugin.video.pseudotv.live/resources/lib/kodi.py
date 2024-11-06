#   Copyright (C) 2024 Lunatixz
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
import json, uuid, zlib, base64

from globals     import *
from six.moves   import urllib 
from fileaccess  import FileAccess
from collections import Counter, OrderedDict
from ast         import literal_eval
from contextlib  import contextmanager, closing
from infotagger.listitem import ListItemInfoTag

def getIP(wait=5):
    monitor = MONITOR()
    while not monitor.abortRequested() and wait > 0:
        ip = xbmc.getIPAddress()
        if ip: return ip
        elif monitor.waitForAbort(1.0): break
        else: wait -= 1
    del monitor
        
def convertString2Num(value):
    try:    return literal_eval(value)
    except: return None
    
def encodeString(text):
    base64_bytes = base64.b64encode(zlib.compress(text.encode(DEFAULT_ENCODING)))
    return base64_bytes.decode(DEFAULT_ENCODING)

def decodeString(base64_bytes):
    try:
        message_bytes = zlib.decompress(base64.b64decode(base64_bytes.encode(DEFAULT_ENCODING)))
        return message_bytes.decode(DEFAULT_ENCODING)
    except Exception as e: return ''
        
def getAbbr(text):
    words = text.split(' ')
    if len(words) > 1: return '%s.%s.'%(words[0][0].upper(),words[1][0].upper())
    else: return words[0][0].upper()
   
def getThumb(item={},opt=0): #unify thumbnail artwork
    keys = {0:['landscape','fanart','thumb','thumbnail','poster','clearlogo','logo','logos','clearart','keyart,icon'],
            1:['poster','clearlogo','logo','logos','clearart','keyart','landscape','fanart','thumb','thumbnail','icon']}[opt]
    for key in keys:
        art = (item.get('art',{}).get('album.%s'%(key))       or 
               item.get('art',{}).get('albumartist.%s'%(key)) or 
               item.get('art',{}).get('artist.%s'%(key))      or 
               item.get('art',{}).get('season.%s'%(key))      or 
               item.get('art',{}).get('tvshow.%s'%(key))      or 
               item.get('art',{}).get(key)                    or
               item.get(key) or '')
        if art: return art
    return {0:FANART,1:COLOR_LOGO}[opt]

def setDictLST(lst=[]):
    return [loadJSON(s) for s in list(OrderedDict.fromkeys([dumpJSON(d) for d in lst]))]

def dumpJSON(item, idnt=None, sortkey=False, separators=(',', ':')):
    try:
        if not isinstance(item,str):
            return json.dumps(item, indent=idnt, sort_keys=sortkey, separators=separators)
        elif isinstance(item,str):
            return item
    except Exception as e: log("dumpJSON, failed! %s"%(e), xbmc.LOGERROR)
    return ''
    
def loadJSON(item):
    try:
        if hasattr(item, 'read'):
            return json.load(item)
        elif item and isinstance(item,str):
            return json.loads(item)
        elif item and isinstance(item,dict):
            return item
    except Exception as e: log("loadJSON, failed! %s\n%s"%(e,item), xbmc.LOGERROR)
    return {}
    
def unquoteString(text):
    return urllib.parse.unquote(text)
    
def quoteString(text):
    return urllib.parse.quote(text)

def genUUID(seed=None):
    if seed:
        m = hashlib.md5()
        m.update(seed.encode(DEFAULT_ENCODING))
        return str(uuid.UUID(m.hexdigest()))
    return str(uuid.uuid1(clock_seq=70420))
    
def getMD5(text,hash=0,hexit=True):
    if isinstance(text,dict):     text = dumpJSON(text)
    elif not isinstance(text,str):text = str(text)
    for ch in text: hash = (hash*281 ^ ord(ch)*997) & 0xFFFFFFFF
    if hexit: return hex(hash)[2:].upper().zfill(8)
    else:     return hash

def getCRC32(text):
    return binascii.crc32(text.encode('utf8'))
   
class Settings:
    #Kodi often breaks settings API with changes between versions. Stick with core setsettings/getsettings to avoid specifics; that may break.
    def __init__(self):
        self.cacheDB  = Cache()
        self.cache    = Cache(mem_cache=True)
        self.property = Properties()

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def getRealSettings(self):
        try:    return xbmcaddon.Addon(id=ADDON_ID)#xbmcaddon.Addon('id').getSettings()
        except: return REAL_SETTINGS


    def updateSettings(self):
        self.log('updateSettings')
        #todo build json of third-party addon settings
        # self.pluginMeta.setdefault(addonID,{})['settings'] = [{'key':'value'}]
 
                
    def openGuide(self, instance=ADDON_NAME):
        def __match(label):
            items = jsonRPC.getDirectory({"directory":baseURL}).get('files',[])
            for item in items:
                if label.lower() == item.get('label','').lower(): return item
            for item in items:
                if item.get('label','').lower().startswith(instance.lower()): return item

        with Builtin().busy_dialog():
            from jsonrpc import JSONRPC
            jsonRPC = JSONRPC()
            baseURL = 'pvr://channels/tv/'
            for name in ['%s [All channels]'%(instance), instance, 'All channels']:
                item = __match(name)
                if item: break
            del jsonRPC
            if not item: item = {'file':baseURL}
        self.log('openGuide, opening %s'%(item.get('file',baseURL)))
        Builtin().executebuiltin("Dialog.Close(all)") 
        Builtin().executebuiltin("ReplaceWindow(TVGuide,%s)"%(item.get('file',baseURL)))
                
        
    def openSettings(self):
        self.log('openSettings')
        REAL_SETTINGS.openSettings()
    
    
    #GET
    def _getSetting(self, func, key):
        try: 
            value = func(key)
            self.log('%s, key = %s, value = %s'%(func.__name__,key,'%s...'%((str(value)[:128]))))
            return value
        except Exception as e: 
            self.log("_getSetting, failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
      
      
    def getSetting(self, key):
        return self._getSetting(self.getRealSettings().getSetting,key)
        
        
    def getSettingBool(self, key):
        return self.getSetting(key).lower() == "true" 


    def getSettingBoolList(self, key):
        return [value.lower() == "true" for value in self.getSetting(key).split('|')]


    def getSettingInt(self, key):
        return convertString2Num(self.getSetting(key))
              
              
    def getSettingIntList(self, key):
        return [convertString2Num(value) for value in self.getSetting(key).split('|')]
              
              
    def getSettingNumber(self, key): 
        return convertString2Num(self.getSetting(key))
        

    def getSettingNumberList(self, key):
        return [convertString2Num(value) for value in self.getSetting(key).split('|')]
        

    def getSettingString(self, key):
        return self.getSetting(key)
  
  
    def getSettingList(self, key):
        return [value for value in self.getSetting(key).split('|')]
       
       
    def getSettingFloat(self, key):
        return convertString2Num(self.getSetting(key))
              
              
    def getSettingFloatList(self, key):
        return [convertString2Num(value) for value in self.getSetting(key).split('|')]
        

    def getSettingDict(self, key):
        return loadJSON(decodeString(self.getSetting(key)))
    
    
    def getCacheSetting(self, key, checksum=1, json_data=False, revive=True):
        if revive: return self.setCacheSetting(key, self.cache.get(key, checksum, json_data), checksum, json_data=json_data)
        else:      return self.cache.get(key, checksum, json_data)
        
        
    #SET
    def _setSetting(self, func, key, value):
        try:
            self.log('%s, key = %s, value = %s'%(func.__name__,key,'%s...'%((str(value)[:128]))))
            return func(key, value)
        except Exception as e: 
            self.log("_setSetting, failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
            return False
            
        
    def setSetting(self, key, value=""):  
        if not isinstance(value,str): value = str(value)
        if self.getSetting(key) != value: #Kodi setsetting() can tax system performance. i/o issue? block redundant saves.
            return self._setSetting(self.getRealSettings().setSetting,key,value)
            
            
    def setSettingBool(self, key, value):
        return self.setSetting(key,value)
        
                      
    def setSettingBoolList(self, key, value):
        return self.setSetting(key,('|').join(value))
        
           
    def setSettingInt(self, key, value):  
        return self.setSetting(key,value)
        
        
    def setSettingIntList(self, key, value):  
        return self.setSetting(key,('|').join(value))
         
            
    def setSettingNumber(self, key, value):  
        return self.setSetting(key,value)
        
            
    def setSettingNumberList(self, key, value):  
        return self.setSetting(key,('|').join(value))
        
            
    def setSettingString(self, key, value):  
        return self.setSetting(key,value)
        

    def setSettingList(self, key, values):
        return self.setSetting(key,('|').join(value))
                   
                   
    def setSettingFloat(self, key, value):  
        return self.setSetting(key,value)
        
        
    def setSettingDict(self, key, values):
        return self.setSetting(key,encodeString(dumpJSON(values)))
            
            
    def setCacheSetting(self, key, value, checksum=1, life=datetime.timedelta(days=84), json_data=False):
        return self.cache.set(key, value, checksum, life, json_data)
            

    def getEXTMeta(self, id):
        addon = xbmcaddon.Addon(id)
        properties = ['name', 'version', 'summary', 'description', 'path', 'author', 'icon', 'disclaimer', 'fanart', 'changelog', 'id', 'profile', 'stars', 'type']
        for property in properties: yield (property, addon.getAddonInfo(property))


    def getEXTSetting(self, id, key):
        return xbmcaddon.Addon(id).getSetting(key)
        
        
    def setEXTSetting(self, id, key, value):
        return xbmcaddon.Addon(id).setSetting(key,value)


    def getFriendlyName(self):
        friendly = self.getCacheSetting('Friendly_Name')
        if not friendly:
            from jsonrpc import JSONRPC
            jsonRPC  = JSONRPC()
            friendly = self.setCacheSetting('Friendly_Name',jsonRPC.InputFriendlyName())
            del jsonRPC
        return friendly


    def getMYUUID(self):
        uuid = self.getCacheSetting('MY_UUID')
        if not uuid: uuid = self.setCacheSetting('MY_UUID',genUUID(seed=self.getFriendlyName()))
        return uuid


    @cacheit(expiration=datetime.timedelta(minutes=5), json_data=True)
    def getBonjour(self):
        self.log("getBonjour")
        payload = {'id'      :ADDON_ID,
                   'uuid'    :self.getMYUUID(),
                   'version' :ADDON_VERSION,
                   'machine' :platform.machine(),
                   'platform':Builtin().getInfoLabel('OSVersionInfo','System'),
                   'build'   :Builtin().getInfoLabel('BuildVersion','System'),
                   'name'    :self.getFriendlyName(),
                   'host'    :self.property.getRemoteURL()}
        payload['updated'] = datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
        payload['md5']     = getMD5(dumpJSON(payload))
        return payload
    
    
    @cacheit(expiration=datetime.timedelta(minutes=5), json_data=True)
    def getPayload(self, inclMeta: bool=False):
        self.log("getPayload, inclMeta! %s"%(inclMeta))
        def __getMeta(payload):
            from m3u        import M3U
            from xmltvs     import XMLTVS
            from library    import Library
            from multiroom  import Multiroom
            try:
                payload['library']  = Library().getLibrary()
                payload['m3u']      = M3U().getM3U()
                payload['xmltv']    = {'stations':XMLTVS().getChannels(), 'recordings':XMLTVS().getRecordings()}
                payload['debug']    = loadJSON(self.property.getEXTProperty('%s.debug.log'%(ADDON_NAME))).get('DEBUG',{})
                payload['servers']  = Multiroom().getDiscovery()
            except Exception as e: self.log("getPayload, __getMeta failed! %s"%(e), xbmc.LOGERROR)
            return payload
            
        from channels   import Channels
        payload = self.getBonjour()
        payload['remotes']   = {'remote':'http://%s/%s'%(payload['host'],REMOTEFLE),
                                'm3u'   :'http://%s/%s'%(payload['host'],M3UFLE),
                                'xmltv' :'http://%s/%s'%(payload['host'],XMLTVFLE),
                                'genre' :'http://%s/%s'%(payload['host'],GENREFLE)}
        payload['settings']  = {'Resource_Logos'    :self.getSetting('Resource_Logos').split('|'),
                                'Resource_Bumpers'  :self.getSetting('Resource_Bumpers').split('|'),
                                'Resource_Ratings'  :self.getSetting('Resource_Ratings').split('|'),
                                'Resource_Adverts'  :self.getSetting('Resource_Adverts').split('|'),
                                'Resource_Trailers' :self.getSetting('Resource_Trailers').split('|')}
        payload['channels']  = Channels().getChannels()
        if inclMeta: payload = __getMeta(payload)
        payload['updated']   = datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
        payload['md5']       = getMD5(dumpJSON(payload))
        return payload


    @cacheit(expiration=datetime.timedelta(minutes=5))
    def getPayloadUI(self):
        from json2html import Json2Html
        return Json2Html().convert(self.getPayload(inclMeta=True))


    def IPTV_SIMPLE_SETTINGS(self): #recommended IPTV Simple settings
        return {'kodi_addon_instance_name'      :ADDON_NAME,
                'kodi_addon_instance_enabled'   :'false',
                'm3uPathType'                   :'0',
                'm3uPath'                       :'0',
                'm3uUrl'                        :'0',
                'm3uCache'                      :'true',
                'startNum'                      :'1',
                'numberByOrder'                 :'false',
                'm3uRefreshMode'                :'1',
                'm3uRefreshIntervalMins'        :'15',
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
                'epgPath'                       :'0',
                'epgUrl'                        :'0',
                'epgCache'                      :'true',
                'genresPathType'                :'0',
                'genresPath'                    :'0',
                'genresUrl'                     :'0',
                'logoPathType'                  :'0',
                'logoPath'                      :LOGO_LOC,
                'mediaTitleSeasonEpisode'       :'true',
                'timeshiftEnabled'              :'false',
                'catchupEnabled'                :'true',
                'catchupPlayEpgAsLive'          :'false',
                'catchupWatchEpgEndBufferMins'  :'0',
                'catchupWatchEpgBeginBufferMins':'0'}


    def setPVRPath(self, path, instance=ADDON_NAME, prompt=False, force=False):
        settings  = self.IPTV_SIMPLE_SETTINGS()
        nsettings = {'m3uPathType'                :'0',
                     'm3uPath'                    :os.path.join(path,M3UFLE),
                     'epgPathType'                :'0',
                     'epgPath'                    :os.path.join(path,XMLTVFLE),
                     'genresPathType'             :'0',
                     'genresPath'                 :os.path.join(path,GENREFLE),
                     'kodi_addon_instance_name'   : '%s - %s'%(ADDON_NAME,instance),
                     'kodi_addon_instance_enabled':'true'}
        settings.update(nsettings)
        self.log('setPVRPath, new settings = %s'%(nsettings))
        if self.hasPVRInstance(instance) and not force:
            return self.log('setPVRPath, instance (%s) settings exists.'%(instance))
        return self.chkPluginSettings(PVR_CLIENT_ID,settings,instance,prompt)
        
        
    def setPVRRemote(self, host, instance=ADDON_NAME, prompt=False):
        settings  = self.IPTV_SIMPLE_SETTINGS()
        nsettings = {'m3uPathType'                :'1',
                     'm3uUrl'                     :'http://%s/%s'%(host,M3UFLE),
                     'epgPathType'                :'1',
                     'epgUrl'                     :'http://%s/%s'%(host,XMLTVFLE),
                     'genresPathType'             :'1',
                     'genresUrl'                  :'http://%s/%s'%(host,GENREFLE),
                     'kodi_addon_instance_name'   : '%s - %s'%(ADDON_NAME,instance),
                     'kodi_addon_instance_enabled':'true'}
        settings.update(nsettings)
        self.log('setPVRRemote, new settings = %s'%(nsettings))
        return self.chkPluginSettings(PVR_CLIENT_ID,settings,instance,prompt)
        
        
    def hasPVRInstance(self, instance=ADDON_NAME):
        instancePath = os.path.join(PVR_CLIENT_LOC,'instance-settings-%s.xml'%(self.gePVRInstance(instance)))
        if FileAccess.exists(instancePath): 
            self.log('hasPVRInstance, instance = %s, instancePath = %s'%(instance, instancePath))
            return instancePath
        
        
    def setPVRInstance(self, instance=ADDON_NAME):
        # todo https://github.com/xbmc/xbmc/pull/23648
        if   not self.getSettingBool('Enable_PVR_SETTINGS'): Dialog().notificationDialog(LANGUAGE(32186))
        elif not FileAccess.exists(os.path.join(PVR_CLIENT_LOC,'settings.xml')):
            self.log('setPVRInstance, creating missing default settings.xml')
            return self.chkPluginSettings(PVR_CLIENT_ID,self.IPTV_SIMPLE_SETTINGS(),False)
        else:
            newFile = os.path.join(PVR_CLIENT_LOC,'instance-settings-%s.xml'%(self.gePVRInstance(instance)))
            if FileAccess.exists(newFile): FileAccess.delete(newFile)
            else: #todo remove after migration to new instances
                pvrFile = self.chkPVRInstance(instance)
                if pvrFile: FileAccess.delete(pvrFile)
            #new instance settings
            self.log('setPVRInstance, creating %s'%(newFile))
            return FileAccess.move(os.path.join(PVR_CLIENT_LOC,'settings.xml'),newFile)
           
        
    def gePVRInstance(self, instance=ADDON_NAME):
        return int(re.sub("[^0-9]", "", getMD5(instance))) * 2
        
        
    def chkPVRInstance(self, instance=ADDON_NAME):
        found   = False
        monitor = MONITOR()
        for file in [filename for filename in FileAccess.listdir(PVR_CLIENT_LOC)[1] if filename.endswith('.xml')]:
            if monitor.waitForAbort(.0001): break
            elif file.startswith('instance-settings-'):
                try:
                    xml = FileAccess.open(os.path.join(PVR_CLIENT_LOC,file), "r")
                    txt = xml.read()
                    xml.close()
                except Exception as e:
                    self.log('chkPVRInstance, path = %s, failed to open file = %s\n%s'%(PVR_CLIENT_LOC,file,e))
                    continue
                        
                match = re.compile('<setting id=\"kodi_addon_instance_name\" default=\"true\">(.*?)\</setting>', re.IGNORECASE).search(txt)
                try: name = match.group(1)
                except:
                    match = re.compile('<setting id=\"kodi_addon_instance_name\">(.*?)\</setting>', re.IGNORECASE).search(txt)
                    try:    name = match.group(1)
                    except: name = None
                    
                if name == instance:
                    if found ==  False: found = os.path.join(PVR_CLIENT_LOC,file)
                    else: #auto remove any duplicate entries with the same instance name.
                        FileAccess.delete(os.path.join(PVR_CLIENT_LOC,file))
                        self.log('chkPVRInstance, removing duplicate entry %s'%(file))
                self.log('chkPVRInstance, found %s file = %s'%(name,found))
        del monitor
        return found


    @cacheit(expiration=datetime.timedelta(minutes=5),json_data=True)
    def getPVRInstanceSettings(self, instance):
        instancePath = self.hasPVRInstance(instance)
        if instancePath:
            fle = FileAccess.open(instancePath,'r')
            lines = fle.readlines()
            fle.close()
            settings = dict()
            for line in lines:
                if not 'id=' in line: continue
                #todo refactor using proper minidom
                match = re.compile('<setting id=\"(.*)\" default=\"(.*)\">(.*?)\</setting>', re.IGNORECASE).search(line)
                try: settings.update({match.group(1):(match.group(2),match.group(3))})
                except:
                    match = re.compile('<setting id=\"(.*)\">(.*?)\</setting>', re.IGNORECASE).search(line)
                    try: settings.update({match.group(1):('',match.group(2))})
                    except:
                        match = re.compile('<setting id=\"(.*)\" default=\"(.*?)\" />', re.IGNORECASE).search(line)
                        try: settings.update({match.group(1):(match.group(2),None)})
                        except: pass
            self.log('getPVRInstanceSettings, returning instance = %s\n%s'%(instance,settings))
            return settings
        
        
    def chkPluginSettings(self, id, nsettings, instance=ADDON_NAME, prompt=False):
        self.log('chkPluginSettings, id = %s, instance = %s, prompt=%s'%(id,instance,prompt))
        addon   = xbmcaddon.Addon(id)
        dialog  = Dialog()
        monitor = MONITOR()
        if addon is None: dialog.notificationDialog(LANGUAGE(32034)%(id))
        else:
            changes = {}
            name = addon.getAddonInfo('name')
            osettings = (self.getPVRInstanceSettings(instance) or {})
            for setting, newvalue in list(nsettings.items()):
                if monitor.waitForAbort(.0001): return False
                default, oldvalue = osettings.get(setting,(None,None))
                if str(newvalue).lower() != str(oldvalue).lower(): 
                    changes[setting] = (oldvalue, newvalue)
                
            if not changes:
                self.log('chkPluginSettings, no changes detected!')
                return False
            elif prompt:
                dialog.textviewer('%s\n\n%s'%((LANGUAGE(32035)%(name)),('\n'.join(['Modifying %s: [COLOR=dimgray][B]%s[/B][/COLOR] => [COLOR=green][B]%s[/B][/COLOR]'%(setting,newvalue[0],newvalue[1]) for setting, newvalue in list(changes.items())]))))
                if not dialog.yesnoDialog((LANGUAGE(32036)%name)): 
                    dialog.notificationDialog(LANGUAGE(32046))
                    return False
                
            for s, v in list(changes.items()):
                if monitor.waitForAbort(.0001): return False
                addon.setSetting(s, v[1])
                self.log('chkPluginSettings, setting = %s, current value = %s => %s'%(s,oldvalue,v[1]))
            self.setPVRInstance(instance)
            dialog.notificationDialog((LANGUAGE(32037)%(name)))
            del dialog
            return True
        del dialog
        del monitor
        

    def getCurrentSettings(self):
        self.log('getCurrentSettings')
        settings = ['User_Folder']
        for setting in settings:
            yield (setting,self.getSetting(setting))
               
        
class Properties:
    
    def __init__(self, winID=10000):
        self.winID      = winID
        self.window     = xbmcgui.Window(winID)
        self.InstanceID = self.getInstanceID()


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def clrInstanceID(self):
        instanceID = self.getEXTProperty('%s.InstanceID'%(ADDON_ID))
        if instanceID: self.clearTrash(instanceID)
        self.clearEXTProperty('%s.InstanceID'%(ADDON_ID))


    def setInstanceID(self):
        self.clrInstanceID()
        return self.setEXTProperty('%s.InstanceID'%(ADDON_ID),getMD5(uuid.uuid4()))


    def getInstanceID(self):
        instanceID = self.getEXTProperty('%s.InstanceID'%(ADDON_ID))
        if not instanceID: instanceID = self.setInstanceID()
        return instanceID


    def getRemoteURL(self):
        remote = self.getProperty('%s.Remote_URL'%(ADDON_ID))
        if not remote: remote = self.setRemoteURL(Settings().getSettingInt('TCP_PORT'))
        return remote


    def setRemoteURL(self, value):
        return self.setProperty('%s.Remote_URL'%(ADDON_ID),value)
        

    def hasFirstrun(self):
        return self.getEXTProperty('%s.has.Firstrun'%(ADDON_ID))
        
        
    def setFirstrun(self, state=True):
        return self.setEXTProperty('%s.has.Firstrun'%(ADDON_ID),state) == "true"
               

    def isRunning(self, key):
        return self.getEXTProperty('%s.Running.%s'%(ADDON_ID,key)) == 'true'


    def getLegacy(self):
        return self.getEXTProperty('PseudoTVRunning') == 'True'


    def forceUpdateTime(self, key):
        return self.setPropertyInt(key,0)


    def setEpochTimer(self, key, state=True):
        return self.setEXTProperty('%s.%s'%(ADDON_ID,key),str(state).lower())


    def setAutotuned(self, state=True):
        return self.setEXTProperty('%s.has.Autotuned'%(ADDON_ID),str(state).lower())


    def setChannels(self, state=True):
        return self.setEXTProperty('%s.has.Channels'%(ADDON_ID),str(state).lower())


    def setBackup(self, state=True):
        return self.setEXTProperty('%s.has.Backup'%(ADDON_ID),str(state).lower())


    def setServers(self, state=True):
        return self.setEXTProperty('%s.has.Servers'%(ADDON_ID),str(state).lower())
        
        
    def setEnabledServers(self, state=True):
        return self.setEXTProperty('%s.has.Enabled_Servers'%(ADDON_ID),str(state).lower())
        
        
    def setPendingRestart(self, state=True):
        if state: Dialog().notificationDialog('%s\n%s'%(LANGUAGE(32157),LANGUAGE(32124)))
        return self.setPropertyBool('pendingRestart',state)
        

    def setPendingInterrupt(self, state=True):
        return self.setPropertyBool('pendingInterrupt',state)

        
    def setPendingSuspend(self, state=True):
        return self.setPropertyBool('pendingSuspend',state)
        
                
    def setRestart(self, state=True):
        return self.setPropertyBool('Restart',state)
        

    def setInterrupt(self, state=True):
        return self.setPropertyBool('Interrupt',state)

        
    def setSuspend(self, state=True):
        return self.setPropertyBool('Suspend',state)
        
        
    def isPseudoTVRunning(self):
        return self.getEXTProperty('PseudoTVRunning') == 'true'


    @contextmanager
    def legacy(self):
        monitor = MONITOR()
        while not monitor.abortRequested() and self.isPseudoTVRunning():
            if monitor.waitForAbort(.0001): break
        del monitor
        self.setEXTProperty('PseudoTVRunning','true')
        try: yield
        finally: self.setEXTProperty('PseudoTVRunning','false')


    @contextmanager
    def setRunning(self, key):
        monitor = MONITOR()
        while not monitor.abortRequested() and self.isRunning(key):
            if monitor.waitForAbort(.0001): break
        del monitor
        self.setEXTProperty('%s.Running.%s'%(ADDON_ID,key),'true')
        try: yield
        finally: self.setEXTProperty('%s.Running.%s'%(ADDON_ID,key),'false')


    @contextmanager
    def interruptActivity(self): #suspend/quit running background task.
        if not self.isPendingInterrupt():
            self.setPendingInterrupt(True)
            try: yield
            finally: self.setPendingInterrupt(False)
        else: yield
        
        
    @contextmanager
    def suspendActivity(self): #suspend/quit running background task.
        if not self.isPendingSuspend():
            self.setPendingSuspend(True)
            try: yield
            finally: self.setPendingSuspend(False)
        else: yield

        
    def hasAutotuned(self):
        return self.getEXTProperty('%s.has.Autotuned'%(ADDON_ID)) == "true"
        
        
    def hasChannels(self):
        return self.getEXTProperty('%s.has.Channels'%(ADDON_ID)) == "true"


    def hasBackup(self):
        return self.getEXTProperty('%s.has.Backup'%(ADDON_ID)) == "true"
        

    def hasServers(self):
        return self.getEXTProperty('%s.has.Servers'%(ADDON_ID)) == "true"
        
        
    def hasEnabledServers(self):
        return self.getEXTProperty('%s.has.Enabled_Servers'%(ADDON_ID)) == "true"
        
        
    def isPendingInterrupt(self):
        return self.getPropertyBool('pendingInterrupt')


    def isPendingRestart(self):
        return self.getPropertyBool('pendingRestart')

        
    def isPendingSuspend(self):
        return self.getPropertyBool('pendingSuspend')
        
        
    def isInterrupt(self):
        return self.getPropertyBool('Interrupt')


    def isRestart(self):
        return self.getPropertyBool('Restart')

        
    def isSuspend(self):
        return self.getPropertyBool('Suspend')
        
        
    def getKey(self, key, instanceID=True):
        if not isinstance(key,str): key = str(key)
        if self.winID == 10000 and not key.startswith(ADDON_ID): #create unique id 
            if instanceID: return self.setTrash('%s.%s.%s'%(ADDON_ID,key,self.InstanceID))
            else:          return '%s.%s'%(ADDON_ID,key)
        return key

        
    #CLEAR
    def clearEXTProperty(self, key):
        self.log('clearEXTProperty, id = %s, key = %s'%(10000,key))
        return xbmcgui.Window(10000).clearProperty(key)
        
        
    def clearProperties(self):
        self.log('clearProperties')
        return self.window.clearProperties()
        
        
    def clearProperty(self, key):
        key = self.getKey(key)
        self.log('clearProperty, id = %s, key = %s'%(self.winID,key))
        return self.window.clearProperty(key)


    #GET
    def getEXTProperty(self, key):
        value = xbmcgui.Window(10000).getProperty(key)
        self.log('getEXTProperty, id = %s, key = %s, value = %s'%(10000,key,'%s...'%(str(value)[:128])))
        return value
        
        
    def getProperty(self, key):
        key   = self.getKey(key)
        value = self.window.getProperty(key)
        self.log('getProperty, id = %s, key = %s, value = %s'%(self.winID,key,'%s...'%(str(value)[:128])))
        return value
        
        
    def getPropertyList(self, key):
        return self.getProperty(key).split('|')

        
    def getPropertyBool(self, key):
        return self.getProperty(key).lower() == "true"
        
        
    def getPropertyDict(self, key=''):
        return loadJSON(decodeString(self.getProperty(key)))
        
        
    def getPropertyInt(self, key):
        return convertString2Num(self.getProperty(key))
            
        
    def getPropertyFloat(self, key):
        return float(convertString2Num(self.getProperty(key)))
        

    #SET
    def setEXTProperty(self, key, value):
        self.log('setEXTProperty, id = %s, key = %s, value = %s'%(10000,key,'%s...'%((str(value)[:128]))))
        xbmcgui.Window(10000).setProperty(key,str(value))
        return value
        
        
    def setProperty(self, key, value):
        key = self.getKey(key)
        self.log('setProperty, id = %s, key = %s, value = %s'%(self.winID,key,'%s...'%((str(value)[:128]))))
        self.window.setProperty(key, str(value))
        return value
        
        
    def setPropertyList(self, key, values):
        return self.setProperty(key, '|'.join(values))
        
        
    def setPropertyBool(self, key, value):
        return self.setProperty(key, value)
        
        
    def setPropertyDict(self, key, value={}):
        return self.setProperty(key, encodeString(dumpJSON(value)))
        
                
    def setPropertyInt(self, key, value):
        return self.setProperty(key, int(value))
                
                
    def setPropertyFloat(self, key, value):
        return self.setProperty(key, float(value))

    
    def setTrash(self, key): #catalog instance properties that may become abandoned. 
        tmpDCT = loadJSON(self.getEXTProperty('%s.TRASH'%(ADDON_ID)))
        if key not in tmpDCT.setdefault(self.InstanceID,[]):
            tmpDCT.setdefault(self.InstanceID,[]).append(key)
        self.setEXTProperty('%s.TRASH'%(ADDON_ID),dumpJSON(tmpDCT))
        return key

        
    def clearTrash(self, instanceID=None): #clear abandoned properties after instanceID change
        self.log('clearTrash, instanceID = %s'%(instanceID))
        tmpDCT = loadJSON(self.getEXTProperty('%s.TRASH'%(ADDON_ID)))
        for prop in tmpDCT.get(instanceID,[]): self.clearEXTProperty(prop)


    def __exit__(self):
        self.log('__exit__')
        self.clearTrash()
        
        
class ListItems:
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def getListItem(self, label='', label2='', path='', offscreen=False):
        return xbmcgui.ListItem(label,label2,path,offscreen)


    def infoTagVideo(self, offscreen=False):
        return xbmc.InfoTagVideo(offscreen)


    def InfoTagMusic(self, offscreen=False):
        return xbmc.InfoTagVideo(offscreen)
        

    def buildItemListItem(self, item, media='video', oscreen=False, playable=True):
        info       = item.copy()
        art        = (info.pop('art'              ,{}) or {})
        cast       = (info.pop('cast'             ,[]) or [])
        uniqueid   = (info.pop('uniqueid'         ,{}) or {})
        streamInfo = (info.pop('streamdetails'    ,{}) or {})
        properties = (info.pop('customproperties' ,{}) or {})
        if 'citem'   in info: properties.update({'citem'  :info.pop('citem')})   # write dump to single key
        if 'pvritem' in info: properties.update({'pvritem':info.pop('pvritem')}) # write dump to single key
        
        if media != 'video': #unify default artwork for music.
            art['poster'] = getThumb(info,opt=1)
            art['fanart'] = getThumb(info)
            
        listitem = self.getListItem(info.pop('label',''), info.pop('label2',''), info.pop('file',''), offscreen=oscreen)
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
             
                     
    def buildMenuListItem(self, label="", label2="", icon=COLOR_LOGO, url="", info={}, art={}, props={}, oscreen=False, media='video'):
        if not art: art = {'thumb':icon,'logo':icon,'icon':icon}
        listitem = self.getListItem(label, label2, url, offscreen=oscreen)
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
                    except Exception as e: self.log("buildItemListItem, cleanInfo error! %s\nkey = %s, value = %s, type = %s\n%s"%(e,key,value,type,ninfo), xbmc.LOGWARNING)
                     
            if isinstance(ninfo[key],list):
                for n in ninfo[key]:
                    if isinstance(n,dict): n, properties = self.cleanInfo(n,media,properties)
            if isinstance(ninfo[key],dict): ninfo[key], properties = self.cleanInfo(ninfo[key],media,properties)
        return ninfo, properties


    def cleanProp(self, pvalue):
        if isinstance(pvalue,dict):      return dumpJSON(pvalue)
        elif isinstance(pvalue,list):    return '|'.join(map(str, pvalue))
        elif not isinstance(pvalue,str): return str(pvalue)
        else:                            return pvalue
            
    
class Builtin:
    def __init__(self):
        ...

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
         
     
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
                
                
    def hasSubtitle(self):
        return self.getInfoBool('HasSubtitles','VideoPlayer')


    def isSubtitle(self):
        return self.getInfoBool('SubtitlesEnabled','VideoPlayer')


    def isPlaylistRandom(self):
        return self.getInfoLabel('Random','Playlist').lower() == 'on' # Disable auto playlist shuffling if it's on
        
        
    def isPlaylistRepeat(self):
        return self.getInfoLabel('IsRepeat','Playlist').lower() == 'true' # Disable auto playlist repeat if it's on #todo


    def isPaused(self):
        return self.getInfoBool('Player.Paused')
                
                
    def isBusyDialog(self):
        return (self.getInfoBool('IsActive(busydialognocancel)','Window') | self.getInfoBool('IsActive(busydialog)','Window'))


    def closeBusyDialog(self):
        if self.getInfoBool('IsActive(busydialognocancel)','Window'):
            self.executebuiltin('Dialog.Close(busydialognocancel)')
        elif self.getInfoBool('IsActive(busydialog)','Window'):
            self.executebuiltin('Dialog.Close(busydialog)')


    @contextmanager
    def busy_dialog(self, isPlaying=False):
        if not self.isBusyDialog() and not isPlaying:
            self.executebuiltin('ActivateWindow(busydialognocancel)')
            try: yield
            finally:
                self.executebuiltin('Dialog.Close(busydialognocancel)')
        else: yield
       

    def getInfoLabel(self, key, param='ListItem', timeout=EPOCH_TIMER):
        monitor = MONITOR()
        value   = xbmc.getInfoLabel('%s.%s'%(param,key))
        while not monitor.abortRequested() and (value is None or value == 'Busy'):
            if monitor.waitForAbort(.0001) or timeout < 0: break
            timeout -= .0001
            value = xbmc.getInfoLabel('%s.%s'%(param,key))
        self.log('getInfoLabel, key = %s.%s, value = %s, time = %s'%(param,key,value,(EPOCH_TIMER-timeout)))
        del monitor
        return value
        
        
    def getInfoBool(self, key, param='Library', default=False):
        value = (xbmc.getCondVisibility('%s.%s'%(param,key)) or default)
        self.log('getInfoBool, key = %s.%s, value = %s'%(param,key,value))
        return value
        
    
    def executebuiltin(self, key, wait=False):
        self.log('executebuiltin, key = %s, wait = %s'%(key,wait))
        xbmc.executebuiltin('%s'%(key),wait)
        return True
        
        
class Dialog:
    settings   = Settings()
    properties = Properties()
    listitems  = ListItems()
    builtin    = Builtin()
    
    def __init__(self):
        self.settings.dialog = self
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def toggleInfoMonitor(self, state, wait=0.1):
        self.log('toggleInfoMonitor, state = %s'%(state))
        if self.properties.setPropertyBool('chkInfoMonitor',state): 
            self.properties.clearProperty('monitor.montiorList')
            timerit(self.doInfoMonitor)(0.1)


    def doInfoMonitor(self):
        monitor = MONITOR()
        while not monitor.abortRequested():
            if not self.fillInfoMonitor() or monitor.waitForAbort(0.5): break
        del monitor
            

    def fillInfoMonitor(self, type='ListItem'):
        #todo catch full listitem not singular properties.
        try:
            if not self.properties.getPropertyBool('chkInfoMonitor'): return False
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
                montiorList.insert(0,item)
                self.setInfoMonitor(montiorList)
            return True
        except Exception as e:
            self.log("fillInfoMonitor, failed! %s"%(e), xbmc.LOGERROR)
            return False


    def getInfoMonitor(self):
        return self.properties.getPropertyDict('monitor.montiorList').get('info',[])
    
    
    def setInfoMonitor(self, items):
        return self.properties.setPropertyDict('monitor.montiorList',{'info':list(setDictLST(items))})


    def colorDialog(self, colorlist=[], preselect="", colorfile="", heading=ADDON_NAME):
        return xbmcgui.Dialog().colorpicker(heading, preselect, colorfile, colorlist)
    
    
    def _closeOkDialog(self):
        if self.builtin.getInfoBool('IsActive(okdialog)','Window'):
            self.builtin.executebuiltin('Dialog.Close(okdialog)')
        
        
    def _okDialog(self, msg, heading, autoclose, url):
        timerit(self.okDialog)(0.5,[msg, heading, autoclose])


    def okDialog(self, msg, heading=ADDON_NAME, autoclose=AUTOCLOSE_DELAY, usethread=False):
        if usethread: return self._okDialog(msg, heading, autoclose)
        else:
            if autoclose > 0: timerit(self._closeOkDialog)(autoclose)
            return xbmcgui.Dialog().ok(heading, msg)


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
                try: 
                    if self.acThread.is_alive():
                        self.acThread.cancel()
                        self.acThread.join()
                except: pass
                self.close()

        if not self.properties.isRunning('qrDialog'):
            with self.properties.setRunning('qrDialog'):
                with self.builtin.busy_dialog():
                    imagefile = os.path.join(FileAccess.translatePath(TEMP_LOC),'%s.png'%(getMD5(str(url.split('/')[-1]))))
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
        
        
    def _textViewer(self, msg, heading, usemono, autoclose):
        timerit(self.textviewer)(0.5,[msg, heading, usemono, autoclose])
        
        
    def textviewer(self, msg, heading=ADDON_NAME, usemono=False, autoclose=AUTOCLOSE_DELAY, usethread=False):
        if usethread: return self._textViewer(msg, heading, usemono, autoclose)
        else:
            if autoclose > 0: timerit(self._closeTextViewer)(autoclose)
            xbmcgui.Dialog().textviewer(heading, msg, usemono)
            return True
            
        
    def yesnoDialog(self, message, heading=ADDON_NAME, nolabel='', yeslabel='', customlabel='', autoclose=AUTOCLOSE_DELAY): 
        if customlabel:
            # Returns the integer value for the selected button (-1:cancelled, 0:no, 1:yes, 2:custom)
            return xbmcgui.Dialog().yesnocustom(heading, message, customlabel, nolabel, yeslabel, (autoclose*1000))
        else: 
            # Returns True if 'Yes' was pressed, else False.
            return xbmcgui.Dialog().yesno(heading, message, nolabel, yeslabel, (autoclose*1000))


    def _notificationWait(self, message, header, wait):
        timerit(self.notificationWait)(0.5,[message, header, wait])


    def notificationWait(self, message, header=ADDON_NAME, wait=4, usethread=False):
        if usethread: return self._notificationWait(message, header, wait)
        else:
            pDialog = self.progressBGDialog(message=message,header=header)
            for idx in range(int(wait)):
                pDialog = self.progressBGDialog((((idx+1) * 100)//int(wait)),control=pDialog,header=header)
                if pDialog is None or MONITOR().waitForAbort(1.0): break
            if hasattr(pDialog, 'close'): pDialog.close()
        return True


    def progressBGDialog(self, percent=0, control=None, message='', header=ADDON_NAME, silent=None):
        # if silent is None and self.settings.getSettingBool('Silent_OnPlayback'): 
            # silent = (self.properties.getPropertyBool('OVERLAY') | self.builtin.getInfoBool('Playing','Player'))
        
        # if silent:
            # if hasattr(control, 'close'): control.close()
            # self.log('progressBGDialog, silent = %s; closing dialog'%(silent))
            # return 
            
        if control is None and int(percent) == 0:
            control = xbmcgui.DialogProgressBG()
            control.create(header, message)
        elif control:
            if int(percent) == 100 or control.isFinished(): 
                if hasattr(control, 'close'):
                    control.close()
                    return None
            elif hasattr(control, 'update'):  control.update(int(percent), header, message)
        return control
        

    def progressDialog(self, percent=0, control=None, message='', header=ADDON_NAME):
        if control is None and int(percent) == 0:
            control = xbmcgui.DialogProgress()
            control.create(header, message)
        elif control:
            if int(percent) == 100 or control.iscanceled(): 
                if hasattr(control, 'close'):
                    control.close()
                    return None
            elif hasattr(control, 'update'):  control.update(int(percent), message)
        return control
        
   
    def infoDialog(self, listitem):
        xbmcgui.Dialog().info(listitem)
        

    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=PROMPT_DELAY, icon=COLOR_LOGO):
        self.log('notificationDialog: %s'%(message))
        ## - Builtin Icons:
        ## - xbmcgui.NOTIFICATION_INFO
        ## - xbmcgui.NOTIFICATION_WARNING
        ## - xbmcgui.NOTIFICATION_ERROR
        try:    xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except: self.builtin.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True
             
             
    def selectDialog(self, list, header=ADDON_NAME, preselect=None, useDetails=True, autoclose=SELECT_DELAY, multi=True, custom=False):
        if multi == True:
            if preselect is None: preselect = [-1]
            if custom: ... #todo domodel custom selectDialog for library select.
            else:
                select = xbmcgui.Dialog().multiselect(header, list, (autoclose*1000), preselect, useDetails)
        else:
            if preselect is None: preselect = -1
            if custom: ... #todo domodel custom selectDialog for library select.
            else:
                select = xbmcgui.Dialog().select(header, list, (autoclose*1000), preselect, useDetails)
                if select == -1:  select = None
        return select
      
      
    def inputDialog(self, message, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
        ## - xbmcgui.INPUT_ALPHANUM (standard keyboard)
        ## - xbmcgui.INPUT_NUMERIC (format: #)
        ## - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
        ## - xbmcgui.INPUT_TIME (format: HH:MM)
        ## - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
        ## - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
        return xbmcgui.Dialog().input(message, default, key, opt, close)
        

    def browseDialog(self, type=0, heading=ADDON_NAME, default='', shares='', mask='', options=[], exclude=None, useThumbs=True, treatAsFolder=False, prompt=True, multi=False, monitor=False):
        self.log('browseDialog, type = %s, heading= %s, shares= %s, useThumbs= %s, treatAsFolder= %s, default= %s\nmask= %s, options= %s, exclude= %s'%(type,heading,shares,useThumbs,treatAsFolder,default,mask,options,exclude))
        def __buildMenuItem(option):
            return self.listitems.buildMenuListItem(option['label'],option['label2'],DUMMY_ICON.format(text=getAbbr(option['label'])))
             
        def __importSTRM(strm):
            try:
                with self.builtin.busy_dialog():
                    fle = FileAccess.open(strm,'r')
                    paths = [line for line in fle.readlines() if not line.startswith('#') and '://' in line]
                    fle.close()
                select = self.selectDialog(paths, LANGUAGE(32080), useDetails=False, multi=False)
                self.log("browseDialog, __importSTRM strm = %s found = %s"%(strm,paths))
                if not select is None: return paths[select]
            except Exception as e: self.log("browseDialog, __importSTRM failed! %s\n%s"%(e,strm), xbmc.LOGERROR)
             
        with self.builtin.busy_dialog():
            if prompt:
                opts = [{"label":LANGUAGE(32196), "label2":"library://video/"                   , "default":"library://video/"                   , "shares":"video"   , "mask":xbmc.getSupportedMedia('video')   , "type":0    , "multi":multi},
                        {"label":LANGUAGE(32207), "label2":"library://music/"                   , "default":"library://music/"                   , "shares":"music"   , "mask":xbmc.getSupportedMedia('music')   , "type":0    , "multi":multi},
                        {"label":LANGUAGE(32201), "label2":"Images"                             , "default":""                                   , "shares":"pictures", "mask":xbmc.getSupportedMedia('picture') , "type":1    , "multi":False},
                        {"label":LANGUAGE(32194), "label2":"Import paths from STRM"             , "default":""                                   , "shares":"files"   , "mask":".strm"                           , "type":1    , "multi":False},
                        {"label":LANGUAGE(32191), "label2":"special://profile/playlists/video/" , "default":"special://profile/playlists/video/" , "shares":""        , "mask":".xsp"                            , "type":1    , "multi":False},
                        {"label":LANGUAGE(32192), "label2":"special://profile/playlists/music/" , "default":"special://profile/playlists/music/" , "shares":""        , "mask":".xsp"                            , "type":1    , "multi":False},
                        {"label":LANGUAGE(32193), "label2":"special://profile/playlists/mixed/" , "default":"special://profile/playlists/mixed/" , "shares":""        , "mask":".xsp"                            , "type":1    , "multi":False},
                        {"label":LANGUAGE(32195), "label2":"Create Dynamic Smartplaylist"       , "default":""                                   , "shares":""        , "mask":""                                , "type":1    , "multi":False},
                        {"label":LANGUAGE(32206), "label2":".cue,.m3u,.m3u8,.strm,.pls,.wpl"    , "default":""                                   , "shares":""        , "mask":"|".join(ALT_PLAYLISTS)           , "type":1    , "multi":False},
                        {"label":LANGUAGE(32198), "label2":"All Folders & Files"                , "default":""                                   , "shares":"files"   , "mask":mask                              , "type":type , "multi":multi},
                        {"label":LANGUAGE(32199), "label2":"Local Folders & Files"              , "default":""                                   , "shares":"local"   , "mask":mask                              , "type":type , "multi":multi},
                        {"label":LANGUAGE(32200), "label2":"Local Drives and Network Share"     , "default":""                                   , "shares":shares    , "mask":mask                              , "type":type , "multi":multi},
                        {"label":LANGUAGE(32202), "label2":"resource://"                        , "default":"resource://"                        , "shares":shares    , "mask":mask                              , "type":type , "multi":multi}]

                if isinstance(exclude,list): options = [opt for opt in opts if not opt.get('label') in exclude]
                else:                        options = opts
                if default:                  options.insert(0,{"label":LANGUAGE(32203), "label2":default, "default":default, "shares":shares, "mask":mask, "type":type, "multi":multi})
                lizLST = poolit(__buildMenuItem)(options)
                
                select = self.selectDialog(lizLST, LANGUAGE(32089), multi=False)
                if   options[select].get('label') == LANGUAGE(32195): return self.buildDXSP(default)
                elif options[select].get('label') == LANGUAGE(32202): return self.buildResource(default, mask)
                elif select is not None:
                    default   = options[select]['default']
                    shares    = options[select]['shares']
                    mask      = options[select]['mask']
                    type      = options[select]['type']
                    multi     = options[select]['multi']
                else: return
                
        if monitor: self.toggleInfoMonitor(True)
        if multi == True:
            ## https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#ga856f475ecd92b1afa37357deabe4b9e4
            retval = xbmcgui.Dialog().browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        else:
            ## https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#gafa1e339e5a98ae4ea4e3d3bb3e1d028c
            retval = xbmcgui.Dialog().browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)
            if options[select].get('label') == LANGUAGE(32194): retval = __importSTRM(retval)
        if monitor: self.toggleInfoMonitor(False)
        if len(options) > 0 and default == retval: return
        if retval: return retval
        
        
    def buildResource(self, path, exts=xbmc.getSupportedMedia('picture')):
        #Todo parse for image/video list user select.
        # resourcePlugins = {"jsonrpc":"2.0","method":"Addons.GetAddons","params":{"type":"kodi.resource.images","content":"video","properties":["path"]} .get('addons',[])
        # "addons": [
        # {
            # "addonid": "resource.images.overlays.crttv",
            # "path": "C:\\Program Files\\Kodi\\portable_data\\addons\\resource.images.overlays.crttv\\",
            # "type": "kodi.resource.images"
        # },
        # # special://home/addons/resource.images.overlays.crttv/resources/
        return
        

    def buildDXSP(self, path=''):
        # https://github.com/xbmc/xbmc/blob/master/xbmc/playlists/SmartPlayList.cpp
        
        def mtype(params={"type":"","order":{'direction':'ascending','method':'random','ignorearticle':True,'useartistsortname':True},"rules":{}}):
            path    = ''
            enumLST = list(sorted(['albums', 'artists', 'episodes', 'mixed', 'movies', 'musicvideos', 'songs', 'tvshows']))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Media Type",preselect=(enumLST.index(params.get('type','')) if params.get('type') else -1),useDetails=False, multi=False)
            if not enumSEL is None:
                params['type'] = enumLST[enumSEL]
                if params['type'] in MUSIC_TYPES: db = 'musicdb'
                else:                             db = 'videodb'
                
                if   params['type'] == 'episodes':                         path = "%s://tvshows//titles/-1/-1/-1/"%(db)
                elif params['type'] in ['movies','tvshows','musicvideos']: path = "%s://%s/titles/"%(db,params['type'])
                elif params['type'] in ['albums','artists','songs']:       path = "%s://songs/"%(db)
                else:                                                      path = ''
            return path, params
            
        def andor(params={}):
            enumLST = list(sorted(['and', 'or']))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Conjunction",preselect=(enumLST.index(list(params.get('rules',{}).keys())) if params.get('rules',{}) else -1),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]
                  
        def order(params={}):
            enums   = jsonRPC.getEnums("List.Sort",type="order") 
            enumLST = list(sorted([_f for _f in enums if _f]))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select order",preselect=enumLST.index(params.get('order',{}).get('direction','ascending')),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]
            
        def method(params={}):
            enums   = jsonRPC.getEnums("List.Sort",type="method") 
            enumLST = list(sorted([_f for _f in enums if _f]))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select method",preselect=enumLST.index(params.get('order',{}).get('method','random')),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]
            
        def field(params={}, rule={}):
            if   params.get('type') == 'songs':       enums = jsonRPC.getEnums("List.Filter.Fields.Songs"   , type='items')
            elif params.get('type') == 'albums':      enums = jsonRPC.getEnums("List.Filter.Fields.Albums"  , type='items')
            elif params.get('type') == 'artists':     enums = jsonRPC.getEnums("List.Filter.Fields.Artists" , type='items')
            elif params.get('type') == 'tvshows':     enums = jsonRPC.getEnums("List.Filter.Fields.TVShows" , type='items')
            elif params.get('type') == 'episodes':    enums = jsonRPC.getEnums("List.Filter.Fields.Episodes", type='items')
            elif params.get('type') == 'movies':      enums = jsonRPC.getEnums("List.Filter.Fields.Movies"  , type='items')
            elif params.get('type') == 'musicvideos': enums = jsonRPC.getEnums("List.Filter.Fields.MusicVideos")
            elif params.get('type') == 'mixed':       enums = ['playlist', 'virtualfolder']
            else: return
            enumLST = list(sorted([_f for _f in enums if _f]))
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Filter",preselect=(enumLST.index(rule.get('field')) if rule.get('field') else -1),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]

        def operator(params={}, rule={}):
            enumLST = sorted(jsonRPC.getEnums("List.Filter.Operators"))
            if rule.get("field") != 'date':
                if 'inthelast'    in enumLST: enumLST.remove('inthelast')
                if 'notinthelast' in enumLST: enumLST.remove('notinthelast')
            enumSEL = self.selectDialog(list(sorted([l.title() for l in enumLST])),header="Select Operator",preselect=(enumLST.index(rule.get('operator')) if rule.get('operator') else -1),useDetails=False, multi=False)
            if not enumSEL is None: return enumLST[enumSEL]

        def value(params={}, rule={}):
            return self.getValue(params, rule)
            
        def getRule(params={}, rule={"field":"","operator":"","value":[]}):
            enumSEL = -1
            while not monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value),icon=DUMMY_ICON.format(text=getAbbr(key.title())),props={'key':key,'value':value}) for key, value in list(rule.items())]
                enumSEL = self.selectDialog(enumLST,header="Select method",preselect=-1, multi=False)
                if not enumSEL is None: rule.update({enumLST[enumSEL].getProperty('key'):({"field":field,"operator":operator,"value":value}[enumLST[enumSEL].getProperty('key')])(params,rule)})
            return rule
            
        def getRules(params={}):
            enumSEL = -1
            while not monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),dumpJSON(params.get('rules',{}).get(key,[])),icon=DUMMY_ICON.format(text=getAbbr(key.title())),props={'key':key}) for key in ["and","or"]]
                enumSEL = self.selectDialog(enumLST,header="Edit Rules",multi=False)
                if not enumSEL is None:
                    if enumLST[enumSEL].getLabel() in ['And','Or']:
                        CONSEL  = -1
                        CONLKEY = enumLST[enumSEL].getProperty('key')
                        ruleLST = params.get('rules',{}).get(CONLKEY,[])
                        while not monitor.abortRequested() and not CONSEL is None:
                            andLST = [self.listitems.buildMenuListItem('%s|'%(idx+1),dumpJSON(value),icon=DUMMY_ICON.format(text=str(idx+1)),props={'idx':str(idx)}) for idx, value in enumerate(ruleLST)]
                            andLST.insert(0,self.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32173)),LANGUAGE(33173),icon=ICON,props={'key':'add'}))
                            if len(ruleLST) > 0:
                                andLST.insert(1,self.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32174)),LANGUAGE(33174),icon=ICON,props={'key':'save'}))
                            CONSEL = self.selectDialog(andLST,header="Edit Rules",multi=False)
                            if not CONSEL is None:
                                if   andLST[CONSEL].getProperty('key') == 'add': ruleLST.append(getRule(params,{"field":"","operator":"","value":[]}))
                                elif andLST[CONSEL].getProperty('key') == 'save': 
                                    params.setdefault('rules',{})[CONLKEY] = ruleLST
                                    break
                                elif sorted(loadJSON(andLST[CONSEL].getLabel2())) in [sorted(andd) for andd in ruleLST]:
                                    retval = self.yesnoDialog(LANGUAGE(32175), customlabel=LANGUAGE(32176))
                                    if retval in [1,2]: ruleLST.pop(int(andLST[CONSEL].getProperty('idx')))
                                    if retval == 2:     ruleLST.append(getRule(params,loadJSON(andLST[CONSEL].getLabel2())))
                                else:                   ruleLST.append(getRule(params,loadJSON(andLST[CONSEL].getLabel2())))
            return params

        def getOrder(params={}):
            enumSEL = -1
            while not monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value).title(),icon=DUMMY_ICON.format(text=getAbbr(key.title()))) for key, value in list(params.get('order',{}).items())]
                enumLST.insert(0,self.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32174)),LANGUAGE(33174),icon=ICON,props={'key':'save'}))
                enumSEL = self.selectDialog(enumLST,header="Edit Selection",preselect=-1,multi=False)
                if not enumSEL is None:
                    if   enumLST[enumSEL].getLabel() == 'Direction': params['order'].update({'direction':order(params)})
                    elif enumLST[enumSEL].getLabel() == 'Method':    params['order'].update({'method':method(params)})
                    elif enumLST[enumSEL].getProperty('key') == 'save': break
                    else: params['order'].update({enumLST[enumSEL].getLabel().lower(): not enumLST[enumSEL].getLabel2() == 'True'})
            return params

        from jsonrpc import JSONRPC
        jsonRPC = JSONRPC()
        try:
            path, params = path.split('?xsp=')
            params = loadJSON(params)
        except:
            path, params = mtype()
        self.log('buildDXSP, path = %s, params = %s'%(path,params))
        
        enumSEL = -1
        monitor = MONITOR()
        while not monitor.abortRequested() and not enumSEL is None:
            enumLST = [self.listitems.buildMenuListItem('Path',path,icon=ICON),self.listitems.buildMenuListItem('Order',dumpJSON(params.get('order',{})),icon=ICON),self.listitems.buildMenuListItem('Rules',dumpJSON(params.get('rules',{})),icon=ICON)]
            enumSEL = self.selectDialog(enumLST,header="Edit Dynamic Path", multi=False)
            if not enumSEL is None:
                if   enumLST[enumSEL].getLabel() == 'Path':  path, params = mtype(params)
                elif enumLST[enumSEL].getLabel() == 'Order': params = getOrder(params)
                elif enumLST[enumSEL].getLabel() == 'Rules': params = getRules(params)
        
        if len(params.get('rules',{}).get('and',[]) or params.get('rules',{}).get('and',[])) > 0:
            url = '%s?xsp=%s'%(path,dumpJSON(params))
            self.log('buildDXSP, returning %s'%(url))
            del jsonRPC
            return url


    def getValue(self, params={}, rule={}):
        # etype  = params.get("type")
        # efield = str(rule.get("field")).lower()
        # evalue = ','.join([unquoteString(value) for value in rule.get('value',[])])
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

        def getInput():  return self.inputDialog("Enter Value\nSeparate by ',' ex. Action,Comedy",','.join([unquoteString(value) for value in rule.get('value',[])]))
        def getBrowse(): return self.browseDialog(default='|'.join([unquoteString(value) for value in rule.get('value',[])]))
        def getSelect(): return self.notificationDialog(LANGUAGE(32020))
        enumLST = sorted(['Enter', 'Browse', 'Select'])
        enumKEY = {'Enter':{'func':getInput},'Browse':{'func':getBrowse},'Select':{'func':getSelect}}
        enumSEL = self.selectDialog(enumLST,header="Select Input",useDetails=False, multi=False)
        if not enumSEL is None: return [quoteString(value) for value in (enumKEY[enumLST[enumSEL]].get('func')()).split(',')]


    @contextmanager
    def sudo_dialog(self, msg):
        dia = self.progressBGDialog((int(time.time()) % 60),Dialog().progressBGDialog(message=msg))
        try:
            yield
        finally: 
            dia = self.progressBGDialog(100,dia)