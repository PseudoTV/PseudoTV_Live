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
    def __init__(self, jsonRPC=None):
        log('Library: __init__')
        if jsonRPC is None:
            from resources.lib.jsonrpc import JSONRPC
            self.jsonRPC  = JSONRPC()
        else:
            self.jsonRPC  = jsonRPC
            
        self.cache    = self.jsonRPC.cache
        self.pool     = PoolHelper()
        self.logoSets = self.buildLogoResources()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def buildLogoResources(self):
        self.log('buildLogoResources')
        logos     = []
        packs     = (getSetting('Resource_Logos')).split(',')
        radios    = ["resource.images.musicgenreicons.text"]
        genres    = ["resource.images.moviegenreicons.transparent"]
        studios   = ["resource.images.studios.white", 
                     "resource.images.studios.coloured"]
        if bool(getSettingInt('Color_Logos')): studios.reverse()
        
        [logos.append({'type':[LANGUAGE(30171)],                                                'path':'resource://%s'%(pack)  ,'files': self.getResourceFiles(pack)})   for pack   in packs]
        [logos.append({'type':[LANGUAGE(30097),LANGUAGE(30171)],                                'path':'resource://%s'%(radio) ,'files': self.getResourceFiles(radio)})  for radio  in radios]
        [logos.append({'type':[LANGUAGE(30004),LANGUAGE(30005),LANGUAGE(30006),LANGUAGE(30171)],'path':'resource://%s'%(genre) ,'files': self.getResourceFiles(genre)})  for genre  in genres]
        [logos.append({'type':[LANGUAGE(30002),LANGUAGE(30007),LANGUAGE(30171)],                'path':'resource://%s'%(studio),'files': self.getResourceFiles(studio)}) for studio in studios]
        logos.append( {'type':[LANGUAGE(30003),LANGUAGE(30171)],                                'path':''                      ,'files': self.jsonRPC.getTVshows()}) #tvshow meta
        logos.append( {'type':[LANGUAGE(30026),LANGUAGE(30033),LANGUAGE(30171)],                'path':''                      ,'files': self.jsonRPC.getAddons()})  #addon meta
        # logos.append( {'type':[LANGUAGE(30004),LANGUAGE(30005),LANGUAGE(30006),LANGUAGE(30171)],'path':IMAGE_LOC,'files': self.jsonRPC.getListDirectory(IMAGE_LOC,ADDON_VERSION)[1]}) #default image folder
        return logos


    def getResourceFiles(self, resource):
        self.log('getResourceFiles, resource = %s'%(resource))
        addonMeta = self.jsonRPC.getPluginMeta(resource)
        if not resource.startswith('resource://'): resource = 'resource://%s'%(resource)
        return self.jsonRPC.getListDirectory(resource,addonMeta.get('version',''))[1]

  
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


    def cleanLogoPath(self, logo=''):
        #todo procs. image, alpha, cache, etc...
        if logo is None: return logo
        realPath = xbmc.translatePath('special://home/addons/')
        if logo.startswith(realPath):
            return logo.replace(realPath,'special://home/addons/').replace('\\','/')
        return logo
               
                
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

        
    def getFilePatterns(self, name):
        patterns = [] #todo add regex to ignore wildcards ie. NBC (US), NBC_1
        for ext in LOGO_EXTS: 
            patterns.extend(['%s%s'%(name,ext),
                             '%s%s'%(name.lower(),ext),
                             '%s%s'%(slugify(name),ext),
                             '%s%s'%(slugify(name.lower()),ext)])
        return patterns


    def parseDirectory(self, path, name, patterns=None):
        if patterns is None: patterns = self.getFilePatterns(name)
        dirs, files = self.jsonRPC.getListDirectory(path,ADDON_VERSION)
        for pattern in patterns:
            for file in files:
                if file == pattern:
                    return self.cleanLogoPath(os.path.join(path,pattern))
            for dir in dirs:
                if dir == os.path.splitext(pattern)[0]:
                    return self.chkDirectory4Logo(dir,name,patterns)
        return None

        
    def chkLocalLogo(self, pattern):
        paths = [IMAGE_LOC, LOGO_LOC]
        for path in paths:
            filePath = os.path.join(path,pattern)
            if FileAccess.exists(filePath): 
                return self.cleanLogoPath(filePath)
        return None
        
        
    def findResourceLogo(self, data):
        item, data = data
        name, type = data
        if type in item['type']:
            for file in item['files']:
                if isinstance(file, dict): #jsonrpc item
                    if name.lower() == (file.get('showtitle','').lower() or file.get('label','').lower() or file.get('name','').lower() or file.get('title','').lower()):
                        channellogo = (file.get('art',file).get('clearlogo','') or file.get('thumbnail',''))
                        if channellogo: return channellogo
                else: #resource item
                    if os.path.splitext(file.lower())[0] == name.lower():
                        return os.path.join(item['path'],file)
        return None
        
    
    def getLogo(self, name, type=LANGUAGE(30171), path=None, item=None, featured=False): 
        if type == LANGUAGE(30003): name, year = splitYear(name) #TV Show
        log('getLogo: name = %s, type = %s'%(name,type))
        
        #local
        local = (self.pool.poolList(self.chkLocalLogo,self.getFilePatterns(name)))
        if local: return self.cleanLogoPath(local[0])
        
        #resources
        if ' (' in name: #todo prop regex to fix region in name NBC (US), lazy fix needs re.match
            name = name.split(' (')[0]
        rlogo = (self.pool.poolList(self.findResourceLogo,self.logoSets,(name,type)))
        if rlogo: return self.cleanLogoPath(rlogo[0])
        
        if item is not None:
            art  = (item.get('art','') or item)
            logo = (art.get('clearlogo','') or art.get('logo','') or art.get('icon',''))
            if logo: return self.cleanLogoPath(logo)
            
        if path is not None:
            if isinstance(path, list) and len(path) > 0: path = path[0]
            if path.startswith('plugin://'): return self.cleanLogoPath(self.jsonRPC.getPluginMeta(path).get('icon',''))
        # if featured: logo = self.chkMono(logo)
        return LOGO
        
    
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
        

    def chkMono(self, logo):
        try:
            dest = os.path.join(LOGO_MONO_LOC,'w%s'%(os.path.split(xbmcvfs.translatePath(logo))[1]))
            if FileAccess.exists(dest): return dest
            return self.monoConvert(logo,dest,bool(getSettingInt('Color_Logos')))
        except Exception as e: self.log("chkMono, failed! " + str(e), xbmc.LOGERROR)
        return logo
            

    def monoConvert(self, logo, dest, useColor=bool(getSettingInt('Color_Logos'))):
        return logo
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