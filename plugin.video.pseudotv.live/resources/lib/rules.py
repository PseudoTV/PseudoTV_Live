#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
from resources.lib.globals import *

def listTitle(list):
     return [item.title() for item in list]
 
class RulesList:
    def __init__(self):
        self.ruleList = [BaseRule(),HandleMethodOrder(),HandleFilter()]


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
        if act.getId() == ACTION_SELECT_ITEM:
            keyb = xbmc.Keyboard(self.optionValues[optionindex], self.name, False)
            keyb.doModal()

            if keyb.isConfirmed():
                self.optionValues[optionindex] = keyb.getText()
        button = act.getButtonCode()

        # Upper-case values
        if button >= 0x2f041 and button <= 0x2f05b:
            self.optionValues[optionindex] += chr(button - 0x2F000)

        # Lower-case values
        if button >= 0xf041 and button <= 0xf05b:
            self.optionValues[optionindex] += chr(button - 0xEFE0)

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

        # Space
        if button == 0xF020:
            self.optionValues[optionindex] += ' '

        if xbmc.getCondVisibility("Window.IsVisible(10111)"):
            log("shutdown window is visible")
            xbmc.executebuiltin("Dialog.close(10111)")


    def onActionDateBox(self, act, optionindex):
        log("onActionDateBox")
        if act.getId() == ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            info = dlg.numeric(1, self.optionLabels[optionindex], self.optionValues[optionindex])

            if info != None:
                self.optionValues[optionindex] = info


    def onActionTimeBox(self, act, optionindex):
        log("onActionTimeBox")
        action = act.getId()

        if action == ACTION_SELECT_ITEM:
            dlg = xbmcgui.Dialog()
            info = dlg.numeric(2, self.optionLabels[optionindex], self.optionValues[optionindex])

            if info != None:
                if info[0] == ' ':
                    info = info[1:]

                if len(info) == 4:
                    info = "0" + info
                self.optionValues[optionindex] = info
        button = act.getButtonCode()

        # Numbers
        if action >= ACTION_NUMBER_0 and action <= ACTION_NUMBER_9:
            value = action - ACTION_NUMBER_0
            length = len(self.optionValues[optionindex])

            if length == 0:
                if value <= 2:
                    self.optionValues[optionindex] = chr(value + 48)
            elif length == 1:
                if int(self.optionValues[optionindex][0]) == 2:
                    if value < 4:
                        self.optionValues[optionindex] += chr(value + 48)
                else:
                    self.optionValues[optionindex] += chr(value + 48)
            elif length == 2:
                if value < 6:
                    self.optionValues[optionindex] += ":" + chr(value + 48)
            elif length < 5:
                self.optionValues[optionindex] += chr(value + 48)

        # Backspace
        if button == 0xF008:
            if len(self.optionValues[optionindex]) >= 1:
                if len(self.optionValues[optionindex]) == 4:
                    self.optionValues[optionindex] = self.optionValues[optionindex][:-1]

                self.optionValues[optionindex] = self.optionValues[optionindex][:-1]


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

                
    def onActionSingleSelect(self, act, optionindex, header=ADDON_NAME, psel=-1):
        log("onActionSingleSelect")
        if act.getId() in ACTION_SELECT_ITEM:
            info = xbmcgui.Dialog().select(header, self.selectBoxOptions[optionindex], preselect=psel)
            if info > -1: self.optionValues[optionindex] = self.selectBoxOptions[optionindex][info]
                
                
    def onActionBrowse(self, act, optionindex, header=ADDON_NAME, multi=False, type=0, shares='', mask='', useThumbs=True, treatAsFolder=False, default='', prompt=False):
        log("onActionBrowse")
        if act.getId() == ACTION_SELECT_ITEM:
            info = browseDialog(multi, type, header, shares, mask, useThumbs, treatAsFolder, default, prompt)
            if len(info) > -1: 
                self.optionValues[optionindex] = info 
                     
                
    def onActionSelectBox(self, act, optionindex):
        if act.getId() == ACTION_SELECT_ITEM:
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
        log("onActionDaysofWeekBox")

        if act.getId() == ACTION_SELECT_ITEM:
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
            log("shutdown window is visible")
            xbmc.executebuiltin("Dialog.close(10111)")


    def validateDaysofWeekBox(self, optionindex):
        log("validateDaysofWeekBox")
        daysofweek = "UMTWHFS"
        newstr = ''

        for day in daysofweek:
            loc = self.optionValues[optionindex].find(day)

            if loc != -1:
                newstr += day
        self.optionValues[optionindex] = newstr


    def validateRange(self, optionindex, minimum, maximum, default):
        if int(self.optionValues[optionindex]) < minimum:
            log("Invalid minimum range")
            self.optionValues[optionindex] = str(default)
            return
        elif int(self.optionValues[optionindex]) > maximum:
            log("Invalid maximum range")
            self.optionValues[optionindex] = str(default)
            return


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
        if action == ACTION_SELECT_ITEM:
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

                
    def onActionSelectDialog(self, act, optionindex, header=ADDON_NAME, psel=-1):
        if act.getId() == ACTION_SELECT_ITEM:
            info = xbmcgui.Dialog().select(header, self.selectBoxOptions[optionindex], preselect=psel)
            if info > -1: self.optionValues[optionindex] = self.selectBoxOptions[optionindex][info]
                
                       
class HandleMethodOrder(BaseRule):
    def __init__(self):
        self.name = "Limit & Sort Methods"
        self.optionLabels = ['Limit','Method','Order','Ignore Folders']
        self.optionValues = ['25', 'Random','Ascending','False']
        self.myId = 19
        self.actions = RULES_ACTION_START | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED
        self.selectBoxOptions = [PAGE_LIMIT, sorted(listTitle(JSON_METHOD)), sorted(listTitle(JSON_ORDER)), ['True', 'False']]

        
    def copy(self):
        return HandleMethodOrder()


    def getTitle(self):
        return self.name


    def onAction(self, act, optionindex):
        if optionindex == 1:
            focus = [idx for idx, item in enumerate(self.selectBoxOptions[optionindex]) if item.title() == self.optionValues[optionindex].title()][0]
            self.onActionSelectDialog(act, optionindex, 'Select Sort Method', focus)
        else:
            self.onActionSelectBox(act, optionindex)
        if isinstance(self.optionValues[optionindex], (basestring, unicode)):
            return self.optionValues[optionindex].title()
        return self.optionValues[optionindex]


    def runAction(self, actionid, channelList, channeldata):
        #"sort": {"order": "ascending", "ignorefolders": "false", "method": "random"}
        if actionid == RULES_ACTION_START:
            self.storedLimitValue = channelList.mediaLimit
            self.storedSortValue = channelList.fileListSort
            sort = {"method": self.optionValues[0].lower(), "order": self.optionValues[1].lower(), "ignorefolders": (self.optionValues[2] == "True")}
            log("Option for HandleMethodOrder is Method = " + self.optionValues[0] + " Order = " + self.optionValues[1]+ " Ignore = " + str(self.optionValues[2]))
            for i in range(len(self.optionValues)):
                if len(self.optionValues[i]) == 0:
                    return channeldata
            channelList.mediaLimit =  int(self.optionValues[0])
            channelList.fileListSort = sort
        elif actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channelList.mediaLimit  = self.storedLimitValue
            channelList.fileListSort  = self.storedSortValue
        return channeldata


class HandleFilter(BaseRule):
    def __init__(self):
        self.name = "Filter Content"
        self.myId = 20
        self.actions = RULES_ACTION_START | RULES_ACTION_FINAL_MADE | RULES_ACTION_FINAL_LOADED
        self.optionLabels     = ['Field','Operator','Value']
        self.optionValues     = ['Showtitle','Contains','']
        self.selectBoxOptions = [sorted(listTitle(JSON_FILES)), sorted(listTitle(JSON_OPERATORS))]
        

    def copy(self): 
        return HandleFilter()
        
        
    def getTitle(self): 
        return self.name
        
        
    def onAction(self, act, optionindex):
        if optionindex == 2:
            self.onActionTextBox(act, optionindex)
            self.validate()
        else: 
            items = [item.title() for item in self.selectBoxOptions[optionindex]]
            focus = [idx for idx, item in enumerate(self.selectBoxOptions[optionindex]) if item.title() == self.optionValues[optionindex].title()][0]
            self.onActionSelectDialog(act, optionindex, 'Select Filter %s'%(self.optionLabels[optionindex]), focus)
        if isinstance(self.optionValues[optionindex], (basestring, unicode)):
            return self.optionValues[optionindex].title()
        return self.optionValues[optionindex]
        
        
    def validate(self): 
        self.validateTextBox(0, 240)


    def runAction(self, actionid, channelList, channeldata):
        #"filter": {"and": [{"operator": "contains", "field": "title", "value": "Star Wars"}, {"operator": "contains", "field": "tag", "value": "Good"}]}
        if actionid == RULES_ACTION_START: 
            self.storedFilterValue = channelList.fileListFilter
            filter = {"field": self.optionValues[0].lower(), "operator": self.optionValues[1].lower(), "value": urllib.quote((self.optionValues[2]))}
            log("Filter for HandleFilter is = " + str(filter))
            for i in range(len(self.optionValues)):
                if len(self.optionValues[i]) == 0:
                    return channeldata
            channelList.fileListFilter = filter
        elif actionid == RULES_ACTION_FINAL_MADE or actionid == RULES_ACTION_FINAL_LOADED:
            channelList.fileListFilter = self.storedFilterValue
        return channeldata  
        
        
        
        
        
        
        
            # def loadRules(self, channelID):
        # ruleList  = []
        # listrules = RulesList()
        # try:
            # rulecount = int(getSetting('Channel_%s_rulecount'%(channelID)))
            # for i in range(rulecount):
                # ruleid = int(getSetting('Channel_%s_rule_%s_id'%(channelID,i + 1)))

                # for rule in listrules.ruleList:
                    # if rule.getId() == ruleid:
                        # ruleList.append(rule.copy())

                        # for x in range(rule.getOptionCount()):
                            # ruleList[-1].optionValues[x] = getSetting('Channel_%s_rule_%s_opt_%s'%(channelID,i + 1,x + 1))
                        # break
        # except: ruleList = []
        # return ruleList
        
                