#   Copyright (C) 2016 Kevin S. Graer
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

import xbmc, xbmcgui, xbmcaddon, xbmcvfs

from resources.lib.utils import *
from resources.lib.Globals import *

def autostart():
    infoDialog("AutoStart Enabled")
    if handle_wait(AUTOSTART_TIMER,"PseudoTV Live will autostart in %s seconds, Cancel?") == True:
        xbmc.executebuiltin('RunScript("' + ADDON_PATH + '/default.py' + '")')
 
if AUTOSTART_TIMER > 0:
    autostart()