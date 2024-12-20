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

class OpenCV:
    def determineLength(self, filename: str) -> int and float:
        try:
            import cv2
            log("OpenCV: determineLength %s"%(filename))
            dur = cv2.VideoCapture(FileAccess.translatePath(filename)).get(cv2.CAP_PROP_POS_MSEC)
            log('OpenCV: Duration is %s'%(dur))
            return dur
        except Exception as e:
            log("OpenCV: failed! %s"%(e), xbmc.LOGERROR)
            return 0
