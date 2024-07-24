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
from ast        import literal_eval
from xsp        import XSP
from m3u        import M3U
from xmltvs     import XMLTVS
from infotagger.listitem import ListItemInfoTag

MONITOR = xbmc.Monitor()
PLAYER  = xbmc.Player()

# Actions
ACTION_MOVE_LEFT     = 1
ACTION_MOVE_RIGHT    = 2
ACTION_MOVE_UP       = 3
ACTION_MOVE_DOWN     = 4
ACTION_SELECT_ITEM   = 7
ACTION_INVALID       = 999
ACTION_SHOW_INFO     = [11,24,401]
ACTION_PREVIOUS_MENU = [92, 10,110,521] #+ [9, 92, 216, 247, 257, 275, 61467, 61448]
     
def forceUpdateTime(key):
    PROPERTIES.setPropertyInt(key,0)

def findItemsInLST(items, values, item_key='getLabel', val_key='', index=True):
    if not values: return [-1]
    matches = []
    def match(fkey,fvalue):
        if fkey.lower() == fvalue.lower():
            matches.append(idx if index else item)
                    
    for value in values:
        if isinstance(value,dict): 
            value = value.get(val_key,'')
            
        for idx, item in enumerate(items): 
            if isinstance(item,xbmcgui.ListItem): 
                if item_key == 'getLabel':  
                    match(item.getLabel() ,value)
                elif item_key == 'getLabel2': 
                    match(item.getLabel2(),value)
            elif isinstance(item,dict):       
                match(item.get(item_key,''),value)
            else: match(item,value)
    return matches

class Manager(xbmcgui.WindowXMLDialog):
    lockAutotune   = False
    madeChanges    = False
    lastActionTime = time.time()
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        if isClient():
            DIALOG.notificationDialog(LANGUAGE(32058))
            return openAddonSettings((0,1))
        else:
            with busy_dialog(), suspendActivity():
                self.cntrlStates  = {}
                self.showingList  = True
                
                self.cache        = Cache(mem_cache=True)
                self.channels     = Channels()
                self.eChannels    = self.channels.getChannels() #existing channels
                self.rules        = RulesList()
                self.jsonRPC      = JSONRPC()
                self.resources    = Resources(self.jsonRPC, self.cache)
                self.m3u          = M3U()
                self.xmltv        = XMLTVS()
                
                self.newChannel   = self.channels.getTemplate()
                self.channelList  = sorted(self.createChannelList(self.buildArray(), self.eChannels), key=lambda k: k['number'])
                self.channelList.extend(self.channels.getAutotuned())
                self.newChannels  = self.channelList.copy()
                
                self.startChannel = kwargs.get('channel',-1)
                if self.startChannel == -1: self.startChannel = self.getFirstAvailChannel()
                self.focusIndex   = (self.startChannel - 1) #Convert from Channel number to array index
                self.log('Manager, startChannel = %s, focusIndex = %s'%(self.startChannel, self.focusIndex))
               
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
        
        
    def buildArray(self):
        self.log('buildArray') # Create blank array of citem templates. 
        def _create(idx):
            newChannel = self.newChannel.copy()
            newChannel['number'] = idx + 1
            return newChannel
        return [_create(channel) for channel in range(CHANNEL_LIMIT)]
  
        
    def createChannelList(self, channelArray, channelList):
        self.log('createChannelList') # Fill blank array with citems from channels.json.
        def _update(item):
            for channel in channelList:
                if item["number"] == channel["number"]:
                    item.update(channel)
                    break
            return item
        return [_update(channel) for channel in channelArray]
            
        
    @cacheit(expiration=datetime.timedelta(minutes=15))
    def newStation(self, citem: dict={}):
        if citem.get('id') is None: return False
        else: return self.m3u.findStation(citem)[0] is None


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def hasProgrammes(self, citem: dict={}):
        if citem.get('id') is None: return False
        else: return not self.xmltv.findChannel(citem)[0] is None


    def buildListItem(self, label: str="", label2: str="", icon: str="", paths: list=[], items: dict={}):
        self.log('buildListItem, label = %s, label2 = %s'%(label,label2))
        if not icon:  icon  = (items.get('citem',{}).get('logo') or COLOR_LOGO)
        if not paths: paths = (items.get('citem',{}).get("path") or [])
        return LISTITEMS.buildMenuListItem(label, label2, icon, url='|'.join(paths), props=items)


    def buildChannelListItem(self, citem: dict={}):
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
       
        return self.buildListItem('[COLOR=%s][B]%s|[/COLOR][/B]'%(channelColor,citem["number"]),'[COLOR=%s]%s[/COLOR]'%(labelColor,citem.get("name",'')),items={'citem':citem,'description':LANGUAGE(32169)%(citem["number"])})
        

    def fillChanList(self, channelList, reset=False, focus=None):
        self.log('fillChanList, focus = %s'%(focus))
        ## Fill chanList listitem for display. *reset draws new control list. *focus list index for channel position.
        self.togglechanList(True,reset=reset)
        with self.toggleSpinner(self.chanList):
            listitems = poolit(self.buildChannelListItem)(channelList)
            self.chanList.addItems(listitems)
            if focus is None: self.chanList.selectItem(self.setFocusPOS(listitems))
            else:             self.chanList.selectItem(focus)


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
                          
                listItems = list()
                for key in list(self.newChannel.keys()):
                    key   = key.lower()
                    value = citem.get(key,' ')
                    if   key in ["number","type","logo","id","catchup"]: continue # keys to ignore, internal use only.
                    elif isinstance(value,(list,dict)): 
                        if   key == "group" : value = '|'.join(sorted(set(value)))
                        elif key == "path"  : value = '|'.join(value)
                        elif key == "rules" : value = '|'.join([rule.name for key, rule in self.rules.loadRules([citem]).get(citem['id'],{}).items()])#todo load rule names
                    elif not isinstance(value,str): value = str(value)
                    elif not value: value = ' '
                    listItems.append(self.buildListItem(LABEL.get(key,' '),value,items={'key':key,'value':value,'citem':citem,'description':DESC.get(key,''),'colorDiffuse':self.getLogoColor(citem)}))

            self.itemList.addItems(listItems)
            self.itemList.selectItem([idx for idx, liz in enumerate(listItems) if liz.getProperty('key')== focuskey][0])
            self.setFocus(self.itemList)


    def itemInput(self, channelListItem):
        key   = channelListItem.getProperty('key')
        value = channelListItem.getProperty('value')
        citem = loadJSON(channelListItem.getProperty('citem'))
        self.log('itemInput, In value = %s, key = %s\ncitem = %s'%(value,key,citem))
        
        KEY_INPUT = {"name"     : {'func':self.getName    ,'kwargs':{'name'  :value}},
                     "path"     : {'func':self.getPaths   ,'kwargs':{'paths' :value.split('|')}},
                     "group"    : {'func':self.getGroups  ,'kwargs':{'groups':value.split('|')}},
                     "rules"    : {'func':self.getRules   ,'kwargs':{'rules' :self.rules.loadRules([citem],incRez=False).get(citem['id'],{})}},
                     "radio"    : {'func':self.getBool    ,'kwargs':{'state' :value}},
                     "favorite" : {'func':self.getBool    ,'kwargs':{'state' :value}}}
                     
        retval, citem = KEY_INPUT[key]['func'](citem, *KEY_INPUT[key].get('args',()),**KEY_INPUT[key].get('kwargs',{}))
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
        return SETTINGS.getSetting('DIFFUSE_LOGO')
        
   
    def getRuleAbbr(self, citem, myId, optionindex):
        value = citem.get('rules',{}).get(str(myId),{}).get('values',{}).get(str(optionindex))
        self.log('getRuleAbbr, id = %s, myId = %s, optionindex = %s, optionvalue = %s'%(citem.get('id',-1),myId,optionindex,value))
        return value
                    
           
    def getName(self, citem: dict={}, name: str=''):
        return DIALOG.inputDialog(message=LANGUAGE(32079),default=name), citem
   

    def getPaths(self, citem: dict={}, paths: list=[]):
        select = -1
        while not MONITOR.abortRequested() and not select is None:
            with self.toggleSpinner(self.itemList):
                paths  = list(filter(None,paths))
                npath  = None
                lizLST = [self.buildListItem('%s|'%(idx+1),path,paths=[path],icon=DUMMY_ICON.format(text=str(idx+1)),items={'citem':citem}) for idx, path in enumerate(paths) if path]
                lizLST.insert(0,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32100)),LANGUAGE(33113),icon=ICON,items={'key':'add' ,'citem':citem}))
                if len(paths) > 0:
                    lizLST.insert(1,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32101)),LANGUAGE(33114),icon=ICON,items={'key':'save','citem':citem}))
                
            select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32086), multi=False)
            if not select is None:
                key, path = lizLST[select].getProperty('key'), lizLST[select].getPath()
                if key == 'add': 
                    with self.toggleSpinner(self.itemList):
                        npath, citem = self.validatePath(DIALOG.browseDialog(heading=LANGUAGE(32080),monitor=True), citem)
                elif key == 'save': break
                elif path in paths:
                    retval = DIALOG.yesnoDialog(LANGUAGE(32102), customlabel=LANGUAGE(32103))
                    if retval in [1,2]: paths.pop(paths.index(path))
                    if retval == 2:
                        with self.toggleSpinner(self.itemList):
                            npath, citem = self.validatePath(DIALOG.browseDialog(heading=LANGUAGE(32080),default=path,monitor=True), citem)
                if not npath is None: paths.append(npath)
        self.log('getPaths, paths = %s'%(paths))
        return paths, citem
           
           
    def getGroups(self, citem: dict={}, groups: list=[]):
        groups  = list(filter(None,groups))
        ngroups = sorted(filter(None,set(SETTINGS.getSetting('User_Groups').split('|') + GROUP_TYPES + groups)))
        if len(ngroups) > 0: 
            groups = [ngroups[idx] for idx in DIALOG.selectDialog(ngroups,header=LANGUAGE(32081),preselect=findItemsInLST(ngroups,groups),useDetails=False)]
        self.log('getGroups, groups = %s'%(groups))
        return groups, citem
    
    
    def getBool(self, citem: dict={}, state: str='True'):
        state = not literal_eval(state)
        self.log('getBool, state = %s'%(state))
        return state, citem


    def getRules(self, citem: dict={}, rules: dict={}):
        if citem.get('id') is None: DIALOG.notificationDialog(LANGUAGE(32071))
        else:            
            select = -1
            while not MONITOR.abortRequested() and not select is None:
                with self.toggleSpinner(self.itemList):
                    nrule  = None
                    crules = self.rules.loadRules([citem],append=True,incRez=False).get(citem['id'],{}) #all rule instances w/ channel rules
                    arules = [rule for key, rule in crules.items() if not rules.get(key)] #all unused rule instances
                    
                    lizLST = [self.buildListItem(rule.name,rule.getTitle(),icon=DUMMY_ICON.format(text=str(rule.myId)),items={'myId':rule.myId,'citem':citem}) for key, rule in rules.items() if rule.myId]
                    lizLST.insert(0,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32173)),LANGUAGE(33173),icon=ICON,items={'key':'add' ,'citem':citem}))
                    if len(rules) > 0:
                        lizLST.insert(1,self.buildListItem('[COLOR=white][B]%s[/B][/COLOR]'%(LANGUAGE(32174)),LANGUAGE(33174),icon=ICON,items={'key':'save','citem':citem}))
                            
                select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32095), multi=False)
                if not select is None:
                    key, myId = lizLST[select].getProperty('key'), int(lizLST[select].getProperty('myId') or '-1')
                    
                    if key == 'add':
                        with self.toggleSpinner(self.itemList):
                            lizLST = [self.buildListItem(rule.name,rule.description,icon=DUMMY_ICON.format(text=str(rule.myId)),items={'idx':idx,'myId':rule.myId,'citem':citem}) for idx, rule in enumerate(arules) if rule.myId]
                        select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32072), multi=False)
                        nrule, citem = self.getRule(citem, arules[int(lizLST[select].getProperty('idx') or "-1")])
                    elif key == 'save': break
                    elif rules.get(str(myId)):
                        retval = DIALOG.yesnoDialog(LANGUAGE(32175), customlabel=LANGUAGE(32176))
                        if retval in [1,2]: rules.pop(str(myId))
                        if retval == 2: nrule, citem = self.getRule(citem, crules.get(str(myId),{}))
                    elif not rules.get(str(myId)): nrule, citem = self.getRule(citem, crules.get(str(myId),{}))
                    if not nrule is None: rules.update({str(nrule.myId):nrule})
            self.log('getRules, rules = %s'%(len(rules)))
            return self.rules.dumpRules(rules), citem
        

    def getRule(self, citem={}, rule={}):
        select = -1
        while not MONITOR.abortRequested() and not select is None:
            with self.toggleSpinner(self.itemList):
                lizLST = [self.buildListItem('%s = %s'%(rule.optionLabels[idx],rule.optionValues[idx]),rule.optionDescriptions[idx],icon=DUMMY_ICON.format(text=str(idx+1)),items={'value':optionValue,'idx':idx,'myId':rule.myId,'citem':citem}) for idx, optionValue in enumerate(rule.optionValues)]
            select = DIALOG.selectDialog(lizLST, header='%s %s - %s'%(LANGUAGE(32176),rule.myId,rule.name), multi=False)
            try:
                rule.onAction(int(lizLST[select].getProperty('idx') or "0"))
                self.madeChanges = True
            except Exception as e:
                self.log("getRule, onAction failed! %s"%(e), xbmc.LOGERROR)
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
                with self.toggleSpinner(self.itemList):
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
            
        if not label or (len(label) < 1 or len(label) > 128): return None, citem
        elif _chkName(label): return '', citem
        else:
            self.log('validateLabel, label = %s'%(label))
            return label, self.setLogo(label, citem, force=True)


    def validatePaths(self, paths, citem):
        if len(paths) == 0: return None, citem
        else:
            citem = self.setName(paths[0], citem)
            self.log('validatePaths, paths = %s'%paths)
            return paths, self.setLogo(citem.get('name'),citem)

        
    def validatePath(self, path, citem, spinner=True):
        def _seek(item, citem):
            file = item.get('file')
            dur  = item.get('duration')
            if PLAYER.isPlaying() or not file.startswith(tuple(VFS_TYPES)) and not file.endswith('.strm'): return True
            # todo test seek for support disable via adv. rule if fails.
            # todo set seeklock rule if seek == False
            liz = xbmcgui.ListItem('Seek Test', path=file)
            liz.setProperty('startoffset', str(int(dur//8)))
            infoTag = ListItemInfoTag(liz, 'video')
            infoTag.set_resume_point({'ResumeTime':int(dur/4),'TotalTime':int(dur/4)})
        
            getTime  = 0
            waitTime = 30
            PLAYER.play(file, liz, windowed=True)
            while not MONITOR.abortRequested():
                waitTime -= 1
                if MONITOR.waitForAbort(1.0) or waitTime < 1: break
                elif not PLAYER.isPlaying(): continue
                elif ((int(PLAYER.getTime()) > getTime) or BUILTIN.getInfoBool('SeekEnabled','Player')):
                    PLAYER.stop()
                    return True
            PLAYER.stop()
            return False
            
        def _vfs(path, citem):
            if isRadio({'path':[path]}) or isMixed({'path':[path]}): return True
            else:
                valid = False
                media = 'music' if isRadio({'path':[path]}) else 'video'
                dia   = DIALOG.progressDialog(message='%s %s, %s..\n%s'%(LANGUAGE(32098),'Path',LANGUAGE(32099),path))
                with busy_dialog():
                    items = self.jsonRPC.walkFileDirectory(path, media, depth=5, retItem=True)
                
                for idx, dir in enumerate(items):
                    if MONITOR.waitForAbort(.001): break
                    else:
                        item = random.choice(items.get(dir,[]))
                        dia  = DIALOG.progressDialog(int((idx*100)//len(items)),control=dia, message='%s %s...\n%s\n%s'%(LANGUAGE(32098),'Path',dir,item.get('file','')))
                        item.update({'duration':self.jsonRPC.getDuration(item.get('file'), item, accurate=True)})
                        if item.get('duration',0) == 0: continue
                        dia = DIALOG.progressDialog(int((idx*100)//len(items)),control=dia, message='%s %s...\n%s\n%s'%(LANGUAGE(32098),'Seeking',dir,item.get('file','')))
                        if _seek(item, citem):
                            self.log('_vfs, found playable and seek-able file %s'%(item.get('file')))
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
                return self.setID(self.setLogo(citem.get('name'),citem))
            
        channelList = sorted(filter(None,[_validate(channel) for channel in channelList]), key=lambda k: k['number'])
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
        # [self.buildFileList(citem, file, 'video', roundupDIV(self.limit,len(citem['path'])), self.sort, self.limits) for file in citem['path'] if not self.myService._interrupt()]


    def getMontiorList(self):
        self.log('getMontiorList')
        try:
            itemLST = [self.buildListItem(cleanLabel(value).title(),icon=ICON) for info in DIALOG.getInfoMonitor() for key, value in info.items() if value not in ['','..'] and key not in ['path','logo']]
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
            self.channels.setChannels(self.validateChannels(self.newChannels))
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
        retval = int(DIALOG.inputDialog(LANGUAGE(32137), key=xbmcgui.INPUT_NUMERIC, opt=citem['number']))
        if retval and (retval > 0 and retval < CHANNEL_LIMIT) and retval != channelPOS + 1:
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
                retval = DIALOG.browseDialog(type=1,heading='%s (%s)'%(LANGUAGE(32066).split('[CR]')[0],chname),default=channelData.get('icon',''), shares='files',mask=xbmc.getSupportedMedia('picture'),prompt=False)
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
                                                     customlabel = LANGUAGE(32069)) #Auto
                                             
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
        if self.madeChanges: forceUpdateTime('chkChannels')
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
                citem = loadJSON(sitem.getProperty('citem'))
                chnum = (citem.get('number') or literal_eval(cleanLabel(sitem.getLabel())) or (spos+1))
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
            self.log('onAction: actionId = %s'%(actionId))
            if actionId in ACTION_PREVIOUS_MENU:
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
            if   focusItems['label'] == LANGUAGE(32062): self.closeManager()#Close
            elif focusItems['label'] == LANGUAGE(32059): self.saveChannels()#Save 
            elif focusItems['label'] == LANGUAGE(32063):#OK
                if   self.isVisible(self.itemList) and self.madeChanges: self.saveChannelItems(focusItems.get('citem'))
                # elif self.isVisible(self.ruleList):                      self.toggleruleList(False)
                else:                                                    self.togglechanList(True,focus=focusItems.get('position'))
        elif controlId == 9002: #dynamic button
            if focusItems['label'] == LANGUAGE(32060):#Cancel
                if   self.isVisible(self.chanList) and self.madeChanges: self.saveChanges()
                # elif self.isVisible(self.ruleList):                      self.toggleruleList(False)
                else:                                                    self.togglechanList(True,focus=focusItems.get('position'))
        elif controlId == 9003: #dynamic button
            if focusItems['label'] == LANGUAGE(32136):self.moveChannel(focusItems.get('citem'),focusItems.get('position'))#Move 
        elif controlId == 9004: #dynamic button
            if focusItems['label'] == LANGUAGE(32061): self.clearChannel(focusItems.get('citem'))#Delete