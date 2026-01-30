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
    def __init__(self, builder):
        self.builder    = builder
        self.bctTypes   = builder.bctTypes
        self.runActions = builder.runActions
        self.jsonRPC    = builder.jsonRPC
        self.cache      = builder.jsonRPC.cache
        self.resources  = Resources(service=builder.service)
        self.fillSources(builder.bctTypes)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)


    def fillSources(self, bctTypes=None):
        if bctTypes is None:
            bctTypes = self.bctTypes

        # Local references for speed
        builder = self.builder
        pDialog = getattr(builder, 'pDialog', None)
        pCount  = getattr(builder, 'pCount', 0)
        pMSG    = getattr(builder, 'pMSG', '')

        for ftype, values in bctTypes.items():
            if not values.get('enabled', False):
                continue

            # single update call per type (avoid heavy formatting inside loops)
            builder.pDialog = DIALOG._updateProgress(pDialog, pCount,
                                                     message='%s %s' % (LANGUAGE(30014), ftype.title()),
                                                     header='%s, %s' % (ADDON_NAME, pMSG))
            # include KODI trailers if requested
            if values.get('incKODI', False):
                # mergeDictLST returns a new dict/list structure; call only when needed
                values["items"] = mergeDictLST(values.get('items', {}), builder.getTrailers())

            # parse resource packs (ids)
            ids = values.get("sources", {}).get("ids", ())
            for id_ in ids:
                values['items'] = mergeDictLST(values.get('items', {}), self.buildSource(ftype, id_))

            # parse paths (vfs/local)
            paths = values.get("sources", {}).get("paths", ())
            for path in paths:
                values['items'] = mergeDictLST(values.get('items', {}), self.buildSource(ftype, path))

            # canonicalize items
            values['items'] = Globals._setDictLST(values['items'])
            self.log('fillSources, type = %s, items = %s' % (ftype, len(values['items'])))

    @cacheit(expiration=datetime.timedelta(minutes=30), json_data=False)
    def buildSource(self, ftype, path=''):
        # Localize frequently used names
        self.log('buildSource, type = %s, path = %s' % ( ftype, path))
        jsonRPC = self.jsonRPC
        settings = SETTINGS
        file_access = FileAccess

        def _parseResource(id_):
            # resources inside addon: <addon>/resources
            try:
                if settings.hasAddon(id_, install=True):
                    res_path = os.path.join('special://home/addons', id_, 'resources')
                    return jsonRPC.walkListDirectory(res_path, exts=VIDEO_EXTS, depth=CHANNEL_LIMIT, checksum=False)
            except Exception:
                return {}
            return {}

        def _parseVFS(p):
            # plugin:// paths or other vfs types
            try:
                if p.startswith('plugin://'):
                    # settings.hasAddon may accept addon id; original code checked install - keep guard
                    if not settings.hasAddon(p, install=True):
                        return {}
                return jsonRPC.walkFileDirectory(escapeDirJSON(p), depth=CHANNEL_LIMIT, chkDuration=True, retItem=True)
            except Exception:
                return {}

        def _parseLocal(p):
            try:
                if file_access.exists(p):
                    return jsonRPC.walkListDirectory(p, exts=VIDEO_EXTS, depth=CHANNEL_LIMIT, chkDuration=True)
            except Exception:
                return {}
            return {}

        def __sortItems(data, stype='folder'):
            tmpDCT = {}
            if not data:
                self.log('buildSource, __sortItems: stype = %s, items = %s' % (stype, 0))
                return tmpDCT

            # Iterate once; compute basename/key once per path
            for path_key, files in data.items():
                # Normalize path_key and compute folder key
                try:
                    # base name for folder type keying
                    folder_key = os.path.basename(os.path.normpath(path_key)).replace('\\', '/').strip('/').split('/')[-1].lower()
                except Exception:
                    folder_key = path_key.lower()

                if not files:
                    continue

                for file in files:
                    # If the file is already a dict (pre-built item), use its genre(s).
                    if isinstance(file, dict):
                        genres = file.get('genre') or ['resources']
                        for g in genres:
                            tmpDCT.setdefault(g.lower(), []).append(file)
                        continue

                    # file is a filename string
                    if stype == 'file':
                        key = file.split('.')[0].lower()
                    else:
                        key = folder_key

                    fullpath = os.path.join(path_key, file)
                    # getDuration is expensive -> keep call minimal and only once
                    dur = jsonRPC.getDuration(fullpath, accurate=True)
                    if dur and dur > 0:
                        label = '%s - %s' % (os.path.basename(path_key).strip('/').split('/')[-1], os.path.splitext(file)[0])
                        tmpDCT.setdefault(key.lower(), []).append({'file': fullpath, 'duration': dur, 'label': label})

            self.log('buildSource, __sortItems: stype = %s, items = %s' % (stype, len(tmpDCT)))
            return tmpDCT

        try:
            # Decide parser based on path prefix
            if path.startswith('resource.'):
                return __sortItems(_parseResource(path))
            elif path.startswith(tuple(VFS_TYPES + DB_TYPES)):
                return __sortItems(_parseVFS(path))
            else:
                return __sortItems(_parseLocal(path))
        except Exception as e:
            self.log("buildSource, failed! %s\n path = %s" % (e, path), xbmc.LOGERROR)
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
        return (mpaa.replace('TV-Y', 'G')
                    .replace('TV-Y7', 'G')
                    .replace('TV-G', 'G')
                    .replace('NA', 'NR')
                    .replace('TV-PG', 'PG')
                    .replace('TV-14', 'PG-13')
                    .replace('TV-MA', 'R'))

    def getSingle(self, type_, keys=None, chance=False):
        if keys is None:
            keys = ['resources']

        candidates = []
        bt = self.bctTypes.get(type_, {}).get('items', {})
        for key in keys:
            lst = bt.get(key.lower(), [])
            if lst:
                candidates.append(random.choice(lst))

        if not candidates and chance:
            candidates.extend(self.getSingle(type_, chance=False) or [])

        self.log('getSingle, type = %s, keys = %s, chance = %s, returning = %s' %
                 (type_, keys, chance, len(candidates)))
        return Globals._setDictLST(candidates)

    def getMulti(self, type_, keys=None, count=1, chance=False):
        if keys is None:
            keys = ['resources']

        bt = self.bctTypes.get(type_, {}).get('items', {})
        tmpLST = []
        for key in keys:
            tmpLST.extend(bt.get(key.lower(), []))

        items = []
        if tmpLST:
            if len(tmpLST) >= count:
                items = random.sample(tmpLST, count)
            else:
                items = Globals._setDictLST(random.choices(tmpLST, k=count))

        if len(items) < count and chance:
            needed = count - len(items)
            items.extend(self.getMulti(type_, count=needed))

        self.log('getMulti, type = %s, keys = %s, count = %s, chance = %s, returning = %s' %
                 (type_, keys, count, chance, len(items)))
        return Globals._setDictLST(items)

    def injectBCTs(self, citem, fileList):
        # Optimize hot-path by localizing attributes and using deque for post-rolls
        nfileList = []
        builder = self.builder
        service = builder.service
        bctTypes = self.bctTypes
        citem_id = citem.get('id')
        ignore_cht = IGNORE_CHTYPE
        movie_types = MOVIE_TYPES
        tv_types = TV_TYPES

        for idx, fileItem in enumerate(fileList):
            if service._interrupt():
                # return the rest of the list untouched
                return nfileList + fileList[idx + 1:]
            if not fileItem:
                continue

            runtime = fileItem.get('duration', 0)
            if runtime == 0:
                continue

            chtype = citem.get('type', '')
            chname = citem.get('name', '')
            fitem = fileItem  # don't copy unless necessary
            dbtype = fileItem.get('type', '')
            fmpaa = (self.convertMPAA(fileItem.get('mpaa')) or 'NR')
            fcodec = (fileItem.get('streamdetails', {}).get('audio') or [{}])[0].get('codec', '')
            fgenre = (fileItem.get('genre') or citem.get('group') or '')
            if isinstance(fgenre, list) and fgenre:
                fgenre = fgenre[0]

            # pre roll - bumpers/ratings
            ftype = None
            preKeys = []
            if dbtype.startswith(tuple(movie_types)):
                ftype = 'ratings'
                preKeys = [fmpaa, fcodec]
            elif dbtype.startswith(tuple(tv_types)):
                ftype = 'bumpers'
                preKeys = [chname, fgenre]

            if ftype:
                preFileList = []
                bct = bctTypes.get(ftype, {})
                if bct.get('enabled', False) and chtype not in ignore_cht:
                    preFileList = self.getSingle(ftype, preKeys, chanceBool(bct.get('chance', 0)))

                # iterate and add pre-rolls
                for i, item in enumerate(Globals._setDictLST(preFileList)):
                    if service._interrupt() or service._suspend():
                        self.log("[%s] injectBCTs, _interrupt/_suspend" % citem_id)
                        builder.pDialog = DIALOG._updateProgress(builder.pDialog, builder.pCount,
                                                                 message='%s: %s' % (LANGUAGE(32144), LANGUAGE(32213)),
                                                                 header=ADDON_NAME)
                        break
                    dur = item.get('duration', 0)
                    if dur > 0:
                        runtime += dur
                        self.log('[%s] injectBCTs, adding pre-roll %s - %s' % (citem_id, dur, item.get('file')))
                        # Update progress infrequently; keep message simple
                        builder.pDialog = DIALOG._updateProgress(builder.pDialog, builder.pCount,
                                                                 message='Filling Pre-Rolls %s%%' % (int((i + 1) * 100 // max(1, len(preFileList)))),
                                                                 header='%s, %s' % (ADDON_NAME, getattr(builder, 'pMSG', '')))
                        item.update({'title': 'Pre-Roll',
                                     'episodetitle': item.get('label'),
                                     'genre': ['Pre-Roll'],
                                     'plot': item.get('plot', item.get('file')),
                                     'path': item.get('file')})
                        built = builder.buildCells(citem, dur, entries=1, info=item)
                        if built:
                            nfileList.append(built[0])

            # original media
            nfileList.append(fileItem)
            self.log('[%s] injectBCTs, adding media %s - %s' % (citem_id, fileItem.get('duration'), fileItem.get('file')))

            # post roll - adverts/trailers
            postFileList = []
            ftypes = ['adverts', 'trailers']
            for ftype in ftypes:
                if service._interrupt() or service._suspend():
                    self.log("[%s] injectBCTs, _interrupt/_suspend" % citem_id)
                    builder.pDialog = DIALOG._updateProgress(builder.pDialog, builder.pCount,
                                                             message='%s: %s' % (LANGUAGE(32144), LANGUAGE(32213)),
                                                             header=ADDON_NAME)
                    break

                bct = bctTypes.get(ftype, {})
                postIgnoreTypes = {'adverts': ignore_cht + MOVIE_CHTYPE,
                                   'trailers': ignore_cht}.get(ftype, ignore_cht)

                # determine how much runtime we can fill after the media; compute once
                postFillRuntime = diffRuntime(runtime) if bct.get('auto', False) else MIN_EPG_DURATION

                if bct.get('enabled', False) and chtype not in postIgnoreTypes:
                    # numberToFetch either auto-based max or configured min
                    if bct.get('auto', False):
                        numberToFetch = bct.get('max', 0)
                    else:
                        numberToFetch = bct.get('min', 0)
                    if numberToFetch > 0:
                        postFileList.extend(self.getMulti(ftype, [chname, fgenre], numberToFetch, chanceBool(bct.get('chance', 0))))

            # Efficient consumption: use deque for O(1) pops from left
            if postFileList:
                random.shuffle(postFileList)
                post_queue = deque(postFileList)
                postAuto = (bctTypes.get('adverts', {}).get('auto', False) or bctTypes.get('trailers', {}).get('auto', False))
                postCounter = 0
                total_available = len(post_queue)
                self.log('[%s] injectBCTs, post-roll current runtime %s, available content %s' % (citem_id, runtime, total_available))

                iteration = 0
                while not builder.monitor.abortRequested() and postFillRuntime > 0 and post_queue:
                    iteration += 1
                    if service._interrupt() or service._suspend():
                        self.log("[%s] injectBCTs, _interrupt/_suspend" % citem_id)
                        builder.pDialog = DIALOG._updateProgress(builder.pDialog, builder.pCount,
                                                                 message='%s: %s' % (LANGUAGE(32144), LANGUAGE(32213)),
                                                                 header=ADDON_NAME)
                        break

                    item = post_queue.popleft()
                    dur = item.get('duration', 0)
                    if dur == 0:
                        continue

                    # if auto and we've looped more than available, break to avoid infinite loop
                    if postAuto and postCounter >= total_available:
                        self.log('[%s] injectBCTs, unused post roll runtime %s %s/%s' % (citem_id, postFillRuntime, postCounter, total_available))
                        break

                    if postFillRuntime >= dur:
                        postFillRuntime -= dur
                        self.log('[%s] injectBCTs, adding post-roll %s - %s' % (citem_id, dur, item.get('file')))
                        builder.pDialog = DIALOG._updateProgress(builder.pDialog, builder.pCount,
                                                                 message='Filling Post-Rolls %s%%' % (int(iteration * 100 // max(1, total_available))),
                                                                 header='%s, %s' % (ADDON_NAME, getattr(builder, 'pMSG', '')))
                        item.update({'title': 'Post-Roll',
                                     'episodetitle': item.get('label'),
                                     'genre': ['Post-Roll'],
                                     'plot': item.get('plot', item.get('file')),
                                     'path': item.get('file')})
                        built = builder.buildCells(citem, dur, entries=1, info=item)
                        if built:
                            nfileList.append(built[0])
                    else:
                        # not enough space now; append back and count attempt
                        post_queue.append(item)
                        postCounter += 1

        self.log('[%s] injectBCTs, finished' % (citem.get('id')))
        return nfileList