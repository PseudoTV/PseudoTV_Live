  # Copyright (C) 2024 Lunatixz


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
from resources import Resources
from rules     import RulesList

# class Video(xbmcgui.WindowXML):
    # #todo adv. rule apply overlay ie. scanline, etc to videowindow.
    # def onInit(self):
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
        self.player = kwargs.get('player' ,None)


    def onInit(self):
        try:
            logo = (self.player.sysInfo.get('citem',{}).get('logo',(BUILTIN.getInfoLabel('Art(icon)','Player') or  COLOR_LOGO)))
            self.getControl(40001).setVisibleCondition('[!Player.Playing]')
            self.getControl(40002).setImage(COLOR_LOGO if logo.endswith('wlogo.png') else logo)
            self.getControl(40003).setText(LANGUAGE(32104)%(self.player.sysInfo.get('citem',{}).get('name',(BUILTIN.getInfoLabel('ChannelName','VideoPlayer') or ADDON_NAME))))
        except Exception as e:
            log("Background: onInit, failed! %s"%(e), xbmc.LOGERROR)
            self.close()

            
            
class Replay(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self._closing = False
        self.player   = kwargs.get('player' ,None)
        
        
    def onInit(self):
        log("Replay: onInit")
        try:
            self._closing  = False
            self.service   = self.player.service
            self._progressLoop(self.getControl(40000))
            self.setFocusId(40001)
        except Exception as e:
            log("Replay: onInit, failed! %s\ncitem = %s"%(e,self.player.sysInfo), xbmc.LOGERROR)
            self.onClose()


    def _progressLoop(self, control, wait=OVERLAY_DELAY):
        tot  = wait
        xpos = control.getX()
        while not self.service.monitor.abortRequested():
            if (self.service._interrupt(1.0) or wait < 0 or self._closing): break
            prog = int((abs(wait-tot)*100)//tot)
            if prog > 0: control.setAnimations([('Conditional', 'effect=zoom start=%s,100 end=%s,100 time=1000 center=%s,100 condition=True'%((prog-20),(prog),xpos))])
            wait -= 1
        self.onClose()

        
    def onAction(self, act):
        actionId = act.getId()
        log('Replay: onAction: actionId = %s'%(actionId))
        if actionId in ACTION_SELECT_ITEM and self.getFocusId(40001): 
            if   self.player.sysInfo.get('isPlaylist',False): self.player.seekTime(0)
            elif self.player.sysInfo.get('fitem'): 
                liz = LISTITEMS.buildItemListItem(self.player.sysInfo.get('fitem',{}))
                liz.setProperty('sysInfo',encodeString(dumpJSON(self.player.sysInfo)))
                self.player.play(self.player.sysInfo.get('fitem',{}).get('catchup-id'),liz)
            else: DIALOG.notificationDialog(LANGUAGE(30154))
        elif actionId == ACTION_MOVE_UP:       BUILTIN.executebuiltin('AlarmClock(up,Action(up),time,100,true,false)')
        elif actionId == ACTION_MOVE_DOWN:     BUILTIN.executebuiltin('AlarmClock(down,Action(down),time,100,true,false)')
        elif actionId in ACTION_PREVIOUS_MENU: BUILTIN.executebuiltin('AlarmClock(back,Action(back),time,100,true,false)')
        self.onClose()


    def onClose(self):
        log("Replay: onClose")
        self._closing = True
        self.close()
  
  
class Overlay():
    controlManager = dict()
    
    def __init__(self, jsonRPC, player=None):
        self.jsonRPC      = jsonRPC
        self.player       = player
        self.resources    = Resources(self.jsonRPC)
        self.runActions   = RulesList().runActions
        
        self.window = xbmcgui.Window(12005) 
        self.window_h, self.window_w = (self.window.getHeight() , self.window.getWidth())
        
        self._vinImage = 'None'
        self._vinOffsetX, self._vinOffsetY = (0,0) 
        
        self.channelBugColor    = '0x%s'%((SETTINGS.getSetting('DIFFUSE_LOGO') or 'FFFFFFFF')) #todo adv. channel rule for color selection
        self.enableOnNext       = SETTINGS.getSettingBool('Enable_OnNext')
        self.enableChannelBug   = SETTINGS.getSettingBool('Enable_ChannelBug')
        self.channelBugInterval = SETTINGS.getSettingInt("Channel_Bug_Interval")
        self.channelBugDiffuse  = SETTINGS.getSettingBool('Force_Diffuse')
        self.minDuration        = SETTINGS.getSettingInt('Seek_Tolerance')
        
        try:    self.channelBugX, self.channelBugY = literal_eval(SETTINGS.getSetting("Channel_Bug_Position_XY")) #user
        except: self.channelBugX, self.channelBugY = (abs(int(self.window_w // 8) - self.window_w) - 128, abs(int(self.window_h // 16) - self.window_h) - 128) #auto
         
        #init controls
        self._channelBug = xbmcgui.ControlImage(self.channelBugX, self.channelBugY, 128, 128, 'None', aspectRatio=2)
        self._onNext     = xbmcgui.ControlTextBox(int(self.window_w // 8), abs(int(self.window_h // 16) - self.window_h), 1920, 36, 'font12', '0xFFFFFFFF')
        self._background = xbmcgui.ControlImage(0, 0, self.window_w, self.window_h, 'None', aspectRatio=2, colorDiffuse='black')
        self._vignette   = xbmcgui.ControlImage(self._vinOffsetX, self._vinOffsetY, self.window_w, self.window_h, 'None', aspectRatio=0)
        
        self._channelBugThread = Timer(0.1, self.toggleBug, [False])
        self._onNextThread     = Timer(0.1, self.toggleOnNext, [False])


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
                self._setControl(control,self._setVisible(control, False))
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
        
        
    def _setText(self, control, text: str):
        try: 
            if self._hasControl(control):
                control.setText(text)
        except Exception as e: self.log('_setText failed! %s'%(e), xbmc.LOGERROR)
        
        
    def _setImage(self, control, image: str, cache: bool=False):
        try: 
            if self._hasControl(control):
                control.setImage(image, useCache=cache)
        except Exception as e: self.log('_setImage failed! %s'%(e), xbmc.LOGERROR)
        
        
    def _setVisible(self, control, state: bool=False):
        try:
            if self._hasControl(control):
                self._setControl(control,state)
                control.setVisible(state)
                self.log('setVisible, %s = %s'%(control,state))
        except Exception('setVisible, failed! control does not exist'): pass
        return state
        
        
    def _isVisible(self, control):
        try:    return control.isVisible()
        except: return (self._getControl(control) or False)
    
        
    def open(self):
        self.log('open, id = %s'%(self.player.sysInfo.get('citem',{}).get('id')))
        if not self.player.isPseudoTV:  return self.close()
        self.runActions(RULES_ACTION_OVERLAY_OPEN, self.player.sysInfo.get('citem',{}), inherited=self)
        self.toggleBackground(), self.toggleVignette(), self.toggleBug(), self.toggleOnNext()
            
            
    def close(self):
        self.log('close')
        self._cancelOnNext()
        self._cancelChannelBug()
        self.runActions(RULES_ACTION_OVERLAY_CLOSE, self.player.sysInfo.get('citem',{}), inherited=self)
        for control, visible in list(self.controlManager.items()): self._removeControl(control)
        

    def _cancelOnNext(self):
        self.log('_cancelOnNext')
        self._setText(self._onNext,' ')
        self._setVisible(self._onNext,False)
        if self._onNextThread.is_alive():
            self._onNextThread.cancel()
            
            
    def _cancelChannelBug(self):
        self.log('_cancelChannelBug')
        self._setImage(self._channelBug,' ')
        self._setVisible(self._channelBug,False)
        if self._channelBugThread.is_alive():
            try: 
                self._channelBugThread.cancel()
                self._channelBugThread.join()
            except: pass

        
    def toggleBackground(self, state: bool=True):
        self.log('toggleBackground, state = %s'%(state))
        if state:
            if not self._hasControl(self._background):
                self._addControl(self._background)
            self._setImage(self._background,os.path.join(MEDIA_LOC,'colors','white.png'))
            self._background.setVisibleCondition('[!Player.Playing]', True)
            self._setVisible(self._background,True)
        else:
            self._setImage(self._background,'None')
            self._setVisible(self._background,False)
        

    def toggleVignette(self, state: bool=True):
        self.log('toggleVignette, state = %s'%(state))
        if state:
            if not self._hasControl(self._vignette):
                self._addControl(self._vignette)
            
            if self._vinImage:
                self._setImage(self._vignette,self._vinImage)
                self._vignette.setPosition(self._vinOffsetX, self._vinOffsetY)
                self._vignette.setVisibleCondition('[Player.Playing]', True)
                self._vignette.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=500 delay=0 condition=True reversible=False')])
                self._setVisible(self._vignette,True)
                self.log('toggleVignette, set = %s @ (%s,%s)'%(self._vinImage,self._vinOffsetX, self._vinOffsetY))
        else:
            self._setImage(self._vignette,'None')
            self._setVisible(self._vignette,False)

        
    def toggleBug(self, state: bool=True):
        def _getWait(state):
            if self.channelBugInterval == -1: 
                onVAL  = self.player.getTimeLabel('TimeRemaining')
                offVAL = 0.1
            elif self.channelBugInterval == 0:
                onVAL  = random.randint(300,900)
                offVAL = random.randint(300,900)
            else:
                onVAL  = self.channelBugInterval * 60
                offVAL = round(onVAL // 2)
            self.log('toggleBug, _getWait onVAL, offVAL (%s,%s)'%(onVAL, offVAL))
            return {True:float(onVAL),False:float(offVAL)}[state]

        try:
            wait   = _getWait(state)
            nstate = not bool(state)
            
            if self._channelBugThread.is_alive():
                try: 
                    self._channelBugThread.cancel()
                    self._channelBugThread.join()
                except: pass
                  
            try: 
                try:    self.channelBugX, self.channelBugY = literal_eval(SETTINGS.getSetting("Channel_Bug_Position_XY"))
                except: self.channelBugX, self.channelBugY = (abs(int(self.window_w // 8) - self.window_w) - 128, abs(int(self.window_h // 16) - self.window_h) - 128)
                self.log('toggleBug, channelbug POSXX (%s,%s)'%(self.channelBugX, self.channelBugY))
                self._channelBug.setPosition(self.channelBugX, self.channelBugY)
            except: pass
            
            if state and self.player.isPseudoTV and self.enableChannelBug and not BUILTIN.getInfoLabel('Genre','VideoPlayer') in FILLER_TYPE:
                if not self._hasControl(self._channelBug):
                    self._addControl(self._channelBug)
                    self._channelBug.setVisibleCondition('Player.Playing + [!String.Contains(VideoPlayer.Genre,Pre-Roll) | !String.Contains(VideoPlayer.Genre,Post-Roll)]')
                    self._channelBug.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=2000 delay=1000 condition=True reversible=False'),
                                                    ('Conditional', 'effect=fade start=100 end=25 time=1000 delay=3000 condition=True reversible=False')])
                                                
                logo = self.player.sysInfo.get('citem',{}).get('logo',(BUILTIN.getInfoLabel('Art(icon)','Player') or  LOGO))
                self.log('toggleBug, channelbug logo = %s)'%(logo))
                
                if   self.channelBugDiffuse:      self._channelBug.setColorDiffuse(self.channelBugColor)
                elif self.resources.isMono(logo): self._channelBug.setColorDiffuse(self.channelBugColor)
                
                self._setImage(self._channelBug,logo)
                self._setVisible(self._channelBug,True)
            else: 
                self._setVisible(self._channelBug,False)
                self._setImage(self._channelBug,'None')
                
            self.log('toggleBug, state %s wait %s to new state %s'%(state,wait,nstate))
            self._channelBugThread = Timer(wait, self.toggleBug, [nstate])
            self._channelBugThread.name = "_channelBugThread"
            self._channelBugThread.daemon=True
            self._channelBugThread.start()
        except Exception as e: self.log("toggleBug, failed! %s"%(e), xbmc.LOGERROR)
          
          
    def toggleOnNext(self, state: bool=True):
        def getOnNextInterval(interval=3):
            #split totalTime time into quarters, last quarter triggers nextup split by equal intervals of 3. ie. display 3 times in the last quarter of show.
            totalTime  = int(self.player.getPlayerTime())
            remaining  = floor(self.player.getTimeLabel('TimeRemaining'))
            showTime   = (abs(totalTime - (totalTime * .75)) - (OVERLAY_DELAY * interval))
            intTime    = roundupDIV(showTime,interval)
            showOnNext = remaining <= showTime and totalTime > SELECT_DELAY and not BUILTIN.getInfoLabel('NextGenre','VideoPlayer') in FILLER_TYPE and self.player.getPlayerTime() > self.minDuration
            
            if remaining < intTime: return getOnNextInterval(interval + 1)
            self.log('toggleOnNext, totalTime = %s, interval = %s, remaining = %s, intTime = %s, showOnNext = %s'%(totalTime,interval,remaining,intTime,showOnNext))
            return showOnNext, intTime

        try:
            showOnNext, intTime = getOnNextInterval()
            wait   = {True:EPOCH_TIMER,False:float(intTime)}[state]
            nstate = not bool(state)
            try: 
                if self._onNextThread.is_alive():
                    self._onNextThread.cancel()
                    self._onNextThread.join()
            except: pass
                
            if state and showOnNext and self.player.isPseudoTV and self.enableOnNext:
                citem = self.player.sysInfo.get('citem',{})
                if not self._hasControl(self._onNext):
                    self._addControl(self._onNext)
                    self._onNext.setVisibleCondition('Player.Playing + [!String.Contains(VideoPlayer.Genre,Pre-Roll) | !String.Contains(VideoPlayer.Genre,Post-Roll)]')
                             
                citem = self.player.sysInfo.get('citem',{})
                fitem = self.player.sysInfo.get('fitem',{})
                nitem = self.player.sysInfo.get('nitem',{})
                
                if self.player.sysInfo.get('isPlaylist',False): self._updateUpNext(fitem,nitem)
                else:
                    chname    = citem.get('name',BUILTIN.getInfoLabel('ChannelName','VideoPlayer'))
                    nowTitle  = fitem.get('label',BUILTIN.getInfoLabel('Title','VideoPlayer'))
                    nextTitle = nitem.get('showlabel',BUILTIN.getInfoLabel('NextTitle','VideoPlayer'))
                    
                    onNow  = '%s on %s'%(nowTitle,chname) if chname not in nowTitle else fitem.get('showlabel',nowTitle)
                    onNext = '%s @ %s'%(nextTitle,BUILTIN.getInfoLabel('NextStartTime','VideoPlayer'))
                    self._setText(self._onNext,'%s\n%s'%(LANGUAGE(32104)%(onNow),LANGUAGE(32116)%(onNext)))
                    self._onNext.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=2000 delay=1000 condition=True reversible=True')])
                    self._onNext.autoScroll(5500, 2500, int(EPOCH_TIMER//3))
                    self._setVisible(self._onNext,True)
                    playSFX(BING_WAV)
            else: 
                self._setVisible(self._onNext,False)
            
            self.log('toggleOnNext, state %s wait %s to new state %s'%(state,wait,nstate))
            self._onNextThread = Timer(wait, self.toggleOnNext, [nstate])
            self._onNextThread.name = "onNextThread"
            self._onNextThread.daemon=True
            self._onNextThread.start()
        except Exception as e: self.log("toggleOnNext, failed! %s"%(e), xbmc.LOGERROR)


    def _updateUpNext(self, nowItem: dict={}, nextItem: dict={}):
        self.log('_updateUpNext')
        try:
            # https://github.com/im85288/service.upnext/wiki/Example-source-code
            data            = dict()
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
        self.jsonRPC.notifyAll(message='upnext_data', data=binascii.hexlify(json.dumps(data).encode('utf-8')).decode('utf-8'), sender='%s.SIGNAL'%(ADDON_ID))