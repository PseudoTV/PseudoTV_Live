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
            match = re.compile(r'<%s>(.*?)\</%s>'%(key,key), re.IGNORECASE).search(string)
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
        

    def parseXSP(self, path: str, media: str='video', sort: dict={}, filter: dict={}, limit: int=SETTINGS.getSettingInt('Page_Limit')):
        try: 
            paths = []
            xml   = FileAccess.open(path, "r")
            dom   = parse(xml)
            xml.close()
            
            try: media = 'music' if dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value.lower() in MUSIC_TYPES else 'video'
            except Exception as e: self.log("parseXSP, no media type", xbmc.LOGDEBUG)
            
            # try: limit = (int(dom.getElementsByTagName('limit')[0].childNodes[0].nodeValue) or limit)
            # except Exception as e: self.log("parseXSP, no limit set", xbmc.LOGDEBUG)

            try: sort.update({"method":dom.getElementsByTagName('order')[0].childNodes[0].nodeValue.lower()}) #todo pop rules to filter var.
            except Exception as e:
                if "method" in sort: sort.pop("method")
                self.log("parseXSP, no sort method", xbmc.LOGDEBUG)
            
            try: sort.update({"order":dom.getElementsByTagName('order')[0].getAttribute('direction').lower()})#todo pop rules to filter var.
            except Exception as e: 
                if "order" in sort: sort.pop("order")
                self.log("parseXSP, no sort direction", xbmc.LOGDEBUG)

            try:
                type = dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value
                if type.lower() in ["mixed"]:
                    for rule in dom.getElementsByTagName('rule'):
                        if rule.getAttribute('field').lower() == 'path' and rule.getAttribute('operator').lower() in ['is']:
                            paths.append(rule.getElementsByTagName("value")[0].childNodes[0].data)
                        elif rule.getAttribute('field').lower() in ['playlist','virtualfolder'] and rule.getAttribute('operator').lower() in ['is']:
                            paths.extend(self.findXSP(rule.getElementsByTagName("value")[0].childNodes[0].data))
            except Exception as e:
                self.log("parseXSP, parsing paths failed! %s"%(e), xbmc.LOGDEBUG)
                type  = ''
                
            self.log("parseXSP, type = %s, media = %s, sort = %s, filter = %s, limit = %s\npaths = %s"%(type, media, sort, filter, limit, paths))
        except Exception as e: self.log("parseXSP, failed! %s"%(e), xbmc.LOGERROR)
        return paths, media, sort, filter, limit
            

    def parseDXSP(self, opath: str, sort: dict={}, filter: dict={}, incExtras: bool=SETTINGS.getSettingBool('Enable_Extras')):
        try:
            path, params = opath.split('?xsp=')
            
            if   path.startswith('videodb://tvshows/'): type = 'episodes'
            elif path.startswith('videodb://movies/'):  type = 'movies'
            elif path.startswith('musicdb://songs/'):   type = 'music'
            else:                                       type = 'files'
            
            if type == 'episodes' and '-1/-1/-1/' not in path: flatten = '-1/-1/-1/'
            else:                                              flatten = ''

            media = 'music' if path.lower().startswith('musicdb://') else 'video'
            param = loadJSON(unquoteString(params))
            sort.update(param.get("order",{}))
            filter.update(param.get("rules",{}))
            
            if not incExtras and type.startswith(tuple(TV_TYPES)): #filter out extras/specials
                filter.setdefault("and",[]).extend([{"field":"season" ,"operator":"greaterthan","value":"0"}, 
                                                    {"field":"episode","operator":"greaterthan","value":"0"}])
                                                    
            param["type"]  = type
            param["order"] = sort
            param["rules"] = filter
            opath = '%s%s?xsp=%s'%(path,flatten,quoteString(dumpJSON(param)))
            self.log("parseDXSP, type = %s, media = %s, sort = %s, filter = %s\npath = %s"%(type, media, sort, {}, opath))
        except Exception as e: self.log("parseDXSP, failed! %s"%(e), xbmc.LOGERROR)
        return opath, media, sort, {}
        
if __name__ == '__main__':
    main()