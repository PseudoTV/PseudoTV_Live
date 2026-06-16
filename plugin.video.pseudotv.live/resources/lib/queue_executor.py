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

# -*- coding: utf-8 -*-
import threading
import queue
import time
import traceback
from concurrent.futures import Future
from typing import Callable, Any, Optional, Dict, Tuple

from variables import *
from logger import log
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError


class Service(object):
    player  = PLAYER()
    monitor = MONITOR()
    def _shutdown(self, wait=CPU_CYCLE) -> bool:
        return PROPERTIES.isPendingShutdown() or self.monitor.waitForAbort(wait)
    def _restart(self) -> bool:
        return PROPERTIES.isPendingRestart()
    def _interrupt(self) -> bool:
        any([PROPERTIES.isPendingSuspend(),BUILTIN.isSettingsOpened()])
    def _suspend(self) -> bool:
        return any([PROPERTIES.isPendingSuspend(),BUILTIN.isSettingsOpened()])
    def _sleep(self, wait=CPU_CYCLE):
        while not self.monitor.abortRequested() and wait > 0:
            if any([self.monitor.waitForAbort(CPU_CYCLE), self._interrupt()]):
                return True
            wait -= CPU_CYCLE
        return False
    
    
class QueueThreadPoolExecutor:
    """
    A custom thread pool executor that integrates with the existing queue system
    to optimize channel building and task execution.
    
    This executor manages a queue of tasks and a thread pool to execute them,
    providing better control over task scheduling and resource utilization.
    """
    
    def __init__(self, service=None, max_workers: int = None):
        if service is None: service = Service()
        if max_workers is None: max_workers = THREAD_WORKERS
        self.service     = service
        self.max_workers = max_workers
        self._threads = []
        self._task_queue = queue.PriorityQueue()
        self._shutdown = threading.Event()
        self._active_tasks = {}
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self.log(f"QueueThreadPoolExecutor initialized with max_workers={max_workers}")
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG) -> None:
        return log(f"{self.__class__.__name__}: {msg}", level)
        
    def submit(self, func: Callable, *args, **kwargs) -> Future:
        task_id = f"{func.__name__}_{time.time()}"
        
        with self._lock:
            future = Future()
            self._active_tasks[task_id] = (future, func, args, kwargs)
            self._task_queue.put((0, time.time(), task_id, future, func, args, kwargs))
            self._condition.notify()
            
        self.log(f"Submitted task: {func.__name__} (ID: {task_id})")
        return future
        
    def _worker(self) -> None:
        while not self.service.monitor.abortRequested() and not self._shutdown.is_set():
            try:
                with self._condition:
                    while not self.service.monitor.abortRequested() and self._task_queue.empty() and not self._shutdown.is_set():
                        self._condition.wait(timeout=0.1)
                    
                    if self._shutdown.is_set(): break
                    if self._task_queue.empty(): continue
                    priority, execute_at, task_id, future, func, args, kwargs = self._task_queue.get()
                execute_at = time.time()
                
                try:
                    self.log(f"Worker executing task: {func.__name__} (ID: {task_id})")
                    result = func(*args, **kwargs)
                    
                    with self._lock:
                        future.set_result(result)
                        
                except Exception as e:
                    self.log(f"Worker failed to execute task {func.__name__} (ID: {task_id}): {e}", xbmc.LOGERROR)
                    with self._lock:
                        future.set_exception(e)
                        
                finally:
                    with self._lock:
                        self._active_tasks.pop(task_id, None)
            except Exception as e:
                self.log(f"Worker thread error: {e}", xbmc.LOGERROR)
                
    def start(self) -> None:
        for i in range(self.max_workers):
            thread = threading.Thread(target=self._worker, name=f"QueueThreadPoolExecutor-{i}")
            thread.daemon = True
            thread.start()
            self._threads.append(thread)
        self.log(f"Started {len(self._threads)} worker threads")
        
    def shutdown(self, wait: bool = True) -> None:
        self.log(f"Shutting down executor (wait={wait})")
        self._shutdown.set()
        
        with self._condition:
            self._condition.notify_all()
            
        if wait:
            for thread in self._threads:
                thread.join(timeout=1.0)
        self.log("Executor shutdown complete")
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown(wait=True)
        
    def __del__(self):
        self.shutdown(wait=False)
        
    def is_shutdown(self) -> bool:
        return self._shutdown.is_set()
        
    def active_tasks_count(self) -> int:
        with self._lock:
            return len(self._active_tasks)
            
    def pending_tasks_count(self) -> int:
        return self._task_queue.qsize()
