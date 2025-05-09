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
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, TimeoutError
from itertools          import repeat, count
from functools          import partial, wraps, reduce, update_wrapper

try:
    import multiprocessing
    cpu_count   = multiprocessing.cpu_count()
    ENABLE_POOL = False #True force disable multiproc. until monkeypatch/wrapper to fix pickling error. 
except:
    ENABLE_POOL = False
    cpu_count   = os.cpu_count()

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
        log('%s, starting %s waiting (%s)'%(method.__qualname__.replace('.',': => -:'),timer.name,wait))
        if (timer.is_alive() or timer.error): log('%s, Timed out! Errors: %s'%(method.__qualname__.replace('.',': '),timer.error), xbmc.LOGERROR)
        return timer.result
    return wrapper

def poolit(method):
    @wraps(method)
    def wrapper(items=[], *args, **kwargs):
        try:
            pool = ExecutorPool()
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
        pool = ExecutorPool()
        log('%s executeit => %s'%(pool.__class__.__name__, method.__qualname__.replace('.',': ')))
        return pool.executor(method, None, *args, **kwargs)
    return wrapper

class ExecutorPool:
    def __init__(self):
        self.CPUCount = cpu_count
        if ENABLE_POOL: self.pool = ProcessPoolExecutor
        else:           self.pool = ThreadPoolExecutor
        self.log(f"__init__, multiprocessing = {ENABLE_POOL}, CORES = {self.CPUCount}, THREADS = {self._calculate_thread_count()}")


    def _calculate_thread_count(self):
        if ENABLE_POOL: return self.CPUCount
        else:           return int(os.getenv('THREAD_COUNT', self.CPUCount * 2))
            
            
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def executor(self, func, timeout=None, *args, **kwargs):
        self.log("executor, func = %s, timeout = %s"%(func.__name__,timeout))
        with self.pool(self._calculate_thread_count()) as executor:
            try: return executor.submit(func, *args, **kwargs).result(timeout)
            except Exception as e: self.log("executor, func = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,e,args,kwargs), xbmc.LOGERROR)


    def executors(self, func, items=[], *args, **kwargs):
        self.log("executors, func = %s, items = %s"%(func.__name__,len(items)))
        with self.pool(self._calculate_thread_count()) as executor:
            try: return executor.map(wrapped_partial(func, *args, **kwargs), items)
            except Exception as e: self.log("executors, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)


    def generator(self, func, items=[], *args, **kwargs):
        self.log("generator, items = %s"%(len(items)))
        try: return [wrapped_partial(func, *args, **kwargs)(i) for i in items]
        except Exception as e: self.log("generator, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)
