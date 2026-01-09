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
    def wrapper(items=[], wait=TIMEOUT_EXECUTORS, *args, **kwargs):
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
    _executor = ThreadPoolExecutor(max_workers=THREAD_COUNT)
    
    def __init__(self):
        self.useExecutor = REAL_SETTINGS.getSettingBool('Enable_Executor')


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


    def executors(self, func, items=[], timeout=None, *args, **kwargs):
        self.log("executors, func = %s, items = %s, timeout = %s"%(func.__name__,len(items),timeout))
        if self.useExecutor:
            if self.isShutdown(): self._executor = ThreadPoolExecutor(max_workers=THREAD_COUNT)
            with timeit(func), self._executor as executor:
                try: 
                    results = executor.map(wrapped_partial(func, *args, **kwargs), items, timeout=timeout)
                    return [r for r in results if r is not None]
                except Exception as e: self.log("executors, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)
        return self.generator(func, items, *args, **kwargs)


    def generator(self, func, items=[], *args, **kwargs):
        self.log("generator, items = %s"%(len(items)))
        try:
            with timeit(func):
                results = [wrapped_partial(func, *args, **kwargs)(i) for i in items]
                return [r for r in results if r is not None]
        except Exception as e: self.log("generator, func = %s, items = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,len(items),e,args,kwargs), xbmc.LOGERROR)