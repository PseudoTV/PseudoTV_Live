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
# from globals import *

# class Service(object):
    # from jsonrpc import JSONRPC
    # jsonRPC = JSONRPC()
    player  = PLAYER()
    monitor = MONITOR()
    def _shutdown(self, wait=CPU_CYCLE) -> bool:
        return PROPERTIES.isPendingShutdown() or self.monitor.waitForAbort(wait)
    def _restart(self) -> bool:
        return PROPERTIES.isPendingRestart()
    def _interrupt(self) -> bool:
        return any([PROPERTIES.isPendingInterrupt(),self._shutdown(),self._restart(),BUILTIN.isScanning()])
    def _suspend(self) -> bool:
        return any([PROPERTIES.isPendingSuspend(),BUILTIN.isSettingsOpened()])
    def _sleep(self, wait=CPU_CYCLE):
        while not self.monitor.abortRequested() and wait > 0:
            if any([self.monitor.waitForAbort(CPU_CYCLE),self._interrupt()]): return True
            else: wait -= CPU_CYCLE
        return False
        
# class Skin(object):
    # def __init__(self, service=None):
        # if service is None: service = Service()
        # self.jsonRPC = service.jsonRPC

# #todo match kodi skin color scheme/profile by parsing json values and creating skin vars.

# lookandfeel.skincolors
# {"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"lookandfeel.skincolors"}.get('value')
# {"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"special://skin/colors/"}..get('files')