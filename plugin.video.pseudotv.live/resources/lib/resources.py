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

from typing import Any, Optional

from variables    import *
from _services    import _Service
from seasonal     import Seasonal 
from intergration import OpenRouter
from cache        import cacheit

# Tunable: maximum number of entries to keep in the in-memory image cache.
IMAGE_CACHE_MAX = CHANNEL_LIMIT
LOCAL_FOLDERS   = [LOGO_LOC, IMAGE_LOC, TEMP_LOC]

# Precompile regexes used across calls
_YEAR_RE      = re.compile(r'\b\d{4}\b')
_PAREN_RE     = re.compile(r'\([^)]*\)')
_NON_ALNUM_RE = re.compile(r'[^a-zA-Z0-9\s&]')
_MULTI_WS_RE  = re.compile(r'\s+')


def _xbtFrameSize(xbt: bytes, name: str) -> Optional[tuple]:
    """Width/height of the named frame in a Textures.xbt archive (XBTF header)."""
    if xbt[:4] != b'XBTF':
        return None
    nof = struct.unpack('<I', xbt[5:9])[0]
    pos = 9
    name = name.lower()
    for _ in range(nof):
        path = xbt[pos:pos + 256].split(b'\x00', 1)[0].decode('utf-8', 'replace').lower()
        loop, nf = struct.unpack('<II', xbt[pos + 256:pos + 264]); pos += 264
        for _ in range(nf):
            w, h, fmt, psz, usz, dur, off = struct.unpack('<IIIQQIQ', xbt[pos:pos + 40]); pos += 40
            if path == name:
                return (w, h)
    return None


def _bgraToPNG(data: bytes, width: int, height: int) -> bytes:
    """Encode a raw BGRA frame (XB_FMT_A8R8G8B8, as returned by the xbt VFS)
    as a PNG. Stdlib-only; PIL not required."""
    stride = width * 4
    raw = bytearray()
    for y in range(height):
        row = bytearray(data[y * stride:(y + 1) * stride])
        for x in range(0, stride, 4):
            row[x], row[x + 2] = row[x + 2], row[x]  # BGRA -> RGBA
        raw.append(0)
        raw += row

    def _chunk(tag: bytes, payload: bytes) -> bytes:
        return (struct.pack('>I', len(payload)) + tag + payload
                + struct.pack('>I', zlib.crc32(tag + payload) & 0xffffffff))

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', ihdr)
            + _chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + _chunk(b'IEND', b''))

class Resources(object):


    def __init__(self, service: Optional[_Service] = None):
        if service is None: service = _Service()
        self.remoteHost  = Globals.properties.getRemoteHost()
        self.processID   = Globals.properties.getProcessID()
        
        self.service     = service
        self.monitor     = service.monitor
        self.jsonRPC     = service.jsonRPC
        self.cache       = service.cache
        
        self.imageCache = getattr(service, 'imageCache', None)
        if self.imageCache is not None:
            self.pruneimageCache()
        else:
            self.imageCache = OrderedDict(Globals.settings.getCacheSetting('imageCache',default={}))
        self._logo_cache = {}
        self._tvshows_by_title = None  # lazily built title->show index (see getTVShowLogo)
        self.seasonal    = Seasonal(service)
        self.holiday     = self.seasonal.getHoliday()
        self.openRouter  = OpenRouter(service)
        
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def selectLogo(self, citem: dict) -> list:
        logos = []
        logos.extend(self.getLocalLogo(citem.get('name'),select=True) or [])
        logos.extend(self.getLogoResources(citem, select=True) or [])
        logos.extend(self.getTVShowLogo(citem.get('name'), select=True) or [])
        logos.extend(self.generateOnline(citem,True) or [])
        logos.extend(self.generateLocal(citem.get('name')) or [])
        logos = [f for f in logos if f]
        self.log('selectLogo, chname = %s, logos = %s'%(citem.get('name'), len(logos)))
        return logos


    def queueLogo(self, chname: str) -> str:
        if hasattr(self.service,'logoQue'):
            try: self.service.logoQue.add(chname)
            except Exception as e: self.log(f'queueLogo failed!\n{e}', xbmc.LOGWARNING)
        return 'http://%s/logos/%s?%s'%(self.remoteHost,Globals._quoteString(chname),self.processID) # host channel logos


    def pruneimageCache(self):
        while not self.monitor.abortRequested() and len(self.imageCache) > IMAGE_CACHE_MAX:
            self.imageCache.popitem(last=False)
            self.log(f'pruneimageCache = {len(self.imageCache)}')


    def getImageCache(self, chname: str, fallback: str = LOGO) -> str:
        # Use OrderedDict LRU behavior: move to end on access
        try:
            image = self.imageCache.get(chname)
            self.log('getImageCache, name = %s, image = %s'%(chname,image))
            # Ignore stale entries pointing at non-existent resource/image paths so
            # /logos/{name} serves the default until the queue re-resolves a real
            # icon (old caches hold phantom resource:// URLs that don't exist).
            if image is not None and image.startswith('resource://'):
                try:
                    real = FileAccess.translatePath(image)
                    if not FileAccess.exists(real) or real.endswith(('/', '\\')):
                        self.log('getImageCache, dropping stale logo: %s' % image)
                        self.imageCache.pop(chname, None)
                        image = None
                except Exception:
                    pass
            # Local generated logos (special:// or absolute paths) can go missing
            # too — e.g. an interrupted AI-image save or a cache cleanup that
            # cleared LOGO_LOC. Treat a missing local file the same as a phantom
            # resource://: drop the stale entry and fall back to the default so
            # /logos/{name} never 404s on a vanished file.
            elif image is not None and not image.startswith(('http://', 'https://')):
                try:
                    if not FileAccess.exists(image) or image.endswith(('/', '\\')):
                        self.log('getImageCache, dropping stale local logo: %s' % image)
                        self.imageCache.pop(chname, None)
                        image = None
                except Exception:
                    pass
            if image is not None:
                try: self.imageCache.move_to_end(chname)
                except Exception as e: self.log('getImageCache move_to_end failed: %s' % e, xbmc.LOGDEBUG)
            else: 
                image = fallback
                self.queueLogo(chname)
            return image
        except Exception as e: self.log('getImageCache failed: %s' % e, xbmc.LOGWARNING)


    def setImageCache(self, chname: str, image: Optional[str] = None) -> Optional[str]:
        if image:
            try:
                self.imageCache[chname] = image
                try: self.imageCache.move_to_end(chname)
                except Exception as e: self.log('setImageCache move_to_end failed: %s' % e, xbmc.LOGDEBUG)
                self.pruneimageCache()
                self.log('setImageCache, name = %s, image = %s'%(chname,image))
            except Exception as e: self.log(f'setImageCache failed!\n{e}', xbmc.LOGWARNING)
        return image


    def getLogo(self, citem: dict, fallback: str = LOGO, lookup: bool = False) -> str:
        try:
            logo = None
            if not logo and citem.get('name') == LANGUAGE(32002): logo = self.holiday.get('logo') # seasonal
            if not logo and not lookup:                           logo = self.getImageCache(citem.get('name'),fallback) # cache
            if not logo and lookup: # perform progressively heavier lookups only when lookup=True
                logo = self.getLocalLogo(citem.get('name'))                  # local
                if not logo: logo = self.getLogoResources(citem)             # resources
                if not logo: logo = self.getTVShowLogo(citem.get('name'))    # tvshow
                if not logo: logo = self.generateOnline(citem)               # generative (online)
                if not logo: logo = self.generateLocal(citem.get('name'))    # generative (local)
                if logo: self.setImageCache(citem.get('name'), Globals._toWebImage(logo))  # cache (browser-loadable URL)
            self.log('[%s] getLogo, name = %s, lookup = %s, logo = %s'%(citem.get('id'),citem.get('name'),lookup,logo))
            return self._buildWebImage(citem.get('name'), logo, fallback)
        except Exception as e: self.log(f'getLogo failed!\n{e}\n{citem}', xbmc.LOGERROR)
        return LOGO


    def _readImage(self, path: str) -> Optional[bytes]:
        """Read raw bytes for a Kodi VFS path (resource:// xbt packs decompress natively)."""
        try:
            with FileAccess.stream(path, 'rb') as fle:
                return fle.readBytes()
        except Exception as e:
            self.log('readImage failed: %s' % e, xbmc.LOGDEBUG)
        return None


    def _xbtToPNG(self, img: str, data: bytes) -> Optional[bytes]:
        """Re-encode a raw xbt frame (BGRA pixels) as PNG, cached in LOGO_LOC.
        Returns None if the path isn't an xbt-backed resource:// logo."""
        try:
            if not img.startswith('resource://'): return None
            cache = os.path.join(FileAccess.translatePath(LOGO_LOC),
                                 'xbt_%s.png' % FileAccess._getMD5(img))
            if FileAccess.exists(cache):
                with FileAccess.stream(cache, 'rb') as fle:
                    return fle.readBytes()
            addon_id, rest = img[len('resource://'):].split('/', 1)
            name = rest.rsplit('/', 1)[-1]
            # resource:// can't stat the .xbt itself (CResource only allows images),
            # so resolve the real addon folder and read Textures.xbt from there.
            addon = (Globals.settings.getAddonDetails(addon_id).get('path', '')
                     if Globals.settings.hasAddon(addon_id) else '')
            size = None
            for rel in ('resources/Textures.xbt', 'Textures.xbt'):
                xbt_path = os.path.join(addon, rel.replace('/', os.sep))
                if FileAccess.exists(xbt_path):
                    with FileAccess.stream(xbt_path, 'rb') as fle:
                        size = _xbtFrameSize(fle.readBytes(), name)
                    if size: break
            if not size:
                return None
            width, height = size
            if width * height * 4 != len(data): return None
            png = _bgraToPNG(data, width, height)
            with FileAccess.open(cache, 'w') as fle:
                fle.write(png)
            return png
        except Exception as e:
            self.log('xbtToPNG failed: %s' % e, xbmc.LOGDEBUG)
        return None


    def _staticLogo(self, name: Optional[str]) -> str:
        """The stable, self-hosted icon URL for a named item. Every consumer
        (channel/library/m3u/xmltv) stores this static URL; the /logos/{name}
        endpoint serves whatever the in-memory imageCache holds, so the icon
        updates dynamically once the logo queue resolves it — no config rewrites."""
        remote = Globals.properties.getEXTProperty('%s.Remote_Host'%(ADDON_ID))
        return f'http://{remote}/logos/{Globals._quoteString(name)}'


    def _buildWebImage(self, name: Optional[str], image: Optional[str] = None, fallback: str = LOGO) -> str:
        # Every named item resolves through the self-hosted /logos/{name} cache
        # endpoint, which serves whatever the in-memory imageCache holds (filling
        # via queueLogo when missing). The URL never changes — only the cache does,
        # so channels/library/m3u/xmltv all get dynamic logos without rewriting.
        if name:
            return self._staticLogo(name)
        # Unnamed fallback: serve the LOGO var through the image endpoint.
        return f'http://{Globals.properties.getEXTProperty("%s.Remote_Host"%(ADDON_ID))}/image/{Globals._quoteString(fallback or LOGO)}'
        
        
    def getLocalLogo(self, chname: str, select: bool = False) -> list:
        key = (str(chname) if chname is not None else '', select)
        cached = self._logo_cache.get(key)
        if cached is not None: return cached
        logos = []
        chname = key[0]
        for path in LOCAL_FOLDERS:
            for ext in IMG_EXTS:
                fn = os.path.join(path, chname + ext)
                if FileAccess.exists(fn):
                    self.log('getLocalLogo, found %s' % fn)
                    if select: logos.append(fn)
                    else:
                        self._logo_cache[key] = fn
                        return fn
        result = logos if select else None
        self._logo_cache[key] = result
        return result


    def getLogoResources(self, citem: dict, select: bool = False) -> Optional[dict]:
        citem['name'] = str(citem.get('name', '')) if citem.get('name') is not None else ''
        self.log('getLogoResources, chname = %s, type = %s, select = %s'%(citem.get('name'), citem.get('type'),select))

        def __getResources(type: str) -> list:
            return Globals.settings.getSetting('Resource_Logos').split('|')

        def __exists(path: str) -> bool:
            # Accept any resource:// path Kodi can resolve — including .xbt texture
            # packs, which render correctly inside Kodi (PVR/skin). We do NOT skip
            # xbt here; failing the lookup would strip logos from Kodi, where they
            # work. The web-browser rendering of xbt is handled at serve time.
            try: return bool(FileAccess.exists(path))
            except Exception: return False

        resources     = __getResources(citem.get('type','Custom'))
        checksum      = FileAccess._getMD5('|'.join([Globals.settings.getAddonDetails(id).get('version',ADDON_VERSION) for id in resources if Globals.settings.hasAddon(id)]))
        # v3: strict loose-file validation. Only resource:// logos backed by a real
        # file on disk (root, media/, or resources/) are accepted — .xbt texture
        # packs return raw pixels that browsers/PVR can't render, so they're
        # skipped and the lookup falls through to the next source.
        cacheName     = 'getLogoResources.v3.%s.%s' % (FileAccess._getMD5(citem.get('name')), select)
        cacheResponse = self.cache.get(cacheName, checksum=checksum)
        if not cacheResponse:
            logos = []
            names = self.getNames(citem.get('name'), citem.get('type'))
            for name in names:
                for id in resources:
                    if Globals.settings.hasAddon(id):
                        for folder in ('resources/', 'media/', ''):
                            # packs mix .png and .jpg textures (e.g. genre icons
                            # are .jpg, studios are .png) — try every extension.
                            for ext in IMG_EXTS:
                                logo = f'resource://{id}/{folder}{name}{ext}'
                                if __exists(logo):
                                    self.log('getLogoResources, found %s'%(logo))
                                    logos.append(logo)
                                    if not select:
                                        return self.cache.set(cacheName, logo, checksum=checksum, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if logos: cacheResponse = self.cache.set(cacheName, logos, checksum=checksum, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
        return cacheResponse


    def getTVShowLogo(self, chname: str, select: bool = False) -> Optional[dict]:
        chname = str(chname) if chname is not None else ''
        self.log('getTVShowLogo, chname = %s, select = %s'%(chname,select))
        cacheName     = 'getTVShowLogo.%s.%s'%(FileAccess._getMD5(chname),select)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            logos = []
            items = self._getTVShowsReuse()
            if items is None:
                self.log('getTVShowLogo: getTVshows failed!', xbmc.LOGWARNING)
                return None

            names = self.getNames(chname, "TV Shows")
            for name in names:
                item = self._tvshows_by_title.get(name.casefold())
                if item:
                    art = item.get('art', {})
                    for key in ['clearlogo','logo','logos','clearart','icon']:
                        logo = art.get(key,'').replace('image://DefaultFolder.png/','').rstrip('/')
                        if not logo: continue
                        self.log('getTVShowLogo, found %s'%(logo))
                        logos.append(logo)
                        if not select: return self.cache.set(cacheName, logo, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if logos: cacheResponse = self.cache.set(cacheName, logos, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
        return cacheResponse


    def _getTVShowsReuse(self) -> Optional[list]:
        """Fetch the full TV-show list once per Resources instance and index it by
        title. getTVShowLogo is called per-channel during a build — re-fetching the
        entire library (1237 shows x ~50 props) for every channel blows up memory.
        Persists the index to SQLite so it survives service restarts.
        """
        if self._tvshows_by_title is None:
            try:
                # Try SQLite cache first — avoids JSON-RPC on restart
                try:
                    cacheName = 'tvshows.library.index'
                    cached = self.cache.get(cacheName, checksum=ADDON_VERSION)
                    if cached is not None:
                        self._tvshows_by_title = cached
                        self.log('getTVShowLogo: loaded %d shows from cache' % len(cached), xbmc.LOGDEBUG)
                        return self._tvshows_by_title
                except Exception:
                    pass

                items = self.jsonRPC.getTVshows()
                index = {str(item.get('title','')).casefold(): item for item in (items or []) if item.get('title')}
                try:
                    from cache import MemoryBudget
                    budget = MemoryBudget.instance()
                    budget.register('tvshows', TVSHOWS_MEM_MAX)
                    size = sys.getsizeof(index)
                    if size <= TVSHOWS_MEM_MAX and budget.acquire('tvshows', size):
                        self._tvshows_by_title = index
                    else:
                        self.log('getTVShowLogo: library index (%d bytes) over TVSHOWS_MEM_MAX, logo lookups degraded' % size, xbmc.LOGWARNING)
                        self._tvshows_by_title = {}
                except Exception:
                    self._tvshows_by_title = index

                # Persist to SQLite for next restart
                try:
                    if self._tvshows_by_title:
                        self.cache.set(cacheName, self._tvshows_by_title, checksum=ADDON_VERSION,
                                       expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
                except Exception:
                    pass
            except Exception as e:
                self.log('getTVShowLogo: getTVshows failed!\n%s' % e, xbmc.LOGWARNING)
                self._tvshows_by_title = {}
        return self._tvshows_by_title or None


    def getNames(self, chname: str, type: str = "Custom") -> list:
        if not chname: return []
        variations = {chname} # original name
        variations.add(Globals._cleanChannelSuffix(chname, type)) # Remove Suffix
        if chname is not None: chname = str(chname)
        if isinstance(chname,str): 
            variations.add(_NON_ALNUM_RE.sub(' ', chname)) # Remove Non-Alphanumeric (except spaces and &)
            if '&' in chname: variations.add(chname.replace('&', ' and '))  # '&' to 'and' replacement
            elif ' and ' in chname: variations.add(chname.replace(' and ', '&')) # 'and' to '&' replacement
            if '(' in chname and ')' in chname: variations.add(_PAREN_RE.sub(' ', chname))# Remove Parentheses contents
            if _YEAR_RE.search(chname): variations.add(_YEAR_RE.sub(' ', chname)) # Remove Years
            if chname.lower().startswith('the '): variations.add(chname[4:])# Handle 'the ' prefix removal
        final_results = set() # Final cleanup: apply the 'multi-whitespace' rule to all generated variants
        for v in variations:
            cleaned = _MULTI_WS_RE.sub(' ', v).strip()
            if cleaned: final_results.add(cleaned)
        return sorted(list(final_results))
            
        
    def isMono(self, file: str, mono: bool = False) -> bool:
        if   file.startswith('resource://') and (bool(set([match in file.lower() for match in ['transparent','white','mono']]))):
            return True
        elif file.startswith('http'):
            # network check would require streaming; skip to avoid allocation unless explicitly requested
            pass
        elif Globals.settings.hasAddon('script.module.pil'):
            try:
                from PIL import Image, ImageStat
                # translate Kodi resource/image path to filesystem path
                file_path = Globals._unquoteString(file.replace('resource://','special://home/addons/').replace('image://','')).replace('\\','/')
                # open via FileAccess.stream to avoid loading multiple copies
                with FileAccess.stream(file_path, "rb") as f:
                    img = Image.open(BytesIO(f.read()))
                    stat = ImageStat.Stat(img)
                    # consider mono if all channel variances are very low
                    mono = all(v < 0.005 for v in stat.var)
                self.log('isMono, mono = %s, file = %s'%(mono,file))
            except Exception as e:
                self.log("isMono, failed! %s\nfile = %s"%(e,file), xbmc.LOGWARNING)
        return mono


    def generateLocal(self, text: str, background: str = os.path.join(MEDIA_LOC,'blank.png'),
                      font_path: str = FileAccess.translatePath(os.path.join('special://skin/fonts','arial.ttf')),
                      font_size: int = 120, text_color: tuple = (255,255,255,255)) -> Optional[str]:
        """
        Generates a placeholder image with text on a background image.

        Args:
            text: The text to display on the placeholder.
            background: Path to the background image.
            font_path: Path to the font file (optional).
            font_size: Font size for the text (optional).
            text_color: Color of the text (optional).
        Returns:
            Path to generated image in TEMP_LOC or None on failure.
        """
        if not text is None and Globals.settings.hasAddon('script.module.pil'):
            try:
                from PIL import Image, ImageDraw, ImageFont
                try: 
                    fle = FileAccess.open(background, "rb")
                    bg_bytes = fle.readBytes()
                except Exception as e: self.log(f'generateLocal failed!\n{e}', xbmc.LOGERROR)
                finally:
                    if hasattr(fle,'close'): fle.close()
                        
                img  = Image.open(BytesIO(bg_bytes)).convert("RGBA")
                draw = ImageDraw.Draw(img)
                # Resolve the font through FileAccess (special:// skin fonts may not
                # exist on Android). Fall back to PIL's bundled default font so logo
                # generation never throws "cannot open resource".
                font = None
                try:
                    real_font = FileAccess.translatePath(font_path) if font_path else ''
                    if FileAccess.exists(real_font):
                        font = ImageFont.truetype(real_font, font_size)
                except Exception:
                    font = None
                if font is None:
                    font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width  = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                # Center the text; adjust by bbox origin so fonts with offsets are handled.
                x = (img.width - text_width) // 2 - bbox[0]
                y = (img.height - text_height) // 2 - bbox[1]
                draw.text((x, y), text, font=font, fill=text_color)
                
                # Save to a BytesIO then write using FileAccess to avoid PIL writing to paths that may not be writable directly
                filepath = os.path.join(TEMP_LOC, f"{text}.png")
                buf = BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                try: 
                    out = FileAccess.open(filepath, "wb")
                    out.write(buf.read())
                except Exception as e: self.log(f'generateLocal failed!\n{e}', xbmc.LOGERROR)
                finally:
                    if hasattr(out,'close'): out.close()
                if FileAccess.exists(filepath): return filepath
            except Exception as e: self.log(f'generateLocal failed!\n{e}', xbmc.LOGERROR)


    def generateOnline(self, citem: dict, select: bool = False) -> Optional[str]:
        if self.openRouter:
            try:
                count = 3 if select else 1
                result = self.openRouter.getImage(citem, count, Globals.settings.getSetting('Generative_Image_Model'))
                # getImage returns a path (count==1) or list (count>1); keep the
                # return type stable for getLogo (str) and selectLogo (list).
                if isinstance(result, list):
                    return result[0] if result and not select else result
                return result
            except Exception as e: self.log(f'generateOnline failed!: {e}', xbmc.LOGERROR)
                
                
    def getTexture(self, url: str) -> Optional[str]:
        """Resolve a Kodi image URL (resource://, image://, smb://, http) to its
        cached texture file (special://userdata/Thumbnails/...) if Kodi has
        decoded it. Returns None when not cached yet."""
        textures = self.jsonRPC.getTextures()
        image = next((t for t in textures if t.get('url','').lower() == url.lower()), None)
        self.log('getTexture, url = %s\nimage = %s'%(url,image))
        if image is not None and image.get('cachedurl'):
            return f'special://userdata/Thumbnails/{image["cachedurl"]}'
        return None


    def setTexture(self, url: str) -> str:
        """Force Kodi to decode + cache a texture by rendering it in a hidden
        WindowXMLDialog image control (this triggers CTextureCache::CacheImage),
        then return its cached thumbnail path. Falls back to the source URL when
        caching isn't ready (caller can retry via getTexture)."""
        try:
            import xbmcgui as _xbmcgui
            import threading as _threading
            class _CacheWindow(_xbmcgui.WindowXMLDialog):
                def onInit(self):
                    try: self.getControl(5000).setImage(url)
                    except Exception as e:
                        self.log(f'CacheWindow setImage failed: {e}', xbmc.LOGDEBUG)
                    # brief visible render lets CTextureCache decode the image
                    _threading.Timer(2.0, self.close).start()
                def onAction(self, act):
                    pass
            win = _CacheWindow('plugin.video.pseudotv.live.texturecache.xml',
                               ADDON_PATH, 'default')
            win.doModal()
            for _ in range(20):
                cached = self.getTexture(url)
                if cached: return cached
                if self.monitor.abortRequested(): break
                self.monitor.waitForAbort(0.5)
            return url
        except Exception as e:
            self.log(f'setTexture failed: {e}', xbmc.LOGDEBUG)
            return url
        
        
        