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

LOCAL_RESOURCES = [LOGO_LOC, IMAGE_LOC]
MUSIC_RESOURCE  = ["resource.images.musicgenreicons.text"]
GENRE_RESOURCE  = ["resource.images.moviegenreicons.transparent"]
STUDIO_RESOURCE = ["resource.images.studios.white"]

class Resources:
    def __init__(self, jsonRPC, cache):
        self.cache   = cache
        self.jsonRPC = jsonRPC
                
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getLogo(self, chname, type="Custom", logo=None):
        if not logo: logo = self.getLocalLogo(chname)              #local
        if not logo: logo = self.getLogoResources(chname, type)    #resource
        if not logo: logo = self.getTVShowLogo(chname)             #tvshow 
        if not logo: logo = LOGO
        self.log('getLogo, chname = %s, logo = %s'%(chname, logo))
        return logo
        
        
    def selectLogo(self, chname, type="Custom"):
        logos = []
        logos.extend(self.getLocalLogo(chname,select=True))
        logos.extend(self.getLogoResources(chname,type,select=True))
        logos.append(self.getTVShowLogo(chname))
        self.log('selectLogo, chname = %s, logos = %s'%(chname, len(logos)))
        return list([_f for _f in logos if _f])


    def getLocalLogo(self, chname, select=False):
        logos = []
        for path in LOCAL_RESOURCES:
            for ext in IMG_EXTS:
                if FileAccess.exists(os.path.join(path,'%s%s'%(chname,ext))):
                    if select: logos.append(os.path.join(path,'%s%s'%(chname,ext)))
                    else: return os.path.join(path,'%s%s'%(chname,ext))
        if select: return logos
        
    
    def getLogoResources(self, chname, type, select=False):
        self.log('getLogoResources, chname = %s, type = %s'%(chname, type))
        resources = SETTINGS.getSetting('Resource_Logos').split('|').copy()
        if type in ["TV Genres","Movie Genres"]:
            resources.extend(GENRE_RESOURCE)
        elif type in ["TV Networks","Movie Studios"]:
            resources.extend(STUDIO_RESOURCE)
        elif type == "Music Genres":
            resources.extend(MUSIC_RESOURCE)
        else:
            resources.extend(GENRE_RESOURCE)
            resources.extend(STUDIO_RESOURCE)
            resources.extend(MUSIC_RESOURCE)
        
        logos = []
        cacheName = 'getLogoResources.%s.%s'%(getMD5(chname),select)
        cacheResponse = self.cache.get(cacheName, checksum=getMD5('|'.join(resources)))
        if not cacheResponse:
            for id in list(dict.fromkeys(resources)):
                if MONITOR.waitForAbort(0.001): 
                    self.log('getLogoResources, waitForAbort')
                    break
                elif not hasAddon(id):
                    self.log('getLogoResources, missing %s'%(id))
                    continue
                else:
                    self.log('getLogoResources, checking %s'%(id))
                    results = self.jsonRPC.walkListDirectory(os.path.join('special://home/addons/%s'%id,'resources'), exts=IMG_EXTS, depth=CHANNEL_LIMIT, checksum=self.jsonRPC.getAddonDetails(id).get('version',ADDON_VERSION), expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
                    for path, images in list(results.items()):
                        for image in images:
                            name, ext = os.path.splitext(image)
                            if self.matchName(chname, name, type):
                                self.log('getLogoResources, found %s'%('%s/%s'%(path,image)))
                                if select: logos.append('%s/%s'%(path,image))
                                else: return self.cache.set(cacheName, '%s/%s'%(path,image), checksum=getMD5('|'.join(resources)), expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
            if select:
                if len(logos) > 0: cacheResponse = self.cache.set(cacheName, logos, checksum=getMD5('|'.join(resources)), expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
                else: return logos
        return cacheResponse
        
        
    def getTVShowLogo(self, chname):
        self.log('getTVShowLogo, chname = %s'%(chname))
        cacheName = 'getTVShowLogo.%s'%(getMD5(chname))
        cacheResponse = self.cache.get(cacheName)
        if not cacheResponse:
            items = self.jsonRPC.getTVshows()
            for item in items:
                if self.matchName(chname, item.get('title','')):
                    keys = ['clearlogo','logo','logos','clearart','icon']
                    for key in keys:
                        art = item.get('art',{}).get(key,'').replace('image://DefaultFolder.png/','')
                        if art:
                            self.log('getTVShowLogo, found %s'%(art))
                            return self.cache.set(cacheName, art, expiration=datetime.timedelta(days=MAX_GUIDEDAYS))
        return cacheResponse
        
        
    def matchName(self, chname, name, type='Custom'):
        patterns = list(set([chname, getChannelSuffix(chname,type), cleanChannelSuffix(chname, type), stripRegion(chname), splitYear(chname)[0], slugify(chname), slugify(stripRegion(chname))]))
        for pattern in patterns:
            if name.lower() == pattern.lower():
                return True
        

    def buildWebImage(self, image):
        if image.startswith(('resource://','special://','image://','http://')): return image
        # return '%s/image/%s'%(self.jsonRPC.buildWebBase(),'image://%s'%(quoteString(image))) #todo debug
        return image
            
            
    def isMono(self, file):
        if file.startswith('resource://') and (bool(set([match in file.lower() for match in ['transparent','white','mono']]))):
            return True
        elif hasAddon('script.module.pil'):
            try:
                from PIL import Image, ImageStat
                file = unquoteString(file.replace('resource://','special://home/addons/').replace('image://','')).replace('\\','/')
                mono = reduce(lambda x, y: x and y < 0.005, ImageStat.Stat(Image.open(FileAccess.open(file))).var, True)
                self.log('isMono, mono = %s, file = %s'%(mono,file))
                return mono
            except Exception as e: self.log("isMono, failed! %s"%(e), xbmc.LOGWARNING)
        return False