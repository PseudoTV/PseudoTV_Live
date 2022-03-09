#   Copyright (C) 2022 Lunatixz
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

from resources.lib.globals     import *
from fuzzywuzzy                import process as FuzzyProcess

try:
    from PIL                   import Image, ImageStat
    hasPillow = True
except:
    hasPillow = False

class Resources:
    TEXTURES = 'Textures.xbt'

    def __init__(self, jsonRPC):
        self.jsonRPC     = jsonRPC
        self.cache       = jsonRPC.cache
        self.pool        = jsonRPC.pool
        self.LOGO_LOC    = LOGO_LOC
        self.logoSets    = self.buildLogoResources()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def buildLogoResources(self):
        self.log('buildLogoResources')#build all logo resources into dict. array.
        local_folder = [{"id":pack,"version":getInstanceID(),"items":self.walkDirectory(pack,checksum=getInstanceID())} for pack in [IMAGE_LOC,self.LOGO_LOC]]#LOGO_LOC

        user_pack = local_folder.copy()
        user_pack.extend([{"id":pack,"version":ADDON_VERSION,"items":self.walkResource(pack)} for pack in SETTINGS.getSetting('Resource_Logos').split('|')])
                
        show_pack = user_pack.copy()
        
        studios = ["resource.images.studios.white", "resource.images.studios.coloured"]
        if bool(SETTINGS.getSettingInt('Color_Logos')): studios.reverse()
        studios_pack = user_pack.copy()
        studios_pack.extend([{"id":pack,"version":self.jsonRPC.getPluginMeta(pack).get('version',ADDON_VERSION),"items":self.walkResource(pack)} for pack in studios])
        
        genres_pack = user_pack.copy()
        genres_pack.extend([{"id":pack,"version":self.jsonRPC.getPluginMeta(pack).get('version',ADDON_VERSION),"items":self.walkResource(pack)} for pack in ["resource.images.moviegenreicons.transparent"]])

        music_pack = user_pack.copy()
        music_pack.extend([{"id":pack,"version":self.jsonRPC.getPluginMeta(pack).get('version',ADDON_VERSION),"items":self.walkResource(pack)} for pack in ["resource.images.musicgenreicons.text"]])

        custom_pack = user_pack.copy() + studios_pack.copy() + genres_pack .copy()+ music_pack.copy()
        custom_pack = setDictLST(custom_pack)
        
        return {LANGUAGE(30002):{"label":"TV Networks"  ,"packs":studios_pack},
                LANGUAGE(30003):{"label":"TV Shows"     ,"packs":show_pack},
                LANGUAGE(30004):{"label":"TV Genres"    ,"packs":genres_pack},
                LANGUAGE(30005):{"label":"Movie Genres" ,"packs":genres_pack},
                LANGUAGE(30007):{"label":"Movie Studios","packs":studios_pack},
                LANGUAGE(30006):{"label":"Mixed Genres" ,"packs":genres_pack},
                LANGUAGE(30097):{"label":"Music Genres" ,"packs":music_pack},
                LANGUAGE(30026):{"label":"Recommended"  ,"packs":user_pack},
                LANGUAGE(30033):{"label":"Imports"      ,"packs":user_pack},
                LANGUAGE(30080):{"label":"Mixed"        ,"packs":user_pack},
                LANGUAGE(30320):{"label":"Local"        ,"packs":local_folder},
                LANGUAGE(30171):{"label":"Custom"       ,"packs":custom_pack}}


    def walkResource(self, id, exts=IMG_EXTS): #convert path from id to vfs, include version checksum 4 cache expiration
        return self.walkDirectory(os.path.join('special://home/addons/%s'%id,'resources'),exts,checksum=self.jsonRPC.getPluginMeta(id).get('version',ADDON_VERSION))


    def walkDirectory(self, path, exts=IMG_EXTS, checksum=ADDON_VERSION): #recursively walk all folders, parse xbt textures.
        def _parseXBT():
            resource = path.replace('/resources','').replace('special://home/addons/','resource://')
            walk.setdefault(resource,[]).extend(self.jsonRPC.getListDirectory(resource,checksum,expiration)[1])
            return walk
            
        walk = dict()
        path = path.replace('\\','/')
        self.log('walkDirectory, path = %s, exts = %s'%(path,exts))
        expiration  = datetime.timedelta(days=28)
        dirs, files = self.jsonRPC.getListDirectory(path,checksum,expiration)
        if    self.TEXTURES in files: return _parseXBT()
        else: walk.setdefault(path,[]).extend(list(filter(lambda f:f.endswith(tuple(exts)),files)))
        for dir in dirs: walk.update(self.walkDirectory(os.path.join(path, dir),exts,checksum))
        return walk
            
            
    def buildImagebase(self): #todo host/use kodi webserver to share image files for remote m3u/xmltv
        port     = 80
        username = 'kodi'
        password = ''
        secure   = False
        enabled  = True
        settings = (self.jsonRPC.getSetting('control','services') or [])
        for setting in settings:
            if setting['id'] == 'services.webserver' and not setting['value']:
                enabled = False
                break
            if setting['id'] == 'services.webserverusername':
                username = setting['value']
            elif setting['id'] == 'services.webserverport':
                port = setting['value']
            elif setting['id'] == 'services.webserverpassword':
                password = setting['value']
            elif setting['id'] == 'services.webserverssl' and setting['value']:
                secure = True
            username = '{0}:{1}@'.format(username, password) if username and password else ''
            
        if enabled:
            protocol = 'https' if secure else 'http'
            return '{0}://{1}localhost:{2}/image/'.format(protocol, username, port)
            # http://192.168.0.53:8080/image/image%3A%2F%2Fsmb%253a%252f%252f192.168.0.51%252fTV%252fCosmos%2520A%2520Space-Time%2520Odyssey%252fposter.jpg%2F
            
            
    def getNamePatterns(self, chname, type):
        return list(set([slugify(chname),slugify(stripRegion(chname)),chname,stripRegion(chname),splitYear(chname)[0],cleanChannelSuffix(chname, type)]))

        
    def cleanLogoPath(self, logo):
        if logo: #convert fs to kodi vfs.
            realPath = xbmcvfs.translatePath('special://home/addons/')
            if logo.startswith(realPath): #convert real path. to vfs
                logo = logo.replace(realPath,'special://home/addons/').replace('\\','/')
            return logo
               
               
    def findLogos(self, name, type=LANGUAGE(30171)): #channel manager search
        self.log('findLogos, chname = %s'%(name))
        def _match(dir, meta, chname):
            match = self.findFuzzyMatch(chname,meta.get(dir,[]),matchOne=False)
            if match: 
                return dir, match
        
        def _parse(pack, chname):
            meta = pack.get('items',{})
            for dir in meta.keys():
                results = _match(dir,meta,chname)
                if results: return pack.get('id'),results
                    
        chnames = self.getNamePatterns(name,type)
        packs   = self.logoSets.get(type,{}).get('packs',[])
        cacheName  = 'findLogos.%s.%s'%(name,type)
        cacheCHK   = getMD5(dumpJSON(packs))
        matches    = self.cache.get(cacheName, checksum=cacheCHK)
        if not matches:
            results = [self.pool.poolList(_parse,packs,kwargs={'chname':chname}) for chname in chnames]
            #results =  [[('resource.images.pseudotv.logos', ('special://home/addons/resource.images.pseudotv.logos/resources', [('Action Movies.png', 30), ('Action TV.png', 30), ('AMC Pictures.png', 30), ('Anonymous Content.png', 30), ('Biography Movies.png', 30)]))]]
            if results:
                matches = []
                results = sorted(results[0], key=lambda x: x[1][1]) #sort high-lowest match score.
                results.reverse()
                self.log('findLogos, found = %s'%(results))
                for result in results:
                    matches.extend([{'label':label,'label2':result[0],'path':os.path.join(result[1][0],label).replace('\\','/')} for label, val in result[1][1]])
                self.cache.set(cacheName, matches, checksum=cacheCHK, expiration=datetime.timedelta(days=28))
        return matches
            

    def findFuzzyMatch(self, chname, files, matchOne=True, THLD=90):
        try:
            if files:
                if matchOne: 
                    match = FuzzyProcess.extractOne(chname, files)
                    if match[1] >= THLD: return match
                else:  
                    fuzzy = FuzzyProcess.extract(chname, files)
                    match = [fuzz for fuzz in fuzzy if fuzz[1] >= THLD]
                    if match: return match        
        except Exception as e: 
            self.log("findFuzzyMatch, failed! %s"%(e), xbmc.LOGERROR)


    def fuzzyResource(self, chname, type):
        def cleanLogo(match):
            if isinstance(match,(list,tuple)):
                logo = os.path.join(match[0],match[1][0])
                return logo.replace('\\','/')
            
        def _match(pack):
            #pack = {'id': 'resource.images.studios.white', 'version': '0.0.28', 'items': {'special://home/addons/resource.images.studios.white/resources': ['#0.png']}}
            meta = pack.get('items',{})
            for dir in meta.keys():
                match = self.findFuzzyMatch(chname,meta.get(dir,[]))
                if match: return dir, match
                    
        packs      = self.logoSets.get(type,{}).get('packs',[])
        cacheName  = 'fuzzyResource.%s.%s'%(chname,type)
        cacheCHK   = getMD5(dumpJSON(packs))
        matches    = self.cache.get(cacheName, checksum=cacheCHK)
        if not matches:
            matches = self.pool.poolList(_match,packs)
            # matches = [('D:/Kodi/portable_data/addons/plugin.video.pseudotv.live/resources/images',('Recently Added.png', 95))]
            if matches:
                matches = (sorted(matches, key=lambda x: x[1][1])) #sort high-lowest match score.
                matches.reverse()
                matches = cleanLogo(matches[0])
                self.cache.set(cacheName, matches, checksum=cacheCHK, expiration=datetime.timedelta(days=28))
        return matches
        

    @cacheit()
    def parseLogo(self, chname, type):
        chnames = self.getNamePatterns(chname,type)
        for chname in chnames:
            logo = self.fuzzyResource(chname,type)
            if logo: return logo
        
          
    def chkResource(self, name, type):
        chnames = self.getNamePatterns(name,type)
        ids     = [pack.get('id') for pack in self.logoSets.get(type,{}).get('packs',[])]
        for chname in chnames:
            for id in ids:
                if not id.startswith('resource'): continue
                for ext in IMG_EXTS:
                    logo = 'resource://%s/%s%s'%(id,chname,ext)
                    if FileAccess.exists(logo):
                        self.log('chkResource: chname = %s, type = %s found = %s'%(name,type,logo))
                        return logo
        

    def chkTVShows(self, name):
        chnames = list(set([name,splitYear(name)[0]]))
        shows   = self.jsonRPC.getTVInfo().get('shows',[])
        for chname in chnames:
            for show in shows:
                if chname.lower() == show.get('label','').lower():
                    logo = show.get('logo')
                    if FileAccess.exists(unquoteImage(logo)):
                        return logo
        
        
    def chkLocal(self, chname):
        for path in [IMAGE_LOC,self.LOGO_LOC]:
            for ext in IMG_EXTS:
                logo = os.path.join(path,'%s%s'%(chname,ext))
                if FileAccess.exists(logo):
                    self.log('chkLocal: chname = %s found = %s'%(chname,logo))
                    return logo


    def chkItem(self, chname, item):
        logo = item.get('logo')
        if logo and logo != LOGO and not logo.startswith(self.LOGO_LOC):
            if FileAccess.exists(unquoteImage(logo)): 
                return logo


    def getLogo(self, chname, type=LANGUAGE(30171), path='', item={}, featured=False, lookup=False):
        self.log('getLogo: chname = %s, type = %s, featured = %s'%(chname,type,featured)) 
        def cleanLogo(logo):
            return self.cleanLogoPath(logo.replace('\\','/'))
            
        logo = self.chkLocal(chname)
        if not logo:
            logo = self.chkItem(chname, item)
            if not logo:
                logo = self.chkTVShows(chname)
                if not logo:
                    logo = self.chkResource(chname, type)
                    if not logo and lookup: #parse all resources for match using channel name variations.
                        logo = self.parseLogo(chname, type)
                        
        if logo: 
            logo = cleanLogo(logo)
            self.log('getLogo: found %s'%(logo))
            return logo
        return LOGO