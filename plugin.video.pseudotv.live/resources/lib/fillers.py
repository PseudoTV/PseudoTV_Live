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

from typing import Any, Dict, List, Optional
from variables  import *
from resources  import Resources

class Fillers(object):


    def __init__(self, citem: Dict[str, Any] = {}, builder: Any = None):
        self.citem      = citem
        self.builder    = builder
        self.bctTypes   = builder.bctTypes
        self.runActions = builder.runActions
        self.jsonRPC    = builder.jsonRPC
        self.cache      = builder.cache
        self.trailers   = self.jsonRPC.getTrailers()
        self.service    = builder.service
        self.resources  = Resources(service=builder.service)
        self.processID  = Globals.properties.getProcessID()
        self.accurate   = bool(Globals.settings.getSettingInt('Duration_Type'))
        try:              self.fbuild = re.search(r'^(\d{2})\.', Globals.builtin.getInfoLabel("System.BuildVersion")).group(1)
        except Exception: self.fbuild = '22'
        if not self._hasFillerItems():
            self.fillSources()


    def _hasFillerItems(self) -> bool:
        for values in self.bctTypes.values():
            if not values.get('enabled', False): continue
            items = values.get('items', {})
            if items and any(isinstance(v, list) and v for v in items.values()):
                return True
        return False


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s' % (self.__class__.__name__, msg), level)


    def fillSources(self) -> Dict[str, Any]:
        def _build(ftype: str, path: str, checksum: str = ADDON_VERSION, expiration: datetime.timedelta = datetime.timedelta(minutes=15)) -> Dict[str, List[Dict[str, Any]]]:
            self.log('[%s] fillSources _build, type = %s, path = %s'%(self.citem.get('id'),ftype, path))
            data    = self.jsonRPC.walkFileDirectory(path, 'video', None, self.builder.limit, checksum, expiration)
            tmpDICT: Dict[str, List[Dict[str, Any]]] = {}
            for path, items in list(data.items()):
                if self.service.interrupt(): break
                for item in items:
                    if self.service.interrupt(): break
                    if not item.get('file'): continue
                    item['label']    = '%s - %s'%(path.strip('/').split('/')[-1:][0],os.path.split(item.get('file'))[1])
                    item['duration'] = self.jsonRPC.getDuration(item.get('file'), item, accurate=True, save=False)
                    if item['duration'] == 0: continue
                    tmpDICT.setdefault(path.lower(),[]).append(item)
                    [tmpDICT.setdefault(genre.lower(),[]).append(item) for genre in item.get('genre',[])] #breakdown genres if available
            return tmpDICT

        pDialog = getattr(self.builder, 'pDialog', None)
        pCount  = getattr(self.builder, 'pCount', 0)
        pMSG    = getattr(self.builder, 'pMSG', '')

        for ftype, values in list(self.bctTypes.items()):
            if self.service.interrupt(): break
            if not values.get('enabled', False): continue
            self.builder.pDialog = Globals.dialog._updateProgressThrottled(pDialog, pCount, message='%s %s' % (LANGUAGE(30014), ftype.title()), header='%s, %s' % (ADDON_NAME, pMSG))
            
            # resources
            for id in values.get("sources",{}).get("ids",[]):
                if self.service.interrupt(): break
                if not Globals.settings.hasAddon(id): continue
                values.setdefault('items',{}).update(_build(ftype, os.path.join('special://home/addons/%s'%id), Globals.settings.getAddonDetails(id).get('version',ADDON_VERSION), datetime.timedelta(days=MAX_GUIDEDAYS)))

            # vfs
            for path in values.get("sources", {}).get("paths",[]):
                if self.service.interrupt(): break
                values.setdefault('items',{}).update(_build(ftype, path))
                
            if values.get('incKODI', False):
                if   ftype.lower() == 'trailers': trailers = self.trailers.get('movies',{})
                elif ftype.lower() == 'adverts':  trailers = self.trailers.get('tvshows',{})
                else:                             trailers = {}
                for genre, items in trailers.items():
                    if self.service.interrupt(): break
                    for item in items:
                        if self.service.interrupt(): break
                        item['duration'] = self.jsonRPC.getDuration(item.get('file'), item, accurate=True, save=False)
                        if item['duration'] == 0: continue
                        values.setdefault('items',{}).setdefault(genre.lower(),[]).append(item)
        
            total = sum(len(item) for item in values.get('items', {}).values() if isinstance(item, list))
            self.log('fillSources, type = %s, items = %s' % (ftype, len(values['items'])))
        return values
        
        
    def convertMPAA(self, ompaa: str) -> str:
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


    def _getFillterItem(self, ftype: str, count: int = 1, keys: List[Any] = ['resources'], chance: bool = False, passes: Optional[int] = None) -> List[Dict[str, Any]]:
        tmpLST: List[Dict[str, Any]] = []
        filler = self.bctTypes.get(ftype, {})
        if passes is None: passes = count * len(keys)
        if passes <= 0: return tmpLST
        for key in keys:
            if not key: continue
            elif isinstance(key, list):
                tmpLST.extend(self._getFillterItem(ftype, count, key, Globals._chanceBool(filler.get('chance', 0)), passes))
                continue
            items = Globals._randomSamples(filler.get('items', {}).get(key.lower(),[]), count)
            tmpLST.extend(items)
            self.log('[%s] _getFillterItem [%s (%s)] %s/%s, total = %s, chance = %s'%(self.citem.get('id'), ftype, key, len(items), count, len(tmpLST), chance))
        
        if (len(tmpLST) < count and chance) and 'resources' not in keys:
            tmpLST.extend(self._getFillterItem(ftype, count, ['resources'], Globals._chanceBool(filler.get('chance', 0)), passes - 1))
        return tmpLST


    def _getExtras(self, fileItem: Dict[str, Any]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        try:# https://kodi.wiki/view/Video_extras
            if   'movieid'  in fileItem: items = self.getDirectory({"directory":'%s/%s'%(os.path.split(fileItem.get('file'))[0],'extras'),"media":'video'})
            elif 'tvshowid' in fileItem: items = self.jsonRPC.getEpisode(fileItem.get('tvshowid'),season=0)
        except Exception as e: self.log('_getExtras failed: %s' % e, xbmc.LOGDEBUG)
        self.log('[%s] _getExtras, items = %s'%(self.citem.get('id'), len(items)))
        return items
        


    def _getPreRoll(self, fileItem: Dict[str, Any]) -> List[Dict[str, Any]]:
        # pre roll - bumpers/ratings
        nfileList: List[Dict[str, Any]] = []
        for ftype in ['bumpers','ratings']:
            filler = self.bctTypes.get(ftype, {})
            ignore = {'bumpers': IGNORE_CHTYPE + MOVIE_CHTYPE, 'ratings': IGNORE_CHTYPE + TV_CHTYPE}[ftype]
            keys   = {'bumpers':[self.citem.get('name'), fileItem.get('genre'), self.citem.get('group',[]), self.fbuild],'ratings':[(self.convertMPAA(fileItem.get('mpaa')) or 'NR'), (fileItem.get('streamdetails',{}).get('audio') or [{}])[0].get('codec','')]}[ftype]
            if filler.get('enabled', False) and self.citem.get('type') not in ignore:
                items = self._getFillterItem(ftype, 1, keys, Globals._chanceBool(filler.get('chance', 0)))
                # iterate and add pre-rolls
                for i, item in enumerate(items):
                    dur = item.get('duration', 0)
                    if not item.get('file') or dur == 0: continue
                    self.builder.pDialog = Globals.dialog._updateProgressThrottled(self.builder.pDialog, self.builder.pCount, message='Filling Pre-Rolls %s%%' % (int((i + 1) * 100 // max(1, len(items)))), header='%s, %s' % (ADDON_NAME, getattr(self.builder, 'pMSG', '')))
                    item.update({'title'       : item.get('label'),
                                 'episodetitle': 'Pre-Roll',
                                 'plot'        : item.get('plot', item.get('file')),
                                 'genre'       : ['Fillers','Pre-Roll'],
                                 'path'        : item.get('file'),
                                 'art'         : {"thumb":LOGO,"poster":LOGO_POSTER,"fanart":LOGO_LANDSCAPE,"landscape":LOGO_LANDSCAPE,"logo":LOGO,"icon":LOGO}})
                    self.log('[%s] injectFillers [%s: Pre-Roll (%s)] %s, %s'%(self.citem.get('id'), i, ftype, dur, item.get('file')))
                    nfileList.extend(self.builder.buildCells(self.citem, dur, entries=1, info=item))
        return Globals._setDictLST(nfileList)
        
        
    def _getPostRoll(self, fileItem: Dict[str, Any], nextItem: Dict[str, Any] = {}, remaining_seconds: int = 0) -> List[Dict[str, Any]]:
        # post roll - adverts/trailers/extras
        items: List[Dict[str, Any]] = []
        nfileList: List[Dict[str, Any]] = []
        for ftype in ['adverts', 'trailers', 'extras']:
            filler = self.bctTypes.get(ftype, {})
            ignore = {'adverts': IGNORE_CHTYPE + MOVIE_CHTYPE, 'trailers': IGNORE_CHTYPE + TV_CHTYPE}.get(ftype, IGNORE_CHTYPE)
            if filler.get('enabled', False) and self.citem.get('type') not in ignore:
                if filler.get('auto', False): numberToFetch = filler.get('max',self.builder.limit)
                else:                         numberToFetch = filler.get('min',Globals.settings.getSettingInt('Enable_Postroll'))
                for item in [fileItem, nextItem]:
                    if not item: continue
                    keys = [self.citem.get('name',''), item.get('genre',''), self.citem.get('group',[])]
                    if numberToFetch > 0:
                        items.extend(self._getFillterItem(ftype, numberToFetch, keys, Globals._chanceBool(filler.get('chance', 0))))
                    if ftype == 'extras' and filler.get('incKODI',False) and ('movieid' in item or 'tvshowid' in item):
                        items.extend(self._getExtras(item))
                        
        if items:
            iteration     = 0
            post_counter  = 0
            post_queue    = deque(Globals._randomShuffle(Globals._setDictLST(items)))
            post_auto     = (self.bctTypes.get('adverts', {}).get('auto', False) or self.bctTypes.get('trailers', {}).get('auto', False))
            total_queue   = len(post_queue)
            post_runtime  = remaining_seconds if post_auto else MIN_EPG_DURATION
            while not self.builder.monitor.abortRequested() and post_runtime > 0 and post_queue and post_counter < total_queue:
                iteration += 1
                item = post_queue.popleft()
                dur  = item.get('duration', 0)
                if 0 < dur <= post_runtime:
                    post_counter = 0
                    post_runtime -= dur
                    self.builder.pDialog = Globals.dialog._updateProgressThrottled(self.builder.pDialog, self.builder.pCount, message='Filling Post-Rolls %s%%' % (int(iteration * 100 // max(1, total_queue))), header='%s, %s' % (ADDON_NAME, getattr(self.builder, 'pMSG', '')))
                    item.update({'title'       : item.get('label'),
                                 'episodetitle': 'Post-Roll',
                                 'plot'        : item.get('plot', item.get('file')),
                                 'genre'       : ['Fillers','Post-Roll'],
                                 'path'        : item.get('file')})
                    self.log('[%s] injectFillers [%s: Post-Roll (%s/%s)] %s, %s'%(self.citem.get('id'), iteration, post_runtime, remaining_seconds, dur, item.get('file')))
                    nfileList.extend(self.builder.buildCells(self.citem, dur, entries=1, info=item))
                else:
                    post_queue.append(item)
                    post_counter += 1
        return nfileList
        


    def injectFillers(self, fileList: List[Dict[str, Any]], slot_size_mins: int = 30) -> List[Dict[str, Any]]:
        self.log('[%s] injectFillers, IN fileList = %s'%(self.citem.get('id'), len(fileList)))
        nfileList: List[Dict[str, Any]] = []
        SLOT_SEC  = slot_size_mins * 60
        runtime   = fileList[0]['start']
        for i in range(len(fileList)):
            if self.service.interrupt(): 
                return nfileList + fileList[i + 1:]
            fileItem = fileList[i]
            if not fileItem: continue
            duration = fileItem.get('duration', 0)
            if duration == 0: continue
                
            #Pre-Rolls
            prerolls = self._getPreRoll(fileItem)
            for item in prerolls:
                item_dur = item.get('duration', 0)
                item['start'] = runtime
                runtime += item_dur
                item['stop'] = runtime
                nfileList.append(item)
                
            #Main Media
            fileItem['start'] = runtime
            runtime += duration
            fileItem['stop'] = runtime
            nfileList.append(fileItem)
            self.log('[%s] injectFillers [%s: Media (%s)] %s, %s'%(self.citem.get('id'), i, fileItem.get('type'), fileItem.get('duration'), fileItem.get('file')))
            
            #Post-Rolls
            next_duration = fileList[i+1].get('duration', 0) if i + 1 < len(fileList) else 0
            if next_duration > 0:
                next_fileitem = fileList[i+1]
                total_runtime = runtime + next_duration
                next_grid_boundary = ((total_runtime + SLOT_SEC - 1) // SLOT_SEC) * SLOT_SEC
                gap_seconds = next_grid_boundary - total_runtime
                if gap_seconds > 0:
                    postrolls = self._getPostRoll(fileItem, next_fileitem, gap_seconds)
                    for item in postrolls:
                        item['start'] = runtime
                        runtime += item.get('duration', 0)
                        item['stop'] = runtime
                        nfileList.append(item)
            else:
                next_grid_boundary = ((runtime + SLOT_SEC - 1) // SLOT_SEC) * SLOT_SEC
                final_gap = next_grid_boundary - runtime
                if final_gap > 0:
                    postrolls = self._getPostRoll(fileItem, {}, final_gap)
                    for item in postrolls:
                        item['start'] = runtime
                        runtime += item.get('duration', 0)
                        item['stop'] = runtime
                        nfileList.append(item)
        self.log('[%s] injectFillers, OUT fileList = %s'%(self.citem.get('id'), len(nfileList)))
        return nfileList
