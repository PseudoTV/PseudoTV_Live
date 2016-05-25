#   Copyright (C) 2015 Kevin S. Graer
#
#
# This file is part of PseudoTV.
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

import xbmc
import os, struct
import traceback

from resources.lib.Globals import *
from resources.lib.FileAccess import FileAccess
from xml.dom.minidom import parse, parseString


class STRMParser:
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('STRMParser: ' + ascii(msg), level)


    def determineLength(self, filename):
        self.log("determineLength " + filename)
        fleName, fleExt = os.path.splitext(filename)
        fleName += '.nfo'
        duration = 0
        durationinseconds = 0
        
        if FileAccess.exists(fleName):
            file = FileAccess.open(fleName, "r")
            dom = parse(file)
            
            try:                    
                xmldurationinseconds = dom.getElementsByTagName('durationinseconds')[0].toxml()
                durationinseconds = xmldurationinseconds.replace('<durationinseconds>','').replace('</durationinseconds>','')    
                duration = int(durationinseconds)
            except Exception,e:
                duration = 0
                
            if duration == 0:
                try:
                    xmlruntime = dom.getElementsByTagName('runtime')[0].toxml()
                    runtime = xmlruntime.replace('<runtime>','').replace('</runtime>','').replace(' min.','')    
                    runtime = int(runtime)
                    duration = runtime * 60
                except Exception,e:
                    duration = 0
                    
            if duration == 0:
                try:
                    xmlruntime = dom.getElementsByTagName('duration')[0].toxml()
                    runtime = xmlruntime.replace('<duration>','').replace('</duration>','')
                    runtime = int(runtime)
                    duration = runtime * 60
                except Exception,e:
                    duration = 0
                    
            file.close()
        self.log('script.pseudotv-STRMParser: duration = ' + str(duration))
        return duration
