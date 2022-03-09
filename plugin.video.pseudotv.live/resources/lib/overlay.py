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
    def __init__(self):
        xbmc.Player.__init__(self)
        self.playingTitle = ""
        self.OnNextWait   = 300
            
            
    def onPlayBackStarted(self):
        self.overlay.log('onPlayBackStarted')
        self.playingTitle = xbmc.getInfoLabel('Player.Title')
        self.OnNextWait   = self.getOnNextInterval()
        
        
    def onPlayBackEnded(self):
        self.overlay.log('onPlayBackEnded')
        self.playingTitle = ""
        self.overlay.updateOnNext()
    
    
    def onPlayBackStopped(self):
        self.overlay.log('onPlayBackStopped')
        self.overlay.closeOverlay()
                
                
    def getPlayerTime(self):
        self.overlay.log('getPlayerTime')
        try:    return self.getTotalTime()
        except: return 0

        
    def getOnNextInterval(self,interval=3):
        totalTime = self.getPlayerTime()
        if totalTime == 0: return
        remaining = ((totalTime - (totalTime * .75)) - ((NOTIFICATION_CHECK_TIME//2) * interval))
        return remaining // interval
        
        
class Overlay(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.service            = kwargs.get('service')
        self.pvritem            = {}
        self.citem              = {}
        self.nowitem            = {}
        self.nextitems          = [] 
        self.listitems          = []
        self.listcycle          = []
        self.isPlaylist         = False
        self.staticOverlay      = False
        self.showChannelBug     = False
        self.showOnNext         = False
        
        self.runActions         = RulesList().runActions
        
        self.bugToggleThread    = threading.Timer(5.0, self.bugToggle)
        self.onNextChkThread    = threading.Timer(5.0, self.onNextChk)
        self.onNextToggleThread = threading.Timer(5.0, self.onNextToggle)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onInit(self):
        try:
            self.log('onInit')
            self.showChannelBug = SETTINGS.getSettingBool('Enable_ChannelBug')
            self.showOnNext     = SETTINGS.getSettingBool('Enable_OnNext')
            self.staticOverlay  = SETTINGS.getSettingBool("Static_Overlay")
            self.channelBugVal  = SETTINGS.getSettingInt("Channel_Bug_Interval")

            self.container = self.getControl(40000)
            
            self.static = self.getControl(40001)
            self.static.setVisible(self.staticOverlay)
            
            self.startOver = self.getControl(41002)
            self.startOver.setVisible(False)
            
            self.onNext = self.getControl(41003)
            self.onNext.setVisible(False)
            
            self.channelbug = self.getControl(41004)
            self.channelbug.setVisible(False)
                        
            self.overlayLayer = self.getControl(39999)
            self.overlayLayer.setVisible(False)
            
            self.myPlayer = Player()
            self.myPlayer.overlay = self
        
            # todo requires kodi core update. videowindow control requires setPosition,setHeight,setWidth functions.
            # https://github.com/xbmc/xbmc/issues/19467
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
            
            if self.load(): 
                self.overlayLayer.setVisible(True)
                self.log('showChannelBug = %s'%(self.showChannelBug))
                self.log('showOnNext = %s'%(self.showOnNext))
                if self.showChannelBug: self.bugToggle() #start bug timer
                if self.showOnNext:     self.onNextChk()#start onnext timer
            else: 
                self.closeOverlay()
        except Exception as e: 
            self.log("onInit, Failed! %s"%(e), xbmc.LOGERROR)
            self.closeOverlay()


    def load(self):
        try:
            self.log('load')
            self.pvritem = self.service.player.getPVRitem()
            if not self.pvritem or not isPseudoTV(): 
                return False

            self.citem       = self.pvritem.get('citem',{})
            self.channelbug.setImage(self.citem.get('logo',LOGO))

            self.isPlaylist  = self.pvritem.get('isPlaylist',False)
            self.nowitem     = self.pvritem.get('broadcastnow',{}) # current item
            self.nextitems   = self.pvritem.get('broadcastnext',[])
            del self.nextitems[PAGE_LIMIT:]# list of upcoming items, truncate for speed.
                            
            self.nowwriter   = getWriter(self.pvritem.get('broadcastnow',{}).get('writer',{}))
            self.nowwriter.get('art',{})['thumb'] = getThumb(self.nowwriter) #unify artwork
            
            self.nextwriters = []
            for nextitem in self.nextitems: 
                nextitem = getWriter(nextitem.get('writer',{}))
                nextitem.get('art',{})['thumb'] = getThumb(nextitem) #unify artwork
                self.nextwriters.append(nextitem)

            self.listitems   = [self.service.writer.dialog.buildItemListItem(self.nowwriter)]
            self.listitems.extend([self.service.writer.dialog.buildItemListItem(nextwriter) for nextwriter in self.nextwriters])
            
            self.container.reset()
            xbmc.sleep(100)
            self.container.addItems(self.listitems)
                        
            self.runActions(RULES_ACTION_OVERLAY, self.citem, inherited=self)
            self.static.setVisible(self.staticOverlay)
            self.myPlayer.onPlayBackStarted()
            self.log('load finished')
            return True
        except Exception as e: 
            self.log("load, Failed! %s"%(e), xbmc.LOGERROR)
            return False
     

    def getPlayerProgress(self):
        try:    return float(xbmc.getInfoLabel('Player.Progress'))
        except: return 0.0


    def getTimeRemaining(self):
        try:    return int(sum(x*y for x, y in zip(map(float, xbmc.getInfoLabel('Player.TimeRemaining(hh:mm:ss)').split(':')[::-1]), (1, 60, 3600, 86400))))
        except: return 0
   
   
    def playSFX(self, filename, cached=True):
        self.log('playSFX, filename = %s, cached = %s'%(filename,cached))
        xbmc.playSFX(filename, useCached=cached)
   
   
    def cancelOnNext(self): #channel changing and/or not playing cancel on next
        self.onNext.setVisible(False)
        if self.onNextToggleThread.is_alive(): 
            try: 
                self.onNextToggleThread.cancel()
                self.onNextToggleThread.join()
            except: pass


    def updateOnNext(self):
        try: #if playlist, pop older played item and refresh meta container.
            self.log('updateOnNext, isPlaylist = %s'%(self.isPlaylist))
            self.cancelOnNext()
            if self.isPlaylist:
                if len(self.listitems) > 0:
                    self.listitems.pop(0)
                    self.container.reset()
                    self.container.addItems(self.listitems)
                    return
        except Exception as e: self.log("updateOnNext, Failed! %s"%(e), xbmc.LOGERROR)
        

    def onNextChk(self):
        def playerAssert():
            try: #test playing item, contains title? remaining time / progress within parameters?
                titleAssert    = self.listitems[0].getLabel() == self.myPlayer.playingTitle
                remainAssert   = self.getTimeRemaining() <= NOTIFICATION_TIME_REMAINING
                progressAssert = self.getPlayerProgress() >= 75.0
                return (titleAssert & remainAssert & progressAssert)
            except: 
                return False
        try:
            if self.onNextToggleThread.is_alive():
                if not self.overlayLayer.isVisible(): 
                    self.cancelOnNext()
            else:
                if playerAssert(): 
                    self.onNextToggle()
                    
             #poll player every XXsecs.
            self.onNextChkThread = threading.Timer(NOTIFICATION_CHECK_TIME, self.onNextChk)
            self.onNextChkThread.name = "onNextChkThread"
            self.onNextChkThread.start()
        except Exception as e: self.log("onNextChk, Failed! %s"%(e), xbmc.LOGERROR)
        

    def onNextToggle(self, state=True):
        try:
            self.playSFX(BING_WAV)
            wait = {True:(NOTIFICATION_CHECK_TIME//2),False:float(self.myPlayer.OnNextWait)}[state]
            self.log('onNextToggle, state = %s, wait = %s'%(state,wait))
            self.onNext.setVisible(state)
            self.onNextToggleThread = threading.Timer(wait, self.onNextToggle, [not bool(state)])
            self.onNextToggleThread.name = "onNextToggleThread"
            self.onNextToggleThread.start()
        except Exception as e: self.log("onNextToggle, Failed! %s"%(e), xbmc.LOGERROR)
            
            
    def bugToggle(self, state=True):
        def getWait(state):
            if self.channelBugVal == -1: 
                onVAL  = self.getTimeRemaining()
                offVAL = 0.1
            elif self.channelBugVal == 0:
                onVAL  = random.randint(300,600)
                offVAL = random.randint(300,600)
            else:
                onVAL  = self.channelBugVal * 60
                offVAL = round(onVAL // 2)
            return {True:float(onVAL),False:float(offVAL)}[state]
        try:   
            wait = getWait(state)
            self.log('bugToggle, state = %s, wait = %s'%(state,wait))
            self.channelbug.setVisible(state)
            self.bugToggleThread = threading.Timer(wait, self.bugToggle, [not bool(state)])
            self.bugToggleThread.name = "bugToggleThread"
            self.bugToggleThread.start()
        except Exception as e: self.log("bugToggle, Failed! %s"%(e), xbmc.LOGERROR)

      
    def closeOverlay(self):
        self.log('closeOverlay')
        threads = [self.bugToggleThread,
                   self.onNextChkThread,
                   self.onNextToggleThread]
                   
        for thread_item in threads:
            if thread_item.is_alive(): 
                try: 
                    thread_item.cancel()
                    thread_item.join(1.0)
                except: pass
        self.close()


    def onAction(self, act):
        actionID = act.getId()
        actionBC = act.getButtonCode()
        self.log('onAction, actionID = %s, actionBC = %s'%(actionID,actionBC))
        if actionID == ACTION_PREVIOUS_MENU:
            xbmc.executebuiltin("Action(PreviousMenu)")
        elif actionID == ACTION_MOVE_LEFT:
            xbmc.executebuiltin("ActivateWindowAndFocus(pvrosdchannels)")
        elif actionID == ACTION_MOVE_RIGHT:
            xbmc.executebuiltin("ActivateWindowAndFocus(pvrchannelguide)")
        elif actionID == ACTION_MOVE_UP:
            self.service.writer.jsonRPC.sendButton('Up')
        elif actionID == ACTION_MOVE_DOWN:
            self.service.writer.jsonRPC.sendButton('Down')
        elif actionID == ACTION_SELECT_ITEM:
            self.service.writer.jsonRPC.sendButton('I')
        self.closeOverlay()