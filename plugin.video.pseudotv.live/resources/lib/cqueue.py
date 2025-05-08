#   Copyright (C) 2024 Lunatixz
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
from globals     import *
from pool        import ThreadPool
from collections import defaultdict

class LlNode:
    def __init__(self, package: tuple, priority: int=0, delay: int=0):
        self.prev      = None
        self.next      = None
        self.package   = package
        self.priority  = priority
        self.wait      = delay


class CustomQueue:
    isRunning = False
    
    def __init__(self, fifo: bool=False, lifo: bool=False, priority: bool=False, delay: bool=False, service=None):
        self.log("__init__, fifo = %s, lifo = %s, priority = %s, delay = %s"%(fifo, lifo, priority, delay))
        self.service   = service
        self.lock      = Lock()
        self.fifo      = fifo
        self.lifo      = lifo
        self.priority  = priority
        self.delay     = delay
        self.head      = None
        self.tail      = None
        self.qsize     = 0
        self.min_heap  = []
        self.itemCount = defaultdict(int)
        self.popThread = Thread(target=self.__pop)
        self.pool      = ThreadPool()
        self.executor  = SETTINGS.getSettingBool('Enable_Executors')


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def __manage(self, thread, target_function, name, daemon=True):
        if thread.is_alive():
            if hasattr(thread, 'cancel'): thread.cancel()
            try: thread.join()
            except Exception: pass
        
        new_thread = Thread(target=target_function)
        new_thread.name = name
        new_thread.daemon = daemon
        new_thread.start()
        return new_thread
        
        
    def __start(self):
        self.log("__starting popThread")
        self.popThread = self.__manage(self.popThread, self.__pop, "popThread")


    def __run(self, func, *args, **kwargs):
        self.log(f"__run, func = {func.__name__}, executor = {self.executor}")
        try:
            if self.executor:
                return self.pool.executor(func, None, *args, **kwargs)
            else:
                thread = Thread(target=func, args=args, kwargs=kwargs)
                thread.start()
        except Exception as e:
            self.log(f"__run, func = {func.__name__} failed! {e}\nargs = {args}, kwargs = {kwargs}", xbmc.LOGERROR)
               
               
    def __exists(self, priority, package):
        for idx, item in enumerate(self.min_heap):
            epriority,_,epackage = item
            if package == epackage:
                if priority < epriority:
                    try:
                        self.min_heap.pop(idx)
                        heapq.heapify(self.min_heap)  # Ensure heap property is maintained
                        self.log("__exists, replacing queue: func = %s, priority %s => %s"%(epackage[0].__name__,epriority,priority))
                    except: self.log("__exists, replacing queue: func = %s, idx = %s failed!"%(epackage[0].__name__,idx))
                else: return True
        return False
        
             
    def _push(self, package: tuple, priority: int = 0, delay: int = 0):
        node = LlNode(package, priority, delay)
        if self.priority:
            if not self.__exists(priority, package):
                try:
                    self.qsize += 1
                    self.itemCount[priority] += 1
                    self.log(f"_push, func = {package[0].__name__}, priority = {priority}")
                    heapq.heappush(self.min_heap, (priority, self.itemCount[priority], package))
                except Exception as e:
                    self.log(f"_push, func = {package[0].__name__} failed! {e}", xbmc.LOGFATAL)
        else:
            if self.head:
                self.tail.next = node
                node.prev = self.tail
                self.tail = node
            else:
                self.head = node
                self.tail = node
            self.log(f"_push, func = {package[0].__name__}")

        if not self.isRunning:
            self.log("_push, starting __pop")
            self.__start()
                 
                 
    def __process(self, node, fifo=True):
        package = node.package
        self.log(f"process_node, package = {package}")
        next_node = node.__next__ if fifo else node.prev
        if next_node: next_node.prev = None if fifo else next_node.prev
        if node.prev: node.prev.next = None if fifo else node.prev
        if fifo: self.head = next_node
        else:    self.tail = next_node
        return package
        
        
    def __pop(self):
        self.isRunning = True
        self.log("__pop, starting")
        self.executor = SETTINGS.getSettingBool('Enable_Executors')
        while not self.service.monitor.abortRequested():
            if self.service.monitor.waitForAbort(0.0001): 
                self.log("__pop, waitForAbort")
                break
            elif self.service._interrupt(): 
                self.log("__pop, _interrupt")
                break
            elif self.service._suspend():
                self.log("__pop, _suspend")
                self.service.monitor.waitForAbort(SUSPEND_TIMER)
                continue
            elif not self.head and not self.priority:
                self.log("__pop, The queue is empty!")
                break
            elif self.priority:
                if not self.min_heap:
                    self.log("__pop, The priority queue is empty!")
                    break
                else:
                    try: priority, _, package = heapq.heappop(self.min_heap)
                    except Exception as e: continue
                    self.qsize -= 1
                    self.__run(package[0],*package[1],**package[2])
            elif self.fifo or self.lifo:
                curr_node = self.head if self.fifo else self.tail
                if curr_node is None:
                    break
                else:
                    package = self.__process(curr_node, fifo=self.fifo)
                    if not self.delay: self.__run(*package)
                    else: timerit(curr_node.wait, [*package])
            else:
                self.log("__pop, queue undefined!")
                break
                
        self.isRunning = False
        self.log("__pop, finished: shutting down!")
                
                
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