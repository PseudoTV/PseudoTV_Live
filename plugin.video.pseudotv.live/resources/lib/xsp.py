#   Copyright (C) 2022 Lunatixz
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

# -*- coding: utf-8 -*-

from resources.lib.globals     import *

class XSP:
    def __init__(self, builder=None):
        if builder is None: return
        self.cache = builder.cache
        self.pool  = builder.pool


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    @cacheit(checksum=getInstanceID(),json_data=True)
    def parseSmartPlaylist(self, file):
        sort  = {}
        media = 'video'
        try: 
            xml   = FileAccess.open(file, "r")
            dom   = parse(xml)
            xml.close()
            try:
                pltype = dom.getElementsByTagName('smartplaylist')
                mediatype = pltype[0].attributes['type'].value
                media = 'music' if mediatype.lower() in MUSIC_TYPES else 'video'
            except:pass
            try:
                sort["method"] = dom.getElementsByTagName('order')[0].childNodes[0].nodeValue.lower()
                sort["order"]  = dom.getElementsByTagName('order')[0].getAttribute('direction').lower()
            except: pass
        except: self.log("parseSmartPlaylist, Unable to open the smart playlist %s"%(file), xbmc.LOGERROR)
        self.log("parseSmartPlaylist, file = %s, media = %s, sort = %s"%(file, media, sort))
        return media, sort


    #todo parse "Mixed" smart-playlist for indv. xsp. buildlist and interleave. 