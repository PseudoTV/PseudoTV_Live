#   Copyright (C) 2024 Lunatixz
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
from globals import *

class Service:
    from jsonrpc import JSONRPC
    monitor = MONITOR()
    jsonRPC = JSONRPC()
    def _interrupt(self, wait: float=.001) -> bool:
        return self.monitor.waitForAbort(wait)
    def _suspend(self) -> bool:
        return PROPERTIES.isPendingSuspend()

class Skin:
    def __init__(self, service=None):
        if service is None: service = Service()
        self.jsonRPC = service.jsonRPC



lookandfeel.skincolors
{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"lookandfeel.skincolors"}.get('value')
{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"special://skin/colors/"}..get('files')