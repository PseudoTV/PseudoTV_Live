#   Copyright (C) 2023 Lunatixz
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

TEXTURES        = 'Textures.xbt'
IMG_EXTS        = ['.png','.jpg','.gif']

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


    def getLogo(self, chname, type="Custom"):
        logo = self.getLocalLogo(chname)                        #local
        if not logo: logo = self.getLogoResources(chname, type) #resource
        if not logo: logo = self.getTVShowLogo(chname)          #tvshow 
        return (logo or LOGO)
        
        
    def getLocalLogo(self, chname):
        for path in LOCAL_RESOURCES:
            for ext in IMG_EXTS:
                if FileAccess.exists(os.path.join(path,'%s%s'%(chname,ext))):
                    return os.path.join(path,'%s%s'%(chname,ext))
        
    
    def getLogoResources(self, chname, type):
        self.log('getLogoResources, chname = %s, type = %s'%(chname, type))
        resources = SETTINGS.getSetting('Resource_Logos').split('|')
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
            
        cacheName = 'getLogoResources.%s'%(getMD5(chname))
        cacheResponse = self.cache.get(cacheName, checksum=getMD5('|'.join(resources)))
        if not cacheResponse:
            for id in list(set(resources)):
                if MONITOR.waitForAbort(0.001): 
                    self.log('getLogoResources, interrupted')
                    break
                    
                if not BUILTIN.getInfoBool('HasAddon(%s)'%(id),'System'):
                    self.log('getLogoResources, missing %s'%(id))
                    continue
                    
                self.log('getLogoResources, checking %s'%(id))
                paths = self.walkResource(id)
                for path in paths:
                    for image in paths[path]:
                        name, ext = os.path.splitext(image)
                        if self.matchName(chname, name):
                            self.log('getLogoResources, found %s'%('%s/%s'%(path,image)))
                            return self.cache.set(cacheName, '%s/%s'%(path,image), checksum=getMD5('|'.join(resources)), expiration=datetime.timedelta(days=int(SETTINGS.getSetting('Max_Days'))))
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
                        art = item.get('art',{}).get(key)
                        if art:
                            self.log('getTVShowLogo, found %s'%(art))
                            return self.cache.set(cacheName, art, expiration=datetime.timedelta(days=int(SETTINGS.getSetting('Max_Days'))))
        return cacheResponse
        
        
    def matchName(self, chname, name):
        patterns = list(set([cleanChannelSuffix(chname, type),stripRegion(chname),splitYear(chname)[0],slugify(chname),slugify(stripRegion(chname))]))
        patterns.insert(0,chname)#make sure unaltered channel name first to parse.
        for pattern in patterns:
            if name.lower() == pattern.lower():
                return True
        
        
    def walkResource(self, id, exts=IMG_EXTS): #convert path from id to vfs, include version checksum for cache expiration
        return self.walkDirectory(os.path.join('special://home/addons/%s'%id,'resources'),exts,checksum=self.jsonRPC.getAddonDetails(id).get('version',ADDON_VERSION))
        
        
    @cacheit(expiration=datetime.timedelta(days=28),json_data=True)
    def walkDirectory(self, path, exts=IMG_EXTS, checksum=ADDON_VERSION): #recursively walk all folders, parse xbt textures.
        def _parseXBT():
            self.log('walkDirectory, %s Found'%(TEXTURES))
            resource = path.replace('/resources','').replace('special://home/addons/','resource://')
            walk.setdefault(resource,[]).extend(self.jsonRPC.getListDirectory(resource,checksum,datetime.timedelta(days=int(SETTINGS.getSetting('Max_Days'))))[1])
            return walk
            
        walk = dict()
        path = path.replace('\\','/')
        self.log('walkDirectory, path = %s, exts = %s'%(path,exts))
        dirs, files = self.jsonRPC.getListDirectory(path,checksum,datetime.timedelta(days=int(SETTINGS.getSetting('Max_Days'))))
        if TEXTURES in files: return _parseXBT()
        else: walk.setdefault(path,[]).extend(list([f for f in files if f.endswith(tuple(exts))]))
        for idx, dir in enumerate(dirs): 
            if MONITOR.waitForAbort(0.001): 
                self.log('walkDirectory, interrupted')
                return
                
            self.log('walkDirectory, walking %s/%s directory'%(idx,len(dirs)))
            walk.update(self.walkDirectory(os.path.join(path, dir),exts,checksum))
        return walk
            

    def buildWebImage(self, image):
        if image.startswith(('resource://','special://','image://')): return image
        return '%s/image/%s'%(self.jsonRPC.buildWebBase(),'image://%s'%(quoteString(image)))
            
            
    def isMono(self, file):
        if file.startswith('resource://') and (bool(set([match in file.lower() for match in ['transparent','white','mono']]))):
            return True
        elif BUILTIN.getInfoBool('HasAddon(script.module.pil)','System'):
            try:
                from PIL import Image, ImageStat
                file = unquoteString(file.replace('resource://','special://home/addons/').replace('image://','')).replace('\\','/')
                mono = reduce(lambda x, y: x and y < 0.005, ImageStat.Stat(Image.open(xbmcvfs.translatePath(file))).var, True)
                self.log('isMono, mono = %s, file = %s'%(mono,file))
                return mono
            except Exception as e: self.log("isMono, failed! %s"%(e), xbmc.LOGWARNING)
        return False