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
        self.player  = kwargs.get('player', None)
        self.visible = self._chkGenre()


    def _chkGenre(self):
        genres = self.player.sysInfo.get('fitem',{}).get('genre',[]) + self.player.sysInfo.get('nitem',{}).get('genre',[])
        for genre in genres:
            if genre.lower() in ['pre-roll','post-roll']: return False
        else: return True


    def onInit(self):
        try:
            log("Background: onInit, visible = %s"%(self.visible))
            self.getControl(40004).setVisible(self.visible)   
            if self.visible:      
                logo = (self.player.sysInfo.get('citem',{}).get('logo',(BUILTIN.getInfoLabel('Art(icon)','Player') or  COLOR_LOGO)))
                self.getControl(40002).setImage(COLOR_LOGO if logo.endswith('wlogo.png') else logo)
                self.getControl(40003).setText(LANGUAGE(32104)%(self.player.sysInfo.get('citem',{}).get('name',(BUILTIN.getInfoLabel('ChannelName','VideoPlayer') or ADDON_NAME))))
        except Exception as e:
            log("Background: onInit, failed! %s"%(e), xbmc.LOGERROR)
            self.close()
            
           
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


    def _progressLoop(self, control, wait=SETTINGS.getSettingInt('OSD_Timer')):
        prog = 0
        tot  = wait
        xpos = control.getX()
        control.setVisibleCondition('Player.Playing')
        while not self.monitor.abortRequested():
            if (self.monitor.waitForAbort(1.0) or wait < 0 or self.closing or not self.player.isPlaying()): break
            else:
                prog = int((abs(wait-tot)*100)//tot)
                if prog > 0: control.setAnimations([('Conditional', 'effect=zoom start=%s,100 end=%s,100 time=1000 center=%s,100 condition=True'%((prog-20),(prog),xpos))])
                wait -= 1
        control.setAnimations([('Conditional', 'effect=fade start=%s end=0 time=240 condition=True'%(prog))])
        self.monitor.waitForAbort(0.240)
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
        elif actionId == ACTION_MOVE_UP:       BUILTIN.executebuiltin('AlarmClock(up,Action(up),.5,true,false)')
        elif actionId == ACTION_MOVE_DOWN:     BUILTIN.executebuiltin('AlarmClock(down,Action(down),.5,true,false)')
        elif actionId in ACTION_PREVIOUS_MENU: BUILTIN.executebuiltin('AlarmClock(back,Action(back),.5,true,false)')
        self.onClose()


    def onClose(self):
        log("Restart: onClose")
        self.closing = True
  
  
class Overlay():
    background     = None
    controlManager = dict()
    
    class Player(PLAYER):
        def __init__(self, overlay=None):
            PLAYER.__init__(self)
            self.overlay = overlay
            

        def onAVStarted(self):
            self.overlay.log('onAVStarted')
            self.overlay.toggleBackground(state=False)


        def onPlayBackEnded(self):
            self.overlay.log('onPlayBackEnded')
            self.overlay.toggleBackground()
            
            
        def onPlayBackStopped(self):
            self.overlay.log('onPlayBackStopped')
            self.overlay.toggleBackground(state=False)
            

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
        self.enableOnNext       = SETTINGS.getSettingBool('Enable_OnNext')
        self.enableChannelBug   = SETTINGS.getSettingBool('Enable_ChannelBug')
        self.channelBugInterval = SETTINGS.getSettingInt("Channel_Bug_Interval")
        self.channelBugDiffuse  = SETTINGS.getSettingBool('Force_Diffuse')
        self.minDuration        = SETTINGS.getSettingInt('Seek_Tolerance')
        self.onNextColor        = '0x%s'%((SETTINGS.getSetting('ON_Next_Color')    or 'FFFFFFFF'))
        self.channelBugColor    = '0x%s'%((SETTINGS.getSetting('ChannelBug_Color') or 'FFFFFFFF'))
        
        try:    self.channelBugX, self.channelBugY = eval(SETTINGS.getSetting("Channel_Bug_Position_XY")) #user
        except: self.channelBugX, self.channelBugY = (abs(int(self.window_w // 8) - self.window_w) - 128, abs(int(self.window_h // 16) - self.window_h) - 128) #auto
        self._channelBug = xbmcgui.ControlImage(self.channelBugX, self.channelBugY, 128, 128, ' ', aspectRatio=2)
        
        try:    self.onNextX, self.onNextY = eval(SETTINGS.getSetting("On_Next_Position_XY")) #user
        except: self.onNextX, self.onNextY = abs(int(self.window_w // 8)), abs(int(self.window_h // 16) - self.window_h) #auto
        self._onNext = xbmcgui.ControlTextBox(self.onNextX, self.onNextY, abs(int(self.window_w // 2)), abs(int(self.window_h // 32)), 'font12', self.onNextColor)
        
        #init controls
        self._defViewMode = self.jsonRPC.getViewMode()
        self._vinViewMode = self._defViewMode
        self._vinImage    = SETTINGS.getSetting('Vignette_Image')
        self._vignette    = xbmcgui.ControlImage(0, 0, self.window_w, self.window_h, ' ', aspectRatio=0)
        
        #thread timers
        self._bugThread    = Timer(0.1, self.toggleBug, [False])
        self._onNextThread = Timer(0.1, self.toggleOnNext, [False])
        
        self._Player       = self.Player(overlay=self)


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)

        
    def show(self):
        self.log('show, id = %s, rules = %s'%(self.player.sysInfo.get('citem',{}).get('id'),self.player.sysInfo.get('rules',{})))
        self.runActions(RULES_ACTION_OVERLAY_OPEN, self.player.sysInfo.get('citem',{}), inherited=self)
        self.toggleVignette()
        self.toggleOnNext()
        self.toggleBug()

   
    def close(self):
        self.log('close')
        self.runActions(RULES_ACTION_OVERLAY_CLOSE, self.player.sysInfo.get('citem',{}), inherited=self)
        self.toggleVignette(False)
        self._cancelOnNext()
        self._cancelBug() 
        
        for control, visible in list(self.controlManager.items()):
            self._removeControl(control)
        

    def _hasControl(self, control):
        ctrl = self._getControl(control) != None
        self.log('_hasControl, %s = %s'%(control,ctrl))
        return ctrl
        

    def _getControl(self, control):
        """ If control is not None  == Exists, 
            If control is     True  == Visible, 
            If control is     False == Hidden 
        """
        return self.controlManager.get(control)
        
        
    def _setControl(self, control, state):
        self.controlManager[control] = state
        
        
    def _delControl(self, control):
        self.controlManager.pop(control)
        
        
    def _addControl(self, control):
        """ Create Control & Add to manager.
        """
        try:
            if not self._hasControl(control):
                self._setControl(control,self._setVisible(control, False))
                self.window.addControl(control)
                self.log('_addControl, %s'%(control))
        except Exception as e: self.log('_addControl failed! %s'%(e), xbmc.LOGERROR)
        
        
    def _removeControl(self, control):
        """ Remove Control & Delete from manager.
        """
        try:
            if self._hasControl(control):
                self._delControl(control)
                self.window.removeControl(control)
                self.log('_removeControl, %s'%(control))
        except Exception as e: self.log('_removeControl failed! control = %s %s'%(control, e), xbmc.LOGERROR)

        
    def _setVisible(self, control, state: bool=False):
        try:
            if self._hasControl(control):
                self._setControl(control,state)
                control.setVisible(state)
                self.log('setVisible, %s = %s'%(control,state))
        except Exception('setVisible, failed! control does not exist'): pass
        return state
        
        
    def _isVisible(self, control):
        if hasattr(control, 'isVisible'): return control.isVisible()
        else:                             return (self._getControl(control) or False)


    def toggleBackground(self, state: bool=True):
        if state and self.background is None: 
            self.background = Background(BACKGROUND_XML, ADDON_PATH, "default", player=self.player)
            self.log('toggleBackground, state = %s'%(state))
            self.background.doModal()
            self.background = None
        elif not state and not self.background is None:
            self.background = self.background.close()
            
        # if self.player.isPlaying() and not BUILTIN.getInfoBool('IsTopMost(fullscreenvideo)','Window'):
            # BUILTIN.executebuiltin('ActivateWindow(fullscreenvideo)')


    def toggleVignette(self, state: bool=True):
        if state and self.enableVignette:
            if not self._hasControl(self._vignette):
                timerit(self.jsonRPC.setViewMode)(0.1,[self._vinViewMode])
                self._vignette = xbmcgui.ControlImage(0, 0, self.window_w, self.window_h, self._vinImage, aspectRatio=0)
                self._addControl(self._vignette)
                self._vignette.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=240 delay=160 condition=True reversible=True')])
                self._vignette.setImage(self._vinImage)
                self._setVisible(self._vignette,True)
                self.log('toggleVignette, state = %s, image = %s\nmode = %s'%(state, self._vinImage,self._vinViewMode))
        elif not state and self._hasControl(self._vignette):
            timerit(self.jsonRPC.setViewMode)(0.1,[self._defViewMode])
            self._removeControl(self._vignette)
            self.log('toggleVignette, state = %s, image = %s\nmode = %s'%(state, self._vinImage,self._defViewMode))
            
                
    def _cancelBug(self):
        self.log('_cancelBug')
        if self._bugThread.is_alive():
            if hasattr(self._bugThread, 'cancel'): self._bugThread.cancel()
            try: self._bugThread.join()
            except: pass
        if self._hasControl(self._channelBug):
            self._removeControl(self._channelBug)
            
            
    def toggleBug(self, state: bool=True):
        def _getWait(state, remaining):
            if self.channelBugInterval == -1: 
                onVAL  = remaining
                offVAL = 0.1
            elif self.channelBugInterval == 0:
                onVAL  = random.randint(0,remaining)
                offVAL = random.randint(0,remaining)
            else:
                onVAL  = self.channelBugInterval * 60
                offVAL = round(onVAL // 2)
            self.log('toggleBug, _getWait onVAL, offVAL (%s,%s)'%(onVAL, offVAL))
            return {True:float(onVAL),False:float(offVAL)}[state]

        remaining = abs(floor(self.player.getRemainingTime()))
        if remaining <= 0 or remaining <= self.minDuration: return 

        wait   = _getWait(state, remaining)
        nstate = not bool(state)
        
        if state and self.enableChannelBug:
            if BUILTIN.getInfoLabel('Genre','VideoPlayer') in FILLER_TYPE:
                return  self.log('toggleBug, Filler Playing') 
                
            elif self.player.getPlayerProgress() >= SETTINGS.getSettingInt('Seek_Threshold'):
                return  self.log('toggleBug, remaining time greater than threshold') 
                
            elif not self._hasControl(self._channelBug):
                logo = self.player.sysInfo.get('citem',{}).get('logo',(BUILTIN.getInfoLabel('Art(icon)','Player') or  LOGO))
                try:    self.channelBugX, self.channelBugY = eval(SETTINGS.getSetting("Channel_Bug_Position_XY")) #user
                except: self.channelBugX, self.channelBugY = subZoom(abs(int(self.window_w // 8) - self.window_w) - 128, self._vinViewMode.get('zoom')), subZoom(abs(int(self.window_h // 16) - self.window_h) - 128, self._vinViewMode.get('zoom')) #auto w/ zoom offset
                
                self._channelBug = xbmcgui.ControlImage(self.channelBugX, self.channelBugY, 128, 128, logo, aspectRatio=2)
                self._addControl(self._channelBug)
                self._channelBug.setVisibleCondition('[!String.Contains(VideoPlayer.Genre,Pre-Roll) | !String.Contains(VideoPlayer.Genre,Post-Roll)]')
                self._channelBug.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=2000 delay=1000 condition=True reversible=False'),
                                                ('Conditional', 'effect=fade start=100 end=25 time=1000 delay=3000 condition=True reversible=False')])
                
                if   self.channelBugDiffuse:      self._channelBug.setColorDiffuse(self.channelBugColor)
                elif self.resources.isMono(logo): self._channelBug.setColorDiffuse(self.channelBugColor)
                self.log('toggleBug, logo = %s, setColorDiffuse = %s, POSXY (%s,%s))'%(logo, self.channelBugColor, self.channelBugX, self.channelBugY))
            self._setVisible(self._channelBug,True)
        elif not state and self._hasControl(self._channelBug):
            if self._hasControl(self._channelBug): self._channelBug.setImage(' ')
            self._setVisible(self._channelBug,False)
            
        self.log('toggleBug, state %s wait %s to new state %s'%(state,wait,nstate))
        self._bugThread = Timer(wait, self.toggleBug, [nstate])
        self._bugThread.name = "_bugThread"
        self._bugThread.daemon=True
        self._bugThread.start()

    
    def _cancelOnNext(self):
        self.log('_cancelOnNext')
        if self._onNextThread.is_alive():
            if hasattr(self._onNextThread, 'cancel'): self._onNextThread.cancel()
            try: self._onNextThread.join()
            except: pass
        if self._hasControl(self._onNext):
            self._removeControl(self._channelBug)
                
            
    def toggleOnNext(self, state: bool=True, cancel: bool=False):
        def getOnNextInterval(interval, remaining):
            #split totalTime time into quarters, last quarter triggers nextup split by equal intervals of 3. ie. display 3 times in the last quarter of show
            totalTime  = int(self.player.getPlayerTime())
            showTime   = (abs(totalTime - (totalTime * .75)) - (SETTINGS.getSettingInt('OSD_Timer') * interval))
            intTime    = roundupDIV(showTime,interval)
            showOnNext = (remaining <= showTime and totalTime > self.minDuration)
            
            if remaining < intTime: return getOnNextInterval(interval+1, remaining)
            self.log('toggleOnNext, totalTime = %s, interval = %s, remaining = %s, intTime = %s, showOnNext = %s'%(totalTime,interval,remaining,intTime,showOnNext))
            return showOnNext, intTime

        remaining = abs(floor(self.player.getRemainingTime()))
        if remaining <= 0: return 
        showOnNext, intTime = getOnNextInterval(ON_NEXT_COUNT,remaining)
        wait   = {True:FIFTEEN,False:float(intTime)}[state]
        nstate = not bool(state)
        if state and showOnNext and self.enableOnNext:
            if BUILTIN.getInfoLabel('Genre','VideoPlayer') in FILLER_TYPE: return  self.log('toggleOnNext, Filler Playing') 
            elif self.player.getPlayerProgress() >= SETTINGS.getSettingInt('Seek_Threshold'): return  self.log('toggleOnNext, remaining time greater than threshold') 
            elif not self._hasControl(self._onNext):
                self._onNext = xbmcgui.ControlTextBox(addZoom((self.window_w // 8),self._vinViewMode.get('zoom'),50), subZoom(abs(int(self.window_h // 16) - self.window_h),self._vinViewMode.get('zoom')), 1920, 36, 'font12', self.onNextColor)
                self._addControl(self._onNext)
                self._onNext.setVisibleCondition('[!String.Contains(VideoPlayer.Genre,Pre-Roll) | !String.Contains(VideoPlayer.Genre,Post-Roll)]')
            
            citem = self.player.sysInfo.get('citem',{}) #channel
            fitem = self.player.sysInfo.get('fitem',{}) #onnow
            nitem = self.player.sysInfo.get('nitem',{}) #onnext
            if self.player.sysInfo.get('isPlaylist',False): self._updateUpNext(fitem,nitem)
            else:
                chname    = citem.get('name',BUILTIN.getInfoLabel('ChannelName','VideoPlayer'))
                nowTitle  = fitem.get('label',BUILTIN.getInfoLabel('Title','VideoPlayer'))
                nextTitle = nitem.get('showlabel',BUILTIN.getInfoLabel('NextTitle','VideoPlayer'))
                onNow     = '%s on %s'%(nowTitle,chname) if chname not in validString(nowTitle) else fitem.get('showlabel',nowTitle)
                onNext    = '%s @ %s'%(nextTitle,BUILTIN.getInfoLabel('NextStartTime','VideoPlayer'))
                
                self._onNext.setText('%s\n%s'%(LANGUAGE(32104)%(onNow),LANGUAGE(32116)%(onNext)))
                self._onNext.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=%s delay=%s condition=True reversible=True'%(ceil(wait//4)*1000,(ceil(wait//4)-2)*1000))])
                self._onNext.autoScroll(5500, 2500, int(FIFTEEN//3))
                self._setVisible(self._onNext,True)
                nstate = not bool(state)
                timerit(playSFX)(0.1,[BING_WAV])
        elif not state and self._hasControl(self._onNext):
            if self._hasControl(self._onNext): self._onNext.setText(' ')
            self._setVisible(self._onNext,False)
            
        self.log('toggleOnNext, state %s wait %s to new state %s'%(state,wait,nstate))
        self._onNextThread = Timer(wait, self.toggleOnNext, [nstate])
        self._onNextThread.name = "onNextThread"
        self._onNextThread.daemon=True
        self._onNextThread.start()
        
        
    def _updateUpNext(self, nowItem: dict={}, nextItem: dict={}):
        self.log('_updateUpNext')
        try:
            # https://github.com/im85288/service.upnext/wiki/Example-source-code
            data            = dict()
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
        timerit(self.jsonRPC.notifyAll)(0.1,['upnext_data', binascii.hexlify(json.dumps(data).encode('utf-8')).decode('utf-8'), '%s.SIGNAL'%(ADDON_ID)])