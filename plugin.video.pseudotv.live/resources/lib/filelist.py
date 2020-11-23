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
            
        self.videoParser = VideoParser()
            
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def getDuration(self, path, item={}, accurate=None):
        if accurate is None:
            accurate = getSettingBool('Duration_Type') == 1
        self.log("getDuration, accurate = %s, path = %s"%(accurate,path))
        
        duration = 0
        runtime  = int(item.get('runtime','') or item.get('duration','') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration','') or '0')
        if path.startswith(('plugin://','upnp://','pvr://')): return runtime
        
        conditions = [runtime == 0, accurate]
        if True in conditions:
            if path.startswith('stack://'): #handle "stacked" videos:
                stack = (path.replace('stack://','').replace(',,',',')).split(' , ') #todo move to regex match
                for file in stack: duration += self.parseDuration(file, item)
            else: 
                duration = self.parseDuration(path, item)
            if duration > 0: runtime = duration
        self.log("getDuration, path = %s, runtime = %s"%(path,runtime))
        return runtime 
        
        
    def parseDuration(self, path, item={}, save=None):
        cacheName = '%s.parseDuration:.%s'%(ADDON_ID,path)
        duration  = self.cache.get(cacheName)
        runtime   = int(item.get('runtime','') or item.get('duration','') or (item.get('streamdetails',{}).get('video',[]) or [{}])[0].get('duration','') or '0')
        if duration is None:
            try:
                if path.startswith(('http','ftp')):
                    duration = 0
                elif path.startswith(('plugin://','upnp://','pvr://')):
                    duration = runtime
                else:
                    duration = self.videoParser.getVideoLength(path.replace("\\\\", "\\"))
            except Exception as e: 
                log("parseDuration, Failed! " + str(e), xbmc.LOGERROR)
                duration = 0
            self.cache.set(cacheName, duration, checksum=duration, expiration=datetime.timedelta(days=28))
        
        dbid    = item.get('id',-1)
        rundiff = int(percentDiff(runtime,duration))
        self.log("parseDuration, path = %s, runtime = %s, duration = %s, difference = %s"%(path,runtime,duration,rundiff))
        conditions = [(dbid > 0),(runtime != duration),(duration > 0),(rundiff <= 45 or rundiff == 100)]
        if save is None: save = getSettingBool('Store_Duration')
        if save and (False not in conditions):
            self.jsonRPC.setDuration(item['type'], dbid, duration)
        if ((rundiff > 45 and rundiff != 100) or rundiff == 0): duration = runtime
        self.log("parseDuration, returning duration = %s"%(duration))
        return duration
        
        
    def autoPagination(self, id, path, limits={}):
        cacheName = '%s.autoPagination.%s.%s'%(ADDON_ID,id,path)
        if not limits:
            msg = 'get'
            # limits = self.channels.getPage(id) #todo move page to channels.json
            limits = (self.cache.get(cacheName) or {"end": 0, "start": 0, "total": 0})
        else:
            msg = 'set'
            # self.channels.setPage(id, limits) #todo move page to channels.json
            self.cache.set(cacheName, limits, checksum=len(limits), expiration=datetime.timedelta(days=28))
        self.log("%s autoPagination, id = %s, path = %s, limits = %s"%(msg,id,path,limits))
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
        
        self.log('requestList, id = %s, path = %s, params = %s, page = %s'%(id,path,params,page))
        json_response = self.jsonRPC.getDirectory(dumpJSON(params))
        if 'filedetails' in json_response: 
            key = 'filedetails'
        else: 
            key = 'files'
            
        results = json_response.get('result',{})
        items   = results.get(key,[])
        limits  = results.get('limits',params['limits'])
        self.log('requestList, id = %s, response items = %s, key = %s, limits = %s'%(id,len(items),key,limits))
        
        if limits.get('end',0) >= limits.get('total',0): # restart page, exceeding boundaries.
            self.log('requestList, id = %s, resetting page to 0'%(id))
            limits = {"end": 0, "start": 0, "total": 0}
        self.autoPagination(id, path, limits)
        
        if len(items) == 0 and limits.get('start',0) > 0 and limits.get('total',0) > 0:
            self.log("requestList, id = %s, trying again at start page 0"%(id))
            return self.requestList(id, path, media, page, sort, filter, limits)
        
        self.log("requestList, id = %s, return items = %s"%(id,len(items)))
        return items