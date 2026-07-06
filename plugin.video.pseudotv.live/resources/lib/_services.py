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

# --- imports needed BEFORE globals to define Service class early ---
from kodi_six  import xbmc, xbmcgui
from threading import Thread
from variables import *

def _getProp(key, default=None):
    return xbmcgui.Window(10000).getProperty(key) or default
    
def _log(event, level=xbmc.LOGDEBUG):
    if REAL_SETTINGS.getSetting('Debug_Enable') == 'true' or level >= 3:
        DEBUG_LEVELS = {0: xbmc.LOGDEBUG, 1: xbmc.LOGINFO, 2: xbmc.LOGWARNING, 3: xbmc.LOGERROR, 4: xbmc.LOGFATAL}
        DEBUG_LEVEL  = DEBUG_LEVELS[int((REAL_SETTINGS.getSetting('Debug_Level') or "3"))]
        if level >= 3: event = '%s\n%s' % (event, traceback.format_exc())
        event = '%s-%s-%s' % (ADDON_ID, ADDON_VERSION, event)
        if level >= DEBUG_LEVEL:
            xbmc.log(event, level)
            
class _Service(object):
    """Lightweight dummy service - used by Dialog when full services.Service isn't required."""
    def __init__(self):
        from jsonrpc import JSONRPC
        from pool    import ExecutorPool
        from cache   import Cache
        self.player           = xbmc.Player()
        self.monitor          = xbmc.Monitor()
        self.pool             = ExecutorPool()
        self.cache            = Cache(mem_cache=True)
        self.jsonRPC          = JSONRPC(service=self)
        self.pendingShutdown  = False
        self.pendingRestart   = False
        self.pendingInterrupt = False
        self.pendingSuspend   = False
        self.serviceThread    = Thread(target=self._run, name=f"{ADDON_ID}.serviceThread")

        if self.serviceThread.is_alive():
            self.log('__init__, serviceThread already alive, joining for %.1fs' % SERVICE_INTERVAL, xbmc.LOGINFO)
            try: self.serviceThread.join(SERVICE_INTERVAL)
            except Exception as e: self.log('__init__, serviceThread join failed: %s' % e, xbmc.LOGWARNING)
        else:
            self.serviceThread.daemon = True
            self.serviceThread.start()
            self.log('__init__, serviceThread started (daemon=%s)' % self.serviceThread.daemon, xbmc.LOGINFO)

    def log(self, msg, level=xbmc.LOGDEBUG):
        _log(f"{self.__class__.__name__}: {msg}", level)

    def _shutdown(self) -> bool:
        return _getProp('%s.pendingShutdown'%(ADDON_ID),'false') == 'true' or self.monitor.abortRequested()

    def _restart(self) -> bool:
        return _getProp('%s.pendingRestart'%(ADDON_ID),'false') == 'true'

    def _interrupt(self) -> bool:
        return any([_getProp('%s.pendingInterrupt'%(ADDON_ID),'false') == 'true', self.monitor.abortRequested()])

    def _suspend(self) -> bool:
        return any([_getProp('%s.pendingSuspend'%(ADDON_ID),'false') == 'true', self.monitor.abortRequested()])

    def _sleep(self, wait=None):
        if wait is None: wait = CPU_CYCLE
        while not self.monitor.abortRequested() and wait > 0:
            if any([self.monitor.waitForAbort(CPU_CYCLE), self._interrupt()]):
                return True
            wait -= CPU_CYCLE
        return False

    def _run(self):
        self.log('_run, starting service loop (interval=%.1fs)' % SERVICE_INTERVAL, xbmc.LOGINFO)
        while not self.monitor.abortRequested():
            self.pendingShutdown  = self._shutdown()
            self.pendingRestart   = self._restart()
            self.pendingInterrupt = self._interrupt()
            self.pendingSuspend   = self._suspend()
            if self.monitor.waitForAbort(SERVICE_INTERVAL):
                break
        self.pool.shutdown()
        self.cache.shutdown()
        self.log('_run, service loop ended (shutdown=%s, restart=%s)' % (self.pendingShutdown, self.pendingRestart), xbmc.LOGINFO)

def _start():
    try:
        from services import Service
        monitor = xbmc.Monitor()
        _log("_start, importing Service and entering main loop", xbmc.LOGINFO)
        while not monitor.abortRequested():
            restart = Service()._start()
            if monitor.waitForAbort(CPU_CYCLE) or not restart: 
                xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(32141))
                _log("_start, shutting down (restart=%s, abort=%s)" % (restart, monitor.abortRequested()), xbmc.LOGINFO)
                break
            elif restart:
                xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(32124))
                _log("_start, restarting service loop", xbmc.LOGINFO)
        del monitor
    except Exception as e:
         _log("_start, failed! %s" % (e), xbmc.LOGERROR)
         xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30079))
    finally:
        _log("_start, exiting (sys.exit)", xbmc.LOGINFO)
        sys.exit()
   
if __name__ == '__main__': _start()
