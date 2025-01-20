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
        self.quePriority = CustomQueue(priority=True,service=service)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _que(self, func, priority=-1, *args, **kwargs):# priority -1 autostack, 1 Highest, 5 Lowest
        if priority == -1: priority = self.quePriority.qsize + 1
        self.log('_que, priority = %s, func = %s, args = %s, kwargs = %s' % (priority,func.__name__, args, kwargs))
        self.quePriority._push((func, args, kwargs), priority)
        

    def _initialize(self, sleep=FIFTEEN):
        tasks = [self.chkInstanceID,
                 self.chkDirs,
                 self.chkWelcome,
                 self.chkDebugging,
                 self.chkBackup,
                 self.chkServers,
                 self.chkPVRBackend]
                 
        DIALOG.notificationWait(LANGUAGE(32054),wait=sleep)
        for func in tasks: self._que(func)
        self.log('_initialize, finished...')
        
        
    def chkInstanceID(self):
        self.log('chkInstanceID')
        PROPERTIES.getInstanceID()
        

    @cacheit(expiration=datetime.timedelta(days=28), checksum=1)
    def chkWelcome(self):
        self.log('chkWelcome')
        return BUILTIN.executebuiltin('RunScript(special://home/addons/%s/resources/lib/utilities.py, Show_Wiki_QR)'%(ADDON_ID))
        

    def chkDebugging(self):
        self.log('chkDebugging')
        if SETTINGS.getSettingBool('Debug_Enable'):
            if DIALOG.yesnoDialog(LANGUAGE(32142),autoclose=4):
                self.log('_chkDebugging, disabling debugging.')
                SETTINGS.setSettingBool('Debug_Enable',False)
                DIALOG.notificationDialog(LANGUAGE(321423))
        # self.jsonRPC.setSettingValue("debug.showloginfo",SETTINGS.getSettingBool('Debug_Enable'))


    def chkBackup(self):
        self.log('chkBackup')
        Backup().hasBackup()


    def chkServers(self):
        self.log('chkServers')
        Multiroom(service=self.service).chkServers()


    def chkPVRBackend(self): 
        self.log('chkPVRBackend')
        if hasAddon(PVR_CLIENT_ID,True,True,True,True):
            if not SETTINGS.hasPVRInstance():
                SETTINGS.setPVRPath(USER_LOC, SETTINGS.getFriendlyName())
              

    def _chkQueTimer(self):
        self.log('_chkQueTimer')
        self._chkEpochTimer('chkVersion'      , self.chkVersion      , 21600)
        self._chkEpochTimer('chkKodiSettings' , self.chkKodiSettings , 900)
        self._chkEpochTimer('chkHTTP'         , self.chkHTTP         , 900)
        self._chkEpochTimer('chkDiscovery'    , self.chkDiscovery    , 300)
        self._chkEpochTimer('chkRecommended'  , self.chkRecommended  , 900)
        self._chkEpochTimer('chkLibrary'      , self.chkLibrary      , 900)
        self._chkEpochTimer('chkChannels'     , self.chkChannels     , (MAX_GUIDEDAYS*3600))
        self._chkEpochTimer('chkJSONQUE'      , self.chkJSONQUE      , 300)
        self._chkEpochTimer('chkFiles'        , self.chkFiles        , 300)
        
        self._chkPropTimer('chkPVRRefresh'    , self.chkPVRRefresh   , 1)
        self._chkPropTimer('chkFillers'       , self.chkFillers      , 2)
        self._chkPropTimer('chkAutoTune'      , self.chkAutoTune     , 2)
                  
        
    def _chkEpochTimer(self, key, func, runevery, nextrun=None, *args, **kwargs):
        if nextrun is None: nextrun = PROPERTIES.getPropertyInt(key,default=0)# nextrun == 0 => force que
        epoch = int(time.time())
        if epoch >= nextrun:
            self.log('_chkEpochTimer, key = %s'%(key))
            PROPERTIES.setPropertyInt(key,(epoch+runevery))
            return self._que(func, -1, *args, **kwargs)
        

    def _chkPropTimer(self, key, func, priority=-1, *args, **kwargs):
        key = '%s.%s'%(ADDON_ID,key)
        if PROPERTIES.getEXTPropertyBool(key):
            self.log('_chkPropTimer, key = %s'%(key))
            PROPERTIES.clrEXTProperty(key)
            self._que(func, priority , *args, **kwargs)
            

    @cacheit(expiration=datetime.timedelta(minutes=10))
    def getOnlineVersion(self):
        try:    ONLINE_VERSON = re.compile('" version="(.+?)" name="%s"'%(ADDON_NAME)).findall(str(requestURL(ADDON_URL)))[0]
        except: ONLINE_VERSON = ADDON_VERSION
        self.log('getOnlineVersion, ONLINE_VERSON = %s'%(ONLINE_VERSON))
        return ONLINE_VERSON
        
        
    def chkVersion(self):
        self.log('chkVersion')
        update = False
        ONLINE_VERSION = self.getOnlineVersion()
        if ADDON_VERSION < ONLINE_VERSION: 
            update = True
            DIALOG.notificationDialog(LANGUAGE(30073)%(LANGUAGE(32168),ONLINE_VERSION))
        elif ADDON_VERSION > (SETTINGS.getCacheSetting('lastVersion', checksum=ADDON_VERSION) or '0.0.0'):
            SETTINGS.setCacheSetting('lastVersion',ADDON_VERSION, checksum=ADDON_VERSION)
            BUILTIN.executebuiltin('RunScript(special://home/addons/%s/resources/lib/utilities.py,Show_Changelog)'%(ADDON_ID))
        SETTINGS.setSetting('Update_Status',{'True':'[COLOR=yellow]%s Version: [B]%s[/B][/COLOR]'%(LANGUAGE(32168),ONLINE_VERSION),'False':'None'}[str(update)])


    def chkKodiSettings(self):
        self.log('chkKodiSettings')
        MIN_GUIDEDAYS = SETTINGS.setSettingInt('Min_Days' ,self.jsonRPC.getSettingValue('epg.pastdaystodisplay'     ,default=1))
        MAX_GUIDEDAYS = SETTINGS.setSettingInt('Max_Days' ,self.jsonRPC.getSettingValue('epg.futuredaystodisplay'   ,default=3))
        OSD_TIMER     = SETTINGS.setSettingInt('OSD_Timer',self.jsonRPC.getSettingValue('pvrmenu.displaychannelinfo',default=5))
         

    def chkDirs(self):
        self.log('chkDirs')
        [FileAccess.makedirs(folder) for folder in [LOGO_LOC,FILLER_LOC,TEMP_LOC] if not FileAccess.exists(os.path.join(folder,''))]


    def chkFiles(self):
        self.log('chkFiles')
        self.chkDirs()
        if not FileAccess.exists(LIBRARYFLEPATH): self._que(self.chkLibrary,2)
        if not (FileAccess.exists(CHANNELFLEPATH) & FileAccess.exists(M3UFLEPATH) & FileAccess.exists(XMLTVFLEPATH) & FileAccess.exists(GENREFLEPATH)): self._que(self.chkChannels,3)


    def chkHTTP(self):
        self.log('chkHTTP')
        timerit(self.httpServer._start)(1.0)
              

    def chkDiscovery(self):
        self.log('chkDiscovery')
        timerit(Multiroom(service=self.service)._chkDiscovery)(1.0)
        
            
    def chkRecommended(self):
        self.log('chkRecommended')
        try:
            library = Library(service=self.service)
            library.searchRecommended()
            del library
        except Exception as e: self.log('chkRecommended failed! %s'%(e), xbmc.LOGERROR)

        
    def chkLibrary(self, force=PROPERTIES.getPropertyBool('ForceLibrary')):
        self.log('chkLibrary, force = %s'%(force))
        try: 
            library = Library(service=self.service)
            library.importPrompt()
            complete = library.updateLibrary(force)
            del library
            if complete: 
                if force: PROPERTIES.setPropertyBool('ForceLibrary',False)
                self.chkAutoTune() #run autotune for the first time this Kodi/PTVL instance.
            else: self._que(self.chkLibrary,2,force)
        except Exception as e: self.log('chkLibrary failed! %s'%(e), xbmc.LOGERROR)


    def chkChannels(self, channels: list=[]):
        try:
            if not channels:
                ids = SETTINGS.getUpdateChannels()
                if ids:
                    channels = self.getChannels()
                    channels = [citem for id in ids for citem in channels if citem.get('id') == id]
                else:
                    channels = self.getChannels()
                    SETTINGS.setSetting('Select_Channels','[B]%s[/B] Channels'%(len(channels)))
                    PROPERTIES.setChannels(len(channels) > 0)
                    self.service.currentChannels = channels #update service channels
                    
            if len(channels) > 0:
                complete, updated = Builder(self.service).build(channels)
                self.log('chkChannels, channels = %s, complete = %s, updated = %s'%(len(channels),complete,updated))
                if complete:
                    if updated: PROPERTIES.setPropTimer('chkPVRRefresh')
                    if SETTINGS.getSettingBool('Build_Filler_Folders'): self._que(self.chkFillers,-1,channels)
                else: self._que(self.chkChannels,3,channels)
        except Exception as e:
            self.log('chkChannels failed! %s'%(e), xbmc.LOGERROR)


    def chkJSONQUE(self):
        if not PROPERTIES.isRunning('chkJSONQUE'):
            with PROPERTIES.setRunning('chkJSONQUE'):
                queuePool = (SETTINGS.getCacheSetting('queuePool', json_data=True) or {})
                params = queuePool.get('params',[])
                for i in list(range(SETTINGS.getSettingInt('Page_Limit'))):
                    if   self.service._interrupt(): break
                    elif len(params) > 0:
                        param = params.pop(0)
                        self.log("chkJSONQUE, queueing = %s\n%s"%(len(params),param))
                        self._que(self.jsonRPC.sendJSON,-1, param)
                queuePool['params'] = setDictLST(params)
                self.log('chkJSONQUE, remaining = %s'%(len(queuePool['params'])))
                SETTINGS.setCacheSetting('queuePool', queuePool, json_data=True)


    def chkPVRRefresh(self):
        self.log('chkPVRRefresh')
        timerit(self._que)(FIFTEEN,[self.chkPVRToggle,1])


    def chkPVRToggle(self):
        isIdle      = self.service.monitor.isIdle
        isPlaying   = self.service.player.isPlaying()
        isScanning  = BUILTIN.getInfoBool('IsScanningVideo','Library')
        isRecording = BUILTIN.getInfoBool('IsRecording','Pvr')
        self.log('chkPVRToggle, isIdle = %s, isPlaying = %s'%(isIdle,isPlaying))
        if isIdle and not (isPlaying | isScanning | isRecording): togglePVR(False,True)
        else: PROPERTIES.setPropTimer('chkPVRRefresh')


    def chkFillers(self, channels=None):
        self.log('chkFillers')
        if channels is None: channels = self.getChannels()
        pDialog = DIALOG.progressBGDialog(header='%s, %s'%(ADDON_NAME,LANGUAGE(32179)))
        for idx, ftype in enumerate(FILLER_TYPES):
            if not FileAccess.exists(os.path.join(FILLER_LOC,ftype.lower(),'')): 
                pDialog = DIALOG.progressBGDialog(int(idx*50//len(ftype)), pDialog, message='%s: %s'%(ftype,int(idx*100//len(ftype)))+'%', header='%s, %s'%(ADDON_NAME,LANGUAGE(32179)))
                FileAccess.makedirs(os.path.join(FILLER_LOC,ftype.lower(),''))
        
        genres = self.getGenreNames()
        for idx, citem in enumerate(channels):
            for ftype in FILLER_TYPES[1:]:
                for genre in genres:
                    if not FileAccess.exists(os.path.join(FILLER_LOC,ftype.lower(),genre.lower(),'')):
                        pDialog = DIALOG.progressBGDialog(int(idx*50//len(channels)), pDialog, message='%s: %s'%(genre,int(idx*100//len(channels)))+'%', header='%s, %s'%(ADDON_NAME,LANGUAGE(32179)))
                        FileAccess.makedirs(os.path.join(FILLER_LOC,ftype.lower(),genre.lower()))
                
                if not FileAccess.exists(os.path.join(FILLER_LOC,ftype.lower(),citem.get('name','').lower())):
                    if ftype.lower() == 'adverts': IGNORE = IGNORE_CHTYPE + MOVIE_CHTYPE
                    else:                          IGNORE = IGNORE_CHTYPE
                    if citem.get('name') and not citem.get('radio',False) and citem.get('type') not in IGNORE: 
                        pDialog = DIALOG.progressBGDialog(int(idx*50//len(channels)), pDialog, message='%s: %s'%(citem.get('name'),int(idx*100//len(channels)))+'%', header='%s, %s'%(ADDON_NAME,LANGUAGE(32179)))
                        FileAccess.makedirs(os.path.join(FILLER_LOC,ftype.lower(),citem['name'].lower()))
        pDialog = DIALOG.progressBGDialog(100, pDialog, message=LANGUAGE(32025), header='%s, %s'%(ADDON_NAME,LANGUAGE(32179)))
    

    def chkAutoTune(self):
        self.log('chkAutoTune')
        try: SETTINGS.setAutotuned(Autotune(service=self.service)._runTune())
        except Exception as e: self.log('chkAutoTune failed! %s'%(e), xbmc.LOGERROR)
    
    
    @cacheit(expiration=datetime.timedelta(minutes=15),json_data=False)
    def getGenreNames(self):
        self.log('getGenres')
        try:
            library     = Library(self.service)
            tvgenres    = library.getTVGenres()
            moviegenres = library.getMovieGenres()
            genres  = set([tvgenre.get('name') for tvgenre in tvgenres if tvgenre.get('name')] + [movgenre.get('name') for movgenre in moviegenres if movgenre.get('name')])
            del library
            return list(genres)
        except Exception as e: 
            self.log('getGenres failed! %s'%(e), xbmc.LOGERROR)
            return []
    

    def getChannels(self):
        try:
            channels = Builder(self.service).getChannels()
            self.log('getChannels, channels = %s'%(len(channels)))
            return channels
        except Exception as e: 
            self.log('getChannels failed! %s'%(e), xbmc.LOGERROR)
            return []
        

    def chkChannelChange(self, channels=[]):
        nChannels = self.getChannels()
        if channels != nChannels:
            self.log('chkChannelChange, channels changed %s => %s: queueing chkChannels'%(len(channels),len(nChannels)))
            self._que(self.chkChannels,3,diffLSTDICT(channels,nChannels))
            return nChannels
        return channels

        
    def chkSettingsChange(self, settings={}):
        self.log('chkSettingsChange, settings = %s'%(settings))
        nSettings = dict(SETTINGS.getCurrentSettings())
        for setting, value in list(settings.items()):
            actions = {'User_Folder':{'func':self.setUserPath,'kwargs':{'old':value,'new':nSettings.get(setting)}}}
            if nSettings.get(setting) != value and actions.get(setting):
                action = actions.get(setting)
                self.log('chkSettingsChange, detected change in %s - from: %s to: %s\naction = %s'%(setting,value,nSettings.get(setting),action))
                self._que(action.get('func'),1,*action.get('args',()),**action.get('kwargs',{}))
        return nSettings


    def setUserPath(self, old, new):
        with PROPERTIES.interruptActivity():
            self.log('setUserPath, old = %s, new = %s'%(old,new))
            dia = DIALOG.progressDialog(message='%s\n%s'%(LANGUAGE(32050),old))
            FileAccess.copyFolder(old, new, dia)
            SETTINGS.setPVRPath(new,prompt=True,force=True)
            PROPERTIES.setPendingRestart()
            DIALOG.progressDialog(100, dia)