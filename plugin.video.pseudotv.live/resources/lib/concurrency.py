  # Copyright (C) 2021 Lunatixz


# This file is part of PseudoTV Live.

# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import concurrent.futures
import time, re, os, subprocess, traceback

from kodi_six                  import xbmc, xbmcaddon
from itertools                 import repeat
from functools                 import partial, wraps
from resources.lib.cache       import Cache, cacheit

try:
    import _multiprocessing # android will raise issue, inherent decency of multiprocessing.
    try:    from multiprocessing.dummy import Pool as ThreadPool
    except: from multiprocessing.pool  import ThreadPool
    ENABLE_POOL  = True
    THREAD_ERROR = ""
except Exception as e:
    # Android currently does not support multiprocessing (parallelism), use (concurrent) threads.
    THREAD_ERROR = e
    ENABLE_POOL  = False

ADDON_ID      = 'plugin.video.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
PAGE_LIMIT    = REAL_SETTINGS.getSettingInt('Page_Limit')

def timeit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result     = method(*args, **kwargs)
        end_time   = time.time()
        log('%s => %s ms'%(method.__qualname__.replace('.',': '),(end_time-start_time)*1000))
        return result
    return wrapper
    
def roundupDIV(p, q):
    try:
        d, r = divmod(p, q)
        if r: d += 1
        return d
    except ZeroDivisionError: 
        return 1
    
def log(msg, level=xbmc.LOGDEBUG):
    if not REAL_SETTINGS.getSetting('Enable_Debugging') == "true" and level != xbmc.LOGERROR: return
    if not isinstance(msg,str): msg = str(msg)
    if level == xbmc.LOGERROR: msg = '%s\n%s'%((msg),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    
class Concurrent:    
    def __init__(self, workerCNT=2):
        self.thread  = Concurrent_Thread(workerCNT)
        if ENABLE_POOL and workerCNT >= 2:
            self.worker = Concurrent_Process(workerCNT)
        else: 
            self.worker = self.thread
                
        # self.log('__init__, workerCNT = %s, work = %s'%(workerCNT,self.worker))
        # https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    @timeit
    def executor(self, func, args=None, kwargs=None, call=None):
        try:
            return self.worker.executor(func, args, kwargs, call)
        except Exception as e: 
            self.log("executor, Failed! %s"%(e), xbmc.LOGERROR)
            if self.worker == self.thread: return []
            #if Concurrent_Process raises exception try Concurrent_Thread
            return self.thread.executor(func, args, kwargs, call)
        
        
    @timeit
    def executors(self, func, items=[], args=None, kwargs=None, chunksize=None, timeout=300):
        try:
            return self.worker.executors(func, items, args, kwargs, chunksize, timeout)
        except Exception as e: 
            self.log("executors, Failed! %s"%(e), xbmc.LOGERROR)
            if self.worker == self.thread: return []
            #if Concurrent_Process raises exception try Concurrent_Thread
            return self.thread.executors(func, items, args, kwargs, chunksize, timeout)
        
        
class Concurrent_Thread:
    def __init__(self, workerCNT=2):
        self.workerCNT    = workerCNT
        self.workexecutor = concurrent.futures.ThreadPoolExecutor
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def executor(self, func, args=None, kwargs=None, call=None):
        with self.workexecutor(self.workerCNT) as executor:
            if   args:   future = executor.submit(func, args)
            elif kwargs: future = executor.submit(func, kwargs)
            else:        future = executor.submit(func)
            if call: future.add_done_callback(call)
            return future.result()
            
            
    def executors(self, func, items=[], args=None, kwargs=None, chunksize=None, timeout=300):
        results = []
        if chunksize is None: chunksize = roundupDIV(len(items), self.workerCNT)
        if len(items) == 0 or chunksize < 1: chunksize = 1 #set min. size
        self.log("poolList, chunksize = %s, items = %s"%(chunksize,len(items)))
        with self.workexecutor(self.workerCNT) as executor:
            if kwargs and isinstance(kwargs,dict):
                results = executor.map(partial(func, **kwargs), items, timeout, chunksize)
            else:
                if args: items = zip(items,repeat(args))
                try:
                    results = executor.map(func, items, timeout, chunksize)
                except Exception as e:
                    for item in items: results.append(self.executor(func, item))
                    # self.log("executors, Failed! %s"%(e), xbmc.LOGERROR)
            return list(filter(None,results))
        
        
class Concurrent_Process:
    def __init__(self, workerCNT=2):
        self.workerCNT    = workerCNT
        self.workexecutor = concurrent.futures.ProcessPoolExecutor
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def executor(self, func, args=None, kwargs=None, call=None):
        with self.workexecutor(self.workerCNT) as executor:
            if   args:   future = executor.submit(func, args)
            elif kwargs: future = executor.submit(func, kwargs)
            else:        future = executor.submit(func)
            if call: future.add_done_callback(call)
            try:    return future.result()
            except: return Concurrent_Thread(self.workerCNT).executor(func, args, kwargs, call)
            ##todo debug process issues:
            #concurrent.futures.process.BrokenProcessPool: A process in the process pool was terminated abruptly while the future was running or pending.
            
            
    def executors(self, func, items=[], args=None, kwargs=None, chunksize=None, timeout=300):
        results = []
        with self.workexecutor(self.workerCNT) as executor:
            if kwargs and isinstance(kwargs,dict):
                results = executor.map(partial(func, **kwargs), items, timeout)
            else:
                if args: items = zip(items,repeat(args))
                try:
                    results = executor.map(func, items, timeout)
                except Exception as e:
                    for item in items: results.append(self.executor(func, item))
                    # self.log("executors, Failed! %s"%(e), xbmc.LOGERROR)
                    ##todo debug serialization issues:
                    #AttributeError: Can't pickle local object Library.getEnabledItems
                    #TypeError: 'int' object is not iterable Library.getEnabledItems
            return list(filter(None,results))
        

class multiProcess:
    def __init__(self, workerCNT=2):
        self.workerCNT = workerCNT


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    @timeit
    def poolThread(self, func, items=[], args=None, kwargs=None, chunksize=None):
        results = []
        if chunksize is None: chunksize = roundupDIV(len(items), self.workerCNT)
        if len(items) == 0 or chunksize < 1: chunksize = 1 #set min. size
        self.log("poolThread, chunksize = %s, items = %s"%(chunksize,len(items)))
        
        pool = ThreadPool(self.workerCNT)
        if kwargs and isinstance(kwargs,dict):
            results = pool.imap(partial(func, **kwargs), items, chunksize)
        else:
            if args: items = zip(items,repeat(args))
            results = pool.imap(func, items, chunksize)
        pool.close()
        pool.join()
        return list(filter(None, results))


class PoolHelper:
    def __init__(self):
        self.procSetting = {0:False,1:0,2:2,3:1}[REAL_SETTINGS.getSettingInt('Enable_CPU_CORES')]#User Select Full or *Half cores. *default
        self.procEnabled = (ENABLE_POOL and self.procSetting) != False
        self.procCount   = int(roundupDIV(Cores().CPUcores(), self.procSetting))
        
        if self.procEnabled or self.procSetting != False:
            self.log("ThreadPool procCount = %s"%(self.procCount))
        else:
            if ENABLE_POOL: THREAD_MSG = "User Disabled!"
            else:           THREAD_MSG = "Multiprocessing not supported!"
            self.log("ThreadPool %s\n%s"%(THREAD_MSG,THREAD_ERROR))


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def poolList(self, func, items=[], args=None, kwargs=None, chunksize=None):
        results = []
        failed  = False
        
        if self.procEnabled:
            try:
                workexecutor = multiProcess(self.procCount)
                results = workexecutor.poolThread(func, items, args, kwargs, chunksize)
            except Exception as e: 
                failed = True
                self.log("poolList, multiProcess Failed! %s"%(e), xbmc.LOGERROR)
        elif self.procSetting != False:
            try:
                workexecutor = Concurrent_Thread(self.procCount)
                results = workexecutor.executors(func, items, args, kwargs)
            except Exception as e:
                failed = True
                self.log("poolList, Concurrent Failed! %s"%(e), xbmc.LOGERROR)

        if not results and not failed: 
            results = self.genList(func, items, args, kwargs)
        return results
        

    @timeit
    def genList(self, func, items=[], args=None, kwargs=None):
        self.log("genList, %s"%(func.__name__))
        try:
            if kwargs and isinstance(kwargs,dict):
                results = (partial(func, **kwargs)(item) for item in items)
            elif args:
                results = (func((item, args)) for item in items)
            else:
                results = (func(item) for item in items)
            return list(filter(None, results))
        except Exception as e: 
            self.log("genList, Failed! %s"%(e), xbmc.LOGERROR)
            return []


class Cores:
    def __init__(self):
        self.cache = Cache()
    
    
    @cacheit()
    def CPUcores(self):
        """ Number of available virtual or physical CPUs on this system, i.e.
        user/real as output by time(1) when called with an optimally scaling
        userspace-only program"""
        # cpuset
        # cpuset may restrict the number of *available* processors
        try:
            m = re.search(r'(?m)^Cpus_allowed:\s*(.*)$',open('/proc/self/status').read())
            if m:
                res = bin(int(m.group(1).replace(',', ''), 16)).count('1')
                if res > 0: return res
        except IOError: pass
        
        # Python 2.6+
        try:
            from multiprocessing import cpu_count
            return cpu_count()
        except (ImportError, NotImplementedError):
            pass

        try:
            import psutil
            return psutil.cpu_count()   # psutil.NUM_CPUS on old versions
        except (ImportError, AttributeError):  pass

        # POSIX
        try:
            res = int(os.sysconf('SC_NPROCESSORS_ONLN'))
            if res > 0: return res
        except (AttributeError, ValueError): pass

        # Windows
        try:
            res = int(os.environ['NUMBER_OF_PROCESSORS'])
            if res > 0: return res
        except (KeyError, ValueError): pass

        # jython
        try:
            from java.lang import Runtime
            runtime = Runtime.getRuntime()
            res = runtime.availableProcessors()
            if res > 0: return res
        except ImportError: pass

        # BSD
        try:
            sysctl = subprocess.Popen(['sysctl', '-n', 'hw.ncpu'],stdout=subprocess.PIPE)
            scStdout = sysctl.communicate()[0]
            res = int(scStdout)
            if res > 0: return res
        except (OSError, ValueError): pass

        # Linux
        try:
            res = open('/proc/cpuinfo').read().count('processor\t:')
            if res > 0: return res
        except IOError: pass

        # Solaris
        try:
            pseudoDevices = os.listdir('/devices/pseudo/')
            res = 0
            for pd in pseudoDevices:
                if re.match(r'^cpuid@[0-9]+$', pd): res += 1
            if res > 0: return res
        except OSError: pass

        # Other UNIXes (heuristic)
        try:
            try:
                dmesg = open('/var/run/dmesg.boot').read()
            except IOError:
                dmesgProcess = subprocess.Popen(['dmesg'], stdout=subprocess.PIPE)
                dmesg = dmesgProcess.communicate()[0]

            res = 0
            while '\ncpu' + str(res) + ':' in dmesg: res += 1
            if res > 0: return res
        except OSError: pass
        return 1