#   Copyright (C) 2025 Lunatixz
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

from globals     import *
from seasonal    import Seasonal
from fileaccess  import FileAccess, FileLock

#todo check for empty recordings/channel meta and trigger refresh/rebuild empty xmltv via Kodi json rpc?

class XMLTVS(object):
    xmltv_lock = Lock()
    
    def __init__(self, file=XMLTVFLEPATH, writable=False):
        self.writable  = writable
        self.XMLTVFile = file
        self.XMLTVDATA = self._load()
        self.stopTimes = dict(self.loadStopTimes())


    def __del__(self):
        self.log('__del__, writable = %s'%(self.writable))
        if writable: self._save()
            
            
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _load(self) -> dict:
        self.log('_load')
        channels, recordings = self.cleanSelf(self.loadChannels(),'id')
        return {'data'       : self.loadData(),
                'channels'   : channels,
                'recordings' : recordings,
                'programmes' : self.cleanSelf(self.loadProgrammes(),'channel')}


    @debounceit(SERVICE_INTERVAL)
    def _save(self, reset: bool=True) -> bool:
        with PROPERTIES.interruptActivity(), self.xmltv_lock:
            if reset: data = self.resetData()
            else:     data = self.XMLTVDATA['data']
                
            self.XMLTVDATA['programmes'] = self.sortProgrammes(self.XMLTVDATA['programmes'])
            self.XMLTVDATA['channels']   = self.cleanChannels(self.sortChannels(self.XMLTVDATA['channels'])  , self.XMLTVDATA['programmes'], opt='PROGRAMMES')
            self.XMLTVDATA['recordings'] = self.cleanChannels(self.sortChannels(self.XMLTVDATA['recordings']), self.XMLTVDATA['programmes'], opt='RECORDINGS')
            self.log('_save, writable = %s, file = %s, reset = %s\nchannels = %s, programmes = %s, recordings = %s'%(self.writable,self.XMLTVFile,reset,len(self.XMLTVDATA['channels']),len(self.XMLTVDATA['programmes']),len(self.XMLTVDATA['recordings'])))
            
            if self.writable:
                writer = xmltv.Writer(encoding            = DEFAULT_ENCODING, 
                                      date                = data['date'],
                                      source_info_url     = self.cleanString(data['source-info-url']), 
                                      source_info_name    = self.cleanString(data['source-info-name']),
                                      generator_info_url  = self.cleanString(data['generator-info-url']), 
                                      generator_info_name = self.cleanString(data['generator-info-name']))

                for channel in (self.XMLTVDATA['recordings'] + self.XMLTVDATA['channels']):
                    writer.addChannel(channel)
                    
                for program in self.XMLTVDATA['programmes']:
                    writer.addProgramme(program)
                try:
                    with FileLock(self.XMLTVFile):
                        try:
                            fle = FileAccess.open(self.XMLTVFile, "w")
                            writer.write(fle, pretty_print=True)
                        except Exception as e: self.log("_save, failed!", xbmc.LOGERROR)
                        finally: 
                            if hasattr(fle, 'close'): 
                                fle.close()
                except Exception as e:
                    self.log("_save, failed!", xbmc.LOGERROR)
                    DIALOG.notificationDialog(LANGUAGE(32000))
                return self.buildGenres()
        
        
    def _reload(self) -> bool:
        self.log('_reload') 
        self.__init__()
    
    
    def _error(self, name, e):
        #hacky; try to log malformed xml's by printing error position..
        if not 'no element found: line 1, column 0' in str(e):
            try:
                match = re.compile(r'line\ (.*?),\ column\ (.*)', re.IGNORECASE).search(str(e))
                if match:
                    try: 
                        fle   = FileAccess.open(self.XMLTVFile,'r')
                        return fle.readlines()
                    except Exception: 
                        self.log('%s, failed! parser error %s\nLine: %s\n Error: %s'%(name,e,lines[int(match.group(1))],lines[int(match.group(1))][int(match.group(2))-5:]), xbmc.LOGERROR)
                        return
                    finally:
                        if hasattr(fle, 'close'): 
                            fle.close()
                else: raise Exception('no parser match %s'%(str(e)))
            except Exception as en: self.log('%s, failed! %s\n%s'%(name,e,en), xbmc.LOGERROR)
    
                
    def resetData(self):
        self.log('resetData')
        return {'date'                : epochTime(float(time.time()),tz=False).strftime(DTFORMAT),
                'generator-info-name' : self.cleanString('%s Guidedata'%(ADDON_NAME)),
                'generator-info-url'  : self.cleanString(ADDON_ID),
                'source-info-name'    : self.cleanString(ADDON_NAME),
                'source-info-url'     : self.cleanString(ADDON_ID)}


    def loadData(self) -> dict:
        self.log('loadData, file = %s'%self.XMLTVFile)
        try:
            data = self.resetData()
            try: 
                fle  = FileAccess.open(self.XMLTVFile, 'r')
                return (xmltv.read_data(fle) or data)
            except: pass
            finally:
                if hasattr(fle, 'close'): 
                    fle.close()
        except Exception as e:
            self._error('loadData',self.XMLTVFile,e)
            return data


    def loadChannels(self) -> list:
        self.log('loadChannels, file = %s'%self.XMLTVFile)
        try:
            try: 
                fle  = FileAccess.open(self.XMLTVFile, 'r')
                return (xmltv.read_channels(fle) or [])
            except Exception: pass
            finally:
                if hasattr(fle, 'close'): 
                    fle.close()
        except Exception as e:
            self._error('loadChannels',self.XMLTVFile,e)
            return []
        
        
    def loadProgrammes(self) -> list:
        self.log('loadProgrammes, file = %s'%self.XMLTVFile)
        try: 
            try: 
                fle = FileAccess.open(self.XMLTVFile, 'r')
                return (xmltv.read_programmes(fle) or [])
            except Exception: pass
            finally:
                if hasattr(fle, 'close'): 
                    fle.close()
        except Exception as e: 
            self._error('loadProgrammes',self.XMLTVFile,e)
            return []

            
    def loadStopTimes(self, channels: list=[], programmes: list=[], fallback=None):
        if not channels:   channels   = self.getChannels()
        if not programmes: programmes = self.getProgrammes()
        if not fallback:   fallback   = epochTime(roundTimeDown(getUTCstamp(),offset=60),tz=False).strftime(DTFORMAT)
        
        for channel in channels:
            try: 
                firstStart = min((program['start'] for program in programmes if program['channel'] == channel['id']), default=fallback)
                lastStop   = max((program['stop']  for program in programmes if program['channel'] == channel['id']), default=fallback)
                self.log('loadStopTimes [%s] first-start = %s, last-stop = %s, fallback = %s'%(channel['id'],firstStart,lastStop,fallback))
                if firstStart > fallback: raise Exception('First start-time in the future, rebuild channel with fallback')
                yield channel['id'],datetime.datetime.timestamp(strpTime(lastStop, DTFORMAT))
            except Exception as e:
                self.log("loadStopTimes [%s] failed!\nMalformed XMLTV channel/programmes %s! rebuilding channel with default stop-time %s"%(channel.get('id'),e,fallback), xbmc.LOGWARNING)
                yield channel['id'],datetime.datetime.timestamp(strpTime(fallback, DTFORMAT))


    def hasProgrammes(self, channels: list=[], programmes: list=[], now=None):
        if not channels:   channels   = self.getChannels()
        if not programmes: programmes = self.getProgrammes()
        if not now: now = epochTime(roundTimeDown(getUTCstamp(),offset=60),tz=False).strftime(DTFORMAT)
        
        for channel in channels:
            try: 
                valid = False
                lastStop  = max((program['stop']  for program in programmes if program['channel'] == channel['id']), default=now)
                if lastStop > now: valid = True
                self.log('hasProgrammes, channel = %s, valid = %s'%(channel['id'],valid))
                yield channel['id'],valid
            except Exception as e:
                self.log("hasProgrammes, channel = %s failed!\nMalformed XMLTV channel/programmes %s! valid = False %s"%(channel.get('id'),e), xbmc.LOGWARNING)
                yield channel['id'],False


    def cleanString(self, text: str) -> str:
        if text == ', ' or not text: text = LANGUAGE(32020) #"Unavailable"
        return bytes(text,DEFAULT_ENCODING).decode(DEFAULT_ENCODING,'ignore')

             
    def cleanSelf(self, items: list, key: str='id', slug: str='@%s'%(Globals._slugify(ADDON_NAME))) -> list: # remove (Non PseudoTV Live), key = {'id':channels,'channel':programmes}
        if not slug: return items
        channels   = list([item for item in items if item.get(key,'').endswith(slug) and len(item.get(key,'').replace(slug,'')) == 32])
        recordings = list([item for item in items if item.get(key,'').endswith(slug) and len(item.get(key,'').replace(slug,'')) == 16])
        if key == 'id': #stations
            self.log('cleanSelf, slug = %s, key = %s: returning channels = %s, recordings = %s'%(slug,key,len(channels),len(recordings)))
            return self.sortChannels(Globals._setDictLST(channels)), self.sortChannels(Globals._setDictLST(recordings))
        else: #programmes
            programmes = self.cleanProgrammes(channels) + recordings
            self.log('cleanSelf, slug = %s, key = %s: returning programmes = %s'%(slug,key,len(programmes)))
            return self.sortProgrammes(programmes)
        
        
    def cleanChannels(self, channels: list, programmes: list, opt='PROGRAMMES') -> list: # remove stations with no guidedata
        stations    = list(set([program.get('channel') for program in programmes]))
        tmpChannels = [channel for station in stations for channel in channels if channel.get('id') == station]
        self.log('cleanChannels [%s], before = %s, after = %s'%(opt,len(channels),len(tmpChannels)))
        return tmpChannels


    def cleanProgrammes(self, programmes: list) -> list:
        now = (epochTime(float(getUTCstamp()),tz=False) - datetime.timedelta(days=MIN_GUIDEDAYS)) #allow some old programmes to avoid empty cells
        holiday = Seasonal().getHoliday()
        
        def __filterProgrammes(program):
            citem = Globals._decodePlot(program.get('desc',([{}],''))[0][0]).get('citem',{})
            if citem.get('holiday') and citem.get('holiday',{}).get('name',str(random.random())) != holiday.get('name',str(random.random())): return None
            elif (strpTime(program.get('stop',now).rstrip(),DTFORMAT) < now): return None  # remove expired content, ignore "recordings" ie. media=True
            return program
            
        tmpProgrammes = [program for program in [__filterProgrammes(program) for program in programmes] if program is not None]
        self.log('cleanProgrammes, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
        return tmpProgrammes


    def sortChannels(self, channels: list) -> list:
        try:    return sorted(channels, key=itemgetter('display-name'))
        except Exception: return channels
        

    def sortProgrammes(self, programmes: list) -> list:
        try:
            programmes.sort(key=itemgetter('start'))
            programmes.sort(key=itemgetter('channel'))
            self.log('sortProgrammes, programmes = %s'%(len(programmes)))
            return programmes
        except Exception as e:
            self.log("sortProgrammes, failed! %s"%(e), xbmc.LOGERROR)
            return []


    def getRecordings(self) -> list:
        self.log('getRecordings')
        return self.sortChannels(self.XMLTVDATA.get('recordings',[]))
                
                
    def getChannels(self) -> list:
        self.log('getChannels')
        return self.sortChannels(self.XMLTVDATA.get('channels',[]))
        
        
    def getProgrammes(self) -> list:
        self.log('getProgrammes')
        return self.sortProgrammes(self.XMLTVDATA.get('programmes',[]))


    def findChannel(self, citem: dict, channels: list=[]) -> tuple:
        if not channels: channels = self.getChannels()
        return tuple(next(((idx, eitem) for idx, eitem in enumerate(channels) if citem.get('id') == eitem.get('id',str(random.random()))),(None, {})))
        
        
    def findRecording(self, ritem: dict, recordings: list=[]) -> tuple:
        if not recordings: recordings = self.getRecordings()
        def __match(eitem):
            return ritem.get('id') == eitem.get('id',str(random.random())) or (ritem.get('name','').lower() == eitem.get('display-name')[0][0].lower())
        return tuple(next(((idx, eitem) for idx, eitem in enumerate(recordings) if __match(eitem)),(None, {})))


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
        item['sub-title']     = (fItem.get('episodetitle') or '')
        item['categories']    = (fItem.get('genre')        or ['Undefined'])[:5]#trim list to five
        item['type']          = fItem.get('type','video')
        item['new']           = int(fItem.get('playcount','1')) == 0
        
        item['thumb']         = cleanImage((Globals._getThumb(fItem,EPG_ARTWORK) or {0:FANART,1:COLOR_LOGO}[EPG_ARTWORK])) #unify thumbnail by user preference 
        fItem.get('art',{})['thumb'] = cleanImage(Globals._getThumb(fItem,{0:1,1:0}[EPG_ARTWORK]) or {0:FANART,1:COLOR_LOGO}[{0:1,1:0}[EPG_ARTWORK]]) #unify thumbnail artwork, opposite of EPG_Artwork
         
        if item['type'] == 'movie': item['date'] = (fItem.get('premiered')  or fItem.get('releasedate') or fItem.get('firstaired'))
        else:                       item['date'] = (fItem.get('firstaired') or fItem.get('releasedate') or fItem.get('premiered'))
        
        item['catchup-id']    = VOD_URL.format(addon=ADDON_ID,title=Globals._quoteString(item['title']),chid=Globals._quoteString(citem['id']),vid=Globals._quoteString(Globals._encodeString((fItem.get('originalfile') or fItem.get('file','')))),name=Globals._quoteString(citem['name']))
        fItem['catchup-id']   = item['catchup-id']
            
        if (item['type'] != 'movie' and ((fItem.get("season",0) > 0) and (fItem.get("episode",0) > 0))):
            item['episode-num'] = {'xmltv_ns':'%s.%s'%(fItem.get("season",1)-1,fItem.get("episode",1)-1), # todo support totaleps <episode-num system="xmltv_ns">..44/47</episode-num>https://github.com/kodi-pvr/pvr.iptvsimple/pull/884
                                   'onscreen':'S%sE%s'%(str(fItem.get("season",0)).zfill(2),str(fItem.get("episode",0)).zfill(2))}

        item['rating']      = cleanMPAA(fItem.get('mpaa') or 'NA')
        item['stars']       = (fItem.get('rating')        or '0')
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


    def addRecording(self, ritem: dict, fitem: dict):
        self.log('addRecording = %s'%(ritem.get('id')))
        sitem = ({'id'           : ritem['id'],
                  'display-name' : [(self.cleanString(ritem['name']), LANG)],
                  'icon'         : [{'src':ritem['logo']}]})
                  
        self.log('addRecording, sitem = %s'%(sitem))
        try:              self.XMLTVDATA['recordings'][self.findRecording(ritem)[0]] = sitem # replace existing channel meta
        except Exception: self.XMLTVDATA['recordings'].append(sitem)

        fitem['start'] = getUTCstamp()
        fitem['stop']  = fitem['start'] + fitem['duration']
        if self.addProgram(ritem['id'],self.getProgramItem(ritem,fitem),encodeDESC=True):
            return True
        
    
    def addChannel(self, citem: dict) -> bool:
        mitem = ({'id'           : citem['id'],
                  'display-name' : [(self.cleanString(citem['name']), LANG)],
                  'icon'         : [{'src':citem['logo']}]})
                  
        self.log('addChannel, mitem = %s'%(mitem))
        try:              self.XMLTVDATA['channels'][self.findChannel(mitem)[0]] = mitem
        except Exception: self.XMLTVDATA['channels'].append(mitem)
        return True


    def addProgram(self, id: str, item: dict, encodeDESC: bool=True) -> bool:
        pitem = {'channel'     : id,
                 'category'    : [(self.cleanString(genre.replace(LANGUAGE(32105),'Undefined')),LANG) for genre in item['categories']],
                 'title'       : [(self.cleanString(item['title']), LANG)],
                 'desc'        : [(Globals._encodePlot(self.cleanString(item['desc']),item['fitem']), LANG) if encodeDESC else (self.cleanString(item['desc']), LANG)],
                 'stop'        : (epochTime(float(item['stop']),tz=False).strftime(DTFORMAT)),
                 'start'       : (epochTime(float(item['start']),tz=False).strftime(DTFORMAT)),
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
            except Exception: pass

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


    def clrProgrammes(self, citem: dict) -> bool:
        self.XMLTVDATA['programmes'] = [program for program in self.XMLTVDATA['programmes'] if program.get('channel') != citem.get('id')]
        self.log('clrProgrammes, removing channel %s programmes' % citem.get('id'))
        return True


    def delBroadcast(self, citem: dict) -> bool:# remove single channel and all programmes from XMLTVDATA
        channels   = self.XMLTVDATA['channels']
        programmes = self.XMLTVDATA['programmes']
        self.XMLTVDATA['channels']   = list([channel for channel in channels if channel.get('id') != citem.get('id')])
        self.XMLTVDATA['programmes'] = list([program for program in programmes if program.get('channel') != citem.get('id')])
        if citem.get('id') in self.stopTimes: del self.stopTimes[citem['id']] 
        self.log('delBroadcast, removing channel %s; channels: before = %s, after = %s; programmes: before = %s, after = %s'%(citem.get('id'),len(channels),len(self.XMLTVDATA['channels']),len(programmes),len(self.XMLTVDATA['programmes'])))
        return True
        
        
    def delRecording(self, ritem: dict):
        self.log('[%s] delRecording'%((ritem.get('id') or ritem.get('label'))))
        recordings = self.XMLTVDATA['recordings']
        programmes = self.XMLTVDATA['programmes']
        idx, recording = self.findRecording(ritem)
        if idx is not None:
            self.XMLTVDATA['recordings'].pop(idx)
            if not ritem.get('id'): ritem['id'] = recording['id']
            self.XMLTVDATA['programmes'] = list([program for program in programmes if program.get('channel') != ritem.get('id')])
            return True
        
        
    def buildGenres(self, epggenres={}):
        def __parseGenres(plines):
            for line in plines:
                try:    
                    names = line.childNodes[0].data
                    items = names.split(' / ')
                    data  = {'genre':names,'name':names,'genreId':line.attributes['genreId'].value}
                    epggenres[names.lower()] = data
                    for item in items:
                        name = item.strip()
                        if name and not epggenres.get(name.lower()):
                            epgdata = data.copy()
                            epgdata['name'] = name
                            epggenres[name.lower()] = epgdata
                except Exception: continue
            self.log('buildGenres, __parseGenres: epggenres = %s'%(epggenres.keys())) #todo custom user color selector.
            return epggenres

        def __matchGenres(program):
            categories = [cat[0] for cat in program.get('category',[])]
            catcombo   = ' / '.join(categories)
            for category in categories:
                match = genres.get(category.lower())
                if match and not genres.get(catcombo.lower()):
                    genres[catcombo.lower()] = match
                    break
            
        def __getGenres(file=GENREFLE_DEFAULT):
            if FileAccess.exists(file): 
                fle = FileAccess.open(file, "r")
                dom = parse(fle)
                fle.close()
                return __parseGenres(dom.getElementsByTagName('genre'))
            return {}
            
        try:
            doc  = Document()
            root = doc.createElement('genres')
            doc.appendChild(root)
            name = doc.createElement('name')
            name.appendChild(doc.createTextNode('%s'%(ADDON_NAME)))
            root.appendChild(name)
            
            genres = __getGenres()
            [__matchGenres(program) for program in self.XMLTVDATA.get('programmes',[])]
            epggenres = __getGenres(GENREFLEPATH)
            epggenres.update(dict(sorted(sorted(list(genres.items()), key=lambda v:v[1]['name']), key=lambda v:v[1]['genreId'])))
            for key in list(set(epggenres)):
                gen = doc.createElement('genre')
                gen.setAttribute('genreId',epggenres[key].get('genreId'))
                gen.appendChild(doc.createTextNode(key.title()))
                root.appendChild(gen)
            try:
                with FileLock(GENREFLEPATH):
                    xmlData = FileAccess.open(GENREFLEPATH, "w")
                    xmlData.write(doc.toprettyxml(indent='  ',encoding=DEFAULT_ENCODING))
                    xmlData.close()
                    return True
            except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)
        except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)