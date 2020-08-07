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

from resources.lib.globals import *
from config                import Config
from resources.lib.parser  import JSONRPC, Channels

class Manager(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        with busy_dialog():
            self.showingList   = True
            self.madeChange    = False
            self.myMonitor     = MY_MONITOR
            self.config        = Config()
            self.jsonRPC       = JSONRPC()
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
        self.cntrlStates = {}
        self.spinner     = self.getControl(4)
        self.chanList    = self.getControl(5)
        self.itemList    = self.getControl(6)
        self.togglechanList(True)
        self.toggleSpinner(self.chanList,True)
        self.fillChanList(self.channelList)
        
        
    def togglechanList(self, state):
        if state:
            self.getControl(9001).setLabel('Close')
            self.getControl(9002).setLabel('')
            self.getControl(9003).setLabel('')
            self.setVisibility(self.itemList,False)
            self.setVisibility(self.chanList,True)
            self.setFocus(self.chanList)
        else:
            self.getControl(9001).setLabel('Save')
            self.getControl(9002).setLabel('Cancel')
            self.getControl(9003).setLabel('')
            self.setVisibility(self.chanList,False)
            self.setVisibility(self.itemList,True)
            self.setFocus(self.itemList)
        
        
    def toggleSpinner(self, ctrl, state):
        self.setVisibility(self.spinner,state)
        # ctrl.setPageControlVisible(state)
        
        
    def fillChanList(self, channelList):
        self.log('fillChanList')
        self.chanList.addItems(list(PoolHelper().poolList(self.buildChannelListItem,channelList)))
        self.toggleSpinner(self.chanList,False)
           
           
    def buildChannelListItem(self, channel):
        predefined = channel["number"] > CHANNEL_LIMIT
        chColor = 'white'
        laColor = 'white'
        label  = str(channel["number"])
        label2 = channel["name"]
        
        if predefined: 
            chColor = 'dimgray'
            laColor = 'dimgray'
        elif not label2: 
            chColor = 'dimgray'
            laColor = 'dimgray'
        
        # label  = '[COLOR=%s][B]%s:[/COLOR][/B]'%(chColor,label)
        # label2 = '[COLOR=%s]%s[/COLOR]'%(laColor,label2)
        type   = (channel['type'] or 'Custom')
        path   = '|'.join(channel.get("path",[]))
        logo   = channel.get("logo",self.jsonRPC.getLogo(channel['name'], type, channel['path'], featured=True))
        prop   = {'writer':dumpJSON(channel, sortkey=False)}
        return buildMenuListItem(label,label2,logo,path,propItem=prop)
        

    def buildChannelItem(self, channel):
        self.log('buildChannelItem')
        self.togglechanList(False)
        
        LABEL2 = {'name'  : LANGUAGE(30087),
                  'path'  : LANGUAGE(30088),
                  'groups': LANGUAGE(30089),
                  'rules' : LANGUAGE(30090)}
        channelData = loadJSON(channel.getProperty('writer'))
        listItems = []
        for key, value in channelData.items():
            if key in ["number","type","logo","id","xmltv","radio","page"]: continue # keys to ignore, internal use only.
            if not value: value = ''
            elif isinstance(value,list): 
                if   key == "groups": value = ' / '.join(value)
                elif key == "path"  : value = '|'.join(value)
            listItems.append(buildMenuListItem(LABEL2[key],value,channelData.get("logo",LOGO),propItem={'key':key,'value':value}))
        self.itemList.addItems(listItems)
        
        
    def itemInput(self, channelData):
        key   = channelData.getProperty('key')
        value = channelData.getProperty('value')
        log('Manager: itemInput, value = %s, key = %s'%(value,key))
        KEY_INPUT = {"type"  : {'func':selectDialog     ,'args':()},# unneeded ATM
                     "name"  : {'func':inputDialog      ,'args':{'message':LANGUAGE(30087),'default':value}},
                     "path"  : {'func':browseDialog     ,'args':{'heading':LANGUAGE(30088),'default':value}},
                     "groups": {'func':selectDialog     ,'args':{'list':GROUP_TYPES,'header':LANGUAGE(30089),'preselect':findItemsIn(GROUP_TYPES,value.split(' / ')),'useDetails':False}},
                     "rules" : {'func':self.selectRules ,'args':{'channelData':channelData}},
                     "clear" : {'func':self.clearChannel,'args':{'item':channelData}},
                     "save"  : {'func':self.addChannel  ,'args':{'item':channelData}}}
           
        func = KEY_INPUT[key.lower()]['func']
        args = KEY_INPUT[key.lower()]['args']# move args to kwargs?
        if isinstance(args,dict): 
            retval = func(**args)
        else: 
            retval = func()
        if retval:
            if key in ['clear']: return retval
            elif isinstance(retval,list):
                retval = [args[0][idx] for idx in retval]
            channelData[key.lower()] = retval
        channelData['type'] = 'Custom' #todo 
        return channelData
        
   
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
        except Exception as e: self.log("setLabels, failed! " + str(e), xbmc.LOGERROR)
    
    
    def getLabels(self, cntrl):
        try:
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            return cntrl.getLabel(), cntrl.getLabel2()
        except Exception as e: self.log("getLabels, failed! " + str(e), xbmc.LOGERROR)
        return '',''
        
    
    def setImages(self, cntrl, image='NA.png'):
        try: 
            if isinstance(cntrl, int): cntrl = self.getControl(cntrl)
            cntrl.setImage(image)
        except Exception as e: self.log("setImages, failed! " + str(e), xbmc.LOGERROR)
 

    def closeManager(self):
        self.log('closeManager')
        self.close()


    def onAction(self, act):
        actionId = act.getId()
        self.log('onAction: actionId = %s'%(actionId))
        if actionId in ACTION_PREVIOUS_MENU: self.closeManager()
        
        
    def onClick(self, controlId):
        self.log('onClick: controlId = %s'%(controlId))
        if   controlId == 0: self.closeManager()
        elif controlId == 5:
            self.buildChannelItem(self.chanList.getSelectedItem())
        elif controlId == 6:
            self.itemInput(self.chanList.getSelectedItem())
        elif controlId == 9001:
            label = self.getControl(controlId).getLabel()
            if   label == 'Close':  self.closeManager()
            # elif label == 'Save':   self.closeManager()
            # elif label == 'OK':     self.closeManager()
            # elif label == 'Cancel': self.closeManager()
    
    
    def onFocus(self, controlId):
        self.log('onFocus: controlId = %s'%(controlId))
        pass
            

    def saveChannels(self):
        log('saveChannels')
        if not self.madeChange: return
        if not yesnoDialog(LANGUAGE(30073)): return
        [self.channels.add(channel) for channel in self.newChannels if channel['path']]
        self.channels.save()
        self.madeChange = False
        setSetting('saveChannels', str(random.random()))
        return notificationDialog(LANGUAGE(30053))
        
        
    def clearChannel(self, item, prompt=True):
        if prompt and not yesnoDialog(LANGUAGE(30092)): return item
        nitem = self.newChannel.copy()
        nitem['number'] = item['number']
        newChannels = self.newChannels
        for channel in newChannels:
            if nitem["number"] == channel["number"]:
                self.madeChange = True
                log('Manager: Clearing channel %s settings'%(nitem["number"]))
                channel.update(nitem)
                return nitem
        return nitem


    def addChannel(self, item, prompt=True):
        log('Manager: addChannel, item = %s'%(item))
        if prompt and not yesnoDialog(LANGUAGE(30091)): return False
        self.madeChange = True
        newChannels = self.newChannels
        for channel in newChannels:
            if item["number"] == channel["number"]:
                log('Manager: Updating channel %s settings'%(item["number"]))
                channel.update(item)
                return True
        log('Manager: Adding channel %s settings'%(item["number"]))
        newChannels.append(item)
        self.newChannels = newChannels
        return True
        
        
    def buildArray(self):
        log('Manager: buildArray')
        for idx in range(self.channelLimit):
            newChannel = self.newChannel.copy()
            newChannel['number'] = idx + 1
            yield newChannel
                
                
    def createChannelList(self, channelArray, channelList):
        log('Manager: createChannelList')#todo elegant solution? 
        for item in channelArray:
            for channel in channelList:
                if item["number"] == channel["number"]:
                    item.update(channel)
            yield item


    # def buildChannelListItems(self):
        # log('Manager: buildChannelListItems')
        # if isBusy(): 
            # return notificationDialog(LANGUAGE(30029)%(ADDON_NAME))
        # with busy_dialog():
            # listItems = list(PoolHelper().poolList(self.buildChannelListItem,self.channelList))
        # select = selectDialog(listItems,'%s: %s'%(ADDON_NAME,LANGUAGE(30072)), multi=False)
        # if select >= 0: 
            # self.buildChannelItem(listItems[select])
            
        # if self.saveChannels():
            # return REAL_SETTINGS.openSettings()
        
    def selectRules(self, channelData):
        log('Manager: selectRules')
        notificationDialog('Coming Soon')
    
if __name__ == '__main__': Manager("%s.manager.xml"%(ADDON_ID), ADDON_PATH, "default")