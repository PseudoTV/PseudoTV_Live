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
 
import os, json, traceback

from kodi_six               import xbmc, xbmcaddon
from datetime               import timedelta

try:
    from simplecache             import SimpleCache
except:
    from simplecache.simplecache import SimpleCache #pycharm stub

ADDON_ID      = 'plugin.video.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')

def stringify(serial):
    try:    return json.dumps(serial)
    except: return serial

def serialize(string):
    try:    return json.loads(string)
    except: return string

def log(msg, level=xbmc.LOGDEBUG):
    if not REAL_SETTINGS.getSetting('Enable_Debugging') == "true" and level != xbmc.LOGERROR: return
    if not isinstance(msg,str): msg = str(msg)
    if level == xbmc.LOGERROR: msg = '%s\n%s'%((msg),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)

def cacheit(expiration=timedelta(days=REAL_SETTINGS.getSettingInt('Max_Days')), checksum=ADDON_VERSION, json_data=False):
    def decorator(func):
        def decorated(*args, **kwargs):
            method_class = args[0]
            cacheName    = "%s.%s"%(method_class.__class__.__name__, func.__name__)
            for item in args[1:]: cacheName += u".%s"%item
            results = method_class.cache.get(cacheName.lower(), checksum, json_data)
            if results: return results
            return method_class.cache.set(cacheName.lower(), func(*args, **kwargs), checksum, expiration, json_data)
        return decorated
    return decorator


class Cache:
    cache = SimpleCache() 
    
    def __init__(self, mem_cache=True, is_json=False):
        self.log('__init__')
        self.cache.enable_mem_cache = mem_cache
        self.cache.data_is_json     = is_json  


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def set(self, name, data, checksum=ADDON_VERSION, expiration=timedelta(minutes=15), json_data=False):
        if not name.startswith(ADDON_ID): name = '%s.%s'%(ADDON_ID,name)
        self.log('set, name = %s, checksum = %s'%(name,checksum))
        self.cache.set(name.lower(),data,checksum,expiration,json_data)
        return data
        
    
    def get(self, name, checksum=ADDON_VERSION, json_data=False):
        if not name.startswith(ADDON_ID): name = '%s.%s'%(ADDON_ID,name)
        self.log('get, name = %s, checksum = %s'%(name,checksum))
        return self.cache.get(name.lower(),checksum,json_data)