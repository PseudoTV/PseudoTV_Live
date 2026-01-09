#   Copyright (C) 2025 Lunatixz
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

import sqlite3

from globals     import *
from functools   import wraps, reduce
from fileaccess  import FileAccess, FileLock
from kodi_six    import xbmc, xbmcgui

class Service(object):
    monitor = MONITOR()
    def _shutdown(self, wait=1.0) -> bool:
        pendingShutdown = xbmcgui.Window(10000).getProperty('%s.pendingShutdown'%(ADDON_ID)) == "true"
        return (self.monitor.waitForAbort(wait) | pendingShutdown)
    def _interrupt(self) -> bool:
        pendingShutdown   = xbmcgui.Window(10000).getProperty('%s.pendingShutdown'%(ADDON_ID)) == "true"
        pendingInterrupt  = xbmcgui.Window(10000).getProperty('%s.pendingInterrupt'%(ADDON_ID)) == "true"
        pendingRestart    = xbmcgui.Window(10000).getProperty('%s.pendingRestart'%(ADDON_ID)) == "true"
        interruptActivity = xbmcgui.Window(10000).getProperty('%s.interruptActivity'%(ADDON_ID)) == "true"
        return (pendingShutdown | pendingRestart | pendingInterrupt | interruptActivity)
    def _suspend(self, wait=1.0) -> bool:
        pendingSuspend = xbmcgui.Window(10000).getProperty('%s.pendingSuspend'%(ADDON_ID)) == "true"
        return pendingSuspend
    def _sleep(self, wait=1.0):
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) | self._interrupt()): return True
            else: wait -= CPU_CYCLE
        return False

def cacheit(expiration=datetime.timedelta(minutes=15), checksum=ADDON_VERSION, json_data=False):
    def internal(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            method_class = args[0]
            cacheName = "%s.%s"%(method_class.__class__.__name__, method.__name__)
            for item in args[1:]: cacheName += u".%s"%item
            for k, v in list(kwargs.items()): cacheName += u".%s"%(v)
            results = method_class.cache.get(cacheName, checksum, json_data)
            if results:
                log('%s, cacheit returning cache'%(method.__qualname__.replace('.',': ')))
                return results
            log('%s, cacheit saving results'%(method.__qualname__.replace('.',': ')))
            return method_class.cache.set(cacheName, method(*args, **kwargs), checksum, expiration, json_data)
        return wrapper
    return internal
    
class Cache(object):
    service = Service()

    @contextmanager
    def cacheLocker(self): #Lazy collision avoidance.
        while not self.service.monitor.abortRequested():
            if   self.service._shutdown(CPU_CYCLE): break
            elif xbmcgui.Window(10000).getProperty('%s.cacheLocker'%(ADDON_ID)) != 'true': break
        xbmcgui.Window(10000).setProperty('%s.cacheLocker'%(ADDON_ID),'true')
        try: yield
        finally:
            xbmcgui.Window(10000).setProperty('%s.cacheLocker'%(ADDON_ID),'false')


    def __init__(self, mem_cache=False, is_json=False, disable_cache=False):
        self.cache = _Cache(service=self.service)
        self.cache.enable_mem_cache = mem_cache
        self.cache.data_is_json     = is_json  
        self.disable_cache          = (disable_cache | REAL_SETTINGS.getSettingBool('Disable_Cache'))
        self.log('__init__, mem_cache = %s, is_json = %s, disable_cache = %s'%(mem_cache,is_json,disable_cache))


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s [%s]: %s'%(self.__class__.__name__,{True:'MEM',False:'DB'}[self.cache.enable_mem_cache],msg),level)


    def set(self, name, value, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15), json_data=False):
        if not self.disable_cache or (not isinstance(value,(bool,list,dict)) and not value):
            with self.cacheLocker():
                self.log('set, name = %s, value = %s'%(name,'%s...'%(str(value)[:128])))
                self.cache.set(name,value,checksum,expiration,json_data)
        return value
        
    
    def get(self, name, checksum=ADDON_VERSION, json_data=False):
        if not self.disable_cache:
            with self.cacheLocker():
                try: 
                    value = self.cache.get(name,checksum,json_data)
                    self.log('get, name = %s, value = %s'%(name,'%s...'%(str(value)[:128])))
                    return value
                except Exception as e:
                    self.log("get, name = %s failed! %s"%(name,e), xbmc.LOGERROR)
                    self.cache.clr(name)
                    
                    
    def clear(self, name, wait=15):
        with self.cacheLocker():
            self.log('clear, name = %s'%name)
            self.cache.clear(name)
            
            
class _Cache(object):
    enable_mem_cache     = False
    data_is_json         = False
    window               = None
    global_checksum      = ADDON_VERSION
    _auto_clean_interval = datetime.timedelta(hours=MAX_GUIDEDAYS)
    _busy_tasks          = []
    _database            = None
    
    def __init__(self, service=None, winID=10000):
        self.service = service
        self.window  = xbmcgui.Window(winID)
        self.chkCleanup()


    def __del__(self):
        del self.window
        
        
    def _getProperty(self, key):
        return self.window.getProperty('%s.%s'%(ADDON_ID,key))
        
        
    def _setProperty(self, key, value):
        self.window.setProperty('%s.%s'%(ADDON_ID,key), value)
        return value
                
                
    def _clrProperty(self, key):
        return self.window.clearProperty('%s.%s'%(ADDON_ID,key))

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def chkCleanup(self):
        cur_time     = datetime.datetime.now()
        lastexecuted = self._getProperty("cache.lastexecuted")
        if not lastexecuted: self._setProperty("cache.lastexecuted", repr(cur_time))
        elif (eval(lastexecuted) + self._auto_clean_interval) < cur_time:
            self._cleanUp()


    def get(self, endpoint, checksum="", json_data=False):
        checksum = self.getChecksum(checksum)
        cur_time = self.getTimestamp(datetime.datetime.now())
        result   = None
        if self.enable_mem_cache: result = self._get_mem_cache(endpoint, checksum, cur_time, json_data)
        if result is None:        result = self._get_db_cache(endpoint, checksum, cur_time, json_data)
        return result


    def set(self, endpoint, data, checksum="", expiration=datetime.timedelta(days=30), json_data=False):
        task_name = "set.%s" % endpoint
        self._busy_tasks.append(task_name)
        checksum = self.getChecksum(checksum)
        expires  = self.getTimestamp(datetime.datetime.now() + expiration)
        if self.enable_mem_cache: self._set_mem_cache(endpoint, checksum, expires, data, json_data)
        self._set_db_cache(endpoint, checksum, expires, data, json_data)
        self._busy_tasks.remove(task_name)

    
    def clr(self, endpoint, wait=15):
        dbfile = FileAccess.translatePath(CACHEFLEPATH)
        if FileAccess.exists(dbfile):
            with FileAccess.FileLock(dbfile):
                try:
                    connection = sqlite3.connect(dbfile, timeout=wait, isolation_level=None)
                    connection.execute('DELETE FROM cache WHERE id LIKE ?', (endpoint + '%',))
                    connection.commit()
                except sqlite3.Error as e: self.log('clr, failed! %s' % e, xbmc.LOGERROR)
                finally:
                    if connection:
                        connection.close()
                        del connection
                
          
    def _get_mem_cache(self, endpoint, checksum, cur_time, json_data):
        result    = None
        cachedata = self._getProperty(endpoint)
        if cachedata:
            if json_data or self.data_is_json: cachedata = json.loads(cachedata)
            else:                              cachedata = literal_eval(cachedata)
            if cachedata[0] > cur_time:
                if not checksum or checksum == cachedata[2]: result = cachedata[1]
        return result


    def _set_mem_cache(self, endpoint, checksum, expires, data, json_data):
        cachedata = (expires, data, checksum)
        if json_data or self.data_is_json: cachedata_str = json.dumps(cachedata)
        else:                              cachedata_str = repr(cachedata)
        self._setProperty(endpoint, cachedata_str)


    def _get_db_cache(self, endpoint, checksum, cur_time, json_data):
        result     = None
        query      = "SELECT expires, data, checksum FROM cache WHERE id = ?"
        cache_data = self._execute_sql(query, (endpoint,))
        if cache_data:
            cache_data = cache_data.fetchone()
            if cache_data and cache_data[0] > cur_time:
                if not checksum or cache_data[2] == checksum:
                    if json_data or self.data_is_json: result = json.loads(cache_data[1])
                    else:                              result = literal_eval(cache_data[1])
                    if self.enable_mem_cache: self._set_mem_cache(endpoint, checksum, cache_data[0], result, json_data)
        return result


    def _set_db_cache(self, endpoint, checksum, expires, data, json_data):
        query = "INSERT OR REPLACE INTO cache( id, expires, data, checksum) VALUES (?, ?, ?, ?)"
        if json_data or self.data_is_json: data = json.dumps(data)
        else:                              data = repr(data)
        self._execute_sql(query, (endpoint, expires, data, checksum))


    def _cleanUp(self):
        self._busy_tasks.append(__name__)
        cur_time      = datetime.datetime.now()
        cur_timestamp = self.getTimestamp(cur_time)
        self.log("_cleanUp, running _cleanUp...")
        
        if self._getProperty("cache.cleanbusy"): return
        else:
            self._setProperty("cache.cleanbusy", "busy")
            query = "SELECT id, expires FROM cache"
            for cache_data in self._execute_sql(query).fetchall():
                if self.service._shutdown(CPU_CYCLE): return
                cache_id      = cache_data[0]
                cache_expires = cache_data[1]
                self._clrProperty(cache_id)
                if cache_expires < cur_timestamp:
                    query = 'DELETE FROM cache WHERE id = ?'
                    self._execute_sql(query, (cache_id,))
                    self.log("_cleanUp, delete from db %s" % cache_id)

            self._execute_sql("VACUUM")
            self._busy_tasks.remove(__name__)
            self._setProperty("cache.lastexecuted", repr(cur_time))
            self._clrProperty("cache.cleanbusy")
            self.log("_cleanUp, auto _cleanUp done")


    def _execute_sql(self, query, data=None):
        retries = 0
        result  = None
        dbfile  = FileAccess.translatePath(CACHEFLEPATH)
        if not FileAccess.exists(USER_LOC): FileAccess.mkdirs(USER_LOC)
        try:
            connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
            connection.execute('SELECT * FROM cache LIMIT 1')
        except Exception as e:
            if FileAccess.exists(dbfile): FileAccess.delete(dbfile)
            try:
                connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
                connection.execute( """CREATE TABLE IF NOT EXISTS cache(id TEXT UNIQUE, expires INTEGER, data TEXT, checksum INTEGER)""")
            except Exception as e:
                self.log("_execute_sql, Failed! while initializing connection: %s" % str(e), xbmc.LOGWARNING)
                return

        while not self.service.monitor.abortRequested() and not retries == LOCK_MAX_FILE_TIMEOUT:
            if self.service._shutdown(CPU_CYCLE): break
            else:
                try:
                    if isinstance(data, list): result = connection.executemany(query, data)
                    elif data:                 result = connection.execute(query, data)
                    else:                      result = connection.execute(query)
                    return result
                except Exception as e:
                    if "connection is locked" in e:
                        self.log("_execute_sql, retrying DB commit...")
                        retries += 1
                        self.service._sleep(LOCK_MAX_FILE_DELAY)
                    else: break
                self.log("_execute_sql, connection ERROR ! -- %s" % str(e), xbmc.LOGWARNING)
                    
        if connection:
            connection.close()
            del connection
        return None


    @staticmethod
    def getTimestamp(date_time):
        return int(time.mktime(date_time.timetuple()))


    def getChecksum(self, stringinput):
        if not stringinput and not self.global_checksum: return 0
        if self.global_checksum: stringinput = "%s-%s" %(self.global_checksum, stringinput)
        else:                    stringinput = str(stringinput)
        return reduce(lambda x, y: x + y, map(ord, stringinput))