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
    def _shutdown(self, wait=1.0) -> bool:
        return (self.monitor.waitForAbort(wait) | (Globals._getProperty('%s.pendingShutdown'%(ADDON_ID),False)))
    def _interrupt(self) -> bool:
        return (Globals._getProperty('%s.pendingShutdown'%(ADDON_ID),False) | Globals._getProperty('%s.pendingRestart'%(ADDON_ID),False) | Globals._getProperty('%s.pendingInterrupt'%(ADDON_ID),False))
    def _suspend(self, wait=1.0) -> bool:
        return Globals._getProperty('%s.pendingSuspend'%(ADDON_ID),False)
    def _sleep(self, wait=1.0):
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
        self.disable_cache          = (disable_cache or REAL_SETTINGS.getSettingBool('Disable_Cache'))
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
    _cache_idx           = deque()
    _busy_tasks          = []
    enable_mem_cache     = False
    window               = None
    global_checksum      = ADDON_VERSION
    _auto_clean_interval = datetime.timedelta(hours=int((REAL_SETTINGS.getSetting('Max_Days') or "3")))

    def __init__(self, service=None, winID=10000):
        self.max_bytes = _Cache._getFreeMEM()
        self.service   = service
        self.monitor   = service.monitor
        self.window    = xbmcgui.Window(winID)
        self.dbfile    = FileAccess.translatePath(os.path.join(REAL_SETTINGS.getSetting('User_Folder'),'cache.db'))
        self.log('__init__, max_bytes = %s, winID = %s, dbfile = %s' % (self.max_bytes, winID, self.dbfile))
        self.chkCleanup()


    def __del__(self):
        try: self.chkCleanup()
        except Exception: pass


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)


    @staticmethod
    def _getFreeMEM():
        try:              free = int("".join(re.findall(r"\d", BUILTIN.getInfoLabel('FreeMemory','System'))))
        except Exception: free = 1024 #1GB
        return floor(free * (REAL_SETTINGS.getSettingInt('Cache_MEM_Limit') / 100)) * 1024 * 1024
        
        
        
    def chkCleanup(self):
        cur_time     = datetime.datetime.now()
        lastexecuted = Globals._getProperty("%s.cache.lastexecuted"%(ADDON_ID))
        if not lastexecuted: Globals._setProperty("%s.cache.lastexecuted"%(ADDON_ID), repr(cur_time))
        elif (eval(lastexecuted) + self._auto_clean_interval) < cur_time:
            self._cleanUP()


    def get(self, endpoint, checksum=""):
        checksum = self.getChecksum(checksum)
        cur_time = self.getTimestamp(datetime.datetime.now())
        result   = None
        if self.enable_mem_cache: result = self._getMEM(endpoint, checksum, cur_time)
        if result is None:        result = self._getDB(endpoint, checksum, cur_time)
        return result


    def set(self, endpoint, data, checksum="", expiration=datetime.timedelta(days=30)):
        task_name = "set.%s" % endpoint
        self._busy_tasks.append(task_name)
        checksum = self.getChecksum(checksum)
        expires  = self.getTimestamp(datetime.datetime.now() + expiration)
        if self.enable_mem_cache: self._setMEM(endpoint, checksum, expires, data)
        self._setDB(endpoint, checksum, expires, data)
        self._busy_tasks.remove(task_name)


    def clr(self, endpoint, wait=15):
        self._execute_sql('DELETE FROM cache WHERE id LIKE ?', (endpoint + '%',))


    def _getMEM(self, endpoint, checksum, cur_time):
        result = None
        try: 
            cachedata = FileAccess.loadPICKLE(FileAccess._decodeString(Globals._getProperty('%s.%s'%(ADDON_ID,endpoint))))
            if cachedata[0] > cur_time and not checksum or checksum == cachedata[2]: result = cachedata[1]
        except Exception as e: pass
        return result


    def _setMEM(self, endpoint, checksum, expires, data):
        try: 
            string_text = FileAccess._encodeString(FileAccess.dumpPICKLE((expires, data, checksum)))
            string_size = sys.getsizeof(string_text)
            if string_size > self.max_bytes: raise Exception(f"_setMEM, {endpoint} too large for cache limit {self.max_bytes}!")
            else:
                Globals._setProperty('%s.%s'%(ADDON_ID,endpoint), string_text)
                self._cache_idx.append((endpoint, string_size))
                self._trimMEM()
        except Exception as e: self.log("_setMEM, failed! %s"%(e), xbmc.LOGERROR)


    def _getSize(self):
        return sum(size for _, size in self._cache_idx)


    def _trimMEM(self):
        # While current size exceeds limit, remove the oldest (leftmost) items
        while not self.monitor.abortRequested() and self._getSize() > self.max_bytes:
            try:
                endpoint, removed_size = self._cache_idx.popleft().items()
                Globals._clrProperty('%s.%s'%(ADDON_ID,endpoint))
                self.log(f"_trimMEM, {endpoint} removed {removed_size} bytes from memory!")
            except Exception as e: self.log("_trimMEM, failed! %s"%(e), xbmc.LOGERROR)
        self.log(f'_trimMEM, {self._getSize()}/{self.max_bytes} available bytes')


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
                        if self.enable_mem_cache: self._setMEM(endpoint, checksum, cache_data[0], result)
                    except Exception as e: self.log("_getDB, failed! %s"%(e), xbmc.LOGERROR)
        return result


    def _setDB(self, endpoint, checksum, expires, data):
        query = "INSERT OR REPLACE INTO cache( id, expires, data, checksum) VALUES (?, ?, ?, ?)"
        try: self._execute_sql(query, (endpoint, expires, FileAccess.dumpPICKLE(data), checksum))
        except Exception as e: self.log("_setDB, failed! %s"%(e), xbmc.LOGERROR)


    def _cleanUP(self):
        self._busy_tasks.append(__name__)
        cur_time      = datetime.datetime.now()
        cur_timestamp = self.getTimestamp(cur_time)
        self.log("_cleanUP, running _cleanUP...")
        
        if not Globals._getProperty("%s.cache.cleanbusy"%(ADDON_ID)):
            Globals._setProperty("%s.cache.cleanbusy"%(ADDON_ID), "busy")
            query = "SELECT id, expires FROM cache"
            for cache_data in self._execute_sql(query).fetchall():
                if self.service._shutdown(CPU_CYCLE): break
                else:
                    cache_id      = cache_data[0]
                    cache_expires = cache_data[1]
                    Globals._clrProperty('%s.%s'%(ADDON_ID,cache_id))
                    if cache_expires < cur_timestamp:
                        query = 'DELETE FROM cache WHERE id = ?'
                        self._execute_sql(query, (cache_id,))
                        self.log("_cleanUP, delete from db %s" % cache_id)

            self._execute_sql("VACUUM")
            self._busy_tasks.remove(__name__)
            Globals._setProperty("%s.cache.lastexecuted"%(ADDON_ID), repr(cur_time))
            Globals._clrProperty("%s.cache.cleanbusy"%(ADDON_ID))
            self.log("_cleanUP, auto _cleanUP done")


    def _execute_sql(self, query, data=None):
        retries = 0
        result  = None
        if not FileAccess.exists(CACHE_LOC):
            FileAccess.mkdirs(CACHE_LOC)
        try:
            connection = sqlite3.connect(self.dbfile, timeout=30, isolation_level=None)
            connection.execute('SELECT * FROM cache LIMIT 1')
        except Exception as e:
            if FileAccess.exists(self.dbfile):
                FileAccess.delete(self.dbfile)
            try:
                connection = sqlite3.connect(self.dbfile, timeout=30, isolation_level=None)
                connection.execute( """CREATE TABLE IF NOT EXISTS cache(id TEXT UNIQUE, expires INTEGER, data TEXT, checksum INTEGER)""")
            except Exception as e:
                self.log("_execute_sql, Failed! while initializing connection: %s" % str(e), xbmc.LOGWARNING)
                return

        while not self.service.monitor.abortRequested() and not retries == LOCK_MAX_FILE_TIMEOUT:
            if self.service._shutdown(CPU_CYCLE): break
            else:
                try:
                    with FileLock(self.dbfile):
                        if isinstance(data, list): result = connection.executemany(query, data)
                        elif data:                 result = connection.execute(query, data)
                        else:                      result = connection.execute(query)
                        return result
                except sqlite3.OperationalError as e:
                    retries += 1
                    self.log("_execute_sql, retrying DB commit...", xbmc.LOGWARNING)
                    self.service._sleep(LOCK_MAX_FILE_DELAY)
                except Exception:
                    self.log("_execute_sql, connection ERROR ! -- %s" % str(e), xbmc.LOGERROR)
                    break
                    
        if connection:
            connection.close()
            del connection


    @staticmethod
    def getTimestamp(date_time):
        try:
            return int(date_time.timestamp())
        except Exception:
            return int(time.mktime(date_time.timetuple()))


    def getChecksum(self, stringinput):
        # return simple summed-ord checksum; include global checksum if present
        if not stringinput and not self.global_checksum: return 0
        if self.global_checksum: combined = "%s-%s" % (self.global_checksum, stringinput)
        else:                    combined = str(stringinput)
        return sum(map(ord, combined))