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


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def __start(self):
        if not self.popThread.is_alive():
            self.log("__starting popThread")
            self.popThread = Thread(target=self.__pop)
            self.popThread.daemon = True
            self.popThread.start()


    def __run(self, func, args=None, kwargs=None):
        self.log("__run, func = %s"%(func.__name__))
        try: return self.pool.executor(func, None, *args, *kwargs)
        except Exception as e: self.log("__run, func = %s failed! %s\nargs = %s, kwargs = %s"%(func.__name__,e,args,kwargs), xbmc.LOGERROR)

                
    def __exists(self, package):
        for idx, item in enumerate(self.min_heap):
            _,epriority,epackage = item
            if epackage == package[2]:
                if epriority >= package[1]: return True
                else:
                    try:
                        self.min_heap.pop(idx)
                        self.log("__exists, pop func = %s"%(epackage[0].__name__))
                    except: 
                        self.log("__exists, pop failed func = %s, idx = %s"%(epackage[0].__name__,idx))
                    return False
        return False
             
             
    def _push(self, package: tuple, priority: int=0, delay: int=0):
        node = LlNode(package, priority, delay)
        if   self.__exists((1,priority,package)): self.log("_push, func = %s exists; ignoring package"%(package[0].__name__))
        elif self.priority:
            self.qsize += 1
            item = (priority, package)
            self.itemCount[priority] += 1
            self.log("_push, func = %s, priority = %s"%(package[0].__name__,priority))
            heapq.heappush(self.min_heap, (item[0], self.itemCount[priority], item[1]))
        elif self.head:
            self.tail.next = node
            node.prev = self.tail
            self.tail = node
            self.log("_push, func = %s"%(package[0].__name__))
        else:
            self.head = node
            self.log("_push, func = %s"%(package[0].__name__))
            self.tail = node
            
        if not self.isRunning:
            self.__start()
    
    
    def __pop(self):
        self.isRunning = True
        while not self.service.monitor.abortRequested():
            if self.service.monitor.waitForAbort(.0001): 
                self.log("__pop, waitForAbort")
                break
            elif self.service._suspend():
                if self.service._interrupt(OVERLAY_DELAY): 
                    self.log("__pop, _interrupt")
                    break
                else: 
                    self.log("__pop, _suspend")
                    continue
            else:
                if not self.head and not self.priority:
                    self.log("__pop, The queue is empty!")
                    break
                    
                elif self.priority:
                    if not self.min_heap:
                        self.log("__pop, The priority queue is empty!")
                        break
                    min_num, _, package = heapq.heappop(self.min_heap)
                    self.qsize -= 1
                    self.__run(*package)
                        
                elif self.fifo or self.lifo:
                    curr_node = self.head if self.fifo else self.tail
                    if curr_node is None: break
                    package = curr_node.package
                    self.log('__pop, fifo/lifo package = %s'%(package))
                    next_node = curr_node.__next__ if self.fifo else curr_node.prev
                    if next_node:      next_node.prev = curr_node.prev if self.fifo else next_node.prev
                    if curr_node.prev: curr_node.prev.next = curr_node.__next__ if self.fifo else curr_node.prev
    
                    if self.fifo: self.head = next_node
                    else:         self.tail = next_node
                    
                    if not self.delay: package, self.__run(*package)
                    else:
                        popTimer = Timer(curr_node.wait, *package)
                        if popTimer.is_alive(): popTimer.join()
                        else:
                            popTimer.daemon = True
                            popTimer.start()
                else:
                    self.log("__pop, queue undefined!")
                    break
        self.isRunning = False
                
                
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