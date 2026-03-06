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
import traceback

from variables           import *
from logger              import log
from concurrent.futures  import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

@contextmanager
def timeit(method):
    start_time = time.time()
    try: yield
    finally:
        end_time = time.time()
        log('%s timeit => %.2f ms'%(method.__qualname__.replace('.',': '),(end_time-start_time)*1000))

def debounceit(wait=SERVICE_INTERVAL):
    def decorator(method):
        timer = None
        timer_lock = Lock()
        @wraps(method)
        def wrapper(*args, **kwargs):
            def __run():
                try: 
                    with timeit(method):
                        method(*args, **kwargs)
                    log('%s, debounceit running %s'%(method.__qualname__.replace('.',': => -:'),timer.name))
                except Exception as e:
                    log('%s, debounceit failed! %s'%(method.__qualname__.replace('.',': '),e), xbmc.LOGERROR) 
            nonlocal timer
            with timer_lock:
                if timer is not None: timer.cancel()
                timer = Timer(float(wait), __run)
                timer.name = '%s.%s'%('debounceit',method.__qualname__.replace('.',': '))
                log('%s, debounceit starting %s waiting (%s)'%(method.__qualname__.replace('.',': => -:'),timer.name,wait))
                timer.start()
        return wrapper
    return decorator

def killit(method):
    @wraps(method)
    def wrapper(wait=30, *args, **kwargs):
        response = {'result': None, 'success': False, 'error': ''}
        def __run():
            try:
                with timeit(method):
                    response['result']  = method(*args, **kwargs)
                    response['success'] = True
            except Exception as e:
                response['error'] = e
        
        thread = Thread(target=__run)
        thread.name = f'killit.{method.__qualname__.replace('.',': ')}'
        thread.daemon = True # This is crucial: allows the app to exit even if thread hangs
        thread.start()
        thread.join(timeout=float(wait))
        if thread.is_alive() or response.get('error'):
            log('%s, killit Timed out! Errors: %s'%(method.__qualname__.replace('.',': '),response.get('error')), xbmc.LOGERROR)
            return None 
        return response['result'] if response['success'] else None
    return wrapper
       
def poolit(method):
    @wraps(method)
    def wrapper(items=None, wait=TIMEOUT_EXECUTORS, *args, **kwargs):
        if items is None: items = []
        class pooler(Thread):
            def __init__(self):
                Thread.__init__(self)
                self.result = None
                self.error  = None
            def run(self):
                try:    self.result = ExecutorPool().executors(method, items, wait, *args, **kwargs)
                except Exception: self.error  = traceback.format_exc()
        thread = pooler()
        thread.name   = '%s.%s'%('poolit',method.__qualname__.replace('.',': '))
        thread.start()
        log('%s, poolit starting %s waiting (%s)'%(method.__qualname__.replace('.',': => -:'),thread.name,wait))
        try:    thread.join(wait)
        except Exception: pass
        if (thread.is_alive() or thread.error): log('%s, poolit Timed out! Errors: %s'%(method.__qualname__.replace('.',': '),thread.error), xbmc.LOGERROR)
        return thread.result
    return wrapper
    
def executeit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        log('executeit => %s'%(method.__qualname__.replace('.',': ')))
        return ExecutorPool().executor(method, TIMEOUT_EXECUTOR, *args, **kwargs)
    return wrapper
    
def threadit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        thread_name = 'timerit.%s'%(method.__qualname__.replace('.',': '))
        for thread in thread_enumerate():
            if thread.name == thread_name and thread.is_alive():
                try:
                    thread.join(CPU_CYCLE) 
                    log('%s, threadit joining existing Thread: %s'%(method.__qualname__.replace('.',': '),thread_name)) 
                except Exception: pass
        def __run():
            try: 
                with timeit(method):
                    method(*args, **kwargs)
                log('%s, threadit running %s'%(method.__qualname__.replace('.',': => -:'),thread_name))
            except Exception as e:
                log('%s, threadit failed! %s'%(method.__qualname__.replace('.',': '),e), xbmc.LOGERROR) 
             
        thread = Thread(target=__run)
        thread.name = thread_name
        thread.start()
        log('%s, threadit starting %s'%(method.__qualname__.replace('.',': '),thread_name))
        return thread
    return wrapper

def timerit(method):
    @wraps(method)
    def wrapper(wait, *args, **kwargs):
        timer_name = 'timerit.%s'%(method.__qualname__.replace('.',': '))
        for thread in thread_enumerate():
            if thread.name == timer_name:
                if hasattr(thread, 'cancel'):
                    thread.cancel()
                    log('%s, timerit canceling existing Timer: %s'%(method.__qualname__.replace('.',': '),timer_name)) 
        def __run():
            try:
                with timeit(method):
                    method(*args, **kwargs)
                log('%s, timerit running %s'%(method.__qualname__.replace('.',': => -:'),timer_name))
            except Exception as e:
                log('%s, timerit failed! %s'%(method.__qualname__.replace('.',': '),e), xbmc.LOGERROR) 

        timer = Timer(float(wait), __run)
        timer.name = timer_name
        timer.start()
        log('%s, timerit starting %s wait = %s'%(method.__qualname__.replace('.',': '),timer_name,wait))
        return timer
    return wrapper

class ExecutorPool:
    _executor = ThreadPoolExecutor(max_workers=THREAD_COUNT)
    
    def __init__(self):
        self.useExecutor = REAL_SETTINGS.getSettingBool('Enable_Executor')


    def __del__(self):
        self._executor.shutdown(wait=False, cancel_futures=True)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def isShutdown(self):
        return getattr(self._executor, "_shutdown", False)
            
            
    def executor(self, func, timeout=None, *args, **kwargs):
        self.log("executor, func = %s, timeout = %s"%(func.__name__,timeout))
        if self.useExecutor:
            if self.isShutdown(): self._executor = ThreadPoolExecutor(max_workers=THREAD_COUNT)
            with timeit(func), self._executor as executor:
                try: return executor.submit(func, *args, **kwargs).result(timeout)
                except Exception as e: self.log("executor, func = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,e,args,kwargs), xbmc.LOGERROR)
        return self.execute(func, *args, **kwargs)


    def execute(self, func, *args, **kwargs):
        self.log("execute, func = %s"%(func.__name__))
        try:
            with timeit(func):
                return func(*args, **kwargs)
        except Exception as e: self.log("execute, func = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,e,args,kwargs), xbmc.LOGERROR)


    def _wrapped_partial(self, func, *args, **kwargs):
        partial_func = partial(func, *args, **kwargs)
        update_wrapper(partial_func, func)
        return partial_func
        
        
    def executors(self, func, items=[], timeout=None, *args, **kwargs):
        self.log("executors, func = %s, items = %s, timeout = %s"%(func.__name__,len(items),timeout))
        if self.useExecutor:
            if self.isShutdown(): self._executor = ThreadPoolExecutor(max_workers=THREAD_COUNT)
            with timeit(func), self._executor as executor:
                try: 
                    results = executor.map(self._wrapped_partial(func, *args, **kwargs), items, timeout=timeout)
                    return [r for r in results if r is not None]
                except Exception as e: self.log("executors, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)
        return self.generator(func, items, *args, **kwargs)


    def generator(self, func, items=[], *args, **kwargs):
        self.log("generator, items = %s"%(len(items)))
        try:
            with timeit(func):
                results = [self._wrapped_partial(func, *args, **kwargs)(i) for i in items]
                return [r for r in results if r is not None]
        except Exception as e: self.log("generator, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)