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
    def __init__(self, writer=None):
        self.log('__init__')
        if writer is None:
            from resources.lib.parser import Writer
            writer = Writer()
        self.writer = writer
        self.cache  = writer.cache
        
        if self.writer.vault.channelList is None: 
            self._reload()
        else: 
            self._withdraw()
            
                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def _clear(self):
        self.log('_clear')
        self.writer.vault.channelList = {}
        return self._deposit()
        

    def _reload(self):
        self.log('_reload')
        self.writer.vault.channelList = self.getTemplate()
        self.writer.vault.channelList.update(self.cleanSelf(self._load()))
        SETTINGS.setSetting('Select_Channels','[B]%s[/B] Channels'%(len(self.getChannels())))
        self.chkClient()
        return self._deposit()
        
        
    def _deposit(self):
        self.log('_deposit, channels = %s'%(len(self.writer.vault.channelList.get('channels',[]))))
        self.writer.vault.set_channelList(self.writer.vault.channelList)
        return True
        
    
    def _withdraw(self):
        self.writer.vault.channelList = self.writer.vault.get_channelList()
        self.log('_withdraw, channels = %s'%(len(self.writer.vault.channelList)))
        return True
        

    def _load(self, file=getUserFilePath(CHANNELFLE)):
        self.log('_load, file = %s'%(file))
        fle  = FileAccess.open(file, 'r')
        data = (loadJSON(fle.read()) or {})
        fle.close()
        return data
        
            
    def loadChannels(self, file=getUserFilePath(CHANNELFLE)):
        self.log('loadChannels, file = %s'%(file))
        return self.cleanSelf(self._load(file)).get('channels',[])
        
       
    def saveChannels(self):
        with fileLocker(self.writer.globalFileLock):
            filePath = getUserFilePath(CHANNELFLE)
            fle = FileAccess.open(filePath, 'w')
            self.log('saveChannels, saving %s channels to %s'%(len(self.getChannels()),filePath))
            fle.write(dumpJSON(self.cleanSelf(self.writer.vault.channelList), idnt=4, sortkey=False))
            fle.close()
        return self._reload()


    @cacheit(checksum='%s.%s'%(ADDON_VERSION,getIP()),json_data=True)
    def getTemplate(self):
        self.log('getTemplate')
        channelList = self._load(CHANNELFLE_DEFAULT)
        channelList['uuid'] = self.getUUID(channelList)
        return channelList


    def getCitem(self):#channel schema
        citem = self.getTemplate().get('channels',[{}])[0].copy()
        citem['rules'] = []
        return citem
        
  
    def cleanSelf(self, channelList):
        channels = channelList.get('channels',[])
        channelList['channels'] = self.sortChannels([citem for citem in channels if citem['number'] > 0])
        self.log('cleanSelf, before = %s, after = %s'%(len(channels),len(channelList.get('channels',[]))))
        return channelList
  
  
    @staticmethod
    def sortChannels(channels):
        return sorted(channels, key=lambda k: k['number'])

  
    def getMYUUID(self):
        uuid = SETTINGS.getCacheSetting('MY_UUID')
        if not uuid: 
            uuid = genUUID(seed=getIP())
            SETTINGS.setCacheSetting('MY_UUID',uuid)
        return uuid


    def getUUID(self, channelList=None):
        if channelList is None: 
            channelList = self.writer.vault.channelList
        uuid = channelList.get('uuid','')
        if not uuid: 
            uuid = self.getMYUUID()
            channelList['uuid'] = uuid
            self.writer.vault.channelList = channelList
        return uuid
            
            
    def chkClient(self):
        isClient = (PROPERTIES.getPropertyBool('isClient') or SETTINGS.getSettingBool('Enable_Client'))
        if not isClient:
            isClient = self.getUUID() != self.getMYUUID()
            PROPERTIES.setPropertyBool('isClient',isClient)
            SETTINGS.setSettingBool('Enable_Client',isClient)
        self.log('chkClient, isClient = %s'%(isClient))
        return isClient


    def getChannels(self):
        channels = self.sortChannels(self.writer.vault.channelList.get('channels',[]))
        self.log('getChannels, channels = %s'%(len(channels)))
        return channels.copy()


    def getUserChannels(self):
        return self.sortChannels(list(filter(lambda citem:citem.get('number') <= CHANNEL_LIMIT, self.getChannels())))


    def getPredefinedChannels(self):
        return self.sortChannels(list(filter(lambda citem:citem.get('number') > CHANNEL_LIMIT, self.getChannels())))


    def getPredefinedChannelsByType(self, type, channels=None):
        if channels is None: channels = self.getPredefinedChannels()
        return self.sortChannels(filter(lambda c:c.get('type') == type, channels))


    def getImports(self):
        self.log('getImports')
        return self.writer.vault.channelList.get('imports',[])


    def setImports(self, imports): #save called by config.
        self.log('setImports, imports = %s'%(imports))
        self.writer.vault.channelList['imports'] = imports
        return True


    def addChannel(self, citem):
        self.log('addChannel, id = %s'%(citem['id']))
        idx, channel = self.writer.findChannel(citem, self.writer.vault.channelList.get('channels',[]))
        if idx is not None:
            for key in ['id','rules','number','favorite']: 
                citem[key] = channel[key] # existing id found, reuse channel meta.
            citem['group'] = list(set(citem.get('group',[])))
            self.log('addChannel, updating channel %s, id %s'%(citem["number"],citem["id"]))
            self.writer.vault.channelList['channels'][idx] = citem #can't .update() must replace.
        else:
            citem['group'] = list(set(citem.get('group',[])))
            self.log('addChannel, adding channel %s, id %s'%(citem["number"],citem["id"]))
            self.writer.vault.channelList.setdefault('channels',[]).append(citem)
            self.log('addChannel, total channels = %s'%(len(self.writer.vault.channelList.get('channels',[]))))
        return True
        
        
    def removeChannel(self, citem):
        self.log('removeChannel, id = %s'%(citem['id']))
        idx, channel = self.writer.findChannel(citem, self.writer.vault.channelList.get('channels',[]))
        if idx is not None: self.writer.vault.channelList['channels'].pop(idx)
        return True

    
    def deleteChannels(self):
        self.log('deleteChannels')
        if FileAccess.delete(getUserFilePath(CHANNELFLE)):
            return self.dialog.notificationDialog(LANGUAGE(30016)%('Channels'))
        return False


    def clearChannels(self):
        self.log('clearChannels')
        return self._clear()


    def getRitem(self):
        self.log('getRitem') #rule schema
        return self.getTemplate().get('channels',[{}])[0].get('rules',[])[0].copy()