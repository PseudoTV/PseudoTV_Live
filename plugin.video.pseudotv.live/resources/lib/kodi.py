#   Copyright (C) 2023 Lunatixz
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
import json, uuid

from globals     import *
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
    finally:
        Builtin().executebuiltin('Dialog.Close(busydialognocancel)')

def setDictLST(lst=[]):
    sLST = [dumpJSON(d) for d in lst]
    sLST = list(OrderedDict.fromkeys(sLST))
    return [loadJSON(s) for s in sLST]

def dumpJSON(item, idnt=None, sortkey=False, separators=(',', ':')):
    if not isinstance(item,str):
        return json.dumps(item, indent=idnt, sort_keys=sortkey, separators=separators)
    elif isinstance(item,str):
        return item
    return ''
    
def loadJSON(item):
    if isinstance(item,str):
        return json.loads(item)
    elif isinstance(item,dict):
        return item
    return {}
      
def getMD5(text,hash=0,hexit=True):
    if isinstance(text,dict):     text = dumpJSON(text)
    elif not isinstance(text,str):text = str(text)
    for ch in text: hash = (hash*281 ^ ord(ch)*997) & 0xFFFFFFFF
    if hexit: return hex(hash)[2:].upper().zfill(8)
    else:     return hash

class Settings:       
    def __init__(self):
        self.cache    = Cache(mem_cache=True)
        self.property = Properties()

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def updateSettings(self):
        self.log('updateSettings')
        #todo build json of third-party addon settings
        # self.pluginMeta.setdefault(addonID,{})['settings'] = [{'key':'value'}]
 
        
    def getRealSettings(self):
        try:    return xbmcaddon.Addon(id=ADDON_ID)
        except: return REAL_SETTINGS


    def openSettings(self):     
        REAL_SETTINGS.openSettings()
    
    #GET
    def _getSetting(self, func, key):
        try: 
            value = func(key)
            self.log('%s, key = %s, value = %s'%(func.__name__,key,value))
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
        return loadJSON(self.getSetting(key))
    
    
    def getCacheSetting(self, key, checksum=ADDON_VERSION, json_data=False, default=None):
        return self.cache.get(key, checksum, json_data, default)
        
        
    def getPropertySetting(self, key):
        return self.property.getProperty(key)
    
    #SET
    def _setSetting(self, func, key, value):
        try:
            self.log('%s, key = %s, value = %s'%(func.__name__,key,value))
            return func(key, value)
        except Exception as e: 
            self.log("_setSetting, failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
            return False
            
        
    def setSetting(self, key, value=""):  
        if not isinstance(value,str): value = str(value)
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
        self.setSetting(key,dumpJSON(values))
            
            
    def setCacheSetting(self, key, value, checksum=ADDON_VERSION, life=datetime.timedelta(days=84), json_data=False):
        return self.cache.set(key, value, checksum, life, json_data)
            
            
    def setPropertySetting(self, key, value):
        return self.property.setProperty(key, value)
        
        
class Properties:
    def __init__(self, winID=10000):
        self.winID  = winID
        self.window = xbmcgui.Window(winID)


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def getInstanceID(self):
        instanceID = self.getEXTProperty('InstanceID') 
        if not instanceID: self.setEXTProperty('InstanceID',uuid.uuid4())
        return self.getEXTProperty('InstanceID')
      

    def getKey(self, key, instance=False):
        if self.winID == 10000 and not key.startswith(ADDON_ID): #create unique id 
            if instance:
                return '%s.%s.%s'%(ADDON_ID,key,getMD5(self.getInstanceID()))
            else:
                return '%s.%s'%(ADDON_ID,key)
        return key


    def clearProperties(self):
        return self.window.clearProperties()
        
        
    def clearProperty(self, key):
        return self.window.clearProperty(self.getKey(key))

    #GET
    def getPropertyList(self, key):
        return self.getProperty(key).split('|')

        
    def getPropertyBool(self, key):
        return self.getProperty(key).lower() == "true"
        
        
    def getPropertyDict(self, key=''):
        try:    return loadJSON(self.getProperty(key))
        except: return {}
        
        
    def getPropertyInt(self, key):
        return convertString2Num(self.getProperty(key))
            
        
    def getPropertyFloat(self, key):
        return float(convertString2Num(self.getProperty(key)))
        

    def getProperty(self, key):
        value = self.window.getProperty(self.getKey(key))
        self.log('getProperty, id = %s, key = %s, value = %s'%(self.winID,self.getKey(key),value))
        return value
        
        
    def clearEXTProperty(self, key):
        return self.window.clearProperty(key)
        
        
    def getEXTProperty(self, key):
        return xbmcgui.Window(10000).getProperty(key)
        
    #SET
    def setEXTProperty(self, key, value):
        if not isinstance(value,str): value = str(value)
        return xbmcgui.Window(10000).setProperty(key,value)
        
        
    def setPropertyList(self, key, values):
        return self.setProperty(key, '|'.join(values))
        
        
    def setPropertyBool(self, key, value):
        if not isinstance(value,bool): value = value.lower() == "true"
        return self.setProperty(key, value)
        
        
    def setPropertyDict(self, key, value={}):
        return self.setProperty(key, dumpJSON(value))
        
                
    def setPropertyInt(self, key, value):
        if not isinstance(value,int): value = int(value)
        return self.setProperty(key, value)
                
                
    def setPropertyFloat(self, key, value):
        if not isinstance(value,float): value = float(value)
        return self.setProperty(key, value)
        
        
    def setProperty(self, key, value):
        if not isinstance(value,str): value = str(value)
        self.log('setProperty, id = %s, key = %s, value = %s'%(self.winID,self.getKey(key),value))
        self.window.setProperty(self.getKey(key), value)
        return True

        
class ListItems:
    def __init__(self):
        ...

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def getListItem(self, label='', label2='', path='', offscreen=False):
        return xbmcgui.ListItem(label,label2,path,offscreen)


    def infoTagVideo(self, offscreen=False):
        return xbmc.InfoTagVideo(offscreen)


    def InfoTagMusic(self, offscreen=False):
        return xbmc.InfoTagVideo(offscreen)
        

    def buildItemListItem(self, item, media='video', oscreen=False, playable=True):
        if media == 'music':
            LISTITEM_TYPES = {'tracknumber'             : (int,),  #integer (8)
                              'discnumber'              : (int,),  #integer (2)
                              'duration'                : (int,),  #integer (245) - duration in seconds
                              'year'                    : (int,),  #integer (1998)
                              'genre'                   : (str,),  
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
                              'musicbrainztrackid'      : (str,),
                              'musicbrainzartistid'     : (str,),
                              'musicbrainzalbumid'      : (str,),
                              'musicbrainzalbumartistid': (str,),
                              'comment'                 : (str,),  
                              'count'                   : (int,),  #integer (12) - can be used to store an id for later, or for sorting purposes
                              # 'size'                    : (int,), #long (1024) - size in bytes
                              'date'                    : (str,),} #string (d.m.Y / 01.01.2009) - file date
        else:      
            LISTITEM_TYPES = {'genre'                   : (str,list),
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
                              
        info       = item.copy()
        art        = (info.pop('art'              ,{}) or {})
        cast       = (info.pop('cast'             ,[]) or [])
        uniqueid   = (info.pop('uniqueid'         ,{}) or {})
        streamInfo = (info.pop('streamdetails'    ,{}) or {})
        properties = (info.pop('customproperties' ,{}) or {})
        properties.update(info.get('citem'        ,{}))# write individual props for keys 
        properties['citem']   = info.pop('citem'  ,{}) # write dump to single key
        properties['pvritem'] = info.pop('pvritem',{}) # write dump to single key
        
        if media != 'video': #unify default artwork for music.
            art['poster'] = getThumb(info,opt=1)
            art['fanart'] = getThumb(info)
            
        def cleanInfo(ninfo):
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
                        except Exception as e:
                            self.log("buildItemListItem, cleanInfo error! %s\nkey = %s, value = %s, type = %s\n%s"%(e,key,value,type,ninfo), xbmc.LOGWARNING)
                         
                if isinstance(ninfo[key],list):
                    for n in ninfo[key]:
                        if isinstance(n,dict):
                            n = cleanInfo(n)
                            
                if isinstance(ninfo[key],dict):
                    ninfo[key] = cleanInfo(ninfo[key])
            return ninfo
                
        def cleanProp(pvalue):
            if isinstance(pvalue,dict):
                return dumpJSON(pvalue)
            elif isinstance(pvalue,list):
                return '|'.join(map(str, pvalue))
            elif not isinstance(pvalue,str):
                return str(pvalue)
            else:
                return pvalue
                
        listitem = self.getListItem(info.pop('label',''), info.pop('label2',''), info.pop('file',''), offscreen=oscreen)
        listitem.setArt(art)
        
        infoTag = ListItemInfoTag(listitem, media)
        infoTag.set_info(cleanInfo(info))
        if not media.lower() == 'music': 
            infoTag.set_cast(cast)
            infoTag.set_unique_ids(uniqueid)
            
        for ainfo in streamInfo.get('audio',[]):    infoTag.add_stream_info('audio'   , ainfo)
        for vinfo in streamInfo.get('video',[]):    infoTag.add_stream_info('video'   , vinfo)
        for sinfo in streamInfo.get('subtitle',[]): infoTag.add_stream_info('subtitle', sinfo)
        
        # listitem.setProperties({})
        # listitem.setIsFolder(True)
        for key, pvalue in list(properties.items()): listitem.setProperty(key, cleanProp(pvalue))
        if playable: listitem.setProperty("IsPlayable","true")
        return listitem
             
                     
    def buildMenuListItem(self, label1="", label2="", iconImage=None, url="", infoItem=None, artItem=None, propItem=None, oscreen=False, media='video'):
        listitem  = xbmcgui.ListItem(label1, label2, path=url, offscreen=oscreen)
        iconImage = (iconImage or COLOR_LOGO)
        if propItem: 
            listitem.setProperties(propItem)
        if infoItem: 
            if infoItem.get('label'):  listitem.setLabel(infoItem.pop('label',''))
            if infoItem.get('label2'): listitem.setLabel2(infoItem.pop('label2',''))
            infoTag = ListItemInfoTag(listitem, media)
            infoTag.set_info(infoItem)
        else: 
            listitem.setLabel(label1)
            listitem.setLabel2(label2)
            infoTag = ListItemInfoTag(listitem, media)
            infoTag.set_info({'mediatype': 'video', 'title' : label1})
                                         
        if artItem: 
            listitem.setArt(artItem)
        else: 
            listitem.setArt({'thumb': iconImage,
                             'logo' : iconImage,
                             'icon' : iconImage})
        return listitem
        
        
class Builtin: #todo move all infolabels, infobools, executers, etc here.
    def __init__(self):
        ...

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def getInfoLabel(self, key, param='ListItem', default=''):
        return (xbmc.getInfoLabel('%s.%s'%(param,key)) or default)
        
        
    def getInfoBool(self, key, param='Library', default=False):
        return (xbmc.getCondVisibility('%s.%s'%(param,key)) or default)
        
    
    def executebuiltin(self, key):
        self.log('executebuiltin, key=%s'%(key))
        return xbmc.executebuiltin('%s'%(key))
        
        
class Dialog:
    settings   = Settings()
    properties = Properties()
    listitems  = ListItems()
    builtin    = Builtin()
    
    def __init__(self):
        ...

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def chkInfoMonitor(self):
        return self.properties.getPropertyBool('chkInfoMonitor')
        
    
    def getInfoMonitor(self):
        return self.properties.getPropertyDict('monitor.montiorList').get('info',[])
    
    
    def setInfoMonitor(self, items):
        return self.properties.setPropertyDict('monitor.montiorList',{'info':list(setDictLST(items))})


    def toggleInfoMonitor(self, state, wait=0.1):
        self.log('toggleInfoMonitor, state = %s'%(state))
        self.properties.setPropertyBool('chkInfoMonitor',state)
        if state: 
            self.properties.clearProperty('monitor.montiorList')
            timerit(self.doInfoMonitor)(wait)


    def doInfoMonitor(self):
        while not MONITOR.abortRequested():
            if not self.fillInfoMonitor() or MONITOR.waitForAbort(1): break
            

    def fillInfoMonitor(self, type='ListItem'):
        #todo catch full listitem not singular properties.
        if not self.chkInfoMonitor(): return False
        item = {'label' :self.builtin.getInfoLabel('Label' ,type),
                'label2':self.builtin.getInfoLabel('Label2',type),
                'path'  :self.builtin.getInfoLabel('Path'  ,type),
                'writer':self.builtin.getInfoLabel('Writer',type),
                'logo'  :self.builtin.getInfoLabel('Icon'  ,type),
                'thumb' :self.builtin.getInfoLabel('Thumb' ,type)}
        if item.get('label'):
            montiorList = self.getInfoMonitor()
            montiorList.insert(0,item)
            self.setInfoMonitor(montiorList)
        return True
        

    def colorDialog(self, xml='', items=[], preselect=[], heading=ADDON_NAME):
        # https://xbmc.github.io/docs.kodi.tv/master/kodi-base/d6/de8/group__python___dialog.html#ga571ffd3c58c38b1f81d4f98eedb78bef
        # <colors>
          # <color name="white">ffffffff</color>
          # <color name="grey">7fffffff</color>
          # <color name="green">ff00ff7f</color>
        # </colors>
        # dialog.colorpicker('Select color', 'ff00ff00', 'os.path.join(xbmcaddon.Addon().getAddonInfo("path"),"colors.xml")')
        return xbmcgui.Dialog().colorpicker(heading, colorfile=xml, colorlist=items, selectedcolor=preselect)
             
        
    def _okDialog(self, msg, heading, autoclose, url, wait=0.5):
        timerit(self.okDialog)(wait,[msg, heading, autoclose, url])
        
        
    def okDialog(self, msg, heading=ADDON_NAME, autoclose=0, url=None, usethread=False):
        if usethread: return self._okDialog(msg, heading, autoclose, url)
        else:
            if autoclose > 0: timerit(Builtin().executebuiltin)(autoclose,['Dialog.Close(okdialog)'])
            # todo add qr code support
            # if not url is None and BUILTIN.getInfoBool('HasAddon(script.module.pyqrcode)','System'):
                # import pyqrcode
                # imagefile = os.path.join(xbmcvfs.translatePath(PROFILE),'%s.png' % str(url.split('/')[-1]))
                # qrIMG = pyqrcode.create(url)
                # qrIMG.png(imagefile, scale=10)
                # qr = QRCode( "main.xml" , ADDON_PATH, "default", image=imagefile, text=message)
                # qr.doModal()
                # del qr
                # xbmcvfs.delete(imagefile)
                # return
            return xbmcgui.Dialog().ok(heading, msg)


    def _textviewer(self, msg, heading, usemono, autoclose, wait=0.5):
        timerit(self.textviewer)(wait,[msg, heading, usemono, autoclose])
        
        
    def textviewer(self, msg, heading=ADDON_NAME, usemono=False, autoclose=0, usethread=False):
        if usethread: return self._textviewer(msg, heading, usemono, autoclose)
        else:
            if autoclose > 0: timerit(Builtin().executebuiltin)(autoclose,['Dialog.Close(textviewer)'])
            return xbmcgui.Dialog().textviewer(heading, msg, usemono)
        
    def yesnoDialog(self, message, heading=ADDON_NAME, nolabel='', yeslabel='', customlabel='', autoclose=0): 
        if autoclose > 0: autoclose = (autoclose*1000) #secs to msecs
        if customlabel:
            # Returns the integer value for the selected button (-1:cancelled, 0:no, 1:yes, 2:custom)
            return xbmcgui.Dialog().yesnocustom(heading, message, customlabel, nolabel, yeslabel, autoclose)
        else: 
            # Returns True if 'Yes' was pressed, else False.
            return xbmcgui.Dialog().yesno(heading, message, nolabel, yeslabel, autoclose)


    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=PROMPT_DELAY, icon=COLOR_LOGO):
        self.log('notificationDialog: %s'%(message))
        ## - Builtin Icons:
        ## - xbmcgui.NOTIFICATION_INFO
        ## - xbmcgui.NOTIFICATION_WARNING
        ## - xbmcgui.NOTIFICATION_ERROR
        try:    xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except: self.builtin.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True
             
             
    def selectDialog(self, list, header=ADDON_NAME, preselect=None, useDetails=True, autoclose=0, multi=True, custom=False):
        if autoclose > 0: autoclose = (autoclose*1000) #secs to msecs
        if multi == True:
            if preselect is None: preselect = [-1]
            if custom: ... #todo domodel custom selectDialog for library select.
            else:
                select = xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
        else:
            if preselect is None: preselect = -1
            if custom: ... #todo domodel custom selectDialog for library select.
            else:
                select = xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
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
            return self.listitems.buildMenuListItem(option['label'],option['label2'],iconImage=COLOR_LOGO)
            
        if prompt: 
            if options is None:
                options = [{"label":"Video Playlists" , "label2":"Video Playlists"               , "default":"special://profile/playlists/video/" , "mask":".xsp"                            , "type":1, "multi":False},
                           {"label":"Music Playlists" , "label2":"Music Playlists"               , "default":"special://profile/playlists/music/" , "mask":".xsp"                            , "type":1, "multi":False},
                           {"label":"Mixed Playlists" , "label2":"Mixed Playlists"               , "default":"special://profile/playlists/mixed/" , "mask":".xsp"                            , "type":1, "multi":False},
                           {"label":"Video"           , "label2":"Video Sources"                 , "default":"library://video/"                   , "mask":xbmc.getSupportedMedia('video')   , "type":0, "multi":False},
                           {"label":"Music"           , "label2":"Music Sources"                 , "default":"library://music/"                   , "mask":xbmc.getSupportedMedia('music')   , "type":0, "multi":False},
                           {"label":"Files"           , "label2":"File Sources"                  , "default":""                                   , "mask":""                                , "type":0, "multi":False},
                           {"label":"Local"           , "label2":"Local Drives"                  , "default":""                                   , "mask":""                                , "type":0, "multi":False},
                           {"label":"Network"         , "label2":"Local Drives and Network Share", "default":""                                   , "mask":""                                , "type":0, "multi":False},
                           {"label":"Pictures"        , "label2":"Picture Sources"               , "default":""                                   , "mask":xbmc.getSupportedMedia('picture') , "type":0, "multi":False},
                           {"label":"Resources"       , "label2":"Resource Plugins"              , "default":"resource://"                        , "mask":""                                , "type":0, "multi":False}]
                if default:
                    default, file = os.path.split(default)
                    if file: type = 1
                    else:    type = 0
                    options.insert(0,{"label":"Existing Path", "label2":default, "default":default , "mask":"", "type":type, "multi":False})
                   
            with busy_dialog():
                lizLST = poolit(buildMenuItem)(options)
            select = self.selectDialog(lizLST, LANGUAGE(32089), multi=False)
            if select is not None:
                # if options[select]['default'] == "resource://": #TODO PARSE RESOURCE JSON, LIST PATHS
                    # listitems = self.pool.poolList(buildMenuItem,options)
                    # select    = self.selectDialog(listitems, LANGUAGE(32089), multi=False)
                    # if select is not None:
                # else:    
                shares    = options[select]['label'].lower().replace("network","")
                mask      = options[select]['mask']
                type      = options[select]['type']
                multi     = options[select]['multi']
                default   = options[select]['default']
            else: return
                
        self.log('browseDialog, type = %s, heading= %s, shares= %s, mask= %s, useThumbs= %s, treatAsFolder= %s, default= %s'%(type, heading, shares, mask, useThumbs, treatAsFolder, default))
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
        

    def notificationWait(self, message, header=ADDON_NAME, wait=4):
        if not isinstance(wait,int): wait = int(wait)
        pDialog = self.progressBGDialog(message=message,header=header)
        for idx in range(wait):
            pDialog = self.progressBGDialog((((idx+1) * 100)//wait),control=pDialog,header=header)
            if pDialog is None or MONITOR.waitForAbort(1): break
        return True


    def progressBGDialog(self, percent=0, control=None, message='', header=ADDON_NAME, silent=None):
        if not isinstance(percent,int): percent = int(percent)
        if silent is None: 
            silent = (self.settings.getSettingBool('Silent_OnPlayback') & (self.properties.getPropertyBool('OVERLAY') | self.builtin.getInfoBool('Playing','Player')))
        
        if silent:
            if hasattr(control, 'close'): control.close()
            return 
            
        if control is None and percent == 0:
            control = xbmcgui.DialogProgressBG()
            control.create(header, message)
        elif control:
            if percent == 100 or control.isFinished(): 
                if hasattr(control, 'close'): control.close()
                return
            elif hasattr(control, 'update'): control.update(percent, header, message)
        return control
        

    def progressDialog(self, percent=0, control=None, message='', header=ADDON_NAME):
        if not isinstance(percent,int): percent = int(percent)
        if control is None and percent == 0:
            control = xbmcgui.DialogProgress()
            control.create(header, message)
        elif control:
            if percent == 100 or control.iscanceled(): 
                if hasattr(control, 'close'): control.close()
                return
            elif hasattr(control, 'update'): control.update(percent, message)
        return control
        
   
    def infoDialog(self, listitem):
        xbmcgui.Dialog().info(listitem)
        