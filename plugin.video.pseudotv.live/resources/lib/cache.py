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
import json
import ast
import time
import os
import threading
import collections

from contextlib  import contextmanager
from functools   import wraps, lru_cache
from globals     import *
from fileaccess  import FileAccess, FileLock
from kodi_six    import xbmc, xbmcgui

# Tunables for memory usage
MEM_CACHE_MAX_ENTRIES = 128            # number of entries kept in the in-process mem cache
MEM_CACHE_MAX_BYTES   = 256 * 1024     # don't mem-cache values larger than this (approx bytes of repr/json)
MEM_CACHE_KEY_TRIM    = 128            # truncate components when building cache keys to avoid huge keys

def _getProperty(key):
    return xbmcgui.Window(10000).getProperty('%s.%s' % (ADDON_ID, key))

def _setProperty(key, value):
    xbmcgui.Window(10000).setProperty('%s.%s' % (ADDON_ID, key), value)
    return value

def _clrProperty(key):
    return xbmcgui.Window(10000).clearProperty('%s.%s' % (ADDON_ID, key))

class Service(object):
    monitor = MONITOR()
    def _shutdown(self, wait=1.0) -> bool:
        pendingShutdown = _getProperty('%s.pendingShutdown'%(ADDON_ID)) == "true"
        return (self.monitor.waitForAbort(wait) | pendingShutdown)
    def _interrupt(self) -> bool:
        pendingShutdown   = _getProperty('%s.pendingShutdown'%(ADDON_ID)) == "true"
        pendingInterrupt  = _getProperty('%s.pendingInterrupt'%(ADDON_ID)) == "true"
        pendingRestart    = _getProperty('%s.pendingRestart'%(ADDON_ID)) == "true"
        interruptActivity = _getProperty('%s.interruptActivity'%(ADDON_ID)) == "true"
        return (pendingShutdown | pendingRestart | pendingInterrupt | interruptActivity)
    def _suspend(self, wait=1.0) -> bool:
        pendingSuspend = _getProperty('%s.pendingSuspend'%(ADDON_ID)) == "true"
        return pendingSuspend
    def _sleep(self, wait=1.0):
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) | self._interrupt()): return True
            else: wait -= CPU_CYCLE
        return False

def _safe_component_str(x):
    s = repr(x)
    if len(s) > MEM_CACHE_KEY_TRIM:
        return s[:MEM_CACHE_KEY_TRIM]
    return s

def cacheit(expiration=datetime.timedelta(minutes=15), checksum=ADDON_VERSION, json_data=False):
    def internal(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            # Build safe, truncated key to avoid huge key strings (which can blow memory)
            instance = args[0]
            cacheName = "%s.%s" % (instance.__class__.__name__, method.__name__)
            for item in args[1:]:
                cacheName += u".%s" % _safe_component_str(item)
            for k, v in list(kwargs.items()):
                cacheName += u".%s=%s" % (k, _safe_component_str(v))
            results = instance.cache.get(cacheName, checksum, json_data)
            if results is not None:
                log('%s, cacheit returning cache' % (method.__qualname__.replace('.', ': ')))
                return results
            log('%s, cacheit saving results' % (method.__qualname__.replace('.', ': ')))
            value = method(*args, **kwargs)
            instance.cache.set(cacheName, value, checksum, expiration, json_data)
            return value
        return wrapper
    return internal


class Cache(object):
    service = Service()
    monitor = service.monitor
    cache_lock = threading.Lock()

    def __init__(self, mem_cache=False, is_json=False, disable_cache=False):
        self.cache = _Cache(service=self.service)
        self.cache.enable_mem_cache = mem_cache
        self.cache.data_is_json     = is_json
        # disable_cache is True if explicitly passed OR addon settings say so
        self.disable_cache          = (disable_cache or REAL_SETTINGS.getSettingBool('Disable_Cache'))
        self.log('__init__, mem_cache = %s, is_json = %s, disable_cache = %s' % (mem_cache, is_json, disable_cache))


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s [%s]: %s' % (self.__class__.__name__, {True:'MEM',False:'DB'}[self.cache.enable_mem_cache], msg), level)


    def set(self, name, value, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15), json_data=False):
        # don't store empty values when cache disabled unless explicitly allowed
        if not self.disable_cache or (not isinstance(value,(bool,list,dict)) and not value):
            with self.cache_lock:
                self.log('set, name = %s, value = %s' % (name, '%s...'%(str(value)[:128])))
                self.cache.set(name, value, checksum, expiration, json_data)
        return value


    def get(self, name, checksum=ADDON_VERSION, json_data=False):
        if not self.disable_cache:
            with self.cache_lock:
                try:
                    value = self.cache.get(name, checksum, json_data)
                    self.log('get, name = %s, value = %s' % (name, '%s...'%(str(value)[:128])))
                    return value
                except Exception as e:
                    self.log("get, name = %s failed! %s" % (name, e), xbmc.LOGERROR)
                    self.cache.clr(name)


    def clear(self, name, wait=15):
        with self.cache_lock:
            self.log('clear, name = %s' % name)
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
        self.monitor = service.monitor
        self.window  = xbmcgui.Window(winID)
        self.dbfile  = FileAccess.translatePath(CACHEFLEPATH)

        # mem store: OrderedDict to keep insertion order for pruning
        self._mem_store = collections.OrderedDict()
        self._mem_lock  = threading.Lock()

        # lru-backed lookup function. keys are tuples (endpoint, checksum)
        @lru_cache(maxsize=MEM_CACHE_MAX_ENTRIES)
        def _mem_lookup(key_tuple):
            # Return the stored tuple (expires, data) or None
            return self._mem_store.get(key_tuple)
        self._mem_lookup = _mem_lookup
        self._ensure_db_initialized()
        self.chkCleanup()


    def __del__(self):
        del self.window


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)


    def chkCleanup(self):
        cur_time     = datetime.datetime.now()
        lastexecuted = _getProperty("cache.lastexecuted")
        if not lastexecuted:
            _setProperty("cache.lastexecuted", repr(cur_time))
        else:
            try:
                last_time = eval(lastexecuted)
                if (last_time + self._auto_clean_interval) < cur_time:
                    self._cleanUp()
            except Exception:
                # if corrupted, reset marker
                _setProperty("cache.lastexecuted", repr(cur_time))


    def get(self, endpoint, checksum="", json_data=False):
        checksum = self.getChecksum(checksum)
        cur_time = int(time.time())
        result   = None
        if self.enable_mem_cache:
            result = self._get_mem_cache(endpoint, checksum, cur_time, json_data)
        if result is None:
            result = self._get_db_cache(endpoint, checksum, cur_time, json_data)
        return result


    def set(self, endpoint, data, checksum="", expiration=datetime.timedelta(days=30), json_data=False):
        task_name = "set.%s" % endpoint
        self._busy_tasks.append(task_name)
        checksum = self.getChecksum(checksum)
        expires  = int((datetime.datetime.now() + expiration).timestamp())
        if self.enable_mem_cache:
            self._set_mem_cache(endpoint, checksum, expires, data, json_data)
        self._set_db_cache(endpoint, checksum, expires, data, json_data)
        try:
            self._busy_tasks.remove(task_name)
        except ValueError:
            pass


    def clr(self, endpoint, wait=15):
        # remove DB entries matching endpoint prefix
        like_pattern = endpoint + '%'
        try:
            self._execute_sql('DELETE FROM cache WHERE id LIKE ?', (like_pattern,))
        except Exception as e:
            self.log('clr, failed! %s' % e, xbmc.LOGERROR)
        # remove mem store entries and clear lru cache
        with self._mem_lock:
            keys_to_remove = [k for k in self._mem_store.keys() if k[0].startswith(endpoint)]
            for k in keys_to_remove:
                try:
                    del self._mem_store[k]
                except KeyError:
                    pass
            try:
                # clear the lru cache so it won't return stale values
                self._mem_lookup.cache_clear()
            except Exception:
                pass


    def _get_mem_cache(self, endpoint, checksum, cur_time, json_data):
        key = (endpoint, checksum)
        with self._mem_lock:
            try:
                entry = self._mem_lookup(key)
            except Exception:
                entry = None
            if not entry:
                return None
            expires, data = entry
            if expires > cur_time:
                return data
            else:
                # expired; remove
                try:
                    del self._mem_store[key]
                except KeyError:
                    pass
                try:
                    self._mem_lookup.cache_clear()
                except Exception:
                    pass
                return None


    def _set_mem_cache(self, endpoint, checksum, expires, data, json_data):
        try:    data_repr = json.dumps(data) if (json_data or self.data_is_json) else repr(data)
        except: data_repr = repr(data)
        if len(data_repr) > MEM_CACHE_MAX_BYTES: return
        key = (endpoint, checksum)
        with self._mem_lock:
            # insert/update source store
            self._mem_store[key] = (expires, data)
            # maintain insertion-order size bound on _mem_store to avoid unbounded growth
            while not self.monitor.abortRequested() and len(self._mem_store) > (2 * MEM_CACHE_MAX_ENTRIES):
                try: self._mem_store.popitem(last=False)
                except Exception: break
            # populate the lru cache by calling the decorated lookup
            try: self._mem_lookup(key)
            except Exception: pass


    def _get_db_cache(self, endpoint, checksum, cur_time, json_data):
        result = None
        query = "SELECT expires, data, checksum FROM cache WHERE id = ?"
        rows = self._execute_sql(query, (endpoint,))
        if rows:
            cache_data = rows[0]
            try: cache_expires = int(cache_data[0])
            except Exception: return None
            if cache_expires > cur_time:
                stored_checksum = cache_data[2]
                if not checksum or stored_checksum == checksum:
                    raw = cache_data[1]
                    try:
                        if json_data or self.data_is_json:
                            result = json.loads(raw)
                        else:
                            result = ast.literal_eval(raw)
                    except Exception:
                        try: 
                            result = json.loads(raw)
                        except Exception:
                            try:              result = ast.literal_eval(raw)
                            except Exception: result = None
                    if result is not None and self.enable_mem_cache:
                        # store parsed object in mem cache
                        self._set_mem_cache(endpoint, stored_checksum, cache_expires, result, json_data)
        return result


    def _set_db_cache(self, endpoint, checksum, expires, data, json_data):
        query = "INSERT OR REPLACE INTO cache( id, expires, data, checksum) VALUES (?, ?, ?, ?)"
        try:
            if json_data or self.data_is_json:
                data_blob = json.dumps(data)
            else:
                data_blob = repr(data)
        except Exception:
            # Fallback to repr if JSON serialization fails
            data_blob = repr(data)
        self._execute_sql(query, (endpoint, int(expires), data_blob, checksum))


    def _cleanUp(self):
        self._busy_tasks.append(__name__)
        cur_timestamp = int(time.time())
        self.log("_cleanUp, running _cleanUp...")

        if _getProperty("cache.cleanbusy"):
            try:
                self._busy_tasks.remove(__name__)
            except ValueError:
                pass
            return
        else:
            _setProperty("cache.cleanbusy", "busy")
            query = "SELECT id, expires FROM cache"
            rows = self._execute_sql(query)
            if rows:
                for cache_data in rows:
                    if self.service._shutdown(CPU_CYCLE):
                        _clrProperty("cache.cleanbusy")
                        try:
                            self._busy_tasks.remove(__name__)
                        except ValueError:
                            pass
                        return
                    cache_id      = cache_data[0]
                    try:
                        cache_expires = int(cache_data[1])
                    except Exception:
                        cache_expires = 0
                    # clear any window property used previously
                    try:
                        _clrProperty(cache_id)
                    except Exception:
                        pass
                    if cache_expires < cur_timestamp:
                        self._execute_sql('DELETE FROM cache WHERE id = ?', (cache_id,))
                        self.log("_cleanUp, delete from db %s" % cache_id)

            # VACUUM to reclaim space (may be costly; keep it but wrapped)
            try:
                self._execute_sql("VACUUM")
            except Exception:
                pass

            try:
                self._busy_tasks.remove(__name__)
            except ValueError:
                pass
            _setProperty("cache.lastexecuted", repr(datetime.datetime.now()))
            _clrProperty("cache.cleanbusy")
            self.log("_cleanUp, auto _cleanUp done")


    def _ensure_db_initialized(self):
        # Ensure DB and table exist. Keep it simple and idempotent.
        if not FileAccess.exists(USER_LOC):
            try: FileAccess.mkdirs(USER_LOC)
            except Exception: pass
        try:
            # Use connection context; create table if missing
            conn = sqlite3.connect(self.dbfile, timeout=30)
            try:
                conn.execute("""CREATE TABLE IF NOT EXISTS cache(
                                    id TEXT UNIQUE,
                                    expires INTEGER,
                                    data TEXT,
                                    checksum INTEGER
                                )""")
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            self.log("_ensure_db_initialized Failed: %s" % e, xbmc.LOGWARNING)


    def _execute_sql(self, query, data=None):
        """
        Execute a query with retries on locked DB. For SELECT queries, returns a list of rows.
        For non-SELECT queries, performs commit and returns None.
        """
        retries = 0
        max_retries = LOCK_MAX_FILE_TIMEOUT if isinstance(LOCK_MAX_FILE_TIMEOUT, int) else 5

        # ensure DB path exists
        while not self.monitor.abortRequested() and retries <= max_retries:
            if self.service._shutdown(CPU_CYCLE):
                break
            conn = None
            try:
                conn = sqlite3.connect(self.dbfile, timeout=30)
                cur = conn.cursor()
                if data is not None:
                    if isinstance(data, list):
                        cur.executemany(query, data)
                    else:
                        cur.execute(query, data)
                else:
                    cur.execute(query)
                qtype = query.strip().split()[0].upper() if query.strip() else ""
                if qtype == 'SELECT':
                    rows = cur.fetchall()
                    return rows
                else:
                    conn.commit()
                    return None
            except Exception as e:
                estr = str(e)
                if 'database is locked' in estr or 'database table is locked' in estr or 'database busy' in estr:
                    self.log("_execute_sql, retrying DB operation... (%s)" % estr)
                    retries += 1
                    # sleep a bit (use monitor sleep to allow aborts)
                    self.service._sleep(LOCK_MAX_FILE_DELAY)
                    continue
                else:
                    self.log("_execute_sql, connection ERROR ! -- %s" % estr, xbmc.LOGWARNING)
                    break
            finally:
                try:
                    if conn:
                        conn.close()
                except Exception:
                    pass
        return None


    @staticmethod
    def getTimestamp(date_time):
        # use POSIX timestamp
        try:
            return int(date_time.timestamp())
        except Exception:
            return int(time.mktime(date_time.timetuple()))


    def getChecksum(self, stringinput):
        # return simple summed-ord checksum; include global checksum if present
        if not stringinput and not self.global_checksum:
            return 0
        if self.global_checksum:
            combined = "%s-%s" % (self.global_checksum, stringinput)
        else:
            combined = str(stringinput)
        # faster summation than reduce+map
        return sum(map(ord, combined))