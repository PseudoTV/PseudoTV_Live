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
    
        def __get1stChannel(channelList):
            for channel in channelList:
                if not channel.get('id'): return channel.get('number')
            return 1
            
            
        def __findChannel(chnum, retitem=False, channels=[]):
            for idx, channel in enumerate(channels):
                if channel.get('number') == (chnum or 1): 
                    if retitem: return channel
                    else:       return idx
            
        with BUILTIN.busy_dialog(), PROPERTIES.interruptActivity():
            self.server         = {}
            self.lockAutotune   = True
            self.madeChanges    = False
            self.lastActionTime = time.time()
            self.cntrlStates    = {}
            self.showingList    = True
            self.startChannel   = kwargs.get('channel',-1)
            self.openChannel    = kwargs.get('open')
            
            self.cache          = SETTINGS.cache
            self.channels       = Channels()
            self.rule           = RulesList()
            self.jsonRPC        = JSONRPC()
            self.resource       = Resources(self.jsonRPC)

            self.host           = PROPERTIES.getRemoteHost()
            self.friendly       = SETTINGS.getFriendlyName()
            self.newChannel     = self.channels.getTemplate()
            self.eChannels      = self.loadChannels(SETTINGS.getSetting('Default_Channels'))
            
            if self.eChannels is None: self.closeManager()
            else:
                self.channelList = self.channels.sortChannels(self.createChannelList(self.buildArray(), self.eChannels))
                self.newChannels = self.channelList.copy()

                if self.startChannel == -1:            self.startChannel = __get1stChannel(self.channelList)
                if self.startChannel <= CHANNEL_LIMIT: self.focusIndex   = (self.startChannel - 1) #Convert from Channel number to array index
                else:                                  self.focusIndex   = __findChannel(self.startChannel,channels=self.channelList)
                if self.openChannel: self.openChannel = self.channelList[self.focusIndex]
                self.log('Manager, startChannel = %s, focusIndex = %s, openChannel = %s'%(self.startChannel, self.focusIndex, self.openChannel))

            try:
                if kwargs.get('start',True): self.doModal()
            except Exception as e: 
                self.log('Manager failed! %s'%(e), xbmc.LOGERROR)
                self.closeManager()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onInit(self):
        try:
            self.focusItems    = dict()
            self.spinner       = self.getControl(4)
            self.chanList      = self.getControl(5)
            self.itemList      = self.getControl(6)
            self.right_button1 = self.getControl(9001)
            self.right_button2 = self.getControl(9002)
            self.right_button3 = self.getControl(9003)
            self.right_button4 = self.getControl(9004)
            self.fillChanList(self.newChannels,focus=self.focusIndex,channel=self.openChannel)
        except Exception as e: 
            log("onInit, failed! %s"%(e), xbmc.LOGERROR)
            self.closeManager()


    def getServers(self):
        from multiroom  import Multiroom
        return Multiroom().getDiscovery()
    

    def loadChannels(self, name=''):
        self.log('loadChannels, name = %s'%(name))
        channels = self.channels.getChannels()
        if   name == self.friendly: return channels
        elif name == LANGUAGE(30022):#Auto
            if len(channels) > 0: return channels
            else:                 return self.loadChannels('Ask')
        elif name == 'Ask':
            def __buildItem(server, servers):
                if server.get('online',False):
                    return LISTITEMS.buildMenuListItem(server.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],{True:'Online',False:'Offline'}[server.get('online',False)]),server.get('host'),len(server.get('channels',[]))),icon=DUMMY_ICON.format(text=str(servers.index(server)+1)))

            servers = self.getServers()
            lizlst = poolit(__buildItem)(*(list(servers.values()),list(servers.values())))
            lizlst.insert(0,LISTITEMS.buildMenuListItem(self.friendly,'%s - %s: Channels (%s)'%('[B]Local[/B]',self.host,len(channels)),icon=DUMMY_ICON.format(text=str(1))))
            select = DIALOG.selectDialog(lizlst, LANGUAGE(30173), None, True, SELECT_DELAY, False)
            if not select is None: return self.loadChannels(lizlst[select].getLabel())
            else: return
        elif name:
            self.server = self.getServers().get(name,{})
            return self.server.get('channels',[])
        return channels

        
    @cacheit(json_data=True)
    def buildArray(self):
        self.log('buildArray') # Create blank array of citem templates. 
        def __create(idx):
            newChannel = self.newChannel.copy()
            newChannel['number'] = idx + 1
            return newChannel
        return poolit(__create)(list(range(CHANNEL_LIMIT)))
  
        
    def createChannelList(self, channelArray, channelList):
        self.log('createChannelList') # Fill blank array with citems from channels.json
        def __update(item):
            try:    channelArray[item["number"]-1].update(item) #CUSTOM
            except: channelArray.append(item)                   #AUTOTUNE
            
        checksum  = getMD5(dumpJSON(channelList))
        cacheName = 'createChannelList.%s'%(checksum)
        cacheResponse = self.cache.get(cacheName, checksum=checksum, json_data=True)
        if not cacheResponse:
            poolit(__update)(channelList)
            cacheResponse = self.cache.set(cacheName, channelArray, checksum=checksum, json_data=True)
        return cacheResponse


    def buildListItem(self, label: str="", label2: str="", icon: str="", paths: list=[], items: dict={}):
        if not icon:  icon  = (items.get('citem',{}).get('logo') or COLOR_LOGO)
        if not paths: paths = (items.get('citem',{}).get("path") or [])
        return LISTITEMS.buildMenuListItem(label, label2, icon, url='|'.join(paths), props=items)


    def fillChanList(self, channelList, refresh=False, focus=None, channel=None):
        self.log('fillChanList, focus = %s, channel = %s'%(focus,channel))
        def __buildItem(citem):
            isPredefined  = citem["number"] > CHANNEL_LIMIT
            isFavorite    = citem.get('favorite',False)
            isRadio       = citem.get('radio',False)
            isLocked      = isPredefined #todo parse channel lock rule
            channelColor  = COLOR_UNAVAILABLE_CHANNEL
            labelColor    = COLOR_UNAVAILABLE_CHANNEL
            
            if citem.get("path"):
                if isPredefined: channelColor = COLOR_LOCKED_CHANNEL
                else:
                    labelColor = COLOR_AVAILABLE_CHANNEL
                    if   isLocked:       channelColor = COLOR_LOCKED_CHANNEL
                    elif isFavorite:     channelColor = COLOR_FAVORITE_CHANNEL
                    elif isRadio:        channelColor = COLOR_RADIO_CHANNEL
                    else:                channelColor = COLOR_AVAILABLE_CHANNEL
            return self.buildListItem('[COLOR=%s][B]%s|[/COLOR][/B]'%(channelColor,citem["number"]),'[COLOR=%s]%s[/COLOR]'%(labelColor,citem.get("name",'')),items={'citem':citem,'chname':citem["name"],'chnum':'%i'%(citem["number"]),'radio':citem.get('radio',False),'description':LANGUAGE(32169)%(citem["number"],self.server.get('name',self.friendly))})
                
        self.togglechanList(reset=refresh)
        with self.toggleSpinner():
            listitems = poolit(__buildItem)(channelList)
            self.chanList.addItems(listitems)
            if focus is None: self.chanList.selectItem(self.setFocusPOS(listitems))
            else:             self.chanList.selectItem(focus)
            self.setFocus(self.chanList)
            if channel: self.buildChannelItem(channel)


    @contextmanager
    def toggleSpinner(self, state=None):
        if state is None:
            self.setVisibility(self.spinner,True)
            try: yield
            finally: self.setVisibility(self.spinner,False)
        else: self.setVisibility(self.spinner,state)


    def togglechanList(self, state=True, focus=0, reset=False):
        self.log('togglechanList, state = %s, focus = %s, reset = %s'%(state,focus,reset))
        with self.toggleSpinner():
            if state: # channellist
                if reset: 
                    self.setVisibility(self.chanList,False)
                    self.chanList.reset()
                    
                self.setVisibility(self.itemList,False)
                self.setVisibility(self.chanList,True)
                self.setFocus(self.chanList)
                self.chanList.selectItem(focus)
                
                if self.madeChanges:
                    self.setLabels(self.right_button1,LANGUAGE(32059))#Save
                    self.setLabels(self.right_button2,LANGUAGE(32060))#Cancel
                    self.setLabels(self.right_button3,LANGUAGE(32136))#Move
                    self.setLabels(self.right_button4,LANGUAGE(32061))#Delete
                    self.setEnableCondition(self.right_button1,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chnum))]')
                    self.setEnableCondition(self.right_button2,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chnum))]')
                else:
                    self.setLabels(self.right_button1,LANGUAGE(32062))#Close
                    self.setLabels(self.right_button2,LANGUAGE(32235))#Preview
                    self.setLabels(self.right_button3,LANGUAGE(32136))#Move
                    self.setLabels(self.right_button4,LANGUAGE(32061))#Delete
                    self.setEnableCondition(self.right_button1,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chnum))]')
                    self.setEnableCondition(self.right_button2,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Path) + String.IsEqual(Container(5).ListItem(Container(5).Position).Property(radio),False)]')
                    
                self.setFocus(self.right_button1)
                self.setEnableCondition(self.right_button3,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Path)]')# + Integer.IsLessOrEqual(Container(5).ListItem(Container(5).Position).Property(chnum),CHANNEL_LIMIT)]')
                self.setEnableCondition(self.right_button4,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Path)]')# + Integer.IsLessOrEqual(Container(5).ListItem(Container(5).Position).Property(chnum),CHANNEL_LIMIT)]')
            else: # channelitems
                self.itemList.reset()
                self.setVisibility(self.chanList,False)
                self.setVisibility(self.itemList,True)
                self.itemList.selectItem(focus)
                self.setFocus(self.itemList)
                
                if self.madeChanges:
                    self.setLabels(self.right_button1,LANGUAGE(32240))#Confirm
                    self.setLabels(self.right_button2,LANGUAGE(32060))#Cancel
                    self.setEnableCondition(self.right_button1,'[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Label) + !String.IsEmpty(Container(6).ListItem(Container(6).Position).Path)]')
                    self.setEnableCondition(self.right_button2,'[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Property(chnum))]')
                else:
                    self.setLabels(self.right_button1,LANGUAGE(32062))#Close
                    self.setLabels(self.right_button2,'')
                    self.setEnableCondition(self.right_button1,'[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Property(chnum))]')
                    
                self.setLabels(self.right_button3,LANGUAGE(32235))#Preview
                self.setLabels(self.right_button4,LANGUAGE(32239))#Clear
                self.setEnableCondition(self.right_button3,'[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Path) + String.IsEqual(Container(6).ListItem(Container(6).Position).Property(radio),False)]')
                self.setEnableCondition(self.right_button4,'[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Path)]')
            
        
    def setFocusPOS(self, listitems, chnum=None, ignore=True):
        for idx, listitem in enumerate(listitems):
            chnumber = int(cleanLabel(listitem.getLabel()).strip('|'))
            if  ignore and chnumber > CHANNEL_LIMIT: continue
            elif chnum is not None and chnum == chnumber: return idx
            elif chnum is None and cleanLabel(listitem.getLabel2()): return idx
        return 0
        
           
    def getRuleAbbr(self, citem, myId, optionindex):
        value = citem.get('rules',{}).get(str(myId),{}).get('values',{}).get(str(optionindex))
        self.log('getRuleAbbr, id = %s, myId = %s, optionindex = %s, optionvalue = %s'%(citem.get('id',-1),myId,optionindex,value))
        return value
                    

    def getLogoColor(self, citem):
        self.log('getLogoColor, id = %s'%(citem.get('id',-1)))
        if  (citem.get('logo') and citem.get('name')) is None: return 'FFFFFFFF'
        elif citem.get('rules',{}).get("1"):
            if (self.getRuleAbbr(citem,1,4) or self.resource.isMono(citem['logo'])):
                return self.getRuleAbbr(citem,1,3)
        return SETTINGS.getSetting('ChannelBug_Color')
        
        
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
            return self.buildListItem(LABEL.get(key,' '),value,items={'key':key,'value':value,'citem':citem,'chname':citem["name"],'chnum':'%i'%(citem["number"]),'radio':citem.get('radio',False),'description':DESC.get(key,''),'colorDiffuse':self.getLogoColor(citem)})

        self.togglechanList(False)
        with self.toggleSpinner():
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


    def itemInput(self, channelListItem=xbmcgui.ListItem()):
        def __getName(citem: dict={}, name: str=''):
            return DIALOG.inputDialog(message=LANGUAGE(32079),default=name), citem
       
        def __getPath(citem: dict={}, paths: list=[]):
            return self.getPaths(citem, paths)
        
        def __getGroups(citem: dict={}, groups: list=[]):
            groups  = list([_f for _f in groups if _f])
            ngroups = sorted([_f for _f in set(SETTINGS.getSetting('User_Groups').split('|') + GROUP_TYPES + groups) if _f])
            ngroups.insert(0, '-%s'%(LANGUAGE(30064)))
            selects = DIALOG.selectDialog(ngroups,header=LANGUAGE(32081),preselect=findItemsInLST(ngroups,groups),useDetails=False)
            if 0 in selects:
                SETTINGS.setSetting('User_Groups',DIALOG.inputDialog(LANGUAGE(32044), default=SETTINGS.getSetting('User_Groups')))
                return __getGroups(citem, groups)
            elif len(ngroups) > 0: groups = [ngroups[idx] for idx in selects]
            if not groups:         groups = [LANGUAGE(30127)]
            return groups, citem
        
        def __getRule(citem: dict={}, rules: dict={}):
            return self.getRules(citem, rules)
            
        def __getBool(citem: dict={}, state: bool=False):
            return not bool(state), citem

        key   = channelListItem.getProperty('key')
        value = channelListItem.getProperty('value')
        citem = loadJSON(channelListItem.getProperty('citem'))
        self.log('itemInput, In value = %s, key = %s\ncitem = %s'%(value,key,citem))
        
        KEY_INPUT = {"name"     : {'func':__getName  , 'kwargs':{'citem':citem, 'name'  :citem.get('name','')}},
                     "path"     : {'func':__getPath  , 'kwargs':{'citem':citem, 'paths' :citem.get('path',[])}},
                     "group"    : {'func':__getGroups, 'kwargs':{'citem':citem, 'groups':citem.get('group',[])}},
                     "rules"    : {'func':__getRule  , 'kwargs':{'citem':citem, 'rules' :self.rule.loadRules([citem],incRez=False).get(citem['id'],{})}},
                     "radio"    : {'func':__getBool  , 'kwargs':{'citem':citem, 'state' :citem.get('radio',False)}},
                     "favorite" : {'func':__getBool  , 'kwargs':{'citem':citem, 'state' :citem.get('favorite',False)}}}
              
        action = KEY_INPUT.get(key) 
        retval, citem = action['func'](*action.get('args',()),**action.get('kwargs',{}))
        retval, citem = self.validateInputs(key,retval,citem)
        if not retval is None:
            self.madeChanges = True
            if key in list(self.newChannel.keys()): citem[key] = retval
            self.log('itemInput, Out value = %s, key = %s\ncitem = %s'%(retval,key,citem))
        return citem
   
   
    def getPaths(self, citem: dict={}, paths: list=[]):
        select  = -1
        epaths  = paths.copy()
        pathLST = list([_f for _f in paths if _f])
        lastOPT = None
        
        if not citem.get('radio',False) and isRadio({'path':paths}): citem['radio'] = True #set radio on music paths
        if citem.get('radio',False): excLST = [10,12,21,22]
        else:                        excLST = [11,13,21]
        
        while not MONITOR().abortRequested() and not select is None:
            with self.toggleSpinner():
                npath   = None
                lizLST  = [self.buildListItem('%s|'%(idx+1),path,paths=[path],icon=DUMMY_ICON.format(text=str(idx+1)),items={'citem':citem,'idx':idx+1}) for idx, path in enumerate(pathLST) if path]
                lizLST.insert(0,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32100)),LANGUAGE(33113),icon=ICON,items={'key':'add','citem':citem,'idx':0}))
                if len(pathLST) > 0 and epaths != pathLST: lizLST.insert(1,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32101)),LANGUAGE(33114),icon=ICON,items={'key':'save','citem':citem}))
                
            select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32086), preselect=lastOPT, multi=False)
            with self.toggleSpinner():
                if not select is None:
                    key, path = lizLST[select].getProperty('key'), lizLST[select].getPath()
                    try:    lastOPT = int(lizLST[select].getProperty('idx'))
                    except: lastOPT = None
                    if key == 'add': 
                        retval = DIALOG.browseSources(heading=LANGUAGE(32080), exclude=excLST, monitor=True)
                        if not retval is None:
                            npath, citem = self.validatePaths(retval,citem)
                            if npath: pathLST.append(npath)
                    elif key == 'save': 
                        self.madeChanges = True
                        paths = pathLST
                        break
                    elif path in pathLST:
                        retval = DIALOG.yesnoDialog(LANGUAGE(32102), customlabel=LANGUAGE(32103))
                        if retval in [1,2]: pathLST.pop(pathLST.index(path))
                        if retval == 2:
                            with self.toggleSpinner():
                                npath, citem = self.validatePaths(DIALOG.browseSources(heading=LANGUAGE(32080), default=path, monitor=True, exclude=excLST), citem)
                                pathLST.append(npath)
        self.log('getPaths, paths = %s'%(paths))
        return paths, citem


    def getRules(self, citem: dict={}, rules: dict={}):
        if citem.get('id') is None or len(citem.get('path',[])) == 0: DIALOG.notificationDialog(LANGUAGE(32071))
        else:            
            select  = -1
            erules  = rules.copy()
            ruleLST = rules.copy()
            lastIDX = None
            lastXID = None
            while not MONITOR().abortRequested() and not select is None:
                with self.toggleSpinner():
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
                        with self.toggleSpinner():
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
        if rule.exclude and True in list(set([True for p in citem.get('path',[]) if p.endswith('.xsp')])): return DIALOG.notificationDialog(LANGUAGE(32178))
        else:
            select = -1
            while not MONITOR().abortRequested() and not select is None:
                with self.toggleSpinner():
                    lizLST = [self.buildListItem('%s = %s'%(rule.optionLabels[idx],rule.optionValues[idx]),rule.optionDescriptions[idx],icon=DUMMY_ICON.format(text=str(idx+1)),items={'value':optionValue,'idx':idx,'myId':rule.myId,'citem':citem}) for idx, optionValue in enumerate(rule.optionValues)]
                select = DIALOG.selectDialog(lizLST, header='%s %s - %s'%(LANGUAGE(32176),rule.myId,rule.name), multi=False)
                if not select is None:
                    try: rule.onAction(int(lizLST[select].getProperty('idx') or "0"))
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
        with self.toggleSpinner():
            if citem.get('name'): return citem
            elif path.strip('/').endswith(('.xml','.xsp')):            citem['name'] = XSP().getName(path)
            elif path.startswith(tuple(DB_TYPES+WEB_TYPES+VFS_TYPES)): citem['name'] = self.getMontiorList().getLabel()
            else:                                                      citem['name'] = os.path.basename(os.path.dirname(path)).strip('/')
            self.log('setName, id = %s, name = %s'%(citem['id'],citem['name']))
            return citem


    def setLogo(self, name=None, citem={}, force=False):
        name = (name or citem.get('name'))
        if name:
            if force: logo = ''
            else:     logo = citem.get('logo')
            if not logo or logo in [LOGO,COLOR_LOGO,ICON]:
                with self.toggleSpinner():
                    citem['logo'] = self.resource.getLogo(name, citem.get('type',"Custom"))
        self.log('setLogo, id = %s, logo = %s, force = %s'%(citem.get('id'),citem.get('logo'),force))
        return citem
       
       
    def validateInputs(self, key, value, citem):
        self.log('validateInputs, key = %s, value = %s'%(key,value))
        def __validateName(name, citem):
            if name and (len(name) > 1 or len(name) < 128): 
                citem['name'] = validString(name)
                self.log('__validateName, name = %s'%(citem['name']))
                return citem['name'], self.setLogo(name, citem, force=True)
            return None, citem

        def __validatePath(paths, citem):
            if len(paths) > 0: 
                name, citem = __validateName(citem.get('name',''),self.setName(paths[0], citem))
                self.log('__validatePath, name = %s, paths = %s'%(name,paths))
                return paths, citem
            return None, citem

        def __validateGroup(groups, citem):
            return groups, citem #todo check values
                   
        def __validateRules(rules, citem):
            return rules, citem #todo check values
            
        def __validateBool(state, citem):
            if isinstance(state,bool): return state, citem
            return None, citem
        
        KEY_VALIDATION = {'name'    :__validateName,
                          'path'    :__validatePath,
                          'group'   :__validateGroup,
                          'rules'   :__validateRules,
                          'radio'   :__validateBool,
                          'favorite':__validateBool}.get(key,None)
        try:
            with toggleSpinner():
                retval, citem = KEY_VALIDATION(value,citem)
                if retval is None:
                    DIALOG.notificationDialog(LANGUAGE(32077)%key.title()) 
                    return None , citem
                return retval, self.setID(citem)
        except Exception as e: 
            self.log("validateInputs, key = %s no action! %s"%(key,e))
            return value, citem
            

    @cacheit(expiration=datetime.timedelta(minutes=5))
    def validatePaths(self, path, citem, spinner=True):
        def __set(path, citem):
            citem = self.setName(path, citem)
            self.log('validatePaths, path = %s'%path)
            return path, self.setLogo(citem.get('name'),citem)
            
        def __seek(item, citem):
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
                self.log('validatePaths _seek, waiting (%s) to seek %s'%(waitTime, item.get('file')))
                if monitor.waitForAbort(1.0) or waitTime < 1: break
                elif not player.isPlaying(): continue
                elif ((int(player.getTime()) > getTime) or BUILTIN.getInfoBool('SeekEnabled','Player')):
                    player.stop()
                    return True
            player.stop()
            return False
            
        def __vfs(path, citem):
            if isRadio({'path':[path]}) or isMixed_XSP({'path':[path]}): return True
            else:
                valid   = False
                media   = 'music' if isRadio({'path':[path]}) else 'video'
                dia     = DIALOG.progressDialog(message='%s %s, %s..\n%s'%(LANGUAGE(32098),'Path',LANGUAGE(32099),'%s...'%(str(path)[:48])))
                with BUILTIN.busy_dialog():
                    items = self.jsonRPC.walkFileDirectory(path, media, depth=5, retItem=True)
                
                for idx, dir in enumerate(items):
                    if MONITOR().waitForAbort(0.1): break
                    else:
                        item = random.choice(items.get(dir,[]))
                        dia  = DIALOG.progressDialog(int((idx*100)//len(items)),control=dia, message='%s %s...\n%s\n%s'%(LANGUAGE(32098),'Path','%s...'%(str(dir)[:48]),'%s...'%(str(item.get('file',''))[:48])))
                        item.update({'duration':self.jsonRPC.getDuration(item.get('file'), item, accurate=bool(SETTINGS.getSettingInt('Duration_Type')))})
                        if item.get('duration',0) == 0: continue
                        dia = DIALOG.progressDialog(int((idx*100)//len(items)),control=dia, message='%s %s...\n%s\n%s'%(LANGUAGE(32098),'Seeking','%s...'%(str(dir)[:48]),'%s...'%(str(item.get('file',''))[:48])))
                        if __seek(item, citem):
                            self.log('validatePaths _vfs, found playable and seek-able file %s'%(item.get('file')))
                            valid = True
                            break
                DIALOG.progressDialog(100,control=dia)
                return valid

        if path:
            if spinner:
                with self.toggleSpinner(): valid = __vfs(path, citem)
            else:                          valid = __vfs(path, citem)
            if valid:
                if spinner:
                    with self.toggleSpinner(): return __set(path, citem)
                else:                          return __set(path, citem)
                
        DIALOG.notificationDialog(LANGUAGE(32030))
        return None, citem


    def openEditor(self, path):
        self.log('openEditor, path = %s'%(path))
        if '|' in path: 
            path = path.split('|')
            path = path[0]#prompt user to select:
        media = 'video' if 'video' in path else 'music'
        if   '.xsp' in path: return self.openEditor(path,media)
        elif '.xml' in path: return self.openNode(path,media)
       

    def previewChannel(self, citem, retCntrl=None):
        def __buildItem(fileList, fitem):
            return LISTITEMS.buildMenuListItem('%s| %s'%(fileList.index(fitem),fitem.get('showlabel',fitem.get('label'))), fitem.get('file') ,icon=getThumb(fitem,opt=EPG_ARTWORK))
            
        def __fileList(citem):
            from builder import Builder
            monitor = MONITOR()
            builder = Builder()
            start_time = 0
            end_time = 0
            PROPERTIES.setInterruptActivity(False)
            while not monitor.abortRequested() and PROPERTIES.isRunning('OVERLAY_MANAGER'):
                if monitor.waitForAbort(1.0): break
                elif not PROPERTIES.isRunning('builder.build') and not PROPERTIES.isInterruptActivity():
                    DIALOG.notificationDialog('%s: [B]%s[/B]\n%s'%(LANGUAGE(32236),citem.get('name','Untitled'),LANGUAGE(32140)))
                    tmpcitem = citem.copy()
                    tmpcitem['id'] = getChannelID(citem['name'], citem['path'], random.random())
                    start_time = time.time()
                    fileList = builder.build([tmpcitem],preview=True)
                    end_time = time.time()
                    if not fileList or isinstance(fileList,list): break
                
            del builder
            del monitor
            PROPERTIES.setInterruptActivity(True)
            return fileList, round(abs(end_time-start_time),2)
            
        if not PROPERTIES.isRunning('previewChannel'):
            listitems = []
            with PROPERTIES.setRunning('previewChannel'), self.toggleSpinner():
                fileList, run_time = __fileList(citem)
                if not isinstance(fileList,list) and not fileList: DIALOG.notificationDialog('%s or\n%s'%(LANGUAGE(32030),LANGUAGE(32000)))
                else:
                    listitems = poolit(__buildItem)(*(fileList,fileList))
                    self.log('previewChannel, id = %s, listitems = %s'%(citem['id'],len(listitems)))
            if len(listitems) > 0: return DIALOG.selectDialog(listitems, header='%s: [B]%s[/B] - Build Time: [B]%ss[/B]'%(LANGUAGE(32235),citem.get('name','Untitled'),f"{run_time:.2f}"))
            if retCntrl: self.setFocusId(retCntrl)


    def getMontiorList(self):
        self.log('getMontiorList')
        try:
            with self.toggleSpinner():
                itemLST = [self.buildListItem(cleanLabel(value).title(),icon=ICON) for info in DIALOG.getInfoMonitor() for key, value in list(info.items()) if value not in ['','..'] and key not in ['path','logo']]
                if len(itemLST) == 0: raise Exception()
                itemSEL = DIALOG.selectDialog(itemLST,LANGUAGE(32078)%('Name'),useDetails=True,multi=False)
                if itemSEL is not None: return itemLST[itemSEL]
                else: raise Exception()
        except: return xbmcgui.ListItem(LANGUAGE(32079))


    def clearChannel(self, item, prompt=True, open=False):
        self.log('clearChannel, channelPOS = %s'%(item['number'] - 1))
        with self.toggleSpinner():
            if item['number'] > CHANNEL_LIMIT: return DIALOG.notificationDialog(LANGUAGE(32238))
            elif prompt and not DIALOG.yesnoDialog(LANGUAGE(32073)): return item
            self.madeChanges = True
            nitem = self.newChannel.copy()
            nitem['number'] = item['number'] #preserve channel number
            self.saveChannelItems(nitem, open)
            

    def moveChannel(self, citem, channelPOS):
        self.log('moveChannel, channelPOS = %s'%(channelPOS))
        if citem['number'] > CHANNEL_LIMIT: return DIALOG.notificationDialog(LANGUAGE(32064))
        retval = DIALOG.inputDialog(LANGUAGE(32137), key=xbmcgui.INPUT_NUMERIC, opt=citem['number'])
        if not retval: return citem, channelPOS
        retval = int(retval)
        if (retval > 0 and retval < CHANNEL_LIMIT) and retval != channelPOS + 1:
            if DIALOG.yesnoDialog('%s %s %s from [B]%s[/B] to [B]%s[/B]?'%(LANGUAGE(32136),citem['name'],LANGUAGE(32023),citem['number'],retval)):
                with self.toggleSpinner():
                    if retval in [channel.get('number') for channel in self.newChannels if channel.get('path')]: DIALOG.notificationDialog(LANGUAGE(32138))
                    else:
                        self.madeChanges = True
                        nitem = self.newChannel.copy()
                        nitem['number'] = channelPOS + 1
                        self.newChannels[channelPOS] = nitem
                        citem['number'] = retval
                        self.saveChannelItems(citem)
        

    def switchLogo(self, channelData, channelPOS):
        def __cleanLogo(chlogo):
            #todo convert resource from vfs to fs
            # return chlogo.replace('resource://','special://home/addons/')
            # resource = path.replace('/resources','').replace(,)
            # resource://resource.images.studios.white/Amazon.png
            return chlogo
        
        def __select(chname):
            def _build(logo):
                return self.buildListItem('%s| %s'%(logos.index(logo)+1, chname), unquoteString(logo), logo, [logo])
                
            DIALOG.notificationDialog(LANGUAGE(32140))
            with self.toggleSpinner():
                logos = self.resource.selectLogo(chname)
                listitems = poolit(_build)(logos)
            select = DIALOG.selectDialog(listitems,'%s (%s)'%(LANGUAGE(32066).split('[CR]')[1],chname),useDetails=True,multi=False)
            if select is not None: return listitems[select].getPath()

        def __browse(chname):
            with self.toggleSpinner():
                retval = DIALOG.browseSources(type=1,heading='%s (%s)'%(LANGUAGE(32066).split('[CR]')[0],chname), default=channelData.get('icon',''), shares='files', mask=xbmc.getSupportedMedia('picture'), exclude=[12,13,14,15,16,17,21,22])
            if FileAccess.copy(__cleanLogo(retval), os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')): 
                if FileAccess.exists(os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')): 
                    return os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')
            return retval
            
        def __match(chname):
            with self.toggleSpinner():
                return self.resource.getLogo(chname)

        chname  = channelData.get('name')
        if not chname: return DIALOG.notificationDialog(LANGUAGE(32065))
        
        chlogo = None
        retval = DIALOG.yesnoDialog(LANGUAGE(32066), heading     ='%s - %s'%(ADDON_NAME,LANGUAGE(32172)),
                                                     nolabel     = LANGUAGE(32067), #Select
                                                     yeslabel    = LANGUAGE(32068), #Browse
                                                     customlabel = LANGUAGE(30022)) #Auto
              
        if   retval == 0: chlogo = __select(chname)
        elif retval == 1: chlogo = __browse(chname)
        elif retval == 2: chlogo = __match(chname)
        else: DIALOG.notificationDialog(LANGUAGE(32070))
        self.log('switchLogo, chname = %s, chlogo = %s'%(chname,chlogo))
        
        if chlogo:
            self.madeChanges = True
            channelData['logo'] = chlogo
            DIALOG.notificationDialog(LANGUAGE(32139))
            if self.isVisible(self.itemList): self.buildChannelItem(channelData)
            else:
                self.newChannels[channelPOS] = channelData
                self.fillChanList(self.newChannels,refresh=True,focus=channelPOS)


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
 
 
    def setLabels(self, cntrl, label='', label2=''):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setLabel(str(label), str(label2))
            self.setVisibility(cntrl,(len(label) > 0 or len(label2) > 0))
        except Exception as e: self.log("setLabels, failed! %s"%(e), xbmc.LOGERROR)
    
    
    def setEnableCondition(self, cntrl, condition):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setEnableCondition(condition)
        except Exception as e: self.log("setEnableCondition, failed! %s"%(e), xbmc.LOGERROR)

        
    def saveChannelItems(self, citem: dict={}, open=False):
        self.log('saveChannelItems [%s], open = %s'%(citem.get('id'),open))
        self.newChannels[citem['number'] - 1] = citem
        self.fillChanList(self.newChannels,True,(citem['number'] - 1),citem if open else None)
        return citem
    
    
    def saveChanges(self):
        self.log("saveChanges")
        if DIALOG.yesnoDialog(LANGUAGE(32234)): self.saveChannels() 
        else:                                   self.closeManager()


    def saveChannels(self):
        def __validateChannels(channelList):
            def _validate(citem):
                if citem.get('name') and citem.get('path'):
                    if citem['number'] <= CHANNEL_LIMIT: citem['type'] = "Custom"
                    return self.setID(citem)
            channelList = self.channels.sortChannels([_f for _f in [_validate(channel) for channel in channelList] if _f])
            self.log('__validateChannels, channelList = %s'%(len(channelList)))
            return channelList
              
        if   not self.madeChanges: return
        elif not DIALOG.yesnoDialog(LANGUAGE(32076)): return
        with self.toggleSpinner():
            channels = __validateChannels(self.newChannels)
            changes  = __validateChannels(diffLSTDICT(self.channelList,self.newChannels))
            ids      = [citem.get('id') for citem in changes]
            self.log("saveChannels, channels = %s, ids = %s"%(len(channels), ids))
            if self.server:
                return DIALOG.notificationDialog(LANGUAGE(32197))
                # payload = {'uuid':SETTINGS.getMYUUID(),'name':self.friendly,'channels':self.newChannels}
                # requestURL('http://%s/%s'%(self.server.get('host'),CHANNELFLE), data=dumpJSON(payload), header=HEADER, json_data=True)
                #todo write tmp file if post fails, add to que to repost when url online.
            else:
                self.resetPagination(changes)
                SETTINGS.setResetChannels(ids)
                SETTINGS.setUpdateChannels(ids)
                self.channels.setChannels(channels)
        self.closeManager()
            
        
    def resetPagination(self, citem):
            if isinstance(citem, list): [self.resetPagination(item) for item in citem]
            else: 
                with self.toggleSpinner():
                    self.log('resetPagination, citem = %s'%(citem))
                    [self.jsonRPC.resetPagination(citem.get('id'), path) for path in citem.get('path',[]) if citem.get('id')]
        
        
    def closeManager(self):
        self.log('closeManager')
        if self.madeChanges: PROPERTIES.setEpochTimer('chkChannels')
        self.close()

        
    def __exit__(self):
        self.log('__exit__')
        del self.resource
        del self.jsonRPC
        del self.rule
        del self.channels
        
        
    def getFocusItems(self, controlId=None):
        focusItems = dict()
        if controlId in [5,6,7,9001,9002,9003,9004]:
            label, label2 = self.getLabels(controlId)
            try:    snum = int(cleanLabel(label.replace("|",'')))
            except: snum = 1
            if self.isVisible(self.chanList):
                cntrl = controlId
                sitem = self.chanList.getSelectedItem()
                citem = loadJSON(sitem.getProperty('citem'))
                chnum = (citem.get('number') or snum)
                chpos = self.chanList.getSelectedPosition()
                itpos = -1
            elif self.isVisible(self.itemList):
                cntrl = controlId
                sitem = self.itemList.getSelectedItem()
                citem = loadJSON(sitem.getProperty('citem'))
                chnum = (citem.get('number') or snum)
                chpos = chnum - 1
                itpos = self.itemList.getSelectedPosition()
            else:
                sitem = xbmcgui.ListItem()
                cntrl = (self.focusItems.get('cntrl')  or controlId)
                citem = (self.focusItems.get('citem')  or {})
                chnum = (self.focusItems.get('number') or snum)
                chpos = (self.focusItems.get('chpos')  or chnum - 1)
                itpos = (self.focusItems.get('itpos')  or -1)
            self.focusItems.update({'retCntrl':cntrl,'label':label,'label2':label2,'number':chnum,'chpos':chpos,'itpos':itpos,'item':sitem,'citem':citem})
            self.log('getFocusItems, controlId = %s, focusItems = %s'%(controlId,self.focusItems))
        return self.focusItems


    def onAction(self, act):
        actionId = act.getId()   
        if (time.time() - self.lastActionTime) < .5 and actionId not in ACTION_PREVIOUS_MENU: action = ACTION_INVALID # during certain times we just want to discard all input
        else:
            if actionId in ACTION_PREVIOUS_MENU:
                self.log('onAction: actionId = %s'%(actionId))
                if   xbmcgui.getCurrentWindowDialogId() == "13001": BUILTIN.executebuiltin("Action(Back)")
                elif self.isVisible(self.itemList): self.togglechanList(focus=self.getFocusItems().get('position'))
                elif self.isVisible(self.chanList):
                    if self.madeChanges: self.saveChanges()
                    else:                self.closeManager()
            
        
    def onFocus(self, controlId):
        self.log('onFocus: controlId = %s'%(controlId))

        
    def onClick(self, controlId):
        focusItems  = self.getFocusItems(controlId)
        focusID     = focusItems.get('retCntrl')
        focusLabel  = focusItems.get('label')
        focusNumber = focusItems.get('number',0)
        focusCitem  = focusItems.get('citem')
        focusPOS    = focusItems.get('chpos',0)
        autoTuned   = focusNumber > CHANNEL_LIMIT
        
        self.log('onClick: controlId = %s\nitems = %s'%(controlId,focusItems))
        if   controlId == 0: self.closeManager()
        #item list
        elif controlId == 5: self.buildChannelItem(focusCitem)
        elif controlId == 6:
            if    self.lockAutotune and autoTuned: DIALOG.notificationDialog(LANGUAGE(32064))
            else: self.buildChannelItem(self.itemInput(focusItems.get('item')),focusItems.get('item').getProperty('key'))
        #logo button
        elif controlId == 10: 
            if    self.lockAutotune and autoTuned: DIALOG.notificationDialog(LANGUAGE(32064))
            else: self.switchLogo(focusCitem,focusPOS)
        #side buttons
        elif controlId in [9001,9002,9003,9004]:
            if   focusLabel == LANGUAGE(32059): self.saveChannels() #Save 
            elif focusLabel == LANGUAGE(32061): self.clearChannel(focusCitem)#Delete
            elif focusLabel == LANGUAGE(32239): self.clearChannel(focusCitem,open=True)#Clear
            elif focusLabel == LANGUAGE(32136): self.moveChannel(focusCitem,focusItems.get('position'))#Move 
            elif focusLabel == LANGUAGE(32062): #Close
                if   self.isVisible(self.itemList): self.togglechanList(focus=focusPOS)
                elif self.isVisible(self.chanList): self.closeManager()
            elif focusLabel == LANGUAGE(32060): #Cancel
                if   self.isVisible(self.itemList): self.togglechanList(focus=focusPOS)
                elif self.isVisible(self.chanList): self.closeManager()
            elif focusLabel == LANGUAGE(32240): #Confirm
                if   self.isVisible(self.itemList) and self.madeChanges: self.saveChannelItems(focusCitem)
                elif self.isVisible(self.chanList) and self.madeChanges: self.saveChanges()
            elif focusLabel == LANGUAGE(32235): #Preview
                if self.madeChanges: self.saveChannelItems(focusCitem, open=True)
                self.previewChannel(focusCitem, focusID)