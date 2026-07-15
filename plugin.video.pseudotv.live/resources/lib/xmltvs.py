#   Copyright (C) 2026 Lunatixz
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

from variables   import *
from m3u         import M3U
from seasonal    import Seasonal
from typing       import Generator, Optional
from fileaccess  import FileAccess, FileLock

_ERROR_RE = re.compile(r'line\ (.*?),\ column\ (.*)', re.IGNORECASE)

class XMLTVS(object):
    
    def __init__(self, file: str = XMLTVFLEPATH, writable: bool = False, m3u: Optional[M3U] = None):
        self._lock       = RLock()
        if m3u is None: m3u = M3U(writable=writable)
        self.m3u        = m3u
        self.writable   = writable
        self.XMLTVFile  = file
        self.XMLTVDATA  = {}
        self.XMLTVDATA  = self._load()
        
        
    def __enter__(self) -> 'XMLTVS':
        return self


    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]):
        try:
            if self.writable: self._save()
            self.log('__exit__, writable = %s'%(self.writable))
        except Exception as e: self.log('__exit__ save failed: %s' % e, xbmc.LOGDEBUG)
            
            
    def __del__(self):
        try:
            if self.writable: self._save()
            self.log('__del__, writable = %s'%(self.writable))
        except Exception as e: self.log('__del__ save failed: %s' % e, xbmc.LOGDEBUG)
            
            
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def _clean(self, items: list=None, key: str='id', slug: str="") -> list: # remove (Non PseudoTV Live) entires from XMLTV, key = {'id':channels,'channel':programmes}
        if items is None: items = []
        if not slug: slug = '@%s'%(Globals._slugify(ADDON_NAME))
        channels   = list([item for item in items if item.get(key,'').endswith(slug) and len(item.get(key,'').replace(slug,'')) == 32])#128byte ChannelIDS
        recordings = list([item for item in items if item.get(key,'').endswith(slug) and len(item.get(key,'').replace(slug,'')) == 16])#64byte RecordingIDs
        if key == 'id': #stations
            self.log('_clean, slug=%s, key=%s: channels=%d, recordings=%d' % (slug, key, len(channels), len(recordings)))
            return self.sortChannels(Globals._setDictLST(channels)), self.sortChannels(Globals._setDictLST(recordings))
        elif key == 'channel': #programmes
            programmes = self.cleanStations(self.cleanProgrammes(channels)) +  self.cleanRecordings(recordings)
            self.log('_clean, slug=%s, key=%s: programmes=%d' % (slug, key, len(programmes)))
            return self.sortProgrammes(programmes)
        
        
    def _load(self) -> dict:
        self.log('_load, file=%s' % self.XMLTVFile)
        fle = None
        try:
            fle = FileAccess.open(self.XMLTVFile, 'r')
            data        = xmltv.read_data(fle)        or self.resetData()
            fle.seek(0)
            channels    = xmltv.read_channels(fle)    or []
            fle.seek(0)
            programmes  = xmltv.read_programmes(fle)  or []
        except Exception as e:
            self._error('_load', e)
            data, channels, programmes = self.resetData(), [], []
        finally:
            if fle and hasattr(fle, 'close'):
                fle.close()
        channels, recordings = self._clean(channels, 'id')
        return {'data'       : data,
                'channels'   : channels,
                'recordings' : recordings,
                'programmes' : self._clean(programmes, 'channel')}


    def _save(self, reset: bool=True) -> bool:
        with self._lock:
            if reset: data = self.resetData()
            else:     data = self.XMLTVDATA['data']
            self.XMLTVDATA['programmes'] = self.sortProgrammes(self.XMLTVDATA['programmes'])
            self.XMLTVDATA['channels']   = self.cleanChannels(self.sortChannels(self.XMLTVDATA['channels'])  , self.XMLTVDATA['programmes'], opt='PROGRAMMES')
            self.XMLTVDATA['recordings'] = self.cleanChannels(self.sortChannels(self.XMLTVDATA['recordings']), self.XMLTVDATA['programmes'], opt='RECORDINGS')
            self.log('_save, writable=%s, file=%s, reset=%s, channels=%d, programmes=%d, recordings=%d' % (
                self.writable, self.XMLTVFile, reset,
                len(self.XMLTVDATA['channels']),
                len(self.XMLTVDATA['programmes']),
                len(self.XMLTVDATA['recordings'])
            ))
            
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
                        with FileAccess.open(self.XMLTVFile, "w") as fle:
                            writer.write(fle, pretty_print=True)
                except Exception as e:
                    self.log("_save, failed!", xbmc.LOGERROR)
                    Globals.dialog.notificationDialog(LANGUAGE(32000))
                
                # Update PVR status with current M3U/XMLTV data
                status = Globals.settings.instances.updatePVRStatus(Globals.properties.getRemoteHost(), Globals.properties.getFriendlyName())
                xmltv_channels = self.getChannels()
                status['xmltv']['channel_ids'] = {c.get('id') for c in xmltv_channels if c.get('id')}
                status['xmltv']['programmes'] = len(self.getProgrammes())
                status['xmltv']['last_write'] = time.time()
                Globals.settings.instances._computeDerived(status)
                return self.buildGenres()
        
    
    def _error(self, e: Exception):
        try:
            name = self.XMLTVFile
            if 'no element found: line 1, column 0' in str(e): return   
            match = _ERROR_RE.search(str(e))
            if match:
                try: 
                    with FileAccess.open(self.XMLTVFile, 'r') as fle:
                        lines = fle.readlines()
                        line_num = int(match.group(1)) - 1
                        self.log('%s parser error: %s\nLine: %s' % (name, e, lines[line_num].strip()), xbmc.LOGERROR)
                except Exception as e2: self.log('%s error logging read failed: %s' % (name, e2), xbmc.LOGDEBUG)
        except Exception as en: 
            self.log('%s, logging failed! %s' % (name, en), xbmc.LOGERROR)
    
                
    def resetData(self) -> dict:
        self.log('resetData')
        return {'date'                : Globals._epochTime(float(time.time()),tz=False).strftime(DTFORMAT),
                'generator-info-name' : self.cleanString('%s Guidedata'%(ADDON_NAME)),
                'generator-info-url'  : self.cleanString(ADDON_ID),
                'source-info-name'    : self.cleanString(ADDON_NAME),
                'source-info-url'     : self.cleanString(ADDON_ID)}


    def loadData(self) -> dict:
        self.log('loadData, file = %s'%self.XMLTVFile)
        data = self.resetData()
        try: 
            with FileAccess.open(self.XMLTVFile, 'r') as fle:
                return (xmltv.read_data(fle) or data)
        except Exception as e:
            self._error('loadData',e)
            return data
        


    def loadChannels(self) -> list:
        self.log('loadChannels, file = %s'%self.XMLTVFile)
        try: 
            with FileAccess.open(self.XMLTVFile, 'r') as fle:
                return (xmltv.read_channels(fle) or [])
        except Exception as e:
            self._error('loadChannels', e)
            return []
        
        
    def loadProgrammes(self) -> list:
        self.log('loadProgrammes, file = %s'%self.XMLTVFile)
        try: 
            with FileAccess.open(self.XMLTVFile, 'r') as fle:
                return (xmltv.read_programmes(fle) or [])
        except Exception as e: 
            self._error('loadProgrammes',e)
            return []
        
        
    def loadStopTimes(self, channels: list = None, programmes: list = None, fallback: Optional[str] = None) -> Generator:
        if channels is None:   channels   = []
        if programmes is None: programmes = []
        if not channels:   channels   = self.getChannels()
        if not programmes: programmes = self.getProgrammes()
        if not fallback:   fallback   = Globals._epochTime(Globals._roundTimeDown(Globals._getUTCstamp(), offset=60), tz=False).strftime(DTFORMAT)
            
        channel_bounds = { channel['id']: {'start': fallback, 'stop': fallback} for channel in channels if 'id' in channel }
        for program in programmes:
            ch_id = program.get('channel')
            if ch_id not in channel_bounds: continue
                
            p_start = program.get('start')
            if not channel_bounds[ch_id]['start'] or p_start < channel_bounds[ch_id]['start']:
                channel_bounds[ch_id]['start'] = p_start
                
            p_stop = program.get('stop')
            if not channel_bounds[ch_id]['stop'] or p_stop > channel_bounds[ch_id]['stop']:
                channel_bounds[ch_id]['stop'] = p_stop

        self.log('loadStopTimes channel_bounds %s'%channel_bounds)
        for ch_id, bounds in channel_bounds.items():
            firstStart = bounds['start']
            lastStop   = bounds['stop']
            
            try:
                self.log(' [%s] loadStopTimes first-start = %s, last-stop = %s, fallback = %s' % (ch_id, firstStart, lastStop, fallback))
                if firstStart > fallback:# Check if the program's actual first start time is in the future
                    raise Exception('First start-time in the future, rebuild channel with fallback')
                yield ch_id, datetime.datetime.timestamp(Globals._strpTime(lastStop, DTFORMAT))
            except Exception as e:
                self.log(" [%s] loadStopTimes failed! Malformed XMLTV channel/programmes %s! rebuilding channel with default stop-time %s" % (ch_id, e, fallback), xbmc.LOGWARNING)
                yield ch_id, datetime.datetime.timestamp(Globals._strpTime(fallback, DTFORMAT))


    def hasProgrammes(self, channels: list=None, programmes: list=None, now: Optional[str] = None) -> Generator:
        if channels is None:   channels   = []
        if programmes is None: programmes = []
        if not channels:   channels   = self.getChannels()
        if not programmes: programmes = self.getProgrammes()
        if not now: now = Globals._epochTime(Globals._roundTimeDown(Globals._getUTCstamp(),offset=60),tz=False).strftime(DTFORMAT)
        # Single-pass: build max stop time per channel
        max_stops = {}
        for program in programmes:
            ch_id = program.get('channel')
            if ch_id is None: continue
            p_stop = program.get('stop', '')
            if p_stop > max_stops.get(ch_id, ''):
                max_stops[ch_id] = p_stop
        for channel in channels:
            ch_id = channel.get('id')
            try: 
                last_stop = max_stops.get(ch_id, now)
                valid = last_stop > now
                self.log('[%s] hasProgrammes, valid = %s'%(ch_id, valid))
                yield ch_id, valid
            except Exception as e:
                self.log("[%s] hasProgrammes, failed!\nMalformed XMLTV channel/programmes %s! valid = False"%(ch_id, e), xbmc.LOGWARNING)
                yield ch_id, False


    def cleanString(self, text: str) -> str:
        if text == ', ' or not text: text = LANGUAGE(32020) or 'Unavailable'
        if not isinstance(text, str): text = str(text)
        return bytes(text,DEFAULT_ENCODING).decode(DEFAULT_ENCODING,'ignore')


    def cleanStations(self, programmes: list=None) -> list:
        if programmes is None: programmes = []
        if not self.m3u is None:
            programs = dict(self.hasProgrammes(self.getChannels(),programmes))
            for id, hasProgram in programs.items():
                if id and not hasProgram:
                    self.m3u.delStation({'id':id})
                    self.delBroadcast({'id':id})
                    self.log('cleanStations, removing = %s; no programmes!'%(id))
        return programmes
        
        
    def cleanRecordings(self, programmes: list=None) -> list:
        if programmes is None: programmes = []
        if not self.m3u is None:
            programs = dict(self.hasProgrammes(self.getRecordings(), programmes))
            for id, hasProgram in programs.items():
                if id and not hasProgram:
                    self.m3u.delRecording({'id':id})
                    self.delRecording({'id':id})
                    self.log('cleanRecordings, removing = %s; no programmes!'%(id))
        return programmes
        
         
    def cleanChannels(self, channels: list=None, programmes: list=None, opt: str = 'PROGRAMMES') -> list: # remove stations with no guidedata
        if channels is None:   channels   = []
        if programmes is None: programmes = []
        stations    = list(set([program.get('channel') for program in programmes]))
        tmpChannels = [channel for station in stations for channel in channels if channel.get('id') == station]
        self.log('cleanChannels [%s], before = %s, after = %s'%(opt,len(channels),len(tmpChannels)))
        return tmpChannels


    def cleanProgrammes(self, programmes: list=None) -> list:
        if programmes is None: programmes = []
        now     = (Globals._epochTime(float(Globals._getUTCstamp()),tz=False) - datetime.timedelta(days=MIN_GUIDEDAYS)) #allow some old programmes to avoid empty cells
        holiday = Seasonal().getHoliday()
        
        def __filterProgrammes(program: dict) -> Optional[dict]:
            try:
                citem    = Globals._decodePlot(program.get('desc',([{}],''))[0][0]).get('citem',{})
                seasonal = citem.get('rules',{}).get(800,{}).get('values',{}).get(0,[{}])[0].get('holiday',{})
                stopTime = program.get('stop',now).rstrip()
                if seasonal and seasonal.get('name',str(random.random())) != holiday.get('name'):
                    self.log('[%s] cleanProgrammes, __filterProgrammes removing expired holiday (%s)'%(citem.get('id'),seasonal))
                    return None
                elif Globals._strpTime(stopTime,DTFORMAT) < now: 
                    self.log('[%s] cleanProgrammes, __filterProgrammes removing expired programmes (%s)'%(citem.get('id'),stopTime))
                    return None  # remove expired content, todo ignore "recordings" ie. media=True
            except Exception as e: self.log(f"__filterProgrammes, failed!\n{e}", xbmc.LOGWARNING)
            return program
            
        tmpProgrammes = [program for program in [__filterProgrammes(program) for program in programmes] if program is not None]
        self.log('cleanProgrammes, before = %s, after = %s'%(len(programmes),len(tmpProgrammes)))
        return tmpProgrammes


    def sortChannels(self, channels: list=None) -> list:
        if channels is None: channels = []
        try:    return sorted(channels, key=itemgetter('display-name'))
        except Exception: return channels
        


    def sortProgrammes(self, programmes: list=None) -> list:
        if programmes is None: programmes = []
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


    def findChannel(self, citem: dict, channels: list=None) -> tuple:
        if channels is None: channels = []
        if not channels: channels = self.getChannels()
        return tuple(next(((idx, eitem) for idx, eitem in enumerate(channels) if citem.get('id') == eitem.get('id',str(random.random()))),(None, {})))
        
        
    def findRecording(self, ritem: dict, recordings: list=None) -> tuple:
        if recordings is None: recordings = []
        if not recordings: recordings = self.getRecordings()
        def __match(eitem: dict) -> bool:
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
        item['thumb']                = Globals._getThumb(fItem,self.m3u.EPGArtwork)            #unify thumbnail by user preference 
        fItem.get('art',{})['thumb'] = Globals._getThumb(fItem,{0:1,1:0}[self.m3u.EPGArtwork]) #unify thumbnail artwork, opposite of EPG_Artwork
         
        if item['type'] == 'movie': item['date'] = (fItem.get('premiered')  or fItem.get('releasedate') or fItem.get('firstaired'))
        else:                       item['date'] = (fItem.get('firstaired') or fItem.get('releasedate') or fItem.get('premiered'))
        
        item['catchup-id']    = VOD_URL.format(addon=ADDON_ID,title=Globals._quoteString(item['title']),chid=Globals._quoteString(citem['id']),vid=(FileAccess._encodeString((fItem.get('originalfile') or fItem.get('file','')))),name=Globals._quoteString(citem['name']))
        fItem['catchup-id']   = item['catchup-id']
            
        if (item['type'] != 'movie' and ((fItem.get("season",0) > 0) and (fItem.get("episode",0) > 0))):
            item['episode-num'] = {'xmltv_ns':'%s.%s'%(fItem.get("season",1)-1,fItem.get("episode",1)-1), # todo support totaleps <episode-num system="xmltv_ns">..44/47</episode-num>https://github.com/kodi-pvr/pvr.iptvsimple/pull/884
                                   'onscreen':'S%sE%s'%(str(fItem.get("season",0)).zfill(2),str(fItem.get("episode",0)).zfill(2))}

        item['rating']      = Globals._cleanMPAA(fItem.get('mpaa') or 'NA')
        item['stars']       = (fItem.get('rating')        or '0')
        item['votes']       = (fItem.get('votes')         or '')
        item['writer']      = fItem.get('writer',[])[:5]   #trim list to five
        item['director']    = fItem.get('director',[])[:5] #trim list to five
        item['actor']       = ['%s - %s'%(actor.get('name'),actor.get('role',LANGUAGE(32020))) for actor in fItem.get('cast',[])[:5] if actor.get('name')]
        item['studio']      = fItem.get('studio','')
        item['country']     = fItem.get('country','')
        item['tagline']     = fItem.get('tagline','')
        item['originaltitle'] = fItem.get('originaltitle','')
        
        fItem['citem']      = citem #channel item (stale data due to xmltv storage) use for reference
        item['fitem']       = fItem #raw kodi fileitem/listitem, contains citem both passed through 'plot' xmltv param.
        
        streamdetails = fItem.get('streamdetails',{})
        if streamdetails:
            item['subtitle'] = list(set([sub.get('language','')                    for sub in streamdetails.get('subtitle',[]) if sub.get('language')]))
            item['language'] = ', '.join(list(set([aud.get('language','')          for aud in streamdetails.get('audio',[])    if aud.get('language')])))
            item['audio']    = True if True in list(set([aud.get('codec','')       for aud in streamdetails.get('audio',[])    if aud.get('channels',0) >= 2])) else False
            item.setdefault('video',{})['aspect'] = list(set([vid.get('aspect','') for vid in streamdetails.get('video',[])    if vid.get('aspect','')]))
        return item


    def addRecording(self, ritem: dict, fitem: dict) -> bool:
        with self._lock:
            self.log('addRecording = %s'%(ritem.get('id')))
            sitem = ({'id'           : ritem['id'],
                      'display-name' : [(self.cleanString(ritem['name']), LANG)],
                      'icon'         : [{'src':ritem['logo']}]})
                      
            self.log('addRecording, sitem = %s'%(sitem))
            idx, _ = self.findRecording(ritem)
            if idx is not None:
                self.XMLTVDATA['recordings'][idx] = sitem
            else:
                self.XMLTVDATA['recordings'].append(sitem)

            fitem['start'] = Globals._getUTCstamp()
            fitem['stop']  = fitem['start'] + fitem['duration']
            if self.addProgram(ritem['id'],self.getProgramItem(ritem,fitem),encodeDESC=True):
                return True
        
    
    def addChannel(self, citem: dict) -> bool:
        with self._lock:
            mitem = ({'id'           : citem['id'],
                      'display-name' : [(self.cleanString(citem['name']), LANG)],
                      'icon'         : [{'src':citem['logo']}]})
            self.log('addChannel, mitem = %s'%(mitem))
            idx, _ = self.findChannel(mitem)
            if idx is not None:
                self.XMLTVDATA['channels'][idx] = mitem
            else:
                self.XMLTVDATA['channels'].append(mitem)
            return True


    def addProgram(self, id: str, item: dict, encodeDESC: bool=True) -> bool:
        with self._lock:
            pitem = {'channel'     : id,
                     'category'    : [(self.cleanString(genre.replace(LANGUAGE(32105),'Undefined')),LANG) for genre in item['categories']],
                     'title'       : [(self.cleanString(item['title']), LANG)],
                     'desc'        : [(Globals._encodePlot(self.cleanString(item['desc']),item['fitem']), LANG) if encodeDESC else (self.cleanString(item['desc']), LANG)],
                     'stop'        : (Globals._epochTime(float(item['stop']),tz=False).strftime(DTFORMAT)),
                     'start'       : (Globals._epochTime(float(item['start']),tz=False).strftime(DTFORMAT)),
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
                try: pitem['date'] = (Globals._strpTime(item['date'], '%Y-%m-%d')).strftime('%Y%m%d')
                except Exception as e: self.log('addProgram date parse failed: %s' % e, xbmc.LOGDEBUG)

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

            if item.get('language',''):
                pitem['language'] = [(item.get('language'), LANG)]

            if item.get('subtitle',[]):
                pitem['subtitles'] = [{'type': 'teletext', 'language': (sub, LANG)} for sub in item.get('subtitle',[]) if sub]

            if item.get('video',{}).get('aspect'):
                pitem['video'] = [{'aspect': item['video']['aspect']}]

            if not item.get('new', False):
                pitem['previously-shown'] = [{}]

            if item.get('votes',''):
                try: pitem['star-rating'] = [{'value': '%s/10'%(int(round(float(item['stars'])))), 'votes': str(item['votes'])}]
                except Exception: pass

            if item.get('studio',''):
                pitem['credits'] = pitem.get('credits',{})
                pitem['credits']['studio'] = [self.cleanString(item['studio'])]

            if item.get('country',''):
                pitem['country'] = [(item['country'], LANG)]

            if item.get('tagline',''):
                pitem['desc'] = list(pitem.get('desc',[]))
                if not pitem['desc']:
                    pitem['desc'] = [(self.cleanString(item['tagline']), LANG)]

            self.log('[%s] addProgram'%(id))
            self.XMLTVDATA['programmes'].append(pitem)
            return True


    def clrProgrammes(self, citem: dict) -> bool:
        with self._lock:
            self.XMLTVDATA['programmes'] = [program for program in self.XMLTVDATA['programmes'] if program.get('channel') != citem.get('id')]
            self.log('clrProgrammes, removing channel %s programmes' % citem.get('id'))
            return True


    def delBroadcast(self, citem: dict) -> bool:# remove single channel and all programmes from XMLTVDATA
        with self._lock:
            channels   = self.XMLTVDATA['channels']
            programmes = self.XMLTVDATA['programmes']
            self.XMLTVDATA['channels']   = list([channel for channel in channels if channel.get('id') != citem.get('id')])
            self.XMLTVDATA['programmes'] = list([program for program in programmes if program.get('channel') != citem.get('id')])
            self.log('delBroadcast, removing channel %s; channels: before = %s, after = %s; programmes: before = %s, after = %s'%(citem.get('id'),len(channels),len(self.XMLTVDATA['channels']),len(programmes),len(self.XMLTVDATA['programmes'])))
            return True
        
        
    def delRecording(self, ritem: dict) -> bool:
        with self._lock:
            self.log('[%s] delRecording'%((ritem.get('id') or ritem.get('label'))))
            recordings = self.XMLTVDATA['recordings']
            programmes = self.XMLTVDATA['programmes']
            idx, recording = self.findRecording(ritem)
            if idx is not None:
                self.XMLTVDATA['recordings'].pop(idx)
                if not ritem.get('id'): ritem['id'] = recording['id']
                self.XMLTVDATA['programmes'] = list([program for program in programmes if program.get('channel') != ritem.get('id')])
                return True
        
        
    def buildGenres(self, epggenres: Optional[dict] = None) -> bool:
        if epggenres is None: epggenres = {}
        def __parseGenres(plines: list) -> dict:
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

        def __matchGenres(program: dict):
            categories = [cat[0] for cat in program.get('category',[])]
            catcombo   = ' / '.join(categories)
            for category in categories:
                match = genres.get(category.lower())
                if match and not genres.get(catcombo.lower()):
                    genres[catcombo.lower()] = match
                    break
            
        def __getGenres(file: str = GENREFLE_DEFAULT) -> dict:
            if FileAccess.exists(file): 
                with FileAccess.open(file, "r") as fle:
                    dom = parse(fle)
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
            for program in self.XMLTVDATA.get('programmes', []):
                __matchGenres(program)
                
            epggenres = __getGenres(GENREFLEPATH)
            epggenres.update(dict(sorted(sorted(list(genres.items()), key=lambda v:v[1]['name']), key=lambda v:v[1]['genreId'])))
            for key in list(set(epggenres)):
                gen = doc.createElement('genre')
                gen.setAttribute('genreId',epggenres[key].get('genreId'))
                gen.appendChild(doc.createTextNode(key.title()))
                root.appendChild(gen)
            try:
                with FileLock(GENREFLEPATH):
                    with FileAccess.open(GENREFLEPATH, "w") as xmlData:
                        xmlData.write(doc.toprettyxml(indent='  ',encoding=DEFAULT_ENCODING))
                        return True
            except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)
        except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)