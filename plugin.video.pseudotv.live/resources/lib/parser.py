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
# https://github.com/kodi-pvr/pvr.iptvsimple/blob/Matrix/README.md#m3u-format-elements
# https://raw.githubusercontent.com/XMLTV/xmltv/master/xmltv.dtd
# -*- coding: utf-8 -*-

from resources.lib.globals     import *
from resources.lib             import xmltv

GLOBAL_FILELOCK = FileLock()

class Writer:
    def __init__(self, cache=None, builder=None):
        self.log('__init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.m3u           = M3U(self.cache)
        self.xmltv         = XMLTV(self.cache)
        self.channels      = Channels(self.cache)
        
        if builder:
            self.builder  = builder
            self.dialog   = self.builder.dialog
            self.progress = self.builder.progress
            self.chanName = self.builder.chanName
        else:
            self.dialog   = None
            self.progress = 0
            self.chanName = ''


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
        
    def reset(self):
        self.log('reset')
        if False in [self.xmltv.reset(),
                     self.m3u.reset(),
                     self.channels.reset()]: return False
        return True
        
        
    def isClient(self):
        return self.channels.isClient
        
        
    def getEndtime(self, id, fallback):
        self.log('getEndtime, id = %s'%(id))
        return (self.xmltv.getEndtimes().get(id,'') or fallback)
        
        
    def delete(self, full=False):
        self.log('delete')
        funcs = [self.m3u.delete,
                 self.xmltv.delete]
        if full: funcs.extend([self.channels.delete,self.deleteSettings])
        if False in [func() for func in funcs]:
            return False
        return True
        

    @staticmethod
    def deleteSettings():
        self.log('deleteSettings')
        if FileAccess.delete(SETTINGS_FLE):
            return notificationDialog(LANGUAGE(30016)%('SETTINGS'))
        return False
        
        
    def save(self):
        self.log('save')
        if self.cleanChannels():
            self.importSETS()
            if self.xmltv.save() and self.m3u.save():
                if self.dialog is not None:
                    self.dialog = ProgressBGDialog(self.progress, self.dialog, message=LANGUAGE(30152))
                return True
        return False
        
        
    def saveChannels(self):
        self.log('saveChannels')
        if self.channels.save(): 
           return self.save()
        return False
        
        
    def importSETS(self):
        self.log('importSETS')
        importLST = self.channels.getImports()
        if getSettingBool('User_Import'): 
            importLST.append({'type':'iptv','name':'User M3U/XMLTV','m3u':{'path':getSetting('Import_M3U'),'slug':getSetting('Import_SLUG')},'xmltv':{'path':getSetting('Import_XMLTV')}})
        for idx, importItem in enumerate(importLST):
            try:
                if importItem.get('type','') == 'iptv':
                    if self.dialog is not None:
                        self.dialog = ProgressBGDialog(self.progress, self.dialog, message='%s %s'%(LANGUAGE(30151),importItem.get('name','')))
                    idx += 1
                    slug   = importItem.get('m3u'  ,{}).get('slug','')
                    m3ufle = importItem.get('m3u'  ,{}).get('path','')
                    xmlfle = importItem.get('xmltv',{}).get('path','')
                    self.m3u.importM3U(m3ufle,slug,multiplier=idx)
                    self.xmltv.importXMLTV(xmlfle,slug)
            except Exception as e: self.log(" importSETS, Failed! " + str(e), xbmc.LOGERROR)
        return True
        
        
    def addChannelLineup(self, citem, radio=False, catchup=True):
        item = citem.copy()
        item['label'] = (item.get('label','') or item['name'])
        item['url']   = 'plugin://%s/?mode=play&name=%s&id=%s&radio=%s'%(ADDON_ID,urllib.parse.quote(item['name']),urllib.parse.quote(item['id']),str(item['radio']))
        if not getSettingBool('Enable_Grouping'): 
            item['group'] = [ADDON_NAME]
        else:
            item['group'].append(ADDON_NAME)
        item['group'] = list(set(item['group']))
        self.log('addChannelLineup, item = %s, radio = %s, catchup = %s'%(item,radio,catchup))
        self.m3u.addChannel(item)
        self.xmltv.addChannel(item)
    
    
    def removeChannel(self, citem): #remove channel completely from channels.json and m3u/xmltv
        self.log('removeChannel, citem = %s'%(citem))
        self.channels.remove(citem)
        self.removeChannelLineup(citem)
        
        
    def removeChannelLineup(self, citem): #clean channel from m3u/xmltv
        self.log('removeChannelLineup, citem = %s'%(citem))
        self.m3u.removeChannel(citem.get('id',''))
        self.xmltv.removeChannel(citem.get('id',''))
    

    def addProgrammes(self, citem, fileList, radio=False, catchup=True):
        self.log('addProgrammes, radio = %s, catchup = %s, programmes = %s, citem = %s'%(radio,catchup,len(fileList),citem))
        for idx, file in enumerate(fileList):
            item = {}
            item['radio']       = radio
            item['channel']     = citem['id']
            item['start']       = file['start']
            item['stop']        = file['stop']
            item['title']       = file['label']
            item['desc']        = file['plot']
            item['length']      = file['duration']
            item['sub-title']   = (file.get('episodetitle','') or '')
            item['rating']      = (file.get('mpaa','')         or 'NA')
            item['stars']       = (file.get('rating','')       or '0')
            item['categories']  = (file.get('genre','')        or ['Undefined'])
            item['type']        = file.get('type','video')
            item['new']         = int(file.get('playcount','1')) == 0
            item['thumb']       = getThumb(file,getSettingInt('EPG_Artwork'))
            file['art']['thumb']= getThumb(file,{0:1,1:0}[getSettingInt('EPG_Artwork')]) #unify thumbnail artwork, opposite of EPG_Artwork
            item['date']        = (file.get('firstaired','') or file.get('premiered','') or file.get('releasedate','') or file.get('originaldate','') or None)
            
            if catchup:
                item['catchup-id'] = 'plugin://%s/?mode=vod&name=%s&id=%s&channel=%s&radio=%s'%(ADDON_ID,urllib.parse.quote(item['title']),urllib.parse.quote(encodeString(file.get('file',''))),urllib.parse.quote(citem['id']),str(item['radio']))
            
            if (item['type'] != 'movie' and (file.get("episode",0) > 0)):
                item['episode-num'] = 'S%sE%s'%(str(file.get("season",0)).zfill(2),str(file.get("episode",0)).zfill(2))
                
            item['director']    = (','.join(file.get('director',[])))
            item['writer']      = (','.join(file.get('writer',[])))
            
            file['citem']       = citem #channel dict (stale data due to xmltv storage)
            item['fitem']       = file # kodi fileitem/listitem dict.
            
            # streamdetails       = file.get('streamdetails',{})
            # if streamdetails:
                # item['subtitle'] = list(set([sub.get('language','') for sub in streamdetails.get('subtitle',[]) if sub.get('language','')]))
                # item['audio']    = list(set([aud.get('codec','') for aud in streamdetails.get('audio',[]) if aud.get('codec','')]))
                # item['language'] = list(set([aud.get('language','') for aud in streamdetails.get('audio',[]) if aud.get('language','')]))
                # item['video']    = list(set([vid.get('aspect','') for vid in streamdetails.get('video',[]) if vid.get('aspect','')]))
            
            self.xmltv.addProgram(citem['id'], item)
            
            
    def clearChannels(self,all=False):
        channels = self.channels.getChannels()
        if not all: channels = list(filter(lambda citem:citem.get('number') <= CHANNEL_LIMIT, channels))
        self.log('cleanChannels, channels = %s'%(len(channels)))
        for citem in channels: 
            self.removeChannel(citem)
        return self.saveChannels()
        
            
    def cleanChannels(self): # remove abandoned/missing channels from m3u/xmltv
        self.log('cleanChannels')
        channels = self.channels.getChannels()
        m3u      = self.m3u.getChannels().copy()
        xmltv    = self.xmltv.getChannels().copy()
        
        for channel in channels:
            chid = channel.get('id','')
            if not chid: continue
            
            for idx, item in enumerate(m3u):
                if chid == item.get('id',''):
                    m3u.pop(idx)
                    
            for idx, item in enumerate(xmltv):
                if chid == item.get('id',''):
                    xmltv.pop(idx)
        
        [self.m3u.removeChannel(item.get('id',''))   for item in m3u]
        [self.xmltv.removeChannel(item.get('id','')) for item in xmltv]
        return True
        
    
    def recoverChannels(self):
        self.log('recoverChannels') #rebuild channels.json from m3u.
        channels = self.channels.getChannels()
        m3u      = self.m3u.getChannels().copy()
        if not channels and m3u:
            self.log('recoverChannels, recovering %s m3u channels'%(m3u))
            if not yesnoDialog('%s ?'%(LANGUAGE(30178))): return
            for item in m3u: 
                citem = self.channels.getCitem()
                citem.update(item) #todo repair path.
                self.channels.add(citem)
            if self.channels.save(): return True
        return False
        
        
    def buildImports(self, items, imports):
        self.log('buildImports')
        self.channels.setImports([item['data'] for item in items for eimport in imports if ((item.get('data',{}).get('name','').startswith(eimport.get('name'))) and (item['data'].get('type','').lower() == 'iptv'))])
        return self.channels.save()


    def buildPredefinedChannels(self, libraryItems):  
        # convert enabled library.json into channels.json items
        # types = list(filter(lambda k:k != LANGUAGE(30033), CHAN_TYPES)) #ignore Imports, use buildImports
        def findChannel():
            for idx, eitem in enumerate(echannels):
                if (citem['id'] == eitem['id']) or (citem['type'].lower() == eitem['type'].lower() and citem['name'].lower() == eitem['name'].lower()):
                    return idx, eitem
            return None, {}
                
        def buildAvailableRange():
            # create number array for given type, excluding existing channel numbers.
            start = ((CHANNEL_LIMIT+1)*(CHAN_TYPES.index(type)+1))
            stop  = (start + CHANNEL_LIMIT)
            self.log('buildAvailableRange, type = %s, range = %s-%s, enumbers = %s'%(type,start,stop,enumbers))
            # return list(set(range(start,stop)).difference(set(blist))) #set bug with even array in bytes? 
            return [num for num in range(start,stop) if num not in enumbers]
            
        for type in libraryItems.keys():
            self.log('buildPredefinedChannels, type = %s'%(type))
            echannels = list(filter(lambda k:k['type'] == type, self.channels.getPredefinedChannels())) # existing channels, avoid duplicates, aid in removal.
            enumbers  = [echannel.get('number') for echannel in echannels if echannel.get('number',0) > 0] #existing channel numbers
            numbers   = iter(buildAvailableRange()) #list of available channel numbers 
            leftovers = echannels.copy()
            items     = libraryItems.get(type,[])
            for item in items:
                citem = self.channels.getCitem()
                citem.update({'name'   :getChannelSuffix(item['name'], type),
                              'path'   :item['path'],
                              'type'   :item['type'],
                              'logo'   :item['logo'],
                              'group'  :[type]})
                              
                citem['radio']   = (item['type'] == LANGUAGE(30097) or 'musicdb://' in item['path'])
                citem['catchup'] = ('vod' if not citem['radio'] else '')
                match, eitem = findChannel()
                if match is not None: #update new citems with existing values.
                    leftovers.remove(eitem)
                    for key in ['rules','number','favorite','page']: citem[key] = eitem[key]
                else: 
                    citem['number'] = next(numbers,0)
                citem['id'] = getChannelID(citem['name'], citem['path'], citem['number'])
                self.channels.add(citem)
            [self.removeChannel(eitem) for eitem in leftovers] #remove channels unselected.
        return self.saveChannels()
         
        
    def autoPagination(self, id, path, limits={}):
        cacheName = '%s.autoPagination.%s.%s'%(ADDON_ID,id,path)
        if not limits:
            msg = 'get'
            try:    limits = self.channels.getPage(id)
            except: limits = ''
            limits = (limits or self.cache.get(cacheName) or {"end": 0, "start": 0, "total": 0})
        else:
            msg = 'set'
            try:
                if self.channels.setPage(id, limits): 
                    self.channels.save()
            except: pass
            self.cache.set(cacheName, limits, checksum=len(limits), expiration=datetime.timedelta(days=28))
        self.log("%s autoPagination, id = %s, path = %s, limits = %s"%(msg,id,path,limits))
        return limits

        
    @staticmethod
    def syncCustom(): #todo sync user created smartplaylists/nodes for multi-room.
        for type in ['library','playlists']:
            for media in ['video','music','mixed']:
                path  = 'special://userdata/%s/%s/'%(type,media)
                files = FileAccess.listdir(path)[1]
                for file in files:
                    orgpath  = os.path.join(path,file)
                    copypath = os.path.join(PLS_LOC,type,media,file)
                    self.log('copyNodes, orgpath = %s, copypath = %s'%(orgpath,copypath))
                    yield FileAccess.copy(orgpath, copypath)


class Channels:
    def __init__(self, cache=None):
        log('Channels: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache

        self.channelList = self.getTemplate(ADDON_VERSION)
        self.channelList.update(self.load())
        self.isClient    = self.chkClient()
        
        
    def reset(self):
        log('Channels: reset')
        self.__init__()
        return True


    def getUUID(self, channelList=None):
        log('Channels: getUUID')
        if channelList is None: channelList = self.channelList
        uuid = channelList.get('uuid','')
        if not uuid: 
            uuid = getMYUUID()
            channelList['uuid'] = uuid
            self.channelList = channelList
        return uuid


    def chkClient(self):
        isClient = getClient()
        if not isClient:
            isClient = self.getUUID() != getMYUUID()
            if isClient: setClient('true')
            else: setClient('false')
        log('Channels: chkClient, isClient = %s'%(isClient))
        return isClient


    @staticmethod
    def sortChannels(channels):
        return sorted(channels, key=lambda k: k['number'])


    def getChannels(self):
        log('Channels: getChannels')
        return self.sortChannels(self.channelList.get('channels',[]))


    def getPredefinedChannels(self):
        log('Channels: getPredefinedChannels')
        return self.sortChannels(list(filter(lambda citem:citem.get('number') > CHANNEL_LIMIT, self.channelList.get('channels',[]))))


    def getPage(self, id):
        idx, citem = self.findChannel({'id':id}, self.getChannels())
        log('Channels: getPage, id = %s, page = %s'%(id, citem.get('page','')))
        return citem.get('page','')


    def setPage(self, id, page={}):
        log('Channels: setPage, id = %s, page = %s'%(id, page))
        channels = self.channelList['channels']
        idx, citem = self.findChannel({'id':id}, channels)
        if idx is not None: 
            channels[idx]['page'] = page
            self.channelList['channels'] = channels
            return True#todo save here
        return False


    def getImports(self):
        log('Channels: getImports')
        return self.channelList.get('imports',[])


    def setImports(self, imports):
        log('Channels: setImports, imports = %s'%(imports))
        self.channelList['imports'] = imports
        return True #todo save here
        

    def add(self, citem):
        log('Channels: add, id = %s'%(citem['id']))
        idx, channel = self.findChannel(citem, channels = self.channelList['channels'])
        if idx is not None:
            for key in ['rules','number','favorite','page']: citem[key] = channel[key] # existing id found, reuse channel meta.
            log('Channels: Updating channel %s, id %s'%(citem["number"],citem["id"]))
            self.channelList['channels'][idx] = citem #can't .update() must replace.
        else:
            log('Channels: Adding channel %s, id %s'%(citem["number"],citem["id"]))
            self.channelList['channels'].append(citem)
        return True
        
        
    def remove(self, citem):
        log('Channels: removing id = %s'%(citem['id']))
        idx, channel = self.findChannel(citem, self.channelList['channels'])
        if idx is not None: self.channelList['channels'].pop(idx)
        return True
        
        
    @staticmethod
    def findChannel(citem, channels):
        match = None, {}
        for idx, channel in enumerate(channels):
            if (citem["id"] == channel["id"]):
                log('Channels: findChannel, item = %s, found = %s'%(citem['id'],channel['id']))
                return idx, channel
            elif ((citem.get("name") == channel["name"]) and (citem["type"] == channel["type"])):
                log('Channels: findChannel, possible match found = %s'%(channel['id']))
                match = idx, channel
        return match
        

    @use_cache(7)
    def getTemplate(self, version=ADDON_VERSION):
        log('Channels: getTemplate')
        channelList = (self.load(CHANNELFLE_DEFAULT) or {})
        channelList['uuid'] = self.getUUID(channelList)
        return channelList


    def getCitem(self):
        log('Channels: getCitem') #channel schema
        citem = self.getTemplate(ADDON_VERSION).get('channels',[])[0].copy()
        citem['rules'] = []
        return citem
        
       
    def getRitem(self):
        log('Channels: getRitem') #rule schema
        return self.getTemplate(ADDON_VERSION).get('channels',[{}])[0].get('rules',[])[0].copy()


    def cleanSelf(self, channelList):
        channels = channelList.get('channels',[])
        channelList['channels'] = self.sortChannels([citem for citem in channels if citem['number'] > 0])
        log('Channels: cleanSelf, before = %s, after = %s'%(len(channels),len(channelList['channels'])))
        return channelList
        

    @staticmethod
    def load(file=CHANNELFLE):
        log('Channels: load file = %s'%(file))
        if not FileAccess.exists(file): 
            file = CHANNELFLE_DEFAULT
        with fileLocker(GLOBAL_FILELOCK):
            fle  = FileAccess.open(file, 'r')
            data = (loadJSON(fle.read()) or {})
            fle.close()
            return data
        
        
    def save(self):
        with fileLocker(GLOBAL_FILELOCK):
            fle = FileAccess.open(CHANNELFLE, 'w')
            log('Channels: save, saving to %s'%(CHANNELFLE))
            fle.write(dumpJSON(self.cleanSelf(self.channelList), idnt=4, sortkey=False))
            fle.close()
        return self.reset() #force memory/file parity 


class XMLTV:
    def __init__(self, cache=None):
        log('XMLTV: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.xmltvList = {'data'       : self.loadData(),
                          'channels'   : self.sortChannels(self.cleanSelf(self.loadChannels(),'id')),
                          'programmes' : self.sortProgrammes(self.cleanSelf(self.loadProgrammes(),'channel'))}


    def reset(self):
        log('XMLTV: reset')
        self.__init__()
        return True


    def getChannels(self):
        log('XMLTV: getChannels')
        return self.xmltvList.get('channels',[])


    def getProgrammes(self):
        log('XMLTV: getProgrammes')
        return self.xmltvList.get('programmes',[])


    def importXMLTV(self, file, slug=None):
        log('XMLTV: importXMLTV, file = %s'%file)
        try:
            if file.startswith('http'):
                url  = file
                file = os.path.join(TEMP_LOC,'%s.xml'%(slugify(url)))
                saveURL(url,file)
            self.xmltvList['channels'].extend(self.sortChannels(self.cleanSelf(self.loadChannels(file),'id',slug)))#todo collision logic?
            self.xmltvList['programmes'].extend(self.sortProgrammes(self.cleanSelf(self.loadProgrammes(file),'channel',slug)))
        except Exception as e: self.log("XMLTV: importXMLTV, failed! " + str(e), xbmc.LOGERROR)
        return True

        
    def loadChannels(self, file=XMLTVFLE):
        log('XMLTV: loadChannels, file = %s'%file)
        try:
            with fileLocker(GLOBAL_FILELOCK):
                return self.sortChannels(xmltv.read_channels(FileAccess.open(file, 'r')) or [])
        except Exception as e:
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            log('XMLTV: loadChannels, failed! %s'%(e))
            return []
        
        
    def loadProgrammes(self, file=XMLTVFLE):
        log('XMLTV: loadProgrammes, file = %s'%file)
        try: 
            with fileLocker(GLOBAL_FILELOCK):
                return self.sortProgrammes(self.cleanProgrammes(xmltv.read_programmes(FileAccess.open(file, 'r')) or []))
        except Exception as e: 
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            log('XMLTV: loadProgrammes, failed! %s'%(e))
            return []


    def loadData(self):
        log('XMLTV: loadData')
        try: 
            with fileLocker(GLOBAL_FILELOCK):
                return (xmltv.read_data(FileAccess.open(XMLTVFLE, 'r')) or self.resetData())
        except Exception as e: 
            log('XMLTV: loadData, failed! %s'%(e))
            return self.resetData()


    def buildGenres(self):
        log('XMLTV: buildGenres')
        with fileLocker(GLOBAL_FILELOCK):
            dom = parse(FileAccess.open(GENREFLE_DEFAULT, "r"))
        
        epggenres = {}
        lines = dom.getElementsByTagName('genre')
        for line in lines: 
            items = line.childNodes[0].data.split(' / ')
            for item in items:
                epggenres[item] = line.attributes['genreId'].value
            
        proggenres = []
        for program in self.xmltvList['programmes']:
            group = []
            for genre in program.get('category',[]):
                group.append(genre[0])
            proggenres.append(group)
            
        # [print(list(genre)) for genre in program.get('category',[]) for program in self.xmltvList['programmes']]
        for genres in proggenres:
            for genre in genres:
                if epggenres.get(genre,''):#{'Drama': '0x81'}
                    epggenres[(' / ').join(genres)] = epggenres.get(genre,'0x00')
                    break
                    
        doc  = Document()
        root = doc.createElement('genres')
        doc.appendChild(root)
        name = doc.createElement('name')
        name.appendChild(doc.createTextNode('%s Genres using Hexadecimal for genreId'%(ADDON_NAME)))
        root.appendChild(name)
        [root.appendChild(line) for line in lines] #append org. genre.xml list
        
        for key in epggenres:
            gen = doc.createElement('genre')
            gen.setAttribute('genreId',epggenres[key])
            gen.appendChild(doc.createTextNode(key))
            root.appendChild(gen)
        
        with fileLocker(GLOBAL_FILELOCK):
            xmlData = FileAccess.open(GENREFLE, "w")
            xmlData.write(doc.toprettyxml(indent='\t'))
            xmlData.close()
        return True


    def getEndtimes(self): 
        endtime    = {} # get "Endtime" channels last stopDate in programmes
        channels   = self.sortChannels(self.xmltvList['channels'])
        programmes = self.sortProgrammes(self.xmltvList['programmes'])
        log('XMLTV: getEndtimes, channels = %s, programmes = %s'%(len(channels), len(programmes)))
        for channel in channels:
            try: 
                stopDate = max([strpTime(program['stop'], DTFORMAT).timetuple() for program in programmes if program['channel'] == channel['id']])
                stopTime = time.mktime(stopDate)
                endtime[channel['id']] = stopTime
                log('XMLTV: getEndtimes, channelid = %s, endtime = %s, epoch = %s'%(channel['id'], stopDate, stopTime))
            except Exception as e: 
                log("XMLTV: getEndtimes, Failed! " + str(e), xbmc.LOGERROR)
                self.removeChannel(channel['id'])
        return endtime
         
         
    def resetData(self):
        log('XMLTV: resetData')
        return {'date'                : datetime.datetime.fromtimestamp(float(time.time())).strftime(DTFORMAT),
                'generator-info-name' : self.cleanString('%s Guidedata'%(ADDON_NAME)),
                'generator-info-url'  : self.cleanString(ADDON_ID),
                'source-info-name'    : self.cleanString(ADDON_NAME),
                'source-info-url'     : self.cleanString(ADDON_ID)}


    def addChannel(self, item, update=False):
        citem    = ({'id'           : item['id'],
                     'display-name' : [(self.cleanString(item['name']), LANG)],
                     'icon'         : [{'src':item['logo']}]})
        log('XMLTV: addChannel, update = %s, citem = %s'%(update,citem))
        idx, channel = self.findChannel(citem, self.xmltvList['channels'])
        if idx is None: self.xmltvList['channels'].append(citem)
        else:
            if update:
                self.xmltvList['channels'][idx].update(citem) # update existing channel meta
            else:
                self.xmltvList['channels'][idx] = citem       # replace existing channel meta
        return True


    def addProgram(self, id, item):
        pitem      = {'channel'     : id,
                      'credits'     : {'writer':['%s [COLOR item="%s"][/COLOR]'%(self.cleanString(item['writer']),encodeString(dumpJSON(item['fitem'])))]},
                      'category'    : [(self.cleanString(genre.replace('Unknown','Undefined')),LANG) for genre in item['categories']],
                      'title'       : [(self.cleanString(item['title']), LANG)],
                      'desc'        : [(self.cleanString(item['desc']), LANG)],
                      'star-rating' : [{'value': self.cleanStar(item['stars'])}],
                      'stop'        : (datetime.datetime.fromtimestamp(float(item['stop'])).strftime(DTFORMAT)),
                      'start'       : (datetime.datetime.fromtimestamp(float(item['start'])).strftime(DTFORMAT)),
                      'icon'        : [{'src': item['thumb']}],
                      'length'      : {'units': 'seconds', 'length': str(item['length'])}}

        if item.get('sub-title',''):
            pitem['sub-title'] = [(self.cleanString(item['sub-title']), LANG)]

        if item.get('director',''):
            pitem['credits']['director'] = [self.cleanString(item['director'])]

        if item.get('catchup-id',''):
            pitem['catchup-id'] = item['catchup-id']
            
        # if item['date']: #todo fix
            # pitem['date'] = (datetime.datetime.strptime(item['date'], '%Y-%m-%d')).strftime('%Y%m%d'),

        if item.get('new',False): 
            pitem['new'] = '' #write blank tag, tag == True
        
        rating = self.cleanMPAA(item.get('rating',''))
        if rating != 'NA' and rating.startswith('TV'): 
            pitem['rating'] = [{'system': 'VCHIP', 'value': rating}]
        elif rating != 'NA' :  
            pitem['rating'] = [{'system': 'MPAA', 'value': rating}]
            
        if item.get('episode-num',''): 
            pitem['episode-num'] = [(item['episode-num'], 'onscreen')]
            
        if item.get('audio',[]):
            pitem['audio'] = {'stereo': item.get('audio',[])[0]}

        if item.get('video',[]):
            pitem['video'] = {'aspect': item.get('video',[])[0]}
        
        if item.get('language',[]):
            pitem['language'] = (item.get('language',[])[0], LANG)
           
        if item.get('subtitle',[]): #needed?
            pitem['subtitles'] = [{'type': 'teletext', 'language': ('%s'%(sub), LANG)} for sub in item.get('subtitle',[])]
            
         ##### TODO #####
           # 'country'     : [('USA', LANG)],#todo
           # 'premiere': (u'Not really. Just testing', u'en'),
            
        log('XMLTV: addProgram = %s'%(pitem))
        self.xmltvList['programmes'].append(pitem)
        return True


    @staticmethod
    def cleanStar(str1):
        return '%s/10'%(int(round(float(str1))))


    @staticmethod
    def cleanMPAA(str1):
        #todo regex, detect other region rating formats
        try: return str1.split('Rated ')[1]
        except: return str1


    @staticmethod
    def cleanString(text):
        if text == ',' or not text: text = LANGUAGE(30161) #"Unavailable"
        return re.sub(u'[^\n\r\t\x20-\x7f]+',u'',text)
        
        
    @staticmethod
    def sortChannels(channels):
        try: channels.sort(key=lambda x:x.get('display-name'))
        except: pass
        log('XMLTV: sortChannels, channels = %s'%(len(channels)))
        return channels


    @staticmethod
    def sortProgrammes(programmes):
        programmes.sort(key=lambda x:x['start'])
        programmes.sort(key=lambda x:x['channel'])
        log('XMLTV: sortProgrammes, programmes = %s'%(len(programmes)))
        return programmes


    @staticmethod
    def cleanSelf(items, key='id', slug='@%s'%(slugify(ADDON_NAME))): # remove imports (Non PseudoTV Live), key = {'id':channels,'channel':programmes}
        log('XMLTV: cleanSelf, key = %s'%(key))
        if not slug: return items
        return list(filter(lambda item:item.get(key,'').endswith(slug), items))
        
        
    @staticmethod
    def cleanProgrammes(programmes): # remove expired content
        try: 
            now = (datetime.datetime.fromtimestamp(float(getLocalTime()))) - datetime.timedelta(hours=3) #allow some old programmes to avoid empty cells.
            try:    tmpProgrammes = [program for program in programmes if strpTime(program['stop'].rstrip(),DTFORMAT)  > now]
            except: tmpProgrammes = [program for program in programmes if strpTime(program['stop'].rstrip(),DTZFORMAT) > now]
        except Exception as e: 
            log("cleanProgrammes, Failed! " + str(e), xbmc.LOGERROR)
            tmpProgrammes = programmes
        log('XMLTV: cleanProgrammes, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
        return tmpProgrammes

        
    def removeChannel(self, id): # remove single channel and all programmes from xmltvList
        channels   = self.xmltvList['channels'].copy()
        programmes = self.xmltvList['programmes'].copy()
        self.xmltvList['channels']   = list(filter(lambda channel:channel.get('id','') != id, channels))
        self.xmltvList['programmes'] = list(filter(lambda program:program.get('channel','') != id, programmes))
        log('XMLTV: removeChannel, removing channel %s; channels: before = %s, after = %s; programmes: before = %s, after = %s'%(id,len(channels),len(self.xmltvList['channels']),len(programmes),len(self.xmltvList['programmes'])))
        return True
        
        
    @staticmethod
    def findChannel(item, channels): #find existing channel id in xmltvList
        for idx, channel in enumerate(channels): 
            if channel['id'] == item['id']: 
                return idx, channel
        return None, {}
        
        
    def save(self, reset=True):
        log('XMLTV: save')
        if reset: 
            data = self.resetData()
        else:     
            data = self.xmltvList['data']
            
        with fileLocker(GLOBAL_FILELOCK):
            writer = xmltv.Writer(encoding=DEFAULT_ENCODING, 
                                  date                = data['date'],
                                  source_info_url     = data['source-info-url'], 
                                  source_info_name    = data['source-info-name'],
                                  generator_info_url  = data['generator-info-url'], 
                                  generator_info_name = data['generator-info-name'])
                   
            channels = self.sortChannels(self.xmltvList['channels'])
            for channel in channels: writer.addChannel(channel)

            programmes = self.sortProgrammes(self.xmltvList['programmes'])
            for program in programmes: writer.addProgramme(program)
            
            log('XMLTV: save, saving to %s'%(XMLTVFLE))
            writer.write(FileAccess.open(XMLTVFLE, "w"), pretty_print=True)
            self.buildGenres()
        return self.reset() #force clean and memory/file parity 
        

    @staticmethod
    def delete():
        log('XMLTV: delete')
        if FileAccess.delete(XMLTVFLE): #xmltv.xml
            FileAccess.delete(GENREFLE) #genre.xml
            notificationDialog(LANGUAGE(30016)%('XMLTV'))
            

class M3U:
    def __init__(self, cache=None):
        log('M3U: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.m3uList   = {'data':'#EXTM3U tvg-shift="%s" x-tvg-url="" x-tvg-id=""'%(self.getShift()),
                          'channels':self.cleanSelf(self.load())}
        

    def getShift(self):
        log('M3U: getShift')
        return '' # '-%s'%((round(datetime.datetime.now().minute) / 60)[:3])

    
    def getChannels(self):
        log('M3U: getChannels')
        return self.sortChannels(self.m3uList.get('channels',[]))
        
        
    @staticmethod
    def sortChannels(channels):
        return sorted(channels, key=lambda k: k['number'])
        

    def reset(self):
        log('M3U: reset')
        self.__init__()
        return True


    def chkImport(self, channels, multiplier=1):
        def roundup(x):
            return x if x % 1000 == 0 else x + 1000 - x % 1000
        channels = sorted(channels, key=lambda k: k['number'])
        chstart  = roundup((CHANNEL_LIMIT * len(CHAN_TYPES)+1))
        chmin    = int(chstart + (multiplier*1000))
        chmax    = int(chmin + (CHANNEL_LIMIT))
        chrange  = list(range(chmin,chmax))
        log('M3U: chkImport, channels = %s, multiplier = %s, chstart = %s, chmin = %s, chmax = %s'%(len(channels),multiplier,chstart,chmin,chmax))
        #check tvg-chno for conflict, use multiplier to modify org chnum.
        for citem in channels:
            if len(chrange) == 0: #todo handle floats, which will increase import capacity. 
                log('M3U: chkImport, reached max import')
                break
            elif citem['number'] <= CHANNEL_LIMIT: 
                citem['number'] = (chmin+citem['number'])
                if citem['number'] in chrange: chrange.remove(citem['number'])
            else:              
                citem['number'] = chrange.pop(0)
            yield citem
        
    
    def importM3U(self, file, slug=None, multiplier=1):
        log('M3U: importM3U, file = %s'%file)
        try:
            if file.startswith('http'):
                url  = file
                file = os.path.join(TEMP_LOC,'%s.m3u'%(slugify(url)))
                saveURL(url,file)
            self.m3uList['channels'].extend(self.sortChannels(self.cleanSelf(self.chkImport(self.load(file),multiplier),slug)))
        except Exception as e: self.log("M3U: importM3U, failed! " + str(e), xbmc.LOGERROR)
        return True
        

    @staticmethod
    def load(file=M3UFLE):
        log('M3U: load, file = %s'%file)
        if file.startswith('http'):
            url  = file
            file = os.path.join(TEMP_LOC,slugify(url),'.m3u')
            saveURL(url,file)
            
        with fileLocker(GLOBAL_FILELOCK):
            fle   = FileAccess.open(file, 'r')
            lines = (fle.readlines())
            data  = lines.pop(0)
            fle.close()
        chCount = 0
        for idx, line in enumerate(lines):
            line = line.rstrip()
            if line.startswith('#EXTINF:'):
                chCount += 1
                match = {'number' :re.compile('tvg-chno=\"(.*?)\"'   , re.IGNORECASE).search(line),
                         'id'     :re.compile('tvg-id=\"(.*?)\"'     , re.IGNORECASE).search(line),
                         'name'   :re.compile('tvg-name=\"(.*?)\"'   , re.IGNORECASE).search(line),
                         'logo'   :re.compile('tvg-logo=\"(.*?)\"'   , re.IGNORECASE).search(line),
                         'group'  :re.compile('group-title=\"(.*?)\"', re.IGNORECASE).search(line),
                         'radio'  :re.compile('radio=\"(.*?)\"'      , re.IGNORECASE).search(line),
                         'catchup':re.compile('catchup=\"(.*?)\"'    , re.IGNORECASE).search(line),
                         'label'  :re.compile(',(.*)'                , re.IGNORECASE).search(line),
                         'shift'  :re.compile('tvg-shift=\"(.*?)\"'  , re.IGNORECASE).search(line)}#todo shift timestamp delta to localtime
                
                item  = {'number' :chCount,
                         'logo'   :LOGO,
                         'radio'  :'false',
                         'catchup':'',
                         'group'  :[],
                         'props'  :[]}
                         
                for key in match.keys():
                    if not match[key]: continue
                    item[key] = match[key].group(1)
                    if key == 'number':
                        try:    item[key] = int(item[key])
                        except: item[key] = float(item[key])
                    elif key == 'group':
                        item[key] = item[key].split(';')
                        try: item[key].remove(ADDON_NAME)
                        except: pass
                        finally: 
                            item[key] = list(filter(None,list(set(item[key]))))
                    elif key == 'radio':
                        item[key] = item[key].lower() == 'true'

                for nidx in range(idx+1,len(lines)):
                    nline = lines[nidx].rstrip()
                    if   nline.startswith('#EXTINF:'): break
                    elif nline.startswith('#KODIPROP:'):
                        prop = re.compile('^#KODIPROP:(.*)$', re.IGNORECASE).search(nline)
                        if prop: item['props'].append(prop.group(1))
                    elif nline.startswith('##'): continue
                    elif not nline: continue
                    else: item['url'] = nline
                        
                item['name']  = (item.get('name','')  or item.get('label',''))
                item['label'] = (item.get('label','') or item.get('name',''))
                if not item.get('id','') or not item.get('name','') or not item.get('number',''): 
                    log('M3U: load, SKIPPED MISSING META item = %s'%item)
                    continue
                log('M3U: load, item = %s'%item)
                yield item
                    

    def save(self):
        log('M3U: save')
        with fileLocker(GLOBAL_FILELOCK):
            fle = FileAccess.open(M3UFLE, 'w')
            log('M3U: save, saving to %s'%(M3UFLE))
            fle.write('%s\n'%(self.m3uList['data']))
            citem = '#EXTINF:-1 tvg-chno="%s" tvg-id="%s" tvg-name="%s" tvg-shift="%s" tvg-logo="%s" group-title="%s" radio="%s" catchup="%s",%s\n'
            channels = self.sortChannels(self.m3uList['channels'])
            for channel in channels:
                if not channel: continue
                fle.write(citem%(channel['number'],
                                 channel['id'],
                                 channel['name'],
                                 channel.get('shift',0),#opt from user imports, not used internally.
                                 channel['logo'],
                                 ';'.join(channel['group']),
                                 channel['radio'],
                                 channel['catchup'],
                                 channel['label']))
                if channel.get('props',[]):
                    fle.write('%s\n'%('\n'.join(['#KODIPROP:%s'%(prop) for prop in channel['props']])))
                fle.write('%s\n'%(channel['url']))
            fle.close()
        return self.reset() #force clean and memory/file parity 
        

    def addChannel(self, item, update=False):
        log('M3U: addChannel, update = %s, item = %s'%(update,item))
        idx, line = self.findChannel(item['id'])
        if idx is None: self.m3uList['channels'].append(item)
        else:
            if update: 
                self.m3uList['channels'][idx].update(item) # update existing channel
            else: 
                self.m3uList['channels'][idx] = item       # replace existing channel
        return True


    def findChannel(self, id):
        channels = self.m3uList['channels']
        for idx, line in enumerate(channels):
            if line.get('id','') == id:
                log('M3U: findChannel, idx = %s, line = %s'%(idx, line))
                return idx, line
        return None, {}
        
        
    def removeChannel(self, id=''):
        idx, line = self.findChannel(id)
        if idx is not None: 
            log('M3U: removeChannel, removing %s'%(line))
            self.m3uList['channels'].remove(line)
            return True
        return False


    @staticmethod
    def cleanSelf(channels, slug='@%s'%(slugify(ADDON_NAME))):
        log('M3U: cleanSelf, slug = %s'%(slug)) # remove imports (Non PseudoTV Live)
        if not slug: return channels
        return list(filter(lambda line:line.get('id','').endswith(slug), channels))
        

    @staticmethod
    def delete():
        log('M3U: delete')
        if FileAccess.delete(M3UFLE): return notificationDialog(LANGUAGE(30016)%('M3U'))
        return False