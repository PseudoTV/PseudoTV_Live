#   Copyright (C) 2022 Lunatixz
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

from globals    import *
from threading  import Thread, Event
from queue      import Empty, PriorityQueue

class Consumer():
    queue = PriorityQueue()
    
    def __init__(self, service):
        self.log('__init__')
        self.service = service
        self.thread  = Thread(target=self._run, daemon=True, name="Consumer")
        self.thread.start()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _run(self):
        self.log('_run, starting...')
        while not self.service.monitor.abortRequested():
            try:
                priority, randomheap, package  = self.queue.get(block=False)
                func, args, kwargs = package
                try: 
                    self.log("_run, priority = %s, func = %s"%(priority,func.__name__))
                    func(*args,**kwargs)
                except Exception as e:
                    self.log("_run, func = %s failed! %s"%(func.__name__,e), xbmc.LOGERROR)
            except Empty:
                if self.service.monitor.waitForAbort(5): break
                else: continue
                
            if self.service.monitor.waitForAbort(1) or self.service.monitor.chkRestart() or isClient(): 
                self.log('_run, interrupted')
                break
        self.log('_run, stopping...')