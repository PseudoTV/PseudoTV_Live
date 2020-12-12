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
from resources.lib.fileaccess  import FileLock

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
    def __init__(self, cache=None):
        log('Writer: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.m3u           = M3U(self.cache)
        self.xmltv         = XMLTV(self.cache)
        self.channels      = Channels(self.cache)
        self.importEnabled = getSettingBool('User_Import')
        
        try:
            self.dialog   = self.builder.dialog
            self.progress = self.builder.progress
            self.chanName = self.builder.chanName
        except:
            self.dialog   = None
            self.progress = 0
            self.chanName = ''
        # if self.channels.isClient: self.syncCustom()
        
        
    def reset(self):
        log('Writer: reset')
        if self.xmltv.reset() and self.m3u.reset(): return True
        return False
        
        
    def getEndtime(self, id, fallback):
        log('Writer: getEndtime, id = %s'%(id))
        return (self.xmltv.getEndtimes().get(id,'') or fallback)
        
        
    def delete(self, full=False):
        log('Writer: delete')
        if full: self.deleteSettings()
        if False in [func() for func in [self.m3u.delete,self.xmltv.delete,self.channels.delete]]:
            return False
        return True
        

    def deleteSettings(self):
        log('Writer: deleteSettings')
        if FileAccess.delete(SETTINGS_FLE):
            return notificationDialog(LANGUAGE(30016)%('SETTINGS'))
        return False
        
        
    def save(self):
        log('Writer: save')
        if self.cleanChannels(): 
            self.importSETS()
            if self.xmltv.save() and self.m3u.save():
                if self.dialog is not None:
                    self.dialog = ProgressBGDialog(self.progress, self.dialog, message=LANGUAGE(30152))
                return True
        return False
        
        
    def importSETS(self):
        log('Writer: importSETS')
        importLST = self.channels.getImports()
        if self.importEnabled: 
            importLST.append({'type':'iptv','name':'User M3U/XMLTV','m3u':getSetting('Import_M3U'),'xmltv':getSetting('Import_XMLTV')})
        for importItem in importLST:
            try:
                if importItem.get('type','') == 'iptv':
                    if self.dialog is not None:
                        self.dialog = ProgressBGDialog(self.progress, self.dialog, message='%s: %s'%(LANGUAGE(30151),importItem.get('name','')))
                    self.m3u.importM3U(importItem.get('m3u',''))
                    self.xmltv.importXMLTV(importItem.get('xmltv',{}).get('path',''))
            except Exception as e: log("Writer: importSETS, Failed! " + str(e), xbmc.LOGERROR)
        return True
        
        
    def addChannel(self, citem, radio=False, catchup=True):
        log('Writer: addChannel, citem = %s, radio = %s, catchup = %s'%(citem,radio,catchup))
        self.m3u.addChannel(citem)
        self.xmltv.addChannel(citem)
    
    
    def removeChannel(self, citem):
        log('Writer: removeChannel, citem = %s'%(citem))
        self.m3u.removeChannel(citem.get('id',''))
        self.xmltv.removeChannel(citem.get('id',''))
    
    
    def addProgrammes(self, citem, fileList, radio=False, catchup=True):
        log('Writer: addProgrammes, radio = %s, catchup = %s, programmes = %s, citem = %s'%(radio,catchup,len(fileList),citem))
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
            
            
    def cleanChannels(self): # remove abandoned/missing channels
        log('Writer: cleanChannels')
        channels = self.channels.getAllChannels()
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

        
    def syncCustom(self): #todo sync user created smartplaylists/nodes for multi-room.
        for type in ['library','playlists']:
            for media in ['video','music','mixed']:
                path  = 'special://userdata/%s/%s/'%(type,media)
                files = FileAccess.listdir(path)[1]
                for file in files:
                    orgpath  = os.path.join(path,file)
                    copypath = os.path.join(PLS_LOC,type,media,file)
                    log('parser: copyNodes, orgpath = %s, copypath = %s'%(orgpath,copypath))
                    yield FileAccess.copy(orgpath, copypath)


class Channels:
    def __init__(self, cache=None):
        log('Channels: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache

        self.channelList = {}
        self.channelList = self.getTemplate(ADDON_VERSION)
        self.channelList.update(self.load())
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
            if isClient: setClient('true')
            else: setClient('false')
        log('Channels: chkClient, isClient = %s'%(isClient))
        return isClient


    def getChannels(self):
        log('Channels: getChannels')
        return sorted(self.channelList.get('channels',[]), key=lambda k: k['number'])


    def getPredefinedChannels(self):
        log('Channels: getPredefinedChannels')
        return sorted(self.channelList.get('predefined',{}).get('channels',[]), key=lambda k: k['number'])
        

    def getAllChannels(self):
        log('Channels: getAllChannels')
        channels = self.getChannels()
        channels.extend(self.getPredefinedChannels())
        return channels
     
                 
    def setPredefinedChannels(self, channels):
        log('Channels: setPredefinedChannels, channels = %s'%(len(channels)))
        self.channelList['predefined']['channels'] = sorted(channels, key=lambda k: k['number'])
        return self.save()
        

    def getPredefinedItems(self, type):
        log('Channels: getPredefinedItems, type = %s'%(type))
        return sorted(self.channelList.get('predefined',{}).get('items',{}).get(type,[]), key=lambda k: k['name'])

        
    def setPredefinedItems(self, type, items=[]):
        log('Channels: setPredefinedItems, type = %s, items = %s'%(type,len(items)))
        self.channelList['predefined']['items'][type] = sorted(items, key=lambda k: k['name'])
        return self.save()
        
        
    def getRecommended(self):
        log('Channels: getRecommended')
        return self.channelList.get('recommended',{})
 
 
    def setRecommended(self, items={}):
        log('Channels: setRecommended, items = %s'%(len(items)))
        self.channelList['recommended'] = items
        return self.save()
 
 
    def getImports(self):
        log('Channels: getImports')
        return sorted(self.channelList.get('recommended',{}).get('imports',[]), key=lambda k: k['name'])
    
    
    def setImports(self, imports):
        log('Channels: setImports, imports = %s'%(imports))
        self.channelList['recommended']['imports'] = sorted(imports, key=lambda k: k['name'])
        return self.save()


    def getPage(self, id):
        page = {"end": 0, "start": 0, "total": 0}
        idx, citem = self.findChannel({'id':id}, self.getAllChannels())
        if idx is not None: page = citem.get('page',page)
        log('Channels: getPage, id = %s, page = %s'%(id, page))
        return page


    def setPage(self, id, page={}):
        log('Channels: setPage, id = %s, page = %s'%(id, page))
        idx, citem = self.findChannel({'id':id}, self.getAllChannels())
        if idx is not None:
            if citem['number'] > CHANNEL_LIMIT:
                channels = self.getPredefinedChannels()
            else:
                channels = self.getChannels()
            idx, citem = self.findChannel(citem, channels)
            self.channelList[idx]['page'] = page
            
            
    def getChannelRules(self, citem, channels=None):
        log('Channels: getChannelRules, id = %s'%(citem['id']))
        if channels is None: channels = self.getChannels()
        idx, channel = self.findChannel(citem, channels)
        if idx is not None: return channel.get('rules',[])
        return []
            
            
    def add(self, citem, channels=None):
        if channels is None: channels = self.getChannels()
        log('Channels: add, item = %s'%(citem))
        idx, channel = self.findChannel(citem, channels)
        if idx is not None:
            citem["number"] = channels[idx]["number"] # existing id found, reuse channel number.
            log('Channels: Updating channel %s, id %s'%(citem["number"],citem["id"]))
            channels[idx] = citem
        else:
            log('Channels: Adding channel %s, id %s'%(citem["number"],citem["id"]))
            channels.append(citem)
        self.channelList['channels'] = sorted(channels, key=lambda k: k['number'])
        return True
        
        
    def remove(self, citem, channels=None):
        if channels is None: channels = self.getChannels()
        log('Channels: removing item = %s'%(citem))
        idx, channel = self.findChannel(citem, channels)
        if idx is not None: channels.pop(idx)
        self.channelList['channels'] = channels
        return True
        
        
    def findChannel(self, citem, channels=None):
        if channels is None: channels = self.getChannels()
        for idx, channel in enumerate(channels):
            if (citem["id"] == channel["id"]):
                log('Channels: findChannel, item = %s, found = %s'%(citem,channel))
                return idx, channel
        return None, {}
        
        
    # @use_cache(7)
    def getTemplate(self, version=ADDON_VERSION):
        log('Channels: getTemplate')
        data = (self.load(CHANNELFLE_DEFAULT) or {})
        data['uuid'] = self.getUUID()
        return data


    def getCitem(self):
        log('Channels: getCitem')
        return self.getTemplate(ADDON_VERSION).get('channels',[])[0].copy()
       

    def load(self, file=CHANNELFLE):
        log('Channels: load file = %s'%(file))
        if not FileAccess.exists(file): 
            file = CHANNELFLE_DEFAULT
        fle  = FileAccess.open(file, 'r')
        data = (loadJSON(fle.read()) or {})
        fle.close()
        return data
        

    def cleanSelf(self):
        channels = self.getChannels()
        self.channelList['channels'] = [citem for citem in channels if citem['number'] > 0]
        

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


class XMLTV:
    def __init__(self, cache=None):
        log('XMLTV: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.maxDays        = getSettingInt('Max_Days')
        self.xmltvList      = {'data'       : self.loadData(),
                               'channels'   : self.sortChannels(self.cleanSelf(self.loadChannels(),'id')),
                               'programmes' : self.sortProgrammes(self.cleanSelf(self.loadProgrammes(),'channel'))}


    def reset(self):
        log('XMLTV: reset')
        self.__init__()
        return True


    def getChannels(self):
        log('XMLTV: getChannels')
        return self.xmltvList.get('channels',[])


    def importXMLTV(self, file):
        if not file: return False
        log('XMLTV: importXMLTV, file = %s'%file)
        if file.startswith('http'):
            url  = file
            file = os.path.join(TEMP_LOC,slugify(url),'.xml')
            saveURL(url,file)
        self.xmltvList['channels'].extend(self.loadChannels(file)) #todo collision logic?
        self.xmltvList['programmes'].extend(self.loadProgrammes(file))
        return True

        
    def loadChannels(self, file=XMLTVFLE):
        log('XMLTV: loadChannels, file = %s'%file)
        try:
            return self.sortChannels(xmltv.read_channels(FileAccess.open(file, 'r')) or [])
        except Exception as e:
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            log('XMLTV: loadChannels, failed! %s'%(e))
            return []
        
        
    def loadProgrammes(self, file=XMLTVFLE):
        log('XMLTV: loadProgrammes, file = %s'%file)
        try: 
            return self.sortProgrammes(self.cleanProgrammes(xmltv.read_programmes(FileAccess.open(file, 'r')) or []))
        except Exception as e: 
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            log('XMLTV: loadProgrammes, failed! %s'%(e))
            return []


    def loadData(self):
        log('XMLTV: loadData')
        try: 
            return (xmltv.read_data(FileAccess.open(XMLTVFLE, 'r')) or self.resetData())
        except Exception as e: 
            log('XMLTV: loadData, failed! %s'%(e))
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
        
        
    def buildGenres(self): #todo fix genre list to start with default, append custom!
        log('XMLTV: buildGenres')
        try:
            epggenres  = self.getGenres(ADDON_VERSION)
            programmes = self.xmltvList['programmes']
            genres     = []
            [genres.extend(genre for genre in program['category']) for program in programmes]
            
            doc  = Document()
            root = doc.createElement('genres')
            doc.appendChild(root)
            
            name = doc.createElement('name')
            name.appendChild(doc.createTextNode('%s Genres using Hexadecimal for genreId'%(ADDON_NAME)))
            root.appendChild(name)
            
            genres  = list(set(genres))
            matches = epggenres #build all
            # matches = set(x[0] for x in genres)&set(x for x in epggenres)
            
            for key in matches:
                gen = doc.createElement('genre')
                gen.setAttribute('genreId',epggenres[key])
                gen.appendChild(doc.createTextNode(key))
                root.appendChild(gen)
            
            xmlData = FileAccess.open(GENREFLE, "w")
            xmlData.write(doc.toprettyxml(indent='\t'))
            xmlData.close()
        except Exception as e: log("xmltv: buildGenres, Failed! " + str(e), xbmc.LOGERROR)
        return True


    def getEndtimes(self, channels=None, programmes=None): # get "Endtime" channels last stopDate in programmes
        endtime = {}
        if channels is None:    channels   = self.sortChannels(self.xmltvList['channels'])
        if programmes is None:  programmes = self.sortProgrammes(self.xmltvList['programmes'])
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
        return {'date'                : datetime.datetime.fromtimestamp(float(time.time())).strftime(xmltv.date_format),
                'generator-info-name' : self.cleanString('%s Guidedata'%(ADDON_NAME)),
                'generator-info-url'  : self.cleanString(ADDON_ID),
                'source-info-name'    : self.cleanString(ADDON_NAME),
                'source-info-url'     : self.cleanString(ADDON_ID)}


    def addChannel(self, item):
        channels = self.xmltvList['channels'].copy()
        citem    = ({'id'           : item['id'],
                     'display-name' : [(self.cleanString(item['name']), LANG)],
                     'icon'         : [{'src':item['logo']}]})
        log('XMLTV: addChannel = %s'%(citem))
        idx, channel = self.findChannel(citem, channels)
        if idx is None: channels.append(citem)
        else: channels[idx] = citem # update existing channel meta
        self.xmltvList['channels'] = channels
        return True


    def addProgram(self, id, item):
        programmes = self.xmltvList['programmes'].copy()
        pitem      = {'channel'     : id,
                      'credits'     : {'writer':['%s [COLOR item="%s"][/COLOR]'%(self.cleanString(item['writer']),encodeString(dumpJSON(item['fitem'])))]},
                      'category'    : [(self.cleanString(genre.replace('Unknown','Undefined')),LANG) for genre in item['categories']],
                      'title'       : [(self.cleanString(item['title']), LANG)],
                      'desc'        : [(self.cleanString(item['desc']), LANG)],
                      'star-rating' : [{'value': self.cleanStar(item['stars'])}],
                      'stop'        : (datetime.datetime.fromtimestamp(float(item['stop'])).strftime(xmltv.date_format)),
                      'start'       : (datetime.datetime.fromtimestamp(float(item['start'])).strftime(xmltv.date_format)),
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
        if rating != 'NA' and rating.startswith('TV-'): 
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
        if text == ',' or not text: text = LANGUAGE(30161)
        return re.sub(u'[^\n\r\t\x20-\x7f]+',u'',text)
        
        
    def sortChannels(self, channels=None):
        if channels is None: channels = self.xmltvList['channels']
        channels.sort(key=lambda x:x['display-name'])
        log('XMLTV: sortChannels, channels = %s'%(len(channels)))
        return channels


    def sortProgrammes(self, programmes=None):
        if programmes is None: programmes = self.xmltvList['programmes']
        programmes.sort(key=lambda x:x['start'])
        programmes.sort(key=lambda x:x['channel'])
        log('XMLTV: sortProgrammes, programmes = %s'%(len(programmes)))
        return programmes


    def cleanSelf(self, items, key='id'): # remove imports (Non PseudoTV Live)
        log('XMLTV: cleanSelf, key = %s'%(key))
        return list(filter(lambda item:item.get(key,'').endswith('@%s'%(slugify(ADDON_NAME))), items))
        
        
    def cleanProgrammes(self, programmes=None): # remove expired content
        now = (datetime.datetime.fromtimestamp(float(getLocalTime()))) - datetime.timedelta(hours=3) #allow some old programmes to avoid empty cells.
        if programmes is None: programmes = self.xmltvList['programmes']
        try: 
            tmpProgrammes = [program for program in programmes if strpTime(program['stop'],xmltv.date_format) > now]
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
        
        
    def findChannel(self, item, channels=None): #find existing channel id in xmltvList
        if channels is None: channels = self.xmltvList['channels']
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
            
        writer = xmltv.Writer(encoding=xmltv.locale, date=data['date'],
                              source_info_url     = data['source-info-url'], 
                              source_info_name    = data['source-info-name'],
                              generator_info_url  = data['generator-info-url'], 
                              generator_info_name = data['generator-info-name'])
               
        channels = self.sortChannels(self.xmltvList['channels'])
        for channel in channels: writer.addChannel(channel)

        programmes = self.sortProgrammes(self.xmltvList['programmes'])
        for program in programmes: writer.addProgramme(program)
        
        with fileLocker():
            log('XMLTV: save, saving to %s'%(XMLTVFLE))
            writer.write(FileAccess.open(XMLTVFLE, "w"), pretty_print=True)
            self.buildGenres()
        return self.reset()
        

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
            
        self.m3uList = {'data':'#EXTM3U tvg-shift="%s" x-tvg-url="" x-tvg-id=""'%(self.getShift()),
                        'channels':self.cleanSelf(self.load())}
        

    def getShift(self):
        log('M3U: getShift')
        return '' # '-%s'%((round(datetime.datetime.now().minute) / 60)[:3])


    def getChannels(self):
        log('M3U: getChannels')
        return sorted(self.m3uList.get('channels',[]), key=lambda k: k['number'])
        

    def reset(self):
        log('M3U: reset')
        self.__init__()
        return True


    def importM3U(self, file):
        if not file: return False
        log('M3U: importM3U, file = %s'%file)   
        self.m3uList['channels'].extend(self.load(file)) #todo collision logic?
        return True
        

    def load(self, file=M3UFLE):
        log('M3U: load, file = %s'%file)
        if file.startswith('http'):
            url  = file
            file = os.path.join(TEMP_LOC,slugify(url),'.m3u')
            saveURL(url,file)
            
        fle   = FileAccess.open(file, 'r')
        lines = (fle.readlines())
        data  = lines.pop(0)
        fle.close()
        
        for idx, line in enumerate(lines):
            if line.startswith('#EXTINF:'):
                vod   = ''
                label = ''
                if 'catchup' in line:
                    line1 = re.compile('#EXTINF:-1 tvg-chno=\"(.*?)\" tvg-id=\"(.*?)\" tvg-name=\"(.*?)\" tvg-logo=\"(.*?)\" group-title=\"(.*?)\" radio=\"(.*?)\" catchup=\"(.*?)\",(.*)', re.IGNORECASE).search(line)
                    if line1: 
                        vod   = line1.group(7)
                        label = line1.group(8)
                else:
                    line1 = re.compile('#EXTINF:-1 tvg-chno=\"(.*?)\" tvg-id=\"(.*?)\" tvg-name=\"(.*?)\" tvg-logo=\"(.*?)\" group-title=\"(.*?)\" radio=\"(.*?)\",(.*)', re.IGNORECASE).search(line)
                    vod   = ''
                    label = line1.group(7)
                    
                #todo TypedDict for all dict. lists.
                try:    number = int(line1.group(1))
                except: number = float(line1.group(1))
                    
                channel = {'number' :number,
                           'id'     :line1.group(2),
                           'name'   :line1.group(3),
                           'logo'   :line1.group(4),
                           'group'  :line1.group(5).split(';'),
                           'radio'  :line1.group(6).lower() == 'true',
                           'label'  :label,
                           'catchup':vod,
                           'props'  :[]}
                
                for nidx in range(idx+1,len(lines)):
                    nline = lines[nidx]
                    if   nline.startswith('#EXTINF:'): break
                    elif nline.startswith('#KODIPROP:'):
                        prop = re.compile('^#KODIPROP:(.*)$', re.IGNORECASE).search(nline)
                        if prop: channel['props'].append(prop.group(1))
                    else: channel['url'] = nline
                yield channel
                

    def save(self):
        log('M3U: save')
        with fileLocker():
            fle = FileAccess.open(M3UFLE, 'w')
            log('M3U: save, saving to %s'%(M3UFLE))
            fle.write('%s\n'%(self.m3uList['data']))
            channels = self.m3uList['channels']
            citem = '#EXTINF:-1 tvg-chno="%s" tvg-id="%s" tvg-name="%s" tvg-logo="%s" group-title="%s" radio="%s" catchup="%s",%s\n'
            for channel in channels:
                if not channel: continue
                fle.write(citem%(channel['number'],
                                 channel['id'],
                                 channel['name'],
                                 channel['logo'],
                                 ';'.join(channel['group']),
                                 channel['radio'],
                                 channel['catchup'],
                                 channel['label']))
                if channel.get('props',[]):
                    fle.write('%s\n'%('\n'.join(['#KODIPROP:%s'%(prop) for prop in channel['props']])))
                fle.write('%s\n'%(channel['url']))
            fle.close()
        return self.reset()
        

    def addChannel(self, item, rebuild=True):
        log('M3U: addChannel, rebuild = %s, item = %s'%(rebuild,item))
        channels  = self.getChannels()
        idx, line = self.findChannel(item['id'], channels)
        if idx is None: channels.append(item)
        else:
            if rebuild: channels[idx] = item # replace existing channel
            else: channels[idx].update(item) # update existing channel
        self.m3uList['channels'] = channels
        return True


    def findChannel(self, id, channels=None):
        if channels is None: channels = self.getChannels()
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


    def cleanSelf(self, channels): # remove imports (Non PseudoTV Live)
        log('M3U: cleanSelf')
        return list(filter(lambda line:line.get('id','').endswith('@%s'%(slugify(ADDON_NAME))), channels))
        

    def delete(self):
        log('M3U: delete')
        if FileAccess.delete(M3UFLE): 
            return notificationDialog(LANGUAGE(30016)%('M3U'))
        return False