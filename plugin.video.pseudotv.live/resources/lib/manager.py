  # Copyright (C) 2026 Lunatixz


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

from variables    import *
from cache      import Cache, cacheit
from library    import Library 
from channels   import Channels
from jsonrpc    import JSONRPC
from rules      import RulesList
from resources  import Resources
from multiroom  import Multiroom
from xsp        import XSP
from builder    import Builder
from predefined import Predefined
from backup     import Backup
from cache      import Cache
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
    focusItems     = {}
    chanList       = xbmcgui.ControlList
    itemList       = xbmcgui.ControlList
    monitor        = MONITOR()
    lastActionTime = time.time()
    
    def __init__(self, *args, **kwargs):
        self.log('__init__, running = %s'%(Globals.properties.isRunning('Manager')))
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)    

        def __loadChannels(name=Globals.settings.getSetting('Default_Channels')): #load local or remote channel configurations
            self.log('__loadChannels, name = %s, local = %s'%(name, self.friendly))
            self.oldChannels = self.channels.getChannels()
            if name == self.friendly or not kwargs.get('start', False): 
                return self.oldChannels #Local
            elif name == LANGUAGE(30022): #Auto
                if len(self.oldChannels) > 0: 
                    return self.oldChannels 
                else:                         
                    return __loadChannels(LANGUAGE(32069))
            elif name == LANGUAGE(32069): #Ask
                def __buildItem(server):
                    online_state = server.get('online', False)
                    color = 'green' if online_state else 'red'
                    status_text = LANGUAGE(32158) if online_state else LANGUAGE(32253)
                    
                    label2 = '%s - %s: Channels (%s)' % (
                        LANGUAGE(32211) % (color, status_text),
                        server.get('host'),
                        len(server.get('channels', []))
                    )
                    return Globals.listitems.buildMenuListItem(
                        server.get('name'),
                        label2,
                        icon=Globals._getDummyIcon(str(servers.index(server) + 1))
                    )
                
                lizLST  = []
                serLST  = Multiroom().getServers()
                servers = [value for key, value in serLST.items() if value.get('online', False)]
                if servers: 
                    lizLST.extend(poolit(__buildItem)(servers))
                
                lizLST.insert(0, Globals.listitems.buildMenuListItem(
                    self.friendly,
                    '%s - %s: Channels (%s)' % ('[B]Local[/B]', self.host, len(self.oldChannels)),
                    icon=ICON
                ))
                
                select = Globals.dialog.selectDialog(lizLST, '%s for Channel Setup' % (LANGUAGE(30173)), None, True, SELECT_DELAY, False)
                if select is not None: 
                    return __loadChannels(lizLST[select].getLabel())
                else:                  
                    return
            elif name:
                self.server = Multiroom().getServers().get(name, {})
                return self.server.get('channels', [])
            return self.oldChannels

        with Globals.builtin.busy_dialog(lock=True):
            self.server         = {}
            self.cntrlStates    = {}
            
            self.madeChanges    = False
            self.madeItemchange = False
            self.showingList    = True
            self.EPGArtwork     = int((Globals.settings.getSetting('EPG_Artwork') or "0"))
            
            self.cache          = Cache(mem_cache=True)
            self.channels       = Channels(writable=True)
            self.rule           = RulesList()
            self.jsonRPC        = JSONRPC()
            self.resources      = Resources()
            self.backup         = Backup(channels=self.channels)

            self.host           = Globals.properties.getRemoteHost()
            self.friendly       = Globals.properties.getFriendlyName()
            self.hasBackups     = Globals.properties.hasBackups()
            self.newChannel     = self.channels.getTemplate()
            
        try:
            with Globals.builtin.busy_dialog(lock=True):
                self.channelList   = self.channels.sortChannels(self.createChannelList(list(self.buildArray()), __loadChannels()))
                self.newChannels   = self.channelList.copy()
                self.openChannel   = kwargs.get('open')
                self.launchManager = kwargs.get('start', True)
                self.startChannel  = self._findAvailChannel(kwargs.get('channel', -1))
                self.focusIndex    = (self.startChannel - 1) #Convert from channel number to list index ie. channel 1 => index 0
                
                if self.openChannel: 
                    self.openChannel = self.channelList[self.focusIndex]
                
                self.log('Manager, startChannel = %s, focusIndex = %s, openChannel = %s' % (self.startChannel, self.focusIndex, self.openChannel))
                if self.launchManager and not Globals.properties.isRunning('Manager'):
                    with Globals.properties.chkRunning('Manager'):
                        self.doModal()
        except Exception as e: 
            self.log('Manager failed! %s' % (e), xbmc.LOGERROR)
            self.closeManager()

    def log(self, msg, level=xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)

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
            self.fillChanList(self.newChannels, focus=self.focusIndex, channel=self.openChannel)
            self.log('onInit, backup=%s' % self.backup.backupChannels(CHANNELLATEST_KEY, silent=True))
        except Exception as e: 
            LOG("Manager.onInit failed: %s" % (e), xbmc.LOGERROR)
            self.closeManager()

    def _findAvailChannel(self, start=-1):
        if start == -1: 
            for channel in self.channelList:
                if not channel.get('id'): 
                    return channel.get('number')
        return start

    @cacheit(checksum=lambda: Globals.properties.getProcessID())
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
            if item.get("number", 0) > 0:
                channelArray[item["number"] - 1].update(item) #CUSTOM
            
        checksum  = Globals.properties.getProcessID()
        cacheName = 'createChannelList.%s' % (checksum)
        try:   
            cacheResponse = list(self.cache.get(cacheName, checksum=checksum))
        except Exception:
            cacheResponse = []
            
        if not cacheResponse:
            poolit(__update)(channelList)
            cacheResponse = self.cache.set(cacheName, channelArray, checksum=checksum, expiration=datetime.timedelta(seconds=5))
        return cacheResponse

    def fillChanList(self, channelList, refresh=False, focus=None, channel=None):
        self.log('fillChanList, focus = %s, channel = %s' % (focus, channel))
        def __buildItem(citem):
            isFavorite    = citem.get('favorite', False)
            isLocked      = False #todo parse channel lock rule
            isSeasonal    = citem.get('path', []) == ["{Seasonal}"]
            channelColor  = COLOR_UNAVAILABLE_CHANNEL
            labelColor    = COLOR_UNAVAILABLE_CHANNEL
            
            if citem.get("path"):
                labelColor = COLOR_AVAILABLE_CHANNEL
                if   isLocked:       channelColor = COLOR_LOCKED_CHANNEL
                elif isFavorite:     channelColor = COLOR_FAVORITE_CHANNEL
                elif Globals._isRadio(citem): channelColor = COLOR_RADIO_CHANNEL
                elif not isSeasonal: channelColor = COLOR_AVAILABLE_CHANNEL
                
            return Globals.listitems.buildMenuListItem(
                '[COLOR=%s][B]%s|[/COLOR][/B]' % (channelColor, citem["number"]),
                '[COLOR=%s]%s[/COLOR]' % (labelColor, citem.get("name", '')),
                citem.get("logo", LOGO_COLOR),
                '|'.join(citem.get("path", [])),
                props={
                    'citem': citem,
                    'chname': citem["name"],
                    'chnum': '%i' % (citem["number"]),
                    'radio': citem.get('radio', False),
                    'description': LANGUAGE(32169) % (citem["number"], self.server.get('name', self.friendly))
                }
            )
                
        self.togglechanList(reset=refresh)
        with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
            lizLST = poolit(__buildItem)(channelList)
            self.chanList.addItems(lizLST)
            if focus is None: 
                self.selItem(self.chanList, self.setFocusPOS(lizLST))
            else:             
                self.selItem(self.chanList, focus)
            self.setFocus(self.chanList)
            if channel: 
                self.buildChannelItem(channel)

    def isLocked(self):
        return Globals.properties.getProperty('Manager.isLocked', False)
        
    def setLocked(self, state=True):
        try: 
            color = "0xC0FF0000" if state else "0xFFFFFFFF"
            self.getControl(41).setColorDiffuse(color)
            Globals.properties.setProperty('Manager.isLocked', state)
        except Exception as e: 
            self.log('setLocked failed: %s' % e, xbmc.LOGDEBUG)

    @contextmanager
    def toggleSpinner(self, state=True, lock=True, condition=None):
        self.log('toggleSpinner, state = %s, condition = %s, lock = %s' % (state, condition, lock))
        if self.launchManager:
            if condition is not None and condition:
                Globals.properties.setRunning('Manager.toggleSpinner', state)
                self.setVisibility(self.spinner, state)
                if lock: 
                    self.setLocked(True)
                try: 
                    yield
                finally:
                    if self.isLocked(): 
                        self.setLocked(False)
                    self.setVisibility(self.spinner, False)
                    Globals.properties.setRunning('Manager.toggleSpinner', False)
            else: 
                yield
        else:
            with Globals.builtin.busy_dialog(not bool(condition), lock):
                yield

    def togglechanList(self, state=True, focus=0, reset=False):
        self.log('togglechanList, state = %s, focus = %s, reset = %s' % (state, focus, reset))
        with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
            if state and hasattr(self.chanList, 'reset'): # channellist
                if reset: 
                    self.setVisibility(self.chanList, False)
                    self.chanList.reset()
                    
                self.setVisibility(self.itemList, False)
                self.setVisibility(self.chanList, True)
                self.setFocus(self.chanList)
                self.selItem(self.chanList, focus)
                
                if self.madeChanges:
                    #1 Save
                    self.setLabels(self.right_button1, LANGUAGE(32059))
                    self.setEnableCondition(self.right_button1, '')
                    #2 Cancel
                    self.setLabels(self.right_button2, LANGUAGE(32060))
                    self.setEnableCondition(self.right_button2, '')
                    #3 Move
                    self.setLabels(self.right_button3, LANGUAGE(32136))
                    self.setEnableCondition(self.right_button3, '[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chname))]')
                    #4 Delete
                    self.setLabels(self.right_button4, LANGUAGE(32061))
                    self.setEnableCondition(self.right_button4, '[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chname))]')
                else:
                    #1 Close
                    self.setLabels(self.right_button1, LANGUAGE(32062))
                    self.setEnableCondition(self.right_button1, '')
                    #2 AutoTune / Predefined
                    if len(self.oldChannels) == 0: 
                        self.setLabels(self.right_button2, LANGUAGE(30038))
                        self.setEnableCondition(self.right_button2, '[String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chname))]')
                    else:
                        self.setLabels(self.right_button2, LANGUAGE(30229))
                        self.setEnableCondition(self.right_button2, '[String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chname))]')
                    #3 Recover / Move
                    if len(self.oldChannels) == 0: 
                        if self.hasBackups: 
                            self.setLabels(self.right_button3, LANGUAGE(32112))
                        self.setEnableCondition(self.right_button3, '[String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chname))]')
                    else: 
                        self.setLabels(self.right_button3, LANGUAGE(32136))
                        self.setEnableCondition(self.right_button3, '[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chname))]')
                    #4 Delete
                    self.setLabels(self.right_button4, LANGUAGE(32061))
                    self.setEnableCondition(self.right_button4, '[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Property(chname))]')

                self.setFocus(self.right_button1)
            elif hasattr(self.itemList, 'reset'): # channelitems
                self.itemList.reset()
                self.setVisibility(self.chanList, False)
                self.setVisibility(self.itemList, True)
                self.selItem(self.itemList, focus)
                self.setFocus(self.itemList)
                
                if self.madeItemchange:
                    self.setLabels(self.right_button1, LANGUAGE(32240)) #Confirm
                    self.setLabels(self.right_button2, LANGUAGE(32060)) #Cancel
                    self.setEnableCondition(self.right_button1, '[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Label) + !String.IsEmpty(Container(6).ListItem(Container(6).Position).Path)]')
                    self.setEnableCondition(self.right_button2, '[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Property(chnum))]')
                else:
                    self.setLabels(self.right_button1, LANGUAGE(32062)) #Close
                    self.setLabels(self.right_button2, LANGUAGE(32060)) #Cancel
                    self.setEnableCondition(self.right_button1, '[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Property(chnum))]')
                    self.setEnableCondition(self.right_button2, '[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Path)]')
                    
                self.setLabels(self.right_button3, LANGUAGE(32235)) #Preview
                self.setLabels(self.right_button4, LANGUAGE(32239)) #Clear
                self.setEnableCondition(self.right_button3, '[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Path) + String.IsEqual(Container(6).ListItem(Container(6).Position).Property(radio),False)]')
                self.setEnableCondition(self.right_button4, '[!String.IsEmpty(Container(6).ListItem(Container(6).Position).Path)]')

    def setFocusPOS(self, listitems, chnum=None, ignore=True):
        for idx, listitem in enumerate(listitems):
            chnumber = int(Globals._cleanLabel(listitem.getLabel()).strip('|'))
            if ignore and chnumber > CHANNEL_LIMIT: 
                continue
            elif chnum is not None and chnum == chnumber: 
                return idx
            elif chnum is None and Globals._cleanLabel(listitem.getLabel2()): 
                return idx
        return 0
           
    def selItem(self, cntrl, focus=0):
        try: 
            cntrl.selectItem(focus)
        except Exception as e: 
            self.log('selItem failed: %s' % e, xbmc.LOGDEBUG)
           
    def getRuleAbbr(self, citem, myId, optionindex):
        value = citem.get('rules', {}).get(myId, {}).get('values', {}).get(optionindex)
        self.log('getRuleAbbr, id = %s, myId = %s, optionindex = %s, optionvalue = %s' % (citem.get('id', -1), myId, optionindex, value))
        return value

    def getLogoColor(self, citem):
        self.log('getLogoColor, id = %s' % (citem.get('id', -1)))
        if (citem.get('logo') and citem.get('name')) is None: 
            return 'FFFFFFFF'
        elif citem.get('rules', {}).get(1):
            if self.getRuleAbbr(citem, 1, 4) or self.resources.isMono(citem['logo']):
                return self.getRuleAbbr(citem, 1, 3)
        return Globals.settings.getSetting('ChannelBug_Color')
        
    def buildChannelItem(self, citem: dict={}, focuskey: str='path'):
        self.log('buildChannelItem, id = %s, focuskey = %s' % (citem.get('id'), focuskey))
        def __buildItem(key):
            key   = key.lower()
            value = citem.get(key, ' ')
            if key in ["number", "type", "logo", "id", "catchup"]: 
                return # keys to ignore, internal use only.
            elif isinstance(value, (list, dict)): 
                if   key == "group": value = ('|'.join(sorted(set(value))) or LANGUAGE(30127))
                elif key == "path" : value = '|'.join(value)
                elif key == "rules": value = '|'.join([rule.name for k, rule in self.rule.loadRules([citem]).get(citem['id'], {}).items()])
            elif not isinstance(value, str): 
                value = str(value)
            elif not value: 
                value = ' '
                
            return Globals.listitems.buildMenuListItem(
                LABEL.get(key, ' '),
                value,
                citem.get('logo', LOGO_COLOR),
                '|'.join(citem.get('path', [])),
                props={
                    'key': key,
                    'value': value,
                    'citem': citem,
                    'chname': citem["name"],
                    'chnum': '%i' % (citem["number"]),
                    'radio': citem.get('radio', False),
                    'description': DESC.get(key, ''),
                    'colorDiffuse': self.getLogoColor(citem)
                }
            )

        self.togglechanList(False)
        LABEL = {
            'name'    : LANGUAGE(32092),
            'path'    : LANGUAGE(32093),
            'group'   : LANGUAGE(32094),
            'rules'   : LANGUAGE(32095),
            'radio'   : LANGUAGE(32091),
            'favorite': LANGUAGE(32090),
            'enable'  : LANGUAGE(30184),
            'changed' : LANGUAGE(32259)
        }
                 
        DESC = {
            'name'    : LANGUAGE(32085),
            'path'    : LANGUAGE(32086),
            'group'   : LANGUAGE(32087),
            'rules'   : LANGUAGE(32088),
            'radio'   : LANGUAGE(32084),
            'favorite': LANGUAGE(32083),
            'enable'  : LANGUAGE(33184),
            'changed' : LANGUAGE(33259)
        }

        lizLST = []
        lizLST.extend(poolit(__buildItem)(list(self.newChannel.keys())))
        self.itemList.addItems(lizLST)
        self.itemList.selectItem([idx for idx, liz in enumerate(lizLST) if liz.getProperty('key') == focuskey][0])
        self.setFocus(self.itemList)

    def itemInput(self, channelListItem=xbmcgui.ListItem()):
        def __getName(citem: dict={}, name: str=''):
            return Globals.dialog.inputDialog(message=LANGUAGE(32079), default=name), citem
       
        def __getPath(citem: dict={}, paths: list=[]):
            return self.getPaths(citem, paths)
        
        def __getRule(citem: dict={}, rules: dict={}):
            return self.getRules(citem, rules)
            
        def __getBool(citem: dict={}, state: bool=False):
            return not bool(state), citem

        def __getGroups(citem: dict={}, groups: list=[]):
            groups  = list([_f for _f in groups if _f])
            ngroups = sorted([_f for _f in set(Globals.settings.getSetting('User_Groups').split('|') + GROUP_TYPES + groups) if _f])
            ngroups.insert(0, '-%s' % (LANGUAGE(30064)))
            selects = Globals.dialog.selectDialog(ngroups, header=LANGUAGE(32081), preselect=Globals._findItemsInLST(ngroups, groups), useDetails=False)
            if selects is not None:
                if 0 in selects:
                    Globals.settings.setSetting('User_Groups', Globals.dialog.inputDialog(LANGUAGE(32044), default=Globals.settings.getSetting('User_Groups')))
                    return __getGroups(citem, groups)
                elif len(ngroups) > 0: 
                    groups = [ngroups[idx] for idx in selects]
            if not groups: 
                groups = [LANGUAGE(30127)]
            return groups, citem
        
        key   = channelListItem.getProperty('key')
        value = channelListItem.getProperty('value')
        citem = FileAccess.loadJSON(channelListItem.getProperty('citem'))
        self.log('itemInput, In value = %s, key = %s\ncitem = %s' % (value, key, citem))
        
        KEY_INPUT = {
            "name"     : {'func': __getName,   'kwargs': {'citem': citem, 'name': citem.get('name', '')}},
            "path"     : {'func': __getPath,   'kwargs': {'citem': citem, 'paths': citem.get('path', [])}},
            "group"    : {'func': __getGroups, 'kwargs': {'citem': citem, 'groups': citem.get('group', [])}},
            "rules"    : {'func': __getRule,   'kwargs': {'citem': citem, 'rules': self.rule.loadRules([citem]).get(citem['id'], {})}},
            "radio"    : {'func': __getBool,   'kwargs': {'citem': citem, 'state': citem.get('radio', False)}},
            "favorite" : {'func': __getBool,   'kwargs': {'citem': citem, 'state': citem.get('favorite', False)}},
            "enable"   : {'func': __getBool,   'kwargs': {'citem': citem, 'state': citem.get('enable', False)}},
            "changed"  : {'func': __getBool,   'kwargs': {'citem': citem, 'state': citem.get('changed', False)}}
        }
              
        action = KEY_INPUT.get(key) 
        retval, citem = action['func'](*action.get('args', ()), **action.get('kwargs', {}))
        retval, citem = self.validateInputs(key, retval, citem)
        if retval is not None:
            citem['changed']    = value != retval
            self.madeItemchange = value != retval
            if key in self.newChannel: 
                citem[key] = retval
            self.log('itemInput, Out value = %s, key = %s\ncitem = %s' % (retval, key, citem))
        return citem
   
    def getPaths(self, citem: dict={}, paths: list=[]):
        def __buildItem(path):
            return Globals.listitems.buildMenuListItem('', path, url='|'.join([path]), icon=Globals._getDummyIcon(str(pathLST.index(path) + 1)), props={'citem': citem, 'idx': pathLST.index(path) + 1})
        
        select  = -1
        lastOPT = None
        epaths  = paths.copy()
        pathLST = list([_f for _f in paths if _f])
        
        if not citem.get('radio', False) and Globals._isRadio({'path': paths}): 
            citem['radio'] = True 
        excLST = [10, 12, 21, 22] if citem.get('radio', False) else [11, 13, 21]
        
        while not self.monitor.abortRequested() and select is not None:
            with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
                npath  = None
                lizLST = poolit(__buildItem)(pathLST) if pathLST else []
                lizLST.append(Globals.listitems.buildMenuListItem('', LANGUAGE(33113), icon=Globals._getDummyIcon(str(len(pathLST) + 1)), props={'key': 'add', 'citem': citem, 'idx': 0}))
                if len(pathLST) > 0 and epaths != pathLST: 
                    lizLST.insert(0, Globals.listitems.buildMenuListItem('[B]%s[/B]' % (LANGUAGE(32059)), LANGUAGE(33114), icon=ICON, props={'key': 'save', 'citem': citem}))
                
            select = Globals.dialog.selectDialog(lizLST, header=LANGUAGE(32086), preselect=lastOPT, multi=False)
            if select is not None:
                with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
                    key, path = lizLST[select].getProperty('key'), lizLST[select].getPath()
                    try:    
                        lastOPT = int(lizLST[select].getProperty('idx'))
                    except Exception: 
                        lastOPT = None
                        
                    if key == 'add': 
                        retval = Globals.dialog.browseSources(heading=LANGUAGE(32080), exclude=excLST, monitor=True)
                        if retval is not None:
                            npath, citem = self.validatePaths(retval, citem)
                            if npath: pathLST.append(npath)
                    elif key == 'save': 
                        paths = pathLST
                        break
                    elif path in pathLST:
                        retval = Globals.dialog.yesnoDialog(LANGUAGE(32102), customlabel=LANGUAGE(32103))
                        if retval in [1, 2]: 
                            pathLST.pop(pathLST.index(path))
                        if retval == 2:
                            npath, citem = self.validatePaths(Globals.dialog.browseSources(heading=LANGUAGE(32080), default=path, monitor=True, exclude=excLST), citem)
                            pathLST.append(npath)
        self.log('getPaths, paths = %s' % (paths))
        return paths, citem

    def getRules(self, citem: dict={}, rules: dict={}):
        def __buildItem(data):
            return Globals.listitems.buildMenuListItem(data[1].name, data[1].getTitle(), icon=Globals._getDummyIcon(str(data[1].myId)), props={'myId': data[1].myId, 'citem': citem, 'idx': list(ruleLST.keys()).index(data[0]) + 1}) 
        
        if citem.get('id') is None or len(citem.get('path', [])) == 0: 
            Globals.dialog.notificationDialog(LANGUAGE(32071))
            return rules, citem
        else:            
            select  = -1
            erules  = rules.copy()
            ruleLST = rules.copy()
            lastIDX = None
            lastXID = None
            while not self.monitor.abortRequested() and select is not None:
                with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
                    nrule  = None
                    crules = self.rule.loadRules([citem], append=True).get(citem['id'], {}) 
                    arules = [rule for key, rule in crules.items() if not ruleLST.get(key)] 
                    lizLST = []
                    lizLST.extend(poolit(__buildItem)([(key, rule) for key, rule in ruleLST.items() if rule.myId]))
                    lizLST.insert(0, Globals.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]' % (LANGUAGE(32173)), "", icon=ICON, props={'key': 'add', 'citem': citem, 'idx': 0}))
                    if len(ruleLST) > 0 and erules != ruleLST: 
                        lizLST.insert(1, Globals.listitems.buildMenuListItem('[COLOR=white][B]%s[/B][/COLOR]' % (LANGUAGE(32174)), "", icon=ICON, props={'key': 'save', 'citem': citem}))
                            
                select = Globals.dialog.selectDialog(lizLST, header=LANGUAGE(32095), preselect=lastIDX, multi=False)
                if select is not None:
                    key, myId = lizLST[select].getProperty('key'), int(lizLST[select].getProperty('myId') or '-1')
                    try:    
                        lastIDX = int(lizLST[select].getProperty('idx'))
                    except Exception: 
                        lastIDX = None
                        
                    if key == 'add':
                        with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
                            lizLST = [Globals.listitems.buildMenuListItem(rule.name, rule.description, icon=Globals._getDummyIcon(rule.myId), props={'idx': idx, 'myId': rule.myId, 'citem': citem}) for idx, rule in enumerate(arules) if rule.myId]
                        select = Globals.dialog.selectDialog(lizLST, header=LANGUAGE(32072), preselect=lastXID, multi=False)
                        with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
                            try:    
                                lastXID = int(lizLST[select].getProperty('idx'))
                            except Exception: 
                                lastXID = -1
                            nrule, citem = self.getRule(citem, arules[lastXID])
                            if nrule is not None: 
                                ruleLST.update({str(nrule.myId): nrule})
                    elif key == 'save':
                        rules = ruleLST
                        break
                    elif ruleLST.get(str(myId)):
                        with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
                            retval = Globals.dialog.yesnoDialog(LANGUAGE(32175), customlabel=LANGUAGE(32176))
                            if retval in [1, 2]: 
                                ruleLST.pop(str(myId))
                            if retval == 2: 
                                nrule, citem = self.getRule(citem, crules.get(myId, {}))
                                if nrule is not None: 
                                    ruleLST.update({nrule.myId: nrule})
            self.log('getRules, rules = %s' % (len(rules)))
            return self.rule.dumpRules(rules), citem

    def getRule(self, citem={}, rule={}):
        self.log('getRule, name = %s' % (rule.name))
        select = -1
        while not self.monitor.abortRequested() and select is not None:
            with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
                lizLST = [Globals.listitems.buildMenuListItem('%s = %s' % (rule.optionLabels[idx], rule.optionValues[idx]), rule.optionDescriptions[idx], Globals._getDummyIcon(idx + 1), [rule.myId], {'value': optionValue, 'idx': idx, 'myId': rule.myId, 'citem': citem}) for idx, optionValue in enumerate(rule.optionValues)]
            select = Globals.dialog.selectDialog(lizLST, header='%s %s - %s' % (LANGUAGE(32176), rule.myId, rule.name), multi=False)
            if select is not None:
                try: 
                    rule.onAction(int(lizLST[select].getProperty('idx') or "0"))
                except Exception as e:
                    self.log("getRule, onAction failed! %s" % (e), xbmc.LOGERROR)
                    Globals.dialog.okDialog(LANGUAGE(32000))
        return rule, citem
        
    def setID(self, citem: dict={}) -> dict:
        if not citem.get('id') and citem.get('name') and citem.get('path') and citem.get('number'): 
            citem['id'] = Globals._getChannelID(citem['name'], citem['path'], citem['number'], Globals.settings.getMYUUID())
            self.log('setID, id = %s' % (citem['id']))
        return citem
       
    def setName(self, path, citem: dict={}) -> dict:
        with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
            if citem.get('name'): 
                return citem
            elif path.strip('/').endswith(('.xml', '.xsp')):            
                citem['name'] = XSP().getName(path)
            elif path.startswith(tuple(DB_TYPES + WEB_TYPES + VFS_TYPES)): 
                citem['name'] = self.getMontiorList().getLabel()
            else:                                                                     
                citem['name'] = os.path.basename(os.path.dirname(path)).strip('/')
            self.log('setName, id = %s, name = %s' % (citem['id'], citem['name']))
            return citem

    def setLogo(self, name=None, citem={}, force=False):
        name = (name or citem.get('name'))
        if name:
            logo = '' if force else citem.get('logo')
            if not logo or logo in [LOGO, LOGO_COLOR, ICON]:
                with self.toggleSpinner(condition=(Globals.properties.isRunning('Manager.toggleSpinner') == False)):
                    citem['logo'] = self.resources.getLogo(citem, fallback=self.resources.getImageCache(citem['name']))
        self.log('setLogo, id = %s, logo = %s, force = %s' % (citem.get('id'), citem.get('logo'), force))
        return citem
       
    def validateInputs(self, key, value, citem):
        self.log('validateInputs, key = %s, value = %s' % (key, value))
        def __validateName(name, citem):
            if name and (1 < len(name) < 128): 
                citem['name'] = Globals._validString(name)
                self.log('__validateName, name = %s' % (citem['name']))
                return citem['name'], self.setLogo(name, citem, force=True)
            return None, citem

        def __validatePath(paths, citem):
            if len(paths) > 0:
                for path in paths:
                    name, citem = __validateName(citem.get('name', ''), self.setName(path, citem))
                    self.log('__validatePath, name = %s, path = %s' % (name, path))
                    if name: return paths, citem
            return None, citem

        def __validateGroup(groups, citem):
            return groups, Globals._cleanGroups(citem)
                   
                   
        def __validateRules(rules, citem):
            return rules, citem

        VALIDATORS = {
            "name" : __validateName,
            "path" : __validatePath,
            "group": __validateGroup,
            "rules": __validateRules
        }
        
        validator = VALIDATORS.get(key, lambda val, item: (val, item))
        return validator(value, citem)
            
            
    def validatePaths(self, path, citem):
        def __convert(path): #convert videodb:// paths to dynamic xsp thru. predefined
            paths = [path]
            if path.lower().startswith('videodb://'):
                if   'tvshows/titles'  in path: paths = Predefined.createShowPlaylist(self.jsonRPC.DBIDtoLabel(path))
                elif 'tvshows/studios' in path: paths = Predefined.createNetworkPlaylist(self.jsonRPC.DBIDtoLabel(path))
                elif 'tvshows/genres'  in path: paths = Predefined.createTVGenrePlaylist(self.jsonRPC.DBIDtoLabel(path))
                elif 'movies/genres'   in path: paths = Predefined.createMovieGenrePlaylist(self.jsonRPC.DBIDtoLabel(path))
                elif 'movies/studios'  in path: paths = Predefined.createStudioPlaylist(self.jsonRPC.DBIDtoLabel(path))
            return paths

        def __vfs(path, citem, cnt=3):
            def __fileList(citem, fileList=[]):
                return Globals.properties.preemptActivity('%s %s\n%s'%(LANGUAGE(32098),LANGUAGE(32093),LANGUAGE(32140)), Builder().buildVideo, *(citem,True))

            with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                if Globals._isRadio({'path':[path]}): return True
                Globals.dialog.notificationDialog('%s %s\n%s'%(LANGUAGE(32098),LANGUAGE(32093),LANGUAGE(32140)))
                tmpcitem = citem.copy()
                tmpcitem.update({'name':FileAccess._getMD5(citem['path']),'path':[path]})
                tmpcitem['id'] = Globals._getChannelID(tmpcitem['name'], tmpcitem['path'], random.randrange(1, CHANNEL_LIMIT, 1), 'validatePaths')
                fileList = __fileList(tmpcitem)
                if fileList:
                    while not self.monitor.abortRequested() and cnt > 0:
                        if __seek(random.choice(fileList)): return Globals.dialog.notificationDialog(f'{LANGUAGE(32098)} {LANGUAGE(32093)}: [B]PASSED![/B]')
                        else:
                            retval = Globals.dialog.yesnoDialog(LANGUAGE(30202),customlabel='Try Again (%s)'%(cnt))
                            if   retval == 1: return Globals.dialog.notificationDialog('%s %s: [B]OVERRIDE![/B]'%(LANGUAGE(32098),LANGUAGE(32093)))
                            elif retval == 2: cnt -=1
                            else: break
                self.log('validatePaths, __vfs: path = %s fileList = %s'%(path,len(fileList) if isinstance(fileList,list) else fileList))
                return not bool(Globals.dialog.notificationDialog('%s %s: [B]FAILED![/B]'%(LANGUAGE(32098),LANGUAGE(32093))))
                
        def __seek(item, passed=False, wait=30):
            player = PLAYER()
            if player.isPlaying(): return Globals.dialog.notificationDialog('%s %s\n%s'%(LANGUAGE(32098),LANGUAGE(32093),LANGUAGE(30136)))
            else:
                # todo test seek for support disable via adv. rule if fails.
                # todo set seeklock rule if seek == False
                duration = item.get('duration',item.get('realtime',0))
                resume   = abs(int(duration/8))
                liz = xbmcgui.ListItem('Seek Test', path=item.get('file'))
                liz.setProperty('startoffset', str(resume))
                infoTag = ListItemInfoTag(liz, 'video')
                infoTag.set_resume_point({'ResumeTime':resume,'TotalTime':int(duration*60)})
                player.play(item.get('file'),liz)
                
                while not self.monitor.abortRequested():
                    if   self.monitor.waitForAbort(1.0) or wait < 1: break
                    elif player.isPlaying():
                        self.log('validatePaths, _seek: playing %s seeking to %s'%(item.get('file'),resume))
                        if ((int(player.getTime()) >= resume) or Globals.builtin.getInfoBool('Player.SeekEnabled')):
                            passed = True
                            break
                    else: wait -= 1
                    
                if player.isPlaying():
                    player.stop()
                    
            del player
            self.log('validatePaths, _seek: passed = %s'%(passed))
            return passed
            
        def __set(path, citem):
            citem = self.setName(path, citem)
            return path, self.setLogo(citem.get('name'),citem)
            
        if path: 
            paths = __convert(path)
            self.log(f'validatePaths, paths = {paths}')
            if any(citem for path in paths if __vfs(path, citem)): return __set(path, citem)
        return None, citem


    def autoRecovery(self):
        self.log('autoRecovery')
        if Globals.dialog.yesnoDialog(LANGUAGE(32101)):
            with Globals.builtin.busy_dialog():
                key = self.backup.selectBackups()
                channels = self.backup.recoverChannels(key)
                self.log('autoRecovery, file = %s, channels = %s'%(key, len(channels)))
                number = 1
                for channel in channels:
                    number = channel.get('number',0)
                    if number > 0: 
                        self.madeChanges = True
                        self.newChannels.insert(number-1,channel)
                if self.madeChanges and self.launchManager: self.fillChanList(self.newChannels,True,focus=(number-1))


    def getLibrary(self, type=None):
        return Library().getLibrary(type)


    def clrLibrary(self):
        return Library().clrLibraryCache()


    def autoTune(self, start=1):
        with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
            try:
                if Globals.dialog.yesnoDialog(LANGUAGE(32100)):   
                    Globals.settings.setAutotuned(True)
                    items = []
                    for idx, type in enumerate(AUTOTUNE_TYPES):
                        try:
                            samples = self.getLibrary(type)
                            items.extend([s for s in samples if s])
                        except Exception as e: self.log('autoTune getLibrary(%s) failed: %s' % (type, e), xbmc.LOGDEBUG)
                    self._addChannels(start, Globals._randomSamples(items,AUTOTUNE_LIMIT))
            except Exception as e: self.log("autoTune, failed! %s"%(e), xbmc.LOGERROR)


    def selectPredefined(self, start=1):
        def __buildMenuItem(citem):
            return Globals.listitems.buildMenuListItem(citem['name'],citem['type'],citem['logo'],'|'.join(citem['path']),props={'citem':citem})
        try:
            with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                items = self.getLibrary()
                types = [Globals.listitems.buildMenuListItem(type,icon=Globals._getDummyIcon(type)) for type in (list(items.keys()))]
            
            type = types[Globals.dialog.selectDialog(types, header=ADDON_NAME, multi=False)].getLabel()
            lizLST   = poolit(__buildMenuItem)(items.get(type,[]))
            selected = Globals.dialog.selectDialog(lizLST, header=ADDON_NAME)
            if selected:
                with self.toggleSpinner(lock=True, condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                    self.log(f'selectPredefined, type = {type}, start = {start}, lizLST = {len(lizLST)}, selected = {len(selected)}')
                    self._addChannels(start,  Globals._randomShuffle([FileAccess.loadJSON(liz.getProperty('citem')) for idx, liz in enumerate(lizLST) if idx in selected]))
        except Exception as e: self.log("selectPredefined, failed! %s"%(e), xbmc.LOGERROR)
        
            
    def _addChannels(self, start=1, items=[]):
        if start > 0 and items:
            self.log(f'_addChannels, start = {start}, items = {len(items)}')
            numbers = sorted([channel.get('number',0) for channel in self.newChannels if not channel.get('id')])
            numbers = numbers[numbers.index(start):] + numbers[:numbers.index(start)]
            for number in numbers:
                if len(items) > 0:
                    self.madeChanges = True
                    item  = items.pop(0)
                    citem = self.newChannel.copy()
                    type  = item.get('type',LANGUAGE(30127))
                    radio = Globals._isRadio(item)
                    citem.update({"id"      : Globals._getChannelID(item['name'],item['path'],number),
                                  "type"    : type,
                                  "number"  : number,
                                  "name"    : Globals._getChannelSuffix(item['name'], type),
                                  "logo"    : item.get('logo'),
                                  "path"    : item.get('path',''),
                                  "group"   : [type],
                                  "rules"   : item.get('rules',{}),
                                  "catchup" : ('vod' if not radio else ''),
                                  "changed" : True,
                                  "enable"  : True,
                                  "radio"   : radio,
                                  "favorite": False})
                    self.newChannels[number-1] = Globals._cleanGroups(citem)
            if self.madeChanges and self.launchManager: self.fillChanList(self.newChannels,True,focus=number)
            return True
                
         
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
            return Globals.listitems.buildMenuListItem('%s| %s'%(fileList.index(fitem),fitem.get('showlabel',fitem.get('label'))), fitem.get('file') ,icon=Globals._getThumb(fitem,opt=self.EPGArtwork))

        def __fileList(citem):
            fileList = []
            try:
                Globals.dialog.notificationDialog('%s: [B]%s[/B]\n%s'%(LANGUAGE(32236),citem.get('name','Untitled'),LANGUAGE(32140)))
                tmpcitem = citem.copy()
                tmpcitem['id'] = Globals._getChannelID(citem['name'], citem['path'], random.random())
                start_time = time.time()
                fileList   = Globals.properties.preemptActivity('%s %s\n%s'%(LANGUAGE(32098),LANGUAGE(32093),LANGUAGE(32140)), Builder().buildChannels, *([tmpcitem],True,False,False))
                end_time   = time.time()
                # self.log('previewChannel: __fileList, id = %s, fileList = %s'%(citem['id'],len(fileList)))
                return fileList, round(abs(end_time-start_time),2)
            except Exception as e:
                self.log("previewChannel, __fileList: failed! %s"%(e), xbmc.LOGERROR)
                return [], 0
            
        if not Globals.properties.isRunning('Manager.previewChannel'):
            with Globals.properties.chkRunning('Manager.previewChannel'), self.toggleSpinner(lock=True,condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                lizLST = []
                fileList, run_time = __fileList(citem)
                if not isinstance(fileList,list) and not fileList: Globals.dialog.notificationDialog('%s or\n%s'%(LANGUAGE(32030),LANGUAGE(32000)))
                elif fileList: lizLST.extend(poolit(__buildItem)(fileList))
            if len(lizLST) > 0: return Globals.dialog.selectDialog(lizLST, header='%s: [B]%s[/B] - Build Time: [B]%ss[/B]'%(LANGUAGE(32235),citem.get('name','Untitled'),f"{run_time:.2f}"))
            if retCntrl: self.setFocusId(retCntrl)


    def getMontiorList(self):
        self.log('getMontiorList')
        try:
            with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                titles  = Globals.dialog.getInfoMonitor()
                labels  = sorted(set([Globals._cleanLabel(value).title() for info in titles for key, value in list(info.items()) if value not in ['','..'] and key not in ['path','logo']]))
                itemLST = [Globals.listitems.buildMenuListItem(label,icon=ICON) for label in labels]
                if len(itemLST) == 0: raise Exception()
                itemSEL = Globals.dialog.selectDialog(itemLST,LANGUAGE(32078)%('Name'),useDetails=True,multi=False)
                if itemSEL is not None: return itemLST[itemSEL]
                else: raise Exception()
        except Exception: return xbmcgui.ListItem(LANGUAGE(32079))


    def switchLogo(self, channelData, channelPOS):
        def __cleanLogo(chlogo):
            #todo convert resources from vfs to fs
            # return chlogo.replace('resources://','special://home/addons/')
            # resources = path.replace('/resources','').replace(,)
            # resources://resources.images.studios.white/Amazon.png
            return chlogo
        
        def __select():
            def __buildItem(logo):
                return Globals.listitems.buildMenuListItem('%s| %s'%(logos.index(logo)+1, os.path.splitext(os.path.basename(logo))[0].upper() if len(os.path.splitext(os.path.basename(logo))[0]) <= 4 else os.path.splitext(os.path.basename(logo))[0].title()), Globals._unquoteString(logo), logo, [logo])
                
            Globals.dialog.notificationDialog(LANGUAGE(32140))
            with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                chname = channelData.get('name')
                logos  = self.resources.selectLogo(channelData)
                lizLST = []
                lizLST.extend(poolit(__buildItem)(logos))
            select = Globals.dialog.selectDialog(lizLST,'%s (%s)'%(LANGUAGE(32066).split('[CR]')[1],chname),useDetails=True,multi=False)
            if select is not None: return lizLST[select].getPath()

        def __browse():
            with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                chname = channelData.get('name')
                retval = Globals.dialog.browseSources(type=1,heading='%s (%s)'%(LANGUAGE(32066).split('[CR]')[0],chname), default=channelData.get('icon',''), shares='files', mask=xbmc.getSupportedMedia('picture'), exclude=[12,13,14,15,16,17,21,22])
            if FileAccess.copy(__cleanLogo(retval), os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')): 
                if FileAccess.exists(os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')): 
                    return os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')
            return retval
            
        def __match():
            with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                return self.resources.getLogo(channelData, fallback=self.resources.getImageCache(channelData['name']), lookup=True)

        if not channelData.get('name'): return Globals.dialog.notificationDialog(LANGUAGE(32065))
        chlogo = None
        retval = Globals.dialog.yesnoDialog(LANGUAGE(32066), heading     ='%s - %s'%(ADDON_NAME,LANGUAGE(32172)),
                                                     nolabel     = LANGUAGE(32067), #Select
                                                     yeslabel    = LANGUAGE(32068), #Browse
                                                     customlabel = LANGUAGE(30022)) #Auto
              
        if   retval == 0: chlogo = __select()
        elif retval == 1: chlogo = __browse()
        elif retval == 2: chlogo = __match()
        else: Globals.dialog.notificationDialog(LANGUAGE(32070))
        if chlogo and chlogo != LOGO:
            self.log('switchLogo, chname = %s, chlogo = %s'%(channelData.get('name'),chlogo))
            Globals.dialog.notificationDialog(LANGUAGE(32139))
            self.madeChanges = True
            channelData['logo'] = chlogo
            self.newChannels[channelPOS] = channelData
            if self.launchManager: 
                self.fillChanList(self.newChannels,refresh=True,focus=channelPOS)


    def getControlID(self, cntrl):
        try: return cntrl.getId()
        except Exception as e: 
            self.log("getControlID, failed! %s"%(e), xbmc.LOGERROR)


    def isVisible(self, cntrl):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            if hasattr(cntrl, 'isVisible'): state = cntrl.isVisible()
        except Exception: state = self.cntrlStates.get(self.getControlID(cntrl),False)
        self.log('isVisible, cntrl = %s, state = %s'%(self.getControlID(cntrl),state))
        return state
        
        
    def setVisibility(self, cntrl, state):
        try: 
            if isinstance(cntrl, int):       cntrl = self.getControl(cntrl)
            if hasattr(cntrl, 'setVisible'): cntrl.setVisible(state)
            self.cntrlStates[self.getControlID(cntrl)] = state
            self.log('setVisibility, cntrl = ' + str(self.getControlID(cntrl)) + ', state = ' + str(state))
        except Exception as e: self.log("setVisibility, failed! %s"%(e), xbmc.LOGERROR)
        return state
        
    
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


    def clearChannel(self, citem, channelPOS, prompt=True, open=False):
        self.log('clearChannel, channelPOS = %s'%(citem['number'] - 1))
        with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
            if prompt and not Globals.dialog.yesnoDialog('%s %s\n%s'%(LANGUAGE(30223),citem.get('number',-1),LANGUAGE(32073))): return citem
            self.madeItemchange = True
            tmpItem = self.newChannel.copy()
            tmpItem['number'] = citem['number'] #preserve channel number
            self.newChannels[channelPOS] = tmpItem
            self.saveChannelItems(tmpItem, open)
            

    def moveChannel(self, citem, channelPOS):
        self.log('moveChannel, channelPOS = %s'%(channelPOS))
        if citem['number'] > CHANNEL_LIMIT: return Globals.dialog.notificationDialog(LANGUAGE(32064))
        retval = Globals.dialog.inputDialog(LANGUAGE(32137), key=xbmcgui.INPUT_NUMERIC, opt=citem['number'])
        if retval:
            retval = int(retval)
            if (retval > 0 and retval < CHANNEL_LIMIT) and retval != channelPOS + 1:
                if Globals.dialog.yesnoDialog('%s %s %s from [B]%s[/B] to [B]%s[/B]?'%(LANGUAGE(32136),citem['name'],LANGUAGE(32023),citem['number'],retval)):
                    with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                        if retval in [channel.get('number') for channel in self.newChannels if channel.get('path')]: Globals.dialog.notificationDialog(LANGUAGE(32138))
                        else:
                            self.madeItemchange = True
                            tmpItem = self.newChannel.copy()
                            tmpItem['number'] = channelPOS + 1
                            self.newChannels[channelPOS] = tmpItem
                            citem['number'] = retval
                            self.saveChannelItems(citem)
            

    def closeChannel(self, citem, focus=0, open=False):
        self.log('closeChannel')
        if self.madeItemchange:
            if Globals.dialog.yesnoDialog(LANGUAGE(32243)): return self.saveChannelItems(citem, open)
        self.togglechanList(focus=focus)
                 
                 
    def closeManager(self):
        self.log('closeManager, madeChanges = %s'%(self.madeChanges))
        if self.madeChanges: self.saveChanges(close=True)
        self.close()
        
        
    def saveChannelItems(self, citem: dict={}, open=False):
        self.log('saveChannelItems [%s], open = %s'%(citem.get('id'),open))
        if self.madeItemchange:
            self.madeChanges = True
            with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                self.madeItemchange = False
                citem['changed'] = True
                self.newChannels[citem['number'] - 1] = citem
        if self.launchManager:
            self.fillChanList(self.newChannels,True,(citem['number'] - 1),citem if open else None)
        return citem
    
   
    def saveChanges(self, start=1, close=True):
        def __yesno():
            if   self.launchManager: return Globals.dialog.yesnoDialog(LANGUAGE(32076))
            elif not self.server:    return True
                
        self.log("saveChanges")
        def __validateChannels(newChannels):
            def __validate(citem):
                if citem.get('name') and citem.get('path'):
                    return self.setID(citem)
            newChannels = self.channels.sortChannels([_f for _f in [__validate(channel) for channel in newChannels] if _f])
            self.log('__validateChannels, newChannels = %s'%(len(newChannels)))
            return newChannels
        
        if self.madeChanges:
            if __yesno():
                with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                    channels = __validateChannels(self.newChannels)
                    self.log("saveChanges, channels = %s"%(len(channels)))
                    if self.server: #remote save
                        self.jsonRPC.requestURL('http://%s/%s'%(self.server.get('host'), CHANNELFLE), payload={'uuid':Globals.settings.getMYUUID(),'name':self.friendly,'payload':channels})
                        Globals.properties.setPropTimer('chkPVRRefresh')#refresh pvr guide
                    else: #local save
                        if self.channels.setChannels(channels):
                            self.madeChanges = False
                            self.log(f"saveChanges, backup {CHANNELCHANGED_KEY} = {self.backup.backupChannels(CHANNELCHANGED_KEY,silent=True)}")
                            Globals.properties.setPropTimer('chkChanged')# Refresh Channel Changed!
                            if self.launchManager: 
                                self.fillChanList(self.newChannels,True,focus=start)
            else: self.madeChanges = False
        if close: self.closeManager()
            
            
    def getFocusItems(self, controlId=None):
        if controlId in [5,6,7,9000,9001,9002,9003,9004]:
            label, label2 = self.getLabels(controlId)
            try:     snum = int(Globals._cleanLabel(label.replace("|",'')))
            except Exception:  snum = 1
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
                if self.isLocked(): Globals.dialog.notificationDialog(LANGUAGE(32260))
                else:
                    with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                        self.log('onAction: actionId = %s, locked = %s'%(actionId,self.isLocked()))
                        if   xbmcgui.getCurrentWindowDialogId() == "13001": Globals.builtin.executebuiltin('Action(Back)')
                        elif self.isVisible(self.chanList): self.closeManager()
                        else:
                            focusItems = self.getFocusItems
                            if self.isVisible(self.itemList):
                                self.closeChannel(focusItems.get('citem'),focusItems.get('position'))
            
            
    def onFocus(self, controlId):
        self.log('onFocus: controlId = %s'%(controlId))

        
    def onClick(self, controlId):
        if (self.isLocked() or (time.time() - self.lastActionTime) < .5 and controlId not in [9000,9001,9002,9003,9004]): Globals.dialog.notificationDialog(LANGUAGE(32260))
        else:
            with self.toggleSpinner(condition=Globals.properties.isRunning('Manager.toggleSpinner')==False):
                self.log('onClick: controlId = %s, locked = %s'%(controlId,self.isLocked()))
                if controlId == 0: self.closeManager()
                else:
                    focusItems = self.getFocusItems(controlId)
                    if   controlId == 5:  self.buildChannelItem(focusItems.get('citem')) #item list
                    elif controlId == 6:  self.buildChannelItem(self.itemInput(focusItems.get('item')),focusItems.get('item').getProperty('key'))
                    elif controlId == 10: self.switchLogo(focusItems.get('citem'), focusItems.get('chpos',0))#logo button
                    elif controlId in [9001,9002,9003,9004]: #side buttons
                        if   focusItems.get('label') == LANGUAGE(32059): self.saveChanges(focusItems.get('citem'),close=False) #Save 
                        elif focusItems.get('label') == LANGUAGE(32061): self.clearChannel(focusItems.get('citem'), focusItems.get('chpos',0)) #Delete
                        elif focusItems.get('label') == LANGUAGE(32239): self.clearChannel(focusItems.get('citem'), focusItems.get('chpos',0), open=True)#Clear
                        elif focusItems.get('label') == LANGUAGE(32136): self.moveChannel(focusItems.get('citem'), focusItems.get('chpos',0))  #Move 
                        elif focusItems.get('label') == LANGUAGE(32062): #Close
                            if   self.isVisible(self.itemList): self.closeChannel(focusItems.get('citem'), focus=focusItems.get('chpos',0))
                            elif self.isVisible(self.chanList): self.closeManager()
                        elif focusItems.get('label') == LANGUAGE(32060): #Cancel
                            if self.isVisible(self.itemList): 
                                self.madeItemchange = False
                                self.closeChannel(focusItems.get('citem'), focus=focusItems.get('chpos',0))
                            elif self.isVisible(self.chanList): self.closeManager()
                        elif focusItems.get('label') == LANGUAGE(32240): #Confirm
                            if   self.isVisible(self.itemList): self.saveChannelItems(focusItems.get('citem'))
                            elif self.isVisible(self.chanList): self.saveChanges(focusItems.get('citem'))
                        elif focusItems.get('label') == LANGUAGE(32235): #Preview
                            if self.isVisible(self.itemList) and self.madeItemchange: self.closeChannel(focusItems.get('citem'), focus=focusItems.get('chpos',0), open=True)
                            self.previewChannel(focusItems.get('citem'), focusItems.get('retCntrl'))
                        elif focusItems.get('label') == LANGUAGE(32110): ...#Backup
                        elif focusItems.get('label') == LANGUAGE(32112): self.autoRecovery() #Recover
                        elif focusItems.get('label') == LANGUAGE(30038): self.autoTune(focusItems.get('number',1)) #AutoTune
                        elif focusItems.get('label') == LANGUAGE(30229): self.selectPredefined(focusItems.get('number',1)) #Predefined
                            
                            
