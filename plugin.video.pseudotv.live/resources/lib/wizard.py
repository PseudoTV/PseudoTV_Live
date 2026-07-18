  # Copyright (C) 2025 Lunatixz


# This file is part of PseudoTV Live.

# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
# https://github.com/xbmc/xbmc/blob/master/xbmc/input/actions/ActionIDs.h
# https://github.com/xbmc/xbmc/blob/master/xbmc/input/Key.h

# -*- coding: utf-8 -*-
from typing import Generator, Optional
from variables  import *

# https://github.com/PseudoTV/PseudoTV_Live/issues/68

#todo move autotuning/startup to wizard.

#display welcome
#search discovery
#parse library
#prompt autotune



# if SETTINGS.hasWizardRun():
        # DIALOG.qrDialog(URL_WIKI,LANGUAGE(32216).format(name=ADDON_NAME,author=ADDON_AUTHOR))

class Wizard(xbmcgui.WindowXMLDialog):
    lastActionTime = time.time()
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)    
        with Globals.builtin.busy_dialog():
            self.tasks   = kwargs.get('inherited')
            self.cache   = Globals.settings.cache    
            self.cacheDB = Globals.settings.cacheDB
            self.player  = PLAYER()
            self.monitor = MONITOR()
            
        if not Globals.properties.isRunning('chkWizard'):
            with Globals.properties.chkRunning('chkWizard'):
                self.doModal()
            
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def onInit(self):
        self.log('onInit')  

        
    def isLocked(self) -> bool:
        return Globals.properties.getProperty('Wizard.isLocked',False)
        
        
    def setLocked(self, state: bool = True):
        self.getControl(41).setColorDiffuse({True:"0xC0FF0000",False:"0xFFFFFFFF"}[Globals.properties.setProperty('Wizard.isLocked',state)])


    @contextmanager
    def toggleSpinner(self, state: bool = True, lock: bool = True, condition: Optional[bool] = None) -> Generator:
        # Shows/hides spinner with optional locking; yields if condition is met, else yields immediately
        self.log('toggleSpinner, state = %s, condition = %s, lock = %s'%(state,condition,lock))
        if not condition is None and condition:
            Globals.properties.setRunning('Manager.toggleSpinner',state)
            self.setVisibility(self.spinner,state)
            if lock: self.setLocked(True)
            try: yield
            finally:
                if self.isLocked(): self.setLocked(False)
                self.setVisibility(self.spinner,False)
                Globals.properties.setRunning('Manager.toggleSpinner',False)
        else: yield


    def onClose(self):
        self.close()
        
        
    def onAction(self, act: xbmcgui.Action):
        actionId = act.getId()   
        if (time.time() - self.lastActionTime) < .5 and actionId not in ACTION_PREVIOUS_MENU: pass # during certain times we just want to discard all input
        else:
            if actionId in ACTION_PREVIOUS_MENU:
                if self.isLocked(): Globals.dialog.notificationDialog(LANGUAGE(32260))
            else:
                with self.toggleSpinner(condition=Globals.properties.isRunning('Wizard.toggleSpinner')==False):
                    self.log('onAction: actionId = %s, locked = %s'%(actionId,self.isLocked()))

            
    def onFocus(self, controlId: int):
        self.log('onFocus: controlId = %s'%(controlId))

        
    def onClick(self, controlId: int):
        if (self.isLocked() or (time.time() - self.lastActionTime) < .5): Globals.dialog.notificationDialog(LANGUAGE(32260))
        else:
            with self.toggleSpinner(condition=Globals.properties.isRunning('Wizard.toggleSpinner')==False):
                self.log('onClick: controlId = %s, locked = %s'%(controlId,self.isLocked()))
                if controlId == 0: self.onClose()
