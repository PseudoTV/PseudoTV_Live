#   Copyright (C) 2021 Lunatixz
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
# https://github.com/kodi-pvr/pvr.iptvsimple/blob/Matrix/README.md#m3u-format-elements
# https://raw.githubusercontent.com/XMLTV/xmltv/master/xmltv.dtd
# -*- coding: utf-8 -*-

from resources.lib.globals     import *

class Channels:
    isClient = False
    
    def __init__(self, writer=None):
        self.log('__init__')
        if writer:
            self.writer = writer
        else:
            from resources.lib.writer import Writer
            self.writer = Writer()
            
        self.vault      = self.writer.vault
        self.cache      = self.writer.cache
        self.monitor    = self.writer.monitor
        self.filelock   = self.writer.GlobalFileLock
        
        if not self.vault.channelList: 
            self.reload()
        
                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def clear(self):
        self.log('clear')
        self.vault.channelList = {}
        return self.deposit()
        

    def reload(self):
        self.log('reload')
        self.vault.channelList = self.cleanSelf(self.load())
        self.isClient = self.chkClient()
        return self.deposit()
        
        
    def deposit(self):
        self.log('deposit')
        self.vault.set_channelList(self.vault.channelList)
        return True
        
    
    def withdraw(self):
        self.log('withdraw')
        return self.vault.get_channelList()
     

    def load(self, file=getUserFilePath(CHANNELFLE)):
        self.log('load file = %s'%(file))
        if not FileAccess.exists(file): 
            file = CHANNELFLE_DEFAULT
        with fileLocker(self.filelock):
            fle  = FileAccess.open(file, 'r')
            data = (loadJSON(fle.read()) or {})
            fle.close()
            return data
        
        
    def save(self):
        with fileLocker(self.filelock):
            filePath = getUserFilePath(CHANNELFLE)
            fle = FileAccess.open(filePath, 'w')
            self.log('save, saving to %s'%(filePath))
            fle.write(dumpJSON(self.cleanSelf(self.vault.channelList), idnt=4, sortkey=False))
            fle.close()
        return self.reload()


    @cacheit(checksum=ADDON_VERSION,json_data=True)
    def getTemplate(self):
        self.log('getTemplate')
        channelList = (self.load(CHANNELFLE_DEFAULT) or {})
        channelList['uuid'] = self.getUUID(channelList)
        return channelList


    def getCitem(self):
        self.log('getCitem') #channel schema
        citem = self.getTemplate().get('channels',[])[0].copy()
        citem['rules'] = []
        return citem
        
  
    def cleanSelf(self, channelList):
        channels = channelList.get('channels',[])
        channelList['channels'] = self.sortChannels([citem for citem in channels if citem['number'] > 0])
        self.log('cleanSelf, before = %s, after = %s'%(len(channels),len(channelList['channels'])))
        return channelList
  
  
    @staticmethod
    def sortChannels(channels):
        return sorted(channels, key=lambda k: k['number'])

  
    def getMYUUID(self):
        uuid = SETTINGS.getSetting('MY_UUID')
        if not uuid: 
            uuid = genUUID(seed=getIP())
            SETTINGS.setSetting('MY_UUID',uuid)
        return uuid


    def getUUID(self, channelList=None):
        if channelList is None: 
            channelList = self.vault.channelList
        uuid = channelList.get('uuid','')
        if not uuid: 
            uuid = self.getMYUUID()
            channelList['uuid'] = uuid
            self.vault.channelList = channelList
        return uuid
            
            
    def chkClient(self):
        isClient = (SETTINGS.getSettingBool('Enable_Client') | PROPERTIES.getPropertyBool('Enable_Client'))
        if not isClient:
            isClient = self.getUUID() != self.getMYUUID()
            if isClient: PROPERTIES.setPropertyBool('Enable_Client',True)
            else:        PROPERTIES.setPropertyBool('Enable_Client',False)
        self.log('chkClient, isClient = %s'%(isClient))
        return isClient


    def getChannels(self):
        self.log('getChannels')
        return self.sortChannels(self.withdraw().get('channels',[]))


    def getPredefinedChannels(self):
        self.log('getPredefinedChannels')
        return self.sortChannels(list(filter(lambda citem:citem.get('number') > CHANNEL_LIMIT, self.withdraw().get('channels',[]))))


    def getPredefinedChannelsByType(self, type):
        self.log('getPredefinedChannelsByType')
        return self.sortChannels(filter(lambda c:c.get('type') == type, self.getPredefinedChannels()))


    def getPage(self, id):
        idx, citem = self.findChannel({'id':id}, self.getChannels())
        page = citem.get('page',{"end":0,"start":0,"total":0})
        self.log('getPage, id = %s, page = %s'%(id, page))
        return page


    def setPage(self, id, page={}):
        self.log('setPage, id = %s, page = %s'%(id, page))
        channels = self.getChannels()
        idx, citem = self.findChannel({'id':id}, channels)
        if idx is None: return False
        channels[idx]['page'] = page
        self.vault.channelList['channels'] = channels
        return True


    def getImports(self):
        self.log('getImports')
        return self.vault.channelList.get('imports',[])


    def setImports(self, imports):
        self.log('setImports, imports = %s'%(imports))
        self.vault.channelList['imports'] = imports
        return True
        

    def add(self, citem):
        self.log('add, id = %s'%(citem['id']))
        idx, channel = self.findChannel(citem, channels = self.getChannels())
        if idx is not None:
            for key in ['rules','number','favorite','page']: citem[key] = channel[key] # existing id found, reuse channel meta.
            citem['group'] = list(set(citem.get('group',[])))
            self.log('Updating channel %s, id %s'%(citem["number"],citem["id"]))
            self.vault.channelList['channels'][idx] = citem #can't .update() must replace.
        else:
            citem['group'] = list(set(citem.get('group',[])))
            self.log('Adding channel %s, id %s'%(citem["number"],citem["id"]))
            self.vault.channelList['channels'].append(citem)
        self.log('add, total channels = %s'%(len(self.vault.channelList['channels'])))
        return True
        
        
    def remove(self, citem):
        self.log('removing id = %s'%(citem['id']))
        idx, channel = self.findChannel(citem, self.getChannels())
        if idx is not None: self.vault.channelList['channels'].pop(idx)
        return True

        
    def findChannel(self, citem, channels):
        match = None, {}
        for idx, channel in enumerate(channels):
            if citem.get("id") == channel.get("id"):
                self.log('findChannel, item = %s, found = %s'%(citem['id'],channel['id']))
                return idx, channel
            elif ((citem.get("name") == channel["name"]) and (citem["type"] == channel["type"])):
                self.log('findChannel, possible match found = %s'%(channel['id']))
                match = idx, channel
        return match
        
       
    def getRitem(self):
        self.log('getRitem') #rule schema
        return self.getTemplate().get('channels',[{}])[0].get('rules',[])[0].copy()