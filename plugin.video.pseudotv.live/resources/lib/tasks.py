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
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _client(self):
        self.service._que(SETTINGS.chkPVRBackend,1)
        self.service._que(self.chkHTTP          ,1)
        self.service._que(self.chkDebugging     ,1)
        self.service._que(self.monitor.chkIdle  ,1)
        self.log('_initialize, _client...')
        
        
    def _host(self):
        self._client()
        self._migrateChannels() #temp, remove in v.0.7.5.
        self.service._que(self.chkDirs,1)
        self.service._que(self.chkCrash,1)
        self.log('_initialize, _host...')
    
    
    def _migrateChannels(self, old=CACHE_LOC, new=BACKUP_LOC):
        old_path = os.path.join(old,CHANNELFLE)
        new_path = os.path.join(new,CHANNELFLE)
        if FileAccess.exists(old_path):
            self.log('migrate, importing %s...'%(old_path))
            if Backup().importChannels(old_path):
                if old_path != new_path: 
                    FileAccess.move(old_path,new_path)
                    self.service._que(self.chkChannels,3)
    
    
    def chkHTTP(self):
        timerit(HTTP)(0.1,self.service)
        self.log('chkHTTP')
        
        
    def chkDebugging(self):
        self.log('chkDebugging')
        if SETTINGS.getSettingBool('Debug_Enable'):
            if DIALOG.yesnoDialog(LANGUAGE(32142),autoclose=4):
                self.log('_chkDebugging, disabling debugging.')
                SETTINGS.setSettingBool('Debug_Enable',False)
                DIALOG.notificationDialog(LANGUAGE(32025))
        #Force enable Kodi Debugging when enabled in PseudoTV via JSONRPC only if Kodi access allowed by user.
        if SETTINGS.getSettingBool('Enable_Kodi_Access'):
            self.jsonRPC.toggleShowLog(SETTINGS.getSettingBool('Debug_Enable'))
                    
             
    def chkDiscovery(self):
        timerit(Discovery)(0.1,*(self.service, Multiroom(service=self.service)))
        self.log('chkDiscovery')
         

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
        self._chkEpochTimer('chkVersion'      , self.chkVersion       , 43200 , 1)#12HRS
        self._chkEpochTimer('chkKodiSettings' , self.chkKodiSettings  , 10800 , 1)#3HRS
        self._chkEpochTimer('chkDiscovery'    , self.chkDiscovery     , 300   , 1)#5MINS
        self._chkEpochTimer('chkQUES'         , self.chkQUES          , 120   , 1)#2MINS
        
        if not self.service.isClient:
            self._chkEpochTimer('chkFiles'    , self.chkFiles         , 900   , 1)#15MINS
            self._chkEpochTimer('chkLibrary'  , self.chkLibrary       , 900   , 2)#15MINS
            
        #immediate run, bypass schedule
        self._chkPropTimer('chkPVRRefresh'    , self.chkPVRRefresh    , 1) 
        self._chkPropTimer('chkChanged'       , self.chkChanged       , 3)
        
        
    #_chkEpochTimer trigger - Time = 0 == Run
    def _chkEpochTimer(self, key, func, runevery=900, priority=-1, nextrun=None, *args, **kwargs):
        if nextrun is None: nextrun = int(PROPERTIES.getEXTProperty(key,'0')) # nextrun == 0 => force que
        epoch = int(time.time())
        if epoch >= nextrun:
            self.log('_chkEpochTimer, key = %s, last run %s' % (key, epoch - nextrun))
            PROPERTIES.setEXTProperty(key, (epoch + runevery))
            self.service._que(func, priority, *args, **kwargs)


     #_chkPropTimer trigger - True == Run
    def _chkPropTimer(self, key, func, priority=-1, *args, **kwargs):
        if PROPERTIES.getPropTimer(key):
            self.log('_chkPropTimer, key = %s'%(key))
            PROPERTIES.clrEXTProperty(key)
            self.service._que(func, priority, *args, **kwargs)

 
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


    def chkKodiSettings(self):
        self.log('chkKodiSettings')
        MIN_GUIDEDAYS = SETTINGS.setSettingInt('Min_Days' ,self.jsonRPC.getSettingValue('epg.pastdaystodisplay'     ,default=1))
        MAX_GUIDEDAYS = SETTINGS.setSettingInt('Max_Days' ,self.jsonRPC.getSettingValue('epg.futuredaystodisplay'   ,default=3))
        OSD_TIMER     = SETTINGS.setSettingInt('OSD_Timer',self.jsonRPC.getSettingValue('pvrmenu.displaychannelinfo',default=5))
         

    def chkDirs(self):
        [(self.log('chkDirs, creating [%s]'%(folder)),FileAccess.makedirs(folder)) for folder in [LOGO_LOC,FILLER_LOC,TEMP_LOC] if not FileAccess.exists(os.path.join(folder,''))]


    def chkFiles(self):
        if not PROPERTIES.isRunning('Builder.buildChannels'):
            if any([not bool(FileAccess.exists(file)) for file in [M3UFLEPATH,XMLTVFLEPATH,GENREFLEPATH]]): 
                self.log('chkFiles, missing files! running chkChannels to rebuild.')
                return self.service._que(self.chkChannels,3)


    def chkFillers(self, channels=None, silent=None):
        if silent is None: silent = BUILTIN.isPlaying()
        self.log('chkFillers')
        # if channels is None: channels = self.getChannels())))
        # if len(channels) > 0:
            # for fidx, ftype in enumerate(FILLER_TYPES):
                # fpath = os.path.join(FILLER_LOC,ftype.lower(),'')
                # if not FileAccess.exists(fpath): FileAccess.makedirs(fpath)
                
                # for cidx, citem in enumerate(channels):
                    # cpath = os.path.join(fpath, citem.get('name','').lower())
                    # if not FileAccess.exists(cpath): FileAccess.makedirs(cpath)
                    
                    # for gidx, genres in channels()
                    
                    # if not FileAccess.exists(os.path.join(FILLER_LOC,ftype.lower(),genre.lower(),'')):
                        # FileAccess.makedirs(os.path.join(FILLER_LOC,ftype.lower(),''))
                
                # for ftype in FILLER_TYPES[1:]:
                    # for genre in genres:
                        # if not FileAccess.exists(os.path.join(FILLER_LOC,ftype.lower(),genre.lower(),'')):
                            # pDialog = DIALOG.progressBGDialog(int(idx*50//len(channels)), pDialog, message='%s: %s'%(genre,int(idx*100//len(channels)))+'%', header='%s, %s'%(ADDON_NAME,LANGUAGE(32179)))
                            # FileAccess.makedirs(os.path.join(FILLER_LOC,ftype.lower(),genre.lower()))
                    
                    # if not FileAccess.exists(os.path.join(FILLER_LOC,ftype.lower(),citem.get('name','').lower())):
                        # if ftype.lower() == 'adverts': IGNORE = IGNORE_CHTYPE + MOVIE_CHTYPE
                        # else:                          IGNORE = IGNORE_CHTYPE
                        # if citem.get('name') and not citem.get('radio',False) and citem.get('type') not in IGNORE: 
                            # pDialog = DIALOG.progressBGDialog(int(idx*50//len(channels)), pDialog, message='%s: %s'%(citem.get('name'),int(idx*100//len(channels)))+'%', header='%s, %s'%(ADDON_NAME,LANGUAGE(32179)))
                            # FileAccess.makedirs(os.path.join(FILLER_LOC,ftype.lower(),citem['name'].lower()))
            # pDialog = DIALOG.progressBGDialog(100, pDialog, message=LANGUAGE(32025), header='%s, %s'%(ADDON_NAME,LANGUAGE(32179)))
        
        
    def chkTrailers(self, silent=None):
        if silent is None: silent = BUILTIN.isPlaying()
        self.log("_chkTrailers, silent = %s"%(silent))
        #todo clean old trailers by "added" epoch
        if not PROPERTIES.isRunning('Tasks.chkTrailers'):
            with PROPERTIES.chkRunning('Tasks.chkTrailers'):
                trailers = self.jsonRPC.getTrailers()
                pDialog  = None
                pHeader  = '%s, %s %ss'%(ADDON_NAME,LANGUAGE(32022),LANGUAGE(30187))
                with DIALOG._progressDialog(LANGUAGE(32015), pHeader, silent) as pDialog:
                    movies = self.jsonRPC.getMovies()
                    for midx, movie in enumerate(movies):
                        if movie.get('trailer'):
                            pDialog = DIALOG._updateProgress(pDialog,int(midx*100))
                            trailers = self.jsonRPC.addTrailer(movie, trailers)
                with DIALOG._progressDialog(LANGUAGE(32014), pHeader, silent) as pDialog:
                    tvshows  = self.jsonRPC.getTVshows()
                    for tidx, tvshow in enumerate(tvshows):
                        if tvshow.get('trailer'):
                            print(tidx,tvshow)
                            pDialog = DIALOG._updateProgress(pDialog,int(tidx*100))
                            trailers = self.jsonRPC.addTrailer(tvshow, trailers)
                self.jsonRPC.setTrailers(trailers)
                
                            
    def chkLibrary(self, types=None, silent=None):
        if silent is None: silent = BUILTIN.isPlaying()
        self.log("chkLibrary, types = %s, silent = %s"%(types,silent))
        complete = []
        library  = Library(service=self.service, writable=True)
        library.searchRecommended()
        if types is None: types = AUTOTUNE_TYPES
        for idx, type in enumerate(types):
            items = library.getLibrary(type)
            if self.service._interrupt() or self.service._suspend():
                self.log("chkLibrary, _interrupt/_suspend")
                return self.service._que(self.chkLibrary,2,*(types[idx:],silent))
            elif items:
                self.log("chkLibrary, %s library found! Setting items (%s), queuing update."%(type,len(items)))
                complete.append(library.setLibrary(type, items))
                self.service._que(library.updateLibrary,-1,*([type],True))
            else:
                self.log("chkLibrary, %s library not found! starting update."%(type))
                complete.append(library.updateLibrary([type],silent))
        del library
        if any(complete): self.service._que(self.chkChannels,3)
        self.log("chkLibrary, complete = %s"%(any(complete)))
        

    def chkChanged(self, channels=None, silent=None):
        if silent is None: silent = BUILTIN.isPlaying()
        if channels is None: channels = self.getChannels()
        [self.service._que(Builder(service=self.service).buildChannels,3,*([channel],False,silent)) for channel in channels if channel.get('changed',False)]
        
        
    def chkChannels(self, channels=None, silent=None):
        autotune = SETTINGS.getSettingBool('Enable_Autotune')
        if silent is None: silent = BUILTIN.isPlaying()
        if channels is None: channels = self.getChannels()
        if len(channels) > 0:
            self.log('chkChannels, channels = %s'%(len(channels)))
            self.service._que(Builder(service=self.service).buildChannels,3,*(channels,False,silent))
            if SETTINGS.getSettingBool('Build_Filler_Folders'): self._que(self.chkFillers,4,*(channels,silent))
        else:
            self.log('chkChannels, No Channels Configured!')
            if autotune or not SETTINGS.hasAutotuned():
                self.log('chkChannels, Auto-tuning Channels.')
                if SETTINGS.setAutotuned(_autotune(automatic=autotune)): PROPERTIES.setPropTimer('chkChanged')
            elif PROPERTIES.hasEnabledServers():                         PROPERTIES.setPropTimer('chkPVRRefresh')#refresh pvr guide


    @debounceit(M3U_INTERVAL)
    def chkPVRRefresh(self, brute=SETTINGS.getSettingBool('Enable_PVR_RELOAD')):
        self.log('chkPVRRefresh')
        def __toggle(state=True):
            with BUILTIN.busy_dialog(lock=True):
                self.log('chkPVRRefresh, __toggle = %s'%(state))
                self.service.jsonRPC.sendJSON({"method":"Addons.SetAddonEnabled","params":{"addonid":PVR_CLIENT_ID,"enabled":state}})
            
        if not PROPERTIES.isRunning('Tasks.chkPVRRefresh'):
            with PROPERTIES.chkRunning('Tasks.chkPVRRefresh'):
                if brute:
                    if not self.service.player.isPlaying() and BUILTIN.getInfoBool('System.AddonIsEnabled(%s)'%(PVR_CLIENT_ID)):
                        DIALOG.notificationWait('%s: %s'%(PVR_CLIENT_NAME,LANGUAGE(32125)),wait=M3U_REFRESH, usethread=True)
                        BUILTIN.executewindow('ActivateWindow(home)')
                        __toggle(False), self.service._sleep(M3U_REFRESH), __toggle(True)
                    else: PROPERTIES.setPropTimer('chkPVRRefresh')#refresh pvr guide
                else:
                    try: self.jsonRPC.PVRScan(self.jsonRPC.getPVRClient(PVR_CLIENT_ID).get('clientid',-1)) #currently not supported by IPTV Simple.
                    except Exception: pass #PROPERTIES.setEXTProperty('%s.HTTP.pendingRestart'%(ADDON_ID),True)
            
            
    def chkSettingsChange(self, settings={}):
        nSettings = SETTINGS.getCurrentSettings()
        for setting, value in list(settings.items()):
            actions = {'User_Folder'     :{'func':self.setUserPath            ,'kwargs':{'old':value,'new':nSettings.get(setting)}},
                       'Debug_Enable'    :{'func':self.jsonRPC.toggleShowLog  ,'kwargs':{'state':SETTINGS.getSettingBool('Debug_Enable')}},
                       'TCP_PORT'        :{'func':SETTINGS.chkPVRBackend},
                       'Autotune_Limit'  :{'func':SETTINGS.setAutotuned       ,'kwargs':{'state':False}},
                       'Enable_Autotune':{'func':PROPERTIES.setPropTimer     ,'kwargs':{'key':'chkChanged','state':True}},}
                       
            if nSettings.get(setting) != value and actions.get(setting):
                action = actions.get(setting)
                self.log('chkSettingsChange, detected change in %s: %s => %s\naction = %s'%(setting,value,nSettings.get(setting),action))
                self.service._que(action.get('func'),1,*action.get('args',()),**action.get('kwargs',{}))
        return nSettings


    def chkQUES(self):
        library = Library()
        for i in list(range(QUEUE_CHUNK)):
            if self.service._interrupt() or self.service._suspend():
                self.log("chkQUES, _interrupt/_suspend")
                self.service._que(self.chkQUES,-1)
                break
            else:
                if len(self.service.postQue) > 0:
                    try:
                        param = self.service.postQue.pop()
                        self.service._que(self.jsonRPC.requestURL,1,*param)
                    except Exception as e: self.log("chkQUES failed!, queuing = %s\npostQue: %s\n%s"%(len(self.service.postQue),param,e))
                if len(self.service.jsonQue) > 0:
                    try:
                        param = self.service.jsonQue.pop()
                        self.service._que(self.jsonRPC.sendJSON,-1,param)
                    except Exception as e: self.log("chkQUES failed!, queuing = %s\njsonQue: %s\n%s"%(len(self.service.jsonQue),param,e))
                if len(self.service.logoQue) > 0:
                    try:
                        param = FileAccess.loadJSON(self.service.logoQue.pop())
                        self.service._que(library.resources.getLogo,-1,*(param,library.resources.getCache(param),True))
                    except Exception as e: self.log("chkQUES failed!, queuing = %s\nlogoQue: %s\n%s"%(len(self.service.logoQue),param,e))
        del library
        
                
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