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

from variables   import *
from logger      import log
from fileaccess  import FileAccess, FileLock


class Service(object):
    monitor = MONITOR()
    def _shutdown(self, wait=CPU_CYCLE) -> bool:
        return (self.monitor.waitForAbort(wait) | (Globals._getEXTProperty('%s.pendingShutdown'%(ADDON_ID),False)))
    def _interrupt(self) -> bool:
        return (Globals._getEXTProperty('%s.pendingShutdown'%(ADDON_ID),False) | Globals._getEXTProperty('%s.pendingRestart'%(ADDON_ID),False) | Globals._getEXTProperty('%s.pendingInterrupt'%(ADDON_ID),False))
    def _suspend(self, wait=CPU_CYCLE) -> bool:
        if wait > 0: self._sleep(wait)
        return Globals._getEXTProperty('%s.pendingSuspend'%(ADDON_ID),False)
    def _sleep(self, wait=CPU_CYCLE):
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) | self._interrupt()): return True
            else: wait -= CPU_CYCLE
        return False

def cacheit(expiration=datetime.timedelta(minutes=15), checksum=ADDON_VERSION):
    def internal(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            # Build safe, truncated key to avoid huge key strings (which can blow memory)
            instance = args[0]
            cacheName = "%s.%s" % (instance.__class__.__name__, method.__name__)
            for item in args[1:]:
                cacheName += u".%s"%(FileAccess._getMD5(item))
            for k, v in list(kwargs.items()):
                cacheName += u".%s=%s"%(k,FileAccess._getMD5(v))
            results = instance.cache.get(cacheName, checksum,)
            if results is not None:
                log('%s, cacheit returning cache' % (method.__qualname__.replace('.', ': ')))
                return results
            log('%s, cacheit saving results' % (method.__qualname__.replace('.', ': ')))
            value = method(*args, **kwargs)
            instance.cache.set(cacheName, value, checksum, expiration,)
            return value
        return wrapper
    return internal

class Cache(object):
    service = Service()
    monitor = service.monitor

    def __init__(self, mem_cache=False, disable_cache=False):
        self.cache = _Cache(service=self.service)
        self.cache.enable_mem_cache = mem_cache
        # disable_cache is True if explicitly passed OR addon settings say so
        self.disable_cache = (disable_cache or REAL_SETTINGS.getSettingBool('Disable_Cache'))
        self.log('__init__, mem_cache = %s, disable_cache = %s' % (mem_cache, disable_cache))


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s [%s]: %s' % (self.__class__.__name__, {True:'MEM',False:'DB'}[self.cache.enable_mem_cache], msg), level)


    def set(self, name, value, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        # don't store empty values when cache disabled unless explicitly allowed
        if not any([self.disable_cache,value is None]):
            self.cache.set(name, value, checksum, expiration)
            self.log('set, name = %s, value = %s, type = %s' % (name, '%s...'%(str(value)[:128]),type(value).__name__))
        return value


    def get(self, name, checksum=ADDON_VERSION):
        if not self.disable_cache:
            try:
                value = self.cache.get(name, checksum)
                self.log('get, name = %s, value = %s, type = %s' % (name, '%s...'%(str(value)[:128]),type(value).__name__))
                return value
            except Exception as e:
                self.log("get, name = %s failed! %s" % (name, e), xbmc.LOGERROR)
                self.cache.clr(name)


    def clr(self, name, wait=15):
        self.log('clr, name = %s' % name)
        self.cache.clr(name)


class _Cache(object):
    _lock       = RLock() 
    _exit       = False
    _database   = None
    _cache_idx  = deque()
    global_checksum  = ADDON_VERSION
    enable_mem_cache = False


    @staticmethod
    def _getFreeMEM():
        try:              free = int("".join(re.findall(r"\d", BUILTIN.getInfoLabel('FreeMemory','System'))))
        except Exception: free = 1024 #1GB
        return floor(free * (REAL_SETTINGS.getSettingInt('Cache_MEM_Limit') / 100)) * 1024 * 1024
        
        
    def __init__(self, service=None, winID=10000):
        self.service   = service
        self.monitor   = service.monitor
        self.window    = xbmcgui.Window(winID)
        self.max_bytes = _Cache._getFreeMEM()
        self.dbfile    = FileAccess.translatePath(os.path.join(REAL_SETTINGS.getSetting('User_Folder'), 'cache.db'))
        self._auto_clean_interval = int(REAL_SETTINGS.getSetting('Max_Days') or "3") * 86400 
        self.log('__init__, max_bytes = %s' % self.max_bytes)


    def __del__(self):
        if not self._exit:
            self._close()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)


    def _open(self):
        with self._lock:
            retries = 0
            while not self.monitor.abortRequested() and retries < LOCK_MAX_FILE_TIMEOUT:
                try:
                    _database = sqlite3.connect(self.dbfile, timeout=30, check_same_thread=False)
                    _database.execute("PRAGMA journal_mode=WAL;")
                    _database.execute("PRAGMA synchronous=NORMAL;")
                    _database.execute("""
                        CREATE TABLE IF NOT EXISTS cache(
                            id TEXT UNIQUE, 
                            expires INTEGER, 
                            data BLOB, 
                            checksum INTEGER
                        )""")
                    _database.commit()
                    return _database
                except sqlite3.OperationalError:
                    if self.service._sleep(0.5): break
                    retries += 1
                except Exception as e: 
                    self.log("_open failed: %s" % str(e), xbmc.LOGERROR)
                    break
                    

    def _execute_sql(self, query, data=None):
        with self._lock:
            if self._database is None: self._database = self._open()
            if self._database:
                if isinstance(data, list): result = self._database.executemany(query, data)
                elif data:                 result = self._database.execute(query, data)
                else:                      result = self._database.execute(query)
                self._database.commit()
                return result


    def get(self, endpoint, checksum=""):
        checksum = self.getChecksum(checksum)
        cur_time = self.getTimestamp(datetime.datetime.now())
        with self._lock:
            if self.enable_mem_cache:
                result = self._getMEM(endpoint, checksum, cur_time)
                if result: return result
            return self._getDB(endpoint, checksum, cur_time)


    def set(self, endpoint, data, checksum="", expiration=datetime.timedelta(days=30)):
        checksum = self.getChecksum(checksum)
        expires  = self.getTimestamp(datetime.datetime.now() + expiration)
        with self._lock:
            if self.enable_mem_cache and not self._exit:
                self._setMEM(endpoint, checksum, expires, data)
            query = "INSERT OR REPLACE INTO cache(id, expires, data, checksum) VALUES (?, ?, ?, ?)"
            self._execute_sql(query, (endpoint, expires, FileAccess.dumpPICKLE(data), checksum))


    def clr(self, endpoint, wait=15):
        query = "DELETE FROM cache WHERE id LIKE ?'"
        self._execute_sql(query, (endpoint + '%',))


    def _getDB(self, endpoint, checksum, cur_time):
        result     = None
        query      = "SELECT expires, data, checksum FROM cache WHERE id = ?"
        cache_data = self._execute_sql(query, (endpoint,))
        if cache_data:
            cache_data = cache_data.fetchone()
            if cache_data and cache_data[0] > cur_time:
                if not checksum or cache_data[2] == checksum:
                    try: 
                        result = FileAccess.loadPICKLE(cache_data[1])
                        if self.enable_mem_cache and not self._exit: self._setMEM(endpoint, checksum, cache_data[0], result)
                    except Exception as e: self.log("_getDB, failed! %s"%(e), xbmc.LOGERROR)
        return result


    def _getMEM(self, endpoint, checksum, cur_time):
        result = None
        try: 
            cachedata = FileAccess._decodeString(Globals._getEXTProperty('%s.%s'%(ADDON_ID,endpoint)))
            if cachedata[0] > cur_time and not checksum or checksum == cachedata[2]: 
                result = cachedata[1]
        except Exception as e: pass
        return result


    def _setMEM(self, endpoint, checksum, expires, data):
        """Thread-safe memory allocation with FIFO eviction."""
        try:
            encoded_data = FileAccess._encodeString((expires, data, checksum))
            item_size = sys.getsizeof(encoded_data)
            if item_size > self.max_bytes: return
            with self._lock:
                Globals._setEXTProperty('%s.%s' % (ADDON_ID, endpoint), encoded_data)
                self._cache_idx.append((endpoint, item_size))
                self._trimMEM()
        except Exception as e:
            self.log("_setMEM failed: %s" % e)


    def _trimMEM(self):
        """Evicts oldest items until memory usage is under max_bytes."""
        current_total = sum(size for _, size in self._cache_idx)
        while self.monitor.abortRequested() and current_total > self.max_bytes and self._cache_idx:
            endpoint, size = self._cache_idx.popleft()
            Globals._clrEXTProperty('%s.%s' % (ADDON_ID, endpoint))
            current_total -= size
            self.log("_trimMEM, %s to free %s bytes" % (endpoint, size))


    def _clean(self):
        cur_time      = datetime.datetime.now()
        cur_timestamp = self.getTimestamp(cur_time)
        self.log("_clean, running...")
        if not Globals._getEXTProperty("%s.cache.cleanbusy"%(ADDON_ID)):
            Globals._setEXTProperty("%s.cache.cleanbusy"%(ADDON_ID), "busy")
            query = "SELECT id, expires FROM cache"
            for cache_data in self._execute_sql(query).fetchall():
                if self.service._shutdown(CPU_CYCLE): break
                else:
                    cache_id      = cache_data[0]
                    cache_expires = cache_data[1]
                    Globals._clrEXTProperty('%s.%s'%(ADDON_ID,cache_id))
                    if cache_expires < cur_timestamp:
                        query = 'DELETE FROM cache WHERE id = ?'
                        self._execute_sql(query, (cache_id,))
                        self.log("_clean, delete from db %s" % cache_id)

            self._execute_sql("VACUUM")
            Globals._setEXTProperty("%s.cache.lastexecuted"%(ADDON_ID), repr(cur_time))
            Globals._clrEXTProperty("%s.cache.cleanbusy"%(ADDON_ID))
            self.log("_clean, auto _cleanUP done")


    def _close(self):
        with self._lock:
            self._exit = True
            if self._database:
                try:
                    self._clean()
                    self._database.commit()
                    self._database.close()
                except: pass
                self._database = None
            self._exit = False

                    
    @staticmethod
    def getTimestamp(date_time):
        try:              return int(date_time.timestamp())
        except Exception: return int(time.mktime(date_time.timetuple()))


    def getChecksum(self, stringinput):
        if not stringinput and not self.global_checksum: return 0
        combined = "%s-%s" % (self.global_checksum, stringinput) if self.global_checksum else str(stringinput)
        return abs(hash(combined)) % (10**8)