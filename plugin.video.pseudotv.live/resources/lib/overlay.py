  # Copyright (C) 2022 Lunatixz


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
from resources.lib.globals import *
from resources.lib.rules   import RulesList

# class Video(xbmcgui.WindowXML):
# todo adv. rule apply overlay ie. scanline, etc to videowindow.
# xbmcgui.lock()
# self.videoWindow  = self.getControl(41000)
# self.videoWindow.setPosition(0, 0)
# self.videoWindow.setHeight(self.videoWindow.getHeight())
# self.videoWindow.setWidth(self.videoWindow.getWidth())
# self.videoOverlay = self.getControl(41005)
# self.videoOverlay.setPosition(0, 0)
# self.videoOverlay.setHeight(0)
# self.videoOverlay.setWidth(0)
# xbmcgui.unlock()

class Background(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.overlay = kwargs.get('overlay')
        
        
    def onInit(self):
        self.getControl(40001).setVisible(self.overlay.showStatic)
        self.getControl(40002).setImage(self.overlay._getPlayingCitem().get('logo',LOGO))
        self.getControl(40003).setText(self.overlay._onNext.getText())
        

class Player(xbmc.Player):
    def __init__(self, overlay):
        xbmc.Player.__init__(self)
        self.overlay = overlay


    def _hasBackground(self):
        return PROPERTIES.getPropertyBool('OVERLAY_BACKGROUND')


    def startBackground(self):
        if not self._hasBackground():
            self.overlay.log('startBackground')
            self.background = Background("%s.background.xml"%(ADDON_ID), ADDON_PATH, "default", overlay=self.overlay)
            self.background.show()
            xbmc.sleep(2000)
            

    def closeBackground(self):
        try:
            self.background.close()
            del self.background
            self.overlay.log('closeBackground')
            xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')
        except: pass
        
        
    def onAVStarted(self):
        self.overlay.log('onAVStarted')
        self.closeBackground()
        
        
    def onPlayBackStarted(self):
        self.overlay.log('onPlayBackStarted')
        if self.overlay._hasControl(self.overlay._channelBug):
            self.overlay.setImage(self.overlay._channelBug,(self.overlay._getPlayingCitem().get('logo',LOGO)))
        
        
    def onPlayBackEnded(self):
        self.overlay.log('onPlayBackEnded')
        self.startBackground()
        self.overlay.cancelOnNext()


class Overlay():
    controlManager = dict()
    
    def __init__(self, service):
        self.service    = service
        self.player     = service.player
        self.runActions = RulesList().runActions
        self.showStatic = SETTINGS.getSettingBool("Static_Overlay")
        
        #win control - Inheriting from 12005 (fullscreenvideo) puts the overlay in front of the video, but behind the video interface
        self.window   = xbmcgui.Window(12005) 
        self.window_w = self.window.getWidth()
        self.window_h = self.window.getHeight()
        
        #init controls
        self._onNext     = xbmcgui.ControlTextBox(128, 952, 1418, 36, 'font12', '0xFFFFFFFF')#todo user sets size & location 
        self._channelBug = xbmcgui.ControlImage(1556, 920, 128, 128, 'None', aspectRatio=2)#todo user sets size & location 


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _getPVRItem(self):
        return self.player.getPVRitem()
    
    
    def _getPlayingCitem(self):
        return self._getPVRItem().get('citem',{})
        
    
    def _getNowItem(self):
        return self._getPVRItem().get('broadcastnow',{})
        
        
    def _getNextItems(self):
        return self._getPVRItem().get('broadcastnext',[])
        
        
    def _getItemWriter(self, item):
        return getWriter(item.get('writer',''))
        
        
    def _hasControl(self, control):
        return control in self.controlManager
        

    def _getControl(self, control):
        """ If control is not None  == Exists, 
            If control is     True  == Visible, 
            If control is     False == Hidden 
        """
        return self.controlManager.get(control,None)
        
        
    def _setControl(self, control, state):
        self.controlManager[control] = state
        
        
    def _delControl(self, control):
        if self._hasControl(control):
            self.controlManager.pop(control)
        
        
    def _addControl(self, control):
        """ Create Control & Add to manager.
        """
        try:
            self.log('_addControl, %s'%(control))
            self.window.addControl(control)
            self._setControl(control,self.setVisible(control, False))
        except Exception as e: self.log('_addControl failed! %s'%(e))
        
        
    def _removeControl(self, control):
        """ Remove Control & Delete from manager.
        """
        try:
            self.log('_removeControl, %s'%(control))
            self.window.removeControl(control)
            self._delControl(control)
        except Exception as e: self.log('_removeControl failed! %s'%(e))
        
        
    def setImage(self, control, image, cache=False):
        try: control.setImage(image, useCache=cache)
        except Exception as e: self.log('setImage failed! %s'%(e))
        
        
    def setVisible(self, control, state):
        try:
            self._setControl(control,state)
            control.setVisible(state)
            self.log('setVisible, %s = %s'%(control,state))
        except Exception('setVisible, failed! control does not exist'): pass
        return state
        
        
    def isVisible(self, control):
        try:    return control.isVisible()
        except: return (self._getControl(control) or False)
        

    def open(self):
        self.log('open')
        self.myPlayer = Player(self)
        if isOverlay(): 
            return self.close()
            
        setOverlay(True)
        self.showStatic      = SETTINGS.getSettingBool("Static_Overlay")
        self.channelBugColor = '0x%s'%((SETTINGS.getSetting('DIFFUSE_LOGO') or 'FFFFFFFF')) #todo adv. channel rule for color selection.
        self.runActions(RULES_ACTION_OVERLAY, self._getPlayingCitem(), inherited=self)
        
        self._chkonNextThread  = threading.Timer(1.0, self.chkOnNext)
        self._onNextThread     = threading.Timer(5.0, self.toggleOnNext)
        self._channelBugThread = threading.Timer(5.0, self.toggleBug)
        
        self._overlayThreads   = [self._channelBugThread,
                                  self._chkonNextThread, 
                                  self._onNextThread]

        for thread_item in self._overlayThreads:
            thread_item.start()
            

    def close(self):
        self.log('close')
        for control, visible in list(self.controlManager.items()):
            self._removeControl(control)

        for thread_item in self._overlayThreads:
            if thread_item.is_alive(): 
                try: 
                    self.log("close, joining thread %s"%(thread_item.name))
                    thread_item.cancel()
                    thread_item.join(0.5)
                except: pass
                    
        self.setImage(self._channelBug,'None')
        self.window.clearProperties()
        self.myPlayer.closeBackground()
        setOverlay(False)
        del self.myPlayer


    def toggleBug(self, state=True):
        def getWait(state):
            _channelBugInterval = SETTINGS.getSettingInt("Channel_Bug_Interval")
            if _channelBugInterval == -1: 
                onVAL  = self.player.getTimeRemaining()
                offVAL = 0.1
            elif _channelBugInterval == 0:
                onVAL  = random.randint(300,600)
                offVAL = random.randint(300,600)
            else:
                onVAL  = _channelBugInterval * 60
                offVAL = round(onVAL // 2)
            return {True:float(onVAL),False:float(offVAL)}[state]

        try:              
            wait   = getWait(state)
            nstate = not bool(state)
            
            if state: 
                if not self._hasControl(self._channelBug):
                    self._addControl(self._channelBug)
                    self._channelBug.setEnableCondition('[Player.HasMedia + Player.Playing]')
                    
                self.setImage(self._channelBug,(self._getPlayingCitem().get('logo',LOGO)))
                if not bool(SETTINGS.getSettingInt('Color_Logos')): #apply user diffuse color only to "prefer white".
                    self._channelBug.setColorDiffuse(self.channelBugColor)
                    
                self.setVisible(self._channelBug,True)
                self._channelBug.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=2000 delay=500 condition=True reversible=True'),
                                                ('Conditional', 'effect=fade start=100 end=25 time=1000 delay=2000 condition=True reversible=False')])
            else: 
                self.setVisible(self._channelBug,False)
                
            self.log('toggleBug, state %s wait %s to new state %s'%(state,wait,nstate))
            self._channelBugThread = threading.Timer(wait, self.toggleBug, [nstate])
            self._channelBugThread.name = "_channelBugThread"
            self._channelBugThread.start()
        except Exception as e: self.log("toggleBug, Failed! %s"%(e), xbmc.LOGERROR)
           

    def cancelOnNext(self):
        self.log('cancelOnNext')
        self.setVisible(self._onNext,False)
        try: 
            self._onNextThread.cancel()
            self._onNextThread.join()
        except: pass


    def chkOnNext(self):
        def playerAssert():
            """ #test playing item, title match? remaining time / progress within parameters?
            """
            try: 
                titleAssert    = self._getNowItem().get('label') == self.player.getPlayerLabel()
                remainAssert   = self.player.getTimeRemaining() <= NOTIFICATION_TIME_REMAINING
                progressAssert = self.player.getPlayerProgress() >= 75.0
                return (titleAssert & remainAssert & progressAssert & self.player.isPlaying() & self.player.isPseudoTV)
            except: 
                return False
        try:
            if self._onNextThread.is_alive():
                # cancel onNext Toggle.
                if not playerAssert(): 
                    self.cancelOnNext()
            else:# start onNext Toggle
                if playerAssert(): 
                    self.toggleOnNext()
                    
             #poll player every XXsecs.
            self._chkonNextThread = threading.Timer(NOTIFICATION_CHECK_TIME, self.chkOnNext)
            self._chkonNextThread.name = "chkonNextThread"
            self._chkonNextThread.start()
        except Exception as e: self.log("chkOnNext, Failed! %s"%(e), xbmc.LOGERROR)

    
    def toggleOnNext(self, state=True):
        def getOnNextInterval(interval=3):
            totalTime = self.player.getPlayerTime()
            remaining = self.player.getTimeRemaining()
            if interval < 1: 
                intTime = NOTIFICATION_MIN_TIME
            else:
                intTime = roundupDIV(abs((totalTime - (totalTime * .75)) - ((NOTIFICATION_CHECK_TIME//2) * interval)),interval)
                if (intTime * interval) < remaining: intTime = getOnNextInterval((interval - 1))
            self.log('toggleOnNext, totalTime = %s, interval = %s, remaining = %s, intTime = %s'%(totalTime,interval,remaining,intTime))
            return intTime
            
        try:
            wait   = {True:(NOTIFICATION_CHECK_TIME//2),False:float(getOnNextInterval())}[state]
            nstate = not bool(state)
            
            if state: 
                if not self._hasControl(self._onNext):
                    self._addControl(self._onNext)
                    self._onNext.setEnableCondition('[Player.HasMedia + Player.Playing]')

                try:    writer = self._getItemWriter(self._getNextItems()[0])
                except: return self.cancelOnNext()
                chname = self._getPlayingCitem().get('label',ADDON_NAME)
                onNow  = (self._getNowItem().get('label','') or self._getNowItem().get('title','') or chname)
                onNext = '%s - %s'%(writer.get('label',''), writer.get('episodelabel',''))
                self._onNext.setText("[B]You're Watching:[/B] %s %s[CR][B]Up Next:[/B] %s"%(onNow,('' if chname.lower().startswith(onNow.lower()) else 'on %s'%(chname)),onNext))
                self.setVisible(self._onNext,True)
                self._onNext.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=2000 delay=1000 condition=True reversible=True')])
                self._onNext.autoScroll(6000, 3000, 5000)
                self.playSFX(BING_WAV)
            else: 
                self.setVisible(self._onNext,False)
            
            self.log('toggleOnNext, state %s wait %s to new state %s'%(state,wait,nstate))
            self._onNextThread = threading.Timer(wait, self.toggleOnNext, [nstate])
            self._onNextThread.name = "onNextThread"
            self._onNextThread.start()
        except Exception as e: self.log("toggleOnNext, Failed! %s"%(e), xbmc.LOGERROR)
    

    def playSFX(self, filename, cached=True):
        self.log('playSFX, filename = %s, cached = %s'%(filename,cached))
        xbmc.playSFX(filename, useCached=cached)