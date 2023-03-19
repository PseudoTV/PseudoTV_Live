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
    def __init__(self, sysARG=sys.argv):
        self.log('__init__, sysARG = %s'%(sysARG))
        self.sysARG   = sysARG
        self.library  = Library()
        self.channels = Channels()
        
                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def getAutotuned(self):
        return self.channels.getAutotuned()


    def _runTune(self, samples=False, rebuild=True):
        self.log('_runTune, samples = %s, rebuild = %s'%(samples,rebuild))
        if   isClient(): return
        elif samples:
            if hasAutotuned() or len(self.getAutotuned()) != 0: return #don't create samples when channels exist or prompt already displayed.
            else:
                opt = ''
                msg = (LANGUAGE(32042)%ADDON_NAME)
                if PROPERTIES.getPropertyBool('has.Backup'):
                    opt = LANGUAGE(32112)
                    msg = '%s\n%s'%((LANGUAGE(32042)%ADDON_NAME),LANGUAGE(32111))
                retval = DIALOG.yesnoDialog(message=msg,customlabel=opt,autoclose=90000)
                if retval == 1:
                    dia = DIALOG.progressBGDialog(header='%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(32021),LANGUAGE(30038))))
                elif retval == 2: return Backup().recoverChannels()
                else: return
                
        for idx, type in enumerate(AUTOTUNE_TYPES): 
            if samples: dia = DIALOG.progressBGDialog(int((idx+1)*100//len(AUTOTUNE_TYPES)),dia,type,'%s, %s'%(ADDON_NAME,'%s %s'%(LANGUAGE(32021),LANGUAGE(30038))))
            self.selectAUTOTUNE(type, samples, rebuild)
        if samples: setAutotuned()
        

    def selectAUTOTUNE(self, type, autoSelect=False, rebuildChannels=False):
        self.log('selectAUTOTUNE, type = %s'%(type))
        if isClient(): return
        def _build(item):
            print(item)
            return LISTITEMS.buildMenuListItem(item['name'],item['type'],item['logo'])
        
        def _match(enabledItems):
            for item in enabledItems:
                for idx, liz in enumerate(lizlst):
                    if item.get('name').lower() == liz.getLabel().lower():
                        yield idx

        def _set(selects=[]):
            for item in items:
                item['enabled'] = False #disable everything before selecting new items.
                for select in selects:
                    if item.get('name').lower() == lizlst[select].getLabel().lower():
                        item['enabled'] = True
            self.library.setLibrary(type, items)
           
        items = self.library.getLibrary(type)
        print(items)
        if len(items) == 0 and (not rebuildChannels and not autoSelect): 
            return DIALOG.notificationDialog(LANGUAGE(32018)%(type))
        
        lizlst = poolit(_build)(items)
        if rebuildChannels:#rebuild channels.json entries
            selects = list(_match(self.library.getEnabled(type)))
        elif autoSelect:#build sample channels
            if len(items) >= AUTOTUNE_LIMIT:
                selects = list(set(random.sample(list(set(range(0,len(items)))),AUTOTUNE_LIMIT)))
            else: 
                selects = list(range(0,len(items)))
        else:
            selects = DIALOG.selectDialog(lizlst,LANGUAGE(32017)%(type),preselect=list(_match(self.library.getEnabled(type))))
        
        if not selects is None: _set(selects)
        return self.buildAUTOTUNE(type, self.library.getEnabled(type))
        
        
    def buildAUTOTUNE(self, type, items):
        def buildAvailableRange(existing):
            # create number array for given type, excluding existing channel numbers.
            if existing:
                existingNUMBERS = [eitem.get('number') for eitem in existing if eitem.get('number',0) > 0] # existing channel numbers
            else:
                existingNUMBERS = []
            start = ((CHANNEL_LIMIT+1)*(AUTOTUNE_TYPES.index(type)+1))
            stop  = (start + CHANNEL_LIMIT)
            self.log('buildAUTOTUNE, type = %s, range = %s-%s, existingNUMBERS = %s'%(type,start,stop,existingNUMBERS))
            return [num for num in range(start,stop) if num not in existingNUMBERS]
                  
        existingAUTOTUNE = self.channels.popChannels(type,self.getAutotuned())
        usesableNUMBERS  = iter(buildAvailableRange(existingAUTOTUNE)) # available channel numbers
        for item in items:
            music = isRadio(item)
            citem = self.channels.getTemplate()
            citem.update({"id"      : "",
                          "type"    : type,
                          "number"  : 0,
                          "name"    : getChannelSuffix(item['name'], type),
                          "logo"    : item['logo'],
                          "path"    : item['path'],
                          "group"   : [item['type']],
                          "rules"   : [],
                          "catchup" : ('vod' if not music else ''),
                          "radio"   : music,
                          "favorite": True})
                          
            match, eitem = self.channels.findChannel(citem, channels=existingAUTOTUNE)
            if match is None:
                citem['number'] = next(usesableNUMBERS,0)
                citem['id']     = getChannelID(citem['name'],citem['path'],citem['number'])
            else:
                citem['number']   = eitem.get('number') 
                citem['id']       = eitem.get('id')
                citem['favorite'] = eitem.get('favorite')
            self.channels.addChannel(citem)
        return self.channels._save()
       

    def run(self):  
        ctl = (1,1) #settings return focus
        try:    param = self.sysARG[1]
        except: param = None
        self.log('run, param = %s'%(param))
        if param.replace('_',' ') in AUTOTUNE_TYPES:
            ctl = (1,AUTOTUNE_TYPES.index(param.replace('_',' '))+1)
            self.selectAUTOTUNE(param.replace('_',' '))
        return openAddonSettings(ctl)
        
if __name__ == '__main__': Autotune(sys.argv).run()