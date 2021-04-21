#   Copyright (C) 2021 Lunatixz
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

try:
    from PIL                   import Image, ImageStat
    hasPillow = True
except:
    hasPillow = False

class Resources:
    IMG_EXTS = ['.png','.jpg','.gif']

    def __init__(self, jsonRPC):
        self.log('__init__')
        self.jsonRPC  = jsonRPC
        self.cache    = self.jsonRPC.cache
        self.pool     = self.jsonRPC.pool
        self.logoSets = self.buildLogoResources()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def buildLogoResources(self):
        self.log('buildLogoResources')#Collect all logo resources into dict. array. #todo refactor this approach. 
        logos     = []
        packs     = (SETTINGS.getSetting('Resource_Logos')).split(',')
        radios    = ["resource.images.musicgenreicons.text"]
        genres    = ["resource.images.moviegenreicons.transparent"]
        studios   = ["resource.images.studios.white", 
                     "resource.images.studios.coloured"]
        if bool(SETTINGS.getSettingInt('Color_Logos')): studios.reverse()
        
        [logos.append({'type':[LANGUAGE(30003),LANGUAGE(30007),LANGUAGE(30171),
                               LANGUAGE(30026),LANGUAGE(30033),LANGUAGE(30002),
                               LANGUAGE(30004),LANGUAGE(30005),LANGUAGE(30006),LANGUAGE(30097)],'path':'resource://%s'%(pack)  ,'files': self.getResourceFiles(pack)})   for pack   in packs]
        [logos.append({'type':[LANGUAGE(30097),LANGUAGE(30171)],                                'path':'resource://%s'%(radio) ,'files': self.getResourceFiles(radio)})  for radio  in radios]
        [logos.append({'type':[LANGUAGE(30004),LANGUAGE(30005),LANGUAGE(30006),LANGUAGE(30171)],'path':'resource://%s'%(genre) ,'files': self.getResourceFiles(genre)})  for genre  in genres]
        [logos.append({'type':[LANGUAGE(30002),LANGUAGE(30007),LANGUAGE(30171)],                'path':'resource://%s'%(studio),'files': self.getResourceFiles(studio)}) for studio in studios]
        return logos


    def getResourceFiles(self, resource):
        self.log('getResourceFiles, resource = %s'%(resource))
        if not resource.startswith('resource://'): resource = 'resource://%s'%(resource)
        return self.jsonRPC.getListDirectory(resource,version=self.jsonRPC.getPluginMeta(resource).get('version',ADDON_VERSION))[1]

  
    def getNamePatterns(self, chname, type):
        patterns = list(set([chname,stripRegion(chname),splitYear(chname)[0],cleanChannelSuffix(chname, type),slugify(chname)]))#,stripNumber(chname),stripNumber(stripRegion(chname))]
        patterns = ['%s%s'%(pattern,ext) for ext in self.IMG_EXTS for pattern in patterns]
        return patterns


    def cleanLogoPath(self, logo=''):
        if logo is None: return logo
        realPath = xbmcvfs.translatePath('special://home/addons/')
        if logo.startswith(realPath): #convert real path. to vfs
            logo = logo.replace(realPath,'special://home/addons/').replace('\\','/')
        return logo
               
               
    def chkLocalLogo(self, chname, type): ## CHK user folder, Plugin folder
        def matchPattern(item):
            for pattern in patterns:
                if item.lower() == pattern.lower():
                    return self.cleanLogoPath(os.path.join(path,item))
                
        paths    = [LOGO_LOC,IMAGE_LOC]
        patterns = self.getNamePatterns(chname,type)
        for path in paths:
            results = self.pool.poolList(matchPattern,self.jsonRPC.getListDirectory(path)[1])
            if len(results) > 0: 
                self.log('chkLocalLogo, found = %s'%(results[0]))
                return results[0]
               
               
    def findResourceLogo(self, chname, type):
        def chkFile(file):
            if isinstance(file, dict): #file item
                if chname.lower() == (file.get('showtitle','') or file.get('label','') or file.get('name','') or file.get('title','')).lower():
                    art  = (file.get('art','') or file)
                    logo = (art.get('clearlogo','') or art.get('thumbnail',''))
                    if logo: return self.cleanLogoPath(logo)
            else: #resource item
                for pattern in patterns:
                    if pattern.lower() == file.lower():
                        return self.cleanLogoPath(os.path.join(item['path'],file))
                
        patterns = self.getNamePatterns(chname,type)
        for item in self.logoSets:
            if type in item['type']:
                results = self.pool.poolList(chkFile,item.get('files',[]))
                if len(results) > 0:
                    self.log('findResourceLogo, found = %s'%(results[0]))
                    return results[0]
            
            
    def findTVLogo(self, chname, art='clearlogo'):
        self.log('findTVLogo: chname = %s'%(chname))
        def findMatch(item):
            for pattern in patterns:
                if item.get('label','').lower() == pattern.lower():
                    return self.cleanLogoPath(item.get('art',{}).get(art,''))
        
        items    = self.jsonRPC.getTVshows()
        patterns = [chname, splitYear(chname)[0]]
        results  = self.pool.poolList(findMatch,items)
        if len(results) > 0:
            self.log('findTVLogo, found = %s'%(results[0]))
            return results[0]
        
        
    @cacheit(expiration=datetime.timedelta(minutes=15),json_data=False) #cache long enough for duplicate run-throughs. Should be fresh data, not cached. 
    def getLogo(self, name, type=LANGUAGE(30171), path=None, item=None, featured=False): 
        self.log('getLogo: name = %s, type = %s'%(name,type))
        ##local
        local = self.chkLocalLogo(name, type)
        if local: return local
            
        #fileitem
        if item is not None:
            #todo check if item art is a default fallback LOGO, COLOR_LOGO, ETC and ignore
            art  = (item.get('art','') or item)
            logo = (art.get('clearlogo','') or art.get('logo','') or art.get('icon',''))
            if logo: return self.cleanLogoPath(logo)
            
        #plugin meta
        if path is not None:
            if isinstance(path, list) and len(path) > 0: path = path[0]
            if path.startswith('plugin://'): return self.cleanLogoPath(self.jsonRPC.getPluginMeta(path).get('icon',''))
            #todo parse vfs for logo
            
        if type == LANGUAGE(30003): #TV Show
            tvlogo = self.findTVLogo(name)
            if tvlogo: return tvlogo
        else: #resources
            rlogo = self.findResourceLogo(name,type)
            if rlogo: return rlogo
            
        return LOGO
        
        
    def buildBCTresource(self, type, path, media='video'):
        self.log('buildBCTresource, type = %s, path = %s, media = %s'%(type,path,media))
        if path.startswith(('resource://')):
            version = self.jsonRPC.getPluginMeta(path).get('version',ADDON_VERSION)
        else: 
            version = ADDON_VERSION
        if type in PRE_ROLL: 
            force = True
        else: 
            force = False
        return self.jsonRPC.listVFS(cleanResourcePath(path),media,force,version)


    def buildResourceType(self, type, paths):
        for resource in paths:
            yield self.getPlayablePaths(type,resource)
        
        
    def getPlayablePaths(self, type, resource):
        self.log('getPlayablePaths, type = %s, resource = %s'%(type,resource))
        if not resource.startswith('resource://'): resource = 'resource://%s'%(resource)
        tmpdict = dict()
        items   = list(self.buildBCTresource(type, resource))
        for item in items:
            folder = os.path.basename(os.path.normpath(item.get('path','')))
            if folder and folder != 'resources': 
                tmpdict.setdefault(folder.lower(),[]).append(item)
            else:
                if type == "ratings":
                    tmpdict.setdefault(os.path.splitext(item.get('label'))[0].lower(),{}).update(item)
                else:
                    tmpdict.setdefault('root',[]).append(item)
        return tmpdict


                
        # elif logo.startswith('resource://'):
            # path, file = os.path.split(logo)
            # return path.replace('resource:\\','special://home/addons/') + '/resources/%s'%(file)
        # if logo.startswith(ADDON_PATH):
            # logo = logo.replace(ADDON_PATH,'special://home/addons/%s/'%(ADDON_ID)).replace('\\','/')
        # if featured:
            # localIcon = os.path.join(LOGO_LOC,'%s.png'%(channelname))
            # if logo.startswith('resource://'): return logo #todo parse xbt and extract image?
            # # if FileAccess.copy(logo, localIcon): return localIcon
        # return logo


    def parseDirectory(self, path, name, patterns=None):
        if patterns is None: patterns = self.getNamePatterns(name)
        dirs, files = self.jsonRPC.getListDirectory(path)
        for pattern in patterns:
            for file in files:
                if file == pattern:
                    return self.cleanLogoPath(os.path.join(path,pattern))
            for dir in dirs:
                if dir == os.path.splitext(pattern)[0]:
                    return self.chkDirectory4Logo(dir,name,patterns)
        return None

    
    # def buildLocalTrailers(self, path=None, items=[]):
        # self.log('buildLocalTrailers, path = %s, items = %s'%(path,len(items)))
        # if path is None and len(items) > 0:
            # return [{'label':item.get('label',''),'duration':self.parseDuration(item.get('trailer',''),item),'file'}]
        # list(filter(lambda item:(,item.get('trailer')), validItems))
# # os.path.splitext(os.path.basename(item.get('file')))[0]

     # def buildResourcePath(self, path, file):
        # if path.startswith('resource://'):
            # path = path.replace('resource://','special://home/addons/') + '/resources/%s'%(file)
        # else: 
            # path = os.path.join(path,file)
        # return path
        
    # resourceMap = {'path':path,'files':files,'dirs':dirs,'filepaths':files}
    # resourceMap = {'path':path,'files':files,'dirs':dirs,'filepaths':[self.buildResourcePath(path,file) for file in files]}
        

    # def chkMono(self, logo):
        # try:
            # dest = os.path.join(LOGO_MONO_LOC,'w%s'%(os.path.split(xbmcvfs.translatePath(logo))[1]))
            # if FileAccess.exists(dest): return dest
            # return self.monoConvert(logo,dest,bool(SETTINGS.getSettingInt('Color_Logos')))
        # except Exception as e: self.log("chkMono, failed! " + str(e), xbmc.LOGERROR)
        # return logo
            

    # def monoConvert(self, logo, dest, useColor=bool(SETTINGS.getSettingInt('Color_Logos'))):
        # return logo
        # self.log('monoConvert, logo = %s, dest = %s'%(logo,dest)) #detect if logo is color and if preference is mono, covert to mono.
        # pil_img = Image.open(FileAccess.translatePath(logo))
        # # pil_img = Image.open(FileAccess.open(logo,"r"))
        # def isColor(adjust_color_bias=True):
            # bands = pil_img.getbands()
            # if bands == ('R','G','B') or bands== ('R','G','B','A'):
                # thumb = pil_img.resize((40,40))
                # SSE, bias = 0, [0,0,0]
                # if adjust_color_bias:
                    # bias = ImageStat.Stat(thumb).mean[:3]
                    # bias = [b - sum(bias)/3 for b in bias ]
                # for pixel in thumb.getdata():
                    # mu = sum(pixel)/3
                    # SSE += sum((pixel[i] - mu - bias[i])*(pixel[i] - mu - bias[i]) for i in [0,1,2])
                # MSE = float(SSE)/(40*40)
                # if MSE <= 22: return False #grayscale
                # else: return True#Color
            # elif len(bands)==1: return False #Mono"
            # else: return True #Undetermined
            
        # if not hasPillow: return logo
        # if isColor(logo) and useColor:
            # img_bright = ImageEnhance.Brightness(pil_img.convert('LA'))
            # converted_img = img_bright.enhance(2.0)
            # converted_img.save(dest)
            # return dest
        # return logo