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
from globals             import *
from fileaccess          import FileAccess
from concurrent.futures  import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

class CustomQueue(object):
    def __init__(self, service=None):
        self.service        = service
        self.lock           = Lock()
        self.min_heap       = []
        self.itemCount      = defaultdict(int)
        self.maxPriority    = 0
        self.useExecutor    = SETTINGS.getSettingBool('Enable_Executor')
        self.active_tasks   = {}
        self.executor       = ThreadPoolExecutor(max_workers=THREAD_WORKERS)
        self.popThread      = None

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f'{self.__class__.__name__}: {msg}', level)
        
    def _clear(self):
        with self.lock:
            self.min_heap.clear()
            self.itemCount.clear()
            self.maxPriority = 0
            
    def _use_executor(self):
        if self.useExecutor or BUILTIN.isPlaying(): return True
        return False

    def _run(self):
        if self.service._interrupt() or self.service._suspend(): return
        self.useExecutor = SETTINGS.getSettingBool('Enable_Executor')
        if self.popThread is None or not self.popThread.is_alive():
            self.log(f'_run, Spin up new worker thread. useExecutor = {self.useExecutor}')
            self.popThread = Thread(target=self._start)
            self.popThread.daemon = True
            self.popThread.start()
            
    def _exe(self, package, task_key, task_id):
        try:
            func, args, kwargs = package
            if self._use_executor():
                self.log(f"_exe, Routing task concurrently to Executor: {func.__name__}")
                future = self.executor.submit(func, *args, **kwargs)
                future.add_done_callback(lambda fut: self._future_callback(fut, task_key, task_id))
            else:
                self.log(f"_exe, Routing task sequentially on worker thread: {func.__name__}")
                func(*args, **kwargs)
        except Exception as e: self.log(f"_exe, Execution processing failure: {e}", xbmc.LOGERROR)
        finally:
            with self.lock:
                if self.active_tasks.get(task_key, (None,))[0] == task_id:
                    self.active_tasks.pop(task_key, None)


    def _future_callback(self, future, task_key, task_id):
        try: future.result() 
        except Exception as e: self.log(f"_future_callback failed!, Background worker thread execution threw error: {e}", xbmc.LOGERROR)
        finally:
            with self.lock:
                if self.active_tasks.get(task_key, (None,))[0] == task_id:
                    self.active_tasks.pop(task_key, None)
            
    def _exists(self, task_key: str, requested_priority: int):
        if task_key in self.active_tasks:
            existing_task_id, existing_priority = self.active_tasks[task_key]
            if requested_priority == -1 or requested_priority >= existing_priority:
                self.log(f"_exists, dropping duplicate/delayed task signature: {task_key} existing priority {existing_priority}, requested {requested_priority})")
                return True, None
            else:
                self.log(f"_exists, overriding priority for task signature: {task_key} ({existing_priority} => {requested_priority})")
                return False, existing_task_id
        return False, None
                    
    def _push(self, package: tuple, priority: int = 0, delay: int = 0, timer: int = 0):
        self.log(f"_push, package = {package[0].__name__}, priority = {priority}, delay = {delay}, timer = {timer}, isAlive = {self.popThread.is_alive() if self.popThread else False}")
        with self.lock:
            now = time.time()
            if   timer: execute_at = timer
            elif delay: execute_at = now + delay
            else:       execute_at = now

            priority_penalty = float(priority) * 2.0
            scheduling_score = execute_at + priority_penalty
            task_key = self._getKey(package)
            should_drop, old_task_id = self._exists(task_key, priority)
            if not should_drop:
                if priority == -1:
                    self.maxPriority += 1
                    priority = self.maxPriority
                elif priority > self.maxPriority:
                    self.maxPriority = priority

                try:
                    self.itemCount[priority] += 1
                    unique_task_id = f"{package[0].__name__}_{now}_{self.itemCount[priority]}"
                    self.active_tasks[task_key] = (unique_task_id, priority)
                    
                    heapq.heappush(self.min_heap, (scheduling_score, execute_at, self.itemCount[priority], unique_task_id, task_key, package))
                except Exception as e:
                    self.log(f"_push, failed! {e}", xbmc.LOGFATAL)
                    return
                
        if self.service._shutdown(CPU_CYCLE): 
            self._stop()
        else:
            is_paused = self.service._interrupt() or self.service._suspend()
            is_worker_dead = self.popThread is None or not self.popThread.is_alive()
            if not is_paused and is_worker_dead: 
                self._run()

    def _start(self):
        is_idle = False
        while not self.service.monitor.abortRequested():
            if self.service._interrupt() or self.service._suspend():
                break
                
            package = None
            task_key = None
            task_id = None
            now = time.time()
            sleep_duration = None
            
            with self.lock:
                while self.min_heap:
                    priority, execute_at, count, task_id_peek, task_key_peek, peek_package = self.min_heap[0]
                    current_active = self.active_tasks.get(task_key_peek)
                    
                    if current_active is None or current_active[0] != task_id_peek:
                        heapq.heappop(self.min_heap) 
                        continue
                        
                    if execute_at > now:
                        sleep_duration = min(execute_at - now, 0.5)
                        break
                        
                    _, _, _, task_id, task_key, package = heapq.heappop(self.min_heap)
                    break

            if package is None:
                with self.lock:
                    has_items = len(self.min_heap) > 0
                
                if has_items and sleep_duration:
                    if self.service.monitor.waitForAbort(sleep_duration): break
                elif has_items:
                    if self.service.monitor.waitForAbort(0.1): break
                else:
                    if not is_idle:
                        try: SETTINGS.cache.cache.checkpoint()
                        except Exception as e: self.log(f"cache checkpoint failed! {e}", xbmc.LOGERROR)
                        is_idle = True
                    if self.service.monitor.waitForAbort(SERVICE_INTERVAL): break
                continue
                    
            is_idle = False
            self._exe(package, task_key, task_id)
            if not self._use_executor():
                cooldown = 1.0 if BUILTIN.isPlaying() else CPU_CYCLE
                if self.service.monitor.waitForAbort(max(cooldown, 0.005)): break
                
        if self.service._shutdown(CPU_CYCLE):
            self._stop()
                
    def _stop(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.log("_stop, finished: shutting down...")
        
    def _getKey(self, package: tuple) -> str:
        func, args, kwargs = package
        sorted_kwargs = tuple(sorted(kwargs.items()))
        return f"{func.__name__}|args:{args}|kwargs:{sorted_kwargs}"