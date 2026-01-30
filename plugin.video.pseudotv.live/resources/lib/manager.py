  # Copyright (C) 2025 Lunatixz


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
from multiroom  import Multiroom
from xsp        import XSP
from builder    import Builder
from predefined import Predefined
from backup     import Backup
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
    focusIndex     = -1
    newChannels    = []
    oldChannels    = []
    spinner        = None
    monitor        = MONITOR()
    lastActionTime = time.time()
    
    def __init__(self, *args, **kwargs):
        self.log('__init__, running = %s'%(PROPERTIES.isRunning('Manager.__init__')))
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)    

        def __findAvailChannel(start):
            if start == -1: 
                for channel in self.channelList:
                    if not channel.get('id'): return channel.get('number')
            return start

        def __loadChannels(name=SETTINGS.getSetting('Default_Channels')): #load local or remote channel configurations
            self.log('__loadChannels, name = %s, local = %s'%(name, self.friendly))
            self.oldChannels = self.channels.getChannels()
            if   name == self.friendly or not kwargs.get('start',False): return self.oldChannels #Local
            elif name == LANGUAGE(30022):#Auto
                if len(self.oldChannels ) > 0: return self.oldChannels 
                else:                          return __loadChannels(LANGUAGE(32069))
            elif name == LANGUAGE(32069):#Ask
                def __buildItem(server):
                    return self.buildListItem(server.get('name'),'%s - %s: Channels (%s)'%(LANGUAGE(32211)%({True:'green',False:'red'}[server.get('online',False)],
                    {True:LANGUAGE(32158),False:LANGUAGE(32253)}[server.get('online',False)]),server.get('host'),len(server.get('channels',[]))),icon=DUMMY_ICON.format(text=str(servers.index(server)+1)))
                
                lizLST  = []
                serLST  = Multiroom().getDiscovery()
                servers = [value for key, value in list(serLST.items()) if value.get('online',False)]
                if servers: lizLST.extend(poolit(__buildItem)(servers))
                lizLST.insert(0,self.buildListItem(self.friendly,'%s - %s: Channels (%s)'%('[B]Local[/B]',self.host,len(self.oldChannels)),icon=ICON))
                select = DIALOG.selectDialog(lizLST, '%s for Channel Setup'%(LANGUAGE(30173)), None, True, SELECT_DELAY, False)
                if not select is None: return __loadChannels(lizLST[select].getLabel())
                else:                  return
            elif name:
                self.server = Multiroom().getDiscovery().get(name,{})
                return self.server.get('channels',[])
            return self.oldChannels

        with BUILTIN.busy_dialog(lock=True), PROPERTIES.interruptActivity():
            self.server         = {}
            self.cntrlStates    = {}
            
            self.madeChanges    = False
            self.madeItemchange = False
            self.showingList    = True
            
            self.openChannel    = kwargs.get('open')
            self.startChannel   = __findAvailChannel(kwargs.get('channel',-1))
            self.focusIndex     = (self.startChannel - 1) #Covert from channel number to list index ie. channel 1 => index 0
            
            self.cache          = SETTINGS.cache
            self.channels       = Channels(writable=True)
            self.rule           = RulesList()
            self.jsonRPC        = JSONRPC()
            self.resources      = Resources()

            self.host           = PROPERTIES.getRemoteHost()
            self.friendly       = PROPERTIES.getFriendlyName()
            self.newChannel     = self.channels.getTemplate()
            
        try:
            with BUILTIN.busy_dialog(lock=True):
                self.channelList = self.channels.sortChannels(self.createChannelList(self.buildArray(), __loadChannels()))
                self.newChannels = self.channelList.copy()
                if self.openChannel: self.openChannel = self.channelList[self.focusIndex]
                self.log('Manager, startChannel = %s, focusIndex = %s, openChannel = %s'%(self.startChannel, self.focusIndex, self.openChannel))
                if kwargs.get('start',True) and not PROPERTIES.isRunning('Manager.__init__'):
                    with PROPERTIES.chkRunning('Manager.__init__'):
                        self.doModal()
        except Exception as e: 
            self.log('Manager failed! %s'%(e), xbmc.LOGERROR)
            self.closeManager()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def onInit(self):
        try:
            self.focusItems    = {}
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

     
    def buildPreview(self, citem={}, msg=''):
        builder  = Builder()
        fileList = PROPERTIES.recessActivity(msg, builder.buildChannels, *([citem],True))
        del builder
        self.log('buildPreview, fileList = %s'%(len(fileList))) 
        return fileList


    def buildFileList(self, citem={}, path='', msg='', limit=SETTINGS.getSettingInt('Page_Limit')):
        fileList = PROPERTIES.recessActivity(msg, Builder().buildFileList, *(citem,path,'video',limit,{},{}))
        self.log('buildFileList, fileList = %s'%(len(fileList))) 
        return fileList


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
            channelArray[item["number"]-1].update(item) #CUSTOM
            
        checksum  = Globals._getMD5(FileAccess.dumpJSON(channelList))
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
            isFavorite    = citem.get('favorite',False)
            isRadio       = citem.get('radio',False)
            isLocked      = False #todo parse channel lock rule
            channelColor  = COLOR_UNAVAILABLE_CHANNEL
            labelColor    = COLOR_UNAVAILABLE_CHANNEL
            
            if citem.get("path"):
                labelColor = COLOR_AVAILABLE_CHANNEL
                if   isLocked:   channelColor = COLOR_LOCKED_CHANNEL
                elif isFavorite: channelColor = COLOR_FAVORITE_CHANNEL
                elif isRadio:    channelColor = COLOR_RADIO_CHANNEL
                else:            channelColor = COLOR_AVAILABLE_CHANNEL
            return self.buildListItem('[COLOR=%s][B]%s|[/COLOR][/B]'%(channelColor,citem["number"]),'[COLOR=%s]%s[/COLOR]'%(labelColor,citem.get("name",'')),items={'citem':citem,'chname':citem["name"],'chnum':'%i'%(citem["number"]),'radio':citem.get('radio',False),'description':LANGUAGE(32169)%(citem["number"],self.server.get('name',self.friendly))})
                
        self.togglechanList(reset=refresh)
        with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
            lizLST = []
            lizLST.extend(poolit(__buildItem)(channelList))
            self.chanList.addItems(lizLST)
            if focus is None: self.selItem(self.chanList, self.setFocusPOS(lizLST))
            else:             self.selItem(self.chanList, focus)
            self.setFocus(self.chanList)
            if channel: self.buildChannelItem(channel)


    def isLocked(self):
        return PROPERTIES.getEXTPropertyBool('%s.Manager.isLocked'%(ADDON_ID))
        
        
    def setLocked(self, state=True):
        try: self.getControl(41).setColorDiffuse({True:"0xC0FF0000",False:"0xFFFFFFFF"}[PROPERTIES.setEXTPropertyBool('%s.Manager.isLocked'%(ADDON_ID),state)])
        except: pass
        

    @contextmanager
    def toggleSpinner(self, state=True, lock=True, condition=None):
        self.log('toggleSpinner, state = %s, condition = %s, lock = %s'%(state,condition,lock))
        if not condition is None and condition:
            PROPERTIES.setRunning('Manager.toggleSpinner',state)
            self.setVisibility(self.spinner,state)
            if lock: self.setLocked(True)
            try: yield
            finally:
                if self.isLocked(): self.setLocked(False)
                self.setVisibility(self.spinner,False)
                PROPERTIES.setRunning('Manager.toggleSpinner',False)
        else: yield
        

    def togglechanList(self, state=True, focus=0, reset=False):
        self.log('togglechanList, state = %s, focus = %s, reset = %s'%(state,focus,reset))
        with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
            if state: # channellist
                if reset: 
                    self.setVisibility(self.chanList,False)
                    self.chanList.reset()
                    
                self.setVisibility(self.itemList,False)
                self.setVisibility(self.chanList,True)
                self.setFocus(self.chanList)
                self.selItem(self.chanList, focus)
                
                if self.madeChanges:
                    self.setLabels(self.right_button1,LANGUAGE(32059))#Save
                    self.setLabels(self.right_button2,LANGUAGE(32060))#Cancel
                    self.setLabels(self.right_button3,LANGUAGE(32136))#Move
                    self.setLabels(self.right_button4,LANGUAGE(32061))#Delete
                    self.setEnableCondition(self.right_button1,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chnum))]')
                    self.setEnableCondition(self.right_button2,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chnum))]')
                else:
                    if len(self.oldChannels) == 0:
                        self.setLabels(self.right_button1,LANGUAGE(32062))#Close
                        if PROPERTIES.hasBackup():  self.setLabels(self.right_button2,LANGUAGE(32112))#Recover
                        else:                       self.setLabels(self.right_button2,"")
                        if SETTINGS.hasAutotuned(): self.setLabels(self.right_button3,LANGUAGE(30038))#AutoTune
                        else:                       self.setLabels(self.right_button3,"")
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
                self.selItem(self.itemList, focus)
                self.setFocus(self.itemList)
                
                if self.madeItemchange:
                    self.setLabels(self.right_button1,LANGUAGE(32240))#Confirm
                    self.setLabels(self.right_button2,LANGUAGE(32060))#Cancel
                    self.setEnableCondition(self.right_button1,'[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Label) + !String.IsEmpty(Container(6).ListItem(Container(6).Position).Path)]')
                    self.setEnableCondition(self.right_button2,'[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Property(chnum))]')
                else:
                    self.setLabels(self.right_button1,LANGUAGE(32062))#Close
                    self.setLabels(self.right_button2,LANGUAGE(32060))#Cancel
                    self.setEnableCondition(self.right_button1,'[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Property(chnum))]')
                    self.setEnableCondition(self.right_button2,'[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Path)]')
                    
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
        
           
    def selItem(self, cntrl, focus=0):
        try: cntrl.selectItem(focus)
        except Exception as e:
            self.log("selItem, failed! %s"%(e), xbmc.LOGERROR)
           
           
    def getRuleAbbr(self, citem, myId, optionindex):
        value = citem.get('rules',{}).get(str(myId),{}).get('values',{}).get(str(optionindex))
        self.log('getRuleAbbr, id = %s, myId = %s, optionindex = %s, optionvalue = %s'%(citem.get('id',-1),myId,optionindex,value))
        return value
                    

    def getLogoColor(self, citem):
        self.log('getLogoColor, id = %s'%(citem.get('id',-1)))
        if  (citem.get('logo') and citem.get('name')) is None: return 'FFFFFFFF'
        elif citem.get('rules',{}).get("1"):
            if (self.getRuleAbbr(citem,1,4) or self.resources.isMono(citem['logo'])):
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
        LABEL = {'name'    : LANGUAGE(32092),
                 'path'    : LANGUAGE(32093),
                 'group'   : LANGUAGE(32094),
                 'rules'   : LANGUAGE(32095),
                 'radio'   : LANGUAGE(32091),
                 'favorite': LANGUAGE(32090),
                 'changed' : LANGUAGE(32259)}
                 
        DESC = {'name'    : LANGUAGE(32085),
                'path'    : LANGUAGE(32086),
                'group'   : LANGUAGE(32087),
                'rules'   : LANGUAGE(32088),
                'radio'   : LANGUAGE(32084),
                'favorite': LANGUAGE(32083),
                'changed' : LANGUAGE(33259)}

        lizLST = []
        lizLST.extend(poolit(__buildItem)(list(self.newChannel.keys())))
        self.itemList.addItems(lizLST)
        self.itemList.selectItem([idx for idx, liz in enumerate(lizLST) if liz.getProperty('key')== focuskey][0])
        self.setFocus(self.itemList)


    def itemInput(self, channelListItem=xbmcgui.ListItem()):
        def __getName(citem: dict={}, name: str=''):
            return DIALOG.inputDialog(message=LANGUAGE(32079),default=name), citem
       
        def __getPath(citem: dict={}, paths: list=[]):
            return self.getPaths(citem, paths)
        
        def __getRule(citem: dict={}, rules: dict={}):
            return self.getRules(citem, rules)
            
        def __getBool(citem: dict={}, state: bool=False):
            return not bool(state), citem

        def __getGroups(citem: dict={}, groups: list=[]):
            groups  = list([_f for _f in groups if _f])
            ngroups = sorted([_f for _f in set(SETTINGS.getSetting('User_Groups').split('|') + GROUP_TYPES + groups) if _f])
            ngroups.insert(0, '-%s'%(LANGUAGE(30064)))
            selects = DIALOG.selectDialog(ngroups,header=LANGUAGE(32081),preselect=Globals._findItemsInLST(ngroups,groups),useDetails=False)
            if not selects is None:
                if 0 in selects:
                    SETTINGS.setSetting('User_Groups',DIALOG.inputDialog(LANGUAGE(32044), default=SETTINGS.getSetting('User_Groups')))
                    return __getGroups(citem, groups)
                elif len(ngroups) > 0: groups = [ngroups[idx] for idx in selects]
            if not groups: groups = [LANGUAGE(30127)]
            return groups, citem
        
        key   = channelListItem.getProperty('key')
        value = channelListItem.getProperty('value')
        citem = FileAccess.loadJSON(channelListItem.getProperty('citem'))
        self.log('itemInput, In value = %s, key = %s\ncitem = %s'%(value,key,citem))
        
        KEY_INPUT = {"name"     : {'func':__getName  , 'kwargs':{'citem':citem, 'name'  :citem.get('name','')}},
                     "path"     : {'func':__getPath  , 'kwargs':{'citem':citem, 'paths' :citem.get('path',[])}},
                     "group"    : {'func':__getGroups, 'kwargs':{'citem':citem, 'groups':citem.get('group',[])}},
                     "rules"    : {'func':__getRule  , 'kwargs':{'citem':citem, 'rules' :self.rule.loadRules([citem]).get(citem['id'],{})}},
                     "radio"    : {'func':__getBool  , 'kwargs':{'citem':citem, 'state' :citem.get('radio',False)}},
                     "favorite" : {'func':__getBool  , 'kwargs':{'citem':citem, 'state' :citem.get('favorite',False)}},
                     "changed"  : {'func':__getBool  , 'kwargs':{'citem':citem, 'state' :citem.get('changed',False)}}}
              
        action = KEY_INPUT.get(key) 
        retval, citem = action['func'](*action.get('args',()),**action.get('kwargs',{}))
        retval, citem = self.validateInputs(key,retval,citem)
        if not retval is None:
            citem['changed']    = value != retval
            self.madeItemchange = value != retval
            if key in list(self.newChannel.keys()): citem[key] = retval
            self.log('itemInput, Out value = %s, key = %s\ncitem = %s'%(retval,key,citem))
        return citem
   
   
    def getPaths(self, citem: dict={}, paths: list=[]):
        def __buildItem(path):
            return self.buildListItem('%s|'%(pathLST.index(path)+1),path,paths=[path],icon=DUMMY_ICON.format(text=str(pathLST.index(path)+1)),items={'citem':citem,'idx':pathLST.index(path)+1})
        
        select  = -1
        lastOPT = None
        epaths  = paths.copy()
        pathLST = list([_f for _f in paths if _f])
        #radio check
        if not citem.get('radio',False) and isRadio({'path':paths}): citem['radio'] = True #set radio on music paths
        if citem.get('radio',False): excLST = [10,12,21,22]
        else:                        excLST = [11,13,21]
        
        while not self.monitor.abortRequested() and not select is None:
            with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                npath  = None
                lizLST = []
                if pathLST: lizLST.extend(poolit(__buildItem)(pathLST))
                lizLST.insert(0,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32100)),LANGUAGE(33113),icon=ICON,items={'key':'add','citem':citem,'idx':0}))
                if len(pathLST) > 0 and epaths != pathLST: lizLST.insert(1,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32101)),LANGUAGE(33114),icon=ICON,items={'key':'save','citem':citem}))
                
            select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32086), preselect=lastOPT, multi=False)
            if not select is None:
                with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                    key, path = lizLST[select].getProperty('key'), lizLST[select].getPath()
                    try:    lastOPT = int(lizLST[select].getProperty('idx'))
                    except: lastOPT = None
                    if key == 'add': 
                        predefined = {"idx":9, "label":'Predefined Channels', "label2":"Predefined Dynamic Playlists", "default":"", "shares":"", "mask":"?xsp=", "type":"", "multi":False}
                        retval     = DIALOG.browseSources(heading=LANGUAGE(32080), exclude=excLST, monitor=True, include=[])#include=[predefined]
                        if not retval is None:
                            npath, citem = self.validatePaths(retval,citem)
                            if npath: pathLST.append(npath)
                    elif key == 'save': 
                        paths = pathLST
                        break
                    elif path in pathLST:
                        retval = DIALOG.yesnoDialog(LANGUAGE(32102), customlabel=LANGUAGE(32103))
                        if retval in [1,2]: pathLST.pop(pathLST.index(path))
                        if retval == 2:
                            npath, citem = self.validatePaths(DIALOG.browseSources(heading=LANGUAGE(32080), default=path, monitor=True, exclude=excLST), citem)
                            pathLST.append(npath)
        self.log('getPaths, paths = %s'%(paths))
        return paths, citem


    def getRules(self, citem: dict={}, rules: dict={}):
        def __buildItem(data):
            return self.buildListItem(data[1].name,data[1].getTitle(),icon=DUMMY_ICON.format(text=str(data[1].myId)),items={'myId':data[1].myId,'citem':citem,'idx':list(ruleLST.keys()).index(data[0])+1}) 
        
        if citem.get('id') is None or len(citem.get('path',[])) == 0: DIALOG.notificationDialog(LANGUAGE(32071))
        else:            
            select  = -1
            erules  = rules.copy()
            ruleLST = rules.copy()
            lastIDX = None
            lastXID = None
            while not self.monitor.abortRequested() and not select is None:
                with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                    nrule  = None
                    crules = self.rule.loadRules([citem],append=True).get(citem['id'],{}) #all rule instances w/ channel rules
                    arules = [rule for key, rule in list(crules.items()) if not ruleLST.get(key)] #all unused rule instances
                    lizLST = []
                    lizLST.extend(poolit(__buildItem)([(key, rule) for key, rule in list(ruleLST.items()) if rule.myId]))
                    lizLST.insert(0,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32173)),"",icon=ICON,items={'key':'add' ,'citem':citem,'idx':0}))
                    if len(ruleLST) > 0 and erules != ruleLST: lizLST.insert(1,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32174)),"",icon=ICON,items={'key':'save','citem':citem}))
                            
                select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32095), preselect=lastIDX, multi=False)
                if not select is None:
                    key, myId = lizLST[select].getProperty('key'), int(lizLST[select].getProperty('myId') or '-1')
                    try:    lastIDX = int(lizLST[select].getProperty('idx'))
                    except: lastIDX = None
                    if key == 'add':
                        with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                            lizLST = [self.buildListItem(rule.name,rule.description,icon=DUMMY_ICON.format(text=str(rule.myId)),items={'idx':idx,'myId':rule.myId,'citem':citem}) for idx, rule in enumerate(arules) if rule.myId]
                        select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32072), preselect=lastXID, multi=False)
                        with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                            try:    lastXID = int(lizLST[select].getProperty('idx'))
                            except: lastXID = -1
                            nrule, citem = self.getRule(citem, arules[lastXID])
                            if not nrule is None: ruleLST.update({str(nrule.myId):nrule})
                    elif key == 'save':
                        rules = ruleLST
                        break
                    elif ruleLST.get(str(myId)):
                        with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
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
        select = -1
        while not self.monitor.abortRequested() and not select is None:
            with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                lizLST = [self.buildListItem('%s = %s'%(rule.optionLabels[idx],rule.optionValues[idx]),rule.optionDescriptions[idx],DUMMY_ICON.format(text=str(idx+1)),[str(rule.myId)],{'value':optionValue,'idx':idx,'myId':rule.myId,'citem':citem}) for idx, optionValue in enumerate(rule.optionValues)]
            select = DIALOG.selectDialog(lizLST, header='%s %s - %s'%(LANGUAGE(32176),rule.myId,rule.name), multi=False)
            if not select is None:
                try: rule.onAction(int(lizLST[select].getProperty('idx') or "0"))
                except Exception as e:
                    self.log("getRule, onAction failed! %s"%(e), xbmc.LOGERROR)
                    DIALOG.okDialog(LANGUAGE(32000))
        return rule, citem
    
        
    def setID(self, citem: dict={}) -> dict:
        if not citem.get('id') and citem.get('name') and citem.get('path') and citem.get('number'): 
            citem['id'] = getChannelID(citem['name'], citem['path'], citem['number'], SETTINGS.getMYUUID())
            self.log('setID, id = %s'%(citem['id']))
        return citem
    
       
    def setName(self, path, citem: dict={}) -> dict:
        with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
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
                with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                    citem['logo'] = self.resources.getLogo(citem, fallback=self.resources.getCache(citem['name']), lookup=True)
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
            with self.toggleSpinner():
                retval, citem = KEY_VALIDATION(value,citem)
                if retval is None:
                    DIALOG.notificationDialog(LANGUAGE(32077)%key.title()) 
                    return None , citem
                return retval, self.setID(citem)
        except Exception as e: 
            self.log("validateInputs, key = %s no action! %s"%(key,e))
            return value, citem
            
            
    def validatePaths(self, path, citem):
        # def __convert(path): #convert videodb:// paths to dynamic xsp.
            # if path.lower().startswith(('videodb://','musicdb://')):
                # if   'tvshows/titles'  in path: path = Predefined().createShowPlaylist(self.jsonRPC.videoIDtoLabel(path))
                # elif 'tvshows/studios' in path: path = Predefined().createNetworkPlaylist(self.jsonRPC.videoIDtoLabel(path))
                # elif 'tvshows/genres'  in path: path = Predefined().createTVGenrePlaylist(self.jsonRPC.videoIDtoLabel(path))
                # elif 'movies/genres'   in path: path = Predefined().createStudioPlaylist(self.jsonRPC.videoIDtoLabel(path))
                # elif 'movies/studios'  in path: path = Predefined().createStudioPlaylist(self.jsonRPC.videoIDtoLabel(path))
            # return path[0] if isinstance(path,list) else path

        def __set(path, citem):
            citem = self.setName(path, citem)
            return path, self.setLogo(citem.get('name'),citem)
            
        def __fileList(tmpcitem, fileList=[]):
            tmpcitem['id'] = getChannelID(tmpcitem['name'], tmpcitem['path'], random.random())
            return self.buildFileList(tmpcitem, path, msg='%s Path: %s\n%s'%(LANGUAGE(32098),tmpcitem['name'],LANGUAGE(32140)))
            
        def __seek(item, path, passed=False):
            player = PLAYER()
            if player.isPlaying(): DIALOG.notificationDialog('%s Path: %s\n%s'%(LANGUAGE(32098),path,LANGUAGE(30136)),time=1)
            else:
                # todo test seek for support disable via adv. rule if fails.
                # todo set seeklock rule if seek == False
                wait   = FIFTEEN
                resume = int(item.get('duration')/8)
                liz = xbmcgui.ListItem('Seek Test', path=item.get('file'))
                liz.setProperty('startoffset', str(resume))
                infoTag = ListItemInfoTag(liz, 'video')
                infoTag.set_resume_point({'ResumeTime':resume,'TotalTime':int(item.get('duration')*60)})
                
                player.play(item.get('file'),liz)
                while not self.monitor.abortRequested() and not player.isPlaying():
                    DIALOG.notificationDialog('%s Path: %s\n%s'%(LANGUAGE(32098),path,'Waiting for Playback (%s)'%(wait)),time=1)
                    if self.monitor.waitForAbort(1.0) or wait < 1: break
                    else: wait -= 1
                    
                if player.isPlaying() and not  self.monitor.waitForAbort(1.0):
                    self.log('validatePaths, _seek: playing %s seeking to %s'%(item.get('file'),resume))
                    if ((int(player.getTime()) > resume) or BUILTIN.getInfoBool('SeekEnabled','Player')):
                        DIALOG.notificationDialog('%s Path: %s\n[B]%s[/B]'%(LANGUAGE(32098),path,'PASSED!'),time=1)
                        passed = True
                    player.stop()
                    
            del player
            self.log('validatePaths, _seek: passed = %s'%(passed))
            return passed
            
        def __vfs(path, citem, cnt=3):
            with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                if    isRadio({'path':[path]}) or isMixed_XSP({'path':[path]}): return True
                else: DIALOG.notificationDialog('%s Path: %s\n%s'%(LANGUAGE(32098),path,LANGUAGE(32140)))
                tmpcitem = citem.copy()
                tmpcitem.update({'name':path,'path':[path]})
                fileList = __fileList(tmpcitem)
                self.log('validatePaths, __vfs: path = %s fileList = %s'%(path,len(fileList)))
            
            while not self.monitor.abortRequested() and cnt > 0:
                try:    file = FileAccess._getShortPath(path)
                except: file = FileAccess._getFolderPath(path)
                if not fileList: return not bool(DIALOG.notificationDialog('%s Path: %s\n%s'%(LANGUAGE(32098),path,LANGUAGE(32030))))
                else:
                    if __seek(random.choice(fileList), path): return DIALOG.notificationDialog('%s Path: %s\n[B]%s[/B]'%(LANGUAGE(32098),path,'PASSED!'),time=1)
                    else:
                        retval = DIALOG.yesnoDialog(LANGUAGE(30202),customlabel='Try Again (%s)'%(cnt))
                        if   retval == 1: return DIALOG.notificationDialog('%s Path: %s\n[B]%s[/B]'%(LANGUAGE(32098),path,'FORCED!'),time=1)
                        elif retval == 2: cnt -=1
                        else: return not bool(DIALOG.notificationDialog('%s Path: %s\n[B]%s[/B]'%(LANGUAGE(32098),path,'FAILED!'),time=1))
        if path: 
            # path = __convert(path)
            if __vfs(path, citem): return __set(path, citem)
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
        def __buildItem(fitem):
            return self.buildListItem('%s| %s'%(fileList.index(fitem),fitem.get('showlabel',fitem.get('label'))), fitem.get('file') ,icon=(Globals._getThumb(fitem,opt=EPG_ARTWORK) or {0:FANART,1:COLOR_LOGO}[EPG_ARTWORK]))
            
        def __fileList(citem):
            fileList = []
            try:
                DIALOG.notificationDialog('%s: [B]%s[/B]\n%s'%(LANGUAGE(32236),citem.get('name','Untitled'),LANGUAGE(32140)))
                tmpcitem = citem.copy()
                tmpcitem['id'] = getChannelID(citem['name'], citem['path'], random.random())
                start_time = time.time()
                fileList   = self.buildPreview(tmpcitem)
                end_time   = time.time()
                self.log('previewChannel: __fileList, id = %s, fileList = %s'%(citem['id'],len(fileList)))
                return fileList, round(abs(end_time-start_time),2)
            except Exception as e:
                self.log("previewChannel, __fileList: failed! %s"%(e), xbmc.LOGERROR)
                return [], 0
            
        if not PROPERTIES.isRunning('Manager.previewChannel'):
            with PROPERTIES.chkRunning('Manager.previewChannel'), self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                lizLST = []
                fileList, run_time = __fileList(citem)
                if not isinstance(fileList,list) and not fileList: DIALOG.notificationDialog('%s or\n%s'%(LANGUAGE(32030),LANGUAGE(32000)))
                elif fileList:
                    lizLST.extend(poolit(__buildItem)(fileList))
            if len(lizLST) > 0: return DIALOG.selectDialog(lizLST, header='%s: [B]%s[/B] - Build Time: [B]%ss[/B]'%(LANGUAGE(32235),citem.get('name','Untitled'),f"{run_time:.2f}"))
            if retCntrl: self.setFocusId(retCntrl)


    def getMontiorList(self):
        self.log('getMontiorList')
        try:
            with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                labels  = sorted(set([cleanLabel(value).title() for info in DIALOG.getInfoMonitor() for key, value in list(info.items()) if value not in ['','..'] and key not in ['path','logo']]))
                itemLST = [self.buildListItem(label,icon=ICON) for label in labels]
                if len(itemLST) == 0: raise Exception()
                itemSEL = DIALOG.selectDialog(itemLST,LANGUAGE(32078)%('Name'),useDetails=True,multi=False)
                if itemSEL is not None: return itemLST[itemSEL]
                else: raise Exception()
        except: return xbmcgui.ListItem(LANGUAGE(32079))


    def clearChannel(self, item, prompt=True, open=False):
        self.log('clearChannel, channelPOS = %s'%(item['number'] - 1))
        with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
            if item['number'] > CHANNEL_LIMIT: return DIALOG.notificationDialog(LANGUAGE(32238))
            elif prompt and not DIALOG.yesnoDialog(LANGUAGE(32073)): return item
            self.madeItemchange = True
            nitem = self.newChannel.copy()
            nitem['number'] = item['number'] #preserve channel number
            self.saveChannelItems(nitem, open)
            

    def moveChannel(self, citem, channelPOS):
        self.log('moveChannel, channelPOS = %s'%(channelPOS))
        if citem['number'] > CHANNEL_LIMIT: return DIALOG.notificationDialog(LANGUAGE(32064))
        retval = DIALOG.inputDialog(LANGUAGE(32137), key=xbmcgui.INPUT_NUMERIC, opt=citem['number'])
        if retval:
            retval = int(retval)
            if (retval > 0 and retval < CHANNEL_LIMIT) and retval != channelPOS + 1:
                if DIALOG.yesnoDialog('%s %s %s from [B]%s[/B] to [B]%s[/B]?'%(LANGUAGE(32136),citem['name'],LANGUAGE(32023),citem['number'],retval)):
                    with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                        if retval in [channel.get('number') for channel in self.newChannels if channel.get('path')]: DIALOG.notificationDialog(LANGUAGE(32138))
                        else:
                            self.madeItemchange = True
                            nitem = self.newChannel.copy()
                            nitem['number'] = channelPOS + 1
                            self.newChannels[channelPOS] = nitem
                            citem['number'] = retval
                            self.saveChannelItems(citem)
            

    def switchLogo(self, channelData, channelPOS):
        def __cleanLogo(chlogo):
            #todo convert resources from vfs to fs
            # return chlogo.replace('resources://','special://home/addons/')
            # resources = path.replace('/resources','').replace(,)
            # resources://resources.images.studios.white/Amazon.png
            return chlogo
        
        def __select():
            def __buildItem(logo):
                return self.buildListItem('%s| %s'%(logos.index(logo)+1, os.path.splitext(os.path.basename(logo))[0].upper() if len(os.path.splitext(os.path.basename(logo))[0]) <= 4 else os.path.splitext(os.path.basename(logo))[0].title()), Globals._unquoteString(logo), logo, [logo])
                
            DIALOG.notificationDialog(LANGUAGE(32140))
            with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                chname = channelData.get('name')
                logos  = self.resources.selectLogo(channelData)
                lizLST = []
                lizLST.extend(poolit(__buildItem)(logos))
            select = DIALOG.selectDialog(lizLST,'%s (%s)'%(LANGUAGE(32066).split('[CR]')[1],chname),useDetails=True,multi=False)
            if select is not None: return lizLST[select].getPath()

        def __browse():
            with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                chname = channelData.get('name')
                retval = DIALOG.browseSources(type=1,heading='%s (%s)'%(LANGUAGE(32066).split('[CR]')[0],chname), default=channelData.get('icon',''), shares='files', mask=xbmc.getSupportedMedia('picture'), exclude=[12,13,14,15,16,17,21,22])
            if FileAccess.copy(__cleanLogo(retval), os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')): 
                if FileAccess.exists(os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')): 
                    return os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')
            return retval
            
        def __match():
            with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                return self.resources.getLogo(channelData, fallback=self.resources.getCache(channelData['name']), lookup=True)

        if not channelData.get('name'): return DIALOG.notificationDialog(LANGUAGE(32065))
        chlogo = None
        retval = DIALOG.yesnoDialog(LANGUAGE(32066), heading     ='%s - %s'%(ADDON_NAME,LANGUAGE(32172)),
                                                     nolabel     = LANGUAGE(32067), #Select
                                                     yeslabel    = LANGUAGE(32068), #Browse
                                                     customlabel = LANGUAGE(30022)) #Auto
              
        if   retval == 0: chlogo = __select()
        elif retval == 1: chlogo = __browse()
        elif retval == 2: chlogo = __match()
        else: DIALOG.notificationDialog(LANGUAGE(32070))
        if chlogo and chlogo != LOGO:
            self.log('switchLogo, chname = %s, chlogo = %s'%(channelData.get('name'),chlogo))
            DIALOG.notificationDialog(LANGUAGE(32139))
            self.madeChanges = True
            channelData['logo'] = chlogo
            self.newChannels[channelPOS] = channelData
            self.fillChanList(self.newChannels,refresh=True,focus=channelPOS)


    def isVisible(self, cntrl):
        try: 
            if isinstance(cntrl, int):      cntrl = self.getControl(cntrl)
            if hasattr(cntrl, 'isVisible'): state = cntrl.isVisible()
        except: state = self.cntrlStates.get(cntrl.getId(),False)
        self.log('isVisible, cntrl = %s, state = %s'%(cntrl.getId(),state))
        return state
        
        
    def setVisibility(self, cntrl, state):
        try: 
            if isinstance(cntrl, int):       cntrl = self.getControl(cntrl)
            if hasattr(cntrl, 'setVisible'): cntrl.setVisible(state)
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
        if self.madeItemchange:
            with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                self.madeItemchange = False
                citem['changed'] = True
                self.madeChanges = True
                self.newChannels[citem['number'] - 1] = citem
        self.fillChanList(self.newChannels,True,(citem['number'] - 1),citem if open else None)
        return citem
    

    def closeChannel(self, citem, focus=0, open=False):
        self.log('closeChannel')
        if self.madeItemchange:
            if DIALOG.yesnoDialog(LANGUAGE(32243)): return self.saveChannelItems(citem, open)
        self.togglechanList(focus=focus)
                    
            
    def saveChanges(self):
        self.log("saveChanges")
        def __validateChannels(channelList):
            def __validate(citem):
                if citem.get('name') and citem.get('path'):
                    if citem['number'] <= CHANNEL_LIMIT: citem['type'] = LANGUAGE(30127) #"Custom"
                    return self.setID(citem)
            channelList = Globals._setDictLST(self.channels.sortChannels([_f for _f in [__validate(channel) for channel in channelList] if _f]))
            self.log('__validateChannels, channelList = %s'%(len(channelList)))
            return channelList
        
        if self.madeChanges:
            if DIALOG.yesnoDialog(LANGUAGE(32076)):
                with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                    self.log("saveChanges, backup = %s"%(Backup().backupChannels(CHANNELFLE_CHANGE,silent=True)))
                    channels = __validateChannels(self.newChannels)
                    self.log("saveChanges, channels = %s"%(len(channels)))
                    if self.server: #remote save
                        requestURL('http://%s/%s'%(self.server.get('host'), CHANNELFLE), payload={'uuid':SETTINGS.getMYUUID(),'name':self.friendly,'payload':channels})
                    else: #local save
                        self.channels.setChannels(channels) #save changes
                        timerit(PROPERTIES.setPropTimer)(FIFTEEN,'chkChannels')#trigger channel building
                    self.madeChanges = False
        self.closeManager()
            

    def closeManager(self):
        self.log('closeManager, madeChanges = %s'%(self.madeChanges))
        if self.madeChanges: self.saveChanges() 
        else:                self.close()
        
        
    def getFocusItems(self, controlId=None):
        if controlId in [5,6,7,9000,9001,9002,9003,9004]:
            label, label2 = self.getLabels(controlId)
            try:     snum = int(cleanLabel(label.replace("|",'')))
            except:  snum = 1
            if self.isVisible(self.chanList):
                cntrl = controlId
                sitem = (self.chanList.getSelectedItem() or xbmcgui.ListItem())
                citem = FileAccess.loadJSON(sitem.getProperty('citem'))
                chnum = (citem.get('number') or snum)
                chpos = self.chanList.getSelectedPosition()
                itpos = -1
            elif self.isVisible(self.itemList):
                cntrl = controlId
                sitem = (self.itemList.getSelectedItem() or xbmcgui.ListItem())
                citem = FileAccess.loadJSON(sitem.getProperty('citem'))
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
        if  (time.time() - self.lastActionTime) < .5 and actionId not in ACTION_PREVIOUS_MENU: pass #ACTION_INVALID # during certain times we just want to discard all input
        else:
            if actionId in ACTION_PREVIOUS_MENU:
                if self.isLocked(): DIALOG.notificationDialog(LANGUAGE(32260))
                else:
                    with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                        self.log('onAction: actionId = %s, locked = %s'%(actionId,self.isLocked()))
                        if   xbmcgui.getCurrentWindowDialogId() == "13001": BUILTIN.executebuiltin('Action(Back)')
                        elif self.isVisible(self.chanList): self.closeManager()
                        else:
                            focusItems = self.getFocusItems
                            if self.isVisible(self.itemList):
                                self.closeChannel(focusItems.get('citem'),focusItems.get('position'))
            
            
    def onFocus(self, controlId):
        self.log('onFocus: controlId = %s'%(controlId))

        
    def onClick(self, controlId):
        if (self.isLocked() or (time.time() - self.lastActionTime) < .5 and controlId not in [9000,9001,9002,9003,9004]): DIALOG.notificationDialog(LANGUAGE(32260))
        else:
            with self.toggleSpinner(condition=PROPERTIES.isRunning('Manager.toggleSpinner')==False):
                self.log('onClick: controlId = %s, locked = %s'%(controlId,self.isLocked()))
                if controlId == 0: self.closeManager()
                else:
                    focusItems = self.getFocusItems(controlId)
                    if   controlId == 5:  self.buildChannelItem(focusItems.get('citem')) #item list
                    elif controlId == 6:  self.buildChannelItem(self.itemInput(focusItems.get('item')),focusItems.get('item').getProperty('key'))
                    elif controlId == 10: self.switchLogo(focusItems.get('citem'), focusItems.get('chpos',0))#logo button
                    elif controlId in [9001,9002,9003,9004]: #side buttons
                        if   focusItems.get('label') == LANGUAGE(32059): self.saveChanges()                                   #Save 
                        elif focusItems.get('label') == LANGUAGE(32061): self.clearChannel(focusItems.get('citem'))           #Delete
                        elif focusItems.get('label') == LANGUAGE(32239): self.clearChannel(focusItems.get('citem'), open=True)#Clear
                        elif focusItems.get('label') == LANGUAGE(32136): self.moveChannel(focusItems.get('citem'), focusItems.get('chpos',0))  #Move 
                        elif focusItems.get('label') == LANGUAGE(32062): #Close
                            if   self.isVisible(self.itemList): self.closeChannel(focusItems.get('citem'), focus=focusItems.get('chpos',0))
                            elif self.isVisible(self.chanList): self.closeManager()
                        elif focusItems.get('label') == LANGUAGE(32060): #Cancel
                            if   self.isVisible(self.itemList): self.closeChannel(focusItems.get('citem'))
                            elif self.isVisible(self.chanList): self.closeManager()
                        elif focusItems.get('label') == LANGUAGE(32240): #Confirm
                            if   self.isVisible(self.itemList): self.saveChannelItems(focusItems.get('citem'))
                            elif self.isVisible(self.chanList): self.saveChanges()
                        elif focusItems.get('label') == LANGUAGE(32235): #Preview
                            if self.isVisible(self.itemList) and self.madeItemchange: self.closeChannel(focusItems.get('citem'), open=True)
                            self.previewChannel(focusItems.get('citem'), focusItems.get('retCntrl'))
                        elif focusItems.get('label') == LANGUAGE(32110): ...#Backup
                        elif focusItems.get('label') == LANGUAGE(32112): ...#Recover
                        elif focusItems.get('label') == LANGUAGE(30038): timerit(SETTINGS.autoTune)(0.1)#AutoTune
                    