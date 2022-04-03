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


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    @cacheit(checksum=getInstanceID(),json_data=True)
    def parseSmartPlaylist(self, file):
        sort  = {}
        media = 'video'
        try: 
            xml = FileAccess.open(file, "r")
            dom = parse(xml)
            xml.close()
            try:
                pltype = dom.getElementsByTagName('smartplaylist')
                media  = 'music' if pltype[0].attributes['type'].value.lower() in MUSIC_TYPES else 'video'
            except:pass
            try:
                sort["method"] = dom.getElementsByTagName('order')[0].childNodes[0].nodeValue.lower()
                sort["order"]  = dom.getElementsByTagName('order')[0].getAttribute('direction').lower()
            except: pass
            self.log("parseSmartPlaylist, file = %s, sort = %s"%(file, sort))
        except Exception as e: self.log("parseSmartPlaylist, failed! %s"%(e), xbmc.LOGERROR)
        return media, sort


    @cacheit(checksum=getInstanceID(),json_data=True)
    def parseDynamicPlaylist(self, path):
        sort   = {}
        media  = 'video'
        try:
            media   = 'music' if path.lower().startswith('musicdb://') else 'video'
            payload = loadJSON(path.split('?xsp=')[1])
            if payload: sort = {'order':payload.get('order',{}).get('direction','ascending'), 'method':payload.get('order',{}).get('method','random')}
            else:       sort = {}
            self.log("parseDynamicPlaylist, path = %s, media = %s, sort = %s"%(path, media, sort))
        except Exception as e: self.log("parseDynamicPlaylist, failed! %s"%(e), xbmc.LOGERROR)
        return media, sort