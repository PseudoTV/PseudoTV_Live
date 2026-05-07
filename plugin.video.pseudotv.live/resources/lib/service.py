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
from services   import Service

def _start():
    try:
        service = Service()
        while not service.monitor.abortRequested():
            restart = service._start()
            if service.monitor.waitForAbort(CPU_CYCLE) or not restart: 
                DIALOG.notificationDialog(LANGUAGE(32141))
                log("Services: _start, shutting down...")
                break
            elif restart:
                DIALOG.notificationDialog(LANGUAGE(32124))
                log("Services: _start, restarting...")
        del service
    except Exception as e:
         log("Services: _start, failed! %s"%(e), xbmc.LOGERROR)
         DIALOG.notificationDialog(LANGUAGE(30079))
    finally:
        sys.exit()
   
if __name__ == '__main__': _start()