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
# https://github.com/kodi-pvr/pvr.iptvsimple#supported-m3u-and-xmltv-elements

# -*- coding: utf-8 -*-

from variables     import *
from channels    import Channels
from fileaccess  import FileAccess, FileLock

class M3U(object):
    _RE_GLOBAL = {
        'tvg-shift': re.compile(r'tvg-shift="([^"]*)"', re.IGNORECASE),
        'x-tvg-url': re.compile(r'x-tvg-url="([^"]*)"', re.IGNORECASE),
        'catchup-correction': re.compile(r'catchup-correction="([^"]*)"', re.IGNORECASE)
    }

    _RE_TAGS = {
        'label': re.compile(r',(.*)', re.IGNORECASE),
        'id': re.compile(r'tvg-id="([^"]*)"', re.IGNORECASE),
        'name': re.compile(r'tvg-name="([^"]*)"', re.IGNORECASE),
        'group': re.compile(r'group-title="([^"]*)"', re.IGNORECASE),
        'number': re.compile(r'tvg-chno="([^"]*)"', re.IGNORECASE),
        'logo': re.compile(r'tvg-logo="([^"]*)"', re.IGNORECASE),
        'radio': re.compile(r'radio="([^"]*)"', re.IGNORECASE),
        'tvg-shift': re.compile(r'tvg-shift="([^"]*)"', re.IGNORECASE),
        'catchup': re.compile(r'catchup="([^"]*)"', re.IGNORECASE),
        'catchup-source': re.compile(r'catchup-source="([^"]*)"', re.IGNORECASE),
        'catchup-days': re.compile(r'catchup-days="([^"]*)"', re.IGNORECASE),
        'catchup-correction': re.compile(r'catchup-correction="([^"]*)"', re.IGNORECASE),
        'provider': re.compile(r'provider="([^"]*)"', re.IGNORECASE),
        'provider-type': re.compile(r'provider-type="([^"]*)"', re.IGNORECASE),
        'provider-logo': re.compile(r'provider-logo="([^"]*)"', re.IGNORECASE),
        'provider-countries': re.compile(r'provider-countries="([^"]*)"', re.IGNORECASE),
        'provider-languages': re.compile(r'provider-languages="([^"]*)"', re.IGNORECASE),
        'media': re.compile(r'media="([^"]*)"', re.IGNORECASE),
        'media-dir': re.compile(r'media-dir="([^"]*)"', re.IGNORECASE),
        'media-size': re.compile(r'media-size="([^"]*)"', re.IGNORECASE),
        'realtime': re.compile(r'realtime="([^"]*)"', re.IGNORECASE)
    }

    _RE_EXTGRP    = re.compile(r'^#EXTGRP:(.*)$', re.IGNORECASE)
    _RE_KODIPROP  = re.compile(r'^#KODIPROP:(.*)$', re.IGNORECASE)
    _RE_EXTVLCOPT = re.compile(r'^#EXTVLCOPT:(.*)$', re.IGNORECASE)
    _RE_WEBPROP   = re.compile(r'^#WEBPROP:(.*)$', re.IGNORECASE)
    _RE_XPLAYLIST = re.compile(r'^#EXT-X-PLAYLIST-TYPE:(.*)$', re.IGNORECASE)

    def __init__(self, file=M3UFLEPATH, writable=False):
        self.EPGArtwork  = int((REAL_SETTINGS.getSetting('EPG_Artwork') or "0"))
        self.writable    = writable
        self.stationFile = file
        self.M3UDATA     = {}
        
        stations, recordings = self.cleanSelf(list(self._load()))
        self.M3UDATA = { 'data': '#EXTM3U tvg-shift="" x-tvg-url="%s" x-tvg-id="" catchup-correction=""' % (
                         'http://%s/%s' % (Globals.PROPERTIES.getRemoteHost(), XMLTVFLE) ),
                         'stations': stations,
                         'recordings': recordings }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if getattr(self, 'writable', False): self._save()
            self.log('__exit__, writable = %s' % (getattr(self, 'writable', False)))
        except Exception: pass
            
    def __del__(self):
        try:
            if getattr(self, 'writable', False): self._save()
            self.log('__del__, writable = %s' % (getattr(self, 'writable', False)))
        except Exception: 
            pass
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return Globals._log(f"{self.__class__.__name__}: {msg}", level)

    def _load(self):
        self.log('_load, file = %s' % self.stationFile)
        lines = []
        if FileAccess.exists(self.stationFile): 
            fle = None
            try:
                fle = FileAccess.open(self.stationFile, 'r')
                lines = fle.readlines()
            except Exception as e: 
                self.log(f"Error reading file lines: {e}", xbmc.LOGERROR)
                lines = []
            finally:
                if fle and hasattr(fle, 'close'): 
                    fle.close()
            
            chCount = 0
            global_data = {}
            seen_ids = set()
            
            for idx, line in enumerate(lines):
                line = line.rstrip()
                if not line:
                    continue
                
                if line.startswith('#EXTM3U'):
                    global_data = {k: pattern.search(line) for k, pattern in self._RE_GLOBAL.items()}

                elif line.startswith('#EXTINF:'):
                    chCount += 1
                    match = {k: pattern.search(line) for k, pattern in self._RE_TAGS.items()}
                    
                    m_id = match['id'].group(1) if (match['id'] and match['id'].group(1)) else None
                    if m_id:
                        if m_id in seen_ids:
                            self.log('_load, filtering duplicate %s' % m_id)
                            continue
                        seen_ids.add(m_id)
                    
                    mitem = self.getMitem()
                    mitem.update({
                        'number': chCount,
                        'logo': LOGO,
                        'catchup': ''
                    })
                    
                    for key, value in match.items():
                        if value is None:
                            if global_data.get(key) is not None:
                                self.log('_load, using #EXTM3U "%s" value for #EXTINF' % key)
                                value = global_data[key]
                            else: 
                                continue
                        
                        val_str = value.group(1)
                        if val_str is None:
                            continue
                            
                        if key == 'logo':
                            mitem[key] = val_str
                        elif key == 'number':
                            try:    
                                mitem[key] = int(val_str)
                            except Exception: 
                                try:
                                    mitem[key] = float(val_str)
                                except Exception:
                                    mitem[key] = chCount
                        elif key == 'group':
                            mitem[key] = [_f for _f in sorted(list(set(val_str.split(';')))) if _f]
                        elif key in ['radio', 'favorite', 'realtime', 'media']:
                            mitem[key] = val_str.lower() == 'true'
                        else:
                            mitem[key] = val_str

                    for nidx in range(idx + 1, len(lines)):
                        nline = lines[nidx].rstrip()
                        if not nline or nline.startswith('##'): 
                            continue
                        if nline.startswith('#EXTINF:'): 
                            break
                            
                        if nline.startswith('#EXTGRP'):
                            grop = self._RE_EXTGRP.search(nline)
                            if grop:
                                current_groups = mitem.get('group', [])
                                current_groups.extend(grop.group(1).split(';'))
                                mitem['group'] = sorted(list(set(current_groups)))
                        elif nline.startswith('#KODIPROP:'):
                            prop = self._RE_KODIPROP.search(nline)
                            if prop: 
                                mitem.setdefault('kodiprops', []).append(prop.group(1))
                        elif nline.startswith('#EXTVLCOPT'):
                            copt = self._RE_EXTVLCOPT.search(nline)
                            if copt:  
                                mitem.setdefault('extvlcopt', []).append(copt.group(1))
                        elif nline.startswith('#WEBPROP'):
                            web = self._RE_WEBPROP.search(nline)
                            if web:  
                                mitem.setdefault('webprops', []).append(web.group(1))
                        elif nline.startswith('#EXT-X-PLAYLIST-TYPE'):
                            xplay = self._RE_XPLAYLIST.search(nline)
                            if xplay: 
                                mitem['x-playlist-type'] = xplay.group(1)
                        else: 
                            mitem['url'] = nline

                    mitem['name']     = (mitem.get('name') or mitem.get('label') or '')
                    mitem['label']    = (mitem.get('label') or mitem.get('name') or '')
                    mitem['favorite'] = (mitem.get('favorite') or False)
                    
                    if LANGUAGE(32019) in mitem.get('group', []) and not mitem['favorite']:
                        mitem['favorite'] = True
                    
                    if not mitem.get('id') or not mitem.get('name') or not mitem.get('number'): 
                        self.log('_load, SKIPPED MISSING META m3u item = %s' % mitem)
                        continue
                        
                    self.log('_load, m3u item = %s' % mitem)
                    yield mitem

    def _save(self):
        self.M3UDATA['data'] = '#EXTM3U tvg-shift="" x-tvg-url="%s" x-tvg-id="" catchup-correction=""' % (
                               'http://%s/%s' % (Globals.PROPERTIES.getRemoteHost(), XMLTVFLE) )
        self.M3UDATA['stations'] = self.sortStations(self.M3UDATA.get('stations', []))
        self.M3UDATA['recordings'] = self.sortStations(self.M3UDATA.get('recordings', []), key='name')
        
        self.log('_save, writable = %s, file = %s\nstations = %s recordings = %s' % (
            self.writable, self.stationFile, len(self.M3UDATA['stations']), len(self.M3UDATA['recordings'])
        ))
        
        if self.writable:
            with FileLock(self.stationFile):
                fle = None
                try:
                    fle = FileAccess.open(self.stationFile, 'w')
                    fle.write('%s\n' % (self.M3UDATA['data']))
                    opts = list(self.getMitem().keys())
                    line_template = '#EXTINF:-1 tvg-chno="%s" tvg-id="%s" tvg-name="%s" tvg-logo="%s" group-title="%s" radio="%s" catchup="%s" %s,%s\n'
                    
                    for station in (self.M3UDATA['recordings'] + self.M3UDATA['stations']):
                        try:
                            optional  = ''
                            kodiprops = station.get('kodiprops', [])
                            extvlcopt = station.get('extvlcopt', [])
                            xplaylist = station.get('x-playlist-type', '')
                            
                            for key, value in station.items():
                                if key not in ['kodiprops', 'extvlcopt', 'x-playlist-type'] and key in opts and str(value):
                                    optional += '%s="%s" ' % (key, value)

                            fle.write(line_template % (
                                station.get('number', ''),
                                station.get('id', ''),
                                station.get('name', ''),
                                station.get('logo', ''),
                                ';'.join(station.get('group', [])),
                                str(station.get('radio', False)),
                                station.get('catchup', ''),
                                optional,
                                station.get('label', '')
                            ))
                                    
                            if kodiprops: 
                                fle.write('%s\n' % ('\n'.join(['#KODIPROP:%s' % prop for prop in kodiprops])))
                            if extvlcopt: 
                                fle.write('%s\n' % ('\n'.join(['#EXTVLCOPT:%s' % prop for prop in extvlcopt])))
                            if xplaylist: 
                                fle.write('#EXT-X-PLAYLIST-TYPE:%s\n' % xplaylist)
                                
                            fle.write('%s\n' % (station.get('url', '')))
                        except Exception as e:
                            self.log("_save, loop record entry failed! %s" % e, xbmc.LOGERROR)
                            continue
                    return True
                except Exception as e: 
                    self.log("_save, global write process failed! %s" % e, xbmc.LOGERROR)
                finally:
                    if fle and hasattr(fle, 'close'): 
                        fle.close()
        return False

    def _verify(self, stations=None, recordings=None, chkPath=None):
        if chkPath is None:
            chkPath = Globals.SETTINGS.getSettingBool('Clean_Recordings')
            
        if stations:
            channels = Channels().getChannels()
            chan_ids = {channel.get('id') for channel in channels if channel.get('id')}
            verified_stations = [station for station in stations if station.get('id') in chan_ids]
            self.log('_verify, stations = %s' % (len(verified_stations)))
            return verified_stations
            
        elif recordings:
            verified_recordings = []
            for recording in recordings:
                if chkPath:
                    url = recording.get('url', '')
                    parsed_query = dict(urllib.parse.parse_qsl(url))
                    vid_param = parsed_query.get('vid', '').replace('.pvr', '')
                    decoded_path = FileAccess._decodeString(vid_param) if vid_param else ''
                    if decoded_path and Globals._hasFile(decoded_path):
                        verified_recordings.append(recording)
                else:
                    if recording.get('media', False):
                        verified_recordings.append(recording)
            self.log('_verify, recordings = %s, chkPath = %s' % (len(verified_recordings), chkPath))
            return verified_recordings
        return []
        
    def cleanSelf(self, items, key='id', slug=None):
        if slug is None:
            slug = '@%s' % (Globals._slugify(ADDON_NAME))
        if not slug: 
            return items
            
        stations_raw = [st for st in items if str(st.get(key, '')).endswith(slug) and not st.get('media', False)]
        recordings_raw = [rec for rec in items if str(rec.get(key, '')).endswith(slug) and rec.get('media', False)]
        
        stations = self.sortStations(self._verify(stations=stations_raw))
        recordings = self.sortStations(self._verify(recordings=recordings_raw), key='name')
        
        self.log('cleanSelf, slug = %s, key = %s: returning: stations = %s, recordings = %s' % (slug, key, len(stations), len(recordings)))
        return stations, recordings

    def sortStations(self, stations, key='number'):
        try:              
            return sorted(stations, key=itemgetter(key))
        except Exception: 
            return stations
        
    def getM3U(self):
        return self.M3UDATA
        
    def getMitem(self):
        return {"id"                : "",
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
                "provider"          : ADDON_NAME,
                "provider-type"     : "addon",
                "provider-logo"     : LOGO_COLOR,
                "provider-countries": Globals._getCountry(),
                "provider-languages": Globals._getLanguage(),
                "x-playlist-type"   : "",
                "kodiprops"         : []}.copy()
            
    def getTZShift(self):
        self.log('getTZShift')
        return ((time.mktime(time.localtime()) - time.mktime(time.gmtime())) / 60.0 / 60.0)

    def getStations(self):
        stations = self.sortStations(self.M3UDATA.get('stations', []))
        self.log('getStations, stations = %s' % (len(stations)))
        return stations
              
    def getRecordings(self):
        recordings = self.sortStations(self.M3UDATA.get('recordings', []), key='name')
        self.log('getRecordings, recordings = %s' % (len(recordings)))
        return recordings
               
    def getStationItem(self, sitem):
        if 3000 in list(sitem.get('rules', {}).keys()): 
            sitem['url'] = RESUME_URL.format(addon=ADDON_ID, name=Globals._quoteString(sitem['name']), chid=Globals._quoteString(sitem['id']))
        elif sitem.get('radio'): 
            sitem['url'] = RADIO_URL.format(addon=ADDON_ID, name=Globals._quoteString(sitem['name']), chid=Globals._quoteString(sitem['id']), radio=str(sitem['radio']), vid='{catchup-id}')
        elif sitem.get('catchup'):
            sitem['catchup-source'] = BROADCAST_URL.format(addon=ADDON_ID, name=Globals._quoteString(sitem['name']), chid=Globals._quoteString(sitem['id']), vid='{catchup-id}')
            sitem['url'] = LIVE_URL.format(addon=ADDON_ID, name=Globals._quoteString(sitem['name']), chid=Globals._quoteString(sitem['id']), vid='{catchup-id}', now='{lutc}', start='{utc}', duration='{duration}', stop='{utcend}')
        else:  
            sitem['url'] = TV_URL.format(addon=ADDON_ID, name=Globals._quoteString(sitem['name']), chid=Globals._quoteString(sitem['id']))
        return sitem
    
    def getRecordItem(self, fitem, seek=0):
        group = LANGUAGE(30119) if seek <= 0 else LANGUAGE(30152)
        ritem = self.getMitem()
        ritem['provider'] = '%s (%s)' % (ADDON_NAME, Globals.PROPERTIES.getFriendlyName())
        ritem['provider-type'] = 'video'
        ritem['provider-logo'] = LOGO_HOST
        ritem['label'] = (fitem.get('showlabel') or '%s%s' % (fitem.get('label', ''), ' - %s' % (fitem.get('episodelabel', '')) if fitem.get('episodelabel', '') else ''))
        ritem['name'] = ritem['label']
        ritem['number'] = random.Random(str(fitem.get('id', 1))).random()
        ritem['logo'] = Globals._getThumb(fitem, opt=self.EPGArtwork)
        ritem['media'] = True
        ritem['media-size'] = str(fitem.get('size', 0))
        ritem['media-dir'] = ''
        ritem['group'] = ['%s (%s)' % (group, ADDON_NAME)]
        ritem['id'] = Globals._getRecordID(ritem['name'], (fitem.get('originalfile') or fitem.get('file', '')), ritem['number'], Globals.SETTINGS.getMYUUID())
        ritem['url'] = DVR_URL.format(addon=ADDON_ID, title=Globals._quoteString(ritem['label']), chid=Globals._quoteString(ritem['id']), vid=(FileAccess._encodeString((fitem.get('originalfile') or fitem.get('file', '')))), seek=seek, duration=fitem.get('duration', 0))
        return ritem
        
    def delStation(self, citem):
        try: 
            idx, _ = self.findStation(citem)
            if idx is not None:
                self.M3UDATA['stations'].pop(idx)
                self.log('[%s] delStation, channel deleted!' % (citem['id']), xbmc.LOGINFO)
                return True
        except Exception: 
            pass
        return False

    def delRecording(self, ritem):
        try: 
            idx, _ = self.findRecording(ritem)
            if idx is not None:
                self.M3UDATA['recordings'].pop(idx)
                self.log('[%s] delRecording, channel deleted!' % (ritem['id']), xbmc.LOGINFO)
                return True
        except Exception: 
            pass
        return False
            
    def addStation(self, citem):
        mitem = self.getMitem()
        mitem.update(citem)            
        mitem['label'] = citem['name'] 
        mitem['logo'] = citem['logo']
        mitem['realtime'] = False
        mitem['provider'] = '%s (%s)' % (ADDON_NAME, Globals.PROPERTIES.getFriendlyName())
        mitem['provider-type'] = 'audio' if citem.get('radio', False) else 'video'
        mitem['provider-logo'] = LOGO_HOST
        
        self.delStation(citem)
        self.M3UDATA.setdefault('stations', []).append(mitem)
        self.log('addStation, [%s] adding channel %s' % (citem["id"], citem["name"]), xbmc.LOGINFO)
        return True
        
    def addRecording(self, ritem):
        self.delRecording(ritem)
        self.M3UDATA.setdefault('recordings', []).append(ritem)
        self.log('addRecording, [%s] adding recording %s' % (ritem["id"], ritem["name"]), xbmc.LOGINFO)
        return True
        
    def findStation(self, citem):
        c_id = citem.get('id')
        c_url_lower = citem.get('url', '').lower() if citem.get('url') else None
        
        for idx, eitem in enumerate(self.M3UDATA.get('stations', [])):
            if c_id and c_id == eitem.get('id'):
                return idx, eitem
            if c_url_lower and c_url_lower == eitem.get('url', '').lower():
                return idx, eitem
        return None, {}
        
    def findRecording(self, ritem):
        r_id = ritem.get('id')
        r_label_lower = ritem.get('label', '').lower() if ritem.get('label') else None
        r_path = ritem.get('path', '')
        
        for idx, eitem in enumerate(self.M3UDATA.get('recordings', [])):
            if r_id and r_id == eitem.get('id'):
                return idx, eitem
            if r_label_lower and r_label_lower == eitem.get('label', '').lower():
                return idx, eitem
            if r_path and r_path.endswith('%s.pvr' % (eitem.get('name', ''))):
                return idx, eitem
        return None, {}