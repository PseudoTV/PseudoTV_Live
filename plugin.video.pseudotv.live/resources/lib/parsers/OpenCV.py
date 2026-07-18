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

class OpenCV:


    def determineLength(self, filename: str) -> int:
        """
        Determines video length using OpenCV.
        Returns duration in seconds.
        """
        cap = None
        try:
            import cv2
            LOG("OpenCV: determineLength %s"%(filename))
            cap = cv2.VideoCapture(FileAccess.translatePath(filename))
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if frame_count > 0 and fps > 0:
                dur = int(frame_count / fps)
            else:
                dur = 0
            LOG('OpenCV: Duration is %s seconds'%(dur))
            return dur
        except ImportError:
            LOG("OpenCV: cv2 module not available", xbmc.LOGERROR)
            return 0
        except Exception as e:
            LOG("OpenCV: failed! %s"%(e), xbmc.LOGERROR)
            return 0
        finally:
            if cap is not None:
                cap.release()
