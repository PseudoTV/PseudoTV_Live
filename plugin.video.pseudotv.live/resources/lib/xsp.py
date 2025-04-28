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
        self.library    = Library()
        self.jsonRPC    = self.library.jsonRPC
        self.predefined = self.library.predefined


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
            match = re.compile(r'<%s>(.*?)\</%s>'%(key,key), re.IGNORECASE).search(string)
            if match: name = unescapeString(match.group(1))
            self.log("getName, fle = %s, name = %s"%(fle,name))
        except: self.log("getName, return unable to parse %s"%(fle), xbmc.LOGERROR)
        return name


    def findXSP(self, name: str) -> str:
        self.log("findXSP, name = %s"%(name))
        playlists = self.library.getPlaylists()
        for item in playlists:
            if item.get('name','').lower() == name.lower():
                self.log("findXSP, found = %s"%(item.get('path')))
                return item.get('path')
        return ""
      
      
    def _parseRoot(self, id, path, media='files', checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
        self.log("[%s] _parseRoot, path = %s"%(id,path))
        paths = []
        items = self.jsonRPC.getDirectory({"directory":path,"media":media},True,checksum,expiration).get('files',[])
        [paths.extend(self.predefined.createShowPlaylist(item.get('label'))) for item in items if item.get('filetype') == 'directory' and item.get('label')]
        return paths


    def parseXSP(self, id: str, path: str, media: str='video', sort: dict={}, limit: int=SETTINGS.getSettingInt('Page_Limit')):
        try: 
            paths = []
            xml   = FileAccess.open(path, "r")
            dom   = parse(xml)
            xml.close()
            
            try: media = 'music' if dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value.lower() in MUSIC_TYPES else 'video'
            except Exception as e: self.log("[%s] parseXSP, no media type, fallback to %s"%(id,media), xbmc.LOGDEBUG)
            
            try: limit = int(dom.getElementsByTagName('limit')[0].childNodes[0].nodeValue)
            except Exception as e: self.log("[%s] parseXSP, no limit set, fallback to %s"%(id,limit), xbmc.LOGDEBUG)

            try: sort.update({"method":dom.getElementsByTagName('order')[0].childNodes[0].nodeValue.lower()})
            except Exception as e:
                if "method" in sort: sort.pop("method")
                self.log("[%s] parseXSP, no sort method, fallback to %s"%(id,sort.get('method')), xbmc.LOGDEBUG)
            
            try: sort.update({"order":dom.getElementsByTagName('order')[0].getAttribute('direction').lower()})
            except Exception as e: 
                if "order" in sort: sort.pop("order")
                self.log("[%s] parseXSP, no sort direction, fallback to %s"%(id,sort.get('order')), xbmc.LOGDEBUG)

            try:
                type = dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value
                if type.lower() == "mixed":
                    for rule in dom.getElementsByTagName('rule'):
                        if rule.getAttribute('operator').lower() == 'is':
                            if   rule.getAttribute('field').lower() == 'path':                       paths.append(rule.getElementsByTagName("value")[0].childNodes[0].data)
                            elif rule.getAttribute('field').lower() in ['playlist','virtualfolder']: paths.extend(self.findXSP(rule.getElementsByTagName("value")[0].childNodes[0].data))
                elif type.lower() == "tvshows": paths.extend(list(self._parseRoot(id,path)))
            except Exception as e:
                self.log("[%s] parseXSP, parsing paths failed! %s"%(id,e), xbmc.LOGDEBUG)
                type  = 'Unknown'
                
            self.log("[%s] parseXSP, type = %s, media = %s, sort = %s, limit = %s\npaths = %s"%(id,type, media, sort, limit, paths))
        except Exception as e: self.log("[%s] parseXSP, failed! %s"%(id,e), xbmc.LOGERROR)
        return paths, media, sort, limit
            

    def parseDXSP(self, id: str, opath: str, sort: dict={}, filter: dict={}, incExtras: bool=SETTINGS.getSettingBool('Enable_Extras')):
        try:
            path, params = opath.split('?xsp=')
            media = 'music' if path.lower().startswith('musicdb://') else 'video'
            param = loadJSON(unquoteString(params))
            
            if   path.startswith('videodb://tvshows/'): param["type"] = 'episodes'
            elif path.startswith('videodb://movies/'):  param["type"] = 'movies'
            elif path.startswith('musicdb://songs/'):   param["type"] = 'music'
            else:                                       param["type"] = 'files'
            
            if param["type"] == 'episodes' and '-1/-1/-1/' not in path: flatten = '-1/-1/-1/'
            else:                                                       flatten = ''

            if not incExtras and param["type"].startswith(tuple(TV_TYPES)): #filter out extras/specials
                filter.setdefault("and",[]).extend([{"field":"season" ,"operator":"greaterthan","value":"0"}, 
                                                    {"field":"episode","operator":"greaterthan","value":"0"}])
            if sort: param["order"].update(sort)
            #if filter: param["rules"].update(filter)
            
            opath = '%s%s?xsp=%s'%(path,flatten,quoteString(dumpJSON(param)))
            self.log("[%s] parseDXSP, type = %s, media = %s, sort = %s, filter = %s\npath = %s"%(id,param["type"], media, sort, {}, opath))
        except Exception as e: self.log("[%s] parseDXSP, failed! %s"%(id,e), xbmc.LOGERROR)
        return opath, media, sort, {}
        