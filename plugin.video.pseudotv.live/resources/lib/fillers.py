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
    def __init__(self, builder, citem={}):
        self.builder    = builder
        self.bctTypes   = builder.bctTypes
        self.runActions = builder.runActions
        self.jsonRPC    = builder.jsonRPC
        self.cache      = builder.jsonRPC.cache
        self.citem      = citem
        self.resources  = Resources(service=builder.service)
        self.log('[%s] __init__, bctTypes = %s'%(self.citem.get('id'),builder.bctTypes))
        self.fillSources(citem, builder.bctTypes)
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def fillSources(self, citem={}, bctTypes={}):
        for ftype, values in list(bctTypes.items()):
            if values.get('enabled',False):
                self.builder.updateProgress(self.builder.pCount,message='%s %s'%(LANGUAGE(30014),ftype.title()),header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                if values.get('incKODI',False): values["items"] = mergeDictLST(values.get('items',{}), self.builder.getTrailers())
                    
                for id   in values["sources"].get("ids",[]):
                    values['items'] = mergeDictLST(values.get('items',{}),self.buildSource(ftype,id))   #parse resource packs
                    
                for path in values["sources"].get("paths",[]):
                    values['items'] = mergeDictLST(values.get('items',{}),self.buildSource(ftype,path)) #parse vfs paths
                    
                values['items'] = lstSetDictLst(values['items'])
                self.log('[%s] fillSources, type = %s, items = %s'%(self.citem.get('id'),ftype,len(values['items'])))
    
    
    @cacheit(expiration=datetime.timedelta(minutes=30),json_data=False)
    def buildSource(self, ftype, path=''):
        self.log('[%s] buildSource, type = %s, path = %s'%(self.citem.get('id'),ftype, path))
        def _parseResource(id):
            if hasAddon(id, install=True): return self.jsonRPC.walkListDirectory(os.path.join('special://home/addons/%s'%id,'resources'),exts=VIDEO_EXTS,depth=CHANNEL_LIMIT,checksum=self.jsonRPC.getAddonDetails(id).get('version',ADDON_VERSION),expiration=datetime.timedelta(days=MAX_GUIDEDAYS))

        def _parseVFS(path):
            if path.startswith('plugin://'):
                if not hasAddon(path, install=True): return {}
            return self.jsonRPC.walkFileDirectory(path, depth=CHANNEL_LIMIT, chkDuration=True, retItem=True)

        def _parseLocal(path):
            if FileAccess.exists(path): return self.jsonRPC.walkListDirectory(path,exts=VIDEO_EXTS,depth=CHANNEL_LIMIT,chkDuration=True)

        def __sortItems(data, stype='folder'):
            tmpDCT = {}
            if data:
                for path, files in list(data.items()):
                    if   stype == 'file':   key = file.split('.')[0].lower()
                    elif stype == 'folder': key = (os.path.basename(os.path.normpath(path)).replace('\\','/').strip('/').split('/')[-1:][0]).lower()
                    for file in files:
                        if isinstance(file,dict): [tmpDCT.setdefault(key.lower(),[]).append(file) for key in (file.get('genre',[]) or ['resources'])]
                        else:
                            dur = self.jsonRPC.getDuration(os.path.join(path,file), accurate=True)
                            if dur > 0: tmpDCT.setdefault(key.lower(),[]).append({'file':os.path.join(path,file),'duration':dur,'label':'%s - %s'%(path.strip('/').split('/')[-1:][0],file.split('.')[0])})
            self.log('[%s] buildSource, __sortItems: stype = %s, items = %s'%(self.citem.get('id'),stype,len(tmpDCT)))
            return tmpDCT
        
        try:
            if   path.startswith('resource.'):               return __sortItems(_parseResource(path))
            elif path.startswith(tuple(VFS_TYPES+DB_TYPES)): return __sortItems(_parseVFS(path))
            else:                                            return __sortItems(_parseLocal(path))
        except Exception as e: self.log("[%s] buildSource, failed! %s\n path = %s"%(self.citem.get('id'),e,path), xbmc.LOGERROR)
        return {}
        
        
    def convertMPAA(self, ompaa):
        try:
            ompaa = ompaa.upper()
            mpaa  = re.compile(":(.*?)/", re.IGNORECASE).search(ompaa).group(1).strip()
        except: return ompaa
        mpaa = mpaa.replace('TV-Y','G').replace('TV-Y7','G').replace('TV-G','G').replace('NA','NR').replace('TV-PG','PG').replace('TV-14','PG-13').replace('TV-MA','R')
        return mpaa

#todo always add a bumper for pseudo/kodi (based on build ver.)
# resource.videos.bumpers.kodi
# resource.videos.bumpers.pseudotv

    def getSingle(self, type, keys=['resources'], chance=False):
        items = [random.choice(tmpLST) for key in keys if (tmpLST := self.bctTypes.get(type, {}).get('items', {}).get(key.lower(), []))]
        if not items and chance:
            items.extend(self.getSingle(type))
        self.log('[%s] getSingle, type = %s, keys = %s, chance = %s, returning = %s' % (self.citem.get('id'),type, keys, chance, len(items)))
        return setDictLST(items)
        

    def getMulti(self, type, keys=['resources'], count=1, chance=False):
        items = []
        tmpLST = []
        for key in keys:
            tmpLST.extend(self.bctTypes.get(type, {}).get('items', {}).get(key.lower(), []))
        if len(tmpLST) >= count:
            items = random.sample(tmpLST, count)
        elif tmpLST:
            items = setDictLST(random.choices(tmpLST, k=count))
        if len(items) < count and chance:
            items.extend(self.getMulti(type, count=(count - len(items))))
        self.log('[%s] getMulti, type = %s, keys = %s, count = %s, chance = %s, returning = %s' % (self.citem.get('id'),type, keys, count, chance, len(items)))
        return setDictLST(items)
    

    def injectBCTs(self, fileList):
        nfileList = []
        for idx, fileItem in enumerate(fileList):
            if not fileItem: continue
            else:
                runtime = fileItem.get('duration',0)
                if runtime == 0: continue
                
                chtype  = self.citem.get('type','')
                chname  = self.citem.get('name','')
                fitem   = fileItem.copy()
                dbtype  = fileItem.get('type','')
                fmpaa   = (self.convertMPAA(fileItem.get('mpaa')) or 'NR')
                fcodec  = (fileItem.get('streamdetails',{}).get('audio') or [{}])[0].get('codec','')
                fgenre  = (fileItem.get('genre') or self.citem.get('group') or '')
                if isinstance(fgenre,list) and len(fgenre) > 0: fgenre = fgenre[0]
                
                #pre roll - bumpers/ratings
                if dbtype.startswith(tuple(MOVIE_TYPES)):
                    ftype   = 'ratings'
                    preKeys = [fmpaa, fcodec]
                elif dbtype.startswith(tuple(TV_TYPES)):
                    ftype   = 'bumpers'
                    preKeys = [chname, fgenre]
                else:
                    ftype   = None
                
                if ftype:
                    preFileList = []
                    if self.bctTypes[ftype].get('enabled',False) and chtype not in IGNORE_CHTYPE:
                        preFileList.extend(self.getSingle(ftype, preKeys, chanceBool(self.bctTypes[ftype].get('chance',0))))

                    for item in setDictLST(preFileList):
                        if (item.get('duration') or 0) > 0:
                            runtime += item.get('duration')
                            self.log('[%s] injectBCTs, adding pre-roll %s - %s'%(self.citem.get('id'),item.get('duration'),item.get('file')))
                            self.builder.updateProgress(self.builder.pCount,message='Filling Pre-Rolls',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                            item.update({'title':'Pre-Roll','episodetitle':item.get('label'),'genre':['Pre-Roll'],'plot':item.get('plot',item.get('file')),'path':item.get('file')})
                            nfileList.append(self.builder.buildCells(self.citem,item.get('duration'),entries=1,info=item)[0])

                # original media
                nfileList.append(fileItem)
                self.log('[%s] injectBCTs, adding media %s - %s'%(self.citem.get('id'),fileItem.get('duration'),fileItem.get('file')))
                
                # post roll - adverts/trailers
                postFileList = []
                for ftype in ['adverts','trailers']:
                    postIgnoreTypes = {'adverts':IGNORE_CHTYPE + MOVIE_CHTYPE,'trailers':IGNORE_CHTYPE}[ftype]
                    postFillRuntime = diffRuntime(runtime) if self.bctTypes[ftype]['auto'] else MIN_EPG_DURATION
                    if self.bctTypes[ftype].get('enabled',False) and chtype not in postIgnoreTypes:
                        postFileList.extend(self.getMulti(ftype, [chname, fgenre], self.bctTypes[ftype]['max'] if self.bctTypes[ftype]['auto'] else self.bctTypes[ftype]['min'], chanceBool(self.bctTypes[ftype].get('chance',0))))

                postAuto = (self.bctTypes['adverts']['auto'] | self.bctTypes['trailers']['auto'])
                postCounter = 0
                if len(postFileList) > 0:
                    postFileList = randomShuffle(postFileList)
                    self.log('[%s] injectBCTs, post-roll current runtime %s, available runtime %s, available content %s'%(self.citem.get('id'),runtime, postFillRuntime,len(postFileList)))
                    while not self.builder.service.monitor.abortRequested() and postFillRuntime > 0 and len(postFileList) > 0:
                        if self.builder.service.monitor.waitForAbort(0.001): break
                        else:
                            item = postFileList.pop(0)
                            if (item.get('duration') or 0) == 0: continue
                            elif postAuto and postCounter >= len(postFileList):
                                self.log('[%s] injectBCTs, unused post roll runtime %s %s/%s'%(self.citem.get('id'),postFillRuntime,postCounter,len(postFileList)))
                                break
                            elif postFillRuntime >= item.get('duration'):
                                postFillRuntime -= item.get('duration')
                                self.log('[%s] injectBCTs, adding post-roll %s - %s'%(self.citem.get('id'),item.get('duration'),item.get('file')))
                                self.builder.updateProgress(self.builder.pCount,message='Filling Post-Rolls',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                item.update({'title':'Post-Roll','episodetitle':item.get('label'),'genre':['Post-Roll'],'plot':item.get('plot',item.get('file')),'path':item.get('file')})
                                nfileList.append(self.builder.buildCells(self.citem,item.get('duration'),entries=1,info=item)[0])
                            elif postFillRuntime < item.get('duration'):
                                postFileList.append(item)
                                postCounter += 1
        self.log('[%s] injectBCTs, finished'%(self.citem.get('id')))
        return nfileList