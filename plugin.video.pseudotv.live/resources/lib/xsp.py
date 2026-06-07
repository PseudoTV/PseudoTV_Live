#   Copyright (C) 2026 Lunatixz
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

class XSP(object):
    library = Library()
    
    def __init__(self):
        self.jsonRPC    = self.library.jsonRPC
        self.predefined = self.library.predefined


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)
    
    
    def isNode(self, path: str) -> bool:
        if path.lower().endswith('.xml'): return True
        return False
    

    def isXSP(self, path: str) -> bool:
        if path.lower().endswith('.xsp'): return True
        return False
        
    
    def isDXSP(self, path: str) -> bool:
        if 'db://' in path.lower() and '?xsp=' in path.lower(): return True
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
            if match: name = Globals._unescapeString(match.group(1))
            self.log("getName, fle = %s, name = %s"%(fle,name))
        except Exception: self.log("getName, return unable to parse %s"%(fle), xbmc.LOGERROR)
        return name


    def findXSP(self, name: str) -> str:
        self.log("findXSP, name = %s"%(name))
        playlists = self.library.getPlaylists()
        for item in playlists:
            if item.get('name','').lower() == name.lower():
                self.log("findXSP, found = %s"%(item.get('path')))
                return item.get('path')
        return ""
      

    def parseXSP(self, id, file):
        def _createDXSP(tvshow, sort={'order':'ascending','method':'episode'}, operator='is'):
            param = {"type":"episodes","rules":{"and":[],"or":[]},"order":{"direction":sort.get('order','ascending'),"method":sort.get('method','episode'),"ignorearticle":True,"useartistsortname":True}}
            try:
                match = re.compile(r'(.*) \((.*)\)', re.IGNORECASE).search(tvshow)
                year, title = int(match.group(2)), match.group(1)
                param.setdefault("rules",{}).setdefault("and",[]).extend([{"field":"year","operator":f"{operator}","value":[year]},{"field":"tvshow","operator":"is","value":[Globals._quoteString(title)]}])
            except Exception:
                param.setdefault("rules",{}).setdefault("and",[]).append({"field":"tvshow","operator":f"{operator}","value":[Globals._quoteString(tvshow)]})
            return param
        try: 
            xml = FileAccess.open(file, "r")
            dom = parse(xml)
            xml.close()
            
            try:    type = dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value
            except Exception: type = MUSIC_TYPES[0]
            if type.lower() in map(str.lower,MUSIC_TYPES): return []
            else:
                try:    limit = int(dom.getElementsByTagName('limit')[0].childNodes[0].nodeValue)
                except Exception: limit = 0
                    
                if type.lower() == "tvshows":
                    sort  = {}
                    order = dom.getElementsByTagName("order")
                    if order: 
                        try: sort.update({'order':order[0].getAttribute("direction")})
                        except Exception: pass
                        try: sort.update({'method':order[0].firstChild.data})
                        except Exception: pass

                    paths = []
                    for rule in dom.getElementsByTagName("rule"):
                        if rule.getAttribute("field").lower() == "title" and rule.getAttribute("operator").lower() in ["is", "contains"]:
                            for value in rule.getElementsByTagName("value"):
                                if value.firstChild:
                                    paths.append('videodb://tvshows/titles/-1/-1/-1/?xsp=%s'%(FileAccess.dumpJSON(_createDXSP(value.firstChild.data, sort, rule.getAttribute("operator")))))
                    
                    if len(paths) == 0:   
                        items = self.jsonRPC.getDirectory({"directory":file,"media":"video"},True,ADDON_VERSION,datetime.timedelta(minutes=15))[0]
                        for item in items:
                            if item.get('filetype') == 'directory' and item.get('label'):
                                paths.append('videodb://tvshows/titles/-1/-1/-1/?xsp=%s'%(FileAccess.dumpJSON(_createDXSP(item.get('label'), sort))))
                    
                    self.log("[%s] parseXSP [%s], type = %s, sort = %s, paths = %s"%(id,file, type, sort, '\n'.join(paths)))
                    if len(paths) > 0: return paths
        except Exception as e: self.log("[%s] parseXSP [%s], failed! %s"%(id,file,e), xbmc.LOGERROR)
        return [file]
            

    def parseDXSP(self, id, file, filters={}, incExtras: bool=SETTINGS.getSettingBool('Enable_Extras')):
        self.log("[%s] parseDXSP, IN = %s, filters = %s, incExtras = %s"%(id,file,filters,incExtras))
        try:
            path, params = str(file).split('?xsp=')
            if path.lower().startswith('musicdb://'):
                self.log("[%s] parseDXSP, found invalid music path! %s"%(id), xbmc.LOGINFO)
                return ''
        
            params = FileAccess.loadJSON(params)
            params['rules'].update(filters)
            if '-1/-1/-1/' not in path: path = '%s/-1/-1/-1/'%(path.strip('/')) #flatten xsp
            if 'tvshows' in path:
                if not incExtras: #hide seasons and extras
                    params['rules'].setdefault("and",[]).extend([{"field":"season" ,"operator":"greaterthan","value":"0"}, 
                                                                 {"field":"episode","operator":"greaterthan","value":"0"}])
                else:
                    params['rules']['and'] = [r for r in params['rules'].get("and", []) if not (('season' in r or 'episode' in r) and r.get("value") == "0")]
                    params['rules']['and'] = Globals._setDictLST(params['rules']['and'])
            file = '%s?xsp=%s'%(path,FileAccess.dumpJSON(params))
            self.log("[%s] parseDXSP, OUT = %s"%(id,file))
        except Exception as e: self.log("[%s] parseDXSP, failed! %s"%(id,e), xbmc.LOGERROR)
        return file
        
        