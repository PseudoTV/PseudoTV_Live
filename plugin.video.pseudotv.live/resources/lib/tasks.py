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
#
# -*- coding: utf-8 -*-

from globals    import *
from library    import Library
from autotune   import Autotune
from builder    import Builder
from backup     import Backup
from multiroom  import Discovery, Multiroom
from wizard     import Wizard
from server     import HTTP

class Tasks():
    cache   = SETTINGS.cache
    cacheDB = SETTINGS.cacheDB
    
    def __init__(self, service):
        self.log('__init__')    
        self.service = service       
        self.jsonRPC = service.jsonRPC
        self.player  = service.player
        self.monitor = service.monitor
        self.http    = HTTP(service=self.service)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _client(self):
        self.service._que(self.chkHTTP,1)
        self.service._que(self.chkInstanceID,1)
        self.service._que(self.chkPVRBackend,1)
        self.service._que(self.chkDebugging,1)
        self.service._que(self.chkDiscovery,1)
        self.log('_initialize, _client...')
        
        
    def _host(self):
        self._client()
        self.service._que(self.chkDirs,1)
        self.service._que(self.chkBackup,1)
        self.service._que(self.chkWizard,1)
        self.log('_initialize, _host...')
    
    
    def chkHTTP(self):
        self.log('chkHTTP')
        Thread(target=self.http._start).start()
        
        
    def chkInstanceID(self):
        self.log('chkInstanceID')
        PROPERTIES.getInstanceID()
        

    def chkWizard(self):
        self.log('chkWizard')
        if not SETTINGS.hasWizardRun():
            BUILTIN.executescript('special://home/addons/%s/resources/lib/utilities.py, Run_Wizard'%(ADDON_ID))
            

    def chkDebugging(self):
        self.log('chkDebugging')
        if SETTINGS.getSettingBool('Debug_Enable'):
            if DIALOG.yesnoDialog(LANGUAGE(32142),autoclose=4):
                self.log('_chkDebugging, disabling debugging.')
                SETTINGS.setSettingBool('Debug_Enable',False)
                DIALOG.notificationDialog(LANGUAGE(32025))
        if SETTINGS.getSettingBool('Enable_Kodi_Access'):
            self.jsonRPC.toggleShowLog(SETTINGS.getSettingBool('Debug_Enable'))
                    
                   
    def chkDiscovery(self):
        self.log('chkDiscovery')
        Thread(target=Discovery(self.service, Multiroom(service=self.service))._start).start()
        
         
    def chkBackup(self):
        self.log('chkBackup')
        Backup().hasBackup()


    def chkServers(self):
        self.log('chkServers')
        self.service._que(Multiroom(service=self.service)._chkServers,1)


    def chkPVRBackend(self): 
        self.log('chkPVRBackend')
        if SETTINGS.hasAddon(PVR_CLIENT_ID,True,True,True,True):
            if not SETTINGS.hasPVRInstance():
                SETTINGS.setPVRRemote(PROPERTIES.getRemoteHost(), PROPERTIES.getFriendlyName())


    def chkQueTimer(self):
        self.log('chkQueTimer')
        self._chkEpochTimer('chkVersion'      , self.chkVersion       , 43200)
        self._chkEpochTimer('chkKodiSettings' , self.chkKodiSettings  , 1800)
        self._chkEpochTimer('chkServers'      , self.chkServers       , 900)
        
        if not self.service.isClient:
            self._chkEpochTimer('chkLibrary'  , self.chkLibrary       , 3600)
            self._chkEpochTimer('chkChannels' , self.chkChannels      , 3600)
            self._chkEpochTimer('chkFiles'    , self.chkFiles         , 600)
            self._chkEpochTimer('chkJSONQUE'  , self.chkJSONQUE       , 600)
            self._chkEpochTimer('chkLOGOQUE'  , self.chkLOGOQUE       , 600)
            
        self._chkPropTimer('chkPVRRefresh'    , self.chkPVRRefresh    , 1)
        
        
    def _chkEpochTimer(self, key, func, runevery=900, priority=-1, nextrun=None, *args, **kwargs):
        if nextrun is None: nextrun = PROPERTIES.getPropertyInt(key, default=0) # nextrun == 0 => force que
        epoch = int(time.time())
        if epoch >= nextrun:
            self.log('_chkEpochTimer, key = %s, last run %s' % (key, epoch - nextrun))
            PROPERTIES.setEpochTimer(key, (epoch + runevery))
            self.service._que(func, priority, *args, **kwargs)


    def _chkPropTimer(self, key, func, priority=-1, *args, **kwargs):
        key = '%s.%s' % (ADDON_ID, key)
        if PROPERTIES.getEXTPropertyBool(key):
            self.log('_chkPropTimer, key = %s'%(key))
            PROPERTIES.clrEXTProperty(key)
            self.service._que(func, priority, *args, **kwargs)
            

    @cacheit(expiration=datetime.timedelta(minutes=FIFTEEN))
    def getOnlineVersion(self):
        try:    ONLINE_VERSION = re.compile('" version="(.+?)" name="%s"'%(ADDON_NAME)).findall(str(requestURL(ADDON_URL)))[0]
        except: ONLINE_VERSION = ADDON_VERSION
        self.log('getOnlineVersion, version = %s'%(ONLINE_VERSION))
        return ONLINE_VERSION
        
        
    def chkVersion(self):
        update = False
        ONLINE_VERSION = self.getOnlineVersion()
        if ADDON_VERSION < ONLINE_VERSION: 
            update = True
            DIALOG.notificationDialog(LANGUAGE(30073)%(ONLINE_VERSION))
        elif ADDON_VERSION > (SETTINGS.getCacheSetting('lastVersion', checksum=ADDON_VERSION) or '0.0.0'):
            SETTINGS.setCacheSetting('lastVersion',ADDON_VERSION, checksum=ADDON_VERSION)
            BUILTIN.executescript('special://home/addons/%s/resources/lib/utilities.py, Show_Changelog'%(ADDON_ID))
        self.log('chkVersion, update = %s, installed version = %s, online version = %s'%(update,ADDON_VERSION,ONLINE_VERSION))
        SETTINGS.setSetting('Update_Status',{'True':'[COLOR=yellow]%s [B]v.%s[/B][/COLOR]'%(LANGUAGE(32168),ONLINE_VERSION),'False':'None'}[str(update)])


    def chkKodiSettings(self):
        self.log('chkKodiSettings')
        MIN_GUIDEDAYS = SETTINGS.setSettingInt('Min_Days' ,self.jsonRPC.getSettingValue('epg.pastdaystodisplay'     ,default=1))
        MAX_GUIDEDAYS = SETTINGS.setSettingInt('Max_Days' ,self.jsonRPC.getSettingValue('epg.futuredaystodisplay'   ,default=3))
        OSD_TIMER     = SETTINGS.setSettingInt('OSD_Timer',self.jsonRPC.getSettingValue('pvrmenu.displaychannelinfo',default=5))
         

    def chkDirs(self):
        [(self.log('chkDirs, creating [%s]'%(folder)),FileAccess.makedirs(folder)) for folder in [LOGO_LOC,FILLER_LOC,TEMP_LOC] if not FileAccess.exists(os.path.join(folder,''))]


    def chkFiles(self):
        for file in [CHANNELFLEPATH,M3UFLEPATH,XMLTVFLEPATH,GENREFLEPATH]:
            if not FileAccess.exists(file):
                self.log('chkFiles, missing [%s]'%(file))
                return self.service._que(self.chkChannels,3)


    def chkLibrary(self, types=None):
        library = Library(service=self.service)
        # library.searchRecommended()
        # library.importPrompt() #todo refactor feature
        if types is None: types = list(library.AUTOTUNE.keys())
        for idx, type in enumerate(types):
            if self.service._interrupt(): 
                self.log("chkLibrary, _interrupt")
                self.service._que(self.chkLibrary,2)
                break
            elif self.jsonRPC.cache.get("%s.%s"%(library.__class__.__name__,library.AUTOTUNE[type]['func'].__name__)) is None:
                self.log("chkLibrary, %s cache unavailable queuing build."%(type))
                self.service._que(library.queLibrary,-1,type)
            else:
                self.log("chkLibrary, %s cache found queuing update."%(type))
                self.service._que(library.updateLibrary,-1,type)
        del library
        
        
    def chkChannels(self, channels: list=[], save=False):
        builder            = Builder(service=self.service)
        hasAutotuned       = SETTINGS.hasAutotuned()
        hasEnabledServers  = PROPERTIES.hasEnabledServers()
        buildFillerFolders = SETTINGS.getSettingBool('Build_Filler_Folders')
        
        if not channels:
            save = True #only save full channel list
            channels = builder.getVerifiedChannels()
        self.log('chkChannels, channels = %s, hasAutotuned = %s, hasEnabledServers = %s, buildFillerFolders = %s'%(len(channels),hasAutotuned,hasEnabledServers,buildFillerFolders))

        if len(channels) > 0:
            complete, refresh = builder.build(channels)
            self.log('chkChannels, complete = %s, save = %s, refresh = %s'%(complete,save,refresh))
            if complete:
                if save: builder.channels.setChannels(channels)
                if refresh: PROPERTIES.setPropTimer('chkPVRRefresh')
                # if buildFillerFolders: self.service._que(self.chkFillers,2,channels)#todo repair
            else: self.service._que(self.chkChannels,3,channels)
        else:
            self.log('chkChannels, No Channels Configured!')
            if not hasAutotuned:    pass#DIALOG.notificationDialog(LANGUAGE(32181))
            elif hasEnabledServers: PROPERTIES.setPropTimer('chkPVRRefresh')
            else:                   DIALOG.notificationDialog(LANGUAGE(32058))
        PROPERTIES.setChannels(len(channels) > 0)
        del builder


    def chkLOGOQUE(self):
        def __run(idx):
            if len(params) > 0:
                param = params.pop(0)
                self.log("chkLOGOQUE, remaining queue = %s\n%s"%(len(params),param))
                if param.get('name','').startswith('getLogoResources'):
                    self.service._que(resources.getLogoResources, 5+i, *param.get('args',()), **param.get('kwargs',{}))
                elif param.get('name','').startswith('getTVShowLogo'):
                    self.service._que(resources.getTVShowLogo, 5+i, *param.get('args',()), **param.get('kwargs',{}))

        if not PROPERTIES.isRunning('Tasks.chkLOGOQUE') and self.monitor.isIdle:
            with PROPERTIES.chkRunning('Tasks.chkLOGOQUE'):
                params = randomShuffle(SETTINGS.queuePool.get('queueLOGO',[]))
                if len(params) == 0: return
                resources = Library(service=self.service).resources
                poolit(__run)(list(range(QUEUE_CHUNK)))
                SETTINGS.queuePool['queueLOGO'] = setDictLST(params)
                self.log('chkLOGOQUE, remaining = %s'%(len(SETTINGS.queuePool['queueLOGO'])))
                del resources
                
                
    def chkJSONQUE(self):
        def __run(idx):
            if len(params) > 0:
                param = params.pop(0)
                self.log("chkJSONQUE, remaining queue = %s\n%s"%(len(params),param))
                self.service._que(self.jsonRPC.sendJSON,5+i, param)

        if not PROPERTIES.isRunning('Tasks.chkJSONQUE') and self.monitor.isIdle:
            with PROPERTIES.chkRunning('Tasks.chkJSONQUE'):
                params = randomShuffle(SETTINGS.queuePool.get('queueJSON',[]))
                if len(params) == 0: return
                poolit(__run)(list(range(QUEUE_CHUNK)))
                SETTINGS.queuePool['queueJSON'] = setDictLST(params)
                self.log('chkJSONQUE, remaining = %s'%(len(SETTINGS.queuePool['queueJSON'])))


    def chkPVRRefresh(self, brute=SETTINGS.getSettingBool('Enable_PVR_RELOAD')):
        self.log('chkPVRRefresh')
        def __toggle(state):
            self.log('chkPVRRefresh, __toggle = %s'%(state))
            self.service.jsonRPC.sendJSON({"method":"Addons.SetAddonEnabled","params":{"addonid":PVR_CLIENT_ID,"enabled":state}})
            
        if not PROPERTIES.isRunning('Tasks.chkPVRRefresh'):
            with PROPERTIES.chkRunning('Tasks.chkPVRRefresh'):
                self.service._que(self.http._restart,1)
                if brute:
                    if not BUILTIN.isPlaying() and BUILTIN.getInfoBool('AddonIsEnabled(%s)'%(PVR_CLIENT_ID),'System'):
                        with BUILTIN.busy_dialog(lock=True):
                            # BUILTIN.executebuiltin("Dialog.Close(all)")
                            DIALOG.notificationWait('%s: %s'%(PVR_CLIENT_NAME,LANGUAGE(32125)),wait=M3U_REFRESH, usethread=True)
                            __toggle(False), self.service._wait(M3U_REFRESH*2), __toggle(True)
                    else: self.service._que(self.chkPVRRefresh,1)
            
            
    def chkSettingsChange(self, settings={}):
        nSettings = SETTINGS.getCurrentSettings()
        for setting, value in list(settings.items()):
            actions = {'User_Folder'  :{'func':self.setUserPath            ,'kwargs':{'old':value,'new':nSettings.get(setting)}},
                       'Debug_Enable' :{'func':self.jsonRPC.toggleShowLog  ,'kwargs':{'state':SETTINGS.getSettingBool('Debug_Enable')}},
                       'TCP_PORT'     :{'func':SETTINGS.setPVRRemote       ,'kwargs':{'host':PROPERTIES.getRemoteHost(),'instance':PROPERTIES.getFriendlyName()}},}
                       
            if nSettings.get(setting) != value and actions.get(setting):
                action = actions.get(setting)
                self.log('chkSettingsChange, detected change in %s: %s => %s\naction = %s'%(setting,value,nSettings.get(setting),action))
                self.service._que(action.get('func'),1,*action.get('args',()),**action.get('kwargs',{}))
        return nSettings


    def setUserPath(self, old, new):
        with PROPERTIES.interruptActivity():
            self.log('setUserPath, old = %s, new = %s'%(old,new))
            dia = DIALOG.progressDialog(message='%s\n%s'%(LANGUAGE(32050),old))
            FileAccess.copyFolder(old, new, dia)
            PROPERTIES.setPendingRestart()
            DIALOG.progressDialog(100, dia)
            
            
    def getVerifiedChannels(self):
        return Builder(service=self.service).getVerifiedChannels()