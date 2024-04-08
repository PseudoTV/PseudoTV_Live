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
from globals    import *
from jsonrpc    import JSONRPC
from seasonal   import Seasonal

class RulesList:
    def __init__(self, channels=None):
        if channels is None:
            from channels import Channels
            channels = Channels().getChannels()
        self.log('__init__, channels = %s'%(len(channels)))
        self.ruleList  = [BaseRule(),
                          EvenShowsRule(),
                          ShowChannelBug(),
                          ShowOnNext(),
                          ShowStaticOverlay(),
                          DisableOverlay(),
                          SetScreenOverlay(),
                          HandleMethodOrder(),
                          ProvisionalRule(),
                         ]
                         
        self.channels  = channels
        self.allRules  = self.allRules()
        self.chanRules = self.loadRules(channels)


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
        
        
    def loadRules(self, channels=[]): #load channel rules and their instances.
        def _loadRule(tmpruleList, channel={}):
            ruleList = []
            chid     = channel.get('id','')
            chrules  = sorted(channel.get('rules',[]), key=lambda k: k['id'])
            if chid is None: return None
            for chrule in chrules:
                for rule in tmpruleList:
                    if rule.myId == chrule['id']:
                        ruleInstance = rule.copy()
                        for idx in chrule.get('values',{}):
                            if chrule['values'].get(idx):
                                ruleInstance.optionValues[int(idx)] = chrule['values'][idx]
                        ruleList.append(ruleInstance)
            return chid, ruleList
        
        self.log('loadRules, channels = %s'%(len(channels)))
        tmpruleList = self.ruleList.copy()
        tmpruleList.pop(0) #remove boilerplate baseRule()
        return dict(poolit(_loadRule)(channels, tmpruleList))
      
      
    def allRules(self): #load all rules.
        self.log('allRules')
        tmpruleList = self.ruleList.copy()
        tmpruleList.pop(0) #remove boilerplate baseRule()
        ruleList = [rule.copy() for rule in tmpruleList]
        return ruleList
               
        
    def runActions(self, action, citem, parameter=None, inherited=None):
        if inherited is None: inherited = self
        self.log("runActions, %s action = %s, channel = %s"%(inherited.__class__.__name__,action,citem['id']))
        for rule in self.chanRules.get(citem['id'],[]):
            if action in rule.actions:
                self.log("runActions, %s performing channel rule: %s"%(inherited.__class__.__name__,rule.name))
                parameter = rule.runAction(action, citem, parameter, inherited)
        return parameter


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
        self.actions          = [RULES_ACTION_OVERLAY_OPEN]
        self.selectBoxOptions = [[True, False],list(range(-1,17))]
        #"Interval between channel bug appearances (Minutes). [-1 Indefinitely, 0 Randomly]"
        

    def copy(self):
        return ShowChannelBug()


    def getTitle(self):
        if self.optionValues[0]:
            return 'Show Channel Bug (%s)'%({'-1':'Indefinitely','0':'Randomly'}.get(str(self.optionValues[1]),'Every %s Minutes'%(self.optionValues[1])))
        else:
            return 'Hide Channel Bug'


    def onAction(self, act, optionindex):
        if optionindex == 0:
            self.onActionToggleBool(optionindex)
        elif optionindex == 1:
            self.onActionSelect(optionindex, 'Select Interval [-1 = Indefinitely, 0 = Randomly]',self.optionValues[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, overlay):
        if actionid == RULES_ACTION_OVERLAY_OPEN:
            overlay.showChannelBug = self.optionValues[0]
            overlay.channelBugVal  = self.optionValues[1]
            self.log("runAction, setting showChannelBug = %s, channelBugVal = %s"%(overlay.showChannelBug,overlay.channelBugVal))
        return citem


class ShowOnNext(BaseRule):
    def __init__(self):
        self.myId             = 2
        self.name             = "Show OnNext"
        self.description      = ""
        self.optionLabels     = ["Show OnNext"]
        self.optionValues     = [SETTINGS.getSettingBool('Enable_OnNext')]
        self.actions          = [RULES_ACTION_OVERLAY_OPEN]
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
        if actionid == RULES_ACTION_OVERLAY_OPEN:
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
        self.actions          = [RULES_ACTION_OVERLAY_OPEN]
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
        if actionid == RULES_ACTION_OVERLAY_OPEN:
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
        self.actions          = [RULES_ACTION_OVERLAY_OPEN]
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


class HandleMethodOrder(BaseRule):
    def __init__(self):
        self.myId             = 51
        self.name             = "Limits & Sort Methods"
        self.description      = ""
        self.optionLabels     = ['Page Limit','Method','Order','Ignore Folders']
        self.optionValues     = [int((REAL_SETTINGS.getSetting('Page_Limit') or "25")), 'random','ascending',False]
        self.actions          = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        # self.selectBoxOptions = [[n for n in range(25, 275, 25)], JSONRPC().getEnums("List.Sort",type="method"), JSONRPC().getEnums("List.Sort",type="order"), [True, False]]
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


class ProvisionalRule(BaseRule):
    def __init__(self):
        self.myId             = 53
        self.name             = "Provisional Placeholder"
        self.description      = "Fill Provisional Placeholder"
        self.optionLabels     = ["Provisional Label"]
        self.optionValues     = [""]
        self.actions          = [RULES_ACTION_CHANNEL_BUILD_PATH, RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.storedValues     = [list()]
        

    def copy(self): 
        return ProvisionalRule()
        
        
    def getTitle(self): 
        return self.name
        

    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_BUILD_PATH: 
            PROVISIONAL_TYPES = {"TV Shows"     : [{"path":"videodb://tvshows/titles/","limit":"","sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"field":"tvshow","operator":"is","value":""}]},
                                                    "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"}],
                                 "TV Networks"  : [{"path":"videodb://tvshows/studios/","limit":"","sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"field":"studio","operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"}],
                                 "Movie Studios": [{"path":"videodb://movies/studios/" ,"limit":"","sort":{"method":"random" ,"order":"ascending"},"filter":{"and":[{"field":"studio","operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetMovies","enum":"Video.Fields.Movie","key":"movies"}],
                                 "TV Genres"    : [{"path":"videodb://tvshows/genres/" ,"limit":"","sort":{"method":"random","order":"ascending"},"filter":{"and":[{"field":"genre" ,"operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"}],
                                 "Movie Genres" : [{"path":"videodb://movies/genres/" ,"limit":"","sort":{"method":"random" ,"order":"ascending"},"filter":{"and":[{"field":"genre" ,"operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetMovies","enum":"Video.Fields.Movie","key":"movies"}],
                                 "Mixed Genres" : [{"path":"videodb://tvshows/genres/" ,"limit":"","sort":{"method":"random","order":"ascending"},"filter":{"and":[{"field":"genre" ,"operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"},
                                                   {"path":"videodb://movies/genres/" ,"limit":"","sort":{"method":"random" ,"order":"ascending"},"filter":{"and":[{"field":"genre" ,"operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetMovies","enum":"Video.Fields.Movie","key":"movies"}]}

            if self.optionValues[0]:
                self.log("%s: runAction, id: %s, provisional value = %s"%(self.__class__.__name__,citem['id'],self.optionValues[0]))
                if builder.pDialog: builder.pDialog = DIALOG.progressBGDialog(builder.pCount, builder.pDialog, message='Applying Rule: %s'%(self.getTitle()),header='%s, %s'%(ADDON_NAME,builder.pMSG))
                if self.optionValues[0] == "Seasonal": queries = list(Seasonal().buildSeasonal())
                else:                                  queries = PROVISIONAL_TYPES.get(citem['type'],[])
                for provisional in queries:
                    if builder.service._interrupt() or builder.service._suspend(): break
                    elif not provisional: continue
                    else:
                        if self.optionValues[0] == "Seasonal": citem['logo'] = provisional.get('holiday',{}).get('logo',citem['logo'])
                        elif not parameter.startswith(provisional.get('path','')): continue
                        else: provisional["filter"]["and"][0]['value'] = self.optionValues[0]
                        if not builder.incExtras and provisional["key"].startswith(tuple(TV_TYPES)): #filter out extras/specials
                            provisional["filter"].setdefault("and",[]).extend([{"field":"season" ,"operator":"greaterthan","value":"0"},
                                                                               {"field":"episode","operator":"greaterthan","value":"0"}])
                        fileList, dirList = builder.buildList(citem, parameter, media='video', page=(provisional.get('limit') or builder.limit), sort=provisional.get('sort'), limits={}, dirItem={}, query=provisional)
                        if len(fileList) > 0: self.storedValues[0].append(fileList)

        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE: 
            return [_f for _f in self.storedValues.pop(0) if _f]
            
        return parameter
        
 
class EvenShowsRule(BaseRule):
    def __init__(self):
        self.myId         = 54
        self.name         = "Even Show Distribution"
        self.description  = "Sort shows in blocks." 
        self.optionLabels = ['Same Show Eps in a Row','Pagination Limit']
        self.optionValues = [2,PAGE_LIMIT]
        self.actions      = [RULES_ACTION_CHANNEL_BUILD_START,RULES_ACTION_CHANNEL_BUILD_PATH,RULES_ACTION_CHANNEL_BUILD_FILELIST_POST,RULES_ACTION_CHANNEL_BUILD_STOP]
        self.storedValues = [dict(),list(),PAGE_LIMIT]
        

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


    def runAction(self, actionid, citem, parameter, builder):
        def _sortShows(fileItem): #group by type & show; no duplicates. 
            if fileItem.get('type').startswith(tuple(TV_TYPES)):
                if fileItem not in self.storedValues[0].setdefault(fileItem['showtitle'],[]):
                    self.storedValues[0].setdefault(fileItem['showtitle'],[]).append(fileItem)
            elif fileItem.get('type').startswith(tuple(MOVIE_TYPES)):
                if fileItem not in self.storedValues[1]:
                    self.storedValues[1].append(fileItem)

        def _chunkShows():
            for show, episodes in list(self.storedValues[0].items()):
                yield show,[episodes[i:i+self.optionValues[0]] for i in range(0,len(episodes),self.optionValues[0])]

        def _mergeShows(shows, movies):
            nfileList = []
            while not MONITOR.abortRequested() and shows:
                for show, chunks in list(shows.items()):
                    if   len(chunks) == 0: del shows[show]
                    elif len(chunks) > 0:  nfileList.extend(shows[show].pop(0))
                    if len(movies) > 0:    nfileList.append(movies.pop(0))
                    
            if len(movies) > 0:
                self.log('runAction, _mergeShows appending remaining movies, movie count = %s'%(len(movies)))
                nfileList.extend(movies) #add any remaning movies to the end of sets.
                
            self.log('runAction, _mergeShows returning items = %s'%(len(nfileList)))
            return [_f for _f in nfileList if _f]
                
        if actionid == RULES_ACTION_CHANNEL_BUILD_START:
            self.storedValues[2] = builder.limit # store global pagination limit
            self.log('runAction, saving limit %s'%(builder.limit))
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_PATH:
            print('RULES_ACTION_CHANNEL_BUILD_PATH',parameter)
            if parameter.startswith(tuple(['videodb://%s'%tv for tv in TV_TYPES])):
                builder.limit = self.storedValues[2] * self.optionValues[0]
            elif parameter:
                builder.limit = self.storedValues[2]
            self.log('runAction, changing limit %s'%(builder.limit))
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_POST:
            try:
                if parameter:
                    if builder.pDialog: builder.pDialog = DIALOG.progressBGDialog(builder.pCount, builder.pDialog, message='Applying Rule: %s'%(self.getTitle()),header='%s, %s'%(ADDON_NAME,builder.pMSG))
                    poolit(_sortShows)(list(sorted(parameter, key=lambda k: k.get('episode',0))))
                    self.storedValues[0] = dict(_chunkShows())
                    return _mergeShows(self.storedValues[0],self.storedValues[1])
            except Exception as e: log("runAction, failed! %s"%(e), xbmc.LOGERROR)
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_STOP:
            builder.limit = self.storedValues[2] # restore global pagination limit
            self.log('runAction, restoring limit %s'%(self.storedValues[2]))
            
        return parameter