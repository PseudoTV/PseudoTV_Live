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

class Player(xbmc.Player):
    def __init__(self, overlay):
        xbmc.Player.__init__(self)
        self.overlay      = overlay
        self.playingTitle = self.getPlayerLabel()
        self.OnNextWait   = self.getOnNextInterval()
           
           
    def getPlayerLabel(self):
        return (xbmc.getInfoLabel('Player.Title') or xbmc.getInfoLabel('Player.Label') or '')
           
           
    def getPlayerTime(self):
        self.overlay.log('getPlayerTime')
        try:    return self.getTotalTime()
        except: return 0

        
    def getOnNextInterval(self,interval=3):
        totalTime = self.getPlayerTime()
        if totalTime == 0: return 300
        remaining = ((totalTime - (totalTime * .75)) - ((NOTIFICATION_CHECK_TIME//2) * interval))
        return remaining // interval
            
            
    def onPlayBackStarted(self):
        self.overlay.log('onPlayBackStarted')

        
    def onPlayBackEnded(self):
        self.overlay.log('onPlayBackEnded')
    
    
    def onPlayBackStopped(self):
        self.overlay.log('onPlayBackStopped')
                

class Overlay():
    windowManager = dict()
    PROPERTIES.setPropertyBool('OVERLAY',True)
    
    def __init__(self):
        self.myPlayer = Player(self)
        self.window   = xbmcgui.Window(12005) # Inheriting from 12005 (fullscreenvideo) puts the overlay in front of the video, but behind the video interface
        self.window_w = self.window.getWidth()
        self.window_h = self.window.getHeight()
        
        #init controls
        self._channelBug = xbmcgui.ControlImage(1556, 920, 128, 128, LOGO)#todo user sets size & location 
        self._channelBug.setEnableCondition('Player.HasMedia + Player.Playing')
        self._channelBug.setVisibleCondition('[Control.IsVisible(12005)]', True)
        self._channelBug.setAnimations([('VisibleChange', 'effect=fade start=0 end=100 time=2000 delay=500 reversible=true'),
                                        ('VisibleChange', 'effect=fade start=100 end=25 time=1000 delay=3000 reversible=true')])
        
        # https://kodi.wiki/view/Animating_your_skin
        # .setAnimations([('conditional','effect=fade start=0 end=100 time=2000 delay=500 condition=true', True),
                                        # ('conditional','effect=fade start=100 end=25 time=1000 delay=3000 condition=true', True)])
                                        
                                      
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def _addControl(self, control):
        if not self._hasWindow(control):
            self.window.addControl(control)
            self._setWindow(control,self.isVisible(control))
        
        
    def _removeControl(self, control):
        if self._hasWindow(control):
            self._delWindow(control)
            self.window.removeControl(control)
        
        
    def _hasWindow(self, control):
        return control in self.windowManager
        

    def _getWindow(self, control):
        return self.windowManager.get(control,False)
        
        
    def _setWindow(self, control, state):
        self.windowManager[control] = control
        
        
    def _delWindow(self, control):
        self.windowManager.pop(control)
        

    def setVisible(self, control, state):
        try:    
            self._setWindow(control,state)
            control.setVisible(state)
        except: pass
        
        
    def isVisible(self, control):
        try:    return control.isVisible()
        except: return self._getWindow(control)
        

    def show(self):
        self._addControl(self._channelBug)


    def hide(self):
        self._removeControl(self._channelBug)


    def close(self):
        PROPERTIES.setPropertyBool('OVERLAY',False)
        for window, visible in self.windowManager.items():
            self.removeControl(window)
        self.window.clearProperties()
    
    
    
    
    
    
    
    
    # def __init__(self, *args, **kwargs):
        # xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        # self.service            = kwargs.get('service')
        # self.pvritem            = {}
        # self.citem              = {}
        # self.nowitem            = {}
        # self.nextitems          = [] 
        # self.listitems          = []
        # self.listcycle          = []
        # self.isPlaylist         = False
        # self.staticOverlay      = False
        # self.showChannelBug     = False
        # self.showOnNext         = False
        
        # self.runActions         = RulesList().runActions
        
        # self.bugToggleThread    = threading.Timer(5.0, self.bugToggle)
        # self.onNextChkThread    = threading.Timer(5.0, self.onNextChk)
        # self.onNextToggleThread = threading.Timer(5.0, self.onNextToggle)


    # def log(self, msg, level=xbmc.LOGDEBUG):
        # return log('%s: %s'%(self.__class__.__name__,msg),level)


    # def onInit(self):
        # try:
            # self.log('onInit')
            # self.showChannelBug = SETTINGS.getSettingBool('Enable_ChannelBug')
            # self.showOnNext     = SETTINGS.getSettingBool('Enable_OnNext')
            # self.staticOverlay  = SETTINGS.getSettingBool("Static_Overlay")
            # self.channelBugVal  = SETTINGS.getSettingInt("Channel_Bug_Interval")

            # self.container = self.getControl(40000)
            
            # self.static = self.getControl(40001)
            # self.static.setVisible(self.staticOverlay)
            
            # self.startOver = self.getControl(41002)
            # self.startOver.setVisible(False)
            
            # self.onNext = self.getControl(41003)
            # self.onNext.setVisible(False)
            
            # self.channelbug = self.getControl(41004)
            # self.channelbug.setVisible(False)
                        
            # self.overlayLayer = self.getControl(39999)
            # self.overlayLayer.setVisible(False)
        
            # # todo requires kodi core update. videowindow control requires setPosition,setHeight,setWidth functions.
            # # https://github.com/xbmc/xbmc/issues/19467
            # # xbmcgui.lock()
            # # self.videoWindow  = self.getControl(41000)
            # # self.videoWindow.setPosition(0, 0)
            # # self.videoWindow.setHeight(self.videoWindow.getHeight())
            # # self.videoWindow.setWidth(self.videoWindow.getWidth())
            # # self.videoOverlay = self.getControl(41005)
            # # self.videoOverlay.setPosition(0, 0)
            # # self.videoOverlay.setHeight(0)
            # # self.videoOverlay.setWidth(0)
            # # xbmcgui.unlock()
            
            # self.myPlayer = Player(self)
            
            # if self.load(): 
                # self.overlayLayer.setVisible(True)
                # self.log('showChannelBug = %s'%(self.showChannelBug))
                # self.log('showOnNext = %s'%(self.showOnNext))
                # if self.showChannelBug: self.bugToggle() #start bug timer
                # if self.showOnNext:     self.onNextChk()#start onnext timer
            # else: 
                # self.closeOverlay()
                
        # except Exception as e: 
            # self.log("onInit, Failed! %s"%(e), xbmc.LOGERROR)
            # self.closeOverlay()


    # def load(self):
        # try:
            # self.log('load')
            # self.pvritem = self.service.player.getPVRitem()
            # if not self.pvritem or not isPseudoTV(): 
                # return False

            # self.citem       = self.pvritem.get('citem',{})
            # self.channelbug.setImage(self.citem.get('logo',LOGO))

            # self.isPlaylist  = self.pvritem.get('isPlaylist',False)
            # self.nowitem     = self.pvritem.get('broadcastnow',{}) # current item
            # self.nextitems   = self.pvritem.get('broadcastnext',[])
            # del self.nextitems[PAGE_LIMIT:]# list of upcoming items, truncate for speed.
                            
            # self.nowwriter   = getWriter(self.pvritem.get('broadcastnow',{}).get('writer',{}))
            # self.nowwriter.get('art',{})['thumb'] = getThumb(self.nowwriter) #unify artwork
            
            # self.nextwriters = []
            # for nextitem in self.nextitems: 
                # nextitem = getWriter(nextitem.get('writer',{}))
                # nextitem.get('art',{})['thumb'] = getThumb(nextitem) #unify artwork
                # self.nextwriters.append(nextitem)

            # self.listitems   = [self.service.writer.dialog.buildItemListItem(self.nowwriter)]
            # self.listitems.extend([self.service.writer.dialog.buildItemListItem(nextwriter) for nextwriter in self.nextwriters])
            
            # self.container.reset()
            # xbmc.sleep(100)
            # self.container.addItems(self.listitems)
                        
            # self.runActions(RULES_ACTION_OVERLAY, self.citem, inherited=self)
            # self.static.setVisible(self.staticOverlay)
            # # self.myPlayer.onPlayBackStarted()
            # self.log('load finished')
            # return True
        # except Exception as e: 
            # self.log("load, Failed! %s"%(e), xbmc.LOGERROR)
            # return False
     

    # def getPlayerProgress(self):
        # try:    return float(xbmc.getInfoLabel('Player.Progress'))
        # except: return 0.0


    # def getTimeRemaining(self):
        # try:    return int(sum(x*y for x, y in zip(map(float, xbmc.getInfoLabel('Player.TimeRemaining(hh:mm:ss)').split(':')[::-1]), (1, 60, 3600, 86400))))
        # except: return 0
   
   
    # def playSFX(self, filename, cached=True):
        # self.log('playSFX, filename = %s, cached = %s'%(filename,cached))
        # xbmc.playSFX(filename, useCached=cached)
   
   
    # def cancelOnNext(self): #channel changing and/or not playing cancel on next
        # self.onNext.setVisible(False)
        # if self.onNextToggleThread.is_alive(): 
            # try: 
                # self.onNextToggleThread.cancel()
                # self.onNextToggleThread.join()
            # except: pass


    # def updateOnNext(self):
        # try: #if playlist, pop older played item and refresh meta container.
            # self.log('updateOnNext, isPlaylist = %s'%(self.isPlaylist))
            # self.cancelOnNext()
            # if self.isPlaylist:
                # if len(self.listitems) > 0:
                    # self.listitems.pop(0)
                    # self.container.reset()
                    # self.container.addItems(self.listitems)
                    # return
        # except Exception as e: self.log("updateOnNext, Failed! %s"%(e), xbmc.LOGERROR)
        

    # def onNextChk(self):
        # def playerAssert():
            # try: #test playing item, contains title? remaining time / progress within parameters?
                # titleAssert    = self.listitems[0].getLabel() == self.myPlayer.playingTitle
                # remainAssert   = self.getTimeRemaining() <= NOTIFICATION_TIME_REMAINING
                # progressAssert = self.getPlayerProgress() >= 75.0
                # return (titleAssert & remainAssert & progressAssert)
            # except: 
                # return False
        # try:
            # if self.onNextToggleThread.is_alive():
                # if not self.overlayLayer.isVisible(): 
                    # self.cancelOnNext()
            # else:
                # if playerAssert(): 
                    # self.onNextToggle()
                    
             # #poll player every XXsecs.
            # self.onNextChkThread = threading.Timer(NOTIFICATION_CHECK_TIME, self.onNextChk)
            # self.onNextChkThread.name = "onNextChkThread"
            # self.onNextChkThread.start()
        # except Exception as e: self.log("onNextChk, Failed! %s"%(e), xbmc.LOGERROR)
        

    # def onNextToggle(self, state=True):
        # if self.onNextToggleThread.is_alive():
            # try:
                # self.onNextToggleThread.cancel()
                # self.onNextToggleThread.join()
            # except: pass
        # try:
            # self.playSFX(BING_WAV)
            # wait   = {True:(NOTIFICATION_CHECK_TIME//2),False:float(self.myPlayer.OnNextWait)}[state]
            # nstate = not bool(state)
            # self.onNext.setVisible(state)
            # self.log('onNextToggle, state %s wait %s to new state %s'%(state,wait,nstate))
            # self.onNextToggleThread = threading.Timer(wait, self.onNextToggle, [nstate])
            # self.onNextToggleThread.name = "onNextToggleThread"
            # self.onNextToggleThread.start()
        # except Exception as e: self.log("onNextToggle, Failed! %s"%(e), xbmc.LOGERROR)
            
            
    # def bugToggle(self, state=True):
        # def getWait(state):
            # if self.channelBugVal == -1: 
                # onVAL  = self.getTimeRemaining()
                # offVAL = 0.1
            # elif self.channelBugVal == 0:
                # onVAL  = random.randint(300,600)
                # offVAL = random.randint(300,600)
            # else:
                # onVAL  = self.channelBugVal * 60
                # offVAL = round(onVAL // 2)
            # return {True:float(onVAL),False:float(offVAL)}[state]
            
        # if self.bugToggleThread.is_alive():
            # try:
                # self.bugToggleThread.cancel()
                # self.bugToggleThread.join()
            # except: pass
        # try:   
            # wait   = getWait(state)
            # nstate = not bool(state)
            # self.channelbug.setVisible(state)
            # self.log('bugToggle, state %s wait %s to new state %s'%(state,wait,nstate))
            # self.bugToggleThread = threading.Timer(wait, self.bugToggle, [nstate])
            # self.bugToggleThread.name = "bugToggleThread"
            # self.bugToggleThread.start()
        # except Exception as e: self.log("bugToggle, Failed! %s"%(e), xbmc.LOGERROR)

      
    # def closeOverlay(self):
        # self.log('closeOverlay')
        # threads = [self.bugToggleThread,
                   # self.onNextChkThread,
                   # self.onNextToggleThread]
                   
        # for thread_item in threads:
            # if thread_item.is_alive(): 
                # try: 
                    # thread_item.cancel()
                    # thread_item.join(1.0)
                # except: pass
        # self.close()


    # def onAction(self, act):
        # actionID = act.getId()
        # actionBC = act.getButtonCode()
        # self.log('onAction, actionID = %s, actionBC = %s'%(actionID,actionBC))
        # if actionID == ACTION_PREVIOUS_MENU:
            # xbmc.executebuiltin("Action(PreviousMenu)")
        # elif actionID == ACTION_MOVE_LEFT:
            # xbmc.executebuiltin("ActivateWindowAndFocus(pvrosdchannels)")
        # elif actionID == ACTION_MOVE_RIGHT:
            # xbmc.executebuiltin("ActivateWindowAndFocus(pvrchannelguide)")
        # elif actionID == ACTION_MOVE_UP:
            # self.service.writer.jsonRPC.sendButton('Up')
        # elif actionID == ACTION_MOVE_DOWN:
            # self.service.writer.jsonRPC.sendButton('Down')
        # elif actionID == ACTION_SELECT_ITEM:
            # self.service.writer.jsonRPC.sendButton('I')
        # self.closeOverlay()