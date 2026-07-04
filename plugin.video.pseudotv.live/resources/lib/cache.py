#   Copyright (C) 2026 Lunatixz
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
from variables   import *
from fileaccess  import FileAccess

def cacheit(expiration=datetime.timedelta(minutes=15), checksum=None):
    def internal(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            nonlocal checksum
            instance = args[0]
            if checksum is None: checksum = ADDON_VERSION# checksum=Globals.PROPERTIES.getProcessID()
            cache_checksum = checksum() if callable(checksum) else checksum
            cache_segments = [f"{instance.__class__.__name__}.{method.__name__}"]
            for item in args[1:]:
                if isinstance(item, (str, int, float, bool)) or item is None:
                    cache_segments.append(str(item))
                elif isinstance(item, dict) and 'id' in item:
                    cache_segments.append(str(item['id']))
                else:
                    cache_segments.append(f"obj_{id(item)}")
            
            for k in sorted(kwargs.keys()):
                v = kwargs[k]
                if isinstance(v, (str, int, float, bool)) or v is None:
                    cache_segments.append(f"{k}={v}")
                else:
                    cache_segments.append(f"{k}=obj_{id(v)}")
            cacheName = ".".join(cache_segments)
            
            results = instance.cache.get(cacheName, cache_checksum)
            if results is not None:
                log(f'{method.__qualname__.replace(".", ": ")}, cacheit returning cache')
                return results
                
            log(f'{method.__qualname__.replace(".", ": ")}, cacheit saving results')
            value = method(*args, **kwargs)
            instance.cache.set(cacheName, value, cache_checksum, expiration)
            return value
        return wrapper
    return internal
    
class Cache(object):
    def __init__(self, mem_cache=False, disable_cache=False):
        self.monitor = xbmc.Monitor()
        self.cache   = _Cache(monitor=self.monitor)
        self.cache.enable_mem_cache = mem_cache
        self.disable_cache = (disable_cache or REAL_SETTINGS.getSetting('Disable_Cache'))
        self.log('__init__, mem_cache = %s, disable_cache = %s' % (mem_cache, disable_cache))

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s [%s]: %s' % (self.__class__.__name__, {True:'MEM|DB',False:'DB'}[self.cache.enable_mem_cache], msg), level)

    def set(self, name, value, checksum=None, expiration=datetime.timedelta(minutes=15)):
        if checksum is None: checksum = ADDON_VERSION# checksum=Globals.PROPERTIES.getProcessID()
        if not any([self.disable_cache,value is None]):
            self.cache._set(name, value, checksum, expiration)
            self.log('set, name = %s, value = %s, type = %s' % (name, '%s...'%(str(value)[:128]),type(value).__name__))
        return value

    def get(self, name, checksum=None):
        if checksum is None: checksum = ADDON_VERSION# checksum=Globals.PROPERTIES.getProcessID()
        if not self.disable_cache:
            try:
                value = self.cache._get(name, checksum)
                self.log('get, name = %s, value = %s, type = %s' % (name, '%s...'%(str(value)[:128]),type(value).__name__))
                return value
            except Exception as e:
                self.log("get, name = %s failed! %s" % (name, e), xbmc.LOGERROR)
                self.cache._clr(name)

    def clear(self, name):
        self.log('clr, name = %s' % name)
        self.cache._clr(name)

    def checkpoint(self):
        self.cache._checkpoint()
        
    def shutdown(self):
        self.cache._shutdown()

class _Cache(object):
    _lock            = RLock() 
    _trim            = False
    _clean           = False
    _exit            = False
    _checkpointing   = False
    _database        = None
    _cache_idx       = deque()
    global_checksum  = '1.0.0'
    enable_mem_cache = False

    def __init__(self, monitor=None, winID=10000):
        self.monitor        = monitor
        self.window         = xbmcgui.Window(winID)
        self.max_bytes      = self.getFreeMEM()
        self.dbfile         = FileAccess.translatePath(CACHE_FLE)
        self.timeout        = int(REAL_SETTINGS.getSetting('API_Timeout'))
        self.clean_interval = MAX_GUIDEDAYS * 86400

    def __del__(self):
        self._chkClean()
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)

    def _open(self):
        with self._lock:
            retries = 0
            while not self.monitor.abortRequested() and retries < LOCK_MAX_FILE_TIMEOUT:
                try:
                    conn = sqlite3.connect(self.dbfile, timeout=self.timeout, check_same_thread=False)
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA synchronous=NORMAL;")
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS cache(
                            id TEXT UNIQUE, 
                            expires INTEGER, 
                            data BLOB, 
                            checksum BLOB
                        )""")
                    conn.commit()
                    return conn
                except sqlite3.OperationalError:
                    if self.monitor.waitForAbort(1.0): break
                    retries += 1
                except Exception as e: 
                    self.log("_open failed: %s" % str(e), xbmc.LOGERROR)
                    break
            return None
                    
    def _execute_sql(self, query, data=None):
        with self._lock:
            if self._exit:
                return None
            if self._checkpointing: 
                if self.monitor.waitForAbort(1.0): return None
                return self._execute_sql(query, data)
            if self._database is None:
                self._database = self._open()
                
            if self._database:
                try:
                    # Fix: Handle executemany cleanly when list of tuples is provided
                    if isinstance(data, list):  
                        result = self._database.executemany(query, data)
                    elif data:                  
                        result = self._database.execute(query, data)
                    else:                       
                        result = self._database.execute(query)
                    self._database.commit()
                    return result
                except Exception as e:
                    self.log(f"SQL Error during [{query[:48]}]: {e}", xbmc.LOGERROR)
                    return None

    def _get(self, endpoint, checksum=""):
        checksum = self.getChecksum(checksum)
        cur_time = self.getTimestamp(datetime.datetime.now())
        with self._lock:
            if self.enable_mem_cache:
                result = self._getMEM(endpoint, checksum, cur_time)
                if result is not None: return result
            return self._getDB(endpoint, checksum, cur_time)

    def _set(self, endpoint, data, checksum="", delta_time=-1):
        checksum = self.getChecksum(checksum)
        expires  = delta_time
        if isinstance(delta_time, datetime.timedelta):
            expires = self.getTimestamp(datetime.datetime.now() + delta_time)
        with self._lock:
            if self.enable_mem_cache and not self._exit: 
                self._setMEM(endpoint, checksum, expires, data)
            query = "INSERT OR REPLACE INTO cache(id, expires, data, checksum) VALUES (?, ?, ?, ?)"
            self._execute_sql(query, (endpoint, expires, FileAccess.dumpPICKLE(data), checksum))

    def _clr(self, endpoint):
        query = "DELETE FROM cache WHERE id LIKE ?"
        self._execute_sql(query, (endpoint + '%',))

    def _getDB(self, endpoint, checksum, cur_time):
        query  = "SELECT expires, data, checksum FROM cache WHERE id = ?"
        cursor = self._execute_sql(query, (endpoint,))
        cache_data = cursor.fetchone() if cursor else None
        
        if not cache_data:                                   return None
        if cache_data[0] >= 0 and cache_data[0] <= cur_time: return None
        if checksum and cache_data[2] != checksum:           return None

        try:
            result = FileAccess.loadPICKLE(cache_data[1])
            if result is not None and self.enable_mem_cache and not self._exit: 
                self._setMEM(endpoint, checksum, cache_data[0], result)
            return result
        except Exception as e:
            self.log("_getDB [%s]: Decoding failed: %s" % (endpoint, e))
            return None

    def _getMEM(self, endpoint, checksum, cur_time):
        try: 
            raw_data = self.window.getProperty('%s.%s' % (ADDON_ID, endpoint))
            if not raw_data: return None
            
            cache_data = FileAccess._decodeString(raw_data)
            if (cache_data[0] < 0 or cache_data[0] > cur_time) and (not checksum or cache_data[2] == checksum): 
                return cache_data[1]
        except Exception: 
            pass
        return None

    def _setMEM(self, endpoint, checksum, expires, data):
        try:
            encoded_data = FileAccess._encodeString((expires, data, checksum))
            item_size = sys.getsizeof(encoded_data)
            if item_size > self.max_bytes: return
            with self._lock:
                self.window.setProperty('%s.%s' % (ADDON_ID, endpoint), str(encoded_data))
                self._cache_idx.append((endpoint, item_size))
        except Exception as e:
            self.log("_setMEM failed: %s" % e)

    def _chkClean(self):
        cur_time = self.getTimestamp(datetime.datetime.now())
        try:
            lastexec = self.window.getProperty("%s.CACHE.LastExecuted" % (ADDON_ID))
            lastexec = int(lastexec) if lastexec else cur_time
        except Exception:
            lastexec = cur_time
            
        if (lastexec + self.clean_interval) < cur_time: 
            self._cleanDB()
        else:                                                 
            self._trimMEM()
             
    def _trimMEM(self):
        if not self._exit and not self._trim:
            try:
                self._trim = True
                current_total = sum(size for _, size in self._cache_idx)
                while not self.monitor.abortRequested() and current_total > self.max_bytes and self._cache_idx:
                    endpoint, size = self._cache_idx.popleft()
                    self.window.clearProperty('%s.%s' % (ADDON_ID, endpoint))
                    current_total -= size
            except Exception as e: 
                self.log("_trimMEM failed: %s" % e, xbmc.LOGERROR)
            finally: 
                self._trim = False

    def purge(self):
        with self._lock:
            try:
                if self._database is None:
                    self._database = self._open()
                if self._database:
                    self._cache_idx.clear()
                    self._database.execute("DROP TABLE IF EXISTS cache;")
                    self._database.execute("VACUUM;")
                    self._database.commit()
                    self._database.execute("""
                        CREATE TABLE IF NOT EXISTS cache(
                            id TEXT UNIQUE, 
                            expires INTEGER, 
                            data BLOB, 
                            checksum BLOB
                        )""")
                    self._database.commit()
                    return True
            except Exception as e:
                self.log("purge failed: %s" % e, xbmc.LOGERROR)
                return False
            
    def _checkpoint(self):
        with self._lock:
            if self._database and not self._exit and not self._checkpointing:
                try:
                    self._checkpointing = True
                    self._database.commit()
                    self._database.execute("PRAGMA wal_checkpointing(FULL);")
                except Exception as e:
                    self.log("_checkpoint failed: %s" % e, xbmc.LOGERROR)
                finally:
                    self._checkpointing = False 

    def _shutdown(self):
        with self._lock:
            if self._database and not self._exit:
                try:
                    self._exit = True
                    self._database.commit()
                    self._database.execute("PRAGMA wal_checkpointing(TRUNCATE);")
                except Exception as e:
                    self.log("_shutdown SQL commands failed: %s" % e, xbmc.LOGERROR)
                finally:
                    try: self._database.close()
                    except Exception: pass
                    self._database = None
                    self._exit = False

    def getChecksum(self, stringinput):
        if not stringinput and not self.global_checksum: return ADDON_VERSION
        combined = "%s-%s" % (self.global_checksum, stringinput) if self.global_checksum else str(stringinput)
        return zlib.adler32(combined.encode(DEFAULT_ENCODING)) & 0xffffffff
        
    @staticmethod
    def getTimestamp(date_time):
        try:              return int(date_time.timestamp())
        except Exception: return int(time.mktime(date_time.timetuple()))

    @staticmethod
    def getFreeMEM():
        try:
            raw_mem = xbmc.getInfoLabel('System.FreeMemory')
            free = int("".join(c for c in raw_mem if c.isdigit()))
        except Exception: 
            free = 1024 
        pct = int(REAL_SETTINGS.getSetting('Cache_MEM_Limit') or "10")
        return floor(free * (pct / 100)) * 1024 * 1024
        