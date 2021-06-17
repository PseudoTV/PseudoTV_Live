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
        
        
    def onPlayBackStarted(self):
        self.overlay.reload()


    def onAVChange(self):
        self.overlay.cancelOnNext()
        
        
    def onPlayBackStopped(self):
        self.overlay.cancelOnNext()
        
        
    def onPlayBackEnded(self):
        self.overlay.cancelOnNext()
    
    
class Widgets(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)
        self.config = kwargs.get('config')


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onInit(self, refresh=False):
        self.log('onInit, refresh = %s'%(refresh))
        self.windowProperty = Properties(winID=xbmcgui.getCurrentWindowId())

        self.myPlayer = Player()
        self.myPlayer.overlay = self
    
        self.container = self.getControl(40000)
        self.container.reset()

        if self.load(): ...
        else: self.closeWidgets()
               

    def load(self):
        self.log('load')
        return True
     

    def getTimeRemaining(self):
        try:    return (sum(x*y for x, y in zip(map(float, xbmc.getInfoLabel('Player.TimeRemaining(hh:mm:ss)').split(':')[::-1]), (1, 60, 3600, 86400))))
        except: return 0

              
    def closeWidgets(self):
        self.log('closeWidgets')
        self.close()


    def onAction(self, act):
        self.log('onAction, actionid = %s'%(act.getId()))
        
        
        

    # def addLink(self, name, channel, path, mode='',icon=ICON, liz=None, total=0):
        # if liz is None:
            # liz=xbmcgui.ListItem(name)
            # liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
            # liz.setArt({'thumb':icon,'logo':icon,'icon':icon})
        # self.log('addLink, name = %s'%(name))
        # u=self.sysARG[0]+"?url="+urllib.parse.quote(path)+"&channel="+str(channel)+"&name="+urllib.parse.quote(name)+"&mode="+str(mode)
        # xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,totalItems=total)


    # def addDir(self, name, channel, path, mode='',icon=ICON, liz=None):
        # self.log('addDir, name = %s'%(name))
        # if liz is None:
            # liz=xbmcgui.ListItem(name)
            # liz.setInfo(type="Video", infoLabels={"mediatype":"video","label":name,"title":name})
            # liz.setArt({'thumb':icon,'logo':icon,'icon':icon})
        # liz.setProperty('IsPlayable', 'false')
        # u=self.sysARG[0]+"?url="+urllib.parse.quote(path)+"&channel="+str(channel)+"&name="+urllib.parse.quote(name)+"&mode="+str(mode)
        # xbmcplugin.addDirectoryItem(handle=int(self.sysARG[1]),url=u,listitem=liz,isFolder=True)

        