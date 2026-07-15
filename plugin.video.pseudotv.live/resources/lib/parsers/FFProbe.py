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

class FFProbe:


    def determineLength(self, filename: str) -> Union[int, float]:
        """
        Determines video length using FFProbe.
        Returns duration in seconds.
        """
        try:
            import ffmpeg
            LOG("FFProbe: determineLength %s"%(filename))
            dur = ffmpeg.probe(FileAccess.translatePath(filename))["format"]["duration"]
            dur = int(float(dur))  # Ensure integer seconds
            LOG('FFProbe: Duration is %s seconds'%(dur))
            return dur
        except ImportError:
            LOG("FFProbe: ffmpeg-python module not available", xbmc.LOGERROR)
            return 0
        except (KeyError, ValueError, TypeError) as e:
            LOG("FFProbe: failed to parse duration! %s"%(e), xbmc.LOGERROR)
            return 0
        except Exception as e:
            LOG("FFProbe: failed! %s"%(e), xbmc.LOGERROR)
            return 0