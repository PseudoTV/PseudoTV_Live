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

from globals    import *
from library    import Library
from channels   import Channels

class Autotune:
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        if service is None: service = Service()
        self.sysARG   = sysARG 
        self.channels = Channels()
        self.library  = Library()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getCustom(self) -> dict:
        #return autotuned channels ie. channels > CHANNEL_LIMIT
        channels = self.channels.getCustom()
        self.log('getCustom, channels = %s'%(len(channels)))
        return channels


    def getAutotuned(self) -> dict:
        #return autotuned channels ie. channels > CHANNEL_LIMIT
        channels = self.channels.getAutotuned()
        self.log('getAutotuned, channels = %s'%(len(channels)))
        return channels


    def _runTune(self, samples: bool=False, rebuild: bool=False, dia=None):
        autoEnabled    = []
        customChannels = self.getCustom()
        autoChannels   = self.getAutotuned()
        hasAutotuned   = SETTINGS.hasAutotuned()
        self.log('_runTune, custom channels = %s,  autotune channels = %s,  has autotuned = %s'%(len(customChannels),len(autoChannels),hasAutotuned))
        
        if len(autoChannels) > 0: #rebuild existing autotune, no samples needed
            rebuild = True
            PROPERTIES.setEXTPropertyBool('%s.has.Predefined'%(ADDON_ID),True)
        elif len(customChannels) == 0 and not hasAutotuned: #begin check if samples needed
            [autoEnabled.extend(self.library.getEnabled(type)) for type in AUTOTUNE_TYPES]
            if len(autoEnabled) > 0:
                self.log('_runTune, library enabled items = %s; recovering enabled items'%(len(autoEnabled)))
                rebuild = True #recover empty channels.json with enabled library.json items.
            elif hasAutotuned: # autotune already ran once, manual only going forward
                return DIALOG.notificationDialog(LANGUAGE(32024))
            else:
                samples = True #create sample channels "autotune".
            
            if samples:
                hasBackup   = PROPERTIES.hasBackup()
                hasServers  = PROPERTIES.hasServers()
                hasChannels = PROPERTIES.hasChannels()
                
                if hasBackup:
                    opt = LANGUAGE(32112)
                    msg = '%s\n%s'%((LANGUAGE(32042)%ADDON_NAME),LANGUAGE(32111))
                elif hasServers:
                    opt = LANGUAGE(30092)
                    msg = '%s\n%s'%((LANGUAGE(32042)%ADDON_NAME),LANGUAGE(32215))
                else:
                    opt = ''
                    msg = (LANGUAGE(32042)%ADDON_NAME)
                
                retval = DIALOG.yesnoDialog(message=msg,customlabel=opt)
                if   retval == 1: dia = DIALOG.progressBGDialog(header='%s, %s'%(ADDON_NAME,LANGUAGE(32021))) #Yes
                elif retval == 2: #Custom
                    if   hasBackup:   return BUILTIN.executebuiltin('RunScript(special://home/addons/%s/resources/lib/backup.py, Recover_Channels)'%(ADDON_ID))
                    elif hasServers:  return BUILTIN.executebuiltin('RunScript(special://home/addons/%s/resources/lib/multiroom.py, Select_Server)'%(ADDON_ID))
                elif not hasChannels: return openAddonSettings() #No w/exception
                else: return True #No
        else: return True
            
        for idx, ATtype in enumerate(AUTOTUNE_TYPES): 
            if dia: dia = DIALOG.progressBGDialog(int((idx+1)*100//len(AUTOTUNE_TYPES)),dia,ATtype,'%s, %s'%(ADDON_NAME,LANGUAGE(32021)))
            self.selectAUTOTUNE(ATtype, autoSelect=samples, rebuildChannels=rebuild)
        return True
        

    def selectAUTOTUNE(self, ATtype: str, autoSelect: bool=False, rebuildChannels: bool=False):
        self.log('selectAUTOTUNE, ATtype = %s, autoSelect = %s, rebuildChannels = %s'%(ATtype,autoSelect,rebuildChannels))
        def __buildMenuItem(item):
            return LISTITEMS.buildMenuListItem(item['name'],item['type'],item['logo'])
        
        def _match(enabledItems):
            for item in enabledItems:
                for idx, liz in enumerate(lizlst):
                    if item.get('name').lower() == liz.getLabel().lower():
                        yield idx

        def _set(ATtype, selects=[]):
            for item in items:
                item['enabled'] = False #disable everything before selecting new items.
                for select in selects:
                    if item.get('name').lower() == lizlst[select].getLabel().lower():
                        item['enabled'] = True
            self.library.setLibrary(ATtype, items)
           
        items = self.library.getLibrary(ATtype)
        if len(items) == 0 and (not rebuildChannels and not autoSelect): 
            if SETTINGS.getSettingBool('Debug_Enable'): DIALOG.notificationDialog(LANGUAGE(32018)%(ATtype))
            return
        
        with BUILTIN.busy_dialog(rebuildChannels):
            lizlst = poolit(__buildMenuItem)(items)
            
        if rebuildChannels:#rebuild channels.json entries
            selects = list(_match(self.library.getEnabled(ATtype)))
        elif autoSelect:#build sample channels
            if len(items) >= AUTOTUNE_LIMIT:
                selects = sorted(set(random.sample(list(set(range(0,len(items)))),AUTOTUNE_LIMIT)))
            else: 
                selects = list(range(0,len(items)))
        else:
            selects = DIALOG.selectDialog(lizlst,LANGUAGE(32017)%(ATtype),preselect=list(_match(self.library.getEnabled(ATtype))))
        
        if not selects is None: _set(ATtype, selects)
        return self.buildAUTOTUNE(ATtype, self.library.getEnabled(ATtype))
        
        
    def buildAUTOTUNE(self, ATtype: str, items: list=[]):
        if not list: return
        def buildAvailableRange(existing):
            # create number array for given type, excluding existing channel numbers.
            if existing: existingNUMBERS = [eitem.get('number') for eitem in existing if eitem.get('number',0) > 0] # existing channel numbers
            else:        existingNUMBERS = []
            
            start = ((CHANNEL_LIMIT+1)*(AUTOTUNE_TYPES.index(ATtype)+1))
            stop  = (start + CHANNEL_LIMIT)
            self.log('buildAUTOTUNE, ATtype = %s, range = %s-%s, existingNUMBERS = %s'%(ATtype,start,stop,existingNUMBERS))
            return [num for num in range(start,stop) if num not in existingNUMBERS]
      
        existingAUTOTUNE = self.channels.popChannels(ATtype,self.getAutotuned())
        usesableNUMBERS  = iter(buildAvailableRange(existingAUTOTUNE)) # available channel numbers
        for item in items:
            music = isRadio(item)
            citem = self.channels.getTemplate()
            citem.update({"id"      : "",
                          "type"    : ATtype,
                          "number"  : 0,
                          "name"    : getChannelSuffix(item['name'], ATtype),
                          "logo"    : item.get('logo',LOGO),
                          "path"    : item.get('path',''),
                          "group"   : [item.get('type','')],
                          "rules"   : item.get('rules',{}),
                          "catchup" : ('vod' if not music else ''),
                          "radio"   : music,
                          "favorite": True})
                          
            match, eitem = self.channels.findAutotuned(citem, channels=existingAUTOTUNE)
            if match is None:
                citem['id']       = getChannelID(citem['name'],citem['path'],citem['number']) #generate new channelid
                citem['number']   = next(usesableNUMBERS,0) #first available channel number
            else:
                citem['id']       = eitem.get('id')
                citem['number']   = eitem.get('number')
                citem['logo']     = eitem.get('logo',citem.get('logo',LOGO))
                citem['favorite'] = eitem.get('favorite',False)
            self.channels.addChannel(citem)
            SETTINGS.setUpdateChannels(citem['id'])
        return self.channels.setChannels()
       
       
    def clearLibrary(self):
        self.library.resetLibrary()
        DIALOG.notificationDialog(LANGUAGE(32025))
       
       
    def clearBlacklist(self):
        SETTINGS.setSetting('Clear_BlackList','')
        DIALOG.notificationDialog(LANGUAGE(32025))
        
        
    def run(self):  
        with BUILTIN.busy_dialog():
            ctl = (1,1) #settings return focus
            try:    param = self.sysARG[1]
            except: param = None
            if param.replace('_',' ') in AUTOTUNE_TYPES:
                ctl = (1,AUTOTUNE_TYPES.index(param.replace('_',' '))+1)
                self.selectAUTOTUNE(param.replace('_',' '))
            elif param == 'Clear_Autotune' : self.clearLibrary()
            elif param == 'Clear_BlackList': self.clearBlacklist()
            elif param == None: return
            return openAddonSettings(ctl)
        
if __name__ == '__main__': Autotune(sys.argv).run()