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

class GUI(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.myPlayer        = MY_PLAYER
        self.pvritem         = {}
        self.listitems       = []
        self.maxDays         = getSettingInt('Max_Days')
        self.bugToggleThread = threading.Timer(CHANNELBUG_CHECK_TIME, self.bugToggle)
        # self.onNextThread    = threading.Timer(NOTIFICATION_CHECK_TIME, self.checkOnNext)
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def onInit(self):
        self.log('onInit')
        self.listitems  = []
        self.nowitem    = []
        self.nextitems  = []
        self.pvritem    = getCurrentChannelItem()
        
        self.container  = self.getControl(40000)
        self.container.reset()
        
        self.channelbug = self.getControl(41004)
        self.channelbug.setImage(self.pvritem.get('icon',LOGO))
        
        if self.load():
            self.bugToggle()
            # self.checkOnNext()
        else: self.closeOverlay()
        
        
    def reset(self):
        self.log('reset')
        self.onInit()
        
        
    def load(self):
        self.log('load')
        try:
            if not self.pvritem or not isPseudoTV(): return False
            ruleslist      = []#check overlay channel rules.
            self.nowitem   = self.pvritem.get('broadcastnow',{}) # current item
            self.nextitems = self.pvritem.get('broadcastnext',[])[slice(0, PAGE_LIMIT)] # list of upcoming items, truncate for speed.
            self.listitems.append(buildItemListItem(loadJSON(self.nowitem.get('writer',{}))))
            self.listitems.extend([buildItemListItem(loadJSON(nextitem.get('writer',''))) for nextitem in self.nextitems]) 
            self.container.addItems(self.listitems)
            return True
        except Exception as e: 
            self.log("load, Failed! " + str(e), xbmc.LOGERROR)
            return False
        
             
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


    # def getCurrentPosition(self):
        # self.log('getCurrentPosition')
        # for idx, listitem in enumerate(self.nextitems): #todo rework to include start times?
            # if listitem.getVideoInfoTag().getTitle() == self.myPlayer.getVideoInfoTag().getTitle(): 
                # return idx
        

    def checkOnNext(self):
        self.log('checkOnNext')
        # if self.onNextThread.isAlive(): 
            # self.onNextThread.cancel()
        # pos = self.getCurrentPosition()
        # print(self.pvritem)
        # print(pos,self.listitems[pos])
        # print(self.listitems[pos].getPath())
        # print(self.listitems[pos].getVideoInfoTag().getDuration())
        # print(self.listitems[pos].getVideoInfoTag().getTitle())
        # print(self.listitems[pos].getProperty('duration'))
        # self.onNextThread = threading.Timer(NOTIFICATION_CHECK_TIME, self.checkOnNext)
        # self.onNextThread.name = "onNextThread"
        # self.onNextThread.start()
        # timedif = self.listitems[self.getCurrentPosition()].getProperty('runtime') - self.myPlayer.getTime()
        


    # def onNextToggle(self, state=True):
        # self.log('onNextToggle, state = %s'%(state))
        
        # # if self.notificationShowedNotif == False and timedif < NOTIFICATION_TIME_BEFORE_END and timedif > NOTIFICATION_DISPLAY_TIME:
            # # nextshow = 


    def closeOverlay(self):
        self.log('closeOverlay')
        if self.bugToggleThread.isAlive(): 
            self.bugToggleThread.cancel()
        # if self.onNextThread.isAlive(): 
            # self.onNextThread.cancel()
        self.close()


    def onAction(self, act):
        self.closeOverlay()
        
        
    def onClick(self, controlId):
        self.closeOverlay()