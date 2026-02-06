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

class Tasks(object):
    citems  = []
    cache   = SETTINGS.cache
    cacheDB = SETTINGS.cacheDB
    
    def __init__(self, service):
        self.service = service       
        self.jsonRPC = service.jsonRPC
        self.player  = service.player
        self.monitor = service.monitor


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _client(self):
        self.service._que(self.monitor.chkIdle,1)
        self.service._que(self.chkHTTP        ,1)
        self.service._que(self.chkInstanceID  ,1)
        self.service._que(self.chkPVRBackend  ,1)
        self.service._que(self.chkDebugging   ,1)
        self.log('_initialize, _client...')
        
        
    def _host(self):
        self._client()
        self.service._que(self.chkDirs,1)
        self.service._que(self.chkBackup,1)
        self.service._que(self.chkCrash,1)
        self.log('_initialize, _host...')
    
    
    def chkHTTP(self):
        timerit(HTTP)(0.1,[self.service])
        self.log('chkHTTP')
        
        
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
        timerit(Discovery)(0.1,[self.service, Multiroom(service=self.service)])
        self.log('chkDiscovery')
         
         
    def chkBackup(self):
        self.log('chkBackup')
        Backup().hasBackup()


    def chkCrash(self):
        self.log('chkCrash')
        # failed_citem = (SETTINGS.getCacheSetting('KODI.CRASH.JSONRPC.CITEM',json_data=True) or {})
        # if failed_citem:
            # SETTINGS.setCacheSetting('KODI.CRASH.JSONRPC.CITEM',None,json_data=False)
            # DIALOG.okDialog(f'Kodi encountered a fatal error while parsing a {ADDON_NAME} channel.\n{failed_citem.get('name')} was temporarily disabled!', usethread=True)
        
        
    def chkServers(self):
        self.log('chkServers')
        Multiroom(service=self.service)._chkServers()


    def chkPVRBackend(self): 
        self.log('chkPVRBackend')
        if SETTINGS.hasAddon(PVR_CLIENT_ID,True,True,True,True):
            if not SETTINGS.hasPVRInstance():
                SETTINGS.setPVRRemote(PROPERTIES.getRemoteHost(), PROPERTIES.getFriendlyName())


    def chkQueTimer(self):
        self.log('chkQueTimer')
        self._chkEpochTimer('chkVersion'      , self.chkVersion       , 43200 , 1)#12HRS
        self._chkEpochTimer('chkKodiSettings' , self.chkKodiSettings  , 10800 , 1)#3HRS
        self._chkEpochTimer('chkDiscovery'    , self.chkDiscovery     , 300   , 1)#10MINS
        self._chkEpochTimer('chkServers'      , self.chkServers       , 1800  , 1)#30MINS
        self._chkEpochTimer('chkQUES'         , self.chkQUES          , 300   , 1)#10MINS
        
        if not self.service.isClient:
            self._chkEpochTimer('chkFiles'    , self.chkFiles         , 600   , 1)
            self._chkEpochTimer('chkLibrary'  , self.chkLibrary       , 10800 , 2)#3HRS
            
        #immediate run, bypass schedule
        self._chkPropTimer('chkPVRRefresh'    , self.chkPVRRefresh    , 1) 
        self._chkPropTimer('chkChannels'      , self.chkChannels      , 3)
        
        
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
        elif ADDON_VERSION > (SETTINGS.getCacheSetting('lastVersion', checksum=ADDON_VERSION, revive=True) or '0.0.0'):
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
        [(self.log('chkDirs, creating [%s]'%(folder)),FileAccess.makedirs(folder)) for folder in [LOGO_LOC,FILLER_LOC,TEMP_LOC,TEMP_IMAGE_LOC] if not FileAccess.exists(os.path.join(folder,''))]


    def chkFiles(self):
        for file in [CHANNELFLEPATH,M3UFLEPATH,XMLTVFLEPATH,GENREFLEPATH]:
            if not FileAccess.exists(file):
                self.log('chkFiles, missing [%s]'%(file))
                return self.service._que(self.chkChannels,3)


    def chkLibrary(self, types=None, silent=False):
        self.log("chkLibrary, types = %s, silent = %s"%(types,silent))
        complete = set()
        library  = Library(service=self.service)
        library.searchRecommended()
        if types is None: types = AUTOTUNE_TYPES
        for idx, type in enumerate(types):
            items = library.getLibrary(type)
            if self.service._interrupt() or self.service._suspend():
                self.log("chkLibrary, _interrupt/_suspend")
                return self.service._que(self.chkLibrary,2,*(types[idx:],silent))
            elif items:
                self.log("chkLibrary, %s library found! Setting items (%s), queuing update."%(type,len(items)))
                complete.add(library.setLibrary(type, items))
                self.service._que(library.updateLibrary,-1,*([type],True))
            else:
                self.log("chkLibrary, %s library not found! starting update."%(type))
                complete.add(library.updateLibrary([type],silent))
        if any(list(complete)): self.service._que(self.chkChannels,3)
        self.log("chkLibrary, complete = %s"%(any(list(complete))))
        del library
        
        
    def chkChannels(self, channels: list=[], save=False):
        builder = Builder(service=self.service)
        if not channels:
            channels = builder.getVerifiedChannels()
            self.citems = channels
        if len(channels) > 0:
            self.log('chkChannels, channels = %s'%(len(channels)))
            [self.service._que(builder.buildChannels,3,[channel]) for channel in channels]
        else:
            self.log('chkChannels, No Channels Configured!')
            if not SETTINGS.hasAutotuned():      SETTINGS.setAutotuned(Autotune()._runTune())
            elif PROPERTIES.hasEnabledServers(): timerit(PROPERTIES.setPropTimer)(FIFTEEN,['chkPVRRefresh'])
        del builder


    def chkPVRRefresh(self, brute=SETTINGS.getSettingBool('Enable_PVR_RELOAD')):
        self.log('chkPVRRefresh')
        def __toggle(state):
            self.log('chkPVRRefresh, __toggle = %s'%(state))
            self.service.jsonRPC.sendJSON({"method":"Addons.SetAddonEnabled","params":{"addonid":PVR_CLIENT_ID,"enabled":state}})
            
        if not PROPERTIES.isRunning('Tasks.chkPVRRefresh') and not PROPERTIES.isRunning('Builder.buildChannels'):
            with PROPERTIES.chkRunning('Tasks.chkPVRRefresh'):
                self.service._que(self.http._restart,1)
                if brute:
                    if not self.service.player.isPlaying() and BUILTIN.getInfoBool('AddonIsEnabled(%s)'%(PVR_CLIENT_ID),'System'):
                        with BUILTIN.busy_dialog(lock=True):
                            # BUILTIN.executebuiltin("Dialog.Close(all)")
                            DIALOG.notificationWait('%s: %s'%(PVR_CLIENT_NAME,LANGUAGE(32125)),wait=M3U_REFRESH, usethread=True)
                            __toggle(False), self.service._sleep(M3U_REFRESH*2), __toggle(True)
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


    def chkQUES(self):
        library = Library()
        for i in list(range(QUEUE_CHUNK)):
            if self.service._interrupt() or self.service._suspend():
                self.log("chkQUES, _interrupt/_suspend")
                self.service._que(self.chkQUES,-1)
                break
            else:
                if len(self.service.postQue) > 0:
                    param = self.service.postQue.pop()
                    self.log("chkQUES, queuing = %s\npostQue: %s"%(len(self.service.postQue),param))
                    self.service._que(requestURL,1,*param)
                if len(self.service.jsonQue) > 0:
                    param = self.service.jsonQue.pop()
                    self.log("chkQUES, queuing = %s\njsonQue:%s"%(len(self.service.jsonQue),param))
                    self.service._que(self.jsonRPC.sendJSON,-1,param)
                if len(self.service.logoQue) > 0:
                    param = FileAccess.loadJSON(self.service.logoQue.pop())
                    self.log("chkQUES, queuing = %s\nlogoQue:%s"%(len(self.service.logoQue),param))
                    self.service._que(library.resources.getLogo,-1,*(param,library.resources.getCache(param.get('name')),True,None))
        del library
        
                
    def setUserPath(self, old, new):
        with PROPERTIES.interruptActivity():
            self.log('setUserPath, old = %s, new = %s'%(old,new))
            dia = DIALOG.progressDialog(message='%s\n%s'%(LANGUAGE(32050),old))
            FileAccess.copyFolder(old, new, dia)
            PROPERTIES.setPendingRestart()
            DIALOG.progressDialog(100, dia)
