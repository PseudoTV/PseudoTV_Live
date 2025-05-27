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

# -*- coding: utf-8 -*-

from globals    import *
from functools  import reduce
from difflib    import SequenceMatcher
from seasonal   import Seasonal 

LOCAL_FOLDERS   = [LOGO_LOC, IMAGE_LOC]
MUSIC_RESOURCE  = ["resource.images.musicgenreicons.text"]
GENRE_RESOURCE  = ["resource.images.moviegenreicons.transparent"]
STUDIO_RESOURCE = ["resource.images.studios.white"]

class Service:
    from jsonrpc import JSONRPC
    player  = PLAYER()
    monitor = MONITOR()
    jsonRPC = JSONRPC()
    def _interrupt(self) -> bool:
        return PROPERTIES.isPendingInterrupt()
    def _suspend(self) -> bool:
        return PROPERTIES.isPendingSuspend()
        
        
class Resources:    
    queuePool = {}
    
    def __init__(self, service=None):
        if service is None: service = Service()
        self.service    = service
        self.jsonRPC    = service.jsonRPC
        self.cache      = service.jsonRPC.cache
        self.baseURL    = service.jsonRPC.buildWebBase()
        self.remoteHost = PROPERTIES.getRemoteHost()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getLogo(self, citem: dict, fallback=LOGO, auto=False) -> str:
        if citem.get('name') == LANGUAGE(32002): logo = Seasonal().getHoliday().get('logo')   #seasonal
        else:                                    logo = self.getLocalLogo(citem.get('name'))  #local
        if not logo:                             logo = self.getCachedLogo(citem)             #cache
        if not logo and auto:                    logo = self.getLogoResources(citem)          #resources
        if not logo and auto:                    logo = self.getTVShowLogo(citem.get('name')) #tvshow
        if not logo:                             logo = (fallback or LOGO)                    #fallback
        self.log('getLogo, name = %s, logo = %s, auto = %s'%(citem.get('name'), logo, auto))
        return logo
        

    @cacheit(expiration=datetime.timedelta(days=MAX_GUIDEDAYS), json_data=True)
    def selectLogo(self, citem: dict) -> list:
        logos = []
        logos.extend(self.getLocalLogo(citem.get('name'),select=True))
        logos.extend(self.getLogoResources(citem, select=True))
        logos.extend(self.getTVShowLogo(citem.get('name'), select=True))
        self.log('selectLogo, chname = %s, logos = %s'%(citem.get('name'), len(logos)))
        return list([_f for _f in logos if _f])


    def queueLOGO(self, param):
        params = self.queuePool.setdefault('params',[])
        params.append(param)
        self.queuePool['params'] = setDictLST(params)
        self.log("queueLOGO, saving = %s, param = %s"%(len(self.queuePool['params']),param))
        timerit(SETTINGS.setCacheSetting)(5.0,['queueLOGO', self.queuePool, ADDON_VERSION, True])
            
            
    def getCachedLogo(self, citem, select=False):
        cacheFuncs = [{'name':'getLogoResources.%s.%s'%(getMD5(citem.get('name')),select), 'args':(citem,select)             ,'checksum':getMD5('|'.join([self.jsonRPC.getAddonDetails(id).get('version',ADDON_VERSION) for id in self.getResources(citem)]))},
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
        response = self.jsonRPC.walkListDirectory(os.path.join('special://home/addons/%s/resources'%id), exts=IMG_EXTS, checksum=self.jsonRPC.getAddonDetails(id).get('version',ADDON_VERSION), expiration=datetime.timedelta(days=28))
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
        cacheResponse = self.cache.get(cacheName, checksum=getMD5('|'.join([self.jsonRPC.getAddonDetails(id).get('version',ADDON_VERSION) for id in resources])))
        if not cacheResponse:
            for id in list(dict.fromkeys(resources)):
                if not hasAddon(id):
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
        logos     = []
        items     = self.jsonRPC.getTVshows()
        cacheName = 'getTVShowLogo.%s.%s'%(getMD5(chname),select)
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            for item in items:
                if self.matchName(chname, item.get('title',''), auto=select):
                    keys = ['clearlogo','logo','logos','clearart','icon']
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
        #convert any local images to url via local server and/or kodi web server.
        if image.startswith(LOGO_LOC) and self.remoteHost:
            image = 'http://%s/images/%s'%(self.remoteHost,quoteString(os.path.split(image)[1]))
        elif image.startswith(('image://','image%3A')) and self.baseURL and not ('smb' in image or 'nfs' in image or 'http' in image):
            image = '%s/image/%s'%(self.baseURL,quoteString(image))
        self.log('buildWebImage, returning image = %s'%(image))
        return image
            
            
    def isMono(self, file: str) -> bool:
        if file.startswith('resource://') and (bool(set([match in file.lower() for match in ['transparent','white','mono']]))): return True
        elif hasAddon('script.module.pil'):
            try:
                from PIL import Image, ImageStat
                file = unquoteString(file.replace('resource://','special://home/addons/').replace('image://','')).replace('\\','/')
                mono = reduce(lambda x, y: x and y < 0.005, ImageStat.Stat(Image.open(FileAccess.open(file.encode('utf-8').strip(),'r'),mode='r')).var, True)
                self.log('isMono, mono = %s, file = %s'%(mono,file))  
                return mono
            except Exception as e: self.log("isMono, failed! %s\nfile = %s"%(e,file), xbmc.LOGWARNING)
        return False
        
        
    def generate_placeholder(self, text, background_image_path=FileAccess.translatePath(os.path.join(MEDIA_LOC,'blank.png')), output_path=TEMP_LOC, font_path=FileAccess.translatePath(os.path.join('special://skin','fonts','NotoSans-Regular.ttf')), font_size=30, text_color=(255, 255, 255)):
        """
        Generates a placeholder image with text on a background image.

        Args:
            text: The text to display on the placeholder.
            background_image_path: Path to the background image.
            output_path: Path to save the generated placeholder image.
            font_path: Path to the font file (optional).
            font_size: Font size for the text (optional).
            text_color: Color of the text (optional).
        """

        if hasAddon('script.module.pil'):
            from PIL import Image, ImageDraw, ImageFont
            # Open the background image
            background_image = Image.open(background_image_path)
            # Create a drawing object
            draw = ImageDraw.Draw(background_image)
            # Choose a font
            font = ImageFont.truetype(font_path, font_size)
            # Calculate text size
            text_width, text_height = draw.textsize(text, font)
            # Calculate text position for centering 
            x = (background_image.width - text_width) // 2
            y = (background_image.height - text_height) // 2
            # Draw the text on the image
            draw.text((x, y), text, font=font, fill=text_color)
            # Save the image
            file_name = os.path.join(output_path,'%s.png'%(text))
            fle = FileAccess.open(file_name,'wb')
            background_image.save(fle,'png')
            fle.close()

        # Example usage
        # generate_placeholder("Product Image", "background.jpg", "placeholder.jpg")