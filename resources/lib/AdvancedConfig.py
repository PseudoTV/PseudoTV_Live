#   Copyright (C) 2015 Jason Anderson, Kevin S. Graer
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
import subprocess, os, sys, re, random
import datetime, time, threading

from Globals import *
from utils import *
from Rules import *
from ChannelList import ChannelList

class AdvancedConfig(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.log("__init__")
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.ruleList = []
        self.allRules = RulesList()

        
    def log(self, msg, level = xbmc.LOGDEBUG):
        log('AdvancedConfig: ' + msg, level)


    def onInit(self):
        self.log("onInit")
        self.listOffset = 0
        self.lineSelected = 0
        self.optionRowOffset = 0
        self.optionRowSelected = 0
        self.selectedRuleIndex = -1
        self.makeList()
        self.wasSaved = False
        self.log("onInit return")


    def onFocus(self, controlId):
        pass


    def onAction(self, act):
        action = act.getId()
        self.log("onAction " + str(action))
        focusid = 0

        try:
            focusid = self.getFocusId()
            self.log("focus id is " + str(focusid))
        except Exception,e:
            pass

        if focusid >= 160:
            self.getControl(focusid).setLabel(self.ruleList[self.selectedRuleIndex].onAction(act, (focusid - 160) + (self.optionRowOffset * 2)))

        if action in ACTION_PREVIOUS_MENU:
            if self.selectedRuleIndex > -1:
                xbmc.executebuiltin("SetProperty(itempress,100)")
                self.lineSelected = 0
                self.onClick(130)
            else:
                if xbmcgui.Dialog().yesno("Save", "Would you like to save your changes?"):
                    self.saveRules()
                self.close()
            xbmc.sleep(25)
            if getProperty("PTVL.showingList") == 'True':
                xbmc.executebuiltin("Control.SetFocus(102)")
            else:
                xbmc.executebuiltin("Control.SetFocus(112)")
                
        elif action in ACTION_MOVE_DOWN:
            if focusid > 119 and focusid < (120 + RULES_PER_PAGE):
                # If we highlighted the last rule previously and are now pressing arrow down
                if (focusid == (119 + RULES_PER_PAGE)) and (self.lineSelected == (RULES_PER_PAGE - 1)):
                    curoffset = self.listOffset
                    self.scrollDownList()

                    if self.listOffset != curoffset:
                        xbmc.executebuiltin("Control.SetFocus(" + str(119 + RULES_PER_PAGE) + ")")
                else:
                    self.lineSelected = focusid - 120
            elif (focusid >= 160) and (focusid < 164):
                self.log("Down on option")

                if focusid > 161:
                    if self.optionRowSelected == 1:
                        self.scrollOptionsDown()

                        # If we're actually offset, then make sure that the top options don't have a
                        # control-up value
                        if self.optionRowOffset > 0:
                            self.getControl(160).controlUp(self.getControl(160))
                            self.getControl(161).controlUp(self.getControl(161))
                    else:
                        self.optionRowSelected = 1
                        
        elif action in ACTION_MOVE_UP:
            if focusid > 119 and focusid < (120 + RULES_PER_PAGE):
                # If we highlighted the last rule previously and are now pressing arrow down
                if (focusid == 120) and (self.lineSelected == 0):
                    curoffset = self.listOffset
                    self.scrollUpList()

                    if self.listOffset != curoffset:
                        xbmc.executebuiltin("Control.SetFocus(120)")
                else:
                    self.lineSelected = focusid - 120
            elif (focusid >= 160) and (focusid < 164):
                if focusid < 162:
                    if self.optionRowSelected == 0:
                        self.scrollOptionsUp()

                        # If we're not offset, make sure that the top options have a
                        # control-up value
                        if self.optionRowOffset == 0:
                            self.getControl(160).controlUp(self.getControl(131))
                            self.getControl(161).controlUp(self.getControl(131))
                    else:
                        self.optionRowSelected = 0
                        
        elif action in ACTION_MOVE_LEFT:
            try:
                if self.getFocusId() == 131:
                    self.scrollRulesLeft()
            except Exception,e:
                pass
                
        elif action in ACTION_MOVE_RIGHT:
            try:
                if self.getFocusId() == 131:
                    self.scrollRulesRight()
            except Exception,e:
                pass


    def scrollOptionsUp(self):
        self.log("scrollOptionsUp")

        if self.optionRowOffset == 0:
            return

        self.optionRowOffset -= 1
        self.setupOptions()


    def scrollOptionsDown(self):
        self.log("scrollOptionsDown")
        allowedrows = (self.ruleList[self.selectedRuleIndex].getOptionCount() / 2) + (self.ruleList[self.selectedRuleIndex].getOptionCount() % 2)

        if allowedrows <= (self.optionRowOffset + 2):
            return

        self.optionRowOffset += 1
        self.setupOptions()


    def setupOptions(self):
        self.log("setupOptions")
        self.getControl(102).setVisible(False)
        optcount = self.ruleList[self.selectedRuleIndex].getOptionCount()

        try:
            arrowup = self.getControl(170)
            arrowdown = self.getControl(171)

            if (optcount > 4) and (optcount > (4 + (self.optionRowOffset * 2))):
                arrowup.setVisible(True)
            else:
                arrowup.setVisible(False)

            if self.optionRowOffset > 0:
                arrowdown.setVisible(True)
            else:
                arrowdown.setVisible(False)
        except Exception,e:
            pass

        for i in range(4):
            if i < (optcount - (self.optionRowOffset * 2)):
                self.getControl(i + 150).setVisible(True)
                self.getControl(i + 150).setLabel(self.ruleList[self.selectedRuleIndex].getOptionLabel(i + (self.optionRowOffset * 2)))
                self.getControl(i + 160).setVisible(True)
                self.getControl(i + 160).setEnabled(True)
                self.getControl(i + 160).setLabel(self.ruleList[self.selectedRuleIndex].getOptionValue(i + (self.optionRowOffset * 2)))
            else:
                self.getControl(i + 150).setVisible(False)
                self.getControl(i + 160).setVisible(False)

        self.getControl(102).setVisible(True)

        
    def scrollRulesLeft(self):
        self.log("scrollRulesLeft")

        if self.selectedRuleIndex >= 0:
            curid = self.ruleList[self.selectedRuleIndex].getId()

            for i in range(self.allRules.getRuleCount()):
                if self.allRules.getRule(i).getId() == curid:
                    self.ruleList[self.selectedRuleIndex] = self.allRules.getRule(i - 1).copy()
                    break

            self.setRuleControls(self.selectedRuleIndex - self.listOffset)


    def scrollRulesRight(self):
        self.log("scrollRulesRight")

        if self.selectedRuleIndex >= 0:
            curid = self.ruleList[self.selectedRuleIndex].getId()

            for i in range(self.allRules.getRuleCount()):
                if self.allRules.getRule(i).getId() == curid:
                    self.ruleList[self.selectedRuleIndex] = self.allRules.getRule(i + 1).copy()
                    break

            self.setRuleControls(self.selectedRuleIndex - self.listOffset)


    def saveRules(self):
        self.wasSaved = True


    def scrollDownList(self):
        if len(self.ruleList) > self.listOffset + (RULES_PER_PAGE - 1):
            self.listOffset += 1
            self.makeList()


    def scrollUpList(self):
        if self.listOffset > 0:
            self.listOffset -= 1
            self.makeList()


    def makeList(self):
        self.log("makeList")

        if self.listOffset + (RULES_PER_PAGE - 1) > len(self.ruleList):
            self.listOffset = len(self.ruleList) - (RULES_PER_PAGE - 1)

        if self.listOffset < 0:
            self.listOffset = 0

        for i in range(RULES_PER_PAGE):
            if self.listOffset + i < len(self.ruleList):
                self.getControl(120 + i).setLabel(str(i + 1 + self.listOffset) + ". " + self.ruleList[i + self.listOffset].getTitle())
                self.getControl(120 + i).setEnabled(True)

                if i < (RULES_PER_PAGE - 1):
                    self.getControl(120 + i).controlDown(self.getControl(121 + i))

                if i > 0:
                    self.getControl(120 + i).controlUp(self.getControl(119 + i))
            else:
                if self.listOffset + i == len(self.ruleList):
                    self.getControl(120 + i).setLabel(str(i + 1 + self.listOffset) + ".")
                    self.getControl(120 + i).controlDown(self.getControl(120 + i))
                    self.getControl(120 + i).setEnabled(True)

                    if i > 0:
                        self.getControl(120 + i).controlUp(self.getControl(119 + i))
                else:
                    self.getControl(120 + i).setLabel('')
                    self.getControl(120 + i).setEnabled(False)

        self.log("makeList return")


    def getRuleName(self, ruleindex):
        self.log("getRuleName")
        if ruleindex < 0 or ruleindex >= len(self.ruleList):
            return ""

        return self.ruleList[ruleindex].getName()


    def onClick(self, controlId):
        self.log("onClick " + str(controlId))

        if controlId >= 120 and controlId <= (119 + RULES_PER_PAGE):
            self.optionRowSelected = 0
            self.optionRowOffset = 0
            self.setRuleControls(controlId - 120)
            self.getControl(160).controlUp(self.getControl(131))
            self.getControl(161).controlUp(self.getControl(131))
        elif controlId == 130:
            self.listOffset = self.selectedRuleIndex - 1
            self.selectedRuleIndex = -1
            self.consolidateRules()
            self.makeList()


    def consolidateRules(self):
        self.log("consolidateRules")
        index = 0

        for i in range(len(self.ruleList)):
            if index >= len(self.ruleList):
                break

            if self.ruleList[index].getId() == 0:
                self.ruleList.pop(index)
            else:
                index += 1

        self.log("count is " + str(len(self.ruleList)))


    def setRuleControls(self, listindex):
        self.log("setRuleControls")
        self.selectedRuleIndex = listindex + self.listOffset
        self.getControl(130).setLabel("Rule " + str(self.selectedRuleIndex + 1) + " Configuration")

        if self.selectedRuleIndex >= len(self.ruleList):
            self.ruleList.append(BaseRule())

        strlen = len(self.getRuleName(self.selectedRuleIndex))
        spacesstr = ''

        for i in range(20 - strlen / 2):
            spacesstr += ' '

        self.getControl(131).setLabel('<-' + spacesstr + self.getRuleName(self.selectedRuleIndex) + spacesstr + '->')
        self.setupOptions()
