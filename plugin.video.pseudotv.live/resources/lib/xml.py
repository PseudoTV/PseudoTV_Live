#   Copyright (C) 2021 Lunatixz
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
# https://raw.githubusercontent.com/XMLTV/xmltv/master/xmltv.dtd
# -*- coding: utf-8 -*-

from resources.lib.globals     import *
from resources.lib             import xmltv

class XMLTV:
    def __init__(self, writer=None):
        self.log('__init__')
        if writer is None:
            from resources.lib.parser import Writer
            writer = Writer()
        self.writer = writer

        if self.writer.vault.xmltvList is None:
            self._reload()
        else:
            self._withdraw()
                
                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

            
    def _clear(self):
        self.log('_clear')
        self.writer.vault.xmltvList = {}
        return self._deposit()
        

    def _reload(self):
        self.log('_reload')
        self.writer.vault.xmltvList = self._load()
        return self._deposit()
        
        
    def _deposit(self):
        self.log('_deposit')
        self.writer.vault.set_xmltvList(self.writer.vault.xmltvList)
        return True
        
    
    def _withdraw(self):
        self.log('_withdraw')
        self.writer.vault.xmltvList = self.writer.vault.get_xmltvList()
        return True
     

    def _load(self):
        self.log('_load')
        xmltvList = {'data'       : self.loadData(),
                     'channels'   : self.sortChannels(self.cleanSelf(self.loadChannels(),'id')),
                     'programmes' : self.sortProgrammes(self.cleanProgrammes(self.cleanSelf(self.loadProgrammes(),'channel')))}
        return xmltvList
        
        
    def loadData(self):
        self.log('loadData')
        try: 
            with fileLocker(self.writer.globalFileLock):
                return (xmltv.read_data(FileAccess.open(getUserFilePath(XMLTVFLE), 'r')) or self.resetData())
        except Exception as e: 
            self.log('loadData, failed! %s'%(e))
            return self.resetData()


    def loadChannels(self, file=getUserFilePath(XMLTVFLE)):
        self.log('loadChannels, file = %s'%file)
        try:
            with fileLocker(self.writer.globalFileLock):
                return self.sortChannels(xmltv.read_channels(FileAccess.open(file, 'r')) or [])
        except Exception as e:
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            self.log('loadChannels, failed! %s'%(e))
            return []
        
        
    def loadProgrammes(self, file=getUserFilePath(XMLTVFLE)):
        self.log('loadProgrammes, file = %s'%file)
        try: 
            with fileLocker(self.writer.globalFileLock):
                return self.sortProgrammes(xmltv.read_programmes(FileAccess.open(file, 'r')) or [])
        except Exception as e: 
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            self.log('loadProgrammes, failed! %s'%(e))
            return []


    def loadEndTimes(self, channels=None, programmes=None, fallback=None):
        if channels   is None: channels   = self.getChannels()
        if programmes is None: programmes = self.getProgrammes()
        if fallback   is None: fallback   = datetime.datetime.fromtimestamp(roundTimeDown(getLocalTime(),offset=60)).strftime(DTFORMAT)
            
        for channel in channels:
            try: 
                stopString = max([program['stop'] for program in programmes if program['channel'] == channel['id']], default=fallback)
                self.log('loadEndTimes, channel = %s, stopString = %s'%(channel['id'],stopString))
                yield channel['id'],datetime.datetime.timestamp(strpTime(stopString, DTFORMAT))
            except Exception as e:
                self.log("loadEndTimes, Failed!\n%s\nRemoving malformed XMLTV channel/programmes %s"%(e,channel.get('id')), xbmc.LOGERROR)
                self.removeBroadcasts(channel) #something went wrong; remove existing xmltv; force fresh rebuild.
                yield channel['id'],datetime.datetime.timestamp(strpTime(fallback, DTFORMAT))


    def saveXMLTV(self, reset=True):
        self.log('saveXMLTV')
        if reset: 
            data = self.resetData()
        else:     
            data = self.writer.vault.xmltvList['data']
            
        with fileLocker(self.writer.globalFileLock):
            writer = xmltv.Writer(encoding            = DEFAULT_ENCODING, 
                                  date                = data['date'],
                                  source_info_url     = data['source-info-url'], 
                                  source_info_name    = data['source-info-name'],
                                  generator_info_url  = data['generator-info-url'], 
                                  generator_info_name = data['generator-info-name'])
                   

            programmes = self.sortProgrammes(self.writer.vault.xmltvList['programmes'])
            channels   = self.sortChannels(self.cleanChannels(self.writer.vault.xmltvList['channels'], programmes))
            for channel in channels:   writer.addChannel(channel)
            for program in programmes: writer.addProgramme(program)
            
            filePath = getUserFilePath(XMLTVFLE)
            self.log('saveXMLTV, saving to %s'%(filePath))
            writer.write(FileAccess.open(filePath, "w"), pretty_print=True)
            self.buildGenres()
        return self._reload()
        

    def deleteXMLTV(self):
        self.log('deleteXMLTV')
        if FileAccess.delete(getUserFilePath(XMLTVFLE)): #xmltv.xml
            FileAccess.delete(getUserFilePath(GENREFLE)) #genre.xml
            return self.writer.dialog.notificationDialog(LANGUAGE(30016)%('XMLTV'))
        return False


    @staticmethod
    def cleanSelf(items, key='id', slug='@%s'%(slugify(ADDON_NAME))): # remove imports (Non PseudoTV Live), key = {'id':channels,'channel':programmes}
        log('XMLTV: cleanSelf, key = %s'%(key))
        if not slug: return items
        return list(filter(lambda item:item.get(key,'').endswith(slug), items))
        
        
    @staticmethod
    def cleanChannels(channels, programmes): # remove stations with no guidedata
        stations    = list(set([program.get('channel') for program in programmes]))
        tmpChannels = [channel for station in stations for channel in channels if channel.get('id') == station]
        log('XMLTV: cleanChannels, before = %s, after = %s'%(len(channels),len(tmpChannels)))
        return tmpChannels
        
        
    def cleanProgrammes(self, programmes): # remove expired content
        try:
            min = (self.writer.jsonRPC.getSettingValue('epg.pastdaystodisplay')  or 1)
            now = (datetime.datetime.fromtimestamp(float(getLocalTime()))) - datetime.timedelta(days=min) #allow some old programmes to avoid empty cells.
            tmpProgrammes = [program for program in programmes if strpTime(program['stop'].rstrip(),DTFORMAT) > now]
        except Exception as e: 
            self.log("cleanProgrammes, Failed! " + str(e), xbmc.LOGERROR)
            tmpProgrammes = programmes
        self.log('cleanProgrammes, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
        return tmpProgrammes


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


    def importXMLTV(self, file, filters={}):
        self.log('importXMLTV, file = %s, filters = %s'%(file,filters))
        try:
            if file.startswith('http'):
                url  = file
                file = os.path.join(TEMP_LOC,'%s.xml'%(slugify(url)))
                saveURL(url,file)
                
                
            importChannels, importProgrammes = [],[]
            channels, programmes = self.loadChannels(file), self.loadProgrammes(file)
            
            for key, value in filters.items():
                if key == 'slug' and value:
                    importChannels, importProgrammes = self.cleanSelf(channels,'id',value), self.cleanSelf(programmes,'channel',value)
            
            #currently no provider filter for xmltv, include all guide meta; let m3u filter by provider.
            if not importChannels and importProgrammes: 
                importChannels, importProgrammes = channels, programmes
                
            importChannels, importProgrammes = self.chkImport(importChannels, importProgrammes)
            self.log('importXMLTV, found importChannels = %s, importProgrammes = %s'%(len(importChannels),len(importProgrammes)))
            self.writer.vault.xmltvList.get('channels',[]).extend(self.sortChannels(importChannels))
            self.writer.vault.xmltvList.get('programmes',[]).extend(self.sortProgrammes(importProgrammes))
                            
        except Exception as e: self.log("importXMLTV, failed! " + str(e), xbmc.LOGERROR)
        return True


    def chkImport(self, channels, programmes): # parse for empty programmes, inject single cell entry.
        try:
            def parsePrograms(channel):
                for program in programmes:
                    if channel.get('id') == program.get('channel'):
                        try: tmpChannels.remove(channel)
                        except: continue
                          
            tmpChannels = channels.copy() 
            self.writer.pool.poolList(parsePrograms,channels)
            for channel in tmpChannels: programmes.append(self.addSingleEntry(channel))
            self.log("chkImport, added %s single entries"%(len(tmpChannels)))
        except Exception as e: 
            self.log("chkImport, Failed! %s"%(e), xbmc.LOGERROR)
        return channels, programmes


    def buildGenres(self):
        self.log('buildGenres') #todo user color selector.
        with fileLocker(self.writer.globalFileLock):
            dom = parse(FileAccess.open(GENREFLE_DEFAULT, "r"))
        
        epggenres = {}
        lines = dom.getElementsByTagName('genre')
        for line in lines: 
            items = line.childNodes[0].data.split('/')
            for item in items:
                epggenres[item.strip()] = line.attributes['genreId'].value
            
        proggenres = []
        for program in self.writer.vault.xmltvList['programmes']:
            group = []
            for genre in program.get('category',[]):
                group.append(genre[0])
            proggenres.append(group)
            
        for genres in proggenres:
            for genre in genres:
                if genre and epggenres.get(genre,''): #{'Drama': '0x81'}
                    epggenres[('/').join(list(filter(None,genres)))] = (epggenres.get(genre,'') or '0x00')
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
        
        with fileLocker(self.writer.globalFileLock):
            xmlData = FileAccess.open(getUserFilePath(GENREFLE), "w")
            xmlData.write(doc.toprettyxml(indent='\t'))
            xmlData.close()
            return True


    def getChannels(self):
        self.log('getChannels')
        return self.sortChannels(self.writer.vault.xmltvList.get('channels',[]))


    def getProgrammes(self):
        self.log('getProgrammes')
        return self.sortProgrammes(self.writer.vault.xmltvList.get('programmes',[]))


    def resetData(self):
        self.log('resetData')
        return {'date'                : datetime.datetime.fromtimestamp(float(time.time())).strftime(DTFORMAT),
                'generator-info-name' : self.cleanString('%s Guidedata'%(ADDON_NAME)),
                'generator-info-url'  : self.cleanString(ADDON_ID),
                'source-info-name'    : self.cleanString(ADDON_NAME),
                'source-info-url'     : self.cleanString(ADDON_ID)}


    def addChannel(self, item):
        citem    = ({'id'           : item['id'],
                     'display-name' : [(self.cleanString(item['name']), LANG)],
                     'icon'         : [{'src':item['logo']}]})
        self.log('addChannel, citem = %s'%(citem))
        idx, channel = self.findChannel(citem, channels=self.writer.vault.xmltvList['channels'])
        if idx is None: self.writer.vault.xmltvList['channels'].append(citem)
        else: self.writer.vault.xmltvList['channels'][idx] = citem # replace existing channel meta
        return True


    def addProgram(self, id, item):
        pitem      = {'channel'     : id,
                      'credits'     : {'writer':[setWriter(self.cleanString(item['writer']),item['fitem'])]},
                      'category'    : [(self.cleanString(genre.replace('Unknown','Undefined')),LANG) for genre in item['categories']],
                      'title'       : [(self.cleanString(item['title']), LANG)],
                      'desc'        : [(self.cleanString(item['desc']), LANG)],
                      'stop'        : (datetime.datetime.fromtimestamp(float(item['stop'])).strftime(DTFORMAT)),
                      'start'       : (datetime.datetime.fromtimestamp(float(item['start'])).strftime(DTFORMAT)),
                      'icon'        : [{'src': item['thumb']}],
                      'length'      : {'units': 'seconds', 'length': str(item['length'])}}
                      
        if item.get('sub-title',''):
            pitem['sub-title'] = [(self.cleanString(item['sub-title']), LANG)]

        if item.get('stars'):
            pitem['star-rating'] = [{'value': '%s/10'%(int(round(float(item['stars']))))}]
                      
        if item.get('director',''):
            pitem['credits']['director'] = [self.cleanString(item['director'])]
            
        if item.get('actor',''):
            pitem['credits']['actor'] = item['actor']

        if item.get('catchup-id',''):
            pitem['catchup-id'] = item['catchup-id']
            
        if item.get('date',''):
            try: pitem['date'] = (strpTime(item['date'], '%Y-%m-%d')).strftime('%Y%m%d')
            except: pass

        if item.get('new',False): 
            pitem['new'] = '' #write empty tag, tag == True
        
        rating = item.get('rating','')
        if rating != 'NA':
            if rating.lower().startswith('tv'): 
                pitem['rating'] = [{'system': 'VCHIP', 'value': rating}]
            else:  
                pitem['rating'] = [{'system': 'MPAA', 'value': rating}]
            
        if item.get('episode-num',{}): 
            pitem['episode-num'] = [(item['episode-num'].get('xmltv_ns',''), 'xmltv_ns'),
                                    (item['episode-num'].get('onscreen',''), 'onscreen')]
            
        if item.get('audio',False):
            pitem['audio'] = [{'stereo': 'stereo'}]

        # if item.get('video',{}):
            # pitem['video'] = [{'aspect': item.get('video',{}).get('aspect')}]
        
        # if item.get('language',''):
            # pitem['language'] = [(item.get('language'), LANG)]
           
        # if item.get('subtitle',[]):
            # pitem['subtitles'] = [{'type': 'teletext', 'language': ('%s'%(sub), LANG)} for sub in item.get('subtitle',[])]
            
         ##### TODO #####
           # 'country'     : [('USA', LANG)],#todo
           # 'premiere': (u'Not really. Just testing', u'en'),
           
        self.log('addProgram = %s'%(pitem.get('channel')))
        self.writer.vault.xmltvList['programmes'].append(pitem)
        return True


    def addSingleEntry(self, channel, start=None, length=EPG_HRS): #create a single entry with min. channel meta, use as a filler.
        if start is None: start = datetime.datetime.fromtimestamp(roundTimeDown(getLocalTime(),offset=60))
        pitem = {'channel'     : channel.get('id'),
                 'title'       : [(channel.get('display-name',[{'',LANG}])[0][0], LANG)],
                 'desc'        : [(xbmc.getLocalizedString(161), LANG)],
                 'stop'        : ((start + datetime.timedelta(seconds=length)).strftime(DTFORMAT)),
                 'start'       : (start.strftime(DTFORMAT)),
                 'icon'        : [{'src': channel.get('icon',[{}])[0].get('src')}],
                 'length'      : {'units': 'seconds', 'length': str(length)}}
        self.log('addSingleEntry = %s'%(pitem))
        return pitem


    def removeBroadcasts(self, citem): # remove single channel and all programmes from xmltvList
        channels   = self.writer.vault.xmltvList['channels'].copy()
        programmes = self.writer.vault.xmltvList['programmes'].copy()
        self.writer.vault.xmltvList['channels']   = list(filter(lambda channel:channel.get('id') != citem.get('id'), channels))
        self.writer.vault.xmltvList['programmes'] = list(filter(lambda program:program.get('channel') != citem.get('id'), programmes))
        self.log('removeBroadcasts, removing channel %s; channels: before = %s, after = %s; programmes: before = %s, after = %s'%(citem.get('id'),len(channels),len(self.writer.vault.xmltvList['channels']),len(programmes),len(self.writer.vault.xmltvList['programmes'])))
        return True
        
        
    def findChannel(self, citem, channels=None): #find existing channel id in xmltvList
        if channels is None: channels = self.writer.vault.xmltvList['channels']
        for idx, channel in enumerate(channels): 
            if channel.get('id') == citem.get('id'): 
                return idx, channel
        return None, {}


    @staticmethod
    def cleanString(text):
        if text == ', ' or not text: text = LANGUAGE(30161) #"Unavailable"
        return text
