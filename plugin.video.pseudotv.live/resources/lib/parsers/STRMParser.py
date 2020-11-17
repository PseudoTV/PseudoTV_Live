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
from xml.dom.minidom import parse, parseString

class STRMParser:
    def determineLength(self, filename):
        fleName, fleExt = os.path.splitext(filename)
        fleName += '.nfo'
        log("STRMParser: determineLength, file = %s, nfo = %s"%(filename,fleName))
        duration = 0
        durationinseconds = 0
        
        try:
            # self.File = xbmcvfs.File(fleName, "r")
            self.File = FileAccess.open(filename, "rb", None)
            dom = parse(self.File)
        except:
            log("STRMParser: MKVParser: Unable to open the file %s"%(fleName), xbmc.LOGERROR)
            return duration

        try:                    
            xmldurationinseconds = dom.getElementsByTagName('durationinseconds')[0].toxml()
            return int(xmldurationinseconds.replace('<durationinseconds>','').replace('</durationinseconds>',''))
        except Exception as e: log("STRMParser: <durationinseconds> not found")
            
        try:
            xmlruntime = dom.getElementsByTagName('runtime')[0].toxml()
            return int(xmlruntime.replace('<runtime>','').replace('</runtime>','').replace(' min.','')) * 60
        except Exception as e: log("STRMParser: <runtime> not found")
                
        try:
            xmlruntime = dom.getElementsByTagName('duration')[0].toxml()
            return int(xmlruntime.replace('<duration>','').replace('</duration>','')) * 60
        except Exception as e: log("STRMParser: <duration> not found")
                
        self.File.close()
        log("STRMParser: Duration is " + str(duration))
        return duration
