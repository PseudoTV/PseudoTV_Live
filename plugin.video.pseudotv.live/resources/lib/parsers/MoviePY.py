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

class MoviePY:
    def determineLength(self, filename: str) -> Union[int, float]:
        """
        Determines video length using MoviePy.
        Returns duration in seconds.
        """
        try:
            from moviepy.editor import VideoFileClip
            log("MoviePY: determineLength %s"%(filename))
            clip = VideoFileClip(FileAccess.translatePath(filename))
            dur = int(clip.duration)
            clip.close()
            log('MoviePY: Duration is %s seconds'%(dur))
            return dur
        except ImportError:
            log("MoviePY: moviepy module not available", xbmc.LOGERROR)
            return 0
        except Exception as e:
            log("MoviePY: failed! %s"%(e), xbmc.LOGERROR)
            return 0