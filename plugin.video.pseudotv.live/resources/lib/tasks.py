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

from globals    import *
from m3u        import M3U
from backup     import Backup
from library    import Library
from builder    import Builder
from channels   import Channels
from multiroom  import Multiroom
from server     import HTTP, Discovery

from context_create import _autotune

class Tasks(object):
    citems  = []
    cache   = SETTINGS.cache
    cache = SETTINGS.cache
    
    def __init__(self, service):
        self.service   = service       
        self.jsonRPC   = service.jsonRPC
        self.player    = service.player
        self.monitor   = service.monitor


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)


    def _client(self):
        self.service._que(self.chkPVRBackend    ,1)
        self.service._que(self.chkHTTP          ,1)
        self.service._que(self.chkDebugging     ,1)
        self.service._que(self.chkVersion       ,1)
        self.service._que(self.chkKodiSettings  ,1)
        self.service._que(self.chkDiscovery     ,1)
        self.service._que(self.chkQUES          ,5)
        self.log('_initialize, _client...')
        
        
    def _host(self):
        self._client()
        self._migrateChannels() #temp, remove in v.0.7.5.
        self.service._que(self.chkDirs          ,1)
        self.service._que(self.chkCrash         ,1)
        self.service._que(self.chkStations      ,1)
        self.service._que(self.chkLibrary       ,2)
        self.service._que(self.chkChannels      ,3)
        self.service._que(self.chkFiles         ,5)
        self.service._que(self.chkTrailers      ,5)
        self.log('_initialize, _host...')
    
    
    def _migrateChannels(self, old=CACHE_LOC, new=BACKUP_LOC):
        old_path = os.path.join(old,CHANNELFLE)
        new_path = os.path.join(new,CHANNELFLE)
        if FileAccess.exists(old_path):
            self.log('migrate, importing %s...'%(old_path))
            if Backup().importChannels(old_path): PROPERTIES.setPendingRestart(True)
            if FileAccess.move(old_path,new_path): DIALOG.notificationDialog(LANGUAGE(32025))
                  
   
    def chkPVRBackend(self): 
        instanceName = PROPERTIES.getFriendlyName()
        hasPVR       = SETTINGS.hasAddon(PVR_CLIENT_ID,notify=True)
        self.log('chkPVRBackend, instanceName = %s, hasPVR = %s'%(instanceName,hasPVR))
        if hasPVR:
            SETTINGS.instances.chkInstances(instanceName)
            SETTINGS.setPVRLocal(PROPERTIES.getRemoteHost(),instanceName)
            

    def chkHTTP(self):
        timerit(HTTP)(0.1,self.service)
        self.log('chkHTTP')
        
        
    def chkDebugging(self, disable=False):
        kodi_access = SETTINGS.getSettingBool('Enable_Kodi_Access')
        keep_debug  = SETTINGS.getSettingBool('Debug_Keep_Enable')
        self.log('chkDebugging, disable = %s'%(disable))
        if SETTINGS.getSettingBool('Debug_Enable'):
            if disable: SETTINGS.setSettingBool('Debug_Enable',False)
            elif DIALOG.yesnoDialog(LANGUAGE(32142) if kodi_access else '%s\n%s'%(LANGUAGE(32142),LANGUAGE(32266)%(DEBUG_TIMEOUT//60)) ,autoclose=4):
                self.log('_chkDebugging, disabling debugging.')
                SETTINGS.setSettingBool('Debug_Enable',False)
                DIALOG.notificationDialog(LANGUAGE(32025))
            elif kodi_access and not keep_debug: self.service._que(self.chkDebugging,0,DEBUG_TIMEOUT,0,True)
        #Force enable Kodi Debugging when enabled in PseudoTV via JSONRPC only if Kodi access allowed by user.
        if kodi_access: self.jsonRPC.toggleShowLog(SETTINGS.getSettingBool('Debug_Enable'))
                    
             
    def chkDiscovery(self):
        timerit(Discovery)(0.1,*(self.service, Multiroom(service=self.service)))
        self.log('chkDiscovery')
        self.service._que(self.chkDiscovery,1,300)#5MINS
         

    def chkCrash(self):
        citem = SETTINGS.getCacheSetting('KODI.CRASH.JSONRPC.CITEM', default={})
        SETTINGS.setCacheSetting('KODI.CRASH.JSONRPC.CITEM',None)
        if citem:
            self.log('chkCrash\n%s'%(citem))
            # with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
                # channels = Channels(writable=True)
                # chanLST  = channels.getChannels()
                # idx, channel = channels.findChannel(citem, chanLST)
                # chanLST[idx].update({'enabled':False})
                # if channels.setChannels(chanLST):
                    # DIALOG.okDialog(f'Kodi encountered a fatal crash while parsing a [B]{ADDON_NAME}[\B] channel.\nPlease check the channel configuration for [B]{citem.get('name')}[\B]\n Channel [B]{citem.get('number')}[\B] temporarily disabled!', usethread=False)
                # del channels
  
  
    def chkQueTimer(self):
        self.log('chkQueTimer')
        self._chkPropTimer('chkChanged'   , self.chkChanged   , 3)
        self._chkPropTimer('chkPVRRefresh', self.chkPVRRefresh, 4)
        
        
     #_chkPropTimer trigger - True == Run
    def _chkPropTimer(self, key, func, priority=-1, *args, **kwargs):
        if PROPERTIES.getPropTimer(key):
            self.log('_chkPropTimer, key = %s'%(key))
            PROPERTIES.clrEXTProperty(key)
            self.service._que(func, priority, 0, 0, *args, **kwargs)

 
    def chkVersion(self):
        try:              ONLINE_VERSION = re.compile('" version="(.+?)" name="%s"'%(ADDON_NAME)).findall(str(self.jsonRPC.requestURL(ADDON_URL)))[0]
        except Exception: ONLINE_VERSION = ADDON_VERSION
        UPDATE_AVAILABLE = False
        LAST_VERSION = SETTINGS.getCacheSetting('chkVersion.LAST_VERSION', default='0.0.0')
        if ADDON_VERSION < ONLINE_VERSION:
            UPDATE_AVAILABLE = True
            DIALOG.notificationDialog(LANGUAGE(30073)%(ONLINE_VERSION))
        elif ADDON_VERSION != LAST_VERSION:
            SETTINGS.setCacheSetting('chkVersion.LAST_VERSION', ADDON_VERSION)
            BUILTIN.executescript('special://home/addons/%s/resources/lib/utilities.py, Show_Changelog'%(ADDON_ID))
        SETTINGS.setSetting('Update_Status',{True:'[COLOR=yellow]%s [B]v.%s[/B][/COLOR]'%(LANGUAGE(32168),ONLINE_VERSION),False:'None'}[UPDATE_AVAILABLE])
        self.log('chkVersion, installed = %s, online = %s, last = %s'%(ADDON_VERSION,ONLINE_VERSION,LAST_VERSION))
        self.service._que(self.chkVersion,1,43200)#12HRS


    def chkKodiSettings(self):
        self.log('chkKodiSettings')
        MIN_GUIDEDAYS = SETTINGS.setSettingInt('Min_Days' ,self.jsonRPC.getSettingValue('epg.pastdaystodisplay'     ,default=1))
        MAX_GUIDEDAYS = SETTINGS.setSettingInt('Max_Days' ,self.jsonRPC.getSettingValue('epg.futuredaystodisplay'   ,default=3))
        OSD_TIMER     = SETTINGS.setSettingInt('OSD_Timer',self.jsonRPC.getSettingValue('pvrmenu.displaychannelinfo',default=5))
        self.service._que(self.chkKodiSettings,1,10800)#3HRS
         

    def chkDirs(self):
        [(self.log('chkDirs, creating [%s]'%(folder)),FileAccess.makedirs(folder)) for folder in [LOGO_LOC,FILLER_LOC,TEMP_LOC] if not FileAccess.exists(os.path.join(folder,''))]


    def chkFiles(self):
        if not PROPERTIES.isRunning('Builder.buildChannels'):
            if any(not bool(FileAccess.exists(file)) for file in [M3UFLEPATH,XMLTVFLEPATH,GENREFLEPATH]): 
                self.log('chkFiles, missing files! running chkChannels to rebuild.')
                self.service._que(self.chkChannels,3)
        self.service._que(self.chkFiles,5,900)#15MINS


    def chkFillers(self, channels=None, silent=None):
        with DIALOG._progressDialog(f'{ADDON_NAME}, {LANGUAGE(32179)}', ADDON_NAME, silent=silent, background=True) as pDialog:
            if channels is None: channels = self.getChannels()
            if not isinstance(channels, list) or len(channels) == 0:
                self.log("chkFillers: No valid channels provided. Exiting tree scaffolding.")
                return

            def __create(idx, total, label, path):
                FileAccess.makedirs(path)
                return DIALOG._updateProgress(pDialog, int((idx / max(1, total)) * 100), message=label, header=f'{ADDON_NAME}, {LANGUAGE(32179)}')

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
        
        
    def chkTrailers(self, movies=None, tvshows=None, silent=None):
        if movies is None: movies = self.jsonRPC.getMovies()
        if tvshows is None: tvshows = self.jsonRPC.getTVshows()
        if silent is None: silent = not SETTINGS.showDialog(silent)
        self.log('chkTrailers, movies = %s, tvshows = %s, silent = %s'%(len(movies),len(tvshows), silent))
        if not PROPERTIES.isRunning('Tasks.chkTrailers') and SETTINGS.getSettingBool('Include_Trailers_KODI'):
            with PROPERTIES.chkRunning('Tasks.chkTrailers'):
                pDialog  = None
                pHeader  = '%s, %s %ss'%(ADDON_NAME,LANGUAGE(32022),LANGUAGE(30187))
                with DIALOG._progressDialog('%ss: %s'%(LANGUAGE(32208),LANGUAGE(32015)), pHeader, silent) as pDialog:
                    for midx, movie in enumerate(movies):
                        if movie.get('trailer'):
                            pDialog = DIALOG._updateProgress(pDialog,int(midx*100)//len(movies))
                            self.service.trailerQue.add(FileAccess.dumpJSON(movie,sortkey=True))
                with DIALOG._progressDialog('%ss: %s'%(LANGUAGE(32208),LANGUAGE(32014)), pHeader, silent) as pDialog:
                    for tidx, tvshow in enumerate(tvshows):
                        if tvshow.get('trailer'):
                            pDialog = DIALOG._updateProgress(pDialog,int(tidx*100)//len(tvshows))
                            self.service.trailerQue.add(FileAccess.dumpJSON(tvshow,sortkey=True))
        self.service._que(self.chkTrailers,5,259200)#3DAYS
                
                
    def chkStations(self, channels=None):
        if channels is None: channels = self.getChannels()
        if channels:
            programmes = []
            if BUILTIN.getInfoBool("Pvr.HasTVChannels"):    programmes.extend(self.jsonRPC.getPVRChannels())
            if BUILTIN.getInfoBool("Pvr.HasRadioChannels"): programmes.extend(self.jsonRPC.getPVRChannels(radio=True))
            if not programmes: return self.service._que(self.chkStations,1,30)#30SECS
            broadcasts = { Globals._decodePlot(b.get('plot', '')).get('citem', {}).get('name') for b in programmes if 'broadcastnow' in b and b.get('plot')}
            remove     = [c for c in channels if c.get('name') not in broadcasts]
            print(tv,radio,broadcasts,remove)
            self.log(f"chkStations, channels = {len(channels)}, removing = {len(remove)}")
            with M3U(writable=len(remove)>0) as m3u:
                for channel in remove: m3u.delStation(channel)
            self.service._que(self.chkStations,-1,MIN_EPG_DURATION)#3HRS
            PROPERTIES.setPropTimer('chkPVRRefresh') # Refresh PVR Guide
                

    def chkLibrary(self, types=None, silent=None):
        if silent is None: silent = not SETTINGS.showDialog(silent)
        self.log("chkLibrary, types = %s, silent = %s"%(types,silent))
        complete = set()
        library  = Library(service=self.service, writable=True)
        library.searchRecommended()
        if types is None: types = AUTOTUNE_TYPES
        for idx, type in enumerate(types):
            items = library.getLibrary(type)
            if items:
                self.log("chkLibrary, %s library found! Setting items (%s), queuing update."%(type,len(items)))
                complete.add(library.setLibrary(type, items))
                self.service._que(library.updateLibrary,-1,0,0,*([type],True))
            else:
                self.log("chkLibrary, %s library not found! starting update."%(type))
                complete.add(library.updateLibrary([type],silent))
        del library
        if any(complete): self.service._que(self.chkChannels,3,0,0,*(None,silent))
        self.service._que(self.chkLibrary,2,1800,0,0,*(None,True))#30MINS
        self.log("chkLibrary, complete = %s"%(any(complete)))
        
        
    def chkChanged(self, channels=None, silent=None):
        if channels is None: channels = self.getChannels()
        if silent is None: silent = not SETTINGS.showDialog(silent)
        self.log("chkChanged, channels = %s, silent = %s"%(len(channels),silent))
        changed_channels = [ch for ch in channels if isinstance(ch, dict) and ch.get('changed', False)]
        if len(changed_channels) == 0:
            self.log("chkChanged: No channel modifications detected. Skipping batch allocation.")
            return
        self.log(f"chkChanged: Distributing {len(changed_channels)} modified channels across concurrent batches.")
        chunk_size = max(1, len(changed_channels) // QUEUE_CHUNK)
        for i in range(0, len(changed_channels), chunk_size):
            batch = changed_channels[i:i + chunk_size]
            self.service._que(Builder(service=self.service).buildChannels, 3, 0, 0, batch, False, silent, True)
        if SETTINGS.getSettingBool('Build_Filler_Folders'): 
            self.service._que(self.chkFillers, 3, 0, 0, changed_channels, silent)


    def chkChannels(self, channels=None, silent=None):
        if channels is None: channels = self.getChannels()
        if silent is None: silent = not SETTINGS.showDialog(silent)
        self.log("chkChannels, channels = %s, silent = %s"%(len(channels),silent))
        channel_count = len(channels) if isinstance(channels, list) else 0
        if channel_count > 0:
            self.log(f"chkChannels, processing channels count = {channel_count}")
            if SETTINGS.getSettingBool('Build_Filler_Folders'): 
                self.service._que(self.chkFillers, 3, 0, 0, channels, silent)

            chunk_size = max(1, channel_count // QUEUE_CHUNK)
            for i in range(0, channel_count, chunk_size):
                batch = channels[i:i + chunk_size]
                self.service._que(Builder(service=self.service).buildChannels, 3, 0, 0, batch, False, silent, True)
        else:
            self.log('chkChannels, No Channels Configured!')
            run_autotune = SETTINGS.getSettingBool('Enable_Autotune')
            if run_autotune or not SETTINGS.hasAutotuned():
                self.log('chkChannels, Auto-tuning Channels.')
                if SETTINGS.setAutotuned(_autotune(automatic=run_autotune)): 
                    PROPERTIES.setPropTimer('chkChanged')# Refresh Channel Changed!
            elif PROPERTIES.hasEnabledServers():                     
                PROPERTIES.setPropTimer('chkPVRRefresh') # Refresh PVR Guide


    @debounceit(M3U_REFRESH)
    def chkPVRRefresh(self, brute: bool = None):
        if brute is None: brute = SETTINGS.getSettingBool('Enable_PVR_RELOAD')
        self.log(f"chkPVRRefresh, brute force reload state = {brute}")
        def __toggle(state: bool):
            current_state = BUILTIN.getInfoBool(f"System.AddonIsEnabled({PVR_CLIENT_ID})")
            if current_state == state: return
            self.log(f"chkPVRRefresh: __toggle transitioning target state to = {state}")
            
            with BUILTIN.busy_dialog(lock=True):
                notification_msg = f"{PVR_CLIENT_NAME}: {LANGUAGE(32125)}"
                DIALOG.notificationWait(notification_msg, wait=M3U_REFRESH // 2, usethread=True)
                payload = { "method": "Addons.SetAddonEnabled", "params": {"addonid": PVR_CLIENT_ID, "enabled": state} }
                self.service.jsonRPC.sendJSON(payload)
                self.service._sleep(M3U_REFRESH // 2)

        if not PROPERTIES.isRunning('Tasks.chkPVRRefresh'):
            with PROPERTIES.chkRunning('Tasks.chkPVRRefresh'):
                if brute:
                    if not self.service.player.isPlaying(): 
                        __toggle(False)
                        __toggle(True)
                    else: 
                        PROPERTIES.setPropTimer('chkPVRRefresh')
                
                try: 
                    client_id = self.jsonRPC.getPVRClient(PVR_CLIENT_ID).get('clientid', -1)
                    if client_id != -1: self.jsonRPC.PVRScan(client_id)
                except Exception as e: 
                    self.log(f"chkPVRRefresh: PVR backend scanning trigger unsupported or failed: {str(e)}", xbmc.LOGDEBUG)
            
            
    def chkSettingsChange(self, old_settings={}):
        #if cleanstart ie del settings.xml, restore important values.
        if SETTINGS.restoreSettings(SETTINGS.getCacheSetting('Utilities._runCleanup',default={})):
            SETTINGS.setCacheSetting('Utilities._runCleanup',None)
            
        #settings changed actions.
        new_settings = SETTINGS.getCurrentSettings()
        for setting, old_value in list(old_settings.items()):
            new_value = new_settings.get(setting)
            actions = {'User_Folder'     :{'func':self.setUserPath ,'args':(old_value,new_value)},
                       'Debug_Enable'    :{'func':self.chkDebugging,'args':(new_value)},
                       'TCP_PORT'        :{'func':PROPERTIES.setPendingRestart},
                       'Enable_Autotune' :{'func':self.chkLibrary}}
                       
            if setting in actions and old_value != new_value:
                action = actions.get(setting)
                self.log('chkSettingsChange, detected change in %s: %s => %s\naction = %s'%(setting,old_value,new_value,action))
                self.service._que(action.get('func'),1,0,0,*action.get('args',()),**action.get('kwargs',{}))
        return new_settings


    def chkQUES(self):
        library = Library()
        for i in list(range(BATCH_SIZE)):
            if len(self.service.postQue) > 0:
                try:
                    self.log(f"chkQUES postQue {len(self.service.postQue)}")
                    param = self.service.postQue.pop()
                    self.service._que(self.jsonRPC.requestURL,1,0,0,*param)
                except Exception as e: self.log("chkQUES failed!, queuing = %s postQue: %s\n%s"%(len(self.service.postQue),param,e))
            if len(self.service.jsonQue) > 0:
                try:
                    self.log(f"chkQUES jsonQue {len(self.service.jsonQue)}")
                    param = self.service.jsonQue.pop()
                    self.service._que(self.jsonRPC.sendJSON,-1,0,0,param)
                except Exception as e: self.log("chkQUES failed!, queuing = %s jsonQue: %s\n%s"%(len(self.service.jsonQue),param,e))
            if len(self.service.logoQue) > 0:
                try:
                    self.log(f"chkQUES logoQue {len(self.service.logoQue)}")
                    param = FileAccess.loadJSON(self.service.logoQue.pop())
                    self.service._que(library.resources.getLogo,-1,0,0,*({'name':param},library.resources.getImageCache(param),True))
                except Exception as e: self.log("chkQUES failed!, queuing = %s logoQue: %s\n%s"%(len(self.service.logoQue),param,e))
            if len(self.service.trailerQue) > 0:
                try:
                    self.log(f"chkQUES trailerQue {len(self.service.trailerQue)}")
                    param = FileAccess.loadJSON(self.service.trailerQue.pop())
                    self.service._que(self.jsonRPC.addTrailer,-1,0,0,param)
                except Exception as e: self.log("chkQUES failed!, queuing = %s trailerQue: %s\n%s"%(len(self.service.trailerQue),param,e))        
        del library
        self.service._que(self.chkQUES,5,120)#2MINS
     
     
    def setUserPath(self, old, new):
        self.log('setUserPath, old = %s, new = %s'%(old,new))
        dia = DIALOG.progressDialog(message='%s\n%s'%(LANGUAGE(32050),old))
        with PROPERTIES.interruptActivity():
            FileAccess.copyFolder(old, new, dia)
        PROPERTIES.setPendingRestart()
        DIALOG.progressDialog(100, dia)


    def getChannels(self):
        return Channels().getChannels()
        
        
    def getLibrary(self, type=None):
        Library(service=self.service).getLibrary(type)