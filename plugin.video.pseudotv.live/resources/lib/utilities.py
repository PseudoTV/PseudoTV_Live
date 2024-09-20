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
        self.sysARG  = sysARG
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def showWelcome(self):
        try: 
            with BUILTIN.busy_dialog():
                fle   = FileAccess.open(WELCOME_FLE, "r")
                ftext = fle.read()
                fsize = fle.size()
                fle.close()
                
            if (SETTINGS.getCacheSetting('showWelcome', checksum=fsize) or 'true') == 'true':
                SETTINGS.setCacheSetting('showWelcome', 'false', checksum=fsize)
                DIALOG.textviewer(ftext.format(addon_name = ADDON_NAME,
                                               pvr_name   = PVR_CLIENT_NAME,
                                               m3u        = M3UFLEPATH.replace('special://profile','.'),
                                               xmltv      = XMLTVFLEPATH.replace('special://profile','.'),
                                               genre      = GENREFLEPATH.replace('special://profile','.'),
                                               logo       = LOGO_LOC.replace('special://profile','.')), heading=(LANGUAGE(32043)%(ADDON_NAME,ADDON_VERSION)),usemono=True)
        except Exception as e: self.log('showWelcome failed! %s'%(e), xbmc.LOGERROR)
        

    def showChangelog(self):
        try:  
            def addColor(text):
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
                txt = addColor(fle.read())
                fle.close()
            DIALOG.textviewer(txt, heading=(LANGUAGE(32045)%(ADDON_NAME,ADDON_VERSION)),usemono=True)
        except Exception as e: self.log('showChangelog failed! %s'%(e), xbmc.LOGERROR)
   

    def showReadme(self):
        try: 
            def convertMD2TXT(md):
                markdown = (re.sub(r'(\[[^][]*]\([^()]*\))|^(#+)(.*)', lambda x:x.group(1) if x.group(1) else "[COLOR=cyan][B]{1} {0} {1}[/B][/COLOR]".format(x.group(3),('#'*len(x.group(2)))), md, flags=re.M))
                markdown = (re.sub(r'`(.*?)`', lambda x:x.group(1) if not x.group(1) else '"[I]{0}[/I]"'.format(x.group(1)), markdown, flags=re.M))
                markdown = re.sub(r'\[!\[(.*?)\]\((.*?)\)]\((.*?)\)', lambda x:x.group(1) if not x.group(1) else '[B]{0}[/B]\n[I]{1}[/I]'.format(x.group(1),x.group(3)), markdown, flags=re.M)
                markdown = re.sub(r'\[(.*?)\]\((.*?)\)', lambda x:x.group(1) if not x.group(2) else '- [B]{0}[/B]\n[I]{1}[/I]'.format(x.group(1),x.group(2)), markdown, flags=re.M)
                markdown = re.sub(r'\[(.*?)\]\((.*?)\)', lambda x:x.group(1) if not x.group(1) else '- [B]{0}[/B]'.format(x.group(1)), markdown, flags=re.M)
                markdown = '\n'.join(list([filelist for filelist in markdown.split('\n') if filelist[:2] not in ['![','[!','!.','!-','ht']]))
                return markdown
                
            with BUILTIN.busy_dialog():
                openAddonSettings((7,1))
                fle = FileAccess.open(README_FLE, "r")
                txt = convertMD2TXT(fle.read())
                fle.close()
            DIALOG.textviewer(txt, heading=(LANGUAGE(32043)%(ADDON_NAME,ADDON_VERSION)),usemono=True, autoclose=90)
        except Exception as e: self.log('showReadme failed! %s'%(e), xbmc.LOGERROR)


    def userGroups(self):
        self.log('userGroups')
        retval = DIALOG.inputDialog(LANGUAGE(32044), default=SETTINGS.getSetting('User_Groups'))
        if retval: SETTINGS.setSetting('User_Groups',retval)
                
                
    def showFile(self, file):
        with BUILTIN.busy_dialog():
            def openFile(fle):
                if fle.lower().endswith('xml'):
                    fle = FileAccess.open(fle, "r")
                    dom = parse(fle) # or xml.dom.minidom.parseString(xml_string)
                    fle.close()
                    return dom.toprettyxml()
                else:
                    fle = FileAccess.open(fle, "r")
                    ppstring = fle.read()
                    fle.close()
                    return ppstring.replace('#EXTINF:','\n[COLOR=cyan][B]#EXTINF:[/B][/COLOR]')
        openAddonSettings((7,1))
        #todo generate qrcode to server file location.
        #todo change xmltv to display statistics not raw file.
        try: DIALOG.textviewer(openFile(file), heading=('%s - %s')%(ADDON_NAME,os.path.basename(file)),usemono=True)
        except Exception as e: self.log('showFile failed! %s'%(e), xbmc.LOGERROR)


    def openChannelManager(self, chnum: int=1):
        self.log('openChannelManager, chnum = %s'%(chnum))
        if not PROPERTIES.isRunning('MANAGER_RUNNING'):
            with PROPERTIES.setRunning('MANAGER_RUNNING'), PROPERTIES.suspendActivity():
                from manager import Manager
                chmanager = Manager(MANAGER_XML, ADDON_PATH, "default", channel=chnum)
                del chmanager
        
        
    def openChannelBug(self):
        self.log('openChannelBug')
        if not PROPERTIES.isRunning('OVERLAY_CHANNELBUG_RUNNING'):
            from channelbug import ChannelBug
            channelbug = ChannelBug(CHANNELBUG_XML, ADDON_PATH, "default")
            SETTINGS.setSetting("Channel_Bug_Position_XY",PROPERTIES.getProperty("Channel_Bug_Position_XY"))
            del channelbug


    def _togglePVR(self):
        if DIALOG.yesnoDialog('%s?'%(LANGUAGE(32121)%(xbmcaddon.Addon(PVR_CLIENT_ID).getAddonInfo('name')))):
            PROPERTIES.setEXTProperty('%s.chkPVRRefresh'%(ADDON_ID),'true')
            

    def buildMenu(self, select=None):
        items = [{'label':LANGUAGE(32117),'label2':LANGUAGE(32120),'icon':COLOR_LOGO,'func':self.deleteFiles          ,'args':(LANGUAGE(32120),False)              , 'hide':False},#"Rebuild M3U/XMLTV"
                 {'label':LANGUAGE(32118),'label2':LANGUAGE(32119),'icon':COLOR_LOGO,'func':self.deleteFiles          ,'args':(LANGUAGE(32119),True)               , 'hide':False},#"Clean Start"
                 {'label':LANGUAGE(32121)%(PVR_CLIENT_NAME),'label2':LANGUAGE(32122) ,'icon':COLOR_LOGO,'func':self._togglePVR                                     , 'hide':False},#"Force PVR reload"
                 {'label':LANGUAGE(32123),'label2':LANGUAGE(32124),'icon':COLOR_LOGO,'func':setPendingRestart                                                      , 'hide':False},#"Force PTVL reload"
                 {'label':LANGUAGE(32154),'label2':LANGUAGE(32154),'icon':COLOR_LOGO,'func':self.showFile             ,'args':(M3UFLEPATH,)                        , 'hide':False},#"Show M3U"
                 {'label':LANGUAGE(32155),'label2':LANGUAGE(32155),'icon':COLOR_LOGO,'func':self.showFile             ,'args':(XMLTVFLEPATH,)                      , 'hide':False}, #"Show XMLTV"
                 {'label':LANGUAGE(32159),'label2':LANGUAGE(33159),'icon':COLOR_LOGO,'func':PROPERTIES.setEXTProperty ,'args':('%s.chkLibrary'%(ADDON_ID),'true')  , 'hide':False}, #Rescan library
                 {'label':LANGUAGE(32180),'label2':LANGUAGE(33180),'icon':COLOR_LOGO,'func':PROPERTIES.setEXTProperty ,'args':('%s.chkFillers'%(ADDON_ID),'true')  , 'hide':False}, #Rescan library
                 {'label':LANGUAGE(32181),'label2':LANGUAGE(33181),'icon':COLOR_LOGO,'func':PROPERTIES.setEXTProperty ,'args':('%s.runAutoTune'%(ADDON_ID),'true') , 'hide':False}] #Run Autotune
                
        with BUILTIN.busy_dialog():
            listItems = [LISTITEMS.buildMenuListItem(item.get('label'),item.get('label2'),item.get('icon')) for item in sorted(items,key=itemgetter('label')) if not (item.get('hide'))]
            if select is None: select = DIALOG.selectDialog(listItems, '%s - %s'%(ADDON_NAME,LANGUAGE(32126)),multi=False)
            
        if not select is None:
            try: 
                selectItem = [item for item in items if item.get('label') == listItems[select].getLabel()][0]
                self.log('buildMenu, selectItem = %s'%selectItem)
                if selectItem.get('args'): selectItem['func'](*selectItem['args'])
                else:                      selectItem['func']()
            except Exception as e: 
                self.log("buildMenu, failed! %s"%(e), xbmc.LOGERROR)
                return DIALOG.notificationDialog(LANGUAGE(32000))
        else: openAddonSettings((7,1))
                

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
            with BUILTIN.busy_dialog(), PROPERTIES.suspendActivity():
                 for key in keys:
                    if FileAccess.delete(files[key]): DIALOG.notificationDialog(LANGUAGE(32127)%(key.replace(':','')))
        if full: 
            SETTINGS.setAutotuned(False)
            setPendingRestart()


    def run(self):  
        ctl = (7,1) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))
        
        if param == 'Apply_PVR_Settings':
            ctl = (7,9)
            with BUILTIN.busy_dialog():
                from jsonrpc import JSONRPC
                jsonRPC = JSONRPC()
                if SETTINGS.setPVRPath(USER_LOC,validString(SETTINGS.getFriendlyName()),prompt=True,force=True):
                    DIALOG.notificationDialog(LANGUAGE(32152))
                else: DIALOG.notificationDialog(LANGUAGE(32165))
                del jsonRPC
        elif param.startswith('Channel_Manager'):
            ctl = (0,1)
            self.openChannelManager()
        elif param.startswith('Move_Channelbug'):
            ctl = (5,5)
            self.openChannelBug()
        elif param == 'Show_Welcome':
            return self.showWelcome()
        elif param == 'Show_Readme':  
            return self.showReadme()
        elif param == 'Show_Changelog':
            return self.showChangelog()
        elif param == 'User_Groups':
            return self.userGroups()
        elif param == 'Utilities':
            return self.buildMenu()
        return openAddonSettings(ctl)

if __name__ == '__main__': Utilities(sys.argv).run()
    
    