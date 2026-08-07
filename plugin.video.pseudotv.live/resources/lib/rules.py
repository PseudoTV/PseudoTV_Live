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
from typing import Any, Optional
from variables  import *
from jsonrpc    import JSONRPC
from channels   import Channels
import ratings

_DAY_RE   = re.compile(r'\_Day(.*?)', re.IGNORECASE)
_NIGHT_RE = re.compile(r'\_Night(.*?)', re.IGNORECASE)


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


    def __init__(self, channels: Optional[list] = None):
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
                         PinLockRule(),
                         PauseRule(),
                         ForceRebuild(),
                         DurationOptions(),
                         IncludeOptions(),
                         PreRoll(),
                         PostRoll(),
                         InterleaveValue(),
                         HandleMethodOrder(),
                         HandleLimits(),
                         Dayparting(),
                         SeasonalRule(),
                         PathKeywordFilter(),
                         AudioLangPreference(),
                         RatingFilter(),
                         DurationRangeFilter(),
                         ForceRandom(),
                         ForceEpisodeOrder(),
                         EvenShowsRule(),
                         UnwatchedFirst(),
                         SeriesMarathon(),
                         RecentFirst(),
                         GenreWeighting(),
                         PadScheduling(),
                         ProgrammeSpacing(),
                         PrimeTimeBlock(),
                         ChannelFilter(),
                         GroupHide(),
                         LogoOverride(),
                         RenumberRule(),
                         GuideLabel(),
                         ExternalFeed()]

        if channels: self.ruleItems = self.loadRules(channels)
        else:        self.ruleItems = {}


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s'%(self.__class__.__name__,msg),level)


    def getTemplate(self) -> dict:
        return Channels(Globals.getChannelKey()).channelRULE.copy()


    def dumpRules(self, rules: dict = {}) -> dict:
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


    def loadRules(self, channels: Optional[list] = None, append: bool = False) -> dict:
        if channels is None: channels = Channels(Globals.getChannelKey()).getChannels()
        #load channel rules and their instances. append = full rule list.
        def __load(ruleList, citem={}):
            tmpruleList = {}
            if not append and len(citem.get('rules',{})) == 0:
                # Rule-less channel — still register an empty entry so runActions
                # finds it in ruleItems and skips the expensive per-dispatch reload.
                rules[citem.get('id')] = {}
                return None
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


    def allRules(self) -> list:
        self.log('allRules')
        tmpruleList = self.ruleList.copy()
        tmpruleList.pop(0) #remove boilerplate baseRule()
        return [rule.copy() for rule in tmpruleList]


    def runActions(self, action: str, citem: dict = {}, parameter: Any = None, inherited: Any = None) -> Any:
        """Dispatch an action to all rules registered for it, in myId order.

        Rules are loaded lazily if not pre-cached. Each rule can transform
        the parameter before passing it to the next rule in the chain.

        Args:
            action: Action constant (e.g., RULES_ACTION_CHANNEL_START).
            citem: Channel item dict (must have 'id' key).
            parameter: Data to pass through the rule chain (file list, schedule, etc.).
            inherited: Builder or service instance with context.

        Returns:
            The parameter after all rules have processed it.
        """
        if inherited is None: inherited = self
        cid = citem.get('id','')
        rules = self.ruleItems.get(cid)
        # Channels are registered by loadRules (rule-less ones as empty dicts), so
        # only genuinely unknown channels take the expensive per-channel reload —
        # and that result is memoized so a channel never pays it on every dispatch.
        if cid not in self.ruleItems:
            rules = (self.loadRules([citem]).get(cid) or {})
            self.ruleItems[cid] = rules
        # Pre-sort by myId once per loadRules call (cached in ruleItems)
        sorted_rules = rules.get('_sorted')
        if sorted_rules is None:
            sorted_rules = list(sorted(rules.items()))
            rules['_sorted'] = sorted_rules
        for myId, rule in sorted_rules:
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


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        return ''


    def getId(self) -> int:
        return self.myId


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        return parameter


    def copy(self) -> 'BaseRule':
        return BaseRule()


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG('%s: %s'%(self.__class__.__name__,msg),level)


    def validate(self):
        pass


    def reset(self):
        self.__init__()


    def validateTextBox(self, optionindex: int, length: int):
        if len(self.optionValues[optionindex]) > length:
            self.optionValues[optionindex] = self.optionValues[optionindex][:length]


    def validateTimeBox(self, optionindex: int):
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


    def validateDaysofWeekBox(self, optionindex: int):
        self.log("validateDaysofWeekBox")
        daysofweek = "UMTWHFS"
        newstr = ''
        for day in daysofweek:
            loc = self.optionValues[optionindex].find(day)
            if loc != -1: newstr += day
        self.optionValues[optionindex] = newstr


    def validateRange(self, optionindex: int, minimum: int, maximum: int, default: int):
        if int(self.optionValues[optionindex]) < minimum:
            self.log("Invalid minimum range")
            Globals.dialog.notificationDialog(LANGUAGE(32077).format(name=self.optionLabels[optionindex]))
            self.optionValues[optionindex] = default
            return
        elif int(self.optionValues[optionindex]) > maximum:
            self.log("Invalid maximum range")
            Globals.dialog.notificationDialog(LANGUAGE(32077).format(name=self.optionLabels[optionindex]))
            self.optionValues[optionindex] = default
            return


    def validateDigitBox(self, optionindex: int, minimum: int, maximum: int, default: int):
        try:
            val = int(str(self.optionValues[optionindex]).strip())
        except Exception as e:
            self.log('validateDigitBox failed: %s' % e, xbmc.LOGDEBUG)
            Globals.dialog.notificationDialog(LANGUAGE(32077).format(name=self.optionLabels[optionindex]))
            self.optionValues[optionindex] = default
            return
        if val == 0: #preserve 0 as disabled/no-limit convention
            self.optionValues[optionindex] = 0
            return
        if val < minimum or val > maximum:
            self.log('validateDigitBox out of range: %s [%s-%s]' % (val, minimum, maximum), xbmc.LOGDEBUG)
            Globals.dialog.notificationDialog(LANGUAGE(32077).format(name=self.optionLabels[optionindex]))
            self.optionValues[optionindex] = default
            return
        self.optionValues[optionindex] = val


    def updateProgress(self, builder: Any, action: str = ''):
        """Uniform build-progress update. No-op unless a progress dialog is active.

        Message: "Applying Rule: <rule name> - <action>" (action optional).
        """
        if not getattr(builder, 'pDialog', None): return
        message = '%s: %s%s'%(LANGUAGE(32209), self.name, (' - %s'%action) if action else '')
        builder.pDialog = Globals.dialog._updateProgressThrottled(builder.pDialog, getattr(builder, 'pCount', 0), message=message, header='%s, %s'%(ADDON_NAME, getattr(builder, 'pMSG', '')))


    def onActionToggleBool(self, optionindex: int):
        self.log("onActionToggleBool")
        self.optionValues[optionindex] = not self.optionValues[optionindex]


    def onActionFunction(self, optionindex: int):
        self.log("onActionFunction")
        value = self.selectBoxOptions[optionindex]()
        if value: self.optionValues[optionindex] = value


    def onActionPickColor(self, optionindex: int, colorlist: list = [], colorfile: str = ""):
        self.log("onActionPickColor")
        value = Globals.dialog.colorDialog(colorlist, self.optionValues[optionindex], colorfile, self.name)
        if value: self.optionValues[optionindex] = value


    def onActionTextBox(self, optionindex: int):
        self.log("onActionTextBox")
        value = Globals.dialog.inputDialog(self.name, default=self.optionValues[optionindex], key=xbmcgui.INPUT_ALPHANUM)
        if value: self.optionValues[optionindex] = value


    def onActionDigitBox(self, optionindex: int):
        self.log("onActionDigitBox")
        info =  Globals.dialog.inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)
        if info != None: self.optionValues[optionindex] = info


    def onActionTimeBox(self, optionindex: int):
        self.log("onActionTimeBox")
        info = Globals.dialog.inputDialog(self.optionLabels[optionindex], default=self.optionValues[optionindex], key=xbmcgui.INPUT_NUMERIC)
        if info != None:
            if info[0] == ' ': info = info[1:]
            if len(info) == 4: info = "0" + info
            self.optionValues[optionindex] = info


    def onActionSelect(self, optionindex: int, header: Optional[str] = None, preselect: Any = None, useDetails: bool = False, autoclose: int = SELECT_DELAY, multi: bool = False):
        self.log("onActionSelect")
        if header is None:
            if multi: header = '%s - %s'%(ADDON_NAME,LANGUAGE(32017).format(type=''))
            else:     header = '%s - %s'%(ADDON_NAME,LANGUAGE(32223).format(type=''))

        so     = self.selectBoxOptions[optionindex]
        keys   = list(so.keys())   if isinstance(so, dict) else so
        values = list(so.values()) if isinstance(so, dict) else so  # parallel to items
        items  = [str(v).title() for v in keys]
        if preselect is None: preselect = Globals._findItemsInLST(values, self.optionValues[optionindex])
        select = Globals.dialog.selectDialog(items, header, preselect, useDetails, autoclose, multi)
        if not select is None:
            if   isinstance(select,list): self.optionValues[optionindex] = [values[idx] for idx in select]
            elif select < len(values):    self.optionValues[optionindex] = values[select]
            elif select:                  self.optionValues[optionindex] = select


    def onActionBrowse(self, optionindex: int, type: int = 0, heading: str = ADDON_NAME, shares: str = '', mask: str = '', useThumbs: bool = True, treatAsFolder: bool = False, multi: bool = False, monitor: bool = False, options: list = [], exclude: list = []):
        self.log("onActionBrowse")
        info = Globals.dialog.browseSources(type, heading, self.optionValues[optionindex], shares, mask, useThumbs, treatAsFolder, multi, monitor, options, exclude)
        if info is not None: self.optionValues[optionindex] = info


    def onActionMultiBrowse(self, optionindex: int, header: str = ADDON_NAME, exclude: list = [], monitor: bool = True):
        self.log("onActionMultiBrowse")
        info = Globals.dialog.multiBrowse(self.optionValues[optionindex], header, exclude, monitor)
        if info is not None: self.optionValues[optionindex] = info


    def onActionResources(self, optionindex: int, ftype: str = ''):
        LOG("onActionResources")
        info = Globals.dialog.browseResources(self.optionValues[optionindex].split('|'), ftype=ftype)
        if not info is None: self.optionValues[optionindex] = '|'.join(info)

#Rules apply sequentially by myId
# myId=200 OVERLAY - channel bug/logo on the overlay. OPEN saves overlay bug state + applies logo/pos/color/diffuse/fade; CLOSE restores.
class ShowChannelBug(BaseRule): #OVERLAY RULES [200-202]
    """USAGE: Show a channel bug/logo on the overlay.
    PARAMS (options): [0] enable bool, [1] position XY, [2] color hex,
    [3] force-diffuse bool, [4] transparency int. runAction(actionid, citem,
    overlay, inherited) saves the overlay bug state on OVERLAY_OPEN and applies
    the options; OVERLAY_CLOSE restores it."""


    def __init__(self):
        self.myId               = 200
        self.name               = LANGUAGE(30143)
        self.description        = LANGUAGE(30144)
        self.optionLabels       = [LANGUAGE(30043),LANGUAGE(30112),LANGUAGE(30044),LANGUAGE(30208),LANGUAGE(33209)]
        self.optionValues       = [Globals.settings.getSettingBool('Enable_ChannelBug'),Globals.settings.getSetting("Channel_Bug_Position_XY"),Globals.settings.getSetting('ChannelBug_Color'),Globals.settings.getSettingBool('Force_Diffuse'),Globals.settings.getSettingInt('ChannelBug_Transparency')]
        self.optionDescriptions = [LANGUAGE(33043),LANGUAGE(33112),LANGUAGE(33044),LANGUAGE(33209),LANGUAGE(33209)]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = [[True,False],[LANGUAGE(30022),LANGUAGE(32136)],"","",list(range(15,51,5))]
        self.storedValues       = [[],[],[],[],[],[]]


    def copy(self) -> 'ShowChannelBug':
        return ShowChannelBug()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def getPosition(self, optionindex: int):
        orgvalue = self.optionValues[optionindex]
        self.onActionSelect(optionindex, LANGUAGE(32223).format(type=''))
        if self.optionValues[optionindex] == self.selectBoxOptions[optionindex][1]:
            from overlaytool import OverlayTool
            try: overlaytool = OverlayTool(OVERLAYTOOL_XML, ADDON_PATH, "default", ADV_RULES=True, Focus_IDX=1, Channel_Bug_Position_XY=self.optionValues[optionindex], ChannelBug_Color=self.optionValues[3])
            except Exception as e: self.log("getPosition, failed! %s"%(e), xbmc.LOGERROR)
            finally: del overlaytool
            value = Globals.properties.getProperty("Channel_Bug_Position_XY")
            Globals.properties.clrProperty("Channel_Bug_Position_XY")
            if value: self.optionValues[optionindex] = value
            else:     self.optionValues[optionindex] = orgvalue
        elif self.optionValues[optionindex] != self.selectBoxOptions[optionindex][0]:
            self.optionValues[optionindex] = orgvalue


    def onAction(self, optionindex: int) -> Any:
        if   optionindex == 0: self.onActionToggleBool(optionindex)
        elif optionindex == 1: self.getPosition(optionindex)
        elif optionindex == 2: self.onActionPickColor(optionindex)
        elif optionindex == 3: self.onActionToggleBool(optionindex)
        elif optionindex == 4: self.onActionSelect(optionindex, LANGUAGE(33209))
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, overlay: Any) -> Any:
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
            self.log("runAction, setting enableChannelBug = %s, channelBugPosition = %s, channelBugColor = %s, channelBugDiffuse = %s, channelBugFade = %s"%(overlay.enableChannelBug,(overlay.channelBugX, overlay.channelBugY),overlay.channelBugColor,overlay.channelBugDiffuse,overlay.channelBugFade))

        elif actionid == RULES_ACTION_OVERLAY_CLOSE:
            overlay.enableChannelBug   = self.storedValues[0]
            overlay.channelBugX, overlay.channelBugY = self.storedValues[1]
            overlay.channelBugColor   = self.storedValues[2]
            overlay.channelBugDiffuse = self.storedValues[3]
            overlay.channelBugFade    = self.storedValues[4]
            self.log("runAction, restoring enableChannelBug = %s, channelBugPosition = %s, channelBugColor = %s, channelBugDiffuse = %s, channelBugFade = %s"%(overlay.enableChannelBug,(overlay.channelBugX, overlay.channelBugY),overlay.channelBugColor,overlay.channelBugDiffuse,overlay.channelBugFade))
        return parameter


# myId=100 PLAYER - on-next programme notification. START saves+applies onNext position/mode; STOP restores.
class ShowOnNext(BaseRule):
    """USAGE: On-next programme notification overlay.
    PARAMS (options): [0] enabled bool, [1] position XY, [2] mode int (0=off,
    1=info, 2=thumb, 3=full, 4=UpNext). runAction saves/applies onNext position
    and mode on PLAYER_START and restores on PLAYER_STOP."""


    def __init__(self):
        self.myId               = 100
        self.name               = LANGUAGE(30045)
        self.description        = LANGUAGE(33045)
        self.optionLabels       = [LANGUAGE(30045),LANGUAGE(32229),LANGUAGE(30196)]
        self.optionValues       = [bool(Globals.settings.getSettingInt('OnNext_Mode')),Globals.settings.getSetting("OnNext_Position_XY"),Globals.settings.getSettingInt('OnNext_Mode')]
        self.optionDescriptions = [LANGUAGE(30045),LANGUAGE(33229),LANGUAGE(30196)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions   = ["",[LANGUAGE(30022),LANGUAGE(32136)],{LANGUAGE(30021):0,LANGUAGE(30193):1,LANGUAGE(30194):2,LANGUAGE(30197):3,LANGUAGE(30195):4}]
        self.storedValues       = [[],[],[],[]]


    def copy(self) -> 'ShowOnNext':
        return ShowOnNext()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def getPosition(self, optionindex: int):
        orgvalue = self.optionValues[optionindex]
        self.onActionSelect(optionindex, LANGUAGE(32223).format(type=''))
        if self.optionValues[optionindex] == self.selectBoxOptions[optionindex][1]:
            from overlaytool import OverlayTool
            try: overlaytool = OverlayTool(OVERLAYTOOL_XML, ADDON_PATH, "default", ADV_RULES=True, Focus_IDX=0, OnNext_Position_XY=self.optionValues[optionindex], OnNext_Color=self.optionValues[2])
            except Exception as e: self.log("getPosition, failed! %s"%(e), xbmc.LOGERROR)
            finally: del overlaytool
            value = Globals.properties.getProperty("OnNext_Position_XY")
            Globals.properties.clrProperty("OnNext_Position_XY")
            if value: self.optionValues[optionindex] = value
            else:     self.optionValues[optionindex] = orgvalue
        elif self.optionValues[optionindex] != self.selectBoxOptions[optionindex][0]:
            self.optionValues[optionindex] = orgvalue


    def onAction(self, optionindex: int) -> Any:
        if   optionindex == 0: self.onActionToggleBool(optionindex)
        elif optionindex == 1: self.getPosition(optionindex)
        elif optionindex == 2: self.onActionSelect(optionindex, LANGUAGE(30196))
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, player: Any) -> Any:
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


# myId=201 OVERLAY - fullscreen vignette. OPEN saves+applies enable/image/zoom/shift/ratio/stretch; CLOSE restores.
class SetScreenVingette(BaseRule):
    """USAGE: Fullscreen vignette effect on the overlay.
    PARAMS (options): [0] enable bool, [1] image, [2] zoom, [3] vertical shift,
    [4] pixel ratio, [5] nonlinear stretch. runAction saves/applies on
    OVERLAY_OPEN (auto-swaps _Day/_Night image by hour) and restores on CLOSE."""


    def __init__(self):
        self.myId               = 201
        self.name               = LANGUAGE(30177)
        self.description        = LANGUAGE(33177)
        self.optionLabels       = [LANGUAGE(30174),LANGUAGE(30175),LANGUAGE(30176),LANGUAGE(30178),LANGUAGE(30185),LANGUAGE(30186)]
        self.optionValues       = [False,' ',1.00,0.00,1.00,False]
        self.optionDescriptions = [LANGUAGE(33174),LANGUAGE(33175),LANGUAGE(33176),LANGUAGE(34179),LANGUAGE(33185),LANGUAGE(34186)]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_CLOSE]
        self.selectBoxOptions   = ['','',list(Globals._frange(5,21,1)),list(range(-2,3,1)),list(Globals._frange(5,21,1)),'']#[LANGUAGE(30022),LANGUAGE(32136)]]
        self.storedValues       = [[],[],[]]


    def copy(self) -> 'SetScreenVingette':
        return SetScreenVingette()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,self.optionValues)

            # todo set viewmode as {} response from json.


    def getPosition(self, optionindex: int):#todo vin utility to adjust zoom,vshift,pratio and nls
        Globals.dialog.notificationDialog(LANGUAGE(32020))


    def getImage(self, image: str = '') -> str:
        self.log('getImage, In image = %s'%(image))
        day    = _DAY_RE.search(image)
        night  = _NIGHT_RE.search(image)
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


    def onAction(self, optionindex: int) -> Any:
        if   optionindex == 1:       self.onActionBrowse(optionindex, type=1, heading=self.optionLabels[1], mask=xbmc.getSupportedMedia('picture'), exclude=[12,13,14,15,16,17])
        elif optionindex in [0,5]:   self.onActionToggleBool(optionindex)
        elif optionindex in [2,3,4]: self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, overlay: Any) -> Any:
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


# myId=202 OVERLAY - MST3K silhouette animation (cycles 2 gifs on a 5s self-timer via fractional action 30.1). OPEN saves, CLOSE restores.
class MST3k(BaseRule):
    """USAGE: Mystery Science Theater 3000 silhouette animation on the overlay.
    PARAMS (options): [0] enabled bool. Cycles two gifs on a 5s self-timer that
    fires the fractional action 30.1 via overlay.runActions; restores on close."""


    def __init__(self):
        self.myId               = 202
        self.name               = "Mystery Science Theater 3K Silhouette"
        self.description        = "Animated Silhouette of MST3K"
        self.optionLabels       = ['Enable MST3K Silhouette']
        self.optionValues       = [False]
        self.optionDescriptions = ["Enable Silhouette"]
        self.actions            = [RULES_ACTION_OVERLAY_OPEN,RULES_ACTION_OVERLAY_OPEN+.1,RULES_ACTION_OVERLAY_CLOSE]
        self.storedValues       = [[],[],[]]
        self.threadTimer        = Timer(SERVICE_INTERVAL, self.runAction)
        self.threadTimer.daemon = True
        self.optionImages       = [os.path.join(MEDIA_LOC,'overlays','MST3K_1.gif'), os.path.join(MEDIA_LOC,'overlays','MST3K_2.gif')]


    def copy(self) -> 'MST3k':
        return MST3k()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def setImage(self, actionid: str, citem: dict, overlay: Any, image: str) -> str:
        if not self.threadTimer.is_alive():
            self.threadTimer = Timer(SERVICE_INTERVAL, overlay.runActions,[actionid, citem, None, overlay])
            self.threadTimer.name = 'MST3k.setImage'
            self.threadTimer.daemon = True
            self.threadTimer.start()
        self.log('setImage, image = %s'%(image))
        return image


    def onAction(self, optionindex: int) -> Any:
        if optionindex == 0: self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, overlay: Any) -> Any:
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
                except Exception as e: self.log('threadTimer join failed: %s' % e, xbmc.LOGDEBUG)
        return parameter


# myId=101 PLAYER - toggle the fullscreen overlay. START saves+overrides enableOverlay; STOP restores.
class DisableOverlay(BaseRule): #PLAYER RULES [100-199]
    """USAGE: Disable the fullscreen overlay for this channel.
    PARAMS (options): [0] enabled bool. runAction saves/overrides
    player.enableOverlay on PLAYER_START and restores on PLAYER_STOP."""


    def __init__(self):
        self.myId               = 101
        self.name               = LANGUAGE(30042)
        self.description        = LANGUAGE(33042)
        self.optionLabels       = [LANGUAGE(30042)]
        self.optionValues       = [Globals.settings.getSettingBool('Overlay_Enable')]
        self.optionDescriptions = [LANGUAGE(33042)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def copy(self) -> 'DisableOverlay':
        return DisableOverlay()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, player: Any) -> Any:
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.enableOverlay
            player.enableOverlay = self.optionValues[0]
            self.log("runAction, setting enableOverlay = %s"%(player.enableOverlay))

        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.enableOverlay = self.storedValues[0]
            self.log("runAction, restore enableOverlay = %s"%(player.enableOverlay))
        return parameter


# myId=102 PLAYER - force subtitles on/off. START saves+overrides lastSubState; STOP restores.
class ForceSubtitles(BaseRule):
    """USAGE: Force subtitles on/off for this channel.
    PARAMS (options): [0] enabled bool. runAction saves/overrides
    player.lastSubState on PLAYER_START and restores on PLAYER_STOP."""


    def __init__(self):
        self.myId               = 102
        self.name               = "Force Subtitles"
        self.description        = "Show Subtitles"
        self.optionLabels       = ['Force Subtitles?']
        self.optionValues       = [Globals.builtin.isSubtitle()]
        self.optionDescriptions = [""]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def copy(self) -> 'ForceSubtitles':
        return ForceSubtitles()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, pvritem: Any, player: Any) -> Any:
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.lastSubState
            player.lastSubState  = self.optionValues[0]
            self.log("runAction, setting lastSubState = %s"%(player.lastSubState))

        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.lastSubState = self.storedValues[0]
            self.log("runAction, restoring lastSubState = %s"%(player.lastSubState))
        return pvritem


# myId=103 PLAYER - disable Trakt scrobbling. START saves+overrides disableTrakt; STOP restores.
class DisableTrakt(BaseRule):
    """USAGE: Disable Trakt scrobbling for this channel.
    PARAMS (options): [0] enabled bool. runAction saves/overrides
    player.disableTrakt on PLAYER_START and restores on PLAYER_STOP."""


    def __init__(self):
        self.myId               = 103
        self.name               = "Trakt scrobbling"
        self.description        = "Disable Trakt scrobbling."
        self.optionLabels       = [LANGUAGE(30131)]
        self.optionValues       = [Globals.settings.getSettingBool('Disable_Trakt')]
        self.optionDescriptions = [LANGUAGE(33131)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def copy(self) -> 'DisableTrakt':
        return DisableTrakt()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, player: Any) -> Any:
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.disableTrakt
            player.disableTrakt = self.optionValues[0]
            self.log("runAction, setting disableTrakt = %s"%(player.disableTrakt))

        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.disableTrakt = self.storedValues[0]
            self.log("runAction, restoring disableTrakt = %s"%(player.disableTrakt))
        return parameter


# myId=104 PLAYER - rollback watched/playcount. START saves+overrides rollbackPlaycount; STOP restores.
class RollbackPlaycount(BaseRule):
    """USAGE: Roll back watched/playcount for this channel's items.
    PARAMS (options): [0] enabled bool. runAction saves/overrides
    player.rollbackPlaycount on PLAYER_START and restores on PLAYER_STOP."""


    def __init__(self):
        self.myId               = 104
        self.name               = "Rollback Playcount"
        self.description        = "Passive Playback w/o playcount & progress tracking."
        self.optionLabels       = [LANGUAGE(30132)]
        self.optionValues       = [Globals.settings.getSettingBool('Rollback_Watched')]
        self.optionDescriptions = [LANGUAGE(33132)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def copy(self) -> 'RollbackPlaycount':
        return RollbackPlaycount()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, player: Any) -> Any:
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.rollbackPlaycount
            player.rollbackPlaycount = self.optionValues[0]
            self.log("runAction, setting rollbackPlaycount = %s"%(player.rollbackPlaycount))

        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.rollbackPlaycount = self.storedValues[0]
            self.log("runAction, restoring rollbackPlaycount = %s"%(player.rollbackPlaycount))
        return parameter


# myId=105 PLAYER - restart/replay button behaviour. START saves+overrides replayPercentage; STOP restores.
class DisableRestart(BaseRule):
    """USAGE: Control the restart/replay button behaviour.
    PARAMS (options): [0] replay percentage select (25-95). runAction
    saves/overrides player.replayPercentage on PLAYER_START, restores on STOP."""


    def __init__(self):
        self.myId               = 105
        self.name               = "Restart Button"
        self.description        = LANGUAGE(33153)
        self.optionLabels       = [LANGUAGE(30153)]
        self.optionValues       = [Globals.settings.getSettingInt('Replay_Percentage')]
        self.optionDescriptions = [LANGUAGE(33153)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.selectBoxOptions   = [list(range(25,100,5))]
        self.storedValues       = [[]]


    def copy(self) -> 'DisableRestart':
        return DisableRestart()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,self.optionValues[0])


    def onAction(self, optionindex: int) -> Any:
        self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, player: Any) -> Any:
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.replayPercentage
            player.replayPercentage = self.optionValues[0]
            self.log("runAction, setting replayPercentage = %s"%(player.replayPercentage))

        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.replayPercentage = self.storedValues[0]
            self.log("runAction, restoring replayPercentage = %s"%(player.replayPercentage))
        return parameter


# myId=106 PLAYER - info-on-change behaviour. START saves+overrides infoOnChange; STOP restores.
class DisableOnChange(BaseRule):
    """USAGE: Control info-on-change behaviour for this channel.
    PARAMS (options): [0] enabled bool. runAction saves/overrides
    player.infoOnChange on PLAYER_START and restores on PLAYER_STOP."""


    def __init__(self):
        self.myId               = 106
        self.name               = LANGUAGE(30170)
        self.description        = LANGUAGE(33170)
        self.optionLabels       = [LANGUAGE(30170)]
        self.optionValues       = [Globals.settings.getSettingBool('Enable_OnInfo')]
        self.optionDescriptions = [LANGUAGE(33170)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_PLAYER_STOP]
        self.storedValues       = [[]]


    def copy(self) -> 'DisableOnChange':
        return DisableOnChange()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, player: Any) -> Any:
        if actionid == RULES_ACTION_PLAYER_START:
            self.storedValues[0] = player.infoOnChange
            player.infoOnChange = self.optionValues[0]
            self.log("runAction, setting infoOnChange = %s"%(player.infoOnChange))

        elif actionid == RULES_ACTION_PLAYER_STOP:
            player.infoOnChange = self.storedValues[0]
            self.log("runAction, restoring infoOnChange = %s"%(player.infoOnChange))
        return parameter


# myId=107 PLAYER - parental pin lock. PLAYER_START gates locked channels/ratings behind a PIN.
class PinLockRule(BaseRule): #PLAYER RULES [100-199]
    """USAGE: Parental PIN lock for channels or ratings.
    PARAMS (options): [0] PIN, [1] lock this channel bool, [2] lock rating
    select (programmes at/above this MPAA severity — any rating system is
    interpreted to MPAA). On PLAYER_START a locked programme prompts for the
    PIN: correct plays, wrong leaves current playback untouched, and with
    nothing playing opens the channel list. Approval is per-channel and
    resets on CHANNEL_STOP."""


    def __init__(self):
        self.myId               = 107
        self.name               = LANGUAGE(32330)
        self.description        = LANGUAGE(32331)
        self.optionLabels       = [LANGUAGE(32332),LANGUAGE(32333),LANGUAGE(32334)]
        self.optionValues       = ['',False,0]
        self.optionDescriptions = [LANGUAGE(32331),LANGUAGE(32331),LANGUAGE(32331)]
        self.actions            = [RULES_ACTION_PLAYER_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = ["",'',{'Off':0,'G':1,'PG':2,'PG-13':3,'R':4,'NC-17':5}]
        self.storedValues       = [False]


    def copy(self) -> 'PinLockRule':
        return PinLockRule()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self._isEnabled()])


    def _isEnabled(self) -> bool:
        return bool(self.optionValues[1] or int(self.optionValues[2] or 0))


    def _isLocked(self, parameter: Any) -> bool:
        if self.optionValues[1]: return True
        threshold = int(self.optionValues[2] or 0)
        if not threshold: return False
        fitem = parameter.get('fitem', parameter) if isinstance(parameter, dict) else parameter
        if not isinstance(fitem, dict): return False
        return ratings.rank(fitem.get('mpaa','')) >= threshold


    def _promptPIN(self) -> Optional[str]:
        try: return Globals.dialog.inputDialog(self.name, key=xbmcgui.INPUT_NUMERIC)
        except Exception as e: self.log('_promptPIN, failed! %s'%(e), xbmc.LOGERROR)
        return None


    def onAction(self, optionindex: int) -> Any:
        if   optionindex == 0: self.onActionTextBox(optionindex)
        elif optionindex == 1: self.onActionToggleBool(optionindex)
        elif optionindex == 2: self.onActionSelect(optionindex, LANGUAGE(32334))
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, player: Any) -> Any:
        if actionid == RULES_ACTION_CHANNEL_STOP:
            self.storedValues[0] = False  # reset per-channel approval
            return parameter
        if actionid != RULES_ACTION_PLAYER_START:
            return parameter
        if not self._isEnabled() or not self._isLocked(parameter):
            return parameter
        if self.storedValues and self.storedValues[0]:
            return parameter  # already approved this channel
        self.log('[%s] PinLock, locked programme, prompting for PIN'%(citem.get('id')))
        pin = self._promptPIN()
        if pin is not None and str(pin).strip() == str(self.optionValues[0]).strip():
            self.storedValues[0] = True
            self.log('[%s] PinLock, correct PIN, unlocking'%(citem.get('id')))
            return parameter
        self.log('[%s] PinLock, incorrect PIN'%(citem.get('id')))
        if player.isPlaying():
            self.log('[%s] PinLock, already playing - nothing happens'%(citem.get('id')))
        else:
            self.log('[%s] PinLock, not playing - opening channel list'%(citem.get('id')))
            try: Globals.builtin.executewindow('ActivateWindow(10025, "plugin://%s/")'%(ADDON_ID))
            except Exception as e: self.log('PinLock, executewindow failed! %s'%(e), xbmc.LOGERROR)
        return parameter


# myId=400 CHANNEL - force a channel rebuild on every build cycle (sets changed=True on CHANNEL_CITEM).
class ForceRebuild(BaseRule):
    """USAGE: Force this channel to rebuild on every build cycle.
    PARAMS (options): [0] enabled bool. runAction sets parameter['changed']=True
    on CHANNEL_CITEM so the builder treats it as modified."""


    def __init__(self):
        self.myId               = 400
        self.name               = "Force Rebuild"
        self.description        = "Force Rebuild All Channel Content."
        self.optionLabels       = ["Force Rebuild Channel"]
        self.optionValues       = [False]
        self.optionDescriptions = ["Always Force Rebuild Channel"]
        self.actions            = [RULES_ACTION_CHANNEL_CITEM]
        self.storedValues       = []


    def copy(self) -> 'ForceRebuild':
        return ForceRebuild()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,self.optionValues)


    def onAction(self, optionindex: int) -> Any:
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, builder: Any) -> Any:
        if actionid == RULES_ACTION_CHANNEL_CITEM:
            if self.optionValues[0]: parameter['changed'] = True
            self.log("runAction, setting changed = %s"%(self.optionValues[0]))
        return parameter


# myId=500 BUILD - duration accuracy options. START saves+overrides accurate/save/minDuration; STOP restores.
class DurationOptions(BaseRule): #BUILD_SOURCE RULES [500-507]
    """USAGE: Duration accuracy and storage options for the build.
    PARAMS (options): [0] duration type select, [1] store duration bool,
    [2] seek tolerance digit. runAction saves/overrides builder
    accurate/saveDuration/minDuration on CHANNEL_START and restores on STOP."""


    def __init__(self):
        self.myId               = 500
        self.name               = "Duration Options"
        self.description        = "Duration Options"
        self.optionLabels       = [LANGUAGE(30049),LANGUAGE(30052),LANGUAGE(32233)]
        self.optionValues       = [Globals.settings.getSettingInt('Duration_Type'),Globals.settings.getSettingBool('Store_Duration'),Globals.settings.getSettingInt('Seek_Tolerance')]
        self.optionDescriptions = [LANGUAGE(33015),LANGUAGE(33049),LANGUAGE(33052),LANGUAGE(32233)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [{LANGUAGE(30050):0,LANGUAGE(30051):1},[],list(range(0,900,5))]
        self.storedValues       = [[],[],[]]


    def copy(self) -> 'DurationOptions':
        return DurationOptions()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,self.optionValues)


    def onAction(self, optionindex: int) -> Any:
        if optionindex == 0:
            self.onActionSelect(optionindex, LANGUAGE(30049))
            self.validateRange(optionindex, 0, 1, 0)
        else:
            self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
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


# myId=501 BUILD - include extras/strm/3D/stream-details. START saves+overrides include flags; STOP restores.
class IncludeOptions(BaseRule):
    """USAGE: What file types to include when building the channel.
    PARAMS (options): [0] extras, [1] strm, [2] 3D, [3] stream-details (bools).
    runAction saves/overrides the builder include flags on CHANNEL_START,
    restores on CHANNEL_STOP."""


    def __init__(self):
        self.myId               = 501
        self.name               = "Include Options"
        self.description        = "Include Options"
        self.optionLabels       = [LANGUAGE(30053),LANGUAGE(30054),LANGUAGE(30055),LANGUAGE(30225)]
        self.optionValues       = [Globals.settings.getSettingBool('Enable_Extras'),Globals.settings.getSettingBool('Enable_Strms'),Globals.settings.getSettingBool('Enable_3D'),Globals.settings.getSettingBool('Enable_Details')]
        self.optionDescriptions = [LANGUAGE(33053),LANGUAGE(33054),LANGUAGE(33055),LANGUAGE(33225)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.storedValues       = [[],[],[],[]]


    def copy(self) -> 'IncludeOptions':
        return IncludeOptions()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,self.optionValues)


    def onAction(self, optionindex: int) -> Any:
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, builder: Any) -> Any:
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


# myId=502 BUILD - pre-roll bumpers/ratings. START updates bctTypes[bumpers/ratings] (max/auto/chance/sources); STOP restores.
class PreRoll(BaseRule):
    """USAGE: Insert pre-roll bumpers/ratings before channel content.
    PARAMS (options): [0] enable (-1 auto/0 off), [1] chance %, [2]/[3] bumpers
    resource + folder, [4]/[5] ratings resource + folder. runAction updates
    builder.bctTypes['bumpers'/'ratings'] on CHANNEL_START, restores on STOP."""


    def __init__(self):
        self.myId               = 502
        self.name               = "Pre-Roll"
        self.description        = "Pre-Roll Options"
        self.optionLabels       = [LANGUAGE(30017),LANGUAGE(30139),LANGUAGE(30029),LANGUAGE(30028),"Bumpers Folder","Ratings Folder"]
        self.optionValues       = [Globals.settings.getSettingInt('Enable_Preroll'),Globals.settings.getSettingInt('Random_Pre_Chance'),Globals.settings.getSetting('Resource_Bumpers'),Globals.settings.getSetting('Resource_Ratings'),[os.path.join(FILLER_LOC,'Bumpers','')],[os.path.join(FILLER_LOC,'Ratings','')]]
        self.optionDescriptions = [LANGUAGE(33017),LANGUAGE(33139),LANGUAGE(33029),LANGUAGE(33028),"",""]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [{LANGUAGE(30022):-1,LANGUAGE(30021):0},list(range(0,101,1)),"","","",""]
        self.storedValues       = [{},{}]


    def copy(self) -> 'PreRoll':
        return PreRoll()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        if   optionindex in [0,1]: self.onActionSelect(optionindex)
        elif optionindex in [2,3]: self.onActionResources(optionindex, ftype={2:"bumpers",3:"ratings"}[optionindex])
        elif optionindex in [4,5]: self.onActionMultiBrowse(optionindex, header="%s for %s"%(LANGUAGE(32080), {4:"Bumpers",5:"Ratings"}[optionindex]), exclude=[12,13,14,15,16,21,22])
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, builder: Any) -> Any:
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


# myId=503 BUILD - post-roll adverts/trailers (+extras). START updates bctTypes; STOP restores.
class PostRoll(BaseRule):
    """USAGE: Insert post-roll adverts/trailers (+ extras) after content.
    PARAMS (options): [0] enable (-1/0/1/2/3), [1] chance %, [2]/[3] adverts
    resource + folder, [4]/[5] trailers resource + folder, [6]/[7] include
    KODI trailers/extras bools. runAction updates builder.bctTypes on
    CHANNEL_START, restores on CHANNEL_STOP."""


    def __init__(self):
        self.myId               = 503
        self.name               = "Post-Roll"
        self.description        = "Post-Roll Options"
        self.optionLabels       = [LANGUAGE(30019),LANGUAGE(30134),LANGUAGE(30030),"Adverts Folder",LANGUAGE(30031),"Trailers Folder",LANGUAGE(30126),LANGUAGE(30053)]
        self.optionValues       = [Globals.settings.getSettingInt('Enable_Postroll'),Globals.settings.getSettingInt('Random_Post_Chance'),Globals.settings.getSetting('Resource_Adverts'),[os.path.join(FILLER_LOC,'Adverts','')],Globals.settings.getSetting('Resource_Trailers'),[os.path.join(FILLER_LOC,'Trailers','')],Globals.settings.getSettingBool('Include_Trailers_KODI'),Globals.settings.getSettingBool('Include_Extras_KODI')]
        self.optionDescriptions = [LANGUAGE(33019),LANGUAGE(33139),LANGUAGE(33030),"",LANGUAGE(33031),"",LANGUAGE(33126),LANGUAGE(33233)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [{LANGUAGE(30022):-1,LANGUAGE(30021):0,LANGUAGE(30026):1,LANGUAGE(30024):2,LANGUAGE(30025):3},list(range(0,101,1)),[]]
        self.storedValues       = [{},{}]


    def copy(self) -> 'PostRoll':
        return PostRoll()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        if   optionindex in [0,1]: self.onActionSelect(optionindex)
        elif optionindex in [2,4]: self.onActionResources(optionindex, ftype={2:"adverts",4:"trailers"}[optionindex])
        elif optionindex in [3,5]: self.onActionMultiBrowse(optionindex, header="%s for %s"%(LANGUAGE(32080),{3:"Adverts",5:"Trailers"}[optionindex]), exclude=[12,13,14,15,16,21,22])
        elif optionindex in [6,7]: self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, builder: Any) -> Any:
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


# myId=504 BUILD - interleave set size + repeat. START saves+overrides interleaveSet/Repeat; STOP restores.
class InterleaveValue(BaseRule):
    """USAGE: Interleave content across sources.
    PARAMS (options): [0] interleave set select (0-25), [1] repeat bool.
    runAction saves/overrides builder.interleaveSet/Repeat on CHANNEL_START,
    restores on CHANNEL_STOP."""


    def __init__(self):
        self.myId               = 504
        self.name               = LANGUAGE(30192)
        self.description        = LANGUAGE(34179)
        self.optionLabels       = [LANGUAGE(30179),LANGUAGE(30211)]
        self.optionValues       = [Globals.settings.getSettingInt('Interleave_Set'), Globals.settings.getSettingBool('Interleave_Repeat')]
        self.optionDescriptions = [LANGUAGE(34179),LANGUAGE(33211)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [list(range(0,26,1))]
        self.storedValues       = [[],[]]


    def copy(self) -> 'InterleaveValue':
        return InterleaveValue()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,self.optionValues[0])


    def onAction(self, optionindex: int) -> Any:
        if optionindex == 0: self.onActionSelect(optionindex)
        else:                self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, builder: Any) -> Any:
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


# myId=600 BUILD - seasonal/holiday content injection (FILEARRAY_PRE builds a fileArray from holiday queries).
class SeasonalRule(BaseRule): #BUILD_SELECT RULES [600-699]
    """USAGE: Seasonal/holiday content injection during the build.
    PARAMS (options): [0] internal holiday query list (path/method/enum/limits/
    sort/filter/holiday). runAction on BUILD_FILEARRAY_PRE builds a fileArray
    from the queries (cached per path) and sets the channel's holiday logo."""
    """
    SeasonalRule
    """


    def __init__(self):
        self.myId               = 600
        self.name               = "Seasonal"
        self.description        = "Automatically Populate Channels with Seasonal Media."
        self.optionLabels       = ["Holiday"]
        self.optionValues       = [[{"path":"","method":"","enum":"","limits":{},"sort":{},"filter":{},"holiday":{}}]]
        self.optionDescriptions = ["INTERNAL USE ONLY!"]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE]
        self.storedValues       = [[]]


    def copy(self) -> 'SeasonalRule':
        return SeasonalRule()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,self.optionValues[0][0].get('holiday',{}).get('name','None'))


    def runAction(self, actionid: str, citem: dict, parameter: Any, builder: Any) -> Any:
        if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
            if self.optionValues[0][0].get('holiday',{}):
                try:
                    if builder.pDialog: self.updateProgress(builder, LANGUAGE(32335))
                    self.log(f"[{citem['id']}] runAction, {self.optionValues[0][0]['holiday']['name']}")
                    for query in self.optionValues[0]:
                        citem['logo'] = (query.get('holiday',{}).get('logo') or LOGO_SEASONAL)
                        if query["key"].startswith(tuple(TV_TYPES)): #filter out extras/specials
                            if not builder.incExtras:
                                # If filter is a single rule (has 'field'), wrap in 'and' first
                                if query["filter"].get("field") and not query["filter"].get("and"):
                                    query["filter"] = {"and": [query["filter"]]}
                                query["filter"].setdefault("and",[]).extend([{"field":"season" ,"operator":"greaterthan","value":"0"},
                                                                             {"field":"episode","operator":"greaterthan","value":"0"}])
                            else:
                                query['filter']['and'] = [r for r in query['filter'].get("and", []) if not (('season' in r or 'episode' in r) and r.get("value") == "0")]
                                query['filter']['and'] = Globals._setDictLST(query['filter']['and'])
                        # Cache buildFileList result per path to avoid repeated JSONRPC calls
                        path = query.get('path','')
                        cache_key = f'seasonal.{citem["id"]}.{FileAccess._getMD5(path)}'
                        cached = builder.jsonRPC.cache.get(cache_key)
                        if cached is not None:
                            self.storedValues[0].append(cached)
                        else:
                            result = builder.buildFileList(citem, path, 'video', (query.get('limit') or builder.limit), query.get('sort',{}), builder.limits, query)
                            if result: builder.jsonRPC.cache.set(cache_key, result, expiration=datetime.timedelta(hours=1))
                            self.storedValues[0].append(result)
                    return [fileList for fileList in self.storedValues[0] if fileList] #fileArray
                except Exception as e: self.log(f"[{citem['id']}] runAction, failed! {e}", xbmc.LOGERROR)
                return []
        return parameter


# myId=505 BUILD - sort method/order (List.Sort enums, class-cached). START overrides builder.sort; STOP restores.
class HandleMethodOrder(BaseRule):
    """USAGE: Sort method/order for the channel's file list.
    PARAMS (options): [0] method (List.Sort enum), [1] order, [2] ignore
    articles bool, [3] use artist sort bool. runAction saves/overrides
    builder.sort on CHANNEL_START, restores on CHANNEL_STOP."""
    """Rule 505: Override sort method and order for channel builds.

    Caches sort/order enum lookups at class level to avoid repeated JSONRPC
    Introspect calls on every instantiation (allRules → copy → __init__).
    """

    _cached_sort  = None
    _cached_order = None

    def __init__(self):
        self.myId               = 505
        self.name               = LANGUAGE(32232)
        self.description        = LANGUAGE(33232)
        self.optionLabels       = ['Method','Order','Ignore Articles','Ignore Artist Sort Name']
        self.optionValues       = ['random','ascending',True,True]
        self.optionDescriptions = ["","","",""]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [self.getSort(), self.getOrder()]
        self.storedValues       = [[],[],[],[],[]]


    def copy(self) -> 'HandleMethodOrder':
        return HandleMethodOrder()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,self.optionValues)


    def getSort(self) -> list:
        if HandleMethodOrder._cached_sort is None:
            HandleMethodOrder._cached_sort = JSONRPC().getEnums("List.Sort",type="method")
        return HandleMethodOrder._cached_sort


    def getOrder(self) -> list:
        if HandleMethodOrder._cached_order is None:
            HandleMethodOrder._cached_order = JSONRPC().getEnums("List.Sort",type="order")
        return HandleMethodOrder._cached_order


    def onAction(self, optionindex: int) -> Any:
        if optionindex in [2,3]: self.onActionToggleBool(optionindex)
        else:                    self.onActionSelect(optionindex, self.optionLabels[optionindex])
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, builder: Any) -> Any:
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.sort
            builder.sort.update({"method":self.optionValues[0],"order":self.optionValues[1],"ignorearticle":self.optionValues[2],"useartistsortname":self.optionValues[3]})
            self.log("runAction, setting sort to %s"%(builder.sort))

        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.sort = self.storedValues[0]
            self.log("runAction, restoring sort to %s"%(builder.sort))

        return parameter


# myId=506 BUILD - list limit/end/start. START overrides builder.limit+limits; STOP restores.
class HandleLimits(BaseRule):
    """USAGE: Pagination limits for the channel's content query.
    PARAMS (options): [0] limit select, [1] end, [2] start (digits).
    runAction saves/overrides builder.limit and builder.limits on CHANNEL_START,
    restores on CHANNEL_STOP."""


    def __init__(self):
        self.myId               = 506
        self.name               = LANGUAGE(32263)
        self.description        = LANGUAGE(33015)
        self.optionLabels       = ['Limit','Limits End','Limits Start']
        self.optionValues       = [Globals.settings.getSettingInt('Page_Limit'),-1,0]
        self.optionDescriptions = [f"Force Limit [{Globals.settings.getSettingInt('Page_Limit')}:Default]","Force End [-1:Auto, 0:Unlimited]","Force Start [-1:Unlimited, 0:Auto]"]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [[0,10,25,50,100,250,500,1000]]
        self.storedValues       = [[],{}]


    def copy(self) -> 'HandleLimits':
        return HandleLimits()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,self.optionValues)


    def onAction(self, optionindex: int) -> Any:
        if optionindex == 0: self.onActionSelect(optionindex)
        else:
            self.onActionDigitBox(optionindex)
            self.validateDigitBox(optionindex,-1,self.selectBoxOptions[0][-1] if self.storedValues[1].get('total',0) == 0 else self.storedValues[1].get('total'),25)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, builder: Any) -> Any:
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

        return parameter


# myId=700 BUILD - force episode ordering (superseded by EvenShowsRule; partially implemented).
class ForceEpisodeOrder(BaseRule):
    """USAGE: Force episode ordering during the build.
    PARAMS (options): [0] enabled bool. NOTE: largely superseded by
    EvenShowsRule(1000) and only partially implemented."""


    def __init__(self):
        self.myId               = 700
        self.name               = LANGUAGE(30181)
        self.description        = LANGUAGE(33181)
        self.optionLabels       = [LANGUAGE(30181)]
        self.optionValues       = [False]  # superseded by EvenShowsRule (701) - disabled by default
        self.optionDescriptions = [LANGUAGE(33181)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE,RULES_ACTION_CHANNEL_BUILD_PATH,RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE,RULES_ACTION_CHANNEL_STOP]
        self.storedValues       = [[],[],{},[],[],[]]
        self.selectBoxOptions   = []


    def copy(self) -> 'ForceEpisodeOrder':
        return ForceEpisodeOrder()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        return self.optionValues[optionindex]


    def _episodeSort(self, showArray: dict = {}) -> list:
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


    def _sortShows(self, fileList: list = []) -> tuple:
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


    def runAction(self, actionid: str, citem: dict, parameter: Any, builder: Any) -> Any:
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
                    self.updateProgress(builder, LANGUAGE(32336))
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
                self.storedValues = [[],[],{},[],[],[]]  # clear memory from show/movie partitioning
                self.log("runAction, restoring enableEven = %s, evenEpisode = %s, evenShuffle = %s"%(builder.enableEven,builder.evenEpisode,builder.evenShuffle))

        return parameter


# myId=605 BUILD - force random sort. FILEARRAY_PRE sets method=random; FILELIST_PRE restores + shuffles.
class ForceRandom(BaseRule):
    """USAGE: Force random ordering of the channel's content.
    PARAMS (options): [0] enabled bool. runAction sets method=random on
    FILEARRAY_PRE and shuffles the fileList on FILELIST_PRE."""


    def __init__(self):
        self.myId               = 605
        self.name               = LANGUAGE(30182)
        self.description        = LANGUAGE(33183)
        self.optionLabels       = [LANGUAGE(30182)]
        self.optionValues       = [True]
        self.optionDescriptions = [LANGUAGE(33183)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE,RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.storedValues       = [[]]


    def copy(self) -> 'ForceRandom':
        return ForceRandom()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, fileList: Any, builder: Any) -> Any:
        if actionid == RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE:
            self.updateProgress(builder, LANGUAGE(32349))
            self.storedValues[0] = builder.sort
            builder.sort.update({"method":"random"})
            self.log("runAction, setting sort to %s"%(builder.sort))

        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE:
            self.updateProgress(builder, LANGUAGE(32350))
            builder.sort = self.storedValues[0]
            self.log("runAction, restoring sort and forcing random shuffle of %s items"%(len(fileList)))
            return Globals._randomShuffle(fileList)
        return fileList


# myId=701 BUILD - even show distribution (chunk episodes + interleave movies). START sets even flags; FILELIST_PRE reorders; STOP restores.
class EvenShowsRule(BaseRule): #BUILD_SCHEDULE RULES [700-799]
    """USAGE: Distribute shows evenly (chunk episodes, interleave movies).
    PARAMS (options): [0] even chunk size select (0-25), [1] force episode bool,
    [2] force random bool (mutually exclusive with [1]). runAction on
    CHANNEL_START/FILELIST_PRE reorders the fileList, restores on STOP."""


    def __init__(self):
        self.myId               = 701
        self.name               = LANGUAGE(30121)
        self.description        = LANGUAGE(33121)
        self.optionLabels       = [LANGUAGE(30180),LANGUAGE(30181),LANGUAGE(30182)]
        self.optionValues       = [Globals.settings.getSettingInt('Enable_Even'),Globals.settings.getSettingBool('Enable_Even_Force_Episode'),Globals.settings.getSettingBool('Enable_Even_Force_Random')]
        self.optionDescriptions = [LANGUAGE(33121),LANGUAGE(33181),LANGUAGE(30182)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE,RULES_ACTION_CHANNEL_STOP]
        self.selectBoxOptions   = [list(range(0,26,1))]
        self.storedValues       = [[],[],[],{},[]]


    def copy(self) -> 'EvenShowsRule':
        return EvenShowsRule()


    def getTitle(self) -> str:
        return self.name


    def toggle(self, optionindex: int):
        if optionindex == 1:
            if self.optionValues[2]: self.optionValues[2] = not self.optionValues[optionindex]
        elif optionindex == 2:
            if self.optionValues[1]: self.optionValues[1] = not self.optionValues[optionindex]


    def onAction(self, optionindex: int) -> Any:
        if optionindex == 0: self.onActionSelect(optionindex,self.optionLabels[optionindex])
        else:
            self.onActionToggleBool(optionindex)
            self.toggle(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, builder: Any) -> Any:
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = builder.enableEven
            self.storedValues[1] = builder.evenEpisode
            self.storedValues[2] = builder.evenShuffle
            builder.enableEven   = bool(self.optionValues[0])
            builder.evenEpisode  = bool(self.optionValues[1])
            builder.evenShuffle  = bool(self.optionValues[2])
            self.log("runAction, setting enableEven = %s, evenEpisode = %s, evenShuffle = %s"%(builder.enableEven, builder.evenEpisode, builder.evenShuffle))

        elif actionid == RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE:
            if self.optionValues[0] and isinstance(parameter, list) and len(parameter) > 0:
                self.updateProgress(builder, LANGUAGE(32338))
                self.storedValues[3] = {}
                self.storedValues[4] = []
                showArray, movies = self._sortShows(parameter, bool(self.optionValues[1]), bool(self.optionValues[2]))
                return self._mergeShows(showArray, movies, builder)

        elif actionid == RULES_ACTION_CHANNEL_STOP:
            builder.enableEven  = self.storedValues[0]
            builder.evenEpisode = self.storedValues[1]
            builder.evenShuffle = self.storedValues[2]
            self.storedValues   = [[],[],[],{},[]]
            self.log("runAction, restoring enableEven = %s, evenEpisode = %s, evenShuffle = %s"%(builder.enableEven, builder.evenEpisode, builder.evenShuffle))
        return parameter


    def _chunkEpisodes(self, showArray: dict = {}):
        for show, episodes in showArray.items():
            yield show, [episodes[i : i + self.optionValues[0]] for i in range(0, len(episodes), self.optionValues[0])]


    def _sortShows(self, fileItems: list, episode_order: bool = False, random_order: bool = False) -> tuple:
        """Partition file items into TV shows and movies, with optional deduplication.

        Uses a set of item IDs for O(1) dedup when episode_order=True,
        instead of O(n) 'item not in list' checks.
        """
        try:
            seen_ids = set()
            for item in fileItems:
                type    = item.get('type', '')
                title   = item.get('showtitle')
                item_id = item.get('id') or item.get('file')
                if title and type.startswith(tuple(TV_TYPES)):
                    if episode_order:
                        if item_id and item_id in seen_ids: continue
                        if item_id: seen_ids.add(item_id)
                    self.storedValues[3].setdefault(title, []).append(item)
                else:
                    if episode_order:
                        if item_id and item_id in seen_ids: continue
                        if item_id: seen_ids.add(item_id)
                    self.storedValues[4].append(item)
            if random_order:
                self.storedValues[3] = Globals._randomShuffle(self.storedValues[3])
                self.storedValues[4] = Globals._randomShuffle(self.storedValues[4])
            return dict(self._chunkEpisodes(self.storedValues[3])), self.storedValues[4]
        except Exception as e: self.log("runAction, _sortShows failed! %s"%(e), xbmc.LOGERROR)
        return {}, []


    def _mergeShows(self, shows: dict = {}, movies: list = [], inherited: Any = None) -> list:
        try:
            movie_queue = deque(movies or [])
            show_keys   = list(shows.keys())

            all_chunks  = [chunk for chunks in shows.values() for chunk in chunks]

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


# myId=706 BUILD - pad the guide schedule out to Min_Days (TIME_POST cycles the fileList).
class PadScheduling(BaseRule):
    """USAGE: Pad the guide schedule out to Min_Days.
    PARAMS (options): [0] enabled bool. runAction on CHANNEL_BUILD_TIME_POST
    cycles the fileList until the schedule reaches now + MIN_GUIDEDAYS,
    stamping sequential start/stop times."""


    def __init__(self):
        self.myId               = 706
        self.name               = "Pad Scheduling"
        self.description        = f"Pad EPG with duplicates to meet minimum EPG requirement [{MIN_GUIDEDAYS} days]"
        self.optionLabels       = ["Pad Scheduling"]
        self.optionValues       = [True]
        self.optionDescriptions = [""]
        self.actions            = [RULES_ACTION_CHANNEL_START, RULES_ACTION_CHANNEL_BUILD_TIME_POST,RULES_ACTION_CHANNEL_STOP]
        self.storedValues       = [[],[]]


    def copy(self) -> 'PadScheduling':
        return PadScheduling()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        self.log('[%s] runAction, actionid = %s,'%(citem.get('id'),actionid))
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0]    = inherited.padScheduling
            inherited.padScheduling = self.optionValues[0]
            self.log("runAction, setting padScheduling to %s"%(inherited.padScheduling))

        elif actionid == RULES_ACTION_CHANNEL_BUILD_TIME_POST:
            # Pad scheduling with duplicates to meet minimum guide requirements
            # (Min_Days). Loops the content pool so the guide never runs blank after
            # a few hours. Pre-calculates needed iterations, logs only first/last
            # to reduce log spam.
            if inherited.padScheduling and len(parameter) > 0:
                iters  = cycle(parameter)
                totDur = 0
                start  = parameter[-1]['stop']
                idx    = len(parameter)
                now    = Globals._getGMTstamp()
                target = now + (MIN_GUIDEDAYS * 86400)
                while not inherited.monitor.abortRequested() and start < target:
                    idx += 1
                    item = next(iters).copy()
                    item["idx"]   = idx
                    item['start'] = start
                    item['stop']  = start + item['duration']
                    start = item['stop']
                    totDur += item['duration']
                    parameter.append(item)
                    self.updateProgress(inherited, LANGUAGE(32337))
                self.log("[%s] addScheduling, padded %s items, totDur = %s/%s"%(citem['id'],idx-len(parameter)+1,totDur,MIN_EPG_DURATION))

        elif actionid == RULES_ACTION_CHANNEL_STOP:
            inherited.padScheduling = self.storedValues[0]
            self.log("runAction, restoring padScheduling to %s"%(inherited.padScheduling))

        return parameter


# myId=300 BUILD/PLAYER - resume/pause state engine (cached filelist, resume URL, playlist truncation on playback).
class PauseRule(BaseRule): #PRE-BUILD RULES [300]
    """USAGE: Resume/pause state engine (cached filelist + resume URL).
    PARAMS (options): [0] enabled bool, [1] resume filelist (self-generated,
    leave blank). runAction across 13 actions maintains the cached filelist,
    truncates the resume playlist on PLAYBACK_RESUME, and persists resume
    progress on PLAYER_CHANGE/STOP."""


    def __init__(self):
        self.myId               = 300
        self.name               = LANGUAGE(32230)
        self.description        = LANGUAGE(33228)
        self.optionLabels       = [LANGUAGE(32231),"FileList"]
        self.optionValues       = [True,""]
        self.optionDescriptions = [LANGUAGE(32231),"Self Generated, Please leave blank!"]
        self.actions            = [RULES_ACTION_PLAYBACK_RESUME, RULES_ACTION_PLAYER_START, RULES_ACTION_PLAYER_CHANGE, RULES_ACTION_PLAYER_STOP, RULES_ACTION_CHANNEL_START, RULES_ACTION_CHANNEL_STOP, RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE, RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST, RULES_ACTION_CHANNEL_BUILD_FILELIST_POST, RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN, RULES_ACTION_CHANNEL_BUILD_TIME_PRE, RULES_ACTION_CHANNEL_CITEM, RULES_ACTION_CHANNEL_TEMP_CITEM]
        self.storedValues       = [[],[],False]


    def copy(self) -> 'PauseRule':
        return PauseRule()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        return self.optionValues[optionindex]


    def _getURL(self, id: int) -> str:
        return 'http://%s/filelist/%s'%(Globals.properties.getRemoteHost(),self._getKey(id))


    def _addIDX(self, key: str):
        keys = set(Globals.settings.getCacheSetting(RESUME_INDEX, FileAccess._getMD5(RESUME_INDEX), default={}))
        keys.add(key)
        return Globals.settings.setCacheSetting(RESUME_INDEX, keys, FileAccess._getMD5(RESUME_INDEX), datetime.timedelta(days=84))


    def _delIDX(self, key: str):
        keys = set(Globals.settings.getCacheSetting(RESUME_INDEX, FileAccess._getMD5(RESUME_INDEX), default={}))
        if key in list(keys): keys.pop(key)
        return Globals.settings.setCacheSetting(RESUME_INDEX, keys, FileAccess._getMD5(RESUME_INDEX), datetime.timedelta(days=84))


    def _chkIDX(self):
        keys = set(Globals.settings.getCacheSetting(RESUME_INDEX, FileAccess._getMD5(RESUME_INDEX), default={}))
        valid = {k for k in keys if Globals.settings.getCacheSetting(k, FileAccess._getMD5(k), default={})}
        return Globals.settings.setCacheSetting(RESUME_INDEX, valid, FileAccess._getMD5(RESUME_INDEX), datetime.timedelta(days=84))


    def _getKey(self, id: int) -> str:
        return '%s.json'%(FileAccess._getMD5('%s.%s'%(Globals.properties.getFriendlyName(),id)))


    def _getTotDuration(self, id: int, filelist: list = []) -> float:
        if not hasattr(self, '_jsonrpc'): self._jsonrpc = JSONRPC()
        return self._jsonrpc.getTotDuration(filelist)


    def _buildSchedule(self, citem: dict, filelist: list, builder: Any) -> dict:
        self.log('[%s] _buildSchedule, filelist = %s'%(citem.get('id'),len(filelist)))
        self._builder = builder
        duration = self._getTotDuration(citem.get('id'), filelist)
        updated = self._getResumeData(citem.get('id')).get('updated',{})
        try:    viewed = '%s: %s (%s)'%(LANGUAGE(32250),Globals._epochTime(updated.get('time')).strftime(BACKUP_TIME_FORMAT),updated.get('instance'))
        except Exception: viewed = LANGUAGE(32251)
        return builder.buildCells(citem, duration=duration, entries=1,
                                  info={"title":'%s (%s)'%(citem.get('name'),LANGUAGE(32145)),
                                        "episodetitle":viewed,
                                        "plot":'%s: %s\nSize: %s\nRuntime: ~%s hrs.'%(LANGUAGE(32249),Globals._epochTime(time.time(),tz=False).strftime(BACKUP_TIME_FORMAT),len(filelist),round(duration//60//60)),
                                        "art":{"thumb":LOGO,"poster":LOGO_POSTER,"fanart":LOGO_LANDSCAPE,"landscape":LOGO_LANDSCAPE,"logo":citem.get('logo',LOGO),"icon":citem.get('logo',LOGO)}})

    def _setResume(self, id: int, filelist: list = [], resume: dict = {"idx":0,"position":0.0,"total":0.0,"file":"","updated":{"instance":"","time":-1}}):
        key = self._getKey(id)
        self._addIDX(key)
        self.log("[%s] runAction, _setResume: filelist = %s, resume = %s, key = %s, url = %s"%(id,len(filelist),resume,key,self.optionValues[1]))
        friendly = Globals.properties.getFriendlyName()
        if resume.get('updated',{}).get('instance') == friendly: return Globals.settings.setCacheSetting(key, {'resume':resume,'filelist':filelist}, FileAccess._getMD5(key), datetime.timedelta(days=84))
        elif self.optionValues[1]:                               return self._builder.jsonRPC.requestURL(self.optionValues[1],payload={'uuid':Globals.settings.getMYUUID(),'name':friendly,'payload':{'resume':resume,'filelist':filelist}},
                                                                                                   cache={"cache":Globals.settings.cache, "checksum":ADDON_VERSION, "life": datetime.timedelta(minutes=15)})


    def _getResumeData(self, id: int) -> dict:
        key = self._getKey(id)
        self.log("[%s] runAction, _getResumeData: key = %s, url = %s"%(id,key,self.optionValues[1]))
        if self.optionValues[1]: return self._builder.jsonRPC.requestURL(self.optionValues[1])
        else:                    return Globals.settings.getCacheSetting(key, FileAccess._getMD5(key), default={})


    def _getResume(self, id: int) -> dict:
        return (self._getResumeData(id).get('resume') or {"idx":0,"position":0.0,"total":0.0,"file":"","updated":{"instance":"","time":-1}})


    def _getFilelist(self, id: int) -> list:
        return (self._getResumeData(id).get('filelist') or [])


    def _getPlaylist(self, id: int) -> list:
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


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        self.log('[%s] runAction, actionid = %s,'%(citem.get('id'),actionid))
        if actionid == RULES_ACTION_CHANNEL_START:
            self._chkIDX()
            self.storedValues[0]    = inherited.padScheduling
            self.storedValues[1]    = self._getFilelist(citem.get('id'))
            inherited.padScheduling = False #disable guide padding with duplicates to fill quota.
            self.log("[%s] runAction, setting padScheduling = %s"%(citem.get('id'),inherited.padScheduling))

        elif actionid == RULES_ACTION_CHANNEL_CITEM:
            try:
                parameter["rules"][self.myId]["values"].update({1:self._getURL(parameter.get('id'))})
                self.log("runAction, updated rule values = %s"%( parameter["rules"][self.myId]["values"]), xbmc.LOGERROR)
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
                if inherited.xmltv.clrProgrammes(citem):
                    self.updateProgress(inherited, LANGUAGE(32352))
                    return self._buildSchedule(citem, parameter, inherited)

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

# myId=1100 SERVE - exclude this channel from the served M3U/XMLTV (M3U_FILTER/XMLTV_FILTER).
class ChannelFilter(BaseRule): #SERVE RULES [1100-1199]
    """USAGE: Exclude this channel from the served M3U/XMLTV guide.
    PARAMS (options): [0] enabled bool. runAction removes the channel's station
    (s['id'] == citem['id']) from the list on RULES_ACTION_M3U_FILTER /
    RULES_ACTION_XMLTV_FILTER."""
    """Exclude a channel from the served M3U/XMLTV.

    Runs on both RULES_ACTION_M3U_FILTER and RULES_ACTION_XMLTV_FILTER (the HTTP
    serve path). When enabled, the channel's station is removed from the list fed
    to pvr.iptvsimple, so it no longer appears in the guide. Serves as the
    scaffold for per-channel serve filters - expand runAction to add richer
    filtering as needed.
    """

    def __init__(self):
        self.myId               = 1100
        self.name               = LANGUAGE(32283)
        self.description        = LANGUAGE(33283)
        self.optionLabels       = [LANGUAGE(32284)]
        self.optionValues       = [False]
        self.optionDescriptions = [LANGUAGE(33283)]
        self.actions            = [RULES_ACTION_M3U_FILTER, RULES_ACTION_XMLTV_FILTER]
        self.storedValues       = [[]]


    def copy(self) -> 'ChannelFilter':
        return ChannelFilter()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        if actionid in self.actions and parameter is not None and self.optionValues and self.optionValues[0]:
            ch_id = citem.get('id')
            if ch_id and isinstance(parameter, list):
                before = len(parameter)
                parameter = [s for s in parameter if s.get('id') != ch_id]
                if len(parameter) != before:
                    target = 'M3U' if actionid == RULES_ACTION_M3U_FILTER else 'XMLTV'
                    self.log("[%s] ChannelFilter, excluded from served %s (%d -> %d stations)" % (ch_id, target, before, len(parameter)))
        return parameter

class Dayparting(BaseRule): #BUILD_SOURCE [500-507]
    """USAGE: Use different content sources by time of day.
    PARAMS (options): [0] day path, [1] night path, [2] night start hour,
    [3] night end hour. CHANNEL_START swaps citem['path'] to the day/night
    source by local hour; CHANNEL_STOP restores the original path."""

    def __init__(self):
        self.myId               = 507
        self.name               = LANGUAGE(32285)
        self.description        = LANGUAGE(33285)
        self.optionLabels       = [LANGUAGE(32286),LANGUAGE(32287),LANGUAGE(32288),LANGUAGE(32289)]
        self.optionValues       = ['','',22,6]
        self.optionDescriptions = [LANGUAGE(33285),LANGUAGE(33285),LANGUAGE(33285),LANGUAGE(33285)]
        self.actions            = [RULES_ACTION_CHANNEL_START,RULES_ACTION_CHANNEL_STOP]
        self.storedValues       = [[]]


    def copy(self) -> 'Dayparting':
        return Dayparting()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        if   optionindex in (0,1): self.onActionBrowse(optionindex, type=0, heading=self.optionLabels[optionindex], mask=xbmc.getSupportedMedia('video'))
        elif optionindex in (2,3):
            self.onActionDigitBox(optionindex)
            self.validateDigitBox(optionindex, 0, 23, 22)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        if actionid == RULES_ACTION_CHANNEL_START:
            self.storedValues[0] = citem.get('path', [])
            hour = int(datetime.datetime.now().strftime('%H'))
            ns, ne = int(self.optionValues[2]), int(self.optionValues[3])
            night = (hour >= ns) if ns > ne else (ns <= hour < ne)
            path = self.optionValues[1] if night else self.optionValues[0]
            if path:
                self.updateProgress(inherited, LANGUAGE(32351))
                citem['path'] = [path] if isinstance(path, str) else path
        elif actionid == RULES_ACTION_CHANNEL_STOP:
            if self.storedValues[0]:
                citem['path'] = self.storedValues[0]
        return parameter


class PathKeywordFilter(BaseRule): #BUILD_SELECT [600-699]
    """USAGE: Include or exclude files whose path contains given keywords.
    PARAMS (options): [0] mode select (Include|Exclude), [1] keywords textbox
    (|-separated). FILELIST_PRE filters the flat file list before ordering."""

    def __init__(self):
        self.myId               = 601
        self.name               = LANGUAGE(32290)
        self.description        = LANGUAGE(33290)
        self.optionLabels       = [LANGUAGE(32291),LANGUAGE(32292)]
        self.optionValues       = [0,'']
        self.optionDescriptions = [LANGUAGE(33290),LANGUAGE(33290)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.selectBoxOptions   = [{LANGUAGE(30021):0,LANGUAGE(30184):1}]
        self.storedValues       = [[]]


    def copy(self) -> 'PathKeywordFilter':
        return PathKeywordFilter()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        if   optionindex == 0: self.onActionSelect(optionindex, LANGUAGE(32291))
        elif optionindex == 1: self.onActionTextBox(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        keywords = [k.strip().lower() for k in str(self.optionValues[1]).split('|') if k.strip()]
        if parameter and keywords and isinstance(parameter, list):
            self.updateProgress(inherited, LANGUAGE(32339))
            def _match(item):
                fle = str(item.get('file','')).lower()
                return any(k in fle for k in keywords)
            keep = _match if self.optionValues[0] == 1 else (lambda i: not _match(i))
            parameter = [i for i in parameter if keep(i)]
        return parameter


class AudioLangPreference(BaseRule): #BUILD_SELECT [600-699]
    """USAGE: Prefer files whose name or stream carries a language tag.
    PARAMS (options): [0] audio lang textbox, [1] sub lang textbox (e.g. eng,
    jpn; [ENG], .eng., multi). Defaults to the current Kodi language.
    FILELIST_PRE keeps matching items (by filename tag OR stream language)
    when any match."""


    def __init__(self):
        self.myId               = 602
        self.name               = LANGUAGE(32293)
        self.description        = LANGUAGE(33293)
        self.optionLabels       = [LANGUAGE(32294),LANGUAGE(32295)]
        self.optionValues       = [self._defaultLang(),'']
        self.optionDescriptions = [LANGUAGE(33293),LANGUAGE(33293)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.storedValues       = [[]]


    def copy(self) -> 'AudioLangPreference':
        return AudioLangPreference()


    def getTitle(self) -> str:
        return self.name


    @staticmethod
    def _defaultLang() -> str:
        """Current Kodi language code ('eng', 'deu', ...) as a sensible default."""
        try:
            lang = xbmc.getLanguage(xbmc.ISO_639_2)  # 3-letter ISO code
            if isinstance(lang, str) and re.match(r'^[a-z]{2,3}$', lang.strip(), re.I):
                return lang.strip().lower()
        except Exception:
            pass
        try:
            lang = str(Globals._getLanguage()).replace('_', '-').split('-')[0].lower()
            if re.match(r'^[a-z]{2,3}$', lang):
                return lang
        except Exception:
            pass
        return ''


    @staticmethod
    def _streamMatch(item: dict, lang: str, streamkey: str = 'audio') -> bool:
        """True if any stream of streamkey (audio/subtitle) matches the language."""
        lang = (lang or '').lower()
        if not lang: return False
        want = lang[:3]
        for track in (item.get('streamdetails', {}).get(streamkey) or []):
            sl = str(track.get('language', '') or '').lower()
            if sl and (sl == lang or (want and sl[:3] == want)):
                return True
        return False


    def _matches(self, item: dict, lang: str, streamkey: str) -> bool:
        lang = (lang or '').lower()
        if not lang: return False
        fle = str(item.get('file', '')).lower()
        if any(t in fle for t in (lang, '[%s]' % lang, '.%s.' % lang, 'multi')):
            return True
        return self._streamMatch(item, lang, streamkey)


    def onAction(self, optionindex: int) -> Any:
        self.onActionTextBox(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        if not parameter or not isinstance(parameter, list):
            return parameter
        if not (str(self.optionValues[0] or '').strip() or str(self.optionValues[1] or '').strip()):
            return parameter
        self.updateProgress(inherited, LANGUAGE(32340))
        matches = [i for i in parameter
                   if self._matches(i, self.optionValues[0], 'audio')
                   or self._matches(i, self.optionValues[1], 'subtitle')]
        return matches if matches else parameter


class RatingFilter(BaseRule): #BUILD_SELECT [600-699]
    """USAGE: Skip programmes rated above a threshold or matching a genre.
    PARAMS (options): [0] max MPAA select, [1] genre deny textbox (|-separated).
    FILELIST_PRE drops over-rated / denied-genre items before ordering.
    Item ratings from any system (FSK, BBFC, ...) are interpreted to MPAA
    severity via ratings.rank()."""

    def __init__(self):
        self.myId               = 603
        self.name               = LANGUAGE(32296)
        self.description        = LANGUAGE(33296)
        self.optionLabels       = [LANGUAGE(32297),LANGUAGE(32298)]
        self.optionValues       = [0,'']
        self.optionDescriptions = [LANGUAGE(33296),LANGUAGE(33296)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.selectBoxOptions   = [{'Off':0,'G':1,'PG':2,'PG-13':3,'R':4,'NC-17':5}]
        self.storedValues       = [[]]


    def copy(self) -> 'RatingFilter':
        return RatingFilter()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        if   optionindex == 0: self.onActionSelect(optionindex, LANGUAGE(32297))
        elif optionindex == 1: self.onActionTextBox(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        if not parameter or not isinstance(parameter, list):
            return parameter
        maxrank = int(self.optionValues[0] or 0)
        denied = [g.strip().lower() for g in str(self.optionValues[1]).split('|') if g.strip()]
        if not maxrank and not denied:
            return parameter
        self.updateProgress(inherited, LANGUAGE(32341))
        out = []
        for item in parameter:
            if maxrank:
                if ratings.rank(item.get('mpaa','')) > maxrank:
                    continue
            if denied:
                genres = [str(g).lower() for g in (item.get('genre') or [])]
                if any(g in genres for g in denied):
                    continue
            out.append(item)
        return out


class DurationRangeFilter(BaseRule): #BUILD_SELECT [600-699]
    """USAGE: Keep only programmes within a duration range.
    PARAMS (options): [0] min minutes, [1] max minutes (0 = no limit).
    FILELIST_PRE drops items outside the range before ordering."""

    def __init__(self):
        self.myId               = 604
        self.name               = LANGUAGE(32299)
        self.description        = LANGUAGE(33299)
        self.optionLabels       = [LANGUAGE(32300),LANGUAGE(32301)]
        self.optionValues       = [0,0]
        self.optionDescriptions = [LANGUAGE(33299),LANGUAGE(33299)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.storedValues       = [[]]


    def copy(self) -> 'DurationRangeFilter':
        return DurationRangeFilter()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        self.onActionDigitBox(optionindex)
        self.validateDigitBox(optionindex, 0, 600, 0)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        if not parameter or not isinstance(parameter, list):
            return parameter
        lo = int(self.optionValues[0] or 0) * 60
        hi = int(self.optionValues[1] or 0) * 60
        if not lo and not hi:
            return parameter
        self.updateProgress(inherited, LANGUAGE(32342))
        out = []
        for item in parameter:
            dur = int(item.get('duration') or item.get('runtime') or 0)
            if lo and dur < lo: continue
            if hi and dur > hi: continue
            out.append(item)
        return out


class UnwatchedFirst(BaseRule): #BUILD_SCHEDULE [700-799]
    """USAGE: Play unwatched programmes first.
    PARAMS (options): [0] enabled bool. FILELIST_PRE stable-partitions items
    with playcount==0 to the front, applied after ordering rules."""

    def __init__(self):
        self.myId               = 702
        self.name               = LANGUAGE(32302)
        self.description        = LANGUAGE(33302)
        self.optionLabels       = [LANGUAGE(32303)]
        self.optionValues       = [False]
        self.optionDescriptions = [LANGUAGE(33302)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.storedValues       = [[]]


    def copy(self) -> 'UnwatchedFirst':
        return UnwatchedFirst()


    def getTitle(self) -> str:
        return '%s (%s)'%(self.name,{True:LANGUAGE(30184),False:LANGUAGE(30021)}[self.optionValues[0]])


    def onAction(self, optionindex: int) -> Any:
        self.onActionToggleBool(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        if self.optionValues and self.optionValues[0] and isinstance(parameter, list):
            self.updateProgress(inherited, LANGUAGE(32343))
            unwatched = [i for i in parameter if not (i.get('playcount') or 0)]
            watched   = [i for i in parameter if (i.get('playcount') or 0)]
            parameter = unwatched + watched
        return parameter


class SeriesMarathon(BaseRule): #BUILD_SCHEDULE [700-799]
    """USAGE: Play a limited run of episodes from one show before switching.
    PARAMS (options): [0] max episodes per run select (1-25). FILELIST_PRE
    caps consecutive same-show items by deferring the excess to the end."""

    def __init__(self):
        self.myId               = 703
        self.name               = LANGUAGE(32304)
        self.description        = LANGUAGE(33304)
        self.optionLabels       = [LANGUAGE(32305)]
        self.optionValues       = [0]
        self.optionDescriptions = [LANGUAGE(33304)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.selectBoxOptions   = [list(range(1,26,1))]
        self.storedValues       = [[]]


    def copy(self) -> 'SeriesMarathon':
        return SeriesMarathon()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        self.onActionSelect(optionindex, LANGUAGE(32305))
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        cap = int(self.optionValues[0] or 0)
        if not cap or not isinstance(parameter, list):
            return parameter
        self.updateProgress(inherited, LANGUAGE(32344))
        ordered, deferred = [], []
        cur_show, run = None, 0
        for item in parameter:
            show = item.get('showtitle') or item.get('tvshowid') or ''
            if show == cur_show and show:
                run += 1
                if run > cap:
                    deferred.append(item)
                    continue
            else:
                cur_show, run = show, 1
            ordered.append(item)
        return ordered + deferred


class RecentFirst(BaseRule): #BUILD_SCHEDULE [700-799]
    """USAGE: Pull recently added programmes to the front.
    PARAMS (options): [0] recent days (0-365). FILELIST_PRE partitions items
    whose dateadded is within N days to the front."""

    def __init__(self):
        self.myId               = 704
        self.name               = LANGUAGE(32306)
        self.description        = LANGUAGE(33306)
        self.optionLabels       = [LANGUAGE(32307)]
        self.optionValues       = [0]
        self.optionDescriptions = [LANGUAGE(33306)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.storedValues       = [[]]


    def copy(self) -> 'RecentFirst':
        return RecentFirst()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        self.onActionDigitBox(optionindex)
        self.validateDigitBox(optionindex, 0, 365, 0)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        days = int(self.optionValues[0] or 0)
        if not days or not isinstance(parameter, list):
            return parameter
        self.updateProgress(inherited, LANGUAGE(32345))
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
        recent, rest = [], []
        for item in parameter:
            try:
                added = Globals._strpTime(str(item.get('dateadded','')), '%Y-%m-%d %H:%M:%S')
            except Exception:
                added = None
            (recent if (added and added >= cutoff) else rest).append(item)
        return recent + rest


class GenreWeighting(BaseRule): #BUILD_SCHEDULE [700-799]
    """USAGE: Give matching genres extra airtime.
    PARAMS (options): [0] genre keyword, [1] boost select (1-3x). FILELIST_PRE
    appends extra copies of matching items to increase their presence."""

    def __init__(self):
        self.myId               = 705
        self.name               = LANGUAGE(32308)
        self.description        = LANGUAGE(33308)
        self.optionLabels       = [LANGUAGE(32309),LANGUAGE(32310)]
        self.optionValues       = ['',1]
        self.optionDescriptions = [LANGUAGE(33308),LANGUAGE(33308)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE]
        self.selectBoxOptions   = ["",list(range(1,4,1))]
        self.storedValues       = [[]]


    def copy(self) -> 'GenreWeighting':
        return GenreWeighting()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        if   optionindex == 0: self.onActionTextBox(optionindex)
        elif optionindex == 1: self.onActionSelect(optionindex, LANGUAGE(32310))
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        kw = str(self.optionValues[0]).lower()
        boost = int(self.optionValues[1] or 1)
        if not kw or boost <= 1 or not isinstance(parameter, list):
            return parameter
        self.updateProgress(inherited, LANGUAGE(32346))
        extra = []
        for item in parameter:
            if any(kw in str(g).lower() for g in (item.get('genre') or [])):
                extra.extend([item] * (boost - 1))
        return parameter + extra


class ProgrammeSpacing(BaseRule): #BUILD_SCHEDULE [700-799]
    """USAGE: Insert a bumper at regular intervals.
    PARAMS (options): [0] interval minutes, [1] bumpers folder. TIME_POST re-stamps
    the schedule, inserting a short bumper item every N minutes of content."""

    def __init__(self):
        self.myId               = 707
        self.name               = LANGUAGE(32311)
        self.description        = LANGUAGE(33311)
        self.optionLabels       = [LANGUAGE(32312),LANGUAGE(32313)]
        self.optionValues       = [0,'']
        self.optionDescriptions = [LANGUAGE(33311),LANGUAGE(33311)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_TIME_POST]
        self.selectBoxOptions   = [list(range(0,121,5))]
        self.storedValues       = [[]]


    def copy(self) -> 'ProgrammeSpacing':
        return ProgrammeSpacing()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        if   optionindex == 0: self.onActionSelect(optionindex, LANGUAGE(32312))
        elif optionindex == 1: self.onActionBrowse(optionindex, type=0, heading=self.optionLabels[optionindex], mask=xbmc.getSupportedMedia('video'))
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        interval = int(self.optionValues[0] or 0) * 60
        bumper_dir = self.optionValues[1]
        if not interval or not bumper_dir or not isinstance(parameter, list):
            return parameter
        self.updateProgress(inherited, LANGUAGE(32347))
        # Re-stamp: insert a 20s bumper after every `interval` seconds of content.
        result, elapsed, idx = [], 0, 0
        start = float(parameter[0].get('start', 0)) if parameter and parameter[0].get('start') else 0
        for item in parameter:
            dur = int(item.get('duration') or 0)
            if elapsed and elapsed // interval > (elapsed - dur) // interval and dur:
                result.append({'title': 'Bumper', 'file': bumper_dir, 'duration': 20,
                               'start': start, 'stop': start + 20, 'idx': idx, 'filler': True})
                start += 20
                idx += 1
            item['start'] = start
            item['stop'] = start + dur
            item['idx'] = idx
            start += dur
            elapsed += dur
            idx += 1
            result.append(item)
        return result


class PrimeTimeBlock(BaseRule): #BUILD_SCHEDULE [700-799]
    """USAGE: Reserve a time window for a chosen content type.
    PARAMS (options): [0] start HH:MM, [1] end HH:MM, [2] target keyword (genre/
    title/type). TIME_PRE reorders the queue so matching items land in the window."""

    def __init__(self):
        self.myId               = 708
        self.name               = LANGUAGE(32314)
        self.description        = LANGUAGE(33314)
        self.optionLabels       = [LANGUAGE(32315),LANGUAGE(32316),LANGUAGE(32317)]
        self.optionValues       = ['20:00','23:00','']
        self.optionDescriptions = [LANGUAGE(33314),LANGUAGE(33314),LANGUAGE(33314)]
        self.actions            = [RULES_ACTION_CHANNEL_BUILD_TIME_PRE]
        self.storedValues       = [[]]


    def copy(self) -> 'PrimeTimeBlock':
        return PrimeTimeBlock()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        if   optionindex in (0,1):
            self.onActionTimeBox(optionindex)
            self.validateTimeBox(optionindex)
        elif optionindex == 2:    self.onActionTextBox(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        kw = str(self.optionValues[2]).lower()
        if not kw or not isinstance(parameter, list):
            return parameter
        self.updateProgress(inherited, LANGUAGE(32348))
        # Move matching items to the front so they air as early as possible;
        # slot-exact placement is refined by the schedule machinery later.
        matches = [i for i in parameter if kw in str(i.get('title','')).lower() or
                   any(kw in str(g).lower() for g in (i.get('genre') or []))]
        rest = [i for i in parameter if i not in matches]
        return matches + rest


class GroupHide(BaseRule): #SERVE [1100-1199]
    """USAGE: Hide configured channel groups from the served guide.
    PARAMS (options): [0] groups textbox (|-separated). M3U_FILTER/XMLTV_FILTER
    remove stations whose group list intersects the configured groups."""

    def __init__(self):
        self.myId               = 1101
        self.name               = LANGUAGE(32318)
        self.description        = LANGUAGE(33318)
        self.optionLabels       = [LANGUAGE(32319)]
        self.optionValues       = ['']
        self.optionDescriptions = [LANGUAGE(33318)]
        self.actions            = [RULES_ACTION_M3U_FILTER, RULES_ACTION_XMLTV_FILTER]
        self.storedValues       = [[]]


    def copy(self) -> 'GroupHide':
        return GroupHide()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        self.onActionTextBox(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        groups = [g.strip().lower() for g in str(self.optionValues[0]).split('|') if g.strip()]
        if not groups or not isinstance(parameter, list):
            return parameter
        return [s for s in parameter if not any(str(g).lower() in groups for g in (s.get('group') or []))]


class LogoOverride(BaseRule): #SERVE [1100-1199]
    """USAGE: Override this channel's logo in the served guide.
    PARAMS (options): [0] image path. XMLTV_FILTER sets station['logo']."""

    def __init__(self):
        self.myId               = 1102
        self.name               = LANGUAGE(32320)
        self.description        = LANGUAGE(33320)
        self.optionLabels       = [LANGUAGE(32321)]
        self.optionValues       = ['']
        self.optionDescriptions = [LANGUAGE(33320)]
        self.actions            = [RULES_ACTION_XMLTV_FILTER]
        self.storedValues       = [[]]


    def copy(self) -> 'LogoOverride':
        return LogoOverride()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        self.onActionBrowse(optionindex, type=1, heading=self.optionLabels[optionindex], mask=xbmc.getSupportedMedia('picture'))
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        logo = self.optionValues[0]
        if not logo or not isinstance(parameter, list):
            return parameter
        for s in parameter:
            if s.get('id') == citem.get('id'):
                s['logo'] = logo
        return parameter


class RenumberRule(BaseRule): #SERVE [1100-1199]
    """USAGE: Renumber served channels from a starting value.
    PARAMS (options): [0] start number. M3U_FILTER assigns sequential tvg-chno."""

    def __init__(self):
        self.myId               = 1103
        self.name               = LANGUAGE(32322)
        self.description        = LANGUAGE(33322)
        self.optionLabels       = [LANGUAGE(32323)]
        self.optionValues       = [0]
        self.optionDescriptions = [LANGUAGE(33322)]
        self.actions            = [RULES_ACTION_M3U_FILTER]
        self.storedValues       = [[]]


    def copy(self) -> 'RenumberRule':
        return RenumberRule()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        self.onActionDigitBox(optionindex)
        self.validateDigitBox(optionindex, 0, 999, 1)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        start = int(self.optionValues[0] or 0)
        if not start or not isinstance(parameter, list):
            return parameter
        for idx, s in enumerate(parameter):
            s['number'] = start + idx
        return parameter


class GuideLabel(BaseRule): #SERVE [1100-1199]
    """USAGE: Override this channel's display name in the served guide.
    PARAMS (options): [0] name textbox. XMLTV_FILTER sets station['name']."""

    def __init__(self):
        self.myId               = 1104
        self.name               = LANGUAGE(32324)
        self.description        = LANGUAGE(33324)
        self.optionLabels       = [LANGUAGE(32325)]
        self.optionValues       = ['']
        self.optionDescriptions = [LANGUAGE(33324)]
        self.actions            = [RULES_ACTION_XMLTV_FILTER]
        self.storedValues       = [[]]


    def copy(self) -> 'GuideLabel':
        return GuideLabel()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        self.onActionTextBox(optionindex)
        return self.optionValues[optionindex]


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        label = self.optionValues[0]
        if not label or not isinstance(parameter, list):
            return parameter
        for s in parameter:
            if s.get('id') == citem.get('id'):
                s['name'] = label
        return parameter


class ExternalFeed(BaseRule): #FEED [1200-1299]
    """USAGE: Pull content from a remote JSON/M3U feed into the channel.
    PARAMS (options): [0] URL, [1] refresh interval minutes, [2] headers.
    REQUEST_FILELIST_PRE fetches (cached for the interval) and returns items;
    POST merges/dedupes. JSON schema: {"items":[{"file","title","duration"}]}."""

    _CACHE_KEY = 'rules.externalfeed.%s'

    def __init__(self):
        self.myId               = 1200
        self.name               = LANGUAGE(32326)
        self.description        = LANGUAGE(33326)
        self.optionLabels       = [LANGUAGE(32327),LANGUAGE(32328),LANGUAGE(32329)]
        self.optionValues       = ['',60,'']
        self.optionDescriptions = [LANGUAGE(33326),LANGUAGE(33326),LANGUAGE(33326)]
        self.actions            = [RULES_ACTION_CHANNEL_REQUEST_FILELIST_PRE, RULES_ACTION_CHANNEL_REQUEST_FILELIST_POST]
        self.storedValues       = [[]]


    def copy(self) -> 'ExternalFeed':
        return ExternalFeed()


    def getTitle(self) -> str:
        return self.name


    def onAction(self, optionindex: int) -> Any:
        if   optionindex in (0,2):
            self.onActionTextBox(optionindex)
            if optionindex == 0: self.validateTextBox(optionindex, 2000)
        elif optionindex == 1:
            self.onActionDigitBox(optionindex)
            self.validateDigitBox(optionindex, 1, 1440, 60)
        return self.optionValues[optionindex]


    def _fetch(self, citem: dict) -> list:
        url = str(self.optionValues[0]).strip()
        interval = int(self.optionValues[1] or 60)
        if not url:
            return []
        cid = self._CACHE_KEY % (citem.get('id',''))
        now = time.time()
        try:
            cached = Globals.settings.getCacheSetting(cid, default={}) or {}
            if cached.get('ts') and now - cached.get('ts', 0) < interval:
                return cached.get('items', [])
        except Exception:
            cached = {}
        try:
            import urllib.request as _urlreq
            data = None
            try:
                data = _urlreq.urlopen(url, timeout=30).read()
            except Exception:
                data = None
            if not data: return cached.get('items', [])
            items = []
            text = data.decode('utf-8','replace')
            if text.lstrip().startswith('{'):
                import json as _json
                try:
                    payload = _json.loads(text)
                    for it in (payload.get('items') or []):
                        if it.get('file'):
                            items.append({'file': it['file'], 'title': it.get('title', ''),
                                          'duration': int(it.get('duration') or 0), 'citem': citem})
                except Exception: pass
            else:
                for line in text.splitlines():
                    if line.startswith('#EXTINF:'):
                        dur = 0
                        try: dur = int(line.split(':',1)[1].split(',',1)[0])
                        except Exception: pass
                    elif line.strip() and not line.startswith('#'):
                        items.append({'file': line.strip(), 'title': '', 'duration': dur, 'citem': citem})
            try:  # best-effort cache write — never discard fetched items on failure
                Globals.settings.setCacheSetting(cid, {'ts': now, 'items': items}, life=-1)
            except Exception: pass
            return items
        except Exception as e:
            self.log("ExternalFeed, fetch failed: %s"%e, xbmc.LOGDEBUG)
            return cached.get('items', [])


    def runAction(self, actionid: str, citem: dict, parameter: Any, inherited: Any) -> Any:
        if actionid == RULES_ACTION_CHANNEL_REQUEST_FILELIST_PRE:
            items = self._fetch(citem)
            return items or parameter
        elif actionid == RULES_ACTION_CHANNEL_REQUEST_FILELIST_POST:
            if isinstance(parameter, list):
                seen = set()
                out = []
                for i in parameter:
                    key = i.get('file')
                    if key and key not in seen:
                        seen.add(key); out.append(i)
                return out
        return parameter