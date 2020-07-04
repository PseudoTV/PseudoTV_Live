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

from globals    import *
from parsers    import M3U, XMLTV, JSONRPC, Channels
from predefined import Predefined 
from resources.lib.FileAccess import FileLock

class Builder:
    def __init__(self):
        log('Builder: __init__')
        self.m3u       = M3U()
        self.xmltv     = XMLTV()
        self.channels  = Channels()
        self.predefined = Predefined()
        self.jsonRPC   = JSONRPC()
        self.dircount  = 0
        self.filecount = 0
        self.incStrms  = INCLUDE_STRMS  #todo adv. rules
        self.incExtras = INCLUDE_EXTRAS #todo adv. rules
        self.strictDuration = STRICT_DURATION
        self.maxDays   = getSettingInt('Max_Days')
        self.fillBCTs  = getSettingBool('Enable_Fillers')
        self.pageLimit = getSettingInt('Page_Limit')
        self.accurateDuration = PARSE_DURATION
        self.now       = getLocalTime()
        self.start     = rollbackTime(self.now)
        self.grouping  = getSettingBool('Enable_Grouping') 
        # self.fileLock  = FileLock()


    # Run rules for a channel
    def runActions(self, action, channelID, parameter):
        log("Builder: runActions %s on channel %s"%(action,channelID))
        self.runningActionChannel = channelID
        index = 0
        channelList = self.createChannelItems()
        ruleList = [item['ruleList'] for item in channelList if channelID == item['id']]
        for rule in ruleList:
            if rule.actions & action > 0:
                self.runningActionId = index
                parameter = rule.runAction(action, self, parameter)
            index += 1
        self.runningActionChannel = 0
        self.runningActionId = 0
        return parameter


    def createChannelItems(self):
        log('Builder: createChannelItems')
        #add internal references to channel.json #todo move to Channels() class
        items = sorted(self.predefined.buildChannelList(), key=lambda k: k['number']) #todo user opt. sort by, name, etc?
        channels = []
        for idx, item in enumerate(items):
            item['id']     = getChannelID(item['name'], item['path'])
            item['number'] = item.get('number',0)
            item['label']  = item['name'] #todo custom channel name?
            item['group']  = [ADDON_NAME, item['type']] if self.grouping else [ADDON_NAME]
            item['url']    = 'plugin://%s/?mode=play&name=%s&id=%s'%(ADDON_ID,urllib.parse.quote(item['name']),urllib.parse.quote(item['id']))
            channels.append(item)
        return sorted(channels, key=lambda k: k['number'])
        
        
    def reload(self):
        log('Builder: reload')
        try:
            self.channels.reset()
            self.xmltv.reset()
            self.m3u.reset()
        except Exception as e: log("Builder: reload, Failed! " + str(e), xbmc.LOGERROR)
        
        
    def save(self):
        log('Builder: save')
        try:
            self.m3u.save()
            self.xmltv.save()
        except Exception as e: log("Builder: save, Failed! " + str(e), xbmc.LOGERROR)
        
        
    def buildService(self, channels=None, reloadPVR=True):
        log('Builder: buildService')
        if isBusy(): 
            return notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        if channels is None: 
            channels = self.createChannelItems()
        if not channels: 
            return notificationDialog(LANGUAGE(30056))
            
        setBusy(True)
        # isLock = self.fileLock.lockFile("MasterLock", False)
        self.reload()
        
        msg = LANGUAGE(30050) if reloadPVR else LANGUAGE(30051)
        dlg = ProgressDialogBG(message=ADDON_NAME)
        for idx, channel in enumerate(channels):
            dlg = ProgressDialogBG((idx*100//len(channels)), dlg, '%s: %s'%(msg,channel['name']))
            cacheResponse = self.getFileList(channel)
            if cacheResponse:
                self.buildM3U(channel)
            else: continue
            if isinstance(cacheResponse,list):
                self.buildXMLTV(channel, cacheResponse)
        
        self.save()
        setBusy(False)
        # self.fileLock.unlockFile('MasterLock')
        dlg = ProgressDialogBG(100,dlg,LANGUAGE(30053))
        # notificationDialog(LANGUAGE(30017)%(msg))
        if reloadPVR: configurePVR()
        # self.fileLock.close()


    def getFileList(self, channel):
        log('Builder: getFileList; channel = %s'%(channel))
        try:
            media = 'video' #todo support music channels via radio.
            self.dircount  = 0
            self.filecount = 0
            self.now       = getLocalTime()
            self.start     = (self.xmltv.xmltvList['endtimes'].get(channel['id'],'') or rollbackTime(self.now)) #offset time to start on half hour

            if datetime.datetime.fromtimestamp(self.start) >= (datetime.datetime.fromtimestamp(self.now) + datetime.timedelta(days=self.maxDays)): 
                log('Builder: getFileList, programmes exceed MAX_DAYS: endtime = %s'%(self.start))
                return True# prevent over-building
                
            # global values prior to channel rules
            filter = {}
            sort   = {}#{"order": "ascending", "ignorefolders": "false", "method": "random"}
            limits = {}#adv. rule to force page.
            page   = self.pageLimit
            
            # todo load rules, pre json (cacheResponse).
            
            if isinstance(channel['path'], list): 
                mixed = True # build 'mixed' channels ie more than one path.
                path  = channel['path']
            else:
                mixed = False
                path  = [channel['path']]
                
            cacheResponse = [self.buildFileList(channel['id'], file, media, page, sort, filter, limits) for file in path]
            cacheResponse = list(interleave(*cacheResponse)) # interleave multi-paths
            if not cacheResponse: 
                log('Builder: getFileList, cacheResponse empty')
                return False
            
            # todo load rules, post json (cacheResponse).
            # random.shuffle(cacheResponse)# interleave, shuffle Mixed
            # cacheResponse = random.sample(cacheResponse,len(cacheResponse))
            # cacheResponse = filter(None,list(chain.from_iterable(izip_longest(L1, L2))))
            # if sort.get("method",'') == 'random': random.shuffle(cacheResponse)
            # if sort.get("order",'')  == 'descending': cacheResponse.reverse()
            # cacheResponse[:limit] # trim list
            # todo run rules, filelist (cacheResponse).
            if self.fillBCTs: cacheResponse = self.injectBCTs(cacheResponse)
            return sorted(cacheResponse, key=lambda k: k['start'])
        except Exception as e: log("Builder: getFileList, Failed! " + str(e), xbmc.LOGERROR)
        return False
            
        
    def getDuration(self, path, item={}, accurate=False):
        log("Builder: getDuration; accurate = %s, path = %s"%(accurate,path))
        duration = 0
        runtime  = int(item.get('runtime','') or item.get('duration','0') or '0')
        if accurate == False: return runtime
        elif path.startswith('stack://'): #handle "stacked" videos:
            stack = (path.replace('stack://','').replace(',,',',')).split(' , ') #todo move to regex match
            for file in stack: duration += self.jsonRPC.parseDuration(file, item)
        else: 
            duration = self.jsonRPC.parseDuration(path, item)
        if self.strictDuration or duration > 0: 
            return duration
        return runtime 
        
    
    def injectBCTs(self, channel, fileList):
        log("Builder: injectBCTs; channel = %s"%(channel))
        # resourcePack = os.path.join('resource.videos.ratings.mpaa.classic')
        # for item in fileList:
            # print endOnHalfHour(item['stop'])
        # todo round item duration to nearest greater half hour, calc. difference time and auto fill with BCTs
        return fileList
        
        
    def buildXMLTV(self, channelData, fileList):
        log("Builder: buildXMLTV, channel = %s"%(channelData))
        self.xmltv.addChannel(channelData)
        for file in fileList:
            if not file: continue
            item = {}
            item['channel']     = channelData['id']
            item['start']       = file['start']
            item['stop']        = file['stop']
            item['title']       = file['label']
            item['sub-title']   = file['episodetitle']
            item['desc']        = file['plot']
            item['rating']      = (file.get('mpaa','')   or 'NA')
            item['stars']       = (file.get('rating','') or '0')
            item['categories']  = (file.get('genre','')  or ['Undefined'])
            item['type']        = file.get('type','video')
            item['new']         = int(file.get('playcount',0)) == 0
            item['thumb']       = getThumb(file)
            
            item['episode-num'] = ''
            if (item['type'] != 'movie' and (file.get("episode",0) > 0)):
                item['episode-num'] = 'S%sE%s'%(str(file.get("season",0)).zfill(2),str(file.get("episode",0)).zfill(2))
                
            # key hijacking
            item['director']    = str(file['id'])# dbid
            file['data']        = channelData #channel dict
            item['writer']      = file # kodi listitem dict.
            self.xmltv.addProgram(channelData['id'], item)
            
            
    def buildM3U(self, channel):
        log("Builder: buildM3U, channel = %s"%(channel))
        self.m3u.add(channel)


    def buildFileList(self, id, path, media='video', limit={}, sort={}, filter={}, limits={}):
        if not limit: limit = self.pageLimit
        log("Builder: buildFileList, path = %s, limit = %s, sort = %s, filter = %s, limits = %s"%(path,limit,sort,filter,limits))
        fileList = []
        seasoneplist = []
        method =  sort.get("method",'random')
        json_response = self.jsonRPC.requestList(id, path, media, limit, sort, filter, limits)
        for item in json_response:
            file = item.get('file','')
            fileType = item.get('filetype','file')
            if not file:
                log("Builder: buildFileList, no file found")
                continue
            if fileType == 'file':
                if file[-4].lower() == 'strm' and self.incStrms == False: 
                    log("Builder: buildFileList, skipping strm")
                    continue
                dur = self.getDuration(file, item, self.accurateDuration) # add to adv. rules
                if dur > 0:
                    item['dur']   = dur
                    item['start'] = self.start
                    item['stop']  = self.start + dur
                    item["idx"]   = self.filecount
                    
                    mType = item['type']
                    title = item['label']
                    label = title
                    showtitle = item.get("showtitle","")
                    plot = item.get("plot","")

                    if showtitle:
                        # This is a TV show
                        # method  = 'episode' #todo move to rules, ie sort parameter
                        swtitle = item.get("title",title)
                        seasonval  = int(item.get("season","0"))
                        epval = int(item.get("episode","0"))
                        if not self.incExtras and (seasonval == 0 or epval == 0): 
                            log("Builder: buildFileList, skipping extras")
                            continue
                            
                        if epval > 0: swtitle = swtitle + ' (' + str(seasonval) + 'x' + str(epval).zfill(2) + ')'
                        item["episodetitle"] = swtitle
                        label = showtitle
                    else:
                        # This is a Movie
                        if not showtitle:
                            years = int(item.get("year","0"))
                            if years > 0: title = "%s (%s)"%(title, years)
                        item["episodetitle"] = item.get("tagline","")
                        seasonval = None
                        
                    item['label'] = label
                    item['plot']  = (item.get("plot","") or item.get("plotoutline","") or item.get("description","") or xbmc.getLocalizedString(161))
                    self.start    = item['stop']
                    
                    if method == 'episode' and seasonval is not None: seasoneplist.append([seasonval, epval, item])
                    else: fileList.append(item)
            
                    self.filecount += 1
                    if self.filecount >= limit: break
                    
            elif (fileType == 'directory' or (file.endswith("/") or file.endswith("\\"))) and (self.filecount < limit and self.dircount < limit):
                self.dircount += 1
                fileList.extend(self.buildFileList(id, file, media, limit, sort, filter, limits))
                       
        if self.filecount < limit and self.dircount == 0:
            self.dircount += 1
            fileList.extend(self.buildFileList(id, path, media, limit, sort, filter, limits))
            
        if method == 'episode':
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])
            [fileList.append(seepitem[2]) for seepitem in seasoneplist]
        log("Builder: buildFileList return, fileList size = %s"%len(fileList))
        return fileList
        
        
    def fillFileList(self, fileList, end):
        fillList = []
        listSize = len(fileList)
        if listSize > 0 and (listSize >= end-listSize):  # fill existing fileList to given size.
            fillList = random.sample(fileList, (end-listSize))
            for fillItem in fillList:
                fillItem['start'] = self.start
                fillItem['stop']  = self.start + fillItem['dur']
                self.start = fillItem['stop']
                yield fillItem