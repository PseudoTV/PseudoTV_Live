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

from globals    import *
from channels   import Channels
from xmltvs     import XMLTVS
from xsp        import XSP
from m3u        import M3U
from fillers    import Fillers
from resources  import Resources
from seasonal   import Seasonal 
from rules      import RulesList
from itertools  import cycle

class Service(object):
    from jsonrpc import JSONRPC
    jsonRPC = JSONRPC()
    player  = PLAYER()
    monitor = MONITOR()
    def _shutdown(self, wait=1.0) -> bool:
        return (self.monitor.waitForAbort(wait) or PROPERTIES.isPendingShutdown())
    def _interrupt(self) -> bool:
        return (PROPERTIES.isPendingShutdown() or PROPERTIES.isPendingRestart() or PROPERTIES.isPendingInterrupt() or PROPERTIES.isInterruptActivity())
    def _suspend(self, wait=1.0) -> bool:
        pendingSuspend = PROPERTIES.isPendingSuspend()
        return pendingSuspend
    def _sleep(self, wait=1.0):
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) or self._interrupt()): return True
            else: wait -= CPU_CYCLE
        return False

class Builder(object):
    xsp       = XSP()
    xmltv     = XMLTVS()
    m3u       = M3U()
    channels  = Channels()
    loopback  = None
    
    def __init__(self, service=None):
        if service is None: service = Service()
        self.service = service        
        self.jsonRPC = service.jsonRPC
        self.cache   = service.jsonRPC.cache
        
        #global dialog
        self.pCount  = 0
        self.pDialog = None
        self.pMSG    = ''
        self.pName   = ''
        self.pHeader = ''
        self.pErrors = []
        
        #global rules
        self.accurateDuration = bool(SETTINGS.getSettingInt('Duration_Type'))
        self.enableEven       = bool(SETTINGS.getSettingInt('Enable_Even'))
        self.buildFolders     = SETTINGS.getSettingBool('Build_Filler_Folders')
        self.interleaveSet    = SETTINGS.getSettingInt('Interleave_Set')
        self.interleaveRepeat = SETTINGS.getSettingBool('Interleave_Repeat')
        self.incStrms         = SETTINGS.getSettingBool('Enable_Strms')
        self.inc3D            = SETTINGS.getSettingBool('Enable_3D')
        self.incExtras        = SETTINGS.getSettingBool('Enable_Extras') 
        self.fillBCTs         = SETTINGS.getSettingBool('Enable_Fillers')
        self.enableChanged    = SETTINGS.getSettingBool('Enable_Changed')
        self.saveDuration     = SETTINGS.getSettingBool('Store_Duration')
        self.epgArt           = SETTINGS.getSettingInt('EPG_Artwork')
        self.enableGrouping   = SETTINGS.getSettingBool('Enable_Grouping')
        self.minDuration      = SETTINGS.getSettingInt('Seek_Tolerance')
        self.limit            = SETTINGS.getSettingInt('Page_Limit')
        self.incStrmDetails   = False #todo adv. ch rule
        self.padScheduling    = False #todo adv. ch rule
        self.filelistQuota    = False #todo adv. ch rule
        self.schedulingQuota  = True  #todo adv. ch rule
        self.padFilelist      = False #todo adv. ch rule
        self.recursiveDepth   = SETTINGS.getSettingInt('Recursive_Depth') #todo adv. channel rule. set recursive depth.
        
        self.filter           = {}#{"and": [{"operator": "contains", "field": "title", "value": "Star Wars"},{"operator": "contains", "field": "tag", "value": "Good"}],"or":[]}
        self.sort             = {}#{"ignorearticle":True,"method":"random","order":"ascending","useartistsortname":True}
        self.limits           = {"end":-1,"start":0,"total":0}
        
        self.bctTypes         = {"ratings" :{"min":-1, "max":SETTINGS.getSettingInt('Enable_Preroll'), "auto":SETTINGS.getSettingInt('Enable_Preroll') == -1, "enabled":bool(SETTINGS.getSettingInt('Enable_Preroll')), "chance":SETTINGS.getSettingInt('Random_Pre_Chance'),
                                             "sources" :{"ids":SETTINGS.getSetting('Resource_Ratings').split('|'),"paths":[os.path.join(FILLER_LOC,'Ratings' ,'')]},"items":{}},
                                 
                                 "bumpers" :{"min":-1, "max":SETTINGS.getSettingInt('Enable_Preroll'), "auto":SETTINGS.getSettingInt('Enable_Preroll') == -1, "enabled":bool(SETTINGS.getSettingInt('Enable_Preroll')), "chance":SETTINGS.getSettingInt('Random_Pre_Chance'),
                                             "sources" :{"ids":SETTINGS.getSetting('Resource_Bumpers').split('|'),"paths":[os.path.join(FILLER_LOC,'Bumpers' ,'')]},"items":{}},
                                 
                                 "adverts" :{"min":SETTINGS.getSettingInt('Enable_Postroll'), "max":PAGE_LIMIT, "auto":SETTINGS.getSettingInt('Enable_Postroll') == -1, "enabled":bool(SETTINGS.getSettingInt('Enable_Postroll')), "chance":SETTINGS.getSettingInt('Random_Post_Chance'),
                                             "sources" :{"ids":SETTINGS.getSetting('Resource_Adverts').split('|'),"paths":[os.path.join(FILLER_LOC,'Adverts' ,'')]},"items":{}},
                                 
                                 "trailers":{"min":SETTINGS.getSettingInt('Enable_Postroll'), "max":PAGE_LIMIT, "auto":SETTINGS.getSettingInt('Enable_Postroll') == -1, "enabled":bool(SETTINGS.getSettingInt('Enable_Postroll')), "chance":SETTINGS.getSettingInt('Random_Post_Chance'),
                                             "sources" :{"ids":SETTINGS.getSetting('Resource_Trailers').split('|'),"paths":[os.path.join(FILLER_LOC,'Trailers','')]},"items":{}, "incKODI":SETTINGS.getSettingBool('Include_Trailers_KODI')}}

        self.resources        = Resources(service=self.service)
        self.runActions       = RulesList(self.channels.getChannels()).runActions
        self.trailerCache     = (SETTINGS.getCacheSetting('trailerCache', json_data=True) or {})
        self.fillers          = Fillers(self)
        self.log(f'__init__, trailerCache = {len(self.trailerCache)}')


    def __del__(self):
        SETTINGS.setCacheSetting('trailerCache', self.trailerCache, json_data=True)
        self.log(f'__del__, trailerCache = {len(self.trailerCache)}')


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        

    def getVerifiedChannels(self, channels=None):
        channels = sorted(self._verify(channels), key=itemgetter('number'))
        self.log('getVerifiedChannels, channels = %s'%(len(channels)))
        return channels

 
    def _verify(self, channels=None):
        if channels is None: channels = self.channels.getChannels()
        for idx, citem in enumerate(channels):
            if not citem.get('name') or len(citem.get('path',[])) == 0 or not citem.get('number'):
                self.log('[%s] SKIPPING - missing necessary channel meta\n%s'%(citem.get('id'),citem))
                continue
            elif not citem.get('id'):
                citem['id'] = getChannelID(citem['name'],citem['path'],citem['number'],SETTINGS.getMYUUID()) #generate new channelid
            citem['logo'] = self.resources.getLogo(citem,fallback=self.resources.getCache(citem['name']))
            self.log('[%s] VERIFIED - channel %s: %s changed = %s'%(citem['id'],citem['number'],citem['name'],citem.get('changed',False)))
            yield self.runActions(RULES_ACTION_CHANNEL_CITEM, citem, citem, inherited=self) #inject persistent citem changes here

             
    def buildCells(self, citem: dict, duration: int=10800, type: str='video', entries: int=3, info=None) -> list:
        if info is None:
            info = {}
        tmpItem  = {'label'       : (info.get('title')        or citem['name']),
                    'episodetitle': (info.get('episodetitle') or '|'.join(citem.get('group',[]))),
                    'plot'        : (info.get('plot')         or LANGUAGE(32020)),
                    'genre'       : (info.get('genre')        or ['Undefined']),
                    'file'        : (info.get('path')         or info.get('file') or info.get('originalpath') or  '|'.join(citem.get('path',[]))),
                    'art'         : (info.get('art')          or {"thumb":COLOR_LOGO,"fanart":FANART,"logo":LOGO,"icon":LOGO}),
                    'type'        : type,
                    'duration'    : duration,
                    'start'       : 0,
                    'stop'        : 0}
        info.update(tmpItem)
        out = []
        for _ in range(entries):
            out.append(info.copy())
        return out


    def needsUpdate(self, citem: dict):
        state = True
        stop  = self.xmltv.stopTimes.get(citem['id'],-1)#check last stop times
        #max guidedata days to seconds, minus fill buffer (12hrs) in seconds.
        if stop > (getUTCstamp() + ((MAX_GUIDEDAYS * 86400) - 43200)):  state = False
        self.log('[%s] needsUpdate = %s, stop = %s'%(citem['id'],state, stop))
        return state, stop
        


    def buildChannels(self, channels: list=None, stop=-1, preview=False):
        if channels is None:
            channels = []
        def __hasChanged(citem: dict, detect=SETTINGS.getSettingBool('Enable_Changed')) -> bool:
            if not citem.get('changed',False) and detect:
                state = any(set([SETTINGS.getFileCRC(file) for file in citem.get('path',[]) if file.endswith(tuple(KODI_PLAYLISTS + BASIC_PLAYLISTS))]))
            else:
                state = citem.get('changed',False)
            self.log('[%s] buildChannels, __hasChanged = %s'%(citem['id'],state))
            return state
                    
        def __hasProgrammes(citem: dict) -> bool:
            try:
                state = dict(self.xmltv.hasProgrammes([citem])).get(citem['id'],False)
            except:
                state = False
            self.log('[%s] buildChannels, __hasProgrammes = %s'%(citem['id'],state))
            return state

        def __hasFileList(fileList: list, state=False) -> bool:
            if isinstance(fileList,list) and len(fileList) > 0:
                state = True
            self.log('[%s] buildChannels, __hasFileList = %s'%(citem['id'],state))
            return state
        
        def __clrChannel(citem: dict) -> bool:
            self.log('[%s] buildChannels, __clrChannel'%(citem['id']))
            if self.resetPagination(citem) and self.m3u.delStation(citem) and self.xmltv.delBroadcast(citem):
                nonlocal_stop = -1
                stop = nonlocal_stop
                citem['changed'] = False
                return self.channels.addChannel(citem)
                
        def __addStation(citem: dict) -> bool:
            sitem = self.m3u.getStationItem(cleanGroups(citem, self.enableGrouping))
            state = self.m3u.addStation(sitem) and self.xmltv.addChannel(sitem)
            self.log('[%s] buildChannels, __addStation = %s'%(citem['id'],state))
            return state
        
        def __addProgrammes(citem: dict, fileList: list) -> bool:
            state = False
            for item in fileList:
                if self.xmltv.addProgram(citem['id'], self.xmltv.getProgramItem(citem, item)):
                    state = True
            self.log('[%s] buildChannels, __addProgrammes = %s, fileList = %s'%(citem['id'],state,len(fileList)))
            return state
        
        def __setChannels():
            state = self.channels.setChannels()
            self.log('[%s] buildChannels, __setChannels = %s'%(citem['id'],state))
            return state
            
        def __setProgrammes():
            state = self.xmltv._save() and self.m3u._save()
            self.log('[%s] buildChannels, __setProgrammes = %s'%(citem['id'],state))
            return state
        
        if not PROPERTIES.isRunning('Builder.buildChannels'):
            with PROPERTIES.legacy(), PROPERTIES.chkRunning('Builder.buildChannels'):
                channels = self.getVerifiedChannels(channels)
                if len(channels) > 0:
                    completed = set()
                    updated   = set()
                    now       = getUTCstamp()
                    nstart    = roundTimeDown(now,offset=60)#offset time to start bottom of the hour
                    fallback  = epochTime(nstart,tz=False).strftime(DTFORMAT)

                    self.pDialog = None
                    self.pMSG    = ''
                    self.pName   = ''
                    self.pHeader = ''
                    self.pErrors = []
                    
                    for idx, citem in enumerate(channels):
                        self.pCount  = int(idx*100)//len(channels)
                        self.pMSG    = '%s: %s'%(LANGUAGE(32144),LANGUAGE(32212))
                        self.pHeader = ADDON_NAME
                        self.pName   = citem['name']
                        citem = self.runActions(RULES_ACTION_CHANNEL_TEMP_CITEM, citem, citem, inherited=self) #inject temporary citem changes here
                        self.log('[%s] buildChannels, preview = %s, rules = %s'%(citem['id'],preview,citem.get('rules',{})))
                        if self.service._interrupt():
                            self.log("[%s] buildChannels, _interrupt"%(citem['id']))
                            self.pErrors = [LANGUAGE(32160)]
                            self.service._que(self.service.tasks.chkChannels,3,channels[idx:])
                            break
                        elif self.service._suspend():
                            self.log("[%s] buildChannels, _suspend"%(citem['id']))
                            self.service._que(self.service.tasks.chkChannels,3,citem)
                            continue
                        else:
                            if __hasChanged(citem, self.enableChanged):
                                __clrChannel(citem) #clear channel m3u/xmltv
                            if stop < 0:
                                stop  = self.xmltv.stopTimes.get(citem['id'],-1)   #check last stop times
                            if stop < 0:
                                start = nstart
                            else:
                                start = stop #last stop time is the next start time.
                            
                            if    preview:
                                self.pMSG = LANGUAGE(32236)                           #Preview
                            elif  stop > 0:
                                self.pMSG = '%s %s'%(LANGUAGE(32022),LANGUAGE(30223)) #Updating
                            else:
                                self.pMSG = '%s %s'%(LANGUAGE(30014),LANGUAGE(30223)) #Building
                            self.pHeader = f'{ADDON_NAME}, {self.pMSG}'
                            self.log("[%s] buildChannels, stop (%s) - start (%s) => %s"%(citem['id'],stop,start,self.pMSG))

                            if start > 0:
                                response = False
                                with DIALOG._progressDialog(self.pMSG, ADDON_NAME, silent=BUILTIN.isPlaying(), background=not preview) as self.pDialog:
                                    self.runActions(RULES_ACTION_CHANNEL_START, citem, inherited=self)
                                    if citem.get('radio',False):
                                        response = self.buildMusic(citem)
                                    else:
                                        response = self.buildVideo(citem)
                                    #response = {False:'In-Valid Channel', True:'Valid Channel w/o programmes', list:'Valid Channel w/ programmes}
                                    if isinstance(response,list):
                                        response = sorted(self.addScheduling(citem, response, now, start), key=itemgetter('start'))
                                        if not preview and __hasFileList(response):
                                            updated.add(__addProgrammes(citem, response))#add xmltv lineup entries.
                                    elif not response:
                                        self.pErrors.append(LANGUAGE(32026))
                                        chanErrors = ' | '.join(list(sorted(set(self.pErrors))))
                                        self.log('[%s] buildChannels, In-Valid Channel (%s) %s'%(citem['id'],self.pName,chanErrors))
                                        self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message='%s: %s'%(self.pName,chanErrors),header=f'{ADDON_NAME}, {LANGUAGE(32027)} {LANGUAGE(30223)}')
                                        if not __hasProgrammes(citem):
                                            __clrChannel(citem) #remove m3u/xmltv references when no valid programmes found.
                                    self.runActions(RULES_ACTION_CHANNEL_STOP, citem, inherited=self)
                                    if   preview:
                                        return response
                                    elif isinstance(response,list):
                                        response = True
                            else:
                                response = __hasProgrammes(citem)
                            if response: __addStation(citem) #add m3u station if lineup available. 
                            completed.add(response)
                            
                    #save changes
                    if any(completed):
                        self.log('[%s] buildChannels, saved programmes = %s, saved channels = %s'%(citem['id'],__setProgrammes(),__setChannels()))
                        if self.buildFolders: self.service._que(self.service.tasks.chkFillers,4,channels)
                    if any(updated): PROPERTIES.setPropTimer('chkPVRRefresh')
                    self.log('[%s] buildChannels, completed = %s, updated = %s'%(citem['id'],any(completed),any(updated)))
                else:
                    self.log('[%s] buildChannels, no verified channels found!'%(citem['id']))


    def buildMusic(self, citem: dict) -> list:
        self.log("[%s] buildMusic"%(citem['id']))
        #todo insert custom radio labels,plots based on genre type?
        # https://www.musicgenreslist.com/
        # https://www.musicgateway.com/blog/how-to/what-are-the-different-genres-of-music
        return self.buildCells(citem, MIN_EPG_DURATION, 'music', ((MAX_GUIDEDAYS * 8)), info={'genre':["Music"],'art':{'thumb':citem['logo'],'icon':citem['logo'],'fanart':citem['logo']},'plot':LANGUAGE(32029)%(citem['name'])})
        


    def buildVideo(self, citem: dict):
        def _validFileList(fileArray):
            for fileList in fileArray:
                if len(fileList) > 0: return True
            return False
            
        def _injectFillers(citem, fileList, enable=False):#todo refactor
            self.log("[%s] buildVideo: _injectFillers, fileList = %s, enable = %s"%(citem['id'],len(fileList),enable))
            if enable: return self.fillers.injectBCTs(citem,fileList)
            return fileList
          
        def _injectRules(citem):#todo refactor
            def __chkEvenDistro(citem):
                if self.enableEven and not citem.get('rules',{}).get("1000"):
                    nrules = {"1000":{"values":{"0":SETTINGS.getSettingInt('Enable_Even')}}}
                    self.log(" [%s] buildVideo: _injectRules, __chkEvenDistro, new rules = %s"%(citem['id'],nrules))
                    citem.setdefault('rules',{}).update(nrules)
                return citem
            return __chkEvenDistro(citem)
            
        citem     = _injectRules(citem) #inject temporary adv. channel rules here
        fileArray = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE, citem, list(), inherited=self) #inject fileArray thru adv. channel rules here
        self.log("[%s] buildVideo, channel pre fileArray items = %s"%(citem['id'],len(fileArray)),xbmc.LOGINFO)
        
        #Primary rule for handling fileList injection bypassing channel building below.
        if not _validFileList(fileArray): #if valid array bypass channel building
            for idx, paths in enumerate(citem.get('path',[])):
                if self.service._interrupt() or self.service._suspend():
                    self.log("[%s] buildVideo, _interrupt/_suspend"%(citem['id']))
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32213)),header=self.pHeader)
                    return []
                else:
                    if self.xsp.isXSP(paths):
                        paths, self.sort = self.xsp.parseXSP(citem['id'], paths, self.sort)# smartplaylist - convert tvshows/mixed types to multi-path, apply sort methods
                    elif isinstance(paths,str):
                        paths=[paths]
                    for path in paths:
                        if len(paths) > 1: self.pName = '%s %s/%s'%(citem['name'],idx+1,len(paths))
                        self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'{self.pName}',header=self.pHeader)
                        fileList = self.buildFileList(citem, self.runActions(RULES_ACTION_CHANNEL_BUILD_PATH, citem, path, inherited=self), 'video', self.limit, self.sort, self.limits)
                        fileArray.append(fileList)
                        self.log("[%s]  buildVideo, path = %s, fileList = %s"%(citem['id'],path,len(fileList)))
        fileArray = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST, citem, fileArray, inherited=self) #flatten fileArray here to pass as fileList below
        #Primary rule for handling adv. interleaving, must return single list to avoid default interleave() below. Add adv. rule to setDictLST duplicates
        if isinstance(fileArray, list):
            self.log("[%s] buildVideo, channel post fileArray items = %s"%(citem['id'],len(fileArray)),xbmc.LOGINFO)
            if not _validFileList(fileArray):#check that at least one fileList in array contains meta
                self.log("[%s] buildVideo, channel fileArray In-Valid!"%(citem['id']),xbmc.LOGINFO)
                return False
            # self.log("[%s] buildVideo, fileArray = %s"%(citem['id'],','.join(['[%s]'%(len(fileList)) for fileList in fileArray])))
            fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE, citem, interleave(fileArray, self.interleaveSet, self.interleaveRepeat), inherited=self)
            self.log('[%s] buildVideo, pre fileList items = %s'%(citem['id'],len(fileList)),xbmc.LOGINFO)
            fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_POST, citem, _injectFillers(citem, fileList, self.fillBCTs), inherited=self)
            self.log('[%s] buildVideo, post fileList items = %s'%(citem['id'],len(fileList)),xbmc.LOGINFO)
        else:
            fileList = fileArray
        return self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN, citem, fileList, inherited=self)


    def buildFileList(self, citem: dict, path: str, media: str='video', page: int=None, sort=None, limits=None) -> list: #buildChannels channel via vfs path.
        if page is None:
            page = SETTINGS.getSettingInt('Page_Limit')
        if sort is None:
            sort = {}
        if limits is None:
            limits = {"end":-1,"start":0,"total":0}
        self.log("[%s] buildFileList, media = %s, limit = %s, sort = %s, page = %s\npath = %s"%(citem['id'],media,page,sort,limits,path))
        self.loopback = None
        def __padFileList(fileItems, page):
            if page > len(fileItems):
                tmpList   = fileItems * (page // len(fileItems))
                remainder = page % len(fileItems)
                if remainder > 0:
                    tmpList.extend(fileItems[-remainder:])
                self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'padding {remainder} files',header=self.pHeader)
                return tmpList
            return fileItems

        if self.xsp.isDXSP(path):
            path = self.xsp.parseDXSP(citem['id'], path, self.filter, self.incExtras)#dynamicplaylist - correct param issues, inject adv. filters rules.
        
        fileList = []
        dirCount = -1
        dirList  = [{'file':path}]
        self.log("[%s] buildFileList, page = %s, sort = %s, limits = %s\npath = %s"%(citem['id'],page, sort, limits, path))
        monitor = self.service.monitor
        while not monitor.abortRequested() and dirCount < self.recursiveDepth:
            if self.service._interrupt():
                self.log("[%s] buildFileList, _interrupt"%(citem['id']))
                self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32213)), header=self.pHeader)
                return []
            elif self.service._suspend():
                self.log("[%s] buildFileList, _suspend"%(citem['id']))
                self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32145)), header=self.pHeader)
                continue
            elif len(dirList) > 0:
                dirCount += 1
                dir  = dirList.pop(0)
                path = dir.get('file')
                if dir.get("label"):
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'parsing folder: {dir.get("label")}',header=self.pHeader)
                subfileList, subdirList, limits, errors = self.buildList(citem, path, media, abs(page - len(fileList)), sort, limits, dir) #parse all directories under root. Flattened hierarchies required to stream line channel building.
                if subfileList:
                    fileList.extend(subfileList)
                if subdirList:
                    dirList = setDictLST(dirList + subdirList)#recursive path, fill to limit.
                self.log('[%s] buildFileList, adding = %s/%s remaining dirs (%s)\npath = %s, limits = %s'%(citem['id'],len(fileList),page,len(dirList),path,limits))
            elif len(dirList) == 0:
                if self.padFilelist and len(fileList) > 0 and len(fileList) < page:
                    fileList = __padFileList(fileList,page)
                self.log('[%s] buildFileList, no more folders to parse'%(citem['id']))
                break
                
        self.log("[%s] buildFileList, returning fileList %s/%s"%(citem['id'],len(fileList),page))
        return fileList


    def buildList(self, citem: dict, path: str, media: str='video', page: int=None, sort=None, limits=None, dirItem=None, query=None):
        if page is None:
            page = SETTINGS.getSettingInt('Page_Limit')
        if sort is None:
            sort = {}
        if limits is None:
            limits = {"end":-1,"start":0,"total":0}
        if dirItem is None:
            dirItem = {}
        if query is None:
            query = {}
        self.log("[%s] buildList, media = %s, path = %s\npage = %s, sort = %s, query = %s, limits = %s\ndirItem = %s"%(citem['id'],media,path,page,sort,query,limits,dirItem))
        dirList, fileList, seasoneplist = [], [], []
        jsonRPC = self.jsonRPC
        items, nlimits, errors = jsonRPC.requestList(citem, path, media, page, sort, self.filter, limits, query)
        
        if errors.get('message'):
            self.pErrors.append(errors['message'])
            return fileList, dirList, nlimits, errors
            
        elif items == self.loopback and limits != nlimits:# malformed jsonrpc queries will return root response, catch a re-parse and return.
            self.log("[%s] buildList, loopback detected using path = %s\nreturning: fileList (%s), dirList (%s)"%(citem['id'],path,len(fileList),len(dirList)))
            self.pErrors.append(LANGUAGE(32030))
            return fileList, dirList, nlimits, errors
            
        elif not items and len(fileList) == 0:
            self.log("[%s] buildList, no request items found using path = %s\nreturning: fileList (%s), dirList (%s)"%(citem['id'],path,len(fileList),len(dirList)))
            self.pErrors.append(LANGUAGE(32026))
            return fileList, dirList, nlimits, errors
            
        elif items:
            self.loopback = items
            for idx, item in enumerate(items):
                file        = item.get('file','')
                fileType    = item.get('filetype','file')
                self.fCount = int(idx*100)//len(items)
                if self.service._interrupt() or self.service._suspend():
                    self.log("[%s] buildList, _interrupt/_suspend"%(citem['id']))
                    jsonRPC.autoPagination(citem['id'], path, query, limits) #rollback pagination limits
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32213)), header=self.pHeader)
                    return [], [], nlimits, errors
                    
                if not item.get('type'):
                    item['type'] = query.get('key','files')
                if fileType == 'directory':
                    dirList.append(item)
                    continue
                if fileType != 'file':
                    continue

                self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'{self.pName}: {self.fCount}%',header=self.pHeader)
                if file.startswith('pvr://'): #parse encoded fileitem otherwise no relevant meta provided via org. query. playable pvr:// paths are limited in Kodi.
                    self.log("[%s] buildList, IDX = %s, PVR item => FileItem! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                    item = decodePlot(item.get('plot',''))
                    file = item.get('file')
                        
                if not file:
                    self.pErrors.append(LANGUAGE(32031))
                    self.log("[%s] buildList, IDX = %s, skipping missing playable file! path = %s"%(citem['id'],idx,path),xbmc.LOGINFO)
                    continue
                        
                if (file.lower().endswith('strm') and not self.incStrms): 
                    self.pErrors.append('%s STRM'%(LANGUAGE(32027)))
                    self.log("[%s] buildList, IDX = %s, skipping strm file! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                    continue
                        
                if self.incStrmDetails and not item.get('streamdetails',{}).get('video',[]) and not file.startswith(tuple(VFS_TYPES)): #parsing missing meta, kodi rpc bug fails to return streamdetails during Files.GetDirectory.
                    item['streamdetails'] = jsonRPC.getStreamDetails(file, media)

                if not self.inc3D and self.is3D(item):
                    self.pErrors.append('%s 3D'%(LANGUAGE(32027)))
                    self.log("[%s] buildList, IDX = %s skipping 3D file! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                    continue

                title   = (item.get("title")     or item.get("label") or dirItem.get('label') or '')
                tvtitle = (item.get("showtitle") or item.get("label") or dirItem.get('label') or '')
                if (item['type'].startswith(tuple(TV_TYPES)) or item.get("showtitle")):# This is a TV show
                    season  = int(item.get("season","0"))
                    episode = int(item.get("episode","0"))
                    if not file.startswith(tuple(VFS_TYPES)) and not self.incExtras and (season == 0 or episode == 0):
                        self.pErrors.append('%s Extras'%(LANGUAGE(32027)))
                        self.log("[%s] buildList, IDX = %s skipping extras! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                        continue

                    label = tvtitle
                    item["tvshowtitle"]  = tvtitle
                    item["episodetitle"] = title
                    item["episodelabel"] = '%s%s'%(title,' (%sx%s)'%(season,str(episode).zfill(2))) #Episode Title (SSxEE) Mimic Kodi's PVR label format
                    item["showlabel"]    = '%s%s'%(item["tvshowtitle"],' - %s'%(item['episodelabel']) if item['episodelabel'] else '')
                else: # This is a Movie
                    label = title
                    item["episodetitle"] = item.get("tagline","")
                    item["episodelabel"] = item.get("tagline","")
                    item["showlabel"]    = '%s%s'%(item.get("title",""), ' - %s'%(item['episodelabel']) if item['episodelabel'] else '')
                
                if not label: 
                    self.pErrors.append(LANGUAGE(32018)(LANGUAGE(30188)))
                    continue
                    
                dur = jsonRPC.getDuration(file, item, self.accurateDuration, self.saveDuration)
                if dur > self.minDuration: #include media that's duration is above the players seek tolerance & users adv. rule
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'{self.pName}: {self.fCount}%',header=self.pHeader)
                    item['duration']     = dur
                    item['media']        = media
                    item['originalpath'] = path #use for path sorting/playback verification 
                    item['friendly']     = PROPERTIES.getFriendlyName()
                    item['remote']       = PROPERTIES.getRemoteHost()
                        
                    if item.get("year",0) == 1601:
                        item['year'] = 0 #detect kodi bug that sets a fallback year to 1601 https://github.com/xbmc/xbmc/issues/15554
                    spTitle, spYear = splitYear(label)
                    item['label'] = spTitle
                        
                    if item.get('year',0) == 0 and spYear:
                        item['year'] = spYear #replace missing item year with one parsed from show title
                    item['plot'] = (item.get("plot","") or item.get("plotoutline","") or item.get("description","") or LANGUAGE(32020)).strip()
                        
                    if query.get('holiday'):
                        citem['holiday'] = query.get('holiday')
                        holiday = "[B]%s[/B] - [I]%s[/I]"%(query["holiday"]["name"],query["holiday"]["tagline"]) if query["holiday"]["tagline"] else "[B]%s[/B]"%(query["holiday"]["name"])
                        item["plot"] = "%s \n%s"%(holiday,item["plot"])

                    item['art'] = (item.get('art',{}) or dirItem.get('art',{}))
                    item.get('art',{})['icon'] = citem['logo']
                        
                    if self.bctTypes['trailers'].get('enabled',False) and item.get('trailer'):
                        self.setTrailers(item)
                    if sort.get("method","") == 'episode' and (int(item.get("season","0")) + int(item.get("episode","0"))) > 0: 
                        seasoneplist.append([int(item.get("season","0")), int(item.get("episode","0")), item])
                    else: 
                        fileList.append(item)
                else: 
                    self.pErrors.append(LANGUAGE(32032))
                    self.log("[%s] buildList, IDX = %s skipping content no duration meta found! or runtime below minDuration (%s/%s) file = %s"%(citem['id'],idx,dur,self.minDuration,file),xbmc.LOGINFO)

            if sort.get("method","").startswith('episode'):
                self.log("[%s] buildList, sorting by episode"%(citem['id']))
                seasoneplist.sort(key=lambda seep: seep[1])
                seasoneplist.sort(key=lambda seep: seep[0])
                for seepitem in seasoneplist: 
                    fileList.append(seepitem[2])
                    
            elif sort.get("method","") == 'random':
                self.log("[%s] buildList, random shuffling"%(citem['id']))
                dirList  = randomShuffle(dirList)
                fileList = randomShuffle(fileList)
                
            self.log("[%s] buildList, returning (%s) files, (%s) dirs"%(citem['id'],len(fileList),len(dirList)))
            return fileList, dirList, nlimits, errors


    def addScheduling(self, citem: dict, fileList: list, now: int, start: int) -> list: #quota meet MIN_EPG_DURATION requirements. 
        self.log("[%s] addScheduling, IN fileList = %s, now = %s, start = %s"%(citem['id'],len(fileList),now,start))
        totDur   = 0
        tmpList  = []
        fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_PRE, citem, fileList, inherited=self)
        for idx, item in enumerate(fileList):
            item["idx"]   = idx
            item['start'] = start
            item['stop']  = start + item['duration']
            start = item['stop']
            tmpList.append(item)
            
        if self.padScheduling and len(tmpList) > 0:
            iters = cycle(fileList)
            monitor = self.service.monitor
            while not monitor.abortRequested() and tmpList[-1].get('stop') <= (now + MIN_EPG_DURATION):
                if self.service._interrupt():
                    self.log("[%s] addScheduling, _interrupt"%(citem['id']))
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32213)), header=self.pHeader)
                    return []
                elif tmpList[-1].get('stop') >= (now + MIN_EPG_DURATION):
                    break
                else: 
                    idx += 1
                    item = next(iters).copy()
                    item["idx"]   = idx
                    item['start'] = start
                    item['stop']  = start + item['duration']
                    start = item['stop']
                    totDur += item['duration']
                    tmpList.append(item)
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f"{self.pName}: {LANGUAGE(33085)} {totDur}/{MIN_EPG_DURATION}",header=self.pHeader)
                    self.log("[%s] addScheduling, ADD fileList = %s, totDur = %s/%s, stop = %s"%(citem['id'],len(tmpList),totDur,MIN_EPG_DURATION,tmpList[-1].get('stop')))
        self.log("[%s] addScheduling, OUT fileList = %s, stop = %s"%(citem['id'],len(tmpList),tmpList[-1].get('stop')))
        return self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_POST, citem, tmpList, inherited=self) #adv. scheduling second pass and cleanup.


    def isHD(self, item: dict) -> bool:
        if 'isHD' in item:
            return item['isHD']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and len(details.get('video')) > 0:
            videowidth  = int(details['video'][0]['width']  or '0')
            videoheight = int(details['video'][0]['height'] or '0')
            if (videowidth >= 1280 or videoheight >= 720) and (videowidth < 1920 or videoheight < 1080):
                return True
        return False


    def isUHD(self, item: dict) -> bool:
        if 'isUHD' in item:
            return item['isUHD']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and len(details.get('video')) > 0:
            videowidth  = int(details['video'][0]['width']  or '0')
            videoheight = int(details['video'][0]['height'] or '0')
            if videowidth > 1920 or videoheight > 1080:
                return True
        return False
        
        
    def is3D(self, item: dict) -> bool:
        if 'is3D' in item:
            return item['is3D']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and details.get('video') != [] and len(details.get('video')) > 0:
            stereomode = (details['video'][0]['stereomode'] or [])
            if len(stereomode) > 0:
                return True
        return False


    def setTrailers(self, item):
        dur = self.jsonRPC.getDuration(item.get('trailer'), accurate=True, save=False)
        if dur > 0:
            tdur = dur
            item.update({'label':'%s - %s'%(item.get("label",""),LANGUAGE(30187)),'episodetitle':'%s - %s'%(item.get("episodetitle",""),LANGUAGE(30187)),'episodelabel':'%s - %s'%(item.get("episodelabel",""),LANGUAGE(30187)),'duration':tdur, 'runtime':tdur, 'file':item.get('trailer'), 'streamdetails':{}})
            genres = (item.get('genre',[]) or ['resources'])
            for genre in genres:
                self.trailerCache.setdefault(genre.lower(),[]).append(item)
                        
                        
    def getTrailers(self, genre=None) -> dict:
        if genre:
            return self.trailerCache.get(genre,[])
        return self.trailerCache


    def resetPagination(self, citem):
        if isinstance(citem, list):
            for item in citem:
                self.resetPagination(item)
        else:
            for path in citem.get('path',[]):
                if citem.get('id'):
                    self.jsonRPC.resetPagination(citem.get('id'), path)
        return True
    
        