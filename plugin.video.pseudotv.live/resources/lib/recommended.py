#   Copyright (C) 2020 Lunatixz
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

# -*- coding: utf-8 -*-

from resources.lib.globals    import *
from resources.lib.parser     import JSONRPC

REG_KEY = 'PseudoTV_Recommended.%s'

class Recommended:
    def __init__(self):
        self.log('__init__')
        self.jsonrpc          = JSONRPC()
        self.recommendedList  = self.getRecommendedList()
        self.recommendedItems = self.getData()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def reset(self):
        self.log('reset')
        self.__init__()
        return True


    def getRecommendedList(self):
        return loadJSON(getSetting('Recommended_List'))


    def setRecommendedList(self):
        return setSetting('Recommended_List',dumpJSON(self.recommendedList))


    def getWhiteList(self):
        return self.recommendedList.get('whitelist',[])
        
        
    def getBlackList(self):
        return self.recommendedList.get('blacklist',[])
    
    
    def addWhiteList(self, addonid):
        whitelist = self.getWhiteList()
        whitelist.append(addonid)
        self.setRecommendedList()
        return True
        
        
    def addBlackList(self, addonid):
        blacklist = self.getBlackList()
        blacklist.append(addonid)
        self.setRecommendedList()
        return True
    
    
    def getAddons(self):
        response = self.jsonrpc.cacheJSON('{"jsonrpc":"2.0","method":"Addons.GetAddons","params":{"type":"xbmc.addon.video","enabled":true},"id":1}')
        return response.get('result',{}).get('addons',[])
        
        
    def buildData(self, addon):
        addonid = addon.get('addonid','')
        blackList = self.getBlackList()
        if not addonid in blackList:
            data = xbmcgui.Window(10000).getProperty(REG_KEY%(addonid))
            if data: 
                self.log('buildData, found addonid = %s, data = %s'%(addonid,data))
                return {'id':addonid,'data':loadJSON(data),'meta':getPluginMeta(addonid)}
            
            
    def getData(self):
        self.log('getData')
        return list(PoolHelper().poolList(self.buildData, self.getAddons()))
        
        
    def getDataType(self, type='iptv'):
        self.log('getDataType, type = %s'%(type))
        return [item for item in self.recommendedItems if item.get('type','').lower() == type.lower()]
        
    
    def importPrompt(self):
        self.log('importPrompt')
        whiteList = self.getWhiteList()
        for addon in self.recommendedItems:
            if not addon['id'] in whiteList:
                if not yesnoDialog('%s'%(LANGUAGE(30147)%(ADDON_NAME,addon['meta'].get('name','')))):
                    return self.addBlackList(addon['id'])
                else:
                    print(addon)
        return True