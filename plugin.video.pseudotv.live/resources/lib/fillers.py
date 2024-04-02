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

#todo support converting other region ratings, move desc. to language po
RATING_DESC = {"G"    :"General audiences – All ages admitted.\nNothing that would offend parents for viewing by children.",
               "PG"   :"Parental guidance suggested – Some material may not be suitable for children.\nParents urged to give “parental guidance.” May contain some material parents might not like for their young children",
               "PG-13":"Parents strongly cautioned – Some material may be inappropriate for children under 13.\nParents are urged to be cautious. Some material may be inappropriate for pre-teenagers.",
               "R"    :"Restricted – Under 17 requires accompanying parent or adult guardian.\nContains some adult material. Parents are urged to learn more about the film before taking their young children with them.",
               "NC-17":"Adults only – No one 17 and under admitted.\nClearly adult. Children are not admitted.",
               "NR"   :"Film has not been submitted for a rating or it's rating is unknown."}
             
IMDB_PATHS  = ['plugin://plugin.video.imdb.trailers/?action=list1&key=showing',
               'plugin://plugin.video.imdb.trailers/?action=list1&key=coming']
               
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

        #default global rules:
        self.bctTypes   = {"ratings"  :{"max":1                 ,"auto":builder.incRatings == 1,"enabled":bool(builder.incRatings),"sources":builder.srcRatings,"items":{}},
                           "bumpers"  :{"max":1                 ,"auto":builder.incBumpers == 1,"enabled":bool(builder.incBumpers),"sources":builder.srcBumpers,"items":{}},
                           "adverts"  :{"max":builder.incAdverts,"auto":builder.incAdverts == 1,"enabled":bool(builder.incAdverts),"sources":builder.srcAdverts,"items":{}},
                           "trailers" :{"max":builder.incTrailer,"auto":builder.incTrailer == 1,"enabled":bool(builder.incTrailer),"sources":builder.srcTrailer,"items":{}}}
        self.fillSources()
        print('self.bctTypes',self.bctTypes)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def fillSources(self):
        for ftype, values in self.bctTypes.items():
            for id in values.get("sources",{}).get("resource",[]):
                values['items'].update(self.buildResource(ftype,id))
            # for id in values.get("sources",{}).get("paths",[]): #parse vfs for media
                # values['items'].update(self.getfilelist(ftype,id))
        

    @cacheit(expiration=datetime.timedelta(minutes=15),json_data=True)
    def buildResource(self, ftype, addonid):
        self.log('buildResource, type = %s, addonid = %s'%(ftype, addonid))
        def _parse(addonid):
            if hasAddon(addonid):
                 #{'special://home/addons/resource.videos.ratings.mpaa.classic/resources': ['G.mkv', 'NC-17.mkv', 'NR.mkv', 'PG-13.mkv', 'PG.mkv', 'R.mkv']}
                return self.resources.walkResource(addonid,exts=VIDEO_EXTS)
            return {}
            
        def _rating(addonid):
            tmpDCT = {}
            for path, files in _parse(addonid).items():
                for file in files:
                    dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                    if dur > 0: tmpDCT.setdefault(file.split('.')[0],[]).append((os.path.join(path,file),dur)) #{'PG-13':[('PG-13.mkv',7)]}
            return tmpDCT
            
        def _bumper(addonid):
            tmpDCT = {}
            for path, files in _parse(addonid).items():
                for file in files:
                    dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                    if dur > 0: tmpDCT.setdefault(os.path.basename(path).lower(),[]).append((os.path.join(path,file),dur))
            return tmpDCT
                
        def _advert(addonid):
            tmpDCT = {}
            for path, files in _parse(addonid).items():
                for file in files:
                    dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                    if dur > 0: tmpDCT.setdefault(os.path.basename(path).lower(),[]).append((os.path.join(path,file),dur))
            return tmpDCT
            
        def _trailer(addonid):
            tmpDCT = {}
            for path, files in _parse(addonid).items():
                for file in files:
                    dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                    if dur > 0: tmpDCT.setdefault(os.path.basename(path).lower(),[]).append((os.path.join(path,file),dur))
            return tmpDCT
            
        if   ftype == 'ratings':  return _rating(addonid)
        elif ftype == 'bumpers':  return _bumper(addonid)
        elif ftype == 'adverts':  return _advert(addonid)
        elif ftype == 'trailers': return _trailer(addonid)
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


    def getRating(self, keys=[]):
        def _parse(key):
            tmpLST.extend(self.bctTypes['ratings'].get('items',{}).get(key,[]))
        try:
            tmpLST = []
            poolit(_parse)(keys)
            return random.choice(tmpLST)
        except: return None, 0
        

    def getBumper(self, keys=['resources']):
        def _parse(key):
            tmpLST.extend(self.bctTypes['bumpers'].get('items',{}).get(key.lower(),[]))
        try:
            tmpLST = []
            poolit(_parse)(keys)
            random.shuffle(tmpLST)
            return random.choice(tmpLST)
        except: return None, 0
    

    def getAdverts(self, keys=['resources'], count=1):
        def _parse(key):
            return self.bctTypes['adverts'].get('items',{}).get(key.lower(),[])
        try:
            tmpLST = poolit(_parse)(keys)
            random.shuffle(tmpLST)
            removeDUPDICT(random.choices(tmpLST,k=count))
        except: return [(None, 0)]
    

    def getTrailers(self, keys=['resources'], count=1):
        def _parse(key):
            return self.bctTypes['trailers'].get('items',{}).get(key.lower(),[])
        try:
            tmpLST = poolit(_parse)(keys)
            random.shuffle(tmpLST)
            removeDUPDICT(random.choices(tmpLST,k=count))
        except: return [(None, 0)]


    def buildKodiTrailers(self, fileList):
        def _parse(fileItem):
            if fileItem.get('trailer') and not fileItem.get('trailer','').startswith(tuple(VFS_TYPES)):
                dur = self.jsonRPC.getDuration(fileItem.get('trailer'), accurate=True)
                if dur > 0: tmpLST.append((fileItem.get('trailer'), dur))
        tmpLST = []
        poolit(_parse)(fileList)
        if len(tmpLST) > 0:
            tmpLST.reverse()
            self.bctTypes['trailers']['items'].setdefault("resources",[]).extend(tmpLST)
            self.bctTypes['trailers']['items']['resources'] = [t for t in (set(tuple(i) for i in self.bctTypes['trailers']['items']['resources']))]
            print('buildKodiTrailers',self.bctTypes['trailers']['items']['resources'])


    def injectBCTs(self, citem, fileList):
        nfileList = []
        if self.bctTypes['trailers']['enabled'] and SETTINGS.getSettingInt('Include_Trailers') < 2:
            self.buildKodiTrailers(fileList)
            
        for idx, fileItem in enumerate(fileList):
            if not fileItem: continue
            elif self.builder.service._interrupt() or self.builder.service._suspend(): break
            else:
                chtype  = citem.get('type','')
                chname  = citem.get('name','')
                ftype   = fileItem.get('type','')
                fgenre  = fileItem.get('genre',citem.get('group',['']))
                ftitle  = fileItem.get('title',fileItem.get('label'))
                fmpaa   = fileItem.get('mpaa','NR')
                runtime = fileItem.get('duration',0)
                if runtime == 0: continue

                #pre roll - bumpers
                if self.bctTypes['bumpers']['enabled']:
                    # #todo movie bumpers for audio/video codecs? imax bumpers?
                    if ftype.startswith(tuple(TV_TYPES)):
                        if chtype in ['Playlists','TV Networks','TV Genres','Mixed Genres','Custom']:
                            bkeys = ['resources',chname, fgenre[0]] if chanceBool(SETTINGS.getSettingInt('Random_Bumper_Chance')) else [chname, fgenre[0]]
                            file, dur = self.getBumper(bkeys)
                            if file:
                                runtime += dur
                                self.log('injectBCTs, adding bumper %s - %s'%(file,dur))
                                if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='%s - Inserting Filler: Bumpers'%(self.builder.pName),header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                nfileList.append(self.builder.buildCells(citem,dur,entries=1,info={'title':'%s (%s)'%(chname,fgenre[0]),'genre':['Bumper'],'plot':file,'path':file})[0])
                
                #pre roll - ratings
                if self.bctTypes['ratings']['enabled']:
                    if ftype.startswith(tuple(MOVIE_TYPES)):
                        mpaa, rkeys = self.convertMPAA(fmpaa)
                        file, dur = self.getRating(rkeys)
                        if file:
                            runtime += dur
                            self.log('injectBCTs, adding rating %s - %s'%(file,dur))
                            if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='%s - Inserting Filler: Ratings'%(self.builder.pName),header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                            nfileList.append(self.builder.buildCells(citem,dur,entries=1,info={'title':'%s (%s)'%(ftitle,mpaa),'genre':['Rating'],'plot':RATING_DESC.get(mpaa,''),'path':file})[0])
                            
                # original media
                nfileList.append(fileItem)
                
                # post roll - commercials
                pfileList    = []
                pfillRuntime = roundRuntimeUP(runtime)
                self.log('injectBCTs, post roll current runtime %s, available runtime %s'%(runtime, pfillRuntime))
                if self.bctTypes['adverts']['enabled']:
                    acnt = 25 if self.bctTypes['adverts']['auto'] else self.bctTypes['adverts']['max']
                    afillRuntime = (pfillRuntime // 2) if self.bctTypes['trailers']['enabled'] else pfillRuntime #if trailers enabled only fill half the required space, leaving room for trailers.  
                    pfillRuntime -= afillRuntime
                    self.log('injectBCTs, advert fill runtime %s'%(afillRuntime))
                    if chtype in ['Playlists','TV Networks','TV Genres','Mixed Genres','Custom']:
                        akeys = ['resources',chname, fgenre[0]] if chanceBool(SETTINGS.getSettingInt('Random_Advert_Chance')) else [chname, fgenre[0]]
                        for file, dur in self.getAdverts(akeys, acnt):
                            if file:
                                if afillRuntime <= 0: break
                                afillRuntime -= dur
                                self.log('injectBCTs, adding advert %s - %s'%(file,dur))
                                if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='%s - Inserting Filler: Adverts'%(self.builder.pName),header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                pfileList.append(self.builder.buildCells(citem,dur,entries=1,info={'title':'%s (%s)'%(chname,fgenre[0]),'genre':['Adverts'],'plot':file,'path':file})[0])
                            
                # post roll - trailers
                if self.bctTypes['trailers']['enabled']:
                    self.log('injectBCTs, trailers fill runtime %s'%(pfillRuntime))
                    tcnt = 25 if self.bctTypes['trailers']['auto'] else self.bctTypes['trailers']['max']
                    self.log('injectBCTs, trailers fill runtime %s'%(pfillRuntime))
                    if chtype in ['Playlists','TV Networks','TV Genres','Movie Genres','Movie Genres','Movie Studios','Mixed Genres','Custom']:
                        tkeys = ['resources',chname, fgenre[0]] if chanceBool(SETTINGS.getSettingInt('Random_Trailers_Chance')) else [chname, fgenre[0]]
                        for file, dur in self.getTrailers(tkeys, tcnt):
                            if file:
                                if pfillRuntime <= 0: break
                                pfillRuntime -= dur
                                self.log('injectBCTs, adding trailers %s - %s'%(file,dur))
                                if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='%s - Inserting Filler: Trailers'%(self.builder.pName),header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                pfileList.append(self.builder.buildCells(citem,dur,entries=1,info={'title':'%s (%s)'%(chname,fgenre[0]),'genre':['Trailers'],'plot':file,'path':file})[0])
                                
                if len(pfileList) > 0:
                    pfileList.shuffle()
                    nfileList.extend(pfileList)
        return nfileList
                    
        # getSettingInt('Include_Trailers')
        # HasAddon(plugin.video.imdb.trailers)
        # HasContent(Movies)
        # return fileList
        # if not fileList: return fileList
        # self.log("injectBCTs, channel = %s, fileList = %s"%(citem.get('id'),len(fileList)))
        # ratings = self.buildResourceByType('ratings')
        # bumpers = self.buildResourceByType('bumpers')
        
        # lstop     = 0
        # nFileList = list()
        # chname    = citem.get('name','')
        # chcats    = citem.get('groups',[])
        
        # for idx,fileItem in enumerate(fileList):
            # fileItem['originalfile'] = fileItem.get('file','')
            # fileItem['start'] = fileItem['start'] if lstop == 0 else lstop
            # fileItem['stop']  = fileItem['start'] + fileItem['duration']
        
            # paths  = [file]
            # oPaths = paths.copy()
            # stop   = fileItem['stop']
            # end    = abs(roundTimeUp(stop) - stop) #auto mode
            
            # # print('duration',fileItem['duration'])
            # # print('start',datetime.datetime.fromtimestamp(fileItem['start']))
            # # print('stop',datetime.datetime.fromtimestamp(stop))
            # # print('end',end)
            
            # if ratings and self.bctTypes['ratings'].get('enabled',True):
                # mpaa = cleanMPAA(fileItem.get('mpaa',''))
                # if self.builder.is3D(fileItem): mpaa += ' (3DSBS)'
                # rating = ratings.get(mpaa.lower(), {})
                # if rating:
                    # paths.insert(0,rating.get('file'))
                    # end -= rating.get('duration')
                    # # print('end ratings', end)
                    # # print('mpaa',mpaa)  
                    # # print('rating',rating) 
        
            # if bumpers and self.bctTypes['bumpers'].get('enabled',True):
                # bumper = random.choice(bumpers)
                # paths.insert(0,bumper.get('file'))
                # end -= bumper.get('duration')
                # # print('end bumper', end)
                # # print('chname',chname)
                # # print('bumper',bumper)
        
        
        
        
        
        # return fileList















#settings
# Fillers_Ratings #0=disabled,1=auto,2=1 insert,3=2 insert, 4=3 insert, 5=4 insert.
# Fillers_Bumpers
# Fillers_Commercials
# Fillers_Trailers

# Resource_Ratings #ex resource.videos.trailers.sample
# Resource_Bumpers #ex resource.videos.bumpers.pseudotv|resource.videos.bumpers.sample
# Resource_Commericals
# Resource_Trailers