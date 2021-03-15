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
# https://github.com/kodi-community-addons/script.module.simplecache/blob/master/README.md
# -*- coding: utf-8 -*-
 
import resources.lib.globals as globals
  
from kodi_six               import xbmc, xbmcaddon
from simplecache            import SimpleCache
from datetime               import timedelta
from resources.lib.kodi     import Settings  

def stringify(serial):
    return globals.dumpJSON(serial)

def serialize(string):
    return globals.loadJSON(string)

def getSettingInt(key):
    return Settings(xbmcaddon.Addon('plugin.video.pseudotv.live')).getSettingInt(key)

def cacheit(life=timedelta(days=getSettingInt('Max_Days'))):
    def decorator(func):
        def decorated(*args, **kwargs):
            method_class = args[0]
            method_class_name = method_class.__class__.__name__
            cache_str = "%s.%s" % (method_class_name, func.__name__)
            for item in args[1:]: cache_str += u".%s"%item
            results = method_class.cache.get(cache_str.lower())
            if results: return results
            return method_class.cache.set(cache_str.lower(), func(*args, **kwargs), expiration=life)
        return decorated
    return decorator


class Cache:
    def __init__(self, memory=True):
        self.log('Cache: __init__')
        self.cache = SimpleCache()
        self.cache.enable_mem_cache = memory
            
            
    def log(self, msg, level=xbmc.LOGDEBUG):
        return globals.log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def set(self, name, data, checksum="", expiration=timedelta(minutes=15)):
        if not name.startswith(globals.ADDON_ID): name = '%s.%s'%(globals.ADDON_ID,name)#create unique id
        self.log('set, name = %s'%(name))
        if not data is None: self.cache.set(name.lower(), stringify(data), stringify(checksum), expiration)
        return data
        
    
    def get(self, name, checksum=""):
        if not name.startswith(globals.ADDON_ID): name = '%s.%s'%(globals.ADDON_ID,name)#create unique id
        results = serialize(self.cache.get(name.lower(),stringify(checksum)))
        self.log('get, name = %s'%(name))
        return results