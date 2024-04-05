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
from resources  import Resources
           
#Ratings  - resource only, Movie Type only any channel type
#Bumpers  - plugin, path only, tv type, tv network, custom channel type
#Adverts  - plugin, path only, tv type, any tv channel type
#Trailers - plug, path only, movie type, any movie channel.

class Fillers:
    def __init__(self, builder):
        self.builder    = builder
        self.cache      = builder.cache
        self.jsonRPC    = builder.jsonRPC
        self.runActions = builder.runActions
        self.resources  = Resources(self.jsonRPC,self.cache)
        self.bctTypes   = {"ratings"  :{"max":1                 ,"auto":builder.incRatings == 1,"enabled":bool(builder.incRatings),"sources":builder.srcRatings,"items":{}},
                           "bumpers"  :{"max":1                 ,"auto":builder.incBumpers == 1,"enabled":bool(builder.incBumpers),"sources":builder.srcBumpers,"items":{}},
                           "adverts"  :{"max":builder.incAdverts,"auto":builder.incAdverts == 1,"enabled":bool(builder.incAdverts),"sources":builder.srcAdverts,"items":{}},
                           "trailers" :{"max":builder.incTrailer,"auto":builder.incTrailer == 1,"enabled":bool(builder.incTrailer),"sources":builder.srcTrailer,"items":{}}}
        self.fillSources()
        print('bctTypes',self.bctTypes)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def fillSources(self):
        for ftype, values in self.bctTypes.items():
            for id in values.get("sources",{}).get("resource",[]): values['items'].update(self.buildSource(ftype,id))   #parse resource packs
            for path in values.get("sources",{}).get("paths",[]):  values['items'].update(self.buildSource(ftype,path)) #parse vfs paths
                
                
    def buildTrailers(self, fileList):
        tmpLST = {}
        for fileItem in fileList:
            if fileItem.get('trailer') and not fileItem.get('trailer','').startswith(('http','upnp','ftp')):
                dur = self.jsonRPC.getDuration(fileItem.get('trailer'), accurate=True)
                if dur == 0: continuex
                for key in (fileItem.get('genre',[]) or ['resources']):
                    tmpDCT.setdefault(key.lower(),[]).append((fileItem.get('trailer'),dur,fileItem))
        for k, v in tmpLST.items(): self.bctTypes['trailers']['items'].setdefault(k,[]).extend(v)
          
          
    @cacheit(expiration=datetime.timedelta(minutes=15),json_data=False)
    def buildSource(self, ftype, path):
        self.log('buildSource, type = %s, path = %s'%(ftype, path))
        def _parseResource(path):
            if not hasAddon(path, install=True): return {}
            return self.resources.walkResource(path,exts=VIDEO_EXTS)
                
        def _parseVFS(path):
            tmpDCT = {}
            if hasAddon(path, install=True):
                for url, fileItems in self.jsonRPC.walkFileDirectory(path,append_items=True).items():
                    for fileItem in fileItems:
                        if fileItem.get('runtime',0) == 0: continue
                        for key in (fileItem.get('genre',[]) or ['resources']): 
                            tmpDCT.setdefault(key.lower(),[]).append((fileItem.get('file'),fileItem.get('runtime'),fileItem))
            return tmpDCT
            
        def _parseLocal(path):
            tmpDCT = {}
            print('_parseLocal',self.jsonRPC.walkListDirectory(path,append_path=True))
            # dirs, files = self.jsonRPC.walkListDirectory(path,append_path=True)
            # for idx, dir in enumerate(dirs):
                # for file in files[idx]
                # tmpDCT.setdefault(os.path.basename(dir).lower(),[]).append([ for file in])
                
            
            # dur = self.jsonRPC.getDuration(item.get('file'),item, accurate=True)
            # tmpDCT.setdefault('resources',[]).append([(item.get('file'),item.get('runtime')) for item in items if item.get('runtime',0) > 0])
            return tmpDCT

        def _rating(data):
            tmpDCT = {}
            for path, files in data.items():
                for file in files:
                    dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                    if dur > 0: tmpDCT.setdefault(file.split('.')[0],[]).append((os.path.join(path,file),dur,{})) #{'PG-13':[('PG-13.mkv',7)]}
            return tmpDCT
            
        def _bumper(data):
            tmpDCT = {}
            for path, files in data.items():
                for file in files:
                    dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                    if dur > 0: tmpDCT.setdefault(os.path.basename(path).lower(),[]).append((os.path.join(path,file),dur,{}))
            return tmpDCT
                
        def _advert(data):
            tmpDCT = {}
            for path, files in data.items():
                for file in files:
                    dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                    if dur > 0: tmpDCT.setdefault(os.path.basename(path).lower(),[]).append((os.path.join(path,file),dur,{}))
            return tmpDCT
            
        def _trailer(data):
            tmpDCT = {}
            for path, files in data.items():
                for file in files:
                    dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                    if dur > 0: tmpDCT.setdefault(os.path.basename(path).lower(),[]).append((os.path.join(path,file),dur,{}))
            return tmpDCT
            
        if   path.startswith('plugin://'): return _parseVFS(path)
        if   ftype == 'ratings':  return _rating(_parseResource(path))
        elif ftype == 'bumpers':  return _bumper(_parseResource(path))
        elif ftype == 'adverts':  return _advert(_parseResource(path))
        elif ftype == 'trailers': return _trailer(_parseResource(path))
        return {}
        
        
    def convertMPAA(self, ompaa):
        tmpLST = ompaa.split(' / ')
        tmpLST.append(ompaa.upper())
        try:    mpaa = re.compile(":(.*?)/", re.IGNORECASE).search(ompaa.upper()).group(1).strip()
        except: mpaa = ompaa.upper()
        #https://www.spherex.com/tv-ratings-vs-movie-ratings, #https://www.spherex.com/which-is-more-regulated-film-or-tv
        mpaa = mpaa.replace('TV-Y','G').replace('TV-Y7','G').replace('TV-G','G').replace('NA','NR').replace('TV-PG','PG').replace('TV-14','PG-13').replace('TV-MA','R')
        tmpLST.append(mpaa)
        return mpaa, tmpLST


    def cleanFillers(self, fillLST):
        tmpLST = []
        for i in fillLST:
            if (i[0], i[1], i[2]) not in tmpLST: tmpLST.append(i)
        return tmpLST


    def getRating(self, keys=[]):
        try:
            tmpLST = []
            for key in keys: tmpLST.extend(self.bctTypes['ratings'].get('items',{}).get(key,[]))
            return random.choice(tmpLST)
        except: return None, 0 ,{}
        

    def getBumper(self, keys=['resources']):
        try:
            tmpLST = []
            for key in keys: tmpLST.extend(self.bctTypes['bumpers'].get('items',{}).get(key.lower(),[]))
            return random.choice(tmpLST)
        except: return None, 0 ,{}
    

    def getAdverts(self, keys=['resources'], count=1):
        try:
            tmpLST = []
            for key in keys: tmpLST.extend(self.bctTypes['adverts'].get('items',{}).get(key.lower(),[]))
            return self.cleanFillers(random.choices(tmpLST,k=count))
        except: return [(None, 0 ,{})]
    

    def getTrailers(self, keys=['resources'], count=1):
        try:
            tmpLST = []
            for key in keys: tmpLST.extend(self.bctTypes['trailers'].get('items',{}).get(key.lower(),[]))
            return self.cleanFillers(random.choices(tmpLST,k=count))
        except: return [(None, 0 ,{})]


    def injectBCTs(self, citem, fileList):
        nfileList = []
        if self.bctTypes['trailers']['enabled'] and SETTINGS.getSettingInt('Include_Trailers') < 2:
            if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Parsing Kodi for Trailers...',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
            if len(fileList) > 0: self.buildTrailers(fileList)
            
        for idx, fileItem in enumerate(fileList):
            if not fileItem: continue
            elif self.builder.service._interrupt() or self.builder.service._suspend(): break
            else:
                runtime = fileItem.get('duration',0)
                if runtime == 0: continue
                
                chtype  = citem.get('type','')
                chname  = citem.get('name','')
                fitem   = fileItem.copy()
                ftype   = fileItem.get('type','')
                fgenre  = fileItem.get('genre',citem.get('group',['']))[0]

                #pre roll - bumpers
                if self.bctTypes['bumpers']['enabled']:
                    # #todo movie bumpers for audio/video codecs? imax bumpers?
                    if ftype.startswith(tuple(TV_TYPES)):
                        if chtype in ['Playlists','TV Networks','TV Genres','Mixed Genres','Custom']:
                            bkeys = ['resources',chname, fgenre] if chanceBool(SETTINGS.getSettingInt('Random_Bumper_Chance')) else [chname, fgenre]
                            file, dur, oitem = self.getBumper(bkeys)
                            if file:
                                runtime += dur
                                self.log('injectBCTs, adding bumper %s - %s'%(file,dur))
                                if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Injecting Filler: Bumpers',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                item = {'title':'%s (%s)'%(fitem.get('showlabel'),chname),'episodetitle':oitem.get('label',oitem.get('title','Bumper')),'genre':['Bumpers'],'plot':fitem.get('plot',file),'path':file}
                                nfileList.append(self.builder.buildCells(citem,dur,entries=1,info=item)[0])
                
                #pre roll - ratings
                if self.bctTypes['ratings']['enabled']:
                    if ftype.startswith(tuple(MOVIE_TYPES)):
                        mpaa, rkeys = self.convertMPAA(fileItem.get('mpaa','NR'))
                        file, dur, oitem = self.getRating(rkeys)
                        if file:
                            runtime += dur
                            self.log('injectBCTs, adding rating %s - %s'%(file,dur))
                            if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Injecting Filler: Ratings',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                            item = {'title':'%s (%s)'%(fitem.get('showlabel'),mpaa),'episodetitle':oitem.get('label',oitem.get('title','Rating')),'genre':['Ratings'],'plot':fitem.get('plot',file),'path':file}
                            nfileList.append(self.builder.buildCells(citem,dur,entries=1,info=item)[0])
                            
                # original media
                nfileList.append(fileItem)
                
                # post roll - commercials
                pfileList    = []
                pfillRuntime = roundRuntimeUP(runtime)
                pchance      = (chanceBool(SETTINGS.getSettingInt('Random_Advert_Chance')) | chanceBool(SETTINGS.getSettingInt('Random_Trailers_Chance')))
                
                self.log('injectBCTs, post roll current runtime %s, available runtime %s'%(runtime, pfillRuntime))
                if self.bctTypes['adverts']['enabled']:
                    acnt = PAGE_LIMIT if self.bctTypes['adverts']['auto'] else self.bctTypes['adverts']['max']
                    afillRuntime = (pfillRuntime // 2) if self.bctTypes['trailers']['enabled'] else pfillRuntime #if trailers enabled only fill half the required space, leaving room for trailers.  
                    pfillRuntime -= afillRuntime
                    self.log('injectBCTs, advert fill runtime %s'%(afillRuntime))
                    if chtype in ['Playlists','TV Networks','TV Genres','Mixed Genres','Custom']:
                        akeys = ['resources',chname, fgenre] if pchance else [chname, fgenre]
                        for file, dur, oitem in self.getAdverts(akeys, acnt):
                            if file:
                                if afillRuntime <= 0: break
                                afillRuntime -= dur
                                self.log('injectBCTs, adding advert %s - %s'%(file,dur))
                                if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Injecting Filler: Adverts',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                item = {'title':'Advert','episodetitle':oitem.get('label',oitem.get('title','%s (%s)'%(chname,fgenre))),'genre':['Adverts'],'plot':oitem.get('plot',file),'path':file}
                                pfileList.append(self.builder.buildCells(citem,dur,entries=1,info=item)[0])
                            
                # post roll - trailers
                if self.bctTypes['trailers']['enabled']:
                    self.log('injectBCTs, trailers fill runtime %s'%(pfillRuntime))
                    tcnt = PAGE_LIMIT if self.bctTypes['trailers']['auto'] else self.bctTypes['trailers']['max']
                    self.log('injectBCTs, trailers fill runtime %s'%(pfillRuntime))
                    if chtype in ['Playlists','TV Networks','TV Genres','Movie Genres','Movie Studios','Mixed Genres','Custom']:
                        tkeys = ['resources',chname, fgenre] if pchance else [chname, fgenre]
                        for file, dur, oitem in self.getTrailers(tkeys, tcnt):
                            if file:
                                if pfillRuntime <= 0: break
                                pfillRuntime -= dur
                                self.log('injectBCTs, adding trailers %s - %s'%(file,dur))
                                if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Injecting Filler: Trailers',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                item = {'title':'Trailer','episodetitle':oitem.get('label',oitem.get('title','%s (%s)'%(chname,fgenre))),'genre':['Trailers'],'plot':oitem.get('plot',file),'path':file}
                                pfileList.append(self.builder.buildCells(citem,dur,entries=1,info=item)[0])
                                
                if len(pfileList) > 0:
                    nfileList.extend(randomShuffle(pfileList))
        return nfileList