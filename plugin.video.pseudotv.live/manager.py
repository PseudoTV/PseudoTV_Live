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
from config                    import Config
from resources.lib.parser      import JSONRPC, Channels
from resources.lib.fileaccess  import FileAccess

class Manager(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        if isBusy():
            notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
            return REAL_SETTINGS.openSettings()
        elif getProperty('Config.Running') == "True": return
        with busy_dialog():
            setBusy(True)
            setProperty('Config.Running','True')
            self.showingList   = True
            self.madeChanges   = False
            self.myMonitor     = MY_MONITOR
            self.config        = Config()
            self.jsonRPC       = JSONRPC()
            self.cntrlStates   = {}
            self.channel       = 0
            self.channels      = Channels()
            self.channelLimit  = CHANNEL_LIMIT
            self.newChannel    = self.channels.getTemplate(ADDON_VERSION).get('channels',[])[0]
            self.channelList   = sorted(self.createChannelList(self.buildArray(), self.channels.getChannels()), key=lambda k: k['number'])
            self.channelList.extend(self.channels.getPredefined())
            self.newChannels   = self.channelList.copy()
        self.doModal()


    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)
    

    def onInit(self):
        self.log('onInit')
        try:
            self.focusItems    = {}
            self.spinner       = self.getControl(4)
            self.chanList      = self.getControl(5)
            self.itemList      = self.getControl(6)
            self.right_button1 = self.getControl(9001)
            self.right_button2 = self.getControl(9002)
            self.right_button3 = self.getControl(9003)
            self.fillChanList(self.newChannels) #all changes made to self.newChannels before final save to self.channellist
        except Exception as e: 
            log("onInit, Failed! %s"%(e), xbmc.LOGERROR)
            self.closeManager()
        
        
    def togglechanList(self, state, reset=False, focus=0):
        # toggle between channellist and channelitems
        if state: # channellist
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
        # getSpinControl() #todo when working
        # ctrl.setPageControlVisible(state)


    def setDescription(self, stid):
        setProperty('manager.description',LANGUAGE(stid))


    def setFocusPOS(self, listitems, chnum=None, ignore=True):
        for idx, listitem in enumerate(listitems):
            chnumber = int(cleanLabel(listitem.getLabel()))
            if   ignore and chnumber > CHANNEL_LIMIT: continue
            elif chnum is not None and chnum == chnumber: return idx
            elif chnum is None and cleanLabel(listitem.getLabel2()): return idx
        return 0
        
        
    def fillChanList(self, channelList, reset=False, focus=None):
        self.log('fillChanList')
        self.togglechanList(True,reset)
        self.toggleSpinner(self.chanList,True)
        listitems = list(PoolHelper().poolList(self.buildChannelListItem,channelList))
        self.chanList.addItems(listitems)
        if focus is None: 
            self.chanList.selectItem(self.setFocusPOS(listitems))
        else:
            self.chanList.selectItem(focus)
        self.toggleSpinner(self.chanList,False)


    def buildChannelListItem(self, channelData):
        predefined = channelData["number"] > CHANNEL_LIMIT
        label  = str(channelData["number"])
        label2 = channelData["name"]

        if predefined: 
            chColor = 'orange'
            laColor = 'dimgray'
        elif not label2: 
            chColor = 'dimgray'
            laColor = 'dimgray'
        else:
            if channelData['radio']:
                chColor = 'yellow'
            else:
                chColor = 'white'
            laColor = 'white'
        label  = '[COLOR=%s][B]%s:[/COLOR][/B]'%(chColor,label)
        if label2: label2 = '[COLOR=%s]%s[/COLOR]'%(laColor,label2)
        path   = '|'.join(channelData.get("path",[]))
        prop   = {'description':LANGUAGE(30122)%(channelData['number']),'channelData':dumpJSON(channelData, sortkey=False)}
        return buildMenuListItem(label,label2,channelData.get("logo",''),path,propItem=prop)
        

    def buildChannelItem(self, channelData, selkey='path'):
        self.log('buildChannelItem, channelData = %s'%(channelData))
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
            if key in ["number","type","logo","id","xmltv","page"]: continue # keys to ignore, internal use only.
            elif isinstance(value,list): 
                if   key == "group" :    value = ' / '.join(value)
                elif key == "path"  :    value = '|'.join(value)
            elif isinstance(value,bool): value = str(value)
            value = (value or '')
            listItems.append(buildMenuListItem(LABEL[key],value,channelData.get("logo",COLOR_LOGO),propItem={'key':key,'value':value,'channelData':channelProp,'description':DESC[key]}))
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
        KEY_INPUT = {"name"  : {'func':inputDialog      ,'args':{'message':LANGUAGE(30123),'default':value}},
                     "path"  : {'func':browseDialog     ,'args':{'heading':LANGUAGE(30124),'default':value,'monitor':True}},
                     "group" : {'func':selectDialog     ,'args':{'list':getGroups(),'header':LANGUAGE(30125),'preselect':findItemsIn(GROUP_TYPES,value.split(' / ')),'useDetails':False}},
                     "rules" : {'func':self.selectRules ,'args':{'channelData':channelData}},
                     "radio" : {'func':self.toggleBool  ,'args':{'state':channelData.get('radio',False)}},
                     "clear" : {'func':self.clearChannel,'args':{'item':channelData}}}
           
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


    def getChannelName(self, retval, channelData):
        self.log('getChannelName')
        if not channelData['name']: 
            if retval.strip('/').endswith(('.xml','.xsp')):
                channelData['name'] = self.getSmartPlaylistName(retval)
            elif retval.startswith(('plugin://','upnp://','videodb://','musicdb://','library://','special://')):
                channelData['name'] = self.getLabelList()
            else:
                channelData['name'] = os.path.basename(os.path.dirname(retval)).strip('/')
        return channelData

   
    def getLabelList(self):
        self.log('getLabelList')
        labelList = list(filter(lambda x: x != "",getInfoMonitor().get('labelList',[])))
        select = selectDialog(labelList,LANGUAGE(30121),useDetails=False,multi=False)
        if select: return labelList[select]
        

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
        if not logo or logo in [ICON,COLOR_LOGO,MONO_LOGO,LOGO]:
            channelData['logo'] = self.jsonRPC.getLogo(name, 'Custom', path, featured=True)
        return channelData
        
    
    def validateInput(self, retval, key, channelData):
        self.log('validateInput')
        if retval is None:   return None  , channelData
        elif key == 'clear': return retval, channelData
        elif key == 'path':
            if not self.validatePath(channelData, retval, key): 
                return None, channelData
                
            if retval.strip('/').endswith(('.xml','.xsp')):
                retval, channelData = self.validatePlaylist(retval, channelData)
                
            channelData = self.getChannelName(retval, channelData)
            channelData = self.getChannelIcon(channelData, path=retval)
        elif key == 'name':
            if not self.validateLabel(retval, key): 
                return None, channelData
            channelData = self.getChannelIcon(channelData, name=retval)
        return retval, channelData
        
        
    def validateLabel(self, label, key):
        self.log('validateLabel')
        if len(label) < 1 and len(label) > 128: 
            notificationDialog(LANGUAGE(30112)%key.title())
            return False
        else:
            return True
    
    
    def validatePlaylist(self, path, channelData):
        self.log('validatePlaylist')
        return path, channelData
        # if not self.m3u.isClient(): return channelData, path
        # path, filename = os.path.split(retval)
        # cache_fle = os.path.join(CACHE_LOC,filename)
        # FileAccess.copy(retval, cache_fle): return cache_fle)


    def validatePath(self, channelData, path, key):
        self.log('validatePath')
        radio = channelData.get('radio',False)
        media = 'music' if radio else 'video'
        self.toggleSpinner(self.itemList,True)
        found = self.jsonRPC.existsVFS(path, media)
        self.toggleSpinner(self.itemList,False)
        self.log('validatePath, path = %s, found duration = %s'%(path,found))
        if not found: notificationDialog('%s\n%s'%(LANGUAGE(30112)%key.title(),LANGUAGE(30115)))
        return found
        

    def validateID(self, channelData):
        self.log('validateID')
        # idLST = [channel['id'] for channel in self.newChannels if channel.get('id',None)]
        # print('idLST',idLST)
        channelData['id'] = getChannelID(channelData['name'], channelData['path'], channelData['number'])
        return channelData
        # if id not in idLST: 
            # channelData['id'] = id
            # return channelData
        # else:
            # channelData['name'] = '%s.%s'%(channelData['name'],random.randint(1,10))
            # return self.validateID(channelData)
        

    def validateChannel(self, channelData):
        if not channelData.get('name','') or not channelData.get('path',[]): 
            return None
            
        if channelData['number'] <= CHANNEL_LIMIT: 
            channelData['type'] = 'Custom'
            
        if not channelData.get('id',''):
            channelData = self.validateID(channelData)
            
        if not channelData.get('logo',''):
            channelData = self.getChannelIcon(channelData)
       
        return channelData
    
    
    def validateChannels(self, channelList):
        self.log('validateChannels')
        return sorted(PoolHelper().poolList(self.validateChannel,channelList), key=lambda k: k['number'])
              

    def saveChannelItems(self, channelData, channelPOS):
        self.log('saveChannelItems, channelPOS = %s'%(channelPOS))
        self.itemList.reset() #todo find origins of LANGUAGE(30088) "Browse Path" label bug.
        self.newChannels[channelPOS] = channelData
        self.fillChanList(self.newChannels,reset=True,focus=channelPOS)
        
    
    def saveChanges(self):
        self.log("saveChanges")
        if yesnoDialog("Changes Detected, Do you want to save?"): return self.saveChannels() 
        else: self.closeManager()


    def saveChannels(self):
        log('saveChannels')
        if   not self.madeChanges: return
        elif not yesnoDialog(LANGUAGE(30073)): return
        self.toggleSpinner(self.itemList,True)
        self.newChannels = self.validateChannels(self.newChannels)
        self.channelList = self.validateChannels(self.channelList)
        difference = sorted(diffDICT(self.newChannels,self.channelList), key=lambda k: k['number'])
        [self.channels.add(citem) if citem in self.newChannels else self.channels.remove(citem) for citem in difference]
        self.channels.save()
        notificationDialog(LANGUAGE(30053))
        self.toggleSpinner(self.itemList,False)
        self.closeManager()
            
        
    def clearChannel(self, item, prompt=True):
        self.log('clearChannel')
        if prompt and not yesnoDialog(LANGUAGE(30092)): return item
        self.madeChanges = True
        nitem = self.newChannel.copy()
        nitem['number'] = item['number'] #preserve channel number
        return nitem


    def buildArray(self):
        self.log('buildArray')
        for idx in range(self.channelLimit):
            newChannel = self.newChannel.copy()
            newChannel['number'] = idx + 1
            yield newChannel
                
                
    def createChannelList(self, channelArray, channelList):
        self.log('createChannelList')#todo elegant solution?
        for item in channelArray:
            for channel in channelList:
                if item["number"] == channel["number"]:
                    item.update(channel)
            yield item


    def selectRules(self, channelData):
        self.log('selectRules')
        notificationDialog('Coming Soon')
    
    
    def selectLogo(self, channelData, channelPOS):
        self.log('selectLogo, channelPOS = %s'%(channelPOS))
        retval = browseDialog(type=1,heading=LANGUAGE(30111),default=channelData.get('icon',''),shares='files',mask=IMAGE_EXTS,prompt=False)
        if not retval or not yesnoDialog(LANGUAGE(30091)): return
        self.madeChanges = True
        channelData['logo'] = retval
        if self.isVisible(self.itemList): self.buildChannelItem(channelData)
        else:
            self.newChannels[channelPOS] = channelData
            self.fillChanList(self.newChannels,reset=True,focus=channelPOS)


    def isVisible(self, cntrl):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            state = bool(cntrl.isVisible())
        except: state = self.cntrlStates.get(cntrl.getId(),False)
        self.log('isVisible, cntrl = ' + str(cntrl.getId()) + ', state = ' + str(state))
        return state
        
        
    def setVisibility(self, cntrl, state):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setVisible(state)
            self.cntrlStates[cntrl.getId()] = state
            self.log('setVisibility, cntrl = ' + str(cntrl.getId()) + ', state = ' + str(state))
        except Exception as e: self.log("setVisibility, failed! " + str(e), xbmc.LOGERROR)
    
    
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
        setProperty('Config.Running','False')
        setBusy(False)
        self.close()


    def setFocusVARS(self, controlId=None):
        if controlId not in [5,6,10,9001,9002,9003]: return self.focusItems
        self.log('setFocusVARS, controlId = %s'%(controlId))
        try:
            channelitem     = (self.chanList.getSelectedItem()     or xbmcgui.ListItem())
            channelPOS      = (self.chanList.getSelectedPosition() or 0)
            channelListItem = (self.itemList.getSelectedItem()     or xbmcgui.ListItem())
            itemPOS         = (self.itemList.getSelectedPosition() or 0)

            self.focusItems = {'chanList':{'item'    :channelitem,
                                           'position':channelPOS},
                               'itemList':{'item'    :channelListItem,
                                           'position':itemPOS}}
            if controlId is not None: 
                label, label2 = self.getLabels(controlId)
                self.focusItems.update({'label':label,'label2':label2})
                
            self.focusItems['chanList']['data'] = loadJSON(channelitem.getProperty('channelData'))
            self.focusItems['itemList']['data'] = loadJSON(channelListItem.getProperty('channelData'))
            
            chnumber = cleanLabel(channelitem.getLabel())
            if chnumber.isdigit(): 
                self.focusItems['number'] = int(chnumber)
            elif self.focusItems['chanList']['data'].get('number',''):
                self.focusItems['number'] = self.focusItems['chanList']['data']['number']
            else:
                self.focusItems['number'] = channelPOS + 1
            return self.focusItems
        except: return {}


    def onAction(self, act):
        actionId = act.getId()
        self.log('onAction: actionId = %s'%(actionId))
        if actionId in ACTION_PREVIOUS_MENU:
            if xbmcgui.getCurrentWindowDialogId() == "13001":
                xbmc.executebuiltin("ActivateWindow(Action(Back)")
            elif self.isVisible(self.itemList): self.togglechanList(True,focus=channelPOS)
            elif self.isVisible(self.chanList):
                if    self.madeChanges: self.saveChanges()
                else: self.closeManager()
        
    
    def onFocus(self, controlId):
        self.log('onFocus: controlId = %s'%(controlId))

        
    def onClick(self, controlId):
        self.log('onClick: controlId = %s'%(controlId))
        items = self.setFocusVARS(controlId)
        if self.isVisible(self.chanList):
            channelData = items['chanList']['data'] 
        else:
            channelData = items['itemList']['data']
            
        if   controlId == 0: self.closeManager()
        elif controlId == 5: self.buildChannelItem(channelData)
        elif controlId == 6:
            if items['number'] > CHANNEL_LIMIT: return notificationDialog(LANGUAGE(30110))
            self.buildChannelItem(self.itemInput(items['itemList']['item']))
        elif controlId == 10: 
            if items['number'] > CHANNEL_LIMIT: return notificationDialog(LANGUAGE(30110))
            self.selectLogo(channelData,items['chanList']['position'] )
        elif controlId == 9001:
            if   items['label'] == LANGUAGE(30117):#'Close'
                self.closeManager()
            elif items['label'] == LANGUAGE(30119):#'Save'
                self.saveChannels()
            elif items['label'] == LANGUAGE(30118):#'OK'
                if self.isVisible(self.itemList) and self.madeChanges:
                    self.saveChannelItems(channelData,items['chanList']['position'])
                else: 
                    self.togglechanList(True,focus=items['chanList']['position'] )
        elif controlId == 9002:
            if items['label'] == LANGUAGE(30120):#'Cancel'
                if self.isVisible(self.chanList) and self.madeChanges: 
                    self.saveChanges()
                else: 
                    self.togglechanList(True,focus=items['chanList']['position'] )
        elif controlId == 9003:
            if items['number'] > CHANNEL_LIMIT: return notificationDialog(LANGUAGE(30110))
            self.saveChannelItems(self.clearChannel(channelData),items['chanList']['position'])
            
if __name__ == '__main__': 
    Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default")
    del Manager