#   Copyright (C) 2026 Lunatixz
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
import traceback, threading

from variables           import *
from logger              import log
from concurrent.futures  import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

class ExecutorPool:
    _executor = ThreadPoolExecutor(max_workers=THREAD_COUNT)
    
    def __del__(self):
        try: self._executor.shutdown(wait=False, cancel_futures=True)
        except Exception: pass


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def isShutdown(self):
        return getattr(self._executor, "_shutdown", False)
            
            
    def executor(self, func, timeout=None, *args, **kwargs):
        self.log("executor, func = %s, timeout = %s"%(func.__name__,timeout))
        useExecutor = REAL_SETTINGS.getSettingBool('Enable_Executor')
        if not useExecutor and xbmc.getCondVisibility('Player.Playing'): useExecutor = True
        if useExecutor:
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
        useExecutor = REAL_SETTINGS.getSettingBool('Enable_Executor')
        if not useExecutor and xbmc.getCondVisibility('Player.Playing'): useExecutor = True
        if useExecutor:
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

@contextmanager
def timeit(method):
    start_time = time.time()
    try: yield
    finally:
        end_time = time.time()
        log('%s timeit => %.2f ms'%(method.__qualname__.replace('.',': '),(end_time-start_time)*1000))

def debounceit(wait=SERVICE_INTERVAL):
    def decorator(method):
        state   = {'timer': None}
        lock    = Lock()
        monitor = MONITOR()
        
        @wraps(method)
        def wrapper(*args, **kwargs):
            if monitor.abortRequested():
                return

            def __run():
                try:
                    if not monitor.abortRequested():
                        with timeit(method):
                            method(*args, **kwargs)
                    log('%s, executing %s' % (method.__qualname__.replace('.', ': => -:'), threading.current_thread().name))
                except Exception as e:
                    log('%s, failed! %s' % (method.__qualname__.replace('.', ': '), e), xbmc.LOGERROR)
                finally:
                    with lock:
                        if state['timer'] == threading.current_thread():
                            state['timer'] = None

            with lock:
                if state['timer'] is not None: 
                    state['timer'].cancel()
                    
                if monitor.abortRequested():
                    state['timer'] = None
                    return

                timer = Timer(float(wait), __run)
                timer.name = 'debounceit.%s' % (method.__qualname__.replace('.', ': '))
                state['timer'] = timer
                timer.start()
                
        return wrapper
    return decorator
    
def killit(method):
    @wraps(method)
    def wrapper(wait=None, *args, **kwargs):
        if wait is None: 
            wait = REAL_SETTINGS.getSettingInt('RPC_Wait')
        monitor  = MONITOR() 
        timeout  = float(wait) if wait >= 0 else None
        response = {'result': None, 'success': False, 'error': ''}

        def __run():
            if monitor.abortRequested(): 
                return
            try:
                with timeit(method):
                    response['result']  = method(*args, **kwargs)
                    response['success'] = True
                log('%s, executing %s' % (method.__qualname__.replace('.', ': => -:'), threading.current_thread().name))
            except Exception as e:
                response['error'] = e
                log('%s, failed! %s' % (method.__qualname__.replace('.', ': '), e), xbmc.LOGERROR)

        if monitor.abortRequested():
            return None
            
        thread = Thread(target=__run)
        thread.name = 'killit.%s' % (method.__qualname__.replace('.', ': '))
        thread.daemon = True 
        
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            log('%s timed out after %ss. Background thread remains active.' % (thread.name, wait), xbmc.LOGWARNING)
            return None
        return response['result'] if response['success'] else None
    return wrapper
    
def executeit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        if MONITOR().abortRequested():
            return None
        try:
            log('executeit => %s'%(method.__qualname__.replace('.',': ')))
            return EXECUTOR_POOL.executor(method, TIMEOUT_EXECUTOR, *args, **kwargs)
        except (RuntimeError, KeyError): return None
    return wrapper
    
def threadit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        monitor = MONITOR()
        if monitor.abortRequested():
            return None

        existing_thread = None
        with wrapper._lock:
            if wrapper._active_thread and wrapper._active_thread.is_alive():
                existing_thread = wrapper._active_thread

        if existing_thread:
            if not monitor.abortRequested():
                log('%s, joining existing Thread: %s' % (method.__qualname__, existing_thread.name))
                existing_thread.join(CPU_CYCLE)

        def __run():
            if monitor.abortRequested(): 
                return
            try:
                with timeit(method):
                    method(*args, **kwargs)
                log('%s, executing %s' % (method.__qualname__.replace('.', ': => -:'), threading.current_thread().name))
            except Exception as e: 
                log('%s, failed! %s' % (method.__qualname__.replace('.', ': '), e), xbmc.LOGERROR)
            finally:
                with wrapper._lock:
                    if wrapper._active_thread == threading.current_thread():
                        wrapper._active_thread = None

        thread = Thread(target=__run)
        thread.name = 'threadit.%s'%(method.__qualname__.replace('.',': '))
        thread.daemon = True
        
        with wrapper._lock:
            wrapper._active_thread = thread
            if not monitor.abortRequested():
                thread.start()
            else: return None
        return thread

    wrapper._active_thread = None
    wrapper._lock = Lock()
    return wrapper
    
def timerit(method):
    @wraps(method)
    def wrapper(wait, *args, **kwargs):
        monitor = MONITOR()
        wrapper._session_id += 1
        current_session = wrapper._session_id

        def __run():
            if monitor.abortRequested(): 
                return
            
            with wrapper._lock:
                if wrapper._session_id != current_session:
                    return

            try:
                if not monitor.abortRequested():
                    with timeit(method):
                        method(*args, **kwargs)
                    log('%s, running %s' % (method.__qualname__.replace('.', ': => -:'), threading.current_thread().name))
            except Exception as e:
                log('%s, failed! %s' % (method.__qualname__.replace('.', ': '), e), xbmc.LOGERROR)
            finally:
                with wrapper._lock:
                    if wrapper._session_id == current_session:
                        wrapper._active_timer = None

        with wrapper._lock:
            if wrapper._active_timer is not None:
                wrapper._active_timer.cancel()

            timer = Timer(float(wait), __run)
            timer.name = 'timerit.%s'%(method.__qualname__.replace('.',': '))
            timer.daemon = True
            wrapper._active_timer = timer
            
            if not monitor.abortRequested():
                timer.start()
            return timer

    wrapper._active_timer = None
    wrapper._session_id = 0
    wrapper._lock = Lock()
    return wrapper
    
def poolit(method):
    @wraps(method)
    def wrapper(items=None, wait=TIMEOUT_EXECUTORS, *args, **kwargs):
        monitor = MONITOR()
        if items is None: items = []
        
        if monitor.abortRequested():
            return None

        class pooler(Thread):
            def __init__(self):
                Thread.__init__(self)
                self.result = None
                self.error  = None
                self.daemon = True

            def run(self):
                if monitor.abortRequested(): return
                try:    
                    with timeit(method):
                        self.result = ExecutorPool().executors(method, items, wait, *args, **kwargs)
                    log('%s, running %s' % (method.__qualname__.replace('.', ': => -:'), threading.current_thread().name))
                except Exception as e:
                    self.error = traceback.format_exc()

        thread = pooler()
        thread.name = '%s.%s'%('poolit', method.__qualname__.replace('.',': '))
        
        if not monitor.abortRequested():
            thread.start()
            log('%s, poolit starting %s' % (method.__name__, thread.name))
            thread.join(float(wait))
        
        if thread.is_alive():
            log('%s, poolit Timed out! Thread remains in background.' % method.__name__, xbmc.LOGWARNING)
            return None
            
        if thread.error:
            log('%s, poolit Errors: %s' % (method.__name__, thread.error), xbmc.LOGERROR)
            
        return thread.result
    return wrapper