#   Copyright (C) 2022 Lunatixz
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
from jsonrpc    import JSONRPC
from autotune   import Autotune
from builder    import Builder
from backup     import Backup
from multiroom  import Multiroom

PAGE_LIMIT = int((REAL_SETTINGS.getSetting('Page_Limit') or "25"))

class Tasks():
    queueRunning      = False
    backgroundRunning = False
    

    def __init__(self):
        self.log('__init__')


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _startProcess(self):
        #first processes before service loop starts. Only runs once per instance.
        setInstanceID()
        setClient(isClient(),silent=False)
        self.chkWelcome()
        self.chkVersion()
        self.chkDebugging()
        
        self.chkBackup()
        self.chkLowPower()
        self.chkPVRBackend()
        self.chkMultiroom()
        
        
    def chkMultiroom(self):
        self.log('chkMultiroom')
        Multiroom(monitor=self.myService.monitor)
        
        
    def chkBackup(self):
        self.log('chkBackup')
        Backup().hasBackup()
        
        
    def chkLowPower(self):
        self.log('chkLowPower')
        setLowPower(state=getLowPower())
        

    def chkQueTimer(self):
        self.log('chkQueTimer')
        if self.chkUpdateTime('chkFiles',runEvery=600):
            self.myService._que(self.chkFiles,1)
        if self.chkUpdateTime('chkPVRSettings',runEvery=(MAX_GUIDEDAYS*3600)):
            self.myService._que(self.chkPVRSettings,1)
        if self.chkUpdateTime('chkRecommended',runEvery=900):
            self.myService._que(self.chkRecommended,2)
        if self.chkUpdateTime('chkLibrary',runEvery=(MAX_GUIDEDAYS*3600)):
            self.myService._que(self.chkLibrary,2)
        if self.chkUpdateTime('chkChannels',runEvery=(MAX_GUIDEDAYS*3600)):
            self.myService._que(self.chkChannels,3)
        if self.chkUpdateTime('chkJSONQUE',runEvery=600):
            self.myService._que(self.chkJSONQUE,4)
              
              
    def chkWelcome(self):
        self.log('chkWelcome')
        BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/utilities.py,Show_Welcome)')
              
              
    def chkVersion(self):
        self.log('chkVersion')
        if ADDON_VERSION != SETTINGS.getCacheSetting('lastVersion', default='v.0.0.0'):
            #todo check kodi repo addon.xml version number, prompt user if outdated.
            SETTINGS.setCacheSetting('lastVersion',ADDON_VERSION)
            BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/utilities.py,Show_Changelog)')


    def chkDebugging(self):
        self.log('chkDebugging')
        if SETTINGS.getSettingBool('Enable_Debugging'):
            if DIALOG.yesnoDialog(LANGUAGE(32142),autoclose=5):
                self.log('_chkDebugging, disabling debugging.')
                SETTINGS.setSettingBool('Enable_Debugging',False)
                DIALOG.notificationDialog(LANGUAGE(321423))


    def chkPVRBackend(self): 
        self.log('chkPVRBackend')
        if hasAddon(PVR_CLIENT_ID,install=True,enable=True) and not SETTINGS.chkPVRInstance('special://profile/addon_data/%s'%(PVR_CLIENT_ID)):
            with busy_dialog():
                if SETTINGS.chkPluginSettings(PVR_CLIENT_ID,IPTV_SIMPLE_SETTINGS(),override=True):
                    DIALOG.notificationDialog(LANGUAGE(32152))
                else:
                    DIALOG.notificationDialog(LANGUAGE(32046))
        
     
    def chkUpdateTime(self, key, runEvery, nextUpdate=None):
        #schedule updates, first boot always forces run!
        if nextUpdate is None: nextUpdate = (PROPERTIES.getPropertyInt(key) or 0)
        epoch = int(time.time())
        if (epoch >= nextUpdate) and not self.myService._suspend():
            PROPERTIES.setPropertyInt(key,(epoch+runEvery))
            return True
        return False


    def chkPVRSettings(self):
        try:
            if isClient(): return
            with sudo_dialog(msg='%s %s'%(LANGUAGE(32028),LANGUAGE(30069))):
                jsonRPC = JSONRPC()
                if (jsonRPC.getSettingValue('epg.pastdaystodisplay')   or 1) != MIN_GUIDEDAYS:
                    SETTINGS.setSettingInt('Min_Days',min)
                    
                if (jsonRPC.getSettingValue('epg.futuredaystodisplay') or 3) != MAX_GUIDEDAYS:
                    SETTINGS.setSettingInt('Max_Days',max)

                PROPERTIES.setPropertyBool('hasPVRSource',jsonRPC.hasPVRSource())
                del jsonRPC
        except Exception as e: self.log('chkPVRSettings failed! %s'%(e), xbmc.LOGERROR)
         

    def chkLibrary(self):
        try: 
            library = Library(service=self.myService)
            library.importPrompt()
            complete = library.updateLibrary()
            del library
            if not complete: forceUpdateTime('chkLibrary')
            elif not hasAutotuned(): self.runAutoTune() #run autotune for the first time this Kodi/PTVL instance.
        except Exception as e: self.log('chkLibrary failed! %s'%(e), xbmc.LOGERROR)

    
    def chkRecommended(self):
        try:
            if isClient(): return
            else:
                library = Library(service=self.myService)
                library.searchRecommended()
                del library
        except Exception as e: self.log('chkRecommended failed! %s'%(e), xbmc.LOGERROR)

        
    def chkChannels(self):
        try:
            if isClient(): return
            builder  = Builder(self.myService)
            complete = builder.build()
            channels = builder.verify()
            del builder
            if complete:
                setFirstrun(state=True) #set init. boot status to true.
                self.myService.currentChannels = list(channels)
            else: forceUpdateTime('chkChannels')
        except Exception as e: self.log('chkChannels failed! %s'%(e), xbmc.LOGERROR)
               
               
    def chkFiles(self):
        self.log('_chkFiles')
        # check for missing files and run appropriate action to rebuild them only after init. startup.
        if hasFirstrun() and not isClient():
            if not (FileAccess.exists(LIBRARYFLEPATH)): forceUpdateTime('chkLibrary')
            if not (FileAccess.exists(CHANNELFLEPATH) & FileAccess.exists(M3UFLEPATH) & FileAccess.exists(XMLTVFLEPATH) & FileAccess.exists(GENREFLEPATH)):
                forceUpdateTime('chkChannels')


    def chkJSONQUE(self):
        if not self.queueRunning and not isClient():
            threadit(self.runJSON)


    def runJSON(self):
        #Only run after idle for 2mins to reduce system impact. Check interval every 15mins, run in chunks set by PAGE_LIMIT.
        self.queueRunning = True
        queuePool = SETTINGS.getCacheSetting('queuePool', json_data=True, default={})
        params = queuePool.get('params',[])
        for param in (list(chunkLst(params,SETTINGS.getSettingInt('Page_Limit'))) or [[]])[0]:
            if self.myService._interrupt():
                self.log('runJSON, _interrupt')
                break
            elif not self.myService.isIdle or self.myService.player.isPlaying():
                self.log('runJSON, waiting for idle...')
                break
            else:
                runParam = params.pop(0)
                if 'Files.GetDirectory' in runParam:
                    self.myService._que(JSONRPC().cacheJSON,2,runParam, **{'life':datetime.timedelta(days=28),'timeout':90})
                else:
                    self.myService._que(JSONRPC().sendJSON,5,runParam)
            queuePool['params'] = setDictLST(params)
            self.log('runJSON, remaining = %s'%(len(queuePool['params'])))
            SETTINGS.setCacheSetting('queuePool', queuePool, json_data=True)
        self.queueRunning = False


    def runAutoTune(self):
        try:
            autotune = Autotune(service=self.myService)
            autotune._runTune(samples=True)
            del autotune
        except Exception as e: self.log('runAutoTune failed! %s'%(e), xbmc.LOGERROR)
    

    def getChannels(self):
        self.log('getChannels')
        try:
            if isClient(): return []
            builder  = Builder(self.myService)
            channels = builder.verify()
            del builder
            return list(channels)
        except Exception as e: 
            self.log('getChannels failed! %s'%(e), xbmc.LOGERROR)
            return []
        

    def chkChannelChange(self, channels=[]):
        if isClient(): return channels
        with sudo_dialog(msg='%s %ss'%(LANGUAGE(32028),LANGUAGE(32023))):
            nChannels = self.getChannels()
            if channels != nChannels:
                self.log('chkChannelChange, resetting chkChannels')
                forceUpdateTime('chkChannels')
                return nChannels
            return channels

        
    def chkSettingsChange(self, settings=[]):
        self.log('chkSettingsChange')
        with sudo_dialog(msg='%s %s'%(LANGUAGE(32028),LANGUAGE(32053))):
            nSettings = dict(SETTINGS.getCurrentSettings())
            for setting, value in list(settings.items()):
                actions = {'User_Folder'    :{'func':self.setUserPath     ,'args':(value,nSettings.get(setting))},
                           'Network_Folder' :{'func':SETTINGS.setPVRPath  ,'args':(nSettings.get(setting))},
                           'Remote_URL'     :{'func':SETTINGS.setPVRRemote,'args':(nSettings.get(setting))},
                           'UDP_PORT'       :{'func':setPendingRestart},
                           'TCP_PORT'       :{'func':setPendingRestart},
                           'Client_Mode'    :{'func':setPendingRestart},
                           'Disable_Cache'  :{'func':setPendingRestart}}
                           
                if nSettings.get(setting) != value and actions.get(setting):
                    with sudo_dialog(LANGUAGE(32157)):
                        self.log('chkSettingsChange, detected change in %s - from: %s to: %s'%(setting,value,nSettings.get(setting)))
                        self.myService._que(actions[setting].get('func'),1,*actions[setting].get('args',()),**actions[setting].get('kwargs',{}))
            return nSettings


    def setUserPath(self, userFolders, forceOverride=False):
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
                        if DIALOG.yesnoDialog((LANGUAGE(30120)%newFilePath),autoclose=90):
                            dia = DIALOG.progressDialog(pnt, dia, message='%s: %s'%(LANGUAGE(32151),os.path.join(newFolder,'%s.bak'%(file))))
                            if FileAccess.copy(newFilePath,bakFilePath): #backup existing file.
                                dia = DIALOG.progressDialog(pnt, dia, message='%s: %s\n%s'%(LANGUAGE(32151),bakFilePath,LANGUAGE(32025)))
                        else: continue
                    if FileAccess.move(oldFilePath,newFilePath):
                        dia = DIALOG.progressDialog(pnt, dia, message='%s: %s\n%s'%(LANGUAGE(32051),file,LANGUAGE(32025)))
                        continue
                dia = DIALOG.progressDialog(pnt, dia, message=LANGUAGE(32052)%(file))
        SETTINGS.setPVRPath(newFolder)

