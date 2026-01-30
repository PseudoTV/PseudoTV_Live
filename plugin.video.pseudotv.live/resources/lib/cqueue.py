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
import pickle

from globals             import *
from collections         import defaultdict
from concurrent.futures  import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

class LlNode(object):
    def __init__(self, package: tuple, priority: int=0, timer: int=0):
        self.prev      = None
        self.next      = None
        self.package   = package
        self.priority  = priority 
        self.time      = timer


class CustomQueue(object):
    futures = set()
    try:    min_heap = list(pickle.loads((SETTINGS.getCacheSetting('min_heap', revive=False) or b'')))
    except: min_heap = []
   
    def __init__(self, fifo: bool=False, lifo: bool=False, priority: bool=False, delay: bool=False, timer: bool=False, service=None):
        self.isWorking   = False
        self.isRunning   = False
        self.service     = service
        self.fifo        = fifo
        self.lifo        = lifo
        self.priority    = priority
        self.delay       = delay
        self.timer       = timer
        self.head        = None
        self.tail        = None
        self.qsize       = 0
        self.nodes       = set()
        self.type        = self._getType()
        self.itemCount   = defaultdict(int)
        self.useExecutor = REAL_SETTINGS.getSettingBool('Enable_Executor')
        self.executor    = ThreadPoolExecutor(max_workers=THREAD_COUNT)
        self.popThread   = Thread(target=self._start)
        self.wrkThread   = Thread(target=self._worker)
        self.log("__init__, type = %s, delay = %s, timer = %s, min_heap = %s"%(self.type, delay, timer, len(self.min_heap)))
        self.log(f"__init_,: ENABLE_EXECUTORS = {self.useExecutor}, CORES = {CPU_COUNT}, THREADS = {THREAD_COUNT}, QUEUE_CHUNK = {QUEUE_CHUNK}, CPU_CYCLE = {CPU_CYCLE}")


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s [%s]: %s'%(self.__class__.__name__,self.type,msg),level)


    def _getType(self):
        if   self.fifo:     return 'FIFO'
        elif self.lifo:     return 'LIFO'
        elif self.priority: return 'PRIORITY'
        else:               return 'UNKNOWN'
        

    def _clear(self):
        self.nodes     = set()
        self.head      = None
        self.tail      = None
        self.min_heap  = []
        self.itemCount = defaultdict(int)

        
    def _run(self):
        self.log("_run")
        self.useExecutor = REAL_SETTINGS.getSettingBool('Enable_Executor')
        if self.useExecutor:
            if self.wrkThread.is_alive():
                try:
                    self.wrkThread.join(0.1)  
                    self.log('_run, joining existing wrkThread')                          
                except: pass
            elif not self.service._interrupt() and not self.service._suspend():
                self.wrkThread = Thread(target=self._worker)
                self.wrkThread.daemon = True
                self.wrkThread.start()
          
        if self.popThread.is_alive():
            try:
                self.popThread.join(0.1)  
                self.log('_run, joining existing popThread')                          
            except: pass
        elif not self.service._interrupt() and not self.service._suspend():
            self.popThread = Thread(target=self._start)
            self.popThread.daemon = True
            self.popThread.start()
          
          
    def _worker(self, timeout=TIMEOUT_EXECUTOR):
        self.isWorking = True
        while not self.service.monitor.abortRequested():
            if self.service._interrupt() or self.service._suspend() or self.useExecutor:
                self.log("_worker, _interrupt/_suspend")
                break
            else:
                try:
                    for i in range(QUEUE_CHUNK):
                        if self.service._interrupt() or self.service._suspend():
                            self.log("_worker, _interrupt/_suspend")
                            break
                        elif len(self.futures) > THREAD_COUNT:
                            self.log(f"_worker, waiting for jobs to complete. Max thread count reached!")
                            done, self.futures = wait(self.futures, return_when=FIRST_COMPLETED) 
                            for future in done: yield future.result(timeout)
                        self.futures.add(self.executor.submit(func(*args, **kwargs)))
                        self.log(f"_worker [{i/QUEUE_CHUNK}] func = {func.__name__}")
                    for future in as_completed(self.futures): yield future.result(timeout)
                except Exception as e:
                    self.log("_worker, func = %s failed!\n%s\nargs = %s, kwargs = %s"%(func.__name__,e,args,kwargs), xbmc.LOGERROR)
                    yield func(*args, **kwargs)


    def _exe(self, func, *args, **kwargs):
        if self.useExecutor: 
            self.futures.add(self.executor.submit(func(*args, **kwargs)))
            self.log(f"_exe, func = {func.__name__} isWorking = {self.isWorking}")
        else: return func(*args, **kwargs)
            
            
    def _exists(self, package: tuple, priority: int = 0, timer: int = 0):
        if priority:
            for idx, item in enumerate(self.min_heap):
                epriority,_,epackage = item
                if package == epackage:
                    if priority < epriority:
                        try:
                            self.min_heap.pop(idx)
                            heapq.heapify(self.min_heap)  # Ensure heap property is maintained
                            self.log("_exists, replacing queue: func = %s, priority %s => %s"%(epackage[0].__name__,epriority,priority))
                        except: self.log("_exists, replacing queue: func = %s, idx = %s failed!"%(epackage[0].__name__,idx))
                    else: return True
        elif timer:
            for idx, func in enumerate(self.nodes):
                if func == package[0].__name__: return True
            self.nodes.add(package[0].__name__)
        return False
        
             
    def _push(self, package: tuple, priority: int = 0, delay: int = 0, timer: int = 0):
        if   priority == -1: priority = self.qsize + 1 #lazy FIFO
        elif delay: #lazy timer
            if not timer: timer = time.time()
            timer += delay
        
        if self.priority:
            if not self._exists(package, priority, timer):
                try:
                    self.qsize += 1
                    self.itemCount[priority] += 1
                    self.log(f"_push, func = {package[0].__name__}, priority = {priority}, isRunning = {self.isRunning}")
                    heapq.heappush(self.min_heap, (priority, self.itemCount[priority], package))
                except Exception as e:
                    self.log(f"_push, func = {package[0].__name__} failed! {e}", xbmc.LOGFATAL)
                    return
        else:
            if timer and self._exists(package, priority, timer): self.log(f"{package[0].__name__} exists")
            else:
                node = LlNode(package, priority, timer)
                if self.head:
                    self.tail.next = node
                    node.prev = self.tail
                    self.tail = node
                else:
                    self.head = node
                    self.tail = node
                self.log(f"_push, func = {package[0].__name__}, timer = {timer}, isRunning = {self.isRunning}")
        if not self.isRunning or not self.popThread.is_alive(): self._run()
                

    def _process(self, node, fifo=True):
        package = node.package
        next_node = node.next if fifo else node.prev
        if next_node: next_node.prev = None if fifo else next_node.prev
        if node.prev: node.prev.next = None if fifo else node.prev
        if fifo: self.head = next_node
        else:    self.tail = next_node
        return package
        
        
    def _start(self):
        self.isRunning = True
        while not self.service.monitor.abortRequested():
            if self.service._interrupt() or self.service._suspend():
                self.log("_start, _interrupt/_suspend")
                break
            elif not self.head and not self.priority:
                self.log("_start, The queue is empty!")
                break
            elif self.priority:
                if not self.min_heap:
                    self.log("_start, The priority queue is empty!")
                    break
                else:
                    try:
                        priority, _, package = heapq.heappop(self.min_heap)
                        self.qsize -= 1
                        self._exe(package[0],*package[1],**package[2])
                    except Exception as e: self.log("_start, failed! %s"%(e), xbmc.LOGERROR)
            elif self.fifo or self.lifo:
                curr_node = self.head if self.fifo else self.tail
                if curr_node is None: break
                else:
                    try:
                        package = self._process(curr_node, fifo=self.fifo)
                        if self.timer or curr_node.time:
                            if time.time() < curr_node.time: self._push(package, timer=curr_node.time)
                            else:
                                self.nodes.remove((package[0].__name__))
                                self._exe(package[0],*package[1],**package[2])
                        else: self._exe(package[0],*package[1],**package[2])
                    except Exception as e: self.log("_start, failed! %s"%(e), xbmc.LOGERROR)
            else:
                self.log("_start, queue undefined!")
                break
        
        self.isRunning = False
        if self.service._shutdown(CPU_CYCLE):
            self.log("_start, _shutdown")
            return self._stop()
                
                
    def _stop(self):
        # self._clear()
        self.executor.shutdown(wait=False, cancel_futures=True)
        # for item in self.min_heap:
            # print(item)
        # SETTINGS.setCacheSetting('min_heap', pickle.dumps(self.min_heap), checksum=ADDON_VERSION)
        self.log("_stop, finished: shutting down...")
                
                
# def quePriority(package: tuple, priority: int=0):
    # q_priority = CustomQueue(priority=True)
    # q_priority.log("quePriority")
    # q_priority._push(package, priority)
    
# def queFIFO(package: tuple, delay: int=0):
    # q_fifo = CustomQueue(fifo=True, delay=bool(delay))
    # q_fifo.log("queFIFO")
    # q_fifo._push(package, delay)
    
# def queLIFO(package: tuple, delay: int=0):
    # q_lifo = CustomQueue(lifo=True, delay=bool(delay))
    # q_lifo.log("queLIFO")
    # q_lifo._push(package, delay)
    
# def queThread(packages, delay=0):
    # q_fifo = CustomQueue(fifo=True)
    # q_fifo.log("queThread")

    # def thread_function(*package):
        # q_fifo._push(package)

    # for package in packages:
        # t = Thread(target=thread_function, args=(package))
        # t.daemon = True
        # t.start()