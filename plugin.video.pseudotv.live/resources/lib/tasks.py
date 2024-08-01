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
        self.service     = service
        self.jsonRPC     = service.jsonRPC
        self.cache       = service.jsonRPC.cache
        self.httpServer  = HTTP(service.monitor)
        self.quePriority = CustomQueue(priority=True,service=self.service)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _que(self, func, priority=-1, *args, **kwargs):# priority -1 autostack, 1 Highest, 5 Lowest
        if priority == -1: priority = self.quePriority.qsize + 1
        self.log('_que, priority = %s, func = %s, args = %s, kwargs = %s' % (priority,func.__name__, args, kwargs))
        self.quePriority._push((func,args,kwargs),priority)
        

    def _initialize(self):
        setInstanceID()
        isClient(silent=False)
        tasks = [self.chkWelcome,
                 self.chkVersion,
                 self.chkDebugging,
                 self.chkBackup,
                 self.chkPVRBackend]
        [self._que(func) for func in tasks if not self.service._interrupt()]
        self.log('_initialize, finished...')
        

    def chkWelcome(self):
        self.log('chkWelcome')
        BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/utilities.py,Show_Welcome)')
              
                  
    @cacheit(checksum=getInstanceID())
    def getOnlineVersion(self):
        try:    ONLINE_VERSON = re.compile('" version="(.+?)" name="%s"'%(ADDON_NAME)).findall(str(urllib.request.urlopen(ADDON_URL).read()))[0]
        except: ONLINE_VERSON = ADDON_VERSION
        self.log('getOnlineVersion, ONLINE_VERSON = %s'%(ONLINE_VERSON))
        return ONLINE_VERSON
        
        
    def chkVersion(self):
        self.log('chkVersion')
        ONLINE_VERSION = self.getOnlineVersion()
        if ADDON_VERSION < ONLINE_VERSION: DIALOG.notificationDialog('%s\n%s'%(LANGUAGE(32168),'Version (%s)'%(ONLINE_VERSION)))
        if ADDON_VERSION != (SETTINGS.getCacheSetting('lastVersion') or 'v.0.0.0'):
            SETTINGS.setCacheSetting('lastVersion',ADDON_VERSION)
            BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/utilities.py,Show_Changelog)')


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
        if hasAddon(PVR_CLIENT_ID,install=True,enable=True):
            if SETTINGS.chkPVRInstance('special://profile/addon_data/%s'%(PVR_CLIENT_ID)) == False:
                with busy_dialog():
                    if SETTINGS.chkPluginSettings(PVR_CLIENT_ID,IPTV_SIMPLE_SETTINGS(),override=True):
                        DIALOG.notificationDialog(LANGUAGE(32152))
                    else: 
                        DIALOG.notificationDialog(LANGUAGE(32046))
        
        
    def chkUpdateTime(self, key: str, runEvery: int, nextUpdate=None) -> bool:
        #schedule updates, first boot always forces run!
        if nextUpdate is None: nextUpdate = (PROPERTIES.getPropertyInt(key) or 0)
        epoch = int(time.time())
        if (epoch >= nextUpdate) and not self.service._suspend():
            PROPERTIES.setPropertyInt(key,(epoch+runEvery))
            return True
        return False

                     
    def chkQueTimer(self):
        if self.chkUpdateTime('chkQueTimer',runEvery=30):
            self._que(self._chkQueTimer)
        
        
    def _chkQueTimer(self, client=isClient()):
        self.log('chkQueTimer, client = %s'%(client))
        if self.chkUpdateTime('chkFiles',runEvery=600) and not client:
            self._que(self.chkFiles)
        if self.chkUpdateTime('chkRecommended',runEvery=900) and not client:
            self._que(self.chkRecommended)
        if self.chkUpdateTime('chkLibrary',runEvery=(MAX_GUIDEDAYS*3600)):
            self._que(self.chkLibrary)
        if self.chkUpdateTime('chkChannels',runEvery=(MAX_GUIDEDAYS*3600)) and not client:
            self._que(self.chkChannels)
        if self.chkUpdateTime('chkPVRSettings',runEvery=(MAX_GUIDEDAYS*3600)) and not client:
            self._que(self.chkPVRSettings)
        if self.chkUpdateTime('chkHTTP',runEvery=900) and not client:
            self._que(self.chkHTTP)
        if self.chkUpdateTime('chkJSONQUE',runEvery=300):
            self._que(self.chkJSONQUE)
                          

    def chkFiles(self):
        self.log('_chkFiles')
        # check for missing files and run appropriate action to rebuild them only after init. startup.
        if hasFirstrun():
            if not FileAccess.exists(LIBRARYFLEPATH): self._que(self.chkLibrary)
            if not (FileAccess.exists(CHANNELFLEPATH) & FileAccess.exists(M3UFLEPATH) & FileAccess.exists(XMLTVFLEPATH) & FileAccess.exists(GENREFLEPATH)):
                self._que(self.chkChannels)


    def chkRecommended(self):
        try:
            library = Library(service=self.service)
            library.searchRecommended()
            del library
        except Exception as e: self.log('chkRecommended failed! %s'%(e), xbmc.LOGERROR)

        
    def chkLibrary(self):
        try: 
            library = Library(service=self.service)
            library.importPrompt()
            complete = library.updateLibrary()
            del library
            if   not complete: self._que(self.chkLibrary)
            elif not hasAutotuned(): self.runAutoTune() #run autotune for the first time this Kodi/PTVL instance.
        except Exception as e: self.log('chkLibrary failed! %s'%(e), xbmc.LOGERROR)


    def chkChannels(self):
        try:
            builder  = Builder(self.service)
            complete = builder.build()
            channels = builder.verify()
            del builder
            if complete:
                if not hasFirstrun(): setFirstrun(state=True)
                self.service.currentChannels = list(channels)
            else: self._que(self.chkChannels)
        except Exception as e:
            self.log('chkChannels failed! %s'%(e), xbmc.LOGERROR)
               

    def chkPVRSettings(self):
        try:
            # with sudo_dialog(msg='%s %s'%(LANGUAGE(32028),LANGUAGE(30069))):
            if (self.jsonRPC.getSettingValue('epg.pastdaystodisplay')   or 1) != MIN_GUIDEDAYS:
                SETTINGS.setSettingInt('Min_Days',min)
                
            if (self.jsonRPC.getSettingValue('epg.futuredaystodisplay') or 3) != MAX_GUIDEDAYS:
                SETTINGS.setSettingInt('Max_Days',max)
        except Exception as e: self.log('chkPVRSettings failed! %s'%(e), xbmc.LOGERROR)
         
         
    def chkHTTP(self):
        self.log('chkHTTP')
        self.httpServer._start()
            
            
    def chkJSONQUE(self):
        if not isRunning('chkJSONQUE'):
            with setRunning('chkJSONQUE'):
                queuePool = (SETTINGS.getCacheSetting('queuePool', json_data=True) or {})
                params = queuePool.get('params',[])
                for param in (list(chunkLst(params,int((REAL_SETTINGS.getSetting('Page_Limit') or "25")))) or [[]])[0]:
                    if   self.service._interrupt(): break
                    elif len(params) > 0: self._que(self.jsonRPC.sendJSON,10,params.pop(0))
                queuePool['params'] = setDictLST(params)
                self.log('chkJSONQUE, remaining = %s'%(len(queuePool['params'])))
                SETTINGS.setCacheSetting('queuePool', queuePool, json_data=True)


    def runAutoTune(self):
        try:
            autotune = Autotune(service=self.service)
            complete = autotune._runTune()
            if complete: setAutotuned()
            del autotune
        except Exception as e: self.log('runAutoTune failed! %s'%(e), xbmc.LOGERROR)
    

    def getChannels(self):
        self.log('getChannels')
        try:
            if isClient(): return []
            builder  = Builder(self.service)
            channels = builder.verify()
            del builder
            return list(channels)
        except Exception as e: 
            self.log('getChannels failed! %s'%(e), xbmc.LOGERROR)
            return []
        

    def chkChannelChange(self, channels=[]):
        if isClient(): return channels
        # with sudo_dialog(msg='%s %ss'%(LANGUAGE(32028),LANGUAGE(32023))):
        nChannels = self.getChannels()
        if channels != nChannels:
            self.log('chkChannelChange, resetting chkChannels')
            self._que(self.chkChannels)
            return nChannels
        return channels

        
    def chkSettingsChange(self, settings=[]):
        self.log('chkSettingsChange')
        # with sudo_dialog(msg='%s %s'%(LANGUAGE(32028),LANGUAGE(32053))):
        nSettings = dict(SETTINGS.getCurrentSettings())
        for setting, value in list(settings.items()):
            actions = {'User_Folder'    :{'func':self.setUserPath      ,'kwargs':{'userFolders':nSettings.get(setting)}},
                       'Network_Folder' :{'func':self.setPVRPath   ,'kwargs':{'userFolder':nSettings.get(setting)}},
                       'Remote_URL'     :{'func':self.setPVRRemote ,'kwargs':{'userURL':nSettings.get(setting)}},
                       'UDP_PORT'       :{'func':setPendingRestart},
                       'TCP_PORT'       :{'func':setPendingRestart},
                       'Client_Mode'    :{'func':setPendingRestart},
                       'Disable_Cache'  :{'func':setPendingRestart}}
                       
            if nSettings.get(setting) != value and actions.get(setting):
                # with sudo_dialog(LANGUAGE(32157)):
                self.log('chkSettingsChange, detected change in %s - from: %s to: %s'%(setting,value,nSettings.get(setting)))
                self._que(actions[setting].get('func'),2,*actions[settings].get('args',()),**actions[setting].get('kwargs',{}))
        return nSettings


    def setUserPath(self, userFolders):
        oldFolder, newFolder = userFolders
        self.log('setUserPath, oldFolder = %s, newFolder = %s, isClient = %s'%(oldFolder,newFolder,isClient()))
        if not isClient():
            files = [M3UFLE,XMLTVFLE,GENREFLE,LIBRARYFLE,CHANNELFLE]
            dia   = DIALOG.progressDialog(message=LANGUAGE(32050))
            FileAccess.move(os.path.join(oldFolder,'logos'),os.path.join(newFolder,'logos'))
            for idx, file in enumerate(files):
                pnt = int(((idx+1)*100)//len(files))
                dia = DIALOG.progressDialog(pnt, dia, message='%s: %s'%(LANGUAGE(32051),file))
                oldFilePath = os.path.join(oldFolder,file)
                newFilePath = os.path.join(newFolder,file)
                bakFilePath = os.path.join(newFolder,'%s.bak'%(file))
                if FileAccess.exists(oldFilePath):
                    dia = DIALOG.progressDialog(pnt, dia, message='%s: %s'%(LANGUAGE(32051),file))
                    if FileAccess.exists(newFilePath):
                        if DIALOG.yesnoDialog((LANGUAGE(30120)%newFilePath)):
                            dia = DIALOG.progressDialog(pnt, dia, message='%s: %s'%(LANGUAGE(32151),os.path.join(newFolder,'%s.bak'%(file))))
                            if FileAccess.copy(newFilePath,bakFilePath): #backup existing file.
                                dia = DIALOG.progressDialog(pnt, dia, message='%s: %s\n%s'%(LANGUAGE(32151),bakFilePath,LANGUAGE(32025)))
                        else: continue
                    if FileAccess.move(oldFilePath,newFilePath):
                        dia = DIALOG.progressDialog(pnt, dia, message='%s: %s\n%s'%(LANGUAGE(32051),file,LANGUAGE(32025)))
                        continue
                dia = DIALOG.progressDialog(pnt, dia, message=LANGUAGE(32052)%(file))
        self.setPVRPath(newFolder)
        
        
    def setPVRPath(self, userFolder):
        self.log('setPVRPath, userFolder = %s'%(userFolder)) #set local pvr folder
        SETTINGS.setSetting('User_Folder' ,userFolder)
        SETTINGS.setSetting('Remote_M3U'  ,'%s'%(os.path.join(userFolder,  M3UFLE).replace('special://profile/addon_data','/addon_data')))
        SETTINGS.setSetting('Remote_XMLTV','%s'%(os.path.join(userFolder,XMLTVFLE).replace('special://profile/addon_data','/addon_data')))
        SETTINGS.setSetting('Remote_GENRE','%s'%(os.path.join(userFolder,GENREFLE).replace('special://profile/addon_data','/addon_data')))
        
        Client_Mode = SETTINGS.getSettingInt('Client_Mode')
        newSettings = {'m3uPathType'   :'%s'%('1' if Client_Mode == 1 else '0'),
                       'm3uPath'       :os.path.join(userFolder,M3UFLE),
                       'epgPathType'   :'%s'%('1' if Client_Mode == 1 else '0'),
                       'epgPath'       :os.path.join(userFolder,XMLTVFLE),
                       'genresPathType':'%s'%('1' if Client_Mode == 1 else '0'),
                       'genresPath'    :os.path.join(userFolder,GENREFLE)}
        SETTINGS.chkPluginSettings(PVR_CLIENT_ID,newSettings,prompt=False)
        setPendingRestart()
        
        
    def setPVRRemote(self, userURL):
        self.log('setPVRRemote, userURL = %s'%(userURL)) #set remote pvr url
        SETTINGS.setSetting('Remote_URL'  ,userURL)
        SETTINGS.setSetting('Remote_M3U'  ,'%s/%s'%(userURL,M3UFLE))
        SETTINGS.setSetting('Remote_XMLTV','%s/%s'%(userURL,XMLTVFLE))
        SETTINGS.setSetting('Remote_GENRE','%s/%s'%(userURL,GENREFLE))
        
        Client_Mode = SETTINGS.getSettingInt('Client_Mode')
        newSettings = {'m3uPathType'   :'%s'%('1' if Client_Mode == 1 else '0'),
                       'm3uUrl'        :SETTINGS.getSetting('Remote_M3U'),
                       'epgPathType'   :'%s'%('1' if Client_Mode == 1 else '0'),
                       'epgUrl'        :SETTINGS.getSetting('Remote_XMLTV'),
                       'genresPathType':'%s'%('1' if Client_Mode == 1 else '0'),
                       'genresUrl'     :SETTINGS.getSetting('Remote_GENRE')}
        SETTINGS.chkPluginSettings(PVR_CLIENT_ID,newSettings,prompt=False)
        setPendingRestart()
