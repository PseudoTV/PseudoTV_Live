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
  
class RulesList:
    def __init__(self, channels=None):
        self.log('__init__')
        self.ruleList  = [BaseRule(),
                          ShowChannelBug(),
                          ShowOnNext(),
                          SetScreenVingette(),
                          MST3k(),
                          DisableOverlay(),
                          ForceSubtitles(),
                          DisableTrakt(),
                          RollbackPlaycount(),
                          DisableRestart(),
                          DisableOnChange(),
                          DurationOptions(),
                          IncludeOptions(),
                          PreRoll(),
                          PostRoll(),
                          InterleaveValue(),
                          ProvisionalRule(),
                          HandleMethodOrder(),
                          ForceEpisode(),
                          ForceRandom(),
                          EvenShowsRule(),
                          PauseRule()]
        self.ruleItems = self.loadRules(channels)
                         

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
                try:
                    if not incRez and rule.ignore: continue
                    try:    chrule = chrules.get(str(rule.myId)) #temp fix.issue after converting list to dict in channels.json
                    except: chrule = {}
                    if chrule:
                        ruleInstance = rule.copy()
                        for key, value in list(chrule.get('values',{}).items()):
                            ruleInstance.optionValues[int(key)] = value
                        ruleList.update({str(rule.myId):ruleInstance})
                    elif append: ruleList.update({str(rule.myId):rule.copy()})
                except Exception as e: log('loadRules: _load failed! %s\nchrule = %s'%(e,chrule), xbmc.LOGERROR)
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
        rules = self.ruleItems.get(citem.get('id',''))
        if not rules: rules = (self.loadRules([citem]).get(citem.get('id','')) or {})
        for myId, rule in list(sorted(rules.items())):
            if action in rule.actions:
                self.log("runActions, %s performing channel rule: %s"%(inherited.__class__.__name__,rule.name))
                parameter = rule.runAction(action, citem, parameter, inherited)
        return parameter


class BaseRule:
    dialog = Dialog()
    
    def __init__(self):
        self.myId               = 0
        self.ignore             = False #ignore from manager options, reserved for auto-tuning
        self.exclude            = False #applies only to db queries not smart-playlists
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


    def log(self, msg, level=xbmc.LOGDEBUG):
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


    def onActionSelect(self, optionindex, header=None, preselect=None, useDetails=False, autoclose=SELECT_DELAY, multi=False):
        log("onActionSelect")
        if header is None:
            if multi: header = '%s - %s'%(ADDON_NAME,LANGUAGE(32017)%(''))
            else:     header = '%s - %s'%(ADDON_NAME,LANGUAGE(32223)%(''))
        
        if isinstance(self.selectBoxOptions[optionindex],dict):
            selectBoxOptions = list(self.selectBoxOptions[optionindex].keys())
            preselect = findItemsInLST(list(self.selectBoxOptions[optionindex].values()), self.optionValues[optionindex])
        else:
            selectBoxOptions = self.selectBoxOptions[optionindex]
            preselect = findItemsInLST(self.selectBoxOptions[optionindex], self.optionValues[optionindex])
        
        select = self.dialog.selectDialog([str(v).title() for v in selectBoxOptions], header, preselect, useDetails, autoclose, multi)
        if not select is None: 
            if isinstance(self.selectBoxOptions[optionindex],dict):
                self.optionValues[optionindex] = self.selectBoxOptions[optionindex].get(selectBoxOptions[select])
            else:
                self.optionValues[optionindex] = selectBoxOptions[select]
                
          
    def onActionBrowse(self, optionindex, type=0, heading=ADDON_NAME, shares='', mask='', useThumbs=True, treatAsFolder=False, multi=False, monitor=False, options=[], exclude=[]):
        log("onActionBrowse")
        info = self.dialog.browseSources(type, heading, self.optionValues[optionindex], shares, mask, useThumbs, treatAsFolder, multi, monitor, options, exclude)
        if info is not None: self.optionValues[optionindex] = info 
    
    
    def onActionMultiBrowse(self, optionindex, header=ADDON_NAME, exclude=[], monitor=True):
        log("onActionMultiBrowse")
        info = self.dialog.multiBrowse(self.optionValues[optionindex], header, exclude, monitor)
        if info is not None: self.optionValues[optionindex] = info 


    def onActionResources(self, optionindex, ftype=''):
        log("onActionResources")
        info = self.dialog.browseResources(self.optionValues[optionindex].split('|'), ftype=ftype)
        if not info is None: self.optionValues[optionindex] = '|'.join(info)

#Rules apply sequentially by myId
class ShowChannelBug(BaseRule): #OVERLAY RULES [1-49]
    def __init__(self):
        self.myId               = 1
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30143)
        self.description        = LANGUAGE(30144)
        self.optionLabels       = [LANGUAGE(30043),LANGUAGE(30086),LANGUAGE(30112),LANGUAGE(30044),LANGUAGE(30113)]
        self.optionValues       = [SETTINGS.getSettingBool('Enable_ChannelBug'),SETTINGS.getSettingInt("Channel_Bug_Interval"),SETTINGS.getSetting("Channel_Bug_Position_XY"),SETTINGS.getSetting('ChannelBug_Color'),SETTINGS.getSettingBool('Force_Diffuse')]
        self.optionDescriptions = [LANGUAGE(33043),LANGUAGE(33086),LANGUAGE(33112),LANGUAGE(33044),LANGUAGE(33111)]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = ["",list(range(-1,16)),[LANGUAGE(30022),LANGUAGE(32136)],"",""]
        self.storedValues       = [[],[],[],[],[]]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return ShowChannelBug()


    def getTitle(self):
        if self.optionValues[0]: return LANGUAGE(30145)%({'-1':LANGUAGE(32224),'0':LANGUAGE(32225)}.get(str(self.optionValues[1]),LANGUAGE(30146)%(self.optionValues[1])),self.optionValues[2],{True:LANGUAGE(32226),False:''}[self.optionValues[4]],self.optionValues[3])
        else:                    return LANGUAGE(30147)


    def getPosition(self, optionindex):
        orgvalue = self.optionValues[optionindex]
        self.onActionSelect(optionindex, LANGUAGE(32223)%(''))
        if self.optionValues[optionindex] == self.selectBoxOptions[optionindex][1]:
            from overlaytool import OverlayTool
            overlaytool = OverlayTool(OVERLAYTOOL_XML, ADDON_PATH, "default", ADV_RULES=True, Focus_IDX=1, Channel_Bug_Position_XY=self.optionValues[optionindex], ChannelBug_Color=self.optionValues[3])
            del overlaytool
            value = PROPERTIES.getProperty("Channel_Bug_Position_XY")
            PROPERTIES.clearProperty("Channel_Bug_Position_XY")
            if value: self.optionValues[optionindex] = value
            else:     self.optionValues[optionindex] = orgvalue
        elif self.optionValues[optionindex] != self.selectBoxOptions[optionindex][0]:
            self.optionValues[optionindex] = orgvalue


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
            overlay.channelBugX, overlay.channelBugY = eval(self.optionValues[2])
            overlay.channelBugColor    = '0x%s'%(self.optionValues[3])
            overlay.channelBugDiffuse  = self.optionValues[4]
            self.log("runAction, setting enableChannelBug = %s, channelBugInterval = %s, channelBugInterval = %s, channelBugColor = %s, channelBugDiffuse = %s"%(overlay.enableChannelBug,overlay.channelBugInterval,(overlay.channelBugX, overlay.channelBugY),overlay.channelBugColor,overlay.channelBugDiffuse))
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay.enableChannelBug   = self.storedValues[0]
            overlay.channelBugInterval = self.storedValues[1]
            overlay.channelBugX, overlay.channelBugY = self.storedValues[2]
            overlay.channelBugColor   = self.storedValues[3]
            overlay.channelBugDiffuse = self.storedValues[4]
            self.log("runAction, restoring enableChannelBug = %s, channelBugInterval = %s, channelBugInterval = %s, channelBugColor = %s, channelBugDiffuse = %s"%(overlay.enableChannelBug,overlay.channelBugInterval,(overlay.channelBugX, overlay.channelBugY),overlay.channelBugColor,overlay.channelBugDiffuse))
        return parameter


class ShowOnNext(BaseRule):
    def __init__(self):
        self.myId               = 2
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30045)
        self.description        = LANGUAGE(33045)
        self.optionLabels       = [LANGUAGE(30045),LANGUAGE(32229),LANGUAGE(30044),LANGUAGE(30196)]
        self.optionValues       = [bool(SETTINGS.getSettingInt('OnNext_Enable')),SETTINGS.getSetting("OnNext_Position_XY"),SETTINGS.getSetting("OnNext_Color"),SETTINGS.getSettingInt('OnNext_Enable')]
        self.optionDescriptions = [LANGUAGE(30045),LANGUAGE(33229),LANGUAGE(33044),LANGUAGE(30196)]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = ["",[LANGUAGE(30022),LANGUAGE(32136)],"",{LANGUAGE(30021):0,LANGUAGE(30193):1,LANGUAGE(30194):2,LANGUAGE(30197):3,LANGUAGE(30195):4}]
        self.storedValues       = [[],[],[],[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return ShowOnNext()


    def getTitle(self):
        return '%s (%s)'%(LANGUAGE(30045), self.optionValues[0])


    def getPosition(self, optionindex):
        orgvalue = self.optionValues[optionindex]
        self.onActionSelect(optionindex, LANGUAGE(32223)%(''))
        if self.optionValues[optionindex] == self.selectBoxOptions[optionindex][1]:
            from overlaytool import OverlayTool
            overlaytool = OverlayTool(OVERLAYTOOL_XML, ADDON_PATH, "default", ADV_RULES=True, Focus_IDX=0, OnNext_Position_XY=self.optionValues[optionindex], OnNext_Color=self.optionValues[2])
            del overlaytool
            value = PROPERTIES.getProperty("OnNext_Position_XY")
            PROPERTIES.clearProperty("OnNext_Position_XY")
            if value: self.optionValues[optionindex] = value
            else:     self.optionValues[optionindex] = orgvalue
        elif self.optionValues[optionindex] != self.selectBoxOptions[optionindex][0]:
            self.optionValues[optionindex] = orgvalue


    def onAction(self, optionindex):
        if   optionindex == 0: self.onActionToggleBool(optionindex)
        elif optionindex == 1: self.getPosition(optionindex)
        elif optionindex == 2: self.onActionPickColor(optionindex)
        elif optionindex == 3: self.onActionSelect(optionindex, LANGUAGE(30196))
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, overlay):
        if actionid == RULES_ACTION_OVERLAY_OPEN:
            self.storedValues[0] = overlay.enableOnNext
            self.storedValues[1] = (overlay.onNextX, overlay.onNextY)
            self.storedValues[2] = overlay.onNextColor
            self.storedValues[3] = overlay.onNextMode

            overlay.enableOnNext             = self.optionValues[0]
            overlay.onNextX, overlay.onNextY = eval(self.optionValues[1])
            overlay.onNextColor              = '0x%s'%(self.optionValues[2])
            self.log("runAction, setting enableOnNext = %s, onNextX = %s, onNextY = %s, onNextColor = %s, onNextMode = %s"%(overlay.enableOnNext, overlay.onNextX, overlay.onNextY, overlay.onNextColor, overlay.onNextMode))
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay.enableOnNext             = self.storedValues[0]
            overlay.onNextX, overlay.onNextY = self.storedValues[1]
            overlay.onNextColor              = self.storedValues[2]
            overlay.onNextMode               = self.storedValues[3]
            self.log("runAction, restoring enableOnNext = %s, onNextX = %s, onNextY = %s, onNextColor = %s, onNextMode = %s"%(overlay.enableOnNext, overlay.onNextX, overlay.onNextY, overlay.onNextColor, overlay.onNextMode))
        return parameter


class SetScreenVingette(BaseRule):
    def __init__(self):
        self.myId               = 3
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30177)
        self.description        = LANGUAGE(33177)
        self.optionLabels       = [LANGUAGE(30174),LANGUAGE(30175),LANGUAGE(30176),LANGUAGE(30178),LANGUAGE(30185),LANGUAGE(30186)]
        self.optionValues       = [False,' ',1.00,0.00,1.00,False]
        self.optionDescriptions = [LANGUAGE(33174),LANGUAGE(33175),LANGUAGE(33176),LANGUAGE(33179),LANGUAGE(33185),LANGUAGE(34186)]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = ['','',list(frange(5,21,1)),list(range(-2,3,1)),list(frange(5,21,1)),'']#[LANGUAGE(30022),LANGUAGE(32136)]]
        self.storedValues       = [[],[],[]]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return SetScreenVingette()


    def getTitle(self):
        if self.optionValues[0]: return '%s @ %s x %s\n%s'%(LANGUAGE(32227),self.optionValues[2],self.optionValues[3],self.getImage(self.optionValues[1]))
        else:                    return LANGUAGE(32228)
            
            # todo set viewmode as dict() response from json.
    def getPosition(self, optionindex):#todo vin utility to adjust zoom,vshift,pratio and nls
        self.dialog.notificationDialog(LANGUAGE(32020))


    def getImage(self, image=''):
        self.log('getImage, In image = %s'%(image))
        day    = re.compile(r'\_Day(.*?)', re.IGNORECASE).search(image)
        night  = re.compile(r'\_Night(.*?)', re.IGNORECASE).search(image)
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
        if   optionindex == 1:       self.onActionBrowse(optionindex, type=1, heading=self.optionLabels[1], mask=xbmc.getSupportedMedia('picture'), exclude=[12,13,14,15,16,17,22])
        elif optionindex in [0,5]:   self.onActionToggleBool(optionindex)
        elif optionindex in [2,3,4]: self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, overlay):
        if actionid == RULES_ACTION_OVERLAY_OPEN:
            self.storedValues[0] = overlay.enableVignette
            self.storedValues[1] = overlay._vinImage
            self.storedValues[2] = overlay._vinViewMode
            
            overlay.enableVignette = self.optionValues[0]
            overlay._vinImage      = self.getImage(self.optionValues[1])
            overlay._vinViewMode   = {"nonlinearstretch":self.optionValues[5] ,"pixelratio":self.optionValues[4],"verticalshift":self.optionValues[3],"viewmode":"custom","zoom": self.optionValues[2]}
            self.log('runAction, setting vignette image = %s\nmode = %s'%(overlay._vinImage,overlay._vinViewMode))
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay.enableVignette = self.storedValues[0]
            overlay._vinImage      = self.storedValues[1]
            overlay._vinViewMode   = self.storedValues[2]
            self.log('runAction, restoring vignette image = %s\nmode = %s'%(overlay._vinImage,overlay._vinViewMode))


class MST3k(BaseRule):
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
        self.storedValues       = [[],[],[]]
        self.threadTimer        = Timer(5.0, self.runAction)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

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
            self.storedValues[1] = overlay._vinOffsetXY
            self.storedValues[2] = overlay._vinZoom
            
            overlay._vinImage    = self.setImage(actionid+.1, citem, overlay, MST3K_1)
            overlay._vinOffsetXY = (0,0)
            overlay._vinZoom     = 1.0
            self.log("runAction, setting overlay enabled = %s, image %s @ (%s) X %s"%(overlay.enableVignette, overlay._vinImage, overlay._vinOffsetXY, overlay._vinZoom))
            
        elif actionid == RULES_ACTION_OVERLAY_OPEN+.1:
            overlay._vinImage = self.setImage(actionid, citem, overlay, MST3K_2)
            overlay._setImage(overlay._vignette,overlay._vinImage)
            self.log("runAction, setting overlay enabled = %s, image %s @ (%s) X %s"%(overlay.enableVignette, overlay._vinImage, overlay._vinOffsetXY, overlay._vinZoom))
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay._vinImage    = self.storedValues[0]
            overlay._vinOffsetXY = self.storedValues[1]
            overlay._vinZoom     = self.storedValues[2]
            self.log("runAction, restoring overlay enabled = %s, image %s @ (%s) X %s"%(overlay.enableVignette, overlay._vinImage, overlay._vinOffsetXY, overlay._vinZoom))
            
            if self.threadTimer.is_alive():
                if hasattr(thread, 'cancel'): self.threadTimer.cancel()
                try: self.threadTimer.join()
                except: pass
        return parameter
        

class DisableOverlay(BaseRule): #PLAYER RULES [50-99]
    def __init__(self):
        self.myId               = 50
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30170)
        self.description        = LANGUAGE(33042)
        self.optionLabels       = [LANGUAGE(30170)]
        self.optionValues       = [SETTINGS.getSettingBool('Overlay_Enable')]
        self.optionDescriptions = [LANGUAGE(33042)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return DisableOverlay()


    def getTitle(self):
        if self.optionValues[0]: return LANGUAGE(30170)
        else:                    return LANGUAGE(30170)


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.enableOverlay
            player.enableOverlay = self.optionValues[0]
            self.log("runAction, setting enableOverlay = %s"%(player.enableOverlay))
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.enableOverlay = self.storedValues[0]
            self.log("runAction, restore enableOverlay = %s"%(player.enableOverlay))
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
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

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
            self.log("runAction, setting lastSubState = %s"%(player.lastSubState))
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.lastSubState = self.storedValues[0]
            self.log("runAction, restoring lastSubState = %s"%(player.lastSubState))
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
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

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
            self.log("runAction, setting disableTrakt = %s"%(player.disableTrakt))
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.disableTrakt = self.storedValues[0]
            self.log("runAction, restoring disableTrakt = %s"%(player.disableTrakt))
        return parameter


class RollbackPlaycount(BaseRule):
    """
    RollbackPlaycount
    """
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
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

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
            self.log("runAction, setting rollbackPlaycount = %s"%(player.rollbackPlaycount))
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.rollbackPlaycount = self.storedValues[0]
            self.log("runAction, restoring rollbackPlaycount = %s"%(player.rollbackPlaycount))
        return parameter


class DisableRestart(BaseRule):
    """
    DisableRestart
    """
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
        self.selectBoxOptions   = [list(range(25,100,5))]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return DisableRestart()


    def getTitle(self):
        return LANGUAGE(32184)%(self.optionValues[0])


    def onAction(self, optionindex):
        self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.restartPercentage
            player.restartPercentage = self.optionValues[0]
            self.log("runAction, setting restartPercentage = %s"%(player.restartPercentage))
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.restartPercentage = self.storedValues[0]
            self.log("runAction, restoring restartPercentage = %s"%(player.restartPercentage))
        return parameter

        
class DisableOnChange(BaseRule):
    """
    DisableOnChange
    """
    def __init__(self):
        self.myId               = 55
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30170)
        self.description        = LANGUAGE(33171)
        self.optionLabels       = [LANGUAGE(30170)]
        self.optionValues       = [SETTINGS.getSettingBool('Enable_OnInfo')]
        self.optionDescriptions = [LANGUAGE(33171)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return DisableOverlay()


    def getTitle(self):
        if self.optionValues[0]: return LANGUAGE(30170)
        else:                    return LANGUAGE(30171)


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.infoOnChange
            player.infoOnChange = self.optionValues[0]
            self.log("runAction, setting infoOnChange = %s"%(player.infoOnChange))
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.infoOnChange = self.storedValues[0]
            self.log("runAction, restoring infoOnChange = %s"%(player.infoOnChange))
        return parameter


class DurationOptions(BaseRule): #CHANNEL RULES [500-599]
    """
    DurationOptions
    """
    def __init__(self):
        self.myId               = 500
        self.ignore             = False
        self.exclude            = False
        self.name               = "Duration Options"
        self.description        = "Duration Options"
        self.optionLabels       = [LANGUAGE(30049),LANGUAGE(30052),LANGUAGE(32233)]
        self.optionValues       = [SETTINGS.getSettingInt('Duration_Type'),SETTINGS.getSettingBool('Store_Duration'),SETTINGS.getSettingInt('Seek_Tolerance')]
        self.optionDescriptions = [LANGUAGE(33015),LANGUAGE(33049),LANGUAGE(33052),LANGUAGE(32233)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [{LANGUAGE(30050):0,LANGUAGE(30051):1},[],list(range(0,605,5))]
        self.storedValues       = [[],[],[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return DurationOptions()


    def getTitle(self):
        msgs = []
        if self.optionValues[0]: msgs.append('%s (%s)'%(self.optionLabels[0],self.optionValues[0]))
        if self.optionValues[1]: msgs.append('%s (%s)'%(self.optionLabels[1],self.optionValues[1]))
        if self.optionValues[2]: msgs.append('%s (%s)'%(self.optionLabels[2],self.optionValues[2]))
        return ', '.join(msgs)


    def onAction(self, optionindex):
        if optionindex == 0:
            self.onActionSelect(optionindex, LANGUAGE(30049))
            self.validateRange(optionindex, 0, 1, 0)
        else:
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
            self.log("runAction, setting accurateDuration = %s, saveDuration = %s, minDuration = %s"%(inherited.accurateDuration,inherited.saveDuration,inherited.minDuration))
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            inherited.accurateDuration = self.storedValues[0]
            inherited.saveDuration     = self.storedValues[1]
            inherited.minDuration      = self.storedValues[2]
            self.log("runAction, restoring accurateDuration = %s, saveDuration = %s, minDuration = %s"%(inherited.accurateDuration,inherited.saveDuration,inherited.minDuration))
        return parameter


class IncludeOptions(BaseRule):
    """
    IncludeOptions
    """
    def __init__(self):
        self.myId               = 501
        self.ignore             = False
        self.exclude            = False
        self.name               = "Include Options"
        self.description        = "Include Options"
        self.optionLabels       = [LANGUAGE(30053),LANGUAGE(30054),LANGUAGE(30055)]
        self.optionValues       = [SETTINGS.getSettingBool('Enable_Extras'),SETTINGS.getSettingBool('Enable_Strms'),SETTINGS.getSettingBool('Enable_3D')]
        self.optionDescriptions = [LANGUAGE(33053),LANGUAGE(33054),LANGUAGE(33055)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.storedValues       = [[],[],[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return IncludeOptions()


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
            self.log("runAction, setting incExtras = %s, incStrms = %s, inc3D = %s"%(builder.incExtras,builder.incStrms,builder.inc3D))
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.incExtras = self.storedValues[0]
            builder.incStrms  = self.storedValues[1]
            builder.inc3D     = self.storedValues[2]
            self.log("runAction, restoring incExtras = %s, incStrms = %s, inc3D = %s"%(builder.incExtras,builder.incStrms,builder.inc3D))
        return parameter


class PreRoll(BaseRule):
    """
    PreRoll
    """
    def __init__(self):
        self.myId               = 502
        self.ignore             = False
        self.exclude            = False
        self.name               = "Pre-Roll"
        self.description        = "Pre-Roll Options"
        self.optionLabels       = [LANGUAGE(30017),LANGUAGE(30139),LANGUAGE(30028),LANGUAGE(30029),"Ratings Folder","Bumpers Folder"]
        self.optionValues       = [SETTINGS.getSettingInt('Enable_Preroll'),SETTINGS.getSettingInt('Random_Pre_Chance'),SETTINGS.getSetting('Resource_Ratings'),SETTINGS.getSetting('Resource_Bumpers'),[os.path.join(FILLER_LOC,'Ratings','')],[os.path.join(FILLER_LOC,'Bumpers','')]]
        self.optionDescriptions = [LANGUAGE(30018),LANGUAGE(33134),LANGUAGE(33028),LANGUAGE(33029),"",""]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [{LANGUAGE(30022):-1,LANGUAGE(30021):0},list(range(0,101,1)),"","","",""]
        self.storedValues       = [{},{}]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return PreRoll()


    def getTitle(self):
        return self.name
        
        
    def onAction(self, optionindex):
        if   optionindex in [0,1]: self.onActionSelect(optionindex)
        elif optionindex in [2,3]: self.onActionResources(optionindex, ftype={"2":"ratings","3":"bumpers"}[str(optionindex)])
        elif optionindex in [4,5]: self.onActionMultiBrowse(optionindex, header="%s for %s"%(LANGUAGE(32080), {"4":"Ratings","5":"Bumpers"}[str(optionindex)]), exclude=[12,13,14,15,16,21,22])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.bctTypes.get('ratings',{})
            self.storedValues[1] = builder.bctTypes.get('bumpers',{})
            builder.bctTypes['ratings'].update({"max":self.optionValues[0], "auto":self.optionValues[0] == -1, "enabled":bool(self.optionValues[0]), "chance":self.optionValues[1],"sources":{"ids":self.optionValues[2].split('|'),"paths":self.optionValues[4]}})
            builder.bctTypes['bumpers'].update({"max":self.optionValues[0], "auto":self.optionValues[0] == -1, "enabled":bool(self.optionValues[0]), "chance":self.optionValues[1],"sources":{"ids":self.optionValues[3].split('|'),"paths":self.optionValues[5]}})
            self.log("runAction, setting bctTypes = %s"%(builder.bctTypes))

        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.bctTypes['ratings'] = self.storedValues[0]
            builder.bctTypes['bumpers'] = self.storedValues[1]
            self.log("runAction, restoring bctTypes = %s"%(builder.bctTypes))
        return parameter
        
                            
class PostRoll(BaseRule):
    """
    PostRoll
    """
    def __init__(self):
        self.myId               = 503
        self.ignore             = False
        self.exclude            = False
        self.name               = "Post-Roll"
        self.description        = "Post-Roll Options"
        self.optionLabels       = [LANGUAGE(30019),LANGUAGE(30134),LANGUAGE(30030),"Adverts Folder",LANGUAGE(30136),LANGUAGE(30031),"Trailers Folder",LANGUAGE(30126),LANGUAGE(30125)]
        self.optionValues       = [SETTINGS.getSettingInt('Enable_Postroll'),SETTINGS.getSettingInt('Random_Post_Chance'),SETTINGS.getSetting('Resource_Adverts'),[os.path.join(FILLER_LOC,'Adverts','')],SETTINGS.getSettingBool('Include_Adverts_iSpot'),SETTINGS.getSetting('Resource_Trailers'),[os.path.join(FILLER_LOC,'Trailers','')],SETTINGS.getSettingBool('Include_Trailers_KODI'),SETTINGS.getSettingBool('Include_Trailers_IMDB')]
        self.optionDescriptions = [LANGUAGE(30020),LANGUAGE(33134),LANGUAGE(33030),"",LANGUAGE(33136),LANGUAGE(33031),"",LANGUAGE(33126),LANGUAGE(33125)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [{LANGUAGE(30022):-1,LANGUAGE(30021):0,LANGUAGE(30026):1,LANGUAGE(30024):2,LANGUAGE(30025):3},list(range(0,101,1)),[]]
        self.storedValues       = [{},{}]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return PostRoll()


    def getTitle(self):
        return self.name


    def onAction(self, optionindex):
        if   optionindex in [0,1]:   self.onActionSelect(optionindex)
        elif optionindex in [2,5]:   self.onActionResources(optionindex, ftype={"2":"adverts","5":"trailers"}[str(optionindex)])
        elif optionindex in [3,6]:   self.onActionMultiBrowse(optionindex, header="%s for %s"%(LANGUAGE(32080),{"3":"Adverts","6":"Trailers"}[str(optionindex)]), exclude=[12,13,14,15,16,21,22])
        elif optionindex in [4,7,8]: self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.bctTypes.get('adverts',{})
            self.storedValues[1] = builder.bctTypes.get('trailers',{})
            builder.bctTypes['adverts'].update({"min":self.optionValues[0] , "auto":self.optionValues[0] == -1, "enabled":bool(self.optionValues[0]), "chance":self.optionValues[1],"sources":{"ids":self.optionValues[2].split('|'),"paths":self.optionValues[3], "incIspot":self.optionValues[4]}})
            builder.bctTypes['trailers'].update({"min":self.optionValues[0], "auto":self.optionValues[0] == -1, "enabled":bool(self.optionValues[0]), "chance":self.optionValues[1],"sources":{"ids":self.optionValues[5].split('|'),"paths":self.optionValues[6], "incKODI":self.optionValues[7] ,"incIMDB":self.optionValues[8]}})
            self.log("runAction, setting bctTypes = %s"%(builder.bctTypes))

        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.bctTypes['adverts']  = self.storedValues[0]
            builder.bctTypes['trailers'] = self.storedValues[1]
            self.log("runAction, restoring bctTypes = %s"%(builder.bctTypes))
        return parameter
        

class InterleaveValue(BaseRule):
    """
    InterleaveValue
    """
    def __init__(self):
        self.myId               = 504
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30192)
        self.description        = LANGUAGE(33215)
        self.optionLabels       = [LANGUAGE(30179)]
        self.optionValues       = [SETTINGS.getSettingInt('Interleave_Value')]
        self.optionDescriptions = [LANGUAGE(33215)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [list(range(0,26,1))]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return InterleaveValue()


    def getTitle(self):
        if bool(self.optionValues[0]): return '%s %s'%(LANGUAGE(30192),LANGUAGE(30184))
        else:                          return '%s %s'%(LANGUAGE(30192),LANGUAGE(30021))


    def onAction(self, optionindex):
        self.onActionSelect(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.interleaveValue
            builder.interleaveValue = self.optionValues[0]
            self.log("runAction, setting interleaveValue = %s"%(builder.interleaveValue))
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.interleaveValue = self.storedValues[0]
            self.log("runAction, restoring interleaveValue = %s"%(builder.interleaveValue))
        return parameter


class ProvisionalRule(BaseRule): #PARSING RULES [800-999]
    """
    ProvisionalRule
    """
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
        self.storedValues       = [[]]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self): 
        return ProvisionalRule()
        
        
    def getTitle(self): 
        if self.optionValues[0]: return "%s (%s)"%(self.name, self.optionValues[0])
        else:                    return self.name
            
            
    def _getProvisional(self, citem):
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
        return PROVISIONAL_TYPES.get(citem.get('type',''),[])
            
  
    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE: 
            if self.optionValues[0]:
                try:
                    if builder.pDialog: builder.pDialog = self.dialog.progressBGDialog(builder.pCount, builder.pDialog, message='%s: %s'%(LANGUAGE(32209),self.name),header='%s, %s'%(ADDON_NAME,builder.pMSG))
                    if self.optionValues[0] == "Seasonal": queries = list(Seasonal().buildSeasonal())
                    else:                                  queries = self._getProvisional(citem)
                    self.log("%s: runAction, id: %s, provisional value = %s\nqueries = %s"%(self.__class__.__name__,citem.get('id'),self.optionValues[0],queries))
                    for provisional in queries:
                        if not provisional: continue
                        else:
                            if self.optionValues[0] == "Seasonal": citem['logo'] = provisional.get('holiday',{}).get('logo',citem['logo'])
                            else: provisional["filter"]["and"][0]['value'] = self.optionValues[0]
                            if not builder.incExtras and provisional["key"].startswith(tuple(TV_TYPES)): #filter out extras/specials
                                provisional["filter"].setdefault("and",[]).extend([{"field":"season" ,"operator":"greaterthan","value":"0"},
                                                                                   {"field":"episode","operator":"greaterthan","value":"0"}])
                            fileList, dirList = builder.buildList(citem, provisional.get('path'), media='video', page=(provisional.get('limit') or builder.limit), sort=provisional.get('sort'), limits=builder.limits, dirItem={}, query=provisional)
                            if len(fileList) > 0: self.storedValues[0].append(fileList)
                    return [fileList for fileList in self.storedValues[0] if fileList]
                except Exception as e: self.log("runAction, failed! %s"%(e), xbmc.LOGERROR)
                return []
        return parameter


class HandleMethodOrder(BaseRule):
    """
    HandleMethodOrder
    """
    def __init__(self):
        self.myId               = 950
        self.ignore             = False
        self.exclude            = True
        self.name               = LANGUAGE(32232)
        self.description        = LANGUAGE(33232)
        self.optionLabels       = ['Page Limit','Method','Order','Ignore Articles','Ignore Artist Sort Name']
        self.optionValues       = [REAL_SETTINGS.getSettingInt('Page_Limit'),SETTINGS.getSetting('Sort_Method').lower(),'ascending',True,True]
        self.optionDescriptions = ["","","","",""]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [list(range(25,525,25)), self.getSort(), self.getOrder()]
        self.storedValues       = [[],[],[],[],[]]
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return HandleMethodOrder()


    def getTitle(self):
        return self.name


    def getSort(self):
        from jsonrpc import JSONRPC
        return JSONRPC().getEnums("List.Sort",type="method")


    def getOrder(self):
        from jsonrpc import JSONRPC
        return JSONRPC().getEnums("List.Sort",type="order")


    def onAction(self, optionindex):
        if optionindex in [3,4]: self.onActionToggleBool(optionindex)
        else:                    self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.limit
            self.storedValues[1] = builder.sort
            builder.limit = self.optionValues[0]
            builder.sort.update({"method":self.optionValues[1],"order":self.optionValues[2],"ignorearticle":self.optionValues[3],"useartistsortname":self.optionValues[4]})
            self.log("runAction, setting limit to %s and sort to %s"%(builder.limit,builder.sort))
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.limit = self.storedValues[0]
            builder.sort  = self.storedValues[1]
            self.log("runAction, restoring limit to %s and sort to %s"%(builder.limit,builder.sort))
        return citem


class ForceEpisode(BaseRule):
    """
    ForceEpisode
    """
    def __init__(self):
        self.myId               = 998
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30181)
        self.description        = LANGUAGE(33230)
        self.optionLabels       = [LANGUAGE(30181),LANGUAGE(30183)]
        self.optionValues       = [SETTINGS.getSettingBool('Enable_Even_Force'),SETTINGS.getSettingInt('Interleave_Value')]
        self.optionDescriptions = [LANGUAGE(33230),LANGUAGE(33215)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE,RULES_ACTION_CHANNEL_BUILD_PATH,RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.storedValues       = [{},{},[],[],[],[]]
        self.selectBoxOptions   = ["",list(range(0,26,1))]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return ForceEpisode()


    def getTitle(self):
        if self.optionValues[0]: return '%s %s'%(self.name,LANGUAGE(30184))
        else:                    return '%s %s'%(self.name,LANGUAGE(30021))


    def onAction(self, optionindex):
        if   optionindex == 0: self.onActionToggleBool(optionindex)
        elif optionindex == 1: self.onActionSelect(optionindex)
        return self.optionValues[optionindex]


    def _episodeSort(self, showArray: dict={}):
        try:
            for show, fileItems in list(showArray.items()):
                self.storedValues[4] = []
                for item in fileItems:
                    if (int(item.get("season","0")) + int(item.get("episode","0"))) > 0: #episode
                        self.storedValues[4].append([int(item.get("season","0")), int(item.get("episode","0")), item])
                    else:
                        self.storedValues[3].append(item) #movie
                    
                self.storedValues[4].sort(key=lambda seep: seep[1])
                self.storedValues[4].sort(key=lambda seep: seep[0])
                for seepitem in self.storedValues[4]: self.storedValues[5].append(seepitem[2])
            return self.storedValues[5]
        except Exception as e: self.log("runAction, _episodeSort failed! %s"%(e), xbmc.LOGERROR)
        return []


    def _sortShows(self, fileList: list=[]): #group by type & show; no duplicates. 
        try:
            for fileItem in fileList:
                if fileItem.get('type').startswith(tuple(TV_TYPES)):
                    if fileItem not in self.storedValues[2].setdefault(fileItem['showtitle'],[]):
                        self.storedValues[2].setdefault(fileItem['showtitle'],[]).append(fileItem)
                elif fileItem not in self.storedValues[3]: self.storedValues[3].append(fileItem) #Movies/Other no duplicates allowed
            return self._episodeSort(self.storedValues[2]), sorted(self.storedValues[3], key=lambda k: k.get('year',0))
        except Exception as e: self.log("runAction, _sortShows failed! %s"%(e), xbmc.LOGERROR)
        return []


    def runAction(self, actionid, citem, parameter, builder):
        if self.optionValues[0]: 
            if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
                self.storedValues[0] = builder.sort
                
            elif actionid == RULES_ACTION_CHANNEL_BUILD_PATH:
                if   parameter.startswith(tuple(['videodb://%s'%tv for tv in TV_TYPES])): builder.sort.update({"method":"episode"})
                elif parameter:                                                           builder.sort.update({"method":"year"})
                self.log("runAction, setting sort to %s"%(builder.sort))
                
            elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE:
                builder.sort = self.storedValues[0]
                self.log("runAction, restoring sort and forcing episode/year ordering (%s)"%(len(parameter)))
                fileList = list(sorted(parameter, key=lambda k: k.get('year',0)))
                return interleave(list(self._sortShows(fileList)),self.optionValues[1])
        return parameter
        
        
class ForceRandom(BaseRule):
    """
    ForceRandom
    """
    def __init__(self):
        self.myId               = 999
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30182)
        self.description        = LANGUAGE(33231)
        self.optionLabels       = [LANGUAGE(30182)]
        self.optionValues       = [False]
        self.optionDescriptions = [LANGUAGE(33231)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE,RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.storedValues       = [{}]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return ForceRandom()


    def getTitle(self):
        if self.optionValues[0]: return '%s %s'%(self.name,LANGUAGE(30184))
        else:                    return '%s %s'%(self.name,LANGUAGE(30021))


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem,  fileList, builder):
        if self.optionValues[0]: 
            if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
                self.storedValues[0] = builder.sort
                builder.sort.update({"method":"random"})
                self.log("runAction, setting sort to %s"%(builder.sort))
                
            elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE:
                builder.sort = self.storedValues[0]
                self.log("runAction, restoring sort and forcing random shuffle of %s items"%(len(fileList)))
                return randomShuffle(fileList)
        return fileList
        

class EvenShowsRule(BaseRule): #BUILDING RULES [1000-2999]
    """
    EvenShowsRule
    """
    def __init__(self):
        self.myId               = 1000
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(30121)
        self.description        = LANGUAGE(33121)
        self.optionLabels       = [LANGUAGE(30180),LANGUAGE(30015),LANGUAGE(30181)]
        self.optionValues       = [SETTINGS.getSettingInt('Enable_Even'),SETTINGS.getSettingInt('Page_Limit'),SETTINGS.getSettingBool('Enable_Even_Force')]
        self.optionDescriptions = [LANGUAGE(33121),LANGUAGE(33015),LANGUAGE(33230)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE,RULES_ACTION_CHANNEL_BUILD_PATH,RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE,RULES_ACTION_CHANNEL_BUILD_FILELIST_POST]
        self.selectBoxOptions   = [list(range(0,6)),list(range(25,501,25)),""]
        self.storedValues       = [[],[],[],{},[]]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self): 
        return EvenShowsRule()
      
      
    def getTitle(self):
        if bool(self.optionValues[0]): return '%s %s'%(self.name,LANGUAGE(30184))
        else:                          return '%s %s'%(self.name,LANGUAGE(30021))


    def onAction(self, optionindex):
        if optionindex in [0,1]: self.onActionSelect(optionindex,self.optionLabels[optionindex])
        elif optionindex ==2:    self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def _chunkEpisodes(self, showArray: dict={}):
        for show, episodes in list(showArray.items()):
            yield show,[episodes[i:i+self.optionValues[0]] for i in range(0,len(episodes),self.optionValues[0])]


    def _sortShows(self, fileItems): #group by type & show; no duplicates. 
        try:
            for fileItem in fileItems:
                if fileItem.get('type').startswith(tuple(TV_TYPES)): #TV Shows
                    if fileItem not in self.storedValues[3].setdefault(fileItem['showtitle'],[]): self.storedValues[3].setdefault(fileItem['showtitle'],[]).append(fileItem)
                elif fileItem not in self.storedValues[4]: self.storedValues[4].append(fileItem) #Movies/Other no duplicates allowed
            if self.optionValues[2]: self.storedValues[4] = list(sorted(self.storedValues[4], key=lambda k: k.get('year',0))) #force year ordering
            return dict(self._chunkEpisodes(self.storedValues[3])), self.storedValues[4]
        except Exception as e: self.log("runAction, _sortShows failed! %s"%(e), xbmc.LOGERROR)
        return {}


    def _mergeShows(self, shows, movies):
        nfileList = []
        try:
            while not MONITOR().abortRequested() and shows:
                for show, chunks in list(shows.items()):
                    if   len(movies) > 0:  nfileList.append(movies.pop(0))
                    if   len(chunks) == 0: del shows[show]
                    elif len(chunks) > 0:  nfileList.extend(shows[show].pop(0))
                    
            if len(movies) > 0:
                self.log('runAction, _mergeShows appending remaining movies, movie count = %s'%(len(movies)))
                nfileList.extend(movies) #add any remaining movies to the end of sets.
            self.log('runAction, _mergeShows returning items = %s'%(len(nfileList)))
            return [_f for _f in nfileList if _f]
        except Exception as e: self.log("runAction, _mergeShows failed! %s"%(e), xbmc.LOGERROR)
        return []
        
            
    def runAction(self, actionid, citem, parameter, builder):
        if bool(self.optionValues[0]):
            if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
                self.storedValues[1] = builder.limit
                
            elif actionid == RULES_ACTION_CHANNEL_BUILD_PATH:
                if parameter.startswith(tuple(['videodb://%s'%tv for tv in TV_TYPES])):
                    builder.limit = self.optionValues[1] * self.optionValues[0] #Double parser limit for tv content inorder to aid even distro. 
                elif parameter:
                    builder.limit = self.optionValues[1]
                self.log('runAction, setting limit %s'%(builder.limit))
                
            elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE:
                if len(parameter) > 0:
                    if builder.pDialog: builder.pDialog = self.dialog.progressBGDialog(builder.pCount, builder.pDialog, message='%s: %s'%(LANGUAGE(32209),self.name),header='%s, %s'%(ADDON_NAME,builder.pMSG))
                    if self.optionValues[2]: fileItems = list(sorted(parameter, key=lambda k: k.get('episode',0))) #force episode ordering
                    else:                    fileItems = parameter
                    self.log('runAction, group by episode %s'%(self.optionValues[2]))
                    return self._mergeShows(*(self._sortShows(fileItems)))
                
            elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_POST:
                builder.limit = (self.storedValues[1] or SETTINGS.getSettingInt('Page_Limit')) #_injectedRules don't retain stored values use globals
                self.log('runAction, restoring limit = %s'%(builder.limit))
        return parameter
        
        
class PauseRule(BaseRule): #Finial RULES [3000-~]
    def __init__(self):
        self.myId               = 3000
        self.ignore             = False
        self.exclude            = False
        self.name               = LANGUAGE(32230)
        self.description        = LANGUAGE(33228)
        self.optionLabels       = [LANGUAGE(32231)]
        self.optionValues       = [True]
        self.optionDescriptions = [LANGUAGE(32231)]
        self.actions            = [RULES_ACTION_PLAYBACK_RESUME, RULES_ACTION_PLAYER_START, RULES_ACTION_PLAYER_CHANGE, RULES_ACTION_PLAYER_STOP, RULES_ACTION_CHANNEL_START, RULES_ACTION_CHANNEL_STOP, RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE, RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST, RULES_ACTION_CHANNEL_BUILD_FILELIST_POST, RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN, RULES_ACTION_CHANNEL_BUILD_TIME_PRE, RULES_ACTION_CHANNEL_TEMP_CITEM]
        self.storedValues       = [[],[],[]]
        
        f"""
        {self.__class__.__name__}
        
        {self.myId}. "{self.name}" - {self.description}
              * "{self.optionLabels[0]}" - {self.optionDescriptions[0]}
                    
        """
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self): 
        return PauseRule()
        
        
    def getTitle(self): 
        return self.name
            
            
    def _getResume(self, id):
        resume = (SETTINGS.getCacheSetting('resumeChannel.%s'%(id), json_data=True) or {"idx":0,"position":0.0,"total":0.0,"file":""})
        self.log('_getResume, id = %s, resume = %s'%(id,resume))
        return resume


    def _setResume(self, id, resume: dict={"idx":0,"position":0.0,"total":0.0,"file":""}):
        self.log('_setResume, id = %s, resume = %s'%(id, SETTINGS.setCacheSetting('resumeChannel.%s'%(id),resume, json_data=True)))


    def _getPosition(self, id):
        return self._getResume(id)["idx"]

        
    def _setPosition(self, id, idx: int=0):
        resume = self._getResume(id)
        resume["idx"] = idx
        return self._setResume(id, resume)
        

    def _getFileList(self, id):
        idx = self._getPosition(id)
        self.log('_getFileList, id = %s, idx = %s'%(id,idx))
        try:
            fileList = SETTINGS.getCacheSetting('pausedFileList.%s'%(id), json_data=True)[idx:]
            self._setPosition(id) #reset idx, keep resume
        except:
            fileList = []
            self._setResume(id) #reset all
        finally: 
            self.log('_getFileList, fileList = %s, resetting position to 0, resume = %s'%(len(fileList),self._getResume(id)))
            return self._setFileList(id, fileList)
            
            
    def _setFileList(self, id, fileList: list=[]):
        self.log('_setFileList, id = %s, fileList = %s'%(id,len(fileList)))
        return SETTINGS.setCacheSetting('pausedFileList.%s'%(id), fileList, json_data=True)
        

    def _getTotDuration(self, fileList=[]):
        from jsonrpc import JSONRPC
        return JSONRPC().getTotRuntime(fileList)
            
            
    def _getduration(self, fileList=[]):
        from jsonrpc import JSONRPC
        return JSONRPC()._getRuntime(fileList)
        
        
    def _buildSchedule(self, citem, fileList, builder):     
        self.log('_buildSchedule, id = %s, fileList = %s'%(citem.get('id'),len(fileList)))
        return builder.buildCells(citem, duration=self._getTotDuration(fileList), entries=1, 
                                  info={"title":'%s (%s)'%(citem.get('name'),LANGUAGE(32145)), 
                                        "episodetitle":'Updated: %s'%(datetime.datetime.fromtimestamp(time.time()).strftime(DTJSONFORMAT)),
                                        "plot":'Size: %s videos \nTotal Runtime: %s hrs.'%(len(fileList),round(self._getTotDuration(fileList)//60//60)),
                                        "art":{"thumb":citem.get('logo',COLOR_LOGO),"fanart":FANART,"logo":citem.get('logo',LOGO),"icon":citem.get('logo',LOGO)}})

    def runAction(self, actionid, citem, parameter, inherited):
        self.log('runAction, actionid = %s, id = %s'%(actionid,citem.get('id')))
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0]    = inherited.padScheduling
            inherited.padScheduling = False #disable guide padding with duplicates to fill quota.
            self.log("runAction, setting padScheduling = %s"%(inherited.padScheduling))
            
        elif actionid == RULES_ACTION_CHANNEL_TEMP_CITEM: 
            parameter['resume'] = True
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
            self.storedValues[1] = self._getFileList(citem.get('id'))
            if self._getTotDuration(self.storedValues[1]) >= (MIN_GUIDEDAYS * 86400): return [self.storedValues[1]]
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST:
            if [self.storedValues[1]] != parameter: self.storedValues[2] = True #changed, pending fileList expansion.
            elif len(self.storedValues[1]) > 0: return True

        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_POST:
            if self.storedValues[2] and len(parameter) > 0:
                self.log("runAction, updating fileList (%s) extending by (%s)"%(len(self.storedValues[1]),len(parameter)))
                self.storedValues[1].extend(parameter)
                self.storedValues[1] = self._setFileList(citem.get('id'), self.storedValues[1])
                
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN:
            if parameter: return self.storedValues[1]
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_TIME_PRE:
            if len(parameter) > 0: 
                if inherited.xmltv.clrProgrammes(citem):
                    return self._buildSchedule(citem, parameter, inherited)

        elif actionid == RULES_ACTION_CHANNEL_STOP:
            inherited.padScheduling = self.storedValues[0]
            self.log("runAction, restoring padScheduling = %s"%(inherited.padScheduling))
            
        elif actionid == RULES_ACTION_PLAYBACK_RESUME:
            if len(self.storedValues[1]) == 0: self.storedValues[1] = self._getFileList(citem.get('id'))
            if len(self.storedValues[1]) > 0:
                item   = self.storedValues[1].pop(0)
                resume = self._getResume(citem.get('id'))
                if item.get('file') == resume.get('file',str(random.random())):
                    self.log("runAction, restoring last resume point = %s"%(resume))
                    item['resume'] = resume
                self.storedValues[1].insert(0,item)
                if self._getTotDuration(self.storedValues[1]) < (MIN_GUIDEDAYS * 86400) : PROPERTIES.setUpdateChannels(citem.get('id'))
                return self.storedValues[1]
            return []
                                            
        elif actionid == RULES_ACTION_PLAYER_START:
            if len(self.storedValues[1]) == 0: self.storedValues[1] = self._getFileList(citem.get('id'))
            
        elif actionid == RULES_ACTION_PLAYER_CHANGE:
            self._setResume(citem.get('id'), parameter.get('resume'))
            self.log("runAction, updating resume = %s"%(self._getResume(citem.get('id'))))
                
        elif actionid == RULES_ACTION_PLAYER_STOP:
            self._setResume(inherited.sysInfo.get('citem',{}).get('id'), inherited.sysInfo.get('resume'))
            self.log("runAction, saving resume = %s"%(self._getResume(inherited.sysInfo.get('citem',{}).get('id'))))
        return parameter
       
