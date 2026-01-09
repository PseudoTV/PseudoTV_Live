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
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) | self._interrupt()): return True
            else: wait -= CPU_CYCLE
        return False
        
        
class Resources(object):
    seasonal = Seasonal()
    
    def __init__(self, service=None):
        if service is None: service = Service()
        self.service    = service
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.jsonRPC.cache
        self.baseURL    = service.jsonRPC.buildWebBase()
        self.remoteHost = PROPERTIES.getRemoteHost()
        self.season     = self.seasonal.getHoliday()
        self.openRouter = OpenRouter(cache=self.cache)
        self.imageCache = (SETTINGS.getCacheSetting('imageCache'  , json_data=True) or {})
        self.log(f'__init__, imageCache = {len(self.imageCache)}')
        
        
    def __del__(self):
        SETTINGS.setCacheSetting('imageCache'  , self.imageCache  , json_data=True)
        self.log(f'__del__, imageCache = {len(self.imageCache)}')
        
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

       
    def selectLogo(self, citem: dict) -> list:
        logos = []
        logos.extend(self.getLocalLogo(citem.get('name'),select=True))
        logos.extend(self.getLogoResources(citem, select=True))
        logos.extend(self.getTVShowLogo(citem.get('name'), select=True))
        self.log('selectLogo, chname = %s, logos = %s'%(citem.get('name'), len(logos)))
        return list([_f for _f in logos if _f])


    def queueLogo(self, citem):
        if hasattr(self.service,'logoQue'): 
            self.service.logoQue.add(dumpJSON(citem))


    def getCache(self, chname):
        image = self.imageCache.get(chname)
        if not image: self.queueLogo({'name':chname})
        self.log('getCache, name = %s, image = %s'%(chname,image))
        return image


    def setCache(self, chname, image=None):
        if image in [LOGO,COLOR_LOGO]: return image
        self.imageCache[chname] = image
        self.log('setCache, name = %s, image = %s'%(chname,image))
        return image
        
        

    def getLogo(self, citem: dict, fallback=None, lookup=False, logo=None) -> str:
        self.log('[%s] getLogo, name = %s, lookup = %s'%(citem.get('id'),citem.get('name'),lookup))
        if not logo and citem.get('name') == LANGUAGE(32002): logo = self.season.get('logo')               #seasonal
        if not logo and not lookup:                           logo = self.getCache(citem.get('name'))      #cache
        if not logo and not lookup:                           logo = self.queueLogo(citem)                 #queue ie lookup/find from resources.
        if not logo and not lookup and fallback:              logo = fallback                              #fallback
        if not logo and lookup:                               logo = self.getLocalLogo(citem.get('name'))  #local
        if not logo and lookup:                               logo = self.getLogoResources(citem)          #resources
        if not logo and lookup:                               logo = self.getTVShowLogo(citem.get('name')) #tvshow
        if not logo and lookup:                               logo = self.generateOnline(citem.get('name'))#generative online
        if not logo and lookup:                               logo = self.generateLocal(citem.get('name')) #generative local
        if not logo:                                          logo = LOGO                                  #default
        return self.buildWebImage(citem.get('name'), cleanImage(logo))
            
            
    def buildWebImage(self, chname: str, image: str='') -> str:
        if not any(set(['smb' in image, 'nfs' in image, 'http' in image, 'resource' in image])):
            if image.startswith('image://'):                                 image = '%s/image/%s'%(self.baseURL,quoteString(image))
            elif not image.startswith('http://%s/logos/'%(self.remoteHost)): image = 'http://%s/images/%s'%(self.remoteHost,quoteString(image))
            self.setCache(chname, image)
            return 'http://%s/logos/%s'%(self.remoteHost,quoteString(chname)) #host channel logos, cache returns image
        return self.setCache(chname, image)
        

    @cacheit(expiration=datetime.timedelta(minutes=5))
    def getLocalLogo(self, chname: str, select: bool=False) -> list:
        logos = []
        for path in LOCAL_FOLDERS:
            for ext in IMG_EXTS:
                if FileAccess.exists(os.path.join(path,'%s%s'%(chname,ext))):
                    self.log('getLocalLogo, found %s'%(os.path.join(path,'%s%s'%(chname,ext))))
                    if select: logos.append(os.path.join(path,'%s%s'%(chname,ext)))
                    else: return os.path.join(path,'%s%s'%(chname,ext))
        if select: return logos
        
        
    def getLogoResources(self, citem: dict, select: bool=False,  copy: bool=False) -> dict and None:
        self.log('getLogoResources, chname = %s, type = %s, select = %s'%(citem.get('name'), citem.get('type'),select))
        def __getResources(type):
            resources = SETTINGS.getSetting('Resource_Logos').split('|').copy()
            if   type in ["TV Genres","Movie Genres"]:               resources.extend(GENRE_RESOURCE)
            elif type in ["TV Networks","Movie Studios"]:            resources.extend(STUDIO_RESOURCE)
            elif type in ["Music Genres","Radio"] or isRadio(citem): resources.extend(MUSIC_RESOURCE)
            else:                                                    resources.extend(GENRE_RESOURCE + STUDIO_RESOURCE)
            self.log('getResources, type = %s, resources = %s'%(type,resources))
            return resources

        def __fillResource(id):
            results  = {}
            response = self.jsonRPC.walkListDirectory(os.path.join('special://home/addons/%s/resources'%id), exts=IMG_EXTS, checksum=SETTINGS.getAddonDetails(id).get('version',ADDON_VERSION), expiration=datetime.timedelta(days=28))
            for path, images in list(response.items()):
                for image in images: results[os.path.splitext(image)[0]] = '%s/%s'%(path,image)
            return results
            
        resources     = __getResources(citem.get('type','Custom'))
        cacheName     = 'getLogoResources.%s.%s'%(getMD5(citem.get('name')),select)
        cacheResponse = self.cache.get(cacheName, checksum=getMD5('|'.join([SETTINGS.getAddonDetails(id).get('version',ADDON_VERSION) for id in resources])))
        if not cacheResponse:
            logos = []
            for id in resources:
                if SETTINGS.hasAddon(id):
                    results = __fillResource(id)
                    self.log('getLogoResources, checking %s, results = %s'%(id,len(results)))
                    for name, logo in list(results.items()):
                        if self.matchName(citem.get('name'), name):
                            self.log('getLogoResources, found %s'%(logo))
                            logos.append(logo)
                            if not select:
                                if copy:
                                    nlogo = os.path.join(TEMP_IMAGE_LOC,'%s.%s'%(citem.get('name'),logo.strip('/')[-3:]))
                                    if FileAccess.copy(logo,nlogo): logo = nlogo
                                return self.cache.set(cacheName, logo, checksum=getMD5('|'.join(resources)), expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if logos: return self.cache.set(cacheName, logos, checksum=getMD5('|'.join(resources)), expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
        return cacheResponse
        

    def getTVShowLogo(self, chname: str, select: bool=False):
        self.log('getTVShowLogo, chname = %s, select = %s'%(chname,select))
        cacheName     = 'getTVShowLogo.%s.%s'%(getMD5(chname),select)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            logos = []
            items = self.jsonRPC.getTVshows()
            for item in items:
                if self.matchName(chname, item.get('title','')):
                    for key in ['clearlogo','logo','logos','clearart','icon']:
                        logo = item.get('art',{}).get(key,'').replace('image://DefaultFolder.png/','').rstrip('/')
                        if logo:
                            self.log('getTVShowLogo, found %s'%(logo))
                            logos.append(logo)
                            if not select: return self.cache.set(cacheName, logo, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if logos: return self.cache.set(cacheName, logos, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
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
        
        if __normalize(chname) == __normalize(title): return True
        if SequenceMatcher(None, __normalize(chname), __normalize(title)).ratio() >= threshold: return True
        return False
        
            
    def isMono(self, file: str, mono: bool=False) -> bool:
        if   file.startswith('resource://') and (bool(set([match in file.lower() for match in ['transparent','white','mono']]))): return True
        elif file.startswith('http'): pass #todo dl to io then check
        elif SETTINGS.hasAddon('script.module.pil'):
            try:
                from PIL import Image, ImageStat
                file = unquoteString(file.replace('resource://','special://home/addons/').replace('image://','')).replace('\\','/')
                with FileAccess.stream(file, "rb") as f:
                    img = Image.open(io.BytesIO(f.read()))
                mono = reduce(lambda x, y: x and y < 0.005, ImageStat.Stat(img).var, True)
                self.log('isMono, mono = %s, file = %s'%(mono,file))  
            except Exception as e: self.log("isMono, failed! %s\nfile = %s"%(e,file), xbmc.LOGWARNING)
        return mono
        
        
    def generateLocal(self, text, background=os.path.join(MEDIA_LOC,'blank.png'), font_path=FileAccess.translatePath(os.path.join('special://skin','fonts','NotoSans-Regular.ttf')), font_size=60, text_color=(255, 255, 255)):
        """
        Generates a placeholder image with text on a background image.

        Args:
            text: The text to display on the placeholder.
            background: Path to the background image.
            font_path: Path to the font file (optional).
            font_size: Font size for the text (optional).
            text_color: Color of the text (optional).
        """

        if SETTINGS.hasAddon('script.module.pil'):
            from PIL import Image, ImageDraw, ImageFont
            # Read background bytes and close the file handle safely
            fle = FileAccess.open(background, "rb")
            try: bg_bytes = fle.readBytes()
            finally: fle.close()
            # Load image and ensure an alpha channel for safe drawing
            img  = Image.open(io.BytesIO(bg_bytes)).convert("RGBA")
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype(font_path, font_size)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width  = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            # Center the text. Adjust by bbox origin so fonts with offsets are handled.
            x = (img.width - text_width) // 2 - bbox[0]
            y = (img.height - text_height) // 2 - bbox[1]
            draw.text((x, y), text, font=font, fill=text_color)
            # Sanitize text for filename and limit length
            safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', text)[:200] or "image"
            image_path = os.path.join(FileAccess.translatePath(TEMP_IMAGE_LOC), f"{safe_name}.png")
            fle = FileAccess.open(image_path, "rb")
            img.save(fle, "PNG")
            fle.close()
            return image_path
        
        
    def generateOnline(self, chname, select=False, model=SETTINGS.getSetting('OPENROUTER_IMAGE_MODEL')):
        return
        # if select: count = 5
        # else:      count = 1
        # logos = self.openRouter.getImage(chname, count, model)