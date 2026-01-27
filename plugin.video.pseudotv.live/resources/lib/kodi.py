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
from json2html   import Json2Html
from collections import Counter, OrderedDict
from contextlib  import contextmanager, closing
from infotagger.listitem import ListItemInfoTag

def slugify(s, lowercase=False):
  if lowercase: s = s.lower()
  s = s.strip()
  s = re.sub(r'[^\w\s-]', '', s)
  s = re.sub(r'[\s_-]+', '_', s)
  s = re.sub(r'^-+|-+$', '', s)
  return s
        
def convertString2Num(value):
    from ast import literal_eval
    try: return literal_eval(value)
    except Exception as e:
        log("convertString2Num, failed! value = %s %s"%(value,e), xbmc.LOGERROR)
        return value
    
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

def setDictLST(lst=[]): #set lst of dicts then return
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
     
def findItemsInLST(items, values, item_key='getLabel', val_key='', index=True):
    if not values: return [-1]
    if not isinstance(values,list): values = [values]
    matches = []
    def _match(fkey,fvalue):
        if str(fkey).lower() == str(fvalue).lower():
            matches.append(idx if index else item)
                    
    for value in values:
        if isinstance(value,dict): 
            value = value.get(val_key,'')
            
        for idx, item in enumerate(items): 
            if isinstance(item,xbmcgui.ListItem): 
                if item_key == 'getLabel':  
                    _match(item.getLabel() ,value)
                elif item_key == 'getLabel2': 
                    _match(item.getLabel2(),value)
                elif item_key == 'getPath': 
                    _match(item.getPath(),value)
            elif isinstance(item,dict):       
                _match(item.get(item_key,''),value)
            else: _match(item,value)
    return matches

class Settings:
    monitor = MONITOR()
    
    def __init__(self):
        self.cacheDB = Cache()
        self.cache   = Cache(mem_cache=True)

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    

    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getIP(self, default='127.0.0.1'):
        IP = (xbmc.getIPAddress() or gethostbyname(gethostname()) or default)
        log('getIP, IP = %s'%(IP))
        return IP
    
    
    def getRealSettings(self):
        try:    return xbmcaddon.Addon(id=ADDON_ID)
        except: return REAL_SETTINGS


    def updateSettings(self):
        self.log('updateSettings')
        #todo build json of third-party addon settings
        # self.pluginMeta.setdefault(addonID,{})['settings'] = [{'key':'value'}]
 
    
    def openSettings(self, ctl=(0,1), id=ADDON_ID):
        builtin = Builtin()
        builtin.closeBusyDialog()
        with builtin.busy_dialog():
            builtin.executebuiltin(f'Addon.OpenSettings({id})')
            xbmc.sleep(100)
            builtin.executebuiltin('SetFocus(%i)'%(ctl[0]-200))
            xbmc.sleep(50)
            builtin.executebuiltin('SetFocus(%i)'%(ctl[1]-180))
        del builtin
    
 
    def openGuide(self, instance=ADDON_NAME):
        def __match(label):
            items = jsonRPC.getDirectory({"directory":baseURL}).get('files',[])
            for item in items:
                if label.lower() == item.get('label','').lower(): return item
            for item in items:
                if item.get('label','').lower().startswith(instance.lower()): return item

        with self.builtin.busy_dialog():
            from jsonrpc import JSONRPC
            jsonRPC = JSONRPC()
            baseURL = 'pvr://channels/tv/'
            for name in ['%s [All channels]'%(instance), instance, 'All channels']:
                item = __match(name)
                if item: break
            del jsonRPC
            if not item: item = {'file':baseURL}
        self.log('openGuide, opening %s'%(item.get('file',baseURL)))
        self.builtin.executebuiltin("Dialog.Close(all)") 
        self.builtin.executebuiltin("ReplaceWindow(TVGuide,%s)"%(item.get('file',baseURL)))
                    
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
        return float(convertString2Num(self.getSetting(key)))
              
              
    def getSettingFloatList(self, key):
        return [convertString2Num(value) for value in self.getSetting(key).split('|')]
        

    def getSettingDict(self, key):
        return loadJSON(decodeString(self.getSetting(key)))
    
    
    def getCacheSetting(self, key, checksum=ADDON_VERSION, json_data=False, revive=True):
        value = self.cacheDB.get(key, checksum, json_data)
        if revive: return self.setCacheSetting(key, value, checksum, json_data)
        else:      return value
        
        
    def getAddonDetails(self, id):
        try:
            addon = xbmcaddon.Addon(id)
            properties = ['name', 'version', 'summary', 'description', 'path', 'author', 'icon', 'disclaimer', 'fanart', 'changelog', 'id', 'profile', 'stars', 'type']
            return dict([(property,addon.getAddonInfo(property)) for property in properties])    
        except:
            from jsonrpc import JSONRPC
            return JSONRPC().getAddonDetails(id)


    def getEXTSetting(self, id, key):
        return xbmcaddon.Addon(id).getSetting(key)
        
        
    def getFriendlyName(self):
        friendly = Properties().getProperty('INSTANCE_NAME')
        if not friendly:
            from jsonrpc import JSONRPC
            friendly = Properties().setProperty('INSTANCE_NAME', JSONRPC().inputFriendlyName())
        return friendly
        
        
    def getMYUUID(self):
        friendly = self.getFriendlyName()
        uuid = self.getCacheSetting('MY_UUID', checksum=friendly)
        if not uuid: uuid = self.setCacheSetting('MY_UUID', genUUID(seed=self.getFriendlyName()), checksum=friendly)
        return uuid

        
    def getResetChannels(self):
        return (self.getCacheSetting('clearChannels') or [])


    #CLR
    def clrCacheSetting(self, key):
        self.cache.clear(key)
    
    
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
            
            
    def setCacheSetting(self, key, value, checksum=ADDON_VERSION, json_data=False):
        return self.cacheDB.set(key, value, checksum, datetime.timedelta(days=84), json_data)
            

    def setEXTSetting(self, id, key, value):
        return xbmcaddon.Addon(id).setSetting(key,value)


    def setResetChannels(self, id):
        ids = self.getResetChannels()
        if isinstance(id, list): ids.extend(id)
        else:                    ids.append(id)
        return self.setCacheSetting('clearChannels',list(set(ids)))


    @cacheit(expiration=datetime.timedelta(minutes=5), json_data=True)
    def getBonjour(self, inclChannels=False):
        self.log("getBonjour, inclChannels = %s"%(inclChannels))
        payload = {'id'      :ADDON_ID,
                   'uuid'    :self.getMYUUID(),
                   'version' :ADDON_VERSION,
                   'python'  :platform.python_version(),
                   'machine' :platform.machine(),
                   'platform':self.builtin.getInfoLabel('OSVersionInfo','System'),
                   'build'   :self.builtin.getInfoLabel('BuildVersion','System'),
                   'name'    :self.getFriendlyName(),
                   'host'    :self.property.getRemoteHost()}
                   
        payload['remotes']   = {'bonjour':'http://%s/%s'%(payload['host'],BONJOURFLE),
                                'remote' :'http://%s/%s'%(payload['host'],REMOTEFLE),
                                'm3u'    :'http://%s/%s'%(payload['host'],M3UFLE),
                                'xmltv'  :'http://%s/%s'%(payload['host'],XMLTVFLE),
                                'genre'  :'http://%s/%s'%(payload['host'],GENREFLE)}
                              
        payload['settings']  = {'Resource_Logos'    :self.getSetting('Resource_Logos').split('|'),
                                'Resource_Bumpers'  :self.getSetting('Resource_Bumpers').split('|'),
                                'Resource_Ratings'  :self.getSetting('Resource_Ratings').split('|'),
                                'Resource_Adverts'  :self.getSetting('Resource_Adverts').split('|'),
                                'Resource_Trailers' :self.getSetting('Resource_Trailers').split('|')}
                                
        if inclChannels: 
            from channels    import Channels
            payload['channels'] = Channels().getChannels()
        payload['updated'] = datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
        payload['md5']     = getMD5(dumpJSON(payload))
        return payload
    
    
    @cacheit(expiration=datetime.timedelta(minutes=5), json_data=True)
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
                                  'programmes':[{'id':key,'end-time':datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)} for key, value in list(dict(xmltv.loadStopTimes()).items())]}
            payload['library'] = Library().getLibrary()
            payload['servers'] = Multiroom().getDiscovery()
            del xmltv
            return payload

        payload = __getMeta(self.getBonjour(inclChannels=True))
        if inclDebug: payload['debug'] = loadJSON(self.property.getEXTProperty('%s.debug.log'%(ADDON_ID))).get('DEBUG',{})
        payload['updated']   = datetime.datetime.fromtimestamp(time.time()).strftime(DTFORMAT)
        payload['md5']       = getMD5(dumpJSON(payload))
        return payload

            
    @cacheit(expiration=datetime.timedelta(minutes=5))
    def getPayloadUI(self):
        return Json2Html().convert(self.getPayload(inclDebug=True))


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
                'useEpgGenreText'               :'true',
                'logoPathType'                  :'0',
                'logoPath'                      :LOGO_LOC,
                'logoFromEpg'                   :'2',
                'mediaTitleSeasonEpisode'       :'true',
                'timeshiftEnabled'              :'false',
                'catchupEnabled'                :'true',
                'catchupPlayEpgAsLive'          :'false',
                'catchupWatchEpgEndBufferMins'  :'0',
                'catchupWatchEpgBeginBufferMins':'0'}


    def setPVRPath(self, path, instance=ADDON_NAME, prompt=False, force=False): #local instance
        settings  = self.IPTV_SIMPLE_SETTINGS()
        nsettings = {'m3uPathType'                :'0',
                     'm3uPath'                    :os.path.join(path,M3UFLE),
                     'epgPathType'                :'0',
                     'epgPath'                    :os.path.join(path,XMLTVFLE),
                     'genresPathType'             :'0',
                     'genresPath'                 :os.path.join(path,GENREFLE),
                     'logoPathType'               :'0',
                     'logoPath'                   :os.path.join(path,'logos'),
                     'kodi_addon_instance_name'   : '%s - %s'%(ADDON_NAME,instance),
                     'kodi_addon_instance_enabled':'true'}
        settings.update(nsettings)
        self.log('setPVRPath, new settings = %s'%(nsettings))
        if self.hasPVRInstance(instance) and not force:
            return self.log('setPVRPath, instance (%s) settings exists.'%(instance))
        return self.chkPluginSettings(PVR_CLIENT_ID,settings,instance,prompt)
        
        
    def setPVRRemote(self, host, instance=ADDON_NAME, prompt=False): #multi-room instances
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
        if   not self.getSettingBool('Enable_PVR_SETTINGS'): self.dialog.notificationDialog(LANGUAGE(32186))
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
        for file in [filename for filename in FileAccess.listdir(PVR_CLIENT_LOC)[1] if filename.endswith('.xml')]:
            if self.monitor.waitForAbort(0.0001): break
            elif file.startswith('instance-settings-'):
                try:
                    xml = FileAccess.open(os.path.join(PVR_CLIENT_LOC,file), "r")
                    txt = xml.read()
                    xml.close()
                except Exception as e:
                    self.log('chkPVRInstance, path = %s, failed to open file = %s\n%s'%(PVR_CLIENT_LOC,file,e))
                    continue
                        
                match = re.compile(r'<setting id=\"kodi_addon_instance_name\" default=\"true\">(.*?)\</setting>', re.IGNORECASE).search(txt)
                try: name = match.group(1)
                except:
                    match = re.compile(r'<setting id=\"kodi_addon_instance_name\">(.*?)\</setting>', re.IGNORECASE).search(txt)
                    try:    name = match.group(1)
                    except: name = None
                    
                if name == instance:
                    if found ==  False: found = os.path.join(PVR_CLIENT_LOC,file)
                    else: #auto remove any duplicate entries with the same instance name.
                        FileAccess.delete(os.path.join(PVR_CLIENT_LOC,file))
                        self.log('chkPVRInstance, removing duplicate entry %s'%(file))
                self.log('chkPVRInstance, found %s file = %s'%(name,found))
        return found


    @cacheit(expiration=datetime.timedelta(minutes=5),json_data=True)
    def getPVRInstanceSettings(self, instance):
        instanceConf = dict()
        instancePath = self.hasPVRInstance(instance)
        if instancePath:
            fle = FileAccess.open(instancePath,'r')
            lines = fle.readlines()
            for line in lines:
                if not 'id=' in line: continue
                match = re.compile(r'<setting id=\"(.*)\" default=\"(.*)\">(.*?)\</setting>', re.IGNORECASE).search(line)
                try: instanceConf.update({match.group(1):(match.group(2),match.group(3))})
                except:
                    match = re.compile(r'<setting id=\"(.*)\">(.*?)\</setting>', re.IGNORECASE).search(line)
                    try: instanceConf.update({match.group(1):('',match.group(2))})
                    except:
                        match = re.compile(r'<setting id=\"(.*)\" default=\"(.*?)\" />', re.IGNORECASE).search(line)
                        try: instanceConf.update({match.group(1):(match.group(2),None)})
                        except: pass
            fle.close()
        self.log('getPVRInstanceSettings, returning instance = %s\n%s'%(instance,instanceConf))
        return instanceConf
        
        
    def chkPluginSettings(self, id, nsettings, instance=ADDON_NAME, prompt=False):
        self.log('chkPluginSettings, id = %s, instance = %s, prompt=%s'%(id,instance,prompt))
        addon   = xbmcaddon.Addon(id)
        dialog  = Dialog()
        if addon is None: dialog.notificationDialog(LANGUAGE(32034)%(id))
        else:
            changes   = {}
            name      = addon.getAddonInfo('name')
            osettings = self.getPVRInstanceSettings(instance)
            for setting, newvalue in list(nsettings.items()):
                if self.monitor.waitForAbort(0.0001): return False
                default, oldvalue = osettings.get(setting,({},{}))
                if str(newvalue).lower() != str(oldvalue).lower(): 
                    changes[setting] = (oldvalue, newvalue)
                
            if not changes:
                self.log('chkPluginSettings, no changes detected!')
                return False
            elif prompt:
                modified = '\n'.join(['Modifying %s: [COLOR=dimgray][B]%s[/B][/COLOR] => [COLOR=green][B]%s[/B][/COLOR]'%(setting,newvalue[0],newvalue[1]) for setting, newvalue in list(changes.items())])
                dialog.textviewer('%s\n\n%s'%(LANGUAGE(32035)%(name),modified))
                if not dialog.yesnoDialog((LANGUAGE(32036)%name)): 
                    dialog.notificationDialog(LANGUAGE(32046))
                    return False
                
            for s, v in list(changes.items()):
                if self.monitor.waitForAbort(0.0001): return False
                addon.setSetting(s, v[1])
                self.log('chkPluginSettings, setting = %s, current value = %s => %s'%(s,oldvalue,v[1]))
            self.setPVRInstance(instance)
            dialog.notificationDialog((LANGUAGE(32037)%(name)))
            del dialog
            return True
        del dialog
        

    def getCurrentSettings(self):
        settings = ['User_Folder',
                    'Debug_Enable',
                    'Overlay_Enable',
                    'Enable_OnInfo',
                    'Disable_Trakt',
                    'Rollback_Watched',
                    'Store_Duration',
                    'Seek_Tolerance',
                    'Seek_Threshold',
                    'Idle_Timer',
                    'Run_While_Playing',
                    'Restart_Percentage',]
        for setting in settings:
            yield (setting,self.getSetting(setting))
               

    def hasAutotuned(self):
        return self.getCacheSetting('has.Autotuned')
        
        
    def setAutotuned(self, state=True):
        return self.setCacheSetting('has.Autotuned',state)


    def setWizardRun(self, state=True):
        return self.setCacheSetting('has.wizardRun',state)


    def hasWizardRun(self):
        return self.getCacheSetting('has.wizardRun')

       
class Properties:
    monitor = MONITOR()
    
    def __init__(self, winID=10000):
        self.winID      = winID
        self.window     = xbmcgui.Window(winID)


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def setEpochTimer(self, key, time=0):
        return self.setPropertyInt(key,time)


    def setPropTimer(self, key, state=True):
        return self.setEXTPropertyBool('%s.%s'%(ADDON_ID,key),state)


    def setRemoteHost(self, value):
        return self.setProperty('%s.Remote_Host'%(ADDON_ID),value)
        
        
    def getRemoteHost(self):
        remote = self.getProperty('%s.Remote_Host'%(ADDON_ID))
        if not remote: remote = self.setRemoteHost('%s:%s'%(Settings().getIP(),Settings().getSettingInt('TCP_PORT')))
        return remote


    @contextmanager
    def chkRunning(self, key):
        if not self.isRunning(key):
            self.setRunning(key,True)
            try: yield
            finally: self.setRunning(key,False)
        else: yield
        
        
    def setUpdateChannels(self, id):
        ids = self.getUpdateChannels()
        if isinstance(id, list): ids.extend(id)
        else:                    ids.append(id)
        timerit(self.setPropTimer)(FIFTEEN,['chkUpdate'])
        return self.setPropertyList('updateChannels',list(set(ids)))
    
    
    def getUpdateChannels(self):
        ids = (self.getPropertyList('updateChannels') or [])
        self.clrProperty('updateChannels')
        return ids
    
    
    def setRunning(self, key, state=True):
        return self.setEXTPropertyBool('%s.Running.%s'%(ADDON_ID,key),state)
        
        
    def isRunning(self, key):
        return self.getEXTPropertyBool('%s.Running.%s'%(ADDON_ID,key))


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
        
        
    def setServers(self, state=True):
        return self.setEXTPropertyBool('%s.has.Servers'%(ADDON_ID),state)
        

    def hasServers(self):
        return self.getEXTPropertyBool('%s.has.Servers'%(ADDON_ID))
        
                
    def setEnabledServers(self, state=True):
        return self.setEXTPropertyBool('%s.has.Enabled_Servers'%(ADDON_ID),state)
        
        
    def hasEnabledServers(self):
        return self.getEXTPropertyBool('%s.has.Enabled_Servers'%(ADDON_ID))
        
                
    def hasEnabledLibrary(self, type):
        return self.getEXTPropertyBool('%s.has.%s.enabled'%(ADDON_ID,slugify(type)))
        
        
    def hasLibrary(self):
        return True in list(set([self.hasEnabledLibrary(type) for type in AUTOTUNE_TYPES]))
        
        
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
    def interruptActivity(self): #quit background task
        self.setInterruptActivity(True)
        try: yield
        finally: self.setInterruptActivity(False)
         
        
    def setInterruptActivity(self, state=True):
        return self.setEXTPropertyBool('interruptActivity',state)
        

    def isInterruptActivity(self):
        return self.getEXTPropertyBool('interruptActivity')


    def setPendingInterrupt(self, state=True):
        return self.setEXTPropertyBool('pendingInterrupt',state)


    def isPendingInterrupt(self):
        return self.getEXTPropertyBool('pendingInterrupt')

        
    @contextmanager
    def suspendActivity(self): #pause background task.
        self.setSuspendActivity(True)
        try: yield
        finally: self.setSuspendActivity(False)


    def setSuspendActivity(self, state=True):
        return self.setEXTPropertyBool('suspendActivity',state)


    def isSuspendActivity(self):
        return self.getEXTPropertyBool('suspendActivity')
        
        
    def setPendingSuspend(self, state=True):
        return self.setEXTPropertyBool('pendingSuspend',state)
        
        
    def isPendingSuspend(self):
        return self.getEXTPropertyBool('pendingSuspend')


    @contextmanager
    def legacy(self):
        if not self.isPseudoTVRunning():
            self.setEXTPropertyBool('PseudoTVRunning',True)
            try: yield
            finally: self.setEXTPropertyBool('PseudoTVRunning',False)
        else: yield


    def isPseudoTVRunning(self):
        return self.getEXTPropertyBool('PseudoTVRunning')


    def setInstanceID(self):
        self.clearTrash(self.getEXTProperty('%s.InstanceID'%(ADDON_ID)))
        return self.setEXTProperty('%s.InstanceID'%(ADDON_ID),getMD5(uuid.uuid4()))


    def getInstanceID(self):
        instanceID = self.getEXTProperty('%s.InstanceID'%(ADDON_ID))
        if not instanceID: instanceID = self.setInstanceID()
        return instanceID


    def getKey(self, key, useInstance=True):
        if not isinstance(key,str): key = str(key)
        if self.winID == 10000 and not key.startswith(ADDON_ID): #create unique id 
            if useInstance: return self.setTrash('%s.%s.%s'%(ADDON_ID,key,self.getInstanceID()))
            else:           return '%s.%s'%(ADDON_ID,key)
        return key

        
    #CLEAR
    def clrEXTProperty(self, key):
        self.log('clrEXTProperty, id = %s, key = %s'%(10000,key))
        return xbmcgui.Window(10000).clearProperty(key)
        
        
    def clrProperties(self):
        self.log('clrProperties')
        return self.window.clearProperties()
        
        
    def clrProperty(self, key):
        key = self.getKey(key)
        self.log('clrProperty, id = %s, key = %s'%(self.winID,key))
        return self.window.clearProperty(key)


    #GET
    def getEXTProperty(self, key):
        value = xbmcgui.Window(10000).getProperty(key)
        if not '.TRASH' in key: self.log('getEXTProperty, id = %s, key = %s, value = %s'%(10000,key,'%s...'%(str(value)[:128])))
        return value
        
        
    def getEXTPropertyBool(self, key):
        return (self.getEXTProperty(key) or '').lower() == "true"
        
        
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
        
        
    def getPropertyInt(self, key, default=-1):
        value = self.getProperty(key)
        if value: return int(convertString2Num(value))
        else:     return default
            
        
    def getPropertyFloat(self, key, default=-1):
        value = self.getProperty(key)
        if value: return float(convertString2Num(value))
        else:     return default
        

    #SET
    def setEXTProperty(self, key, value):
        if not '.TRASH' in key: self.log('setEXTProperty, id = %s, key = %s, value = %s'%(10000,key,'%s...'%((str(value)[:128]))))
        xbmcgui.Window(10000).setProperty(key,str(value))
        return value
        
        
    def setEXTPropertyBool(self, key, value):
        if value: self.setEXTProperty(key,str(value).lower())
        else:     self.clrEXTProperty(key)
        return str(value).lower() == 'true'
        
        
    def setProperty(self, key, value):
        key = self.getKey(key)
        self.log('setProperty, id = %s, key = %s, value = %s'%(self.winID,key,'%s...'%((str(value)[:128]))))
        self.window.setProperty(key, str(value))
        return value
        
        
    def setPropertyList(self, key, values):
        return self.setProperty(key, '|'.join(values))
        
        
    def setPropertyBool(self, key, value):
        if value: self.setProperty(key, value)
        else:     self.clrProperty(key)
        return str(value).lower() == 'true'
        
        
    def setPropertyDict(self, key, value={}):
        return self.setProperty(key, encodeString(dumpJSON(value)))
        
                
    def setPropertyInt(self, key, value):
        return self.setProperty(key, int(value))
                
                
    def setPropertyFloat(self, key, value):
        return self.setProperty(key, float(value))

    
    def setTrakt(self, state=False):
        self.log('setTrakt, disable trakt = %s'%(state))
        # https://github.com/trakt/script.trakt/blob/d45f1363c49c3e1e83dabacb70729cc3dec6a815/resources/lib/kodiUtilities.py#L104
        if state: self.setEXTPropertyBool('script.trakt.paused',state)
        else:     self.clrEXTProperty('script.trakt.paused')


    def setTrash(self, key): #catalog instance properties that may become abandoned
        instanceID = self.getInstanceID()
        tmpDCT = loadJSON(self.getEXTProperty('%s.TRASH'%(ADDON_ID)))
        if key not in tmpDCT.setdefault(instanceID,[]): tmpDCT.setdefault(instanceID,[]).append(key)
        self.setEXTProperty('%s.TRASH'%(ADDON_ID),dumpJSON(tmpDCT))
        return key

        
    def clearTrash(self, instanceID=None): #clear abandoned properties after instanceID change
        if instanceID is None: instanceID = self.getInstanceID()
        tmpDCT = loadJSON(self.getEXTProperty('%s.TRASH'%(ADDON_ID)))
        if instanceID in tmpDCT:
            self.log('clearTrash, instanceID = %s'%(instanceID))
            tmpLST = tmpDCT.pop(instanceID)
            for prop in tmpLST:
                self.clrProperty(prop)
                self.clrEXTProperty(prop)


    def __exit__(self):
        self.log('__exit__')
        self.clearTrash(self.getInstanceID())
        
        
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
            art['poster'] = (getThumb(info,opt=1) or COLOR_LOGO)
            art['fanart'] = (getThumb(info)       or FANART)
            
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
        if item.get('file'):
            file_path = item.get('file','')
            # log(f'buildItemListItem, Translating path "{file_path}"...')
            file_path = xbmcvfs.translatePath(file_path)
            # log(f'buildItemListItem, Translated path to "{file_path}".')
            listitem.setPath(file_path)
            if file_path.endswith('.strm'):
                with io.open(file_path, mode='r', encoding="utf-8") as f:
                    file_path = f.read()
            listitem.setPath(file_path) # if info.get('file'):   listitem.setPath(item.get('file','')) # (item.get('file','') or item.get('url','') or item.get('path',''))
        
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
                    except Exception as e: self.log("cleanInfo failed! %s\nkey = %s, value = %s, type = %s\n%s"%(e,key,value,type,ninfo), xbmc.LOGWARNING)
                     
            if isinstance(ninfo[key],list):
                for n in ninfo[key]:
                    if isinstance(n,dict): n, properties = self.cleanInfo(n,media,properties)
            if isinstance(ninfo[key],dict): ninfo[key], properties = self.cleanInfo(ninfo[key],media,properties)
        return ninfo, properties


    def cleanProp(self, pvalue):
        if       isinstance(pvalue,dict): return dumpJSON(pvalue)
        elif     isinstance(pvalue,list): return '|'.join(map(str, pvalue))
        elif not isinstance(pvalue,str):  return str(pvalue)
        else:                             return pvalue
            
    
class Builtin:
    busy       = None
    monitor    = MONITOR()
    properties = Properties()
    
    
    def __init__(self):
        ...

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
                
                
    def isRecording(self):
        return self.getInfoBool('IsRecording','Pvr')
        
        
    def isScanning(self):
        return (self.getInfoBool('IsScanningVideo','Library') & self.getInfoBool('IsScanningMusic','Library'))
          
                      
    def isSettingsOpened(self) -> bool:
        return (self.getInfoBool('IsVisible(addonsettings)','Window') | self.getInfoBool('IsVisible(selectdialog)' ,'Window'))

  
    def isBusyDialog(self):
        return (self.properties.isRunning('OVERLAY_BUSY') | self.getInfoBool('IsActive(busydialognocancel)','Window') | self.getInfoBool('IsActive(busydialog)','Window'))


    def closeBusyDialog(self):
        if hasattr(self.busy, 'close'):
            self.busy = self.busy.close()
        elif self.getInfoBool('IsActive(busydialognocancel)','Window'):
            self.executebuiltin('Dialog.Close(busydialognocancel)')
        elif self.getInfoBool('IsActive(busydialog)','Window'):
            self.executebuiltin('Dialog.Close(busydialog)')


    @contextmanager
    def busy_dialog(self, cancel=False):
        if not self.isBusyDialog() and not cancel:
            try: 
                if self.busy is None:
                    from overlay import Busy 
                    self.busy = Busy(BUSY_XML, ADDON_PATH, "default")
                    self.busy.show()
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
            if not MONITOR().waitForAbort(1.0): return self.getInfoLabel(key,param,default)
        self.log('getInfoLabel, key = %s.%s, value = %s'%(param,key,value))
        return (value or default)
        

    def getInfoBool(self, key, param='Library'):
        value = (xbmc.getCondVisibility('%s.%s'%(param,key)) or False)
        self.log('getInfoBool, key = %s.%s, value = %s'%(param,key,value))
        return value
        
        
    def executeWindow(self, key):
        if self.getInfoBool('Playing','Player'):
            self.executebuiltin(key)
        
        
    def executebuiltin(self, key, wait=False):
        self.log('executebuiltin, key = %s, wait = %s'%(key,wait))
        xbmc.executebuiltin('%s'%(key),wait)
        return True
        
        
    def executescript(self, path):
        self.log('executescript, path = %s'%(path))
        xbmc.executescript('%s'%(path))
        return True
        
        
    @contextmanager
    def sendLocker(self, wait=0.0001):
        while not self.monitor.abortRequested(): #try and make kodi api thread safe / thread locks not working? todo debug.
            if self.monitor.waitForAbort(wait) or self.properties.getEXTPropertyBool('%s.pendingInterrupt'%(ADDON_ID)): break
            elif not self.properties.getEXTPropertyBool('%s.sendLocker'%(ADDON_ID)): break
            else: log('sendLocker, avoiding collision')
        self.properties.setEXTPropertyBool('%s.sendLocker'%(ADDON_ID),True)
        try: yield
        finally: self.properties.setEXTPropertyBool('%s.sendLocker'%(ADDON_ID),False)


    def executeJSONRPC(self, command):
        self.log('executeJSONRPC, command = %s'%(command))
        # with self.sendLocker():
        return xbmc.executeJSONRPC(command)


    def getResolution(self):
        WH, WIN = self.getInfoLabel('ScreenResolution','System').split(' - ')
        return (1920,1080), WIN #tuple(int(x) for x in WH.split('x')), WIN


class Dialog:
    settings   = Settings()
    properties = Properties()
    listitems  = ListItems()
    builtin    = Builtin()
    dialog     = xbmcgui.Dialog()
    
    def __init__(self):
        self.settings.dialog   = self
        self.settings.property = self.properties
        self.settings.builtin  = self.builtin
        self.monitor           = self.builtin.monitor
        

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
        return self.properties.setPropertyDict('monitor.montiorList',{'info':list(setDictLST(items))})


    def colorDialog(self, colorlist=[], preselect="", colorfile="", heading=ADDON_NAME):
        return self.dialog.colorpicker(heading, preselect, colorfile, colorlist)
    
    
    def _closeOkDialog(self):
        if self.builtin.getInfoBool('IsActive(okdialog)','Window'):
            self.builtin.executebuiltin('Dialog.Close(okdialog)')
        
        
    def _okDialog(self, msg, heading, autoclose, url):
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

        if not self.properties.isRunning('qrDialog'):
            with self.properties.chkRunning('qrDialog'):
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
                    xbmc.executebuiltin('SetFocus(3000)')
                    xbmc.executebuiltin('AlarmClock(down,Action(down),.5,true,false)')
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


    def notificationWait(self, message, header=ADDON_NAME, wait=4, usethread=False):
        if usethread: return self._notificationWait(message, header, wait)
        else:
            pDialog = self.progressBGDialog(message=message,header=header)
            for idx in range(int(wait)):
                pDialog = self.progressBGDialog((((idx+1) * 100)//int(wait)),pDialog,header=header)
                if pDialog is None or MONITOR().waitForAbort(1.0): break
            if hasattr(pDialog, 'close'): pDialog.close()
        return True


    def updateProgress(self, percent=-1, control=None, message='', header=ADDON_NAME):
        if   isinstance(control,xbmcgui.DialogProgressBG): return self.progressBGDialog(percent, control, message, header)
        elif isinstance(control,xbmcgui.DialogProgress):
            title = header.replace('%s, '%(ADDON_NAME),'')
            match = re.compile(r'(.*?): (.*?)\%', re.IGNORECASE).search(message)
            try:
                message = match.group(1)
                percent = int(match.group(2))
            except: pass
            if title: message = '%s: %s'%(title,message)
            return self.progressDialog(percent, control, message)


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
        

    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=PROMPT_DELAY, icon=COLOR_LOGO, show=True):
        self.log('notificationDialog: %s'%(message))
        ## - Builtin Icons:
        ## - xbmcgui.NOTIFICATION_INFO
        ## - xbmcgui.NOTIFICATION_WARNING
        ## - xbmcgui.NOTIFICATION_ERROR
        if show:
            try:    self.dialog.notification(header, message, icon, time, sound=False)
            except: self.builtin.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
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
                
        if not self.properties.isRunning('SELECT_DIALOG'):
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
        

    def importSTRM(self, strm):
        try:
            with self.builtin.busy_dialog():
                fle   = FileAccess.open(strm,'r')
                paths = [line for line in fle.readlines() if not line.startswith('#') and '://' in line]
                fle.close()
                if len(paths) == 0: return self.notificationDialog(LANGUAGE(32018)%(LANGUAGE(30047)))
            select = self.selectDialog(paths, LANGUAGE(32080), useDetails=False, multi=False)
            self.log("importSTRM, strm = %s paths = %s"%(strm,paths))
            if not select is None: return paths[select]
        except Exception as e: self.log("importSTRM, failed! %s\n%s"%(e,strm), xbmc.LOGERROR)
             
               
    def _resourcePath(self, id=[], content='videos', ftype=''):
        if not id: id = self.browseResources(id, content, ftype, multi=False)
        path = 'special://home/addons/%s/resources/'%(id)
        self.log("_resourcePath, id = %s, content = %s, ftype = %s, path = %s"%(id, content, ftype,path))
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
        jsonRPC = JSONRPC()
        with self.builtin.busy_dialog():
            lizLST = poolit(__buildMenuItem)([result for result in __getResources() if result.get('addonid').startswith('resource.%s.%s'%(content,ftype))])
            del jsonRPC
            
        selects = self.selectDialog(lizLST, 'Select one or more resources', preselect=findItemsInLST(lizLST,ids,'getPath'), multi=multi)
        if selects is None:                return
        elif not isinstance(selects,list): return lizLST[selects].getPath()
        else:                              return [lizLST[select].getPath() for select in selects]


    def browseSources(self, type=0, heading=ADDON_NAME, default='', shares='', mask='', useThumbs=True, treatAsFolder=False, multi=False, monitor=False, include=[], exclude=[]):
        self.log('browseSources, type = %s, heading= %s, shares= %s, useThumbs= %s, treatAsFolder= %s, default= %s, mask= %s, include= %s, exclude= %s'%(type,heading,shares,useThumbs,treatAsFolder,default,mask,len(include),exclude))
        def __buildMenuItem(option):
            return self.listitems.buildMenuListItem(option['label'],option['label2'],DUMMY_ICON.format(text=getAbbr(option['label'])))

        with self.builtin.busy_dialog():
            optlabel = "%s"%({'0':'Folders','1':'Files'}[str(type)])  if multi else "%s"%({'0':'Folder','1':'File'}[str(type)])
            opts = [{"idx":10, "label":'%s %s'%(LANGUAGE(32196),optlabel) , "label2":"library://video/"                      , "default":"library://video/"                   , "shares":"video"   , "mask":xbmc.getSupportedMedia('video')   , "type":0    , "multi":multi},
                    {"idx":11, "label":'%s %s'%(LANGUAGE(32207),optlabel) , "label2":"library://music/"                      , "default":"library://music/"                   , "shares":"music"   , "mask":xbmc.getSupportedMedia('music')   , "type":0    , "multi":multi},
                    {"idx":12, "label":LANGUAGE(32191)                    , "label2":"special://profile/playlists/video/"    , "default":"special://profile/playlists/video/" , "shares":""        , "mask":".xsp"                            , "type":1    , "multi":False},
                    {"idx":13, "label":LANGUAGE(32192)                    , "label2":"special://profile/playlists/music/"    , "default":"special://profile/playlists/music/" , "shares":""        , "mask":".xsp"                            , "type":1    , "multi":False},
                    {"idx":14, "label":LANGUAGE(32193)                    , "label2":"special://profile/playlists/mixed/"    , "default":"special://profile/playlists/mixed/" , "shares":""        , "mask":".xsp"                            , "type":1    , "multi":False},
                    {"idx":15, "label":LANGUAGE(32195)                    , "label2":"Create Dynamic Smartplaylist"          , "default":""                                   , "shares":""        , "mask":""                                , "type":1    , "multi":False},
                    {"idx":16, "label":LANGUAGE(32194)                    , "label2":"Import directory paths from STRM"      , "default":""                                   , "shares":"files"   , "mask":".strm"                           , "type":1    , "multi":False},
                    {"idx":17, "label":LANGUAGE(32206)                    , "label2":"Media from basic playlists"            , "default":""                                   , "shares":""        , "mask":"|".join(ALT_PLAYLISTS)           , "type":1    , "multi":False},
                    {"idx":18, "label":'%s %s'%(LANGUAGE(32198),'Folders'), "label2":""                                      , "default":""                                   , "shares":"files"   , "mask":mask                              , "type":type , "multi":multi},
                    {"idx":19, "label":'%s %s'%(LANGUAGE(32199),'Folders'), "label2":""                                      , "default":""                                   , "shares":"local"   , "mask":mask                              , "type":type , "multi":multi},
                    {"idx":20, "label":'%s %s'%(LANGUAGE(32200),'Folders'), "label2":""                                      , "default":""                                   , "shares":shares    , "mask":mask                              , "type":type , "multi":multi},
                    {"idx":21, "label":LANGUAGE(32201)                    , "label2":""                                      , "default":""                                   , "shares":"pictures", "mask":xbmc.getSupportedMedia('picture') , "type":1    , "multi":False},
                    {"idx":22, "label":LANGUAGE(32202)                    , "label2":"Resource Plugin"                       , "default":""                                   , "shares":shares    , "mask":mask                              , "type":type , "multi":multi}]

            options = include.copy()
            options.extend([opt for opt in opts if not opt.get('idx',-1) in exclude])
            options = setDictLST(options)
            if default: options.insert(0,{"idx":0, "label":LANGUAGE(32203), "label2":default, "default":default, "shares":shares, "mask":mask, "type":type, "multi":multi})
            lizLST = poolit(__buildMenuItem)(sorted(options, key=itemgetter('idx')))
       
        select = self.selectDialog(lizLST, LANGUAGE(32089), multi=False)
        if select is None: return
        default = options[select]['default']
        shares  = options[select]['shares']
        mask    = options[select]['mask']
        type    = options[select]['type']
        multi   = options[select]['multi']
        if type == 0:
            if "resource."   in default or options[select]["idx"] == 22: return self._resourcePath(default, {xbmc.getSupportedMedia('video'):'videos',xbmc.getSupportedMedia('picture'):'images'}.get(mask,xbmc.getSupportedMedia('video')))
        elif type == 1:
            if   "?xsp="     in default or options[select]["idx"] == 15: return self.buildDXSP(default)
            elif ".strm"     in default or options[select]["idx"] == 16: return self.importSTRM(default)
            elif "resource." in default or options[select]["idx"] == 22: default = self._resourcePath(default, {xbmc.getSupportedMedia('video'):'videos',xbmc.getSupportedMedia('picture'):'images'}.get(mask,xbmc.getSupportedMedia('video')))
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
        def __buildListItem(label: str="", label2: str="", icon: str=COLOR_LOGO, paths: list=[], items: dict={}):
            return self.listitems.buildMenuListItem(label, label2, icon, url='|'.join(paths), props=items)

        select  = -1
        epaths  = paths.copy()
        pathLST = list([_f for _f in paths if _f])
        lastOPT = None
        while not MONITOR().abortRequested() and not select is None:
            with self.builtin.busy_dialog():
                npath  = None
                lizLST = [__buildListItem('%s|'%(idx+1),path,paths=[path],icon=DUMMY_ICON.format(text=str(idx+1)),items={'idx':idx+1}) for idx, path in enumerate(pathLST) if path]
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
            while not self.monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value),icon=DUMMY_ICON.format(text=getAbbr(key.title())),props={'key':key,'value':value}) for key, value in list(rule.items())]
                enumSEL = self.selectDialog(enumLST,header="Select method",preselect=-1, multi=False)
                if not enumSEL is None: rule.update({enumLST[enumSEL].getProperty('key'):({"field":field,"operator":operator,"value":value}[enumLST[enumSEL].getProperty('key')])(params,rule)})
            return rule
            
        def getRules(params={}):
            enumSEL = -1
            eparams = params.copy()
            while not self.monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),dumpJSON(params.get('rules',{}).get(key,[])),icon=DUMMY_ICON.format(text=getAbbr(key.title())),props={'key':key}) for key in ["and","or"]]
                enumSEL = self.selectDialog(enumLST,header="Edit Rules",multi=False)
                if not enumSEL is None:
                    if enumLST[enumSEL].getLabel() in ['And','Or']:
                        CONSEL  = -1
                        CONLKEY = enumLST[enumSEL].getProperty('key')
                        ruleLST = params.get('rules',{}).get(CONLKEY,[])
                        while not self.monitor.abortRequested() and not CONSEL is None:
                            andLST = [self.listitems.buildMenuListItem('%s|'%(idx+1),dumpJSON(value),icon=DUMMY_ICON.format(text=str(idx+1)),props={'idx':str(idx)}) for idx, value in enumerate(ruleLST)]
                            andLST.insert(0,self.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32173)),"",icon=ICON,props={'key':'add'}))
                            if len(ruleLST) > 0 and eparams != params: andLST.insert(1,self.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32174)),"",icon=ICON,props={'key':'save'}))
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
            while not self.monitor.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value).title(),icon=DUMMY_ICON.format(text=getAbbr(key.title()))) for key, value in list(params.get('order',{}).items())]
                enumLST.insert(0,self.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32174)),"",icon=ICON,props={'key':'save'}))
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
        while not self.monitor.abortRequested() and not enumSEL is None:
            enumLST = [self.listitems.buildMenuListItem('Path',path,icon=ICON),self.listitems.buildMenuListItem('Order',dumpJSON(params.get('order',{})),icon=ICON),self.listitems.buildMenuListItem('Rules',dumpJSON(params.get('rules',{})),icon=ICON)]
            enumSEL = self.selectDialog(enumLST,header="Edit Dynamic Path", multi=False)
            if not enumSEL is None:
                if   enumLST[enumSEL].getLabel() == 'Path':  path, params = mtype(params)
                elif enumLST[enumSEL].getLabel() == 'Order': params = getOrder(params)
                elif enumLST[enumSEL].getLabel() == 'Rules': params = getRules(params)
        del jsonRPC
        
        if len(params.get('rules',{}).get('and',[]) or params.get('rules',{}).get('and',[])) > 0:
            url = '%s?xsp=%s'%(path,dumpJSON(params))
            self.log('buildDXSP, returning %s'%(url))
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

        def __getInput():  return self.inputDialog("Enter Value\nSeparate by ',' ex. Action,Comedy",','.join([unquoteString(value) for value in rule.get('value',[])]))
        def __getBrowse(): return self.browseSources(default='|'.join([unquoteString(value) for value in rule.get('value',[])]))
        def __getSelect(): return self.notificationDialog(LANGUAGE(32020))
        enumLST = sorted(['Enter', 'Browse', 'Select'])
        enumKEY = {'Enter':{'func':__getInput},'Browse':{'func':__getBrowse},'Select':{'func':__getSelect}}
        enumSEL = self.selectDialog(enumLST,header="Select Input",useDetails=False, multi=False)
        if not enumSEL is None: return [quoteString(value) for value in (enumKEY[enumLST[enumSEL]].get('func')()).split(',')]