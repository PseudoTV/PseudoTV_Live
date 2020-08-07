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

# https://bitbucket.org/jfunk/python-xmltv/src/default/README.txt
# https://github.com/kodi-pvr/pvr.iptvsimple/blob/Matrix/README.md#m3u-format-elements

# -*- coding: utf-8 -*-

from resources.lib.globals     import *
from resources.lib             import xmltv
from resources.lib.fileaccess  import FileAccess
from resources.lib.videoparser import VideoParser
 
xmltv.locale      = 'UTF-8'
xmltv.date_format = DTFORMAT
LINE_ITEM         = '#EXTINF:0 tvg-chno=%s tvg-id="%s" tvg-name="%s" tvg-logo="%s" group-title="%s" radio="%s",%s\n%s'

class Channels:
    def __init__(self):
        self.jsonRPC      = JSONRPC()
        self.cache        = self.jsonRPC.cache
        self.channelList  = (self.load() or self.getTemplate(ADDON_VERSION))
        
        
    def reset(self):
        log('channels: reset')
        self.__init__()
        return True


    def getChannels(self):
        log('channels: getChannels')
        return sorted(self.channelList.get('channels',[]), key=lambda k: k['number'])
        
        
    def getPredefined(self):
        log('channels: getPredefined')
        return sorted(self.channelList.get('predefined',[]), key=lambda k: k['number'])
        
        
    def getAllChannels(self):
        log('channels: getAllChannels')
        channels = self.getChannels()
        channels.extend(self.getPredefined())
        return channels
        
        
    def getReservedChannels(self, channelkey='predefined'):
        log('channels: getReservedChannels, channelkey = %s'%(channelkey))
        return [channel["number"] for channel in self.channelList.get(channelkey,[])]


    def add(self, item):
        channelkey = 'predefined' if item['number'] > CHANNEL_LIMIT else 'channels'
        log('channels: add, item = %s, channelkey = %s'%(item,channelkey))
        channels = self.channelList[channelkey]
        idx = self.findChannelIDX(item, channels)
        if idx:
            item["number"] = channels[idx]["number"]
            log('channels: Updating channel %s, id %s'%(item["number"],item["id"]))
            channels[idx] = item
        else:
            log('channels: Adding channel %s, id %s'%(item["number"],item["id"]))
            channels.append(item)
        self.channelList[channelkey] = sorted(channels, key=lambda k: k['number'])
        return True
        
        
    def remove(self, item):
        channelkey = 'predefined' if item['number'] > CHANNEL_LIMIT else 'channels'
        log('channels: removing item = %s, channelkey = %s'%(item,channelkey))
        channels = self.channelList[channelkey]
        idx = self.findChannelIDX(item, channels)
        if idx: channels.pop(idx)
        self.channelList[channelkey] = channels
        return True
        
        
    def findChannelIDX(self, item, channels, return_channel=False):
        for idx, channel in enumerate(channels):
            if (item["id"] == channel["id"]):
                log('channels: findChannelIDX, item = %s, found = %s'%(item,channel))
                if return_channel: return channel
                return idx
        return None
        
        
    @use_cache(28)
    def getTemplate(self, version=ADDON_VERSION):
        log('channels: getTemplate')
        return self.load(CHANNELFLE_DEFAULT)
        
        
    def getCitem(self):
        log('channels: getCitem')
        return self.getTemplate(ADDON_VERSION).get('channels',[])[0]
       
       
    def load(self, file=CHANNELFLE):
        log('channels: load file = %s'%(file))
        if not FileAccess.exists(file): file = CHANNELFLE_DEFAULT
        fle  = FileAccess.open(file, 'r')
        data = loadJSON(fle.read())
        fle.close()
        return data
        

    def save(self):
        fle = FileAccess.open(CHANNELFLE, 'w')
        log('channels: save, saving to %s'%(CHANNELFLE))
        fle.write(dumpJSON(self.channelList, idnt=4, sortkey=False))
        fle.close()
        return True
        
        
    def delete(self):
        log('channels: delete')
        if FileAccess.delete(CHANNELFLE):
            notificationDialog(LANGUAGE(30016)%(LANGUAGE(30024)))


class XMLTV:
    def __init__(self):
        self.cache       = SimpleCache()
        self.xmltvTMP    = []
        self.maxDays     = getSettingInt('Max_Days')
        self.xmltvList   = {'data'       : self.getData(),
                            'channels'   : self.cleanSelf(self.getChannels(),'id'),
                            'programmes' : self.cleanSelf(self.getProgrammes(),'channel')}
        self.xmltvList['endtimes'] = self.getEndtimes()
        self.extImport      = getSettingBool('User_Import')
        self.extImportXMLTV = getSetting('Import_XMLTV')

        
    def reset(self):
        log('xmltv: reset')
        self.__init__()


    def importXMLTV(self, file):
        log('xmltv: importXMLTV, file = %s'%file)
        self.xmltvList['channels'].extend(self.getChannels(file)) #todo collision logic?
        self.xmltvList['programmes'].extend(self.getProgrammes(file))
        return True
        
        
    def getChannels(self, file=XMLTVFLE):
        log('xmltv: getChannels, file = %s'%file)
        try: 
            return self.sortChannels(xmltv.read_channels(FileAccess.open(file, 'r')) or [])
        except Exception as e: 
            return []
        
        
    def getProgrammes(self, file=XMLTVFLE):
        log('xmltv: getProgrammes, file = %s'%file)
        try: 
            return self.sortProgrammes(self.cleanProgrammes(xmltv.read_programmes(FileAccess.open(file, 'r')) or []))
        except Exception as e: 
            return []


    def getData(self):
        log('xmltv: getData')
        try: 
            return (xmltv.read_data(FileAccess.open(XMLTVFLE, 'r')) or self.resetData())
        except Exception as e: 
            return self.resetData()


    @use_cache(28)
    def getGenres(self, version=ADDON_VERSION):  #build list of all genre combinations. 
        log('xmltv: getGenres')
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
        log('xmltv: buildGenres')
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
                log('xmltv: getEndtimes, channelid = %s, endtime = %s, epoch = %s'%(channel['id'], stopDate, stopTime))
            except Exception as e: 
                log("getEndtimes, Failed! " + str(e), xbmc.LOGERROR)
                stopTime = now
            endtime[channel['id']] = stopTime
        return endtime
         
         
    def resetData(self):
        log('xmltv: resetData')
        return {'date'                : datetime.datetime.fromtimestamp(float(time.time())).strftime(xmltv.date_format),
                'generator-info-name' : '%s Guidedata'%(ADDON_NAME),
                'generator-info-url'  : ADDON_ID,
                'source-info-name'    : ADDON_NAME,
                'source-info-url'     : ADDON_ID}


    def addChannel(self, item):
        channels = self.xmltvList['channels']
        citem    = ({'id'           : item['id'],
                     'display-name' : [(item['name'], LANG)],
                     'icon'         : [{'src':item['logo']}]})
        log('xmltv: addChannel = %s'%(citem))
        self.xmltvTMP.append(item['id'])
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
                      'credits'     : {'director': [str(item['director'])], 'writer': ['\n\n\n\n\n\n\n\n\n\n\n\n%s'%(dumpJSON(item['writer']))]}, #Hijacked director = dbid, writer = listitem dict.
                      'category'    : [(self.cleanString(genre.replace('Unknown','Undefined')),LANG) for genre in item['categories']],
                      'title'       : [(self.cleanString(item['title']), LANG)],
                      'sub-title'   : [(self.cleanString(item['sub-title']), LANG)],
                      'desc'        : [(self.cleanString(item['desc']), LANG)],
                      'star-rating' : [{'value': self.cleanStar(item['stars'])}],
                      'stop'        : (datetime.datetime.fromtimestamp(float(item['stop'])).strftime(xmltv.date_format)),
                      'start'       : (datetime.datetime.fromtimestamp(float(item['start'])).strftime(xmltv.date_format)),
                      'icon'        : [{'src': item['thumb']}]}

        # if item['date']: #todo fix
            # pitem['date'] = (datetime.datetime.strptime(item['date'], '%Y-%m-%d')).strftime('%Y%m%d'),
            
            
        if item['new']: pitem['new'] = '' #write blank tag, tag == True
        rating = self.cleanMPAA(item['rating'])
        if rating != 'NA' and rating.startswith('TV-'): 
            pitem['rating'] = [{'system': 'VCHIP', 'value': rating}]
        elif rating != 'NA' :  
            pitem['rating'] = [{'system': 'MPAA', 'value': rating}]
            
        if item['episode-num']: 
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
            
        log('xmltv: addProgram = %s'%(pitem))
        programmes.append(pitem)
        self.xmltvList['programmes'] = programmes
        return True


    def cleanStar(self, str1):
        return '%s/10'%(int(round(float(str1))))


    def cleanMPAA(self, str1):
        #todo regex, detect other region rating strings
        try: return str1.split('Rated ')[1]
        except: return str1


    def cleanString(self, str1):
        #todo last stop to clean xmltv strings
        return (str1)
        
        
    def sortChannels(self, channels=None):
        if channels is None: 
            channels = self.xmltvList['channels']
        channels.sort(key=lambda x:x['display-name'])
        log('xmltv: sortChannels, channels = %s'%(len(channels)))
        return channels


    def sortProgrammes(self, programmes=None):
        if programmes is None: 
            programmes = self.xmltvList['programmes']
        programmes.sort(key=lambda x:x['channel'])
        programmes.sort(key=lambda x:x['start'])
        log('xmltv: sortProgrammes, programmes = %s'%(len(programmes)))
        return programmes


    def cleanSelf(self, items, key='id'): # remove imports (Non PseudoTV Live)
        log('xmltv: cleanSelf, key = %s'%(key))
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
        log('xmltv: cleanProgrammes, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
        return tmpProgrammes


    def cleanChannels(self): # remove missing channels from xmltvList
        log('xmltv: cleanChannels')
        # if not self.xmltvTMP: return
        # channels = self.xmltvList['channels'].copy()
        # print(channels, self.xmltvTMP)
        # for item in self.xmltvTMP:
            # for idx, channel in enumerate(channels):
                # if channel['id'] == item:
                    # channels.pop(idx)
        # [self.removeChannel(id) for id in channels]
                                
        
    def removeChannel(self, id): # remove single channel and all programmes from xmltvList
        channels   = self.xmltvList['channels']
        programmes = self.xmltvList['programmes']
        self.xmltvList['channels']   = [channel for channel in channels if channel['id'] != id]
        self.xmltvList['programmes'] = [program for program in programmes if program['channel'] != id]
        log('xmltv: removeChannel, removing channel %s; channels: before = %s, after = %s; programmes: before = %s, after = %s'%(id,len(channels),len(self.xmltvList['channels']),len(programmes),len(self.xmltvList['programmes'])))


    def findChannelIDX(self, item, channels=None): #find existing channel id in xmltvList
        if channels is None: channels = self.xmltvList['channels']
        for idx, channel in enumerate(channels): 
            if channel['id'] == item['id']: 
                return idx
        return None
        
        
    def save(self, reset=True):
        log('xmltv: save')
        self.cleanChannels()
        
        if reset: 
            data = self.resetData()
        else:     
            data = self.xmltvList['data']
            
        if self.extImport: 
            self.importXMLTV(self.extImportXMLTV)
        
        writer = xmltv.Writer(encoding=xmltv.locale, date=data['date'],
                              source_info_url     = data['source-info-url'], 
                              source_info_name    = data['source-info-name'],
                              generator_info_url  = data['generator-info-url'], 
                              generator_info_name = data['generator-info-name'])
               
        channels = self.xmltvList['channels']
        for channel in channels: writer.addChannel(channel)
        programmes = self.sortProgrammes(removeDUPS(self.xmltvList['programmes']))
        for program in programmes: writer.addProgramme(program)
        writer.write(FileAccess.open(XMLTVFLE, "w"), pretty_print=True)
        log('xmltv: save, saving to %s'%(XMLTVFLE))
        self.buildGenres()
        return True
        

    def delete(self):
        log('xmltv: delete')
        if FileAccess.delete(XMLTVFLE):
            FileAccess.delete(GENREFLE)
            notificationDialog(LANGUAGE(30016)%('XMLTV'))


class M3U:
    def __init__(self):
        self.m3uTMP  = []
        self.m3uList = ['#EXTM3U tvg-shift="%s" x-tvg-url="" x-tvg-id="%s"'%(self.getShift(),getuuid())]
        self.m3uList.extend(self.cleanSelf(self.load()))
        self.extImport    = getSettingBool('User_Import')
        self.extImportM3U = getSetting('Import_M3U')


    def getShift(self):
        log('m3u: getShift') #offset list to avoid rebuild starting at the top of the hour, might be useful?
        return ''
        # self.now = datetime.datetime.now()
        # min = str(round(self.now.minute) / 60)[:3]
        # return '-%s'%(min)


    def setClientID(self, line):
        log('m3u: setClientID')
        match = re.compile('x-tvg-id=\"(.*?)\"', re.IGNORECASE).search(line)
        if match: return setSetting('mu3id',match.group(1))


    def reset(self):
        log('m3u: reset')
        self.__init__()
        return True


    def importM3U(self, file):
        log('m3u: importM3U, file = %s'%file)
        self.m3uList.extend(self.load(file)) #todo collision logic?
        return True
        

    def load(self, file=M3UFLE):
        log('m3u: load, file = %s'%file)
        fle = FileAccess.open(file, 'r')
        m3uListTMP = (fle.readlines())
        self.setClientID(m3uListTMP[0])
        fle.close()
        return ['%s\n%s'%(line,m3uListTMP[idx+1]) for idx, line in enumerate(m3uListTMP) if line.startswith('#EXTINF:')]


    def save(self):
        log('m3u: save')
        self.cleanChannels()
        if self.extImport: 
            self.importM3U(self.extImportM3U)
        fle = FileAccess.open(M3UFLE, 'w')
        log('m3u: save, saving to %s'%(M3UFLE))
        fle.write('\n'.join([item for item in self.m3uList]))
        fle.close()
        return True
        

    def add(self, item, radio=False, rebuild=True):
        log('m3u: add item = %s'%(item))
        self.m3uTMP.append(item['id'])
        citem = LINE_ITEM%(item['number'],item['id'],item['name'],item['logo'],';'.join(item['group']),str(radio).lower(),item['label'],item['url'])
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
                log('m3u: findChannelNumber, found %s'%(match.group(1)))
                return match.group(1)
        return None
        
        
    def findChannelID(self, line):
        if line.startswith('#EXTINF:'):
            match = re.compile('tvg-id=\"(.*?)\"', re.IGNORECASE).search(line)
            if match: 
                log('m3u: findChannelID, found %s'%(match.group(1)))
                return match.group(1)
        return None


    def findChannelIDX(self, id='', channels=None, return_line=False):
        if channels is None: channels = self.m3uList
        for idx, line in enumerate(channels):
            lineID = self.findChannelID(line)
            if not lineID: continue
            if lineID == id:
                log('m3u: findChannelIDX, match = %s, idx = %s'%(line, idx))
                if return_line: return line
                return idx
        return None
        
        
    def removeChannel(self, line=None, id=''):
        if line is None: line = self.findChannelIDX(id, return_line=True)
        log('m3u: removeChannel, removing %s'%(line))
        self.m3uList.remove(line)
        return True


    def cleanSelf(self, items): # remove imports (Non PseudoTV Live)
        log('m3u: cleanSelf')
        slugName = slugify(ADDON_NAME)
        for line in items:
            lineID = self.findChannelID(line)
            if not lineID: continue
            if lineID.endswith('@%s'%(slugName)):
                yield line


    def cleanChannels(self): # remove abandoned channels, better method?
        log('m3u: cleanChannels')
        if not self.m3uTMP: return
        channels = self.m3uList.copy()
        channels.pop(0)
        for id in self.m3uTMP:
            line = self.findChannelIDX(id, channels, return_line=True)
            if line: channels.remove(line)
        [self.removeChannel(line) for line in channels]
                
        
    def delete(self):
        log('m3u: delete')
        if FileAccess.delete(M3UFLE): notificationDialog(LANGUAGE(30016)%('M3U'))


class JSONRPC:
    def __init__(self, myWorker=None):
        self.cache         = SimpleCache()
        self.queue         = myWorker
        self.useColor      = USE_COLOR
        self.videoParser   = VideoParser()
        self.resourcePacks = self.buildLogoResources()
        FileAccess.makedirs(LOGO_LOC)
        

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
        self.log('getPlayerItem, playlist = %s'%(playlist))
        if playlist: json_query = '{"jsonrpc":"2.0","method":"Playlist.GetItems","params":{"playlistid":%s,"properties":["runtime","title","plot","genre","year","studio","mpaa","season","episode","showtitle","thumbnail","file"]},"id":1}'%(self.getActivePlaylist())
        else:        json_query = '{"jsonrpc":"2.0","method":"Player.GetItem","params":{"playerid":%s,"properties":["file","writer","channel","channels","channeltype","mediapath"]}, "id": 1}'%(self.getActivePlayer())
        result = sendJSON(json_query).get('result',{})
        return (result.get('item',{}) or result.get('items',{}))
           

    def getPVRChannels(self, radio=False):
        type = 'allradio' if radio else 'alltv'
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetChannels","params":{"channelgroupid":"%s","properties":["icon","channeltype","channelnumber","broadcastnow","broadcastnext"]}, "id": 1}'%(type))
        return sendJSON(json_query).get('result',{}).get('channels',[])


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
                writer = loadJSON(writer)
                if writer['data']['id'] == id:
                    log('matchPVRChannel, match found chname = %s, id = %s'%(chname,id))
                    return item
            except: continue
        return None
        
        
    def fillPVRbroadcasts(self, channelItem):
        log('JSONRPC: fillPVRbroadcasts')
        channelItem['broadcastnext'] = []
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetBroadcasts","params":{"channelid":%s,"properties":["title","plot","starttime","runtime","progress","progresspercentage","episodename","writer","director"]}, "id": 1}'%(channelItem['channelid']))
        json_response = (sendJSON(json_query)).get('result',{}).get('broadcasts',[])
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
            broadcastnext = channelItem['broadcastnext']
            channelItem['broadcastnext'] = [broadcastnext]
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
        [genres.extend(re.split(';|/|,',genre)) for song in json_response for genre in song.get('genre',[])]
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
        if not sort and path.startswith('videodb://movies'): sort = {"method": "random"}
            
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
        
        
    @use_cache(1)
    def listVFS(self, path, version=None):
        log('jsonrpc, listVFS path = %s, version = %s'%(path,version))
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","properties":["duration","runtime"]},"id":1}'%(path))
        json_response = (sendJSON(json_query)).get('result',{}).get('files',[])
        dirs, files = [[],[]]
        for item in json_response:
            file = item['file']
            if item['filetype'] == 'file':
                self.parseDuration(file, item)
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
        if STORE_DURATION and (runtime != duration and duration > 0) and dbid > 0:
            self.setDuration(item['type'], dbid, duration)
        log("jsonrpc, parseDuration, path = %s, duration = %s"%(path,duration))
        return duration
        

    def setDuration(self, media, dbid, dur):
        log('setDuration, media = %s, dbid = %s, dur = %s'%(media, dbid, dur))
        if media == 'movie': 
            self.queue.add((sendJSON,('{"jsonrpc": "2.0", "method":"VideoLibrary.SetMovieDetails"  ,"params":{"movieid"   : %i, "runtime" : %i }, "id": 1}'%(dbid,dur))))
        elif media == 'episode': 
            self.queue.add((sendJSON,('{"jsonrpc": "2.0", "method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid" : %i, "runtime" : %i }, "id": 1}'%(dbid,dur))))
     
    
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
        if self.useColor: studios.reverse()
        [logos.append({'type':['MUSIC Genres'],'path':radio,'files': self.getResourcesFolders(radio, self.getPluginMeta(radio).get('version',''))[1]}) for radio in radios]
        [logos.append({'type':['TV Genres','MOVIE Genres','MIXED Genres','Custom'],'path':genre,'files': self.getResourcesFolders(genre, self.getPluginMeta(genre).get('version',''))[1]}) for genre  in genres]
        [logos.append({'type':['TV Networks','MOVIE Studios','Custom'],'path':studio,'files': self.getResourcesFolders(studio, self.getPluginMeta(studio).get('version',''))[1]}) for studio in studios]
        logos.append( {'type':['TV Shows'],'path':'','files': self.fillTVShows()})
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


    @use_cache(1)
    def findLogo(self, channelname, channeltype, useColor, featured=False, version=ADDON_VERSION):
        log('findLogo')
        for item in self.resourcePacks:
            if channeltype in item['type']:
                for file in item['files']:
                    if isinstance(file, dict):
                        fileItem = file.get('item',{})
                        if channelname.lower() == fileItem.get('label','').lower(): 
                            return self.cacheImage(channelname,fileItem.get('art',{}).get('clearlogo',''),featured)
                    else:
                        if file.lower().startswith(channelname.lower()): 
                            return self.cacheImage(channelname,os.path.join(item['path'],file),featured)
        return LOGO
        
        
    def cacheImage(self, channelname, logo, featured): #copy image to users logo folder. #todo translate .xbt resource:// to github urls? 
        if featured:
            log('cacheImage: channelname = %s, featured = %s'%(channelname,featured))
            localIcon = os.path.join(LOGO_LOC,'%s.png'%(channelname))
            if logo.startswith('resource://'): return logo #todo parse xbt and extract image?
            # if FileAccess.copy(logo, localIcon): return localIcon
        return logo
        
        
    def getLogo(self, channelname, type, path=None, featured=False):
        log('getLogo: channelname = %s, type = %s'%(channelname,type))
        icon = LOGO
        localIcon = os.path.join(LOGO_LOC,'%s.png'%(channelname))
        if FileAccess.exists(localIcon): 
            log('getLogo: using local logo = %s'%(localIcon))
            return localIcon
        elif type in ['TV Shows','TV Networks','MOVIE Studios','TV Genres','MOVIE Genres','MIXED Genres','MUSIC Genres','Custom']: 
            icon = (self.findLogo(channelname, type, self.useColor, featured) or LOGO)
        log('getLogo: icon = %s'%(icon))
        if icon in [None,LOGO] and path:
            if isinstance(path, list): path = path[0]
            if path.startswith('plugin://'): icon = self.getPluginMeta(path).get('icon',None)
        if icon is None: icon = LOGO #last check to make sure a default logo is set; unneeded...
        if icon.startswith(ADDON_PATH):
            icon = icon.replace(ADDON_PATH,'special://home/addons/%s/'%(ADDON_ID))
        log('getLogo, channelname = %s, logo = %s'%(channelname,icon))
        return icon