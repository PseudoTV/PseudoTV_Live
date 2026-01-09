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
from globals    import *
from service    import Service

def _start():
    """
    Main entry point for the PseudoTV Live service monitor.

    This function continuously checks for abort requests and handles service entry.
    - Initializes the Kodi monitor.
    - Waits for abort signals or service entry breaks.
    - Displays notifications during the wait.
    - On exceptions, shows an error dialog.
    - Ensures proper exit from the script.
    """
    try:
        monitor = MONITOR()
        while not monitor.abortRequested():
            restart = Service()._start()
            if monitor.waitForAbort(CPU_CYCLE): 
                log("Services: _start, shutting down...")
                break
            elif not restart:
                DIALOG.notificationDialog(LANGUAGE(32141))
                break
            else:
                DIALOG.notificationDialog(LANGUAGE(32124))
    except Exception as e:
         log("Services: _start, failed! %s"%(e), xbmc.LOGERROR)
         DIALOG.notificationDialog(LANGUAGE(30079))
    finally:
        sys.exit()
   
if __name__ == '__main__': _start()