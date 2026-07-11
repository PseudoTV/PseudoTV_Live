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
from backup         import Backup
from library        import Library
from builder        import Builder
from channels       import Channels

_VERSION_RE = re.compile('" version="(.+?)" name="%s"'%(ADDON_NAME))
from multiroom      import Multiroom
from server         import HTTP, Discovery
from context_create import _autotune

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

    def chkSync(self) -> bool:
        """Check if PseudoTV files are in sync with Kodi's PVR state. Returns True if in sync."""
        try:
            status = Globals.settings.instances.chkPVRStatus()
            m3u_synced   = status['m3u']['sync_state']   in ('fresh', 'stale')
            xmltv_synced = status['xmltv']['sync_state']  in ('fresh', 'stale')
            has_errors   = len(status['log']['pvr_errors']) > 0
            has_channels = status['m3u']['channels'] > 0
            has_programs = status['xmltv']['programmes'] > 0
            
            in_sync = m3u_synced and xmltv_synced and has_channels and has_programs and not has_errors
            
            if not in_sync:
                reasons = []
                if not has_channels:  reasons.append('no M3U channels')
                if not has_programs:  reasons.append('no XMLTV programmes')
                if status['m3u']['sync_state'] == 'outdated':   reasons.append('M3U outdated')
                if status['xmltv']['sync_state'] == 'outdated':  reasons.append('XMLTV outdated')
                if has_errors: reasons.append(f'{len(status["log"]["pvr_errors"])} PVR errors')
                self.log(f"chkSync, out of sync: {', '.join(reasons)}", xbmc.LOGWARNING)
                Globals.properties.setPropTimer('chkPVRRefresh')
            else:
                self.log(f"chkSync, in sync: m3u={status['m3u']['channels']}ch, xmltv={status['xmltv']['channels']}ch/{status['xmltv']['programmes']}prog")
            return in_sync
        except Exception as e:
            self.log(f"chkSync, failed: {e}", xbmc.LOGERROR)
            return True


    def _client(self):
        """Initialize client-side checks."""
        self.service._que(self.chkPVRBackend    ,1)
        self.service._que(self.chkHTTP          ,1)
        self.service._que(self.chkDebugging     ,1)
        self.service._que(self.chkVersion       ,1)
        self.service._que(self.chkKodiSettings  ,1)
        self.service._que(self.chkDiscovery     ,1)
        self.service._que(self.chkQUES          ,5)
        self.log('_initialize, _client...')
        
        
    def _host(self):
        """Initialize host-side checks and setup."""
        self._client()
        self._migrateChannels() #temp, remove in v.0.7.5.
        self.service._que(self.chkDirs          ,1)
        self.service._que(self.chkCrash         ,1)
        # self.service._que(self.chkStations      ,1)
        self.service._que(self.chkLibrary       ,2)
        self.service._que(self.chkChannels      ,3)
        self.service._que(self.chkFiles         ,5)
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
        self.log('chkHTTP')
        
        
    def chkDebugging(self, disable: bool = False):
        """Check and manage debug settings, optionally force disable."""
        kodi_access = Globals.settings.getSettingBool('Enable_Kodi_Access')
        self.log(f'chkDebugging, disable = {disable}, kodi access = {kodi_access}')
        if Globals.settings.getSettingBool('Debug_Enable'):
            if   Globals.settings.getSettingBool('Debug_Keep_Enable'): return
            elif disable: Globals.settings.setSettingBool('Debug_Enable',False)
            elif Globals.dialog.yesnoDialog('%s\n%s'%(LANGUAGE(32142),LANGUAGE(32266)%(DEBUG_TIMEOUT//60)) ,autoclose=4):
                self.log('_chkDebugging, disabling debugging.')
                Globals.settings.setSettingBool('Debug_Enable',False)
            elif kodi_access: self.service._que(self.chkDebugging,0,DEBUG_TIMEOUT,0,True)
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
        self._chkPropTimer('chkChanged'   , self.chkChanged   , 3)
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
            Globals.dialog.notificationDialog(LANGUAGE(30073)%(ONLINE_VERSION))
        elif ADDON_VERSION != LAST_VERSION:
            Globals.settings.setCacheSetting('chkVersion.LAST_VERSION', ADDON_VERSION)
            Globals.builtin.executescript('special://home/addons/%s/resources/lib/utilities.py, Show_Changelog'%(ADDON_ID))
        Globals.settings.setSetting('Update_Status',{True:'[COLOR=yellow]%s [B]v.%s[/B][/COLOR]'%(LANGUAGE(32168),ONLINE_VERSION),False:'None'}[UPDATE_AVAILABLE])
        self.log('chkVersion, installed = %s, online = %s, last = %s'%(ADDON_VERSION,ONLINE_VERSION,LAST_VERSION))
        self.service._que(self.chkVersion,1,43200)#12HRS


    def chkKodiSettings(self):
        """Check and sync Kodi settings like EPG days and OSD timer."""
        self.log('chkKodiSettings')
        MIN_GUIDEDAYS = Globals.settings.setSettingInt('Min_Days' ,self.jsonRPC.getSettingValue('epg.pastdaystodisplay'     ,default=1))
        MAX_GUIDEDAYS = Globals.settings.setSettingInt('Max_Days' ,self.jsonRPC.getSettingValue('epg.futuredaystodisplay'   ,default=3))
        OSD_TIMER     = Globals.settings.setSettingInt('OSD_Timer',self.jsonRPC.getSettingValue('pvrmenu.displaychannelinfo',default=5))
        self.service._que(self.chkKodiSettings,1,10800)#3HRS
         

    def chkDirs(self):
        """Create required directories if they don't exist."""
        [(self.log('chkDirs, creating [%s]'%(folder)),FileAccess.makedirs(folder)) for folder in [LOGO_LOC,FILLER_LOC,TEMP_LOC] if not FileAccess.exists(os.path.join(folder,''))]


    def chkFiles(self):
        """Check if critical files exist and rebuild channels if missing."""
        if not Globals.properties.isRunning('Builder.buildChannels'):
            if any(not bool(FileAccess.exists(file)) for file in [M3UFLEPATH,XMLTVFLEPATH,GENREFLEPATH]): 
                self.log('chkFiles, missing files! running chkChannels to rebuild.')
                self.service._que(self.chkChannels,5)
        self.service._que(self.chkFiles,5,900)#15MINS


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
        """Check and queue trailers for movies and TV shows."""
        if movies is None: movies = self.jsonRPC.getMovies()
        if tvshows is None: tvshows = self.jsonRPC.getTVshows()
        if silent is None: silent = not Globals.settings.showDialog(silent)
        self.log('chkTrailers, movies = %s, tvshows = %s, silent = %s'%(len(movies),len(tvshows), silent))
        if not Globals.properties.isRunning('Tasks.chkTrailers') and Globals.settings.getSettingBool('Include_Trailers_KODI'):
            with Globals.properties.chkRunning('Tasks.chkTrailers'):
                pDialog  = None
                pHeader  = '%s, %s %ss'%(ADDON_NAME,LANGUAGE(32022),LANGUAGE(30187))
                with Globals.dialog._progressDialog('%ss: %s'%(LANGUAGE(32208),LANGUAGE(32015)), pHeader, silent) as pDialog:
                    for midx, movie in enumerate(movies):
                        if movie.get('trailer'):
                            pDialog = Globals.dialog._updateProgress(pDialog,int(midx*100)//len(movies))
                            self.service.trailerQue.add(FileAccess.dumpJSON(movie,sortkey=True))
                with Globals.dialog._progressDialog('%ss: %s'%(LANGUAGE(32208),LANGUAGE(32014)), pHeader, silent) as pDialog:
                    for tidx, tvshow in enumerate(tvshows):
                        if tvshow.get('trailer'):
                            pDialog = Globals.dialog._updateProgress(pDialog,int(tidx*100)//len(tvshows))
                            self.service.trailerQue.add(FileAccess.dumpJSON(tvshow,sortkey=True))
        self.service._que(self.chkTrailers,5,259200)#3DAYS
                
                
    def chkStations(self, channels: Optional[list] = None):
        """Check PVR stations and remove inactive channels."""
        if channels is None: channels = self.getChannels()
        if channels:
            programmes = []
            if Globals.builtin.getInfoBool("Pvr.HasTVChannels"):    programmes.extend(self.jsonRPC.getPVRChannels())
            if Globals.builtin.getInfoBool("Pvr.HasRadioChannels"): programmes.extend(self.jsonRPC.getPVRChannels(radio=True))
            if not programmes: return self.service._que(self.chkStations,1,30)#30SECS
            broadcasts = { Globals._decodePlot(b.get('plot', '')).get('citem', {}).get('name') for b in programmes if 'broadcastnow' in b and b.get('plot')}
            remove = [c for c in channels if c.get('name') not in broadcasts]
            self.log(f"chkStations, channels = {len(channels)}, removing = {len(remove)}")
            with M3U(writable=len(remove)>0) as m3u:
                for channel in remove: 
                    m3u.delStation(channel)
            if len(remove) > 0: Globals.properties.setPropTimer('chkPVRRefresh') # Refresh PVR Guide
            self.service._que(self.chkStations,-1,MIN_EPG_DURATION)#3HRS
                
    def chkLibrary(self, types: Optional[list] = None, silent: Optional[bool] = None):
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
        self.service._que(self.chkLibrary,2,1800,0,*(None,True))#30MINS
        self.log("chkLibrary, complete = %s"%(any(complete)))
        
        
    def chkChanged(self, channels: Optional[list] = None, silent: Optional[bool] = None):
        """Check for modified channels and rebuild them."""
        if channels is None: channels = self.getChannels()
        if silent is None: silent = not Globals.settings.showDialog(silent)
        self.log("chkChanged, channels = %s, silent = %s"%(len(channels),silent))
        changed = [ch for ch in channels if isinstance(ch, dict) and ch.get('changed', False)]
        if not changed: return self.log("chkChanged: No channel modifications detected. Skipping batch allocation.")
        self.log(f"chkChanged: Distributing {len(changed)} modified channels across concurrent batches.")
        if Globals.settings.getSettingBool('Build_Filler_Folders'): self.service._que(self.chkFillers, 3, 0, 0, changed, silent)
        self.service._que(self.chkChannels, 3, 0, 0, changed, silent)


    def chkChannels(self, channels: Optional[list] = None, silent: Optional[bool] = None):
        """Check channels and run build or autotune if needed."""
        if channels is None: channels = self.getChannels()
        if silent is None: silent = not Globals.settings.showDialog(silent)
        self.log("chkChannels, channels = %s, silent = %s"%(len(channels),silent))
        if len(channels) > 0:
            if Globals.settings.getSettingBool('Build_Filler_Folders'): self.service._que(self.chkFillers, 3, 0, 0, channels, silent)
            chunk_size = max(1, len(channels) // QUEUE_CHUNK)
            self.log(f"chkChannels, processing channels count = {len(channels)} in chunks = {chunk_size}")
            for i in range(0, len(channels), chunk_size):
                self.service._que(Builder(service=self.service).buildChannels, 3, 0, 0, channels[i:i + chunk_size], False, silent, True)
        else:
            runAutoTune  = Globals.settings.getSettingBool('Enable_Autotune')
            hasAutoTuned = Globals.settings.hasAutotuned()
            self.log(f'chkChannels, No Channels Configured! runAutoTune = {runAutoTune}, hasAutoTuned = {hasAutoTuned}')
            if any((runAutoTune, not hasAutoTuned)):
                if Globals.settings.setAutotuned(_autotune()): 
                    Globals.properties.setPropTimer('chkChanged')# Refresh Channel Changed!
            elif Globals.properties.hasEnabledServers():                     
                Globals.properties.setPropTimer('chkPVRRefresh') # Refresh PVR Guide


    @debounceit(M3U_REFRESH * 2)
    def chkPVRRefresh(self, brute: Optional[bool] = None):
        """Refresh PVR guide data using the appropriate reload method.
        
        Three reload methods, used based on context:
          togglePVRBackend  - Full addon disable/enable. Use when PVR is stuck, brute force needed.
          triggerReload      - Toggle m3uCache. Use when M3U/XMLTV files already written.
          PVRScan            - API scan. Use when PVR backend supports it.
        """
        if brute is None: brute = Globals.settings.getSettingBool('Enable_PVR_RELOAD')
        self.log(f"chkPVRRefresh, brute force reload state = {brute}")

        if not Globals.properties.isRunning('Tasks.chkPVRRefresh'):
            with Globals.properties.chkRunning('Tasks.chkPVRRefresh'):
                if self.chkSync():
                    self.log("chkPVRRefresh, already in sync, skipping refresh")
                    return
                # Method 1: brute force - disable/enable addon (full reload)
                if brute:
                    if not self.service.player.isPlaying(): 
                        Globals.settings.instances.togglePVRBackend(False)
                        self.monitor.waitForAbort(M3U_REFRESH)
                        Globals.settings.instances.togglePVRBackend(True)
                    return
                # Method 2: try PVR API scan first
                try: 
                    client_id = self.jsonRPC.getPVRClient(PVR_CLIENT_ID).get('clientid',-1)
                    if self.jsonRPC.PVRScan(client_id).get('error'): raise Exception(f'{PVR_CLIENT_ID} does not support PVR.Scan')
                except Exception as e: self.log(f"chkPVRRefresh: PVR scan failed... {str(e)}", xbmc.LOGDEBUG)
                # Method 3: fallback - toggle m3uCache (lightweight reload)
                Globals.settings.instances.triggerReload()

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
                    param = self.service.jsonQue.pop()
                    self.service._que(self.jsonRPC.sendJSON,4,0,0,param)
                except Exception as e: self.log("chkQUES failed!, queuing = %s jsonQue: %s\n%s"%(len(self.service.jsonQue),param,e))
            if len(self.service.logoQue) > 0:
                try:
                    self.log(f"chkQUES logoQue {len(self.service.logoQue)}")
                    param = FileAccess.loadJSON(self.service.logoQue.pop())
                    self.service._que(library.resources.getLogo,5,0,0,*({'name':param},library.resources.getImageCache(param),True))
                except Exception as e: self.log("chkQUES failed!, queuing = %s logoQue: %s\n%s"%(len(self.service.logoQue),param,e))
            if len(self.service.trailerQue) > 0:
                try:
                    self.log(f"chkQUES trailerQue {len(self.service.trailerQue)}")
                    param = FileAccess.loadJSON(self.service.trailerQue.pop())
                    self.service._que(self.jsonRPC.addTrailer,5,0,0,param)
                except Exception as e: self.log("chkQUES failed!, queuing = %s trailerQue: %s\n%s"%(len(self.service.trailerQue),param,e))        
        del library
        self.service._que(self.chkQUES,5,120)#2MINS
     
     
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
        return Channels().getChannels()
        
        
    def getLibrary(self, type: Optional[str] = None) -> Any:
        """Get library items for specified content type."""
        Library(service=self.service).getLibrary(type)