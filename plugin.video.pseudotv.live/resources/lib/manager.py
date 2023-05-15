  # Copyright (C) 2023 Lunatixz


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
     
# Colors
COLOR_UNAVAILABLE_CHANNEL = 'dimgray'
COLOR_AVAILABLE_CHANNEL   = 'white'
COLOR_LOCKED_CHANNEL      = 'orange'
COLOR_WARNING_CHANNEL     = 'red'
COLOR_RADIO_CHANNEL       = 'cyan'
COLOR_FAVORITE_CHANNEL    = 'yellow'
        
def isManagerRunning():
    return PROPERTIES.getPropertyBool('managerRunning')
    
def setManagerRunning(state=True):
    return PROPERTIES.setPropertyBool('managerRunning',state)

def forceUpdateTime(key):
    PROPERTIES.setPropertyInt(key,0)

def getGroups(add=False):
    if SETTINGS.getSetting('User_Groups'): GROUP_TYPES.extend(SETTINGS.getSetting('User_Groups').split('|'))
    if add: GROUP_TYPES.insert(0,'+Add')
    return sorted(set(GROUP_TYPES))
    
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
    madeChanges    = False
    lastActionTime = time.time()
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        if isClient():
            DIALOG.notificationDialog(LANGUAGE(32058))
            return openAddonSettings(0,1)
        elif isManagerRunning():
            DIALOG.notificationDialog(LANGUAGE(32057)%(LANGUAGE(30107)))
            return openAddonSettings(0,1)
        
        with busy_dialog():
            setManagerRunning(True)
            self.cntrlStates  = {}
            self.showingList  = True
            self.startChannel = kwargs.get('channel',-1)
            self.log('Manager, startChannel = %s'%(self.startChannel))
            
            self.cache        = Cache(mem_cache=True)
            self.channels     = Channels()
            self.jsonRPC      = JSONRPC()
            self.rules        = RulesList()
            self.xsp          = XSP()
            self.m3u          = M3U()
            self.resources    = Resources(self.jsonRPC, self.cache)
            
            self.newChannel   = self.channels.getTemplate()
            self.channelList  = sorted(self.createChannelList(self.buildArray(), self.channels.getChannels()), key=lambda k: k['number'])
            self.channelList.extend(self.channels.getPredefinedChannels())
            self.newChannels  = self.channelList.copy()
            
            if self.startChannel == -1: self.startChannel = self.getFirstAvailChannel()
            self.focusIndex   = (self.startChannel - 1) #Convert from Channel number to array index
           
        try:
            if not kwargs.get('start',True): raise Exception('Bypassed doModal')
            self.doModal()
        except Exception as e: 
            self.log('Manager failed! %s'%(e), xbmc.LOGERROR)
            self.closeManager()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def onInit(self):
        try:
            self.spinner       = self.getControl(4)
            self.chanList      = self.getControl(5)
            self.itemList      = self.getControl(6)
            self.ruleList      = self.getControl(7)
            self.right_button1 = self.getControl(9001)
            self.right_button2 = self.getControl(9002)
            self.right_button3 = self.getControl(9003)
            self.right_button4 = self.getControl(9004)
            
            self.focusItems    = {}
            self.fillChanList(self.newChannels,focus=self.focusIndex) #all changes made to self.newChannels before final save to self.channellist
        except Exception as e: 
            log("onInit, failed! %s"%(e), xbmc.LOGERROR)
            self.closeManager()
        
        
    def getFirstAvailChannel(self):
        for channel in self.channelList:
            if not channel.get('id'): return channel.get('number')
        return 1
        
        
    def buildArray(self):
        self.log('buildArray')
        ## Create blank array of citem templates. 
        for idx in range(CHANNEL_LIMIT):
            newChannel = self.newChannel.copy()
            newChannel['number'] = idx + 1
            yield newChannel
  
        
    def createChannelList(self, channelArray, channelList):
        self.log('createChannelList')
        ## Fill blank array with citems from channels.json.
        for item in channelArray:
            for channel in channelList:
                if item["number"] == channel["number"]:
                    item.update(channel)
            yield item


    def fillChanList(self, channelList, reset=False, focus=None):
        self.log('fillChanList, focus = %s'%(focus))
        ## Fill chanList listitem for display. *reset draws new control list. *focus list index for channel position.
        self.togglechanList(True,reset=reset)
        self.toggleSpinner(self.chanList,True)
        listitems = poolit(self.buildChannelListItem)(channelList)
        self.chanList.addItems(listitems)
        if focus is None: self.chanList.selectItem(self.setFocusPOS(listitems))
        else:             self.chanList.selectItem(focus)
        self.toggleSpinner(self.chanList,False)


    def toggleSpinner(self, ctrl, state):
        self.setVisibility(self.spinner,state)
        # getSpinControl() #todo when avail.
        # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__control__spin.html
        # ctrl.setPageControlVisible(state)


    def togglechanList(self, state, focus=0, reset=False):
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
            self.setEnableCondition(self.right_button3,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Path)]')
            self.setEnableCondition(self.right_button4,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Path)]')
        else: # channelitems
            self.setVisibility(self.ruleList,False)
            self.setVisibility(self.chanList,False)
            self.setVisibility(self.itemList,True)
            self.itemList.reset()
            xbmc.sleep(100)
            self.itemList.selectItem(focus)
            self.setFocus(self.itemList)
            self.setLabels(self.right_button1,LANGUAGE(32063))#ok
            self.setLabels(self.right_button2,LANGUAGE(32060))#cancel
            self.setLabels(self.right_button3,'')
            self.setLabels(self.right_button4,LANGUAGE(32061))#Delete
            self.setEnableCondition(self.right_button4,'[!String.IsEmpty(Container(5).ListItem(Container(5).Position).Path)]')
        
        
    def toggleruleList(self, state, focus=0):
        self.log('toggleruleList, state = %s, focus = %s'%(state,focus))
        if self.isVisible(self.chanList): 
            return DIALOG.notificationDialog(LANGUAGE(32000))
        
        if state: # rulelist
            self.setVisibility(self.itemList,False)
            self.setVisibility(self.ruleList,True)
            self.ruleList.selectItem(focus)
            self.setFocus(self.ruleList)
        else: # channelitems
            self.setVisibility(self.ruleList,False)
            self.setVisibility(self.itemList,True)
            self.itemList.selectItem(focus)
            self.setFocus(self.itemList)
        
        
    def hasStation(self, channelData):
        return not self.m3u.findStation(channelData)[0] is None
        

    def buildChannelListItem(self, channelData):
        chnum        = channelData["number"]
        chname       = channelData.get("name",'')
        isPredefined = chnum > CHANNEL_LIMIT
        isFavorite   = channelData.get('favorite',False)
        isRadio      = channelData.get('radio',False)
        isLocked     = isPredefined #todo parse channel lock rule
        hasStation   = self.hasStation(channelData)
        channelColor = COLOR_UNAVAILABLE_CHANNEL
        labelColor   = COLOR_UNAVAILABLE_CHANNEL
        
        if chname:
            if isPredefined: 
                channelColor = COLOR_LOCKED_CHANNEL
            else:
                labelColor   = COLOR_AVAILABLE_CHANNEL
                
                if not hasStation: channelColor = COLOR_WARNING_CHANNEL
                elif isLocked:     channelColor = COLOR_LOCKED_CHANNEL
                elif isFavorite:   channelColor = COLOR_FAVORITE_CHANNEL
                elif isRadio:      channelColor = COLOR_RADIO_CHANNEL
                else:              channelColor = COLOR_AVAILABLE_CHANNEL
        
        label  = '[COLOR=%s][B]%s.[/COLOR][/B]'%(channelColor,chnum)
        label2 = '[COLOR=%s]%s[/COLOR]'%(labelColor,chname)
        path   = '|'.join(channelData.get("path",[]))
        prop   = {'description':chnum,'channelData':dumpJSON(channelData, sortkey=False),'chname':chname,'chnumber':chnum}
        return LISTITEMS.buildMenuListItem(label,label2,iconImage=channelData.get("logo",''),url=path,propItem=prop)
        

    def setDescription(self, stid):#todo use control id and label
        PROPERTIES.setProperty('manager.description',LANGUAGE(stid))


    def setFocusPOS(self, listitems, chnum=None, ignore=True):
        for idx, listitem in enumerate(listitems):
            chnumber = int(cleanLabel(listitem.getLabel()).strip('.'))
            if  ignore and chnumber > CHANNEL_LIMIT: continue
            elif chnum is not None and chnum == chnumber: return idx
            elif chnum is None and cleanLabel(listitem.getLabel2()): return idx
        return 0
        
        
    def buildChannelItem(self, channelData, selkey='path'):
        self.log('buildChannelItem, channelData = %s'%(channelData))
        if self.isVisible(self.ruleList): return
        self.togglechanList(False)
        self.toggleSpinner(self.itemList,True)
        
        LABEL  = {'name'    : LANGUAGE(32092),
                  'path'    : LANGUAGE(32093),
                  'group'   : LANGUAGE(32094),
                  'rules'   : LANGUAGE(32095),
                  'radio'   : LANGUAGE(32091),
                  'favorite': LANGUAGE(32090)}
                  
        DESC   = {'name'    : LANGUAGE(32085),
                  'path'    : LANGUAGE(32086),
                  'group'   : LANGUAGE(32087),
                  'rules'   : LANGUAGE(32088),
                  'radio'   : LANGUAGE(32084),
                  'favorite': LANGUAGE(32083)}
                  
        listItems = []
        for key in list(self.channels.getTemplate().keys()):
            value = channelData.get(key)
            if   key in ["number","type","logo","id","catchup"]: continue # keys to ignore, internal use only.
            elif isinstance(value,list): 
                if   key == "group" :    value = ' / '.join(list(set(value)))
                elif key == "path"  :    value = '|'.join(value)
            elif isinstance(value,bool): value = str(value)
            if not value: value = ''
            prop = {'key':key,'value':value,'description':DESC.get(key,''),'channelData':dumpJSON(channelData, sortkey=False),'chname':channelData.get('name',''),'chnumber':channelData.get('number','')}
            listItems.append(LISTITEMS.buildMenuListItem(LABEL.get(key,''),value,url='|'.join(channelData.get("path",[])),iconImage=channelData.get("logo",COLOR_LOGO),propItem=prop))
            
        self.toggleSpinner(self.itemList,False)
        self.itemList.addItems(listItems)
        self.itemList.selectItem([idx for idx, liz in enumerate(listItems) if liz.getProperty('key')== selkey][0])
        self.setFocus(self.itemList)


    def itemInput(self, channelListItem):
        key   = channelListItem.getProperty('key')
        value = channelListItem.getProperty('value')
        channelData = loadJSON(channelListItem.getProperty('channelData'))
        self.log('itemInput, In channelData = %s, value = %s, key = %s'%(channelData,value,key))
        KEY_INPUT = {"name"     : {'func':DIALOG.inputDialog  ,'kwargs':{'message':LANGUAGE(32079),'default':value}},
                     "path"     : {'func':self.getPaths       ,'kwargs':{'item':channelData}},
                     "group"    : {'func':self.getGroups      ,'kwargs':{'value':value,'item':channelData}},
                     "rules"    : {'func':self.selectRules    ,'kwargs':{'item':channelData}},
                     "radio"    : {'func':self.toggleBool     ,'kwargs':{'state':channelData.get('radio',False)}},
                     "favorite" : {'func':self.toggleBool     ,'kwargs':{'state':channelData.get('favorite',False)}}}

        func   = KEY_INPUT[key.lower()]['func']
        args   = KEY_INPUT[key.lower()].get('args',())
        kwargs = KEY_INPUT[key.lower()].get('kwargs',{})
        retval, channelData = self.validateInput(key,func(*args,**kwargs),channelData)
        if not retval is None:
            self.madeChanges = True
            if key in list(self.newChannel.keys()):
                channelData[key] = retval
        self.log('itemInput, Out channelData = %s, value = %s, key = %s'%(channelData,value,key))
        return channelData
   
   
    def getGroups(self, value, item):
        self.log('getGroups, value = %s'%(value))
        groups  = getGroups()
        selects = DIALOG.selectDialog(groups,header=LANGUAGE(32081),preselect=findItemsInLST(groups,value.split(' / ')),useDetails=False)
        return [groups[idx] for idx in selects]
    
    
    def getPaths(self, item):
        paths  = item.get('path',[])
        select = -1
        while not MONITOR.abortRequested() and not select is None:
            npath  = None
            lizLST = [LISTITEMS.buildMenuListItem('%s.'%(idx+1),path,iconImage=item.get('logo',COLOR_LOGO),url=path) for idx, path in enumerate(paths)]
            lizLST.insert(0,LISTITEMS.buildMenuListItem(LANGUAGE(32100),LANGUAGE(33113),iconImage=COLOR_LOGO,url='add'))
            lizLST.insert(1,LISTITEMS.buildMenuListItem(LANGUAGE(32101),LANGUAGE(33114),iconImage=COLOR_LOGO,url='save'))
            select = DIALOG.selectDialog(lizLST, header=LANGUAGE(32086), multi=False)
            
            if lizLST[select].getPath() != 'add' and lizLST[select].getPath() in paths:
                retval = DIALOG.yesnoDialog(LANGUAGE(32102), customlabel=LANGUAGE(32103))
                if retval in [1,2]: paths.pop(paths.index(lizLST[select].getPath()))
                if retval == 2:     npath, item = self.validatePath(DIALOG.browseDialog(heading=LANGUAGE(32080),default=lizLST[select].getPath(),monitor=True), item)
                
            elif lizLST[select].getPath() == 'add':  npath, item = self.validatePath(DIALOG.browseDialog(heading=LANGUAGE(32080),monitor=True), item)
            elif lizLST[select].getPath() == 'save': break
            if not npath is None: paths.append(npath)
        self.log('getPaths, paths = %s'%(paths))
        return paths
        
        
    def toggleBool(self, state):
        self.log('toggleBool, state = %s'%(state))
        return not state


    def openEditor(self, path):
        self.log('openEditor, path = %s'%(path))
        if '|' in path: 
            path = path.split('|')
            path = path[0]#prompt user to select:
        media = 'video' if 'video' in path else 'music'
        if   '.xsp' in path: return self.openEditor(path,media)
        elif '.xml' in path: return self.openNode(path,media)
       
   
    def getChannelName(self, path, channelData):
        self.log('getChannelName, path = %s'%(path))
        if  channelData.get('name'): return channelData
        elif path.strip('/').endswith(('.xml','.xsp')):
            channelData['name'] = self.xsp.getSmartPlaylistName(path)
        elif path.startswith(('plugin://','upnp://','videodb://','musicdb://','library://','special://')):
            try: channelData['name'] = self.getMontiorList().getLabel()
            except: pass
        else:
            channelData['name'] = os.path.basename(os.path.dirname(path)).strip('/')
        return channelData


    def getMontiorList(self, key='label'):
        self.log('getMontiorList')
        try:
            def getItem(item):
                return LISTITEMS.buildMenuListItem(label1=item.get(key,''),iconImage=item.get('icon',COLOR_LOGO))
                
            NEWLST   = []
            TMPLST   = ['','...','..']
            infoList = DIALOG.getInfoMonitor()
            for info in infoList:
                info['label'] = cleanLabel(info.get('label'))
                if info.get('label') in TMPLST: continue
                TMPLST.append(info.get('label'))
                NEWLST.append(info)
            itemList = [getItem(info) for info in NEWLST if info.get('label')]
            select   = DIALOG.selectDialog(itemList,LANGUAGE(32078)%(key.title()),useDetails=True,multi=False)
            if select is not None: return itemList[select]
        except Exception as e: 
            self.log("getMontiorList, failed! %s\ninfoList = %s"%(e,NEWLST), xbmc.LOGERROR)
            return xbmcgui.ListItem()


    def getChannelIcon(self, name, channelData, force=False):
        self.log('getChannelIcon, name = %s, force = %s'%(name,force))
        if name is None: name = channelData.get('name','')
        if name: 
            if force: logo = ''
            else:     logo = channelData.get('logo','')
            if not logo or logo in [LOGO,COLOR_LOGO,ICON]:
                channelData['logo'] = self.resources.getLogo(name, channelData.get('type',"Custom"))
        return channelData
        
    
    def validateInput(self, key, value, channelData):
        self.log('validateInput, key = %s'%(key))
        def null(value,channelData):
            return None, channelData
        def new(value,channelData):
            return value, channelData
            
        validateAction = {'name' :self.validateLabel,
                          'path' :self.validatePaths,
                          'rules':null,
                          'radio':new,
                          'favorite':new,
                          'group':new}.get(key.lower(),None)
        try:
            retval, channelData = validateAction(value,channelData)
            if retval is None:
                DIALOG.notificationDialog(LANGUAGE(32077)%key.title())
                return None, channelData 
            self.log('validateInput, value = %s'%(retval))
            return retval, self.getID(channelData)
        except Exception as e: 
            log("validateInput, no action! %s"%(e))
            return value, channelData
        
        
    def validateLabel(self, label, channelData):
        #todo if path already used as channel verify name is different.
        if not label or (len(label) < 1 or len(label) > 128): label = None
        self.log('validateLabel, label = %s'%(label))
        return label, self.getChannelIcon(label, channelData, force=True)


    def validatePaths(self, paths, channelData):
        self.log('validatePaths, paths = %s'%paths)
        if len(paths) == 0: return None, channelData
        channelData = self.getChannelName(paths[0], channelData)
        channelData = self.getChannelIcon(channelData.get('name'),channelData)
        return paths, channelData


    def validatePath(self, path, channelData, spinner=True):
        self.log('validatePath, path = %s'%path)
        if not path: return None, channelData
        if spinner: self.toggleSpinner(self.itemList,True)
        file = self.validateVFS(path, channelData)
        if not file:
            path = None
            DIALOG.notificationDialog(LANGUAGE(32030))
        else:
            # channelData['radio'] = isRadio(channelData)
            channelData = self.getChannelName(path, channelData)
            channelData = self.getChannelIcon(channelData.get('name'),channelData)
        if spinner: self.toggleSpinner(self.itemList,False)
        return path, self.validatePlaylist(path, channelData)
        
        
    def validateVFS(self, path, channelData):
        self.log('validateVFS, path %s'%(path))
        dia   = DIALOG.progressDialog(message='%s %s, %s..\n%s'%(LANGUAGE(32098),'Path',LANGUAGE(32099),path))
        media = 'music' if channelData['radio'] else 'video'
        dirs  = []
        if path.endswith('.xsp'): #smartplaylist
            paths, ofilter, media, osort = self.xsp.parseSmartPlaylist(path)
            if len(paths) > 0: #treat 'mixed' smartplaylists as multi-path mixed content.
                for path in paths:
                    result = self.validateVFS(path, channelData)
                    if result: return result
    
        json_response = self.jsonRPC.requestList(channelData, path, media, limits={"end": 5, "start": 0}) #todo use another means to verify or bypass autopage set limits.
        for idx, item in enumerate(json_response):
            file     = item.get('file', '')
            fileType = item.get('filetype', 'file')
            if fileType == 'file':
                dia = DIALOG.progressDialog(int(((idx)*100)//len(json_response)),control=dia, message='%s %s...\n%s\n%s'%(LANGUAGE(32098),'Path',path,file))
                item['duration'] = self.jsonRPC.getDuration(file, item)
                if item['duration'] == 0: continue
                else:
                    self.log('validateVFS, found playable file %s'%(file))
                    #todo use seekable to set channel seek locks.
                    seekable = self.validateSeek(item, channelData)
                    self.log('validateVFS, seekable path = %s' % (seekable))
                    DIALOG.progressDialog(100,control=dia)
                    closeBusyDialog()
                    return file
            else: dirs.append(file)
                
        for dir in dirs: 
            result = self.validateVFS(dir, channelData)
            if result: return result
            
        closeBusyDialog()
        DIALOG.progressDialog(100,control=dia)
        
        
    def validateSeek(self, item, channelData):
        file = item.get('file')
        dur  = item.get('duration')
        self.log('validateSeek, file = %s, dur = %s'%(file,dur))
        if PLAYER.isPlaying() or not file.startswith(tuple(VFS_TYPES)) and not file.endswith('.strm'): return True
        # todo test seek for support disable via adv. rule if fails.
        # todo set seeklock rule if seek == False
        liz = xbmcgui.ListItem('Seek Test', path=file)
        liz.setProperty('startoffset', str(int(dur/4)))
        infoTag = ListItemInfoTag(liz, 'video')
        infoTag.set_resume_point({'ResumeTime':int(dur/4),'TotalTime':int(dur/4)})
        PLAYER.play(file, liz, windowed=True)
    
        getTime  = 0
        waitTime = 30
        while not MONITOR.abortRequested():
            waitTime -= 1
            if MONITOR.waitForAbort(1) or waitTime < 1:
                self.log('validateSeek, waitForAbort')
                break
            elif not PLAYER.isPlaying():
                continue
            elif ((int(PLAYER.getTime()) > getTime) or BUILTIN.getInfoBool('SeekEnabled','Player')):
                PLAYER.stop()
                return True
        PLAYER.stop()
        return False

        
    def validatePlaylist(self, path, channelData):
        # if path.strip('/').endswith(('.xml','.xsp')):
            # self.log('validatePlaylist, path = %s'%(path))
        #cache playlists to PLS_LOC?
        # if path.strip('/').endswith('.xml'):
            # newPath = path.strip('/').replace('library://','special://userdata/library/')
            # dir, file = (os.path.split(newPath))
            # cachefile = os.path.join(dir.replace('special://userdata/library',PLS_LOC),file)
        # elif path.endswith('.xsp'):
            # cachefile = os.path.join(PLS_LOC,os.path.basename(path))
        # else: 
            # return path, channelData
        # self.log('validatePlaylist, path = %s, cachefile = %s'%(path,cachefile))
        # FileAccess.copy(path, cachefile): 
        return channelData


    def getID(self, channelData):
        if channelData.get('name') and channelData.get('path') and channelData.get('number'): 
            channelData['id'] = getChannelID(channelData['name'], channelData['path'], channelData['number'])
            self.log('getID, id = %s'%(channelData['id']))
        return channelData
        
        
    def validateChannels(self, channelList):
        def validateChannel(channelData):
            if not channelData.get('name','') or not channelData.get('path',[]): return None
            if channelData['number'] <= CHANNEL_LIMIT: channelData['type'] = "Custom" #custom
            return self.getID(self.getChannelIcon(channelData.get('name'),channelData))
        self.log('validateChannels, channelList = %s'%(len(channelList)))
        return sorted(poolit(validateChannel)(channelList), key=lambda k: k['number'])
              

    def saveChannelItems(self, channelData, channelPOS):
        self.log('saveChannelItems, channelPOS = %s'%(channelPOS))
        self.newChannels[channelPOS] = channelData
        self.fillChanList(self.newChannels,reset=True,focus=channelPOS)
        
    
    def saveChanges(self):
        self.log("saveChanges")
        if DIALOG.yesnoDialog("Changes Detected, Do you want to save?"): return self.saveChannels() 
        else: self.closeManager()


    def saveChannels(self):
        if   not self.madeChanges: return
        elif not DIALOG.yesnoDialog(LANGUAGE(32076)): return
        self.toggleSpinner(self.chanList,True)
        self.newChannels = self.validateChannels(self.newChannels)
        self.channelList = self.validateChannels(self.channelList)
        difference = sorted(diffLSTDICT(self.channelList,self.newChannels), key=lambda k: k['number'])
        log('saveChannels, difference = %s'%(len(difference)))
        
        pDialog = DIALOG.progressDialog(message=LANGUAGE(32075))
        for idx, citem in enumerate(difference):
            if citem in self.channelList: 
                self.channels.delChannel(citem)
                
            if citem in self.newChannels:
                pDialog = DIALOG.progressDialog(int(((idx + 1)*100)//len(difference)),pDialog,message="%s: %s"%(LANGUAGE(32074),citem.get('name')),header='%s, %s'%(ADDON_NAME,LANGUAGE(30152)))
                self.channels.addChannel(citem)

        self.channels.setChannels()
        self.toggleSpinner(self.chanList,False)
        self.closeManager()
            
        
    def clearChannel(self, item, prompt=True):
        self.log('clearChannel, channelPOS = %s'%(item['number'] - 1))
        if prompt and not DIALOG.yesnoDialog(LANGUAGE(32073)): return item
        self.madeChanges = True
        nitem = self.newChannel.copy()
        nitem['number'] = item['number'] #preserve channel number
        self.saveChannelItems(nitem, nitem['number'] - 1)
        return nitem


    def moveChannel(self, channelData, channelPOS):
        self.log('moveChannel, channelPOS = %s'%(channelPOS))
        retval = int(DIALOG.inputDialog(LANGUAGE(32137), key=xbmcgui.INPUT_NUMERIC, opt=channelData['number']))
        if retval and (retval > 0 and retval < CHANNEL_LIMIT) and retval != channelPOS + 1:
            if DIALOG.yesnoDialog('%s %s %s from [B]%s[/B] to [B]%s[/B]?'%(LANGUAGE(32136),channelData['name'],LANGUAGE(32023),channelData['number'],retval)):
                if retval in [channel.get('number') for channel in self.newChannels if channel.get('path')]:
                    DIALOG.notificationDialog(LANGUAGE(32138))
                else:
                    self.madeChanges = True
                    nitem = self.newChannel.copy()
                    nitem['number'] = channelPOS + 1
                    self.newChannels[channelPOS] = nitem
                    channelData['number'] = retval
                    self.saveChannelItems(channelData,channelData['number'] - 1)
        return channelData, channelPOS


    def selectRuleItems(self, item):
        self.log('selectRuleItems')
        # print('selectRuleItems',item)
        channelData = loadJSON(item['item'].getProperty('channelData'))
        
        if item['position'] == 0:
            ruleInstances = self.rules.buildRuleList([channelData]).get(channelData['id'],[]) #all rule instances with channel settings applied
        else:
            ruleInstances = [item['item']]
        
        listitems = poolit(self.buildRuleListItem)(ruleInstances,channelData)
        optionIDX = DIALOG.selectDialog(listitems,LANGUAGE(32072),multi=False)

        # ruleInstances = self.rules.buildRuleList([channelData]).get(channelData['id'],[]) #all rule instances with channel settings applied
        # # print(ruleInstances)

        # if not append:
            # ruleInstances = channelRules.copy()
        # else:    
            # ruleInstances = ruleList.copy()
            # for channelRule in channelRules:
                # for idx, ruleInstance in enumerate(ruleInstances):
                    # if channelRule.get('id') == ruleInstance.get('id'):
                        # ruleInstance.pop(idx)
                        
        # listitems = self.pool.poolList(self.buildRuleListItem,ruleInstances,channelData)
        

        if optionIDX is not None:
            ruleSelect    = loadJSON(listitems[optionIDX].getProperty('rule'))
            ruleInstances = self.rules.buildRuleList([channelData]).get(channelData['id'],[]) # all rules
            ruleInstance  = [ruleInstance for ruleInstance in ruleInstances if ruleInstance.myId == ruleSelect.get('id')][0]
            # print(ruleSelect,ruleInstance)
        
            #todo create listitem using ruleInstance and rule.py action map.
            listitems     = [LISTITEMS.buildMenuListItem(ruleInstance.optionLabels[idx],str(ruleInstance.optionValues[idx]),iconImage=channelData.get("logo",''),url=str(ruleInstance.myId),propItem={'channelData':dumpJSON(channelData)}) for idx, label in enumerate(ruleInstance.optionLabels)]
            self.ruleList.addItems(listitems)
            
            # optionIDX    = DIALOG.selectDialog(listitems,LANGUAGE(30135),multi=False)
            # # print(ruleSelect)
            # ruleSelect['options'][str(optionIDX)].update({'value':ruleInstance.onAction(optionIDX)})
            # # print(ruleSelect)
            # self.selectRuleItems(channelData, rules, ruleSelect)
            
            
    def selectRules(self, item):
        self.log('selectRules')
        DIALOG.notificationDialog("Coming Soon")
        return item
        # if not self.validateChannel(channelData): return DIALOG.notificationDialog(LANGUAGE(32071))
        # listitems = self.buildRuleItems(channelData)
        # # print('selectRules listitems',[listitem.getLabel() for listitem in listitems],channelData)
        # self.toggleruleList(True)
        # self.ruleList.addItems(listitems)
        
        # select = DIALOG.selectDialog(listitems,LANGUAGE(30135),useDetails=True,multi=False)
        # if select is None: return DIALOG.notificationDialog(LANGUAGE(30001))
        # # print(listitems[select].getLabel())
        
        # self.ruleList.addItems(listitems)
        
        # return channelData
        # select = DIALOG.selectDialog(listitems,LANGUAGE(30135),useDetails=True,multi=False)
        # if select is None: return DIALOG.notificationDialog(LANGUAGE(30001))
        # return listitems[select]
        
        # ruleid   = int(listitem.getPath())
        # if ruleid < 0: 
            # rules    = sorted(self.fillRules(channelData), key=lambda k: k['id'])
            # listitem = self.buildRuleItems(rules, channelData)
            # ruleid   = int(listitem.getPath())
        # ruleSelect = [idx for idx, rule in enumerate(self.channels.ruleList) if rule['id'] == ruleid]
        # self.selectRuleItems(channelData, rules, self.channels.ruleList[ruleSelect[0]])
        
        # self.toggleruleList(False)
        # return channelData['rules']


    def buildRuleItems(self, channelData, append=True):
        self.log('buildRuleItems, append = %s'%(append))
        self.toggleSpinner(self.ruleList,True)
        channelRules = self.rules.loadRules([channelData]).get(channelData['id'],[]) # all channel rule instances only.
        listitems = poolit(self.buildRuleListItem)(channelRules,channelData)
        if append: listitems.insert(0,LISTITEMS.buildMenuListItem('','Add New Rule',url='-1',propItem={'channelData':dumpJSON(channelData)}))
        self.toggleSpinner(self.ruleList,False)
        self.ruleList.reset()
        xbmc.sleep(100)
        return listitems
        

    def buildRuleListItem(self, data):
        ruleInstance, channelData = data
        rule = {'id':ruleInstance.myId,'name':ruleInstance.name,'description':ruleInstance.description,'labels':ruleInstance.optionLabels,'values':ruleInstance.optionValues,'title':ruleInstance.getTitle()}
        # print(rule)
        prop = {'description':rule['description'],'rule':dumpJSON(rule),'channelData':dumpJSON(channelData),'chname':channelData.get('name',''),'chnumber':channelData.get('number','')}
        return LISTITEMS.buildMenuListItem(rule['title'],rule['description'],iconImage=channelData.get("logo",''),url=str(rule['id']),propItem=prop)


    def saveRuleList(self, items):
        self.log('saveRuleList')
        self.toggleruleList(False)
            
            
    def fillRules(self, channelData): # prepare "new" rule list, remove existing.
        ...
        # chrules  = sorted(self.channels.getChannelRules(channelData, self.newChannels), key=lambda k: k['id'])
        # ruleList = self.channels.rules.copy()
        # for rule in ruleList:
            # for chrule in chrules:
                # if rule['id'] == chrule['id']: continue
            # yield rule


    def getLogo(self, channelData, channelPOS):
        def cleanLogo(chlogo):
            #todo convert resource from vfs to fs
            # return chlogo.replace('resource://','special://home/addons/')
            # resource = path.replace('/resources','').replace(,)
            # resource://resource.images.studios.white/Amazon.png
            return chlogo
        
        def select(chname):
            self.toggleSpinner(self.itemList,True)
            DIALOG.notificationDialog(LANGUAGE(32140))
            listitems = [LISTITEMS.buildMenuListItem('%s. %s'%(idx+1, chname),logo,iconImage=logo,url=logo) for idx, logo in enumerate(self.resources.selectLogo(chname))]
            self.toggleSpinner(self.itemList,False)
            select = DIALOG.selectDialog(listitems,'Select Channel Logo',useDetails=True,multi=False)
            if select is not None:
                return listitems[select].getPath()

        def browse(chname):
            retval = DIALOG.browseDialog(type=1,heading='%s for %s'%(LANGUAGE(32066),chname),default=channelData.get('icon',''), shares='files',mask=xbmc.getSupportedMedia('picture'),prompt=False)
            image  = os.path.join(LOGO_LOC,'%s%s'%(chname,retval[-4:])).replace('\\','/')
            if FileAccess.copy(cleanLogo(retval), image): 
                if FileAccess.exists(image): 
                    return image

        def match(chname):
            return self.resources.getLogo(chname)

        if self.isVisible(self.ruleList): return
        chname = channelData.get('name')
        if not chname: return DIALOG.notificationDialog(LANGUAGE(32065))
            
        chlogo = None
        retval = DIALOG.yesnoDialog('%s Source'%LANGUAGE(32066), 
                                        nolabel=LANGUAGE(32067), #Select
                                       yeslabel=LANGUAGE(32068), #Browse
                                    customlabel=LANGUAGE(32069)) #Match
                                             
        if   retval == 0: chlogo = select(chname)
        elif retval == 1: chlogo = browse(chname)
        elif retval == 2: chlogo = match(chname)
        else: DIALOG.notificationDialog(LANGUAGE(32070))
        self.log('getLogo, chname = %s, chlogo = %s'%(chname,chlogo))
        
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
        if self.madeChanges:
            forceUpdateTime('updateChannels')
        setManagerRunning(False)
        self.close()


    def getFocusVARS(self, controlId=None):
        if controlId not in [5,6,7,10,9001,9002,9003]: return self.focusItems
        self.log('getFocusVARS, controlId = %s'%(controlId))
        try:
            channelitem     = (self.chanList.getSelectedItem()     or xbmcgui.ListItem())
            channelPOS      = (self.chanList.getSelectedPosition() or 0)
            channelListItem = (self.itemList.getSelectedItem()     or xbmcgui.ListItem())
            itemPOS         = (self.itemList.getSelectedPosition() or 0)
            ruleListItem    = (self.ruleList.getSelectedItem()     or xbmcgui.ListItem())
            rulePOS         = (self.ruleList.getSelectedPosition() or 0)

            self.focusItems = {'chanList':{'item'    :channelitem,
                                           'position':channelPOS},
                               'itemList':{'item'    :channelListItem,
                                           'position':itemPOS},
                               'ruleList':{'item'    :ruleListItem,
                                           'position':rulePOS}}
                                           
            if controlId is not None: 
                label, label2 = self.getLabels(controlId)
                self.focusItems.update({'label':label,'label2':label2})
                
            try: self.focusItems['chanList'].setdefault('citem',{}).update(loadJSON(channelitem.getProperty('channelData')))
            except: pass
            try: self.focusItems['itemList'].setdefault('citem',{}).update(loadJSON(channelListItem.getProperty('channelData')))
            except: pass
            try: self.focusItems['ruleList'].setdefault('citem',{}).update(loadJSON(ruleListItem.getProperty('channelData')))
            except: pass
            
            chnumber = cleanLabel(channelitem.getLabel())
            if chnumber.isdigit(): 
                self.focusItems['number'] = convertString2Num(chnumber)
            elif self.focusItems['chanList']['citem'].get('number',''):
                self.focusItems['number'] = self.focusItems['chanList']['citem']['number']
            else:
                self.focusItems['number'] = channelPOS + 1
            return self.focusItems
        except Exception as e:
            self.log('getFocusVARS failed! %s'%(e))
            return {}

    
    def onFocus(self, controlId):
        self.log('onFocus: controlId = %s'%(controlId))

        
    def onAction(self, act):
        actionId = act.getId()   
        lastaction = time.time() - self.lastActionTime
        # during certain times we just want to discard all input   
        if lastaction < .5 and actionId not in ACTION_PREVIOUS_MENU:
            self.log('Not allowing actions')
            action = ACTION_INVALID
        else:
            self.log('onAction: actionId = %s'%(actionId))  
            items = self.getFocusVARS()
            if actionId in ACTION_PREVIOUS_MENU:
                if xbmcgui.getCurrentWindowDialogId() == "13001":
                     BUILTIN.executebuiltin("ActivateWindow(Action(Back)")
                elif self.isVisible(self.ruleList): self.toggleruleList(False)
                elif self.isVisible(self.itemList): self.togglechanList(True,focus=items['chanList']['position'])
                elif self.isVisible(self.chanList):
                    if self.madeChanges: self.saveChanges()
                    else:                self.closeManager()
            
        
    def onClick(self, controlId):
        items = self.getFocusVARS(controlId)
        if controlId <= 9000 and items.get('number'):
            if items.get('number') > CHANNEL_LIMIT: 
                return DIALOG.notificationDialog(LANGUAGE(32064))
            
        self.log('onClick: controlId = %s\nitems = %s'%(controlId,items))
        if self.isVisible(self.chanList):
            channelData = items['chanList']['citem'] 
        else:
            channelData = items['itemList']['citem']
            
        if   controlId == 0: self.closeManager()
        elif controlId == 5: 
            self.buildChannelItem(channelData)
        elif controlId == 6:
            self.buildChannelItem(self.itemInput(items['itemList']['item']),items['itemList']['item'].getProperty('key'))
        elif controlId == 7:
            self.selectRuleItems(items['ruleList'])
        elif controlId == 10: 
            self.getLogo(channelData,items['chanList']['position'] )
        #side menu buttons
        elif controlId == 9001:
            if   items['label'] == LANGUAGE(32062):#Close
                self.closeManager()
            elif items['label'] == LANGUAGE(32059):#Save
                self.saveChannels()
            elif items['label'] == LANGUAGE(32063):#OK
                if self.isVisible(self.itemList) and self.madeChanges:
                    self.saveChannelItems(channelData,items['chanList']['position'])
                elif self.isVisible(self.ruleList): 
                    self.toggleruleList(False)
                else: 
                    self.togglechanList(True,focus=items['chanList']['position'] )
        elif controlId == 9002:
            if items['label'] == LANGUAGE(32060):#Cancel
                if self.isVisible(self.chanList) and self.madeChanges:
                    self.saveChanges()
                elif self.isVisible(self.ruleList): 
                    self.toggleruleList(False)
                else: 
                    self.togglechanList(True,focus=items['chanList']['position'] )
        elif controlId == 9003:
            if items['label'] == LANGUAGE(32136):#Move
                self.moveChannel(channelData, items['chanList']['position'])
        elif controlId == 9004:
            if (self.isVisible(self.itemList) or items['label'] == LANGUAGE(32061)):#Delete
                if not channelData.get('id'): channelData = items['chanList']['citem']
                self.clearChannel(channelData)