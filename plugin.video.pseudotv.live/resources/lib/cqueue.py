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
        self.service     = service
        self.lock        = Lock()
        self.min_heap    = []
        self.nodes       = set()
        self.itemCount   = defaultdict(int)
        self.maxPriority = 0
        self.useExecutor = SETTINGS.getSettingBool('Enable_Executor')
        
        self.sync_queue  = deque()
        self.syncThread  = Thread(target=self._sync_worker)
        self.executor    = ThreadPoolExecutor(max_workers=THREAD_WORKERS)
        self.popThread   = Thread(target=self._start)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f'{self.__class__.__name__}: {msg}', level)

        
    def _clear(self):
        with self.lock:
            self.nodes.clear()
            self.min_heap.clear()
            self.sync_queue.clear()
            self.itemCount.clear()
            self.maxPriority = 0
            
            
    def _use_executor(self):
        if self.useExecutor or BUILTIN.isPlaying(): return True
        return False


    def _run(self):
        if self.service._interrupt() or self.service._suspend(): return
        self.useExecutor = SETTINGS.getSettingBool('Enable_Executor')
        if not self._use_executor():
            if not self.syncThread.is_alive():
                self.syncThread = Thread(target=self._sync_worker)
                self.syncThread.daemon = True
                self.syncThread.start()
        if not self.popThread.is_alive():
            self.popThread = Thread(target=self._start)
            self.popThread.daemon = True
            self.popThread.start()


    def _exe(self, func, *args, **kwargs):
        useExecutor = self._use_executor()
        self.log(f"_exe, func = {func.__name__}, useExecutor = {useExecutor}")
        if useExecutor:
            if len(self.sync_queue) > 0: self._sync_empty()
            try:
                future = self.executor.submit(func, *args, **kwargs)
                future.add_done_callback(self._future_callback)
            except Exception as e:
                self.log(f"Failed to submit future task: {e}", xbmc.LOGERROR)
        else:
            with self.lock:
                self.sync_queue.append((func, args, kwargs))


    def _sync_empty(self):
        self.log(f"Threshold breached ({len(self.sync_queue)} items). Flushing sync_queue to executor pool.")
        while not self.service.monitor.abortRequested():
            try:
                with self.lock:
                    if not self.sync_queue: break
                    func, args, kwargs = self.sync_queue.popleft()
                future = self.executor.submit(func, *args, **kwargs)
                future.add_done_callback(self._future_callback)
            except IndexError: break
            except Exception as e: self.log(f"Failed offloading backlogged task to pool: {e}", xbmc.LOGERROR)


    def _sync_worker(self):
        """Processes tasks sequentially. Shuts down if Executor mode is activated."""
        while not self.service.monitor.abortRequested():
            if self.service._interrupt() or self.service._suspend(): break
            if self._use_executor():
                if len(self.sync_queue) > 0: self._sync_empty()
                break
                
            sync_task = None
            if self.sync_queue: 
                with self.lock:
                    if self.sync_queue: 
                        sync_task = self.sync_queue.popleft()
                    
            if sync_task is None:
                if self.service.monitor.waitForAbort(0.05): break
                continue
            try: 
                func, args, kwargs = sync_task
                func(*args, **kwargs)
            except Exception as e:
                self.log(f"Synchronous execution failed: {e}", xbmc.LOGERROR)
            if self.service.monitor.waitForAbort(CPU_CYCLE): break


    def _future_callback(self, future):
        try:
            future.result() 
        except Exception as e:
            self.log(f"Background worker thread execution threw error: {e}", xbmc.LOGERROR)
            
            
    def _exists(self, package: tuple, priority: int = 0, timer: int = 0):
        func_name = package[0].__name__
        if priority:
            for idx, item in enumerate(self.min_heap):
                epriority, ecount, eexecute_at, epackage = item
                if epackage[0].__name__ == func_name:
                    if priority < epriority:
                        self.min_heap.pop(idx)
                        heapq.heapify(self.min_heap) 
                        self.log(f"_exists, replacing queue item: func = {func_name}, priority {epriority} => {priority}")
                        return False
                    else:
                        self.log(f"_exists, dropping duplicate task: func = {func_name} (existing priority {epriority} <= new {priority})")
                        return True
                    
                    
    def _push(self, package: tuple, priority: int = 0, delay: int = 0, timer: int = 0):
        self.log(f"_push package = {package[0].__name__}, priority = {priority}, delay = {delay}, timer = {timer}")
        with self.lock:
            if   timer: execute_at = timer
            elif delay: execute_at = time.time() + delay
            else:       execute_at = 0.0

            if priority == -1:
                self.maxPriority += 1
                priority = self.maxPriority
            else:
                if priority > self.maxPriority:
                    self.maxPriority = priority

            if not self._exists(package, priority):
                try:
                    self.itemCount[priority] += 1
                    heapq.heappush(self.min_heap, (priority, self.itemCount[priority], execute_at, package))
                except Exception as e:
                    self.log(f"_push failed! {e}", xbmc.LOGFATAL)
                    return
                
        if self.service._shutdown(CPU_CYCLE): self._stop()
        elif (not self.service._interrupt() or self.service._suspend()) and not self.popThread.is_alive(): 
            self._run()


    def _start(self):
        while not self.service.monitor.abortRequested():
            if self.service._interrupt() or self.service._suspend():
                self.log("_start, _interrupt/_suspend")
                break
                
            package = None
            now = time.time()
            with self.lock:
                if self.min_heap:
                    sorted_heap_items = sorted(enumerate(self.min_heap), key=lambda x: (x[1][0], x[1][1]))
                    target_idx = None
                    for original_idx, (priority, count, execute_at, peek_package) in sorted_heap_items:
                        if execute_at <= now:
                            target_idx = original_idx
                            break

                    if target_idx is not None:
                        _, _, _, package = self.min_heap.pop(target_idx)
                        heapq.heapify(self.min_heap)  # Repair the heap structure
                    else: pass

            if package is None:
                if self._use_executor() and len(self.sync_queue) > 0:
                    self._sync_empty()

                with self.lock:
                    has_items = len(self.min_heap) > 0

                if has_items:
                    # Items exist but all are future-delayed. Sleep briefly and check again.
                    if self.service.monitor.waitForAbort(0.05): break
                    continue
                else: break

            try:
                self._exe(package[0], *package[1], **package[2])
            except Exception as e:
                self.log(f"_start processing failure: {e}", xbmc.LOGERROR)

            if self.service.monitor.waitForAbort(CPU_CYCLE): break
        if self.service._shutdown(CPU_CYCLE):
            self._stop()
                
                
    def _stop(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.log("_stop, finished: shutting down...")