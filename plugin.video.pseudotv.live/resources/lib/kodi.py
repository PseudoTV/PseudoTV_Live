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

import os
import resources.lib.globals as globals

from kodi_six import xbmc, xbmcgui, xbmcaddon

ADDON_ID      = 'plugin.video.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
COLOR_LOGO    = os.path.join(ADDON_PATH,'resources','skins','default','media','logo.png')

class Settings:
    def __init__(self, addon):
        self.SETTINGS = addon

         
    def log(self, msg, level=xbmc.LOGDEBUG):
        return globals.log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def getSettings(self, key):
        return self.getSetting(key).split('|')
    
    
    def getSetting(self, key):
        value = self.SETTINGS.getSetting(key)
        self.log('getSetting, key = %s, value = %s'%(key,value))
        return value
        
        
    def getSettingBool(self, key):
        try:    return self.SETTINGS.getSettingBool(key)
        except: return self.getSetting(key).lower() == "true" 
        
        
    def getSettingInt(self, key):
        try: return self.SETTINGS.getSettingInt(key)
        except:
            value = self.getSetting(key)
            if value.isdecimal():
                return float(value)
            elif value.isdigit(): 
                return int(value)
              
              
    def getSettingNumber(self, key): 
        try: return self.SETTINGS.getSettingNumber(key)
        except:
            value = self.getSetting(key)
            if value.isdecimal():
                return float(value)
            elif value.isdigit(): 
                return int(value)    
        
        
    def getSettingString(self, key):     
        return self.SETTINGS.getSettingString(key)
        
        
    def openSettings(self):     
        return self.SETTINGS.openSettings()
    
    
    def setSettings(self, key, values):
        return self.setSetting(key, '|'.join(values))
        
    
    def setSetting(self, key, value):  
        self.log('setSetting, key = %s, value = %s'%(key,value))
        if not isinstance(value,globals.basestring): value = str(value)
        return self.SETTINGS.setSetting(key, value)
        
        
    def setSettingBool(self, key, value):  
        if not isinstance(value,bool): value = value.lower() == "true"
        return self.SETTINGS.setSettingBool(key, value)
        
        
    def setSettingInt(self, key, value):  
        if not isinstance(value,int): value = int(value)
        return self.SETTINGS.setSettingInt(key, value)
        
        
    def setSettingNumber(self, key, value):  
        if not isinstance(value,float): value = float(value)
        return self.SETTINGS.setSettingNumber(key, value)
        
        
    def setSettingString(self, key, value):  
        if not isinstance(value,globals.basestring): value = str(value)
        return self.SETTINGS.setSettingString(key, value)
        
        
class Properties:
    def __init__(self, winID=10000):
        self.winID  = winID
        self.WINDOW = xbmcgui.Window(winID)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return globals.log('%s: %s'%(self.__class__.__name__,msg),level)


    def getKey(self, key):
        if self.winID == 10000: #create unique id 
            return '%s.%s'%(globals.ADDON_ID,key)
        else:
            return key


    def clearProperties(self):
        return self.WINDOW.clearProperties()
        
        
    def clearProperty(self, key):
        return self.WINDOW.clearProperty(self.getKey(key))


    def getProperties(self, key):
        return self.getProperty(key).split('|')

        
    def getPropertyBool(self, key):
        return self.getProperty(key).lower() == "true"


    def getProperty(self, key):
        value = self.WINDOW.getProperty(self.getKey(key))
        self.log('getProperty, id = %s, key = %s, value = %s'%(self.winID,self.getKey(key),value))
        return value
        
        
    def clearEXTProperty(self, key):
        return self.WINDOW.clearProperty(key)
        
        
    def getEXTProperty(self, key):
        return self.WINDOW.getProperty(key)
        
        
    def setEXTProperty(self, key, value):
        if not isinstance(value,globals.basestring): value = str(value)
        return self.WINDOW.setProperty(key,value)
        
        
    def setProperties(self, key, values):
        return self.setProperty(key, '|'.join(values))
        
        
    def setPropertyBool(self, key, value):
        if not isinstance(value,bool): value = value.lower() == "true"
        return self.setProperty(key, value)
        
        
    def setProperty(self, key, value):
        if not isinstance(value,globals.basestring): value = str(value)
        self.log('setProperty, id = %s, key = %s, value = %s'%(self.winID,self.getKey(key),value))
        return self.WINDOW.setProperty(self.getKey(key), value)


class Dialog:
    def __init__(self, dialog=None, progress=0):
        if dialog is None: 
            self.dialog = xbmcgui.Dialog()
        else:
            self.dialog = dialog
            
        self.progress   = progress
        self.onPlayback = globals.getSettingBool('Silent_OnPlayback') #unify silent mode amongst dialogs 
        self.isPlaying  = xbmc.getCondVisibility('Player.Playing')
        self.isOverlay  = globals.isOverlay()
        
                 
    def log(self, msg, level=xbmc.LOGDEBUG):
        return globals.log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def okDialog(self, msg, heading=ADDON_NAME):
        return self.dialog.ok(heading, msg)
        
        
    def textviewer(self, msg, heading=ADDON_NAME, usemono=False):
        return self.dialog.textviewer(heading, msg, usemono)
        
    
    def yesnoDialog(self, message, heading=ADDON_NAME, nolabel='', yeslabel='', customlabel='', autoclose=0): 
        if customlabel:
            return self.dialog.yesnocustom(heading, message, customlabel, nolabel, yeslabel, autoclose)
        else: 
            return self.dialog.yesno(heading, message, nolabel, yeslabel, autoclose)


    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=4000, icon=COLOR_LOGO):
        self.log('notificationDialog: %s'%(message))
        ## - Builtin Icons:
        ## - xbmcgui.NOTIFICATION_INFO
        ## - xbmcgui.NOTIFICATION_WARNING
        ## - xbmcgui.NOTIFICATION_ERROR
        try: 
            self.dialog.notification(header, message, icon, time, sound=False)
        except Exception as e:
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True
             
             
    def selectDialog(self, list, header=ADDON_NAME, preselect=None, useDetails=True, autoclose=0, multi=True):
        if multi == True:
            if preselect is None: preselect = [-1]
            select = self.dialog.multiselect(header, list, autoclose, preselect, useDetails)
        else:
            if preselect is None: preselect = -1
            select = self.dialog.select(header, list, autoclose, preselect, useDetails)
        if select: return select
        return None
      
      
    def inputDialog(self, message, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
        ## - xbmcgui.INPUT_ALPHANUM (standard keyboard)
        ## - xbmcgui.INPUT_NUMERIC (format: #)
        ## - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
        ## - xbmcgui.INPUT_TIME (format: HH:MM)
        ## - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
        ## - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
        retval = self.dialog.input(message, default, key, opt, close)
        if retval: return retval
        return None
        
        
    def browseDialog(self, type=0, heading=ADDON_NAME, default='', shares='', mask='', options=None, useThumbs=True, treatAsFolder=False, prompt=True, multi=False, monitor=False):
        if prompt and not default:
            if options is None:
                options  = [{"label":"Video Playlists" , "label2":"Video Playlists"               , "default":"special://profile/playlists/video/" , "mask":'.xsp'             , "type":1, "multi":False},
                            {"label":"Music Playlists" , "label2":"Music Playlists"               , "default":"special://profile/playlists/music/" , "mask":'.xsp'             , "type":1, "multi":False},
                            {"label":"Video"           , "label2":"Video Sources"                 , "default":"library://video/"                   , "mask":globals.VIDEO_EXTS , "type":0, "multi":False},
                            {"label":"Music"           , "label2":"Music Sources"                 , "default":"library://music/"                   , "mask":globals.MUSIC_EXTS , "type":0, "multi":False},
                            {"label":"Pictures"        , "label2":"Picture Sources"               , "default":""                                   , "mask":globals.IMAGE_EXTS , "type":0, "multi":False},
                            {"label":"Files"           , "label2":"File Sources"                  , "default":""                                   , "mask":""                 , "type":0, "multi":False},
                            {"label":"Local"           , "label2":"Local Drives"                  , "default":""                                   , "mask":""                 , "type":0, "multi":False},
                            {"label":"Network"         , "label2":"Local Drives and Network Share", "default":""                                   , "mask":""                 , "type":0, "multi":False},
                            {"label":"Resources"       , "label2":"Resource Plugins"              , "default":"resource://"                        , "mask":""                 , "type":0, "multi":False}]
            
            listitems = [globals.buildMenuListItem(option['label'],option['label2'],iconImage=COLOR_LOGO) for option in options]
            select    = self.selectDialog(listitems, globals.LANGUAGE(30116), multi=False)
            if select is not None:
                # if options[select]['default'] == "resource://": #TODO PARSE RESOURCE JSON, LIST PATHS
                    # listitems = [globals.buildMenuListItem(option['label'],option['label2'],iconImage=COLOR_LOGO) for option in options]
                    # select    = self.selectDialog(listitems, globals.LANGUAGE(30116), multi=False)
                    # if select is not None:
                # else:    
                shares    = options[select]['label'].lower().replace("network","")
                mask      = options[select]['mask']
                type      = options[select]['type']
                multi     = options[select]['multi']
                default   = options[select]['default']
            
        self.log('browseDialog, type = %s, heading= %s, shares= %s, mask= %s, useThumbs= %s, treatAsFolder= %s, default= %s'%(type, heading, shares, mask, useThumbs, treatAsFolder, default))
        if monitor: globals.toggleCHKInfo(True)
        if multi == True:
            ## https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#ga856f475ecd92b1afa37357deabe4b9e4
            ## type integer - the type of browse dialog.
            ## 1	ShowAndGetFile
            ## 2	ShowAndGetImage
            retval = self.dialog.browseMultiple(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        else:
            ## https://codedocs.xyz/xbmc/xbmc/group__python___dialog.html#gafa1e339e5a98ae4ea4e3d3bb3e1d028c
            ## type integer - the type of browse dialog.
            ## 0	ShowAndGetDirectory
            ## 1	ShowAndGetFile
            ## 2	ShowAndGetImage
            ## 3	ShowAndGetWriteableDirectory
            retval = self.dialog.browseSingle(type, heading, shares, mask, useThumbs, treatAsFolder, default)
        if monitor: globals.toggleCHKInfo(False)
        if retval:
            if prompt and retval == default: return None
            return retval
        return None
        
        
    def notificationProgress(self, message, header=ADDON_NAME, funcs=[], wait=4):
        dia = self.progressBGDialog(message=message,header=header)
        if funcs: 
            workLST = (list(globals.chunks(funcs,wait)))
            if len(workLST) < wait:
                filLST = ([None] * int(wait-len(workLST)))
                workLST.extend(filLST)
        else: workLST = ([None] * time)
        for idx, work in enumerate(workLST):
            dia = self.progressBGDialog((((idx) * 100)//wait),control=dia,header=header)
            if work:
                for func in work:
                    if globals.MY_MONITOR.waitForAbort(0.001): break
                    dia = self.progressBGDialog((((idx) * 100)//wait),control=dia,header=header)
                    try: 
                        if   func[1]:func[0](*func[1])
                        elif func[2]:func[0](**func[2])
                        else: func[0]()
                        self.log('notificationProgress, executing %s(%s,%s)'%(func[0].__name__,func[1],func[2]))
                    except Exception as e: 
                        self.log('notificationProgress, Failed! %s'%(func[0].__name__,e))
            if globals.MY_MONITOR.waitForAbort(1): break
        return self.progressBGDialog(100,control=dia)


    def progressBGDialog(self, percent=0, control=None, message='', header=ADDON_NAME):
        if not isinstance(percent,int): percent = int(percent)
        if (self.onPlayback & self.isOverlay & self.isPlaying):
            if control is None: 
                return False
            else: 
                control.close()
                return True
        elif control is None and percent == 0:
            control = xbmcgui.DialogProgressBG()
            control.create(header, message)
        elif control:
            if percent == 100 or control.isFinished(): 
                control.close()
                return True
            else: control.update(percent, header, message)
        return control
        
class ListItems:
    def __init__(self):
        pass
