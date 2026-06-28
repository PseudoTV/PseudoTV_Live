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

from constants           import *
from logger              import log
from concurrent.futures  import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

class ExecutorPool:
    def __init__(self, workers=THREAD_WORKERS):
        self._workers  = workers
        self._executor = ThreadPoolExecutor(max_workers=workers)
    
    def __del__(self):
        self.shutdown()

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def isShutdown(self):
        return getattr(self._executor, "_shutdown", False)
            
    def shutdown(self, wait=False, cancel=True):
        try: 
            self._executor.shutdown(wait=wait, cancel_futures=cancel)
            self.log("_shutdown, _executor")
        except Exception: pass
            
    def executor(self, func, timeout=None, *args, **kwargs):
        if timeout is None: timeout = int(REAL_SETTINGS.getSetting('API_Timeout'))
        useExecutor = REAL_SETTINGS.getSettingBool('Enable_Executor')
        if not useExecutor and xbmc.getCondVisibility('Player.Playing'): useExecutor = True
        if useExecutor:
            if self.isShutdown(): 
                self._executor = ThreadPoolExecutor(max_workers=self._workers)
                
            with timeit(func):
                try:
                    future = self._executor.submit(func, *args, **kwargs)
                    return future.result(timeout=float(timeout) )
                except TimeoutError:
                    self.log(f"executor, func = {func.__name__} timed out after {timeout}s", xbmc.LOGWARNING)
                    future.cancel()
                except Exception as e: 
                    self.log(f"executor, func = {func.__name__} failed! {e}", xbmc.LOGERROR)
        return self.execute(func, *args, **kwargs)

    def execute(self, func, *args, **kwargs):
        try:
            with timeit(func):
                return func(*args, **kwargs)
        except Exception as e: self.log(f"execute, func = {func.__name__} failed! {e}", xbmc.LOGERROR)

    def _wrapped_partial(self, func, *args, **kwargs):
        partial_func = partial(func, *args, **kwargs)
        update_wrapper(partial_func, func)
        return partial_func
        
    def executors(self, func, items=[], timeout=None, *args, **kwargs):
        if timeout is None: timeout = int(REAL_SETTINGS.getSetting('API_Timeout'))
        useExecutor = REAL_SETTINGS.getSettingBool('Enable_Executor')
        if not useExecutor and xbmc.getCondVisibility('Player.Playing'): useExecutor = True
        if useExecutor:
            if self.isShutdown(): 
                self._executor = ThreadPoolExecutor(max_workers=self._workers)
                
            with timeit(func):
                futures = {self._executor.submit(self._wrapped_partial(func, *args, **kwargs), i): i for i in items}
                results = []
                for future in as_completed(futures, timeout=float(timeout)):
                    try: results.append(future.result())
                    except Exception as e: self.log(f"executors, func = {func.__name__} failed! {e}", xbmc.LOGERROR)
                if results: return results
        return self.generator(func, items, *args, **kwargs)

    def generator(self, func, items=[], *args, **kwargs):
        self.log("generator, items = %s"%(len(items)))
        try:
            with timeit(func):
                results = [self._wrapped_partial(func, *args, **kwargs)(i) for i in items]
                return [r for r in results if r is not None]
        except Exception as e: self.log(f"generator, func = {func.__name__} failed! {e}", xbmc.LOGERROR) 
        return []

@contextmanager
def timeit(method):
    start_time = time.time()
    try: yield
    finally:
        end_time = time.time()
        log('%s timeit => %.2f ms'%(method.__qualname__.replace('.',': '),(end_time-start_time)*1000))

def debounceit(wait=SERVICE_INTERVAL, monitor=None):
    if monitor is None: monitor = MONITOR()
    def decorator(method):
        state = { 'timer': None, 'args': None, 'kwargs': None }
        lock  = threading.Lock()
        
        @wraps(method)
        def wrapper(*args, **kwargs):
            if monitor.abortRequested(): return
            with lock:
                #Cancel existing pending timer if it exists
                if state['timer'] is not None: state['timer'].cancel()
                if monitor.abortRequested():
                    state['timer'] = None
                    return
                
                state['args']   = args
                state['kwargs'] = kwargs
                def __run():
                    try:
                        if monitor.abortRequested(): return
                        with lock:
                            exec_args   = state['args']
                            exec_kwargs = state['kwargs']
                        
                        # Execute the target method
                        with timeit(method):
                            method(*exec_args, **exec_kwargs)
                        xbmc.log(f"{method.__qualname__} executed via {threading.current_thread().name}", xbmc.LOGINFO)
                    except Exception as e: xbmc.log(f"{method.__qualname__} failed! Error: {e}", xbmc.LOGERROR)
                    finally:
                        with lock:
                            if state['timer'] == current_timer:
                                state['timer'] = None

                current_timer = threading.Timer(float(wait), __run)
                current_timer.name = f"{ADDON_ID}.debounceit.{method.__qualname__}"
                state['timer'] = current_timer
                current_timer.start()
        return wrapper
    return decorator
    
def executeit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        monitor = MONITOR()
        try:
            if monitor.abortRequested(): return None
            readable_name = method.__qualname__.replace('.', ': ')
            xbmc.log(f"executeit => {readable_name}", xbmc.LOGINFO)
            return ExecutorPool().executor(method, TIMEOUT_EXECUTOR, *args, **kwargs)
        except (RuntimeError, KeyError) as pool_err:
            xbmc.log(f"executeit => Pool infrastructure error running {method.__name__}: {pool_err}", xbmc.LOGERROR)
            return None
        except concurrent.futures.TimeoutError:
            xbmc.log(f"executeit => {method.__name__} timed out after {TIMEOUT_EXECUTOR}s", xbmc.LOGWARNING)
            return None
        except Exception as method_err:
            xbmc.log(f"executeit => Unhandled exception inside {method.__name__}: {method_err}", xbmc.LOGERROR)
            return None
    return wrapper
    

def threadit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        monitor = MONITOR()
        if monitor.abortRequested(): return None
        with wrapper._lock:
            if wrapper._active_thread and wrapper._active_thread.is_alive():
                xbmc.log(f"{method.__qualname__} execution skipped: previous background thread is still busy.", xbmc.LOGDEBUG)
                return wrapper._active_thread

        def __run():
            try:
                if monitor.abortRequested(): return
                with timeit(method):
                    method(*args, **kwargs)
                xbmc.log(f"{method.__qualname__} finished executing on {threading.current_thread().name}", xbmc.LOGINFO)
            except Exception as e: xbmc.log(f"{method.__qualname__} background run failed! Error: {e}", xbmc.LOGERROR)
            finally:
                with wrapper._lock:
                    if wrapper._active_thread == threading.current_thread():
                        wrapper._active_thread = None

        thread = threading.Thread(target=__run)
        thread.name = f"{ADDON_ID}.threadit.{method.__qualname__}"
        thread.daemon = True
        
        with wrapper._lock:
            if monitor.abortRequested(): return None
            wrapper._active_thread = thread
            thread.start()
        return thread
        
    wrapper._active_thread = None
    wrapper._lock = threading.Lock()
    return wrapper
    

def timerit(method):
    _active_timer = None
    _lock = threading.Lock()
    _latest_args = None
    _latest_kwargs = None

    @wraps(method)
    def wrapper(wait, *args, **kwargs):
        nonlocal _active_timer, _latest_args, _latest_kwargs
        monitor = MONITOR()
        if monitor.abortRequested():  return None
        def __run():
            nonlocal _active_timer
            with _lock:
                current_args = _latest_args
                current_kwargs = _latest_kwargs
            if monitor.abortRequested(): return
            try:
                if not monitor.abortRequested():
                    with timeit(method):
                        method(*current_args, **current_kwargs)
                xbmc.log(f"{method.__qualname__} executed on thread {threading.current_thread().name}", xbmc.LOGINFO)
            except Exception as e: xbmc.log(f"{method.__qualname__} execution failed! Error: {e}", xbmc.LOGERROR)
            finally:
                with _lock:
                    if _active_timer == current_thread_timer:
                        _active_timer = None
        with _lock:
            if _active_timer is not None: _active_timer.cancel()
            if monitor.abortRequested():
                _active_timer = None
                return None
                
            _latest_args = args
            _latest_kwargs = kwargs
            timer = threading.Timer(float(wait), __run)
            timer.name = f"{ADDON_ID}.timerit.{method.__qualname__}"
            timer.daemon = True
            current_thread_timer = timer 
            _active_timer = timer
            timer.start()
        return timer
    return wrapper
    

def poolit(method):
    @wraps(method)
    def wrapper(items=None, wait=TIMEOUT_EXECUTORS, *args, **kwargs):
        monitor = MONITOR()
        if monitor.abortRequested(): return None
        if items is None: items = []
        execution_state = { 'result': None, 'error': None }
        
        def __worker():
            try:
                if monitor.abortRequested(): return
                execution_state['result'] = ExecutorPool().executors(method, items, wait, *args, **kwargs)
                xbmc.log(f"{method.__qualname__} pool completed on {threading.current_thread().name}", xbmc.LOGINFO)
            except Exception: execution_state['error'] = traceback.format_exc()

        if monitor.abortRequested(): return None
        thread = threading.Thread(target=__worker)
        thread.name = f"{ADDON_ID}.poolit.{method.__qualname__}"
        thread.daemon = True
        thread.start()
        
        xbmc.log(f"{method.__name__} supervisor thread started: {thread.name}", xbmc.LOGDEBUG)
        thread.join(timeout=float(wait))
        if thread.is_alive():
            xbmc.log(f"{method.__name__} pool timed out! Background supervisor abandoned.", xbmc.LOGWARNING)
            return None
        if execution_state['error']:
            xbmc.log(f"{method.__name__} pool failed with errors:\n{execution_state['error']}", xbmc.LOGERROR)
            return None
        return execution_state['result']
    return wrapper
