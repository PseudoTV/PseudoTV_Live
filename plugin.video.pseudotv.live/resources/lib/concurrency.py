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
import re, os, subprocess
import resources.lib.globals as globals

from kodi_six    import xbmc
from itertools   import repeat
from functools   import partial
from collections import namedtuple

try:
    from multiprocessing.pool  import ThreadPool
    ENABLE_POOL  = True
    THREAD_ERROR = ""
except Exception as e:
    # Android currently does not support multiprocessing (parallelism), use (concurrent) threads.
    ENABLE_POOL  = False
    THREAD_ERROR = e

try:
    from multiprocessing import Thread, Queue, Empty
    Queue() # importing Queue does not raise importError on android, call directly.
except:
    from threading import Thread
    from queue     import Queue, Empty

Msg = namedtuple('Msg', ['event', 'args'])

class PoolHelper:
    def __init__(self):
        self.procEnabled = ENABLE_POOL
        self.procCount   = int(globals.roundupDIV(self.CPUcores(), {0:0,1:2,2:1}[globals.getSettingInt('CPU_Cores#')]))#User Select Full or *Half cores. *default
        self.minQueue    = self.procCount
        self.maxQueue    = int(globals.PAGE_LIMIT * self.procCount) #limit queue size to reasonable value.
        if not self.procEnabled: self.log("multiprocessing Disabled %s"%(THREAD_ERROR))
        self.log("ThreadPool procCount/threadCount = %s, minQueue = %s, maxQueue = %s"%(self.procCount,self.minQueue,self.maxQueue))


    def log(self, msg, level=xbmc.LOGDEBUG):
        return globals.log('%s: %s'%(self.__class__.__name__,msg),level)


    def poolList(self, func, items=[], args=None, kwargs=None, chunksize=None):
        results = []
        if self.procEnabled:
            try:
                if chunksize is None:
                    chunksize = globals.roundupDIV(len(items), self.procCount)
                    if len(items) == 0 or chunksize < 1: chunksize = 1 #set min. size
                self.log("poolList, chunksize = %s, items = %s"%(chunksize,len(items)))
            
                pool = ThreadPool(self.procCount)
                if kwargs:
                    results = pool.imap(partial(func, **kwargs), items, chunksize)
                elif args:
                    results = pool.imap(func, zip(items,repeat(args)), chunksize)
                else:
                    results = pool.imap(func, items, chunksize)
                pool.close()
                pool.join()
            except Exception as e: 
                self.log("poolList, threadPool Failed! %s"%(e), xbmc.LOGERROR)
        else:
            try:
                threadCount = self.procCount
                if len(items) >= self.minQueue and len(items) <= self.maxQueue:
                    results = self.threadList(func, items, args, kwargs, threadCount)
            except Exception as e: 
                self.log("poolList, threadList Failed! %s"%(e), xbmc.LOGERROR)
                
        if not results: 
            results = self.genList(func, items, args, kwargs)
        results = list(filter(None, results))
        self.log("poolList, %s has %s results"%(func.__name__,len(results)))
        return results
        
        
    def threadList(self, func, items=[], args=None, kwargs=None, threadCount=4):
        queue = Queue()
        if threadCount > len(items):
            threadCount = len(items)
        for idx, item in enumerate(items): 
            queue.put((idx, item))
        self.log("threadList, threadCount = %s, queue size = %s"%(threadCount, len(items)))
            
        results = {}
        errors  = {}
        class Worker(Thread):
            def run(self):
                while not globals.MY_MONITOR.abortRequested() and not errors:
                    try:
                        idx, item = queue.get(block=False)
                        try:
                            if kwargs is not None:
                                results[idx] = partial(func, **kwargs)
                            elif args is not None:
                                results[idx] = func((item,args))
                            else:
                                results[idx] = func(item)
                            if globals.MY_MONITOR.waitForAbort(0.001): break
                        except Exception as e: errors[idx] = sys.exc_info()
                    except Empty: break

        threads = [Worker() for _ in range(threadCount)]
        [t.start() for t in threads]
        [t.join()  for t in threads]

        if errors:
            if len(errors) > 1: self.log("threadList, multiple errors: %d:\n%s"%(len(errors), errors), xbmc.LOGERROR)
            item_i = min(errors.keys())
            type, value, tb = errors[item_i]
            self.log("threadList, exception on item %s/%s:\n%s"%(item_i, totItems, "\n".join(traceback.format_tb(tb))), xbmc.LOGERROR)
            raise value
        return (results[idx] for idx in range(len(results)))
            
        
    def genList(self, func, items=[], args=None, kwargs=None):
        self.log("genList, %s"%(func.__name__))
        try:
            if kwargs:
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
        
class BaseWorker(Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.myQueue   = Queue()
        self.myMonitor = globals.MY_MONITOR


    def log(self, msg, level=xbmc.LOGDEBUG):
        return globals.log('%s: %s'%(self.__class__.__name__,msg),level)


    def send(self, event, *args):
        msg = Msg(event, args)
        self.myQueue.put(msg)


    def dispatch(self, msg):
        event, args = msg
        handler = getattr(self, "do_%s"%event, None)
        if not handler:
            raise NotImplementedError("Thread has no handler for [%s]"%event)
        handler(*args)


    def start(self):
        self.log('BaseWorker: starting worker')
        while not self.myMonitor.abortRequested():
            if self.myMonitor.waitForAbort(1):
                self.log('worker aborted')
                break
            elif self.myQueue.empty(): 
                self.log('worker finished')
                break
            msg = self.myQueue.get()
            self.dispatch(msg)
        self.log('worker stopped')