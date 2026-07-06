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
        self.task_key     = None

    def cancel(self):
        self.is_cancelled = True

    def __lt__(self, other):
        return self.priority < other.priority

class CustomQueue(object):
    AGE_BOOST_INTERVAL = 20  # seconds between priority aging ticks
    AGE_BOOST_STEP     = 1.0 # priority levels boosted per interval
    MAX_HEAP_SIZE      = 500 # hard limit to prevent memory growth
    LOG_THROTTLE       = 5.0 # seconds between repeated log messages per task

    def __init__(self, service, workers=THREAD_WORKERS):
        self.service  = service
        self.monitor  = service.monitor
        self.cache    = service.cache
        self.pool     = service.pool
        self.lock     = RLock()
        self.wake     = Event()
        
        self.heap     = []
        self.pending  = {}
        self.running  = {}
        self.counter  = 0
        
        self.useExecutor = Globals.settings.getSettingBool('Enable_Executor')
        self.queueThread = Thread(target=self.execute, name=f"{ADDON_ID}.priorityQUE")
        
    def log(self, msg, level=xbmc.LOGDEBUG, throttle=0):
        LOG(f'{self.__class__.__name__}: {msg}', level, throttle=throttle)
        
    def _freeze(self, obj):
        if isinstance(obj, list): return tuple(self._freeze(item) for item in obj)
        if isinstance(obj, dict): return tuple(sorted((k, self._freeze(v)) for k, v in obj.items()))
        if isinstance(obj, set):  return frozenset(self._freeze(item) for item in obj)
        return obj
        
    def _get_task_key(self, func, args, kwargs):
        return (func.__name__, tuple(self._freeze(arg) for arg in args), tuple(sorted((k, self._freeze(v)) for k, v in kwargs.items())) if kwargs else ())

    def _fmt_args(self, args, kwargs, maxlen=60):
        parts = []
        for a in args[:3]:
            s = repr(a)
            parts.append(s if len(s) < 20 else s[:17] + '...')
        for k, v in list(kwargs.items())[:3]:
            s = f'{k}={repr(v)}'
            parts.append(s if len(s) < 25 else s[:22] + '...')
        sig = ', '.join(parts)
        if len(sig) > maxlen: sig = sig[:maxlen-3] + '...'
        return f'({sig})' if sig else '()'

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
                if task_key in self.running:
                    self.log(f"push, {func.__name__} skipped (running, dispatched {time.time() - self.running[task_key].created_at:.1f}s ago).", throttle=self.LOG_THROTTLE)
                elif task_key in self.pending:
                    existing_task = self.pending[task_key]
                    if priority < existing_task.priority:
                        self.log(f"push, Upgrading {func.__name__} priority from {existing_task.priority} to {priority}.", xbmc.LOGDEBUG)
                        existing_task.cancel()
                        new_task = Task(func, args, kwargs, priority, execute_at)
                        self.pending[task_key] = new_task
                        self.counter += 1
                        heapq.heappush(self.heap, (self._compute_score(new_task), self.counter, new_task))
                    else:
                        self.log(f"push, {func.__name__} ignored (queued priority {existing_task.priority} <= {priority}).", throttle=self.LOG_THROTTLE)
                else:
                    if len(self.heap) >= self.MAX_HEAP_SIZE: self._evict_lowest()
                    new_task = Task(func, args, kwargs, priority, execute_at)
                    new_task.task_key = task_key
                    self.pending[task_key] = new_task
                    self.counter += 1
                    heapq.heappush(self.heap, (self._compute_score(new_task), self.counter, new_task))
                    self.log(f"push, {func.__name__}{self._fmt_args(args, kwargs)} (Priority: {priority}).", xbmc.LOGDEBUG)

        if not self.monitor.abortRequested() and not self.queueThread.is_alive():
            self.useExecutor = Globals.settings.getSettingBool('Enable_Executor')
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
                task.task_key = task_key
                self.running[task_key] = task
                return task
            return None

    def _finish(self, task):
        if task and task.task_key:
            with self.lock:
                self.running.pop(task.task_key, None)

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
                now = time.time()
                with self.lock:
                    ready = False
                    if self.heap:
                        _, _, top_task = self.heap[0]
                        if top_task.execute_at and top_task.execute_at > now:
                            wait = min(top_task.execute_at - now, SERVICE_INTERVAL)
                        else:
                            ready = True
                            wait = 0
                    else:
                        wait = SERVICE_INTERVAL
                
                if not ready:
                    if wait > 0: self.monitor.waitForAbort(wait)
                    continue
                
                task = self.pop()
                if task is None:
                    self.monitor.waitForAbort(SERVICE_INTERVAL)
                    continue
                
                self.log(f"execute, {task.func.__name__} (Priority: {task.priority}).", xbmc.LOGDEBUG)
                try:
                    if self.useExecutor:
                        future = self.pool._executor.submit(task.func, *task.args, **task.kwargs)
                        future.add_done_callback(lambda f, t=task: self._finish(t))
                        future.add_done_callback(self._future_callback)
                    else: 
                        task.func(*task.args, **task.kwargs)
                except Exception as e: self.log(f"execute, failed! {e}", xbmc.LOGERROR)
                finally:
                    if not self.useExecutor:
                        self._finish(task)
        self.shutdown()
        self.log("execute, finished: shutting down...")

    def _future_callback(self, future, timeout=900):
        if timeout is None: timeout = int(REAL_SETTINGS.getSetting('API_Timeout') or "10")
        try: 
            future.result(float(timeout))
        except Exception as e: 
            self.log(f"_future_callback, failed! {e}", xbmc.LOGERROR)

    def shutdown(self, wait=False, cancel=True):
        try: 
            self.pool._executor.shutdown(wait=wait, cancel_futures=cancel)
            self.log("shutdown, pool")
        except Exception as e: self.log("shutdown failed: %s" % e, xbmc.LOGDEBUG)
        try: self.cache.checkpoint()
        except Exception as e: self.log(f"cache checkpoint failed! {e}", xbmc.LOGERROR)
