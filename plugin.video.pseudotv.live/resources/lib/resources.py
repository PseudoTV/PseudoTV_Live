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

from globals      import *
from functools    import reduce
from seasonal     import Seasonal
from intergration import OpenRouter

from collections import OrderedDict
from difflib     import SequenceMatcher
import datetime
import io
import os
import re

# Tunable: maximum number of entries to keep in the in-memory image cache.
IMAGE_CACHE_MAX = 500

LOCAL_FOLDERS   = [LOGO_LOC, IMAGE_LOC, TEMP_IMAGE_LOC]
MUSIC_RESOURCE  = ["resource.images.musicgenreicons.text"]
GENRE_RESOURCE  = ["resource.images.moviegenreicons.transparent"]
STUDIO_RESOURCE = ["resource.images.studios.white"]

# Precompile regexes used across calls
_YEAR_RE        = re.compile(r'\b(19|20)\d{2}\b')
_PAREN_RE       = re.compile(r'[\(\[\{].*?[\)\]\}]')
_NON_ALNUM_RE   = re.compile(r'[^0-9a-z\s]+', re.IGNORECASE)
_MULTI_WS_RE    = re.compile(r'\s+')
_TOKEN_SPLIT_RE = re.compile(r'\s+')


class Service(object):
    from jsonrpc import JSONRPC
    jsonRPC = JSONRPC()
    player  = PLAYER()
    monitor = MONITOR()
    def _shutdown(self, wait=1.0) -> bool:
        return (self.monitor.waitForAbort(wait) | PROPERTIES.isPendingShutdown())
    def _interrupt(self) -> bool:
        return (PROPERTIES.isPendingShutdown() | PROPERTIES.isPendingRestart() | PROPERTIES.isPendingInterrupt() | PROPERTIES.isInterruptActivity())
    def _suspend(self, wait=1.0) -> bool:
        pendingSuspend = PROPERTIES.isPendingSuspend()
        return pendingSuspend
    def _sleep(self, wait=1.0):
        # use a small cpu-cycle sleep loop but avoid heavy operations inside
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) | self._interrupt()): return True
            else: wait -= CPU_CYCLE
        return False


class Resources(object):

    def __init__(self, service=None):
        if service is None: service = Service()
        self.service     = service
        self.jsonRPC     = service.jsonRPC
        self.cache       = service.jsonRPC.cache
        self.baseURL     = service.jsonRPC.buildWebBase()
        self.remoteHost  = PROPERTIES.getRemoteHost()
        self.seasonal    = Seasonal()
        self.season      = self.seasonal.getHoliday()
        self._openRouter = OpenRouter(cache=self.cache)
        self.imageCache  = OrderedDict(SETTINGS.getCacheSetting('imageCache'  , json_data=True) or {})
        # trim if oversized
        while len(self.imageCache) > IMAGE_CACHE_MAX:
            self.imageCache.popitem(last=False)
        self.log(f'__init__, imageCache = {len(self.imageCache)}')


    def __del__(self):
        try:
            # persist as a plain dict (smaller on disk than OrderedDict)
            SETTINGS.setCacheSetting('imageCache'  , dict(self.imageCache)  , json_data=True)
            self.log(f'__del__, imageCache = {len(self.imageCache)}')
        except Exception:
            # avoid raising in destructor
            pass


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def selectLogo(self, citem: dict) -> list:
        logos = []
        logos.extend(self.getLocalLogo(citem.get('name'),select=True) or [])
        logos.extend(self.getLogoResources(citem, select=True) or [])
        logos.extend(self.getTVShowLogo(citem.get('name'), select=True) or [])
        self.log('selectLogo, chname = %s, logos = %s'%(citem.get('name'), len(logos)))
        return [f for f in logos if f]


    def queueLogo(self, citem):
        if hasattr(self.service,'logoQue'):
            try: self.service.logoQue.add(dumpJSON({'name': citem.get('name')}))
            except Exception as e: self.log(f'queueLogo failed: {e}', xbmc.LOGWARNING)


    def getCache(self, chname):
        # Use OrderedDict LRU behavior: move to end on access
        image = self.imageCache.get(chname)
        if image is not None:
            try: self.imageCache.move_to_end(chname)
            except Exception: pass
        else: self.queueLogo({'name':chname})
        self.log('getCache, name = %s, image = %s'%(chname,image))
        return image


    def setCache(self, chname, image=None):
        # avoid caching sentinel logo values
        if image in [LOGO,COLOR_LOGO]: return image
        try:
            if not image: return None
            self.imageCache[chname] = image
            try: self.imageCache.move_to_end(chname)
            except Exception: pass
            while len(self.imageCache) > IMAGE_CACHE_MAX:
                self.imageCache.popitem(last=False)
            self.log('setCache, name = %s, image = %s'%(chname,image))
        except Exception as e:
            self.log(f'setCache failed: {e}', xbmc.LOGWARNING)
        return image


    def getLogo(self, citem: dict, fallback=None, lookup=False, logo=None) -> str:
        self.log('[%s] getLogo, name = %s, lookup = %s'%(citem.get('id'),citem.get('name'),lookup))
        if not logo and citem.get('name') == LANGUAGE(32002):
            logo = self.season.get('logo')               # seasonal
        if not logo and not lookup:
            logo = self.getCache(citem.get('name'))      # cache
        if not logo and not lookup:
            self.queueLogo(citem)                        # queue lookup
        if not logo and not lookup and fallback:
            logo = fallback                              # fallback
        if not logo and lookup:
            # perform progressively heavier lookups only when lookup=True
            logo = self.getLocalLogo(citem.get('name'))  # local
            if not logo:
                logo = self.getLogoResources(citem)      # resources
            if not logo:
                logo = self.getTVShowLogo(citem.get('name')) # tvshow
            if not logo:
                # online/generative resources are expensive and optional; only try if configured
                try:
                    logo = self.generateOnline(citem.get('name'))
                except Exception:
                    logo = None
            if not logo:
                try:
                    logo = self.generateLocal(citem.get('name'))
                except Exception:
                    logo = None
        if not logo:
            logo = LOGO  # default
        return self.buildWebImage(citem.get('name'), cleanImage(logo))


    def buildWebImage(self, chname: str, image: str='') -> str:
        # Avoid repeated heavy set() operation and use efficient checks
        if image:
            lower_image = image.lower()
            if not (lower_image.startswith('image://') or lower_image.startswith('resource://') or
                    lower_image.startswith('http://') or lower_image.startswith('https://') or
                    'smb://' in lower_image or 'nfs://' in lower_image):
                # convert to web served image URL
                if image.startswith('image://'):
                    image = '%s/image/%s'%(self.baseURL,quoteString(image))
                elif not image.startswith('http://%s/logos/'%(self.remoteHost)):
                    image = 'http://%s/images/%s'%(self.remoteHost,quoteString(image))
                # Cache the resolved image path and return the hosted logo URL
                self.setCache(chname, image)
                return 'http://%s/logos/%s'%(self.remoteHost,quoteString(chname)) # host channel logos
        return self.setCache(chname, image)


    @cacheit(expiration=datetime.timedelta(minutes=5))
    def getLocalLogo(self, chname: str, select: bool=False) -> list:
        logos = []
        for path in LOCAL_FOLDERS:
            for ext in IMG_EXTS:
                fn = os.path.join(path, f'{chname}{ext}')
                if FileAccess.exists(fn):
                    self.log('getLocalLogo, found %s' % fn)
                    if select:
                        logos.append(fn)
                    else:
                        return fn
        if select:
            return logos
        return None


    def getLogoResources(self, citem: dict, select: bool=False,  copy: bool=False) -> dict and None:
        self.log('getLogoResources, chname = %s, type = %s, select = %s'%(citem.get('name'), citem.get('type'),select))

        def __getResources(type):
            resources = SETTINGS.getSetting('Resource_Logos').split('|').copy()
            if   type in ["TV Genres","Movie Genres"]:
                resources.extend(GENRE_RESOURCE)
            elif type in ["TV Networks","Movie Studios"]:
                resources.extend(STUDIO_RESOURCE)
            elif type in ["Music Genres","Radio"] or isRadio(citem):
                resources.extend(MUSIC_RESOURCE)
            else:
                resources.extend(GENRE_RESOURCE + STUDIO_RESOURCE)
            self.log('getResources, type = %s, resources = %s'%(type,resources))
            return resources

        def __fillResource(id):
            results  = {}
            try:
                addon_version = SETTINGS.getAddonDetails(id).get('version', ADDON_VERSION)
                response = self.jsonRPC.walkListDirectory(os.path.join('special://home/addons/%s/resources' % id),
                                                         exts=IMG_EXTS,
                                                         checksum=addon_version,
                                                         expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
                for path, images in list(response.items()):
                    for image in images:
                        results[os.path.splitext(image)[0]] = '%s/%s' % (path, image)
            except Exception as e:
                self.log('__fillResource failed for %s: %s' % (id, e), xbmc.LOGWARNING)
            return results

        resources = __getResources(citem.get('type','Custom'))
        checksum  = getMD5('|'.join([SETTINGS.getAddonDetails(id).get('version',ADDON_VERSION) for id in resources if SETTINGS.hasAddon(id)]))
        cacheName = 'getLogoResources.%s.%s' % (getMD5(citem.get('name')), select)
        cacheResponse = self.cache.get(cacheName, checksum=checksum)
        if not cacheResponse:
            logos = []
            for id in resources:
                if not SETTINGS.hasAddon(id):
                    continue
                results = __fillResource(id)
                self.log('getLogoResources, checking %s, results = %s'%(id,len(results)))
                for name, logo in list(results.items()):
                    if self.matchName(citem.get('name'), name):
                        self.log('getLogoResources, found %s'%(logo))
                        # append full resource path
                        logos.append(logo)
                        if not select:
                            if copy:
                                try:
                                    ext = os.path.splitext(logo)[1].lstrip('/')
                                    nlogo = os.path.join(TEMP_IMAGE_LOC, '%s.%s' % (citem.get('name'), ext))
                                    if FileAccess.copy(logo, nlogo):
                                        logo = nlogo
                                except Exception as e:
                                    self.log(f'copy resource failed: {e}', xbmc.LOGWARNING)
                            # cache first match and return immediately
                            return self.cache.set(cacheName, logo, checksum=checksum, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if logos:
                return self.cache.set(cacheName, logos, checksum=checksum, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
        return cacheResponse


    def getTVShowLogo(self, chname: str, select: bool=False):
        self.log('getTVShowLogo, chname = %s, select = %s'%(chname,select))
        cacheName     = 'getTVShowLogo.%s.%s'%(getMD5(chname),select)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            logos = []
            try:
                items = self.jsonRPC.getTVshows()
            except Exception as e:
                self.log('getTVShowLogo: getTVshows failed: %s' % e, xbmc.LOGWARNING)
                return None
            for item in items:
                if self.matchName(chname, item.get('title','')):
                    art = item.get('art', {})
                    for key in ['clearlogo','logo','logos','clearart','icon']:
                        logo = art.get(key,'')
                        if not logo:
                            continue
                        logo = logo.replace('image://DefaultFolder.png/','').rstrip('/')
                        if logo:
                            self.log('getTVShowLogo, found %s'%(logo))
                            logos.append(logo)
                            if not select:
                                return self.cache.set(cacheName, logo, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if logos:
                return self.cache.set(cacheName, logos, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
        return cacheResponse


    def matchName(self, chname: str, title: str, type: str='Custom', threshold=0.75) -> bool and None:
        def __normalize(s):
            if not s: return ''
            s = s.lower()
            # replace common separators with spaces
            s = s.replace('&', ' and ')
            # Remove parenthetical content: year, regions, extras
            s = _PAREN_RE.sub(' ', s)
            # Remove explicit years (standalone)
            s = _YEAR_RE.sub(' ', s)
            # Replace non-alphanumerics with space
            s = _NON_ALNUM_RE.sub(' ', s)
            # Collapse whitespace and trim
            s = _MULTI_WS_RE.sub(' ', s).strip()
            if s.startswith('the '): s = s[4:]
            return s

        a = __normalize(chname)
        b = __normalize(title)
        if not a and not b: return False
        if a == b:          return True
        # quick token checks to avoid heavy SequenceMatcher when unlikely to match
        a_tokens = set(_TOKEN_SPLIT_RE.split(a))
        b_tokens = set(_TOKEN_SPLIT_RE.split(b))
        if not a_tokens or not b_tokens: return False
        # if there's very low token intersection, skip expensive ratio
        inter = a_tokens.intersection(b_tokens)
        if len(inter) / max(1, min(len(a_tokens), len(b_tokens))) < 0.25:
            # fallback to startswith/contains checks which are cheap
            if a.startswith(b) or b.startswith(a) or (a in b) or (b in a):
                return True
            return False
        # fallback to SequenceMatcher only when token overlap suggests potential match
        try:
            ratio = SequenceMatcher(None, a, b).ratio()
            if ratio >= threshold:
                return True
        except Exception:
            pass
        return False


    def isMono(self, file: str, mono: bool=False) -> bool:
        if   file.startswith('resource://') and (bool(set([match in file.lower() for match in ['transparent','white','mono']]))):
            return True
        elif file.startswith('http'):
            # network check would require streaming; skip to avoid allocation unless explicitly requested
            pass
        elif SETTINGS.hasAddon('script.module.pil'):
            try:
                from PIL import Image, ImageStat
                # translate Kodi resource/image path to filesystem path
                file_path = unquoteString(file.replace('resource://','special://home/addons/').replace('image://','')).replace('\\','/')
                # open via FileAccess.stream to avoid loading multiple copies
                with FileAccess.stream(file_path, "rb") as f:
                    img = Image.open(io.BytesIO(f.read()))
                    stat = ImageStat.Stat(img)
                    # consider mono if all channel variances are very low
                    mono = all(v < 0.005 for v in stat.var)
                self.log('isMono, mono = %s, file = %s'%(mono,file))
            except Exception as e:
                self.log("isMono, failed! %s\nfile = %s"%(e,file), xbmc.LOGWARNING)
        return mono


    def generateLocal(self, text, background=os.path.join(MEDIA_LOC,'blank.png'),
                      font_path=FileAccess.translatePath(os.path.join('special://skin','fonts','NotoSans-Regular.ttf')),
                      font_size=60, text_color=(255,255,255,255)):
        """
        Generates a placeholder image with text on a background image.

        Args:
            text: The text to display on the placeholder.
            background: Path to the background image.
            font_path: Path to the font file (optional).
            font_size: Font size for the text (optional).
            text_color: Color of the text (optional).
        Returns:
            Path to generated image in TEMP_IMAGE_LOC or None on failure.
        """
        if not SETTINGS.hasAddon('script.module.pil'):
            return None

        try:
            from PIL import Image, ImageDraw, ImageFont
            # Read background bytes via FileAccess to avoid holding a file handle open
            fle = FileAccess.open(background, "rb")
            try:
                bg_bytes = fle.readBytes()
            finally:
                try:
                    fle.close()
                except Exception:
                    pass

            img = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype(font_path, font_size)
            # Use textbbox for accurate measurement including font offsets
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width  = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            # Center the text; adjust by bbox origin so fonts with offsets are handled.
            x = (img.width - text_width) // 2 - bbox[0]
            y = (img.height - text_height) // 2 - bbox[1]
            draw.text((x, y), text, font=font, fill=text_color)
            # Sanitize text for filename and limit length
            safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', text)[:200] or "image"
            image_filename = f"{safe_name}.png"
            image_path = os.path.join(FileAccess.translatePath(TEMP_IMAGE_LOC), image_filename)

            # Save to a BytesIO then write using FileAccess to avoid PIL writing to paths that may not be writable directly
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            out = FileAccess.open(image_path, "wb")
            try:
                out.writeBytes(buf.read())
            finally:
                try:
                    out.close()
                except Exception:
                    pass
            return image_path
        except Exception as e:
            self.log(f'generateLocal failed: {e}', xbmc.LOGWARNING)
            return None


    def generateOnline(self, chname, select=False, model=SETTINGS.getSetting('OPENROUTER_IMAGE_MODEL')):
        # deferred/disabled for memory and cost reasons by default; can be implemented on-demand via self.openRouter
        if not self.openRouter:
            return None
        try:
            count = 5 if select else 1
            logos = self.openRouter.getImage(chname, count, model)
            return logos
        except Exception as e:
            self.log(f'generateOnline failed: {e}', xbmc.LOGWARNING)
            return None