#   Copyright (C) 2020 Lunatixz
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
from resources.lib.videoparser import VideoParser

class Filelist:
    def __init__(self, cache=None):
        self.log('__init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.videoParser   = VideoParser()
            
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def getDuration(self, path, item={}, accurate=None):
        if accurate is None:
            accurate = getSettingBool('Parse_Duration')
        self.log("getDuration; accurate = %s, path = %s"%(accurate,path))
        duration = 0
        runtime  = int(item.get('runtime','') or item.get('duration','') or '0')
        if accurate == False or path.startswith(('plugin://','upnp://','pvr://')): return runtime
        elif path.startswith('stack://'): #handle "stacked" videos:
            stack = (path.replace('stack://','').replace(',,',',')).split(' , ') #todo move to regex match
            for file in stack: duration += self.parseDuration(file, item)
        else: 
            duration = self.parseDuration(path, item)
        if getSettingBool('Strict_Duration') or duration > 0: 
            return duration
        return runtime 
        
        
    def parseDuration(self, path, item={}):
        cacheName = '%s.parseDuration:.%s'%(ADDON_ID,path)
        duration = self.cache.get(cacheName)
        if duration is None:
            try:
                if path.startswith(('plugin://','upnp://','pvr://')):
                    duration = int(item.get('runtime','') or item.get('duration','0') or '0')
                else:
                    duration = self.videoParser.getVideoLength(path.replace("\\\\", "\\"))
            except Exception as e: 
                log("parseDuration, Failed! " + str(e), xbmc.LOGERROR)
                duration = 0
            self.cache.set(cacheName, duration, checksum=duration, expiration=datetime.timedelta(days=28))
        dbid    = item.get('id',-1)
        runtime = int(item.get('runtime','') or item.get('duration','0') or '0')
        rundiff = int(round(percentDiff(duration,runtime))) #if duration diff less don't save.
        conditions = [(dbid > 0),(runtime != duration), (rundiff > 0), (rundiff <= 25),(duration > 0)]
        if getSettingBool('Store_Duration') and (False not in conditions):
            self.jsonRPC.setDuration(item['type'], dbid, duration)
        self.log("parseDuration, path = %s, duration = %s"%(path,duration))
        return duration
        
        
    def autoPagination(self, id, path, limits={}):
        cacheName = '%s.autoPagination.%s.%s'%(ADDON_ID,id,path)
        if not limits:
            msg = 'get'
            limits = (self.cache.get(cacheName) or {"end": 0, "start": 0, "total": 0})
        else:
            msg = 'set'
            self.cache.set(cacheName, limits, checksum=len(limits), expiration=datetime.timedelta(days=28))
        self.log("%s autoPagination, path = %s, limits = %s"%(msg,path,limits))
        return limits

        
    def requestList(self, id, path, media='video', page=PAGE_LIMIT, sort={}, filter={}, limits={}):
        limits = self.autoPagination(id, path, limits)
        params                      = {}
        params['limits']            = {}
        params['directory']         = escapeDirJSON(path)
        params['media']             = media
        params['properties']        = JSON_FILE_ENUM
        params['limits']['start']   = limits.get('end',0)
        params['limits']['end']     = limits.get('end',0) + page
        if sort:   params['sort']   = sort
        if filter: params['filter'] = filter
        
        self.log('requestList, path = %s, params = %s, page = %s'%(path,params,page))
        json_response = self.jsonRPC.getDirectory(dumpJSON(params))
        if 'filedetails' in json_response: 
            key = 'filedetails'
        else: 
            key = 'files'
            
        results = json_response.get('result',{})
        items   = results.get(key,[])
        limits  = results.get('limits',params['limits'])
        self.log('requestList, response items = %s, key = %s, limits = %s'%(len(items),key,limits))
        
        if limits.get('end',0) >= limits.get('total',0): # restart page, exceeding boundaries.
            self.log('requestList resetting page to 0')
            limits = {"end": 0, "start": 0, "total": 0}
        self.autoPagination(id, path, limits)
        
        if len(items) == 0 and limits.get('start',0) > 0 and limits.get('total',0) > 0:
            self.log("requestList, trying again at start page 0")
            return self.requestList(id, path, media, page, sort, filter, limits)
        
        self.log("requestList return, items size = %s"%len(items))
        return items