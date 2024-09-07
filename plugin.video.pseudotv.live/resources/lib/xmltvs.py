#   Copyright (C) 2024 Lunatixz
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
from globals    import *
from seasonal   import Seasonal 

#todo check for empty recordings/channel meta and trigger refresh/rebuild empty xmltv via Kodi json rpc?

class XMLTVS:
        
    def __init__(self):   
        self.XMLTVDATA = self._load()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _load(self, file: str=XMLTVFLEPATH) -> dict:
        self.log('_load')
        channels, recordings = self.cleanSelf(self.loadChannels(file),'id')
        return {'data'       : self.loadData(file),
                'channels'   : channels,
                'recordings' : recordings,
                'programmes' : self.cleanSelf(self.loadProgrammes(file),'channel')}


    def _save(self, file: str=XMLTVFLEPATH, reset: bool=True) -> bool:
        self.log('_save')
        if reset: data = self.resetData()
        else:     data = self.XMLTVDATA['data']
            
        with FileLock():
            writer = xmltv.Writer(encoding            = DEFAULT_ENCODING, 
                                  date                = data['date'],
                                  source_info_url     = self.cleanString(data['source-info-url']), 
                                  source_info_name    = self.cleanString(data['source-info-name']),
                                  generator_info_url  = self.cleanString(data['generator-info-url']), 
                                  generator_info_name = self.cleanString(data['generator-info-name']))

            self.XMLTVDATA['programmes'] = self.sortProgrammes(self.XMLTVDATA['programmes'])
            self.XMLTVDATA['channels']   = self.cleanChannels(self.sortChannels(self.XMLTVDATA['channels'])  , self.XMLTVDATA['programmes'])
            self.XMLTVDATA['recordings'] = self.cleanChannels(self.sortChannels(self.XMLTVDATA['recordings']), self.XMLTVDATA['programmes'])
            
            for channel in (self.XMLTVDATA['recordings'] + self.XMLTVDATA['channels']):
                writer.addChannel(channel)
            for program in self.XMLTVDATA['programmes']:
                writer.addProgramme(program)
            
            try:
                self.log('_save, saving to %s'%(file))
                fle = FileAccess.open(file, "w")
                writer.write(fle, pretty_print=True)
                fle.close()
            except Exception as e:
                self.log("_save, failed!", xbmc.LOGERROR)
                DIALOG.notificationDialog(LANGUAGE(32000))
            self.buildGenres()
        return self._reload()
        
        
    def _reload(self) -> bool:
        self.log('_reload') 
        self.__init__()
        return True
    
    
    def _error(self, name, file, e):
        #hacky; try to log malformed xml's by printing error position..
        if not 'no element found: line 1, column 0' in str(e):
            try:
                match = re.compile('line\ (.*?),\ column\ (.*)', re.IGNORECASE).search(str(e))
                if match: 
                    fle  = FileAccess.open(file,'r')
                    file = fle.readlines()
                    fle.close()
                    self.log('%s, failed! parser error %s\nLine: %s\n Error: %s'%(name,e,file[int(match.group(1))],file[int(match.group(1))][int(match.group(2))-5:]), xbmc.LOGERROR)
                else: raise Exception('no parser match %s'%(str(e)))
            except Exception as en: self.log('%s, failed! %s\n%s'%(name,e,en), xbmc.LOGERROR)
    
    
    def loadData(self, file: str=XMLTVFLEPATH) -> dict:
        self.log('loadData, file = %s'%file)
        try: 
            fle  = FileAccess.open(file, 'r')
            data = (xmltv.read_data(fle) or self.resetData())
            fle.close()
            return data
        except Exception as e:
            self._error('loadData',file,e)
            return self.resetData()


    def loadChannels(self, file: str=XMLTVFLEPATH) -> list:
        self.log('loadChannels, file = %s'%file)
        try:
            fle  = FileAccess.open(file, 'r')
            data = (xmltv.read_channels(fle) or [])
            fle.close()
            return data
        except Exception as e:
            self._error('loadChannels',file,e)
            return []
        
        
    def loadProgrammes(self, file: str=XMLTVFLEPATH) -> list:
        self.log('loadProgrammes, file = %s'%file)
        try: 
            fle  = FileAccess.open(file, 'r')
            data = self.sortProgrammes(xmltv.read_programmes(fle) or [])
            fle.close()
            return data
        except Exception as e: 
            self._error('loadProgrammes',file,e)
            return []

            
    def loadStopTimes(self, channels: list=[], programmes: list=[], fallback=None):
        if not channels:   channels   = self.getChannels()
        if not programmes: programmes = self.getProgrammes()
        if not fallback:   fallback   = datetime.datetime.fromtimestamp(roundTimeDown(getUTCstamp(),offset=60)).strftime(DTFORMAT)
        
        for channel in channels:
            try: 
                firstStart = min([program['start'] for program in programmes if program['channel'] == channel['id']], default=fallback)
                lastStop   = max([program['stop']  for program in programmes if program['channel'] == channel['id']], default=fallback)
                self.log('loadStopTimes, channel = %s, first-start = %s, last-stop = %s, fallback = %s'%(channel['id'],firstStart,lastStop,fallback))
                if firstStart > fallback: raise Exception('First start-time in the future, rebuild channel with fallback')
                yield channel['id'],datetime.datetime.timestamp(strpTime(lastStop, DTFORMAT))
            except Exception as e:
                self.log("loadStopTimes, channel = %s failed!\nMalformed XMLTV channel/programmes %s! rebuilding channel with default stop-time %s"%(channel.get('id'),e,fallback), xbmc.LOGWARNING)
                yield channel['id'],datetime.datetime.timestamp(strpTime(fallback, DTFORMAT))
             
             
    def getRecordings(self) -> list:
        self.log('getRecordings')
        return self.sortChannels(self.XMLTVDATA.get('recordings',[]))
                
                
    def getChannels(self) -> list:
        self.log('getChannels')
        return self.sortChannels(self.XMLTVDATA.get('channels',[]))
        
        
    def getProgrammes(self) -> list:
        self.log('getProgrammes')
        return self.sortProgrammes(self.XMLTVDATA.get('programmes',[]))


    def resetData(self):
        self.log('resetData')
        return {'date'                : datetime.datetime.fromtimestamp(float(time.time())).strftime(DTFORMAT),
                'generator-info-name' : self.cleanString('%s Guidedata'%(ADDON_NAME)),
                'generator-info-url'  : self.cleanString(ADDON_ID),
                'source-info-name'    : self.cleanString(ADDON_NAME),
                'source-info-url'     : self.cleanString(ADDON_ID)}


    def cleanString(self, text: str) -> str:
        if text == ', ' or not text: text = LANGUAGE(32020) #"Unavailable"
        return bytes(text,DEFAULT_ENCODING).decode(DEFAULT_ENCODING,'ignore')

             
    def cleanSelf(self, items: list, key: str='id', slug: str='@%s'%(slugify(ADDON_NAME))) -> list: # remove imports (Non PseudoTV Live), key = {'id':channels,'channel':programmes}
        if not slug: return items
        channels   = list([item for item in items if item.get(key,'').endswith(slug) and len(item.get(key,'').replace(slug,'')) == 32])
        recordings = list([item for item in items if item.get(key,'').endswith(slug) and len(item.get(key,'').replace(slug,'')) == 16])
        if key == 'id':
            self.log('cleanSelf, slug = %s, key = %s: returning channels = %s, recordings = %s'%(slug,key,len(channels),len(recordings)))
            return self.sortChannels(channels), self.sortChannels(recordings)
        else:
            programmes = self.cleanProgrammes(channels) + recordings
            self.log('cleanSelf, slug = %s, key = %s: returning programmes = %s'%(slug,key,len(programmes)))
            return self.sortProgrammes(programmes)
        
        
    def cleanChannels(self, channels: list, programmes: list) -> list: # remove stations with no guidedata
        stations    = list(set([program.get('channel') for program in programmes]))
        tmpChannels = [channel for station in stations for channel in channels if channel.get('id') == station]
        self.log('cleanChannels, before = %s, after = %s'%(len(channels),len(tmpChannels)))
        return tmpChannels


    def cleanProgrammes(self, programmes: list) -> list:
        now = (datetime.datetime.fromtimestamp(float(getUTCstamp())) - datetime.timedelta(days=MIN_GUIDEDAYS)) #allow some old programmes to avoid empty cells.
        def filterProgrames(program):
            if (strpTime(program.get('stop',now).rstrip(),DTFORMAT) > now): return program
            
        tmpProgrammes = [filterProgrames(program) for program in programmes] # remove expired content, ignore "recordings" ie. media=True
        self.log('cleanProgrammes, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
        return self.cleanHolidays(tmpProgrammes)


    def cleanHolidays(self, programmes: list=[]) -> list:
        holiday = Seasonal().getHoliday()
        def filterHoliday(program):
            citem = decodePlot(program.get('desc',([{}],''))[0][0]).get('citem',{})
            if citem.get('holiday') and citem.get('holiday',{}).get('name',str(random.random())) != holiday.get('name',str(random.random())): return None
            return program
            
        tmpProgrammes = [filterHoliday(program) for program in programmes if program] # remove expired seasons.
        self.log('cleanHolidays, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
        return tmpProgrammes


    def sortChannels(self, channels: list) -> list:
        return sorted(channels, key=itemgetter('display-name'))


    def sortProgrammes(self, programmes: list) -> list:
        programmes.sort(key=itemgetter('start'))
        programmes.sort(key=itemgetter('channel'))
        self.log('sortProgrammes, programmes = %s'%(len(programmes)))
        return programmes


    def findChannel(self, citem: dict, channels: list=[]) -> tuple:
        if not channels: channels = self.getChannels()
        for idx, eitem in enumerate(channels):
            if citem.get('id') == eitem.get('id',str(random.random())):
                self.log('findChannel, found citem = %s'%(eitem))
                return idx, eitem
        return None, {}
        
        
    def findRecording(self, ritem: dict, recordings: list=[]) -> tuple:
        if not recordings: recordings = self.getRecordings()
        for idx, eitem in enumerate(recordings):
            if (ritem.get('id') == eitem.get('id',str(random.random())) or ritem.get('label').lower() == eitem.get('display-name')[0][0].lower()):
                self.log('findRecording, found ritem = %s'%(eitem))
                return idx, eitem
        return None, {}
        
        
    def addRecording(self, ritem: dict, fitem: dict):
        self.log('addRecording = %s'%(ritem.get('id')))
        sitem = ({'id'           : ritem['id'],
                  'display-name' : [(self.cleanString(ritem['name']), LANG)],
                  'icon'         : [{'src':ritem['logo']}]})
                  
        self.log('addRecording, sitem = %s'%(sitem))
        idx, recording = self.findRecording(ritem)
        if idx is None: 
            self.XMLTVDATA['recordings'].append(sitem)
        else: 
            self.XMLTVDATA['recordings'][idx] = sitem # replace existing channel meta

        fitem['start'] = getUTCstamp()
        fitem['stop']  = fitem['start'] + fitem['duration']
        if self.addProgram(ritem['id'],self.getProgramItem(ritem,fitem),encodeDESC=False):
            return self._save()
        
    
    def addChannel(self, citem: dict) -> bool:
        mitem = ({'id'           : citem['id'],
                  'display-name' : [(self.cleanString(citem['name']), LANG)],
                  'icon'         : [{'src':citem['logo']}]})
                  
        self.log('addChannel, mitem = %s'%(mitem))
        idx, channel = self.findChannel(mitem)
        if idx is None: 
            self.XMLTVDATA['channels'].append(mitem)
        else: 
            self.XMLTVDATA['channels'][idx] = mitem # replace existing channel meta
        return True


    def addProgram(self, id: str, item: dict, encodeDESC: bool=True) -> bool:
        pitem = {'channel'     : id,
                 'category'    : [(self.cleanString(genre.replace('Unknown','Undefined')),LANG) for genre in item['categories']],
                 'title'       : [(self.cleanString(item['title']), LANG)],
                 'desc'        : [(encodePlot(self.cleanString(item['desc']),item['fitem']), LANG) if encodeDESC else (self.cleanString(item['desc']), LANG)],
                 'stop'        : (datetime.datetime.fromtimestamp(float(item['stop'])).strftime(DTFORMAT)),
                 'start'       : (datetime.datetime.fromtimestamp(float(item['start'])).strftime(DTFORMAT)),
                 'icon'        : [{'src': item['thumb']}],
                 'length'      : {'units': 'seconds', 'length': str(item['length'])}}
                        
        if item.get('sub-title'):
            pitem['sub-title'] = [(self.cleanString(item['sub-title']), LANG)]

        if item.get('stars'):
            pitem['star-rating'] = [{'value': '%s/10'%(int(round(float(item['stars']))))}]
 
        if item.get('writer'):
            pitem.setdefault('credits',{})['writer'] = [self.cleanString(writer) for writer in item['writer']]
            
        if item.get('director'):
            pitem.setdefault('credits',{})['director'] = [self.cleanString(director) for director in item['director']]
            
        if item.get('actor'):
            pitem.setdefault('credits',{})['actor'] = [self.cleanString(actor) for actor in item['actor']]

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

    
    def delBroadcast(self, citem: dict) -> bool:# remove single channel and all programmes from XMLTVDATA
        channels   = self.XMLTVDATA['channels'].copy()
        programmes = self.XMLTVDATA['programmes'].copy()
        self.XMLTVDATA['channels']   = list([channel for channel in channels if channel.get('id') != citem.get('id')])
        self.XMLTVDATA['programmes'] = list([program for program in programmes if program.get('channel') != citem.get('id')])
        self.log('delBroadcast, removing channel %s; channels: before = %s, after = %s; programmes: before = %s, after = %s'%(citem.get('id'),len(channels),len(self.XMLTVDATA['channels']),len(programmes),len(self.XMLTVDATA['programmes'])))
        return True
        
        
    def delRecording(self, ritem: dict):
        self.log('delRecording id = %s'%((ritem.get('id') or ritem.get('label'))))
        recordings = self.XMLTVDATA['recordings'].copy()
        programmes = self.XMLTVDATA['programmes'].copy()
        idx, recording = self.findRecording(ritem)
        if idx is not None:
            self.XMLTVDATA['recordings'].pop(idx)
            if not ritem.get('id'): ritem['id'] = recording['id']
            self.XMLTVDATA['programmes'] = list([program for program in programmes if program.get('channel') != ritem.get('id')])
            return self._save()
        

    def importXMLTV(self, file: str, m3uChannels: dict={}):
        self.log('importXMLTV, file = %s, m3uChannels = %s'%(file,len(m3uChannels)))
        def matchChannel(channel, channels, programmes):
            importChannels.extend(list([chan for chan in channels if chan.get('id') == channel.get('id')]))
            importProgrammes.extend(list([prog for prog in programmes if prog.get('channel') == channel.get('id')]))

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


    def chkImport(self, channels: list, programmes: list) -> tuple: # parse for empty programmes, inject single cell entry.
        try:
            def addSingleEntry(channel, start=None, length=10800): #create a single entry with min. channel meta, use as a filler.
                if start is None: start = datetime.datetime.fromtimestamp(roundTimeDown(getUTCstamp(),offset=60))
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
        self.log('buildGenres') #todo custom user color selector.
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
                fle = FileAccess.open(GENREFLE_DEFAULT, "r")
                dom = parse(fle)
                fle.close()
                epggenres = parseGenres(dom.getElementsByTagName('genre'))
                matchGenres(self.XMLTVDATA.get('programmes',[]))
                epggenres = dict(sorted(sorted(list(epggenres.items()), key=lambda v:v[1]['name']), key=lambda v:v[1]['genreId']))
                
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
                    
                try:
                    with FileLock():
                        xmlData = FileAccess.open(GENREFLEPATH, "w")
                        xmlData.write(doc.toprettyxml(indent='  ',encoding=DEFAULT_ENCODING))
                        xmlData.close()
                except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)
            except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)


    def getProgramItem(self, citem: dict, fItem: dict) -> dict:
        ''' Convert fileItem to Programme (XMLTV) item '''
        item = {}
        item['channel']       = citem['id']
        item['radio']         = citem['radio']
        item['start']         = fItem['start']
        item['stop']          = fItem['stop']
        item['title']         = fItem['label']
        item['desc']          = fItem['plot']
        item['length']        = fItem['duration']
        item['sub-title']     = (fItem.get('episodetitle','') or '')
        item['categories']    = (fItem.get('genre','')        or ['Undefined'])[:5]
        item['type']          = fItem.get('type','video')
        item['new']           = int(fItem.get('playcount','1')) == 0
        item['thumb']         = cleanImage(getThumb(fItem,EPG_ARTWORK)) #unify thumbnail by user preference 
        fItem.get('art',{})['thumb'] = getThumb(fItem,{0:1,1:0}[EPG_ARTWORK])  #unify thumbnail artwork, opposite of EPG_Artwork
        item['date']          = fItem.get('premiered','')
        item['catchup-id']    = VOD_URL.format(addon=ADDON_ID,title=quoteString(item['title']),chid=quoteString(citem['id']),vid=quoteString(encodeString((fItem.get('originalfile') or fItem.get('file','')))))
        fItem['catchup-id']   = item['catchup-id']
            
        if (item['type'] != 'movie' and ((fItem.get("season",0) > 0) and (fItem.get("episode",0) > 0))):
            item['episode-num'] = {'xmltv_ns':'%s.%s'%(fItem.get("season",1)-1,fItem.get("episode",1)-1), # todo support totaleps <episode-num system="xmltv_ns">..44/47</episode-num>https://github.com/kodi-pvr/pvr.iptvsimple/pull/884
                                   'onscreen':'S%sE%s'%(str(fItem.get("season",0)).zfill(2),str(fItem.get("episode",0)).zfill(2))}

        item['rating']      = cleanMPAA(fItem.get('mpaa','') or 'NA')
        item['stars']       = (fItem.get('rating','')        or '0')
        item['writer']      = fItem.get('writer',[])[:5]   #trim list to five
        item['director']    = fItem.get('director',[])[:5] #trim list to five
        item['actor']       = ['%s - %s'%(actor.get('name'),actor.get('role',LANGUAGE(32020))) for actor in fItem.get('cast',[])[:5] if actor.get('name')]
        
        fItem['citem']      = citem #channel item (stale data due to xmltv storage) use for reference
        item['fitem']       = fItem #raw kodi fileitem/listitem, contains citem both passed through 'plot' xmltv param.
        
        streamdetails = fItem.get('streamdetails',{})
        if streamdetails:
            item['subtitle'] = list(set([sub.get('language','')                    for sub in streamdetails.get('subtitle',[]) if sub.get('language')]))
            item['language'] = ', '.join(list(set([aud.get('language','')          for aud in streamdetails.get('audio',[])    if aud.get('language')])))
            item['audio']    = True if True in list(set([aud.get('codec','')       for aud in streamdetails.get('audio',[])    if aud.get('channels',0) >= 2])) else False
            item.setdefault('video',{})['aspect'] = list(set([vid.get('aspect','') for vid in streamdetails.get('video',[])    if vid.get('aspect','')]))
        return item