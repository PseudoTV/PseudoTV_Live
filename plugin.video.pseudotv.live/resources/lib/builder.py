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

from globals    import *
from channels   import Channels
from xmltvs     import XMLTVS
from xsp        import XSP
from m3u        import M3U
from fillers    import Fillers
from resources  import Resources
from seasonal   import Seasonal 
from rules      import RulesList

class Service:
    from jsonrpc import JSONRPC
    player  = PLAYER()
    monitor = MONITOR()
    jsonRPC = JSONRPC()
    def _interrupt(self) -> bool:
        return PROPERTIES.isPendingInterrupt()
    def _suspend(self) -> bool:
        return PROPERTIES.isPendingSuspend()
        
        
class Builder:
    loopback = {}
    
    def __init__(self, service=None):
        if service is None: service = Service()
        self.service      = service        
        self.jsonRPC      = service.jsonRPC
        self.cache        = service.jsonRPC.cache
        self.channels     = Channels()

        #global dialog
        self.pDialog    = None
        self.pCount     = 0
        self.pMSG       = ''
        self.pName      = ''
        self.pErrors    = []
        
        #global rules
        self.accurateDuration = bool(SETTINGS.getSettingInt('Duration_Type'))
        self.enableEven       = bool(SETTINGS.getSettingInt('Enable_Even'))
        self.interleaveValue  = SETTINGS.getSettingInt('Interleave_Value')
        self.incStrms         = SETTINGS.getSettingBool('Enable_Strms')
        self.inc3D            = SETTINGS.getSettingBool('Enable_3D')
        self.incExtras        = SETTINGS.getSettingBool('Enable_Extras') 
        self.fillBCTs         = SETTINGS.getSettingBool('Enable_Fillers')
        self.saveDuration     = SETTINGS.getSettingBool('Store_Duration')
        self.epgArt           = SETTINGS.getSettingInt('EPG_Artwork')
        self.enableGrouping   = SETTINGS.getSettingBool('Enable_Grouping')
        self.minDuration      = SETTINGS.getSettingInt('Seek_Tolerance')
        self.limit            = SETTINGS.getSettingInt('Page_Limit')
        self.padScheduling    = True #todo adv. rule and global opt. 
        
        self.filters          = {}#{"and": [{"operator": "contains", "field": "title", "value": "Star Wars"},{"operator": "contains", "field": "tag", "value": "Good"}],"or":[]}
        self.sort             = {}#{"ignorearticle":True,"method":"random","order":"ascending","useartistsortname":True}
        self.limits           = {"end":-1,"start":0,"total":0}
        self.completedBuild   = False
        
        self.bctTypes         = {"ratings" :{"min":-1, "max":SETTINGS.getSettingInt('Enable_Preroll'), "auto":SETTINGS.getSettingInt('Enable_Preroll') == -1, "enabled":bool(SETTINGS.getSettingInt('Enable_Preroll')), "chance":SETTINGS.getSettingInt('Random_Pre_Chance'),
                                             "sources" :{"ids":SETTINGS.getSetting('Resource_Ratings').split('|'),"paths":[os.path.join(FILLER_LOC,'Ratings' ,'')]},"items":{}},
                                 
                                 "bumpers" :{"min":-1, "max":SETTINGS.getSettingInt('Enable_Preroll'), "auto":SETTINGS.getSettingInt('Enable_Preroll') == -1, "enabled":bool(SETTINGS.getSettingInt('Enable_Preroll')), "chance":SETTINGS.getSettingInt('Random_Pre_Chance'),
                                             "sources" :{"ids":SETTINGS.getSetting('Resource_Bumpers').split('|'),"paths":[os.path.join(FILLER_LOC,'Bumpers' ,'')]},"items":{}},
                                 
                                 "adverts" :{"min":SETTINGS.getSettingInt('Enable_Postroll'), "max":PAGE_LIMIT, "auto":SETTINGS.getSettingInt('Enable_Postroll') == -1, "enabled":bool(SETTINGS.getSettingInt('Enable_Postroll')), "chance":SETTINGS.getSettingInt('Random_Post_Chance'),
                                             "sources" :{"ids":SETTINGS.getSetting('Resource_Adverts').split('|'),"paths":[os.path.join(FILLER_LOC,'Adverts' ,'')]},"items":{}},
                                 
                                 "trailers":{"min":SETTINGS.getSettingInt('Enable_Postroll'), "max":PAGE_LIMIT, "auto":SETTINGS.getSettingInt('Enable_Postroll') == -1, "enabled":bool(SETTINGS.getSettingInt('Enable_Postroll')), "chance":SETTINGS.getSettingInt('Random_Post_Chance'),
                                             "sources" :{"ids":SETTINGS.getSetting('Resource_Trailers').split('|'),"paths":[os.path.join(FILLER_LOC,'Trailers','')]},"items":{}, "incKODI":SETTINGS.getSettingBool('Include_Trailers_KODI')}}

        self.xsp              = XSP()
        self.xmltv            = XMLTVS()
        self.m3u              = M3U()
        self.resources        = Resources(service=self.service)
        self.runActions       = RulesList(self.channels.getChannels()).runActions


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def updateProgress(self, percent, message, header):
        """Utility function to update progress dialogs."""
        if self.pDialog: self.pDialog = DIALOG.updateProgress(percent, self.pDialog, message=message, header=header)


    def getVerifiedChannels(self):
        return sorted(self.verify(), key=itemgetter('number'))


    def verify(self, channels=None):
        if channels is None: channels = self.channels.getChannels()
        for idx, citem in enumerate(channels):
            if not citem.get('name') or not citem.get('id') or len(citem.get('path',[])) == 0:
                self.log('[%s] SKIPPING - missing necessary channel meta\n%s'%(citem.get('id'),citem))
                continue
            citem['name'] = validString(citem['name']) #todo temp. correct existing file names; drop by v.0.6
            citem['logo'] = self.resources.getLogo(citem,fallback=Seasonal().getHoliday().get('logo',LOGO) if citem['name'] == LANGUAGE(32002) else citem.get('logo',LOGO))
            self.log('[%s] VERIFIED - channel %s: %s'%(citem['id'],citem['number'],citem['name']))
            yield self.runActions(RULES_ACTION_CHANNEL_CITEM, citem, citem, inherited=self) #inject persistent citem changes here


    def build(self, channels: list=[], preview=False):
        def __hasGuideData(citem):
            try:    return dict(self.xmltv.hasProgrammes([citem])).get(citem['id'],False)
            except: return False
            
        def __hasProgrammes(cacheResponse):
            if isinstance(cacheResponse,list):
                if len(cacheResponse) > 0: return True
            return False
        
        def __clrChannel(citem):
            return self.delChannelStation(citem)
        
        if not PROPERTIES.isRunning('builder.build'):
            with PROPERTIES.legacy(), PROPERTIES.chkRunning('builder.build'):
                try:    
                    if len(channels) == 0: raise Exception('No individual channels to update, updating all!')
                    else: channels = sorted(self.verify(channels), key=itemgetter('number'))
                except: channels = self.getVerifiedChannels()
                
                if len(channels) > 0:
                    self.completedBuild = True
                    updated  = set()
                    now      = getUTCstamp()
                    start    = roundTimeDown(now,offset=60)#offset time to start bottom of the hour
                    fallback = datetime.datetime.fromtimestamp(start).strftime(DTFORMAT)
                    clrIDS   = SETTINGS.getResetChannels()
                    
                    if preview: self.pDialog = DIALOG.progressDialog()
                    else:       self.pDialog = DIALOG.progressBGDialog()
                    
                    for idx, citem in enumerate(channels):
                        self.pCount = int(idx*100//len(channels))
                        
                        citem = self.runActions(RULES_ACTION_CHANNEL_TEMP_CITEM, citem, citem, inherited=self) #inject temporary citem changes here
                        self.log('[%s] build, preview = %s, rules = %s'%(citem['id'],preview,citem.get('rules',{})))
                        if self.service._interrupt():                       
                            self.log("[%s] build, _interrupt"%(citem['id']))
                            self.completedBuild = False
                            self.pErrors = [LANGUAGE(32160)]
                            self.updateProgress(self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32213)), header=ADDON_NAME)
                            break
                        else:
                            self.pMSG  = '%s: %s'%(LANGUAGE(32144),LANGUAGE(32212))
                            self.pName = citem['name']
                            self.runActions(RULES_ACTION_CHANNEL_START, citem, inherited=self)
                            
                            if not preview and citem['id'] in clrIDS: __clrChannel({'id':clrIDS.pop(clrIDS.index(citem['id']))}) #clear channel m3u/xmltv
                            stopTimes = dict(self.xmltv.loadStopTimes([citem], fallback=fallback)) #check last stop times
                            
                            if    preview:                                                                           self.pMSG = LANGUAGE(32236)                           #Preview
                            elif  (stopTimes.get(citem['id']) or start) > (now + ((MAX_GUIDEDAYS * 86400) - 43200)): self.pMSG = '%s %s'%(LANGUAGE(32028),LANGUAGE(32023)) #Checking
                            elif  (stopTimes.get(citem['id']) or fallback) == fallback:                              self.pMSG = '%s %s'%(LANGUAGE(30014),LANGUAGE(32023)) #Building
                            elif  stopTimes.get(citem['id']):                                                        self.pMSG = '%s %s'%(LANGUAGE(32022),LANGUAGE(32023)) #Updating
                            else:                                                                                    self.pMSG = '%s %s'%(LANGUAGE(32245),LANGUAGE(32023)) #Parsing  
                            
                            self.updateProgress(self.pCount, message='%s: %s'%(LANGUAGE(32248),self.pName), header='%s, %s'%(ADDON_NAME,self.pMSG))
                            cacheResponse = self.getFileList(citem, now, (stopTimes.get(citem['id']) or start))# {False:'In-Valid Channel', True:'Valid Channel w/o programmes', list:'Valid Channel w/ programmes}
                            if preview: return cacheResponse
                            elif cacheResponse:
                                if self.addChannelStation(citem) and __hasProgrammes(cacheResponse): updated.add(self.addChannelProgrammes(citem, cacheResponse)) #added xmltv lineup entries.
                            else: 
                                if self.completedBuild: self.pErrors.append(LANGUAGE(32026))
                                chanErrors = ' | '.join(list(sorted(set(self.pErrors))))
                                self.log('[%s] build, In-Valid Channel (%s) %s'%(citem['id'],self.pName,chanErrors))
                                self.updateProgress(self.pCount, message='%s: %s'%(self.pName,chanErrors),header='%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(32027),LANGUAGE(32023))))
                                if not __hasGuideData(citem): 
                                    self.updateProgress(self.pCount, message=self.pName,header='%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(32244),LANGUAGE(32023))))
                                    self.delChannelStation(citem) #remove m3u/xmltv references when no valid programmes found. # todo del citem causes issues down the road with citem missing params. reeval need to remove here
                            self.runActions(RULES_ACTION_CHANNEL_STOP, citem, inherited=self)
                         
                    SETTINGS.setResetChannels(clrIDS)       
                    self.pDialog = DIALOG.updateProgress(100, self.pDialog, message='%s %s'%(self.pMSG,LANGUAGE(32025) if self.completedBuild else LANGUAGE(32135)))
                    self.log('build, completed = %s, updated = %s, saved = %s'%(self.completedBuild,bool(updated),self.saveChannelLineups()))
                    return self.completedBuild, bool(updated)
                else: self.log('build, no verified channels found!')
        return False, False
        

    def getFileList(self, citem: dict, now: time, start: time) -> bool and list:
        self.log('[%s] getFileList, start = %s'%(citem['id'],start))
        try:
            if start > (now + ((MAX_GUIDEDAYS * 86400) - 43200)): #max guidedata days to seconds, minus fill buffer (12hrs) in seconds.
                self.updateProgress(self.pCount, message=self.pName, header='%s, %s'%(ADDON_NAME,self.pMSG))
                self.log('[%s] getFileList, programmes over MAX_DAYS! start = %s'%(citem['id'],datetime.datetime.fromtimestamp(start)),xbmc.LOGINFO)
                return True# prevent over-building
            
            multi = len(citem.get('path',[])) > 1 #multi-path source
            radio = True if citem.get('radio',False) else False
            media = 'music' if radio else 'video'
            self.log('[%s] getFileList, multipath = %s, radio = %s, media = %s, path = %s'%(citem['id'],multi,radio,media,citem.get('path')),xbmc.LOGINFO)
            
            if radio: cacheResponse = self.buildRadio(citem)
            else:     cacheResponse = self.buildChannel(citem)
            
            if isinstance(cacheResponse,list): return sorted(self.addScheduling(citem, cacheResponse, now, start, self.padScheduling), key=itemgetter('start'))
            elif self.service._interrupt():   
                self.log("[%s] getFileList, _interrupt"%(citem['id']))
                self.updateProgress(self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32213)), header=ADDON_NAME)
                return True
            else:
                return cacheResponse
        except Exception as e: self.log("[%s] getFileList, failed! %s"%(citem['id'],e), xbmc.LOGERROR)
        return False


    def buildCells(self, citem: dict={}, duration: int=10800, type: str='video', entries: int=3, info: dict={}) -> list:
        tmpItem  = {'label'       : (info.get('title')        or citem['name']),
                    'episodetitle': (info.get('episodetitle') or '|'.join(citem['group'])),
                    'plot'        : (info.get('plot')         or LANGUAGE(32020)),
                    'genre'       : (info.get('genre')        or ['Undefined']),
                    'file'        : (info.get('path')         or info.get('file') or info.get('originalpath') or  '|'.join(citem.get('path'))),
                    'art'         : (info.get('art')          or {"thumb":COLOR_LOGO,"fanart":FANART,"logo":LOGO,"icon":LOGO}),
                    'type'        : type,
                    'duration'    : duration,
                    'start'       : 0,
                    'stop'        : 0}
        info.update(tmpItem)
        return [info.copy() for idx in range(entries)]


    def addScheduling(self, citem: dict, fileList: list, now: time, start: time, padScheduling=True) -> list:
        self.log("[%s] addScheduling, IN fileList = %s, now = %s, start = %s, padScheduling = %s"%(citem['id'],len(fileList),now,start,padScheduling))
        totDur   = 0
        tmpList  = []
        fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_PRE, citem, fileList, inherited=self)
        for idx, item in enumerate(fileList):
            item["idx"]   = idx
            item['start'] = start
            item['stop']  = start + item['duration']
            start = item['stop']
            tmpList.append(item)

        if padScheduling and len(tmpList) > 0:
            iters = cycle(fileList)
            while not self.service.monitor.abortRequested() and tmpList[-1].get('stop') <= (now + MIN_EPG_DURATION):
                if   self.service.monitor.waitForAbort(0.001): break
                elif tmpList[-1].get('stop') >= (now + MIN_EPG_DURATION): 
                    self.log("[%s] addScheduling, OUT fileList = %s, stop = %s"%(citem['id'],len(tmpList),tmpList[-1].get('stop')))
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
                    self.updateProgress(self.pCount, message="%s: %s %s/%s"%(self.pName,LANGUAGE(33085),totDur,MIN_EPG_DURATION),header='%s, %s'%(ADDON_NAME,self.pMSG))
                    self.log("[%s] addScheduling, ADD fileList = %s, totDur = %s/%s, stop = %s"%(citem['id'],len(tmpList),totDur,MIN_EPG_DURATION,tmpList[-1].get('stop')))
        return self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_POST, citem, tmpList, inherited=self) #adv. scheduling second pass and cleanup.
        
        
    def buildRadio(self, citem: dict) -> list:
        self.log("[%s] buildRadio"%(citem['id']))
        #todo insert custom radio labels,plots based on genre type?
        # https://www.musicgenreslist.com/
        # https://www.musicgateway.com/blog/how-to/what-are-the-different-genres-of-music
        return self.buildCells(citem, MIN_EPG_DURATION, 'music', ((MAX_GUIDEDAYS * 8)), info={'genre':["Music"],'art':{'thumb':citem['logo'],'icon':citem['logo'],'fanart':citem['logo']},'plot':LANGUAGE(32029)%(citem['name'])})
        

    def buildChannel(self, citem: dict) -> bool and list:
        def _validFileList(fileArray):
            for fileList in fileArray:
                if len(fileList) > 0: return True
            
        def _injectFillers(citem, fileList, enable=False):
            self.log("[%s] buildChannel: _injectFillers, fileList = %s, enable = %s"%(citem['id'],len(fileList),enable))
            if enable: return Fillers(self,citem).injectBCTs(fileList)
            else:      return fileList
          
        def _injectRules(citem):
            def __chkEvenDistro(citem):
                if self.enableEven and not citem.get('rules',{}).get("1000"):
                    nrules = {"1000":{"values":{"0":SETTINGS.getSettingInt('Enable_Even'),"1":SETTINGS.getSettingInt('Page_Limit'),"2":SETTINGS.getSettingBool('Enable_Even_Force')}}}
                    self.log(" [%s] buildChannel: _injectRules, __chkEvenDistro, new rules = %s"%(citem['id'],nrules))
                    citem.setdefault('rules',{}).update(nrules)
                return citem
            return __chkEvenDistro(citem)
            
        citem     = _injectRules(citem) #inject temporary adv. channel rules here
        fileArray = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE, citem, list(), inherited=self)
        #Primary rule for handling fileList injection bypassing channel building below.
        self.log("[%s] buildChannel, channel pre fileArray items = %s"%(citem['id'],len(fileArray)),xbmc.LOGINFO)
        
        if not _validFileList(fileArray): #if valid array bypass build
            paths = citem.get('path',[])
            for idx, file in enumerate(paths):
                self.counter = 0
                if self.service._interrupt():
                    self.log("[%s]  buildChannel, _interrupt"%(citem['id']))
                    self.updateProgress(self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32213)), header=ADDON_NAME)
                    return []
                else:
                    if len(citem.get('path',[])) > 1: self.pName = '%s %s/%s'%(citem['name'],idx+1,len(citem.get('path',[])))
                    fileArray.append(self.buildFileList(citem, self.runActions(RULES_ACTION_CHANNEL_BUILD_PATH, citem, file, inherited=self), 'video', self.limit, self.sort, self.limits))

        fileArray = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST, citem, fileArray, inherited=self)
        #Primary rule for handling adv. interleaving, must return single list to avoid default interleave() below. Add adv. rule to setDictLST duplicates
        if isinstance(fileArray, list):
            self.log("[%s] buildChannel, channel post fileArray items = %s"%(citem['id'],len(fileArray)),xbmc.LOGINFO)
            if not _validFileList(fileArray):#check that at least one fileList in array contains meta
                self.log("[%s] buildChannel, channel fileArray In-Valid!"%(citem['id']),xbmc.LOGINFO)
                return False
                
            self.log("[%s] buildChannel, fileArray = %s"%(citem['id'],','.join(['[%s]'%(len(fileList)) for fileList in fileArray])))
            fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE, citem, interleave(fileArray, self.interleaveValue), inherited=self)
            self.log('[%s] buildChannel, pre fileList items = %s'%(citem['id'],len(fileList)),xbmc.LOGINFO)
            fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_POST, citem, _injectFillers(citem, fileList, self.fillBCTs), inherited=self)
            self.log('[%s] buildChannel, post fileList items = %s'%(citem['id'],len(fileList)),xbmc.LOGINFO)
        else: fileList = fileArray
        return self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN, citem, fileList, inherited=self)


    def buildFileList(self, citem: dict, path: str, media: str='video', limit: int=SETTINGS.getSettingInt('Page_Limit'), sort: dict={}, limits: dict={}) -> list: #build channel via vfs path.
        self.log("[%s] buildFileList, media = %s, path = %s\nlimit = %s, sort = %s limits = %s"%(citem['id'],media,path,limit,sort,limits))
        fileList = []
        if path.endswith('.xsp'): #smartplaylist - parse xsp for path, sort info
            paths, media, sort, limit = self.xsp.parseXSP(citem.get('id',''), path, media, sort, limit)
            if len(paths) > 0:
                for idx, npath in enumerate(paths):
                    self.pName = '%s %s/%s'%(citem['name'],idx+1,len(paths))
                    fileList.append(self.buildFileList(citem, npath, media, limit, sort, limits))
                return interleave(fileList, self.interleaveValue)
        
        elif 'db://' in path and '?xsp=' in path: #dynamicplaylist - parse xsp for path, filter and sort info
            path, media, sort, filter = self.xsp.parseDXSP(citem.get('id',''), path, sort, {}, self.incExtras) #todo filter adv. rules
            
        nlimits  = limits
        dirList  = [{'file':path}]
        self.loopback = {}
        self.log("[%s] buildFileList, limit = %s, sort = %s, limits = %s\npath = %s"%(citem['id'],limit,sort,limits,path))
        
        while not self.service.monitor.abortRequested():
            #Not all results are flat hierarchies; walk all paths until fileList limit is reached. ie. folders with pagination and/or directories
            if self.service._interrupt(): 
                self.log("[%s] buildFileList, _interrupt"%(citem['id']))
                self.updateProgress(self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32213)), header=ADDON_NAME)
                return []       
            elif self.service._suspend(): 
                self.log("[%s] buildFileList, _suspend"%(citem['id']))
                self.updateProgress(self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32145)), header=ADDON_NAME)
                self.service.monitor.waitForAbort(SUSPEND_TIMER)
                continue
            elif len(fileList) >= limit: break
            elif len(dirList) > 0:
                dir = dirList.pop(0)
                subfileList, subdirList, nlimits, errors = self.buildList(citem, dir.get('file'), media, limit, sort, limits, dir) #parse all directories under root. Flattened hierarchies required to stream line channel building.
                fileList += subfileList
                dirList = setDictLST(dirList + subdirList)
                self.log('[%s] buildFileList, adding = %s/%s remaining dirs (%s)\npath = %s'%(citem['id'],len(subfileList),limit,len(dirList),dir.get('file')))
            elif len(dirList) == 0:
                if len(fileList) < limit and nlimits.get('total') > limit and self.counter < nlimits.get('total',0) and nlimits != limits: 
                    self.log("[%s] buildFileList, retrying (%s/%s) with new autoPagination limits %s"%(citem['id'],self.counter,nlimits.get('total',0),nlimits))
                    self.counter += limit
                    limits = nlimits
                    dirList.insert(0,{'file':path})
                    # fileList.extend(self.buildFileList(citem, path, media, limit, sort, nlimits))
                else:
                    self.log('[%s] buildFileList, no more folders to parse'%(citem['id']))
                    break
        self.log("[%s] buildFileList, returning fileList %s/%s"%(citem['id'],len(fileList),limit))
        return fileList


    def buildList(self, citem: dict, path: str, media: str='video', page: int=SETTINGS.getSettingInt('Page_Limit'), sort: dict={}, limits: dict={}, dirItem: dict={}, query: dict={}):
        self.log("[%s] buildList, media = %s, path = %s\npage = %s, sort = %s, query = %s, limits = %s\ndirItem = %s"%(citem['id'],media,path,page,sort,query,limits,dirItem))
        dirList, fileList, seasoneplist, trailersdict = [], [], [], {}
        items, nlimits, errors = self.jsonRPC.requestList(citem, path, media, page, sort, limits, query)
        
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
                file     = item.get('file','')
                fileType = item.get('filetype','file')
                if not item.get('type'): item['type'] = query.get('key','files')
                
                if self.service._interrupt():
                    self.log("[%s] buildList, _interrupt"%(citem['id']))
                    self.updateProgress(self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32213)), header=ADDON_NAME)
                    self.jsonRPC.autoPagination(citem['id'], path, query, limits) #rollback pagination limits
                    return [], [], nlimits, errors
                    
                elif self.service._suspend(): 
                    self.log("[%s] buildList, _suspend"%(citem['id']))
                    items.insert(idx,item)
                    self.updateProgress(self.pCount, message='%s: %s'%(LANGUAGE(32144),LANGUAGE(32145)), header=ADDON_NAME)
                    self.service.monitor.waitForAbort(SUSPEND_TIMER)
                    continue
                    
                elif fileType == 'directory':
                    dirList.append(item)
                    self.updateProgress(self.pCount, message='%s: %s'%(self.pName,int(idx*100)//page)+'%\nAppending: %s'%(item.get('label')),header='%s, %s'%(ADDON_NAME,self.pMSG))
                    self.log("[%s] buildList, IDX = %s, appending directory: %s"%(citem['id'],idx,file),xbmc.LOGINFO)

                elif fileType == 'file':                        
                    if file.startswith('pvr://'): #parse encoded fileitem otherwise no relevant meta provided via org. query. playable pvr:// paths are limited in Kodi.
                        self.log("[%s] buildList, IDX = %s, PVR item => FileItem! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                        item = decodePlot(item.get('plot',''))
                        file = item.get('file')
                        
                    if not file:
                        self.pErrors.append(LANGUAGE(32031))
                        self.log("[%s] buildList, IDX = %s, skipping missing playable file! path = %s"%(citem['id'],idx,path),xbmc.LOGINFO)
                        continue

                    elif (file.lower().endswith('strm') and not self.incStrms): 
                        self.pErrors.append('%s STRM'%(LANGUAGE(32027)))
                        self.log("[%s] buildList, IDX = %s, skipping strm file! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                        continue
                        
                    if not item.get('streamdetails',{}).get('video',[]) and not file.startswith(tuple(VFS_TYPES)): #parsing missing meta, kodi rpc bug fails to return streamdetails during Files.GetDirectory.
                        item['streamdetails'] = self.jsonRPC.getStreamDetails(file, media)

                    if (self.is3D(item) and not self.inc3D): 
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
                        item["showlabel"]    = '%s%s'%(item["title"], ' - %s'%(item['episodelabel']) if item['episodelabel'] else '')
                
                    if not label: 
                        self.pErrors.append(LANGUAGE(32018)(LANGUAGE(30188)))
                        continue
                    
                    dur = self.jsonRPC.getDuration(file, item, self.accurateDuration, self.saveDuration)
                    if dur > self.minDuration: #include media that's duration is above the players seek tolerance & users adv. rule
                        self.updateProgress(self.pCount, message='%s: %s'%(self.pName,int(idx*100)//page)+'%',header='%s, %s'%(ADDON_NAME,self.pMSG))
                        
                        item['duration']     = dur
                        item['media']        = media
                        item['originalpath'] = path #use for path sorting/playback verification 
                        item['friendly']     = SETTINGS.getFriendlyName()
                        item['remote']       = PROPERTIES.getRemoteHost()
                        
                        if item.get("year",0) == 1601: item['year'] = 0 #detect kodi bug that sets a fallback year to 1601 https://github.com/xbmc/xbmc/issues/15554
                        spTitle, spYear = splitYear(label)
                        item['label'] = spTitle
                        if item.get('year',0) == 0 and spYear: item['year'] = spYear #replace missing item year with one parsed from show title
                            
                        item['plot'] = (item.get("plot","") or item.get("plotoutline","") or item.get("description","") or LANGUAGE(32020)).strip()
                        if query.get('holiday'):
                            citem['holiday'] = query.get('holiday')
                            holiday = "[B]%s[/B] - [I]%s[/I]"%(query["holiday"]["name"],query["holiday"]["tagline"]) if query["holiday"]["tagline"] else "[B]%s[/B]"%(query["holiday"]["name"])
                            item["plot"] = "%s \n%s"%(holiday,item["plot"])

                        item['art'] = (item.get('art',{}) or dirItem.get('art',{}))
                        item.get('art',{})['icon'] = citem['logo']
                        
                        if item.get('trailer') and self.bctTypes['trailers'].get('enabled',False):
                            titem = item.copy()
                            tdur  = self.jsonRPC.getDuration(titem.get('trailer'), accurate=True, save=False)
                            if tdur > 0:
                                titem.update({'label':'%s - %s'%(item["label"],LANGUAGE(30187)),'episodetitle':'%s - %s'%(item["episodetitle"],LANGUAGE(30187)),'episodelabel':'%s - %s'%(item["episodelabel"],LANGUAGE(30187)),'duration':tdur, 'runtime':tdur, 'file':titem['trailer'], 'streamdetails':{}})
                                [trailersdict.setdefault(genre.lower(),[]).append(titem) for genre in (titem.get('genre',[]) or ['resources'])]
                        
                        if sort.get("method","") == 'episode' and (int(item.get("season","0")) + int(item.get("episode","0"))) > 0: 
                            seasoneplist.append([int(item.get("season","0")), int(item.get("episode","0")), item])
                        else: 
                            fileList.append(item)
                    else: 
                        self.pErrors.append(LANGUAGE(32032))
                        self.log("[%s] buildList, IDX = %s skipping content no duration meta found or runtime below minDuration! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)

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
                
            self.getTrailers(trailersdict)
            self.log("[%s] buildList, returning (%s) files, (%s) dirs; parsed (%s) trailers"%(citem['id'],len(fileList),len(dirList),len(trailersdict)))
            return fileList, dirList, nlimits, errors

 
    def isHD(self, item: dict) -> bool:
        if 'isHD' in item: return item['isHD']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and len(details.get('video')) > 0:
            videowidth  = int(details['video'][0]['width']  or '0')
            videoheight = int(details['video'][0]['height'] or '0')
            if videowidth >= 1280 or videoheight >= 720: return True
        return False


    def isUHD(self, item: dict) -> bool:
        if 'isUHD' in item: return item['isUHD']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and len(details.get('video')) > 0:
            videowidth  = int(details['video'][0]['width']  or '0')
            videoheight = int(details['video'][0]['height'] or '0')
            if videowidth > 1920 or videoheight > 1080: return True
        return False
        
        
    def is3D(self, item: dict) -> bool:
        if 'is3D' in item: return item['is3D']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and details.get('video') != [] and len(details.get('video')) > 0:
            stereomode = (details['video'][0]['stereomode'] or [])
            if len(stereomode) > 0: return True
        return False


    def addChannelStation(self, citem: dict) -> bool:
        self.log('[%s] addChannelStation'%(citem['id']))
        citem['logo']  = self.getImage(citem['logo'])
        citem['group'] = cleanGroups(citem, self.enableGrouping)
        sitem = self.m3u.getStationItem(citem)
        return self.m3u.addStation(sitem) & self.xmltv.addChannel(sitem)
        
        
    def addChannelProgrammes(self, citem: dict, fileList: list) -> bool:
        self.log('[%s] addChannelProgrammes, fileList = %s'%(citem['id'],len(fileList)))
        for idx, item in enumerate(fileList): self.xmltv.addProgram(citem['id'], self.xmltv.getProgramItem(citem, item))
        return True
        
        
    def delChannelStation(self, citem: dict) -> bool:
        self.log('[%s] delChannelStation'%(citem['id']))
        return self.m3u.delStation(citem) & self.xmltv.delBroadcast(citem)
        
        
    def saveChannelLineups(self) -> bool:
        self.log('saveChannelLineups')
        return self.xmltv._save() & self.m3u._save()


    def getTrailers(self, nitems: dict={}) -> dict:
        return self.cache.set('kodiTrailers', mergeDictLST((self.cache.get('kodiTrailers', json_data=True) or {}),nitems), expiration=datetime.timedelta(days=28), json_data=True)


    def getImage(self, image):
        return self.resources.buildWebImage(cleanImage(image))