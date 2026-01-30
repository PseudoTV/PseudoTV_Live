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

from globals    import *
from library    import Library
from channels   import Channels

class Autotune(object):    
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG  = sysARG 
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _runTune(self, silent=False, count=AUTOTUNE_LIMIT):
        def __buildAutotune(type: str, count):
            items   = randomSamples(Library().getLibrary(type),count)
            isRadio = True if type == "Music Genres" else False
            self.log(f'_runTune: __buildAutotune, type = {type}, items = {len(items)}, isRadio = {isRadio}')
            for idx, item in enumerate(items):
                chnum = numbers.pop(0)
                citem = channels.getTemplate()
                citem.update({"id"      : getChannelID(item['name'],item['path'],chnum),
                              "type"    : type,
                              "number"  : chnum,
                              "name"    : getChannelSuffix(item['name'], type),
                              "logo"    : item.get('logo'),
                              "path"    : item.get('path',''),
                              "group"   : [item.get('type','')],
                              "rules"   : item.get('rules',{}),
                              "catchup" : ('vod' if not isRadio else ''),
                              "radio"   : isRadio,
                              "favorite": False})
                self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, '%s: %s%%'%(self.pMSG,int((idx)*100//len(items))), header=self.pHeader)
                channels.addChannel(citem)
            return channels.setChannels()
            
        hasChannels = PROPERTIES.hasChannels()
        hasLibrary  = any([PROPERTIES.hasLibrary(ty) for ty in AUTOTUNE_TYPES])
        self.log(f'_runTune, hasChannels = {hasChannels}, hasLibrary = {hasLibrary}')
        if not hasChannels and hasLibrary:
            with PROPERTIES.interruptActivity():
                if not silent:
                    opt = ''
                    msg = '%s?'%(LANGUAGE(32042)%(ADDON_NAME))
                    hasBackup  = PROPERTIES.hasBackup()
                    hasServers = PROPERTIES.hasServers()
                    self.log(f'_runTune, hasBackup = {hasBackup}, hasServers = {hasServers}')
                    if (hasBackup or hasServers):
                        opt = LANGUAGE(32254)
                        msg = '%s\n%s'%(LANGUAGE(32042)%(ADDON_NAME),LANGUAGE(32255))
                        
                    while not MONITOR().abortRequested():
                        retval = DIALOG.yesnoDialog(message=msg,customlabel=opt)
                        if   retval == 0: return True #No
                        elif retval == 1: break       #Yes
                        elif retval == 2:             #Custom
                            with BUILTIN.busy_dialog():
                                menu = [LISTITEMS.buildMenuListItem(LANGUAGE(30107),LANGUAGE(33310),url='special://home/addons/%s/resources/lib/utilities.py, Channel_Manager'%(ADDON_ID))]
                                if hasBackup:  menu.append(LISTITEMS.buildMenuListItem('%s %s'%(LANGUAGE(32112),LANGUAGE(30108)),LANGUAGE(32111),url='special://home/addons/%s/resources/lib/backup.py, Recover_Backup'%(ADDON_ID)))
                                if hasServers: menu.append(LISTITEMS.buildMenuListItem(LANGUAGE(30173),LANGUAGE(32215),url='special://home/addons/%s/resources/lib/multiroom.py, Select_Server_Client'%(ADDON_ID)))
                            select = DIALOG.selectDialog(menu,multi=False)
                            if not select is None: return BUILTIN.executescript(menu[select].getPath())
                        else: return False #Cancel

                self.pMSG    = ""
                self.pHeader = '%s, %s'%(ADDON_NAME,LANGUAGE(32021))
                channels     = Channels(writable=True)
                numbers      = list(range(1,CHANNEL_LIMIT))
                with BUILTIN.busy_dialog(), DIALOG._progressDialog(self.pMSG, self.pHeader, silent) as self.pDialog:
                    for idx, type in enumerate(AUTOTUNE_TYPES):
                        self.pMSG    = type
                        self.pCount  = int(idx+1*100//len(AUTOTUNE_TYPES))
                        self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, self.pMSG, header=self.pHeader)
                        __buildAutotune(type,count)
                timerit(PROPERTIES.setPropTimer)(FIFTEEN,*('chkChannels',True))
                del channels
        return True
        
 
    def clrLibrary(self):
        Library().clrLibraryCache()
        DIALOG.notificationDialog(LANGUAGE(32025))
       
       
    def clrBlacklist(self):
        SETTINGS.setSetting('Clear_BlackList','')
        DIALOG.notificationDialog(LANGUAGE(32025))
        
        
    def run(self):  
        with BUILTIN.busy_dialog():
            ctl = (1,1) #settings return focus
            try:    param = self.sysARG[1]
            except: param = None
            if param.replace('_',' ') in AUTOTUNE_TYPES:
                ctl = (1,AUTOTUNE_TYPES.index(param.replace('_',' '))+1)
                self.selectAutotune(param.replace('_',' '))
            elif param == 'Clear_Autotune' :  self.clrLibrary()
            elif param == 'Clear_BlackList':  self.clrBlacklist()
            elif param == None: return
            return SETTINGS.openSettings(ctl)
        
if __name__ == '__main__': Autotune(sys.argv).run()
