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
# https://stackoverflow.com/questions/747793/python-borg-pattern-problem/747888#747888
# -*- coding: utf-8 -*-

from resources.lib.globals     import *
from types                     import SimpleNamespace

class Vault:
    #todo convert json to dataclass create class array to handle types. https://pypi.org/project/dataclasses-json/
    #use dataclass to enforce key types. int, bool, dict, etc...
    _vault = {}
    
    def __init__(self):
        self.__dict__ = self._vault

            
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _load(self, file):
        self.log('_load file = %s'%(file))
        fle  = FileAccess.open(file, 'r')
        data = (loadJSON(fle.read()) or {})
        fle.close()
        return data
        
        
    def set_m3uList(self, m3uList):
        self.log('set_m3uList, m3uList: channels = %s'%(len(m3uList.get('channels',[]))))
        self._m3uList = m3uList


    def get_m3uList(self):
        return getattr(self, '_m3uList', None)


    def set_xmltvList(self, xmltvList):
        self.log('set_xmltvList, xmltvList: channels = %s'%(len(xmltvList.get('channels',[]))))
        self._xmltvList = xmltvList


    def get_xmltvList(self):
        return getattr(self, '_xmltvList', None)


    def set_channelList(self, channelList):
        self.log('set_channelList, channelList: channels = %s'%(len(channelList.get('channels',[]))))
        self._channelList = channelList


    def get_channelList(self):
        return getattr(self, '_channelList', self.load_channelList())
        
        
    def load_channelList(self):
        if getattr(self,'_channelList',None) is None:
            channelList = self._load(CHANNELFLE_DEFAULT)
            channelList.update(self._load(CHANNELFLEPATH))
            channelList['uuid'] = getUUID(channelList)
            self.set_channelList(channelList)
            return channelList


    def set_libraryItems(self, libraryItems):
        self.log('set_libraryItems, libraryItems')
        self._libraryItems = libraryItems


    def get_libraryItems(self):
        return getattr(self,'_libraryItems', self.load_libraryItems())
        
        
    def load_libraryItems(self):
        if getattr(self,'_libraryItems',None) is None:
            libraryItems = self._load(LIBRARYFLE_DEFAULT)
            libraryItems.update(self._load(LIBRARYFLEPATH))
            self.set_libraryItems(libraryItems)
            return libraryItems
        

    m3uList      = property(get_m3uList     , set_m3uList)
    xmltvList    = property(get_xmltvList   , set_xmltvList)
    channelList  = property(get_channelList , set_channelList)
    libraryItems = property(get_libraryItems, set_libraryItems)

class StationItem():
    #M3U Entry
    def __init__(self): ...
        
class ProgramItem():
    #XMLTV Entry
    def __init__(self): ...
    
class ChannelItem():
    #Channel Entry
    def __init__(self): ...
     
class LibraryItem():
    #Library Entry
    def __init__(self): ...

# todo json to class
# StationItem = json.loads(data, object_hook=lambda d: SimpleNamespace(**d))
# data = '{"name": "John Smith", "hometown": {"name": "New York", "id": 123}}'
# print(x.name, x.hometown.name, x.hometown.id)