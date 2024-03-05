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
from globals          import *
from xml.dom.minidom  import parse, parseString

class Utilities:
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG  = sysARG
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def userGroups(self):
        self.log('userGroups')
        retval = DIALOG.inputDialog(LANGUAGE(32044), default=SETTINGS.getSetting('User_Groups'))
        if retval: SETTINGS.setSetting('User_Groups',retval)
                
                
    def showFile(self, file):
        with busy_dialog():
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
        try: DIALOG.textviewer(openFile(file), heading=('%s - %s')%(ADDON_NAME,os.path.basename(file)),usemono=True,usethread=True)
        except Exception as e: self.log('showFile failed! %s'%(e), xbmc.LOGERROR)


    def showWelcome(self):
        try: 
            fle = FileAccess.open(WELCOME_FLE, "r")
            txt = fle.read()
            siz = fle.size()
            fle.close()
            if SETTINGS.getCacheSetting('showWelcome', checksum=siz, default='true') == 'true':
                SETTINGS.setCacheSetting('showWelcome', 'false', checksum=siz)
                DIALOG.textviewer(txt.format(addon_name=ADDON_NAME,
                                                    pvr_name=PVR_CLIENT_NAME,
                                                    m3u=M3UFLEPATH,
                                                    xmltv=XMLTVFLEPATH,
                                                    genre=GENREFLEPATH,
                                                    logo=LOGO_LOC,
                                                    lang_30074=LANGUAGE(30074)), heading=(LANGUAGE(32043)%(ADDON_NAME,ADDON_VERSION)),usemono=True,usethread=False)
        except Exception as e: self.log('showWelcome failed! %s'%(e), xbmc.LOGERROR)
        

    def showReadme(self):
        with busy_dialog():
            def convertMD2TXT(md):
                markdown = (re.sub(r'(\[[^][]*]\([^()]*\))|^(#+)(.*)', lambda x:x.group(1) if x.group(1) else "[COLOR=cyan][B]{1} {0} {1}[/B][/COLOR]".format(x.group(3),('#'*len(x.group(2)))), md, flags=re.M))
                markdown = (re.sub(r'`(.*?)`', lambda x:x.group(1) if not x.group(1) else '"[I]{0}[/I]"'.format(x.group(1)), markdown, flags=re.M))
                markdown = re.sub(r'\[!\[(.*?)\]\((.*?)\)]\((.*?)\)', lambda x:x.group(1) if not x.group(1) else '[B]{0}[/B]\n[I]{1}[/I]'.format(x.group(1),x.group(3)), markdown, flags=re.M)
                markdown = re.sub(r'\[(.*?)\]\((.*?)\)', lambda x:x.group(1) if not x.group(2) else '- [B]{0}[/B]\n[I]{1}[/I]'.format(x.group(1),x.group(2)), markdown, flags=re.M)
                markdown = re.sub(r'\[(.*?)\]\((.*?)\)', lambda x:x.group(1) if not x.group(1) else '- [B]{0}[/B]'.format(x.group(1)), markdown, flags=re.M)
                markdown = '\n'.join(list([filelist for filelist in markdown.split('\n') if filelist[:2] not in ['![','[!','!.','!-','ht']]))
                return markdown
        openAddonSettings((7,1))
        fle = FileAccess.open(README_FLE, "r")
        txt = fle.read()
        fle.close()
        try: DIALOG.textviewer(convertMD2TXT(txt), heading=(LANGUAGE(32043)%(ADDON_NAME,ADDON_VERSION)),usemono=True,usethread=True)
        except Exception as e: self.log('showReadme failed! %s'%(e), xbmc.LOGERROR)
   
   
    def showChangelog(self):
        with busy_dialog():
            def addColor(text):
                text = text.replace('-Added'      ,'[COLOR=green][B]-Added:[/B][/COLOR]')
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
        fle = FileAccess.open(CHANGELOG_FLE, "r")
        txt = fle.read()
        fle.close()
        try: DIALOG.textviewer(addColor(txt), heading=(LANGUAGE(32045)%(ADDON_NAME,ADDON_VERSION)),usemono=True, autoclose=30, usethread=True)
        except Exception as e: self.log('showChangelog failed! %s'%(e), xbmc.LOGERROR)
   
   
    def openChannelManager(self, chnum=-1):
        self.log('openChannelManager, chnum = %s'%(chnum))
        if not isRunning('MANAGER_RUNNING'):
            with setRunning('MANAGER_RUNNING'), suspendActivity():
                from manager import Manager
                chmanager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", channel=chnum)
                del chmanager
        
        
    def openChannelBug(self):
        self.log('openChannelBug')
        if not PROPERTIES.getEXTProperty('%s.OVERLAY_CHANNELBUG'%(ADDON_ID)) == 'true':
            from channelbug import ChannelBug
            channelbug = ChannelBug("%s.channelbug.xml"%(ADDON_ID), ADDON_PATH, "default")
            del channelbug


    def scanLibrary(self):
        from library import Library 
        library = Library()
        library.updateLibrary(force=True)
        del library


    def buildMenu(self, select=None):
        items = [{'label':LANGUAGE(32117),'label2':LANGUAGE(32120),'icon':COLOR_LOGO,'func':self.deleteFiles          ,'args':(LANGUAGE(32120),False)},    #"Rebuild M3U/XMLTV"
                 {'label':LANGUAGE(32118),'label2':LANGUAGE(32119),'icon':COLOR_LOGO,'func':self.deleteFiles          ,'args':(LANGUAGE(32119),True)},     #"Clean Start"
                 {'label':LANGUAGE(32121)%(PVR_CLIENT_NAME),'label2':LANGUAGE(32122) ,'icon':COLOR_LOGO,'func':brutePVR}, #"Force PVR reload"
                 {'label':LANGUAGE(32123),'label2':LANGUAGE(32124),'icon':COLOR_LOGO,'func':setPendingRestart},                                            #"Force PTVL reload"
                 {'label':LANGUAGE(32154),'label2':LANGUAGE(32154),'icon':COLOR_LOGO,'func':self.showFile             ,'args':(M3UFLEPATH,)},              #"Show M3U"
                 {'label':LANGUAGE(32155),'label2':LANGUAGE(32155),'icon':COLOR_LOGO,'func':self.showFile             ,'args':(XMLTVFLEPATH,)},            #"Show XMLTV"
                 {'label':LANGUAGE(32159),'label2':LANGUAGE(33159),'icon':COLOR_LOGO,'func':self.scanLibrary},
                 ]            

        with busy_dialog():
            listItems = [LISTITEMS.buildMenuListItem(item.get('label'),item.get('label2'),item.get('icon')) for item in sorted(items,key=lambda x:x['label'])]
            if select is None: 
                select = DIALOG.selectDialog(listItems, '%s - %s'%(ADDON_NAME,LANGUAGE(32126)),multi=False)
            
        if not select is None:
            try: 
                selectItem = [item for item in items if item.get('label') == listItems[select].getLabel()][0]
                self.log('buildMenu, selectItem = %s'%selectItem)
                if selectItem.get('args'): 
                    selectItem['func'](*selectItem['args'])
                else: 
                    selectItem['func']()
            except Exception as e: 
                self.log("buildMenu, failed! %s"%(e), xbmc.LOGERROR)
                return DIALOG.notificationDialog(LANGUAGE(32000))
        else: openAddonSettings((7,1))
                


    def deleteFiles(self, msg, full=False):
        self.log('deleteFiles, full = %s'%(full))
        files = {LANGUAGE(30094):M3UFLEPATH,    #"M3U"
                 LANGUAGE(30095):XMLTVFLEPATH,  #"XMLTV"
                 LANGUAGE(30096):GENREFLEPATH,  #"Genre"
                 LANGUAGE(30108):CHANNELFLEPATH,#"Channels"
                 LANGUAGE(32041):LIBRARYFLEPATH}#"Library"

        keys = list(files.keys())
        if not full: keys = keys[:2]
        if DIALOG.yesnoDialog('%s ?'%(msg)): 
            with busy_dialog():
                [DIALOG.notificationDialog(LANGUAGE(32127)%(key.replace(':',''))) for key in keys if FileAccess.delete(files[key])]
        if full: setPendingRestart()


    # def clearImport(self):
        # self.log('clearImport') 
        # keys = ['Import_M3U','Import_M3U_FILE','Import_M3U_URL',
                # 'Import_XMLTV','Import_XMLTV_FILE','Import_XMLTV_URL','Import_XMLTV_M3U'
                # 'Import_Provider']
                
        # with busy_dialog():
            # for key in keys: SETTINGS.setSetting(key,'')
            # SETTINGS.setSetting('User_Import','false')
            # DIALOG.notificationDialog('%s %s'%(LANGUAGE(30037),LANGUAGE(30053)))

    def run(self):  
        ctl = (7,1) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))
        
        if param == 'Apply_PVR_Settings':
            ctl = (7,9)
            with busy_dialog():
                if SETTINGS.chkPluginSettings(PVR_CLIENT_ID,IPTV_SIMPLE_SETTINGS(),override=True):
                    DIALOG.notificationDialog(LANGUAGE(32152))
                else:
                    DIALOG.notificationDialog(LANGUAGE(32046))
        elif param.startswith('Channel_Manager'):
            ctl = (0,1)
            self.openChannelManager()
        elif param.startswith('Move_Channelbug'):
            ctl = (5,5)
            self.openChannelBug()
        elif param == 'Show_Welcome':
            with busy_dialog():
                return self.showWelcome()
        elif param == 'Show_Readme':  
            with busy_dialog():
                return self.showReadme()
        elif param == 'Show_Changelog':
            return self.showChangelog()
        elif param == 'User_Groups':
            return self.userGroups()
        elif param == 'Utilities':
            return self.buildMenu()
        # elif param == 'Clear_Import':
            # ctl = (2,7)
            # self.clearImport()
        # elif param == 'Install_Resources': chkResources()
        # else: 
            # with busy_dialog():
                # PROPERTIES.setProperty('utilities',param)
                # xbmc.Monitor().waitForAbort(2)
                # return
        return openAddonSettings(ctl)

        # # ('ReplaceWindow(pvrsettings)') #todo open pvr settings.
if __name__ == '__main__': Utilities(sys.argv).run()
    
    