#   Copyright (C) 2025 Lunatixz
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
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
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
      

    def parseXSP(self, id, file, sort={}):
        def _root(id, file, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
            self.log("[%s] _root, file = %s"%(id,file))
            try:
                items = self.jsonRPC.getDirectory({"directory":file,"media":"video"},True,checksum,expiration)[0]
                return next((self.predefined.createShowPlaylist(item.get('label')) for item in items if item.get('filetype') == 'directory' and item.get('label')),None)
            except: return []
        try: 
            xml = FileAccess.open(file, "r")
            dom = parse(xml)
            xml.close()
            try:
                if dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value.lower() in MUSIC_TYPES: return [], {}
            except Exception as e: self.log("[%s] parseXSP, music/no media found"%(id), xbmc.LOGDEBUG)
            
            try: 
                if int(dom.getElementsByTagName('limit')[0].childNodes[0].nodeValue) != 0: self.log("[%s] parseXSP, invalid configuration set playlist [%s] limit to '0'"%(id,file), xbmc.LOGINFO)
            except Exception as e: self.log("[%s] parseXSP, no limit set"%(id), xbmc.LOGDEBUG)

            paths = []
            type  = dom.getElementsByTagName('smartplaylist')[0].attributes['type'].value
            if type.lower() == "mixed":
                for rule in dom.getElementsByTagName('rule'):
                    if rule.getAttribute('operator').lower() == 'is':
                        if   rule.getAttribute('field').lower() == 'path':     paths.append(rule.getElementsByTagName("value")[0].childNodes[0].data)
                        elif rule.getAttribute('field').lower() == 'playlist': paths.extend(self.findXSP(rule.getElementsByTagName("value")[0].childNodes[0].data))
                        # elif rule.getAttribute('field').lower() == 'virtualfolder': todo refactor for virtualfolder
            elif type.lower() == "tvshows": paths.extend(_root(id,file)) #build dynamic xsp from tvshow, apply sort values.
            else: paths = [file]
                
            if type.lower() in ['mixed','tvshows']:
                try: sort.update({"method":dom.getElementsByTagName('order')[0].childNodes[0].nodeValue.lower()})
                except Exception as e:
                    if "method" in sort: sort.pop("method")
                    self.log("[%s] parseXSP, no sort method, fallback to %s"%(id,sort.get('method')), xbmc.LOGDEBUG)
                
                try: sort.update({"order":dom.getElementsByTagName('order')[0].getAttribute('direction').lower()})
                except Exception as e: 
                    if "order" in sort: sort.pop("order")
                    self.log("[%s] parseXSP, no sort direction, fallback to %s"%(id,sort.get('order')), xbmc.LOGDEBUG)
            self.log("[%s] parseXSP, type = %s, sort = %s, paths = %s"%(id, type, sort, paths))
            return paths, sort
        except Exception as e: self.log("[%s] parseXSP, failed! %s"%(id,e), xbmc.LOGERROR)
        return [file], sort
            

    def parseDXSP(self, id, file, filters={}, incExtras: bool=SETTINGS.getSettingBool('Enable_Extras')):
        self.log("[%s] parseDXSP, IN = %s, filters = %s, incExtras = %s"%(id,file,filters,incExtras))
        try:
            path, params = str(file).split('?xsp=')
            if path.lower().startswith('musicdb://'):
                self.log("[%s] parseDXSP, found invalid music path! %s"%(id), xbmc.LOGINFO)
                return ''
        
            if isinstance(params,str):
                if hasURLencoding(params):
                    params = unquoteString(params)
                params = loadJSON(params)
                
            params['rules'].update(filters)
            if path.startswith('videodb://tvshows/'):
                if '-1/-1/-1/' not in path: path = '%s/-1/-1/-1/'%(path) #flatten tvshows for episodes
                if not incExtras: #hide seasons and extras
                    params['rules'].setdefault("and",[]).extend([{"field":"season" ,"operator":"greaterthan","value":"0"}, 
                                                                 {"field":"episode","operator":"greaterthan","value":"0"}])
                else:
                    params['rules']['and'] = [r for r in params['rules'].get("and", []) if not (('season' in r or 'episode' in r) and r.get("value") == "0")]
                    # next((r for r in params['rules'].get("and", []) if not (('season' in r or 'episode' in r) and r.get("value") == "0")), None)
                params['rules']['and'] = setDictLST(params['rules']['and'])
            file = '%s?xsp=%s'%(path,dumpJSON(params))
            self.log("[%s] parseDXSP, OUT = %s"%(id,file))
        except Exception as e: self.log("[%s] parseDXSP, failed! %s"%(id,e), xbmc.LOGERROR)
        return file
        
        