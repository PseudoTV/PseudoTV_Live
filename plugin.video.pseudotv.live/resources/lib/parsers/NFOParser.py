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

from variables import *
from typing import Union

class NFOParser:
    """
    Parses video duration from NFO metadata files.
    
    NFO EXAMPLE:
    <episodedetails>
      <runtime>25</runtime>
      <duration>1575</duration>
      <fileinfo>
        <streamdetails>
          <video>
            <durationinseconds>1575</durationinseconds>
          </video>
        </streamdetails>
      </fileinfo>
    </episodedetails>
    """
    
    def determineLength(self, filename: str) -> Union[int, float]:
        """
        Determines video duration from accompanying .nfo file.
        Returns duration in seconds.
        Priority: durationinseconds > runtime (in minutes) > duration (in seconds)
        """
        duration = 0
        fleName, fleExt = os.path.splitext(filename)
        fleName += '.nfo'
        
        if not FileAccess.exists(fleName):
            log("NFOParser: Unable to locate NFO %s"%(fleName), xbmc.LOGERROR)
            return 0
            
        log("NFOParser: determineLength, file = %s, nfo = %s"%(filename, fleName))
        
        try:
            File = FileAccess.open(fleName, "rb")
            dom = parse(File)
            File.close()
        except IOError as e:
            log("NFOParser: Unable to open the file %s: %s"%(fleName, e), xbmc.LOGERROR)
            return 0
        except Exception as e:
            log("NFOParser: Failed to parse XML: %s"%(e), xbmc.LOGERROR)
            return 0
        
        # Try durationinseconds first (already in seconds)
        try:                    
            xmldurationinseconds = dom.getElementsByTagName('durationinseconds')[0].toxml()
            duration = int(xmldurationinseconds.replace('<durationinseconds>','').replace('</durationinseconds>','').strip())
            if duration > 0:
                log("NFOParser: Found durationinseconds: %s"%(duration))
        except (IndexError, ValueError):
            log("NFOParser: <durationinseconds> not found or invalid")
        
        # Fallback to runtime in minutes
        if duration == 0:
            try:
                xmlruntime = dom.getElementsByTagName('runtime')[0].toxml()
                runtime_str = xmlruntime.replace('<runtime>','').replace('</runtime>','').replace(' min.','').strip()
                duration = int(float(runtime_str)) * 60  # Convert minutes to seconds
                if duration > 0:
                    log("NFOParser: Found runtime (minutes): %s"%(runtime_str))
            except (IndexError, ValueError):
                log("NFOParser: <runtime> not found or invalid")
        
        # Fallback to duration tag (interpret as seconds)
        if duration == 0:    
            try:
                xmlduration = dom.getElementsByTagName('duration')[0].toxml()
                duration_str = xmlduration.replace('<duration>','').replace('</duration>','').strip()
                duration = int(float(duration_str))
                if duration > 0:
                    log("NFOParser: Found duration (seconds): %s"%(duration_str))
            except (IndexError, ValueError):
                log("NFOParser: <duration> not found or invalid")
                
        log("NFOParser: Duration is %s seconds"%(duration))
        return duration