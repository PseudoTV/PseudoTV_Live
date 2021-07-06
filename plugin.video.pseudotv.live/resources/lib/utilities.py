#   Copyright (C) 2021 Lunatixz
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


    def buildMenu(self, select=None):
        with busy():
            PVR_NAME = getPluginMeta(PVR_CLIENT).get('name','')
            items    = [{'label':LANGUAGE(30010)              ,'label2':LANGUAGE(30011)             ,'icon':COLOR_LOGO,'func':self.deleteFiles,'args':(LANGUAGE(30011), False)}, #"Rebuild M3U/XMLTV"
                        {'label':LANGUAGE(30096)              ,'label2':LANGUAGE(30309)             ,'icon':COLOR_LOGO,'func':self.deleteFiles,'args':(LANGUAGE(30096), True)},  #"Clean Start"
                        {'label':LANGUAGE(30012)%(PVR_NAME)   ,'label2':LANGUAGE(30145)             ,'icon':COLOR_LOGO,'func':configurePVR},                                     #"Reconfigure PVR for use with PTVL"
                        {'label':LANGUAGE(30065)%(PVR_NAME)   ,'label2':LANGUAGE(30310)             ,'icon':COLOR_LOGO,'func':brutePVR},                                         #"Force PVR reload"
                        {'label':LANGUAGE(30065)%(ADDON_NAME) ,'label2':LANGUAGE(30311)%(ADDON_NAME),'icon':COLOR_LOGO,'func':setRestartRequired}]                               #"Force PTVL reload"

            listItems = [self.dialog.buildMenuListItem(item.get('label'),item.get('label2'),item.get('icon')) for item in items]
            if not select: select = self.dialog.selectDialog(listItems, '%s - %s'%(ADDON_NAME,'Select utility to perform'),multi=False)
            if select:
                try: 
                    selectItem = items[findItemsInLST(items,[listItems[select].getLabel()],item_key='label')[0]]
                    self.log('buildMenu, selectItem = %s'%selectItem)
                    if selectItem.get('args'): 
                        return selectItem['func'](*selectItem['args'])
                    else: 
                        return selectItem['func']()
                except Exception as e: 
                    self.log("buildMenu, Failed! %s"%(e), xbmc.LOGERROR)
                    return self.dialog.notificationDialog(LANGUAGE(30001))


    def userGroups(self):
        self.log('userGroups')
        with busy():
            retval = self.dialog.inputDialog(LANGUAGE(30076), default=SETTINGS.getSetting('User_Groups'))
            if not retval: return
            SETTINGS.setSetting('User_Groups',retval)
            return self.dialog.notificationDialog(LANGUAGE(30053))
            

    def clearImport(self):
        self.log('clearImport') 
        with busy_dialog():
            SETTINGS.setSetting('Import_M3U'       ,'')
            SETTINGS.setSetting('Import_M3U_FILE'  ,'')
            SETTINGS.setSetting('Import_M3U_URL'   ,'')
            SETTINGS.setSetting('Import_XMLTV'     ,'')
            SETTINGS.setSetting('Import_XMLTV_FILE','')
            SETTINGS.setSetting('Import_XMLTV_URL' ,'')
            SETTINGS.setSetting('Import_Provider'  ,'')
            SETTINGS.setSetting('User_Import'      ,'false')
            setPendingChange()#setRestartRequired()
            return self.dialog.notificationDialog(LANGUAGE(30053))


    def deleteFiles(self, msg, full=False):
        self.log('deleteFiles, full = %s'%(full))
        with busy():
            files = {LANGUAGE(30172):getUserFilePath(M3UFLE),    #"M3U"
                     LANGUAGE(30173):getUserFilePath(XMLTVFLE),  #"XMLTV"
                     LANGUAGE(30009):getUserFilePath(CHANNELFLE),#"Channels"
                     LANGUAGE(30179):getUserFilePath(LIBRARYFLE)}#"Library"

            keys = list(files.keys())
            if not full: keys = keys[:2]
            if self.dialog.yesnoDialog('%s ?'%(msg)): 
                with busy_dialog():
                    for key in keys:
                        if FileAccess.delete(files[key]):
                            self.dialog.notificationDialog(LANGUAGE(30016)%(key))
            if full: 
                setAutoTuned(False)
                setPendingChange()#setRestartRequired()


    def run(self):  
        ctl = (0,0) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))
        
        if isBusy():
            self.dialog.notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            return SETTINGS.openSettings()

        if    param is None: self.buildMenu(param)
        elif  param == 'Show_Readme':       showReadme()
        elif  param == 'Show_Changelog':    showChangelog()
        elif  param == 'User_Groups':       self.userGroups()
        elif  param == 'Clear_Import':      self.clearImport()
        elif  param == 'Install_Resources': chkResources()
        else: setUtilities(param)
            
if __name__ == '__main__': Utilities(sys.argv).run()
    
    