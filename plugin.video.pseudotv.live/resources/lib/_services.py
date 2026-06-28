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
from globals    import *

def _getEXTProperty(key, default=''):
    try:
        value = xbmcgui.Window(10000).getProperty(key)
        if not value: return default
        try: value = literal_eval(value)
        except (ValueError, SyntaxError): pass
        return value
    except Exception as e: 
        return default
        
def _isScanning():
    return (xbmc.getCondVisibility('Library.IsScanningVideo') &  xbmc.getCondVisibility('Library.IsScanningMusic'))

def _isSettingsOpened() -> bool:
    return any([ xbmc.getCondVisibility('Window.IsVisible(addonsettings)'), xbmc.getCondVisibility('Window.IsVisible(selectdialog)')])

class Service(object):
    def __init__(self):
        self.log('__init__')
        from jsonrpc import JSONRPC
        from pool    import ExecutorPool
        from cache   import Cache
        self.player  = PLAYER()
        self.monitor = MONITOR()
        self.pool    = ExecutorPool()
        self.cache   = Cache(mem_cache=True)
        self.jsonRPC = JSONRPC(service=self)

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
        return log(f"{self.__class__.__name__}: {msg}", level)
        
    def _shutdown(self) -> bool:
        return _getEXTProperty('%s.pendingShutdown'%(ADDON_ID),False) or self.monitor.abortRequested()

    def _restart(self) -> bool:
        return _getEXTProperty('%s.pendingRestart'%(ADDON_ID),False)

    def _interrupt(self) -> bool:
        return any([_getEXTProperty('%s.pendingInterrupt'%(ADDON_ID),False), _isScanning()])

    def _suspend(self) -> bool:
        return any([_getEXTProperty('%s.pendingSuspend'%(ADDON_ID),False), _isSettingsOpened()])

    def _sleep(self, wait=CPU_CYCLE):
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
            