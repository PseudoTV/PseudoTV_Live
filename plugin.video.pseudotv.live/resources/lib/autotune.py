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


    def _runTune(self, manager=False, start=1, count=AUTOTUNE_CHANNEL_DEFAULT):
        def __buildAutotune(type: str, count):
            citems  = []
            items   = library.getLibrary(type)
            items   = Globals._randomSamples(items,count)
            isRadio = True if type == "Music Genres" else False
            self.log(f'_runTune: __buildAutotune, type = {type}, items = {len(items)}, isRadio = {isRadio}')
            for idx, item in enumerate(items):
                if len(numbers) > 0:
                    chnum = numbers.pop(0)
                    citem = template.copy()
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
                    citems.append(citem)
            return citems
            
        hasChannels = PROPERTIES.hasChannels()
        hasLibrary  = any([PROPERTIES.hasLibrary(ty) for ty in AUTOTUNE_TYPES])
        if count > AUTOTUNE_CHANNEL_LIMIT: count = AUTOTUNE_CHANNEL_DEFAULT
        self.log(f'_runTune, manager = {manager}, start = {start}, Count = {count}, hasChannels = {hasChannels}, hasLibrary = {hasLibrary}')
        if not hasChannels and hasLibrary:
            if not manager:
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
            
            channels     = Channels()
            template     = channels.getTemplate()
            xchannels    = channels.getChannels() 
            del channels
            
            xnumbers     = [ch.get('number',0) for ch in xchannels]
            xrange       = list(range(1, CHANNEL_LIMIT+1))
            numbers      = [num for num in xrange if num+1 not in xnumbers]
            numbers      = numbers[start-1:] + numbers[:start-1]
            citems       = []
            with DIALOG._progressDialog(self.pMSG, self.pHeader, manager) as self.pDialog:
                library = Library()
                for idx, type in enumerate(AUTOTUNE_TYPES):
                    self.pMSG    = type
                    self.pCount  = int(idx*100//len(AUTOTUNE_TYPES))
                    self.pDialog = DIALOG._updateProgress(self.pDialog, self.pCount, self.pMSG, header=self.pHeader)
                    citems.extend([item for item in __buildAutotune(type,count) if item])
                del library
            if manager: return citems
            elif len(citems) > 0:
                channels = Channels(writable=True)
                channels.addChannel(citems)
                state = channels.setChannels(channels.getChannels())
                del channels
                timerit(PROPERTIES.setPropTimer)(FIFTEEN,['chkChanged'])#trigger channel building
                return state
                
 
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
            except Exception: param = None
            if param.replace('_',' ') in AUTOTUNE_TYPES:
                ctl = (1,AUTOTUNE_TYPES.index(param.replace('_',' '))+1)
                self.selectAutotune(param.replace('_',' '))
            elif param == 'Clear_Autotune' :  self.clrLibrary()
            elif param == 'Clear_BlackList':  self.clrBlacklist()
            elif param == None: return
            return Globals._openSettings(ctl)
        
if __name__ == '__main__': Autotune(sys.argv).run()
