#   Copyright (C) 2015 Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import subprocess, os, sys, re, random, threading
import datetime, time, shutil

from urllib import unquote
from xml.dom.minidom import parse, parseString
from resources.lib.utils import *
from resources.lib.Globals import *

try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
    
class SkinManager(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log("__init__")
        if getProperty("PseudoTVRunning") != "True":
            xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)      
            self.clearProps() 
            self.local = False
            self.skinPOSMAX = 0
            self.screenshotPOS = 1
            self.selSkin = Skin_Select
            self.skinLOC = xbmc.translatePath(PTVL_SKIN_LOC)
            self.skinNames = ['Default']
            self.fillSkins()
            self.skinPOS = self.findSkin()
            self.setSkin(self.skinPOS)
            self.doModal()
            self.log("__init__ return")
    
    
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('SkinManager: ' + msg, level)

        
    def findSkin(self):
        self.log("findSkin")
        for i in range(len(self.skinNames)):
            if Skin_Select.lower() == self.skinNames[i].lower():
                return i
        
        
    def fillSkins(self):
        self.log("fillSkins")  
        github_skinList = fillGithubItems('https://github.com/PseudoTV/PseudoTV_Skins')
        for i in range(len(github_skinList)):
            ssList = fillGithubItems('https://github.com/PseudoTV/PseudoTV_Skins/tree/master/%s' % github_skinList[i])
            for n in range(len(ssList)):
                if (ssList[n].lower()).startswith('screenshot'):
                    self.skinNames.append(github_skinList[i])
                    break 
        self.skinPOSMAX = len(self.skinNames) - 1
        self.log("fillSkins, self.skinNames = " + str(self.skinNames)) 

        
    def setSkin(self, skinPOS):
        self.clearProps() 
        self.local = False
        self.screenshotPOS = 1
        self.log("setSkin, Skin = " + self.skinNames[skinPOS])
        BaseURL = 'https://raw.githubusercontent.com/PseudoTV/PseudoTV_Skins/master/'+self.skinNames[skinPOS]
        
        if xbmcvfs.exists(os.path.join(self.skinLOC,self.skinNames[skinPOS],'skin.xml')):
            self.BasePath = os.path.join(self.skinLOC,self.skinNames[skinPOS])
            self.local = True
        else:
            self.BasePath = BaseURL
        self.log("self.BasePath = " + self.BasePath)
        
        try:
            fle = self.BasePath + '/skin.xml'
            if self.BasePath.startswith('http'):
                xml = open_url(fle)
            else:
                xml = open(fle, "r")
            dom = parse(xml)
            name = dom.getElementsByTagName('name')
            version = dom.getElementsByTagName('version')
            skinname = dom.getElementsByTagName('skinname') 
            version = version[0].childNodes[0].nodeValue   
            sknname = skinname[0].childNodes[0].nodeValue    
            xml.close()
            
            if version == PTVL_SKINVER:
                if self.selSkin.lower() == sknname.lower():
                    sknname = ' [ ' + sknname + ' ]'
            else:
                sknname = sknname + ' [COLOR=red][OUTDATED][/COLOR]'
            setProperty('PTVL.SKINNAME',sknname)
            setProperty('PTVL.SKINVERSION',version)
            setProperty('PTVL.SKINAUTHOR','Designed by: ' + name[0].childNodes[0].nodeValue)
            setProperty('PTVL.SKINSHOT',self.BasePath + '/screenshot0%s.png' %str(self.screenshotPOS))
            setProperty('PTVL.SKINSHOT_FALLBACK',self.BasePath + '/screenshot01.png')
        except:
            pass
        
            
    def closeManager(self):
        self.log("closeManager") 
        REAL_SETTINGS.setSetting("SkinSelector",self.selSkin)
        # REAL_SETTINGS.openSettings()
        self.close()
                   
 
    def onAction(self, act):
        action = act.getId()
        if action in ACTION_SELECT_ITEM:
            self.SelectAction()
        elif action in ACTION_MOVE_LEFT:   
            self.log("onAction, ACTION_MOVE_LEFT")
            setProperty('PTVL.SSLEFTD','FF0297eb')
            setProperty('PTVL.SSRIGHTD','FFFFFFFF')
            self.onLeft()    
        elif action in ACTION_MOVE_RIGHT:
            self.log("onAction, ACTION_MOVE_RIGHT")
            setProperty('PTVL.SSRIGHTD','FF0297eb')
            setProperty('PTVL.SSLEFTD','FFFFFFFF')
            self.onRight()
        elif action in ACTION_PREVIOUS_MENU:
            self.closeManager()
        elif action in ACTION_MOVE_UP or action in ACTION_PAGEUP:
            self.log("onAction, ACTION_MOVE_UP")
            setProperty('PTVL.SSUPD','FF0297eb')
            setProperty('PTVL.SSDOWND','FFFFFFFF')
            self.rotateImage('UP') 
        elif action in ACTION_MOVE_DOWN or action in ACTION_PAGEDOWN:
            self.log("onAction, ACTION_MOVE_DOWN")
            setProperty('PTVL.SSDOWND','FF0297eb')
            setProperty('PTVL.SSUPD','FFFFFFFF')
            self.rotateImage('DOWN') # Delete button
        elif act.getButtonCode() == 61575 or action == ACTION_DELETE_ITEM:
            self.deleteSkin(self.skinNames[self.skinPOS])
                 

    def deleteSkin(self, selSkin):
        if selSkin == 'Default':
            return
        try:
            if yesnoDialog('%s "%s" Skin' %('Delete', selSkin)) == True:
                shutil.rmtree(os.path.join(self.skinLOC,selSkin))
        except:
            pass
        self.selSkin = self.skinNames[0]
        REAL_SETTINGS.setSetting("SkinSelector",self.selSkin)
        self.closeManager()
    
    
    def downloadSkin(self, selSkin):
        self.log("downloadSkin")
        url = ('https://github.com/PseudoTV/PseudoTV_Skins/raw/master/%s/%s.zip' %(selSkin,selSkin))  
        dl = os.path.join(self.skinLOC,'%s.zip'%selSkin)
        try:
            download(url, dl, '')
            all(dl, os.path.join(self.skinLOC,''),True)
            try:
                xbmcvfs.delete(dl)
            except:
                pass
            return True
        except:
            return False
            
      
    def SelectAction(self):
        self.log("SelectAction")
        if self.skinNames[self.skinPOS].lower() != self.selSkin.lower():
            if ['[COLOR=red][OUTDATED][/COLOR]'] in getProperty('PTVL.SKINNAME'):
                return
                
            if self.local == True:
                msg = 'Apply'
            else:
                msg = 'Download & Apply'
            if yesnoDialog('%s "%s" Skin' %(msg, self.skinNames[self.skinPOS])) == True:
                if self.local == False:
                    if self.downloadSkin(self.skinNames[self.skinPOS]) == False:
                        return
                self.selSkin = self.skinNames[self.skinPOS]
                REAL_SETTINGS.setSetting("SkinSelector",self.selSkin)
                self.closeManager()
        
        
    def onLeft(self):
        self.log("onLeft") 
        if self.skinPOS == 0:
            self.skinPOS = self.skinPOSMAX
        else:
            self.skinPOS -= 1
        self.log("self.skinPOS = " + str(self.skinPOS)) 
        self.setSkin(self.skinPOS)

        
    def onRight(self):
        self.log("onRight")
        if self.skinPOS == self.skinPOSMAX:
            self.skinPOS = 0
        else:
            self.skinPOS += 1
        self.log("self.skinPOS = " + str(self.skinPOS)) 
        self.setSkin(self.skinPOS)
            
      
    def clearProps(self):
        self.log("clearProps")
        clearProperty("PTVL.SKINNAME")
        clearProperty("PTVL.SKINAUTHOR")
        clearProperty("PTVL.SKINVERSION")
        clearProperty("PTVL.SKINSHOT")
        clearProperty("PTVL.SKINSHOT_FALLBACK")
    

    def rotateImage(self, dir):  
        self.log('rotateImage')
        if dir == 'UP' and self.screenshotPOS == 4:
            self.screenshotPOS = 1
        elif dir == 'DOWN' and self.screenshotPOS == 1:
            self.screenshotPOS = 4
        elif dir == 'UP':
            self.screenshotPOS += 1
        elif dir == 'DOWN':
            self.screenshotPOS -= 1
        setProperty('PTVL.SKINSHOT',self.BasePath + '/screenshot0%s.png' %str(self.screenshotPOS))
            
            
# SkinSelector setsetting to skin name
__cwd__ = REAL_SETTINGS.getAddonInfo('path')

mydialog = SkinManager("script.pseudotv.live.SkinManager.xml", __cwd__, "Default")
del mydialog