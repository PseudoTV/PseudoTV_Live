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

def cacheit(expiration: datetime.timedelta=datetime.timedelta(days=MIN_GUIDEDAYS), checksum: str=ADDON_VERSION, json_data: bool=False):
    def internal(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            method_class = args[0]
            cacheName = "%s.%s"%(method_class.__class__.__name__, method.__name__)
            for item in args[1:]: cacheName += u".%s"%item
            results = method_class.cache.get(cacheName.lower(), checksum, json_data)
            if results: return results
            return method_class.cache.set(cacheName.lower(), method(*args, **kwargs), checksum, expiration, json_data)
        return wrapper
    return internal
    
class Cache:
    cache = SimpleCache()
    
    @contextmanager
    def cacheLocker(self): #simplecache is not thread safe, threadlock not avoiding collisions? Hack/Lazy avoidance.
        if xbmcgui.Window(10000).getProperty('%s.cacheLocker'%(ADDON_ID)) == 'true':
            while not xbmc.Monitor().abortRequested():
                if not xbmcgui.Window(10000).getProperty('%s.cacheLocker'%(ADDON_ID)) == 'true': break
                elif xbmc.Monitor().waitForAbort(0.001): break
        xbmcgui.Window(10000).setProperty('%s.cacheLocker'%(ADDON_ID),'true')
        try: yield
        finally:
            xbmcgui.Window(10000).setProperty('%s.cacheLocker'%(ADDON_ID),'false')


    def __init__(self, mem_cache=False, is_json=False):
        self.cache.enable_mem_cache = mem_cache
        self.cache.data_is_json     = is_json  


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def getname(self, name: str) -> str:
        if not name.startswith(ADDON_ID): name = '%s.%s'%(ADDON_ID,name)
        return name.lower()
        
        
    def set(self, name: str, value, checksum: str=ADDON_VERSION, expiration: datetime.timedelta=datetime.timedelta(minutes=15), json_data: bool=False):
        if value and not DISABLE_CACHE:
            with self.cacheLocker():
                self.log('set, name = %s'%self.getname(name))
                self.cache.set(self.getname(name),value,checksum,expiration,json_data)
        return value
        
    
    def get(self, name: str, checksum: str=ADDON_VERSION, json_data: bool=False):
        if not DISABLE_CACHE:
            with self.cacheLocker():
                self.log('get, name = %s'%self.getname(name))
                return (self.cache.get(self.getname(name),checksum,json_data))
        
            
    def clear(self, name: str, wait: int=15):
        import sqlite3
        self.log('clear, name = %s'%self.getname(name))
        sc = xbmcvfs.translatePath(xbmcaddon.Addon(id='script.module.simplecache').getAddonInfo('profile'))
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