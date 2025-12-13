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

LOCAL_FOLDERS   = [LOGO_LOC, IMAGE_LOC]
MUSIC_RESOURCE  = ["resource.images.musicgenreicons.text"]
GENRE_RESOURCE  = ["resource.images.moviegenreicons.transparent"]
STUDIO_RESOURCE = ["resource.images.studios.white"]

class Service:
    from jsonrpc import JSONRPC
    player    = PLAYER()
    monitor   = MONITOR()
    jsonRPC   = JSONRPC()
    def _shutdown(self, wait=1.0) -> bool:
        return (self._wait(wait) | PROPERTIES.isPendingShutdown())
    def _interrupt(self) -> bool:
        return PROPERTIES.isPendingInterrupt()
    def _suspend(self, wait=1.0) -> bool:
        return (self._wait(wait) | PROPERTIES.isPendingSuspend())
    def _wait(self, wait=1.0):
        while not self.monitor.abortRequested() and wait > 0:
            if (self.monitor.waitForAbort(CPU_CYCLE) | PROPERTIES.isPendingShutdown() | PROPERTIES.isPendingRestart() | PROPERTIES.isPendingSuspend() | PROPERTIES.isPendingInterrupt()): return True
            else: wait -= CPU_CYCLE
        return False
        
        
class Resources:
    
    def __init__(self, service=None):
        self.log('__init__')    
        if service is None:
            service = Service()
            
        self.service    = service
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.jsonRPC.cache
        self.baseURL    = service.jsonRPC.buildWebBase()
        self.remoteHost = PROPERTIES.getRemoteHost()
        self.openRouter = OpenRouter(cache=self.cache)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getLogo(self, citem: dict, fallback=LOGO, auto=False) -> str:
        seasonal = citem.get('name') == LANGUAGE(32002)
        logo = self.getLocalLogo(citem.get('name'))                            #local
        if not logo and seasonal: logo = Seasonal().getHoliday().get('logo')   #seasonal
        if not logo:              logo = self.getCachedLogo(citem)             #cache
        if not logo and auto:     logo = self.getLogoResources(citem)          #resources
        if not logo and auto:     logo = self.getTVShowLogo(citem.get('name')) #tvshow
        if not logo:              logo = (fallback or LOGO)                    #fallback
        self.log('getLogo, name = %s, logo = %s, auto = %s'%(citem.get('name'), logo, auto))
        return self.buildWebImage(cleanImage(logo))
        

    @cacheit(expiration=datetime.timedelta(days=MAX_GUIDEDAYS), json_data=True)
    def selectLogo(self, citem: dict) -> list:
        logos = []
        logos.extend(self.getLocalLogo(citem.get('name'),select=True))
        logos.extend(self.getLogoResources(citem, select=True))
        logos.extend(self.getTVShowLogo(citem.get('name'), select=True))
        self.log('selectLogo, chname = %s, logos = %s'%(citem.get('name'), len(logos)))
        return list([_f for _f in logos if _f])


    @executeit
    def queueLOGO(self, param):
        params = SETTINGS.queuePool.setdefault('queueLOGO',[])
        params.append(param)
        SETTINGS.queuePool['queueLOGO'] = setDictLST(params)
        self.log("queueLOGO, queuing = %s, param = %s"%(len(SETTINGS.queuePool['queueLOGO']),param))
            
            
    def getCachedLogo(self, citem, select=False):
        cacheFuncs = [{'name':'getLogoResources.%s.%s'%(getMD5(citem.get('name')),select), 'args':(citem,select)             ,'checksum':getMD5('|'.join([SETTINGS.getAddonDetails(id).get('version',ADDON_VERSION) for id in self.getResources(citem)]))},
                      {'name':'getTVShowLogo.%s.%s'%(getMD5(citem.get('name')),select)   , 'args':(citem.get('name'), select),'checksum':ADDON_VERSION}]
        for cacheItem in cacheFuncs:
            cacheResponse = self.cache.get(cacheItem.get('name',''),cacheItem.get('checksum',ADDON_VERSION))
            if cacheResponse: 
                self.log('getCachedLogo, chname = %s, type = %s, logo = %s'%(citem.get('name'), citem.get('type'), cacheResponse))
                return cacheResponse
            else: self.queueLOGO(cacheItem)


    def getLocalLogo(self, chname: str, select: bool=False) -> list:
        logos = []
        for path in LOCAL_FOLDERS:
            for ext in IMG_EXTS:
                if FileAccess.exists(os.path.join(path,'%s%s'%(chname,ext))):
                    self.log('getLocalLogo, found %s'%(os.path.join(path,'%s%s'%(chname,ext))))
                    if select: logos.append(os.path.join(path,'%s%s'%(chname,ext)))
                    else: return os.path.join(path,'%s%s'%(chname,ext))
        if select: return logos
        
        
    def fillLogoResource(self, id):
        results  = {}
        response = self.jsonRPC.walkListDirectory(os.path.join('special://home/addons/%s/resources'%id), exts=IMG_EXTS, checksum=SETTINGS.getAddonDetails(id).get('version',ADDON_VERSION), expiration=datetime.timedelta(days=28))
        for path, images in list(response.items()):
            for image in images:
                name, ext = os.path.splitext(image)
                results[name] = '%s/%s'%(path,image)
        return results
        
        
    def getResources(self, citem={}):
        resources = SETTINGS.getSetting('Resource_Logos').split('|').copy()
        if   citem.get('type') in ["TV Genres","Movie Genres"]:               resources.extend(GENRE_RESOURCE)
        elif citem.get('type') in ["TV Networks","Movie Studios"]:            resources.extend(STUDIO_RESOURCE)
        elif citem.get('type') in ["Music Genres","Radio"] or isRadio(citem): resources.extend(MUSIC_RESOURCE)
        else:                                                                 resources.extend(GENRE_RESOURCE + STUDIO_RESOURCE)
        self.log('getResources, type = %s, resources = %s'%(citem.get('type'),resources))
        return resources
        
        
    def getLogoResources(self, citem: dict, select: bool=False) -> dict and None:
        self.log('getLogoResources, chname = %s, type = %s, select = %s'%(citem.get('name'), citem.get('type'),select))
        logos     = []
        resources = self.getResources(citem)
        cacheName = 'getLogoResources.%s.%s'%(getMD5(citem.get('name')),select)
        cacheResponse = self.cache.get(cacheName, checksum=getMD5('|'.join([SETTINGS.getAddonDetails(id).get('version',ADDON_VERSION) for id in resources])))
        if not cacheResponse:
            for id in list(dict.fromkeys(resources)):
                if not SETTINGS.hasAddon(id):
                    self.log('getLogoResources, missing %s'%(id))
                    continue
                else:
                    results = self.fillLogoResource(id)
                    self.log('getLogoResources, checking %s, results = %s'%(id,len(results)))
                    for name, logo in list(results.items()):
                        if self.matchName(citem.get('name'), name, auto=select):
                            self.log('getLogoResources, found %s'%(logo))
                            if select: logos.append(logo)
                            else: return self.cache.set(cacheName, logo, checksum=getMD5('|'.join(resources)), expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if select: return self.cache.set(cacheName, logos, checksum=getMD5('|'.join(resources)), expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
        return cacheResponse
        

    def getTVShowLogo(self, chname: str, select: bool=False) -> dict and None:
        self.log('getTVShowLogo, chname = %s, select = %s'%(chname,select))
        logo      = ""
        logos     = []
        items     = self.jsonRPC.getTVshows()
        keys      = ['clearlogo','logo','logos','clearart','icon']
        cacheName = 'getTVShowLogo.%s.%s'%(getMD5(chname),select)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            for item in items:
                if chname.lower() == item.get('title','').lower():
                    for key in keys:
                        logo = item.get('art',{}).get(key,'').replace('image://DefaultFolder.png/','').rstrip('/')
                        if logo:
                            self.log('getTVShowLogo, found %s'%(logo))
                            if select: logos.append(logo)
                            else: return self.cache.set(cacheName, logo, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
                            
            for item in items:
                if self.matchName(chname, item.get('title',''), auto=select):
                    for key in keys:
                        logo = item.get('art',{}).get(key,'').replace('image://DefaultFolder.png/','').rstrip('/')
                        if logo:
                            self.log('getTVShowLogo, found %s'%(logo))
                            if select: logos.append(logo)
                            else: return self.cache.set(cacheName, logo, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if select: return self.cache.set(cacheName, logos, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
        return cacheResponse
        
        
    #todo refactor this mess, proper pattern matching...
    def matchName(self, chname: str, name: str, type: str='Custom', auto: bool=False) -> bool and None: #todo auto setting SETTINGS.getSettingBool('')
        chnames = list(set([chname, splitYear(chname)[0], stripRegion(chname), getChannelSuffix(chname, type), cleanChannelSuffix(chname, type), chname.replace('and', '&'), chname.replace('&','and'), slugify(chname), validString(chname)]))
        renames = list(set([name, splitYear(name)[0], stripRegion(name), slugify(name), validString(name)]))
        for chname in chnames:
            if not chname: continue
            elif auto: return SequenceMatcher(None, chname.lower(), name.lower()).ratio() >= .75
            elif chname.lower() == name.lower(): return True
            for rename in renames:
                if not rename: continue
                elif chname.lower() == rename.lower(): return True
        return False
        
        
    def buildWebImage(self, image: str) -> str:
        #convert any local images to url via local to kodi web server.
        if image.startswith(LOGO_LOC) and self.remoteHost:
            image = 'http://%s/images/%s'%(self.remoteHost,quoteString(os.path.split(image)[1]))
        elif image.startswith(('image')) and self.baseURL and not any(set(['smb' in image, 'nfs' in image, 'http' in image])):
            image = '%s/image/%s'%(self.baseURL,quoteString(image))
        self.log('buildWebImage, returning image = %s'%(image))
        return image
            
            
    def isMono(self, file: str, mono: bool=False) -> bool:
        if   file.startswith('resource://') and (bool(set([match in file.lower() for match in ['transparent','white','mono']]))): return True
        elif file.startswith('http'): pass #todo dl to io then check
        elif SETTINGS.hasAddon('script.module.pil'):
            try:
                from PIL import Image, ImageStat
                file = unquoteString(file.replace('resource://','special://home/addons/').replace('image://','')).replace('\\','/')
                with xbmcvfs.File(file, "rb") as f:
                    img = Image.open(io.BytesIO(f.read()))
                mono = reduce(lambda x, y: x and y < 0.005, ImageStat.Stat(img).var, True)
                self.log('isMono, mono = %s, file = %s'%(mono,file))  
            except Exception as e: self.log("isMono, failed! %s\nfile = %s"%(e,file), xbmc.LOGWARNING)
        return mono
        
        
    def generate_placeholder(self, text, background_image_path=os.path.join(MEDIA_LOC,'blank.png'), font_path=FileAccess.translatePath(os.path.join('special://skin','fonts','NotoSans-Regular.ttf')), font_size=30, text_color=(255, 255, 255)):
        """
        Generates a placeholder image with text on a background image.

        Args:
            text: The text to display on the placeholder.
            background_image_path: Path to the background image.
            font_path: Path to the font file (optional).
            font_size: Font size for the text (optional).
            text_color: Color of the text (optional).
        """

        if SETTINGS.hasAddon('script.module.pil'):
            from PIL import Image, ImageDraw, ImageFont
            fle = FileAccess.open(background_image_path, "rb")
            img = Image.open(io.BytesIO(fle.readBytes()))
            fle.close()
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype(font_path, font_size)
            text_width, text_height = draw.textsize(text, font)
            draw.text(((img.width - text_width) // 2, (img.height - text_height) // 2), text, font=font, fill=text_color)
            img.save(os.path.join(xbmcvfs.translatePath(TEMP_IMAGE_LOC),'%s.png'%(text)), "PNG")

        # Example usage
        # generate_placeholder("Product Image", "background.jpg", "placeholder.jpg")
        
        
    # def getAI(self, chname, select=False, model=SETTINGS.getSetting('OPENROUTER_IMAGE_MODEL'))
        # if select: count = 5
        # else:      count = 1
        # # logos = self.openRouter.getImage(chname, count, model)