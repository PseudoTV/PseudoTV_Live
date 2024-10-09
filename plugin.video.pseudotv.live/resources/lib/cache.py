#   Copyright (C) 2024 Lunatixz
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
#
# -*- coding: utf-8 -*-

from globals   import *
from functools import wraps
try:    from simplecache             import SimpleCache
except: from simplecache.simplecache import SimpleCache #pycharm stub

ADDON_ID = 'plugin.video.pseudotv.live'

def cacheit(expiration=datetime.timedelta(days=MIN_GUIDEDAYS), checksum=ADDON_VERSION, json_data=False):
    def internal(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            method_class = args[0]
            cacheName = "%s.%s"%(method_class.__class__.__name__, method.__name__)
            for item in args[1:]: cacheName += u".%s"%item
            for k, v in list(kwargs.items()): cacheName += u".%s"%(v)
            results = method_class.cache.get(cacheName.lower(), checksum, json_data)
            if results: return results
            return method_class.cache.set(cacheName.lower(), method(*args, **kwargs), checksum, expiration, json_data)
        return wrapper
    return internal
    
class Cache:
    lock  = Lock()
    cache = SimpleCache()
    
    @contextmanager
    def cacheLocker(self): #simplecache is not thread safe, threadlock not avoiding collisions? Hack/Lazy avoidance.
        xbmcgui.Window(10000).setProperty('%s.cacheLocker'%(ADDON_ID),'true')
        try: yield self.log('cacheLocker, Locked!')
        finally: xbmcgui.Window(10000).setProperty('%s.cacheLocker'%(ADDON_ID),'false')


    def cacheLocked(self):
        return xbmcgui.Window(10000).getProperty('%s.cacheLocker'%(ADDON_ID)) == 'true'
    
    
    def __init__(self, mem_cache=False, is_json=False):
        self.cache.enable_mem_cache = mem_cache
        self.cache.data_is_json     = is_json  


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def getname(self, name):
        if not name.startswith(ADDON_ID): name = '%s.%s'%(ADDON_ID,name)
        return name.lower()
        
        
    def set(self, name, value, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15), json_data=False):
        # with self.lock:
        if value and not DISABLE_CACHE and not self.cacheLocked():
            with self.cacheLocker():
                self.log('set, name = %s'%self.getname(name))
                self.cache.set(self.getname(name),value,checksum,expiration,json_data)
        return value
        
    
    def get(self, name, checksum=ADDON_VERSION, json_data=False):
        # with self.lock:
        if not DISABLE_CACHE and not self.cacheLocked():
            with self.cacheLocker():
                self.log('get, name = %s'%self.getname(name))
                return self.cache.get(self.getname(name),checksum,json_data)
        
            
    def clear(self, name, wait=15):
        import sqlite3
        self.log('clear, name = %s'%self.getname(name))
        sc = FileAccess.translatePath(xbmcaddon.Addon(id='script.module.simplecache').getAddonInfo('profile'))
        dbpath = os.path.join(sc, 'simplecache.db')
        connection = sqlite3.connect(dbpath, timeout=wait, isolation_level=None)
        try:
            connection.execute('DELETE FROM simplecache WHERE id LIKE ?', (self.getname(name) + '%',))
            connection.commit()
            connection.close()
        except sqlite3.Error as e:
            self.log('clear, failed! %s'%(e), xbmc.LOGERROR)
        finally:
            del connection
            del sqlite3