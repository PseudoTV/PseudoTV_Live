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

class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.start = 0
        
        
    def onPlayBackEnded(self):
        self.log('onPlayBackEnded')
        if self.overlay.isPlaylist:
            start = self.start + 1
            self.overlay.load(start)
        
        
class Overlay(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.pvritem          = {}
        self.channeldata      = {}
        self.nowitem          = {}
        self.nextitems        = [] 
        self.listitems        = []
        self.myPlayer         = Player()
        self.myPlayer.overlay = self
        
        self.bugToggleThread    = threading.Timer(CHANNELBUG_CHECK_TIME, self.bugToggle)
        self.onNextToggleThread = threading.Timer(NOTIFICATION_CHECK_TIME, self.onNextToggle)
        
        #place global values here before rules.
        self.showChannelBug  = True
        self.showOnNext      = getSettingBool('Enable_OnNext')
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def runActions(self, action, citem, parameter=None):
        self.log("runActions action = %s, channel = %s"%(action,citem))
        if not citem.get('id',''): 
            return parameter
            
        chrules = citem.get('rules',[])
        for chrule in chrules:
            ruleInstance = chrule['action']
            if ruleInstance.actions & action > 0:
                self.log("runActions performing channel rule: %s"%(chrule['name']))
                parameter = ruleInstance.runAction(action, self, parameter)
        return parameter


    def onInit(self):
        self.log('onInit')
        self.listitems   = []
        self.pvritem     = getCurrentChannelItem()
        self.isPlaylist  = self.pvritem['isPlaylist']
        
        self.container   = self.getControl(40000)
        self.container.reset()
        
        self.onNext      = self.getControl(41003)
        self.onNext.setVisible(False)
        
        self.channelbug  = self.getControl(41004)
        self.channelbug.setImage(self.pvritem.get('icon',LOGO))

        if self.load():
            if self.showChannelBug:
                self.bugToggle()
                
            if self.showOnNext:
                self.onNextToggle()
        else:
            self.closeOverlay()


    def reset(self):
        self.log('reset')
        self.onInit()
          

    def getTimeRemaining(self):
        return (sum(x*y for x, y in zip(map(float, xbmc.getInfoLabel('Player.TimeRemaining(hh:mm:ss)').split(':')[::-1]), (1, 60, 3600, 86400))))
       
       
    def onNextToggle(self):
        self.log('onNextToggle')
        try:
            if self.onNextToggleThread.isAlive(): 
                self.onNextToggleThread.cancel()
            
            timeReamining = self.getTimeRemaining()
            if timeReamining > 30 and timeReamining <= NOTIFICATION_TIME_BEFORE_END:
                self.onNext.setVisible(True)
            else:
                self.onNext.setVisible(False)
                
            self.onNextToggleThread = threading.Timer(NOTIFICATION_CHECK_TIME, self.onNextToggle)
            self.onNextToggleThread.name = "onNextToggleThread"
            self.onNextToggleThread.start()
        except Exception as e: self.log("onNextToggle, Failed! " + str(e), xbmc.LOGERROR)
            

    def bugToggle(self, state=True):
        self.log('bugToggle, state = %s'%(state))
        try:
            if self.bugToggleThread.isAlive(): 
                self.bugToggleThread.cancel()
            self.channelbug.setVisible(state)
            wait    = {True:float(random.randint(10,30)),False:float(random.randint(900,1800))}[state]
            nstate  = not bool(state)
            self.bugToggleThread = threading.Timer(wait, self.bugToggle, [nstate])
            self.bugToggleThread.name = "bugToggleThread"
            self.bugToggleThread.start()
        except Exception as e: self.log("bugToggle, Failed! " + str(e), xbmc.LOGERROR)

      
    def load(self, start=0):
        self.log('load, start = %s'%(start))
        try:
            if not self.pvritem or not isPseudoTV(): return False
            self.nowitem     = self.pvritem.get('broadcastnow',{}) # current item
            self.nextitems   = self.pvritem.get('broadcastnext',[])[slice(start, PAGE_LIMIT)] # list of upcoming items, truncate for speed.
            self.nowwriter   = getWriter(self.pvritem.get('broadcastnow',{}).get('writer',{}))
            self.channeldata = self.nowwriter.get('data',{})
            self.runActions(RULES_ACTION_OVERLAY, self.channeldata, self)
            
            # for key, value in self.channeldata.items(): setProperty('overlay.%s'%(key),str(value))
            self.listitems.append(buildItemListItem(self.nowwriter))
            self.listitems.extend([buildItemListItem(getWriter(nextitem.get('writer',{}))) for nextitem in self.nextitems])
            self.container.addItems(self.listitems)
            return True
        except Exception as e: 
            self.log("load, Failed! " + str(e), xbmc.LOGERROR)
            return False
                  
        
    def closeOverlay(self):
        self.log('closeOverlay')
        threads = [self.bugToggleThread,self.onNextToggleThread]
        for thread_item in threads:
            if thread_item.isAlive(): 
                thread_item.cancel()
        self.close()


    def onAction(self, act):
        self.closeOverlay()
        
        
    def onClick(self, controlId):
        self.closeOverlay()