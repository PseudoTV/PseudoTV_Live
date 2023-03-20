#   Copyright (C) 2023 Lunatixz
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
from globals     import *
from manager     import Manager
from channelbug  import ChannelBug

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
                
                 
    def showReadme(self):
        def convertMD2TXT(md):
            markdown = (re.sub(r'(\[[^][]*]\([^()]*\))|^(#+)(.*)', lambda x:x.group(1) if x.group(1) else "[COLOR=cyan][B]{1} {0} {1}[/B][/COLOR]".format(x.group(3),('#'*len(x.group(2)))), md, flags=re.M))
            markdown = (re.sub(r'`(.*?)`', lambda x:x.group(1) if not x.group(1) else '"[I]{0}[/I]"'.format(x.group(1)), markdown, flags=re.M))
            markdown = re.sub(r'\[!\[(.*?)\]\((.*?)\)]\((.*?)\)', lambda x:x.group(1) if not x.group(1) else '[B]{0}[/B]\n[I]{1}[/I]'.format(x.group(1),x.group(3)), markdown, flags=re.M)
            markdown = re.sub(r'\[(.*?)\]\((.*?)\)', lambda x:x.group(1) if not x.group(2) else '- [B]{0}[/B]\n[I]{1}[/I]'.format(x.group(1),x.group(2)), markdown, flags=re.M)
            markdown = re.sub(r'\[(.*?)\]\((.*?)\)', lambda x:x.group(1) if not x.group(1) else '- [B]{0}[/B]'.format(x.group(1)), markdown, flags=re.M)
            markdown = '\n'.join(list(filter(lambda filelist:filelist[:2] not in ['![','[!','!.','!-','ht'], markdown.split('\n'))))
            return markdown
        try: DIALOG.textviewer(convertMD2TXT(xbmcvfs.File(README_FLE).read()), heading=(LANGUAGE(32043)%(ADDON_NAME,ADDON_VERSION)),usemono=True,usethread=True)
        except Exception as e: self.log('showReadme failed! %s'%(e), xbmc.LOGERROR)
   
   
    def showChangelog(self):
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
        try: DIALOG.textviewer(addColor(xbmcvfs.File(CHANGELOG_FLE).read()), heading=(LANGUAGE(32045)%(ADDON_NAME,ADDON_VERSION)),usemono=True,usethread=True)
        except Exception as e: self.log('showChangelog failed! %s'%(e), xbmc.LOGERROR)
   
   
    def openChannelManager(self, chnum=1):
        self.log('openChannelManager, chnum = %s'%(chnum))
        if not PROPERTIES.getPropertyBool('OVERLAY_MANAGER'):
            chmanager = Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default", channel=chnum)
            del chmanager
        
        
    def openChannelBug(self):
        self.log('openChannelBug')
        if not PROPERTIES.getPropertyBool('OVERLAY_CHANNELBUG'):
            channelbug = ChannelBug("%s.channelbug.xml"%(ADDON_ID), ADDON_PATH, "default")
            del channelbug


    def buildMenu(self, select=None):
        with busy_dialog():
            items    = [{'label':LANGUAGE(32117),'label2':LANGUAGE(32120),'icon':COLOR_LOGO,'func':self.deleteFiles          ,'args':(LANGUAGE(32120),False)}, #"Rebuild M3U/XMLTV"
                        {'label':LANGUAGE(32118),'label2':LANGUAGE(32119),'icon':COLOR_LOGO,'func':self.deleteFiles          ,'args':(LANGUAGE(32119),True)},  #"Clean Start"
                        {'label':LANGUAGE(32121)%(xbmcaddon.Addon(PVR_CLIENT).getAddonInfo('name')),'label2':LANGUAGE(32122),'icon':COLOR_LOGO,'func':brutePVR},                                                  #"Force PVR reload"
                        {'label':LANGUAGE(32123),'label2':LANGUAGE(32124),'icon':COLOR_LOGO,'func':PROPERTIES.setPropertyBool,'args':('pendingRestart',True)}] #"Force PTVL reload"

            listItems = [LISTITEMS.buildMenuListItem(item.get('label'),item.get('label2'),item.get('icon')) for item in items]
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
        if full: PROPERTIES.setPropertyBool('pendingRestart',True)


    # def clearImport(self):
        # self.log('clearImport') 
        # keys = ['Import_M3U','Import_M3U_FILE','Import_M3U_URL',
                # 'Import_XMLTV','Import_XMLTV_FILE','Import_XMLTV_URL','Import_XMLTV_M3U'
                # 'Import_Provider']
                
        # with busy_dialog():
            # for key in keys: SETTINGS.setSetting(key,'')
            # SETTINGS.setSetting('User_Import','false')
            # DIALOG.notificationDialog('%s %s'%(LANGUAGE(30037),LANGUAGE(30053)))

    
    def selectServer(self):
        self.log('selectServer')
        labels  = []
        servers = getDiscovery()
        epoch   = time.time()
        current = SETTINGS.getSetting('Remote_URL').strip('http://')
        
        try:    idx = list(servers.keys()).index(current)
        except: idx = 0
            
        for server in servers:
            offline = '(Offline)' if epoch >= (servers[server].get('received',epoch) + UPDATE_WAIT) else ''
            color   = 'dimgray' if offline else 'white'
            labels.append('[COLOR=%s]%s %s[/COLOR]'%(color,servers[server].get('name'),offline))
            
        select = DIALOG.selectDialog(labels, header=LANGUAGE(32048), preselect=idx, useDetails=False, autoclose=90000, multi=False)
        if select is not None:
            server = list(servers.keys())[select]
            chkDiscovery({server:servers[server]}, forced=True)


    def run(self):  
        ctl = (7,1) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))
        
        if param == 'Apply_Settings':
            ctl = (7,9)
            chkPluginSettings(PVR_CLIENT,IPTV_SIMPLE_SETTINGS(),silent=False)
        elif param.startswith('Channel_Manager'):
            ctl = (0,1)
            self.openChannelManager()
        elif param.startswith('Move_Channelbug'):
            ctl = (5,5)
            self.openChannelBug()
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
        elif param == 'Select_Server': 
            ctl = (7,7)
            self.selectServer()
        # elif param == 'Install_Resources': chkResources()
        # else: 
            # with busy_dialog():
                # PROPERTIES.setProperty('utilities',param)
                # xbmc.Monitor().waitForAbort(2)
                # return
        return openAddonSettings(ctl)

        # # ('ActivateWindow(pvrsettings)') #todo open pvr settings.
if __name__ == '__main__': Utilities(sys.argv).run()
    
    