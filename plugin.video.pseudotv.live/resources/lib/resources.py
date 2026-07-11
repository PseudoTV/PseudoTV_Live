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
                if logo: self.setImageCache(citem.get('name'), logo)         # cache
            self.log('[%s] getLogo, name = %s, lookup = %s, logo = %s'%(citem.get('id'),citem.get('name'),lookup,logo))
            return self._buildWebImage(citem.get('name'), logo, fallback)
        except Exception as e: self.log(f'getLogo failed!\n{e}\n{citem}', xbmc.LOGERROR)
        return LOGO


    def _buildWebImage(self, name: Optional[str], image: Optional[str] = None, fallback: str = LOGO) -> str:
        image = Globals._cleanImage(image)
        if name and image is None: 
            return self._buildWebImage(None, OrderedDict(Globals.settings.getCacheSetting('imageCache', default={})).get(name), f'http://{Globals.properties.getEXTProperty(f"{ADDON_ID}.Remote_Host")}/logo/{Globals._quoteString(name)}')
        elif image.startswith(('image://')):
            image = f'{Globals.properties.getEXTProperty("%s.Local_Host"%(ADDON_ID))}/image/{Globals._quoteString(image)}'
        elif not image.startswith(('http','resource')):
            image = f'http://{Globals.properties.getEXTProperty("%s.Remote_Host"%(ADDON_ID))}/image/{Globals._quoteString(image)}'
        elif fallback:
            image = fallback
        return image
        
        
    @cacheit(expiration=datetime.timedelta(minutes=5))
    def getLocalLogo(self, chname: str, select: bool = False) -> list:
        logos = []
        for path in LOCAL_FOLDERS:
            for ext in IMG_EXTS:
                fn = os.path.join(path, chname + ext)
                if FileAccess.exists(fn):
                    self.log('getLocalLogo, found %s' % fn)
                    if select: logos.append(fn)
                    else: return fn
        if select: return logos
        return None


    def getLogoResources(self, citem: dict, select: bool = False) -> Optional[dict]:
        self.log('getLogoResources, chname = %s, type = %s, select = %s'%(citem.get('name'), citem.get('type'),select))

        def __getResources(type: str) -> list:
            return Globals.settings.getSetting('Resource_Logos').split('|')

        def __exists(path: str) -> bool:
            return FileAccess.exists(path)

        resources     = __getResources(citem.get('type','Custom'))
        checksum      = FileAccess._getMD5('|'.join([Globals.settings.getAddonDetails(id).get('version',ADDON_VERSION) for id in resources if Globals.settings.hasAddon(id)]))
        cacheName     = 'getLogoResources.%s.%s' % (FileAccess._getMD5(citem.get('name')), select)
        cacheResponse = self.cache.get(cacheName, checksum=checksum)
        if not cacheResponse:
            logos = []
            names = self.getNames(citem.get('name'), citem.get('type'))
            for name in names:
                for id in resources:
                    if Globals.settings.hasAddon(id):
                        logo = f'resource://{id}/{name}.png'
                        if __exists(logo):
                            self.log('getLogoResources, found %s'%(logo))
                            logos.append(logo)
                            if not select: 
                                return self.cache.set(cacheName, logo, checksum=checksum, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if logos: cacheResponse = self.cache.set(cacheName, logos, checksum=checksum, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
        return cacheResponse


    def getTVShowLogo(self, chname: str, select: bool = False) -> Optional[dict]:
        self.log('getTVShowLogo, chname = %s, select = %s'%(chname,select))
        cacheName     = 'getTVShowLogo.%s.%s'%(FileAccess._getMD5(chname),select)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            logos = []
            try: items = self.jsonRPC.getTVshows()
            except Exception as e:
                self.log(f'getTVShowLogo: getTVshows failed!\n{e}', xbmc.LOGWARNING)
                return None
            
            names = self.getNames(chname, "TV Shows")
            for name in names:
                for item in items:
                    if name.casefold() == item.get('title','').casefold():
                        art = item.get('art', {})
                        for key in ['clearlogo','logo','logos','clearart','icon']:
                            logo = art.get(key,'').replace('image://DefaultFolder.png/','').rstrip('/')
                            if not logo: continue
                            self.log('getTVShowLogo, found %s'%(logo))
                            logos.append(logo)
                            if not select: return self.cache.set(cacheName, logo, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if logos: cacheResponse = self.cache.set(cacheName, logos, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
        return cacheResponse


    def getNames(self, chname: str, type: str = "Custom") -> list:
        if not chname: return []
        variations = {chname} # original name
        variations.add(Globals._cleanChannelSuffix(chname, type)) # Remove Suffix
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
                font = ImageFont.truetype(font_path, font_size)
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
            try: return self.openRouter.getImage(citem, 3 if select else 1, Globals.settings.getSetting('Generative_Image_Model'), select)
            except Exception as e: self.log(f'generateOnline failed!: {e}', xbmc.LOGERROR)
                
                
    @cacheit(expiration=datetime.timedelta(minutes=15))
    def getTexture(self, url: str) -> Optional[str]:
        textures = self.jsonRPC.getTextures()
        image = next((texture for texture in textures if texture.get('cachedurl','').lower() == url.lower()),None)
        self.log('getTexture, url = %s\nimage = %s'%(url,image))
        if not image is None: return f'special://userdata/Thumbnails/{image}'
        

    def setTexture(self, url: str) -> str:
        image = f'{Globals.properties.getEXTProperty("%s.Local_Host"%(ADDON_ID))}/image/image://%s{Globals.double_urlencode(image)}'
        self.log('setTexture, url = %s\nimage = %s'%(url,image))
        self.jsonRPC.requestURL(image)
        return image
        
        
        