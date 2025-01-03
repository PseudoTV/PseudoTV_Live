  # Copyright (C) 2024 Lunatixz


# This file is part of PseudoTV Live.

# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
# -*- coding: utf-8 -*-

from globals    import *
from cache      import Cache
from channels   import Channels
from jsonrpc    import JSONRPC
from rules      import RulesList
from resources  import Resources
from xsp        import XSP
from m3u        import M3U
from xmltvs     import XMLTVS
from infotagger.listitem import ListItemInfoTag

# Actions
ACTION_MOVE_LEFT     = 1
ACTION_MOVE_RIGHT    = 2
ACTION_MOVE_UP       = 3
ACTION_MOVE_DOWN     = 4
ACTION_SELECT_ITEM   = 7
ACTION_INVALID       = 999
ACTION_SHOW_INFO     = [11,24,401]
ACTION_PREVIOUS_MENU = [92, 10,110,521] #+ [9, 92, 216, 247, 257, 275, 61467, 61448]
     
class Manager(xbmcgui.WindowXMLDialog):
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        with BUILTIN.busy_dialog():
            self.server         = {}
            self.lockAutotune   = True
            self.madeChanges    = False
            self.lastActionTime = time.time()
            self.cntrlStates    = {}
            self.showingList    = True
            self.startChannel   = kwargs.get('channel',-1)
            
            self.cache          = SETTINGS.cache
            self.channels       = Channels()
            self.jsonRPC        = JSONRPC()
            self.resources      = Resources(self.jsonRPC)
            self.rule           = RulesList()

            self.newChannel     = self.channels.getTemplate()
            self.eChannels      = self.__loadChannels(SETTINGS.getSetting('Default_Channels'))
            if self.eChannels is None: self.closeManager()
            else:
                self.channelList = self.channels.sortChannels(self.createChannelList(self.buildArray(), self.eChannels))
                self.newChannels = self.channelList.copy()
                
                if self.startChannel == -1:            self.startChannel = self.getFirstAvailChannel()
                if self.startChannel <= CHANNEL_LIMIT: self.focusIndex   = (self.startChannel - 1) #Convert from Channel number to array index
                else:                                  self.focusIndex   = self.findChannelIDXbyNum(self.startChannel)
                self.log('Manager, startChannel = %s, focusIndex = %s'%(self.startChannel, self.focusIndex))
                
        try:
            if kwargs.get('start',True): self.doModal()
        except Exception as e: 
            self.log('Manager failed! %s'%(e), xbmc.LOGERROR)
            self.closeManager()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def __loadChannels(self, name=''):
        self.log('__loadChannels, name = %s'%(name))
        with BUILTIN.busy_dialog():
            from multiroom  import Multiroom
            channels = self.channels.getChannels()
            servers  = Multiroom().getDiscovery()
            enabled  = SETTINGS.getSettingList('Select_server')
            friendly = SETTINGS.getFriendlyName()
            
        if name == LANGUAGE(30022):#Auto
            if   len(channels) > 0: return channels
            elif len(enabled) > 0:
                for name in enabled:
                    if servers.get(name,{}).get('online',False):
                        self.server = servers.get(name,{})
                        return self.server.get('channels',[])
            return self.__loadChannels('Ask')
        elif name == 'Ask':
            def __build(idx, server):
                return LISTITEMS.buildMenuListItem(server.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],{True:'Online',False:'Offline'}[server.get('online',False)]),server.get('host'),len(server.get('channels',[]))),icon=DUMMY_ICON.format(text=str(idx+1)))
      
            lizlst = [__build(idx+1, server) for idx, server in enumerate(list(servers.values())) if server.get('online',False)]
            lizlst.insert(0,LISTITEMS.buildMenuListItem(friendly,'%s - %s: Channels (%s)'%('[B]Local[/B]',PROPERTIES.getRemoteHost(),len(channels)),icon=DUMMY_ICON.format(text=str(1))))
            select = DIALOG.selectDialog(lizlst, LANGUAGE(30173), None, True, SELECT_DELAY, False)
            if not select is None: return self.__loadChannels(lizlst[select].getLabel())
            else: return
        elif name == friendly: return channels
        elif name:
            self.server = servers.get(name,{})
            return self.server.get('channels',[])
        return channels
    
        
    def onInit(self):
        try:
            self.focusItems    = dict()
            self.spinner       = self.getControl(4)
            self.chanList      = self.getControl(5)
            self.itemList      = self.getControl(6)
            self.ruleList      = self.getControl(7)
            self.right_button1 = self.getControl(9001)
            self.right_button2 = self.getControl(9002)
            self.right_button3 = self.getControl(9003)
            self.right_button4 = self.getControl(9004)
            self.fillChanList(self.newChannels,focus=self.focusIndex) #all changes made to self.newChannels before final save to self.channellist
        except Exception as e: 
            log("onInit, failed! %s"%(e), xbmc.LOGERROR)
            self.closeManager()
    
        
    def getFirstAvailChannel(self):
        for channel in self.channelList:
            if not channel.get('id'): return channel.get('number')
        return 1
        
        
    @cacheit(json_data=True)
    def buildArray(self):
        self.log('buildArray') # Create blank array of citem templates. 
        def _create(idx):
            newChannel = self.newChannel.copy()
            newChannel['number'] = idx + 1
            return newChannel
        return poolit(_create)(list(range(CHANNEL_LIMIT)))
  
        
    def createChannelList(self, channelArray, channelList):
        self.log('createChannelList') # Fill blank array with citems from channels.json
        def _update(item):
            try:    channelArray[item["number"]-1].update(item) #CUSTOM
            except: channelArray.append(item)                   #AUTOTUNE
            
        checksum  = getMD5(dumpJSON(channelList))
        cacheName = 'createChannelList.%s'%(checksum)
        cacheResponse = self.cache.get(cacheName, checksum=checksum, json_data=True)
        if not cacheResponse:
            poolit(_update)(channelList)
            cacheResponse = self.cache.set(cacheName, channelArray, checksum=checksum, json_data=True)
        return cacheResponse


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def newStation(self, citem: dict={}):
        if citem.get('id') is None: return False
        else: return M3U().findStation(citem)[0] is None


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def hasProgrammes(self, citem: dict={}):
        if citem.get('id') is None: return False
        else: return not XMLTVS().findChannel(citem)[0] is None


    def buildListItem(self, label: str="", label2: str="", icon: str="", paths: list=[], items: dict={}):
        if not icon:  icon  = (items.get('citem',{}).get('logo') or COLOR_LOGO)
        if not paths: paths = (items.get('citem',{}).get("path") or [])
        return LISTITEMS.buildMenuListItem(label, label2, icon, url='|'.join(paths), props=items)


    def fillChanList(self, channelList, reset=False, focus=None):
        self.log('fillChanList, focus = %s'%(focus))
        def __buildItem(citem):
            isPredefined  = citem["number"] > CHANNEL_LIMIT
            isFavorite    = citem.get('favorite',False)
            isRadio       = citem.get('radio',False)
            isLocked      = isPredefined #todo parse channel lock rule
            isNew         = False#self.newStation(citem)
            hasProgram    = True#self.hasProgrammes(citem)
            channelColor  = COLOR_UNAVAILABLE_CHANNEL
            labelColor    = COLOR_UNAVAILABLE_CHANNEL
            
            if citem.get("path"):
                if isPredefined: channelColor = COLOR_LOCKED_CHANNEL
                else:
                    labelColor = COLOR_AVAILABLE_CHANNEL
                    if   isNew:          channelColor = COLOR_NEW_CHANNEL
                    elif not hasProgram: channelColor = COLOR_WARNING_CHANNEL
                    elif isLocked:       channelColor = COLOR_LOCKED_CHANNEL
                    elif isFavorite:     channelColor = COLOR_FAVORITE_CHANNEL
                    elif isRadio:        channelColor = COLOR_RADIO_CHANNEL
                    else:                channelColor = COLOR_AVAILABLE_CHANNEL
            return self.buildListItem('[COLOR=%s][B]%s|[/COLOR][/B]'%(channelColor,citem["number"]),'[COLOR=%s]%s[/COLOR]'%(labelColor,citem.get("name",'')),items={'citem':citem,'description':LANGUAGE(32169)%('%s on %s'%(citem["number"],self.server.get('name','local')))})
                
        ## Fill chanList listitem for display. *reset draws new control list. *focus list index for channel position.
        self.togglechanList(True,reset=reset)
        with self.toggleSpinner(self.chanList):
            listitems = poolit(__buildItem)(channelList)
            self.chanList.addItems(listitems)
            if focus is None: self.chanList.selectItem(self.setFocusPOS(listitems))
            else:             self.chanList.selectItem(focus)
            self.setFocus(self.chanList)


    @contextmanager
    def toggleSpinner(self, ctrl, state=None):
        if state is None:
            self.setVisibility(self.spinner,True)
            try: yield
            finally: self.setVisibility(self.spinner,False)
        else: self.setVisibility(self.spinner,state)
        # getSpinControl() #todo when avail.
        # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__control__spin.html
        # ctrl.setPageControlVisible(state)


    def togglechanList(self, state, focus=-1, reset=False):
        if focus < 0: focus = 0
        self.log('togglechanList, state = %s, focus = %s, reset = %s'%(state,focus,reset))
        if state: # channellist
            self.setVisibility(self.ruleList,False)
            self.setVisibility(self.itemList,False)
            self.setVisibility(self.chanList,True)
            
            if reset: 
                self.chanList.reset()
                xbmc.sleep(100)
            self.chanList.selectItem(focus)
            self.setFocus(self.chanList)
            
            if self.madeChanges:
                self.setLabels(self.right_button1,LANGUAGE(32059))#Save
                self.setLabels(self.right_button2,LANGUAGE(32060))#Cancel
                self.setLabels(self.right_button3,LANGUAGE(32136))#Move
                self.setLabels(self.right_button4,LANGUAGE(32061))#Delete
            else:
                self.setLabels(self.right_button1,LANGUAGE(32062))#Close
                self.setLabels(self.right_button2,'')
                self.setLabels(self.right_button3,LANGUAGE(32136))#Move
                self.setLabels(self.right_button4,LANGUAGE(32061))#Delete
                
            self.setFocus(self.right_button1)  
            self.setEnableCondition(self.right_button3,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Path) + Integer.IsLessOrEqual(Container(5).ListItem(Container(5).Position).Property(chnum),CHANNEL_LIMIT)]')
            self.setEnableCondition(self.right_button4,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Path) + Integer.IsLessOrEqual(Container(5).ListItem(Container(5).Position).Property(chnum),CHANNEL_LIMIT)]')
        else: # channelitems
            self.setVisibility(self.ruleList,False)
            self.setVisibility(self.chanList,False)
            self.setVisibility(self.itemList,True)
            self.itemList.reset()
            xbmc.sleep(100)
            self.itemList.selectItem(focus)
            self.setFocus(self.itemList)
            self.setLabels(self.right_button1,LANGUAGE(32063))#OK
            self.setLabels(self.right_button2,LANGUAGE(32060))#Cancel
            self.setLabels(self.right_button3,'')
            self.setLabels(self.right_button4,LANGUAGE(32061))#Delete
            self.setEnableCondition(self.right_button4,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Path)]')
        
        
    def toggleruleList(self, state, focus=0, reset=False):
        self.log('toggleruleList, state = %s, focus = %s'%(state,focus))
        if self.isVisible(self.chanList): return DIALOG.notificationDialog(LANGUAGE(32000))
        elif state: # rulelist
            self.setVisibility(self.itemList,False)
            self.setVisibility(self.ruleList,True)
            if reset: 
                self.ruleList.reset()
                xbmc.sleep(100)
            self.ruleList.selectItem(focus)
            self.setFocus(self.ruleList)
        else: # channelitems
            self.setVisibility(self.ruleList,False)
            self.setVisibility(self.itemList,True)
            self.itemList.reset()
            xbmc.sleep(100)
            self.itemList.selectItem(focus)
            self.setFocus(self.itemList)
        

    def setFocusPOS(self, listitems, chnum=None, ignore=True):
        for idx, listitem in enumerate(listitems):
            chnumber = int(cleanLabel(listitem.getLabel()).strip('|'))
            if  ignore and chnumber > CHANNEL_LIMIT: continue
            elif chnum is not None and chnum == chnumber: return idx
            elif chnum is None and cleanLabel(listitem.getLabel2()): return idx
        return 0
        
        
    def buildChannelItem(self, citem: dict={}, focuskey: str='path'):
        self.log('buildChannelItem, id = %s, focuskey = %s'%(citem.get('id'),focuskey))
        def __buildItem(key):
            key   = key.lower()
            value = citem.get(key,' ')
            if   key in ["number","type","logo","id","catchup"]: return # keys to ignore, internal use only.
            elif isinstance(value,(list,dict)): 
                if   key == "group" : value = ('|'.join(sorted(set(value))) or LANGUAGE(30127))
                elif key == "path"  : value = '|'.join(value)
                elif key == "rules" : value = '|'.join([rule.name for key, rule in list(self.rule.loadRules([citem]).get(citem['id'],{}).items())])#todo load rule names
            elif not isinstance(value,str): value = str(value)
            elif not value: value = ' '
            return self.buildListItem(LABEL.get(key,' '),value,items={'key':key,'value':value,'citem':citem,'description':DESC.get(key,''),'colorDiffuse':self.getLogoColor(citem)})

        if not self.isVisible(self.ruleList):
            self.togglechanList(False)
            with self.toggleSpinner(self.itemList):
                LABEL = {'name'    : LANGUAGE(32092),
                         'path'    : LANGUAGE(32093),
                         'group'   : LANGUAGE(32094),
                         'rules'   : LANGUAGE(32095),
                         'radio'   : LANGUAGE(32091),
                         'favorite': LANGUAGE(32090)}
                          
                DESC = {'name'    : LANGUAGE(32085),
                        'path'    : LANGUAGE(32086),
                        'group'   : LANGUAGE(32087),
                        'rules'   : LANGUAGE(32088),
                        'radio'   : LANGUAGE(32084),
                        'favorite': LANGUAGE(32083)}
                          
            listitems = poolit(__buildItem)(list(self.newChannel.keys()))
            self.itemList.addItems(listitems)
            self.itemList.selectItem([idx for idx, liz in enumerate(listitems) if liz.getProperty('key')== focuskey][0])
            self.setFocus(self.itemList)


    def itemInput(self, channelListItem):
        key   = channelListItem.getProperty('key')
        value = channelListItem.getProperty('value')
        citem = loadJSON(channelListItem.getProperty('citem'))
        self.log('itemInput, In value = %s, key = %s\ncitem = %s'%(value,key,citem))
        
        KEY_INPUT = {"name"     : {'func':self.getName    ,'kwargs':{'name'  :value}},
                     "path"     : {'func':self.getPaths   ,'kwargs':{'paths' :value.split('|')}},
                     "group"    : {'func':self.getGroups  ,'kwargs':{'groups':value.split('|')}},
                     "rules"    : {'func':self.getRules   ,'kwargs':{'rules' :self.rule.loadRules([citem],incRez=False).get(citem['id'],{})}},
                     "radio"    : {'func':self.getBool    ,'kwargs':{'state' :value}},
                     "favorite" : {'func':self.getBool    ,'kwargs':{'state' :value}}}
              
        action = KEY_INPUT.get(key) 
        retval, citem = action['func'](citem, *action.get('args',()),**action.get('kwargs',{}))
        retval, citem = self.validateInputs(key,retval,citem)
        if not retval is None:
            self.madeChanges = True
            if key in list(self.newChannel.keys()): citem[key] = retval
        self.log('itemInput, Out value = %s, key = %s\ncitem = %s'%(value,key,citem))
        return citem
   
   
    def getLogoColor(self, citem):
        self.log('getLogoColor, id = %s'%(citem.get('id',-1)))
        if  (citem.get('logo') and citem.get('name')) is None: return 'FFFFFFFF'
        elif citem.get('rules',{}).get("1"):
            if (self.getRuleAbbr(citem,1,4) or self.resources.isMono(citem['logo'])):
                return self.getRuleAbbr(citem,1,3)
        return SETTINGS.getSetting('ChannelBug_Color')
        
   
    def getRuleAbbr(self, citem, myId, optionindex):
        value = citem.get('rules',{}).get(str(myId),{}).get('values',{}).get(str(optionindex))
        self.log('getRuleAbbr, id = %s, myId = %s, optionindex = %s, optionvalue = %s'%(citem.get('id',-1),myId,optionindex,value))
        return value
                    
           
    def getName(self, citem: dict={}, name: str=''):
        return DIALOG.inputDialog(message=LANGUAGE(32079),default=name), citem
   

    def getPaths(self, citem: dict={}, paths: list=[]):
        select  = -1
        epaths  = paths.copy()
        pathLST = list([_f for _f in paths if _f])
        lastOPT = None
        while not MONITOR().abortRequested() and not select is None:
            with self.toggleSpinner(self.itemList):
                npath   = None
                lizLST  = [self.buildListItem('%s|'%(idx+1),path,paths=[path],icon=DUMMY_ICON.format(text=str(idx+1)),items={'citem':citem,'idx':idx+1}) for idx, path in enumerate(pathLST) if path]
                lizLST.insert(0,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32100)),LANGUAGE(33113),icon=ICON,items={'key':'add','citem':citem,'idx':0}))
                if len(pathLST) > 0 and epaths != pathLST: lizLST.insert(1,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32101)),LANGUAGE(33114),icon=ICON,items={'key':'save','citem':citem}))
                
            select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32086), preselect=lastOPT, multi=False)
            if not select is None:
                key, path = lizLST[select].getProperty('key'), lizLST[select].getPath()
                try:    lastOPT = int(lizLST[select].getProperty('idx'))
                except: lastOPT = None
                if key == 'add': 
                    with self.toggleSpinner(self.itemList):
                        retval = DIALOG.browseSources(heading=LANGUAGE(32080), exclude=[21], monitor=True)
                        if not retval is None:
                            npath, citem = self.validatePath(retval,citem)
                            if npath: pathLST.append(npath)
                elif key == 'save': 
                    self.madeChanges = True
                    paths = pathLST
                    break
                elif path in pathLST:
                    retval = DIALOG.yesnoDialog(LANGUAGE(32102), customlabel=LANGUAGE(32103))
                    if retval in [1,2]: pathLST.pop(pathLST.index(path))
                    if retval == 2:
                        with self.toggleSpinner(self.itemList):
                            npath, citem = self.validatePath(DIALOG.browseSources(heading=LANGUAGE(32080), default=path, monitor=True, exclude=[21]), citem)
                            pathLST.append(npath)
        self.log('getPaths, paths = %s'%(paths))
        return paths, citem
           
           
    def getGroups(self, citem: dict={}, groups: list=[]):
        groups  = list([_f for _f in groups if _f])
        ngroups = sorted([_f for _f in set(SETTINGS.getSetting('User_Groups').split('|') + GROUP_TYPES + groups) if _f])
        ngroups.insert(0, '-%s'%(LANGUAGE(30064)))
        selects = DIALOG.selectDialog(ngroups,header=LANGUAGE(32081),preselect=findItemsInLST(ngroups,groups),useDetails=False)
        if 0 in selects:
            SETTINGS.setSetting('User_Groups',DIALOG.inputDialog(LANGUAGE(32044), default=SETTINGS.getSetting('User_Groups')))
            return self.getGroups(citem, groups)
        elif len(ngroups) > 0: groups = [ngroups[idx] for idx in selects]
        if not groups:         groups = [LANGUAGE(30127)]
        self.log('getGroups, groups = %s'%(groups))
        return groups, citem
    
    
    def getBool(self, citem: dict={}, state: str='True'):
        state = not bool(state)
        self.log('getBool, state = %s'%(state))
        return state, citem


    def getRules(self, citem: dict={}, rules: dict={}):
        if citem.get('id') is None or len(citem.get('path',[])) == 0: DIALOG.notificationDialog(LANGUAGE(32071))
        else:            
            select  = -1
            erules  = rules.copy()
            ruleLST = rules.copy()
            lastIDX = None
            lastXID = None
            while not MONITOR().abortRequested() and not select is None:
                with self.toggleSpinner(self.itemList):
                    nrule  = None
                    crules = self.rule.loadRules([citem],append=True,incRez=False).get(citem['id'],{}) #all rule instances w/ channel rules
                    arules = [rule for key, rule in list(crules.items()) if not ruleLST.get(key)] #all unused rule instances
                    lizLST = [self.buildListItem(rule.name,rule.getTitle(),icon=DUMMY_ICON.format(text=str(rule.myId)),items={'myId':rule.myId,'citem':citem,'idx':list(ruleLST.keys()).index(key)+1}) for key, rule in list(ruleLST.items()) if rule.myId]
                    lizLST.insert(0,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32173)),LANGUAGE(33173),icon=ICON,items={'key':'add' ,'citem':citem,'idx':0}))
                    if len(ruleLST) > 0 and erules != ruleLST: lizLST.insert(1,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32174)),LANGUAGE(33174),icon=ICON,items={'key':'save','citem':citem}))
                            
                select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32095), preselect=lastIDX, multi=False)
                if not select is None:
                    key, myId = lizLST[select].getProperty('key'), int(lizLST[select].getProperty('myId') or '-1')
                    try:    lastIDX = int(lizLST[select].getProperty('idx'))
                    except: lastIDX = None
                    if key == 'add':
                        with self.toggleSpinner(self.itemList):
                            lizLST = [self.buildListItem(rule.name,rule.description,icon=DUMMY_ICON.format(text=str(rule.myId)),items={'idx':idx,'myId':rule.myId,'citem':citem}) for idx, rule in enumerate(arules) if rule.myId]
                        select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32072), preselect=lastXID, multi=False)
                        try:    lastXID = int(lizLST[select].getProperty('idx'))
                        except: lastXID = -1
                        nrule, citem = self.getRule(citem, arules[lastXID])
                        if not nrule is None: ruleLST.update({str(nrule.myId):nrule})
                    elif key == 'save':
                        self.madeChanges = True
                        rules = ruleLST
                        break
                    elif ruleLST.get(str(myId)):
                        retval = DIALOG.yesnoDialog(LANGUAGE(32175), customlabel=LANGUAGE(32176))
                        if retval in [1,2]: ruleLST.pop(str(myId))
                        if retval == 2: 
                            nrule, citem = self.getRule(citem, crules.get(str(myId),{}))
                            if not nrule is None: ruleLST.update({str(nrule.myId):nrule})
                    # elif not ruleLST.get(str(myId)):
                        # nrule, citem = self.getRule(citem, crules.get(str(myId),{}))
                        # if not nrule is None:  ruleLST.update({str(nrule.myId):nrule})
                        
            self.log('getRules, rules = %s'%(len(rules)))
            return self.rule.dumpRules(rules), citem
        

    def getRule(self, citem={}, rule={}):
        self.log('getRule, name = %s'%(rule.name))
        if rule.exclude and True in list(set([True for p in citem.get('path',[]) if p.endswith('.xsp')])):
           return DIALOG.notificationDialog(LANGUAGE(32178))
        else:
            select = -1
            while not MONITOR().abortRequested() and not select is None:
                with self.toggleSpinner(self.itemList):
                    lizLST = [self.buildListItem('%s = %s'%(rule.optionLabels[idx],rule.optionValues[idx]),rule.optionDescriptions[idx],icon=DUMMY_ICON.format(text=str(idx+1)),items={'value':optionValue,'idx':idx,'myId':rule.myId,'citem':citem}) for idx, optionValue in enumerate(rule.optionValues)]
                select = DIALOG.selectDialog(lizLST, header='%s %s - %s'%(LANGUAGE(32176),rule.myId,rule.name), multi=False)
                if not select is None:
                    try:
                        rule.onAction(int(lizLST[select].getProperty('idx') or "0"))
                    except Exception as e:
                        self.log("getRule, onAction failed! %s"%(e), xbmc.LOGERROR)
                        DIALOG.okDialog(LANGUAGE(32000))
            return rule, citem
        
        
    def setID(self, citem: dict={}) -> dict:
        if not citem.get('id') and citem.get('name') and citem.get('path') and citem.get('number'): 
            citem['id'] = getChannelID(citem['name'], citem['path'], citem['number'])
            self.log('setID, id = %s'%(citem['id']))
        return citem
    
       
    def setName(self, path, citem: dict={}) -> dict:
        if citem.get('name'): return citem
        elif path.strip('/').endswith(('.xml','.xsp')):
            citem['name'] = XSP().getName(path)
        elif path.startswith(('plugin://','upnp://','videodb://','musicdb://','library://','special://')): 
            citem['name'] = self.getMontiorList().getLabel()
        else:
            citem['name'] = os.path.basename(os.path.dirname(path)).strip('/')
        self.log('setName, id = %s, name = %s'%(citem['id'],citem['name']))
        return citem


    def setLogo(self, name=None, citem={}, force=False):
        if name is None: name = citem.get('name','')
        if name:
            logo = citem.get('logo')
            if force: logo = ''
            if not logo or logo in [LOGO,COLOR_LOGO,ICON]:
                with BUILTIN.busy_dialog():
                    citem['logo'] = self.resources.getLogo(name, citem.get('type',"Custom"))
                self.log('setLogo, id = %s, logo = %s'%(citem.get('id'),citem.get('logo')))
        return citem
        
          
    def validateInputs(self, key, value, citem):
        self.log('validateInputs, key = %s'%(key))
        KEY_VALIDATION = {'name'    :self.validateLabel,
                          'path'    :self.validatePaths,
                          'group'   :self.validateGroups,
                          'rules'   :self.validateRules}.get(key,None)
        try: retval, citem = KEY_VALIDATION(value,citem)
        except Exception as e: 
            log("validateInputs, no action! %s"%(e))
            return value, citem
            
        if retval is None:
            DIALOG.notificationDialog(LANGUAGE(32077)%key.title()) 
            return None , citem
        elif not retval:
            DIALOG.notificationDialog(LANGUAGE(32171)%key.title())
            return None , citem
        else:
            self.log('validateInputs, value = %s'%(retval))
            return retval, self.setID(citem)
        
        
    def validateLabel(self, label, citem):
        def _chkName(name):
            for channel in self.eChannels:
                if channel.get('name','').lower() == name.lower(): return True
            return False
            
        if label and (len(label) > 1 or len(label) < 128): 
            label = validString(label)
            if _chkName(label): return '', citem
            else:
                self.log('validateLabel, label = %s'%(label))
                return label, self.setLogo(label, citem, force=True)
        return None, citem


    def validatePaths(self, paths, citem):
        if len(paths) == 0: return None, citem
        else:
            citem = self.setName(paths[0], citem)
            self.log('validatePaths, paths = %s'%paths)
            return paths, self.setLogo(citem.get('name'),citem)

        
    def validatePath(self, path, citem, spinner=True):
        def _seek(item, citem):
            monitor = MONITOR()
            player  = PLAYER()
            file    = item.get('file')
            dur     = item.get('duration')
            if player.isPlaying() or not file.startswith(tuple(VFS_TYPES)) and not file.endswith('.strm'): return True
            # todo test seek for support disable via adv. rule if fails.
            # todo set seeklock rule if seek == False
            liz = xbmcgui.ListItem('Seek Test', path=file)
            liz.setProperty('startoffset', str(int(dur//8)))
            infoTag = ListItemInfoTag(liz, 'video')
            infoTag.set_resume_point({'ResumeTime':int(dur/4),'TotalTime':int(dur/4)})
        
            getTime  = 0
            waitTime = 30
            threadit(BUILTIN.executebuiltin)('PlayMedia(%s)'%(file))
            while not monitor.abortRequested():
                waitTime -= 1
                self.log('validatePath _seek, waiting (%s) to seek %s'%(waitTime, item.get('file')))
                if monitor.waitForAbort(1.0) or waitTime < 1: break
                elif not player.isPlaying(): continue
                elif ((int(player.getTime()) > getTime) or BUILTIN.getInfoBool('SeekEnabled','Player')):
                    player.stop()
                    return True
            player.stop()
            return False
            
        def _vfs(path, citem):
            if isRadio({'path':[path]}) or isMixed({'path':[path]}): return True
            else:
                valid = False
                media = 'music' if isRadio({'path':[path]}) else 'video'
                dia   = DIALOG.progressDialog(message='%s %s, %s..\n%s'%(LANGUAGE(32098),'Path',LANGUAGE(32099),path))
                with BUILTIN.busy_dialog():
                    items = self.jsonRPC.walkFileDirectory(path, media, depth=5, retItem=True)
                
                for idx, dir in enumerate(items):
                    if MONITOR().waitForAbort(.0001): break
                    else:
                        item = random.choice(items.get(dir,[]))
                        dia  = DIALOG.progressDialog(int((idx*100)//len(items)),control=dia, message='%s %s...\n%s\n%s'%(LANGUAGE(32098),'Path',dir,item.get('file','')))
                        item.update({'duration':self.jsonRPC.getDuration(item.get('file'), item, accurate=bool(SETTINGS.getSettingInt('Duration_Type')))})
                        if item.get('duration',0) == 0: continue
                        dia = DIALOG.progressDialog(int((idx*100)//len(items)),control=dia, message='%s %s...\n%s\n%s'%(LANGUAGE(32098),'Seeking',dir,item.get('file','')))
                        if _seek(item, citem):
                            self.log('validatePath _vfs, found playable and seek-able file %s'%(item.get('file')))
                            valid = True
                            break
                DIALOG.progressDialog(100,control=dia)
                return valid

        if not path: return None, citem
        else:
            if spinner:
                with self.toggleSpinner(self.itemList):
                    valid = _vfs(path, citem)
            else: valid = _vfs(path, citem)
            if not valid:
                DIALOG.notificationDialog(LANGUAGE(32030))
                return None, citem
            else:
                citem = self.setName(path, citem)
                self.log('validatePath, path = %s'%path)
                return path, self.setLogo(citem.get('name'),citem)


    def validateGroups(self, groups, citem):
        return groups, citem #todo check values
        
        
    def validateRules(self, rules, citem):
        return rules, citem #todo check values
        

    def validateChannels(self, channelList):
        def _validate(citem):
            if citem.get('name') and citem.get('path'):
                if citem['number'] <= CHANNEL_LIMIT: citem['type'] = "Custom"
                return self.setID(citem)
            
        channelList = self.channels.sortChannels([_f for _f in [_validate(channel) for channel in channelList] if _f])
        self.log('validateChannels, channelList = %s'%(len(channelList)))
        return channelList
              

    def openEditor(self, path):
        self.log('openEditor, path = %s'%(path))
        if '|' in path: 
            path = path.split('|')
            path = path[0]#prompt user to select:
        media = 'video' if 'video' in path else 'music'
        if   '.xsp' in path: return self.openEditor(path,media)
        elif '.xml' in path: return self.openNode(path,media)
       

    def viewChannel(self, citem): #todo preview uncached filelist for visual breakdown of channel content.
        self.log('viewChannel, id = %s'%(citem['id']))
        # [self.buildFileList(citem, file, 'video', roundupDIV(self.limit,len(citem['path'])), self.sort, self.limits) for file in citem['path']]


    def getMontiorList(self):
        self.log('getMontiorList')
        try:
            itemLST = [self.buildListItem(cleanLabel(value).title(),icon=ICON) for info in DIALOG.getInfoMonitor() for key, value in list(info.items()) if value not in ['','..'] and key not in ['path','logo']]
            if len(itemLST) == 0: raise Exception()
            itemSEL = DIALOG.selectDialog(itemLST,LANGUAGE(32078)%('Name'),useDetails=True,multi=False)
            if itemSEL is not None: return itemLST[itemSEL]
            else: raise Exception()
        except: return xbmcgui.ListItem(LANGUAGE(32079))


    def saveChannelItems(self, citem: dict={}):
        self.log('saveChannelItems, id = %s'%(citem.get('id')))
        idx = citem['number'] - 1
        self.newChannels[idx] = citem
        self.fillChanList(self.newChannels,reset=True,focus=idx)
        
    
    def saveChanges(self):
        self.log("saveChanges")
        if DIALOG.yesnoDialog("Changes Detected, Do you want to save?"): return self.saveChannels() 
        else: self.closeManager()


    def saveChannels(self):
        self.log("saveChannels")
        if   not self.madeChanges: return
        elif not DIALOG.yesnoDialog(LANGUAGE(32076)): return
        with self.toggleSpinner(self.chanList):
            if self.server:
                payload = {'uuid':SETTINGS.getMYUUID(),'name':SETTINGS.getFriendlyName(),'channels':self.validateChannels(self.newChannels)}
                requestURL('http://%s/%s'%(self.server.get('host'),CHANNELFLE), data=dumpJSON(payload), header=HEADER, json_data=True)
                #todo write tmp file if post fails, add to que to repost when url online.
            else: self.channels.setChannels(self.validateChannels(self.newChannels))
        self.closeManager()
            
        
    def clearChannel(self, item, prompt=True):
        self.log('clearChannel, channelPOS = %s'%(item['number'] - 1))
        if prompt and not DIALOG.yesnoDialog(LANGUAGE(32073)): return item
        self.madeChanges = True
        nitem = self.newChannel.copy()
        nitem['number'] = item['number'] #preserve channel number
        self.saveChannelItems(nitem)
        return nitem


    def moveChannel(self, citem, channelPOS):
        self.log('moveChannel, channelPOS = %s'%(channelPOS))
        retval = DIALOG.inputDialog(LANGUAGE(32137), key=xbmcgui.INPUT_NUMERIC, opt=citem['number'])
        if retval:
            retval = int(retval)
            if (retval > 0 and retval < CHANNEL_LIMIT) and retval != channelPOS + 1:
                if DIALOG.yesnoDialog('%s %s %s from [B]%s[/B] to [B]%s[/B]?'%(LANGUAGE(32136),citem['name'],LANGUAGE(32023),citem['number'],retval)):
                    if retval in [channel.get('number') for channel in self.newChannels if channel.get('path')]:
                        DIALOG.notificationDialog(LANGUAGE(32138))
                    else:
                        self.madeChanges = True
                        nitem = self.newChannel.copy()
                        nitem['number'] = channelPOS + 1
                        self.newChannels[channelPOS] = nitem
                        citem['number'] = retval
                        self.saveChannelItems(citem)
        return citem, channelPOS


    def switchLogo(self, channelData, channelPOS):
        def cleanLogo(chlogo):
            #todo convert resource from vfs to fs
            # return chlogo.replace('resource://','special://home/addons/')
            # resource = path.replace('/resources','').replace(,)
            # resource://resource.images.studios.white/Amazon.png
            return chlogo
        
        def select(chname):
            def _build(logo):
                return self.buildListItem('%s| %s'%(logos.index(logo)+1, chname), unquoteString(logo), logo, [logo])
                
            DIALOG.notificationDialog(LANGUAGE(32140))
            with self.toggleSpinner(self.itemList):
                logos = self.resources.selectLogo(chname)
                listitems = poolit(_build)(logos)
            select = DIALOG.selectDialog(listitems,'%s (%s)'%(LANGUAGE(32066).split('[CR]')[1],chname),useDetails=True,multi=False)
            if select is not None:
                return listitems[select].getPath()

        def browse(chname):
            with self.toggleSpinner(self.itemList):
                retval = DIALOG.browseSources(type=1,heading='%s (%s)'%(LANGUAGE(32066).split('[CR]')[0],chname), default=channelData.get('icon',''), shares='files', mask=xbmc.getSupportedMedia('picture'), exclude=[12,13,14,15,16,17,21,22])
            if FileAccess.copy(cleanLogo(retval), os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')): 
                if FileAccess.exists(os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')): 
                    return os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')
            return retval
            
        def match(chname):
            with self.toggleSpinner(self.itemList):
                return self.resources.getLogo(chname)

        if self.isVisible(self.ruleList): return
        chname = channelData.get('name')
        if not chname: return DIALOG.notificationDialog(LANGUAGE(32065))
            
        chlogo = None
        retval = DIALOG.yesnoDialog(LANGUAGE(32066), heading     ='%s - %s'%(ADDON_NAME,LANGUAGE(32172)),
                                                     nolabel     = LANGUAGE(32067), #Select
                                                     yeslabel    = LANGUAGE(32068), #Browse
                                                     customlabel = LANGUAGE(30022)) #Auto
                                             
        if   retval == 0: chlogo = select(chname)
        elif retval == 1: chlogo = browse(chname)
        elif retval == 2: chlogo = match(chname)
        else: DIALOG.notificationDialog(LANGUAGE(32070))
        self.log('switchLogo, chname = %s, chlogo = %s'%(chname,chlogo))
        
        if chlogo:
            self.madeChanges = True
            channelData['logo'] = chlogo
            DIALOG.notificationDialog(LANGUAGE(32139))
            if self.isVisible(self.itemList): self.buildChannelItem(channelData)
            else:
                self.newChannels[channelPOS] = channelData
                self.fillChanList(self.newChannels,reset=True,focus=channelPOS)


    def isVisible(self, cntrl):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            state = cntrl.isVisible()
        except: state = self.cntrlStates.get(cntrl.getId(),False)
        self.log('isVisible, cntrl = %s, state = %s'%(cntrl.getId(),state))
        return state
        
        
    def setVisibility(self, cntrl, state):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setVisible(state)
            self.cntrlStates[cntrl.getId()] = state
            self.log('setVisibility, cntrl = ' + str(cntrl.getId()) + ', state = ' + str(state))
        except Exception as e: self.log("setVisibility, failed! %s"%(e), xbmc.LOGERROR)
    
    
    def setLabels(self, cntrl, label='', label2=''):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setLabel(str(label), str(label2))
            self.setVisibility(cntrl,(len(label) > 0 or len(label2) > 0))
        except Exception as e: self.log("setLabels, failed! %s"%(e), xbmc.LOGERROR)
    
    
    def getLabels(self, cntrl):
        try:
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            return cntrl.getLabel(), cntrl.getLabel2()
        except Exception as e: return '',''
        
        
    def setImages(self, cntrl, image='NA.png'):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setImage(image)
        except Exception as e: self.log("setImages, failed! %s"%(e), xbmc.LOGERROR)
 
 
    def setEnableCondition(self, cntrl, condition):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setEnableCondition(condition)
        except Exception as e: self.log("setEnableCondition, failed! %s"%(e), xbmc.LOGERROR)


    def closeManager(self):
        self.log('closeManager')
        if self.madeChanges: PROPERTIES.forceUpdateTime('chkChannels')
        self.close()


    def getFocusItems(self, controlId=None):
        if controlId in [5,6,7,10,9001,9002,9003,9004]:
            self.focusItems = dict()
            label, label2 = self.getLabels(controlId)
            if self.isVisible(self.chanList):
                spos  = self.chanList.getSelectedPosition()
                sitem = self.chanList.getSelectedItem()
            elif self.isVisible(self.itemList):
                spos  = self.itemList.getSelectedPosition()
                sitem = self.itemList.getSelectedItem()
            elif self.isVisible(self.ruleList):
                spos  = self.ruleList.getSelectedPosition()
                sitem = self.ruleList.getSelectedItem()
            else:
                spos  = -1
                sitem = xbmcgui.ListItem()
            if sitem:
                try:    chlnum = int(cleanLabel(sitem.getLabel()))
                except: chlnum = None
                citem = loadJSON(sitem.getProperty('citem'))
                chnum = (citem.get('number') or chlnum or (spos+1))
                self.focusItems.update({'label':label,'label2':label2,'number':chnum,'position':spos,'item':sitem,'citem':citem})
                self.log('getFocusItems, controlId = %s, focusItems = %s'%(controlId,self.focusItems))
        return self.focusItems

    
    def onFocus(self, controlId):
        self.log('onFocus: controlId = %s'%(controlId))

        
    def onAction(self, act):
        actionId   = act.getId()   
        lastaction = time.time() - self.lastActionTime
        # during certain times we just want to discard all input
        if lastaction < .5 and actionId not in ACTION_PREVIOUS_MENU: action = ACTION_INVALID
        else:
            if actionId in ACTION_PREVIOUS_MENU:
                self.log('onAction: actionId = %s'%(actionId))
                if   xbmcgui.getCurrentWindowDialogId() == "13001": BUILTIN.executebuiltin("Action(Back)")
                elif self.isVisible(self.ruleList): self.toggleruleList(False)
                elif self.isVisible(self.itemList): self.togglechanList(True,focus=self.getFocusItems().get('position'))
                elif self.isVisible(self.chanList):
                    if self.madeChanges: self.saveChanges()
                    else:                self.closeManager()
            
        
    def onClick(self, controlId):
        focusItems = self.getFocusItems(controlId)
        self.log('onClick: controlId = %s\nitems = %s'%(controlId,focusItems))
        if   controlId == 0: self.closeManager()
        #item list
        elif controlId == 5: self.buildChannelItem(focusItems.get('citem'))
        elif controlId == 6:
            if self.lockAutotune and focusItems.get('number',0) > CHANNEL_LIMIT: DIALOG.notificationDialog(LANGUAGE(32064))
            else: self.buildChannelItem(self.itemInput(focusItems.get('item')),focusItems.get('item').getProperty('key'))
        # elif controlId == 7: self.buildRuleItem(*self.ruleInput(focusItems.get('item')),focusItems.get('item').getProperty('key'))
        #logo button
        elif controlId == 10: 
            if self.lockAutotune and focusItems.get('number',0) > CHANNEL_LIMIT: DIALOG.notificationDialog(LANGUAGE(32064))
            else: self.switchLogo(focusItems.get('citem'),focusItems.get('position'))
        #side buttons
        elif controlId == 9001: #dynamic button
            if   focusItems.get('label') == LANGUAGE(32062): self.closeManager()#Close
            elif focusItems.get('label') == LANGUAGE(32059): self.saveChannels()#Save 
            elif focusItems.get('label') == LANGUAGE(32063):#OK
                if   self.isVisible(self.itemList) and self.madeChanges: self.saveChannelItems(focusItems.get('citem'))
                # elif self.isVisible(self.ruleList):                      self.toggleruleList(False)
                else:                                                    self.togglechanList(True,focus=focusItems.get('position'))
        elif controlId == 9002: #dynamic button
            if focusItems.get('label') == LANGUAGE(32060):#Cancel
                if   self.isVisible(self.chanList) and self.madeChanges: self.saveChanges()
                # elif self.isVisible(self.ruleList):                      self.toggleruleList(False)
                else:                                                    self.togglechanList(True,focus=focusItems.get('position'))
        elif controlId == 9003: #dynamic button
            if focusItems.get('label') == LANGUAGE(32136):self.moveChannel(focusItems.get('citem'),focusItems.get('position'))#Move 
        elif controlId == 9004: #dynamic button
            if focusItems.get('label') == LANGUAGE(32061): self.clearChannel(focusItems.get('citem'))#Delete
            
            
    def findChannelIDXbyNum(self, chnum, channels=[]):
        if not channels: channels = self.channelList
        for idx, channel in enumerate(channels):
            if channel.get('number') == chnum: return idx
        return 1