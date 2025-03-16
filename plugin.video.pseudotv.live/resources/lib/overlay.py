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
        self.player    = kwargs.get('player', None)
        self.sysInfo   = kwargs.get('sysInfo', self.player.sysInfo)
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
            self.window_h, self.window_w = (self.getHeight(), self.getWidth())
            self.getControl(40004).setImage(COLOR_FANART if self.land == FANART else self.land, useCache=True)
            self.getControl(40003).setText('%s %s[CR]%s %s'%(LANGUAGE(32104),self.onNow,LANGUAGE(32116),self.onNext))
            self.getControl(40002).setImage(COLOR_LOGO if self.logo.endswith('wlogo.png') else self.logo)
            self.getControl(40001).setPosition(abs(int(self.window_w // 9)), abs(int(self.window_h // 16) - self.window_h) - 356)
        except Exception as e:
            log("Background: onInit, failed! %s"%(e), xbmc.LOGERROR)
            self.onClose()
       
       
    def onClose(self):
        log("Background: onClose")
        self.close()
            
            
class Busy(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)


    def onAction(self, act):
        actionId = act.getId()
        log('Busy: onAction: actionId = %s'%(actionId))
        if actionId in ACTION_PREVIOUS_MENU: self.close()


class Restart(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.closing = False
        self.player  = kwargs.get('player', None)
        self.sysInfo = kwargs.get('sysInfo', self.player.sysInfo)
        
    def onInit(self):
        try:
            log("Restart: onInit")
            self.closing = False
            self.monitor = self.player.service.monitor
            self._progressLoop(self.getControl(40000))
            self.setFocusId(40001)
        except Exception as e:
            log("Restart: onInit, failed! %s\ncitem = %s"%(e,self.sysInfo), xbmc.LOGERROR)
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
            if   self.sysInfo.get('isPlaylist',False): self.player.seekTime(0)
            elif self.sysInfo.get('fitem'): 
                liz = LISTITEMS.buildItemListItem(self.sysInfo.get('fitem',{}))
                liz.setProperty('sysInfo',encodeString(dumpJSON(self.sysInfo)))
                self.player.play(self.sysInfo.get('fitem',{}).get('catchup-id'),liz)
            else: DIALOG.notificationDialog(LANGUAGE(30154))
        elif actionId == ACTION_MOVE_UP:       timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(up,Action(up),.5,true,false)'])
        elif actionId == ACTION_MOVE_DOWN:     timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(down,Action(down),.5,true,false)'])
        elif actionId in ACTION_PREVIOUS_MENU: timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(back,Action(back),.5,true,false)'])
        self.onClose()


    def onClose(self):
        log("Restart: onClose")
        self.closing = True
  
    
class Overlay():
    controlManager = dict()
    
    def __init__(self, jsonRPC, player=None):
        self.cache      = SETTINGS.cache
        self.jsonRPC    = jsonRPC
        self.player     = player
        self.resources  = Resources(service=player.service)
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
        self.forceBugDiffuse    = SETTINGS.getSettingBool('Force_Diffuse')
        self.channelBugColor    = '0x%s'%((SETTINGS.getSetting('ChannelBug_Color') or 'FFFFFFFF'))
        self.onNextColor        = '0x%s'%((SETTINGS.getSetting('OnNext_Color')     or 'FFFFFFFF'))
        
        #vignette
        self.defaultView = self.jsonRPC.getViewMode()
        self.vinView     = self.defaultView
        self.vinImage    = ''
        self.vignette    = xbmcgui.ControlImage(0, 0, self.window_w, self.window_h, ' ', aspectRatio=0)
        
        #channelBug
        try:    self.channelBugX, self.channelBugY = eval(SETTINGS.getSetting("Channel_Bug_Position_XY")) #user
        except: self.channelBugX, self.channelBugY = abs(int(self.window_w // 9) - self.window_w) - 128, abs(int(self.window_h // 16) - self.window_h) - 128 #auto
        self.channelBug = xbmcgui.ControlImage(self.channelBugX, self.channelBugY, 128, 128, ' ', aspectRatio=2)
        
        #onNext
        try:    self.onNextX, self.onNextY = eval(SETTINGS.getSetting("OnNext_Position_XY")) #user
        except: self.onNextX, self.onNextY = abs(int(self.window_w // 9)), abs(int(self.window_h // 16) - self.window_h) - 356 #auto
        self.onNext_Border  = xbmcgui.ControlImage(self.onNextX, self.onNextY, 256, 128, ' ', aspectRatio=0)
        self.onNext_Artwork = xbmcgui.ControlImage((self.onNextX + 5), (self.onNextY + 5), 246, 118, ' ', aspectRatio=0)
        self.onNext_Text    = xbmcgui.ControlTextBox(self.onNextX, (self.onNextY + 156), 960, 72, 'font27', self.onNextColor)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

        
    def open(self):
        self.log('[%s] open, rules = %s'%(self.player.sysInfo.get('citem',{}).get('id'),self.player.sysInfo.get('rules',{})))
        self.runActions(RULES_ACTION_OVERLAY_OPEN, self.player.sysInfo.get('citem',{}), inherited=self)
        self.toggleVignette(self.enableVignette)
        self.toggleBug()
        self.toggleOnNext()

   
    def close(self):
        self.log('close')
        self.runActions(RULES_ACTION_OVERLAY_CLOSE, self.player.sysInfo.get('citem',{}), inherited=self)
        self.toggleVignette(False)
        self.toggleBug(False,cancel=True)
        self.toggleOnNext(False,cancel=True)
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
        self.log('_setVisible, %s = %s'%(control,state))
        if self._hasControl(control): 
            try:
                control.setVisible(state)
                return state
            except Exception as e: 
                self.log('_setVisible, failed! control = %s %s'%(control,e))
                self._delControl(control)
                return False


    def _addControl(self, control):
        self.log('_addControl, %s'%(control))
        if not self._hasControl(control):
            try: 
                self.window.addControl(control)
                self.controlManager[control] = self._setVisible(control,False)
            except Exception as e: 
                self.log('_addControl failed! control = %s %s'%(control, e), xbmc.LOGERROR)
                self._delControl(control)
        
        
    def _delControl(self, control):
        self.log('_delControl, %s'%(control))
        if self._hasControl(control):
            try: self.window.removeControl(control)
            except Exception as e: self.log('_delControl failed! control = %s %s'%(control, e), xbmc.LOGERROR)
            self.controlManager.pop(control)


    def toggleVignette(self, state: bool=True):
        if state:
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
            

    def chkBugConditions(self):
        def __isFiller():
            for genre in self.player.sysInfo.get('fitem',{}).get('genre',[]):
                if genre.lower() in ['pre-roll','post-roll']: return True
            return False
            
        if   self.player.sysInfo.get('fitem',{}).get('duration', 0) < self.minDuration: return False
        elif self.player.getPlayerProgress() >= self.maxProgress: return False
        elif __isFiller() or PROPERTIES.isRunning('Overlay.close'): return False
        return True

                
    def toggleBug(self, state: bool=True, cancel=False):
        def __show(state, remaining):
            try:
                if (remaining <= self.minDuration or not self.chkBugConditions()): return False, OSD_TIMER
                elif self.channelBugInterval < 0: #Indefinitely 
                    onVAL  = remaining
                    offVAL = FIFTEEN
                elif self.channelBugInterval == 0: #random
                    onVAL  = random.randint(roundupDIV(remaining,4),roundupDIV(remaining,2))
                    offVAL = random.randint(roundupDIV(remaining,8),roundupDIV(remaining,4))
                else: #set time
                    setVal = self.channelBugInterval * 60
                    onVAL  = setVal if setVal <= remaining else remaining
                    offVAL = round(onVAL//2)
                self.log('toggleBug, __show: onVAL, offVAL (%s,%s)'%(onVAL, offVAL))
                return state, {True:float(onVAL),False:float(offVAL)}[state]
            except:
                return False, OSD_TIMER

        show, wait = __show(state, int(floor(self.player.getRemainingTime())))
        self.log('toggleBug, show = %s, wait = %s'%(show, wait))
        
        if state and show:
            logo = self.player.sysInfo.get('citem',{}).get('logo',(BUILTIN.getInfoLabel('Art(icon)','Player') or  LOGO))
            
            if not self._hasControl(self.channelBug):
                self.channelBug = xbmcgui.ControlImage(self.channelBugX, self.channelBugY, 128, 128, ' ', aspectRatio=2)
                self._addControl(self.channelBug)
            if   self.forceBugDiffuse:        self.channelBug.setColorDiffuse(self.channelBugColor)
            elif self.resources.isMono(logo): self.channelBug.setColorDiffuse(self.channelBugColor)
            self.channelBug.setImage(logo)
            self.channelBug.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=2000 delay=1000 condition=True reversible=false'),
                                           ('Conditional', 'effect=fade start=100 end=25 time=1000 delay=3000 condition=True reversible=false')])
            self._setVisible(self.channelBug,True)
            self.log('toggleBug, logo = %s, setColorDiffuse = %s, POSXY (%s,%s))'%(logo, self.channelBugColor, self.channelBugX, self.channelBugY))
            
        elif self._hasControl(self.channelBug): self._delControl(self.channelBug)

        if not cancel:
            nstate = not bool(state)
            self.log('toggleBug, state %s wait %s to new state %s'%(state,wait,nstate))
            timerit(self.toggleBug)(wait,[nstate])


    def chkOnNextConditions(self):
        def __isFiller():
            for genre in self.player.sysInfo.get('fitem',{}).get('genre',[]) + self.player.sysInfo.get('nitem',{}).get('genre',[]):
                if genre.lower() in ['pre-roll','post-roll']: return True
            return False
            
        def __isShort():
            for item in [self.player.sysInfo.get('fitem',{}),self.player.sysInfo.get('nitem',{})]:
                if item.get('duration', self.minDuration) < self.minDuration: return True
            return False
                
        if __isFiller() or __isShort() or PROPERTIES.isRunning('Overlay.close'): return False
        return True

        
    def toggleOnNext(self, state: bool=True, cancel: bool=False):
        def __show(state, interval=3):
            try:
                totalTime = int(self.player.getTotalTime() * (self.maxProgress / 100))
                threshold = abs((totalTime - (totalTime * .75)) - (OSD_TIMER*interval)*interval)
                remaining = floor(totalTime - self.player.getPlayedTime())
                intTime   = roundupDIV(threshold,interval)
                if state:
                    if remaining < intTime: return __show(state,interval+1)
                    show = (self.chkOnNextConditions() and remaining <= threshold)
                    self.log('toggleOnNext, __show: totalTime = %s, threshold = %s, remaining = %s, intTime = %s, interval = %s'%(totalTime, threshold, remaining, intTime, interval))
                    return show, {True:OSD_TIMER*interval,False:intTime}[show]
                return False, remaining - threshold
            except: 
                return False, 0
        
        show, wait = __show(state)
        self.log('toggleOnNext, state = %s, cancel = %s, show = %s, wait = %s'%(state,cancel,show,wait))
        
        if state and show:
            citem   = self.player.sysInfo.get('citem',{}) #channel
            fitem   = self.player.sysInfo.get('fitem',{}) #onnow
            nitem   = self.player.sysInfo.get('nitem',{}) #onnext
            
            if self.onNextMode in [1,2]:                    
                chname    = citem.get('name'     ,BUILTIN.getInfoLabel('ChannelName','VideoPlayer'))
                nowTitle  = fitem.get('label'    ,BUILTIN.getInfoLabel('Title','VideoPlayer'))
                nextTitle = nitem.get('showlabel',BUILTIN.getInfoLabel('NextTitle','VideoPlayer'))
                onNow     = '%s on %s'%(nowTitle,chname) if chname not in validString(nowTitle) else fitem.get('showlabel',nowTitle)
                onNext    = '[B]@ %s[/B] %s'%(BUILTIN.getInfoLabel('NextStartTime','VideoPlayer'),nextTitle if chname not in validString(nextTitle) else nitem.get('showlabel',nextTitle))
                
                if not self._hasControl(self.onNext_Text):
                    self.onNext_Text = xbmcgui.ControlTextBox(self.onNextX, (self.onNextY + 156), 960, 72, 'font27', self.onNextColor)
                    self._addControl(self.onNext_Text)
                self.onNext_Text.setText('%s %s[CR]%s %s'%(LANGUAGE(32104),onNow,LANGUAGE(32116),onNext))
                self.onNext_Text.setAnimations([('WindowOpen' , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                ('WindowOpen' , 'effect=fade start=0 end=100 delay=160 time=240 reversible=false'),
                                                ('WindowClose', 'effect=zoom start=100 end=80 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                ('WindowClose', 'effect=fade start=100 end=0 time=240 reversible=false'),
                                                ('Visible'    , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                ('Visible'    , 'effect=fade end=100 time=240 reversible=false')])
                self._setVisible(self.onNext_Text,True)
                
                if self.onNextMode == 2:
                    landscape = getThumb(nitem)
                    
                    if not self._hasControl(self.onNext_Border):
                        self.onNext_Border = xbmcgui.ControlImage(self.onNextX, self.onNextY, 256, 128, os.path.join(MEDIA_LOC,'colors','white.png'), 0, '0xC0%s'%(COLOR_BACKGROUND))#todo adv. rule to change color.
                        self._addControl(self.onNext_Border)
                    self.onNext_Border.setAnimations([('WindowOpen' , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                      ('WindowOpen' , 'effect=fade start=0 end=100 delay=160 time=240 reversible=false'),
                                                      ('WindowClose', 'effect=zoom start=100 end=80 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                      ('WindowClose', 'effect=fade start=100 end=0 time=240 reversible=false'),
                                                      ('Visible'    , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                      ('Visible'    , 'effect=fade end=100 time=240 reversible=false')])

         
                    if not self._hasControl(self.onNext_Artwork):
                        self.onNext_Artwork = xbmcgui.ControlImage((self.onNextX + 5), (self.onNextY + 5), 246, 118, ' ', aspectRatio=0)
                        self._addControl(self.onNext_Artwork)
                    self.onNext_Artwork.setImage(COLOR_FANART if landscape == FANART else landscape, useCache=False)
                    self.onNext_Artwork.setAnimations([('WindowOpen' , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                       ('WindowOpen' , 'effect=fade start=0 end=100 delay=160 time=240 reversible=false'),
                                                       ('WindowClose', 'effect=zoom start=100 end=80 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                       ('WindowClose', 'effect=fade start=100 end=0 time=240 reversible=false'),
                                                       ('Visible'    , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                       ('Visible'    , 'effect=fade end=100 time=240 reversible=false')])
                        
                    self._setVisible(self.onNext_Artwork,True)
                    self._setVisible(self.onNext_Border,True)
                    xbmc.playSFX(BING_WAV)

            elif self.onNextMode == 3: self.player.toggleInfo()
            elif self.onNextMode == 4: self._updateUpNext(fitem,nitem)
                
        elif self._hasControl(self.onNext_Text):
            self._delControl(self.onNext_Text)
            if self._hasControl(self.onNext_Border):  self._delControl(self.onNext_Border)
            if self._hasControl(self.onNext_Artwork): self._delControl(self.onNext_Artwork)
   
        if not cancel and wait > 0:
            nstate = not bool(show)
            self.log('toggleOnNext, state %s wait %s to new state %s'%(state,wait,nstate))
            timerit(self.toggleOnNext)(wait,[nstate])
            
        
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