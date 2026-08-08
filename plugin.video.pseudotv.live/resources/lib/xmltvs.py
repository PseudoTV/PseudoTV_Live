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
import ratings

_ERROR_RE = re.compile(r'line\ (.*?),\ column\ (.*)', re.IGNORECASE)

# Module-level holder for the served XMLTV data. The 51MB XMLTV was re-parsed
# (3-pass xmltv.read_*) on every XMLTVS() construction (serve, chkPVRSync, plugin).
# Data now lives in SQLite (xmltv.channels/programmes/recordings) and is loaded
# once per save (keyed on xmltv.meta.version); subsequent loads are O(1).
_XMLTV_HOLDER = {'sig': None, 'channels': [], 'programmes': [], 'recordings': []}
_XMLTV_HOLDER_LOCK = RLock()

# Phase 2: indexed `programmes` table backing the hot stop-time/coverage queries.
# One-time DDL guard (the table persists in cache.db across processes).
_PROG_TABLE_READY = False

# buildGenres caches: the default genre mapping is static (parsed once) and the
# rendered genres.xml only changes when the programme category set changes, so
# repeated _save calls with the same categories skip the recompute entirely.
_DEFAULT_GENRES = None
_GENRE_SIG = None


# Curated Kodi-genre -> DVB genreId overrides and gap-fillers. Consulted before the
# DVB synonym/word index so ambiguous words (e.g. 'classical' -> music, not history)
# and Kodi-specific genres absent from the ETSI list ('anime', 'reality', 'mystery',
# 'sitcom', 'basketball') resolve to the colour that matches user expectation rather
# than ETSI document order.
_GENRE_ALIASES = {
    'movie': '0x10', 'drama': '0x10', 'action': '0x12', 'adventure': '0x12', 'western': '0x12', 'war': '0x12',
    'crime': '0x11', 'detective': '0x11', 'mystery': '0x11', 'thriller': '0x11', 'suspense': '0x11', 'police': '0x11',
    'scifi': '0x13', 'sci-fi': '0x13', 'science-fiction': '0x13', 'fantasy': '0x13', 'horror': '0x13', 'supernatural': '0x13', 'paranormal': '0x13',
    'comedy': '0x14', 'sitcom': '0x14', 'stand-up': '0x14', 'standup': '0x14', 'sketch': '0x14',
    'soap': '0x15', 'romance': '0x16', 'history': '0x17', 'historical': '0x17', 'classic': '0x17', 'classics': '0x17',
    'biography': '0x83', 'biographical': '0x83', 'documentary': '0x23', 'news': '0x20', 'weather': '0x21', 'current-affairs': '0x20', 'information': '0x20',
    'talk': '0x33', 'talk-show': '0x33', 'interview': '0x24', 'debate': '0x24', 'discussion': '0x24',
    'game-show': '0x31', 'quiz': '0x31', 'contest': '0x31', 'game': '0x31', 'reality': '0x30', 'variety': '0x32', 'show': '0x30',
    'sport': '0x40', 'sports': '0x40', 'football': '0x43', 'soccer': '0x43', 'rugby': '0x43', 'basketball': '0x45', 'baseball': '0x45', 'cricket': '0x45',
    'hockey': '0x49', 'tennis': '0x44', 'squash': '0x44', 'golf': '0x40', 'boxing': '0x4B', 'mma': '0x4B', 'ufc': '0x4B', 'wrestling': '0x4B', 'martial': '0x4B',
    'racing': '0x47', 'motorsport': '0x47', 'motoring': '0xA3', 'nascar': '0x47', 'formula': '0x47', 'athletics': '0x46', 'swimming': '0x48', 'skiing': '0x49', 'equestrian': '0x4A',
    'kids': '0x50', 'children': '0x50', 'family': '0x50', 'cartoon': '0x55', 'cartoons': '0x55', 'animation': '0x55', 'anime': '0x55', 'preschool': '0x51', 'youth': '0x50',
    'music': '0x60', 'musical': '0x65', 'opera': '0x65', 'broadway': '0x65', 'jazz': '0x64', 'rock': '0x61', 'pop': '0x61', 'classical': '0x62', 'country': '0x63', 'folk': '0x63',
    'rap': '0x61', 'hip-hop': '0x61', 'hiphop': '0x61', 'dance': '0x60', 'electronic': '0x61', 'edm': '0x61', 'reggae': '0x63', 'blues': '0x61', 'r&b': '0x61', 'metal': '0x61', 'punk': '0x61',
    'art': '0x70', 'arts': '0x70', 'culture': '0x70', 'fashion': '0x7B', 'literature': '0x75', 'poetry': '0x75', 'film': '0x76', 'cinema': '0x76', 'performing': '0x71',
    'politics': '0x80', 'political': '0x80', 'economics': '0x82', 'finance': '0x82', 'business': '0x82', 'social': '0x80',
    'education': '0x90', 'educational': '0x90', 'science': '0x90', 'nature': '0x91', 'animals': '0x91', 'wildlife': '0x91', 'environment': '0x91',
    'technology': '0x92', 'tech': '0x92', 'medicine': '0x93', 'medical': '0x93', 'psychology': '0x93', 'space': '0x92', 'astronomy': '0x92',
    'leisure': '0xA0', 'hobby': '0xA0', 'hobbies': '0xA0', 'travel': '0xA1', 'tourism': '0xA1', 'cooking': '0xA5', 'food': '0xA5', 'gardening': '0xA7',
    'fitness': '0xA4', 'health': '0xA4', 'cars': '0xA3', 'auto': '0xA3', 'craft': '0xA2', 'shopping': '0xA6',
    'religion': '0x73', 'religious': '0x73', 'spiritual': '0x95', 'adult': '0x18', 'mature': '0x18', 'erotic': '0x18',
    'live': '0xB3', 'special': '0xB0', 'black-and-white': '0xB1', 'local': '0xB5', 'regional': '0xB5',
}

# Lazy-built reverse index over remotes/genres.xml:
#   'exact': {synonym.lower(): genreId}  (first synonym wins)
#   'tokens': {word: genreId}            (words len>=3; later wins)
#   'by_id': {genreId: canonical entry}
_GENRE_INDEX = None


# =========================================================================
# HTTP serve helpers — filtered M3U / XMLTV / genres rendering + grouping.
# Kept here (not server.py) because XMLTVS already has both M3U and XMLTV
# class access; the HTTP handler just wires in the channel list + rule
# dispatcher. pvr.iptvsimple polls these repeatedly, so rendered bytes are
# cached keyed by the data version tokens + grouping state.
# =========================================================================
_M3U_RENDER_CACHE = {'sig': None, 'data': None}
_XMLTV_RENDER_CACHE = {'sig': None, 'data': None}


def m3u_render_signature() -> tuple:
    """Signature of the data the filtered M3U depends on.

    M3U/XMLTV live in the SQLite cache, so the render cache keys off the data
    version tokens rather than file mtime/size. A data write bumps the token
    and invalidates the render; nothing else does.
    """
    def _sig(key: str, field: str):
        try:
            v = Globals.settings.getCacheSetting(key) or {}
            return v.get(field)
        except Exception:
            return None
    return (_sig(M3U_CACHE_KEY, 'version'), _sig(XMLTV_META_KEY, 'version'), Globals.getChannelKey(),
            Globals.settings.getSetting('Enable_Grouping'))


def xmltv_render_signature() -> tuple:
    """Signature of the data the served XMLTV depends on.

    Same inputs as the M3U render signature (XMLTV + M3U + channels.json +
    grouping state) so both caches invalidate together — the served XMLTV
    mirrors the filtered M3U, so a change in channels.json, the M3U or the
    grouping toggle must re-render it too.
    """
    return m3u_render_signature()


def applyGrouping(stations: list, channels: list) -> list:
    """On-the-fly channel grouping for the served M3U.

    Re-runs the same grouping rules the builder applies (_cleanGroups) on the
    served station set so toggling Enable_Grouping — or editing a channel's
    group/favorite/type — takes effect on the next HTTP poll without a rebuild.
    """
    if not isinstance(stations, list):
        return stations
    chans = {c.get('id'): c for c in channels if c.get('id')}
    for station in stations:
        citem = chans.get(station.get('id'))
        if not citem: continue
        Globals._cleanGroups(citem)  # reflects Enable_Grouping on/off + favorite/type/genre
        if citem.get('group'):
            station['group'] = list(citem['group'])
    return stations


def _storeRender(cache: dict, sig: tuple, data: bytes, name: str) -> bool:
    """Cache rendered bytes under the shared 'render' MemoryBudget owner.

    The M3U and XMLTV render caches share RENDER_CACHE_MAX (a fraction of the
    global cache budget) — combined they can never exceed it. Old cached bytes
    are released before stashing new ones.
    """
    from cache import MemoryBudget
    budget = MemoryBudget.instance()
    budget.register('render', RENDER_CACHE_MAX)
    old = cache.get('data')
    if old is not None:
        budget.release('render', len(old))
    if not data or len(data) >= RENDER_CACHE_MAX or not budget.acquire('render', len(data)):
        if data and len(data) >= RENDER_CACHE_MAX:
            LOG("%s, render too large (%s bytes), not caching" % (name, len(data)), xbmc.LOGWARNING)
        return False
    cache['sig'], cache['data'] = sig, data
    return True


def renderFilteredM3U(channels: list, runActions) -> bytes:
    """Get filtered M3U content using M3U class render() + filter pipeline.

    Rendered output is cached keyed by source file mtimes — pvr.iptvsimple
    polls the M3U repeatedly during builds, and each render otherwise
    re-parses the full M3U + XMLTV + channels.json (3-pass parse of a 7MB+ file).
    """
    global _M3U_RENDER_CACHE
    sig = m3u_render_signature()
    if _M3U_RENDER_CACHE['sig'] == sig:
        return _M3U_RENDER_CACHE['data']
    from io import BytesIO
    m3u = M3U()
    # runActions dispatches by citem['id'] — iterate every configured channel to
    # let its M3U_FILTER rule act (each receives the list from the previous one).
    def _filter(stations):
        for citem in channels:
            stations = runActions(RULES_ACTION_M3U_FILTER, citem, stations)
        return stations
    buf = BytesIO()
    # Reflect Enable_Grouping (and channel group edits) in the served group-title
    # on the fly, before the per-channel M3U_FILTER rules run — so GroupHide sees
    # the grouped groups without waiting for a rebuild.
    stations = applyGrouping(m3u.getFilteredStations(), channels)
    m3u.render(buf, stations=_filter(stations))
    data = buf.getvalue()
    # never cache an implausibly large render — a half-written M3U read during a
    # build once produced a 776MB blob served on every poll. The shared render
    # budget (RENDER_CACHE_MAX) also refuses oversized or combined-over-budget
    # stashes.
    _storeRender(_M3U_RENDER_CACHE, sig, data, 'renderFilteredM3U')
    return data


def renderFilteredXMLTV(channels: list, runActions) -> bytes:
    """Get XMLTV content with temporary placeholder programmes injected.

    Channels whose EPG doesn't reach the Min_Days horizon — including no-guide
    channels — get an informative placeholder so pvr.iptvsimple shows a non-empty
    row. Data is served from the SQLite cache (renderWithPlaceholders), not disk.

    Rendered output is cached keyed on the XMLTV data version token.
    """
    global _XMLTV_RENDER_CACHE
    sig = xmltv_render_signature()
    if _XMLTV_RENDER_CACHE['sig'] == sig:
        return _XMLTV_RENDER_CACHE['data']
    from io import BytesIO
    xmltv_obj = XMLTVS()
    # runActions dispatches by citem['id'] — iterate every configured channel
    # so each channel's XMLTV_FILTER rule can act on the served set (chained).
    def _filter(stations):
        for citem in channels:
            stations = runActions(RULES_ACTION_XMLTV_FILTER, citem, stations)
        return stations
    buf = BytesIO()
    xmltv_obj.renderWithPlaceholders(buf, stations=_filter(xmltv_obj.m3u.getFilteredStations(programmes=xmltv_obj.getProgrammes())))
    data = buf.getvalue()
    # don't cache implausibly large / empty renders (shared render budget cap)
    _storeRender(_XMLTV_RENDER_CACHE, sig, data, 'renderFilteredXMLTV')
    return data


def getFilteredGenres() -> bytes:
    """Return rendered genres.xml bytes from the SQLite cache.

    Falls back to the on-disk export file (legacy) if the cache is empty and
    an export file exists.
    #todo: apply genre filtering to the served genres.xml mirroring the
    M3U/XMLTV filter rules (per-channel genre filter rules) — for now the
    served genres reflect the full library set.
    """
    try:
        data = Globals.settings.getCacheSetting(GENRES_CACHE_KEY)
        if data is not None:
            return data if isinstance(data, bytes) else bytes(data, DEFAULT_ENCODING)
    except Exception as e:
        LOG("getFilteredGenres, cache read failed: %s" % e, xbmc.LOGDEBUG)
    if FileAccess.exists(GENREFLEPATH):
        try:
            with FileAccess.stream(GENREFLEPATH) as fle:
                return fle.readBytes()
        except Exception as e:
            LOG("getFilteredGenres, file fallback failed: %s" % e, xbmc.LOGDEBUG)
    if FileAccess.exists(GENREFLE_DEFAULT):
        try:
            with FileAccess.stream(GENREFLE_DEFAULT) as fle:
                return fle.readBytes()
        except Exception as e:
            LOG("getFilteredGenres, default fallback failed: %s" % e, xbmc.LOGDEBUG)
    return b''


def _genre_tokens(key: str) -> list:
    return [t for t in re.split(r'[\s/&,;.]+', key) if t]


def _build_genre_index() -> dict:
    global _GENRE_INDEX
    if _GENRE_INDEX is not None:
        return _GENRE_INDEX
    index = {'exact': {}, 'tokens': {}, 'by_id': {}}
    if FileAccess.exists(GENREFLE_DEFAULT):
        try:
            with FileAccess.open(GENREFLE_DEFAULT, "r") as fle:
                dom = parse(fle)
            for line in dom.getElementsByTagName('genre'):
                try:
                    gid = line.attributes['genreId'].value
                    names = line.childNodes[0].data
                    index['by_id'].setdefault(gid, {'genre': names, 'name': names.split(' / ')[0], 'genreId': gid})
                    for syn in (s.strip() for s in names.split(' / ') if s.strip()):
                        skey = syn.lower()
                        index['exact'].setdefault(skey, gid)
                        for tok in _genre_tokens(skey):
                            if len(tok) >= 3:
                                index['tokens'][tok] = gid
                except Exception:
                    continue
        except Exception:
            pass
    _GENRE_INDEX = index
    return index


def _matchGenreId(category: str) -> Optional[str]:
    """Resolve a Kodi genre string to a DVB genreId (the EPG colour).

    Priority: curated alias > exact DVB synonym > DVB word token. Covers compound
    genres ('Sci-Fi & Fantasy'), Kodi-specific genres missing from the ETSI list
    ('anime', 'reality', 'mystery') and ambiguous words ('classical' -> music).
    """
    key = (category or '').strip().lower()
    if not key:
        return None
    index = _build_genre_index()
    if key in _GENRE_ALIASES: return _GENRE_ALIASES[key]
    if key in index['exact']: return index['exact'][key]
    for tok in _genre_tokens(key):
        if tok in _GENRE_ALIASES: return _GENRE_ALIASES[tok]
        if tok in index['tokens']: return index['tokens'][tok]
    return None


def _utcOffset() -> str:
    """Local UTC offset as an XMLTV '+HHMM'/'-HHMM' suffix (e.g. '-0400').

    pvr.iptvsimple interprets XMLTV start/stop as UTC unless an explicit offset
    is present. Our schedule stores LOCAL %Y%m%d%H%M%S, so without this suffix
    pvr.iptvsimple misreads the times and catchup seek drifts by the UTC offset,
    landing playback on a programme from hours earlier.
    """
    delta = datetime.datetime.now().astimezone().utcoffset() or datetime.timedelta(0)
    total = int(delta.total_seconds())
    sign = '-' if total < 0 else '+'
    total = abs(total)
    return '%s%02d%02d' % (sign, total // 3600, (total % 3600) // 60)
_PROG_DDL = (
    "CREATE TABLE IF NOT EXISTS programmes("
    "channel TEXT NOT NULL, start TEXT NOT NULL, stop TEXT NOT NULL, data BLOB, "
    "PRIMARY KEY (channel, start))",
    "CREATE INDEX IF NOT EXISTS idx_prog_stop ON programmes(stop)",
)


def _xmltv_cache_sig():
    """Return the current XMLTV cache version token, or None if never saved."""
    meta = Globals.settings.getCacheSetting(XMLTV_META_KEY) or {}
    return meta.get('version')


def clearXMLTVCache():
    """Clear the XMLTV cache entries and invalidate the module holder.

    Used by the utilities cleanup — data now lives in cache.db, so "cleaning" the
    guide means dropping the cache keys (and the in-memory holder), not deleting
    any physical export file.
    """
    with _XMLTV_HOLDER_LOCK:
        _XMLTV_HOLDER.update(sig=None, channels=[], programmes=[], recordings=[])
    for key in (XMLTV_CHANNELS_KEY, XMLTV_PROGRAMMES_KEY, XMLTV_RECORDINGS_KEY, XMLTV_META_KEY):
        Globals.settings.clrCacheSetting(key)

class XMLTVS(object):
    
    def __init__(self, file: str = XMLTVFLEPATH, writable: bool = False, m3u: Optional[M3U] = None):
        if m3u is None: m3u = M3U(writable=writable)
        self._lock      = RLock()
        self.m3u        = m3u
        self.writable   = writable
        self.XMLTVFile  = file
        self.XMLTVDATA  = {}
        self.XMLTVDATA  = self._load()
        
        
    def __enter__(self) -> 'XMLTVS':
        self._saved = False
        return self


    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]):
        try:
            if self.writable and not getattr(self, '_saved', False):
                self._save()
        except Exception:
            pass
            
            
    def __del__(self):
        try:
            if self.writable and not getattr(self, '_saved', False):
                self._save()
        except Exception: pass
            
            
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
        self.log('_load, cache=%s' % self.XMLTVFile)
        with _XMLTV_HOLDER_LOCK:
            sig = _xmltv_cache_sig()
            # Fresh if: (a) cache has a version token and the holder matches it, or
            # (b) no token yet but the holder already holds file-migrated data (so we
            # don't re-parse the 51MB export on every load before the first save).
            holder_fresh = ((sig is not None and sig == _XMLTV_HOLDER['sig'])
                            or (sig is None and (_XMLTV_HOLDER['channels'] or _XMLTV_HOLDER['programmes'])))
            if not holder_fresh:
                channels   = Globals.settings.getCacheSetting(XMLTV_CHANNELS_KEY)   or []
                programmes = Globals.settings.getCacheSetting(XMLTV_PROGRAMMES_KEY) or []
                recordings = Globals.settings.getCacheSetting(XMLTV_RECORDINGS_KEY) or []
                if not (channels or programmes or recordings):
                    # Legacy migration: first run after the file->cache switch or a
                    # cache clear — parse the on-disk export once; the next writable
                    # _save populates the cache so subsequent loads hit SQLite.
                    channels_raw, programmes_raw = self._load_file()
                    channels, recordings = self._clean(channels_raw, 'id')
                    programmes = self._clean(programmes_raw, 'channel')
                else:
                    channels, recordings = self._clean(channels, 'id')
                    programmes = self._clean(programmes, 'channel')
                _XMLTV_HOLDER.update(sig=sig, channels=channels,
                                     programmes=programmes, recordings=recordings)
        data = self.resetData()
        if self.writable:
            # writable (builder) instances work on copies so their mutations never
            # corrupt the shared holder that read-only servers are using.
            return {'data'       : data,
                    'channels'   : list(_XMLTV_HOLDER['channels']),
                    'recordings' : list(_XMLTV_HOLDER['recordings']),
                    'programmes' : list(_XMLTV_HOLDER['programmes'])}
        return {'data'       : data,
                'channels'   : _XMLTV_HOLDER['channels'],
                'recordings' : _XMLTV_HOLDER['recordings'],
                'programmes' : _XMLTV_HOLDER['programmes']}


    def _load_file(self) -> tuple:
        """Legacy XMLTV parse from the on-disk export (migration fallback)."""
        self.log('_load_file, file=%s' % self.XMLTVFile)
        fle = None
        try:
            fle = FileAccess.open(self.XMLTVFile, 'r')
            fle.seek(0)
            channels   = xmltv.read_channels(fle)   or []
            fle.seek(0)
            programmes = xmltv.read_programmes(fle) or []
        except Exception as e:
            self._error('_load', e)
            channels, programmes = [], []
        finally:
            if fle and hasattr(fle, 'close'):
                fle.close()
        return channels, programmes


    def _save(self, reset: bool=True) -> bool:
        with self._lock:
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
                # Guard against clobbering existing guide data with an empty dataset:
                # a failed/partial _load or an orphan-cleanup over a narrowed channel
                # set can leave 0 channels, which would wipe the XMLTV mid-build.
                # Skip the write when the cache already holds content.
                if len(self.XMLTVDATA['channels']) == 0 and len(self.XMLTVDATA['programmes']) == 0:
                    if Globals.settings.getCacheSetting(XMLTV_META_KEY):
                        self.log("_save, refusing to overwrite existing XMLTV with empty dataset", xbmc.LOGWARNING)
                        return False
                # Persist to the SQLite cache (transactional; avoids file-lock races
                # with HTTP serving / pvr.iptvsimple). Version token increments on
                # every save, invalidating the holder and HTTP render caches.
                Globals.settings.setCacheSetting(XMLTV_CHANNELS_KEY,   self.XMLTVDATA['channels'],   life=-1)
                Globals.settings.setCacheSetting(XMLTV_PROGRAMMES_KEY, self.XMLTVDATA['programmes'], life=-1)
                Globals.settings.setCacheSetting(XMLTV_RECORDINGS_KEY, self.XMLTVDATA['recordings'], life=-1)
                old_meta = Globals.settings.getCacheSetting(XMLTV_META_KEY) or {}
                meta = {'updated': time.time(), 'version': (old_meta.get('version', 0) or 0) + 1}
                Globals.settings.setCacheSetting(XMLTV_META_KEY, meta, life=-1)
                with _XMLTV_HOLDER_LOCK:
                    _XMLTV_HOLDER['sig'] = meta['version']
                    # Keep the holder's data in sync with what was just saved, not
                    # just the version token: otherwise the next load sees a matching
                    # sig, treats the holder as fresh, and reuses the PREVIOUS chunk's
                    # data — the xmltv.programmes blob then only ever holds the last
                    # chunk instead of the accumulated guide. Copies so a writable
                    # instance's mutations never alias the shared holder.
                    _XMLTV_HOLDER['channels']   = list(self.XMLTVDATA['channels'])
                    _XMLTV_HOLDER['programmes'] = list(self.XMLTVDATA['programmes'])
                    _XMLTV_HOLDER['recordings'] = list(self.XMLTVDATA['recordings'])
                # Backfill the indexed programmes table for rows written before the
                # schema existed; addProgram/delBroadcast/clrProgrammes keep it synced.
                self._backfill_programmes_table()
                if Globals.settings.getSettingBool('Enable_File_Export'):
                    self._save_export()

                self._saved = True
                # Update PVR status with current M3U/XMLTV data
                try:
                    status = Globals.settings.instances.updatePVRStatus(Globals.properties.getRemoteHost(), Globals.properties.getFriendlyName())
                    xmltv_channels = self.getChannels()
                    status['xmltv']['channel_ids'] = {c.get('id') for c in xmltv_channels if c.get('id')}
                    status['xmltv']['programmes'] = len(self.getProgrammes())
                    status['xmltv']['last_write'] = time.time()
                    Globals.settings.instances._resolvePVRStatus(status)
                    Globals.properties.notifyDataChanged('xmltv')
                except Exception as e: self.log("_save, status update failed: %s" % e, xbmc.LOGDEBUG)
                return self.buildGenres()


    def _save_export(self) -> bool:
        """Write the physical pseudotv.xml export (atomic temp+rename).

        Only runs when Enable_File_Export is on — the SQLite cache remains the
        source of truth. Keeps the legacy file on disk for local-file pvr.iptvsimple
        configs or third-party tooling.
        """
        try:
            data = self.XMLTVDATA.get('data', self.resetData())
            writer = xmltv.Writer(encoding            = DEFAULT_ENCODING,
                                  date                = data.get('date', ''),
                                  source_info_url     = self.cleanString(data.get('source-info-url', '')),
                                  source_info_name    = self.cleanString(data.get('source-info-name', '')),
                                  generator_info_url  = self.cleanString(data.get('generator-info-url', '')),
                                  generator_info_name = self.cleanString(data.get('generator-info-name', '')))
            for channel in (self.XMLTVDATA['recordings'] + self.XMLTVDATA['channels']):
                writer.addChannel(channel)
            for program in self.XMLTVDATA['programmes']:
                writer.addProgramme(self._offsetProgramme(program))
            tmp_file = '%s.tmp' % (self.XMLTVFile)
            with FileLock(self.XMLTVFile):
                with FileAccess.open(tmp_file, "w") as fle:
                    writer.write(fle, pretty_print=True)
                if FileAccess.rename(tmp_file, self.XMLTVFile):
                    self.log("_save_export, atomic write complete")
                else:
                    self.log("_save_export, atomic rename failed, retrying direct write", xbmc.LOGWARNING)
                    FileAccess.delete(tmp_file)
                    with FileAccess.open(self.XMLTVFile, "w") as fle:
                        writer.write(fle, pretty_print=True)
            return True
        except Exception as e:
            self.log("_save_export failed!\n%s" % e, xbmc.LOGERROR)
            try: FileAccess.delete(tmp_file)
            except Exception: pass
            return False


    def render(self, fle, channels=None, recordings=None, programmes=None):
        """Render XMLTV content to a file-like object without touching disk.

        Uses xmltv.Writer to write to any file-like object (e.g. BytesIO).
        Used by the HTTP server to serve filtered XMLTV content based on channels.json.
        """
        if channels is None:    channels = self.getChannels()
        if recordings is None:  recordings = self.getRecordings()
        if programmes is None:  programmes = self.getProgrammes()
        data = self.XMLTVDATA.get('data', self.resetData())
        writer = xmltv.Writer(encoding            = DEFAULT_ENCODING,
                              date                = data['date'],
                              source_info_url     = self.cleanString(data['source-info-url']),
                              source_info_name    = self.cleanString(data['source-info-name']),
                              generator_info_url  = self.cleanString(data['generator-info-url']),
                              generator_info_name = self.cleanString(data['generator-info-name']))
        for channel in (recordings + channels):
            writer.addChannel(channel)
        for program in programmes:
            writer.addProgramme(self._offsetProgramme(program))
        writer.write(fle, pretty_print=True)


    def _offsetProgramme(self, program: dict) -> dict:
        """Return a copy of a programme with the local UTC offset appended to its
        start/stop, so pvr.iptvsimple parses the LOCAL DTFORMAT times correctly
        (it assumes UTC otherwise, which shifts catchup seek by the UTC offset)."""
        p = dict(program)
        if p.get('start'): p['start'] = '%s %s' % (p['start'], _utcOffset())
        if p.get('stop'):  p['stop']  = '%s %s' % (p['stop'],  _utcOffset())
        return p


    def renderWithPlaceholders(self, fle, channels=None, programmes=None, stations=None, horizon: int = None):
        """Render XMLTV with temporary placeholder programmes injected.

        Every served channel gets a non-empty guide row: channels whose EPG does
        not reach `horizon` (default Min_Days) ahead of now — including channels
        with NO guide data at all — get a "No Guide Data - Check Back Later"
        placeholder spanning [last-stop-or-now, now+horizon). This replaces the
        old "hide empty-guide channels" approach: configured channels stay visible
        in Kodi with a labelled placeholder instead of a blank row.

        The placeholder is served only — it is never persisted and is stripped by
        _isPlaceholder in loadStopTimes/hasProgrammes.

        `stations` (optional) is the filtered M3U station set served to pvr.iptvsimple;
        when provided, the rendered XMLTV is restricted to exactly those channels
        (channel entries are rebuilt from the station dicts, so channels that had no
        guide and were dropped from the persisted XMLTV still get a row here).
        """
        if horizon is None: horizon = MIN_GUIDEDAYS * 86400
        if channels is None:   channels = self.getChannels()
        if programmes is None: programmes = self.getProgrammes()
        programmes = list(programmes)
        if stations is not None:
            served = {s.get('id') for s in stations if s.get('id')}
            channels = [{'id': s['id'],
                         'display-name': [(self.cleanString(s.get('name', '')), LANG)],
                         'icon': [{'src': s.get('logo', '')}]}
                        for s in stations if s.get('id')]
            programmes = [p for p in programmes if p.get('channel') in served]
        try:
            now_epoch = float(Globals._getGMTstamp())
            now_rounded_epoch = float(Globals._roundTimeDown(now_epoch, offset=60))
            now_str = Globals._epochTime(now_rounded_epoch, tz=False).strftime(DTFORMAT)
            min_end_epoch = now_epoch + horizon
            ph_min_epoch = now_rounded_epoch + MIN_EPG_DURATION
            # Channels whose real guide covers now need no placeholder. For the
            # rest (no data at all, or a future-start guide that leaves today
            # empty), inject a labelled placeholder from rounded-now filling the
            # gap up to the next real programme — at least MIN_EPG_DURATION.
            covers_now = set()
            first_starts = {}
            for p in programmes:
                ch = p.get('channel')
                if not ch:
                    continue
                start, stop = p.get('start'), p.get('stop')
                if start and start <= now_str < stop:
                    covers_now.add(ch)
                if start and (ch not in first_starts or start < first_starts[ch]):
                    first_starts[ch] = start
            for ch in channels:
                cid = ch.get('id')
                if not cid or cid in covers_now:
                    continue
                ph_stop_epoch = ph_min_epoch
                first = first_starts.get(cid)
                if first and first > now_str:
                    first_epoch = Globals._strpTime(first, DTFORMAT).timestamp()
                    ph_stop_epoch = max(first_epoch, ph_min_epoch)
                ph_stop_epoch = min(ph_stop_epoch, min_end_epoch)
                programmes.append(self._placeholderProgramme(cid, ch, start=now_rounded_epoch, stop=ph_stop_epoch))
        except Exception as e:
            self.log(f"renderWithPlaceholders, failed: {e}", xbmc.LOGDEBUG)
        self.render(fle, channels=channels, programmes=programmes)


    def _placeholderProgramme(self, ch_id: str, ch: dict, start: Optional[float] = None, stop: Optional[float] = None) -> dict:
        now  = float(Globals._getGMTstamp())
        if start is None: start = now
        if stop  is None: stop  = now + MIN_EPG_DURATION
        logo = ch.get('logo') or (ch.get('icon') or [{}])[0].get('src', '')
        # Short title for the EPG row; the informative message goes in the
        # description/plot so the user knows the guide is still building.
        title = LANGUAGE(32277)
        desc  = LANGUAGE(32282)
        return {'channel' : ch_id,
                'category': [('Undefined', LANG)],
                'title'   : [(title, LANG)],
                'desc'    : [(desc, LANG)],
                'start'   : Globals._epochTime(start, tz=False).strftime(DTFORMAT),
                'stop'    : Globals._epochTime(stop, tz=False).strftime(DTFORMAT),
                'icon'    : [{'src': logo}],
                'length'  : {'units': 'seconds', 'length': str(max(0, int(stop - start)))}}
    
    
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
        
        
    def _programme_db(self) -> Any:
        """SQLite cache handle for the indexed programmes table (Phase 2)."""
        global _PROG_TABLE_READY
        cache = Globals.settings.cache
        if not _PROG_TABLE_READY:
            for ddl in _PROG_DDL:
                cache.execute(ddl)
            _PROG_TABLE_READY = True
        return cache


    def _add_program_row(self, pitem: dict):
        try:
            if pitem.get('channel'):
                self._programme_db().execute(
                    "INSERT OR REPLACE INTO programmes(channel,start,stop,data) VALUES(?,?,?,?)",
                    (pitem.get('channel'), pitem.get('start'), pitem.get('stop'), FileAccess.dumpPICKLE(pitem)))
        except Exception as e:
            self.log(f"_add_program_row failed: {e}", xbmc.LOGDEBUG)


    def _del_channel_programmes(self, ch_id: str):
        try:
            if ch_id:
                self._programme_db().execute("DELETE FROM programmes WHERE channel=?", (ch_id,))
        except Exception as e:
            self.log(f"_del_channel_programmes failed: {e}", xbmc.LOGDEBUG)


    def _backfill_programmes_table(self):
        """Sync the indexed programmes table with the in-memory guide.

        Runs on every save: for each channel present in XMLTVDATA its table rows
        are rebuilt from the in-memory set, so the table (used by
        loadStopTimes/hasProgrammes for the build's coverage check) can never
        drift from the served blob (used by the HTTP guide). A stale table once
        reported guides that covered today while the served XMLTV did not — the
        channel was marked 'guide sufficient' yet showed no guide data.
        """
        try:
            db = self._programme_db()
            with self._lock:
                by_channel = {}
                for p in self.XMLTVDATA['programmes']:
                    ch = p.get('channel')
                    if ch:
                        by_channel.setdefault(ch, []).append(p)
                for ch_id, progs in by_channel.items():
                    db.execute("DELETE FROM programmes WHERE channel=?", (ch_id,))
                    if progs:
                        rows = [(ch_id, p.get('start'), p.get('stop'), FileAccess.dumpPICKLE(p)) for p in progs]
                        db.execute("INSERT OR REPLACE INTO programmes(channel,start,stop,data) VALUES(?,?,?,?)", rows)
                if by_channel:
                    self.log(f"_backfill_programmes_table, synced {sum(len(v) for v in by_channel.values())} rows across {len(by_channel)} channels", xbmc.LOGDEBUG)
        except Exception as e:
            self.log(f"_backfill_programmes_table failed: {e}", xbmc.LOGDEBUG)


    def _db_channel_bounds(self, channels: list, fallback: str) -> Optional[dict]:
        """Return {ch_id: {'start': min, 'stop': max}} from the indexed table, or None
        when the table is empty (caller falls back to the in-memory scan)."""
        try:
            cursor = self._programme_db().execute(
                "SELECT channel, MIN(start), MAX(stop) FROM programmes GROUP BY channel")
            rows = cursor.fetchall() if cursor else []
            if not rows:
                return None
            row_map = {r[0]: r for r in rows}
            bounds = {}
            for ch in channels:
                ch_id = ch.get('id')
                if not ch_id: continue
                row = row_map.get(ch_id)
                bounds[ch_id] = {'start': row[1] if row else fallback,
                                 'stop' : row[2] if row else fallback}
            return bounds
        except Exception as e:
            self.log(f"_db_channel_bounds failed: {e}", xbmc.LOGDEBUG)
            return None


    def _db_max_stops(self) -> Optional[dict]:
        """Return {ch_id: max_stop} from the indexed table, or None when empty."""
        try:
            cursor = self._programme_db().execute(
                "SELECT channel, MAX(stop) FROM programmes GROUP BY channel")
            rows = cursor.fetchall() if cursor else []
            if not rows:
                return None
            return {r[0]: r[1] for r in rows}
        except Exception as e:
            self.log(f"_db_max_stops failed: {e}", xbmc.LOGDEBUG)
            return None


    def loadStopTimes(self, channels: list = None, programmes: list = None, fallback: Optional[str] = None) -> Generator:
        if channels is None:   channels   = []
        if programmes is None: programmes = []
        if not channels:   channels   = self.getChannels()
        if not fallback:   fallback   = Globals._epochTime(Globals._roundTimeDown(Globals._getGMTstamp(), offset=60), tz=False).strftime(DTFORMAT)

        # Phase 2: prefer the indexed programmes table (no full-list scan).
        channel_bounds = self._db_channel_bounds(channels, fallback)
        if channel_bounds is None:
            channel_bounds = {channel['id']: {'start': fallback, 'stop': fallback} for channel in channels if 'id' in channel}
            for program in (programmes or self.getProgrammes()):
                if self._isPlaceholder(program): continue
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
        if not now: now = Globals._epochTime(Globals._roundTimeDown(Globals._getGMTstamp(),offset=60),tz=False).strftime(DTFORMAT)
        # Phase 2: prefer the indexed table; fall back to a single-pass scan.
        max_stops = self._db_max_stops()
        if max_stops is None:
            max_stops = {}
            for program in (programmes or self.getProgrammes()):
                if self._isPlaceholder(program): continue
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
        now     = (Globals._epochTime(float(Globals._getGMTstamp()),tz=False) - datetime.timedelta(days=MIN_GUIDEDAYS)) #allow some old programmes to avoid empty cells
        # Holiday rollover is handled at build time (builder.truncateProgrammes):
        # the per-programme holiday marker was never persisted, so a decode-based
        # check here was a silent no-op AND a 12k-_decodePlot cost per load.
        def __filterProgrammes(program: dict) -> Optional[dict]:
            try:
                stopTime = program.get('stop', now).rstrip()
                if Globals._strpTime(stopTime,DTFORMAT) < now: 
                    self.log('[%s] cleanProgrammes, __filterProgrammes removing expired programmes (%s)'%(program.get('channel'),stopTime))
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
            sorted_progs = sorted(programmes, key=itemgetter('start'))
            sorted_progs = sorted(sorted_progs, key=itemgetter('channel'))
            self.log('sortProgrammes, programmes = %s'%(len(sorted_progs)))
            return sorted_progs
        except Exception as e:
            self.log("sortProgrammes, failed! returning unsorted, %s"%(e), xbmc.LOGERROR)
            return programmes


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
        item['channel']       = citem.get('id', '')
        item['radio']         = citem.get('radio', False)
        item['start']         = fItem.get('start', '')
        item['stop']          = fItem.get('stop', '')
        item['title']         = fItem.get('label', '')
        item['desc']          = fItem.get('plot', '')
        item['length']        = fItem.get('duration', 0)
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

        item['rating']      = ratings.local(fItem.get('mpaa') or 'NA') or 'NA'
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

            fitem['start'] = Globals._getGMTstamp()
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
                # value stays the user's local label; system is detected
                # (VCHIP for TV-*, named system for international, MPAA fallback).
                pitem['rating'] = [{'system': ratings.system(rating), 'value': rating}]
                
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
            self._add_program_row(pitem)
            return True


    def addPlaceholder(self, ch_id: str, ch_name: str, ch_logo: str = '', msg: str = '') -> bool:
        """Write a single placeholder programme for channels with no EPG.
        Excluded from stop-time/coverage via _isPlaceholder in loadStopTimes/hasProgrammes."""
        if not msg: msg = LANGUAGE(32277)
        desc = LANGUAGE(32282)
        now  = Globals._getGMTstamp()
        stop = now + MIN_EPG_DURATION
        self.addChannel({'id': ch_id, 'name': ch_name, 'logo': ch_logo})
        self.addProgram(ch_id, {'title': msg, 'desc': desc, 'categories': ['Undefined'], 'thumb': ch_logo, 'start': now, 'stop': stop, 'length': MIN_EPG_DURATION, 'fitem': {}, 'new': False}, encodeDESC=False)
        self.log('[%s] addPlaceholder' % ch_id)
        return True


    def _isPlaceholder(self, program: dict) -> bool:
        """Check if a programme entry is a placeholder.

        Matches on placeholder title; no dedicated XMLTV flag exists for placeholders."""
        title = program.get('title', [('', '')])
        try: return title[0][0] in (LANGUAGE(32277), LANGUAGE(32279))
        except: return False


    def clrProgrammes(self, citem: dict) -> bool:
        with self._lock:
            self.XMLTVDATA['programmes'] = [program for program in self.XMLTVDATA['programmes'] if program.get('channel') != citem.get('id')]
            self._del_channel_programmes(citem.get('id'))
            self.log('clrProgrammes, removing channel %s programmes' % citem.get('id'))
            return True


    def truncateProgrammes(self, ch_id: str, boundary: str, mode: str = 'start') -> int:
        """Remove a channel's programmes that overlap a boundary (DTFORMAT).

        mode='start' removes programmes starting at/after `boundary` (used when a
        new seasonal holiday begins). mode='stop' removes programmes ending after
        `boundary` (used when a rebuild's future-start clamp pulls the schedule
        back to now — otherwise the new content overlaps the still-valid tail and
        the guide shows duplicate rows). Returns the number removed. The indexed
        programmes table is kept in sync.
        """
        with self._lock:
            if mode == 'stop':
                def _overlaps(program): return program.get('stop', '') > boundary
            else:
                def _overlaps(program): return program.get('start', '') >= boundary
            before = len(self.XMLTVDATA['programmes'])
            self.XMLTVDATA['programmes'] = [
                program for program in self.XMLTVDATA['programmes']
                if program.get('channel') != ch_id or not _overlaps(program)
            ]
            removed = before - len(self.XMLTVDATA['programmes'])
            if removed:
                self._del_channel_programmes(ch_id)
                for program in self.XMLTVDATA['programmes']:
                    if program.get('channel') == ch_id:
                        self._add_program_row(program)
            return removed


    def delBroadcast(self, citem: dict) -> bool:# remove single channel and all programmes from XMLTVDATA
        with self._lock:
            channels   = self.XMLTVDATA['channels']
            programmes = self.XMLTVDATA['programmes']
            self.XMLTVDATA['channels']   = list([channel for channel in channels if channel.get('id') != citem.get('id')])
            self.XMLTVDATA['programmes'] = list([program for program in programmes if program.get('channel') != citem.get('id')])
            self._del_channel_programmes(citem.get('id'))
            self.log('delBroadcast, removing channel %s; channels: before = %s, after = %s; programmes: before = %s, after = %s'%(citem.get('id'),len(channels),len(self.XMLTVDATA['channels']),len(programmes),len(self.XMLTVDATA['programmes'])))
            return True
        
        
    def delRecording(self, ritem: dict) -> bool:
        with self._lock:
            self.log('[%s] delRecording'%((ritem.get('id') or ritem.get('label'))))
            programmes = self.XMLTVDATA['programmes']
            idx, recording = self.findRecording(ritem)
            if idx is not None:
                self.XMLTVDATA['recordings'].pop(idx)
                if not ritem.get('id'): ritem['id'] = recording['id']
                self.XMLTVDATA['programmes'] = list([program for program in programmes if program.get('channel') != ritem.get('id')])
                self._del_channel_programmes(ritem.get('id'))
                return True
        
        
    def buildGenres(self, epggenres: Optional[dict] = None) -> bool:
        if epggenres is None: epggenres = {}
        global _DEFAULT_GENRES, _GENRE_SIG
        def __parseGenres(plines: list, out: Optional[dict] = None) -> dict:
            if out is None: out = {}
            for line in plines:
                try:
                    names = line.childNodes[0].data
                    items = names.split(' / ')
                    data  = {'genre':names,'name':names,'genreId':line.attributes['genreId'].value}
                    out.setdefault(names.lower(), data)
                    for item in items:
                        name = item.strip()
                        if name:
                            out.setdefault(name.lower(), dict(data, name=name))
                except Exception: continue
            return out

        def __getGenres(file: str = GENREFLE_DEFAULT) -> dict:
            # Default mapping is static — parse once, return a copy so the
            # caller's mutation (catcombo additions) never dirties the cache.
            global _DEFAULT_GENRES
            if file == GENREFLE_DEFAULT and _DEFAULT_GENRES is not None:
                return dict(_DEFAULT_GENRES)
            result = {}
            if FileAccess.exists(file):
                with FileAccess.open(file, "r") as fle:
                    dom = parse(fle)
                result = __parseGenres(dom.getElementsByTagName('genre'))
            if file == GENREFLE_DEFAULT:
                _DEFAULT_GENRES = result
            return result

        try:
            # Categories are stable across a build's chunk saves — if the set is
            # unchanged since the last render, the cached genres.xml is still
            # valid, so skip the recompute + DOM build + write entirely.
            seen_categories = set()
            for program in self.XMLTVDATA.get('programmes', []):
                cats = tuple(cat[0] for cat in program.get('category', []))
                if cats: seen_categories.add(cats)
            sig = tuple(sorted(seen_categories))
            if sig == _GENRE_SIG and Globals.settings.getCacheSetting(GENRES_CACHE_KEY):
                return True

            doc  = Document()
            root = doc.createElement('genres')
            doc.appendChild(root)
            name = doc.createElement('name')
            name.appendChild(doc.createTextNode('%s'%(ADDON_NAME)))
            root.appendChild(name)

            genres = __getGenres()
            # Match once per unique category list instead of once per programme —
            # thousands of entries share the same combo. First category that
            # resolves wins; _matchGenreId handles compound/aliased genres.
            for cats in seen_categories:
                catcombo = ' / '.join(cats)
                if genres.get(catcombo.lower()):
                    continue
                for category in cats:
                    gid = _matchGenreId(category)
                    if gid:
                        genres[catcombo.lower()] = dict(_build_genre_index()['by_id'].get(gid, {'genre': category, 'name': category, 'genreId': gid}))
                        break

            epggenres = __getGenres(GENREFLEPATH)
            epggenres.update(dict(sorted(sorted(list(genres.items()), key=lambda v:v[1]['name']), key=lambda v:v[1]['genreId'])))
            for key in list(set(epggenres)):
                gen = doc.createElement('genre')
                gen.setAttribute('genreId',epggenres[key].get('genreId'))
                gen.appendChild(doc.createTextNode(key.title()))
                root.appendChild(gen)
            try:
                # Genres persist in the SQLite cache; the physical file is an optional
                # export for local-file PVR configs / third-party tooling.
                xml_bytes = doc.toprettyxml(indent='  ', encoding=DEFAULT_ENCODING)
                # Store as str, not bytes: dumpPICKLE passes bytes through unpickled
                # (fileaccess.py), so a bytes value is stored raw and the cache
                # reader's loadPICKLE fails on it — genres would serve empty.
                Globals.settings.setCacheSetting(GENRES_CACHE_KEY, xml_bytes.decode(DEFAULT_ENCODING), life=-1)
                if Globals.settings.getSettingBool('Enable_File_Export'):
                    with FileLock(GENREFLEPATH):
                        with FileAccess.open(GENREFLEPATH, "w") as xmlData:
                            xmlData.write(xml_bytes)
                _GENRE_SIG = sig
                return True
            except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)
        except Exception as e: self.log("buildGenres failed! %s"%(e), xbmc.LOGERROR)