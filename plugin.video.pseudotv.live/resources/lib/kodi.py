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

#variables
DEBUG_ENABLED       = REAL_SETTINGS.getSetting('Enable_Debugging').lower() == 'true'
MONITOR             = xbmc.Monitor()

def log(event, level=xbmc.LOGDEBUG):
    if not DEBUG_ENABLED and level != xbmc.LOGERROR: return #todo use debug level filter
    if level == xbmc.LOGERROR: event = '%s\n%s'%(event,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,event),level)
    
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
    except:
        return ''

def getAbbr(text):
    words = text.split(' ')
    if len(words) > 1: return '%s.%s.'%(words[0][0].upper(),words[1][0].upper())
    else: return words[0][0].upper()
   
def getThumb(item={},opt=0): #unify thumbnail artwork
    keys = {0:['landscape','fanart','thumb','thumbnail','poster','clearlogo','logo','logos','clearart','keyart,icon'],
            1:['poster','clearlogo','logo','logos','clearart','keyart','landscape','fanart','thumb','thumbnail','icon']}[opt]
    for key in keys:
        art = (item.get('art',{}).get('album.%s'%(key),'')       or 
               item.get('art',{}).get('albumartist.%s'%(key),'') or 
               item.get('art',{}).get('artist.%s'%(key),'')      or 
               item.get('art',{}).get('season.%s'%(key),'')      or 
               item.get('art',{}).get('tvshow.%s'%(key),'')      or 
               item.get('art',{}).get(key,'')                    or
               item.get(key,''))
        if art: return art
    return {0:FANART,1:COLOR_LOGO}[opt]
               
def isBusyDialog():
    return (Builtin().getInfoBool('IsActive(busydialognocancel)','Window') | Builtin().getInfoBool('IsActive(busydialog)','Window'))

def closeBusyDialog():
    if Builtin().getInfoBool('IsActive(busydialognocancel)','Window'):
        Builtin().executebuiltin('Dialog.Close(busydialognocancel)')
    elif Builtin().getInfoBool('IsActive(busydialog)','Window'):
        Builtin().executebuiltin('Dialog.Close(busydialog)')

@contextmanager
def busy_dialog():
    if not isBusyDialog():
        Builtin().executebuiltin('ActivateWindow(busydialognocancel)')
        try: yield
        finally: Builtin().executebuiltin('Dialog.Close(busydialognocancel)')
    else: yield
                  
@contextmanager
def sudo_dialog(msg):
    dia = Dialog().progressBGDialog((int(time.time()) % 60),Dialog().progressBGDialog(message=msg))
    try: 
        yield
    finally: 
        dia = Dialog().progressBGDialog(100,dia)

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

def getMD5(text,hash=0,hexit=True):
    if isinstance(text,dict):     text = dumpJSON(text)
    elif not isinstance(text,str):text = str(text)
    for ch in text: hash = (hash*281 ^ ord(ch)*997) & 0xFFFFFFFF
    if hexit: return hex(hash)[2:].upper().zfill(8)
    else:     return hash

def getCRC32(text):
    return binascii.crc32(text.encode('utf8'))
    
def convertString(data):
    if isinstance(data, dict):
        return dumpJSON(data)
    elif isinstance(data, list):
        return ', '.join(data)
    elif isinstance(data, bytes):
        return data.decode(DEFAULT_ENCODING)
    elif not isinstance(data, str):
        return str(data)
    else:
        return data
             
class Settings:
    #Kodi often breaks settings API with changes between versions. Stick with core setsettings/getsettings to avoid specifics; that may break.
    def __init__(self):
        self.cache    = Cache()
        self.property = Properties()

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def getRealSettings(self):
        try:    return xbmcaddon.Addon(id=ADDON_ID)
        except: return REAL_SETTINGS


    def updateSettings(self):
        self.log('updateSettings')
        #todo build json of third-party addon settings
        # self.pluginMeta.setdefault(addonID,{})['settings'] = [{'key':'value'}]
 
        
    def openSettings(self):
        self.log('openSettings')
        REAL_SETTINGS.openSettings()
    
    
    #GET
    def _getSetting(self, func, key):
        try: 
            value = func(key)
            self.log('%s, key = %s, value = %s'%(func.__name__,key,'%s...'%((convertString(value)[:128]))))
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
    
    
    def getCacheSetting(self, key, checksum=ADDON_VERSION, json_data=False):
        return self.cache.get(key, checksum, json_data)
        
        
    def getPropertySetting(self, key):
        return self.property.getProperty(key)
    
    
    #SET
    def _setSetting(self, func, key, value):
        try:
            self.log('%s, key = %s, value = %s'%(func.__name__,key,'%s...'%((convertString(value)[:128]))))
            return func(key, value)
        except Exception as e: 
            self.log("_setSetting, failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
            return False
            
        
    def setSetting(self, key, value=""):  
        if not isinstance(value,str): value = str(value)
        if self.getSetting(key) != value: #Kodi setsetting() can tax system performance. i/o issue? block redundant saves.
            self._setSetting(self.getRealSettings().setSetting,key,value)
            
            
    def setSettingBool(self, key, value):
        self.setSetting(key,value)
        
                      
    def setSettingBoolList(self, key, value):
        self.setSetting(key,('|').join(value))
        
           
    def setSettingInt(self, key, value):  
        self.setSetting(key,value)
        
        
    def setSettingIntList(self, key, value):  
        self.setSetting(key,('|').join(value))
         
            
    def setSettingNumber(self, key, value):  
        self.setSetting(key,value)
        
            
    def setSettingNumberList(self, key, value):  
        self.setSetting(key,('|').join(value))
        
            
    def setSettingString(self, key, value):  
        self.setSetting(key,value)
        

    def setSettingList(self, key, values):
        self.setSetting(key,('|').join(value))
                   
                   
    def setSettingFloat(self, key, value):  
        self.setSetting(key,value)
        
        
    def setSettingDict(self, key, values):
        self.setSetting(key,encodeString(dumpJSON(values)))
            
            
    def setCacheSetting(self, key, value, checksum=ADDON_VERSION, life=datetime.timedelta(days=84), json_data=False):
        return self.cache.set(key, value, checksum, life, json_data)
            
            
    def setPropertySetting(self, key, value):
        return self.property.setProperty(key, value)

        
    def getEXTMeta(self, id):
        addon = xbmcaddon.Addon(id)
        properties = ['name', 'version', 'summary', 'description', 'path', 'author', 'icon', 'disclaimer', 'fanart', 'changelog', 'id', 'profile', 'stars', 'type']
        for property in properties: yield (property, addon.getAddonInfo(property))


    def getEXTSetting(self, id, key):
        return xbmcaddon.Addon(id).getSetting(key)
        
        
    def setEXTSetting(self, id, key, value):
        return xbmcaddon.Addon(id).setSetting(key,value)
        


    def chkPluginSettings(self, id, values, override=False, prompt=True):
        self.log('chkPluginSettings, id = %s, override=%s'%(id,override))
        try: 
            if override:
                changes = dict([(s, (v,v)) for s, v in list(values.items())])
            else:
                changes = {}
                addon   = xbmcaddon.Addon(id)
                if addon is None: raise Exception('%s Not Found'%id)
                
                for s, v in list(values.items()):
                    if MONITOR.waitForAbort(1.0): return False
                    value = addon.getSetting(s)
                    if str(value).lower() != str(v).lower(): changes[s] = (value, v)
            if changes: return self.setPluginSettings(id,changes,prompt)
        except: self.dialog.notificationDialog(LANGUAGE(32034)%(id))
        return False
            
            
    def setPluginSettings(self, id, values, prompt=True):
        self.log('setPluginSettings, id = %s, prompt = %s'%(id,prompt))
        try:
            addon = xbmcaddon.Addon(id)
            addon_name = addon.getAddonInfo('name')
            if addon is None: raise Exception('%s Not Found'%id)
            
            if prompt:
                self.dialog.textviewer('%s\n\n%s'%((LANGUAGE(32035)%(addon_name)),('\n'.join(['Modifying %s: [COLOR=dimgray][B]%s[/B][/COLOR] => [COLOR=green][B]%s[/B][/COLOR]'%(s,v[0],v[1]) for s,v in list(values.items())]))))
                if not self.dialog.yesnoDialog((LANGUAGE(32036)%addon_name)): return False
                
            for s, v in list(values.items()):
                if MONITOR.waitForAbort(1.0): return False
                addon.setSetting(s, v[1])
            self.setPVRInstance(id)
            return self.dialog.notificationDialog((LANGUAGE(32037)%(addon_name)))
        except: self.dialog.notificationDialog(LANGUAGE(32034)%(id))
        return False


    def chkPVRInstance(self, path):
        found = False
        for file in [filename for filename in FileAccess.listdir(path)[1] if filename.endswith('.xml')]:
            if MONITOR.waitForAbort(1.0): break
            elif file.startswith('instance-settings-'):
                try:
                    xml = FileAccess.open(os.path.join(path,file), "r")
                    txt = xml.read()
                    xml.close()
                except Exception as e:
                    self.log('chkPVRInstance, path = %s, failed to open file = %s\n%s'%(path,file,e))
                    continue
                    
                name = re.compile('<setting id=\"kodi_addon_instance_name\">(.*?)\</setting>', re.IGNORECASE).search(txt)
                if name: name = name.group(1)
                else:
                    name = re.compile('<setting id=\"kodi_addon_instance_name\" default=\"true\">(.*?)\</setting>', re.IGNORECASE).search(txt)
                    if name: name = name.group(1)
                    else: continue
                
                if name == ADDON_NAME:
                    if found ==  False:
                        found = file
                    else:
                        FileAccess.delete(os.path.join(path,file))
                        self.log('chkPVRInstance, removing duplicate entry %s'%(file))
        self.log('chkPVRInstance, found file = %s'%(found))
        return found


    def setPVRInstance(self, id):
        # # https://github.com/xbmc/xbmc/pull/23648
        # newid = REAL_SETTINGS.getFreeNewInstanceId()
        # addonsettingnew = REAL_SETTINGS.getSettings(newid)
        # addonsettingnew.setString('kodi_addon_instance_name', 'By Python added')
        # addonsettingnew.setBool('kodi_addon_instance_enabled', True)
        # addonsettingnew.setString('host', '10.144.12.13')
        # REAL_SETTINGS.publishInstanceChange(newid
        # # REAL_SETTINGS.deleteInstanceId(1001);
        # printstring = "Support Instances: " + str(REAL_SETTINGS.supportsInstanceSettings()) + "\n" \
                      # "Used Instances:\n"
        # for x in REAL_SETTINGS.getKnownInstanceIds():
            # printstring += "ID: " + str(x) + "\n"
            # printstring += "Test setting: " + REAL_SETTINGS.getSettings(x).getString('host') + "\n"
        # xbmcgui.Dialog().textviewer(ADDON_NAME, printstring)
        
        settingInstance = 1
        pvrPath = 'special://profile/addon_data/%s'%(PVR_CLIENT_ID)
        pvrFile = self.chkPVRInstance(pvrPath)
        if pvrFile != False:
            self.log('setPVRInstance, id = %s deleting %s...'%(id,pvrFile))
            FileAccess.delete(os.path.join(pvrPath,pvrFile))
            settingInstance += int(re.compile('instance-settings-([0-9.]+).xml', re.IGNORECASE).search(pvrFile).group(1))
            
        #copy new instance settings
        if FileAccess.exists(os.path.join(pvrPath,'settings.xml')):
            self.log('setPVRInstance, id = %s creating %s...'%(id,'instance-settings-%d.xml'%(settingInstance)))
            return FileAccess.copy(os.path.join(pvrPath,'settings.xml'),os.path.join(pvrPath,'instance-settings-%d.xml'%(settingInstance)))
           
        
    def getCurrentSettings(self):
        self.log('getCurrentSettings')
        settings = ['User_Folder','Network_Folder','UDP_PORT','TCP_PORT','Client_Mode','Remote_URL','Disable_Cache','Disable_Trakt','Rollback_Watched']
        for setting in settings:
            yield (setting,self.getSetting(setting))
               
        
class Properties:
    
    def __init__(self, winID=10000):
        self.winID      = winID
        self.window     = xbmcgui.Window(winID)
        self.InstanceID = self.getInstanceID()


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def setInstanceID(self):
        instanceID = self.getEXTProperty('%s.InstanceID'%(ADDON_ID))
        if instanceID: self.clearTrash(instanceID)
        self.setEXTProperty('%s.InstanceID'%(ADDON_ID),getMD5(uuid.uuid4()))


    def getInstanceID(self):
        instanceID = self.getEXTProperty('%s.InstanceID'%(ADDON_ID))
        if not instanceID: self.setInstanceID()
        return self.getEXTProperty('%s.InstanceID'%(ADDON_ID))
      

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
        self.log('getEXTProperty, id = %s, key = %s, value = %s'%(10000,key,'%s...'%(convertString(value)[:128])))
        return value
        
        
    def getProperty(self, key):
        key   = self.getKey(key)
        value = self.window.getProperty(key)
        self.log('getProperty, id = %s, key = %s, value = %s'%(self.winID,key,'%s...'%(convertString(value)[:128])))
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
        self.log('setEXTProperty, id = %s, key = %s, value = %s'%(10000,key,'%s...'%((convertString(value)[:128]))))
        xbmcgui.Window(10000).setProperty(key,str(value))
        return True
        
        
    def setProperty(self, key, value):
        key = self.getKey(key)
        self.log('setProperty, id = %s, key = %s, value = %s'%(self.winID,key,'%s...'%((convertString(value)[:128]))))
        self.window.setProperty(key, str(value))
        return value
        
        
    def setPropertyList(self, key, values):
        if self.setProperty(key, '|'.join(values)):
            return value
        
        
    def setPropertyBool(self, key, value):
        if self.setProperty(key, value):
            return value
        
        
    def setPropertyDict(self, key, value={}):
        if self.setProperty(key, encodeString(dumpJSON(value))):
            return value
        
                
    def setPropertyInt(self, key, value):
        if self.setProperty(key, int(value)):
            return value
                
                
    def setPropertyFloat(self, key, value):
        if self.setProperty(key, float(value)):
            return value

    
    def setTrash(self, key): #catalog instance properties that may become abandoned. 
        tmpDCT = loadJSON(self.getEXTProperty('%s.TRASH'%(ADDON_ID)))
        if key not in tmpDCT.setdefault(self.InstanceID,[]):
            tmpDCT.setdefault(self.InstanceID,[]).append(key)
        self.setEXTProperty('%s.TRASH'%(ADDON_ID),dumpJSON(tmpDCT))
        return key

        
    def clearTrash(self, instanceID=None): #clear abandoned properties after instanceID change
        tmpDCT = loadJSON(self.getEXTProperty('%s.TRASH'%(ADDON_ID)))
        for prop in tmpDCT.get(instanceID,[]): self.clearEXTProperty(prop)
        
        
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
        properties.update(info.get('citem'        ,{}))# write individual props for keys / needed? legacy!
        properties['citem']   = info.pop('citem'  ,{}) # write dump to single key
        properties['pvritem'] = info.pop('pvritem',{}) # write dump to single key
        
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
    
    
    def getInfoLabel(self, key, param='ListItem', default=''):
        value = (xbmc.getInfoLabel('%s.%s'%(param,key)) or default)
        self.log('getInfoLabel, key = %s.%s, value = %s'%(param,key,value))
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
        while not MONITOR.abortRequested():
            if not self.fillInfoMonitor() or MONITOR.waitForAbort(0.5): break
            

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
        if Builtin().getInfoBool('IsActive(okdialog)','Window'):
            Builtin().executebuiltin('Dialog.Close(okdialog)')
        
        
    def _okDialog(self, msg, heading, autoclose, url):
        timerit(self.okDialog)(0.5,[msg, heading, autoclose])


    def okDialog(self, msg, heading=ADDON_NAME, autoclose=AUTOCLOSE_DELAY, usethread=False):
        if usethread: return self._okDialog(msg, heading, autoclose)
        else:
            if autoclose > 0: timerit(self._closeOkDialog)(autoclose)
            return xbmcgui.Dialog().ok(heading, msg)


    def _closeTextViewer(self):
        if Builtin().getInfoBool('IsActive(textviewer)','Window'):
            Builtin().executebuiltin('Dialog.Close(textviewer)')
        
        
    def _textViewer(self, msg, heading, usemono, autoclose):
        timerit(self.textviewer)(0.5,[msg, heading, usemono, autoclose])
        
        
    def textviewer(self, msg, heading=ADDON_NAME, usemono=False, autoclose=AUTOCLOSE_DELAY, usethread=False):
        if usethread: return self._textViewer(msg, heading, usemono, autoclose)
        else:
            if autoclose > 0: timerit(self._closeTextViewer)(autoclose)
            return xbmcgui.Dialog().textviewer(heading, msg, usemono)
        
        
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
                if pDialog is None or MONITOR.waitForAbort(1.0): break
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
        

    def browseDialog(self, type=0, heading=ADDON_NAME, default='', shares='', mask='', options=None, useThumbs=True, treatAsFolder=False, prompt=True, multi=False, monitor=False):
        def buildMenuItem(option):
            return self.listitems.buildMenuListItem(option['label'],option['label2'],DUMMY_ICON.format(text=getAbbr(option['label'])))
            
        if prompt: 
            optTMP = []
            proOpt = [{"label":"Video Playlists" , "label2":"special://profile/playlists/video/" , "default":"special://profile/playlists/video/" , "mask":".xsp"                            , "type":1    , "multi":False},
                      {"label":"Music Playlists" , "label2":"special://profile/playlists/music/" , "default":"special://profile/playlists/music/" , "mask":".xsp"                            , "type":1    , "multi":False},
                      {"label":"Mixed Playlists" , "label2":"special://profile/playlists/mixed/" , "default":"special://profile/playlists/mixed/" , "mask":".xsp"                            , "type":1    , "multi":False},
                      {"label":"Dynamic Playlist", "label2":"Create Dynamic Smartplaylist"       , "default":""                                   , "mask":""                                , "type":1    , "multi":False},
                      {"label":"Video"           , "label2":"library://video/"                   , "default":"library://video/"                   , "mask":xbmc.getSupportedMedia('video')   , "type":0    , "multi":False},
                      {"label":"Music"           , "label2":"library://music/"                   , "default":"library://music/"                   , "mask":xbmc.getSupportedMedia('music')   , "type":0    , "multi":False},
                      {"label":"Files"           , "label2":"All Folders & Files"                , "default":""                                   , "mask":mask                              , "type":type , "multi":False},
                      {"label":"Local"           , "label2":"Local Folders & Files"              , "default":""                                   , "mask":mask                              , "type":type , "multi":False},
                      {"label":"Network"         , "label2":"Local Drives and Network Share"     , "default":""                                   , "mask":mask                              , "type":type , "multi":False},
                      {"label":"Pictures"        , "label2":"Picture Sources"                    , "default":""                                   , "mask":xbmc.getSupportedMedia('picture') , "type":1    , "multi":False},
                      {"label":"Resources"       , "label2":"Resource Plugins"                   , "default":"resource://"                        , "mask":mask                              , "type":type , "multi":False}
                      ]

            if isinstance(options,list): [optTMP.append(proOpt[idx]) for idx in options]
            else: optTMP = proOpt
                
            if default:
                default, file = os.path.split(default)
                if file: type = 1
                else:    type = 0
                optTMP.insert(0,{"label":"Current Path", "label2":default, "default":default , "mask":mask, "type":type, "multi":multi})
                   
            with busy_dialog():
                lizLST = poolit(buildMenuItem)(optTMP)
                
            select = self.selectDialog(lizLST, LANGUAGE(32089), multi=False)
            if   optTMP[select].get('label') == "Dynamic Playlist": return self.buildDXSP(default)
            elif optTMP[select].get('label') == "Resource Plugins": return self.buildResource(default, mask)
            elif select is not None:
                shares    = optTMP[select]['label'].lower().replace("network","")
                mask      = optTMP[select]['mask']
                type      = optTMP[select]['type']
                multi     = optTMP[select]['multi']
                default   = optTMP[select]['default']
            else: return
                
        self.log('browseDialog, type = %s, heading= %s, shares= %s, useThumbs= %s, treatAsFolder= %s, default= %s\nmask= %s'%(type, heading, shares, useThumbs, treatAsFolder, default, mask))
        if monitor: self.toggleInfoMonitor(True)
        if multi == True:
            ## https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#ga856f475ecd92b1afa37357deabe4b9e4
            ## type integer - the type of browse dialog.
            ## 1	ShowAndGetFile
            ## 2	ShowAndGetImage
            retval = xbmcgui.Dialog().browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        else:
            ## https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#gafa1e339e5a98ae4ea4e3d3bb3e1d028c
            ## type integer - the type of browse dialog.
            ## 0	ShowAndGetDirectory
            ## 1	ShowAndGetFile
            ## 2	ShowAndGetImage
            ## 3	ShowAndGetWriteableDirectory
            retval = xbmcgui.Dialog().browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        if monitor: self.toggleInfoMonitor(False)
        if options is not None and default == retval: return
        return retval
        
        
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
        return default
        

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
            while not MONITOR.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),str(value),icon=DUMMY_ICON.format(text=getAbbr(key.title())),props={'key':key,'value':value}) for key, value in list(rule.items())]
                enumSEL = self.selectDialog(enumLST,header="Select method",preselect=-1, multi=False)
                if not enumSEL is None: rule.update({enumLST[enumSEL].getProperty('key'):({"field":field,"operator":operator,"value":value}[enumLST[enumSEL].getProperty('key')])(params,rule)})
            return rule
            
        def getRules(params={}):
            enumSEL = -1
            while not MONITOR.abortRequested() and not enumSEL is None:
                enumLST = [self.listitems.buildMenuListItem(key.title(),dumpJSON(params.get('rules',{}).get(key,[])),icon=DUMMY_ICON.format(text=getAbbr(key.title())),props={'key':key}) for key in ["and","or"]]
                enumSEL = self.selectDialog(enumLST,header="Edit Rules",multi=False)
                if not enumSEL is None:
                    if enumLST[enumSEL].getLabel() in ['And','Or']:
                        CONSEL  = -1
                        CONLKEY = enumLST[enumSEL].getProperty('key')
                        ruleLST = params.get('rules',{}).get(CONLKEY,[])
                        while not MONITOR.abortRequested() and not CONSEL is None:
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
            while not MONITOR.abortRequested() and not enumSEL is None:
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
        while not MONITOR.abortRequested() and not enumSEL is None:
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



