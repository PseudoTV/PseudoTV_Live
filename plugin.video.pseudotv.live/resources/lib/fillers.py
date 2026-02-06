#   Copyright (C) 2025 Lunatixz
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

class Fillers(object):
    def __init__(self, citem={}, builder=None):
        self.citem      = citem
        self.builder    = builder
        self.bctTypes   = builder.bctTypes
        self.runActions = builder.runActions
        self.jsonRPC    = builder.jsonRPC
        self.cache      = builder.jsonRPC.cache
        self.resources  = Resources(service=builder.service)
        self.fillSources()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)


    def fillSources(self):
        # Local references for speed
        builder = self.builder
        pDialog = getattr(builder, 'pDialog', None)
        pCount  = getattr(builder, 'pCount', 0)
        pMSG    = getattr(builder, 'pMSG', '')

        for ftype, values in self.bctTypes.items():
            if not values.get('enabled', False): continue
            builder.pDialog = DIALOG._updateProgress(pDialog, pCount,
                                                     message='%s %s' % (LANGUAGE(30014), ftype.title()),
                                                     header='%s, %s' % (ADDON_NAME, pMSG))
            # include KODI trailers if requested
            if values.get('incKODI', False):
                # mergeDictLST returns a new dict/list structure; call only when needed
                values["items"] = Globals._mergeDictLST(values.get('items', {}), builder.getTrailers())

            # parse resource packs (ids)
            ids = values.get("sources", {}).get("ids", [])
            for id_ in ids:
                values['items'] = Globals._mergeDictLST(values.get('items', {}), self.buildSource(ftype, id_))

            # parse paths (vfs/local)
            paths = values.get("sources", {}).get("paths", [])
            for path in paths:
                values['items'] = Globals._mergeDictLST(values.get('items', {}), self.buildSource(ftype, path))

            values['items'] = Globals._lstSetDictLst(values['items'])
            self.log('fillSources, type = %s, items = %s' % (ftype, len(values['items'])))


    @cacheit(expiration=datetime.timedelta(minutes=30), checksum=PROPERTIES.getInstanceID(), json_data=True)
    def buildSource(self, ftype, path=''):
        self.log('[%s] buildSource, type = %s, path = %s'%(self.citem.get('id'),ftype, path))
        def _parseResource(id):
            if SETTINGS.hasAddon(id, install=True): return self.jsonRPC.walkListDirectory(os.path.join('special://home/addons/%s'%id,'resources'),exts=VIDEO_EXTS,depth=CHANNEL_LIMIT,checksum=SETTINGS.getAddonDetails(id).get('version',ADDON_VERSION),expiration=datetime.timedelta(days=MAX_GUIDEDAYS))

        def _parseVFS(path):
            if path.startswith('plugin://'):
                if not SETTINGS.hasAddon(path, install=True): return {}
            return self.jsonRPC.walkFileDirectory(escapeDirJSON(path), depth=CHANNEL_LIMIT, chkDuration=True, retItem=True)

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
            if not ompaa:
                return ompaa
            ompaa = ompaa.upper()
            m = re.search(r":(.*?)/", ompaa, re.IGNORECASE)
            if not m:
                return ompaa
            mpaa = m.group(1).strip()
        except Exception:
            return ompaa
        return (mpaa.replace('TV-Y' , 'G')
                    .replace('TV-Y7', 'G')
                    .replace('TV-G' , 'G')
                    .replace('NA'   , 'NR')
                    .replace('TV-PG', 'PG')
                    .replace('TV-14', 'PG-13')
                    .replace('TV-MA', 'R'))

    def getSingle(self, type, keys=['resources'], chance=False):
        items = [random.choice(tmpLST) for key in keys if (tmpLST := self.bctTypes.get(type, {}).get('items', {}).get(key.lower(), []))]
        if not items and chance: items.extend(self.getSingle(type))
        self.log('[%s] getSingle, type = %s, keys = %s, chance = %s, returning = %s' % (self.citem.get('id'),type, keys, chance, len(items)))
        return Globals._setDictLST(items)


    def getMulti(self, type, keys=['resources'], count=1, chance=False):
        items  = []
        tmpLST = []
        for key in keys:
            tmpLST.extend(self.bctTypes.get(type, {}).get('items', {}).get(key.lower(), []))
        if len(tmpLST) >= count: items = random.sample(tmpLST, count)
        elif tmpLST:             items = Globals._setDictLST(random.choices(tmpLST, k=count))
        if len(items) < count and chance: items.extend(self.getMulti(type, count=(count - len(items))))
        self.log('[%s] getMulti, type = %s, keys = %s, count = %s, chance = %s, returning = %s' % (self.citem.get('id'),type, keys, count, chance, len(items)))
        return Globals._setDictLST(items)


    def injectBCTs(self, fileList):
        nfileList = []
        builder   = self.builder
        service   = builder.service

        for idx, fileItem in enumerate(fileList):
            if service._interrupt(): 
                return nfileList + fileList[idx + 1:]
            elif not fileItem: 
                continue
            runtime = fileItem.get('duration', 0)
            if runtime == 0:
                continue

            chtype = self.citem.get('type', '')
            chname = self.citem.get('name', '')
            fitem = fileItem  # don't copy unless necessary
            dbtype = fileItem.get('type', '')
            fmpaa = (self.convertMPAA(fileItem.get('mpaa')) or 'NR')
            fcodec = (fileItem.get('streamdetails', {}).get('audio') or [{}])[0].get('codec', '')
            fgenre = (fileItem.get('genre') or self.citem.get('group') or '')
            if isinstance(fgenre, list) and fgenre:
                fgenre = fgenre[0]

            # pre roll - bumpers/ratings
            ftype = None
            preKeys = []
            if dbtype.startswith(tuple(MOVIE_TYPES)):
                ftype = 'ratings'
                preKeys = [fmpaa, fcodec]
            elif dbtype.startswith(tuple(TV_TYPES)):
                ftype = 'bumpers'
                preKeys = [chname, fgenre]

            if ftype:
                preFileList = []
                bct = self.bctTypes.get(ftype, {})
                if bct.get('enabled', False) and chtype not in IGNORE_CHTYPE:
                    preFileList = self.getSingle(ftype, preKeys, chanceBool(bct.get('chance', 0)))

                # iterate and add pre-rolls
                for i, item in enumerate(Globals._setDictLST(preFileList)):
                    if service._interrupt() or service._suspend():
                        self.log("[%s] injectBCTs, _interrupt/_suspend" % self.citem.get('id'))
                        builder.pDialog = DIALOG._updateProgress(builder.pDialog, builder.pCount,
                                                                 message='%s: %s' % (LANGUAGE(32144), LANGUAGE(32213)),
                                                                 header=ADDON_NAME)
                        break
                    dur = item.get('duration', 0)
                    if dur > 0:
                        runtime += dur
                        self.log('[%s] injectBCTs, adding pre-roll %s - %s' % (self.citem.get('id'), dur, item.get('file')))
                        # Update progress infrequently; keep message simple
                        builder.pDialog = DIALOG._updateProgress(builder.pDialog, builder.pCount,
                                                                 message='Filling Pre-Rolls %s%%' % (int((i + 1) * 100 // max(1, len(preFileList)))),
                                                                 header='%s, %s' % (ADDON_NAME, getattr(builder, 'pMSG', '')))
                        item.update({'title'       : 'Pre-Roll',
                                     'episodetitle': item.get('label'),
                                     'genre'       : ['Pre-Roll'],
                                     'plot'        : item.get('plot', item.get('file')),
                                     'path'        : item.get('file')})
                        built = builder.buildCells(self.citem, dur, entries=1, info=item)
                        if built:
                            nfileList.append(built[0])

            # original media
            nfileList.append(fileItem)
            self.log('[%s] injectBCTs, adding media %s - %s' % (self.citem.get('id'), fileItem.get('duration'), fileItem.get('file')))

            # post roll - adverts/trailers
            postFileList = []
            ftypes = ['adverts', 'trailers']
            for ftype in ftypes:
                if service._interrupt() or service._suspend():
                    self.log("[%s] injectBCTs, _interrupt/_suspend" % self.citem.get('id'))
                    builder.pDialog = DIALOG._updateProgress(builder.pDialog, builder.pCount, message='%s: %s' % (LANGUAGE(32144), LANGUAGE(32213)), header=ADDON_NAME)
                    break

                bct = self.bctTypes.get(ftype, {})
                postIgnoreTypes = {'adverts': IGNORE_CHTYPE + MOVIE_CHTYPE,
                                   'trailers': IGNORE_CHTYPE}.get(ftype, IGNORE_CHTYPE)

                postFillRuntime = diffRuntime(runtime) if bct.get('auto', False) else MIN_EPG_DURATION

                if bct.get('enabled', False) and chtype not in postIgnoreTypes:
                    if bct.get('auto', False):
                        numberToFetch = bct.get('max', 0)
                    else:
                        numberToFetch = bct.get('min', 0)
                    if numberToFetch > 0:
                        postFileList.extend(self.getMulti(ftype, [chname, fgenre], numberToFetch, chanceBool(bct.get('chance', 0))))

            if postFileList:
                random.shuffle(postFileList)
                post_queue = deque(postFileList)
                postAuto = (self.bctTypes.get('adverts', {}).get('auto', False) or self.bctTypes.get('trailers', {}).get('auto', False))
                postCounter = 0
                total_available = len(post_queue)
                self.log('[%s] injectBCTs, post-roll current runtime %s, available content %s' % (self.citem.get('id'), runtime, total_available))

                iteration = 0
                while not builder.monitor.abortRequested() and postFillRuntime > 0 and post_queue:
                    iteration += 1
                    if service._interrupt() or service._suspend():
                        self.log("[%s] injectBCTs, _interrupt/_suspend" % self.citem.get('id'))
                        builder.pDialog = DIALOG._updateProgress(builder.pDialog, builder.pCount, message='%s: %s' % (LANGUAGE(32144), LANGUAGE(32213)), header=ADDON_NAME)
                        break

                    item = post_queue.popleft()
                    dur = item.get('duration', 0)
                    if dur == 0:
                        continue

                    if postAuto and postCounter >= total_available:
                        self.log('[%s] injectBCTs, unused post roll runtime %s %s/%s' % (self.citem.get('id'), postFillRuntime, postCounter, total_available))
                        break

                    if postFillRuntime >= dur:
                        postFillRuntime -= dur
                        self.log('[%s] injectBCTs, adding post-roll %s - %s' % (self.citem.get('id'), dur, item.get('file')))
                        builder.pDialog = DIALOG._updateProgress(builder.pDialog, builder.pCount, message='Filling Post-Rolls %s%%' % (int(iteration * 100 // max(1, total_available))), header='%s, %s' % (ADDON_NAME, getattr(builder, 'pMSG', '')))
                        item.update({'title'       : 'Post-Roll',
                                     'episodetitle': item.get('label'),
                                     'genre'       : ['Post-Roll'],
                                     'plot'        : item.get('plot', item.get('file')),
                                     'path'        : item.get('file')})
                        built = builder.buildCells(self.citem, dur, entries=1, info=item)
                        if built:
                            nfileList.append(built[0])
                    else:
                        post_queue.append(item)
                        postCounter += 1

        self.log('[%s] injectBCTs, finished' % (self.citem.get('id')))
        return nfileList