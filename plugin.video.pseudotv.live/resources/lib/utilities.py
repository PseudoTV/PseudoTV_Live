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

# -*- coding: utf-8 -*-
from globals import *


class Utilities:
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG = sysARG
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

   
    def qrWiki(self):
        with PROPERTIES.suspendActivity():
            DIALOG.qrDialog(URL_WIKI,LANGUAGE(32216)%(ADDON_NAME,ADDON_AUTHOR))


    def qrSupport(self):
        with PROPERTIES.suspendActivity():
            DIALOG.qrDialog(URL_SUPPORT, LANGUAGE(30033)%(ADDON_NAME))
        
        
    def qrRemote(self):
        with PROPERTIES.suspendActivity():
            DIALOG.qrDialog('http://%s/%s'%(PROPERTIES.getRemoteHost(),'remote.html'), LANGUAGE(30165))
        

    def qrReadme(self):
        with PROPERTIES.suspendActivity():
            DIALOG.qrDialog(URL_README, LANGUAGE(32043)%(ADDON_NAME,ADDON_VERSION))
    
    
    def qrBonjourDL(self):
        with PROPERTIES.suspendActivity():
            DIALOG.qrDialog(URL_WIN_BONJOUR, LANGUAGE(32217))
        
        
    def showChangelog(self):
        try:  
            def __addColor(text):
                text = text.replace('- Added'      ,'[COLOR=green][B]- Added:[/B][/COLOR]')
                text = text.replace('- Introduced' ,'[COLOR=green][B]- Introduced:[/B][/COLOR]')
                text = text.replace('- Addressed'  ,'[COLOR=green][B]- Addressed:[/B][/COLOR]')
                text = text.replace('- New!'       ,'[COLOR=yellow][B]- New!:[/B][/COLOR]')
                text = text.replace('- Optimized'  ,'[COLOR=yellow][B]- Optimized:[/B][/COLOR]')
                text = text.replace('- Improved'   ,'[COLOR=yellow][B]- Improved:[/B][/COLOR]')
                text = text.replace('- Modified'   ,'[COLOR=yellow][B]- Modified:[/B][/COLOR]')
                text = text.replace('- Enhanced'   ,'[COLOR=yellow][B]- Enhanced:[/B][/COLOR]')
                text = text.replace('- Refactored' ,'[COLOR=yellow][B]- Refactored:[/B][/COLOR]')
                text = text.replace('- Reworked'   ,'[COLOR=yellow][B]- Reworked:[/B][/COLOR]')
                text = text.replace('- Tweaked'    ,'[COLOR=yellow][B]- Tweaked:[/B][/COLOR]')
                text = text.replace('- Updated'    ,'[COLOR=yellow][B]- Updated:[/B][/COLOR]')
                text = text.replace('- Changed'    ,'[COLOR=yellow][B]- Changed:[/B][/COLOR]')
                text = text.replace('- Corrected'  ,'[COLOR=yellow][B]- Corrected:[/B][/COLOR]')
                text = text.replace('- Proper'     ,'[COLOR=yellow][B]- Proper:[/B][/COLOR]')
                text = text.replace('- Included'   ,'[COLOR=yellow][B]- Changed:[/B][/COLOR]')
                text = text.replace('- Notice'     ,'[COLOR=orange][B]- Notice:[/B][/COLOR]')
                text = text.replace('- Fixed'      ,'[COLOR=orange][B]- Fixed:[/B][/COLOR]')
                text = text.replace('- Resolved'   ,'[COLOR=orange][B]- Resolved:[/B][/COLOR]')
                text = text.replace('- Removed'    ,'[COLOR=red][B]- Removed:[/B][/COLOR]')
                text = text.replace('- Excluded'   ,'[COLOR=red][B]- Excluded:[/B][/COLOR]')
                text = text.replace('- Deprecated' ,'[COLOR=red][B]- Deprecated:[/B][/COLOR]')
                text = text.replace('- Important'  ,'[COLOR=red][B]- Important:[/B][/COLOR]')
                text = text.replace('- Warning'    ,'[COLOR=red][B]- Warning:[/B][/COLOR]')
                return text  
                
            with BUILTIN.busy_dialog():
                fle = FileAccess.open(CHANGELOG_FLE, "r")
                txt = __addColor(fle.read())
                fle.close()
            DIALOG.textviewer(txt, heading=(LANGUAGE(32045)%(ADDON_NAME,ADDON_VERSION)),usemono=True)
        except Exception as e: self.log('showChangelog failed! %s'%(e), xbmc.LOGERROR)


    def qrDebug(self):
        def __cleanLog(content):           
            content = re.sub('//.+?:.+?@'                  ,'//USER:PASSWORD@'     , content)
            content = re.sub('<user>.+?</user>'            ,'<user>USER</user>'    , content)
            content = re.sub('<pass>.+?</pass>'            ,'<pass>PASSWORD</pass>', content)
            content = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", '0.0.0.0'             , content)
            return content
                
        def __cleanPayload(payload):
            def __getDebug(payload): #only post errors
                debug = payload.get('debug',{})
                # [debug.pop(key) for key in list(debug.keys()) if key in ['LOGDEBUG','LOGINFO']]
                return debug
                    
            payload['debug']    = loadJSON(__cleanLog(dumpJSON(__getDebug(payload),idnt=4)))
            payload['channels'] = loadJSON(__cleanLog(dumpJSON(payload.get('channels',[]),idnt=4)))
            payload['m3u']      = loadJSON(__cleanLog(dumpJSON(payload.get('m3u',[]),idnt=4)))
            [payload.pop(key) for key in ['host','remotes','bonjour','library','servers'] if key in payload]
            return payload
        
        def __postLog(data):
            try:
                session = requests.Session()
                response = session.post('https://paste.kodi.tv/' + 'documents', data=data.encode('utf-8'), headers={'User-Agent':'%s: %s'%(ADDON_ID, ADDON_VERSION)})
                if 'key' in response.json():
                    return True, 'https://paste.kodi.tv/' + response.json()['key']
                elif 'message' in response.json():
                    self.log('qrDebug, upload failed, paste may be too large')
                    return False, response.json()['message']
                else:
                    self.log('qrDebug failed! %s'%response.text)
                    return False, LANGUAGE(30191)
            except:
                self.log('qrDebug, unable to retrieve the paste url')
                return False, LANGUAGE(30190)
              
        with BUILTIN.busy_dialog():
            payload = SETTINGS.getPayload(inclDebug=True)
        if   not payload.get('debug',{}): return DIALOG.notificationDialog(LANGUAGE(32187))
        elif not DIALOG.yesnoDialog(message=LANGUAGE(32188)): return
        
        with BUILTIN.busy_dialog():
            succes, data = __postLog(dumpJSON(__cleanPayload(payload),idnt=4))
            
        if succes: DIALOG.qrDialog(data,LANGUAGE(32189)%(data))
        else:      DIALOG.okDialog(LANGUAGE(32190)%(data))
                

    def _runCPUBench(self):
        with BUILTIN.busy_dialog():
            if hasAddon('script.pystone.benchmark',install=True, enable=True, notify=True):
                return BUILTIN.executebuiltin('RunScript(script.pystone.benchmark)')
        
        
    def _runIOBench(self):
        with BUILTIN.busy_dialog():
            if hasAddon('script.io.benchmark',install=True, enable=True, notify=True):
                return BUILTIN.executebuiltin('RunScript(script.io.benchmark,%s)'%(escapeString(f'path={USER_LOC}')))
        
        
    def _runLogger(self):
        with BUILTIN.busy_dialog():
            if hasAddon('script.kodi.loguploader',install=True, enable=True, notify=True):
                return BUILTIN.executebuiltin('RunScript(script.kodi.loguploader)')
        
 
    def _runCleanup(self, full=False):
        self.log('_runCleanup, full = %s'%(full))
        files = {LANGUAGE(30094):M3UFLEPATH,    #"M3U"
                 LANGUAGE(30095):XMLTVFLEPATH,  #"XMLTV"
                 LANGUAGE(30096):GENREFLEPATH,  #"Genre"
                 LANGUAGE(30108):CHANNELFLEPATH,#"Channels"
                 LANGUAGE(32041):LIBRARYFLEPATH}#"Library"

        keys = list(files.keys())
        if not full: keys = keys[:2]
        if DIALOG.yesnoDialog('%s ?'%(msg)): 
            with BUILTIN.busy_dialog(), PROPERTIES.interruptActivity():
                for key in keys:
                    if FileAccess.delete(files[key]): DIALOG.notificationDialog(LANGUAGE(32127)%(key.replace(':','')))
                    else:                             DIALOG.notificationDialog('%s %s'%((LANGUAGE(32127)%(key.replace(':',''))),LANGUAGE(32052)))
        self._runUpdate(full)


    def _runReload(self):
        if DIALOG.yesnoDialog('%s?'%(LANGUAGE(32121)%(xbmcaddon.Addon(PVR_CLIENT_ID).getAddonInfo('name')))): PROPERTIES.setPropTimer('chkPVRRefresh')
            
            
    def _runRestart(self):
        return PROPERTIES.setPendingRestart()
            
            
    def _runFillers(self):
        return PROPERTIES.setPropTimer('chkFillers')


    def _runLibrary(self):
        PROPERTIES.setPropertyBool('ForceLibrary',True)
        PROPERTIES.setEpochTimer('chkLibrary')
        DIALOG.notificationDialog('%s %s'%(LANGUAGE(30199),LANGUAGE(30200)))


    def _runAutotune(self):
        self.log('_runAutotune')
        SETTINGS.setAutotuned(False)
        PROPERTIES.setPropTimer('chkChannels')
         
         
    def _runUpdate(self, full=False):
        self.log('_runUpdate, full = %s'%(full))
        if full: PROPERTIES.setEpochTimer('chkLibrary')
        PROPERTIES.setEpochTimer('chkChannels')
               

    def buildMenu(self, select=None):
        items = [
                 {'label':LANGUAGE(32117)                  ,'label2':LANGUAGE(32120),'icon':COLOR_LOGO,'func':self._runCleanup  , 'hide':True ,'args':(False,)}, #"Rebuild M3U/XMLTV"
                 {'label':LANGUAGE(32118)                  ,'label2':LANGUAGE(32119),'icon':COLOR_LOGO,'func':self._runCleanup  , 'hide':True ,'args':(True,)}, #"Clean Start"
                 {'label':LANGUAGE(32121)%(PVR_CLIENT_NAME),'label2':LANGUAGE(32122),'icon':COLOR_LOGO,'func':self._runReload   , 'hide':False},#"Force PVR reload"
                 {'label':LANGUAGE(32123)                  ,'label2':LANGUAGE(32124),'icon':COLOR_LOGO,'func':self._runRestart  , 'hide':False},#"Force PTVL reload"
                 {'label':LANGUAGE(32159)                  ,'label2':LANGUAGE(33159),'icon':COLOR_LOGO,'func':self._runLibrary  , 'hide':False},
                 {'label':LANGUAGE(32180)                  ,'label2':LANGUAGE(33180),'icon':COLOR_LOGO,'func':self._runFillers  , 'hide':False},
                 {'label':LANGUAGE(32181)                  ,'label2':LANGUAGE(33181),'icon':COLOR_LOGO,'func':self._runAutotune , 'hide':False},
                 {'label':LANGUAGE(30205)                  ,'label2':LANGUAGE(30205),'icon':COLOR_LOGO,'func':self._runCPUBench , 'hide':False},
                 {'label':LANGUAGE(30208)                  ,'label2':LANGUAGE(30208),'icon':COLOR_LOGO,'func':self._runIOBench  , 'hide':False},
                 ]

        with BUILTIN.busy_dialog():
            if not SETTINGS.getSettingBool('Debug_Enable'): items = [item for item in items if not item.get('hide',False)]
            listItems = [LISTITEMS.buildMenuListItem(item.get('label'),item.get('label2'),item.get('icon')) for item in sorted(items,key=itemgetter('label'))]
            if select is None: select = DIALOG.selectDialog(listItems, '%s - %s'%(ADDON_NAME,LANGUAGE(32126)),multi=False)
            
        if not select is None:
            with PROPERTIES.interruptActivity():
                try: 
                    selectItem = [item for item in items if item.get('label') == listItems[select].getLabel()][0]
                    self.log('buildMenu, selectItem = %s'%selectItem)
                    if selectItem.get('args'): selectItem['func'](*selectItem['args'])
                    else:                      selectItem['func']()
                except Exception as e: 
                    self.log("buildMenu, failed! %s"%(e), xbmc.LOGERROR)
                    return DIALOG.notificationDialog(LANGUAGE(32000))
        else: SETTINGS.openSettings((6,1))
         
         
    def openChannelManager(self, chnum: int=1):
        self.log('openChannelManager, chnum = %s'%(chnum))
        if not PROPERTIES.isRunning('OVERLAY_MANAGER'):
            with PROPERTIES.chkRunning('OVERLAY_MANAGER'), PROPERTIES.interruptActivity():
                with BUILTIN.busy_dialog():
                    from manager import Manager
                chmanager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=chnum)
                del chmanager
        else: DIALOG.notificationDialog(LANGUAGE(32057)%(ADDON_NAME))
     
        
    def openPositionUtil(self, idx):
        self.log('openPositionUtil, idx = %s'%(idx))
        if not PROPERTIES.isRunning('OVERLAY_UTILITY'):
            with PROPERTIES.chkRunning('OVERLAY_UTILITY'), PROPERTIES.interruptActivity():
                with BUILTIN.busy_dialog():
                    from overlaytool import OverlayTool
                overlaytool = OverlayTool(OVERLAYTOOL_XML, ADDON_PATH, "default", Focus_IDX=idx)
                del overlaytool


    def defaultChannels(self):
        self.log('defaultChannels')
        with BUILTIN.busy_dialog():
            values = SETTINGS.getSettingList('Select_server')
            values = [cleanLabel(value) for value in values]
            values.insert(0,LANGUAGE(30022)) #Auto
            values.insert(1,LANGUAGE(32069))
        select = DIALOG.selectDialog(values, LANGUAGE(30173), findItemsInLST(values, [SETTINGS.getSetting('Default_Channels')])[0], False, SELECT_DELAY, False)
        if not select is None: return SETTINGS.setSetting('Default_Channels',values[select])
        else:                  return SETTINGS.setSetting('Default_Channels',LANGUAGE(30022))


    def run(self):
        with BUILTIN.busy_dialog():
            ctl = (0,1)
            try:    param = self.sysARG[1]
            except: param = None
            
            #Channels
            if param.startswith('Channel_Manager'):
                ctl = (0,1)
                self.openChannelManager()
            elif param.startswith('Default_Channels'):
                ctl = (0,2)
                self.defaultChannels()
                
            #Globals
            elif param.startswith('Move_Channelbug'):
                ctl = (3,15)
                self.openPositionUtil(1)
            elif param.startswith('Move_OnNext'):
                ctl = (3,15)
                self.openPositionUtil(2)
                
            #Multi-Room
            elif param == 'Show_ZeroConf_QR':
                ctl = (5,5)
                self.qrBonjourDL()
                
            #Misc. Scripts
            elif param == 'CPU_Bench':
                self._runCPUBench()
            elif param == 'IO_Bench':
                self._runIOBench()
            elif param == 'Logger':
                self._runLogger()
                
            #Misc.Docs
            elif param == 'Utilities':
                ctl = (6,1)
                return self.buildMenu()
            elif param == 'Show_Wiki_QR':
                ctl = (6,4)
                return self.qrWiki()
            elif param == 'Show_Support_QR':
                ctl = (6,5)
                return self.qrSupport()
            elif param == 'Show_Remote_UI':
                ctl = (6,6)
                return self.qrRemote()
            elif param == 'Show_Changelog':
                ctl = (6,8)
                return self.showChangelog()
                
            #Misc. Debug
            elif param == 'Debug_QR':
                ctl = (6,1)
                return self.qrDebug()
                
            elif param == 'Run_Autotune':
                return self._runAutotune()
                
            return SETTINGS.openSettings(ctl)

if __name__ == '__main__': timerit(Utilities(sys.argv).run)(0.1)
   