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
    def __init__(self, fifo: bool=False, lifo: bool=False, priority: bool=False, delay: bool=False, timer: bool=False, service=None):
        self.service     = service
        self.fifo        = fifo
        self.lifo        = lifo
        self.priority    = priority
        self.delay       = delay
        self.timer       = timer
        
        self.lock        = Lock()
        self.min_heap    = []
        self.deque_queue = deque()
        self.nodes       = set()
        
        self.sync_queue  = deque()
        self.syncThread  = Thread(target=self._sync_worker)
        
        self.type        = self._getType()
        self.itemCount   = defaultdict(int)
        self.max_priority_seen = 0
        
        self.executor    = ThreadPoolExecutor(max_workers=THREAD_COUNT)
        self.popThread   = Thread(target=self._start)
        self.log(f"__init__, type = {self.type}, delay = {delay}, timer = {timer}")


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f'{self.__class__.__name__} [{self.type}]: {msg}', level)


    def _getType(self):
        if self.fifo:        return 'FIFO'
        elif self.lifo:      return 'LIFO'
        elif self.priority:  return 'PRIORITY'
        return 'UNKNOWN'
        
        
    def _clear(self):
        with self.lock:
            self.nodes.clear()
            self.deque_queue.clear()
            self.min_heap.clear()
            self.sync_queue.clear()
            self.itemCount.clear()
            self.max_priority_seen = 0
            
            
    def _use_executor(self):
        if SETTINGS.getSettingBool('Enable_Executor') or BUILTIN.isPlaying(): return True
        return len(self.sync_queue) >= QUEUE_CHUNK


    def _run(self):
        if self.service._interrupt() or self.service._suspend(): return
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
                self._sync_empty()
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
                epriority, _, epackage = item
                if package[0] == epackage[0]:
                    if priority < epriority:
                        self.min_heap.pop(idx)
                        heapq.heapify(self.min_heap) 
                        self.log(f"_exists, replacing queue: func = {func_name}, priority {epriority} => {priority}")
                        return False
                    return True
        elif timer:
            if func_name in self.nodes: 
                return True
            self.nodes.add(func_name)
        return False
             
             
    def _push(self, package: tuple, priority: int = 0, delay: int = 0, timer: int = 0):
        with self.lock:
            if priority == -1:
                self.max_priority_seen += 1
                priority = self.max_priority_seen
            else:
                if priority > self.max_priority_seen:
                    self.max_priority_seen = priority

            if delay:
                if not timer: timer = time.time()
                timer += delay
            
            if self.priority:
                if not self._exists(package, priority, timer):
                    try:
                        self.itemCount[priority] += 1
                        heapq.heappush(self.min_heap, (priority, self.itemCount[priority], package))
                    except Exception as e:
                        self.log(f"_push failed! {e}", xbmc.LOGFATAL)
                        return
            else:
                if timer and self._exists(package, priority, timer):
                    self.log(f"{package[0].__name__} exists")
                else:
                    self.deque_queue.append((package, priority, timer))
        
        if self.service._shutdown(CPU_CYCLE): 
            self._stop()
        elif (not self.service._interrupt() or self.service._suspend()) and not self.popThread.is_alive(): 
            self._run()


    def _start(self):
        while not self.service.monitor.abortRequested():
            if self.service._interrupt() or self.service._suspend():
                break
                
            package = None
            target_timer = 0
            
            with self.lock:
                if self.priority:
                    if self.min_heap:
                        _, _, package = heapq.heappop(self.min_heap)
                else:
                    if self.deque_queue:
                        item = self.deque_queue.popleft() if self.fifo else self.deque_queue.pop()
                        package, _, target_timer = item

            # Main pipeline ran out of tasks
            if package is None:
                if self._use_executor():
                    self._sync_empty()
                break
                
            try:
                if (self.timer or target_timer) and time.time() < target_timer:
                    self._push(package, timer=target_timer)
                    if self.service.monitor.waitForAbort(0.05): break
                else:
                    if target_timer:
                        with self.lock:
                            self.nodes.discard(package[0].__name__)
                            
                    self._exe(package[0], *package[1], **package[2])
                    
            except Exception as e:
                self.log(f"_start processing failure: {e}", xbmc.LOGERROR)
            if self.service.monitor.waitForAbort(CPU_CYCLE): break
        
        if self.service._shutdown(CPU_CYCLE):
            self._stop()
                
                
    def _stop(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.log("_stop, finished: shutting down...")