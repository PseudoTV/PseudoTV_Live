#   Copyright (C) 2024 Lunatixz
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
 
from globals            import *
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from itertools          import repeat, count
from functools          import partial, wraps, reduce, update_wrapper
 
def wrapped_partial(func, *args, **kwargs):
    partial_func = partial(func, *args, **kwargs)
    update_wrapper(partial_func, func)
    return partial_func
    
def timeit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result     = method(*args, **kwargs)
        end_time   = time.time()
        if REAL_SETTINGS.getSetting('Debug_Enable').lower() == 'true':
            log('%s timeit => %.2f ms'%(method.__qualname__.replace('.',': '),(end_time-start_time)*1000))
        return result
    return wrapper
    
def killit(method):
    @wraps(method)
    def wrapper(wait=30, *args, **kwargs):
        class waiter(Thread):
            def __init__(self):
                Thread.__init__(self)
                self.result = None
                self.error  = None
            def run(self):
                try:    self.result = method(*args, **kwargs)
                except: self.error  = sys.exc_info()[0]
        timer = waiter()
        timer.name = '%s.%s'%('killit',method.__qualname__.replace('.',': '))
        timer.daemon=True
        timer.start()
        try: timer.join(wait)
        except: pass
        log('%s, starting %s'%(method.__qualname__.replace('.',': '),timer.name))
        if (timer.is_alive() or timer.error): log('%s, Timed out! Errors: %s'%(method.__qualname__.replace('.',': '),timer.error), xbmc.LOGERROR)
        return timer.result
    return wrapper

def poolit(method):
    @wraps(method)
    def wrapper(items=[], *args, **kwargs):
        try:
            pool = ThreadPool()
            name = '%s.%s'%('poolit',method.__qualname__.replace('.',': '))
            log('%s, starting %s'%(method.__qualname__.replace('.',': '),name))
            results = pool.executors(method, items, *args, **kwargs)
        except Exception as e:
            log('poolit, failed! %s'%(e), xbmc.LOGERROR)
            results = pool.generator(method, items, *args, **kwargs)
        log('%s poolit => %s'%(pool.__class__.__name__, method.__qualname__.replace('.',': ')))
        return list([_f for _f in results if _f])
    return wrapper

def threadit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        thread_name = 'threadit.%s'%(method.__qualname__.replace('.',': '))
        for thread in thread_enumerate():
            if thread.name == thread_name and thread.is_alive():
                if hasattr(thread, 'cancel'):
                    thread.cancel()
                    log('%s, canceling %s'%(method.__qualname__.replace('.',': '),thread_name))        
        thread = Thread(None, method, None, args, kwargs)
        thread.name = thread_name
        thread.daemon=True
        thread.start()
        log('%s, starting %s'%(method.__qualname__.replace('.',': '),thread.name))
        return thread
    return wrapper

def timerit(method):
    @wraps(method)
    def wrapper(wait, *args, **kwargs):
        thread_name = 'timerit.%s'%(method.__qualname__.replace('.',': '))
        for timer in thread_enumerate():
            if timer.name == thread_name and timer.is_alive():
                if hasattr(timer, 'cancel'): 
                    timer.cancel()
                    log('%s, canceling %s'%(method.__qualname__.replace('.',': '),thread_name))    
                try: 
                    timer.join()
                    log('%s, joining %s'%(method.__qualname__.replace('.',': '),thread_name))    
                except: pass
        timer = Timer(float(wait), method, *args, **kwargs)
        timer.name = thread_name
        timer.start()
        log('%s, starting %s wait = %s'%(method.__qualname__.replace('.',': '),thread_name,wait))
        return timer
    return wrapper  

def executeit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        pool = ThreadPool()
        log('%s executeit => %s'%(pool.__class__.__name__, method.__qualname__.replace('.',': ')))
        return pool.executor(method, None, *args, **kwargs)
    return wrapper

class Cores:
    def __init__(self):
        self.cache = Cache(mem_cache=True)
    
    
    @cacheit()
    def CPUcount(self):
        """ Number of available virtual or physical CPUs on this system, i.e.
        user/real as output by time(1) when called with an optimally scaling
        userspace-only program
        """
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
            monitor = MONITOR()
            while not monitor.abortRequested() and '\ncpu%s:'%(res) in dmesg:
                if monitor.waitForAbort(0.001): break
                res += 1
            if res > 0: return res
            del monitor
        except OSError: pass
        return 1

class ThreadPool:
    CPUCount    = Cores().CPUcount()
    ThreadCount = CPUCount*2
    
    def __init__(self):
        self.log("__init__, ThreadPool Threads = %s, CPU's = %s"%(self.ThreadCount, self.CPUCount))


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def executor(self, func, timeout=None, *args, **kwargs):
        self.log("executor, func = %s, timeout = %s"%(func.__name__,timeout))
        with ThreadPoolExecutor(self.ThreadCount) as executor:
            try: return executor.submit(func, *args, **kwargs).result(timeout)
            except Exception as e: self.log("executor, func = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,e,args,kwargs), xbmc.LOGERROR)


    def executors(self, func, items=[], *args, **kwargs):
        self.log("executors, func = %s, items = %s"%(func.__name__,len(items)))
        with ThreadPoolExecutor(self.ThreadCount) as executor:
            try: return executor.map(wrapped_partial(func, *args, **kwargs), items)
            except Exception as e: self.log("executors, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)


    def generator(self, func, items=[], *args, **kwargs):
        self.log("generator, items = %s"%(len(items)))
        try: return [wrapped_partial(func, *args, **kwargs)(i) for i in items]
        except Exception as e: self.log("generator, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)
