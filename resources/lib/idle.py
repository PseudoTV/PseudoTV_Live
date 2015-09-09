#   Copyright (C) 2015 Anisan, Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

#Standard modules
import os
import sys
#Third-party modules
import xbmcaddon
#Project modules
from Globals import *

###Path handling
rootDir = ADDON_PATH
if rootDir[-1] == ';':rootDir = rootDir[0:-1]
resDir = os.path.join(rootDir, 'resources')
libDir = os.path.join(resDir, 'lib')
skinsDir = os.path.join(resDir, 'skins')

sys.path.append (libDir)

import idle_gui
ui = idle_gui.GUI("idle.xml" , ADDON_PATH, "Default")
ui.doModal()
    