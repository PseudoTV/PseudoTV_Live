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
from typing import Any, Callable, Optional
from variables import *

class ExecutorPool:


    def __init__(self, workers: Optional[int] = None):
        if workers is None: workers = THREAD_WORKERS
        self._workers  = workers
        self._executor = ThreadPoolExecutor(max_workers=workers)
        self.log('__init__, workers=%d' % workers, xbmc.LOGINFO)
    
    def __del__(self):
        self.shutdown()


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s' % (self.__class__.__name__, msg), level)


    def isShutdown(self) -> bool:
        return getattr(self._executor, "_shutdown", False)
            
    def shutdown(self, wait: bool = False, cancel: bool = True):
        try: 
            self._executor.shutdown(wait=wait, cancel_futures=cancel)
            self.log("shutdown, executor stopped (wait=%s, cancel=%s)" % (wait, cancel), xbmc.LOGINFO)
        except Exception as e: self.log("shutdown failed: %s" % e, xbmc.LOGWARNING)
            
    def submit(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> bool:
        """Submit a function to the thread pool without blocking (fire-and-forget)."""
        if self.isShutdown():
            self.log('submit, pool was shutdown, skipping', xbmc.LOGWARNING)
            return False
        try:
            self._executor.submit(func, *args, **kwargs)
            return True
        except Exception as e:
            self.log("submit, %s failed: %s" % (func.__name__, e), xbmc.LOGERROR)
            return False


    def executor(self, func: Callable[..., Any], timeout: Optional[float] = None, *args: Any, **kwargs: Any) -> Any:
        """Execute a single function in the thread pool with a timeout."""
        if timeout is None: timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        useExecutor = REAL_SETTINGS.getSetting('Enable_Executor') == 'true'
        if not useExecutor and xbmc.getCondVisibility('Player.Playing'): useExecutor = True
        if self.isShutdown():
            self.log('executor, pool was shutdown, skipping', xbmc.LOGWARNING)
            return None
            
        with timeit(func):
            try:
                future = self._executor.submit(func, *args, **kwargs)
                return future.result(timeout=float(timeout))
            except TimeoutError:
                self.log("executor, %s timed out after %ds" % (func.__name__, timeout), xbmc.LOGWARNING)
                future.cancel()
            except Exception as e: 
                self.log("executor, %s failed: %s" % (func.__name__, e), xbmc.LOGERROR)


    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function synchronously with timing."""
        try:
            with timeit(func):
                return func(*args, **kwargs)
        except Exception as e: self.log(f"execute, func = {func.__name__} failed! {e}", xbmc.LOGERROR)


    def _wrapped_partial(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> partial:
        """Create a partial function that preserves the original function's metadata."""
        partial_func = partial(func, *args, **kwargs)
        update_wrapper(partial_func, func)
        return partial_func
        
    def executors(self, func: Callable[..., Any], items: Optional[list] = None, timeout: Optional[float] = None, *args: Any, **kwargs: Any) -> Optional[list]:
        """Execute a function over multiple items in parallel, returning collected results."""
        if items is None: items = []
        if timeout is None: timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        useExecutor = REAL_SETTINGS.getSetting('Enable_Executor') == 'true'
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


    def generator(self, func: Callable[..., Any], items: Optional[list] = None, *args: Any, **kwargs: Any) -> list:
        """Execute a function over items sequentially, filtering out None results."""
        if items is None: items = []
        self.log("generator, items = %s"%(len(items)))
        try:
            with timeit(func):
                results = [self._wrapped_partial(func, *args, **kwargs)(i) for i in items]
                return [r for r in results if r is not None]
        except Exception as e: self.log(f"generator, func = {func.__name__} failed! {e}", xbmc.LOGERROR) 
        return []

@contextmanager
def timeit(method: Callable[..., Any]) -> Any:
    """Context manager that logs the execution time of a method."""
    start_time = time.time()
    try: yield
    finally:
        LOG('%s timeit => %.2f ms'%(method.__qualname__.replace('.',': '),(time.time()-start_time)*1000))

def debounceit(wait: Optional[float] = None, monitor: Optional[Any] = None) -> Callable:
    """Decorator that debounces method calls, delaying execution until quiet period elapses."""
    if wait is None: wait = SERVICE_INTERVAL
    if monitor is None: monitor = MONITOR()
    def decorator(method: Callable[..., Any]) -> Callable:
        state = { 'timer': None, 'args': None, 'kwargs': None }
        lock  = Lock()
        
        @wraps(method)
        def wrapper(*args: Any, **kwargs: Any):
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
                        LOG(f"pool: {method.__qualname__} executed via {current_thread().name}", xbmc.LOGINFO)
                    except Exception as e: LOG(f"pool: {method.__qualname__}, failed!\n{e}", xbmc.LOGERROR)
                    finally:
                        with lock:
                            if state['timer'] == current_timer:
                                state['timer'] = None

                current_timer = Timer(float(wait), __run)
                current_timer.name = f"{ADDON_ID}.debounceit.{method.__qualname__}"
                current_timer.daemon = True
                state['timer'] = current_timer
                current_timer.start()
        return wrapper
    return decorator
    
_EXECUTOR_POOL = ExecutorPool()
    
def executeit(method: Callable[..., Any]) -> Callable:
    """Decorator that runs a method in the global executor pool with timeout handling."""
    @wraps(method)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        monitor = MONITOR()
        try:
            if monitor.abortRequested(): return None
            readable_name = method.__qualname__.replace('.', ': ')
            LOG(f"pool: executeit => {readable_name}", xbmc.LOGINFO)
            return _EXECUTOR_POOL.executor(method, TIMEOUT_EXECUTOR, *args, **kwargs)
        except (RuntimeError, KeyError) as pool_err:
            LOG(f"pool: executeit, infrastructure error running {method.__name__}, failed!\n{pool_err}", xbmc.LOGERROR)
            return None
        except concurrent.futures.TimeoutError:
            LOG(f"pool: executeit, {method.__name__} timed out after {TIMEOUT_EXECUTOR}s", xbmc.LOGWARNING)
            return None
        except Exception as method_err:
            LOG(f"pool: executeit, unhandled exception inside {method.__name__}, failed!\n{method_err}", xbmc.LOGERROR)
            return None
    return wrapper
    

def threadit(method: Callable[..., Any]) -> Callable:
    """Decorator that runs a method in a background thread, skipping if already active."""
    @wraps(method)
    def wrapper(*args: Any, **kwargs: Any) -> Optional[Thread]:
        monitor = MONITOR()
        if monitor.abortRequested(): return None
        with wrapper._lock:
            if wrapper._active_thread and wrapper._active_thread.is_alive():
                LOG(f"pool: {method.__qualname__}, execution skipped: previous background thread is still busy.", xbmc.LOGDEBUG)
                return wrapper._active_thread

        def __run():
            try:
                if monitor.abortRequested(): return
                with timeit(method):
                    method(*args, **kwargs)
                LOG(f"pool: {method.__qualname__} finished executing on {current_thread().name}", xbmc.LOGINFO)
            except Exception as e: LOG(f"pool: {method.__qualname__}, background run, failed!\n{e}", xbmc.LOGERROR)
            finally:
                with wrapper._lock:
                    if wrapper._active_thread == current_thread():
                        wrapper._active_thread = None

        thread = Thread(target=__run)
        thread.name = f"{ADDON_ID}.threadit.{method.__qualname__}"
        thread.daemon = True
        
        with wrapper._lock:
            if monitor.abortRequested(): return None
            wrapper._active_thread = thread
            thread.start()
        return thread
        
    wrapper._active_thread = None
    wrapper._lock = Lock()
    return wrapper
    

def timerit(method: Callable[..., Any]) -> Callable:
    """Decorator that schedules a method to run after a delay, cancelling previous pending calls."""
    _active_timer = None
    _lock = Lock()
    _latest_args = None
    _latest_kwargs = None

    @wraps(method)
    def wrapper(wait: float, *args: Any, **kwargs: Any) -> Optional[Timer]:
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
                LOG(f"pool: {method.__qualname__} executed on thread {current_thread().name}", xbmc.LOGINFO)
            except Exception as e: LOG(f"pool: {method.__qualname__}, execution, failed!\n{e}", xbmc.LOGERROR)
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
            timer = Timer(float(wait), __run)
            timer.name = f"{ADDON_ID}.timerit.{method.__qualname__}"
            timer.daemon = True
            current_thread_timer = timer 
            _active_timer = timer
            timer.start()
        return timer
    return wrapper
    

def poolit(method: Callable[..., Any]) -> Callable:
    """Decorator that runs a method over items in parallel via the executor pool with supervisor thread."""
    @wraps(method)
    def wrapper(items: Optional[list] = None, wait: float = TIMEOUT_EXECUTORS, *args: Any, **kwargs: Any) -> Any:
        monitor = MONITOR()
        if monitor.abortRequested(): return None
        if items is None: items = []
        execution_state = { 'result': None, 'error': None }
        
        def __worker():
            try:
                if monitor.abortRequested(): return
                execution_state['result'] = _EXECUTOR_POOL.executors(method, items, wait, *args, **kwargs)
                LOG(f"pool: {method.__qualname__} pool completed on {current_thread().name}", xbmc.LOGINFO)
            except Exception: execution_state['error'] = traceback.format_exc()

        if monitor.abortRequested(): return None
        thread = Thread(target=__worker)
        thread.name = f"{ADDON_ID}.poolit.{method.__qualname__}"
        thread.daemon = True
        thread.start()
        
        LOG(f"pool: {method.__name__} supervisor thread started: {thread.name}", xbmc.LOGDEBUG)
        thread.join(timeout=float(wait))
        if thread.is_alive():
            LOG(f"pool: {method.__name__} pool timed out! Background supervisor abandoned.", xbmc.LOGWARNING)
            return None
        if execution_state['error']:
            LOG(f"pool: {method.__name__} pool, failed!\n{execution_state['error']}", xbmc.LOGERROR)
            return None
        return execution_state['result']
    return wrapper
