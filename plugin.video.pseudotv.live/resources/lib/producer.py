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

PAGE_LIMIT = int((REAL_SETTINGS.getSetting('Page_Limit') or "25"))

class Producer():
    queueRunning = False
    
    def __init__(self, service):
        self.log('__init__')
        self.service  = service
        self.consumer = Consumer(service)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
 

    def _que(self, func, priority=3, *args, **kwargs):
        try: #priority 1 Highest, 5 Lowest
            self.consumer.queue.put((priority, random.random(), (func, args, kwargs)),block=False)
            self.log('_que, func = %s, args = %s, kwargs = %s'%(func.__name__, args, kwargs))
        except TypeError: pass
        except Exception as e: 
            self.log("_que, failed! %s"%(e), xbmc.LOGERROR)


    def chkUpdateTime(self, key, wait, nextUpdate=None):
        #schedule updates, first boot always forces run!
        if nextUpdate is None: nextUpdate = (PROPERTIES.getPropertyInt(key) or 0)
        epoch = int(time.time())
        if (epoch >= nextUpdate):
            PROPERTIES.setPropertyInt(key,(epoch+wait))
            return True
        return False


    def _startProcess(self):
        #first processes before service loop starts. Only runs once per instance.
        # chkPluginSettings(PVR_CLIENT,IPTV_SIMPLE_SETTINGS()) #reconfigure iptv-simple if needed.
        self._chkVersion()
        self._chkDebugging()
        setClient(isClient(),silent=False)
        Backup().hasBackup()
        chkPVREnabled()
        setLowPower(state=getLowPower())
        self._chkAutotune()
        

    def _chkDebugging(self):
        #prompt user warning concerning disabled cache.
        DEBUG_CACHE = (SETTINGS.getSettingBool('Enable_Debugging') & SETTINGS.getSettingBool('Disable_Cache'))
        if DEBUG_CACHE: DIALOG.okDialog(LANGUAGE(32130))
    

    def _chkFiles(self):
        #check for missing files and run appropriate action to rebuild them only after init. startup.
        if hasFirstrun():
            fileTasks = [{'files':[CHANNELFLEPATH,M3UFLEPATH,XMLTVFLEPATH,GENREFLEPATH],'action':self.updateChannels,'priority':3},
                         {'files':[LIBRARYFLEPATH],'action':self.updateLibrary,'priority':2}]
            for task in fileTasks:
                for file in task.get('files',[]):
                    if not FileAccess.exists(file):
                        self._que(task['action'],task['priority'])
                        break
                        

    def _taskManager(self):
        #main function to handle all scheduled queues. 
        if self.chkUpdateTime('updateSettings',3600):
            self._que(self.updateSettings,1)
        if self.chkUpdateTime('chkFiles',300):
            self._que(self._chkFiles,2)
        if self.chkUpdateTime('updateRecommended',300):
            self._que(self.updateRecommended,2)
        if self.chkUpdateTime('updateLibrary',(REAL_SETTINGS.getSettingInt('Max_Days')*3600)):
            self._que(self.updateLibrary,2)
        if self.chkUpdateTime('updateChannels',3600):
            self._que(self.updateChannels,3)
        if self.chkUpdateTime('updateJSON',600):
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
            library = Library(service=self.service)
            library.importPrompt()
            complete = library.updateLibrary()
            del library
            if not complete: forceUpdateTime('updateLibrary')
            elif not hasAutotuned(): self.runAutoTune() #run autotune for the first time this Kodi/PTVL instance.
        except Exception as e: self.log('updateLibrary failed! %s'%(e), xbmc.LOGERROR)
    
    
    def updateSettings(self):
        #parse/sync varies third-party and Kodi settings.
        self.log('updateSettings')
        try:
            with sudo_dialog(msg='%s %s'%(LANGUAGE(32028),LANGUAGE(30069))):
                jsonRPC = JSONRPC()
                setClient(isClient())
                if (jsonRPC.getSettingValue('epg.pastdaystodisplay')   or 1) != SETTINGS.getSettingInt('Min_Days'): SETTINGS.setSettingInt('Min_Days',min)
                if (jsonRPC.getSettingValue('epg.futuredaystodisplay') or 3) != SETTINGS.getSettingInt('Max_Days'): SETTINGS.setSettingInt('Max_Days',max)
                if (SETTINGS.getSetting('Network_Path')) != (SETTINGS.getSetting('User_Folder')):                   SETTINGS.setSetting('Network_Path',SETTINGS.getSetting('User_Folder'))
                PROPERTIES.setPropertyBool('hasPVRSource',jsonRPC.hasPVRSource())
                del jsonRPC
        except Exception as e: self.log('updateSettings failed! %s'%(e), xbmc.LOGERROR)
            

    def _chkAutotune(self):
        self._que(self.updateAutoTune,2)
        
        
    def updateAutoTune(self):
        self.log('updateAutoTune')
        try:
            autotune = Autotune(service=self.service)
            autotune._runTune()
            del autotune
        except Exception as e: self.log('updateAutoTune failed! %s'%(e), xbmc.LOGERROR)
        
        
    def runAutoTune(self):
        self.log('runAutoTune')
        try:
            autotune = Autotune(service=self.service)
            autotune._runTune(samples=True,rebuild=False)
            del autotune
        except Exception as e: self.log('runAutoTune failed! %s'%(e), xbmc.LOGERROR)
    
        
    def updateChannels(self):
        self.log('updateChannels')
        try:
            builder  = Builder(self.service)
            complete = builder.build()
            del builder
            if not complete: forceUpdateTime('updateChannels') #clear run schedule
            else: setFirstrun() #set init. boot status to true.
        except Exception as e: self.log('updateChannels failed! %s'%(e), xbmc.LOGERROR)
        
    
    def getChannels(self):
        self.log('getChannels')
        if isClient(): return []
        try:
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

        
    def getSettings(self):
        self.log('getSettings')
        settings = ['User_Folder','UDP_PORT','TCP_PORT','Client_Mode','Remote_URL','Disable_Cache']
        for setting in settings:
            yield (setting,SETTINGS.getSetting(setting))
               
        
    def chkSettingsChange(self, settings=[]):
        self.log('chkSettingsChange')
        with sudo_dialog(msg='%s %s'%(LANGUAGE(32028),LANGUAGE(32053))):
            nSettings = dict(self.getSettings())
            actions   = {'User_Folder'  :self.moveUser,
                         'UDP_PORT'     :self.serviceRestart,
                         'TCP_PORT'     :self.serviceRestart,
                         'Client_Mode'  :self.serviceRestart,
                         'Remote_URL'   :self.serviceRestart,
                         'Disable_Cache':self.serviceRestart}
            #serviceRestart runs on a threaded delay, multi-calls allowed/cancelled
            for setting, value in list(settings.items()):
                if nSettings.get(setting) != value and actions.get(setting):
                    if setting == 'User_Folder': args = (value,nSettings.get(setting))
                    else:                        args = None
                    if args: self._que(actions[setting],1,args)
                    else:    self._que(actions[setting],1)
            return nSettings


    def moveUser(self, folders):
        oldFolder, newFolder = folders
        self.log('moveUser, oldFolder = %s, newFolder = %s'%(oldFolder,newFolder))
        files = [M3UFLE,XMLTVFLE,GENREFLE]
        dia   = DIALOG.progressDialog(message=LANGUAGE(32050))
        FileAccess.copy(os.path.join(oldFolder,'logos'),os.path.join(newFolder,'logos'))
        for idx, file in enumerate(files):
            pnt = int(((idx+1)*100)//len(files))
            dia = DIALOG.progressDialog(pnt, dia, message='%s %s'%(LANGUAGE(32051),file))
            oldFilePath = os.path.join(oldFolder,file)
            newFilePath = os.path.join(newFolder,file)
            if FileAccess.exists(oldFilePath):
                dia = DIALOG.progressDialog(pnt, dia, message='%s %s'%(LANGUAGE(32051),file))
                if FileAccess.copy(oldFilePath,newFilePath):
                    dia = DIALOG.progressDialog(pnt, dia, message='%s %s %s'%(LANGUAGE(32051),file,LANGUAGE(30053)))
                    continue
            dia = DIALOG.progressDialog(pnt, dia, message=LANGUAGE(32052)%(file))
        SETTINGS.setSetting('Network_Path',SETTINGS.getSetting('User_Folder'))
        self.serviceRestart()


    def serviceRestart(self):
        timerit(self._serviceRestart)(15.0)
        
        
    def _serviceRestart(self):
        self.service.monitor.pendingRestart = True
        
        
    def updateJSON(self):
        if not self.queueRunning:
            timerit(self.runJSON)(5)


    def runJSON(self):
        #Only run after idle for 2mins to reduce system impact. Check interval every 15mins, run in chunks set by PAGE_LIMIT.
        if not self.queueRunning:
            self.queueRunning = True
            queuePool = SETTINGS.getCacheSetting('queuePool', json_data=True, default={})
            params = queuePool.get('params',[])
            for param in (list(chunkLst(params,PAGE_LIMIT)) or [[]])[0]:
                if self.service.monitor.waitForAbort(1):
                    self.log('runJSON, waitForAbort')
                    forceUpdateTime('updateJSON')
                    break
                elif not (int(xbmc.getGlobalIdleTime()) or 0) > OVERLAY_DELAY:
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
            SETTINGS.setCacheSetting('lastVersion',ADDON_VERSION)
            BUILTIN.executebuiltin('RunScript(special://home/addons/plugin.video.pseudotv.live/resources/lib/utilities.py,Show_Changelog)')
