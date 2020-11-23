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

class RulesList:
    def __init__(self):
        self.ruleList = [BaseRule(),
                         HandleMethodOrder(),
                         HandleFilter(),
                         SeekLock()]


    def getRitem(self):
        ritem = {"id":0,
                 "name":"",
                 "description":"",
                 "options":{},
                 "action":""}
        return ritem.copy()


    def getRuleCount(self):
        return len(self.ruleList)


    def getRule(self, index):
        while index < 0:
            index += len(self.ruleList)
        while index >= len(self.ruleList):
            index -= len(self.ruleList)
        return self.ruleList[index]


    def loadRuleActions(self, rules):
        actions = self.getRuleTypes()
        for rule in rules:
            for action in actions:
                if rule.get('id') == action.get('id'):
                    rule['action'] = action['action']
            

    def getRuleTypes(self):
        return sorted(self.buildRuleTypes(), key=lambda k: k['id'])


    def buildRuleTypes(self): #Build all default rule types
        rules = self.ruleList
        rbase = rules.pop(0) #remove base example.
        for rule in rules:
            ritem = self.getRitem()
            ritem.update({'id':rule.getId(),'name':rule.getTitle(),'description':rule.getDesc(),'options':{},'action':rule.copy()})
            for opt in range(rule.getOptionCount()):
                ritem['options'][str(opt)] = {'label':rule.getOptionLabel(opt),'value':rule.getOptionValue(opt)}
            yield ritem


    # def addChannelRule(self, citem, ritem):
        # if channelkey is None:
            # channels = self.getChannels()
        # log('ruleList: addChannelRule, id = %s, rule = %s'%(citem['id'],ritem))
        # rules = self.getChannelRules(citem, channelkey)
        # idx, rule = self.findChannelRule(citem, ritem, channelkey)
        # if idx is None:
            # rules.append(ritem)
        # else:
            # rules[idx].update(ritem)
        # self.channelList['channels']['rules'] = sorted(rules, key=lambda k: k['id'])
        # return True




    # def findChannelRule(self, citem, ritem):
        # if channelkey is None:
            # channels = self.getChannels()
        # log('Channels: findChannelRule, id = %s, rule = %s'%(citem['id'],ritem))
        # rules = self.getChannelRules(citem,channels)
        # for idx, rule in enumerate(rules):
            # if rule['id'] == ritem['id']:
                # return idx, rule
        # return None, {}
        
 
class BaseRule:
    def __init__(self):
        self.name         = ""
        self.description  = ""
        self.optionLabels = []
        self.optionValues = []
        self.myId         = 0
        self.actions      = 0


    def getTitle(self):
        return self.name
        
        
    def getDesc(self):
        return self.description


    def getOptionCount(self):
        return len(self.optionLabels)


    def onAction(self, optionindex):
        return ''


    def getOptionLabel(self, index):
        if index >= 0 and index < self.getOptionCount():
            return self.optionLabels[index]
        return ''


    def getOptionValue(self, index):
        if index >= 0 and index < len(self.optionValues):
            return self.optionValues[index]
        return ''


    def getselectBoxOptions(self, index):
        if index >= 0 and index < len(self.selectBoxOptions):
            return self.selectBoxOptions[index]
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


    def runAction(self, actionid, Builder, param):
        return param


    def copy(self):
        return BaseRule()


    def log(self, msg, level = xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)


    def validate(self):
        pass


    def reset(self):
        self.__init__()


    def validateTextBox(self, optionindex, length):
        if len(self.optionValues[optionindex]) > length:
            self.optionValues[optionindex] = self.optionValues[optionindex][:length]


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


    def validateDaysofWeekBox(self, optionindex):
        log("validateDaysofWeekBox")
        daysofweek = "UMTWHFS"
        newstr = ''
        for day in daysofweek:
            loc = self.optionValues[optionindex].find(day)
            if loc != -1: newstr += day
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
        if len(self.optionValues[optionindex]) == 0: return

        try:
            val = int(self.optionValues[optionindex])
            if val >= minimum and val <= maximum:
                self.optionValues[optionindex] = str(val)
            return
        except: pass
        self.optionValues[optionindex] = str(default)

   
    def onActionToggleBool(self, optionindex):
        log("onActionToggleBool")
        self.optionValues[optionindex] = not self.optionValues[optionindex]


    def onActionTextBox(self, optionindex):
        value = inputDialog(self.name, default=self.optionValues[optionindex], key=xbmcgui.INPUT_ALPHANUM)
        if value: self.optionValues[optionindex] = value
        

    def onActionDateBox(self, optionindex):
        log("onActionDateBox")
        info =  inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)
        if info != None: self.optionValues[optionindex] = info


    def onActionTimeBox(self, optionindex):
        log("onActionTimeBox")
        info = inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)
        if info != None:
            if info[0] == ' ': info = info[1:]
            if len(info) == 4: info = "0" + info
            self.optionValues[optionindex] = info


    def onActionSelect(self, optionindex, header=ADDON_NAME, psel=-1, multi=False):
        log("onActionSelect")
        if psel < 0:
            psel = [idx for idx, item in enumerate(self.selectBoxOptions[optionindex]) if item == self.optionValues[optionindex]]
            if not multi: psel = (psel[0] or -1)
        select = selectDialog(titleLabels(self.selectBoxOptions[optionindex]), header, preselect=psel, useDetails=False, multi=multi)
        if select is not None: self.optionValues[optionindex] = self.selectBoxOptions[optionindex][select]
                
          
    def onActionBrowse(self, optionindex, header=ADDON_NAME, multi=False, type=0, shares='', mask='', useThumbs=True, treatAsFolder=False, default='', prompt=False):
        log("onActionBrowse")
        info = browseDialog(yype, header, default, shares, mask, None, useThumbs, treatAsFolder, prompt, multi, monitor=False)
        if info is not None: self.optionValues[optionindex] = info 
                     
                
    def onActionSelectBox(self, optionindex):
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


    def onActionDaysofWeekBox(self, optionindex):
        log("onActionDaysofWeekBox")
        value = inputDialog(self.name, default=self.optionValues[optionindex], key=xbmcgui.INPUT_ALPHANUM)
        if value: self.optionValues[optionindex] = value.upper()


    def onActionDigitBox(self, optionindex):
        self.optionValues[optionindex] = inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)


class HandleMethodOrder(BaseRule):
    def __init__(self):
        self.myId             = 1
        self.name             = "Limits & Sort Methods"
        self.description      = ""
        self.optionLabels     = ['Page Limit','Method','Order','Ignore Folders']
        self.optionValues     = [PAGE_LIMIT, 'random','ascending',False]
        self.actions          = RULES_ACTION_CHANNEL_START | RULES_ACTION_CHANNEL_STOP
        self.selectBoxOptions = [[n for n in range(25, 275, 25)], sorted(JSON_METHOD), sorted(JSON_ORDER), [True, False]]

        
    def copy(self):
        return HandleMethodOrder()


    def getTitle(self):
        return self.name


    def onAction(self, optionindex):
        if optionindex == 3:
            self.onActionToggleBool(optionindex)
        else:
            self.onActionSelect(optionindex, LANGUAGE(30144)%(self.optionLabels[optionindex]))
        return self.optionValues[optionindex]


    def runAction(self, actionid, Builder, channeldata):
        #"sort": {"order": "ascending", "ignorefolders": "false", "method": "random"}
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedLimitValue = Builder.mediaLimit
            self.storedSortValue  = Builder.fileListSort
            sort = {"method": self.optionValues[0].lower(), "order": self.optionValues[1].lower(), "ignorefolders": int(self.optionValues[2] == True)}
            log("HandleMethodOrder sort = %s"%(sort))
            for value in self.optionValues:
                if len(value) == 0:
                    return channeldata
            Builder.mediaLimit   = self.optionValues[0]
            Builder.fileListSort = sort
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            Builder.mediaLimit    = self.storedLimitValue
            Builder.fileListSort  = self.storedSortValue
        return channeldata


class HandleFilter(BaseRule):
    def __init__(self):
        self.myId             = 2
        self.name             = "Filter Content"
        self.description      = ""
        self.actions          = RULES_ACTION_CHANNEL_START | RULES_ACTION_CHANNEL_STOP
        self.optionLabels     = ['Field','Operator','Value']
        self.optionValues     = ['showtitle','contains','']
        self.selectBoxOptions = [sorted(JSON_FILE_ENUM), sorted(JSON_OPERATORS)]
        

    def copy(self): 
        return HandleFilter()
        
        
    def getTitle(self): 
        return self.name
        
        
    def onAction(self, optionindex):
        if optionindex == 2:
            self.onActionTextBox(optionindex)
        else: 
            self.onActionSelect(optionindex, 'Select Filter %s'%(self.optionLabels[optionindex]))
        self.validate(optionindex)
        return self.optionValues[optionindex]
        
        
    def validate(self, optionindex):
        if optionindex == 2:
            self.validateTextBox(0, 240)


    def runAction(self, actionid, Builder, channeldata):
        #"filter": {"and": [{"operator": "contains", "field": "title", "value": "Star Wars"}, {"operator": "contains", "field": "tag", "value": "Good"}]}
        if actionid == RULES_ACTION_CHANNEL_START: 
            self.storedFilterValue = Builder.fileListFilter
            filter = {"field": self.optionValues[0].lower(), "operator": self.optionValues[1].lower(), "value": urllib.quote((self.optionValues[2]))}
            log("Filter for HandleFilter is = " + str(filter))
            for i in range(len(self.optionValues)):
                if len(self.optionValues[i]) == 0:
                    return channeldata
            Builder.fileListFilter = filter
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            Builder.fileListFilter = self.storedFilterValue
        return channeldata
           
               
class SeekLock(BaseRule):
    def __init__(self):
        self.myId         = 20
        self.name         = "Disable Seeking"
        self.description  = ''
        self.optionLabels = ['Disable Seeking']
        self.optionValues = [False]
        self.actions = RULES_ACTION_PLAYBACK
        self.selectBoxOptions = [[False,True]]
        

    def copy(self):
        return SeekLock()


    def getTitle(self):
        if self.optionValues[0]:
            return 'Seeking Disabled'
        else: 
            return 'Seeking Enabled'
            

    def onAction(self, act, optionindex):
        self.onActionSelectBox(act, optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, Channels, nowitem):
        if actionid == RULES_ACTION_PLAYBACK:
            self.log("setting Seek Lock to %s"%(self.optionValues[0]))
            nowitem['progress'] = 0
        return nowitem        
               
               
class UPNP(BaseRule):
    def __init__(self):
        self.myId         = 24
        self.name         = "UPNP Lookup"
        self.description  = ''
        self.optionLabels = ['UPNP Lookup']
        self.optionValues = [False]
        self.actions = RULES_ACTION_CHANNEL_JSON
        self.selectBoxOptions = [[False,True]]
        

    def copy(self):
        return UPNP()


    def getTitle(self):
        return 'UPNP Lookup %s'%({True:'Enabled',False:'Disabled'}[self.optionValues[0]])
            

    def onAction(self, act, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, Channels, Builder):
        if actionid == RULES_ACTION_CHANNEL_JSON:
            if channel['path'].startswith('upnp://'):
                channel['path'] = Builder.jsonRPC.chkUPNP(channel['path'])
        return channel