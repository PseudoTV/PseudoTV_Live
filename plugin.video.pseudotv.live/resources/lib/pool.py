#   Copyright (C) 2023 Lunatixz
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
from threading          import Event, Thread, Timer, enumerate
from itertools          import repeat, count
from functools          import partial, wraps, reduce    

#info
ADDON_ID      = 'plugin.video.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')

#variables
PAGE_LIMIT    = int((REAL_SETTINGS.getSetting('Page_Limit') or "25"))
DEBUG_ENABLED = REAL_SETTINGS.getSetting('Enable_Debugging').lower() == 'true'

def log(event, level=xbmc.LOGDEBUG):
    if not DEBUG_ENABLED and level != xbmc.LOGERROR: return #todo use debug level filter
    if level == xbmc.LOGERROR: event = '%s\n%s'%(event,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,event),level)
       
def chunkLst(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def roundupDIV(p, q):
    try:
        d, r = divmod(p, q)
        if r: d += 1
        return d
    except ZeroDivisionError: 
        return 1
        
def timeit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result     = method(*args, **kwargs)
        end_time   = time.time()
        if REAL_SETTINGS.getSetting('Enable_Debugging').lower() == 'true':
            log('%s => %s ms'%(method.__qualname__.replace('.',': '),(end_time-start_time)*1000))
        return result
    return wrapper
    
def killit(timeout=15.0, default={}):
    def internal(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            class waiter(Thread):
                def __init__(self):
                    Thread.__init__(self)
                    self.result = None
                    self.error  = None
                def run(self):
                    try:    self.result = method(*args, **kwargs)
                    except: self.error  = sys.exc_info()[0]
            timer = waiter()
            timer.start()
            timer.join(timeout)
            if timer.is_alive():
                log('%s, Timed out!'%(method.__qualname__.replace('.',': ')))
                return default
            if timer.error:
                log('%s, failed! %s'%(method.__qualname__.replace('.',': '),timer.error), xbmc.LOGERROR)
                return default
            return timer.result
        return wrapper
    return internal

def killJSON(method):
    @wraps(method)
    def wrapper(timeout, *args, **kwargs):
        class waiter(Thread):
            def __init__(self):
                Thread.__init__(self)
                self.result = None
                self.error  = None
            def run(self):
                try:    self.result = method(*args, **kwargs)
                except: self.error  = sys.exc_info()[0]
        timer = waiter()
        timer.start()
        timer.join(timeout)
        if timer.is_alive():
            log('%s, Timed out!'%(method.__qualname__.replace('.',': ')))
            return {'error':{'message':'JSONRPC timed out!'}}
        if timer.error:
            log('%s, failed! %s'%(method.__qualname__.replace('.',': '),timer.error), xbmc.LOGERROR)
            return {'error':{'message':'JSONRPC timed out!'}}
        return timer.result
    return wrapper

def poolit(method):
    @wraps(method)
    def wrapper(items=[], *args, **kwargs):
        results  = []
        cpucount = Cores().CPUcount()
        threads  = cpucount * 2
        pool = Concurrent(threads)
        try:
            if cpucount > 1 and len(items) > 1:
                results = pool.executors(method, items, *args, **kwargs)
            else:
                results = pool.generator(method, items, *args, **kwargs)
        except Exception as e:
            log('poolit, failed! %s'%(e), xbmc.LOGERROR)
        results = pool.generator(method, items, *args, **kwargs)
        log('%s => %s'%(pool.__class__.__name__, method.__qualname__.replace('.',': ')))
        return list([_f for _f in results if _f])
    return wrapper

def threadit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        cpucount = Cores().CPUcount()
        pool = Concurrent(roundupDIV(cpucount,2))
        results = pool.executor(method, None, *args, **kwargs)
        log('%s => %s'%(pool.__class__.__name__, method.__qualname__.replace('.',': ')))
        return results
    return wrapper

def timerit(method):
    @wraps(method)
    def wrapper(wait, *args, **kwargs):
        thread_name = '%s.%s'%('timerit',method.__qualname__.replace('.',': '))
        for thread in enumerate():
            if thread.name == thread_name and thread.is_alive():
                try: 
                    thread.cancel()
                    thread.join()
                    log('%s, canceling %s'%(method.__qualname__.replace('.',': '),thread_name))
                except: pass
        threadTimer = Timer(wait, method, *args, **kwargs)
        threadTimer.name = thread_name
        threadTimer.start()
        log('%s, starting %s wait = %s'%(method.__qualname__.replace('.',': '),thread_name,wait))
        return threadTimer
    return wrapper  


class Concurrent:
    def __init__(self, cpuCount=None):
        # https://pythonhosted.org/futures/
        # https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures
        if cpuCount is None: cpuCount = Cores().CPUcount()
        self.cpuCount = cpuCount
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def executor(self, func, timeout=None, *args, **kwargs):
        with ThreadPoolExecutor(roundupDIV(self.cpuCount,2)) as executor:
            future = executor.submit(func, *args, **kwargs)
            return future.result(timeout)


    @timeit
    def executors(self, func, items=[], timeout=None, *args, **kwargs):
        return [self.executor((partial(func, *args, **kwargs)), timeout, item) for item in items]


    @timeit
    def generator(self, func, items=[], *args, **kwargs):
        self.log("generator, items = %s"%(len(items)))
        return [partial(func, *args, **kwargs)(i) for i in items]


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
            while not MONITOR.abortRequested() and '\ncpu%s:'%(res) in dmesg: res += 1
            if res > 0: return res
        except OSError: pass
        return 1