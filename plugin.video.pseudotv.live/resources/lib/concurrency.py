  # Copyright (C) 2022 Lunatixz


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
import sys, time, re, os, subprocess, traceback

from kodi_six                  import xbmc, xbmcaddon
from itertools                 import repeat
from functools                 import partial, wraps
from resources.lib.cache       import Cache, cacheit

try:
    if (xbmc.getCondVisibility('System.Platform.Android') or xbmc.getCondVisibility('System.Platform.Windows')):
        from multiprocessing.dummy import Pool as ThreadPool
        USING_THREAD = True
    else:
        from multiprocessing.pool  import ThreadPool
        USING_THREAD = False
    from _multiprocessing import SemLock, sem_unlink #hack to raise two python issues. _multiprocessing import error, sem_unlink missing from native python (android).
except Exception as e:
    from resources.lib._threadpool import ThreadPool 
    USING_THREAD = True
    
ADDON_ID      = 'plugin.video.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
PAGE_LIMIT    = REAL_SETTINGS.getSettingInt('Page_Limit')

def timeit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        if not REAL_SETTINGS.getSetting('Enable_Debugging') == "true": return
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
    if level == xbmc.LOGERROR: msg = '%s\n%s'%(msg,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    
    
class Concurrent:
    def __init__(self):
        self.cpuCount = Cores().CPUcount() * 2
        # https://pythonhosted.org/futures/
        # https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def executor(self, func, args=None, kwargs=None, call=None):
        with concurrent.futures.ThreadPoolExecutor(self.cpuCount) as executor:
            if   args:   future = executor.submit(func, args)
            elif kwargs: future = executor.submit(func, kwargs)
            else:        future = executor.submit(func)
            if call: future.add_done_callback(call)
            return future.result()
            
            
    @timeit
    def executors(self, func, items=[], args=None, kwargs=None, chunksize=None, timeout=300):
        results = []
        if chunksize is None: chunksize = roundupDIV(len(items), Cores().CPUcount())
        if len(items) == 0 or chunksize < 1: chunksize = 1 #set min. size
        self.log("executors, chunksize = %s, items = %s"%(chunksize,len(items)))
        
        with concurrent.futures.ThreadPoolExecutor(self.cpuCount) as executor:
            if kwargs and isinstance(kwargs,dict):
                results = executor.map(partial(func, **kwargs), items, timeout, chunksize)
            else:
                if args: items = zip(items,repeat(args))
                try:
                    results = executor.map(func, items, timeout, chunksize)
                except Exception as e:
                    for item in items: results.append(self.executor(func, item))
                    # self.log("executors, Failed! %s"%(e), xbmc.LOGERROR)
            try:    return list(filter(None,results))
            except: return list(results)


class Parallel:
    def __init__(self):
        self.cpuCount = Cores().CPUcount()
        # https://pythonhosted.org/futures/
        # https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def executor(self, func, args=None, kwargs=None, call=None):
        with concurrent.futures.ProcessPoolExecutor(self.cpuCount) as executor:
            if   args:   future = executor.submit(func, args)
            elif kwargs: future = executor.submit(func, kwargs)
            else:        future = executor.submit(func)
            if call: future.add_done_callback(call)
            return future.result()
            
            
    @timeit
    def executors(self, func, items=[], args=None, kwargs=None, chunksize=None, timeout=300):
        results = []
        if chunksize is None: chunksize = roundupDIV(len(items), Cores().CPUcount())
        if len(items) == 0 or chunksize < 1: chunksize = 1 #set min. size
        self.log("executors, chunksize = %s, items = %s"%(chunksize,len(items)))
        
        with concurrent.futures.ProcessPoolExecutor(self.cpuCount) as executor:
            if kwargs and isinstance(kwargs,dict):
                results = executor.map(partial(func, **kwargs), items, timeout, chunksize)
            else:
                if args: items = zip(items,repeat(args))
                try:
                    results = executor.map(func, items, timeout, chunksize)
                except Exception as e:
                    for item in items: results.append(self.executor(func, item))
                    # self.log("executors, Failed! %s"%(e), xbmc.LOGERROR)
            try:    return list(filter(None,results))
            except: return list(results)
                
                
class PoolHelper:
    def __init__(self):
        self.cpuCount = Cores().CPUcount()
        if USING_THREAD: self.pool = Concurrent()
        else:            self.pool = Parallel()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
 
 
    def executor(self, func, args=None, kwargs=None, call=None):
        return self.pool.executor(func, args, kwargs, call)
            
        
    @timeit
    def poolList(self, func, items=[], args=None, kwargs=None, timeout=300, chunksize=None): 
        if chunksize is None: chunksize = roundupDIV(len(items), self.cpuCount)
        if len(items) == 0 or chunksize < 1: chunksize = 1 #set min. size
        self.log("poolList, chunksize = %s, items = %s"%(chunksize,len(items)))
        
        if kwargs and isinstance(kwargs,dict): 
            func = partial(func, **kwargs)
        elif args: 
            items = zip(items,repeat(args))
            
        try:    
            pool = ThreadPool(processes=self.cpuCount)
            results = pool.imap(func, items, chunksize)
            pool.close()
            pool.join()
        except Exception as e: 
            self.log("poolList, threadPool Failed! %s"%(e), xbmc.LOGERROR)
            results = [results.append(func(i)) for i in items]

        try:    return list(filter(None,results))
        except: return list(results)


class Cores:
    def __init__(self):
        self.cache = Cache()
    
    
    @cacheit()
    def CPUcount(self):
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
            while not xbmc.Monitor().abortRequested() and '\ncpu%s:'%(res) in dmesg: res += 1
            if res > 0: return res
        except OSError: pass
        return 1