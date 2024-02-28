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
from rules      import RulesList
from xmltvs     import XMLTVS
from seasonal   import Seasonal
from jsonrpc    import JSONRPC
from xsp        import XSP
from m3u        import M3U
from fillers    import Fillers
from resources  import Resources

class Builder:
    loopback   = {}
    
    
    def __init__(self, service=None):
        #global dialog
        self.pDialog    = None
        self.pCount     = 0
        self.pMSG       = ''
        self.pName      = ''
        self.pErrors    = []
        
        #global rules
        self.incStrms         = SETTINGS.getSettingBool('Enable_Strms')
        self.inc3D            = SETTINGS.getSettingBool('Enable_3D')
        self.incExtras        = SETTINGS.getSettingBool('Enable_Extras') 
        self.fillBCTs         = SETTINGS.getSettingBool('Enable_Fillers')
        self.accurateDuration = bool(SETTINGS.getSettingInt('Duration_Type'))
        self.epgArt           = SETTINGS.getSettingInt('EPG_Artwork')
        self.enableGrouping   = SETTINGS.getSettingBool('Enable_Grouping')
        self.limit            = SETTINGS.getSettingInt('Page_Limit')
        self.filter           = {}                           #"filter":{"and": [{"operator": "contains", "field": "title", "value": "Star Wars"},{"operator": "contains", "field": "tag", "value": "Good"}]}
        self.sort             = {}                           #"sort":{"ignorearticle":true,"method":"random","order":"ascending","useartistsortname":true}
        self.limits           = {}                           #"limits":{"end":0,"start":0,"total":0}

        self.minDuration      = SETTINGS.getSettingInt('Seek_Tolerance')
        self.maxDays          = MAX_GUIDEDAYS
        self.minEPG           = 10800 #Secs., Min. EPG guidedata
        self.completeBuild    = True
        
        self.service    = service
        self.cache      = Cache()
        self.channels   = Channels()
        self.rules      = RulesList(self.channels.getChannels())
        self.runActions = self.rules.runActions
        self.xmltv      = XMLTVS()
        self.jsonRPC    = JSONRPC()
        self.xsp        = XSP()
        self.m3u        = M3U()
        self.fillers    = Fillers(self)
        self.resources  = Resources(self.jsonRPC,self.cache)
           
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def verify(self, channels=None):
        if channels is None: channels = self.channels.getChannels()
        for idx, citem in enumerate(channels):
            if self.service._interrupt(): break
            elif not citem.get('id'):
                self.log('verify, skipping - missing channel id\n%s'%(citem))
                continue
            self.log('verify, channel %s: %s - %s'%(citem['number'],citem['name'],citem['id']))
            yield self.runActions(RULES_ACTION_CHANNEL_VERIFY, citem, citem, inherited=self)
            
            
    @timeit
    def build(self):
        self.log('build')
        channels = sorted(self.verify(self.channels.getChannels()), key=lambda k: k['number'])
        if not channels: return False
        
        now       = getUTCstamp()
        start     = roundTimeDown(getUTCstamp(),offset=60)#offset time to start bottom of the hour
        stopTimes = dict(self.xmltv.loadStopTimes(fallback=datetime.datetime.fromtimestamp(start).strftime(DTFORMAT)))
        self.pDialog = DIALOG.progressBGDialog()
        
        for idx, citem in enumerate(channels):
            if self.service._interrupt(): break
            elif self.service._suspend():
                self.completeBuild = False
                break
            else:
                self.runActions(RULES_ACTION_CHANNEL_START, citem, inherited=self)
                self.pName  = citem['name']
                self.pCount = int(idx*100//len(channels))
                
                if stopTimes.get(citem['id'],start) > (now + ((self.maxDays * 86400) - 43200)):
                    self.pMSG = '%s %s'%(LANGUAGE(32028),LANGUAGE(32023)) #Checking
                elif stopTimes.get(citem['id']):
                    self.pMSG = '%s %s'%(LANGUAGE(32022),LANGUAGE(32023)) #Updating
                else:
                    self.pMSG = '%s %s'%(LANGUAGE(32021),LANGUAGE(32023)) #Building
                
                #cacheResponse = {False:'In-Valid Channel w/o programmes)', True:'Valid Channel that exceeds MAX_DAYS', list:'Valid Channel w/ programmes}
                cacheResponse = self.getFileList(citem, now, stopTimes.get(citem['id'],start))
                if cacheResponse:
                    if self.addChannelStation(citem) and (isinstance(cacheResponse,list) and len(cacheResponse) > 0):
                        self.addChannelProgrammes(citem, cacheResponse) #added xmltv lineup entries.
                else: 
                    self.pErrors.append(LANGUAGE(32026))
                    chanErrors = ' | '.join(list(sorted(set(self.pErrors))))
                    self.log('build, In-Valid Channel (%s) %s - %s'%(chanErrors, citem['id'],self.pName))
                    self.pDialog = DIALOG.progressBGDialog(self.pCount, self.pDialog, message='%s: %s'%(self.pName,chanErrors),header='%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(32027),LANGUAGE(32023))))
                    self.delChannelStation(citem)
                    self.service.monitor.waitForAbort(PROMPT_DELAY/1000)
                self.runActions(RULES_ACTION_CHANNEL_STOP, citem, inherited=self)
                    
        self.pDialog = DIALOG.progressBGDialog(100, self.pDialog, message='%s %s'%(self.pMSG,LANGUAGE(32025) if self.completeBuild else LANGUAGE(32135)))
        self.log('build, completeBuild = %s, saved = %s'%(self.completeBuild,self.saveChannelLineups()))
        return self.completeBuild

        
    def getFileList(self, citem, now, start):
        self.log('getFileList, id: %s, start = %s'%(citem['id'],start))
        try:
            citem = self.runActions(RULES_ACTION_CHANNEL_BUILD_START, self.buildProvisional(citem), citem, inherited=self)
            if start > (now + ((self.maxDays * 86400) - 43200)): #max guidedata days to seconds.
                self.log('getFileList, id: %s programmes exceeds MAX_DAYS: start = %s'%(citem['id'],datetime.datetime.fromtimestamp(start)),xbmc.LOGINFO)
                return True# prevent over-building
            
            multi = len(citem['path']) > 1 #multi-path source
            radio = True if citem.get('radio',False) else False
            media = 'music' if radio else 'video'
            self.log('getFileList, id: %s, multi-path = %s, radio = %s, media = %s, path = %s'%(citem['id'],multi,radio,media,citem['path']),xbmc.LOGINFO)

            if radio: cacheResponse = self.buildRadio(citem)
            else:     cacheResponse = self.buildChannel(citem)
            
            if cacheResponse:
                cacheResponse = self.addScheduling(citem, cacheResponse, start)
                if self.fillBCTs and not radio: 
                    cacheResponse = self.fillers.injectBCTs(citem, cacheResponse)
                return sorted(self.runActions(RULES_ACTION_CHANNEL_BUILD_STOP, citem, cacheResponse, inherited=self), key=lambda k: k['start'])
            else: raise Exception('cacheResponse in-valid!')
        except Exception as e: self.log("getFileList, failed! %s"%(e), xbmc.LOGERROR)
        return False

        
    def buildProvisional(self, citem):
        try:
            provisional = re.findall(r"\{(.*?)}", str(citem['path']))[0]#match proper paths for provisional autotune.
            if provisional and not bool(list(set([True for path in citem.get('path',[]) if self.xsp.isDXSP(path)]))): #exclude dynamic paths which trigger false positive during provisional regex.
                if provisional == "Seasonal": #Seasonal
                    citem['seasonal'] = Seasonal().buildSeasonal(citem)
                elif citem['type'] in list(PROVISIONAL_TYPES.keys()): #Autotune
                    citem['provisional'] = {'value':provisional,'json':PROVISIONAL_TYPES.get(citem['type'],{}).get('json',[]),'path':self.jsonRPC.buildProvisionalPaths(provisional,citem['type'])}
        except: pass
        return citem


    def buildCells(self, citem, duration=10800, type='video', entries=3, info={}):
        self.log("buildCells; id: %s"%(citem.get('id')))
        tmpItem  = {'label'       : (info.get('title','')        or citem['name']),
                    'episodetitle': (info.get('episodetitle','') or '|'.join(citem['group'])),
                    'plot'        : (info.get('plot' ,'')        or LANGUAGE(30161)),
                    'genre'       : (info.get('genre','')        or ['Undefined']),
                    'file'        : (info.get('path','')         or '|'.join(citem.get('path'))),
                    'type'        : type,
                    'duration'    : duration,
                    'start'       : 0,
                    'stop'        : 0,
                    'art'         : (info.get('art','') or {"thumb":COLOR_LOGO,"fanart":FANART,"logo":LOGO,"icon":LOGO})}
        return [tmpItem.copy() for idx in range(entries)]


    def addScheduling(self, citem, fileList, start):
        self.log("addScheduling; id: %s, fileList = %s, start = %s"%(citem['id'],len(fileList),start))
        tmpList  = []
        fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_PRE, citem, fileList, inherited=self) #adv. scheduling rules start here.
        for idx, item in enumerate(fileList):
            if not item.get('file',''):
                self.log("addScheduling, id: %s, IDX = %s skipping missing playable file!"%(citem['id'],idx),xbmc.LOGINFO)
                continue
                
            item["idx"]   = idx
            item['start'] = start
            item['stop']  = start + item['duration']
            start = item['stop']
            # print('addScheduling',idx,item['title'],item['start'])
            tmpList.append(item)
            
        #force removal of channel with no current programmes
        if fileList[-1].get('stop') < getUTCstamp():
            self.log("addScheduling; id: %s, last stop = %s, returning empty fileList\nNo Current Programs!!"%(citem['id'],fileList[-1].get('stop')))
            tmpList = []
        return self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_POST, citem, tmpList, inherited=self) #adv. scheduling second pass and cleanup.
        
        
    def buildRadio(self, citem):
        self.log("buildRadio; id: %s"%(citem.get('id')))
        #todo insert custom radio labels,plots based on genre type?
        # https://www.musicgenreslist.com/
        # https://www.musicgateway.com/blog/how-to/what-are-the-different-genres-of-music
        return self.buildCells(citem, self.minEPG, 'music', ((self.maxDays * 8)), info={'genre':["Music"],'art':{'thumb':citem['logo'],'icon':citem['logo'],'fanart':citem['logo']},'plot':LANGUAGE(32029)%(citem['name'])})
        

    def buildChannel(self, citem):
        def validFileList(cacheResponse):
            for fileList in cacheResponse:
                if len(fileList) > 0: return True

        # refactor library queries and path queries, unify to path only queries and create table to convert json requests to dynamic xsp.
        # # build multi-paths as individual arrays for easier interleaving.
        cacheResponse = []
        if citem.get('provisional',None):
            for query in citem['provisional'].get('json',[]):
                if self.service._interrupt(): break
                self.runActions(RULES_ACTION_CHANNEL_BUILD_GLOBAL, citem, query, inherited=self)
                cacheResponse.append(self.buildLibraryList(citem, citem['provisional'].get('value'), query, 'video', self.limit, self.sort, self.filter, self.limits))
        elif citem.get('seasonal',None):
            for file in citem['seasonal']['path']:
                if self.service._interrupt(): break
                self.runActions(RULES_ACTION_CHANNEL_BUILD_GLOBAL, citem, file, inherited=self)
                cacheResponse.append(self.buildFileList(citem, file, 'video', self.limit, self.sort, self.filter, self.limits))
        else:
            for file in citem['path']:
                if self.service._interrupt(): break
                self.runActions(RULES_ACTION_CHANNEL_BUILD_GLOBAL, citem, file, inherited=self)
                cacheResponse.append(self.buildFileList(citem, file, 'video', self.limit, self.sort, self.filter, self.limits))

        if not validFileList(cacheResponse):#check that at least one fileList array contains meta.
            self.log("buildChannel, id: %s skipping channel cacheResponse empty!"%(citem['id']),xbmc.LOGINFO)
            return False
            
        #todo move all interleaving to a channel rule, apply rules by default when multi-path found.
        cacheResponse = list([_f for _f in self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE, citem, cacheResponse, inherited=self) if _f]) #Primary rule for handling adv. interleaving, must return single list to avoid default interleave() below. Add avd. rule to setDictLST duplicates.
        self.log("buildChannel, id: %s cacheResponse arrays = %s"%(citem['id'],len(cacheResponse)))
        cacheResponse = list(interleave(cacheResponse)) # default interleave multi-paths, while keeping order. 
        cacheResponse = list([_f for _f in self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_POST, citem, cacheResponse, inherited=self) if _f]) #Primary rule for handling adv. interleaving, must return single list to avoid default interleave() below. Add avd. rule to setDictLST duplicates.
        self.log('buildChannel, id: %s, cacheResponse items = %s'%(citem['id'],len(cacheResponse)),xbmc.LOGINFO)
        return cacheResponse


    def buildLibraryList(self, citem, value, query, media='video', page=SETTINGS.getSettingInt('Page_Limit'), sort={}, filter={}, limits={}):
        self.log("buildLibraryList; id: %s, media = %s, provisional value = %s\npage = %s, sort = %s, filter = %s, limits = %s\nquery = %s"%(citem['id'],media,value,page,sort,filter,limits,query))
        query['value'] = value
        fileList       = []
        seasoneplist   = []
        
        if not sort:
            sort = {"ignorearticle":True,"method":query.get('sort'),"order":"ascending","useartistsortname":True}
            
        if not filter:
            filter = {"and":[{"field":query.get('field'),"operator":query.get('operator'),"value":[value]}]}
            if not self.incExtras and query.get('sort','').startswith(tuple(TV_TYPES)):
                filter.get("and",[]).extend([{"field":"season","operator":"greaterthan","value":"0"},
                                             {"field":"episode","operator":"greaterthan","value":"0"}])
                
        json_response = self.jsonRPC.requestList(citem, query, media, page, sort, filter, limits)
        key     = list(json_response.keys())[0]
        results = json_response.get(key, [])
        if not results: self.pErrors.append(LANGUAGE(32026))

        for idx, item in enumerate(results):
            if self.service._interrupt() or self.service._suspend():
                self.completeBuild = False
                self.jsonRPC.autoPagination(citem['id'], query.get('value'), limits)
                return []
            else:
                if not isinstance(item, dict):
                    self.log('buildLibraryList, id: %s, item malformed %s'%(citem['id'],item)) #todo debug issue where key is injected into results as a string? ex. results = [{},{},'episode'], bug with keys()?
                    continue
                    
                file = item.get('file','')
                item['type'] = key
                if not file:
                    self.pErrors.append(LANGUAGE(32031))
                    self.log("buildLibraryList, id: %s, IDX = %s skipping missing playable file!"%(citem['id'],idx),xbmc.LOGINFO)
                    continue
                    
                elif not file.startswith(tuple(VFS_TYPES)) and self.accurateDuration:
                    if not FileAccess.exists(file): 
                        self.pErrors.append('%s'%(LANGUAGE(32147)))
                        self.log("buildLibraryList, id: %s, IDX = %s skipping missing file!"%(citem['id'],idx),xbmc.LOGINFO)
                        continue
                
                elif (file.lower().endswith('strm') and not self.incStrms): 
                    self.pErrors.append('%s STRM'%(LANGUAGE(32027)))
                    self.log("buildLibraryList, id: %s, IDX = %s skipping strm!"%(citem['id'],idx),xbmc.LOGINFO)
                    continue
                    
                if not item.get('streamdetails',{}).get('video',[]): #parsing missing meta, kodi rpc bug fails to return streamdetails during Files.GetDirectory.
                    item['streamdetails'] = self.jsonRPC.getStreamDetails(file, media)

                if (self.is3D(item) and not self.inc3D): #requires streamdetails, parse last.
                    self.pErrors.append('%s 3D'%(LANGUAGE(32027)))
                    self.log("buildLibraryList, id: %s, IDX = %s skipping 3D!"%(citem['id'],idx),xbmc.LOGINFO)
                    continue

                dur = self.jsonRPC.getDuration(file, item, self.accurateDuration)
                if dur > self.minDuration: #ignore media that's duration is under the players seek tolerance.
                    item['duration']     = dur
                    item['media']        = media
                    item['originalpath'] = file
                    if item.get("year",0) == 1601: #detect kodi bug that sets a fallback year to 1601 https://github.com/xbmc/xbmc/issues/15554.
                        item['year'] = 0
                        
                    title   = (item.get("title",'') or item.get("label",''))
                    tvtitle = item.get("showtitle",'')
                    
                    if (tvtitle or item['type'].startswith(tuple(TV_TYPES))):# This is a TV show
                        season  = int(item.get("season","0"))
                        episode = int(item.get("episode","0"))
                        if not file.startswith(tuple(VFS_TYPES)) and not self.incExtras and (season == 0 or episode == 0):
                            self.pErrors.append('%s Extras'%(LANGUAGE(32027)))
                            self.log("buildLibraryList, id: %s skipping extras!"%(citem['id']),xbmc.LOGINFO)
                            continue

                        label = tvtitle
                        item["tvshowtitle"]  = tvtitle
                        item["episodetitle"] = title
                        item["episodelabel"] = '%s (%sx%s)'%(title,season,str(episode).zfill(2)) #Episode Title (SSxEE) Mimic Kodi's PVR label format
                        item["showlabel"]    = '%s %s'%(item["tvshowtitle"], '- %s'%(item['episodelabel']) if item['episodelabel'] else '')
                    else: # This is a Movie
                        label = title
                        item["episodetitle"] = item.get("tagline","")
                        item["episodelabel"] = item.get("tagline","")
                        item["showlabel"]    = '%s %s'%(item["title"], '- %s'%(item['episodelabel']) if item['episodelabel'] else '')
            
                    if not label: continue
                    spTitle, spYear = splitYear(label)
                    item['label'] = spTitle
                    if item.get('year',0) == 0 and spYear: #replace missing item year with one parsed from show title
                        item['year'] = spYear
                        
                    item['plot'] = (item.get("plot","") or item.get("plotoutline","") or item.get("description","") or LANGUAGE(30161)).strip()
                    if citem.get('seasonal',{}).get('holiday'):
                        item['plot'] = '[B]%s [/B]\n%s'%(citem.get('seasonal',{}).get('holiday'),item['plot'])
                    
                    item['art']  = item.get('art',{})
                    item.get('art',{})['icon'] = citem['logo']
                    
                    #correct for missing genre meta, some library returns don't include genre. https://github.com/xbmc/xbmc/issues/22955
                    if not item.get('genre'):
                        if citem.get('type') in ["TV Shows","TV Networks"]: item['genre'] = ["Show"]
                        else:                                               item['genre'] = [cleanChannelSuffix(citem.get('name'),citem.get('type'))]
                        
                    if sort.get("method","") == 'episode' and (int(item.get("season","0")) + int(item.get("episode","0"))) > 0: 
                        seasoneplist.append([int(item.get("season","0")), int(item.get("episode","0")), item])
                    else: 
                        fileList.append(item)
                        
                    if self.pDialog: 
                        self.pDialog = DIALOG.progressBGDialog(self.pCount, self.pDialog, message='%s: %s'%(self.pName,int((len(seasoneplist+fileList)*100)//len(results)))+'%',header='%s, %s'%(ADDON_NAME,self.pMSG))
                else: 
                    self.pErrors.append(LANGUAGE(32032))
                    self.log("buildLibraryList, id: %s skipping %s no duration meta found!"%(citem['id'],file),xbmc.LOGINFO)
                    
        if sort.get("method","") == 'episode':
            self.log("buildLibraryList, id: %s, method = episode: sorting."%(citem['id']))
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])
            for seepitem in seasoneplist: 
                fileList.append(seepitem[2])
                
        elif sort.get("method","") == 'random':
            self.log("buildLibraryList, id: %s, method = random: shuffling."%(citem['id']))
            if len(fileList) > 0: fileList = randomShuffle(fileList)
        self.log("buildLibraryList, id: %s returning (%s) files"%(citem['id'],len(fileList)))
        return fileList
        
          
    def buildFileList(self, citem, path, media='video', limit=SETTINGS.getSettingInt('Page_Limit'), sort={}, filter={}, limits={}):
        self.log("buildFileList, id: %s, media = %s, path = %s\nlimit = %s, sort = %s, filter = %s, limits = %s"%(citem['id'],media,path,limit,sort,filter,limits))
        if path.endswith('.xsp'): #smartplaylist - parse xsp for path, filter and sort info.
            paths, ofilter, media, osort = self.xsp.parseSmartPlaylist(path)
            if not sort: sort = osort #restore default sort if new sort not found.
            if len(paths) > 0: #treat 'mixed' smartplaylists as mixed-path mixed content.
                self.log("buildFileList, id: %s, mixed-path smartplaylist detected! changing limits to %s over %s paths\npaths = %s"%(citem['id'], roundupDIV(limit,len(paths)),len(paths),paths),xbmc.LOGINFO)
                return list(interleave([self.buildFileList(citem, file, media, roundupDIV(limit,len(paths)), sort, filter, limits) for file in paths if not self.service._interrupt()]))
        elif 'db://' in path:
            param = {}
            if '?xsp=' in path:  #dynamicplaylist - parse xsp for path, filter and sort info.
                path, ofilter, media, osort = self.xsp.parseDynamicPlaylist(path)
                if not sort:   sort   = osort   #restore default sort if new not found.
                if not filter: filter = ofilter #restore default filter if new not found.

            if   path.startswith('videodb://tvshows/'): type, media, osort = ('episodes','video',{"method": "episode"}) #tvshows
            elif path.startswith('videodb://movies/'):  type, media, osort = ('movies'  ,'video',{"method": "random"})  #movies
            elif path.startswith('musicdb://songs/'):   type, media, osort = ('music'   ,'music',{"method": "random"})  #music
            else:                                       type, media, osort = ('files'   ,'video',{"method": "random"})  #other
            if not sort: sort = osort #add default sorts by db

            if not self.incExtras and type.startswith(tuple(TV_TYPES)):
                filter.setdefault("and",[]).extend([{"field":"season" ,"operator":"greaterthan","value":"0"},
                                                    {"field":"episode","operator":"greaterthan","value":"0"}])

            if sort:   param["order"] = sort
            if filter: param["rules"] = filter
            if param:
                param["type"] = type
                filter  = {} #clear filter since it was injected into the dynamic path.
                flatten = ''
                if type == 'episodes' and '-1/-1/-1/-1/' not in path: flatten = '-1/-1/-1/-1/'
                path ='%s%s?xsp=%s'%(path,flatten,dumpJSON(param))
            self.log("buildFileList, id: %s, dynamic library path detected! augmenting path to %s"%(citem['id'],path),xbmc.LOGINFO)
            
        fileList = []
        dirList  = [{'file':path}]
        self.loopback = {}
        
        self.log("buildFileList, id: %s, limit = %s, sort = %s, filter = %s, limits = %s\npath = %s"%(citem['id'],limit,sort,filter,limits,path))
        while not self.service.monitor.abortRequested() and (len(fileList) < limit):
            #Not all results are flat hierarchies; walk all paths until fileList limit is reached. ie. Plugins with [NEXT PAGE]
            if self.service._interrupt(): break
            elif self.service._suspend():
                self.completeBuild = False
                break
            elif len(dirList) == 0:
                self.log('buildFileList, id: %s, no more folders to parse'%(citem['id']))
                break
            else:
                dir = dirList.pop(0)
                try: 
                    if fileList[0] == {}: fileList.pop(0)
                except: fileList = []
                subfileList, subdirList = self.buildList(citem, dir.get('file'), media, limit, sort, filter, limits, dir)
                fileList += subfileList
                dirList = setDictLST(dirList + subdirList)
                self.log('buildFileList, id: %s, parsing %s, fileList = %s'%(citem['id'],dir.get('file'),len(fileList)))
        try: 
            if fileList[0] == {}: fileList.pop(0)
        except: fileList = []
        self.log("buildFileList, id: %s returning fileList %s / %s"%(citem['id'],len(fileList),limit))
        return fileList


    def buildList(self, citem, path, media='video', page=SETTINGS.getSettingInt('Page_Limit'), sort={}, filter={}, limits={}, dirItem={}):
        self.log("buildList, id: %s, media = %s, path = %s\npage = %s, sort = %s, filter = %s, limits = %s\ndirItem = %s"%(citem['id'],media,path,page,sort,filter,limits,dirItem))
        dirList, fileList, seasoneplist = [], [], []
        json_response = self.jsonRPC.requestList(citem, path, media, page, sort, filter, limits)

        if json_response == self.loopback:# malformed jsonrpc queries will return root response, catch a re-parse and return.
            self.pErrors.append(LANGUAGE(32030))
            self.log("buildList, id: %s, loopback detected using path = %s\nreturning: fileList (%s), dirList (%s)"%(citem['id'],path,len(fileList),len(dirList)))
            return fileList, dirList
        elif json_response: self.loopback = json_response
        else:self.pErrors.append(LANGUAGE(32026))
            
        for idx, item in enumerate(json_response):
            if self.service._interrupt() or self.service._suspend():
                self.completeBuild = False
                self.jsonRPC.autoPagination(citem['id'], path, limits)
                return [], []
            else:
                file     = item.get('file','')
                fileType = item.get('filetype','file')

                if fileType == 'directory':
                    dirList.append(item)
                    self.log("buildList, id: %s, IDX = %s, appending directory: %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                    
                elif fileType == 'file':
                    if not file:
                        self.pErrors.append(LANGUAGE(32031))
                        self.log("buildList, id: %s, IDX = %s, skipping missing playable file! path = %s"%(citem['id'],idx,path),xbmc.LOGINFO)
                        continue
                        
                    elif (file.lower().endswith('strm') and not self.incStrms): 
                        self.pErrors.append('%s STRM'%(LANGUAGE(32027)))
                        self.log("buildList, id: %s, IDX = %s, skipping strm file! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                        continue
                        
                    if not item.get('streamdetails',{}).get('video',[]) and not file.startswith(tuple(VFS_TYPES)): #parsing missing meta, kodi rpc bug fails to return streamdetails during Files.GetDirectory.
                        item['streamdetails'] = self.jsonRPC.getStreamDetails(file, media)

                    if (self.is3D(item) and not self.inc3D): 
                        self.pErrors.append('%s 3D'%(LANGUAGE(32027)))
                        self.log("buildList, id: %s, IDX = %s skipping 3D file! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                        continue

                    dur = self.jsonRPC.getDuration(file, item, self.accurateDuration)
                    if dur > self.minDuration: #ignore media that's duration is under the players seek tolerance.
                        item['duration']     = dur
                        item['media']        = media
                        item['originalpath'] = path #use for path sorting/playback verification 
                        if item.get("year",0) == 1601: item['year'] = 0 #detect kodi bug that sets a fallback year to 1601 https://github.com/xbmc/xbmc/issues/15554.
                            
                        title   = (item.get("title",'')     or item.get("label",'')     or dirItem.get('label',''))
                        tvtitle = (item.get("showtitle",'') or dirItem.get('label',''))

                        if (tvtitle or item['type'].startswith(tuple(TV_TYPES))):# This is a TV show
                            season  = int(item.get("season","0"))
                            episode = int(item.get("episode","0"))
                            if not file.startswith(tuple(VFS_TYPES)) and not self.incExtras and (season == 0 or episode == 0):
                                self.pErrors.append('%s Extras'%(LANGUAGE(32027)))
                                self.log("buildList, id: %s, IDX = %s skipping extras! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                                continue

                            label = tvtitle
                            item["tvshowtitle"]  = tvtitle
                            item["episodetitle"] = title
                            item["episodelabel"] = '%s (%sx%s)'%(title,season,str(episode).zfill(2)) #Episode Title (SSxEE) Mimic Kodi's PVR label format
                            item["showlabel"]    = '%s %s'%(item["tvshowtitle"], '- %s'%(item['episodelabel']) if item['episodelabel'] else '')
                        else: # This is a Movie
                            label = title
                            item["episodetitle"] = item.get("tagline","")
                            item["episodelabel"] = item.get("tagline","")
                            item["showlabel"]    = '%s %s'%(item["title"], '- %s'%(item['episodelabel']) if item['episodelabel'] else '')
                    
                        if not label: continue
                        spTitle, spYear = splitYear(label)
                        item['label'] = spTitle
                        if item.get('year',0) == 0 and spYear: #replace missing item year with one parsed from show title
                            item['year'] = spYear
                            
                        item['plot'] = (item.get("plot","") or item.get("plotoutline","") or item.get("description","") or LANGUAGE(30161)).strip()
                        if citem.get('seasonal',{}).get('holiday'):
                            item['plot'] = '[B]%s [/B]\n%s'%(citem.get('seasonal',{}).get('holiday'),item['plot'])
                        
                        item['art']  = (item.get('art',{})  or dirItem.get('art',{}))
                        item.get('art',{})['icon'] = citem['logo']
                        
                        if sort.get("method","") == 'episode' and (int(item.get("season","0")) + int(item.get("episode","0"))) > 0: 
                            seasoneplist.append([int(item.get("season","0")), int(item.get("episode","0")), item])
                        else: 
                            fileList.append(item)
                            
                        if self.pDialog: 
                            self.pDialog = DIALOG.progressBGDialog(self.pCount, self.pDialog, message='%s: %s'%(self.pName,int((len(seasoneplist+fileList)*100)//len(json_response)))+'%',header='%s, %s'%(ADDON_NAME,self.pMSG))
                    else: 
                        self.pErrors.append(LANGUAGE(32032))
                        self.log("buildList, id: %s, IDX = %s skipping content no duration meta found! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                
        if sort.get("method","") == 'episode':
            self.log("buildList, id: %s, method = episode: sorting."%(citem['id']))
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])
            for seepitem in seasoneplist: 
                fileList.append(seepitem[2])
        elif sort.get("method","") == 'random':
            self.log("buildList, id: %s, method = random: shuffling."%(citem['id']))
            if len(dirList)  > 0: dirList  = randomShuffle(dirList)
            if len(fileList) > 0: fileList = randomShuffle(fileList)
                
        if not fileList: fileList.append({})
        self.log("buildList, id: %s returning (%s) files, (%s) dirs."%(citem['id'],len(fileList),len(dirList)))
        return fileList, dirList


    def isHD(self, item):
        if 'isHD' in item: return item['isHD']
        elif not 'streamdetails' in item: item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and len(details.get('video')) > 0:
            videowidth  = int(details['video'][0]['width']  or '0')
            videoheight = int(details['video'][0]['height'] or '0')
            if videowidth >= 1280 and videoheight >= 720: return True
        return False


    def isUHD(self, item):
        if 'isUHD' in item: return item['isUHD']
        elif not 'streamdetails' in item: item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and len(details.get('video')) > 0:
            videowidth  = int(details['video'][0]['width']  or '0')
            videoheight = int(details['video'][0]['height'] or '0')
            if videowidth > 1920 and videoheight > 1080: return True
        return False
        
        
    def is3D(self, item):
        if 'is3D' in item: return item['is3D']
        elif not 'streamdetails' in item: item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and details.get('video') != [] and len(details.get('video')) > 0:
            stereomode = (details['video'][0]['stereomode'] or '')
            if len(stereomode) > 0: return True
        return False


    def addChannelStation(self, citem):
        self.log('addChannelStation, id: %s'%(citem['id']))
        if citem['catchup']:
            citem['url'] = LIVE_URL.format(addon=ADDON_ID,name=quoteString(citem['name']),chid=quoteString(citem['id']),vid='{catchup-id}',duration='{duration}',start='{Y}-{m}-{d} {H}:{M}:{S}')
            citem['catchup-source'] = BROADCAST_URL.format(addon=ADDON_ID,name=quoteString(citem['name']),chid=quoteString(citem['id']),vid='{catchup-id}',duration='{duration}',start='{Y}-{m}-{d} {H}:{M}:{S}')
        elif citem['radio']:
            citem['url'] = RADIO_URL.format(addon=ADDON_ID,name=quoteString(citem['name']),chid=quoteString(citem['id']),radio=str(citem['radio']),vid='{catchup-id}')
        else:
            citem['url'] = TV_URL.format(addon=ADDON_ID,name=quoteString(citem['name']),chid=quoteString(citem['id']))
        
        citem['logo']  = cleanImage(citem['logo'])
        citem['group'] = cleanGroups(citem, self.enableGrouping)
        self.m3u.addStation(citem)
        return self.xmltv.addChannel(citem)
        
        
    def addChannelProgrammes(self, citem, fileList):
        self.log('addProgrammes, id: %s, fileList = %s'%(citem['id'],len(fileList)))
        for idx, item in enumerate(fileList):
            # print('addScheduling',idx,item['title'],item['start'])
            self.xmltv.addProgram(citem['id'], self.xmltv.getProgramItem(citem, item))
            
        
    def delChannelStation(self, citem):
        self.log('delChannelStation, id: %s'%(citem['id']))
        return self.m3u.delStation(citem) & self.xmltv.delBroadcast(citem)
        
        
    def saveChannelLineups(self):
        self.log('saveChannelLineups')
        return self.m3u._save() & self.xmltv._save()
