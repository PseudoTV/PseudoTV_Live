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
        DIALOG.qrDialog(URL_WIKI,LANGUAGE(32216)%(ADDON_NAME))


    def qrSupport(self):
        DIALOG.qrDialog(URL_SUPPORT, LANGUAGE(30033)%(ADDON_NAME))
        
        
    def qrRemote(self):
        DIALOG.qrDialog('http://%s/%s'%(PROPERTIES.getRemoteHost(),'remote.html'), LANGUAGE(30165))
        

    def qrReadme(self):
        DIALOG.qrDialog(URL_README, LANGUAGE(32043)%(ADDON_NAME,ADDON_VERSION))
    
    
    def qrBonjourDL(self):
        DIALOG.qrDialog(URL_WIN_BONJOUR, LANGUAGE(32217))
        
        
    def showChangelog(self):
        try:  
            def __addColor(text):
                text = text.replace('-Added'      ,'[COLOR=green][B]-Added:[/B][/COLOR]')
                text = text.replace('-New!'       ,'[COLOR=yellow][B]-New!:[/B][/COLOR]')
                text = text.replace('-Optimized'  ,'[COLOR=yellow][B]-Optimized:[/B][/COLOR]')
                text = text.replace('-Improved'   ,'[COLOR=yellow][B]-Improved:[/B][/COLOR]')
                text = text.replace('-Refactored' ,'[COLOR=yellow][B]-Refactored:[/B][/COLOR]')
                text = text.replace('-Tweaked'    ,'[COLOR=yellow][B]-Tweaked:[/B][/COLOR]')
                text = text.replace('-Updated'    ,'[COLOR=yellow][B]-Updated:[/B][/COLOR]')
                text = text.replace('-Changed'    ,'[COLOR=yellow][B]-Changed:[/B][/COLOR]')
                text = text.replace('-Notice'     ,'[COLOR=orange][B]-Notice:[/B][/COLOR]')
                text = text.replace('-Fixed'      ,'[COLOR=orange][B]-Fixed:[/B][/COLOR]')
                text = text.replace('-Removed'    ,'[COLOR=red][B]-Removed:[/B][/COLOR]')
                text = text.replace('-Important'  ,'[COLOR=red][B]-Important:[/B][/COLOR]')
                text = text.replace('-Warning'    ,'[COLOR=red][B]-Warning:[/B][/COLOR]')
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
                # for key in list(debug.keys()):
                    # if key in ['LOGDEBUG','LOGINFO']: debug.pop(key)
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
                if 'key' in response.json(): return True, 'https://paste.kodi.tv/' + response.json()['key']
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
                

    def openChannelManager(self, chnum: int=1):
        self.log('openChannelManager, chnum = %s'%(chnum))
        if not PROPERTIES.isRunning('OVERLAY_MANAGER'):
            with PROPERTIES.setRunning('OVERLAY_MANAGER'), PROPERTIES.interruptActivity():
                with BUILTIN.busy_dialog():
                    from manager import Manager
                chmanager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=chnum)
                del chmanager
     
        
    def openPositionUtil(self, idx):
        self.log('openPositionUtil, idx = %s'%(idx))
        if not PROPERTIES.isRunning('OVERLAY_UTILITY'):
            with PROPERTIES.setRunning('OVERLAY_UTILITY'), PROPERTIES.suspendActivity():
                with BUILTIN.busy_dialog():
                    from overlaytool import OverlayTool
                overlaytool = OverlayTool(OVERLAYTOOL_XML, ADDON_PATH, "default", Focus_IDX=idx)
                del overlaytool


    def _togglePVR(self):
        if DIALOG.yesnoDialog('%s?'%(LANGUAGE(32121)%(xbmcaddon.Addon(PVR_CLIENT_ID).getAddonInfo('name')))): PROPERTIES.setEpochTimer('chkPVRRefresh')
            

    def buildMenu(self, select=None):
        items = [{'label':LANGUAGE(32117),'label2':LANGUAGE(32120),'icon':COLOR_LOGO,'func':self.deleteFiles ,'args':(LANGUAGE(32120),False) , 'hide':False},#"Rebuild M3U/XMLTV"
                 {'label':LANGUAGE(32118),'label2':LANGUAGE(32119),'icon':COLOR_LOGO,'func':self.deleteFiles ,'args':(LANGUAGE(32119),True) , 'hide':False},#"Clean Start"
                 {'label':LANGUAGE(32121)%(PVR_CLIENT_NAME),'label2':LANGUAGE(32122) ,'icon':COLOR_LOGO,'func':self._togglePVR , 'hide':False},#"Force PVR reload"
                 {'label':LANGUAGE(32123),'label2':LANGUAGE(32124),'icon':COLOR_LOGO,'func':PROPERTIES.setPendingRestart , 'hide':False},#"Force PTVL reload"
                 {'label':LANGUAGE(32159),'label2':LANGUAGE(33159),'icon':COLOR_LOGO,'func':PROPERTIES.forceUpdateTime ,'args':('chkLibrary',) , 'hide':False}, #Rescan library
                 {'label':LANGUAGE(32180),'label2':LANGUAGE(33180),'icon':COLOR_LOGO,'func':PROPERTIES.setEpochTimer ,'args':('chkFillers',) , 'hide':False}, #Rescan library
                 {'label':LANGUAGE(32181),'label2':LANGUAGE(33181),'icon':COLOR_LOGO,'func':self._runAutotune , 'hide':False}] #Run Autotune
                
        with BUILTIN.busy_dialog():
            listItems = [LISTITEMS.buildMenuListItem(item.get('label'),item.get('label2'),item.get('icon')) for item in sorted(items,key=itemgetter('label')) if not (item.get('hide'))]
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
        else: openAddonSettings((6,1))
         
         
    def _runAutotune(self):
        SETTINGS.setAutotuned(False)
        PROPERTIES.setEpochTimer('chkAutoTune')
         
         
    def _runUpdate(self, full=False):
        if full:
            SETTINGS.setAutotuned(False)
            PROPERTIES.forceUpdateTime('chkLibrary')
        PROPERTIES.forceUpdateTime('chkChannels')
               

    def deleteFiles(self, msg, full: bool=False):
        self.log('deleteFiles, full = %s'%(full))
        files = {LANGUAGE(30094):M3UFLEPATH,    #"M3U"
                 LANGUAGE(30095):XMLTVFLEPATH,  #"XMLTV"
                 LANGUAGE(30096):GENREFLEPATH,  #"Genre"
                 LANGUAGE(30108):CHANNELFLEPATH,#"Channels"
                 LANGUAGE(32041):LIBRARYFLEPATH}#"Library"

        keys = list(files.keys())
        if not full: keys = keys[:2]
        if DIALOG.yesnoDialog('%s ?'%(msg)): 
            with BUILTIN.busy_dialog():
                 for key in keys:
                    if FileAccess.delete(files[key]): DIALOG.notificationDialog(LANGUAGE(32127)%(key.replace(':','')))
        self._runUpdate(full)


    def sortMethod(self):
        self.log('sortMethod')
        with BUILTIN.busy_dialog():
            from jsonrpc import JSONRPC
            values  = sorted([item.title() for item in JSONRPC().getEnums("List.Sort",type="method")])
        try: return SETTINGS.setSetting('Sort_Method',values[DIALOG.selectDialog(values, LANGUAGE(32214), findItemsInLST(values, [SETTINGS.getSetting('Sort_Method').lower()])[0], False, SELECT_DELAY, False)])
        except: pass


    def defaultChannels(self):
        self.log('defaultChannels')
        with BUILTIN.busy_dialog():
            values = [cleanLabel(value) for value in SETTINGS.getSettingList('Select_server')]
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
            elif param == 'Sort_Method':
                ctl = (3,22)
                self.sortMethod()
                
            #Multi-Room
            elif param == 'Show_ZeroConf_QR':
                ctl = (5,5)
                self.qrBonjourDL()

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
            return openAddonSettings(ctl)

if __name__ == '__main__': Utilities(sys.argv).run()
   