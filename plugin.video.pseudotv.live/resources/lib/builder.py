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
from channels   import Channels
from xmltvs     import XMLTVS
from xsp        import XSP
from m3u        import M3U
from fillers    import Fillers
from resources  import Resources
from seasonal   import Seasonal 
from rules      import RulesList
from seasonal   import Seasonal

class Service(object):
    from jsonrpc import JSONRPC
    jsonRPC = JSONRPC()
    player  = PLAYER()
    monitor = MONITOR()
    def _shutdown(self, wait=CPU_CYCLE) -> bool:
        return PROPERTIES.isPendingShutdown() or self.monitor.waitForAbort(wait)
    def _restart(self) -> bool:
        return PROPERTIES.isPendingRestart()
    def _interrupt(self) -> bool:
        any(PROPERTIES.isPendingSuspend(),BUILTIN.isSettingsOpened())
    def _suspend(self) -> bool:
        return any(PROPERTIES.isPendingSuspend(),BUILTIN.isSettingsOpened())
    def _sleep(self, wait=CPU_CYCLE):
        while not self.monitor.abortRequested() and wait > 0:
            if any(self.monitor.waitForAbort(CPU_CYCLE), self._interrupt()):
                return True
            wait -= CPU_CYCLE
        return False

class Builder(object):
    xsp      = XSP()
    m3u      = M3U(writable=True)
    xmltv    = XMLTVS(writable=True, m3u=m3u)
    seasonal = Seasonal()
    loopback = None
    
    def __init__(self, service=None):
        self.service  = service if service is not None else Service()
        self.monitor  = self.service.monitor
        self.jsonRPC  = self.service.jsonRPC
        self.cache    = self.service.jsonRPC.cache
        self.holiday  = self.seasonal.getHoliday()
        self.channels = Channels(writable=True)
        
        # Global dialog properties
        self.fCount  = 0
        self.pCount  = 0
        self.cCount  = 0
        self.pDialog = None
        self.pMSG    = ''
        self.pName   = ''
        self.pHeader = ''
        self.pErrors = []
        
        # Global rules setup
        self.accurateDuration = bool(SETTINGS.getSettingInt('Duration_Type'))
        self.interleaveSet    = SETTINGS.getSettingInt('Interleave_Set')
        self.interleaveRepeat = SETTINGS.getSettingBool('Interleave_Repeat')
        self.incStrms         = SETTINGS.getSettingBool('Enable_Strms')
        self.inc3D            = SETTINGS.getSettingBool('Enable_3D')
        self.incExtras        = SETTINGS.getSettingBool('Enable_Extras') 
        self.incStrmDetails   = SETTINGS.getSettingBool('Enable_Details')
        self.enableBCTs       = SETTINGS.getSettingBool('Enable_Fillers')
        self.saveDuration      = SETTINGS.getSettingBool('Store_Duration')
        self.minDuration      = SETTINGS.getSettingInt('Seek_Tolerance')
        self.limit            = SETTINGS.getSettingInt('Page_Limit')
        self.recursiveLimit   = SETTINGS.getSettingInt('Recursive_Depth')
        self.padScheduling    = False 
        self.padFilelist      = False 
        self.enableEven       = bool(SETTINGS.getSettingInt('Enable_Even'))
        self.evenEpisode      = SETTINGS.getSettingBool('Enable_Even_Force_Episode')
        self.evenShuffle      = SETTINGS.getSettingBool('Enable_Even_Force_Random')
        self.enableChanged    = SETTINGS.getSettingBool('Enable_Changed')
        
        self.filter           = {}
        self.sort             = {}
        self.limits           = {"end": -1, "start": 0, "total": 0}
        self.query            = {}
        
        # Pre-cache constant configuration lookups to minimize setting poll overhead
        preroll_max = SETTINGS.getSettingInt('Enable_Preroll')
        postroll_min = SETTINGS.getSettingInt('Enable_Postroll')
        post_chance = SETTINGS.getSettingInt('Random_Post_Chance')
        include_trailers = SETTINGS.getSettingBool('Include_Trailers_KODI')

        self.bctTypes = {
            "bumpers": {
                "min": -1, "max": preroll_max, "auto": preroll_max == -1, "enabled": bool(preroll_max), 
                "chance": SETTINGS.getSettingInt('Random_Pre_Chance'),
                "sources": {"ids": SETTINGS.getSetting('Resource_Bumpers').split('|'), "paths": [os.path.join(FILLER_LOC, 'Bumpers', '')]}, "items": {}
            },
            "ratings": {
                "min": -1, "max": preroll_max, "auto": preroll_max == -1, "enabled": bool(preroll_max), 
                "chance": SETTINGS.getSettingInt('Random_Pre_Chance'),
                "sources": {"ids": SETTINGS.getSetting('Resource_Ratings').split('|'), "paths": [os.path.join(FILLER_LOC, 'Ratings', '')]}, "items": {}
            },
            "adverts": {
                "min": postroll_min, "max": PAGE_LIMIT, "auto": postroll_min == -1, "enabled": bool(postroll_min), 
                "chance": post_chance,
                "sources": {"ids": SETTINGS.getSetting('Resource_Adverts').split('|'), "paths": [os.path.join(FILLER_LOC, 'Adverts', '')]}, "items": {}, "incKODI": include_trailers
            },
            "trailers": {
                "min": postroll_min, "max": PAGE_LIMIT, "auto": postroll_min == -1, "enabled": bool(postroll_min), 
                "chance": post_chance,
                "sources": {"ids": SETTINGS.getSetting('Resource_Trailers').split('|'), "paths": [os.path.join(FILLER_LOC, 'Trailers', '')]}, "items": {}, "incKODI": include_trailers
            },
            "extras": {
                "min": postroll_min, "max": PAGE_LIMIT, "auto": postroll_min == -1, "enabled": bool(postroll_min), 
                "chance": post_chance,
                "sources": {"ids": [], "paths": []}, "items": {}, "incKODI": SETTINGS.getSettingBool('Include_Extras_KODI')
            }
        }

        self.resources  = Resources(service=self.service)
        self.runActions = RulesList(self.channels.getChannels()).runActions


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)
        

    def getVerifiedChannels(self, channels=None):
        if channels is None: 
            channels = self.channels.getChannels()
        channels = sorted(self._verify(channels), key=itemgetter('number'))
        self.log(f"getVerifiedChannels, channels = {len(channels)}")
        return channels

 
    def _verify(self, channels=None):
        if channels is None: 
            channels = self.channels.getChannels()
        for idx, citem in enumerate(channels):
            if not citem.get('name') or len(citem.get('path', [])) == 0 or not citem.get('number'):
                self.log(f"[{citem.get('id')}] SKIPPING - missing necessary channel meta\n{citem}", xbmc.LOGINFO)
                continue
            elif not citem.get('enable', True):
                self.log(f"[{citem.get('id')}] SKIPPING - disabled channel\n{citem}", xbmc.LOGINFO)
                continue
            else:
                if not citem.get('id'): 
                    citem['id'] = getChannelID(citem['name'], citem['path'], citem['number'], SETTINGS.getMYUUID())
                citem['logo'] = self.resources.getLogo(citem, fallback=self.resources.getImageCache(citem['name']), lookup=True)
                self.log(f"[{citem['id']}] VERIFIED - channel {citem['number']}: {citem['name']} changed = {citem.get('changed', False)}", xbmc.LOGINFO)
                yield self.runActions(RULES_ACTION_CHANNEL_CITEM, citem, Globals._cleanGroups(citem), inherited=self)
             
             
    def buildCells(self, citem: dict, duration: int=10800, type: str='video', entries: int=3, info=None) -> list:
        if info is None: 
            info = {}
        info.setdefault('art', {})['poster'] = Globals._getThumb(info, opt=1)
        info.setdefault('art', {})['fanart'] = Globals._getThumb(info)
        info.update({
            'label': (info.get('title') or citem['name']),
            'episodetitle': (info.get('episodetitle') or '|'.join(citem.get('group', []))),
            'plot': (info.get('plot') or LANGUAGE(32020)),
            'genre': (info.get('genre') or ['Undefined']),
            'file': (info.get('path') or info.get('file') or info.get('originalpath') or '|'.join(citem.get('path', []))),
            'art': (info.get('art') or {"thumb": LOGO, "poster": LOGO_POSTER, "fanart": LOGO_LANDSCAPE, "landscape": LOGO_LANDSCAPE, "logo": LOGO, "icon": LOGO}),
            'type': type,
            'duration': duration,
            'start': 0,
            'stop': 0
        })
        return [info.copy() for _ in range(entries)]

                
    def buildChannels(self, channels: list=None, preview=False, silent=None):
        if channels is None:
            channels = []
        if silent is None: 
            silent = not SETTINGS.showDialog(silent)
        self.log(f"buildChannels, channels = {len(channels)}")
        
        def __needsUpdate(citem, now, fallback, state=True):
            last_stop   = dict(self.xmltv.loadStopTimes([citem], fallback=fallback)).get(citem['id'])
            future_stop = now + ((MAX_GUIDEDAYS * 86400) - 10800)
            if last_stop > (future_stop): state = False
            self.log(f"[{citem['id']}] buildChannels, __needsUpdate = {state}, last_stop = {last_stop}, future_stop = {future_stop}")
            return state, last_stop
            
        def __hasChanged(citem: dict, detect=False) -> bool:
            state = citem.get('changed', False)
            if not state and detect:
                state = any(SETTINGS.getFileCRC(file) for file in citem.get('path', []) if file.endswith(tuple(KODI_PLAYLISTS + BASIC_PLAYLISTS)))
                if state: self.log(f"[{citem['id']}] buildChannels, __hasChanged playlist detected!")
            self.log(f"[{citem['id']}] buildChannels, __hasChanged = {state}")
            if state: 
                if __clrStation(citem): citem['changed'] = False
                changes.add(self.channels.addChannel(citem))
            return state, citem
                    
        def __hasProgrammes(citem: dict) -> bool:
            try:              state = dict(self.xmltv.hasProgrammes([citem])).get(citem['id'], False)
            except Exception: state = False
            self.log(f"[{citem['id']}] buildChannels, __hasProgrammes = {state}")
            return state

        def __hasFileList(fileList: list, state=False) -> bool:
            if isinstance(fileList, list) and len(fileList) > 0: state = True
            self.log(f"[{citem['id']}] buildChannels, __hasFileList = {state}")
            return state
        
        def __addProgrammes(citem: dict, fileList: list) -> bool:
            state = any([self.xmltv.addProgram(citem['id'], self.xmltv.getProgramItem(citem, item)) for item in fileList])
            self.log(f"[{citem['id']}] buildChannels, __addProgrammes {state} fileList = {len(fileList)}")
            return state
        
        def __addStation(citem: dict) -> bool:
            sitem = self.m3u.getStationItem(citem)
            state = any([self.m3u.addStation(sitem), self.xmltv.addChannel(sitem)])
            self.log(f"[{citem['id']}] buildChannels, __addStation = {state}")
            return state
        
        def __clrStation(citem: dict) -> bool:
            state = any([self.resetPagination(citem), self.m3u.delStation(citem), self.xmltv.delBroadcast(citem)])
            self.log(f"[{citem['id']}] buildChannels, __clrStation = {state}")
            return state
        
        def __setStation():
            state = any([self.m3u._save(), self.xmltv._save()])
            self.log(f"[{citem['id']}] buildChannels, __setStation = {state}")
            return state
            
        def __addScheduling(citem: dict, fileList: list, now: int, start: int) -> list: 
            self.log(f"[{citem['id']}] __addScheduling, IN fileList = {len(fileList)}, now = {now}, start = {start}")
            fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_PRE, citem, fileList.copy(), inherited=self)
            for idx, item in enumerate(fileList):
                if not item.get('duration'): continue
                item["idx"]   = idx
                item['start'] = start
                item['stop']  = start + item['duration']
                start = item['stop']
            fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_POST, citem, fileList.copy(), inherited=self)
            self.log(f"[{citem['id']}] buildChannels, __addScheduling, OUT fileList = {len(fileList)}")
            return fileList
        
        def __addFillers(citem, fileList, enable=False):
            self.log(f"[{citem['id']}] buildChannels, __addFillers, enable = {enable}, fileList = {len(fileList)}")
            if enable: return Fillers(citem, self).injectFillers(fileList)
            return fileList
                
        if PROPERTIES.isRunning('Builder.buildChannels'): return
        with PROPERTIES.legacy(), PROPERTIES.chkRunning('Builder.buildChannels'):
            channels = self.getVerifiedChannels(channels)
            if len(channels) == 0:
                return

            complete  = set()
            changes   = set()
            now       = getUTCstamp()
            nstart    = roundTimeDown(now, offset=60)
            fallback  = epochTime(nstart, tz=False).strftime(DTFORMAT)

            self.pDialog, self.pMSG, self.pName, self.pHeader = None, '', '', ''
            self.pErrors = []
            self.pCount  = 0
            self.cCount  = len(channels)

            for idx, citem in enumerate(channels):
                try:
                    updated      = set()
                    self.pMSG    = f"{LANGUAGE(32144)}: {LANGUAGE(32212)}"
                    self.pHeader = ADDON_NAME
                    self.pName   = citem['name']
                    self.pCount  = int(idx * 100) // self.cCount
                    citem = self.runActions(RULES_ACTION_CHANNEL_TEMP_CITEM, citem, citem, inherited=self)
                    _update, start  = __needsUpdate(citem, now, fallback)
                    _changed, citem = __hasChanged(citem,  self.enableChanged) 
                    self.log(f"[{citem['id']}] buildChannels, preview = {preview}, rules = {citem.get('rules', {})}, _update = {_update}")
                    
                    if self.service._interrupt():
                        self.log(f"[{citem['id']}] buildChannels, _interrupt")
                        self.pErrors = [LANGUAGE(32160)]
                        if hasattr(self.service, '_que'): 
                            self.service._que(self.service.tasks.chkChannels, 3, 0, 0, *(channels[idx:], silent))
                        break
                    elif self.service._suspend():
                        self.log(f"[{citem['id']}] buildChannels, _suspend")
                        if not self.service._sleep(CPU_CYCLE): 
                            continue
                    elif _update or _changed:                       
                        if preview:          
                            self.pMSG = LANGUAGE(32236)                           
                        elif start == fallback: 
                            self.pMSG = f"{LANGUAGE(30014)} {LANGUAGE(30223)}"
                        else:                  
                            self.pMSG = f"{LANGUAGE(32022)} {LANGUAGE(30223)}"
                            
                        self.pHeader = f'{ADDON_NAME}, {self.pMSG}'
                        self.log(f"[{citem['id']}] buildChannels, start ({start}) => {self.pMSG}")

                        if start > 0:
                            with DIALOG._progressDialog(self.pMSG, ADDON_NAME, silent=silent, background=not preview) as self.pDialog:
                                self.runActions(RULES_ACTION_CHANNEL_START, citem, inherited=self)
                                if citem.get('radio', False): 
                                    fileList = self.buildMusic(citem)
                                else:                        
                                    fileList = self.buildVideo(citem)
                                    
                                if isinstance(fileList, list):
                                    fileList = sorted(__addScheduling(citem, fileList, now, start), key=itemgetter('start'))
                                    if not citem.get('radio', False): 
                                        fileList = sorted(__addFillers(citem, fileList, self.enableBCTs), key=itemgetter('start'))
                                    if not preview and __hasFileList(fileList):
                                        updated.add(__addProgrammes(citem, fileList))
                                elif not fileList:
                                    hasProgrammes = __hasProgrammes(citem)
                                    updated.add(hasProgrammes)
                                    if len(self.pErrors) > 0:
                                        if hasProgrammes: 
                                            self.pErrors.append(LANGUAGE(32033))
                                        chanErrors = ' | '.join(list(sorted(set(self.pErrors))))
                                        self.log(f"[{citem['id']}] buildChannels, In-Valid Channel ({self.pName}) {chanErrors}")
                                        self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'{self.pName}: {chanErrors}', header=f'{ADDON_NAME}, {LANGUAGE(32027)} {LANGUAGE(30223)}')
                                self.runActions(RULES_ACTION_CHANNEL_STOP, citem, inherited=self)
                                if preview: 
                                    return fileList
                    else: 
                        updated.add(__hasProgrammes(citem))
                        
                    if any(updated): 
                        complete.add(__addStation(citem)) 
                        PROPERTIES.setPropTimer('chkPVRRefresh')
                    else: 
                        __clrStation(citem)
                    __setStation()
                except Exception as e: 
                    self.log(f"buildChannels, failed! {e}", xbmc.LOGERROR)
            if any(changes): 
                self.channels.setChannels()
            self.log(f"buildChannels execution completed. Status metrics matched successfully.")


    def buildMusic(self, citem: dict) -> list:
        self.log(f"[{citem['id']}] buildMusic")
        return self.buildCells(
            citem, MIN_EPG_DURATION, 'music', (MAX_GUIDEDAYS * 8), 
            info={
                'genre': ["Music"],
                'art': {"thumb": citem.get('logo', LOGO), "poster": LOGO_POSTER, "fanart": LOGO_LANDSCAPE, "landscape": LOGO_LANDSCAPE, "logo": citem.get('logo', LOGO), "icon": citem.get('logo', LOGO)},
                'plot': LANGUAGE(32029) % (citem['name'])
            }
        )
        
        
    def buildVideo(self, citem: dict, validate: bool=False):
        def _validFileList(fileArray):
            return any(len(fileList) > 0 for fileList in fileArray)
            
        def _injectRules(citem):
            tmpCitem = citem.copy()
            if tmpCitem.get('path', []) == ["{Seasonal}"]:
                nrules = {800: {"values": {0: list(self.seasonal.buildSeasonal(self.holiday))}}}
                tmpCitem.setdefault('rules', {}).update(nrules)
                self.log(f" [{citem['id']}] buildVideo: _injectRules, Seasonal Content, new rules = {nrules}")
                
            if self.enableEven and not citem.get('rules', {}).get(1000):
                nrules = {1000: {"values": {0: SETTINGS.getSettingInt('Enable_Even'), 1: self.evenEpisode, 2: self.evenShuffle}}}
                tmpCitem.setdefault('rules', {}).update(nrules)
                self.log(f" [{citem['id']}] buildVideo: _injectRules, Even Show Distribution, new rules = {nrules}")
            return tmpCitem
            
        citem     = _injectRules(citem) 
        fileArray = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE, citem, list(), inherited=self) 
        self.log(f"[{citem['id']}] buildVideo, channel pre fileArray items = {len(fileArray)}", xbmc.LOGINFO)
        
        if not _validFileList(fileArray): 
            for idx, paths in enumerate(citem.get('path', [])):
                if self.service._interrupt():
                    self.log(f"[{citem['id']}] buildVideo, _interrupt")
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f"{LANGUAGE(32144)}: {LANGUAGE(32213)}", header=self.pHeader)
                    return []
                elif self.service._suspend():
                    self.log(f"[{citem['id']}] buildVideo, _suspend")
                    if not self.service._sleep(CPU_CYCLE): 
                        continue
                else:
                    if len(citem.get('path', [])) > 1:
                        self.pName = f"{citem['name']} {idx+1}/{len(citem.get('path',[]))}"
                        
                    if self.xsp.isXSP(paths):
                        paths = self.xsp.parseXSP(citem['id'], paths)
                    elif isinstance(paths, (str, bytes)):
                        paths = [paths]
                    
                    if self.sort.get("method", "") == 'random':
                        self.log(f"[{citem['id']}] buildVideo, random shuffling [{idx}/{len(paths)}]")
                        paths = Globals._randomShuffle(paths)               

                    for cnt, path in enumerate(paths):
                        if len(paths) > 1:
                            self.pName = f"{citem['name']} {idx+1}/{len(citem.get('path',[]))}\n{cnt+1}/{len(paths)}"
                            
                        self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'{self.pName}', header=self.pHeader)
                        fileList = self.buildFileList(citem, self.runActions(RULES_ACTION_CHANNEL_BUILD_PATH, citem, path, inherited=self), 'video', self.limit, self.sort, self.limits, self.query)
                        if isinstance(fileList, list): 
                            fileArray.append(fileList)
                        if validate and len(fileList) > 0: 
                            break
                        self.log(f"[{citem['id']}]  buildVideo, validate = {validate}, fileList [{len(fileList)}/{sum(len(sublist) for sublist in fileArray)}], path [{cnt}/{self.limit}]\n{path}, ")
        
        fileArray = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST, citem, fileArray, inherited=self) 
        if isinstance(fileArray, list):
            self.log(f"[{citem['id']}] buildVideo, channel post fileArray items = {len(fileArray)}", xbmc.LOGINFO)
            if not _validFileList(fileArray):
                self.log(f"[{citem['id']}] buildVideo, channel fileArray In-Valid!", xbmc.LOGINFO)
                return False
            fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE, citem, interleave(fileArray, self.interleaveSet, self.interleaveRepeat), inherited=self)
            self.log(f"[{citem['id']}] buildVideo, pre fileList items = {len(fileList)}", xbmc.LOGINFO)
            fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_POST, citem, fileList, inherited=self)
            self.log(f"[{citem['id']}] buildVideo, post fileList items = {len(fileList)}", xbmc.LOGINFO)
        else:
            fileList = fileArray
        return self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN, citem, fileList, inherited=self)


    def buildFileList(self, citem: dict, path: str, media: str='video', page: int=None, sort=None, limits=None, query=None) -> list:
        if page is None:   page   = SETTINGS.getSettingInt('Page_Limit')
        if sort is None:   sort   = {}
        if limits is None: limits = {"end": -1, "start": 0, "total": 0}
        if query is None:  query  = {}

        self.log(f"[{citem['id']}] buildFileList, path = {path}\nmedia = {media}, limit = {page}, sort = {sort}, page = {limits}")
        self.loopback = None
        
        def __padFileList(fileItems, page):
            self.log(f"[{citem['id']}] buildFileList, __padFileList fileItems")
            if page > len(fileItems):
                tmpList   = fileItems * (page // len(fileItems))
                remainder = page % len(fileItems)
                if remainder > 0:
                    tmpList.extend(fileItems[-remainder:])
                self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'padding {remainder} files', header=self.pHeader)
                return tmpList
            return fileItems

        if self.xsp.isDXSP(path):
            path = self.xsp.parseDXSP(citem['id'], path, self.filter, self.incExtras)
  
        fileList = []
        dirCount = -1
        dirList  = [{'file': path}]
        self.log(f"[{citem['id']}] buildFileList, path = {path}\nsort = {sort}, limits = {limits}, page = {page}")
        
        while not self.monitor.abortRequested():
            if self.service._interrupt():
                self.log(f"[{citem['id']}] buildFileList, _interrupt")
                self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f"{LANGUAGE(32144)}: {LANGUAGE(32213)}", header=self.pHeader)
                return []
            elif self.service._suspend():
                self.log(f"[{citem['id']}] buildFileList, _suspend")
                self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f"{LANGUAGE(32144)}: {LANGUAGE(32145)}", header=self.pHeader)
                if not self.service._sleep(CPU_CYCLE): 
                    continue
            elif len(dirList) == 0 or dirCount >= self.recursiveLimit:
                if self.padFilelist and 0 < len(fileList) < page: 
                    fileList = __padFileList(fileList, page)
                elif len(fileList) < page and len(dirList) > dirCount: 
                    self.pErrors.append(LANGUAGE(32262))
                self.log(f"[{citem['id']}] buildFileList, no more folders to parse or recursive limit met.")
                break
            elif len(dirList) > 0:
                dirCount += 1
                folder   = dirList.pop(0)
                path     = folder.get('file')
                if folder.get("label"): 
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'parsing folder: {folder.get("label")}', header=self.pHeader)
                
                subfileList, subdirList, limits, errors = self.buildList(citem, path, media, abs(page - len(fileList)), sort, limits, folder, query)
                if sort.get("method", "") == 'random':
                    self.log(f"[{citem['id']}] buildFileList, depth [{dirCount}/{self.recursiveLimit}], random shuffling ")
                    subdirList  = Globals._randomShuffle(subdirList)
                    subfileList = Globals._randomShuffle(subfileList)
                    
                if isinstance(subfileList, list): 
                    fileList.extend(subfileList)
                if isinstance(subdirList, list):  
                    dirList = Globals._setDictLST(dirList + subdirList)
                self.log(f"[{citem['id']}] buildFileList, depth [{dirCount}/{self.recursiveLimit}], adding fileList [{len(fileList)}/{page}] remaining sub-directories [{len(dirList)}]\npath = {path}, limits = {limits}")

        self.log(f"[{citem['id']}] buildFileList, depth [{dirCount}/{self.recursiveLimit}], returning fileList [{len(fileList)}/{page}]")
        return fileList


    def buildList(self, citem: dict, path: str, media: str='video', page: int=None, sort=None, limits=None, dirItem=None, query=None):
        if page is None:    page    = SETTINGS.getSettingInt('Page_Limit')
        if sort is None:    sort    = {}
        if limits is None:  limits  = {"end": -1, "start": 0, "total": 0}
        if dirItem is None: dirItem = {}
        if query is None:   query   = {}

        self.log(f"[{citem['id']}] buildList, media = {media}, path = {path}\npage = {page}, sort = {sort}, query = {query}, limits = {limits}\ndirItem = {dirItem}")
        nlimits = limits
        errors  = {}
        items   = self.runActions(RULES_ACTION_CHANNEL_REQUEST_FILELIST_PRE, citem, [], inherited=self)
        items, nlimits, errors = self.jsonRPC.requestList(citem, path, media, page, sort, self.filter, limits, query)
        items = self.runActions(RULES_ACTION_CHANNEL_REQUEST_FILELIST_POST, citem, items, inherited=self)
        
        if errors.get('message'):
            self.pErrors.append(errors['message'])
            return [], [], nlimits, errors
        elif not items:
            self.log(f"[{citem['id']}] buildList, no request items found using path = {path}")
            self.pErrors.append(LANGUAGE(32026))
            return [], [], nlimits, errors
        elif items == self.loopback and limits != nlimits:
            self.log(f"[{citem['id']}] buildList, loopback detected using path = {path}")
            self.pErrors.append(LANGUAGE(32030))
            return [], [], nlimits, errors
        elif items:
            self.loopback = items
            fileList, dirList = self.buildFiles(citem, path, items, media, page, sort, limits, dirItem, query)
            if len(fileList) == 0 and path in dirList: 
                self.jsonRPC.autoPagination(citem['id'], path, query, limits)
            self.log(f"[{citem['id']}] buildList, returning fileList [{len(fileList)}], dirList [{len(dirList)}]")
            return fileList, dirList, nlimits, errors


    def buildFiles(self, citem: dict, path: str, items: list=None, media: str='video', page: int=None, sort=None, limits=None, dirItem=None, query=None):
        if items is None:   items    = []
        if page is None:    page    = SETTINGS.getSettingInt('Page_Limit')
        if sort is None:    sort    = {}
        if limits is None:  limits  = {"end": -1, "start": 0, "total": 0}
        if dirItem is None: dirItem = {}
        if query is None:   query   = {}

        fileList, dirList, seasoneplist = [], [], []
        for idx, item in enumerate(items):
            file        = item.get('file', '')
            fileType    = item.get('filetype', 'file')
            self.fCount = int(idx * 100) // len(items)
            
            if not item.get('type'): item['type'] = query.get('key', 'files')
            if self.service._interrupt() or self.service._suspend():
                self.log(f"[{citem['id']}] buildFiles, _interrupt/_suspend")
                self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f"{LANGUAGE(32144)}: {LANGUAGE(32213)}", header=self.pHeader)
                break
            elif fileType == 'directory':
                dirList.append(item)
                continue
            elif fileType != 'file':
                continue
            else:
                self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'{self.pName}: {self.fCount}%',header=self.pHeader)
                if file.startswith('pvr://'): #parse encoded fileitem otherwise no relevant meta provided via org. query. playable pvr:// paths are limited in Kodi.
                    self.log("[%s] buildFiles, IDX = %s, PVR item => FileItem! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                    item = Globals._decodePlot(item.get('plot',''))
                    file = item.get('file')
                if not file:
                    self.pErrors.append(LANGUAGE(32031))
                    self.log("[%s] buildFiles, IDX = %s, skipping missing playable file! path = %s"%(citem['id'],idx,path),xbmc.LOGINFO)
                    continue
                elif (file.lower().endswith('strm') and not self.incStrms): 
                    self.pErrors.append('%s STRM'%(LANGUAGE(32027)))
                    self.log("[%s] buildFiles, IDX = %s, skipping strm file! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                    continue
                elif not self.inc3D:
                    if self.is3D(item):
                        item['is3D'] = True
                        self.pErrors.append('%s 3D'%(LANGUAGE(32027)))
                        self.log("[%s] buildFiles, IDX = %s skipping 3D file! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                        continue

                if self.incStrmDetails and not item.get('streamdetails',{}).get('video',[]) and not file.startswith(tuple(VFS_TYPES)): #parsing missing meta, kodi rpc bug fails to return streamdetails during Files.GetDirectory.
                    item['streamdetails'] = self.jsonRPC.getStreamDetails(file, media)

                label = (item.get("title") or item.get("label") or dirItem.get('label') or '')
                if not label:  
                    self.pErrors.append(LANGUAGE(32018)(LANGUAGE(30188)))
                    continue
                    
                # This is a TV show
                if (item['type'].startswith(tuple(TV_TYPES)) or item.get("showtitle")):
                    tvtitle = (item.get("showtitle") or item.get("label") or dirItem.get('label') or '')
                    season  = int(item.get("season","0"))
                    episode = int(item.get("episode","0"))
                    if not file.startswith(tuple(VFS_TYPES)) and not self.incExtras and (season == 0 or episode == 0):
                        self.pErrors.append('%s Extras'%(LANGUAGE(32027)))
                        self.log("[%s] buildFiles, IDX = %s skipping extras! file = %s"%(citem['id'],idx,file),xbmc.LOGINFO)
                        continue

                    label = tvtitle
                    item["tvshowtitle"]  = tvtitle
                    item["episodetitle"] = label
                    item["episodelabel"] = '%s%s'%(label,' (%sx%s)'%(season,str(episode).zfill(2))) #Episode Title (SSxEE) Mimic Kodi's PVR label format
                    item["showlabel"]    = '%s%s'%(item["tvshowtitle"],' - %s'%(item['episodelabel']) if item['episodelabel'] else '')
                else: # This is a Movie
                    item["episodetitle"] = item.get("tagline","")
                    item["episodelabel"] = item.get("tagline","")
                    item["showlabel"]    = '%s%s'%(item.get("title",""), ' - %s'%(item['episodelabel']) if item['episodelabel'] else '')
                
                dur = self.jsonRPC.getDuration(file, item, self.accurateDuration, self.saveDuration)
                if dur > self.minDuration: #include media that's duration is above the players seek tolerance & users adv. rule
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, message=f'{self.pName}: {self.fCount}%',header=self.pHeader)
                    item['duration']     = dur
                    item['media']        = media
                    item['originalpath'] = path #use for path sorting/playback verification 
                    item['friendly']     = PROPERTIES.getFriendlyName()
                    item['remote']       = PROPERTIES.getRemoteHost()
                        
                    if item.get("year",0) == 1601: item['year'] = 0 #detect kodi bug that sets a fallback year to 1601 https://github.com/xbmc/xbmc/issues/15554
                    spTitle, spYear = splitYear(label)
                    item['label']   = spTitle
                        
                    if item.get('year',0) == 0 and spYear: item['year'] = spYear #replace missing item year with one parsed from show title
                    item['plot'] = (item.get("plot","") or item.get("plotoutline","") or item.get("description","") or LANGUAGE(32020)).strip()
                        
                    holiday = citem.get('rules',{}).get(800,{}).get('values',{}).get(0,[{}])[0].get('holiday',{})
                    if holiday: #add seasonal meta
                        item["plot"] = "%s \n%s"%("[B]%s[/B] - [I]%s[/I]"%(holiday["name"],holiday["tagline"]) if holiday["tagline"] else "[B]%s[/B]"%(holiday["name"]),item["plot"])
                        
                    item['art'] = (item.get('art',{}) or dirItem.get('art',{}))
                    item.get('art',{})['icon'] = citem['logo']
                        
                    if item.get('trailer'): self.service._que(self.jsonRPC.addTrailer,-1,0,0,item)
                    if sort.get("method","") == 'episode' and (int(item.get("season","0")) + int(item.get("episode","0"))) > 0: 
                        seasoneplist.append([int(item.get("season","0")), int(item.get("episode","0")), item])
                    else: 
                        fileList.append(item)
                else: 
                    self.pErrors.append(LANGUAGE(32032))
                    self.log("[%s] buildFiles, IDX = %s skipping content no duration meta found! or runtime below minDuration (%s/%s) file = %s"%(citem['id'],idx,dur,self.minDuration,file),xbmc.LOGINFO)
        
        if sort.get("method","") == 'episode':
            self.log("[%s] buildFiles, sorting by episode"%(citem['id']))
            seasoneplist.sort(key=lambda seep: seep[1])
            seasoneplist.sort(key=lambda seep: seep[0])
            for seepitem in seasoneplist: 
                fileList.append(seepitem[2])
                
        elif sort.get("method","") == 'random':
            self.log("[%s] buildFiles, random shuffling"%(citem['id']))
            dirList  = Globals._randomShuffle(dirList)
            fileList = Globals._randomShuffle(fileList)
            
        self.log("[%s] buildFiles, returning (%s) files, (%s) dirs"%(citem['id'],len(fileList),len(dirList)))
        return fileList, dirList


    def is3D(self, item: dict) -> bool:
        if 'is3D' in item: return item['is3D']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and details.get('video') != [] and len(details.get('video')) > 0:
            if len(details['video'][0]['stereomode'] or []) > 0: return True
        return False


    def resetPagination(self, citem):
        if isinstance(citem, list): return any([self.resetPagination(item) for item in citem])
        return any([self.jsonRPC.resetPagination(citem.get('id'), path) for path in citem.get('path',[]) if citem.get('id')])
    
        