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
from globals import *

class GUI(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.bugToggleThread = threading.Timer(15.0, self.bugToggle)
        
        
    def onInit(self):
        log('GUI: onInit')
        self.listitems = []
        self.maxDays    = getSettingInt('Max_Days')
        self.container  = self.getControl(40000)
        self.channelbug = self.getControl(41004)
        self.container.reset()
        self.load()
        self.bugToggle()
        
        
    def reset(self):
        log('GUI: reset')
        self.onInit()
        
        
        #todo nextup, onnow meta
    def load(self):
        log('GUI: load')
        try:
            pvritem   = getCurrentChannelItem()
            if not pvritem or not isPseudoTV(): self.closeOverlay()
            ruleslist = []#check overlay channel rules.
            setProperty('chlogo',pvritem.get('icon',LOGO))
            nowitem   = pvritem.get('broadcastnow',{}) # current item
            nextitems = pvritem.get('broadcastnext',[])[slice(0, self.maxDays)]
            self.listitems.append(buildItemListItem(loadJSON(nowitem.get('writer',{}))))
            self.listitems.extend([buildItemListItem(loadJSON(nextitem.get('writer',''))) for nextitem in nextitems]) 
            self.container.addItems(self.listitems)
            self.addItems(self.listitems)
        except Exception as e: log("GUI: load, Failed! " + str(e), xbmc.LOGERROR)
        
        
    def bugToggle(self, state=True):
        log('GUI: bugToggle, state = %s'%(state))
        try:
            if self.bugToggleThread.isAlive(): 
                self.bugToggleThread.cancel()
            self.channelbug.setVisible(state)
            wait    = {True:float(random.randint(10,30)),False:float(random.randint(900,1800))}[state]
            state   = not bool(state)
            self.bugToggleThread = threading.Timer(wait, self.bugToggle, [state])
            self.bugToggleThread.name = "bugToggleThread"
            self.bugToggleThread.start()
        except Exception as e: log("GUI: bugToggle, Failed! " + str(e), xbmc.LOGERROR)


    def closeOverlay(self):
        if self.bugToggleThread.isAlive(): 
            self.bugToggleThread.cancel()
        self.close()


    def onAction(self, act):
        self.closeOverlay()
        
        
    def onClick(self, controlId):
        self.closeOverlay()