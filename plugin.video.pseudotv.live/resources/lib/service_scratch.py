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

import sys
import time
import heapq
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor

try:
    import xbmc
    import xbmcaddon
except ImportError:
    # Dummy mock implementations for off-Kodi testing environments
    class XBMC_Mock(object):
        LOGDEBUG = 0
        LOGINFO = 1
        LOGWARNING = 2
        LOGERROR = 3
        LOGFATAL = 4
        
        class Player(object):
            def __init__(self): pass
            def isPlaying(self): return False
            
        class Monitor(object):
            def __init__(self): pass
            def abortRequested(self): return False
            def waitForAbort(self, timeout):
                time.sleep(timeout)
                return False
                
        def log(self, msg, level=0):
            print(f"MOCK-KODI [{level}]: {msg}")
            
    xbmc = XBMC_Mock()
    
    class XBMCAddon_Mock(object):
        class Addon(object):
            def __init__(self, id=None): pass
            def getLocalizedString(self, string_id):
                return f"String_{string_id}"
                
    xbmcaddon = XBMCAddon_Mock()


# Priority Queue Tasks
class Task(object):
    """
    Represents a task containing the function to execute, arguments,
    and a priority rating.
    """
    def __init__(self, func, args=(), kwargs=None, priority=3):
        self.func = func
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}
        self.priority = priority
        self.is_cancelled = False

    def cancel(self):
        """Marks the task as cancelled/obsolete."""
        self.is_cancelled = True

    def __lt__(self, other):
        # Tie-breaker logic (won't be reached if counters are unique, but standard safety)
        return self.priority < other.priority


class PriorityQueueExecutor(object):
    """
    Thread-safe Priority Queue with duplicate task detection, keeping
    the duplicate with the highest priority (1 = Highest, 5 = Lowest).
    Uses ThreadPoolExecutor for background execution.
    """
    def __init__(self, service, max_workers=5):
        self.service = service
        self.max_workers = max_workers
        self.lock = threading.Lock()
        self.heap = []
        self.pending_tasks = {}  # task_key -> Task
        self.counter = 0  # Tie-breaker to prevent heapq comparing Tasks directly
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    def _get_task_key(self, func, args, kwargs):
        """Generates unique signature key for duplicate task matching."""
        sorted_kwargs = tuple(sorted(kwargs.items())) if kwargs else ()
        return (func.__name__, tuple(args), sorted_kwargs)

    def push(self, func, args=(), kwargs=None, priority=3):
        """
        Pushes a task with a priority between 1 (Highest) and 5 (Lowest).
        Checks if task signature is already queued; retains highest priority.
        """
        if kwargs is None:
            kwargs = {}
        priority = max(1, min(5, int(priority)))
        task_key = self._get_task_key(func, args, kwargs)
        
        with self.lock:
            if task_key in self.pending_tasks:
                existing_task = self.pending_tasks[task_key]
                # Lower numerical value means HIGHER priority (1 is highest, 5 is lowest)
                if priority < existing_task.priority:
                    self.service.log(f"PriorityQueue: Upgrading {func.__name__} priority from {existing_task.priority} to {priority}.", xbmc.LOGDEBUG)
                    existing_task.cancel()  # Cancel lower-priority duplicate
                    
                    new_task = Task(func, args, kwargs, priority)
                    self.pending_tasks[task_key] = new_task
                    self.counter += 1
                    heapq.heappush(self.heap, (priority, self.counter, new_task))
                else:
                    self.service.log(f"PriorityQueue: Task {func.__name__} ignored (already queued with higher/equal priority {existing_task.priority}).", xbmc.LOGDEBUG)
            else:
                new_task = Task(func, args, kwargs, priority)
                self.pending_tasks[task_key] = new_task
                self.counter += 1
                heapq.heappush(self.heap, (priority, self.counter, new_task))
                self.service.log(f"PriorityQueue: Pushed task {func.__name__} (Priority: {priority}).", xbmc.LOGDEBUG)

    def pop(self):
        """Pops the next valid (non-cancelled) task from queue."""
        with self.lock:
            while self.heap:
                _, _, task = heapq.heappop(self.heap)
                task_key = self._get_task_key(task.func, task.args, task.kwargs)
                
                if task.is_cancelled:
                    continue
                
                # Pop from mapping if it is the current active task version
                if self.pending_tasks.get(task_key) is task:
                    self.pending_tasks.pop(task_key, None)
                    
                return task
            return None

    def execute(self):
        """
        Processes queue tasks in ThreadPoolExecutor.
        Flow Control logic:
        - If interrupt flag is set: break execution loop.
        - If shutdown flag is set: stop processing immediately.
        - If suspend flag is set: idle and wait until suspend is lifted.
        """
        self.service.log("PriorityQueue: Thread execution loop active.", xbmc.LOGINFO)
        
        while True:
            # 1. Check for shutdown signal
            if self.service.shutdown_flag or self.service.monitor.abortRequested():
                self.service.log("PriorityQueue: Shutdown/Abort requested. Exiting queue.", xbmc.LOGINFO)
                break

            # 2. Check for suspend signal (idle until lifted or shutdown)
            if self.service.suspend_flag:
                self.service.log("PriorityQueue: Suspend detected. Idling execution loop...", xbmc.LOGDEBUG)
                while self.service.suspend_flag:
                    if self.service.shutdown_flag or self.service.monitor.abortRequested():
                        break
                    time.sleep(0.5)
                continue

            # 3. Check for interrupt signal (break execution)
            if self.service.interrupt_flag:
                self.service.log("PriorityQueue: Interrupt active. Breaking execution loop.", xbmc.LOGWARNING)
                break

            # 4. Fetch next task
            task = self.pop()
            if task is None:
                time.sleep(0.2)
                continue

            # 5. Submit to ThreadPool with exceptions caught
            self.service.log(f"PriorityQueue: Dispatching {task.func.__name__} (Priority: {task.priority}) to ThreadPool.", xbmc.LOGDEBUG)
            self.executor.submit(self._run_task_safely, task)

    def _run_task_safely(self, task):
        """Runs the task within a robust exception-catching wrapper."""
        try:
            task.func(*task.args, **task.kwargs)
        except Exception as e:
            self.service.log(f"PriorityQueue: Task {task.func.__name__} threw exception: {e}\n{traceback.format_exc()}", xbmc.LOGERROR)

    def shutdown(self):
        """Force stops executor threads."""
        self.executor.shutdown(wait=False)


# Kodi Player Class
class Player(xbmc.Player):
    def __init__(self, service):
        super(Player, self).__init__()
        self.service = service

    def onPlayBackStarted(self):
        self.service.log("Player: Playback started. Setting interrupt_flag.", xbmc.LOGDEBUG)
        self.service.interrupt_flag = True

    def onPlayBackStopped(self):
        self.service.log("Player: Playback stopped. Clearing interrupt_flag.", xbmc.LOGDEBUG)
        self.service.interrupt_flag = False

    def onPlayBackEnded(self):
        self.service.log("Player: Playback ended. Clearing interrupt_flag.", xbmc.LOGDEBUG)
        self.service.interrupt_flag = False

    def onPlayBackError(self):
        self.service.log("Player: Playback error. Clearing interrupt_flag.", xbmc.LOGERROR)
        self.service.interrupt_flag = False


# Kodi Monitor Class
class Monitor(xbmc.Monitor):
    def __init__(self, service):
        super(Monitor, self).__init__()
        self.service = service

    def onSettingsChanged(self):
        self.service.log("Monitor: Settings updated.", xbmc.LOGDEBUG)
        
    def onScreensaverActivated(self):
        self.service.log("Monitor: Screensaver activated. Suspending operations.", xbmc.LOGDEBUG)
        self.service.suspend_flag = True

    def onScreensaverDeactivated(self):
        self.service.log("Monitor: Screensaver deactivated. Resuming operations.", xbmc.LOGDEBUG)
        self.service.suspend_flag = False


# Kodi Service Class
class Service(object):
    def __init__(self):
        self.log_tag = "KodiService"
        
        # Core flags
        self.interrupt_flag = False
        self.suspend_flag = False
        self.shutdown_flag = False
        self.reboot_flag = False

        # Initialize sub-objects
        self.monitor = Monitor(service=self)
        self.player = Player(service=self)
        self.queue_executor = PriorityQueueExecutor(service=self)

    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(f"[{self.log_tag}] {msg}", level)

    def start(self):
        self.log("Service: Initializing main background thread and queue loop.", xbmc.LOGINFO)
        
        # Spin up queue execution thread
        queue_thread = threading.Thread(target=self.queue_executor.execute, name="PriorityQueueExecutorThread")
        queue_thread.daemon = True
        queue_thread.start()

        # Main service lifecycle checking both API shutdown and custom reboot flags
        while not self.monitor.abortRequested() and not self.reboot_flag:
            try:
                # Flow control action check
                if self.shutdown_flag:
                    self.log("Service: Shutdown flag detected. Initiating teardown.", xbmc.LOGINFO)
                    break

                if self.suspend_flag:
                    self.log("Service: Suspend flag active. Main service loop idling...", xbmc.LOGDEBUG)
                    time.sleep(1.0)
                    continue

                if self.interrupt_flag:
                    self.log("Service: Interrupt flag set. Main cycle paused, skipping routine steps.", xbmc.LOGDEBUG)
                    time.sleep(0.5)
                    continue

                # Run routine tasks/maintenance here when flags are clear
                self.log("Service: Executing routine tick task.", xbmc.LOGDEBUG)
                
                # Check for queue resume if we broke from interrupt earlier
                if not self.interrupt_flag and queue_thread and not queue_thread.is_alive() and not self.shutdown_flag:
                    self.log("Service: Restarting QueueExecutorThread after interrupt resolved.", xbmc.LOGINFO)
                    queue_thread = threading.Thread(target=self.queue_executor.execute, name="PriorityQueueExecutorThread")
                    queue_thread.daemon = True
                    queue_thread.start()

                # Loop cycle timing throttle (1 second sleep)
                if self.monitor.waitForAbort(1.0):
                    break

            except Exception as e:
                self.log(f"Service: Exception caught in main loop: {e}\n{traceback.format_exc()}", xbmc.LOGERROR)

        self.log("Service: Loop broken. Starting final teardown.", xbmc.LOGINFO)
        self.cleanup()

    def cleanup(self):
        """Teardown and safe shutdown of queue resources."""
        self.shutdown_flag = True
        self.queue_executor.shutdown()
        self.log("Service: Cleanup sequence finished successfully.", xbmc.LOGINFO)


if __name__ == "__main__":
    # Self-test simulation when run directly
    print("Initializing from-scratch service test...")
    
    # Mocking Service instance
    srv = Service()
    
    # Helper dummy tasks
    def task_alpha():
        print("Executing Task Alpha")
        
    def task_beta():
        print("Executing Task Beta")
        
    # Queueing duplicates with various priorities
    srv.queue_executor.push(task_alpha, priority=5)  # Lowest priority
    srv.queue_executor.push(task_alpha, priority=1)  # Upgrade to Highest priority
    srv.queue_executor.push(task_beta, priority=3)   # Medium priority
    srv.queue_executor.push(task_beta, priority=4)   # Lower priority (should be ignored)

    # Launch execution manually in background
    t = threading.Thread(target=srv.queue_executor.execute)
    t.daemon = True
    t.start()
    
    # Wait a second for processing to finish
    time.sleep(1.5)
    
    # Shutdown queue
    srv.cleanup()
    print("From-scratch service test completed.")
