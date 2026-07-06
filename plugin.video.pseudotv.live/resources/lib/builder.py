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

from variables    import *
from channels   import Channels
from xmltvs     import XMLTVS
from xsp        import XSP
from m3u        import M3U
from fillers    import Fillers
from resources  import Resources
from seasonal   import Seasonal 
from rules      import RulesList
from seasonal   import Seasonal

class Builder(object):
    xsp      = XSP()
    seasonal = Seasonal()
    loopback = None
    
    def __init__(self, service):
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
        self.accurateDuration = bool(Globals.settings.getSettingInt('Duration_Type'))
        self.interleaveSet    = Globals.settings.getSettingInt('Interleave_Set')
        self.interleaveRepeat = Globals.settings.getSettingBool('Interleave_Repeat')
        self.incStrms         = Globals.settings.getSettingBool('Enable_Strms')
        self.inc3D            = Globals.settings.getSettingBool('Enable_3D')
        self.incExtras        = Globals.settings.getSettingBool('Enable_Extras') 
        self.incStrmDetails   = Globals.settings.getSettingBool('Enable_Details')
        self.enableBCTs       = Globals.settings.getSettingBool('Enable_Fillers')
        self.saveDuration     = Globals.settings.getSettingBool('Store_Duration')
        self.minDuration      = Globals.settings.getSettingInt('Seek_Tolerance')
        self.limit            = Globals.settings.getSettingInt('Page_Limit')
        self.recursiveLimit   = Globals.settings.getSettingInt('Recursive_Depth')
        self.padScheduling    = False #TODO Adv. Rules 
        self.padFilelist      = False #TODO Adv. Rules 
        self.enableEven       = bool(Globals.settings.getSettingInt('Enable_Even'))
        self.evenEpisode      = Globals.settings.getSettingBool('Enable_Even_Force_Episode')
        self.evenShuffle      = Globals.settings.getSettingBool('Enable_Even_Force_Random')
        self.enableChanged    = Globals.settings.getSettingBool('Enable_Changed')
        self.pageLimit        = Globals.settings.getSettingInt('Page_Limit')
        
        self.filter           = {}
        self.sort             = {}
        self.limits           = {"end": -1, "start": 0, "total": 0}
        self.query            = {}
        
        # Pre-cache constant configuration lookups to minimize setting poll overhead
        preroll_max = Globals.settings.getSettingInt('Enable_Preroll')
        postroll_min = Globals.settings.getSettingInt('Enable_Postroll')
        post_chance = Globals.settings.getSettingInt('Random_Post_Chance')
        include_trailers = Globals.settings.getSettingBool('Include_Trailers_KODI')

        self.bctTypes = {
            "bumpers": {
                "min": -1, "max": preroll_max, "auto": preroll_max == -1, "enabled": bool(preroll_max), 
                "chance": Globals.settings.getSettingInt('Random_Pre_Chance'),
                "sources": {"ids": Globals.settings.getSetting('Resource_Bumpers').split('|'), "paths": [os.path.join(FILLER_LOC, 'Bumpers', '')]}, "items": {}
            },
            "ratings": {
                "min": -1, "max": preroll_max, "auto": preroll_max == -1, "enabled": bool(preroll_max), 
                "chance": Globals.settings.getSettingInt('Random_Pre_Chance'),
                "sources": {"ids": Globals.settings.getSetting('Resource_Ratings').split('|'), "paths": [os.path.join(FILLER_LOC, 'Ratings', '')]}, "items": {}
            },
            "adverts": {
                "min": postroll_min, "max": self.pageLimit, "auto": postroll_min == -1, "enabled": bool(postroll_min), 
                "chance": post_chance,
                "sources": {"ids": Globals.settings.getSetting('Resource_Adverts').split('|'), "paths": [os.path.join(FILLER_LOC, 'Adverts', '')]}, "items": {}, "incKODI": include_trailers
            },
            "trailers": {
                "min": postroll_min, "max": self.pageLimit, "auto": postroll_min == -1, "enabled": bool(postroll_min), 
                "chance": post_chance,
                "sources": {"ids": Globals.settings.getSetting('Resource_Trailers').split('|'), "paths": [os.path.join(FILLER_LOC, 'Trailers', '')]}, "items": {}, "incKODI": include_trailers
            },
            "extras": {
                "min": postroll_min, "max": self.pageLimit, "auto": postroll_min == -1, "enabled": bool(postroll_min), 
                "chance": post_chance,
                "sources": {"ids": [], "paths": []}, "items": {}, "incKODI": Globals.settings.getSettingBool('Include_Extras_KODI')
            }
        }
        self.service   = service
        self.monitor   = service.monitor
        self.jsonRPC   = service.jsonRPC
        self.cache     = service.cache
        self.holiday   = self.seasonal.getHoliday()
        self.channels  = Channels(writable=True)
        self.resources = Resources(service)
        self.runActions = RulesList(self.channels.getChannels()).runActions


    def log(self, msg, level=xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)
        

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
                    citem['id'] = Globals._getChannelID(citem['name'], citem['path'], citem['number'], Globals.settings.getMYUUID())
                citem['logo'] = self.resources.getLogo(citem, fallback=self.resources.getImageCache(citem['name']), lookup=True)
                self.log(f"[{citem['id']}] VERIFIED - channel {citem['number']}: {citem['name']} changed = {citem.get('changed', False)}", xbmc.LOGINFO)
                yield self.runActions(RULES_ACTION_CHANNEL_CITEM, citem, Globals._cleanGroups(citem), inherited=self)
             
             
    def buildCells(self, citem: dict, duration: int=10800, type: str='video', entries: int=3, info=None) -> list:
        if info is None: info = {}
        art = info.setdefault('art', {})
        art['poster'] = art.get('poster') or Globals._getThumb(info, opt=1)
        art['fanart'] = art.get('fanart') or Globals._getThumb(info)
        
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
        copy_info = info.copy
        return [copy_info() for _ in range(entries)]


    def buildChannels(self, channels: list = None, preview=False, silent=None, write=True):
        if channels is None: channels = []
        if silent is None:   silent = not Globals.settings.showDialog(silent)
        self.log('buildChannels, channels=%d, preview=%s, silent=%s, write=%s' % (len(channels), preview, silent, write))
        
        if Globals.properties.isRunning('Builder.buildChannels'): return
        with Globals.properties.legacy(), Globals.properties.chkRunning('Builder.buildChannels'):
            channels = self.getVerifiedChannels(channels)
            if not channels: return
            changes  = set()
            complete = set()
            
            now = float(Globals._getUTCstamp())
            fallback_epoch = float(Globals._roundTimeDown(now, offset=60))
            future_stop = now + ((MAX_GUIDEDAYS * 86400) - 10800)
            fallback_str = Globals._epochTime(fallback_epoch, tz=False).strftime(DTFORMAT)

            self.pDialog, self.pMSG, self.pName, self.pHeader = None, '', '', ''
            self.pErrors = []
            self.pCount  = 0
            self.cCount  = len(channels)
            
            preview_results = {}
            with M3U(writable=write) as m3u, XMLTVS(writable=write, m3u=m3u) as epg:
                all_stop_times = dict(epg.loadStopTimes(channels, fallback=fallback_str))
                has_programmes = dict(epg.hasProgrammes(channels)) if hasattr(self, 'xmltv') else {}
                
                for idx, citem in enumerate(channels):
                    try:
                        updated = set()
                        self.pMSG = f"{LANGUAGE(32144)}: {LANGUAGE(32212)}"
                        self.pHeader = ADDON_NAME
                        self.pName   = citem.get('name', '')
                        self.pCount  = int(idx * 100) // self.cCount
                        
                        if self.service.pendingInterrupt:
                            self.log(f"[{citem.get('id')}] buildChannels, _interrupt")
                            if hasattr(self.service,'_que'): self.service._que(self.service.tasks.chkChannels,3,0,0,*(channels[idx:],silent))
                            break
                        elif self.service.pendingSuspend:
                            self.log(f"[{citem.get('id')}] buildChannels, _suspend")
                            if not self.service._sleep(CPU_CYCLE): 
                                continue
                                
                        citem = self.runActions(RULES_ACTION_CHANNEL_TEMP_CITEM, citem, citem, inherited=self)
                        raw_start = all_stop_times.get(citem.get('id'), fallback_epoch)
                        
                        if isinstance(raw_start, str):
                            start_epoch = float(datetime.datetime.strptime(raw_start, DTFORMAT).timestamp())
                            start_timestamp_str = raw_start
                        else:
                            start_epoch = float(raw_start)
                            start_timestamp_str = Globals._epochTime(start_epoch, tz=False).strftime(DTFORMAT)

                        _update = start_epoch <= fallback_epoch or start_epoch <= future_stop
                        self.log(f"[{citem.get('id')}] Schedule delta audit -> Update Required: {_update} | Target End: {start_timestamp_str}")

                        _changed = citem.get('changed', False)
                        if not _changed and getattr(self, 'enableChanged', False):
                            paths = citem.get('path', [])
                            valid_extensions = tuple(KODI_PLAYLISTS + BASIC_PLAYLISTS)
                            _changed = any(Globals.settings.getFileCRC(f) for f in paths if f.endswith(valid_extensions))
                        
                        if _changed:
                            self.log(f"[{citem.get('id')}] Playlist signature mutation caught; flushing target datasets.")
                            self._resetPagination(citem)
                            m3u.delStation(citem)
                            epg.delBroadcast(citem)
                            citem['changed'] = False
                            changes.add(self.channels.addChannel(citem))

                        if _update or _changed:                       
                            self.pMSG = LANGUAGE(32236) if preview else (f"{LANGUAGE(30014)} {LANGUAGE(30223)}" if start_timestamp_str == fallback_str else f"{LANGUAGE(32022)} {LANGUAGE(30223)}")
                            self.pHeader = f'{ADDON_NAME}, {self.pMSG}'

                            if start_epoch > 0:
                                with Globals.dialog._progressDialog(self.pMSG, ADDON_NAME, silent=silent, background=not preview) as self.pDialog:
                                    self.runActions(RULES_ACTION_CHANNEL_START, citem, inherited=self)
                                    fileList = self.buildMusic(citem) if citem.get('radio', False) else self.buildVideo(citem)
                                    
                                    if isinstance(fileList, list) and fileList:
                                        fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_PRE, citem, fileList, inherited=self)
                                        for s_idx, item in enumerate(fileList):
                                            duration = item.get('duration')
                                            if not duration: continue
                                            item["idx"] = s_idx
                                            item['start'] = start_epoch
                                            item['stop'] = start_epoch + duration
                                            start_epoch = item['stop']
                                            
                                        fileList = sorted(self.runActions(RULES_ACTION_CHANNEL_BUILD_TIME_POST, citem, fileList, inherited=self), key=itemgetter('start'))
                                        if not citem.get('radio', False): fileList = sorted(Fillers(citem, self).injectFillers(fileList), key=itemgetter('start'))
                                        if preview: preview_results[citem.get('id')] = fileList
                                        else:
                                            prog_added = any([epg.addProgram(citem.get('id'), epg.getProgramItem(citem, item)) for item in fileList])
                                            updated.add(prog_added)
                                            self.log(f"[{citem.get('id')}] Pipeline serialization completed -> Total entries matching: {len(fileList)}")
                                    
                                    elif not fileList:
                                        has_progs = has_programmes.get(citem.get('id'), False)
                                        updated.add(has_progs)
                                        if self.pErrors:
                                            if has_progs: self.pErrors.append(LANGUAGE(32033))
                                            chanErrors = ' | '.join(sorted(set(self.pErrors)))
                                            self.pDialog = Globals.dialog._updateProgress(self.pDialog, self.pCount, message=f'{self.pName}: {chanErrors}', header=f'{ADDON_NAME}, Errors detected.')
                                    self.runActions(RULES_ACTION_CHANNEL_STOP, citem, inherited=self)
                        else:
                            has_progs = has_programmes.get(citem.get('id'), False)
                            updated.add(has_progs)
                        
                        if any(updated): 
                            sitem = m3u.getStationItem(citem)
                            station_added = any([m3u.addStation(sitem), epg.addChannel(sitem)])
                            complete.add(station_added) 
                        else:
                            self._resetPagination(citem)
                            m3u.delStation(citem)
                            epg.delBroadcast(citem)
                    except Exception as e: 
                        self.log(f"Channel compiler faulted critically at index execution point: {str(e)}", xbmc.LOGERROR)

            if any(changes): self.channels.setChannels()
            self.log("Channel compilation loop finished successfully.")
            return preview_results if preview else None


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
        
        
    def buildVideo(self, citem: dict, validate: bool = False):
        paths = citem.get('path', [])
        if isinstance(paths, (str, bytes)):
            paths = [paths]
        path_len = len(paths)

        tmp_citem = citem.copy()
        if paths == ["{Seasonal}"]:
            nrules = {800: {"values": {0: list(self.seasonal.buildSeasonal(self.holiday))}}}
            tmp_citem.setdefault('rules', {}).update(nrules)
            self.log(f" [{citem.get('id')}] buildVideo: Seasonal Content, new rules = {nrules}")
            
        if self.enableEven and not tmp_citem.get('rules', {}).get(1000):
            nrules = {1000: {"values": {0: Globals.settings.getSettingInt('Enable_Even'), 1: self.evenEpisode, 2: self.evenShuffle}}}
            tmp_citem.setdefault('rules', {}).update(nrules)
            self.log(f" [{citem.get('id')}] buildVideo: Even Show Distribution, new rules = {nrules}")
            
        citem = tmp_citem
        fileArray = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE, citem, list(), inherited=self) 
        self.log(f"[{citem.get('id')}] buildVideo, channel pre fileArray items = {len(fileArray)}", xbmc.LOGINFO)
        
        has_valid_files = any(len(sublist) > 0 for sublist in fileArray if isinstance(sublist, list))
        if not has_valid_files: 
            for idx, base_path in enumerate(paths):
                if self.service.pendingInterrupt:
                    self.log(f"[{citem.get('id')}] buildVideo, _interrupt")
                    self.pDialog = Globals.dialog._updateProgress(self.pDialog, self.pCount, message=f"{LANGUAGE(32144)}: {LANGUAGE(32213)}", header=self.pHeader)
                    return []
                elif self.service.pendingSuspend:
                    self.log(f"[{citem.get('id')}] buildVideo, _suspend")
                    if not self.service._sleep(CPU_CYCLE): 
                        continue
                
                if path_len > 1: self.pName = f"{citem.get('name', '')} {idx + 1}/{path_len}"
                sub_paths = self.xsp.parseXSP(citem.get('id'), base_path) if self.xsp.isXSP(base_path) else [base_path]
                if self.sort.get("method", "") == 'random':
                    self.log(f"[{citem.get('id')}] buildVideo, random shuffling [{idx}/{len(sub_paths)}]")
                    sub_paths = Globals._randomShuffle(sub_paths)               

                sub_path_len = len(sub_paths)
                for cnt, path in enumerate(sub_paths):
                    if sub_path_len > 1:
                        self.pName = f"{citem.get('name', '')} {idx + 1}/{path_len}\n{cnt + 1}/{sub_path_len}"
                        
                    self.pDialog = Globals.dialog._updateProgressThrottled(self.pDialog, self.pCount, message=f'{self.pName}', header=self.pHeader)
                    processed_path = self.runActions(RULES_ACTION_CHANNEL_BUILD_PATH, citem, path, inherited=self)
                    fileList = self.buildFileList(citem, processed_path, 'video', self.limit, self.sort, self.limits, self.query)
                    
                    if isinstance(fileList, list): 
                        fileArray.append(fileList)
                        if validate and len(fileList) > 0: 
                            break
                            
                    self.log(f"[{citem.get('id')}] buildVideo, validate = {validate}, fileList [{len(fileList)}/{sum(len(sublist) for sublist in fileArray if isinstance(sublist, list))}], path [{cnt}/{self.limit}]\n{path}")
                if validate and any(len(sublist) > 0 for sublist in fileArray if isinstance(sublist, list)):
                    break

        fileArray = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST, citem, fileArray, inherited=self) 
        if isinstance(fileArray, list):
            self.log(f"[{citem.get('id')}] buildVideo, channel post fileArray items = {len(fileArray)}", xbmc.LOGINFO)
            if not any(len(sublist) > 0 for sublist in fileArray if isinstance(sublist, list)):
                self.log(f"[{citem.get('id')}] buildVideo, channel fileArray In-Valid!", xbmc.LOGINFO)
                return False
                
            interleaved = Globals._interleave(fileArray, self.interleaveSet, self.interleaveRepeat)
            fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE, citem, interleaved, inherited=self)
            self.log(f"[{citem.get('id')}] buildVideo, pre fileList items = {len(fileList)}", xbmc.LOGINFO)
            fileList = self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_POST, citem, fileList, inherited=self)
            self.log(f"[{citem.get('id')}] buildVideo, post fileList items = {len(fileList)}", xbmc.LOGINFO)
        else:
            fileList = fileArray if isinstance(fileArray, list) else []
        return self.runActions(RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN, citem, fileList, inherited=self)


    def buildFileList(self, citem: dict, path: str, media: str = 'video', page: int = None, sort = None, limits = None, query = None) -> list:
        if page is None:   page   = Globals.settings.getSettingInt('Page_Limit')
        if sort is None:   sort   = {}
        if limits is None: limits = {"end": -1, "start": 0, "total": 0}
        if query is None:  query  = {}
        self.log(f"[{citem.get('id')}] buildFileList, path = {path}\nmedia = {media}, limit = {page}, sort = {sort}, page = {limits}")
        self.loopback = None

        if self.xsp.isDXSP(path):
            path = self.xsp.parseDXSP(citem.get('id'), path, self.filter, self.incExtras)
     
        fileList = []
        dirCount = -1
        dirList  = [{'file': path}]
        self.log(f"[{citem.get('id')}] buildFileList, path = {path}\nsort = {sort}, limits = {limits}, page = {page}")
        
        while not self.monitor.abortRequested():
            if self.service.pendingInterrupt:
                self.log(f"[{citem.get('id')}] buildFileList, _interrupt")
                self.pDialog = Globals.dialog._updateProgress(self.pDialog, self.pCount, message=f"{LANGUAGE(32144)}: {LANGUAGE(32213)}", header=self.pHeader)
                return []
            
            elif self.service.pendingSuspend:
                self.log(f"[{citem.get('id')}] buildFileList, _suspend")
                self.pDialog = Globals.dialog._updateProgress(self.pDialog, self.pCount, message=f"{LANGUAGE(32144)}: {LANGUAGE(32145)}", header=self.pHeader)
                if not self.service._sleep(CPU_CYCLE): 
                    continue
            
            elif len(dirList) == 0 or dirCount >= self.recursiveLimit:
                list_len = len(fileList)
                if self.padFilelist and 0 < list_len < page: 
                    self.log(f"[{citem.get('id')}] buildFileList, __padFileList processing")
                    multiplier = page // list_len
                    remainder  = page % list_len
                    paddedList = fileList * multiplier
                    if remainder > 0: paddedList.extend(fileList[:remainder])
                    self.pDialog = Globals.dialog._updateProgressThrottled(self.pDialog, self.pCount, message=f'padding {remainder} files', header=self.pHeader)
                    fileList = paddedList
                    
                elif list_len < page and len(dirList) > dirCount: self.pErrors.append(LANGUAGE(32262))
                self.log(f"[{citem.get('id')}] buildFileList, no more folders to parse or recursive limit met.")
                break
                
            else:
                dirCount += 1
                folder   = dirList.pop(0)
                current_path = folder.get('file')
                
                if folder.get("label"): 
                    self.pDialog = Globals.dialog._updateProgressThrottled(self.pDialog, self.pCount, message=f'parsing folder: {folder.get("label")}', header=self.pHeader)
                
                remaining_needed = abs(page - len(fileList))
                subfileList, subdirList, limits, errors = self.buildList(citem, current_path, media, remaining_needed, sort, limits, folder, query)
                if sort.get("method", "") == 'random':
                    self.log(f"[{citem.get('id')}] buildFileList, depth [{dirCount}/{self.recursiveLimit}], random shuffling")
                    if isinstance(subdirList, list):  subdirList  = Globals._randomShuffle(subdirList)
                    if isinstance(subfileList, list): subfileList = Globals._randomShuffle(subfileList)
                    
                if isinstance(subfileList, list): 
                    fileList.extend(subfileList)
                    
                if isinstance(subdirList, list):  
                    dirList.extend(subdirList)
                    dirList = Globals._setDictLST(dirList)
                self.log(f"[{citem.get('id')}] buildFileList, depth [{dirCount}/{self.recursiveLimit}], adding fileList [{len(fileList)}/{page}] remaining sub-directories [{len(dirList)}]\npath = {current_path}, limits = {limits}")
        self.log(f"[{citem.get('id')}] buildFileList, depth [{dirCount}/{self.recursiveLimit}], returning fileList [{len(fileList)}/{page}]")
        return fileList


    def buildList(self, citem: dict, path: str, media: str = 'video', page: int = None, sort = None, limits = None, dirItem = None, query = None):
        if page is None:    page    = Globals.settings.getSettingInt('Page_Limit')
        if sort is None:    sort    = {}
        if limits is None:  limits  = {"end": -1, "start": 0, "total": 0}
        if dirItem is None: dirItem = {}
        if query is None:   query   = {}
        self.log(f"[{citem.get('id')}] buildList, media = {media}, path = {path}\npage = {page}, sort = {sort}, query = {query}, limits = {limits}\ndirItem = {dirItem}")
        
        nlimits = limits
        pre_items = self.runActions(RULES_ACTION_CHANNEL_REQUEST_FILELIST_PRE, citem, [], inherited=self)
        items, nlimits, errors = self.jsonRPC.requestList(citem, path, media, page, sort, self.filter, limits, query)
        if not items and pre_items: items = pre_items
        items = self.runActions(RULES_ACTION_CHANNEL_REQUEST_FILELIST_POST, citem, items, inherited=self)
        
        error_msg = errors.get('message') if isinstance(errors, dict) else None
        if error_msg:
            self.pErrors.append(error_msg)
            return [], [], nlimits, errors
            
        if not items:
            self.log(f"[{citem.get('id')}] buildList, no request items found using path = {path}")
            self.pErrors.append(LANGUAGE(32026))
            return [], [], nlimits, errors
            
        if items == self.loopback and limits != nlimits:
            self.log(f"[{citem.get('id')}] buildList, loopback detected using path = {path}")
            self.pErrors.append(LANGUAGE(32030))
            return [], [], nlimits, errors
            
        self.loopback = items
        fileList, dirList = self.buildFiles(citem, path, items, media, page, sort, limits, dirItem, query)
        if len(fileList) == 0 and isinstance(dirList, list):
            has_matching_dir = any(
                path == d or (isinstance(d, dict) and d.get('file') == path) 
                for d in dirList
            )
            if has_matching_dir:
                self.jsonRPC.autoPagination(citem.get('id'), path, query, limits)
                
        self.log(f"[{citem.get('id')}] buildList, returning fileList [{len(fileList)}], dirList [{len(dirList)}]")
        return fileList, dirList, nlimits, errors


    def buildFiles(self, citem: dict, path: str, items: list = None, media: str = 'video', page: int = None, sort = None, limits = None, dirItem = None, query = None):
        if items is None:   items   = []
        if page is None:    page    = Globals.settings.getSettingInt('Page_Limit')
        if sort is None:    sort    = {}
        if limits is None:  limits  = {"end": -1, "start": 0, "total": 0}
        if dirItem is None: dirItem = {}
        if query is None:   query   = {}
        fileList, dirList, seasoneplist = [], [], []
        items_len = len(items)
        vfs_tuple = tuple(VFS_TYPES) if 'VFS_TYPES' in globals() else ()
        tv_tuple  = tuple(TV_TYPES) if 'TV_TYPES' in globals() else ()
        
        holiday   = None
        holiday_values = citem.get('rules', {}).get(800, {}).get('values', {}).get(0, [])
        if holiday_values and isinstance(holiday_values, list):
            holiday = holiday_values[0].get('holiday') if isinstance(holiday_values[0], dict) else None

        default_type = query.get('key', 'files')
        sort_method = sort.get("method", "")
        for idx, item in enumerate(items):
            if not isinstance(item, dict): continue
            
            file = item.get('file', '')
            fileType = item.get('filetype', 'file')
            
            if items_len > 0:
                self.fCount = int(idx * 100) // items_len
                if self.cCount == 1: 
                    self.pCount = max(0, min(self.fCount, 99))
                    self.fCount = -1

            if not item.get('type'): 
                item['type'] = default_type

            if self.service.pendingInterrupt or self.service.pendingSuspend:
                self.log(f"[{citem.get('id')}] buildFiles, _interrupt/_suspend")
                self.pDialog = Globals.dialog._updateProgressThrottled(self.pDialog, self.pCount, message=f"{LANGUAGE(32144)}: {LANGUAGE(32213)}", header=self.pHeader)
                break

            if fileType == 'directory':
                dirList.append(item)
                continue
            elif fileType != 'file':
                continue

            suffix = "" if self.fCount < 0 else f": {self.fCount}%"
            self.pDialog = Globals.dialog._updateProgressThrottled(self.pDialog, self.pCount, message=f'{self.pName}{suffix}', header=self.pHeader)

            if file.startswith('pvr://'):
                self.log(f"[{citem.get('id')}] buildFiles, IDX = {idx}, PVR item => FileItem! file = {file}", xbmc.LOGINFO)
                item = Globals._decodePlot(item.get('plot', ''))
                file = item.get('file', '')

            if not file:
                self.pErrors.append(LANGUAGE(32031))
                self.log(f"[{citem.get('id')}] buildFiles, IDX = {idx}, skipping missing playable file! path = {path}", xbmc.LOGINFO)
                continue

            if file.lower().endswith('strm') and not self.incStrms: 
                self.pErrors.append(f"{LANGUAGE(32027)} STRM")
                self.log(f"[{citem.get('id')}] buildFiles, IDX = {idx}, skipping strm file! file = {file}", xbmc.LOGINFO)
                continue

            if not self.inc3D and self.is3D(item):
                item['is3D'] = True
                self.pErrors.append(f"{LANGUAGE(32027)} 3D")
                self.log(f"[{citem.get('id')}] buildFiles, IDX = {idx} skipping 3D file! file = {file}", xbmc.LOGINFO)
                continue

            # Fetch Missing Stream Details Metadata (Kodi JSON-RPC bug workaround)
            if self.incStrmDetails and not file.startswith(vfs_tuple):
                if not item.get('streamdetails', {}).get('video', []):
                    item['streamdetails'] = self.jsonRPC.getStreamDetails(file, media)

            label = item.get("title") or item.get("label") or dirItem.get('label') or ''
            if not label:  
                self.pErrors.append(LANGUAGE(32018)(LANGUAGE(30188)))
                continue
                
            # Normalize Metadata Schemas (TV Shows vs Movies)
            is_tv_show = item['type'].startswith(tv_tuple) or "showtitle" in item
            
            if is_tv_show:
                tvtitle = item.get("showtitle") or item.get("label") or dirItem.get('label') or ''
                try:
                    season  = int(item.get("season", 0))
                    episode = int(item.get("episode", 0))
                except (ValueError, TypeError):
                    season, episode = 0, 0
                    
                if not file.startswith(vfs_tuple) and not self.incExtras and (season == 0 or episode == 0):
                    self.pErrors.append(f"{LANGUAGE(32027)} Extras")
                    self.log(f"[{citem.get('id')}] buildFiles, IDX = {idx} skipping extras! file = {file}", xbmc.LOGINFO)
                    continue

                label = tvtitle
                item["tvshowtitle"]  = tvtitle
                item["episodetitle"] = label
                item["episodelabel"] = f"{label} ({season}x{str(episode).zfill(2)})"
                item["showlabel"]    = f"{tvtitle} - {item['episodelabel']}" if item['episodelabel'] else tvtitle
            else:
                tagline = item.get("tagline", "")
                item["episodetitle"] = tagline
                item["episodelabel"] = tagline
                item["showlabel"]    = f"{item.get('title', '')} - {tagline}" if tagline else item.get('title', '')
            
            # Duration Validation
            dur = self.jsonRPC.getDuration(file, item, self.accurateDuration, self.saveDuration)
            if dur > self.minDuration:
                self.pDialog = Globals.dialog._updateProgressThrottled(self.pDialog, self.pCount, message=f'{self.pName}{suffix}', header=self.pHeader)
                item.update({
                    'duration'    : dur,
                    'media'       : media,
                    'originalpath': path,
                    'friendly'    : Globals.properties.getFriendlyName(),
                    'remote'      : Globals.properties.getRemoteHost()
                })
                    
                if item.get("year", 0) == 1601: 
                    item['year'] = 0
                    
                spTitle, spYear = Globals._splitYear(label)
                item['label'] = spTitle
                    
                if item.get('year', 0) == 0 and spYear: 
                    item['year'] = spYear
                    
                raw_plot = item.get("plot") or item.get("plotoutline") or item.get("description") or LANGUAGE(32020)
                item['plot'] = raw_plot.strip()
                    
                if holiday:
                    tagline_str = f" - [I]{holiday['tagline']}[/I]" if holiday.get("tagline") else ""
                    item["plot"] = f"[B]{holiday.get('name', '')}[/B]{tagline_str}\n{item['plot']}"
                    
                item['art'] = item.get('art', {}) or dirItem.get('art', {})
                item['art']['icon'] = citem.get('logo', '')
                    
                if item.get('trailer') and hasattr(self.service,'_que'): 
                    self.service._que(self.jsonRPC.addTrailer, 3, 0, 0, item)
                    
                if sort_method == 'episode' and (season + episode) > 0: 
                    seasoneplist.append((season, episode, item))
                else: 
                    fileList.append(item)
            else: 
                self.pErrors.append(LANGUAGE(32032))
                self.log(f"[{citem.get('id')}] buildFiles, IDX = {idx} skipping content: duration too low ({dur}/{self.minDuration}) file = {file}", xbmc.LOGINFO)
        
        if sort_method == 'episode':
            self.log(f"[{citem.get('id')}] buildFiles, sorting by episode")
            seasoneplist.sort(key=lambda seep: (seep[0], seep[1]))
            fileList.extend(seep[2] for seep in seasoneplist)
                
        elif sort_method == 'random':
            self.log(f"[{citem.get('id')}] buildFiles, random shuffling")
            dirList  = Globals._randomShuffle(dirList)
            fileList = Globals._randomShuffle(fileList)
            
        self.log(f"[{citem.get('id')}] buildFiles, returning ({len(fileList)}) files, ({len(dirList)}) dirs")
        return fileList, dirList


    def is3D(self, item: dict) -> bool:
        if 'is3D' in item: return item['is3D']
        elif not item.get('streamdetails',{}).get('video',[]) and not item.get('file','').startswith(tuple(VFS_TYPES)):
            item['streamdetails'] = self.jsonRPC.getStreamDetails(item.get('file'), item.get('media','video'))
        details = item.get('streamdetails',{})
        if 'video' in details and details.get('video') != [] and len(details.get('video')) > 0:
            if len(details['video'][0]['stereomode'] or []) > 0: return True
        return False


    def _resetPagination(self, citem):
        if isinstance(citem, list): return any([self.jsonRPC.resetPagination(item) for item in citem])
        return any([self.jsonRPC.resetPagination(citem.get('id'), path) for path in citem.get('path',[]) if citem.get('id')])
    