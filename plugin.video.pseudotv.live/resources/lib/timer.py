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

# -*- coding: utf-8 -*--

from resources.lib.globals import *

class Timer:
    def __init__(self, timeout, callback):
        self._timeout  = timeout
        self._callback = callback
        self._task     = asyncio.ensure_future(self._job())


    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()


    def cancel(self):
        self._task.cancel()