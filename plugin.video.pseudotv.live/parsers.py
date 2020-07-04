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

import xmltv

from globals import *
from resources.lib import VideoParser
from resources.lib.FileAccess import FileAccess

xmltv.locale = 'UTF-8'
xmltv.date_format = DTFORMAT

class Channels:
    def __init__(self):
        self.channels = []#self.getChannels()
        
        
    def reset(self):
        log('channels: reset')
        self.__init__()
        return True

        
    def add(self, item):
        log('channels: add, item = %s'%(item))


    def getChannels(self, channels=CHANNELFLE):
        log('channels: getChannels')
        if not FileAccess.exists(channels): channels = CHANNELFLE_DEFAULT
        return json.load(channels)

        
    def save(self):
        if not FileAccess.makedirs(os.path.dirname(CHANNELFLE)): 
            return False


class XMLTV:
    def __init__(self):
        self.newChannels = []
        self.maxDays     = getSettingInt('Max_Days')
        self.xmltvList   = {'data'       : self.getData(),
                            'channels'   : self.cleanSelf(self.getChannels(),'id'),
                            'programmes' : self.cleanSelf(self.getProgrammes(),'channel')}
        self.xmltvList['endtimes'] = self.getEndtimes()
        self.oldChannels = self.xmltvList['channels'].copy()
        
        
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
            log("xmltv: getChannels, Failed! " + str(e), xbmc.LOGERROR)
            return []
        
        
    def getProgrammes(self, file=XMLTVFLE):
        log('xmltv: getProgrammes, file = %s'%file)
        try: 
            return self.sortProgrammes(self.cleanProgrammes(xmltv.read_programmes(FileAccess.open(file, 'r')) or []))
        except Exception as e: 
            log("xmltv: getProgrammes, Failed! " + str(e), xbmc.LOGERROR)
            return []


    def getData(self):
        log('xmltv: getData')
        try: 
            return (xmltv.read_data(FileAccess.open(XMLTVFLE, 'r')) or self.resetData())
        except Exception as e: 
            return self.resetData()


    def buildGenres(self): #build list of all genre combinations. 
        log('xmltv: buildGenres')
        programmes = self.xmltvList['programmes']
        genres = []
        # [genres.append(' / '.join(genre[0] for genre in program['category'])) for program in programmes]
        [genres.extend(genre for genre in program['category']) for program in programmes]
        try:
            epggenres = {}
            xml   = FileAccess.open(GENREFLE_DEFAULT, "r")
            dom   = parse(xml)
            lines = dom.getElementsByTagName('genre')
            for line in lines: 
                items = line.childNodes[0].data.split(' / ')
                for item in items: epggenres[item] = line.attributes['genreId'].value
            xml.close()
            
            #todo faster method?
            doc  = Document()
            root = doc.createElement('genres')
            doc.appendChild(root)
            
            name = doc.createElement('name')
            name.appendChild(doc.createTextNode('%s Genres using Hexadecimal for genreId'%(ADDON_NAME)))           
            root.appendChild(name)
            
            # def sort():
                # for key in matches: yield {key:epggenres[key]}
                
            genres    = list(set(genres))
            matches   = set(x[0] for x in genres)&set(x for x in epggenres)
            # matches   = list(sort())
            
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
        now        = rollbackTime(getLocalTime())
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
        
        channelIDX = self.findChannelIDX(citem, channels)
        if channelIDX is None: 
            channels.append(citem)
        else: 
            channels[channelIDX] = citem # update existing channel meta
        self.newChannels.append(citem)
        self.xmltvList['channels'] = channels
        return True


    def addProgram(self, id, item):
        programmes = self.xmltvList['programmes']
        pitem      = {'channel'     : id,
                      'new'         : item['new'],
                      'credits'     : {'director': [str(item['director'])], 'writer': [dumpJSON(item['writer'])]}, #Hijacked director = dbid, writer = listitem dict.
                      'category'    : [(self.cleanString(genre.replace('Unknown','Undefined')),LANG) for genre in item['categories']],
                      'title'       : [(self.cleanString(item['title']), LANG)],
                      'sub-title'   : [(self.cleanString(item['sub-title']), LANG)],
                      'desc'        : [(self.cleanString(item['desc']), LANG)],
                      'star-rating' : [{'value': self.cleanStar(item['stars'])}],
                      'date'        : datetime.datetime.fromtimestamp(float(item['start'])).strftime('%Y%m%d'),
                      'stop'        : datetime.datetime.fromtimestamp(float(item['stop'])).strftime(xmltv.date_format),
                      'start'       : datetime.datetime.fromtimestamp(float(item['start'])).strftime(xmltv.date_format),
                      'icon'        : [{'src': item['thumb']}]}
            
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
        slugName = slugify(ADDON_NAME)
        tmpitems = [item for item in items if item[key].endswith('@%s'%(slugName))]
        log('xmltv: cleanSelf, before = %s, after = %s, key = %s'%(len(items),len(tmpitems),key))
        return tmpitems
        
        
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


    def cleanChannels(self, channels=None): # remove missing and non PseudoTV Live channels from xmltvList
        if channels is None: channels = self.xmltvList['channels']
        # diffChannels = diffDICT(self.newChannels,self.oldChannels)
        # if len(diffChannels) > 0 and not assertDICT(diffChannels, channels):
            # [self.removeChannel(diff['id']) for diff in diffChannels if (self.findChannelIDX(diff['id'],self.oldChannels) is not None and self.findChannelIDX(diff['id'],self.newChannels) is None)]
        log('xmltv: cleanChannels, before = %s, after = %s'%(len(channels),len(self.xmltvList['channels'])))
        

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
        # self.cleanChannels()
        
        if reset: 
            data = self.resetData()
        else:     
            data = self.xmltvList['data']
            
        if EXT_IMPORT: 
            self.importXMLTV(EXT_IMPORT_XMLTV)
        
        writer = xmltv.Writer(encoding=xmltv.locale, date=data['date'],
                              source_info_url=data['source-info-url'], source_info_name=data['source-info-name'],
                              generator_info_url=data['generator-info-url'], generator_info_name=data['generator-info-name'])
               
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
        self.m3uNEW  = []
        self.m3uList = ['#EXTM3U tvg-shift="%s" x-tvg-url=""'%(self.getShift())]
        self.m3uList.extend(self.cleanSelf(self.load()))
        self.m3uOLD  = self.m3uList.copy()


    def getShift(self):
        log('m3u: getShift') #offset list to avoid rebuild starting at the top of the hour, might be useful?
        return ''
        # self.now = datetime.datetime.now()
        # min = str(round(self.now.minute) / 60)[:3]
        # return '-%s'%(min)


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
        m3uListTMP = (fle.read()).split('\n')
        fle.close()
        return ['%s\n%s'%(line,m3uListTMP[idx+1]) for idx, line in enumerate(m3uListTMP) if line.startswith('#EXTINF:')]


    def save(self):
        log('m3u: save')
        # if not FileAccess.makedirs(os.path.dirname(M3UFLE)): 
            # return False
            
        # self.cleanChannels()
        if EXT_IMPORT: 
            self.importM3U(EXT_IMPORT_M3U)
        fle = FileAccess.open(M3UFLE, 'w')
        log('m3u: save, saving to %s'%(M3UFLE))
        fle.write('\n'.join([str(item) for item in self.m3uList]))
        fle.close()
        return True


    def add(self, item):
        match = self.findChannel(item['id'])
        if match: 
            self.removeChannel(item['id'], match) # update existing channel by removing old one.
        log('m3u: add item = %s'%(item))
        citem = '#EXTINF:0 tvg-chno=%s tvg-id="%s" tvg-name="%s" tvg-logo="%s" group-title="%s",%s\n%s'%(item['number'],item['id'],item['name'],item['logo'],';'.join(item['group']),item['label'],item['url'])
        self.m3uList.append(citem)
        self.m3uNEW.append(citem)
        return True
        

    def findChannel(self, id, lst=None):
        if lst is None: lst = self.m3uList
        for line in lst:
            if line.startswith('#EXTINF:'):
                match = re.compile('tvg-id=\"(.*?)\"', re.IGNORECASE).search(line)
                if not match: continue
                if match.group(1) == id:
                    log('m3u: findChannel, match = %s'%(line))
                    return line
        return None
        
        
    def removeChannel(self, id, line=None):
        if line is None: line = self.findChannel(id)
        log('m3u: removeChannel, removing %s'%(line))
        self.m3uList.remove(line)
        return True


    def cleanSelf(self, items): # remove imports (Non PseudoTV Live)
        slugName = slugify(ADDON_NAME)
        tmpitems = []
        for line in items:
            if line.startswith('#EXTINF:'):
                match = re.compile('tvg-id=\"(.*?)\"', re.IGNORECASE).search(line)
                if not match: continue
                id = match.group(1)
                if id.endswith('@%s'%(slugName)):
                    tmpitems.append(line)
        log('m3u: cleanSelf, before = %s, after = %s'%(len(items),len(tmpitems)))
        return tmpitems


    def cleanChannels(self): # remove abandoned channels
        log('m3u: cleanChannels')
        # channels = self.m3uList
        # diffChannels = diffLST(self.m3uNEW,self.m3uOLD)
        # if len(diffChannels) > 0 and not assertLST(diffChannels, channels):
            # [self.removeChannel(diff['id']) for diff in diffChannels if (self.findChannel(diff['id'],self.m3uOLD) is not None and self.findChannel(diff['id'],self.m3uNEW) is None)]
        # log('m3u: cleanChannels, before = %s, after = %s'%(len(channels),len(self.m3uList)))
        

    def delete(self):
        log('m3u: delete')
        if FileAccess.delete(M3UFLE): notificationDialog(LANGUAGE(30016)%('M3U'))


class JSONRPC:
    def __init__(self):
        self.cache = SimpleCache()
        self.pageLimit     = getSettingInt('Page_Limit')
        self.useColor      = getSettingBool('Use_Color_Logos')
        self.videoParser   = VideoParser.VideoParser()
        self.resourcePacks = self.buildResources()
        FileAccess.makedirs(LOGO_LOC)


    def getPVRChannels(self):
        json_query = ('{"jsonrpc":"2.0","method":"PVR.GetChannels","params":{"channelgroupid":"alltv","properties":["icon","channeltype","channelnumber","broadcastnow","broadcastnext"]}, "id": 1}')
        return sendJSON(json_query).get('result',{}).get('channels',[])


    def matchPVRPath(self, channelid=None):
        if channelid is None: return ''
        log('JSONRPC: matchPVRPath, channelid = %s'%(channelid))
        json_query = ('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"pvr://channels/tv/All channels/","properties":["file"]},"id":1}')
        json_response = self.cacheJSON(json_query).get('result',{}).get('files',[])
        try: 
            path = [path['file'] for path in json_response if channelid == path['id']][0]
            log('JSONRPC: matchPVRPath, found path = %s'%(path))
            return path
        except Exception as e: 
            log("JSONRPC: matchPVRPath, Failed! " + str(e), xbmc.LOGERROR)
            return ''
        

    def matchPVRChannel(self, chname, id): # Convert PseudoTV Live channelID into a Kodi channelID for playback
        channels = self.getPVRChannels()
        for item in channels:
            writer = loadJSON(item.get('broadcastnow',{}).get('writer',''))
            if not writer: continue #filter other PVR backends; currently NO API support.
            try: 
                if writer['data']['id'] == id:
                    log('matchPVRChannel, match found chname = %s, id = %s'%(chname,id))
                    return item
            except: continue
        return None
        
        
    def getPVRposition(self, chname, id, isPlaylist=False): # Current PVR Position data
        log('JSONRPC: getPVRposition, chname = %s, id = %s, isPlaylist = %s'%(chname,id,isPlaylist))
        channelItem = self.matchPVRChannel(chname, id)
        if not channelItem: return {}
        if isPlaylist:
            channelItem['broadcastnext'] = []
            json_query = ('{"jsonrpc":"2.0","method":"PVR.GetBroadcasts","params":{"channelid":%s,"properties":["title","plot","starttime","runtime","progress","progresspercentage","episodename","writer","director"]}, "id": 1}'%(channelItem['channelid']))
            json_response = (sendJSON(json_query)).get('result',{}).get('broadcasts',[])
            
            for idx, item in enumerate(json_response):
                if item['progresspercentage'] == 100.0: continue
                elif item['progresspercentage'] > 0.0: 
                    broadcastnow = channelItem['broadcastnow']
                    channelItem.pop('broadcastnow')
                    item.update(broadcastnow) 
                    channelItem['broadcastnow'] = item
                elif item['progresspercentage'] == 0.0: 
                    channelItem['broadcastnext'].append(item)
        else: 
            broadcastnext = channelItem['broadcastnext']
            channelItem['broadcastnext'] = [broadcastnext]
        return channelItem


    def cacheJSON(self, command, life=datetime.timedelta(minutes=15)):
        cacheName = '%s.cacheJSON.%s'%(ADDON_ID,command)
        cacheResponse = self.cache.get(cacheName)
        if cacheResponse is None:
            cacheResponse = sendJSON(command)
            self.cache.set(cacheName, cacheResponse, checksum=len(cacheResponse), expiration=life)
        return cacheResponse


    def fillTVShows(self):
        tvshows = []
        if not hasTV(): return tvshows
        json_query = ('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","params":{"properties":["title","genre","year","rating","plot","studio","mpaa","cast","playcount","episode","imdbnumber","premiered","votes","lastplayed","fanart","thumbnail","file","originaltitle","sorttitle","episodeguide","season","watchedepisodes","dateadded","tag","art","userrating","ratings","runtime","uniqueid"]}, "id": 1}')
        json_response = (self.cacheJSON(json_query)).get('result',{}).get('tvshows',[])
        for item in json_response: tvshows.append({'label':item['label'],'item':item,'thumb':item['thumbnail']})
        log('jsonrpc, fillTVShows, found = %s'%(len(tvshows)))
        return tvshows


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


    def requestList(self, id, path, media='video', page={}, sort={}, filter={}, limits={}):
        if not page: page = self.pageLimit
        if not sort and path.startswith('videodb://movies'): 
            sort = {"method": "random"}
            
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
        log("jsonrpc: requestList return, items size = %s"%len(items))
        return items
        
        
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
            try: duration = self.videoParser.getVideoLength(path.replace("\\\\", "\\"))
            except Exception as e: 
                log("parseDuration, Failed! " + str(e), xbmc.LOGERROR)
                duration = 0
            self.cache.set(cacheName, duration, checksum=duration, expiration=datetime.timedelta(days=28))
        dbid    = item.get('id',-1)
        runtime = int(item.get('runtime','') or item.get('duration','0') or '0')
        if STORE_DURATION and (runtime != duration and duration > 0) and dbid > 0: self.setDuration(item['type'], dbid, duration)
        log("jsonrpc, parseDuration, path = %s, duration = %s"%(path,duration))
        return duration
        

    def setDuration(self, media, dbid, dur):
        log('setDuration, media = %s, dbid = %s, dur = %s'%(media, dbid, dur))
        # todo create thread queue, use join
        # if media == 'movie': sendJSON('{"jsonrpc": "2.0", "method":"VideoLibrary.SetMovieDetails"  ,"params":{"movieid"   : %i, "runtime" : %i }, "id": 1}'%(dbid,dur))
        # elif media == 'episode': sendJSON('{"jsonrpc": "2.0", "method":"VideoLibrary.SetEpisodeDetails","params":{"episodeid" : %i, "runtime" : %i }, "id": 1}'%(dbid,dur))
        
            
    def buildResources(self):
        log('jsonrpc, buildResources')
        logos     = []
        genres    = ["resource://resource.images.moviegenreicons.transparent"]
        studios   = ["resource://resource.images.studios.white/", "resource://resource.images.studios.coloured/"]
        if self.useColor: studios.reverse()
        [logos.append({'type':['TV Genres','MOVIE Genres','MIXED Genres'],'path':genre,'files': self.getFolderFiles(genre)[1]}) for genre  in genres]
        [logos.append({'type':['TV Networks','MOVIE Studios'],'path':studio,'files': self.getFolderFiles(studio)[1]}) for studio in studios]
        logos.append( {'type':['TV Shows'],'path':'','files': list(self.fillTVShows())})
        log('jsonrpc, buildResources return')
        return logos


    @use_cache(1)
    def getPluginMeta(plugin):
        log('getPluginMeta: plugin = %s'%(plugin))
        if '?' in plugin: plugin = plugin.split('?')[0]
        if plugin[0:9] == 'plugin://':
            plugin = plugin.replace("plugin://","")
            plugin = splitall(plugin)[0]
        else: plugin = plugin
        pluginID = xbmcaddon.Addon(plugin)
        return {'label':pluginID.getAddonInfo('name'), 'label':pluginID.getAddonInfo('path'), 'author':pluginID.getAddonInfo('author'), 'icon':pluginID.getAddonInfo('icon'), 'fanart':pluginID.getAddonInfo('fanart'), 'id':pluginID.getAddonInfo('id'), 'plot':(pluginID.getAddonInfo('description') or pluginID.getAddonInfo('summary'))}


    @use_cache(7)
    def getFolderFiles(self, path):
        log('jsonrpc, getFolderFiles path = %s'%(path))
        try: 
            return FileAccess.listdir(path)
        except: 
            return [],[]


    @use_cache(1)
    def findLogo(self, channelname, channeltype, useColor, featured=False):
        log('findLogo')
        for item in self.resourcePacks:
            if channeltype in item['type']:
                for file in item['files']:
                    if isinstance(file, dict):
                        fileItem = file.get('item',{})
                        if channelname.lower() == fileItem.get('label','').lower(): 
                            return self.cacheImage(channelname,fileItem.get('art',{}).get('clearlogo',''),featured)
                    else:
                        if file.lower() == '%s.png'%(channelname.lower()): 
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
        if FileAccess.exists(localIcon): return localIcon
        elif type in ['TV Shows','TV Networks','MOVIE Studios','TV Genres','MOVIE Genres','MIXED Genres']: 
            icon = (self.findLogo(channelname, type, self.useColor, featured) or LOGO)
        else:
            if isinstance(path, list): path = path[0]
            if path.startswith('plugin://'): icon = self.getPluginMeta(path).get('icon',None)
        log('getLogo, channelname = %s, logo = %s'%(channelname,icon))
        return icon