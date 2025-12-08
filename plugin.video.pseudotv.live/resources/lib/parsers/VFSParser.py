#   Copyright (C) 2024 Lunatixz
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

from globals import *

class VFSParser:
    VFSPaths = VFS_TYPES
    def _normalizeDuration(self, value, source_hint=None) -> int and float:
        """Normalize duration to seconds, handling both millisecond and second inputs.
        
        Uses source-aware hints and divisibility/range heuristics to detect milliseconds:
        - streamdetails sources: ALWAYS milliseconds, divide by 1000
        - runtime/duration/resume: prefer seconds, only convert if seconds is genuinely implausible
        
        Args:
            value: Duration value (could be seconds or milliseconds)
            source_hint: One of 'streamdetails', 'runtime', 'duration', 'resume' or None
        
        Returns:
            Duration in seconds
        """
        if value is None:
            return 0
        try:
            raw = float(value)
        except (TypeError, ValueError):
            return 0
        if raw <= 0:
            return 0
        
        MIN_SECONDS = 1           # Minimum plausible duration
        TYPICAL_MAX = 6 * 3600    # 6 hours - typical max for most content
        EXTREME_MAX = 72 * 3600   # 72 hours - absolute max for any recording
        
        # streamdetails.video.duration is ALWAYS in milliseconds
        if source_hint in ('streamdetails', 'streamdetails.video', 'streamdetails.video.duration'):
            return max(MIN_SECONDS, raw / 1000.0)
        
        # For other sources, use heuristics to detect milliseconds
        seconds_value = raw
        ms_value = raw / 1000.0
        
        # Check if value is near a multiple of 1000 (suggests millisecond granularity)
        remainder = abs(raw - round(raw / 1000.0) * 1000.0)
        near_multiple = remainder <= 1.5  # Allow small floating point tolerance
        
        # Check if interpretations are plausible
        seconds_plausible = MIN_SECONDS <= seconds_value <= EXTREME_MAX
        ms_plausible = MIN_SECONDS <= ms_value <= TYPICAL_MAX
        
        prefer_seconds = source_hint in ('runtime', 'duration', 'resume', 'resume.total')
        
        if prefer_seconds:
            # For sources that should be in seconds, convert if:
            # - Value is near 1000-multiple AND
            # - Ms interpretation gives a plausible result AND
            # - Either seconds interpretation is implausible (> 72 hours) OR exceeds typical max (6 hours)
            if near_multiple and ms_plausible and (not seconds_plausible or seconds_value > TYPICAL_MAX):
                return max(MIN_SECONDS, ms_value)
        else:
            # For unknown sources, be more aggressive about detecting milliseconds
            # Convert if ms interpretation is plausible and seconds seems too large
            if near_multiple and ms_plausible and (not seconds_plausible or seconds_value > TYPICAL_MAX):
                return max(MIN_SECONDS, ms_value)
        
        return seconds_value

    def _getDurationFromItem(self, item: dict) -> int and float:
        """Get duration from item, handling milliseconds conversion for streamdetails.
        
        Kodi returns duration in different units depending on the source:
        - resume.total, runtime, duration: seconds (but apply safety normalization)
        - streamdetails.video[].duration: milliseconds (always convert to seconds)
        """
        # Try each source in priority order with source-aware normalization
        resume_total = item.get('resume',{}).get('total')
        if resume_total: return self._normalizeDuration(resume_total, 'resume')
        
        runtime = item.get('runtime')
        if runtime: return self._normalizeDuration(runtime, 'runtime')
        
        duration = item.get('duration')
        if duration: return self._normalizeDuration(duration, 'duration')
        
        # streamdetails.video.duration is ALWAYS in milliseconds
        streamdetails_duration = (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration') or 0
        if streamdetails_duration > 0:
            return self._normalizeDuration(streamdetails_duration, 'streamdetails')
        return 0

    def determineLength(self, filename: str, fileitem: dict={}, jsonRPC=None)-> int and float:
        log("VFSParser: determineLength, file = %s\nitem = %s"%(filename,fileitem))
        duration = self._getDurationFromItem(fileitem)
        if duration == 0 and jsonRPC and not filename.lower().startswith(fileitem.get('originalpath','').lower()) and not filename.lower().startswith(tuple(self.VFSPaths)):
            response = jsonRPC.getFileDetails((fileitem.get('originalpath') or fileitem.get('file') or filename))
            # Extract filedetails from JSON-RPC response structure
            metadata = response.get('result',{}).get('filedetails',{}) if isinstance(response, dict) else {}
            duration = self._getDurationFromItem(metadata)
        log("VFSParser: Duration is %s"%(duration))
        return duration
