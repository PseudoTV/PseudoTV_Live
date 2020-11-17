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

from resources.lib.globals     import *
from resources.lib.jsonrpc     import JSONRPC

REG_KEY = 'PseudoTV_Recommended.%s'

class Recommended:
    def __init__(self, cache=None):
        self.log('__init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.jsonRPC           = JSONRPC(self.cache)
        self.recommendEnabled  = getSettingBool('Enable_Recommended')
        self.recommendedList   = self.getRecommendedList()
        self.importPrompt_busy = False
        #whitelist - prompt shown, added to import list and/or manager dropdown.
        #blacklist - plugin ignored for the life of the list.
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def reset(self):
        self.log('reset')
        self.__init__()
        return True


    def clearRecommendedList(self):
        self.log('clearRecommendedList')
        self.recommendedList = {}
        return self.setRecommendedList()


    def getRecommendedList(self):
        self.log('getRecommendedList')
        return loadJSON(getSetting('Recommended_List'))


    def setRecommendedList(self):
        self.log('setRecommendedList')
        return setSetting('Recommended_List',dumpJSON(self.recommendedList))


    def getWhiteList(self):
        return self.recommendedList.get('whitelist',[])
        
        
    def getBlackList(self):
        return self.recommendedList.get('blacklist',[])
    
    
    def addWhiteList(self, addonid):
        self.log('addWhiteList')
        whitelist = self.getWhiteList()
        whitelist.append(addonid)
        self.recommendedList['whitelist'] = whitelist
        return self.setRecommendedList()
        
        
    def addBlackList(self, addonid):
        self.log('addBlackList')
        blacklist = self.getBlackList()
        blacklist.append(addonid)
        self.recommendedList['blacklist'] = blacklist
        return self.setRecommendedList()
    
    
    def buildData(self, addon):
        addonid = addon.get('addonid','')
        blackList = self.getBlackList()
        if not addonid in blackList:
            data = xbmcgui.Window(10000).getProperty(REG_KEY%(addonid))
            if data: 
                self.log('buildData, found addonid = %s, payload = %s'%(addonid,data))
                return {'id':addonid,'data':loadJSON(data),'item':getPluginMeta(addonid)}
            
            
    def getData(self):
        self.log('getData')
        return list(PoolHelper().poolList(self.buildData, self.jsonRPC.getAddons()))
        
        
    def getDataType(self, type='iptv'):
        self.log('getDataType, type = %s'%(type))
        whiteList = self.getWhiteList()
        recommendedItems = self.getData()
        return [item for item in recommendedItems for addonid in whiteList if ((item.get('id','') == addonid) and (item['data'].get('type','').lower() == type.lower()))]
        
        
    def fillRecommended(self):
        self.log('fillRecommended')
        whiteList = self.getWhiteList()
        recommendedItems = self.getData()
        return [item for item in recommendedItems for addonid in whiteList if ((item.get('id','') == addonid) and (item['data'].get('type','').lower() != 'iptv'))]
        
    
    def importPrompt(self):
        self.log('importPrompt')
        if self.importPrompt_busy: return
        self.importPrompt_busy = True
        ignoreList = self.getWhiteList()
        ignoreList.extend(self.getBlackList())
        recommendedItems = self.getData()
        for addon in recommendedItems:
            if not addon['id'] in ignoreList:
                if not yesnoDialog('%s'%(LANGUAGE(30147)%(ADDON_NAME,addon['item'].get('name','')))):
                    self.addBlackList(addon['id'])
                else:
                    self.addWhiteList(addon['id'])
        self.importPrompt_busy = False
        return True