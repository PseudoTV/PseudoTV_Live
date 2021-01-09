#   Copyright (C) 2020 Lunatixz
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
    def __init__(self, cache=None, jsonRPC=None):
        log('Library: __init__')
        if cache is None:
            self.cache = SimpleCache()
        else: 
            self.cache = cache
                
        if jsonRPC is None:
            from resources.lib.jsonrpc import JSONRPC
            self.jsonRPC  = JSONRPC(self.cache)
        else:
            self.jsonRPC  = jsonRPC
            
        self.logoSets = self.buildLogoResources()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def buildLogoResources(self):
        self.log('buildLogoResources')
        logos     = []
        packs     = []#todo user selected resource packs
        radios    = ["resource://resource.images.musicgenreicons.text"]
        genres    = ["resource://resource.images.moviegenreicons.transparent"]
        studios   = ["resource://resource.images.studios.white/", 
                     "resource://resource.images.studios.coloured/"]
                     
        if bool(getSettingInt('Color_Logos')): studios.reverse()
        [logos.append({'type':[LANGUAGE(30171)],                                                'path':pack     ,'files': self.jsonRPC.getListDirectory(pack , self.jsonRPC.getPluginMeta(pack).get('version',''))[1]})   for pack   in packs]
        [logos.append({'type':[LANGUAGE(30097)],                                                'path':radio    ,'files': self.jsonRPC.getListDirectory(radio, self.jsonRPC.getPluginMeta(radio).get('version',''))[1]})  for radio  in radios]
        [logos.append({'type':[LANGUAGE(30004),LANGUAGE(30005),LANGUAGE(30006),LANGUAGE(30171)],'path':genre    ,'files': self.jsonRPC.getListDirectory(genre, self.jsonRPC.getPluginMeta(genre).get('version',''))[1]})  for genre  in genres]
        [logos.append({'type':[LANGUAGE(30002),LANGUAGE(30007),LANGUAGE(30171)],                'path':studio   ,'files': self.jsonRPC.getListDirectory(studio,self.jsonRPC.getPluginMeta(studio).get('version',''))[1]}) for studio in studios]
        logos.append( {'type':[LANGUAGE(30003),LANGUAGE(30171)],                                'path':''       ,'files': self.jsonRPC.getTVshows()}) #tvshow meta
        logos.append( {'type':[LANGUAGE(30026),LANGUAGE(30033),LANGUAGE(30171)],                'path':''       ,'files': self.jsonRPC.getAddons()})  #addon meta
        # logos.append( {'type':[LANGUAGE(30004),LANGUAGE(30005),LANGUAGE(30006),LANGUAGE(30171)],'path':IMAGE_LOC,'files': self.jsonRPC.getListDirectory(IMAGE_LOC,ADDON_VERSION)[1]}) #default image folder
        return logos


    def cleanLogoPath(self, logo=''):
        #todo procs. image, alpha, cache, etc...
        if logo is None: return logo
        if logo.startswith(ADDON_PATH):
            return logo.replace(ADDON_PATH,'special://home/addons/%s/'%(ADDON_ID)).replace('\\','/')
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
                             '%s%s'%(slugify(name),ext),
                             '%s%s'%(name.lower(),ext),
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

        
    def chkLocalLogo(self, name, featured=False):
        paths    = [IMAGE_LOC,LOGO_LOC]
        patterns = self.getFilePatterns(name)
        for pattern in patterns:
            for path in paths:
                filePath = os.path.join(path,pattern)
                if FileAccess.exists(filePath): 
                    return self.cleanLogoPath(filePath)
        return None
        
    
    def chkMono(self, logo):
        dest = os.path.join(LOGO_MONO_LOC,'w%s'%(os.path.split(os.path.abspath(logo))[1]))
        if FileAccess.exists(dest): return dest
        return self.monoConvert(logo,dest,bool(getSettingInt('Color_Logos')))
    

    def getLogo(self, name, type=LANGUAGE(30171), path=None, item=None, featured=False): 
        #featured == channel found in channels.json ie. in-use channel. Switch to handle image procs. and other additional features.
        if type == LANGUAGE(30003): name, year = splitYear(name) #TV Show
        log('getLogo: name = %s, type = %s'%(name,type))
        local = self.chkLocalLogo(name, featured)#before parse check for user logos.
        if local: return local
        
        name = cleanChannelPostfix(name,type)
        logo = self.findResourceLogo(name, type, ADDON_VERSION)#parse for logo
        if not logo and path: #find fallbacks, parse path, parse listitem
            if isinstance(path, list) and len(path) > 0: path = path[0]
            if path and path.startswith('plugin://'):
                logo = self.jsonRPC.getPluginMeta(path).get('icon','')
        if not logo and item:
            art  = item.get('art',item)
            logo = (art.get('logo','') or art.get('icon','') or art.get('clearlogo',''))
        logo = self.cleanLogoPath(logo)
        if featured: logo = self.chkMono(logo)
        return (logo or LOGO)
        
        
    @use_cache(7)
    def findResourceLogo(self, name, type, version=ADDON_VERSION):
        log('findResourceLogo')
        for item in self.logoSets:
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
        
            
    
    # def buildLocalTrailers(self, path=None, items=[]):
        # self.log('buildLocalTrailers, path = %s, items = %s'%(path,len(items)))
        # if path is None and len(items) > 0:
            # return [{'label':item.get('label',''),'duration':self.parseDuration(item.get('trailer','')),'file'}]
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
        

    def buildBCTresource(self, path):
        resourceMap = {}
        self.log('buildBCTresource, path = %s'%(path))
        if path.startswith(('resource://','plugin://')): 
            version = self.jsonRPC.getPluginMeta(path).get('version',ADDON_VERSION)
        else: 
            version = ADDON_VERSION
        if path.startswith('resource://'):
            dirs, files = self.jsonRPC.getListDirectory(path,version)
        else:
            dirs, files = self.jsonRPC.listVFS(path,version)
        return dirs, files
        
  
    @use_cache(7)
    def monoConvert(self, logo, dest, useColor=bool(getSettingInt('Color_Logos'))):
        return logo
        # self.log('monoConvert, logo = %s, dest = %s'%(logo,dest)) #detect if logo is color and if preference is mono, covert to mono.
        # pil_img = Image.open(xbmcvfs.translatePath(logo))
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