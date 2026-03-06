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

# -*- coding: utf-8 -*-
from globals import *

class Utilities(object):

    @staticmethod
    def qrWiki():
        DIALOG.qrDialog(URL_WIKI,LANGUAGE(32216)%(ADDON_NAME,ADDON_AUTHOR))

    @staticmethod
    def qrSupport():
        DIALOG.qrDialog(URL_SUPPORT, LANGUAGE(30033)%(ADDON_NAME))
        
    @staticmethod
    def qrRemote():
        DIALOG.qrDialog('Utilities: http://%s/%s'%(PROPERTIES.getRemoteHost(),'remote.html'), LANGUAGE(30165))

    @staticmethod
    def qrReadme():
        DIALOG.qrDialog(URL_README, LANGUAGE(32043)%(ADDON_NAME,ADDON_VERSION))

    @staticmethod
    def qrBonjourDL():
        DIALOG.qrDialog(URL_WIN_BONJOUR, LANGUAGE(32217))
        
    @staticmethod
    def showChangelog():
        try:  
            def __addColor(text):
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
                
            with BUILTIN.busy_dialog():
                fle = FileAccess.open(CHANGELOG_FLE, "r")
                txt = __addColor(fle.read())
                fle.close()
            DIALOG.textviewer(txt, heading=(LANGUAGE(32045)%(ADDON_NAME,ADDON_VERSION)),usemono=True)
        except Exception as e: log('Utilities: showChangelog failed! %s'%(e), xbmc.LOGERROR)

    @staticmethod
    def qrDebug():
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
                    
            payload['debug']    = FileAccess.loadJSON(__cleanLog(FileAccess.dumpJSON(__getDebug(payload),idnt=4)))
            payload['channels'] = FileAccess.loadJSON(__cleanLog(FileAccess.dumpJSON(payload.get('channels',[]),idnt=4)))
            payload['m3u']      = FileAccess.loadJSON(__cleanLog(FileAccess.dumpJSON(payload.get('m3u',[]),idnt=4)))
            [payload.pop(key) for key in ['host','remotes','bonjour','library','servers'] if key in payload]
            return payload
        
        def __postLog(data):
            try:
                session = requests.Session()
                response = session.post('https://paste.kodi.tv/' + 'documents', data=data.encode('utf-8'), headers={'User-Agent':'%s: %s'%(ADDON_ID, ADDON_VERSION)})
                if 'key' in response.json():
                    return True, 'https://paste.kodi.tv/' + response.json()['key']
                elif 'message' in response.json():
                    log('Utilities: qrDebug, upload failed, paste may be too large')
                    return False, response.json()['message']
                else:
                    log('Utilities: qrDebug failed! %s'%response.text)
                    return False, LANGUAGE(30191)
            except Exception:
                log('Utilities: qrDebug, unable to retrieve the paste url')
                return False, LANGUAGE(30190)
              
        with BUILTIN.busy_dialog():
            payload = SETTINGS.getPayload(inclDebug=True)
        if   not payload.get('debug',{}): return DIALOG.notificationDialog(LANGUAGE(32187))
        elif not DIALOG.yesnoDialog(message=LANGUAGE(32188)): return
        
        with BUILTIN.busy_dialog():
            succes, data = __postLog(FileAccess.dumpJSON(__cleanPayload(payload),idnt=4))
            
        if succes: DIALOG.qrDialog(data,LANGUAGE(32189)%(data))
        else:      DIALOG.okDialog(LANGUAGE(32190)%(data))
       
    @staticmethod
    def _runCPUBench():
        with BUILTIN.busy_dialog():
            if SETTINGS.hasAddon('script.pystone.benchmark',install=True, enable=True, notify=True):
                return BUILTIN.executebuiltin('RunScript(script.pystone.benchmark)')
        
    @staticmethod
    def _runIOBench():
        with BUILTIN.busy_dialog():
            if SETTINGS.hasAddon('script.io.benchmark',install=True, enable=True, notify=True):
                return BUILTIN.executebuiltin('RunScript(script.io.benchmark,%s)'%(Gloabls._escapeString(f'path={USER_LOC}')))
        
    @staticmethod
    def _runLogger():
        with BUILTIN.busy_dialog():
            if SETTINGS.hasAddon('script.kodi.loguploader',install=True, enable=True, notify=True):
                return BUILTIN.executebuiltin('RunScript(script.kodi.loguploader)')
        
    @staticmethod
    def _runCleanup(full=False):
        log('Utilities: _runCleanup, full = %s'%(full))
        files = {LANGUAGE(30094):M3UFLEPATH,    #"M3U"
                 LANGUAGE(30095):XMLTVFLEPATH,  #"XMLTV"
                 LANGUAGE(30096):GENREFLEPATH,  #"Genre"
                 LANGUAGE(30108):CHANNELFLEPATH,#"Channels"
                 LANGUAGE(32041):LIBRARYFLEPATH}#"Library"

        keys = list(files.keys())
        if not full: keys = keys[:2]
        if DIALOG.yesnoDialog('Utilities: %s ?'%(msg)): 
            with BUILTIN.busy_dialog(), PROPERTIES.interruptActivity():
                for key in keys:
                    if FileAccess.delete(files[key]): DIALOG.notificationDialog(LANGUAGE(32127)%(key.replace(':','')))
                    else:                             DIALOG.notificationDialog('Utilities: %s %s'%((LANGUAGE(32127)%(key.replace(':',''))),LANGUAGE(32052)))
        _runUpdate(full)

    @staticmethod
    def _runReload():
        if DIALOG.yesnoDialog('Utilities: %s?'%(LANGUAGE(32121)%(xbmcaddon.Addon(PVR_CLIENT_ID).getAddonInfo('name')))):
            timerit(PROPERTIES.setPropTimer)(15,'chkPVRRefresh')
            
    @staticmethod
    def _runRestart():
        return PROPERTIES.setPendingRestart()
            
    @staticmethod
    def _runFillers():
        return PROPERTIES.setPropTimer('chkFillers')

    @staticmethod
    def _runUpdate(full=False):
        log('Utilities: _runUpdate, full = %s'%(full))
        timerit(PROPERTIES.setPropTimer)(15,'chkChanged')#trigger channel building
              
    @staticmethod
    def buildMenu(select=None):
        items = [
                 {'label':LANGUAGE(32117)                  ,'label2':LANGUAGE(32120),'icon':COLOR_LOGO,'func':_runCleanup  , 'hide':True ,'args':(False,)}, #"Rebuild M3U/XMLTV"
                 {'label':LANGUAGE(32118)                  ,'label2':LANGUAGE(32119),'icon':COLOR_LOGO,'func':_runCleanup  , 'hide':True ,'args':(True,)}, #"Clean Start"
                 {'label':LANGUAGE(32121)%(PVR_CLIENT_NAME),'label2':LANGUAGE(32122),'icon':COLOR_LOGO,'func':_runReload   , 'hide':False},#"Force PVR reload"
                 {'label':LANGUAGE(32123)                  ,'label2':LANGUAGE(32124),'icon':COLOR_LOGO,'func':_runRestart  , 'hide':False},#"Force PTVL reload"
                 {'label':LANGUAGE(32159)                  ,'label2':LANGUAGE(33159),'icon':COLOR_LOGO,'func':_runLibrary  , 'hide':False},
                 {'label':LANGUAGE(32180)                  ,'label2':LANGUAGE(33180),'icon':COLOR_LOGO,'func':_runFillers  , 'hide':False},
                 {'label':LANGUAGE(30205)                  ,'label2':LANGUAGE(30205),'icon':COLOR_LOGO,'func':_runCPUBench , 'hide':False},
                 {'label':LANGUAGE(30208)                  ,'label2':LANGUAGE(30208),'icon':COLOR_LOGO,'func':_runIOBench  , 'hide':False},
                 ]

        with BUILTIN.busy_dialog():
            if not SETTINGS.getSettingBool('Debug_Enable'): items = [item for item in items if not item.get('hide',False)]
            listItems = [LISTITEMS.buildMenuListItem(item.get('label'),item.get('label2'),item.get('icon')) for item in sorted(items,key=itemgetter('label'))]
            if select is None: select = DIALOG.selectDialog(listItems, '%s - %s'%(ADDON_NAME,LANGUAGE(32126)),multi=False)
            
        if not select is None:
            try: 
                selectItem = [item for item in items if item.get('label') == listItems[select].getLabel()][0]
                log('Utilities: buildMenu, selectItem = %s'%selectItem)
                if selectItem.get('args'): selectItem['func'](*selectItem['args'])
                else:                      selectItem['func']()
            except Exception as e: 
                log('Utilities: buildMenu, failed! %s'%(e), xbmc.LOGERROR)
                return DIALOG.notificationDialog(LANGUAGE(32000))
        else: Globals._openSettings((6,1))
        
    @staticmethod
    def openPositionUtil(idx):
        log('Utilities: openPositionUtil, idx = %s'%(idx))
        if not PROPERTIES.isRunning('Utilities.openPositionUtil'):
            with PROPERTIES.chkRunning('Utilities.openPositionUtil'):
                with BUILTIN.busy_dialog():
                    from overlaytool import OverlayTool
                try: overlaytool = OverlayTool(OVERLAYTOOL_XML, ADDON_PATH, "default", Focus_IDX=idx)
                except Exception as e: log("Utilities: openPositionUtil, failed! %s"%(e), xbmc.LOGERROR)
                finally: del overlaytool
            
    @threadit
    @staticmethod
    def _run(sysARG):
        with BUILTIN.busy_dialog():
            ctl = (0,1)
            try:    param = sysARG[1]
            except Exception: param = None
            log('Utilities: param = %s'%(param))

            #Globals
            elif param.startswith('Move_Channelbug'):
                ctl = (3,15)
                Utilities().openPositionUtil(1)
            elif param.startswith('Move_OnNext'):
                ctl = (3,15)
                Utilities().openPositionUtil(2)
                
            #Multi-Room
            elif param == 'Show_ZeroConf_QR':
                ctl = (5,5)
                Utilities().qrBonjourDL()
                
            #Misc. Scripts
            elif param == 'CPU_Bench':
                Utilities()._runCPUBench()
            elif param == 'IO_Bench':
                Utilities()._runIOBench()
            elif param == 'Logger':
                Utilities()._runLogger()
                
            #Misc.Docs
            elif param == 'Utilities':
                ctl = (6,1)
                return Utilities().buildMenu()
            elif param == 'Show_Wiki_QR':
                ctl = (6,4)
                return Utilities().qrWiki()
            elif param == 'Show_Support_QR':
                ctl = (6,5)
                return Utilities().qrSupport()
            elif param == 'Show_Remote_UI':
                ctl = (6,6)
                return Utilities().qrRemote()
            elif param == 'Show_Changelog':
                ctl = (6,8)
                return Utilities().showChangelog()
                
            #Misc. Debug
            elif param == 'Debug_QR':
                ctl = (6,1)
                return Utilities().qrDebug()
            return Globals._openSettings(ctl)

if __name__ == '__main__': Utilities()._run(sys.argv)