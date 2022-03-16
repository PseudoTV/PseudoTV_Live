#   Copyright (C) 2022 Lunatixz
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
        return {'data'       : self.loadData(),
                'channels'   : self.sortChannels(self.cleanSelf(self.loadChannels(),'id')),
                'programmes' : self.sortProgrammes(self.cleanProgrammes(self.cleanSelf(self.loadProgrammes(),'channel')))}
        
        
    def loadData(self, file=XMLTVFLEPATH):
        self.log('loadData')
        try: 
            return (xmltv.read_data(FileAccess.open(file, 'r')) or self.resetData())
        except Exception as e: 
            self.log('loadData, failed! %s'%(e))
            return self.resetData()


    def loadChannels(self, file=XMLTVFLEPATH):
        self.log('loadChannels, file = %s'%file)
        try:
            return (xmltv.read_channels(FileAccess.open(file, 'r')) or [])
        except Exception as e:
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            self.log('loadChannels, failed! %s'%(e))
            return []
        
        
    def loadProgrammes(self, file=XMLTVFLEPATH):
        self.log('loadProgrammes, file = %s'%file)
        try: 
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


    def _save(self, reset=True):
        self.log('_save')
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
            
            try:
                self.log('_save, saving to %s'%(XMLTVFLEPATH))
                writer.write(FileAccess.open(XMLTVFLEPATH, "w"), pretty_print=True)
                self.buildGenres()
            except Exception as e:
                self.log("_save, Failed!", xbmc.LOGERROR)
                self.writer.dialog.notificationDialog(LANGUAGE(30001))
        return self._reload()
        

    def deleteXMLTV(self):
        self.log('deleteXMLTV')
        if FileAccess.delete(XMLTVFLEPATH): #xmltv.xml
            FileAccess.delete(GENREFLEPATH) #genre.xml
            self._clear()
            return self.writer.dialog.notificationDialog(LANGUAGE(30016)%('XMLTV'))
        return False


    @staticmethod
    def cleanSelf(items, key='id', slug='@%s'%(slugify(ADDON_NAME))): # remove imports (Non PseudoTV Live), key = {'id':channels,'channel':programmes}
        log('XMLTV: cleanSelf, key = %s'%(key))
        if not slug: return items
        return(list(filter(lambda item:item.get(key,'').endswith(slug), items)))
        
        
    @staticmethod
    def cleanChannels(channels, programmes): # remove stations with no guidedata
        stations    = list(set([program.get('channel') for program in programmes]))
        tmpChannels = [channel for station in stations for channel in channels if channel.get('id') == station]
        log('XMLTV: cleanChannels, before = %s, after = %s'%(len(channels),len(tmpChannels)))
        return tmpChannels
        
        
    def cleanProgrammes(self, programmes): # remove expired content
        try:
            SETTINGS.setSettingInt('Max_Days',(self.writer.jsonRPC.getSettingValue('epg.futuredaystodisplay') or 3))
            min = (self.writer.jsonRPC.getSettingValue('epg.pastdaystodisplay') or 1)
            now = (datetime.datetime.fromtimestamp(float(getLocalTime()))) - datetime.timedelta(days=min) #allow some old programmes to avoid empty cells.
            tmpProgrammes = [program for program in programmes if strpTime(program['stop'].rstrip(),DTFORMAT) > now]
        except Exception as e: 
            self.log("cleanProgrammes, Failed! %s"%(e), xbmc.LOGERROR)
            tmpProgrammes = programmes
        self.log('cleanProgrammes, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
        return tmpProgrammes


    @staticmethod
    def sortChannels(channels):
        try: channels.sort(key=lambda x:x.get('display-name'))
        except: pass
        return channels


    @staticmethod
    def sortProgrammes(programmes):
        programmes.sort(key=lambda x:x['start'])
        programmes.sort(key=lambda x:x['channel'])
        log('XMLTV: sortProgrammes, programmes = %s'%(len(programmes)))
        return programmes


    def importXMLTV(self, file, m3uChannels={}):
        self.log('importXMLTV, file = %s, m3uChannels = %s'%(file,len(m3uChannels)))
        def matchChannel(channel, channels, programmes):
            importChannels.extend(list(filter(lambda chan:chan.get('id') == channel.get('id'), channels)))
            importProgrammes.extend(list(filter(lambda prog:prog.get('channel') == channel.get('id'), programmes)))

        try:
            if file.startswith('http'):
                files = []
                for file in file.split(','): #handle possible list.
                    url  = file
                    file = os.path.join(TEMP_LOC,'%s'%(slugify(url)))
                    files.append(file)
                    saveURL(url,file)
            else:
                files = [file]
                
            for file in files:
                importChannels, importProgrammes = [],[]
                channels, programmes = self.loadChannels(file), self.loadProgrammes(file)
                
                if m3uChannels: #filter imported programmes by m3uchannels list.
                    self.writer.pool.poolList(matchChannel, m3uChannels, kwargs={'channels':channels,'programmes':programmes})
                else: #no filter, import everything!
                    importChannels   = channels
                    importProgrammes = programmes
                    
                importChannels, importProgrammes = self.chkImport(importChannels, importProgrammes)
                self.log('importXMLTV, found importChannels = %s, importProgrammes = %s from %s'%(len(importChannels),len(importProgrammes),file))
                self.writer.vault.xmltvList.get('channels',[]).extend(self.sortChannels(importChannels))
                self.writer.vault.xmltvList.get('programmes',[]).extend(self.sortProgrammes(importProgrammes))
        except Exception as e: self.log("importXMLTV, failed! %s"%(e), xbmc.LOGERROR)
        return True


    def chkImport(self, channels, programmes): # parse for empty programmes, inject single cell entry.
        try:
            def chkPrograms(channel):
                for program in programmes:
                    if channel.get('id') == program.get('channel'):
                        try:    return tmpChannels.remove(channel)
                        except: continue
                          
            tmpChannels = channels.copy() 
            self.writer.pool.poolList(chkPrograms,channels)
            for channel in tmpChannels: programmes.append(self.addSingleEntry(channel)) #append single cell entry for channels missing programmes
            self.log("chkImport, added %s single entries"%(len(tmpChannels)))
        except Exception as e: 
            self.log("chkImport, Failed! %s"%(e), xbmc.LOGERROR)
        return channels, programmes


    def buildGenres(self):
        self.log('buildGenres') #todo user color selector.
        def parseGenres(plines):
            epggenres = {}
            for line in plines:
                try:    
                    names = line.childNodes[0].data
                    items = names.split('/')
                    data  = {'genre':names,'name':names,'genreId':line.attributes['genreId'].value}
                    epggenres[names.lower()] = data
                    for item in items:
                        name = item.strip()
                        if name and not epggenres.get(name.lower()):
                            epgdata = data.copy()
                            epgdata['name'] = name
                            epggenres[name.lower()] = epgdata
                except: continue
            return epggenres

        def matchGenres(programmes):
            for program in programmes:
                categories = [cat[0] for cat in program.get('category',[])]
                catcombo   = '/'.join(categories)
                for category in categories:
                    match = epggenres.get(category.lower())
                    if match and not epggenres.get(catcombo.lower()):
                        epggenres[catcombo.lower()] = match
                        break
        
        if FileAccess.exists(GENREFLE_DEFAULT): 
            try:
                dom = parse(FileAccess.open(GENREFLE_DEFAULT, "r"))
                epggenres = parseGenres(dom.getElementsByTagName('genre'))
                matchGenres(self.writer.vault.xmltvList['programmes'])     
                epggenres = dict(sorted(sorted(epggenres.items(), key=lambda v:v[1]['name']), key=lambda v:v[1]['genreId']))   
                
                doc  = Document()
                root = doc.createElement('genres')                
                doc.appendChild(root)
                name = doc.createElement('name')
                name.appendChild(doc.createTextNode('%s'%(ADDON_NAME)))
                root.appendChild(name)
                
                for key in epggenres:
                    gen = doc.createElement('genre')
                    gen.setAttribute('genreId',epggenres[key].get('genreId'))
                    gen.appendChild(doc.createTextNode(key.title().replace('Tv','TV').replace('Nr','NR').replace('Na','NA')))
                    root.appendChild(gen)
                    
                with fileLocker(self.writer.globalFileLock):
                    try:
                        xmlData = FileAccess.open(GENREFLEPATH, "w")
                        xmlData.write(doc.toprettyxml(indent='\t'))
                        xmlData.close()
                    except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)
                    return True

            except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)


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
        idx, channel = self.writer.findChannel(citem, channels=self.getChannels())
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
                      
        if item.get('sub-title'):
            pitem['sub-title'] = [(self.cleanString(item['sub-title']), LANG)]

        if item.get('stars'):
            pitem['star-rating'] = [{'value': '%s/10'%(int(round(float(item['stars']))))}]
                      
        if item.get('director'):
            pitem['credits']['director'] = [self.cleanString(director) for director in item['director']]
            
        if item.get('actor'):
            pitem['credits']['actor'] = [self.cleanString(actor) for actor in item['actor']]

        if item.get('catchup-id'):
            pitem['catchup-id'] = item['catchup-id']
            
        if item.get('date'):
            try: pitem['date'] = (strpTime(item['date'], '%Y-%m-%d')).strftime('%Y%m%d')
            except: pass

        if item.get('new',False): 
            pitem['new'] = '' #write empty tag, tag == True
        
        rating = item.get('rating','NA')
        if rating != 'NA':
            if rating.lower().startswith('tv'): 
                pitem['rating'] = [{'system': 'VCHIP', 'value': rating}]
            else:  
                pitem['rating'] = [{'system': 'MPAA', 'value': rating}] #todo support international rating systems
            
        if item.get('episode-num'): 
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
                 'icon'        : [{'src': (channel.get('icon','') or [{}])[0].get('src')}],
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


    @staticmethod
    def cleanString(text):
        if text == ', ' or not text: text = LANGUAGE(30161) #"Unavailable"
        return bytes(text,DEFAULT_ENCODING).decode(DEFAULT_ENCODING,'ignore')
