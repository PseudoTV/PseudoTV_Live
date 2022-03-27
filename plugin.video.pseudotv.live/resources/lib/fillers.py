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

class Fillers:
    def __init__(self, builder=None):
        if builder is None: return
        self.builder = builder
        self.writer  = builder.writer
        self.cache   = builder.cache
        self.pool    = builder.pool


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def buildLocalTrailers(self, citem, fileList, includeVFS=False):
        #parse filelist for trailers, collect duration meta.
        self.log("buildLocalTrailers, channel = %s, fileList = %s"%(citem.get('id'),len(fileList)))
        def getItem(item):
            file = item.get('trailer','')
            if file:
                if not includeVFS and file.lower().startswith(tuple(VFS_TYPES)): return
                return {'label':'%s - Trailer'%(item['label']),'duration':self.writer.jsonRPC.parseDuration(file),'path':'','file':file,'art':item.get('art',{})}
        return setDictLST(list(filter(None,[getItem(fileItem) for fileItem in fileList])))


    def buildBCTresource(self, type, path, media='video'):
        self.log('buildBCTresource, type = %s, path = %s, media = %s'%(type,path,media))                
        def cleanResourcePath(path):
            if path.startswith('resource://'):
                return (path.replace('resource://','special://home/addons/'))
            return path

        if not path.startswith(('resource://')): checksum = ADDON_VERSION
        else: checksum = self.writer.jsonRPC.getPluginMeta(path).get('version',ADDON_VERSION)
        if type in PRE_ROLL: ignoreDuration = True
        else: ignoreDuration = False 
        return self.writer.jsonRPC.getFileDirectory(cleanResourcePath(path),media,ignoreDuration,checksum)


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

    
    def injectBCTs(self, citem, fileList):
        if not fileList: return fileList
        self.log("injectBCTs, channel = %s, fileList = %s"%(citem.get('id'),len(fileList)))
        #bctTypes = {"ratings" :{"min":1,"max":1,"enabled":True  ,"paths":[SETTINGS.getSetting('Resource_Ratings')]}}

        lstop     = 0
        bctItems  = dict()
        nfileList = list()
        chname    = citem.get('name','')
        chcats    = citem.get('groups',[])
        isMovie   = 'movie' in citem.get('type','').lower()
        [[bctItems.setdefault(key,{}).update(d) for d in list(self.buildResourceType(key, self.builder.bctTypes[key].get('paths',[])))]  for key in self.builder.bctTypes.keys() if self.builder.bctTypes[key].get('enabled',False)]
        
        if 'ratings' in bctItems:
            ratings = bctItems.get('ratings',{})
        else: 
            ratings = {}
        
        if 'bumpers' in bctItems:
            bumpers = bctItems.get('bumpers',{}).get('root',[])
            bumpers.extend(bctItems.get('bumpers',{}).get(chname.lower(),[]))
        else: 
            bumpers = []
        
        # min_commercials  = self.builder.bctTypes.get('commercials',{}).get('min',0) #0==Disabled,1==Auto
        # max_commercials  = self.builder.bctTypes.get('commercials',{}).get('max',4)
        # auto_commercials = min_commercials == 1
        # if 'commercials' in bctItems:
            # commercials = bctItems.get('commercials',{}).get(chname.lower(),[])
            # commercials.extend(bctItems.get('commercials',{}).get('root',[]))
            # if isinstance(commercials,list) and len(commercials) > 0: random.shuffle(commercials)
            # print('commercials',commercials)
        # else: 
            # commercials = []
            # auto_commercials = False
                  
        # min_trailers  = self.builder.bctTypes.get('trailers',{}).get('min',0) #0==Disabled,1==Auto
        # max_trailers  = self.builder.bctTypes.get('trailers',{}).get('max',4)
        # auto_trailers = min_trailers == 1
        # if 'trailers' in bctItems:  
            # trailers = []   
            # for chcat in chcats: trailers.extend(bctItems.get('trailers',{}).get(chcat.lower(),[]))
            # trailers.extend(bctItems.get('trailers',{}).get('root',[]))
            # trailers.extend(self.buildLocalTrailers(citem, fileList))
            # if isinstance(trailers,list) and len(trailers) > 0: random.shuffle(trailers)
            # print('trailers',trailers)
        # else: 
            # trailers = []
            # auto_trailers = False
        
        for idx,fileItem in enumerate(fileList):
            file = fileItem.get('file','')
            fileItem['originalfile'] = file
            fileItem['start'] = fileItem['start'] if lstop == 0 else lstop
            fileItem['stop']  = fileItem['start'] + fileItem['duration']
            
            if not file.startswith(tuple(VFS_TYPES)): #stacks not compatible with VFS sources.
                if isStack(file): 
                    paths = splitStacks(file)
                else: 
                    paths = [file]
                    
                oPaths = paths.copy()
                stop   = fileItem['stop']
                end    = abs(roundTimeUp(stop) - stop) #auto mode
                
                print('duration',fileItem['duration'])
                print('start',datetime.datetime.fromtimestamp(fileItem['start']))
                print('stop',datetime.datetime.fromtimestamp(stop))
                print('end',end)
                
                #ratings (auto == 1)
                mpaa = cleanMPAA(fileItem.get('mpaa',''))
                if is3D(fileItem): mpaa += ' (3DSBS)'  
                rating = ratings.get(mpaa.lower(), {})
                if rating:
                    paths.insert(0,rating.get('file'))
                    end -= rating.get('duration')
                    print('end ratings', end)
                    print('mpaa',mpaa)  
                    print('rating',rating) 
                    
                #bumpers (auto == 1)
                if bumpers:
                    bumper = random.choice(bumpers)
                    paths.insert(0,bumper.get('file'))
                    end -= bumper.get('duration')
                    print('end bumper', end)
                    print('chname',chname)
                    print('bumper',bumper)
                    
                # CTItems = set()
                # cnt_commercials = 0
                # cnt_trailers    = 0
                # #commercials
                # if commercials and not auto_commercials:
                    # for cnt in range(min_commercials):
                        # commercial = random.choice(commercials)
                        # CTItems.add(commercial.get('file'))
                        # end -= commercial.get('duration')
                        # print('end commercial', end)
                        # print('commercial',commercial)
                            
                #trailers
                # if trailers and not auto_trailers:
                    # trailers_sel = random.sample(trailers, random.randint(min_trailers,max_trailers))
                    # print('trailers_sel',trailers_sel)
                    # for trailer in trailers_sel:
                        # tfile = trailer.get('file')
                        # # if tfile.startwith(tuple(VFS_TYPES)):
                        # CTItems.add(tfile)
                        # end -= trailer.get('duration')
                        # print('end trailer', end)
                        # print('trailer',trailer)
                        
                # #auto fill POST_ROLL
                # if auto_commercials | auto_trailers:
                    # while end > 0 and not self.writer.monitor.abortRequested():
                        # if self.writer.monitor.waitForAbort(0.001): 
                            # self.log('injectBCTs, interrupted')
                            # break
                        # print('autofill while loop',end)
                        # stpos = end
                        # if commercials and auto_commercials and cnt_commercials <= max_commercials:
                            # commercial = random.choice(commercials)
                            # CTItems.add(commercial.get('file'))
                            # end -= commercial.get('duration')
                            # print('end commercial', end)
                            # print('commercial',commercial)
                        
                        # if trailers and auto_trailers and cnt_trailers <= max_trailers:
                            # trailer = random.choice(trailers)
                            # CTItems.add(trailer.get('file'))
                            # end -= trailer.get('duration')
                            # print('end trailer', end)
                            # print('trailer',trailer)
                            
                        # if stpos == end: break #empty list
                        
                # CTItems = list(CTItems)
                # print('CTItems',CTItems)
                # if len(CTItems) > 0:
                    # random.shuffle(CTItems)#shuffle, then random sample for increased diversity. 
                    # paths.extend(random.sample(CTItems, len(CTItems)))
                    
                # #todo trailers, commercials when "Auto" loop fill till end time close to 0. else fill random min,max count.
                # #trailers, commercials do not match by chname, random.choice from list, for variation users change resource folder in adv. rules.
                # #trailers always incorporate local_trailers from the media in current fileList playlist.
                
                # print('oPaths',oPaths)
                # print('paths',paths)
                    
                if oPaths != paths:
                    fileItem['file'] = buildStack(paths)
                    fileItem['stop'] = abs(roundTimeUp(stop) - abs(end))
                    fileItem['duration'] = (datetime.datetime.fromtimestamp(fileItem['stop']) - datetime.datetime.fromtimestamp(fileItem['start'])).seconds
                    print('end',end,'lstop',datetime.datetime.fromtimestamp(fileItem['stop']),'dur',fileItem['duration'])
                    print('fileItem',fileItem)

            lstop = fileItem['stop']  #new stop time, offset next start time.
            nfileList.append(fileItem)
        return nfileList
        
        
        
                        
        
        # # todo use zip to inject bcts?
        # # for r, b, f, c, t in zip(ratings, bumpers, filelist, commercials, trailers):
        
        
        
        
        
        # def buildResourcePaths(paths):
            # return list([self.writer.jsonRPC.resources.walkResource(path,VIDEO_EXTS) for path in paths])
            
        # def buildResourceType():
            # for key in self.builder.bctTypes.keys():
                # if self.builder.bctTypes[key].get('enabled',False):
                    # resources = buildResourcePaths(self.builder.bctTypes[key].get('paths',[]))
                    # for resource in resources:
                        # bcts = {}
                        # for id, filenames in resource.items():
                            # for file in filenames:
                                # bcts.setdefault(splitFilename(file)[0],[]).append(os.path.join(id,file))
                # yield key,bcts
                
        # print('injectBCTs',self.builder.bctTypes)
        # print('injectBCTs',dict(buildResourceType()))
       
        # {
            # 'ratings': [{
                # 'special://home/addons/resource.videos.ratings.mpaa.classic/resources': ['G (3DSBS).mp4', 'G.mp4', 'NC-17 (3DSBS).mp4', 'NC-17.mp4', 'NR (3DSBS).mp4', 'NR.mp4', 'PG (3DSBS).mp4', 'PG-13 (3DSBS).mp4', 'PG-13.mp4', 'PG.mp4', 'R (3DSBS).mp4', 'R.mp4']
            # }], 
                
            # 'bumpers': [{
                # 'special://home/addons/resource.videos.bumpers.pseudotv/resources': ['Glass Prism 1080p.mp4', 'HBO 1080p.mp4', 'Netflix 1080p.mp4', 'Netflix Colors 1080p.mp4']
            # }, {
                # 'special://home/addons/resource.videos.bumpers.sample/resources': [],
                # 'special://home/addons/resource.videos.bumpers.sample/resources/Cartoon Network': ['Cartoon Network.mp4'],
                # 'special://home/addons/resource.videos.bumpers.sample/resources/Discovery Channel': ['1.mp4'],
                # 'special://home/addons/resource.videos.bumpers.sample/resources/HBO': ['bumper.mp4'],
                # 'special://home/addons/resource.videos.bumpers.sample/resources/ITV': ['ITV.mp4', 'ITV2.mp4']
            # }],
            # 'commercials': [{
                # 'special://home/addons/resource.videos.commercials.sample/resources': ['t30s.mp4', 'teS5.mp4', 'teSG.mp4', 'teSI.mp4']
            # }],
            # 'trailers': [{
                # 'special://home/addons/resource.videos.trailers.sample/resources': ['Coming 2 America Trailer #2 (2021) - Movieclips Trailers.mp4', 'Raya and the Last Dragon Super Bowl TV Spot (2021) - Movieclips Trailers.mp4', 'Super Bowl Movie & TV Trailers (2021) - Movieclips Trailers.mp4']
            # }]
        # }
            
        # interleave
        # intersperse
        
        #ratings
        
        
        
        