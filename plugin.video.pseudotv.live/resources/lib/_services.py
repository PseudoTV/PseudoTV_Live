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
from kodi_six  import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
from threading import Thread
from variables import *

class _Service(object):
    """Lightweight dummy service - used by Dialog when full services.Service isn't required."""
    def __init__(self):
        from jsonrpc import JSONRPC
        from pool    import ExecutorPool
        from cache   import Cache
        self.player           = xbmc.Player()
        self.monitor          = xbmc.Monitor()
        self.pool             = ExecutorPool()
        self.kodi             = Kodi(self)
        self.cache            = Cache(mem_cache=True)
        self.jsonRPC          = JSONRPC(service=self)
        self.pendingShutdown  = False
        self.pendingRestart   = False
        self.pendingInterrupt = False
        self.pendingSuspend   = False
        self.serviceThread    = Thread(target=self._run, name=f"{ADDON_ID}.serviceThread")

        if self.serviceThread.is_alive():
            try: self.serviceThread.join(SERVICE_INTERVAL)
            except Exception: pass
        else:
            self.serviceThread.daemon = True
            self.serviceThread.start()

    def log(self, msg, level=xbmc.LOGDEBUG):
        return Globals._log(f"{self.__class__.__name__}: {msg}", level)

    def _shutdown(self) -> bool:
        return _getEXTProperty('%s.pendingShutdown'%(ADDON_ID),False) or self.monitor.abortRequested()

    def _restart(self) -> bool:
        return _getEXTProperty('%s.pendingRestart'%(ADDON_ID),False)

    def _interrupt(self) -> bool:
        return any([_getEXTProperty('%s.pendingInterrupt'%(ADDON_ID),False), self.Kodi.builtin._isScanning()])

    def _suspend(self) -> bool:
        return any([_getEXTProperty('%s.pendingSuspend'%(ADDON_ID),False), self.kodi.builtin._isSettingsOpened()])

    def _sleep(self, wait=None):
        if wait is None: wait = CPU_CYCLE
        while not self.monitor.abortRequested() and wait > 0:
            if any([self.monitor.waitForAbort(CPU_CYCLE), self._interrupt()]):
                return True
            wait -= CPU_CYCLE
        return False

    def _run(self):
        self.log('_run, starting')
        while not self.monitor.abortRequested():
            self.pendingShutdown  = self._shutdown()
            self.pendingRestart   = self._restart()
            self.pendingInterrupt = self._interrupt()
            self.pendingSuspend   = self._suspend()
            if self.monitor.waitForAbort(SERVICE_INTERVAL):
                break
        self.pool.shutdown()
        self.cache.shutdown()
        self.log('_run, stopping...')

def _start():
    try:
        from services import Service
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            restart = Service()._start()
            if monitor.waitForAbort(CPU_CYCLE) or not restart: 
                Globals.DIALOG.notificationDialog(LANGUAGE(32141))
                log("Services: _start, shutting down...")
                break
            elif restart:
                Globals.DIALOG.notificationDialog(LANGUAGE(32124))
                log("Services: _start, restarting...")
        del monitor
    except Exception as e:
         log("Services: _start, failed! %s"%(e), xbmc.LOGERROR)
         Globals.DIALOG.notificationDialog(LANGUAGE(30079))
    finally:
        sys.exit()
   
if __name__ == '__main__': _start()
