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


class ChannelBug(xbmcgui.WindowXMLDialog):
    overlays = ["Bug","Vig","Next"]
    lastActionTime = time.time()
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        with BUILTIN.busy_dialog():
            self.window = xbmcgui.Window(12005) 
            self.window_h, self.window_w = (self.window.getHeight() , self.window.getWidth())
            
            self.advRule = True if kwargs.get("Channel_Bug_Position_XY") else False
            self.autoPOSX, self.autoPOSY = (abs(int(self.window_w // 8) - self.window_w) - 128, abs(int(self.window_h // 16) - self.window_h) - 128)
            try:    self.userPOSX, self.userPOSY = tuple(kwargs.get("Channel_Bug_Position_XY",SETTINGS.getSetting("Channel_Bug_Position_XY")))
            except: self.userPOSX, self.userPOSY = self.autoPOSX, self.autoPOSY

            #todo add vignette and on next POS controls, use adv. and global rules to set value.
            # self._vinEnabled = (kwargs.get("Enable_Vignette") or SETTINGS.getSettingBool('Enable_Vignette'))
            # self._vinImage   = (kwargs.get("Vignette_Image")  or SETTINGS.getSetting('Vignette_Image'))
            # self._vinZoom    = (kwargs.get("Vignette_Zoom")   or SETTINGS.getSettingFloat('Vignette_Zoom'))
            
            # SETTINGS.getSettingBool('Enable_OnNext')
            # self._onNext      = xbmcgui.ControlTextBox(abs(int(self.window_w // 8)), abs(int(self.window_h // 16) - self.window_h), 1920, 36, 'font12', '0xFFFFFFFF')

            self.posx, self.posy = self.userPOSX, self.userPOSY
            if BUILTIN.getInfoBool('Playing','Player'): BUILTIN.executebuiltin('ActivateWindow(fullscreenvideo)')
        self.doModal()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onInit(self):
        if not BUILTIN.getInfoBool('IsFullscreen','System'):
            DIALOG.okDialog(LANGUAGE(32097)%(BUILTIN.getInfoLabel('ScreenResolution','System')))
            
        self.log('onInit, channelbug posx,posy = (%s,%s)'%(self.userPOSX,self.userPOSY))
        self.overlayControl = self.getControl(40001)
        self.overlayControl.setVisible(False)
        self.overlayControl.setImage(os.path.join(MEDIA_LOC,'backgrounds','ratio.png'))
        # if self._vinEnabled: 
            # self.overlayControl.setPosition(self._vinOffsetXY[0], self._vinOffsetXY[1])
            # self.overlayControl.setHeight(self.window_h)
            # self.overlayControl.setWidth(self.window_w)
            # self.overlayControl.setImage(self._vinImage)
        self.overlayControl.setVisible(True)

        self._channelBug = xbmcgui.ControlImage(self.userPOSX, self.userPOSY, 128, 128, COLOR_LOGO, aspectRatio=2)
        self.addControl(self._channelBug)
        self.posx, self.posy = (self._channelBug.getX(),self._channelBug.getY())


    def save(self):
        self.log('save')
        if (self.posx != self.userPOSX or self.posy != self.userPOSY):
            if   self.posx == self.autoPOSX and self.posy == self.autoPOSY:  self.set(self.posx, self.posy, auto=True)
            elif DIALOG.yesnoDialog(LANGUAGE(32096)%(self.posx, self.posy)): self.set(self.posx, self.posy, auto=False)
        self.close()

    
    def set(self, posx, posy, auto=False):
        self.log('set, channelbug posx,posy = (%s,%s) Auto? %s'%(posx, posy, auto))
        if self.advRule: 
            if auto: PROPERTIES.setProperty("Channel_Bug_Position_XY","Auto")
            else:    PROPERTIES.setProperty("Channel_Bug_Position_XY","(%s,%s)"%(posx, posy))
        else:  
            if auto: SETTINGS.setSetting("Channel_Bug_Position_XY","Auto")
            else:    SETTINGS.setSetting("Channel_Bug_Position_XY","(%s,%s)"%(posx, posy))

        
    def onAction(self, act):
        actionId = act.getId()
        self.log('onAction: actionId = %s'%(actionId))
        lastaction = time.time() - self.lastActionTime
        # during certain times we just want to discard all input
        if lastaction < 2 and actionId not in ACTION_PREVIOUS_MENU:
            self.log('Not allowing actions')
            action = ACTION_INVALID
        elif actionId in ACTION_PREVIOUS_MENU:
            self.save()
        else:
            if   actionId == ACTION_MOVE_UP:    self.posy-=1
            elif actionId == ACTION_MOVE_DOWN:  self.posy+=1
            elif actionId == ACTION_MOVE_LEFT:  self.posx-=1
            elif actionId == ACTION_MOVE_RIGHT: self.posx+=1
            else: return
            if (self.posx != self.userPOSX or self.posy != self.userPOSY):
                self._channelBug.setPosition(self.posx, self.posy)
        
        
        