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

# -*- coding: utf-8 -*-

from resources.lib.globals     import *
from resources.lib             import xmltv
from resources.lib.fileaccess  import FileAccess, FileLock
from resources.lib.rules       import RulesList
from resources.lib.videoparser import VideoParser
from resources.lib.worker      import BaseWorker
 
GlobalFileLock = FileLock()

@contextmanager
def fileLocker():
    log('parser: fileLocker')
    GlobalFileLock.lockFile("MasterLock")
    try: yield
    finally: 
        GlobalFileLock.unlockFile('MasterLock')
        GlobalFileLock.close()

xmltv.locale      = 'utf-8'
xmltv.date_format = DTFORMAT
        
class Writer:
    def __init__(self):
        log('Writer: __init__')
        self.cache         = SimpleCache()
        self.m3u           = M3U(cache=self.cache)
        self.xmltv         = XMLTV(cache=self.cache)
        self.channels      = Channels(cache=self.cache)
        self.endtimes      = self.xmltv.xmltvList['endtimes']
        self.importEnabled = getSettingBool('User_Import')
        self.importLST     = self.buildImportLST()
        # if self.channels.isClient: self.syncCustom()
        
        
    def buildImportLST(self):
        log("Writer: buildImportLST") #todo insert custom groups.
        for n in range(MAX_IMPORT):
            yield {'m3u':getSetting('Import_M3U%s'%(n+1)),'xmltv':getSetting('Import_XMLTV%s'%(n+1)),'group':getSetting('Import_GROUP%s'%(n+1))}


    def reset(self):
        log('Writer: reset')
        if self.xmltv.reset() and self.m3u.reset():
            return True
        else: 
            return False
        
        
    def save(self):
        log('Writer: save')
        if self.cleanChannels():
            if self.importEnabled: 
                self.importSETS()
            if self.xmltv.save() and self.m3u.save():
                return True
        return False
        
        
    def importSETS(self):
        log('Writer: importSETS')
        for importItem in self.importLST: 
            self.m3u.importM3U(importItem.get('m3u',''))
            self.xmltv.importXMLTV(importItem.get('xmltv',''))
        return True
        
        
    def addChannel(self, citem, radio=False, catchup=True):
        log('Writer: addChannel, citem = %s, radio = %s, catchup = %s'%(citem,radio,catchup))
        self.m3u.addChannel(citem, radio, catchup)
        self.xmltv.addChannel(citem)
    
    
    def addProgrammes(self, citem, fileList, radio=False, catchup=True):
        log('Writer: addProgrammes, radio = %s, catchup = %s, programmes = %s, citem = %s'%(radio,catchup,len(fileList),citem))
        for idx, file in enumerate(fileList):
            if   not file: continue
            elif not file.get('file',''): continue
            item = {}
            item['radio']       = radio
            item['channel']     = citem['id']
            item['start']       = file['start']
            item['stop']        = file['stop']
            item['title']       = file['label']
            item['desc']        = file['plot']
            item['sub-title']   = (file.get('episodetitle','') or '')
            item['rating']      = (file.get('mpaa','')         or 'NA')
            item['stars']       = (file.get('rating','')       or '0')
            item['categories']  = (file.get('genre','')        or ['Undefined'])
            item['type']        = file.get('type','video')
            item['new']         = int(file.get('playcount','1')) == 0
            item['thumb']       = getThumb(file)
            item['date']        = (file.get('firstaired','') or file.get('premiered','') or file.get('releasedate','') or file.get('originaldate','') or None)
            
            if catchup:
                item['catchup-id'] = 'plugin://%s/?mode=vod&name=%s&id=%s&channel=%s&radio=%s'%(ADDON_ID,urllib.parse.quote(item['title']),urllib.parse.quote(encodeString(file.get('file',''))),urllib.parse.quote(citem['id']),str(item['radio']))
            
            if (item['type'] != 'movie' and (file.get("episode",0) > 0)):
                item['episode-num'] = 'S%sE%s'%(str(file.get("season",0)).zfill(2),str(file.get("episode",0)).zfill(2))
                
            item['director']    = (', '.join(file.get('director',[])) or '')
            item['writer']      = (', '.join(file.get('writer',[]))   or '')
            file['data']        = citem #channel dict
            item['file']        = encodeString(dumpJSON(file)) # kodi fileitem/listitem dict.
            self.xmltv.addProgram(citem['id'], item)
            
            
    def cleanChannels(self): # remove abandoned/missing channels
        log('Writer: cleanChannels')
        
        
        # log('M3U: cleanChannels')
        # if not self.m3uTMP: return
        # oldChannels = self.m3uTMP.copy()
        # newChannels = self.m3uList.copy()
        # newChannels.pop(0)
        # newIDS = [self.findChannelID(line) for line in newChannels]
        # [oldChannels.pop(idx) for idx, line in enumerate(oldChannels) if self.findChannelID(line) in newIDS]
        # [self.removeChannel(line) for line in oldChannels]
        # return True
        
            
            
        # oldChannels = self.xmltvTMP.copy()['channels']
        # newIDS = [citem['id'] for citem in self.xmltvNEW]
        # print(oldChannels,newIDS)
        
        # for citem in oldChannels:
            # print(citem['id'],citem['id'] in newIDS)
            # if citem['id'] in newIDS: 
                # print('pop',oldChannels.remove(citem))
            
        # # [oldChannels.pop(idx) for idx, citem in enumerate(self.xmltvTMP['channels']) if citem['id'] in newIDS]
        # print(oldChannels)
        # [self.removeChannel(citem['id']) for citem in oldChannels]
        return True
        
        
    def syncCustom(self): #todo sync user created smartplaylists/nodes for multi-room.
        for type in ['library','playlists']: 
            for media in ['video','music','mixed']: 
                path  = 'special://userdata/%s/%s/'%(type,media)
                files = FileAccess.listdir(path)[1]
                for file in files:
                    orgpath  = os.path.join(path,file)
                    copypath = os.path.join(CACHE_LOC,type,media,file)
                    log('parser: copyNodes, orgpath = %s, copypath = %s'%(orgpath,copypath))
                    yield FileAccess.copy(orgpath, copypath)


class Channels:
    def __init__(self, cache=None):
        log('Channels: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
        self.rules       = RulesList()
        self.channelList = (self.load() or self.getTemplate(ADDON_VERSION))
        self.ruleList    = sorted(self.rules.buildRuleList(), key=lambda k: k['id'])
        self.isClient    = self.chkClient()
        
        
    def reset(self):
        log('Channels: reset')
        self.__init__()
        return True


    def getUUID(self):
        log('Channels: getUUID')
        uuid = self.channelList.get('uuid','')
        if not uuid: 
            uuid = getMYUUID()
            self.channelList['uuid'] = uuid
        return uuid
        
        
    def chkClient(self):
        isClient = getClient()
        if not isClient:
            isClient = self.getUUID() != getMYUUID()
            if isClient: 
                setClient('true')
            else: 
                setClient('false')
        log('Channels: chkClient, isClient = %s'%(isClient))
        return isClient
        
        
    def getChannels(self):
        log('Channels: getChannels')
        return sorted(self.channelList.get('channels',[]), key=lambda k: k['number'])
        
        
    def getPredefined(self):
        log('Channels: getPredefined')
        return sorted(self.channelList.get('predefined',[]), key=lambda k: k['number'])
        
        
    def getAllChannels(self):
        log('Channels: getAllChannels')
        channels = self.getChannels()
        channels.extend(self.getPredefined())
        return channels
        
        
    def getRSVDchnums(self, channelkey='predefined'):
        log('Channels: getRSVDchnums, channelkey = %s'%(channelkey))
        return [channel["number"] for channel in self.channelList.get(channelkey,[])]


    def add(self, citem, channelkey=None):
        if channelkey is None:
            channelkey = 'predefined' if citem['number'] > CHANNEL_LIMIT else 'channels'
        log('Channels: add, item = %s, channelkey = %s'%(citem,channelkey))
        channels = self.channelList[channelkey]
        idx = self.findChannelIDX(citem, channels)
        if idx is not None:
            citem["number"] = channels[idx]["number"] # existing id found, reuse channel number.
            log('Channels: Updating channel %s, id %s'%(citem["number"],citem["id"]))
            channels[idx] = citem
        else:
            log('Channels: Adding channel %s, id %s'%(citem["number"],citem["id"]))
            channels.append(citem)
        self.channelList[channelkey] = sorted(channels, key=lambda k: k['number'])
        return True
        
        
    def remove(self, citem, channelkey=None):
        if channelkey is None:
            channelkey = 'predefined' if citem['number'] > CHANNEL_LIMIT else 'channels'
        log('Channels: removing item = %s, channelkey = %s'%(citem,channelkey))
        channels = self.channelList[channelkey]
        idx = self.findChannelIDX(citem, channels)
        if idx is not None: channels.pop(idx)
        self.channelList[channelkey] = channels
        return True
        
        
    def findChannelIDX(self, citem, channels, return_channel=False):
        for idx, channel in enumerate(channels):
            if (citem["id"] == channel["id"]):
                log('Channels: findChannelIDX, item = %s, found = %s'%(citem,channel))
                if return_channel: return channel
                return idx
        return None
        
        
    @use_cache(7)
    def getTemplate(self, version=ADDON_VERSION):
        log('Channels: getTemplate')
        data = self.load(CHANNELFLE_DEFAULT)
        data['uuid'] = getMYUUID()
        return data
        
        
    def getCitem(self):
        log('Channels: getCitem')
        return self.getTemplate(ADDON_VERSION).get('channels',[])[0].copy()
       

    def load(self, file=CHANNELFLE):
        log('Channels: load file = %s'%(file))
        if not FileAccess.exists(file): file = CHANNELFLE_DEFAULT
        fle  = FileAccess.open(file, 'r')
        data = loadJSON(fle.read())
        fle.close()
        return data
        

    def cleanSelf(self):
        log('Channels: cleanSelf') # remove channel template
        citem = self.getCitem()
        if citem in self.channelList.get('channels',[]):
            self.channelList['channels'].remove(citem)
            

    def save(self):
        self.cleanSelf()
        with fileLocker():
            fle = FileAccess.open(CHANNELFLE, 'w')
            log('Channels: save, saving to %s'%(CHANNELFLE))
            fle.write(dumpJSON(self.channelList, idnt=4, sortkey=False))
            fle.close()
        return True
        
        
    def delete(self):
        log('Channels: delete')
        if FileAccess.delete(CHANNELFLE):
            return notificationDialog(LANGUAGE(30016)%(LANGUAGE(30024)))


    def deleteSettings(self):
        log('Channels: deleteSettings')
        if FileAccess.delete(SETTINGS_FLE):
            return notificationDialog(LANGUAGE(30016)%('SETTINGS'))


    def addRule(self, citem, ritem, channelkey=None):
        if channelkey is None:
            channelkey = 'predefined' if citem['number'] > CHANNEL_LIMIT else 'channels'
        log('Channels: addRule, id = %s, rule = %s'%(citem['id'],ritem))
        rules = self.getChannelRules(citem)
        for rule in rules:
            if rule['id'] == ritem['id']:
                rule.update(ritem)
        if ritem not in rules: rules.append(ritem)
        self.channelList[channelkey]['rules'] = sorted(rules, key=lambda k: k['id'])
        return True


    def getChannelRules(self, citem, channels=None): #Channel rules
        log('Channels: getChannelRules, id = %s'%(citem['id']))
        if channels is None: channels = self.getAllChannels()
        for channel in channels:
            if channel['id'] == citem['id']:
                return channel.get('rules',[])
        return []


class XMLTV:
    def __init__(self, cache=None):
        log('XMLTV: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
        self.maxDays        = getSettingInt('Max_Days')
        self.xmltvList      = {'data'       : self.getData(),
                               'channels'   : self.cleanSelf(self.getChannels(),'id'),
                               'programmes' : self.cleanSelf(self.getProgrammes(),'channel')}
        self.xmltvList['endtimes'] = self.getEndtimes()
        
        
    def reset(self):
        log('XMLTV: reset')
        self.__init__()
        return True


    def importXMLTV(self, file):
        if not file: return False
        log('XMLTV: importXMLTV, file = %s'%file)
        if file.startswith('http'):
            url  = file
            file = os.path.join(TEMP_LOC,slugify(url),'.xml')
            saveURL(url,file)
        self.xmltvList['channels'].extend(self.getChannels(file)) #todo collision logic?
        self.xmltvList['programmes'].extend(self.getProgrammes(file))
        return True

        
    def getChannels(self, file=XMLTVFLE):
        log('XMLTV: getChannels, file = %s'%file)
        try: 
            return self.sortChannels(xmltv.read_channels(FileAccess.open(file, 'r')) or [])
        except Exception as e: 
            log('XMLTV: getChannels, failed! %s'%(e))
            return []
        
        
    def getProgrammes(self, file=XMLTVFLE):
        log('XMLTV: getProgrammes, file = %s'%file)
        try: 
            return self.sortProgrammes(self.cleanProgrammes(xmltv.read_programmes(FileAccess.open(file, 'r')) or []))
        except Exception as e: 
            log('XMLTV: getProgrammes, failed! %s'%(e))
            return []


    def getData(self):
        log('XMLTV: getData')
        try: 
            return (xmltv.read_data(FileAccess.open(XMLTVFLE, 'r')) or self.resetData())
        except Exception as e: 
            log('XMLTV: getData, failed! %s'%(e))
            return self.resetData()


    @use_cache(28)
    def getGenres(self, version=ADDON_VERSION):  #build list of all genre combinations. 
        log('XMLTV: getGenres')
        epggenres = {}
        xml   = FileAccess.open(GENREFLE_DEFAULT, "r")
        dom   = parse(xml)
        lines = dom.getElementsByTagName('genre')
        xml.close()
        for line in lines: 
            items = line.childNodes[0].data.split(' / ')
            for item in items: 
                epggenres[item] = line.attributes['genreId'].value
        return epggenres
        
        
    def buildGenres(self):
        log('XMLTV: buildGenres')
        programmes = self.xmltvList['programmes']
        genres = []
        # [genres.append(' / '.join(genre[0] for genre in program['category'])) for program in programmes]
        [genres.extend(genre for genre in program['category']) for program in programmes]
        try:
            epggenres = self.getGenres(ADDON_VERSION)
            doc  = Document()
            root = doc.createElement('genres')
            doc.appendChild(root)
            
            name = doc.createElement('name')
            name.appendChild(doc.createTextNode('%s Genres using Hexadecimal for genreId'%(ADDON_NAME)))
            root.appendChild(name)
            
            genres  = list(set(genres))
            matches = set(x[0] for x in genres)&set(x for x in epggenres)
            
            for key in matches:
                gen = doc.createElement('genre')
                gen.setAttribute('genreId',epggenres[key])
                gen.appendChild(doc.createTextNode(key))
                root.appendChild(gen)
            
            xmlData = FileAccess.open(GENREFLE, "w")
            xmlData.write(doc.toprettyxml(indent='\t'))
            xmlData.close()
        except Exception as e: log("xmltv: buildGenres, Failed! " + str(e), xbmc.LOGERROR)
        return


    def getEndtimes(self): # get "Endtime" channels last stopDate in programmes
        endtime    = {}
        now        = roundToHalfHour(getLocalTime())
        channels   = self.xmltvList['channels']
        programmes = self.xmltvList['programmes']
        
        for channel in channels:
            try: 
                stopDate = [program['stop'] for program in programmes if program['channel'] == channel['id']][-1]
                stopTime = time.mktime(strpTime(stopDate, DTFORMAT).timetuple())
                log('XMLTV: getEndtimes, channelid = %s, endtime = %s, epoch = %s'%(channel['id'], stopDate, stopTime))
            except Exception as e:
                log("getEndtimes, Error! channel %s, %s"%(channel['id'],e))
                stopTime = now
            endtime[channel['id']] = stopTime
        return endtime
         
         
    def resetData(self):
        log('XMLTV: resetData')
        return {'date'                : datetime.datetime.fromtimestamp(float(time.time())).strftime(xmltv.date_format),
                'generator-info-name' : '%s Guidedata'%(ADDON_NAME),
                'generator-info-url'  : ADDON_ID,
                'source-info-name'    : ADDON_NAME,
                'source-info-url'     : ADDON_ID}


    def addChannel(self, item):
        channels = self.xmltvList['channels']
        citem    = ({'id'           : item['id'],
                     'display-name' : [(self.cleanString(item['name']), LANG)],
                     'icon'         : [{'src':item['logo']}]})
        log('XMLTV: addChannel = %s'%(citem))
        channelIDX = self.findChannelIDX(citem, channels)
        if channelIDX is None: 
            channels.append(citem)
        else: 
            channels[channelIDX] = citem # update existing channel meta
        self.xmltvList['channels'] = channels
        return True


    def addProgram(self, id, item):
        programmes = self.xmltvList['programmes']
        pitem      = {'channel'     : id,
                      'credits'     : {'director': [item['director']], 'writer': ['%s [COLOR item="%s"][/COLOR]'%(item['writer'],item['file'])]},
                      'category'    : [(self.cleanString(genre.replace('Unknown','Undefined')),LANG) for genre in item['categories']],
                      'title'       : [(self.cleanString(item['title']), LANG)],
                      'sub-title'   : [(self.cleanString(item['sub-title']), LANG)],
                      'desc'        : [(self.cleanString(item['desc']), LANG)],
                      'star-rating' : [{'value': self.cleanStar(item['stars'])}],
                      'stop'        : (datetime.datetime.fromtimestamp(float(item['stop'])).strftime(xmltv.date_format)),
                      'start'       : (datetime.datetime.fromtimestamp(float(item['start'])).strftime(xmltv.date_format)),
                      'icon'        : [{'src': item['thumb']}]}

        if item.get('catchup-id',''):
            pitem['catchup-id'] = item['catchup-id']
        # if item['date']: #todo fix
            # pitem['date'] = (datetime.datetime.strptime(item['date'], '%Y-%m-%d')).strftime('%Y%m%d'),

        if item.get('new',''): 
            pitem['new'] = '' #write blank tag, tag == True
        
        rating = self.cleanMPAA(item.get('rating',''))
        if rating != 'NA' and rating.startswith('TV-'): 
            pitem['rating'] = [{'system': 'VCHIP', 'value': rating}]
        elif rating != 'NA' :  
            pitem['rating'] = [{'system': 'MPAA', 'value': rating}]
            
        if item.get('episode-num',''): 
            pitem['episode-num'] = [(item['episode-num'], 'onscreen')]
            
         ##### TODO #####
           # 'country'     : [('USA', LANG)],#todo
           # 'language': (u'English', u''),
           #  'length': {'units': u'minutes', 'length': '22'},
           # 'orig-language': (u'English', u''),
           # 'premiere': (u'Not really. Just testing', u'en'),
           # 'previously-shown': {'channel': u'C12whdh.zap2it.com', 'start': u'19950921103000 ADT'},
           # 'audio'       : {'stereo': u'stereo'},#todo                 
           # 'subtitles'   : [{'type': u'teletext', 'language': (u'English', u'')}],#todo
           # 'url'         : [(u'http://www.nbc.com/')],#todo
           # 'review'      : [{'type': 'url', 'value': 'http://some.review/'}],
           # 'video'       : {'colour': True, 'aspect': u'4:3', 'present': True, 'quality': 'standard'}},#todo
            
        log('XMLTV: addProgram = %s'%(pitem))
        programmes.append(pitem)
        self.xmltvList['programmes'] = programmes
        return True


    def cleanStar(self, str1):
        return '%s/10'%(int(round(float(str1))))


    def cleanMPAA(self, str1):
        #todo regex, detect other region rating strings
        try: return str1.split('Rated ')[1]
        except: return str1


    def cleanString(self, text):
        if text is None: return ''
        return text
        
        
    def sortChannels(self, channels=None):
        if channels is None: 
            channels = self.xmltvList['channels']
        channels.sort(key=lambda x:x['display-name'])
        log('XMLTV: sortChannels, channels = %s'%(len(channels)))
        return channels


    def sortProgrammes(self, programmes=None):
        if programmes is None: 
            programmes = self.xmltvList['programmes']
        programmes.sort(key=lambda x:x['channel'])
        programmes.sort(key=lambda x:x['start'])
        log('XMLTV: sortProgrammes, programmes = %s'%(len(programmes)))
        return programmes


    def cleanSelf(self, items, key='id'): # remove imports (Non PseudoTV Live)
        log('XMLTV: cleanSelf, key = %s'%(key))
        slugName = slugify(ADDON_NAME)
        return [item for item in items if item[key].endswith('@%s'%(slugName))]
        
        
    def cleanProgrammes(self, programmes=None): # remove expired content
        now = (datetime.datetime.fromtimestamp(float(getLocalTime()))) - datetime.timedelta(days=self.maxDays) #allow some old programmes to avoid empty cells.
        if programmes is None: programmes = self.xmltvList['programmes']
        try: 
            tmpProgrammes = [program for program in programmes if strpTime(program['stop'],xmltv.date_format) > now]
        except Exception as e: 
            log("cleanProgrammes, Failed! " + str(e), xbmc.LOGERROR)
            tmpProgrammes = programmes
        log('XMLTV: cleanProgrammes, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
        return tmpProgrammes


    def removeChannel(self, id): # remove single channel and all programmes from xmltvList
        channels   = self.xmltvList['channels']
        programmes = self.xmltvList['programmes']
        self.xmltvList['channels']   = [channel for channel in channels if channel['id'] != id]
        self.xmltvList['programmes'] = [program for program in programmes if program['channel'] != id]
        log('XMLTV: removeChannel, removing channel %s; channels: before = %s, after = %s; programmes: before = %s, after = %s'%(id,len(channels),len(self.xmltvList['channels']),len(programmes),len(self.xmltvList['programmes'])))
        return True
        

    def findChannelIDX(self, item, channels=None): #find existing channel id in xmltvList
        if channels is None: channels = self.xmltvList['channels']
        for idx, channel in enumerate(channels): 
            if channel['id'] == item['id']: 
                return idx
        return None
        
        
    def save(self, reset=True):
        log('XMLTV: save')
        if reset: 
            data = self.resetData()
        else:     
            data = self.xmltvList['data']
            
        writer = xmltv.Writer(encoding=xmltv.locale, date=data['date'],
                              source_info_url     = data['source-info-url'], 
                              source_info_name    = data['source-info-name'],
                              generator_info_url  = data['generator-info-url'], 
                              generator_info_name = data['generator-info-name'])
               
        channels = self.xmltvList['channels']
        for channel in channels: writer.addChannel(channel)

        programmes = self.sortProgrammes(removeDUPS(self.xmltvList['programmes']))
        for program in programmes: writer.addProgramme(program)
        
        with fileLocker():
            log('XMLTV: save, saving to %s'%(XMLTVFLE))
            writer.write(FileAccess.open(XMLTVFLE, "w"), pretty_print=True)
            self.buildGenres()
        return True
        

    def delete(self):
        log('XMLTV: delete')
        if FileAccess.delete(XMLTVFLE):
            FileAccess.delete(GENREFLE)
            return notificationDialog(LANGUAGE(30016)%('XMLTV'))


class M3U:
    def __init__(self, cache=None):
        log('M3U: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
        self.litem        = '#EXTINF:-1 tvg-chno="%s" tvg-id="%s" tvg-name="%s" tvg-logo="%s" group-title="%s" radio="%s"%s,%s\n%s'
        self.m3uList      = list(self.cleanSelf(self.load()))
        self.m3uTMP       = self.m3uList.copy()
        self.m3uList.insert(0,'#EXTM3U tvg-shift="%s" x-tvg-url="" x-tvg-id=""'%(self.getShift()))
        

    def getShift(self):
        log('M3U: getShift') #offset list to avoid rebuild starting at the top of the hour, might be useful?
        return ''
        # self.now = datetime.datetime.now()
        # min = str(round(self.now.minute) / 60)[:3]
        # return '-%s'%(min)


    def reset(self):
        log('M3U: reset')
        self.__init__()
        return True


    def importM3U(self, file):
        if not file: return False
        log('M3U: importM3U, file = %s'%file)   
        self.m3uList.extend(self.load(file)) #todo collision logic?
        return True
        

    def load(self, file=M3UFLE):
        log('M3U: load, file = %s'%file)
        if file.startswith('http'):
            url  = file
            file = os.path.join(TEMP_LOC,slugify(url),'.m3u')
            saveURL(url,file)
        fle = FileAccess.open(file, 'r')
        m3uListTMP = (fle.readlines())
        fle.close()
        return ['%s\n%s'%(line,m3uListTMP[idx+1]) for idx, line in enumerate(m3uListTMP) if line.startswith('#EXTINF:')]


    def save(self):
        log('M3U: save')
        with fileLocker():
            fle = FileAccess.open(M3UFLE, 'w')
            log('M3U: save, saving to %s'%(M3UFLE))
            fle.write('\n'.join([item for item in self.m3uList]))
            fle.close()
        return True
        

    def addChannel(self, item, radio=False, catchup=True, rebuild=True):
        log('M3U: addChannel, radio = %s, catchup = %s, rebuild = %s, item = %s'%(radio,catchup,rebuild,item))
        if catchup: 
            vod = ' catchup="vod"'
        else:
            vod = ''
            
        citem = self.litem%(item['number'],item['id'],item['name'],item['logo'],';'.join(item['group']),str(radio).lower(),vod,item['label'],item['url'])
        channelIDX = self.findChannelIDX(item['id'])
        if channelIDX is None:
            self.m3uList.append(citem)
        else:
            if rebuild: 
                self.removeChannel(id=item['id'])
                self.m3uList.append(citem)
            else:
                self.m3uList[channelIDX] = citem # update existing channel
        return True


    def findChannelNumber(self, line):
        if line.startswith('#EXTINF:'):
            match = re.compile('tvg-chno=\"(.*?)\"', re.IGNORECASE).search(line)
            if match: 
                log('M3U: findChannelNumber, found %s'%(match.group(1)))
                return match.group(1)
        return None
        
        
    def findChannelID(self, line):
        if line.startswith('#EXTINF:'):
            match = re.compile('tvg-id=\"(.*?)\"', re.IGNORECASE).search(line)
            if match: 
                log('M3U: findChannelID, found %s'%(match.group(1)))
                return match.group(1)
        return None


    def findChannelIDX(self, id='', channels=None, return_line=False):
        if channels is None: channels = self.m3uList
        for idx, line in enumerate(channels):
            lineID = self.findChannelID(line)
            if not lineID: continue
            if lineID == id:
                log('M3U: findChannelIDX, match = %s, idx = %s'%(line, idx))
                if return_line: return line
                return idx
        return None
        
        
    def removeChannel(self, line=None, id=''):
        if line is None: line = self.findChannelIDX(id, return_line=True)
        log('M3U: removeChannel, removing %s'%(line))
        if line is not None: self.m3uList.remove(line)
        return True


    def cleanSelf(self, items): # remove imports (Non PseudoTV Live)
        log('M3U: cleanSelf')
        slugName = slugify(ADDON_NAME)
        for line in items:
            lineID = (self.findChannelID(line) or '')
            if lineID.endswith('@%s'%(slugName)):
                yield line


    def delete(self):
        log('M3U: delete')
        if FileAccess.delete(M3UFLE): return notificationDialog(LANGUAGE(30016)%('M3U'))


class JSONRPC:
    def __init__(self, myWorker=None, cache=None):
        log('JSONRPC: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
        self.saveDuration     = getSettingBool('Store_Duration')
        self.videoParser      = VideoParser()
        self.myProcess        = Worker()
        self.resourcePacks    = self.buildLogoResources()
        self.myPlayer         = MY_PLAYER
        self.myMonitor        = MY_MONITOR
        self.processThread    = threading.Timer(30.0, self.myProcess.start)
        FileAccess.makedirs(LOGO_LOC)
        FileAccess.makedirs(CACHE_LOC)
        
        
    def startProcess(self):
        log("JSONRPC: startProcess")
        if self.processThread.isAlive():
            self.processThread.cancel()
            self.processThread.join()
        self.processThread = threading.Timer(30.0, self.myProcess.start)
        self.processThread.name = "processThread"
        self.processThread.start()


    def cacheJSON(self, command, life=datetime.timedelta(minutes=15)):
        cacheName = '%s.cacheJSON.%s'%(ADDON_ID,command)
        cacheResponse = self.cache.get(cacheName)
        if cacheResponse is None:
            cacheResponse = sendJSON(command)
            self.cache.set(cacheName, cacheResponse, checksum=len(cacheResponse), expiration=life)
        return cacheResponse

        
    def getActivePlayer(self, return_item=False):
        json_query = ('{"jsonrpc":"2.0","method":"Player.GetActivePlayers","params":{},"id":1}')
        json_response = (sendJSON(json_query))
        item = json_response.get('result',[])[0]
        try: id = item['playerid']
        except: id = 1
        log("JSONRPC: getActivePlayer, id = %s"%(id))
        if return_item: return item
        return id
        
        
    def getActivePlaylist(self):
        json_query = ('{"jsonrpc":"2.0","method":"Playlist.GetPlaylists","params":{},"id":1}')
        json_response = (sendJSON(json_query)).get('result',[])[0]
        ptype = self.getActivePlayer(return_item=True).get('type','video')
        try: 
            for type in json_response:
                if type['type'] == ptype:
                    id = type["playlistid"]
                    log("JSONRPC: getActivePlaylist, id = %s"%(id))
                    return id
        except: id = 1
        return id
        
        
    def getPlayerItem(self, playlist=False):
        log('JSONRPC: getPlayerItem, playlist = %s'%(playlist))
        if playlist: json_query = '{"jsonrpc":"2.0","method":"Playlist.GetItems","params":{"playlistid":%s,"properties":["runtime","title","plot","genre","year","studio","mpaa","season","episode","showtitle","thumbnail","file"]},"id":1}'%(self.getActivePlaylist())
        else:        json_query = '{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":%s,"properties":["file","writer","channel","channels","channeltype","mediapath"]}, "id": 1}'%(self.getActivePlayer())
        result = sendJSON(json_query).get('result',{})
        return (result.get('item',{}) or result.get('items',{}))
           

    def getPVRChannels(self, radio=False):
        type = 'allradio' if radio else 'alltv'
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetChannels","params":{"channelgroupid":"%s","properties":["icon","channeltype","channelnumber","broadcastnow","broadcastnext"]}, "id": 1}'%(type))
        return sendJSON(json_query).get('result',{}).get('channels',[])


    def getPVRBroadcasts(self, id):
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetBroadcasts","params":{"channelid":%s,"properties":["title","plot","starttime","runtime","progress","progresspercentage","episodename","writer","director"]}, "id": 1}'%(id))
        return sendJSON(json_query).get('result',{}).get('broadcasts',[])


    def matchPVRPath(self, channelid=None):
        if channelid is None: 
            log('JSONRPC: matchPVRPath no channelid provided')
            return ''
        log('JSONRPC: matchPVRPath, channelid = %s'%(channelid))
        selfPath      = 'pvr://channels/tv/%s/'%(urllib.parse.quote(ADDON_NAME))
        json_query    = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","properties":["file"]},"id":1}'%(selfPath))
        json_response = sendJSON(json_query).get('result',{}).get('files',[])
        if len(json_response) == 0:
            pvrPath       = "pvr://channels/tv/All%20channels/"
            json_query    = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","properties":["file"]},"id":2}'%(pvrPath))
            json_response = sendJSON(json_query).get('result',{}).get('files',[])
        try: 
            for path in json_response:
                if channelid == path['id']:
                    log('JSONRPC: matchPVRPath, found path = %s'%(path['file']))
                    return path['file']
            log('JSONRPC: matchPVRPath, path not found \n%s'%(dumpJSON(json_response)))
            # path = [path['file'] for path in json_response if channelid == path['id']][0]
            # log('JSONRPC: matchPVRPath, found path = %s'%(path))
            # return path
        except Exception as e:  
            log("JSONRPC: matchPVRPath, Failed! " + str(e), xbmc.LOGERROR)
            notificationDialog(LANGUAGE(30059))
            brutePVR()
            return ''
        

    def matchPVRChannel(self, chname, id, radio=False): # Convert PseudoTV Live channelID into a Kodi channelID for playback
        channels = self.getPVRChannels(radio)
        for item in channels:
            writer = item.get('broadcastnow',{}).get('writer','')
            if not writer: continue #filter other PVR backends
            try: 
                if getWriter(writer)['data']['id'] == id:
                    log('matchPVRChannel, match found chname = %s, id = %s'%(chname,id))
                    return item
            except: continue
        return None
        
        
    def fillPVRbroadcasts(self, channelItem):
        log('JSONRPC: fillPVRbroadcasts')
        channelItem['broadcastnext'] = []
        json_response = self.getPVRBroadcasts(channelItem['channelid'])
        for idx, item in enumerate(json_response):
            if item['progresspercentage'] == 100: continue
            elif item['progresspercentage'] > 0: 
                broadcastnow = channelItem['broadcastnow']
                channelItem.pop('broadcastnow')
                item.update(broadcastnow) 
                channelItem['broadcastnow'] = item
            elif item['progresspercentage'] == 0: 
                channelItem['broadcastnext'].append(item)
        log('JSONRPC: fillPVRbroadcasts, found broadcastnext = %s'%(len(channelItem['broadcastnext'])))
        return channelItem
        
        
    def getPVRposition(self, chname, id, radio=False, isPlaylist=False): # Current PVR Position data
        log('JSONRPC: getPVRposition, chname = %s, id = %s, isPlaylist = %s'%(chname,id,isPlaylist))
        channelItem = self.matchPVRChannel(chname, id, radio)
        if not channelItem: return {}
        if isPlaylist:
            channelItem = self.fillPVRbroadcasts(channelItem)
        else: 
            channelItem['broadcastnext'] = [channelItem.get('broadcastnext',[])]
        return channelItem


    def fillTVShows(self):
        tvshows = []
        if not hasTV(): return tvshows
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":{"properties":["title","genre","year","rating","plot","studio","mpaa","cast","playcount","episode","imdbnumber","premiered","votes","lastplayed","fanart","thumbnail","file","originaltitle","sorttitle","episodeguide","season","watchedepisodes","dateadded","tag","art","userrating","ratings","runtime","uniqueid"]}, "id": 1}')
        json_response = (self.cacheJSON(json_query)).get('result',{}).get('tvshows',[])
        for item in json_response: tvshows.append({'label':item['label'],'item':item,'thumb':item['thumbnail']})
        log('jsonrpc, fillTVShows, found = %s'%(len(tvshows)))
        return tvshows


    def fillMusicInfo(self, sortbycount=True):
        genres = []
        MusicGenreList = []
        if not hasMusic(): return MusicGenreList
        json_query = ('{"jsonrpc":"2.0","method":"AudioLibrary.GetSongs","params":{"properties":["genre"]},"id":1}')
        json_response = self.cacheJSON(json_query).get('result',{}).get('songs',[])
        [genres.extend(re.split(';|/|,',genre.strip())) for song in json_response for genre in song.get('genre',[])]
        genres = collections.Counter([genre for genre in genres if not genre.isdigit()])
        if sortbycount: genres.most_common(25)
        values = sorted(genres.items())
        [MusicGenreList.append(key) for key, value in values]
        MusicGenreList.sort(key=lambda x: x.lower())
        log('jsonrpc, fillMusicInfo, found genres = %s'%(MusicGenreList))
        return MusicGenreList


    def getTVInfo(self, sortbycount=False):
        log('jsonrpc, getTVInfo')
        NetworkList   = []
        ShowGenreList = []
        if not hasTV(): return NetworkList, ShowGenreList
        
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":{"properties":["studio","genre"]},"id":1}')
        json_response = (self.cacheJSON(json_query)).get('result',{}).get('tvshows',[])
        
        for info in json_response:
            networks = info.get('studio','')
            if networks:
                for network in networks:
                    found = False
                    for n in range(len(NetworkList)):
                        itm = NetworkList[n]
                        if sortbycount: itm = itm[0]
                        if network.lower() == itm.lower():
                            found = True
                            if sortbycount: NetworkList[n][1] += 1
                            break
                            
                    if found == False:
                        if sortbycount: NetworkList.append([network, 1])
                        else: NetworkList.append(network)

            genres = info.get('genre','')
            if genres:
                for genre in genres:
                    found = False
                    for g in range(len(ShowGenreList)):
                        itm = ShowGenreList[g]
                        if sortbycount: itm = itm[0]
                        if genre.lower() == itm.lower():
                            found = True
                            if sortbycount: ShowGenreList[g][1] += 1
                            break
                            
                    if found == False:
                        if sortbycount: ShowGenreList.append([genre, 1])
                        else: ShowGenreList.append(genre)

        if sortbycount:
            NetworkList.sort(key=lambda x: x[1], reverse = True)
            ShowGenreList.sort(key=lambda x: x[1], reverse = True)
        else:
            NetworkList.sort(key=lambda x: x.lower())
            ShowGenreList.sort(key=lambda x: x.lower())
        log('jsonrpc, getTVInfo, networks = %s, genres = %s'%(len(NetworkList),len(ShowGenreList)))
        return NetworkList, ShowGenreList


    def getMovieInfo(self, sortbycount=False):
        log('jsonrpc, getMovieInfo')
        tmpStudios     = []
        StudioList     = []
        MovieGenreList = []
        if not hasMovie(): return StudioList, MovieGenreList
        
        json_query = ('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties":["studio", "genre"]}, "id": 1}')
        json_response = (self.cacheJSON(json_query)).get('result',{}).get('movies',[])
        
        for info in json_response:
            genres = info.get('genre','')
            if genres:
                for genre in genres:
                    found = False
                    for g in range(len(MovieGenreList)):
                        itm = MovieGenreList[g]
                        if sortbycount: itm = itm[0]
                        if genre.lower() == itm.lower():
                            found = True
                            if sortbycount: MovieGenreList[g][1] += 1
                            break
                            
                    if not found:
                        if sortbycount: MovieGenreList.append([genre.replace('"','').strip(), 1])
                        else: MovieGenreList.append(genre.replace('"','').strip())

            studios = info.get('studio','')
            if studios:
                for studio in studios:
                    found = False
                    for i in range(len(tmpStudios)):
                        if tmpStudios[i][0].lower() == studio.lower():
                            tmpStudios[i][1] += 1
                            found = True
                            break
                    if found == False and len(studio) > 0: tmpStudios.append([studio, 1])

        maxcount = 0
        for i in range(len(tmpStudios)):
            if tmpStudios[i][1] > maxcount: maxcount = tmpStudios[i][1]

        bestmatch = 1
        lastmatch = 1000
        counteditems = 0

        for i in range(maxcount, 0, -1):
            itemcount = 0
            for j in range(len(tmpStudios)):
                if tmpStudios[j][1] == i: itemcount += 1
            if abs(itemcount + counteditems - 8) < abs(lastmatch - 8):
                bestmatch = i
                lastmatch = itemcount
            counteditems += itemcount

        if sortbycount:
            tmpStudios.sort(key=lambda x: x[1], reverse=True)
            MovieGenreList.sort(key=lambda x: x[1], reverse=True)
        else:
            tmpStudios.sort(key=lambda x: x[0].lower())
            MovieGenreList.sort(key=lambda x: x.lower())

        for i in range(len(tmpStudios)):
            if tmpStudios[i][1] >= bestmatch:
                if sortbycount: StudioList.append([tmpStudios[i][0], tmpStudios[i][1]])
                else: StudioList.append(tmpStudios[i][0])
        log('jsonrpc, getMovieInfo, studios = %s, genres = %s'%(len(StudioList),len(MovieGenreList)))
        return StudioList, MovieGenreList
        

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
        
        log('jsonrpc, requestList, path = %s, params = %s, page = %s'%(path,params,page))
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":'+dumpJSON(params)+',"id":1}')
        json_response = (self.cacheJSON(json_query))
        
        if 'filedetails' in json_response: 
            key = 'filedetails'
        else: 
            key = 'files'
            
        results = json_response.get('result',{})
        items   = results.get(key,[])
        limits  = results.get('limits',params['limits'])
        log('jsonrpc, requestList, response items = %s, key = %s, limits = %s'%(len(items),key,limits))
        
        if limits.get('end',0) >= limits.get('total',0): # restart page, exceeding boundaries.
            log('jsonrpc, requestList resetting page to 0')
            limits = {"end": 0, "start": 0, "total": 0}
        self.autoPagination(id, path, limits)
        
        if len(items) == 0 and limits.get('start',0) > 0 and limits.get('total',0) > 0:
            log("jsonrpc: requestList, trying again at start page 0")
            return self.requestList(id, path, media, page, sort, filter, limits)
        
        log("jsonrpc: requestList return, items size = %s"%len(items))
        return items


    @use_cache(1) # check for duration data.
    def existsVFS(self, path, media='video', accurate=ACCURATE_DURATION):
        log('jsonrpc, existsVFS path = %s, media = %s'%(path,media))
        dirs  = []
        json_response = self.requestList(str(random.random()), path, media)
        for item in json_response:
            file = item.get('file','')
            fileType = item.get('filetype','file')
            if fileType == 'file':
                dur = self.getDuration(file, item, accurate)
                if dur > 0: return {'file':file,'duration':dur,'seek':self.chkSeeking(file, dur)}
            else: dirs.append(file)
        for dir in dirs: return self.existsVFS(dir, media)
        return None


    def chkSeeking(self, file, dur):
        if not file.startswith(('plugin://','upnp://')): return True
        #todo test seek for support disable via adv. rule if fails.
        notificationDialog(LANGUAGE(30142))
        liz = xbmcgui.ListItem('Seek Test',path=file)
        playpast = False
        progress = int(dur/2)
        liz.setProperty('totaltime'  , str(dur))
        liz.setProperty('resumetime' , str(progress))
        liz.setProperty('startoffset', str(progress))
        liz.setProperty("IsPlayable" ,"true")
        if self.myPlayer.isPlaying(): return True #todo prompt to stop playback and test.
        self.myPlayer.play(file,liz,windowed=True)
        while not self.myMonitor.abortRequested():
            log('jsonrpc, chkSeeking seeking')
            if self.myMonitor.waitForAbort(2): break
            elif not self.myPlayer.isPlaying(): break
            if int(self.myPlayer.getTime()) > progress:
                log('jsonrpc, chkSeeking seeking complete')
                playpast = True
                break
        while not self.myMonitor.abortRequested() and self.myPlayer.isPlaying():
            if self.myMonitor.waitForAbort(1): break
            log('jsonrpc, chkSeeking stopping playback')
            self.myPlayer.stop()
        msg = LANGUAGE(30143) if playpast else LANGUAGE(30144)
        log('jsonrpc, chkSeeking file = %s %s'%(file,msg))
        notificationDialog(msg)
        return playpast


    @use_cache(1)
    def listVFS(self, path, version=None):
        log('jsonrpc, listVFS path = %s, version = %s'%(path,version))
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","properties":["duration","runtime"]},"id":1}'%(path))
        json_response = (sendJSON(json_query)).get('result',{}).get('files',[])
        dirs, files = [[],[]]
        for item in json_response:
            file = item['file']
            if item['filetype'] == 'file':
                if self.parseDuration(file, item) == 0: continue
                files.append(file)
            else: dirs.append(file)
        return dirs, files
        
        
    def autoPagination(self, id, path, limits={}):
        cacheName = '%s.autoPagination.%s.%s'%(ADDON_ID,id,path)
        if not limits:
            msg = 'get'
            limits = (self.cache.get(cacheName) or {"end": 0, "start": 0, "total": 0})
        else:
            msg = 'set'
            self.cache.set(cacheName, limits, checksum=len(limits), expiration=datetime.timedelta(days=28))
        log("jsonrpc, %s autoPagination, path = %s, limits = %s"%(msg,path,limits))
        return limits


    def getDuration(self, path, item={}, accurate=False):
        log("jsonrpc, getDuration; accurate = %s, path = %s"%(accurate,path))
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
                if path.startswith(('plugin://','upnp://')):
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
        conditions = [(dbid > 0),(runtime != duration),(rundiff < 25),(duration > 0)]
        if self.saveDuration and (False not in conditions):
            self.setDuration(item['type'], dbid, duration)
        log("jsonrpc, parseDuration, path = %s, duration = %s"%(path,duration))
        return duration


    def setDuration(self, media, dbid, dur):
        self.startProcess()
        if media == 'movie': 
            param = '{"jsonrpc": "2.0", "method":"VideoLibrary.SetMovieDetails"  ,"params":{"movieid"   : %i, "runtime" : %i }, "id": 1}'%(dbid,dur)
        elif media == 'episode': 
            param = '{"jsonrpc": "2.0", "method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid" : %i, "runtime" : %i }, "id": 1}'%(dbid,dur)
        if param: 
            log('setDuration, media = %s, dbid = %s, dur = %s'%(media, dbid, dur))
            self.myProcess.send('sendJSON', param)
             

    @use_cache(28)
    def getStreamDetails(self, path, media='video'):
        log("getStreamDetails, path = " + path)
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetFileDetails","params":{"file":"%s","media":"%s","properties":["streamdetails"]},"id":1}'%((path),media))
        json_response = sendJSON(json_query).get('result',{}).get('filedetails',{}).get('streamdetails',{})
        if json_response: return json_response
        return {}


    def CHKUPNP_Setting(self):
        log('CHKUPNP_Setting')# Check Kodi UPNP support.
        json_query = ('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"services.upnp"},"id":1}')
        if sendJSON(json_query).get('result',{}).get('value',True) == False: self.setUPNP_Setting()
        
    
    def setUPNP_Setting(self):
        log('setUPNP_Setting') #Enable Kodi UPNP support.
        json_query = ('{"jsonrpc":"2.0","method":"Settings.SetSettingValue","params":{"setting":"services.upnp","value":true},"id":1}')
        return sendJSON(json_query)

    
    def getUPNP_IDs(self):
        log('getUPNP_IDs') #Check if upnp id is valid.
        self.CHKUPNP_Setting()
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"upnp://"},"id":1}')
        return sendJSON(json_query).get('result',{}).get('files',[])
            
            
    def chkUPNP(self, path):
        log('chkUPNP') #Query json, match old path with new upnp id.
        files = self.getUPNP_IDs()
        return path
        # for file in files:            
        # log('jsonrpc, existsVFS path = %s, media = %s'%(path,media))
        # dirs  = []
        # json_response = self.requestList(str(random.random()), path, media)
        # for item in json_response:
            # file = item.get('file','')
            # fileType = item.get('filetype','file')
            # if fileType == 'file':
                # dur = self.getDuration(file, item, accurate)
                # if dur > 0: return {'file':file,'duration':dur,'seek':self.chkSeeking(file, dur)}
            # else: dirs.append(file)
        # for dir in dirs: return self.existsVFS(dir, media)
        # return None
            # if file.get('label','').lower() == label.lower(): return file.get('file',path)
        # return path


    def buildResourcePath(self, path, file):
        if path.startswith('resource://'):
            path = path.replace('resource://','special://home/addons/') + '/resources/%s'%(file)
        else: 
            path = os.path.join(path,file)
        return path
        
    
    def buildBCTresource(self, path):
        resourceMap = {}
        log('jsonrpc, buildBCTresource, path = %s'%(path))
        if path.startswith('resource://'):
            dirs, files = self.getResourcesFolders(path,self.getPluginMeta(path).get('version',''))
            resourceMap = {'path':path,'files':files,'dirs':dirs,'filepaths':[self.buildResourcePath(path,file) for file in files]}
        elif path.startswith('plugin://'):
            dirs, files = self.listVFS(path,self.getPluginMeta(path).get('version',''))
            resourceMap = {'path':path,'files':files,'dirs':dirs,'filepaths':files}
        return resourceMap
        
            
    def buildLogoResources(self):
        log('jsonrpc, buildLogoResources')
        logos     = []
        radios    = ["resource://resource.images.musicgenreicons.text"]
        genres    = ["resource://resource.images.moviegenreicons.transparent"]
        studios   = ["resource://resource.images.studios.white/", "resource://resource.images.studios.coloured/"]
        if USE_COLOR: studios.reverse()
        #todo apply music genres to custom channels.
        [logos.append({'type':['MUSIC Genres'],'path':radio,'files': self.getResourcesFolders(radio, self.getPluginMeta(radio).get('version',''))[1]}) for radio in radios]
        [logos.append({'type':['TV Genres','MOVIE Genres','MIXED Genres','Custom'],'path':genre,'files': self.getResourcesFolders(genre, self.getPluginMeta(genre).get('version',''))[1]}) for genre  in genres]
        [logos.append({'type':['TV Networks','MOVIE Studios','Custom'],'path':studio,'files': self.getResourcesFolders(studio, self.getPluginMeta(studio).get('version',''))[1]}) for studio in studios]
        logos.append( {'type':['TV Shows','Custom'],'path':'','files': self.fillTVShows()})
        log('jsonrpc, buildLogoResources return')
        return logos


    @use_cache(1)
    def getPluginMeta(self, plugin):
        return getPluginMeta(plugin)
    
    
    @use_cache(28)
    def getResourcesFolders(self, path, version=None):
        log('jsonrpc, getResourcesFolders path = %s, version = %s'%(path,version))
        try: 
            return FileAccess.listdir(path)
        except: 
            return [],[]


    @use_cache(7)
    def findLogo(self, channelname, channeltype, useColor, featured=False, version=ADDON_VERSION):
        log('findLogo')
        for item in self.resourcePacks:
            if channeltype in item['type']:
                for file in item['files']:
                    if isinstance(file, dict):
                        #jsonrpc item
                        fileItem = file.get('item',{})
                        if channelname.lower() == fileItem.get('label','').lower(): 
                            return self.cacheImage(channelname,fileItem.get('art',{}).get('clearlogo',''),featured)
                    else:
                        #resource file
                        if os.path.splitext(file.lower())[0] == channelname.lower():
                            return self.cacheImage(channelname,os.path.join(item['path'],file),featured)
        return LOGO
        
        
    def cacheImage(self, channelname, logo, featured): #copy image to users logo folder. #todo translate .xbt resource:// to github urls? 
        if featured:
            log('cacheImage: channelname = %s, featured = %s'%(channelname,featured))
            localIcon = os.path.join(LOGO_LOC,'%s.png'%(channelname))
            if logo.startswith('resource://'): return logo #todo parse xbt and extract image?
            # if FileAccess.copy(logo, localIcon): return localIcon
        return logo
        
        
    def getLogo(self, channelname, type='Custom', path=None, featured=False):
        # features; in-use by a channel, triggers future local caching.
        if not channelname: return
        log('getLogo: channelname = %s, type = %s'%(channelname,type))
        icon      = LOGO
        localIcon = os.path.join(IMAGE_LOC,'%s.png'%(channelname))
        userIcon  = os.path.join(LOGO_LOC,'%s.png'%(channelname))
        if FileAccess.exists(userIcon): 
            log('getLogo: using user logo = %s'%(userIcon))
            icon = userIcon
        elif FileAccess.exists(localIcon): 
            log('getLogo: using local logo = %s'%(localIcon))
            icon = localIcon
        else:
            icon = (self.findLogo(channelname, type, USE_COLOR, featured, ADDON_VERSION) or LOGO)
        log('getLogo: icon = %s'%(icon))
        if icon.endswith(('wlogo.png','logo.png','icon.png')):
            if isinstance(path, list): path = path[0]
            elif path is not None:
                if path.startswith('plugin://'): icon = self.getPluginMeta(path).get('icon',LOGO)
        if icon.startswith(ADDON_PATH):
            icon = icon.replace(ADDON_PATH,'special://home/addons/%s/'%(ADDON_ID))
        log('getLogo, channelname = %s, logo = %s'%(channelname,icon))
        return icon
        
        
class Worker(BaseWorker):
    def do_sendJSON(self, param):
        log('Worker: do_sendJSON, param = %s'%(param))
        sendJSON(param)