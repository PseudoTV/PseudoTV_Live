# Copyright (C) 2024 Jason Anderson, Lunatixz
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

from globals import *


class MKVParser:
    """
    A parser for determining the duration of MKV files.
    """

    monitor = MONITOR()

    def determineLength(self, filename: str) -> int:
        """
        Determines the duration of an MKV file.

        Args:
            filename: Path to the MKV file.

        Returns:
            The duration of the file in seconds, or 0 on failure.
        """
        log(f"MKVParser: determineLength {filename}")
        try:
            self.File = FileAccess.open(filename, "rb", None)
        except Exception:
            log("MKVParser: Unable to open the file")
            log(traceback.format_exc(), xbmc.LOGERROR)
            return 0

        size = self.findHeader()

        if size == 0:
            log("MKVParser: Unable to find the segment info")
            duration = 0
        else:
            duration = int(round(self.parseHeader(size)))

        log(f"MKVParser: Duration is {duration}")
        return duration

    def parseHeader(self, size: int) -> float:
        """
        Parses the header to extract duration information.

        Args:
            size: Size of the segment info.

        Returns:
            Duration in seconds, or 0 on failure.
        """
        duration = 0
        timecode = 0
        file_end = self.File.tell() + size

        while (not self.monitor.abortRequested() and
               self.File.tell() < file_end and duration == 0):
            data = self.getEBMLId()
            data_size = self.getDataSize()

            if data == 0x2AD7B1:  # TimecodeScale
                try:
                    timecode = int.from_bytes(self.getData(data_size), "big")
                except Exception:
                    timecode = 0
            elif data == 0x4489:  # Duration
                try:
                    duration = struct.unpack(">f", self.getData(data_size))[0]
                except Exception:
                    log("MKVParser: Error extracting duration", xbmc.LOGERROR)
                    duration = 0

        if duration > 0 and timecode > 0:
            return (duration * timecode) / 1_000_000_000

        return 0

    def findHeader(self) -> int:
        """
        Locates the segment header in the MKV file.

        Returns:
            Size of the segment info, or 0 on failure.
        """
        log("MKVParser: findHeader")
        filesize = self.getFileSize()
        if filesize == 0:
            log("MKVParser: Empty file")
            return 0

        data = self.getEBMLId()
        if data != 0x1A45DFA3:  # EBML header
            log("MKVParser: Not a proper MKV")
            return 0

        try:
            self.File.seek(self.getDataSize(), 1)
        except Exception:
            log("MKVParser: Error while seeking")
            return 0

        while not self.monitor.abortRequested():
            data = self.getEBMLId()
            if data == 0x18538067:  # Segment
                return self.getDataSize()

        return 0

    def getFileSize(self) -> int:
        """
        Retrieves the size of the file.

        Returns:
            File size in bytes.
        """
        try:
            current_pos = self.File.tell()
            self.File.seek(0, 2)
            size = self.File.tell()
            self.File.seek(current_pos, 0)
            return size
        except Exception:
            return 0

    def getData(self, size: int) -> bytes:
        """
        Reads a specified number of bytes.

        Args:
            size: Number of bytes to read.

        Returns:
            The read bytes.
        """
        return self.File.readBytes(size)

    def getDataSize(self) -> int:
        """
        Reads the size of the next data block.

        Returns:
            Size of the data block.
        """
        try:
            first_byte = struct.unpack(">B", self.File.readBytes(1))[0]
            data_size = first_byte & 0x7F
            if first_byte >> 7 != 1:
                for _ in range(3):
                    next_byte = struct.unpack(">B", self.File.readBytes(1))[0]
                    data_size = (data_size << 8) | next_byte
            return data_size
        except Exception:
            return 0

    def getEBMLId(self) -> int:
        """
        Reads the EBML ID.

        Returns:
            EBML ID.
        """
        try:
            first_byte = struct.unpack(">B", self.File.readBytes(1))[0]
            ebml_id = first_byte
            if first_byte >> 7 != 1:
                for _ in range(3):
                    next_byte = struct.unpack(">B", self.File.readBytes(1))[0]
                    ebml_id = (ebml_id << 8) | next_byte
            return ebml_id
        except Exception:
            return 0