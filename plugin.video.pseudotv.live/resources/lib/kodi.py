  # Copyright (C) 2021 Lunatixz


# This file is part of PseudoTV Live.

# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

import os, json, traceback

from kodi_six  import xbmc, xbmcgui, xbmcvfs, xbmcaddon
from resources.lib.concurrency import PoolHelper

ADDON_ID      = 'plugin.video.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
LANGUAGE      = REAL_SETTINGS.getLocalizedString
COLOR_LOGO    = os.path.join(ADDON_PATH,'resources','skins','default','media','logo.png')
    
def splitPath(filepath):
    return (os.path.split(filepath))
    
def dumpJSON(item):
    try:    return json.dumps(item)
    except: return ''
    
def loadJSON(item):
    try:    return json.loads(item)
    except: return {}
    
def log(msg, level=xbmc.LOGDEBUG):
    if not REAL_SETTINGS.getSetting('Enable_Debugging') == "true" and level != xbmc.LOGERROR: return
    if not isinstance(msg,str): msg = str(msg)
    if level == xbmc.LOGERROR: msg = '%s\n%s'%((msg),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)

class Settings:
    realSetting = REAL_SETTINGS
    
    def __init__(self, reload=False):
        if reload: 
            REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
            self.realSetting = REAL_SETTINGS
            
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def _getSetting(self, func, key):
        try:
            value = func(key)
            self.log('%s, key = %s, value = %s'%(func.__name__,key,value))
            return value
        except Exception as e: 
            self.log("_getSetting, Failed! %s - key = %s"%(e,key), xbmc.LOGERROR)


    def getSetting(self, key):
        return self._getSetting(xbmcaddon.Addon(id=ADDON_ID).getSetting,key)
        
        
    def getSettingList(self, key):
        return self.getSetting(key).split('|')
    
    
    def getSettingDict(self, key):
        return loadJSON(self.getSetting(key))
    
    
    def getSettingBool(self, key):
        try:    return self._getSetting(xbmcaddon.Addon(id=ADDON_ID).getSettingBool,key)
        except: return self._getSetting(xbmcaddon.Addon(id=ADDON_ID).getSetting,key).lower() == "true" 
        
        
    def getSettingInt(self, key):
        try: return self._getSetting(xbmcaddon.Addon(id=ADDON_ID).getSettingInt,key)
        except:
            value = self._getSetting(xbmcaddon.Addon(id=ADDON_ID).getSetting,key)
            if value.isdecimal():
                return float(value)
            elif value.isdigit(): 
                return int(value)
            elif value: 
                return eval(value)
              
              
    def getSettingNumber(self, key): 
        try: return self._getSetting(xbmcaddon.Addon(id=ADDON_ID).getSettingNumber,key)
        except:
            value = self._getSetting(xbmcaddon.Addon(id=ADDON_ID).getSetting,key)
            if value.isdecimal():
                return float(value)
            elif value.isdigit(): 
                return int(value)    
            elif value: 
                return eval(value)
        
        
    def getSettingString(self, key):
        return self._getSetting(xbmcaddon.Addon(id=ADDON_ID).getSettingString,key)
        
        
    def openSettings(self):     
        self.realSetting.openSettings()
    

    def _setSetting(self, func, key, value):
        try:
            self.log('%s, key = %s, value = %s'%(func.__name__,key,value))
            func(key, value)
        except Exception as e: 
            self.log("_setSetting, Failed! %s - key = %s"%(e,key), xbmc.LOGERROR)
        
        
    def setSetting(self, key, value=""):  
        if not isinstance(value,str): value = str(value)
        self._setSetting(self.realSetting.setSetting,key,value)
            
            
    def setSettingDict(self, key, values):
        self.setSetting(key, dumpJSON(values))
            
            
    def setSettingList(self, key, values):
        self.setSetting(key, '|'.join(values))
        
        
    def setSettingBool(self, key, value):  
        if not isinstance(value,bool): value = value.lower() == "true"
        self._setSetting(self.realSetting.setSettingBool,key,value)
        
        
    def setSettingInt(self, key, value):  
        if not isinstance(value,int): value = int(value)
        self._setSetting(self.realSetting.setSettingInt,key,value)
        
        
    def setSettingNumber(self, key, value):  
        if not isinstance(value,float): value = float(value)
        self._setSetting(self.realSetting.setSettingNumber,key,value)
        
        
    def setSettingString(self, key, value):  
        if not isinstance(value,str): value = str(value)
        self._setSetting(self.realSetting.setSettingString,key,value)
        
        
class Properties:
    def __init__(self, winID=10000):
        self.winID  = winID
        self.window = xbmcgui.Window(winID)


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def getKey(self, key):
        if self.winID == 10000: #create unique id 
            return '%s.%s'%(ADDON_ID,key)
        else:
            return key


    def clearProperties(self):
        return self.window.clearProperties()
        
        
    def clearProperty(self, key):
        return self.window.clearProperty(self.getKey(key))


    def getPropertyList(self, key):
        return self.getProperty(key).split('|')

        
    def getPropertyBool(self, key):
        return self.getProperty(key).lower() == "true"
        
        
    def getPropertyDict(self, key):
        return loadJSON(self.getProperty(key))
        
        
    def getPropertyInt(self, key):
        value = self.getProperty(key)
        if value.isdecimal():
            return float(value)
        elif value.isdigit(): 
            return int(value)
        elif value: 
            return eval(value)
        

    def getProperty(self, key):
        value = self.window.getProperty(self.getKey(key))
        self.log('getProperty, id = %s, key = %s, value = %s'%(self.winID,self.getKey(key),value))
        return value
        
        
    def clearEXTProperty(self, key):
        return self.window.clearProperty(key)
        
        
    def getEXTProperty(self, key):
        return self.window.getProperty(key)
        
        
    def setEXTProperty(self, key, value):
        if not isinstance(value,str): value = str(value)
        return self.window.setProperty(key,value)
        
        
    def setPropertyList(self, key, values):
        return self.setProperty(key, '|'.join(values))
        
        
    def setPropertyBool(self, key, value):
        if not isinstance(value,bool): value = value.lower() == "true"
        return self.setProperty(key, value)
        
        
    def setPropertyDict(self, key, value):
        return self.setProperty(key, dumpJSON(value))
        
                
    def setPropertyInt(self, key, value):
        return self.setProperty(key, str(value))
        
        
    def setProperty(self, key, value):
        if not isinstance(value,str): value = str(value)
        self.log('setProperty, id = %s, key = %s, value = %s'%(self.winID,self.getKey(key),value))
        self.window.setProperty(self.getKey(key), value)
        return True


class Dialog:
    monitor    = xbmc.Monitor()
    settings   = Settings()
    properties = Properties()
    pool       = PoolHelper()
    
    def __init__(self):
        ...


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def toggleCHKInfo(self, state):
        self.properties.setPropertyBool('chkInfo',state)
        if state: self.properties.clearProperty('monitor.montiorList')
        else:     self.properties.clearProperty('chkInfo')
        
        
    @staticmethod
    def buildItemListItem(item, mType='video', oscreen=False, playable=True):
        LISTITEM_TYPES = {'label': (str,list),'genre': (list,str),
                          'country': (str,list),'year': (int,),'episode': (int,),
                          'season': (int,),'sortepisode': (int,),'sortseason': (int,),
                          'episodeguide': (str,),'showlink': (str,list),'top250': (int,),
                          'setid': (int,),'tracknumber': (int,),'rating': (float,),'userrating': (int,),
                          'playcount': (int,),'overlay': (int,),'cast': (list,),'castandrole': (list,),
                          'director': (str,list),'mpaa': (str,),'plot': (str,),'plotoutline': (str,),
                          'title': (str,),'originaltitle': (str,),'sorttitle': (str,),'duration': (int,),
                          'studio': (str,list),'tagline': (str,),'writer': (str,list),'tvshowtitle': (str,),
                          'premiered': (str,),'status': (str,),'set': (str,),'setoverview': (str,),'tag': (list,str),
                          'imdbnumber': (str,),'code': (str,),'aired': (str,),'credits': (str,list),'lastplayed': (str,),
                          'album': (str,),'artist': (list,),'votes': (str,),'path': (str,),'trailer': (str,),'dateadded': (str,),
                          'mediatype': (str,),'dbid': (int,),'track': (int,),'aspect': (float,),'codec': (str,),'language': (str,),
                          'width': (int,),'height': (int,),'duration': (int,),'channels': (int,),'audio': (list,),'video': (list,),
                          'subtitle': (list,),'stereomode': (str,),'count': (int,),'size': (int,),'date': (str,)}
                          
        info       = item.copy()
        art        = info.pop('art'                ,{})
        cast       = info.pop('cast'               ,[])
        uniqueid   = info.pop('uniqueid'           ,{})
        streamInfo = info.pop('streamdetails'      ,{})
        properties = info.pop('customproperties'   ,{})
        properties.update(info.get('citem'         ,{}))# write induvial props for keys 
        properties['citem']   = info.pop('citem'   ,{}) # write dump to single key
        properties['pvritem'] = info.pop('pvritem' ,{}) # write dump to single key
        
        def cleanInfo(ninfo):
            tmpInfo = ninfo.copy()
            for key, value in tmpInfo.items():
                types = LISTITEM_TYPES.get(key,None)
                if not types:# key not in json enum, move to customproperties
                    ninfo.pop(key)
                    properties[key] = value
                    continue
                    
                elif not isinstance(value,types):# convert to schema type
                    ninfo[key] = types[0](value)
                    
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
                
        listitem = xbmcgui.ListItem(offscreen=oscreen)
        if info.get('label'):  listitem.setLabel(info.get('label',''))
        if info.get('label2'): listitem.setLabel2(info.get('label2',''))
        if info.get('file'):   listitem.setPath(item.get('file','')) # (item.get('file','') or item.get('url','') or item.get('path',''))
        
        listitem.setInfo(type=mType, infoLabels=cleanInfo(info))
        listitem.setArt(art)
        listitem.setCast(cast)
        listitem.setUniqueIDs(uniqueid)
        # listitem.setProperties({})
    
        for ainfo in streamInfo.get('audio',[]):    listitem.addStreamInfo('audio'   , ainfo)
        for vinfo in streamInfo.get('video',[]):    listitem.addStreamInfo('video'   , vinfo)
        for sinfo in streamInfo.get('subtitle',[]): listitem.addStreamInfo('subtitle', sinfo)
        for key, pvalue in properties.items():      listitem.setProperty(key, cleanProp(pvalue))
        if playable: listitem.setProperty("IsPlayable","true")
        return listitem
             
         
    def okDialog(self, msg, heading=ADDON_NAME):
        return xbmcgui.Dialog().ok(heading, msg)
        
        
    def textviewer(self, msg, heading=ADDON_NAME, usemono=False):
        return xbmcgui.Dialog().textviewer(heading, msg, usemono)
        
    
    def yesnoDialog(self, message, heading=ADDON_NAME, nolabel='', yeslabel='', customlabel='', autoclose=0): 
        if customlabel:
            return xbmcgui.Dialog().yesnocustom(heading, message, customlabel, nolabel, yeslabel, autoclose)
        else: 
            return xbmcgui.Dialog().yesno(heading, message, nolabel, yeslabel, autoclose)


    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=4000, icon=COLOR_LOGO):
        self.log('notificationDialog: %s'%(message))
        ## - Builtin Icons:
        ## - xbmcgui.NOTIFICATION_INFO
        ## - xbmcgui.NOTIFICATION_WARNING
        ## - xbmcgui.NOTIFICATION_ERROR
        try: 
            xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except Exception as e:
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True
             
             
    def selectDialog(self, list, header=ADDON_NAME, preselect=None, useDetails=True, autoclose=0, multi=True):
        if multi == True:
            if preselect is None: preselect = [-1]
            select = xbmcgui.Dialog().multiselect(header, list, autoclose, preselect, useDetails)
        else:
            if preselect is None: preselect = -1
            select = xbmcgui.Dialog().select(header, list, autoclose, preselect, useDetails)
        return select
      
      
    def inputDialog(self, message, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
        ## - xbmcgui.INPUT_ALPHANUM (standard keyboard)
        ## - xbmcgui.INPUT_NUMERIC (format: #)
        ## - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
        ## - xbmcgui.INPUT_TIME (format: HH:MM)
        ## - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
        ## - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
        retval = xbmcgui.Dialog().input(message, default, key, opt, close)
        if retval: return retval
        return None
        
        
    def buildMenuListItem(self, label1="", label2="", iconImage=None, url="", infoItem=None, artItem=None, propItem=None, oscreen=False, mType='video'):
        listitem  = xbmcgui.ListItem(label1, label2, path=url, offscreen=oscreen)
        iconImage = (iconImage or COLOR_LOGO)
        if propItem: listitem.setProperties(propItem)
        if infoItem: listitem.setInfo(mType, infoItem)
        else: 
            listitem.setInfo(mType, {'mediatype': 'video',
                                     'Label' : label1,
                                     'Label2': label2,
                                     'Title' : label1})
                                         
        if artItem: listitem.setArt(artItem)
        else: 
            listitem.setArt({'thumb': iconImage,
                             'logo' : iconImage,
                             'icon' : iconImage})
        return listitem
        
        
    def browseDialog(self, type=0, heading=ADDON_NAME, default='', shares='', mask='', options=None, useThumbs=True, treatAsFolder=False, prompt=True, multi=False, monitor=False):
        def buildMenuItem(option):
            return self.buildMenuListItem(option['label'],option['label2'],iconImage=COLOR_LOGO)
            
        if prompt:
            if options is None:
                options = [{"label":"Video Playlists" , "label2":"Video Playlists"               , "default":"special://videoplaylists/"          , "mask":".xsp"                            , "type":1, "multi":False},
                           {"label":"Music Playlists" , "label2":"Music Playlists"               , "default":"special://musicplaylists/"          , "mask":".xsp"                            , "type":1, "multi":False},
                           {"label":"Video"           , "label2":"Video Sources"                 , "default":"library://video/"                   , "mask":xbmc.getSupportedMedia('video')   , "type":0, "multi":False},
                           {"label":"Music"           , "label2":"Music Sources"                 , "default":"library://music/"                   , "mask":xbmc.getSupportedMedia('music')   , "type":0, "multi":False},
                           {"label":"Pictures"        , "label2":"Picture Sources"               , "default":""                                   , "mask":xbmc.getSupportedMedia('picture') , "type":0, "multi":False},
                           {"label":"Files"           , "label2":"File Sources"                  , "default":""                                   , "mask":""                                , "type":0, "multi":False},
                           {"label":"Local"           , "label2":"Local Drives"                  , "default":""                                   , "mask":""                                , "type":0, "multi":False},
                           {"label":"Network"         , "label2":"Local Drives and Network Share", "default":""                                   , "mask":""                                , "type":0, "multi":False},
                           {"label":"Resources"       , "label2":"Resource Plugins"              , "default":"resource://"                        , "mask":""                                , "type":0, "multi":False}]
                if default:
                    default, file = splitPath(default)
                    if file: type = 1
                    else:    type = 0
                    options.insert(0,{"label":"Existing Path", "label2":default, "default":default , "mask":"", "type":type, "multi":False})
                    
            listitems = self.pool.poolList(buildMenuItem,options)
            select    = self.selectDialog(listitems, LANGUAGE(30116), multi=False)
            if select is not None:
                # if options[select]['default'] == "resource://": #TODO PARSE RESOURCE JSON, LIST PATHS
                    # listitems = self.pool.poolList(buildMenuItem,options)
                    # select    = self.selectDialog(listitems, LANGUAGE(30116), multi=False)
                    # if select is not None:
                # else:    
                shares    = options[select]['label'].lower().replace("network","")
                mask      = options[select]['mask']
                type      = options[select]['type']
                multi     = options[select]['multi']
                default   = options[select]['default']
            
        self.log('browseDialog, type = %s, heading= %s, shares= %s, mask= %s, useThumbs= %s, treatAsFolder= %s, default= %s'%(type, heading, shares, mask, useThumbs, treatAsFolder, default))
        if monitor: self.toggleCHKInfo(True)
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
        if monitor: self.toggleCHKInfo(False)
        if retval:
            if prompt and retval == default: return None
            return retval
        return None
        
        
    def notificationProgress(self, message, header=ADDON_NAME, wait=4):
        dia = self.progressBGDialog(message=message,header=header)
        for idx in range(wait):
            dia = self.progressBGDialog((((idx) * 100)//wait),control=dia,header=header)
            if self.monitor.waitForAbort(1): break
        return self.progressBGDialog(100,control=dia)


    def progressBGDialog(self, percent=0, control=None, message='', header=ADDON_NAME, silent=None):
        if not isinstance(percent,int): percent = int(percent)
        if silent is None:
            silent = (self.settings.getSettingBool('Silent_OnPlayback') & (self.properties.getPropertyBool('OVERLAY') | xbmc.getCondVisibility('Player.Playing')))
        
        if silent and hasattr(control, 'close'): 
            control.close()
            return
        elif control is None and percent == 0:
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
            if percent == 100 or control.isFinished(): 
                if hasattr(control, 'close'): control.close()
                return
            else: control.update(percent, header, message)
        elif control.iscanceled():
            if hasattr(control, 'close'): control.close()
            return
        return control
        
   
    def infoDialog(self, listitem):
        xbmcgui.Dialog().info(listitem)
        
        
class ListItems: #TODO move listitem funcs. here.
    def __init__(self):
        ...
