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

from globals    import *
from library    import Library
from channels   import Channels
from backup     import Backup

class Autotune:
    def __init__(self, sysARG=sys.argv, service=None):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG   = sysARG
        self.library  = Library(service)
        self.channels = Channels()
        
                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getAutotuned(self):
        #return autotuned channels ie. channels > CHANNEL_LIMIT
        channels = self.channels.getAutotuned()
        self.log('getAutotuned, channels = %s'%(len(channels)))
        return channels


    def _runTune(self, samples=False, rebuild=False, dia=None):
        self.log('_runTune, samples = %s'%(samples))
        if not hasAutotuned() and not isClient():
            setAutotuned()
            autoChannels = self.getAutotuned()
            if len(autoChannels) == 0 and samples:
                opt = ''
                msg = (LANGUAGE(32042)%ADDON_NAME)
                if Backup().hasBackup():
                    opt = LANGUAGE(32112)
                    msg = '%s\n%s'%((LANGUAGE(32042)%ADDON_NAME),LANGUAGE(32111))
                retval = DIALOG.yesnoDialog(message=msg,customlabel=opt,autoclose=90)
                if   retval == 1: dia = DIALOG.progressBGDialog(header='%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(32021),LANGUAGE(30038))))
                elif retval == 2: return Backup().recoverChannels()
                else: return
            elif len(autoChannels) > 0:
                samples = False
                rebuild = True
            
            if samples or rebuild:
                PROPERTIES.setEXTProperty('plugin.video.pseudotv.live.has.Predefined',True)
                for idx, ATtype in enumerate(AUTOTUNE_TYPES): 
                    if samples and dia: dia = DIALOG.progressBGDialog(int((idx+1)*100//len(AUTOTUNE_TYPES)),dia,ATtype,'%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(32021),LANGUAGE(30038))))
                    self.selectAUTOTUNE(ATtype, autoSelect=samples, rebuildChannels=rebuild)


    def selectAUTOTUNE(self, ATtype, autoSelect=False, rebuildChannels=False):
        self.log('selectAUTOTUNE, ATtype = %s'%(ATtype))
        def _build(item):
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
           
        if not isClient():
            items = self.library.getLibrary(ATtype)
            if len(items) == 0 and (not rebuildChannels and not autoSelect): 
                return DIALOG.notificationDialog(LANGUAGE(32018)%(ATtype))
            
            lizlst = [_build(item) for item in items]
            if rebuildChannels:#rebuild channels.json entries
                selects = list(_match(self.library.getEnabled(ATtype)))
            elif autoSelect:#build sample channels
                if len(items) >= AUTOTUNE_LIMIT:
                    selects = sorted(list(set(random.sample(list(set(range(0,len(items)))),AUTOTUNE_LIMIT))))
                else: 
                    selects = list(range(0,len(items)))
            else:
                selects = DIALOG.selectDialog(lizlst,LANGUAGE(32017)%(ATtype),preselect=list(_match(self.library.getEnabled(ATtype))))
            
            if not selects is None: _set(ATtype, selects)
            return self.buildAUTOTUNE(ATtype, self.library.getEnabled(ATtype))
        
        
    def buildAUTOTUNE(self, ATtype, items):
        def buildAvailableRange(existing):
            # create number array for given type, excluding existing channel numbers.
            if existing:
                existingNUMBERS = [eitem.get('number') for eitem in existing if eitem.get('number',0) > 0] # existing channel numbers
            else:
                existingNUMBERS = []
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
                          "logo"    : item['logo'],
                          "path"    : item['path'],
                          "group"   : [item['type']],
                          "rules"   : [],
                          "catchup" : ('vod' if not music else ''),
                          "radio"   : music,
                          "favorite": True})
                          
            match, eitem = self.channels.findAutotune(citem, channels=existingAUTOTUNE)
            if match is None:
                citem['number'] = next(usesableNUMBERS,0)
                citem['id']     = getChannelID(citem['name'],citem['path'],citem['number'])
            else:
                citem['number']   = eitem.get('number') 
                citem['id']       = eitem.get('id')
                citem['favorite'] = eitem.get('favorite')
            self.channels.addChannel(citem)
        return self.channels.setChannels()
       
       
    def clearLibrary(self):
        self.library.resetLibrary()
        DIALOG.notificationDialog(LANGUAGE(32025))
       
       
    def clearBlacklist(self):
        SETTINGS.setSetting('Clear_BlackList','')
        DIALOG.notificationDialog(LANGUAGE(32025))
        
        
    def run(self):  
        ctl = (1,1) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))
        if param.replace('_',' ') in AUTOTUNE_TYPES:
            ctl = (1,AUTOTUNE_TYPES.index(param.replace('_',' '))+1)
            self.selectAUTOTUNE(param.replace('_',' '))
        elif param == 'Clear_Autotune' : self.clearLibrary()
        elif param == 'Clear_BlackList': self.clearBlacklist()
        return openAddonSettings(ctl)
        
if __name__ == '__main__': Autotune(sys.argv).run()