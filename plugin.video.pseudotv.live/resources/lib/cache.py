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
from typing      import Any, Callable, Optional

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
    
class MemoryBudget(object):
    """Global, thread-safe byte budget shared by every in-memory cache.

    A single global cap (GLOBAL_CACHE_MEM_MAX, chosen by RAM/SoC) bounds the
    combined memory of all caches. Each cache registers an owner with a
    per-task cap (a fraction of the global). acquire() refuses a stash when it
    would exceed the owner's cap OR the shared global cap, so no combination
    of caches can blow the budget. Caches release() bytes as they evict.
    """
    _instance = None
    _lock = Lock()

    @classmethod
    def instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self.max_bytes = GLOBAL_CACHE_MEM_MAX
        self._l = RLock()
        self._owners = {}

    def register(self, owner: str, cap: int):
        with self._l:
            self._owners[owner] = {'used': 0, 'cap': int(cap)}

    def cap(self, owner: str) -> int:
        with self._l:
            return self._owners.get(owner, {}).get('cap', self.max_bytes)

    def used(self, owner: str = None) -> int:
        with self._l:
            if owner: return self._owners.get(owner, {}).get('used', 0)
            return sum(a['used'] for a in self._owners.values())

    def acquire(self, owner: str, size: int) -> bool:
        """Reserve `size` bytes for `owner`. False if it would exceed the owner's
        per-task cap or the shared global cap (combined across all caches)."""
        if size <= 0: return True
        with self._l:
            acc   = self._owners.get(owner)
            cap   = acc['cap'] if acc else self.max_bytes
            total = sum(a['used'] for a in self._owners.values())
            if acc and acc['used'] + size > cap: return False
            if total + size > self.max_bytes: return False
            if acc: acc['used'] += size
            return True

    def release(self, owner: str, size: int):
        with self._l:
            acc = self._owners.get(owner)
            if acc and size > 0:
                acc['used'] = max(0, acc['used'] - size)

    def reset(self, owner: str = None):
        with self._l:
            if owner:
                acc = self._owners.get(owner)
                if acc: acc['used'] = 0
            else:
                for a in self._owners.values(): a['used'] = 0


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
        if value is None:
            # None == explicit delete: callers use setCacheSetting(key, None)
            # to clear an entry (e.g. consume-and-clear markers). Previously the
            # None write was silently dropped, leaving stale data cached.
            self.cache._clr(name)
        elif not self.disable_cache:
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

    def execute(self, query: str, data: Any = None) -> Any:
        """Run a raw SQL statement against the cache DB (Phase 2 — programmes index).

        Reads flush pending buffered writes first; writes are batched/committed via
        the normal deferred-commit path. Returns the sqlite cursor for SELECTs.
        """
        return self.cache._execute_sql(query, data)

class _Cache(object):
    _checksum_cache  = {}
    global_checksum  = '1.0.0'
    enable_mem_cache = False
    clean_interval   = MAX_GUIDEDAYS * 86400

    def __init__(self, monitor: Any = None, winID: int = 10000):
        self._lock          = RLock() 
        self.monitor        = monitor
        self.window         = xbmcgui.Window(winID)
        self.max_entries    = MAX_CACHE_SIZE
        self.max_mem_bytes  = CACHE_MEM_MAX   # hard byte budget for the mem cache
        self._mem_bytes     = 0               # running total of encoded mem-cache bytes
        self.dbfile         = FileAccess.translatePath(CACHE_FLE)
        self.timeout        = int(REAL_SETTINGS.getSetting('API_Timeout') or "10") * 2
        self._trim          = False
        self._clean         = False
        self._exit          = False
        self._checkpointing = False
        self._database      = None
        self._cache_idx     = deque()
        # Deferred-commit write buffer: accumulate writes and commit in one
        # transaction, cutting SQLite commit amplification on low-power devices.
        self._write_batch   = []   # list of (query, data) pending writes
        self._batch_limit   = 64   # flush when this many writes accumulate
        self._batch_dirty   = False

    def __del__(self):
        try: self._chkClean()
        except AttributeError: pass
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s' % (self.__class__.__name__, msg), level)

    def _open(self) -> Optional[sqlite3.Connection]:
        """Open or connect to the SQLite database, creating the cache table if needed.

        Uses a short connect timeout so a contended DB can't block addon threads
        for minutes (API_Timeout is user-facing and can be 90s+).
        """
        with self._lock:
            retries = 0
            # Cap the SQLite lock wait — the user-facing API_Timeout can be huge,
            # and a long-held DB lock would freeze every cache consumer.
            db_timeout = min(self.timeout, 5)
            while not self.monitor.abortRequested() and retries < LOCK_MAX_FILE_TIMEOUT:
                try:
                    self.log('_open, connecting to %s (timeout=%ds, attempt=%d)' % (self.dbfile, db_timeout, retries + 1), xbmc.LOGINFO)
                    conn = sqlite3.connect(self.dbfile, timeout=db_timeout, check_same_thread=False)
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA synchronous=NORMAL;")
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS cache(
                            id TEXT UNIQUE, 
                            expires INTEGER, 
                            data BLOB, 
                            checksum BLOB
                        )""")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires)")
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
        """Execute a SQL query with optional data, handling executemany for lists of tuples.

        Writes are buffered into _write_batch and committed in one transaction via
        _flush_batch — avoids a SQLite commit per cache.set (O(n²) on large builds).
        Reads flush pending writes first so buffered data is visible.
        """
        with self._lock:
            if self._exit:
                return None
            if self._checkpointing:
                # WAL checkpoint in progress — skip this query rather than
                # recurse (which blew the stack when checkpointing stalled).
                return None
            if self._database is None:
                self._database = self._open()
                
            if self._database:
                is_write = not query.lstrip().upper().startswith('SELECT')
                if is_write:
                    # Buffer the write; commit only when the batch fills or on flush.
                    self._write_batch.append((query, data))
                    self._batch_dirty = True
                    if len(self._write_batch) >= self._batch_limit:
                        self._flush_batch()
                    return None
                self._flush_batch()  # reads must see pending writes
                try:
                    if isinstance(data, list):  
                        return self._database.executemany(query, data)
                    elif data:                  
                        return self._database.execute(query, data)
                    else:                       
                        return self._database.execute(query)
                except Exception as e:
                    self.log(f"SQL Error during [{query[:48]}]: {e}", xbmc.LOGERROR)
                    return None

    def _flush_batch(self):
        """Commit all buffered writes in a single SQLite transaction.

        The batch is snapshotted under the lock, then committed WITHOUT holding
        self._lock — a blocking SQLite commit must never freeze other threads
        that need the cache (build queue, HTTP serving, chkQUES).
        """
        with self._lock:
            if self._exit or not self._batch_dirty or not self._write_batch:
                return
            batch = self._write_batch
            self._write_batch = []
            self._batch_dirty = False
        # Commit outside the lock.
        with self._lock:
            if self._database is None:
                self._database = self._open()
        if not self._database:
            # DB unavailable — re-buffer so writes aren't lost silently.
            with self._lock:
                self._write_batch = batch + self._write_batch
                self._batch_dirty = True
            return
        try:
            self._database.execute('BEGIN')
            for query, data in batch:
                if isinstance(data, list):
                    self._database.executemany(query, data)
                elif data:
                    self._database.execute(query, data)
                else:
                    self._database.execute(query)
            self._database.commit()
        except Exception as e:
            self.log(f"_flush_batch, SQL batch failed: {e}", xbmc.LOGERROR)
            try: self._database.rollback()
            except Exception: pass
            # Re-buffer on failure so a transient lock doesn't lose writes.
            with self._lock:
                self._write_batch = batch + self._write_batch
                self._batch_dirty = True

    def _get(self, endpoint: str, checksum: Any = "") -> Optional[Any]:
        """Retrieve a cached value by endpoint, checking memory cache first if enabled."""
        checksum = self.getChecksum(checksum)
        cur_time = self.getTimestamp(datetime.datetime.now())
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
        if self.enable_mem_cache and not self._exit: 
            self._setMEM(endpoint, checksum, expires, data)
        query = "INSERT OR REPLACE INTO cache(id, expires, data, checksum) VALUES (?, ?, ?, ?)"
        self._execute_sql(query, (endpoint, expires, FileAccess.dumpPICKLE(data), checksum))

    def _clr(self, endpoint: str):
        """Delete all cache entries matching the endpoint prefix (DB + mem)."""
        query = "DELETE FROM cache WHERE id LIKE ?"
        self._execute_sql(query, (endpoint + '%',))
        if self.enable_mem_cache and not self._exit:
            # Purge matching in-memory entries too — a DB-only delete leaves a
            # stale window-property hit that _get would still return.
            budget = MemoryBudget.instance()
            budget.register('memcache', self.max_mem_bytes)
            with self._lock:
                remaining = deque()
                for ep, size in self._cache_idx:
                    if ep.startswith(endpoint):
                        self._mem_bytes = max(0, self._mem_bytes - size)
                        budget.release('memcache', size)
                        self.window.clearProperty('%s.%s' % (ADDON_ID, ep))
                    else:
                        remaining.append((ep, size))
                self._cache_idx = remaining

    def _getDB(self, endpoint: str, checksum: Any, cur_time: int) -> Optional[Any]:
        """Fetch a value from the database cache, checking expiration and checksum validity."""
        query  = "SELECT expires, data, checksum FROM cache WHERE id = ?"
        cursor = self._execute_sql(query, (endpoint,))
        cache_data = cursor.fetchone() if cursor else None
        
        if not cache_data:                                   return None
        expires = cache_data[0] if cache_data[0] is not None else -1
        if expires >= 0 and expires <= cur_time:             return None
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
        """Store a value in the in-memory window property cache.

        Enforces this cache's own byte cap (max_mem_bytes) plus the shared
        global MemoryBudget: trims the oldest entries to make room, and refuses
        a stash that would exceed either cap or a single value larger than the
        whole budget.
        """
        try:
            budget = MemoryBudget.instance()
            budget.register('memcache', self.max_mem_bytes)
            encoded_data = FileAccess._encodeString((expires, data, checksum))
            item_size    = sys.getsizeof(encoded_data)
            if item_size > self.max_mem_bytes: return  # never cache one oversized value
            with self._lock:
                self._trimMEM()  # free room if at the count, per-cache or global cap
                if len(self._cache_idx) >= self.max_entries: return
                if self._mem_bytes + item_size > self.max_mem_bytes: return
                if not budget.acquire('memcache', item_size): return  # global budget exhausted
                self.window.setProperty('%s.%s' % (ADDON_ID, endpoint), encoded_data)
                self._cache_idx.append((endpoint, item_size))
                self._mem_bytes += item_size
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

    def _cleanDB(self):
        """Purge expired cache rows so the DB never grows unboundedly.

        Historically called (and referenced by _chkClean) but never implemented —
        expired rows (esp. the multi-MB movie/tvshow library dumps) accumulated
        forever, bloating cache.db to 300+MB on low-RAM SOCs.
        """
        with self._lock:
            try:
                self._flush_batch()
                if self._database is None:
                    self._database = self._open()
                if self._database:
                    cur_time = self.getTimestamp(datetime.datetime.now())
                    cur = self._database.execute("DELETE FROM cache WHERE expires >= 0 AND expires < ?", (cur_time,))
                    deleted = cur.rowcount
                    self._database.commit()
                    if deleted:
                        self.log('_cleanDB, purged %d expired entries' % deleted, xbmc.LOGINFO)
            except Exception as e:
                self.log("_cleanDB failed: %s" % e, xbmc.LOGERROR)
             
    def _trimMEM(self):
        """Evict oldest in-memory cache entries until the count, this cache's byte
        budget and the shared global MemoryBudget all fit."""
        if not self._exit and not self._trim:
            try:
                self._trim = True
                budget = MemoryBudget.instance()
                budget.register('memcache', self.max_mem_bytes)
                initial_count = len(self._cache_idx)
                while not self.monitor.abortRequested() and self._cache_idx and \
                      (len(self._cache_idx) > self.max_entries or
                       self._mem_bytes > self.max_mem_bytes or
                       budget.used() > budget.max_bytes):
                    endpoint, size = self._cache_idx.popleft()
                    self._mem_bytes = max(0, self._mem_bytes - size)
                    budget.release('memcache', size)
                    self.window.clearProperty('%s.%s' % (ADDON_ID, endpoint))
                trimmed = initial_count - len(self._cache_idx)
                if trimmed: self.log('_trimMEM, evicted %d entries (%d -> %d, max=%d, %.1fMB own / %.1fMB global)' % (trimmed, initial_count, len(self._cache_idx), self.max_entries, budget.used('memcache')/1048576.0, budget.used()/1048576.0), xbmc.LOGDEBUG)
            except Exception as e: 
                self.log("_trimMEM failed: %s" % e, xbmc.LOGERROR)
            finally: 
                self._trim = False

    def purge(self) -> bool:
        """Drop and recreate the cache table, clearing all persisted data."""
        with self._lock:
            try:
                self._write_batch = []   # purge wipes everything — drop buffered writes
                self._batch_dirty = False
                if self._database is None:
                    self._database = self._open()
                if self._database:
                    self._cache_idx.clear()
                    self._mem_bytes = 0
                    MemoryBudget.instance().reset('memcache')
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
                    self._database.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires)")
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
                    self._flush_batch()
                    self._database.execute("PRAGMA wal_checkpointing(FULL);")
                    self._chkClean()
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
                    self._flush_batch()          # write buffered entries before exit
                    self._exit = True
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
        cache_key = (self.global_checksum, stringinput)
        cached = _Cache._checksum_cache.get(cache_key)
        if cached is not None: return cached
        combined = "%s-%s" % (self.global_checksum, stringinput) if self.global_checksum else str(stringinput)
        result = zlib.adler32(combined.encode(DEFAULT_ENCODING)) & 0xffffffff
        _Cache._checksum_cache[cache_key] = result
        if len(_Cache._checksum_cache) > CHECKSUM_CACHE_MAX:  # bound unbounded growth
            _Cache._checksum_cache.clear()
        return result
        
    @staticmethod
    def getTimestamp(date_time: datetime.datetime) -> int:
        """Convert a datetime object to a Unix timestamp integer."""
        try:              return int(date_time.timestamp())
        except Exception: return int(time.mktime(date_time.timetuple()))
