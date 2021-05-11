  # Copyright (C) 2021 Lunatixz


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
from resources.lib.globals     import *

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.playingTitle = ""
            
            
    def onPlayBackStarted(self):
        self.overlay.log('onPlayBackStarted')
        self.playingTitle = xbmc.getInfoLabel('Player.Title')
        
        
    def onPlayBackEnded(self):
        self.overlay.log('onPlayBackEnded')
        self.playingTitle = ""
        self.overlay.updateOnNext()
    
    
class Overlay(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.player             = kwargs.get('player')
        self.service            = self.player.myService
        self.rules              = self.service.rules
        self.dialog             = self.service.dialog
        self.monitor            = self.service.monitor
        self.ruleList           = {}
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
        self.bugToggleThread    = threading.Timer(5.0, self.bugToggle)
        self.onNextChkThread    = threading.Timer(5.0, self.onNextChk)
        self.onNextToggleThread = threading.Timer(5.0, self.onNextToggle)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def runActions(self, action, citem, parameter=None):
        self.log("runActions action = %s, channel = %s"%(action,citem))
        if not citem.get('id',''): return parameter
        ruleList = self.ruleList.get(citem['id'],[])
        for rule in ruleList:
            if action in rule.actions:
                self.log("runActions performing channel rule: %s"%(rule.name))
                parameter = rule.runAction(action, self, parameter)
        return parameter


    def onInit(self):
        try:
            self.log('onInit')            
            self.staticOverlay  = SETTINGS.getSettingBool("Static_Overlay")
            self.showChannelBug = SETTINGS.getSettingBool('Enable_ChannelBug')
            self.showOnNext     = SETTINGS.getSettingBool('Enable_OnNext')
            
            self.overlayToggle(False)
            self.container = self.getControl(40000)
            
            self.static = self.getControl(40001)
            self.static.setVisible(self.staticOverlay)
            
            self.startOver = self.getControl(41002)
            self.startOver.setVisible(False)
            
            self.onNext = self.getControl(41003)
            self.onNext.setVisible(False)
            
            self.channelbug = self.getControl(41004)
            self.channelbug.setVisible(False)
            
            self.myPlayer = Player()
            self.myPlayer.overlay = self
        
            # todo requires kodi core update. videowindow control requires setPosition,setHeight,setWidth functions.
            # https://github.com/xbmc/xbmc/issues/19467
            # self.videoWindow = self.getControl(41000)
            # self.videoWindow.setPosition(0, 0)
            # self.videoWindow.setHeight(self.videoWindow.getHeight())
            # self.videoWindow.setWidth(self.videoWindow.getWidth())
            
            if self.load(): 
                self.overlayToggle(True)
                if self.showChannelBug: self.bugToggle() #start bug timer
                if self.showOnNext: self.onNextChk()#start onnext timer
            else: 
                self.closeOverlay()
        except Exception as e: 
            self.log("onInit, Failed! " + str(e), xbmc.LOGERROR)
            self.closeOverlay()


    def overlayToggle(self, state=True):
        try:
            self.log('overlayToggle, state = %s'%(state))
            self.getControl(39999).setVisible(state)
        except Exception as e: self.log("overlayToggle, Failed! " + str(e), xbmc.LOGERROR)
        

    def isoverlayVisible(self):
        try:    return self.getControl(39999).isVisible()
        except: return False


    def load(self):
        try:
            self.log('load')
            self.pvritem = self.player.getPVRitem()
            if not self.pvritem or not isPseudoTV(): 
                return False
                
            self.citem   = self.pvritem.get('citem',{})
            self.container.reset()
            
            self.isPlaylist  = self.pvritem.get('isPlaylist',False)
            self.channelbug.setImage(self.pvritem.get('icon',LOGO))
        
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

            self.listitems   = [self.dialog.buildItemListItem(self.nowwriter)]
            self.listitems.extend([self.dialog.buildItemListItem(nextwriter) for nextwriter in self.nextwriters])
            self.container.addItems(self.listitems)
                        
            self.ruleList    = self.rules.loadRules([self.citem])
            self.runActions(RULES_ACTION_OVERLAY, self.citem)
            self.static.setVisible(self.staticOverlay)
            self.myPlayer.onPlayBackStarted()
            self.log('load finished')
            return True
        except Exception as e: 
            self.log("load, Failed! " + str(e), xbmc.LOGERROR)
            return False
     

    def getPlayerProgress(self):
        try:    return float(xbmc.getInfoLabel('Player.Progress'))
        except: return 0.0


    def getTimeRemaining(self):
        try:    return int(sum(x*y for x, y in zip(map(float, xbmc.getInfoLabel('Player.TimeRemaining(hh:mm:ss)').split(':')[::-1]), (1, 60, 3600, 86400))))
        except: return 0
   
   
    def playerAssert(self):
        try:    
            titleAssert    = self.listitems[0].getLabel() == self.myPlayer.playingTitle
            remainAssert   = self.getTimeRemaining() <= NOTIFICATION_TIME_REMAINING
            progressAssert = self.getPlayerProgress() >= 75.0
            return (titleAssert & remainAssert & progressAssert)
        except: return False
        
        
    def cancelOnNext(self):
        self.onNext.setVisible(False)
        if self.onNextToggleThread.is_alive(): 
            self.onNextToggleThread.cancel()
            try: self.onNextToggleThread.join()
            except: pass


    def updateOnNext(self):
        try:
            self.log('updateOnNext, isPlaylist = %s'%(self.isPlaylist))
            self.cancelOnNext()            
            if self.isPlaylist:
                if len(self.listitems) > 0:
                    self.listitems.pop(0)
                    self.container.reset()
                    self.container.addItems(self.listitems)
                    return
        except Exception as e: self.log("updateOnNext, Failed! " + str(e), xbmc.LOGERROR)
        

    def onNextChk(self):
        try:
            if self.onNextChkThread.is_alive(): 
                self.onNextChkThread.cancel()
                try: self.onNextChkThread.join()
                except: pass
            
            if self.onNextToggleThread.is_alive() and not self.isoverlayVisible(): 
                self.cancelOnNext()
            elif not self.onNextToggleThread.is_alive() and self.playerAssert():
                self.onNextToggle()
            
            self.onNextChkThread = threading.Timer(NOTIFICATION_CHECK_TIME, self.onNextChk)
            self.onNextChkThread.name = "onNextChkThread"
            self.onNextChkThread.start()
        except Exception as e: self.log("onNextChk, Failed! " + str(e), xbmc.LOGERROR)
        

    def onNextToggle(self, state=True):
        try:
            self.log('onNextToggle, state = %s'%(state))
            if self.onNextToggleThread.is_alive(): 
                self.onNextToggleThread.cancel()
                try: self.onNextToggleThread.join()
                except: pass
                    
            wait   = {True:float(10),False:float(random.randint(180,300))}[state]
            nstate = not bool(state)
            self.onNext.setVisible(state)
            self.onNextToggleThread = threading.Timer(wait, self.onNextToggle, [nstate])
            self.onNextToggleThread.name = "onNextToggleThread"
            self.onNextToggleThread.start()
        except Exception as e: self.log("onNextToggle, Failed! " + str(e), xbmc.LOGERROR)
            
            
    def bugToggle(self, state=True):
        try:
            self.log('bugToggle, state = %s'%(state))
            if self.bugToggleThread.is_alive(): 
                self.bugToggleThread.cancel()
                try: self.bugToggleThread.join()
                except: pass
            wait   = {True:float(random.randint(30,60)),False:float(random.randint(300,600))}[state]
            nstate = not bool(state)
            self.channelbug.setVisible(state)
            self.bugToggleThread = threading.Timer(wait, self.bugToggle, [nstate])
            self.bugToggleThread.name = "bugToggleThread"
            self.bugToggleThread.start()
        except Exception as e: self.log("bugToggle, Failed! " + str(e), xbmc.LOGERROR)

      
    def closeOverlay(self):
        self.log('closeOverlay')
        threads = [self.bugToggleThread,self.onNextChkThread,self.onNextToggleThread]
        for thread_item in threads:
            if thread_item.is_alive(): 
                thread_item.cancel()
                try: thread_item.join(1.0)
                except: pass
        self.close()


    def onAction(self, act):
        self.log('onAction, actionid = %s'%(act.getId()))
        # actionid = act.getId()
        # if actionid in ACTION_SHOW_INFO:
            # xbmc.executebuiltin("action(Info)")
        # elif actionid in ACTION_PREVIOUS_MENU:
            # xbmc.executebuiltin("action(PreviousMenu)") 
        self.closeOverlay()