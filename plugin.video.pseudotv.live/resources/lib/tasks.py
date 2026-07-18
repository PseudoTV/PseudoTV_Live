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
#
# -*- coding: utf-8 -*-

from typing         import Any, Callable, Optional
from variables      import *
from m3u            import M3U
from xmltvs         import XMLTVS
from backup         import Backup
from library        import Library
from builder        import Builder
from channels       import Channels
from multiroom      import Multiroom
from server         import HTTP, Discovery
from context_create import _autotune

_VERSION_RE = re.compile('" version="(.+?)" name="%s"'%(ADDON_NAME))

class Tasks(object):
    citems = []
    
    def __init__(self, service: Any):
        self.service   = service       
        self.pool      = service.pool
        self.jsonRPC   = service.jsonRPC
        self.player    = service.player
        self.monitor   = service.monitor
        self.cache     = service.cache


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def _client(self):
        """Run client-side initialization."""
        self.service._que(self.chkPVRBackend    ,1)
        self.service._que(self.chkHTTP          ,1)
        self.service._que(self.chkDebugging     ,1)
        self.service._que(self.chkVersion       ,1)
        self.service._que(self.chkKodiSettings  ,1)
        self.service._que(self.chkDiscovery     ,1)
        self.service._que(self.chkQUES          ,1)
        self.log('_client, initialized')
        
        
    def _host(self):
        """Initialize host-side checks and setup."""
        self.service._que(self.chkDirs          ,1)
        self.service._que(self.chkCrash         ,1)
        self.service._que(self.chkPVRSync       ,1)
        self.service._que(self.chkLibrary       ,2)
        self.service._que(self.chkTrailers      ,5)
        self.log('_initialize, _host...')
    
    
    def _migrateChannels(self, old: str = CACHE_LOC, new: str = BACKUP_LOC):
        """Migrate channel files from old location to new backup location."""
        old_path = os.path.join(old,CHANNELFLE)
        new_path = os.path.join(new,CHANNELFLE)
        if FileAccess.exists(old_path):
            self.log('migrate, importing %s...'%(old_path))
            if Backup().importChannels(old_path): Globals.properties.setPendingRestart(True)
            if FileAccess.move(old_path,new_path): Globals.dialog.notificationDialog(LANGUAGE(32025))
                  
   
    def chkPVRBackend(self):
        """Check and configure PVR backend addon."""
        instanceName = Globals.properties.getFriendlyName()
        hasPVR       = Globals.settings.hasAddon(PVR_CLIENT_ID,enable=True,notify=True)
        self.log('chkPVRBackend, instanceName = %s, hasPVR = %s'%(instanceName,hasPVR))
        if hasPVR:
            Globals.settings.instances.chkInstances(instanceName)
            Globals.settings.setPVRLocal(Globals.properties.getRemoteHost(),instanceName)
            


    def chkHTTP(self):
        """Start HTTP server instance."""
        timerit(HTTP)(0.1,self.service)
        Globals.properties.setEXTProperty(f'{ADDON_ID}.Local_Host', self.jsonRPC.getLocalHost())
        self.log('chkHTTP')
        
        
    def chkDebugging(self, disable: bool = False):
        """Check and manage debug settings, optionally force disable."""
        kodi_access = Globals.settings.getSettingBool('Enable_Kodi_Access')
        self.log(f'chkDebugging, disable = {disable}, kodi access = {kodi_access}')
        if disable: Globals.settings.setSettingBool('Debug_Enable',False)
        if Globals.settings.getSettingBool('Debug_Enable'):
            if not Globals.settings.getSettingBool('Debug_Keep_Enable'):
                if Globals.dialog.yesnoDialog('%s\n%s'%(LANGUAGE(32142),LANGUAGE(32266).format(minutes=DEBUG_TIMEOUT//60)) ,autoclose=4):
                    self.log('_chkDebugging, disabling debugging.')
                    Globals.settings.setSettingBool('Debug_Enable',False)
                elif kodi_access: self.service._que(self.chkDebugging,0,DEBUG_TIMEOUT,0,True) # Auto disable.
        if kodi_access: self.jsonRPC.toggleShowLog(Globals.settings.getSettingBool('Debug_Enable'))
                    
             
    def chkDiscovery(self):
        """Start discovery service and schedule periodic refresh."""
        timerit(Discovery)(0.1,*(self.service, Multiroom(service=self.service)))
        self.log('chkDiscovery')
        self.service._que(self.chkDiscovery,1,300)#5MINS
         


    def chkCrash(self):
        """Check for Kodi crash data and handle recovery."""
        citem = Globals.settings.getCacheSetting('KODI.CRASH.JSONRPC.CITEM', default={})
        Globals.settings.setCacheSetting('KODI.CRASH.JSONRPC.CITEM',None)
        if citem:
            self.log('chkCrash\n%s'%(citem))
            # with Globals.builtin.busy_dialog(), Globals.properties.suspendActivity():
                # channels = Channels(writable=True)
                # chanLST  = channels.getChannels()
                # idx, channel = channels.findChannel(citem, chanLST)
                # chanLST[idx].update({'enabled':False})
                # if channels.setChannels(chanLST):
                    # Globals.dialog.okDialog(f'Kodi encountered a fatal crash while parsing a [B]{ADDON_NAME}[\B] channel.\nPlease check the channel configuration for [B]{citem.get('name')}[\B]\n Channel [B]{citem.get('number')}[\B] temporarily disabled!', usethread=False)
                # del channels
  
  
    def chkQueTimer(self):
        """Check property timers and trigger queued operations."""
        self.log('chkQueTimer')
        self._chkPropTimer('chkChannels'  , self.chkChannels  , 3)
        self._chkPropTimer('chkPVRRefresh', self.chkPVRRefresh, 4)
        self.service._que(self.chkQueTimer, 3, TASK_INTERVAL)
        
        
    def _chkPropTimer(self, key: str, func: Callable, priority: int = -1):
        """Check if a property timer is set and run the associated function."""
        state, args, kwargs = Globals.properties.getPropTimer(key)
        if state:
            self.log('_chkPropTimer, key = %s'%(key))
            Globals.properties.clrEXTProperty(key)
            self.service._que(func, priority, 0, 0, *args, **kwargs)


    def chkVersion(self):
        """Check for addon updates and show changelog if version changed."""
        try:              ONLINE_VERSION = _VERSION_RE.findall(str(self.jsonRPC.requestURL(ADDON_URL)))[0]
        except Exception as e: 
            self.log(f'chkVersion, failed to check online version: {e}', xbmc.LOGWARNING)
            ONLINE_VERSION = ADDON_VERSION
        UPDATE_AVAILABLE = False
        LAST_VERSION = Globals.settings.getCacheSetting('chkVersion.LAST_VERSION', default='0.0.0')
        if ADDON_VERSION < ONLINE_VERSION:
            UPDATE_AVAILABLE = True
            Globals.dialog.notificationDialog(LANGUAGE(30073).format(version=ONLINE_VERSION))
        elif ADDON_VERSION != LAST_VERSION:
            Globals.settings.setCacheSetting('chkVersion.LAST_VERSION', ADDON_VERSION)
            Globals.builtin.executescript('special://home/addons/%s/resources/lib/utilities.py, Show_Changelog'%(ADDON_ID))
        Globals.settings.setSetting('Update_Status',{True:'[COLOR=yellow]%s [B]v.%s[/B][/COLOR]'%(LANGUAGE(32168),ONLINE_VERSION),False:'None'}[UPDATE_AVAILABLE])
        self.log('chkVersion, installed = %s, online = %s, last = %s'%(ADDON_VERSION,ONLINE_VERSION,LAST_VERSION))
        self.service._que(self.chkVersion,1,43200)#12HRS


    def chkKodiSettings(self):
        """Check and sync Kodi settings like EPG days and OSD timer."""
        self.log('chkKodiSettings')
        Globals.settings.setSettingInt('Min_Days' ,self.jsonRPC.getSettingValue('epg.pastdaystodisplay'     ,default=1))
        Globals.settings.setSettingInt('Max_Days' ,self.jsonRPC.getSettingValue('epg.futuredaystodisplay'   ,default=3))
        Globals.settings.setSettingInt('OSD_Timer',self.jsonRPC.getSettingValue('pvrmenu.displaychannelinfo',default=5))
        self.service._que(self.chkKodiSettings,1,10800)#3HRS
         


    def chkDirs(self):
        """Create required directories if they don't exist."""
        [(self.log('chkDirs, creating [%s]'%(folder)),FileAccess.makedirs(folder)) for folder in [LOGO_LOC,FILLER_LOC,TEMP_LOC] if not FileAccess.exists(os.path.join(folder,''))]


    def chkFillers(self, channels: Optional[list] = None, silent: Optional[bool] = None):
        """Create filler folder structure for channels (bumpers, ratings, etc.)."""
        with Globals.dialog._progressDialog(f'{ADDON_NAME}, {LANGUAGE(32179)}', ADDON_NAME, silent=silent, background=True) as pDialog:
            if channels is None: channels = self.getChannels()
            if not isinstance(channels, list) or len(channels) == 0:
                self.log("chkFillers: No valid channels provided. Exiting tree scaffolding.")
                return

            def __create(idx: int, total: int, label: str, path: str) -> Any:
                FileAccess.makedirs(path)
                return Globals.dialog._updateProgress(pDialog, int((idx / max(1, total)) * 100), message=label, header=f'{ADDON_NAME}, {LANGUAGE(32179)}')

            genres = Globals._mergeDict(self.jsonRPC.getVideoGenres(type="movie"), self.jsonRPC.getVideoGenres(type="tvshow"), 'label')
            mpaas  = Globals._mergeDict(self.jsonRPC.getMPAA(type="movie"), self.jsonRPC.getMPAA(type="tvshow"), 'label')
            
            filler_len = len(FILLER_TYPES)
            for fidx, ftype in enumerate(FILLER_TYPES):
                if ftype == 'Extras': 
                    continue
                    
                ignore = {
                    'bumpers' : IGNORE_CHTYPE + MOVIE_CHTYPE, 
                    'ratings' : IGNORE_CHTYPE + TV_CHTYPE,
                    'adverts' : IGNORE_CHTYPE + MOVIE_CHTYPE, 
                    'trailers': IGNORE_CHTYPE + TV_CHTYPE
                }.get(ftype.lower(), IGNORE_CHTYPE)
                      
                fpath = os.path.join(FILLER_LOC, ftype)
                if not FileAccess.exists(fpath): 
                    pDialog = __create(fidx, filler_len, ftype, fpath)
                    
                # --- RATINGS ---
                if ftype == 'Ratings':
                    mpaas_len = len(mpaas)
                    for midx, mpaa in enumerate(mpaas):
                        mpaa_label = mpaa.get('label')
                        if mpaa_label:
                            mpath = os.path.join(fpath, mpaa_label)
                            if not FileAccess.exists(mpath): 
                                pDialog = __create(midx, mpaas_len, mpaa_label, mpath)
                    continue
                    
                # --- GENRES ---
                elif ftype in ['Bumpers', 'Adverts', 'Trailers']:
                    genres_len = len(genres)
                    for gidx, genre in enumerate(genres):
                        genre_label = genre.get('label')
                        if genre_label:
                            genre_folder_path = os.path.join(fpath, genre_label)
                            if not FileAccess.exists(genre_folder_path): 
                                pDialog = __create(gidx, genres_len, genre_label, genre_folder_path)
                                
                # --- GROUPS ---
                channels_len = len(channels)
                for cidx, channel in enumerate(channels):    
                    if channel.get('type') in ignore or channel.get('radio', False): 
                        continue
                        
                    ch_name = channel.get('name', '')
                    if not ch_name: continue
                    cpath = os.path.join(fpath, ch_name)
                    if not FileAccess.exists(cpath): 
                        pDialog = __create(cidx, channels_len, ch_name, cpath)
                            
                    if ftype in ['Bumpers', 'Adverts', 'Trailers']:
                        groups = channel.get('group', [])
                        groups_len = len(groups)
                        for gpidx, group in enumerate(groups):
                            group_folder_path = os.path.join(fpath, group)
                            if not FileAccess.exists(group_folder_path): 
                                pDialog = __create(gpidx, groups_len, group, group_folder_path)
        
        
    def chkTrailers(self, movies: Optional[list] = None, tvshows: Optional[list] = None, silent: Optional[bool] = None):
        """Check and queue trailers for movies and TV shows.
        """
        if not Globals.properties.isRunning('Tasks.chkTrailers') and Globals.settings.getSettingBool('Include_Trailers_KODI'):
            with Globals.properties.chkRunning('Tasks.chkTrailers'):
                if movies is None: movies = self.jsonRPC.getMovies()
                if tvshows is None: tvshows = self.jsonRPC.getTVshows()
                if silent is None: silent = not Globals.settings.showDialog(silent)
                self.log('chkTrailers, movies = %s, tvshows = %s, silent = %s'%(len(movies),len(tvshows), silent))
                for mv in movies: self.service.trailerQue.add(FileAccess.dumpJSON(mv, sortkey=True))
                for tv in tvshows: self.service.trailerQue.add(FileAccess.dumpJSON(tv, sortkey=True))
                self.service._que(self.chkTrailers,5,259200)#3DAYS



    def chkLibrary(self, types: Optional[list] = None, silent: Optional[bool] = None, wait: int=MIN_EPG_DURATION):
        """Check and update library for specified content types."""
        if types is None: types = AUTOTUNE_TYPES
        if silent is None: silent = not Globals.settings.showDialog(silent)
        self.log("chkLibrary, types = %s, silent = %s"%(types,silent))
        complete = set()
        library  = Library(service=self.service, writable=True)
        # library.searchRecommended()
        for idx, type in enumerate(types):
            self.log("chkLibrary, processing [%d/%d] %s" % (idx+1,len(types),type))
            items = library.getLibrary(type)
            if items:
                self.log("chkLibrary, %s library found! Setting items (%s), queuing update."%(type,len(items)))
                complete.add(library.setLibrary(type, items))
                self.log("chkLibrary, %s setLibrary done, queuing updateLibrary."%(type))
                self.service._que(library.updateLibrary,-1,0,0,*([type],True))
                self.log("chkLibrary, %s updateLibrary queued."%(type))
            else:
                self.log("chkLibrary, %s library not found! starting update."%(type))
                complete.add(library.updateLibrary([type],silent))
            self.log("chkLibrary, %s done. complete=%s" % (type,complete))
        del library
        if any(complete): self.service._que(self.chkChannels,3,0,0,*(None,silent))
        else: wait = 1800
        self.service._que(self.chkLibrary,2,wait,0,*(None,True))#30MINS
        self.log(f"chkLibrary, complete = {any(complete)}, next check in {wait} seconds.")
        
        
    def chkChannels(self, channels: Optional[list] = None, silent: Optional[bool] = None):
        """Check channels and run build or autotune if needed."""
        if channels is None: channels = self.getChannels()
        if silent is None: silent = not Globals.settings.showDialog(silent)
        # Filter for changed channels only
        channels = [ch for ch in channels if isinstance(ch, dict) and ch.get('changed', False)]
        self.log("chkChannels, channels = %s, silent = %s"%(len(channels),silent))
        if len(channels) > 0:
            # Filter out channel IDs already queued for building
            queued_ids = self.service.queue.get_queued_dedup_keys('build.')
            before = len(channels)
            channels = [ch for ch in channels if f"build.{ch.get('id')}" not in queued_ids]
            if before != len(channels):
                self.log(f"chkChannels, filtered {before - len(channels)} already-queued channels")
            if not channels:
                self.log("chkChannels, all channels already queued, skipping")
                return
            if Globals.settings.getSettingBool('Build_Filler_Folders'): self.service._que(self.chkFillers, 3, 0, 0, channels, silent)
            chunk_size = max(1, len(channels) // QUEUE_CHUNK)
            self.log(f"chkChannels, processing channels count = {len(channels)} in chunks = {chunk_size}")
            for i in range(0, len(channels), chunk_size):
                chunk = channels[i:i + chunk_size]
                # Build dedup keys for this chunk — enables cross-call deduplication
                dedup_keys = {f"build.{ch.get('id')}" for ch in chunk if ch.get('id')}
                self.log(f"chkChannels, queuing chunk {i//chunk_size + 1} with {len(chunk)} channels, dedup_keys={len(dedup_keys)}")
                self.service._que(Builder(service=self.service).buildChannels, 3, 0, 0, chunk, False, silent, True, dedup_keys=dedup_keys)
        else:
            runAutoTune  = Globals.settings.getSettingBool('Enable_Autotune')
            hasAutoTuned = Globals.settings.hasAutotuned()
            self.log(f'chkChannels, No Channels Configured! runAutoTune = {runAutoTune}, hasAutoTuned = {hasAutoTuned}')
            if any((runAutoTune, not hasAutoTuned)):
                if autotune_result is not None and Globals.settings.setAutotuned(_autotune()): 
                    Globals.properties.setPropTimer('chkChannels')# Refresh Channel Changed!
            Globals.properties.setPropTimer('chkPVRRefresh') # Refresh PVR Guide


    @debounceit(60)
    def chkPVRRefresh(self, brute: Optional[bool] = None, findings: Optional[dict] = None):
        """Refresh PVR guide data using the appropriate reload method.

        Uses updatePVRStatus data to intelligently select the refresh method.
        If findings dict is provided (from chkPVRSync), reuses it to avoid
        duplicate updatePVRStatus call. Falls back to fetching fresh status.

        Decision tree (ordered by specificity, least to most invasive):
          1. PVR not connected                     -> triggerReload
          2. Local M3U empty + local XMLTV empty   -> chkLibrary (full rebuild)
          3. Local M3U has channels + XMLTV empty  -> chkChannels for M3U station IDs (not full rebuild)
          4. Local M3U+XMLTV have data, PVR missing channels -> chkChannels for missing IDs
          5. Local M3U==XMLTV, PVR different set   -> PVRScan (re-read files)
          6. Files stale/outdated                   -> triggerReload (force cache refresh)
          7. PVR errors                             -> triggerReload (retry)
          8. Channels with no EPG data              -> chkChannels (rebuild to populate guide)
          9. Brute (last resort)                    -> togglePVRBackend (only when player inactive)
        """
        if brute is None: brute = Globals.settings.getSettingBool('Enable_PVR_RELOAD')
        self.log(f"chkPVRRefresh, called (brute={brute}, isRunning={Globals.properties.isRunning('Tasks.chkPVRRefresh')})", xbmc.LOGDEBUG)

        if not Globals.properties.isRunning('Tasks.chkPVRRefresh'):
            with Globals.properties.chkRunning('Tasks.chkPVRRefresh'):
                # Cooldown: skip if we triggered a refresh within the last 90s
                last_refresh = Globals.settings.getCacheSetting('chkPVRRefresh.LAST_RUN', default=0)
                if time.time() - last_refresh < 90 and not brute:
                    self.log(f"chkPVRRefresh, cooldown ({int(time.time() - last_refresh)}s since last refresh), skipping", xbmc.LOGDEBUG)
                    return
                Globals.settings.setCacheSetting('chkPVRRefresh.LAST_RUN', time.time())

                # Use findings if provided, otherwise fetch fresh
                if findings is not None:
                    status = findings.get('status', {})
                else:
                    status = Globals.settings.instances.updatePVRStatus(Globals.properties.getRemoteHost(),Globals.properties.getFriendlyName())
                    findings = {'status': status, 'missing_epg': [], 'epg_expired': [], 'rebuild_ids': set(), 'pvr_no_channels': False}

                pvr_connected   = status['log'].get('pvr_connected', True)
                m3u_ids         = set(status['m3u'].get('channel_ids', []))
                xmltv_ids       = set(status['xmltv'].get('channel_ids', []))
                pvr_ids         = set(status['log'].get('pvr_channel_ids', []))
                xmltv_programs  = status['xmltv'].get('programmes', 0)
                missing_ids     = status['m3u'].get('unloaded_by_pvr', [])
                m3u_sync        = status['m3u']['sync_state']
                xmltv_sync      = status['xmltv']['sync_state']
                has_errors      = len(status['log'].get('pvr_errors', [])) > 0

                # Files fresh and PVR connected: PVR is still loading, wait instead of rebuild
                # BUT if M3U has channels that PVR hasn't loaded yet, trigger reload
                m3u_fresh   = m3u_sync == 'fresh'
                xmltv_fresh = xmltv_sync == 'fresh'
                if m3u_fresh and xmltv_fresh and pvr_connected and not has_errors:
                    unloaded = status['m3u'].get('unloaded_by_pvr', [])
                    if unloaded:
                        self.log(f"chkPVRRefresh, files fresh but PVR missing {len(unloaded)} channels, triggering reload", xbmc.LOGWARNING)
                        Globals.settings.instances.triggerReload()
                    else:
                        self.log("chkPVRRefresh, files fresh and PVR connected, waiting for PVR to load", xbmc.LOGDEBUG)
                    return

                #1 PVR not connected - wait for reconnection
                if not pvr_connected:
                    self.log("chkPVRRefresh, #1 PVR not connected, triggerReload", xbmc.LOGWARNING)
                    Globals.settings.instances.triggerReload()
                    return

                #2 Local M3U empty + local XMLTV empty - no files exist, full rebuild needed
                if not m3u_ids and not xmltv_programs:
                    self.log("chkPVRRefresh, #2 Local M3U+XMLTV empty, chkLibrary (full rebuild)", xbmc.LOGWARNING)
                    self.chkLibrary()
                    return

                #2b Channels in channels.json but not in M3U - mark as changed for rebuild
                channels = Channels(getChannelKey(), writable=True)
                all_channels = channels.getChannels()
                m3u_name_map = {}
                with M3U() as m3u:
                    for station in m3u.getStations():
                        if station.get('name'): m3u_name_map[station['name']] = station.get('id')
                missing_from_m3u = [ch for ch in all_channels if ch.get('name') and ch['name'] not in m3u_name_map and ch.get('id') and ch.get('path')]
                if missing_from_m3u:
                    for ch in missing_from_m3u:
                        ch['changed'] = True
                    channels.setChannels()
                    self.log(f"chkPVRRefresh, #2b {len(missing_from_m3u)} channels missing from M3U, marking changed for rebuild", xbmc.LOGWARNING)
                    del channels
                    self.service._que(self.chkChannels, 3, 0, 0, missing_from_m3u, True)
                    return
                del channels

                #3 Local M3U has channels + local XMLTV empty - channels exist but no programme data
                if m3u_ids and not xmltv_programs:
                    self.log(f"chkPVRRefresh, #3 Local M3U has {len(m3u_ids)}ch but no XMLTV, rebuilding specific channels", xbmc.LOGWARNING)
                    try:
                        with M3U() as m3u:
                            m3u_stations = m3u.getStations()
                            rebuild = [ch for ch in m3u_stations if ch.get('id') in m3u_ids]
                            if rebuild:
                                self.service._que(self.chkChannels, 3, 0, 0, rebuild, True)
                            else:
                                self.log("chkPVRRefresh, #3 no matching M3U stations found, skipping", xbmc.LOGDEBUG)
                    except Exception as e:
                        self.log(f"chkPVRRefresh, #3 chkChannels error: {e}", xbmc.LOGDEBUG)
                    return

                #4 Local M3U+XMLTV have data, PVR missing some channels - rebuild missing ones
                if m3u_ids and xmltv_programs > 0 and missing_ids:
                    self.log(f"chkPVRRefresh, #4 PVR missing {len(missing_ids)} channels, chkChannels", xbmc.LOGWARNING)
                    try:
                        with M3U(writable=True) as m3u, XMLTVS(writable=True, m3u=m3u) as epg:
                            m3u_stations = m3u.getStations()
                            rebuild = [ch for ch in m3u_stations if ch.get('id') in missing_ids]
                            if rebuild:
                                self.service._que(self.chkChannels, 3, 0, 0, rebuild, True)
                            else:
                                # Missing IDs not in local M3U - check if channels exist in channels.json
                                # If not, they're abandoned: remove from M3U/XMLTV and trigger refresh
                                try:
                                    with Channels() as channels:
                                        ch_ids = {ch.get('id') for ch in channels.getChannels()}
                                    orphan_ids = [ch_id for ch_id in missing_ids if ch_id not in ch_ids]
                                    if orphan_ids:
                                        self.log(f"chkPVRRefresh, #4 removing {len(orphan_ids)} abandoned channels not in channels.json: {orphan_ids}", xbmc.LOGWARNING)
                                        for ch_id in orphan_ids:
                                            m3u.delStation({'id': ch_id})
                                            epg.delBroadcast({'id': ch_id})
                                        Globals.settings.instances.triggerReload()
                                except Exception as e:
                                    self.log(f"chkPVRRefresh, #4 orphan cleanup error: {e}", xbmc.LOGDEBUG)
                    except Exception as e:
                        self.log(f"chkPVRRefresh, #4 chkChannels error: {e}", xbmc.LOGDEBUG)
                    else:
                        return

                #5 M3U+XMLTV in sync with each other, PVR has different set - tell PVR to re-read
                if m3u_ids == xmltv_ids and pvr_ids != m3u_ids and pvr_ids:
                    self.log("chkPVRRefresh, #5 PVR set differs from M3U+XMLTV, PVRScan", xbmc.LOGWARNING)
                    try:
                        client_id = self.jsonRPC.getPVRClient(PVR_CLIENT_ID).get('clientid', -1)
                        if not self.jsonRPC.PVRScan(client_id).get('error'):
                            self.log("chkPVRRefresh, #5 PVRScan initiated", xbmc.LOGDEBUG)
                            return
                    except Exception as e:
                        self.log(f"chkPVRRefresh, #5 PVRScan failed: {e}", xbmc.LOGDEBUG)
                        Globals.settings.instances.triggerReload()
                        return
                        
                #6 Files stale/outdated but PVR connected - force cache refresh
                if m3u_sync in ('outdated', 'unknown') or xmltv_sync in ('outdated', 'unknown'):
                    self.log(f"chkPVRRefresh, #6 Files outdated (m3u={m3u_sync}, xmltv={xmltv_sync}), triggerReload", xbmc.LOGWARNING)
                    Globals.settings.instances.triggerReload()
                    return

                #7 PVR errors - retry
                if has_errors:
                    self.log(f"chkPVRRefresh, #7 {len(status['log']['pvr_errors'])} PVR errors, triggerReload", xbmc.LOGWARNING)
                    Globals.settings.instances.triggerReload()
                    return

                #8 Channels with no EPG data - rebuild to populate guide
                missing_epg = findings.get('missing_epg', [])
                if missing_epg:
                    self.log(f"chkPVRRefresh, #8 {len(missing_epg)} channels with no EPG data, triggering rebuild", xbmc.LOGWARNING)
                    try:
                        with M3U() as m3u:
                            m3u_stations = m3u.getStations()
                            rebuild = [ch for ch in m3u_stations if ch.get('id') in missing_epg]
                            if rebuild:
                                self.service._que(self.chkChannels, 3, 0, 0, rebuild, True)
                            else:
                                self.log("chkPVRRefresh, #8 missing EPG IDs not found in M3U", xbmc.LOGDEBUG)
                    except Exception as e:
                        self.log(f"chkPVRRefresh, #8 chkChannels error: {e}", xbmc.LOGDEBUG)
                    return

                #8b Channels with EPG expiring before MIN_GUIDEDAYS - rebuild to extend guide
                epg_expired = findings.get('epg_expired', [])
                if epg_expired:
                    self.log(f"chkPVRRefresh, #8b {len(epg_expired)} channels with EPG expiring soon, triggering rebuild", xbmc.LOGWARNING)
                    try:
                        with M3U() as m3u:
                            m3u_stations = m3u.getStations()
                            rebuild = [ch for ch in m3u_stations if ch.get('id') in epg_expired]
                            if rebuild:
                                self.service._que(self.chkChannels, 3, 0, 0, rebuild, True)
                            else:
                                self.log("chkPVRRefresh, #8b expired EPG IDs not found in M3U", xbmc.LOGDEBUG)
                    except Exception as e:
                        self.log(f"chkPVRRefresh, #8b chkChannels error: {e}", xbmc.LOGDEBUG)
                    return

                #8c PVR has no channels loaded but M3U files exist - recovery
                if findings.get('pvr_no_channels', False):
                    self.log("chkPVRRefresh, #8c PVR has no channels loaded, checking recovery options...", xbmc.LOGWARNING)
                    try:
                        configured_channels = self.getChannels()
                    except Exception:
                        configured_channels = []
                    if configured_channels:
                        brute_key = 'brute_pvr_refresh.LAST_RUN'
                        last_brute = Globals.settings.getCacheSetting(brute_key, default=0)
                        elapsed = time.time() - last_brute
                        if elapsed > 900:
                            self.log(f"chkPVRRefresh, #8c triggering brute PVR refresh for {len(configured_channels)} channels", xbmc.LOGWARNING)
                            Globals.settings.setCacheSetting(brute_key, time.time())
                            Globals.properties.setPropTimer('chkPVRRefresh')
                        else:
                            self.log(f"chkPVRRefresh, #8c brute refresh skipped ({int(elapsed)}s since last attempt)", xbmc.LOGDEBUG)
                    else:
                        self.log("chkPVRRefresh, #8c no configured channels found, resetting autotune", xbmc.LOGWARNING)
                        Globals.settings.setAutotuned(False)
                        self.service._que(self.chkChannels, 2, 0, 0)
                    return

                #9 Brute force (last resort) - full addon disable/enable
                if brute:
                    if not self.service.player.isPlaying():
                        self.log("chkPVRRefresh, #9 Brute: togglePVRBackend", xbmc.LOGWARNING)
                        Globals.settings.instances.togglePVRBackend(False)
                        self.monitor.waitForAbort(M3U_REFRESH)
                        Globals.settings.instances.togglePVRBackend(True)
                    else:
                        self.log("chkPVRRefresh, #9 Brute requested but player active, triggerReload fallback", xbmc.LOGWARNING)
                        Globals.settings.instances.triggerReload()
                    return

                self.log("chkPVRRefresh, no action needed (in sync)", xbmc.LOGDEBUG)


    def chkSettingsChange(self, old_settings: dict = {}) -> dict:
        """Check for settings changes and trigger appropriate actions."""
        #if cleanstart ie del settings.xml, restore important values.
        if Globals.settings.restoreSettings(Globals.settings.getCacheSetting('Utilities._runCleanup',default={})):
            Globals.settings.setCacheSetting('Utilities._runCleanup',None)
            
        #settings changed actions.
        new_settings = Globals.settings.getCurrentSettings()
        for setting, old_value in list(old_settings.items()):
            new_value = new_settings.get(setting)
            actions = {'User_Folder'     :{'func':self.setUserPath ,'args':(old_value,new_value)},
                       'Debug_Enable'    :{'func':self.chkDebugging,'args':(new_value,)},
                       'TCP_PORT'        :{'func':Globals.properties.setPendingRestart},
                       'Enable_Autotune' :{'func':self.chkLibrary}}
                       
            if setting in actions and old_value != new_value:
                action = actions.get(setting)
                self.log('chkSettingsChange, detected change in %s: %s => %s\naction = %s'%(setting,old_value,new_value,action))
                self.service._que(action.get('func'),1,0,0,*action.get('args',()),**action.get('kwargs',{}))
        return new_settings


    def chkQUES(self):
        """Process queued requests for URLs, JSON, logos, and trailers."""
        library = Library()
        for i in list(range(BATCH_SIZE)):
            if len(self.service.postQue) > 0:
                try:
                    self.log(f"chkQUES postQue {len(self.service.postQue)}")
                    param = self.service.postQue.pop()
                    self.service._que(self.jsonRPC.requestURL,3,0,0,*param)
                except Exception as e: self.log("chkQUES failed!, queuing = %s postQue: %s\n%s"%(len(self.service.postQue),param,e))
            if len(self.service.jsonQue) > 0:
                try:
                    self.log(f"chkQUES jsonQue {len(self.service.jsonQue)}")
                    param = FileAccess.loadJSON(self.service.jsonQue.pop(), skip_cache=True)
                    self.service._que(self.jsonRPC.sendJSON,4,0,0,param)
                except Exception as e: self.log("chkQUES failed!, queuing = %s jsonQue: %s\n%s"%(len(self.service.jsonQue),param,e))
            if len(self.service.logoQue) > 0:
                try:
                    self.log(f"chkQUES logoQue {len(self.service.logoQue)}")
                    param = FileAccess.loadJSON(self.service.logoQue.pop(), skip_cache=True)
                    self.service._que(library.resources.getLogo,5,0,0,*({'name':param},library.resources.getImageCache(param),True))
                    self.service._que(self.chkLogos,5,120)#2MINS
                except Exception as e: self.log("chkQUES failed!, queuing = %s logoQue: %s\n%s"%(len(self.service.logoQue),param,e))
            if len(self.service.trailerQue) > 0:
                try:
                    self.log(f"chkQUES trailerQue {len(self.service.trailerQue)}")
                    param = FileAccess.loadJSON(self.service.trailerQue.pop(), skip_cache=True)
                    self.service._que(self.jsonRPC.addTrailer,5,0,0,param)
                except Exception as e: self.log("chkQUES failed!, queuing = %s trailerQue: %s\n%s"%(len(self.service.trailerQue),param,e))
        del library
        self.service._que(self.chkQUES ,5,120)#2MINS
        
        
    @debounceit(LOGO_REFRESH)
    def chkLogos(self):
        try:
            image_cache = Globals.settings.getCacheSetting('imageCache', default={})
            if not image_cache: return
            updated      = 0
            channels     = Channels(getChannelKey(), writable=True)
            library      = Library()
            channel_map  = {c.get('name'): c for c in channels.getChannels() if c.get('name')}
            library_data = library.getLibrary()
            library_map  = {}
            for type, items in (library_data or {}).items():
                for item in (items or []):
                    if item.get('name'): library_map[item['name']] = item
            for name, cached in image_cache.items():
                if not cached: continue
                ch = channel_map.get(name)
                if ch and cached != ch.get('logo'):
                    ch['logo'] = cached
                    ch['changed'] = True
                    updated += 1
                lib = library_map.get(name)
                if lib and cached != lib.get('logo'):
                    lib['logo'] = cached
                    updated += 1
            if updated > 0:
                channels.setChannels()
                for type, items in (library_data or {}).items():
                    library.setLibrary(type, items)
                self.log(f"chkLogos, updated {updated} logos", xbmc.LOGINFO)
                Globals.properties.setPropTimer('chkChanged')
            del channels, library
        except Exception as e: self.log(f"chkLogos, logo update failed: {e}", xbmc.LOGDEBUG)
 
     
    def setUserPath(self, old: str, new: str):
        """Copy user data folder from old path to new path."""
        self.log('setUserPath, old = %s, new = %s'%(old,new))
        dia = Globals.dialog.progressDialog(message='%s\n%s'%(LANGUAGE(32050),old))
        with Globals.properties.interruptActivity():
            FileAccess.copyFolder(old, new, dia)
        Globals.properties.setPendingRestart()
        Globals.dialog.progressDialog(100, dia)


    def getChannels(self) -> list:
        """Get list of configured channels."""
        return Channels(getChannelKey()).getChannels()
        
        
    def getLibrary(self, type: Optional[str] = None) -> Any:
        """Get library items for specified content type."""
        Library(service=self.service).getLibrary(type)


    def chkPVRSync(self, host=None, friendly=None) -> tuple:
        """Check if PseudoTV files are in sync with Kodi's PVR state.
        
        Pure state checker — gathers data but does NOT trigger actions.
        Returns (in_sync: bool, findings: dict) for callers to act on.
        
        findings keys:
            status        - full updatePVRStatus dict
            missing_epg   - list of channel IDs with no EPG data
            epg_expired   - list of channel IDs with EPG expiring before MIN_GUIDEDAYS
            orphan_ids    - list of XMLTV channel IDs not in local M3U
            rebuild_ids   - set of all channel IDs needing rebuild
            pvr_no_channels - bool: PVR connected but no channels loaded
        """
        if host is None: host = Globals.properties.getRemoteHost()
        if friendly is None: friendly = Globals.properties.getFriendlyName()
        findings = {'status': {}, 'missing_epg': [], 'epg_expired': [], 'orphan_ids': [], 'rebuild_ids': set(), 'pvr_no_channels': False}
        try:
            status = Globals.settings.instances.updatePVRStatus(host,friendly)
            findings['status'] = status

            m3u_synced   = status['m3u']['sync_state']    in ('fresh', 'stale')
            xmltv_synced = status['xmltv']['sync_state']  in ('fresh', 'stale')
            has_errors   = len(status['log']['pvr_errors']) > 0
            has_channels = status['m3u']['channels'] > 0
            has_programs = status['xmltv']['programmes'] > 0
            pvr_connected = status['log'].get('pvr_connected', True)
            in_sync      = m3u_synced and xmltv_synced and has_channels and has_programs and not has_errors

            # Detect PVR no-channels state: PVR connected, files exist, but PVR hasn't loaded them
            pvr_has_tv = Globals.builtin.getInfoBool('Pvr.HasTVChannels')
            pvr_has_radio = Globals.builtin.getInfoBool('Pvr.HasRadioChannels')
            findings['pvr_no_channels'] = pvr_connected and not pvr_has_tv and not pvr_has_radio and has_channels

            if not in_sync:
                reasons = []
                if not has_channels:  reasons.append('no M3U channels')
                if not has_programs:  reasons.append('no XMLTV programmes')
                if status['m3u']['sync_state'] == 'outdated':   reasons.append('M3U outdated')
                if status['xmltv']['sync_state'] == 'outdated':  reasons.append('XMLTV outdated')
                if has_errors: reasons.append(f'{len(status["log"]["pvr_errors"])} PVR errors')
                if not pvr_connected: reasons.append('PVR client not connected')
                self.log(f"chkPVRSync, out of sync: {', '.join(reasons)}", xbmc.LOGWARNING)
            else:
                self.log(f"chkPVRSync, in sync: m3u={status['m3u']['channels']}ch, xmltv={status['xmltv']['channels']}ch/{status['xmltv']['programmes']}prog")
                rebuild_ids = set()
                rebuild_ids.update(status.get('m3u', {}).get('unloaded_by_pvr', []))
                rebuild_ids.update(status.get('xmltv', {}).get('empty_channels', []))
                # Channels with no EPG data
                missing_epg = status.get('m3u', {}).get('missing_epg', [])
                if missing_epg:
                    self.log(f"chkPVRSync, {len(missing_epg)} channels with no EPG data: {missing_epg}", xbmc.LOGWARNING)
                    rebuild_ids.update(missing_epg)
                findings['missing_epg'] = missing_epg
                orphan_ids = status.get('xmltv', {}).get('missing_from_local', [])
                findings['orphan_ids'] = orphan_ids
                # Orphan cleanup (safe — only removes stale XMLTV entries)
                if orphan_ids:
                    try:
                        with M3U(writable=True) as m3u, XMLTVS(writable=True, m3u=m3u) as epg:
                            for ch_id in orphan_ids:
                                self.log(f"chkPVRSync, removing orphan XMLTV channel: {ch_id}", xbmc.LOGWARNING)
                                epg.delBroadcast({'id': ch_id})
                    except Exception as e:
                        self.log(f"chkPVRSync, orphan cleanup error: {e}", xbmc.LOGDEBUG)
                # Check EPG coverage — channels whose last stop time < MIN_GUIDEDAYS
                if rebuild_ids or orphan_ids:
                    try:
                        with M3U() as m3u, XMLTVS(m3u=m3u) as epg:
                            epg_expired = []
                            now = Globals._epochTime(Globals._getUTCstamp(), tz=False)
                            min_stop = now + datetime.timedelta(days=int((REAL_SETTINGS.getSetting('Min_Days') or "1")))
                            min_stop_str = min_stop.strftime(DTFORMAT)
                            for ch_id, stop_ts in epg.loadStopTimes():
                                stop_str = datetime.datetime.fromtimestamp(stop_ts).strftime(DTFORMAT)
                                if stop_str < min_stop_str:
                                    rebuild_ids.add(ch_id)
                                    epg_expired.append(ch_id)
                            if epg_expired:
                                self.log(f"chkPVRSync, {len(epg_expired)} channels with EPG expiring before {min_stop_str}: {epg_expired}", xbmc.LOGWARNING)
                            findings['epg_expired'] = epg_expired
                    except Exception as e:
                        self.log(f"chkPVRSync, EPG expiration check error: {e}", xbmc.LOGDEBUG)
                findings['rebuild_ids'] = rebuild_ids

            return in_sync, findings
        except Exception as e:
            self.log(f"chkPVRSync, exception: {e}", xbmc.LOGDEBUG)
            return True, findings