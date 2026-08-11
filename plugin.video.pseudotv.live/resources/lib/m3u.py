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

from typing      import Any, Generator, List, Tuple, Optional, Dict
from variables   import *
from channels    import Channels
from fileaccess  import FileAccess, FileLock

def clearM3UCache():
    """Clear the M3U cache entry (utilities cleanup).

    The playlist now lives in cache.db, so "cleaning" it means dropping the
    m3u.data key rather than deleting any physical export file.
    """
    Globals.settings.clrCacheSetting(M3U_CACHE_KEY)


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


    def __init__(self, file: str = M3UFLEPATH, writable: bool = False):
        self._lock       = DATA_LOCK
        self.EPGArtwork  = int((Globals.settings.getSetting('EPG_Artwork') or "0"))
        self.writable    = writable
        self.stationFile = file
        self.M3UDATA     = {}
        stations, recordings = self.cleanSelf(list(self._load()))
        self.M3UDATA = {'data'      : '#EXTM3U tvg-shift="" x-tvg-url="%s" x-tvg-id="" catchup-correction=""' % ('http://%s/%s' % (Globals.properties.getRemoteHost(), XMLTVFLE)),
                        'stations'  : stations,
                        'recordings': recordings}
        self._initial_ids = {s.get('id') for s in stations if s.get('id')}


    def __enter__(self) -> 'M3U':
        self._saved = False
        return self


    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        try:
            if getattr(self, 'writable', False) and not getattr(self, '_saved', False):
                self._save()
        except Exception:
            pass
            
            
    def __del__(self):
        try:
            if getattr(self, 'writable', False) and not getattr(self, '_saved', False):
                self._save()
        except Exception: pass
        
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def _load(self) -> Generator[Dict[str, Any], None, None]:
        self.log('_load, cache=%s' % self.stationFile)
        payload = Globals.settings.getCacheSetting(M3U_CACHE_KEY) or {}
        stations   = payload.get('stations')   or []
        recordings = payload.get('recordings') or []
        if stations or recordings:
            # data lives in the SQLite cache — serve it directly (no file I/O)
            yield from (recordings + stations)
            return
        # Legacy migration: first run after the file->cache switch, or after a
        # cache clear — parse the on-disk export once; the next writable _save
        # populates the cache so subsequent loads hit SQLite.
        yield from self._load_file()


    def _load_file(self) -> Generator[Dict[str, Any], None, None]:
        self.log('_load_file, file=%s' % self.stationFile)
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


    def _save(self) -> bool:
        self.M3UDATA['data'] = '#EXTM3U tvg-shift="" x-tvg-url="%s" x-tvg-id="" catchup-correction=""' % (
                               'http://%s/%s' % (Globals.properties.getRemoteHost(), XMLTVFLE) )
        self.M3UDATA['stations'] = self.sortStations(self.M3UDATA.get('stations', []))
        self.M3UDATA['recordings'] = self.sortStations(self.M3UDATA.get('recordings', []), key='name')
        
        self.log('_save, writable=%s, file=%s, stations=%d, recordings=%d' % (
            self.writable, self.stationFile, len(self.M3UDATA['stations']), len(self.M3UDATA['recordings'])
        ))
        
        if self.writable:
            # Persist to the SQLite cache (transactional; avoids file-lock races with
            # the HTTP server / pvr.iptvsimple polling). Version token bumps on every
            # save so the HTTP render cache invalidates.
            old = Globals.settings.getCacheSetting(M3U_CACHE_KEY) or {}
            Globals.settings.setCacheSetting(M3U_CACHE_KEY, {
                'stations'  : self.M3UDATA['stations'],
                'recordings': self.M3UDATA['recordings'],
                'updated'   : time.time(),
                'version'   : (old.get('version', 0) or 0) + 1}, life=-1)
            # Optional physical export for local-file PVR configs / external tools.
            if Globals.settings.getSettingBool('Enable_File_Export'):
                self._save_export()

            self._saved = True
            # Update PVR status with current M3U/XMLTV data
            status   = Globals.settings.instances.updatePVRStatus(Globals.properties.getRemoteHost(), Globals.properties.getFriendlyName())
            stations = self.getStations()
            current_ids = {s.get('id') for s in stations if s.get('id')}
            status['m3u']['channel_ids'] = current_ids
            status['m3u']['last_write'] = time.time()
            Globals.settings.instances._computeDerived(status)
            # Only force PVR reload if station set actually changed
            if current_ids != self._initial_ids:
                Globals.properties.setPropTimer('chkPVRRefresh')
            Globals.properties.notifyDataChanged('m3u')
            return True
        return False


    def _save_export(self) -> bool:
        """Write the physical pseudotv.m3u export (atomic temp+rename).

        Only runs when Enable_File_Export is on; keeps the legacy file on disk
        for local-file pvr.iptvsimple configs or third-party tooling. The SQLite
        cache remains the source of truth.
        """
        try:
            tmp_file = '%s.tmp' % (self.stationFile)
            with FileAccess.open(tmp_file, 'w') as fle:
                self._write(fle)
            if FileAccess.rename(tmp_file, self.stationFile):
                self.log('_save_export, atomic write complete')
            else:
                self.log("_save_export, atomic rename failed, retrying direct write", xbmc.LOGWARNING)
                FileAccess.delete(tmp_file)
                with FileAccess.open(self.stationFile, 'w') as fle:
                    self._write(fle)
            return True
        except Exception as e:
            self.log("_save_export failed! %s" % e, xbmc.LOGERROR)
            try: FileAccess.delete(tmp_file)
            except Exception: pass
            return False


    def _write(self, fle) -> None:
        """Write the full M3U body to a file-like object (data header + stations).

        Shared by _save (atomic temp+rename) and render (in-memory HTTP serving)
        so both produce byte-identical output.
        """
        fle.write('%s\n' % (self.M3UDATA['data']))
        opts = list(self.getMitem().keys())
        line_template = '#EXTINF:-1 tvg-chno="%s" tvg-id="%s" tvg-name="%s" tvg-logo="%s" group-title="%s" radio="%s" catchup="%s" %s,%s\n'
        for station in (self.M3UDATA['recordings'] + self.M3UDATA['stations']):
            try:
                optional  = ''
                kodiprops = station.get('kodiprops', [])
                extvlcopt = station.get('extvlcopt', [])
                xplaylist = station.get('x-playlist-type', '')
                # Exclude template keys so attrs are not duplicated in the EXTINF line.
                skip = {'kodiprops', 'extvlcopt', 'x-playlist-type', 'url', 'number', 'id', 'name', 'logo', 'group', 'radio', 'catchup'}
                for key, value in station.items():
                    if key not in skip and key in opts and str(value):
                        optional += '%s="%s" ' % (key, value)
                fle.write(line_template % (
                    station.get('number', ''),
                    station.get('id', ''),
                    station.get('name', ''),
                    Globals._toWebImage(station.get('logo', '')),
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

    def render(self, fle, stations=None, recordings=None):
        """Render M3U content to a file-like object without touching disk.

        Reuses the exact same template and logic as _save() lines 236-272.
        Used by the HTTP server to serve filtered M3U content based on channels.json.
        """
        if stations is None:   stations = self.getStations()
        if recordings is None: recordings = self.getRecordings()
        # Build a str buffer, then delegate to _write so render and _save share the
        # exact same template logic (byte-identical output).
        import io
        buf = io.StringIO()
        saved_stations = self.M3UDATA['stations']
        saved_recordings = self.M3UDATA['recordings']
        try:
            self.M3UDATA['stations'] = stations
            self.M3UDATA['recordings'] = recordings
            self._write(buf)
        finally:
            self.M3UDATA['stations'] = saved_stations
            self.M3UDATA['recordings'] = saved_recordings
        fle.write(buf.getvalue().encode(DEFAULT_ENCODING))


    def _verify(self, stations: Optional[List[Dict[str, Any]]] = None, recordings: Optional[List[Dict[str, Any]]] = None, chkPath: Optional[bool] = None) -> List[Dict[str, Any]]:
        if chkPath is None:
            chkPath = Globals.settings.getSettingBool('Clean_Recordings')
            
        if stations:
            channels = Channels(Globals.getChannelKey()).getChannels()
            chan_ids = {channel.get('id') for channel in channels if channel.get('id')}
            verified_stations = [station for station in stations if station.get('id') in chan_ids]
            self.log('_verify, stations %d -> %d (matched active channels)' % (len(stations), len(verified_stations)))
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
        
    def cleanSelf(self, items: List[Dict[str, Any]], key: str = 'id', slug: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
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


    def sortStations(self, stations: List[Dict[str, Any]], key: str = 'number') -> List[Dict[str, Any]]:
        try:              
            return sorted(stations, key=itemgetter(key))
        except Exception: 
            return stations
        
    def getM3U(self) -> Dict[str, Any]:
        return self.M3UDATA
        
    def getMitem(self) -> Dict[str, Any]:
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
            
    def getTZShift(self) -> float:
        self.log('getTZShift')
        return ((time.mktime(time.localtime()) - time.mktime(time.gmtime())) / 60.0 / 60.0)


    def getStations(self) -> List[Dict[str, Any]]:
        stations = self.sortStations(self.M3UDATA.get('stations', []))
        self.log('getStations, stations = %s' % (len(stations)))
        return stations
              
    def getRecordings(self) -> List[Dict[str, Any]]:
        recordings = self.sortStations(self.M3UDATA.get('recordings', []), key='name')
        self.log('getRecordings, recordings = %s' % (len(recordings)))
        return recordings


    # =========================================================================
    # HTTP Content Filtering
    # =========================================================================
    # Filters are applied in sequence to M3U stations before serving to
    # pvr.iptvsimple via the HTTP server. pvr.iptvsimple uses the M3U to
    # determine which channels appear in Kodi's EPG — missing M3U entry
    # means the channel is invisible in the guide, regardless of XMLTV data.
    #
    # Filter chain (applied in order):
    #   1. _filterByChannel — removes stations not in channels.json
    #   2. _filterM3UByXMLTV — removes stations with no EPG programmes
    #
    # XMLTV is NOT filtered — it's served raw. Only M3U filtering matters
    # because pvr.iptvsimple ignores XMLTV entries for channels absent from M3U.
    # =========================================================================

    def _filterByChannel(self, stations: List[Dict[str, Any]], allowed_ids: set) -> List[Dict[str, Any]]:
        """Keep only stations whose 'id' exists in channels.json.

        Why: channels.json is the master list of configured channels. Stations
        removed from channels.json (e.g. during autotune or manual edits)
        should not appear in the served M3U, even if the cached M3U file
        still contains them. This ensures pvr.iptvsimple only sees channels
        that are actively managed by PseudoTV.
        """
        if not allowed_ids:
            return []
        return [s for s in stations if s.get('id') in allowed_ids]

    def _filterM3UByXMLTV(self, stations: List[Dict[str, Any]], channel_ids_with_programmes: set) -> List[Dict[str, Any]]:
        """Remove stations that have no corresponding XMLTV programmes.

        Why: A channel in M3U without XMLTV data shows as an empty entry
        in Kodi's EPG guide — no title, no plot, no artwork. These are
        useless to the user and clutter the guide. This happens when:
          - The channel's content source is unreachable (SMB share down)
          - The channel's smart playlist resolved to zero items
          - All items were filtered out (extras, strm files, etc.)
          - The channel was just created and no EPG data was generated yet

        The filter reads the XMLTV programmes to find which channel IDs
        have at least one programme, then drops M3U stations not in that set.
        """
        if not channel_ids_with_programmes:
            return stations  # no programmes at all — safety: don't filter
        return [s for s in stations if s.get('id') in channel_ids_with_programmes]

    def _filterM3UByCurrentGuide(self, stations: List[Dict[str, Any]], current_ids: set) -> List[Dict[str, Any]]:
        """Remove stations whose EPG does not cover the current time.

        Why: A channel with only past programmes (EPG ends hours ago) shows an
        empty guide row — nothing is airing "now" and nothing is scheduled.
        Until the channel is rebuilt with fresh EPG the guide would be blank,
        so keep the channel invisible to pvr.iptvsimple. `current_ids` is the
        set of channel IDs having a programme whose [start, stop) window
        contains `now` or starts shortly after (MIN_EPG_DURATION look-ahead).
        """
        if not current_ids:
            return stations  # no coverage data — safety: don't filter
        return [s for s in stations if s.get('id') in current_ids]

    def getFilteredStations(self, programmes: Optional[list] = None) -> List[Dict[str, Any]]:
        """Return stations filtered for HTTP serving to pvr.iptvsimple.

        Two-layer filter:
          1. channels.json membership — only configured channels are served.
          2. XMLTV presence — channels that exist but have NO guide data at all
             (e.g. a content source that resolved to nothing) are dropped from the
             M3U so they don't appear as blank rows in Kodi.

        Channels that DO have some guide data but lack current coverage, are
        temporarily missing / mid-build, or have less than the minimum EPG duration
        of future data are KEPT here — the served XMLTV (renderWithPlaceholders)
        injects an informative "No Guide Data" placeholder for them.

        `programmes` (optional) lets callers pass an already-loaded XMLTV programme
        list so the serve path doesn't load XMLTV twice.
        """
        stations = self.getStations()

        # Filter 1: Only stations in channels.json
        allowed_ids = {ch.get('id') for ch in Channels(Globals.getChannelKey()).getChannels() if ch.get('id')}
        stations = self._filterByChannel(stations, allowed_ids)

        # Filter 2: Only stations with at least one XMLTV programme (drop no-guide channels)
        if programmes is None:
            from xmltvs import XMLTVS
            programmes = XMLTVS().getProgrammes()
        channel_ids_with_programmes = {p.get('channel') for p in programmes if p.get('channel')}
        stations = self._filterM3UByXMLTV(stations, channel_ids_with_programmes)

        return stations
               
    def getStationItem(self, sitem: Dict[str, Any]) -> Dict[str, Any]:
        if 300 in list(sitem.get('rules', {}).keys()): # PauseRule (myId 300) -> resume URL
            sitem['url'] = RESUME_URL.format(addon=ADDON_ID, name=Globals._quoteString(sitem['name']), chid=Globals._quoteString(sitem['id']))
        elif sitem.get('radio'): 
            sitem['url'] = RADIO_URL.format(addon=ADDON_ID, name=Globals._quoteString(sitem['name']), chid=Globals._quoteString(sitem['id']), radio=str(sitem['radio']), vid='{catchup-id}')
        elif sitem.get('catchup'):
            sitem['catchup-source'] = BROADCAST_URL.format(addon=ADDON_ID, name=Globals._quoteString(sitem['name']), chid=Globals._quoteString(sitem['id']), vid='{catchup-id}')
            sitem['url'] = LIVE_URL.format(addon=ADDON_ID, name=Globals._quoteString(sitem['name']), chid=Globals._quoteString(sitem['id']), vid='{catchup-id}', now='{lutc}', start='{utc}', duration='{duration}', stop='{utcend}')
        else:  
            sitem['url'] = TV_URL.format(addon=ADDON_ID, name=Globals._quoteString(sitem['name']), chid=Globals._quoteString(sitem['id']))
        return sitem
    
    def getRecordItem(self, fitem: Dict[str, Any], seek: int = 0) -> Dict[str, Any]:
        group = LANGUAGE(30119) if seek <= 0 else LANGUAGE(30152)
        ritem = self.getMitem()
        ritem['provider'] = '%s (%s)' % (ADDON_NAME, Globals.properties.getFriendlyName())
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
        ritem['id'] = Globals._getRecordID(ritem['name'], (fitem.get('originalfile') or fitem.get('file', '')), ritem['number'], Globals.settings.getMYUUID())
        ritem['url'] = DVR_URL.format(addon=ADDON_ID, title=Globals._quoteString(ritem['label']), chid=Globals._quoteString(ritem['id']), vid=(FileAccess._encodeString((fitem.get('originalfile') or fitem.get('file', '')))), seek=seek, duration=fitem.get('duration', 0))
        return ritem
        
    def delStation(self, citem: Dict[str, Any]) -> bool:
        with self._lock:
            try: 
                idx, _ = self.findStation(citem)
                if idx is not None:
                    self.M3UDATA['stations'].pop(idx)
                    self.log('[%s] delStation, channel deleted!' % (citem['id']), xbmc.LOGINFO)
                    return True
            except Exception as e: 
                self.log('[%s] delStation failed: %s' % (citem.get('id',''), e), xbmc.LOGDEBUG)
            return False


    def delRecording(self, ritem: Dict[str, Any]) -> bool:
        with self._lock:
            try: 
                idx, _ = self.findRecording(ritem)
                if idx is not None:
                    self.M3UDATA['recordings'].pop(idx)
                    self.log('[%s] delRecording, channel deleted!' % (ritem['id']), xbmc.LOGINFO)
                    return True
            except Exception as e: 
                self.log('[%s] delRecording failed: %s' % (ritem.get('id',''), e), xbmc.LOGDEBUG)
            return False
            
    def addStation(self, citem: Dict[str, Any]) -> bool:
        with self._lock:
            mitem = self.getMitem()
            mitem.update(citem)            
            mitem['label'] = citem['name'] 
            mitem['logo'] = citem['logo']
            mitem['realtime'] = False
            mitem['provider'] = '%s (%s)' % (ADDON_NAME, Globals.properties.getFriendlyName())
            mitem['provider-type'] = 'audio' if citem.get('radio', False) else 'video'
            mitem['provider-logo'] = LOGO_HOST
            
            self.delStation(citem)
            self.M3UDATA.setdefault('stations', []).append(mitem)
            self.log('addStation, [%s] adding channel %s' % (citem["id"], citem["name"]), xbmc.LOGINFO)
            return True
        
    def addRecording(self, ritem: Dict[str, Any]) -> bool:
        with self._lock:
            self.delRecording(ritem)
            self.M3UDATA.setdefault('recordings', []).append(ritem)
            self.log('addRecording, [%s] adding recording %s' % (ritem["id"], ritem["name"]), xbmc.LOGINFO)
            return True
        
    def findStation(self, citem: Dict[str, Any]) -> Tuple[Optional[int], Dict[str, Any]]:
        c_id = citem.get('id')
        c_url_lower = citem.get('url', '').lower() if citem.get('url') else None
        
        for idx, eitem in enumerate(self.M3UDATA.get('stations', [])):
            if c_id and c_id == eitem.get('id'):
                return idx, eitem
            if c_url_lower and c_url_lower == eitem.get('url', '').lower():
                return idx, eitem
        return None, {}
        
    def findRecording(self, ritem: Dict[str, Any]) -> Tuple[Optional[int], Dict[str, Any]]:
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