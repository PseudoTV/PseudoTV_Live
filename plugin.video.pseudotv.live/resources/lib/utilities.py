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

# -*- coding: utf-8 -*-
from typing import Any, Optional, Tuple, List, Dict
from variables import *

class Utilities(object):
    
    @staticmethod
    def buildMenu(select: Optional[int] = None):        
        def __buildMenuItem(item: Dict[str, Any]):
            return Globals.listitems.buildMenuListItem(item.get('label'),item.get('label2'),item.get('icon'))
        
        items = [
                 {'label':LANGUAGE(32117)                  ,'label2':LANGUAGE(32120),'icon':ICON,'func':Utilities._runCleanup  , 'hide':False ,'args':(False,),'kwargs':{}}, #"Rebuild M3U/XMLTV/Genres"
                 {'label':LANGUAGE(32118)                  ,'label2':LANGUAGE(32119),'icon':ICON,'func':Utilities._runCleanup  , 'hide':False ,'args':(True,) ,'kwargs':{}}, #"Clean Start"
                 {'label':LANGUAGE(32121)%(PVR_CLIENT_NAME),'label2':LANGUAGE(32122),'icon':ICON,'func':Utilities._runReload   , 'hide':False ,'args':()      ,'kwargs':{}}, #"Force PVR reload"
                 {'label':LANGUAGE(32123)                  ,'label2':LANGUAGE(32124),'icon':ICON,'func':Utilities._runRestart  , 'hide':False ,'args':()      ,'kwargs':{}}, #"Force PTVL restart"
                 {'label':LANGUAGE(30205)                  ,'label2':LANGUAGE(30205),'icon':ICON,'func':Utilities._runCPUBench , 'hide':False ,'args':()      ,'kwargs':{}}, 
                 {'label':LANGUAGE(30208)                  ,'label2':LANGUAGE(30208),'icon':ICON,'func':Utilities._runIOBench  , 'hide':False ,'args':()      ,'kwargs':{}}, 
                 ]

        with Globals.builtin.busy_dialog():
            if not Globals.settings.getSettingBool('Debug_Enable'): items = [item for item in items if not item.get('hide',False)]
            listItems = poolit(__buildMenuItem)(sorted(items,key=itemgetter('label')))
            
        select = Globals.dialog.selectDialog(listItems, '%s - %s'%(ADDON_NAME,LANGUAGE(32126)),multi=False)
        if not select is None:
            try: 
                selectItem = [item for item in items if item.get('label') == listItems[select].getLabel()][0]
                LOG('Utilities: buildMenu, selectItem = %s'%selectItem)
                selectItem['func'](*selectItem.get('args',()),**selectItem.get('kwargs',{}))
            except Exception as e: 
                LOG('Utilities: buildMenu, failed! %s'%(e), xbmc.LOGERROR)
                return Globals.dialog.notificationDialog(LANGUAGE(32000))
        else: Globals._openSettings((6,1))
    
    
    @staticmethod
    def _runCleanup(full: bool = False):
        if Globals.dialog.yesnoDialog('Utilities: %s ?'%( LANGUAGE(32119) if full else LANGUAGE(32120) )): 
            with Globals.builtin.busy_dialog(lock=True), Globals.properties.interruptActivity():
                LOG('Utilities: _runCleanup, full %s'%(full))
                files = {LANGUAGE(30094):M3UFLEPATH,    #"M3U"
                         LANGUAGE(30095):XMLTVFLEPATH,  #"XMLTV"
                         LANGUAGE(30096):GENREFLEPATH}  #"Genre"
                if full:
                    instanceName = Globals.properties.getFriendlyName()
                    files.update({LANGUAGE(32053)                :SETTINGS_FLE, #Settings.xml
                                  f'PVR Instance: {instanceName}':Globals.settings.instances.getPVRInstancePath(instanceName)}) #IPTV Instance.xml
                
                for key, path in list(files.items()):
                    if FileAccess.delete(path): 
                        Globals.dialog.notificationDialog('%s: %s\n%s'%(LANGUAGE(32127),key.replace(': ',''),os.path.split(path)[1]),silent=False)
                        
                if full:
                    Globals.settings.setCacheSetting('Utilities._runCleanup',Globals.settings.getCurrentSettings())
                    # if Globals.settings.cache.cache.purge(): #TODO REROUTE
                    timerit(Globals.properties.setPendingRestart)(SERVICE_INTERVAL)
                Globals.dialog.notificationDialog(LANGUAGE(32025))

    
    @staticmethod
    def _runReload():
        if Globals.dialog.yesnoDialog('Utilities: %s?'%(LANGUAGE(32121)%(xbmcaddon.Addon(PVR_CLIENT_ID).getAddonInfo('name')))):
            state = Globals.settings.getSettingBool('Enable_PVR_RELOAD')
            Globals.settings.setSettingBool('Enable_PVR_RELOAD',True)
            Globals.properties.setPropTimer('chkPVRRefresh')#refresh pvr guide
            timerit(Globals.settings.setSettingBool)(M3U_REFRESH,*('Enable_PVR_RELOAD',state))
        Globals.dialog.notificationDialog(LANGUAGE(32025))
            
    @staticmethod
    def _runRestart() -> bool:
        return Globals.properties.setPendingRestart()
        
    @staticmethod
    def _runCPUBench():
        with Globals.builtin.busy_dialog():
            if Globals.settings.hasAddon('script.pystone.benchmark', notify=True):
                return Globals.builtin.executebuiltin('RunScript(script.pystone.benchmark)')
        
    @staticmethod
    def _runIOBench():
        with Globals.builtin.busy_dialog():
            if Globals.settings.hasAddon('script.io.benchmark', notify=True):
                return Globals.builtin.executebuiltin('RunScript(script.io.benchmark,%s)'%(Globals._escapeString(f'path={CACHE_LOC}')))
    
    @staticmethod
    def qrWiki():
        Globals.dialog.qrDialog(URL_WIKI,LANGUAGE(32216)%(ADDON_NAME,ADDON_AUTHOR))

    @staticmethod
    def qrSupport():
        Globals.dialog.qrDialog(URL_SUPPORT, LANGUAGE(30033)%(ADDON_NAME))
        
    @staticmethod
    def qrRemote():
        Globals.dialog.qrDialog('Utilities: http://%s/%s'%(Globals.properties.getRemoteHost(),'remote.html'), LANGUAGE(30165))

    @staticmethod
    def qrReadme():
        Globals.dialog.qrDialog(URL_README, LANGUAGE(32043)%(ADDON_NAME,ADDON_VERSION))

    @staticmethod
    def qrBonjourDL():
        Globals.dialog.qrDialog(URL_WIN_BONJOUR, LANGUAGE(32217))
        
    @staticmethod
    def showChangeLOG():
        try:  
            def __addColor(text: str) -> str:
                text = text.replace('- Added'      ,'[COLOR=green][B]- Added:[/B][/COLOR]')
                text = text.replace('- Implemented','[COLOR=green][B]- Implemented:[/B][/COLOR]')
                text = text.replace('- Introduced' ,'[COLOR=green][B]- Introduced:[/B][/COLOR]')
                text = text.replace('- Addressed'  ,'[COLOR=green][B]- Addressed:[/B][/COLOR]')
                text = text.replace('- New!'       ,'[COLOR=yellow][B]- New!:[/B][/COLOR]')
                text = text.replace('- Optimized'  ,'[COLOR=yellow][B]- Optimized:[/B][/COLOR]')
                text = text.replace('- Improved'   ,'[COLOR=yellow][B]- Improved:[/B][/COLOR]')
                text = text.replace('- Modified'   ,'[COLOR=yellow][B]- Modified:[/B][/COLOR]')
                text = text.replace('- Enhanced'   ,'[COLOR=yellow][B]- Enhanced:[/B][/COLOR]')
                text = text.replace('- Refactored' ,'[COLOR=yellow][B]- Refactored:[/B][/COLOR]')
                text = text.replace('- Refined'    ,'[COLOR=yellow][B]- Refined:[/B][/COLOR]')
                text = text.replace('- Overhauled' ,'[COLOR=yellow][B]- Overhauled:[/B][/COLOR]')
                text = text.replace('- Reworked'   ,'[COLOR=yellow][B]- Reworked:[/B][/COLOR]')
                text = text.replace('- Tweaked'    ,'[COLOR=yellow][B]- Tweaked:[/B][/COLOR]')
                text = text.replace('- Adjusted'   ,'[COLOR=yellow][B]- Adjusted:[/B][/COLOR]')
                text = text.replace('- Updated'    ,'[COLOR=yellow][B]- Updated:[/B][/COLOR]')
                text = text.replace('- Changed'    ,'[COLOR=yellow][B]- Changed:[/B][/COLOR]')
                text = text.replace('- Corrected'  ,'[COLOR=yellow][B]- Corrected:[/B][/COLOR]')
                text = text.replace('- Proper'     ,'[COLOR=yellow][B]- Proper:[/B][/COLOR]')
                text = text.replace('- Included'   ,'[COLOR=yellow][B]- Changed:[/B][/COLOR]')
                text = text.replace('- Notice'     ,'[COLOR=orange][B]- Notice:[/B][/COLOR]')
                text = text.replace('- Fixed'      ,'[COLOR=orange][B]- Fixed:[/B][/COLOR]')
                text = text.replace('- Resolved'   ,'[COLOR=orange][B]- Resolved:[/B][/COLOR]')
                text = text.replace('- Removed'    ,'[COLOR=red][B]- Removed:[/B][/COLOR]')
                text = text.replace('- Replaced'   ,'[COLOR=red][B]- Replaced:[/B][/COLOR]')
                text = text.replace('- Eliminated' ,'[COLOR=red][B]- Eliminated:[/B][/COLOR]')
                text = text.replace('- Excluded'   ,'[COLOR=red][B]- Excluded:[/B][/COLOR]')
                text = text.replace('- Deprecated' ,'[COLOR=red][B]- Deprecated:[/B][/COLOR]')
                text = text.replace('- Important'  ,'[COLOR=red][B]- Important:[/B][/COLOR]')
                text = text.replace('- Warning'    ,'[COLOR=red][B]- Warning:[/B][/COLOR]')
                return text  
                
            with Globals.builtin.busy_dialog():
                try: CHANGELOG_URL
                except:
                    with FileAccess.stream(CHANGELOG_FLE) as fle:
                        txt = __addColor(fle.read())
                Globals.dialog.textviewer(txt, heading=(LANGUAGE(32045)%(ADDON_NAME,ADDON_VERSION)),usemono=True)
        except Exception as e: LOG('Utilities: showChangelog failed! %s'%(e), xbmc.LOGERROR)

    @staticmethod
    def qrDebug():
        def __cleanLog(content: str) -> str:           
            content = re.sub('//.+?:.+?@'                  ,'//USER:PASSWORD@'     , content)
            content = re.sub('<user>.+?</user>'            ,'<user>USER</user>'    , content)
            content = re.sub('<pass>.+?</pass>'            ,'<pass>PASSWORD</pass>', content)
            content = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", '0.0.0.0'             , content)
            return content
                
        def __cleanPayload(payload: Dict[str, Any]) -> Dict[str, Any]:
            def __getDebug(payload: Dict[str, Any]) -> Dict[str, Any]: #only post errors
                debug = payload.get('debug',{})
                # [debug.pop(key) for key in list(debug.keys()) if key in ['LOGDEBUG','LOGINFO']]
                return debug
                    
            payload['debug']    = FileAccess.loadJSON(__cleanLog(FileAccess.dumpJSON(__getDebug(payload),idnt=4)))
            payload['channels'] = FileAccess.loadJSON(__cleanLog(FileAccess.dumpJSON(payload.get('channels',[]),idnt=4)))
            payload['m3u']      = FileAccess.loadJSON(__cleanLog(FileAccess.dumpJSON(payload.get('m3u',[]),idnt=4)))
            [payload.pop(key) for key in ['host','remotes','bonjour','library','servers'] if key in payload]
            return payload
        
        def __postLog(data: str) -> Tuple[bool, str]:
            try:
                session = requests.Session()
                response = session.post('https://paste.kodi.tv/' + 'documents', data=data.encode(DEFAULT_ENCODING), headers={'User-Agent':'%s: %s'%(ADDON_ID, ADDON_VERSION)})
                if 'key' in response.json():
                    return True, 'https://paste.kodi.tv/' + response.json()['key']
                elif 'message' in response.json():
                    LOG('Utilities: qrDebug, upload failed, paste may be too large')
                    return False, response.json()['message']
                else:
                    LOG('Utilities: qrDebug failed! %s'%response.text)
                    return False, LANGUAGE(30191)
            except Exception:
                LOG('Utilities: qrDebug, unable to retrieve the paste url')
                return False, LANGUAGE(30190)
              
        with Globals.builtin.busy_dialog():
            payload = Globals.settings.getPayload(inclDebug=True)
        if   not payload.get('debug',{}): return Globals.dialog.notificationDialog(LANGUAGE(32187))
        elif not Globals.dialog.yesnoDialog(message=LANGUAGE(32188)): return
        
        with Globals.builtin.busy_dialog():
            succes, data = __postLog(FileAccess.dumpJSON(__cleanPayload(payload),idnt=4))
            
        if succes: Globals.dialog.qrDialog(data,LANGUAGE(32189)%(data))
        else:      Globals.dialog.okDialog(LANGUAGE(32190)%(data))
       
    @staticmethod
    def _runLogger():
        with Globals.builtin.busy_dialog():
            if Globals.settings.hasAddon('script.kodi.loguploader', notify=True):
                return Globals.builtin.executebuiltin('RunScript(script.kodi.loguploader)')
        
    @staticmethod
    def _runUpdate(full: bool = False):
        LOG('Utilities: _runUpdate, full = %s'%(full))
        Globals.properties.setPropTimer('chkChanged')# Refresh Channel Changed!
              
    @staticmethod
    def openPositionUtil(idx: int):
        LOG('Utilities: openPositionUtil, idx = %s'%(idx))
        if not Globals.properties.isRunning('Utilities.openPositionUtil'):
            with Globals.properties.chkRunning('Utilities.openPositionUtil'):
                with Globals.builtin.busy_dialog():
                    from overlaytool import OverlayTool
                try: overlaytool = OverlayTool(OVERLAYTOOL_XML, ADDON_PATH, "default", Focus_IDX=idx)
                except Exception as e: LOG("Utilities: openPositionUtil, failed! %s"%(e), xbmc.LOGERROR)
                finally: del overlaytool
                          
# @threadit      
# def _clrLibrary():
    # #elif mode == 'clear_autotune' : _clrLibrary()
    # Globals.dialog.notificationDialog(LANGUAGE(32025))
    # manager = Manager(MANAGER_XML, ADDON_PATH, "default", start=False, channel=-1)
    # manager.clrLibraryCache()
    # del manager       
    
# @threadit   
# def _clrBlacklist():
    # # elif mode == 'clear_blackList': _clrBlacklist()
    # Globals.dialog.notificationDialog(LANGUAGE(32025))
    # Globals.settings.setSetting('Clear_BlackList','')
        
            
    @threadit
    def _run(self, sysARG: List[str]):
        with Globals.builtin.busy_dialog():
            ctl = (0,1)
            try:              param = sysARG[1]
            except Exception: param = None
            LOG('Utilities: param = %s'%(param))

            if param == 'Show_Menu':
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
                return self.showChangeLOG()
                
            #Globals
            if param.startswith('Move_Channelbug'):
                ctl = (3,15)
                self.openPositionUtil(1)
            elif param.startswith('Move_OnNext'):
                ctl = (3,15)
                self.openPositionUtil(2)
                
            #Multi-Room
            elif param == 'Show_ZeroConf_QR':
                ctl = (5,5)
                Utilities(sys.argv).qrBonjourDL()
                
            #Misc. Scripts
            elif param == 'CPU_Bench':
                self._runCPUBench()
            elif param == 'IO_Bench':
                self._runIOBench()
            elif param == 'Logger':
                self._runLogger()
                
            #Misc. Debug
            elif param == 'Debug_QR':
                ctl = (6,1)
                return Utilities(sys.argv).qrDebug()
            return Globals._openSettings(ctl)

if __name__ == '__main__': Utilities()._run(sys.argv)