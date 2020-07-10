#   Copyright (C) 2020 Lunatixz
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

# https://bitbucket.org/jfunk/python-xmltv/src/default/README.txt
# https://github.com/kodi-pvr/pvr.iptvsimple/blob/Matrix/README.md#m3u-format-elements

# -*- coding: utf-8 -*-

from resources.lib.globals import *

class Worker:
    def __init__(self):
        self.myMonitor   = MY_MONITOR
        self.close       = False
        self.que         = Queue()
        self.queueThread = threading.Timer(0.5, self.runner)
        

    def add(self, que):
        log('Worker: adding %s %s'%(tuple(que)))
        self.que.put(que)


    def stop(self):
        log('Worker: stop')
        self.close = True


    def run(self):
        log('Worker: run')
        if self.queueThread.isAlive(): self.queueThread.cancel()
        self.queueThread = threading.Timer(0.5, self.runner)
        self.queueThread.name = "queueThread"
        self.queueThread.start()
        
        
    def runner(self, wait=10):
        log('Worker: runner')
        self.close = False
        while not self.myMonitor.abortRequested():
            func, args = self.que.get()
            log('Worker: runner, executing %s, args =%s'%(func,args))
            func(args)
            if self.que.empty() or self.close or self.myMonitor.waitForAbort(wait): 
                log('Worker: runner, stopping')
                break
            
if __name__ == '__main__': Worker()