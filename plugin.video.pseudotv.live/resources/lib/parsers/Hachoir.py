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

# hachoir parses local file streams only — smb:// and nfs:// are converted to
# UNC via FileAccess.localizePath; other un-localizable protocols are skipped.
_REMOTE_PREFIXES = ('dav://', 'davs://', 'ftp://', 'http://', 'https://',
                    'upnp://', 'plugin://', 'pvr://', 'stack://')

class Hachoir:


    def determineLength(self, filename: str) -> Union[int, float]:
        """
        Determines video length using Hachoir metadata.
        Returns duration in seconds.
        """
        local = FileAccess.localizePath(filename)
        if local.lower().startswith(_REMOTE_PREFIXES):
            return 0
        try:
            meta = {}
            from hachoir.parser   import createParser
            from hachoir.metadata import extractMetadata
            LOG("Hachoir: determineLength %s"%(filename))

            parser = createParser(local)
            if not parser:
                raise Exception('Unable to create parser')
            
            meta = extractMetadata(parser)
            
            if not meta:
                raise Exception('No metadata found')
            
            duration = meta.get('duration')
            if not duration:
                raise Exception('Duration not found in metadata')
            
            dur = int(duration.total_seconds())
            LOG('Hachoir: Duration is %s seconds'%(dur))
            return dur
        except ImportError:
            LOG("Hachoir: hachoir module not available", xbmc.LOGERROR)
            return 0
        except Exception as e:
            LOG("Hachoir: failed! %s"%(e), xbmc.LOGERROR)
            return 0