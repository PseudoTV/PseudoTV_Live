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

from globals    import *

class Hachoir:
    def determineLength(self, filename):
        try:
            meta = {}
            from hachoir.parser   import createParser
            from hachoir.metadata import extractMetadata
            log("Hachoir: determineLength %s"%(filename))
            meta = extractMetadata(createParser(FileAccess.open(filename,'r')))
            if not meta: raise Exception('No meta found')
            dur  = meta.get('duration').total_seconds()
            log('Hachoir: Duration is %s'%(dur))
            return dur
        except Exception as e:
            log("Hachoir: failed! %s\nmeta = %s"%(e,meta), xbmc.LOGERROR)
            return 0
