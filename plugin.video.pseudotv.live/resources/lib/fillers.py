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
        self.jsonRPC    = builder.jsonRPC
        self.cache      = builder.jsonRPC.cache
        self.runActions = builder.runActions
        self.resources  = Resources(service=builder.service)
        self.fillSources()
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def fillSources(self):
        items = list(self.builder.bctTypes.items())
        for ftype, values in items:
            if not values.get('enabled',False): continue
            if self.builder.bctTypes.get(ftype,{}).get('incKODI',False):  self.builder.bctTypes.get(ftype,{})["items"] = mergeDictLST(self.builder.bctTypes.get(ftype,{}).get("items",[]), self.builder.getTrailers())
            for id   in values["sources"].get("ids",[]):   values['items'] = mergeDictLST(values.get('items',{}),self.buildSource(ftype,id))   #parse resource packs
            for path in values["sources"].get("paths",[]): values['items'] = mergeDictLST(values.get('items',{}),self.buildSource(ftype,path)) #parse vfs paths
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
            if       path.startswith('resource.'):      return __sortItems(_parseResource(path))
            elif     path.startswith('plugin://'):      return __sortItems(_parseVFS(path),'plugin')
            elif not path.startswith(tuple(VFS_TYPES)): return __sortItems(_parseLocal(path))
            else:                                       return {}
        except Exception as e: self.log("buildSource, failed! %s\n path = %s"%(e,path), xbmc.LOGERROR)
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
        items = [random.choice(tmpLST) for key in keys if (tmpLST := self.builder.bctTypes.get(type, {}).get('items', {}).get(key.lower(), []))]
        if not items and chance:
            items.extend(self.getSingle(type))
        self.log('getSingle, type = %s, keys = %s, chance = %s, returning = %s' % (type, keys, chance, len(items)))
        return setDictLST(items)
        

    def getMulti(self, type, keys=['resources'], count=1, chance=False):
        items = []
        tmpLST = []
        for key in keys:
            tmpLST.extend(self.builder.bctTypes.get(type, {}).get('items', {}).get(key.lower(), []))
        if len(tmpLST) >= count:
            items = random.sample(tmpLST, count)
        elif tmpLST:
            items = setDictLST(random.choices(tmpLST, k=count))
        if len(items) < count and chance:
            items.extend(self.getMulti(type, count=(count - len(items))))
        self.log('getMulti, type = %s, keys = %s, count = %s, chance = %s, returning = %s' % (type, keys, count, chance, len(items)))
        return setDictLST(items)
    

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
                dbtype  = fileItem.get('type','')
                fmpaa   = (self.convertMPAA(fileItem.get('mpaa')) or 'NR')
                fcodec  = (fileItem.get('streamdetails',{}).get('audio') or [{}])[0].get('codec','')
                fgenre  = (fileItem.get('genre') or citem.get('group') or '')
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
                    if self.builder.bctTypes[ftype].get('enabled',False) and chtype not in IGNORE_CHTYPE:
                        preFileList.extend(self.getSingle(ftype, preKeys, chanceBool(self.builder.bctTypes[ftype].get('chance',0))))

                    for item in setDictLST(preFileList):
                        if (item.get('duration') or 0) > 0:
                            runtime += item.get('duration')
                            self.log('[%s] injectBCTs, adding pre-roll %s - %s'%(citem.get('id'),item.get('duration'),item.get('file')))
                            if self.builder.pDialog: self.builder.pDialog = DIALOG.updateProgress(self.builder.pCount, self.builder.pDialog, message='Filling Pre-Rolls',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                            item.update({'title':'Pre-Roll','episodetitle':item.get('label'),'genre':['Pre-Roll'],'plot':item.get('plot',item.get('file')),'path':item.get('file')})
                            nfileList.append(self.builder.buildCells(citem,item.get('duration'),entries=1,info=item)[0])

                # original media
                nfileList.append(fileItem)
                self.log('[%s] injectBCTs, adding media %s - %s'%(citem.get('id'),fileItem.get('duration'),fileItem.get('file')))
                
                # post roll - adverts/trailers
                postFileList = []
                for ftype in ['adverts','trailers']:
                    postIgnoreTypes = {'adverts':IGNORE_CHTYPE + MOVIE_CHTYPE,'trailers':IGNORE_CHTYPE}[ftype]
                    postFillRuntime = diffRuntime(runtime) if self.builder.bctTypes[ftype]['auto'] else self.builder.bctTypes[ftype]['max']
                    if self.builder.bctTypes[ftype].get('enabled',False) and chtype not in postIgnoreTypes:
                        postFileList.extend(self.getMulti(ftype, [chname, fgenre], (PAGE_LIMIT * 2) if self.builder.bctTypes[ftype]['auto'] else self.builder.bctTypes[ftype]['min'],chanceBool(self.builder.bctTypes[ftype].get('chance',0))))

                if len(postFileList) > 0:
                    postFileList = len(randomShuffle(postFileList))
                    self.log('[%s] injectBCTs, post-roll current runtime %s, available runtime %s, available content %s'%(citem.get('id'),runtime, postFillRuntime,len(postFileList)))
                    while not self.builder.service.monitor.abortRequested() and postFillRuntime > 0 and len(postFileList) > 0:
                        if self.builder.service.monitor.waitForAbort(0.001): break
                        elif len(postFileList) == 0: break
                        else:
                            item = postFileList.pop(0)
                            if (item.get('duration') or 0) == 0: continue
                            elif postFillRuntime <= 0: break
                            elif postFillRuntime >= item.get('duration'):
                                postFillRuntime -= item.get('duration')
                                self.log('[%s] injectBCTs, adding post-roll %s - %s'%(citem.get('id'),item.get('duration'),item.get('file')))
                                if self.builder.pDialog: self.builder.pDialog = DIALOG.updateProgress(self.builder.pCount, self.builder.pDialog, message='Filling Post-Rolls',header='%s, %s'%(ADDON_NAME,self.builder.pMSG))
                                item.update({'title':'Post-Roll','episodetitle':item.get('label'),'genre':['Post-Roll'],'plot':item.get('plot',item.get('file')),'path':item.get('file')})
                                nfileList.append(self.builder.buildCells(citem,item.get('duration'),entries=1,info=item)[0])
                            elif postFillRuntime < item.get('duration'): postFileList.append(item)
                        if (self.builder.bctTypes['adverts']['auto'] and self.builder.bctTypes['trailers']['auto']): self.log('[%s] injectBCTs, unused post roll runtime %s'%(citem.get('id'),postFillRuntime))
        self.log('[%s] injectBCTs, finished'%(citem.get('id')))
        return nfileList