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
from typing import Any, Optional
from variables import *
from resources import Resources


def _parse_position(value: str, fallback: tuple) -> tuple:
    """Parse a '(x, y)' string into a tuple, returning fallback on failure."""
    try:    return literal_eval(value)
    except: return fallback


def _on_next_position() -> tuple:
    """Default position for on-next notification (bottom-left)."""
    WH, _ = Globals.builtin.getResolution()
    w, h = WH
    return (abs(int(w // 9)), abs(int(h // 16) - h) - 356)


def _channel_bug_position() -> tuple:
    """Default position for channel bug (bottom-right)."""
    WH, _ = Globals.builtin.getResolution()
    w, h = WH
    return (abs(int(w // 9) - w) - 128, abs(int(h // 16) - h) - 128)


class Busy(xbmcgui.WindowXMLDialog):


    def __init__(self, *args: Any, **kwargs: Any):
        self.isLocked = kwargs.pop('isLocked', False)
        super().__init__(*args, **kwargs)
                
    def onInit(self):
        LOG(f"Busy: onInit, isLocked = {self.isLocked}")
        
        try:
            spinner = self.getControl(41)
            diffuse_color = "0xC0FF0000" if self.isLocked else "0xFF01416b"
            spinner.setColorDiffuse(diffuse_color)
        except Exception as e:
            LOG(f"Busy: onInit, failed!\n{str(e)}", xbmc.LOGERROR)


    def setStatus(self, text: str):
        try:
            label = self.getControl(40002)
            label.setLabel(text)
        except Exception:
            pass


    def onAction(self, act: xbmcgui.Action):
        actionId = act.getId()
        if actionId == 0 or not actionId: return
        LOG(f"Busy: onAction, actionId = {actionId}, isLocked = {self.isLocked}")
        if actionId in ACTION_PREVIOUS_MENU:
            if not self.isLocked:
                self.close()
            else:
                Globals.dialog.notificationDialog(LANGUAGE(32260))
                
class Background(xbmcgui.WindowXMLDialog):


    def __init__(self, *args: Any, **kwargs: Any):
        self.service = kwargs.pop('service', None)
        super().__init__(*args, **kwargs)
        
        self.player  = self.service.player if self.service else None
        playing_item = self.player.playingItem if (self.player and hasattr(self.player, 'playingItem')) else {}
        
        self.citem = playing_item.get('citem', {})
        self.fitem = playing_item.get('fitem', {})
        self.nitem = playing_item.get('nitem', {})
        self.videoWindow = None
      
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"Background: {msg}", level)


    def onInit(self):
        try:
            self.log(f"onInit: citem={self.citem}\nfitem={self.fitem}\nnitem={self.nitem}")
            WH, WIN   = Globals.builtin.getResolution()
            logo      = self.citem.get('logo') or Globals.builtin.getInfoLabel('Player.Art(icon)') or LOGO
            chname    = self.citem.get('name') or Globals.builtin.getInfoLabel('VideoPlayer.ChannelName')
            nowTitle  = self.fitem.get('label') or Globals.builtin.getInfoLabel('VideoPlayer.Title')
            nextTitle = self.nitem.get('showlabel') or Globals.builtin.getInfoLabel('VideoPlayer.NextTitle') or chname
            onNextX, onNextY = _on_next_position()

            nextTime = ""
            start_val = self.nitem.get('start')
            if start_val:
                try:              nextTime = Globals._epochTime(start_val).strftime('%I:%M%p')
                except Exception: 
                    self.log(f'onInit, failed to format nextTime from {start_val}', xbmc.LOGDEBUG)
                    nextTime = ""
                    
            if not nextTime: nextTime = Globals.builtin.getInfoLabel('VideoPlayer.NextStartTime')
            if not nextTime:
                self.log("onInit: Time markers missing. Aborting overlay instantiation.", xbmc.LOGDEBUG)
                self.close()
                return
                
            onNow  = nowTitle if chname in Globals._validString(nowTitle) else f"{nowTitle} on {chname}"
            onNext = f"@ {nextTime}: {nextTitle}"
            
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
            
            try:
                self.videoWindow = self.getControl(41000)
                self._shrinkVideo()
            except Exception as e:
                self.log(f"onInit videowindow: {e}", xbmc.LOGDEBUG)
        except Exception as e:
            self.log(f"onInit execution failed: {str(e)}", xbmc.LOGERROR)
            self.close()


    def _shrinkVideo(self):
        if self.videoWindow is None: return
        try:
            WH, _ = Globals.builtin.getResolution()
            winW, winH = WH
            targetX, targetY = _on_next_position()
            targetW, targetH = 960, 380
            
            startX, startY = 0, 0
            startW, startH = winW, winH
            steps = 20
            for i in range(1, steps + 1):
                t = i / steps
                x = int(startX + (targetX - startX) * t)
                y = int(startY + (targetY - startY) * t)
                w = int(startW + (targetW - startW) * t)
                h = int(startH + (targetH - startH) * t)
                self.videoWindow.setPosition(x, y)
                self.videoWindow.setWidth(w)
                self.videoWindow.setHeight(h)
                xbmc.Monitor().waitForAbort(0.015)
        except Exception as e:
            self.log(f"_shrinkVideo: {e}", xbmc.LOGDEBUG)


    def _expandVideo(self):
        if self.videoWindow is None: return
        try:
            WH, _ = Globals.builtin.getResolution()
            winW, winH = WH
            startX, startY = _on_next_position()
            startW, startH = 960, 380
            
            steps = 20
            for i in range(1, steps + 1):
                t = i / steps
                x = int(startX + (0 - startX) * t)
                y = int(startY + (0 - startY) * t)
                w = int(startW + (winW - startW) * t)
                h = int(startH + (winH - startH) * t)
                self.videoWindow.setPosition(x, y)
                self.videoWindow.setWidth(w)
                self.videoWindow.setHeight(h)
                xbmc.Monitor().waitForAbort(0.015)
        except Exception as e:
            self.log(f"_expandVideo: {e}", xbmc.LOGDEBUG)

class Replay(xbmcgui.WindowXMLDialog):
    closing = False
    
    def __init__(self, *args: Any, **kwargs: Any):
        self.service = kwargs.pop('service', None)
        super().__init__(*args, **kwargs)
        
        self.monitor = self.service.monitor if self.service else None
        self.player  = self.service.player if self.service else None
        
        playing_item = self.player.playingItem if (self.player and hasattr(self.player, 'playingItem')) else {}
        self.citem   = playing_item.get('citem', {})
        self.fitem   = playing_item.get('fitem', {})
        
    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"Replay: {msg}", level)
        
    def show_dialog(self) -> bool:
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
        
    def _isVisible(self, control: xbmcgui.Control) -> bool:
        try:              
            return control.isVisible()
        except Exception: 
            is_playing    = Globals.builtin.getInfoBool('Player.Playing')
            info_visible  = Globals.builtin.getInfoBool('Window.IsVisible(fullscreeninfo)')
            video_visible = Globals.builtin.getInfoBool('Window.IsVisible(fullscreenvideo)')
            return (is_playing and not info_visible) or video_visible
        
    def onInit(self):
        self.log("onInit: Initializing dialog components.")
        try:
            control = self.getControl(40000)
            control.setVisibleCondition('[Player.Playing + !Window.IsVisible(fullscreeninfo) + Window.IsVisible(fullscreenvideo)]')
            self._run(control)
        except Exception as e: 
            self.log(f"onInit failed: {str(e)}", xbmc.LOGERROR)
            self.close()


    def _run(self, control: xbmcgui.Control):
        try:
            wait = OSD_TIMER * 2
            tot  = wait
            xpos = control.getX()
            
            while not self.monitor.abortRequested():
                if self.service._shutdown(CPU_CYCLE) or self._isVisible(control) or self.closing: 
                    break
                self.service.sleep(int(CPU_CYCLE * 1000))
                    
            while not self.monitor.abortRequested():
                if self.service._shutdown(CPU_CYCLE) or wait < 0 or self.closing or not self.player.isPlayingPseudoTV(): 
                    break
                
                prog = int((abs(wait - tot) * 100) // tot)
                if prog > 0: 
                    control.setAnimations([('Conditional', f'effect=zoom start={prog-20},100 end={prog},100 time=1000 center={xpos},100 tween="out" condition=True')])
                
                wait -= CPU_CYCLE
                self.service.sleep(int(CPU_CYCLE * 1000))
            
            control.setAnimations([('Conditional', f'effect=fade start={prog if "prog" in locals() else 100} end=0 time=240 delay=0.240 condition=True')])
            control.setVisible(False)
            self.setFocusId(40001)
        except Exception as e:
            self.log(f"_run crashed: {str(e)}", xbmc.LOGERROR)
        finally:
            self.close()


    def onAction(self, act: xbmcgui.Action):
        actionId = act.getId()
        self.log(f"onAction: actionId = {actionId}")
        self.closing = True
        if   actionId == ACTION_MOVE_UP:       Globals.builtin.executebuiltin('AlarmClock(up,Action(up),.5,true,false)')
        elif actionId == ACTION_MOVE_DOWN:     Globals.builtin.executebuiltin('AlarmClock(down,Action(down),.5,true,false)')
        elif actionId in ACTION_PREVIOUS_MENU: Globals.builtin.executebuiltin('AlarmClock(back,Action(back),.5,true,false)')
        elif actionId in ACTION_SELECT_ITEM and self.getFocusId() == 40001: 
            if self.player.playingItem.get('isPlaylist', False): self.player.seekTime(0)
            elif self.fitem: 
                with Globals.builtin.busy_dialog():
                    liz = Globals.listitems.buildItemListItem(self.fitem)
                    liz.setProperty('sysInfo', FileAccess._encodeString(self.player.playingItem))
                    timerit(self.player.play)(0.5, *(self.fitem.get('catchup-id'), liz))
                    self.player.stop()
            else: 
                Globals.dialog.notificationDialog(LANGUAGE(30154))


    def onClose(self):
        self.log("onClose")
        self.closing = True


class Overlay(xbmcgui.WindowXMLDialog):
    """Unified fullscreen overlay: vignette + channel bug + on-next notification.
    
    Replaces old Overlay (plain class) + OnNext (separate WindowXMLDialog).
    All controls defined in XML; Python sets data and toggles visibility.
    Kodi animations handle fade/zoom natively.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        self.service = kwargs.pop('service', None)
        super().__init__(*args, **kwargs)
        
        self.monitor = self.service.monitor if self.service else None
        self.player  = self.service.player if self.service else None
        self.jsonRPC = self.player.jsonRPC if self.player else None
        self.runActions = self.player.runActions if self.player else None
        self.resources = Resources(self.service) if self.service else None
        
        playing_item = self.player.playingItem if (self.player and hasattr(self.player, 'playingItem')) else {}
        self.citem   = playing_item.get('citem', {})
        self.fitem   = playing_item.get('fitem', {})
        self.nitem   = playing_item.get('nitem', {})
        
        self._vignette_visible = False
        self._bug_visible      = False
        self._onnext_visible   = False
        self._onnext_sending   = False
        self._closing          = False
        
        # Vignette
        self.enableVignette = False
        self.defaultView = self.jsonRPC.getViewMode() if self.jsonRPC else 0
        self.vinView = self.defaultView
        self.vinImage = ''
        
        # Channel bug
        self.enableChannelBug = Globals.settings.getSettingBool('Enable_ChannelBug')
        self.forceBugDiffuse  = Globals.settings.getSettingBool('Force_Diffuse')
        self.channelBugColor  = f"0x{Globals.settings.getSetting('ChannelBug_Color') or 'FFFFFFFF'}"
        self.channelBugFade   = Globals.settings.getSettingInt('ChannelBug_Transparency')
        self.channelBugX, self.channelBugY = _parse_position(
            Globals.settings.getSetting("Channel_Bug_Position_XY"), _channel_bug_position())


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"Overlay: {msg}", level)


    def onInit(self):
        self.log("onInit")
        self._setupVignette()
        self._setupChannelBug()


    def _setupVignette(self):
        if not self.enableVignette: return
        try:
            control = self.getControl(40000)
            control.setImage(self.vinImage)
            control.setAnimations([('Conditional', 'effect=fade start=0 end=100 time=240 delay=160 condition=True reversible=True')])
            if self.vinView != self.defaultView and self.jsonRPC:
                timerit(self.jsonRPC.setViewMode)(0.5, [self.vinView])
            self._vignette_visible = True
        except Exception as e:
            self.log(f"_setupVignette: {e}", xbmc.LOGERROR)


    def _setupChannelBug(self):
        if not self.enableChannelBug: return
        try:
            control = self.getControl(40005)
            logo = self.citem.get('logo') or Globals.builtin.getInfoLabel('Player.Art(icon)') or LOGO
            if   self.forceBugDiffuse:        control.setColorDiffuse(self.channelBugColor)
            elif self.resources and self.resources.isMono(logo): control.setColorDiffuse(self.channelBugColor)
            control.setImage(logo)
            control.setPosition(self.channelBugX, self.channelBugY)
            cid = control.getId()
            control.setAnimations([('Conditional', f'effect=fade start=0 end=100 time=2000 delay=1000 condition=Control.IsVisible({cid}) reversible=false'),
                                   ('Conditional', f'effect=fade start=100 end={self.channelBugFade} time=1000 delay=3000 condition=Control.IsVisible({cid}) reversible=false'),
                                   ('Visible', f'effect=fade start={self.channelBugFade} end=100 time=2000 delay=5000 loop=true condition=Control.IsVisible({cid}) reversible=false'),
                                   ('Visible', f'effect=fade start=100 end={self.channelBugFade} time=2000 delay=7000 loop=true condition=Control.IsVisible({cid}) reversible=false')])
            self._bug_visible = True
        except Exception as e:
            self.log(f"_setupChannelBug: {e}", xbmc.LOGERROR)


    def open(self):
        if Globals.properties.isRunning('Overlay'): return
        Globals.properties.setRunning('Overlay', True)
        if not self.citem: return self.close()
        if self.runActions: self.runActions(RULES_ACTION_OVERLAY_OPEN, self.citem, inherited=self)
        self.log(f"open: vignette={self.enableVignette}, bug={self.enableChannelBug}")
        self.show()


    def updatePlayingItem(self, playing_item: Optional[dict] = None):
        """Refresh overlay data when playback advances to a new program/channel.

        The overlay caches citem/fitem/nitem at construction; without this the
        channel bug logo and on-next row go stale after the playlist moves on.
        Re-applies the channel bug and, if the on-next row is visible, repopulates it.
        """
        if playing_item is None and self.player:
            playing_item = getattr(self.player, 'playingItem', {})
        if not playing_item: return
        self.citem = playing_item.get('citem', {})
        self.fitem = playing_item.get('fitem', {})
        self.nitem = playing_item.get('nitem', {})
        self._setupChannelBug()
        if self._onnext_visible:
            self._populateOnNext()


    def toggleVignette(self, state: bool):
        if state == self._vignette_visible: return
        try:
            self.getControl(40000).setVisible(state)
            self._vignette_visible = state
        except Exception: pass


    def toggleChannelBug(self, state: bool):
        if state == self._bug_visible: return
        try:
            self.getControl(40005).setVisible(state)
            self._bug_visible = state
        except Exception: pass


    def showOnNext(self, mode: Optional[int] = None):
        """Show on-next notification. Mode: 1=text, 2=text+thumb+sfx, 3=toggleInfo, 4=UpNext signal."""
        if mode is None: mode = Globals.settings.getSettingInt('OnNext_Mode')
        if mode == 0 or self._onnext_visible: return

        if mode == 3:
            self.player.toggleInfo()
            return

        if mode == 4:
            self._sendUpNextSignal()
            return

        # Modes 1, 2: populate controls
        if not self._populateOnNext():
            # overlay window not ready (closing / not yet open) — skip
            # so we don't set _onnext_visible and trip hideOnNext on dead controls.
            return

        if mode == 2:
            try: xbmc.playSFX(BING_WAV)
            except: pass
            # Auto-hide after ONNEXT_TIMER
            timerit(self.hideOnNext)(float(ONNEXT_TIMER))

        self._onnext_visible = True


    def _populateOnNext(self) -> bool:
        """Fill on-next text/thumbnail controls from current playing item.

        Returns True on success; False if the overlay window's controls are not
        available (e.g. the window is closing or not yet open) — caller should
        then skip the on-next display.
        """
        try:
            chname    = self.citem.get('name') or Globals.builtin.getInfoLabel('VideoPlayer.ChannelName')
            nowTitle  = self.fitem.get('label') or Globals.builtin.getInfoLabel('VideoPlayer.Title')
            nextTitle = self.nitem.get('showlabel') or Globals.builtin.getInfoLabel('VideoPlayer.NextTitle') or chname
            onNextX, onNextY = _parse_position(
                Globals.settings.getSetting("OnNext_Position_XY"), _on_next_position())

            try:    nextTime = Globals._epochTime(self.nitem['start']).strftime('%I:%M%p')
            except: nextTime = Globals.builtin.getInfoLabel('VideoPlayer.NextStartTime')

            if not nextTime: return
            onNow  = nowTitle if chname in Globals._validString(nowTitle) else f"{nowTitle} on {chname}"
            onNext = f"@ {nextTime}: {nextTitle}"

            container = self.getControl(40001)
            container.setPosition(onNextX, onNextY)
            container.setAnimations([
                ('Visible', f'effect=slide start=100,0 end=0,0 center={onNextX},{onNextY} time=300 tween="back" reversible=false'),
                ('Hidden',  f'effect=slide start=0,0 end=100,0 center={onNextX},{onNextY} time=200 reversible=false'),
            ])
            self.getControl(40003).setText(f"{LANGUAGE(32104)} {onNow}[CR]{LANGUAGE(32116)} [B]{onNext}[B]")

            has_thumb = False
            thumb_art = Globals._getThumb(self.nitem)
            if thumb_art:
                self.getControl(40004).setImage(thumb_art)
                has_thumb = True

            # Staggered fade: thumbnail first, text 200ms later
            self.getControl(40001).setVisible(True)
            self.getControl(40004).setAnimations([('Visible', 'effect=fade start=0 end=100 time=200 delay=0 reversible=false')])
            self.getControl(40004).setVisible(has_thumb)
            self.getControl(40003).setAnimations([('Visible', 'effect=fade start=0 end=100 time=200 delay=200 reversible=false')])
            self.getControl(40003).setVisible(True)
            return True
        except Exception as e:
            # transient UI race — window closing or controls not loaded yet.
            self._onnext_visible = False
            self.log(f"_populateOnNext: {e}", xbmc.LOGDEBUG)
            return False


    def hideOnNext(self):
        if not self._onnext_visible: return
        try:
            self.getControl(40001).setVisible(False)
            self.getControl(40003).setVisible(False)
            self.getControl(40004).setVisible(False)
            self._onnext_visible = False
        except Exception: pass


    def _sendUpNextSignal(self):
        """Send UpNext signal for external UpNext addon compatibility."""
        if self._onnext_sending: return
        self._onnext_sending = True
        try:
            data: dict = {}
            data["notification_offset"] = int(floor(self.player.getRemainingTime())) + OSD_TIMER
            def _map(item: dict) -> dict:
                return {k: item.get(k, "") for k in ["episodeid","tvshowid","title","art","season","episode","showtitle","plot","playcount","rating","firstaired","runtime"]}
            data["current_episode"] = _map(self.fitem)
            data["next_episode"]    = _map(self.nitem)
            hex_payload = binascii.hexlify(FileAccess.dumpJSON(data).encode(DEFAULT_ENCODING)).decode(DEFAULT_ENCODING)
            self.jsonRPC.notifyAll('upnext_data', hex_payload, f"{ADDON_ID}.SIGNAL")
        except Exception as e:
            self.log(f"_sendUpNextSignal: {e}", xbmc.LOGERROR)
        finally:
            self._onnext_sending = False


    def close(self):
        self.log("close")
        self._closing = True
        self.hideOnNext()
        if self.vinView != self.defaultView and self.jsonRPC:
            timerit(self.jsonRPC.setViewMode)(0.5, self.defaultView)
        Globals.properties.setRunning('Overlay', False)


    def onAction(self, act: xbmcgui.Action):
        self._closing = True


    def onClose(self):
        self.log("onClose")
        self._closing = True
        Globals.properties.setRunning('Overlay', False)
