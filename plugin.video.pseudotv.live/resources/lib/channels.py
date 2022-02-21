#   Copyright (C) 2022 Lunatixz
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
        if writer is None:
            from resources.lib.parser import Writer
            writer = Writer()
            
        self.writer = writer
        self.cache  = writer.cache
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def _withdraw(self):
        channelList = self.writer.vault.get_channelList()
        self.log('_withdraw, channels = %s'%(len(channelList)))
        return channelList
        
        
    def _deposit(self):
        self.log('_deposit, channels = %s'%(len(self.writer.vault.channelList.get('channels',[]))))
        self.writer.vault.set_channelList(self.writer.vault.channelList)
        SETTINGS.setSetting('Select_Channels','[B]%s[/B] Channels'%(len(self.getChannels())))
        return True
        
        
    def _clear(self):
        self.log('_clear')
        self.writer.vault.channelList = None
        return self._deposit()
       
       
    def _save(self):
        with fileLocker(self.writer.globalFileLock):
            filePath = CHANNELFLEPATH
            fle = FileAccess.open(filePath, 'w')
            self.log('_save, saving %s channels to %s'%(len(self.getChannels()),filePath))
            fle.write(dumpJSON(self.cleanSelf(self.writer.vault.channelList), idnt=4, sortkey=False))
            fle.close()
        return self._deposit()

          
    def cleanSelf(self, channelList):
        tempkeys = self.getCitem().keys()
        channels = channelList.get('channels',[])
        for idx, citem in enumerate(channels):
            citem = dict([(key,value) for key, value in citem.items() if key in tempkeys]) #remove leftover m3u keys, only save citem elements #todo split channels.json and m3u elements the their own dataobject?
            citem['group'] = list(set(citem['group'])) #clean duplicates, necessary?
            channels[idx]  = citem
        channelList['channels'] = self.sortChannels([citem for citem in channels if citem['number'] > 0])
        self.log('cleanSelf, before = %s, after = %s'%(len(channels),len(channelList.get('channels',[]))))
        return channelList
        
        
    @staticmethod
    def sortChannels(channels):
        return sorted(channels, key=lambda k: k['number'])


    def getChannels(self):
        channels = self.cleanSelf(self.writer.vault.channelList).get('channels',[])
        self.log('getChannels, channels = %s'%(len(channels)))
        return channels.copy()


    def getUserChannels(self):
        return list(filter(lambda citem:citem.get('number') <= CHANNEL_LIMIT, self.getChannels()))


    def getPredefinedChannels(self):
        return list(filter(lambda citem:citem.get('number') > CHANNEL_LIMIT, self.getChannels()))


    def getPredefinedChannelsByType(self, type, channels=None):
        if channels is None: channels = self.getPredefinedChannels()
        return list(filter(lambda c:c.get('type') == type, channels))


    @cacheit(checksum=getInstanceID(),json_data=True)
    def getTemplate(self):
        fle = FileAccess.open(CHANNELFLE_DEFAULT, 'r')
        channelList = loadJSON(fle.read())
        fle.close()
        return channelList


    def getCitem(self):#channel schema
        return self.getTemplate().get('channels',[])[0].copy()
        

    def getRitem(self): #rule schema
        return {"id": 0, "name": "", "description": "", "options": {}}


    def getImports(self):
        self.log('getImports')
        return self.writer.vault.channelList.get('imports',[]).copy()


    def setImports(self, imports): #save called by config.
        self.log('setImports, imports = %s'%(imports))
        self.writer.vault.channelList['imports'] = imports
        return True


    def addChannel(self, citem):
        self.log('addChannel, id = %s'%(citem['id']))
        idx, channel = self.writer.findChannel(citem, self.getChannels())
        if idx is not None:
            for key in ['id','rules','number','favorite']: 
                if channel.get(key):
                    citem[key] = channel[key] # existing id found, reuse channel meta.
            citem['group'] = list(set(citem.get('group',[])))
            self.log('addChannel, updating channel %s, id %s'%(citem["number"],citem["id"]))
            self.writer.vault.channelList['channels'][idx] = citem #can't .update() must replace.
        else:
            citem['group'] = list(set(citem.get('group',[])))
            self.log('addChannel, adding channel %s, id %s'%(citem["number"],citem["id"]))
            self.writer.vault.channelList.setdefault('channels',[]).append(citem)
            self.log('addChannel, total channels = %s'%(len(self.getChannels())))
        return True
        
        
    def removeChannel(self, citem):
        self.log('removeChannel, id = %s'%(citem['id']))
        idx, channel = self.writer.findChannel(citem, self.getChannels())
        if idx is not None: self.writer.vault.channelList['channels'].pop(idx)
        return True

    
    def deleteChannels(self):
        self.log('deleteChannels')
        if FileAccess.delete(CHANNELFLEPATH):
            self._clear()
            return self.dialog.notificationDialog(LANGUAGE(30016)%('Channels'))
        return False

