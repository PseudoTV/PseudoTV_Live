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
from globals     import *
from pool        import ExecutorPool
from collections import defaultdict

class LPickle: #todo lazy pickle no pickles / or / don't store obj's in heaps.
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

    def serialize(self, heap, unsup=False):
        # heap is (priority, _, (obj, args, kwargs)) ex. [(1, 6, (<bound method Tasks.chkDiscovery of <tasks.Tasks object at 0x000002AD4A1B42F0>>, (), {}))]
        priority, _, (obj, args, kwargs) = heap
        if inspect.ismethod(obj) and getattr(obj, "__self__", None) is not None:
            inst = obj.__self__
            cls  = inst.__class__
            method_name = obj.__func__.__name__
            # get instance state
            if hasattr(inst, "__getstate__"): state = inst.__getstate__()   # getstate can be arbitrary; we'll pickle it
            else:                             state = getattr(inst, "__dict__", {})  # fall back to __dict__
            try: return {"priority": priority, "_": _, "callable": {"kind": "bound_method", "module": cls.__module__, "class": cls.__name__, "method": method_name, "state_blob": base64.b64encode(pickle.dumps(state)).decode("ascii"), }, "args": args, "kwargs": kwargs, }
            except:
                if    inspect.isfunction(obj): return {"priority": priority, "_": _, "callable": {"kind": "function"    , "module": obj.__module__, "name": obj.__name__,}, "args": args, "kwargs": kwargs,}
                else: self.log("serialize, Unsupported callable type: %s"%repr(obj))
        elif inspect.isfunction(obj): return {"priority": priority, "_": _, "callable": {"kind": "function", "module": obj.__module__, "name": obj.__name__,}, "args": args, "kwargs": kwargs,}
        else: self.log("serialize, Unsupported callable type: %s"%repr(obj))

    def deserialize(self, obj):
        priority = obj["priority"]; _ = obj["_"]
        call   = obj["callable"]
        args   = tuple(obj.get("args", ()))
        kwargs = dict(obj.get("kwargs", {}))
        if call["kind"] == "bound_method":
            # create instance without running __init__
            cls   = getattr(importlib.import_module(call["module"]), call["class"])
            inst  = cls.__new__(cls)
            state = pickle.loads(base64.b64decode(call["state_blob"].encode("ascii")))
            # restore state
            if hasattr(inst, "__setstate__"): inst.__setstate__(state)
            else: # assume state is a dict (from __dict__ fallback)
                if isinstance(state, dict): inst.__dict__.update(state)
                else: return self.log("deserialize, Cannot restore state for instance of %s"%cls)# unexpected; you may want to implement custom restoration
            return (priority, _, (getattr(inst, call["method"]), args, kwargs))
        elif call["kind"] == "function": return (priority, _, (getattr(importlib.import_module(call["module"]), call["name"]), args, kwargs))
        else: self.log("deserialize, Unknown callable kind: %s"%repr(call["kind"]))

    def get(self):
        def __deserialize(heaps=[]):
            for heap in heaps:
                if not heap: continue
                print('get',self.deserialize(heap))
                yield self.deserialize(heap)
        return list(filter(None,__deserialize((SETTINGS.getCacheSetting('min_heap',json_data=True) or []))))
           
    def set(self, min_heap=[]):
        def __serialize(min_heap):
            for heap in min_heap:
                if not heap: continue
                print('set',self.serialize(heap))
                yield self.serialize(heap)
        if min_heap: SETTINGS.setCacheSetting('min_heap', list(__serialize(min_heap)),json_data=True)


class LlNode:
    def __init__(self, package: tuple, priority: int=0, timer: int=0):
        self.prev      = None
        self.next      = None
        self.package   = package
        self.priority  = priority
        self.time      = timer


class CustomQueue:
    min_heap = []
    executor = False
    pool     = ExecutorPool()
    
    def __init__(self, fifo: bool=False, lifo: bool=False, priority: bool=False, delay: bool=False, timer: bool=False, service=None):
        self.isRunning = False
        self.service   = service
        self.fifo      = fifo
        self.lifo      = lifo
        self.priority  = priority
        self.delay     = delay
        self.timer     = timer
        self.head      = None
        self.tail      = None
        self.lPickle   = LPickle()
        self.min_heap  = self.lPickle.get()
        self.qsize     = 0
        self.nodes     = set()
        self.itemCount = defaultdict(int)
        self.popThread = Thread(target=self._start)
        self.executor  = SETTINGS.getSettingBool('Enable_Executors')
        self.log("__init__, fifo = %s, lifo = %s, priority = %s, delay = %s, timer = %s, min_heap = %s"%(fifo, lifo, priority, delay, timer,len(self.min_heap)))
 
 
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _clear(self):
        self.nodes     = set()
        self.head      = None
        self.tail      = None
        self.min_heap  = []
        self.itemCount = defaultdict(int)

        
    def _run(self):
        self.log("_run")
        if self.popThread.is_alive():
            if hasattr(self.popThread, 'cancel'): self.popThread.cancel()
            try: self.popThread.join()
            except: pass
        self.popThread = Thread(target=self._start)
        self.popThread.daemon = True
        self.popThread.start()


    def _wait(self, package):
        self.log(f"_wait, func = {package[0].__name__}")
        self._exe(package[0],*package[1],**package[2])
           

    def _exe(self, func, *args, **kwargs):
        self.log(f"_exe, func = {func.__name__}")
        try:
            if self.executor: self.pool.executor(func, None, *args, **kwargs)
            else:             self.pool.execute(func, *args, **kwargs)
        except Exception as e:
            self.log(f"_exe, func = {func.__name__} failed! {e}\nargs = {args}, kwargs = {kwargs}", xbmc.LOGERROR)
               
               
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
                    self.log(f"_push, func = {package[0].__name__}, priority = {priority}")
                    heapq.heappush(self.min_heap, (priority, self.itemCount[priority], package))
                    if not self.isRunning: self._run()
                except Exception as e:
                    self.log(f"_push, func = {package[0].__name__} failed! {e}", xbmc.LOGFATAL)
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
                self.log(f"_push, func = {package[0].__name__}, timer = {timer}")
                if not self.isRunning: self._run()
                

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
        self.executor  = SETTINGS.getSettingBool('Enable_Executors')
        while not self.service.monitor.abortRequested():
            if not self.head and not self.priority:
                self.log("_start, The queue is empty!")
                break
            elif self.service._shutdown(CPU_CYCLE): 
                self.log("_start, _shutdown")
                break
            elif self.service._interrupt(): 
                self.log("_start, _interrupt")
                break
            elif self.service._suspend(SUSPEND_TIMER): 
                self.log("_start, _suspend")
                continue
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
        self.lPickle.set(self.min_heap)
        self.log("_start, finished: shutting down...")
                
                
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