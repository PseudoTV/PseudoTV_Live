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

import xbmc, xbmcgui, xbmcaddon
import subprocess, os
import time, threading
import datetime
import sys, re
import random

from utils import *
from Globals import *
from Playlist import PlaylistItem


class RulesList:
    def __init__(self):
        self.ruleList = [BaseRule(), RenameRule(), NoShowRule(), ScheduleChannelRule(), OnlyWatchedRule(), DontAddChannel(), InterleaveChannel(), ForceRealTime(), AlwaysPause(), ForceResume(), ForceRandom(), OnlyUnWatchedRule(), PlayShowInOrder(), SetResetTime(), HandleIceLibrary(), HandleChannelLogo(), EvenShowsRule(), HandleBCT(), HandlePOP(), Handle3D(), HandleDurFilter(), HandleSeek(), PinLock(), HandleMeta()]
        

    def getRuleCount(self):
        return len(self.ruleList)


    def getRule(self, index):
        while index < 0:
            index += len(self.ruleList)

        while index >= len(self.ruleList):
            index -= len(self.ruleList)

        return self.ruleList[index]



class BaseRule:
    def __init__(self):
        self.name = ""
        self.description = ""
        self.optionLabels = []
        self.optionValues = []
        self.myId = 0
        self.actions = 0


    def getName(self):
        return self.name


    def getTitle(self):
        return self.name


    def getOptionCount(self):
        return len(self.optionLabels)


    def onAction(self, act, optionindex):
        return ''


    def getOptionLabel(self, index):
        if index >= 0 and index < self.getOptionCount():
            return self.optionLabels[index]
        return ''


    def getOptionValue(self, index):
        if index >= 0 and index < len(self.optionValues):
            return self.optionValues[index]
        return ''


    def getRuleIndex(self, channeldata):
        index = 0

        for rule in channeldata.ruleList:
            if rule == self:
                return index
            index += 1
        return -1


    def getId(self):
        return self.myId


    def runAction(self, actionid, channelList, param):
        return param


    def copy(self):
        return BaseRule()


    def log(self, msg, level = xbmc.LOGDEBUG):
        log("Rule " + self.getTitle() + ": " + msg, level)


    def validate(self):
        pass


    def reset(self):
        self.__init__()


    def validateTextBox(self, optionindex, length):
        if len(self.optionValues[optionindex]) > length:
            self.optionValues[optionindex] = self.optionValues[optionindex][:length]


    def onActionTextBox(self, act, optionindex):
        action = act.getId()

        if act.getId() in ACTION_SELECT_ITEM:
            keyb = xbmc.Keyboard(self.optionValues[optionindex], self.name, False)
            keyb.doModal()
            if keyb.isConfirmed():
                self.optionValues[optionindex] = keyb.getText()


    def onActionDateBox(self, act, optionindex):
        self.log("onActionDateBox")

        if act.getId() in ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            info = dlg.numeric(1, self.optionLabels[optionindex], self.optionValues[optionindex])
            if info != None:
                self.optionValues[optionindex] = info


    def onActionTimeBox(self, act, optionindex):
        self.log("onActionTimeBox")
        action = act.getId()

        if action in ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            info = dlg.numeric(2, self.optionLabels[optionindex], self.optionValues[optionindex])
            if info != None:
                if info[0] == ' ':
                    info = info[1:]
                if len(info) == 4:
                    info = "0" + info
                self.optionValues[optionindex] = info

                
    def validateTimeBox(self, optionindex):
        values = []
        broken = False

        try:
            values.append(int(self.optionValues[optionindex][0]))
            values.append(int(self.optionValues[optionindex][1]))
            values.append(int(self.optionValues[optionindex][3]))
            values.append(int(self.optionValues[optionindex][4]))
        except:
            self.optionValues[optionindex] = "00:00"
            return

        if values[0] > 2:
            broken = True

        if values[0] == 2:
            if values[1] > 3:
                broken = True

        if values[2] > 5:
            broken = True

        if broken:
            self.optionValues[optionindex] = "00:00"
            return


    def onActionSelectBox(self, act, optionindex):
        if act.getId() in ACTION_SELECT_ITEM:
            optioncount = len(self.selectBoxOptions[optionindex])
            cursel = -1

            for i in range(optioncount):
                if self.selectBoxOptions[optionindex][i] == self.optionValues[optionindex]:
                    cursel = i
                    break

            cursel += 1

            if cursel >= optioncount:
                cursel = 0

            self.optionValues[optionindex] = self.selectBoxOptions[optionindex][cursel]


    def onActionDaysofWeekBox(self, act, optionindex):
        self.log("onActionDaysofWeekBox")

        if act.getId() in ACTION_SELECT_ITEM:
            keyb = xbmc.Keyboard(self.optionValues[optionindex], self.name, False)
            keyb.doModal()

            if keyb.isConfirmed():
                self.optionValues[optionindex] = keyb.getText().upper()

        button = act.getButtonCode()

        # Remove the shift key if it's there
        if button >= 0x2F041 and button <= 0x2F05B:
            button -= 0x20000

        # Pressed some character
        if button >= 0xF041 and button <= 0xF05B:
            button -= 0xF000

            # Check for UMTWHFS
            if button == 85 or button == 77 or button == 84 or button == 87 or button == 72 or button == 70 or button == 83:
                # Check to see if it's already in the string
                loc = self.optionValues[optionindex].find(chr(button))

                if loc != -1:
                    self.optionValues[optionindex] = self.optionValues[optionindex][:loc] + self.optionValues[optionindex][loc + 1:]
                else:
                    self.optionValues[optionindex] += chr(button)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]

        if xbmc.getCondVisibility("Window.IsVisible(10111)"):
            self.log("shutdown window is visible")
            xbmc.executebuiltin("Dialog.close(10111)")


    def validateDaysofWeekBox(self, optionindex):
        self.log("validateDaysofWeekBox")
        daysofweek = "UMTWHFS"
        newstr = ''

        for day in daysofweek:
            loc = self.optionValues[optionindex].find(day)

            if loc != -1:
                newstr += day

        self.optionValues[optionindex] = newstr


    def validateDigitBox(self, optionindex, minimum, maximum, default):
        if len(self.optionValues[optionindex]) == 0:
            return

        try:
            val = int(self.optionValues[optionindex])

            if val >= minimum and val <= maximum:
                self.optionValues[optionindex] = str(val)

            return
        except:
            pass

        self.optionValues[optionindex] = str(default)


    def onActionDigitBox(self, act, optionindex):
        action = act.getId()

        if action in ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            value = dlg.numeric(0, self.optionLabels[optionindex], self.optionValues[optionindex])

            if value != None:
                self.optionValues[optionindex] = value

        button = act.getButtonCode()

        # Numbers
        if action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
            self.optionValues[optionindex] += chr(action - ACTION_NUMBER_0 + 48)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]

        # Delete
        if button == 0xF02E:
            self.optionValues[optionindex] = ''


class RenameRule(BaseRule):
    def __init__(self):
        self.name = "Set Channel Name"
        self.optionLabels = ['New Channel Name']
        self.optionValues = [' ']
        self.myId = 1
        self.actions = RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED


    def copy(self):
        return RenameRule()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            return 'Rename Channel to ' + self.optionValues[0]

        return self.name


    def onAction(self, act, optionindex):
        self.onActionTextBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateTextBox(0, 18)


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            self.validate()
            channeldata.name = self.optionValues[0]

        return channeldata



class NoShowRule(BaseRule):
    def __init__(self):
        self.name = "Don't Include a Show"
        self.optionLabels = ['Show Name']
        self.optionValues = [' ']
        self.myId = 2
        self.actions = RULES_ACTION_LIST


    def copy(self):
        return NoShowRule()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            return "Don't Include '" + self.optionValues[0] + "'"

        return self.name


    def onAction(self, act, optionindex):
        self.onActionTextBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateTextBox(0, 20)


    def runAction(self, actionid, channelList, filelist):
        if actionid == RULES_ACTION_LIST:
            self.validate()
            opt = self.optionValues[0].lower()
            realindex = 0

            for index in range(len(filelist)):
                item = filelist[realindex]
                loc = item.find(',')

                if loc > -1:
                    loc2 = item.find("//")

                    if loc2 > -1:
                        showname = item[loc + 1:loc2]
                        showname = showname.lower()

                        if showname.find(opt) > -1:
                            filelist.pop(realindex)
                            realindex -= 1

                realindex += 1

        return filelist



class ScheduleChannelRule(BaseRule):
    def __init__(self):
        self.name = "Best-Effort Channel Scheduling"
        now = datetime.datetime.now()
        today = now.strftime("%d/%m/%Y")
        self.optionLabels = ['Channel Number', 'Days of the Week (UMTWHFS)', 'Time (HH:MM)', 'Episode Count', 'Starting Episode', 'Starting Date (DD/MM/YYYY)']
        self.optionValues = ['0', 'UMTWHFS', '00:00', '1', '1', today]
        self.myId = 3
        self.actions = RULES_ACTION_START | RULES_ACTION_BEFORE_CLEAR | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED
        self.clearedcount = 0
        self.appended = False
        self.hasRun = False
        self.nextScheduledTime = 0
        self.startIndex = 0


    def copy(self):
        return ScheduleChannelRule()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            return "Schedule Channel " + self.optionValues[0]
        return self.name


    def onAction(self, act, optionindex):
        if optionindex == 0:
            self.onActionDigitBox(act, optionindex)

        if optionindex == 1:
            self.onActionDaysofWeekBox(act, optionindex)

        if optionindex == 2:
            self.onActionTimeBox(act, optionindex)

        if optionindex == 3:
            self.onActionDigitBox(act, optionindex)

        if optionindex == 4:
            self.onActionDigitBox(act, optionindex)

        if optionindex == 5:
            self.onActionDateBox(act, optionindex)

        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 1000, '')
        self.validateDaysofWeekBox(1)
        self.validateTimeBox(2)
        self.validateDigitBox(3, 1, 1000, 1)
        self.validateDigitBox(4, 1, 1000, 1)


    def runAction(self, actionid, channelList, channeldata):
        self.log("runAction " + str(actionid))

        if actionid == RULES_ACTION_START:
            self.clearedcount = 0
            self.hasRun = False
            self.nextScheduledTime = 0

        if actionid == RULES_ACTION_BEFORE_CLEAR:
            self.clearedcount = channeldata.Playlist.size()

            if channeldata.totalTimePlayed > 0:
                self.appended = True
            else:
                self.appended = False

        # When resetting the channel, make sure the starting episode and date are correct.
        # Work backwards from the current ep and date to set the current date to today and proper ep
        if actionid == RULES_ACTION_FINAL_MADE and self.hasRun == False:
            curchan = channeldata.channelNumber
            ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_lastscheduled', '0')

            for rule in channeldata.ruleList:
                if rule.getId() == self.myId:
                    rule.reverseStartingEpisode()
                    rule.nextScheduledTime = 0

        if (actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED) and (self.hasRun == False):
            self.runSchedulingRules(channelList, channeldata)
        return channeldata


    def reverseStartingEpisode(self):
        self.log("reverseStartingEpisode")
        tmpdate = 0

        try:
            tmpdate = time.mktime(time.strptime(self.optionValues[5] + " " + self.optionValues[2], "%d/%m/%Y %H:%M"))
        except:
            pass

        if tmpdate > 0:
            count = 0
            currentdate = int(time.time())

            while tmpdate > currentdate:
                thedate = datetime.datetime.fromtimestamp(currentdate)
                self.optionValues[5] = thedate.strftime("%d/%m/%Y")
                self.determineNextTime()

                if self.nextScheduledTime > 0:
                    count += 1
                    currentdate = self.nextScheduledTime + (60 * 60 * 24)
                else:
                    break

            try:
                startep = int(self.optionValues[4])
                count = startep - count

                if count > 0:
                    self.optionValues[4] = str(count)
                    thedate = datetime.datetime.fromtimestamp(int(time.time()))
#                        self.optionValues[5] = thedate.strftime(xbmc.getRegion("dateshort"))
                    self.optionValues[5] = thedate.strftime("%d/%m/%Y")
                    self.saveOptions(channeldata)
            except:
                pass


    def runSchedulingRules(self, channelList, channeldata):
        self.log("runSchedulingRules")
        curchan = channelList.runningActionChannel
        self.hasRun = True

        try:
            self.startIndex = int(ADDON_SETTINGS.getSetting('Channel_' + str(curchan) + '_lastscheduled'))
        except:
            self.startIndex = 0

        if self.appended == True:
            self.startIndex -= self.clearedcount - channeldata.Playlist.size()

        if self.startIndex < channeldata.playlistPosition:
            self.startIndex = channeldata.fixPlaylistIndex(channeldata.playlistPosition + 1)

            if self.startIndex == 0:
                self.log("Currently playing the last item, odd")
                return

        # Have all scheduling rules determine the next scheduling time
        self.determineNextTime()
        minimum = self

        for rule in channeldata.ruleList:
            if rule.getId() == self.myId:
                if rule.nextScheduledTime == 0:
                    rule.determineNextTime()

                rule.startIndex = self.startIndex
                rule.hasRun = True

                if rule.nextScheduledTime < minimum.nextScheduledTime or minimum.nextScheduledTime == 0:
                    minimum = rule

        added = True
        newstart = 0

        while added == True and minimum.nextScheduledTime != 0:
            added = minimum.addScheduledShow(channelList, channeldata, self.appended)
            newstart = minimum.startIndex

            # Determine the new minimum
            if added:
                minimum.determineNextTime()

                for rule in channeldata.ruleList:
                    if rule.getId() == self.myId:
                        rule.startIndex = newstart

                        if rule.nextScheduledTime < minimum.nextScheduledTime or minimum.nextScheduledTime == 0:
                            minimum = rule

        ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_lastscheduled', str(newstart))
        # Write the channel playlist to a file
        channeldata.Playlist.save(CHANNELS_LOC + 'channel_' + str(curchan) + '.m3u')


    # Fill in nextScheduledTime
    def determineNextTime(self):
        self.optionValues[5] = self.optionValues[5].replace(' ', '0')
        self.log("determineNextTime " + self.optionValues[5] + " " + self.optionValues[2])
        starttime = 0
        daysofweek = 0

        if len(self.optionValues[2]) != 5 or self.optionValues[2][2] != ':':
            self.log("Invalid time")
            self.nextScheduledTime = 0
            return

        try:
            # This is how it should be, but there is a bug in XBMC preventing this
#            starttime = time.mktime(time.strptime(self.optionValues[5] + " " + self.optionValues[2], xbmc.getRegion("dateshort") + " %H:%M"))
            starttime = time.mktime(time.strptime(self.optionValues[5] + " " + self.optionValues[2], "%d/%m/%Y %H:%M"))
        except:
            self.log("Invalid date or time")
            self.nextScheduledTime = 0
            return

        try:
            tmp = self.optionValues[1]

            if tmp.find('M') > -1:
                daysofweek |= 1

            if tmp.find('T') > -1:
                daysofweek |= 2

            if tmp.find('W') > -1:
                daysofweek |= 4

            if tmp.find('H') > -1:
                daysofweek |= 8

            if tmp.find('F') > -1:
                daysofweek |= 16

            if tmp.find('S') > -1:
                daysofweek |= 32

            if tmp.find('U') > -1:
                daysofweek |= 64
        except:
            self.log("Invalid date or time")
            self.nextScheduledTime = 0
            return

        thedate = datetime.datetime.fromtimestamp(starttime)
        delta = datetime.timedelta(days=1)

        # If no day selected, assume every day
        if daysofweek == 0:
            daysofweek = 127

        # Determine the proper day of the week
        while True:
            if daysofweek & (1 << thedate.weekday()) > 0:
                break

            thedate += delta

        self.nextScheduledTime = int(time.mktime(thedate.timetuple()))


    def saveOptions(self, channeldata):
        curchan = channeldata.channelNumber
        curruleid = self.getRuleIndex(channeldata) + 1
        ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rule_' + str(curruleid) + '_opt_5', self.optionValues[4])
        ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rule_' + str(curruleid) + '_opt_6', self.optionValues[5])


    # Add a single show (or shows) to the channel at nextScheduledTime
    # This needs to modify the startIndex value if something is added
    def addScheduledShow(self, channelList, channeldata, appending):
        self.log("addScheduledShow")
        chan = 0
        epcount = 0
        startingep = 0
        curchan = channeldata.channelNumber
        curruleid = self.getRuleIndex(channeldata)
        currentchantime = channelList.lastExitTime + channeldata.totalTimePlayed

        if channeldata.Playlist.size() == 0:
            return False

        try:
            chan = int(self.optionValues[0])
            epcount = int(self.optionValues[3])
            startingep = int(self.optionValues[4]) - 1
        except:
            pass

        if startingep < 0:
            startingep = 0

        # If the next scheduled show has already passed, then skip it
        if currentchantime > self.nextScheduledTime:
            thedate = datetime.datetime.fromtimestamp(self.nextScheduledTime)
            delta = datetime.timedelta(days=1)
            thedate += delta
            self.optionValues[4] = str(startingep + epcount)
#            self.optionValues[5] = thedate.strftime(xbmc.getRegion("dateshort"))
            self.optionValues[5] = thedate.strftime("%d/%m/%Y")
            self.log("Past the scheduled date and time, skipping")
            self.saveOptions(channeldata)
            return True

        if chan > channelList.maxChannels or chan < 1 or epcount < 1:
            self.log("channel number is invalid")
            return False

        if len(channelList.channels) < chan or channelList.channels[chan - 1].isSetup == False:
            if channelList.myOverlay.isMaster:
                channelList.setupChannel(chan, True, True, False)
            else:
                channelList.setupChannel(chan, True, False, False)

        if channelList.channels[chan - 1].Playlist.size() < 1:
            self.log("scheduled channel isn't valid")
            return False

        # If the total time played value hasn't been updated
        if appending == False:
            timedif = self.nextScheduledTime - channelList.lastExitTime
        else:
            # If the total time played value HAS been updated
            timedif = self.nextScheduledTime + channeldata.totalTimePlayed - channelList.myOverlay.timeStarted

        showindex = 0

        # Find the proper location to insert the show(s)
        while timedif > 120 or showindex < self.startIndex:
            timedif -= channeldata.getItemDuration(showindex)
            showindex = channeldata.fixPlaylistIndex(showindex + 1)

            # Shows that there was a looparound, so exit.
            if showindex == 0:
                self.log("Couldn't find a location for the show")
                return False

        # If there is nothing after the selected show index and the time is still
        # too far away, don't do anything
        if (channeldata.Playlist.size() - (showindex + 1) <= 0) and (timedif < -300):
            return False

        # rearrange episodes to get an optimal time
        if timedif < -300 and channeldata.isRandom:
            # This is a crappy way to do it, but implementing a subset sum algorithm is
            # a bit daunting at the moment.  Plus this uses a minimum amount of memory, so as
            # a background task it works well.
            lasttime = int(abs(timedif))

            # Try a maximum of 5 loops
            for loops in range(5):
                newtime = self.rearrangeShows(showindex, lasttime, channeldata, channelList)

                if channelList.threadPause() == False:
                    return False

                # If no match found, then stop
                # If the time difference is less than 2 minutes, also stop
                if newtime == lasttime or newtime < 120:
                    break

                lasttime = newtime

        for i in range(epcount):
            item = PlaylistItem()
            item.duration = channelList.channels[chan - 1].getItemDuration(startingep + i)
            item.filename = channelList.channels[chan - 1].getItemFilename(startingep + i)
            item.description = channelList.channels[chan - 1].getItemDescription(startingep + i)
            item.title = channelList.channels[chan - 1].getItemTitle(startingep + i)
            item.episodetitle = channelList.channels[chan - 1].getItemEpisodeTitle(startingep + i)
            item.genre = channelList.channels[chan - 1].getItemgenre(startingep + i)
            item.timestamp = channelList.channels[chan - 1].getItemtimestamp(startingep + i)
            item.LiveID = channelList.channels[chan - 1].getItemLiveID(startingep + i)
            channeldata.Playlist.itemlist.insert(showindex, item)
            channeldata.Playlist.totalDuration += item.duration
            showindex += 1

        thedate = datetime.datetime.fromtimestamp(self.nextScheduledTime)
        delta = datetime.timedelta(days=1)
        thedate += delta
        self.startIndex = showindex
        self.optionValues[4] = str(startingep + epcount + 1)
#        self.optionValues[5] = thedate.strftime(xbmc.getRegion("dateshort"))
        self.optionValues[5] = thedate.strftime("%d/%m/%Y")
        self.saveOptions(channeldata)
        self.log("successfully scheduled at index " + str(self.startIndex))
        return True


    def rearrangeShows(self, showindex, timedif, channeldata, channelList):
        self.log("rearrangeShows " + str(showindex) + " " + str(timedif))
        self.log("start index: " + str(self.startIndex) + ", end index: " + str(showindex))
        matchdur = timedif
        matchidxa = 0
        matchidxb = 0

        if self.startIndex >= showindex:
            self.log("Invalid indexes")
            return timedif

        if channeldata.Playlist.size() - (showindex + 1) <= 0:
            self.log("No shows after the show index")
            return timedif

        for curindex in range(self.startIndex, showindex + 1):
            neededtime = channeldata.getItemDuration(curindex) - timedif

            if channelList.threadPause() == False:
                return timedif

            if neededtime > 0:
                for inx in range(showindex + 1, channeldata.Playlist.size()):
                    curtime = channeldata.getItemDuration(inx) - neededtime

                    if abs(curtime) < matchdur:
                        matchdur = abs(curtime)
                        matchidxa = curindex
                        matchidxb = inx

        # swap curindex with inx
        if matchdur < abs(timedif):
            self.log("Found with a new timedif of " + str(matchdur) + "!  Swapping " + str(matchidxa) + " with " + str(matchidxb))
            plitema = channeldata.Playlist.itemlist[matchidxa]
            plitemb = channeldata.Playlist.itemlist[matchidxb]
            channeldata.Playlist.itemlist[matchidxa] = plitemb
            channeldata.Playlist.itemlist[matchidxb] = plitema
            return matchdur

        self.log("No match found")
        return timedif



class OnlyWatchedRule(BaseRule):
    def __init__(self):
        self.name = "Only Play Watched Items"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 4
        self.actions = RULES_ACTION_JSON


    def copy(self):
        return OnlyWatchedRule()


    def runAction(self, actionid, channelList, filedata):
        if actionid == RULES_ACTION_JSON:
            playcount = re.search('"playcount" *: *([0-9]*?),', filedata)
            pc = 0

            try:
                pc = int(playcount.group(1))
            except:
                pc = 0

            if pc == 0:
                return ''

        return filedata



class DontAddChannel(BaseRule):
    def __init__(self):
        self.name = "Don't Play This Channel"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 5
        self.actions = RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED


    def copy(self):
        return DontAddChannel()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channeldata.isValid = False

        return channeldata



class InterleaveChannel(BaseRule):
    def __init__(self):
        self.name = "Interleave Channel"
        self.optionLabels = ['Channel Number', 'Min Interleave Count', 'Max Interleave Count', 'Starting Episode', 'Play # Episodes', 'Start Position']
        self.optionValues = ['0', '1', '1', '1', '1', '1']
        self.myId = 6
        self.actions = RULES_ACTION_LIST


    def copy(self):
        return InterleaveChannel()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            return "Interleave Channel " + self.optionValues[0]

        return self.name


    def onAction(self, act, optionindex):
        self.onActionDigitBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 1000, 0)
        self.validateDigitBox(1, 1, 100, 1)
        self.validateDigitBox(2, 1, 100, 1)
        self.validateDigitBox(3, 1, 10000, 1)
        self.validateDigitBox(4, 1, 10000, 1)
        self.validateDigitBox(5, 1, 1, 1)


    def runAction(self, actionid, channelList, filelist):
        if actionid == RULES_ACTION_LIST:
            self.log("runAction")
            chan = 0
            minint = 0
            maxint = 0
            startingep = 0
            numbereps = 1
            startfrom = 1
            curchan = channelList.runningActionChannel
            curruleid = channelList.runningActionId
            self.validate()

            try:
                chan = int(self.optionValues[0])
                minint = int(self.optionValues[1])
                maxint = int(self.optionValues[2])
                startingep = int(self.optionValues[3])
                numbereps = int(self.optionValues[4])
                startfrom = int(self.optionValues[5])
            except:
                self.log("Except when reading params")

            if chan > channelList.maxChannels or chan < 1 or minint < 1 or maxint < 1 or startingep < 1 or numbereps < 1:
                return filelist

            if minint > maxint:
                v = minint
                minint = maxint
                maxint = v

            if len(channelList.channels) < chan or channelList.channels[chan - 1].isSetup == False:
                if channelList.myOverlay.isMaster:
                    channelList.setupChannel(chan, True, True, False)
                else:
                    channelList.setupChannel(chan, True, False, False)

            if channelList.channels[chan - 1].Playlist.size() < 1:
                self.log("The target channel is empty")
                return filelist

            if startfrom > 0:
                startfrom = 1
            else:
                startfrom = 0

            startfrom -= 1
            
            realindex = random.randint(minint, maxint)
            startindex = 0
            
            # Use more memory, but greatly speed up the process by just putting everything into a new list
            newfilelist = []
            self.log("Length of original list: " + str(len(filelist)))

            realindex += startfrom

            while realindex < len(filelist):
                if channelList.threadPause() == False:
                    return filelist

                while startindex < realindex:
                    newfilelist.append(filelist[startindex])
                    startindex += 1

                # Added FOR loop to iterate interleaving multiple-continuous episodes from chosen channel
                for i in range(numbereps):
                    newstr = str(channelList.channels[chan - 1].getItemDuration(startingep - 1)) + ','
                    newstr += channelList.channels[chan - 1].getItemTitle(startingep - 1) + "//" + channelList.channels[chan - 1].getItemEpisodeTitle(startingep - 1) + "//" + channelList.channels[chan - 1].getItemDescription(startingep - 1) + "//" + channelList.channels[chan - 1].getItemgenre(startingep - 1) + "//" + channelList.channels[chan - 1].getItemtimestamp(startingep - 1) + "//" + channelList.channels[chan - 1].getItemLiveID(startingep - 1)
                    newstr = uni(newstr)
                    newstr = newstr.replace("\\n", " ").replace("\\r", " ").replace("\\\"", "\"")
                    newstr = uni(newstr) + uni('\n') + uni(channelList.channels[chan - 1].getItemFilename(startingep - 1))                  
                    newfilelist.append(newstr)
                    # Moved startingep to FOR loop - otherwise it just adds the same file multiple times
                    startingep += 1        
                realindex += random.randint(minint, maxint)
                
    
            while startindex < len(filelist):
                newfilelist.append(filelist[startindex])
                startindex += 1
                
            startingep = channelList.channels[chan - 1].fixPlaylistIndex(startingep) + 1
            # Write starting episode
            self.optionValues[2] = str(startingep)
            ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_rule_' + str(curruleid + 1) + '_opt_4', self.optionValues[2])
            self.log("Done interleaving, new length is " + str(len(newfilelist)))
            return newfilelist
        return filelist


class ForceRealTime(BaseRule):
    def __init__(self):
        self.name = "Force Real-Time Mode"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 7
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return ForceRealTime()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode &= ~MODE_STARTMODES
            channeldata.mode |= MODE_REALTIME

        return channeldata



class AlwaysPause(BaseRule):
    def __init__(self):
        self.name = "Pause When Not Watching"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 8
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return AlwaysPause()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode |= MODE_ALWAYSPAUSE

        return channeldata


class ForceResume(BaseRule):
    def __init__(self):
        self.name = "Force Resume Mode"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 9
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return ForceResume()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode &= ~MODE_STARTMODES
            channeldata.mode |= MODE_RESUME

        return channeldata



class ForceRandom(BaseRule):
    def __init__(self):
        self.name = "Force Random Start"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 10
        self.actions = RULES_ACTION_BEFORE_TIME


    def copy(self):
        return ForceRandom()


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_BEFORE_TIME:
            channeldata.mode &= ~MODE_STARTMODES
            channeldata.mode |= MODE_RANDOM

        return channeldata



class OnlyUnWatchedRule(BaseRule):
    def __init__(self):
        self.name = "Only Play Unwatched Items"
        self.optionLabels = []
        self.optionValues = []
        self.myId = 11
        self.actions = RULES_ACTION_JSON


    def copy(self):
        return OnlyUnWatchedRule()


    def runAction(self, actionid, channelList, filedata):
        if actionid == RULES_ACTION_JSON:
            playcount = re.search('"playcount" *: *([0-9]*?),', filedata)
            pc = 0

            try:
                pc = int(playcount.group(1))
            except:
                pc = 0

            if pc > 0:
                return ''

        return filedata


class PlayShowInOrder(BaseRule):
    def __init__(self):
        self.name = "Play TV Shows In Order"
        self.optionLabels = []
        self.optionValues = []
        self.showInfo = []
        self.myId = 12
        self.actions = RULES_ACTION_START | RULES_ACTION_JSON | RULES_ACTION_LIST


    def copy(self):
        return PlayShowInOrder()


    def runAction(self, actionid, channelList, param):
        if actionid == RULES_ACTION_START:
            del self.showInfo[:]

        if actionid == RULES_ACTION_JSON:
            self.storeShowInfo(channelList, param)

        if actionid == RULES_ACTION_LIST:
            return self.sortShows(channelList, param)

        return param


    def storeShowInfo(self, channelList, filedata):
        # Store the filename, season, and episode number
        match = re.search('"file" *: *"(.*?)",', filedata)

        if match:
            showtitle = re.search('"showtitle" *: *"(.*?)"', filedata)
            season = re.search('"season" *: *(.*?),', filedata)
            episode = re.search('"episode" *: *(.*?),', filedata)

            try:
                seasonval = int(season.group(1))
                epval = int(episode.group(1))
                self.showInfo.append([showtitle.group(1), match.group(1).replace("\\\\", "\\"), seasonval, epval])
            except:
                pass


    def sortShows(self, channelList, filelist):
        if len(self.showInfo) == 0:
            return filelist

        newfilelist = []
        self.showInfo.sort(key=lambda seep: seep[3])
        self.showInfo.sort(key=lambda seep: seep[2])
        self.showInfo.sort(key=lambda seep: seep[0])

        # Create a new array. It will have 2 dimensions.  The first dimension is a certain show.  This show
        # name is in index 0 of the second dimension.  The currently used index is in index 1.  The other
        # items are the file names in season / episode order.
        showlist = []
        curshow = self.showInfo[0][0]
        showlist.append([])
        showlist[0].append(curshow.lower())
        showlist[0].append(0)

        for item in self.showInfo:
            if channelList.threadPause() == False:
                return filelist

            if item[0] != curshow:
                curshow = item[0]
                showlist.append([])
                showlist[-1].append(curshow.lower())
                showlist[-1].append(0)

            showstr = self.findInFileList(filelist, item[1])

            if len(showstr) > 0:
                showlist[-1].append(showstr)

        curindex = 0

        for item in filelist:
            if channelList.threadPause() == False:
                return filelist

            # First, get the current show for the entry
            pasttime = item.find(',')

            if pasttime > -1:
                endofshow = item.find("//")

                if endofshow > -1:
                    show = item[pasttime + 1:endofshow].lower()

                    for entry in showlist:
                        if entry[0] == show:
                            if len(entry) == 2:
                                break

                            filelist[curindex] = entry[entry[1] + 2]
                            entry[1] += 1

                            if entry[1] > (len(entry) - 3):
                                entry[1] = 0

                            break

            curindex += 1
        return filelist


    def findInFileList(self, filelist, text):
        text = text.lower()

        for item in filelist:
            tmpitem = item.lower()

            if tmpitem.find(text) > -1:
                return item

        return ''


class SetResetTime(BaseRule):
    def __init__(self):
        self.name = "Reset Every x Hours"
        self.optionLabels = ['Number of Hours']
        self.optionValues = ['24']
        self.myId = 13
        self.actions = RULES_ACTION_START
        

    def copy(self):
        return SetResetTime()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            if self.optionValues[0] == '1':
                return "Reset Every Hour"
            else:
                return "Reset Every " + self.optionValues[0] + " Hours"
        return self.name


    def onAction(self, act, optionindex):
        self.onActionDigitBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 50, '')


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_START:
            numhours = 0
            curchan = channeldata.channelNumber
            
            try:
                numhours = int(self.optionValues[0])
            except:
                pass

            if numhours <= 0:
                self.log("Invalid count: " + str(numhours))
                return channeldata

            rightnow = int(time.time())
            nextreset = rightnow

            try:
                nextreset = int(ADDON_SETTINGS.getSetting('Channel_' + str(curchan) + '_SetResetTime'))
            except:
                pass
                
            if rightnow >= nextreset:
                channeldata.isValid = False
                ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_changed', 'True')
                nextreset = rightnow + ((60 * 60 * numhours))
                ADDON_SETTINGS.setSetting('Channel_' + str(curchan) + '_SetResetTime', str(nextreset))

        return channeldata


class Handle3D(BaseRule):
    def __init__(self):
        self.name = "Include 3D Videos"
        self.optionLabels = ['Include 3D Videos']
        self.optionValues = ['Yes']
        self.myId = 19
        self.actions = RULES_ACTION_START | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED
        self.selectBoxOptions = [["Yes", "No"]]

        
    def copy(self):
        return Handle3D()


    def getTitle(self):
        if self.optionValues[0] == 'Yes':
            return 'Include 3D'
        else:
            return 'Exclude 3D'


    def onAction(self, act, optionindex):
        self.onActionSelectBox(act, optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_START:
            self.stored3dValue = channelList.inc3D
            self.log("Option for Handle3D is " + self.optionValues[0])

            if self.optionValues[0] == 'Yes':
                channelList.inc3D = True
            else:
                channelList.inc3D = False
        elif actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channelList.inc3D = self.stored3dValue

        return channeldata

        
class HandleIceLibrary(BaseRule):
    def __init__(self):
        self.name = "Include STRM Files"
        self.optionLabels = ['Include STRM Files']
        self.optionValues = ['Yes']
        self.myId = 14
        self.actions = RULES_ACTION_START | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED
        self.selectBoxOptions = [["Yes", "No"]]

        
    def copy(self):
        return HandleIceLibrary()


    def getTitle(self):
        if self.optionValues[0] == 'Yes':
            return 'Include STRM'
        else:
            return 'Exclude STRM'


    def onAction(self, act, optionindex):
        self.onActionSelectBox(act, optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_START:
            self.storedIceLibValue = channelList.incIceLibrary
            self.log("Option for HandleIceLibrary is " + self.optionValues[0])

            if self.optionValues[0] == 'Yes':
                channelList.incIceLibrary = True
            else:
                channelList.incIceLibrary = False
        elif actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channelList.incIceLibrary = self.storedIceLibValue
        
        return channeldata
                                  
                                  
class HandleMeta(BaseRule):
    def __init__(self):
        self.name = "Include Metadata"
        self.optionLabels = ['Include Metadata']
        self.optionValues = ['Yes']
        self.myId = 23
        self.actions = RULES_ACTION_START | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED
        self.selectBoxOptions = [["Yes", "No"]]

        
    def copy(self):
        return HandleMeta()


    def getTitle(self):
        if self.optionValues[0] == 'Yes':
            return 'Include Metadata'
        else:
            return 'Exclude Metadata'


    def onAction(self, act, optionindex):
        self.onActionSelectBox(act, optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_START:
            self.storedMetaValue = channelList.includeMeta
            self.log("Option for HandleMeta is " + self.optionValues[0])

            if self.optionValues[0] == 'Yes':
                channelList.includeMeta = True
            else:
                channelList.includeMeta = False
        elif actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channelList.includeMeta = self.storedMetaValue
        
        return channeldata
      
      
class HandleDurFilter(BaseRule):
    def __init__(self):
        self.name = "Duration Filter"
        self.optionLabels = ['Minimum Allowed Duration in seconds']
        self.optionValues = ['900']
        self.myId = 20
        self.actions = RULES_ACTION_START | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED

        
    def copy(self):
        return HandleDurFilter()


    def getTitle(self):
        if len(self.optionValues[0]) > 0:
            if int(self.optionValues[0]) > 0:        
                return "Exclude under " + self.optionValues[0] + "s"
            else:
                return "No Minimum Duration"
        return self.name
        
        
    def onAction(self, act, optionindex):
        self.onActionDigitBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 50, '')


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_START:
            self.storeddurFilter = channelList.durFilter
            self.log("Option for HandleDurFilter is " + str(self.optionValues[0]))
            channelList.durFilter = int(self.optionValues[0])
        
        elif actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channelList.durFilter = self.storeddurFilter
        return channeldata
        
class HandleBCT(BaseRule):
    def __init__(self):
        self.name = "Ignore BCT's"
        self.optionLabels = ["Include BCT's"]
        self.optionValues = ['Yes']
        self.myId = 17
        self.actions = RULES_ACTION_START | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED
        self.selectBoxOptions = [["Yes", "No"]]


    def copy(self):
        return HandleBCT()


    def getTitle(self):
        if self.optionValues[0] == 'Yes':
            return "Include BCT"
        else:
            return "Exclude BCT"


    def onAction(self, act, optionindex):
        self.onActionSelectBox(act, optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, channelList, channeldata):
        if actionid == RULES_ACTION_START:
            self.storedBCTValue = channelList.incBCTs
            self.log("Option for HandleBCT is " + self.optionValues[0])

            if self.optionValues[0] == 'Yes':
                channelList.incBCTs = True
            else:
                channelList.incBCTs = False
        elif actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channelList.incBCTs = self.storedBCTValue

        return channeldata
        
           
class HandlePOP(BaseRule):
    def __init__(self):
        self.name = 'Display Coming Up Next'
        self.optionLabels = ['Display Coming Up Next']
        self.optionValues = ['Yes']
        self.myId = 18
        self.actions = RULES_ACTION_OVERLAY_SET_CHANNEL | RULES_ACTION_OVERLAY_SET_CHANNEL_END
        self.selectBoxOptions = [["Yes", "No"]]


    def copy(self):
        return HandlePOP()


    def getTitle(self):
        if self.optionValues[0] == 'Yes':
            return 'Display ComingUp'
        else:
            return 'Hide ComingUp'


    def onAction(self, act, optionindex):
        self.onActionSelectBox(act, optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, overlay, channeldata):
        if actionid == RULES_ACTION_OVERLAY_SET_CHANNEL:
            self.storedPopValue = overlay.showNextItem

            if self.optionValues[0] == 'Yes':
                overlay.showNextItem = True
                self.log("setting comingup next to true")
            else:
                overlay.showNextItem = False
        elif actionid == RULES_ACTION_OVERLAY_SET_CHANNEL_END:
            overlay.showNextItem = self.storedPopValue
            self.log("set Coming Up Next to " + str(overlay.showNextItem))

        return channeldata
       
                    
class PinLock(BaseRule):
    def __init__(self):
        self.name = 'Channel PIN Lock '
        self.optionLabels = ['PIN Lock Channel', 'Set PIN']
        self.optionValues = ['No', '0000']
        self.myId = 22
        self.actions = RULES_ACTION_OVERLAY_SET_CHANNEL | RULES_ACTION_OVERLAY_SET_CHANNEL_END
        self.selectBoxOptions = [["Yes", "No"]]


    def copy(self):
        return PinLock()


    def getTitle(self):
        if self.optionValues[0] == 'Yes':
            return 'Channel locked'
        else:
            return 'Channel Unlocked'


    def onAction(self, act, optionindex):      
        if optionindex == 0:
            self.onActionSelectBox(act, optionindex)   
        if optionindex == 1:
            self.onActionDigitBox(act, optionindex)

        self.validate()
        return self.optionValues[optionindex]
        
        
    def validate(self):
        self.validateDigitBox(1, 4, 4, 0000)


    def runAction(self, actionid, overlay, channeldata):
        if actionid == RULES_ACTION_OVERLAY_SET_CHANNEL:
            if self.optionValues[0] == 'Yes':
                overlay.PinLocked = True
                overlay.PinNumber = self.optionValues[1]
                self.log("setting PIN lock to true")
            else:
                overlay.PinLocked = False
                overlay.PinNumber = '0000'
        elif actionid == RULES_ACTION_OVERLAY_SET_CHANNEL_END:
            overlay.PinLocked = False
            overlay.PinNumber = '0000'
            self.log("set PIN lock to " + str(overlay.PinLocked))

        return channeldata
       
        
class HandleChannelLogo(BaseRule):
    def __init__(self):
        self.name = "Display Channel Logo"
        self.optionLabels = ['Display the Logo']
        self.optionValues = ['Yes']
        self.myId = 15
        self.actions = RULES_ACTION_OVERLAY_SET_CHANNEL | RULES_ACTION_OVERLAY_SET_CHANNEL_END
        self.selectBoxOptions = [["Yes", "No"]]


    def copy(self):
        return HandleChannelLogo()


    def getTitle(self):
        if self.optionValues[0] == 'Yes':
            return 'Display Channel Logo'
        else:
            return 'Hide Channel Logo'


    def onAction(self, act, optionindex):
        self.onActionSelectBox(act, optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, overlay, channeldata):
        if actionid == RULES_ACTION_OVERLAY_SET_CHANNEL:
            self.storedLogoValue = overlay.showChannelBug

            if self.optionValues[0] == 'Yes':
                overlay.showChannelBug = True
                self.log("setting channel bug to true")
            else:
                overlay.showChannelBug = False
        elif actionid == RULES_ACTION_OVERLAY_SET_CHANNEL_END:
            overlay.showChannelBug = self.storedLogoValue
            self.log("set channel bug to " + str(overlay.showChannelBug))
        return channeldata


class EvenShowsRule(BaseRule):
    def __init__(self):
        self.name = "Even Show Distribution"
        self.optionLabels = ['Same Show Eps in a Row']
        self.optionValues = ['2']
        self.myId = 16
        self.actions = RULES_ACTION_LIST


    def copy(self):
        return EvenShowsRule()


    def getTitle(self):
        return self.name


    def onAction(self, act, optionindex):
        self.onActionDigitBox(act, optionindex)
        self.validate()
        return self.optionValues[optionindex]


    def validate(self):
        self.validateDigitBox(0, 1, 20, 1)


    def runAction(self, actionid, channelList, filelist):
        if actionid == RULES_ACTION_LIST:
            self.validate()
            
            opt = int(self.optionValues[0]) + 1
            self.log("Allowed shows in a row: " + str(opt))
            lastshow = ''
            realindex = 0
            inarow = 0

            for index in range(len(filelist)):
                try:
                    item = filelist[index]
                    self.log("index " + str(index) + " is " + item)
                    loc = item.find(',')

                    if loc > -1:
                        loc2 = item.find("//")

                        if loc2 > -1:
                            showname = item[loc + 1:loc2]
                            showname = showname.lower()
                            self.log("showname is " + showname)
                                    
                            if showname == lastshow:
                                inarow += 1
                                self.log("same show now at " + str(inarow))
                                
                                if inarow >= opt:
                                    nextline = self.insertNewShow(filelist, lastshow, index)
                                    
                                    if nextline == '':
                                        filelist = filelist[:index]
                                        return filelist
                                    else:
                                        filelist.insert(index, nextline)
                                        lastshow = ''
                            else:
                                lastshow = showname
                                self.log("new show: " + lastshow)
                                inarow = 0
                except:
                    pass
        return filelist
        
        
    def insertNewShow(self, filelist, lastshow, startindex):
        self.log("insertNewShow: " + str(startindex) + ", " + str(len(filelist)))
        for index in range(startindex + 1, len(filelist)):
            item = filelist[index]
            self.log("insertNewShow index " + str(index) + " is " + item)
            loc = item.find(',')

            if loc > -1:
                loc2 = item.find("//")

                if loc2 > -1:
                    showname = item[loc + 1:loc2]
                    showname = showname.lower()

                    if showname != lastshow:
                        self.log("insertNewShow found " + showname)
                        filelist.pop(index)
                        return item         
        return ''
                   
class HandleSeek(BaseRule):
    def __init__(self):
        self.name = 'Disable Real-Time'
        self.optionLabels = ['Disable Real-Time offsets']
        self.optionValues = ['Yes']
        self.myId = 21
        self.actions = RULES_ACTION_OVERLAY_SET_CHANNEL | RULES_ACTION_OVERLAY_SET_CHANNEL_END
        self.selectBoxOptions = [["Yes", "No"]]


    def copy(self):
        return HandleSeek()


    def getTitle(self):
        if self.optionValues[0] == 'Yes':
            return 'Disable RealTime'
        else:
            return 'Allow RealTime'


    def onAction(self, act, optionindex):
        self.onActionSelectBox(act, optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, overlay, channeldata):
        if actionid == RULES_ACTION_OVERLAY_SET_CHANNEL:
            self.storedSeekValue = overlay.ignoreSeektime

            if self.optionValues[0] == 'Yes':
                overlay.ignoreSeektime = True
                self.log("setting comingup next to true")
            else:
                overlay.ignoreSeektime = False
        elif actionid == RULES_ACTION_OVERLAY_SET_CHANNEL_END:
            overlay.ignoreSeektime = self.storedSeekValue
            self.log("set Coming Up Next to " + str(overlay.ignoreSeektime))

        return channeldata
       