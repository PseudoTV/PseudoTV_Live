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
from functools   import wraps
from fileaccess  import FileAccess
from pool        import ExecutorPool
        
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
            # return method_class.cache.set(cacheName, method(*args, **kwargs), checksum, expiration, json_data)
            log('%s, cacheit saving results'%(method.__qualname__.replace('.',': ')))
            return method_class.cache.set(cacheName, ExecutorPool().executor(method, None, *args, **kwargs), checksum, expiration, json_data)
        return wrapper
    return internal
    
class Service:
    monitor = MONITOR()
    def _is(self, text):
        return text == "true"
    def _shutdown(self, wait=1.0) -> bool:
        return (self._wait(wait) | self._is(xbmcgui.Window(10000).getProperty('%s.pendingShutdown'%(ADDON_ID))))
    def _interrupt(self) -> bool:
        return self._is(xbmcgui.Window(10000).getProperty('%s.pendingInterrupt'%(ADDON_ID)))
    def _suspend(self, wait=1.0) -> bool:
        return (self._wait(wait) | self._is(xbmcgui.Window(10000).getProperty('%s.pendingSuspend'%(ADDON_ID))))
    def _wait(self, wait=1.0):
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) | self._is(xbmcgui.Window(10000).getProperty('%s.pendingShutdown'%(ADDON_ID))) | self._is(xbmcgui.Window(10000).getProperty('%s.pendingRestart'%(ADDON_ID))) | self._is(xbmcgui.Window(10000).getProperty('%s.pendingSuspend'%(ADDON_ID))) | self._is(xbmcgui.Window(10000).getProperty('%s.pendingInterrupt'%(ADDON_ID)))): return True
            else: wait -= CPU_CYCLE
        return False

class Cache:
    lock    = Lock()
    service = Service()

    @contextmanager
    def cacheLocker(self): #Hack/Lazy avoidance.
        while not self.service.monitor.abortRequested():
            if self.service._shutdown(CPU_CYCLE) or self.service._interrupt(): break
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
                    self.cache.clear(name)
                    
                    
    def clear(self, name, wait=15):
        with self.cacheLocker():
            self.log('clear, name = %s'%name)
            self.cache.clear(name)
            
            
class _Cache(object):
    '''simple stateless caching system for Kodi'''
    _exit            = False
    _busy_tasks      = []
    _database        = None
    monitor          = MONITOR()
    global_checksum  = None
    enable_mem_cache = True
    data_is_json     = False
    clean_interval   = datetime.timedelta(hours=4)


    def __init__(self, service=None):
        if service is None: service = Service()
        self.service = service
        self.check_cleanup()
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def close(self):
        '''tell any tasks to stop immediately (as we can be called multithreaded) and cleanup objects'''
        self._exit = True
        # wait for all tasks to complete
        while self._busy_tasks and not self.service.monitor.abortRequested():
            if self.service._wait(25): break
        self.log("Closed")


    def __del__(self):
        '''make sure close is called'''
        if not self._exit: self.close()


    def get(self, endpoint, checksum="", json_data=False):
        '''
            get object from cache and return the results
            endpoint: the (unique) name of the cache object as reference
            checkum: optional argument to check if the checksum in the cacheobject matches the checkum provided
        '''
        checksum = self._get_checksum(checksum)
        cur_time = self._get_timestamp(datetime.datetime.now())
        result = None
        # 1: try memory cache first
        if self.enable_mem_cache: result = self._get_mem_cache(endpoint, checksum, cur_time, json_data)
        # 2: fallback to _database cache
        if result is None: result = self._get_db_cache(endpoint, checksum, cur_time, json_data)
        return result


    def set(self, endpoint, data, checksum="", expiration=datetime.timedelta(days=30), json_data=False):
        '''
            set data in cache
        '''
        task_name = "set.%s" % endpoint
        self._busy_tasks.append(task_name)
        checksum = self._get_checksum(checksum)
        expires  = self._get_timestamp(datetime.datetime.now() + expiration)
        # memory cache: write to window property
        if self.enable_mem_cache and not self._exit: self._set_mem_cache(endpoint, checksum, expires, data, json_data)
        # db cache
        if not self._exit: self._set_db_cache(endpoint, checksum, expires, data, json_data)
        # remove this task from list
        self._busy_tasks.remove(task_name)

    
    def clear(self, name, wait=15):
        dbfile = xbmcvfs.translatePath(CACHEFLEPATH)
        if xbmcvfs.exists(dbfile):
            try:
                connection = sqlite3.connect(dbfile, timeout=wait, isolation_level=None)
                connection.execute('DELETE FROM cache WHERE id LIKE ?', (name + '%',))
                connection.commit()
            except sqlite3.Error as e: self.log('clear, failed! %s' % e, xbmc.LOGERROR)
            finally:
                if connection:
                    connection.close()
                    del connection
                self.close()
                
            
    def check_cleanup(self):
        '''check if cleanup is needed - public method, may be called by calling addon'''
        cur_time = datetime.datetime.now()
        lastexecuted = xbmcgui.Window(10000).getProperty("%s.cache.lastexecuted"%(ADDON_ID))
        if not lastexecuted: xbmcgui.Window(10000).setProperty("'%s.cache.lastexecuted"%(ADDON_ID), repr(cur_time))
        elif (eval(lastexecuted) + self.clean_interval) < cur_time: self._do_cleanup()


    def _get_mem_cache(self, endpoint, checksum, cur_time, json_data):
        '''
            get cache data from memory cache
            we use window properties because we need to be stateless
        '''
        result    = None
        cachedata = xbmcgui.Window(10000).getProperty('%s.%s'%(ADDON_ID,endpoint))
        if cachedata:
            if json_data or self.data_is_json: 
                try:    cachedata = json.loads(cachedata)
                except: cachedata = None
            else:       cachedata = eval(cachedata)
            if cachedata[0] > cur_time:
                if not checksum or checksum == cachedata[2]: result = cachedata[1]
        return result


    def _set_mem_cache(self, endpoint, checksum, expires, data, json_data):
        '''
            window property cache as alternative for memory cache
            usefull for (stateless) plugins
        '''
        cachedata = (expires, data, checksum)
        if json_data or self.data_is_json:
            try:    cachedata_str = json.dumps(cachedata)
            except: cachedata_str = ""
        else:       cachedata_str = repr(cachedata)
        xbmcgui.Window(10000).setProperty('%s.%s'%(ADDON_ID,endpoint), cachedata_str)


    def _get_db_cache(self, endpoint, checksum, cur_time, json_data):
        '''get cache data from sqllite _database'''
        result = None
        query  = "SELECT expires, data, checksum FROM cache WHERE id = ?"
        cache_data = self._execute_sql(query, (endpoint,))
        if cache_data:
            cache_data = cache_data.fetchone()
            if cache_data and cache_data[0] > cur_time:
                if not checksum or cache_data[2] == checksum:
                    if json_data or self.data_is_json:
                        try:    result = json.loads(cache_data[1])
                        except: result = None
                    else:       result = eval(cache_data[1])
                    # also set result in memory cache for further access
                    if self.enable_mem_cache: self._set_mem_cache(endpoint, checksum, cache_data[0], result, json_data)
        return result


    def _set_db_cache(self, endpoint, checksum, expires, data, json_data):
        ''' store cache data in _database '''
        query = "INSERT OR REPLACE INTO cache( id, expires, data, checksum) VALUES (?, ?, ?, ?)"
        if json_data or self.data_is_json:
            try:    data = json.dumps(data)
            except: data = None
        else:       data = repr(data)
        self._execute_sql(query, (endpoint, expires, data, checksum))


    def _do_cleanup(self):
        '''perform cleanup task'''
        if self._exit or self.service.monitor.abortRequested(): return
        self._busy_tasks.append(__name__)
        cur_time = datetime.datetime.now()
        cur_timestamp = self._get_timestamp(cur_time)
        self.log("Running cleanup...")
        if xbmcgui.Window(10000).getProperty("%s.cache.cleanbusy"%(ADDON_ID)): return
        xbmcgui.Window(10000).setProperty("%s.cache.cleanbusy"%(ADDON_ID), "busy")

        query = "SELECT id, expires FROM cache"
        for cache_data in self._execute_sql(query).fetchall():
            cache_id = cache_data[0]
            cache_expires = cache_data[1]

            if self._exit or self.service.monitor.abortRequested(): return
            # always cleanup all memory objects on each interval
            xbmcgui.Window(10000).clearProperty('%s.%s'%(ADDON_ID,cache_id))
            # clean up db cache object only if expired
            if cache_expires < cur_timestamp:
                query = 'DELETE FROM cache WHERE id = ?'
                self._execute_sql(query, (cache_id,))
                self.log("delete from db %s" % cache_id)

        # compact db
        self._execute_sql("VACUUM")
        # remove task from list
        self._busy_tasks.remove(__name__)
        xbmcgui.Window(10000).setProperty("%s.cache.lastexecuted"%(ADDON_ID), repr(cur_time))
        xbmcgui.Window(10000).clearProperty("%s.cache.cleanbusy"%(ADDON_ID))
        self.log("Auto cleanup done")


    def _get_database(self):
        '''get reference to our sqllite _database - performs basic integrity check'''
        if not xbmcvfs.exists(USER_LOC): xbmcvfs.mkdirs(USER_LOC)
        dbfile = xbmcvfs.translatePath(CACHEFLEPATH)
        try:
            connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
            connection.execute('SELECT * FROM cache LIMIT 1')
            return connection
        except Exception as error:
            # our _database is corrupt or doesn't exist yet, we simply try to recreate it
            if xbmcvfs.exists(dbfile): xbmcvfs.delete(dbfile)
            try:
                connection = sqlite3.connect(dbfile, timeout=30, isolation_level=None)
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS cache(
                    id TEXT UNIQUE, expires INTEGER, data TEXT, checksum INTEGER)""")
                return connection
            except Exception as error:
                self.log("Exception while initializing _database: %s" % str(error), xbmc.LOGWARNING)
                self.close()
                return None


    def _execute_sql(self, query, data=None):
        '''little wrapper around execute and executemany to just retry a db command if db is locked'''
        retries = 0
        result  = None
        # always use new db object because we need to be sure that data is available for other cache instances
        with self._get_database() as _database:
            while not retries == LOCK_MAX_FILE_TIMEOUT and not self.service.monitor.abortRequested():
                if self._exit: return None
                try:
                    if isinstance(data, list): result = _database.executemany(query, data)
                    elif data:                 result = _database.execute(query, data)
                    else:                      result = _database.execute(query)
                    return result
                except sqlite3.OperationalError as e:
                    if "_database is locked" in e:
                        self.log("retrying DB commit...")
                        retries += 1
                        self.service.monitor.waitForAbort(LOCK_MAX_FILE_DELAY)
                    else: break
                except Exception as e: break
                self.log("_database ERROR ! -- %s" % str(e), xbmc.LOGWARNING)
        return None


    @staticmethod
    def _get_timestamp(date_time):
        '''Converts a datetime object to unix timestamp'''
        return int(time.mktime(date_time.timetuple()))


    def _get_checksum(self, stringinput):
        '''get int checksum from string'''
        if not stringinput and not self.global_checksum: return 0
        if self.global_checksum: stringinput = "%s-%s" %(self.global_checksum, stringinput)
        else:                    stringinput = str(stringinput)
        return reduce(lambda x, y: x + y, map(ord, stringinput))