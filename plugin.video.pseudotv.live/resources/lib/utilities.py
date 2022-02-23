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

# -*- coding: utf-8 -*-
from resources.lib.globals     import *

class Utilities:
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG  = sysARG
        self.dialog  = Dialog()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def deleteFiles(self, msg, full=False):
        self.log('deleteFiles, full = %s'%(full))
        with busy():
            files = {LANGUAGE(30172):M3UFLEPATH,    #"M3U"
                     LANGUAGE(30173):XMLTVFLEPATH,  #"XMLTV"
                     LANGUAGE(30009):CHANNELFLEPATH,#"Channels"
                     LANGUAGE(30179):LIBRARYFLEPATH}#"Library"

            keys = list(files.keys())
            if not full: keys = keys[:2]
            if self.dialog.yesnoDialog('%s ?'%(msg)): 
                with busy_dialog():
                    [self.dialog.notificationDialog(LANGUAGE(30016)%(key)) for key in keys if FileAccess.delete(files[key])]
            if full: 
                setRestartRequired()


    def buildMenu(self, select=None):
        with busy():
            PVR_NAME = getPluginMeta(PVR_CLIENT).get('name','')
            items    = [{'label':LANGUAGE(30010)              ,'label2':LANGUAGE(30011)             ,'icon':COLOR_LOGO,'func':self.deleteFiles,'args':(LANGUAGE(30011), False)}, #"Rebuild M3U/XMLTV"
                        {'label':LANGUAGE(30096)              ,'label2':LANGUAGE(30309)             ,'icon':COLOR_LOGO,'func':self.deleteFiles,'args':(LANGUAGE(30096), True)},  #"Clean Start"
                        {'label':LANGUAGE(30012)%(PVR_NAME)   ,'label2':LANGUAGE(30145)             ,'icon':COLOR_LOGO,'func':setPVR},                                     #"Reconfigure PVR for use with PTVL"
                        {'label':LANGUAGE(30065)%(PVR_NAME)   ,'label2':LANGUAGE(30310)             ,'icon':COLOR_LOGO,'func':brutePVR},                                         #"Force PVR reload"
                        {'label':LANGUAGE(30065)%(ADDON_NAME) ,'label2':LANGUAGE(30311)%(ADDON_NAME),'icon':COLOR_LOGO,'func':setRestartRequired}]                               #"Force PTVL reload"

            listItems = [self.dialog.buildMenuListItem(item.get('label'),item.get('label2'),item.get('icon')) for item in items]
            if select is None: 
                select = self.dialog.selectDialog(listItems, '%s - %s'%(ADDON_NAME,'Select utility to perform'),multi=False)
            
            if not select is None:
                try: 
                    selectItem = items[findItemsInLST(items,[listItems[select].getLabel()],item_key='label')[0]]
                    self.log('buildMenu, selectItem = %s'%selectItem)
                    if selectItem.get('args'): 
                        selectItem['func'](*selectItem['args'])
                    else: 
                        selectItem['func']()
                except Exception as e: 
                    self.log("buildMenu, Failed! %s"%(e), xbmc.LOGERROR)
                    return self.dialog.notificationDialog(LANGUAGE(30001))


    def userGroups(self):
        self.log('userGroups')
        with busy():
            retval = self.dialog.inputDialog(LANGUAGE(30076), default=SETTINGS.getSetting('User_Groups'))
            if retval: SETTINGS.setSetting('User_Groups',retval)
            

    def clearImport(self):
        self.log('clearImport') 
        keys = ['Import_M3U','Import_M3U_FILE','Import_M3U_URL',
                'Import_XMLTV','Import_XMLTV_FILE','Import_XMLTV_URL',
                'Import_Provider']
                
        with busy_dialog():
            for key in keys: SETTINGS.setSetting(key,'')
            SETTINGS.setSetting('User_Import','false')
            self.dialog.notificationDialog('%s %s'%(LANGUAGE(30037),LANGUAGE(30053)))


    def run(self):  
        ctl = (8,3) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))
        
        if param is None:
            return self.buildMenu(param)
        elif param == 'Show_Readme':  
            return showReadme()
        elif param == 'Show_Changelog':
            return showChangelog()
        elif param == 'User_Groups':
            return self.userGroups()
        elif param == 'Clear_Import':
            ctl = (2,7)
            self.clearImport()
        elif  param == 'Install_Resources': chkResources()
        else: 
            with busy_dialog():
                PROPERTIES.setProperty('utilities',param)
                return xbmc.Monitor().waitForAbort(2)
        return openAddonSettings(ctl)

                
if __name__ == '__main__': Utilities(sys.argv).run()
    
    