#   Copyright (C) 2015 Jason Anderson, Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
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
import os, platform
import subprocess

import parsers.MP4Parser as MP4Parser
import parsers.AVIParser as AVIParser
import parsers.MKVParser as MKVParser
import parsers.FLVParser as FLVParser
import parsers.TSParser  as TSParser
import parsers.STRMParser  as STRMParser

from Globals import *
from FileAccess import FileAccess

class VideoParser:
    def __init__(self):
        self.AVIExts = ['.avi']
        self.MP4Exts = ['.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov']
        self.MKVExts = ['.mkv']
        self.FLVExts = ['.flv']
        self.TSExts  = ['.ts', '.m2ts', '.mts']
        self.STRMExts = ['.strm']


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('VideoParser: ' + msg, level)
        

    def getVideoLength(self, filename):
        self.log("getVideoLength, " + filename)
        if len(filename) == 0:
            self.log("getVideoLength, No file name specified")
            return 0
            
        # todo improve network files
        # if FileAccess.exists(filename) == False:
            # try:
                # if filename[0:6].lower() == 'smb://':
                    # self.log("getVideoLength, Unknown SMB file found, Trying to mount drive")
                    # filename = FileAccess._openSMB(filename, 'r')
                # else:
                    # self.log("getVideoLength, Unable to find the file")
                    # return 0
            # except:
                # return 0

        base, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if ext in self.AVIExts:
            self.parser = AVIParser.AVIParser()
        elif ext in self.MP4Exts:
            self.parser = MP4Parser.MP4Parser()
        elif ext in self.MKVExts:
            self.parser = MKVParser.MKVParser()
        elif ext in self.FLVExts:
            self.parser = FLVParser.FLVParser()
        elif ext in self.TSExts:
            self.parser = TSParser.TSParser()
        elif ext in self.STRMExts:
            self.parser = STRMParser.STRMParser()
        else:
            self.log("getVideoLength, No parser found for extension " + ext)
            return 0
        return self.parser.determineLength(filename)