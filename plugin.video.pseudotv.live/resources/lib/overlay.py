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
             
class Background(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.overlay   = kwargs.get('overlay', None)
        self.sysInfo   = self.overlay.player.sysInfo.copy()
        self.citem     = self.sysInfo.get('citem',{})
        self.fitem     = self.sysInfo.get('fitem',{})
        self.nitem     = self.sysInfo.get('nitem',{})
        
        self.land      = getThumb(self.nitem)
        self.logo      = self.citem.get('logo'     , BUILTIN.getInfoLabel('Art(icon)','Player'))
        self.chname    = self.citem.get('name'     , BUILTIN.getInfoLabel('ChannelName','VideoPlayer'))
        self.nowTitle  = self.fitem.get('label'    , BUILTIN.getInfoLabel('Title','VideoPlayer'))
        self.nextTitle = self.nitem.get('showlabel', BUILTIN.getInfoLabel('NextTitle','VideoPlayer'))
        self.onNow     = '%s on %s'%(self.nowTitle,self.chname) if self.chname not in validString(self.nowTitle) else self.fitem.get('showlabel',self.nowTitle)
        self.onNext    = '[B]@ %s[/B] %s'%(BUILTIN.getInfoLabel('NextStartTime','VideoPlayer'),self.nextTitle)
        
        
    def onInit(self):
        try:
            log("Background: onInit")
            self.getControl(40004).setImage(COLOR_FANART if self.land == FANART else self.land, useCache=True)
            self.getControl(40003).setText('%s %s[CR]%s %s'%(LANGUAGE(32104),self.onNow,LANGUAGE(32116),self.onNext))
            self.getControl(40002).setImage(COLOR_LOGO if self.logo.endswith('wlogo.png') else self.logo)
            self.getControl(40001).setPosition(self.overlay.onNextX, self.overlay.onNextY)
            self.getControl(40001).setVisible(self.overlay.chkOnNextConditions())
        except Exception as e:
            log("Background: onInit, failed! %s"%(e), xbmc.LOGERROR)
            self.close()
            
       
class Busy(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)


    def onAction(self, act):
        actionId = act.getId()
        log('Busy: onAction: actionId = %s'%(actionId))
        if actionId in ACTION_PREVIOUS_MENU: self.close()
        else: pass


class Restart(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.closing = False
        self.player  = kwargs.get('player', None)
        
        
    def onInit(self):
        try:
            log("Restart: onInit")
            self.closing = False
            self.monitor = self.player.service.monitor
            self._progressLoop(self.getControl(40000))
            self.setFocusId(40001)
        except Exception as e:
            log("Restart: onInit, failed! %s\ncitem = %s"%(e,self.player.sysInfo), xbmc.LOGERROR)
            self.onClose()


    def _progressLoop(self, control, wait=(OSD_TIMER*2)):
        prog = 0
        tot  = wait
        xpos = control.getX()
        control.setVisibleCondition('Player.Playing')
        while not self.monitor.abortRequested():
            if (self.monitor.waitForAbort(0.5) or wait < 0 or self.closing or not self.player.isPlaying()): break
            else:
                prog = int((abs(wait-tot)*100)//tot)
                if prog > 0: control.setAnimations([('Conditional', 'effect=zoom start=%s,100 end=%s,100 time=1000 center=%s,100 condition=True'%((prog-20),(prog),xpos))])
                wait -= 1
        control.setAnimations([('Conditional', 'effect=fade start=%s end=0 time=240 delay=0.240 condition=True'%(prog))])
        control.setVisible(False)
        self.close()

        
    def onAction(self, act):
        actionId = act.getId()
        log('Restart: onAction: actionId = %s'%(actionId))
        if actionId in ACTION_SELECT_ITEM and self.getFocusId(40001): 
            sysInfo = self.player.sysInfo
            if   sysInfo.get('isPlaylist',False): self.player.seekTime(0)
            elif sysInfo.get('fitem'): 
                liz = LISTITEMS.buildItemListItem(sysInfo.get('fitem',{}))
                liz.setProperty('sysInfo',encodeString(dumpJSON(sysInfo)))
                self.player.sysInfo = {}
                self.player.play(sysInfo.get('fitem',{}).get('catchup-id'),liz)
            else: DIALOG.notificationDialog(LANGUAGE(30154))
        elif actionId == ACTION_MOVE_UP:       timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(up,Action(up),.5,true,false)'])
        elif actionId == ACTION_MOVE_DOWN:     timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(down,Action(down),.5,true,false)'])
        elif actionId in ACTION_PREVIOUS_MENU: timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(back,Action(back),.5,true,false)'])
        self.onClose()


    def onClose(self):
        log("Restart: onClose")
        self.closing = True
  
  
class Overlay():
    onNext         = None
    background     = None
    controlManager = dict()
    
    class Player(PLAYER):
        def __init__(self, overlay=None):
            PLAYER.__init__(self)
            self.overlay = overlay
            

        def onAVStarted(self):
            self.overlay.log('onAVStarted')
            self.overlay.toggleBug()
            self.overlay.toggleOnNext()
            self.overlay.toggleBackground(False)
            

        def onPlayBackEnded(self):
            self.overlay.log('onPlayBackEnded')
            self.overlay.toggleBug(False)
            self.overlay.toggleOnNext(False)
            self.overlay.toggleBackground()
                
            
        def onPlayBackStopped(self):
            self.overlay.log('onPlayBackStopped')
            self.overlay.toggleBug(False, cancel=False)
            self.overlay.toggleOnNext(False, cancel=False)
            self.overlay.toggleBackground(False)
            

    def __init__(self, jsonRPC, player=None):
        self.cache      = SETTINGS.cache
        self.jsonRPC    = jsonRPC
        self.player     = player
        self.resources  = Resources(jsonRPC)
        self.runActions = self.player.runActions

        self.windowID = 12005
        self.window   = xbmcgui.Window(self.windowID) 
        self.window_h, self.window_w = (self.window.getHeight(), self.window.getWidth())
                
        self.enableVignette     = False
        self.enableOnNext       = bool(SETTINGS.getSettingInt('OnNext_Enable'))
        self.onNextMode         = SETTINGS.getSettingInt('OnNext_Enable')
        self.minDuration        = SETTINGS.getSettingInt('Seek_Tolerance')
        self.maxProgress        = SETTINGS.getSettingInt('Seek_Threshold')
        self.enableChannelBug   = SETTINGS.getSettingBool('Enable_ChannelBug')
        self.channelBugInterval = SETTINGS.getSettingInt("Channel_Bug_Interval")
        self.channelBugDiffuse  = SETTINGS.getSettingBool('Force_Diffuse')
        self.channelBugColor    = '0x%s'%((SETTINGS.getSetting('ChannelBug_Color') or 'FFFFFFFF'))
        self.onNextColor        = '0x%s'%((SETTINGS.getSetting('OnNext_Color')     or 'FFFFFFFF'))
        
        #vignette
        self.defaultView = self.jsonRPC.getViewMode()
        self.vinView     = self.defaultView
        self.vinImage    = ''
        self.vignette    = xbmcgui.ControlImage(0, 0, self.window_w, self.window_h, ' ', aspectRatio=0)
        
        #channelBug
        try:    self.channelBugX, self.channelBugY = eval(SETTINGS.getSetting("Channel_Bug_Position_XY")) #user
        except: self.channelBugX, self.channelBugY = abs(int(self.window_w // 8) - self.window_w) - 128, abs(int(self.window_h // 16) - self.window_h) - 128 #auto
        self.channelBug = xbmcgui.ControlImage(self.channelBugX, self.channelBugY, 128, 128, ' ', aspectRatio=2)
        
        #onNext
        try:    self.onNextX, self.onNextY = eval(SETTINGS.getSetting("OnNext_Position_XY")) #user
        except: self.onNextX, self.onNextY = abs(int(self.window_w // 8)), abs(int(self.window_h // 16) - self.window_h) #auto
        self.onNext_Border  = xbmcgui.ControlImage(self.onNextX, self.onNextY, 240, 135, ' ', aspectRatio=0)
        self.onNext_Artwork = xbmcgui.ControlImage((self.onNextX + 5), (self.onNextY + 5), 230, 125, ' ', aspectRatio=0)
        self.onNext_Text    = xbmcgui.ControlTextBox(self.onNextX, (self.onNextY + 140), 960, 70, 'font27', self.onNextColor)

        self._bugThread    = Timer(0.1, self.toggleBug, [False])
        self._onNextThread = Timer(0.1, self.toggleOnNext, [False])
        self._player       = self.Player(overlay=self)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

        
    def show(self):
        self.log('show, id = %s, rules = %s'%(self.player.sysInfo.get('citem',{}).get('id'),self.player.sysInfo.get('rules',{})))
        self.runActions(RULES_ACTION_OVERLAY_OPEN, self.player.sysInfo.get('citem',{}), inherited=self)
        self._player.onAVStarted(), self.toggleVignette()

   
    def close(self):
        self.log('close')
        self.runActions(RULES_ACTION_OVERLAY_CLOSE, self.player.sysInfo.get('citem',{}), inherited=self)
        self._player.onPlayBackStopped(), self.toggleVignette(False)
        self._clrRemaining()
                
        
    def _clrRemaining(self):
        for control, visible in list(self.controlManager.items()):
            self.log('_clrRemaining, removing orphaned control %s'%(control))
            self._delControl(control)


    def _hasControl(self, control):
        return control in self.controlManager
        

    def _isVisible(self, control):
        return self.controlManager.get(control,False)


    def _setVisible(self, control, state: bool=False):
        try:
            self.log('_setVisible, %s = %s'%(control,state))
            if self._hasControl(control): control.setVisible(state)
        except Exception('_setVisible, failed! control does not exist'): pass
        return state


    def _addControl(self, control):
        try:
            self.log('_addControl, %s'%(control))
            if not self._hasControl(control):
                self.window.addControl(control)
                self.controlManager[control] = self._setVisible(control,False)
                MONITOR().waitForAbort(0.5)
        except Exception as e: self.log('_addControl failed! %s'%(e), xbmc.LOGERROR)
        
        
    def _delControl(self, control):
        try:
            self.log('_delControl, %s'%(control))
            if self._hasControl(control):
                self.window.removeControl(control)
                self.controlManager.pop(control)
        except Exception as e: self.log('_delControl failed! control = %s %s'%(control, e), xbmc.LOGERROR)


    def chkOnNextConditions(self):
        def __isFiller():
            for genre in self.player.sysInfo.get('fitem',{}).get('genre',[]) + self.player.sysInfo.get('nitem',{}).get('genre',[]):
                if genre.lower() in ['pre-roll','post-roll']: return True
            return False
            
        if not self.enableOnNext or self.player.sysInfo.get('nitem',{}).get('duration', 0) < self.minDuration: return False
        elif __isFiller(): return False
        return True

        
    def chkBugConditions(self):
        def __isFiller():
            for genre in self.player.sysInfo.get('fitem',{}).get('genre',[]):
                if genre.lower() in ['pre-roll','post-roll']: return True
            return False
            
        if not self.enableChannelBug or self.player.sysInfo.get('fitem',{}).get('duration', 0) < self.minDuration or not self.player.isPlaying(): return False
        elif self.player.getPlayerProgress() >= self.maxProgress: return False
        elif __isFiller(): return False
        return True


    def toggleBackground(self, state: bool=True):
        self.log('toggleBackground, state = %s'%(state))
        if state:
            if self.background is None: self.background = Background(BACKGROUND_XML, ADDON_PATH, "default", overlay=self)
            self.background.doModal()
            del self.background
            self.background = None
        elif hasattr(self.background,'close'):
            self.background = self.background.close()
            

    def toggleVignette(self, state: bool=True):
        if state and self.enableVignette:
            if not self._hasControl(self.vignette):
                self.vignette = xbmcgui.ControlImage(0, 0, self.window_w, self.window_h, ' ', aspectRatio=0)
                self._addControl(self.vignette)
            
            timerit(self.jsonRPC.setViewMode)(0.5,[self.vinView])
            self.vignette.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=240 delay=160 condition=True reversible=True')])
            self.vignette.setImage(self.vinImage)
            self._setVisible(self.vignette,True)
            self.log('toggleVignette, state = %s, image = %s\nmode = %s'%(state, self.vinImage,self.vinView))
            
        elif self._hasControl(self.vignette):
            self._delControl(self.vignette)
            timerit(self.jsonRPC.setViewMode)(0.5,[self.defaultView])
            self.log('toggleVignette, state = %s, image = %s\nmode = %s'%(state, self.vinImage,self.defaultView))
            
                
    def toggleBug(self, state: bool=True, cancel=False):
        def __getWait(state, remaining):
            if (remaining <= self.minDuration or not self.chkBugConditions()): return False, remaining
            elif self.channelBugInterval == -1: #Indefinitely 
                onVAL  = remaining
                offVAL = FIFTEEN
            elif self.channelBugInterval == 0: #random
                onVAL  = random.randint(0,remaining)
                offVAL = random.randint(0,(abs(remaining - onVAL) // 2))
            else: #set time
                setVal = self.channelBugInterval * 60
                onVAL  = setVal if setVal <= remaining else remaining
                offVAL = round(onVAL // 2)
            self.log('toggleBug, _getWait onVAL, offVAL (%s,%s)'%(onVAL, offVAL))
            return state, {True:float(onVAL),False:float(offVAL)}[state]

        showbug, wait = __getWait(state, int(floor(self.player.getRemainingTime())))
        nstate = not bool(showbug)
        
        if state and showbug:
            logo = self.player.sysInfo.get('citem',{}).get('logo',(BUILTIN.getInfoLabel('Art(icon)','Player') or  LOGO))
            
            if not self._hasControl(self.channelBug):
                self.channelBug = xbmcgui.ControlImage(self.channelBugX, self.channelBugY, 128, 128, ' ', aspectRatio=2)
                self._addControl(self.channelBug)
                
            self.channelBug.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=2000 delay=1000 condition=True reversible=False'),
                                           ('Conditional', 'effect=fade start=100 end=25 time=1000 delay=3000 condition=True reversible=False')])
            
            if   self.channelBugDiffuse:      self.channelBug.setColorDiffuse(self.channelBugColor)
            elif self.resources.isMono(logo): self.channelBug.setColorDiffuse(self.channelBugColor)
            self.channelBug.setImage(logo)
            self._setVisible(self.channelBug,True)
            self.log('toggleBug, logo = %s, setColorDiffuse = %s, POSXY (%s,%s))'%(logo, self.channelBugColor, self.channelBugX, self.channelBugY))
            
        elif self._hasControl(self.channelBug):
            self._delControl(self.channelBug)
            
        if self._bugThread.is_alive():
            if hasattr(self._bugThread, 'cancel'): self._bugThread.cancel()
            try: self._bugThread.join()
            except: pass
            
        if cancel or wait < 1: return self.log('toggleBug, cancelling timer...')
        self.log('toggleBug, state %s wait %s to new state %s'%(state,wait,nstate))
        self._bugThread = Timer(wait, self.toggleBug, [nstate])
        self._bugThread.name = "_bugThread"
        self._bugThread.daemon=True
        self._bugThread.start()

    
    def toggleOnNext(self, state: bool=True, cancel: bool=False):
        def __getOnNextInterval(interval, displayTime):
            conditions = self.chkOnNextConditions()
            totalTime  = int(self.player.getPlayerTime() * (self.maxProgress / 100))
            remaining  = int(totalTime - self.player.getPlayedTime())
            threshold  = roundupDIV(totalTime,4)
            intTime    = roundupDIV(threshold,interval)
            
            self.log('toggleOnNext, conditions = %s, totalTime = %s, remaining = %s, threshold = %s, intTime = %s'%(conditions, totalTime, remaining, threshold, intTime))
            if not conditions or remaining <= self.minDuration: return False, remaining, 0
            elif remaining > threshold:                         return False, abs(remaining - threshold), 0
            elif remaining < intTime:                           return __getOnNextInterval(interval+1, displayTime)
            else:                                               return True, abs(intTime - displayTime), displayTime
            
        showOnNext, sleepTime, displayTime = __getOnNextInterval(ON_NEXT_COUNT,int(OSD_TIMER * ON_NEXT_COUNT))
        self.log('toggleOnNext, showOnNext = %s, sleepTime = %s, displayTime = %s'%(showOnNext, sleepTime, displayTime))
        
        wait    = {True:displayTime,False:sleepTime}[showOnNext]
        nstate  = not bool(showOnNext)
        sysInfo = self.player.sysInfo.copy()
        citem   = sysInfo.get('citem',{}) #channel
        fitem   = sysInfo.get('fitem',{}) #onnow
        nitem   = sysInfo.get('nitem',{}) #onnext
        
        if state and showOnNext:
            if self.onNextMode in [1,2]:                    
                chname    = citem.get('name'     ,BUILTIN.getInfoLabel('ChannelName','VideoPlayer'))
                nowTitle  = fitem.get('label'    ,BUILTIN.getInfoLabel('Title','VideoPlayer'))
                nextTitle = nitem.get('showlabel',BUILTIN.getInfoLabel('NextTitle','VideoPlayer'))
                onNow  = '%s on %s'%(nowTitle,chname) if chname not in validString(nowTitle) else fitem.get('showlabel',nowTitle)
                onNext = '[B]@ %s[/B] %s'%(BUILTIN.getInfoLabel('NextStartTime','VideoPlayer'),nextTitle)
                
                if not self._hasControl(self.onNext_Text):
                    self.onNext_Text = xbmcgui.ControlTextBox(self.onNextX, (self.onNextY + 140), 960, 70, 'font27', self.onNextColor)
                    self._addControl(self.onNext_Text)

                self.onNext_Text.setText('%s %s[CR]%s %s'%(LANGUAGE(32104),onNow,LANGUAGE(32116),onNext))
                self.onNext_Text.setAnimations([('WindowOpen' , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                ('WindowOpen' , 'effect=fade start=0 end=100 delay=160 time=240 reversible=false'),
                                                ('WindowClose', 'effect=zoom start=100 end=80 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                ('WindowClose', 'effect=fade start=100 end=0 time=240 reversible=false'),
                                                ('Visible'    , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                ('Visible'    , 'effect=fade end=100 time=240 reversible=false')])
                if self.onNextMode == 2:
                    landscape = getThumb(nitem)    
                    
                    if not self._hasControl(self.onNext_Border):
                        self.onNext_Border = xbmcgui.ControlImage(self.onNextX, self.onNextY, 240, 135, os.path.join(MEDIA_LOC,'colors','white.png'), 0, '0xC0%s'%(COLOR_BACKGROUND))#todo adv. rule to change color.
                        self._addControl(self.onNext_Border)

                    self.onNext_Border.setAnimations([('WindowOpen' , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                       ('WindowOpen' , 'effect=fade start=0 end=100 delay=160 time=240 reversible=false'),
                                                       ('WindowClose', 'effect=zoom start=100 end=80 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                       ('WindowClose', 'effect=fade start=100 end=0 time=240 reversible=false'),
                                                       ('Visible'    , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                       ('Visible'    , 'effect=fade end=100 time=240 reversible=false')])
         
                    if not self._hasControl(self.onNext_Artwork):
                        self.onNext_Artwork = xbmcgui.ControlImage((self.onNextX + 5), (self.onNextY + 5), 230, 125, ' ', aspectRatio=0)
                        self._addControl(self.onNext_Artwork)
                        
                    self.onNext_Artwork.setImage(COLOR_FANART if landscape == FANART else landscape, useCache=True)
                    self.onNext_Artwork.setAnimations([('WindowOpen' , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                       ('WindowOpen' , 'effect=fade start=0 end=100 delay=160 time=240 reversible=false'),
                                                       ('WindowClose', 'effect=zoom start=100 end=80 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                       ('WindowClose', 'effect=fade start=100 end=0 time=240 reversible=false'),
                                                       ('Visible'    , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                       ('Visible'    , 'effect=fade end=100 time=240 reversible=false')])
     
                    self._setVisible(self.onNext_Border,True)
                    self._setVisible(self.onNext_Artwork,True)
                self._setVisible(self.onNext_Text,True)

            elif self.onNextMode == 3: self.player.toggleInfo()
            elif self.onNextMode == 4: self._updateUpNext(fitem,nitem)
            timerit(playSFX)(0.5,[BING_WAV])
                
        elif self._hasControl(self.onNext_Text):
            self._delControl(self.onNext_Text)
            if self._hasControl(self.onNext_Border):  self._delControl(self.onNext_Border)
            if self._hasControl(self.onNext_Artwork): self._delControl(self.onNext_Artwork)
                        
        if self._onNextThread.is_alive():
            if hasattr(self._onNextThread, 'cancel'): self._onNextThread.cancel()
            try: self._onNextThread.join()
            except: pass
            
        if cancel: return self.log('toggleOnNext, cancelling timer...')
        self.log('toggleOnNext, state %s wait %s to new state %s'%(state,wait,nstate))
        self._onNextThread = Timer(wait, self.toggleOnNext, [nstate])
        self._onNextThread.name = "onNextThread"
        self._onNextThread.daemon=True
        self._onNextThread.start()
        
        
    def _updateUpNext(self, nowItem: dict={}, nextItem: dict={}):
        self.log('_updateUpNext')
        try:
            # https://github.com/im85288/service.upnext/wiki/Example-source-code
            data = dict()
            data.update({"notification_offset":int(floor(self.player.getRemainingTime())) + OSD_TIMER})
            current_episode = {"current_episode":{"episodeid" :(nowItem.get("id")            or ""),
                                                  "tvshowid"  :(nowItem.get("tvshowid")      or ""),
                                                  "title"     :(nowItem.get("title")         or ""),
                                                  "art"       :(nowItem.get("art")           or ""),
                                                  "season"    :(nowItem.get("season")        or ""),
                                                  "episode"   :(nowItem.get("episode")       or ""),
                                                  "showtitle" :(nowItem.get("tvshowtitle")   or ""),
                                                  "plot"      :(nowItem.get("plot")          or ""),
                                                  "playcount" :(nowItem.get("playcount")     or ""),
                                                  "rating"    :(nowItem.get("rating")        or ""),
                                                  "firstaired":(nowItem.get("firstaired")    or ""),
                                                  "runtime"   :(nowItem.get("runtime")       or "")}}
            data.update(current_episode)
        except: pass
        try:
            next_episode    = {"next_episode"   :{"episodeid" :(nextItem.get("id")           or ""),
                                                  "tvshowid"  :(nextItem.get("tvshowid")     or ""),
                                                  "title"     :(nextItem.get("title")        or ""),
                                                  "art"       :(nextItem.get("art")          or ""),
                                                  "season"    :(nextItem.get("season")       or ""),
                                                  "episode"   :(nextItem.get("episode")      or ""),
                                                  "showtitle" :(nextItem.get("tvshowtitle")  or ""),
                                                  "plot"      :(nextItem.get("plot" )        or ""),
                                                  "playcount" :(nextItem.get("playcount")    or ""),
                                                  "rating"    :(nextItem.get("rating")       or ""),
                                                  "firstaired":(nextItem.get("firstaired")   or ""),
                                                  "runtime"   :(nextItem.get("runtime")      or "")}}
            data.update(next_episode)

        except: pass
        timerit(self.jsonRPC.notifyAll)(0.5,['upnext_data', binascii.hexlify(json.dumps(data).encode('utf-8')).decode('utf-8'), '%s.SIGNAL'%(ADDON_ID)])