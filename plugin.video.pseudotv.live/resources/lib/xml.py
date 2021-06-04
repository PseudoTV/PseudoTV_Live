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
        if writer:
            self.writer = writer
        else:
            from resources.lib.parser import Writer
            self.writer = Writer()
            
        self.pool       = self.writer.pool
        self.vault      = self.writer.vault
        self.dialog     = self.writer.dialog
        self.filelock   = self.writer.GlobalFileLock
        
        if not self.vault.xmltvList:
            self.reload()
        else:
            self.withdraw()
                   
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
            
    def clear(self):
        self.log('clear')
        self.vault.xmltvList = {}
        return self.deposit()
        

    def reload(self):
        self.log('reload')
        self.vault.xmltvList = self.load()
        return self.deposit()
        
        
    def deposit(self):
        self.log('deposit')
        self.vault.set_xmltvList(self.vault.xmltvList)
        return True
        
    
    def withdraw(self):
        self.log('withdraw')
        self.vault.xmltvList = self.vault.get_xmltvList()
        return True
     

    def load(self):
        self.log('load')
        return {'data'       : self.loadData(),
                'channels'   : self.sortChannels(self.cleanSelf(self.loadChannels(),'id')),
                'programmes' : self.sortProgrammes(self.cleanProgrammes(self.cleanSelf(self.loadProgrammes(),'channel')))}
        
        
    def loadData(self):
        self.log('loadData')
        try: 
            with fileLocker(self.filelock):
                return (xmltv.read_data(FileAccess.open(getUserFilePath(XMLTVFLE), 'r')) or self.resetData())
        except Exception as e: 
            self.log('loadData, failed! %s'%(e))
            return self.resetData()


    def loadChannels(self, file=getUserFilePath(XMLTVFLE)):
        self.log('loadChannels, file = %s'%file)
        try:
            with fileLocker(self.filelock):
                return self.sortChannels(xmltv.read_channels(FileAccess.open(file, 'r')) or [])
        except Exception as e:
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            self.log('loadChannels, failed! %s'%(e))
            return []
        
        
    def loadProgrammes(self, file=getUserFilePath(XMLTVFLE)):
        self.log('loadProgrammes, file = %s'%file)
        try: 
            with fileLocker(self.filelock):
                return self.sortProgrammes(xmltv.read_programmes(FileAccess.open(file, 'r')) or [])
        except Exception as e: 
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            self.log('loadProgrammes, failed! %s'%(e))
            return []


    def save(self, reset=True):
        self.log('save')
        if reset: 
            data = self.resetData()
        else:     
            data = self.vault.xmltvList['data']
            
        with fileLocker(self.filelock):
            writer = xmltv.Writer(encoding            = DEFAULT_ENCODING, 
                                  date                = data['date'],
                                  source_info_url     = data['source-info-url'], 
                                  source_info_name    = data['source-info-name'],
                                  generator_info_url  = data['generator-info-url'], 
                                  generator_info_name = data['generator-info-name'])
                   
            channels = self.sortChannels(self.vault.xmltvList['channels'])
            for channel in channels: writer.addChannel(channel)

            programmes = self.sortProgrammes(self.vault.xmltvList['programmes'])
            for program in programmes: writer.addProgramme(program)
            
            filePath = getUserFilePath(XMLTVFLE)
            self.log('save, saving to %s'%(filePath))
            writer.write(FileAccess.open(filePath, "w"), pretty_print=True)
            self.buildGenres()
        return self.reload()
        

    def delete(self):
        self.log('delete')
        if FileAccess.delete(getUserFilePath(XMLTVFLE)): #xmltv.xml
            FileAccess.delete(getUserFilePath(GENREFLE)) #genre.xml
            return self.dialog.notificationDialog(LANGUAGE(30016)%('XMLTV'))
        return False


    @staticmethod
    def cleanSelf(items, key='id', slug='@%s'%(slugify(ADDON_NAME))): # remove imports (Non PseudoTV Live), key = {'id':channels,'channel':programmes}
        log('XMLTV: cleanSelf, key = %s'%(key))
        if not slug: return items
        return list(filter(lambda item:item.get(key,'').endswith(slug), items))
        
        
    @staticmethod
    def cleanProgrammes(programmes): # remove expired content
        try:
            now = (datetime.datetime.fromtimestamp(float(getLocalTime()))) - datetime.timedelta(hours=3) #allow some old programmes to avoid empty cells.
            tmpProgrammes = [program for program in programmes if strpTime(program['stop'].rstrip(),DTFORMAT)  > now]
        except Exception as e: 
            log("XMLTV: cleanProgrammes, Failed! " + str(e), xbmc.LOGERROR)
            tmpProgrammes = programmes
        log('XMLTV: cleanProgrammes, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
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
                
            channels   = self.loadChannels(file)
            programmes = self.loadProgrammes(file)
            
            for key, value in filters.items():
                if not value: continue
                elif key == 'slug':
                    importChannels, importProgrammes = self.chkImport(self.cleanSelf(channels,'id',value), self.cleanSelf(programmes,'channel',value))
                elif key == 'providers':  #currently no provider filter for xmltv, include all guide meta; let m3u filter by provider.
                    importChannels, importProgrammes = self.chkImport(channels, programmes)
                else: continue
                self.vault.xmltvList.get('channels',[]).extend(self.sortChannels(importChannels))
                self.vault.xmltvList.get('programmes',[]).extend(self.sortProgrammes(importProgrammes))
                
        except Exception as e: log("XMLTV: importXMLTV, failed! " + str(e), xbmc.LOGERROR)
        return True


    def chkImport(self, channels, programmes): # parse for empty programmes, inject single cell entry.
        try:
            def parsePrograms(channel):
                for program in programmes:
                    if channel.get('id') == program.get('channel'):
                        try: tmpChannels.remove(channel)
                        except: continue
                          
            tmpChannels = channels.copy() 
            self.pool.poolList(parsePrograms,channels)
            for channel in tmpChannels: programmes.append(self.addSingleEntry(channel))
            self.log("chkImport, added %s single entries"%(len(tmpChannels)))
        except Exception as e: 
            self.log("chkImport, Failed! %s"%(e), xbmc.LOGERROR)
        return channels, programmes


    def buildGenres(self):
        self.log('buildGenres') #todo user color selector.
        with fileLocker(self.filelock):
            dom = parse(FileAccess.open(GENREFLE_DEFAULT, "r"))
        
        epggenres = {}
        lines = dom.getElementsByTagName('genre')
        for line in lines: 
            items = line.childNodes[0].data.split('/')
            for item in items:
                epggenres[item.strip()] = line.attributes['genreId'].value
            
        proggenres = []
        for program in self.vault.xmltvList['programmes']:
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
        
        with fileLocker(self.filelock):
            xmlData = FileAccess.open(getUserFilePath(GENREFLE), "w")
            xmlData.write(doc.toprettyxml(indent='\t'))
            xmlData.close()
        return True


    def getChannels(self):
        self.log('getChannels')
        return self.sortChannels(self.vault.xmltvList.get('channels',[]))


    def getProgrammes(self):
        self.log('getProgrammes')
        return self.sortProgrammes(self.vault.xmltvList.get('programmes',[]))


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
        idx, channel = self.findChannel(citem, channels=self.vault.xmltvList['channels'])
        if idx is None: self.vault.xmltvList['channels'].append(citem)
        else: self.vault.xmltvList['channels'][idx] = citem # replace existing channel meta
        return True


    def addProgram(self, id, item):
        pitem      = {'channel'     : id,
                      'credits'     : {'writer':[setWriter(self.cleanString(item['writer']),item['fitem'])]},
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
            
        if item.get('date',''):
            try: pitem['date'] = (strpTime(item['date'], '%Y-%m-%d')).strftime('%Y%m%d')
            except: pass

        if item.get('new',False): 
            pitem['new'] = '' #write empty tag, tag == True
        
        rating = self.cleanMPAA(item.get('rating',''))
        if rating != 'NA' and rating.startswith('TV'): 
            pitem['rating'] = [{'system': 'VCHIP', 'value': rating}]
        elif rating != 'NA' :  
            pitem['rating'] = [{'system': 'MPAA', 'value': rating}]
            
        if item.get('episode-num',{}): 
            pitem['episode-num'] = [(item['episode-num'].get('xmltv_ns',''), 'xmltv_ns'),
                                    (item['episode-num'].get('onscreen',''), 'onscreen')]
            
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
            
        self.log('addProgram = %s'%(pitem.get('channel')))
        self.vault.xmltvList['programmes'].append(pitem)
        return True


    def addSingleEntry(self, channel):
        secs  = EPG_HRS #(SETTINGS.getSettingInt('Max_Days') * 3600)
        now   = datetime.datetime.fromtimestamp(roundTimeDown(getLocalTime(),offset=60))
        pitem = {'channel'     : channel.get('id'),
                 'title'       : [(channel.get('display-name',[{'',LANG}])[0][0], LANG)],
                 'desc'        : [(xbmc.getLocalizedString(161), LANG)],
                 'stop'        : ((now + datetime.timedelta(seconds=secs)).strftime(DTFORMAT)),
                 'start'       : (now.strftime(DTFORMAT)),
                 'icon'        : [{'src': channel.get('icon',[{}])[0].get('src')}],
                 'length'      : {'units': 'seconds', 'length': str(secs)}}
        self.log('addSingleEntry = %s'%(pitem))
        return pitem


    def removeChannel(self, citem): # remove single channel and all programmes from xmltvList
        channels   = self.vault.xmltvList['channels'].copy()
        programmes = self.vault.xmltvList['programmes'].copy()
        self.vault.xmltvList['channels']   = list(filter(lambda channel:channel.get('id') != citem.get('id'), channels))
        self.vault.xmltvList['programmes'] = list(filter(lambda program:program.get('channel') != citem.get('id'), programmes))
        self.log('removeChannel, removing channel %s; channels: before = %s, after = %s; programmes: before = %s, after = %s'%(citem.get('id'),len(channels),len(self.vault.xmltvList['channels']),len(programmes),len(self.vault.xmltvList['programmes'])))
        return True
        
        
    def findChannel(self, citem, channels=None): #find existing channel id in xmltvList
        if channels is None: channels = self.vault.xmltvList['channels']
        for idx, channel in enumerate(channels): 
            if channel.get('id') == citem.get('id'): 
                return idx, channel
        return None, {}
        

    @staticmethod
    def cleanStar(str1):
        return '%s/10'%(int(round(float(str1))))


    @staticmethod
    def cleanMPAA(text):
        #todo regex, detect other region rating formats
        # re.compile(':(.*)', re.IGNORECASE).search(text))
        try:
            text = re.sub('/ US', ''  , text)
            text = re.sub('Rated ', '', text)
            return text
        except: return text


    @staticmethod
    def cleanString(text):
        if text == ',' or not text: text = LANGUAGE(30161) #"Unavailable"
        return text
