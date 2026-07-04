#   Copyright (C) 2026 Lunatixz
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
from variables  import *
from jsonrpc    import JSONRPC
from channels   import Channels
#todo pinlock
        

# Enable_Fillers
# Enable_Preroll
# Random_Pre_Chance
# Enable_Postroll
# Random_Post_Chance
# Build_Post_Folders
# Resource_Trailers
# Include_Trailers_KODI


# Resource_Overlay
# Resource_Ratings
# Resource_Bumpers
# Resource_Adverts
  
class RulesList(object):
    def __init__(self, channels=None):
        self.channels = channels
        self.ruleList = [BaseRule(),
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
                         ForceRebuild(),
                         DurationOptions(),
                         IncludeOptions(),
                         PreRoll(),
                         PostRoll(),
                         InterleaveValue(),
                         SeasonalRule(),
                         HandleMethodOrder(),
                         HandleLimits(),
                         ForceEpisodeOrder(),
                         ForceRandom(),
                         EvenShowsRule(),
                         PauseRule(),
                         PadScheduling()]
                          
        if channels: self.ruleItems = self.loadRules(channels)
        else:        self.ruleItems = {}
                         

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def getTemplate(self) -> dict: 
        return Channels().channelRULE.copy()
        
                  
    def dumpRules(self, rules={}):
        #convert rule instances to json
        nrules = {}
        for myId, rule in list(rules.items()):
            ritem = {}
            if isinstance(myId, str): myId = int(myId) #temp correct format change
            ritem[myId] = {"values":dict()}
            for idx, value in enumerate(rule.optionValues):
                if isinstance(idx, str): idx = int(idx) #temp correct format change
                ritem[myId]["values"][idx] = value
            nrules.update(ritem)
        return nrules
            

    def loadRules(self, channels=None, append=False):
        if channels is None: channels = Channels().getChannels()
        #load channel rules and their instances. append = full rule list.
        def __load(ruleList, citem={}):
            tmpruleList = {}
            if not append and len(citem.get('rules',{})) == 0: return None
            for rule in ruleList:
                ruleInstance = rule.copy()
                tmpritem = {"values":{}}
                for idx, value in enumerate(ruleInstance.optionValues): #load default rule as template
                    if isinstance(idx, str): idx = int(idx) #temp correct format change
                    tmpritem["values"][idx] = value

                if citem.get('rules',{}).get(rule.myId):
                    for key, value in list(citem['rules'][rule.myId].get('values',{}).items()): #load channel rule
                        try:
                            if isinstance(key, str): key = int(key) #temp correct format change
                            tmpritem["values"].update({key:value}) #update default rule value with channel value.
                            ruleInstance.optionValues[key] = tmpritem["values"][key] #load values to rule instance
                        except Exception as e: log('[%s] loadRules, failed! %s\nrule = %s'%(citem['id'],e,citem['rules'][rule.myId]), xbmc.LOGERROR)
                    tmpruleList[rule.myId] = ruleInstance
                    
                elif append: #append missing default rule values
                    tmpruleList[rule.myId] = ruleInstance

            self.log('[%s] loadRules: append = %s, rule myIds = %s'%(citem.get('id'), append,list(tmpruleList.keys())))
            rules[citem['id']] = tmpruleList
            
        rules    = {}
        ruleList = self.ruleList.copy()
        ruleList.pop(0) #remove boilerplate baseRule()
        [__load(ruleList,channel) for channel in channels]
        return rules


    def allRules(self): #load all rules.
        self.log('allRules')
        tmpruleList = self.ruleList.copy()
        tmpruleList.pop(0) #remove boilerplate baseRule()
        return [rule.copy() for rule in tmpruleList]
               
        
    def runActions(self, action, citem={}, parameter=None, inherited=None):
        if inherited is None: inherited = self
        rules = self.ruleItems.get(citem.get('id',''))
        if not rules: rules = (self.loadRules([citem]).get(citem.get('id','')) or {})
        for myId, rule in list(sorted(rules.items())):
            if action in rule.actions:
                self.log("[%s] runActions, %s performing channel rule: %s"%(citem.get('id'),inherited.__class__.__name__,rule.name))
                try: parameter = rule.runAction(action, citem, parameter, inherited)
                except Exception as e: log('[%s] runActions, failed! %s\nrule = %s'%(citem.get('id'),e,rule), xbmc.LOGERROR)
        return parameter


class BaseRule(object):
    
    def __init__(self):
        self.myId               = 0
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
        except Exception:
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
        self.log("validateDaysofWeekBox")
        daysofweek = "UMTWHFS"
        newstr = ''
        for day in daysofweek:
            loc = self.optionValues[optionindex].find(day)
            if loc != -1: newstr += day
        self.optionValues[optionindex] = newstr


    def validateRange(self, optionindex, minimum, maximum, default):
        if int(self.optionValues[optionindex]) < minimum:
            self.log("Invalid minimum range")
            self.Globals.DIALOG.notificationDialog(LANGUAGE(32077)%(self.optionLabels[optionindex]))
            self.optionValues[optionindex] = default
            return
        elif int(self.optionValues[optionindex]) > maximum:
            self.log("Invalid maximum range")
            self.Globals.DIALOG.notificationDialog(LANGUAGE(32077)%(self.optionLabels[optionindex]))
            self.optionValues[optionindex] = default
            return


    def validateDigitBox(self, optionindex, minimum, maximum, default):
        if int(self.optionValues[optionindex]) == 0: return
        try:
            val = int(self.optionValues[optionindex])
            if val >= minimum and val <= maximum:
                self.optionValues[optionindex] = val
            return
        except Exception: pass
        self.Globals.DIALOG.notificationDialog(LANGUAGE(32077)%(self.optionLabels[optionindex]))
        self.optionValues[optionindex] = default

    
    def onActionToggleBool(self, optionindex):
        self.log("onActionToggleBool")
        self.optionValues[optionindex] = not self.optionValues[optionindex]


    def onActionFunction(self, optionindex):
        self.log("onActionFunction")
        value = self.selectBoxOption[optionindex]()
        if value: self.optionValues[optionindex] = value


    def onActionPickColor(self, optionindex, colorlist=[], colorfile=""):
        self.log("onActionPickColor")
        value = self.Globals.DIALOG.colorDialog(colorlist, self.optionValues[optionindex], colorfile, self.name)
        if value: self.optionValues[optionindex] = value
        

    def onActionTextBox(self, optionindex):
        self.log("onActionTextBox")
        value = self.Globals.DIALOG.inputDialog(self.name, default=self.optionValues[optionindex], key=xbmcgui.INPUT_ALPHANUM)
        if value: self.optionValues[optionindex] = value


    def onActionDigitBox(self, optionindex):
        self.log("onActionDigitBox")
        info =  self.Globals.DIALOG.inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)
        if info != None: self.optionValues[optionindex] = info


    def onActionTimeBox(self, optionindex):
        self.log("onActionTimeBox")
        info = self.Globals.DIALOG.inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)
        if info != None:
            if info[0] == ' ': info = info[1:]
            if len(info) == 4: info = "0" + info
            self.optionValues[optionindex] = info


    def onActionSelect(self, optionindex, header=None, preselect=None, useDetails=False, autoclose=SELECT_DELAY, multi=False):
        self.log("onActionSelect")
        if header is None:
            if multi: header = '%s - %s'%(ADDON_NAME,LANGUAGE(32017)%(''))
            else:     header = '%s - %s'%(ADDON_NAME,LANGUAGE(32223)%(''))
        
        if isinstance(self.selectBoxOptions[optionindex],dict): values, options = list(self.selectBoxOptions[optionindex].values()), list(self.selectBoxOptions[optionindex].keys())
        else:                                                   values, options = self.selectBoxOptions[optionindex], self.optionValues[optionindex]
        items  = [str(v).title() for v in self.selectBoxOptions[optionindex]]
        select = self.Globals.DIALOG.selectDialog(items, header, Globals._findItemsInLST(values, options), useDetails, autoclose, multi)
        if not select is None: 
            if   isinstance(self.selectBoxOptions[optionindex],dict): self.optionValues[optionindex] = self.selectBoxOptions[optionindex].get(self.selectBoxOptions[optionindex][select])
            elif isinstance(select,list):                             self.optionValues[optionindex] = [self.selectBoxOptions[optionindex][idx] for idx in select]
            elif select < len(self.selectBoxOptions[optionindex]):    self.optionValues[optionindex] = self.selectBoxOptions[optionindex][select]
            elif select:                                              self.optionValues[optionindex] = select
                
          
    def onActionBrowse(self, optionindex, type=0, heading=ADDON_NAME, shares='', mask='', useThumbs=True, treatAsFolder=False, multi=False, monitor=False, options=[], exclude=[]):
        self.log("onActionBrowse")
        info = self.Globals.DIALOG.browseSources(type, heading, self.optionValues[optionindex], shares, mask, useThumbs, treatAsFolder, multi, monitor, options, exclude)
        if info is not None: self.optionValues[optionindex] = info 
    
    
    def onActionMultiBrowse(self, optionindex, header=ADDON_NAME, exclude=[], monitor=True):
        self.log("onActionMultiBrowse")
        info = self.Globals.DIALOG.multiBrowse(self.optionValues[optionindex], header, exclude, monitor)
        if info is not None: self.optionValues[optionindex] = info 


    def onActionResources(self, optionindex, ftype=''):
        log("onActionResources")
        info = self.Globals.DIALOG.browseResources(self.optionValues[optionindex].split('|'), ftype=ftype)
        if not info is None: self.optionValues[optionindex] = '|'.join(info)

#Rules apply sequentially by myId
class ShowChannelBug(BaseRule): #OVERLAY RULES [1-49]
    def __init__(self):
        self.myId               = 1
        self.name               = LANGUAGE(30143)
        self.description        = LANGUAGE(30144)
        self.optionLabels       = [LANGUAGE(30043),LANGUAGE(30112),LANGUAGE(30044),LANGUAGE(30208)]
        self.optionValues       = [Globals.SETTINGS.getSettingBool('Enable_ChannelBug'),Globals.SETTINGS.getSetting("Channel_Bug_Position_XY"),Globals.SETTINGS.getSetting('ChannelBug_Color'),Globals.SETTINGS.getSettingBool('Force_Diffuse'),Globals.SETTINGS.getSettingInt('ChannelBug_Transparency')]
        self.optionDescriptions = [LANGUAGE(33043),LANGUAGE(33112),LANGUAGE(33044),LANGUAGE(33209)]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = [[True,False],[LANGUAGE(30022),LANGUAGE(32136)],"","",list(range(15,51,5))]
        self.storedValues       = [[],[],[],[],[],[]]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return ShowChannelBug()


    def getTitle(self):
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def getPosition(self, optionindex):
        orgvalue = self.optionValues[optionindex]
        self.onActionSelect(optionindex, LANGUAGE(32223)%(''))
        if self.optionValues[optionindex] == self.selectBoxOptions[optionindex][1]:
            from overlaytool import OverlayTool
            try: overlaytool = OverlayTool(OVERLAYTOOL_XML, ADDON_PATH, "default", ADV_RULES=True, Focus_IDX=1, Channel_Bug_Position_XY=self.optionValues[optionindex], ChannelBug_Color=self.optionValues[3])
            except Exception as e: self.log("getPosition, failed! %s"%(e), xbmc.LOGERROR)
            finally: del overlaytool
            value = Globals.PROPERTIES.getProperty("Channel_Bug_Position_XY")
            Globals.PROPERTIES.clrProperty("Channel_Bug_Position_XY")
            if value: self.optionValues[optionindex] = value
            else:     self.optionValues[optionindex] = orgvalue
        elif self.optionValues[optionindex] != self.selectBoxOptions[optionindex][0]:
            self.optionValues[optionindex] = orgvalue


    def onAction(self, optionindex):
        if   optionindex == 0: self.onActionToggleBool(optionindex)
        elif optionindex == 1: self.getPosition(optionindex)
        elif optionindex == 2: self.onActionPickColor(optionindex)
        elif optionindex == 3: self.onActionToggleBool(optionindex)
        elif optionindex == 4: self.onActionSelect(optionindex, LANGUAGE(33209))
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, overlay):
        if actionid == RULES_ACTION_OVERLAY_OPEN:
            self.storedValues[0] = overlay.enableChannelBug
            self.storedValues[1] = (overlay.channelBugX, overlay.channelBugY)
            self.storedValues[2] = overlay.channelBugColor
            self.storedValues[3] = overlay.channelBugDiffuse
            self.storedValues[4] = overlay.channelBugFade
            
            overlay.enableChannelBug   = self.optionValues[0]
            overlay.channelBugX, overlay.channelBugY = literal_eval(self.optionValues[1])
            overlay.channelBugColor    = '0x%s'%(self.optionValues[2])
            overlay.channelBugDiffuse  = self.optionValues[3]
            overlay.channelBugFade     = self.optionValues[4]
            self.log("runAction, setting enableChannelBug = %s, channelBugColor = %s, channelBugDiffuse = %s"%(overlay.enableChannelBug,(overlay.channelBugX, overlay.channelBugY),overlay.channelBugColor,overlay.channelBugDiffuse,overlay.channelBugFade))
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay.enableChannelBug   = self.storedValues[0]
            overlay.channelBugX, overlay.channelBugY = self.storedValues[1]
            overlay.channelBugColor   = self.storedValues[2]
            overlay.channelBugDiffuse = self.storedValues[3]
            overlay.channelBugFade    = self.storedValues[4]
            self.log("runAction, restoring enableChannelBug = %s, channelBugColor = %s, channelBugDiffuse = %s"%(overlay.enableChannelBug,(overlay.channelBugX, overlay.channelBugY),overlay.channelBugColor,overlay.channelBugDiffuse,overlay.channelBugFade))
        return parameter


class ShowOnNext(BaseRule):
    def __init__(self):
        self.myId               = 2
        self.name               = LANGUAGE(30045)
        self.description        = LANGUAGE(33045)
        self.optionLabels       = [LANGUAGE(30045),LANGUAGE(32229),LANGUAGE(30044),LANGUAGE(30196)]
        self.optionValues       = [bool(Globals.SETTINGS.getSettingInt('OnNext_Mode')),Globals.SETTINGS.getSetting("OnNext_Position_XY"),Globals.SETTINGS.getSettingInt('OnNext_Mode')]
        self.optionDescriptions = [LANGUAGE(30045),LANGUAGE(33229),LANGUAGE(30196)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions   = ["",[LANGUAGE(30022),LANGUAGE(32136)],"",{LANGUAGE(30021):0,LANGUAGE(30193):1,LANGUAGE(30194):2,LANGUAGE(30197):3,LANGUAGE(30195):4}]
        self.storedValues       = [[],[],[],[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return ShowOnNext()


    def getTitle(self):
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def getPosition(self, optionindex):
        orgvalue = self.optionValues[optionindex]
        self.onActionSelect(optionindex, LANGUAGE(32223)%(''))
        if self.optionValues[optionindex] == self.selectBoxOptions[optionindex][1]:
            from overlaytool import OverlayTool
            try: overlaytool = OverlayTool(OVERLAYTOOL_XML, ADDON_PATH, "default", ADV_RULES=True, Focus_IDX=0, OnNext_Position_XY=self.optionValues[optionindex], OnNext_Color=self.optionValues[2])
            except Exception as e: self.log("getPosition, failed! %s"%(e), xbmc.LOGERROR)
            finally: del overlaytool
            value = Globals.PROPERTIES.getProperty("OnNext_Position_XY")
            Globals.PROPERTIES.clrProperty("OnNext_Position_XY")
            if value: self.optionValues[optionindex] = value
            else:     self.optionValues[optionindex] = orgvalue
        elif self.optionValues[optionindex] != self.selectBoxOptions[optionindex][0]:
            self.optionValues[optionindex] = orgvalue


    def onAction(self, optionindex):
        if   optionindex == 0: self.onActionToggleBool(optionindex)
        elif optionindex == 1: self.getPosition(optionindex)
        elif optionindex == 2: self.onActionSelect(optionindex, LANGUAGE(30196))
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0]  = bool(player.OnNextMode)
            self.storedValues[1]  = player.onNextPosition
            self.storedValues[2]  = player.onNextMode
            player.onNextPosition = self.optionValues[1]
            player.OnNextMode     = self.optionValues[2]
            self.log("runAction, restoring onNextPosition = %s, onNextMode = %s"%(player.onNextPosition, player.onNextMode))
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.onNextPosition = self.storedValues[1]
            player.onNextMode     = self.storedValues[2]
            self.log("runAction, restoring onNextPosition = %s, onNextMode = %s"%(player.onNextPosition, player.onNextMode))
        return parameter


class SetScreenVingette(BaseRule):
    def __init__(self):
        self.myId               = 3
        self.name               = LANGUAGE(30177)
        self.description        = LANGUAGE(33177)
        self.optionLabels       = [LANGUAGE(30174),LANGUAGE(30175),LANGUAGE(30176),LANGUAGE(30178),LANGUAGE(30185),LANGUAGE(30186)]
        self.optionValues       = [False,' ',1.00,0.00,1.00,False]
        self.optionDescriptions = [LANGUAGE(33174),LANGUAGE(33175),LANGUAGE(33176),LANGUAGE(33179),LANGUAGE(33185),LANGUAGE(34186)]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = ['','',list(Globals._frange(5,21,1)),list(range(-2,3,1)),list(Globals._frange(5,21,1)),'']#[LANGUAGE(30022),LANGUAGE(32136)]]
        self.storedValues       = [[],[],[]]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return SetScreenVingette()


    def getTitle(self):
        return '%s (%s)'%(self.name,self.optionValues)
            
            # todo set viewmode as {} response from json.
    def getPosition(self, optionindex):#todo vin utility to adjust zoom,vshift,pratio and nls
        self.Globals.DIALOG.notificationDialog(LANGUAGE(32020))


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
        if   optionindex == 1:       self.onActionBrowse(optionindex, type=1, heading=self.optionLabels[1], mask=xbmc.getSupportedMedia('picture'), exclude=[12,13,14,15,16,17])
        elif optionindex in [0,5]:   self.onActionToggleBool(optionindex)
        elif optionindex in [2,3,4]: self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, overlay):
        if actionid == RULES_ACTION_OVERLAY_OPEN:
            self.storedValues[0] = overlay.enableVignette
            self.storedValues[1] = overlay.vinImage
            self.storedValues[2] = overlay.vinView
            
            overlay.enableVignette = self.optionValues[0]
            overlay.vinImage      = self.getImage(self.optionValues[1])
            overlay.vinView   = {"nonlinearstretch":self.optionValues[5] ,"pixelratio":self.optionValues[4],"verticalshift":self.optionValues[3],"viewmode":"custom","zoom": self.optionValues[2]}
            self.log('runAction, setting vignette image = %s\nmode = %s'%(overlay.vinImage,overlay.vinView))
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay.enableVignette = self.storedValues[0]
            overlay.vinImage      = self.storedValues[1]
            overlay.vinView   = self.storedValues[2]
            self.log('runAction, restoring vignette image = %s\nmode = %s'%(overlay.vinImage,overlay.vinView))
        return parameter
        

class MST3k(BaseRule):
    def __init__(self):
        self.myId               = 4
        self.name               = "Mystery Science Theater 3K Silhouette"
        self.description        = "Animated Silhouette of MST3K"
        self.optionLabels       = ['Enable MST3K Silhouette']
        self.optionValues       = [False]
        self.optionDescriptions = ["Enable Silhouette"]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_OPEN+.1,RULES_ACTION_OVERLAY_CLOSE]
        self.storedValues       = [[],[],[]]
        self.threadTimer        = Timer(SERVICE_INTERVAL, self.runAction)
        self.optionImages       = [os.path.join(MEDIA_LOC,'overlays','MST3K_1.gif'), os.path.join(MEDIA_LOC,'overlays','MST3K_2.gif')]

   
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return MST3k()


    def getTitle(self):
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def setImage(self, actionid, citem, overlay, image):
        if not self.threadTimer.is_alive():
            self.threadTimer = Timer(SERVICE_INTERVAL, overlay.runActions,[actionid, citem, None, overlay])
            self.threadTimer.name = 'MST3k.setImage'
            self.threadTimer.start()
        self.log('setImage, image = %s'%(image))
        return image


    def onAction(self, optionindex):
        if optionindex == 0: self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, overlay):
        if actionid == RULES_ACTION_OVERLAY_OPEN:
            self.storedValues[0] = overlay.vinImage
            self.storedValues[1] = overlay._vinOffsetXY
            self.storedValues[2] = overlay._vinZoom
            
            overlay.vinImage    = self.setImage(actionid+.1, citem, overlay, self.optionImages[0])
            overlay._vinOffsetXY = (0,0)
            overlay._vinZoom     = 1.0
            self.log("runAction, setting overlay enabled = %s, image %s @ (%s) X %s"%(overlay.enableVignette, overlay.vinImage, overlay._vinOffsetXY, overlay._vinZoom))
            
        elif actionid == RULES_ACTION_OVERLAY_OPEN+.1:
            overlay.vinImage = self.setImage(actionid, citem, overlay, self.optionImages[1])
            overlay._setImage(overlay.vignette,overlay.vinImage)
            self.log("runAction, setting overlay enabled = %s, image %s @ (%s) X %s"%(overlay.enableVignette, overlay.vinImage, overlay._vinOffsetXY, overlay._vinZoom))
            
        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay.vinImage    = self.storedValues[0]
            overlay._vinOffsetXY = self.storedValues[1]
            overlay._vinZoom     = self.storedValues[2]
            self.log("runAction, restoring overlay enabled = %s, image %s @ (%s) X %s"%(overlay.enableVignette, overlay.vinImage, overlay._vinOffsetXY, overlay._vinZoom))
            
            if self.threadTimer.is_alive():
                if hasattr(self.threadTimer, 'cancel'): self.threadTimer.cancel()
                try: self.threadTimer.join()
                except Exception: pass
        return parameter
        

class DisableOverlay(BaseRule): #PLAYER RULES [50-99]
    def __init__(self):
        self.myId               = 50
        self.name               = LANGUAGE(30042)
        self.description        = LANGUAGE(33042)
        self.optionLabels       = [LANGUAGE(30042)]
        self.optionValues       = [Globals.SETTINGS.getSettingBool('Overlay_Enable')]
        self.optionDescriptions = [LANGUAGE(33042)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return DisableOverlay()


    def getTitle(self):
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


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
        self.name               = "Force Subtitles"
        self.description        = "Show Subtitles"
        self.optionLabels       = ['Force Subtitles?']
        self.optionValues       = [Globals.BUILTIN.isSubtitle()]
        self.optionDescriptions = [""]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return ForceSubtitles()


    def getTitle(self):
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


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
        self.name               = "Trakt scrobbling"
        self.description        = "Disable Trakt scrobbling."
        self.optionLabels       = [LANGUAGE(30131)]
        self.optionValues       = [Globals.SETTINGS.getSettingBool('Disable_Trakt')]
        self.optionDescriptions = [LANGUAGE(33131)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return DisableTrakt()


    def getTitle(self):
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


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
    def __init__(self):
        self.myId               = 53
        self.name               = "Rollback Playcount"
        self.description        = "Passive Playback w/o playcount & progress tracking."
        self.optionLabels       = [LANGUAGE(30132)]
        self.optionValues       = [Globals.SETTINGS.getSettingBool('Rollback_Watched')]
        self.optionDescriptions = [LANGUAGE(33132)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return RollbackPlaycount()


    def getTitle(self):
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


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
    def __init__(self):
        self.myId               = 54
        self.name               = "Restart Button"
        self.description        = LANGUAGE(33153)
        self.optionLabels       = [LANGUAGE(30153)]
        self.optionValues       = [Globals.SETTINGS.getSettingInt('Replay_Percentage')]
        self.optionDescriptions = [LANGUAGE(33153)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions   = [list(range(25,100,5))]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return DisableRestart()


    def getTitle(self):
        return '%s (%s)'%(self.name,self.optionValues[0])


    def onAction(self, optionindex):
        self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, player):
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.replayPercentage
            player.replayPercentage = self.optionValues[0]
            self.log("runAction, setting replayPercentage = %s"%(player.replayPercentage))
            
        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.replayPercentage = self.storedValues[0]
            self.log("runAction, restoring replayPercentage = %s"%(player.replayPercentage))
        return parameter

        
class DisableOnChange(BaseRule):
    def __init__(self):
        self.myId               = 55
        self.name               = LANGUAGE(30170)
        self.description        = LANGUAGE(33171)
        self.optionLabels       = [LANGUAGE(30170)]
        self.optionValues       = [Globals.SETTINGS.getSettingBool('Enable_OnInfo')]
        self.optionDescriptions = [LANGUAGE(33171)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return DisableOverlay()


    def getTitle(self):
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


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


class ForceRebuild(BaseRule):
    def __init__(self):
        self.myId               = 497
        self.name               = "Force Rebuild"
        self.description        = "Force Rebuild All Channel Content."
        self.optionLabels       = ["Force Rebuild Channel"]
        self.optionValues       = [False]
        self.optionDescriptions = ["Always Force Rebuild Channel"]
        self.actions            = [RULES_ACTION_CHANNEL_CITEM]
        self.storedValues       = []


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return ForceRebuild()


    def getTitle(self):
        return '%s (%s)'%(self.name,self.optionValues)


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_CITEM:
            if self.optionValues[0]: parameter['changed'] = True
            self.log("runAction, setting changed = %s"%(self.optionValues[0]))
        return parameter
            
            
class DurationOptions(BaseRule): #PRE-BUILD RULES [500-599]
    def __init__(self):
        self.myId               = 500
        self.name               = "Duration Options"
        self.description        = "Duration Options"
        self.optionLabels       = [LANGUAGE(30049),LANGUAGE(30052),LANGUAGE(32233)]
        self.optionValues       = [Globals.SETTINGS.getSettingInt('Duration_Type'),Globals.SETTINGS.getSettingBool('Store_Duration'),Globals.SETTINGS.getSettingInt('Seek_Tolerance')]
        self.optionDescriptions = [LANGUAGE(33015),LANGUAGE(33049),LANGUAGE(33052),LANGUAGE(32233)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [{LANGUAGE(30050):0,LANGUAGE(30051):1},[],list(range(0,900,5))]
        self.storedValues       = [[],[],[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return DurationOptions()


    def getTitle(self):
        return '%s (%s)'%(self.name,self.optionValues)


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
    def __init__(self):
        self.myId               = 501
        self.name               = "Include Options"
        self.description        = "Include Options"
        self.optionLabels       = [LANGUAGE(30053),LANGUAGE(30054),LANGUAGE(30055),LANGUAGE(30225)]
        self.optionValues       = [Globals.SETTINGS.getSettingBool('Enable_Extras'),Globals.SETTINGS.getSettingBool('Enable_Strms'),Globals.SETTINGS.getSettingBool('Enable_3D'),Globals.SETTINGS.getSettingBool('Enable_Details')]
        self.optionDescriptions = [LANGUAGE(33053),LANGUAGE(33054),LANGUAGE(33055),LANGUAGE(33225)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.storedValues       = [[],[],[],[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return IncludeOptions()


    def getTitle(self):
        return '%s (%s)'%(self.name,self.optionValues)


    def onAction(self, optionindex):
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0]   = builder.incExtras
            self.storedValues[1]   = builder.incStrms
            self.storedValues[2]   = builder.inc3D
            self.storedValues[3]   = builder.incStrmDetails
            builder.incExtras      = self.optionValues[0]
            builder.incStrms       = self.optionValues[1]
            builder.inc3D          = self.optionValues[2]
            builder.incStrmDetails = self.optionValues[3]
            self.log("runAction, setting incExtras = %s, incStrms = %s, inc3D = %s"%(builder.incExtras,builder.incStrms,builder.inc3D))
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.incExtras      = self.storedValues[0]
            builder.incStrms       = self.storedValues[1]
            builder.inc3D          = self.storedValues[2]
            builder.incStrmDetails = self.storedValues[3]
            self.log("runAction, restoring incExtras = %s, incStrms = %s, inc3D = %s"%(builder.incExtras,builder.incStrms,builder.inc3D))
        return parameter


class PreRoll(BaseRule):
    def __init__(self):
        self.myId               = 502
        self.name               = "Pre-Roll"
        self.description        = "Pre-Roll Options"
        self.optionLabels       = [LANGUAGE(30017),LANGUAGE(30139),LANGUAGE(30029),LANGUAGE(30028),"Bumpers Folder","Ratings Folder"]
        self.optionValues       = [Globals.SETTINGS.getSettingInt('Enable_Preroll'),Globals.SETTINGS.getSettingInt('Random_Pre_Chance'),Globals.SETTINGS.getSetting('Resource_Bumpers'),Globals.SETTINGS.getSetting('Resource_Ratings'),[os.path.join(FILLER_LOC,'Bumpers','')],[os.path.join(FILLER_LOC,'Ratings','')]]
        self.optionDescriptions = [LANGUAGE(30018),LANGUAGE(33134),LANGUAGE(33029),LANGUAGE(33028),"",""]
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
        elif optionindex in [2,3]: self.onActionResources(optionindex, ftype={2:"bumpers",3:"ratings"}[optionindex])
        elif optionindex in [4,5]: self.onActionMultiBrowse(optionindex, header="%s for %s"%(LANGUAGE(32080), {4:"Bumpers",5:"Ratings"}[optionindex]), exclude=[12,13,14,15,16,21,22])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.bctTypes.get('bumpers',{})
            self.storedValues[1] = builder.bctTypes.get('ratings',{})
            builder.bctTypes['bumpers'].update({"max":self.optionValues[0], "auto":self.optionValues[0] == -1, "enabled":bool(self.optionValues[0]), "chance":self.optionValues[1],"sources":{"ids":self.optionValues[2].split('|'),"paths":self.optionValues[4]}})
            builder.bctTypes['ratings'].update({"max":self.optionValues[0], "auto":self.optionValues[0] == -1, "enabled":bool(self.optionValues[0]), "chance":self.optionValues[1],"sources":{"ids":self.optionValues[3].split('|'),"paths":self.optionValues[5]}})
            self.log("runAction, setting bctTypes = %s"%(builder.bctTypes))

        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.bctTypes['bumpers'] = self.storedValues[0]
            builder.bctTypes['ratings'] = self.storedValues[1]
            self.log("runAction, restoring bctTypes = %s"%(builder.bctTypes))
        return parameter
        
                            
class PostRoll(BaseRule):
    def __init__(self):
        self.myId               = 503
        self.name               = "Post-Roll"
        self.description        = "Post-Roll Options"
        self.optionLabels       = [LANGUAGE(30019),LANGUAGE(30134),LANGUAGE(30030),"Adverts Folder",LANGUAGE(30031),"Trailers Folder",LANGUAGE(30126),LANGUAGE(30053)]
        self.optionValues       = [Globals.SETTINGS.getSettingInt('Enable_Postroll'),Globals.SETTINGS.getSettingInt('Random_Post_Chance'),Globals.SETTINGS.getSetting('Resource_Adverts'),[os.path.join(FILLER_LOC,'Adverts','')],Globals.SETTINGS.getSetting('Resource_Trailers'),[os.path.join(FILLER_LOC,'Trailers','')],Globals.SETTINGS.getSettingBool('Include_Trailers_KODI'),Globals.SETTINGS.getSettingBool('Include_Extras_KODI')]
        self.optionDescriptions = [LANGUAGE(30020),LANGUAGE(33134),LANGUAGE(33030),"",LANGUAGE(33031),"",LANGUAGE(33126),LANGUAGE(33233)]
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
        if   optionindex in [0,1]: self.onActionSelect(optionindex)
        elif optionindex in [2,4]: self.onActionResources(optionindex, ftype={2:"adverts",4:"trailers"}[optionindex])
        elif optionindex in [3,5]: self.onActionMultiBrowse(optionindex, header="%s for %s"%(LANGUAGE(32080),{3:"Adverts",5:"Trailers"}[optionindex]), exclude=[12,13,14,15,16,21,22])
        elif optionindex in [6,7]: self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.bctTypes.get('adverts',{})
            self.storedValues[1] = builder.bctTypes.get('trailers',{})
            builder.bctTypes['adverts'].update({"min":self.optionValues[0] , "max":builder.limit, "auto":self.optionValues[0] == -1, "enabled":bool(self.optionValues[0]), "chance":self.optionValues[1],"sources":{"ids":self.optionValues[2].split('|'),"paths":self.optionValues[3]}})
            builder.bctTypes['trailers'].update({"min":self.optionValues[0], "max":builder.limit, "auto":self.optionValues[0] == -1, "enabled":bool(self.optionValues[0]), "chance":self.optionValues[1],"sources":{"ids":self.optionValues[4].split('|'),"paths":self.optionValues[5]},"incKODI":self.optionValues[6]})
            builder.bctTypes['extras'].update({"min":self.optionValues[0]  , "max":builder.limit, "auto":self.optionValues[0] == -1, "enabled":bool(self.optionValues[0]), "chance":self.optionValues[1],"sources":{"ids":[]                             ,"paths":[]}                  ,"incKODI":self.optionValues[7]})
            self.log("runAction, setting bctTypes = %s"%(builder.bctTypes))
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.bctTypes['adverts'].update(self.storedValues[0])
            builder.bctTypes['trailers'].update(self.storedValues[1])
            self.log("runAction, restoring bctTypes = %s"%(builder.bctTypes))
        return parameter
        

class InterleaveValue(BaseRule):
    def __init__(self):
        self.myId               = 504
        self.name               = LANGUAGE(30192)
        self.description        = LANGUAGE(33215)
        self.optionLabels       = [LANGUAGE(30179),LANGUAGE(30211)]
        self.optionValues       = [Globals.SETTINGS.getSettingInt('Interleave_Set'), Globals.SETTINGS.getSettingBool('Interleave_Repeat')]
        self.optionDescriptions = [LANGUAGE(33215),LANGUAGE(33211)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [list(range(0,26,1))]
        self.storedValues       = [[],[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return InterleaveValue()


    def getTitle(self):
        return '%s (%s)'%(self.name,self.optionValues[0])


    def onAction(self, optionindex):
        if optionindex == 0: self.onActionSelect(optionindex)
        else:                self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.interleaveSet
            self.storedValues[1] = builder.interleaveRepeat
            builder.interleaveSet    = self.optionValues[0]
            builder.interleaveRepeat = self.optionValues[1]
            self.log("runAction, setting interleaveSet = %s, interleaveRepeat = %s"%(builder.interleaveSet, builder.interleaveRepeat))
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.interleaveSet    = self.storedValues[0]
            builder.interleaveRepeat = self.storedValues[1]
            self.log("runAction, restoring interleaveSet = %s, interleaveRepeat = %s"%(builder.interleaveSet, builder.interleaveRepeat))
        
        return parameter


class SeasonalRule(BaseRule): #PARSING RULES [800-999]
    """
    SeasonalRule
    """
    def __init__(self):
        self.myId               = 800
        self.name               = "Seasonal"
        self.description        = "Automatically Populate Channels with Seasonal Media."
        self.optionLabels       = ["Holiday"]
        self.optionValues       = [[{"path":"","method":"","enum":"","limits":{},"sort":{},"filter":{},"holiday":{}}]]
        self.optionDescriptions = ["INTERNAL USE ONLY!"]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE]
        self.storedValues       = [[]]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self): 
        return SeasonalRule()
        
        
    def getTitle(self): 
        return '%s (%s)'%(self.name,self.optionValues[0][0].get('holiday',{}).get('name','None'))
            

    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE: 
            if self.optionValues[0][0].get('holiday',{}):
                try:
                    if builder.pDialog: builder.pDialog = Globals.DIALOG._updateProgressThrottled(builder.pDialog, builder.pCount, message=f"{builder.pName}: {LANGUAGE(32209)} {self.name}",header=builder.pHeader)
                    self.log(f"[{citem['id']}] runAction, {self.optionValues[0][0]['holiday']['name']}")
                    for query in self.optionValues[0]:
                        citem['logo'] = (query.get('holiday',{}).get('logo') or LOGO_SEASONAL)
                        if query["key"].startswith(tuple(TV_TYPES)): #filter out extras/specials
                            if not builder.incExtras:
                                query["filter"].setdefault("and",[]).extend([{"field":"season" ,"operator":"greaterthan","value":"0"},
                                                                             {"field":"episode","operator":"greaterthan","value":"0"}])
                            else:
                                query['filter']['and'] = [r for r in params['filter'].get("and", []) if not (('season' in r or 'episode' in r) and r.get("value") == "0")]
                                query['filter']['and'] = Globals.Globals._setDictLST(params['filter']['and'])
                        # subfileList, subdirList, limits, errors = builder.buildList(citem, query.get('path',''), 'video', (query.get('limit') or builder.limit), query.get('sort',{}), builder.limits, {'file':query.get('path')}, query) #parse all directories under root. Flattened hierarchies recommended to stream line channel building.
                        self.storedValues[0].append(builder.buildFileList(citem, query.get('path',''), 'video', (query.get('limit') or builder.limit), query.get('sort',{}), builder.limits, query))
                    return [fileList for fileList in self.storedValues[0] if fileList] #fileArray
                except Exception as e: self.log(f"[{citem['id']}] runAction, failed! {e}", xbmc.LOGERROR)
                return []
        return parameter


class HandleMethodOrder(BaseRule):
    def __init__(self):
        self.myId               = 950
        self.name               = LANGUAGE(32232)
        self.description        = LANGUAGE(33232)
        self.optionLabels       = ['Method','Order','Ignore Articles','Ignore Artist Sort Name']
        self.optionValues       = ['random','ascending',True,True]
        self.optionDescriptions = ["","","",""]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [self.getSort(), self.getOrder()]
        self.storedValues       = [[],[],[],[],[]]
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return HandleMethodOrder()


    def getTitle(self):
        return '%s (%s)'%(self.name,self.optionValues)


    def getSort(self):
        return JSONRPC().getEnums("List.Sort",type="method")


    def getOrder(self):
        return JSONRPC().getEnums("List.Sort",type="order")


    def onAction(self, optionindex):
        if optionindex in [2,3]: self.onActionToggleBool(optionindex)
        else:                    self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.sort
            builder.sort.update({"method":self.optionValues[0],"order":self.optionValues[1],"ignorearticle":self.optionValues[2],"useartistsortname":self.optionValues[3]})
            self.log("runAction, setting sort to %s"%(builder.sort))
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.sort = self.storedValues[0]
            self.log("runAction, restoring sort to %s"%(builder.sort))
            
        return citem


class HandleLimits(BaseRule):
    def __init__(self):
        self.myId               = 951
        self.name               = LANGUAGE(32263)
        self.description        = LANGUAGE(33015)
        self.optionLabels       = ['Limit','Limits End','Limits Start']
        self.optionValues       = [Globals.SETTINGS.getSettingInt('Page_Limit'),-1,0]
        self.optionDescriptions = [f"Force Limit [{Globals.SETTINGS.getSettingInt('Page_Limit')}:Default]","Force End [-1:Auto, 0:Unlimited]","Force Start [-1:Unlimited, 0:Auto]"]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [[0,10,25,50,100,250,500,1000]]
        self.storedValues       = [[],{}]
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return HandleLimits()


    def getTitle(self):
        return '%s (%s)'%(self.name,self.optionValues)


    def onAction(self, optionindex):
        if optionindex == 0: self.onActionSelect(optionindex)
        else:
            self.onActionDigitBox(optionindex)
            self.validateDigitBox(optionindex,-1,self.selectBoxOptions[0][-1] if self.storedValues[1].get('total',0) == 0 else self.storedValues[1].get('total'),25)
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.limit
            self.storedValues[1] = builder.limits
            builder.limit = self.optionValues[0]
            builder.limits.update({"end":self.optionValues[1],"start":self.optionValues[2]})
            self.log("runAction, setting limit to %s, limits to %s"%(builder.limit,builder.limits))
            
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.limit = self.storedValues[0]
            builder.limits.update(self.storedValues[1])
            self.log("runAction, restoring limit to %s, limits to %s"%(builder.limit,builder.limits))
            
        return citem


class ForceEpisodeOrder(BaseRule):
    def __init__(self):
        self.myId               = 998
        self.name               = LANGUAGE(30181)
        self.description        = LANGUAGE(33230)
        self.optionLabels       = [LANGUAGE(30181)]
        self.optionValues       = [True]
        self.optionDescriptions = [LANGUAGE(33230)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE,RULES_ACTION_CHANNEL_BUILD_PATH,RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.storedValues       = [[],[],{},[],[],[]]
        self.selectBoxOptions   = []


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return ForceEpisodeOrder()


    def getTitle(self):
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex):
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
                if fileItem.get('type').startswith(tuple(TV_TYPES)) and fileItem.get('showtitle'):
                    if fileItem not in self.storedValues[2].setdefault(fileItem['showtitle'],[]): 
                        self.storedValues[2].setdefault(fileItem['showtitle'],[]).append(fileItem)
                elif fileItem not in self.storedValues[3]: 
                    self.storedValues[3].append(fileItem) #Movies/Other no duplicates allowed
            return self._episodeSort(self.storedValues[2]), sorted(self.storedValues[3], key=lambda k: k.get('year',0))
        except Exception as e: self.log("runAction, _sortShows failed! %s"%(e), xbmc.LOGERROR)
        return []


    def runAction(self, actionid, citem, parameter, builder):
        if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
            self.storedValues[0] = builder.sort
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_PATH:
            if   parameter.startswith(tuple(['videodb://%s'%tv for tv in TV_TYPES])): builder.sort.update({"method":"episode"})
            elif parameter:                                                           builder.sort.update({"method":"year"})
            self.log("runAction, setting sort to %s"%(builder.sort))
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE:
            builder.sort = self.storedValues[0]
            self.log("runAction, restoring sort and forcing episode/year ordering (%s)"%(len(parameter)))
            return Globals._interleave(list(self._sortShows(parameter)), builder.interleaveSet, builder.interleaveRepeat)
        return parameter
        
        
class ForceRandom(BaseRule):
    def __init__(self):
        self.myId               = 999
        self.name               = LANGUAGE(30182)
        self.description        = LANGUAGE(33231)
        self.optionLabels       = [LANGUAGE(30182)]
        self.optionValues       = [True]
        self.optionDescriptions = [LANGUAGE(33231)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE,RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.storedValues       = [[]]


    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self):
        return ForceRandom()


    def getTitle(self):
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex):
        return self.optionValues[optionindex]


    def runAction(self, actionid, citem,  fileList, builder):
        if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
            self.storedValues[0] = builder.sort
            builder.sort.update({"method":"random"})
            self.log("runAction, setting sort to %s"%(builder.sort))
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE:
            builder.sort = self.storedValues[0]
            self.log("runAction, restoring sort and forcing random shuffle of %s items"%(len(fileList)))
            return Globals._randomShuffle(fileList)
        return fileList
        

class EvenShowsRule(BaseRule): #BUILD RULES [1000-2999]
    def __init__(self):
        self.myId               = 1000
        self.name               = LANGUAGE(30121)
        self.description        = LANGUAGE(33121)
        self.optionLabels       = [LANGUAGE(30180),LANGUAGE(30181),LANGUAGE(30182)]
        self.optionValues       = [Globals.SETTINGS.getSettingInt('Enable_Even'),Globals.SETTINGS.getSettingBool('Enable_Even_Force_Episode'),Globals.SETTINGS.getSettingBool('Enable_Even_Force_Random')]
        self.optionDescriptions = [LANGUAGE(33121),LANGUAGE(33230),LANGUAGE(30182)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [list(range(0,26,1))]
        self.storedValues       = [[],[],[],{},[]]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self): 
        return EvenShowsRule()
      
      
    def getTitle(self):
        return self.name


    def toggle(self, optionindex):
        if optionindex == 1: 
            if self.optionValues[2]: self.optionValues[2] = not self.optionValues[optionindex]
        elif optionindex == 2: 
            if self.optionValues[1]: self.optionValues[1] = not self.optionValues[optionindex]


    def onAction(self, optionindex):
        if optionindex == 0: self.onActionSelect(optionindex,self.optionLabels[optionindex])
        else:
            self.onActionToggleBool(optionindex)
            self.toggle(optionindex)
        return self.optionValues[optionindex]


    def _chunkEpisodes(self, showArray: dict={}):
        for show, episodes in showArray.items():
            yield show, [episodes[i : i + self.optionValues[0]] for i in range(0, len(episodes), self.optionValues[0])]


    def _sortShows(self, fileItems, episode_order=False, random_order=False):
        try:
            for item in fileItems:
                type  = item.get('type', '')
                title = item.get('showtitle')
                if title and type.startswith(tuple(TV_TYPES)):
                    if episode_order and item not in self.storedValues[3].setdefault(title,[]): 
                        self.storedValues[3].setdefault(title, []).append(item) #no duplicates
                    elif not episode_order:
                        self.storedValues[3].setdefault(title, []).append(item) #duplicates allowed
                else:
                    item_id = item.get('id') or item.get('file')
                    if episode_order and item_id in self.storedValues[4]: continue
                    self.storedValues[4].append(item)
            if random_order:
                self.storedValues[3] = Globals._randomShuffle(self.storedValues[3])
                self.storedValues[4] = Globals._randomShuffle(self.storedValues[4])
            return dict(self._chunkEpisodes(self.storedValues[3])), self.storedValues[4]
        except Exception as e: self.log("runAction, _sortShows failed! %s"%(e), xbmc.LOGERROR)
        return {}, []


    def _mergeShows(self, shows={}, movies=[], inherited=None):
        try:
            movie_queue = deque(movies or [])
            movie_cnt   = (len(movie_queue) // len(shows)) if len(shows) > 0 else 0
            show_keys   = list(shows.keys())
            
            all_chunks  = []
            for show, chunks in shows.items():
                for chunk in chunks:
                    all_chunks.append(chunk)
                    
            total_slots = len(all_chunks)
            if total_slots == 0: return list(movie_queue)
            movies_per_slot = len(movie_queue) / total_slots
            accumulator = 0.0

            nfileList   = []
            while not inherited.monitor.abortRequested() and shows:
                for show in show_keys[:]:  # Iterate over a copy of keys
                    if show not in shows: continue
                    chunks = shows[show]
                    if chunks:
                        accumulator += movies_per_slot
                        try: nfileList.extend(chunks.pop(0) if isinstance(chunks, list) else next(chunks))# If it's a list, pop(0) is still slow; if it's a generator, use next()
                        except (IndexError, StopIteration):
                            del shows[show]
                            show_keys.remove(show)
                            
                        while not inherited.monitor.abortRequested() and accumulator >= 1.0 and movie_queue:
                            nfileList.append(movie_queue.popleft())
                            accumulator -= 1.0
                    else:
                        del shows[show]
                        show_keys.remove(show)
            nfileList.extend(movie_queue)
            return nfileList
        except Exception as e: self.log("runAction, _mergeShows failed! %s"%(e), xbmc.LOGERROR)
        return []


    def runAction(self, actionid, citem, parameter, builder):
        if bool(self.optionValues[0]):
            if actionid == RULES_ACTION_CHANNEL_START:
                self.storedValues[0] = builder.enableEven
                self.storedValues[1] = builder.evenEpisode
                self.storedValues[2] = builder.evenShuffle
                builder.enableEven   = self.optionValues[0]
                builder.evenEpisode  = self.optionValues[1]
                builder.evenShuffle  = self.optionValues[2]
                self.log("runAction, setting enableEven = %s, evenEpisode = %s, evenShuffle = %s"%(builder.enableEven,builder.evenEpisode,builder.evenShuffle))
                
            elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE:
                if len(parameter) > 0:
                    builder.pDialog = Globals.DIALOG._updateProgressThrottled(builder.pDialog, builder.pCount, message='%s: %s'%(LANGUAGE(32209),self.name), header='%s, %s'%(ADDON_NAME,builder.pMSG))
                    episode_order = False if self.optionValues[2] else self.optionValues[1]
                    random_order  = False if self.optionValues[1] else self.optionValues[2]
                    if episode_order: 
                                       fileItems = list(sorted(parameter, key=lambda k: k.get('year',0)))    #force year ordering
                                       fileItems = list(sorted(fileItems, key=lambda k: k.get('episode',0))) #force episode ordering
                                       fileItems = list(sorted(fileItems, key=lambda k: k.get('season',0)))  #force season ordering
                    elif random_order: fileItems = Globals._randomShuffle(parameter)
                    else:              fileItems = parameter
                    sortShows, sortMovies = self._sortShows(fileItems, episode_order, random_order)
                    self.log('runAction, episode_order %s, random_order %s, tvshows = %s, movies = %s'%(episode_order, random_order, len(list(sortShows.keys())), len(sortMovies)))
                    return self._mergeShows(sortShows,sortMovies,builder)
                    
            elif actionid == RULES_ACTION_CHANNEL_STOP:
                builder.enableEven  = self.storedValues[0]
                builder.evenEpisode = self.storedValues[1]
                builder.evenShuffle = self.storedValues[2]
                self.log("runAction, restoring enableEven = %s, evenEpisode = %s, evenShuffle = %s"%(builder.enableEven,builder.evenEpisode,builder.evenShuffle))
            
        return parameter
        
        
class PadScheduling(BaseRule):
    def __init__(self):
        self.myId               = 2999
        self.name               = "Pad Scheduling"
        self.description        = f"Pad EPG with duplicates to met minimum EPG requirement [{MIN_EPG_DURATION//60//60} Hrs.]"
        self.optionLabels       = ["Pad Scheduling"]
        self.optionValues       = [True]
        self.optionDescriptions = [""]
        self.actions            = [RULES_ACTION_CHANNEL_START, RULES_ACTION_CHANNEL_BUILD_TIME_POST,RULES_ACTION_CHANNEL_STOP]
        self.storedValues       = [[],[]]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self): 
        return PadScheduling()
        
        
    def getTitle(self): 
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])
            
            
    def onAction(self, optionindex):
        return self.optionValues[optionindex]
        

    def runAction(self, actionid, citem, parameter, inherited):
        self.log('[%s] runAction, actionid = %s,'%(citem.get('id'),actionid))
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0]    = inherited.padScheduling
            inherited.padScheduling = self.optionValues[0]
            self.log("runAction, setting padScheduling to %s"%(inherited.padScheduling))
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_TIME_POST:
            # pad scheduling with duplicates to met minimum guide requirements (MIN_EPG_DURATION).
            if self.padScheduling and len(parameter) > 0:
                iters  = cycle(parameter)
                totDur = 0
                start  = parameter[-1]['stop']
                idx    = len(parameter)
                now    = Globals._getUTCstamp()
                while not inherited.monitor.abortRequested() and start <= (now + MIN_EPG_DURATION):
                    if start >= (now + MIN_EPG_DURATION): break
                    else: 
                        idx += 1
                        item = next(iters).copy()
                        item["idx"]   = idx
                        item['start'] = start
                        item['stop']  = start + item['duration']
                        start = item['stop']
                        totDur += item['duration']
                        parameter.append(item)
                        inherited.pDialog = Globals.DIALOG._updateProgressThrottled(inherited.pDialog, inherited.pCount, message=f"{inherited.pName}: {LANGUAGE(33085)} {totDur}/{MIN_EPG_DURATION}",header=inherited.pHeader)
                        self.log("[%s] addScheduling, ADD fileList = %s, totDur = %s/%s, stop = %s"%(citem['id'],len(parameter),totDur,MIN_EPG_DURATION,parameter[-1].get('stop')))
        
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            inherited.padScheduling = self.storedValues[0]
            self.log("runAction, restoring padScheduling to %s"%(inherited.padScheduling))
            
        return parameter
        
        
class PauseRule(BaseRule): #POST-BUILD RULES [3000-~]
    def __init__(self):
        self.myId               = 3000
        self.name               = LANGUAGE(32230)
        self.description        = LANGUAGE(33228)
        self.optionLabels       = [LANGUAGE(32231),"FileList"]
        self.optionValues       = [True,""]
        self.optionDescriptions = [LANGUAGE(32231),"Self Generated, Please leave blank!"]
        self.actions            = [RULES_ACTION_PLAYBACK_RESUME, RULES_ACTION_PLAYER_START, RULES_ACTION_PLAYER_CHANGE, RULES_ACTION_PLAYER_STOP, RULES_ACTION_CHANNEL_START, RULES_ACTION_CHANNEL_STOP, RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE, RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST, RULES_ACTION_CHANNEL_BUILD_FILELIST_POST, RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN, RULES_ACTION_CHANNEL_BUILD_TIME_PRE, RULES_ACTION_CHANNEL_CITEM, RULES_ACTION_CHANNEL_TEMP_CITEM]
        self.storedValues       = [[],[],False]
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        log('%s: %s'%(self.__class__.__name__,msg),level)
                  

    def copy(self): 
        return PauseRule()
        
        
    def getTitle(self): 
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])
            
            
    def onAction(self, optionindex):
        return self.optionValues[optionindex]
        
        
    def _getURL(self, id):
        return 'http://%s/filelist/%s'%(Globals.PROPERTIES.getRemoteHost(),self._getKey(id))
        
        
    def _addIDX(self, key):
        keys = set(Globals.SETTINGS.getCacheSetting(RESUME_INDEX, FileAccess._getMD5(RESUME_INDEX), default={}))
        keys.add(key)
        return Globals.SETTINGS.setCacheSetting(RESUME_INDEX, keys, FileAccess._getMD5(RESUME_INDEX), datetime.timedelta(days=84))
        
        
    def _delIDX(self, key):
        keys = set(Globals.SETTINGS.getCacheSetting(RESUME_INDEX, FileAccess._getMD5(RESUME_INDEX), default={}))
        if key in list(keys): keys.pop(key)
        return Globals.SETTINGS.setCacheSetting(RESUME_INDEX, keys, FileAccess._getMD5(RESUME_INDEX), datetime.timedelta(days=84))
        
        
    def _chkIDX(self):
        keys = set(Globals.SETTINGS.getCacheSetting(RESUME_INDEX, FileAccess._getMD5(RESUME_INDEX), default={}))
        for key in list(keys):
            if not Globals.SETTINGS.getCacheSetting(key, FileAccess._getMD5(key), default={}): keys.pop(key)
        return Globals.SETTINGS.setCacheSetting(RESUME_INDEX, keys, FileAccess._getMD5(RESUME_INDEX), datetime.timedelta(days=84))
        
        
    def _getKey(self, id):
        return '%s.json'%(FileAccess._getMD5('%s.%s'%(Globals.PROPERTIES.getFriendlyName(),id)))
        
        
    def _getTotDuration(self, id, filelist=[]):
        return JSONRPC().getTotDuration(filelist)
            

    def _buildSchedule(self, citem, filelist, builder):     
        self.log('[%s] _buildSchedule, filelist = %s'%(citem.get('id'),len(filelist)))
        updated = self._getResume(citem.get('id')).get('updated',{})
        try:    viewed = '%s: %s (%s)'%(LANGUAGE(32250),Globals._epochTime(updated.get('time')).strftime(BACKUP_TIME_FORMAT),updated.get('instance'))
        except Exception: viewed = LANGUAGE(32251)
        return builder.buildCells(citem, duration=self._getTotDuration(citem.get('id'), filelist), entries=1, 
                                  info={"title":'%s (%s)'%(citem.get('name'),LANGUAGE(32145)), 
                                        "episodetitle":viewed,
                                        "plot":'%s: %s\nSize: %s\nRuntime: ~%s hrs.'%(LANGUAGE(32249),Globals._epochTime(time.time(),tz=False).strftime(BACKUP_TIME_FORMAT),len(filelist),round(self._getTotDuration(citem.get('id'), filelist)//60//60)),
                                        "art":{"thumb":LOGO,"poster":LOGO_POSTER,"fanart":LOGO_LANDSCAPE,"landscape":LOGO_LANDSCAPE,"logo":citem.get('logo',LOGO),"icon":citem.get('logo',LOGO)}})
            
    def _setResume(self, id, filelist=[], resume={"idx":0,"position":0.0,"total":0.0,"file":"","updated":{"instance":"","time":-1}}):
        key = self._getKey(id)
        self._addIDX(key)
        self.log("[%s] runAction, _setResume: filelist = %s, resume = %s, key = %s, url = %s"%(id,len(filelist),resume,key,self.optionValues[1]))
        friendly = Globals.PROPERTIES.getFriendlyName()
        if resume.get('updated',{}).get('instance') == friendly: return Globals.SETTINGS.setCacheSetting(key, {'resume':resume,'filelist':filelist}, FileAccess._getMD5(key), datetime.timedelta(days=84))
        elif self.optionValues[1]:                               return builder.jsonRPC.requestURL(self.optionValues[1],payload={'uuid':Globals.SETTINGS.getMYUUID(),'name':friendly,'payload':{'resume':resume,'filelist':filelist}},
                                                                                                   cache={"cache":Globals.SETTINGS.cache, "checksum":ADDON_VERSION, "life": datetime.timedelta(minutes=15)})

    def _getResume(self, id):
        key = self._getKey(id)
        self.log("[%s] runAction, _getResume: key = %s, url = %s"%(id,key,self.optionValues[1]))
        if self.optionValues[1]: return builder.jsonRPC.requestURL(self.optionValues[1])
        else:                    return Globals.SETTINGS.getCacheSetting(key, FileAccess._getMD5(key), default={})


    def _getResume(self, id):
        return (self._getResume(id).get('resume') or {"idx":0,"position":0.0,"total":0.0,"file":"","updated":{"instance":"","time":-1}})
        
        
    def _getFilelist(self, id):
        return (self._getResume(id).get('filelist') or [])
        

    def _getPlaylist(self, id):
        resume   = self._getResume(id)
        filelist = self._getFilelist(id)
        if len(filelist) > 0:
            for idx, item in enumerate(filelist):
                if item.get('file') == resume.get('file',-1):
                    resume.update({'idx':0})
                    item['resume'] = resume
                    filelist = filelist[idx:]
                    if self._setResume(id, filelist, resume): break
        self.log('[%s] runAction, _getPlaylist: filelist = %s, resume = %s'%(id,len(filelist),resume))
        return filelist
        
        
    def runAction(self, actionid, citem, parameter, inherited):
        self.log('[%s] runAction, actionid = %s,'%(citem.get('id'),actionid))
        if actionid == RULES_ACTION_CHANNEL_START:
            self._chkIDX()
            self.storedValues[0]    = inherited.padScheduling
            self.storedValues[1]    = self._getFilelist(citem.get('id'))
            inherited.padScheduling = False #disable guide padding with duplicates to fill quota.
            self.log("[%s] runAction, setting padScheduling = %s"%(citem.get('id'),inherited.padScheduling))
            
        elif actionid == RULES_ACTION_CHANNEL_CITEM:
            try:
                parameter["rules"][3000]["values"].update({1:self._getURL(parameter.get('id'))})
                self.log("runAction, updated rule values = %s"%( parameter["rules"][3000]["values"]), xbmc.LOGERROR)
            except Exception as e:
                self.log("runAction, updated rule values failed! %s"%(e), xbmc.LOGERROR)

        # elif actionid == RULES_ACTION_CHANNEL_TEMP_CITEM: 
            # parameter['resume'] = True
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE: #load cached filelist if not outdated, else new buildFileList
            if self._getTotDuration(citem.get('id'), self.storedValues[1]) >= (MIN_GUIDEDAYS * 86400): 
                self.log("[%s] runAction, returning valid cached filelist = %s"%(citem.get('id'),len(self.storedValues[1])))
                return [self.storedValues[1]]
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST: #check if cached filelist is the same as existing filelist.
            if [self.storedValues[1]] != parameter: self.storedValues[2] = True #finish building new filelist extend filelist.
            elif len(self.storedValues[1]) > 0: return True #use cached filelist

        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_POST:#update cached filelist
            if self.storedValues[2] and len(parameter) > 0:
                self.log("[%s] runAction, updating fileList (%s) extending by (%s)"%(citem.get('id'),len(self.storedValues[1]),len(parameter)))
                self.storedValues[1].extend(parameter)
                self._setResume(citem.get('id'), self.storedValues[1], self._getResume(citem.get('id')))
                
        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN:
            if parameter: 
                self.log("[%s] runAction, returning fileList (%s)"%(citem.get('id'),len(self.storedValues[1])))
                return self.storedValues[1]
            
        elif actionid == RULES_ACTION_CHANNEL_BUILD_TIME_PRE:
            if len(parameter) > 0: 
                if inherited.xmltv.clrProgrammes(citem): return self._buildSchedule(citem, parameter, inherited)

        elif actionid == RULES_ACTION_CHANNEL_STOP:
            inherited.padScheduling = self.storedValues[0]
            self.storedValues[1] = []
            self.log("[%s] runAction, restoring padScheduling = %s"%(citem.get('id'),inherited.padScheduling))
            
        elif actionid == RULES_ACTION_PLAYBACK_RESUME:
            return self._getPlaylist(citem.get('id'))
                                                        
        elif actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[1] = self._getFilelist(citem.get('id'))
            
        elif actionid in [RULES_ACTION_PLAYER_CHANGE, RULES_ACTION_PLAYER_STOP]:
            if parameter.get('resume').get('updated'):
                self.log("[%s] runAction, updating resume = %s"%(citem.get('id'),parameter.get('resume')))
                self._setResume(citem.get('id'),self.storedValues[1],parameter.get('resume'))
                
        return parameter
       