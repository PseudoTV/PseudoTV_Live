  # Copyright (C) 2024 Lunatixz


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
from globals   import *
from jsonrpc   import JSONRPC


class OverlayTool(xbmcgui.WindowXMLDialog):
    focusControl   = None
    focusCycle     = None
    focusCycleLST  = []
    focusCNTRLST   = {}
    lastActionTime = time.time()
    posx, posy     = 0, 0
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.log('__init__, args = %s, kwargs = %s'%(args,kwargs))
        with BUILTIN.busy_dialog():
            self.jsonRPC = JSONRPC()
            if BUILTIN.getInfoBool('Playing','Player'): self.window = xbmcgui.Window(12005) 
            else:                                       self.window = xbmcgui.Window(10000) 
            self.window_h, self.window_w = (self.window.getHeight() , self.window.getWidth())
            
            self.advRule  = (kwargs.get("ADV_RULES") or False)
            self.focusIDX = (kwargs.get("Focus_IDX") or 1)
            
            self._defViewMode = self.jsonRPC.getViewMode()
            self._vinViewMode = (kwargs.get("Vignette_VideoMode") or self._defViewMode)
            self._vinImage    = (kwargs.get("Vignette_Image")     or os.path.join(MEDIA_LOC,'overlays','ratio.png'))
            
            self.channelBugDiffuse = '0x%s'%((kwargs.get("ChannelBug_Color") or SETTINGS.getSetting('ChannelBug_Color')))
            self.autoBugX, self.autoBugY = (abs(int(self.window_w // 8) - self.window_w) - 128, abs(int(self.window_h // 16) - self.window_h) - 128)
            try:    self.channelBugX, self.channelBugY = tuple(kwargs.get("Channel_Bug_Position_XY",SETTINGS.getSetting("Channel_Bug_Position_XY")))
            except: self.channelBugX, self.channelBugY = self.autoBugX, self.autoBugY

            self.onNextColor = '0x%s'%((kwargs.get("ON_Next_Color") or SETTINGS.getSetting("ON_Next_Color")))
            self.autoNextX, self.autoNextY = abs(int(self.window_w // 8)), abs(int(self.window_h // 16) - self.window_h)
            try:    self.onNextX, self.onNextY = tuple(kwargs.get("On_Next_Position_XY",SETTINGS.getSetting("On_Next_Position_XY")))
            except: self.onNextX, self.onNextY = self.autoNextX, self.autoNextY
            
        try: 
            # if isplaying() timerit(self.jsonRPC.setViewMode)(0.1,[self._defZoom, self._defVShift, self._defPratio, self._defNLS]) #todo add video mode changes
            if BUILTIN.getInfoBool('Playing','Player'): BUILTIN.executebuiltin('ActivateWindow(fullscreenvideo)')
            self.doModal()
        except Exception as e: self.log("__init__, failed! %s"%(e), xbmc.LOGERROR)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onInit(self):
        if not BUILTIN.getInfoBool('IsFullscreen','System'):
            DIALOG.okDialog(LANGUAGE(32097)%(BUILTIN.getInfoLabel('ScreenResolution','System')))
            
        self._overlayControl = xbmcgui.ControlImage(0, 0, self.window_w, self.window_h, self._vinImage, aspectRatio=0) #IDX 0
        self._addCntrl(self._overlayControl)  
        
        self._channelBug = xbmcgui.ControlImage(self.channelBugX, self.channelBugY, 128, 128, COLOR_LOGO, 2, self.channelBugDiffuse) #IDX 1
        self._addCntrl(self._channelBug)
        self.posx, self.posy = self._channelBug.getX(),self._channelBug.getY()
        
        self._onNext = xbmcgui.ControlTextBox(self.onNextX, self.onNextY, abs(int(self.window_w // 2)), abs(int(self.window_h // 32)), 'font12', self.onNextColor) #IDX 2
        self._onNext.setText('%s\n%s'%(LANGUAGE(32104)%(ADDON_NAME),LANGUAGE(32116)%(ADDON_NAME)))
        self._addCntrl(self._onNext)

        self.focusCycleLST.insert(0,self.focusCycleLST.pop(self.focusIDX))
        self.focusCycle = cycle(self.focusCycleLST).__next__#,self._onNext
        self.focusControl = self.focusCycle()
        self.switch(self.focusControl)
        


    def _addCntrl(self, cntrl):
        self.log('_addCntrl cntrl = %s'%(cntrl))
        self.addControl(cntrl)
        cntrl.setVisible(True)  
        if not cntrl in self.focusCycleLST: self.focusCycleLST.append(cntrl)
        if not cntrl in self.focusCNTRLST:  self.focusCNTRLST[cntrl] = cntrl.getX(),cntrl.getY()
        

    def switch(self, cntrl=None):
        self.log('switch cntrl = %s'%(cntrl))
        if not self.focusCycle is None:
            if cntrl is None: self.focusControl = self.focusCycle()
            else:             self.focusControl = cntrl
            self._setFocus(self.focusControl)
            for cntrl in self.focusCNTRLST:
                if self.focusControl != cntrl: cntrl.setAnimations([('Conditional', 'effect=fade start=100 end=50 time=240 delay=160 condition=True reversible=False')])
                else:
                    self.posx, self.posy = cntrl.getX(),cntrl.getY()
                    cntrl.setAnimations([('Conditional', 'effect=fade start=50 end=100 time=240 delay=160 condition=True reversible=False')])


    def move(self, cntrl):
        posx, posy = self.focusCNTRLST[cntrl]
        if (self.posx != posx or self.posy != posy):
            cntrl.setPosition(self.posx, self.posy)
            
                      
    def save(self):
        changes = {}
        for cntrl in self.focusCNTRLST:
            posx, posy = cntrl.getX(), cntrl.getY()
            if  cntrl == self._channelBug:
                if (posx != self.channelBugX or posy != self.channelBugY):
                    changes[cntrl] = posx, posy, (posx == self.autoBugX & posy == self.autoBugY)
            elif cntrl == self._onNext:
                if (posx != self.onNextX or posy != self.onNextY):
                    changes[cntrl] = posx, posy, (posx == self.autoNextX & posy == self.autoNextY)
          
        if changes:
            self.log('save, saving %s'%(changes))
            if DIALOG.yesnoDialog(LANGUAGE(32096)): 
                for cntrl, value in list(changes.items()): self.set(cntrl,value[0],value[1],value[2])
        self.close()

    
    def set(self, cntrl, posx, posy, auto=False):
        self.log('set, cntrl = %s, posx,posy = (%s,%s) Auto? %s'%(cntrl, posx, posy, auto))
        if self.advRule: save = PROPERTIES.setProperty
        else:            save = SETTINGS.setSetting
        
        if cntrl == self._channelBug:
            if auto: save("Channel_Bug_Position_XY","Auto")
            else:    save("Channel_Bug_Position_XY","(%s,%s)"%(posx, posy))
        elif cntrl == self._onNext:
            if auto: save("On_Next_Position_XY","Auto")
            else:    save("On_Next_Position_XY","(%s,%s)"%(posx, posy))
        

    def _setFocus(self, cntrl):
        self.log('_setFocus cntrl = %s'%(cntrl))
        try: self.setFocus(cntrl)
        except: pass
        
        
    def _getFocus(self, cntrl):
        self.log('_getFocus cntrl = %s'%(cntrl))
        try: self.getFocus(cntrl)
        except: pass

        
    def onAction(self, act):
        actionId = act.getId()
        self.log('onAction: actionId = %s'%(actionId))
        lastaction = time.time() - self.lastActionTime
        # during certain times we just want to discard all input
        if lastaction < 2 and lastaction > 1 and actionId not in ACTION_PREVIOUS_MENU:
            self.log('Not allowing actions')
            action = ACTION_INVALID
        elif actionId in ACTION_SELECT_ITEM:   self.switch()
        elif actionId in ACTION_PREVIOUS_MENU: self.save()
        else:
            if   actionId == ACTION_MOVE_UP:    self.posy-=1
            elif actionId == ACTION_MOVE_DOWN:  self.posy+=1
            elif actionId == ACTION_MOVE_LEFT:  self.posx-=1
            elif actionId == ACTION_MOVE_RIGHT: self.posx+=1
            else: return
            self.move((self.focusControl))
        
        
        