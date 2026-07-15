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
# GNU General Fonte Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
# -*- coding: utf-8 -*-
import sys, traceback

def _excepthook(exc_type, exc_value, exc_tb):
    """Global exception handler - logs errors instead of crashing Kodi."""
    if exc_type is SystemExit: return
    tb = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        from constants import LOG, ADDON_ID
        LOG(f'{ADDON_ID}: Unhandled exception:\n{tb}', 3)  # LOGERROR
    except Exception:
        sys.stderr.write(f'PseudoTV Live unhandled: {tb}\n')

sys.excepthook = _excepthook

# --- imports needed BEFORE globals to define Service class early ---
from kodi_six  import xbmc, xbmcgui
from threading import Thread
from typing    import Any, Optional
from variables import *

def _getProp(key: str, default: Any = None) -> Any:
    return xbmcgui.Window(10000).getProperty(key) or default
       
class _Service(object):
    """Lightweight dummy service - singleton, one xbmc.Monitor() per process."""
    _instance        = None
    pendingShutdown  = False
    pendingRestart   = False
    pendingInterrupt = False
    pendingSuspend   = False
    
    def __new__(cls) -> '_Service':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'): return
        self._initialized = True
        from jsonrpc import JSONRPC
        from pool    import ExecutorPool
        from cache   import Cache
        self.player           = PLAYER()
        self.monitor          = MONITOR()
        self.pool             = ExecutorPool()
        self.cache            = Cache(mem_cache=True)
        self.jsonRPC          = JSONRPC(service=self)
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)
        
    def _shutdown(self, wait: Optional[float] = None) -> bool:
        if wait is None: wait = SERVICE_INTERVAL
        return any((_getProp('%s.pendingShutdown'%(ADDON_ID),'false') == 'true', self.monitor.waitForAbort(wait)))
       
    def interrupt(self) -> bool:
        return _getProp('%s.pendingInterrupt'%(ADDON_ID),'false') == 'true'
        
    def suspend(self) -> bool:
        return _getProp('%s.pendingSuspend'%(ADDON_ID),'false') == 'true'


    def sleep(self, wait: Optional[float] = None) -> bool:
        """Blocks until shutdown/interrupt, returns True on completion."""
        while not self.monitor.abortRequested():
            if   self.interrupt():     break
            elif self._shutdown(wait): break
        return True

def _start():
    """Main entry point - runs the service loop and handles restarts."""
    service = None
    try:
        from services import Service
        service = Service()
        monitor = service.monitor
        while not monitor.abortRequested():
            restart = service._start()
            if monitor.waitForAbort(CPU_CYCLE) or not restart: 
                Globals.dialog.notificationWait(LANGUAGE(32141), usethread=True)
                service.log("_start, shutting down (restart=%s, abort=%s)" % (restart, monitor.abortRequested()), xbmc.LOGINFO)
                break
            elif restart:
                Globals.dialog.notificationWait(LANGUAGE(32124))
                service.log("_start, restarting service loop", xbmc.LOGINFO)
    except Exception as e:
        if service: service.log("_start, failed! %s" % (e), xbmc.LOGERROR)
        else: LOG("_start, import failed: %s" % (e), xbmc.LOGERROR)
        Globals.dialog.notificationDialog(ADDON_NAME, LANGUAGE(30079))
   
if __name__ == '__main__': _start()
