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
from consumer   import Consumer
from library    import Library
from jsonrpc    import JSONRPC
from autotune   import Autotune
from builder    import Builder
from backup     import Backup
from server     import HTTP

PAGE_LIMIT = int((REAL_SETTINGS.getSetting('Page_Limit') or "25"))

class Producer():
    queueRunning      = False
    backgroundRunning = False
    

    def __init__(self, service):
        self.log('__init__')
        self.service   = service
        self.consumer  = Consumer(service)
        self.webServer = HTTP(service.monitor)


    @contextmanager
    def backgroundActivity(self): #background running, reset suspend when finished.
        self.backgroundRunning = True
        try: yield
        finally:
            self.backgroundRunning = False


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
 

    def _que(self, func, priority=3, *args, **kwargs):
        try: #priority 1 Highest, 5 Lowest
            self.consumer.queue.put((priority, random.random(), (func, args, kwargs)),block=False)
            self.log('_que, func = %s, args = %s, kwargs = %s'%(func.__name__, args, kwargs))
        except TypeError: pass
        except Exception as e: 
            self.log("_que, failed! %s"%(e), xbmc.LOGERROR)


    def chkUpdateTime(self, key, runEvery, nextUpdate=None):
        #schedule updates, first boot always forces run!
        if nextUpdate is None: nextUpdate = (PROPERTIES.getPropertyInt(key) or 0)
        epoch = int(time.time())
        if (epoch >= nextUpdate):
            PROPERTIES.setPropertyInt(key,(epoch+runEvery))
            return True
        return False


    def _startProcess(self):
        #first processes before service loop starts. Only runs once per instance.
        setInstanceID() #create new instanceID
        setClient(isClient(),silent=False)
        setAutotuned(False)#reset autotuned state #todo find better solution for resetting
        setFirstrun(False) #reset firstrun state  #todo find better solution for resetting
        setLowPower()
        Backup().hasBackup()
        self._chkPVRBackend()
        self._chkVersion()
        self._chkDebugging()
        self.webServer._run()
        
     
    def _chkPVRBackend(self): #todo limit to one initial. run, as base template. Allowing users to edit settings. All future changes only set local/remote paths.
        if hasAddon(PVR_CLIENT,install=True,enable=True):
            SETTINGS.chkPluginSettings(PVR_CLIENT,IPTV_SIMPLE_SETTINGS()) #reconfigure iptv-simple, if needed.
        else: ... #todo okdialog user to explain IPTV PVR requirements. 
        

    def _chkDebugging(self):
        if SETTINGS.getSettingBool('Enable_Debugging'):
            if DIALOG.yesnoDialog(LANGUAGE(32142),autoclose=5):
                self.log('_chkDebugging, disabling debugging.')
                SETTINGS.setSettingBool('Enable_Debugging',False)
                DIALOG.notificationDialog(LANGUAGE(321423))


    def _chkFiles(self):
        self.log('_chkFiles')
        #check for missing files and run appropriate action to rebuild them only after init. startup.
        if hasFirstrun():
            if not (FileAccess.exists(CHANNELFLEPATH) & FileAccess.exists(M3UFLEPATH) & FileAccess.exists(XMLTVFLEPATH) & FileAccess.exists(GENREFLEPATH)):
                self.log('_chkFiles, rebuilding missing playlists')
                self._que(self.updateChannels,3)
            if not (FileAccess.exists(LIBRARYFLEPATH)):
                self.log('_chkFiles, rebuilding missing library')
                self._que(self.updateLibrary,1)


    def _taskManager(self):
        #main function to handle all scheduled queues. 
        if self.chkUpdateTime('updateSettings',runEvery=3600):
            self._que(self.updateSettings,1)
        if self.chkUpdateTime('chkFiles',runEvery=300):
            self._que(self._chkFiles,2)
        if self.chkUpdateTime('updateRecommended',runEvery=300):
            self._que(self.updateRecommended,2)
            
        if not self.backgroundRunning:
            if self.chkUpdateTime('updateLibrary',runEvery=(REAL_SETTINGS.getSettingInt('Max_Days')*3600)):
                self._que(self.updateLibrary,2)
            if self.chkUpdateTime('updateChannels',runEvery=3600):
                self._que(self.updateChannels,3)
    
        if not self.queueRunning:
            if self.chkUpdateTime('updateJSON',runEvery=600):
                self._que(self.updateJSON,4)


    def updateRecommended(self):
        self.log('updateRecommended')
        try:
            library = Library(service=self.service)
            library.searchRecommended()
            del library
        except Exception as e: self.log('updateRecommended failed! %s'%(e), xbmc.LOGERROR)


    def updateLibrary(self):
        self.log('updateLibrary')
        try:
            with self.backgroundActivity():
                library = Library(service=self.service)
                library.importPrompt()
                complete = library.updateLibrary()
                del library
                if   not complete: forceUpdateTime('updateLibrary')
                elif not hasAutotuned(): self.runAutoTune() #run autotune for the first time this Kodi/PTVL instance.
        except Exception as e: self.log('updateLibrary failed! %s'%(e), xbmc.LOGERROR)
    
    
    def updateSettings(self):
        #parse/sync varies third-party and Kodi settings.
        self.log('updateSettings')
        try:
            with sudo_dialog(msg='%s %s'%(LANGUAGE(32028),LANGUAGE(30069))):
                jsonRPC = JSONRPC()
                setClient(isClient())
                if (jsonRPC.getSettingValue('epg.pastdaystodisplay')   or 1) != SETTINGS.getSettingInt('Min_Days'):
                    SETTINGS.setSettingInt('Min_Days',min)
                    
                if (jsonRPC.getSettingValue('epg.futuredaystodisplay') or 3) != SETTINGS.getSettingInt('Max_Days'):
                    SETTINGS.setSettingInt('Max_Days',max)
                    
                if SETTINGS.getSetting('Network_Folder') != SETTINGS.getSetting('User_Folder'):
                    SETTINGS.setSetting('Network_Folder',SETTINGS.getSetting('User_Folder'))
                    
                PROPERTIES.setPropertyBool('hasPVRSource',jsonRPC.hasPVRSource())
                del jsonRPC
        except Exception as e: self.log('updateSettings failed! %s'%(e), xbmc.LOGERROR)
         
         
    def runAutoTune(self):
        self.log('runAutoTune')
        try:
            with self.backgroundActivity():
                autotune = Autotune(service=self.service)
                autotune._runTune(samples=True)
                del autotune
        except Exception as e: self.log('runAutoTune failed! %s'%(e), xbmc.LOGERROR)
    
        
    def updateChannels(self):
        self.log('updateChannels')
        try:
            with self.backgroundActivity():
                builder  = Builder(self.service)
                complete = builder.build()
                del builder
                if not complete: forceUpdateTime('updateChannels') #clear run schedule
                else: setFirstrun() #set init. boot status to true.
        except Exception as e: self.log('updateChannels failed! %s'%(e), xbmc.LOGERROR)
        
    
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
        with sudo_dialog(msg='%s %ss'%(LANGUAGE(32028),LANGUAGE(32023))):
            nChannels = self.getChannels()
            if channels != nChannels:
                self.log('chkChannelChange, resetting updateChannels')
                forceUpdateTime('updateChannels')
                return nChannels
            return channels


    def chkSettingsChange(self, settings=[]):
        self.log('chkSettingsChange')
        with sudo_dialog(msg='%s %s'%(LANGUAGE(32028),LANGUAGE(32053))):
            nSettings = dict(SETTINGS.getCurrentSettings())
            actions   = {'User_Folder'  :self.moveUser,
                         'UDP_PORT'     :setPendingRestart,
                         'TCP_PORT'     :setPendingRestart,
                         'Client_Mode'  :setPendingRestart,
                         'Remote_URL'   :setPendingRestart,
                         'Disable_Cache':setPendingRestart}
            #serviceRestart runs on a threaded delay, multi-calls allowed/cancelled
            for setting, value in list(settings.items()):
                if nSettings.get(setting) != value and actions.get(setting):
                    if setting == 'User_Folder': args = (value,nSettings.get(setting))
                    else:                        args = None
                    if args: self._que(actions[setting],1,args)
                    else:    self._que(actions[setting],1)
            return nSettings


    def moveUser(self, folders, forceOverride=False):
        oldFolder, newFolder = folders
        self.log('moveUser, oldFolder = %s, newFolder = %s'%(oldFolder,newFolder))
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
        SETTINGS.setPVRPath(SETTINGS.getSetting('User_Folder'))
        setPendingRestart()

        
    def updateJSON(self):
        timerit(self.runJSON)(5)


    def runJSON(self):
        #Only run after idle for 2mins to reduce system impact. Check interval every 15mins, run in chunks set by PAGE_LIMIT.
        if not self.queueRunning and not isClient():
            self.queueRunning = True
            queuePool = SETTINGS.getCacheSetting('queuePool', json_data=True, default={})
            params = queuePool.get('params',[])
            for param in (list(chunkLst(params,PAGE_LIMIT)) or [[]])[0]:
                if self.service.monitor.waitForAbort(1):
                    self.log('runJSON, waitForAbort')
                    forceUpdateTime('updateJSON')
                    break
                elif self.service.player.isPlaying():
                    self.log('runJSON, waiting for playback to finish...')
                    break
                elif not (int(xbmc.getGlobalIdleTime()) or 0) > OVERLAY_DELAY or self.service.player.isPlaying():
                    self.log('runJSON, waiting for idle...')
                    break
                else:
                    runParam = params.pop(0)
                    if 'Files.GetDirectory' in runParam:
                        self._que(JSONRPC().cacheJSON,2,runParam, **{'life':datetime.timedelta(days=28),'timeout':90})
                    else:
                        self._que(JSONRPC().sendJSON,5,runParam)
                queuePool['params'] = setDictLST(params)
                self.log('runJSON, remaining = %s'%(len(queuePool['params'])))
                SETTINGS.setCacheSetting('queuePool', queuePool, json_data=True)
            self.queueRunning = False


    def _chkVersion(self):
        if ADDON_VERSION != SETTINGS.getCacheSetting('lastVersion', default='v.0.0.0'):
            #todo check kodi repo addon.xml version number, prompt user if outdated.
            SETTINGS.setCacheSetting('lastVersion',ADDON_VERSION)
            BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/utilities.py,Show_Changelog)')
