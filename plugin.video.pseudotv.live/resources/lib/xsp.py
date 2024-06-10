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

# -*- coding: utf-8 -*-

from globals          import *
from library          import Library

class XSP:
    def __init__(self):
        ...


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def isNode(self, path: str) -> bool:
        if path.lower().endswith('.xml'): return True
        return False
    

    def isXSP(self, path: str) -> bool:
        if path.lower().endswith('.xsp'): return True
        return False
        
    
    def isDXSP(self, path: str) -> bool:
        if '?xsp=' in path.lower(): return True
        return False
        
        
    def getName(self, fle: str) -> str:
        try:
            name = ''
            key  = 'name'
            if self.isNode(fle): key = 'label' #node not playlist
            fle = fle.strip('/').replace('library://','special://userdata/library/')
            xml = FileAccess.open(fle, "r")
            string = xml.read()
            xml.close()
            match = re.compile('<%s>(.*?)\</%s>'%(key,key), re.IGNORECASE).search(string)
            if match: name = unescapeString(match.group(1))
            self.log("getName, fle = %s, name = %s"%(fle,name))
        except: self.log("getName, return unable to parse %s"%(fle), xbmc.LOGERROR)
        return name


    def findXSP(self, name: str) -> str:
        self.log("findXSP, name = %s"%(name))
        library   = Library()
        playlists = library.getPlaylists()
        del library
        for item in playlists:
            if item.get('name','').lower() == name.lower():
                self.log("findXSP, found = %s"%(item.get('path')))
                return item.get('path')
        return ""
        

    def parseXSP(self, file: str):
        self.log("parseXSP, file = %s"%(file))
        type   = ''
        media  = 'video'
        paths  = []
        sort   = {}
        filter = {}
        limit  = None
        
        try: 
            xml = FileAccess.open(file, "r")
            dom = parse(xml)
            xml.close()
            media = 'music' if dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value.lower() in MUSIC_TYPES else 'video'
            type  = dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value
            if type.lower() == "mixed":
                try:#todo use operators to build filter list for mixed content.
                    for rule in dom.getElementsByTagName('rule'):
                        if rule.getAttribute('field').lower() == 'path' and rule.getAttribute('operator').lower() in ['is','contains']:
                            paths.append(rule.getElementsByTagName("value")[0].childNodes[0].data)
                        elif rule.getAttribute('field').lower() in ['playlist','virtualfolder'] and rule.getAttribute('operator').lower() in ['is','contains']:
                            paths.extend(self.findXSP(rule.getElementsByTagName("value")[0].childNodes[0].data))
                except Exception as e: self.log("parseXSP, mixed parsing failed! %s"%(e), xbmc.LOGERROR)
            try: sort["method"] = dom.getElementsByTagName('order')[0].childNodes[0].nodeValue.lower()#todo pop rules to filter var.
            except: pass
            try: sort["order"] = dom.getElementsByTagName('order')[0].getAttribute('direction').lower()#todo pop rules to filter var.
            except: pass
            self.log("parseXSP, type = %s, media = %s, paths = %s, sort = %s"%(type, media, paths, sort))
        except Exception as e: self.log("parseXSP, failed! %s"%(e), xbmc.LOGERROR)
        #todo parse limits
        return paths, media, sort, filter, limit


    def parseDXSP(self, path: str):
        media  = 'video'
        sort   = {}
        filter = {}
        limit  = None
        try:
            media = 'music' if path.lower().startswith('musicdb://') else 'video'
            url, params = path.split('?xsp=')
            payload = loadJSON(params)
            if payload: 
                path = url
                if payload.get('order'): sort   = payload.pop('order')
                if payload.get('rules'): filter = payload.pop('rules')
                # if payload.get('limit'): limits  = payload.pop('limit')
            self.log("parseDXSP, path = %s, media = %s, sort = %s, filter = %s"%(path, media, sort, filter))
        except Exception as e: self.log("parseDXSP, failed! %s"%(e), xbmc.LOGERROR)
        return path, media, filter, sort, limit
        
if __name__ == '__main__':
    main()