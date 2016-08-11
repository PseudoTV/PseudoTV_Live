#   Copyright (C) 2015 Anisan, Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import time
import threading
import xbmc
import xbmcgui
import xbmcaddon
import datetime
import random
from Globals import *

rootDir = ADDON_PATH
if rootDir[-1] == ';':rootDir = rootDir[0:-1]
resDir = os.path.join(rootDir, 'resources')
skinsDir = os.path.join(resDir, 'skins')
addon_image_path = os.path.join( resDir, "skins", "Default", "media")
background = (os.path.join( addon_image_path, "idle", "Background"))
digits = os.path.join( addon_image_path, "idle", "Digits")
backMEDIA_LOC = xbmc.translatePath(os.path.join(MEDIA_LOC, BACKGROUND_SKIN))

cacheDir = xbmc.translatePath('special://profile/addon_data/script.twitXBMC/cache/')
if not os.path.exists(cacheDir): os.makedirs(cacheDir)

EXIT_SCRIPT = ( 9, 6, 10, 247, 275, 61467, 216, 257, 61448, )
CANCEL_DIALOG = EXIT_SCRIPT + ( 1, 2, 3, 4, 12, 122, 75, 7, 92, )


FLIP1=210
DIGIT1 = 211
DIGIT11 = 2111
DIGIT12 = 2112
DIGIT110 = 21110
DIGIT120 = 21120
DIGIT2 = 212
DIGIT21 = 2121
DIGIT22 = 2122
DIGIT210 = 21210
DIGIT220 = 21220
FLIP2=220
DIGIT3 = 221
DIGIT31 = 2211
DIGIT32 = 2212
DIGIT310 = 22110
DIGIT320 = 22120
DIGIT4 = 222
DIGIT41 = 2221
DIGIT42 = 2222
DIGIT410 = 22210
DIGIT420 = 22220
LABEL = 224
CLOCK = 200


class GUI( xbmcgui.WindowXMLDialog ):
    class TimeCounter(threading.Thread):
        def __init__(self, ui):
            threading.Thread.__init__(self)
            self.ui = ui
            self.h1=0
            self.h2=0
            self.m1=0
            self.m2=0
            self.clockMode = REAL_SETTINGS.getSetting("ClockMode")
            self.ui.getControl(100).setImage(backMEDIA_LOC)
            
            
        def run(self):
            print 'run'
            i=0
            while (not self.ui.terminate):
                time.sleep(1)
                dtn = datetime.datetime.now()
                
                if self.clockMode == "1":
                    dte = dtn.strftime("%d.%m.%Y %H:%M:%S")
                    h = dtn.strftime("%H")
                else:
                    dte = dtn.strftime("%d.%m.%Y %I:%M:%S")
                    h = dtn.strftime("%I")
                    
                h1=int(h[0])
                h2=int(h[1])
                m = dtn.strftime("%M")
                m1=int(m[0])
                m2=int(m[1])
                if (self.h1!=h1)|(self.h2!=h2):
                    Flip = self.ui.Fliper(self.ui,1,self.h1,h1,self.h2,h2)
                    Flip.start()
                    self.h1=h1
                    self.h2=h2
                if (self.m1!=m1)|(self.m2!=m2):
                    Flip = self.ui.Fliper(self.ui,2,self.m1,m1,self.m2,m2)
                    Flip.start()
                    self.m1=m1
                    self.m2=m2
                
                # print background+"|"+str(i)+".png"
                self.ui.getControl( LABEL ).setLabel(dte)
            
            
    class Fliper(threading.Thread):
        def __init__(self, ui,flip,old1,new1,old2,new2):
            threading.Thread.__init__(self)
            self.ui = ui
            self.flip = flip
            self.old1 = old1 
            self.new1 = new1
            self.old2 = old2
            self.new2 = new2
            
            
        def run (self):
            if (self.flip==1):
                self.flip1()
            else:
                self.flip2()
        
        
        def flip1(self):
            print 'flip1'
            i=1
            print (os.path.join(background,"0.png"))
            print (os.path.join(digits,str(self.new1)+"(1).png"))
            self.ui.getControl( FLIP1 ).setImage(os.path.join(background,"0.png"))
            self.ui.getControl( FLIP1 ).setVisible(1)
            self.ui.getControl( DIGIT11 ).setImage(os.path.join(digits,str(self.new1)+"(1).png"))
            self.ui.getControl( DIGIT12 ).setImage(os.path.join(digits,str(self.old1)+"(2).png"))
            self.ui.getControl( DIGIT110 ).setImage(os.path.join(digits,str(self.old1)+"(1).png"))
            self.ui.getControl( DIGIT21 ).setImage(os.path.join(digits,str(self.new2)+"(1).png"))
            self.ui.getControl( DIGIT22 ).setImage(os.path.join(digits,str(self.old2)+"(2).png"))
            self.ui.getControl( DIGIT210 ).setImage(os.path.join(digits,str(self.old2)+"(1).png"))
            self.ui.getControl( DIGIT110 ).setHeight(40)
            self.ui.getControl( DIGIT110 ).setPosition(15,24)
            self.ui.getControl( DIGIT210 ).setHeight(40)
            self.ui.getControl( DIGIT210 ).setPosition(65,24)
            self.ui.getControl( DIGIT110 ).setVisible(1)
            self.ui.getControl( DIGIT210 ).setVisible(1)
            self.ui.getControl( DIGIT12 ).setVisible(1)
            self.ui.getControl( DIGIT22 ).setVisible(1)
            self.ui.getControl( DIGIT1 ).setVisible(0)
            self.ui.getControl( DIGIT2 ).setVisible(0)
            self.ui.getControl( DIGIT11 ).setVisible(1)
            self.ui.getControl( DIGIT21 ).setVisible(1)
            h=40
            while (i<12):
                time.sleep(0.01)
                # print background+ "|"+ str(i)+".png"
                self.ui.getControl( FLIP1 ).setImage(os.path.join(background,str(i)+".png"))
                h=h-3
                self.ui.getControl( DIGIT110 ).setPosition(15,24+(40-h))
                self.ui.getControl( DIGIT110 ).setHeight(h)
                self.ui.getControl( DIGIT210 ).setPosition(65,24+(40-h))
                self.ui.getControl( DIGIT210 ).setHeight(h)
                i = i +1
            h=43
            self.ui.getControl( DIGIT110 ).setVisible(0)
            self.ui.getControl( DIGIT210 ).setVisible(0)
            self.ui.getControl( DIGIT120 ).setHeight(3)
            self.ui.getControl( DIGIT120 ).setImage(os.path.join(digits,str(self.new1)+"(2).png"))
            self.ui.getControl( DIGIT220 ).setHeight(3)
            self.ui.getControl( DIGIT220 ).setImage(os.path.join(digits,str(self.new2)+"(2).png"))
            self.ui.getControl( DIGIT120 ).setVisible(1)
            self.ui.getControl( DIGIT220 ).setVisible(1)
            h=3
            while (i<20):
                time.sleep(0.01)
                print background+ "|"+ str(i)+".png"
                h=h+4
                self.ui.getControl( FLIP1 ).setImage(os.path.join(background,str(i)+".png"))
                self.ui.getControl( DIGIT120 ).setHeight(h)
                self.ui.getControl( DIGIT220 ).setHeight(h)
                i = i +1
            self.ui.getControl( DIGIT1 ).setImage(os.path.join(digits,str(self.new1)+".png"))
            self.ui.getControl( DIGIT2 ).setImage(os.path.join(digits,str(self.new2)+".png"))
            self.ui.getControl( DIGIT1 ).setVisible(1)
            self.ui.getControl( DIGIT2 ).setVisible(1)
            self.ui.getControl( DIGIT11 ).setVisible(0)
            self.ui.getControl( DIGIT12 ).setVisible(0)
            self.ui.getControl( DIGIT120 ).setVisible(0)
            self.ui.getControl( DIGIT21 ).setVisible(0)
            self.ui.getControl( DIGIT22 ).setVisible(0)
            self.ui.getControl( DIGIT220 ).setVisible(0)
            self.ui.getControl( FLIP1 ).setVisible(0)
        
        
        def flip2(self):
            i=1
            self.ui.getControl( FLIP2 ).setImage(os.path.join(background,"0.png"))
            self.ui.getControl( FLIP2 ).setVisible(1)
            self.ui.getControl( DIGIT31 ).setImage(os.path.join(digits,str(self.new1)+"(1).png"))
            self.ui.getControl( DIGIT32 ).setImage(os.path.join(digits,str(self.old1)+"(2).png"))
            self.ui.getControl( DIGIT310 ).setImage(os.path.join(digits,str(self.old1)+"(1).png"))
            self.ui.getControl( DIGIT41 ).setImage(os.path.join(digits,str(self.new2)+"(1).png"))
            self.ui.getControl( DIGIT42 ).setImage(os.path.join(digits,str(self.old2)+"(2).png"))
            self.ui.getControl( DIGIT410 ).setImage(os.path.join(digits,str(self.old2)+"(1).png"))
            self.ui.getControl( DIGIT310 ).setHeight(40)
            self.ui.getControl( DIGIT310 ).setPosition(15,24)
            self.ui.getControl( DIGIT410 ).setHeight(40)
            self.ui.getControl( DIGIT410 ).setPosition(65,24)
            self.ui.getControl( DIGIT310 ).setVisible(1)
            self.ui.getControl( DIGIT410 ).setVisible(1)
            self.ui.getControl( DIGIT32 ).setVisible(1)
            self.ui.getControl( DIGIT42 ).setVisible(1)
            self.ui.getControl( DIGIT3 ).setVisible(0)
            self.ui.getControl( DIGIT4 ).setVisible(0)
            self.ui.getControl( DIGIT31 ).setVisible(1)
            self.ui.getControl( DIGIT41 ).setVisible(1)
            h=40
            while (i<12):
                time.sleep(0.01)
                print background+ "|"+ str(i)+".png"
                self.ui.getControl( FLIP2 ).setImage(os.path.join(background,str(i)+".png"))
                h=h-3
                self.ui.getControl( DIGIT310 ).setPosition(15,24+(40-h))
                self.ui.getControl( DIGIT310 ).setHeight(h)
                self.ui.getControl( DIGIT410 ).setPosition(65,24+(40-h))
                self.ui.getControl( DIGIT410 ).setHeight(h)
                i = i +1
            h=43
            self.ui.getControl( DIGIT310 ).setVisible(0)
            self.ui.getControl( DIGIT410 ).setVisible(0)
            self.ui.getControl( DIGIT320 ).setHeight(3)
            self.ui.getControl( DIGIT320 ).setImage(os.path.join(digits,str(self.new1)+"(2).png"))
            self.ui.getControl( DIGIT420 ).setHeight(3)
            self.ui.getControl( DIGIT420 ).setImage(os.path.join(digits,str(self.new2)+"(2).png"))
            self.ui.getControl( DIGIT320 ).setVisible(1)
            self.ui.getControl( DIGIT420 ).setVisible(1)
            h=3
            while (i<20):
                time.sleep(0.01)
                print background+ "|"+ str(i)+".png"
                h=h+4
                self.ui.getControl( FLIP2 ).setImage(os.path.join(background,str(i)+".png"))
                self.ui.getControl( DIGIT320 ).setHeight(h)
                self.ui.getControl( DIGIT420 ).setHeight(h)
                i = i +1
            self.ui.getControl( DIGIT3 ).setImage(os.path.join(digits,str(self.new1)+".png"))
            self.ui.getControl( DIGIT4 ).setImage(os.path.join(digits,str(self.new2)+".png"))
            self.ui.getControl( DIGIT3 ).setVisible(1)
            self.ui.getControl( DIGIT4 ).setVisible(1)
            self.ui.getControl( DIGIT31 ).setVisible(0)
            self.ui.getControl( DIGIT32 ).setVisible(0)
            self.ui.getControl( DIGIT320 ).setVisible(0)
            self.ui.getControl( DIGIT41 ).setVisible(0)
            self.ui.getControl( DIGIT42 ).setVisible(0)
            self.ui.getControl( DIGIT420 ).setVisible(0)
            self.ui.getControl( FLIP2 ).setVisible(0)
          
          
    class MoveClock(threading.Thread):
        def __init__(self, ui):
            threading.Thread.__init__(self)
            self.ui = ui
            
            
        def run(self):
            i =0
            while (not self.ui.terminate):
                time.sleep(1)
                i=i+1
                if (i>4):
                    i=0
                    x = random.randint(0,990)
                    y = random.randint(0,570)
                    self.ui.getControl( CLOCK ).setPosition(x,y)
            
            
    def __init__( self, *args, **kwargs ):
        self.terminate = False


    def onInit( self ):
        counter = self.TimeCounter(self)
        counter.start()
        mover = self.MoveClock(self)
        mover.start()
    
   
    def onClick( self, controlId ):
        pass	
        
        
    def onFocus( self, controlId ):
        pass
    
    
    def onAction( self, action ):
        self.terminate = True
        self.close()