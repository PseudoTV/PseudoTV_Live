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
# https://github.com/kodi-pvr/pvr.iptvsimple#supported-m3u-and-xmltv-elements

# -*- coding: utf-8 -*-

from globals    import *
from channels   import Channels

M3U_TEMP = {"id"                : "",
            "number"            : 0,
            "name"              : "",
            "logo"              : "",
            "group"             : [],
            "catchup"           : "vod",
            "radio"             : False,
            "favorite"          : False,
            "realtime"          : False,
            "media"             : "",
            "label"             : "",
            "url"               : "",
            "tvg-shift"         : "",
            "x-tvg-url"         : "",
            "media-dir"         : "",
            "media-size"        : "",
            "media-type"        : "",
            "catchup-source"    : "",
            "catchup-days"      : "",
            "catchup-correction": "",
            "provider"          : "",
            "provider-type"     : "",
            "provider-logo"     : "",
            "provider-countries": "",
            "provider-languages": "",
            "x-playlist-type"   : "",
            "kodiprops"         : []}
            
M3U_MIN  = {"id"                : "",
            "number"            : 0,
            "name"              : "",
            "logo"              : "",
            "group"             : [],
            "catchup"           : "vod",
            "radio"             : False,
            "label"             : "",
            "url"               : ""}
            
class M3U:
    def __init__(self):
        stations, recordings = self.cleanSelf(list(self._load()))
        self.M3UDATA = {'data':'#EXTM3U tvg-shift="" x-tvg-url="" x-tvg-id="" catchup-correction=""', 'stations':stations, 'recordings':recordings}
        # self.M3UTEMP = getJSON(M3UFLE_DEFAULT)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _load(self, file=M3UFLEPATH):
        self.log('_load, file = %s'%file)
        if file.startswith('http'):
            url  = file
            file = os.path.join(TEMP_LOC,slugify(url))
            saveURL(url,file)
            
        if FileAccess.exists(file): 
            fle   = FileAccess.open(file, 'r')
            lines = (fle.readlines())
            fle.close()
            
            chCount = 0
            data    = {}
            filter  = []
            
            for idx, line in enumerate(lines):
                line = line.rstrip()
                
                if line.startswith('#EXTM3U'):
                    data = {'tvg-shift'         :re.compile('tvg-shift=\"(.*?)\"'          , re.IGNORECASE).search(line),
                            'x-tvg-url'         :re.compile('x-tvg-url=\"(.*?)\"'          , re.IGNORECASE).search(line),
                            'catchup-correction':re.compile('catchup-correction=\"(.*?)\"' , re.IGNORECASE).search(line)}
                            
                    # if SETTINGS.getSettingInt('Import_XMLTV_TYPE') == 2 and file == os.path.join(TEMP_LOC,slugify(SETTINGS.getSetting('Import_M3U_URL'))):
                        # if data.get('x-tvg-url').group(1):
                            # self.log('_load, using #EXTM3U "x-tvg-url"')
                            # SETTINGS.setSetting('Import_XMLTV_M3U',data.get('x-tvg-url').group(1))
                           
                elif line.startswith('#EXTINF:'):
                    chCount += 1
                    match = {'label'             :re.compile(',(.*)'                        , re.IGNORECASE).search(line),
                             'id'                :re.compile('tvg-id=\"(.*?)\"'             , re.IGNORECASE).search(line),
                             'name'              :re.compile('tvg-name=\"(.*?)\"'           , re.IGNORECASE).search(line),
                             'group'             :re.compile('group-title=\"(.*?)\"'        , re.IGNORECASE).search(line),
                             'number'            :re.compile('tvg-chno=\"(.*?)\"'           , re.IGNORECASE).search(line),
                             'logo'              :re.compile('tvg-logo=\"(.*?)\"'           , re.IGNORECASE).search(line),
                             'radio'             :re.compile('radio=\"(.*?)\"'              , re.IGNORECASE).search(line),
                             'tvg-shift'         :re.compile('tvg-shift=\"(.*?)\"'          , re.IGNORECASE).search(line),
                             'catchup'           :re.compile('catchup=\"(.*?)\"'            , re.IGNORECASE).search(line),
                             'catchup-source'    :re.compile('catchup-source=\"(.*?)\"'     , re.IGNORECASE).search(line),
                             'catchup-days'      :re.compile('catchup-days=\"(.*?)\"'       , re.IGNORECASE).search(line),
                             'catchup-correction':re.compile('catchup-correction=\"(.*?)\"' , re.IGNORECASE).search(line),
                             'provider'          :re.compile('provider=\"(.*?)\"'           , re.IGNORECASE).search(line),
                             'provider-type'     :re.compile('provider-type=\"(.*?)\"'      , re.IGNORECASE).search(line),
                             'provider-logo'     :re.compile('provider-logo=\"(.*?)\"'      , re.IGNORECASE).search(line),
                             'provider-countries':re.compile('provider-countries=\"(.*?)\"' , re.IGNORECASE).search(line),
                             'provider-languages':re.compile('provider-languages=\"(.*?)\"' , re.IGNORECASE).search(line),
                             'media'             :re.compile('media=\"(.*?)\"'              , re.IGNORECASE).search(line),
                             'media-dir'         :re.compile('media-dir=\"(.*?)\"'          , re.IGNORECASE).search(line),
                             'media-size'        :re.compile('media-size=\"(.*?)\"'         , re.IGNORECASE).search(line),
                             'realtime'          :re.compile('realtime=\"(.*?)\"'           , re.IGNORECASE).search(line)}
                    
                    if match['id'].group(1) in filter:
                        self.log('_load, filtering duplicate %s'%(match['id'].group(1)))
                        continue
                    filter.append(match['id'].group(1)) #filter dups, todo find where dups originate from. 
                    
                    mitem = self.getMitem()
                    mitem.update({'number' :chCount,
                                  'logo'   :LOGO,
                                  'catchup':''}) #set default parameters
                    
                    for key, value in list(match.items()):
                        if value is None:
                            if data.get(key,None) is not None:
                                self.log('_load, using #EXTM3U "%s" value for #EXTINF'%(key))
                                value = data[key] #no local EXTINF value found; use global EXTM3U if applicable.
                            else: continue
                        
                        if value.group(1) is None:
                            continue
                        elif key == 'logo':
                            mitem[key] = value.group(1)
                        elif key == 'number':
                            try:    mitem[key] = int(value.group(1))
                            except: mitem[key] = float(value.group(1))#todo why was this needed?
                        elif key == 'group':
                            mitem[key] = [_f for _f in sorted(list(set((value.group(1)).split(';')))) if _f]
                        elif key in ['radio','favorite','realtime','media']:
                            mitem[key] = (value.group(1)).lower() == 'true'
                        else:
                            mitem[key] = value.group(1)

                    for nidx in range(idx+1,len(lines)):
                        try:
                            nline = lines[nidx].rstrip()
                            if   nline.startswith('#EXTINF:'): break
                            elif nline.startswith('#EXTGRP'):
                                grop = re.compile('^#EXTGRP:(.*)$', re.IGNORECASE).search(nline)
                                if grop is not None: 
                                    mitem['group'].append(grop.group(1).split(';'))
                                    mitem['group'] = sorted(set(mitem['group']))
                            elif nline.startswith('#KODIPROP:'):
                                prop = re.compile('^#KODIPROP:(.*)$', re.IGNORECASE).search(nline)
                                if prop is not None: mitem.setdefault('kodiprops',[]).append(prop.group(1))
                            elif nline.startswith('#EXTVLCOPT'):
                                copt = re.compile('^#EXTVLCOPT:(.*)$', re.IGNORECASE).search(nline)
                                if copt is not None:  mitem.setdefault('extvlcopt',[]).append(copt.group(1))
                            elif nline.startswith('#EXT-X-PLAYLIST-TYPE'):
                                xplay = re.compile('^#EXT-X-PLAYLIST-TYPE:(.*)$', re.IGNORECASE).search(nline)
                                if xplay is not None: mitem['x-playlist-type'] = xplay.group(1)
                            elif nline.startswith('##'): continue
                            elif not nline: continue
                            else: mitem['url'] = nline
                        except Exception as e: self.log('_load, error parsing m3u! %s'%(e))
                            
                    #Fill missing with similar parameters.
                    mitem['name']     = (mitem.get('name')     or mitem.get('label') or '')
                    mitem['label']    = (mitem.get('label')    or mitem.get('name')  or '')
                    mitem['favorite'] = (mitem.get('favorite') or False)
                    
                    #Set Fav. based on group value.
                    if LANGUAGE(32019) in mitem['group'] and not mitem['favorite']:
                        mitem['favorite'] = True
                    
                    #Core m3u parameters missing, ignore entry.
                    if not mitem.get('id') or not mitem.get('name') or not mitem.get('number'): 
                        self.log('_load, SKIPPED MISSING META m3u item = %s'%mitem)
                        continue
                        
                    self.log('_load, m3u item = %s'%mitem)
                    yield mitem
        
        
    def _save(self, file=M3UFLEPATH):
        with FileLock():
            fle = FileAccess.open(file, 'w')
            fle.write('%s\n'%(self.M3UDATA['data']))
            
            opts = list(self.getMitem().keys())
            mins = [opts.pop(opts.index(key)) for key in list(M3U_MIN.keys()) if key in opts] #min required m3u entries.
            line = '#EXTINF:-1 tvg-chno="%s" tvg-id="%s" tvg-name="%s" tvg-logo="%s" group-title="%s" radio="%s" catchup="%s" %s,%s\n'
            self.M3UDATA['stations']   = self.sortStations(self.M3UDATA.get('stations',[]))
            self.M3UDATA['recordings'] = self.sortStations(self.M3UDATA.get('recordings',[]), key='name')
            self.log('_save, saving %s stations and %s recordings to %s'%(len(self.M3UDATA['stations']),len(self.M3UDATA['recordings']),file))
            
            for station in (self.M3UDATA['recordings'] + self.M3UDATA['stations']):
                optional  = ''
                xplaylist = ''
                kodiprops = {}
                extvlcopt = {}
                    
                # write optional m3u parameters.
                if 'kodiprops'       in station: kodiprops = station.pop('kodiprops')
                if 'extvlcopt'       in station: extvlcopt = station.pop('extvlcopt')
                if 'x-playlist-type' in station: xplaylist = station.pop('x-playlist-type')
                for key, value in list(station.items()):
                    if key in opts and str(value):
                        optional += '%s="%s" '%(key,value)

                fle.write(line%(station['number'],
                                station['id'],
                                station['name'],
                                station['logo'],
                                ';'.join(station['group']),
                                station['radio'],
                                station['catchup'],
                                optional,
                                station['label']))
                       
                if kodiprops:  fle.write('%s\n'%('\n'.join(['#KODIPROP:%s'%(prop)  for prop in kodiprops])))
                if extvlcopt:  fle.write('%s\n'%('\n'.join(['#EXTVLCOPT:%s'%(prop) for prop in extvlcopt])))
                if xplaylist:  fle.write('%s\n'%('#EXT-X-PLAYLIST-TYPE:%s'%(xplaylist)))
                fle.write('%s\n'%(station['url']))
            fle.close()
        return self._reload()
        
        
    def _reload(self):
        self.log('_reload') 
        self.__init__()
        return True
        
        
    def _verify(self, stations=[], recordings=[], chkPath=SETTINGS.getSettingBool('Clean_Recordings')):
        if stations: #remove abandoned m3u entries; Stations that are not found in the channel list
            stations = [station for station in stations for channel in Channels().getChannels() if channel.get('id') == station.get('id',str(random.random()))] 
            self.log('_verify, stations = %s'%(len(stations)))
            return stations
        elif recordings:#remove recordings that no longer exists on disk
            if chkPath: recordings = [recording for recording in recordings if hasFile(decodeString(dict(urllib.parse.parse_qsl(recording.get('url',''))).get('vid').replace('.pvr','')))]
            else:       recordings = [recording for recording in recordings if recording.get('media',False)]
            self.log('_verify, recordings = %s, chkPath = %s'%(len(recordings),chkPath))
            return recordings
        return []
        

    def cleanSelf(self, items, key='id', slug='@%s'%(slugify(ADDON_NAME))): # remove m3u imports (Non PseudoTV Live)
        if not slug: return items
        stations   = self.sortStations(self._verify(stations=[station for station in items if station.get(key,'').endswith(slug) and not station.get('media',False)]))
        recordings = self.sortStations(self._verify(recordings=[recording for recording in items if recording.get(key,'').endswith(slug) and recording.get('media',False)]), key='name')
        self.log('cleanSelf, slug = %s, key = %s: returning: stations = %s, recordings = %s'%(slug,key,len(stations),len(recordings)))
        return stations, recordings


    def sortStations(self, stations, key='number'):
        try:    return sorted(stations, key=itemgetter(key))
        except: return stations
        
        
    def getM3U(self):
        return self.M3UDATA
        
        
    def getMitem(self):
        return M3U_TEMP.copy()
        
        
    def getTZShift(self):
        self.log('getTZShift')
        return ((time.mktime(time.localtime()) - time.mktime(time.gmtime())) / 60 / 60)

    
    def getStations(self):
        stations = self.sortStations(self.M3UDATA.get('stations',[]))
        self.log('getStations, stations = %s'%(len(stations)))
        return stations
              
              
    def getRecordings(self):
        recordings = self.sortStations(self.M3UDATA.get('recordings',[]), key='name')
        self.log('getRecordings, recordings = %s'%(len(recordings)))
        return recordings
               
               
    def findStation(self, citem):
        for idx, eitem in enumerate(self.M3UDATA.get('stations',[])):
            if (citem.get('id',str(random.random())) == eitem.get('id') or citem.get('url',str(random.random())).lower() == eitem.get('url','').lower()):
                self.log('findStation, found eitem = %s'%(eitem))
                return idx, eitem
        return None, {}
        
                        
    def findRecording(self, ritem):
        for idx, eitem in enumerate(self.M3UDATA.get('recordings',[])):
            if (ritem.get('id',str(random.random())) == eitem.get('id')) or (ritem.get('label',str(random.random())).lower() == eitem.get('label','').lower()) or (ritem.get('path',str(random.random())).endswith('%s.pvr'%(eitem.get('name')))):
                self.log('findRecording, found eitem = %s'%(eitem))
                return idx, eitem
        return None, {} 
        
        
    def getStationItem(self, sitem):
        if sitem.get('resume',False):
                             sitem['url'] = RESUME_URL.format(addon=ADDON_ID,name=quoteString(sitem['name']),chid=quoteString(sitem['id']))
        elif sitem['catchup']:
                             sitem['catchup-source'] = BROADCAST_URL.format(addon=ADDON_ID,name=quoteString(sitem['name']),chid=quoteString(sitem['id']),vid='{catchup-id}')
                             sitem['url'] = LIVE_URL.format(addon=ADDON_ID,name=quoteString(sitem['name']),chid=quoteString(sitem['id']),vid='{catchup-id}',now='{lutc}',start='{utc}',duration='{duration}',stop='{utcend}')
        elif sitem['radio']: sitem['url'] = RADIO_URL.format(addon=ADDON_ID,name=quoteString(sitem['name']),chid=quoteString(sitem['id']),radio=str(sitem['radio']),vid='{catchup-id}')
        else:                sitem['url'] = TV_URL.format(addon=ADDON_ID,name=quoteString(sitem['name']),chid=quoteString(sitem['id']))
        return sitem
    
    def getRecordItem(self, fitem, seek=0):
        if seek <= 0: group = LANGUAGE(30119)
        else:         group = LANGUAGE(30152)
        ritem = self.getMitem()
        ritem['provider']      = '%s (%s)'%(ADDON_NAME,SETTINGS.getFriendlyName())
        ritem['provider-type'] = 'addon'
        ritem['provider-logo'] = HOST_LOGO
        ritem['label']         = (fitem.get('showlabel') or '%s%s'%(fitem.get('label',''),' - %s'%(fitem.get('episodelabel','')) if fitem.get('episodelabel','') else ''))
        ritem['name']          = ritem['label']
        ritem['number']        = random.Random(str(fitem.get('id',1))).random()
        ritem['logo']          = cleanImage(getThumb(fitem,opt=EPG_ARTWORK))
        ritem['media']         = True
        ritem['media-size']    = str(fitem.get('size',0))
        ritem['media-dir']     = ''#todo optional add parent directory via user prompt?
        ritem['group']         = ['%s (%s)'%(group,ADDON_NAME)]
        ritem['id']            = getRecordID(ritem['name'], (fitem.get('originalfile') or fitem.get('file','')), ritem['number'])
        ritem['url']           = DVR_URL.format(addon=ADDON_ID,title=quoteString(ritem['label']),chid=quoteString(ritem['id']),vid=quoteString(encodeString((fitem.get('originalfile') or fitem.get('file','')))),seek=seek,duration=fitem.get('duration',0))#fitem.get('catchup-id','')
        return ritem
        
        
    def addStation(self, citem):
        idx, line = self.findStation(citem)
        self.log('addStation,\nchannel item = %s\nfound existing = %s'%(citem,line))
        mitem = self.getMitem()
        mitem.update(citem)            
        mitem['label']         = citem['name'] #todo channel manager opt to change channel 'label' leaving 'name' static for channelid purposes.
        mitem['logo']          = citem['logo']
        mitem['realtime']      = False
        mitem['provider']      = '%s (%s)'%(ADDON_NAME,SETTINGS.getFriendlyName())
        mitem['provider-type'] = 'addon'
        mitem['provider-logo'] = HOST_LOGO
        
        if not idx is None: self.M3UDATA['stations'].pop(idx)
        self.M3UDATA.get('stations',[]).append(mitem)
        self.log('addStation, channels = %s'%(len(self.M3UDATA.get('stations',[]))))
        return True
        
        
    def addRecording(self, ritem):
        # https://github.com/kodi-pvr/pvr.iptvsimple/blob/Omega/README.md#media
        idx, line = self.findRecording(ritem)
        self.log('addRecording,\nrecording ritem = %s\nfound existing = %s'%(ritem,idx))
        if not idx is None: self.M3UDATA['recordings'].pop(idx)
        self.M3UDATA.get('recordings',[]).append(ritem)
        return self._save()


    def delStation(self, citem):
        self.log('delStation id = %s'%(citem['id']))
        idx, line = self.findStation(citem)
        if not idx is None: self.M3UDATA['stations'].pop(idx)
        return True
        

    def delRecording(self, ritem):
        self.log('delRecording id = %s'%((ritem.get('id') or ritem.get('label'))))
        idx, line = self.findRecording(ritem)
        if not idx is None:
            self.M3UDATA['recordings'].pop(idx)
            return self._save()
    
    
    def importM3U(self, file, filters={}, multiplier=1):
        self.log('importM3U, file = %s, filters = %s, multiplier = %s'%(file,filters,multiplier))
        try:
            importChannels = []
            if file.startswith('http'):
                url  = file
                file = os.path.join(TEMP_LOC,'%s'%(slugify(url)))
                setURL(url,file)
                
            stations = self._load(file)
            for key, value in list(filters.items()):
                if key == 'slug' and value:
                    importChannels.extend(self.cleanSelf(stations,'id',value)[0])
                elif key == 'providers' and value:
                    for provider in value: 
                        importChannels.extend(self.cleanSelf(stations,'provider',provider)[0])
            
            #no filter found, import all stations.
            if not importChannels: importChannels.extend(stations)
            importChannels = self.sortStations(list(self.chkImport(importChannels,multiplier)))
            self.log('importM3U, found import stations = %s'%(len(importChannels)))
            self.M3UDATA.get('stations',[]).extend(importChannels)
        except Exception as e: self.log("importM3U, failed! %s"%(e), xbmc.LOGERROR)
        return importChannels
        
        
    def chkImport(self, stations, multiplier=1):
        def roundup(x):
            return x if x % 1000 == 0 else x + 1000 - x % 1000
            
        def frange(start, stop, step):
          while not xbmc.Monitor().abortRequested() and start < stop:
            yield float(start)
            start += decimal.Decimal(step)

        stations  = self.sortStations(stations)
        chstart   = roundup((CHANNEL_LIMIT * len(CHAN_TYPES)+1))
        chmin     = int(chstart + (multiplier*1000))
        chmax     = int(chmin + (CHANNEL_LIMIT))
        chrange   = list(frange(chmin,chmax,0.1))
        leftovers = []
        self.log('chkImport, stations = %s, multiplier = %s, chstart = %s, chmin = %s, chmax = %s'%(len(stations),multiplier,chstart,chmin,chmax))
        ## check tvg-chno for conflict, use multiplier to modify org chnum.
        for mitem in stations:
            if len(chrange) == 0:
                self.log('chkImport, reached max import')
                break
            elif mitem['number'] < CHANNEL_LIMIT: 
                newnumber = (chmin+mitem['number'])
                if newnumber in chrange:
                    chrange.remove(newnumber)
                    mitem['number'] = newnumber
                    yield mitem
                else: leftovers.append(mitem)
            else: leftovers.append(mitem)
        
        for mitem in leftovers:
            if len(chrange) == 0:
                self.log('chkImport, reached max import')
                break
            else:
                mitem['number'] = chrange.pop(0)
                yield mitem
