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
from variables     import *

class Task(object):
    def __init__(self, func, args=(), kwargs=None, priority=3, execute_at=0):
        self.func         = func
        self.args         = args
        self.kwargs       = kwargs if kwargs is not None else {}
        self.priority     = priority
        self.execute_at   = execute_at
        self.is_cancelled = False
        self.created_at   = time.time()

    def cancel(self):
        self.is_cancelled = True

    def __lt__(self, other):
        return self.priority < other.priority

class CustomQueue(object):
    AGE_BOOST_INTERVAL = 20  # seconds between priority aging ticks
    AGE_BOOST_STEP     = 1.0 # priority levels boosted per interval
    MAX_HEAP_SIZE      = 500 # hard limit to prevent memory growth

    def __init__(self, service, workers=THREAD_WORKERS):
        self.service  = service
        self.monitor  = service.monitor
        self.cache    = service.cache
        self.pool     = service.pool
        self.lock     = Lock()
        self.wake     = Event()
        
        self.heap     = []
        self.pending  = {}
        self.counter  = 0
        
        self.useExecutor = Globals.SETTINGS.getSettingBool('Enable_Executor')
        self.queueThread = Thread(target=self.execute, name=f"{ADDON_ID}.priorityQUE")
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return Globals._log(f'{self.__class__.__name__}: {msg}', level)
        
    def _freeze(self, obj):
        if isinstance(obj, list): return tuple(self._freeze(item) for item in obj)
        if isinstance(obj, dict): return tuple(sorted((k, self._freeze(v)) for k, v in obj.items()))
        if isinstance(obj, set):  return frozenset(self._freeze(item) for item in obj)
        return obj
        
    def _get_task_key(self, func, args, kwargs):
        return (func.__name__, tuple(self._freeze(arg) for arg in args), tuple(sorted((k, self._freeze(v)) for k, v in kwargs.items())) if kwargs else ())

    def _compute_score(self, task):
        wait_time    = max(0.0, time.time() - task.created_at)
        aging_boost  = (wait_time / self.AGE_BOOST_INTERVAL) * self.AGE_BOOST_STEP
        eff_priority = max(1.0, task.priority - aging_boost)
        return task.execute_at + (eff_priority * 2.0)

    def _evict_lowest(self):
        if not self.heap: return
        worst_idx = max(range(len(self.heap)), key=lambda i: self.heap[i][0])
        _, _, task = self.heap[worst_idx]
        self.log(f"_evict_lowest, Dropping {task.func.__name__} (Priority: {task.priority}).", xbmc.LOGWARNING)
        task.cancel()
        task_key = self._get_task_key(task.func, task.args, task.kwargs)
        self.pending.pop(task_key, None)
        self.heap[worst_idx] = self.heap[-1]
        self.heap.pop()
        if self.heap: heapq.heapify(self.heap)

    def push(self, package: tuple, priority: int = 3, delay: int = 0, timer: int = 0):
        now = time.time()
        if   timer: execute_at = timer
        elif delay: execute_at = now + delay
        else:       execute_at = now
            
        func, args, kwargs = package
        if kwargs is None: kwargs = {}
        task_key = self._get_task_key(func, args, kwargs)
        if task_key:
            priority = max(1, min(5, int(priority)))
            with self.lock:
                if task_key in self.pending:
                    existing_task = self.pending[task_key]
                    # Lower numerical value = HIGHER priority (1=highest, 5=lowest)
                    if priority < existing_task.priority:
                        self.log(f"push, Upgrading {func.__name__} priority from {existing_task.priority} to {priority}.", xbmc.LOGDEBUG)
                        existing_task.cancel()
                        new_task = Task(func, args, kwargs, priority, execute_at)
                        self.pending[task_key] = new_task
                        self.counter += 1
                        heapq.heappush(self.heap, (self._compute_score(new_task), self.counter, new_task))
                    else: self.log(f"push, Task {func.__name__} ignored (already queued with higher/equal priority {existing_task.priority}).", xbmc.LOGDEBUG)
                else:
                    if len(self.heap) >= self.MAX_HEAP_SIZE: self._evict_lowest()
                    new_task = Task(func, args, kwargs, priority, execute_at)
                    self.pending[task_key] = new_task
                    self.counter += 1
                    heapq.heappush(self.heap, (self._compute_score(new_task), self.counter, new_task))
                    self.log(f"push, Pushed task {func.__name__} (Priority: {priority}).", xbmc.LOGDEBUG)

            if not self.monitor.abortRequested() and not self.queueThread.is_alive():
                self.useExecutor = Globals.SETTINGS.getSettingBool('Enable_Executor')
                self.queueThread = Thread(target=self.execute, name=f"{ADDON_ID}.queueThread")
                self.queueThread.daemon = True
                self.queueThread.start()

    def pop(self):
        with self.lock:
            while not self.monitor.abortRequested() and self.heap:
                _, _, task = heapq.heappop(self.heap)
                task_key = self._get_task_key(task.func, task.args, task.kwargs)
                if task.is_cancelled:
                    self.pending.pop(task_key, None)
                    continue
                if self.pending.get(task_key) is task:
                    self.pending.pop(task_key, None)
                return task
            return None

    def execute(self):
        self.log("execute, Thread execution loop active.", xbmc.LOGINFO)
        while not self.monitor.abortRequested():
            if self.service.pendingShutdown:
                self.log("execute, Shutdown/Abort requested. Exiting queue.", xbmc.LOGINFO)
                break
            elif self.service.pendingSuspend:
                self.log("execute, Suspend detected. Idling execution loop...", xbmc.LOGDEBUG)
                while self.service.pendingSuspend:
                    if self.service.pendingShutdown: break
                    self.monitor.waitForAbort(SERVICE_INTERVAL//2)
                continue
            elif self.service.pendingInterrupt:
                self.log("execute, Interrupt active. Breaking execution loop.", xbmc.LOGWARNING)
                break
            else:
                task = self.pop()
                if task is None:
                    self.monitor.waitForAbort(SERVICE_INTERVAL)
                    continue
                
                now = time.time()
                if task.execute_at and task.execute_at > now:
                    with self.lock:
                        self.push((task.func, task.args, task.kwargs), task.priority, 0, task.execute_at)
                    continue
                        
                self.log(f"execute, Dispatching {task.func.__name__} (Priority: {task.priority}) to ThreadPool.", xbmc.LOGDEBUG)
                try:
                    with timeit(task.func):
                        if self.useExecutor:
                            future = self.pool._executor.submit(task.func, *task.args, **task.kwargs)
                            future.add_done_callback(self._future_callback)
                        else: 
                            task.func(*task.args, **task.kwargs)
                except Exception as e: self.log(f"execute, failed! {e}", xbmc.LOGERROR)
        self.shutdown()
        self.log("execute, finished: shutting down...")

    def _future_callback(self, future, timeout=900):
        try: 
            future.result(float(timeout))
        except Exception as e: 
            self.log(f"_future_callback, failed! {e}", xbmc.LOGERROR)

    def shutdown(self, wait=False, cancel=True):
        try: 
            self.pool._executor.shutdown(wait=wait, cancel_futures=cancel)
            self.log("shutdown, pool")
        except Exception: pass
        try: self.cache.checkpoint()
        except Exception as e: self.log(f"cache checkpoint failed! {e}", xbmc.LOGERROR)
