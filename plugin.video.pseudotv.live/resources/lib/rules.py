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
from seasonal   import Seasonal
#todo pinlock

class RulesList:
    def __init__(self):
        self.log('__init__')
        self.ruleList  = [BaseRule(),
                          ShowChannelBug(),
                          ShowOnNext(),
                          SetScreenVingette(),
                          MST3k(),
                          DisableOverlay(),
                          DisableReplay(),
                          ForceSubtitles(),
                          DisableTrakt(),
                          RollbackPlaycount(),
                          DurationOptions(),
                          FilterOptions(),
                          ProvisionalRule(),
                          HandleMethodOrder(),
                          ForceEpisode(),
                          ForceRandom(),
                          EvenShowsRule()]
        self.ruleItems = self.loadRules()
                         

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def getTemplate(self) -> dict: 
        return getJSON(RULEFLE_ITEM).copy()
        
                  
    def dumpRules(self, rules={}): #convert rule instances to channel format
        nrules = dict()
        if not list(rules.items()): return None
        for key, rule in list(rules.items()):
            ritem = dict()
            ritem[key] = {"values":dict()}
            for idx, value in enumerate(rule.optionValues):
                ritem[key]["values"][str(idx)] = value
            nrules.update(ritem)
        return nrules
            

    def loadRules(self, channels=None, append=False, incRez=True): #load channel rules and their instances.
        if channels is None:
            from channels import Channels
            channel  = Channels()
            channels = channel.getChannels()
            del channel
            
        def _load(tmpruleList, citem={}):
            ruleList = {}
            chrules  = citem.get('rules',{})
            if not append and len(chrules) == 0: return None
            for rule in tmpruleList:
                if not incRez and rule.ignore: continue
                try:    chrule = chrules.get(str(rule.myId)) #temp fix.issue after converting list to dict in channels.json
                except: chrule = {}
                if chrule:
                    ruleInstance = rule.copy()
                    for key, value in list(chrule.get('values',{}).items()):
                        ruleInstance.optionValues[int(key)] = value
                    ruleList.update({str(rule.myId):ruleInstance})
                elif append: ruleList.update({str(rule.myId):rule.copy()})
            self.log('loadRules, id = %s, append = %s, incRez = %s, rule myIds = %s'%(citem.get('id'),append, incRez,list(ruleList.keys())))
            rules.update({citem.get('id'):ruleList})
            
        rules = dict()
        tmpruleList = self.ruleList.copy()
        tmpruleList.pop(0) #remove boilerplate baseRule()
        [_load(tmpruleList,channel) for channel in channels]
        self.log('loadRules, channels = %s'%(len(channels)))
        return rules


    def allRules(self): #load all rules.
        self.log('allRules')
        tmpruleList = self.ruleList.copy()
        tmpruleList.pop(0) #remove boilerplate baseRule()
        return [rule.copy() for rule in tmpruleList]
               
        
    def runActions(self, action, citem={}, parameter=None, inherited=None):
        if inherited is None: inherited = self
        self.log("runActions, %s action = %s, id = %s"%(inherited.__class__.__name__,action,citem.get('id')))
        rules = (self.ruleItems.get(citem.get('id','')) or self.loadRules([citem]).get(citem.get('id','')) or {})
        for myId, rule in list(sorted(rules.items())):
            if action in rule.actions:
                self.log("runActions, %s performing channel rule: %s"%(inherited.__class__.__name__,rule.name))
                parameter = rule.runAction(action, citem, parameter, inherited)
        return parameter


class BaseRule:
    dialog = Dialog()
    
    def __init__(self):
        self.myId               = 0
        self.ignore             = False #ignore from manager options, reserved for autotuning.
        self.exclude            = False #applies only to db queries not smartplaylists
        self.name               = ""
        self.description        = ""
        self.optionLabels       = []
        self.optionValues       = []
        self.optionDescriptions = []
        self.actions            = []
        self.selectBoxOptions   = []
        self.storedValues       = []
        

    def getTitle(self):
        return self.name
        

    def onAction(self, optionindex):
        return ''


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
            self.dialog.notificationDialog(LANGUAGE(32077)%(self.optionLabels[optionindex]))
            self.optionValues[optionindex] = default
            return
        elif int(self.optionValues[optionindex]) > maximum:
            log("Invalid maximum range")
            self.dialog.notificationDialog(LANGUAGE(32077)%(self.optionLabels[optionindex]))
            self.optionValues[optionindex] = default
            return


    def validateDigitBox(self, optionindex, minimum, maximum, default):
        if int(self.optionValues[optionindex]) == 0: return
        try:
            val = int(self.optionValues[optionindex])
            if val >= minimum and val <= maximum:
                self.optionValues[optionindex] = val
            return
        except: pass
        self.dialog.notificationDialog(LANGUAGE(32077)%(self.optionLabels[optionindex]))
        self.optionValues[optionindex] = default

    
    def onActionToggleBool(self, optionindex):
        log("onActionToggleBool")
        self.optionValues[optionindex] = not self.optionValues[optionindex]


    def onActionFunction(self, optionindex):
        log("onActionFunction")
        value = self.selectBoxOption[optionindex]()
        if value: self.optionValues[optionindex] = value


    def onActionPickColor(self, optionindex, colorlist=[], colorfile=""):
        log("onActionPickColor")
        value = self.dialog.colorDialog(colorlist, self.optionValues[optionindex], colorfile, self.name)
        if value: self.optionValues[optionindex] = value
        

    def onActionTextBox(self, optionindex):
        log("onActionTextBox")
        value = self.dialog.inputDialog(self.name, default=self.optionValues[optionindex], key=xbmcgui.INPUT_ALPHANUM)
        if value: self.optionValues[optionindex] = value


    def onActionDigitBox(self, optionindex):
        log("onActionDigitBox")
        info =  self.dialog.inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)
        if info != None: self.optionValues[optionindex] = info


    def onActionTimeBox(self, optionindex):
        log("onActionTimeBox")
        info = self.dialog.inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)
        if info != None:
            if info[0] == ' ': info = info[1:]
            if len(info) == 4: info = "0" + info
            self.optionValues[optionindex] = info


    def onActionSelect(self, optionindex, header=ADDON_NAME, preselect=-1, useDetails=False, autoclose=SELECT_DELAY, multi=False, custom=False):
        log("onActionSelect")
        self.selectBoxOptions[optionindex] = list(sorted(self.selectBoxOptions[optionindex]))
        if preselect < 0 and multi: preselect = [idx for idx, item in enumerate(self.selectBoxOptions[optionindex]) if item == self.optionValues[optionindex]]
        select = self.dialog.selectDialog(list(sorted([str(v).title() for v in self.selectBoxOptions[optionindex]])), header, preselect, useDetails, autoclose, multi, custom)
        if select is not None: 
            self.optionValues[optionindex] = self.selectBoxOptions[optionindex][select]
                
          
    def onActionBrowse(self, optionindex, type=0, heading=ADDON_NAME, shares='', mask='', options=None, useThumbs=True, treatAsFolder=False, prompt=True, multi=False, monitor=False):
        log("onActionBrowse")
        info = self.dialog.browseDialog(type, heading, self.optionValues[optionindex].replace('None',''), shares, mask, options, useThumbs, treatAsFolder, prompt, multi, monitor)
        if info is not None: self.optionValues[optionindex] = info 
                     

class ShowChannelBug(BaseRule):
    def __init__(self):
        self.myId               = 1
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30143)
        self.description        = LANGUAGE(30144)
        self.optionLabels       = [LANGUAGE(30043),LANGUAGE(30086),LANGUAGE(30112),LANGUAGE(30044),LANGUAGE(30113)]
        self.optionValues       = [SETTINGS.getSettingBool('Enable_ChannelBug'),SETTINGS.getSettingInt("Channel_Bug_Interval"),self.getPOS(),SETTINGS.getSetting('DIFFUSE_LOGO'),SETTINGS.getSettingBool('Force_Diffuse')]
        self.optionDescriptions = [LANGUAGE(33043),LANGUAGE(33086),LANGUAGE(33112),LANGUAGE(33044),LANGUAGE(33111)]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = ["",list(range(-1,16)),"","",""]
        self.storedValues       = [[],[],[],[],[]]
        

    def copy(self):
        return ShowChannelBug()


    def getPOS(self):
        try:    return literal_eval(SETTINGS.getSetting("Channel_Bug_Position_XY"))
        except: return (abs(int(1920 // 8) - 1920) - 128, abs(int(1080 // 16) - 1080) - 128)

    def getTitle(self):
        if self.optionValues[0]: return LANGUAGE(30145)%({'-1':'Indefinitely','0':'Randomly'}.get(str(self.optionValues[1]),LANGUAGE(30146)%(self.optionValues[1])),self.optionValues[2],{True:'Forcing',False:''}[self.optionValues[4]],self.optionValues[3])
        else:                    return LANGUAGE(30147)


    def getPosition(self, optionindex):
        self.dialog.notificationDialog(LANGUAGE(32020))
        # from channelbug import ChannelBug
        # channelbug = ChannelBug(CHANNELBUG_XML, ADDON_PATH, "default")
        # del  channelbug
        # value = PROPERTIES.getProperty("Channel_Bug_Position_XY")
        # if value: self.optionValues[optionindex] = value


    def onAction(self, optionindex):
        if   optionindex == 0: self.onActionToggleBool(optionindex)
        elif optionindex == 1: self.onActionSelect(optionindex, LANGUAGE(30148))
        elif optionindex == 2: self.getPosition(optionindex)
        elif optionindex == 3: self.onActionPickColor(optionindex)
        elif optionindex == 4: self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, overlay):
        if actionid == RULES_ACTION_OVERLAY_OPEN:
            self.storedValues[0] = overlay.enableChannelBug
            self.storedValues[1] = overlay.channelBugInterval
            self.storedValues[2] = (overlay.channelBugX, overlay.channelBugY)
            self.storedValues[3] = overlay.channelBugColor
            self.storedValues[4] = overlay.channelBugDiffuse
            
            overlay.enableChannelBug   = self.optionValues[0]
            overlay.channelBugInterval = self.optionValues[1]
            overlay.channelBugX, overlay.channelBugY = literal_eval(self.optionValues[2])
            overlay.channelBugColor    = '0x%s'%(self.optionValues[3])
            overlay.channelBugDiffuse  = self.optionValues[4]
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay.enableChannelBug   = self.storedValues[0]
            overlay.channelBugInterval = self.storedValues[1]
            overlay.channelBugX, overlay.channelBugY = self.storedValues[2]
            overlay.channelBugColor   = self.storedValues[3]
            overlay.channelBugDiffuse = self.storedValues[4]
            self.log("runAction, enableChannelBug = %s, channelBugInterval = %s, channelBugInterval = %s"%(overlay.enableChannelBug,overlay.channelBugInterval,(overlay.channelBugX, overlay.channelBugY)))
            self.log("runAction, channelBugColor = %s, channelBugDiffuse = %s"%(overlay.channelBugColor,overlay.channelBugDiffuse))
        return parameter


class ShowOnNext(BaseRule):
    def __init__(self):
        self.myId               = 2
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30045)
        self.description        = LANGUAGE(33045)
        self.optionLabels       = [LANGUAGE(30045)]
        self.optionValues       = [SETTINGS.getSettingBool('Enable_OnNext')]
        self.optionDescriptions = [LANGUAGE(30045)]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = [""]
        self.storedValues       = [[]]


    def copy(self):
        return ShowOnNext()


    def getTitle(self):
        return '%s (%s)'%(LANGUAGE(30045), self.optionValues[0])


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, overlay):
        if actionid == RULES_ACTION_OVERLAY_OPEN:
            self.storedValues[0] = overlay.enableOnNext
            overlay.enableOnNext = self.optionValues[0]
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay.enableOnNext = self.storedValues[0]
        self.log("runAction, setting enableOnNext = %s"%(overlay.enableOnNext))
        return parameter


class SetScreenVingette(BaseRule): #todo requires Kodi core changes. resize videowindow control
    def __init__(self):
        self.myId               = 3
        self.ignore             = False
        self.exclude            = False
        self.name               = "Screen Vignette"
        self.description        = "Add Channel Overlay to create a immersive viewing experience."
        self.optionLabels       = ['Enable Screen Vignette','Vignette Image','Vignette Image offset']
        self.optionValues       = [False,'None',"(0,0)"]
        self.optionDescriptions = ["Show Screen Vignette","Change Vignette Image","Change Vignette Offset"]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = ["",self.optionValues[1],""]
        self.storedValues       = [[],[],[]]


    def copy(self):
        return SetScreenVingette()


    def getTitle(self):
        if self.optionValues[0]: return 'Show Screen Vignette w/%s offset\n%s'%(self.optionValues[2],self.getImage(self.optionValues[1]))
        else:                    return 'Hide Screen Vignette'
            
            
    def getPosition(self, optionindex):
        self.dialog.notificationDialog(LANGUAGE(32020))


    def getImage(self, image='None'):
        if not image is None:
            self.log('getImage, In image = %s'%(image))
            day    = re.compile('\_Day(.*?)', re.IGNORECASE).search(image)
            night  = re.compile('\_Night(.*?)', re.IGNORECASE).search(image)
            mytime = time.localtime()
            if mytime.tm_hour < 6 or mytime.tm_hour > 18:
                if day:
                    nImage = image.replace(day.group(),'_Night')
                    if FileAccess.exists(nImage): image = nImage
            else:
                if night:
                    nImage = image.replace(night.group(),'_Day')
                    if FileAccess.exists(nImage): image = nImage
            self.log('getImage, Out image = %s'%(image))
        return image


    def onAction(self, optionindex):
        if   optionindex == 0: self.onActionToggleBool(optionindex)
        elif optionindex == 1: self.onActionBrowse(optionindex, type=1, heading=self.optionLabels[1], mask=xbmc.getSupportedMedia('picture'), options=list(range(6,11)))
        elif optionindex == 2: self.getPosition(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, overlay):
        if actionid == RULES_ACTION_OVERLAY_OPEN:
            self.storedValues[1] = overlay._vinImage
            self.storedValues[2] = (overlay._vinOffsetX,overlay._vinOffsetY)
            
            overlay._vinImage    = self.getImage(self.optionValues[1])
            overlay._vinOffsetX, overlay._vinOffsetY = literal_eval(self.optionValues[2])
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay._vinImage    = self.storedValues[1]
            overlay._vinOffsetX, overlay._vinOffsetY = self.storedValues[2]
        self.log("runAction, setting overlay image to %s (%s,%s)"%(overlay._vinImage,overlay._vinOffsetX,overlay._vinOffsetY))
        return parameter
        

# Enable_Fillers
# Enable_Preroll
# Random_Pre_Chance
# Enable_Postroll
# Random_Post_Chance
# Build_Post_Folders
# Include_Adverts_iSpot
# Resource_Trailers
# Include_Trailers_KODI
# Include_Trailers_IMDB


# Resource_Overlay
# Resource_Ratings
# Resource_Bumpers
# Resource_Adverts
  
class MST3k(BaseRule): #todo requires Kodi core changes. resize videowindow control
    def __init__(self):
        self.myId               = 4
        self.ignore             = False
        self.exclude            = False
        self.name               = "Mystery Science Theater 3K Silhouette"
        self.description        = "Animated Silhouette of MST3K"
        self.optionLabels       = ['Enable MST3K Silhouette']
        self.optionValues       = [False]
        self.optionDescriptions = ["Enable Silhouette"]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_OPEN+.1,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = [""]
        self.storedValues       = [[],[]]
        self.threadTimer = Timer(5.0, self.runAction)
        

    def copy(self):
        return MST3k()


    def getTitle(self):
        if self.optionValues[0]: return 'Show MST3K Silhouette'
        else:                    return 'Hide MST3K Silhouette'


    def setImage(self, actionid, citem, overlay, image):
        if not self.threadTimer.is_alive():
            self.threadTimer = Timer(5.0, overlay.runActions,[actionid, citem, None, overlay])
            self.threadTimer.name = 'MST3k.setImage'
            self.threadTimer.start()
        self.log('setImage, image = %s'%(image))
        return image


    def onAction(self, optionindex):
        if optionindex == 0: self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, overlay):
        if actionid == RULES_ACTION_OVERLAY_OPEN:
            self.storedValues[0] = overlay._vinImage
            self.storedValues[1] = overlay._vinOffsetX,overlay._vinOffsetY
            
            overlay._vinImage    = self.setImage(actionid+.1, citem, overlay, MST3K_1)
            overlay._vinOffsetX, overlay._vinOffsetY  = (0,0)
            
        elif actionid == RULES_ACTION_OVERLAY_OPEN+.1:
            overlay._vinImage = self.setImage(actionid, citem, overlay, MST3K_2)
            overlay.setImage(overlay._vignette,overlay._vinImage)
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay._vinImage    = self.storedValues[0]
            overlay._vinOffsetX, overlay._vinOffsetY  = self.storedValues[1]
            if self.threadTimer.is_alive():
                try: 
                    self.threadTimer.cancel()
                    self.threadTimer.join()
                except: pass
        self.log("runAction, setting overlay image to %s (%s,%s)"%(overlay._vinImage,overlay._vinOffsetX,overlay._vinOffsetY))
        return parameter
        

class DisableOverlay(BaseRule):
    def __init__(self):
        self.myId               = 50
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30042)
        self.description        = LANGUAGE(33042)
        self.optionLabels       = [LANGUAGE(30042)]
        self.optionValues       = [SETTINGS.getSettingBool('Enable_Overlay')]
        self.optionDescriptions = [LANGUAGE(33042)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions   = [""]
        self.storedValues       = [list() for idx in self.optionValues]


    def copy(self):
        return DisableOverlay()


    def getTitle(self):
        if self.optionValues[0]: return LANGUAGE(30042)
        else:                    return LANGUAGE(30142)


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.enableOverlay
            player.enableOverlay = self.optionValues[0]
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.enableOverlay = self.storedValues[0]
        self.log("runAction, setting enableOverlay = %s"%(player.enableOverlay))
        return parameter


class ForceSubtitles(BaseRule):
    def __init__(self):
        self.myId               = 51
        self.ignore             = False
        self.exclude            = False
        self.name               = "Force Subtitles"
        self.description        = "Show Subtitles"
        self.optionLabels       = ['Force Subtitles?']
        self.optionValues       = [BUILTIN.isSubtitle()]
        self.optionDescriptions = [""]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions   = [""]
        self.storedValues       = [[]]


    def copy(self):
        return ForceSubtitles()


    def getTitle(self):
        if self.optionValues[0]: return 'Show Subtitles'
        else:                    return 'Hide Subtitles'


    def onAction(self, optionindex):
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


class DisableTrakt(BaseRule):
    def __init__(self):
        self.myId               = 52
        self.ignore             = False
        self.exclude            = False
        self.name               = "Trakt scrobbling"
        self.description        = "Disable Trakt scrobbling."
        self.optionLabels       = [LANGUAGE(30131)]
        self.optionValues       = [SETTINGS.getSettingBool('Disable_Trakt')]
        self.optionDescriptions = [LANGUAGE(33131)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions   = [""]
        self.storedValues       = [[]]


    def copy(self):
        return DisableTrakt()


    def getTitle(self):
        if self.optionValues[0]: return 'Enable Trakt scrobbling'
        else:                    return 'Disable Trakt scrobbling'


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.disableTrakt
            player.disableTrakt = self.optionValues[0]
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.disableTrakt = self.storedValues[0]
        self.log("runAction, setting disableTrakt = %s"%(player.disableTrakt))
        return parameter


class RollbackPlaycount(BaseRule):
    def __init__(self):
        self.myId               = 53
        self.ignore             = False
        self.exclude            = False
        self.name               = "Rollback Playcount"
        self.description        = "Passive Playback w/o playcount & progress tracking."
        self.optionLabels       = [LANGUAGE(30132)]
        self.optionValues       = [SETTINGS.getSettingBool('Rollback_Watched')]
        self.optionDescriptions = [LANGUAGE(33132)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions   = [""]
        self.storedValues       = [[]]


    def copy(self):
        return RollbackPlaycount()


    def getTitle(self):
        if self.optionValues[0]: return 'Rollback Playcount'
        else:                    return 'Tally Playcount'


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.rollbackPlaycount
            player.rollbackPlaycount = self.optionValues[0]
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.rollbackPlaycount = self.storedValues[0]
        self.log("runAction, setting rollbackPlaycount = %s"%(player.rollbackPlaycount))
        return parameter


class DisableReplay(BaseRule):
    def __init__(self):
        self.myId               = 54
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30153)
        self.description        = LANGUAGE(33153)
        self.optionLabels       = [LANGUAGE(30153)]
        self.optionValues       = [SETTINGS.getSettingInt('Restart_Percentage')]
        self.optionDescriptions = [LANGUAGE(33153)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions   = [list(range(0,100,5))]
        self.storedValues       = [list() for idx in self.optionValues]


    def copy(self):
        return DisableReplay()


    def getTitle(self):
        return LANGUAGE(32184)%(self.optionValues[0])


    def onAction(self, optionindex):
        self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.restartPercentage
            player.restartPercentage = self.optionValues[0]
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.restartPercentage = self.storedValues[0]
        self.log("runAction, setting restartPercentage = %s"%(player.restartPercentage))
        return parameter


class DurationOptions(BaseRule):
    def __init__(self):
        self.myId               = 500
        self.ignore             = False
        self.exclude            = False
        self.name               = "Duration Options"
        self.description        = "Parser Options"
        self.optionLabels       = [LANGUAGE(30049),LANGUAGE(30052),"Minimum Duration"]
        self.optionValues       = [SETTINGS.getSettingInt('Duration_Type'),SETTINGS.getSettingBool('Store_Duration'),SETTINGS.getSettingInt('Seek_Tolerance')]
        self.optionDescriptions = [LANGUAGE(33015),LANGUAGE(33049),LANGUAGE(33052),"Minimum Duration"]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP,RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions   = [{LANGUAGE(30050):0,LANGUAGE(30051):1},[],list(range(0,605,5))]
        self.storedValues       = [[],[],[]]


    def copy(self):
        return DurationOptions()


    def getTitle(self):
        msgs = []
        if self.optionValues[0]: msgs.append('%s (%s)'%(self.optionLabels[0],self.optionValues[0]))
        if self.optionValues[1]: msgs.append('%s (%s)'%(self.optionLabels[1],self.optionValues[1]))
        if self.optionValues[2]: msgs.append('%s (%s)'%(self.optionLabels[2],self.optionValues[2]))
        return ', '.join(msgs)


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, inherited):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = inherited.accurateDuration
            self.storedValues[1] = inherited.saveDuration
            self.storedValues[2] = inherited.minDuration
            inherited.accurateDuration = self.optionValues[0]
            inherited.saveDuration     = self.optionValues[1]
            inherited.minDuration      = self.optionValues[2]
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            inherited.accurateDuration = self.storedValues[0]
            inherited.saveDuration     = self.storedValues[1]
            inherited.minDuration      = self.storedValues[2]
        self.log("runAction, setting accurateDuration = %s"%(inherited.accurateDuration))
        self.log("runAction, setting saveDuration = %s"%(inherited.saveDuration))
        self.log("runAction, setting minDuration = %s"%(inherited.minDuration))
        return parameter


class FilterOptions(BaseRule):
    def __init__(self):
        self.myId               = 500
        self.ignore             = False
        self.exclude            = False
        self.name               = "Filter Options"
        self.description        = "Filter various content."
        self.optionLabels       = [LANGUAGE(30053),LANGUAGE(30054),LANGUAGE(30055)]
        self.optionValues       = [SETTINGS.getSettingBool('Enable_Extras'),SETTINGS.getSettingBool('Enable_Strms'),SETTINGS.getSettingBool('Enable_3D')]
        self.optionDescriptions = [LANGUAGE(33053),LANGUAGE(33054),LANGUAGE(33055)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [""]
        self.storedValues       = [[],[],[]]


    def copy(self):
        return FilterOptions()


    def getTitle(self):
        msgs = []
        if self.optionValues[0]: msgs.append(self.optionLabels[0])
        if self.optionValues[1]: msgs.append(self.optionLabels[1])
        if self.optionValues[2]: msgs.append(self.optionLabels[2])
        return ', '.join(msgs)


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.incExtras
            self.storedValues[1] = builder.incStrms
            self.storedValues[2] = builder.inc3D
            builder.incExtras = self.optionValues[0]
            builder.incStrms  = self.optionValues[1]
            builder.inc3D     = self.optionValues[2]
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.incExtras = self.storedValues[0]
            builder.incStrms  = self.storedValues[1]
            builder.inc3D     = self.storedValues[2]
        self.log("runAction, setting incExtras = %s"%(builder.incExtras))
        self.log("runAction, setting incStrms = %s"%(builder.incStrms))
        self.log("runAction, setting inc3D = %s"%(builder.inc3D))
        return parameter


class ProvisionalRule(BaseRule):
    def __init__(self):
        self.myId               = 800
        self.ignore             = True
        self.exclude            = True
        self.name               = "Provisional Path"
        self.description        = "Fill Provisional Path"
        self.optionLabels       = ["Provisional Value"]
        self.optionValues       = [""]
        self.optionDescriptions = [""]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE]
        self.selectBoxOptions   = [""]
        self.storedValues       = [[]]
        

    def copy(self): 
        return ProvisionalRule()
        
        
    def getTitle(self): 
        if len(self.optionValues[0]) > 0: return "%s (%s)"%(self.name, self.optionValues[0])
        else:                             return self.name
            
  
    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE: 
            PROVISIONAL_TYPES = {"TV Shows"     : [{"path":"videodb://tvshows/titles/" ,"limit":"","sort":{"method":"episode","order":"ascending"},"filter":{"and":[{"field":"tvshow","operator":"is","value":""}]},
                                                    "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"}],
                                 "TV Networks"  : [{"path":"videodb://tvshows/titles/","limit":"","sort":{"method":"episode","order":"ascending"} ,"filter":{"and":[{"field":"studio","operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"}],
                                 "Movie Studios": [{"path":"videodb://movies/titles/" ,"limit":"","sort":{"method":"random" ,"order":"ascending"} ,"filter":{"and":[{"field":"studio","operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie","key":"movies"}],
                                 "TV Genres"    : [{"path":"videodb://tvshows/titles/" ,"limit":"","sort":{"method":"random","order":"ascending"} ,"filter":{"and":[{"field":"genre" ,"operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"}],
                                 "Movie Genres" : [{"path":"videodb://movies/titles/"  ,"limit":"","sort":{"method":"random" ,"order":"ascending"},"filter":{"and":[{"field":"genre" ,"operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie","key":"movies"}],
                                 "Mixed Genres" : [{"path":"videodb://tvshows/titles/" ,"limit":"","sort":{"method":"random","order":"ascending"} ,"filter":{"and":[{"field":"genre" ,"operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetEpisodes","enum":"Video.Fields.Episode","key":"episodes"},
                                                   {"path":"videodb://movies/titles/"  ,"limit":"","sort":{"method":"random" ,"order":"ascending"},"filter":{"and":[{"field":"genre" ,"operator":"contains","value":""}]},
                                                    "method":"VideoLibrary.GetMovies"  ,"enum":"Video.Fields.Movie","key":"movies"}]}

            if self.optionValues[0]:
                if builder.pDialog: builder.pDialog = self.dialog.progressBGDialog(builder.pCount, builder.pDialog, message='Applying Rule: %s'%(self.name),header='%s, %s'%(ADDON_NAME,builder.pMSG))
                if self.optionValues[0] == "Seasonal": queries = list(Seasonal().buildSeasonal())
                else:                                  queries = PROVISIONAL_TYPES.get(citem['type'],[])
                self.log("%s: runAction, id: %s, provisional value = %s\nqueries = %s"%(self.__class__.__name__,citem.get('id'),self.optionValues[0],queries))
                for provisional in queries:
                    if not provisional: continue
                    elif builder.service._interrupt(): break
                    else:
                        if self.optionValues[0] == "Seasonal": citem['logo'] = provisional.get('holiday',{}).get('logo',citem['logo'])
                        else: provisional["filter"]["and"][0]['value'] = self.optionValues[0]
                        if not builder.incExtras and provisional["key"].startswith(tuple(TV_TYPES)): #filter out extras/specials
                            provisional["filter"].setdefault("and",[]).extend([{"field":"season" ,"operator":"greaterthan","value":"0"},
                                                                               {"field":"episode","operator":"greaterthan","value":"0"}])
                        fileList, dirList = builder.buildList(citem, provisional.get('path'), media='video', page=(provisional.get('limit') or builder.limit), sort=provisional.get('sort'), limits=builder.limits, dirItem={}, query=provisional)
                        if len(fileList) > 0: self.storedValues[0].append(fileList)
                return [_f for _f in self.storedValues.pop(0) if _f]
        return parameter
       
       
class HandleMethodOrder(BaseRule):
    def __init__(self):
        self.myId               = 950
        self.ignore             = False
        self.exclude            = True
        self.name               = "Limits & Sort Methods"
        self.description        = "Change content limits and sorting methods."
        self.optionLabels       = ['Page Limit','Method','Order','Ignore Folders','Ignore Artist Sort Name']
        self.optionValues       = [REAL_SETTINGS.getSettingInt('Page_Limit'),'random','ascending',True,True]
        self.optionDescriptions = ["","","","",""]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [list(range(25,525,25)), self.getSort(), self.getOrder(),"",""]
        self.storedValues       = [[],[],[],[],[]]
        self.cache              = SETTINGS.cacheDB
        
        
    def copy(self):
        return HandleMethodOrder()


    def getTitle(self):
        return self.name


    def getSort(self):
        from jsonrpc import JSONRPC
        jsonrpc = JSONRPC()
        values  = jsonrpc.getEnums("List.Sort",type="method")
        del jsonrpc
        return values


    def getOrder(self):
        from jsonrpc import JSONRPC
        jsonrpc = JSONRPC()
        values  = jsonrpc.getEnums("List.Sort",type="order")
        del jsonrpc
        return values


    def onAction(self, optionindex):
        if optionindex in [3,4]: self.onActionToggleBool(optionindex)
        else:                    self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.limit
            self.storedValues[1] = builder.sort
            builder.limit = self.optionValues[0]
            builder.sort.update({"ignorearticle":self.optionValues[2],"method":self.optionValues[0],"order":self.optionValues[1],"useartistsortname":self.optionValues[3]})
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.limit = self.storedValues[0]
            builder.sort  = self.storedValues[1]
            
        self.log("runAction, setting limit = %s"%(builder.limit))
        self.log("runAction, setting sort = %s"%(builder.sort))
        return citem


class ForceEpisode(BaseRule):
    def __init__(self):
        self.myId               = 998
        self.ignore             = False
        self.exclude            = False
        self.name               = "Force Episode Ordering"
        self.description        = "Force TV to episodes order, Movies to year."
        self.optionLabels       = ['Force Random','Interleave TV & Movies']
        self.optionValues       = [True,True]
        self.optionDescriptions = ["",""]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE,RULES_ACTION_CHANNEL_BUILD_PATH,RULES_ACTION_CHANNEL_BUILD_FILELIST]
        self.selectBoxOptions   = ["",""]
        self.storedValues       = [dict(),dict(),list(),list(),list()]


    def copy(self):
        return ForceEpisode()


    def getTitle(self):
        return 'Force Episode Sort (%s)'%(self.optionValues[0])


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        def _episodeSort(showArray: dict={}):
            for show, fileItems in list(showArray.items()):
                self.storedValues[3] = []
                for item in fileItems:
                    if (int(item.get("season","0")) + int(item.get("episode","0"))) > 0: 
                        self.storedValues[3].append([int(item.get("season","0")), int(item.get("episode","0")), item])
                    else:
                        self.storedValues[2].append(item)
                    
                self.storedValues[3].sort(key=lambda seep: seep[1])
                self.storedValues[3].sort(key=lambda seep: seep[0])
                for seepitem in self.storedValues[3]: self.storedValues[4].append(seepitem[2])
            return self.storedValues[4]

        def _sortShows(fileList: list=[]): #group by type & show; no duplicates. 
            for fileItem in fileList:
                if fileItem.get('type').startswith(tuple(TV_TYPES)):
                    if fileItem not in self.storedValues[1].setdefault(fileItem['showtitle'],[]):
                        self.storedValues[1].setdefault(fileItem['showtitle'],[]).append(fileItem)
                else:
                    if fileItem not in self.storedValues[2]: self.storedValues[2].append(fileItem)
            return _episodeSort(self.storedValues[1]), sorted(self.storedValues[2], key=lambda k: k.get('year',0))

        if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
            self.storedValues[0] = builder.sort
        elif actionid == RULES_ACTION_CHANNEL_BUILD_PATH:
            if parameter.startswith(tuple(['videodb://%s'%tv for tv in TV_TYPES])):
                builder.sort.update({"method":"episode"})
            elif parameter:
                builder.sort.update({"method":"year"})
            self.log("runAction, setting sort to %s"%(builder.sort))
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST:
            builder.sort = self.storedValues[0]
            self.log("runAction, restoring sort and forcing episode/year ordering (%s)"%(len(parameter)))
            fileList = list(sorted(parameter, key=lambda k: k.get('year',0)))
            if self.optionValues[1]: return interleave(list(_sortShows(fileList)))
            else:                    return [j for i in _sortShows(fileList) for j in i]
        return parameter
        
        
class ForceRandom(BaseRule):
    def __init__(self):
        self.myId               = 999
        self.ignore             = False
        self.exclude            = False
        self.name               = "Force Random Ordering"
        self.description        = "Random sort & shuffle channel content."
        self.optionLabels       = ['Force Random']
        self.optionValues       = [True]
        self.optionDescriptions = [""]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE,RULES_ACTION_CHANNEL_BUILD_FILELIST]
        self.selectBoxOptions   = [""]
        self.storedValues       = [dict()]


    def copy(self):
        return ForceRandom()


    def getTitle(self):
        return 'Force Random Sort (%s)'%(self.optionValues[0])


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, fileList, builder):
        if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
            self.storedValues[0] = builder.sort
            builder.sort.update({"method":"random"})
            self.log("runAction, setting sort to %s"%(builder.sort))
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST:
            builder.sort = self.storedValues[0]
            self.log("runAction, restoring sort and forcing random shuffle of %s items"%(len(fileList)))
            return randomShuffle(fileList)
        return fileList
        

class EvenShowsRule(BaseRule):
    def __init__(self):
        self.myId               = 1000
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30121)
        self.description        = "Group TV shows in blocks, query size impacts distribution." 
        self.optionLabels       = ['Group TV shows in blocks','Page Size','Group by Episode']
        self.optionValues       = [SETTINGS.getSettingInt('Enable_Even'),SETTINGS.getSettingInt('Page_Limit'),True]
        self.optionDescriptions = [LANGUAGE(33121),"",""]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE,RULES_ACTION_CHANNEL_BUILD_PATH,RULES_ACTION_CHANNEL_BUILD_FILELIST,RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST]
        self.selectBoxOptions   = [list(range(1,6)),list(range(25,501,25)),list()]
        self.storedValues       = [dict(),list(),SETTINGS.getSettingInt('Page_Limit')]
        

    def copy(self): 
        return EvenShowsRule()
        
        
    def getTitle(self): 
        return "%s (%s)%s%s (%s)"%(self.optionLabels[0],self.optionValues[0],{True:', %s, '%(self.optionLabels[2]),False:', '}[self.optionValues[2]],self.optionLabels[1],(self.optionValues[1]))


    def onAction(self, optionindex):
        if optionindex in [0,1]:
            self.onActionSelect(optionindex,self.optionLabels[optionindex])
            self.validate(optionindex)
        elif optionindex ==2:    self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def validate(self, optionindex):
        if   optionindex == 0: self.validateDigitBox(optionindex, 0, 5, self.optionValues[optionindex])
        elif optionindex == 1: self.validateDigitBox(optionindex, 25, 500, self.optionValues[optionindex])


    def runAction(self, actionid, citem, parameter, builder):
        def _chunkShows(showArray: dict={}):
            for show, episodes in list(showArray.items()):
                yield show,[episodes[i:i+self.optionValues[0]] for i in range(0,len(episodes),self.optionValues[0])]

        def _sortShows(fileItems): #group by type & show; no duplicates. 
            for fileItem in fileItems:
                if fileItem.get('type').startswith(tuple(TV_TYPES)):
                    if fileItem not in self.storedValues[0].setdefault(fileItem['showtitle'],[]):
                        self.storedValues[0].setdefault(fileItem['showtitle'],[]).append(fileItem)
                else:
                    if fileItem not in self.storedValues[1]: self.storedValues[1].append(fileItem)
            return dict(_chunkShows(self.storedValues[0])), self.storedValues[1]

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
                
        if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
            self.storedValues[2] = builder.limit # store global pagination limit
            self.log('runAction, saving limit %s'%(builder.limit))
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_PATH:
            if parameter.startswith(tuple(['videodb://%s'%tv for tv in TV_TYPES])):
                builder.limit = self.storedValues[2] * self.optionValues[0] #Double parser limit for tv content inorder to aid even distro. 
            elif parameter:
                builder.limit = self.storedValues[2]
            self.log('runAction, changing limit %s'%(builder.limit))
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST:
            try:
                if parameter:
                    if builder.pDialog: builder.pDialog = self.dialog.progressBGDialog(builder.pCount, builder.pDialog, message='Applying Rule: %s'%(self.name),header='%s, %s'%(ADDON_NAME,builder.pMSG))
                    if self.optionValues[2]: fileItems = list(sorted(parameter, key=lambda k: k.get('episode',0)))
                    else:                    fileItems = parameter
                    self.log('runAction, even distribution %s'%(self.optionValues[0]))
                    return _mergeShows(*(_sortShows(fileItems)))
            except Exception as e: log("runAction, failed! %s"%(e), xbmc.LOGERROR)
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST:
            builder.limit = self.storedValues[2] # restore global pagination limit
            self.log('runAction, restoring limit %s'%(self.storedValues[2]))
        return parameter
        
        