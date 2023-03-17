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

from globals    import *
from channels   import Channels

M3U_TEMP = {"id"                : "",
            "type"              : "",
            "number"            : 0,
            "name"              : "",
            "logo"              : "",
            "path"              : [],
            "group"             : [],
            "rules"             : [],
            "catchup"           : "vod",
            "radio"             : False,
            "favorite"          : False,
            "label"             : "",
            "url"               : "",
            "tvg-shift"         : "",
            "x-tvg-url"         : "",
            "media"             : "",
            "media-dir"         : "",
            "media-size"        : "",
            "catchup-source"    : "",
            "catchup-days"      : "",
            "catchup-correction": "",
            "provider"          : "",
            "provider-type"     : "",
            "provider-logo"     : "",
            "provider-countries": "",
            "provider-languages": "",
            "kodiprops"         : []}

class M3U:
    def __init__(self):
        self.M3UDATA = {'data':'#EXTM3U tvg-shift="" x-tvg-url="" x-tvg-id="" catchup-correction=""', 'channels':self.cleanSelf(self._load())}
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _verify(self, stations):
        def _log(station):
            self.log('_verify, found = %s'%(station))
            return station
        #remove abandoned m3u entries; Stations that are not found in the channel list.
        return [_log(station) for station in stations for channel in Channels().getChannels() if channel.get('id') == station.get('id',str(random.random()))]


    def _load(self, file=M3UFLEPATH):
        self.log('loadM3U, file = %s'%file)
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
            for idx, line in enumerate(lines):
                line = line.rstrip()
                
                if line.startswith('#EXTM3U'):
                    data = {'tvg-shift'         :re.compile('tvg-shift=\"(.*?)\"'          , re.IGNORECASE).search(line),
                            'x-tvg-url'         :re.compile('x-tvg-url=\"(.*?)\"'          , re.IGNORECASE).search(line),
                            'catchup-correction':re.compile('catchup-correction=\"(.*?)\"' , re.IGNORECASE).search(line)}
                            
                    # if SETTINGS.getSettingInt('Import_XMLTV_TYPE') == 2 and file == os.path.join(TEMP_LOC,slugify(SETTINGS.getSetting('Import_M3U_URL'))):
                        # if data.get('x-tvg-url').group(1):
                            # self.log('loadM3U, using #EXTM3U "x-tvg-url"')
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
                             'media-size'        :re.compile('media-size=\"(.*?)\"'         , re.IGNORECASE).search(line)}
                    
                    mitem = self.getMitem()
                    mitem.update({'number' :chCount,
                                  'logo'   :LOGO,
                                  'catchup':''}) #set default parameters
                    
                    for key, value in match.items():
                        if value is None:
                            if data.get(key,None) is not None:
                                self.log('loadM3U, using #EXTM3U "%s" value for #EXTINF'%(key))
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
                            mitem[key] = list(filter(None,list(set((value.group(1)).split(';')))))
                        elif key == 'radio':
                            mitem[key] = (value.group(1)).lower() == 'true'
                        else:
                            mitem[key] = value.group(1)

                    for nidx in range(idx+1,len(lines)):
                        try:
                            nline = lines[nidx].rstrip()
                            if   nline.startswith('#EXTINF:'): break
                            elif nline.startswith('#EXTGRP'):
                                prop = re.compile('^#EXTGRP:(.*)$', re.IGNORECASE).search(nline)
                                if prop is not None: 
                                    mitem['group'].append(prop.group(1).split(';'))
                                    mitem['group'] = list(set(mitem['group']))
                            elif nline.startswith('#KODIPROP:'):
                                prop = re.compile('^#KODIPROP:(.*)$', re.IGNORECASE).search(nline)
                                if prop is not None:
                                    mitem.setdefault('kodiprops',[]).append(prop.group(1))
                            # elif nline.startswith('#EXTVLCOPT'):
                            # elif nline.startswith('#EXT-X-PLAYLIST-TYPE'):
                            elif nline.startswith('##'): continue
                            elif not nline: continue
                            else: mitem['url'] = nline
                        except Exception as e: self.log('loadM3U, error parsing m3u! %s'%(e))
                            
                    mitem['name']     = (mitem.get('name','')     or mitem.get('label',''))
                    mitem['label']    = (mitem.get('label','')    or mitem.get('name',''))
                    mitem['favorite'] = (mitem.get('favorite','') or False)
                    
                    if LANGUAGE(32019) in mitem['group'] and not mitem['favorite']:
                        mitem['favorite'] = True
                        
                    if not mitem.get('id','') or not mitem.get('name','') or not mitem.get('number',''): 
                        self.log('loadM3U, SKIPPED MISSING META m3u item = %s'%mitem)
                        continue
                        
                    self.log('loadM3U, m3u item = %s'%mitem)
                    yield mitem
        
        
    def _save(self, file=M3UFLEPATH):
        self.log('_save')
        with fileLocker(GLOBAL_FILELOCK):
            fle = FileAccess.open(file, 'w')
            self.log('_save, saving to %s'%(file))
            fle.write('%s\n'%(self.M3UDATA['data']))
            
            keys = list(self.getMitem().keys())
            line = '#EXTINF:-1 tvg-chno="%s" tvg-id="%s" tvg-name="%s" tvg-logo="%s" group-title="%s" radio="%s" catchup="%s" %s,%s\n'
            self.M3UDATA['channels'] = self.sortStations(self.M3UDATA.get('channels',[]))
            
            for channel in self.M3UDATA['channels']:
                optional = ''
                if not channel: continue
                    
                # write optional m3u parameters.
                for key, value in channel.items():
                    if key in keys: continue
                    elif value: optional += '%s="%s" '%(key,value)
                        
                fle.write(line%(channel['number'],
                                channel['id'],
                                channel['name'],
                                channel['logo'],
                                ';'.join(channel['group']),
                                channel['radio'],
                                channel['catchup'],
                                optional,
                                channel['label']))
                                 
                if channel.get('kodiprops',[]):
                    fle.write('%s\n'%('\n'.join(['#KODIPROP:%s'%(prop) for prop in channel['kodiprops']])))
                fle.write('%s\n'%(channel['url']))
            fle.close()
        return True
        
        
    def cleanSelf(self, channels, key='id', slug='@%s'%(slugify(ADDON_NAME))):
        self.log('cleanSelf, slug = %s'%(slug)) # remove imports (Non PseudoTV Live)
        if not slug: return channels
        return list(filter(lambda line:line.get(key,'').endswith(slug), self._verify(channels)))
        
        
    def cleanLogo(self, logo):
        self.log('cleanLogo, logo Out = %s'%(logo))
        return logo
               
               
    def sortStations(self, channels):
        return sorted(channels, key=lambda k: k['number'])
        
        
    def getMitem(self):
        return M3U_TEMP.copy()
        
        
    def getShift(self):
        self.log('getShift') 
        return ((time.mktime(time.localtime()) - time.mktime(time.gmtime())) / 60 / 60)

    
    def getStations(self):
        stations = self.sortStations(self.M3UDATA.get('channels',[]))
        self.log('getStations, channels = %s'%(len(stations)))
        return stations
        
                
    def findStation(self, item, channels=None):
        if channels is None: channels = self.M3UDATA.get('channels',[])
        for idx, eitem in enumerate(channels):
            if (item.get('id') == eitem.get('id',str(random.random()))) or (item.get('type','').lower() == eitem.get('type',str(random.random())).lower() and item.get('name','').lower() == eitem.get('name',str(random.random())).lower()):
                self.log('findChannel, found item = %s'%(eitem))
                return idx, eitem
        return None, {}
        
        
    def addStation(self, citem):
        self.log('addStation, channel item = %s'%(citem))
        idx, line = self.findStation(citem)
        mitem = self.getMitem()
        mitem.update(citem)
        mitem['label']         = citem['name'] #todo channel manager opt to change channel 'label' leaving 'name' static for channelid purposes.
        mitem['logo']          = self.cleanLogo(citem['logo'])
        mitem['provider']      = ADDON_NAME
        mitem['provider-type'] = 'local'
        mitem['provider-logo'] = HOST_LOGO
        if idx is None:  self.M3UDATA.get('channels',[]).append(mitem)
        else:            self.M3UDATA.get('channels',[])[idx] = mitem # replace existing channel
        return True
        

    def delStation(self, citem):
        self.log('delStation id = %s'%(citem['id']))
        idx, line = self.findStation(citem)
        if idx is not None: self.M3UDATA['channels'].pop(idx)
        return True
        
        
    def importM3U(self, file, filters={}, multiplier=1):
        self.log('importM3U, file = %s, filters = %s, multiplier = %s'%(file,filters,multiplier))
        try:
            importChannels = []
            if file.startswith('http'):
                url  = file
                file = os.path.join(TEMP_LOC,'%s'%(slugify(url)))
                setURL(url,file)
                
            channels = self.loadM3U(file)
            for key, value in filters.items():
                if key == 'slug' and value:
                    importChannels.extend(self.cleanSelf(channels,'id',value))
                elif key == 'providers' and value:
                    for provider in value: 
                        importChannels.extend(self.cleanSelf(channels,'provider',provider))
            
            #no filter found, import all channels.
            if not importChannels: importChannels.extend(channels)
            importChannels = self.sortStations(list(self.chkImport(importChannels,multiplier)))
            self.log('importM3U, found import stations = %s'%(len(importChannels)))
            self.M3UDATA.get('channels',[]).extend(importChannels)
        except Exception as e: self.log("importM3U, failed! %s"%(e), xbmc.LOGERROR)
        return importChannels
        
        
    def chkImport(self, channels, multiplier=1):
        def roundup(x):
            return x if x % 1000 == 0 else x + 1000 - x % 1000
            
        def frange(start, stop, step):
          while not xbmc.Monitor().abortRequested() and start < stop:
            yield float(start)
            start += decimal.Decimal(step)

        channels  = self.sortStations(channels)
        chstart   = roundup((CHANNEL_LIMIT * len(CHAN_TYPES)+1))
        chmin     = int(chstart + (multiplier*1000))
        chmax     = int(chmin + (CHANNEL_LIMIT))
        chrange   = list(frange(chmin,chmax,0.1))
        leftovers = []
        self.log('chkImport, channels = %s, multiplier = %s, chstart = %s, chmin = %s, chmax = %s'%(len(channels),multiplier,chstart,chmin,chmax))
        ## check tvg-chno for conflict, use multiplier to modify org chnum.
        for mitem in channels:
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