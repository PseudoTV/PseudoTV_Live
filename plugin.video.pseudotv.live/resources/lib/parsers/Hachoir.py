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

from variables    import *
from typing import Union

class Hachoir:
    def determineLength(self, filename: str) -> Union[int, float]:
        """
        Determines video length using Hachoir metadata.
        Returns duration in seconds.
        """
        try:
            meta = {}
            from hachoir.parser   import createParser
            from hachoir.metadata import extractMetadata
            log("Hachoir: determineLength %s"%(filename))
            
            file_obj = FileAccess.open(filename, 'rb')
            parser = createParser(file_obj)
            if not parser:
                raise Exception('Unable to create parser')
            
            meta = extractMetadata(parser)
            file_obj.close()
            
            if not meta:
                raise Exception('No metadata found')
            
            duration = meta.get('duration')
            if not duration:
                raise Exception('Duration not found in metadata')
            
            dur = int(duration.total_seconds())
            log('Hachoir: Duration is %s seconds'%(dur))
            return dur
        except ImportError:
            log("Hachoir: hachoir module not available", xbmc.LOGERROR)
            return 0
        except Exception as e:
            log("Hachoir: failed! %s"%(e), xbmc.LOGERROR)
            return 0