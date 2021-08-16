  # Copyright (C) 2021 Lunatixz


# This file is part of PseudoTV Live.

# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
import sys, time, re, os, traceback

from kodi_six                  import xbmc, xbmcaddon
from itertools                 import repeat
from functools                 import partial, wraps
from threading                 import Thread
from queue                     import Queue, Empty

ADDON_ID      = 'plugin.video.pseudotv.live'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')

def timeit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        if not REAL_SETTINGS.getSetting('Enable_Debugging') == "true": return
        start_time = time.time()
        result     = method(*args, **kwargs)
        end_time   = time.time()
        log('%s => %s ms'%(method.__qualname__.replace('.',': '),(end_time-start_time)*1000))
        return result
    return wrapper
    
def log(msg, level=xbmc.LOGDEBUG):
    if not REAL_SETTINGS.getSetting('Enable_Debugging') == "true" and level != xbmc.LOGERROR: return
    if not isinstance(msg,str): msg = str(msg)
    if level == xbmc.LOGERROR: msg = '%s\n%s'%((msg),traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)
    
class ThreadPool:
    def __init__(self, cpuCount=4):
        self.cpuCount = cpuCount
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def close(self):
        ...
        
        
    def join(self):
        ...


    def imap(self, func, items=[], chunksize=1):
        queue = Queue()                     
        threadCount = self.cpuCount
        for idx, item in enumerate(items): queue.put((idx, item))
            
        results = {}
        errors  = {}
        class Worker(Thread):
            monitor = xbmc.Monitor()
            
            def run(self):
                while not self.monitor.abortRequested() and not errors:
                    try:
                        idx, item = queue.get(block=False)
                        try: 
                            results[idx] = func(item)
                            # if self.monitor.waitForAbort(.001): break # unnecessary slows down func.  
                        except Exception as e: errors[idx] = sys.exc_info()
                    except Empty: break

        threads = [Worker() for _ in range(threadCount)]
        for t in threads: t.start()
        for t in threads: t.join()

        if errors:
            if len(errors) > 1: self.log("imap, multiple errors: %d:\n%s"%(len(errors), errors), xbmc.LOGERROR)
            item_i = min(errors.keys())
            type, value, tb = errors[item_i]
            self.log("imap, exception on item %s:\n%s"%(item_i, "\n".join(traceback.format_tb(tb))), xbmc.LOGERROR)
            raise value
        return (results[idx] for idx in range(len(results)))