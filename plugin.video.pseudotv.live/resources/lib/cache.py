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
import sqlite3

from variables   import *
from logger      import log
from fileaccess  import FileAccess, FileLock


class Service(object):
    player  = PLAYER()
    monitor = MONITOR()
    def _shutdown(self, wait=CPU_CYCLE) -> bool:
        return any([Globals._getEXTProperty('%s.pendingShutdown'%(ADDON_ID),False),self.monitor.waitForAbort(wait)])
    def _restart(self) -> bool:
        return Globals._getEXTProperty('%s.pendingRestart'%(ADDON_ID),False)
    def _interrupt(self) -> bool:
        return any([Globals._getEXTProperty('%s.pendingInterrupt'%(ADDON_ID),False),self._shutdown(),self._restart()])
    def _suspend(self) -> bool:
        return any([Globals._getEXTProperty('%s.pendingSuspend'%(ADDON_ID),False)])
    def _sleep(self, wait=CPU_CYCLE):
        while not self.monitor.abortRequested() and wait > 0:
            if any([self.monitor.waitForAbort(CPU_CYCLE),self._interrupt()]): return True
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
            instance.cache.set(cacheName, value, checksum, expiration)
            return value
        return wrapper
    return internal

class Cache(object):
    service = Service()
    monitor = service.monitor

    def __init__(self, mem_cache=False, disable_cache=False):
        self.cache = _Cache(service=self.service)
        self.cache.enable_mem_cache = mem_cache
        self.disable_cache = (disable_cache or REAL_SETTINGS.getSettingBool('Disable_Cache'))
        self.log('__init__, mem_cache = %s, disable_cache = %s' % (mem_cache, disable_cache))


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s [%s]: %s' % (self.__class__.__name__, {True:'MEM',False:'DB'}[self.cache.enable_mem_cache], msg), level)


    def set(self, name, value, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
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


    def clr(self, name):
        self.log('clr, name = %s' % name)
        self.cache.clr(name)


class _Cache(object):
    _lock            = RLock() 
    _exit            = False
    _database        = None
    _cache_idx       = deque()
    global_checksum  = '1.0.0'
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
        self.dbfile    = FileAccess.translatePath(os.path.join(SETTINGS_LOC, 'cache.db'))
        self._auto_clean_interval = int(REAL_SETTINGS.getSetting('Max_Days') or "3") * 86400 
        self._chkClean()


    def __del__(self):
        self._chkClean()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)


    def _open(self):
        #todo add support for mysql
        with self._lock:
            retries = 0
            while not self.monitor.abortRequested() and retries < LOCK_MAX_FILE_TIMEOUT:
                try:
                    conn = sqlite3.connect(self.dbfile, timeout=30, check_same_thread=False)
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
                    

    def _execute_sql(self, query, data=None):
        with self._lock:
            if self._database is None: self._database = self._open()
            if not self._database: return None
            try:
                if isinstance(data, list): result = self._database.executemany(query, data)
                elif data:                 result = self._database.execute(query, data)
                else:                      result = self._database.execute(query)
                self._database.commit()
                return result
            except Exception as e:
                self.log("SQL Error: %s" % str(e), xbmc.LOGERROR)
                return None


    def get(self, endpoint, checksum=""):
        checksum = self.getChecksum(checksum)
        cur_time = self.getTimestamp(datetime.datetime.now())
        with self._lock:
            if self.enable_mem_cache:
                result = self._getMEM(endpoint, checksum, cur_time)
                if result: return result
            return self._getDB(endpoint, checksum, cur_time)


    def set(self, endpoint, data, checksum="", delta_time=-1):
        checksum = self.getChecksum(checksum)
        expires  = delta_time
        if isinstance(delta_time, datetime.timedelta):
            expires = self.getTimestamp(datetime.datetime.now() + delta_time)
        with self._lock:
            if self.enable_mem_cache and not self._exit: self._setMEM(endpoint, checksum, expires, data)
            query = "INSERT OR REPLACE INTO cache(id, expires, data, checksum) VALUES (?, ?, ?, ?)"
            self._execute_sql(query, (endpoint, expires, FileAccess.dumpPICKLE(data), checksum))


    def clr(self, endpoint):
        query = "DELETE FROM cache WHERE id LIKE ?'"
        self._execute_sql(query, (endpoint + '%',))


    def _getDB(self, endpoint, checksum, cur_time):
        query  = "SELECT expires, data, checksum FROM cache WHERE id = ?"
        cursor = self._execute_sql(query, (endpoint,))
        cache_data = cursor.fetchone() if cursor else None
        
        if not cache_data:
            self.log("_getDB [%s]: Not found in DB" % endpoint)
            return None

        if cache_data[0] >= 0 and cache_data[0] <= cur_time:
            self.log("_getDB [%s]: Expired! (%s < %s)" % (endpoint, cache_data[0], cur_time))
            return None

        if checksum and cache_data[2] != checksum:
            self.log("_getDB [%s]: Checksum Mismatch! DB: %s vs Req: %s" % (endpoint, cache_data[2], checksum))
            return None

        try:
            result = FileAccess.loadPICKLE(cache_data[1])
            if result and self.enable_mem_cache and not self._exit: self._setMEM(endpoint, checksum, cache_data[0], result)
            return result
        except Exception as e:
            self.log("_getDB [%s]: Decoding failed: %s" % (endpoint, e))
            return None
        

    def _getMEM(self, endpoint, checksum, cur_time):
        try: 
            cache_data = FileAccess._decodeString(Globals._getEXTProperty('%s.%s'%(ADDON_ID,endpoint)))
            if (cache_data[0] < 0 or cache_data[0] > cur_time) and not checksum or checksum == cache_data[2]: result = cache_data[1]
        except Exception as e: pass
        return None


    def _setMEM(self, endpoint, checksum, expires, data):
        """Thread-safe memory allocation with FIFO eviction."""
        try:
            encoded_data = FileAccess._encodeString((expires, data, checksum))
            item_size = sys.getsizeof(encoded_data)
            if item_size > self.max_bytes: return
            with self._lock:
                Globals._setEXTProperty('%s.%s' % (ADDON_ID, endpoint), encoded_data)
                self._cache_idx.append((endpoint, item_size))
        except Exception as e:
            self.log("_setMEM failed: %s" % e)


    def _chkClean(self):
        cur_time = datetime.datetime.now()
        lastexec = Globals._getEXTProperty("%s.cache.lastexecuted"%(ADDON_ID))
        if not lastexec: Globals._getEXTProperty("%s.cache.lastexecuted"%(ADDON_ID), repr(cur_time))
        elif (eval(lastexecuted) + self._auto_clean_interval) < cur_time: self.clean()
        else: self._trimMEM()
            
            
    def _trimMEM(self):
        if   self._exit or self.monitor.abortRequested(): return
        elif not Globals._getEXTProperty("%s.cache.trimbusy"%(ADDON_ID)):
            """Evicts oldest items until memory usage is under max_bytes."""
            self.log('_trimMEM, max_bytes = %s' % self.max_bytes)
            Globals._setEXTProperty("%s.cache.trimbusy"%(ADDON_ID), "busy")
            current_total = sum(size for _, size in self._cache_idx)
            while self.monitor.abortRequested() and current_total > self.max_bytes and self._cache_idx:
                if self.monitor.waitForAbort(CPU_CYCLE): break
                endpoint, size = self._cache_idx.popleft()
                Globals._clrEXTProperty('%s.%s' % (ADDON_ID, endpoint))
                current_total -= size
                self.log("_trimMEM, %s to free %s bytes" % (endpoint, size))
            Globals._clrEXTProperty("%s.cache.trimbusy"%(ADDON_ID))


    def clean(self):
        if   self._exit or self.monitor.abortRequested(): return
        elif not Globals._getEXTProperty("%s.cache.cleanbusy"%(ADDON_ID)):
            Globals._setEXTProperty("%s.cache.cleanbusy"%(ADDON_ID), "busy")
            self.log("clean, running...")
            
            if self._database:
                # Cleanup expired
                time = datetime.datetime.now()
                cur_time = self.getTimestamp(time)
                for cache_data in self._execute_sql("SELECT id, expires FROM cache").fetchall():
                    if self.service._interrupt(): break
                    else:
                        Globals._clrEXTProperty('%s.%s'%(ADDON_ID,cache_data[0]))
                        if cache_data[1] >= 0 and cache_data[1] < cur_time:
                            self.log("clean, [%s]: Expired! (%s < %s)" % (cache_data[0], cache_data[1], cur_time))
                            self._execute_sql('DELETE FROM cache WHERE id = ?', (cache_data[0],))
                            self.log("clean, [%s] deleted from db"%cache_data[0])
                self._execute_sql("VACUUM")
                
                # Cleanup WAL
                with self._lock:
                    self._database.commit()
                    # Force WAL to merge into the main DB file on close
                    self._database.execute("PRAGMA wal_checkpoint(FULL);")
                    self._database.close()
                    self._database = None
                    self.log("clean, Database closed and WAL checkpointed.")
                    Globals._setEXTProperty("%s.cache.lastexecuted"%(ADDON_ID), repr(time))
            Globals._clrEXTProperty("%s.cache.cleanbusy"%(ADDON_ID))
            self.log("clean, complete!")
            if self.service._shutdown():
                self.shutdown()
            
 
    def shutdown(self):
        with self._lock:
            if self._database and not self._exit:
                self.log("shutdown, started...")
                try:
                    self._exit = True
                    self._database.commit()
                    # FORCE Checkpoint (Merges .db-wal into .db)
                    self._database.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                    self._database.close()
                    self._database = None
                    self.log("shutdown, Database closed and WAL checkpointed.")
                except Exception as e: self.log("shutdown, failed!\n%s"%(e),xbmc.LOGERROR)
                finally: self._exit = False


    @staticmethod
    def getTimestamp(date_time):
        try:              return int(date_time.timestamp())
        except Exception: return int(time.mktime(date_time.timetuple()))


    def getChecksum(self, stringinput):
        if not stringinput and not self.global_checksum: return ADDON_VERSION
        combined = "%s-%s" % (self.global_checksum, stringinput) if self.global_checksum else str(stringinput)
        return zlib.adler32(combined.encode(DEFAULT_ENCODING)) & 0xffffffff