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
from resources.lib.rules       import RulesList
from resources.lib.recommended import Recommended

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
        self.endtimes      = self.xmltv.xmltvList['endtimes']
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
        if self.xmltv.reset() and self.m3u.reset():
            return True
        return False
        
        
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
            if importItem.get('type','') == 'iptv':
                if self.dialog is not None:
                    self.dialog = ProgressBGDialog(self.progress, self.dialog, message='%s: %s'%(LANGUAGE(30151),importItem.get('name','')))
                self.m3u.importM3U(importItem.get('m3u',''))
                self.xmltv.importXMLTV(importItem.get('xmltv',''))
        return True
        
        
    def addChannel(self, citem, radio=False, catchup=True):
        log('Writer: addChannel, citem = %s, radio = %s, catchup = %s'%(citem,radio,catchup))
        self.m3u.addChannel(citem)
        self.xmltv.addChannel(citem)
    
    
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
            item['sub-title']   = (file.get('episodetitle','') or '')
            item['rating']      = (file.get('mpaa','')         or 'NA')
            item['stars']       = (file.get('rating','')       or '0')
            item['categories']  = (file.get('genre','')        or ['Undefined'])
            item['type']        = file.get('type','video')
            item['new']         = int(file.get('playcount','1')) == 0
            item['thumb']       = getThumb(file)
            file['art']['thumb']= item['thumb']
            item['date']        = (file.get('firstaired','')   or file.get('premiered','') or file.get('releasedate','') or file.get('originaldate','') or None)
            
            if catchup:
                item['catchup-id'] = 'plugin://%s/?mode=vod&name=%s&id=%s&channel=%s&radio=%s'%(ADDON_ID,urllib.parse.quote(item['title']),urllib.parse.quote(encodeString(file.get('file',''))),urllib.parse.quote(citem['id']),str(item['radio']))
            
            if (item['type'] != 'movie' and (file.get("episode",0) > 0)):
                item['episode-num'] = 'S%sE%s'%(str(file.get("season",0)).zfill(2),str(file.get("episode",0)).zfill(2))
                
            item['director']    = (', '.join(file.get('director',[''])) or '')
            item['writer']      = (', '.join(file.get('writer',['']))   or '')
            file['data']        = citem #channel dict
            item['file']        = file # kodi fileitem/listitem dict.
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
        if not FileAccess.exists(PLS_LOC):
            FileAccess.makedirs(PLS_LOC)
            FileAccess.makedirs(PLS_LOC)
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
            
        self.rules       = RulesList()
        self.rules.channels = self
        
        self.recommended = Recommended(self.cache)
        self.recommended.channels = self
        
        self.channelList = (self.load() or self.getTemplate(ADDON_VERSION))
        
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


    def findImport(self, eitem):
        imports  = self.channelList['imports']
        for idx, item in enumerate(imports):
            if eitem.get('id','') == item.get('id',''): 
                log('Channels: findImport, item = %s, found = %s'%(eitem,item))
                return idx, item
        return None, {}
        

    def addImport(self, eitem):
        log('Channels: addImport, item = %s'%(eitem))
        imports   = self.channelList['imports']
        idx, item = self.findImport(eitem)
        if idx is None:
            imports.append(eitem)
        else:
            imports[idx].update(eitem)
        self.channelList['imports'] = imports
  
  
    def resetImports(self):
        log('Channels: resetImports')
        self.channelList['imports'] = []
        return True


    def getImports(self):
        log('Channels: getImports')
        return self.channelList.get('imports',[])

 
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


    def add(self, citem, channelkey=None):
        if channelkey is None:
            channelkey = 'predefined' if citem['number'] > CHANNEL_LIMIT else 'channels'
        if channelkey == 'predefined':
            channels = self.getPredefined()
        else:
            channels = self.getChannels()
        log('Channels: add, item = %s, channelkey = %s'%(citem,channelkey))
        idx, channel = self.findChannel(citem, channels)
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
        if channelkey == 'predefined':
            channels = self.getPredefined()
        else:
            channels = self.getChannels()
        log('Channels: removing item = %s, channelkey = %s'%(citem,channelkey))
        idx, channel = self.findChannel(citem, channels)
        if idx is not None: channels.pop(idx)
        self.channelList[channelkey] = channels
        return True
        
        
    def findChannel(self, citem, channels=None):
        if channels is None:
            channelkey = 'predefined' if citem['number'] > CHANNEL_LIMIT else 'channels'
            if channelkey == 'predefined':
                channels = self.getPredefined()
            else:
                channels = self.getChannels()
        for idx, channel in enumerate(channels):
            if (citem["id"] == channel["id"]):
                log('Channels: findChannel, item = %s, found = %s'%(citem,channel))
                return idx, channel
        return None, {}
        
        
    # @use_cache(7)
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
        if not FileAccess.exists(file): 
            file = CHANNELFLE_DEFAULT
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


    def addChannelRule(self, citem, ritem, channelkey=None):
        if channelkey is None:
            channelkey = 'predefined' if citem['number'] > CHANNEL_LIMIT else 'channels'
        if channelkey == 'predefined':
            channels = self.getPredefined()
        else:
            channels = self.getChannels()
        log('Channels: addChannelRule, id = %s, rule = %s, channelkey = %s'%(citem['id'],ritem,channelkey))
        rules = self.getChannelRules(citem, channelkey)
        idx, rule = self.findChannelRule(citem, ritem, channelkey)
        if idx is None:
            rules.append(ritem)
        else:
            rules[idx].update(ritem)
        self.channelList[channelkey]['rules'] = sorted(rules, key=lambda k: k['id'])
        return True


    def getChannelRules(self, citem, channelkey=None):
        if channelkey is None:
            channelkey = 'predefined' if citem['number'] > CHANNEL_LIMIT else 'channels'
        if channelkey == 'predefined':
            channels = self.getPredefined()
        else:
            channels = self.getChannels()
        log('Channels: getChannelRules, id = %s'%(citem['id']))
        for channel in channels:
            if channel['id'] == citem['id']:
                return channel.get('rules',[])
        return []


    def findChannelRule(self, citem, ritem, channelkey=None):
        if channelkey is None:
            channelkey = 'predefined' if citem['number'] > CHANNEL_LIMIT else 'channels'
        if channelkey == 'predefined':
            channels = self.getPredefined()
        else:
            channels = self.getChannels()
        log('Channels: findChannelRule, id = %s, rule = %s'%(citem['id'],ritem))
        rules = self.getChannelRules(citem,channels)
        for idx, rule in enumerate(rules):
            if rule['id'] == ritem['id']:
                return idx, rule
        return None, {}
        

class XMLTV:
    def __init__(self, cache=None):
        log('XMLTV: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
            
        self.maxDays        = getSettingInt('Max_Days')
        self.xmltvList      = {'data'       : self.loadData(),
                               'channels'   : self.cleanSelf(self.loadChannels(),'id'),
                               'programmes' : self.cleanSelf(self.loadProgrammes(),'channel')}
        self.xmltvList['endtimes'] = self.getEndtimes()
        
        
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
            log('XMLTV: loadChannels, failed! %s'%(e))
            return []
        
        
    def loadProgrammes(self, file=XMLTVFLE):
        log('XMLTV: loadProgrammes, file = %s'%file)
        try: 
            return self.sortProgrammes(self.cleanProgrammes(xmltv.read_programmes(FileAccess.open(file, 'r')) or []))
        except Exception as e: 
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
        return


    def getEndtimes(self): # get "Endtime" channels last stopDate in programmes
        endtime    = {}
        now        = roundTime(getLocalTime())
        channels   = self.xmltvList['channels']
        programmes = self.xmltvList['programmes']
        
        for channel in channels:
            try: 
                stopDate = [program['stop'] for program in programmes if program['channel'] == channel['id']][-1]
                stopTime = time.mktime(strpTime(stopDate, DTFORMAT).timetuple())
                log('XMLTV: getEndtimes, channelid = %s, endtime = %s, epoch = %s'%(channel['id'], stopDate, stopTime))
            except Exception as e:
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
        idx, channel = self.findChannel(citem, channels)
        if idx is None: 
            channels.append(citem)
        else: 
            channels[idx] = citem # update existing channel meta
        self.xmltvList['channels'] = channels
        return True


    def addProgram(self, id, item):
        programmes = self.xmltvList['programmes']
        pitem      = {'channel'     : id,
                      'credits'     : {'writer':['%s [COLOR item="%s"][/COLOR]'%(self.cleanString(item['writer']),encodeString(dumpJSON(item['file'])))]},
                      'category'    : [(self.cleanString(genre.replace('Unknown','Undefined')),LANG) for genre in item['categories']],
                      'title'       : [(self.cleanString(item['title']), LANG)],
                      'sub-title'   : [(self.cleanString(item['sub-title']), LANG)],
                      'desc'        : [(self.cleanString(item['desc']), LANG)],
                      'star-rating' : [{'value': self.cleanStar(item['stars'])}],
                      'stop'        : (datetime.datetime.fromtimestamp(float(item['stop'])).strftime(xmltv.date_format)),
                      'start'       : (datetime.datetime.fromtimestamp(float(item['start'])).strftime(xmltv.date_format)),
                      'icon'        : [{'src': item['thumb']}]}

        if item.get('director',''):
            pitem['credits']['director'] = [self.cleanString(item['director'])]

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
        return text.replace('\n',' ').replace('\r',' ').replace('\t',' ')
        
        
    def sortChannels(self, channels=None):
        if channels is None: 
            channels = self.xmltvList['channels']
        channels.sort(key=lambda x:x['display-name'])
        log('XMLTV: sortChannels, channels = %s'%(len(channels)))
        return channels


    def sortProgrammes(self, programmes=None):
        if programmes is None: 
            programmes = self.xmltvList['programmes']
        programmes.sort(key=lambda x:x['start'])
        programmes.sort(key=lambda x:x['channel'])
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
            
        self.m3uList   = {'data'    :'#EXTM3U tvg-shift="%s" x-tvg-url="" x-tvg-id=""'%(self.getShift()),
                          'channels':list(self.cleanSelf(self.load()))}
        

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
        fle = FileAccess.open(file, 'r')
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
                try:
                    number = int(line1.group(1))
                except:
                    number = float(line1.group(1))
                    
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
                    else: 
                        channel['url'] = nline
                yield channel
                

    def save(self):
        log('M3U: save')
        with fileLocker():
            fle = FileAccess.open(M3UFLE, 'w')
            log('M3U: save, saving to %s'%(M3UFLE))
            fle.write('%s\n'%(self.m3uList['data']))
            channels = self.m3uList['channels']
            for channel in channels:
                if not channel: continue
                citem = '#EXTINF:-1 tvg-chno="%s" tvg-id="%s" tvg-name="%s" tvg-logo="%s" group-title="%s" radio="%s" catchup="%s",%s\n'%(channel['number'],
                                                                                                                                          channel['id'],
                                                                                                                                          channel['name'],
                                                                                                                                          channel['logo'],
                                                                                                                                          ';'.join(channel['group']),
                                                                                                                                          channel['radio'],
                                                                                                                                          channel['catchup'],
                                                                                                                                          channel['label'])
                
                fle.write(citem)
                if channel.get('props',[]):
                    fle.write('%s\n'%('\n'.join(['#KODIPROP:%s'%(prop) for prop in channel['props']])))
                fle.write('%s\n'%(channel['url']))
            fle.close()
        return True
        

    def addChannel(self, item, rebuild=True):
        log('M3U: addChannel, rebuild = %s, item = %s'%(rebuild,item))
        channels  = self.getChannels()
        idx, line = self.findChannel(item['id'], channels)
        if idx is None:
            channels.append(item)
        else:
            if rebuild: 
                channels[idx] = item       # replace existing channel
            else:
                channels[idx].update(item) # update existing channel
        self.m3uList['channels'] = channels
        return True


    def findChannel(self, id, channels=None):
        if channels is None: 
            channels = self.getChannels()
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


    def cleanSelf(self, items): # remove imports (Non PseudoTV Live)
        log('M3U: cleanSelf')
        for line in items:
            if line['id'].endswith('@%s'%(slugify(ADDON_NAME))):
                yield line


    def delete(self):
        log('M3U: delete')
        if FileAccess.delete(M3UFLE): 
            return notificationDialog(LANGUAGE(30016)%('M3U'))
        return False