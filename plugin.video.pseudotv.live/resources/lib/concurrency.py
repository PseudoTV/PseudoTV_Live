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
import re, os, subprocess, traceback

from kodi_six           import xbmc, xbmcaddon
from itertools          import repeat
from functools          import partial
from collections        import namedtuple

ADDON_ID      = 'plugin.video.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
PAGE_LIMIT    = REAL_SETTINGS.getSettingInt('Page_Limit')
THREAD_ERROR  = ""
    
try:
    import _multiprocessing # android will raise issue
    try:    from multiprocessing.dummy import Pool as ThreadPool
    except: from multiprocessing.pool  import ThreadPool
    ENABLE_POOL  = True
except Exception as e:
    # Android currently does not support multiprocessing (parallelism), use (concurrent) threads.
    THREAD_ERROR = e
    ENABLE_POOL  = False

try:
    from multiprocessing import Thread, Queue, Empty
    Queue() # importing Queue does not raise importError on android, call directly.
except:
    from threading import Thread
    from queue     import Queue, Empty
   
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

class PoolHelper:
    def __init__(self):
        self.procSetting = {0:False,1:0,2:2,3:1}[REAL_SETTINGS.getSettingInt('Enable_CPU_CORES')]#User Select Full or *Half cores. *default
        self.procEnabled = (ENABLE_POOL and self.procSetting) != False
        self.procCount   = int(roundupDIV(self.CPUcores(), self.procSetting)) 
        self.minQueue    = self.procCount
        self.maxQueue    = int(PAGE_LIMIT * self.procCount) #limit queue size to reasonable value.
        
        if self.procEnabled:
            self.log("ThreadPool procCount/threadCount = %s, minQueue = %s, maxQueue = %s"%(self.procCount,self.minQueue,self.maxQueue))
        else:
            if ENABLE_POOL: THREAD_MSG = "User Disabled!"
            else:           THREAD_MSG = "Multiprocessing not supported!"
            self.log("ThreadPool %s\n%s"%(THREAD_MSG,THREAD_ERROR))


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def poolList(self, func, items=[], args=None, kwargs=None, chunksize=None): # chunksize=None # temp Debug
        results = []
        if self.procEnabled:
            try:
                if chunksize is None:
                    chunksize = roundupDIV(len(items), self.procCount)
                    if len(items) == 0 or chunksize < 1: chunksize = 1 #set min. size
                self.log("poolList, chunksize = %s, items = %s"%(chunksize,len(items)))
                
                pool = ThreadPool(self.procCount)
                if kwargs and isinstance(kwargs,dict):
                    results = pool.imap(partial(func, **kwargs), items, chunksize)
                else:
                    if args: items = zip(items,repeat(args))
                    results = pool.imap(func, items, chunksize)
                pool.close()
                pool.join()
            except Exception as e: 
                self.log("poolList, threadPool Failed! %s"%(e), xbmc.LOGERROR)
        elif self.procSetting != False:
            try:
                threadCount = self.procCount
                if len(items) >= self.minQueue and len(items) <= self.maxQueue:
                    results = self.threadList(func, items, args, kwargs, threadCount)
            except Exception as e: 
                self.log("poolList, threadList Failed! %s"%(e), xbmc.LOGERROR)
                
        if results: 
            results = list(filter(None, results))
        else: 
            results = self.genList(func, items, args, kwargs)
        self.log("poolList, %s has %s results"%(func.__name__,len(results)))
        return results
        
        
    def threadList(self, func, items=[], args=None, kwargs=None, threadCount=4):
        if self.procSetting != False:
            queue = Queue()
            if threadCount > len(items): threadCount = len(items)
            for idx, item in enumerate(items): queue.put((idx, item))
            self.log("threadList, threadCount = %s, queue size = %s"%(threadCount, len(items)))
                
            results = {}
            errors  = {}
            class Worker(Thread):
                monitor = xbmc.Monitor()
                
                def run(self):
                    while not self.monitor.abortRequested() and not errors:
                        try:
                            idx, item = queue.get(block=False)
                            try:
                                if kwargs and isinstance(kwargs,dict):
                                    results[idx] = partial(func, **kwargs)
                                elif args is not None:
                                    results[idx] = func((item,args))
                                else:
                                    results[idx] = func(item)
                                if self.monitor.waitForAbort(0.001): break
                            except Exception as e: errors[idx] = sys.exc_info()
                        except Empty: break

            threads = [Worker() for _ in range(threadCount)]
            for t in threads: t.start()
            for t in threads: t.join()

            if errors:
                if len(errors) > 1: self.log("threadList, multiple errors: %d:\n%s"%(len(errors), errors), xbmc.LOGERROR)
                item_i = min(errors.keys())
                type, value, tb = errors[item_i]
                self.log("threadList, exception on item %s/%s:\n%s"%(item_i, totItems, "\n".join(traceback.format_tb(tb))), xbmc.LOGERROR)
                raise value
            return (results[idx] for idx in range(len(results)))
        else:
            return self.genList(func, items, args, kwargs)
        
        
    def genList(self, func, items=[], args=None, kwargs=None):
        self.log("genList, %s"%(func.__name__))
        try:
            if kwargs and isinstance(kwargs,dict):
                results = (partial(func, **kwargs) for item in items)
            elif args:
                results = (func((item, args)) for item in items)
            else:
                results = (func(item) for item in items)
            return list(filter(None, results))
        except Exception as e: 
            self.log("genList, Failed! %s"%(e), xbmc.LOGERROR)
            return []
        
        
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