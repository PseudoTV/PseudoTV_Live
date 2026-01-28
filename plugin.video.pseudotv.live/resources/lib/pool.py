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
 
from globals             import *
from concurrent.futures  import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from functools           import partial, update_wrapper, wraps
from contextlib          import contextmanager
import threading
import time
import traceback
import sys
import os

class Service(object):
    monitor = MONITOR()
    def _shutdown(self, wait=1.0) -> bool:
        pendingShutdown = xbmcgui.Window(10000).getProperty('%s.pendingShutdown'%(ADDON_ID)) == "true"
        return (self.monitor.waitForAbort(wait) | pendingShutdown)
    def _interrupt(self) -> bool:
        pendingShutdown   = xbmcgui.Window(10000).getProperty('%s.pendingShutdown'%(ADDON_ID)) == "true"
        pendingInterrupt  = xbmcgui.Window(10000).getProperty('%s.pendingInterrupt'%(ADDON_ID)) == "true"
        pendingRestart    = xbmcgui.Window(10000).getProperty('%s.pendingRestart'%(ADDON_ID)) == "true"
        interruptActivity = xbmcgui.Window(10000).getProperty('%s.interruptActivity'%(ADDON_ID)) == "true"
        return (pendingShutdown | pendingRestart | pendingInterrupt | interruptActivity)
    def _suspend(self, wait=1.0) -> bool:
        pendingSuspend = xbmcgui.Window(10000).getProperty('%s.pendingSuspend'%(ADDON_ID)) == "true"
        return pendingSuspend
    def _sleep(self, wait=1.0):
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) | self._interrupt()): return True
            else: wait -= CPU_CYCLE
        return False
        

def wrapped_partial(func, *args, **kwargs):
    partial_func = partial(func, *args, **kwargs)
    update_wrapper(partial_func, func)
    return partial_func

@contextmanager
def timeit(method):
    start_time = time.time()
    try: yield
    finally:
        end_time = time.time()
        log('%s timeit => %.2f ms'%(method.__qualname__.replace('.',': '),(end_time-start_time)*1000))


def killit(method):
    @wraps(method)
    def wrapper(wait=30, *args, **kwargs):
        class waiter(Thread):
            def __init__(self):
                Thread.__init__(self)
                self.result = None
                self.error  = None
            def run(self):
                try:    self.result = ExecutorPool().executor(method, wait, *args, **kwargs)
                except: self.error  = sys.exc_info()[0]
        timer = waiter()
        timer.name = '%s.%s'%('killit',method.__qualname__.replace('.',': '))
        timer.daemon=True
        timer.start()
        log('%s, killit starting %s waiting (%s)'%(method.__qualname__.replace('.',': => -:'),timer.name,wait))
        try: timer.join(wait)
        except: pass
        if (timer.is_alive() or timer.error): log('%s, killit Timed out! Errors: %s'%(method.__qualname__.replace('.',': '),timer.error), xbmc.LOGERROR)
        return timer.result
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
                except: self.error  = traceback.format_exc()
        thread = pooler()
        thread.name   = '%s.%s'%('poolit',method.__qualname__.replace('.',': '))
        thread.daemon =True
        thread.start()
        log('%s, poolit starting %s waiting (%s)'%(method.__qualname__.replace('.',': => -:'),thread.name,wait))
        try:    thread.join(wait)
        except: pass
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
        thread_name = 'threadit.%s'%(method.__qualname__.replace('.',': '))
        for thread in thread_enumerate():
            if thread.name == thread_name and thread.is_alive():  
                try:
                    thread.join(0.1)    
                    log('%s, threadit joining existing Thread: %s'%(method.__qualname__.replace('.',': '),thread_name))          
                except: pass
        thread = Thread(None, method, None, args, kwargs)
        thread.name   = thread_name
        thread.daemon = True
        thread.start()
        log('%s, threadit starting %s'%(method.__qualname__.replace('.',': '),thread.name))
        return thread
    return wrapper

def timerit(method):
    @wraps(method)
    def wrapper(timer_wait, *args, **kwargs):
        timer_name = 'timerit.%s'%(method.__qualname__.replace('.',': '))
        for timer in thread_enumerate():
            if timer.name == timer_name and timer.is_alive():
                try:
                    timer.join(CPU_CYCLE)
                    log('%s, timerit joining existing Timer: %s'%(method.__qualname__.replace('.',': '),timer_name))       
                except: pass
                if hasattr(timer, 'cancel'): 
                    timer.cancel()
                    log('%s, timerit canceling existing Timer: %s'%(method.__qualname__.replace('.',': '),timer_name))    
        timer = Timer(float(timer_wait), method, *args, **kwargs)
        timer.name = timer_name
        timer.start()
        log('%s, timerit starting %s wait = %s'%(method.__qualname__.replace('.',': '),timer_name,timer_wait))
        return timer
    return wrapper  

class ExecutorPool:
    # Shared executor configured with an effective thread count computed above.
    _executor = ThreadPoolExecutor(max_workers=THREAD_COUNT, thread_name_prefix='PseudoTV-Executor')
    _executor_lock = threading.Lock()
    
    def __init__(self):
        self.useExecutor = REAL_SETTINGS.getSettingBool('Enable_Executor')
        self._executor = ExecutorPool._executor

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

    def isShutdown(self):
        return getattr(ExecutorPool._executor, "_shutdown", False)
            
    def _ensure_executor(self):
        # recreate the shared executor only when necessary and with a lock to avoid races
        if self.isShutdown():
            with ExecutorPool._executor_lock:
                if self.isShutdown():
                    # choose number of workers from config if available, else use computed default
                    workers = THREAD_COUNT
                    try:
                        user_setting = int(REAL_SETTINGS.getSetting('Executor_Thread_Count') or 0)
                        if user_setting > 0:
                            workers = max(1, min(64, user_setting))  # allow advanced users to change but cap
                    except Exception:
                        pass
                    ExecutorPool._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='PseudoTV-Executor')
        self._executor = ExecutorPool._executor

    def executor(self, func, timeout=None, *args, **kwargs):
        self.log("executor, func = %s, timeout = %s"%(getattr(func, "__name__", str(func)), timeout))
        if self.useExecutor:
            try:
                self._ensure_executor()
                executor = ExecutorPool._executor
                future = executor.submit(func, *args, **kwargs)
                return future.result(timeout)
            except Exception as e:
                self.log("executor, func = %s failed! %s\nargs = %s, kwargs = %s"%(getattr(func, "__name__", str(func)), e, args, kwargs), xbmc.LOGERROR)
        return self.execute(func, *args, **kwargs)

    def execute(self, func, *args, **kwargs):
        self.log("execute, func = %s"%(getattr(func, "__name__", str(func))))
        try:
            with timeit(func):
                return func(*args, **kwargs)
        except Exception as e: self.log("execute, func = %s failed! %s\nargs = %s, kwargs = %s"%(getattr(func, "__name__", str(func)), e, args, kwargs), xbmc.LOGERROR)

    def executors(self, func, items=None, timeout=None, *args, **kwargs):
        if items is None:
            items = []
        total_items = len(items)
        self.log("executors, func = %s, items = %s, timeout = %s"%(getattr(func, "__name__", str(func)), total_items, timeout))
        if total_items == 0:
            return []

        if self.useExecutor:
            try:
                self._ensure_executor()
                executor = ExecutorPool._executor

                results = []
                it = iter(items)
                in_flight = {}
                max_in_flight = max(1, THREAD_COUNT)

                # submit initial batch
                for _ in range(min(max_in_flight, total_items)):
                    try:
                        item = next(it)
                    except StopIteration:
                        break
                    fut = executor.submit(func, item, *args, **kwargs)
                    in_flight[fut] = item

                # process completed futures and keep the window filled
                while in_flight:
                    for fut in as_completed(list(in_flight.keys()), timeout=timeout):
                        try:
                            r = fut.result()
                            if r is not None:
                                results.append(r)
                        except FuturesTimeoutError:
                            self.log("executors, future timeout (unexpected) for func = %s"%(getattr(func, "__name__", str(func))), xbmc.LOGWARNING)
                        except Exception as e:
                            self.log("executors, func = %s item failed! %s\nargs = %s, kwargs = %s"%(getattr(func, "__name__", str(func)), e, args, kwargs), xbmc.LOGERROR)
                        # remove completed future
                        try:
                            del in_flight[fut]
                        except KeyError:
                            pass
                        # submit next item to keep pipeline full
                        try:
                            item = next(it)
                            newf = executor.submit(func, item, *args, **kwargs)
                            in_flight[newf] = item
                        except StopIteration:
                            pass
                return results
            except Exception as e:
                self.log("executors, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(getattr(func, "__name__", str(func)), total_items, e, args, kwargs), xbmc.LOGERROR)
        return self.generator(func, items, *args, **kwargs)

    def generator(self, func, items=None, *args, **kwargs):
        if items is None:
            items = []
        self.log("generator, items = %s"%(len(items)))
        try:
            with timeit(func):
                results = []
                for i in items:
                    try:
                        r = func(i, *args, **kwargs)
                        if r is not None:
                            results.append(r)
                    except Exception as e:
                        self.log("generator, func = %s item failed! %s\nargs = %s, kwargs = %s"%(getattr(func, "__name__", str(func)), e, args, kwargs), xbmc.LOGERROR)
                return results
        except Exception as e: self.log("generator, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(getattr(func, "__name__", str(func)), len(items), e, args, kwargs), xbmc.LOGERROR)