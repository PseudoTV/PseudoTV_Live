#   Copyright (C) 2020 Lunatixz
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

from resources.lib.globals     import *
from resources.lib.rules       import RulesList
from resources.lib.fileaccess  import FileAccess
from resources.lib.concurrency import PoolHelper

class Manager(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        if isBusy() or PROPERTIES.getPropertyBool('Config.Running'):
            Dialog().notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            return REAL_SETTINGS.openSettings()
        
        with busy_dialog():
            setBusy(True)
            PROPERTIES.setPropertyBool('Config.Running',True)
            setLegacyPseudoTV(True)
            
            self.cntrlStates   = {}
            self.showingList   = True
            self.madeChanges   = False
            self.channelLimit  = CHANNEL_LIMIT
            self.monitor       = xbmc.Monitor()
            self.rules         = RulesList()
            self.pool          = PoolHelper()
            self.dialog        = Dialog()
            
            self.channel       = (kwargs.get('channel',1) - 1) #Convert from Channel to Index
            self.config        = kwargs.get('config')
            self.sysARG        = kwargs.get('sysARG')
            
            self.jsonRPC       = self.config.jsonRPC
            self.channels      = self.config.channels
            
            try:
                self.newChannel  = self.channels.getCitem()
                self.channelList = sorted(self.createChannelList(self.buildArray(), self.channels.getChannels()), key=lambda k: k['number'])
                self.channelList.extend(self.channels.getPredefinedChannels())
                self.newChannels = self.channelList.copy()
                self.doModal()
            except: 
                self.closeManager()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def onInit(self):
        self.log('onInit')
        try:
            self.focusItems    = {}
            self.spinner       = self.getControl(4)
            self.chanList      = self.getControl(5)
            self.itemList      = self.getControl(6)
            self.ruleList      = self.getControl(7)
            self.right_button1 = self.getControl(9001)
            self.right_button2 = self.getControl(9002)
            self.right_button3 = self.getControl(9003)
            self.right_button4 = self.getControl(9004)
            self.fillChanList(self.newChannels,focus=self.channel) #all changes made to self.newChannels before final save to self.channellist
        except Exception as e: 
            log("onInit, Failed! %s"%(e), xbmc.LOGERROR)
            self.closeManager()
        
        
    def buildArray(self):
        self.log('buildArray')
        ## Create blank array of citem templates. 
        for idx in range(self.channelLimit):
            newChannel = self.newChannel.copy()
            newChannel['number'] = idx + 1
            yield newChannel
  
        
    def createChannelList(self, channelArray, channelList):
        self.log('createChannelList')
        ## Fill blank array with channels from json.
        for item in channelArray:
            for channel in channelList:
                if item["number"] == channel["number"]:
                    item.update(channel)
            yield item


    def fillChanList(self, channelList, reset=False, focus=None):
        self.log('fillChanList')
        ## Fill chanList listitem for display. *reset draws new control list. *focus list index for channel position.
        self.togglechanList(True,reset=reset)
        self.toggleSpinner(self.chanList,True)
        listitems = (self.pool.poolList(self.buildChannelListItem,channelList))
        self.chanList.addItems(listitems)
        if focus is None: 
            self.chanList.selectItem(self.setFocusPOS(listitems))
        else:
            self.chanList.selectItem(focus)
        self.toggleSpinner(self.chanList,False)


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
                self.setLabels(self.right_button1,LANGUAGE(30119))#save
                self.setLabels(self.right_button2,LANGUAGE(30120))#cancel
                self.setLabels(self.right_button3,LANGUAGE(30133))#Delete
            else:
                self.setLabels(self.right_button1,LANGUAGE(30117))#close
                self.setLabels(self.right_button2,'')
                self.setLabels(self.right_button3,LANGUAGE(30133))#Delete
        else: # channelitems
            self.setVisibility(self.ruleList,False)
            self.setVisibility(self.chanList,False)
            self.setVisibility(self.itemList,True)
            self.itemList.reset()
            xbmc.sleep(100)
            self.itemList.selectItem(focus)
            self.setFocus(self.itemList)
            self.setLabels(self.right_button1,LANGUAGE(30118))#ok
            self.setLabels(self.right_button2,LANGUAGE(30120))#cancel
            self.setLabels(self.right_button3,'')
        
        
    def toggleSpinner(self, ctrl, state):
        self.setVisibility(self.spinner,state)
        # getSpinControl() #todo when avail.
        # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__control__list.html#ga9b9ac0cd03a6d14c732050f707943d42
        # ctrl.setPageControlVisible(state)


    def toggleruleList(self, state, focus=0):
        self.log('toggleruleList, state = %s, focus = %s'%(state,focus))
        if self.isVisible(self.chanList): 
            return self.dialog.notificationDialog(LANGUAGE(30001))
        if state: # rulelist
            self.setVisibility(self.itemList,False)
            self.setVisibility(self.ruleList,True)
            self.ruleList.selectItem(focus)
            self.setFocus(self.ruleList)
        else:
            self.setVisibility(self.ruleList,False)
            self.setVisibility(self.itemList,True)
            self.itemList.selectItem(focus)
            self.setFocus(self.itemList)
        

    def buildChannelListItem(self, channelData):
        label      = str(channelData["number"])
        label2     = channelData["name"]
        predefined = channelData["number"] > CHANNEL_LIMIT

        if predefined: 
            laColor = 'dimgray'
            if channelData.get('page',{}).get('end',0) == 0 and channelData.get('page',{}).get('total',0) == 0:
                chColor = 'red'
            else:
                chColor = 'orange'
        elif not label2: 
            chColor = 'dimgray'
            laColor = 'dimgray'
        else:
            if channelData['radio']:
                chColor = 'cyan'
            elif channelData.get('favorite',False):#todo
                chColor = 'yellow'
            else:
                chColor = 'white'
            laColor = 'white'
            
        label  = '[COLOR=%s][B]%s:[/COLOR][/B]'%(chColor,label)
        if label2: label2 = '[COLOR=%s]%s[/COLOR]'%(laColor,label2)
        path   = '|'.join(channelData.get("path",[]))
        prop   = {'description':LANGUAGE(30122)%(channelData['number']),'channelData':dumpJSON(channelData, sortkey=False),'chname':channelData.get('name',''),'chnumber':channelData.get('number','')}
        return buildMenuListItem(label,label2,iconImage=channelData.get("logo",''),url=path,propItem=prop)
        

    def setDescription(self, stid):#todo use control id and label
        PROPERTIES.setProperty('manager.description',LANGUAGE(stid))


    def setFocusPOS(self, listitems, chnum=None, ignore=True):
        for idx, listitem in enumerate(listitems):
            chnumber = int(cleanLabel(listitem.getLabel()))
            if  ignore and chnumber > CHANNEL_LIMIT: continue
            elif chnum is not None and chnum == chnumber: return idx
            elif chnum is None and cleanLabel(listitem.getLabel2()): return idx
        return 0
        
        
    def buildChannelItem(self, channelData, selkey='path'):
        self.log('buildChannelItem, channelData = %s'%(channelData))
        if self.isVisible(self.ruleList): return
        self.togglechanList(False)
        self.toggleSpinner(self.itemList,True)
        
        LABEL  = {'name'  : LANGUAGE(30087),
                  'path'  : LANGUAGE(30088),
                  'group' : LANGUAGE(30089),
                  'rules' : LANGUAGE(30090),
                  'radio' : LANGUAGE(30114),
                  'clear' : LANGUAGE(30092)}
                  
        DESC   = {'name'  : LANGUAGE(30123),
                  'path'  : LANGUAGE(30124),
                  'group' : LANGUAGE(30125),
                  'rules' : LANGUAGE(30126),
                  'radio' : LANGUAGE(30127),
                  'clear' : LANGUAGE(30128)}
                  
        listItems   = []
        channelProp = dumpJSON(channelData, sortkey=False)
        for key, value in channelData.items():
            if   key in ["number","type","logo","id","page","favorite","catchup"]: continue # keys to ignore, internal use only.
            elif key == 'rules' and not channelData.get('id',''): continue
            elif isinstance(value,list): 
                if   key == "group" :    value = ' / '.join(value)
                elif key == "path"  :    value = '|'.join(value)
            elif isinstance(value,bool): value = str(value)
            value = (value or '')
            listItems.append(buildMenuListItem(LABEL.get(key,''),value,url='|'.join(channelData.get("path",[])),iconImage=channelData.get("logo",COLOR_LOGO),propItem={'key':key,'value':value,'channelData':channelProp,'description':DESC.get(key,''),'chname':channelData.get('name',''),'chnumber':channelData.get('number','')}))
        listItems.append(buildMenuListItem(LABEL['clear'],'',propItem={'key':'clear','channelData':channelProp,'description':DESC['clear']}))
        self.toggleSpinner(self.itemList,False)
        self.itemList.addItems(listItems)
        self.itemList.selectItem([idx for idx, liz in enumerate(listItems) if liz.getProperty('key')== selkey][0])
        self.setFocus(self.itemList)


    def itemInput(self, channelListItem):
        key   = channelListItem.getProperty('key')
        value = channelListItem.getProperty('value')
        channelData = loadJSON(channelListItem.getProperty('channelData'))
        self.log('itemInput, channelData = %s, value = %s, key = %s'%(channelData,value,key))
        KEY_INPUT = {"name"  : {'func':self.dialog.inputDialog  ,'args':{'message':LANGUAGE(30123),'default':value}},
                     "path"  : {'func':self.dialog.browseDialog ,'args':{'heading':LANGUAGE(30124),'default':value,'monitor':True}},
                     "group" : {'func':self.dialog.selectDialog ,'args':{'list':getGroups(),'header':LANGUAGE(30125),'preselect':self.config.findItemsInLST(GROUP_TYPES,value.split(' / ')),'useDetails':False}},
                     "rules" : {'func':self.selectRules      ,'args':{'channelData':channelData}},
                     "radio" : {'func':self.toggleBool       ,'args':{'state':channelData.get('radio',False)}},
                     "clear" : {'func':self.clearChannel     ,'args':{'item':channelData}}}
           
        func = KEY_INPUT[key.lower()]['func']
        args = KEY_INPUT[key.lower()]['args']
        retval, channelData = self.validateInput(funcExecute(func, args),key, channelData)
        if retval is not None:
            self.madeChanges = True
            if isinstance(retval,list):
                retval = [args['list'][idx] for idx in retval]
            if key in self.newChannel:
                channelData[key] = retval
            elif key == 'clear':
                channelData = retval
        return channelData
   

    def toggleBool(self, state):
        self.log('toggleBool, state = %s'%(state))
        return not state


    def openEditor(self, path):
        self.log('openEditor, path = %s'%(path))
        if '|' in path: 
            path = path.split('|')
            path = path[0]#prompt user to select:
        media = 'video' if 'video' in path else 'music'
        if   '.xsp' in path: return self.config.openEditor(path,media)
        elif '.xml' in path: return self.config.openNode(path,media)
       
   
    def getChannelName(self, retval, channelData):
        self.log('getChannelName')
        if not channelData.get('name',''): 
            if retval.strip('/').endswith(('.xml','.xsp')):
                channelData['name'] = self.getSmartPlaylistName(retval)
            elif retval.startswith(('plugin://','upnp://','videodb://','musicdb://','library://','special://')):
                channelData['name'] = self.getMontiorList('name').getLabel()
            else:
                channelData['name'] = os.path.basename(os.path.dirname(retval)).strip('/')
        return channelData


    def getMontiorList(self, key='label'):
        self.log('getMontiorList')
        try:
            def getItem(item):
                return buildMenuListItem(label1=item.get(key,''), iconImage=item.get('icon',COLOR_LOGO))
                
            infoList = getInfoMonitor()
            itemList = [getItem(loadJSON(info)) for info in infoList]
            select   = self.dialog.selectDialog(itemList,LANGUAGE(30121)%(key.title()),useDetails=True,multi=False)
            if select is not None: return itemList[select]
        except Exception as e: self.log("getMontiorList, Failed! %s\ninfoList = %s"%(e,infoList), xbmc.LOGERROR)


    def getSmartPlaylistName(self, fle):
        self.log('getSmartPlaylistName')
        try:
            name = ''
            fle = fle.strip('/').replace('library://','special://userdata/library/')
            xml = FileAccess.open(fle, "r")
            string = xml.read()
            xml.close()
            if fle.endswith('xml'): key = 'label'
            else: key = 'name'
            match = re.compile('<%s>(.*?)\</%s>'%(key,key), re.IGNORECASE).search(string)
            if match: name = match.group(1)
            log("getSmartPlaylistName fle = %s, name = %s"%(fle,name))
        except: log("getSmartPlaylistName return unable to parse %s"%(fle))
        return name


    def getChannelIcon(self, channelData, path=None, name=None):
        self.log('getChannelIcon')
        if name is None: name = channelData.get('name','')
        if path is None: path = channelData.get('path','')
        if not name: return channelData
        logo = channelData.get('logo','')
        if not logo or logo.endswith(('wlogo.png','logo.png','icon.png')):
            logo = self.jsonRPC.getLogo(name, LANGUAGE(30171), path, featured=True)
            if logo.endswith(('wlogo.png','logo.png','icon.png')): 
                channelData['logo'] = ''
            else: 
                channelData['logo'] = logo
        return channelData
        
    
    def validateInput(self, retval, key, channelData):
        self.log('validateInput')
        if retval is None:   return None  , channelData
        elif key == 'clear': return retval, channelData
        elif key == 'path':
            retval, channelData = self.validatePath(channelData, retval, key)
            if not retval: return None, channelData
            if retval.strip('/').endswith(('.xml','.xsp')):
                retval, channelData = self.validatePlaylist(retval, channelData)
            channelData = self.getChannelName(retval, channelData)
            channelData = self.getChannelIcon(channelData, path=retval)
        elif key == 'name':
            if not self.validateLabel(retval, key): 
                return None, channelData
            channelData = self.getChannelIcon(channelData, name=retval)
        channelData = self.getID(channelData)
        return retval, channelData
        
        
    def validateLabel(self, label, key):
        self.log('validateLabel')
        if len(label) < 1 and len(label) > 128: 
            self.dialog.notificationDialog(LANGUAGE(30112)%key.title())
            return False
        else:
            return True
    
    
    def validatePlaylist(self, path, channelData):
        if path.strip('/').endswith('.xml'):
            newPath = path.strip('/').replace('library://','special://userdata/library/')
            dir, file =(os.path.split(newPath))
            dir = dir.replace('special://userdata/library',CACHE_LOC)
            cachefile = os.path.join(dir,file)
        elif path.endswith('.xsp'):
            cachefile = os.path.join(CACHE_LOC,os.path.basename(path))
        else: return path, channelData
        self.log('validatePlaylist, path = %s, cachefile = %s'%(path,cachefile))
        if FileAccess.copy(path, cachefile): 
            return cachefile, channelData
        return path, channelData


    def validatePath(self, channelData, path, key):
        self.log('validatePath')
        found = False
        radio = (channelData.get('radio','') or (channelData['type'] == LANGUAGE(30097) or path.startswith('musicdb://')))
        media = 'music' if radio else 'video'
        self.toggleSpinner(self.itemList,True)
        fitem = self.jsonRPC.playableVFS(path, media)
        if fitem is not None:
            found = True
            seek  = fitem.get('seek',True)
            #todo set seeklock rule if seek == False  #Player.SeekEnabled todo verify seek
        self.toggleSpinner(self.itemList,False)
        self.log('validatePath, path = %s, found duration = %s'%(path,found))
        if not found: 
            self.dialog.notificationDialog('%s\n%s'%(LANGUAGE(30112)%key.title(),LANGUAGE(30115)))
            return None, channelData
        channelData['radio'] = radio
        return path, channelData
        
        
    def getID(self, channelData):
        self.log('getID')
        if channelData.get('name','') and channelData.get('path',''): 
            channelData['id'] = getChannelID(channelData['name'], channelData['path'], channelData['number'])
            self.log('getID, id = %s'%(channelData['id']))
        return channelData
        
        
    def validateChannel(self, channelData):
        if not channelData.get('name','') or not channelData.get('path',[]): 
            return None
        channelData = self.getID(channelData)
        if channelData['number'] <= CHANNEL_LIMIT: 
            channelData['type'] = LANGUAGE(30171) #custom
        if not channelData.get('logo',''):
            channelData = self.getChannelIcon(channelData)
        return channelData
    
    
    def validateChannels(self, channelList):
        self.log('validateChannels')
        return sorted(self.pool.poolList(self.validateChannel,channelList), key=lambda k: k['number'])
              

    def saveChannelItems(self, channelData, channelPOS):
        self.log('saveChannelItems, channelPOS = %s'%(channelPOS))
        self.newChannels[channelPOS] = channelData
        self.fillChanList(self.newChannels,reset=True,focus=channelPOS)
        
    
    def saveChanges(self):
        self.log("saveChanges")
        if self.dialog.yesnoDialog("Changes Detected, Do you want to save?"): return self.saveChannels() 
        else: self.closeManager()


    def saveChannels(self):
        log('saveChannels')
        if   not self.madeChanges: return
        elif not self.dialog.yesnoDialog(LANGUAGE(30073)): return
        self.toggleSpinner(self.chanList,True)
        self.newChannels = self.validateChannels(self.newChannels)
        self.channelList = self.validateChannels(self.channelList)
        difference = sorted(diffLSTDICT(self.channelList,self.newChannels), key=lambda k: k['number'])
        print('difference',difference)
        [self.channels.add(citem) if citem in self.newChannels else self.channels.remove(citem) for citem in difference]
        self.channels.save()
        self.dialog.notificationDialog(LANGUAGE(30053))
        self.toggleSpinner(self.chanList,False)
        SETTINGS.setSetting('Select_Channels','[B]%s[/B] Channels'%(len(self.channelList)))
        self.closeManager()
            
        
    def clearChannel(self, item, prompt=True):
        self.log('clearChannel')
        if prompt and not self.dialog.yesnoDialog(LANGUAGE(30092)): return item
        self.madeChanges = True
        nitem = self.newChannel.copy()
        nitem['number'] = item['number'] #preserve channel number
        return nitem


    def buildRuleItems(self, channelData, append=False):
        self.log('buildRuleItems')
        self.toggleSpinner(self.ruleList,True)
        if append:
            ruleInstances = self.rules.loadRules([channelData]).get(channelData['id'],[]) #load existing rules
        else:
            ruleInstances = self.rules.buildRuleList([channelData]).get(channelData['id'],[]) #load all rules
        listitems = self.pool.poolList(self.buildRuleListItem,ruleInstances,channelData)
        if append: listitems.append(buildMenuListItem('','Add New Rule',url='-1',propItem={'channelData':dumpJSON(channelData)}))
        self.toggleSpinner(self.ruleList,False)        
        self.ruleList.reset()
        xbmc.sleep(100)
        return listitems
        
        
    def buildRuleListItem(self, data):
        ruleInstance, channelData= data
        rule = {'id':ruleInstance.myId,'name':ruleInstance.name,'description':ruleInstance.description,'labels':ruleInstance.optionLabels,'values':ruleInstance.optionValues,'title':ruleInstance.getTitle()}
        print(rule)
        prop = {'description':rule['description'],'rule':dumpJSON(rule),'channelData':dumpJSON(channelData),'chname':channelData.get('name',''),'chnumber':channelData.get('number','')}
        return buildMenuListItem(rule['title'],rule['description'],iconImage=channelData.get("logo",''),url=str(rule['id']),propItem=prop)


    def selectRules(self, channelData):
        self.log('selectRules')
        if not self.validateChannel(channelData): return self.dialog.notificationDialog(LANGUAGE(30139))
        listitems = self.buildRuleItems(channelData, append=True)
        self.toggleruleList(True)
        self.ruleList.addItems(listitems)
        
        # select = self.dialog.selectDialog(listitems,LANGUAGE(30135),useDetails=True,multi=False)
        # if select is None: return self.dialog.notificationDialog(LANGUAGE(30001))
        # print(listitems[select].getLabel())
        
        # self.ruleList.addItems(listitems)
        
        # return channelData
        # select = self.dialog.selectDialog(listitems,LANGUAGE(30135),useDetails=True,multi=False)
        # if select is None: return self.dialog.notificationDialog(LANGUAGE(30001))
        # return listitems[select]
        
        # ruleid   = int(listitem.getPath())
        # if ruleid < 0: 
            # rules    = sorted(self.fillRules(channelData), key=lambda k: k['id'])
            # listitem = self.buildRuleItems(rules, channelData)
            # ruleid   = int(listitem.getPath())
        # ruleSelect = [idx for idx, rule in enumerate(self.channels.ruleList) if rule['id'] == ruleid]
        # self.selectRuleItems(channelData, rules, self.channels.ruleList[ruleSelect[0]])
        # self.toggleruleList(False)
        return channelData['rules']


    def selectRuleItems(self, item):    
        self.log('selectRuleItems')
        print(item)
        ruleItem    = loadJSON(item['item'].getProperty('rule'))
        channelData = loadJSON(item['item'].getProperty('channelData'))
        listitems = self.buildRuleItems(channelData)
        
        optionIDX = self.dialog.selectDialog(listitems,LANGUAGE(30135),multi=False)
        print(ruleSelect)
        # ruleSelect['options'][str(optionIDX)].update({'value':ruleInstance.onAction(optionIDX)})
        # print(ruleSelect)
        # self.selectRuleItems(channelData, rules, ruleSelect)
        
        
        # self.ruleList.addItems(listitems)
        # ruleSelect = {}
        # for rule in channelRules:
            # if rule['id'] == ruleItem['id']: 
                # ruleSelect = rule
        # print(ruleItem,channelRules,ruleSelect)
                
        # if ruleSelect.get('action',None) is None: return self.dialog.notificationDialog(LANGUAGE(30001))
        # ruleInstance  = ruleSelect.get('action',None)
        # valueitems    = (self.pool.poolList(self.buildRuleListItem,rules,channelData))
        # listitems     = [buildMenuListItem(ruleInstance.optionLabels[idx],str(ruleInstance.optionValues[idx]),iconImage=channelData.get("logo",''),url=str(ruleInstance.myId),propItem={'citem':dumpJSON(channelData)}) for idx, label in enumerate(ruleInstance.optionLabels)]
        # self.ruleList.addItems(listitems)
        # optionIDX    = self.dialog.selectDialog(listitems,LANGUAGE(30135),multi=False)
        # print(ruleSelect)
        # ruleSelect['options'][str(optionIDX)].update({'value':ruleInstance.onAction(optionIDX)})
        # print(ruleSelect)
        # self.selectRuleItems(channelData, rules, ruleSelect)
        
            
    def saveRuleList(self, items):
        self.log('saveRuleList')
        print(items)
        self.toggleruleList(False)
            
            
    def fillRules(self, channelData): # prepare "new" rule list, remove existing.
        chrules  = sorted(self.channels.getChannelRules(channelData, self.newChannels), key=lambda k: k['id'])
        ruleList = self.channels.rules.copy()
        for rule in ruleList:
            for chrule in chrules:
                if rule['id'] == chrule['id']: continue
            yield rule


    def selectLogo(self, channelData, channelPOS):
        # todo select from resources, browse resources
        self.log('selectLogo, channelPOS = %s'%(channelPOS))
        if self.isVisible(self.ruleList): return
        retval = self.dialog.browseDialog(type=1,heading=LANGUAGE(30111),default=channelData.get('icon',''),shares='files',mask=IMAGE_EXTS,prompt=False)
        if retval in [None,'',channelData.get('icon','')]: return
        self.madeChanges = True
        channelData['logo'] = retval
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
        except Exception as e: self.log("setLabels, failed! " + str(e), xbmc.LOGERROR)
    
    
    def getLabels(self, cntrl):
        try:
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            return cntrl.getLabel(), cntrl.getLabel2()
        except Exception as e: return '',''
        
        
    def setImages(self, cntrl, image='NA.png'):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setImage(image)
        except Exception as e: self.log("setImages, failed! " + str(e), xbmc.LOGERROR)
 

    def closeManager(self):
        self.log('closeManager')
        PROPERTIES.setPropertyBool('Config.Running',False)
        setLegacyPseudoTV(False)
        setBusy(False)
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
                
            self.focusItems['chanList']['citem'] = loadJSON(channelitem.getProperty('channelData'))
            self.focusItems['itemList']['citem'] = loadJSON(channelListItem.getProperty('channelData'))
            self.focusItems['ruleList']['citem'] = loadJSON(ruleListItem.getProperty('channelData'))
            
            chnumber = cleanLabel(channelitem.getLabel())
            if chnumber.isdigit(): 
                try:
                    self.focusItems['number'] = int(chnumber)
                except:
                    self.focusItems['number'] = float(chnumber)
            elif self.focusItems['chanList']['citem'].get('number',''):
                self.focusItems['number'] = self.focusItems['chanList']['citem']['number']
            else:
                self.focusItems['number'] = channelPOS + 1
            return self.focusItems
        except: return {}

    
    def onFocus(self, controlId):
        self.log('onFocus: controlId = %s'%(controlId))

        
    def onAction(self, act):
        actionId = act.getId()
        self.log('onAction: actionId = %s'%(actionId))
        items = self.getFocusVARS()
        if actionId in ACTION_PREVIOUS_MENU:
            if xbmcgui.getCurrentWindowDialogId() == "13001":
                xbmc.executebuiltin("ActivateWindow(Action(Back)")
            elif self.isVisible(self.ruleList): self.toggleruleList(False)
            elif self.isVisible(self.itemList): self.togglechanList(True,focus=items['chanList']['position'])
            elif self.isVisible(self.chanList):
                if    self.madeChanges: self.saveChanges()
                else: self.closeManager()
        
        
    def onClick(self, controlId):
        self.log('onClick: controlId = %s'%(controlId))
        items = self.getFocusVARS(controlId)
        if self.isVisible(self.chanList):
            channelData = items['chanList']['citem'] 
        else:
            channelData = items['itemList']['citem']
            
        if   controlId == 0: self.closeManager()
        elif controlId == 5: self.buildChannelItem(channelData)
        elif controlId == 6:
            if items['number'] > CHANNEL_LIMIT: return self.dialog.notificationDialog(LANGUAGE(30110))
            self.buildChannelItem(self.itemInput(items['itemList']['item']),items['itemList']['item'].getProperty('key'))
        elif controlId == 7:
            self.selectRuleItems(items['ruleList'])
        elif controlId == 10: 
            if items['number'] > CHANNEL_LIMIT: return self.dialog.notificationDialog(LANGUAGE(30110))
            self.selectLogo(channelData,items['chanList']['position'] )
        elif controlId == 9001:
            if   items['label'] == LANGUAGE(30117):#'Close'
                self.closeManager()
            elif items['label'] == LANGUAGE(30119):#'Save'
                self.saveChannels()
            elif items['label'] == LANGUAGE(30118):#'OK'
                if self.isVisible(self.itemList) and self.madeChanges:
                    self.saveChannelItems(channelData,items['chanList']['position'])
                elif self.isVisible(self.ruleList): 
                    self.toggleruleList(False)
                else: 
                    self.togglechanList(True,focus=items['chanList']['position'] )
        elif controlId == 9002:
            if items['label'] == LANGUAGE(30120):#'Cancel'
                if self.isVisible(self.chanList) and self.madeChanges:  
                    self.saveChanges()
                elif self.isVisible(self.ruleList): 
                    self.toggleruleList(False)
                else: 
                    self.togglechanList(True,focus=items['chanList']['position'] )
        elif controlId == 9003:
            if items['number'] > CHANNEL_LIMIT: return self.dialog.notificationDialog(LANGUAGE(30110))
            self.saveChannelItems(self.clearChannel(channelData),items['chanList']['position'])