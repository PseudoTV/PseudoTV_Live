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
        self.resources  = Resources(self.jsonRPC)
        self.fillSources()
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

        
    def getAdvertPath(self, id: str='plugin.video.ispot.tv') -> list:
        if hasAddon(id):
            try:    folder = os.path.join(xbmcaddon.Addon(id).getSetting('Download_Folder'),'resources','').replace('/resources/resources','/resources').replace('\\','/')
            except: folder = 'special://profile/addon_data/%s/resources/'%(id)
            self.log('getAdvertPath, folder = %s'%(folder))
            return folder
       

    def fillSources(self):
        for ftype, values in list(self.builder.bctTypes.items()):
            if not values.get('enabled',False) or self.builder.service._interrupt(): continue
            if self.builder.bctTypes.get(ftype,{}).get("incIspot",False):
                self.builder.bctTypes.get(ftype,{}).get("sources",{}).get("paths",[]).append(self.getAdvertPath())
                
            if self.builder.bctTypes.get(ftype,{}).get('incIMDB',False):
                self.builder.bctTypes.get(ftype,{}).get("sources",{}).get("paths",[]).extend(IMDB_PATHS) 
                
            if self.builder.bctTypes.get(ftype,{}).get('incKODI',False):
                self.builder.bctTypes.get(ftype,{})["items"] = mergeDictLST(self.builder.bctTypes.get(ftype,{}).get("items",[]), self.builder.kodiTrailers())

            for id   in values["sources"].get("ids",[]):   values['items'] = mergeDictLST(values['items'],self.buildSource(ftype,id))   #parse resource packs
            for path in values["sources"].get("paths",[]): values['items'] = mergeDictLST(values['items'],self.buildSource(ftype,path)) #parse vfs paths
            values['items'] = lstSetDictLst(values['items'])
    
    
    @cacheit(expiration=datetime.timedelta(minutes=15),json_data=False)
    def buildSource(self, ftype, path=''):
        self.log('buildSource, type = %s, path = %s'%(ftype, path))
        def _parseLocal(path):
            if FileAccess.exists(path): return self.jsonRPC.walkListDirectory(path,exts=VIDEO_EXTS,depth=CHANNEL_LIMIT,chkDuration=True)

        def _parseVFS(path):
            if hasAddon(path, install=True): return self.jsonRPC.walkFileDirectory(path,depth=CHANNEL_LIMIT,chkDuration=True,retItem=True)

        def _parseResource(id):
            if hasAddon(id, install=True): return self.jsonRPC.walkListDirectory(os.path.join('special://home/addons/%s'%id,'resources'),exts=VIDEO_EXTS,depth=CHANNEL_LIMIT,checksum=self.jsonRPC.getAddonDetails(id).get('version',ADDON_VERSION),expiration=datetime.timedelta(days=MAX_GUIDEDAYS))

        def __sortItems(data, stype='folder'):
            tmpDCT = {}
            if not data: return {}
            for path, files in list(data.items()):
                key = (os.path.basename(os.path.normpath(path)).replace('\\','/').strip('/').split('/')[-1:][0]).lower()
                for file in files:
                    if stype == 'plugin': [tmpDCT.setdefault(key.lower(),[]).append(file) for key in (file.get('genre',[]) or ['resources'])]
                    else:
                        if stype == 'file': key = file.split('.')[0].lower()
                        dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                        if dur > 0: tmpDCT.setdefault(key.lower(),[]).append({'file':os.path.join(path,file),'duration':dur,'label':'%s - %s'%(path.strip('/').split('/')[-1:][0],file.split('.')[0])})
            return tmpDCT
        
        try:
            if path.startswith('resource.'):
                if   ftype == 'ratings':                return __sortItems(_parseResource(path))
                elif ftype == 'bumpers':                return __sortItems(_parseResource(path))
                elif ftype == 'adverts':                return __sortItems(_parseResource(path))
                elif ftype == 'trailers':               return __sortItems(_parseResource(path))
            elif     path.startswith('plugin://'):      return __sortItems(_parseVFS(path),'plugin')
            elif not path.startswith(tuple(VFS_TYPES)): return __sortItems(_parseLocal(path))
            else:                                       return {}
        except Exception as e: self.log("buildSource, failed! %s\n path = %s"%(e,path), xbmc.LOGERROR)
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


    def getSingle(self, type, keys=['resources'], chance=False):
        self.log('getSingle, type = %s, keys = %s, chance = %s'%(type,keys,chance))
        tmpLST = []
        for key in keys: tmpLST.extend(self.builder.bctTypes.get(type,{}).get('items',{}).get(key.lower(),[]))
        if len(tmpLST) > 0: return random.choice(tmpLST)
        elif chance:        return self.getSingle(type)
        else:               return {}


    def getMulti(self, type, keys=['resources'], count=1, chance=False):
        items  = []
        tmpLST = []
        for key in keys: tmpLST.extend(self.builder.bctTypes.get(type,{}).get('items',{}).get(key.lower(),[]))
        if len(tmpLST) > 0: items = setDictLST(random.choices(tmpLST,k=count))
        if len(items) < count and chance: items.extend(self.getMulti(type,count=(count-len(items))))
        self.log('getMulti, type = %s, keys = %s, count = %s, chance = %s, returning = %s'%(type,keys,count,chance,len(items)))
        return items
    

    def injectBCTs(self, citem, fileList):
        nfileList = []
        for idx, fileItem in enumerate(fileList):
            if not fileItem: continue
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
                if self.builder.bctTypes['bumpers'].get('enabled',False) and ftype.startswith(tuple(TV_TYPES))    and chtype not in IGNORE_CHTYPE: preFileList.append(self.getSingle('bumpers',preKeys,chanceBool(SETTINGS.getSettingInt('Random_Pre_Chance'))))
                if self.builder.bctTypes['bumpers'].get('enabled',False) and ftype.startswith(tuple(MOVIE_TYPES)) and chtype not in IGNORE_CHTYPE: preFileList.append(self.getSingle('bumpers',[(fitem.get('streamdetails',{}).get('audio') or [{}])[0].get('codec','')]))
                if self.builder.bctTypes['ratings'].get('enabled',False) and ftype.startswith(tuple(MOVIE_TYPES)) and chtype not in IGNORE_CHTYPE: preFileList.append(self.getSingle('ratings',self.convertMPAA(fileItem.get('mpaa','NR'))[1]))

                #pre roll - bumpers/ratings
                for item in preFileList:
                    if (item.get('duration') or 0) == 0: continue
                    else:
                        runtime += item.get('duration')
                        self.log('injectBCTs, adding pre-roll %s - %s'%(item.get('duration'),item.get('file')))
                        if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Filling Pre-Rolls',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                        item.update({'title':'Pre-Roll','episodetitle':item.get('label'),'genre':['Pre-Roll'],'plot':item.get('plot',item.get('file')),'path':item.get('file')})
                        nfileList.append(self.builder.buildCells(citem,item.get('duration'),entries=1,info=item)[0])

                # original media
                nfileList.append(fileItem)
                self.log('injectBCTs, adding media %s - %s'%(fileItem.get('duration'),fileItem.get('file')))
                
                # post roll
                postKeys        = [chname, fgenre]
                postChance      = chanceBool(SETTINGS.getSettingInt('Random_Post_Chance'))
                postFillRuntime = diffRuntime(runtime) if (self.builder.bctTypes['adverts']['auto'] and self.builder.bctTypes['trailers']['auto']) else EPG_DURATION
                
                postFileList    = []
                if self.builder.bctTypes['adverts'].get('enabled',False)  and chtype not in IGNORE_CHTYPE + MOVIE_CHTYPE: postFileList.extend(self.getMulti('adverts' ,postKeys, (PAGE_LIMIT * 2) if self.builder.bctTypes['adverts']['auto'] else self.builder.bctTypes['adverts']['max'],postChance))
                if self.builder.bctTypes['trailers'].get('enabled',False) and chtype not in IGNORE_CHTYPE: postFileList.extend(self.getMulti('trailers',postKeys, (PAGE_LIMIT * 2) if self.builder.bctTypes['trailers']['auto'] else self.builder.bctTypes['trailers']['max'],postChance))
                postFileList    = randomShuffle(postFileList)
                postFillCount   = len(postFileList)

                # post roll - adverts/trailers
                if len(postFileList) > 0:
                    self.log('injectBCTs, post-roll current runtime %s, available runtime %s, available content %s'%(runtime, postFillRuntime,len(postFileList)))
                    while not self.builder.service.monitor.abortRequested() and postFillRuntime > 0 and postFillCount > 0:
                        if len(postFileList) == 0: break
                        else:
                            item = postFileList.pop(0)
                            if (item.get('duration') or 0) == 0: continue
                            elif postFillRuntime <= 0: break
                            elif postFillRuntime >= item.get('duration'):
                                postFillRuntime -= item.get('duration')
                                self.log('injectBCTs, adding post-roll %s - %s'%(item.get('duration'),item.get('file')))
                                if self.builder.pDialog: self.builder.pDialog = DIALOG.progressBGDialog(self.builder.pCount, self.builder.pDialog, message='Filling Post-Rolls',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                item.update({'title':'Post-Roll','episodetitle':item.get('label'),'genre':['Post-Roll'],'plot':item.get('plot',item.get('file')),'path':item.get('file')})
                                nfileList.append(self.builder.buildCells(citem,item.get('duration'),entries=1,info=item)[0])
                            elif postFillRuntime < item.get('duration'):
                                postFillCount -= 1
                                postFileList.append(item)
                        if (self.builder.bctTypes['adverts']['auto'] and self.builder.bctTypes['trailers']['auto']): self.log('injectBCTs, unused post roll runtime %s'%(postFillRuntime))
        return nfileList