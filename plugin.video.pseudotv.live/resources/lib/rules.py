#   Copyright (C) 2024 Lunatixz
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
from globals     import *
      
class RulesList:
    def __init__(self, channels=None):
        if channels is None:
            from channels import Channels
            channels = Channels().getChannels()
        self.log('__init__, channels = %s'%(len(channels)))
        self.ruleList  = [BaseRule(),
                          BestEffort()]
                         # [BaseRule(),
                         # ShowChannelBug(),
                         # ShowOnNext(),
                         # ShowStaticOverlay(),
                         # DisableOverlay(),
                         # SetScreenOverlay(),
                         # HandleMethodOrder(),
                         # HandleFilter(),
                         # seekControl(),
                         # ]
        self.channels  = channels
        self.chanRules = self.loadRules(channels)


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def loadRules(self, channels=[]): #load channel rules and their instances.
        def _loadRule(tmpruleList, channel={}):
            ruleList = {}
            chid     = channel.get('id','')
            chrules  = channel.get('rules',[])
            if chid is None: return None
            for chrule in chrules:
                for rule in tmpruleList:
                    if rule.myId == chrule['id']:
                        ruleInstance = rule.copy()
                        optionindex  = chrule.get('index',{})
                        for key in optionindex.keys():
                            ruleInstance.optionLabels[int(key)] = optionindex[str(key)].get('label')
                            ruleInstance.optionValues[int(key)] = optionindex[str(key)].get('value')
                        ruleList.setdefault(chid,[]).append(ruleInstance)
            return ruleList
        
        self.log('loadRules, channels = %s'%((channels)))
        tmpruleList = self.ruleList.copy()
        tmpruleList.pop(0) #remove boilerplate baseRule()
        ruleList = poolit(_loadRule)(channels, tmpruleList)
        print('loadRules',ruleList)
        return ruleList
      
        
    def runActions(self, action, citem, parameter=None, inherited=None):
        if inherited is None: inherited = self
        if not citem.get('id',''): return parameter
        self.log("runActions, %s action = %s, channel = %s"%(inherited.__class__.__name__,action,citem['id']))
        for channel in self.chanRules:
            for rule in channel.get(citem['id'],[]):
                if action in rule.actions:
                    self.log("runActions, %s performing channel rule: %s"%(inherited.__class__.__name__,rule.name))
                    print((action, citem, parameter, inherited))
                    return rule.runAction(action, citem, parameter, inherited)
        return parameter


        
        
        
        
        
        
        
        
        
        
        
        
    # def buildRuleList(self, channels=[]): #load all rules instances and apply their per channel settings.
        # ruleList = {}
        # tmpruleList = self.ruleList.copy() #base rule instances
        # tmpruleList.pop(0) #remove BaseRule()
        # for channel in channels:
            # chid = channel.get('id','')
            # if not chid: continue
            # ruleList[chid] = []
            # chrules = channel.get('rules',[])
            # for rule in tmpruleList:
                # ruleInstance = rule.copy()
                # for chrule in chrules:
                    # if   chrule.get('id',0) == 0: continue #ignore template if exists
                    # elif ruleInstance.myId == chrule['id']:#match rule instance by id
                        # options = chrule.get('options',[])
                        # for key in options.keys():
                            # ruleInstance.optionLabels[int(key)] = options[str(key)].get('label')
                            # ruleInstance.optionValues[int(key)] = options[str(key)].get('value')
                        # break
                # ruleList[chid].append(ruleInstance)
        # self.log('buildRuleList, channels = %s\nruleList = %s'%(len(channels),ruleList))
        # return ruleList
     
     
        

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
    dialog = Dialog()
    
    def __init__(self):
        self.myId         = 0
        self.name         = ""
        self.description  = ""
        self.optionLabels = []
        self.optionValues = []
        self.storedValues = []
        self.actions      = []
        

    def getTitle(self):
        return self.name
        
        
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


    def runAction(self, actionid, citem, parameter, inherited):
        return parameter


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
        value = self.dialog.inputDialog(self.name, default=self.optionValues[optionindex], key=xbmcgui.INPUT_ALPHANUM)
        if value: self.optionValues[optionindex] = value
        

    def onActionDateBox(self, optionindex):
        log("onActionDateBox")
        info =  self.dialog.inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)
        if info != None: self.optionValues[optionindex] = info


    def onActionTimeBox(self, optionindex):
        log("onActionTimeBox")
        info = self.dialog.inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)
        if info != None:
            if info[0] == ' ': info = info[1:]
            if len(info) == 4: info = "0" + info
            self.optionValues[optionindex] = info


    def onActionSelect(self, optionindex, header=ADDON_NAME, psel=-1, multi=False):
        log("onActionSelect")
        if psel < 0:
            psel = [idx for idx, item in enumerate(self.selectBoxOptions[optionindex]) if item == self.optionValues[optionindex]]
            if not multi: psel = (psel[0] or -1)
        select = (self.dialog.selectDialog(titleLabels(self.selectBoxOptions[optionindex]), header, preselect=psel, useDetails=False, multi=multi) or -1)
        if select is not None: 
            self.optionValues[optionindex] = self.selectBoxOptions[optionindex][select]
                
          
    def onActionBrowse(self, optionindex, header=ADDON_NAME, multi=False, type=0, shares='', mask='', useThumbs=True, treatAsFolder=False, default='', prompt=False):
        log("onActionBrowse")
        info = self.dialog.browseDialog(type, header, default, shares, mask, None, useThumbs, treatAsFolder, prompt, multi, monitor=False)
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
        value = self.dialog.inputDialog(self.name, default=self.optionValues[optionindex], key=xbmcgui.INPUT_ALPHANUM)
        if value: self.optionValues[optionindex] = value.upper()


    def onActionDigitBox(self, optionindex):
        self.optionValues[optionindex] = self.dialog.inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)


class ShowChannelBug(BaseRule):
    def __init__(self):
        self.myId             = 1
        self.name             = "Show Channel Bug & Interval"
        self.description      = ""
        self.optionLabels     = ['Show Channel Bug','Channel Bug Interval']
        self.optionValues     = [SETTINGS.getSettingBool('Enable_ChannelBug'),SETTINGS.getSettingInt("Channel_Bug_Interval")]
        self.actions          = [RULES_ACTION_OVERLAY]
        self.selectBoxOptions = [[True, False],list(range(-1,17))]
        #"Interval between channel bug appearances (Minutes). [-1 Indefinitely, 0 Random]"
        

    def copy(self):
        return ShowChannelBug()


    def getTitle(self):
        if self.optionValues[0]:
            return 'Hide Channel Bug'
        else:
            return 'Show Channel Bug'


    def onAction(self, act, optionindex):
        if optionindex == 0:
            self.onActionToggleBool(optionindex)
        elif optionindex == 1:
            self.onActionSelect(optionindex, 'Select Interval [-1 Indefinitely, 0 Random]',self.optionValues[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, overlay):
        if actionid == RULES_ACTION_OVERLAY:
            overlay.showChannelBug = self.optionValues[0]
            overlay.channelBugVal  = self.optionValues[1]            
            self.log("runAction, setting showChannelBug = %s"%(overlay.showChannelBug))
            self.log("runAction, setting channelBugVal = %s"%(overlay.channelBugVal))
        return citem


class ShowOnNext(BaseRule):
    def __init__(self):
        self.myId             = 2
        self.name             = "Show OnNext"
        self.description      = ""
        self.optionLabels     = ["Show OnNext"]
        self.optionValues     = [SETTINGS.getSettingBool('Enable_OnNext')]
        self.actions          = [RULES_ACTION_OVERLAY]
        self.selectBoxOptions = [[True, False]]


    def copy(self):
        return ShowOnNext()


    def getTitle(self):
        if self.optionValues[0]:
            return 'Show OnNext'
        else:
            return 'Hide OnNext'


    def onAction(self, act, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, overlay):
        if actionid == RULES_ACTION_OVERLAY:
            overlay.showOnNext = self.optionValues[0]
            self.log("runAction, setting showOnNext = %s"%(overlay.showOnNext))
        return citem


class ShowStaticOverlay(BaseRule):
    def __init__(self):
        self.myId             = 3
        self.name             = "Show Static Overlay"
        self.description      = ""
        self.optionLabels     = ['Show Static Overlay']
        self.optionValues     = [SETTINGS.getSettingBool('Static_Overlay')]
        self.actions          = [RULES_ACTION_OVERLAY]
        self.selectBoxOptions = [[True, False]]

    def copy(self):
        return ShowStaticOverlay()


    def getTitle(self):
        if self.optionValues[0]:
            return 'Hide Static Overlay'
        else:
            return 'Show Static Overlay'


    def onAction(self, act, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, overlay):
        if actionid == RULES_ACTION_OVERLAY:
            overlay.showStatic = self.optionValues[0]
            self.log("runAction, setting showStatic = %s"%(overlay.showStatic))
        return citem


class SetScreenOverlay(BaseRule): #todo requires Kodi core changes.
    def __init__(self):
        self.myId             = 20
        self.name             = "Set Screen Overlay"
        self.description      = ""
        self.optionLabels     = ['Enable Overlay','Select Image','X-POS','Y-POS']
        self.optionValues     = [False,'',0,0]
        self.actions          = [RULES_ACTION_OVERLAY]
        self.selectBoxOptions = [[True, False],[],[],[]]

            
class DisableOverlay(BaseRule):
    def __init__(self):
        self.myId             = 21
        self.name             = "Disable Overlay"
        self.description      = ""
        self.optionLabels     = ['Disable Overlay']
        self.optionValues     = [not bool(SETTINGS.getSettingBool('Enable_Overlay'))]
        self.actions          = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions = [[True, False]]
        self.storedValues     = [self.optionValues[0]]


    def copy(self):
        return DisableOverlay()


    def getTitle(self):
        if self.optionValues[0]:
            return 'Enable overlay'
        else:
            return 'Disable overlay'


    def onAction(self, act, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, pvritem, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.showOverlay
            player.showOverlay = self.optionValues[0]
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.showOverlay = self.storedValues[0]
        self.log("runAction, setting showOverlay = %s"%(player.showOverlay))
        return pvritem


class ForceSubtitles(BaseRule):
    def __init__(self):
        self.myId             = 22
        self.name             = "Force Subtitles"
        self.description      = ""
        self.optionLabels     = ['Force Subtitles']
        self.optionValues     = [isSubtitle()]
        self.actions          = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions = [[True, False]]
        self.storedValues     = [self.optionValues[0]]


    def copy(self):
        return ForceSubtitles()


    def getTitle(self):
        if self.optionValues[0]:
            return 'Show Subtitles'
        else:
            return 'Hide Subtitles'


    def onAction(self, act, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, pvritem, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.lastSubState
            player.lastSubState  = self.optionValues[0]
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.lastSubState = self.storedValues[0]
        self.log("runAction, setting lastSubState = %s"%(player.lastSubState))
        return pvritem

 
class seekControl(BaseRule):
    def __init__(self):
        self.myId             = 41
        self.name             = "Seek Control, Threshold & Tolerance"
        self.description      = ''
        self.optionLabels     = ['Disable Seeking','Threshold Percentage','Tolerance Seconds']
        self.optionValues     = [False,SETTINGS.getSettingInt('Seek_Threshold'),SETTINGS.getSettingInt('Seek_Tolerance')]
        self.actions          = [RULES_ACTION_PLAYBACK]
        self.selectBoxOptions = [[True,False],list(range(85,101)),list(range(0,901,5))]
        

    def copy(self):
        return seekControl()


    def getTitle(self):
        if self.optionValues[0]:
            return 'Disable seek'
        else: 
            return 'Enabled seek'
            

    def onAction(self, act, optionindex):
        if optionindex == 0:
            self.onActionToggleBool(act, optionindex)
        elif optionindex == 1:
            self.onActionDigitBox(act, optionindex)
        elif optionindex == 2:
            self.onActionDigitBox(act, optionindex)
        self.validate(optionindex)
        return self.optionValues[optionindex]


    def validate(self, optionindex):
        if optionindex > 0:
            self.validateDigitBox(optionindex,self.selectBoxOptions[optionindex][0],self.selectBoxOptions[optionindex][-1],self.optionValues[optionindex])
            
            
    def runAction(self, actionid, citem, nowitem, plugin):
        if actionid == RULES_ACTION_PLAYBACK:
            if self.optionValues[0]:
                self.log("runAction, disabling seek progress")
                nowitem['progress'] = 0
                
            plugin.seekTHLD  = self.optionValues[1]
            plugin.seekTLRNC = self.optionValues[2]
            self.log("runAction, setting seekTHLD = %s"%(plugin.seekTHLD))
            self.log("runAction, setting seekTLRNC = %s"%(plugin.seekTLRNC))
        return nowitem


class HandleMethodOrder(BaseRule):
    def __init__(self):
        self.myId             = 61
        self.name             = "Limits & Sort Methods"
        self.description      = ""
        self.optionLabels     = ['Page Limit','Method','Order','Ignore Folders']
        self.optionValues     = [int((REAL_SETTINGS.getSetting('Page_Limit') or "25")), 'random','ascending',False]
        self.actions          = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions = [[n for n in range(25, 275, 25)], self.jsonRPC.getENUM(JSON_METHOD), self.jsonRPC.getENUM(JSON_ORDER), [True, False]]
        self.storedValues     = []
        
        
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


    def runAction(self, actionid, citem, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.limit
            self.storedValues[1] = builder.sort #"sort": {"order":"ascending","method":"random","ignorefolders":false,"ignorearticle":true,"useartistsortname":true}}
            builder.limit = self.optionValues[0]
            builder.sort  = {"method": self.optionValues[0].lower(), "order": self.optionValues[1].lower(), "ignorefolders": int(self.optionValues[2] == True)}
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.limit = self.storedValues[0]
            builder.sort  = self.storedValues[1]
        self.log("runAction, setting limit = %s"%(builder.limit))
        self.log("runAction, setting sort = %s"%(builder.sort))
        return citem


class HandleFilter(BaseRule):
    def __init__(self):
        self.myId             = 62
        self.name             = "Filter Content"
        self.description      = ""
        self.actions          = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.optionLabels     = ['Field','Operator','Value']
        self.optionValues     = ['showtitle','contains','']
        self.selectBoxOptions = [self.jsonRPC.getENUM(JSON_FILE_ENUM), self.jsonRPC.getENUM(JSON_OPERATORS)]
        self.storedValues     = []
        

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


    def runAction(self, actionid, citem, builder):
        if actionid == RULES_ACTION_CHANNEL_START: 
            self.storedValues[0] = builder.filter #"filter": {"and": [{"operator": "contains", "field": "title", "value": "Star Wars"}, {"operator": "contains", "field": "tag", "value": "Good"}]}
            builder.filter = {"field": self.optionValues[0].lower(), "operator": self.optionValues[1].lower(), "value": quote((self.optionValues[2]))}
        elif actionid == RULES_ACTION_CHANNEL_STOP: 
            builder.filter = self.storedValues[0]
        self.log("runAction, setting filter = %s"%(builder.filter))
        return citem
 

class BestEffort(BaseRule):
    def __init__(self):
        self.myId         = 63
        self.name         = "Best Effort Marathon"
        self.description  = "Sort shows in groups of user defined blocks."
        self.actions      = [RULES_ACTION_CHANNEL_BUILD_GLOBAL,RULES_ACTION_CHANNEL_BUILD_FILELIST_POST,RULES_ACTION_CHANNEL_BUILD_STOP]
        self.optionLabels = ["Group shows in blocks of x episodes"]
        self.optionValues = [3]#todo add global user setting
        self.storedValues = [dict(),list(),dict(),int()]
        

    def copy(self): 
        return BestEffort()
        
        
    def getTitle(self): 
        return self.name


    def runAction(self, actionid, citem, parameter, builder):
        def _sortShows(fileItem):
            if fileItem.get('type').startswith(tuple(TV_TYPES)) and fileItem not in self.storedValues[0].setdefault(fileItem['showtitle'],[]):
                self.storedValues[0].setdefault(fileItem['showtitle'],[]).append(fileItem)
            else:
                self.storedValues[1].append(fileItem)
            
        def _chunkShows():
            for show, episodes in self.storedValues[0].items():
                self.log("_chunkShows, show = %s, episodes = %s"%(show,len(episodes)))
                yield show, list(chunkLst(episodes,self.optionValues[0]))
                
        def _mergeShows(shows):
            nfileList = []
            movies = list(chunkLst(self.storedValues[1],len(shows.keys())))
            print('movies',len(movies),movies)
            
         
            while not MONITOR.abortRequested() and shows:
                for show, chunks in shows.items():
                    if len(chunks) == 0:
                        print('del',show)
                        del shows[show]
                    print('show',show,len(chunks))
                    for idx, chunk in enumerate(chunks):
                        print('idx',idx,chunk)
                        if len(chunk)  > 0: nfileList.extend(chunks.pop(idx))
                        if len(movies) > 0: nfileList.extend(movies.pop(0))
                    break
                    
            for chunk in movies:
                nfileList.extend(chunk) #add any remaning movies to the end of sets.
                
            print(nfileList)
            self.log("_mergeShows, returning items = %s"%(len(nfileList)))
            return nfileList
                   
        if citem['type'] in ['TV Genres','Mixed Genres','Custom']:
            if actionid == RULES_ACTION_CHANNEL_BUILD_GLOBAL:
                self.storedValues[3] = builder.limit
                builder.limit = builder.limit * 4
                # self.storedValues[2] = builder.sort
                # if isinstance(parameter,dict):
                    # if parameter.get('sort','').startswith(tuple(TV_TYPES)):
                        # builder.sort = {"ignorearticle":True,"method":"episode","order":"ascending","useartistsortname":True}
                # elif parameter.startswith('videodb://tvshows/'):
                    # builder.sort = {"ignorearticle":True,"method":"episode","order":"ascending","useartistsortname":True}
                # elif parameter.startswith('videodb://movies/'):
                    # builder.sort = {"ignorearticle":True,"method":"year","order":"ascending","useartistsortname":True}
                    
            elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_POST:
                builder.pDialog = DIALOG.progressBGDialog(builder.pCount, builder.pDialog, message='%s: Adding Rule %s'%(builder.pName,self.getTitle()),header='%s, %s'%(ADDON_NAME,builder.pMSG))
                print(len(parameter),parameter)
                poolit(_sortShows)(list(sorted(parameter, key=lambda k: k.get('episode',0))))
                print(len(self.storedValues[0]),self.storedValues[0])
                return _mergeShows(dict(_chunkShows()))
                
            elif actionid == RULES_ACTION_CHANNEL_BUILD_STOP:
                builder.limit = self.storedValues[3]
                    # builder.sort = self.storedValues[2]
        return parameter

 
# todo control rules
# self.incStrms         = SETTINGS.getSettingBool('Enable_Strms')
# self.inc3D            = SETTINGS.getSettingBool('Enable_3D')
# self.incExtras        = SETTINGS.getSettingBool('Enable_Extras') 
# self.fillBCTs         = SETTINGS.getSettingBool('Enable_Fillers')
# self.accurateDuration = bool(SETTINGS.getSettingInt('Duration_Type'))