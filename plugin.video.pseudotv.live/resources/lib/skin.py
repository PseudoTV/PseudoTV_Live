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
# from globals import *

# class Service(object):
    # from jsonrpc import JSONRPC
    # monitor = MONITOR()
    # jsonRPC = JSONRPC()
    # def _shutdown(self, wait=1.0) -> bool:
        # return (self.monitor.waitForAbort(wait) | PROPERTIES.isPendingShutdown())
    # def _interrupt(self) -> bool:
        # return (PROPERTIES.isPendingShutdown() | PROPERTIES.isPendingRestart() | PROPERTIES.isPendingInterrupt() | PROPERTIES.isInterruptActivity())
    # def _suspend(self, wait=1.0) -> bool:
        # pendingSuspend = PROPERTIES.isPendingSuspend()
        # return pendingSuspend
    # def _sleep(self, wait=1.0):
        # while not self.monitor.abortRequested() and wait > 0:
            # if (self.monitor.waitForAbort(0.5) | self._interrupt()): return True
            # else: wait -= 0.5
        # return False
        
# class Skin(object):
    # def __init__(self, service=None):
        # if service is None: service = Service()
        # self.jsonRPC = service.jsonRPC

# #todo match kodi skin color scheme/profile by parsing json values and creating skin vars.

# lookandfeel.skincolors
# {"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"lookandfeel.skincolors"}.get('value')
# {"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"special://skin/colors/"}..get('files')