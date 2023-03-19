#   Copyright (C) 2023 Lunatixz
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

import xmltv
from globals          import *
from xml.dom.minidom  import parse, parseString, Document

class XMLTVS:
    def __init__(self):   
        self.XMLTVDATA = self._load()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _load(self, file=XMLTVFLEPATH):
        self.log('_load')
        return {'data'       : self.loadData(file),
                'channels'   : self.sortChannels(self.cleanSelf(self.loadChannels(file),'id')),
                'programmes' : self.sortProgrammes(self.cleanProgrammes(self.cleanSelf(self.loadProgrammes(file),'channel')))}


    def _save(self, file=XMLTVFLEPATH, reset=True):
        self.log('_save')
        if reset: data = self.resetData()
        else:     data = self.XMLTVDATA['data']
            
        with fileLocker(GLOBAL_FILELOCK):
            writer = xmltv.Writer(encoding            = DEFAULT_ENCODING, 
                                  date                = data['date'],
                                  source_info_url     = data['source-info-url'], 
                                  source_info_name    = data['source-info-name'],
                                  generator_info_url  = data['generator-info-url'], 
                                  generator_info_name = data['generator-info-name'])
                   
            programmes = self.sortProgrammes(self.XMLTVDATA['programmes'])
            channels   = self.sortChannels(self.cleanChannels(self.XMLTVDATA['channels'], programmes))
            for channel in channels:   writer.addChannel(channel)
            for program in programmes: writer.addProgramme(program)
            
            try:
                self.log('_save, saving to %s'%(file))
                writer.write(FileAccess.open(file, "w"), pretty_print=True)
            except Exception as e:
                self.log("_save, failed!", xbmc.LOGERROR)
                DIALOG.notificationDialog(LANGUAGE(32000))
            self.buildGenres()
        return True
    
    
    def loadData(self, file=XMLTVFLEPATH):
        self.log('loadData, file = %s'%file)
        try: 
            return (xmltv.read_data(FileAccess.open(file, 'r')) or self.resetData())
        except Exception as e: 
            self.log('loadData, failed! %s'%(e), xbmc.LOGERROR)
            return self.resetData()


    def loadChannels(self, file=XMLTVFLEPATH):
        self.log('loadChannels, file = %s'%file)
        try:
            return (xmltv.read_channels(FileAccess.open(file, 'r')) or [])
        except Exception as e:
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            self.log('loadChannels, failed! %s'%(e), xbmc.LOGWARNING)
            return []
        
        
    def loadProgrammes(self, file=XMLTVFLEPATH):
        self.log('loadProgrammes, file = %s'%file)
        try: 
            return self.sortProgrammes(xmltv.read_programmes(FileAccess.open(file, 'r')) or [])
        except Exception as e: 
            if 'no element found: line 1, column 0' in str(e): return [] #new file error
            self.log('loadProgrammes, failed! %s'%(e), xbmc.LOGWARNING)
            return []

            
    def loadStopTimes(self, channels=None, programmes=None, fallback=None):
        if channels   is None: channels   = self.getChannels()
        if programmes is None: programmes = self.getProgrammes()
        if fallback   is None: fallback   = datetime.datetime.fromtimestamp(roundTimeDown(getLocalTime(),offset=60)).strftime(DTFORMAT)
            
        for channel in channels:
            try: 
                stopString = max([program['stop'] for program in programmes if program['channel'] == channel['id']], default=fallback)
                self.log('loadStopTimes, channel = %s, stopString = %s'%(channel['id'],stopString))
                yield channel['id'],datetime.datetime.timestamp(strpTime(stopString, DTFORMAT))
            except Exception as e:
                self.log("loadStopTimes, failed!\n%s\nRemoving malformed XMLTV channel/programmes %s"%(e,channel.get('id')), xbmc.LOGWARNING)
                # self.removeBroadcasts(channel) #something went wrong; remove existing xmltv; force fresh rebuild.
                yield channel['id'],datetime.datetime.timestamp(strpTime(fallback, DTFORMAT))
                
                
    def getChannels(self):
        self.log('getChannels')
        return self.sortChannels(self.XMLTVDATA.get('channels',[]))


    def getProgrammes(self):
        self.log('getProgrammes')
        return self.sortProgrammes(self.XMLTVDATA.get('programmes',[]))


    def resetData(self):
        self.log('resetData')
        return {'date'                : datetime.datetime.fromtimestamp(float(time.time())).strftime(DTFORMAT),
                'generator-info-name' : self.cleanString('%s Guidedata'%(ADDON_NAME)),
                'generator-info-url'  : self.cleanString(ADDON_ID),
                'source-info-name'    : self.cleanString(ADDON_NAME),
                'source-info-url'     : self.cleanString(ADDON_ID)}


    def cleanString(self, text):
        if text == ', ' or not text: text = LANGUAGE(32020) #"Unavailable"
        return bytes(text,DEFAULT_ENCODING).decode(DEFAULT_ENCODING,'ignore')

             
    def cleanSelf(self, items, key='id', slug='@%s'%(slugify(ADDON_NAME))): # remove imports (Non PseudoTV Live), key = {'id':channels,'channel':programmes}
        self.log('cleanSelf, key = %s'%(key))
        if not slug: return items
        return (list(filter(lambda item:item.get(key,'').endswith(slug), items)))
        
        
    def cleanChannels(self, channels, programmes): # remove stations with no guidedata
        stations    = list(set([program.get('channel') for program in programmes]))
        tmpChannels = [channel for station in stations for channel in channels if channel.get('id') == station]
        self.log('cleanChannels, before = %s, after = %s'%(len(channels),len(tmpChannels)))
        return tmpChannels
        
        
    def cleanProgrammes(self, programmes): # remove expired content
        try:
            now = (datetime.datetime.fromtimestamp(float(getLocalTime()))) - datetime.timedelta(days=SETTINGS.getSettingInt('Min_Days')) #allow some old programmes to avoid empty cells.
            tmpProgrammes = [program for program in programmes if strpTime(program['stop'].rstrip(),DTFORMAT) > now]
        except Exception as e: 
            self.log("cleanProgrammes, Failed! %s"%(e), xbmc.LOGERROR)
            tmpProgrammes = programmes
        self.log('cleanProgrammes, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
        return tmpProgrammes


    def cleanLogo(self, logo):
        if not logo.startswith(('image://','resource://','special://')):
            realPath = xbmcvfs.translatePath('special://home/addons/')
            if logo.startswith(realPath):# convert real path. to vfs
                logo = logo.replace(realPath,'special://home/addons/').replace('\\','/')
            elif logo.startswith(realPath.replace('\\','/')):
                logo = logo.replace(realPath.replace('\\','/'),'special://home/addons/').replace('\\','/')
            # else:# convert local art to webserver for clients.
                # logo = self.buildWebImage(logo) #todo m3u/xmltv logos use 'server' instance hosted images
            self.log('cleanLogo, logo Out = %s'%(logo))
        return logo
               
               
    def sortChannels(self, channels):
        try: channels.sort(key=lambda x:x.get('display-name'))
        except: pass
        return channels


    def sortProgrammes(self, programmes):
        programmes.sort(key=lambda x:x['start'])
        programmes.sort(key=lambda x:x['channel'])
        self.log('sortProgrammes, programmes = %s'%(len(programmes)))
        return programmes


    def findChannel(self, item, channels=[]):
        for idx, eitem in enumerate(channels):
            if (item.get('id') == eitem.get('id',str(random.random()))) or (item.get('type','').lower() == eitem.get('type',str(random.random())).lower() and item.get('name','').lower() == eitem.get('name',str(random.random())).lower()):
                self.log('findChannel, found item = %s'%(eitem))
                return idx, eitem
        return None, {}
        
        
    def addChannel(self, citem):
        mitem = ({'id'           : citem['id'],
                  'display-name' : [(self.cleanString(citem['name']), LANG)],
                  'icon'         : [{'src':self.cleanLogo(citem['logo'])}]})
                  
        self.log('addChannel, mitem = %s'%(mitem))
        idx, channel = self.findChannel(mitem, channels=self.getChannels())
        if idx is None: 
            self.XMLTVDATA['channels'].append(mitem)
        else: 
            self.XMLTVDATA['channels'][idx] = mitem # replace existing channel meta
        return True


    def addProgram(self, id, item):
        pitem      = {'channel'     : id,
                      'credits'     : {'writer':[encodeWriter(self.cleanString(item['writer']),item['fitem'])]},
                      'category'    : [(self.cleanString(genre.replace('Unknown','Undefined')),LANG) for genre in item['categories']],
                      'title'       : [(self.cleanString(item['title']), LANG)],
                      'desc'        : [(self.cleanString(item['desc']), LANG)],
                      'stop'        : (datetime.datetime.fromtimestamp(float(item['stop'])).strftime(DTFORMAT)),
                      'start'       : (datetime.datetime.fromtimestamp(float(item['start'])).strftime(DTFORMAT)),
                      'icon'        : [{'src': self.cleanLogo(item['thumb'])}],
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
        self.XMLTVDATA['programmes'].append(pitem)
        return True

    
    def delBroadcast(self, citem):# remove single channel and all programmes from XMLTVDATA
        channels   = self.XMLTVDATA['channels'].copy()
        programmes = self.XMLTVDATA['programmes'].copy()
        self.XMLTVDATA['channels']   = list(filter(lambda channel:channel.get('id') != citem.get('id'), channels))
        self.XMLTVDATA['programmes'] = list(filter(lambda program:program.get('channel') != citem.get('id'), programmes))
        self.log('delBroadcast, removing channel %s; channels: before = %s, after = %s; programmes: before = %s, after = %s'%(citem.get('id'),len(channels),len(self.XMLTVDATA['channels']),len(programmes),len(self.XMLTVDATA['programmes'])))
        return True
        
        
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
                    setURL(url,file)
            else:
                files = [file]
                
            for file in files:
                importChannels, importProgrammes = [],[]
                channels, programmes = self.loadChannels(file), self.loadProgrammes(file)
                
                if m3uChannels: #filter imported programmes by m3uchannels list.
                    poolit(matchChannel)(m3uChannels, **{'channels':channels,'programmes':programmes})
                else: #no filter, import everything!
                    importChannels   = channels
                    importProgrammes = programmes
                    
                importChannels, importProgrammes = self.chkImport(importChannels, importProgrammes)
                self.log('importXMLTV, found importChannels = %s, importProgrammes = %s from %s'%(len(importChannels),len(importProgrammes),file))
                self.XMLTVDATA.get('channels',[]).extend(self.sortChannels(importChannels))
                self.XMLTVDATA.get('programmes',[]).extend(self.sortProgrammes(importProgrammes))
        except Exception as e: self.log("importXMLTV, failed! %s"%(e), xbmc.LOGERROR)
        return True


    def chkImport(self, channels, programmes): # parse for empty programmes, inject single cell entry.
        try:
            def addSingleEntry(channel, start=None, length=10800): #create a single entry with min. channel meta, use as a filler.
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

            def chkPrograms(channel):
                for program in programmes:
                    if channel.get('id') == program.get('channel'):
                        try:    return tmpChannels.remove(channel)
                        except: continue
                          
            tmpChannels = channels.copy() 
            poolit(chkPrograms)(channels)
            for channel in tmpChannels: programmes.append(addSingleEntry(channel)) #append single cell entry for channels missing programmes
            self.log("chkImport, added %s single entries"%(len(tmpChannels)))
        except Exception as e: 
            self.log("chkImport, failed! %s"%(e), xbmc.LOGERROR)
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
                matchGenres(self.XMLTVDATA.get('programmes',[]))
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
                    
                with fileLocker(GLOBAL_FILELOCK):
                    try:
                        xmlData = FileAccess.open(GENREFLEPATH, "w")
                        xmlData.write(doc.toprettyxml(indent='\t'))
                        xmlData.close()
                    except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)
                    return True
            except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)

