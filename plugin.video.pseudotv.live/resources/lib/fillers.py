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
IGNORE_CHTYPE = ['TV Shows','Mixed','Recommended','Services',"Music Genres"]
MOVIE_CHTYPE  = ["Movie Genres","Movie Studios"]
TV_CHTYPE     = ["TV Networks","TV Genres","Mixed Genre"]

class Fillers:
    def __init__(self, builder):
        self.builder    = builder
        self.cache      = builder.cache
        self.jsonRPC    = builder.jsonRPC
        self.runActions = builder.runActions
        self.resources  = Resources(self.jsonRPC,self.cache)

        self.bctTypes   = {"ratings"  :{"max":builder.incPreroll ,"auto":builder.incPreroll  == -1,"enabled":bool(builder.incPreroll) ,"sources":builder.srcRatings,"items":{}},
                           "bumpers"  :{"max":builder.incPreroll ,"auto":builder.incPreroll  == -1,"enabled":bool(builder.incPreroll) ,"sources":builder.srcBumpers,"items":{}},
                           "adverts"  :{"max":builder.incPostroll,"auto":builder.incPostroll == -1,"enabled":bool(builder.incPostroll),"sources":builder.srcAdverts,"items":{}},
                           "trailers" :{"max":builder.incPostroll,"auto":builder.incPostroll == -1,"enabled":bool(builder.incPostroll),"sources":builder.srcTrailer,"items":{}}}
        self.fillSources()
        #todo create subfolders for template resources. channels & genres: Build_Post_Folders
        

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


    def getSingle(self, type, keys=['resources'], chance=False):
        tmpLST = []
        for key in keys: tmpLST.extend(self.bctTypes.get(type,{}).get('items',{}).get(key.lower(),[]))
        if len(tmpLST) > 0: return random.choice(tmpLST)
        elif chance:        return self.getSingle(type)
        else:               return {}


    def getMulti(self, type, keys=['resources'], count=1, chance=False):
        items  = []
        tmpLST = []
        for key in keys: tmpLST.extend(self.bctTypes.get(type,{}).get('items',{}).get(key.lower(),[]))
        if len(tmpLST) > 0: items = setDictLST(random.choices(tmpLST,k=count))
        if len(items) < count and chance: items.extend(self.getMulti(type,count=(count-len(items))))
        return items
    

    def injectBCTs(self, citem, fileList):
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
                ftype   = fileItem.get('type','')
                fgenre  = (fileItem.get('genre') or citem.get('group') or '')
                if isinstance(fgenre,list) and len(fgenre) > 0: fgenre = fgenre[0]
                
                # pre roll
                preFileList = []
                preKeys     = [chname, fgenre]
                if self.bctTypes['bumpers'].get('enabled',False) and ftype.startswith(tuple(TV_TYPES))    and chtype not in IGNORE_CHTYPE: preFileList.append(self.getSingle('bumpers',preKeys,chanceBool(SETTINGS.getSettingInt('Random_Pre_Chance'))))
                if self.bctTypes['bumpers'].get('enabled',False) and ftype.startswith(tuple(MOVIE_TYPES)) and chtype not in IGNORE_CHTYPE: preFileList.append(self.getSingle('bumpers',[(fitem.get('streamdetails',{}).get('audio') or [{}])[0].get('codec','')]))
                if self.bctTypes['ratings'].get('enabled',False) and ftype.startswith(tuple(MOVIE_TYPES)) and chtype not in IGNORE_CHTYPE: preFileList.append(self.getSingle('ratings',self.convertMPAA(fileItem.get('mpaa','NR'))[1]))

                #pre roll - bumpers/ratings
                for item in preFileList:
                    if not item.get('duration'): continue
                    else:
                        runtime += item.get('duration')
                        self.log('injectBCTs, adding bumper/ratings %s - %s'%(item.get('file'),item.get('duration')))
                        if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Filling Pre-Rolls',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                        item.update({'title':'Pre-Roll','episodetitle':item.get('label'),'genre':['Pre-Roll'],'plot':item.get('plot',item.get('file')),'path':item.get('file')})
                        nfileList.append(self.builder.buildCells(citem,item.get('duration'),entries=1,info=item)[0])
                        
                # original media
                nfileList.append(fileItem)
                self.log('injectBCTs, adding media %s - %s'%(fileItem.get('file'),fileItem.get('duration')))
                
                # post roll
                postKeys        = [chname, fgenre]
                postChance      = chanceBool(SETTINGS.getSettingInt('Random_Post_Chance'))
                postFillRuntime = diffRuntime(runtime) if (self.bctTypes['adverts']['auto'] and self.bctTypes['trailers']['auto']) else (MIN_GUIDEDAYS*3600)
                
                postFileList    = []
                if self.bctTypes['adverts'].get('enabled',False)  and chtype not in IGNORE_CHTYPE + MOVIE_CHTYPE: postFileList.extend(self.getMulti('adverts' ,postKeys, PAGE_LIMIT if self.bctTypes['adverts']['auto'] else self.bctTypes['adverts']['max'],postChance))
                if self.bctTypes['trailers'].get('enabled',False) and chtype not in IGNORE_CHTYPE: postFileList.extend(self.getMulti('trailers',postKeys, PAGE_LIMIT if self.bctTypes['trailers']['auto'] else self.bctTypes['trailers']['max'],postChance))
                postFileList    = randomShuffle(postFileList)
                postFillCount   = len(postFileList)

                # post roll - adverts/trailers
                self.log('injectBCTs, post roll current runtime %s, available runtime %s, available content %s'%(runtime, postFillRuntime,len(postFileList)))
                while not self.builder.service.monitor.abortRequested() and postFillRuntime > 0 and len(postFileList) > 0 and postFillCount > 0:
                    if self.builder.service._interrupt() or self.builder.service._suspend(): break
                    item = postFileList.pop(0)
                    if not item.get('duration'): continue
                    elif postFillRuntime <= 0: break
                    elif postFillRuntime >= item.get('duration'):
                        postFillRuntime -= item.get('duration')
                        self.log('injectBCTs, post advert/trailer %s - %s'%(item.get('file'),item.get('duration')))
                        if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Filling Post-Rolls',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                        item.update({'title':'Post-Roll','episodetitle':item.get('label'),'genre':['Post-Roll'],'plot':item.get('plot',item.get('file')),'path':item.get('file')})
                        nfileList.append(self.builder.buildCells(citem,item.get('duration'),entries=1,info=item)[0])
                    elif postFillRuntime < item.get('duration'):
                        postFillCount -= 1
                        postFileList.append(item)
                    self.log('injectBCTs, unused post roll runtime %s'%(postFillRuntime))
        return nfileList