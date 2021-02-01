#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live Live.  If not, see <http://www.gnu.org/licenses/>.

from resources.lib.globals import *

class VFSParser:
    def determineLength(self, filename):
        fleName, fleExt = os.path.splitext(filename)
        fleName += '.nfo'
        log("VFSParser: determineLength, file = %s, nfo = %s"%(filename,fleName))
        duration = 0
        durationinseconds = 0
        #todo parse json for item duration.
        log("VFSParser: Duration is " + str(duration))
        return duration
