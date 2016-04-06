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

import xbmcgui, xbmc
import threading
import time
import traceback

from resources.lib.Globals import ascii, uni
from FileAccess import FileAccess



class PlaylistItem:
    def __init__(self):
        self.duration = 0
        self.filename = ''
        self.description = ''
        self.title = ''
        self.episodetitle = ''
        self.genre = ''
        self.timestamp = ''
        self.LiveID = '' ## tvdb/tmdb id
        



class Playlist:
    def __init__(self):
        self.itemlist = []
        self.totalDuration = 0
        self.processingSemaphore = threading.BoundedSemaphore()


    def getduration(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            dur = self.itemlist[index].duration
            self.processingSemaphore.release()
            return dur

        self.processingSemaphore.release()
        return 0


    def size(self):
        self.processingSemaphore.acquire()
        totsize = len(self.itemlist)
        self.processingSemaphore.release()
        return totsize


    def getfilename(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            fname = self.itemlist[index].filename
            self.processingSemaphore.release()
            return fname

        self.processingSemaphore.release()
        return ''


    def getLiveID(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            lid = self.itemlist[index].LiveID
            self.processingSemaphore.release()
            return lid

        self.processingSemaphore.release()
        return ''
    
    
    def gettimestamp(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            tstp = self.itemlist[index].timestamp
            self.processingSemaphore.release()
            return tstp

        self.processingSemaphore.release()
        return ''    
    
    
    def getgenre(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            genr = self.itemlist[index].genre
            self.processingSemaphore.release()
            return genr

        self.processingSemaphore.release()
        return ''
    
    
    def getdescription(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            desc = self.itemlist[index].description
            self.processingSemaphore.release()
            return desc

        self.processingSemaphore.release()
        return ''


    def getepisodetitle(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            epit = self.itemlist[index].episodetitle
            if ". " in epit:
                param, epit = epit.split(". ",1)
            self.processingSemaphore.release()
            return epit

        self.processingSemaphore.release()
        return ''


    def getTitle(self, index):
        self.processingSemaphore.acquire()

        if index >= 0 and index < len(self.itemlist):
            title = self.itemlist[index].title
            self.processingSemaphore.release()
            return title

        self.processingSemaphore.release()
        return ''


    def clear(self):
        del self.itemlist[:]
        self.totalDuration = 0


    def log(self, msg, level = xbmc.LOGDEBUG):
        xbmc.log('script.pseudotv.live-Playlist: ' + ascii(msg), level)


    def load(self, filename):
        self.log("load " + filename)
        self.processingSemaphore.acquire()
        self.clear()

        try:
            fle = FileAccess.open(filename, 'r')
        except IOError:
            self.log('Unable to open the file: ' + filename)
            self.processingSemaphore.release()
            return False

        # find and read the header
        try:
            lines = fle.readlines()
        except Exception,e:
            self.log("ERROR loading playlist: " + filename)
            self.log(traceback.format_exc(), xbmc.LOGERROR)

        fle.close()
        realindex = -1

        for i in range(len(lines)):
            if lines[i].startswith('#EXTM3U'):
                realindex = i
                break

        if realindex == -1:
            self.log('Unable to find playlist header for the file: ' + filename)
            self.processingSemaphore.release()
            return False

        # past the header, so get the info
        for i in range(len(lines)):
            time.sleep(0)

            if realindex + 1 >= len(lines):
                break

            if len(self.itemlist) > 16384:
                break

            try:
                line = uni(lines[realindex].rstrip())
            except Exception,e:
                self.log("ERROR: Invalid line in playlist - " + filename)
                self.log(traceback.format_exc(), xbmc.LOGERROR)

            if line[:8] == '#EXTINF:':
                tmpitem = PlaylistItem()
                index = line.find(',')

                if index > 0:
                    tmpitem.duration = int(line[8:index])
                    tmpitem.title = line[index + 1:]
                    index = tmpitem.title.find('//')

                    if index >= 0:
                        tmpitem.episodetitle = tmpitem.title[index + 2:]
                        tmpitem.title = tmpitem.title[:index]
                        index = tmpitem.episodetitle.find('//')

                        if index >= 0:
                            tmpitem.description = tmpitem.episodetitle[index + 2:]
                            tmpitem.episodetitle = tmpitem.episodetitle[:index]
                            index = tmpitem.description.find('//')
                            
                            if index >= 0:
                                tmpitem.genre = tmpitem.description[index + 2:]
                                tmpitem.description = tmpitem.description[:index]
                                index = tmpitem.genre.find('//')                            
                            
                                if index >= 0:
                                    tmpitem.timestamp = tmpitem.genre[index + 2:]
                                    tmpitem.genre = tmpitem.genre[:index]
                                    index = tmpitem.timestamp.find('//')
                                    
                                    if index >= 0:
                                        tmpitem.LiveID = tmpitem.timestamp[index + 2:]
                                        tmpitem.timestamp = tmpitem.timestamp[:index]
                realindex += 1
                tmpitem.filename = uni(lines[realindex].rstrip())
                self.itemlist.append(tmpitem)
                self.totalDuration += tmpitem.duration

            realindex += 1

        self.processingSemaphore.release()

        if len(self.itemlist) == 0:
            return False

        return True


    def save(self, filename):
        self.log("save " + filename)
        try:
            fle = FileAccess.open(filename, 'w')
        except Exception,e:
            self.log("save Unable to open the smart playlist", xbmc.LOGERROR)
            return

        flewrite = uni("#EXTM3U\n")

        for i in range(self.size()):
            tmpstr = str(self.getduration(i)) + ','
            tmpstr += self.getTitle(i) + "//" + self.getepisodetitle(i) + "//" + self.getdescription(i) + "//" + self.getgenre(i) + "//" + self.gettimestamp(i) + "//" + self.getLiveID(i)
            tmpstr = tmpstr[:2036]
            tmpstr = tmpstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
            tmpstr = tmpstr + '\n' + self.getfilename(i)
            flewrite += "#EXTINF:" + tmpstr + "\n"

        fle.write(flewrite)
        fle.close()

