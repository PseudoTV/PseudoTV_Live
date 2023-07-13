  # Copyright (C) 2023 Lunatixz


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
from rules     import RulesList
from resources import Resources
from threading import Timer, enumerate

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
        self.player     = kwargs.get('player')
        self.runActions = RulesList().runActions
        self.showStatic = SETTINGS.getSettingBool("Static_Overlay")
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onInit(self):
        self.log('onInit')
        try:
            self.showStatic = SETTINGS.getSettingBool("Static_Overlay")#temp remove when rules finished.
            self.runActions(RULES_ACTION_OVERLAY, self.player.pvritem.get('citem',{}), inherited=self)
            self.getControl(40001).setVisible(self.showStatic)
            self.getControl(40002).setImage(self.player.pvritem.get('icon',(BUILTIN.getInfoLabel('Art(icon)','Player') or COLOR_LOGO)))
            self.getControl(40003).setText(LANGUAGE(32104)%(self.player.pvritem.get('label',ADDON_NAME)))
        except: self.close()
        

class MYPlayer(xbmc.Player):
    def __init__(self, overlay):
        xbmc.Player.__init__(self)
        self.overlay = overlay

        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onAVStarted(self):
        self.log('onAVStarted')
        if not self.overlay.player.isPseudoTV:
            self.onPlayBackEnded()
        else:
            self.overlay.toggleBug()
            self.overlay.toggleOnNext()
            

    def onPlayBackStopped(self):
        self.log('onPlayBackStopped')
        self.onPlayBackEnded()
            

    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        self.overlay.close()


class Overlay():
    controlManager = dict()
    runActions = RulesList().runActions
    
    def __init__(self, player):
        self.player = player
        
        #win control - Inheriting from 12005 (fullscreenvideo) puts the overlay in front of the video, but behind the video interface
        self.window   = xbmcgui.Window(12005) 
        self.window_w = self.window.getWidth()
        self.window_h = self.window.getHeight()
        
        #init controls
        self._channelBugX, self._channelBugY = (literal_eval(SETTINGS.getSetting("Channel_Bug_Position_XY")) or (1556, 920))
        self._channelBug     = xbmcgui.ControlImage(self._channelBugX, self._channelBugY, 128, 128, 'None', aspectRatio=2)

        self._onNext         = xbmcgui.ControlTextBox(128, 952, 1418, 36, 'font12', '0xFFFFFFFF')#todo user sets size & location 
        self._onNextThread   = Timer(30, self.toggleOnNext)
        
        self.channelBugColor = '0x%s'%((SETTINGS.getSetting('DIFFUSE_LOGO') or 'FFFFFFFF')) #todo adv. channel rule for color selection.
        self.enableOnNext    = SETTINGS.getSettingBool('Enable_OnNext')
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _hasControl(self, control):
        ctrl = self._getControl(control) is not None
        self.log('_hasControl, %s = %s'%(control,ctrl))
        return ctrl
        

    def _getControl(self, control):
        """ If control is not None  == Exists, 
            If control is     True  == Visible, 
            If control is     False == Hidden 
        """
        return self.controlManager.get(control,None)
        
        
    def _setControl(self, control, state):
        self.controlManager[control] = state
        
        
    def _delControl(self, control):
        self.controlManager.pop(control)
        
        
    def _addControl(self, control):
        """ Create Control & Add to manager.
        """
        try:
            if not self._hasControl(control):
                self.log('_addControl, %s'%(control))
                self.window.addControl(control)
                self._setControl(control,self.setVisible(control, False))
        except Exception as e: self.log('_addControl failed! %s'%(e), xbmc.LOGERROR)
        
        
    def _removeControl(self, control):
        """ Remove Control & Delete from manager.
        """
        try:
            if self._hasControl(control):
                self.log('_removeControl, %s'%(control))
                self.window.removeControl(control)
                self._delControl(control)
        except Exception as e: self.log('_removeControl failed! %s'%(e), xbmc.LOGERROR)
        
        
    def setImage(self, control, image, cache=True):
        try: 
            if self._hasControl(control):
                control.setImage(image, useCache=cache)
        except Exception as e: self.log('setImage failed! %s'%(e), xbmc.LOGERROR)
        
        
    def setVisible(self, control, state):
        try:
            if self._hasControl(control):
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
        if isOverlay() or not self.player.isPseudoTV: 
            return self.close()
            
        setOverlay(True)
        self.myPlayer = MYPlayer(overlay=self)
        self.myPlayer.onAVStarted()
        
        self.channelBugColor = '0x%s'%((SETTINGS.getSetting('DIFFUSE_LOGO') or 'FFFFFFFF')) #todo adv. channel rule for color selection.
        self.enableOnNext    = SETTINGS.getSettingBool('Enable_OnNext')
        self.runActions(RULES_ACTION_OVERLAY, self.player.pvritem.get('citem',{}), inherited=self)
            

    def close(self):
        self.log('close')
        self.cancelOnNext()
        self.cancelChannelBug()
        self.setImage(self._channelBug,'None')
        for control, visible in list(self.controlManager.items()):
            self._removeControl(control)

        try: del self.myPlayer
        except: pass
        setOverlay(False)

    
    def cancelChannelBug(self):
        self.log('cancelChannelBug')
        self.setVisible(self._channelBug,False)
        try: 
            self._channelBugThread.cancel()
            self._channelBugThread.join()
        except: pass


    def toggleBug(self, state=True):
        def getWait(state):
            _channelBugInterval = SETTINGS.getSettingInt("Channel_Bug_Interval")
            if _channelBugInterval == -1: 
                onVAL  = self.player.getTimeRemaining()
                offVAL = 0.1
            elif _channelBugInterval == 0:
                onVAL  = random.randint(300,900)
                offVAL = random.randint(300,900)
            else:
                onVAL  = _channelBugInterval * 60
                offVAL = round(onVAL // 2)
            return {True:float(onVAL),False:float(offVAL)}[state]

        try:
            wait   = getWait(state)
            nstate = not bool(state)
            
            try: 
                if self._channelBugThread.is_alive():
                    self._channelBugThread.cancel()
                    self._channelBugThread.join()
            except: pass
                  
            try: 
                self._channelBugX, self._channelBugY = (literal_eval(SETTINGS.getSetting("Channel_Bug_Position_XY")) or (1556, 920))
                self.log('toggleBug, channelbug POSXX (%s,%s)'%(self._channelBugX, self._channelBugY))
                self._channelBug.setPosition(self._channelBugX, self._channelBugY)
            except: pass
            
            if state and self.player.isPseudoTV: 
                if not self._hasControl(self._channelBug):
                    self._addControl(self._channelBug)
                    self._channelBug.setEnableCondition('[Player.Playing]')

                logo = self.player.pvritem.get('icon',(BUILTIN.getInfoLabel('Art(icon)','Player') or LOGO))
                self.log('toggleBug, channelbug logo = %s)'%(logo))
                
                if   SETTINGS.getSettingBool('Force_Diffuse'): self._channelBug.setColorDiffuse(self.channelBugColor)
                elif BUILTIN.getInfoBool('HasAddon(script.module.pil)','System'):
                    jsonRPC   = JSONRPC()
                    resources = Resources(jsonRPC,jsonRPC.cache)
                    if resources.isMono(logo): self._channelBug.setColorDiffuse(self.channelBugColor)
                    del resources
                    del jsonRPC
                
                self.setVisible(self._channelBug,True)
                self.setImage(self._channelBug,logo)
                self._channelBug.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=2000 delay=500 condition=True reversible=False'),
                                                ('Conditional', 'effect=fade start=100 end=25 time=1000 delay=2000 condition=True reversible=False')])
            else: 
                self.setImage(self._channelBug,'None')
                self.setVisible(self._channelBug,False)
                
            self.log('toggleBug, state %s wait %s to new state %s'%(state,wait,nstate))
            self._channelBugThread = Timer(wait, self.toggleBug, [nstate])
            self._channelBugThread.name = "_channelBugThread"
            self._channelBugThread.start()
        except Exception as e: self.log("toggleBug, failed! %s"%(e), xbmc.LOGERROR)
          
          
    def toggleOnNext(self, state=True):
        def getOnNextInterval(interval=3):
            #split totalTime time into quarters, last quarter trigger nextup split by equal intervals of 3. 
            totalTime  = int(int(self.player.getPlayerTime()))
            remaining  = floor(self.player.getTimeRemaining())
            showTime   = (abs(totalTime - (totalTime * .75)) - (OVERLAY_DELAY * interval))
            intTime    = roundupDIV(showTime,interval)
            showOnNext = remaining <= showTime
            
            if remaining < intTime:
                return getOnNextInterval(interval + 1)

            self.log('toggleOnNext, totalTime = %s, interval = %s, remaining = %s, intTime = %s, showOnNext = %s'%(totalTime,interval,remaining,intTime,showOnNext))
            return showOnNext, intTime

        if BUILTIN.getInfoBool('HasAddon(service.upnext)','System') and self.player.pvritem.get('isPlaylist',False):
            self.updateUpNext(self.player.pvritem)
        else:
            try:
                showOnNext, intTime = getOnNextInterval()
                wait   = {True:OVERLAY_DELAY,False:float(intTime)}[state]
                nstate = not bool(state)
                try: 
                    if self._onNextThread.is_alive():
                        self._onNextThread.cancel()
                        self._onNextThread.join()
                except: pass
                    
                if state and showOnNext and self.player.isPseudoTV:
                    try:
                        nowItem  = (self.player.pvritem.get('broadcastnow')  or {})      # current item
                        nextItem = (self.player.pvritem.get('broadcastnext') or [{}])[0] # upcoming items
                    except:
                        self.log('toggleOnNext, pvritem = %s failed!'%(self.player.pvritem))
                        return

                    if not self._hasControl(self._onNext):
                        self._addControl(self._onNext)
                        self._onNext.setEnableCondition('[Player.Playing]')
                                                
                    if nowItem and nextItem:
                        onNow  = '%s on %s'%('%s%s'%(nowItem['title'],' - %s'%(nowItem.get('episodename')) if nowItem.get('episodename') else ''), self.player.pvritem.get('label',ADDON_NAME))
                        onNext = '%s%s'%(nextItem['title'],' - %s'%(nextItem.get('episodename')) if nextItem.get('episodename') else '')
                        self._onNext.setText('%s\n%s'%(LANGUAGE(32104)%(onNow),LANGUAGE(32116)%(onNext)))
                        self._onNext.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=2000 delay=1000 condition=True reversible=True')])
                        self._onNext.autoScroll(6000, 3000, 5000)
                        self.setVisible(self._onNext,True)
                        playSFX(BING_WAV)
                else: 
                    self.setVisible(self._onNext,False)
                
                self.log('toggleOnNext, state %s wait %s to new state %s'%(state,wait,nstate))
                self._onNextThread = Timer(wait, self.toggleOnNext, [nstate])
                self._onNextThread.name = "onNextThread"
                self._onNextThread.start()
            except Exception as e: self.log("toggleOnNext, failed! %s"%(e), xbmc.LOGERROR)


    def cancelOnNext(self):
        self.log('cancelOnNext')
        self.setVisible(self._onNext,False)
        if self._onNextThread.is_alive():
            self._onNextThread.cancel()
            self._onNextThread.join()

    
    def updateUpNext(self, playingItem={}):
        self.log('updateUpNext')
        try:
            # https://github.com/im85288/service.upnext/wiki/Example-source-code
            data            = dict()
            nowItem         = decodeWriter(playingItem['broadcastnow'].get('writer',{}))       
            current_episode = {"current_episode":{"episodeid" :(nowItem.get("id"           ,"") or ""),
                                                  "tvshowid"  :(nowItem.get("tvshowid"     ,"") or ""),
                                                  "title"     :(nowItem.get("title"        ,"") or ""),
                                                  "art"       :(nowItem.get("art"          ,"") or ""),
                                                  "season"    :(nowItem.get("season"       ,"") or ""),
                                                  "episode"   :(nowItem.get("episode"      ,"") or ""),
                                                  "showtitle" :(nowItem.get("tvshowtitle"  ,"") or ""),
                                                  "plot"      :(nowItem.get("plot"         ,"") or ""),
                                                  "playcount" :(nowItem.get("playcount"    ,"") or ""),
                                                  "rating"    :(nowItem.get("rating"       ,"") or ""),
                                                  "firstaired":(nowItem.get("firstaired"   ,"") or ""),
                                                  "runtime"   :(nowItem.get("runtime"      ,"") or "")}}
            data.update(current_episode)
        except: pass
        try:
            nextItem        = decodeWriter(playingItem['broadcastnext'][0].get('writer',{}))
            next_episode    = {"next_episode"   :{"episodeid" :(nextItem.get("id"          ,"") or ""),
                                                  "tvshowid"  :(nextItem.get("tvshowid"    ,"") or ""),
                                                  "title"     :(nextItem.get("title"       ,"") or ""),
                                                  "art"       :(nextItem.get("art"         ,"") or ""),
                                                  "season"    :(nextItem.get("season"      ,"") or ""),
                                                  "episode"   :(nextItem.get("episode"     ,"") or ""),
                                                  "showtitle" :(nextItem.get("tvshowtitle" ,"") or ""),
                                                  "plot"      :(nextItem.get("plot"        ,"") or ""),
                                                  "playcount" :(nextItem.get("playcount"   ,"") or ""),
                                                  "rating"    :(nextItem.get("rating"      ,"") or ""),
                                                  "firstaired":(nextItem.get("firstaired"  ,"") or ""),
                                                  "runtime"   :(nextItem.get("runtime"     ,"") or "")}}
            data.update(next_episode)
        except: pass
        jsonRPC = JSONRPC()
        jsonRPC.notifyAll(message='upnext_data', data=binascii.hexlify(json.dumps(data).encode('utf-8')).decode('utf-8'), sender='%s.SIGNAL'%(ADDON_ID))
        del jsonRPC
        
