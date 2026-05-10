#   Copyright (C) 2026 Lunatixz
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
        self.service    = builder.service
        self.resources  = Resources(service=builder.service)
        self.processID  = PROPERTIES.getProcessID()
        self.accurate   = bool(SETTINGS.getSettingInt('Duration_Type'))
        self.fillSources()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)


    def fillSources(self):
        def _build(ftype, path, checksum=ADDON_VERSION, expiration=datetime.timedelta(minutes=15)):
            self.log('[%s] fillSources _build, type = %s, path = %s'%(self.citem.get('id'),ftype, path))
            data    = self.jsonRPC.walkFileDirectory(path, 'video', None, PAGE_LIMIT, checksum, expiration)
            tmpDICT = {}
            for path, items in list(data.items()):
                if not self.service._interrupt():
                    for item in items:
                        if self.service._interrupt(): break
                        elif not item.get('file'): continue
                        else:
                            item['label']    = '%s - %s'%(path.strip('/').split('/')[-1:][0],os.path.split(item.get('file'))[1])
                            item['duration'] = self.jsonRPC.getDuration(item.get('file'), item, accurate=True, save=False)
                            if item['duration'] == 0: continue
                            tmpDICT.setdefault(path,[]).append(item)
                            [tmpDICT.setdefault(genre,[]).append(item) for genre in item.get('genre',[])] #breakdown genres if available
            return tmpDICT

        pDialog = getattr(self.builder, 'pDialog', None)
        pCount  = getattr(self.builder, 'pCount', 0)
        pMSG    = getattr(self.builder, 'pMSG', '')

        for ftype, values in self.bctTypes.items():
            if not values.get('enabled', False): continue
            self.builder.pDialog = DIALOG._updateProgress(pDialog, pCount, message='%s %s' % (LANGUAGE(30014), ftype.title()), header='%s, %s' % (ADDON_NAME, pMSG))
            
            # kodi trailers
            if values.get('incKODI', False):
                trailers = self.builder.getTrailers(ftype)
                for genre, items in list(trailers.items()):
                    if not self.service._interrupt():
                        for item in items:
                            if self.service._interrupt(): break
                            else:
                                item['duration'] = self.jsonRPC.getDuration(item.get('file'), item, accurate=True, save=False)
                                if item['duration'] == 0: continue
                                values.setdefault('items',{}).setdefault(genre,[]).append(item)
                                    
            # resources
            for id in values.get("sources",{}).get("ids",[]):
                if self.service._interrupt(): break
                elif not SETTINGS.hasAddon(id): continue
                else: 
                    values.setdefault('items',{}).update(_build(ftype, os.path.join('special://home/addons/%s'%id), SETTINGS.getAddonDetails(id).get('version',ADDON_VERSION), datetime.timedelta(days=MAX_GUIDEDAYS)))

            # vfs
            for path in values.get("sources", {}).get("paths",[]):
                if self.service._interrupt(): break
                else: values.setdefault('items',{}).update(_build(ftype, path))
                
            self.log('fillSources, type = %s, items = %s' % (ftype, len(values['items'])))
            return values
        
        
    def convertMPAA(self, ompaa):
        #todo robust ratings system supporting international rating systems.
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


    def getFillterItem(self, type, count=1, keys=['resources'], chance=False):
        tmpLST = []
        for key in keys:
            items = Globals._randomSamples(self.bctTypes.get(type,{}).get('items', {}).get(key,[]), count)
            if not items and chance: items.extend(self.getFillterItem(type,count,['resources']))
            tmpLST.extend(items)
        self.log('[%s] getFillterItem, type = %s, count = %s, keys = %s, chance = %s, returning = %s' % (self.citem.get('id'),type, count, keys, chance, len(tmpLST)))
        return [i for i in tmpLST if i]


    def injectBCTs(self, fileList):
        nfileList = []
        for idx, fileItem in enumerate(fileList):
            if self.service._interrupt(): return nfileList + fileList[idx + 1:]
            elif not fileItem: continue
            runtime = fileItem.get('duration',0)
            if runtime == 0: continue

            chtype = self.citem.get('type', '')
            chname = self.citem.get('name', '')
            fitem  = fileItem  # don't copy unless necessary
            dbtype = fileItem.get('type', '')
            fmpaa  = (self.convertMPAA(fileItem.get('mpaa')) or 'NR')
            fcodec = (fileItem.get('streamdetails', {}).get('audio') or [{}])[0].get('codec', '')
            fgenre = (fileItem.get('genre') or self.citem.get('group') or '')
            fbuild = BUILTIN.getInfoLabel("System.BuildVersionCode").split('.')[0]
            
            if isinstance(fgenre, list) and fgenre:
                fgenre = fgenre[0]

            # pre roll - bumpers/ratings
            ftype   = None
            preKeys = []
            if dbtype.startswith(tuple(TV_TYPES)):
                ftype   = 'bumpers'
                preKeys = [chname, fgenre, fbuild]
            elif dbtype.startswith(tuple(MOVIE_TYPES)):
                ftype   = 'ratings'
                preKeys = [fmpaa, fcodec]

            if ftype:
                preFileList = []
                fillerItem  = self.bctTypes.get(ftype, {})
                if fillerItem.get('enabled', False) and chtype not in IGNORE_CHTYPE:
                    preFileList = self.getFillterItem(ftype, 1, preKeys, chanceBool(fillerItem.get('chance', 0)))
                    preFileList = Globals._setDictLST(preFileList)
                    # iterate and add pre-rolls
                    for i, item in enumerate(preFileList):
                        if self.service._interrupt():
                            self.log("[%s] injectBCTs, _interrupt" % self.citem.get('id'))
                            self.builder.pDialog = DIALOG._updateProgress(self.builder.pDialog, self.builder.pCount, message='%s: %s' % (LANGUAGE(32144), LANGUAGE(32213)), header=ADDON_NAME)
                            break
                        elif not item.get('file'): continue
                        dur = item.get('duration', 0)
                        if dur > 0:
                            runtime += dur
                            self.log('[%s] injectBCTs, adding pre-roll %s - %s' % (self.citem.get('id'), dur, item.get('file')))
                            self.builder.pDialog = DIALOG._updateProgress(self.builder.pDialog, self.builder.pCount, message='Filling Pre-Rolls %s%%' % (int((i + 1) * 100 // max(1, len(preFileList)))), header='%s, %s' % (ADDON_NAME, getattr(self.builder, 'pMSG', '')))
                            item.update({'title'       : 'Pre-Roll',
                                         'episodetitle': item.get('label'),
                                         'genre'       : ['Pre-Roll'],
                                         'plot'        : item.get('plot', item.get('file')),
                                         'path'        : item.get('file')})
                            nfileList.extend(self.builder.buildCells(self.citem, dur, entries=1, info=item))
                            self.log('[%s] injectBCTs, adding pre-roll %s - %s' % (self.citem.get('id'), item.get('duration'), item.get('file')))

            # original media
            nfileList.append(fileItem)
            self.log('[%s] injectBCTs, adding media %s - %s' % (self.citem.get('id'), fileItem.get('duration'), fileItem.get('file')))

            # post roll - adverts/trailers
            postFileList = []
            for ftype in ['adverts', 'trailers']:
                if self.service._interrupt():
                    self.log("[%s] injectBCTs, _interrupt" % self.citem.get('id'))
                    self.builder.pDialog = DIALOG._updateProgress(self.builder.pDialog, self.builder.pCount, message='%s: %s' % (LANGUAGE(32144), LANGUAGE(32213)), header=ADDON_NAME)
                    break
                else:
                    fillerItem      = self.bctTypes.get(ftype, {})
                    postIgnoreTypes = {'adverts': IGNORE_CHTYPE + MOVIE_CHTYPE, 'trailers': IGNORE_CHTYPE}.get(ftype, IGNORE_CHTYPE)
                    postFillRuntime = diffRuntime(runtime) if fillerItem.get('auto', False) else MIN_EPG_DURATION

                    if fillerItem.get('enabled', False) and chtype not in postIgnoreTypes:
                        if fillerItem.get('auto', False): numberToFetch = fillerItem.get('max',PAGE_LIMIT)
                        else:                             numberToFetch = fillerItem.get('min',SETTINGS.getSettingInt('Enable_Postroll'))
                        if numberToFetch > 0: postFileList.extend(self.getFillterItem(ftype, numberToFetch, [chname, fgenre], chanceBool(fillerItem.get('chance', 0))))

            if postFileList:
                post_queue   = deque(Globals._randomShuffle(Globals._setDictLST(postFileList)))
                postAuto     = (self.bctTypes.get('adverts', {}).get('auto', False) or self.bctTypes.get('trailers', {}).get('auto', False))
                postCounter  = 0
                total_available = len(post_queue)
                self.log('[%s] injectBCTs, post-roll current runtime %s, available content %s' % (self.citem.get('id'), runtime, total_available))

                iteration = 0
                while not self.builder.monitor.abortRequested() and postFillRuntime > 0 and post_queue:
                    iteration += 1
                    if self.service._interrupt():
                        self.log("[%s] injectBCTs, _interrupt" % self.citem.get('id'))
                        self.builder.pDialog = DIALOG._updateProgress(self.builder.pDialog, self.builder.pCount, message='%s: %s' % (LANGUAGE(32144), LANGUAGE(32213)), header=ADDON_NAME)
                        break
                    else:
                        item = post_queue.popleft()
                        dur  = item.get('duration', 0)
                        if dur == 0: continue

                        if postAuto and postCounter >= total_available:
                            self.log('[%s] injectBCTs, unused post roll runtime %s %s/%s' % (self.citem.get('id'), postFillRuntime, postCounter, total_available))
                            break
                            
                        if postFillRuntime >= dur:
                            postFillRuntime -= dur
                            self.log('[%s] injectBCTs, adding post-roll %s - %s' % (self.citem.get('id'), dur, item.get('file')))
                            self.builder.pDialog = DIALOG._updateProgress(self.builder.pDialog, self.builder.pCount, message='Filling Post-Rolls %s%%' % (int(iteration * 100 // max(1, total_available))), header='%s, %s' % (ADDON_NAME, getattr(builder, 'pMSG', '')))
                            item.update({'title'       : 'Post-Roll',
                                         'episodetitle': item.get('label'),
                                         'genre'       : ['Post-Roll'],
                                         'plot'        : item.get('plot', item.get('file')),
                                         'path'        : item.get('file')})
                            nfileList.append(self.builder.buildCells(self.citem, dur, entries=1, info=item)[0])
                        else:
                            post_queue.append(item)
                            postCounter += 1
        self.log('[%s] injectBCTs, finished' % (self.citem.get('id')))
        return nfileList