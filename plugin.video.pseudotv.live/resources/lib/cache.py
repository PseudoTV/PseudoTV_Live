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
from typing import Any, Callable, Optional
from variables   import *
from fileaccess  import FileAccess

def cacheit(expiration: datetime.timedelta = datetime.timedelta(minutes=15), checksum: Any = None) -> Callable:
    """Decorator that caches function results in the instance's cache, keyed by arguments."""
    def internal(method: Callable) -> Callable:
        @wraps(method)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal checksum
            instance = args[0]
            if checksum is None: checksum = ADDON_VERSION
            cache_checksum = checksum() if callable(checksum) else checksum
            cache_checksum = instance.cache.getChecksum(cache_checksum)
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
                LOG(f'{method.__qualname__.replace(".", ": ")}, cacheit returning cache', xbmc.LOGDEBUG)
                return results
                
            LOG(f'{method.__qualname__.replace(".", ": ")}, cacheit saving results', xbmc.LOGDEBUG)
            value = method(*args, **kwargs)
            instance.cache.set(cacheName, value, cache_checksum, expiration)
            return value
        return wrapper
    return internal
    
class Cache(object):
    def __init__(self, mem_cache: bool = False, disable_cache: bool = False):
        self.monitor = MONITOR()
        self.cache   = _Cache(monitor=self.monitor)
        self.cache.enable_mem_cache = mem_cache
        self.disable_cache = (disable_cache or REAL_SETTINGS.getSetting('Disable_Cache') == 'true')
        self.log('__init__, mem_cache=%s, disable_cache=%s, db=%s' % (mem_cache, self.disable_cache, self.cache.dbfile), xbmc.LOGINFO)

    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s [%s]: %s' % (self.__class__.__name__, {True:'MEM|DB',False:'DB'}[self.cache.enable_mem_cache], msg), level)

    def set(self, name: str, value: Any, checksum: Any = None, expiration: datetime.timedelta = datetime.timedelta(minutes=15)) -> Any:
        if checksum is None: checksum = ADDON_VERSION
        if not any((self.disable_cache,value is None)):
            self.cache._set(name, value, checksum, expiration)
            self.log('set [%s], type=%s, expires=%s, value=%.64s' % (name, type(value).__name__, expiration, str(value)))
        return value

    def get(self, name: str, checksum: Any = None) -> Optional[Any]:
        if checksum is None: checksum = ADDON_VERSION
        if not self.disable_cache:
            try:
                value = self.cache._get(name, checksum)
                self.log('get [%s], type=%s, hit=%s' % (name, type(value).__name__ if value is not None else 'None', value is not None))
                return value
            except Exception as e:
                self.log("get [%s] failed: %s" % (name, e), xbmc.LOGERROR)
                self.cache._clr(name)

    def clear(self, name: str):
        self.log('clr, name = %s' % name)
        self.cache._clr(name)

    def checkpoint(self):
        self.cache._checkpoint()
        
    def shutdown(self):
        self.cache._shutdown()

    def getChecksum(self, stringinput: Any) -> int:
        return self.cache.getChecksum(stringinput)

class _Cache(object):
    _lock            = RLock() 
    global_checksum  = '1.0.0'
    enable_mem_cache = False
    clean_interval   = MAX_GUIDEDAYS * 86400

    def __init__(self, monitor: Any = None, winID: int = 10000):
        self.monitor        = monitor
        self.window         = xbmcgui.Window(winID)
        self.max_entries    = MAX_CACHE_SIZE
        self.dbfile         = FileAccess.translatePath(CACHE_FLE)
        self.timeout        = int(REAL_SETTINGS.getSetting('API_Timeout') or "10") * 2
        self._trim          = False
        self._clean         = False
        self._exit          = False
        self._checkpointing = False
        self._database      = None
        self._cache_idx     = deque()

    def __del__(self):
        try: self._chkClean()
        except AttributeError: pass
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s' % (self.__class__.__name__, msg), level)

    def _open(self) -> Optional[sqlite3.Connection]:
        """Open or connect to the SQLite database, creating the cache table if needed."""
        with self._lock:
            retries = 0
            while not self.monitor.abortRequested() and retries < LOCK_MAX_FILE_TIMEOUT:
                try:
                    self.log('_open, connecting to %s (timeout=%ds, attempt=%d)' % (self.dbfile, self.timeout, retries + 1), xbmc.LOGINFO)
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
                    self.log('_open, connected successfully', xbmc.LOGINFO)
                    return conn
                except sqlite3.OperationalError:
                    self.log('_open, database locked, retrying in 1s (attempt %d/%d)' % (retries + 1, LOCK_MAX_FILE_TIMEOUT), xbmc.LOGDEBUG)
                    if self.monitor.waitForAbort(1.0): break
                    retries += 1
                except Exception as e: 
                    self.log("_open failed: %s" % str(e), xbmc.LOGERROR)
                    break
            return None
                    
    def _execute_sql(self, query: str, data: Any = None) -> Optional[sqlite3.Cursor]:
        """Execute a SQL query with optional data, handling executemany for lists of tuples."""
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

    def _get(self, endpoint: str, checksum: Any = "") -> Optional[Any]:
        """Retrieve a cached value by endpoint, checking memory cache first if enabled."""
        checksum = self.getChecksum(checksum)
        cur_time = self.getTimestamp(datetime.datetime.now())
        with self._lock:
            if self.enable_mem_cache:
                result = self._getMEM(endpoint, checksum, cur_time)
                if result is not None: return result
            return self._getDB(endpoint, checksum, cur_time)

    def _set(self, endpoint: str, data: Any, checksum: Any = "", delta_time: Any = -1):
        """Store data in cache, writing to both memory and database if enabled."""
        checksum = self.getChecksum(checksum)
        expires  = delta_time
        if isinstance(delta_time, datetime.timedelta):
            expires = self.getTimestamp(datetime.datetime.now() + delta_time)
        with self._lock:
            if self.enable_mem_cache and not self._exit: 
                self._setMEM(endpoint, checksum, expires, data)
            query = "INSERT OR REPLACE INTO cache(id, expires, data, checksum) VALUES (?, ?, ?, ?)"
            self._execute_sql(query, (endpoint, expires, FileAccess.dumpPICKLE(data), checksum))

    def _clr(self, endpoint: str):
        """Delete all cache entries matching the endpoint prefix."""
        query = "DELETE FROM cache WHERE id LIKE ?"
        self._execute_sql(query, (endpoint + '%',))

    def _getDB(self, endpoint: str, checksum: Any, cur_time: int) -> Optional[Any]:
        """Fetch a value from the database cache, checking expiration and checksum validity."""
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

    def _getMEM(self, endpoint: str, checksum: Any, cur_time: int) -> Optional[Any]:
        """Retrieve a value from the in-memory window property cache."""
        try: 
            raw_data = self.window.getProperty('%s.%s' % (ADDON_ID, endpoint))
            if not raw_data: return None
            
            cache_data = FileAccess._decodeString(raw_data)
            if (cache_data[0] < 0 or cache_data[0] > cur_time) and (not checksum or cache_data[2] == checksum): 
                return cache_data[1]
        except Exception as e:
            self.log("_getMEM [%s]: %s" % (endpoint, e), xbmc.LOGDEBUG)
        return None

    def _setMEM(self, endpoint: str, checksum: Any, expires: int, data: Any):
        """Store a value in the in-memory window property cache, evicting if entry count limit exceeded."""
        try:
            if len(self._cache_idx) >= self.max_entries: return
            encoded_data = FileAccess._encodeString((expires, data, checksum))
            item_size = sys.getsizeof(encoded_data)
            with self._lock:
                self.window.setProperty('%s.%s' % (ADDON_ID, endpoint), str(encoded_data))
                self._cache_idx.append((endpoint, item_size))
        except Exception as e:
            self.log("_setMEM failed: %s" % e)

    def _chkClean(self):
        """Check if the cache needs periodic cleanup based on last execution time."""
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
        """Evict oldest in-memory cache entries until entry count fits within max_entries."""
        if not self._exit and not self._trim:
            try:
                self._trim = True
                initial_count = len(self._cache_idx)
                while not self.monitor.abortRequested() and len(self._cache_idx) > self.max_entries:
                    endpoint, size = self._cache_idx.popleft()
                    self.window.clearProperty('%s.%s' % (ADDON_ID, endpoint))
                trimmed = initial_count - len(self._cache_idx)
                if trimmed: self.log('_trimMEM, evicted %d entries (count: %d -> %d, max=%d)' % (trimmed, initial_count, len(self._cache_idx), self.max_entries), xbmc.LOGDEBUG)
            except Exception as e: 
                self.log("_trimMEM failed: %s" % e, xbmc.LOGERROR)
            finally: 
                self._trim = False

    def purge(self) -> bool:
        """Drop and recreate the cache table, clearing all persisted data."""
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
        """Force a WAL checkpoint to flush the write-ahead log to the main database file."""
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
        """Commit pending changes, checkpoint WAL, and close the database connection."""
        with self._lock:
            if self._database and not self._exit:
                try:
                    self.log('_shutdown, committing and closing database', xbmc.LOGINFO)
                    self._exit = True
                    self._database.commit()
                    self._database.execute("PRAGMA wal_checkpointing(TRUNCATE);")
                except Exception as e:
                    self.log("_shutdown SQL commands failed: %s" % e, xbmc.LOGERROR)
                finally:
                    try: self._database.close()
                    except Exception as e: self.log("_shutdown close failed: %s" % e, xbmc.LOGDEBUG)
                    self._database = None
                    self.log('_shutdown, database closed', xbmc.LOGINFO)

    def getChecksum(self, stringinput: Any) -> int:
        """Generate an Adler32 checksum from the global checksum combined with the input string."""
        if not stringinput and not self.global_checksum: return ADDON_VERSION
        combined = "%s-%s" % (self.global_checksum, stringinput) if self.global_checksum else str(stringinput)
        return zlib.adler32(combined.encode(DEFAULT_ENCODING)) & 0xffffffff
        
    @staticmethod
    def getTimestamp(date_time: datetime.datetime) -> int:
        """Convert a datetime object to a Unix timestamp integer."""
        try:              return int(date_time.timestamp())
        except Exception: return int(time.mktime(date_time.timetuple()))
