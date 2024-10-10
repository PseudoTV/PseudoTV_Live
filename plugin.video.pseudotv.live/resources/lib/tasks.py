#   Copyright (C) 2024 Lunatixz
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
from cqueue     import *
from library    import Library
from autotune   import Autotune
from builder    import Builder
from backup     import Backup
from multiroom  import Multiroom
from manager    import Manager
from server     import HTTP


class Tasks():
    def __init__(self, service=None):
        self.log('__init__')
        self.cache       = SETTINGS.cache
        self.service     = service
        self.jsonRPC     = service.jsonRPC
        self.httpServer  = HTTP(service=service)
        self.multiroom   = Multiroom(service=service)
        self.quePriority = CustomQueue(priority=True,service=self.service)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _que(self, func, priority=-1, *args, **kwargs):# priority -1 autostack, 1 Highest, 5 Lowest
        if priority == -1: priority = self.quePriority.qsize + 1
        self.log('_que, priority = %s, func = %s, args = %s, kwargs = %s' % (priority,func.__name__, args, kwargs))
        self.quePriority._push((func, args, kwargs), priority)
        

    def _initialize(self):
        tasks = [self.chkInstanceID,
                 self.chkDiscovery,
                 self.chkWelcome,
                 self.chkDebugging,
                 self.chkBackup,
                 self.chkPVRBackend]

        for func in tasks:
            if self.service._interrupt(): break
            self._que(func)
        self.log('_initialize, finished...')
        
        
    def chkInstanceID(self):
        self.log('chkInstanceID')
        PROPERTIES.getInstanceID()
        
        
    def chkWelcome(self):
        self.log('chkWelcome')
        BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/utilities.py,Show_Welcome)')
              
                  
    @cacheit(expiration=datetime.timedelta(hours=3),checksum=PROPERTIES.getInstanceID())
    def getOnlineVersion(self):
        try:    ONLINE_VERSON = re.compile('" version="(.+?)" name="%s"'%(ADDON_NAME)).findall(str(getURL(ADDON_URL)))[0]
        except: ONLINE_VERSON = ADDON_VERSION
        self.log('getOnlineVersion, ONLINE_VERSON = %s'%(ONLINE_VERSON))
        return ONLINE_VERSON
        
        
    def chkDebugging(self):
        self.log('chkDebugging')
        if SETTINGS.getSettingBool('Enable_Debugging'):
            if DIALOG.yesnoDialog(LANGUAGE(32142),autoclose=4):
                self.log('_chkDebugging, disabling debugging.')
                SETTINGS.setSettingBool('Enable_Debugging',False)
                DIALOG.notificationDialog(LANGUAGE(321423))


    def chkBackup(self):
        self.log('chkBackup')
        Backup().hasBackup()


    def chkPVRBackend(self): 
        self.log('chkPVRBackend')
        if hasAddon(PVR_CLIENT_ID,True,True,True,True):
            if not SETTINGS.hasPVRInstance():
                with BUILTIN.busy_dialog(isPlaying=BUILTIN.getInfoBool('Playing','Player')):
                    SETTINGS.setPVRPath(USER_LOC, SETTINGS.getFriendlyName())
        

    def _chkQueTimer(self):
        self.log('_chkQueTimer')
        self._chkEpochTimer('chkVersion'    , self.chkVersion    , 7200)
        self._chkEpochTimer('chkPVRSettings', self.chkPVRSettings, 900)
        self._chkEpochTimer('chkPVRservers' , self.chkPVRservers , 900)
        self._chkEpochTimer('chkFiles'      , self.chkFiles      , 300)
        self._chkEpochTimer('chkHTTP'       , self.chkHTTP       , 900)
        self._chkEpochTimer('chkRecommended', self.chkRecommended, 900)
        self._chkEpochTimer('chkLibrary'    , self.chkLibrary    , (MAX_GUIDEDAYS*3600))
        self._chkEpochTimer('chkChannels'   , self.chkChannels   , (MAX_GUIDEDAYS*3600))
        self._chkEpochTimer('chkJSONQUE'    , self.chkJSONQUE    , 300)
        
        self._chkPropTimer('chkPVRRefresh'  , self.chkPVRRefresh)
        self._chkPropTimer('chkFillers'     , self.chkFillers)
        self._chkPropTimer('chkDiscovery'   , self.chkDiscovery)
        self._chkPropTimer('runAutoTune'    , self.runAutoTune)
        
        
    def _chkEpochTimer(self, key, func, runevery, nextrun=None, *args, **kwargs):
        if nextrun is None: nextrun = (PROPERTIES.getPropertyInt(key) or 0)# nextrun == 0 => force run
        epoch = int(time.time())
        run = (epoch >= nextrun)
        if run and (not self.service._interrupt() and not self.service._suspend()):
            self.log('_chkEpochTimer, key = %s, run = %s'%(key,run))
            PROPERTIES.setPropertyInt(key,(epoch+runevery))
            return self._que(func)
        

    def _chkPropTimer(self, key, func):
        key = '%s.%s'%(ADDON_ID,key)
        run = PROPERTIES.getEXTProperty(key) == 'true'
        self.log('_chkPropTimer, key = %s, run = %s'%(key,run))
        if run and (not self.service._interrupt() and not self.service._suspend()):
            PROPERTIES.clearEXTProperty(key)
            self._que(func)


    def chkVersion(self):
        self.log('chkVersion')
        update = False
        ONLINE_VERSION = self.getOnlineVersion()
        if ADDON_VERSION < ONLINE_VERSION: 
            update = True
            DIALOG.notificationDialog('%s\nVersion: [B]%s[/B]'%(LANGUAGE(32168),ONLINE_VERSION))
        elif ADDON_VERSION > (SETTINGS.getCacheSetting('lastVersion', checksum=ADDON_VERSION) or '0.0.0'):
            SETTINGS.setCacheSetting('lastVersion',ADDON_VERSION, checksum=ADDON_VERSION)
            BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/utilities.py,Show_Changelog)')
        SETTINGS.setSetting('Update_Status',{'True':'[COLOR=yellow]%s Version: [B]%s[/B][/COLOR]'%(LANGUAGE(32168),ONLINE_VERSION),'False':'None'}[str(update)])


    def chkFiles(self):
        # check for missing files and run appropriate action to rebuild them only after init. startup.
        if not FileAccess.exists(LIBRARYFLEPATH): self._que(self.chkLibrary)
        if not (FileAccess.exists(CHANNELFLEPATH) & FileAccess.exists(M3UFLEPATH) & FileAccess.exists(XMLTVFLEPATH) & FileAccess.exists(GENREFLEPATH)): self._que(self.chkChannels)
        if not FileAccess.exists(LOGO_LOC):   FileAccess.makedirs(LOGO_LOC) #check logo folder
        if not FileAccess.exists(FILLER_LOC): FileAccess.makedirs(FILLER_LOC) #check fillers folder
        if not FileAccess.exists(TEMP_LOC):   FileAccess.makedirs(TEMP_LOC)


    def chkPVRRefresh(self):
        self.log('chkPVRRefresh')
        self._que(togglePVR,1,*(False,True))


    def chkFillers(self, channels=None):
        self.log('chkFillers')
        if channels is None: channels = self.getChannels()
        with DIALOG.sudo_dialog(LANGUAGE(32179)):
            [FileAccess.makedirs(os.path.join(FILLER_LOC,ftype.lower(),'')) for ftype in FILLER_TYPES if not FileAccess.exists(os.path.join(FILLER_LOC,ftype.lower(),''))]
            for citem in channels:
                for ftype in FILLER_TYPES[1:]:
                    [FileAccess.makedirs(os.path.join(FILLER_LOC,ftype.lower(),genre.lower())) for genre in self.getGenreNames() if not FileAccess.exists(os.path.join(FILLER_LOC,ftype.lower(),genre.lower(),''))]
                    if not FileAccess.exists(os.path.join(FILLER_LOC,ftype.lower(),citem.get('name','').lower())):
                        if ftype.lower() == 'adverts': IGNORE = IGNORE_CHTYPE + MOVIE_CHTYPE
                        else:                          IGNORE = IGNORE_CHTYPE
                        if citem.get('name') and not citem.get('radio',False) and citem.get('type') not in IGNORE:
                            FileAccess.makedirs(os.path.join(FILLER_LOC,ftype.lower(),citem['name'].lower()))


    def chkRecommended(self):
        try:
            library = Library(service=self.service)
            library.searchRecommended()
            del library
        except Exception as e: self.log('chkRecommended failed! %s'%(e), xbmc.LOGERROR)

        
    def chkLibrary(self, force=False):
        try: 
            library = Library(service=self.service)
            library.importPrompt()
            complete = library.updateLibrary(force)
            del library
            if   not complete: self._que(self.chkLibrary,1,True)
            elif not SETTINGS.hasAutotuned() and not force: self.runAutoTune() #run autotune for the first time this Kodi/PTVL instance.
        except Exception as e: self.log('chkLibrary failed! %s'%(e), xbmc.LOGERROR)


    def chkChannels(self):
        try:
            builder  = Builder(self.service)
            complete, updated = builder.build()
            channels = builder.verify()
            if SETTINGS.getSettingBool('Build_Filler_Folders'): self.chkFillers(channels)
            del builder
            if not complete:
                if PROPERTIES.hasFirstrun(): self._que(self.chkChannels,2)
            else: 
                self.service.currentChannels = list(channels)
                PROPERTIES.setEXTProperty('%s.has.Channels'%(ADDON_ID),str(len(self.service.currentChannels) > 0).lower())
                if updated: PROPERTIES.setEXTProperty('%s.chkPVRRefresh'%(ADDON_ID),'true')
            if not PROPERTIES.hasFirstrun(): PROPERTIES.setFirstrun(state=True)
        except Exception as e:
            self.log('chkChannels failed! %s'%(e), xbmc.LOGERROR)

                
    def chkPVRservers(self):
        self.log('chkPVRservers')
        if self.multiroom.chkPVRservers():
            PROPERTIES.setEXTProperty('%s.chkPVRRefresh'%(ADDON_ID),'true')


    def chkPVRSettings(self):
        try:
            with DIALOG.sudo_dialog(msg='%s %s'%(LANGUAGE(32028),LANGUAGE(32053))): #Kodi PVR & LiveTV Settings
                if (self.jsonRPC.getSettingValue('epg.pastdaystodisplay')   or 1) != MIN_GUIDEDAYS: SETTINGS.setSettingInt('Min_Days',min)
                if (self.jsonRPC.getSettingValue('epg.futuredaystodisplay') or 3) != MAX_GUIDEDAYS: SETTINGS.setSettingInt('Max_Days',max)
        except Exception as e: self.log('chkPVRSettings failed! %s'%(e), xbmc.LOGERROR)
         

    def chkDiscovery(self):
        self.log('chkDiscovery')
        self.multiroom.hasServers()
        timerit(self.multiroom.pairDiscovery)(1.0)


    def chkHTTP(self):
        self.log('chkHTTP')
        timerit(self.httpServer._start)(1.0)
            
            
    def chkJSONQUE(self):
        if not PROPERTIES.isRunning('chkJSONQUE'):
            with PROPERTIES.setRunning('chkJSONQUE'):
                queuePool = (SETTINGS.getCacheSetting('queuePool', json_data=True) or {})
                params = queuePool.get('params',[])
                for i in list(range(int((REAL_SETTINGS.getSetting('Page_Limit') or "25")))):
                    if   self.service._interrupt(): break
                    elif len(params) > 0:
                        param = params.pop(0)
                        self.log("chkJSONQUE, queueing = %s\n%s"%(len(params),param))
                        self._que(self.jsonRPC.sendJSON,10, param)
                queuePool['params'] = setDictLST(params)
                self.log('chkJSONQUE, remaining = %s'%(len(queuePool['params'])))
                SETTINGS.setCacheSetting('queuePool', queuePool, json_data=True)


    def runAutoTune(self):
        try:
            autotune = Autotune(service=self.service)
            complete = autotune._runTune()
            if complete: SETTINGS.setAutotuned()
            del autotune
        except Exception as e: self.log('runAutoTune failed! %s'%(e), xbmc.LOGERROR)
    
    
    @cacheit(expiration=datetime.timedelta(minutes=15),json_data=False)
    def getGenreNames(self):
        self.log('getGenres')
        try:
            library = Library(self.service)
            genres  = set([tvgenre.get('name') for tvgenre in library.getTVGenres() if tvgenre.get('name')] + [movgenre.get('name') for movgenre in library.getMovieGenres() if movgenre.get('name')])
            del library
            return list(genres)
        except Exception as e: 
            self.log('getGenres failed! %s'%(e), xbmc.LOGERROR)
            return []
    

    def getChannels(self):
        self.log('getChannels')
        try:
            builder  = Builder(self.service)
            channels = builder.verify()
            del builder
            return list(channels)
        except Exception as e: 
            self.log('getChannels failed! %s'%(e), xbmc.LOGERROR)
            return []
        

    def chkChannelChange(self, channels=[]):
        with DIALOG.sudo_dialog(msg='%s %ss'%(LANGUAGE(32028),LANGUAGE(32023))):
            nChannels = self.getChannels()
            if channels != nChannels:
                self.log('chkChannelChange, resetting chkChannels')
                self._que(self.chkChannels)
                return nChannels
            return channels

        
    def chkSettingsChange(self, settings={}):
        self.log('chkSettingsChange, settings = %s'%(settings))
        with DIALOG.sudo_dialog(msg='%s %s'%(LANGUAGE(32028),LANGUAGE(32053))):
            nSettings = dict(SETTINGS.getCurrentSettings())
            for setting, value in list(settings.items()):
                actions = {'User_Folder'     :{'func':self.setUserPath  ,'kwargs':{'old':value,'new':nSettings.get(setting)}},
                           'UDP_PORT'        :{'func':setPendingRestart},
                           'TCP_PORT'        :{'func':setPendingRestart},
                           'Disable_Cache'   :{'func':setPendingRestart},
                           'Disable_Trakt'   :{'func':setPendingRestart},
                           'Rollback_Watched':{'func':setPendingRestart}}
                           
                if nSettings.get(setting) != value and actions.get(setting):
                    action = actions.get(setting)
                    self.log('chkSettingsChange, detected change in %s - from: %s to: %s\naction = %s'%(setting,value,nSettings.get(setting),action))
                    self._que(action.get('func'),1,*action.get('args',()),**action.get('kwargs',{}))
            return nSettings


    def setUserPath(self, old, new, overwrite=False):
        with PROPERTIES.suspendActivity():
            self.log('setUserPath, old = %s, new = %s'%(old,new))
            dia = DIALOG.progressDialog(message='%s\n%s'%(LANGUAGE(32050),old))
            with BUILTIN.busy_dialog(isPlaying=BUILTIN.getInfoBool('Playing','Player')):
                fileItems = self.jsonRPC.walkListDirectory(old, depth=-1, appendPath=True)
            
            cnt = 0
            for dir, files in list(fileItems.items()):
                ndir = dir.replace(old,new)
                dia  = DIALOG.progressDialog(int(((cnt)*100)//len(list(fileItems.keys()))), dia, message='%s\n%s'%(LANGUAGE(32051),ndir))
                if ndir and not FileAccess.exists(os.path.join(ndir,'')):
                    if not FileAccess.makedirs(os.path.join(ndir,'')): continue
                    
                pnt = 0
                for idx, file in enumerate(files):
                    pnt = int(((idx)*100)//len(files))
                    nfile = file.replace(old,new)
                    if FileAccess.exists(nfile) and not overwrite:
                        retval = DIALOG.yesnoDialog((LANGUAGE(30120)%nfile),customlabel='Overwrite All')
                        if retval in [1,2]: FileAccess.delete(nfile)
                        else: continue
                        if retval == 2: overwrite = True
                    if FileAccess.copy(file,nfile): dia = DIALOG.progressDialog(pnt, dia, message='%s\n%s\n%s'%(LANGUAGE(32051),ndir,nfile))
                    else:                           dia = DIALOG.progressDialog(pnt, dia, message=LANGUAGE(32052)%(nfile))
            DIALOG.progressDialog(100, dia)
            SETTINGS.setPVRPath(new,prompt=True,force=True)
            setPendingRestart()
            
        