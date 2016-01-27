#   Copyright (C) 2015 Kevin S. Graer
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

import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import subprocess, os, sys, re
import time, threading, datetime, _strptime, traceback
import urllib, urllib2

from Playlist import Playlist
from Globals import *
from Channel import Channel
from ChannelList import ChannelList
from FileAccess import FileAccess
from xml.etree import ElementTree as ET
from utils import *

try:
    import buggalo
    buggalo.SUBMIT_URL = 'http://pseudotvlive.com/buggalo-web/submit.php'
except:
    pass
      
class EPGWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log('__init__')
        self.channelLabel = []    
        self.channelLogos = ''
        self.textcolor = "FFFFFFFF"
        self.focusedcolor = "FF7d7d7d"
        self.shadowcolor = "FF000000"
        self.textfont  = "font14"
        self.infoOffsetV = 0
        self.clockMode = 0
        self.inputChannel = -1
        self.focusRow = 0
        self.focusIndex = 0
        self.focusTime = 0
        self.focusEndTime = 0
        self.shownTime = 0
        self.infoOffset = 0
        self.centerChannel = 0
        self.showingInfo = False
        self.showingContext = False
        self.chanlist = ChannelList()
        self.lastActionTime = time.time()
        self.actionSemaphore = threading.BoundedSemaphore()
        self.channelbugcolor = CHANBUG_COLOR
        self.timeButtonNoFocus = MEDIA_LOC + TIME_BUTTON
        self.timeButtonBar = MEDIA_LOC + TIME_BAR
        
        try:
            self.rowCount = int(getProperty("EPG.rowCount"))
        except:
            self.rowCount = 6
        self.channelButtons = [None] * self.rowCount
        self.channelTags = [None] * self.rowCount
        
        for i in range(self.rowCount):
            self.channelButtons[i] = []
            self.channelTags[i] = []
            
        self.clockMode = ADDON_SETTINGS.getSetting("ClockMode")
        self.showSeasonEpisode = REAL_SETTINGS.getSetting("ShowSeEp") == "true"
        self.toRemove = []

                    
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('EPGWindow: ' + msg, level)


    def onFocus(self, controlid):
        pass


    # set the time labels
    def setTimeLabels(self, thetime):
        now = datetime.datetime.fromtimestamp(thetime)
        self.getControl(5001).setLabel(now.strftime('%A, %B %d'))
        delta = datetime.timedelta(minutes=30)

        for i in range(3):
            if self.clockMode == "0":
                self.getControl(101 + i).setLabel(now.strftime("%I:%M%p").lower())
            else:
                self.getControl(101 + i).setLabel(now.strftime("%H:%M"))
            now = now + delta
        self.log('setTimeLabels return')

        
    def onInit(self):
        self.log('onInit')
        now = datetime.datetime.now()     
        
        if self.clockMode == "0":
            timeex = now.strftime("%I:%M%p").lower()
        else:
            timeex = now.strftime("%H:%M")
        
        timetx, timety = self.getControl(5006).getPosition()
        timetw = self.getControl(5006).getWidth()
        timeth = self.getControl(5006).getHeight()
        timex, timey = self.getControl(5007).getPosition()
        timew = self.getControl(5007).getWidth()
        timeh = self.getControl(5007).getHeight()

        self.ButtonContextGauss = MEDIA_LOC + BUTTON_GAUSS_CONTEXT
        self.ButtonContextFocus = MEDIA_LOC + BUTTON_FOCUS_ALT
        self.ButtonContextNoFocus = MEDIA_LOC + BUTTON_NO_FOCUS_ALT
        self.ButtonContextBackground = MEDIA_LOC + BUTTON_BACKGROUND_CONTEXT
        self.textureButtonFocus = MEDIA_LOC + BUTTON_FOCUS
        self.textureButtonNoFocus = MEDIA_LOC + BUTTON_NO_FOCUS
        self.textureButtonFocusAlt = MEDIA_LOC + BUTTON_FOCUS_ALT
        self.textureButtonNoFocusAlt = MEDIA_LOC + BUTTON_NO_FOCUS_ALT
        
        self.currentTime = xbmcgui.ControlButton(timetx, timety, timetw, timeth, timeex, font='font12', noFocusTexture=self.timeButtonNoFocus)
        self.currentTimeBar = xbmcgui.ControlImage(timex, timey, timew, timeh, self.timeButtonBar) 
        self.addControl(self.currentTime)
        self.addControl(self.currentTimeBar)
        self.curchannelIndex = []

        setProperty("PTVL.VideoWindow","true")
        textcolor = int(getProperty("EPG.textColor"), 16)            
        if textcolor > 0:
            self.textcolor = hex(textcolor)[2:]
        
        focusedcolor = int(getProperty("EPG.focused_textColor"), 16)
        if focusedcolor > 0:
            self.focusedcolor = hex(focusedcolor)[2:]
            
        shadowcolor = int(getProperty("EPG.shadowColor"), 16)
        if shadowcolor > 0:
            self.shadowColor = hex(shadowcolor)[2:]
        
        self.textfont = getProperty("EPG.textFont")

        try:
            if self.setChannelButtons(time.time(), self.MyOverlayWindow.currentChannel) == False:
                self.log('Unable to add channel buttons')
                return

            curtime = time.time()
            self.focusIndex = -1
            basex, basey = self.getControl(113).getPosition()
            baseh = self.getControl(113).getHeight()
            basew = self.getControl(113).getWidth()

            # set the button that corresponds to the currently playing show
            for i in range(len(self.channelButtons[2])):
                left, top = self.channelButtons[2][i].getPosition()
                width = self.channelButtons[2][i].getWidth()
                left = left - basex
                starttime = self.shownTime + (left / (basew / 5400.0))
                endtime = starttime + (width / (basew / 5400.0))

                if curtime >= starttime and curtime <= endtime:
                    self.focusIndex = i
                    self.setFocus(self.channelButtons[2][i])
                    self.focusTime = int(time.time())
                    self.focusEndTime = endtime
                    break

            # If nothing was highlighted, just select the first button
            if self.focusIndex == -1:
                self.focusIndex = 0
                self.setFocus(self.channelButtons[2][0])
                left, top = self.channelButtons[2][0].getPosition()
                width = self.channelButtons[2][0].getWidth()
                left = left - basex
                starttime = self.shownTime + (left / (basew / 5400.0))
                endtime = starttime + (width / (basew / 5400.0))
                self.focusTime = int(starttime + 30)
                self.focusEndTime = endtime
            self.focusRow = 2
            self.setShowInfo()
        except Exception,e:
            self.log("Unknown EPG Initialization exception " + str(e), xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)          
            self.close()
            self.MyOverlayWindow.sleepTimeValue = 1
            self.MyOverlayWindow.startSleepTimer()
            return

        for i in range(3):
            try:
                self.channelLabel.append(xbmcgui.ControlImage(50 + (50 * i), 50, 50, 50, IMAGES_LOC + 'solid.png', colorDiffuse = self.channelbugcolor))
                self.addControl(self.channelLabel[i])
                self.channelLabel[i].setVisible(False)
            except:
                pass
        self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)        
        self.FEEDtoggle()
        self.log('onInit return')


    def FEEDtoggle(self):   
        self.log('FEEDtoggle')
        try:
            if getProperty("PTVL.FEEDtoggle") == "true":
                self.getControl(105).setVisible(True)
            else:
                self.getControl(105).setVisible(False)
        except:
            pass

        
    # setup all channel buttons for a given time
    def setChannelButtons(self, starttime, curchannel, singlerow = -1):
        self.log('setChannelButtons ' + str(starttime) + ', ' + str(curchannel))
        self.centerChannel = self.MyOverlayWindow.fixChannel(curchannel)
        
        # This is done twice to guarantee we go back 2 channels.  If the previous 2 channels
        # aren't valid, then doing a fix on curchannel - 2 may result in going back only
        # a single valid channel.
        curchannel = self.MyOverlayWindow.fixChannel(curchannel - 1, False)
        curchannel = self.MyOverlayWindow.fixChannel(curchannel - 1, False)
        
        starttime = self.roundToHalfHour(int(starttime))
        self.setTimeLabels(starttime)
        self.shownTime = starttime
        
        basex, basey = self.getControl(111).getPosition()
        basew = self.getControl(111).getWidth()
        tmpx, tmpy =  self.getControl(110 + self.rowCount).getPosition()
        
        timetx, timety = self.getControl(5006).getPosition()
        timetw = self.getControl(5006).getWidth()
        timeth = self.getControl(5006).getHeight()
        timex, timey = self.getControl(5007).getPosition()
        timew = self.getControl(5007).getWidth()
        timeh = self.getControl(5007).getHeight()
        
        basecur = curchannel
        self.toRemove.append(self.currentTime)
        self.toRemove.append(self.currentTimeBar)
        myadds = []
                    
        for i in range(self.rowCount):
            if singlerow == -1 or singlerow == i:
                self.setButtons(starttime, basecur, i)
                myadds.extend(self.channelButtons[i])
                myadds.extend(self.channelTags[i])
            basecur = self.MyOverlayWindow.fixChannel(basecur + 1)
        basecur = curchannel

        for i in range(self.rowCount):
            self.getControl(301 + i).setLabel(self.MyOverlayWindow.getChname(basecur))
            basecur = self.MyOverlayWindow.fixChannel(basecur + 1)

        for i in range(self.rowCount): 
            self.getControl(311 + i).setLabel(str(curchannel))
            if REAL_SETTINGS.getSetting("EPGTextEnable") == "0":   
                chlogo = self.MyOverlayWindow.getChlogo(curchannel, False)
                self.getControl(321 + i).setImage(chlogo)
                if not FileAccess.exists(chlogo) and REAL_SETTINGS.getSetting('Enable_FindLogo') == "true":
                    chtype = self.MyOverlayWindow.getChtype(curchannel)
                    if chtype in [6,7]:
                        plpos = self.determinePlaylistPosAtTime(starttime, (curchannel - 1))
                        mediapath = ascii(self.MyOverlayWindow.channels[curchannel - 1].getItemFilename(plpos))
                        FindLogo(chtype, self.MyOverlayWindow.getChname(curchannel), mediapath)
            else:
                self.getControl(321 + i).setImage('NA.png')
            curchannel = self.MyOverlayWindow.fixChannel(curchannel + 1)
   
        if time.time() >= starttime and time.time() < starttime + 5400:
            dif = int((starttime + 5400 - time.time())) 
            self.currentTime.setPosition(int((basex + basew - 2) - (dif * (basew / 5400.0))), timety)
            self.currentTimeBar.setPosition(int((basex + basew - 2) - (dif * (basew / 5400.0))), timey)
        else:
            if time.time() < starttime:
                self.currentTime.setPosition(-1800, timety)
                self.currentTimeBar.setPosition(basex + 2, timey)
            else:
                self.currentTime.setPosition(-1800, timety)
                self.currentTimeBar.setPosition(basex + basew - 2 - timew, timey)

        myadds.append(self.currentTime)
        myadds.append(self.currentTimeBar)
        
        # Update timebutton
        now = datetime.datetime.now()        
        if self.clockMode == "0":
            timeex = now.strftime("%I:%M%p").lower()
        else:
            timeex = now.strftime("%H:%M")
        self.currentTime.setLabel(timeex)
        
        # Set backtime focus width
        TimeBX, TimeBY = self.currentTimeBar.getPosition()
        PFadeX, PFadeY = self.getControl(5004).getPosition()
        self.getControl(5004).setWidth(TimeBX-PFadeX)
        self.getControl(5005).setPosition(TimeBX, PFadeY)
        self.getControl(5005).setWidth(1920-TimeBX)

        Time1X, Time1Y = self.getControl(101).getPosition()
        Time2X, Time2Y = self.getControl(102).getPosition()
        Time3X, Time3Y = self.getControl(103).getPosition()
        TimeBW = int(self.currentTime.getWidth())
        Time1W = int(self.getControl(101).getWidth())
        Time2W = int(self.getControl(102).getWidth())
        Time3W = int(self.getControl(103).getWidth())
        
        # Arrow color
        if TimeBX > Time3X:
            self.getControl(5002).setColorDiffuse('0x'+self.focusedcolor)
        else:
            self.getControl(5002).setColorDiffuse('0x'+self.textcolor)
        if TimeBX < Time1X:
            self.getControl(5003).setColorDiffuse('0x'+self.focusedcolor)
        else:
            self.getControl(5003).setColorDiffuse('0x'+self.textcolor)
         
        # Hide timebutton when near timebar
        self.getControl(101).setVisible(True)
        if TimeBX < Time1X or TimeBX > Time1X + Time1W:
            self.getControl(101).setVisible(True)
        else:
            self.getControl(101).setVisible(False)
            
        self.getControl(102).setVisible(True)
        if TimeBX + TimeBW < Time2X or TimeBX > Time2X + Time2W:
            self.getControl(102).setVisible(True)
        else:
            self.getControl(102).setVisible(False)
            
        self.getControl(103).setVisible(True)            
        if TimeBX + TimeBW < Time3X or TimeBX > Time3X + Time3W:
            self.getControl(103).setVisible(True)
        else:
            self.getControl(103).setVisible(False)
            
        try:
            self.removeControls(self.toRemove)
        except:
            for cntrl in self.toRemove:
                try:
                    self.removeControl(cntrl)
                except:
                    pass
        try:
            self.addControls(myadds)
            self.toRemove = []
            self.log('setChannelButtons return')
        except:
            xbmc.log('self.addControls(myadds) in use')
            pass
            
        
    # round the given time down to the nearest half hour
    def roundToHalfHour(self, thetime):
        n = datetime.datetime.fromtimestamp(thetime)
        delta = datetime.timedelta(minutes=30)
        if n.minute > 29:
            n = n.replace(minute=30, second=0, microsecond=0)
        else:
            n = n.replace(minute=0, second=0, microsecond=0)
        return time.mktime(n.timetuple())

        
    def getEPGtype(self, genre):
        if genre in COLOR_RED_TYPE:
            return (EPGGENRE_LOC + 'COLOR_RED.png')
        elif genre in COLOR_GREEN_TYPE:
            return (EPGGENRE_LOC + 'COLOR_GREEN.png')
        elif genre in COLOR_mdGREEN_TYPE:
            return (EPGGENRE_LOC + 'COLOR_mdGREEN.png')
        elif genre in COLOR_BLUE_TYPE:
            return (EPGGENRE_LOC + 'COLOR_BLUE.png')
        elif genre in COLOR_ltBLUE_TYPE:
            return (EPGGENRE_LOC + 'COLOR_ltBLUE.png')
        elif genre in COLOR_CYAN_TYPE:
            return (EPGGENRE_LOC + 'COLOR_CYAN.png')
        elif genre in COLOR_ltCYAN_TYPE:
            return (EPGGENRE_LOC + 'COLOR_ltCYAN.png')
        elif genre in COLOR_PURPLE_TYPE:
            return (EPGGENRE_LOC + 'COLOR_PURPLE.png')
        elif genre in COLOR_ltPURPLE_TYPE:
            return (EPGGENRE_LOC + 'COLOR_ltPURPLE.png')
        elif genre in COLOR_ORANGE_TYPE:
            return (EPGGENRE_LOC + 'COLOR_ORANGE.png')
        elif genre in COLOR_YELLOW_TYPE:
            return (EPGGENRE_LOC + 'COLOR_YELLOW.png')
        elif genre in COLOR_GRAY_TYPE:
            return (EPGGENRE_LOC + 'COLOR_GRAY.png')
        else:#Unknown or COLOR_ltGRAY_TYPE
            return (EPGGENRE_LOC + 'COLOR_ltGRAY.png') 
        

    # create the buttons for the specified channel in the given row
    def setButtons(self, starttime, curchannel, row):
        try:
            curchannel = self.MyOverlayWindow.fixChannel(curchannel)
            basex, basey = self.getControl(111 + row).getPosition()
            baseh = self.getControl(111 + row).getHeight()
            basew = self.getControl(111 + row).getWidth()
            chtype = self.MyOverlayWindow.getChtype(curchannel)      
            chname = self.MyOverlayWindow.getChname(curchannel)
            
            if xbmc.Player().isPlaying() == False:
                self.log('setButtons, No video is playing, not adding buttons')
                self.closeEPG()
                return False

            # Backup all of the buttons to an array
            self.toRemove.extend(self.channelButtons[row])
            self.toRemove.extend(self.channelTags[row])
            del self.channelButtons[row][:]
            del self.channelTags[row][:]

            playlistpos = int(xbmc.PlayList(xbmc.PLAYLIST_VIDEO).getposition())
            # playlistpos = int(xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition())
            
            # if the channel is paused, then only 1 button needed
            if self.MyOverlayWindow.channels[curchannel - 1].isPaused:
                self.channelButtons[row].append(xbmcgui.ControlButton(basex, basey, basew, baseh, self.MyOverlayWindow.channels[curchannel - 1].getCurrentTitle() + " (paused)", focusTexture=self.textureButtonFocus, noFocusTexture=self.textureButtonNoFocus, alignment=4, shadowColor=self.shadowColor, textColor=self.textcolor, focusedColor=self.focusedcolor))
            
            # if hideShortItems and chtype >=10 stack videos shorter than BYPASS_EPG_SECONDS. 
            # if the channel is stacked, then only 1 button needed
            elif self.MyOverlayWindow.hideShortItems and (chtype >= 10 and self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos) < BYPASS_EPG_SECONDS and chname not in BYPASS_EPG_STACK) or chname in FORCE_EPG_STACK: #Under 15mins "Stacked"
                self.channelButtons[row].append(xbmcgui.ControlButton(basex, basey, basew, baseh, self.MyOverlayWindow.getChname(curchannel), focusTexture=self.textureButtonFocus, noFocusTexture=self.textureButtonNoFocus, alignment=4, shadowColor=self.shadowColor, textColor=self.textcolor, focusedColor=self.focusedcolor))   
            
            else:            
                # Find the show that was running at the given time for the current channel.
                if curchannel == self.MyOverlayWindow.currentChannel:
                    if chtype == 8 and len(self.MyOverlayWindow.channels[curchannel - 1].getItemtimestamp(playlistpos)) > 0:
                        tmpDate = self.MyOverlayWindow.channels[curchannel - 1].getItemtimestamp(playlistpos)
                        epochBeginDate = datetime_to_epoch(tmpDate)
                        videotime = time.time() - epochBeginDate
                        reftime = time.time()
                    else:                        
                        videotime = xbmc.Player().getTime()
                        reftime = time.time()        
                else:
                    if chtype == 8 and len(self.MyOverlayWindow.channels[curchannel - 1].getItemtimestamp(playlistpos)) > 0:
                        playlistpos = self.MyOverlayWindow.channels[curchannel - 1].playlistPosition
                        tmpDate = self.MyOverlayWindow.channels[curchannel - 1].getItemtimestamp(playlistpos)
                        epochBeginDate = datetime_to_epoch(tmpDate)
                        #loop to ensure we get the current show in the playlist
                        while epochBeginDate + self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos) <  time.time():
                            epochBeginDate += self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)
                            playlistpos = self.MyOverlayWindow.channels[curchannel - 1].fixPlaylistIndex(playlistpos + 1)
                        videotime = time.time() - epochBeginDate
                        reftime = time.time()
                    else:
                        playlistpos = self.MyOverlayWindow.channels[curchannel - 1].playlistPosition
                        videotime = self.MyOverlayWindow.channels[curchannel - 1].showTimeOffset
                        reftime = self.MyOverlayWindow.channels[curchannel - 1].lastAccessTime

                # normalize reftime to the beginning of the video
                reftime -= videotime

                while reftime > starttime:
                    playlistpos -= 1
                    # No need to check bounds on the playlistpos, the duration function makes sure it is correct
                    reftime -= self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)

                while reftime + self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos) < starttime:
                    reftime += self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)
                    playlistpos += 1

                # create a button for each show that runs in the next hour and a half
                endtime = starttime + 5400
                totaltime = 0
                totalloops = 0
                
                while reftime < endtime and totalloops < 1000:
                    xpos = int(basex + (totaltime * (basew / 5400.0)))
                    tmpdur = self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos)
                    shouldskip = False

                    # this should only happen the first time through this loop
                    # it shows the small portion of the show before the current one
                    if reftime < starttime:
                        tmpdur -= starttime - reftime
                        reftime = starttime

                        if tmpdur < 60 * 3:
                            shouldskip = True
                    
                    # Don't show very short videos
                    if self.MyOverlayWindow.hideShortItems and shouldskip == False:
                        if chtype <= 7 and self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos) < self.MyOverlayWindow.shortItemLength:
                            shouldskip = True
                            tmpdur = 0
                        elif chtype >= 10 and self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos) < BYPASS_EPG_SECONDS:
                            shouldskip = True
                            tmpdur = 0
                        elif chtype not in [8,9]:
                            nextlen = self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos + 1)
                            prevlen = self.MyOverlayWindow.channels[curchannel - 1].getItemDuration(playlistpos - 1)

                            if nextlen < 60:
                                tmpdur += nextlen / 2

                            if prevlen < 60:
                                tmpdur += prevlen / 2

                    width = int((basew / 5400.0) * tmpdur)
                    if width < 30 and shouldskip == False:
                        width = 30
                        tmpdur = int(30.0 / (basew / 5400.0))

                    if width + xpos > basex + basew:
                        width = basex + basew - xpos

                    if shouldskip == False and width >= 30:
                        mylabel = self.MyOverlayWindow.channels[curchannel - 1].getItemTitle(playlistpos)
                        timestamp = self.MyOverlayWindow.channels[curchannel - 1].getItemtimestamp(playlistpos)
                        myLiveID = self.MyOverlayWindow.channels[curchannel - 1].getItemLiveID(playlistpos)
                        LiveID = self.chanlist.unpackLiveID(myLiveID)
                        type = LiveID[0]
                        rating = LiveID[5]
                        hd = LiveID[6] == 'True'
                        cc = LiveID[7] == 'True'
                        stars = LiveID[8]
                        rec = self.MyOverlayWindow.isRecord(str(chtype), str(curchannel), timestamp, pType='EPG')
                        sch = self.MyOverlayWindow.isReminder(str(chtype), str(curchannel), timestamp, pType='EPG')
                        EPGtags = {'REC': rec, 'SCH': sch, 'RATING': rating, 'HD': hd, 'CC': cc, 'STARS': stars} 
                            
                        if REAL_SETTINGS.getSetting('EPGcolor_enabled') == '1':
                            if type == 'movie' and REAL_SETTINGS.getSetting('EPGcolor_MovieGenre') == "false":
                                self.textureButtonNoFocus = self.getEPGtype('Movie')
                            else:
                                mygenre = self.MyOverlayWindow.channels[curchannel - 1].getItemgenre(playlistpos)
                                self.textureButtonNoFocus = self.getEPGtype(mygenre) 
                        elif REAL_SETTINGS.getSetting('EPGcolor_enabled') == '2':
                            self.textureButtonNoFocus = self.getEPGtype(str(chtype))
                        elif REAL_SETTINGS.getSetting('EPGcolor_enabled') == '3':
                            self.textureButtonNoFocus = self.getEPGtype(rating)
                        else:   
                            self.textureButtonNoFocus = MEDIA_LOC + BUTTON_NO_FOCUS
                            
                        # if self.MyOverlayWindow.channels[self.centerChannel - 1].getItemEpisodeTitle(-999) == ('[COLOR=%s][B]OnDemand[/B][/COLOR]' % ((self.MyOverlayWindow.channelbugcolor).replace('0x',''))):
                            # self.textureButtonFocus = IMAGES_LOC + 'label_ondemand.png'
                            # self.textureButtonNoFocus = MEDIA_LOC + 'label_ondemand.png'
                        
                        #Create Control array
                        self.channelButtons[row].append(xbmcgui.ControlButton(xpos, basey, width, baseh, mylabel, focusTexture=self.textureButtonFocus, noFocusTexture=self.textureButtonNoFocus, alignment=4, shadowColor=self.shadowColor, font=self.textfont, textColor=self.textcolor, focusedColor=self.focusedcolor))
                        self.addButtonTags(row, xpos, basey, width, baseh, mylabel, EPGtags)
                        
                    totaltime += tmpdur
                    reftime += tmpdur
                    playlistpos += 1
                    totalloops += 1

                if totalloops >= 1000:
                    self.log("Broken big loop, too many loops, reftime is " + str(reftime) + ", endtime is " + str(endtime))

                # If there were no buttons added, show some default button
                if len(self.channelButtons[row]) == 0:
                    self.channelButtons[row].append(xbmcgui.ControlButton(basex, basey, basew, baseh, self.MyOverlayWindow.getChname(curchannel), focusTexture=self.textureButtonFocus, noFocusTexture=self.textureButtonNoFocus, alignment=4, shadowColor=self.shadowColor, font=self.textfont, textColor=self.textcolor, focusedColor=self.focusedcolor))

        except:
            self.log("exception in setButtons", xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)
        
        self.log('setButtons return')
        return True


    def onAction(self, act):
        self.log('onAction ' + str(act.getId()))
        
        # temp disabled causes issues with overlay.windowswap
        # if self.actionSemaphore.acquire(False) == False:
            # self.log('Unable to get semaphore')
            # return
            
        action = act.getId()
        
        # if REAL_SETTINGS.getSetting("SFX_Enabled") == "true":
            # self.MyOverlayWindow.playSFX(action)
            
        try:
            if action in ACTION_PREVIOUS_MENU:
                if self.showingContext:    
                    self.closeContext()                    
                else:
                    self.closeEPG()   
                    
                if self.showingInfo:
                    self.infoOffset = 0
                    self.infoOffsetV = 0
            
            elif action in ACTION_MOVE_DOWN: 
                if not self.showingContext:
                    self.GoDown()    
                if self.showingInfo:  
                    self.infoOffsetV -= 1
                    
            elif action in ACTION_MOVE_UP:
                if not self.showingContext:
                    self.GoUp()         
                if self.showingInfo: 
                    self.infoOffsetV += 1

            elif action in ACTION_MOVE_LEFT: 
                if not self.showingContext:
                    self.GoLeft()           
                if self.showingInfo:
                    self.infoOffset -= 1
            
            elif action in ACTION_MOVE_RIGHT: 
                if not self.showingContext:
                    self.GoRight()           
                if self.showingInfo:
                    self.infoOffset += 1
            
            elif action == ACTION_STOP:
                self.closeEPG()           
                if self.showingInfo:
                    self.infoOffset = 0
                    self.infoOffsetV = 0
            
            elif action in ACTION_SELECT_ITEM:
                if self.showingContext:
                    pos = self.contextButton.getSelectedPosition()  
                    if pos == 0:
                        self.MyOverlayWindow.ContextMenuAction('MoreInfo','EPG') 
                    elif pos == 1:
                        self.MyOverlayWindow.ContextMenuAction('Similar','EPG') 
                    elif pos == 2:
                        self.MyOverlayWindow.ContextMenuAction('Record','EPG')  
                    elif pos == 3:
                        self.MyOverlayWindow.ContextMenuAction('Reminder','EPG')  
                        self.closeContext()   
                else:
                    lastaction = time.time() - self.lastActionTime           
                    if self.showingInfo:
                        self.infoOffset = 0
                        self.infoOffsetV = 0

                    if lastaction >= 2:
                        self.selectShow()
                        self.closeEPG()
                        self.infoOffset = 0
                        self.infoOffsetV = 0
                        self.lastActionTime = time.time()
                
            elif action in ACTION_PAGEDOWN: 
                if not self.showingContext:
                    self.GoPgDown()  
                if self.showingInfo:  
                    self.infoOffsetV -= 6       

            elif action in ACTION_PAGEUP: 
                if not self.showingContext:
                    self.GoPgUp()           
                if self.showingInfo:
                    self.infoOffsetV += 6
                    
            elif action == ACTION_RECORD:
                self.log('ACTION_RECORD')
                # PVRrecord(self.PVRchtype, self.PVRmediapath, self.PVRchname, getProperty("EPG.Title"))
                    
            elif action == ACTION_TELETEXT_RED:
                self.log('ACTION_TELETEXT_RED')
                self.MyOverlayWindow.windowSwap('EPG')
                
            elif action == ACTION_TELETEXT_GREEN:
                self.log('ACTION_TELETEXT_GREEN')
                self.MyOverlayWindow.windowSwap('DVR')

            elif action == ACTION_TELETEXT_YELLOW:
                self.log('ACTION_TELETEXT_YELLOW')
                self.MyOverlayWindow.windowSwap('ONDEMAND')
           
            elif action == ACTION_TELETEXT_BLUE:
                self.log('ACTION_TELETEXT_BLUE') 
                self.MyOverlayWindow.windowSwap('APPS')

            elif action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
                if self.inputChannel < 0:
                    self.inputChannel = action - ACTION_NUMBER_0
                else:
                    if self.inputChannel < 100:
                        self.inputChannel = self.inputChannel * 10 + action - ACTION_NUMBER_0
                
                self.showChannelLabel(self.inputChannel)

            elif action == ACTION_SYMBOLS: #Toggle thru favourite channels
                self.log('ACTION_SYMBOLS')
                self.showChannelLabel(self.MyOverlayWindow.Jump2Favorite())  

            elif action in ACTION_CONTEXT_MENU:
                if not self.showingContext:
                    self.showContextMenu()

        except:
            self.log("Unknown EPG exception", xbmc.LOGERROR)
            self.log(traceback.format_exc(), xbmc.LOGERROR)

            try:
                self.close()
            except:
                self.log("Error closing", xbmc.LOGERROR)

            self.MyOverlayWindow.sleepTimeValue = 1
            self.MyOverlayWindow.startSleepTimer()
            return

        # self.actionSemaphore.release()
        self.log('onAction return')


    def closeContext(self):
        self.showingContext = False
        try:
            self.removeControl(self.contextButtonB)
            self.removeControl(self.contextButtonC)       
            self.removeControl(self.contextButtonF)
            self.removeControl(self.contextButton)
        except:
            pass     
               
             
    def closeEPG(self):
        self.log('closeEPG')
        self.closeContext()        
        try:
            if self.channelLabelTimer.isAlive():
                self.channelLabelTimer.cancel()
        except:
            pass
        try:
            if self.GotoChannelTimer.isAlive():
                self.GotoChannelTimer.cancel()
        except:
            pass     
        try:
            self.removeControl(self.currentTime)
            self.removeControl(self.currentTimeBar)
            self.MyOverlayWindow.startSleepTimer()
        except:
            pass
        self.close()
            
                   
    def onControl(self, control):
        self.log('onControl')
        

    # Run when a show is selected, so close the epg and run the show
    def onClick(self, controlid):
        self.log('onClick')
        if not self.showingContext:
            try:
                if self.actionSemaphore.acquire(False) == False:
                    self.log('Unable to get semaphore')
                    return

                lastaction = time.time() - self.lastActionTime

                if lastaction >= 2:
                    try:
                        selectedbutton = self.getControl(controlid)
                    except:
                        self.actionSemaphore.release()
                        self.log('onClick unknown controlid ' + str(controlid))
                        return

                    for i in range(self.rowCount):
                        for x in range(len(self.channelButtons[i])):
                            mycontrol = 0
                            mycontrol = self.channelButtons[i][x]

                            if selectedbutton == mycontrol:
                                self.focusRow = i
                                self.focusIndex = x
                                self.selectShow()
                                self.closeEPG()
                                self.lastActionTime = time.time()
                                self.actionSemaphore.release()
                                self.log('onClick found button return')
                                return

                    self.lastActionTime = time.time()
                    self.closeEPG()

                self.actionSemaphore.release()
                self.log('onClick return')
            except:
                pass
    
    
    # Called from the timer to hide the channel label.
    def hideChannelLabel(self):
        self.log('hideChannelLabel')
        self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)
        for i in range(3):
            self.channelLabel[i].setVisible(False)

        inputChannel = self.inputChannel
        self.GotoChannelTimer = threading.Timer(5.1, self.GotoChannel, [inputChannel])
        self.GotoChannelTimer.name = "GotoChannel"
        if self.GotoChannelTimer.isAlive():
            self.GotoChannelTimer.cancel() 
        self.GotoChannelTimer.start()
        self.inputChannel = -1  
        self.log('hideChannelLabel return')
     
          
    # Display the current channel based on self.currentChannel.
    # Start the timer to hide it.
    def showChannelLabel(self, channel):
        self.log('showChannelLabel ' + str(channel))
        self.channelLabelTimer = threading.Timer(5.0, self.hideChannelLabel)
        self.channelLabelTimer.name = "ChannelLabel"
        if self.channelLabelTimer.isAlive():
            self.channelLabelTimer.cancel()         
            
        tmp = self.inputChannel
        self.hideChannelLabel()
        self.inputChannel = tmp
        curlabel = 0

        if channel > 99:
            if FileAccess.exists(IMAGES_LOC):
                self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str(channel // 100) + '.png')
            self.channelLabel[curlabel].setVisible(True)
            curlabel += 1

        if channel > 9:
            if FileAccess.exists(IMAGES_LOC):
                self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str((channel % 100) // 10) + '.png')
            self.channelLabel[curlabel].setVisible(True)
            curlabel += 1
        
        if FileAccess.exists(IMAGES_LOC):
            self.channelLabel[curlabel].setImage(IMAGES_LOC + 'label_' + str(channel % 10) + '.png')
        self.channelLabel[curlabel].setVisible(True)

        self.channelLabelTimer.start()
        self.log('showChannelLabel return')
        
            
    def GotoChannel(self, inchannel):
        self.log('GotoChannel, inchannel = ' + str(inchannel))
        self.log('GotoChannel, centerChannel = ' + str(self.centerChannel))
        try:
            if self.GotoChannelTimer.isAlive():
                self.GotoChannelTimer.cancel()
        except:
            pass
        try:
            if inchannel > self.centerChannel:
                increasing = False
            else:
                increasing = True
                
            newchannel = inchannel + 2
            self.log('GotoChannel, newchannel = ' + str(newchannel))
            self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(newchannel, increasing))
            self.setProperButton(0)
            self.inputChannel = -1
            self.log('GotoChannel return')
        except Exception,e:
            self.log('GotoChannel Failed! ' + str(e))
            
           
    def GoPgDown(self):
        self.log('GoPgDown')
        try:
            newchannel = self.centerChannel
            for x in range(0, 6):
                newchannel = self.MyOverlayWindow.fixChannel(newchannel + 1)
            self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(newchannel))
            self.setProperButton(0)
            self.log('GoPgDown return') 
        except:
            pass

    
    def GoPgUp(self):
        self.log('GoPgUp')
        try:
            newchannel = self.centerChannel
            for x in range(0, 6):
                newchannel = self.MyOverlayWindow.fixChannel(newchannel - 1, False)
            self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(newchannel))
            self.setProperButton(0)
            self.log('GoPgUp return')
        except:
            pass
            

    def GoDown(self):
        self.log('goDown')
        try:
            # change controls to display the proper junks
            if self.focusRow == self.rowCount - 1:
                self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(self.centerChannel + 1))
                self.focusRow = self.rowCount - 2
            self.setProperButton(self.focusRow + 1)
            self.log('goDown return')
        except:
            pass

    
    def GoUp(self):
        self.log('goUp')
        try:

            # same as godown
            # change controls to display the proper junks
            if self.focusRow == 0:
                self.setChannelButtons(self.shownTime, self.MyOverlayWindow.fixChannel(self.centerChannel - 1, False))
                self.focusRow = 1
            self.setProperButton(self.focusRow - 1)
            self.log('goUp return')
        except:
            pass

    
    def GoLeft(self):
        self.log('goLeft')
        try:
            basex, basey = self.getControl(111 + self.focusRow).getPosition()
            basew = self.getControl(111 + self.focusRow).getWidth()

            # change controls to display the proper junks
            if self.focusIndex == 0:
                left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
                width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
                left = left - basex
                starttime = self.shownTime + (left / (basew / 5400.0))
                self.setChannelButtons(self.shownTime - 1800, self.centerChannel)
                curbutidx = self.findButtonAtTime(self.focusRow, starttime + 30)

                if(curbutidx - 1) >= 0:
                    self.focusIndex = curbutidx - 1
                else:
                    self.focusIndex = 0
            else:
                self.focusIndex -= 1

            left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
            width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / 5400.0))
            endtime = starttime + (width / (basew / 5400.0))
            self.setFocus(self.channelButtons[self.focusRow][self.focusIndex])
            self.setShowInfo()
            self.focusEndTime = endtime
            self.focusTime = starttime + 30
            self.log('goLeft return')
        except:
            pass

    
    def GoRight(self):
        self.log('goRight')
        try:
            basex, basey = self.getControl(111 + self.focusRow).getPosition()
            basew = self.getControl(111 + self.focusRow).getWidth()

            # change controls to display the proper junks
            if self.focusIndex == len(self.channelButtons[self.focusRow]) - 1:
                left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
                width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
                left = left - basex
                starttime = self.shownTime + (left / (basew / 5400.0))
                self.setChannelButtons(self.shownTime + 1800, self.centerChannel)
                curbutidx = self.findButtonAtTime(self.focusRow, starttime + 30)

                if(curbutidx + 1) < len(self.channelButtons[self.focusRow]):
                    self.focusIndex = curbutidx + 1
                else:
                    self.focusIndex = len(self.channelButtons[self.focusRow]) - 1
            else:
                self.focusIndex += 1

            left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
            width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / 5400.0))
            endtime = starttime + (width / (basew / 5400.0))
            self.setFocus(self.channelButtons[self.focusRow][self.focusIndex])
            self.setShowInfo()
            self.focusEndTime = endtime
            self.focusTime = starttime + 30
            self.log('goRight return')
        except:
            pass

            
    def findButtonAtTime(self, row, selectedtime):
        self.log('findButtonAtTime ' + str(row))
        basex, basey = self.getControl(111 + row).getPosition()
        baseh = self.getControl(111 + row).getHeight()
        basew = self.getControl(111 + row).getWidth()

        for i in range(len(self.channelButtons[row])):
            left, top = self.channelButtons[row][i].getPosition()
            width = self.channelButtons[row][i].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / 5400.0))
            endtime = starttime + (width / (basew / 5400.0))

            if selectedtime >= starttime and selectedtime <= endtime:
                return i
        return -1


    # based on the current focus row and index, find the appropriate button in
    # the new row to set focus to
    def setProperButton(self, newrow, resetfocustime = False):
        self.log('setProperButton ' + str(newrow))
        self.focusRow = newrow
        basex, basey = self.getControl(111 + newrow).getPosition()
        baseh = self.getControl(111 + newrow).getHeight()
        basew = self.getControl(111 + newrow).getWidth()

        for i in range(len(self.channelButtons[newrow])):
            left, top = self.channelButtons[newrow][i].getPosition()
            width = self.channelButtons[newrow][i].getWidth()
            left = left - basex
            starttime = self.shownTime + (left / (basew / 5400.0))
            endtime = starttime + (width / (basew / 5400.0))

            if self.focusTime >= starttime and self.focusTime <= endtime:
                self.focusIndex = i
                self.setFocus(self.channelButtons[newrow][i])
                self.setShowInfo()
                self.focusEndTime = endtime

                if resetfocustime:
                    self.focusTime = starttime + 30

                self.log('setProperButton found button return')
                return

        self.focusIndex = 0
        self.setFocus(self.channelButtons[newrow][0])
        left, top = self.channelButtons[newrow][0].getPosition()
        width = self.channelButtons[newrow][0].getWidth()
        left = left - basex
        starttime = self.shownTime + (left / (basew / 5400.0))
        endtime = starttime + (width / (basew / 5400.0))
        self.focusEndTime = endtime

        if resetfocustime:
            self.focusTime = starttime + 30

        self.setShowInfo()
        self.log('setProperButton return')

            
    def setShowInfo(self):
        self.log('setShowInfo')        
        self.showingInfo = True
        
        basex, basey = self.getControl(111 + self.focusRow).getPosition()
        baseh = self.getControl(111 + self.focusRow).getHeight()
        basew = self.getControl(111 + self.focusRow).getWidth()
        
        # use the selected time to set the video
        left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
        left = left - basex + (width / 2)
        
        starttime = self.shownTime + (left / (basew / 5400.0))
        chnoffset = self.focusRow - 2
        newchan = self.centerChannel
        
        if self.MyOverlayWindow.OnDemand and chnoffset == 0:
            plpos = -999
            mediapath = xbmc.Player().getPlayingFile()
        else:
            while chnoffset != 0:
                if chnoffset > 0:
                    newchan = self.MyOverlayWindow.fixChannel(newchan + 1, True)
                    chnoffset -= 1
                else:
                    newchan = self.MyOverlayWindow.fixChannel(newchan - 1, False)
                    chnoffset += 1

            plpos = self.determinePlaylistPosAtTime(starttime, newchan)

            if plpos == -1:
                self.log('Unable to find the proper playlist to set from EPG')
                return
            mediapath = self.MyOverlayWindow.channels[newchan - 1].getItemFilename(plpos)
        
        if self.MyOverlayWindow.OnDemand == True:
            self.getControl(5008).setVisible(False)
            setProperty("EPG.DYNAMIC_LABEL",'OnDemand')    
        elif self.infoOffset > 0:
            self.getControl(5008).setVisible(False)
            setProperty("EPG.DYNAMIC_LABEL",'COMING UP')             
        elif self.infoOffset < 0:
            self.getControl(5008).setVisible(False)
            setProperty("EPG.DYNAMIC_LABEL",'ALREADY SEEN')
        elif self.infoOffset == 0 and self.infoOffsetV == 0:
            self.getControl(5008).setVisible(True)
            setProperty("EPG.DYNAMIC_LABEL",'NOW WATCHING')
        else:
            self.getControl(5008).setVisible(False)
            setProperty("EPG.DYNAMIC_LABEL",'ON NOW')

        chtype = self.MyOverlayWindow.getChtype(newchan)
        chname = self.MyOverlayWindow.getChname(newchan)
        self.SetMediaInfo(chtype, chname, mediapath, newchan, plpos)
        
        
    def SetMediaInfo(self, chtype, chname, mediapath, newchan, plpos):
        self.log('SetMediaInfo') 
        self.MyOverlayWindow.clearProp('EPG')  
        mpath = getMpath(mediapath)
        
        #setCore props
        setProperty("EPG.Chtype",str(chtype))
        setProperty("EPG.Mediapath",mediapath)
        setProperty("EPG.Chname",chname)
        setProperty("EPG.Chnum",str(newchan))
        setProperty("EPG.Mpath",mpath)  

        if plpos == -999:
            if len(getProperty("OVERLAY.OnDemand_tmpstr")) > 0:
                tmpstr = (getProperty("OVERLAY.OnDemand_tmpstr")).split('//')
                title = tmpstr[0]
                SEtitle = ('[COLOR=%s][B]OnDemand[/B][/COLOR]' % ((self.channelbugcolor).replace('0x','')))
                Description = tmpstr[2]
                genre = tmpstr[3]
                timestamp = tmpstr[4]
                LiveID = self.chanlist.unpackLiveID(tmpstr[5])
            else:
                self.MyOverlayWindow.getTMPSTR(chtype, chname, newchan, mediapath, plpos)
        else:
            title = (self.MyOverlayWindow.channels[newchan - 1].getItemTitle(plpos))   
            SEtitle = self.MyOverlayWindow.channels[newchan - 1].getItemEpisodeTitle(plpos) 
            Description = self.MyOverlayWindow.channels[newchan - 1].getItemDescription(plpos)
            genre = self.MyOverlayWindow.channels[newchan - 1].getItemgenre(plpos)
            timestamp = (self.MyOverlayWindow.channels[newchan - 1].getItemtimestamp(plpos))
            myLiveID = (self.MyOverlayWindow.channels[newchan - 1].getItemLiveID(plpos))        
            Chlogo = self.MyOverlayWindow.getChlogo(newchan)
            
        season, episode, swtitle = SEinfo(SEtitle, self.showSeasonEpisode)
        type, id, dbepid, managed, playcount, rating, hd, cc, stars = self.chanlist.unpackLiveID(myLiveID)
        dbid, epid = splitDBID(dbepid)
        year, title, showtitle = getTitleYear(title)
                        
        # SetProperties
        setProperty("EPG.TimeStamp",timestamp)
        setProperty("EPG.LOGOART",Chlogo)
        self.MyOverlayWindow.setProp(showtitle, 0, chtype, id, genre, rating, hd, cc, stars, mpath, mediapath, chname, SEtitle, type, dbid, epid, Description, playcount, season, episode, 'EPG')

   
    # using the currently selected button, play the proper shows
    def selectShow(self):
        self.log('selectShow')    
        self.MyOverlayWindow.setLastChannel(self.MyOverlayWindow.currentChannel)
        
        try:
            basex, basey = self.getControl(111 + self.focusRow).getPosition()
            baseh = self.getControl(111 + self.focusRow).getHeight()
            basew = self.getControl(111 + self.focusRow).getWidth()
            # use the selected time to set the video
            left, top = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
            width = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
            left = left - basex + (width / 2)
            starttime = self.shownTime + (left / (basew / 5400.0))
            chnoffset = self.focusRow - 2
            newchan = self.centerChannel
            
            while chnoffset != 0:
                if chnoffset > 0:
                    newchan = self.MyOverlayWindow.fixChannel(newchan + 1, True)
                    chnoffset -= 1
                else:
                    newchan = self.MyOverlayWindow.fixChannel(newchan - 1, False)
                    chnoffset += 1

            plpos = self.determinePlaylistPosAtTime(starttime, newchan)
            chtype = self.MyOverlayWindow.getChtype(newchan)
            if plpos == -1:
                self.log('Unable to find the proper playlist to set from EPG', xbmc.LOGERROR)
                return
           
            timedif = (time.time() - self.MyOverlayWindow.channels[newchan - 1].lastAccessTime)
            pos = self.MyOverlayWindow.channels[newchan - 1].playlistPosition
            showoffset = self.MyOverlayWindow.channels[newchan - 1].showTimeOffset
            #Start at the beginning of the playlist get the first epoch date
            #position pos of the playlist convert the string add until we get to the current item in the playlist

            if chtype == 8 and len(self.MyOverlayWindow.channels[newchan - 1].getItemtimestamp(pos)) > 0:
                tmpDate = self.MyOverlayWindow.channels[newchan - 1].getItemtimestamp(pos)
                epochBeginDate = datetime_to_epoch(tmpDate)
                while epochBeginDate + self.MyOverlayWindow.channels[newchan - 1].getItemDuration(pos) <  time.time():
                    epochBeginDate += self.MyOverlayWindow.channels[newchan - 1].getItemDuration(pos)
                    pos = self.MyOverlayWindow.channels[newchan - 1].fixPlaylistIndex(pos + 1)
                    self.log('live tv while loop')

            # adjust the show and time offsets to properly position inside the playlist
            else:
                while showoffset + timedif > self.MyOverlayWindow.channels[newchan - 1].getItemDuration(pos):

                    timedif -= self.MyOverlayWindow.channels[newchan - 1].getItemDuration(pos) - showoffset
                    pos = self.MyOverlayWindow.channels[newchan - 1].fixPlaylistIndex(pos + 1)
                    showoffset = 0
                self.log('pos + plpos ' + str(pos) +', ' + str(plpos))
            
            if self.MyOverlayWindow.currentChannel == newchan:
                if plpos == xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition():
                    self.log('selectShow return current show')
                    return

                if chtype == 8 and len(self.MyOverlayWindow.channels[newchan - 1].getItemtimestamp(pos)) > 0:
                    self.log('selectShow return current LiveTV channel')
                    return
            
            if pos != plpos:
                if chtype == 8 and len(self.MyOverlayWindow.channels[newchan - 1].getItemtimestamp(pos)) > 0:
                    self.log('selectShow return different LiveTV channel')
                    tmpDate = self.MyOverlayWindow.channels[newchan - 1].getItemtimestamp(pos)
                    epochBeginDate = datetime_to_epoch(tmpDate)
                    #beginDate = datetime.datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
                    #loop till we get to the current show  
                    while epochBeginDate + self.MyOverlayWindow.channels[newchan - 1].getItemDuration(pos) <  time.time():
                        epochBeginDate += self.MyOverlayWindow.channels[newchan - 1].getItemDuration(pos)
                        pos = self.MyOverlayWindow.channels[newchan - 1].fixPlaylistIndex(pos + 1)

                else:
                    self.MyOverlayWindow.channels[newchan - 1].setShowPosition(plpos)
                    self.MyOverlayWindow.channels[newchan - 1].setShowTime(0)
                    self.MyOverlayWindow.channels[newchan - 1].setAccessTime(time.time())

            self.MyOverlayWindow.newChannel = newchan
            self.log('selectShow return')
        except:
            pass
        
        
    def determinePlaylistPosAtTime(self, starttime, channel):
        self.log('determinePlaylistPosAtTime ' + str(starttime) + ', ' + str(channel))
        channel = self.MyOverlayWindow.fixChannel(channel)
        chtype = self.MyOverlayWindow.getChtype(channel)

        try:
            # if the channel is paused, then it's just the current item
            if self.MyOverlayWindow.channels[channel - 1].isPaused:
                self.log('determinePlaylistPosAtTime paused return')
                return self.MyOverlayWindow.channels[channel - 1].playlistPosition
            else:
                # Find the show that was running at the given time
                # Use the current time and show offset to calculate it
                # At timedif time, channelShowPosition was playing at channelTimes
                # The only way this isn't true is if the current channel is curchannel since
                # it could have been fast forwarded or rewinded (rewound)?
                if channel == self.MyOverlayWindow.currentChannel: #currentchannel epg
                    playlistpos = xbmc.PlayList(xbmc.PLAYLIST_MUSIC).getposition()   
                    #Live TV pull date from the playlist entry
                    if chtype == 8 and len(self.MyOverlayWindow.channels[channel - 1].getItemtimestamp(playlistpos)) > 0:
                        tmpDate = self.MyOverlayWindow.channels[channel - 1].getItemtimestamp(playlistpos)
                        epochBeginDate = datetime_to_epoch(tmpDate)
                        videotime = time.time() - epochBeginDate
                        reftime = time.time()
                    else:
                        videotime = xbmc.Player().getTime()
                        reftime = time.time() 
                else:
                    playlistpos = self.MyOverlayWindow.channels[channel - 1].playlistPosition
                    #Live TV pull date from the playlist entry
                    if chtype == 8 and len(self.MyOverlayWindow.channels[channel - 1].getItemtimestamp(playlistpos)) > 0:
                        tmpDate = self.MyOverlayWindow.channels[channel - 1].getItemtimestamp(playlistpos)
                        epochBeginDate = datetime_to_epoch(tmpDate)
                        while epochBeginDate + self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos) <  time.time():
                            epochBeginDate += self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos)
                            playlistpos = self.MyOverlayWindow.channels[channel - 1].fixPlaylistIndex(playlistpos + 1)
                        videotime = time.time() - epochBeginDate
                        reftime = time.time()
                          
                    else:
                        videotime = self.MyOverlayWindow.channels[channel - 1].showTimeOffset
                        reftime = self.MyOverlayWindow.channels[channel - 1].lastAccessTime

                # normalize reftime to the beginning of the video
                reftime -= videotime

                while reftime > starttime:
                    playlistpos -= 1
                    reftime -= self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos)

                while reftime + self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos) < starttime:
                    reftime += self.MyOverlayWindow.channels[channel - 1].getItemDuration(playlistpos)
                    playlistpos += 1

                self.log('determinePlaylistPosAtTime return' + str(self.MyOverlayWindow.channels[channel - 1].fixPlaylistIndex(playlistpos)))
                return self.MyOverlayWindow.channels[channel - 1].fixPlaylistIndex(playlistpos)
        except:
            pass
        
        
    def addButtonTags(self, row, xpos, basey, width, baseh, mylabel, EPGtags):      
        self.log('addButtonTags')
        cc = EPGtags['CC']
        hd = EPGtags['HD']
        rec = EPGtags['REC']
        sch = EPGtags['SCH']
        rating = EPGtags['RATING']
        stars = EPGtags['STARS']
        
        button_width = xpos + width
        label_width = xpos + len(mylabel) * 15
        
        xtag_left = button_width - 30
        ytag_pos_upper = basey + baseh/4  
        
        xtag_right = label_width + 30
        ytag_pos_lower = basey + baseh/2
        hd_xtag = xtag_left - 30
        cc_xtag = xtag_right + 30
        rat_xtag = cc_xtag + 45
        
        # upper tags (rec or reminder)         
        wtag = 30
        htag = 15
        if button_width > xtag_left and label_width < xtag_left and xtag_left < button_width:
            if rec == True:
                self.channelTags[row].append(xbmcgui.ControlImage(xtag_left, ytag_pos_upper, wtag, htag, os.path.join(TAG_LOC,'REC.png'),2,''))
            elif sch == True:
                self.channelTags[row].append(xbmcgui.ControlImage(xtag_left, ytag_pos_upper, wtag, htag, os.path.join(TAG_LOC,'SCH.png'),2,''))
                    
        # lower tags (cc,ratings,hd)
        if REAL_SETTINGS.getSetting("EPG.xInfo") == "true":     
            wtag = 30
            htag = 30
            # pos end of button
            if hd == True:       
                if button_width > hd_xtag and label_width + 30 < hd_xtag and hd_xtag < button_width:
                    self.channelTags[row].append(xbmcgui.ControlImage(hd_xtag, ytag_pos_lower, wtag, htag, os.path.join(TAG_LOC,'HD.png'),2,''))   
            
            # pos end of mylabel
            if cc == True:
                wtag = 60
                htag = 15
                if button_width > cc_xtag and label_width +30 < cc_xtag and cc_xtag < button_width and cc_xtag + wtag < hd_xtag and cc_xtag < rat_xtag:
                    self.channelTags[row].append(xbmcgui.ControlImage(cc_xtag, ytag_pos_lower, wtag, htag, os.path.join(TAG_LOC,'CC.png'),2,''))
                    
            if not rating in ['NR','NA','']:
                wtag = 60       
                htag = 15
                if button_width > rat_xtag and label_width + 30 < rat_xtag and rat_xtag < button_width and rat_xtag + wtag < hd_xtag:
                    self.channelTags[row].append(xbmcgui.ControlImage(rat_xtag, ytag_pos_lower, wtag, htag, (os.path.join(TAG_LOC,'%s.png') % rating),2,''))
            
            elif not stars in ['0.0','']:
                wtag = 90       
                htag = 15
                if button_width > rat_xtag and label_width + 30 < rat_xtag and rat_xtag < button_width and rat_xtag + wtag < hd_xtag:
                    self.channelTags[row].append(xbmcgui.ControlImage(rat_xtag, ytag_pos_lower, wtag, htag, (os.path.join(STAR_LOC,'%s.png') % stars),2,''))

            
    def showContextMenu(self):
        self.log('showContextMenu')
        self.showingContext = True
        ChanButtonx, ChanButtony = self.channelButtons[self.focusRow][self.focusIndex].getPosition()
        ChanButtonw = self.channelButtons[self.focusRow][self.focusIndex].getWidth()
        ChanButtonh = self.channelButtons[self.focusRow][self.focusIndex].getHeight()
        self.contextButtonB = xbmcgui.ControlImage(0, 0, 1920, 1080, self.ButtonContextGauss)
        self.addControl(self.contextButtonB)
        self.contextButtonC = xbmcgui.ControlImage(ChanButtonx-4, ChanButtony+71, 258, 308, self.ButtonContextBackground)
        self.addControl(self.contextButtonC)
        self.contextButtonF = xbmcgui.ControlButton(ChanButtonx-4, ChanButtony, ChanButtonw+8, ChanButtonh, '[ '+getProperty("EPG.Title")+' ]', focusTexture=self.ButtonContextFocus, noFocusTexture=self.ButtonContextFocus, alignment=4, shadowColor=self.shadowColor, textColor=self.textcolor, focusedColor=self.focusedcolor)
        self.addControl(self.contextButtonF)
        self.contextButton = xbmcgui.ControlList(ChanButtonx, ChanButtony+75, 250, 1000, self.textfont, self.textcolor, self.ButtonContextNoFocus, self.textureButtonFocus, self.focusedcolor, 0, 0, 0, 0, 75, 0, 4)
        self.addControl(self.contextButton)
        self.ContextList = ['More Info','Find Similar','Record Show','Set Reminder']
        if self.MyOverlayWindow.isReminder(getProperty("EPG.Chtype"), getProperty("EPG.Chnum"), getProperty("EPG.TimeStamp"), pType='EPG') == True:
            self.ContextList = replaceStringElem(self.ContextList,'Set Reminder','Remove Reminder')
        self.contextButton.addItems(items=self.ContextList)
        self.setFocus(self.contextButton)