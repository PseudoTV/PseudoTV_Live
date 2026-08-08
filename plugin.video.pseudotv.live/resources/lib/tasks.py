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
        self.service._que(self.chkPVRLoadSetting,1)
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
        self.service._que(self.chkLibrary       ,2,0,0,*(None,False))
        self.service._que(self.chkTrailers      ,5)
        self.log('_initialize, _host...')


    def chkPVRBackend(self):
        """Check and configure PVR backend addon."""
        instanceName = Globals.properties.getFriendlyName()
        hasPVR       = Globals.settings.hasAddon(PVR_CLIENT_ID,enable=True,notify=True)
        self.log('chkPVRBackend, instanceName = %s, hasPVR = %s'%(instanceName,hasPVR))
        if hasPVR:
            Globals.settings.instances.chkInstances(instanceName)
            Globals.settings.setPVRLocal(Globals.properties.getRemoteHost(),instanceName)
            

    def chkPVRLoadSetting(self):
        """Prompt user once at startup to enable PVR auto-reload if disabled."""
        if Globals.settings.getSettingBool('Enable_PVR_RELOAD'): return
        if Globals.settings.getCacheSetting('PVR_RELOAD_PROMPTED', default=False): return
        Globals.settings.setCacheSetting('PVR_RELOAD_PROMPTED', True)
        if Globals.dialog.yesnoDialog(LANGUAGE(32278)):
            Globals.settings.setSettingBool('Enable_PVR_RELOAD', True)
            self.log('chkPVRLoadSetting, user enabled PVR auto-reload')
        else:
            self.log('chkPVRLoadSetting, user declined PVR auto-reload')
            

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
                if Globals.dialog.yesnoDialog('%s\n%s'%(LANGUAGE(32142),LANGUAGE(32266).format(minutes=YESNO_TIMEOUT)) ,autoclose=4):
                    self.log('_chkDebugging, disabling debugging.')
                    Globals.settings.setSettingBool('Debug_Enable',False)
                else: self.service._que(self.chkDebugging,0,DEBUG_TIMEOUT,0,True) # Auto disable.
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
        """Check property timers and drain queued operations.

        Called directly by the service loop (services._tasks) on a time gate, so
        long buildChannels tasks in the priority queue can't starve housekeeping.
        """
        self.log('chkQueTimer')
        self._chkPropTimer('chkChannels'  , self.chkChannels  , 3)
        # priority 4 — the deferred-retry path re-queues itself directly at
        # priority 1 (see chkPVRRefresh deferral), so prop-timer pushes here are only
        # a fallback and must not collide with the higher-priority startup push.
        self._chkPropTimer('chkPVRRefresh', self.chkPVRRefresh, 4)
        
        
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
            Globals.builtin.executebuiltin(f'RunScript(special://home/addons/{ADDON_ID}/resources/lib/utilities.py, Show_Changelog)')
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
                    npath = os.path.join(fpath, 'NR')  # fallback for unrated items
                    if not FileAccess.exists(npath):
                        pDialog = __create(mpaas_len, mpaas_len + 1, 'NR', npath)
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

        Skipped while a build is running or media is playing — trailers flood the
        queue with SMB/JSONRPC work that can overwhelm low-power devices.
        """
        if not Globals.properties.isRunning('Tasks.chkTrailers') and Globals.settings.getSettingBool('Include_Trailers_KODI'):
            if Globals.properties.isRunning('Builder.buildChannels') or self.service._isPlaying():
                self.log("chkTrailers, deferred (build running or media playing), retrying in 5 min", xbmc.LOGDEBUG)
                self.service._que(self.chkTrailers,5,300)
                return
            with Globals.properties.chkRunning('Tasks.chkTrailers'):
                if movies is None: movies = self.jsonRPC.getMovies()
                if tvshows is None: tvshows = self.jsonRPC.getTVshows()
                if silent is None: silent = not Globals.settings.showDialog(silent)
                self.log('chkTrailers, movies = %s, tvshows = %s, silent = %s'%(len(movies),len(tvshows), silent))
                for mv in movies: self.service.trailerQue.add(FileAccess.dumpJSON(mv, sortkey=True))
                for tv in tvshows: self.service.trailerQue.add(FileAccess.dumpJSON(tv, sortkey=True))
                self.service._que(self.chkTrailers,5,259200)#3DAYS


    def chkLibrary(self, types: Optional[list] = None, silent: Optional[bool] = None, wait: int=3600):
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
                changed = library.setLibrary(type, items)
                if changed:
                    self.log("chkLibrary, %s library changed, queuing updateLibrary."%type)
                    self.service._que(library.updateLibrary,-1,0,0,*([type],True))
                    complete.add(True)
                else:
                    self.log("chkLibrary, %s library unchanged, skipping update."%type)
            else:
                self.log("chkLibrary, %s library not found! starting update."%(type))
                complete.add(library.updateLibrary([type],silent))
            self.log("chkLibrary, %s done. complete=%s" % (type,complete))
        del library
        self.service._que(self.chkChannels,3,0,0,*(None,None))
        if not any(complete): wait = 900
        self.service._que(self.chkLibrary,2,wait,0,*(None,True))
        self.log(f"chkLibrary, complete = {any(complete)}, next check in {wait} seconds.")
        
        
    def chkChannels(self, channels: Optional[list] = None, silent: Optional[bool] = None):
        if channels is None: channels = self.getChannels()
        if silent is None: silent = not Globals.settings.showDialog(silent)
        self.log("chkChannels, channels = %s, silent = %s"%(len(channels),silent))
        if len(channels) > 0:
            queued   = self.service.queue.get_queued_dedup_keys('build.')
            channels = [ch for ch in channels if f"build.{ch.get('id')}" not in queued]
            if not channels:
                self.log("chkChannels, all channels already queued")
                return
            if Globals.settings.getSettingBool('Build_Filler_Folders'):
                self.service._que(self.chkFillers, 3, 0, 0, channels, True)
            chunk_size = max(1, len(channels) // QUEUE_CHUNK)
            for i in range(0, len(channels), chunk_size):
                chunk = channels[i:i + chunk_size]
                dedup_keys = {f"build.{ch['id']}" for ch in chunk if ch.get('id')}
                self.service._que(Builder(service=self.service).buildChannels, 3, 0, 0, chunk, False, silent, True, dedup_keys=dedup_keys)
            self.log(f"chkChannels, queued {len(channels)} channels")
        else:
            runAutoTune  = Globals.settings.getSettingBool('Enable_Autotune')
            hasAutoTuned = Globals.settings.hasAutotuned()
            self.log(f'chkChannels, No Channels Configured! runAutoTune = {runAutoTune}, hasAutoTuned = {hasAutoTuned}')
            if any((runAutoTune, not hasAutoTuned)):
                autotune_result = _autotune()
                if autotune_result is not None and Globals.settings.setAutotuned(autotune_result):
                    Globals.properties.setPropTimer('chkChannels')# Refresh Channel Changed!
            # Don't set chkPVRRefresh timer here — builder will write files and
            # _onDataChanged will trigger chkPVRRefresh when done.


    def resolveChannels(self, stations: list, filter_ids: set = None, add_placeholder: bool = False) -> tuple:
        """Filter M3U stations by ID, optionally write placeholder EPG, clean orphan XMLTV entries.

        Caller loads M3U stations and passes them in — this method owns the XMLTV context
        for placeholder writes and orphan cleanup.

        Args:
            stations:        Full list of M3U station dicts (caller loads and passes)
            filter_ids:      If provided, only include stations whose ID is in this set
            add_placeholder: If True, write placeholder EPG for each matched station

        Returns:
            (rebuild_list, orphan_ids)
            - rebuild_list: filtered M3U station dicts
            - orphan_ids:   XMLTV IDs not in local M3U (always computed, always cleaned)
        """
        # orphan cleanup must compare against the FULL M3U station set.
        # filter_ids narrows which stations get rebuilt/placeholder — using the
        # narrowed set here would treat every other valid channel as an orphan and
        # mass-delete the guide (wiped the XMLTV to 0 channels on a clean start).
        m3u_ids = {ch.get('id') for ch in stations if ch.get('id')}
        if filter_ids is not None:
            stations = [ch for ch in stations if ch.get('id') in filter_ids]
        with XMLTVS(writable=True) as epg:
            if add_placeholder:
                for ch in stations:
                    self.log(f"[{ch.get('id')}] resolveChannels, placeholder requested for {ch.get('name','')}, skipped", xbmc.LOGDEBUG)
            # orphan cleanup always runs — stale XMLTV entries break PVR sync
            xmltv_ids = {ch.get('id') for ch in epg.getChannels()}
            orphan_ids = list(xmltv_ids - m3u_ids)
            for ch_id in orphan_ids:
                epg.delBroadcast({'id': ch_id})
        self.log(f"resolveChannels, rebuild={len(stations)}, orphans={len(orphan_ids)}")
        return stations, orphan_ids


    # debounce removed — function has isRunning guard + 90s cooldown
    def chkPVRRefresh(self, brute: Optional[bool] = None, findings: Optional[dict] = None):
        """Refresh PVR guide data using the appropriate reload method.

        Uses updatePVRStatus data to intelligently select the refresh method.
        If findings dict is provided (from chkPVRSync), reuses it to avoid
        duplicate updatePVRStatus call. Falls back to fetching fresh status.

        Decision tree (ordered by specificity, least to most invasive):
          0. Files fresh + PVR connected            -> wait (or togglePVRReload if PVR missing channels)
          1. PVR not connected                      -> togglePVRReload (fallback: chkPVRRefresh)
          2. M3U empty + XMLTV empty                -> togglePVRBackend if stale, else chkLibrary (full rebuild)
          2b. Channels in channels.json not in M3U  -> mark changed, chkChannels
          3. M3U has channels + XMLTV empty          -> chkChannels for M3U stations
          4. M3U+XMLTV have data, PVR missing channels -> chkChannels for missing IDs + orphan cleanup
          5. M3U==XMLTV, PVR different set           -> togglePVRReload (fallback: togglePVRBackend w/ 900s cooldown)
          6. Files stale/outdated                     -> togglePVRReload (fallback: chkPVRRefresh)
          7. PVR errors                               -> togglePVRReload (fallback: chkPVRRefresh)
          8. Channels with no EPG data                -> chkChannels
          8b. EPG expiring before MIN_GUIDEDAYS       -> chkChannels
          8c/9. PVR has no channels / brute            -> togglePVRBackend
        """
        if brute is None: brute = Globals.settings.getSettingBool('Enable_PVR_RELOAD')
        self.log(f"chkPVRRefresh, called (brute={brute}, isRunning={Globals.properties.isRunning('Tasks.chkPVRRefresh')})", xbmc.LOGDEBUG)

        # Skip if a PVR reload cycle is already in progress (async togglePVRBackend)
        if Globals.properties.isPVRReloading():
            self.log("chkPVRRefresh, PVR reload already in progress, skipping", xbmc.LOGDEBUG)
            return

        # Defer PVR reloads while a build is running or media is playing —
        # toggling PVR mid-build makes pvr.iptvsimple do a heavy EPG/M3U reload
        # that collides with the build's JSONRPC and freezes the queue thread.
        # Check both the running flag AND queued build chunks (the running flag
        # briefly clears between chunks, opening a race window for a toggle).
        build_pending = (Globals.properties.isRunning('Builder.buildChannels')
                         or len(self.service.queue.get_queued_dedup_keys('build.')) > 0)
        if build_pending or self.service._isPlaying():
            self.log("chkPVRRefresh, deferred (build running or media playing), retrying in 5 min", xbmc.LOGDEBUG)
            # re-queue directly at priority 1 instead of relying on the
            # prop-timer. The prop-timer pushes at priority 4, which the queue drops
            # whenever the startup push (priority 2) is still pending/running — so the
            # deferred retry never ran and stale guides stayed stale. Directly re-queuing
            # at priority 1 beats any pending instance (queue upgrades on lower priority).
            self.service._que(self.chkPVRRefresh, 1, 300)
            return

        if not Globals.properties.isRunning('Tasks.chkPVRRefresh'):
            with Globals.properties.chkRunning('Tasks.chkPVRRefresh'):
                # Cooldown: skip if we triggered a refresh within the last 90s.
                # Applied even for brute so data-change storms (every M3U/XMLTV/
                # channels save fires _onDataChanged -> chkPVRRefresh) don't trigger
                # a full PVR toggle each time.
                last_refresh = Globals.settings.getCacheSetting('chkPVRRefresh.LAST_RUN', default=0)
                if time.time() - last_refresh < 90:
                    self.log(f"chkPVRRefresh, cooldown ({int(time.time() - last_refresh)}s since last refresh), skipping", xbmc.LOGDEBUG)
                    return
                Globals.settings.setCacheSetting('chkPVRRefresh.LAST_RUN', time.time())

                # Use findings if provided, otherwise fetch fresh
                if findings is not None:
                    status = findings.get('status', {})
                else:
                    status = Globals.settings.instances.updatePVRStatus(Globals.properties.getRemoteHost(),Globals.properties.getFriendlyName())
                    findings = {'status': status, 'missing_epg': [], 'epg_expired': [], 'rebuild_ids': set(), 'pvr_no_channels': False}
                    # detect PVR no-channels state when findings not from chkPVRSync
                    has_channels = len(status['m3u'].get('channel_ids', [])) > 0
                    findings['pvr_no_channels'] = status['log'].get('pvr_connected', True) and not Globals.builtin.getInfoBool('Pvr.HasTVChannels') and not Globals.builtin.getInfoBool('Pvr.HasRadioChannels') and has_channels

                pvr_connected   = status['log'].get('pvr_connected', True)
                m3u_ids         = set(status['m3u'].get('channel_ids', []))
                xmltv_ids       = set(status['xmltv'].get('channel_ids', []))
                pvr_ids         = set(status['log'].get('pvr_channel_ids', []))
                xmltv_programs  = status['xmltv'].get('programmes', 0)
                missing_ids     = status['m3u'].get('unloaded_by_pvr', [])
                m3u_sync        = status['m3u']['sync_state']
                xmltv_sync      = status['xmltv']['sync_state']
                has_errors      = len(status['log'].get('pvr_errors', [])) > 0

                # --- local helpers (scoped to this call, no external callers) ---

                def reloadOrRetry(brute=brute, cooldown_key=None, cooldown_secs=0):
                    """Try togglePVRReload. On failure: cooldown check, brute fallback, or schedule retry."""
                    if Globals.settings.instances.togglePVRReload():
                        return True
                    if cooldown_key:
                        last = Globals.settings.getCacheSetting(cooldown_key, default=0)
                        if time.time() - last > cooldown_secs:
                            Globals.settings.setCacheSetting(cooldown_key, time.time())
                            Globals.settings.instances.togglePVRBackend()
                            return True
                    if brute:
                        Globals.settings.instances.togglePVRBackend()
                        return True
                    Globals.properties.setPropTimer('chkPVRRefresh')
                    return False

                def rebuildChannels(filter_ids, add_placeholder=False):
                    """Load M3U stations, resolve by filter, queue chkChannels if rebuild needed."""
                    try:
                        with M3U() as m3u:
                            stations = m3u.getStations()
                        rebuild, orphan_ids = self.resolveChannels(stations, filter_ids=filter_ids, add_placeholder=add_placeholder)
                        if rebuild:
                            self.service._que(self.chkChannels, 3, 0, 0, *(rebuild, True))
                        return rebuild, orphan_ids
                    except Exception as e:
                        self.log(f"chkPVRRefresh, rebuild error: {e}", xbmc.LOGDEBUG)
                        return [], []

                def checkM3UCompleteness(writable=False):
                    """Check if channels.json has channels missing from M3U."""
                    channels = Channels(Globals.getChannelKey(), writable=writable)
                    all_channels = channels.getChannels()
                    m3u_name_map = {}
                    with M3U() as m3u:
                        for station in m3u.getStations():
                            if station.get('name'):
                                m3u_name_map[station['name']] = station.get('id')
                    missing = [ch for ch in all_channels
                               if ch.get('name') and ch['name'] not in m3u_name_map
                               and ch.get('id') and ch.get('path')]
                    return channels, all_channels, missing

                # --- end local helpers ---

                # Case 0: Files fresh + PVR connected — wait, unless channels are missing
                m3u_fresh   = m3u_sync == 'fresh'
                xmltv_fresh = xmltv_sync == 'fresh'
                if m3u_fresh and xmltv_fresh and pvr_connected:
                    unloaded = status['m3u'].get('unloaded_by_pvr', [])
                    if unloaded:
                        self.log(f"chkPVRRefresh, files fresh but PVR missing {len(unloaded)} channels, setting toggle", xbmc.LOGWARNING)
                        reloadOrRetry(brute=brute)
                        return
                    # Check if M3U is incomplete (channels in channels.json but not in M3U)
                    _, _, missing_from_m3u = checkM3UCompleteness(writable=False)
                    if missing_from_m3u:
                        self.log(f"chkPVRRefresh, files fresh but {len(missing_from_m3u)} channels missing from M3U, falling through to rebuild", xbmc.LOGWARNING)
                    else:
                        self.log("chkPVRRefresh, files fresh and PVR connected, waiting for PVR to load", xbmc.LOGDEBUG)
                        return

                # Case 1: PVR not connected — wait for reconnection
                if not pvr_connected:
                    self.log("chkPVRRefresh, #1 PVR not connected, setting toggle", xbmc.LOGWARNING)
                    reloadOrRetry()
                    return

                # Case 2: M3U empty + XMLTV empty — full rebuild needed
                if not m3u_ids and xmltv_programs <= 0:
                    # Stale PVR: our M3U is empty but Kodi's PVR database still has channels
                    # from a previous session. Disable/enable IPTV Simple to force clear.
                    if Globals.builtin.getInfoBool('Pvr.HasTVChannels') or Globals.builtin.getInfoBool('Pvr.HasRadioChannels'):
                        self.log("chkPVRRefresh, #2 M3U empty but PVR has stale channels, toggling backend", xbmc.LOGWARNING)
                        Globals.settings.instances.togglePVRBackend()
                    # M3U/XMLTV data lives in the SQLite cache now — check there (and the
                    # legacy export file) for a previously-built playlist/guide.
                    if (Globals.settings.getCacheSetting(M3U_CACHE_KEY) or Globals.settings.getCacheSetting(XMLTV_PROGRAMMES_KEY)
                            or FileAccess.exists(M3UFLEPATH) or FileAccess.exists(XMLTVFLEPATH)):
                        self.log("chkPVRRefresh, #2 status empty but data exists, triggering PVR reload", xbmc.LOGWARNING)
                        Globals.properties.setPropTimer('chkPVRRefresh')
                        return
                    # Check if channels.json already has channels (e.g. from autotune).
                    # If yes, skip chkLibrary (already complete) and queue builds directly.
                    existing_channels = Channels(Globals.getChannelKey()).getChannels()
                    if existing_channels:
                        self.log(f"chkPVRRefresh, #2 Local M3U+XMLTV empty but {len(existing_channels)} channels exist, queuing chkChannels", xbmc.LOGWARNING)
                        self.service._que(self.chkChannels, 3, 0, 0, *(None, None))
                    else:
                        self.log("chkPVRRefresh, #2 Local M3U+XMLTV empty, chkLibrary (full rebuild)", xbmc.LOGWARNING)
                        self.service._que(self.chkLibrary,2,0,0,*(None,True))
                    # Don't set prop timer — _onDataChanged triggers chkPVRRefresh when builder writes files.
                    return

                # Case 2b: Channels in channels.json but not in M3U — mark changed for rebuild
                channels, _, missing_from_m3u = checkM3UCompleteness(writable=True)
                if missing_from_m3u:
                    for ch in missing_from_m3u:
                        ch['changed'] = True
                    channels.setChannels()
                    self.log(f"chkPVRRefresh, #2b {len(missing_from_m3u)} channels missing from M3U, marking changed for rebuild", xbmc.LOGWARNING)
                    del channels
                    # skip chkChannels — its task_key dedup causes it to be ignored
                    # when a prior chkChannels is still pending. Queue buildChannels directly
                    # with per-channel dedup keys to avoid redundant builds.
                    if Globals.settings.getSettingBool('Build_Filler_Folders'):
                        self.service._que(self.chkFillers, 3, 0, 0, missing_from_m3u, True)
                    chunk_size = max(1, len(missing_from_m3u) // QUEUE_CHUNK)
                    for i in range(0, len(missing_from_m3u), chunk_size):
                        chunk = missing_from_m3u[i:i + chunk_size]
                        dedup_keys = {f"build.{ch['id']}" for ch in chunk if ch.get('id')}
                        self.service._que(Builder(service=self.service).buildChannels, 3, 0, 0, chunk, False, True, True, dedup_keys=dedup_keys)
                    self.log(f"chkPVRRefresh, #2b queued {len(missing_from_m3u)} channels for direct build", xbmc.LOGWARNING)
                    return

                # Case 3: M3U has channels + XMLTV empty — rebuild channels without programme data
                if m3u_ids and xmltv_programs <= 0:
                    self.log(f"chkPVRRefresh, #3 Local M3U has {len(m3u_ids)}ch but no XMLTV, rebuilding specific channels", xbmc.LOGWARNING)
                    rebuildChannels(m3u_ids)
                    return

                # Case 4: M3U+XMLTV have data, PVR missing some channels — rebuild missing, clean orphans
                if m3u_ids and xmltv_programs > 0 and missing_ids:
                    self.log(f"chkPVRRefresh, #4 PVR missing {len(missing_ids)} channels, chkChannels", xbmc.LOGWARNING)
                    rebuild, orphan_ids = rebuildChannels(missing_ids)
                    if not rebuild and orphan_ids:
                        # orphan_ids are already cleaned up by resolveChannels
                        Globals.properties.setPropTimer('chkPVRRefresh')
                    # if PVR has 0 channels (startup failure), force toggle
                    if findings.get('pvr_no_channels', False):
                        self.log("chkPVRRefresh, #4 PVR has 0 channels, forcing toggle", xbmc.LOGWARNING)
                        Globals.settings.instances.togglePVRBackend()
                    return

                # Case 5: M3U+XMLTV in sync, PVR has different set — brute refresh with cooldown
                if m3u_ids == xmltv_ids and pvr_ids != m3u_ids and pvr_ids:
                    self.log("chkPVRRefresh, #5 PVR set differs from M3U+XMLTV, setting toggle", xbmc.LOGWARNING)
                    reloadOrRetry(cooldown_key='brute_pvr_refresh.LAST_RUN', cooldown_secs=900)
                    return

                # Case 6: Files stale/outdated — force cache refresh
                if m3u_sync in ('outdated', 'unknown') or xmltv_sync in ('outdated', 'unknown'):
                    self.log(f"chkPVRRefresh, #6 Files outdated (m3u={m3u_sync}, xmltv={xmltv_sync}), setting toggle", xbmc.LOGWARNING)
                    reloadOrRetry()
                    return

                # Case 7: PVR errors — retry
                if has_errors:
                    self.log(f"chkPVRRefresh, #7 {len(status['log']['pvr_errors'])} PVR errors, setting toggle", xbmc.LOGWARNING)
                    reloadOrRetry()
                    return

                # Case 8: Channels with no EPG data — write placeholder + rebuild
                missing_epg = findings.get('missing_epg', [])
                if missing_epg:
                    self.log(f"chkPVRRefresh, #8 {len(missing_epg)} channels with no EPG, placeholder + rebuild", xbmc.LOGWARNING)
                    rebuild, _ = rebuildChannels(set(missing_epg), add_placeholder=True)
                    if rebuild:
                        Globals.properties.setPropTimer('chkPVRRefresh')
                    return

                # Case 8b: EPG expiring before MIN_GUIDEDAYS — rebuild to extend guide
                epg_expired = findings.get('epg_expired', [])
                if epg_expired:
                    self.log(f"chkPVRRefresh, #8b {len(epg_expired)} channels with EPG expiring soon, triggering rebuild", xbmc.LOGWARNING)
                    rebuildChannels(set(epg_expired))
                    return

                # Cases 8c/9: PVR has no channels or brute force — full backend toggle
                if findings.get('pvr_no_channels', False) or brute:
                    self.log(f"chkPVRRefresh, #8c/9 PVR no channels={findings.get('pvr_no_channels', False)}, brute={brute}, togglePVRBackend", xbmc.LOGWARNING)
                    Globals.settings.instances.togglePVRBackend()
                    return

                self.log("chkPVRRefresh, no action needed (in sync)", xbmc.LOGDEBUG)


    def chkSettingsChange(self, old_settings: dict = {}) -> dict:
        """Check for settings changes and trigger appropriate actions.

        Clean-start settings (_runCleanup) are restored once in Service.__init__
        at boot, not here — restoring on the first onSettingsChanged would
        overwrite the user's just-made change.
        """
        #settings changed actions.
        new_settings = Globals.settings.getCurrentSettings()
        for setting, old_value in list(old_settings.items()):
            new_value = new_settings.get(setting)
            actions = {'User_Folder'     :{'func':self.setUserPath ,'args':(old_value,new_value)},
                       'Debug_Enable'    :{'func':self.chkDebugging,'args':(new_value,)},
                       'TCP_PORT'        :{'func':Globals.properties.setPendingRestart},
                       'Enable_Autotune' :{'func':Globals.properties.setPendingRestart}}  # just reload service; the autotune->user copy happens in the Manager on open
                       
            if setting in actions and old_value != new_value:
                action = actions.get(setting)
                self.log('chkSettingsChange, detected change in %s: %s => %s\naction = %s'%(setting,old_value,new_value,action))
                self.service._que(action.get('func'),1,0,0,*action.get('args',()),**action.get('kwargs',{}))
        return new_settings


    def chkQUES(self):
        """Process queued requests for URLs, JSON, logos, and trailers.

        Drains a batch per call; if consumables remain, re-schedules itself with a
        short delay so queues drain in bursts until empty. Stops re-queueing once
        idle so low-power devices aren't woken every 30s forever.
        """
        library = None
        if self.service.hasQueued():
            # Trailer lookups hit SMB/JSONRPC per item — cap per cycle on low-power
            # devices so they trickle instead of flooding the queue.
            trailer_batch = max(1, BATCH_SIZE // 2) if IS_CONSTRAINED_SOC else BATCH_SIZE
            # Slow to a single trailer per cycle on low-power devices once the
            # lighter queues (postQue/jsonQue/logoQue) are drained.
            if IS_CONSTRAINED_SOC and not any((self.service.postQue, self.service.jsonQue, self.service.logoQue)):
                trailer_batch = 1
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
                        if library is None: library = Library()
                        self.log(f"chkQUES logoQue {len(self.service.logoQue)}")
                        param = FileAccess.loadJSON(self.service.logoQue.pop(), skip_cache=True)
                        self.service._que(library.resources.getLogo,5,0,0,*({'name':param},library.resources.getImageCache(param),True))
                    except Exception as e: self.log("chkQUES failed!, queuing = %s logoQue: %s\n%s"%(len(self.service.logoQue),param,e))
                if len(self.service.trailerQue) > 0:
                    try:
                        self.log(f"chkQUES trailerQue {len(self.service.trailerQue)}")
                        for _ in range(trailer_batch):
                            if not self.service.trailerQue: break
                            param = FileAccess.loadJSON(self.service.trailerQue.pop(), skip_cache=True)
                            # defer_save batches in-memory; flushTrailers writes once below
                            self.service._que(self.jsonRPC.addTrailer,5,0,0,param,defer_save=True)
                        # Write the whole batch to the trailers cache in one SQLite op.
                        self.service._que(self.jsonRPC.flushTrailers,5,0,0)
                    except Exception as e: self.log("chkQUES failed!, queuing = %s trailerQue: %s\n%s"%(len(self.service.trailerQue),param,e))
            if library: del library
        # Only keep draining while consumables remain — stop when idle.
        if self.service.hasQueued():
            self.service._que(self.chkQUES,3,30)


    @debounceit(LOGO_REFRESH)
    def chkLogos(self):
        # ponytail: was rewriting resolved logos back into channel/library config
        # files on every queue drain. The static /logos/{name} URL already serves
        # whatever the in-memory imageCache holds (fallback -> queue -> fill), so
        # persisting resolved logos is redundant churn. Kept as a no-op stub in case
        # callers reference it; the queue no longer schedules it.
        pass
 
     
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
        return Channels(Globals.getChannelKey()).getChannels()
        
        
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

            m3u_synced     = status['m3u']['sync_state']    in ('fresh', 'stale')
            xmltv_synced   = status['xmltv']['sync_state']  in ('fresh', 'stale')
            has_errors     = len(status['log']['pvr_errors']) > 0
            has_channels   = status['m3u']['channels'] > 0
            has_programs   = status['xmltv']['programmes'] > 0
            pvr_connected  = status['log'].get('pvr_connected', True)
            channels_match = status['m3u']['channels'] == status['xmltv']['channels']
            in_sync        = m3u_synced and xmltv_synced and has_channels and has_programs and channels_match and not has_errors

            # Detect PVR no-channels state: PVR connected, files exist, but PVR hasn't loaded them
            pvr_has_tv = Globals.builtin.getInfoBool('Pvr.HasTVChannels')
            pvr_has_radio = Globals.builtin.getInfoBool('Pvr.HasRadioChannels')
            findings['pvr_no_channels'] = pvr_connected and not pvr_has_tv and not pvr_has_radio and has_channels
            findings['genres_exists'] = status.get('xmltv', {}).get('genres_exists', False)
            findings['genres_loaded'] = status.get('xmltv', {}).get('genres_loaded', 0)

            # rebuild_ids/EPG checks run in BOTH branches — stale guides
            # (channels whose EPG stopped hours ago) must be rebuilt even when PVR
            # is otherwise out of sync, otherwise blank guides never recover.
            rebuild_ids = set()
            rebuild_ids.update(status.get('m3u', {}).get('unloaded_by_pvr', []))
            # Channels with no EPG data — rebuild to populate guide
            missing_epg = status.get('m3u', {}).get('missing_epg', [])
            if missing_epg:
                self.log(f"chkPVRSync, {len(missing_epg)} channels with no EPG data: {missing_epg}", xbmc.LOGWARNING)
                rebuild_ids.update(missing_epg)
            findings['missing_epg'] = missing_epg
            # orphan cleanup deferred to chkPVRRefresh.resolveChannels — state checker should not write
            findings['orphan_ids'] = status.get('xmltv', {}).get('missing_from_local', [])
            # EPG coverage check — channels with stop time before MIN_GUIDEDAYS need rebuild.
            # Computed regardless of in_sync so transient PVR errors can't block stale-guide repair.
            try:
                with XMLTVS(m3u=M3U()) as epg:
                    epg_expired = []
                    min_stop = Globals._epochTime(Globals._getGMTstamp(), tz=False) + datetime.timedelta(days=int((REAL_SETTINGS.getSetting('Min_Days') or "1")))
                    min_stop_str = min_stop.strftime(DTFORMAT)
                    for ch_id, stop_ts in epg.loadStopTimes():
                        if datetime.datetime.fromtimestamp(stop_ts).strftime(DTFORMAT) < min_stop_str:
                            rebuild_ids.add(ch_id)
                            epg_expired.append(ch_id)
                    if epg_expired:
                        self.log(f"chkPVRSync, {len(epg_expired)} channels with EPG expiring before {min_stop_str}: {epg_expired}", xbmc.LOGWARNING)
                    findings['epg_expired'] = epg_expired
            except Exception as e: self.log(f"chkPVRSync, EPG expiration check error: {e}", xbmc.LOGDEBUG)
            findings['rebuild_ids'] = rebuild_ids

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

            return in_sync, findings
        except Exception as e:
            self.log(f"chkPVRSync, exception: {e}", xbmc.LOGDEBUG)
            return True, findings