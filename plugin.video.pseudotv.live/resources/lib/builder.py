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
from resources.lib.parser      import Writer
from resources.lib.jsonrpc     import JSONRPC
from resources.lib.rules       import RulesList

class Builder:
    def __init__(self, cache=None):
        self.log('__init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.rules            = RulesList()
        self.jsonRPC          = JSONRPC(self.cache)
        self.myPlayer         = self.jsonRPC.myPlayer
        self.myMonitor        = self.jsonRPC.myMonitor
        
        self.writer           = Writer(self.cache)
        self.writer.builder   = self
        self.channels         = self.writer.channels
        
        self.maxDays          = getSettingInt('Max_Days')
        self.incStrms         = getSettingBool('Enable_Strms')
        self.incExtras        = getSettingBool('Enable_Extras')
        self.grouping         = getSettingBool('Enable_Grouping') 
        self.fillBCTs         = getSettingBool('Enable_Fillers')
        self.accurateDuration = getSettingBool('Duration_Type')
        
        self.ruleList         = {}
        self.filter           = {}
        self.sort             = {}
        self.limits           = {}
        self.limit            = PAGE_LIMIT
        self.dialog           = None
        self.progress         = 0
        self.channelCount     = 0
        self.chanName         = ''
        
        self.bctTypes         = {"ratings"    :{"min":1,"max":1,"enabled":True  ,"paths":[getSetting('Resource_Ratings')]},
                                 "trailers"   :{"min":1,"max":1,"enabled":True  ,"paths":[getSetting('Resource_Trailers')]},
                                 "bumpers"    :{"min":1,"max":1,"enabled":False ,"paths":[getSetting('Resource_Networks')]},
                                 "commercials":{"min":1,"max":1,"enabled":False ,"paths":[getSetting('Resource_Commericals')]}}#todo check adv. rules get settings
                                 
                                 
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def runActions(self, action, citem, parameter=None):
        self.log("runActions action = %s, channel = %s"%(action,citem))
        if not citem.get('id',''): return parameter
        ruleList = self.ruleList.get(citem['id'],[])
        for rule in ruleList:
            print(rule.name)
            if action in rule.actions:
                self.log("runActions performing channel rule: %s"%(rule.name))
                parameter = rule.runAction(action, self, parameter)
        return parameter
        

    def buildService(self, channels=None):
        if   isBusy(): return
        elif self.channels.isClient:
            self.log('buildService, Client mode enabled; returning!')
            return False
            
        if not self.writer.reset(): 
            self.log('buildService, initializing m3u/xmltv parser failed!')
            return False
            
        if channels is None: 
            channels = self.getChannelList()
        self.log('buildService, channels = %s'%(len(channels)))
        
        if not channels:
            notificationDialog(LANGUAGE(30056))
            return False

        setBusy(True)
        if getProperty('PseudoTVRunning') != 'True': # legacy setting to disable/enable support in third-party applications. 
            setProperty('PseudoTVRunning','True')
            
        self.dialog       = ProgressBGDialog()
        self.channelCount = len(channels)
        self.ruleList     = self.rules.loadRules(channels)
        
        for idx, channel in enumerate(channels):
            channel       = self.runActions(RULES_ACTION_START, channel, channel)
            self.chanName = channel['name']
            self.progress = (idx*100//len(channels))
            cacheResponse = self.getFileList(channel, channel['radio'])
            cacheResponse = self.runActions(RULES_ACTION_STOP, channel, cacheResponse)
            if cacheResponse: # {True:'Valid Channel (exceed MAX_DAYS)',False:'In-Valid Channel (No guidedata)',list:'fileList (guidedata)'}
                self.writer.addChannel(channel, radio=channel['radio'], catchup=not bool(channel['radio']))
                if isinstance(cacheResponse,list) and len(cacheResponse) > 0:
                    self.dialog = ProgressBGDialog(self.progress, self.dialog, message=self.chanName)
                    self.writer.addProgrammes(channel, cacheResponse, radio=channel['radio'], catchup=not bool(channel['radio']))
            else: 
                self.log('buildService, In-Valid Channel (No guidedata)')
                self.writer.removeChannel(channel)
                
        if not self.writer.save(): 
            notificationDialog(LANGUAGE(30001))
            
        setBusy(False)
        self.dialog = ProgressBGDialog(100, self.dialog, message=LANGUAGE(30053))
        self.log('buildService, finished')
        if not self.myPlayer.isPlaying() and getProperty('PseudoTVRunning') == 'True': # legacy setting to disable/enable support in third-party applications. 
            setProperty('PseudoTVRunning','False') 
        return True


    def getChannelList(self):
        self.log('getChannelList')
        return sorted(self.verifyChannelItems(), key=lambda k: k['number'])
        

    def verifyChannelItems(self):
        if self.channels.reset():
            items = self.channels.getAllChannels()
            for idx, item in enumerate(items):
                self.log('verifyChannelItems, %s: %s'%(idx,item))
                if (not item.get('name','') or not item.get('path',None) or item.get('number',0) < 1): 
                    self.log('verifyChannelItems; skipping, missing channel path and/or channel name\n%s'%(dumpJSON(item)))
                    continue
                    
                item['label']   = (item.get('label','')   or item['name']) #legacy todo remove 'label'
                item['id']      = (item.get('id','')      or getChannelID(item['name'], item['path'], item['number'])) # internal use only; use provided id for future xmltv pairing, else create unique Pseudo ID.
                item['radio']   = (item.get('radio','')   or (item['type'] == LANGUAGE(30097) or 'musicdb://' in item['path']))
                item['catchup'] = (item.get('catchup','') or ('vod' if not item['radio'] else ''))
                item['url']     = 'plugin://%s/?mode=play&name=%s&id=%s&radio=%s'%(ADDON_ID,urllib.parse.quote(item['name']),urllib.parse.quote(item['id']),str(item['radio']))

                logo = item.get('logo','')
                if not logo or logo.startswith((ADDON_PATH,IMAGE_LOC,MEDIA_LOC)): #parse for missing logos when none or defaults.
                    item['logo'] = self.jsonRPC.getLogo(item['name'], item['type'], item['path'], featured=True)
                else: # look for new local logo else use existing
                    item['logo'] = (self.jsonRPC.getLocalLogo(item['name'], featured=True) or logo)

                if not self.grouping: 
                    item['group'] = [ADDON_NAME]
                else:
                    item['group'].append(ADDON_NAME)
                item['group'] = list(set(item['group']))

                # if not item.get('rules',[]): #double check rulelist, not needed! remove?
                    # item['rules'] = self.channels.getChannelRules(item)
                
                yield self.runActions(RULES_ACTION_CHANNEL_CREATION, item, item)


    def addScheduling(self, channel, fileList, start):
        self.log("addScheduling; channel = %s, fileList = %s, start = %s"%(channel,len(fileList),start))
        #todo insert adv. scheduling rules here or move to adv. rules.py
        tmpList  = []
        fileList = self.runActions(RULES_ACTION_CHANNEL_PRE_TIME, channel, fileList)
        for idx, item in enumerate(fileList):
            if not item.get('file',''):
                self.log("addScheduling, id: %s, IDX = %s skipping missing playable file!"%(channel['id'],idx),xbmc.LOGINFO)
                continue
                
            item["idx"]   = idx
            item['start'] = start
            item['stop']  = start + item['duration']
            start = item['stop']
            tmpList.append(item)
        return self.runActions(RULES_ACTION_CHANNEL_POST_TIME, channel, tmpList)
            

    def getFileList(self, citem, radio=False):
        self.log('getFileList; citem = %s, radio = %s'%(citem,radio))
        try:
            # global values prior to channel rules
            self.filter = {}
            self.sort   = {}#{"order": "ascending", "ignorefolders": "false", "method": "random"}
            self.limits = {}#adv. rule to force page.
            self.limit  = PAGE_LIMIT
            
            valid  = False
            now    = getLocalTime()
            start  = self.writer.getEndtime(citem['id'],roundTime(now)) #offset time to start on half hour

            self.runActions(RULES_ACTION_CHANNEL_START, citem)
            if datetime.datetime.fromtimestamp(start) >= (datetime.datetime.fromtimestamp(now) + datetime.timedelta(days=self.maxDays)): 
                self.log('getFileList, id: %s programmes exceed MAX_DAYS: endtime = %s'%(citem['id'],start),xbmc.LOGINFO)
                return True# prevent over-building
                
            citem = self.runActions(RULES_ACTION_CHANNEL_JSON, citem, citem)
            if isinstance(citem['path'], list): 
                mixed = True # build 'mixed' channels ie more than one path.
                path  = citem['path']
            else:
                mixed = False
                path  = [citem['path']] 
                
            media = 'music' if radio else 'video'
            if radio:
                cacheResponse = self.buildRadio(citem)
            else:         
                cacheResponse = [self.buildFileList(citem, file, media, self.limit, self.sort, self.filter, self.limits) for file in path] # build multi-paths as induvial arrays for easier interleaving.
                valid = (list(filter(lambda k:k, cacheResponse))) #check that at least one array contains a filelist
                if not valid:
                    self.log("getFileList, id: %s skipping channel cacheResponse empty!"%(citem['id']),xbmc.LOGINFO)
                    return False
                
                cacheResponse = self.runActions(RULES_ACTION_CHANNEL_LIST, citem, cacheResponse)
                cacheResponse = list(interleave(*cacheResponse)) # interleave multi-paths, while keeping order.
                
                # if len(cacheResponse) < limit: # balance media limits, by filling randomly with duplicates.
                    # cacheResponse.extend(list(fillList(cacheResponse,(limit-len(cacheResponse)))))
            cacheResponse = list(filter(lambda filelist:filelist, cacheResponse)) #filter empty filelist elements (probably unnecessary, if empty element is adding during interleave or injection rules remove).
            cacheResponse = self.addScheduling(citem, cacheResponse, start)
            # if self.fillBCTs: cacheResponse = self.injectBCTs(citem, cacheResponse)
            self.runActions(RULES_ACTION_CHANNEL_STOP, citem)
            return sorted((cacheResponse), key=lambda k: k['start'])
        except Exception as e: self.log("getFileList, Failed! " + str(e), xbmc.LOGERROR)
        return False
            
            
    def buildRadio(self, channel):
        self.log("buildRadio; channel = %s"%(channel))
        #todo insert custom radio labels,plots based on genre type?
        channel['genre'] = [channel['name']]
        channel['art']   = {'thumb':channel['logo'],'icon':channel['logo'],'fanart':channel['logo']}
        channel['plot']  = LANGUAGE(30098)%(channel['name'])
        return self.buildFile(channel,type='music')
                
                
    def buildFile(self, channel, duration=10800, type='video', entries=3):
        self.log("buildFile; channel = %s"%(channel))
        tmpItem  = {'label'       : (channel.get('label','') or channel['name']),
                    'episodetitle': channel.get('episodetitle',''),
                    'plot'        : (channel.get('plot' ,'') or LANGUAGE(30161)),
                    'genre'       : channel.get('genre',['Undefined']),
                    'type'        : type,
                    'duration'    : duration,
                    'file'        : channel['path'],
                    'start'       : 0,
                    'stop'        : 0,
                    'art'         : channel.get('art',{"thumb":LOGO,"logo":LOGO})}
        return [tmpItem.copy() for idx in range(entries)]
        
        
    def buildFileList(self, channel, path, media='video', limit=PAGE_LIMIT, sort={}, filter={}, limits={}):
        self.log("buildFileList, id: %s, path = %s, limit = %s, sort = %s, filter = %s, limits = %s"%(channel['id'],path,limit,sort,filter,limits))
        if path.startswith('videodb://movies'): 
            if not sort: sort = {"method": "random"}
        elif path.startswith(LANGUAGE(30174)):#seasonal
            if not sort: sort = {"method": "episode"}
            path = path.format(list=getSeason(),limit=250)
            
        id = channel['id']
        fileList      = []
        seasoneplist  = []
        method        =  sort.get("method","random")
        json_response = self.jsonRPC.requestList(id, path, media, limit, sort, filter, limits)

        for idx, item in enumerate(json_response):
            file     = item.get('file','')
            fileType = item.get('filetype','file')

            if fileType == 'file':
                if not file:
                    self.log("buildFileList, id: %s, IDX = %s skipping missing playable file!"%(id,idx),xbmc.LOGINFO)
                    continue
                elif (file.lower().endswith('strm') and not self.incStrms): 
                    self.log("buildFileList, id: %s, IDX = %s skipping strm!"%(id,idx),xbmc.LOGINFO)
                    continue
                    
                #parsing missing meta
                if not item.get('streamdetails',{}).get('video',[]): 
                    item['streamdetails'] = self.jsonRPC.getStreamDetails(file, media)

                if file.startswith(('plugin://','upnp://','pvr://')):
                    accurateDuration = False
                else: 
                    accurateDuration = self.accurateDuration
                dur = self.jsonRPC.getDuration(file, item, accurateDuration)
                if dur > 0:
                    item['duration'] = dur
                    if int(item.get("year","0")) == 1601: #default null for kodi rpc?
                        item['year'] = 0 
                        
                    mType   = item['type']
                    label   = item['label']
                    title   = (item.get("title",'') or label)
                    tvtitle = (item.get("showtitle","") or item.get("tvshowtitle",""))

                    if tvtitle or mType in ['tvshow','episode']:
                        # This is a TV show
                        seasonval = int(item.get("season","0"))
                        epval     = int(item.get("episode","0"))
                        if not file.startswith(('plugin://','upnp://','pvr://')) and not self.incExtras and (seasonval == 0 or epval == 0) and item.get("episode",None) is not None: 
                            self.log("buildFileList, id: %s skipping extras!"%(id),xbmc.LOGINFO)
                            continue

                        label = tvtitle
                        item["tvshowtitle"]  = tvtitle
                        item["episodetitle"] = title
                        item["episodelabel"] = '%s (%sx%s)'%(title,seasonval,str(epval).zfill(2))
                        
                    else: # This is a Movie
                        year = int(item.get("year","0"))
                        if year > 0 and '(' not in title: 
                            title = "%s (%s)"%(title, year)
                        item["episodetitle"] = item.get("tagline","")
                        item["episodelabel"] = item.get("tagline","")
                        seasonval = None
                        label = title
            
                    if not label: continue
                    item['label'] = label
                    item['plot']  = (item.get("plot","") or item.get("plotoutline","") or item.get("description","") or LANGUAGE(30161))
            
                    if self.dialog is not None:
                        self.dialog = ProgressBGDialog(self.progress, self.dialog, message='%s %s'%(self.chanName,((len(fileList)*100)//PAGE_LIMIT))+'%')

                    item.get('art',{})['icon']  = channel['logo']
                    # item.get('art',{})['thumb'] = getThumb(item) #unify artwork
                    
                    if method == 'episode' and seasonval is not None: 
                        seasoneplist.append([seasonval, epval, item])
                    else: 
                        fileList.append(item)
                else: 
                    self.log("buildFileList, id: %s skipping no duration meta found!"%(id),xbmc.LOGINFO)
                    
            elif fileType == 'directory' and (len(fileList) < limit): #extend fileList by parsing folders, limit folder parsing to limit size to avoid runaways.
                fileList.extend(self.buildFileList(channel, file, media, limit, sort, filter, limits))
            
        if method == 'episode':
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])
            for seepitem in seasoneplist: 
                fileList.append(seepitem[2])
            
        self.log("buildFileList, id: %s returning fileList %s / %s"%(id,len(fileList),limit),xbmc.LOGINFO)
        return fileList
        
    
    def injectBCTs(self, citem, fileList):
        self.log("injectBCTs, citem = %s"%(citem))
        validItems = [item for item in fileList if not item.get('file','').startswith(('pvr://','upnp://','plugin://'))]
        if not citem.get('radio',False) and len(validItems) > 0:
            resourceMap = self.bctTypes.copy()
            for type in resourceMap.keys():
                bctItems = self.bctTypes.get(type,{})
                bctPaths = bctItems.get('paths',[])
                resourceMap[type]['fileList'] = [] #{'label','duration','file'} or (dirs,files)
                if not bctPaths or bctItems.get('enabled',False): continue
                
                # if type == 'trailers': #append local trailers to list.
                    # resourceMap[type]['fileList'] = self.jsonRPC.buildLocalTrailers(items=validItems)
                [resourceMap[type]['fileList'].extend(self.jsonRPC.buildBCTresource(bctPath)) for bctPath in bctPaths]
                print(type,resourceMap[type]['fileList'])
                
            # tmpFileList = fileList.copy()
            # for idx, item in enumerate(tmpFileList):
                # file  = item.get('file','')
                # paths = [file]
                # if   file.startswith(('pvr://','upnp://','plugin://')): continue # Kodi only handles stacks between local content, bug?
                # elif file.startswith('stack://'): paths = splitStacks(file)
                    
                # start       = item['start']
                # stop        = item['stop']
                # endOnHour   = (roundTimeTo(stop) - stop)
                # stack       =  'stack://%s'
                # orgPaths    = paths.copy()
                
                # for bctType in resourceMap.keys():
                    # bctItems = resourceMap[bctType]
                    # if not bctItems.get('fileList',[]): continue
             
                    # if bctType == 'rating':
                        # mpaa = item.get('mpaa','')
                        # if mpaa.startswith('Rated'): mpaa = re.split('Rated ',mpaa)[1]  #todo prop. regex
                        # if is3D(item): mpaa += ' (3DSBS)'
                        # for bctItem in bctItems:
                            
                            # if bctItem.get('label','').lower() == mpaa.lower():
                            
                            
                            
                            
                            # if rating.lower() == mpaa.lower():
                                # buildBCT(bctType,self.jsonRPC.buildResourcePath(resource['path'],file))
                    # else:
                        # max = bctTypes[bctType].get('max',0)
                        # if max > len(filepaths): max = len(filepaths)
                        # matches = random.sample(filepaths, random.randint(bctTypes[bctType].get('min',0),max))
                        # [buildBCT(bctType, match) for match in matches]
                                        
                # if orgPaths != paths:
                    # item['originalfile'] = item['file']
                    # item['file'] = stack%(' , '.join(paths))
                # tmpList.append(item)
        return fileList

        
        # def buildBCT(bctType, path):
            # if path.startswith(('pvr://','upnp://','plugin://')): return # Kodi only handles stacks between local content, bug?
            # duration = self.jsonRPC.parseDuration(path)
            # self.log("injectBCTs; buildBCT building %s, path = %s, duration = %s"%(bctType,path,duration))
            # if bctType in PRE_ROLL:
                # paths.insert(0,path)
            # else:
                # paths.append(path)
                # item['stop'] += duration
                # items[idx+1]['start'] = item['stop']
                          
        # tmpList     = []
        # resourceMap = {}
        # self.log("injectBCTs; channel = %s, configuration = %s, fileList size = %s"%(channel,dumpJSON(bctTypes),len(fileList)))
        
        # bctTypes = self.bctTypes
        # for bctType in bctTypes:
            # if not bctTypes[bctType]['enabled']: continue
            # resourceMap[bctType] = self.jsonRPC.buildBCTresource(bctTypes[bctType].get('path'))
            # if bctType in ['bumper','commercial']: # locate folder by channel name.
                # self.log("injectBCTs; finding channel folder %s for %s"%(channel['name'],bctType))
                # resourceMap[bctType] = [self.jsonRPC.buildBCTresource(os.path.join(bctTypes[bctType].get('path'),dir)) for dir in bctTypes[bctType].get('dirs') if channel['name'].lower() == dir.lower()]
            # elif bctTypes == 'trailer':        
                # # integrate channel trailers along with resources
                # trailers = filter(None,list(set([fileitem.get('trailer',None) for fileitem in fileList])))
                # if not trailers: continue
                # trailers = trailers.reverse()
                # trailers.shuffle()
                # self.log("injectBCTs; adding %s local kodi trailers"%(len(trailers)))
                # resourceMap[bctType]['filepaths'].extend(trailers)
                   
        # for idx, item in enumerate(fileList):
            # stop      = item['stop']
            # endOnHour = (roundTimeTo(stop) - stop)
            # file      = item['file']
            # stack     =  'stack://%s'
            # if   file.startswith(('pvr://','upnp://','plugin://')): continue # Kodi only handles stacks between local content, bug?
            # elif file.startswith('stack://'):
                # paths = splitStacks(file)
            # else:
                # paths = [file]
            # orgPaths  = paths.copy()

            # for bctType in bctTypes:
                # if not bctTypes[bctType]['enabled']: continue
                # resource  = resourceMap.get(bctType,{})
                # files     = resource.get('files',[])
                # filepaths = resource.get('filepaths',[])
                
                # if bctType == 'rating':
                    # mpaa = item.get('mpaa'  ,'')
                    # if mpaa.startswith('Rated'): mpaa = re.split('Rated ',mpaa)[1]  #todo prop. regex
                    # if is3D(item): mpaa += ' (3DSBS)'
                    # for file in files:
                        # rating = os.path.splitext(file)[0]
                        # if rating.lower() == mpaa.lower():
                            # buildBCT(bctType,self.jsonRPC.buildResourcePath(resource['path'],file))
                # else:
                    # max = bctTypes[bctType].get('max',0)
                    # if max > len(filepaths): max = len(filepaths)
                    # matches = random.sample(filepaths, random.randint(bctTypes[bctType].get('min',0),max))
                    # [buildBCT(bctType, match) for match in matches]
                                    
            # if orgPaths != paths:
                # item['originalfile'] = item['file']
                # item['file'] = stack%(' , '.join(paths))
            # tmpList.append(item)
        # return tmpList