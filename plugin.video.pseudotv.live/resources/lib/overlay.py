  # Copyright (C) 2025 Lunatixz


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

class Busy(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)


    def onAction(self, act):
        actionId = act.getId()
        log('Busy: onAction: actionId = %s'%(actionId))
        if actionId in ACTION_PREVIOUS_MENU: self.close()


class Background(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.player  = kwargs.get('player', None)
        self.sysInfo = kwargs.get('sysInfo', self.player.sysInfo)
        
        self.citem   = self.sysInfo.get('citem',{})
        self.fitem   = self.sysInfo.get('fitem',{})
        
        self.nitem   = self.player.jsonRPC.getNextItem(self.citem,self.sysInfo.get('nitem'))
      
      
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onInit(self):
        try:
            self.log('onInit, citem = %s\nfitem = %ss\nnitem = %s'%(self.citem,self.fitem,self.nitem))
            logo      = (self.citem.get('logo')      or BUILTIN.getInfoLabel('Art(icon)','Player') or LOGO)
            land      = (getThumb(self.nitem)        or COLOR_FANART)
            chname    = (self.citem.get('name')      or BUILTIN.getInfoLabel('ChannelName','VideoPlayer'))
            nowTitle  = (self.fitem.get('label')     or BUILTIN.getInfoLabel('Title','VideoPlayer'))
            nextTitle = (self.nitem.get('showlabel') or BUILTIN.getInfoLabel('NextTitle','VideoPlayer') or chname)

            try: nextTime = epochTime(self.nitem['start']).strftime('%I:%M%p')
            except Exception as e: 
                self.log("__init__, nextTime failed! %s\nstart = %s"%(e,self.nitem.get('start')), xbmc.LOGERROR)
                nextTime = BUILTIN.getInfoLabel('NextStartTime','VideoPlayer')
                
            onNow  = '%s on %s'%(nowTitle,chname) if chname not in validString(nowTitle) else nowTitle
            onNext = '@ %s: %s'%(nextTime,nextTitle)
        
            window_h, window_w = 1080, 1920 # window_h, window_w = (self.getHeight(), self.getWidth())
            onNextX, onNextY = abs(int(window_w // 9)), abs(int(window_h // 16) - window_h) - 356 #auto
            
            self.getControl(40001).setPosition(onNextX, onNextY)
            self.getControl(40001).setVisibleCondition('[Player.Playing + !Window.IsVisible(fullscreeninfo) + Window.IsVisible(fullscreenvideo)]')
            self.getControl(40001).setAnimations([('WindowOpen' , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(onNextX, onNextY)),
                                                  ('WindowOpen' , 'effect=fade start=0 end=100 delay=160 time=240 reversible=false'),
                                                  ('WindowClose', 'effect=zoom start=100 end=80 center=%s,%s delay=160 tween=back time=240 reversible=false'%(onNextX, onNextY)),
                                                  ('WindowClose', 'effect=fade start=100 end=0 time=240 reversible=false'),
                                                  ('Visible'    , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(onNextX, onNextY)),
                                                  ('Visible'    , 'effect=fade end=100 time=240 reversible=false')])
            self.getControl(40002).setImage(COLOR_LOGO if logo.endswith('wlogo.png') else logo)
            self.getControl(40003).setText('%s %s[CR]%s [B]%s[/B]'%(LANGUAGE(32104),onNow,LANGUAGE(32116),onNext))
            self.getControl(40004).setImage(land)
        except Exception as e:
            self.log("onInit, failed! %s"%(e), xbmc.LOGERROR)
            self.close()

            
class Restart(xbmcgui.WindowXMLDialog):
    closing = False
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.player  = kwargs.get('player', None)
        self.sysInfo = kwargs.get('sysInfo', self.player.sysInfo)
        self.monitor = self.player.service.monitor
        
        if bool(self.player.restartPercentage) and self.sysInfo.get('fitem'):
            progress = self.player.getPlayerProgress()
            self.log("__init__, restartPercentage = %s, progress = %s"%(self.player.restartPercentage, progress))
            if (progress >= self.player.restartPercentage and progress < self.player.maxProgress) and not isFiller(self.sysInfo.get('fitem',{})):
                self.doModal()
                
                
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    
    
    def _isVisible(self, control):
        try:    return control.isVisible()
        except: return (BUILTIN.getInfoBool('Playing','Player') and not bool(BUILTIN.getInfoBool('IsVisible(fullscreeninfo)','Window')) | BUILTIN.getInfoBool('IsVisible(fullscreenvideo)','Window'))
    
    
    def onInit(self):
        self.log("onInit")
        try:
            prog = 0
            wait = OSD_TIMER*2
            tot  = wait
            control = self.getControl(40000)
            control.setVisibleCondition('[Player.Playing + !Window.IsVisible(fullscreeninfo) + Window.IsVisible(fullscreenvideo)]')
            xpos = control.getX()
            
            while not self.monitor.abortRequested():
                if (self.monitor.waitForAbort(0.5) or self._isVisible(control) or self.closing): break
                    
            while not self.monitor.abortRequested():
                if (self.monitor.waitForAbort(0.5) or wait < 0 or self.closing or not self.player.isPlaying()): break
                else:
                    prog = int((abs(wait-tot)*100)//tot)
                    if prog > 0: control.setAnimations([('Conditional', 'effect=zoom start=%s,100 end=%s,100 time=1000 center=%s,100 condition=True'%((prog-20),(prog),xpos))])
                    wait -= 1
            
            control.setAnimations([('Conditional', 'effect=fade start=%s end=0 time=240 delay=0.240 condition=True'%(prog))])
            control.setVisible(False)
            self.setFocusId(40001)
        except Exception as e: self.log("onInit, failed! %s\ncitem = %s"%(e,self.sysInfo), xbmc.LOGERROR)
        self.log("onInit, closing")
        self.close()


    def onAction(self, act):
        actionId = act.getId()
        self.log('onAction: actionId = %s'%(actionId))
        self.closing = True
        if actionId in ACTION_SELECT_ITEM and self.getFocusId(40001): 
            if   self.sysInfo.get('isPlaylist',False): self.player.seekTime(0)
            elif self.sysInfo.get('fitem'): 
                with BUILTIN.busy_dialog():
                    liz = LISTITEMS.buildItemListItem(self.sysInfo.get('fitem',{}))
                    liz.setProperty('sysInfo',encodeString(dumpJSON(self.sysInfo)))
                    self.player.stop()
                timerit(self.player.play)(1.0,[self.sysInfo.get('fitem',{}).get('catchup-id'),liz])
            else: DIALOG.notificationDialog(LANGUAGE(30154))
        elif actionId == ACTION_MOVE_UP:       timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(up,Action(up),.5,true,false)'])
        elif actionId == ACTION_MOVE_DOWN:     timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(down,Action(down),.5,true,false)'])
        elif actionId in ACTION_PREVIOUS_MENU: timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(back,Action(back),.5,true,false)'])


    def onClose(self):
        self.log("onClose")
        self.closing = True
        

class Overlay():
    channelBug     = None
    vignette       = None
    controlManager = dict()
    
    def __init__(self, *args, **kwargs):
        self.log("__init__")
        self.player     = kwargs.get('player', None)
        self.sysInfo    = kwargs.get('sysInfo', self.player.sysInfo)
        
        self.service    = self.player.service
        self.jsonRPC    = self.player.jsonRPC
        self.runActions = self.player.runActions
        self.resources  = Resources(service=self.service)
        
        self.window     = xbmcgui.Window(12005) 
        self.window_h, self.window_w = 1080, 1920
        
        #vignette rules
        self.enableVignette = False
        self.defaultView    = self.jsonRPC.getViewMode()
        self.vinView        = self.defaultView
        self.vinImage       = ''
        
        #channelBug rules
        self.enableChannelBug = SETTINGS.getSettingBool('Enable_ChannelBug')
        self.forceBugDiffuse  = SETTINGS.getSettingBool('Force_Diffuse')
        self.channelBugColor  = '0x%s'%((SETTINGS.getSetting('ChannelBug_Color') or 'FFFFFFFF'))
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _hasControl(self, control):
        return control in self.controlManager
        

    def _isVisible(self, control):
        return self.controlManager.get(control,False)


    def _setVisible(self, control, state: bool=False):
        self.log('_setVisible, %s = %s'%(control,state))
        try:
            control.setVisible(state)
            return state
        except Exception as e: 
            self.log('_setVisible, failed! control = %s %s'%(control,e))
            self._delControl(control)
            return False


    def _addControl(self, control):
        if not self._hasControl(control):
            try: 
                self.log('_addControl, %s'%(control))
                self.window.addControl(control)
                self.controlManager[control] = self._setVisible(control,True)
            except Exception as e: 
                self.log('_addControl failed! control = %s %s'%(control, e), xbmc.LOGERROR)
                self._delControl(control)
        
        
    def _delControl(self, control):
        if self._hasControl(control):
            self.log('_delControl, %s'%(control))
            try: self.window.removeControl(control)
            except Exception as e: self.log('_delControl failed! control = %s %s'%(control, e), xbmc.LOGERROR)
            self.controlManager.pop(control)  
            
            
    def open(self):
        if self.sysInfo.get('citem',{}):
            self.runActions(RULES_ACTION_OVERLAY_OPEN, self.sysInfo.get('citem',{}), inherited=self)
            self.log("open, enableVignette = %s, enableChannelBug = %s"%(self.enableVignette, self.enableChannelBug))
            if self.enableVignette:
                window_h, window_w = (self.window.getHeight(), self.window.getWidth())
                self.vignette = xbmcgui.ControlImage(0, 0, window_w, window_h, ' ', aspectRatio=0)
                self._addControl(self.vignette)
                self.vignette.setImage(self.vinImage)
                if self.vinView != self.defaultView: timerit(self.jsonRPC.setViewMode)(0.5,[self.vinView])
                self.vignette.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=240 delay=160 condition=True reversible=True')])
                self.log('enableVignette, vinImage = %s, vinView = %s'%(self.vinImage,self.vinView))
            
            if self.enableChannelBug:
                try:    self.channelBugX, self.channelBugY = eval(SETTINGS.getSetting("Channel_Bug_Position_XY")) #user
                except: self.channelBugX, self.channelBugY = abs(int(self.window_w // 9) - self.window_w) - 128, abs(int(self.window_h // 16) - self.window_h) - 128 #auto        

                self.channelBug = xbmcgui.ControlImage(self.channelBugX, self.channelBugY, 128, 128, ' ', aspectRatio=2)
                self._addControl(self.channelBug)
                
                logo = self.sysInfo.get('citem',{}).get('logo',(BUILTIN.getInfoLabel('Art(icon)','Player') or LOGO))
                if   self.forceBugDiffuse:        self.channelBug.setColorDiffuse(self.channelBugColor)
                elif self.resources.isMono(logo): self.channelBug.setColorDiffuse(self.channelBugColor)
                self.channelBug.setImage(logo)
                self.channelBug.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=2000 delay=1000 condition=Control.IsVisible(%i) reversible=false'%(self.channelBug.getId())),
                                               ('Conditional', 'effect=fade start=100 end=25 time=1000 delay=3000 condition=Control.IsVisible(%i) reversible=false'%(self.channelBug.getId()))])
                self.log('enableChannelBug, logo = %s, channelBugColor = %s, window = (%s,%s)'%(logo,self.channelBugColor,self.window_h, self.window_w))
        else: self.close()
        
        
    def close(self):
        self.log("close")
        self._delControl(self.vignette)
        self._delControl(self.channelBug)
        if self.vinView != self.defaultView: timerit(self.jsonRPC.setViewMode)(0.5,[self.defaultView])
        
        
class OnNext(xbmcgui.WindowXMLDialog):
    closing   = False
    totalTime = 0
    threshold = 0
    remaining = 0
    intTime   = 0
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.player     = kwargs.get('player', None)
        self.sysInfo    = kwargs.get('sysInfo', self.player.sysInfo)
        
        self.jsonRPC    = self.player.jsonRPC
        self.monitor    = self.player.service.monitor
        self.runActions = self.player.runActions
        
        self.citem      = self.sysInfo.get('citem',{})
        self.fitem      = self.sysInfo.get('fitem',{})
        self.nitem      = self.jsonRPC.getNextItem(self.citem,self.sysInfo.get('nitem'))
                
        self.window     = xbmcgui.Window(12005) 
        self.window_h, self.window_w = 1080, 1920 #self.window_h, self.window_w = (self.window.getHeight(), self.window.getWidth())
        
        #onNext rules
        self.enableOnNext = bool(SETTINGS.getSettingInt('OnNext_Enable'))
        self.onNextMode   = SETTINGS.getSettingInt('OnNext_Enable')
        
        try:    self.onNextX, self.onNextY = eval(SETTINGS.getSetting("OnNext_Position_XY")) #user
        except: self.onNextX, self.onNextY = abs(int(self.window_w // 9)), abs(int(self.window_h // 16) - self.window_h) - 356 #auto
    
        self.runActions(RULES_ACTION_OVERLAY_OPEN, self.sysInfo.get('citem',{}), inherited=self)
        self.log('__init__, enableOnNext = %s, onNextMode = %s, onNextX = %s, onNextY = %s'%(self.enableOnNext,self.onNextMode,self.onNextX,self.onNextY))
        
        if bool(self.enableOnNext) and not isFiller(self.fitem):
            self.totalTime = int(self.player.getPlayerTime() * (self.player.maxProgress / 100))
            self.threshold = abs((self.totalTime - (self.totalTime * .75)) - (ONNEXT_TIMER*3))
            self.remaining = floor(self.totalTime - self.player.getPlayedTime())
            self.intTime   = roundupDIV(self.threshold,3)
            self.log('__init__, totalTime = %s, threshold = %s, remaining = %s, intTime = %s'%(self.totalTime,self.threshold,self.remaining,self.intTime))
            if self.remaining >= self.intTime:
                self.doModal()
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

        
    def onInit(self):
        def __chkCitem():
            return sorted(self.citem) == sorted(self.player.sysInfo.get('citem',{}))
        try:
            self.log('onInit, citem = %s\nfitem = %ss\nnitem = %s'%(self.citem,self.fitem,self.nitem))
            if self.onNextMode in [1,2]: 
                logo      = (self.citem.get('logo')      or BUILTIN.getInfoLabel('Art(icon)','Player') or LOGO)
                land      = (getThumb(self.nitem)        or COLOR_FANART)
                chname    = (self.citem.get('name')      or BUILTIN.getInfoLabel('ChannelName','VideoPlayer'))
                nowTitle  = (self.fitem.get('label')     or BUILTIN.getInfoLabel('Title','VideoPlayer'))
                nextTitle = (self.nitem.get('showlabel') or BUILTIN.getInfoLabel('NextTitle','VideoPlayer') or chname)

                try: nextTime = epochTime(self.nitem['start']).strftime('%I:%M%p')
                except Exception as e: 
                    self.log("__init__, nextTime failed! %s\nstart = %s"%(e,self.nitem.get('start')), xbmc.LOGERROR)
                    nextTime = BUILTIN.getInfoLabel('NextStartTime','VideoPlayer')

                onNow  = '%s on %s'%(nowTitle,chname) if chname not in validString(nowTitle) else nowTitle
                onNext = '@ %s: %s'%(nextTime,nextTitle)
            
                self.getControl(40001).setPosition(self.onNextX, self.onNextY)
                self.getControl(40001).setVisibleCondition('[Player.Playing + !Window.IsVisible(fullscreeninfo) + Window.IsVisible(fullscreenvideo)]')
                self.getControl(40001).setAnimations([('WindowOpen' , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                      ('WindowOpen' , 'effect=fade start=0 end=100 delay=160 time=240 reversible=false'),
                                                      ('WindowClose', 'effect=zoom start=100 end=80 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                      ('WindowClose', 'effect=fade start=100 end=0 time=240 reversible=false'),
                                                      ('Visible'    , 'effect=zoom start=80 end=100 center=%s,%s delay=160 tween=back time=240 reversible=false'%(self.onNextX, self.onNextY)),
                                                      ('Visible'    , 'effect=fade end=100 time=240 reversible=false')])
                self.onNext_Text = self.getControl(40003)
                self.onNext_Text.setVisible(False)
                self.onNext_Text.setText('%s %s[CR]%s [B]%s[/B]'%(LANGUAGE(32104),onNow,LANGUAGE(32116),onNext))
                
                if self.onNextMode == 2:
                    self.onNext_Artwork = self.getControl(40004)
                    self.onNext_Artwork.setVisible(False)
                    self.onNext_Artwork.setImage(land)

                    self.onNext_Text.setVisible(True)
                    self.onNext_Artwork.setVisible(True)
                    xbmc.playSFX(BING_WAV)
                    
                    show = ONNEXT_TIMER*2
                    while not self.monitor.abortRequested() and not self.closing:
                        self.log('onInit, showing (%s)'%(show))
                        if self.monitor.waitForAbort(0.5) or not self.player.isPlaying() or show < 1 or not __chkCitem(): break
                        else: show -= 1
                        
                    self.onNext_Text.setVisible(False)
                    self.onNext_Artwork.setVisible(False)
                    
            elif  self.onNextMode == 3: self.player.toggleInfo()
            elif  self.onNextMode == 4: self._updateUpNext(self.fitem,self.nitem) 

            wait = self.intTime*2
            while not self.monitor.abortRequested() and not self.closing:
                self.log('onInit, waiting (%s)'%(wait))
                if self.monitor.waitForAbort(0.5) or not self.player.isPlaying() or wait < 1 or not __chkCitem(): break
                else: wait -= 1
                        
        except Exception as e: self.log("onInit, failed! %s"%(e), xbmc.LOGERROR)
        self.log("onInit, closing")
        self.close()
                
                
    def _updateUpNext(self, nowItem: dict={}, nextItem: dict={}):
        self.log('_updateUpNext')
        data = dict()
        try:# https://github.com/im85288/service.upnext/wiki/Example-source-code
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
        if data: timerit(self.jsonRPC.notifyAll)(0.5,['upnext_data', binascii.hexlify(json.dumps(data).encode('utf-8')).decode('utf-8'), '%s.SIGNAL'%(ADDON_ID)])
        
        
    def onAction(self, act):
        actionId = act.getId()
        self.log('onAction: actionId = %s'%(actionId))
        self.closing = True
        if   actionId == ACTION_MOVE_UP:       timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(up,Action(up),.5,true,false)'])
        elif actionId == ACTION_MOVE_DOWN:     timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(down,Action(down),.5,true,false)'])
        elif actionId in ACTION_PREVIOUS_MENU: timerit(BUILTIN.executebuiltin)(0.1,['AlarmClock(back,Action(back),.5,true,false)'])


    def onClose(self):
        self.log('onClose')
        self.closing = True