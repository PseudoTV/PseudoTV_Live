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
        print(self.bctTypes['adverts'])
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def fillSources(self):
        if self.bctTypes['trailers'].get('enabled',False) and self.builder.incKODI:
            self.bctTypes['trailers']['items'] = mergeDictLST(self.bctTypes['trailers']['items'],self.builder.kodiTrailers())
                
        for ftype, values in list(self.bctTypes.items()):
            for id in values.get("sources",{}).get("resource",[]):
                if self.bctTypes[ftype].get('enabled',False): values['items'] = mergeDictLST(values['items'],self.buildSource(ftype,id))   #parse resource packs
            for path in values.get("sources",{}).get("paths",[]):
                if self.bctTypes[ftype].get('enabled',False): values['items'] = mergeDictLST(values['items'],self.buildSource(ftype,path)) #parse vfs paths
                

    @cacheit(expiration=datetime.timedelta(minutes=15),json_data=False)
    def buildSource(self, ftype, path):
        self.log('buildSource, type = %s, path = %s'%(ftype, path))
        def _parseVFS(path):
            tmpDCT = {}
            if hasAddon(path, install=True):
                for url, items in list(self.jsonRPC.walkFileDirectory(path,depth=CHANNEL_LIMIT,chkDuration=True,retItem=True).items()):
                    for item in items:
                        for key in (item.get('genre',[]) or ['resources']): tmpDCT.setdefault(key.lower(),[]).append(item)
            return tmpDCT
            
        def _parseLocal(path):
            if not FileAccess.exists(path): return {}
            return self.jsonRPC.walkListDirectory(path, exts=VIDEO_EXTS, depth=CHANNEL_LIMIT, chkDuration=True)

        def _parseResource(id):
            if not hasAddon(id, install=True): return {}
            return self.jsonRPC.walkListDirectory(os.path.join('special://home/addons/%s'%id,'resources'), exts=VIDEO_EXTS, depth=CHANNEL_LIMIT, checksum=self.jsonRPC.getAddonDetails(id).get('version',ADDON_VERSION), expiration=datetime.timedelta(days=MAX_GUIDEDAYS))

        def _sortbyfile(data):
            tmpDCT = {}
            for path, files in list(data.items()):
                for file in files:
                    dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                    if dur > 0: tmpDCT.setdefault(file.split('.')[0].lower(),[]).append({'file':os.path.join(path,file),'duration':dur,'label':'%s - %s'%(path.strip('/').split('/')[-1:][0],file.split('.')[0])})
            return tmpDCT
 
        def _sortbyfolder(data):
            tmpDCT = {}
            for path, files in list(data.items()):
                for file in files:
                    dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                    if dur > 0: tmpDCT.setdefault(path.strip('/').split('/')[-1:][0].lower(),[]).append({'file':os.path.join(path,file),'duration':dur,'label':'%s - %s'%(path.strip('/').split('/')[-1:][0],file.split('.')[0])})
            return tmpDCT
            
        if not path: return {}
        elif path.startswith('resource.'):
            if   ftype == 'ratings':                return _sortbyfile(_parseResource(path))
            elif ftype == 'bumpers':                return _sortbyfolder(_parseResource(path))
            elif ftype == 'adverts':                return _sortbyfolder(_parseResource(path))
            elif ftype == 'trailers':               return _sortbyfolder(_parseResource(path))
        elif     path.startswith('plugin://'):      return _parseVFS(path)
        elif not path.startswith(tuple(VFS_TYPES)): return _sortbyfolder(_parseLocal(path))
        else:                                       return {}
        
        
    def convertMPAA(self, ompaa):
        tmpLST = ompaa.split(' / ')
        tmpLST.append(ompaa.upper())
        try:    mpaa = re.compile(":(.*?)/", re.IGNORECASE).search(ompaa.upper()).group(1).strip()
        except: mpaa = ompaa.upper()
        #https://www.spherex.com/tv-ratings-vs-movie-ratings, #https://www.spherex.com/which-is-more-regulated-film-or-tv
        mpaa = mpaa.replace('TV-Y','G').replace('TV-Y7','G').replace('TV-G','G').replace('NA','NR').replace('TV-PG','PG').replace('TV-14','PG-13').replace('TV-MA','R')
        tmpLST.append(mpaa)
        return mpaa, tmpLST


    def getSingle(self, type, keys=['resources']):
        try:
            tmpLST = []
            for key in keys: tmpLST.extend(self.bctTypes.get(type,{}).get('items',{}).get(key.lower(),[]))
            return random.choice(tmpLST)
        except: return {}


    def getMulti(self, type, keys=['resources'], count=1):
        try:
            tmpLST = []
            for key in keys: tmpLST.extend(self.bctTypes.get(type,{}).get('items',{}).get(key.lower(),[]))
            return setDictLST(random.choices(tmpLST,k=count))
        except: return []
    

    def injectBCTs(self, citem, fileList):
        addBumpers   = self.bctTypes['bumpers'].get('enabled',False)
        addRatings   = self.bctTypes['ratings'].get('enabled',False)
        addAdverts   = self.bctTypes['adverts'].get('enabled',False)
        addTrailers  = self.bctTypes['trailers'].get('enabled',False)
        cntAdverts   = PAGE_LIMIT if self.bctTypes['adverts']['auto']  else self.bctTypes['adverts']['max']
        cntTrailers  = PAGE_LIMIT if self.bctTypes['trailers']['auto'] else self.bctTypes['trailers']['max']
        self.log('injectBCTs, Bumpers = %s, Ratings = %s, Adverts = %s, Trailers = %s'%(addBumpers,addRatings,addAdverts,addTrailers))
        
        nfileList = []
        for idx, fileItem in enumerate(fileList):
            if not fileItem: continue
            elif self.builder.service._interrupt() or self.builder.service._suspend(): break
            else:
                runtime = fileItem.get('duration',0)
                if runtime == 0: continue
                
                chtype  = citem.get('type','')
                chname  = citem.get('name','')
                fitem   = fileItem.copy()
                # nitem   = fileList[idx + 1].copy()
                ftype   = fileItem.get('type','')
                fgenre  = (fileItem.get('genre') or citem.get('group') or '')
                if isinstance(fgenre,list) and len(fgenre) > 0: fgenre = fgenre[0]
                
                #pre roll - bumpers
                if addBumpers:
                    bchance = chanceBool(SETTINGS.getSettingInt('Random_Bumper_Chance'))
                    if ftype.startswith(tuple(TV_TYPES)):
                        if chtype in ['Playlists','TV Networks','TV Genres','Mixed Genres','Custom']:
                            bkeys = [chname, fgenre]
                            if bchance: bkeys.insert(0,'resources')
                            bitem = self.getSingle('bumpers',bkeys)
                            if bitem.get('file') and bitem.get('duration',0) > 0:
                                runtime += bitem.get('duration')
                                self.log('injectBCTs, adding bumper %s - %s'%(bitem.get('file'),bitem.get('duration')))
                                if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Injecting Filler: Bumpers',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                bitem.update({'title':'%s (%s)'%(fitem.get('showlabel'),chname),'episodetitle':bitem.get('label',bitem.get('title','Bumper')),'genre':['Bumper'],'plot':fitem.get('plot',bitem.get('file')),'path':bitem.get('file')})
                                nfileList.append(self.builder.buildCells(citem,bitem.get('duration'),entries=1,info=bitem)[0])
                    # elif ftype.startswith(tuple(MOVIE_TYPES)):
                        # # #todo movie bumpers for audio/video codecs? imax, cinema experience bumpers?
                        # if chtype in ['Playlists','Movie Genres','Movie Studios','Mixed Genres','Custom']:
                            # bkeys = [fitem.get('streamdetails',{}).get('audio',[{}])[0].get('codec')]
                            # if bchance: bkeys.insert(0,'resources')
                
                #pre roll - ratings
                if addRatings:
                    if ftype.startswith(tuple(MOVIE_TYPES)):
                        mpaa, rkeys = self.convertMPAA(fileItem.get('mpaa','NR'))
                        ritem = self.getSingle('ratings',rkeys)
                        if ritem.get('file') and ritem.get('duration',0) > 0:
                            runtime += ritem.get('duration')
                            self.log('injectBCTs, adding rating %s - %s'%(ritem.get('file'),ritem.get('duration')))
                            if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Injecting Filler: Ratings',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                            ritem.update({'title':'%s (%s)'%(fitem.get('showlabel'),mpaa),'episodetitle':ritem.get('label',ritem.get('title','Rating')),'genre':['Rating'],'plot':fitem.get('plot',ritem.get('file')),'path':ritem.get('file')})
                            nfileList.append(self.builder.buildCells(citem,ritem.get('duration'),entries=1,info=ritem)[0])
                            
                # original media
                nfileList.append(fileItem)
                self.log('injectBCTs, adding media %s - %s'%(fileItem.get('file'),fileItem.get('duration')))

                # post roll init
                pfileList    = []
                afillRuntime = 0
                pfillRuntime = diffRuntime(runtime)
                pchance      = (chanceBool(SETTINGS.getSettingInt('Random_Advert_Chance')) | chanceBool(SETTINGS.getSettingInt('Random_Trailers_Chance')))
                pkeys        = [chname, fgenre]
                if pchance: pkeys.insert(0,'resources')
                self.log('injectBCTs, post roll current runtime %s, available runtime %s, chance insert = %s'%(runtime, pfillRuntime,pchance))
                
                # post roll - commercials
                if addAdverts:
                    afillRuntime = (pfillRuntime // 2) if addTrailers else pfillRuntime #if trailers enabled only fill half the required space with adverts, leaving room for trailers.  
                    pfillRuntime -= afillRuntime
                    self.log('injectBCTs, advert fill runtime %s'%(afillRuntime))
                    if chtype in ['Playlists','TV Networks','TV Genres','Mixed Genres','Custom']:
                        for aitem in self.getMulti('adverts',pkeys, cntAdverts): 
                            if aitem.get('file') and aitem.get('duration',0) > 0:
                                if   afillRuntime <= 0: break
                                elif afillRuntime < aitem.get('duration'): continue
                                else:
                                    afillRuntime -= aitem.get('duration')
                                    self.log('injectBCTs, adding advert %s - %s'%(aitem.get('file'),aitem.get('duration')))
                                    if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Injecting Filler: Adverts',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                    aitem.update({'title':'Advert','episodetitle':aitem.get('label',aitem.get('title','%s (%s)'%(chname,fgenre))),'genre':['Advert'],'plot':aitem.get('plot',aitem.get('file')),'path':aitem.get('file')})
                                    pfileList.append(self.builder.buildCells(citem,aitem.get('duration'),entries=1,info=aitem)[0])
                            
                # post roll - trailers
                if addTrailers:
                    pfillRuntime += afillRuntime
                    self.log('injectBCTs, trailers fill runtime %s'%(pfillRuntime))
                    if chtype in ['Playlists','TV Networks','TV Genres','Movie Genres','Movie Studios','Mixed Genres','Custom']:
                        for titem in self.getMulti('trailers',pkeys, cntTrailers):
                            if titem.get('file') and titem.get('duration',0) > 0:
                                if   pfillRuntime <= 0: break
                                elif pfillRuntime < titem.get('duration'): continue
                                else:
                                    pfillRuntime -= titem.get('duration')
                                    self.log('injectBCTs, adding trailers %s - %s'%(titem.get('file'),titem.get('duration')))
                                    if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Injecting Filler: Trailers',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                    titem.update({'title':'Trailer','episodetitle':titem.get('label',titem.get('title','%s (%s)'%(chname,fgenre))),'genre':['Trailer'],'plot':titem.get('plot',titem.get('file')),'path':titem.get('file')})
                                    pfileList.append(self.builder.buildCells(citem,titem.get('duration'),entries=1,info=titem)[0])
                        
                self.log('injectBCTs, unused post roll runtime %s'%(pfillRuntime))
                if len(pfileList) > 0: nfileList.extend(randomShuffle(pfileList))
        return nfileList