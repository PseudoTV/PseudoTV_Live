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
        self.bctTypes   = {"ratings"  :{"max":1                 ,"auto":builder.incRatings == 1,"enabled":bool(builder.incRatings),"sources":builder.srcRatings,"resources":{}},
                           "bumpers"  :{"max":1                 ,"auto":builder.incBumpers == 1,"enabled":bool(builder.incBumpers),"sources":builder.srcBumpers,"resources":{}},
                           "adverts"  :{"max":builder.incAdverts,"auto":builder.incAdverts == 1,"enabled":bool(builder.incAdverts),"sources":builder.srcAdverts,"resources":{}},
                           "trailers" :{"max":builder.incTrailer,"auto":builder.incTrailer == 1,"enabled":bool(builder.incTrailer),"sources":builder.srcTrailer,"resources":{}}}

        self.fillResources()
        print('self.bctTypes',self.bctTypes)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def fillResources(self):
        data = {}
        for key, values in self.bctTypes.items():
            if values.get("sources",{}).get("RESC"):
                data = self.buildResource(key,values['sources']["RESC"])
            if data: values["resources"].update(data)


    # @cacheit(expiration=datetime.timedelta(minutes=15),json_data=True)
    def buildResource(self, type, ids):
        self.log('buildResource, type = %s, ids = %s'%(type, ids))
        def _parse(addonids):
            for addon in addonids:
                if not hasAddon(addon): continue
                yield self.resources.walkResource(addon,exts=VIDEO_EXTS)

        def _rating(resource):
            for path in resource:
                for file in resource[path]:
                    tmpDCT.setdefault(file.split('.')[0],[]).append(os.path.join(path,file)) #{'PG-13':[],'R':[]}
        tmpDCT = {}
        for id in list(_parse(ids)):
            if type == 'ratings': _rating(id)
        return tmpDCT
            
        
    def getRating(self, mpaa):
        def _convert(rating):
            #https://www.spherex.com/tv-ratings-vs-movie-ratings
            #https://www.spherex.com/which-is-more-regulated-film-or-tv
            return rating.replace('TV-Y','G').replace('TV-Y7','G').replace('TV-G','G').replace('NA','NR').replace('TV-PG','PG').replace('TV-14','PG-13').replace('TV-MA','R')
        try:
            mpaa = re.compile(":(.*?)/", re.IGNORECASE).search(mpaa.upper()).group(1)
            mpaa = mpaa.strip()
        except:
            mpaa = mpaa.upper()
        
        files = []
        for rating in [mpaa, _convert(mpaa)]:
            print('getRating',rating)
            files = self.bctTypes['ratings'].get('resources',{}).get(rating,[])
            if files: return rating, random.choice(files)
        return mpaa, None
        

    # @cacheit(expiration=datetime.timedelta(minutes=15),json_data=True)
    def buildKodiTrailers(self, fileList):
        def _parse(fileItem):
            if not fileItem.get('trailer','').startswith(tuple(VFS_TYPES)):
                return {'title':fileItem.get('title','Trailer'),'plot':(fileItem.get('plotoutline') or fileItem.get('plot','')),'path':fileItem.get('trailer')}
        return poolit(_parse)(fileList)


    def getTrailers(self, fileList):
        files = self.buildKodiTrailers(fileList)
        print('getTrailers',files)
        if files: return random.choice(files)
    

    def injectBCTs(self, citem, fileList):
        nfileList = []
        for idx, fileItem in enumerate(fileList):
            if not fileItem: continue
            elif self.builder.service._interrupt() or self.builder.service._suspend(): break
            else:
                #pre roll - ratings
                if fileItem.get('type').startswith(tuple(MOVIE_TYPES)):
                    if self.bctTypes['ratings'].get('enabled',False):
                        mpaa, file = self.getRating(fileItem.get('mpaa','NR'))
                        print('injectBCTs',mpaa,file)
                        if file:
                            dur = self.jsonRPC.getDuration(file, accurate=True)
                            if dur > 0:
                                self.log('injectBCTs, adding ratings %s\n%s - %s'%(fileItem.get('title'),file,dur))
                                nfileList.append(self.builder.buildCells(citem,dur,entries=1,info={'title':'%s (%s)'%(fileItem.get('title'),mpaa),'genre':['ratings'],'plot':RATING_DESC.get(mpaa,''),'path':file})[0])
                # #pre roll - bumpers
                # elif fileItem.get('type').startswith(tuple(TV_TYPES)):
                    # ...
                nfileList.append(fileItem)
                #post roll - commercials/trailers
                # if self.bctTypes['trailers'].get('enabled',False):
                    # tmpItem = self.getTrailers(fileList):
                    # dur = self.jsonRPC.getDuration(tmpItem.get('file'),tmpItem, accurate=True)
                    # print('injectBCTs',tmpItem,dur)
                    # if dur > 0: nfileList.append(self.builder.buildCells(citem,dur,entries=1,info=tmpItem)[0])
        return nfileList
                    
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