  # Copyright (C) 2026 Lunatixz


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

WH, WIN = BUILTIN.getResolution()

class Busy(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.isLocked = kwargs.pop('isLocked', False)
        super().__init__(*args, **kwargs)
                
    def onInit(self):
        log(f"Busy: onInit, isLocked = {self.isLocked}")
        
        try:
            spinner = self.getControl(41)
            diffuse_color = "0xC0FF0000" if self.isLocked else "0xFF01416b"
            spinner.setColorDiffuse(diffuse_color)
        except Exception as e:
            log(f"Busy: Failed to modify UI Control 41 spinner element: {str(e)}", xbmc.LOGERROR)

    def onAction(self, act):
        actionId = act.getId()
        if actionId == 0 or not actionId: return
        log(f"Busy: onAction, actionId = {actionId}, isLocked = {self.isLocked}")
        if actionId in ACTION_PREVIOUS_MENU:
            if not self.isLocked:
                self.close()
            else:
                DIALOG.notificationDialog(LANGUAGE(32260))
                
class Background(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop('service', None)
        super().__init__(*args, **kwargs)
        
        self.player  = self.service.player if self.service else None
        playing_item = self.player.playingItem if (self.player and hasattr(self.player, 'playingItem')) else {}
        
        self.citem = playing_item.get('citem', {})
        self.fitem = playing_item.get('fitem', {})
        self.nitem = playing_item.get('nitem', {})
      
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def onInit(self):
        try:
            self.log(f"onInit: citem={self.citem}\nfitem={self.fitem}\nnitem={self.nitem}")
            logo      = self.citem.get('logo') or BUILTIN.getInfoLabel('Player.Art(icon)') or LOGO
            chname    = self.citem.get('name') or BUILTIN.getInfoLabel('VideoPlayer.ChannelName')
            nowTitle  = self.fitem.get('label') or BUILTIN.getInfoLabel('VideoPlayer.Title')
            nextTitle = self.nitem.get('showlabel') or BUILTIN.getInfoLabel('VideoPlayer.NextTitle') or chname

            nextTime = ""
            start_val = self.nitem.get('start')
            if start_val:
                try:              nextTime = epochTime(start_val).strftime('%I:%M%p')
                except Exception: nextTime = ""
                    
            if not nextTime: nextTime = BUILTIN.getInfoLabel('VideoPlayer.NextStartTime')
            if not nextTime:
                self.log("onInit: Time markers missing. Aborting overlay instantiation.", xbmc.LOGDEBUG)
                self.close()
                return
                
            onNow  = nowTitle if chname in validString(nowTitle) else f"{nowTitle} on {chname}"
            onNext = f"@ {nextTime}: {nextTitle}"
            window_w, window_h = WH
            onNextX = abs(int(window_w // 9))
            onNextY = abs(int(window_h // 16) - window_h) - 356 
            
            container_control = self.getControl(40001)
            if container_control:
                container_control.setPosition(onNextX, onNextY)
                container_control.setVisibleCondition('[Player.Playing + !Window.IsVisible(fullscreeninfo) + Window.IsVisible(fullscreenvideo)]')
                container_control.setAnimations([
                    ('WindowOpen' , f'effect=zoom start=80 end=100 center={onNextX},{onNextY} delay=160 tween=back time=240 reversible=false'),
                    ('WindowOpen' , 'effect=fade start=0 end=100 delay=160 time=240 reversible=false'),
                    ('WindowClose', f'effect=zoom start=100 end=80 center={onNextX},{onNextY} delay=160 tween=back time=240 reversible=false'),
                    ('WindowClose', 'effect=fade start=100 end=0 time=240 reversible=false'),
                    ('Visible'    , f'effect=zoom start=80 end=100 center={onNextX},{onNextY} delay=160 tween=back time=240 reversible=false'),
                    ('Visible'    , 'effect=fade end=100 time=240 reversible=false')
                ])
            
            logo_img = LOGO_COLOR if logo.endswith('wlogo.png') else logo
            self.getControl(40002).setImage(logo_img)
            info_text = f"{LANGUAGE(32104)} {onNow}[CR]{LANGUAGE(32116)} [B]{onNext}[B]"
            self.getControl(40003).setText(info_text)
            thumb_art = Globals._getThumb(self.nitem)
            if thumb_art: self.getControl(40004).setImage(thumb_art)
        except Exception as e:
            self.log(f"onInit execution failed: {str(e)}", xbmc.LOGERROR)
            self.close()

class Replay(xbmcgui.WindowXMLDialog):
    closing = False
    
    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop('service', None)
        super().__init__(*args, **kwargs)
        
        self.monitor = self.service.monitor if self.service else None
        self.player  = self.service.player if self.service else None
        
        playing_item = self.player.playingItem if (self.player and hasattr(self.player, 'playingItem')) else {}
        self.citem   = playing_item.get('citem', {})
        self.fitem   = playing_item.get('fitem', {})
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)
        
    def show_dialog(self):
        if not self.player or not self.fitem:  return False
        replay_pct = getattr(self.player, 'replayPercentage', 0)
        max_pct = getattr(self.player, 'maxProgress', 100)

        if replay_pct > 0:
            try:
                progress = self.player.getPlayerProgress()
                if replay_pct <= progress < max_pct:
                    self.log(f"show_dialog: Trigger hit. Progress: {progress}%")
                    self.doModal()
                    return True
            except Exception as e:
                self.log(f"show_dialog fallback fail: {str(e)}", xbmc.LOGERROR)
        return False
        
    def _isVisible(self, control):
        try:              
            return control.isVisible()
        except Exception: 
            is_playing    = BUILTIN.getInfoBool('Player.Playing')
            info_visible  = BUILTIN.getInfoBool('Window.IsVisible(fullscreeninfo)')
            video_visible = BUILTIN.getInfoBool('Window.IsVisible(fullscreenvideo)')
            return (is_playing and not info_visible) or video_visible
        
    def onInit(self):
        self.log("onInit: Initializing dialog components.")
        try:
            control = self.getControl(40000)
            control.setVisibleCondition('[Player.Playing + !Window.IsVisible(fullscreeninfo) + Window.IsVisible(fullscreenvideo)]')
            self.service._que(self._run_osd_countdown, 1, 0, 0, control)
        except Exception as e: 
            self.log(f"onInit failed: {str(e)}", xbmc.LOGERROR)
            self.service._que(self.close, 1, 0, 0)

    def _run_osd_countdown(self, control):
        try:
            wait = OSD_TIMER * 2
            tot = wait
            xpos = control.getX()
            
            while not self.monitor.abortRequested():
                if self.service._shutdown(CPU_CYCLE) or self._isVisible(control) or self.closing: 
                    break
                self.service._sleep(int(CPU_CYCLE * 1000))
                    
            while not self.monitor.abortRequested():
                if self.service._shutdown(CPU_CYCLE) or wait < 0 or self.closing or not self.player.isPlayingPseudoTV(): 
                    break
                
                prog = int((abs(wait - tot) * 100) // tot)
                if prog > 0: 
                    control.setAnimations([('Conditional', f'effect=zoom start={prog-20},100 end={prog},100 time=1000 center={xpos},100 condition=True')])
                
                wait -= CPU_CYCLE
                self.service._sleep(int(CPU_CYCLE * 1000))
            
            control.setAnimations([('Conditional', f'effect=fade start={prog if "prog" in locals() else 100} end=0 time=240 delay=0.240 condition=True')])
            control.setVisible(False)
            self.setFocusId(40001)
        except Exception as e:
            self.log(f"Background OSD countdown loop crashed: {str(e)}", xbmc.LOGERROR)
        finally:
            self.service._que(self.close, 1, 0, 0)

    def onAction(self, act):
        actionId = act.getId()
        self.log(f"onAction: actionId = {actionId}")
        self.closing = True
        
        if   actionId == ACTION_MOVE_UP:       BUILTIN.executebuiltin('AlarmClock(up,Action(up),.5,true,false)')
        elif actionId == ACTION_MOVE_DOWN:     BUILTIN.executebuiltin('AlarmClock(down,Action(down),.5,true,false)')
        elif actionId in ACTION_PREVIOUS_MENU: BUILTIN.executebuiltin('AlarmClock(back,Action(back),.5,true,false)')
        elif actionId in ACTION_SELECT_ITEM and self.getFocusId() == 40001: 
            if self.player.playingItem.get('isPlaylist', False): self.player.seekTime(0)
            elif self.fitem: 
                with BUILTIN.busy_dialog():
                    liz = LISTITEMS.buildItemListItem(self.fitem)
                    liz.setProperty('sysInfo', FileAccess._encodeString(self.player.playingItem))
                    timerit(self.player.play)(1.0, *(self.fitem.get('catchup-id'), liz))
                    self.player.stop()
            else: 
                DIALOG.notificationDialog(LANGUAGE(30154))

    def onClose(self):
        self.log("onClose")
        self.closing = True


class Overlay:
    def __init__(self, *args, **kwargs):
        self.service    = kwargs.get('service', None)
        self.player     = self.service.player if self.service else None
        self.jsonRPC    = self.player.jsonRPC if self.player else None
        self.runActions = self.player.runActions if self.player else None
        
        playing_item = self.player.playingItem if (self.player and hasattr(self.player, 'playingItem')) else {}
        self.citem = playing_item.get('citem', {})
        self.fitem = playing_item.get('fitem', {})
        self.nitem = playing_item.get('nitem', {})
        self.resources = Resources(service=self.service) if self.service else None
        
        self.cntrlManager = {}
        self.channelBug   = None
        self.vignette     = None
        self.onnext       = None
        
        # Kodi Fullscreen Video
        self.window = xbmcgui.Window(12005) 
        self.window_w, self.window_h = WH
        
        # Vignette
        self.enableVignette = False
        self.defaultView = self.jsonRPC.getViewMode() if self.jsonRPC else 0
        self.vinView = self.defaultView
        self.vinImage = ''
        
        # Watermark
        self.enableChannelBug = SETTINGS.getSettingBool('Enable_ChannelBug')
        self.forceBugDiffuse = SETTINGS.getSettingBool('Force_Diffuse')
        
        hex_color = SETTINGS.getSetting('ChannelBug_Color') or 'FFFFFFFF'
        self.channelBugColor = f"0x{hex_color}"
        self.channelBugFade = SETTINGS.getSettingInt('ChannelBug_Transparency')
        
        try:    
            self.channelBugX, self.channelBugY = literal_eval(SETTINGS.getSetting("Channel_Bug_Position_XY"))
        except Exception: 
            self.channelBugX = abs(int(self.window_w // 9) - self.window_w) - 128
            self.channelBugY = abs(int(self.window_h // 16) - self.window_h) - 128

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def _hasControl(self, control):
        return control is not None and control in self.cntrlManager

    def _isVisible(self, control):
        return self.cntrlManager.get(control, False)

    def _setVisible(self, control, state: bool = False):
        if control is None:
            return False
        try:
            control.setVisible(state)
            return state
        except Exception as e: 
            self.log(f"_setVisible failed: {str(e)}", xbmc.LOGERROR)
            self._delControl(control)
            return False

    def _addControl(self, control):
        if control is None:
            return
        if not self._hasControl(control):
            try: 
                self.window.addControl(control)
                self.cntrlManager[control] = self._setVisible(control, True)
            except Exception as e: 
                self.log(f"_addControl failed: {str(e)}", xbmc.LOGERROR)
                self._delControl(control)
        
    def _delControl(self, control):
        if self._hasControl(control):
            try: 
                self.window.removeControl(control)
            except Exception as e: 
                self.log(f"_delControl context ejection failure: {str(e)}", xbmc.LOGERROR)
            self.cntrlManager.pop(control, None)  
            
    def open(self):
        if PROPERTIES.isRunning('Overlay'): return
        PROPERTIES.setRunning('Overlay', True)
        if not self.citem:
            self.close()
            return

        if self.runActions: self.runActions(RULES_ACTION_OVERLAY_OPEN, self.citem, inherited=self)
        self.log(f"open: enableVignette={self.enableVignette}, enableChannelBug={self.enableChannelBug}")
        
        if self.enableVignette:
            w_width, w_height = self.window.getWidth(), self.window.getHeight()
            self.vignette = xbmcgui.ControlImage(0, 0, w_width, w_height, ' ', aspectRatio=0)
            self._addControl(self.vignette)
            self.vignette.setImage(self.vinImage)
            
            if self.vinView != self.defaultView and self.jsonRPC: timerit(self.jsonRPC.setViewMode)(0.5, [self.vinView])
            self.vignette.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=240 delay=160 condition=True reversible=True')])
        
        if self.enableChannelBug:
            self.channelBug = xbmcgui.ControlImage(self.channelBugX, self.channelBugY, 128, 128, ' ', aspectRatio=2)
            self._addControl(self.channelBug)
            
            bug_id = 99105 
            try:
                self.channelBug.setId(bug_id)
            except Exception:
                bug_id = self.channelBug.getId()

            logo = self.citem.get('logo') or BUILTIN.getInfoLabel('Player.Art(icon)') or LOGO
            if self.forceBugDiffuse or (self.resources and self.resources.isMono(logo)): 
                self.channelBug.setColorDiffuse(self.channelBugColor)
                
            self.channelBug.setImage(logo)
            self.channelBug.setAnimations([
                ('Conditional', f'effect=fade start=0 end=100 time=2000 delay=1000 condition=Control.IsVisible({bug_id}) reversible=false'),
                ('Conditional', f'effect=fade start=100 end={self.channelBugFade} time=1000 delay=3000 condition=Control.IsVisible({bug_id}) reversible=false')
            ])
        
    def toggleOnNext(self, state: bool = None):
        if state is None:
            state = bool(SETTINGS.getSettingInt('OnNext_Mode'))
            
        if state and self.onnext is None and self.jsonRPC:
            next_item = self.jsonRPC.getNextItem(self.citem, self.nitem)
            self.onnext = OnNext(ONNEXT_XML, ADDON_PATH, "default", "1080i", 
                                 service=self.service, mode=self.player.OnNextMode, 
                                 position=self.player.onNextPosition, next=next_item)
        elif not state and self.onnext is not None:
            if hasattr(self.onnext, 'onClose'):
                self.onnext.onClose()
            self.onnext = None

    def close(self):
        self.log("close: Cleaning overlay layout objects.")
        self.toggleOnNext(False)
        
        if self.vignette:
            self._delControl(self.vignette)
            self.vignette = None
            
        if self.channelBug:
            self._delControl(self.channelBug)
            self.channelBug = None
            
        if self.vinView != self.defaultView and self.jsonRPC: 
            timerit(self.jsonRPC.setViewMode)(0.5, self.defaultView)
            
        PROPERTIES.setRunning('Overlay', False)
       
class OnNext(xbmcgui.WindowXMLDialog):
    closing = False
    totalTime = 0
    threshold = 0
    remaining = 0
    intTime = 0
    
    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop('service', None)
        self.nitem = kwargs.pop('next', {})
        self.onNextMode = kwargs.pop('mode', SETTINGS.getSettingInt('OnNext_Mode'))
        self.onNextPosition = kwargs.pop('position', SETTINGS.getSetting("OnNext_Position_XY"))
        
        super().__init__(*args, **kwargs)
        self.monitor = self.service.monitor if self.service else None
        self.player  = self.service.player if self.service else None
        self.jsonRPC = self.player.jsonRPC if self.player else None
        
        playing_item = self.player.playingItem if (self.player and hasattr(self.player, 'playingItem')) else {}
        self.citem = playing_item.get('citem', {})
        self.fitem = playing_item.get('fitem', {})
                
        self.window = xbmcgui.Window(12005) 
        self.window_w, self.window_h = WH 
                
        try:    
            self.onNextX, self.onNextY = literal_eval(self.onNextPosition)
        except Exception: 
            self.onNextX = abs(int(self.window_w // 9))
            self.onNextY = abs(int(self.window_h // 16) - self.window_h) - 356 
    
        self.log(f"__init__: enableOnNext={bool(self.onNextMode)}, mode={self.onNextMode}, X={self.onNextX}, Y={self.onNextY}")
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        return log(f"{self.__class__.__name__}: {msg}", level)

    def show_dialog(self):
        if not self.player or not self.nitem: return False
        try:
            self.totalTime = int(self.player.getPlayerTime() * (self.player.maxProgress / 100))
            self.threshold = abs((self.totalTime - (self.totalTime * .75)) - (ONNEXT_TIMER * 3))
            self.remaining = floor(self.totalTime - self.player.getPlayedTime())
            self.intTime = roundupDIV(self.threshold, 3)
        except Exception as e:
            self.log(f"show_dialog metrics parse failed: {str(e)}", xbmc.LOGERROR)
            return False

        self.log(f"show_dialog: totalTime={self.totalTime}, threshold={self.threshold}, remaining={self.remaining}, intTime={self.intTime}")
        
        if self.remaining >= self.intTime:
            self.doModal()
            return True
        return False
        
    def onInit(self):
        try:
            self.log(f"onInit: citem={self.citem}\nfitem={self.fitem}\nnitem={self.nitem}")
            self.service._que(self._run_async_notification_flow, 1, 0, 0)
        except Exception as e: 
            self.log(f"onInit critical error layout failed: {str(e)}", xbmc.LOGERROR)
            self.service._que(self.close, 1, 0, 0)
            
    def _run_async_notification_flow(self):
        try:
            if self.onNextMode in [1, 2]: 
                logo      = self.citem.get('logo') or BUILTIN.getInfoLabel('Player.Art(icon)') or LOGO
                chname    = self.citem.get('name') or BUILTIN.getInfoLabel('VideoPlayer.ChannelName')
                nowTitle  = self.fitem.get('label') or BUILTIN.getInfoLabel('VideoPlayer.Title')
                nextTitle = self.nitem.get('showlabel') or BUILTIN.getInfoLabel('VideoPlayer.NextTitle') or chname

                try: 
                    nextTime = epochTime(self.nitem['start']).strftime('%I:%M%p') 
                except Exception:
                    nextTime = BUILTIN.getInfoLabel('VideoPlayer.NextStartTime')

                if not nextTime: 
                    self.service._que(self.close, 1, 0, 0)
                    return

                onNow  = nowTitle if chname in validString(nowTitle) else f"{nowTitle} on {chname}"
                onNext = f"@ {nextTime}: {nextTitle}"
            
                container_control = self.getControl(40001)
                container_control.setPosition(self.onNextX, self.onNextY)
                container_control.setVisibleCondition('[Player.Playing + !Window.IsVisible(fullscreeninfo) + Window.IsVisible(fullscreenvideo)]')
                container_control.setAnimations([
                    ('WindowOpen' , f'effect=zoom start=80 end=100 center={self.onNextX},{self.onNextY} delay=160 tween=back time=240 reversible=false'),
                    ('WindowOpen' , 'effect=fade start=0 end=100 delay=160 time=240 reversible=false'),
                    ('WindowClose', f'effect=zoom start=100 end=80 center={self.onNextX},{self.onNextY} delay=160 tween=back time=240 reversible=false'),
                    ('WindowClose', 'effect=fade start=100 end=0 time=240 reversible=false'),
                    ('Visible'    , f'effect=zoom start=80 end=100 center={self.onNextX},{self.onNextY} delay=160 tween=back time=240 reversible=false'),
                    ('Visible'    , 'effect=fade end=100 time=240 reversible=false')
                ])
                
                self.onNext_Text = self.getControl(40003)
                self.onNext_Text.setVisible(False)
                self.onNext_Text.setText(f"{LANGUAGE(32104)} {onNow}[CR]{LANGUAGE(32116)} [B]{onNext}[B]")
                
                if self.onNextMode == 2:
                    self.onNext_Artwork = self.getControl(40004)
                    self.onNext_Artwork.setVisible(False)
                    self.onNext_Artwork.setImage(Globals._getThumb(self.nitem))

                    self.onNext_Text.setVisible(True)
                    self.onNext_Artwork.setVisible(True)
                    xbmc.playSFX(BING_WAV)
                    
                    show = ONNEXT_TIMER * 2
                    while not self.monitor.abortRequested() and not self.closing:
                        if self.service._shutdown(CPU_CYCLE) or not self.player.isPlayingPseudoTV() or show < 1: 
                            break
                        show -= CPU_CYCLE
                        self.service._sleep(int(CPU_CYCLE * 1000))
                        
                    self.onNext_Text.setVisible(False)
                    self.onNext_Artwork.setVisible(False)
                    
            elif self.onNextMode == 3: 
                self.player.toggleInfo()
            elif self.onNextMode == 4: 
                self._updateUpNext(self.fitem, self.nitem) 

            wait = self.intTime * 2
            while not self.monitor.abortRequested() and not self.closing:
                if self.service._shutdown(CPU_CYCLE) or not self.player.isPlayingPseudoTV() or wait < 1: 
                    break
                wait -= CPU_CYCLE
                self.service._sleep(int(CPU_CYCLE * 1000))
                
        except Exception as e:
            self.log(f"Asynchronous notification task loop crash failure: {str(e)}", xbmc.LOGERROR)
        finally:
            self.service._que(self.close, 1, 0, 0)

    def _updateUpNext(self, nowItem: dict = None, nextItem: dict = None):
        if nowItem is None: nowItem = {}
        if nextItem is None: nextItem = {}
        
        self.log('_updateUpNext')
        data = {}
        try:
            data["notification_offset"] = int(floor(self.player.getRemainingTime())) + OSD_TIMER
            
            def build_episode_map(item):
                return {
                    "episodeid" : item.get("id", ""),
                    "tvshowid"  : item.get("tvshowid", ""),
                    "title"     : item.get("title", ""),
                    "art"       : item.get("art", ""),
                    "season"    : item.get("season", ""),
                    "episode"   : item.get("episode", ""),
                    "showtitle" : item.get("tvshowtitle", ""),
                    "plot"      : item.get("plot", ""),
                    "playcount" : item.get("playcount", ""),
                    "rating"    : item.get("rating", ""),
                    "firstaired": item.get("firstaired", ""),
                    "runtime"   : item.get("runtime", "")
                }
                
            data["current_episode"] = build_episode_map(nowItem)
            data["next_episode"] = build_episode_map(nextItem)
            
            json_dump = FileAccess.dumpJSON(data).encode(DEFAULT_ENCODING)
            hex_payload = binascii.hexlify(json_dump).decode(DEFAULT_ENCODING)
            
            timerit(self.jsonRPC.notifyAll)(0.5, *('upnext_data', hex_payload, f"{ADDON_ID}.SIGNAL"))
        except Exception as e:
            self.log(f"_updateUpNext structural payload packaging failed: {str(e)}", xbmc.LOGERROR)

    def onAction(self, act):
        actionId = act.getId()
        self.log(f"onAction: actionId = {actionId}")
        self.closing = True

    def onClose(self):
        self.log('onClose: Tearing down overlay windows.')
        self.closing = True