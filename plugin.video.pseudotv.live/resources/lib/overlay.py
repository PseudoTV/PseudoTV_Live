  # Copyright (C) 2020 Lunatixz


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

# -*- coding: utf-8 -*-
from resources.lib.globals import *

class MyPlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        
        
    def onPlayBackStarted(self):
        if self.overlay.reload() and self.isPlaying():
            xbmc.executebuiltin("ActivateWindow(fullscreenvideo)")


    def onAVChange(self):
        self.onPlayBackEnded()
        
        
    def onPlayBackStopped(self):
        self.onPlayBackEnded()
        
        
    def onPlayBackEnded(self):
        self.overlay.onNext.setVisible(False)
        if self.overlay.onNextToggleThread.isAlive(): 
            self.overlay.onNextToggleThread.cancel()


class Overlay(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.pvritem            = {}
        self.channeldata        = {}
        self.nowitem            = {}
        self.nextitems          = [] 
        self.listitems          = []
        self.listcycle          = []
        self.isPlaylist         = False
        
        self.bugToggleThread    = threading.Timer(CHANNELBUG_CHECK_TIME  , self.bugToggle)
        self.onNextThread       = threading.Timer(NOTIFICATION_CHECK_TIME, self.onNextChk)
        self.onNextToggleThread = threading.Timer(NOTIFICATION_CHECK_TIME, self.onNextToggle)
        
        #place global values here before rules.
        self.showChannelBug     = True
        self.enableOnNext       = getSettingBool('Enable_OnNext')
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def runActions(self, action, citem, parameter=None):
        self.log("runActions action = %s, channel = %s"%(action,citem))
        if not citem.get('id',''): return parameter
        chrules = citem.get('rules',[])
        for chrule in chrules:
            if chrule.get('id',0) == 0: continue
            ruleInstance = chrule['action']
            if ruleInstance.actions & action > 0:
                self.log("runActions performing channel rule: %s"%(chrule['name']))
                parameter = ruleInstance.runAction(action, self, parameter)
        return parameter


    def onInit(self):
        self.log('onInit')
        self.myPlayer           = MyPlayer()
        self.myPlayer.overlay   = self
        
        self.onNext = self.getControl(41003)
        self.onNext.setVisible(False)
        
        self.channelbug  = self.getControl(41004)
        self.container   = self.getControl(40000)
        self.container.reset()
        
        self.listitems   = []
        self.pvritem     = {}
        
        self.enableOnNext = getSettingBool('Enable_OnNext')
        
        
        if self.load():
            self.runActions(RULES_ACTION_OVERLAY, self.channeldata, self)
            if self.showChannelBug:
                self.bugToggle()
                
            if self.enableOnNext:
                self.onNextChk()
        else:
            self.closeOverlay()


    def reset(self):
        self.log('reset')
        self.onInit()
        

    def reload(self):
        self.log('reload, isPlaylist = %s'%(self.isPlaylist))
        if self.isPlaylist:
            return self.nextListitem()
        else:
            return self.load()
          

    def getTimeRemaining(self):
        try:    return (sum(x*y for x, y in zip(map(float, xbmc.getInfoLabel('Player.TimeRemaining(hh:mm:ss)').split(':')[::-1]), (1, 60, 3600, 86400))))
        except: return 0


    def onNextChk(self):
        try:
            if self.onNextThread.isAlive(): 
                self.onNextThread.cancel()
            timeRemaining = int(self.getTimeRemaining())
            if (timeRemaining < NOTIFICATION_TIME_REMAINING and timeRemaining >= NOTIFICATION_TIME_BEFORE_END):
                if not self.onNext.isVisible(): self.onNextToggle(True)
            self.onNextThread = threading.Timer(NOTIFICATION_CHECK_TIME, self.onNextChk)
            self.onNextThread.name = "onNextThread"
            self.onNextThread.start()
        except Exception as e: self.log("onNextChk, Failed! " + str(e), xbmc.LOGERROR)
            
            
    def onNextToggle(self, state=True):
        self.log('onNextToggle, state = %s'%(state))
        try:
            if self.onNextToggleThread.isAlive(): 
                self.onNextToggleThread.cancel()
            self.onNext.setVisible(state)
            wait    = {True:float(random.randint(15,30)),False:float(random.randint(15,30))}[state]
            nstate  = not bool(state)
            self.onNextToggleThread = threading.Timer(wait, self.onNextToggle, [nstate])
            self.onNextToggleThread.name = "onNextToggleThread"
            self.onNextToggleThread.start()
        except Exception as e: self.log("onNextToggle, Failed! " + str(e), xbmc.LOGERROR)
            

    def bugToggle(self, state=True):
        self.log('bugToggle, state = %s'%(state))
        try:
            if self.bugToggleThread.isAlive(): 
                self.bugToggleThread.cancel()
            self.channelbug.setVisible(state)
            wait    = {True:float(random.randint(30,60)),False:float(random.randint(600,900))}[state]
            nstate  = not bool(state)
            self.bugToggleThread = threading.Timer(wait, self.bugToggle, [nstate])
            self.bugToggleThread.name = "bugToggleThread"
            self.bugToggleThread.start()
        except Exception as e: self.log("bugToggle, Failed! " + str(e), xbmc.LOGERROR)


    def load(self):
        self.log('load')
        try:
            self.pvritem = getCurrentChannelItem()
            if not self.pvritem or not isPseudoTV(): return False
            self.container.reset()
            
            self.isPlaylist  = self.pvritem.get('isPlaylist',False)
            self.channelbug.setImage(self.pvritem.get('icon',LOGO))
        
            self.nowitem     = self.pvritem.get('broadcastnow',{}) # current item
            self.nextitems   = self.pvritem.get('broadcastnext',[])[slice(0, PAGE_LIMIT)] # list of upcoming items, truncate for speed.
            self.nowwriter   = getWriter(self.pvritem.get('broadcastnow',{}).get('writer',{}))
            self.channeldata = self.nowwriter.get('data',{})
            
            self.listitems = [buildItemListItem(self.nowwriter)]
            self.listitems.extend([buildItemListItem(getWriter(nextitem.get('writer',{}))) for nextitem in self.nextitems])
            self.container.addItems(self.listitems)
            return True
        except Exception as e: 
            self.log("load, Failed! " + str(e), xbmc.LOGERROR)
            return False
                 
                 
    def nextListitem(self):
        try:
            self.log('nextListitem, listitems = %s'%(len(self.listitems)))
            self.listitems.pop(0)
            self.container.reset()
            self.container.addItems(self.listitems)
            return True
        except Exception as e: 
            self.log("nextListitem, Failed! " + str(e), xbmc.LOGERROR)
            return False
        
    def closeOverlay(self):
        self.log('closeOverlay')
        threads = [self.bugToggleThread,self.onNextToggleThread,self.onNextThread]
        for thread_item in threads:
            if thread_item.isAlive(): 
                thread_item.cancel()
        self.close()


    def onAction(self, act):
        self.closeOverlay()
        
        
    def onClick(self, controlId):
        self.closeOverlay()